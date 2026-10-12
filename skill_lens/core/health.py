"""Shared health condition classification for discovery, scan, and doctor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from skill_lens.models.enums import ParseStatus, Severity
from skill_lens.models.parsing import (
    ERR_DANGLING_SYMLINK,
    ERR_SYMLINK_CYCLE,
    ERR_UNDECODABLE_TEXT,
    CanonicalStatus,
)

if TYPE_CHECKING:
    from skill_lens.core.discovery import DiscoveredEntry


@dataclass(frozen=True, slots=True)
class HealthCondition:
    """Classified health status of a discovered skill entry."""

    code: str = "ok"
    severity: Severity | None = None
    is_complete: bool = True
    reason: str | None = None
    clause: str = ""

    @property
    def is_healthy(self) -> bool:
        return self.severity is None


def classify_entry_health(entry: DiscoveredEntry) -> HealthCondition:
    """Classify the health condition of a single discovered entry."""
    # 1. Canonical / symlink failures
    if entry.canonical.status is CanonicalStatus.CYCLE:
        return HealthCondition(
            code="symlink_cycle",
            severity=Severity.ERROR,
            is_complete=False,
            reason=ERR_SYMLINK_CYCLE,
            clause="is part of a symlink loop",
        )
    if entry.canonical.status is CanonicalStatus.BROKEN:
        return HealthCondition(
            code="dangling_symlink",
            severity=Severity.ERROR,
            is_complete=False,
            reason=ERR_DANGLING_SYMLINK,
            clause="links to a target that does not exist",
        )
    if entry.canonical.status is CanonicalStatus.UNREADABLE:
        return HealthCondition(
            code="unreadable_skill",
            severity=Severity.ERROR,
            is_complete=False,
            reason="denied",
            clause="exists but the OS refuses to open it",
        )

    # 2. Undecodable UTF-8
    if entry.parse is not None and ERR_UNDECODABLE_TEXT in entry.parse.errors:
        return HealthCondition(
            code="undecodable_skill",
            severity=Severity.ERROR,
            is_complete=False,
            reason="undecodable",
            clause="contains invalid UTF-8 and cannot be read as text",
        )

    # 3. Traversal / asset reading failures
    if not entry.traversal_complete:
        reason = entry.traversal_error or "denied"
        if reason == "denied":
            clause = "exists but the OS refuses to open it"
        elif reason == "disappeared":
            clause = "or one of its files disappeared while scanning"
        else:
            clause = "or one of its files cannot be read (I/O error)"
        return HealthCondition(
            code="unreadable_skill",
            severity=Severity.ERROR,
            is_complete=False,
            reason=reason,
            clause=clause,
        )

    # 4. Unreadable parse
    if entry.parse is not None and entry.parse.status is ParseStatus.UNREADABLE:
        return HealthCondition(
            code="unreadable_skill",
            severity=Severity.ERROR,
            is_complete=False,
            reason="denied",
            clause="exists but the OS refuses to open it",
        )

    # 5. Parse frontmatter issues
    if entry.parse is not None and entry.parse.status is ParseStatus.MALFORMED_YAML:
        return HealthCondition(
            code="malformed_frontmatter",
            severity=Severity.ERROR,
            is_complete=True,
            reason="malformed_yaml",
            clause="has no readable YAML frontmatter",
        )
    if entry.parse is not None and entry.parse.status is ParseStatus.MISSING_DESCRIPTION:
        return HealthCondition(
            code="malformed_frontmatter",
            severity=Severity.ERROR,
            is_complete=True,
            reason="missing_description",
            clause="is missing the required 'description' field",
        )

    if entry.parse is None:
        return HealthCondition(
            code="invalid",
            severity=Severity.ERROR,
            is_complete=False,
            reason="missing_document",
            clause="has no skill document (SKILL.md)",
        )

    return HealthCondition(
        code="ok",
        severity=None,
        is_complete=True,
        reason=None,
        clause="",
    )
