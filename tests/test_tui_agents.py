"""Headless U6 Agents screen tests using captured definitions and Pilot events."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from textual.containers import VerticalScroll
from textual.widgets import DataTable, Input, Static
from typer.testing import CliRunner

import skill_lens.tui.app as app_module
from skill_lens.cli import app as cli_app
from skill_lens.core.snapshot import SnapshotTooLarge
from skill_lens.registry.loader import list_agents
from skill_lens.tui.agents import AgentsScreen, agent_detail_text
from skill_lens.tui.app import SkillLensApp
from skill_lens.tui.home import HomeScreen
from skill_lens.tui.json_view import JsonView

runner = CliRunner()


async def _wait_until(pilot: Any, predicate: Any, label: str, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        await pilot.pause(0.01)
    raise AssertionError(f"timed out waiting for {label}")


async def _wait_home(pilot: Any, app: SkillLensApp) -> None:
    await _wait_until(
        pilot,
        lambda: app.controller.current is not None and app.controller.pending_generation is None,
        "captured session",
    )
    await pilot.pause(0.02)


def _agent_ids(screen: AgentsScreen) -> list[str]:
    table = screen.query_one("#agents-table", DataTable)
    return [
        str(table.coordinate_to_cell_key((index, 1)).row_key.value)
        for index in range(table.row_count)
    ]


def _oracle_payload() -> list[dict[str, object]]:
    """Build the expected CLI shape independently of the new shared helper."""
    return [
        {
            "id": agent.id,
            "name": agent.name,
            "collision_policy": agent.collision_policy,
            "policy_evidence": agent.policy_evidence.value,
            "roots": len(agent.roots),
        }
        for agent in sorted(list_agents(), key=lambda item: item.id)
    ]


def test_agents_lists_every_captured_definition_and_all_root_policy_details(
    mock_home: Path,
) -> None:
    """Known agents remain visible even when the scan detects no installed skills."""
    expected_payload = _oracle_payload()
    cli = runner.invoke(cli_app, ["agents", "--json"])
    assert cli.exit_code == 0
    expected_document = json.dumps(expected_payload, sort_keys=True, indent=2)
    assert cli.stdout == expected_document + "\n"

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_home(pilot, app)
            snapshot = app.controller.current
            assert snapshot is not None
            assert snapshot.scan.summary.detected_agents == ()
            await pilot.press("g")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, AgentsScreen)
            assert _agent_ids(screen) == [str(item["id"]) for item in expected_payload]
            table = screen.query_one("#agents-table", DataTable)
            for row_index, expected in enumerate(expected_payload):
                row = [str(cell) for cell in table.get_row_at(row_index)]
                assert row == [
                    expected["name"],
                    expected["id"],
                    expected["collision_policy"],
                    expected["policy_evidence"],
                    str(expected["roots"]),
                ]

            selected = next(
                agent for agent in snapshot.registry if agent.id == screen.selected_agent_id
            )
            detail = str(screen.query_one("#agents-detail", Static).content)
            assert f"Identity source: {selected.identity_source}" in detail
            assert f"Collision policy: {selected.collision_policy}" in detail
            assert f"Coexistence policy: {selected.coexist_policy}" in detail
            assert f"Policy evidence: {selected.policy_evidence.value}" in detail
            assert f"Source: {selected.source}" in detail
            assert f"Walk boundary: {selected.walk_boundary}" in detail
            assert f"Unsearched rule: {selected.unsearched_rule_id}" in detail
            assert f"Disabled rule: {selected.disabled_rule_id or '(not declared)'}" in detail
            assert f"Disabled settings: {selected.disabled_settings or '(not declared)'}" in detail
            assert f"Disabled key: {selected.disabled_key or '(not declared)'}" in detail
            assert f"Ambiguous rule: {selected.ambiguous_rule_id or '(not declared)'}" in detail
            assert [
                detail.index(f"Root {index}: {root.id}")
                for index, root in enumerate(selected.roots, start=1)
            ] == sorted(
                detail.index(f"Root {index}: {root.id}")
                for index, root in enumerate(selected.roots, start=1)
            )
            for _index, root in enumerate(selected.roots, start=1):
                for label, value in (
                    ("Kind", root.kind),
                    ("Path template", root.path),
                    ("Scope", root.scope.value),
                    ("Rank", str(root.rank)),
                    ("Rule", root.rule_id),
                    ("Evidence", root.evidence.value),
                    ("Base", root.base.value),
                    ("Entry format", root.entry_format.value),
                    ("Nested rule", root.nested_rule_id or "(not declared)"),
                    ("File rule", root.file_rule_id or "(not declared)"),
                    ("Loadability", root.loadability or "(not declared)"),
                ):
                    assert f"  {label}: {value}" in detail

            await pilot.press("J")
            await pilot.pause()
            assert screen.json_mode
            view = screen.query_one("#agents-json", JsonView)
            assert view.document == expected_document
            assert view.document + "\n" == cli.stdout
            selected_before = screen.selected_agent_id
            assert selected_before is not None
            await pilot.press("down")
            assert screen.selected_agent_id == selected_before
            assert screen.query_one("#agents-body").display is False
            assert app.focused is view
            await pilot.press("escape")
            await pilot.pause()
            assert not screen.json_mode
            assert app.focused is not None and app.focused.id == "agents-table"
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            await pilot.press("q")

    asyncio.run(_run())


def test_agents_json_is_empty_array_only_for_a_captured_empty_registry(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty captured registry is ``[]``; a missing capture stays explanatory."""
    original_capture = app_module.capture_session

    def capture_empty_registry(**kwargs: Any) -> Any:
        return replace(original_capture(**kwargs), registry=())

    monkeypatch.setattr(app_module, "capture_session", capture_empty_registry)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test() as pilot:
            await _wait_home(pilot, app)
            await pilot.press("g")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, AgentsScreen)
            assert screen.query_one("#agents-table", DataTable).row_count == 0
            assert "No agent definitions" in str(screen.query_one("#agents-empty", Static).content)
            await pilot.press("J")
            assert screen.query_one("#agents-json", JsonView).document == "[]"
            await pilot.press("q")

    asyncio.run(_run())


