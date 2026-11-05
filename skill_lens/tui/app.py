"""Skill Lens Textual Application and Home integration (Assignments U2-U3).

Specification reference: FULL_SCREEN_TUI.md §9.1, §10, Step 2-3, §21.7 and §22.
Provides:
- SkillLensApp(App[int]) with the U3 Home screen and q/r bindings
- Textual thread workers with exit_on_error=False passing explicit home/cwd/event
- Report adapter for Why, Diff, and Compare using snapshot services
- Thread-safe message marshalling to UI thread
- Containment of unhandled UI/worker exceptions via App._handle_exception
- Clean normal quit (0) or sticky fault quit (3) without terminal tracebacks
"""

from __future__ import annotations

import contextlib
import threading
from collections.abc import Iterable
from pathlib import Path
from typing import Any, ClassVar

from textual import work
from textual.app import App, ScreenStackError, UnknownModeError
from textual.binding import Binding, BindingType
from textual.css.query import NoMatches
from textual.message import Message
from textual.screen import Screen
from textual.widgets import DataTable, Static

from skill_lens import __version__
from skill_lens.core.cancellation import CaptureCancelled
from skill_lens.core.exitcodes import ExitCode
from skill_lens.core.snapshot import (
    DEFAULT_MAX_SNAPSHOT_BYTES,
    capture_session,
    snapshot_compare,
    snapshot_diff,
    snapshot_why,
)
from skill_lens.core.snapshot_models import SessionSnapshot
from skill_lens.tui._textual_compat import record_unhandled_fault
from skill_lens.tui.agents import AgentsScreen
from skill_lens.tui.compare import CompareScreen
from skill_lens.tui.diff import DiffScreen
from skill_lens.tui.doctor import DoctorScreen
from skill_lens.tui.help import HelpScreen
from skill_lens.tui.home import HomeScreen
from skill_lens.tui.session import (
    ReportValue,
    SessionController,
    ViewName,
)
from skill_lens.tui.why import WhyScreen


class CaptureComplete(Message):
    """Fired on worker completion when session capture succeeds."""

    def __init__(self, generation: int, snapshot: SessionSnapshot) -> None:
        super().__init__()
        self.generation = generation
        self.snapshot = snapshot


class CaptureFailed(Message):
    """Fired on worker completion when session capture raises an exception."""

    def __init__(self, generation: int, error: Exception) -> None:
        super().__init__()
        self.generation = generation
        self.error = error


class ViewReportComplete(Message):
    """Fired on worker completion when a view report succeeds."""

    def __init__(
        self,
        view: ViewName,
        request_id: int,
        generation: int,
        arguments: tuple[str, ...],
        report: ReportValue,
    ) -> None:
        super().__init__()
        self.view = view
        self.request_id = request_id
        self.generation = generation
        self.arguments = arguments
        self.report = report


class ViewReportFailed(Message):
    """Fired on worker completion when a view report raises an exception."""

    def __init__(
        self,
        view: ViewName,
        request_id: int,
        generation: int,
        arguments: tuple[str, ...],
        error: Exception,
    ) -> None:
        super().__init__()
        self.view = view
        self.request_id = request_id
        self.generation = generation
        self.arguments = arguments
        self.error = error


class PlaceholderHomeScreen(HomeScreen):
    """Compatibility alias for the former U2 placeholder screen.

    U3 replaced the placeholder with the real Home screen.  Keeping this name
    as a subclass preserves existing ``isinstance`` checks without a second,
    divergent screen implementation.
    """


