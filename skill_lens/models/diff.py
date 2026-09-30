"""Data contracts for ``skill-lens diff`` (Phase 3).

A diff is built from a :class:`~skill_lens.core.discovery.DiscoveryIndex`, whose
entries are already deduplicated by canonical target. A "copy" here is therefore
one *canonical* skill on disk: a symlink farm is one copy reached through N
entrypoints, and two symlinks onto the same target can never produce a diff.

These dataclasses are the contract. The Rich renderer is a layer on top of them
and never recomputes anything (AGENTS.md rule 4).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from skill_lens.models.enums import Scope


class DiffChange(StrEnum):
    """How one file differs between the baseline copy and another copy."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


@dataclass(frozen=True, slots=True)
class DiffHunk:
    """One unified-diff hunk.

    ``old_start`` / ``old_count`` / ``new_start`` / ``new_count`` are stored
    exactly as a unified header spells them (``@@ -old_start,old_count
    +new_start,new_count @@``), including the standard convention that a
    zero-length range names the line *before* it.

    ``lines`` holds the body lines with their leading marker: ``" "`` for
    context, ``"-"`` for a line only the baseline has, ``"+"`` for a line only
    the other copy has. Storing the marker means the renderer can print the
    hunk without recomputing the diff.
    """

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "old_start": self.old_start,
            "old_count": self.old_count,
            "new_start": self.new_start,
            "new_count": self.new_count,
            "lines": list(self.lines),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DiffHunk:
        return cls(
            old_start=int(data["old_start"]),
            old_count=int(data["old_count"]),
            new_start=int(data["new_start"]),
            new_count=int(data["new_count"]),
            lines=tuple(data.get("lines", ())),
        )


@dataclass(frozen=True, slots=True)
class DiffFile:
    """One file that differs between the baseline copy and another copy.

    Only files that genuinely differ appear here; an unchanged file is absent
    rather than listed with an empty hunk list. ``is_binary`` marks a file whose
    content is never printed -- the specification reports it as differing and
    stops there. A file that exists on one side only is ``added`` or ``removed``,
    which is also how a rename shows up, because files are matched by relative
    path.
    """

    path: str
    change: DiffChange
    is_binary: bool = False
    hunks: tuple[DiffHunk, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "change": self.change.value,
            "is_binary": self.is_binary,
            "hunks": [hunk.to_dict() for hunk in self.hunks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DiffFile:
        return cls(
            path=data["path"],
            change=DiffChange(data["change"]),
            is_binary=bool(data.get("is_binary", False)),
            hunks=tuple(DiffHunk.from_dict(hunk) for hunk in data.get("hunks", ())),
        )


@dataclass(frozen=True, slots=True)
class DiffCopy:
    """One copy of a skill name, as it takes part in a diff.

    ``is_readable`` separates a copy that has content to compare from one that
    cannot be read at all -- a dangling symlink, a symlink cycle, a
    permission-denied root. An unreadable copy is still listed (it is a real
    finding) but carries the machine-checkable ``error`` code instead of files.

    ``variant_label`` is ``None`` for a copy that failed frontmatter validation:
    only the valid set receives a Variant letter, so the letters here always
    agree with ``scan`` and ``why``. A copy whose bytes match the baseline has an
    empty ``files`` tuple -- identical content is not a difference.

    ``truncated`` / ``omitted_lines`` describe this copy alone: how much of its
    diff was dropped to stay inside the per-copy changed-line budget.
    """

    path: str
    scope: Scope
    parse_status: str
    is_valid: bool
    is_readable: bool
    is_baseline: bool = False
    variant_label: str | None = None
    content_hash: str | None = None
    error: str | None = None
    files: tuple[DiffFile, ...] = ()
    truncated: bool = False
    omitted_lines: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "scope": self.scope.value,
            "parse_status": self.parse_status,
            "is_valid": self.is_valid,
            "is_readable": self.is_readable,
            "is_baseline": self.is_baseline,
            "variant_label": self.variant_label,
            "content_hash": self.content_hash,
            "error": self.error,
            "files": [file.to_dict() for file in self.files],
            "truncated": self.truncated,
            "omitted_lines": self.omitted_lines,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DiffCopy:
        return cls(
            path=data["path"],
            scope=Scope(data["scope"]),
            parse_status=data["parse_status"],
            is_valid=bool(data["is_valid"]),
            is_readable=bool(data["is_readable"]),
            is_baseline=bool(data.get("is_baseline", False)),
            variant_label=data.get("variant_label"),
            content_hash=data.get("content_hash"),
            error=data.get("error"),
            files=tuple(DiffFile.from_dict(file) for file in data.get("files", ())),
            truncated=bool(data.get("truncated", False)),
            omitted_lines=int(data.get("omitted_lines", 0)),
        )


@dataclass(frozen=True, slots=True)
class DiffReport:
    """The complete answer for ``skill-lens diff <name>``.

    ``found=False`` means the name exists nowhere on disk. That is a fact, not an
    error: like ``why``, ``diff`` reports it and exits ``0`` (finding F-10).

    ``baseline_path`` is the copy every other copy is compared against -- the one
    ``discovery.variant_labels`` calls Variant A. It is ``None`` when no copy
    passed validation, because an invalid copy is never the baseline; ``notes``
    then says so rather than inventing a reference.

    ``omitted_chars`` counts the characters of diff body that were dropped to
    stay inside the report-wide character budget, so the terminal can state how
    much was left out.
    """

    skill_name: str
    home: str
    cwd: str
    found: bool
    baseline_path: str | None = None
    copies: tuple[DiffCopy, ...] = ()
    truncated: bool = False
    omitted_chars: int = 0
    notes: tuple[str, ...] = ()

    @property
    def has_differences(self) -> bool:
        """True when any copy differs from the baseline.

        Derived, never serialized: it is a view of ``copies``, not a fact the
        computation has to keep in sync.
        """
        return any(copy.files for copy in self.copies)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "home": self.home,
            "cwd": self.cwd,
            "found": self.found,
            "baseline_path": self.baseline_path,
            "copies": [copy.to_dict() for copy in self.copies],
            "truncated": self.truncated,
            "omitted_chars": self.omitted_chars,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DiffReport:
        return cls(
            skill_name=data["skill_name"],
            home=data["home"],
            cwd=data["cwd"],
            found=bool(data["found"]),
            baseline_path=data.get("baseline_path"),
            copies=tuple(DiffCopy.from_dict(copy) for copy in data.get("copies", ())),
            truncated=bool(data.get("truncated", False)),
            omitted_chars=int(data.get("omitted_chars", 0)),
            notes=tuple(data.get("notes", ())),
        )
