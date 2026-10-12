"""Skill Lens Textual Application and Placeholder Home Screen (Assignment U2).

Specification reference: FULL_SCREEN_TUI.md §9.1, §10, Step 2, and §21.7.
Provides:
- SkillLensApp(App[int]) with placeholder screen and q/r bindings
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
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.css.query import NoMatches
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from skill_lens import __version__
from skill_lens.core.cancellation import CaptureCancelled
from skill_lens.core.exitcodes import ExitCode
from skill_lens.core.snapshot import (
    capture_session,
    snapshot_compare,
    snapshot_diff,
    snapshot_why,
)
from skill_lens.core.snapshot_models import SessionSnapshot
from skill_lens.tui.session import (
    ReportValue,
    SessionController,
    ViewName,
)


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


class PlaceholderHomeScreen(Screen[None]):
    """Placeholder Home screen displaying session status and error details."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"Skill Lens {__version__} (Placeholder)", id="title")
        yield Static("Initializing...", id="status-text", markup=False)
        yield Static("", id="error-details", markup=False)
        yield Static("q: Quit   r: Refresh", id="footer-help")
        yield Footer()

    def on_mount(self) -> None:
        if isinstance(self.app, SkillLensApp):
            self.app._update_ui()


class SkillLensApp(App[int]):
    """Skill Lens full-screen interactive browsing application."""

    TITLE = "Skill Lens"
    SUB_TITLE = __version__
    ENABLE_COMMAND_PALETTE: ClassVar[bool] = False
    COMMANDS: ClassVar[set[Any]] = set()
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
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
    ) -> None:
        super().__init__()
        self._home = home
        self._cwd = cwd
        self.controller: SessionController = (
            controller if controller is not None else SessionController()
        )

    def get_default_screen(self) -> Screen[None]:
        """Return the placeholder Home screen as the default root screen."""
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
        req = self.controller.request_refresh()
        if req is not None:
            gen, event = req
            self._update_ui()
            self._run_capture(gen, self._home, self._cwd, event)

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
        if accepted:
            self._update_ui()

    def _handle_exception(self, error: Exception) -> None:
        """Contain unhandled UI/worker exceptions without terminal tracebacks.

        Overrides Textual's default _fatal_error renderer to prevent Rich
        traceback dumps to the terminal. Marks sticky failed status and exits
        cleanly with ExitCode.INTERNAL (3).
        """
        self.controller.failed = True
        self.controller.close()
        self._return_code = int(ExitCode.INTERNAL)
        if self._exception is None:
            self._exception = error
            self._exception_event.set()
        self.exit(int(ExitCode.INTERNAL), return_code=int(ExitCode.INTERNAL))

    def _update_ui(self) -> None:
        """Update placeholder screen status labels on the UI thread."""
        try:
            status_widget = self.query_one("#status-text", Static)
            details_widget = self.query_one("#error-details", Static)
        except NoMatches:
            return

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
        elif status == "retry":
            msg = self.controller.retry_message or "Files changed while scanning. Press r to retry."
            status_widget.update(msg)
            details_widget.update("")
        elif status == "error":
            status_widget.update("Error: Unexpected internal fault. Details in memory only.")
            details_widget.update(self.controller.last_error_details or "")
        else:
            status_widget.update("Idle")
            details_widget.update("")


__all__ = [
    "CaptureComplete",
    "CaptureFailed",
    "PlaceholderHomeScreen",
    "SkillLensApp",
    "ViewReportComplete",
    "ViewReportFailed",
]
