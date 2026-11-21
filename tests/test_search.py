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

import skill_lens.core.search as search_module
from skill_lens.cli import app
from skill_lens.core.discovery import UnreadableRoot, discover
from skill_lens.core.scanner import build_scan_report
from skill_lens.core.search import (
    SNIPPET_WIDTH,
    build_search_report,
    normalise_query,
    refit,
    run_search,
    snippet,
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
from skill_lens.models.search import MatchField, SearchHit, SearchReport
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


def test_snippet_still_windows_the_match_when_casefold_changes_length() -> None:
    # "ß" casefolds to "ss", so offsets in the folded text no longer match the
    # original: the excerpt starts from the top of the field (not the match's
    # line) and the window is placed on an approximate offset.
    text = "Straße notes\n" + "filler " * 20 + "\nthe database line"
    excerpt = snippet(text, "database")
    assert "database" in excerpt
    assert excerpt.startswith("…")
    assert len(excerpt) <= SNIPPET_WIDTH


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


# --- rendering ----------------------------------------------------------------


def _hit(name: str, snippet_text: str, **extra: object) -> SearchHit:
    return SearchHit(
        name=name,
        match=MatchField.BODY,
        snippet=snippet_text,
        scope=Scope.USER,
        canonical_path=f"/skills/{name}",
        agents=("claude",),
        parse_status="valid",
        **extra,  # type: ignore[arg-type]
    )


def _render(report: SearchReport, terminal: bool = False) -> str:
    buffer = io.StringIO()
    console = Console(
        file=buffer,
        width=100,
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


def test_environment_home_is_never_read(mock_home: Path) -> None:
    """The fixture moved HOME; the engine must follow it, not the real profile."""
    assert os.environ["HOME"] == str(mock_home)
    _library(mock_home)
    payload = _json(mock_home, "database")
    assert all(str(mock_home.resolve()) in r["canonical_path"] for r in payload["results"])
