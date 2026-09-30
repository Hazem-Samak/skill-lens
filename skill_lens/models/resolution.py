"""The runtime side of the model: how a skill resolves for one agent + cwd."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from skill_lens.models.enums import (
    Collision,
    Evidence,
    HeadlineState,
    Visibility,
)
from skill_lens.models.installation import SkillInstallation


@dataclass(frozen=True, slots=True)
class CandidateResolution:
    """One installation evaluated along the 3 axes for a specific agent.

    ``rule_id`` and ``evidence`` make every reason machine-checkable and
    provenance-tagged (no hallucinated precedence claims).
    """

    state: HeadlineState
    visibility: Visibility
    collision: Collision
    rule_id: str
    evidence: Evidence
    reason: str
    rank: int
    installation: SkillInstallation

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "visibility": self.visibility.value,
            "collision": self.collision.value,
            "rule_id": self.rule_id,
            "evidence": self.evidence.value,
            "reason": self.reason,
            "rank": self.rank,
            "installation": self.installation.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CandidateResolution:
        return cls(
            state=HeadlineState(data["state"]),
            visibility=Visibility(data["visibility"]),
            collision=Collision(data["collision"]),
            rule_id=data["rule_id"],
            evidence=Evidence(data["evidence"]),
            reason=data["reason"],
            rank=int(data["rank"]),
            installation=SkillInstallation.from_dict(data["installation"]),
        )


@dataclass(frozen=True, slots=True)
class ResolutionReport:
    """Full resolution answer for one skill name, one agent, one working dir."""

    skill_name: str
    agent: str
    agent_name: str
    cwd: str
    collision_policy: str
    policy_evidence: Evidence
    headline: HeadlineState
    candidates: tuple[CandidateResolution, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "agent": self.agent,
            "agent_name": self.agent_name,
            "cwd": self.cwd,
            "collision_policy": self.collision_policy,
            "policy_evidence": self.policy_evidence.value,
            "headline": self.headline.value,
            "candidates": [c.to_dict() for c in self.candidates],
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResolutionReport:
        return cls(
            skill_name=data["skill_name"],
            agent=data["agent"],
            agent_name=data["agent_name"],
            cwd=data["cwd"],
            collision_policy=data["collision_policy"],
            policy_evidence=Evidence(data["policy_evidence"]),
            headline=HeadlineState(data["headline"]),
            candidates=tuple(CandidateResolution.from_dict(c) for c in data.get("candidates", ())),
            notes=tuple(data.get("notes", ())),
        )
