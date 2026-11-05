"""Read-only Doctor screen backed by the published session snapshot.

Specification reference: ``FULL_SCREEN_TUI.md`` §8.6, §8.8, §9.1, §10,
Step 7 and §22 U7. Doctor displays the captured report and uses only captured
path relationships when it offers an in-app jump to Home.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import ClassVar, Protocol, cast

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, VerticalScroll
from textual.content import Content
from textual.coordinate import Coordinate
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import DataTable, Footer, Header, Static

from skill_lens.core.discovery import DiscoveredEntry, canonical_key
from skill_lens.core.snapshot import snapshot_path, snapshot_same_location
from skill_lens.core.snapshot_models import SessionSnapshot
from skill_lens.models import dumps
from skill_lens.models.doctor import DoctorFinding, DoctorReport
from skill_lens.models.enums import Severity
from skill_lens.tui.help import HelpContext, HelpRow
from skill_lens.tui.json_view import JsonView, session_explanation
from skill_lens.tui.session import SessionController

_LITERAL_MARKUP = False
_NONE = "(none)"


class _DoctorHost(Protocol):
    """The bounded part of the application used by Doctor."""

    controller: SessionController

    def close_doctor(self, screen: DoctorScreen) -> None:
        """Close this exact Doctor instance and resume Home."""
        ...

    def jump_from_doctor(self, screen: DoctorScreen, generation: int, key: str) -> bool:
        """Validate and perform a frozen in-app Home selection."""
        ...

    def _update_ui(self) -> None:
        """Refresh status and synchronize the active screen."""
        ...

    def action_refresh(self) -> None:
        """Request the existing full session refresh."""
        ...


@dataclass(frozen=True, slots=True)
class FindingIdentity:
    """One finding row, including generation and duplicate occurrence."""

    generation: int
    finding: DoctorFinding
    occurrence: int


def _same_finding(left: FindingIdentity | None, right: FindingIdentity | None) -> bool:
    return (
        left is not None
        and right is not None
        and left.finding == right.finding
        and left.occurrence == right.occurrence
    )


def finding_identities(
    generation: int, findings: tuple[DoctorFinding, ...]
) -> tuple[FindingIdentity, ...]:
    """Give repeated equal findings distinct, stable occurrence identities."""
    occurrences: dict[DoctorFinding, int] = {}
    rows: list[FindingIdentity] = []
    for finding in findings:
        occurrence = occurrences.get(finding, 0)
        occurrences[finding] = occurrence + 1
        rows.append(FindingIdentity(generation, finding, occurrence))
    return tuple(rows)


def finding_catalog_keys(snapshot: SessionSnapshot, finding: DoctorFinding) -> tuple[str, ...]:
    """Return catalog identities proved by the snapshot's stored path map.

    The reverse display lookup deliberately keeps every match: two raw paths
    can share a displayed value, and that ambiguity must remain visible.
    """
    path = finding.path
    if not path:
        return ()

    candidates = {path}
    candidates.update(
        raw_path
        for raw_path, display_path in snapshot.display_paths.items()
        if display_path == path
    )

    keys: set[str] = set()
    for entry in snapshot.index.entries:
        entry_paths = _entry_paths(entry)
        if any(
            candidate == entry_path or snapshot_same_location(snapshot, candidate, entry_path)
            for candidate in candidates
            for entry_path in entry_paths
        ):
            keys.add(canonical_key(entry))
    return tuple(sorted(keys))


def _entry_paths(entry: DiscoveredEntry) -> tuple[str, ...]:
    """All captured entry paths, including paths retained by individual hits."""
    paths = {entry.entrypoint_path, *entry.entrypoint_paths}
    paths.update(hit.entrypoint_path for hit in entry.hits)
    if entry.canonical_path is not None:
        paths.add(entry.canonical_path)
    return tuple(paths)


def finding_detail_text(finding: DoctorFinding) -> str:
    """Show every report field verbatim, using a clear placeholder for nulls."""
    return "\n".join(
        (
            f"Severity: {finding.severity.value}",
            f"Code: {finding.code}",
            f"Message: {finding.message}",
            f"Path: {finding.path if finding.path is not None else _NONE}",
            f"Detail: {finding.detail if finding.detail is not None else _NONE}",
            f"Rule ID: {finding.rule_id}",
            f"Evidence: {finding.evidence.value}",
        )
    )


def doctor_summary(report: DoctorReport) -> str:
    """Summarize counts without conflating info-only and empty reports."""
    if not report.findings:
        return "Skill folders look healthy."
    counts = report.counts_by_severity()
    health = "healthy" if report.healthy else "needs attention"
    return (
        f"{len(report.findings)} findings: {counts[Severity.ERROR.value]} errors, "
        f"{counts[Severity.WARNING.value]} warnings, {counts[Severity.INFO.value]} info. "
        f"Status: {health}."
    )


class DoctorScreen(Screen[None]):
    """Browse one captured Doctor report and optionally select its catalog row."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("enter", "jump", "Select in Home", show=True),
        Binding("escape", "back", "Back", show=True),
        Binding("backspace", "back", "Back", show=False),
        Binding("J", "toggle_json", "JSON", show=True),
        Binding("q", "app.quit", "Quit", show=True),
        Binding("ctrl+c", "app.quit", "Quit", show=False, priority=True),
        Binding("r", "app.refresh", "Refresh", show=True),
    ]

    DEFAULT_CSS = """
    DoctorScreen {
        layout: vertical;
    }
    #doctor-title {
        height: 1;
        padding: 0 1;
        text-style: bold;
    }
    #doctor-summary, #doctor-context, #doctor-navigation,
    #doctor-status, #doctor-error-details {
        height: auto;
        padding: 0 1;
    }
    #doctor-navigation {
        color: $warning;
    }
    #doctor-body {
        width: 1fr;
        height: 1fr;
        layout: horizontal;
    }
    #doctor-findings {
        width: 3fr;
        height: 1fr;
    }
    #doctor-detail-scroll {
        width: 2fr;
        height: 1fr;
        padding: 0 1;
        border-left: solid $primary;
    }
    #doctor-detail {
        width: 1fr;
        height: auto;
    }
    #doctor-empty {
        height: auto;
        padding: 0 1;
        color: $text-muted;
    }
    #doctor-json {
        display: none;
    }
    DoctorScreen.json-mode #doctor-json {
        display: block;
    }
    DoctorScreen.json-mode #doctor-summary,
    DoctorScreen.json-mode #doctor-context,
    DoctorScreen.json-mode #doctor-navigation,
    DoctorScreen.json-mode #doctor-body,
    DoctorScreen.json-mode #doctor-empty {
        display: none;
    }
    DoctorScreen.narrow #doctor-body {
        layout: vertical;
    }
    DoctorScreen.narrow #doctor-findings,
    DoctorScreen.narrow #doctor-detail-scroll {
        width: 1fr;
        height: 1fr;
    }
    DoctorScreen.narrow #doctor-detail-scroll {
        border-left: none;
        border-top: solid $primary;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._generation: int | None = None
        self._identities: tuple[FindingIdentity, ...] = ()
        self._identity_by_row_key: dict[str, FindingIdentity] = {}
        self._selected: FindingIdentity | None = None
        self._syncing = False
        self._mounting = False
        self._json_mode = False
        self._json_previous_focus: Widget | None = None
        self._json_previous_identity: FindingIdentity | None = None
        self._json_previous_detail_scroll = 0
        self._ordinary_detail_scroll = 0
        self._navigation_notice = ""
        self._suspended = False
        self._help_focus: Widget | None = None
        self._help_generation: int | None = None
        self._help_detail_scroll = 0
        self._help_json_scroll = 0

    @property
    def _host(self) -> _DoctorHost:
        return cast(_DoctorHost, self.app)

    @property
    def json_mode(self) -> bool:
        return self._json_mode

    @property
    def selected_finding(self) -> DoctorFinding | None:
        return self._selected.finding if self._selected is not None else None

    @property
    def selected_identity(self) -> FindingIdentity | None:
        return self._selected

    @property
    def navigation_notice(self) -> str:
        return self._navigation_notice

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Doctor", id="doctor-title", markup=False)
        yield Static("", id="doctor-summary", markup=False)
        yield Static("", id="doctor-context", markup=False)
        with Horizontal(id="doctor-body"):
            yield DataTable(id="doctor-findings")
            with VerticalScroll(id="doctor-detail-scroll"):
                yield Static("No finding selected.", id="doctor-detail", markup=False)
        yield Static("", id="doctor-empty", markup=False)
        yield Static("", id="doctor-navigation", markup=False)
        yield JsonView(id="doctor-json")
        yield Static("Initializing...", id="doctor-status", markup=False)
        yield Static("", id="doctor-error-details", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#doctor-findings", DataTable)
        table.cursor_type = "row"
        self._apply_width(self.size.width)
        self._mounting = True
        try:
            self.sync_from_controller()
        finally:
            self._mounting = False
        if not self._json_mode:
            table.focus()
        self.call_after_refresh(self._host._update_ui)

    def on_resize(self, event: events.Resize) -> None:
        self._apply_width(event.size.width)

    def _apply_width(self, width: int) -> None:
        self.set_class(width < 80, "narrow")

    def _is_active(self) -> bool:
        return self.app.screen is self

    def on_screen_suspend(self) -> None:
        """A covering screen (Help) starts; Doctor owns no report workers."""
        self.suspend_help()

    def on_screen_resume(self) -> None:
        """The covering screen closed: reconcile and restore the exact view."""
        self.resume_help()

    # -- Help overlay -------------------------------------------------------

    def help_context(self) -> HelpContext:
        """Describe the captured findings view, its focus and its exit scope."""
        rows: list[HelpRow] = []
        notes: list[str] = []
        if self._json_mode:
            mode = "raw JSON view"
            focus = "JSON document"
            rows.extend(
                [
                    HelpRow(
                        "↑ ↓ / PageUp / PageDown / Home / End",
                        "Scroll the captured doctor JSON report.",
                    ),
                    HelpRow(
                        "J / Esc / Backspace",
                        "Return to the ordinary Doctor view.",
                    ),
                    HelpRow(
                        "r",
                        "Refresh the captured session; this report changes only when a"
                        " new capture is accepted.",
                    ),
                ]
            )
            notes.append("Enter does not select a Home row while JSON is shown.")
        else:
            mode = "findings list"
            focus = "details pane" if self._details_focused() else "findings table"
            rows.extend(
                [
                    HelpRow(
                        "↑ ↓ / j k",
                        "Move the selected finding, or scroll the details pane while it has focus.",
                    ),
                    HelpRow(
                        "Enter",
                        "Select the matching captured row in Home. When no catalog entry"
                        " matches, the path is shown literally in the in-app notice.",
                    ),
                    HelpRow(
                        "J",
                        "Toggle the captured doctor --json report while the findings"
                        " table or details pane has focus.",
                    ),
                    HelpRow(
                        "Esc / Backspace",
                        "Close Doctor and return to Home; leave JSON first if it is shown.",
                    ),
                ]
            )
            snapshot = self._host.controller.current
            if snapshot is None:
                notes.append("No session is captured yet; refresh to capture a Doctor report.")
            else:
                notes.append(doctor_summary(snapshot.doctor))
                notes.append(
                    "Doctor Enter never opens a file, editor or application; it only"
                    " selects an existing captured Home row."
                )
        return HelpContext("Doctor", mode, focus, tuple(rows), tuple(notes))

    def _details_focused(self) -> bool:
        focused = self.app.focused
        return focused is not None and focused.id == "doctor-detail-scroll"

    def suspend_help(self) -> None:
        """Remember the exact focus/scroll; no report worker is owned here."""
        if self._suspended:
            return
        self._suspended = True
        controller = self._host.controller
        snapshot = controller.current
        self._help_generation = snapshot.generation if snapshot is not None else None
        self._help_focus = self.app.focused
        with contextlib.suppress(NoMatches):
            detail = self.query_one("#doctor-detail-scroll", VerticalScroll)
            self._help_detail_scroll = int(detail.scroll_offset.y)
        try:
            view = self.query_one("#doctor-json", JsonView)
        except NoMatches:
            view = None
        self._help_json_scroll = int(view.scroll_offset.y) if view is not None else 0

    def resume_help(self) -> None:
        """Reconcile the revealed Doctor view once and restore its exact state."""
        if not self.is_mounted:
            self._suspended = False
            return
        try:
            if self.app.screen is not self:
                return
        except Exception:  # pragma: no cover - only during teardown
            return
        self._suspended = False
        self.sync_from_controller()
        if not self.is_mounted:
            return
        controller = self._host.controller
        snapshot = controller.current
        same_generation = self._help_generation == (
            snapshot.generation if snapshot is not None else None
        )
        target = self._help_focus
        if target is not None and target.can_focus and target.is_mounted and target.display:
            target.focus()
        else:
            with contextlib.suppress(NoMatches):
                self.query_one("#doctor-findings", DataTable).focus()
        if not same_generation:
            return
        if self._json_mode:
            try:
                view = self.query_one("#doctor-json", JsonView)
            except NoMatches:
                view = None
            if view is not None and self._help_json_scroll:
                self.call_after_refresh(self._scroll_help_widget, view, self._help_json_scroll)
        elif self._help_detail_scroll:
            with contextlib.suppress(NoMatches):
                detail = self.query_one("#doctor-detail-scroll", VerticalScroll)
                self.call_after_refresh(self._scroll_help_widget, detail, self._help_detail_scroll)

    def _scroll_help_widget(self, widget: Widget, offset: int) -> None:
        if not self.is_mounted or self._suspended:
            return
        try:
            if self.app.screen is not self:
                return
        except Exception:  # pragma: no cover - only during teardown
            return
        widget.scroll_to(y=offset, animate=False)

    def _focus_if_active(self, widget: Widget | None) -> None:
        """Complete a deferred focus only while Doctor is still active."""
        if widget is None or not self.is_mounted:
            return
        try:
            if self.app.screen is not self:
                return
        except Exception:  # pragma: no cover - only during teardown
            return
        if self._suspended or not widget.can_focus or not widget.is_mounted:
            return
        if not widget.display:
            return
        widget.focus()

    def sync_from_controller(self) -> None:
        """Reconcile once from the currently published snapshot, never from disk."""
        if not self.is_mounted and not self._mounting:
            return
        if self._suspended:
            return
        snapshot = self._host.controller.current
        if snapshot is None:
            if self._generation is not None:
                self._generation = None
                self._identities = ()
                self._identity_by_row_key = {}
                self._selected = None
                self._rebuild_table()
                self._update_detail(reset_scroll=True)
            self._update_summary(None)
            self._refresh_json(None)
        elif snapshot.generation != self._generation:
            self._replace_snapshot(snapshot)
        else:
            self._refresh_json(snapshot)
        self._update_navigation_notice()
        self._update_status()

    def _replace_snapshot(self, snapshot: SessionSnapshot) -> None:
        previous = self._selected
        previous_scroll = self._detail_scroll_y()
        self._generation = snapshot.generation
        self._identities = finding_identities(snapshot.generation, snapshot.doctor.findings)
        self._identity_by_row_key = {
            f"doctor:{snapshot.generation}:{position}": identity
            for position, identity in enumerate(self._identities)
        }
        self._selected = next(
            (identity for identity in self._identities if _same_finding(previous, identity)),
            self._identities[0] if self._identities else None,
        )
        selection_changed = not _same_finding(previous, self._selected)
        if selection_changed:
            self._ordinary_detail_scroll = 0
            if not _same_finding(self._json_previous_identity, self._selected):
                self._json_previous_detail_scroll = 0
                self._json_previous_identity = self._selected
        else:
            self._ordinary_detail_scroll = previous_scroll

        self._navigation_notice = ""
        self._rebuild_table()
        self._update_summary(snapshot)
        self._update_detail(reset_scroll=selection_changed)
        if not selection_changed and previous_scroll:
            self.call_after_refresh(self._restore_detail_scroll, previous_scroll)
        self._refresh_json(snapshot)

    def _rebuild_table(self) -> None:
        try:
            table = self.query_one("#doctor-findings", DataTable)
        except NoMatches:
            return
        widths = self._column_widths()
        self._syncing = True
        try:
            table.clear(columns=True)
            for label, key in (
                ("Severity", "severity"),
                ("Code", "code"),
                ("Message", "message"),
                ("Path", "path"),
            ):
                table.add_column(label, width=widths[key], key=key)
            for position, identity in enumerate(self._identities):
                row_key = f"doctor:{identity.generation}:{position}"
                finding = identity.finding
                table.add_row(
                    _literal(finding.severity.value),
                    _literal(finding.code),
                    _literal(finding.message),
                    _literal(finding.path if finding.path is not None else _NONE),
                    key=row_key,
                )
            if self._selected is not None:
                selected_key = self._row_key_for_identity(self._selected)
                if selected_key is not None:
                    selected_row = next(
                        (
                            position
                            for position, identity in enumerate(self._identities)
                            if identity == self._selected
                        ),
                        0,
                    )
                    table.move_cursor(row=selected_row, column=0, animate=False)
        finally:
            self._syncing = False

    def _column_widths(self) -> dict[str, int]:
        widths = {
            name: _cell_width(label)
            for name, label in (
                ("severity", "Severity"),
                ("code", "Code"),
                ("message", "Message"),
                ("path", "Path"),
            )
        }
        for identity in self._identities:
            finding = identity.finding
            values = {
                "severity": finding.severity.value,
                "code": finding.code,
                "message": finding.message,
                "path": finding.path if finding.path is not None else _NONE,
            }
            for column, value in values.items():
                widths[column] = max(widths[column], _cell_width(value))
        return widths

    def _row_key_for_identity(self, identity: FindingIdentity) -> str | None:
        return next(
            (key for key, value in self._identity_by_row_key.items() if value == identity), None
        )

    def _selected_from_row_key(self, value: object) -> FindingIdentity | None:
        identity = self._identity_by_row_key.get(str(value))
        if identity is None or identity.generation != self._generation:
            return None
        if identity not in self._identities:
            return None
        return identity

    def _selected_from_table(self) -> FindingIdentity | None:
        if not self._is_active() or self._json_mode:
            return None
        try:
            table = self.query_one("#doctor-findings", DataTable)
        except NoMatches:
            return None
        if not table.has_focus or table.cursor_row < 0 or table.cursor_row >= len(self._identities):
            return None
        try:
            row_key = table.coordinate_to_cell_key(
                Coordinate(row=table.cursor_row, column=0)
            ).row_key.value
        except (IndexError, KeyError):
            return None
        return self._selected_from_row_key(row_key)

    def _finding_is_current(self, generation: int, finding: DoctorFinding) -> bool:
        snapshot = self._host.controller.current
        if snapshot is None or snapshot.generation != generation:
            return False
        return (
            any(
                identity == self._selected
                for identity in finding_identities(snapshot.generation, snapshot.doctor.findings)
            )
            and self._selected is not None
            and self._selected.finding == finding
        )

    def _update_summary(self, snapshot: SessionSnapshot | None) -> None:
        try:
            summary = self.query_one("#doctor-summary", Static)
            context = self.query_one("#doctor-context", Static)
            empty = self.query_one("#doctor-empty", Static)
        except NoMatches:
            return
        if snapshot is None:
            text = session_explanation(self._host.controller)
            summary.update(_literal(text))
            context.update(_literal(""))
            empty.update(_literal(text))
            return
        report = snapshot.doctor
        summary.update(_literal(doctor_summary(report)))
        home = snapshot_path(snapshot, report.home)
        cwd = snapshot_path(snapshot, report.cwd)
        context.update(_literal(f"Home: {home}\nCwd: {cwd}"))
        empty.update(_literal(""))

    def _update_detail(self, *, reset_scroll: bool) -> None:
        try:
            widget = self.query_one("#doctor-detail", Static)
        except NoMatches:
            return
        text = (
            finding_detail_text(self._selected.finding)
            if self._selected is not None
            else "No finding selected."
        )
        widget.update(_literal(text))
        if reset_scroll:
            self._ordinary_detail_scroll = 0
            self.call_after_refresh(self._restore_detail_scroll, 0)

    def _detail_scroll_y(self) -> int:
        try:
            return int(self.query_one("#doctor-detail-scroll", VerticalScroll).scroll_offset.y)
        except NoMatches:
            return self._ordinary_detail_scroll

    def _restore_detail_scroll(self, offset: int) -> None:
        if not self.is_mounted or not self._is_active() or self._json_mode:
            return
        with contextlib.suppress(NoMatches):
            self.query_one("#doctor-detail-scroll", VerticalScroll).scroll_to(
                y=offset, animate=False
            )
        self._ordinary_detail_scroll = offset

    def _refresh_json(self, snapshot: SessionSnapshot | None) -> None:
        try:
            view = self.query_one("#doctor-json", JsonView)
        except NoMatches:
            return
        if snapshot is None:
            view.show_explanation(session_explanation(self._host.controller))
        else:
            view.show_document(dumps(snapshot.doctor.to_dict()))

    def _update_status(self) -> None:
        try:
            status = self.query_one("#doctor-status", Static)
            error_details = self.query_one("#doctor-error-details", Static)
        except NoMatches:
            return
        controller = self._host.controller
        status.update(_literal(session_explanation(controller)))
        error = controller.last_error_details if controller.status == "error" else ""
        error_details.update(_literal(error or ""))

    def _update_navigation_notice(self) -> None:
        with contextlib.suppress(NoMatches):
            self.query_one("#doctor-navigation", Static).update(_literal(self._navigation_notice))

    def set_navigation_notice(self, message: str) -> None:
        self._navigation_notice = message
        self._update_navigation_notice()

    def _set_selected(self, identity: FindingIdentity) -> None:
        if identity == self._selected:
            return
        self._selected = identity
        self._update_detail(reset_scroll=True)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if (
            self._suspended
            or self._syncing
            or self._json_mode
            or not self._is_active()
            or event.data_table.id != "doctor-findings"
        ):
            return
        identity = self._selected_from_row_key(event.row_key.value)
        if identity is None:
            return
        self._set_selected(identity)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if self._suspended or self._syncing or self._json_mode or not self._is_active():
            return
        if event.data_table.id != "doctor-findings" or not event.data_table.has_focus:
            return
        identity = self._selected_from_row_key(event.row_key.value)
        if identity is not None:
            self._jump(identity)

    def action_cursor_down(self) -> None:
        self._move_or_scroll(1)

    def action_cursor_up(self) -> None:
        self._move_or_scroll(-1)

    def _move_or_scroll(self, delta: int) -> None:
        if self._suspended or self._json_mode or not self._is_active():
            return
        focused = self.app.focused
        if isinstance(focused, DataTable) and focused.id == "doctor-findings":
            action = focused.action_cursor_down if delta > 0 else focused.action_cursor_up
            action()
        elif focused is not None and focused.id == "doctor-detail-scroll":
            focused.scroll_relative(y=delta, animate=False)

    def action_toggle_json(self) -> None:
        if self._suspended:
            return
        if self._json_mode:
            self.leave_json_mode()
            return
        focused = self.app.focused
        if focused is None or focused.id not in {"doctor-findings", "doctor-detail-scroll"}:
            return
        self.enter_json_mode()

    def enter_json_mode(self) -> None:
        if self._suspended or self._json_mode:
            return
        table = self.query_one("#doctor-findings", DataTable)
        detail = self.query_one("#doctor-detail-scroll", VerticalScroll)
        self._json_previous_focus = self.app.focused
        self._json_previous_identity = self._selected
        self._json_previous_detail_scroll = int(detail.scroll_offset.y)
        self._ordinary_detail_scroll = self._json_previous_detail_scroll
        table.can_focus = False
        detail.can_focus = False
        self._json_mode = True
        self.add_class("json-mode")
        self._refresh_json(self._host.controller.current)
        self.call_after_refresh(self._focus_if_active, self.query_one("#doctor-json", JsonView))

    def leave_json_mode(self) -> None:
        if not self._json_mode:
            return
        self._json_mode = False
        self.remove_class("json-mode")
        table = self.query_one("#doctor-findings", DataTable)
        detail = self.query_one("#doctor-detail-scroll", VerticalScroll)
        table.can_focus = True
        detail.can_focus = True
        previous = self._json_previous_focus
        self._json_previous_focus = None
        self.call_after_refresh(self._restore_json_focus, previous)

    def _restore_json_focus(self, previous: Widget | None) -> None:
        if not self.is_mounted or self._suspended or not self._is_active() or self._json_mode:
            return
        table = self.query_one("#doctor-findings", DataTable)
        target = previous
        if target is None or not target.is_mounted or not target.can_focus or not target.display:
            target = table
        target.focus()
        identity = self._json_previous_identity
        offset = self._json_previous_detail_scroll
        if _same_finding(identity, self._selected):
            self._restore_detail_scroll(offset)
        else:
            self._restore_detail_scroll(0)
        self._json_previous_identity = None
        self._json_previous_detail_scroll = 0

    def action_back(self) -> None:
        if self._suspended:
            return
        if self._json_mode:
            self.leave_json_mode()
        else:
            self._host.close_doctor(self)

    def action_jump(self) -> None:
        identity = self._selected_from_table()
        if identity is not None:
            self._jump(identity)

    def _jump(self, identity: FindingIdentity) -> None:
        if (
            not self._is_active()
            or self._json_mode
            or identity.generation != self._generation
            or identity != self._selected
        ):
            return
        snapshot = self._host.controller.current
        if snapshot is None:
            return
        if snapshot.generation != identity.generation:
            self.sync_from_controller()
            self.set_navigation_notice(
                "The captured report changed. Review the current finding and press Enter again."
            )
            return
        keys = finding_catalog_keys(snapshot, identity.finding)
        if not identity.finding.path:
            self.set_navigation_notice("This finding has no path to select in Home.")
        elif not keys:
            self.set_navigation_notice(
                f"No matching catalog entry for this path: {identity.finding.path}"
            )
        elif len(keys) > 1:
            self.set_navigation_notice(
                "This path matches more than one catalog entry; no skill was selected. "
                f"Path: {identity.finding.path}"
            )
        else:
            self._host.jump_from_doctor(self, identity.generation, keys[0])

    def current_jump_matches(self, generation: int, key: str) -> bool:
        """Check the selected row against the published report and frozen mapping."""
        identity = self._selected_from_table()
        if identity is None or identity.generation != generation:
            return False
        snapshot = self._host.controller.current
        return (
            snapshot is not None
            and snapshot.generation == generation
            and self._finding_is_current(generation, identity.finding)
            and finding_catalog_keys(snapshot, identity.finding) == (key,)
        )

    def note_stale_jump(self) -> None:
        self.sync_from_controller()
        self.set_navigation_notice(
            "The captured report changed. Review the current finding and press Enter again."
        )

    def action_refresh(self) -> None:
        self._host.action_refresh()


def _literal(value: str) -> Content:
    return Content.from_text(value, markup=_LITERAL_MARKUP)


def _cell_width(value: str) -> int:
    return Content.from_text(value, markup=_LITERAL_MARKUP).cell_length


__all__ = [
    "DoctorScreen",
    "FindingIdentity",
    "doctor_summary",
    "finding_catalog_keys",
    "finding_detail_text",
    "finding_identities",
]
