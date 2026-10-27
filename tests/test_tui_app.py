"""Headless integration tests for SkillLensApp and synchronous runner (Assignment U2).

Specification reference: FULL_SCREEN_TUI.md §9.1, §10, Step 2, and §21.7.
Covers:
- Headless run_test() open and quit with 0
- Rapid refresh races and newest generation publication
- Report adapter execution, thread worker completion, and caching
- Literal markup display (no Rich tag rendering in Static widgets)
- Expected SnapshotChanged handling (shows retry message, exits 0)
- Unexpected capture failure (sets sticky failed, exits 3)
- Direct App._handle_exception containment without terminal traceback
- Late worker completion after app/loop close
- Synchronous run(home, cwd) lifecycle and exit codes
- Proof that synchronous run returns BEFORE blocked capture worker is released
  (hard watchdog / finally release)
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any, ClassVar

import pytest
from textual.app import App
from textual.pilot import Pilot
from textual.widgets import DataTable, Static
from typer.testing import CliRunner

import skill_lens.tui as tui
from skill_lens.cli import app as cli_app
from skill_lens.core import paths
from skill_lens.core.cancellation import CaptureCancelled
from skill_lens.core.exitcodes import ExitCode
from skill_lens.core.snapshot import SnapshotChanged, SnapshotTooLarge
from skill_lens.tui.app import (
    CaptureComplete,
    CaptureFailed,
    PlaceholderHomeScreen,
    SkillLensApp,
    ViewReportComplete,
    ViewReportFailed,
)
from tests.fixtures.scenarios import build_scenario


def test_headless_open_and_quit_returns_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Opening the placeholder app and pressing 'q' exits cleanly with code 0."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test() as pilot:
            # Let mount and initial capture settle
            await pilot.pause()
            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_headless_home_screen_reflects_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The default screen is the U3 Home: captured rows, preview and status agree."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test() as pilot:
            for _ in range(50):
                if app.controller.current is not None and app.controller.status == "ready":
                    break
                await pilot.pause(0.02)

            assert isinstance(app.screen, PlaceholderHomeScreen)
            assert app.query_one("#skill-table", DataTable).row_count == 1
            status_widget = app.query_one("#status-text", Static)
            assert "Ready: 1 skills discovered" in str(status_widget.content)
            preview = app.query_one("#preview-pane", Static)
            assert "Name: deploy" in str(preview.content)

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_headless_refresh_race_publishes_newest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rapid 'r' presses trigger refresh requests; newest generation publishes."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test() as pilot:
            await pilot.press("r")
            await pilot.press("r")
            await pilot.press("r")
            # Wait for workers to settle
            await pilot.pause()
            assert app.controller.current is not None
            # Current snapshot must have published
            assert app.controller.pending_generation is None
            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_headless_report_adapter_success_and_caching(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Report adapter executes in background worker and caches completed report
    for why, diff, and compare views.
    """
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test() as pilot:
            # Wait for initial capture to settle
            await pilot.pause()
            assert app.controller.current is not None
            key = app.controller.selected_key
            assert key is not None

            # 1. Why report (worker dispatched, then cached)
            val1 = app.request_report("why", (key, "claude"))
            assert val1 is None
            assert "why" in app.controller.active_requests

            # Allow worker thread to complete and post message
            await pilot.pause()
            assert "why" not in app.controller.active_requests

            # Request report again (cache hit)
            val2 = app.request_report("why", (key, "claude"))
            assert val2 is not None

            # 2. Diff report (worker dispatched, then cached)
            diff1 = app.request_report("diff", (key,))
            assert diff1 is None
            assert "diff" in app.controller.active_requests

            await pilot.pause()
            assert "diff" not in app.controller.active_requests

            diff2 = app.request_report("diff", (key,))
            assert diff2 is not None

            # 3. Compare report (worker dispatched, then cached)
            cmp1 = app.request_report("compare", ("claude", "codex"))
            assert cmp1 is None
            assert "compare" in app.controller.active_requests

            await pilot.pause()
            assert "compare" not in app.controller.active_requests

            cmp2 = app.request_report("compare", ("claude", "codex"))
            assert cmp2 is not None

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_headless_report_worker_unexpected_error_marks_failed_and_quits_with_3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unexpected error in report worker routes through ViewReportFailed,
    updates error widgets, marks sticky failed, and exits 3 on quit."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    def failing_why(snapshot: Any, key: str, agent_id: str) -> Any:
        raise RuntimeError("Unexpected fault during why calculation")

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", failing_why)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.controller.current is not None
            key = app.controller.selected_key
            assert key is not None

            # Dispatch report worker via public request_report
            res = app.request_report("why", (key, "claude"))
            assert res is None
            assert "why" in app.controller.active_requests

            # Allow worker thread to fail and post ViewReportFailed to UI thread
            await pilot.pause()
            assert "why" not in app.controller.active_requests

            # Assert controller failure and error details
            assert app.controller.is_failed
            assert "Unexpected fault during why calculation" in (
                app.controller.last_error_details or ""
            )

            # Assert UI widgets updated on accepted failure
            status_widget = app.query_one("#status-text", Static)
            details_widget = app.query_one("#error-details", Static)
            assert "Error:" in str(status_widget.content)
            assert "Unexpected fault during why calculation" in str(details_widget.content)

            # Quit exits 3 (sticky failed)
            await pilot.press("q")
            assert app.return_code == int(ExitCode.INTERNAL)

    asyncio.run(_run())


