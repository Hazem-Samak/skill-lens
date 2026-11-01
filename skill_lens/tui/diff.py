"""Read-only unified Diff screen for Skill Lens (Assignment U5).

Specification reference: ``FULL_SCREEN_TUI.md`` §8.2, §8.5, §9.1, Step 5,
§21.5–21.7 and §22 U5.

The screen shows the :class:`~skill_lens.models.diff.DiffReport` the session
already owns for one canonical installation key. It never walks files, re-groups
entries or re-compares copies: the unified hunks, the baseline choice, the
truncation totals and the binary decisions all come from the model, and every
sentence comes from the shared plain helpers in :mod:`skill_lens.presentation`
so the CLI and this screen cannot drift apart.

Report ownership follows the U4 convention exactly. The screen owns at most one
complete :class:`~skill_lens.tui.session.ViewRequest` for ``(key,)``; it peeks at
the controller cache first, refuses to redraw over an identical request, and
dispatches only on a true miss.
"""

from __future__ import annotations

from typing import ClassVar, Protocol, cast

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical, VerticalScroll
from textual.content import Content
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Footer, Header, Static

from skill_lens.core.discovery import canonical_key
from skill_lens.core.exitcodes import ExitCode
from skill_lens.core.snapshot import snapshot_path
from skill_lens.core.snapshot_models import SessionSnapshot
from skill_lens.models import dumps
from skill_lens.models.diff import DiffCopy, DiffFile, DiffReport
from skill_lens.presentation import (
    BASELINE_LABEL,
    BINARY_MARKER,
    COPIES_LABEL,
    NOTE_LABEL,
    HeadingParts,
    NoticeParts,
    baseline_text,
    copy_body,
    copy_heading,
    copy_truncation_notice,
    file_notice,
    needs_listing,
    no_differences_message,
    not_found_message,
    report_truncation_notice,
    unified_text,
)
from skill_lens.tui.json_view import JsonView, session_explanation
from skill_lens.tui.session import ReportValue, SessionController, ViewName, ViewRequest

_LOADING_TEXT = "Loading report…"
_NO_REPORT_TEXT = "No report available."


class _DiffHost(Protocol):
    """The small part of :class:`SkillLensApp` the Diff screen needs."""

    controller: SessionController

    def request_report(self, view: ViewName, arguments: tuple[str, ...]) -> ReportValue | None:
        """Return a cached report or start the existing report worker."""
        ...

    def close_diff(self, removal_notice: str | None = None) -> None:
        """Close the Diff screen and reconcile its origin."""
        ...

    def _update_ui(self) -> None:
        """Ask the host app to refresh its status/error presentation."""
        ...

    def action_refresh(self) -> None:
        """Request a session refresh."""
        ...


def _span(text: str, style: str) -> Content:
    """One literal fragment, styled only when a style is supplied."""
    if not style:
        return Content.from_text(text, markup=False)
    return Content.styled(text, style)


def _join_lines(lines: list[Content]) -> Content:
    """Join composed lines into one literal, multi-line :class:`Content`."""
    return Content("\n").join(lines)


def _heading_content(parts: HeadingParts) -> Content:
    """One copy heading: styled mark, literal path/Variant/scope, styled status."""
    return Content.assemble(
        _span(parts.mark, parts.style),
        " ",
        parts.path,
        parts.variant,
        f" ({parts.scope}, {parts.parse_status})",
        "  ",
        _span(parts.status, parts.style),
    )


def _notice_content(notice: NoticeParts, *, indent: str = "") -> Content:
    """One notice banner: a styled label plus a literal body."""
    return Content.assemble(
        indent,
        _span(notice.label, notice.style),
        Content.from_text(notice.body, markup=False),
    )


def _hunk_line(text: str) -> Content:
    """One unified-diff line, coloured by its marker but never re-worded."""
    if text.startswith("+++") or text.startswith("---"):
        return Content.styled(text, "bold")
    if text.startswith("+"):
        return Content.styled(text, "green")
    if text.startswith("-"):
        return Content.styled(text, "red")
    if text.startswith("@@"):
        return Content.styled(text, "cyan")
    return Content.from_text(text, markup=False)


