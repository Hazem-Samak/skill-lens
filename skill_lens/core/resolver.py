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
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from skill_lens.core import paths
from skill_lens.core.config import (
    ResolvedAgentControls,
    is_loadable_for_agent,
    resolve_agent_controls,
    resolve_candidate_controls,
)
from skill_lens.core.discovery import (
    DiscoveredEntry,
    DiscoveryIndex,
    RootHit,
    canonical_key,
    discover,
    labels_for_entries,
)
from skill_lens.core.snapshot_models import FrozenDiscoveryIndex
from skill_lens.models.enums import (
    Collision,
    Evidence,
    HeadlineState,
    InvocationPolicy,
    LoadabilityStatus,
    ParseStatus,
    PermissionEffect,
    RootBase,
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


def _is_valid_for_agent(
    agent: AgentDefinition, entry: DiscoveredEntry, hit: RootHit | None = None
) -> bool:
    loadability, _ = is_loadable_for_agent(agent, entry, hit)
    return loadability is not LoadabilityStatus.INVALID


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
        is_file=entry.is_file,
    )


def _default_root_id(agent: AgentDefinition) -> str:
    globals_ = [root for root in agent.roots if not root.is_project]
    if globals_:
        return max(globals_, key=lambda root: root.rank).id
    return agent.roots[0].id if agent.roots else f"{agent.id}_roots"


def entrypoint_alias(path: str | Path, is_file: bool = False) -> str:
    """Return the filename stem (for files) or directory name for an entrypoint path."""
    p = Path(path)
    if is_file:
        return p.stem
    return p.name


def _hit_identity_names(agent: AgentDefinition, entry: DiscoveredEntry, hit: RootHit) -> set[str]:
    """Every name this agent would use to look up a candidate reached through ``hit``."""
    alias = entrypoint_alias(hit.entrypoint_path, hit.is_file)
    parse = entry.parse
    if parse is None:
        return {alias}
    directory_name = alias
    frontmatter_name = parse.frontmatter_name
    if agent.identity_source == "frontmatter_name":
        return {frontmatter_name} if frontmatter_name else {directory_name}
    if agent.identity_source == "directory_name":
        return {directory_name}
    return {directory_name, frontmatter_name or directory_name}


def lookup_name_for_entry(
    entry: DiscoveredEntry, agent: AgentDefinition, hit: RootHit | None = None
) -> str:
    """Determine the lookup name for a discovered entry under an agent's policy.

    Reuses hit-specific alias and agent policy:
    - When no parse exists, returns alias.
    - For 'frontmatter_name', chooses frontmatter name with alias fallback.
    - For 'directory_name' or 'either'/'hybrid', chooses alias.
    The returned name always belongs to the agent's identity names.
    """
    if hit is not None:
        alias = entrypoint_alias(hit.entrypoint_path, hit.is_file)
    else:
        hits = _searched_hits(agent, entry)
        if hits:
            best_hit = max(hits, key=lambda h: (h.rank, h.specificity))
            alias = entrypoint_alias(best_hit.entrypoint_path, best_hit.is_file)
        else:
            alias = entrypoint_alias(entry.entrypoint_path, entry.is_file)

    parse = entry.parse
    if parse is None:
        return alias

    directory_name = alias
    frontmatter_name = parse.frontmatter_name or directory_name

    chosen = frontmatter_name if agent.identity_source == "frontmatter_name" else directory_name
    return chosen


def disabled_overrides_from_bytes(agent: AgentDefinition, data: bytes | None) -> frozenset[str]:
    """Decode disabled skill overrides from raw configuration file bytes.

    Returns an empty frozenset for missing (None), unreadable/undecodable input,
    invalid JSON, a non-object top level, or a non-object overrides member. Only an
    override value that is False or 'off' disables a skill name."""
    if not agent.disabled_settings or not agent.disabled_key or data is None:
        return frozenset()
    try:
        text = data.decode("utf-8")
        parsed = json.loads(text)
    except ValueError:
        return frozenset()
    if not isinstance(parsed, dict):
        return frozenset()
    override = parsed.get(agent.disabled_key)
    if not isinstance(override, dict):
        return frozenset()
    return frozenset(
        str(name) for name, enabled in override.items() if enabled is False or enabled == "off"
    )