class SkillLensApp(App[int]):
    """Skill Lens full-screen interactive browsing application."""

    TITLE = "Skill Lens"
    SUB_TITLE = __version__
    ENABLE_COMMAND_PALETTE: ClassVar[bool] = False
    COMMANDS: ClassVar[set[Any]] = set()

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("question_mark", "open_help", "Help", show=False),
        Binding("f1", "toggle_help", "Help", show=True, priority=True),
        Binding("ctrl+c", "quit", "Quit", show=False, priority=True),
    ]

    def action_command_palette(self) -> None:
        """Neutralize command palette action to enforce strict read-only execution."""
        return

    def get_system_commands(self, screen: Screen[Any]) -> Iterable[Any]:
        """Neutralize system command discovery to ensure no write commands are exposed."""
        return ()

    def action_screenshot(self, filename: str | None = None, path: str | None = None) -> None:
        """Neutralize screenshot action to enforce strict read-only execution."""
        return

    def deliver_screenshot(
        self,
        filename: str | None = None,
        path: str | None = None,
        time_format: str | None = None,
    ) -> str | None:
        """Neutralize screenshot delivery to enforce strict read-only execution."""
        return None

    def save_screenshot(
        self,
        filename: str | None = None,
        path: str | None = None,
        time_format: str | None = None,
    ) -> str:
        """Neutralize screenshot saving to enforce strict read-only execution."""
        return ""

    def deliver_binary(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str | None:
        """Neutralize binary delivery to enforce strict read-only execution."""
        return None

    def deliver_text(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str | None:
        """Neutralize text delivery to enforce strict read-only execution."""
        return None

    def __init__(
        self,
        home: Path,
        cwd: Path,
        controller: SessionController | None = None,
        max_snapshot_bytes: int | None = DEFAULT_MAX_SNAPSHOT_BYTES,
    ) -> None:
        super().__init__()
        self._home = home
        self._cwd = cwd
        self._max_snapshot_bytes = max_snapshot_bytes
        self.controller: SessionController = (
            controller if controller is not None else SessionController()
        )
        self._help_origin: Screen[None] | None = None

    def get_default_screen(self) -> Screen[None]:
        """Return the Home screen as the default root screen."""
        return PlaceholderHomeScreen()

    def on_mount(self) -> None:
        self.action_refresh()

    async def action_quit(self) -> None:
        """Close controller, cancel owned workers, and exit with status code."""
        code = self.controller.close()
        self.workers.cancel_all()
        self.exit(code, return_code=code)

    def action_refresh(self) -> None:
        """Request a session refresh and dispatch background worker."""
        if isinstance(self.screen, HomeScreen):
            self.screen._clear_removal_notice()
        req = self.controller.request_refresh()
        if req is not None:
            gen, event = req
            self._update_ui()
            self._run_capture(gen, self._home, self._cwd, event)

    # -- Help overlay -------------------------------------------------------

    def action_open_help(self) -> None:
        """Non-priority ? opens Help over a supported browsing screen."""
        self.open_help()

    def action_toggle_help(self) -> None:
        """App-level priority F1 opens Help, or closes the exact active Help."""
        if isinstance(self.screen, HelpScreen):
            self.close_help(self.screen)
        else:
            self.open_help()

    def open_help(self) -> None:
        """Open one Help modal over the current supported browsing screen.

        Repeated opens cannot stack: the active Help is returned unchanged. The
        origin is suspended first so covered report work cannot keep running or
        receive callbacks; opening Help itself starts no work.
        """
        if isinstance(self.screen, HelpScreen):
            return
        origin = self.screen
        if not isinstance(
            origin,
            (HomeScreen, WhyScreen, DiffScreen, AgentsScreen, CompareScreen, DoctorScreen),
        ):
            return
        context = origin.help_context()
        origin.suspend_help()
        help_screen = HelpScreen(context, self.controller)
        self._help_origin = origin
        self.push_screen(help_screen)

    def close_help(self, expected: HelpScreen) -> None:
        """Close only the expected Help, reconcile the origin, then restore focus."""
        if self.screen is not expected:
            return
        tracked = self._help_origin
        self._help_origin = None
        prev_screen = self.screen_stack[-2] if len(self.screen_stack) >= 2 else None
        origin = tracked if tracked is prev_screen else prev_screen
        self.pop_screen()
        if origin is not None and origin.is_mounted and hasattr(origin, "resume_help"):
            origin.resume_help()
        self._update_ui()

    def open_why(self, key: str, agent_id: str | None) -> None:
        """Open a Why screen for the given installation key and agent."""
        if isinstance(self.screen, WhyScreen):
            return
        home = self.screen if isinstance(self.screen, HomeScreen) else None
        if home is not None:
            home.suspend_why()
        why = WhyScreen(key, agent_id)
        self.push_screen(why)

    def close_why(self, removal_notice: str | None = None) -> None:
        """Close the Why screen and return to Home."""
        if not isinstance(self.screen, WhyScreen):
            return
        why = self.screen
        why._cancel_owned_token()
        prev_screen = self.screen_stack[-2] if len(self.screen_stack) >= 2 else None
        self.pop_screen()
        if isinstance(prev_screen, HomeScreen):
            if removal_notice is not None:
                prev_screen.set_removal_notice(removal_notice)
            prev_screen.resume_why()
            self._update_ui()

    def open_diff(self, key: str) -> None:
        """Open the Diff screen for one canonical installation key.

        Exactly one Diff is ever pushed: asking again while a Diff is active is a
        no-op, so repeated ``d`` presses cannot stack duplicates. The origin is
        suspended first so a covered screen cannot keep requesting reports.
        """
        if isinstance(self.screen, DiffScreen):
            return
        origin = self.screen
        if isinstance(origin, HomeScreen):
            origin.suspend_why()
        elif isinstance(origin, WhyScreen):
            origin.suspend_detail()
        else:
            return
        self.push_screen(DiffScreen(key))

    def close_diff(self, removal_notice: str | None = None) -> None:
        """Close the Diff screen and reconcile the screen it revealed.

        The revealed screen stays the only screen allowed to act on its own
        missing key: Home receives the removal notice this screen captured, and a
        revealed Why re-derives itself and closes with its own notice.
        """
        if not isinstance(self.screen, DiffScreen):
            return
        diff = self.screen
        diff._cancel_owned_token()
        prev_screen = self.screen_stack[-2] if len(self.screen_stack) >= 2 else None
        self.pop_screen()
        if isinstance(prev_screen, HomeScreen):
            if removal_notice is not None:
                prev_screen.set_removal_notice(removal_notice)
            prev_screen.resume_why()
            self._update_ui()
        elif isinstance(prev_screen, WhyScreen):
            prev_screen.resume_detail()
            self._update_ui()

    def open_agents(self) -> None:
        """Open the captured registry browser from Home only."""
        if isinstance(self.screen, AgentsScreen):
            return
        home = self.screen if isinstance(self.screen, HomeScreen) else None
        if home is None:
            return
        home.suspend_why()
        self.push_screen(AgentsScreen())

    def close_agents(self, expected: AgentsScreen) -> None:
        """Close only the expected Agents instance, then resume its Home origin."""
        if self.screen is not expected:
            return
        prev_screen = self.screen_stack[-2] if len(self.screen_stack) >= 2 else None
        self.pop_screen()
        if isinstance(prev_screen, HomeScreen):
            prev_screen.resume_why()
            self._update_ui()

    def open_compare(self) -> None:
        """Open the pair picker from Home only."""
        if isinstance(self.screen, CompareScreen):
            return
        home = self.screen if isinstance(self.screen, HomeScreen) else None
        if home is None:
            return
        home.suspend_why()
        self.push_screen(CompareScreen())

    def open_doctor(self) -> None:
        """Open one Doctor screen from the focused, ordinary Home table."""
        if isinstance(self.screen, DoctorScreen):
            return
        home = self.screen if isinstance(self.screen, HomeScreen) else None
        if home is None or home._suspended or home.json_mode:
            return
        try:
            table = home.query_one("#skill-table", DataTable)
        except NoMatches:
            return
        if not table.has_focus:
            return
        home.suspend_why()
        self.push_screen(DoctorScreen())

    def close_doctor(self, expected: DoctorScreen) -> None:
        """Close only the expected Doctor instance and resume its Home origin."""
        if self.screen is not expected:
            return
        prev_screen = self.screen_stack[-2] if len(self.screen_stack) >= 2 else None
        self.pop_screen()
        if isinstance(prev_screen, HomeScreen):
            prev_screen.resume_why()
            self._update_ui()

    def jump_from_doctor(self, expected: DoctorScreen, generation: int, key: str) -> bool:
        """Validate a displayed Doctor row before queuing Home's selection."""
        prev_screen = self.screen_stack[-2] if len(self.screen_stack) >= 2 else None
        if self.screen is not expected or not isinstance(prev_screen, HomeScreen):
            return False
        snapshot = self.controller.current
        if (
            snapshot is None
            or snapshot.generation != generation
            or not expected.current_jump_matches(generation, key)
        ):
            expected.note_stale_jump()
            return False
        if not prev_screen.prepare_doctor_jump(generation, key):
            expected.set_navigation_notice(
                "Home could not accept this selection. Review the finding and try again."
            )
            return False

        # Home owns the queued handoff before pop: Textual's ScreenResume and
        # this explicit callback both pass through the same idempotent consumer.
        self.pop_screen()
        prev_screen.resume_why()
        self._update_ui()
        return True

    def close_compare(self, expected: CompareScreen) -> None:
        """Close only the expected Compare instance and resume Home."""
        if self.screen is not expected:
            return
        expected._cancel_owned_token()
        prev_screen = self.screen_stack[-2] if len(self.screen_stack) >= 2 else None
        self.pop_screen()
        if isinstance(prev_screen, HomeScreen):
            prev_screen.resume_why()
            self._update_ui()

    def request_report(self, view: ViewName, arguments: tuple[str, ...]) -> ReportValue | None:
        """Adapter method for Why/Diff/Compare report computation.

        Returns cached ReportValue immediately on cache hit.
        Dispatches background thread worker on cache miss and returns None.
        """
        req, event, cached = self.controller.request_view(view, arguments)
        if cached is not None:
            return cached
        if req is not None and event is not None and self.controller.current is not None:
            self._run_report(
                view,
                req.request_id,
                req.generation,
                arguments,
                self.controller.current,
                event,
            )
        return None

    @work(thread=True, exit_on_error=False)
    def _run_capture(self, generation: int, home: Path, cwd: Path, event: threading.Event) -> None:
        """Background thread worker for session capture."""
        try:
            snapshot = capture_session(
                generation=generation,
                home=home,
                cwd=cwd,
                max_snapshot_bytes=self._max_snapshot_bytes,
                cancelled=event.is_set,
            )
        except Exception as exc:
            with contextlib.suppress(RuntimeError, Exception):
                self.post_message(CaptureFailed(generation, exc))
            return
        with contextlib.suppress(RuntimeError, Exception):
            self.post_message(CaptureComplete(generation, snapshot))

    @work(thread=True, exit_on_error=False)
    def _run_report(
        self,
        view: ViewName,
        request_id: int,
        generation: int,
        arguments: tuple[str, ...],
        snapshot: SessionSnapshot,
        event: threading.Event,
    ) -> None:
        """Background thread worker for Why/Diff/Compare reports."""
        try:
            if event.is_set():
                raise CaptureCancelled()
            if view == "why":
                if len(arguments) != 2:
                    raise ValueError(f"expected (key, agent_id), got {arguments}")
                report: ReportValue = snapshot_why(snapshot, arguments[0], arguments[1])
            elif view == "diff":
                if len(arguments) != 1:
                    raise ValueError(f"expected (key,), got {arguments}")
                report = snapshot_diff(snapshot, arguments[0])
            elif view == "compare":
                if len(arguments) != 2:
                    raise ValueError(f"expected (agent_a, agent_b), got {arguments}")
                report = snapshot_compare(snapshot, arguments[0], arguments[1])
            else:
                raise ValueError(f"unknown view {view}")
        except Exception as exc:
            with contextlib.suppress(RuntimeError, Exception):
                self.post_message(ViewReportFailed(view, request_id, generation, arguments, exc))
            return
        with contextlib.suppress(RuntimeError, Exception):
            self.post_message(ViewReportComplete(view, request_id, generation, arguments, report))

    def on_unmount(self) -> None:
        """Ensure controller is closed and events set when app unmounts."""
        self.controller.close()

    def on_capture_complete(self, message: CaptureComplete) -> None:
        """Handle successful capture publication on the UI thread."""
        if self.controller.is_closed:
            return
        if self.controller.accept_capture(message.snapshot, message.generation):
            self._update_ui()

    def on_capture_failed(self, message: CaptureFailed) -> None:
        """Handle capture error on the UI thread."""
        if self.controller.is_closed:
            return
        if self.controller.accept_capture_error(message.generation, message.error):
            self._update_ui()

    def on_view_report_complete(self, message: ViewReportComplete) -> None:
        """Handle successful view report on the UI thread."""
        if self.controller.is_closed:
            return
        accepted = self.controller.accept_view_result(
            message.view,
            message.request_id,
            message.generation,
            message.arguments,
            message.report,
        )
        screen = self.screen
        if isinstance(screen, (HomeScreen, WhyScreen, DiffScreen, CompareScreen)):
            screen.note_report_outcome(
                message.view,
                message.request_id,
                message.generation,
                message.arguments,
                accepted=accepted,
                report=message.report if accepted else None,
            )
        if accepted:
            self._update_ui()

    def on_view_report_failed(self, message: ViewReportFailed) -> None:
        """Handle view report failure on the UI thread."""
        if self.controller.is_closed:
            return
        accepted = self.controller.accept_view_error(
            message.view,
            message.request_id,
            message.generation,
            message.arguments,
            message.error,
        )
        screen = self.screen
        if isinstance(screen, (HomeScreen, WhyScreen, DiffScreen, CompareScreen)):
            screen.note_report_outcome(
                message.view,
                message.request_id,
                message.generation,
                message.arguments,
                accepted=accepted,
                error=message.error,
            )
        if accepted:
            self._update_ui()

    def _home_screen(self) -> HomeScreen | None:
        """Return the mounted Home screen, if it is the current screen."""
        try:
            screen = self.screen
        except (ScreenStackError, UnknownModeError):
            # Expected only while the app is tearing down; any other failure
            # must reach the app's containment path rather than be hidden.
            return None
        return screen if isinstance(screen, HomeScreen) else None

    def _handle_exception(self, error: Exception) -> None:
        """Contain unhandled UI/worker exceptions without terminal tracebacks.

        Overrides Textual's default _fatal_error renderer to prevent Rich
        traceback dumps to the terminal. Marks sticky failed status and exits
        cleanly with ExitCode.INTERNAL (3).
        """
        self.controller.failed = True
        self.controller.close()
        record_unhandled_fault(self, error, int(ExitCode.INTERNAL))
        self.exit(int(ExitCode.INTERNAL), return_code=int(ExitCode.INTERNAL))

    def _update_ui(self) -> None:
        """Update placeholder screen status labels on the UI thread."""
        try:
            screen = self.screen
        except (ScreenStackError, UnknownModeError):
            return

        if isinstance(screen, HelpScreen):
            # Covered screens defer reconciliation until reveal; live status and
            # in-memory fault details belong to Help while it is on top.
            screen.update_session(self.controller)
            return

        if isinstance(screen, HomeScreen):
            try:
                status_widget = screen.query_one("#status-text", Static)
                details_widget = screen.query_one("#error-details", Static)
            except NoMatches:
                status_widget = None
                details_widget = None

            if status_widget is not None and details_widget is not None:
                status = self.controller.status
                if status == "loading":
                    status_widget.update("Scanning skills...")
                    details_widget.update("")
                elif status == "ready":
                    count = (
                        len(self.controller.current.index.entries)
                        if self.controller.current is not None
                        else 0
                    )
                    status_widget.update(f"Ready: {count} skills discovered")
                    details_widget.update("")
                elif status == "refused":
                    msg = self.controller.refusal_message or "Snapshot refused."
                    status_widget.update(msg)
                    details_widget.update("")
                elif status == "retry":
                    msg = (
                        self.controller.retry_message
                        or "Files changed while scanning. Press r to retry."
                    )
                    status_widget.update(msg)
                    details_widget.update("")
                elif status == "error":
                    status_widget.update(
                        "Error: Unexpected internal fault. Details in memory only."
                    )
                    details_widget.update(self.controller.last_error_details or "")
                else:
                    status_widget.update("Idle")
                    details_widget.update("")

            with contextlib.suppress(NoMatches):
                notice_widget = screen.query_one("#removal-notice", Static)
                notice_widget.update(screen._removal_notice or "")

            screen.sync_from_controller()

        elif isinstance(screen, WhyScreen):
            try:
                status_widget = screen.query_one("#why-status", Static)
                details_widget = screen.query_one("#why-error-details", Static)
            except NoMatches:
                status_widget = None
                details_widget = None

            if status_widget is not None and details_widget is not None:
                status = self.controller.status
                if status == "loading":
                    status_widget.update("Scanning skills...")
                    details_widget.update("")
                elif status == "ready":
                    count = (
                        len(self.controller.current.index.entries)
                        if self.controller.current is not None
                        else 0
                    )
                    status_widget.update(f"Ready: {count} skills discovered")
                    details_widget.update("")
                elif status == "refused":
                    msg = self.controller.refusal_message or "Snapshot refused."
                    status_widget.update(msg)
                    details_widget.update("")
                elif status == "retry":
                    msg = (
                        self.controller.retry_message
                        or "Files changed while scanning. Press r to retry."
                    )
                    status_widget.update(msg)
                    details_widget.update("")
                elif status == "error":
                    status_widget.update(
                        "Error: Unexpected internal fault. Details in memory only."
                    )
                    details_widget.update(self.controller.last_error_details or "")
                else:
                    status_widget.update("Idle")
                    details_widget.update("")

            screen.sync_from_controller()

        elif isinstance(screen, DiffScreen):
            # The Diff screen owns its own status line, so one synchronization
            # call keeps its widgets and the controller's published state in step.
            screen.sync_from_controller()

        elif isinstance(screen, (AgentsScreen, CompareScreen, DoctorScreen)):
            screen.sync_from_controller()


__all__ = [
    "AgentsScreen",
    "CaptureComplete",
    "CaptureFailed",
    "DiffScreen",
    "PlaceholderHomeScreen",
    "SkillLensApp",
    "ViewReportComplete",
    "ViewReportFailed",
    "WhyScreen",
    "CompareScreen",
    "DoctorScreen",
    "HelpScreen",
]
