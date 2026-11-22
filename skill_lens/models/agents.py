"""Stable agent-summary data emitted by ``skill-lens agents --json``.

The summary type lives in the model layer so report composition can reuse it
without importing the presentation layer. The registry import is deliberately
``TYPE_CHECKING``-only: ``skill_lens.registry.loader`` imports
``skill_lens.models.enums``, so a runtime import back into the registry from
this module would break a registry-first import with a partially initialised
module. ``agents_payload`` only reads attributes, so the annotation is enough.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from skill_lens.registry.loader import AgentDefinition


class AgentSummary(TypedDict):
    """The stable summary fields emitted by ``skill-lens agents --json``."""

    id: str
    name: str
    collision_policy: str
    policy_evidence: str
    roots: int


def agents_payload(definitions: Iterable[AgentDefinition]) -> list[AgentSummary]:
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
