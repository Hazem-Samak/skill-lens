"""Filesystem discovery: find skill entrypoints and tag how agents reach them.

Discovery is deliberately **agent-agnostic**. It scans every root of every
known agent and records, per entrypoint, which ``(agent, root)`` pairs reach
it. The resolver then decides, per agent, what is searched vs unsearched.

This split is what lets ``why`` explain an ``UNSEARCHED`` copy: the copy is
found because some *other* agent looks there, then marked as outside this
agent's search rules.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path

from skill_lens.core import paths
from skill_lens.core.cancellation import check_cancelled
from skill_lens.core.hasher import (
    IncompleteTreeError,
    PayloadLimitExceeded,
    hash_path,
    hash_path_bounded,
    iter_files,
)
from skill_lens.core.parser import (
    FRONTMATTER_DELIM,
    DocumentTooLarge,
    canonicalize,
    find_skill_document,
    frontmatter_has_description,
    parse_skill,
    split_frontmatter,
)
from skill_lens.models.enums import EntryFormat, ParseStatus, RootBase, Scope
from skill_lens.models.parsing import (
    ERR_DANGLING_SYMLINK,
    ERR_PERMISSION_DENIED,
    ERR_SYMLINK_CYCLE,
    CanonicalResult,
    CanonicalStatus,
    ParseResult,
)
from skill_lens.registry.loader import AgentDefinition, AgentRoot, load_registry

MAX_WALK_DEPTH = 4
MAX_OPENCODE_WALK_DEPTH = 32
MAX_PI_WALK_DEPTH = 16

#: How much of an incidental standalone Markdown file discovery may read to decide
#: whether it is a skill. The frontmatter and description sit at the top, so this
#: is far more than a qualification check needs; the point is that a multi-megabyte
#: README can never be read in full just to be skipped.
MAX_STANDALONE_QUALIFICATION_BYTES = 1024 * 1024

_MIB = 1024 * 1024


class SearchRefused(Exception):
    """Base for a deliberate, reported refusal before search results are built."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class SkillPayloadTooLarge(SearchRefused):
    """A search inventory exceeds its payload budget before any skill text was read.

    Raised only by the budgeted discovery path used by ``skill-lens search``.
    ``scan``, ``why``, ``compare`` and the TUI do not pass a budget and keep their
    existing behaviour.
    """

    def __init__(self, *, total_bytes: int, limit_bytes: int) -> None:
        self.total_bytes = total_bytes
        self.limit_bytes = limit_bytes
        super().__init__(
            f"Search refused: this home holds {_format_bytes(total_bytes)} "
            f"({total_bytes} bytes) of skill payload, above the "
            f"{_format_bytes(limit_bytes)} ({limit_bytes} bytes) search limit. "
            "Nothing was searched."
        )


class StandaloneQualificationTooLarge(SearchRefused):
    """A bounded qualification read could not tell whether a file is a skill.

    The file opens a frontmatter fence, but the closing fence is beyond the
    qualification prefix. Treating it as a skill would promote incidental
    Markdown; dropping it silently would hide a possible valid skill. Report the
    deliberate bound instead.
    """

    def __init__(self, path: Path, limit_bytes: int) -> None:
        self.path = path
        self.limit_bytes = limit_bytes
        super().__init__(
            f"Search refused: cannot qualify {str(path)!r} because its frontmatter is "
            f"larger than the {_format_bytes(limit_bytes)} ({limit_bytes} bytes) "
            "qualification limit. Nothing was searched."
        )


def _format_bytes(count: int) -> str:
    """Short human-readable size, matching the snapshot budget's wording."""
    if count >= _MIB:
        return f"{count / _MIB:.1f} MiB"
    if count >= 1024:
        return f"{count / 1024:.1f} KiB"
    return f"{count} B"


#: Most specific scope first. Used for stable ordering of scan rows and of
#: Variant A / B labels, so both commands agree on what "first" means.
SCOPE_SPECIFICITY = {
    Scope.PROJECT: 0,
    Scope.USER: 1,
    Scope.SYSTEM: 2,
    Scope.PLUGIN: 3,
}

#: Variant labels, in the order they are handed out. Copies beyond this many
#: are left unlabelled rather than given an invented letter.
VARIANT_LABELS = ("A", "B", "C", "D", "E", "F")


def entry_scope(entry: DiscoveredEntry) -> Scope:
    """The most project-specific scope any reaching root assigns to ``entry``.

    Deliberately a property of the *entry*, not of the agent asking about it:
    a library reachable both as a project root and as a user root has one
    inventory scope, and every consumer must agree on it.
    """
    scopes = {hit.scope for hit in entry.hits}
    for scope in (Scope.PROJECT, Scope.SYSTEM, Scope.PLUGIN, Scope.USER):
        if scope in scopes:
            return scope
    return Scope.USER


