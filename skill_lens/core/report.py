"""Composition layer for ``skill-lens report`` and the TUI export.

This module stamps reproducible metadata and calls the existing builders. It
computes no findings, relations, health or collision policy: a report is a
composition, not a fourth engine. One discovery pass feeds every section when a
caller does not already hold an index (``run_report`` walks once and passes the
same index to all three builders).
"""

from __future__ import annotations

import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from skill_lens import __version__
from skill_lens.core.compare import build_compare_report, validate_compare_agents
from skill_lens.core.discovery import DiscoveryIndex, discover
from skill_lens.core.doctor import build_doctor_report
from skill_lens.core.scanner import build_scan_report
from skill_lens.core.system import live_discovery
from skill_lens.models.agents import AgentSummary, agents_payload
from skill_lens.models.compare import CompareReport
from skill_lens.models.doctor import DoctorReport
from skill_lens.models.report import ReportMeta, ReportModel
from skill_lens.registry.loader import AgentDefinition, load_registry


def utc_timestamp(value: datetime) -> str:
    """Return the pinned UTC spelling used by the CLI and the TUI export.

    A naive datetime is rejected rather than guessed: assuming a timezone
    would make the same run render differently on two machines. An aware value
    is converted to UTC, and ``isoformat(timespec="seconds")`` gives the stable
    ``2026-11-19T14:20:00+00:00`` form.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    return value.astimezone(UTC).isoformat(timespec="seconds")


def assemble_report(
    scan_payload: dict[str, Any],
    doctor: DoctorReport,
    agents: tuple[AgentSummary, ...],
    compare: CompareReport | None,
    meta: ReportMeta,
) -> ReportModel:
    """Build one report document from already-computed payloads.

    The single shared constructor: the CLI and the TUI export both call it, so
    their documents cannot drift. It performs no discovery and no reads.
    """
    return ReportModel(meta=meta, agents=agents, scan=scan_payload, doctor=doctor, compare=compare)


def _meta(
    generated_at: datetime | None,
    platform_text: str | None,
) -> ReportMeta:
    stamp = generated_at if generated_at is not None else datetime.now(UTC)
    return ReportMeta(
        generated_at=utc_timestamp(stamp),
        skill_lens_version=__version__,
        platform=platform_text if platform_text is not None else platform.platform(),
    )


def build_report(
    home: Path,
    cwd: Path,
    *,
    compare_agents: tuple[str, str] | None = None,
    index: DiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None,
    generated_at: datetime | None = None,
    platform_text: str | None = None,
) -> ReportModel:
    """Compose a report from one discovery pass.

    A requested pair is validated before any walk. When ``index`` is supplied
    it is passed to every builder (``index=``) so no builder silently re-crawls;
    otherwise exactly one discovery call happens here.
    """
    agents = registry if registry is not None else load_registry()
    if compare_agents is not None:
        validate_compare_agents(compare_agents[0], compare_agents[1], agents)

    discovery = index if index is not None else discover(home, cwd, agents)
    scan = build_scan_report(home, cwd, index=discovery, registry=agents)
    doctor = build_doctor_report(home, cwd, index=discovery, registry=agents)
    compare = (
        build_compare_report(
            compare_agents[0],
            compare_agents[1],
            home,
            cwd,
            index=discovery,
            registry=agents,
        )
        if compare_agents is not None
        else None
    )
    return assemble_report(
        scan_payload=scan.to_dict(),
        doctor=doctor,
        agents=tuple(agents_payload(agents.values())),
        compare=compare,
        meta=_meta(generated_at, platform_text),
    )


def run_report(
    cwd: Path | None = None,
    *,
    compare_agents: tuple[str, str] | None = None,
    registry: dict[str, AgentDefinition] | None = None,
    generated_at: datetime | None = None,
    platform_text: str | None = None,
) -> ReportModel:
    """Live entry point used by the CLI: validate, discover once, then compose."""
    agents = registry if registry is not None else load_registry()
    if compare_agents is not None:
        validate_compare_agents(compare_agents[0], compare_agents[1], agents)
    discovery = live_discovery(cwd, agents)
    return build_report(
        Path(discovery.home),
        Path(discovery.cwd),
        compare_agents=compare_agents,
        index=discovery,
        registry=agents,
        generated_at=generated_at,
        platform_text=platform_text,
    )


__all__ = [
    "assemble_report",
    "build_report",
    "run_report",
    "utc_timestamp",
]
