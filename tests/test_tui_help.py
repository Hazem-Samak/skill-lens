"""Headless U8 Help, keymap, lifecycle and empty/error acceptance tests.

Specification reference: ``FULL_SCREEN_TUI.md`` §8.2, §8.5, §9.1, §10,
Step 8 and §22 U8, plus the frozen U8 plan's A1–A9 evidence matrix.

Every test uses the synthetic ``mock_home`` fixture and the protected-system-root
guard from ``tests/conftest.py``; no real ``$HOME`` is read. Worker races use
threading events and bounded waits, never timing sleeps as proof.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Input, Static
from typer.testing import CliRunner

import skill_lens.tui.app as app_module
from skill_lens.cli import app as cli_app
from skill_lens.core.cancellation import CaptureCancelled
from skill_lens.core.exitcodes import ExitCode
from skill_lens.core.snapshot import (
    SnapshotChanged,
    SnapshotTooLarge,
    capture_session,
    snapshot_compare,
    snapshot_diff,
    snapshot_why,
)
from skill_lens.models import dumps
from skill_lens.models.doctor import DoctorFinding, DoctorReport
from skill_lens.models.enums import Evidence, Severity
from skill_lens.tui.agents import AgentsScreen
from skill_lens.tui.app import (
    SkillLensApp,
    ViewReportComplete,
    ViewReportFailed,
)
from skill_lens.tui.compare import CompareScreen
from skill_lens.tui.diff import DiffScreen
from skill_lens.tui.doctor import DoctorScreen
from skill_lens.tui.help import HelpScreen
from skill_lens.tui.home import HomeScreen
from skill_lens.tui.json_view import JsonView
from skill_lens.tui.why import WhyScreen
from tests.fixtures.builders import make_skill
from tests.fixtures.scenarios import build_scenario

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _until(pilot: Any, predicate: Any, label: str, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        await pilot.pause(0.01)
    raise AssertionError(f"timed out waiting for {label}")


async def _wait_ready(pilot: Any, app: SkillLensApp) -> None:
    await _until(
        pilot,
        lambda: (
            app.controller.current is not None
            and app.controller.pending_generation is None
            and app.controller.status == "ready"
        ),
        "ready session",
    )
    await pilot.pause(0.02)


def _help_text(app: SkillLensApp) -> str:
    screen = app.screen
    assert isinstance(screen, HelpScreen)
    return str(screen.query_one("#help-content", Static).content)


def _help_status(app: SkillLensApp) -> str:
    screen = app.screen
    assert isinstance(screen, HelpScreen)
    return str(screen.query_one("#help-session", Static).content)


def _table(app: SkillLensApp) -> DataTable:
    return app.query_one("#skill-table", DataTable)


def _status(app: SkillLensApp) -> str:
    return str(app.query_one("#status-text", Static).content)


def _focused_id(app: SkillLensApp) -> str | None:
    return app.focused.id if app.focused is not None else None


async def _open_help(pilot: Any) -> HelpScreen:
    await pilot.press("question_mark")
    await pilot.pause()
    screen = pilot.app.screen
    assert isinstance(screen, HelpScreen), f"expected Help, got {type(screen).__name__}"
    return screen


async def _dismiss_help(pilot: Any, route: str) -> None:
    """Dismiss through one real key route or the focused Close button."""
    if route == "escape":
        await pilot.press("escape")
    elif route == "backspace":
        await pilot.press("backspace")
    elif route == "question_mark":
        await pilot.press("question_mark")
    elif route == "f1":
        await pilot.press("f1")
    elif route == "close":
        await pilot.press("tab")
        await pilot.pause()
        assert _focused_id(pilot.app) == "help-close"
        await pilot.press("enter")
    else:  # pragma: no cover - guarded by the parametrization
        raise AssertionError(route)
    await pilot.pause()


async def _goto(pilot: Any, app: SkillLensApp, target: str) -> Any:
    """Drive real keys from Home to one supported browsing screen."""
    if target == "home":
        return app.screen
    if target == "why":
        await pilot.press("enter")
    elif target == "diff":
        await pilot.press("enter")
        await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
        await pilot.press("d")
    elif target == "agents":
        await pilot.press("g")
    elif target == "compare-picker":
        await pilot.press("c")
    elif target == "compare-result":
        await pilot.press("c")
        await _until(pilot, lambda: isinstance(app.screen, CompareScreen), "Compare")
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("down")
        await pilot.press("enter")
    elif target == "doctor":
        await pilot.press("h")
    else:  # pragma: no cover - guarded by the parametrization
        raise AssertionError(target)
    expected = {
        "why": WhyScreen,
        "diff": DiffScreen,
        "agents": AgentsScreen,
        "compare-picker": CompareScreen,
        "compare-result": CompareScreen,
        "doctor": DoctorScreen,
    }[target]
    await _until(pilot, lambda: isinstance(app.screen, expected), target)
    if target == "compare-result":
        await _until(
            pilot,
            lambda: app.screen._report_state in {"ready", "error"},
            "compare report",
        )
    else:
        await pilot.pause(0.05)
    return app.screen


async def _wait_workers_settled(pilot: Any, app: SkillLensApp) -> None:
    await _until(
        pilot,
        lambda: app.controller.pending_generation is None and not app.workers._workers,
        "workers settled",
    )


# ---------------------------------------------------------------------------
# A1 — Help over every screen, mode, state and both terminal sizes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "target",
    ["home", "why", "diff", "agents", "compare-picker", "doctor"],
)
def test_help_opens_and_dismisses_from_each_ordinary_screen(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    """A real ``?`` key opens exactly one Help over each ordinary screen."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            origin = await _goto(pilot, app, target)
            assert app.screen is origin

            help_screen = await _open_help(pilot)

            assert app.screen is help_screen
            assert app.screen_stack[-2] is origin
            assert len([s for s in app.screen_stack if isinstance(s, HelpScreen)]) == 1
            assert (
                help_screen.context.origin
                == {
                    "home": "Home",
                    "why": "Why",
                    "diff": "Diff",
                    "agents": "Agents",
                    "compare-picker": "Compare",
                    "doctor": "Doctor",
                }[target]
            )
            body = _help_text(app)
            assert f"Covered screen: {help_screen.context.origin}" in body
            assert f"{help_screen.context.origin.upper()} —" in body
            assert "q / Ctrl+C" in body and "r —" in body
            assert "CAPTURED DATA" in body and "READ-ONLY" in body

            await _dismiss_help(pilot, "escape")

            assert app.screen is origin
            assert not any(isinstance(s, HelpScreen) for s in app.screen_stack)
            await pilot.press("q")

    asyncio.run(_run())