def variant_labels(items: Iterable[tuple[str, str, str | None, Scope, int]]) -> dict[str, str]:
    """Label same-named copies whose bytes differ as Variant A / B / ...

    **One rule, one set of inputs, used by both ``why`` and ``scan``.** Two
    earlier attempts were wrong in different ways: first the two commands
    ordered differently (scope vs an agent's rank), then they shared the
    ordering but still disagreed because they passed *different scopes* in --
    ``scan`` reported the most project-specific scope any root assigns, while
    ``why`` passed the scope of the one root the requested agent uses. The
    scope must come from :func:`entry_scope` on both sides, because it has to
    be a property of the entry rather than of whoever is asking.

    Ordering is by scope specificity (project before user), then discovery
    order. At most :data:`VARIANT_LABELS` copies are labelled; further copies
    are left unlabelled rather than given an invented letter.

    ``items`` are ``(name, key, content_hash, scope, position)`` tuples for one
    skill name, where ``key`` identifies the copy (its canonical path) and
    ``position`` is its stable index in discovery order.

    Copies with identical content hashes are the same bytes, not variants, and
    share one label. Copies that failed validation have no comparable content
    and are left unlabelled.
    """
    by_hash: dict[str | None, list[tuple[str, str, Scope, int]]] = {}
    for name, key, content_hash, scope, position in items:
        by_hash.setdefault(content_hash, []).append((name, key, scope, position))

    ordered = sorted(
        by_hash.values(),
        key=lambda group: (
            min(SCOPE_SPECIFICITY.get(scope, 9) for _n, _k, scope, _p in group),
            min(position for _n, _k, _s, position in group),
        ),
    )
    labels: dict[str, str] = {}
    for position, group in enumerate(ordered):
        if position >= len(VARIANT_LABELS):
            break
        for _name, key, _scope, _position in group:
            labels[key] = VARIANT_LABELS[position]
    return labels


def canonical_key(entry: DiscoveredEntry) -> str:
    """The key that identifies one copy: its canonical target, or its own path.

    A copy with no resolvable target (a dangling symlink, a cycle) is keyed by
    its entrypoint so it can never collapse onto a real skill.
    """
    return entry.canonical_path or entry.entrypoint_path


def labels_for_entries(entries: Iterable[DiscoveredEntry]) -> dict[str, str]:
    """Variant labels for a set of entries, keyed by :func:`canonical_key`.

    This is the one place the label inputs are assembled, so ``scan``, ``why``
    and ``diff`` cannot drift apart the way they did in finding F-16. The rules
    it encodes, all of them deliberate:

    * only *valid* copies that have a content hash are labelled -- a copy that
      failed validation has no comparable content and gets no letter;
    * the scope is always :func:`entry_scope`'s, because a copy's label must be
      a property of the copy and not of whichever command is asking;
    * ``position`` is the entry's index in the order given, which is what breaks
      ties between two copies of equal scope specificity.
    """
    by_name: dict[str, list[tuple[str, str, str | None, Scope, int]]] = {}
    for position, entry in enumerate(entries):
        if entry.parse_status != ParseStatus.VALID.value or entry.content_hash is None:
            continue
        by_name.setdefault(entry.name, []).append(
            (entry.name, canonical_key(entry), entry.content_hash, entry_scope(entry), position)
        )
    labels: dict[str, str] = {}
    for items in by_name.values():
        labels.update(variant_labels(items))
    return labels


@dataclass(frozen=True, slots=True)
class UnreadableRoot:
    """A search root that could not be read (e.g. TCC / PermissionError)."""

    agent_id: str
    root_id: str
    path: str
    detail: str
    display_path: str = ""


@dataclass(frozen=True, slots=True)
class RootHit:
    """Evidence that a single agent root reached this entrypoint.

    Carries the root's precedence rank and rule id so the resolver never has to
    guess where a copy came from. Carries the entrypoint path *this* root saw,
    which is what lets a symlink farm report genuine entrypoint counts while
    retaining the one canonical library.

    Note on ``is_file``: a root can discover a standalone ``.md`` file or a
    directory skill. When a symlink points to a file, the file rule id
    belongs to the hit -- not to the merged entry.
    """

    agent_id: str
    root_id: str
    rank: int
    rule_id: str
    evidence: str
    scope: Scope
    nested: bool = False
    file_rule_id: str | None = None
    nested_rule_id: str | None = None
    specificity: int = 0
    entrypoint_path: str = ""
    is_file: bool = False
    loadability: str | None = None

    def rule_for(self, is_file: bool) -> str:
        if self.nested and self.nested_rule_id:
            return self.nested_rule_id
        if is_file and self.file_rule_id:
            return self.file_rule_id
        return self.rule_id


@dataclass(frozen=True, slots=True)
class DiscoveredEntry:
    """A single canonical skill on disk plus every entrypoint that reaches it.

    One record per **canonical target** (spec section 4, *Inventory &
    Identity*): a symlink farm is one library with N entrypoints, never N
    installations.

    Each :class:`RootHit` in ``hits`` keeps its own ``entrypoint_path``, so the
    resolver can still judge precedence on the path the *requested* agent uses
    (spec section 4, *Precedence & Collision*). ``entrypoint_paths`` lists every
    path on disk, for honest counts.
    """

    entrypoint_path: str
    name: str
    is_file: bool
    is_symlink: bool
    canonical: CanonicalResult
    parse: ParseResult | None
    content_hash: str | None
    hits: tuple[RootHit, ...] = ()
    entrypoint_paths: tuple[str, ...] = ()
    variant_label: str | None = None
    traversal_complete: bool = True
    traversal_error: str | None = None

    @property
    def canonical_path(self) -> str | None:
        return self.canonical.resolved_path if self.canonical is not None else None

    @property
    def parse_status(self) -> str:
        if self.parse is not None:
            return self.parse.status.value
        return "invalid"

    @property
    def error_code(self) -> str | None:
        if self.canonical is None:
            return None
        if self.canonical.status is CanonicalStatus.CYCLE:
            return ERR_SYMLINK_CYCLE
        if self.canonical.status is CanonicalStatus.BROKEN:
            return ERR_DANGLING_SYMLINK
        if self.canonical.status is CanonicalStatus.UNREADABLE:
            return ERR_PERMISSION_DENIED
        return None


