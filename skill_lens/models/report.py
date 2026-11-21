"""Data contract for the combined ``skill-lens report`` document.

The report is composition, not a fourth engine: every nested payload is the
canonical output of the command that already produces it. ``scan`` is stored
verbatim as the ``ScanReport.to_dict()`` dict because ``ScanReport`` has no
``from_dict`` and its health condition is not fully serialized; rebuilding a
``ScanReport`` from the payload would fabricate unserialized fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from skill_lens.models.agents import AgentSummary
from skill_lens.models.compare import CompareReport
from skill_lens.models.doctor import DoctorReport


@dataclass(frozen=True, slots=True)
class ReportMeta:
    """Reproducible identity of one report run."""

    generated_at: str
    skill_lens_version: str
    platform: str

    def to_dict(self) -> dict[str, str]:
        return {
            "generated_at": self.generated_at,
            "skill_lens_version": self.skill_lens_version,
            "platform": self.platform,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReportMeta:
        return cls(
            generated_at=data["generated_at"],
            skill_lens_version=data["skill_lens_version"],
            platform=data["platform"],
        )


@dataclass(frozen=True, slots=True)
class ReportModel:
    """The complete exportable diagnostic document.

    ``compare`` is ``None`` when no pair was requested; ``to_dict`` always
    emits the key so a scripted consumer can distinguish "no pair" from a
    missing field. No report-level derived counts are serialized: a consumer
    recomputes ``counts_by_relation``/``counts_by_severity`` from the nested
    payloads exactly as the individual commands already require.
    """

    meta: ReportMeta
    agents: tuple[AgentSummary, ...]
    scan: dict[str, Any]
    doctor: DoctorReport
    compare: CompareReport | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta": self.meta.to_dict(),
            "agents": list(self.agents),
            "scan": self.scan,
            "doctor": self.doctor.to_dict(),
            "compare": self.compare.to_dict() if self.compare is not None else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReportModel:
        compare = data.get("compare")
        return cls(
            meta=ReportMeta.from_dict(data["meta"]),
            agents=tuple(cast(AgentSummary, agent) for agent in data["agents"]),
            scan=data["scan"],
            doctor=DoctorReport.from_dict(data["doctor"]),
            compare=CompareReport.from_dict(compare) if compare is not None else None,
        )


__all__ = ["ReportMeta", "ReportModel"]
