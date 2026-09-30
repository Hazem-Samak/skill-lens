"""Unified-diff computation for ``skill-lens diff`` (Phase 3).

Pure by design: this module imports no ``rich``. It turns a
:class:`~skill_lens.core.discovery.DiscoveryIndex` into a
:class:`~skill_lens.models.diff.DiffReport`, and the terminal layer renders that
model and nothing else.

Three rules from the specification (section 6, command 5) drive the design:

* **One copy per canonical target.** The index is already deduplicated, so this
  module never re-groups entrypoints. Two symlinks onto one target are one copy
  and cannot produce a diff.
* **The fingerprint decides, not the raw bytes.** File comparison reuses
  :func:`~skill_lens.core.hasher.hash_file`, which normalises ``\\r\\n`` to
  ``\\n``. Two copies that differ only by line endings therefore share a content
  hash and produce no diff -- a raw byte comparison here would contradict the
  hash that ``scan`` and ``why`` report, which is exactly finding F-16.
* **Only the valid set is labelled.** A copy that fails frontmatter validation is
  still a diff participant (a broken copy is usually the one worth looking at)
  but gets no Variant letter and is never the baseline.
"""

from __future__ import annotations

import difflib
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from skill_lens.core.discovery import (
    DiscoveredEntry,
    DiscoveryIndex,
    canonical_key,
    discover,
    entry_scope,
    labels_for_entries,
)
from skill_lens.core.hasher import hash_file, iter_files
from skill_lens.models.diff import DiffChange, DiffCopy, DiffFile, DiffHunk, DiffReport
from skill_lens.models.enums import ParseStatus
from skill_lens.registry.loader import AgentDefinition, load_registry

#: Changed (``+`` / ``-``) lines shown per copy before the diff is truncated.
MAX_CHANGED_LINES_PER_COPY = 400
#: Characters of diff body shown across the whole report before truncating.
MAX_CHARS_PER_REPORT = 20_000
#: Context lines around each change, matching ``difflib.unified_diff``'s default.
CONTEXT_LINES = 3

#: The label :func:`~skill_lens.core.discovery.variant_labels` gives the copy
#: every other copy is compared against.
BASELINE_LABEL = "A"

_NOT_FOUND_NOTE = "No copy of this skill name was found in any search root."
_NO_BASELINE_NOTE = (
    "No copy passed frontmatter validation, so there is no Variant A baseline to diff against."
)


# --- Content collection ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Collected:
    """One file's comparable content.

    ``text`` is ``None`` for a file that is not UTF-8 text, which is what makes
    it "binary" here: such a file is reported as differing, never printed.
    ``fingerprint`` always comes from the hasher, so "same content" means
    exactly what it means everywhere else in the tool.
    """

    text: str | None
    fingerprint: str
    is_binary: bool


def _read_normalized(path: Path) -> str | None:
    """The file as UTF-8 text with ``\\r\\n`` normalised, or ``None`` if binary.

    Mirrors :func:`~skill_lens.core.hasher.hash_file`'s text path, including
    opening with ``newline=""`` so no translation happens before we normalise.
    """
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError):
        return None
    return text.replace("\r\n", "\n")


def _collect(path: Path) -> _Collected | None:
    """Fingerprint and read one file, or ``None`` when it cannot be read."""
    try:
        fingerprint = hash_file(path)
    except OSError:
        return None
    text = _read_normalized(path)
    return _Collected(text=text, fingerprint=fingerprint, is_binary=text is None)


def _copy_files(entry: DiscoveredEntry) -> dict[str, _Collected]:
    """Every comparable file of one copy, keyed by relative POSIX path.

    A directory skill is walked with exactly :func:`hasher.iter_files` -- the
    same sorted, forward-slash relative set, with the same exclusions -- so the
    diff can never see a file the fingerprint ignored. A standalone ``.md`` skill
    is a single file keyed by its own name.
    """
    root = Path(entry.canonical_path or entry.entrypoint_path)
    if not root.is_dir():
        collected = _collect(root)
        return {root.name: collected} if collected is not None else {}
    files: dict[str, _Collected] = {}
    for relative in iter_files(root):
        collected = _collect(root / relative)
        if collected is not None:
            files[relative.as_posix()] = collected
    return files


# --- Hunk construction -----------------------------------------------------