@dataclass(slots=True)
class DiscoveryIndex:
    """The aggregate output of a discovery run."""

    home: str
    cwd: str
    entries: list[DiscoveredEntry] = field(default_factory=list)
    unreadable_roots: list[UnreadableRoot] = field(default_factory=list)

    def all_agents(self) -> set[str]:
        return {hit.agent_id for entry in self.entries for hit in entry.hits}


# --- Boundary detection ----------------------------------------------------


def find_walk_boundary(cwd: Path, kind: str) -> Path | None:
    """Find the directory that bounds an upward project walk, if any.

    Looks for ``.git`` (a directory for a normal checkout, a file for a linked
    worktree). Returns ``None`` when no boundary marker is found, which means
    "this working directory is not inside a project" -- so project-scoped roots
    do not apply. This prevents a machine-wide ``scan`` from mislabelling
    global roots as project roots.
    """
    markers = (".git",) if kind != "project_root_markers" else (".git", "pyproject.toml")
    for directory in (cwd, *cwd.parents):
        for marker in markers:
            if (directory / marker).exists():
                return directory
    return None


def normalize_cwd(cwd: Path, home: Path) -> Path:
    """Resolve ``cwd`` to an absolute path, treating relative input as home-relative.

    ``--cwd .`` therefore means "the mock/real home itself", which keeps
    sandboxed scans inside the sandbox and never escapes into the process's
    real working directory.
    """
    expanded = Path(cwd).expanduser()
    if expanded.is_absolute():
        return expanded.resolve()
    return (home / expanded).resolve()


def _ancestor_dirs(cwd: Path, boundary: Path) -> list[Path]:
    """Directories from ``cwd`` up to and including ``boundary``."""
    chain: list[Path] = []
    current = cwd
    while True:
        chain.append(current)
        if current == boundary or current.parent == current:
            break
        current = current.parent
    return chain


# --- Root expansion --------------------------------------------------------


def _absolute_roots_allowed(home: Path) -> bool:
    """Absolute system roots (e.g. ``/etc/codex/skills``) are scanned live only.

    Under a sandbox (tests, ``--sandbox``) they are skipped so a scan can never
    read real system directories and contaminate deterministic results.
    """
    return paths.get_sandbox() is None and home == paths.home()


def _directories_for_root(
    home: Path,
    cwd: Path,
    root: AgentRoot,
    boundary: Path | None,
) -> list[tuple[Path, bool]]:
    """Resolve an :class:`AgentRoot` to the concrete filesystem paths to search."""
    if root.is_absolute:
        if not _absolute_roots_allowed(home):
            return []
        return [(Path(root.path), False)]

    if not root.is_project:
        if root.base == RootBase.XDG_CONFIG_HOME:
            xdg_base = paths.xdg_config_home()
            relative_path = (
                root.path[len(".config/") :] if root.path.startswith(".config/") else root.path
            )
            return [(xdg_base / relative_path, False)]
        return [(home / root.path, False)]

    if boundary is None:
        return []

    results: list[tuple[Path, bool]] = []
    for directory in _ancestor_dirs(cwd, boundary):
        candidate = directory / root.path
        try:
            if candidate.exists() or candidate.is_symlink():
                results.append((candidate, directory != boundary))
        except OSError:
            continue
    return results


# --- Entrypoint listing ----------------------------------------------------


def _has_exact_skill_md(directory: Path) -> bool:
    """True when ``directory`` contains a child whose literal name is ``SKILL.md``.

    Comparing actual directory entry names via ``os.listdir`` prevents
    case-insensitive filesystems (such as APFS on macOS) from falsely
    matching lowercase ``skill.md`` or ``.skill.md``.
    """
    try:
        return "SKILL.md" in os.listdir(directory)
    except OSError:
        return False


def _is_skill_dir(path: Path) -> bool:
    return find_skill_document(path) is not None


