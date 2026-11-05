"""Read-only agent picker and captured pairwise comparison screen."""

from __future__ import annotations

import contextlib
from typing import ClassVar, Literal, Protocol, cast

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.content import Content
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Footer, Header, Static

from skill_lens.core.compare import validate_compare_agents
from skill_lens.core.snapshot import snapshot_path
from skill_lens.core.snapshot_models import SessionSnapshot
from skill_lens.models import dumps
from skill_lens.models.compare import CompareReport
from skill_lens.presentation import COMPARE_EMPTY_TEXT, RELATION_LABEL
from skill_lens.registry.loader import AgentDefinition
from skill_lens.tui.help import HelpContext, HelpRow
from skill_lens.tui.json_view import JsonView, session_explanation
from skill_lens.tui.session import ReportValue, SessionController, ViewName, ViewRequest

Pair = tuple[str, str]
_LOADING_TEXT = "Loading comparison…"
_NO_REPORT_TEXT = "No comparison report is available. Return to the picker and submit again."
_INTERNAL_ERROR_TEXT = "Error: Unexpected internal fault. Details in memory only."


class _CompareHost(Protocol):
    """The small application surface needed by Compare."""

    controller: SessionController

    def request_report(self, view: ViewName, arguments: tuple[str, ...]) -> ReportValue | None:
        """Return cached data or dispatch the existing report worker."""
        ...

    def close_compare(self, screen: CompareScreen) -> None:
        """Close this exact Compare screen instance and resume Home."""
        ...

    def _update_ui(self) -> None:
        """Refresh session status and then synchronize the active screen."""
        ...

    def action_refresh(self) -> None:
        """Request a session refresh."""
        ...


def _literal(text: str) -> Content:
    return Content.from_text(text, markup=False)


def _name_by_id(agents: tuple[AgentDefinition, ...], agent_id: str | None) -> str | None:
    if agent_id is None:
        return None
    agent = next((item for item in agents if item.id == agent_id), None)
    return agent.name if agent is not None else None