def test_agents_distinguishes_no_capture_from_an_empty_registry(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A refused first capture is explained and never serialized as an empty list."""
    started = threading.Event()
    release = threading.Event()

    def refuse_capture(**kwargs: Any) -> Any:
        started.set()
        if not release.wait(timeout=3):
            raise AssertionError("capture test release timed out")
        raise SnapshotTooLarge(total_bytes=8, limit_bytes=1)

    monkeypatch.setattr(app_module, "capture_session", refuse_capture)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home, max_snapshot_bytes=1)
        async with app.run_test() as pilot:
            await _wait_until(pilot, started.is_set, "blocked initial capture")
            await pilot.press("g")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, AgentsScreen)
            assert app.controller.current is None
            assert "Scanning skills" in str(screen.query_one("#agents-status", Static).content)
            release.set()
            await _wait_until(pilot, lambda: app.controller.status == "refused", "capture refusal")
            await pilot.pause()
            assert "Snapshot refused" in str(screen.query_one("#agents-status", Static).content)
            await pilot.press("J")
            assert screen.query_one("#agents-json", JsonView).document is None
            assert "Snapshot refused" in screen.query_one("#agents-json", JsonView).displayed_text
            await pilot.press("q")

    try:
        asyncio.run(_run())
    finally:
        release.set()


def test_home_shortcuts_preserve_filter_typing_and_open_empty_catalog_screens(
    mock_home: Path,
) -> None:
    """Home routes g/c only from browsing; the filter keeps those letters."""

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_home(pilot, app)
            await pilot.press("slash", "g", "c")
            assert isinstance(app.screen, HomeScreen)
            assert app.query_one("#filter-input", Input).value == "gc"
            # Exercise the route methods with the filter focused as well. The
            # bindings and the action guard jointly protect letters as input.
            home = app.screen
            filter_input = app.query_one("#filter-input", Input)
            filter_input.focus()
            home.action_open_agents()
            home.action_open_compare()
            assert app.screen is home
            assert app.query_one("#filter-input", Input).value == "gc"
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("g")
            await pilot.pause()
            assert isinstance(app.screen, AgentsScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            await pilot.press("c")
            await pilot.pause()
            assert isinstance(app.screen, app_module.CompareScreen)
            assert app.screen.query_one("#compare-a-table", DataTable).row_count == 10
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("J")
            await pilot.pause()
            home = app.screen
            assert isinstance(home, HomeScreen)
            await pilot.press("g", "c")
            assert app.screen is home
            assert home.json_mode
            await pilot.press("escape")
            home.suspend_why()
            stack_before = len(app.screen_stack)
            home.action_open_agents()
            home.action_open_compare()
            assert len(app.screen_stack) == stack_before
            home.resume_why()
            await pilot.press("q")

    asyncio.run(_run())


def test_agent_details_and_table_render_bracketed_text_literally(mock_home: Path) -> None:
    """Registry metadata is displayed as text, never interpreted as markup."""
    agent = list_agents()[0]
    rooted = replace(agent.roots[0], path="~/.agent/[red]folder[/red]")
    strange = replace(
        agent,
        name="[red]🧪 Agent[/red]",
        source="https://example.test/[blue]source[/blue]",
        roots=(rooted, *agent.roots[1:]),
    )
    detail = agent_detail_text(strange)
    assert "[red]🧪 Agent[/red]" in detail
    assert "~/.agent/[red]folder[/red]" in detail
    assert "https://example.test/[blue]source[/blue]" in detail

    original_capture = app_module.capture_session

    def capture_strange(**kwargs: Any) -> Any:
        snapshot = original_capture(**kwargs)
        return replace(
            snapshot,
            registry=(strange, *tuple(item for item in snapshot.registry if item.id != strange.id)),
        )

    from unittest.mock import patch

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        with patch.object(app_module, "capture_session", capture_strange):
            async with app.run_test(size=(60, 24)) as pilot:
                await _wait_home(pilot, app)
                await pilot.press("g")
                await pilot.pause()
                screen = app.screen
                assert isinstance(screen, AgentsScreen)
                # Find the unusual agent through a real row highlight.
                table = screen.query_one("#agents-table", DataTable)
                row = next(
                    i for i in range(table.row_count) if str(table.get_row_at(i)[1]) == strange.id
                )
                table.move_cursor(row=row, animate=False)
                await pilot.pause()
                assert "[red]🧪 Agent[/red]" in str(
                    screen.query_one("#agents-detail", Static).content
                )
                assert "~/.agent/[red]folder[/red]" in str(
                    screen.query_one("#agents-detail", Static).content
                )
                await pilot.press("q")

    asyncio.run(_run())


def test_agent_json_scroll_and_focus_restore_after_positive_scroll(mock_home: Path) -> None:
    """Raw JSON leaves focus on JsonView and restores the selected pane's scroll."""

    # Ten captured definitions provide a genuinely scrollable details document.
    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(60, 24)) as pilot:
            await _wait_home(pilot, app)
            await pilot.press("g")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, AgentsScreen)
            detail = screen.query_one("#agents-detail-scroll", VerticalScroll)
            detail.focus()
            await pilot.press(*(["down"] * 20))
            await pilot.pause()
            offset = detail.scroll_offset.y
            assert offset > 0
            assert app.focused is detail
            screen.action_cursor_up()
            await pilot.pause()
            moved_offset = detail.scroll_offset.y
            assert moved_offset < offset
            screen.action_cursor_down()
            await pilot.pause()
            assert detail.scroll_offset.y > moved_offset
            await pilot.press("J")
            await pilot.pause()
            assert screen.json_mode
            assert app.focused is screen.query_one("#agents-json", JsonView)
            # Hidden list/pane actions cannot change the captured selection.
            selected = screen.selected_agent_id
            await pilot.press("j", "k", "down", "up")
            assert screen.selected_agent_id == selected
            await pilot.press("escape")
            await pilot.pause()
            assert app.focused is detail
            assert detail.scroll_offset.y == offset
            await pilot.press("J")
            await pilot.pause()
            # If the saved pane disappears while raw mode is open, restore
            # focus to the visible list rather than a dead widget.
            screen._json_previous_focus = Static()
            await pilot.press("escape")
            await pilot.pause()
            assert app.focused is screen.query_one("#agents-table", DataTable)
            assert detail.scroll_offset.y == offset
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("q")

    asyncio.run(_run())