def _read_qualification_prefix(path: Path, max_bytes: int) -> tuple[str, bool] | None:
    """Read a standalone document prefix and say whether the file was truncated.

    ``None`` means the file could not be read at all. A truncated prefix can
    still hold a complete frontmatter block; that is enough to qualify a skill
    whose body is larger than the prefix.
    """
    try:
        with path.open("rb") as handle:
            data = bytearray()
            remaining = max_bytes + 1
            while remaining > 0:
                chunk = handle.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                data.extend(chunk)
                remaining -= len(chunk)
    except OSError:
        return None
    truncated = len(data) > max_bytes
    if truncated:
        del data[max_bytes:]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as err:
        # A prefix can end inside a multi-byte character. Trim at most three
        # bytes only when the cutoff split a character; malformed UTF-8 in a
        # complete file must still fail qualification.
        if not truncated or err.reason != "unexpected end of data":
            return None
        text = data[: err.start].decode("utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text, truncated


def _qualified_standalone_prefix(path: Path, max_bytes: int) -> bool:
    """Qualify a standalone Markdown file from a bounded frontmatter prefix.

    Incidental Markdown is never promoted: without a frontmatter fence at the
    top the rest of the file cannot change the answer. A complete valid
    frontmatter block qualifies even when the body is much larger than the
    prefix, because the real payload budget is enforced afterwards. If the
    prefix ends while a frontmatter block is still open, the bound is reported
    instead of guessing in either direction.
    """
    read = _read_qualification_prefix(path, max_bytes)
    if read is None:
        return False
    text, truncated = read
    complete_text = text
    if truncated:
        # A cutoff partway through a line can make the first part look like a
        # closing YAML fence. Only complete lines can qualify the document.
        complete_text = text[: text.rfind("\n") + 1]
    frontmatter_text, _body = split_frontmatter(complete_text)
    if frontmatter_text is not None:
        return frontmatter_has_description(frontmatter_text)
    stripped = text.lstrip("\ufeff")
    first_line = stripped.split("\n", 1)[0]
    if (
        truncated
        and stripped.startswith(FRONTMATTER_DELIM)
        and first_line.strip() == FRONTMATTER_DELIM
    ):
        raise StandaloneQualificationTooLarge(path, max_bytes)
    return False


def _is_declared_or_qualified_standalone_md(
    path: Path, *, max_prefix_bytes: int | None = None
) -> bool:
    """True when ``path`` is an explicit skill document or a qualified standalone .md.

    For Pi-style discovery: declared skill documents (``SKILL.md``) are always
    discovered so malformed declarations can be diagnosed. Other standalone
    markdown files (e.g. ``README.md``) are incidental unless they contain valid
    frontmatter with a non-empty description.

    With ``max_prefix_bytes``, only the frontmatter prefix is read. A valid
    header qualifies even when the body is oversized; the caller then enforces
    the real payload budget. Incidental Markdown without a header is skipped
    without reading its body. An inconclusive header bound is reported through
    :class:`StandaloneQualificationTooLarge` rather than guessed.
    """
    if path.name == "SKILL.md":
        return True
    if path.suffix.lower() != ".md":
        return False
    if max_prefix_bytes is not None:
        return _qualified_standalone_prefix(path, max_prefix_bytes)
    try:
        parse = parse_skill(path)
        return bool(parse and parse.description and parse.description.strip())
    except (OSError, UnicodeDecodeError, ValueError):
        return False


def _is_standalone_md_allowed(
    fmt: EntryFormat | str, path: Path, *, max_prefix_bytes: int | None = None
) -> bool:
    if fmt in (EntryFormat.STANDALONE_MD, EntryFormat.OPENCODE_V2):
        return True
    if fmt == EntryFormat.QUALIFIED_STANDALONE_MD:
        return _is_declared_or_qualified_standalone_md(path, max_prefix_bytes=max_prefix_bytes)
    return False


def _list_entries(
    base: Path,
    *,
    cancelled: Callable[[], bool] | None = None,
    root: AgentRoot | None = None,
    max_prefix_bytes: int | None = None,
) -> list[tuple[Path, bool]]:
    """List skill entrypoints directly under ``base`` as ``(path, is_file)``.

    A ``.system`` container is **not** descended here: bundled system skills are
    owned by a dedicated root whose path ends in ``.system`` (see codex.toml),
    so attributing them here too would give them the wrong scope and rank.
    """
    check_cancelled(cancelled)
    try:
        children = sorted(base.iterdir(), key=lambda p: p.name)
    except OSError:
        return []

    fmt = root.entry_format if root is not None else EntryFormat.DIRECTORY

    results: list[tuple[Path, bool]] = []
    for child in children:
        check_cancelled(cancelled)
        if child.is_symlink():
            try:
                target = child.resolve()
            except (OSError, RuntimeError):
                results.append((child, False))
                continue

            if not target.exists():
                results.append((child, False))
                continue

            if target.is_dir():
                if fmt in (EntryFormat.QUALIFIED_STANDALONE_MD, EntryFormat.OPENCODE_V2):
                    if _has_exact_skill_md(target) or _unreadable(target):
                        results.append((child, False))
                else:
                    results.append((child, False))
            elif target.is_file():
                if fmt == EntryFormat.DIRECTORY:
                    # Directory-only roots must ignore file targets, regardless of metadata or name.
                    continue
                if fmt in (EntryFormat.STANDALONE_MD, EntryFormat.OPENCODE_V2):
                    if child.name == "SKILL.md" or child.suffix.lower() == ".md":
                        results.append((child, True))
                elif fmt == EntryFormat.QUALIFIED_STANDALONE_MD:
                    is_exact_or_qual = child.name == "SKILL.md" or (
                        child.suffix.lower() == ".md"
                        and _is_declared_or_qualified_standalone_md(
                            target, max_prefix_bytes=max_prefix_bytes
                        )
                    )
                    if is_exact_or_qual:
                        results.append((child, True))
        elif child.is_dir():
            if fmt in (EntryFormat.QUALIFIED_STANDALONE_MD, EntryFormat.OPENCODE_V2):
                if _has_exact_skill_md(child) or _unreadable(child):
                    results.append((child, False))
            else:
                if _is_skill_dir(child) or _unreadable(child):
                    results.append((child, False))
        elif child.suffix.lower() == ".md" and _is_standalone_md_allowed(
            fmt, child, max_prefix_bytes=max_prefix_bytes
        ):
            results.append((child, True))
    return results


def _record_truncation(
    truncated_collector: list[UnreadableRoot] | None,
    agent_id: str,
    root: AgentRoot | None,
    base: Path,
) -> None:
    if (
        truncated_collector is not None
        and root is not None
        and not any(
            ur.agent_id == agent_id
            and ur.root_id == root.id
            and ur.path == str(base)
            and ur.detail == "depth_limit_truncated"
            for ur in truncated_collector
        )
    ):
        truncated_collector.append(
            UnreadableRoot(
                agent_id=agent_id,
                root_id=root.id,
                path=str(base),
                detail="depth_limit_truncated",
                display_path=paths.display(base),
            )
        )


def _list_recursive_entries(
    base: Path,
    *,
    cancelled: Callable[[], bool] | None = None,
    root: AgentRoot | None = None,
    truncated_collector: list[UnreadableRoot] | None = None,
    agent_id: str = "",
    max_prefix_bytes: int | None = None,
) -> list[tuple[Path, bool]]:
    """Find skill directories under ``base``."""
    check_cancelled(cancelled)
    fmt = root.entry_format if root is not None else EntryFormat.DIRECTORY

    found: list[tuple[Path, bool]] = []
    base_depth = len(base.parts)

    # 1. OpenCode V2 discovery
    if fmt == EntryFormat.OPENCODE_V2:
        try:
            root_children = sorted(base.iterdir(), key=lambda p: p.name)
        except OSError:
            return []
        for child in root_children:
            check_cancelled(cancelled)
            if child.is_symlink():
                try:
                    target = child.resolve()
                except (OSError, RuntimeError):
                    found.append((child, False))
                    continue
                if not target.exists():
                    found.append((child, False))
                    continue
                if target.is_file() and (child.suffix.lower() == ".md" or child.name == "SKILL.md"):
                    found.append((child, True))
                elif target.is_dir() and (_has_exact_skill_md(target) or _unreadable(target)):
                    found.append((child, False))
            elif child.is_file() and child.suffix.lower() == ".md":
                found.append((child, True))

        visited_real: set[Path] = set()
        for dirpath, dirnames, filenames in os.walk(base):
            check_cancelled(cancelled)
            current = Path(dirpath)
            try:
                real_p = current.resolve()
                if real_p in visited_real:
                    dirnames[:] = []
                    continue
                visited_real.add(real_p)
            except (OSError, RuntimeError):
                pass

            if current == base:
                dirnames[:] = [d for d in dirnames if d != ".git"]
                continue

            dirnames[:] = [d for d in dirnames if d != ".git"]
            depth = len(current.parts) - base_depth

            if depth > MAX_OPENCODE_WALK_DEPTH:
                if dirnames and truncated_collector is not None and root is not None:
                    _record_truncation(truncated_collector, agent_id, root, base)
                dirnames[:] = []
                continue

            if _has_exact_skill_md(current) or _unreadable(current):
                found.append((current, False))
                # OpenCode V2: DO NOT clear dirnames; continue descending to find nested skills!

            if depth >= MAX_OPENCODE_WALK_DEPTH:
                if dirnames and truncated_collector is not None and root is not None:
                    _record_truncation(truncated_collector, agent_id, root, base)
                dirnames[:] = []
                continue

            for name in list(dirnames) + list(filenames):
                check_cancelled(cancelled)
                child = current / name
                if child.is_symlink():
                    try:
                        target = child.resolve()
                    except (OSError, RuntimeError):
                        found.append((child, False))
                        continue
                    if not target.exists():
                        found.append((child, False))
                        continue
                    if target.is_dir() and (_has_exact_skill_md(target) or _unreadable(target)):
                        found.append((child, False))
        return found

    # 2. Pi Coding Agent discovery (stop-at-SKILL.md, recursion with ignore rules)
    is_pi_root = root is not None and (
        root.id in ("pi_global_agent", "pi_global", "pi_project", "pi_project_agents")
        or (root.id.startswith("pi_") and root.rule_id.startswith("pi_"))
    )
    if is_pi_root:
        try:
            root_children = sorted(base.iterdir(), key=lambda p: p.name)
        except OSError:
            return []
        for child in root_children:
            check_cancelled(cancelled)
            if child.is_symlink():
                try:
                    target = child.resolve()
                except (OSError, RuntimeError):
                    found.append((child, False))
                    continue
                if not target.exists():
                    found.append((child, False))
                    continue
                if target.is_file() and (child.suffix.lower() == ".md" or child.name == "SKILL.md"):
                    if _is_declared_or_qualified_standalone_md(
                        target, max_prefix_bytes=max_prefix_bytes
                    ):
                        found.append((child, True))
                elif target.is_dir() and (_has_exact_skill_md(target) or _unreadable(target)):
                    found.append((child, False))
            elif child.is_file() and child.suffix.lower() == ".md":
                if child.name in (
                    "SKILL.md",
                    "skill.md",
                ) or _is_declared_or_qualified_standalone_md(
                    child, max_prefix_bytes=max_prefix_bytes
                ):
                    found.append((child, True))

        visited_real_pi: set[Path] = set()
        for dirpath, dirnames, _filenames in os.walk(base):
            check_cancelled(cancelled)
            current = Path(dirpath)
            try:
                real_p = current.resolve()
                if real_p in visited_real_pi:
                    dirnames[:] = []
                    continue
                visited_real_pi.add(real_p)
            except (OSError, RuntimeError):
                pass

            if current == base:
                dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "node_modules"]
                continue

            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "node_modules"]
            depth = len(current.parts) - base_depth

            if depth > MAX_PI_WALK_DEPTH:
                if dirnames and truncated_collector is not None and root is not None:
                    _record_truncation(truncated_collector, agent_id, root, base)
                dirnames[:] = []
                continue

            if _has_exact_skill_md(current) or _unreadable(current):
                found.append((current, False))
                # Pi STOP-AT-SKILL: do not recurse into subdirectories of a skill
                dirnames[:] = []
            elif depth >= MAX_PI_WALK_DEPTH:
                if dirnames and truncated_collector is not None and root is not None:
                    _record_truncation(truncated_collector, agent_id, root, base)
                dirnames[:] = []
        return found

    # 3. Standard recursive roots
    for dirpath, dirnames, _filenames in os.walk(base):
        check_cancelled(cancelled)
        current = Path(dirpath)
        if current == base:
            dirnames[:] = [d for d in dirnames if d != ".git"]
            continue

        dirnames[:] = [d for d in dirnames if d != ".git"]
        depth = len(current.parts) - base_depth

        if depth > MAX_WALK_DEPTH:
            if dirnames and truncated_collector is not None and root is not None:
                _record_truncation(truncated_collector, agent_id, root, base)
            dirnames[:] = []
            continue

        if current.name == "skills":
            found.extend(
                _list_entries(
                    current,
                    cancelled=cancelled,
                    root=root,
                    max_prefix_bytes=max_prefix_bytes,
                )
            )
            dirnames[:] = []
        elif depth >= MAX_WALK_DEPTH:
            if dirnames and truncated_collector is not None and root is not None:
                _record_truncation(truncated_collector, agent_id, root, base)
            dirnames[:] = []
    return found