def _load_disabled_overrides(agent: AgentDefinition, home: Path) -> set[str]:
    if not agent.disabled_settings:
        return set()
    try:
        data: bytes | None = (home / agent.disabled_settings).read_bytes()
    except OSError:
        data = None
    return set(disabled_overrides_from_bytes(agent, data))


def _candidates_for(
    agent: AgentDefinition,
    index: DiscoveryIndex | FrozenDiscoveryIndex,
    name: str,
    *,
    controls: ResolvedAgentControls,
    explicit_overrides: frozenset[str] | None = None,
) -> list[Candidate]:
    """Build one candidate per entrypoint this agent reaches for name.

    Uses unified controls to determine override status without duplicate reads.
    """
    fallback_root_id = _default_root_id(agent)
    candidates: list[Candidate] = []
    for entry in index.entries:
        hits = _searched_hits(agent, entry)
        if hits:
            best: dict[str, RootHit] = {}
            for hit in hits:
                path = hit.entrypoint_path
                current = best.get(path)
                if agent.id == "opencode":
                    hit_key = (hit.rank, hit.specificity)
                    cur_key = (current.rank, current.specificity) if current else (-1, -1)
                else:
                    hit_key = (hit.rank, 0)
                    cur_key = (current.rank, 0) if current else (-1, 0)
                if current is None or hit_key > cur_key:
                    best[path] = hit
            for hit in best.values():
                hit_names = _hit_identity_names(agent, entry, hit)
                if name in hit_names:
                    ctrls = resolve_candidate_controls(
                        agent,
                        entry,
                        hit,
                        hit_names,
                        controls=controls,
                        captured_disabled_overrides=explicit_overrides,
                    )
                    candidates.append(
                        Candidate(
                            entry=entry,
                            hit=hit,
                            searched=True,
                            overridden=ctrls.is_disabled,
                        )
                    )
        else:
            aliases = {entrypoint_alias(h.entrypoint_path, h.is_file) for h in entry.hits}
            if entry.entrypoint_paths:
                aliases.update(entrypoint_alias(p, entry.is_file) for p in entry.entrypoint_paths)
            aliases.add(entry.name)
            fm = (
                entry.parse.frontmatter_name
                if entry.parse and entry.parse.frontmatter_name
                else None
            )

            if agent.identity_source == "directory_name":
                matches = name in aliases
                supported_identities = aliases
            elif agent.identity_source == "frontmatter_name":
                matches = (name == fm) if fm else (name in aliases)
                supported_identities = {fm} if fm else aliases
            else:
                matches = (name in aliases) or (fm is not None and name == fm)
                supported_identities = aliases | ({fm} if fm else set())

            if matches:
                rep_hit = _representative_hit(agent, entry, fallback_root_id)
                ctrls = resolve_candidate_controls(
                    agent,
                    entry,
                    rep_hit,
                    supported_identities,
                    controls=controls,
                    captured_disabled_overrides=explicit_overrides,
                )
                candidates.append(
                    Candidate(
                        entry=entry,
                        hit=rep_hit,
                        searched=False,
                        overridden=ctrls.is_disabled,
                    )
                )
    return candidates


# --- Headline derivation ---------------------------------------------------