def test_agents_keyboard_navigation_rootless_metadata_and_removed_id_refresh(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keyboard focus and refresh reconcile the selection with captured facts."""
    original_capture = app_module.capture_session
    agents = {agent.id: agent for agent in list_agents()}
    rootless = replace(
        agents["claude"],
        source="",
        disabled_rule_id=None,
        disabled_settings=None,
        disabled_key=None,
        ambiguous_rule_id=None,
        roots=(),
    )
    codex = agents["codex"]

    def capture_registry(**kwargs: Any) -> Any:
        snapshot = original_capture(**kwargs)
        generation = kwargs["generation"]
        if generation == 1:
            registry = (codex, rootless)
        elif generation == 2:
            registry = (rootless,)
        else:
            registry = ()
        return replace(snapshot, registry=registry)

    monkeypatch.setattr(app_module, "capture_session", capture_registry)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(60, 24)) as pilot:
            await _wait_home(pilot, app)
            await pilot.press("g")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, AgentsScreen)
            table = screen.query_one("#agents-table", DataTable)
            assert _agent_ids(screen) == ["claude", "codex"]
            assert screen.selected_agent_id == "claude"
            await pilot.press("j")
            assert screen.selected_agent_id == "codex"
            await pilot.press("k")
            assert screen.selected_agent_id == "claude"
            await pilot.press("enter")
            await pilot.pause()
            detail_scroll = screen.query_one("#agents-detail-scroll", VerticalScroll)
            assert app.focused is detail_scroll
            detail = str(screen.query_one("#agents-detail", Static).content)
            assert "Source: (not declared)" in detail
            assert "Disabled rule: (not declared)" in detail
            assert "Disabled settings: (not declared)" in detail
            assert "Disabled key: (not declared)" in detail
            assert "Ambiguous rule: (not declared)" in detail
            assert "Search roots (0):\n  (none declared)" in detail
            await pilot.press("escape")
            await pilot.pause()
            assert app.focused is table
            await pilot.press("tab")
            assert app.focused is detail_scroll
            await pilot.press("backspace")
            await pilot.pause()
            assert app.focused is table

            # A selected ID that disappears falls back to the first remaining
            # captured ID; a later empty publication clears the selection.
            await pilot.press("j")
            assert screen.selected_agent_id == "codex"
            await pilot.press("r")
            await _wait_until(
                pilot,
                lambda: (
                    app.controller.current is not None and app.controller.current.generation == 2
                ),
                "selected ID removal publication",
            )
            assert screen.selected_agent_id == "claude"
            screen.action_refresh()
            await _wait_until(
                pilot,
                lambda: (
                    app.controller.current is not None and app.controller.current.generation == 3
                ),
                "empty registry publication",
            )
            assert screen.selected_agent_id is None
            assert table.row_count == 0
            assert "No agent definitions" in str(screen.query_one("#agents-empty", Static).content)
            await pilot.press("J")
            assert screen.query_one("#agents-json", JsonView).document == "[]"
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("backspace")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            await pilot.press("q")

    asyncio.run(_run())


def test_agents_json_reconciles_to_refreshed_registry_and_keeps_selection(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refresh updates raw registry facts while retaining the selected ID and mode."""
    original_capture = app_module.capture_session

    def capture_renamed_agent(**kwargs: Any) -> Any:
        snapshot = original_capture(**kwargs)
        if kwargs["generation"] > 1:
            snapshot = replace(
                snapshot,
                registry=tuple(
                    replace(agent, name="Refreshed Codex") if agent.id == "codex" else agent
                    for agent in snapshot.registry
                ),
            )
        return snapshot

    monkeypatch.setattr(app_module, "capture_session", capture_renamed_agent)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test() as pilot:
            await _wait_home(pilot, app)
            await pilot.press("g")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, AgentsScreen)
            table = screen.query_one("#agents-table", DataTable)
            codex_row = _agent_ids(screen).index("codex")
            table.move_cursor(row=codex_row, column=0, animate=False)
            await pilot.pause()
            assert screen.selected_agent_id == "codex"
            await pilot.press("J")
            await pilot.pause()
            view = screen.query_one("#agents-json", JsonView)
            old_document = view.document
            assert old_document is not None and "Refreshed Codex" not in old_document

            await pilot.press("r")
            await _wait_until(
                pilot,
                lambda: (
                    app.controller.current is not None
                    and app.controller.current.generation == 2
                    and view.document is not None
                    and view.document != old_document
                ),
                "refreshed registry JSON",
            )
            assert screen.json_mode
            assert screen.selected_agent_id == "codex"
            assert app.focused is view
            assert "Refreshed Codex" in view.document
            assert '"id": "codex"' in view.document
            await pilot.press("q")

    asyncio.run(_run())


def test_agents_delayed_close_cannot_pop_a_newer_screen_instance(mock_home: Path) -> None:
    """A stale Agents instance cannot close the newer Agents screen."""

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test() as pilot:
            await _wait_home(pilot, app)
            await pilot.press("g")
            await pilot.pause()
            first = app.screen
            assert isinstance(first, AgentsScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            await pilot.press("g")
            await pilot.pause()
            second = app.screen
            assert isinstance(second, AgentsScreen) and second is not first
            app.close_agents(first)
            assert app.screen is second
            await pilot.press("q")

    asyncio.run(_run())
