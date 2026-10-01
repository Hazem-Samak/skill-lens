"""TOML loader for agent definitions.

Reads ``skill_lens/registry/agents/*.toml`` into frozen dataclasses. Every
root carries an explicit ``rank`` and ``rule_id`` so the resolver never has to
guess precedence and every emitted reason is traceable to a provenance tag.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skill_lens.models.enums import Evidence, Scope
from skill_lens.registry import REGISTRY_DIR


@dataclass(frozen=True, slots=True)
class AgentRoot:
    """A single directory an agent searches for skills."""

    id: str
    kind: str
    path: str
    scope: Scope
    rank: int
    rule_id: str
    evidence: Evidence
    nested_rule_id: str | None = None
    file_rule_id: str | None = None
    recursive: bool = False

    @property
    def is_project(self) -> bool:
        return self.kind == "project"

    @property
    def is_absolute(self) -> bool:
        return self.path.startswith("/")


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    """Everything Skill Lens knows about how one agent finds and ranks skills."""

    id: str
    name: str
    identity_source: str
    collision_policy: str
    policy_evidence: Evidence
    coexist_policy: str
    walk_boundary: str
    unsearched_rule_id: str
    source: str = ""
    disabled_rule_id: str | None = None
    disabled_settings: str | None = None
    disabled_key: str | None = None
    ambiguous_rule_id: str | None = None
    roots: tuple[AgentRoot, ...] = field(default_factory=tuple)

    def root_by_id(self, root_id: str) -> AgentRoot | None:
        for root in self.roots:
            if root.id == root_id:
                return root
        return None


def _parse_root(raw: dict[str, Any]) -> AgentRoot:
    return AgentRoot(
        id=raw["id"],
        kind=raw["kind"],
        path=raw["path"],
        scope=Scope(raw["scope"]),
        rank=int(raw["rank"]),
        rule_id=raw["rule_id"],
        evidence=Evidence(raw["evidence"]),
        nested_rule_id=raw.get("nested_rule_id"),
        file_rule_id=raw.get("file_rule_id"),
        recursive=bool(raw.get("recursive", False)),
    )


def load_agent_file(path: Path) -> AgentDefinition:
    """Load one agent TOML file into an :class:`AgentDefinition`."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    roots = tuple(_parse_root(raw) for raw in data.get("roots", ()))
    return AgentDefinition(
        id=data["id"],
        name=data["name"],
        identity_source=data.get("identity_source", "frontmatter_name"),
        collision_policy=data.get("collision_policy", "Unknown"),
        policy_evidence=Evidence(data.get("policy_evidence", "inferred")),
        coexist_policy=data.get("coexist_policy", "ambiguous"),
        walk_boundary=data.get("walk_boundary", "git_root"),
        unsearched_rule_id=data.get("unsearched_rule_id", f"{data['id']}_search_roots"),
        source=data.get("source", ""),
        disabled_rule_id=data.get("disabled_rule_id"),
        disabled_settings=data.get("disabled_settings"),
        disabled_key=data.get("disabled_key"),
        ambiguous_rule_id=data.get("ambiguous_rule_id"),
        roots=roots,
    )


def load_registry(directory: Path | None = None) -> dict[str, AgentDefinition]:
    """Load every agent definition, keyed by agent id."""
    registry_dir = directory or REGISTRY_DIR
    agents: dict[str, AgentDefinition] = {}
    for path in sorted(registry_dir.glob("*.toml")):
        agent = load_agent_file(path)
        agents[agent.id] = agent
    return agents


def list_agents(directory: Path | None = None) -> list[AgentDefinition]:
    """Return all agents sorted by id."""
    return sorted(load_registry(directory).values(), key=lambda agent: agent.id)


def load_agent(agent_id: str, directory: Path | None = None) -> AgentDefinition:
    """Load a single agent by id, raising ``KeyError`` when unknown."""
    registry = load_registry(directory)
    try:
        return registry[agent_id]
    except KeyError:
        known = ", ".join(sorted(registry))
        raise KeyError(f"unknown agent '{agent_id}'. Known agents: {known}") from None
