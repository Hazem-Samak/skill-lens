"""Shared plain data helpers for the known-agent presentation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict

from skill_lens.registry.loader import AgentDefinition


class AgentSummary(TypedDict):
    """The stable summary fields emitted by ``skill-lens agents --json``."""

    id: str
    name: str
    collision_policy: str
    policy_evidence: str
    roots: int


def agents_payload(definitions: Sequence[AgentDefinition]) -> list[AgentSummary]:
    """Return sorted CLI-compatible agent summaries without loading or reading data."""
    return [
        {
            "id": agent.id,
            "name": agent.name,
            "collision_policy": agent.collision_policy,
            "policy_evidence": agent.policy_evidence.value,
            "roots": len(agent.roots),
        }
        for agent in sorted(definitions, key=lambda agent: agent.id)
    ]


__all__ = ["AgentSummary", "agents_payload"]
