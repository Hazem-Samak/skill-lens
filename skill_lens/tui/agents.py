"""Read-only browsing of agent definitions captured with the current session."""

from __future__ import annotations

import contextlib
from typing import ClassVar, Protocol, cast

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, VerticalScroll
from textual.content import Content
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import DataTable, Header, Static

from skill_lens.models import dumps
from skill_lens.presentation import agents_payload
from skill_lens.registry.loader import AgentDefinition
from skill_lens.tui.help import HelpContext, HelpRow
from skill_lens.tui.json_view import JsonView, session_explanation
from skill_lens.tui.session import SessionController
from skill_lens.tui.theme import KeyBar, fact_block


class _AgentsHost(Protocol):
    """The small part of the application this screen uses."""

    controller: SessionController

    def close_agents(self, screen: AgentsScreen) -> None:
        """Close this exact screen instance and resume Home."""
        ...

    def _update_ui(self) -> None:
        """Refresh session status and then synchronize the active screen."""
        ...

    def action_refresh(self) -> None:
        """Request a session refresh."""
        ...


def _cell_width(value: str) -> int:
    """Terminal cell width of a literal string (wide-character aware)."""
    return Content.from_text(value, markup=False).cell_length


def _optional(value: str | None) -> str:
    return value if value is not None else "(not declared)"


def agent_detail_text(agent: AgentDefinition) -> str:
    """Format every captured policy and root field as literal readable text."""
    lines = [
        f"Name: {agent.name}",
        f"ID: {agent.id}",
        f"Identity source: {agent.identity_source}",
        f"Collision policy: {agent.collision_policy}",
        f"Coexistence policy: {agent.coexist_policy}",
        f"Policy evidence: {agent.policy_evidence.value}",
        f"Source: {_optional(agent.source or None)}",
        f"Walk boundary: {agent.walk_boundary}",
        f"Unsearched rule: {agent.unsearched_rule_id}",
        f"Disabled rule: {_optional(agent.disabled_rule_id)}",
        f"Disabled settings: {_optional(agent.disabled_settings)}",
        f"Disabled key: {_optional(agent.disabled_key)}",
        f"Ambiguous rule: {_optional(agent.ambiguous_rule_id)}",
        "",
        f"Search roots ({len(agent.roots)}):",
    ]
    if not agent.roots:
        lines.append("  (none declared)")
    for index, root in enumerate(agent.roots, start=1):
        lines.extend(
            [
                "",
                f"Root {index}: {root.id}",
                f"  Kind: {root.kind}",
                f"  Path template: {root.path}",
                f"  Scope: {root.scope.value}",
                f"  Rank: {root.rank}",
                f"  Rule: {root.rule_id}",
                f"  Evidence: {root.evidence.value}",
                f"  Base: {root.base.value}",
                f"  Entry format: {root.entry_format.value}",
                f"  Recursive: {'yes' if root.recursive else 'no'}",
                f"  Nested rule: {_optional(root.nested_rule_id)}",
                f"  File rule: {_optional(root.file_rule_id)}",
                f"  Loadability: {_optional(root.loadability)}",
            ]
        )
    return "\n".join(lines)


