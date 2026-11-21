"""Compatibility re-export for the agent-summary helper.

The implementation moved to :mod:`skill_lens.models.agents` so report
composition can share it without a model-to-presentation import. Callers keep
their existing import path and output stays byte-identical.
"""

from __future__ import annotations

from skill_lens.models.agents import AgentSummary, agents_payload

__all__ = ["AgentSummary", "agents_payload"]