# --- Main discovery --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _PendingEntry:
    """One discovered entrypoint whose payload has not been read yet."""

    entrypoint: Path
    is_file: bool
    hit: RootHit
    canonical: CanonicalResult


def _measure_pending_payload(
    pending: list[_PendingEntry],
    *,
    limit_bytes: int,
    cancelled: Callable[[], bool] | None = None,
) -> None:
    """Refuse a known-oversized payload before any skill text is read.

    Only ``stat``/directory listing is used, so an oversized file is sized
    without reading it. The running total is checked after every measurable
    file: a known lower bound above the budget is refused even when some other
    file in the inventory cannot be measured. An unreadable file that does not
    itself prove overage is left to the existing incomplete-tree reporting, so
    an under-budget home keeps its health information.
    """
    seen: set[str] = set()
    total = 0
    for item in pending:
        check_cancelled(cancelled)
        if item.canonical.status is not CanonicalStatus.OK:
            continue
        root = Path(item.canonical.resolved_path or item.entrypoint)
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        try:
            is_directory = root.is_dir()
        except OSError:
            continue
        if is_directory:
            try:
                relatives = iter_files(root, cancelled=cancelled)
            except OSError:
                continue
            for relative in relatives:
                check_cancelled(cancelled)
                try:
                    size = (root / relative).stat().st_size
                except OSError:
                    continue
                total += size
                if total > limit_bytes:
                    raise SkillPayloadTooLarge(total_bytes=total, limit_bytes=limit_bytes)
        else:
            try:
                total += root.stat().st_size
            except OSError:
                continue
            if total > limit_bytes:
                raise SkillPayloadTooLarge(total_bytes=total, limit_bytes=limit_bytes)


