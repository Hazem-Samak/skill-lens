"""The data side of ``skill-lens search``: which skill copies match a query, and where.

Plain frozen dataclasses with ``to_dict()``, like every other report model. The
CLI prints them as canonical JSON (sorted keys), so field order here is for
readers only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from skill_lens.models.enums import Scope


class MatchField(StrEnum):
    """Where a query was found, in ranking order: name beats description beats body."""

    NAME = "name"
    DESCRIPTION = "description"
    BODY = "body"


#: Rank of each field; a lower number sorts first.
MATCH_RANK: dict[MatchField, int] = {
    MatchField.NAME: 0,
    MatchField.DESCRIPTION: 1,
    MatchField.BODY: 2,
}


@dataclass(frozen=True, slots=True)
class LookupState:
    """One agent's state for one lookup name of a copy.

    A copy can be reached through several aliases by the same agent, and those
    aliases can resolve differently (one ACTIVE, another SHADOWED). Keeping the
    name beside the state makes that explicit instead of collapsing it into one
    invented winner.
    """

    agent: str
    name: str
    state: str

    def to_dict(self) -> dict[str, str]:
        return {"agent": self.agent, "name": self.name, "state": self.state}


@dataclass(frozen=True, slots=True)
class SearchHit:
    """One skill copy that matched, with the evidence of why.

    ``name`` is the folder (or file) name every other command uses;
    ``frontmatter_name`` is the ``name:`` field when it exists and differs, so a
    match on it is visible. ``state`` is the selected agent's state for the match
    (``None`` when no agent was given); ``states`` carries the per-agent,
    per-lookup-name evidence behind it, and without ``--agent`` is the only place
    states appear.
    """

    name: str
    match: MatchField
    snippet: str
    scope: Scope
    canonical_path: str
    agents: tuple[str, ...]
    parse_status: str
    frontmatter_name: str | None = None
    variant_label: str | None = None
    state: str | None = None
    states: tuple[LookupState, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "agents": list(self.agents),
            "canonical_path": self.canonical_path,
            "frontmatter_name": self.frontmatter_name,
            "match": self.match.value,
            "name": self.name,
            "parse_status": self.parse_status,
            "scope": self.scope.value,
            "snippet": self.snippet,
            "state": self.state,
            "states": [item.to_dict() for item in self.states],
            "variant_label": self.variant_label,
        }


@dataclass(frozen=True, slots=True)
class SearchReport:
    """The complete answer to one search.

    ``agent`` is the ``--agent`` filter (``None`` for all agents); ``agent_name``
    is its display name for the terminal. ``results`` are already ranked and,
    with an agent, already filtered, so ``total`` and :meth:`counts` describe
    exactly what is shown. ``unreadable`` lists blocked roots in the same shape
    as ``scan``, so an empty result is never silently caused by one.
    """

    query: str
    home: str
    cwd: str
    results: tuple[SearchHit, ...]
    agent: str | None = None
    agent_name: str | None = None
    unreadable: tuple[dict[str, str], ...] = field(default_factory=tuple)

    @property
    def total(self) -> int:
        return len(self.results)

    def counts(self) -> dict[str, int]:
        """How many results matched in each field."""
        tally = {matched.value: 0 for matched in MatchField}
        for hit in self.results:
            tally[hit.match.value] += 1
        return tally

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "counts": self.counts(),
            "cwd": self.cwd,
            "home": self.home,
            "query": self.query,
            "results": [hit.to_dict() for hit in self.results],
            "total": self.total,
            "unreadable": list(self.unreadable),
        }


__all__ = ["MATCH_RANK", "LookupState", "MatchField", "SearchHit", "SearchReport"]
