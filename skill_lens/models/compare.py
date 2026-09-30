"""Comparison model emitted by ``skill-lens compare --agent A --agent B``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skill_lens.models.enums import CompareRelation


@dataclass(frozen=True, slots=True)
class CompareEntry:
    """One skill name and how it sits between exactly two agents.

    ``path_a`` / ``path_b`` are the entrypoint paths each agent actually
    sees -- under a symlink farm those differ even when the library is one.
    ``canonical_a`` / ``canonical_b`` are the resolved targets: equal
    canonicals is what makes the relation ``shared`` rather than merely
    "the same name twice". A relation that leaves one agent without the
    name stores ``None`` on that agent's side.
    """

    name: str
    relation: CompareRelation
    path_a: str | None = None
    path_b: str | None = None
    canonical_a: str | None = None
    canonical_b: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "relation": self.relation.value,
            "path_a": self.path_a,
            "path_b": self.path_b,
            "canonical_a": self.canonical_a,
            "canonical_b": self.canonical_b,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompareEntry:
        return cls(
            name=data["name"],
            relation=CompareRelation(data["relation"]),
            path_a=data.get("path_a"),
            path_b=data.get("path_b"),
            canonical_a=data.get("canonical_a"),
            canonical_b=data.get("canonical_b"),
        )


@dataclass(frozen=True, slots=True)
class CompareReport:
    """The complete answer for one pairwise capability comparison.

    ``agent_a`` / ``agent_b`` are the registry ids used on the command line
    and decide which side of every entry the ``*_a`` fields belong to. An
    empty ``entries`` tuple means the two agents share no skill names and
    neither has any of its own -- a fact, not an error (exit code ``0``).

    The counts are derived views of ``entries`` (same rule as
    ``DiffReport.has_differences``): never serialized, never able to drift.
    """

    agent_a: str
    agent_b: str
    agent_a_name: str
    agent_b_name: str
    home: str
    cwd: str
    entries: tuple[CompareEntry, ...] = ()
    notes: tuple[str, ...] = ()

    def counts_by_relation(self) -> dict[str, int]:
        """Relation -> entry count (all four keys present)."""
        counts = {relation.value: 0 for relation in CompareRelation}
        for entry in self.entries:
            counts[entry.relation.value] += 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_a": self.agent_a,
            "agent_b": self.agent_b,
            "agent_a_name": self.agent_a_name,
            "agent_b_name": self.agent_b_name,
            "home": self.home,
            "cwd": self.cwd,
            "entries": [entry.to_dict() for entry in self.entries],
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompareReport:
        return cls(
            agent_a=data["agent_a"],
            agent_b=data["agent_b"],
            agent_a_name=data["agent_a_name"],
            agent_b_name=data["agent_b_name"],
            home=data["home"],
            cwd=data["cwd"],
            entries=tuple(CompareEntry.from_dict(entry) for entry in data.get("entries", ())),
            notes=tuple(data.get("notes", ())),
        )
