"""Diagnostics model emitted by ``skill-lens doctor``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skill_lens.models.enums import Evidence, Severity


@dataclass(frozen=True, slots=True)
class DoctorFinding:
    """A single hygiene or ecosystem-health finding.

    Findings are informational only: Skill Lens never repairs anything.
    """

    code: str
    severity: Severity
    message: str
    rule_id: str
    evidence: Evidence
    path: str | None = None
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "rule_id": self.rule_id,
            "evidence": self.evidence.value,
            "path": self.path,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DoctorFinding:
        return cls(
            code=data["code"],
            severity=Severity(data["severity"]),
            message=data["message"],
            rule_id=data["rule_id"],
            evidence=Evidence(data["evidence"]),
            path=data.get("path"),
            detail=data.get("detail"),
        )


@dataclass(frozen=True, slots=True)
class DoctorReport:
    """The complete answer for ``skill-lens doctor``.

    An empty ``findings`` tuple is a clean bill of health, not an error: like
    every other command, ``doctor`` exits ``0`` when it ran successfully.
    ``home`` and ``cwd`` record what was inspected so a report is traceable to
    the exact filesystem state that produced it.

    ``healthy`` is derived from the findings -- it is a view, never a stored
    fact the computation has to keep in sync (the same rule ``DiffReport``
    follows for ``has_differences``).
    """

    home: str
    cwd: str
    findings: tuple[DoctorFinding, ...] = ()

    @property
    def healthy(self) -> bool:
        """True when nothing rose above an informational note.

        Derived, never serialized.
        """
        return not any(finding.severity is not Severity.INFO for finding in self.findings)

    def counts_by_severity(self) -> dict[str, int]:
        """Severity -> number of findings at that level (all three keys present)."""
        counts = {severity.value: 0 for severity in Severity}
        for finding in self.findings:
            counts[finding.severity.value] += 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "home": self.home,
            "cwd": self.cwd,
            "findings": [finding.to_dict() for finding in self.findings],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DoctorReport:
        return cls(
            home=data["home"],
            cwd=data["cwd"],
            findings=tuple(
                DoctorFinding.from_dict(finding) for finding in data.get("findings", ())
            ),
        )
