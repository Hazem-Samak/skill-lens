"""``skill-lens search`` (issue #7): ranking, filters, states, excerpts, JSON and safety.

Every test builds its own skills under the synthetic ``mock_home`` fixture and
runs the CLI with ``--sandbox``; nothing here reads the real ``$HOME``.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

import skill_lens.cli as cli_module
import skill_lens.core.discovery as discovery_module
import skill_lens.core.search as search_module
from skill_lens.cli import app
from skill_lens.core.discovery import (
    SkillPayloadTooLarge,
    StandaloneQualificationTooLarge,
    UnreadableRoot,
    discover,
)
from skill_lens.core.parser import parse_skill_document
from skill_lens.core.resolver import resolve_skill
from skill_lens.core.scanner import build_scan_report
from skill_lens.core.search import (
    SNIPPET_WIDTH,
    build_search_report,
    normalise_query,
    refit,
    run_search,
    snippet,
)
from skill_lens.core.snapshot import DEFAULT_MAX_SNAPSHOT_BYTES
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
from skill_lens.models.search import LookupState, MatchField, SearchHit, SearchReport
from skill_lens.registry.loader import load_registry
from skill_lens.render import render_search
from tests.fixtures.builders import make_skill, symlink, write_skill

_ANSI = re.compile(rb"\x1b\[[0-9;]*m")


class _PlainRunner(CliRunner):
    """Strip colour codes so assertions are about text, whatever the shell forces."""

    def invoke(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        result = super().invoke(*args, **kwargs)
        result.stdout_bytes = _ANSI.sub(b"", result.stdout_bytes or b"")
        result.stderr_bytes = _ANSI.sub(b"", result.stderr_bytes or b"")
        return result


runner = _PlainRunner()


def _library(home: Path) -> None:
    """One skill per tier, plus name matches of every closeness and a plugin."""
    claude = home / ".claude" / "skills"
    make_skill(claude / "database", "database", "Talk to the store.")
    make_skill(claude / "database-tools", "database-tools", "Helpers.")
    make_skill(claude / "my-database-kit", "my-database-kit", "A kit.")
    make_skill(home / ".agents" / "skills" / "db-migrate", "db-migrate", "Plan DATABASE moves.")
    make_skill(claude / "deploy", "deploy", "Ship it.", body="Run the database checks.\n")
    make_skill(claude / "notes", "notes", "Notes.", body="Nothing relevant.\n")
    plugin = home / ".codex" / ".tmp" / "plugins" / "plug" / "skills" / "plugskill"
    make_skill(plugin, "plugskill", "Plugin helper.", body="Uses the database driver.\n")


def _search(home: Path, *args: str) -> object:
    return runner.invoke(app, ["search", *args, "--sandbox", str(home)])


def _json(home: Path, *args: str) -> dict:  # type: ignore[type-arg]
    result = _search(home, *args, "--json")
    assert result.exit_code == 0, result.stdout + result.stderr  # type: ignore[attr-defined]
    return json.loads(result.stdout)  # type: ignore[attr-defined]


# --- ranking -----------------------------------------------------------------


def test_tiers_rank_name_then_description_then_body(mock_home: Path) -> None:
    _library(mock_home)
    home = mock_home.resolve()
    report = build_search_report("database", home, home)

    assert [(hit.name, hit.match) for hit in report.results] == [
        ("database", MatchField.NAME),
        ("database-tools", MatchField.NAME),
        ("my-database-kit", MatchField.NAME),
        ("db-migrate", MatchField.DESCRIPTION),
        *[
            (row.name, MatchField.BODY)
            for row in build_scan_report(home, home).skills
            if row.name in {"deploy", "plugskill"}
        ],
    ]
    assert report.counts() == {"name": 3, "description": 1, "body": 2}
    assert "notes" not in {hit.name for hit in report.results}


def test_inside_the_name_tier_exact_beats_prefix_beats_contains(mock_home: Path) -> None:
    claude = mock_home / ".claude" / "skills"
    # Created so that scan order (alphabetical) is the reverse of the closeness order.
    make_skill(claude / "a-sql-helper", "a-sql-helper", "Contains.")
    make_skill(claude / "sql", "sql", "Exact.")
    make_skill(claude / "sql-lint", "sql-lint", "Prefix.")
    home = mock_home.resolve()
    names = [hit.name for hit in build_search_report("SQL", home, home).results]
    assert names == ["sql", "sql-lint", "a-sql-helper"]


def test_matching_ignores_case_and_keeps_phrases_whole(mock_home: Path) -> None:
    _library(mock_home)
    home = mock_home.resolve()
    assert [h.name for h in build_search_report("plan database", home, home).results] == [
        "db-migrate"
    ]
    assert build_search_report("database plan", home, home).results == ()


def test_a_frontmatter_name_is_searched_in_the_name_tier(mock_home: Path) -> None:
    make_skill(mock_home / ".codex" / "skills" / "alias-one", "shared", "Codex alias.")
    home = mock_home.resolve()
    (hit,) = build_search_report("shared", home, home).results
    assert hit.name == "alias-one"
    assert hit.match is MatchField.NAME
    assert hit.frontmatter_name == "shared"


def test_plugin_skills_are_searched_and_labelled(mock_home: Path) -> None:
    _library(mock_home)
    payload = _json(mock_home, "driver")
    (result,) = payload["results"]
    assert result["name"] == "plugskill"
    assert result["scope"] == "plugin"


def test_a_broken_fence_is_still_searched_as_body(mock_home: Path) -> None:
    write_skill(
        mock_home / ".claude" / "skills" / "broken",
        "---\nname: broken\ndescription: secretword here\n# body\n",
    )
    (result,) = _json(mock_home, "secretword")["results"]
    assert result["name"] == "broken"
    assert result["match"] == "body"
    assert result["parse_status"] != "valid"


def test_a_dangling_link_matches_by_name_only(mock_home: Path) -> None:
    try:
        symlink(mock_home / "nowhere", mock_home / ".claude" / "skills" / "ghostly")
    except OSError:
        pytest.skip("this system cannot create symlinks")
    (result,) = _json(mock_home, "ghostly")["results"]
    assert result["match"] == "name"
    assert result["snippet"] == ""


# --- agent filter and states --------------------------------------------------


def _personal_and_project(home: Path) -> Path:
    project = home / "project"
    (project / ".git").mkdir(parents=True)
    make_skill(home / ".claude" / "skills" / "deploy", "deploy", "Personal.", body="ship now\n")
    make_skill(project / ".claude" / "skills" / "deploy", "deploy", "Project.", body="ship it\n")
    make_skill(home / ".codex" / "skills" / "codex-only", "codex-only", "Ship from codex.")
    return project


def test_agent_filter_keeps_reachable_copies_and_adds_their_state(mock_home: Path) -> None:
    project = _personal_and_project(mock_home)
    payload = _json(mock_home, "ship", "--agent", "claude", "--cwd", str(project))

    assert payload["agent"] == "claude"
    states = {Path(r["canonical_path"]).parts[-4]: r["state"] for r in payload["results"]}
    assert states == {"home": "ACTIVE", "project": "SHADOWED"}
    assert "codex-only" not in {r["name"] for r in payload["results"]}
    assert payload["total"] == 2
    assert payload["counts"] == {"body": 2, "description": 0, "name": 0}


def test_without_an_agent_there_is_no_state(mock_home: Path) -> None:
    project = _personal_and_project(mock_home)
    payload = _json(mock_home, "ship", "--cwd", str(project))
    assert payload["agent"] is None
    assert {r["state"] for r in payload["results"]} == {None}
    assert "codex-only" in {r["name"] for r in payload["results"]}


def test_frontmatter_name_agents_resolve_by_their_lookup_name(mock_home: Path) -> None:
    make_skill(mock_home / ".codex" / "skills" / "alias-one", "shared", "Codex alias.")
    (result,) = _json(mock_home, "alias", "--agent", "codex")["results"]
    assert result["state"] == "ACTIVE"


def test_two_aliases_for_one_lookup_name_are_both_ambiguous(mock_home: Path) -> None:
    make_skill(mock_home / ".codex" / "skills" / "alias-one", "shared", "First alias.")
    make_skill(mock_home / ".codex" / "skills" / "alias-two", "shared", "Second alias.")
    results = _json(mock_home, "alias", "--agent", "codex")["results"]
    assert [r["state"] for r in results] == ["AMBIGUOUS", "AMBIGUOUS"]


def _alias_collision(home: Path) -> None:
    """A copy reached by two aliases, one of which a competing copy outranks."""
    working = home / ".claude" / "skills" / "working-alias"
    make_skill(working, "working-alias", "The working alias copy.", body="Run the real work.\n")
    make_skill(
        home / ".config" / "opencode" / "skills" / "primary",
        "primary",
        "The competing primary copy.",
        body="Run the competing work.\n",
    )
    try:
        symlink(working, home / ".agents" / "skills" / "primary")
    except OSError:
        pytest.skip("this system cannot create symlinks")


def test_selected_agent_state_follows_the_matching_alias(mock_home: Path) -> None:
    """Regression: the representative alias was ``primary`` and wrongly SHADOWED.

    ``why working-alias --agent opencode`` reports ACTIVE because that exact
    alias is reachable directly through ``~/.claude/skills``. Search used to
    resolve only the highest-ranked alias (``primary``, shadowed by the
    competing native copy) and disagreed with ``why`` for the same physical copy.
    """
    _alias_collision(mock_home)
    home = mock_home.resolve()
    canonical = str((home / ".claude" / "skills" / "working-alias").resolve())
    why = resolve_skill("working-alias", "opencode", home, home)
    expected = next(
        candidate.state.value
        for candidate in why.candidates
        if candidate.installation.canonical_path == canonical
    )
    assert expected == "ACTIVE"

    payload = _json(home, "working-alias", "--agent", "opencode")
    (hit,) = payload["results"]
    assert hit["state"] == expected
    assert {(item["agent"], item["name"], item["state"]) for item in hit["states"]} == {
        ("opencode", "primary", "SHADOWED"),
        ("opencode", "working-alias", "ACTIVE"),
    }

    plain = _search(home, "working-alias", "--agent", "opencode")
    assert "working-alias: ACTIVE" in plain.stdout  # type: ignore[attr-defined]
    assert "primary: SHADOWED" in plain.stdout  # type: ignore[attr-defined]


def test_states_without_an_agent_are_exposed_by_agent_and_name(mock_home: Path) -> None:
    _alias_collision(mock_home)
    (hit,) = _json(mock_home, "working-alias")["results"]
    assert hit["state"] is None
    states = {(item["agent"], item["name"]): item["state"] for item in hit["states"]}
    assert states[("opencode", "primary")] == "SHADOWED"
    assert states[("opencode", "working-alias")] == "ACTIVE"
    assert states[("claude", "working-alias")] == "ACTIVE"
    assert [(item["agent"], item["name"]) for item in hit["states"]] == sorted(
        (item["agent"], item["name"]) for item in hit["states"]
    )

    plain = _search(mock_home, "working-alias")
    assert "primary" in plain.stdout  # type: ignore[attr-defined]
    assert "SHADOWED" in plain.stdout  # type: ignore[attr-defined]
    assert "ACTIVE" in plain.stdout  # type: ignore[attr-defined]


def test_a_description_or_body_match_shows_every_distinct_alias_state(mock_home: Path) -> None:
    """No alias matched, so reducing the answer to one representative would lie."""
    _alias_collision(mock_home)
    (hit,) = _json(mock_home, "real", "--agent", "opencode")["results"]
    assert hit["match"] == "body"
    assert hit["state"] == "SHADOWED, ACTIVE"


def test_a_non_representative_alias_is_searchable_by_the_selected_agent(
    mock_home: Path,
) -> None:
    """Regression: only the representative folder/frontmatter name was matched."""
    working = mock_home / ".claude" / "skills" / "working-alias"
    make_skill(working, "working-alias", "The working copy.", body="sentinel\n")
    try:
        symlink(working, mock_home / ".agents" / "skills" / "secondary")
    except OSError:
        pytest.skip("this system cannot create symlinks")
    home = mock_home.resolve()

    (body_hit,) = _json(home, "sentinel", "--agent", "opencode")["results"]
    assert ("opencode", "secondary", "ACTIVE") in {
        (item["agent"], item["name"], item["state"]) for item in body_hit["states"]
    }

    (name_hit,) = _json(home, "secondary", "--agent", "opencode")["results"]
    assert name_hit["name"] == "working-alias"
    assert name_hit["state"] == "ACTIVE"


def test_an_exact_alias_beats_a_longer_prefix_with_a_different_state(
    mock_home: Path,
) -> None:
    working = mock_home / ".claude" / "skills" / "alpha"
    make_skill(working, "alpha", "The exact alias.", body="sentinel\n")
    try:
        symlink(working, mock_home / ".agents" / "skills" / "alpha-long")
    except OSError:
        pytest.skip("this system cannot create symlinks")
    make_skill(
        mock_home / ".config" / "opencode" / "skills" / "alpha-long",
        "alpha-long",
        "The competing longer alias.",
    )
    home = mock_home.resolve()

    results = _json(home, "alpha", "--agent", "opencode")["results"]
    working_hit = next(
        result for result in results if Path(result["canonical_path"]) == working.resolve()
    )
    assert working_hit["state"] == "ACTIVE"
    assert ("opencode", "alpha-long", "SHADOWED") in {
        (item["agent"], item["name"], item["state"]) for item in working_hit["states"]
    }


def test_every_lookup_name_gets_its_own_state(mock_home: Path) -> None:
    make_skill(
        mock_home / ".claude" / "skills" / "folder-alias",
        "declared-name",
        "Two names for one copy.",
    )
    (hit,) = _json(mock_home, "folder-alias")["results"]
    assert {(item["agent"], item["name"], item["state"]) for item in hit["states"]} == {
        ("claude", "folder-alias", "ACTIVE"),
        ("claude", "declared-name", "ACTIVE"),
        ("opencode", "folder-alias", "ACTIVE"),
    }
    (filtered,) = _json(mock_home, "declared-name", "--agent", "claude")["results"]
    assert filtered["state"] == "ACTIVE"


def test_a_repeated_alias_is_reported_once(mock_home: Path) -> None:
    native = mock_home / ".config" / "opencode" / "skills" / "primary"
    make_skill(native, "primary", "Reached twice.")
    try:
        symlink(native, mock_home / ".agents" / "skills" / "primary")
    except OSError:
        pytest.skip("this system cannot create symlinks")
    (hit,) = _json(mock_home, "primary", "--agent", "opencode")["results"]
    assert [(item["agent"], item["name"]) for item in hit["states"]] == [("opencode", "primary")]
    # Two entrypoints of one copy: the native one wins, the shared one is shadowed.
    assert hit["state"] == "ACTIVE, SHADOWED"


def _candidate(state: str, canonical: str, entrypoint: str) -> CandidateResolution:
    return CandidateResolution(
        state=HeadlineState(state),
        visibility=Visibility.ACTIVE_ROOT,
        collision=Collision.WINNING_ENTRY,
        rule_id="rule",
        evidence=Evidence.DOCUMENTED,
        reason="reason",
        rank=1,
        installation=SkillInstallation(
            name="deploy",
            entrypoint_path=entrypoint,
            canonical_path=canonical,
            scope=Scope.USER,
            parse_status=ParseStatus.VALID,
        ),
    )


def _resolution(*candidates: CandidateResolution) -> ResolutionReport:
    return ResolutionReport(
        skill_name="deploy",
        agent="claude",
        agent_name="Claude Code",
        cwd="/cwd",
        collision_policy="policy",
        policy_evidence=Evidence.DOCUMENTED,
        headline=HeadlineState.ACTIVE,
        candidates=candidates,
    )


def test_copy_state_prefers_canonical_then_entrypoint() -> None:
    """The copy is found by its canonical target first, its own path only as a fallback.

    Here a symlinked copy (entrypoint ``/link`` -> canonical ``/real``) and an
    unrelated copy whose *entrypoint* happens to be ``/real`` both exist; the
    canonical match must win, as on the TUI's Home screen.
    """
    report = _resolution(
        _candidate("ACTIVE", "/real", "/link"),
        _candidate("SHADOWED", "/other", "/real"),
    )
    assert search_module._copy_state(report, "/real") == "ACTIVE"
    # An unresolved copy (dangling link) is keyed by its entrypoint.
    dangling = _resolution(_candidate("INVALID", "/gone", "/dangling"))
    assert search_module._copy_state(dangling, "/dangling") == "INVALID"
    # Several entrypoints of one copy: every distinct state, no invented winner.
    both = _resolution(
        _candidate("ACTIVE", "/real", "/a"),
        _candidate("SHADOWED", "/real", "/b"),
        _candidate("ACTIVE", "/real", "/c"),
    )
    assert search_module._copy_state(both, "/real") == "ACTIVE, SHADOWED"
    assert search_module._copy_state(report, "/nowhere") == "unknown"


# --- usage errors happen before any walk ---------------------------------------


def _forbid_walk(monkeypatch: pytest.MonkeyPatch) -> None:
    def walk(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("search walked the filesystem before validating its input")

    monkeypatch.setattr(search_module, "live_discovery", walk)


def test_an_empty_query_exits_2_without_walking(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _forbid_walk(monkeypatch)
    result = _search(mock_home, "   ")
    assert result.exit_code == 2  # type: ignore[attr-defined]
    assert "search query must not be empty" in result.stderr  # type: ignore[attr-defined]
    with pytest.raises(ValueError):
        normalise_query("\t\n")


def test_an_unknown_agent_exits_2_without_walking_with_compares_sentence(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    compare = runner.invoke(
        app, ["compare", "--agent", "claude", "--agent", "nope", "--sandbox", str(mock_home)]
    )
    _forbid_walk(monkeypatch)
    result = _search(mock_home, "x", "--agent", "nope")
    assert result.exit_code == 2  # type: ignore[attr-defined]
    sentence = compare.stderr.strip()
    assert sentence.startswith("Error: unknown agent 'nope'. Known agents: ")
    assert result.stderr.strip() == sentence  # type: ignore[attr-defined]


def test_run_search_validates_before_walking(monkeypatch: pytest.MonkeyPatch) -> None:
    _forbid_walk(monkeypatch)
    with pytest.raises(ValueError):
        run_search("  ")
    with pytest.raises(KeyError):
        run_search("deploy", agent_id="nope")


# --- output ---------------------------------------------------------------------


def test_no_results_is_an_answer_not_an_error(mock_home: Path) -> None:
    _library(mock_home)
    result = _search(mock_home, "zzz-nothing")
    assert result.exit_code == 0  # type: ignore[attr-defined]
    assert "No skills match 'zzz-nothing'." in result.stdout  # type: ignore[attr-defined]


def test_json_is_the_model_with_sorted_keys(mock_home: Path) -> None:
    _library(mock_home)
    result = _search(mock_home, "  Database  ", "--json")
    payload = json.loads(result.stdout)  # type: ignore[attr-defined]
    assert list(payload) == sorted(payload)
    assert set(payload) == {
        "agent",
        "counts",
        "cwd",
        "home",
        "query",
        "results",
        "total",
        "unreadable",
    }
    assert payload["query"] == "Database"
    assert payload["total"] == len(payload["results"]) == 6
    first = payload["results"][0]
    assert list(first) == sorted(first)
    assert first == {
        "agents": ["claude", "opencode"],
        "canonical_path": first["canonical_path"],
        "frontmatter_name": None,
        "match": "name",
        "name": "database",
        "parse_status": "valid",
        "scope": "user",
        "snippet": "Talk to the store.",
        "state": None,
        "states": [
            {"agent": "claude", "name": "database", "state": "ACTIVE"},
            {"agent": "opencode", "name": "database", "state": "ACTIVE"},
        ],
        "variant_label": first["variant_label"],
    }
    assert Path(first["canonical_path"]).name == "database"


def test_a_query_starting_with_a_dash_goes_after_double_dash(mock_home: Path) -> None:
    make_skill(mock_home / ".claude" / "skills" / "flags", "flags", "Explains -verbose mode.")
    result = runner.invoke(app, ["search", "--sandbox", str(mock_home), "--json", "--", "-verbose"])
    assert result.exit_code == 0
    assert [r["name"] for r in json.loads(result.stdout)["results"]] == ["flags"]


def test_search_changes_nothing_on_disk(mock_home: Path) -> None:
    _library(mock_home)

    def state() -> dict[str, tuple[bytes, int]]:
        return {
            str(path): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in sorted(mock_home.rglob("*"))
            if path.is_file()
        }

    before = state()
    assert _search(mock_home, "database").exit_code == 0  # type: ignore[attr-defined]
    assert _search(mock_home, "database", "--json").exit_code == 0  # type: ignore[attr-defined]
    assert state() == before


# --- excerpts ------------------------------------------------------------------


def test_snippet_shows_the_matching_line_with_ellipses() -> None:
    text = "# Title\n\n" + "intro words " * 4 + "the needle sits here " + "tail words " * 8
    excerpt = snippet(text, "NEEDLE")
    assert len(excerpt) <= SNIPPET_WIDTH
    assert "needle" in excerpt
    assert excerpt.startswith("…") and excerpt.endswith("…")
    assert "Title" not in excerpt
    assert snippet("short line", "short") == "short line"


def test_snippet_collapses_whitespace_and_drops_control_characters() -> None:
    excerpt = snippet("alpha\t\tbeta \x1b[31mred\x1b[0m  gamma\x07", "beta")
    assert "\x1b" not in excerpt and "\x07" not in excerpt and "\t" not in excerpt
    assert excerpt == "alpha beta [31mred [0m gamma"


def test_snippet_spans_line_breaks_and_double_spaces() -> None:
    assert snippet("one two\nthree four", "two\nthree") == "one two three four"
    long = "x" * 120 + " use  the  tool " + "y" * 120
    assert "use the tool" in snippet(long, "the  tool")


def test_snippet_keeps_the_match_after_an_expanding_casefold_prefix() -> None:
    # "ß" casefolds to "ss", so offsets in the folded text no longer line up with
    # the original. A window computed from the folded offset used to jump past
    # the match and lose it entirely.
    text = "Straße notes\n" + "filler " * 20 + "\nthe database line"
    excerpt = snippet(text, "database")
    assert "database" in excerpt
    assert excerpt == "the database line"
    assert len(excerpt) <= SNIPPET_WIDTH

    # The regression shape: 120 expanding characters, then twice as many after.
    long_text = "ß" * 120 + " database " + "y" * 160
    long_excerpt = snippet(long_text, "database")
    assert "database" in long_excerpt
    assert len(long_excerpt) <= SNIPPET_WIDTH


def test_snippet_does_not_map_every_codepoint_in_a_long_prefix() -> None:
    """A million expanding characters must not allocate one integer each."""
    import tracemalloc

    text = "ß" * 1_000_000 + " database"
    tracemalloc.start()
    try:
        excerpt = snippet(text, "database")
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert "database" in excerpt
    assert len(excerpt) <= SNIPPET_WIDTH
    assert peak < 20 * 1024 * 1024, f"snippet allocated {peak} bytes"


def test_refit_keeps_the_match_in_a_narrow_column() -> None:
    excerpt = "…open the migration database tool and check the schema version before…"
    narrow = refit(excerpt, "DATABASE", 20)
    assert len(narrow) == 20
    assert "database" in narrow
    assert refit("short", "x", 20) == "short"
    assert refit("Name match shows the description text here", "zzz", 10) == "Name matc…"
    assert refit("anything", "x", 0) == ""


def test_snippet_of_nothing_is_empty() -> None:
    assert snippet(None, "x") == ""
    assert snippet("   \n\t", "x") == ""
    assert snippet("Just a description.", "") == "Just a description."


def test_snippet_comes_from_the_matched_field(mock_home: Path) -> None:
    make_skill(
        mock_home / ".claude" / "skills" / "deploy",
        "deploy",
        "Ship it.",
        body="Line one.\nRun the database checks.\n",
    )
    home = mock_home.resolve()
    (hit,) = build_search_report("database", home, home).results
    assert hit.snippet == "Run the database checks."
    (by_name,) = build_search_report("deploy", home, home).results
    assert by_name.snippet == "Ship it."


def test_a_body_match_after_an_expanding_prefix_reaches_the_excerpt(mock_home: Path) -> None:
    body = "ß" * 120 + " database " + "y" * 160 + "\n"
    make_skill(mock_home / ".claude" / "skills" / "unicode", "unicode", "Long body.", body=body)
    (hit,) = _json(mock_home, "database")["results"]
    assert hit["match"] == "body"
    assert "database" in hit["snippet"]
    assert len(hit["snippet"]) <= SNIPPET_WIDTH


# --- rendering ----------------------------------------------------------------


def _hit(
    name: str, snippet_text: str, *, agents: tuple[str, ...] = ("claude",), **extra: object
) -> SearchHit:
    return SearchHit(
        name=name,
        match=MatchField.BODY,
        snippet=snippet_text,
        scope=Scope.USER,
        canonical_path=f"/skills/{name}",
        agents=agents,
        parse_status="valid",
        **extra,  # type: ignore[arg-type]
    )


def _render(report: SearchReport, terminal: bool = False, width: int = 100) -> str:
    buffer = io.StringIO()
    console = Console(
        file=buffer,
        width=width,
        force_terminal=terminal,
        color_system="truecolor" if terminal else None,
        highlight=False,
    )
    render_search(report, console)
    return buffer.getvalue()


def test_markup_in_skill_text_and_query_prints_literally() -> None:
    report = SearchReport(
        query="[bold]q[/bold]",
        home="/h",
        cwd="/h",
        results=(_hit("[red]name[/red]", "[bold red]boom[/]"),),
    )
    text = _render(report)
    assert "[bold]q[/bold]" in text
    assert "[red]name[/red]" in text
    assert "[bold red]boom[/]" in text


def test_escape_sequences_in_names_and_queries_are_not_emitted() -> None:
    report = SearchReport(
        query="\x1b[31mq",
        home="/h",
        cwd="/h",
        results=(_hit("esc\x1b[31mname", "plain"),),
    )
    output = _render(report, terminal=True)
    assert "\x1b[31m" not in output
    plain = _render(report)
    assert "esc?[31mname" in plain
    assert "Search '?[31mq'" in plain


@pytest.mark.skipif(sys.platform == "win32", reason="Windows forbids ESC in file names")
def test_escape_sequences_in_real_folder_names_are_not_emitted(mock_home: Path) -> None:
    make_skill(mock_home / ".claude" / "skills" / "evil\x1b[31mname", "evil", "Evil.")
    home = mock_home.resolve()
    output = _render(build_search_report("evil", home, home), terminal=True)
    assert "\x1b[31m" not in output


def test_frontmatter_name_and_state_columns() -> None:
    report = SearchReport(
        query="q",
        home="/h",
        cwd="/h",
        results=(_hit("alias-one", "x", frontmatter_name="shared", state="ACTIVE"),),
        agent="codex",
        agent_name="OpenAI Codex",
    )
    text = _render(report)
    assert "alias-one (shared)" in text
    assert "ACTIVE" in text
    assert "Agent: OpenAI Codex (codex)" in text
    assert "State" in text


def test_unreadable_roots_reach_the_report(mock_home: Path) -> None:
    _library(mock_home)
    home = mock_home.resolve()
    index = discover(home, home, load_registry())
    index.unreadable_roots.append(UnreadableRoot("claude", "r", "/blocked", "denied"))
    report = build_search_report("database", home, home, index=index)
    assert [root["path"] for root in report.unreadable] == ["/blocked"]
    assert report.to_dict()["unreadable"][0]["detail"] == "denied"


def test_the_matched_word_stays_visible_at_80_columns() -> None:
    hit = _hit("migrate", "…open the migration database tool and check the schema version first…")
    report = SearchReport(query="database", home="/h", cwd="/h", results=(hit,))
    buffer = io.StringIO()
    render_search(report, Console(file=buffer, width=80, force_terminal=False))
    row = next(line for line in buffer.getvalue().splitlines() if "migrate" in line)
    assert "database" in row


def test_unreadable_roots_are_named(mock_home: Path) -> None:
    report = SearchReport(
        query="q",
        home="/h",
        cwd="/h",
        results=(),
        unreadable=({"agent": "claude", "root": "r", "path": "/blocked", "detail": "denied"},),
    )
    text = _render(report)
    assert "Unreadable roots (not searched):" in text
    assert "/blocked (denied)" in text


def test_every_row_stays_on_one_line_at_any_width() -> None:
    long = "word " * 40
    report = SearchReport(
        query="q", home="/h", cwd="/h", results=(_hit("a-very-long-skill-name-here", long),)
    )
    for width in (80, 100, 140):
        buffer = io.StringIO()
        render_search(report, Console(file=buffer, width=width, force_terminal=False))
        lines = buffer.getvalue().splitlines()
        assert all(len(line) <= width for line in lines)
        assert sum("a-very-long" in line for line in lines) == 1


def test_agent_names_are_not_capped_at_140_columns() -> None:
    """Regression: a permanent 16-character cap hid agents even with room to spare."""
    agents = ("antigravity", "claude", "codex", "dsh", "opencode")
    report = SearchReport(
        query="q",
        home="/h",
        cwd="/h",
        results=(_hit("skill", "excerpt", agents=agents),),
    )
    text = _render(report, width=140)
    assert ", ".join(agents) in text


def test_per_agent_states_stay_visible_at_140_columns() -> None:
    states = (
        LookupState("opencode", "primary", "SHADOWED"),
        LookupState("opencode", "working-alias", "ACTIVE"),
    )
    report = SearchReport(
        query="q",
        home="/h",
        cwd="/h",
        results=(_hit("working-alias", "excerpt", agents=("opencode",), states=states),),
    )
    text = _render(report, width=140)
    assert "opencode: primary SHADOWED" in text
    assert "opencode: working-alias ACTIVE" in text
    assert "…" not in text.split("Agents / States")[1].split("Excerpt")[0]


def test_selected_mixed_states_name_each_alias() -> None:
    states = (
        LookupState("opencode", "primary", "SHADOWED"),
        LookupState("opencode", "working-alias", "ACTIVE"),
    )
    report = SearchReport(
        query="q",
        home="/h",
        cwd="/h",
        results=(
            _hit(
                "working-alias",
                "excerpt",
                agents=("opencode",),
                state="SHADOWED, ACTIVE",
                states=states,
            ),
        ),
        agent="opencode",
        agent_name="OpenCode",
    )
    text = _render(report, width=140)
    assert "primary: SHADOWED" in text
    assert "working-alias: ACTIVE" in text


def test_unicode_alias_rows_use_display_width() -> None:
    states = (
        LookupState("opencode", "技能", "ACTIVE"),
        LookupState("opencode", "工作别名", "SHADOWED"),
    )
    report = SearchReport(
        query="q",
        home="/h",
        cwd="/h",
        results=(_hit("skill", "excerpt", agents=("opencode",), states=states),),
    )
    text = _render(report, width=120)
    assert "opencode: 技能 ACTIVE" in text
    assert "opencode: 工作别名 SHADOWED" in text


# --- bounded payload ---------------------------------------------------------


def _sparse(path: Path, size: int) -> None:
    """Create a sparse file of ``size`` bytes without writing them out."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.truncate(size)


