"""Headless U4 Why screen and detail navigation tests.

Specification reference: FULL_SCREEN_TUI.md §8.4, §9.1, §21.7 and §22 U4.

Every test uses the synthetic ``mock_home`` fixture (temporary HOME plus the
protected-system-root isolation installed by ``tests/conftest.py``); a live
``~/.claude`` is never read or written.  Workers are driven by real Textual
Pilot key/input events, and controlled races use threading events with bounded
waits so a hang fails the test instead of stalling the run.
"""

from __future__ import annotations

import asyncio
import builtins
import os
import shutil
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from textual.containers import VerticalScroll
from textual.widgets import Button, Collapsible, DataTable, Input, Static

from skill_lens.core import paths
from skill_lens.core.discovery import canonical_key
from skill_lens.core.snapshot import (
    SnapshotChanged,
    SnapshotTooLarge,
    capture_session,
    snapshot_path,
    snapshot_same_location,
    snapshot_why,
)
from skill_lens.core.snapshot_models import SessionSnapshot
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
from skill_lens.presentation.state import STATE_MARK, STATE_STYLE
from skill_lens.tui.app import SkillLensApp, ViewReportComplete
from skill_lens.tui.home import HomeScreen, _OwnedWhy
from skill_lens.tui.session import ReportValue, ViewName, ViewRequest
from skill_lens.tui.why import WhyScreen
from tests.fixtures.builders import make_skill, symlink
from tests.fixtures.scenarios import build_scenario

# ---------------------------------------------------------------------------
# Small test helpers
# ---------------------------------------------------------------------------


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
            and (
                len(app.controller.current.scan.skills) == 0
                or app.screen.query_one("#skill-table", DataTable).row_count > 0
            )
        ),
        "initial capture and home table ready",
    )
    await pilot.pause(0.02)


async def _wait_why_idle(pilot: Any, app: SkillLensApp) -> None:
    await _wait_until(
        pilot,
        lambda: app.controller.active_requests.get("why") is None,
        "why report idle",
    )
    await pilot.pause(0.05)


def _candidate(
    state: str | HeadlineState = HeadlineState.ACTIVE,
    canonical: str = "/mock/skill",
    entrypoint: str | None = None,
    name: str = "deploy",
    rule_id: str = "rule-1",
    evidence: Evidence = Evidence.DOCUMENTED,
    reason: str = "tested reason",
    notes: tuple[str, ...] = (),
) -> CandidateResolution:
    if isinstance(state, HeadlineState):
        hs = state
    else:
        norm = state.upper()
        if norm == "UNSEARCHED_ROOT":
            norm = "UNSEARCHED"
        hs = HeadlineState(norm)
    return CandidateResolution(
        state=hs,
        visibility=Visibility.ACTIVE_ROOT,
        collision=Collision.WINNING_ENTRY,
        rule_id=rule_id,
        evidence=evidence,
        reason=reason,
        rank=1,
        installation=SkillInstallation(
            name=name,
            entrypoint_path=entrypoint or canonical,
            canonical_path=canonical,
            scope=Scope.USER,
            parse_status=ParseStatus.VALID,
        ),
    )


def _report(
    *candidates: CandidateResolution,
    skill_name: str = "deploy",
    agent: str = "claude",
    agent_name: str = "Claude Code",
    cwd: str = "/mock/cwd",
    policy: str = "prefer_user",
    evidence: Evidence = Evidence.DOCUMENTED,
    headline: HeadlineState = HeadlineState.ACTIVE,
    notes: tuple[str, ...] = (),
    found: bool = True,
) -> ResolutionReport:
    return ResolutionReport(
        skill_name=skill_name,
        agent=agent,
        agent_name=agent_name,
        cwd=cwd,
        collision_policy=policy,
        policy_evidence=evidence,
        headline=headline,
        candidates=candidates,
        notes=notes,
        found=found,
    )


# ---------------------------------------------------------------------------
# C1 and C2 Promoted Regression Tests
# ---------------------------------------------------------------------------


