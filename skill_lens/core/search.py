"""``skill-lens search <query>``: which of my skills can help with X?

Pure function over one discovery pass, like ``compare``. Every row is exactly a
``scan`` row (one per skill copy), so names, scopes, agents and order agree with
the rest of the tool. A copy matches when the query appears, case-insensitively,
in its name (folder name or frontmatter ``name``), its description, or its
``SKILL.md`` body; the first of those fields that matches decides the rank.

Nothing here reads a file: the bodies were already parsed by discovery. Nothing
here writes anything either.
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from skill_lens.core.config import ResolvedAgentControls, resolve_agent_controls
from skill_lens.core.discovery import DiscoveredEntry, DiscoveryIndex, canonical_key, discover
from skill_lens.core.resolver import lookup_names_for_entry, resolve_skill
from skill_lens.core.scanner import ScanEntry, build_scan_report
from skill_lens.core.system import live_discovery
from skill_lens.models.resolution import ResolutionReport
from skill_lens.models.search import MATCH_RANK, LookupState, MatchField, SearchHit, SearchReport
from skill_lens.registry.loader import AgentDefinition, load_registry

#: Longest excerpt shown for one result, in characters (cut ends marked with ``…``).
SNIPPET_WIDTH = 80
#: How many characters of context to keep before the match inside an excerpt.
_SNIPPET_LEAD = 20
_ELLIPSIS = "…"
#: Raw characters kept after the match before cleaning an excerpt.
_SNIPPET_SOURCE_LOOKAHEAD = 4096
#: Control characters (C0, DEL, C1), including tab, newline and ESC. They become
#: spaces, so text can neither break the one-line layout nor reach the terminal
#: as an escape sequence.
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_SPACES = re.compile(r"\s+")


def normalise_query(query: str) -> str:
    """Strip the query; an empty one is a usage error, raised before any walk."""
    stripped = query.strip()
    if not stripped:
        raise ValueError("search query must not be empty")
    return stripped


def _clean(text: str) -> str:
    """One display line: control characters out, whitespace runs collapsed."""
    return _SPACES.sub(" ", _CONTROL.sub(" ", text)).strip()


def _window(text: str, at: int, width: int = SNIPPET_WIDTH, lead: int = _SNIPPET_LEAD) -> str:
    """At most ``width`` characters of ``text`` showing offset ``at``."""
    if len(text) <= width:
        return text
    if at < 0:
        return text[: width - 1] + _ELLIPSIS
    start = max(0, at - lead)
    end = start + width
    if end > len(text):
        end = len(text)
        start = end - width
    segment = text[start:end]
    if start > 0:
        segment = _ELLIPSIS + segment[1:]
    if end < len(text):
        segment = segment[:-1] + _ELLIPSIS
    return segment


#: Original-text characters examined per casefold search step.
_FOLD_CHUNK = 8192


def _folded_find(text: str, needle: str) -> int:
    """Offset of ``needle`` in ``text.casefold()`` without folding all of it.

    Only chunks up to and including the match are folded, and a short overlap
    preserves matches that straddle a chunk boundary. ``casefold`` is applied
    per character, so folding chunks and joining the results is the same as
    folding the whole string.
    """
    if not needle:
        return -1
    folded_before = 0
    overlap = ""
    for start in range(0, len(text), _FOLD_CHUNK):
        folded_chunk = text[start : start + _FOLD_CHUNK].casefold()
        haystack = overlap + folded_chunk
        found = haystack.find(needle)
        if found >= 0:
            return folded_before - len(overlap) + found
        keep = min(len(needle) - 1, len(haystack))
        overlap = haystack[-keep:] if keep else ""
        folded_before += len(folded_chunk)
    return -1


def _original_offset(text: str, folded_offset: int) -> int:
    """Map a casefolded offset back to the original string.

    The scan stops at the target offset and keeps only a counter, so a body of
    one million expanding characters costs constant extra space rather than one
    Python integer per code point.
    """
    if folded_offset <= 0:
        return 0
    position = 0
    for index, character in enumerate(text):
        position += len(character.casefold())
        if position > folded_offset:
            return index
    return max(0, len(text) - 1)


def _first_match_offset(text: str, needle: str) -> int:
    """Offset of ``needle`` in ``text``, using its folded form to find it."""
    at = _folded_find(text, needle)
    if at < 0:
        return -1
    return _original_offset(text, at)


def snippet(text: str | None, needle: str) -> str:
    """A one-line excerpt of ``text`` around the first match of ``needle``.

    The excerpt starts at the line that holds the match, so the reader sees the
    matching sentence rather than the top of the file. Casefold expansion is
    mapped back to the original offsets, so a body whose earlier characters
    expand (for example many ``ß`` before the match) still shows the match
    instead of a window computed from the folded length. After cleaning, the
    cleaned query is found again so the window can be placed on it; with no
    match at all (an empty needle) the first characters are shown.
    """
    if not text:
        return ""
    position = _folded_find(text, needle.casefold()) if needle else -1
    if position >= 0:
        original = _original_offset(text, position)
        start = text.rfind("\n", 0, original) + 1
        # Cleaning the rest of a huge file would allocate its whole suffix even
        # though only one excerpt width is shown. Keep ample raw lookahead (a
        # cleaned character never expands), so normal bodies are unchanged; a
        # query longer than the usual excerpt still keeps its own match.
        lookahead = max(_SNIPPET_SOURCE_LOOKAHEAD, len(needle) + 1)
        source = text[start : original + lookahead]
    else:
        source = text
    cleaned = _clean(source)
    if not cleaned:
        return ""
    cleaned_needle = _clean(needle).casefold()
    at = _first_match_offset(cleaned, cleaned_needle) if cleaned_needle else -1
    return _window(cleaned, at)


def refit(excerpt: str, query: str, width: int) -> str:
    """Re-cut an excerpt for a narrower column so the matched words stay in view.

    The JSON keeps the full 80-character excerpt; a terminal column is often
    narrower, and a plain right-hand cut would hide a match in the middle of
    the line. With no match in the excerpt (a name match shows the
    description) the start is kept. The offset is mapped through casefold
    expansion exactly as :func:`snippet` does.
    """
    if width < 1:
        return ""
    if len(excerpt) <= width:
        return excerpt
    needle = _clean(query).casefold()
    at = _first_match_offset(excerpt, needle) if needle else -1
    return _window(excerpt, at, width=width, lead=4)


def _require_agent(agent_id: str, agents: dict[str, AgentDefinition]) -> AgentDefinition:
    """Fetch one definition or raise the same ``KeyError`` sentence as ``compare``."""
    definition = agents.get(agent_id)
    if definition is None:
        known = ", ".join(sorted(agents))
        raise KeyError(f"unknown agent '{agent_id}'. Known agents: {known}")
    return definition


def _frontmatter_name(entry: DiscoveredEntry | None, folder_name: str) -> str | None:
    """The frontmatter ``name`` when it exists and differs from the folder name."""
    if entry is None or entry.parse is None:
        return None
    name = entry.parse.frontmatter_name
    if not name or name == folder_name:
        return None
    return name


def _alias_names(
    row: ScanEntry,
    entry: DiscoveredEntry | None,
    agent_ids: tuple[str, ...],
    agents: dict[str, AgentDefinition],
) -> tuple[str, ...]:
    """Every name this result can be found by for the agents in play.

    The row name and frontmatter name are kept because they are what search has
    always recognised. Alongside them, each selected agent contributes every
    alias it can actually use for the copy -- a symlink farm can expose the same
    physical skill under different folder names, and ``why`` resolves each name
    separately.
    """
    names: list[str] = []

    def add(name: str | None) -> None:
        if name and name not in names:
            names.append(name)

    add(row.name)
    add(_frontmatter_name(entry, row.name))
    if entry is not None:
        for agent_id in agent_ids:
            agent = agents.get(agent_id)
            if agent is None:
                continue
            for name in lookup_names_for_entry(entry, agent):
                add(name)
    return tuple(names)


def _match(
    row: ScanEntry,
    entry: DiscoveredEntry | None,
    needle: str,
    aliases: tuple[str, ...],
) -> tuple[MatchField, int, tuple[str, ...]] | None:
    """The field that matched, its closeness, and the names that matched.

    Closeness is 0 for an exact name, 1 for a prefix, 2 for any other name
    substring. For a name match, every alias at the best closeness is returned
    so the selected state can follow the alias the query actually named rather
    than a representative one.
    """
    folded_names = [(name, name.casefold()) for name in aliases]
    name_matches = [
        (0 if folded == needle else 1 if folded.startswith(needle) else 2, name)
        for name, folded in folded_names
        if needle in folded
    ]
    if name_matches:
        closeness = min(rank for rank, _name in name_matches)
        matched = tuple(name for rank, name in name_matches if rank == closeness)
        return MatchField.NAME, closeness, matched
    if row.description and needle in row.description.casefold():
        return MatchField.DESCRIPTION, 0, ()
    body = entry.parse.body if entry is not None and entry.parse is not None else ""
    if _folded_find(body, needle) >= 0:
        return MatchField.BODY, 0, ()
    return None


def _copy_state(report: ResolutionReport, key: str) -> str:
    """This copy's state in one resolution report (the TUI's Home rule).

    Candidates are matched by canonical path; an unresolved copy (dangling link,
    cycle) is keyed by its entrypoint, so that is the fallback. Several
    entrypoints of one copy can have different states; all distinct ones are
    shown rather than inventing a winner.
    """
    matches = [c for c in report.candidates if c.installation.canonical_path == key]
    if not matches:
        matches = [c for c in report.candidates if c.installation.entrypoint_path == key]
    if not matches:
        return "unknown"
    states: list[str] = []
    for candidate in matches:
        if candidate.state.value not in states:
            states.append(candidate.state.value)
    return ", ".join(states)


def _lookup_states(
    hit: SearchHit,
    entry: DiscoveredEntry | None,
    agent_ids: tuple[str, ...],
    *,
    agents: dict[str, AgentDefinition],
    discovery: DiscoveryIndex,
    home: Path,
    cwd: Path,
    controls_cache: dict[str, ResolvedAgentControls],
    report_cache: dict[tuple[str, str], ResolutionReport],
) -> tuple[LookupState, ...]:
    """State of this copy under every lookup name each agent can use for it.

    Resolution is per agent *and* per name: the same physical copy can be
    ACTIVE under one alias and SHADOWED under another (a real symlink farm
    case). Resolving only the highest-ranked representative alias -- what search
    used to do -- made a match on a different alias disagree with ``why``.
    """
    states: list[LookupState] = []
    for agent_id in agent_ids:
        agent = agents.get(agent_id)
        if agent is None:
            continue
        controls = controls_cache.get(agent_id)
        if controls is None:
            controls = resolve_agent_controls(agent, home, cwd)
            controls_cache[agent_id] = controls
        names = lookup_names_for_entry(entry, agent) if entry is not None else ()
        if not names:
            names = (hit.name,)
        for name in names:
            key = (agent_id, name)
            report = report_cache.get(key)
            if report is None:
                report = resolve_skill(
                    name,
                    agent_id,
                    cwd,
                    home,
                    index=discovery,
                    registry=agents,
                    controls=controls,
                )
                report_cache[key] = report
            states.append(LookupState(agent_id, name, _copy_state(report, hit.canonical_path)))
    states.sort(key=lambda item: (item.agent, item.name))
    return tuple(states)


def _selected_state(states: tuple[LookupState, ...], matched_names: tuple[str, ...]) -> str:
    """Selected-agent state, preferring the alias the query actually matched.

    A name hit on a usable alias shows that alias's own state, so
    ``search working-alias --agent opencode`` agrees with
    ``why working-alias --agent opencode``. Only aliases at the best closeness
    tier are used, so an exact name wins over a longer prefix or substring. A
    description/body hit has no matched alias, so every distinct state is shown
    -- mixed states are explicit rather than silently reduced to a
    representative alias's answer.
    """
    chosen: list[str] = []
    by_name = {item.name: item.state for item in states}
    for name in matched_names:
        state = by_name.get(name)
        if state is not None and state not in chosen:
            chosen.append(state)
    if chosen:
        return ", ".join(chosen)
    for item in states:
        if item.state not in chosen:
            chosen.append(item.state)
    return ", ".join(chosen) or "unknown"


def build_search_report(
    query: str,
    home: Path,
    cwd: Path,
    *,
    agent_id: str | None = None,
    index: DiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None,
) -> SearchReport:
    """Search one discovery pass and rank the matching copies."""
    needle = normalise_query(query).casefold()
    agents = registry if registry is not None else load_registry()
    agent = _require_agent(agent_id, agents) if agent_id is not None else None
    discovery = index if index is not None else discover(home, cwd, agents)
    scan = build_scan_report(home, cwd, index=discovery, registry=agents)
    entries = {canonical_key(entry): entry for entry in discovery.entries}

    ranked: list[tuple[int, int, int, SearchHit, tuple[str, ...]]] = []
    for position, row in enumerate(scan.skills):
        if agent_id is not None and agent_id not in row.agents:
            continue
        entry = entries.get(row.canonical_path)
        selected = (agent_id,) if agent_id is not None else row.agents
        found = _match(row, entry, needle, _alias_names(row, entry, selected, agents))
        if found is None:
            continue
        matched, closeness, matched_names = found
        if matched is MatchField.NAME:
            excerpt = snippet(row.description, "")
        elif matched is MatchField.DESCRIPTION:
            excerpt = snippet(row.description, needle)
        else:
            body = entry.parse.body if entry is not None and entry.parse is not None else ""
            excerpt = snippet(body, needle)
        hit = SearchHit(
            name=row.name,
            match=matched,
            snippet=excerpt,
            scope=row.scope,
            canonical_path=row.canonical_path,
            agents=row.agents,
            parse_status=row.parse_status,
            frontmatter_name=_frontmatter_name(entry, row.name),
            variant_label=row.variant_label,
        )
        ranked.append((MATCH_RANK[matched], closeness, position, hit, matched_names))
    ranked.sort(key=lambda item: item[:3])
    hits = [(hit, matched_names) for *_order, hit, matched_names in ranked]

    controls_cache: dict[str, ResolvedAgentControls] = {}
    report_cache: dict[tuple[str, str], ResolutionReport] = {}
    stated: list[SearchHit] = []
    for hit, matched_names in hits:
        entry = entries.get(hit.canonical_path)
        selected = (agent_id,) if agent_id is not None else hit.agents
        states = _lookup_states(
            hit,
            entry,
            selected,
            agents=agents,
            discovery=discovery,
            home=home,
            cwd=cwd,
            controls_cache=controls_cache,
            report_cache=report_cache,
        )
        state = _selected_state(states, matched_names) if agent_id is not None else None
        stated.append(replace(hit, state=state, states=states))

    return SearchReport(
        query=normalise_query(query),
        home=str(home),
        cwd=str(cwd),
        results=tuple(stated),
        agent=agent_id,
        agent_name=agent.name if agent is not None else None,
        unreadable=scan.unreadable,
    )


def run_search(
    query: str,
    cwd: Path | None = None,
    *,
    agent_id: str | None = None,
    index: DiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None,
    max_payload_bytes: int | None = None,
) -> SearchReport:
    """Search the live machine (used by the CLI).

    The query and the agent id are checked *before* the filesystem walk, so a
    typo costs an error message, not a crawl. ``max_payload_bytes`` is the same
    payload budget the TUI capture uses; the CLI passes its production default,
    while an injected ``index`` is already-discovered data and is not rewalked.
    """
    normalised = normalise_query(query)
    agents = registry if registry is not None else load_registry()
    if agent_id is not None:
        _require_agent(agent_id, agents)
    chosen = (
        index
        if index is not None
        else live_discovery(cwd, agents, max_payload_bytes=max_payload_bytes)
    )
    return build_search_report(
        normalised,
        Path(chosen.home),
        Path(chosen.cwd),
        agent_id=agent_id,
        index=chosen,
        registry=agents,
    )


__all__ = [
    "SNIPPET_WIDTH",
    "build_search_report",
    "normalise_query",
    "refit",
    "run_search",
    "snippet",
]
