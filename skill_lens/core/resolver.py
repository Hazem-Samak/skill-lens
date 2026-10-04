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
from dataclasses import dataclass, replace
from pathlib import Path

from skill_lens.core.discovery import (
    DiscoveredEntry,
    DiscoveryIndex,
    RootHit,
    canonical_key,
    discover,
    labels_for_entries,
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

# Coexistence policies under which a lower-ranked copy is *not* suppressed.
# ``ambiguous``: ties / undocumented policy. ``merge``: every root is listed and
# no copy is documented to suppress the others (spec section 2, COEXISTS).
_COEXISTING_POLICIES = frozenset({"ambiguous", "merge"})

_FALLBACK_REASON = {
    HeadlineState.ACTIVE: "Winning copy for this agent.",
    HeadlineState.SHADOWED: "Suppressed by a higher-priority copy.",
    HeadlineState.COEXISTS: "Coexists with another copy for this name.",
    HeadlineState.DISABLED: "Explicitly turned off by agent configuration.",
    HeadlineState.UNSEARCHED: "Not searched by this agent.",
    HeadlineState.INVALID: "Rejected: invalid or unreadable skill.",
    HeadlineState.AMBIGUOUS: "Tie or undocumented collision policy.",
}

_NOT_FOUND_NOTE = "No copy of this skill name was found in any search root."


@dataclass(frozen=True, slots=True)
class Candidate:
    """One entrypoint of a discovered copy, evaluated for a single agent.

    A candidate is a *path*, not a canonical library: two entrypoints of the
    same library are two candidates, because precedence is judged on the
    entrypoint path (spec section 4). ``entrypoint_path`` therefore comes from
    ``hit`` -- the path this agent's root actually reaches the skill through.
    """

    entry: DiscoveredEntry
    hit: RootHit
    searched: bool
    overridden: bool

    @property
    def entrypoint_path(self) -> str:
        """The path this agent reaches the skill through."""
        return self.hit.entrypoint_path or self.entry.entrypoint_path

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


def _identity_names(agent: AgentDefinition, entry: DiscoveredEntry) -> set[str]:
    """Every name this agent would use to look up ``entry``.

    A skill that fails validation (for example a missing ``description``) is
    still *findable*: the frontmatter name is populated for
    ``missing_description`` parses, so an agent that identifies skills by
    frontmatter must be able to find it by that name rather than only by its
    folder name.
    """
    parse = entry.parse
    if parse is None:
        return {entry.name}
    directory_name = parse.directory_name
    frontmatter_name = parse.frontmatter_name or directory_name
    if agent.identity_source == "directory_name":
        return {directory_name}
    if agent.identity_source == "frontmatter_name":
        return {frontmatter_name}
    return {directory_name, frontmatter_name}


def _matches(agent: AgentDefinition, entry: DiscoveredEntry, name: str) -> bool:
    return name in _identity_names(agent, entry)


def _load_disabled_overrides(agent: AgentDefinition, home: Path) -> set[str]:
    if not agent.disabled_settings or not agent.disabled_key:
        return set()
    try:
        data = json.loads((home / agent.disabled_settings).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    if not isinstance(data, dict):
        return set()
    override = data.get(agent.disabled_key)
    if not isinstance(override, dict):
        return set()
    return {str(name) for name, enabled in override.items() if enabled is False}


def _candidates_for(agent: AgentDefinition, index: DiscoveryIndex, name: str) -> list[Candidate]:
    """Build one candidate per entrypoint this agent reaches for ``name``.

    A symlink farm reaches one canonical library through several paths. Each of
    those paths is a genuine candidate for *this* agent, because precedence is
    judged on the entrypoint path (spec section 4) -- a project shortcut into a
    global library outranks the global root. Entries the agent never searches
    contribute a single ``UNSEARCHED`` candidate.
    """
    overrides = _load_disabled_overrides(agent, Path(index.home))
    fallback_root_id = _default_root_id(agent)
    candidates: list[Candidate] = []
    for entry in index.entries:
        if not _matches(agent, entry, name):
            continue
        overridden = entry.name in overrides
        hits = _searched_hits(agent, entry)
        if not hits:
            candidates.append(
                Candidate(
                    entry=entry,
                    hit=_representative_hit(agent, entry, fallback_root_id),
                    searched=False,
                    overridden=overridden,
                )
            )
            continue
        # One candidate per distinct entrypoint path; if two roots of the same
        # agent reach the identical path, the higher-ranked rule represents it.
        best: dict[str, RootHit] = {}
        for hit in hits:
            path = hit.entrypoint_path
            current = best.get(path)
            if current is None or hit.rank > current.rank:
                best[path] = hit
        for hit in best.values():
            candidates.append(Candidate(entry=entry, hit=hit, searched=True, overridden=overridden))
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
        (c, roles.get(index, _fallback_state(c, HeadlineState.ACTIVE)))
        for index, c in enumerate(candidates)
    ]


# --- Per-candidate state assignment ----------------------------------------


def _active_roles(candidates: list[Candidate], agent: AgentDefinition) -> dict[int, HeadlineState]:
    """Map each candidate's position to its collision state.

    The top-ranked searched, valid, enabled entrypoint wins. A nested
    (qualified) copy coexists. Under an ``ambiguous`` or ``merge`` coexistence
    policy any other searched valid copy coexists; otherwise it is shadowed.

    States are keyed by candidate index, not by canonical target: two
    entrypoints of the same library are distinct candidates with distinct
    ranks, and collapsing them here is what used to lose a shadowed copy.
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
    roles: dict[int, HeadlineState] = {}
    for index, candidate in enumerate(candidates):
        if ambiguous:
            roles[index] = _fallback_state(candidate, HeadlineState.AMBIGUOUS)
            continue
        roles[index] = _role_for_active(agent, candidate, top_rank, multi)
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
    if agent.coexist_policy in _COEXISTING_POLICIES:
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
        entrypoint_path=candidate.entrypoint_path,
        canonical_path=entry.canonical_path or candidate.entrypoint_path,
        scope=candidate.hit.scope,
        parse_status=parse.status if parse else ParseStatus.UNREADABLE,
        content_hash=entry.content_hash,
        description=parse.description if parse else None,
        frontmatter_name=parse.frontmatter_name if parse else None,
        is_symlink=entry.is_symlink,
        # Paths, not agent ids (Phase 0 contract): every entrypoint that reaches
        # this canonical library, home-relative in display contexts.
        agent_entrypoints=entry.entrypoint_paths or (candidate.entrypoint_path,),
        variant_label=entry.variant_label,
    )


def _winner_label(agent: AgentDefinition, winner: Candidate) -> str:
    """A short, human label for the root that won, e.g. ``the project root .grok/skills``.

    Registry paths are home-relative for global roots and repository-relative
    for project roots, so the two must be named differently -- otherwise
    "``.agents/skills``" would read as the home copy when the project copy won.
    """
    root = agent.root_by_id(winner.hit.root_id)
    if root is None:
        return f"the {winner.hit.root_id} root"
    if root.is_absolute:
        return f"the absolute root {root.path}"
    if root.is_project:
        return f"the project root {root.path}"
    return f"the global root ~/{root.path}"


def _reason(
    agent: AgentDefinition,
    candidate: Candidate,
    state: HeadlineState,
    winner: Candidate | None = None,
) -> str:
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
        if agent.coexist_policy == "merge":
            return (
                f"Listed alongside a higher-priority copy; {agent.name} merges all roots "
                "with no documented winner."
            )
        if agent.coexist_policy == "ambiguous":
            return "Listed alongside another copy; collision policy is undocumented."
        return "Coexists with another copy; both remain available."
    if state is HeadlineState.SHADOWED:
        # Name the *winning* copy's root, never this copy's own description.
        if winner is not None:
            return f"Suppressed by the higher-priority copy in {_winner_label(agent, winner)}."
        return _FALLBACK_REASON[state]
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
    agent: AgentDefinition,
    candidate: Candidate,
    state: HeadlineState,
    winner: Candidate | None = None,
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
    if state is HeadlineState.SHADOWED and winner is not None:
        # The rule that explains a shadow is the rule of the copy that beat it,
        # so the reason is traceable to the actual cause, not to the loser.
        return winner.hit.rule_for(entry.is_file), Evidence(winner.hit.evidence)
    return candidate.hit.rule_for(entry.is_file), Evidence(candidate.hit.evidence)


def _resolution(
    agent: AgentDefinition,
    candidate: Candidate,
    state: HeadlineState,
    winner: Candidate | None = None,
) -> CandidateResolution:
    rule_id, evidence = _rule_and_evidence(agent, candidate, state, winner)
    collision = _COLLISION_FOR_STATE[state]
    if state is HeadlineState.COEXISTS and candidate.hit.nested:
        collision = Collision.QUALIFIED_NAMESPACE
    return CandidateResolution(
        state=state,
        visibility=_VISIBILITY_FOR_STATE[state],
        collision=collision,
        rule_id=rule_id,
        evidence=evidence,
        reason=_reason(agent, candidate, state, winner),
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


def _assign_variant_labels(candidates: list[Candidate]) -> dict[int, str]:
    """Label differing copies of one name as Variant A / B / C.

    Delegates to the shared rule in :mod:`skill_lens.core.discovery` so that
    ``why``, ``scan`` and ``diff`` can never disagree about a copy's label.
    Ordering is by scope specificity (project before user), then discovery
    order -- *not* by this agent's rank, because ``scan`` has no agent to rank
    with. Which copy actually wins is reported by the candidate's ``state``, not
    by its letter.
    """
    labels_by_key = labels_for_entries(candidate.entry for candidate in candidates)
    position_by_key: dict[str, int] = {}
    for position, candidate in enumerate(candidates):
        position_by_key.setdefault(canonical_key(candidate.entry), position)
    return {
        position_by_key[key]: label
        for key, label in labels_by_key.items()
        if key in position_by_key
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

    # The winning copy explains every shadow, so it is resolved first and passed
    # to the rest: their reason and rule then name the real cause.
    winner = next(
        (c for c, state in outcomes if state is HeadlineState.ACTIVE and c.searched), None
    )
    ordered = _sort_resolutions(
        [_resolution(agent, candidate, state, winner) for candidate, state in outcomes]
    )

    labels = {
        candidates[index].entrypoint_path: label
        for index, label in _assign_variant_labels(candidates).items()
    }
    ordered = [_label_resolution(resolution, labels) for resolution in ordered]

    notes: tuple[str, ...] = ()
    if not candidates:
        # F-10: UNSEARCHED means "on disk, outside this agent's search rules".
        # Zero candidates is a different fact: the name is nowhere on disk.
        notes = (_NOT_FOUND_NOTE,)
    elif headline is HeadlineState.AMBIGUOUS:
        notes = (f"{agent.name} has no documented winner for duplicate names.",)
    return ResolutionReport(
        skill_name=name,
        agent=agent.id,
        agent_name=agent.name,
        cwd=str(cwd),
        collision_policy=agent.collision_policy,
        policy_evidence=agent.policy_evidence,
        headline=headline,
        candidates=tuple(ordered),
        notes=notes,
        found=bool(candidates),
    )


def _label_resolution(
    resolution: CandidateResolution, labels: dict[str, str]
) -> CandidateResolution:
    """Attach this entrypoint's variant label to its installation."""
    label = labels.get(resolution.installation.entrypoint_path)
    if label is None or resolution.installation.variant_label == label:
        return resolution
    return replace(resolution, installation=replace(resolution.installation, variant_label=label))


__all__ = ["Candidate", "resolve_skill"]
