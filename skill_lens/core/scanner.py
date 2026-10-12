"""Inventory a discovery pass into a stable, JSON-serializable catalog.

``scan`` is the inventory view: it groups a symlink farm into one canonical
library with N entrypoints, separates user / project / system / plugin scopes,
and reports which agents can reach each skill.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skill_lens.core.discovery import (
    SCOPE_SPECIFICITY,
    DiscoveredEntry,
    DiscoveryIndex,
    discover,
    entry_scope,
    labels_for_entries,
)
from skill_lens.core.health import HealthCondition, classify_entry_health
from skill_lens.models.enums import Scope, Severity
from skill_lens.registry.loader import AgentDefinition, load_registry

_SCOPE_ORDER = SCOPE_SPECIFICITY


@dataclass(frozen=True, slots=True)
class ScanEntry:
    """One row of the scan inventory."""

    name: str
    scope: Scope
    canonical_path: str
    parse_status: str
    agents: tuple[str, ...]
    entrypoint_count: int
    is_symlink: bool
    content_hash: str | None
    description: str | None = None
    variant_label: str | None = None
    traversal_complete: bool = True
    error_reason: str | None = None
    condition: HealthCondition = field(
        default_factory=lambda: HealthCondition("ok", None, True, None, "")
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "scope": self.scope.value,
            "canonical_path": self.canonical_path,
            "parse_status": self.parse_status,
            "agents": list(self.agents),
            "entrypoint_count": self.entrypoint_count,
            "is_symlink": self.is_symlink,
            "content_hash": self.content_hash,
            "description": self.description,
            "variant_label": self.variant_label,
            "traversal_complete": self.traversal_complete,
            "error_reason": self.error_reason,
            "health_status": self.condition.code,
        }


@dataclass(frozen=True, slots=True)
class ScanSummary:
    """Aggregate counts plus the per-scope skill totals."""

    detected_agents: tuple[str, ...]
    user_skills: int
    project_skills: int
    system_skills: int
    plugin_skills: int
    #: Size of the **canonical library** -- the shared, user-scoped skills the
    #: symlink farms point at. This is the user-scope count only: plugin and
    #: system skills are indexed separately and must never inflate it (spec
    #: section 4). The grand total is :attr:`total_skills`.
    canonical_skill_count: int
    symlink_entrypoints: int

    @property
    def total_skills(self) -> int:
        return self.user_skills + self.project_skills + self.system_skills + self.plugin_skills

    def to_dict(self) -> dict[str, Any]:
        return {
            "detected_agents": list(self.detected_agents),
            "user_skills": self.user_skills,
            "project_skills": self.project_skills,
            "system_skills": self.system_skills,
            "plugin_skills": self.plugin_skills,
            "canonical_skill_count": self.canonical_skill_count,
            "symlink_entrypoints": self.symlink_entrypoints,
            "total_skills": self.total_skills,
        }


@dataclass(frozen=True, slots=True)
class ScanReport:
    """The complete result of a scan."""

    home: str
    cwd: str
    summary: ScanSummary
    skills: tuple[ScanEntry, ...]
    unreadable: tuple[dict[str, str], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "home": self.home,
            "cwd": self.cwd,
            "summary": self.summary.to_dict(),
            "skills": [skill.to_dict() for skill in self.skills],
            "unreadable": list(self.unreadable),
        }


def scan_severities(report: ScanReport) -> tuple[Severity, ...]:
    """Every health problem visible in a scan report, as severities.

    Pure: takes a finished report, returns the severities. This is what lets
    ``scan --fail-on`` gate a pipeline without ``cli.py`` re-deriving the rules.

    A skill that parsed cleanly contributes nothing. An unreadable *root* is a
    warning even though no entry can be produced for it, because the absence of
    skills in a blocked directory is itself the finding.
    """
    severities: list[Severity] = []
    for skill in report.skills:
        if skill.condition.severity is not None:
            severities.append(skill.condition.severity)
    severities.extend(Severity.WARNING for _ in report.unreadable)
    return tuple(severities)


def _agents_of(entry: DiscoveredEntry) -> tuple[str, ...]:
    return tuple(sorted({hit.agent_id for hit in entry.hits}))


def _symlink_entrypoint_count(entry: DiscoveredEntry) -> int:
    """Count the entrypoint paths that are genuinely symlinks on disk.

    Counting (agent, root) hits instead would inflate the number, because a
    single real path is reached by several agent roots.
    """
    return sum(
        1 for path in entry.entrypoint_paths or (entry.entrypoint_path,) if Path(path).is_symlink()
    )


def _variant_labels(indexed: list[tuple[DiscoveredEntry, Scope]]) -> dict[str, str]:
    """Label same-named copies as Variant A / B, using the shared rule.

    See :func:`skill_lens.core.discovery.labels_for_entries` -- ``scan``,
    ``why`` and ``diff`` must agree, so a copy is never "Variant A" in one
    command and "B" in another.
    """
    return labels_for_entries(entry for entry, _scope in indexed)


def build_scan_report(
    home: Path,
    cwd: Path,
    index: DiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None,
) -> ScanReport:
    """Turn a discovery pass into a scan report."""
    agents = registry if registry is not None else load_registry()
    discovery = index if index is not None else discover(home, cwd, agents)

    indexed = [(entry, entry_scope(entry)) for entry in discovery.entries]
    labels = _variant_labels(indexed)

    skills: list[ScanEntry] = []
    for entry, scope in indexed:
        canonical = entry.canonical_path or entry.entrypoint_path
        cond = classify_entry_health(entry)
        skills.append(
            ScanEntry(
                name=entry.name,
                scope=scope,
                canonical_path=canonical,
                parse_status=entry.parse_status,
                agents=_agents_of(entry),
                entrypoint_count=len(entry.entrypoint_paths) or len(entry.hits),
                is_symlink=entry.is_symlink,
                content_hash=entry.content_hash,
                description=entry.parse.description if entry.parse else None,
                variant_label=labels.get(canonical),
                traversal_complete=entry.traversal_complete,
                error_reason=(
                    entry.traversal_error or (cond.reason if not cond.is_healthy else None)
                ),
                condition=cond,
            )
        )
    skills.sort(key=lambda s: (_SCOPE_ORDER.get(s.scope, 9), s.name))

    detected = sorted({hit.agent_id for entry in discovery.entries for hit in entry.hits})
    counts = {scope: 0 for scope in Scope}
    for skill in skills:
        counts[skill.scope] += 1

    summary = ScanSummary(
        detected_agents=tuple(detected),
        user_skills=counts[Scope.USER],
        project_skills=counts[Scope.PROJECT],
        system_skills=counts[Scope.SYSTEM],
        plugin_skills=counts[Scope.PLUGIN],
        canonical_skill_count=counts[Scope.USER],
        symlink_entrypoints=sum(_symlink_entrypoint_count(entry) for entry in discovery.entries),
    )
    unreadable = tuple(
        {
            "agent": root.agent_id,
            "root": root.root_id,
            "path": root.path,
            "detail": root.detail,
        }
        for root in discovery.unreadable_roots
    )
    return ScanReport(
        home=str(home),
        cwd=str(cwd),
        summary=summary,
        skills=tuple(skills),
        unreadable=unreadable,
    )
