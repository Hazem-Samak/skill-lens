"""Headless U3 Home browsing tests (table, preview, filters, Why queue).

Specification reference: FULL_SCREEN_TUI.md §8.2-8.5, §9.1, §21.7 and §22 U3.

Every test uses the synthetic ``mock_home`` fixture (temporary HOME plus the
protected-system-root isolation installed by ``tests/conftest.py``); a live
``~/.claude`` is never read or written.  Workers are driven by real Textual
Pilot key/input events, and controlled races use threading events with bounded
waits so a hang fails the test instead of stalling the run.
"""

from __future__ import annotations

import asyncio
import builtins
import dataclasses
import os
import threading
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from textual.containers import VerticalScroll
from textual.widgets import DataTable, Input, Static

from skill_lens.core import paths
from skill_lens.core.exitcodes import ExitCode
from skill_lens.core.snapshot import SnapshotTooLarge, capture_session
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
from skill_lens.tui.app import SkillLensApp
from skill_lens.tui.home import (
    ALL_AGENTS,
    HomeScreen,
    _health_label,
    agent_display_name,
    build_agent_options,
    build_home_rows,
    detected_agent_ids,
    filter_home_rows,
    preview_text,
    resolution_text,
)
from tests.fixtures.builders import make_skill, write_skill
from tests.fixtures.scenarios import build_scenario

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _table(app: SkillLensApp) -> DataTable:
    return app.query_one("#skill-table", DataTable)


def _row_texts(app: SkillLensApp) -> list[list[str]]:
    table = _table(app)
    return [[str(cell) for cell in table.get_row_at(i)] for i in range(table.row_count)]


def _column_labels(app: SkillLensApp) -> list[str]:
    return [str(column.label) for column in _table(app).columns.values()]


def _row_keys(app: SkillLensApp) -> list[str]:
    table = _table(app)
    return [str(table.coordinate_to_cell_key((i, 0)).row_key.value) for i in range(table.row_count)]


def _state_values(app: SkillLensApp) -> list[str] | None:
    labels = _column_labels(app)
    if "State" not in labels:
        return None
    index = labels.index("State")
    return [row[index] for row in _row_texts(app)]


def _preview(app: SkillLensApp) -> str:
    return str(app.query_one("#preview-pane", Static).content)


def _status(app: SkillLensApp) -> str:
    return str(app.query_one("#status-text", Static).content)


def _empty_state(app: SkillLensApp) -> str:
    return str(app.query_one("#empty-state", Static).content)


def _agent_widget(app: SkillLensApp) -> str:
    return str(app.query_one("#agent-filter", Static).content)


def _legend(app: SkillLensApp) -> str:
    return str(app.query_one("#legend", Static).content)


def _catalog_note(app: SkillLensApp) -> str:
    return str(app.query_one("#catalog-note", Static).content)


def _rendered_text(app: SkillLensApp) -> str:
    """The actual compositor output as plain text (proves what a terminal shows)."""
    strips = app.screen._compositor.render_strips()
    return "\n".join(strip.text for strip in strips)


def _column_width(app: SkillLensApp, label: str) -> int:
    """The width, in cells, the compositor uses for a column (padding excluded)."""
    table = _table(app)
    for column in table.columns.values():
        if str(column.label) == label:
            return int(column.get_render_width(table)) - 2 * table.cell_padding
    raise AssertionError(f"no column {label!r}")


async def _wait_until(pilot: Any, predicate: Any, label: str, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        await pilot.pause(0.01)
    raise AssertionError(f"timed out waiting for {label}")


async def _wait_ready(pilot: Any, app: SkillLensApp) -> None:
    await _wait_until(
        pilot,
        lambda: (
            app.controller.current is not None
            and app.controller.status == "ready"
            and isinstance(app.screen, HomeScreen)
            and app.screen._generation == app.controller.current.generation
            and (
                len(app.controller.current.scan.skills) == 0
                or app.screen.query_one("#skill-table", DataTable).row_count > 0
            )
        ),
        "initial capture and home table ready",
    )
    await pilot.pause(0.02)


async def _wait_reports_idle(pilot: Any, app: SkillLensApp) -> None:
    await _wait_until(
        pilot,
        lambda: app.controller.active_requests.get("why") is None,
        "why queue idle",
    )
    # Let the acceptance message reach the Home screen.
    await pilot.pause(0.05)


def _candidate(state: str, canonical: str, entrypoint: str | None = None) -> CandidateResolution:
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
            entrypoint_path=entrypoint or canonical,
            canonical_path=canonical,
            scope=Scope.USER,
            parse_status=ParseStatus.VALID,
        ),
    )


def _report(*candidates: CandidateResolution) -> ResolutionReport:
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


def _codex_alias_home(home: Path) -> None:
    """Two directory aliases that resolve to the same frontmatter lookup name."""
    make_skill(home / ".codex" / "skills" / "alias-one", "shared", "First alias.")
    make_skill(home / ".codex" / "skills" / "alias-two", "shared", "Second alias.")


def _claude_skills(home: Path, *names: str) -> None:
    for name in names:
        make_skill(home / ".claude" / "skills" / name, name, f"{name} description.")


# ---------------------------------------------------------------------------
# Pure presentation helpers
# ---------------------------------------------------------------------------