class _PayloadBudget:
    """Actual payload consumed while building budgeted discovery entries."""

    def __init__(self, limit_bytes: int) -> None:
        self.limit_bytes = limit_bytes
        self.consumed = 0

    @property
    def remaining(self) -> int:
        return max(0, self.limit_bytes - self.consumed)

    def add(self, count: int) -> None:
        self.consumed += count
        if self.consumed > self.limit_bytes:
            raise SkillPayloadTooLarge(total_bytes=self.consumed, limit_bytes=self.limit_bytes)


def discover(
    home: Path,
    cwd: Path,
    registry: dict[str, AgentDefinition] | None = None,
    *,
    cancelled: Callable[[], bool] | None = None,
    max_payload_bytes: int | None = None,
) -> DiscoveryIndex:
    """Scan every agent's roots and return a tagged :class:`DiscoveryIndex`.

    When ``max_payload_bytes`` is a positive number, the walk first lists and
    canonicalises every entrypoint, measures each canonical copy's payload, and
    refuses an oversized inventory with :class:`SkillPayloadTooLarge` before any
    skill document or support file is read. Reads made while deciding whether a
    standalone Markdown file qualifies are bounded too. A value of ``None`` or
    ``0`` keeps the existing unbounded discovery behaviour.
    """
    check_cancelled(cancelled)
    agents = registry if registry is not None else load_registry()
    cwd = normalize_cwd(cwd, home)
    index = DiscoveryIndex(home=str(home), cwd=str(cwd))
    budgeted = max_payload_bytes is not None and max_payload_bytes > 0
    qualification_bytes: int | None = None
    if budgeted and max_payload_bytes is not None:
        qualification_bytes = min(max_payload_bytes, MAX_STANDALONE_QUALIFICATION_BYTES)
    pending: list[_PendingEntry] = []

    seen: set[tuple[str, str, str]] = set()
    for agent in agents.values():
        check_cancelled(cancelled)
        boundary = find_walk_boundary(cwd, agent.walk_boundary)
        for root in agent.roots:
            check_cancelled(cancelled)
            for base, nested in _directories_for_root(home, cwd, root, boundary):
                check_cancelled(cancelled)
                try:
                    if not base.exists() and not base.is_symlink():
                        continue
                    if base.is_dir() and not base.is_symlink() and _unreadable(base):
                        index.unreadable_roots.append(
                            UnreadableRoot(
                                agent_id=agent.id,
                                root_id=root.id,
                                path=str(base),
                                detail=ERR_PERMISSION_DENIED,
                                display_path=paths.display(base),
                            )
                        )
                        continue
                except OSError:
                    # The root, or a parent directory, cannot be inspected --
                    # e.g. a nested root under a TCC-blocked parent. The blocked
                    # parent is recorded as unreadable on its own pass; skip
                    # this one rather than letting a stat behind it abort the
                    # whole walk (Python 3.11-3.13 re-raise PermissionError from
                    # ``exists``/``is_dir``; 3.14 swallows it).
                    continue
                listing = (
                    _list_recursive_entries(
                        base,
                        cancelled=cancelled,
                        root=root,
                        truncated_collector=index.unreadable_roots,
                        agent_id=agent.id,
                        max_prefix_bytes=qualification_bytes,
                    )
                    if root.recursive or root.entry_format == EntryFormat.OPENCODE_V2
                    else _list_entries(
                        base,
                        cancelled=cancelled,
                        root=root,
                        max_prefix_bytes=qualification_bytes,
                    )
                )
                for entrypoint, is_file in listing:
                    check_cancelled(cancelled)
                    key = (agent.id, root.id, str(entrypoint))
                    if key in seen:
                        continue
                    seen.add(key)
                    hit = RootHit(
                        agent_id=agent.id,
                        root_id=root.id,
                        rank=root.rank,
                        rule_id=root.rule_id,
                        evidence=root.evidence.value,
                        scope=root.scope,
                        nested=nested,
                        file_rule_id=root.file_rule_id,
                        nested_rule_id=root.nested_rule_id,
                        specificity=(
                            len(base.parts) if root.is_project else len(Path(root.path).parts)
                        ),
                        entrypoint_path=str(entrypoint),
                        is_file=is_file,
                        loadability=root.loadability,
                    )
                    if budgeted:
                        pending.append(
                            _PendingEntry(
                                entrypoint=entrypoint,
                                is_file=is_file,
                                hit=hit,
                                canonical=canonicalize(entrypoint),
                            )
                        )
                    else:
                        index.entries.append(
                            _build_entry(entrypoint, is_file, hit, cancelled=cancelled)
                        )

    if budgeted:
        assert max_payload_bytes is not None
        _measure_pending_payload(pending, limit_bytes=max_payload_bytes, cancelled=cancelled)
        budget = _PayloadBudget(max_payload_bytes)
        built: dict[str, DiscoveredEntry] = {}
        for item in pending:
            check_cancelled(cancelled)
            copy_key = item.canonical.resolved_path or f"@{item.entrypoint}"
            cached = built.get(copy_key)
            if cached is not None:
                # Another entrypoint reaches the same physical copy. Reuse its
                # parsed text and fingerprint instead of reading the payload a
                # second time; the merge below still records every alias.
                index.entries.append(
                    replace(
                        cached,
                        entrypoint_path=str(item.entrypoint),
                        is_file=item.is_file,
                        is_symlink=item.entrypoint.is_symlink(),
                        hits=(item.hit,),
                        entrypoint_paths=(str(item.entrypoint),),
                        variant_label=None,
                    )
                )
                continue
            entry = _build_entry(
                item.entrypoint,
                item.is_file,
                item.hit,
                canonical=item.canonical,
                budget=budget,
                cancelled=cancelled,
            )
            built[copy_key] = entry
            index.entries.append(entry)

    index.entries = _merge_entries(index.entries)
    return index


