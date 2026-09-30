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