def _lines(text: str) -> list[str]:
    """Split on ``\\n`` only -- the one line separator the hasher normalises.

    ``str.splitlines`` would also break on characters such as ``\\x0b``, which
    the fingerprint treats as ordinary content; using it would let the diff
    disagree with the hash.
    """
    if text.endswith("\n"):
        text = text[:-1]
    return text.split("\n") if text else []


def _range_start(start: int, count: int) -> int:
    """difflib's unified-range rule: an empty range names the line before it."""
    return start + 1 if count else start


def _hunks(old_lines: Sequence[str], new_lines: Sequence[str]) -> tuple[DiffHunk, ...]:
    """Grouped unified-diff hunks with :data:`CONTEXT_LINES` lines of context."""
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    hunks: list[DiffHunk] = []
    for group in matcher.get_grouped_opcodes(CONTEXT_LINES):
        lines: list[str] = []
        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                lines.extend(f" {line}" for line in old_lines[i1:i2])
                continue
            lines.extend(f"-{line}" for line in old_lines[i1:i2])
            lines.extend(f"+{line}" for line in new_lines[j1:j2])
        old_start, old_end = group[0][1], group[-1][2]
        new_start, new_end = group[0][3], group[-1][4]
        hunks.append(
            DiffHunk(
                old_start=_range_start(old_start, old_end - old_start),
                old_count=old_end - old_start,
                new_start=_range_start(new_start, new_end - new_start),
                new_count=new_end - new_start,
                lines=tuple(lines),
            )
        )
    return tuple(hunks)


def _single_sided(content: _Collected, *, removed: bool) -> tuple[DiffHunk, ...]:
    """Hunks for a file that exists on one side only: all added, or all removed."""
    lines = _lines(content.text) if content.text is not None else []
    if not lines:
        return ()
    marker = "-" if removed else "+"
    count = len(lines)
    return (
        DiffHunk(
            old_start=_range_start(0, count if removed else 0),
            old_count=count if removed else 0,
            new_start=_range_start(0, 0 if removed else count),
            new_count=0 if removed else count,
            lines=tuple(f"{marker}{line}" for line in lines),
        ),
    )


def _one_sided(relative: str, content: _Collected, *, removed: bool) -> DiffFile:
    """A file that exists on one side only, shown as all added or all removed."""
    return DiffFile(
        path=relative,
        change=DiffChange.REMOVED if removed else DiffChange.ADDED,
        is_binary=content.is_binary,
        hunks=() if content.is_binary else _single_sided(content, removed=removed),
    )


def _files_between(old: dict[str, _Collected], new: dict[str, _Collected]) -> list[DiffFile]:
    """Every file that differs between the baseline and one other copy.

    Files are matched by relative path, so an added, removed or renamed file
    appears as exactly that. Files whose fingerprints match are the same content
    and are absent from the result.
    """
    files: list[DiffFile] = []
    for relative in sorted(set(old) | set(new)):
        before, after = old.get(relative), new.get(relative)
        if before is None:
            if after is not None:
                files.append(_one_sided(relative, after, removed=False))
            continue
        if after is None:
            files.append(_one_sided(relative, before, removed=True))
            continue
        if before.fingerprint == after.fingerprint:
            continue
        if before.is_binary or after.is_binary:
            files.append(DiffFile(path=relative, change=DiffChange.MODIFIED, is_binary=True))
            continue
        files.append(
            DiffFile(
                path=relative,
                change=DiffChange.MODIFIED,
                hunks=_hunks(_lines(before.text or ""), _lines(after.text or "")),
            )
        )
    return files


# --- Truncation ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Budgeted:
    """One copy's diff after the budgets were applied."""

    files: tuple[DiffFile, ...]
    omitted_lines: int
    omitted_chars: int
    used_chars: int


def _count_changed(hunks: Sequence[DiffHunk]) -> int:
    return sum(1 for hunk in hunks for line in hunk.lines if line[:1] in ("-", "+"))


def _count_chars(hunks: Sequence[DiffHunk]) -> int:
    """Characters of body text, counting the newline each line ends with."""
    return sum(len(line) + 1 for hunk in hunks for line in hunk.lines)