def _forbid_payload_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("search read a skill document or hashed a payload")

    monkeypatch.setattr(discovery_module, "parse_skill", forbidden)
    monkeypatch.setattr(discovery_module, "hash_path", forbidden)
    monkeypatch.setattr(discovery_module, "hash_path_bounded", forbidden)


def test_an_oversized_support_file_is_refused_without_reading_it(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_skill(mock_home / ".claude" / "skills" / "big", "big", "A big skill.")
    _sparse(mock_home / ".claude" / "skills" / "big" / "support.bin", 4097)
    _forbid_payload_reads(monkeypatch)

    with pytest.raises(SkillPayloadTooLarge) as exc_info:
        run_search("big", mock_home, max_payload_bytes=4096)

    assert exc_info.value.limit_bytes == 4096
    assert "above the 4.0 KiB (4096 bytes) search limit" in str(exc_info.value)


def test_an_oversized_skill_document_is_refused_before_parsing(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = make_skill(mock_home / ".claude" / "skills" / "bigdoc", "bigdoc", "A big doc.")
    _sparse(document, 4097)
    _forbid_payload_reads(monkeypatch)

    with pytest.raises(SkillPayloadTooLarge):
        run_search("bigdoc", mock_home, max_payload_bytes=4096)


def test_standalone_qualification_reads_are_bounded(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = mock_home / ".pi" / "agent" / "skills" / "huge.md"
    document.parent.mkdir(parents=True)
    with document.open("wb") as handle:
        # Keep the valid header: truncating from zero would erase it and test a
        # different thing (an incidental file) than an oversized valid skill.
        handle.write(b"---\nname: huge\ndescription: Huge standalone.\n---\n")
        handle.truncate(10 * 1024 * 1024)
    reads: list[int] = []
    original = discovery_module._read_qualification_prefix

    def tracking(path: Path, max_bytes: int) -> tuple[str, bool] | None:
        reads.append(max_bytes)
        return original(path, max_bytes)

    monkeypatch.setattr(discovery_module, "_read_qualification_prefix", tracking)

    with pytest.raises(SkillPayloadTooLarge):
        run_search("huge", mock_home, max_payload_bytes=4096)

    assert reads, "qualification must have inspected the standalone document"
    assert all(limit <= 4096 for limit in reads)


def test_known_overage_is_refused_even_when_another_copy_is_unreadable(
    mock_home: Path,
) -> None:
    """Regression: one unmeasurable copy used to suppress a known overage."""
    broken = make_skill(
        mock_home / ".claude" / "skills" / "a-broken", "a-broken", "Broken support."
    ).parent
    try:
        os.symlink(broken / "missing.bin", broken / "dangling.bin")
    except OSError:
        pytest.skip("this system cannot create symlinks")
    make_skill(mock_home / ".claude" / "skills" / "z-big", "z-big", "Known overage.")
    _sparse(mock_home / ".claude" / "skills" / "z-big" / "support.bin", 4200)

    with pytest.raises(SkillPayloadTooLarge) as exc_info:
        run_search("z-big", mock_home, max_payload_bytes=4096)

    assert exc_info.value.total_bytes > 4096


def test_support_file_growth_after_sizing_is_bounded(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skill = mock_home / ".claude" / "skills" / "grow"
    make_skill(skill, "grow", "A growing support file.")
    support = skill / "support.bin"
    support.write_bytes(b"x" * 100)
    payload = sum(path.stat().st_size for path in skill.rglob("*") if path.is_file())
    budget = payload + 10
    original = discovery_module.parse_skill
    grown = False

    def grow(entrypoint: Path, *args: object, **kwargs: object):
        nonlocal grown
        if not grown and Path(entrypoint).name == "grow":
            grown = True
            with support.open("ab") as handle:
                handle.write(b"z" * 200)
        return original(entrypoint, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(discovery_module, "parse_skill", grow)

    with pytest.raises(SkillPayloadTooLarge) as exc_info:
        run_search("grow", mock_home, max_payload_bytes=budget)
    assert grown
    assert exc_info.value.total_bytes > exc_info.value.limit_bytes


def test_a_bounded_document_read_does_not_allocate_its_whole_limit(tmp_path: Path) -> None:
    """A short document under a huge limit must not reserve the limit up front."""
    import tracemalloc

    document = write_skill(
        tmp_path / "small",
        "---\nname: small\ndescription: Small.\n---\nshort body\n",
    )
    tracemalloc.start()
    try:
        result = parse_skill_document(document, max_document_bytes=256 * 1024 * 1024)
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert result.status is ParseStatus.VALID
    assert peak < 10 * 1024 * 1024, f"bounded read allocated {peak} bytes"


@pytest.mark.parametrize("incomplete_fingerprint", (False, True))
def test_growth_after_preflight_cannot_exceed_the_aggregate_budget(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch, incomplete_fingerprint: bool
) -> None:
    """Each document may stay small, yet aggregate growth must still be refused."""
    first = make_skill(
        mock_home / ".claude" / "skills" / "a-first",
        "a-first",
        "First.",
        body="x" * 100 + "\n",
    )
    second = make_skill(
        mock_home / ".claude" / "skills" / "b-second",
        "b-second",
        "Second.",
        body="y" * 100 + "\n",
    )
    payload = sum(
        path.stat().st_size
        for root in (first.parent, second.parent)
        for path in root.rglob("*")
        if path.is_file()
    )
    budget = payload + 10
    if incomplete_fingerprint:
        try:
            (first.parent / ".broken-asset").symlink_to(first.parent / "missing-asset")
        except OSError:
            pytest.skip("this system cannot create symlinks")
    original = discovery_module.parse_skill
    grown = False

    def grow(entrypoint: Path, *args: object, **kwargs: object):
        nonlocal grown
        if not grown and Path(entrypoint).name == "a-first":
            grown = True
            with first.open("ab") as handle:
                handle.write(b"z" * 80)
            assert first.stat().st_size < budget
        return original(entrypoint, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(discovery_module, "parse_skill", grow)

    with pytest.raises(SkillPayloadTooLarge):
        run_search("first", mock_home, max_payload_bytes=budget)
    assert grown


def test_a_large_incidental_readme_is_not_promoted(mock_home: Path) -> None:
    """Regression: DocumentTooLarge used to make every large README a body hit."""
    readme = mock_home / ".pi" / "agent" / "skills" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text(
        "# Incidental readme\n" + ("padding " * 150_000) + "sentinel\n", encoding="utf-8"
    )
    assert readme.stat().st_size > 1024 * 1024

    report = run_search("sentinel", mock_home, max_payload_bytes=2 * 1024 * 1024)

    assert report.results == ()


def test_a_valid_large_body_standalone_is_classified_from_its_prefix(
    mock_home: Path,
) -> None:
    document = mock_home / ".pi" / "agent" / "skills" / "large.md"
    document.parent.mkdir(parents=True)
    document.write_text(
        "---\nname: large\ndescription: A large standalone.\n---\n"
        + ("body " * 250_000)
        + "sentinel\n",
        encoding="utf-8",
    )
    assert document.stat().st_size > 1024 * 1024

    (hit,) = run_search("sentinel", mock_home, max_payload_bytes=2 * 1024 * 1024).results
    assert hit.name == "large"
    assert hit.match is MatchField.BODY
    assert "sentinel" in hit.snippet

    with pytest.raises(SkillPayloadTooLarge):
        run_search("sentinel", mock_home, max_payload_bytes=1024 * 1024)


def test_a_bom_and_crlf_standalone_header_still_qualifies(mock_home: Path) -> None:
    document = mock_home / ".pi" / "agent" / "skills" / "bom-skill.md"
    document.parent.mkdir(parents=True)
    document.write_bytes(
        "\ufeff---\r\nname: bom-skill\r\ndescription: BOM and CRLF.\r\n---\r\nsentinel\r\n".encode(
            "utf-8"
        )
    )

    (hit,) = run_search("sentinel", mock_home, max_payload_bytes=64 * 1024).results

    assert hit.name == "bom-skill"
    assert hit.match is MatchField.BODY


def test_invalid_utf8_at_the_end_of_a_standalone_file_fails_qualification(mock_home: Path) -> None:
    document = mock_home / ".pi" / "agent" / "skills" / "invalid.md"
    document.parent.mkdir(parents=True)
    document.write_bytes(b"---\nname: invalid\ndescription: Broken UTF-8.\n---\n\xff")

    assert run_search("invalid", mock_home, max_payload_bytes=4096).results == ()


def test_an_inconclusive_qualification_bound_is_reported(
    mock_home: Path,
) -> None:
    document = mock_home / ".pi" / "agent" / "skills" / "huge-frontmatter.md"
    document.parent.mkdir(parents=True)
    with document.open("wb") as handle:
        handle.write(b"---\nname: huge\ndescription: Never closes in the prefix\n")
        handle.truncate(2 * 1024 * 1024)

    with pytest.raises(StandaloneQualificationTooLarge):
        run_search("huge", mock_home, max_payload_bytes=4096)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows disallows ESC in file names")
def test_qualification_refusal_displays_file_names_literally(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = mock_home / ".pi" / "agent" / "skills" / "draft\x1b[31m.md"
    document.parent.mkdir(parents=True)
    document.write_text("---\n" + "x" * 4096, encoding="utf-8")
    monkeypatch.setattr(cli_module, "DEFAULT_MAX_SNAPSHOT_BYTES", 4096)

    result = _search(mock_home, "draft")

    assert result.exit_code == 2  # type: ignore[attr-defined]
    assert "draft\\x1b[31m.md" in result.stderr  # type: ignore[attr-defined]
    assert "\x1b" not in result.stderr  # type: ignore[attr-defined]


def test_payload_is_counted_once_per_canonical_copy(mock_home: Path) -> None:
    canonical = mock_home / ".claude" / "skills" / "shared"
    make_skill(canonical, "shared", "One physical copy.")
    (canonical / "asset.bin").write_bytes(b"x" * 200)
    try:
        symlink(canonical, mock_home / ".agents" / "skills" / "shared")
    except OSError:
        pytest.skip("this system cannot create symlinks")
    payload = sum(path.stat().st_size for path in canonical.rglob("*") if path.is_file())
    report = run_search("shared", mock_home, max_payload_bytes=payload)
    assert [hit.name for hit in report.results] == ["shared"]


def test_cli_refuses_an_oversized_inventory_with_no_partial_output(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_skill(mock_home / ".claude" / "skills" / "big", "big", "A big skill.")
    _sparse(mock_home / ".claude" / "skills" / "big" / "support.bin", 4097)
    monkeypatch.setattr(cli_module, "DEFAULT_MAX_SNAPSHOT_BYTES", 4096)

    result = _search(mock_home, "big")

    assert result.exit_code == 2  # type: ignore[attr-defined]
    assert result.stdout == ""  # type: ignore[attr-defined]
    assert "Error: Search refused" in result.stderr  # type: ignore[attr-defined]
    assert "above the 4.0 KiB (4096 bytes) search limit" in result.stderr  # type: ignore[attr-defined]


def test_cli_search_uses_the_shared_256_mib_payload_limit(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def fake_run_search(*_args: object, **kwargs: object) -> SearchReport:
        captured.update(kwargs)
        return SearchReport(query="x", home=str(mock_home), cwd=str(mock_home), results=())

    monkeypatch.setattr(cli_module, "run_search", fake_run_search)

    result = _search(mock_home, "x")

    assert result.exit_code == 0  # type: ignore[attr-defined]
    assert captured["max_payload_bytes"] == DEFAULT_MAX_SNAPSHOT_BYTES
    assert DEFAULT_MAX_SNAPSHOT_BYTES == 256 * 1024 * 1024


def test_environment_home_is_never_read(mock_home: Path) -> None:
    """The fixture moved HOME; the engine must follow it, not the real profile."""
    assert os.environ["HOME"] == str(mock_home)
    _library(mock_home)
    payload = _json(mock_home, "database")
    assert all(str(mock_home.resolve()) in r["canonical_path"] for r in payload["results"])
