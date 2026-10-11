"""Plain text helpers and structured parts for diff presentation.

These helpers are pure and format model objects into plain text dataclasses
without Rich markup, escaping, or filesystem access.
"""

from __future__ import annotations

from dataclasses import dataclass

from skill_lens.models.diff import DiffCopy, DiffFile, DiffReport
from skill_lens.models.parsing import (
    ERR_DANGLING_SYMLINK,
    ERR_PERMISSION_DENIED,
    ERR_SYMLINK_CYCLE,
)


@dataclass(frozen=True, slots=True)
class HeadingParts:
    """Structured fields for one copy's diff heading line."""

    mark: str
    style: str
    path: str
    variant: str
    scope: str
    parse_status: str
    status: str


@dataclass(frozen=True, slots=True)
class NoticeParts:
    """Structured fields for a diff notice banner."""

    label: str
    style: str
    body: str


_UNREADABLE_REASON: dict[str, str] = {
    ERR_SYMLINK_CYCLE: "symlink cycle",
    ERR_DANGLING_SYMLINK: "dangling symlink",
    ERR_PERMISSION_DENIED: "permission denied",
}


def range_text(start: int, count: int) -> str:
    """Format one side of a unified hunk header the way ``difflib`` does."""
    return str(start) if count == 1 else f"{start},{count}"


def unified_text(file: DiffFile) -> str:
    """The unified diff body for one file, ready for Rich's ``diff`` lexer."""
    lines = [f"--- {file.path}", f"+++ {file.path}"]
    for hunk in file.hunks:
        old = range_text(hunk.old_start, hunk.old_count)
        new = range_text(hunk.new_start, hunk.new_count)
        lines.append(f"@@ -{old} +{new} @@")
        lines.extend(hunk.lines)
    return "\n".join(lines)


def unreadable_reason(copy: DiffCopy) -> str:
    """Return the human-readable explanation for an unreadable copy."""
    return _UNREADABLE_REASON.get(copy.error or "", "no readable content")


def copy_heading(copy: DiffCopy, *, baseline_exists: bool, display_path: str) -> HeadingParts:
    """Return plain heading parts for one copy in a diff report."""
    if copy.is_baseline:
        mark, style, status = "=", "bold cyan", "baseline (no diff shown)"
    elif not copy.is_readable:
        mark, style, status = "x", "bold red", f"cannot be read: {unreadable_reason(copy)}"
    elif copy.files:
        mark, style, status = "*", "bold yellow", f"{len(copy.files)} file(s) differ"
    elif not baseline_exists:
        # Nothing was compared, so claiming identity would be a lie.
        mark, style, status = "-", "dim", "not compared: no baseline"
    else:
        mark, style, status = "=", "dim", "identical to the baseline"

    variant = f" [Variant {copy.variant_label}]" if copy.variant_label else ""
    return HeadingParts(
        mark=mark,
        style=style,
        path=display_path,
        variant=variant,
        scope=copy.scope.value,
        parse_status=copy.parse_status,
        status=status,
    )


def no_differences_message(report: DiffReport) -> NoticeParts:
    """The headline notice when nothing differs -- which is not the same as 'identical'.

    With no baseline nothing was compared at all, so the honest headline is that
    no comparison happened, not that the copies match.
    """
    if report.baseline_path is None:
        return NoticeParts(
            label="Not compared:",
            style="yellow",
            body=" no copy could serve as a baseline.",
        )
    readable = [copy for copy in report.copies if copy.is_readable]
    if len(report.copies) == 1:
        return NoticeParts(
            label="No differences:",
            style="green",
            body=" only one copy exists, so there is nothing to compare.",
        )
    if len(readable) < 2:
        return NoticeParts(
            label="No differences:",
            style="green",
            body=" fewer than two copies could be read.",
        )
    return NoticeParts(
        label="No differences:",
        style="green",
        body=f" all {len(readable)} readable copies are identical.",
    )


def needs_listing(report: DiffReport) -> bool:
    """True when the copies must be listed even though nothing differs.

    A second copy, or a copy that could not be read at all, is itself a finding:
    printing only "no differences" would hide it.
    """
    return len(report.copies) > 1 or any(not copy.is_readable for copy in report.copies)


__all__ = [
    "HeadingParts",
    "NoticeParts",
    "copy_heading",
    "needs_listing",
    "no_differences_message",
    "range_text",
    "unified_text",
    "unreadable_reason",
]