class CompareScreen(Screen[None]):
    """Pick two captured agent definitions and view their existing comparison."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("escape", "back", "Back", show=True),
        Binding("backspace", "back", "Back", show=False),
        Binding("J", "toggle_json", "JSON", show=True),
        Binding("q", "app.quit", "Quit", show=True),
        Binding("ctrl+c", "app.quit", "Quit", show=False, priority=True),
        Binding("r", "app.refresh", "Refresh", show=True),
    ]

    DEFAULT_CSS = """
    CompareScreen {
        layout: vertical;
    }
    #compare-title {
        height: 1;
        padding: 0 1;
        text-style: bold;
    }
    #compare-picker {
        height: 1fr;
        padding: 0 1;
    }
    #compare-columns {
        height: 1fr;
        layout: horizontal;
    }
    .compare-column {
        width: 1fr;
        height: 1fr;
    }
    #compare-column-b {
        border-left: solid $primary;
        padding-left: 1;
    }
    .compare-column-title {
        height: 1;
        text-style: bold;
    }
    #compare-a-table, #compare-b-table {
        height: 1fr;
    }
    #compare-selection, #compare-registry-message, #compare-input-error {
        height: auto;
        padding: 0 1;
    }
    #compare-registry-message, #compare-input-error {
        color: $warning;
    }
    #compare-submit {
        width: auto;
        min-width: 20;
        margin: 0 1;
    }
    #compare-result-scroll {
        height: 1fr;
        padding: 0 1;
        display: none;
    }
    #compare-result {
        height: auto;
    }
    #compare-status, #compare-error-details {
        height: auto;
        padding: 0 1;
    }
    #compare-json {
        display: none;
    }
    CompareScreen.result-mode #compare-picker {
        display: none;
    }
    CompareScreen.result-mode #compare-result-scroll {
        display: block;
    }
    CompareScreen.json-mode #compare-json {
        display: block;
    }
    CompareScreen.json-mode #compare-picker,
    CompareScreen.json-mode #compare-result-scroll {
        display: none;
    }
    CompareScreen.narrow #compare-picker {
        overflow-y: auto;
    }
    CompareScreen.narrow #compare-columns {
        layout: vertical;
    }
    CompareScreen.narrow .compare-column {
        width: 1fr;
        height: 1fr;
    }
    CompareScreen.narrow #compare-column-b {
        border-left: none;
        border-top: solid $primary;
        padding-left: 0;
        padding-top: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._mode: Literal["picker", "result"] = "picker"
        self._generation: int | None = None
        self._agents: tuple[AgentDefinition, ...] = ()
        self._selected_a: str | None = None
        self._selected_b: str | None = None
        self._highlight_a: str | None = None
        self._highlight_b: str | None = None
        self._input_error = ""
        self._submitted_pair: Pair | None = None
        self._owned_request: ViewRequest | None = None
        self._report: CompareReport | None = None
        self._report_state: Literal["idle", "loading", "ready", "error"] = "idle"
        self._report_generation: int | None = None
        self._report_pair: Pair | None = None
        self._report_error = ""
        self._syncing = False
        self._mounting = False
        self._json_mode = False
        self._json_previous_focus: Widget | None = None
        self._json_previous_scroll = 0
        self._rendered_context: tuple[object, ...] | None = None
        self._suspended = False
        self._help_focus: Widget | None = None
        self._help_generation: int | None = None
        self._help_result_scroll = 0
        self._help_picker_scroll = 0
        self._help_json_scroll = 0

    @property
    def _host(self) -> _CompareHost:
        return cast(_CompareHost, self.app)

    @property
    def mode(self) -> Literal["picker", "result"]:
        return self._mode

    @property
    def json_mode(self) -> bool:
        return self._json_mode

    @property
    def report(self) -> CompareReport | None:
        return self._report

    @property
    def selected_pair(self) -> Pair | None:
        if self._selected_a is None or self._selected_b is None:
            return None
        return (self._selected_a, self._selected_b)

    @property
    def owned_request(self) -> ViewRequest | None:
        return self._owned_request

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Compare agents", id="compare-title", markup=False)
        with Vertical(id="compare-picker"):
            with Horizontal(id="compare-columns"):
                with Vertical(classes="compare-column", id="compare-column-a"):
                    yield Static("Agent A", classes="compare-column-title", markup=False)
                    yield DataTable(id="compare-a-table")
                with Vertical(classes="compare-column", id="compare-column-b"):
                    yield Static("Agent B", classes="compare-column-title", markup=False)
                    yield DataTable(id="compare-b-table")
            yield Static(
                "A: Choose an agent    B: Choose an agent", id="compare-selection", markup=False
            )
            yield Static("", id="compare-registry-message", markup=False)
            yield Static("", id="compare-input-error", markup=False)
            yield Button("Compare", id="compare-submit", variant="primary")
        with VerticalScroll(id="compare-result-scroll"):
            yield Vertical(id="compare-result")
        yield JsonView(id="compare-json")
        yield Static("Initializing...", id="compare-status", markup=False)
        yield Static("", id="compare-error-details", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#compare-a-table", DataTable).cursor_type = "row"
        self.query_one("#compare-b-table", DataTable).cursor_type = "row"
        self._apply_width(self.size.width)
        self._mounting = True
        try:
            self.sync_from_controller()
        finally:
            self._mounting = False
        if not self._json_mode:
            self._focus_side("a")
        self.call_after_refresh(self._host._update_ui)

    def on_resize(self, event: events.Resize) -> None:
        self._apply_width(event.size.width)

    def _apply_width(self, width: int) -> None:
        self.set_class(width < 80, "narrow")

    def on_unmount(self) -> None:
        self._cancel_owned_token()

    def on_screen_suspend(self) -> None:
        """A covering screen (Help) starts: suspend this screen's own work."""
        self.suspend_help()

    def on_screen_resume(self) -> None:
        """The covering screen closed: reconcile once and restore the view."""
        self.resume_help()

    # -- Help overlay -------------------------------------------------------

    def help_context(self) -> HelpContext:
        """Describe the actual picker, result or JSON mode and its key scope."""
        rows: list[HelpRow] = []
        notes: list[str] = []
        if self._json_mode:
            mode = "raw JSON view"
            focus = "JSON document"
            rows.extend(
                [
                    HelpRow(
                        "↑ ↓ / PageUp / PageDown / Home / End",
                        "Scroll the canonical compare JSON document.",
                    ),
                    HelpRow(
                        "J / Esc / Backspace",
                        "Return to the comparison result. Esc and Backspace leave JSON"
                        " before the next Back returns to the picker.",
                    ),
                    HelpRow(
                        "r",
                        "Refresh the captured session; this document changes only when"
                        " a new capture is accepted.",
                    ),
                ]
            )
        elif self._mode == "result":
            mode = "comparison result"
            focus = "result pane"
            rows.extend(
                [
                    HelpRow(
                        "↑ ↓ / PageUp / PageDown / Home / End",
                        "Scroll the comparison result while its pane has focus.",
                    ),
                    HelpRow(
                        "J",
                        "Toggle the canonical compare --json report for the accepted ordered pair.",
                    ),
                    HelpRow(
                        "Esc / Backspace",
                        "Return to the picker. If JSON is shown, leave JSON first; Back"
                        " does not close Compare from result mode.",
                    ),
                ]
            )
        else:
            mode = "agent picker"
            focus = "picker columns"
            rows.extend(
                [
                    HelpRow(
                        "↑ ↓ / j k",
                        "Move within the focused agent column.",
                    ),
                    HelpRow(
                        "Enter",
                        "Choose the highlighted agent for A, then for B; choosing B"
                        " submits the pair when both choices are valid.",
                    ),
                    HelpRow(
                        "Esc / Backspace",
                        "Close Compare and return to Home.",
                    ),
                ]
            )
            rows.append(
                HelpRow(
                    "J",
                    "Unavailable in the picker; it applies only to result mode.",
                )
            )
            if self._host.controller.current is None:
                notes.append(
                    "No captured session is available; refresh to capture registry"
                    " definitions before comparing."
                )
            elif len(self._agents) < 2:
                notes.append(self._registry_shortfall())
            elif self._input_error:
                notes.append(self._input_error)
            else:
                notes.append(
                    "Detection is not comparison eligibility: every captured registry"
                    " definition can be chosen, even when it has no detected skills."
                )
        return HelpContext("Compare", mode, focus, tuple(rows), tuple(notes))

    def suspend_help(self) -> None:
        """Cancel only this screen's owned request and remember its exact view."""
        if self._suspended:
            return
        self._suspended = True
        controller = self._host.controller
        snapshot = controller.current
        self._help_generation = snapshot.generation if snapshot is not None else None
        self._help_focus = self.app.focused
        with contextlib.suppress(NoMatches):
            picker = self.query_one("#compare-picker", Vertical)
            self._help_picker_scroll = int(picker.scroll_offset.y)
        with contextlib.suppress(NoMatches):
            result = self.query_one("#compare-result-scroll", VerticalScroll)
            self._help_result_scroll = int(result.scroll_offset.y)
        view = self._json_view_or_none()
        self._help_json_scroll = int(view.scroll_offset.y) if view is not None else 0
        self._cancel_owned_token()

    def resume_help(self) -> None:
        """Reconcile the revealed Compare once, then restore focus and scroll."""
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
        current = controller.current
        same_generation = self._help_generation == (
            current.generation if current is not None else None
        )
        if self._mode == "result" and self._report is None and self._report_state == "loading":
            active = controller.active_requests.get("compare")
            if self._owned_request is not None and active != self._owned_request:
                self._owned_request = None
            if controller.is_failed:
                self._report_state = "error"
                self._report_error = _INTERNAL_ERROR_TEXT
                self._refresh_result()
                self._refresh_json()
            elif self._owned_request is None and self._submitted_pair is not None:
                self._request_pair(self._submitted_pair)
        self._restore_help_view(same_generation)

    def _restore_help_view(self, same_generation: bool) -> None:
        target = self._help_focus
        if target is not None and target.can_focus and target.is_mounted and target.display:
            target.focus()
        elif self._json_mode:
            view = self._json_view_or_none()
            if view is not None:
                view.focus()
        elif self._mode == "result":
            with contextlib.suppress(NoMatches):
                self.query_one("#compare-result-scroll", VerticalScroll).focus()
        else:
            self._focus_side("b" if self._selected_a is not None else "a")
        if not same_generation:
            return
        if self._json_mode:
            view = self._json_view_or_none()
            if view is not None and self._help_json_scroll:
                self.call_after_refresh(self._scroll_help_widget, view, self._help_json_scroll)
        elif self._mode == "result":
            with contextlib.suppress(NoMatches):
                result = self.query_one("#compare-result-scroll", VerticalScroll)
                if self._help_result_scroll:
                    self.call_after_refresh(
                        self._scroll_help_widget, result, self._help_result_scroll
                    )
        elif self._help_picker_scroll:
            with contextlib.suppress(NoMatches):
                picker = self.query_one("#compare-picker", Vertical)
                self.call_after_refresh(self._scroll_help_widget, picker, self._help_picker_scroll)

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
        """Complete a deferred focus only while this Compare is still active."""
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

    # -- snapshot reconciliation ------------------------------------------

    def sync_from_controller(self) -> None:
        """Update from the published registry and never reload live definitions."""
        if not self.is_mounted and not self._mounting:
            return
        if self._suspended:
            return
        controller = self._host.controller
        snapshot = controller.current
        if snapshot is not None and snapshot.generation != self._generation:
            self._on_generation(snapshot.registry, snapshot.generation)
        elif snapshot is None and self._generation is not None:
            self._on_generation((), None)
        self._refresh_picker()
        self._refresh_session_status()
        self._refresh_result()
        if self._json_mode:
            self._refresh_json()

    def _on_generation(
        self,
        registry: tuple[AgentDefinition, ...],
        generation: int | None,
    ) -> None:
        previous_pair = self._submitted_pair
        was_result = self._mode == "result"
        self._generation = generation
        self._agents = tuple(sorted(registry, key=lambda agent: agent.id))
        available = {agent.id for agent in self._agents}
        removed = [
            agent_id
            for agent_id in (self._selected_a, self._selected_b)
            if agent_id is not None and agent_id not in available
        ]
        self._selected_a = self._selected_a if self._selected_a in available else None
        self._selected_b = self._selected_b if self._selected_b in available else None
        if self._highlight_a not in available:
            self._highlight_a = self._agents[0].id if self._agents else None
        if self._highlight_b not in available:
            self._highlight_b = self._agents[0].id if self._agents else None

        # Publication already invalidated all controller requests and cache.
        # Drop every previous-generation reference before displaying new data.
        self._owned_request = None
        self._report = None
        self._report_state = "idle"
        self._report_generation = generation
        self._report_pair = None
        self._report_error = ""
        self._rendered_context = None
        # A new generation can never keep a document serialized from the old
        # report, even while the ordinary result view is currently visible.
        self._refresh_json()
        self._rebuild_tables()

        if removed:
            self._submitted_pair = None
            self._mode = "picker"
            missing = " and ".join(f"'{agent_id}'" for agent_id in removed)
            self._input_error = f"Agent {missing} was removed during refresh. Choose a replacement."
            self._set_mode_classes()
            if self._json_mode:
                self._leave_json_for_invalidation()
            self._focus_side("a" if self._selected_a is None else "b")
            return

        self._input_error = ""
        self._submitted_pair = previous_pair if was_result else None
        if self._submitted_pair is not None:
            if self._mode == "picker":
                self._mode = "result"
            self._request_pair(self._submitted_pair)
        else:
            self._mode = "picker"
            self._set_mode_classes()

    def _leave_json_for_invalidation(self) -> None:
        """Clear invalid raw report state and focus the picker in this transition."""
        view = self._json_view_or_none()
        if view is not None:
            view.show_explanation(
                self._input_error or "The selected agents changed during refresh."
            )
        self._json_mode = False
        self.remove_class("json-mode")
        self._restore_picker_focus()

    def _rebuild_tables(self) -> None:
        self._syncing = True
        try:
            for side, table_id, highlight in (
                ("a", "compare-a-table", self._highlight_a),
                ("b", "compare-b-table", self._highlight_b),
            ):
                table = self.query_one(f"#{table_id}", DataTable)
                table.clear(columns=True)
                table.add_columns("Agent", "ID")
                for agent in self._agents:
                    table.add_row(
                        _literal(agent.name),
                        _literal(agent.id),
                        key=agent.id,
                    )
                chosen = highlight or (self._agents[0].id if self._agents else None)
                if chosen is not None:
                    row = next(
                        (i for i, agent in enumerate(self._agents) if agent.id == chosen),
                        0,
                    )
                    table.move_cursor(row=row, column=0, animate=False)
                if side == "a":
                    self._highlight_a = chosen
                else:
                    self._highlight_b = chosen
        finally:
            self._syncing = False

    # -- picker ------------------------------------------------------------

    def _registry_shortfall(self) -> str:
        if self._host.controller.current is None:
            return ""
        count = len(self._agents)
        if count >= 2:
            return ""
        names = ", ".join(f"{agent.name} ({agent.id})" for agent in self._agents)
        if not names:
            names = "none"
        needed = 2 - count
        noun = "definition" if needed == 1 else "definitions"
        if count == 0:
            available = "No known agent definitions are available"
        else:
            available = "Only one known agent definition is available"
        return f"{available}: {names}. Need {needed} more {noun} to compare."

    def _refresh_picker(self) -> None:
        try:
            selection = self.query_one("#compare-selection", Static)
            registry_note = self.query_one("#compare-registry-message", Static)
            input_error = self.query_one("#compare-input-error", Static)
            submit = self.query_one("#compare-submit", Button)
        except NoMatches:
            return
        selection_text = (
            f"A: {self._selection_text(self._selected_a)}    "
            f"B: {self._selection_text(self._selected_b)}"
        )
        selection.update(Content.from_text(selection_text, markup=False))
        shortfall = self._registry_shortfall()
        registry_note.update(Content.from_text(shortfall, markup=False))
        input_error.update(Content.from_text(self._input_error, markup=False))
        submit.disabled = self._host.controller.current is None or len(self._agents) < 2

    def _selection_text(self, agent_id: str | None) -> str:
        if agent_id is None:
            return "Choose an agent"
        name = _name_by_id(self._agents, agent_id)
        if name is None:
            return f"Unknown agent ({agent_id})"
        return f"{name} ({agent_id})"

    def _focus_side(self, side: Literal["a", "b"]) -> None:
        selector = "#compare-a-table" if side == "a" else "#compare-b-table"
        with contextlib.suppress(NoMatches):
            self.query_one(selector, DataTable).focus()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if self._suspended or self._syncing or self._json_mode or self._mode != "picker":
            return
        table_id = event.data_table.id
        agent_id = str(event.row_key.value)
        if agent_id not in {agent.id for agent in self._agents}:
            return
        if table_id == "compare-a-table":
            self._highlight_a = agent_id
        elif table_id == "compare-b-table":
            self._highlight_b = agent_id

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if self._suspended or self._json_mode or self._mode != "picker":
            return
        table_id = event.data_table.id
        agent_id = str(event.row_key.value)
        if agent_id not in {agent.id for agent in self._agents}:
            return
        if table_id == "compare-a-table":
            self._selected_a = agent_id
            self._input_error = ""
            self._refresh_picker()
            self._focus_side("b")
        elif table_id == "compare-b-table":
            self._selected_b = agent_id
            self._input_error = ""
            self._refresh_picker()
            self._submit_selected()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "compare-submit" and not self._suspended and not self._json_mode:
            self._submit_selected()

    def _submit_selected(self) -> None:
        """Validate captured IDs and submit the pair without any live discovery."""
        if self._suspended or self._mode != "picker" or self._json_mode:
            return
        controller = self._host.controller
        snapshot = controller.current
        if snapshot is None:
            self._input_error = session_explanation(controller)
            self._refresh_picker()
            return
        if self._selected_a is None:
            self._input_error = "Choose an agent for A."
            self._focus_side("a")
            self._refresh_picker()
            return
        if self._selected_b is None:
            self._input_error = "Choose an agent for B."
            self._focus_side("b")
            self._refresh_picker()
            return
        registry = {agent.id: agent for agent in snapshot.registry}
        if self._selected_a not in registry or self._selected_b not in registry:
            try:
                validate_compare_agents(self._selected_a, self._selected_b, registry)
            except (KeyError, ValueError) as exc:
                self._input_error = str(exc.args[0])
            self._focus_side("a" if self._selected_a not in registry else "b")
            self._refresh_picker()
            return
        if self._selected_a == self._selected_b:
            self._input_error = "Pick two different agents."
            self._focus_side("b")
            self._refresh_picker()
            return
        pair = (self._selected_a, self._selected_b)
        self._input_error = ""
        # Clear old report and raw JSON before the new ordered pair is displayed.
        self._cancel_owned_token()
        self._report = None
        self._report_state = "idle"
        self._report_generation = snapshot.generation
        self._report_pair = pair
        self._report_error = ""
        self._submitted_pair = pair
        self._mode = "result"
        self._set_mode_classes()
        self._refresh_json()
        self._refresh_result()
        self._request_pair(pair)
        self.call_after_refresh(
            self._focus_if_active,
            self.query_one("#compare-result-scroll", VerticalScroll),
        )

    # -- report ownership --------------------------------------------------

    def _request_pair(self, pair: Pair) -> None:
        """Use the controller cache first, then retain one complete owned token."""
        if self._suspended:
            return
        controller = self._host.controller
        snapshot = controller.current
        if snapshot is None:
            return
        arguments = pair
        cached = controller.get_cached_report("compare", arguments)
        if isinstance(cached, CompareReport):
            self._cancel_owned_token()
            self._report = cached
            self._owned_request = None
            self._report_state = "ready"
            self._report_generation = snapshot.generation
            self._report_pair = pair
            self._report_error = ""
            self._refresh_result()
            self._refresh_json()
            return

        active = controller.active_requests.get("compare")
        if (
            self._owned_request is not None
            and active == self._owned_request
            and active.generation == snapshot.generation
            and active.arguments == arguments
            and self._report_state == "loading"
            and self._report_pair == pair
        ):
            return

        self._cancel_owned_token()
        self._report = None
        self._report_state = "loading"
        self._report_generation = snapshot.generation
        self._report_pair = pair
        self._report_error = ""
        self._refresh_result()
        self._refresh_json()
        result = self._host.request_report("compare", arguments)
        if isinstance(result, CompareReport):
            self._report = result
            self._report_state = "ready"
            self._owned_request = None
            self._refresh_result()
            self._refresh_json()
            return
        active_now = controller.active_requests.get("compare")
        if (
            active_now is not None
            and active_now.view == "compare"
            and active_now.generation == snapshot.generation
            and active_now.arguments == arguments
        ):
            self._owned_request = active_now
        else:
            self._owned_request = None
            self._report_state = "idle"
        self._refresh_result()
        self._refresh_json()

    def _cancel_owned_token(self) -> None:
        owned = self._owned_request
        self._owned_request = None
        if owned is None:
            return
        active = self._host.controller.active_requests.get("compare")
        if active == owned:
            self._host.controller.invalidate_view("compare")

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
        """Accept only the active screen's exact request for its current pair."""
        if not self.is_mounted or self._suspended or view != "compare":
            return
        owned = self._owned_request
        if owned is None:
            return
        if (
            owned.request_id != request_id
            or owned.generation != generation
            or owned.view != view
            or owned.arguments != arguments
            or self._submitted_pair != arguments
            or self._mode != "result"
        ):
            return
        if accepted and isinstance(report, CompareReport):
            self._report = report
            self._owned_request = None
            self._report_state = "ready"
            self._report_generation = generation
            self._report_pair = (arguments[0], arguments[1])
            self._report_error = ""
        elif accepted:
            self._report = None
            self._owned_request = None
            self._report_state = "error"
            self._report_generation = generation
            self._report_pair = (arguments[0], arguments[1])
            self._report_error = _INTERNAL_ERROR_TEXT
        else:
            active = self._host.controller.active_requests.get("compare")
            if active != owned:
                self._owned_request = None
                self._report_state = "idle"
                self._report_error = (
                    "The comparison request ended before a report was accepted. Submit again "
                    "to retry."
                )
        self._refresh_result()
        self._refresh_json()

    # -- result rendering / JSON ------------------------------------------

    def _set_mode_classes(self) -> None:
        self.set_class(self._mode == "result", "result-mode")
        self.set_class(self._json_mode, "json-mode")

    def _refresh_result(self) -> None:
        try:
            container = self.query_one("#compare-result", Vertical)
        except NoMatches:
            return
        pair = self._report_pair or self._submitted_pair
        context = (
            self._generation,
            pair,
            id(self._report) if self._report is not None else None,
            self._report_state,
            self._report_error,
        )
        if context == self._rendered_context:
            return
        container.remove_children()
        report = self._report
        snapshot = self._host.controller.current
        if self._mode != "result":
            self._rendered_context = context
            return
        if report is None or snapshot is None:
            if self._report_state == "loading":
                placeholder = _LOADING_TEXT
            elif self._report_state == "error":
                placeholder = self._report_error or _INTERNAL_ERROR_TEXT
            elif self._report_error:
                placeholder = self._report_error
            elif snapshot is None:
                placeholder = session_explanation(self._host.controller)
            else:
                placeholder = _NO_REPORT_TEXT
            container.mount(Static(_literal(placeholder), markup=False))
            self._rendered_context = context
            return
        container.mount(*self._report_blocks(report, snapshot))
        self._rendered_context = context

    def _report_blocks(self, report: CompareReport, snapshot: SessionSnapshot) -> list[Static]:
        counts = report.counts_by_relation()
        header = "\n".join(
            [
                f"A: {report.agent_a_name} ({report.agent_a})",
                f"B: {report.agent_b_name} ({report.agent_b})",
                "  ".join(
                    [
                        f"Shared: {counts['shared']}",
                        f"Diverged: {counts['diverged']}",
                        f"A only: {counts['only_a']}",
                        f"B only: {counts['only_b']}",
                    ]
                ),
            ]
        )
        blocks = [Static(_literal(header), classes="compare-summary", markup=False)]
        if not report.entries:
            blocks.append(
                Static(_literal(COMPARE_EMPTY_TEXT), classes="compare-empty", markup=False)
            )
        else:
            for entry in report.entries:
                label, style = RELATION_LABEL[entry.relation]
                path_a = snapshot_path(snapshot, entry.path_a) if entry.path_a else "-"
                path_b = snapshot_path(snapshot, entry.path_b) if entry.path_b else "-"
                lines = [
                    Content.assemble(Content.styled("Skill: ", "bold"), _literal(entry.name)),
                    Content.assemble(
                        Content.styled("Relation: ", "bold"),
                        Content.styled(label, style),
                    ),
                    Content.assemble(Content.styled("Path A: ", "bold"), _literal(path_a)),
                    Content.assemble(Content.styled("Path B: ", "bold"), _literal(path_b)),
                ]
                blocks.append(
                    Static(
                        Content("\n").join(lines),
                        classes="compare-entry",
                        markup=False,
                    )
                )
        if report.notes:
            note_lines = [
                Content.assemble(Content.styled("Note: ", "yellow"), _literal(note))
                for note in report.notes
            ]
            blocks.append(
                Static(
                    Content("\n").join(note_lines),
                    classes="compare-notes",
                    markup=False,
                )
            )
        return blocks

    def _result_text(self) -> str:
        if self._report_state == "loading":
            return _LOADING_TEXT
        if self._report_state == "error":
            return self._report_error or _INTERNAL_ERROR_TEXT
        if self._report_error:
            return self._report_error
        if self._host.controller.current is None:
            return session_explanation(self._host.controller)
        return _NO_REPORT_TEXT

    def _refresh_json(self) -> None:
        view = self._json_view_or_none()
        if view is None:
            return
        if self._report is not None and self._report_state == "ready":
            view.show_document(dumps(self._report.to_dict()))
        else:
            view.show_explanation(self._result_text())

    def _json_view_or_none(self) -> JsonView | None:
        try:
            return self.query_one("#compare-json", JsonView)
        except NoMatches:
            return None

    def _refresh_session_status(self) -> None:
        try:
            status = self.query_one("#compare-status", Static)
            details = self.query_one("#compare-error-details", Static)
        except NoMatches:
            return
        controller = self._host.controller
        status.update(Content.from_text(session_explanation(controller), markup=False))
        error = controller.last_error_details if controller.status == "error" else ""
        details.update(Content.from_text(error or "", markup=False))

    def action_toggle_json(self) -> None:
        if self._suspended or self._mode != "result":
            return
        if self._json_mode:
            self.leave_json_mode()
        else:
            self.enter_json_mode()

    def enter_json_mode(self) -> None:
        if self._suspended or self._mode != "result" or self._json_mode:
            return
        picker = self.query_one("#compare-picker", Vertical)
        result = self.query_one("#compare-result-scroll", VerticalScroll)
        self._json_previous_focus = self.app.focused
        self._json_previous_scroll = result.scroll_offset.y
        picker.can_focus = False
        result.can_focus = False
        for table_id in ("#compare-a-table", "#compare-b-table"):
            self.query_one(table_id, DataTable).can_focus = False
        self.query_one("#compare-submit", Button).can_focus = False
        self._json_mode = True
        self._set_mode_classes()
        self._refresh_json()
        view = self._json_view_or_none()
        if view is not None:
            self.call_after_refresh(self._focus_if_active, view)

    def leave_json_mode(self) -> None:
        if not self._json_mode:
            return
        self._json_mode = False
        self._set_mode_classes()
        self._restore_picker_focus()
        result = self.query_one("#compare-result-scroll", VerticalScroll)
        offset = self._json_previous_scroll
        self._json_previous_scroll = 0
        if offset:
            self.call_after_refresh(lambda: result.scroll_to(y=offset, animate=False))

    def _restore_picker_focus(self) -> None:
        self.query_one("#compare-picker", Vertical).can_focus = True
        self.query_one("#compare-result-scroll", VerticalScroll).can_focus = True
        self.query_one("#compare-a-table", DataTable).can_focus = True
        self.query_one("#compare-b-table", DataTable).can_focus = True
        self.query_one("#compare-submit", Button).can_focus = True
        previous = self._json_previous_focus
        self._json_previous_focus = None
        if previous is not None and previous.is_mounted and previous.can_focus and previous.display:
            previous.focus()
        elif self._mode == "picker":
            self._focus_side("b" if self._selected_a is not None else "a")
        else:
            self.query_one("#compare-result-scroll", VerticalScroll).focus()

    # -- keyboard ----------------------------------------------------------

    def action_cursor_down(self) -> None:
        if self._suspended or self._json_mode or self._mode != "picker":
            return
        focused = self.app.focused
        if isinstance(focused, DataTable) and focused.id in {
            "compare-a-table",
            "compare-b-table",
        }:
            focused.action_cursor_down()

    def action_cursor_up(self) -> None:
        if self._suspended or self._json_mode or self._mode != "picker":
            return
        focused = self.app.focused
        if isinstance(focused, DataTable) and focused.id in {
            "compare-a-table",
            "compare-b-table",
        }:
            focused.action_cursor_up()

    def action_back(self) -> None:
        if self._suspended:
            return
        if self._json_mode:
            self.leave_json_mode()
        elif self._mode == "result":
            self._cancel_owned_token()
            self._mode = "picker"
            self._submitted_pair = None
            self._report = None
            self._report_state = "idle"
            self._report_generation = self._generation
            self._report_pair = None
            self._report_error = ""
            self._rendered_context = None
            self._set_mode_classes()
            self._refresh_result()
            self._refresh_json()
            self._refresh_picker()
            self._focus_side("b")
        else:
            self._host.close_compare(self)

    def action_refresh(self) -> None:
        self._host.action_refresh()


__all__ = ["CompareScreen"]
