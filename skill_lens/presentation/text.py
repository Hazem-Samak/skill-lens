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


# The summary keeps the CLI's labels so both presentation layers read alike.
COPIES_LABEL = "Copies:"
BASELINE_LABEL = "Baseline:"
NOTE_LABEL = "Note:"
TRUNCATED_LABEL = "Truncated:"

#: Marks a file whose content differs but must never be printed.
BINARY_MARKER = "binary"

#: The Baseline value when no copy passed validation.
BASELINE_ABSENT_TEXT = "none (no copy passed validation)"

# Bodies printed under a copy heading when that copy has no printable files.
BASELINE_REFERENCE_BODY = "Reference copy; every diff below is against it."
IDENTICAL_BODY = "No differences from the baseline."
UNCOMPARED_BODY = "Not compared: there is no baseline."

# Notices printed instead of file content, or instead of omitted content.
BINARY_FILE_NOTICE = "Binary content differs and is never printed."
HUNKLESS_TEXT_NOTICE = "No printable content."

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


def not_found_message(report: DiffReport) -> str:
    """The plain explanation for a name that exists nowhere on disk."""
    return f"No copies of '{report.skill_name}' were found in any search root."


def baseline_text(baseline: DiffCopy | None, *, display_path: str | None = None) -> str:
    """The Baseline value: the reference copy, or the reason there is none.

    ``display_path`` is an already-displayed path supplied by the caller (the CLI
    relativises it, the TUI uses the captured one); nothing here touches the disk.
    """
    if baseline is None:
        return BASELINE_ABSENT_TEXT
    path = baseline.path if display_path is None else display_path
    variant = f" (Variant {baseline.variant_label})" if baseline.variant_label else ""
    return f"{path}{variant}"


def copy_body(copy: DiffCopy, *, baseline_exists: bool) -> str | None:
    """The plain line printed under one copy heading, or ``None`` when files follow.

    The three "nothing to show" cases stay distinct on purpose: a reference copy
    is not identical to anything, a copy with no baseline was never compared, and
    an unreadable copy needs its reason named.
    """
    if copy.is_baseline:
        return BASELINE_REFERENCE_BODY
    if not copy.is_readable:
        return f"No content to compare ({unreadable_reason(copy)})."
    if copy.files:
        return None
    if baseline_exists:
        return IDENTICAL_BODY
    return UNCOMPARED_BODY


def file_notice(file: DiffFile) -> str | None:
    """The plain notice shown instead of hunks, or ``None`` when hunks are printable."""
    if file.is_binary:
        return BINARY_FILE_NOTICE
    if not file.hunks:
        return HUNKLESS_TEXT_NOTICE
    return None


def copy_truncation_notice(copy: DiffCopy) -> NoticeParts | None:
    """What this copy's own truncation dropped, or ``None`` when nothing was.

    ``truncated`` is true when either budget bit, but ``omitted_lines`` counts
    changed lines only -- quoting a line count for a character-only cut would read
    as "0 changed lines omitted", which says nothing happened when something did.
    """
    if copy.omitted_lines:
        return NoticeParts(
            label=TRUNCATED_LABEL,
            style="yellow",
            body=f" {copy.omitted_lines} changed lines omitted.",
        )
    if copy.truncated:
        return NoticeParts(
            label=TRUNCATED_LABEL,
            style="yellow",
            body=" part of this diff was omitted; see the report total below.",
        )
    return None


def report_truncation_notice(report: DiffReport) -> NoticeParts | None:
    """How much report-wide diff body was dropped, or ``None`` when nothing was."""
    if not report.truncated:
        return None
    return NoticeParts(
        label=TRUNCATED_LABEL,
        style="yellow",
        body=(
            f" {report.omitted_chars} characters of diff body were omitted to keep this"
            " report readable."
        ),
    )


__all__ = [
    "BASELINE_ABSENT_TEXT",
    "BASELINE_LABEL",
    "BASELINE_REFERENCE_BODY",
    "BINARY_FILE_NOTICE",
    "BINARY_MARKER",
    "COPIES_LABEL",
    "HUNKLESS_TEXT_NOTICE",
    "IDENTICAL_BODY",
    "NOTE_LABEL",
    "TRUNCATED_LABEL",
    "UNCOMPARED_BODY",
    "HeadingParts",
    "NoticeParts",
    "baseline_text",
    "copy_body",
    "copy_heading",
    "copy_truncation_notice",
    "file_notice",
    "needs_listing",
    "no_differences_message",
    "not_found_message",
    "range_text",
    "report_truncation_notice",
    "unified_text",
    "unreadable_reason",
]
