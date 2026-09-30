"""The 3-axis resolution engine.

For one skill name, one agent and one working directory, this answers *why*
that name resolves the way it does. Every decision is derived from the agent
registry, so a reason is always traceable to a ``rule_id`` and an evidence tag
-- never invented.

The three axes:

* **Parse status** -- is the copy well-formed? (valid / malformed / ...)
* **Visibility**  -- can this agent's search rules see it? (searched / hidden)
* **Collision**   -- how does it relate to same-named copies? (winner / shadow)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from skill_lens.core.discovery import (
    DiscoveredEntry,
    DiscoveryIndex,
    RootHit,
    discover,
)
from skill_lens.models.enums import (
    Collision,
    Evidence,
    HeadlineState,
    ParseStatus,
    Scope,
    Visibility,
)
from skill_lens.models.installation import SkillInstallation
from skill_lens.models.resolution import CandidateResolution, ResolutionReport
from skill_lens.registry.loader import AgentDefinition, load_registry

_UNREADABLE_CANONICAL = "unreadable"
_CYCLE = "symlink_cycle"
_DANGLING = "dangling_symlink"
_DENIED = "permission_denied"

_FALLBACK_REASON = {
    HeadlineState.ACTIVE: "Winning copy for this agent.",
    HeadlineState.SHADOWED: "Suppressed by a higher-priority copy.",
    HeadlineState.COEXISTS: "Coexists with another copy for this name.",
    HeadlineState.DISABLED: "Explicitly turned off by agent configuration.",
    HeadlineState.UNSEARCHED: "Not searched by this agent.",
    HeadlineState.INVALID: "Rejected: invalid or unreadable skill.",
    HeadlineState.AMBIGUOUS: "Tie or undocumented collision policy.",
}


@dataclass(frozen=True, slots=True)
class Candidate:
    """Pre-collision view of one discovered copy for an agent."""

    entry: DiscoveredEntry
    hit: RootHit
    searched: bool
    overridden: bool

    @property
    def rank(self) -> int:
        return self.hit.rank if self.searched else -1

    @property
    def canonical_key(self) -> str:
        return self.entry.canonical_path or f"@{self.entry.entrypoint_path}"

    @property
    def reason_fragment(self) -> str:
        parse = self.entry.parse
        if parse is not None and parse.description:
            return parse.description
        if self.hit.nested:
            return "nested project copy"
        return "same-named copy"


# --- Small predicates ------------------------------------------------------


def _is_valid(entry: DiscoveredEntry) -> bool:
    return entry.parse_status == ParseStatus.VALID.value


def _searched_hits(agent: AgentDefinition, entry: DiscoveredEntry) -> list[RootHit]:
    return [hit for hit in entry.hits if hit.agent_id == agent.id]


def _representative_hit(
    agent: AgentDefinition, entry: DiscoveredEntry, fallback_root_id: str
) -> RootHit:
    """The highest-ranked searched root that reaches ``entry`` for this agent."""
    hits = _searched_hits(agent, entry)
    if hits:
        return max(hits, key=lambda hit: (hit.rank, hit.specificity))
    root = agent.root_by_id(fallback_root_id)
    return RootHit(
        agent_id=agent.id,
        root_id=fallback_root_id,
        rank=0,
        rule_id=root.rule_id if root else agent.unsearched_rule_id,
        evidence=root.evidence.value if root else agent.policy_evidence.value,
        scope=root.scope if root else (entry.hits[0].scope if entry.hits else Scope.USER),
    )


def _default_root_id(agent: AgentDefinition) -> str:
    globals_ = [root for root in agent.roots if not root.is_project]
    if globals_:
        return max(globals_, key=lambda root: root.rank).id
    return agent.roots[0].id if agent.roots else f"{agent.id}_roots"


def _matches(agent: AgentDefinition, entry: DiscoveredEntry, name: str) -> bool:
    if not _is_valid(entry):
        return entry.name == name
    parse = entry.parse
    assert parse is not None
    if agent.identity_source == "directory_name":
        candidates = {parse.directory_name}
    elif agent.identity_source == "frontmatter_name":
        candidates = {parse.frontmatter_name or parse.directory_name}
    else:  # hybrid
        candidates = {parse.directory_name, parse.frontmatter_name or parse.directory_name}
    return name in candidates


def _load_disabled_overrides(agent: AgentDefinition, home: Path) -> set[str]:
    if not agent.disabled_settings or not agent.disabled_key:
        return set()
    try:
        data = json.loads((home / agent.disabled_settings).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    override = data.get(agent.disabled_key)
    if not isinstance(override, dict):
        return set()
    return {str(name) for name, enabled in override.items() if enabled is False}


def _candidates_for(agent: AgentDefinition, index: DiscoveryIndex, name: str) -> list[Candidate]:
    overrides = _load_disabled_overrides(agent, Path(index.home))
    fallback_root_id = _default_root_id(agent)
    candidates: list[Candidate] = []
    for entry in index.entries:
        if not _matches(agent, entry, name):
            continue
        hit = _representative_hit(agent, entry, fallback_root_id)
        candidates.append(
            Candidate(
                entry=entry,
                hit=hit,
                searched=bool(_searched_hits(agent, entry)),
                overridden=entry.name in overrides,
            )
        )
    return candidates


# --- Headline derivation ---------------------------------------------------


def _assign_states(
    agent: AgentDefinition, candidates: list[Candidate]
) -> list[tuple[Candidate, HeadlineState]]:
    """Assign each candidate a state and return them alongside it."""
    searched = [c for c in candidates if c.searched]
    if not searched:
        return [(c, HeadlineState.UNSEARCHED) for c in candidates]

    valid = [c for c in searched if _is_valid(c.entry)]
    if not valid:
        return [
            (c, HeadlineState.INVALID if c.searched else HeadlineState.UNSEARCHED)
            for c in candidates
        ]

    enabled = [c for c in valid if not c.overridden]
    if not enabled:
        return [(c, _fallback_state(c, HeadlineState.DISABLED)) for c in candidates]

    roles = _active_roles(candidates, agent)
    return [
        (c, roles.get(c.canonical_key, _fallback_state(c, HeadlineState.ACTIVE)))
        for c in candidates
    ]


# --- Per-candidate state assignment ----------------------------------------


def _active_roles(candidates: list[Candidate], agent: AgentDefinition) -> dict[str, HeadlineState]:
    """Map each candidate key to its state, plus decide the overall headline.

    The top-ranked searched, valid, enabled copy wins. A nested (qualified)
    copy coexists. Under an ambiguous coexistence policy any other searched
    valid copy coexists; otherwise it is shadowed.
    """
    searched_valid = [
        c for c in candidates if c.searched and _is_valid(c.entry) and not c.overridden
    ]
    if not searched_valid:
        return {}
    top_rank = max(c.rank for c in searched_valid)
    winners = [c for c in searched_valid if c.rank == top_rank]
    ambiguous = len(winners) > 1
    multi = len(searched_valid) > 1
    roles: dict[str, HeadlineState] = {}
    for candidate in candidates:
        if ambiguous:
            roles[candidate.canonical_key] = _fallback_state(candidate, HeadlineState.AMBIGUOUS)
            continue
        roles[candidate.canonical_key] = _role_for_active(agent, candidate, top_rank, multi)
    return roles


def _role_for_active(
    agent: AgentDefinition, candidate: Candidate, top_rank: int, multi: bool
) -> HeadlineState:
    if not candidate.searched:
        return HeadlineState.UNSEARCHED
    if not _is_valid(candidate.entry):
        return HeadlineState.INVALID
    if candidate.overridden:
        return HeadlineState.DISABLED
    if candidate.rank == top_rank:
        # A nested winner is qualified; it only "coexists" if another copy exists.
        if candidate.hit.nested and multi:
            return HeadlineState.COEXISTS
        return HeadlineState.ACTIVE
    if candidate.hit.nested:
        return HeadlineState.COEXISTS
    if agent.coexist_policy == "ambiguous":
        return HeadlineState.COEXISTS
    return HeadlineState.SHADOWED


def _headline_from_states(states: list[HeadlineState]) -> HeadlineState:
    """Collapse per-candidate states into the single headline state."""
    if not states:
        return HeadlineState.UNSEARCHED
    if HeadlineState.COEXISTS in states:
        return HeadlineState.COEXISTS
    if HeadlineState.ACTIVE in states:
        return HeadlineState.ACTIVE
    if HeadlineState.AMBIGUOUS in states:
        return HeadlineState.AMBIGUOUS
    if HeadlineState.DISABLED in states:
        return HeadlineState.DISABLED
    if HeadlineState.INVALID in states:
        return HeadlineState.INVALID
    return HeadlineState.UNSEARCHED


def _fallback_state(candidate: Candidate, headline: HeadlineState) -> HeadlineState:
    """Assign a candidate's state for a non-ACTIVE headline."""
    if not candidate.searched:
        return HeadlineState.UNSEARCHED
    if headline is HeadlineState.UNSEARCHED:
        return HeadlineState.UNSEARCHED
    if headline is HeadlineState.INVALID:
        return HeadlineState.INVALID
    if headline is HeadlineState.AMBIGUOUS:
        if candidate.overridden:
            return HeadlineState.DISABLED
        if not _is_valid(candidate.entry):
            return HeadlineState.INVALID
        return HeadlineState.AMBIGUOUS
    if headline is HeadlineState.DISABLED:
        return HeadlineState.DISABLED if candidate.overridden else HeadlineState.UNSEARCHED
    if not _is_valid(candidate.entry):
        return HeadlineState.INVALID
    if candidate.overridden:
        return HeadlineState.DISABLED
    return headline