def test_build_home_rows_order_keys_parse_marks_and_filters(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    snapshot = capture_session(generation=1, home=paths.home(), cwd=mock_home / "project")

    rows = build_home_rows(snapshot)

    assert [row.name for row in rows] == ["deploy", "deploy"]
    assert [row.key for row in rows] == [entry.canonical_path for entry in snapshot.scan.skills]
    assert [row.scope_label for row in rows] == ["Project", "Global"]
    assert [row.parse_mark for row in rows] == ["*", "*"]
    assert [row.variant_label for row in rows] == ["A", "B"]
    assert all(row.agents == ("claude", "opencode") for row in rows)

    # The combined text/agent filter is case-insensitive and never mutates rows.
    assert filter_home_rows(rows, "PERSONAL", None) == (rows[1],)
    assert filter_home_rows(rows, "deploy", "claude") == rows
    assert filter_home_rows(rows, "deploy", "codex") == ()
    assert filter_home_rows(rows, "   ", None) == rows
    assert filter_home_rows(rows, "zzz", None) == ()

    assert detected_agent_ids(snapshot) == ("claude", "opencode")
    options = build_agent_options(snapshot)
    assert options[0].agent_id is None
    assert options[0].label == ALL_AGENTS
    assert [option.agent_id for option in options[1:]] == ["claude", "opencode"]
    assert options[1].label == "Claude Code"
    assert agent_display_name(snapshot, "not-an-agent") == "not-an-agent"


def test_build_home_rows_marks_invalid_parse(mock_home: Path) -> None:
    build_scenario("malformed_frontmatter", mock_home)
    snapshot = capture_session(generation=1, home=paths.home(), cwd=mock_home)

    rows = build_home_rows(snapshot)

    assert [row.parse_mark for row in rows] == ["x", "x"]
    assert {row.parse_status for row in rows} == {"malformed_yaml", "missing_description"}
    assert all(row.description is None for row in rows)


def test_health_label_variants() -> None:
    assert _health_label(SimpleNamespace(code="ok", severity=None, reason=None, clause="")) == "ok"
    assert (
        _health_label(
            SimpleNamespace(
                code="missing_description", severity="warning", reason="frontmatter", clause=""
            )
        )
        == "missing_description (frontmatter)"
    )
    assert (
        _health_label(
            SimpleNamespace(code="broken_link", severity="error", reason=None, clause="cycle")
        )
        == "broken_link - cycle"
    )


def test_resolution_text_matches_canonical_entrypoint_and_unknown() -> None:
    report = _report(
        _candidate("ACTIVE", "/canon-a"),
        _candidate("SHADOWED", "/canon-a"),
        _candidate("ACTIVE", "/canon-other", entrypoint="/canon-b"),
    )

    # Canonical-path match wins and distinct states are preserved without a winner.
    assert resolution_text(report, "/canon-a") == "ACTIVE, SHADOWED"
    # An unresolved copy uses its entrypoint path as the fallback identity.
    assert resolution_text(report, "/canon-b") == "ACTIVE"
    # No candidate at all is explicit, never a headline guess.
    assert resolution_text(report, "/missing") == "unknown"


def test_preview_text_reports_captured_fields_literally(mock_home: Path) -> None:
    write_skill(
        mock_home / ".claude" / "skills" / "<x>y",
        '---\nname: "<x>y"\ndescription: "[bold red]literal[/bold red]"\n---\n# Body\n',
    )
    snapshot = capture_session(generation=1, home=paths.home(), cwd=mock_home)
    row = build_home_rows(snapshot)[0]

    preview = preview_text(row, snapshot)

    assert "Name: <x>y" in preview
    assert "Scope: Global" in preview
    assert "Description:\n[bold red]literal[/bold red]" in preview
    assert "Parse: valid (*)" in preview
    assert "Variant:" in preview


def test_preview_text_shows_missing_description_placeholder(mock_home: Path) -> None:
    build_scenario("malformed_frontmatter", mock_home)
    snapshot = capture_session(generation=1, home=paths.home(), cwd=mock_home)
    row = build_home_rows(snapshot)[0]

    assert "Description:\n(no description)" in preview_text(row, snapshot)


# ---------------------------------------------------------------------------
# Table, preview and key navigation
# ---------------------------------------------------------------------------


def test_home_rows_preview_duplicates_variants_and_navigation(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            assert _column_labels(app) == ["Name", "Scope", "Parse"]
            assert _row_texts(app) == [
                ["deploy", "Project", "*"],
                ["deploy", "Global", "*"],
            ]
            keys = _row_keys(app)
            assert len(set(keys)) == 2  # canonical duplicate names never share a row key

            table = _table(app)
            assert table.cursor_row == 1
            assert app.controller.selected_key == keys[1]
            assert "Scope: Global" in _preview(app)
            assert "Variant: B" in _preview(app)
            assert "Personal deploy helper." in _preview(app)

            await pilot.press("up")
            assert table.cursor_row == 0
            assert app.controller.selected_key == keys[0]
            assert "Scope: Project" in _preview(app)
            assert "Variant: A" in _preview(app)
            assert "~/project/.claude/skills/deploy" in _preview(app)
            assert "Project deploy helper." in _preview(app)

            await pilot.press("j")
            assert table.cursor_row == 1
            assert "Scope: Global" in _preview(app)

            await pilot.press("k")
            assert table.cursor_row == 0
            assert "Scope: Project" in _preview(app)

            assert _status(app) == "Ready: 2 skills discovered"
            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Filters, focus, empty states
# ---------------------------------------------------------------------------


def test_home_text_filter_focus_enter_escape_and_empty_states(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            generation = app.controller.current.generation

            await pilot.press("slash")
            assert isinstance(app.focused, Input)
            assert app.focused.id == "filter-input"

            await pilot.press(*"personal")
            assert _table(app).row_count == 1
            assert "Personal deploy helper." in _preview(app)
            # Ordinary command letters typed into the filter never trigger app actions.
            assert app.controller.current.generation == generation

            await pilot.press("enter")
            assert isinstance(app.focused, DataTable)

            await pilot.press("slash")
            await pilot.press("escape")
            assert isinstance(app.focused, DataTable)
            assert app.query_one("#filter-input", Input).value == ""
            assert _table(app).row_count == 2

            await pilot.press("slash")
            await pilot.press(*"zzz")
            assert _table(app).row_count == 0
            assert _empty_state(app) == "No skills match the current filter."
            assert _preview(app) == ""

            await pilot.press("escape")
            assert _table(app).row_count == 2
            assert _preview(app) != ""

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_home_agent_cycle_combined_filters_and_state_column(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _claude_skills(mock_home, "alpha", "beta")

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            assert _agent_widget(app) == "Agent: All agents"
            assert _state_values(app) is None

            await pilot.press("a")
            await _wait_reports_idle(pilot, app)
            assert _agent_widget(app) == "Agent: Claude Code (claude)"
            assert _column_labels(app) == ["Name", "Scope", "Parse", "State"]
            assert _state_values(app) == ["ACTIVE", "ACTIVE"]
            assert "State:" in _legend(app)

            # Text and agent filters combine.
            await pilot.press("slash")
            await pilot.press(*"beta")
            await pilot.press("enter")
            assert _table(app).row_count == 1
            assert _row_texts(app)[0][0] == "beta"
            assert _state_values(app) == ["ACTIVE"]

            await pilot.press("a")
            await _wait_reports_idle(pilot, app)
            assert _agent_widget(app) == "Agent: OpenCode V2 (opencode)"
            assert _table(app).row_count == 1

            await pilot.press("a")
            assert _agent_widget(app) == "Agent: All agents"
            assert _state_values(app) is None
            assert _table(app).row_count == 1

            await pilot.press("escape")
            assert _table(app).row_count == 2

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_home_no_agents_retains_all_view_with_explanation(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            assert _table(app).row_count == 0
            assert _status(app) == "Ready: 0 skills discovered"
            assert _empty_state(app) == "No skills discovered in this session. Press r to refresh."
            assert _agent_widget(app) == "Agent: All agents (no agents detected)"
            assert "No agents detected" in _legend(app)

            await pilot.press("a")
            assert _agent_widget(app) == "Agent: All agents (no agents detected)"
            assert _state_values(app) is None

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_home_filter_letters_are_text_and_ctrl_c_quits(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            generation = app.controller.current.generation

            await pilot.press("slash")
            await pilot.press("q", "r", "a", "j", "k")
            assert app.query_one("#filter-input", Input).value == "qrajk"
            assert app.controller.current.generation == generation
            assert app.return_code is None

            # Ctrl-C wins over Input copy even with selected text.
            await pilot.press("shift+left")
            await pilot.press("ctrl+c")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_home_literal_markup_strings_render_without_interpretation(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_skill(
        mock_home / ".claude" / "skills" / "<x>y",
        '---\nname: "<x>y"\ndescription: "[bold red]literal[/bold red]"\n---\n# Body\n',
    )

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            assert _row_texts(app)[0][0] == "<x>y"
            preview = _preview(app)
            assert "<x>y" in preview
            assert "[bold red]literal[/bold red]" in preview

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_home_broken_and_unresolved_rows_keep_entrypoint_identity(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("symlink_cycle_guard", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            skills = app.controller.current.scan.skills
            assert _row_keys(app) == [skill.canonical_path for skill in skills]
            assert _row_texts(app)[0][2] == "x"
            assert "Parse: invalid (x)" in _preview(app)

            await pilot.press("a")
            await _wait_reports_idle(pilot, app)
            assert _state_values(app) == ["INVALID", "INVALID"]

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_home_unreadable_root_note_is_shown(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            assert _catalog_note(app) == ""

            # Inject captured unreadable-root data (no live read, no file write).
            snapshot = app.controller.current
            assert snapshot is not None
            new_scan = dataclasses.replace(
                snapshot.scan,
                unreadable=(
                    {
                        "agent": "claude",
                        "root": "claude_personal",
                        "path": "~/.claude/skills",
                        "detail": "denied",
                    },
                ),
            )
            app.controller.current = dataclasses.replace(snapshot, scan=new_scan)
            app.screen.sync_from_controller()

            note = _catalog_note(app)
            assert note.startswith("Unreadable roots:")
            assert "~/.claude/skills" in note
            assert "denied" in note
            assert _table(app).row_count == 2

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Why queue: grouping, per-copy states, cache and races
# ---------------------------------------------------------------------------


def test_home_why_is_skipped_without_agent_filter_and_one_call_per_group(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    import skill_lens.core.snapshot as snapshot_module

    real_snapshot_why = snapshot_module.snapshot_why
    calls: list[tuple[str, str]] = []

    def counting_why(snapshot: Any, key: str, agent: str) -> Any:
        calls.append((key, agent))
        return real_snapshot_why(snapshot, key, agent)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", counting_why)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            # No agent filter means no resolution work at all.
            await pilot.pause(0.1)
            assert calls == []

            await pilot.press("a")
            await _wait_until(pilot, lambda: len(calls) == 1, "single group report")
            await _wait_reports_idle(pilot, app)
            await pilot.pause(0.05)

            # Two same-name copies, one distinct lookup name: exactly one request.
            assert len(calls) == 1
            assert calls[0][1] == "claude"
            assert _state_values(app) == ["SHADOWED", "ACTIVE"]

            # An ordinary redraw reuses the completed group; it never re-dispatches.
            app._update_ui()
            await pilot.pause(0.05)
            app.screen.sync_from_controller()
            await pilot.pause(0.05)
            assert len(calls) == 1

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_home_why_groups_by_actual_lookup_name_not_display_name(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _codex_alias_home(mock_home)

    import skill_lens.core.snapshot as snapshot_module

    real_snapshot_why = snapshot_module.snapshot_why
    calls: list[tuple[str, str]] = []

    def counting_why(snapshot: Any, key: str, agent: str) -> Any:
        calls.append((key, agent))
        return real_snapshot_why(snapshot, key, agent)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", counting_why)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            assert [row[0] for row in _row_texts(app)] == ["alias-one", "alias-two"]

            await pilot.press("a")
            await _wait_reports_idle(pilot, app)
            await pilot.pause(0.05)

            # Different displayed names, one shared frontmatter lookup name.
            assert len(calls) == 1
            assert calls[0][1] == "codex"
            assert _state_values(app) == ["AMBIGUOUS", "AMBIGUOUS"]

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_home_why_make_m_calls_and_reuse_cached_groups(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _claude_skills(mock_home, "alpha", "beta", "gamma")

    import skill_lens.core.snapshot as snapshot_module

    real_snapshot_why = snapshot_module.snapshot_why
    calls: list[tuple[str, str]] = []

    def counting_why(snapshot: Any, key: str, agent: str) -> Any:
        calls.append((key, agent))
        return real_snapshot_why(snapshot, key, agent)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", counting_why)

    def claude_calls() -> int:
        return sum(1 for _, agent in calls if agent == "claude")

    def opencode_calls() -> int:
        return sum(1 for _, agent in calls if agent == "opencode")

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            await pilot.press("a")
            await _wait_until(pilot, lambda: claude_calls() >= 3, "three claude groups")
            await _wait_reports_idle(pilot, app)
            await pilot.pause(0.05)
            assert claude_calls() == 3
            assert _state_values(app) == ["ACTIVE", "ACTIVE", "ACTIVE"]

            await pilot.press("a")
            await _wait_until(pilot, lambda: opencode_calls() >= 3, "three opencode groups")
            await _wait_reports_idle(pilot, app)
            await pilot.pause(0.05)

            await pilot.press("a")
            await pilot.press("a")
            await _wait_reports_idle(pilot, app)
            await pilot.pause(0.1)

            # Cache hits reuse the earlier finished groups; no worker runs again.
            assert claude_calls() == 3
            assert opencode_calls() == 3

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_home_cache_peek_does_not_cancel_unrelated_active_request(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _claude_skills(mock_home, "alpha", "beta")

    import skill_lens.core.snapshot as snapshot_module

    real_snapshot_why = snapshot_module.snapshot_why
    calls: list[tuple[str, str]] = []

    def counting_why(snapshot: Any, key: str, agent: str) -> Any:
        calls.append((key, agent))
        return real_snapshot_why(snapshot, key, agent)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", counting_why)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            for _ in range(3):  # All -> claude -> opencode -> All
                await pilot.press("a")
                await _wait_reports_idle(pilot, app)
                await pilot.pause(0.05)
            assert _agent_widget(app) == "Agent: All agents"

            manual_request, manual_event, cached = app.controller.request_view(
                "why", ("manual-key", "claude")
            )
            assert manual_request is not None
            assert manual_event is not None
            assert cached is None

            before = len(calls)
            await pilot.press("a")
            await pilot.pause(0.1)

            # Returning to claude hits the cache and must not start (and cancel) work.
            assert len(calls) == before
            assert app.controller.active_requests.get("why") == manual_request
            assert manual_event.is_set() is False

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_home_selection_change_redrives_and_rejects_late_result(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _claude_skills(mock_home, "alpha", "beta")

    import skill_lens.core.snapshot as snapshot_module

    real_snapshot_why = snapshot_module.snapshot_why
    first_key: dict[str, str | None] = {"value": None}
    first_started = threading.Event()
    release_first = threading.Event()
    first_finished = threading.Event()
    calls: list[tuple[str, str]] = []

    def racy_why(snapshot: Any, key: str, agent: str) -> Any:
        is_first_call = key == first_key["value"] and not any(c[0] == key for c in calls)
        calls.append((key, agent))
        if is_first_call:
            first_started.set()
            # Far longer than the 5s _wait_until timeout, so a stalled queue is
            # reported as the timeout below instead of racing this release.
            release_first.wait(30.0)
            try:
                stale = real_snapshot_why(snapshot, key, agent)
                # A visibly wrong state: if accepted it would render UNSEARCHED.
                stale_candidates = tuple(
                    replace(candidate, state=HeadlineState.UNSEARCHED)
                    for candidate in stale.candidates
                )
                return replace(
                    stale,
                    candidates=stale_candidates,
                    headline=HeadlineState.UNSEARCHED,
                )
            finally:
                first_finished.set()
        return real_snapshot_why(snapshot, key, agent)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", racy_why)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        try:
            async with app.run_test(size=(100, 30)) as pilot:
                await _wait_ready(pilot, app)
                first_key["value"] = app.controller.selected_key
                assert first_key["value"] is not None

                await pilot.press("a")
                await _wait_until(pilot, first_started.is_set, "first report start")

                # Move to the other row while the first request is still blocked.
                await pilot.press("down")
                await _wait_until(
                    pilot,
                    lambda: len(calls) >= 3,
                    "second group and re-driven first group",
                )
                await _wait_reports_idle(pilot, app)
                assert not first_finished.is_set(), "old worker must still be blocked"

                # The re-driven request already rendered the honest state.
                assert _state_values(app) == ["ACTIVE", "ACTIVE"]
                assert "UNSEARCHED" not in (_state_values(app) or [])

                release_first.set()
                first_finished.wait(5.0)
                await pilot.pause(0.1)

                # The late stale result was rejected: state stays honest.
                assert _state_values(app) == ["ACTIVE", "ACTIVE"]
                assert (
                    app.controller.get_cached_report("why", (first_key["value"] or "", "claude"))
                    is not None
                )

                await pilot.press("q")
                assert app.return_code == int(ExitCode.OK)
        finally:
            release_first.set()
            first_finished.wait(5.0)

    asyncio.run(_run())


def test_home_rejected_old_outcome_preserves_newer_owned_token(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An old rejected outcome must not clear the newer owned Why token.

    Event-controlled race (no bare sleep establishes the ordering): the first
    request is released first so its *rejected* outcome is delivered while the
    newer request is still blocked in its worker and owned by Home.  The newer
    owned token must be preserved (same token object, controller still tracking
    its request) and the queue must still drain once the newer request is
    released, proving the superseded group was left resolvable rather than
    stranded on ``pending``.
    """
    _claude_skills(mock_home, "alpha", "beta")

    import skill_lens.core.snapshot as snapshot_module

    real_snapshot_why = snapshot_module.snapshot_why
    first_key: dict[str, str | None] = {"value": None}
    first_started = threading.Event()
    release_first = threading.Event()
    second_started = threading.Event()
    release_second = threading.Event()

    def racy_why(snapshot: Any, key: str, agent: str) -> Any:
        if first_key["value"] is None:
            first_key["value"] = key
        if key == first_key["value"]:
            first_started.set()
            # Far longer than the 5s _wait_until timeout, so a stalled queue is
            # reported as the timeout below instead of racing this release.
            release_first.wait(30.0)
            return real_snapshot_why(snapshot, key, agent)
        second_started.set()
        release_second.wait(30.0)
        return real_snapshot_why(snapshot, key, agent)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", racy_why)

    first_request_id: dict[str, int | None] = {"value": None}
    rejected_seen = threading.Event()
    original_note = HomeScreen.note_report_outcome

    def spy_note(
        self: HomeScreen,
        view: Any,
        request_id: int,
        generation: int,
        arguments: tuple[str, ...],
        *,
        accepted: bool,
        report: Any = None,
        error: Exception | None = None,
    ) -> None:
        original_note(
            self,
            view,
            request_id,
            generation,
            arguments,
            accepted=accepted,
            report=report,
            error=error,
        )
        if (
            view == "why"
            and not accepted
            and first_request_id["value"] is not None
            and request_id == first_request_id["value"]
        ):
            # The superseded request's rejected outcome has now been processed.
            rejected_seen.set()

    monkeypatch.setattr(HomeScreen, "note_report_outcome", spy_note)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        try:
            async with app.run_test(size=(100, 30)) as pilot:
                await _wait_ready(pilot, app)

                # Start the first request and keep it blocked in its worker.
                await pilot.press("a")
                await _wait_until(pilot, first_started.is_set, "first request start")
                first_request = app.controller.active_requests.get("why")
                assert first_request is not None
                first_request_id["value"] = first_request.request_id

                # Move to the other row: the first request is cancelled and the
                # newer request is dispatched and blocked as well.
                await pilot.press("down")
                await _wait_until(pilot, second_started.is_set, "newer request start")

                newer_owned = app.screen._inflight
                assert newer_owned is not None
                newer_request = newer_owned.request
                assert newer_request.request_id != first_request.request_id
                assert app.controller.active_requests.get("why") == newer_request

                # Release only the *old* worker: its rejected outcome is
                # delivered while the newer request is still owned and in flight.
                release_first.set()
                await _wait_until(pilot, rejected_seen.is_set, "old rejected outcome delivered")

                # Invariant: the newer owned token is preserved, not cleared...
                owned_after = app.screen._inflight
                assert owned_after is newer_owned, (
                    "the newer owned Why token was cleared by a rejected outcome"
                )
                assert app.controller.active_requests.get("why") == newer_request

                # ...and its group still resolves once released: full drain.
                release_second.set()
                await _wait_until(
                    pilot,
                    lambda: _state_values(app) == ["ACTIVE", "ACTIVE"],
                    "full queue resolves",
                )

                await pilot.press("q")
                assert app.return_code == int(ExitCode.OK)
        finally:
            release_first.set()
            release_second.set()

    asyncio.run(_run())


def test_home_agent_change_clears_marks_and_requests_new_agent(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _claude_skills(mock_home, "alpha", "beta")

    import skill_lens.core.snapshot as snapshot_module

    real_snapshot_why = snapshot_module.snapshot_why
    opencode_started = threading.Event()
    release_opencode = threading.Event()
    calls: list[str] = []

    def blocking_why(snapshot: Any, key: str, agent: str) -> Any:
        calls.append(agent)
        if agent == "opencode":
            opencode_started.set()
            release_opencode.wait(5.0)
        return real_snapshot_why(snapshot, key, agent)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", blocking_why)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        try:
            async with app.run_test(size=(100, 30)) as pilot:
                await _wait_ready(pilot, app)

                await pilot.press("a")
                await _wait_until(pilot, lambda: calls.count("claude") >= 2, "claude reports")
                await _wait_reports_idle(pilot, app)
                await pilot.pause(0.05)
                assert _state_values(app) == ["ACTIVE", "ACTIVE"]

                await pilot.press("a")
                await _wait_until(pilot, opencode_started.is_set, "opencode report start")

                # Old agent marks are cleared before the new agent finishes.
                assert _state_values(app) == ["pending", "pending"]

                release_opencode.set()
                await _wait_reports_idle(pilot, app)
                await pilot.pause(0.05)
                assert _state_values(app) == ["ACTIVE", "ACTIVE"]

                await pilot.press("q")
                assert app.return_code == int(ExitCode.OK)
        finally:
            release_opencode.set()

    asyncio.run(_run())


def test_home_failed_report_marks_unavailable_without_retry_loop(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _claude_skills(mock_home, "alpha", "beta")

    calls: list[str] = []

    def failing_why(snapshot: Any, key: str, agent: str) -> Any:
        calls.append(key)
        raise RuntimeError("resolution boom")

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", failing_why)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            await pilot.press("a")
            await _wait_until(
                pilot,
                lambda: _state_values(app) == ["unavailable", "unavailable"],
                "unavailable marks",
            )
            assert len(calls) == 2
            assert app.controller.is_failed is True
            assert "Error:" in _status(app)
            details = str(app.query_one("#error-details", Static).content)
            assert "resolution boom" in details

            # Ordinary redraws or accepted failures must not start a retry loop.
            for _ in range(3):
                app._update_ui()
                app.screen.sync_from_controller()
                await pilot.pause(0.05)
            assert len(calls) == 2
            assert _state_values(app) == ["unavailable", "unavailable"]

            await pilot.press("q")
            assert app.return_code == int(ExitCode.INTERNAL)

    asyncio.run(_run())


def test_home_unmount_discards_late_report_after_prompt_quit(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _claude_skills(mock_home, "alpha")

    import skill_lens.core.snapshot as snapshot_module

    real_snapshot_why = snapshot_module.snapshot_why
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def blocking_why(snapshot: Any, key: str, agent: str) -> Any:
        started.set()
        release.wait(5.0)
        try:
            return real_snapshot_why(snapshot, key, agent)
        finally:
            finished.set()

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", blocking_why)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        try:
            async with app.run_test(size=(100, 30)) as pilot:
                await _wait_ready(pilot, app)
                await pilot.press("a")
                await _wait_until(pilot, started.is_set, "report start")

                # Quit while the report worker is still blocked.
                await pilot.press("q")
                assert app.return_code == int(ExitCode.OK)
        finally:
            release.set()
            finished.wait(5.0)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Refresh, retention and stale generation work
# ---------------------------------------------------------------------------


def test_home_refresh_retains_rows_then_rebuilds_and_clears_marks(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    import skill_lens.core.snapshot as snapshot_module

    real_capture = snapshot_module.capture_session
    real_snapshot_why = snapshot_module.snapshot_why
    capture_started = threading.Event()
    release_capture = threading.Event()
    why_started = threading.Event()
    release_why = threading.Event()

    def gated_capture(
        *,
        generation: int,
        home: Path,
        cwd: Path,
        max_snapshot_bytes: Any = None,
        cancelled: Any = None,
    ) -> Any:
        if generation >= 2:
            capture_started.set()
            release_capture.wait(5.0)
        return real_capture(
            generation=generation,
            home=home,
            cwd=cwd,
            max_snapshot_bytes=max_snapshot_bytes,
            cancelled=lambda: False,
        )

    def gated_why(snapshot: Any, key: str, agent: str) -> Any:
        if snapshot.generation >= 2:
            why_started.set()
            release_why.wait(5.0)
        return real_snapshot_why(snapshot, key, agent)

    monkeypatch.setattr("skill_lens.tui.app.capture_session", gated_capture)
    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", gated_why)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        try:
            async with app.run_test(size=(100, 30)) as pilot:
                await _wait_ready(pilot, app)
                await pilot.press("a")
                await _wait_reports_idle(pilot, app)
                await pilot.pause(0.05)
                assert _state_values(app) == ["SHADOWED", "ACTIVE"]

                await pilot.press("r")
                await _wait_until(pilot, capture_started.is_set, "refresh capture start")
                assert app.controller.status == "loading"
                assert "Scanning skills..." in _status(app)
                # Usable old rows and marks stay visible while loading.
                assert _table(app).row_count == 2
                assert _state_values(app) == ["SHADOWED", "ACTIVE"]

                release_capture.set()
                await _wait_until(
                    pilot,
                    lambda: (
                        app.controller.current is not None
                        and app.controller.current.generation == 2
                    ),
                    "generation 2 publication",
                )
                await _wait_until(pilot, why_started.is_set, "generation 2 why start")

                # A successful publication rebuilds rows and clears old marks.
                assert _table(app).row_count == 2
                assert _state_values(app) == ["pending", "pending"]

                release_why.set()
                await _wait_reports_idle(pilot, app)
                await pilot.pause(0.05)
                assert _state_values(app) == ["SHADOWED", "ACTIVE"]

                await pilot.press("q")
                assert app.return_code == int(ExitCode.OK)
        finally:
            release_capture.set()
            release_why.set()

    asyncio.run(_run())


def test_home_failed_refresh_retains_rows_and_exits_three(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    import skill_lens.core.snapshot as snapshot_module

    real_capture = snapshot_module.capture_session

    def failing_refresh(
        *,
        generation: int,
        home: Path,
        cwd: Path,
        max_snapshot_bytes: Any = None,
        cancelled: Any = None,
    ) -> Any:
        if generation > 1:
            raise RuntimeError("refresh exploded")
        return real_capture(
            generation=generation,
            home=home,
            cwd=cwd,
            max_snapshot_bytes=max_snapshot_bytes,
            cancelled=cancelled,
        )

    monkeypatch.setattr("skill_lens.tui.app.capture_session", failing_refresh)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            initial = app.controller.current
            selected = app.controller.selected_key
            assert selected is not None

            await pilot.press("r")
            await _wait_until(pilot, lambda: app.controller.is_failed, "refresh failure")

            # The usable old snapshot and preview are retained.
            assert app.controller.current is initial
            assert _table(app).row_count == 2
            assert app.controller.selected_key == selected
            assert "deploy" in _preview(app)
            assert "Error:" in _status(app)
            assert "refresh exploded" in str(app.query_one("#error-details", Static).content)

            await pilot.press("q")
            assert app.return_code == int(ExitCode.INTERNAL)

    asyncio.run(_run())


def test_home_size_refusal_retains_rows_and_exits_zero(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    import skill_lens.core.snapshot as snapshot_module

    real_capture = snapshot_module.capture_session
    refusal = SnapshotTooLarge(total_bytes=300 * 1024 * 1024, limit_bytes=256 * 1024 * 1024)

    def refusing_refresh(
        *,
        generation: int,
        home: Path,
        cwd: Path,
        max_snapshot_bytes: Any = None,
        cancelled: Any = None,
    ) -> Any:
        if generation > 1:
            raise refusal
        return real_capture(
            generation=generation,
            home=home,
            cwd=cwd,
            max_snapshot_bytes=max_snapshot_bytes,
            cancelled=cancelled,
        )

    monkeypatch.setattr("skill_lens.tui.app.capture_session", refusing_refresh)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            await pilot.press("r")
            await _wait_until(pilot, lambda: app.controller.status == "refused", "refusal")

            assert _table(app).row_count == 2
            assert "Snapshot refused" in _status(app)
            assert not app.controller.is_failed

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_home_refresh_three_wins_over_stale_two_rows(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _claude_skills(mock_home, "alpha")

    import skill_lens.core.snapshot as snapshot_module

    real_capture = snapshot_module.capture_session
    gen1_snapshot: dict[str, Any] = {}
    gen2_started = threading.Event()
    release_gen2 = threading.Event()

    def racy_capture(
        *,
        generation: int,
        home: Path,
        cwd: Path,
        max_snapshot_bytes: Any = None,
        cancelled: Any = None,
    ) -> Any:
        if generation == 2:
            gen2_started.set()
            release_gen2.wait(5.0)
            # A stale snapshot captured before "beta" existed.
            return dataclasses.replace(gen1_snapshot["value"], generation=2)
        snapshot = real_capture(
            generation=generation,
            home=home,
            cwd=cwd,
            max_snapshot_bytes=max_snapshot_bytes,
            cancelled=cancelled,
        )
        if generation == 1:
            gen1_snapshot["value"] = snapshot
        return snapshot

    monkeypatch.setattr("skill_lens.tui.app.capture_session", racy_capture)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        try:
            async with app.run_test(size=(100, 30)) as pilot:
                await _wait_ready(pilot, app)
                assert [row[0] for row in _row_texts(app)] == ["alpha"]

                # New content appears between refresh 2 and refresh 3.
                make_skill(mock_home / ".claude" / "skills" / "beta", "beta", "Beta description.")

                await pilot.press("r")
                await _wait_until(pilot, gen2_started.is_set, "refresh 2 start")
                await pilot.press("r")
                await _wait_until(
                    pilot,
                    lambda: (
                        app.controller.current is not None
                        and app.controller.current.generation == 3
                    ),
                    "refresh 3 publication",
                )
                assert [row[0] for row in _row_texts(app)] == ["alpha", "beta"]

                release_gen2.set()
                await pilot.pause(0.2)

                # The late generation 2 snapshot was rejected and changed nothing.
                assert app.controller.current.generation == 3
                assert app.controller.pending_generation is None
                assert [row[0] for row in _row_texts(app)] == ["alpha", "beta"]

                await pilot.press("q")
                assert app.return_code == int(ExitCode.OK)
        finally:
            release_gen2.set()

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# No live filesystem reads after capture
# ---------------------------------------------------------------------------


def test_home_navigation_and_filtering_never_read_live_filesystem(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    # Target-specific sentinel: only reads whose path lives under the synthetic
    # target home raise.  Textual's own incidental file access (its CSS, locale
    # data, etc.) is outside the targets and stays allowed, so this catches a
    # real browsing read without false positives.
    target_prefixes = {
        os.path.abspath(str(mock_home)),
        str(mock_home.resolve()),
    }

    def _is_target(value: Any) -> bool:
        try:
            text = os.fspath(value)
        except TypeError:
            return False
        if isinstance(text, bytes):
            text = text.decode("utf-8", "surrogateescape")
        absolute = os.path.abspath(text)
        return any(
            absolute == prefix or absolute.startswith(prefix + os.sep) for prefix in target_prefixes
        )

    path_originals = {
        name: getattr(Path, name) for name in ("open", "read_text", "read_bytes", "resolve")
    }
    builtin_open = builtins.open

    def _guarded(original: Any, label: str) -> Any:
        def wrapper(target: Any, *args: Any, **kwargs: Any) -> Any:
            if _is_target(target):
                raise AssertionError(
                    f"Forbidden synthetic-target filesystem read: {label} {target}"
                )
            return original(target, *args, **kwargs)

        return wrapper

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            def forbid(*args: Any, **kwargs: Any) -> Any:
                raise AssertionError("Forbidden live filesystem probe during browsing")

            with monkeypatch.context() as mp:
                mp.setattr("skill_lens.core.system.live_discovery", forbid)
                mp.setattr("skill_lens.core.discovery.discover", forbid)
                mp.setattr("skill_lens.registry.loader.load_registry", forbid)
                mp.setattr("skill_lens.registry.loader.list_agents", forbid)
                mp.setattr("skill_lens.core.snapshot.load_registry", forbid)
                mp.setattr("skill_lens.core.resolver.load_registry", forbid)
                mp.setattr("skill_lens.core.compare.load_registry", forbid)
                mp.setattr("skill_lens.core.resolver._load_disabled_overrides", forbid)
                mp.setattr("skill_lens.core.hasher.iter_files", forbid)
                mp.setattr("skill_lens.core.paths.home", forbid)
                mp.setattr("skill_lens.core.paths.display", forbid)
                mp.setattr("skill_lens.core.paths.same_location", forbid)
                # Direct target-path reads/probes must never happen while browsing.
                mp.setattr(Path, "open", _guarded(path_originals["open"], "Path.open"))
                mp.setattr(
                    Path, "read_text", _guarded(path_originals["read_text"], "Path.read_text")
                )
                mp.setattr(
                    Path, "read_bytes", _guarded(path_originals["read_bytes"], "Path.read_bytes")
                )
                mp.setattr(Path, "resolve", _guarded(path_originals["resolve"], "Path.resolve"))
                mp.setattr(builtins, "open", _guarded(builtin_open, "builtins.open"))

                await pilot.press("down")
                await pilot.press("up")
                await pilot.press("slash")
                await pilot.press(*"deploy")
                await pilot.press("enter")
                await pilot.press("escape")
                await pilot.press("a")
                await _wait_reports_idle(pilot, app)

                assert _table(app).row_count >= 1
                assert app.controller.cache, "frozen Why must resolve without disk reads"

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Rendered geometry and keyboard preview access (candidate-R1 corrections)
# ---------------------------------------------------------------------------

_LONG_NAME = "a-long-literal-name"
# Rich markup opening tags look like this; a closing tag needs "/" which is a
# path separator, so the literal deliberately uses only an opening tag.  If the
# cell were markup-interpreted, the "[bold]" tag would be stripped.
_MARKUP_NAME = "[bold]literal-name-here"


def test_home_table_columns_size_to_content_and_render_fully(
    mock_home: Path,
) -> None:
    """Literal columns must be sized from their values, not clipped to the header."""
    # Claude identity is the directory name, so both literals live in the
    # directory (and frontmatter) name.
    make_skill(mock_home / ".claude" / "skills" / _LONG_NAME, _LONG_NAME, "Long name.")
    make_skill(
        mock_home / ".claude" / "skills" / _MARKUP_NAME,
        "plain-markup-skill",
        "[red]description[/red]",
    )

    async def _run(size: tuple[int, int]) -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=size) as pilot:
            await _wait_ready(pilot, app)
            await pilot.pause(0.2)
            table = _table(app)
            assert table.row_count == 2

            expected_name = max(len("Name"), len(_LONG_NAME), len(_MARKUP_NAME))
            # Geometry: the compositor width equals the widest literal value.
            assert _column_width(app, "Name") == expected_name
            assert _column_width(app, "Scope") >= len("Global")

            # Rendered output: the actual terminal text carries both full
            # literals, and markup-looking content is shown literally.
            rendered = _rendered_text(app)
            assert _LONG_NAME in rendered
            assert _MARKUP_NAME in rendered
            assert "literal-name-here" in rendered

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run((100, 30)))
    asyncio.run(_run((60, 24)))


def test_home_state_column_grows_to_fit_state_labels(mock_home: Path) -> None:
    """A state label wider than the initial column grows the column, not clips it."""
    # Codex identity is the frontmatter name, so both aliases share one lookup
    # name and resolve to the longer AMBIGUOUS label.
    make_skill(mock_home / ".codex" / "skills" / "alias-one", "shared", "First alias.")
    make_skill(mock_home / ".codex" / "skills" / "alias-two", "shared", "Second alias.")

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("a")
            await _wait_reports_idle(pilot, app)
            await pilot.pause(0.1)

            assert _state_values(app) == ["AMBIGUOUS", "AMBIGUOUS"]
            assert _column_width(app, "State") >= len("AMBIGUOUS")
            assert "AMBIGUOUS" in _rendered_text(app)

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_home_preview_is_keyboard_focusable_and_scrollable(mock_home: Path) -> None:
    """Tab/Shift-Tab reach a focusable preview whose keyboard scroll reveals data."""
    description = "Long description sentence. " * 3
    make_skill(mock_home / ".claude" / "skills" / "alpha", "alpha", description)
    make_skill(mock_home / ".claude" / "skills" / "beta", "beta", "short")

    async def _run(size: tuple[int, int], *, clipped: bool) -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=size) as pilot:
            await _wait_ready(pilot, app)
            await pilot.pause(0.2)

            preview = app.query_one("#preview-scroll", VerticalScroll)
            # The compatibility Static is preserved and is not itself focusable.
            pane = app.query_one("#preview-pane", Static)
            assert not pane.can_focus
            assert pane.content

            # Forward traversal reaches the preview.
            for _ in range(3):
                await pilot.press("tab")
                if preview.has_focus:
                    break
            assert preview.has_focus, "Tab must reach the preview pane"
            # Backward traversal reaches it too.
            for _ in range(4):
                await pilot.press("shift+tab")
                if preview.has_focus:
                    break
            assert preview.has_focus, "Shift+Tab must reach the preview pane"

            if clipped:
                # Narrow pane clips lower metadata until scrolled.
                assert "Variant:" not in _rendered_text(app)
                assert preview.max_scroll_y > 0
                for _ in range(6):
                    await pilot.press("down")
                await pilot.pause(0.1)
                assert "Variant:" in _rendered_text(app)
                await pilot.press("end")
                await pilot.pause(0.1)
                assert preview.scroll_offset.y == preview.max_scroll_y
                assert "Long description sentence." in _rendered_text(app)
            else:
                # Wide pane shows the whole preview without scrolling.
                rendered = _rendered_text(app)
                assert "Variant:" in rendered
                assert "Long description sentence." in rendered

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run((60, 24), clipped=True))
    asyncio.run(_run((100, 30), clipped=False))


def test_home_unexpected_cell_update_fault_routes_to_containment_and_exit3(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unexpected ``update_cell`` fault must not be swallowed (F6).

    Home tolerates only the documented missing/stale-cell condition.  Any other
    update fault has to reach the app's existing containment path, which marks
    sticky failure and exits 3 without rendering a terminal traceback.
    """
    _claude_skills(mock_home, "alpha")

    def exploding_update_cell(self: DataTable, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError("unexpected cell update fault")

    monkeypatch.setattr(DataTable, "update_cell", exploding_update_cell)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        raised: list[BaseException] = []
        try:
            async with app.run_test(size=(100, 30)) as pilot:
                await _wait_ready(pilot, app)
                await pilot.press("a")
                await _wait_until(pilot, lambda: app.controller.is_failed, "contained fault")
        except RuntimeError as exc:
            # Textual's run_test re-raises the recorded fault; the containment
            # path itself ran, as asserted below.
            raised.append(exc)

        assert app.controller.is_failed is True
        assert app.controller.status == "error"
        assert app.return_code == int(ExitCode.INTERNAL)
        # The fault was contained, not dumped as a terminal traceback.
        assert app._exit_renderables == []
        assert raised and "unexpected cell update fault" in str(raised[0])

    asyncio.run(_run())


def test_home_state_cell_suppresses_only_expected_stale_row(mock_home: Path) -> None:
    """The documented stale/missing-cell condition is still handled quietly (F6)."""
    _claude_skills(mock_home, "alpha")

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("a")
            await _wait_reports_idle(pilot, app)
            before = _state_values(app)
            assert before == ["ACTIVE"]

            # A row key that no longer exists in the rebuilt table is the real
            # stale-cell condition the narrow catch must tolerate.
            app.screen._set_state_cell("skill:stale-row-key", "AMBIGUOUS")
            assert _state_values(app) == before

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_initial_capture_completing_before_home_mount_still_populates_table(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A capture that wins the mount race must still populate the Home table.

    Regression: the app starts the initial capture before the default Home
    screen is mounted.  If the worker finishes first, the ready snapshot is
    published while Home's mounted guard is still false.  Without a deferred
    post-mount reconcile, the table stays empty until the user refreshes.
    """
    _claude_skills(mock_home, "alpha")
    home = paths.home()
    snapshot = capture_session(generation=1, home=home, cwd=home)

    def instant_capture(*, generation: int, **_: Any) -> Any:
        return replace(snapshot, generation=generation)

    mount_statuses: list[str] = []
    original_on_mount = HomeScreen.on_mount

    def recording_on_mount(self: HomeScreen) -> None:
        mount_statuses.append(self._host.controller.status)
        original_on_mount(self)

    monkeypatch.setattr("skill_lens.tui.app.capture_session", instant_capture)
    monkeypatch.setattr(HomeScreen, "on_mount", recording_on_mount)

    async def _run() -> None:
        app = SkillLensApp(home=home, cwd=home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_until(
                pilot,
                lambda: (
                    app.controller.status == "ready"
                    and isinstance(app.screen, HomeScreen)
                    and app.screen.is_mounted
                ),
                "ready Home mounted",
            )
            await pilot.pause(0.05)
            assert mount_statuses == ["ready"], (
                "test no longer exercises the early-capture ordering"
            )
            assert _table(app).row_count == 1
            assert _row_texts(app)[0][0] == "alpha"
            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())