def _recount_start(stored_start: int, original_count: int, kept_count: int) -> int:
    """Adjust a range start when truncation has emptied the range.

    A zero-length range names the line *before* it (see :func:`_range_start`).
    The stored start was computed for the original count, so when truncation
    empties a range that was not empty before, the start must step back one line.
    Otherwise a truncated all-deletions hunk renders as ``+1,0`` where a standard
    diff reader requires ``+0,0``.
    """
    if original_count > 0 and kept_count == 0:
        return stored_start - 1
    return stored_start


def _recount(hunk: DiffHunk, lines: Sequence[str]) -> DiffHunk:
    """Rebuild a hunk's header from the lines that survived truncation.

    Without this a truncated hunk would advertise line counts it no longer
    contains, and the printed diff would not add up. The starts are recomputed
    too: a range that truncation emptied must name the line before it, not the
    line it used to begin at.
    """
    old_count = sum(1 for line in lines if line[:1] in (" ", "-"))
    new_count = sum(1 for line in lines if line[:1] in (" ", "+"))
    return DiffHunk(
        old_start=_recount_start(hunk.old_start, hunk.old_count, old_count),
        old_count=old_count,
        new_start=_recount_start(hunk.new_start, hunk.new_count, new_count),
        new_count=new_count,
        lines=tuple(lines),
    )


def _fit_hunk(hunk: DiffHunk, changed_budget: int, char_budget: int) -> tuple[list[str], int, int]:
    """The longest prefix of ``hunk``'s lines that fits both budgets.

    Returns the lines, how many of them are changes, and how many characters they
    cost. ``changed_budget`` and ``char_budget`` are what is *left*, so a caller
    can fit one hunk at a time without double-counting.
    """
    lines: list[str] = []
    changed = 0
    chars = 0
    for line in hunk.lines:
        line_changed = 1 if line[:1] in ("-", "+") else 0
        cost = len(line) + 1
        if changed + line_changed > changed_budget or chars + cost > char_budget:
            break
        lines.append(line)
        changed += line_changed
        chars += cost
    return lines, changed, chars


def _truncate(files: Sequence[DiffFile], *, changed_budget: int, char_budget: int) -> _Budgeted:
    """Keep as much of one copy's diff as the budgets allow.

    ``changed_budget`` counts changed lines (the per-copy limit);
    ``char_budget`` is what is left of the report-wide character limit. Both are
    applied in a single pass so the result is deterministic: once either budget
    is exhausted nothing more is emitted, and the caller is told how much was
    dropped. Files with no printable body -- a binary file, an added or removed
    binary -- are always kept, because they carry a finding, not content.
    """
    kept: list[DiffFile] = []
    used_changed = 0
    used_chars = 0
    exhausted = False
    for file in files:
        hunks: list[DiffHunk] = []
        if not exhausted:
            for hunk in file.hunks:
                lines, hunk_changed, hunk_chars = _fit_hunk(
                    hunk, changed_budget - used_changed, char_budget - used_chars
                )
                if not hunk_changed:
                    # The budget ran out before this hunk's first change, or cut it
                    # back to context lines only. A hunk with no changed lines is not
                    # a diff, so it is dropped -- and because it is dropped, its
                    # context lines are not charged to the budgets either.
                    exhausted = True
                    break
                hunks.append(_recount(hunk, lines))
                used_changed += hunk_changed
                used_chars += hunk_chars
                if len(lines) < len(hunk.lines):
                    exhausted = True
                    break
        kept.append(replace(file, hunks=tuple(hunks)))
    total_changed = sum(_count_changed(file.hunks) for file in files)
    total_chars = sum(_count_chars(file.hunks) for file in files)
    return _Budgeted(
        files=tuple(kept),
        omitted_lines=total_changed - used_changed,
        omitted_chars=total_chars - used_chars,
        used_chars=used_chars,
    )


# --- Public entry point ----------------------------------------------------


def _is_valid(entry: DiscoveredEntry) -> bool:
    return entry.parse_status == ParseStatus.VALID.value


def _is_readable(entry: DiscoveredEntry) -> bool:
    """A copy can be compared when the hasher produced a fingerprint for it.

    Dangling symlinks, cycles and permission-denied roots have no content, so
    they are listed with no diff rather than silently dropped.
    """
    return entry.content_hash is not None