# --- Building the output ---------------------------------------------------


def _installation(candidate: Candidate) -> SkillInstallation:
    entry = candidate.entry
    parse = entry.parse
    return SkillInstallation(
        name=entry.name,
        entrypoint_path=entry.entrypoint_path,
        canonical_path=entry.canonical_path or entry.entrypoint_path,
        scope=candidate.hit.scope,
        parse_status=parse.status if parse else ParseStatus.UNREADABLE,
        content_hash=entry.content_hash,
        description=parse.description if parse else None,
        frontmatter_name=parse.frontmatter_name if parse else None,
        is_symlink=entry.is_symlink,
        agent_entrypoints=tuple(hit.agent_id for hit in entry.hits),
    )


def _reason(agent: AgentDefinition, candidate: Candidate, state: HeadlineState) -> str:
    entry = candidate.entry
    if entry.error_code == _CYCLE:
        return "Symlink cycle detected; traversal stopped safely."
    if entry.error_code == _DANGLING:
        return "Dangling symlink; no real target to resolve."
    if entry.error_code == _DENIED or candidate.canonical_key == _UNREADABLE_CANONICAL:
        return "Directory unreadable (permission denied)."
    if state is HeadlineState.DISABLED:
        return "Disabled by agent configuration override."
    if state is HeadlineState.UNSEARCHED:
        return f"Not searched by {agent.name} (found via another agent's root)."
    if state is HeadlineState.AMBIGUOUS:
        return f"Ties with another copy; {agent.name}'s collision policy is undocumented."
    if state is HeadlineState.ACTIVE:
        if candidate.hit.nested:
            return f"Qualified nested copy ({candidate.reason_fragment}) wins for this directory."
        if entry.is_symlink:
            return "Canonical symlink entrypoint is the winning copy."
        return f"Highest-priority copy ({candidate.reason_fragment})."
    if state is HeadlineState.COEXISTS:
        if candidate.hit.nested:
            return "Qualified namespaced copy, accessible alongside the winning copy."
        return "Coexists with another copy; both remain available."
    if state is HeadlineState.SHADOWED:
        return f"Suppressed by a higher-priority copy ({candidate.reason_fragment})."
    return _FALLBACK_REASON[state]


