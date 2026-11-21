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

from skill_lens.core.config import resolve_agent_controls
from skill_lens.core.discovery import DiscoveredEntry, DiscoveryIndex, canonical_key, discover
from skill_lens.core.resolver import lookup_name_for_entry, resolve_skill
from skill_lens.core.scanner import ScanEntry, build_scan_report
from skill_lens.core.system import live_discovery
from skill_lens.models.resolution import ResolutionReport
from skill_lens.models.search import MATCH_RANK, MatchField, SearchHit, SearchReport
from skill_lens.registry.loader import AgentDefinition, load_registry

#: Longest excerpt shown for one result, in characters (cut ends marked with ``…``).
SNIPPET_WIDTH = 80
#: How many characters of context to keep before the match inside an excerpt.
_SNIPPET_LEAD = 20
_ELLIPSIS = "…"
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


def snippet(text: str | None, needle: str) -> str:
    """A one-line excerpt of ``text`` around the first match of ``needle``.

    The excerpt starts at the line that holds the match, so the reader sees the
    matching sentence rather than the top of the file. That offset is only
    trusted when casefolding left the text's length unchanged (casefold never
    shrinks text, so equal length means the offsets map one to one); otherwise
    the excerpt starts at the top. After cleaning, the cleaned query is found
    again so the window can be placed on it. If casefolding lengthened the
    cleaned text, that offset is approximate (it can be late by the number of
    expanded characters before the match), so it is kept inside the text; with
    no match at all (an empty needle) the first characters are shown.
    """
    if not text:
        return ""
    folded = text.casefold()
    source = text
    position = folded.find(needle.casefold()) if needle else -1
    if position >= 0 and len(folded) == len(text):
        source = text[text.rfind("\n", 0, position) + 1 :]
    cleaned = _clean(source)
    if not cleaned:
        return ""
    cleaned_folded = cleaned.casefold()
    cleaned_needle = _clean(needle).casefold()
    at = cleaned_folded.find(cleaned_needle) if cleaned_needle else -1
    return _window(cleaned, min(at, len(cleaned) - 1))


def refit(excerpt: str, query: str, width: int) -> str:
    """Re-cut an excerpt for a narrower column so the matched words stay in view.

    The JSON keeps the full 80-character excerpt; a terminal column is often
    narrower, and a plain right-hand cut would hide a match in the middle of
    the line. With no match in the excerpt (a name match shows the
    description) the start is kept.
    """
    if width < 1:
        return ""
    if len(excerpt) <= width:
        return excerpt
    needle = _clean(query).casefold()
    at = excerpt.casefold().find(needle) if needle else -1
    return _window(excerpt, min(at, len(excerpt) - 1), width=width, lead=4)


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


def _match(
    row: ScanEntry, entry: DiscoveredEntry | None, needle: str
) -> tuple[MatchField, int] | None:
    """The field that matched and, for name matches, how closely (0 exact, 1 prefix, 2 other)."""
    names = [row.name]
    alias = _frontmatter_name(entry, row.name)
    if alias is not None:
        names.append(alias)
    folded_names = [name.casefold() for name in names]
    if any(needle in name for name in folded_names):
        if any(name == needle for name in folded_names):
            return MatchField.NAME, 0
        if any(name.startswith(needle) for name in folded_names):
            return MatchField.NAME, 1
        return MatchField.NAME, 2
    if row.description and needle in row.description.casefold():
        return MatchField.DESCRIPTION, 0
    body = entry.parse.body if entry is not None and entry.parse is not None else ""
    if body and needle in body.casefold():
        return MatchField.BODY, 0
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

    ranked: list[tuple[int, int, int, SearchHit]] = []
    for position, row in enumerate(scan.skills):
        if agent_id is not None and agent_id not in row.agents:
            continue
        entry = entries.get(row.canonical_path)
        found = _match(row, entry, needle)
        if found is None:
            continue
        matched, closeness = found
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
        ranked.append((MATCH_RANK[matched], closeness, position, hit))
    ranked.sort(key=lambda item: item[:3])
    hits = [hit for *_order, hit in ranked]

    if agent is not None and agent_id is not None:
        controls = resolve_agent_controls(agent, home, cwd)
        reports: dict[str, ResolutionReport] = {}
        stated: list[SearchHit] = []
        for hit in hits:
            entry = entries.get(hit.canonical_path)
            lookup = lookup_name_for_entry(entry, agent) if entry is not None else hit.name
            if lookup not in reports:
                reports[lookup] = resolve_skill(
                    lookup,
                    agent_id,
                    cwd,
                    home,
                    index=discovery,
                    registry=agents,
                    controls=controls,
                )
            stated.append(replace(hit, state=_copy_state(reports[lookup], hit.canonical_path)))
        hits = stated

    return SearchReport(
        query=normalise_query(query),
        home=str(home),
        cwd=str(cwd),
        results=tuple(hits),
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
) -> SearchReport:
    """Search the live machine (used by the CLI).

    The query and the agent id are checked *before* the filesystem walk, so a
    typo costs an error message, not a crawl.
    """
    normalised = normalise_query(query)
    agents = registry if registry is not None else load_registry()
    if agent_id is not None:
        _require_agent(agent_id, agents)
    chosen = index if index is not None else live_discovery(cwd, agents)
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