def _assign_states(
    agent: AgentDefinition, candidates: list[Candidate]
) -> tuple[list[tuple[Candidate, HeadlineState]], Candidate | None]:
    """Assign each candidate a state and return them alongside the unique causal winner."""
    searched = [c for c in candidates if c.searched]
    if not searched:
        return [(c, HeadlineState.UNSEARCHED) for c in candidates], None

    valid = [c for c in searched if _is_valid_for_agent(agent, c.entry, c.hit)]
    if not valid:
        return [
            (c, HeadlineState.INVALID if c.searched else HeadlineState.UNSEARCHED)
            for c in candidates
        ], None

    enabled = [c for c in valid if not c.overridden]
    if not enabled:
        return [(c, _fallback_state(agent, c, HeadlineState.DISABLED)) for c in candidates], None

    roles, winner = _active_roles(candidates, agent)
    return [
        (c, roles.get(index, _fallback_state(agent, c, HeadlineState.ACTIVE)))
        for index, c in enumerate(candidates)
    ], winner


# --- Per-candidate state assignment ----------------------------------------


def _active_roles(
    candidates: list[Candidate], agent: AgentDefinition
) -> tuple[dict[int, HeadlineState], Candidate | None]:
    """Map each candidate's position to its collision state and return the causal winner."""
    searched_valid = [
        c
        for c in candidates
        if c.searched and _is_valid_for_agent(agent, c.entry, c.hit) and not c.overridden
    ]
    if not searched_valid:
        return {}, None
    top_rank = max(c.rank for c in searched_valid)
    winners = [c for c in searched_valid if c.rank == top_rank]
    if len(winners) > 1 and agent.id == "opencode":
        top_specificity = max(c.hit.specificity for c in winners)
        winners = [c for c in winners if c.hit.specificity == top_specificity]
    ambiguous = len(winners) > 1
    winner = winners[0] if len(winners) == 1 else None
    multi = len(searched_valid) > 1
    roles: dict[int, HeadlineState] = {}
    for index, candidate in enumerate(candidates):
        if ambiguous:
            roles[index] = _fallback_state(agent, candidate, HeadlineState.AMBIGUOUS)
            continue
        roles[index] = _role_for_active(agent, candidate, winner, multi)
    causal_winner = (
        winner
        if (winner is not None and agent.coexist_policy not in _COEXISTING_POLICIES)
        else None
    )
    return roles, causal_winner


def _role_for_active(
    agent: AgentDefinition,
    candidate: Candidate,
    winner: Candidate | None,
    multi: bool,
) -> HeadlineState:
    if not candidate.searched:
        return HeadlineState.UNSEARCHED
    if not _is_valid_for_agent(agent, candidate.entry, candidate.hit):
        return HeadlineState.INVALID
    if candidate.overridden:
        return HeadlineState.DISABLED
    if candidate == winner:
        if candidate.hit.nested and multi and agent.id != "opencode":
            return HeadlineState.COEXISTS
        return HeadlineState.ACTIVE
    if candidate.hit.nested:
        if agent.id == "opencode":
            return HeadlineState.SHADOWED
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


def _fallback_state(
    agent: AgentDefinition, candidate: Candidate, headline: HeadlineState
) -> HeadlineState:
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
        if not _is_valid_for_agent(agent, candidate.entry, candidate.hit):
            return HeadlineState.INVALID
        return HeadlineState.AMBIGUOUS
    if headline is HeadlineState.DISABLED:
        return HeadlineState.DISABLED if candidate.overridden else HeadlineState.UNSEARCHED
    if not _is_valid_for_agent(agent, candidate.entry, candidate.hit):
        return HeadlineState.INVALID
    if candidate.overridden:
        return HeadlineState.DISABLED
    return headline


# --- Building the output ---------------------------------------------------