_COLLISION_FOR_STATE = {
    HeadlineState.ACTIVE: Collision.WINNING_ENTRY,
    HeadlineState.SHADOWED: Collision.SUPPRESSED_SHADOW,
    HeadlineState.COEXISTS: Collision.COEXISTING_MERGED,
    HeadlineState.DISABLED: Collision.UNVERIFIED_POLICY,
    HeadlineState.UNSEARCHED: Collision.UNVERIFIED_POLICY,
    HeadlineState.INVALID: Collision.UNVERIFIED_POLICY,
    HeadlineState.AMBIGUOUS: Collision.AMBIGUOUS_TIE,
}

_VISIBILITY_FOR_STATE = {
    HeadlineState.ACTIVE: Visibility.ACTIVE_ROOT,
    HeadlineState.SHADOWED: Visibility.ACTIVE_ROOT,
    HeadlineState.COEXISTS: Visibility.ACTIVE_ROOT,
    HeadlineState.DISABLED: Visibility.DISABLED,
    HeadlineState.UNSEARCHED: Visibility.UNSEARCHED_ROOT,
    HeadlineState.INVALID: Visibility.ACTIVE_ROOT,
    HeadlineState.AMBIGUOUS: Visibility.ACTIVE_ROOT,
}


def _rule_and_evidence(
    agent: AgentDefinition, candidate: Candidate, state: HeadlineState
) -> tuple[str, Evidence]:
    entry = candidate.entry
    if entry.error_code == _CYCLE:
        return "symlink_cycle_guard", Evidence.EMPIRICAL
    if not _is_valid(entry):
        if candidate.hit.nested and candidate.hit.nested_rule_id:
            return candidate.hit.nested_rule_id, Evidence(candidate.hit.evidence)
        return "parser_requires_valid_frontmatter", Evidence.DOCUMENTED
    if state is HeadlineState.AMBIGUOUS and agent.ambiguous_rule_id:
        return agent.ambiguous_rule_id, Evidence(agent.policy_evidence)
    if state is HeadlineState.DISABLED and agent.disabled_rule_id:
        return agent.disabled_rule_id, Evidence.DOCUMENTED
    if state is HeadlineState.UNSEARCHED:
        return agent.unsearched_rule_id, Evidence(agent.policy_evidence)
    return candidate.hit.rule_for(entry.is_file), Evidence(candidate.hit.evidence)