def _entry_name(snapshot: SessionSnapshot, key: str) -> str | None:
    """The captured folder name for one canonical key, or ``None`` when absent."""
    for row in snapshot.scan.skills:
        if row.canonical_path == key:
            return row.name
    return None


class DiffScreen(Screen[None]):
    """Read-only unified diff between the copies that share one folder name."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "back", "Back", show=True),
        Binding("backspace", "back", "Back", show=False),
        Binding("J", "toggle_json", "JSON", show=True),
        Binding("q", "app.quit", "Quit", show=True),
        Binding("ctrl+c", "app.quit", "Quit", show=False, priority=True),
        Binding("r", "app.refresh", "Refresh", show=True),
    ]

    DEFAULT_CSS = """
    DiffScreen {
        layout: vertical;
    }
    #diff-body {
        height: 1fr;
        padding: 0 1;
    }
    #diff-title {
        height: auto;
        text-style: bold;
    }
    #diff-status, #diff-error-details {
        height: auto;
    }
    #diff-content {
        width: 1fr;
        height: auto;
    }
    DiffScreen #diff-json {
        display: none;
    }
    DiffScreen.json-mode #diff-json {
        display: block;
    }
    DiffScreen.json-mode #diff-body {
        height: auto;
    }
    DiffScreen.json-mode #diff-title,
    DiffScreen.json-mode #diff-content,
    DiffScreen.json-mode #diff-error-details {
        display: none;
    }
    """

    def __init__(self, key: str) -> None:
        super().__init__()
        self._key = key
        self._captured_name: str | None = None
        self._report: DiffReport | None = None
        self._owned_request: ViewRequest | None = None
        self._generation: int | None = None
        self._mounting = False
        self._json_mode = False
        self._json_previous_focus: Widget | None = None
        self._json_previous_scroll = 0
        self._rendered_context: tuple[object, ...] | None = None

    # -- host integration ---------------------------------------------------

    @property
    def _host(self) -> _DiffHost:
        return cast(_DiffHost, self.app)

    def _controller_or_none(self) -> SessionController | None:
        return getattr(self._host, "controller", None)

    @property
    def opening_key(self) -> str:
        """The canonical installation key this screen was opened for."""
        return self._key

    @property
    def json_mode(self) -> bool:
        """True while the raw JSON view replaces the ordinary report."""
        return self._json_mode

    @property
    def report(self) -> DiffReport | None:
        """The report this screen currently owns, if any."""
        return self._report

    # -- lifecycle ----------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        # Every line of Diff metadata sits inside the report's own scroll area: a
        # valid but very long skill name or captured path must never be able to
        # push the report body (or the footer) off the screen. Scrolling reaches
        # the metadata above the report instead of hiding either of them.
        with VerticalScroll(id="diff-body"):
            yield Static("", id="diff-title", markup=False)
            yield Static("", id="diff-status", markup=False)
            yield Static("", id="diff-error-details", markup=False)
            yield Vertical(id="diff-content")
        yield JsonView(id="diff-json")
        yield Footer()

    def on_mount(self) -> None:
        body = self._body_or_none()
        if body is not None:
            body.focus()
        self._mounting = True
        try:
            self.sync_from_controller()
        finally:
            self._mounting = False

    def on_unmount(self) -> None:
        self._cancel_owned_token()

    # -- synchronization ----------------------------------------------------

    def sync_from_controller(self) -> bool:
        """Reconcile the screen with the controller's published session.

        Returns True when the screen asked the host to close it because its
        opening installation disappeared from a newly published capture.
        """
        if not self.is_mounted and not self._mounting:
            return False
        controller = self._controller_or_none()
        if controller is None:
            return False
        snapshot = controller.current
        if snapshot is None:
            self._report = None
            self._update_display()
            return False

        if self._captured_name is None:
            self._captured_name = _entry_name(snapshot, self._key)

        if snapshot.generation != self._generation:
            current_keys = {canonical_key(entry) for entry in snapshot.index.entries}
            if self._key not in current_keys:
                # Pop this screen first; the origin is the only screen allowed to
                # report the removal, and it does that when it becomes active.
                self._host.close_diff(removal_notice=self._removal_notice())
                return True
            self._generation = snapshot.generation
            # Drop the previous generation's report (and its JSON text) before
            # anything asks for the new generation's report.
            self._owned_request = None
            self._report = None
            self._rendered_context = None
            self._update_display()
            self._request_report()
            return False

        self._update_display()
        return False

    def _removal_notice(self) -> str:
        """The plain removal message for this screen's opening installation."""
        name = self._captured_name
        if name and name != self._key:
            return f"Installation '{name}' ({self._key}) was removed during refresh."
        return f"Installation '{self._key}' was removed during refresh."

    # -- report ownership ---------------------------------------------------

    def _request_report(self) -> None:
        """Request the Diff report for the opening key, or keep the current token.

        This is the U4 sequence: cached report first, then a full owned-token
        comparison so a plain redraw never re-dispatches, then a true miss.
        """
        controller = self._controller_or_none()
        if controller is None or controller.current is None:
            return
        current_keys = {canonical_key(entry) for entry in controller.current.index.entries}
        if self._key not in current_keys:
            self._host.close_diff(removal_notice=self._removal_notice())
            return

        arguments = (self._key,)
        cached = controller.get_cached_report("diff", arguments)
        if isinstance(cached, DiffReport):
            self._report = cached
            self._owned_request = None
            self._update_display()
            return

        active = controller.active_requests.get("diff")
        if (
            self._owned_request is not None
            and active is not None
            and active == self._owned_request
            and active.arguments == arguments
            and active.generation == controller.current.generation
        ):
            return

        self._cancel_owned_token()
        result = self._host.request_report("diff", arguments)
        if isinstance(result, DiffReport):
            self._report = result
            self._owned_request = None
            self._update_display()
            return

        active_now = controller.active_requests.get("diff")
        if (
            active_now is not None
            and active_now.arguments == arguments
            and active_now.generation == controller.current.generation
        ):
            self._owned_request = active_now
            self._report = None
        self._update_display()

    def _cancel_owned_token(self) -> None:
        """Cancel this screen's own Diff request, and only if it still owns it."""
        owned = self._owned_request
        self._owned_request = None
        if owned is None:
            return
        controller = self._controller_or_none()
        if controller is None:
            return
        active = controller.active_requests.get("diff")
        if active is not None and active == owned:
            controller.invalidate_view("diff")

    def note_report_outcome(
        self,
        view: ViewName,
        request_id: int,
        generation: int,
        arguments: tuple[str, ...],
        *,
        accepted: bool,
        report: ReportValue | None = None,
        error: Exception | None = None,
    ) -> None:
        """Consume an accepted Diff result, or merely wake after a rejection."""
        if not self.is_mounted or view != "diff":
            return
        controller = self._controller_or_none()
        if controller is None:
            return
        owned = self._owned_request
        if owned is None:
            return
        identity_matches = (
            owned.request_id == request_id
            and owned.generation == generation
            and owned.view == view
            and owned.arguments == arguments
        )
        if identity_matches:
            if accepted:
                self._report = report if isinstance(report, DiffReport) else None
                self._owned_request = None
                self._update_display()
            else:
                active = controller.active_requests.get("diff")
                if active is None or active != owned:
                    self._owned_request = None
                self._update_display()
                self._request_report()
        elif not accepted:
            # Rejected data for someone else's token must never clear or mark
            # the newer owned token.
            pass

    # -- display ------------------------------------------------------------

    def _update_display(self) -> None:
        self._refresh_title()
        self._refresh_status()
        self._render_body()
        self._refresh_json()

    def _refresh_title(self) -> None:
        title = self.query_one("#diff-title", Static)
        controller = self._controller_or_none()
        snapshot = controller.current if controller is not None else None
        report = self._report
        if report is not None and report.found:
            name = report.skill_name
        else:
            name = self._captured_name or self._key
        installation = snapshot_path(snapshot, self._key) if snapshot is not None else self._key
        lines = [f"Diff: '{name}'", f"Installation: {installation}"]
        title.update(Content.from_text("\n".join(lines), markup=False))

    def _refresh_status(self) -> None:
        """Show the session state, keeping old content visible while a refresh runs."""
        controller = self._controller_or_none()
        status_widget = self.query_one("#diff-status", Static)
        error_widget = self.query_one("#diff-error-details", Static)
        if controller is None:
            status_widget.update(Content.from_text("No session captured.", markup=False))
            error_widget.update(Content.from_text("", markup=False))
            return
        status_widget.update(Content.from_text(session_explanation(controller), markup=False))
        details = (
            controller.last_error_details
            if controller.status == "error" and controller.last_error_details
            else ""
        )
        error_widget.update(Content.from_text(details, markup=False))

    def _placeholder_text(self) -> str:
        controller = self._controller_or_none()
        if controller is None:
            return _NO_REPORT_TEXT
        if controller.current is None:
            return session_explanation(controller)
        if self._owned_request is not None:
            return _LOADING_TEXT
        return _NO_REPORT_TEXT

    def _render_body(self) -> None:
        """Mount the report's summary, copies, truncation totals and notes."""
        container = self.query_one("#diff-content", Vertical)
        context = (
            id(self._report) if self._report is not None else None,
            self._generation,
            self._placeholder_text() if self._report is None else "",
        )
        if self._rendered_context == context:
            return
        container.remove_children()
        report = self._report
        controller = self._controller_or_none()
        snapshot = controller.current if controller is not None else None

        if report is None or snapshot is None:
            container.mount(
                Static(
                    Content.from_text(self._placeholder_text(), markup=False),
                    markup=False,
                )
            )
            self._rendered_context = context
            return

        if not report.found:
            container.mount(
                Static(
                    Content.from_text(not_found_message(report), markup=False),
                    classes="diff-block diff-not-found",
                    markup=False,
                )
            )
            self._rendered_context = context
            return

        blocks: list[Static] = [
            Static(
                self._summary_content(report, snapshot),
                classes="diff-block diff-summary",
                markup=False,
            )
        ]
        show_notes = report.baseline_path is not None
        listing_needed = True
        if not report.has_differences:
            blocks.append(
                Static(
                    _notice_content(no_differences_message(report)),
                    classes="diff-block diff-notice",
                    markup=False,
                )
            )
            listing_needed = needs_listing(report)

        if listing_needed:
            baseline_exists = report.baseline_path is not None
            for copy in report.copies:
                blocks.append(
                    Static(
                        self._copy_content(
                            copy, baseline_exists=baseline_exists, snapshot=snapshot
                        ),
                        classes="diff-block diff-copy",
                        markup=False,
                    )
                )
            truncation = report_truncation_notice(report)
            if truncation is not None:
                blocks.append(
                    Static(
                        _notice_content(truncation),
                        classes="diff-block diff-truncated",
                        markup=False,
                    )
                )
        if show_notes:
            blocks.append(
                Static(
                    self._notes_content(report),
                    classes="diff-block diff-notes",
                    markup=False,
                )
            )
        container.mount(*blocks)
        self._rendered_context = context

    def _summary_content(self, report: DiffReport, snapshot: SessionSnapshot) -> Content:
        baseline = next((copy for copy in report.copies if copy.is_baseline), None)
        display = snapshot_path(snapshot, baseline.path) if baseline is not None else None
        lines = [
            Content.assemble(Content.styled(COPIES_LABEL, "bold"), f" {len(report.copies)}"),
            Content.assemble(
                Content.styled(BASELINE_LABEL, "bold"),
                " ",
                Content.from_text(baseline_text(baseline, display_path=display), markup=False),
            ),
        ]
        return _join_lines(lines)

    def _copy_content(
        self,
        copy: DiffCopy,
        *,
        baseline_exists: bool,
        snapshot: SessionSnapshot,
    ) -> Content:
        parts = copy_heading(
            copy,
            baseline_exists=baseline_exists,
            display_path=snapshot_path(snapshot, copy.path),
        )
        lines: list[Content] = [_heading_content(parts)]
        body = copy_body(copy, baseline_exists=baseline_exists)
        if body is not None:
            lines.append(Content.assemble("  ", Content.from_text(body, markup=False)))
        else:
            for file in copy.files:
                lines.extend(self._file_lines(file))
        truncation = copy_truncation_notice(copy)
        if truncation is not None:
            lines.append(_notice_content(truncation, indent="  "))
        return _join_lines(lines)

    def _file_lines(self, file: DiffFile) -> list[Content]:
        marker = f" {BINARY_MARKER}" if file.is_binary else ""
        lines = [
            Content.assemble(
                "  ",
                Content.styled(file.path, "bold"),
                " ",
                Content.styled(file.change.value, "yellow"),
                marker,
            )
        ]
        notice = file_notice(file)
        if notice is not None:
            lines.append(Content.assemble("    ", Content.from_text(notice, markup=False)))
            return lines
        lines.extend(_hunk_line(text) for text in unified_text(file).split("\n"))
        return lines

    def _notes_content(self, report: DiffReport) -> Content:
        lines = [
            Content.assemble(Content.styled(NOTE_LABEL, "yellow"), f" {note}")
            for note in report.notes
        ]
        return _join_lines(lines)

    # -- raw JSON -----------------------------------------------------------

    def _refresh_json(self) -> None:
        """Keep the raw view bound to this screen's accepted report."""
        view = self.query_one("#diff-json", JsonView)
        controller = self._controller_or_none()
        if controller is None or controller.current is None:
            view.show_explanation(self._placeholder_text())
            return
        cached = controller.get_cached_report("diff", (self._key,))
        if isinstance(cached, DiffReport):
            view.show_document(dumps(cached.to_dict()))
            return
        if self._report is not None and self._generation == controller.current.generation:
            view.show_document(dumps(self._report.to_dict()))
            return
        view.show_explanation(self._placeholder_text())

    def action_toggle_json(self) -> None:
        """Toggle between the unified diff and its canonical JSON document."""
        if self._json_mode:
            self.leave_json_mode()
        else:
            self.enter_json_mode()

    def enter_json_mode(self) -> None:
        """Show the JSON document, remembering the ordinary focus and scroll."""
        if self._json_mode:
            return
        body = self._body_or_none()
        self._json_previous_focus = self.app.focused
        self._json_previous_scroll = body.scroll_offset.y if body is not None else 0
        self._json_mode = True
        self.add_class("json-mode")
        if body is not None:
            # The collapsed metadata strip stays visible for the status line, but
            # it must not become a Tab stop between the reader and the JSON pane.
            body.can_focus = False
        self._refresh_json()
        view = self._json_view_or_none()
        if view is not None:
            # Focus lands after the stylesheet has hidden the ordinary report.
            self.call_after_refresh(view.focus)

    def _json_view_or_none(self) -> JsonView | None:
        try:
            return self.query_one("#diff-json", JsonView)
        except NoMatches:
            return None

    def leave_json_mode(self) -> None:
        """Return to the ordinary report, restoring a valid focus and scroll."""
        if not self._json_mode:
            return
        self._json_mode = False
        self.remove_class("json-mode")
        body = self._body_or_none()
        if body is not None:
            body.can_focus = True
        self._restore_ordinary_focus()
        if self._json_previous_scroll:
            self.call_after_refresh(self._restore_body_scroll, self._json_previous_scroll)

    def _restore_ordinary_focus(self) -> None:
        previous = self._json_previous_focus
        self._json_previous_focus = None
        if previous is not None and previous.can_focus and previous.is_mounted and previous.display:
            previous.focus()
            return
        body = self._body_or_none()
        if body is not None:
            body.focus()

    def _restore_body_scroll(self, offset: int) -> None:
        body = self._body_or_none()
        if body is not None:
            body.scroll_to(y=offset, animate=False)

    def _body_or_none(self) -> VerticalScroll | None:
        try:
            return self.query_one("#diff-body", VerticalScroll)
        except NoMatches:
            return None

    # -- actions ------------------------------------------------------------

    def action_back(self) -> None:
        """Leave JSON mode first, otherwise return to the origin screen."""
        if self._json_mode:
            self.leave_json_mode()
            return
        self._host.close_diff()

    def action_quit(self) -> None:
        """Quit the application with the controller's exit code."""
        controller = self._controller_or_none()
        code = controller.close() if controller is not None else int(ExitCode.OK)
        self.app.exit(code, return_code=code)

    def action_refresh(self) -> None:
        """Request a session refresh through the host app."""
        self._host.action_refresh()


__all__ = ["DiffScreen"]