def _installation(candidate: Candidate) -> SkillInstallation:
    entry = candidate.entry
    parse = entry.parse
    alias = entrypoint_alias(candidate.entrypoint_path, candidate.hit.is_file or entry.is_file)
    return SkillInstallation(
        name=alias,
        entrypoint_path=candidate.entrypoint_path,
        canonical_path=entry.canonical_path or candidate.entrypoint_path,
        scope=candidate.hit.scope,
        parse_status=parse.status if parse else ParseStatus.UNREADABLE,
        content_hash=entry.content_hash,
        description=parse.description if parse else None,
        frontmatter_name=parse.frontmatter_name if parse else None,
        is_symlink=entry.is_symlink,
        agent_entrypoints=entry.entrypoint_paths or (candidate.entrypoint_path,),
        variant_label=entry.variant_label,
    )


def _winner_label(agent: AgentDefinition, winner: Candidate) -> str:
    """A short, human label for the root that won."""
    root = agent.root_by_id(winner.hit.root_id)
    if root is None:
        return f"the {winner.hit.root_id} root"
    if root.is_absolute:
        return f"the absolute root {root.path}"
    if root.is_project:
        return f"the project root {root.path}"
    if root.base == RootBase.XDG_CONFIG_HOME:
        return f"the global root ~/.config/{root.path}"
    return f"the global root ~/{root.path}"


def _reason(
    agent: AgentDefinition,
    candidate: Candidate,
    state: HeadlineState,
    winner: Candidate | None = None,
    qualification: str | None = None,
) -> str:
    entry = candidate.entry
    if entry.error_code == _CYCLE:
        return "Symlink cycle detected; traversal stopped safely."
    if entry.error_code == _DANGLING:
        return "Dangling symlink; no real target to resolve."
    if entry.error_code == _DENIED or candidate.canonical_key == _UNREADABLE_CANONICAL:
        return "Directory unreadable (permission denied)."
    if state is HeadlineState.DISABLED:
        if qualification and "Denied" in qualification:
            return qualification
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
    if not _is_valid_for_agent(agent, entry, candidate.hit):
        if candidate.hit.nested and candidate.hit.nested_rule_id:
            return candidate.hit.nested_rule_id, Evidence(candidate.hit.evidence)
        return "parser_requires_valid_frontmatter", Evidence.DOCUMENTED
    if state is HeadlineState.AMBIGUOUS and agent.ambiguous_rule_id:
        return agent.ambiguous_rule_id, Evidence(agent.policy_evidence)
    if state is HeadlineState.DISABLED:
        if agent.disabled_rule_id:
            return agent.disabled_rule_id, Evidence.DOCUMENTED
        if agent.id == "codex":
            return "codex_skills_config_disabled", Evidence.DOCUMENTED
        if agent.id == "opencode":
            return "opencode_permission_denied", Evidence.DOCUMENTED
        if agent.id == "omp":
            return "omp_frontmatter_disabled", Evidence.DOCUMENTED
        return f"{agent.id}_disabled", Evidence.DOCUMENTED
    if state is HeadlineState.UNSEARCHED:
        return agent.unsearched_rule_id, Evidence(agent.policy_evidence)
    if state is HeadlineState.SHADOWED and winner is not None:
        return winner.hit.rule_for(winner.hit.is_file), Evidence(winner.hit.evidence)
    return candidate.hit.rule_for(candidate.hit.is_file), Evidence(candidate.hit.evidence)