def _resolution(
    agent: AgentDefinition, candidate: Candidate, state: HeadlineState
) -> CandidateResolution:
    rule_id, evidence = _rule_and_evidence(agent, candidate, state)
    collision = _COLLISION_FOR_STATE[state]
    if state is HeadlineState.COEXISTS and candidate.hit.nested:
        collision = Collision.QUALIFIED_NAMESPACE
    return CandidateResolution(
        state=state,
        visibility=_VISIBILITY_FOR_STATE[state],
        collision=collision,
        rule_id=rule_id,
        evidence=evidence,
        reason=_reason(agent, candidate, state),
        rank=max(candidate.rank, 0),
        installation=_installation(candidate),
    )


_STATE_ORDER = {
    HeadlineState.ACTIVE: 0,
    HeadlineState.COEXISTS: 1,
    HeadlineState.DISABLED: 2,
    HeadlineState.SHADOWED: 3,
    HeadlineState.AMBIGUOUS: 4,
    HeadlineState.INVALID: 5,
    HeadlineState.UNSEARCHED: 6,
}


def _sort_resolutions(resolutions: list[CandidateResolution]) -> list[CandidateResolution]:
    deduped: list[CandidateResolution] = []
    seen: set[tuple[str, str]] = set()
    for resolution in resolutions:
        key = (resolution.installation.entrypoint_path, resolution.state.value)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(resolution)
    deduped.sort(
        key=lambda r: (_STATE_ORDER.get(r.state, 99), -r.rank, r.installation.entrypoint_path)
    )
    return deduped


# --- Public entry point ----------------------------------------------------


def resolve_skill(
    name: str,
    agent_id: str,
    cwd: Path,
    home: Path,
    index: DiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None,
) -> ResolutionReport:
    """Resolve ``name`` for ``agent_id`` from ``cwd`` and explain the result."""
    agents = registry if registry is not None else load_registry()
    if agent_id not in agents:
        known = ", ".join(sorted(agents))
        raise KeyError(f"unknown agent '{agent_id}'. Known agents: {known}")
    agent = agents[agent_id]
    discovery = index if index is not None else discover(home, cwd, agents)

    candidates = _candidates_for(agent, discovery, name)
    outcomes = _assign_states(agent, candidates)
    headline = _headline_from_states([state for _candidate, state in outcomes])
    resolutions = [_resolution(agent, candidate, state) for candidate, state in outcomes]

    notes: tuple[str, ...] = ()
    if headline is HeadlineState.AMBIGUOUS:
        notes = (f"{agent.name} has no documented winner for duplicate names.",)
    return ResolutionReport(
        skill_name=name,
        agent=agent.id,
        agent_name=agent.name,
        cwd=str(cwd),
        collision_policy=agent.collision_policy,
        policy_evidence=agent.policy_evidence,
        headline=headline,
        candidates=tuple(_sort_resolutions(resolutions)),
        notes=notes,
    )


__all__ = ["Candidate", "resolve_skill"]
