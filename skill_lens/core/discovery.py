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
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from skill_lens.core.hasher import hash_path
from skill_lens.core.parser import canonicalize, find_skill_document, parse_skill
from skill_lens.models.enums import ParseStatus, Scope
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
class RootHit:
    """One ``(agent, root)`` pair that reaches an entrypoint.

    ``entrypoint_path`` is the *path this root actually sees*. A symlink farm
    reaches one canonical library through several different paths, and
    precedence is judged per entrypoint path (spec section 4), so the path
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

    @property
    def canonical_path(self) -> str | None:
        return self.canonical.resolved_path

    @property
    def parse_status(self) -> str:
        if self.parse is not None:
            return self.parse.status.value
        return "invalid"

    @property
    def error_code(self) -> str | None:
        if self.canonical.status is CanonicalStatus.CYCLE:
            return ERR_SYMLINK_CYCLE
        if self.canonical.status is CanonicalStatus.BROKEN:
            return ERR_DANGLING_SYMLINK
        if self.canonical.status is CanonicalStatus.UNREADABLE:
            return ERR_PERMISSION_DENIED
        return None


@dataclass(frozen=True, slots=True)
class UnreadableRoot:
    """A root that exists but could not be listed (e.g. macOS TCC)."""

    agent_id: str
    root_id: str
    path: str
    detail: str


@dataclass(slots=True)
class DiscoveryIndex:
    """The result of one full discovery pass over a mock or real home."""

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
        return expanded
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
    from skill_lens.core import paths

    return paths.get_sandbox() is None and home == paths.home()


def _directories_for_root(
    home: Path, cwd: Path, root: AgentRoot, boundary: Path | None
) -> list[tuple[Path, bool]]:
    """Return ``(directory, nested)`` pairs a root resolves to for this cwd.

    Global/system/plugin roots are relative to the home directory. Project
    roots are joined onto each ancestor of ``cwd`` up to the git boundary, so a
    project skill is the *root* copy (not nested) while a skill found further up
    the monorepo from the working directory is nested (qualifies as ``dir:skill``).
    When there is no boundary (cwd is not in a project), no project root applies.
    """
    if root.is_absolute:
        if not _absolute_roots_allowed(home):
            return []
        return [(Path(root.path), False)]
    if not root.is_project:
        return [(home / root.path, False)]
    if boundary is None:
        return []

    results: list[tuple[Path, bool]] = []
    for directory in _ancestor_dirs(cwd, boundary):
        candidate = directory / root.path
        if candidate.exists() or candidate.is_symlink():
            results.append((candidate, directory != boundary))
    return results


# --- Entry listing ---------------------------------------------------------


def _is_skill_dir(path: Path) -> bool:
    return find_skill_document(path) is not None


def _is_symlinked_markdown(path: Path) -> bool:
    """True when ``path`` is a symlink whose target is a standalone ``.md`` file.

    A symlinked file skill must keep the *file* classification, otherwise the
    root's ``file_rule_id`` is never emitted and a standalone-file agent reports
    the directory-skill rule instead. Resolved safely: an unresolvable link
    (cycle, dangling) simply is not a markdown file skill.
    """
    if path.suffix.lower() != ".md":
        return False
    try:
        return path.resolve().is_file()
    except OSError:
        return False


def _list_entries(base: Path) -> list[tuple[Path, bool]]:
    """List skill entrypoints directly under ``base`` as ``(path, is_file)``.

    A ``.system`` container is **not** descended here: bundled system skills are
    owned by a dedicated root whose path ends in ``.system`` (see codex.toml),
    so attributing them here too would give them the wrong scope and rank.
    """
    try:
        children = sorted(base.iterdir(), key=lambda p: p.name)
    except OSError:
        return []

    results: list[tuple[Path, bool]] = []
    for child in children:
        if child.is_symlink():
            results.append((child, _is_symlinked_markdown(child)))
        elif child.is_dir():
            if _is_skill_dir(child) or _unreadable(child):
                results.append((child, False))
        elif child.suffix.lower() == ".md":
            results.append((child, True))
    return results


def _list_recursive_entries(base: Path) -> list[tuple[Path, bool]]:
    """Find ``skills`` directories under ``base`` up to :data:`MAX_WALK_DEPTH`."""
    found: list[tuple[Path, bool]] = []
    base_depth = len(base.parts)
    for dirpath, dirnames, _filenames in os.walk(base):
        current = Path(dirpath)
        if len(current.parts) - base_depth >= MAX_WALK_DEPTH:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d != ".git"]
        if current.name == "skills":
            found.extend(_list_entries(current))
            dirnames[:] = []
    return found


# --- Main discovery --------------------------------------------------------


def discover(
    home: Path,
    cwd: Path,
    registry: dict[str, AgentDefinition] | None = None,
) -> DiscoveryIndex:
    """Scan every agent's roots and return a tagged :class:`DiscoveryIndex`."""
    agents = registry if registry is not None else load_registry()
    cwd = normalize_cwd(cwd, home)
    index = DiscoveryIndex(home=str(home), cwd=str(cwd))

    seen: set[tuple[str, str, str]] = set()
    for agent in agents.values():
        boundary = find_walk_boundary(cwd, agent.walk_boundary)
        for root in agent.roots:
            for base, nested in _directories_for_root(home, cwd, root, boundary):
                if not base.exists() and not base.is_symlink():
                    continue
                if base.is_dir() and not base.is_symlink() and _unreadable(base):
                    index.unreadable_roots.append(
                        UnreadableRoot(
                            agent_id=agent.id,
                            root_id=root.id,
                            path=str(base),
                            detail=ERR_PERMISSION_DENIED,
                        )
                    )
                    continue
                listing = _list_recursive_entries(base) if root.recursive else _list_entries(base)
                for entrypoint, is_file in listing:
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
                        specificity=len(Path(root.path).parts),
                        entrypoint_path=str(entrypoint),
                    )
                    index.entries.append(_build_entry(entrypoint, is_file, hit))

    index.entries = _merge_entries(index.entries)
    return index


def _unreadable(path: Path) -> bool:
    try:
        os.listdir(path)
    except OSError:
        return True
    return False


def _build_entry(entrypoint: Path, is_file: bool, hit: RootHit) -> DiscoveredEntry:
    canonical = canonicalize(entrypoint)
    parse: ParseResult | None = None
    content_hash: str | None = None
    if canonical.status is CanonicalStatus.OK:
        parse = parse_skill(entrypoint)
        try:
            content_hash = hash_path(entrypoint)
        except OSError:
            content_hash = None

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
    )


def _entry_name(entrypoint: Path, is_file: bool, parse: ParseResult | None) -> str:
    if parse is not None:
        return parse.directory_name
    if is_file or entrypoint.suffix.lower() == ".md":
        return entrypoint.stem
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
            content_hash=existing.content_hash or entry.content_hash,
            hits=hits,
            entrypoint_paths=_union_paths(existing.entrypoint_paths, entry.entrypoint_paths),
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
    existing = {(h.agent_id, h.root_id, h.nested) for h in combined}
    for hit in incoming:
        marker = (hit.agent_id, hit.root_id, hit.nested)
        if marker not in existing:
            combined.append(hit)
            existing.add(marker)
    return tuple(combined)
