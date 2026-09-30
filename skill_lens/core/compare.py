"""``skill-lens compare --agent A --agent B``: pairwise capability surface.

Pure function over one discovery pass. Both agents are read from the *same*
:class:`~skill_lens.core.discovery.DiscoveryIndex` so the comparison is
consistent: a skill counts as shared when the two entrypoints resolve to one
canonical target, or -- when they are separate files -- to identical bytes.
Names that exist in both agents with genuinely different content are called
out as divergences, exactly the state where ``skill-lens diff`` is the
follow-up command.
"""

from __future__ import annotations

from pathlib import Path

from skill_lens.core.discovery import DiscoveredEntry, DiscoveryIndex, discover
from skill_lens.core.system import live_discovery
from skill_lens.models.compare import CompareEntry, CompareReport
from skill_lens.models.enums import CompareRelation
from skill_lens.registry.loader import AgentDefinition, load_registry


def build_compare_report(
    agent_a: str,
    agent_b: str,
    home: Path,
    cwd: Path,
    index: DiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None,
) -> CompareReport:
    """Compare the skills two agents can reach, name by name.

    Raises ``KeyError`` for an unknown agent id -- the CLI turns that into
    exit code ``2``. ``agent_a`` decides which side of every entry the ``*_a``
    fields describe, so ``claude vs codex`` and ``codex vs claude`` are honest
    mirrors of one another, not re-judged.
    """
    agents = registry if registry is not None else load_registry()
    definition_a = _require(agent_a, agents)
    definition_b = _require(agent_b, agents)

    discovery = index if index is not None else discover(home, cwd, agents)

    by_agent: dict[str, dict[str, list[DiscoveredEntry]]] = {agent_a: {}, agent_b: {}}
    for entry in discovery.entries:
        for agent_id in (agent_a, agent_b):
            if any(hit.agent_id == agent_id for hit in entry.hits):
                by_agent[agent_id].setdefault(entry.name, []).append(entry)

    entries = [
        _classify(
            name,
            by_agent[agent_a].get(name, []),
            by_agent[agent_b].get(name, []),
            agent_a,
            agent_b,
        )
        for name in sorted(set(by_agent[agent_a]) | set(by_agent[agent_b]))
    ]
    notes: list[str] = []
    diverged = [entry.name for entry in entries if entry.relation is CompareRelation.DIVERGED]
    if diverged:
        joined = ", ".join(f"'{name}'" for name in diverged)
        notes.append(
            f"names where {agent_a} and {agent_b} read different copies: {joined}. "
            "Run 'skill-lens diff <name>' to see the text differences."
        )

    return CompareReport(
        agent_a=agent_a,
        agent_b=agent_b,
        agent_a_name=definition_a.name,
        agent_b_name=definition_b.name,
        home=str(home),
        cwd=str(cwd),
        entries=tuple(entries),
        notes=tuple(notes),
    )


def _require(agent_id: str, agents: dict[str, AgentDefinition]) -> AgentDefinition:
    """Fetch one definition or raise the CLI-friendly ``KeyError``."""
    definition = agents.get(agent_id)
    if definition is None:
        known = ", ".join(sorted(agents))
        raise KeyError(f"unknown agent '{agent_id}'. Known agents: {known}")
    return definition


def _entrypoint_for(agent_id: str, entry: DiscoveredEntry) -> str | None:
    """The path *this* agent sees for this entry (its own hit, not the first)."""
    for hit in entry.hits:
        if hit.agent_id == agent_id:
            return hit.entrypoint_path
    return None


def _classify(
    name: str,
    entries_a: list[DiscoveredEntry],
    entries_b: list[DiscoveredEntry],
    agent_a: str,
    agent_b: str,
) -> CompareEntry:
    """One name, two agents: shared copy, divergent copies, or only one side.

    An agent that reaches a name through *several* canonical copies (its own
    ambiguous duplicates) is compared on the first entry discovery produced;
    ``why`` and ``diff`` are the tools for that mess, ``compare`` only needs
    to be honest that both sides exist.
    """
    if entries_a and entries_b:
        canonicals_b = {entry.canonical_path for entry in entries_b if entry.canonical_path}
        shared = next((entry for entry in entries_a if entry.canonical_path in canonicals_b), None)
        if shared is not None:
            mirror = next(e for e in entries_b if e.canonical_path == shared.canonical_path)
            return CompareEntry(
                name=name,
                relation=CompareRelation.SHARED,
                path_a=_entrypoint_for(agent_a, shared),
                path_b=_entrypoint_for(agent_b, mirror),
                canonical_a=shared.canonical_path,
                canonical_b=mirror.canonical_path,
            )
        # Separate canonical files. They still describe the same capability
        # when the bytes match -- hashing a copy is what discovery already
        # does for `diff`, so reuse it here instead of sending the user to
        # `diff` for copies that would then report "no differences".
        hash_a = entries_a[0].content_hash
        hash_b = entries_b[0].content_hash
        if hash_a is not None and hash_a == hash_b:
            return CompareEntry(
                name=name,
                relation=CompareRelation.SHARED,
                path_a=_entrypoint_for(agent_a, entries_a[0]),
                path_b=_entrypoint_for(agent_b, entries_b[0]),
                canonical_a=entries_a[0].canonical_path,
                canonical_b=entries_b[0].canonical_path,
            )
        return CompareEntry(
            name=name,
            relation=CompareRelation.DIVERGED,
            path_a=_entrypoint_for(agent_a, entries_a[0]),
            path_b=_entrypoint_for(agent_b, entries_b[0]),
            canonical_a=entries_a[0].canonical_path,
            canonical_b=entries_b[0].canonical_path,
        )
    only_a = bool(entries_a)
    side = entries_a if only_a else entries_b
    return CompareEntry(
        name=name,
        relation=CompareRelation.ONLY_A if only_a else CompareRelation.ONLY_B,
        path_a=_entrypoint_for(agent_a, side[0]) if only_a else None,
        path_b=_entrypoint_for(agent_b, side[0]) if not only_a else None,
        canonical_a=side[0].canonical_path if only_a else None,
        canonical_b=side[0].canonical_path if not only_a else None,
    )


def run_compare(agent_a: str, agent_b: str, cwd: Path | None = None) -> CompareReport:
    """Compare two agents against the live machine (used by the CLI).

    Agent ids are validated *before* the filesystem walk, so a typo costs an
    error message, not a crawl. The loaded registry is handed down, too.
    """
    agents = load_registry()
    _require(agent_a, agents)
    _require(agent_b, agents)
    index = live_discovery(cwd, agents)
    return build_compare_report(
        agent_a, agent_b, Path(index.home), Path(index.cwd), index=index, registry=agents
    )