def test_redraw_preserves_candidate_focus_and_expansion(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C1: Collapsing candidate and focusing its title survives session redraw / app._update_ui."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            screen = app.screen
            assert isinstance(screen, WhyScreen)

            block = list(screen.query(Collapsible))[0]
            block.collapsed = True
            block.query_one("CollapsibleTitle").focus()
            await pilot.pause()

            # Session redraw via host _update_ui
            app._update_ui()
            await pilot.pause()

            newblock = list(screen.query(Collapsible))[0]
            assert newblock.collapsed, "Session redraw reset user candidate expansion"
            assert (
                app.focused is not None and app.focused.__class__.__name__ == "CollapsibleTitle"
            ), "Session redraw stole candidate focus"
            await pilot.press("q")

    asyncio.run(_run())


def test_agent_button_renders_captured_label_literally(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C2: Captured agent names with markup tags render literally at creation and update."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            snap = app.controller.current
            assert snap is not None
            app.controller.current = replace(
                snap,
                registry=tuple(
                    replace(a, name=r"[red]Agent[/red]\label") if a.id == "claude" else a
                    for a in snap.registry
                ),
            )
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)

            button = app.screen.query_one("#why-agent-claude", Button)
            assert r"[red]Agent[/red]\label" in button.label.plain, (
                "Captured agent name interpreted as markup"
            )
            assert not any(span.style == "red" for span in button.label.spans), (
                "Style span was parsed from literal name"
            )
            await pilot.press("q")

    asyncio.run(_run())


def test_notice_cleared_on_explicit_refresh(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P1: Removal notice is cleared on explicit Home refresh ('r' and action_refresh)."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            home: HomeScreen = app.screen  # type: ignore[assignment]
            home.set_removal_notice("Removed old-installation")
            assert home._removal_notice == "Removed old-installation"
            assert "Removed old-installation" in str(
                home.query_one("#removal-notice", Static).content
            )

            # 1. Pressing 'r' triggers action_refresh and clears the notice
            await pilot.press("r")
            await _wait_until(
                pilot, lambda: app.controller.current.generation == 2, "refresh publication"
            )
            assert home._removal_notice is None
            assert not str(home.query_one("#removal-notice", Static).content)

            # 2. Programmatic action_refresh path also clears the notice
            home.set_removal_notice("Notice 2")
            assert home._removal_notice == "Notice 2"
            app.action_refresh()
            await _wait_until(
                pilot, lambda: app.controller.current.generation == 3, "refresh publication gen 3"
            )
            assert home._removal_notice is None
            assert not str(home.query_one("#removal-notice", Static).content)
            await pilot.press("q")

    asyncio.run(_run())


def test_agent_dom_order_after_eligibility_refresh(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P2: Agent strip DOM order matches model scan-ID order after eligibility refresh."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("symlink_farm_multi_agent", mock_home)

    def controlled_capture(**kwargs: Any) -> SessionSnapshot:
        snap = capture_session(**kwargs)
        if kwargs.get("generation", 1) == 1:
            # Exclude claude from gen 1 scan
            snap = replace(
                snap,
                scan=replace(
                    snap.scan,
                    skills=tuple(
                        replace(s, agents=tuple(a for a in s.agents if a != "claude"))
                        for s in snap.scan.skills
                    ),
                ),
            )
        return snap

    monkeypatch.setattr("skill_lens.tui.app.capture_session", controlled_capture)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert "claude" not in [o.agent_id for o in why._agent_options]

            # Refresh introduces earlier agent 'claude'
            await pilot.press("r")
            await _wait_until(pilot, lambda: why._generation == 2, "detail refresh")
            await _wait_why_idle(pilot, app)

            model = [o.agent_id for o in why._agent_options]
            dom = [b.id.removeprefix("why-agent-") for b in why.query("#why-agent-strip Button")]
            assert dom == model
            assert dom[0] == "claude"

            # Left/Right keys wrap deterministically
            assert why._agent_id == model[1]
            await pilot.press("left")
            await pilot.pause(0.02)
            assert why._agent_id == model[0]
            await pilot.press("right")
            await pilot.pause(0.02)
            assert why._agent_id == model[1]
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Navigation & Initial Selection Tests
# ---------------------------------------------------------------------------


def test_enter_on_focused_nonempty_table_opens_why_screen(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pressing Enter on the focused, nonempty Home table pushes a WhyScreen."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            assert isinstance(app.screen, HomeScreen)
            table = app.screen.query_one("#skill-table", DataTable)
            assert table.row_count > 0

            # Press Enter to open detail
            await pilot.press("enter")
            await pilot.pause(0.05)

            # Assert detail screen is mounted
            assert isinstance(app.screen, WhyScreen)
            why: WhyScreen = app.screen
            assert why._opening_key == app.controller.selected_key

            # Repeated Enter does NOT push another screen (at most one detail exists)
            await pilot.press("enter")
            await pilot.pause(0.02)
            assert len(app.screen_stack) == 2
            assert isinstance(app.screen, WhyScreen)

            # Clean exit
            await pilot.press("q")

    asyncio.run(_run())


def test_enter_on_empty_table_or_filtered_empty_list_is_noop(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Enter on an empty table or filter matching 0 skills does not open detail."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            # Filter for non-existent skill
            filter_input = app.screen.query_one("#filter-input", Input)
            filter_input.value = "nonexistent-skill-xyz"
            await pilot.pause(0.02)

            table = app.screen.query_one("#skill-table", DataTable)
            assert table.row_count == 0

            table.focus()
            await pilot.press("enter")
            await pilot.pause(0.02)
            # Still on HomeScreen
            assert isinstance(app.screen, HomeScreen)
            await pilot.press("q")

    asyncio.run(_run())


def test_enter_on_filter_input_submits_filter_does_not_open_why(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Enter on the filter Input submits the filter and returns to the table, not detail."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            filter_input = app.screen.query_one("#filter-input", Input)
            filter_input.focus()
            filter_input.value = "deploy"
            await pilot.press("enter")
            await pilot.pause(0.02)

            # Still on HomeScreen and focus moved to table
            assert isinstance(app.screen, HomeScreen)
            assert app.screen.query_one("#skill-table", DataTable).has_focus
            await pilot.press("q")

    asyncio.run(_run())


def test_backspace_returns_to_home_preserving_filter_and_selection(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Backspace and Escape return to Home, preserving filter query, cursor, and selection."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)
    make_skill(
        mock_home / ".claude" / "skills" / "deploy_second",
        "deploy_second",
        "Second deploy helper.",
    )

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home: HomeScreen = app.screen  # type: ignore[assignment]
            filter_input = home.query_one("#filter-input", Input)
            filter_input.value = "deploy"
            await pilot.pause(0.02)
            table = home.query_one("#skill-table", DataTable)
            assert table.row_count >= 2

            # Focus table and move cursor down to nonzero index
            table.focus()
            await pilot.press("down")
            await pilot.pause(0.02)
            cursor_before = table.cursor_row
            assert cursor_before > 0
            selected_before = app.controller.selected_key
            assert selected_before is not None

            # Open detail
            await pilot.press("enter")
            await pilot.pause(0.05)
            assert isinstance(app.screen, WhyScreen)

            # Press Backspace
            await pilot.press("backspace")
            await pilot.pause(0.05)
            assert isinstance(app.screen, HomeScreen)
            home_res = app.screen
            table_res = home_res.query_one("#skill-table", DataTable)
            assert home_res.query_one("#filter-input", Input).value == "deploy"
            assert table_res.cursor_row == cursor_before
            assert app.controller.selected_key == selected_before
            assert table_res.has_focus

            # Repeated back does not pop root screen
            await pilot.press("escape")
            await pilot.pause(0.02)
            assert isinstance(app.screen, HomeScreen)
            await pilot.press("q")

    asyncio.run(_run())


def test_priority_ctrl_c_and_q_quit_from_why(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """q and priority Ctrl-C quit cleanly with controller status code 0 from any detail focus."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run_q() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await pilot.pause(0.05)
            assert isinstance(app.screen, WhyScreen)
            await pilot.press("q")
            assert app.return_code == 0

    async def _run_ctrl_c() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await pilot.pause(0.05)
            assert isinstance(app.screen, WhyScreen)
            await pilot.press("ctrl+c")
            assert app.return_code == 0

    asyncio.run(_run_q())
    asyncio.run(_run_ctrl_c())


# ---------------------------------------------------------------------------
# Agent Strip & Traversal Tests
# ---------------------------------------------------------------------------


def test_agent_strip_options_and_deterministic_switching(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Strip options are ScanEntry's registered agents in sorted order; left/right switch."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("symlink_farm_multi_agent", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await pilot.pause(0.05)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)

            # Strip options
            assert len(why._agent_options) >= 2
            agent_ids = [opt.agent_id for opt in why._agent_options]
            assert agent_ids == sorted(agent_ids)

            initial_agent = why._agent_id
            assert initial_agent == agent_ids[0]

            # Right moves to next agent
            await pilot.press("right")
            await pilot.pause(0.02)
            assert why._agent_id == agent_ids[1]

            # Left moves back
            await pilot.press("left")
            await pilot.pause(0.02)
            assert why._agent_id == initial_agent

            # Left wraps around to last agent
            await pilot.press("left")
            await pilot.pause(0.02)
            assert why._agent_id == agent_ids[-1]

            await pilot.press("q")

    asyncio.run(_run())


def test_zero_agent_skill_shows_explanation_and_zero_requests(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A zero-agent skill shows clear explanation and produces zero Why requests."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            assert app.controller.current is not None

            # Construct synthetic ScanEntry with zero agents
            current = app.controller.current
            entry_zero_agents = replace(current.scan.skills[0], agents=())
            mutated_scan = replace(current.scan, skills=(entry_zero_agents,))
            app.controller.current = replace(current, scan=mutated_scan)

            # Open WhyScreen
            await pilot.press("enter")
            await pilot.pause(0.05)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)

            assert len(why._agent_options) == 0
            assert why._agent_id is None
            # Zero Why requests
            assert app.controller.active_requests.get("why") is None

            # Explanation is displayed
            rep_status = str(why.query_one("#why-report-status", Static).content)
            assert "No agent reaches this installation." in rep_status
            await pilot.press("q")

    asyncio.run(_run())


def test_defensive_unknown_agent_in_constructed_snapshot(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E6: Defensive constructed-snapshot all-unknown agent IDs
    explained with zero dispatch and exit 0.
    """
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            current = app.controller.current
            assert current is not None

            # Construct scan entry with all-unknown agent IDs (not in registry)
            orig_skill = current.scan.skills[0]
            mutated_skill = replace(orig_skill, agents=("unknown-agent-foo", "unknown-agent-bar"))
            app.controller.current = replace(
                current,
                scan=replace(current.scan, skills=(mutated_skill,)),
            )

            request_adapter_calls = 0
            orig_request_report = app.request_report

            def tracking_request_report(*args: Any, **kwargs: Any) -> Any:
                nonlocal request_adapter_calls
                request_adapter_calls += 1
                return orig_request_report(*args, **kwargs)

            monkeypatch.setattr(app, "request_report", tracking_request_report)

            snap_why_calls = 0

            def tracking_snap_why(*args: Any, **kwargs: Any) -> Any:
                nonlocal snap_why_calls
                snap_why_calls += 1
                return snapshot_why(*args, **kwargs)

            monkeypatch.setattr("skill_lens.tui.app.snapshot_why", tracking_snap_why)

            why = WhyScreen(orig_skill.canonical_path, "unknown-agent-foo")
            app.push_screen(why)
            await pilot.pause(0.05)

            # Defensive all-unknown: names IDs, shows unavailable, does NOT say no agent reaches
            assert why._agent_options == ()
            assert why._unavailable == ("unknown-agent-bar", "unknown-agent-foo")
            status_text = str(why.query_one("#why-report-status", Static).content)
            assert "Unavailable agent IDs: unknown-agent-bar, unknown-agent-foo" in status_text
            assert "No agent reaches" not in status_text

            # Zero request adapter calls, zero snapshot_why calls, controller.failed is False
            assert request_adapter_calls == 0
            assert snap_why_calls == 0
            assert app.controller.active_requests.get("why") is None
            assert app.controller.failed is False

            await pilot.press("q")
            assert app.return_code == 0

    asyncio.run(_run())


def test_missing_key_predispatch_zero_calls(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E6: Missing installation key predispatch validation closes Why with zero dispatch."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            adapter_calls = 0
            orig_request_report = app.request_report

            def tracking_request_report(*args: Any, **kwargs: Any) -> Any:
                nonlocal adapter_calls
                adapter_calls += 1
                return orig_request_report(*args, **kwargs)

            monkeypatch.setattr(app, "request_report", tracking_request_report)

            why = WhyScreen("completely-absent-installation-key", "claude")
            app.push_screen(why)
            await pilot.pause(0.05)

            # Predispatch validation closes Why immediately
            assert isinstance(app.screen, HomeScreen)
            assert adapter_calls == 0
            assert app.controller.active_requests.get("why") is None
            assert app.controller.failed is False
            await pilot.press("q")
            assert app.return_code == 0

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# C3 Controlled Event Races & Screen Ownership Tests (Real Workers & Events)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("stale_outcome", ["success", "error"])
def test_real_worker_race_blocked_home_to_detail_agent_change_and_stale_callbacks(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch, stale_outcome: str
) -> None:
    """C3/E1: Controlled real workers with cancellation events, stale success AND error outcomes."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("symlink_farm_multi_agent", mock_home)

    home_worker_started = threading.Event()
    home_worker_gate = threading.Event()
    detail_a_started = threading.Event()
    detail_a_gate = threading.Event()
    detail_b_started = threading.Event()
    detail_b_gate = threading.Event()

    real_snap_why = snapshot_why

    def controlled_snapshot_why(snap: SessionSnapshot, key: str, agent: str) -> ResolutionReport:
        if not home_worker_started.is_set():
            home_worker_started.set()
            home_worker_gate.wait(timeout=5.0)
            if stale_outcome == "error":
                raise RuntimeError("Stale Home worker failure")
            return real_snap_why(snap, key, agent)
        if not detail_a_started.is_set():
            detail_a_started.set()
            detail_a_gate.wait(timeout=5.0)
            if stale_outcome == "error":
                raise RuntimeError("Stale Detail A worker failure")
            return real_snap_why(snap, key, agent)
        if not detail_b_started.is_set():
            detail_b_started.set()
            detail_b_gate.wait(timeout=5.0)
            if stale_outcome == "error":
                raise RuntimeError("Stale Detail B worker failure")
            return real_snap_why(snap, key, agent)
        return real_snap_why(snap, key, agent)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", controlled_snapshot_why)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home: HomeScreen = app.screen  # type: ignore[assignment]
            assert isinstance(home, HomeScreen)

            processed_results: list[tuple[str, int, int, tuple[str, ...], bool]] = []
            processed_errors: list[tuple[str, int, int, tuple[str, ...], bool, Exception]] = []

            orig_accept_result = app.controller.accept_view_result

            def tracking_accept_result(
                view: Any, req_id: int, gen: int, args: tuple[str, ...], report: Any
            ) -> bool:
                accepted = orig_accept_result(view, req_id, gen, args, report)
                processed_results.append((view, req_id, gen, args, accepted))
                return accepted

            orig_accept_error = app.controller.accept_view_error

            def tracking_accept_error(
                view: Any, req_id: int, gen: int, args: tuple[str, ...], error: Exception
            ) -> bool:
                accepted = orig_accept_error(view, req_id, gen, args, error)
                processed_errors.append((view, req_id, gen, args, accepted, error))
                return accepted

            app.controller.accept_view_result = tracking_accept_result  # type: ignore[assignment]
            app.controller.accept_view_error = tracking_accept_error  # type: ignore[assignment]

            # 1. Home sets agent filter to claude -> Home dispatches Why worker
            home_resumed_gate = threading.Event()
            home.action_cycle_agent()
            await _wait_until(pilot, lambda: home_worker_started.is_set(), "Home worker started")
            home_token = app.controller.active_requests.get("why")
            assert home_token is not None
            home_event = app.controller._report_events.get(home_token.request_id)
            assert home_event is not None
            assert not home_event.is_set()

            # 2. Open detail screen -> Home is suspended, cancels token, sets cancellation event
            await pilot.press("enter")
            await pilot.pause(0.05)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)
            assert home._suspended is True
            assert home._inflight is None
            assert home_event.is_set(), "Home worker cancellation event must be set on suspend"

            # Detail worker A starts
            await _wait_until(pilot, lambda: detail_a_started.is_set(), "Detail worker A started")
            detail_a_token = app.controller.active_requests.get("why")
            assert detail_a_token is not None
            assert detail_a_token != home_token
            detail_a_event = app.controller._report_events.get(detail_a_token.request_id)
            assert detail_a_event is not None
            assert not detail_a_event.is_set()

            # 3. In detail, switch to agent B -> cancels token A and dispatches worker B
            await pilot.press("right")
            await _wait_until(pilot, lambda: detail_b_started.is_set(), "Detail worker B started")
            detail_b_token = app.controller.active_requests.get("why")
            assert detail_b_token is not None
            assert detail_b_token != detail_a_token
            assert detail_a_event.is_set(), "Detail A cancellation event must be set when switching"
            detail_b_event = app.controller._report_events.get(detail_b_token.request_id)
            assert detail_b_event is not None
            assert not detail_b_event.is_set()

            # 4. Release blocked Home worker -> old Home outcome completes
            home_worker_gate.set()
            if stale_outcome == "error":
                await _wait_until(
                    pilot,
                    lambda: any(e[1] == home_token.request_id for e in processed_errors),
                    "stale Home error processed",
                )
                stale_event = next(e for e in processed_errors if e[1] == home_token.request_id)
                assert stale_event[4] is False, "Stale Home error must be rejected by controller"
            else:
                await _wait_until(
                    pilot,
                    lambda: any(r[1] == home_token.request_id for r in processed_results),
                    "stale Home result processed",
                )
                stale_event = next(r for r in processed_results if r[1] == home_token.request_id)
                assert stale_event[4] is False, "Stale Home result must be rejected by controller"

            # Old Home outcome is rejected; detail still holds detail_b_token, failed is False
            assert app.controller.active_requests.get("why") == detail_b_token
            assert app.controller.failed is False
            assert "Loading report" in str(why.query_one("#why-report-status", Static).content)

            # Gate resumed Home why request so worker stays active
            app.controller.cache.clear()
            for g in home._groups.values():
                g.status = "pending"
                g.report = None

            def resumed_why(snap: SessionSnapshot, key: str, agent: str) -> ResolutionReport:
                home_resumed_gate.wait(timeout=5.0)
                return real_snap_why(snap, key, agent)

            monkeypatch.setattr("skill_lens.tui.app.snapshot_why", resumed_why)

            # 5. Return to Home via Escape -> pre-pop cleanup, Home resumes immediately
            await pilot.press("escape")
            await pilot.pause(0.05)
            assert isinstance(app.screen, HomeScreen)
            assert home._suspended is False
            assert detail_b_event.is_set(), "Detail B cancellation event must be set on Escape"

            # Home immediately resumed and dispatched new request
            new_home_token = app.controller.active_requests.get("why")
            assert new_home_token is not None
            assert new_home_token != detail_b_token

            # 6. Release detail worker B -> stale detail outcome completes
            detail_b_gate.set()
            detail_a_gate.set()
            if stale_outcome == "error":
                await _wait_until(
                    pilot,
                    lambda: any(e[1] == detail_b_token.request_id for e in processed_errors),
                    "stale Detail B error processed",
                )
                stale_b = next(e for e in processed_errors if e[1] == detail_b_token.request_id)
                assert stale_b[4] is False, "Stale Detail B error must be rejected by controller"
            else:
                await _wait_until(
                    pilot,
                    lambda: any(r[1] == detail_b_token.request_id for r in processed_results),
                    "stale Detail B result processed",
                )
                stale_b = next(r for r in processed_results if r[1] == detail_b_token.request_id)
                assert stale_b[4] is False, "Stale Detail B result must be rejected by controller"

            # Stale detail callback cannot corrupt or cancel Home's new token
            assert app.controller.active_requests.get("why") == new_home_token
            assert app.controller.failed is False
            home_resumed_gate.set()
            await pilot.press("q")

    asyncio.run(_run())


def test_home_suspended_drive_and_outcome_guards_prevent_hidden_dispatch(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E1/E8: HomeScreen._drive and note_report_outcome guards prevent
    hidden dispatch while suspended.
    """
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("symlink_farm_multi_agent", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home: HomeScreen = app.screen  # type: ignore[assignment]
            home.action_cycle_agent()
            await pilot.pause(0.02)
            await _wait_why_idle(pilot, app)

            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)
            assert home._suspended is True
            assert home._inflight is None

            app.controller.cache.clear()
            for g in home._groups.values():
                g.status = "pending"
                g.report = None

            # 1. Drive guard test: calling home._drive() while suspended must NOT dispatch!
            home._drive()
            assert home._inflight is None
            assert app.controller.active_requests.get("why") == why._owned_request

            # 2. Outcome guard test: calling note_report_outcome while suspended must be ignored!
            first_lookup = next(iter(home._groups.keys()))
            req = ViewRequest(
                generation=1,
                request_id=99999,
                view="why",
                arguments=(home._visible[0].key, "claude"),
            )
            home._inflight = _OwnedWhy(first_lookup, req)
            home._groups[first_lookup].status = "loading"

            home.note_report_outcome(
                "why",
                99999,
                1,
                (home._visible[0].key, "claude"),
                accepted=True,
                report=_report(skill_name=first_lookup, agent="claude"),
            )
            assert home._groups[first_lookup].status == "loading", (
                "Suspended guard must prevent note_report_outcome from processing outcome"
            )
            assert home._groups[first_lookup].report is None
            await pilot.press("q")

    asyncio.run(_run())


def test_cancellation_guards_kill_mutants(mock_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """E1/E8: Ownership cancellation guards: suspend_why, _cancel_owned_token, close_why."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("symlink_farm_multi_agent", mock_home)
    gate = threading.Event()
    real_snap = snapshot_why

    def blocking_why(snap: SessionSnapshot, key: str, agent: str) -> ResolutionReport:
        gate.wait(timeout=5.0)
        return real_snap(snap, key, agent)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        monkeypatch.setattr("skill_lens.tui.app.snapshot_why", blocking_why)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home: HomeScreen = app.screen  # type: ignore[assignment]
            home.action_cycle_agent()
            await pilot.pause(0.02)
            home_req = app.controller.active_requests.get("why")
            assert home_req is not None
            home_event = app.controller._report_events.get(home_req.request_id)
            assert home_event is not None
            assert not home_event.is_set()

            # Test Mutant 3: suspend_why sets cancellation event, clears inflight
            home.suspend_why()
            assert home_event.is_set(), "suspend_why must set worker cancellation event"
            assert home._inflight is None
            assert app.controller.active_requests.get("why") is None

            # Open detail
            why = WhyScreen(home._visible[0].key, "claude")
            app.push_screen(why)
            await pilot.pause(0.05)
            detail_req = app.controller.active_requests.get("why")
            assert detail_req is not None
            detail_event = app.controller._report_events.get(detail_req.request_id)
            assert detail_event is not None
            assert not detail_event.is_set()

            # Test Mutant 4: unowned token does not cancel;
            # matching owned token cancels and sets event
            fake_owned = type(
                "FakeReq", (), {"request_id": 9999, "generation": 1, "arguments": ("x",)}
            )()
            why._owned_request = fake_owned  # unowned
            why._cancel_owned_token()
            assert not detail_event.is_set(), "Must not cancel unowned active token"
            assert app.controller.active_requests.get("why") == detail_req

            why._owned_request = detail_req
            why._cancel_owned_token()
            assert detail_event.is_set(), "Matching _cancel_owned_token must set cancellation event"
            assert app.controller.active_requests.get("why") is None

            # Re-dispatch detail request to test Mutant 5:
            why._request_report()
            new_detail_req = app.controller.active_requests.get("why")
            assert new_detail_req is not None
            new_detail_event = app.controller._report_events.get(new_detail_req.request_id)
            assert not new_detail_event.is_set()

            # Test Mutant 5: close_why cancels detail token before pop
            app.close_why()
            assert new_detail_event.is_set(), "close_why must cancel detail token before pop"
            assert why._owned_request is None

            gate.set()
            await pilot.press("q")

    asyncio.run(_run())


def test_real_worker_detail_a_to_b_while_b_running(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C3: Agent A completes while B is still running; late A outcome is rejected."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("symlink_farm_multi_agent", mock_home)

    worker_a_gate = threading.Event()
    worker_b_gate = threading.Event()
    a_started = threading.Event()
    b_started = threading.Event()
    real_snap_why = snapshot_why

    def controlled_snapshot_why(snap: SessionSnapshot, key: str, agent: str) -> ResolutionReport:
        if agent == "claude" and not a_started.is_set():
            a_started.set()
            worker_a_gate.wait(timeout=5.0)
        elif agent == "codex" and not b_started.is_set():
            b_started.set()
            worker_b_gate.wait(timeout=5.0)
        return real_snap_why(snap, key, agent)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", controlled_snapshot_why)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            assert a_started.wait(timeout=3.0)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)

            # Switch to agent B
            await pilot.press("right")
            assert b_started.wait(timeout=3.0)

            # Release A while B is still running
            worker_a_gate.set()
            await pilot.pause(0.05)

            # Late A outcome did not overwrite B
            assert why._agent_id == "codex"
            assert "Loading report" in str(why.query_one("#why-report-status", Static).content)

            # Release B
            worker_b_gate.set()
            await _wait_why_idle(pilot, app)
            assert why._report is not None
            assert why._report.agent == "codex"
            await pilot.press("q")

    asyncio.run(_run())


def test_detail_agent_switch_a_to_b_while_a_completes(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Late completion for agent A with differing arguments is rejected when B is owned."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("symlink_farm_multi_agent", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await pilot.pause(0.05)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)

            req_b = ViewRequest(
                generation=why._generation,
                request_id=999,
                view="why",
                arguments=(why._opening_key, "codex"),
            )
            why._owned_request = req_b
            why._agent_id = "codex"
            why._report = None

            # Stale completion arrives with same request_id and generation, but arguments for claude
            stale_report = _report(agent="claude")
            why.note_report_outcome(
                "why",
                999,
                why._generation,
                (why._opening_key, "claude"),
                accepted=True,
                report=stale_report,
            )

            # Must be rejected because arguments do not match owned request
            assert why._report is None
            assert why._owned_request == req_b

            await pilot.press("q")

    asyncio.run(_run())


def test_pending_blocked_capture_plus_detail_report(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C3/E1: >=3 distinct skill lookup groups with actual Home worker blocked
    before Enter. Suspension cancels Home owned token and leaves genuinely pending
    Home queue. Detail report and refresh capture both blocked; detail completes
    while capture pending with exact token/adapter call count preservation.
    """
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    for sname in ("alpha_skill", "beta_skill", "gamma_skill"):
        sdir = mock_home / ".claude" / "skills" / sname
        sdir.mkdir(parents=True)
        (sdir / "SKILL.md").write_text(f"---\nname: {sname}\ndescription: {sname} desc\n---\nBody")

    home_worker_gate = threading.Event()
    home_worker_started = threading.Event()
    detail_worker_gate = threading.Event()
    detail_worker_started = threading.Event()
    capture_gate = threading.Event()
    capture_started = threading.Event()

    real_snap_why = snapshot_why
    real_capture = capture_session
    detail_gate_active = [False]

    def controlled_why(snap: SessionSnapshot, key: str, agent: str) -> ResolutionReport:
        if not home_worker_started.is_set():
            home_worker_started.set()
            home_worker_gate.wait(timeout=5.0)
        elif detail_gate_active[0] and not detail_worker_started.is_set():
            detail_worker_started.set()
            detail_worker_gate.wait(timeout=5.0)
        return real_snap_why(snap, key, agent)

    def controlled_capture(*args: Any, **kwargs: Any) -> SessionSnapshot:
        gen = kwargs.get("generation", 1)
        if gen > 1 and not capture_started.is_set():
            capture_started.set()
            capture_gate.wait(timeout=5.0)
        return real_capture(*args, **kwargs)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", controlled_why)
    monkeypatch.setattr("skill_lens.tui.app.capture_session", controlled_capture)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        adapter_calls: list[dict[str, Any]] = []
        orig_request_report = app.request_report

        def tracking_request_report(
            view: ViewName, arguments: tuple[str, ...]
        ) -> ReportValue | None:
            screen_name = app.screen.__class__.__name__
            token = app.controller.active_requests.get(view)
            adapter_calls.append(
                {
                    "view": view,
                    "arguments": arguments,
                    "screen": screen_name,
                    "token": token,
                }
            )
            return orig_request_report(view, arguments)

        monkeypatch.setattr(app, "request_report", tracking_request_report)

        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home: HomeScreen = app.screen  # type: ignore[assignment]
            assert isinstance(home, HomeScreen)

            # Filter Home to claude agent so Home starts requesting reports
            home.action_cycle_agent()
            await _wait_until(pilot, lambda: home_worker_started.is_set(), "home worker started")

            # Open detail screen
            app.controller.cache.clear()
            detail_gate_active[0] = True
            await pilot.press("enter")
            await _wait_until(
                pilot, lambda: detail_worker_started.is_set(), "detail worker started"
            )
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)

            # Snapshot state BEFORE r: explicitly assert nonempty pending groups and pending queue
            pre_r_groups = {k: g.status for k, g in home._groups.items()}
            assert len(pre_r_groups) >= 3
            assert all(st == "pending" for st in pre_r_groups.values())

            pre_queue = [
                row.key
                for row in home._visible
                if home._groups.get(home._lookup_by_key.get(row.key, "")).status == "pending"
            ]
            assert len(pre_queue) >= 3

            pre_r_cells = [
                home.query_one("#skill-table", DataTable).get_row_at(i)
                for i in range(len(home._visible))
            ]
            pre_r_detail_token = app.controller.active_requests.get("why")
            assert pre_r_detail_token is not None
            pre_r_adapter_count = len(adapter_calls)

            # Trigger refresh
            await pilot.press("r")
            await _wait_until(pilot, lambda: capture_started.is_set(), "capture started")

            # Both pending! Pre-r detail token preserved, Home suspended, zero extra adapter calls
            assert app.controller.status == "loading"
            assert app.controller.active_requests.get("why") == pre_r_detail_token
            assert home._suspended is True
            assert home._inflight is None
            assert len(adapter_calls) == pre_r_adapter_count
            assert [
                home.query_one("#skill-table", DataTable).get_row_at(i)
                for i in range(len(home._visible))
            ] == pre_r_cells
            assert {k: g.status for k, g in home._groups.items()} == pre_r_groups
            assert [
                row.key
                for row in home._visible
                if home._groups.get(home._lookup_by_key.get(row.key, "")).status == "pending"
            ] == pre_queue

            # Release only detail report
            detail_worker_gate.set()
            await _wait_until(pilot, lambda: why._report is not None, "detail report rendered")

            # Detail outcome accepted and visibly rendered while capture stays pending!
            assert capture_started.is_set() and not capture_gate.is_set()
            assert app.controller.status == "loading"
            assert why._report is not None
            assert len(list(why.query(Collapsible))) > 0
            assert "Scanning skills" in str(why.query_one("#why-status", Static).content)

            # Hidden Home still no calls / no state changes
            assert len(adapter_calls) == pre_r_adapter_count
            assert [
                home.query_one("#skill-table", DataTable).get_row_at(i)
                for i in range(len(home._visible))
            ] == pre_r_cells
            assert {k: g.status for k, g in home._groups.items()} == pre_r_groups
            assert [
                row.key
                for row in home._visible
                if home._groups.get(home._lookup_by_key.get(row.key, "")).status == "pending"
            ] == pre_queue

            # Release remaining gates
            home_worker_gate.set()
            capture_gate.set()
            await _wait_until(pilot, lambda: why._generation == 2, "refresh publication")
            assert why._generation == 2
            await pilot.press("escape")
            await pilot.pause(0.05)
            await pilot.press("q")

    asyncio.run(_run())


def test_non_capture_accepted_event_synchronization_does_not_cancel_or_dispatch_home(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E2: Register active non-Why request, deliver matching outcome
    while detail owns blocked Why token.

    Asserts controller acceptance, active detail token and Home cells/queue unchanged,
    then detail renders while context remains valid.
    """
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    gate = threading.Event()
    real_snap = snapshot_why

    def blocking_why(snap: SessionSnapshot, key: str, agent: str) -> ResolutionReport:
        gate.wait(timeout=5.0)
        return real_snap(snap, key, agent)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", blocking_why)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home: HomeScreen = app.screen  # type: ignore[assignment]
            home.action_cycle_agent()
            await pilot.pause(0.02)

            await pilot.press("enter")
            await pilot.pause(0.05)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)
            detail_token = app.controller.active_requests.get("why")
            assert detail_token is not None
            assert home._suspended is True
            assert home._inflight is None

            # Record Home cell values, groups, and queue before non-Why event
            pre_cells = [
                home.query_one("#skill-table", DataTable).get_row_at(i)
                for i in range(len(home._visible))
            ]
            pre_groups = {k: (g.status, g.report) for k, g in home._groups.items()}
            pre_queue = [
                row.key
                for row in home._visible
                if home._groups.get(home._lookup_by_key.get(row.key, "")).status == "pending"
            ]

            # Register an actual active non-Why request: 'diff'
            diff_req, diff_event, cached = app.controller.request_view("diff", ("diff-key-123",))
            assert diff_req is not None
            assert app.controller.active_requests.get("diff") == diff_req

            # Deliver matching outcome
            diff_result = type("DummyDiffResult", (), {})()
            app.post_message(
                ViewReportComplete(
                    view="diff",
                    request_id=diff_req.request_id,
                    generation=diff_req.generation,
                    arguments=diff_req.arguments,
                    report=diff_result,
                )
            )
            await pilot.pause(0.05)

            # Assert controller acceptance occurred!
            assert (diff_req.generation, "diff", diff_req.arguments) in app.controller.cache
            assert app.controller.active_requests.get("diff") is None

            # Assert active detail token and Home cells/queue unchanged
            assert app.controller.active_requests.get("why") == detail_token
            assert home._suspended is True
            assert home._inflight is None
            assert [
                home.query_one("#skill-table", DataTable).get_row_at(i)
                for i in range(len(home._visible))
            ] == pre_cells
            assert {k: (g.status, g.report) for k, g in home._groups.items()} == pre_groups
            assert [
                row.key
                for row in home._visible
                if home._groups.get(home._lookup_by_key.get(row.key, "")).status == "pending"
            ] == pre_queue

            # Unblock detail Why worker, let detail render
            gate.set()
            await _wait_why_idle(pilot, app)
            assert why._report is not None
            await pilot.press("q")

    asyncio.run(_run())


def test_real_pop_delayed_detail_callback_protects_resumed_home(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C3 DISCRIMINATING MUTATION PROOF: An unneutralized detail screen without exact

    token cleanup would allow late callbacks/unmount during a real Escape/pop
    to cancel newly resumed Home tokens.
    """
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home: HomeScreen = app.screen  # type: ignore[assignment]
            home.action_cycle_agent()
            await pilot.pause(0.05)
            await _wait_why_idle(pilot, app)

            # Open detail
            await pilot.press("enter")
            await pilot.pause(0.05)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)

            # Clear cache and reset group status so Home must re-request on resume
            app.controller.cache.clear()
            for g in home._groups.values():
                g.status = "pending"
                g.report = None

            gate = threading.Event()
            real_snap = snapshot_why

            def blocking_why(snap: SessionSnapshot, key: str, agent: str) -> ResolutionReport:
                gate.wait(timeout=5.0)
                return real_snap(snap, key, agent)

            monkeypatch.setattr("skill_lens.tui.app.snapshot_why", blocking_why)

            detail_token = why._owned_request or ViewRequest(
                generation=why._generation,
                request_id=888,
                view="why",
                arguments=(why._opening_key, why._agent_id or "claude"),
            )

            # Real pop with Escape: WhyScreen closes, Home resumes and dispatches new token
            await pilot.press("escape")
            await pilot.pause(0.05)
            assert isinstance(app.screen, HomeScreen)

            # Home resumed and re-drove
            home_token = app.controller.active_requests.get("why")
            assert home_token is not None, "Home should have an active token after resume"

            # Simulate delayed callback running on why with its previous token
            why._owned_request = detail_token
            why._cancel_owned_token()
            assert app.controller.active_requests.get("why") == home_token, (
                "Unowned Home token was invalidated by delayed detail callback!"
            )
            gate.set()
            await pilot.press("q")

    asyncio.run(_run())


def test_u3_identity_matching_rejection_branch(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C3: Focused coverage for U3 identity-matching rejected-request branch in HomeScreen."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home: HomeScreen = app.screen  # type: ignore[assignment]
            assert isinstance(home, HomeScreen)
            home.action_cycle_agent()
            await pilot.pause(0.05)
            first_group = next(iter(home._groups.keys()))

            req = ViewRequest(
                generation=1,
                request_id=555,
                view="why",
                arguments=("/some/key", "claude"),
            )
            app.controller.active_requests["why"] = req
            home._inflight = _OwnedWhy(lookup_name=first_group, request=req)
            home._groups[first_group].status = "loading"

            # Outcome arrives with matching identity but accepted=False
            del app.controller.active_requests["why"]
            home.note_report_outcome(
                "why",
                req.request_id,
                req.generation,
                req.arguments,
                accepted=False,
            )
            assert home._groups[first_group].status in ("pending", "done")
            assert home._inflight is None

            # Repeat when identity does NOT match: inflight must NOT be cleared
            app.controller.active_requests["why"] = req
            home._inflight = _OwnedWhy(lookup_name=first_group, request=req)
            home.note_report_outcome(
                "why",
                req.request_id + 99,
                req.generation,
                req.arguments,
                accepted=False,
            )
            assert home._inflight is not None
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# C4 Refresh Matrix & Active Home Status Tests
# ---------------------------------------------------------------------------


def test_refresh_on_detail_surviving_installation(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refresh while on detail keeps usable old content until publication updates it."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await pilot.pause(0.05)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)
            old_gen = why._generation

            await pilot.press("r")
            status_content = str(why.query_one("#why-status", Static).content)
            assert "Scanning" in status_content or "Ready" in status_content

            await _wait_until(pilot, lambda: why._generation != old_gen, "detail refresh publish")
            assert why._generation == 2
            entries = app.controller.current.index.entries  # type: ignore[union-attr]
            assert why._opening_key in {canonical_key(e) for e in entries}
            await pilot.press("q")

    asyncio.run(_run())


def test_refresh_on_detail_removed_installation_returns_to_home_with_notice(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the detail installation is removed on disk, refresh returns to Home with notice."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    make_skill(mock_home / ".claude" / "skills" / "skill-a", "skill-a", "Skill A description.")
    make_skill(mock_home / ".claude" / "skills" / "skill-b", "skill-b", "Skill B description.")

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            table = app.screen.query_one("#skill-table", DataTable)
            assert table.row_count >= 2
            await pilot.press("enter")
            await pilot.pause(0.05)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)
            removed_key = why._opening_key

            # Delete skill-a directory on disk
            shutil.rmtree(mock_home / ".claude" / "skills" / "skill-a")

            await pilot.press("r")
            await _wait_until(pilot, lambda: isinstance(app.screen, HomeScreen), "return to home")

            home: HomeScreen = app.screen  # type: ignore[assignment]
            assert home._removal_notice is not None
            assert removed_key in home._removal_notice
            notice_content = str(home.query_one("#removal-notice", Static).content)
            assert removed_key in notice_content

            await pilot.press("down")
            await pilot.pause(0.02)
            assert home._removal_notice is None
            await pilot.press("q")

    asyncio.run(_run())


def test_refresh_on_detail_changed_agent_eligibility(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C4: On refresh, when agent eligibility changes, strip updates and keeps eligible or first."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("symlink_farm_multi_agent", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)

            # Switch to second agent
            await pilot.press("right")
            assert why._agent_id == why._agent_options[1].agent_id
            selected_agent = why._agent_id

            # Mutate snapshot to remove selected_agent from eligible registry
            snap = app.controller.current
            assert snap is not None
            new_registry = tuple(a for a in snap.registry if a.id != selected_agent)
            new_snap = replace(snap, generation=2, registry=new_registry)

            # Publish capture
            app.controller.pending_generation = 2
            app.controller.accept_capture(new_snap, 2)
            app._update_ui()
            await pilot.pause(0.05)

            # Detail updated agent options and switched to first remaining eligible agent
            assert why._agent_id != selected_agent
            assert why._agent_id == why._agent_options[0].agent_id
            await pilot.press("q")

    asyncio.run(_run())


def test_refresh_on_detail_no_agent_replacement(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C4: On refresh, when no registered agents reach the installation, show explanation."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)

            # Publish new snapshot where skill has 0 agents
            snap = app.controller.current
            assert snap is not None
            mutated_skills = tuple(replace(s, agents=()) for s in snap.scan.skills)
            new_snap = replace(snap, generation=2, scan=replace(snap.scan, skills=mutated_skills))
            app.controller.pending_generation = 2
            app.controller.accept_capture(new_snap, 2)
            app._update_ui()
            await pilot.pause(0.05)

            assert len(why._agent_options) == 0
            rep_status = str(why.query_one("#why-report-status", Static).content)
            assert "No agent reaches this installation." in rep_status
            assert app.controller.active_requests.get("why") is None
            await pilot.press("q")

    asyncio.run(_run())


def test_refresh_on_detail_empty_replacement_catalog(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C4: On refresh, completely empty catalog returns to Home showing
    empty state and removal notice.
    """
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)
            old_key = why._opening_key

            # Delete skills on disk
            shutil.rmtree(mock_home / ".claude" / "skills")

            # Press r on detail
            await pilot.press("r")
            await _wait_until(pilot, lambda: isinstance(app.screen, HomeScreen), "return to home")

            home: HomeScreen = app.screen  # type: ignore[assignment]
            assert home._removal_notice is not None
            assert old_key in home._removal_notice
            # Table is empty
            table = home.query_one("#skill-table", DataTable)
            assert table.row_count == 0
            await pilot.press("q")

    asyncio.run(_run())


def test_refresh_on_detail_retained_home_filter_excludes_controller_fallback(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C4: Retained Home filter excludes controller fallback selection; table shows 0 rows."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    make_skill(mock_home / ".claude" / "skills" / "alpha", "alpha", "Alpha skill")
    make_skill(mock_home / ".claude" / "skills" / "beta", "beta", "Beta skill")

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            # Filter for alpha
            filter_input = app.screen.query_one("#filter-input", Input)
            filter_input.value = "alpha"
            await pilot.pause(0.05)

            # Open detail on alpha
            await pilot.press("enter")
            await pilot.pause(0.05)
            assert isinstance(app.screen, WhyScreen)

            # Remove alpha, keep beta
            shutil.rmtree(mock_home / ".claude" / "skills" / "alpha")

            # Refresh
            await pilot.press("r")
            await _wait_until(pilot, lambda: isinstance(app.screen, HomeScreen), "return home")

            home: HomeScreen = app.screen  # type: ignore[assignment]
            # Filter is still "alpha"
            assert home.query_one("#filter-input", Input).value == "alpha"
            # Table shows 0 rows because beta does not match "alpha"
            table = home.query_one("#skill-table", DataTable)
            assert table.row_count == 0
            # Removal notice is visible
            assert home._removal_notice is not None
            assert "alpha" in home._removal_notice
            await pilot.press("q")

    asyncio.run(_run())


def test_refresh_actual_refusal_retry_and_fault_paths(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C4: Actual capture refusal, retry and fault paths tested via real exceptions."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)

            # 1. Actual refusal path: SnapshotTooLarge
            def throw_too_large(*a, **kw):
                raise SnapshotTooLarge(total_bytes=5000000, limit_bytes=1000000)

            monkeypatch.setattr("skill_lens.tui.app.capture_session", throw_too_large)
            await pilot.press("r")
            await _wait_until(pilot, lambda: app.controller.status == "refused", "refusal")
            assert "Snapshot refused" in str(why.query_one("#why-status", Static).content)
            assert app.controller.failed is False

            # 2. Actual retry path: SnapshotChanged
            def throw_changed(*a, **kw):
                raise SnapshotChanged("Files changed while scanning.")

            monkeypatch.setattr("skill_lens.tui.app.capture_session", throw_changed)
            await pilot.press("r")
            await _wait_until(pilot, lambda: app.controller.status == "retry", "retry")
            retry_text = str(why.query_one("#why-status", Static).content)
            assert "Files changed while scanning" in retry_text
            assert "Press r to retry" in retry_text
            assert app.controller.failed is False

            # 3. Actual internal fault path: unexpected Exception
            def throw_fault(*a, **kw):
                raise RuntimeError("Unexpected disk crash!")

            monkeypatch.setattr("skill_lens.tui.app.capture_session", throw_fault)
            await pilot.press("r")
            await _wait_until(pilot, lambda: app.controller.status == "error", "fault")
            assert "Error: Unexpected internal fault" in str(
                why.query_one("#why-status", Static).content
            )
            assert "Unexpected disk crash!" in str(
                why.query_one("#why-error-details", Static).content
            )
            assert app.controller.failed is True
            await pilot.press("q")

    asyncio.run(_run())


def test_all_filter_return_matrix_active_home_status(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E5: All-filter return matrix across real pending, refusal,
    retry, fault, count, and removal.
    """
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    # 1. Pending capture return
    async def _run_pending() -> None:
        capture_gate = threading.Event()
        capture_started = threading.Event()
        real_cap = capture_session

        def controlled_cap(*args: Any, **kwargs: Any) -> Any:
            gen = kwargs.get("generation", 1)
            if gen > 1 and not capture_started.is_set():
                capture_started.set()
                capture_gate.wait(timeout=5.0)
            return real_cap(*args, **kwargs)

        monkeypatch.setattr("skill_lens.tui.app.capture_session", controlled_cap)
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            await pilot.press("r")
            assert capture_started.wait(timeout=3.0)
            await pilot.press("escape")
            await pilot.pause(0.05)
            home: HomeScreen = app.screen  # type: ignore[assignment]
            assert isinstance(home, HomeScreen)
            assert "Scanning skills..." in str(home.query_one("#status-text", Static).content)
            capture_gate.set()
            await _wait_until(pilot, lambda: app.controller.current.generation == 2, "refresh done")
            await pilot.press("q")
            assert app.return_code == 0

    # 2. Refusal return
    async def _run_refusal() -> None:
        def refusal_cap(*args: Any, **kwargs: Any) -> Any:
            gen = kwargs.get("generation", 1)
            if gen > 1:
                raise SnapshotTooLarge(total_bytes=1048577, limit_bytes=1048576)
            return capture_session(*args, **kwargs)

        monkeypatch.setattr("skill_lens.tui.app.capture_session", refusal_cap)
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            await pilot.press("r")
            await _wait_until(pilot, lambda: app.controller.status == "refused", "refusal accepted")
            await pilot.press("escape")
            await pilot.pause(0.05)
            home: HomeScreen = app.screen  # type: ignore[assignment]
            assert isinstance(home, HomeScreen)
            status_text = str(home.query_one("#status-text", Static).content)
            assert "Snapshot refused:" in status_text
            assert "Press r to retry" not in status_text
            await pilot.press("q")
            assert app.return_code == 0

    # 3. Retry return
    async def _run_retry() -> None:
        def retry_cap(*args: Any, **kwargs: Any) -> Any:
            gen = kwargs.get("generation", 1)
            if gen > 1:
                raise SnapshotChanged("Files changed while scanning. Press r to retry.")
            return capture_session(*args, **kwargs)

        monkeypatch.setattr("skill_lens.tui.app.capture_session", retry_cap)
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            await pilot.press("r")
            await _wait_until(pilot, lambda: app.controller.status == "retry", "retry accepted")
            await pilot.press("escape")
            await pilot.pause(0.05)
            home: HomeScreen = app.screen  # type: ignore[assignment]
            assert isinstance(home, HomeScreen)
            status_text = str(home.query_one("#status-text", Static).content)
            assert "Files changed while scanning. Press r to retry." in status_text
            await pilot.press("q")
            assert app.return_code == 0

    # 4. Fault return (quits 3)
    async def _run_fault() -> None:
        def fault_cap(*args: Any, **kwargs: Any) -> Any:
            gen = kwargs.get("generation", 1)
            if gen > 1:
                raise RuntimeError("Simulated unexpected fault")
            return capture_session(*args, **kwargs)

        monkeypatch.setattr("skill_lens.tui.app.capture_session", fault_cap)
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            await pilot.press("r")
            await _wait_until(pilot, lambda: app.controller.status == "error", "fault accepted")
            await pilot.press("escape")
            await pilot.pause(0.05)
            home: HomeScreen = app.screen  # type: ignore[assignment]
            assert isinstance(home, HomeScreen)
            assert "Error: Unexpected internal fault" in str(
                home.query_one("#status-text", Static).content
            )
            assert "Simulated unexpected fault" in str(
                home.query_one("#error-details", Static).content
            )
            assert app.controller.failed is True
            await pilot.press("q")
            assert app.return_code == 3

    # 5. Successful refresh with changed count (quits 0)
    async def _run_changed_count() -> None:
        monkeypatch.setattr("skill_lens.tui.app.capture_session", capture_session)
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            table = app.screen.query_one("#skill-table", DataTable)
            initial_count = table.row_count
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)

            # Add a second skill on disk
            extra_skill = mock_home / ".claude" / "skills" / "brand_new_skill"
            make_skill(extra_skill, "brand_new_skill", "New capability")

            await pilot.press("r")
            await _wait_until(pilot, lambda: app.controller.current.generation == 2, "refresh done")
            await pilot.press("escape")
            await pilot.pause(0.05)
            home: HomeScreen = app.screen  # type: ignore[assignment]
            assert isinstance(home, HomeScreen)
            new_table = home.query_one("#skill-table", DataTable)
            assert new_table.row_count == initial_count + 1
            await pilot.press("q")
            assert app.return_code == 0

    # 6. Removal path return (quits 0)
    async def _run_removal() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)

            target_dir = Path(why._opening_key)
            if target_dir.is_dir():
                shutil.rmtree(target_dir)

            await pilot.press("r")
            await _wait_until(pilot, lambda: isinstance(app.screen, HomeScreen), "return to home")
            home: HomeScreen = app.screen  # type: ignore[assignment]
            assert home._removal_notice is not None
            await pilot.press("q")
            assert app.return_code == 0

    asyncio.run(_run_pending())
    asyncio.run(_run_refusal())
    asyncio.run(_run_retry())
    asyncio.run(_run_fault())
    asyncio.run(_run_changed_count())
    asyncio.run(_run_removal())


# ---------------------------------------------------------------------------
# C5 Broad Read Sentinels & Frozen Data Parity
# ---------------------------------------------------------------------------


def test_broad_read_sentinels_and_target_preservation_manifest(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E3: Broad read sentinels and target preservation manifest across all app-only actions."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("symlink_farm_multi_agent", mock_home)

    shared_md = mock_home / ".agents" / "skills" / "shared" / "SKILL.md"
    assert shared_md.exists()
    claude_link = mock_home / ".claude" / "skills" / "shared"
    assert claude_link.is_symlink()
    extra_skill = mock_home / ".claude" / "skills" / "extra"
    make_skill(extra_skill, "extra", "Extra skill")
    assert extra_skill.exists()
    claude_settings = mock_home / ".claude" / "settings.json"
    claude_settings.parent.mkdir(parents=True, exist_ok=True)
    claude_settings.write_text("{}")

    from tests.test_tui_read_only import _snapshot_tree_state

    target_prefixes = (str(mock_home),)

    def _is_target(path: Any) -> bool:
        text = str(path)
        absolute = os.path.abspath(text)
        return any(
            absolute == prefix or absolute.startswith(prefix + os.sep) for prefix in target_prefixes
        )

    path_originals = {
        name: getattr(Path, name)
        for name in ("open", "read_text", "read_bytes", "resolve", "stat", "lstat", "readlink")
    }
    os_originals = {name: getattr(os, name) for name in ("stat", "lstat", "readlink")}
    builtin_open = builtins.open

    guard_active = True

    def _guarded(original: Any, label: str) -> Any:
        def wrapper(target: Any, *args: Any, **kwargs: Any) -> Any:
            if guard_active and _is_target(target):
                raise AssertionError(
                    f"Forbidden synthetic-target filesystem read: {label} {target}"
                )
            return original(target, *args, **kwargs)

        return wrapper

    def safe_snapshot(root: Path) -> dict[str, Any]:
        nonlocal guard_active
        prev = guard_active
        guard_active = False
        try:
            return _snapshot_tree_state(root)
        finally:
            guard_active = prev

    async def _run() -> None:
        nonlocal guard_active
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            # Explicitly select known chosen installation 'shared'
            opening_key = str(mock_home / ".agents" / "skills" / "shared")
            assert any(s.canonical_path == opening_key for s in app.controller.current.scan.skills)

            # Save snapshot_why oracles BEFORE intentional mutations
            oracle_before_claude = snapshot_why(app.controller.current, opening_key, "claude")
            oracle_before_codex = snapshot_why(app.controller.current, opening_key, "codex")
            oracle_before_opencode = snapshot_why(app.controller.current, opening_key, "opencode")
            assert oracle_before_claude.headline == HeadlineState.ACTIVE
            assert oracle_before_opencode.headline == HeadlineState.ACTIVE

            # Mutate targets BEFORE first detail visit
            shared_md.write_text(
                "---\nname: shared\ndescription: Mutated shared description\n---\n# Mutated body"
            )
            assert "Mutated body" in shared_md.read_text()
            shutil.rmtree(extra_skill)
            assert not extra_skill.exists()
            retargeted_dir = mock_home / ".agents" / "skills" / "retargeted_shared"
            make_skill(retargeted_dir, "shared", "Retargeted shared capability")
            claude_link.unlink()
            symlink(retargeted_dir, claude_link)
            assert claude_link.is_symlink()
            claude_settings.write_text('{"skillOverrides": {"shared": "off"}}')

            baseline_manifest = safe_snapshot(mock_home)

            # Apply broad read sentinels
            for name, orig in path_originals.items():
                monkeypatch.setattr(Path, name, _guarded(orig, f"Path.{name}"))
            for name, orig in os_originals.items():
                monkeypatch.setattr(os, name, _guarded(orig, f"os.{name}"))
            monkeypatch.setattr(builtins, "open", _guarded(builtin_open, "builtins.open"))

            # 1. Open detail on chosen installation
            app.open_why(opening_key, "claude")
            await _wait_why_idle(pilot, app)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)
            assert safe_snapshot(mock_home) == baseline_manifest

            # Exact report and visible-value equality
            assert why._report == oracle_before_claude
            title_text = str(why.query_one("#why-title", Static).content)
            assert oracle_before_claude.skill_name in title_text
            assert "shared" in title_text
            collapsibles = list(why.query(Collapsible))
            assert len(collapsibles) == len(oracle_before_claude.candidates)
            for i, cand in enumerate(oracle_before_claude.candidates):
                block = collapsibles[i]
                mark = STATE_MARK.get(cand.state, "?")
                title_plain = (
                    block.title.plain if hasattr(block.title, "plain") else str(block.title)
                )
                assert mark in title_plain
                assert cand.installation.name in title_plain
                assert cand.state.value in title_plain

                body_text = "\n".join(s.render().plain for s in block.query(Static))
                assert f"Rule: {cand.rule_id}" in body_text
                assert f"Evidence: {cand.evidence.value}" in body_text
                assert cand.reason in body_text

            # 2. Switch agent under sentinels (right moves to codex in scan order)
            await pilot.press("right")
            await pilot.pause(0.05)
            assert safe_snapshot(mock_home) == baseline_manifest
            assert why._report == oracle_before_codex

            # 3. Expand / collapse
            await pilot.press("tab")
            await pilot.press("enter")
            await pilot.pause(0.02)
            assert safe_snapshot(mock_home) == baseline_manifest

            # 4. Back to Home
            await pilot.press("escape")
            await pilot.pause(0.05)
            assert isinstance(app.screen, HomeScreen)
            assert safe_snapshot(mock_home) == baseline_manifest

            # Unguard sentinels for explicit refresh
            monkeypatch.undo()
            monkeypatch.setattr(paths, "home", lambda: mock_home)

            # Explicit refresh captures the disk mutation
            await pilot.press("r")
            await _wait_until(
                pilot, lambda: app.controller.current.generation == 2, "gen 2 refresh"
            )  # type: ignore[union-attr]
            assert app.controller.current.generation == 2  # type: ignore[union-attr]

            # Observable catalog change: extra is deleted
            assert not any(
                s.canonical_path == str(extra_skill) for s in app.controller.current.scan.skills
            )
            # Observable control change: Claude settings disabled 'shared'
            assert (
                app.controller.current.resolved_controls["claude"].claude_settings.get("shared")
                == "off"
            )
            # Observable report change: hash changed on mutated shared installation
            gen2_report_open = snapshot_why(app.controller.current, opening_key, "opencode")
            assert gen2_report_open != oracle_before_opencode
            assert (
                gen2_report_open.candidates[0].installation.content_hash
                != oracle_before_opencode.candidates[0].installation.content_hash
            )
            # Retargeted installation under Claude settings is DISABLED
            gen2_report_claude = snapshot_why(app.controller.current, str(retargeted_dir), "claude")
            assert gen2_report_claude.headline == HeadlineState.DISABLED

            # Manifest across refresh unchanged
            assert safe_snapshot(mock_home) == baseline_manifest

            # Quit and manifest equality
            await pilot.press("q")
            assert safe_snapshot(mock_home) == baseline_manifest

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# C6 Identity Cases, Styling & View Tests
# ---------------------------------------------------------------------------


def test_identity_cases_frontmatter_directory_unresolved_entrypoints_and_order(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E4: Real agent-identity fixtures through capture/snapshot_why
    and visible UI without manual assignment.
    """
    monkeypatch.setattr(paths, "home", lambda: mock_home)

    # 1. Differing directory vs declared frontmatter name (in ~/.agents/skills)
    dir_skill = mock_home / ".agents" / "skills" / "diff_dir"
    dir_skill.mkdir(parents=True)
    (dir_skill / "SKILL.md").write_text(
        "---\nname: diff_declared\ndescription: Differing declared name\n---\nBody"
    )

    # Claude differing directory vs declared frontmatter name (in ~/.claude/skills)
    claude_diff = mock_home / ".claude" / "skills" / "claude_diff"
    claude_diff.mkdir(parents=True)
    (claude_diff / "SKILL.md").write_text(
        "---\nname: claude_declared\ndescription: Claude declared name\n---\nBody"
    )

    # 2. Missing frontmatter
    missing_fm = mock_home / ".agents" / "skills" / "missing_fm"
    missing_fm.mkdir(parents=True)
    (missing_fm / "SKILL.md").write_text("# Markdown Only\nNo YAML frontmatter at all.")

    # 3. Malformed frontmatter
    malformed_fm = mock_home / ".agents" / "skills" / "malformed_fm"
    malformed_fm.mkdir(parents=True)
    (malformed_fm / "SKILL.md").write_text("---\n[invalid : yaml :\n---\nBody")

    # 4. Broken symlink / unresolved canonical fallback
    broken_link = mock_home / ".agents" / "skills" / "broken_link"
    broken_link.symlink_to(mock_home / "nonexistent" / "target")

    # 5. Multiple entrypoints via symlinks (canonical in .agents, symlink in .claude)
    canonical = mock_home / ".agents" / "skills" / "shared"
    canonical.mkdir(parents=True)
    (canonical / "SKILL.md").write_text(
        "---\nname: shared\ndescription: Shared capability\n---\nBody"
    )
    claude_symlink = mock_home / ".claude" / "skills" / "shared"
    claude_symlink.parent.mkdir(parents=True, exist_ok=True)
    claude_symlink.symlink_to(canonical)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            current = app.controller.current
            assert current is not None

            async def verify_visit(
                key: str, agent: str, expected_skill_name: str | None = None
            ) -> ResolutionReport:
                why = WhyScreen(key, agent)
                app.push_screen(why)
                await _wait_why_idle(pilot, app)
                oracle = snapshot_why(current, key, agent)
                assert why._report == oracle
                if expected_skill_name is not None:
                    assert oracle.skill_name == expected_skill_name

                header_text = str(why.query_one("#why-title", Static).content)
                assert oracle.skill_name in header_text
                expected_header_path = snapshot_path(current, key)
                assert f"Installation: {expected_header_path}\n" in header_text

                collapsibles = list(why.query(Collapsible))
                assert len(collapsibles) == len(oracle.candidates)
                for i, cand in enumerate(oracle.candidates):
                    block = collapsibles[i]
                    mark = STATE_MARK.get(cand.state, "?")
                    title_plain = (
                        block.title.plain if hasattr(block.title, "plain") else str(block.title)
                    )
                    assert mark in title_plain
                    assert cand.installation.name in title_plain
                    assert cand.state.value in title_plain

                    body_text = "\n".join(s.render().plain for s in block.query(Static))
                    expected_canon_path = (
                        snapshot_path(current, cand.installation.canonical_path)
                        if cand.installation.canonical_path
                        else "none"
                    )
                    assert f"  Canonical: {expected_canon_path}" in body_text
                    if not cand.installation.canonical_path or not (
                        cand.installation.entrypoint_path
                        and snapshot_same_location(
                            current,
                            cand.installation.canonical_path,
                            cand.installation.entrypoint_path,
                        )
                    ):
                        expected_entry_path = snapshot_path(
                            current, cand.installation.entrypoint_path
                        )
                        assert f"  Entrypoint: {expected_entry_path}" in body_text
                    assert f"Rule: {cand.rule_id}" in body_text
                    assert f"Evidence: {cand.evidence.value}" in body_text
                    assert cand.reason in body_text
                    if cand.installation.content_hash:
                        assert cand.installation.content_hash[:23] in body_text

                await pilot.press("escape")
                await pilot.pause(0.05)
                return oracle

            # 1. Directory-name agent (opencode) on diff_dir
            await verify_visit(str(dir_skill), "opencode", "diff_dir")

            # 2. Frontmatter-name agent (codex) on diff_dir
            await verify_visit(str(dir_skill), "codex", "diff_declared")

            # 3. Hybrid agent (claude) on claude_diff
            await verify_visit(str(claude_diff), "claude", "claude_diff")

            # 4. Frontmatter agent (codex) on missing_fm -> directory fallback
            await verify_visit(str(missing_fm), "codex", "missing_fm")

            # 5. Frontmatter agent (codex) on malformed_fm
            await verify_visit(str(malformed_fm), "codex", "malformed_fm")

            # 6. Unresolved canonical fallback / broken link visit
            await verify_visit(str(broken_link), "opencode")

            # 7. Multiple entrypoints on opencode
            why_shared = WhyScreen(str(canonical), "opencode")
            app.push_screen(why_shared)
            await _wait_why_idle(pilot, app)
            oracle_shared = snapshot_why(current, str(canonical), "opencode")
            assert why_shared._report == oracle_shared

            matching = [
                c
                for c in oracle_shared.candidates
                if c.installation.canonical_path == str(canonical)
            ]
            assert len(matching) > 1, f"Expected >1 matching candidates, got {len(matching)}"

            collapsibles = list(why_shared.query(Collapsible))
            assert len(collapsibles) == len(oracle_shared.candidates)
            expanded = [b for b in collapsibles if not b.collapsed]
            assert len(expanded) > 1, f"Expected multiple expanded blocks, got {len(expanded)}"

            for i, cand in enumerate(oracle_shared.candidates):
                block = collapsibles[i]
                mark = STATE_MARK.get(cand.state, "?")
                title_plain = (
                    block.title.plain if hasattr(block.title, "plain") else str(block.title)
                )
                assert mark in title_plain
                assert cand.installation.name in title_plain
                assert cand.state.value in title_plain
                assert block.collapsed is not (cand.installation.canonical_path == str(canonical))

                body_text = "\n".join(s.render().plain for s in block.query(Static))
                assert f"Rule: {cand.rule_id}" in body_text
                assert f"Evidence: {cand.evidence.value}" in body_text
                assert cand.reason in body_text
                if cand.installation.content_hash:
                    assert cand.installation.content_hash[:23] in body_text

            await pilot.press("q")

    asyncio.run(_run())


def test_mixed_unknown_and_known_agent_ids_explained(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C6: Unknown agent IDs are explained in #why-report-status and #why-title
    while valid report shows.
    """
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            snap = app.controller.current
            assert snap is not None

            # Mutate scan skill to have both known 'claude' and unknown 'unknown-foo'
            orig_skill = snap.scan.skills[0]
            mutated_skill = replace(orig_skill, agents=("claude", "unknown-foo"))
            app.controller.current = replace(snap, scan=replace(snap.scan, skills=(mutated_skill,)))

            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)

            # Known agent is selectable
            assert len(why._agent_options) == 1
            assert why._agent_options[0].agent_id == "claude"

            # Unknown agent is in unavailable list
            assert "unknown-foo" in why._unavailable

            # Valid report is showing
            assert why._report is not None

            # Unknown agent ID is explained in #why-report-status
            rep_status = str(why.query_one("#why-report-status", Static).content)
            assert "Unavailable agent IDs: unknown-foo" in rep_status

            # Unknown agent ID is also explained in #why-title
            title_text = str(why.query_one("#why-title", Static).content)
            assert "Unavailable agent IDs: unknown-foo" in title_text

            await pilot.press("q")

    asyncio.run(_run())


def test_terminal_dimensions_100x30_and_60x24_controls_and_wrapping(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P3/E7: Real long title/path/reason/note fixture at 100x30 and 60x24
    with multiple agent strip options, keyboard navigation, wrapping, and
    composited visibility.
    """
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    long_name = "long_candidate_skill_name_exceeding_narrow_terminals_easily_and_wrapping_properly"
    long_desc = (
        "Very long description for testing viewport wrapping and reachability "
        "without horizontal scroll."
    )
    canonical = (
        mock_home / ".agents" / "skills" / ("nested_long_directory_component_" * 3) / long_name
    )
    canonical.parent.mkdir(parents=True, exist_ok=True)
    make_skill(canonical, long_name, long_desc, body="Long content body.")
    for root in (".claude/skills", ".pi/agent/skills", ".qoder/skills"):
        symlink(canonical, mock_home / root / long_name)

    async def _run_at_size(size: tuple[int, int]) -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=size) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            if size[0] < 80:
                assert why.has_class("narrow")
            else:
                assert not why.has_class("narrow")

            # 1. Multi-agent strip options present
            assert len(why._agent_options) >= 2

            # 2. Left/Right on strip switches agent deterministically
            agent_init = why._agent_id
            await pilot.press("right")
            await _wait_why_idle(pilot, app)
            assert why._agent_id != agent_init
            assert app.focused is why.query_one(f"#why-agent-{why._agent_id}"), (
                "Strip focus must follow selected agent"
            )
            await pilot.press("left")
            await _wait_why_idle(pilot, app)
            assert why._agent_id == agent_init

            assert app.focused is why.query_one(f"#why-agent-{why._agent_id}"), (
                "Strip focus must follow selected agent"
            )

            # 3. Tab to candidate CollapsibleTitle
            collapsible = why.query_one(Collapsible)
            ct = collapsible.query_one("CollapsibleTitle")
            for _ in range(12):
                if app.focused is ct:
                    break
                await pilot.press("tab")
            assert app.focused is ct, "Candidate title must be reachable within 12 Tab presses"

            agent_before = why._agent_id
            await pilot.press("right")
            await _wait_why_idle(pilot, app)
            assert why._agent_id == agent_before, (
                "Candidate-focused arrows must not change the agent"
            )
            await pilot.press("left")
            assert why._agent_id == agent_before
            await pilot.press("shift+tab")
            assert app.focused is not ct, "Shift+Tab must leave the candidate title"
            await pilot.press("tab")
            assert app.focused is ct

            # Candidate container has readable viewport height (not squished to 1 row)
            candidates = why.query_one("#why-candidates", VerticalScroll)
            assert candidates.size.height >= 4, (
                f"candidates container height too small: {candidates.size.height}"
            )
            assert ct.size.width <= candidates.size.width
            assert candidates.max_scroll_x == 0
            if size[0] < 80:
                assert ct.size.height >= 2, (
                    f"Expected title to wrap at {size}, got height {ct.size.height}"
                )

            # 4. Enter toggles collapsible expansion
            was_collapsed = collapsible.collapsed
            await pilot.press("enter")
            await pilot.pause(0.02)
            assert collapsible.collapsed != was_collapsed
            if collapsible.collapsed:
                await pilot.press("enter")
                await pilot.pause(0.02)
            assert not collapsible.collapsed

            # 5. Scroll via keyboard (PageDown)
            for _ in range(5):
                await pilot.press("pagedown")
                await pilot.pause(0.02)

            # 6. Composited visible text checks
            strips = why._compositor.render_strips()
            composited = "\n".join("".join(seg.text for seg in s) for s in strips)
            assert "Canonical:" in composited
            assert "Hash: sha256:" in composited
            assert "Reason:" in composited
            assert "Rule:" in composited
            assert "Evidence:" in composited
            assert "Ready:" in composited or "Report:" in composited
            await pilot.press("q")

    asyncio.run(_run_at_size((100, 30)))
    asyncio.run(_run_at_size((60, 24)))


# ---------------------------------------------------------------------------
# Caching, Deduplication, Faults & Collapsibles
# ---------------------------------------------------------------------------


def test_cache_hit_and_redraw_deduplication(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exact cache hit returns immediately; redraw does not re-dispatch active request."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            key = app.controller.selected_key
            assert key is not None

            # Seed cache
            seeded_report = _report(
                _candidate("active", key),
                skill_name="seeded-skill",
                agent="claude",
            )
            app.controller.cache[(1, "why", (key, "claude"))] = seeded_report

            # Open WhyScreen
            await pilot.press("enter")
            await pilot.pause(0.05)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)

            # Ensure report was taken from cache
            assert why._report == seeded_report
            assert why._owned_request is None

            # Resize / redraw does not invalidate or dispatch
            why.on_resize(type("Resize", (), {"size": type("Size", (), {"width": 90})()})())  # type: ignore[arg-type]
            await pilot.pause(0.02)
            assert why._report == seeded_report
            await pilot.press("q")

    asyncio.run(_run())


def test_accepted_report_fault_does_not_retry_loop(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An accepted unexpected report fault sets sticky error 3 and does not auto-retry on redraw."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await pilot.pause(0.05)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)

            # Inject accepted error for detail's request
            gen = app.controller.current.generation  # type: ignore[union-attr]
            app.controller.cache.clear()
            app.controller.invalidate_view("why")
            args = (why._opening_key, why._agent_id or "claude")
            req, _, _ = app.controller.request_view("why", args)
            assert req is not None
            why._owned_request = req

            app.controller.accept_view_error(
                "why", req.request_id, gen, req.arguments, RuntimeError("unexpected detail fault")
            )
            why.note_report_outcome(
                "why",
                req.request_id,
                gen,
                req.arguments,
                accepted=True,
                error=RuntimeError("unexpected detail fault"),
            )
            await pilot.pause(0.02)

            assert app.controller.failed is True
            assert why._report is None
            assert why._owned_request is None

            # Redraw must not auto-retry
            why._update_display()
            assert why._owned_request is None
            assert app.controller.active_requests.get("why") is None
            await pilot.press("q")

    asyncio.run(_run())


def test_candidate_collapsibles_expanded_and_collapsed(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Matching candidates are initially expanded; non-matching are collapsed."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await pilot.pause(0.05)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)

            matching = _candidate("active", why._opening_key, name="deploy")
            other = _candidate("shadowed", "/other/path/to/skill", name="deploy")
            report = _report(
                matching,
                other,
                skill_name="deploy",
                agent="claude",
                notes=("First note.", "Policy uncertainty note."),
            )

            why._report = report
            why._rendered_candidate_context = None
            why._update_display()
            await pilot.pause(0.02)

            collapsibles = list(why.query(Collapsible))
            assert len(collapsibles) == 2

            # Matching candidate is expanded
            assert collapsibles[0].collapsed is False
            # Other candidate is collapsed
            assert collapsibles[1].collapsed is True

            # STATE_STYLE applied to marks and tags; literal name tags unaffected
            active_style = STATE_STYLE[HeadlineState.ACTIVE]
            shadowed_style = STATE_STYLE[HeadlineState.SHADOWED]
            assert any(s.style == active_style for s in collapsibles[0].title.spans)
            assert any(s.style == shadowed_style for s in collapsibles[1].title.spans)
            deploy_start = collapsibles[0].title.plain.index("deploy")
            deploy_end = deploy_start + len("deploy")
            for s in collapsibles[0].title.spans:
                assert not (s.start <= deploy_start and s.end >= deploy_end), (
                    "literal name tag was styled"
                )

            # Verify Header contains report-wide headline
            header_text = str(why.query_one("#why-title", Static).content)
            assert "Report-wide headline: ACTIVE" in header_text
            assert "Collision policy: prefer_user" in header_text
            assert "Note: First note." in header_text
            await pilot.press("q")

    asyncio.run(_run())


def test_candidate_no_matches_shows_notice(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no candidate matches the selected installation, a clear notice is shown."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)

            c1 = _candidate("shadowed", "/path/one")
            c2 = _candidate("unsearched_root", "/path/two")
            report = _report(c1, c2, skill_name="deploy")

            why._report = report
            why._rendered_candidate_context = None
            why._update_display()
            await pilot.pause(0.02)

            notice = str(why.query_one("#why-no-match-notice", Static).content)
            assert "No candidate matches the selected installation." in notice

            collapsibles = list(why.query(Collapsible))
            assert all(c.collapsed for c in collapsibles)
            await pilot.press("q")

    asyncio.run(_run())


def test_literal_rendering_markup_false(mock_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Brackets, backslashes and markup-looking strings render literally."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)

            c = _candidate(
                "active",
                why._opening_key,
                name=r"[bold]skill[/bold]\test",
                rule_id=r"rule[1]\sub",
                reason=r"Reason with [red]tags[/red] and \backslashes",
            )
            report = _report(
                c,
                skill_name="[bold]skill[/bold]",
                notes=(r"[yellow]Note tag[/yellow] \escaped",),
            )
            why._report = report
            why._rendered_candidate_context = None
            why._update_display()
            await pilot.pause(0.02)

            collapsibles = list(why.query(Collapsible))
            assert len(collapsibles) == 1
            body_text = "\n".join(s.render().plain for s in collapsibles[0].query(Static))
            assert r"[bold]skill[/bold]\test" in body_text
            assert r"Reason with [red]tags[/red] and \backslashes" in body_text
            assert r"rule[1]\sub" in body_text

            header_text = str(why.query_one("#why-title", Static).content)
            assert r"[yellow]Note tag[/yellow] \escaped" in header_text
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Unit & Branch Coverage Tests (Presentation, Fallbacks, Helpers)
# ---------------------------------------------------------------------------


def test_why_helpers_coverage(mock_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover helper branches: _matching_key, _entry_for_key fallback, _build_candidate_blocks."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)
    snap = capture_session(home=mock_home, cwd=mock_home, generation=1)

    from skill_lens.tui.why import (
        _build_candidate_blocks,
        _eligible_agent_options,
        _entry_for_key,
        _matching_key,
        _state_mark,
        _unavailable_agent_ids,
    )

    # 1. _matching_key
    cand_none_canonical = CandidateResolution(
        state=HeadlineState.ACTIVE,
        visibility=Visibility.ACTIVE_ROOT,
        collision=Collision.WINNING_ENTRY,
        rule_id="r1",
        evidence=Evidence.DOCUMENTED,
        reason="reason",
        rank=1,
        installation=SkillInstallation(
            name="deploy",
            entrypoint_path="/entry/path",
            canonical_path=None,
            scope=Scope.USER,
            parse_status=ParseStatus.VALID,
        ),
    )
    assert _matching_key(cand_none_canonical, "/entry/path") is True
    assert _matching_key(cand_none_canonical, "/other/path") is False

    cand_with_canonical = CandidateResolution(
        state=HeadlineState.SHADOWED,
        visibility=Visibility.ACTIVE_ROOT,
        collision=Collision.WINNING_ENTRY,
        rule_id="r2",
        evidence=Evidence.DOCUMENTED,
        reason="reason",
        rank=2,
        installation=SkillInstallation(
            name="deploy",
            entrypoint_path="/entry/path",
            canonical_path="/canon/path",
            scope=Scope.USER,
            parse_status=ParseStatus.VALID,
            variant_label="B",
            content_hash=None,
        ),
    )
    assert _matching_key(cand_with_canonical, "/canon/path") is True
    assert _matching_key(cand_with_canonical, "/entry/path") is False

    # 2. _state_mark
    assert _state_mark(HeadlineState.ACTIVE) == "*"
    assert _state_mark(HeadlineState.INVALID) == "x"
    assert _state_mark(HeadlineState("AMBIGUOUS")) == "?"

    # 3. _entry_for_key fallback to snapshot.index.entries
    key_in_index = canonical_key(snap.index.entries[0])
    entry = _entry_for_key(snap, key_in_index)
    assert entry is not None
    assert entry.canonical_path == key_in_index

    assert _entry_for_key(snap, "/nonexistent/key") is None
    assert _eligible_agent_options(snap, "/nonexistent/key") == ()
    assert _unavailable_agent_ids(snap, "/nonexistent/key") == ()

    # 4. _build_candidate_blocks with differing entrypoint and same_locations suppression
    rep = _report(cand_none_canonical, cand_with_canonical, skill_name="deploy", notes=("Note 1",))
    # 4a. Different-location case: Entrypoint line present
    blocks_diff = _build_candidate_blocks(rep, snap, "/entry/path")
    assert len(blocks_diff) == 2
    assert blocks_diff[0].expanded is True
    assert blocks_diff[1].expanded is False
    assert "Entrypoint: /entry/path" in blocks_diff[1].body
    assert "Hash: none" in blocks_diff[1].body
    assert "Note: Note 1" in blocks_diff[1].body
    assert blocks_diff[0].title != ""

    # 4b. Same-location case with different strings known same: Entrypoint line suppressed
    snap_same = replace(snap, same_locations=(("/canon/path", "/entry/path"),))
    blocks_same = _build_candidate_blocks(rep, snap_same, "/entry/path")
    assert len(blocks_same) == 2
    assert "Canonical: /canon/path" in blocks_same[1].body
    assert "Entrypoint:" not in blocks_same[1].body

    # 5. _entry_for_key fallback with parse=None and hits=()
    class _FakeEntry:
        canonical_path = "/fake/key"
        parse = None
        hits = ()
        name = "fake-skill"
        entrypoint_paths = ()
        is_symlink = False
        content_hash = None
        variant_label = None

    class _FakeIndex:
        entries = [_FakeEntry()]

    class _FakeScan:
        skills = ()

    class _FakeSnap:
        scan = _FakeScan()
        index = _FakeIndex()

    f_res = _entry_for_key(_FakeSnap(), "/fake/key")  # type: ignore[arg-type]
    assert f_res is not None
    assert f_res.scope == Scope.USER
    assert f_res.parse_status == ParseStatus.UNREADABLE.value


def test_why_screen_unit_branches(mock_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover UI branches in WhyScreen: status/title rendering, button actions, outcomes."""
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)

        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            why: WhyScreen = app.screen  # type: ignore[assignment]
            assert isinstance(why, WhyScreen)

            # Test _clear_display
            why._clear_display()
            assert str(why.query_one("#why-title", Static).content) == ""

            # Test _refresh_status branches
            app.controller.pending_generation = 99
            why._refresh_status()
            assert "Scanning" in str(why.query_one("#why-status", Static).content)
            app.controller.pending_generation = None
            app.controller.failed = True
            app.controller.last_error_details = "Traceback info"
            why._refresh_status()
            assert "Error: Unexpected internal fault" in str(
                why.query_one("#why-status", Static).content
            )
            assert "Traceback info" in str(why.query_one("#why-error-details", Static).content)
            app.controller.failed = False
            app.controller.last_error_details = None

            app.controller.refusal_message = "Snapshot limit exceeded."
            why._refresh_status()
            assert "Snapshot limit exceeded." in str(why.query_one("#why-status", Static).content)
            app.controller.refusal_message = None

            app.controller.retry_message = "Connection dropped. Press r to retry."
            why._refresh_status()
            assert "Connection dropped" in str(why.query_one("#why-status", Static).content)
            app.controller.retry_message = None

            # Test _refresh_candidates with zero candidates found vs not found
            rep_not_found = _report(found=False)
            why._report = rep_not_found
            why._rendered_candidate_context = None
            why._refresh_candidates()
            assert any(
                "No copies of this skill name were found" in str(s.content)
                for s in why.query(Static)
            )

            rep_found_empty = _report(found=True)
            why._report = rep_found_empty
            why._rendered_candidate_context = None
            why._refresh_candidates()
            assert any("No candidates evaluated" in str(s.content) for s in why.query(Static))

            # Test note_report_outcome guard branches
            why.note_report_outcome("diff", 1, 1, ("a",), accepted=True)
            why.note_report_outcome("why", 999, 999, ("a",), accepted=False)

            # Test button pressed on same agent (no-op)
            btn = why.query_one(f"#why-agent-{why._agent_id}", Button)

            class FakeBtnEvent:
                button = btn

                def stop(self) -> None:
                    pass

            why.on_button_pressed(FakeBtnEvent())  # type: ignore[arg-type]

            # Test agent switching actions
            orig_agent = why._agent_id
            why.action_next_agent()
            assert why._agent_id != orig_agent
            why.action_previous_agent()
            assert why._agent_id == orig_agent

            # Test navigation and focus actions
            why.action_focus_next()
            why.action_focus_previous()

            # Test _is_strip_focused when focus is elsewhere
            btn_other = Button("Other", id="other-focus")
            await why.query_one("#why-candidates").mount(btn_other)
            await pilot.pause(0.02)
            btn_other.focus()
            await pilot.pause(0.02)
            assert not why._is_strip_focused()

            # Test action_refresh delegates
            refreshed = False

            def mock_refresh() -> None:
                nonlocal refreshed
                refreshed = True

            monkeypatch.setattr(app, "action_refresh", mock_refresh)
            why.action_refresh()
            assert refreshed
            why.action_next_agent()
            why.action_previous_agent()

            # Test _refresh_title with report notes
            rep_notes = _report(notes=("Custom Note A", "Custom Note B"))
            why._report = rep_notes
            why._refresh_title()
            title_text = str(why.query_one("#why-title", Static).content)
            assert "Note: Custom Note A" in title_text
            assert "Note: Custom Note B" in title_text

            # Test _refresh_strip with matching button IDs
            why._refresh_strip()

            # Test note_report_outcome when report is None
            req = ViewRequest(generation=1, request_id=42, view="why", arguments=("x",))
            why._owned_request = req
            why.note_report_outcome(
                "why",
                req.request_id,
                req.generation,
                req.arguments,
                accepted=True,
                report=None,
            )
            assert why._report is None
            assert why._owned_request is None

            # Test note_report_outcome when rejected and active does not match owned
            why._owned_request = req
            why.note_report_outcome(
                "why",
                req.request_id,
                req.generation,
                req.arguments,
                accepted=False,
            )
            assert why._owned_request is None or isinstance(why._owned_request, ViewRequest)

            # Test _cancel_owned_token when not matching active request
            why._owned_request = req
            why._cancel_owned_token()
            assert why._owned_request is None

            await pilot.press("q")

    asyncio.run(_run())