def _copy(
    entry: DiscoveredEntry,
    labels: dict[str, str],
    *,
    is_baseline: bool = False,
    files: tuple[DiffFile, ...] = (),
    truncated: bool = False,
    omitted_lines: int = 0,
) -> DiffCopy:
    """Describe one copy of the skill as it takes part in the diff."""
    key = canonical_key(entry)
    return DiffCopy(
        path=key,
        scope=entry_scope(entry),
        parse_status=entry.parse_status,
        is_valid=_is_valid(entry),
        is_readable=_is_readable(entry),
        is_baseline=is_baseline,
        variant_label=labels.get(key),
        content_hash=entry.content_hash,
        error=entry.error_code,
        files=files,
        truncated=truncated,
        omitted_lines=omitted_lines,
    )


def build_diff_report(
    name: str,
    cwd: Path,
    home: Path,
    *,
    index: DiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None,
) -> DiffReport:
    """Diff every copy of ``name`` against the Variant A baseline.

    Arguments mirror :func:`~skill_lens.core.resolver.resolve_skill` -- the
    name-based lookup takes the working directory before the home directory.
    The two optional arguments are keyword-only so a caller cannot silently swap
    a working directory for a home directory.

    A name that exists nowhere yields ``found=False`` and exit code ``0``: like
    ``why``, "nothing found" is a fact, not an error (finding F-10).
    """
    agents = registry if registry is not None else load_registry()
    discovery = index if index is not None else discover(home, cwd, agents)

    entries = [entry for entry in discovery.entries if entry.name == name]
    if not entries:
        return DiffReport(
            skill_name=name,
            home=str(home),
            cwd=str(cwd),
            found=False,
            notes=(_NOT_FOUND_NOTE,),
        )

    labels = labels_for_entries(entries)
    baseline_index = next(
        (
            position
            for position, entry in enumerate(entries)
            if labels.get(canonical_key(entry)) == BASELINE_LABEL
        ),
        None,
    )
    baseline = entries[baseline_index] if baseline_index is not None else None

    # Only meaningful with more than one copy: a single copy has nothing to be
    # compared against, so "no differences" is already the honest answer.
    notes: tuple[str, ...] = (_NO_BASELINE_NOTE,) if baseline is None and len(entries) > 1 else ()

    baseline_files: dict[str, _Collected] | None = None
    copies: list[DiffCopy] = []
    used_chars = 0
    omitted_chars = 0
    truncated = False

    for position, entry in enumerate(entries):
        is_baseline = position == baseline_index
        if not (_is_readable(entry) and not is_baseline and baseline is not None):
            copies.append(_copy(entry, labels, is_baseline=is_baseline))
            continue

        if entry.content_hash == baseline.content_hash:
            # Same bytes, so no diff -- this is the line-ending rule.
            copies.append(_copy(entry, labels, is_baseline=False))
            continue

        if baseline_files is None:
            baseline_files = _copy_files(baseline)
        budgeted = _truncate(
            _files_between(baseline_files, _copy_files(entry)),
            changed_budget=MAX_CHANGED_LINES_PER_COPY,
            char_budget=max(MAX_CHARS_PER_REPORT - used_chars, 0),
        )
        copy_truncated = budgeted.omitted_lines > 0 or budgeted.omitted_chars > 0
        truncated = truncated or copy_truncated
        used_chars += budgeted.used_chars
        omitted_chars += budgeted.omitted_chars
        copies.append(
            _copy(
                entry,
                labels,
                is_baseline=False,
                files=budgeted.files,
                truncated=copy_truncated,
                omitted_lines=budgeted.omitted_lines,
            )
        )

    # The baseline leads the list: it is the reference every other copy is read
    # against, and each diff below it is relative to it.
    ordered = (
        [copies[baseline_index], *(c for i, c in enumerate(copies) if i != baseline_index)]
        if baseline_index is not None
        else copies
    )
    return DiffReport(
        skill_name=name,
        home=str(home),
        cwd=str(cwd),
        found=True,
        baseline_path=canonical_key(baseline) if baseline is not None else None,
        copies=tuple(ordered),
        truncated=truncated,
        omitted_chars=omitted_chars,
        notes=notes,
    )


__all__ = [
    "BASELINE_LABEL",
    "CONTEXT_LINES",
    "MAX_CHANGED_LINES_PER_COPY",
    "MAX_CHARS_PER_REPORT",
    "build_diff_report",
]