def _unreadable(path: Path) -> bool:
    try:
        os.listdir(path)
    except OSError:
        return True
    return False


def _build_entry(
    entrypoint: Path,
    is_file: bool,
    hit: RootHit,
    *,
    canonical: CanonicalResult | None = None,
    budget: _PayloadBudget | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> DiscoveredEntry:
    check_cancelled(cancelled)
    canonical = canonical if canonical is not None else canonicalize(entrypoint)
    parse: ParseResult | None = None
    content_hash: str | None = None
    traversal_complete = True
    traversal_error: str | None = None
    document_bytes = 0
    fingerprint_bytes = 0

    def record_document_size(count: int) -> None:
        nonlocal document_bytes
        document_bytes = count

    if canonical.status is CanonicalStatus.OK:
        check_cancelled(cancelled)
        if budget is None:
            parse = parse_skill(entrypoint)
        else:
            try:
                parse = parse_skill(
                    entrypoint,
                    max_document_bytes=budget.remaining,
                    count_bytes=record_document_size,
                )
            except DocumentTooLarge as err:
                # The document grew after pre-flight (or the previous copies
                # used the remaining allowance). Refuse instead of reading an
                # unbounded file or exceeding the aggregate budget.
                raise SkillPayloadTooLarge(
                    total_bytes=budget.consumed + err.limit_bytes + 1,
                    limit_bytes=budget.limit_bytes,
                ) from err
        check_cancelled(cancelled)
        try:
            if budget is None:
                content_hash = hash_path(entrypoint, cancelled=cancelled)
            else:
                content_hash, fingerprint_bytes = hash_path_bounded(
                    entrypoint,
                    max_bytes=budget.remaining,
                    cancelled=cancelled,
                )
        except PayloadLimitExceeded as err:
            consumed = budget.consumed if budget is not None else 0
            raise SkillPayloadTooLarge(
                total_bytes=consumed + err.total_bytes,
                limit_bytes=budget.limit_bytes if budget is not None else err.limit_bytes,
            ) from err
        except IncompleteTreeError as err:
            content_hash = None
            traversal_complete = False
            traversal_error = err.reason
            fingerprint_bytes = err.payload_bytes
        except OSError as err:
            content_hash = None
            traversal_complete = False
            traversal_error = (
                "denied"
                if isinstance(err, PermissionError)
                else ("disappeared" if isinstance(err, FileNotFoundError) else "io")
            )
        if budget is not None:
            # Keep charging the parsed document if the fingerprint was partial
            # or the document shrank. Both phases normally read the same bytes.
            budget.add(max(document_bytes, fingerprint_bytes))

    name = _entry_name(entrypoint, is_file, parse)
    return DiscoveredEntry(
        entrypoint_path=str(entrypoint),
        name=name,
        is_file=is_file,
        is_symlink=entrypoint.is_symlink(),
        canonical=canonical,
        parse=parse,
        content_hash=content_hash,
        hits=(hit,),
        entrypoint_paths=(str(entrypoint),),
        traversal_complete=traversal_complete,
        traversal_error=traversal_error,
    )


def _entry_name(entrypoint: Path, is_file: bool, parse: ParseResult | None) -> str:
    if is_file:
        return entrypoint.stem
    if parse is not None:
        return parse.directory_name
    return entrypoint.name


def _merge_entries(entries: list[DiscoveredEntry]) -> list[DiscoveredEntry]:
    """Group entrypoints that share a canonical target into one record.

    A symlink farm (many entrypoints, one real target) becomes a single entry
    whose ``hits`` union every reaching root, each hit keeping the entrypoint
    path *it* was reached through. Entries with no resolvable canonical (cycles,
    dangling links) are keyed by their own path so they never collapse with a
    real skill.
    """
    merged: dict[str, DiscoveredEntry] = {}
    order: list[str] = []
    for entry in entries:
        key = entry.canonical_path or f"@{entry.entrypoint_path}"
        if key not in merged:
            merged[key] = entry
            order.append(key)
            continue
        existing = merged[key]
        hits = _union_hits(existing.hits, entry.hits)
        merged[key] = DiscoveredEntry(
            entrypoint_path=existing.entrypoint_path,
            name=existing.name or entry.name,
            # A symlinked ``.md`` is a file skill even when the sibling entry
            # that reached the same target was a directory, so OR the flags.
            is_file=existing.is_file or entry.is_file,
            is_symlink=existing.is_symlink or entry.is_symlink,
            canonical=existing.canonical,
            parse=existing.parse or entry.parse,
            content_hash=(
                None
                if not (existing.traversal_complete and entry.traversal_complete)
                else (existing.content_hash or entry.content_hash)
            ),
            hits=hits,
            entrypoint_paths=_union_paths(existing.entrypoint_paths, entry.entrypoint_paths),
            traversal_complete=existing.traversal_complete and entry.traversal_complete,
            traversal_error=existing.traversal_error or entry.traversal_error,
        )
    return [merged[key] for key in order]


def _union_paths(current: tuple[str, ...], incoming: tuple[str, ...]) -> tuple[str, ...]:
    """Concatenate entrypoint paths, keeping order and dropping duplicates.

    Several agent roots can reach the same physical path, so the same path may
    arrive more than once; counting it twice would inflate the metrics.
    """
    seen: set[str] = set()
    merged: list[str] = []
    for path in (*current, *incoming):
        if path not in seen:
            seen.add(path)
            merged.append(path)
    return tuple(merged)


def _union_hits(current: tuple[RootHit, ...], incoming: tuple[RootHit, ...]) -> tuple[RootHit, ...]:
    combined = list(current)
    existing = {(h.entrypoint_path, h.agent_id, h.root_id, h.nested) for h in combined}
    for hit in incoming:
        marker = (hit.entrypoint_path, hit.agent_id, hit.root_id, hit.nested)
        if marker not in existing:
            combined.append(hit)
            existing.add(marker)
    return tuple(combined)