@pytest.mark.parametrize(
    "target",
    ["home", "why", "diff", "agents", "compare-result", "doctor"],
)
def test_help_opens_over_raw_json_modes(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    """Every raw JSON mode opens Help and reports that JSON context accurately."""
    build_scenario("symlink_farm_multi_agent", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            origin = await _goto(pilot, app, target)
            await _until(
                pilot,
                lambda: getattr(origin, "json_mode", False) is False,
                "ordinary origin",
            )
            await pilot.press("J")
            await pilot.pause()
            assert getattr(origin, "json_mode", False) is True

            help_screen = await _open_help(pilot)

            assert (
                help_screen.context.origin
                == {
                    "home": "Home",
                    "why": "Why",
                    "diff": "Diff",
                    "agents": "Agents",
                    "compare-result": "Compare",
                    "doctor": "Doctor",
                }[target]
            )
            assert help_screen.context.mode == "raw JSON view"
            body = _help_text(app)
            assert "raw JSON" in body
            assert "J / Esc / Backspace" in body

            await _dismiss_help(pilot, "escape")

            assert app.screen is origin
            assert getattr(origin, "json_mode", False) is True
            await pilot.press("q")

    asyncio.run(_run())


@pytest.mark.parametrize("size", [(100, 30), (60, 24)])
def test_help_body_and_close_are_reachable_at_both_sizes(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch, size: tuple[int, int]
) -> None:
    """The full body scrolls and the visible Close button closes at both sizes."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=size) as pilot:
            await _wait_ready(pilot, app)
            await _open_help(pilot)
            body = app.screen.query_one("#help-body", VerticalScroll)
            close = app.screen.query_one("#help-close", Button)
            assert body.scroll_offset.y == 0
            assert close.display
            assert close.region.height > 0
            # The close button sits inside the modal's visible region.
            assert close.region.y < size[1]

            await pilot.press("end")
            await pilot.pause()
            assert body.scroll_offset.y > 0
            assert body.scroll_offset.y == body.max_scroll_y

            await pilot.press("home")
            await pilot.pause()
            assert body.scroll_offset.y == 0

            await pilot.press("tab")
            await pilot.pause()
            assert _focused_id(app) == "help-close"
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            await pilot.press("q")

    asyncio.run(_run())


def test_help_opens_during_initial_loading_and_no_session(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Help opens while the first scan is pending and after a cancelled scan."""
    started = threading.Event()
    release = threading.Event()
    real_capture = capture_session

    def blocked_then_cancelled(**kwargs: Any) -> Any:
        started.set()
        release.wait(timeout=5.0)
        raise CaptureCancelled()

    monkeypatch.setattr(app_module, "capture_session", blocked_then_cancelled)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _until(pilot, lambda: started.is_set(), "capture started")
            assert app.controller.current is None
            assert app.controller.status == "loading"

            await _open_help(pilot)
            status = _help_status(app)
            assert "Initial scan in progress" in status
            assert "no catalog has been captured" in status
            assert "0 skills" not in status

            release.set()
            await _until(
                pilot,
                lambda: app.controller.status == "idle",
                "cancelled capture settles",
            )
            # Help stays open with an honest idle/no-session status.
            assert isinstance(app.screen, HelpScreen)
            assert "No session captured yet." in _help_status(app)

            await _dismiss_help(pilot, "escape")
            assert isinstance(app.screen, HomeScreen)
            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    try:
        asyncio.run(_run())
    finally:
        release.set()
        assert real_capture is capture_session


def test_help_no_session_over_agents_and_compare_picker(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No-session screens still accept Help and explain the missing capture."""
    monkeypatch.setattr(
        app_module,
        "capture_session",
        lambda **kwargs: (_ for _ in ()).throw(CaptureCancelled()),
    )

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _until(pilot, lambda: app.controller.status == "idle", "idle")
            await pilot.press("g")
            await pilot.pause()
            assert isinstance(app.screen, AgentsScreen)
            assert "No session captured" in str(
                app.screen.query_one("#agents-empty", Static).content
            )
            await _open_help(pilot)
            assert "No session is captured yet" in _help_text(app)
            await _dismiss_help(pilot, "escape")
            await pilot.press("escape")
            await pilot.pause()

            await pilot.press("c")
            await pilot.pause()
            assert isinstance(app.screen, CompareScreen)
            await _open_help(pilot)
            assert "No captured session is available" in _help_text(app)
            await _dismiss_help(pilot, "escape")
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# A2 — Input typing, F1 toggle, exact restoration and hidden-key isolation
# ---------------------------------------------------------------------------


def test_home_filter_typing_is_literal_and_f1_preserves_text_and_cursor(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``?qrahdgc/J`` types literally; F1 opens/closes without touching it."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("slash")
            await pilot.pause()
            assert _focused_id(app) == "filter-input"
            typed = "?qrahdgc/J"
            for character in typed:
                await pilot.press(character)
            await pilot.pause()
            filter_input = app.query_one("#filter-input", Input)
            assert filter_input.value == typed
            assert filter_input.cursor_position == len(typed)
            assert isinstance(app.screen, HomeScreen)

            # Cursor/backspace behaviour remains Input's own.
            await pilot.press("backspace")
            assert filter_input.value == typed[:-1]
            assert filter_input.cursor_position == len(typed) - 1
            await pilot.press("left")
            assert filter_input.cursor_position == len(typed) - 2
            await pilot.press("backspace")
            assert filter_input.value == "?qrahdg/"
            await pilot.press("end")
            assert filter_input.cursor_position == len(filter_input.value)

            # F1 opens Help over the filter; typing there cannot reach the Input.
            before_value = filter_input.value
            before_cursor = filter_input.cursor_position
            await pilot.press("f1")
            await pilot.pause()
            assert isinstance(app.screen, HelpScreen)
            assert "filter input" in _help_text(app)
            for character in "xyz":
                await pilot.press(character)
            await pilot.pause()
            assert filter_input.value == before_value
            assert filter_input.cursor_position == before_cursor

            # F1 closes the exact Help and restores Input text, cursor and focus.
            await pilot.press("f1")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            assert app.focused is filter_input
            assert filter_input.value == before_value
            assert filter_input.cursor_position == before_cursor
            await pilot.press("q")

    asyncio.run(_run())


def test_plain_question_mark_opens_help_only_outside_the_filter_input(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``?`` is literal in Input and a Help opener on the focused table."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("slash")
            await pilot.press("question_mark")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            assert app.query_one("#filter-input", Input).value == "?"
            await pilot.press("escape")
            await pilot.pause()
            assert app.query_one("#filter-input", Input).value == ""
            assert app.focused is _table(app)
            await pilot.press("question_mark")
            await pilot.pause()
            assert isinstance(app.screen, HelpScreen)
            await pilot.press("q")

    asyncio.run(_run())


@pytest.mark.parametrize("route", ["escape", "backspace", "question_mark", "f1", "close"])
def test_every_dismiss_route_restores_exact_input_focus_text_and_cursor(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    """Esc, Backspace, ?, F1 and Close each close one Help and restore the Input."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("slash")
            for character in "deploy":
                await pilot.press(character)
            await pilot.press("left")
            await pilot.press("left")
            filter_input = app.query_one("#filter-input", Input)
            value = filter_input.value
            cursor = filter_input.cursor_position

            await pilot.press("f1")
            await pilot.pause()
            help_screen = app.screen
            assert isinstance(help_screen, HelpScreen)
            await _dismiss_help(pilot, route)

            assert isinstance(app.screen, HomeScreen)
            assert app.focused is filter_input
            assert filter_input.value == value
            assert filter_input.cursor_position == cursor
            assert not any(isinstance(s, HelpScreen) for s in app.screen_stack)
            await pilot.press("q")

    asyncio.run(_run())


def test_every_dismiss_route_restores_table_focus_and_preview_scroll(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Help restores the exact table focus and a positive preview scroll."""
    build_scenario("symlink_farm_multi_agent", mock_home)
    for index in range(12):
        make_skill(
            mock_home / ".claude" / "skills" / f"filler-{index:02d}",
            f"filler-{index:02d}",
            "Filler description long enough to make the preview scroll. " * 3,
        )

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            table = _table(app)
            await _until(pilot, lambda: table.row_count > 0, "rows")
            preview = app.query_one("#preview-scroll", VerticalScroll)
            await pilot.press("tab")
            await pilot.pause()
            # Move focus to the preview and scroll it explicitly.
            while app.focused is not preview:
                await pilot.press("tab")
                await pilot.pause()
                if app.focused is table:
                    await pilot.press("tab")
                    await pilot.pause()
            preview.scroll_to(y=3, animate=False)
            await pilot.pause()
            assert preview.scroll_offset.y > 0 or preview.max_scroll_y == 0
            before = preview.scroll_offset.y

            await pilot.press("f1")
            await pilot.pause()
            await _dismiss_help(pilot, "escape")

            assert app.screen is app.screen_stack[-1]
            assert app.focused is preview or preview.max_scroll_y == 0
            assert preview.scroll_offset.y == before
            await pilot.press("q")

    asyncio.run(_run())


@pytest.mark.parametrize(
    "target,hidden_keys",
    [
        ("home", ["d", "h", "g", "c", "J", "enter", "slash", "a", "j", "k"]),
        ("why", ["d", "J", "left", "right"]),
        ("diff", ["J"]),
        ("agents", ["J", "enter"]),
        ("compare-picker", ["J", "enter"]),
        ("doctor", ["J", "enter"]),
    ],
)
def test_hidden_screen_actions_cannot_leak_through_help(
    mock_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    hidden_keys: list[str],
) -> None:
    """Covered screen keys do nothing while Help is the active modal."""
    scenario = (
        "symlink_farm_multi_agent"
        if target == "compare-picker"
        else "claude_personal_beats_project"
    )
    build_scenario(scenario, mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            origin = await _goto(pilot, app, target)
            help_screen = await _open_help(pilot)
            stack_before = tuple(app.screen_stack)
            selection_before = app.controller.selected_key

            for key in hidden_keys:
                await pilot.press(key)
                await pilot.pause(0.01)
                assert app.screen is help_screen, f"{key} left Help"
                assert tuple(app.screen_stack) == stack_before
            assert app.controller.selected_key == selection_before
            assert origin is stack_before[-2]
            await _dismiss_help(pilot, "escape")
            assert app.screen is origin
            await pilot.press("q")

    asyncio.run(_run())


def test_help_does_not_stack_and_stale_instance_cannot_close_a_newer_help(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Repeated opens keep one Help; a stale close cannot pop the newer instance."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            first = await _open_help(pilot)
            app.open_help()  # repeated open while Help is active
            app.action_open_help()
            await pilot.pause()
            assert app.screen is first
            assert (
                len([screen for screen in app.screen_stack if isinstance(screen, HelpScreen)]) == 1
            )
            await pilot.press("question_mark")  # closes the first
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            second = await _open_help(pilot)
            assert second is not first
            stack = tuple(app.screen_stack)

            first.action_dismiss_help()  # stale instance callback
            await pilot.pause()
            assert app.screen is second
            assert tuple(app.screen_stack) == stack

            app.close_help(first)  # stale host call
            await pilot.pause()
            assert app.screen is second

            await _dismiss_help(pilot, "escape")
            assert isinstance(app.screen, HomeScreen)
            assert app.focused is _table(app)
            await pilot.press("q")

    asyncio.run(_run())


def test_f1_toggles_help_while_typing_and_does_not_lose_priority(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The app priority F1 opens and closes Help while Input keeps its state."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("slash")
            for character in "dep":
                await pilot.press(character)
            filter_input = app.query_one("#filter-input", Input)
            assert filter_input.value == "dep"

            await pilot.press("f1")
            await pilot.pause()
            assert isinstance(app.screen, HelpScreen)
            await pilot.press("f1")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            assert app.focused is filter_input
            assert filter_input.value == "dep"
            assert filter_input.cursor_position == 3

            # F1 from a covered JSON screen does not close a second time.
            await pilot.press("enter")
            await pilot.pause()
            assert app.focused is _table(app)
            await pilot.press("f1")
            await pilot.pause()
            assert isinstance(app.screen, HelpScreen)
            await pilot.press("f1")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            await pilot.press("q")

    asyncio.run(_run())


def test_tab_and_shift_tab_stay_inside_help_and_enter_on_body_does_nothing(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tab cycles only body and Close; Enter on the body cannot dismiss or act."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            help_screen = await _open_help(pilot)
            assert _focused_id(app) == "help-body"
            await pilot.press("enter")
            await pilot.pause()
            assert app.screen is help_screen
            await pilot.press("tab")
            await pilot.pause()
            assert _focused_id(app) == "help-close"
            await pilot.press("tab")
            await pilot.pause()
            assert _focused_id(app) == "help-body"
            await pilot.press("shift+tab")
            await pilot.pause()
            assert _focused_id(app) == "help-close"
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            await pilot.press("q")

    asyncio.run(_run())


def test_help_body_scroll_keys_and_explicit_close_route(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Arrows, PageDown, PageUp, End and Home scroll; the Close button dismisses."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await _open_help(pilot)
            body = app.screen.query_one("#help-body", VerticalScroll)
            await pilot.press("down")
            await pilot.pause()
            assert body.scroll_offset.y >= 1
            await pilot.press("pagedown")
            await pilot.pause()
            paged = body.scroll_offset.y
            assert paged >= 2
            await pilot.press("pageup")
            await pilot.pause()
            assert body.scroll_offset.y <= paged
            await pilot.press("end")
            await pilot.pause()
            assert body.scroll_offset.y == body.max_scroll_y
            await pilot.press("home")
            await pilot.pause()
            assert body.scroll_offset.y == 0

            await pilot.click("#help-close")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# A3 — Delayed Home/Why/Diff/Compare work, exact ownership and reveal resume
# ---------------------------------------------------------------------------


def test_home_why_job_is_suspended_and_restarted_once(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Covering Home cancels its own Why token, rejects the old result and asks once."""
    build_scenario("symlink_farm_multi_agent", mock_home)
    calls: list[tuple[str, str]] = []
    first_started = threading.Event()
    release_first = threading.Event()
    real_why = snapshot_why

    def controlled_why(snapshot: Any, key: str, agent_id: str) -> Any:
        calls.append((key, agent_id))
        if len(calls) == 1:
            first_started.set()
            release_first.wait(timeout=5.0)
        return real_why(snapshot, key, agent_id)

    monkeypatch.setattr(app_module, "snapshot_why", controlled_why)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home = app.screen
            assert isinstance(home, HomeScreen)
            await pilot.press("a")  # activate an agent filter, which drives Why work
            await _until(
                pilot,
                lambda: first_started.is_set() and home._inflight is not None,
                "first Why request",
            )
            owned = home._inflight
            assert owned is not None
            event = app.controller._report_events.get(owned.request.request_id)
            assert event is not None and not event.is_set()
            calls_before = len(calls)

            await _open_help(pilot)

            assert home._suspended
            assert event.is_set()
            assert "why" not in app.controller.active_requests
            release_first.set()
            await _until(pilot, lambda: not app.workers._workers, "cancelled worker settles")
            assert len(calls) == calls_before, "Help open must not start replacement work"
            assert not any(key[1] == "why" for key in app.controller.cache)
            assert not app.controller.is_failed
            assert "ACCEPTED INTERNAL FAULT" not in _help_status(app)

            await _dismiss_help(pilot, "escape")

            await _until(pilot, lambda: len(calls) == 2, "one replacement request")
            await pilot.pause()
            await _until(pilot, lambda: not app.workers._workers, "replacement settles")
            assert len(calls) == 2
            assert any(key[1] == "why" for key in app.controller.cache)

            # A cached report is reused: opening and closing Help starts no work.
            await _open_help(pilot)
            await _dismiss_help(pilot, "escape")
            await pilot.pause()
            assert len(calls) == 2
            await pilot.press("q")

    asyncio.run(_run())


def test_why_detail_job_is_suspended_and_restarted_once(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Covering Why cancels only its owned report and resumes with one request."""
    build_scenario("claude_personal_beats_project", mock_home)
    calls: list[tuple[str, str]] = []
    first_started = threading.Event()
    release_first = threading.Event()
    real_why = snapshot_why

    def controlled_why(snapshot: Any, key: str, agent_id: str) -> Any:
        calls.append((key, agent_id))
        if len(calls) == 1:
            first_started.set()
            release_first.wait(timeout=5.0)
        return real_why(snapshot, key, agent_id)

    monkeypatch.setattr(app_module, "snapshot_why", controlled_why)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            why = app.screen
            await _until(
                pilot,
                lambda: first_started.is_set() and why._owned_request is not None,
                "first Why request",
            )
            owned = why._owned_request
            assert owned is not None
            event = app.controller._report_events.get(owned.request_id)
            assert event is not None and not event.is_set()

            await _open_help(pilot)

            assert why._suspended
            assert event.is_set()
            assert "why" not in app.controller.active_requests
            release_first.set()
            await _until(pilot, lambda: not app.workers._workers, "cancelled worker settles")
            assert not app.controller.cache
            assert not app.controller.is_failed

            await _dismiss_help(pilot, "escape")

            await _until(pilot, lambda: len(calls) == 2, "one replacement request")
            await _until(pilot, lambda: why._report is not None, "report ready")
            assert len(calls) == 2

            # Both the explicit and native resume paths ran; a third manual
            # resume must remain idempotent and start no new work.
            why.resume_help()
            await pilot.pause()
            assert len(calls) == 2

            await _open_help(pilot)
            await _dismiss_help(pilot, "escape")
            await pilot.pause()
            assert len(calls) == 2
            await pilot.press("q")

    asyncio.run(_run())


def test_diff_job_is_suspended_and_restarted_once(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Covering Diff cancels its own token; reveal asks exactly once on a miss."""
    build_scenario("claude_personal_beats_project", mock_home)
    calls: list[tuple[str, ...]] = []
    first_started = threading.Event()
    release_first = threading.Event()
    real_diff = snapshot_diff

    def controlled_diff(snapshot: Any, key: str) -> Any:
        calls.append((key,))
        if len(calls) == 1:
            first_started.set()
            release_first.wait(timeout=5.0)
        return real_diff(snapshot, key)

    monkeypatch.setattr(app_module, "snapshot_diff", controlled_diff)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            await pilot.press("d")
            await _until(pilot, lambda: isinstance(app.screen, DiffScreen), "Diff")
            diff = app.screen
            await _until(
                pilot,
                lambda: first_started.is_set() and diff._owned_request is not None,
                "first Diff request",
            )
            owned = diff._owned_request
            assert owned is not None
            event = app.controller._report_events.get(owned.request_id)
            assert event is not None and not event.is_set()

            await _open_help(pilot)

            assert diff._suspended
            assert event.is_set()
            assert "diff" not in app.controller.active_requests
            release_first.set()
            await _until(pilot, lambda: not app.workers._workers, "cancelled worker settles")
            assert not any(key[1] == "diff" for key in app.controller.cache)
            assert not app.controller.is_failed

            await _dismiss_help(pilot, "escape")
            await pilot.pause()
            assert len(calls) >= 2 or diff.report is not None, "reveal must resume Diff work"

            await _until(pilot, lambda: len(calls) == 2, "one replacement request")
            await _until(pilot, lambda: diff.report is not None, "Diff report ready")
            assert len(calls) == 2

            diff.resume_help()
            await pilot.pause()
            assert len(calls) == 2
            await _open_help(pilot)
            await _dismiss_help(pilot, "escape")
            await pilot.pause()
            assert len(calls) == 2
            await pilot.press("q")

    asyncio.run(_run())


def test_compare_job_is_suspended_and_restarted_once(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Covering Compare cancels its pair request and resumes with one request."""
    build_scenario("symlink_farm_multi_agent", mock_home)
    calls: list[tuple[str, str]] = []
    first_started = threading.Event()
    release_first = threading.Event()
    real_compare = snapshot_compare

    def controlled_compare(snapshot: Any, agent_a: str, agent_b: str) -> Any:
        calls.append((agent_a, agent_b))
        if len(calls) == 1:
            first_started.set()
            release_first.wait(timeout=5.0)
        return real_compare(snapshot, agent_a, agent_b)

    monkeypatch.setattr(app_module, "snapshot_compare", controlled_compare)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("c")
            await _until(pilot, lambda: isinstance(app.screen, CompareScreen), "Compare")
            compare = app.screen
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("down")
            await pilot.press("enter")
            await _until(
                pilot,
                lambda: first_started.is_set() and compare.owned_request is not None,
                "first Compare request",
            )
            owned = compare.owned_request
            assert owned is not None
            event = app.controller._report_events.get(owned.request_id)
            assert event is not None and not event.is_set()

            await _open_help(pilot)

            assert compare._suspended
            assert event.is_set()
            assert "compare" not in app.controller.active_requests
            release_first.set()
            await _until(pilot, lambda: not app.workers._workers, "cancelled worker settles")
            assert not any(key[1] == "compare" for key in app.controller.cache)
            assert not app.controller.is_failed

            await _dismiss_help(pilot, "escape")

            await _until(pilot, lambda: len(calls) == 2, "one replacement request")
            await _until(pilot, lambda: compare.report is not None, "Compare report ready")
            assert compare.mode == "result"
            assert len(calls) == 2

            compare.resume_help()
            await pilot.pause()
            assert len(calls) == 2
            await _open_help(pilot)
            await _dismiss_help(pilot, "escape")
            await pilot.pause()
            assert len(calls) == 2
            await pilot.press("q")

    asyncio.run(_run())


def test_help_cancels_only_the_covered_screens_own_token(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A report owned by another view survives Home's Help suspension."""
    build_scenario("symlink_farm_multi_agent", mock_home)
    started = threading.Event()
    release = threading.Event()
    real_compare = snapshot_compare

    def controlled_compare(snapshot: Any, agent_a: str, agent_b: str) -> Any:
        started.set()
        release.wait(timeout=5.0)
        return real_compare(snapshot, agent_a, agent_b)

    monkeypatch.setattr(app_module, "snapshot_compare", controlled_compare)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            app.request_report("compare", ("claude", "codex"))
            await _until(pilot, lambda: started.is_set(), "Compare request")
            owned = app.controller.active_requests.get("compare")
            assert owned is not None
            event = app.controller._report_events.get(owned.request_id)
            assert event is not None and not event.is_set()

            await _open_help(pilot)

            assert app.controller.active_requests.get("compare") == owned
            assert not event.is_set()
            release.set()
            await _until(pilot, lambda: not app.workers._workers, "Compare worker settles")
            assert app.controller.get_cached_report("compare", ("claude", "codex")) is not None
            await _dismiss_help(pilot, "escape")
            await pilot.press("q")

    asyncio.run(_run())


def test_old_successes_and_errors_cannot_affect_newer_work_or_sticky_state(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stale Diff outcomes are rejected before/after Help; a current fault is sticky."""
    build_scenario("claude_personal_beats_project", mock_home)
    calls: list[int] = []
    first_started = threading.Event()
    release_first = threading.Event()
    second_started = threading.Event()
    release_second = threading.Event()
    real_diff = snapshot_diff

    def controlled_diff(snapshot: Any, key: str) -> Any:
        calls.append(1)
        if len(calls) == 1:
            first_started.set()
            release_first.wait(timeout=5.0)
        elif len(calls) == 2:
            second_started.set()
            release_second.wait(timeout=5.0)
        return real_diff(snapshot, key)

    monkeypatch.setattr(app_module, "snapshot_diff", controlled_diff)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            await pilot.press("d")
            await _until(pilot, lambda: isinstance(app.screen, DiffScreen), "Diff")
            diff = app.screen
            await _until(
                pilot,
                lambda: first_started.is_set() and diff._owned_request is not None,
                "first request",
            )
            first = diff._owned_request
            assert first is not None
            first_id = first.request_id
            generation = first.generation
            arguments = first.arguments
            old_report = snapshot_diff(app.controller.current, arguments[0])

            await _open_help(pilot)
            # A stale success and a stale error while Help is open are rejected.
            release_first.set()
            app.on_view_report_complete(
                ViewReportComplete("diff", first_id, generation, arguments, old_report)
            )
            app.on_view_report_failed(
                ViewReportFailed("diff", first_id, generation, arguments, RuntimeError("old fault"))
            )
            await pilot.pause()
            assert not app.controller.is_failed
            assert "ACCEPTED INTERNAL FAULT" not in _help_status(app)

            await _dismiss_help(pilot, "escape")
            await _until(
                pilot,
                lambda: second_started.is_set() and diff._owned_request is not None,
                "second request",
            )
            second = diff._owned_request
            assert second is not None and second.request_id != first_id

            # The other order: stale outcomes after Help has closed.
            app.on_view_report_complete(
                ViewReportComplete("diff", first_id, generation, arguments, old_report)
            )
            app.on_view_report_failed(
                ViewReportFailed("diff", first_id, generation, arguments, RuntimeError("old fault"))
            )
            await pilot.pause()
            assert diff.report is None
            assert diff._owned_request == second
            assert not app.controller.is_failed

            # A current accepted unexpected error is sticky and visible in Help.
            app.on_view_report_failed(
                ViewReportFailed(
                    "diff",
                    second.request_id,
                    second.generation,
                    second.arguments,
                    RuntimeError("current fatal fault"),
                )
            )
            await pilot.pause()
            assert app.controller.is_failed
            await _open_help(pilot)
            status = _help_status(app)
            assert "ACCEPTED INTERNAL FAULT" in status
            assert "current fatal fault" in status
            release_second.set()
            await _dismiss_help(pilot, "escape")
            await pilot.press("q")
            assert app.return_code == int(ExitCode.INTERNAL)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# A4 — Capture/refresh state reconciliation, removals, faults and exits
# ---------------------------------------------------------------------------


def test_help_during_held_initial_capture_defers_home_and_updates_status(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Help stays open while the first capture publishes; Home reconciles on reveal."""
    build_scenario("claude_personal_beats_project", mock_home)
    started = threading.Event()
    release = threading.Event()
    real_capture = capture_session

    def controlled_capture(**kwargs: Any) -> Any:
        started.set()
        release.wait(timeout=5.0)
        return real_capture(**kwargs)

    monkeypatch.setattr(app_module, "capture_session", controlled_capture)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _until(pilot, lambda: started.is_set(), "capture started")
            await _open_help(pilot)
            assert "Initial scan in progress" in _help_status(app)

            release.set()
            await _until(pilot, lambda: app.controller.current is not None, "capture published")
            await pilot.pause(0.05)
            assert isinstance(app.screen, HelpScreen)
            status = _help_status(app)
            assert "Ready: 1 skills discovered." in status
            assert "Initial scan" not in status
            # Reconciliation is deferred: the covered Home table is still empty.
            assert _table(app).row_count == 0

            await _dismiss_help(pilot, "escape")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            assert _table(app).row_count == 1
            assert app.focused is _table(app)
            await pilot.press("q")

    try:
        asyncio.run(_run())
    finally:
        release.set()


def test_out_of_order_refreshes_keep_help_open_and_newest_wins(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Help remains open across overlapping refreshes; reveal uses the newest capture."""
    build_scenario("claude_personal_beats_project", mock_home)
    real_capture = capture_session
    started: dict[int, threading.Event] = {}
    release: dict[int, threading.Event] = {}
    calls: list[int] = []

    def controlled_capture(**kwargs: Any) -> Any:
        generation = int(kwargs["generation"])
        calls.append(generation)
        snapshot = real_capture(**kwargs)
        if generation >= 2:
            started.setdefault(generation, threading.Event()).set()
            release.setdefault(generation, threading.Event()).wait(timeout=5.0)
        return snapshot

    monkeypatch.setattr(app_module, "capture_session", controlled_capture)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            assert _table(app).row_count == 1
            make_skill(
                mock_home / ".claude" / "skills" / "second-skill",
                "second-skill",
                "Added after the first capture.",
            )
            await _open_help(pilot)
            await _dismiss_help(pilot, "f1")
            await _open_help(pilot)

            await pilot.press("r")
            await _until(pilot, lambda: 2 in started, "generation 2 started")
            await pilot.press("r")
            await _until(pilot, lambda: 3 in started, "generation 3 started")

            # Newest finishes first and is published while Help stays open.
            release[3].set()
            await _until(
                pilot,
                lambda: (
                    app.controller.current is not None
                    and app.controller.current.generation == 3
                    and app.controller.pending_generation is None
                ),
                "generation 3 published",
            )
            assert isinstance(app.screen, HelpScreen)
            assert "Captured generation 3: 2 skills." in _help_status(app)
            # The covered Home table has not reconciled yet.
            assert _table(app).row_count == 1

            # The older generation finishing last cannot replace it.
            release[2].set()
            await _until(pilot, lambda: not app.workers._workers, "old worker settles")
            assert app.controller.current is not None
            assert app.controller.current.generation == 3
            assert isinstance(app.screen, HelpScreen)

            await _dismiss_help(pilot, "escape")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            assert _table(app).row_count == 2
            assert app.controller.current.generation == 3
            await pilot.press("q")

    try:
        asyncio.run(_run())
    finally:
        for event in release.values():
            event.set()


def test_help_over_why_survives_removal_and_closes_why_on_reveal(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A refresh that removes the opening installation does not pop Help."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            why = app.screen
            await _open_help(pilot)

            import shutil

            shutil.rmtree(mock_home / ".claude" / "skills" / "deploy")
            await pilot.press("r")
            await _until(
                pilot,
                lambda: (
                    app.controller.current is not None
                    and app.controller.current.generation == 2
                    and app.controller.pending_generation is None
                ),
                "second capture",
            )
            assert isinstance(app.screen, HelpScreen)
            assert why._suspended

            await _dismiss_help(pilot, "escape")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            assert not any(isinstance(screen, WhyScreen) for screen in app.screen_stack)
            notice = str(app.query_one("#removal-notice", Static).content)
            assert "was removed during refresh" in notice
            await pilot.press("q")

    asyncio.run(_run())


def test_help_over_diff_survives_removal_and_closes_diff_on_reveal(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A removed Diff installation closes only after Help reveals its origin."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            await pilot.press("d")
            await _until(pilot, lambda: isinstance(app.screen, DiffScreen), "Diff")
            diff = app.screen
            await _open_help(pilot)

            import shutil

            shutil.rmtree(mock_home / ".claude" / "skills" / "deploy")
            await pilot.press("r")
            await _until(
                pilot,
                lambda: (
                    app.controller.current is not None
                    and app.controller.current.generation == 2
                    and app.controller.pending_generation is None
                ),
                "second capture",
            )
            assert isinstance(app.screen, HelpScreen)
            assert diff._suspended

            await _dismiss_help(pilot, "escape")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            assert not any(isinstance(screen, DiffScreen) for screen in app.screen_stack)
            notice = str(app.query_one("#removal-notice", Static).content)
            assert "was removed during refresh" in notice
            await pilot.press("q")

    asyncio.run(_run())


def test_help_over_compare_result_survives_removed_agent_and_returns_to_picker(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A removed Compare choice is cleared after reveal, never substituted."""
    build_scenario("symlink_farm_multi_agent", mock_home)
    real_capture = capture_session

    def controlled_capture(**kwargs: Any) -> Any:
        snapshot = real_capture(**kwargs)
        if int(kwargs["generation"]) >= 2:
            snapshot = replace(
                snapshot,
                registry=tuple(agent for agent in snapshot.registry if agent.id != "claude"),
            )
        return snapshot

    monkeypatch.setattr(app_module, "capture_session", controlled_capture)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("c")
            await _until(pilot, lambda: isinstance(app.screen, CompareScreen), "Compare")
            compare = app.screen
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("down")
            await pilot.press("enter")
            await _until(pilot, lambda: compare.report is not None, "Compare report")
            assert compare.mode == "result"
            assert compare.selected_pair is not None
            assert compare.selected_pair[1] == "claude"

            await _open_help(pilot)
            await pilot.press("r")
            await _until(
                pilot,
                lambda: (
                    app.controller.current is not None
                    and app.controller.current.generation == 2
                    and app.controller.pending_generation is None
                ),
                "second capture",
            )
            assert isinstance(app.screen, HelpScreen)

            await _dismiss_help(pilot, "escape")
            await pilot.pause()
            assert isinstance(app.screen, CompareScreen)
            assert compare.mode == "picker"
            assert compare.selected_pair is None
            assert "was removed during refresh" in compare._input_error
            await pilot.press("q")

    asyncio.run(_run())


def test_help_over_loading_json_never_shows_a_stale_document(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A report accepted while Help is open reaches JSON only after reveal."""
    build_scenario("claude_personal_beats_project", mock_home)
    started = threading.Event()
    release = threading.Event()
    real_why = snapshot_why

    def controlled_why(snapshot: Any, key: str, agent_id: str) -> Any:
        started.set()
        release.wait(timeout=5.0)
        return real_why(snapshot, key, agent_id)

    monkeypatch.setattr(app_module, "snapshot_why", controlled_why)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            why = app.screen
            await _until(pilot, lambda: started.is_set(), "Why request started")
            await pilot.press("J")
            await pilot.pause()
            view = why.query_one("#why-json", JsonView)
            assert view.shows_document is False
            assert "Loading report" in view.displayed_text

            await pilot.press("f1")
            await pilot.pause()
            assert isinstance(app.screen, HelpScreen)
            release.set()
            await _until(pilot, lambda: not app.workers._workers, "report accepted")
            assert view.shows_document is False
            assert "Loading report" in view.displayed_text

            await _dismiss_help(pilot, "escape")
            await _until(pilot, lambda: view.shows_document, "JSON document after reveal")
            assert view.document is not None
            assert json.loads(view.document)["skill_name"] == "deploy"
            await pilot.press("q")

    asyncio.run(_run())


@pytest.mark.parametrize("failure", ["refused", "retry", "fault"])
def test_help_status_without_prior_data_is_literal_and_exit_is_correct(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """Refusal, retry and fault are distinct before any catalog exists."""
    build_scenario("claude_personal_beats_project", mock_home)
    started = threading.Event()
    release = threading.Event()

    def failing_capture(**kwargs: Any) -> Any:
        started.set()
        release.wait(timeout=5.0)
        if failure == "refused":
            raise SnapshotTooLarge(total_bytes=2 * 1024 * 1024, limit_bytes=1024 * 1024)
        if failure == "retry":
            raise SnapshotChanged()
        raise RuntimeError("initial boom")

    monkeypatch.setattr(app_module, "capture_session", failing_capture)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(60, 24)) as pilot:
            await _until(pilot, lambda: started.is_set(), "capture started")
            await _open_help(pilot)
            release.set()
            await _until(
                pilot,
                lambda: app.controller.status in {"refused", "retry", "error"},
                "failure accepted",
            )
            assert isinstance(app.screen, HelpScreen)
            status = _help_status(app)
            body = _help_text(app)
            if failure == "refused":
                assert "Snapshot refused" in status
                assert "retrying unchanged inputs cannot help" in status
                assert "Press r to retry" not in status
                assert "Retained data" not in status
                expected_code = ExitCode.OK
            elif failure == "retry":
                assert "Press r to retry" in status
                assert "expected capture inconsistency" in status
                assert "ACCEPTED INTERNAL FAULT" not in status
                expected_code = ExitCode.OK
            else:
                assert "ACCEPTED INTERNAL FAULT" in status
                assert "initial boom" in status
                expected_code = ExitCode.INTERNAL
            assert "CAPTURED DATA" in body

            await _dismiss_help(pilot, "escape")
            assert isinstance(app.screen, HomeScreen)
            await pilot.press("q")
            assert app.return_code == int(expected_code)

    try:
        asyncio.run(_run())
    finally:
        release.set()


@pytest.mark.parametrize("failure", ["refused", "retry", "fault"])
def test_help_status_with_prior_data_keeps_retained_wording_and_data(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """A failed refresh with retained data is labelled as retained, not current."""
    build_scenario("claude_personal_beats_project", mock_home)
    real_capture = capture_session
    second_started = threading.Event()
    release_second = threading.Event()

    def controlled_capture(**kwargs: Any) -> Any:
        if int(kwargs["generation"]) == 1:
            return real_capture(**kwargs)
        second_started.set()
        release_second.wait(timeout=5.0)
        if failure == "refused":
            raise SnapshotTooLarge(total_bytes=2 * 1024 * 1024, limit_bytes=1024 * 1024)
        if failure == "retry":
            raise SnapshotChanged()
        raise RuntimeError("refresh boom")

    monkeypatch.setattr(app_module, "capture_session", controlled_capture)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            assert _table(app).row_count == 1
            await _open_help(pilot)
            await pilot.press("r")
            await _until(pilot, lambda: second_started.is_set(), "refresh started")
            release_second.set()
            await _until(
                pilot,
                lambda: app.controller.status in {"refused", "retry", "error"},
                "failure accepted",
            )
            assert isinstance(app.screen, HelpScreen)
            status = _help_status(app)
            assert "Captured generation 1: 1 skills." in status
            assert "Retained data" in status
            if failure == "refused":
                assert "retrying unchanged inputs cannot help" in status
                expected_code = ExitCode.OK
            elif failure == "retry":
                assert "Press r to retry" in status
                expected_code = ExitCode.OK
            else:
                assert "ACCEPTED INTERNAL FAULT" in status
                assert "refresh boom" in status
                expected_code = ExitCode.INTERNAL
            # The covered Home table still holds the previous catalog.
            assert _table(app).row_count == 1

            await _dismiss_help(pilot, "escape")
            assert isinstance(app.screen, HomeScreen)
            assert _table(app).row_count == 1
            await pilot.press("q")
            assert app.return_code == int(expected_code)

    try:
        asyncio.run(_run())
    finally:
        release_second.set()


def test_quit_during_slow_work_through_help_is_prompt_and_cooperative(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """q from Help exits without waiting for a blocked capture worker."""
    started = threading.Event()
    release = threading.Event()

    def blocked_capture(**kwargs: Any) -> Any:
        started.set()
        release.wait(timeout=5.0)
        raise CaptureCancelled()

    monkeypatch.setattr(app_module, "capture_session", blocked_capture)
    watchdog = threading.Timer(2.0, release.set)
    watchdog.daemon = True
    watchdog.start()

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _until(pilot, lambda: started.is_set(), "capture started")
            await _open_help(pilot)
            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    try:
        asyncio.run(_run())
    finally:
        release.set()
        watchdog.cancel()


# ---------------------------------------------------------------------------
# A5 — Complete keyboard browsing flow and captured-data (no live fallback)
# ---------------------------------------------------------------------------


def _home_row_keys(app: SkillLensApp) -> list[str]:
    table = _table(app)
    return [
        str(table.coordinate_to_cell_key((index, 0)).row_key.value)
        for index in range(table.row_count)
    ]


async def _select_home_key(pilot: Any, app: SkillLensApp, key: str) -> None:
    table = _table(app)
    target = _home_row_keys(app).index(key)
    for _ in range(table.row_count + 1):
        if table.cursor_row == target:
            break
        await pilot.press("down" if table.cursor_row < target else "up")
        await pilot.pause(0.01)
    await pilot.pause(0.02)
    assert app.controller.selected_key == key


def test_complete_keyboard_browsing_flow_with_help_json_filters_and_refresh(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Home → Why → Diff → Agents → Compare → Doctor with Help and JSON everywhere."""
    build_scenario("symlink_farm_multi_agent", mock_home)
    make_skill(
        mock_home / ".claude" / "skills" / "literal",
        "literal",
        "Markup-like [bold]literal[/bold] and <angle> stay text.",
    )
    real_capture = capture_session

    def capture_with_finding(**kwargs: Any) -> Any:
        snapshot = real_capture(**kwargs)
        entry = next(item for item in snapshot.index.entries if item.name == "shared")
        finding = DoctorFinding(
            code="u8_flow",
            severity=Severity.INFO,
            message="Captured shared skill.",
            rule_id="u8_flow_rule",
            evidence=Evidence.EMPIRICAL,
            path=entry.entrypoint_path,
            detail="in-app selection only",
        )
        report = DoctorReport(snapshot.doctor.home, snapshot.doctor.cwd, (finding,))
        scan = replace(
            snapshot.scan,
            unreadable=(
                {
                    "agent": "claude",
                    "root": "claude_personal",
                    "path": "~/.claude/skills/blocked",
                    "detail": "denied",
                },
            ),
        )
        return replace(snapshot, scan=scan, doctor=report)

    monkeypatch.setattr(app_module, "capture_session", capture_with_finding)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            snapshot = app.controller.current
            assert snapshot is not None
            assert _table(app).row_count == len(snapshot.scan.skills)
            note = str(app.query_one("#catalog-note", Static).content)
            assert "Unreadable roots" in note
            assert "blocked" in note

            # Home Help, then literal filter typing and full-scan JSON.
            await _open_help(pilot)
            assert "Home — ordinary list" in _help_text(app)
            await _dismiss_help(pilot, "escape")
            await pilot.press("slash")
            await pilot.press(*"literal")
            await pilot.pause()
            assert _table(app).row_count == 1
            preview = str(app.query_one("#preview-pane", Static).content)
            assert "[bold]literal[/bold]" in preview
            assert "<angle>" in preview
            await pilot.press("enter")
            await pilot.press("J")
            await pilot.pause()
            document = app.screen.query_one("#home-json", JsonView).document
            assert document is not None
            parsed = json.loads(document)
            descriptions = [row.get("description") for row in parsed["skills"]]
            assert "Markup-like [bold]literal[/bold] and <angle> stay text." in descriptions
            assert len(parsed["skills"]) == len(snapshot.scan.skills)
            await pilot.press("escape")  # leave JSON
            await pilot.press("escape")  # clear the filter
            await pilot.pause()
            assert app.query_one("#filter-input", Input).value == ""
            assert _table(app).row_count == len(snapshot.scan.skills)

            # Why with a real agent switch, Help and raw JSON.
            shared_key = next(key for key in _home_row_keys(app) if key.endswith("/shared"))
            await _select_home_key(pilot, app, shared_key)
            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            why = app.screen
            await _until(pilot, lambda: why._report is not None, "Why report")
            first_agent = why._agent_id
            await pilot.press("right")
            await pilot.pause()
            assert why._agent_id != first_agent
            await _open_help(pilot)
            assert "Why — resolution detail" in _help_text(app)
            assert "agent strip" in _help_text(app)
            await _dismiss_help(pilot, "escape")
            await pilot.press("J")
            await pilot.pause()
            why_document = why.query_one("#why-json", JsonView).document
            assert why_document is not None
            await _open_help(pilot)
            assert app.screen.context.mode == "raw JSON view"
            await _dismiss_help(pilot, "escape")
            await pilot.press("J")
            await pilot.pause()

            # Diff with Help and raw JSON.
            await pilot.press("d")
            await _until(pilot, lambda: isinstance(app.screen, DiffScreen), "Diff")
            diff = app.screen
            await _until(pilot, lambda: diff.report is not None, "Diff report")
            await _open_help(pilot)
            assert app.screen.context.origin == "Diff"
            await _dismiss_help(pilot, "escape")
            await pilot.press("J")
            await pilot.pause()
            assert diff.query_one("#diff-json", JsonView).document is not None
            await _open_help(pilot)
            assert app.screen.context.mode == "raw JSON view"
            await _dismiss_help(pilot, "escape")
            await pilot.press("J")
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why again")
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")

            # Agents with Help and JSON.
            await pilot.press("g")
            await _until(pilot, lambda: isinstance(app.screen, AgentsScreen), "Agents")
            agents = app.screen
            await _open_help(pilot)
            assert app.screen.context.origin == "Agents"
            await _dismiss_help(pilot, "escape")
            await pilot.press("J")
            await pilot.pause()
            assert agents.query_one("#agents-json", JsonView).document is not None
            await _open_help(pilot)
            assert app.screen.context.mode == "raw JSON view"
            await _dismiss_help(pilot, "escape")
            await pilot.press("J")
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")

            # Compare picker/result with Help and JSON.
            await pilot.press("c")
            await _until(pilot, lambda: isinstance(app.screen, CompareScreen), "Compare")
            compare = app.screen
            await _open_help(pilot)
            assert app.screen.context.mode == "agent picker"
            await _dismiss_help(pilot, "escape")
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("down")
            await pilot.press("enter")
            await _until(
                pilot,
                lambda: compare.report is not None and compare.mode == "result",
                "Compare result",
            )
            await _open_help(pilot)
            assert app.screen.context.mode == "comparison result"
            await _dismiss_help(pilot, "escape")
            await pilot.press("J")
            await pilot.pause()
            assert compare.query_one("#compare-json", JsonView).document is not None
            await _open_help(pilot)
            assert app.screen.context.mode == "raw JSON view"
            await _dismiss_help(pilot, "escape")
            await pilot.press("J")
            await pilot.press("escape")
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")

            # Doctor with Help; Enter selects the captured Home row only.
            await pilot.press("h")
            await _until(pilot, lambda: isinstance(app.screen, DoctorScreen), "Doctor")
            doctor = app.screen
            await _open_help(pilot)
            assert app.screen.context.origin == "Doctor"
            assert "never opens a file" in _help_text(app)
            await _dismiss_help(pilot, "escape")
            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home selection")
            await pilot.pause()
            assert app.controller.selected_key == shared_key
            assert app.query_one("#removal-notice", Static).content == ""
            assert doctor.selected_finding is not None

            # Successful refresh after a fixture edit publishes together.
            make_skill(
                mock_home / ".claude" / "skills" / "new-skill",
                "new-skill",
                "Added during browsing.",
            )
            rows_before = _table(app).row_count
            await pilot.press("r")
            await _until(
                pilot,
                lambda: (
                    app.controller.current is not None
                    and app.controller.current.generation == 2
                    and app.controller.pending_generation is None
                ),
                "successful refresh",
            )
            await pilot.pause()
            assert _table(app).row_count == rows_before + 1
            assert any(key.endswith("/new-skill") for key in _home_row_keys(app))
            assert app.controller.selected_key == shared_key
            assert "Shared capability." in str(app.query_one("#preview-pane", Static).content)
            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_views_stay_on_captured_data_until_refresh_after_fixture_edits(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Editing/deleting targets after capture never changes views until a refresh."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            snapshot = app.controller.current
            assert snapshot is not None
            selected_key = app.controller.selected_key
            assert selected_key is not None
            captured_entry = next(
                entry for entry in snapshot.scan.skills if entry.canonical_path == selected_key
            )
            captured_description = str(captured_entry.description)
            captured_json = dumps(snapshot.scan.to_dict())
            rows_before = _table(app).row_count
            preview_before = str(app.query_one("#preview-pane", Static).content)
            assert captured_description in preview_before

            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            why = app.screen
            await _until(pilot, lambda: why._report is not None, "Why report")
            assert captured_description in why._report.candidates[0].reason

            await pilot.press("d")
            await _until(pilot, lambda: isinstance(app.screen, DiffScreen), "Diff")
            diff = app.screen
            await _until(pilot, lambda: diff.report is not None, "Diff report")
            assert len(diff.report.copies) == 2
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")

            # Edit one captured copy, delete the other, and add a new skill.
            import shutil

            home_target = mock_home / ".claude" / "skills" / "deploy" / "SKILL.md"
            home_target.write_text(
                "---\nname: deploy\ndescription: EDITED LIVE.\n---\n# Instructions\n\nChanged.\n",
                encoding="utf-8",
            )
            shutil.rmtree(mock_home / "project" / ".claude" / "skills" / "deploy")
            make_skill(
                mock_home / ".claude" / "skills" / "added-live",
                "added-live",
                "Added after capture.",
            )

            # Nothing in the captured views follows the live files.
            assert _table(app).row_count == rows_before
            assert captured_description in str(app.query_one("#preview-pane", Static).content)
            await pilot.press("J")
            await pilot.pause()
            document = app.screen.query_one("#home-json", JsonView).document
            assert document == captured_json
            await pilot.press("escape")

            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why again")
            why = app.screen
            await _until(pilot, lambda: why._report is not None, "cached Why report")
            assert captured_description in why._report.candidates[0].reason
            assert "EDITED LIVE" not in why._report.candidates[0].reason
            await pilot.press("d")
            await _until(pilot, lambda: isinstance(app.screen, DiffScreen), "Diff again")
            diff = app.screen
            await _until(pilot, lambda: diff.report is not None, "cached Diff report")
            assert len(diff.report.copies) == 2
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")

            # A successful refresh publishes the edits and removal together.
            await pilot.press("r")
            await _until(
                pilot,
                lambda: (
                    app.controller.current is not None
                    and app.controller.current.generation == 2
                    and app.controller.pending_generation is None
                ),
                "refresh",
            )
            await pilot.pause()
            # The project copy was removed and the live-only skill was added.
            assert _table(app).row_count == rows_before
            assert any(key.endswith("/added-live") for key in _home_row_keys(app))
            live_key = next(
                key
                for key in _home_row_keys(app)
                if key.endswith("/deploy") and "/project/" not in key
            )
            await _select_home_key(pilot, app, live_key)
            assert "EDITED LIVE." in str(app.query_one("#preview-pane", Static).content)
            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why refreshed")
            why = app.screen
            await _until(pilot, lambda: why._report is not None, "new Why report")
            assert "EDITED LIVE." in why._report.candidates[0].reason
            await pilot.press("d")
            await _until(pilot, lambda: isinstance(app.screen, DiffScreen), "Diff refreshed")
            diff = app.screen
            await _until(pilot, lambda: diff.report is not None, "new Diff report")
            assert len(diff.report.copies) == 1
            await pilot.press("q")

    asyncio.run(_run())


@pytest.mark.parametrize("size", [(100, 30), (60, 24)])
def test_every_screen_and_help_remains_usable_at_both_sizes(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch, size: tuple[int, int]
) -> None:
    """All six screens mount, keep Help reachable and return Home at both sizes."""
    build_scenario("symlink_farm_multi_agent", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=size) as pilot:
            await _wait_ready(pilot, app)
            for target in ("home", "why", "diff", "agents", "compare-picker", "doctor"):
                origin = await _goto(pilot, app, target)
                assert app.screen.size == size
                help_screen = await _open_help(pilot)
                close = help_screen.query_one("#help-close", Button)
                assert close.display and close.region.height > 0
                assert close.region.y < size[1]
                await _dismiss_help(pilot, "close")
                assert app.screen is origin
                # Return to Home before the next screen.
                for _ in range(4):
                    if isinstance(app.screen, HomeScreen):
                        break
                    await pilot.press("escape")
                    await pilot.pause()
                await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")
            await pilot.press("q")

    asyncio.run(_run())


def test_help_over_home_json_refresh_replaces_the_document_without_stale_data(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A refresh accepted behind Help replaces Home JSON on reveal; no old bytes."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("J")
            await pilot.pause()
            view = app.screen.query_one("#home-json", JsonView)
            old_document = view.document
            assert old_document is not None

            await _open_help(pilot)
            make_skill(
                mock_home / ".claude" / "skills" / "fresh-skill",
                "fresh-skill",
                "Captured only by the refresh.",
            )
            await pilot.press("r")
            await _until(
                pilot,
                lambda: (
                    app.controller.current is not None
                    and app.controller.current.generation == 2
                    and app.controller.pending_generation is None
                ),
                "refresh",
            )
            assert isinstance(app.screen, HelpScreen)
            # The covered screen still shows the captured document; it is not
            # reconciled while Help is open.
            assert view.document == old_document

            await _dismiss_help(pilot, "escape")
            await pilot.pause()
            snapshot = app.controller.current
            assert snapshot is not None
            assert view.document is not None
            assert view.document != old_document
            assert "fresh-skill" in view.document
            assert view.document == dumps(snapshot.scan.to_dict())
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# A6 — All six JSON views match the existing CLI serializer
# ---------------------------------------------------------------------------


def _cli_document(*args: str) -> str:
    result = runner.invoke(cli_app, [*args, "--json"])
    assert result.exit_code == 0, result.output
    return result.stdout.removesuffix("\n")


async def _choose_table_key(pilot: Any, table: DataTable, key: str) -> None:
    target = next(
        index
        for index in range(table.row_count)
        if str(table.coordinate_to_cell_key((index, 0)).row_key.value) == key
    )
    for _ in range(table.row_count + 1):
        if table.cursor_row == target:
            break
        await pilot.press("down" if table.cursor_row < target else "up")
        await pilot.pause(0.01)
    await pilot.press("enter")
    await pilot.pause()


def test_all_six_json_views_match_the_cli_serializer_on_same_inputs(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Home, Why, Diff, Compare, Doctor and Agents documents equal CLI JSON bytes."""
    build_scenario("claude_personal_beats_project", mock_home)
    project = mock_home / "project"

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            await pilot.press("J")
            await pilot.pause()
            home_document = app.screen.query_one("#home-json", JsonView).document
            assert home_document == _cli_document(
                "scan", "--sandbox", str(mock_home), "--cwd", str(project)
            )
            await pilot.press("escape")

            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            why = app.screen
            await _until(pilot, lambda: why._report is not None, "Why report")
            await pilot.press("J")
            await pilot.pause()
            why_document = why.query_one("#why-json", JsonView).document
            assert why_document == _cli_document(
                "why",
                "deploy",
                "--agent",
                str(why._agent_id),
                "--sandbox",
                str(mock_home),
                "--cwd",
                str(project),
            )

            await pilot.press("J")
            await pilot.pause()
            await pilot.press("d")
            await _until(pilot, lambda: isinstance(app.screen, DiffScreen), "Diff")
            diff = app.screen
            await _until(pilot, lambda: diff.report is not None, "Diff report")
            await pilot.press("J")
            await pilot.pause()
            diff_document = diff.query_one("#diff-json", JsonView).document
            assert diff_document == _cli_document(
                "diff", "deploy", "--sandbox", str(mock_home), "--cwd", str(project)
            )
            await pilot.press("escape")
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")

            await pilot.press("c")
            await _until(pilot, lambda: isinstance(app.screen, CompareScreen), "Compare")
            compare = app.screen
            await _choose_table_key(
                pilot, compare.query_one("#compare-a-table", DataTable), "claude"
            )
            await _choose_table_key(
                pilot, compare.query_one("#compare-b-table", DataTable), "codex"
            )
            await _until(pilot, lambda: compare.report is not None, "Compare report")
            await pilot.press("J")
            await pilot.pause()
            compare_document = compare.query_one("#compare-json", JsonView).document
            assert compare_document == _cli_document(
                "compare",
                "--agent",
                "claude",
                "--agent",
                "codex",
                "--sandbox",
                str(mock_home),
                "--cwd",
                str(project),
            )
            await pilot.press("escape")
            await pilot.press("escape")
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")

            await pilot.press("h")
            await _until(pilot, lambda: isinstance(app.screen, DoctorScreen), "Doctor")
            doctor = app.screen
            await pilot.press("J")
            await pilot.pause()
            doctor_document = doctor.query_one("#doctor-json", JsonView).document
            assert doctor_document == _cli_document(
                "doctor", "--sandbox", str(mock_home), "--cwd", str(project)
            )
            await pilot.press("escape")
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")

            await pilot.press("g")
            await _until(pilot, lambda: isinstance(app.screen, AgentsScreen), "Agents")
            agents = app.screen
            await pilot.press("J")
            await pilot.pause()
            agents_document = agents.query_one("#agents-json", JsonView).document
            assert agents_document == _cli_document("agents")
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# A7 — Empty and error state distinctions at both terminal sizes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("size", [(100, 30), (60, 24)])
def test_empty_catalog_filter_hint_and_unreadable_root_note(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch, size: tuple[int, int]
) -> None:
    """A successful empty catalog, a hidden-everything filter and an unreadable root differ."""
    real_capture = capture_session

    def capture_with_unreadable(**kwargs: Any) -> Any:
        snapshot = real_capture(**kwargs)
        scan = replace(
            snapshot.scan,
            unreadable=(
                {
                    "agent": "claude",
                    "root": "claude_personal",
                    "path": "~/.claude/skills/blocked",
                    "detail": "permission denied",
                },
            ),
        )
        return replace(snapshot, scan=scan)

    monkeypatch.setattr(app_module, "capture_session", capture_with_unreadable)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=size) as pilot:
            await _wait_ready(pilot, app)
            snapshot = app.controller.current
            assert snapshot is not None
            assert snapshot.scan.skills == ()
            assert _table(app).row_count == 0
            empty = str(app.query_one("#empty-state", Static).content)
            assert "No skills discovered in this session" in empty
            note = str(app.query_one("#catalog-note", Static).content)
            assert note.startswith("Unreadable roots:")
            assert "~/.claude/skills/blocked" in note
            assert "permission denied" in note

            await _open_help(pilot)
            assert "Ready: 0 skills discovered." in _help_status(app)
            await _dismiss_help(pilot, "escape")

            # An empty catalog stays honestly empty under a filter; the filter
            # itself is cleared normally and the full JSON remains available.
            await pilot.press("slash")
            await pilot.press(*"zzz")
            await pilot.pause()
            empty = str(app.query_one("#empty-state", Static).content)
            assert empty == "No skills discovered in this session. Press r to refresh."
            await pilot.press("escape")
            await pilot.pause()
            assert app.query_one("#filter-input", Input).value == ""
            await pilot.press("J")
            await pilot.pause()
            document = app.screen.query_one("#home-json", JsonView).document
            assert document is not None
            assert json.loads(document)["skills"] == []
            await pilot.press("escape")
            await pilot.press("q")

    asyncio.run(_run())


@pytest.mark.parametrize("size", [(100, 30), (60, 24)])
def test_no_detected_agents_is_not_no_registry_definitions(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch, size: tuple[int, int]
) -> None:
    """An empty scan detects no agents yet still lists every known definition."""

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=size) as pilot:
            await _wait_ready(pilot, app)
            snapshot = app.controller.current
            assert snapshot is not None
            assert snapshot.scan.summary.detected_agents == ()
            legend = str(app.query_one("#legend", Static).content)
            assert "No agents detected" in legend

            await pilot.press("g")
            await _until(pilot, lambda: isinstance(app.screen, AgentsScreen), "Agents")
            agents = app.screen
            table = agents.query_one("#agents-table", DataTable)
            assert table.row_count == len(snapshot.registry)
            assert table.row_count >= 2
            empty = str(agents.query_one("#agents-empty", Static).content)
            assert empty == ""

            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")
            await pilot.press("c")
            await _until(pilot, lambda: isinstance(app.screen, CompareScreen), "Compare")
            compare = app.screen
            assert compare.query_one("#compare-a-table", DataTable).row_count == len(
                snapshot.registry
            )
            assert compare.query_one("#compare-b-table", DataTable).row_count == len(
                snapshot.registry
            )
            assert compare.query_one("#compare-submit", Button).disabled is False
            assert str(compare.query_one("#compare-registry-message", Static).content) == ""
            await pilot.press("q")

    asyncio.run(_run())


@pytest.mark.parametrize("size", [(100, 30), (60, 24)])
def test_no_registry_definitions_and_compare_shortfall(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch, size: tuple[int, int]
) -> None:
    """Zero definitions is distinct from zero detection and names the exact shortfall."""
    real_capture = capture_session

    def capture_without_registry(**kwargs: Any) -> Any:
        return replace(real_capture(**kwargs), registry=())

    monkeypatch.setattr(app_module, "capture_session", capture_without_registry)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=size) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("g")
            await _until(pilot, lambda: isinstance(app.screen, AgentsScreen), "Agents")
            agents = app.screen
            empty = str(agents.query_one("#agents-empty", Static).content)
            assert empty == "No agent definitions are available in this captured session."
            await _open_help(pilot)
            assert "No agent definitions" in _help_text(app)
            await _dismiss_help(pilot, "escape")
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")

            await pilot.press("c")
            await _until(pilot, lambda: isinstance(app.screen, CompareScreen), "Compare")
            compare = app.screen
            note = str(compare.query_one("#compare-registry-message", Static).content)
            assert note == (
                "No known agent definitions are available: none."
                " Need 2 more definitions to compare."
            )
            assert compare.query_one("#compare-submit", Button).disabled is True
            await _open_help(pilot)
            assert "No known agent definitions" in _help_text(app)
            await _dismiss_help(pilot, "escape")
            await pilot.press("q")

    asyncio.run(_run())


def test_compare_duplicate_choice_is_rejected_inline_and_in_help(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Choosing the same agent twice explains the condition without a fault."""
    build_scenario("symlink_farm_multi_agent", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(60, 24)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("c")
            await _until(pilot, lambda: isinstance(app.screen, CompareScreen), "Compare")
            compare = app.screen
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")  # B defaults to the same highlighted agent
            await pilot.pause()
            assert compare.mode == "picker"
            assert str(compare.query_one("#compare-input-error", Static).content) == (
                "Pick two different agents."
            )
            assert not app.controller.is_failed
            await _open_help(pilot)
            assert "Pick two different agents." in _help_text(app)
            await _dismiss_help(pilot, "escape")
            await pilot.press("q")

    asyncio.run(_run())


@pytest.mark.parametrize("kind", ["empty", "info"])
@pytest.mark.parametrize("size", [(100, 30), (60, 24)])
def test_doctor_empty_versus_info_only_healthy_report(
    mock_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    size: tuple[int, int],
) -> None:
    """An empty Doctor report and an info-only healthy report stay distinct."""
    build_scenario("claude_personal_beats_project", mock_home)
    real_capture = capture_session

    def capture_with_doctor(**kwargs: Any) -> Any:
        snapshot = real_capture(**kwargs)
        findings = (
            ()
            if kind == "empty"
            else (
                DoctorFinding(
                    code="u8_info",
                    severity=Severity.INFO,
                    message="Normal setup note.",
                    rule_id="u8_info_rule",
                    evidence=Evidence.EMPIRICAL,
                    path=None,
                    detail=None,
                ),
            )
        )
        report = DoctorReport(snapshot.doctor.home, snapshot.doctor.cwd, findings)
        return replace(snapshot, doctor=report)

    monkeypatch.setattr(app_module, "capture_session", capture_with_doctor)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=size) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("h")
            await _until(pilot, lambda: isinstance(app.screen, DoctorScreen), "Doctor")
            doctor = app.screen
            summary = str(doctor.query_one("#doctor-summary", Static).content)
            empty = str(doctor.query_one("#doctor-empty", Static).content)
            if kind == "empty":
                assert summary == "Skill folders look healthy."
                assert empty == ""
            else:
                assert summary == ("1 findings: 0 errors, 0 warnings, 1 info. Status: healthy.")
                assert "Normal setup note." in str(
                    doctor.query_one("#doctor-detail", Static).content
                )
                assert empty == ""
            await _open_help(pilot)
            assert summary in _help_text(app)
            await _dismiss_help(pilot, "escape")
            assert not app.controller.is_failed
            await pilot.press("q")

    asyncio.run(_run())


def test_diff_single_copy_no_difference_answer_stays_readable(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A single-copy capture shows the model's no-comparison answer, not a fault."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(60, 24)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            await pilot.press("d")
            await _until(pilot, lambda: isinstance(app.screen, DiffScreen), "Diff")
            diff = app.screen
            await _until(pilot, lambda: diff.report is not None, "Diff report")
            assert diff.report.has_differences is False
            content = diff.query_one("#diff-content", Vertical)
            text = "\n".join(str(widget.content) for widget in content.query(Static))
            assert "No differences:" in text
            assert "only one copy exists, so there is nothing to compare." in text
            await _open_help(pilot)
            assert "DIFF — UNIFIED DIFF" in _help_text(app)
            await _dismiss_help(pilot, "escape")
            assert not app.controller.is_failed
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Scroll and focus restoration for JSON and detail panes
# ---------------------------------------------------------------------------


def _many_compare_skills(home: Path) -> None:
    for index in range(14):
        make_skill(
            home / ".claude" / "skills" / f"pair-{index:02d}",
            f"pair-{index:02d}",
            "Claude copy with a long description for comparison." * 2,
        )
        make_skill(
            home / ".codex" / "skills" / f"pair-{index:02d}",
            f"pair-{index:02d}",
            "Codex copy with a different long description." * 2,
        )


@pytest.mark.parametrize(
    "target,selector",
    [
        ("home", "#home-json"),
        ("why", "#why-json"),
        ("diff", "#diff-json"),
        ("agents", "#agents-json"),
        ("compare-result", "#compare-json"),
        ("doctor", "#doctor-json"),
    ],
)
def test_help_restores_raw_json_scroll_on_every_screen(
    mock_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    selector: str,
) -> None:
    """An unchanged JSON document keeps its scroll position across Help."""
    build_scenario("symlink_farm_multi_agent", mock_home)
    _many_compare_skills(mock_home)
    real_capture = capture_session

    if target == "doctor":

        def capture_with_findings(**kwargs: Any) -> Any:
            snapshot = real_capture(**kwargs)
            findings = tuple(
                DoctorFinding(
                    code=f"u8_long_{index}",
                    severity=Severity.INFO,
                    message=(f"Long finding {index}: " + "detail " * 40),
                    rule_id="u8_scroll_rule",
                    evidence=Evidence.EMPIRICAL,
                    path=None,
                    detail=("Long stored detail. " * 80),
                )
                for index in range(8)
            )
            return replace(
                snapshot,
                doctor=DoctorReport(snapshot.doctor.home, snapshot.doctor.cwd, findings),
            )

        monkeypatch.setattr(app_module, "capture_session", capture_with_findings)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(60, 24)) as pilot:
            await _wait_ready(pilot, app)
            origin = await _goto(pilot, app, target)
            await pilot.press("J")
            await pilot.pause()
            view = origin.query_one(selector, JsonView)
            assert view.shows_document
            assert view.max_scroll_y > 0, f"{target} JSON must be scrollable"
            before = min(3, view.max_scroll_y)
            view.scroll_to(y=before, animate=False)
            await pilot.pause()
            assert view.scroll_offset.y == before

            await pilot.press("f1")
            await pilot.pause()
            assert isinstance(app.screen, HelpScreen)
            await pilot.press("f1")
            await pilot.pause()
            assert app.screen is origin
            assert getattr(origin, "json_mode", False) is True
            assert view.scroll_offset.y == before
            await pilot.press("q")

    asyncio.run(_run())


@pytest.mark.parametrize(
    "target,selector,focus_details",
    [
        ("why", "#why-body", False),
        ("diff", "#diff-body", False),
        ("agents", "#agents-detail-scroll", True),
        ("doctor", "#doctor-detail-scroll", True),
        ("compare-result", "#compare-result-scroll", False),
    ],
)
def test_help_restores_ordinary_detail_scroll_on_supported_screens(
    mock_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    selector: str,
    focus_details: bool,
) -> None:
    """An unchanged ordinary detail pane keeps its scroll across Help."""
    build_scenario("claude_personal_beats_project", mock_home)
    _many_compare_skills(mock_home)
    make_skill(
        mock_home / ".codex" / "skills" / "deploy",
        "deploy",
        "Codex deploy helper.",
        body="# Instructions\n\n" + "Codex line.\n" * 60,
    )
    real_capture = capture_session

    if target == "doctor":

        def capture_with_findings(**kwargs: Any) -> Any:
            snapshot = real_capture(**kwargs)
            findings = tuple(
                DoctorFinding(
                    code=f"u8_detail_{index}",
                    severity=Severity.INFO,
                    message=(f"Finding {index}: " + "message " * 60),
                    rule_id="u8_detail_rule",
                    evidence=Evidence.EMPIRICAL,
                    path=None,
                    detail=("Stored detail line. " * 120),
                )
                for index in range(8)
            )
            return replace(
                snapshot,
                doctor=DoctorReport(snapshot.doctor.home, snapshot.doctor.cwd, findings),
            )

        monkeypatch.setattr(app_module, "capture_session", capture_with_findings)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(60, 24)) as pilot:
            await _wait_ready(pilot, app)
            origin = await _goto(pilot, app, target)
            if focus_details:
                await pilot.press("enter")
                await pilot.pause()
            widget = origin.query_one(selector, VerticalScroll)
            assert widget.max_scroll_y > 0, f"{target} detail must be scrollable"
            before = min(3, widget.max_scroll_y)
            widget.scroll_to(y=before, animate=False)
            await pilot.pause()
            assert widget.scroll_offset.y == before

            await pilot.press("f1")
            await pilot.pause()
            assert isinstance(app.screen, HelpScreen)
            await pilot.press("f1")
            await pilot.pause()
            assert app.screen is origin
            assert widget.scroll_offset.y == before
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Teardown, stale-callback and contextual-content coverage
# ---------------------------------------------------------------------------


def test_help_lifecycle_helpers_are_safe_before_mount_and_during_teardown() -> None:
    """Stale resume/scroll/focus callbacks are inert after a screen is gone.

    Textual may deliver an explicit close and a native ScreenResume in either
    order, and a deferred callback can arrive after teardown. Every screen's
    bounded helpers therefore have to return safely when not mounted or while
    already suspended.
    """
    screens = [
        HomeScreen(),
        WhyScreen("key", None),
        DiffScreen("key"),
        AgentsScreen(),
        CompareScreen(),
        DoctorScreen(),
    ]
    for screen in screens:
        screen._suspended = True
        screen.suspend_help()  # already suspended: idempotent no-op
        screen._scroll_help_widget(Static("text"), 2)  # suspended: no scroll
        screen._focus_if_active(None)  # no widget: no focus
        screen.resume_help()  # not mounted: clear the flag and return
        assert screen._suspended is False, type(screen).__name__


def test_help_screen_stale_update_and_other_buttons_do_not_dismiss(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale/missing session section is inert; only the Close button dismisses."""
    from types import SimpleNamespace

    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            help_screen = await _open_help(pilot)

            # A missing session widget must not raise out of a late update.
            help_screen.query_one("#help-session", Static).remove()
            help_screen.update_session(app.controller)
            await pilot.pause()
            assert app.screen is help_screen

            # A non-Close button event stops without dismissing Help.
            help_screen.on_button_pressed(
                SimpleNamespace(  # type: ignore[arg-type]
                    button=SimpleNamespace(id="not-close"),
                    stop=lambda: None,
                )
            )
            await pilot.pause()
            assert app.screen is help_screen

            await _dismiss_help(pilot, "escape")
            # A late update after unmount is a no-op.
            help_screen.update_session(app.controller)
            assert isinstance(app.screen, HomeScreen)
            await pilot.press("q")

    asyncio.run(_run())


def test_open_help_ignores_an_unsupported_screen(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A future/plain screen is not a Help origin; open_help leaves it alone."""
    from textual.screen import Screen

    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            plain = Screen()
            app.push_screen(plain)
            await pilot.pause()
            assert app.screen is plain
            app.open_help()
            app.action_open_help()
            await pilot.pause()
            assert app.screen is plain
            assert not any(isinstance(screen, HelpScreen) for screen in app.screen_stack)
            app.pop_screen()
            await pilot.pause()
            await pilot.press("q")

    asyncio.run(_run())


def test_help_from_agents_and_doctor_details_names_the_focused_pane(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Help reflects the details-pane focus on Agents and Doctor."""
    build_scenario("claude_personal_beats_project", mock_home)
    real_capture = capture_session

    def capture_with_finding(**kwargs: Any) -> Any:
        snapshot = real_capture(**kwargs)
        finding = DoctorFinding(
            code="u8_detail_context",
            severity=Severity.INFO,
            message="A captured finding.",
            rule_id="u8_detail_context_rule",
            evidence=Evidence.EMPIRICAL,
            path=None,
            detail=None,
        )
        return replace(
            snapshot,
            doctor=DoctorReport(snapshot.doctor.home, snapshot.doctor.cwd, (finding,)),
        )

    monkeypatch.setattr(app_module, "capture_session", capture_with_finding)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("g")
            await _until(pilot, lambda: isinstance(app.screen, AgentsScreen), "Agents")
            agents = app.screen
            await pilot.press("enter")
            await pilot.pause()
            assert _focused_id(app) == "agents-detail-scroll"
            await _open_help(pilot)
            body = _help_text(app)
            assert "Current focus: details pane" in body
            assert "then leave the details pane for the table" in body
            await _dismiss_help(pilot, "escape")
            assert app.focused is agents.query_one("#agents-detail-scroll", VerticalScroll)
            await pilot.press("escape")
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")

            await pilot.press("h")
            await _until(pilot, lambda: isinstance(app.screen, DoctorScreen), "Doctor")
            doctor = app.screen
            for _ in range(4):
                if _focused_id(app) == "doctor-detail-scroll":
                    break
                await pilot.press("tab")
                await pilot.pause()
            assert _focused_id(app) == "doctor-detail-scroll"
            await _open_help(pilot)
            body = _help_text(app)
            assert "Current focus: details pane" in body
            assert "never opens a file" in body
            await _dismiss_help(pilot, "escape")
            assert app.focused is doctor.query_one("#doctor-detail-scroll", VerticalScroll)
            await pilot.press("q")

    asyncio.run(_run())


def test_help_over_diff_not_found_report_explains_the_existing_answer(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A supplied not-found Diff report keeps its model wording and Help note."""
    from skill_lens.models.diff import DiffReport

    build_scenario("claude_personal_beats_project", mock_home)

    def not_found_diff(snapshot: Any, key: str) -> Any:
        return DiffReport(
            skill_name="ghost",
            home=str(mock_home),
            cwd=str(mock_home),
            found=False,
        )

    monkeypatch.setattr(app_module, "snapshot_diff", not_found_diff)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            await pilot.press("d")
            await _until(pilot, lambda: isinstance(app.screen, DiffScreen), "Diff")
            diff = app.screen
            await _until(pilot, lambda: diff.report is not None, "Diff report")
            assert diff.report.found is False
            await _open_help(pilot)
            assert "not-found answer" in _help_text(app)
            await _dismiss_help(pilot, "escape")
            content = diff.query_one("#diff-content", Vertical)
            assert any(
                "No copies of 'ghost' were found" in str(widget.content)
                for widget in content.query(Static)
            )
            await pilot.press("q")

    asyncio.run(_run())


def test_why_help_context_reflects_no_agents_and_loading(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Why Help changes its instructions for missing agents and a loading report."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            why = app.screen
            await _until(pilot, lambda: why._report is not None, "Why report")
            original_options = why._agent_options
            original_unavailable = why._unavailable
            original_report = why._report

            why._agent_options = ()
            why._unavailable = ("ghost-agent",)
            context = why.help_context()
            assert any("Unavailable agent IDs: ghost-agent" in note for note in context.notes)
            why._unavailable = ()
            context = why.help_context()
            assert any("No agent reaches this installation" in note for note in context.notes)

            why._agent_options = original_options
            why._unavailable = original_unavailable
            why._report = None
            why._owned_request = object()  # type: ignore[assignment]
            context = why.help_context()
            assert any("still loading" in note for note in context.notes)
            why._report = original_report
            why._owned_request = None
            await pilot.press("q")

    asyncio.run(_run())


@pytest.mark.parametrize(
    "target",
    ["home", "why", "diff", "agents", "compare-picker", "doctor"],
)
def test_stale_help_callbacks_do_not_act_on_a_covered_screen(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    """Late resume/focus callbacks are inert while Help is the active modal."""
    scenario = (
        "symlink_farm_multi_agent"
        if target == "compare-picker"
        else "claude_personal_beats_project"
    )
    build_scenario(scenario, mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            origin = await _goto(pilot, app, target)
            _open = await _open_help(pilot)
            widget = next(
                (child for child in origin.query("*") if child.can_focus),
                None,
            )

            # A stale explicit resume must not reconcile or focus while covered.
            origin.resume_help()
            origin._focus_if_active(widget)
            await pilot.pause()
            assert app.screen is _open
            assert _focused_id(app) == "help-body"

            await _dismiss_help(pilot, "escape")
            assert app.screen is origin
            await pilot.press("q")

    asyncio.run(_run())


@pytest.mark.parametrize("target", ["agents", "doctor"])
def test_help_never_restores_a_removed_details_widget(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    """A details pane removed while Help is open falls back to the table."""
    build_scenario("claude_personal_beats_project", mock_home)
    real_capture = capture_session

    if target == "doctor":

        def capture_with_finding(**kwargs: Any) -> Any:
            snapshot = real_capture(**kwargs)
            finding = DoctorFinding(
                code="u8_removed_detail",
                severity=Severity.INFO,
                message="Captured finding.",
                rule_id="u8_removed_detail_rule",
                evidence=Evidence.EMPIRICAL,
                path=None,
                detail=None,
            )
            return replace(
                snapshot,
                doctor=DoctorReport(snapshot.doctor.home, snapshot.doctor.cwd, (finding,)),
            )

        monkeypatch.setattr(app_module, "capture_session", capture_with_finding)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("g" if target == "agents" else "h")
            screen_type = AgentsScreen if target == "agents" else DoctorScreen
            await _until(pilot, lambda: isinstance(app.screen, screen_type), target)
            origin = app.screen
            for _ in range(4):
                if _focused_id(app) == f"{target}-detail-scroll":
                    break
                await pilot.press("tab")
                await pilot.pause()
            if target == "agents":
                await pilot.press("enter")
                await pilot.pause()
            await _open_help(pilot)
            # Simulate a rebuild that removed the remembered pane.
            origin.query_one(f"#{target}-detail-scroll", VerticalScroll).remove()
            await pilot.pause()

            await _dismiss_help(pilot, "escape")
            await pilot.pause()
            assert app.screen is origin
            assert _focused_id(app) == f"{target}-{'table' if target == 'agents' else 'findings'}"
            await pilot.press("q")

    asyncio.run(_run())


def test_help_screen_update_before_mount_is_inert() -> None:
    """A session update on a never-mounted Help returns without touching widgets."""
    from skill_lens.tui.help import HelpContext

    controller = __import__(
        "skill_lens.tui.session", fromlist=["SessionController"]
    ).SessionController()
    help_screen = HelpScreen(HelpContext("Home", "ordinary", "table", ()), controller)
    help_screen.update_session(controller)
    assert help_screen.is_mounted is False


def test_help_no_session_over_doctor(mock_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Doctor's no-session Help section is honest and still usable."""
    monkeypatch.setattr(
        app_module,
        "capture_session",
        lambda **kwargs: (_ for _ in ()).throw(CaptureCancelled()),
    )

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(60, 24)) as pilot:
            await _until(pilot, lambda: app.controller.status == "idle", "idle")
            await pilot.press("h")
            await pilot.pause()
            assert isinstance(app.screen, DoctorScreen)
            await _open_help(pilot)
            assert "No session is captured yet" in _help_text(app)
            assert "No session captured yet." in _help_status(app)
            await _dismiss_help(pilot, "escape")
            await pilot.press("q")

    asyncio.run(_run())


def test_help_from_home_preview_names_the_actual_focus(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Help does not claim table-only keys while another Home control has focus."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            preview = app.query_one("#preview-scroll", VerticalScroll)
            await pilot.press("tab")
            await pilot.pause()
            while app.focused is not preview:
                await pilot.press("tab")
                await pilot.pause()
            await _open_help(pilot)
            body = _help_text(app)
            assert "Current focus: another Home control" in body
            assert "Enter and d require the skill table to have focus" in body
            await _dismiss_help(pilot, "escape")
            assert app.focused is preview
            await pilot.press("q")

    asyncio.run(_run())