def _resolution(
    agent: AgentDefinition,
    candidate: Candidate,
    state: HeadlineState,
    winner: Candidate | None = None,
    *,
    controls: ResolvedAgentControls,
    explicit_overrides: frozenset[str] | None = None,
) -> CandidateResolution:
    rule_id, evidence = _rule_and_evidence(agent, candidate, state, winner)
    collision = _COLLISION_FOR_STATE[state]
    if state is HeadlineState.COEXISTS and candidate.hit.nested:
        if agent.id in ("claude", "omp"):
            collision = Collision.QUALIFIED_NAMESPACE
        else:
            collision = Collision.COEXISTING_MERGED
    loadability, _ = is_loadable_for_agent(agent, candidate.entry, candidate.hit)
    hit_names = _hit_identity_names(agent, candidate.entry, candidate.hit)
    ctrls = resolve_candidate_controls(
        agent,
        candidate.entry,
        candidate.hit,
        hit_names,
        controls=controls,
        captured_disabled_overrides=explicit_overrides,
    )
    invocation = ctrls.invocation
    permission = ctrls.permission
    if candidate.overridden or state is HeadlineState.DISABLED:
        invocation = InvocationPolicy.NONE
        permission = PermissionEffect.DENY
    elif state is HeadlineState.INVALID:
        invocation = InvocationPolicy.NONE
        loadability = LoadabilityStatus.INVALID

    return CandidateResolution(
        state=state,
        visibility=_VISIBILITY_FOR_STATE[state],
        collision=collision,
        rule_id=rule_id,
        evidence=evidence,
        reason=_reason(agent, candidate, state, winner, qualification=ctrls.qualification),
        rank=max(candidate.rank, 0),
        installation=_installation(candidate),
        loadability=loadability,
        invocation=invocation,
        permission=permission,
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

    Delegates to the shared rule in :mod: so that
    why, scan and diff can never disagree about a copy's label.
    Ordering is by scope specificity (project before user), then discovery
    order -- *not* by this agent's rank, because scan has no agent to rank
    with. Which copy actually wins is reported by the candidate's state, not
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


def _label_resolution(
    resolution: CandidateResolution, labels: dict[str, str]
) -> CandidateResolution:
    label = labels.get(resolution.installation.entrypoint_path)
    if label == resolution.installation.variant_label:
        return resolution
    return replace(
        resolution,
        installation=replace(resolution.installation, variant_label=label),
    )


def _lexical_display(path: str, home_path: str | Path) -> str:
    """Format path collapsing home prefix purely in-memory without filesystem access."""
    home_str = str(home_path).rstrip("/")
    p_str = str(path)
    if p_str == home_str:
        return "~"
    prefix = home_str + "/"
    if p_str.startswith(prefix):
        return "~/" + p_str[len(prefix) :]
    if home_str.startswith("/private/"):
        alt_home = home_str[len("/private") :]
        if p_str == alt_home:
            return "~"
        if p_str.startswith(alt_home + "/"):
            return "~/" + p_str[len(alt_home) + 1 :]
    elif not home_str.startswith("/private/") and p_str.startswith("/private/"):
        alt_path = p_str[len("/private") :]
        if alt_path == home_str:
            return "~"
        if alt_path.startswith(prefix):
            return "~/" + alt_path[len(prefix) :]
    return p_str


# --- Public entry point ----------------------------------------------------


def resolve_skill(
    name: str,
    agent_id: str,
    cwd: Path,
    home: Path,
    index: DiscoveryIndex | FrozenDiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None,
    *,
    disabled_overrides: frozenset[str] | None = None,
    controls: ResolvedAgentControls | None = None,
    display_paths: Mapping[str, str] | None = None,
) -> ResolutionReport:
    """Resolve ``name`` for ``agent_id`` from ``cwd`` and explain the result."""
    if disabled_overrides is not None:
        if index is None:
            raise ValueError("index must be supplied when disabled_overrides is provided")
        if registry is None:
            raise ValueError("registry must be supplied when disabled_overrides is provided")
    if isinstance(index, FrozenDiscoveryIndex):
        if registry is None:
            raise ValueError("registry must be supplied when index is a FrozenDiscoveryIndex")
        if disabled_overrides is None and controls is None:
            raise ValueError(
                "disabled_overrides must be supplied when index is a FrozenDiscoveryIndex"
            )

    agents = registry if registry is not None else load_registry()
    if agent_id not in agents:
        known = ", ".join(sorted(agents))
        raise KeyError(f"unknown agent '{agent_id}'. Known agents: {known}")
    agent = agents[agent_id]
    discovery = index if index is not None else discover(home, cwd, agents)

    # Determine unified effective controls
    if controls is not None:
        effective_controls = controls
    elif disabled_overrides is not None:
        effective_controls = ResolvedAgentControls(
            agent_id=agent_id,
            disabled_names=disabled_overrides,
        )
    else:
        effective_controls = resolve_agent_controls(agent, home, cwd)

    candidates = _candidates_for(
        agent,
        discovery,
        name,
        controls=effective_controls,
        explicit_overrides=disabled_overrides,
    )
    outcomes, winner = _assign_states(agent, candidates)
    headline = _headline_from_states([state for _candidate, state in outcomes])

    # The winning copy explains every shadow, so it is resolved first and passed
    # to the rest: their reason and rule then name the real cause.

    ordered = _sort_resolutions(
        [
            _resolution(
                agent,
                candidate,
                state,
                winner,
                controls=effective_controls,
                explicit_overrides=disabled_overrides,
            )
            for candidate, state in outcomes
        ]
    )

    labels = {
        candidates[index].entrypoint_path: label
        for index, label in _assign_variant_labels(candidates).items()
    }
    ordered = [_label_resolution(resolution, labels) for resolution in ordered]

    report_notes: list[str] = []
    if not candidates:
        report_notes.append(_NOT_FOUND_NOTE)
    elif headline is HeadlineState.AMBIGUOUS:
        report_notes.append(f"{agent.name} has no documented winner for duplicate names.")

    seen_notes = set(report_notes)
    for n in effective_controls.notes:
        if n not in seen_notes:
            report_notes.append(n)
            seen_notes.add(n)

    if hasattr(discovery, "unreadable_roots"):
        for ur in discovery.unreadable_roots:
            if ur.agent_id == agent.id and ur.detail == "depth_limit_truncated":
                disp = ""
                if getattr(ur, "display_path", ""):
                    disp = ur.display_path
                elif display_paths and ur.path in display_paths:
                    disp = display_paths[ur.path]
                elif isinstance(discovery, FrozenDiscoveryIndex):
                    disp = _lexical_display(ur.path, discovery.home)
                else:
                    disp = paths.display(Path(ur.path))
                note = (
                    f"Discovery traversal in '{disp}' "
                    "was truncated by depth limit; inventory may be incomplete."
                )
                if note not in seen_notes:
                    report_notes.append(note)
                    seen_notes.add(note)

    for c in candidates:
        if not c.entry.traversal_complete:
            reason = c.entry.traversal_error or "denied"
            note = f"Skill content at '{c.entrypoint_path}' is incomplete ({reason})."
            if note not in seen_notes:
                report_notes.append(note)
                seen_notes.add(note)
        cand_load, _ = is_loadable_for_agent(agent, c.entry, c.hit)
        if cand_load is LoadabilityStatus.UNKNOWN:
            note = f"Search root '{c.hit.entrypoint_path}' vendor loadability is unverified."
            if note not in seen_notes:
                report_notes.append(note)
                seen_notes.add(note)

    if winner is not None:
        winner_root = agent.root_by_id(winner.hit.root_id)
        if (
            (winner_root and winner_root.evidence == Evidence.INFERRED)
            or winner.hit.loadability == "unknown"
            or winner.hit.root_id == "omp_agent"
        ):
            note = (
                f"Winning copy at '{winner.entrypoint_path}' is from an "
                "unverified compatibility root; vendor loadability is unverified."
            )
            if note not in seen_notes:
                report_notes.append(note)
                seen_notes.add(note)

    return ResolutionReport(
        skill_name=name,
        agent=agent.id,
        agent_name=agent.name,
        cwd=str(cwd),
        collision_policy=agent.collision_policy,
        policy_evidence=agent.policy_evidence,
        headline=headline,
        candidates=tuple(ordered),
        notes=tuple(report_notes),
        found=bool(candidates),
    )


__all__ = ["Candidate", "entrypoint_alias", "lookup_name_for_entry", "resolve_skill"]