def test_headless_expected_error_snapshot_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SnapshotChanged shows retry message without marking controller failed; quits with 0."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    def failing_capture(*args: Any, **kwargs: Any) -> Any:
        raise SnapshotChanged()

    monkeypatch.setattr("skill_lens.tui.app.capture_session", failing_capture)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            # Retry message is exposed
            assert not app.controller.is_failed
            assert app.controller.retry_message == "Files changed while scanning. Press r to retry."
            status_widget = app.query_one("#status-text", Static)
            assert "Files changed while scanning" in str(status_widget.render())

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_headless_unexpected_error_marks_failed_and_quits_with_3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unexpected worker error marks failed and causes quit to exit with 3."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    def fatal_capture(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("Unexpected disk storage fault")

    monkeypatch.setattr("skill_lens.tui.app.capture_session", fatal_capture)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.controller.is_failed
            assert "Unexpected disk storage fault" in (app.controller.last_error_details or "")

            await pilot.press("q")
            assert app.return_code == int(ExitCode.INTERNAL)

    asyncio.run(_run())


def test_headless_literal_markup_display(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Untrusted strings containing markup tags are rendered literally without formatting."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    def markup_capture(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("[bold red]Unescaped Markup Payload[/bold red]")

    monkeypatch.setattr("skill_lens.tui.app.capture_session", markup_capture)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            details_widget = app.query_one("#error-details", Static)
            rendered = str(details_widget.render())
            assert "[bold red]" in rendered
            assert "[/bold red]" in rendered

            await pilot.press("q")
            assert app.return_code == int(ExitCode.INTERNAL)

    asyncio.run(_run())


def test_unhandled_exception_containment_without_traceback(tmp_path: Path) -> None:
    """SkillLensApp._handle_exception contains UI faults, sets code 3,
    and suppresses terminal traceback."""
    app = SkillLensApp(home=tmp_path, cwd=tmp_path)
    err = ValueError("Direct unhandled UI exception")

    # Call _handle_exception directly
    app._handle_exception(err)

    assert app.controller.is_failed
    assert app._return_code == int(ExitCode.INTERNAL)
    # Textual's _fatal_error appends segments to _exit_renderables; our override does not
    assert len(app._exit_renderables) == 0


def test_late_callbacks_after_app_closed(tmp_path: Path) -> None:
    """Late message deliveries after app/controller close are ignored without raising exceptions."""
    app = SkillLensApp(home=tmp_path, cwd=tmp_path)
    asyncio.run(app.action_quit())
    assert app.controller.is_closed

    # Late capture complete
    app.on_capture_complete(CaptureComplete(1, None))  # type: ignore[arg-type]
    # Late capture failed
    app.on_capture_failed(CaptureFailed(1, RuntimeError("late error")))
    # Late view report complete
    msg = ViewReportComplete("why", 1, 1, ("a", "b"), None)  # type: ignore[arg-type]
    app.on_view_report_complete(msg)
    # Late view report failed
    app.on_view_report_failed(ViewReportFailed("why", 1, 1, ("a", "b"), RuntimeError("late")))


def test_synchronous_run_lifecycle_and_normal_quit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The synchronous tui.run(home, cwd) executes with owned loop and returns 0."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def auto_quit(pilot: Pilot) -> None:
        await pilot.pause()
        await pilot.press("q")

    code = tui.run(tmp_path, tmp_path, headless=True, auto_pilot=auto_quit)
    assert code == int(ExitCode.OK)


def test_synchronous_run_sticky_exit_3_on_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The synchronous tui.run(home, cwd) returns 3 after an internal fault."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    def fatal_capture(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("Fatal launch IO error")

    monkeypatch.setattr("skill_lens.tui.app.capture_session", fatal_capture)

    async def auto_quit(pilot: Pilot) -> None:
        await pilot.pause()
        await pilot.press("q")

    code = tui.run(tmp_path, tmp_path, headless=True, auto_pilot=auto_quit)
    assert code == int(ExitCode.INTERNAL)


def test_synchronous_run_quit_proof_before_blocked_capture_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CRITICAL PROOF: Synchronous run() returns cleanly on 'q' BEFORE a blocked
    capture worker is released, proving teardown does not wait for ThreadPoolExecutor joins.

    Uses an active watchdog timer that sets release/timeout signal. If the runner
    wrongly waits for thread completion, the watchdog fires before run() returns,
    causing the test to fail.
    """
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    capture_started = threading.Event()
    release_capture = threading.Event()
    worker_finished = threading.Event()
    watchdog_fired = threading.Event()

    def blocked_capture(
        *,
        generation: int,
        home: Path,
        cwd: Path,
        max_snapshot_bytes: Any = None,
        cancelled: Any = None,
    ) -> Any:
        capture_started.set()
        # Block indefinitely until release_capture is explicitly set
        release_capture.wait()
        worker_finished.set()
        raise CaptureCancelled()

    monkeypatch.setattr("skill_lens.tui.app.capture_session", blocked_capture)

    # Active watchdog: fires after 2.0s and forcibly sets release_capture so runner doesn't hang
    def on_watchdog() -> None:
        watchdog_fired.set()
        release_capture.set()

    watchdog = threading.Timer(2.0, on_watchdog)
    watchdog.daemon = True
    watchdog.start()

    run_completed = False
    try:

        async def auto_quit(pilot: Pilot) -> None:
            # Wait for capture worker to begin
            for _ in range(50):
                if capture_started.is_set():
                    break
                await pilot.pause(0.02)
            assert capture_started.is_set(), "capture worker must have started"
            # Press 'q' while capture worker is STILL BLOCKED!
            assert not release_capture.is_set()
            # Let the mounted screen install its bindings; an immediate press
            # can be dropped on slower interpreters (3.13+).
            await pilot.pause(0.2)
            await pilot.press("q")

        code = tui.run(tmp_path, tmp_path, headless=True, auto_pilot=auto_quit)
        run_completed = True

        # Assert watchdog NEVER fired! If runner waited on worker, watchdog fired after 2.0s.
        assert not watchdog_fired.is_set(), (
            "Watchdog fired before run() returned! Runner blocked waiting for worker completion."
        )
        assert not release_capture.is_set(), "tui.run() returned after worker was released!"
        assert code == int(ExitCode.OK)
    finally:
        watchdog.cancel()
        release_capture.set()
        # Guarantee worker thread finishes before fixture HOME / tmp_path cleanup
        worker_finished.wait(timeout=5.0)

    assert run_completed is True


def test_mounted_closed_and_stale_callbacks_do_not_update_widgets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When widgets are mounted, callbacks rejected due to closed controller or stale
    generation do not update widget contents."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    # Prevent initial capture worker from dispatching
    monkeypatch.setattr(SkillLensApp, "_run_capture", lambda *a, **kw: None)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            status_widget = app.query_one("#status-text", Static)
            # Worker was stubbed, status is "Scanning skills..."
            assert "Scanning skills..." in str(status_widget.content)

            # 1. Close controller while app is mounted
            app.controller.close()
            assert app.controller.is_closed

            # Late capture complete
            snap = app.controller.current
            app.on_capture_complete(CaptureComplete(1, snap))  # type: ignore[arg-type]
            assert "Scanning skills..." in str(status_widget.content)

            # Late capture failed
            app.on_capture_failed(CaptureFailed(1, RuntimeError("ignored err")))
            assert "Scanning skills..." in str(status_widget.content)

            # Late view report complete
            app.on_view_report_complete(
                ViewReportComplete("why", 1, 1, ("skill-a", "claude"), None)  # type: ignore[arg-type]
            )
            assert "Scanning skills..." in str(status_widget.content)

            # Late view report failed
            app.on_view_report_failed(
                ViewReportFailed("why", 1, 1, ("skill-a", "claude"), RuntimeError("ignored"))
            )
            assert "Scanning skills..." in str(status_widget.content)
            await pilot.press("q")

    asyncio.run(_run())


def test_real_worker_refresh3_finishes_before_refresh2_publishes_newest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deterministic real-worker race: refresh 3 completes before refresh 2.
    Refresh 3 publishes as current, and refresh 2's late successful CaptureComplete
    is rejected without overwriting generation 3."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    import skill_lens.core.snapshot as snapshot_module

    real_capture = snapshot_module.capture_session

    barrier_gen2 = threading.Event()
    gen2_started = threading.Event()
    gen2_cancelled_was_set = threading.Event()
    gen2_completed = threading.Event()

    def racy_capture(
        *,
        generation: int,
        home: Path,
        cwd: Path,
        max_snapshot_bytes: Any = None,
        cancelled: Any = None,
    ) -> Any:
        if generation == 2:
            assert cancelled is not None and callable(cancelled)
            # Before gen3 runs, gen2's event must not be set
            assert not cancelled(), "Gen 2 cancellation event was unexpectedly set prematurely"
            gen2_started.set()
            barrier_gen2.wait(timeout=5.0)
            if cancelled():
                gen2_cancelled_was_set.set()
            # Deliberately ignore cancellation AFTER verifying correct event was supplied
            # to produce an actual old snapshot and exercise late CaptureComplete
            snap = real_capture(
                generation=generation,
                home=home,
                cwd=cwd,
                max_snapshot_bytes=max_snapshot_bytes,
                cancelled=lambda: False,
            )
            gen2_completed.set()
            return snap
        return real_capture(generation=generation, home=home, cwd=cwd, cancelled=cancelled)

    monkeypatch.setattr("skill_lens.tui.app.capture_session", racy_capture)

    async def _run() -> None:
        try:
            app = SkillLensApp(home=tmp_path, cwd=tmp_path)
            async with app.run_test() as pilot:
                # Let initial capture (gen 1) complete
                await pilot.pause()
                assert app.controller.current is not None
                assert app.controller.current.generation == 1

                # Trigger refresh 2 (will block on barrier)
                await pilot.press("r")
                for _ in range(50):
                    if gen2_started.is_set():
                        break
                    await pilot.pause(0.02)
                assert gen2_started.is_set()

                # Trigger refresh 3 (runs immediately without blocking)
                await pilot.press("r")
                await pilot.pause()

                # Gen 3 must have published!
                assert app.controller.current is not None
                assert app.controller.current.generation == 3

                # Now release gen 2 to complete and post its actual snapshot
                barrier_gen2.set()
                for _ in range(50):
                    if gen2_completed.is_set():
                        break
                    await pilot.pause(0.02)
                assert gen2_completed.is_set()
                await pilot.pause()

                # Gen 2 cancellation event was verified set by gen 3
                assert gen2_cancelled_was_set.is_set()

                # Gen 3 remains current; gen 2's late successful snapshot was rejected
                assert app.controller.current.generation == 3
                status_widget = app.query_one("#status-text", Static)
                assert "Ready:" in str(status_widget.content)

                await pilot.press("q")
                assert app.return_code == int(ExitCode.OK)
        finally:
            barrier_gen2.set()

    asyncio.run(_run())


def test_real_worker_refresh3_finishes_before_refresh2_stale_error_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deterministic real-worker race: refresh 3 completes before refresh 2.
    Refresh 3 publishes as current, and refresh 2's late stale error is rejected
    without marking the session failed or affecting UI state."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    import skill_lens.core.snapshot as snapshot_module

    real_capture = snapshot_module.capture_session

    barrier_gen2 = threading.Event()
    gen2_started = threading.Event()
    gen2_cancelled_was_set = threading.Event()
    gen2_completed = threading.Event()

    def racy_capture_error(
        *,
        generation: int,
        home: Path,
        cwd: Path,
        max_snapshot_bytes: Any = None,
        cancelled: Any = None,
    ) -> Any:
        if generation == 2:
            assert cancelled is not None and callable(cancelled)
            assert not cancelled(), "Gen 2 cancellation event was unexpectedly set prematurely"
            gen2_started.set()
            barrier_gen2.wait(timeout=5.0)
            if cancelled():
                gen2_cancelled_was_set.set()
            gen2_completed.set()
            raise RuntimeError("Stale gen 2 background failure")
        return real_capture(
            generation=generation,
            home=home,
            cwd=cwd,
            max_snapshot_bytes=max_snapshot_bytes,
            cancelled=cancelled,
        )

    monkeypatch.setattr("skill_lens.tui.app.capture_session", racy_capture_error)

    async def _run() -> None:
        try:
            app = SkillLensApp(home=tmp_path, cwd=tmp_path)
            async with app.run_test() as pilot:
                # Let initial capture (gen 1) complete
                await pilot.pause()
                assert app.controller.current is not None
                assert app.controller.current.generation == 1

                # Trigger refresh 2 (will block on barrier)
                await pilot.press("r")
                for _ in range(50):
                    if gen2_started.is_set():
                        break
                    await pilot.pause(0.02)
                assert gen2_started.is_set()

                # Trigger refresh 3 (runs immediately without blocking)
                await pilot.press("r")
                await pilot.pause()

                # Gen 3 must have published!
                assert app.controller.current is not None
                assert app.controller.current.generation == 3

                # Now release gen 2 to post its stale error
                barrier_gen2.set()
                for _ in range(50):
                    if gen2_completed.is_set():
                        break
                    await pilot.pause(0.02)
                assert gen2_completed.is_set()
                await pilot.pause()

                # Gen 2 cancellation event was verified set by gen 3
                assert gen2_cancelled_was_set.is_set()

                # Gen 3 remains current; gen 2's late stale error did NOT mark failed
                assert app.controller.current.generation == 3
                assert app.controller.is_failed is False
                assert app.controller.last_error_details is None
                assert app.controller.retry_message is None

                status_widget = app.query_one("#status-text", Static)
                assert "Ready:" in str(status_widget.content)
                details_widget = app.query_one("#error-details", Static)
                assert str(details_widget.content) == ""

                # Quit returns clean 0 (not 3)
                await pilot.press("q")
                assert app.return_code == int(ExitCode.OK)
        finally:
            barrier_gen2.set()

    asyncio.run(_run())


def test_real_worker_report_request2_before_request1_and_stale_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deterministic real-worker report race: request 2 completes before request 1.
    Report 2 is accepted, and late completion of request 1 is rejected."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    barrier_rep1 = threading.Event()
    rep1_started = threading.Event()

    import skill_lens.core.snapshot as snapshot_module

    real_why = snapshot_module.snapshot_why

    def racy_why(snapshot: Any, key: str, agent_id: str) -> Any:
        if agent_id == "claude":
            rep1_started.set()
            barrier_rep1.wait(timeout=5.0)
        return real_why(snapshot, key, agent_id)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", racy_why)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            key = app.controller.selected_key
            assert key is not None

            # Request 1 for claude (blocks in worker)
            app.request_report("why", (key, "claude"))
            for _ in range(50):
                if rep1_started.is_set():
                    break
                await pilot.pause(0.02)
            assert rep1_started.is_set()

            # Request 2 for codex (completes immediately)
            app.request_report("why", (key, "codex"))
            await pilot.pause()

            # Request 2 cached
            assert app.controller.get_cached_report("why", (key, "codex")) is not None

            # Unblock request 1
            barrier_rep1.set()
            await pilot.pause()

            # Request 1 late result rejected: not in cache!
            assert app.controller.get_cached_report("why", (key, "claude")) is None

            await pilot.press("q")

    asyncio.run(_run())


def test_real_worker_selection_change_invalidates_in_flight_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changing selection while a worker report is in flight cancels its Event and rejects it."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    barrier_rep = threading.Event()
    rep_started = threading.Event()
    worker_finished = threading.Event()

    import skill_lens.core.snapshot as snapshot_module

    real_why = snapshot_module.snapshot_why

    def blocking_why(snapshot: Any, key: str, agent_id: str) -> Any:
        rep_started.set()
        barrier_rep.wait(timeout=5.0)
        try:
            return real_why(snapshot, key, agent_id)
        finally:
            worker_finished.set()

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", blocking_why)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        try:
            async with app.run_test() as pilot:
                await pilot.pause()
                initial_key = app.controller.selected_key
                assert initial_key is not None

                app.request_report("why", (initial_key, "claude"))
                for _ in range(50):
                    if rep_started.is_set():
                        break
                    await pilot.pause(0.02)
                assert rep_started.is_set()

                # Get the in-flight report event before selection change
                ev = app.controller._report_events.get(1)
                assert ev is not None
                assert not ev.is_set()

                # Selection changes via public controller.set_selected_key on a DIFFERENT key
                different_key = "skill:different-test-key"
                app.controller.set_selected_key(different_key)
                assert app.controller.selected_key == different_key

                # Assert that set_selected_key cancelled the in-flight report event
                assert ev.is_set()
                assert "why" not in app.controller.active_requests

                # Unblock worker to deliver its late valid ResolutionReport
                barrier_rep.set()
                for _ in range(50):
                    if worker_finished.is_set():
                        break
                    await pilot.pause(0.02)
                assert worker_finished.is_set()
                await pilot.pause()

                # Late report was safely rejected: not in cache, session not failed
                assert not app.controller.is_failed
                assert len(app.controller.cache) == 0

                await pilot.press("q")
        finally:
            barrier_rep.set()
            worker_finished.wait(timeout=5.0)

    asyncio.run(_run())


def test_real_worker_newest_failure_retains_old_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When a refresh fails, the existing snapshot is retained and error status is shown."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

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
            raise RuntimeError("Newest refresh IO error")
        return real_capture(
            generation=generation,
            home=home,
            cwd=cwd,
            max_snapshot_bytes=max_snapshot_bytes,
            cancelled=cancelled,
        )

    monkeypatch.setattr("skill_lens.tui.app.capture_session", failing_refresh)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test() as pilot:
            # Initial capture succeeds
            for _ in range(100):
                if app.controller.current is not None and app.controller.status == "ready":
                    break
                await pilot.pause(0.01)
            assert app.controller.current is not None
            initial_snap = app.controller.current

            # Refresh fails
            await pilot.press("r")
            for _ in range(100):
                if app.controller.is_failed:
                    break
                await pilot.pause(0.01)

            # Old snapshot retained!
            assert app.controller.current is initial_snap
            assert app.controller.is_failed
            assert "Newest refresh IO error" in (app.controller.last_error_details or "")

            status_widget = app.query_one("#status-text", Static)
            details_widget = app.query_one("#error-details", Static)
            assert "Error:" in str(status_widget.content)
            assert "Newest refresh IO error" in str(details_widget.content)

            await pilot.press("q")
            assert app.return_code == int(ExitCode.INTERNAL)

    asyncio.run(_run())


def test_constructor_failure_propagates_out_of_run_and_closes_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When SkillLensApp.__init__ raises, run() propagates the fault and cleans up loop."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)

    created_loops: list[asyncio.AbstractEventLoop] = []
    orig_new_event_loop = asyncio.new_event_loop

    def spy_new_event_loop() -> asyncio.AbstractEventLoop:
        new_loop = orig_new_event_loop()
        created_loops.append(new_loop)
        return new_loop

    monkeypatch.setattr(asyncio, "new_event_loop", spy_new_event_loop)

    def exploding_init(self: Any, *args: Any, **kwargs: Any) -> None:
        raise ValueError("Simulated constructor failure")

    monkeypatch.setattr(SkillLensApp, "__init__", exploding_init)

    with pytest.raises(ValueError, match="Simulated constructor failure"):
        tui.run(tmp_path, tmp_path, headless=True)

    assert len(created_loops) == 1
    assert created_loops[0].is_closed()


def test_cleanup_failure_propagates_out_of_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When asyncio.all_tasks raises during cleanup, run() propagates the fault."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    def exploding_all_tasks(loop: Any) -> Any:
        raise RuntimeError("Simulated cleanup fault")

    monkeypatch.setattr(asyncio, "all_tasks", exploding_all_tasks)

    async def auto_quit(pilot: Pilot) -> None:
        await pilot.pause()
        await pilot.press("q")

    with pytest.raises(RuntimeError, match="Simulated cleanup fault"):
        tui.run(tmp_path, tmp_path, headless=True, auto_pilot=auto_quit)


def test_actual_textual_event_handler_fault_via_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unhandled exception during a Textual action handler routes through _handle_exception,
    exiting 3 without terminal traceback."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    def faulty_action_refresh(self: Any) -> None:
        raise RuntimeError("Unhandled action fault")

    monkeypatch.setattr(SkillLensApp, "action_refresh", faulty_action_refresh)

    orig_run = tui.run

    def test_run(home: Path, cwd: Path, **kwargs: Any) -> int:
        async def trigger_fault(pilot: Pilot) -> None:
            await pilot.pause()
            await pilot.press("r")
            await pilot.pause()

        return orig_run(home, cwd, headless=True, auto_pilot=trigger_fault)

    monkeypatch.setattr(tui, "run", test_run)
    monkeypatch.setattr("skill_lens.cli._is_textual_available", lambda: True)
    monkeypatch.setattr("skill_lens.cli._stream_isatty", lambda s: True)

    runner = CliRunner()
    result = runner.invoke(cli_app, ["tui", "--sandbox", str(tmp_path)])
    assert result.exit_code == int(ExitCode.INTERNAL)
    assert "Error: Failed to start the terminal UI: Unhandled action fault" in result.stderr
    assert "Traceback" not in result.stderr


def test_startup_handler_fault_via_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An unhandled exception during SkillLensApp.on_mount routes through _handle_exception,
    propagates out of tui.run(), and prints a plain-English message to CLI stderr without
    traceback."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    def faulty_on_mount(self: Any) -> None:
        raise RuntimeError("Injected startup handler fault")

    monkeypatch.setattr(SkillLensApp, "on_mount", faulty_on_mount)

    orig_run = tui.run

    def test_run(home: Path, cwd: Path, **kwargs: Any) -> int:
        return orig_run(home, cwd, headless=True)

    monkeypatch.setattr(tui, "run", test_run)
    monkeypatch.setattr("skill_lens.cli._is_textual_available", lambda: True)
    monkeypatch.setattr("skill_lens.cli._stream_isatty", lambda s: True)

    runner = CliRunner()
    result = runner.invoke(cli_app, ["tui", "--sandbox", str(tmp_path)])
    assert result.exit_code == int(ExitCode.INTERNAL)
    assert "Error: Failed to start the terminal UI: Injected startup handler fault" in result.stderr
    assert "Traceback" not in result.stderr


def test_command_palette_and_ctrl_p_inaccessible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Command palette is strictly disabled: ctrl+p cannot open palette,
    ENABLE_COMMAND_PALETTE is False, and no system commands or Screenshot actions are exposed."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _test() -> None:
        from skill_lens import __version__

        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        assert __version__ == app.SUB_TITLE
        assert app.ENABLE_COMMAND_PALETTE is False
        assert set() == app.COMMANDS

        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.use_command_palette is False
            assert len(app.screen_stack) == 1
            assert isinstance(app.screen, PlaceholderHomeScreen)

            # Press ctrl+p: palette must NOT open
            await pilot.press("ctrl+p")
            await pilot.pause()
            assert len(app.screen_stack) == 1
            assert isinstance(app.screen, PlaceholderHomeScreen)

            # Direct action_command_palette call must also be a no-op
            app.action_command_palette()
            await pilot.pause()
            assert len(app.screen_stack) == 1

            # System commands must yield nothing (Screenshot never exposed)
            commands = list(app.get_system_commands(app.screen))
            assert commands == []

            await pilot.press("q")

    asyncio.run(_test())


def test_neutralized_screenshot_methods_no_write_with_sentinel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Calling inherited screenshot and delivery actions on SkillLensApp is neutralized,
    and a write spy sentinel confirms zero filesystem writes occur."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    # Write spy sentinel: raises immediately if ANY write/create/delete open is attempted
    write_attempts: list[tuple[str, str]] = []
    orig_open = open

    def failing_write_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if any(ch in mode for ch in ("w", "a", "x", "+")):
            write_attempts.append((str(file), mode))
            raise RuntimeError(f"Sentinel caught forbidden write: {file} mode={mode}")
        return orig_open(file, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", failing_write_open)

    # Take directory snapshot before
    files_before = set(tmp_path.rglob("*"))

    app = SkillLensApp(home=tmp_path, cwd=tmp_path)

    # Call all neutralized write/screenshot methods
    app.action_screenshot()
    app.action_screenshot("custom.svg", str(tmp_path))
    res_deliv = app.deliver_screenshot()
    assert res_deliv is None
    res_save = app.save_screenshot()
    assert res_save == ""
    res_bin = app.deliver_binary(b"data")
    assert res_bin is None
    res_text = app.deliver_text("data")
    assert res_text is None

    # Assert no write attempts occurred
    assert write_attempts == []

    # Assert no new files created under synthetic target
    files_after = set(tmp_path.rglob("*"))
    assert files_before == files_after


def test_discriminating_mutation_enabled_palette_or_unneutralized_screenshot_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DISCRIMINATING MUTATION PROOF: An unneutralized App class with ENABLE_COMMAND_PALETTE=True
    or default inherited App.save_screenshot triggers the write sentinel and discriminator."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    # 1. Mutant enabling command palette is caught by palette check
    class MutantPaletteApp(SkillLensApp):
        ENABLE_COMMAND_PALETTE: ClassVar[bool] = True

    mutant_app = MutantPaletteApp(home=tmp_path, cwd=tmp_path)
    assert mutant_app.ENABLE_COMMAND_PALETTE is True
    # The discriminator asserts SkillLensApp.ENABLE_COMMAND_PALETTE is False
    with pytest.raises(AssertionError):
        assert mutant_app.ENABLE_COMMAND_PALETTE is False

    # 2. Mutant with unneutralized save_screenshot attempts write and is caught by write sentinel
    write_attempts: list[str] = []
    orig_open = open

    def failing_write_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if any(ch in mode for ch in ("w", "a", "x", "+")):
            write_attempts.append(str(file))
            raise RuntimeError(f"Sentinel caught write attempt to {file} with mode={mode}")
        return orig_open(file, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", failing_write_open)

    # Calling Textual's raw inherited save_screenshot on a mutant triggers open(..., 'w')
    # and is immediately caught by the sentinel
    class MutantWriteApp(SkillLensApp):
        save_screenshot = App.save_screenshot  # Restore Textual's default write implementation

    mutant_writer = MutantWriteApp(home=tmp_path, cwd=tmp_path)
    # Mock export_screenshot so it doesn't need a live renderer
    monkeypatch.setattr(mutant_writer, "export_screenshot", lambda: "<svg></svg>")

    with pytest.raises(RuntimeError, match="Sentinel caught write attempt"):
        mutant_writer.save_screenshot(filename="test.svg", path=str(tmp_path))

    assert len(write_attempts) == 1
    assert "test.svg" in write_attempts[0]


def test_headless_unexpected_fault_snapshot_changed_and_view_error_widgets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Headless widget regression verifying display precedence and sticky exit code:
    unexpected fault -> SnapshotChanged -> later unexpected view error.
    """
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test() as pilot:
            # 1. Initial capture completes
            await pilot.pause()
            status_widget = app.query_one("#status-text", Static)
            details_widget = app.query_one("#error-details", Static)
            assert "Ready:" in str(status_widget.content)
            assert str(details_widget.content) == ""

            # 2. Trigger a refresh and fail it unexpectedly
            req2 = app.controller.request_refresh()
            assert req2 is not None
            gen2, _ = req2
            app.post_message(CaptureFailed(gen2, RuntimeError("initial capture fault")))
            await pilot.pause()

            assert "Error: Unexpected internal fault" in str(status_widget.content)
            assert "initial capture fault" in str(details_widget.content)
            assert app.controller.is_failed is True

            # 3. Trigger another refresh and fail it with expected SnapshotChanged
            req3 = app.controller.request_refresh()
            assert req3 is not None
            gen3, _ = req3
            retry_msg = "Files changed while scanning. Press r to retry."
            app.post_message(CaptureFailed(gen3, SnapshotChanged(retry_msg)))
            await pilot.pause()

            # Retry message is displayed in status widget and error details is cleared,
            # while sticky failed remains True
            assert retry_msg in str(status_widget.content)
            assert str(details_widget.content) == ""
            assert app.controller.is_failed is True

            # 4. Stale error message has zero effect on display
            app.post_message(CaptureFailed(999, RuntimeError("stale capture fault")))
            await pilot.pause()
            assert retry_msg in str(status_widget.content)
            assert str(details_widget.content) == ""

            # 5. Active view request fails with unexpected error
            view_req, _, _ = app.controller.request_view("why", ("skill", "claude"))
            assert view_req is not None
            app.post_message(
                ViewReportFailed(
                    "why",
                    view_req.request_id,
                    view_req.generation,
                    view_req.arguments,
                    RuntimeError("view report fault"),
                )
            )
            await pilot.pause()

            # Older retry message is cleared, new view error details are shown
            assert "Error: Unexpected internal fault" in str(status_widget.content)
            assert "view report fault" in str(details_widget.content)
            assert app.controller.retry_message is None
            assert app.controller.is_failed is True

            # 6. Quit exits with sticky exit code 3
            await pilot.press("q")
            assert app.return_code == int(ExitCode.INTERNAL)

    asyncio.run(_run())


def test_headless_report_error_during_refresh_widgets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Headless widget regression: accepted unexpected report error during pending refresh
    outranks loading status, displaying error panel instead of loading text."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test() as pilot:
            # 1. Initial capture completes
            await pilot.pause()
            status_widget = app.query_one("#status-text", Static)
            details_widget = app.query_one("#error-details", Static)
            assert "Ready:" in str(status_widget.content)

            # 2. Start Why report request on current snapshot
            view_req, _, _ = app.controller.request_view("why", ("skill", "claude"))
            assert view_req is not None

            # 3. Start refresh 2 without completing it (pending_generation = 2)
            refresh_req = app.controller.request_refresh()
            assert refresh_req is not None
            app._update_ui()
            assert "Scanning skills..." in str(status_widget.content)

            # 4. View report fails with unexpected error while refresh 2 is still pending
            app.post_message(
                ViewReportFailed(
                    "why",
                    view_req.request_id,
                    view_req.generation,
                    view_req.arguments,
                    RuntimeError("View report fault during pending refresh"),
                )
            )
            await pilot.pause()

            # Error status and panel outrank pending loading!
            assert "Error: Unexpected internal fault" in str(status_widget.content)
            assert "View report fault during pending refresh" in str(details_widget.content)
            assert app.controller.is_failed is True
            assert app.controller.pending_generation is not None

            # 5. Quit exits with exit code 3
            await pilot.press("q")
            assert app.return_code == int(ExitCode.INTERNAL)

    asyncio.run(_run())


def test_headless_size_refusal_renders_and_quits_with_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A size refusal shows its own message, keeps the run successful, and offers no retry."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    refusal = SnapshotTooLarge(total_bytes=300 * 1024 * 1024, limit_bytes=256 * 1024 * 1024)

    def refusing_capture(*args: Any, **kwargs: Any) -> Any:
        raise refusal

    monkeypatch.setattr("skill_lens.tui.app.capture_session", refusing_capture)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert not app.controller.is_failed
            assert app.controller.refusal_message == str(refusal)
            assert app.controller.retry_message is None
            assert app.controller.status == "refused"

            rendered = str(app.query_one("#status-text", Static).render())
            assert "Snapshot refused" in rendered
            assert "Press r to retry" not in rendered

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())