class AgentsScreen(Screen[None]):
    """Browse the captured registry and inspect one definition at a time."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("enter", "focus_details", "Details", show=False),
        Binding("escape", "back", "Back", show=True),
        Binding("backspace", "back", "Back", show=False),
        Binding("J", "toggle_json", "JSON", show=True),
        Binding("q", "app.quit", "Quit", show=True),
        Binding("ctrl+c", "app.quit", "Quit", show=False, priority=True),
        Binding("r", "app.refresh", "Refresh", show=True),
    ]

    DEFAULT_CSS = """
    AgentsScreen {
        layout: vertical;
        background: $background;
    }
    #agents-title {
        height: 1;
        padding: 0 2;
        color: $muted;
        text-style: bold;
        text-align: center;
    }
    #agents-body {
        width: 1fr;
        height: 1fr;
        layout: horizontal;
    }
    #agents-table {
        width: 2fr;
        height: 1fr;
        border: round $rule;
        padding: 0 1;
    }
    #agents-detail-scroll {
        width: 3fr;
        height: 1fr;
        padding: 0 2;
        border-left: solid $rule;
    }
    #agents-detail {
        width: 1fr;
        height: auto;
    }
    #agents-empty, #agents-status, #agents-error-details {
        height: auto;
        padding: 0 2;
        color: $muted;
    }
    #agents-empty {
        color: $warning;
    }
    #agents-error-details {
        color: $error;
    }
    #agents-json {
        display: none;
    }
    AgentsScreen.json-mode #agents-json {
        display: block;
    }
    AgentsScreen.json-mode #agents-body,
    AgentsScreen.json-mode #agents-empty {
        display: none;
    }
    AgentsScreen.narrow #agents-body {
        layout: vertical;
    }
    AgentsScreen.narrow #agents-table,
    AgentsScreen.narrow #agents-detail-scroll {
        width: 1fr;
        height: 1fr;
    }
    AgentsScreen.narrow #agents-table {
        border: none;
        padding: 0;
    }
    AgentsScreen.narrow #agents-detail-scroll {
        border-left: none;
        border-top: solid $rule;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._generation: int | None = None
        self._agents: tuple[AgentDefinition, ...] = ()
        self._selected_id: str | None = None
        self._syncing = False
        self._mounting = False
        self._json_mode = False
        self._json_previous_focus: Widget | None = None
        self._json_previous_scroll = 0
        self._suspended = False
        self._help_focus: Widget | None = None
        self._help_generation: int | None = None
        self._help_detail_scroll = 0
        self._help_json_scroll = 0

    @property
    def _host(self) -> _AgentsHost:
        return cast(_AgentsHost, self.app)

    @property
    def json_mode(self) -> bool:
        return self._json_mode

    @property
    def selected_agent_id(self) -> str | None:
        return self._selected_id

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("AGENTS", id="agents-title", markup=False)
        with Horizontal(id="agents-body"):
            yield DataTable(id="agents-table")
            with VerticalScroll(id="agents-detail-scroll"):
                yield Static("No session captured.", id="agents-detail", markup=False)
        yield Static("", id="agents-empty", markup=False)
        yield JsonView(id="agents-json")
        yield Static("Initializing...", id="agents-status", markup=False)
        yield Static("", id="agents-error-details", markup=False)
        yield KeyBar()

    def on_mount(self) -> None:
        table = self.query_one("#agents-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.cell_padding = 2
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

    def on_unmount(self) -> None:
        # Agents owns no background report work; the method is here to make the
        # screen's lifecycle boundary explicit and easy to audit.
        return

    def on_screen_suspend(self) -> None:
        """A covering screen (Help) starts; no report work runs here."""
        self.suspend_help()

    def on_screen_resume(self) -> None:
        """The covering screen closed: reconcile and restore the exact view."""
        self.resume_help()

    # -- Help overlay -------------------------------------------------------

    def help_context(self) -> HelpContext:
        """Describe the ordinary table/details or raw JSON mode and its scope."""
        rows: list[HelpRow] = []
        notes: list[str] = []
        if self._json_mode:
            mode = "raw JSON view"
            focus = "JSON document"
            rows.extend(
                [
                    HelpRow(
                        "↑ ↓ / PageUp / PageDown / Home / End",
                        "Scroll the captured agents JSON payload.",
                    ),
                    HelpRow(
                        "J / Esc / Backspace",
                        "Return to the ordinary Agents view.",
                    ),
                    HelpRow(
                        "r",
                        "Refresh the captured session; this payload changes only when a"
                        " new capture is accepted.",
                    ),
                ]
            )
            notes.append("Row selection and Enter do not operate while JSON is shown.")
        else:
            mode = "captured registry browser"
            focus = "details pane" if self._details_focused() else "definitions table"
            rows.extend(
                [
                    HelpRow(
                        "↑ ↓ / j k",
                        "Move the selected definition, or scroll the details pane while"
                        " it has focus.",
                    ),
                    HelpRow(
                        "Enter",
                        "Move focus into the details pane for the selected definition.",
                    ),
                    HelpRow(
                        "J",
                        "Toggle the captured agents --json payload while the table or"
                        " details pane has focus.",
                    ),
                    HelpRow(
                        "Esc / Backspace",
                        "Leave JSON if shown, then leave the details pane for the table,"
                        " then close Agents and return to Home.",
                    ),
                ]
            )
            controller = self._host.controller
            if controller.current is None:
                notes.append("No session is captured yet; refresh to capture registry definitions.")
            elif not self._agents:
                notes.append(
                    "No agent definitions are available in this captured session."
                    " Detection is separate from registry definitions."
                )
            else:
                notes.append(
                    "Captured registry definitions are listed, including agents with"
                    " no detected skills."
                )
        return HelpContext("Agents", mode, focus, tuple(rows), tuple(notes))

    def _details_focused(self) -> bool:
        focused = self.app.focused
        return focused is not None and focused.id == "agents-detail-scroll"

    def suspend_help(self) -> None:
        """Remember the exact focus/scroll; Agents owns no report workers."""
        if self._suspended:
            return
        self._suspended = True
        controller = self._host.controller
        snapshot = controller.current
        self._help_generation = snapshot.generation if snapshot is not None else None
        self._help_focus = self.app.focused
        with contextlib.suppress(NoMatches):
            detail = self.query_one("#agents-detail-scroll", VerticalScroll)
            self._help_detail_scroll = int(detail.scroll_offset.y)
        try:
            view = self.query_one("#agents-json", JsonView)
        except NoMatches:
            view = None
        self._help_json_scroll = int(view.scroll_offset.y) if view is not None else 0

    def resume_help(self) -> None:
        """Reconcile the revealed Agents view once and restore its exact state."""
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
                self.query_one("#agents-table", DataTable).focus()
        if not same_generation:
            return
        if self._json_mode:
            try:
                view = self.query_one("#agents-json", JsonView)
            except NoMatches:
                view = None
            if view is not None and self._help_json_scroll:
                self.call_after_refresh(self._scroll_help_widget, view, self._help_json_scroll)
        elif self._help_detail_scroll:
            with contextlib.suppress(NoMatches):
                detail = self.query_one("#agents-detail-scroll", VerticalScroll)
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
        """Complete a deferred focus only while Agents is still active."""
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
        """Reconcile only from the controller's published snapshot."""
        if not self.is_mounted and not self._mounting:
            return
        if self._suspended:
            return
        controller = getattr(self._host, "controller", None)
        if controller is None:
            return
        snapshot = controller.current
        if snapshot is not None and snapshot.generation != self._generation:
            previous_id = self._selected_id
            self._generation = snapshot.generation
            self._agents = tuple(sorted(snapshot.registry, key=lambda agent: agent.id))
            by_id = {agent.id: agent for agent in self._agents}
            if previous_id in by_id:
                self._selected_id = previous_id
            else:
                self._selected_id = self._agents[0].id if self._agents else None
            self._rebuild_table()
        elif snapshot is None and self._generation is not None:
            self._generation = None
            self._agents = ()
            self._selected_id = None
            self._rebuild_table()
        if self._json_mode:
            self._refresh_json()
        self._update_detail()
        self._update_empty()
        self._update_status()

    def _rebuild_table(self) -> None:
        try:
            table = self.query_one("#agents-table", DataTable)
        except NoMatches:
            return
        self._syncing = True
        try:
            table.clear(columns=True)
            widths = self._column_widths()
            table.add_column("Agent", width=widths["name"], key="name")
            table.add_column("ID", width=widths["id"], key="id")
            table.add_column("Collision Policy", width=widths["policy"], key="policy")
            table.add_column("Evidence", width=widths["evidence"], key="evidence")
            table.add_column("Roots", width=widths["roots"], key="roots")
            for agent in self._agents:
                table.add_row(
                    Content.from_text(agent.name, markup=False),
                    Content.from_text(agent.id, markup=False),
                    Content.from_text(agent.collision_policy, markup=False),
                    Content.from_text(agent.policy_evidence.value, markup=False),
                    str(len(agent.roots)),
                    height=2,
                    key=agent.id,
                )
            if self._selected_id is not None and self._agents:
                row = next(
                    (i for i, agent in enumerate(self._agents) if agent.id == self._selected_id),
                    0,
                )
                table.move_cursor(row=row, column=0, animate=False)
        finally:
            self._syncing = False

    def _selected_agent(self) -> AgentDefinition | None:
        return next((agent for agent in self._agents if agent.id == self._selected_id), None)

    def _column_widths(self) -> dict[str, int]:
        """Explicit column widths so a value is never clipped mid-word.

        The table is narrower than the sum of its columns, so the long ones
        scroll horizontally -- but a short value such as an agent name must
        always be readable in full.
        """
        widths = {
            "name": _cell_width("Agent"),
            "id": _cell_width("ID"),
            "policy": _cell_width("Collision Policy"),
            "evidence": _cell_width("Evidence"),
            "roots": _cell_width("Roots"),
        }
        for agent in self._agents:
            widths["name"] = max(widths["name"], _cell_width(agent.name))
            widths["id"] = max(widths["id"], _cell_width(agent.id))
            widths["policy"] = max(widths["policy"], _cell_width(agent.collision_policy))
            widths["evidence"] = max(widths["evidence"], _cell_width(agent.policy_evidence.value))
            widths["roots"] = max(widths["roots"], _cell_width(str(len(agent.roots))))
        return widths

    def _update_detail(self) -> None:
        try:
            detail = self.query_one("#agents-detail", Static)
        except NoMatches:
            return
        controller = self._host.controller
        if controller.current is None:
            text = session_explanation(controller)
        elif not self._agents:
            text = "No agent definitions are available in this captured session."
        else:
            agent = self._selected_agent()
            text = agent_detail_text(agent) if agent is not None else "Choose an agent."
        detail.update(fact_block(text))

    def _update_empty(self) -> None:
        try:
            empty = self.query_one("#agents-empty", Static)
        except NoMatches:
            return
        controller = self._host.controller
        if controller.current is None:
            text = session_explanation(controller)
        elif not self._agents:
            text = "No agent definitions are available in this captured session."
        else:
            text = ""
        empty.update(Content.from_text(text, markup=False))

    def _update_status(self) -> None:
        try:
            status = self.query_one("#agents-status", Static)
            details = self.query_one("#agents-error-details", Static)
        except NoMatches:
            return
        controller = self._host.controller
        status.update(Content.from_text(session_explanation(controller), markup=False))
        error = controller.last_error_details if controller.status == "error" else ""
        details.update(Content.from_text(error or "", markup=False))

    def _refresh_json(self) -> None:
        try:
            view = self.query_one("#agents-json", JsonView)
        except NoMatches:
            return
        snapshot = self._host.controller.current
        if snapshot is None:
            view.show_explanation(session_explanation(self._host.controller))
        else:
            view.show_document(dumps(agents_payload(snapshot.registry)))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if (
            self._suspended
            or self._syncing
            or self._json_mode
            or event.data_table.id != "agents-table"
        ):
            return
        agent_id = str(event.row_key.value)
        if agent_id not in {agent.id for agent in self._agents}:
            return
        if agent_id != self._selected_id:
            self._selected_id = agent_id
            self._update_detail()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if self._suspended or self._json_mode or event.data_table.id != "agents-table":
            return
        self.action_focus_details()

    def action_cursor_down(self) -> None:
        if self._suspended or self._json_mode:
            return
        focused = self.app.focused
        if isinstance(focused, DataTable) and focused.id == "agents-table":
            focused.action_cursor_down()
        elif focused is not None and focused.id == "agents-detail-scroll":
            focused.scroll_relative(y=1, animate=False)

    def action_cursor_up(self) -> None:
        if self._suspended or self._json_mode:
            return
        focused = self.app.focused
        if isinstance(focused, DataTable) and focused.id == "agents-table":
            focused.action_cursor_up()
        elif focused is not None and focused.id == "agents-detail-scroll":
            focused.scroll_relative(y=-1, animate=False)

    def action_focus_details(self) -> None:
        if self._suspended or self._json_mode:
            return
        with contextlib.suppress(NoMatches):
            self.query_one("#agents-detail-scroll", VerticalScroll).focus()

    def action_toggle_json(self) -> None:
        if self._suspended:
            return
        if self._json_mode:
            self.leave_json_mode()
            return
        if self.app.focused is None or self.app.focused.id not in {
            "agents-table",
            "agents-detail-scroll",
        }:
            return
        self.enter_json_mode()

    def enter_json_mode(self) -> None:
        if self._suspended or self._json_mode:
            return
        table = self.query_one("#agents-table", DataTable)
        detail = self.query_one("#agents-detail-scroll", VerticalScroll)
        self._json_previous_focus = self.app.focused
        self._json_previous_scroll = detail.scroll_offset.y
        table.can_focus = False
        detail.can_focus = False
        self._json_mode = True
        self.add_class("json-mode")
        self._refresh_json()
        self.call_after_refresh(self._focus_if_active, self.query_one("#agents-json", JsonView))

    def leave_json_mode(self) -> None:
        if not self._json_mode:
            return
        self._json_mode = False
        self.remove_class("json-mode")
        table = self.query_one("#agents-table", DataTable)
        detail = self.query_one("#agents-detail-scroll", VerticalScroll)
        table.can_focus = True
        detail.can_focus = True
        previous = self._json_previous_focus
        self._json_previous_focus = None
        target = previous if previous is not None else table
        if target.is_mounted and target.can_focus and target.display:
            target.focus()
        else:
            table.focus()
        offset = self._json_previous_scroll
        self._json_previous_scroll = 0
        if offset:
            self.call_after_refresh(lambda: detail.scroll_to(y=offset, animate=False))

    def action_back(self) -> None:
        if self._suspended:
            return
        if self._json_mode:
            self.leave_json_mode()
        elif self.app.focused is not None and self.app.focused.id == "agents-detail-scroll":
            self.query_one("#agents-table", DataTable).focus()
        else:
            self._host.close_agents(self)

    def action_refresh(self) -> None:
        self._host.action_refresh()


__all__ = ["AgentsScreen", "agent_detail_text"]
