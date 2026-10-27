"""Read-only Home browsing screen for Skill Lens (Assignment U3).

Specification reference: FULL_SCREEN_TUI.md §8.2-8.3, §8.5, §9.1, §21.7,
Step 3 and §22 U3.

The screen renders one row per canonical installation from the already captured
``SessionSnapshot``.  It never reads files, resolves paths or runs discovery
while browsing.  Resolution states are requested only for the one agent named
by the agent filter and only for the lookup-name groups that are actually
visible.

The module is deliberately Textual-only: it imports shared plain presentation
helpers but never ``skill_lens.render`` or ``rich``.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Protocol, cast

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.content import Content
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Static
from textual.widgets.data_table import CellDoesNotExist

from skill_lens.core.discovery import DiscoveredEntry, canonical_key
from skill_lens.core.resolver import lookup_name_for_entry
from skill_lens.core.snapshot_models import SessionSnapshot
from skill_lens.models.enums import ParseStatus
from skill_lens.models.resolution import ResolutionReport
from skill_lens.presentation.state import SCOPE_LABEL
from skill_lens.registry.loader import AgentDefinition
from skill_lens.tui.session import ReportValue, SessionController, ViewName, ViewRequest

if TYPE_CHECKING:
    from collections.abc import Sequence

ALL_AGENTS = "All agents"
_LITERAL_CELL_MARKUP = False
_NO_AGENT_MESSAGE = "No agents detected. Showing every discovered skill."


class _ReportHost(Protocol):
    """The small part of :class:`SkillLensApp` this screen needs."""

    controller: SessionController

    def request_report(self, view: ViewName, arguments: tuple[str, ...]) -> ReportValue | None:
        """Return a cached report or start the existing report worker."""
        ...

    def _update_ui(self) -> None:
        """Ask the host app to refresh its status/error presentation."""
        ...

    def open_why(self, key: str, agent_id: str | None) -> None:
        """Open a Why screen for the given installation key and agent."""
        ...


@dataclass(frozen=True, slots=True)
class AgentOption:
    """One entry in the cyclic agent filter."""

    agent_id: str | None
    label: str


@dataclass(frozen=True, slots=True)
class HomeRow:
    """Immutable view model for one canonical installation."""

    key: str
    name: str
    description: str | None
    scope_label: str
    parse_status: str
    parse_mark: str
    agents: tuple[str, ...]
    content_hash: str | None
    variant_label: str | None
    display_path: str
    health_label: str
    search_text: str


@dataclass(slots=True)
class _Group:
    """Per-generation/agent state for one distinct lookup name."""

    lookup_name: str
    representative_key: str
    status: Literal["pending", "loading", "done", "unavailable"] = "pending"
    report: ResolutionReport | None = None


@dataclass(frozen=True, slots=True)
class _OwnedWhy:
    """The exact controller request currently owned by this screen."""

    lookup_name: str
    request: ViewRequest


def _parse_mark(parse_status: str) -> str:
    """Return the compact parse mark: ``*`` valid, ``x`` anything else."""
    return "*" if parse_status == ParseStatus.VALID.value else "x"


def _health_label(entry_health: Any) -> str:
    """A literal, plain-English health summary from captured scan fields."""
    code = str(getattr(entry_health, "code", "ok"))
    severity = getattr(entry_health, "severity", None)
    reason = getattr(entry_health, "reason", None)
    clause = getattr(entry_health, "clause", "")
    if severity is None and code == "ok":
        return "ok"
    parts = [code]
    if reason:
        parts.append(f"({reason})")
    if clause:
        parts.append(f"- {clause}")
    return " ".join(parts)


def build_home_rows(snapshot: SessionSnapshot) -> tuple[HomeRow, ...]:
    """Build immutable Home rows from the captured scan report.

    Order follows :attr:`ScanReport.skills` exactly.  The row key is the same
    canonical key used by discovery, the controller and ``snapshot_why``.
    """
    rows: list[HomeRow] = []
    display_paths = snapshot.display_paths
    for entry in snapshot.scan.skills:
        description = entry.description
        rows.append(
            HomeRow(
                key=entry.canonical_path,
                name=entry.name,
                description=description,
                scope_label=SCOPE_LABEL.get(entry.scope, entry.scope.value),
                parse_status=entry.parse_status,
                parse_mark=_parse_mark(entry.parse_status),
                agents=tuple(entry.agents),
                content_hash=entry.content_hash,
                variant_label=entry.variant_label,
                display_path=display_paths.get(entry.canonical_path, entry.canonical_path),
                health_label=_health_label(entry.condition),
                search_text=f"{entry.name}\n{description or ''}".casefold(),
            )
        )
    return tuple(rows)


def detected_agent_ids(snapshot: SessionSnapshot) -> tuple[str, ...]:
    """Detected agent IDs in the deterministic order the filter cycles."""
    detected = set(snapshot.scan.summary.detected_agents)
    detected.update(agent_id for row in snapshot.scan.skills for agent_id in row.agents)
    return tuple(sorted(detected))


def _registry_by_id(snapshot: SessionSnapshot) -> dict[str, AgentDefinition]:
    return {agent.id: agent for agent in snapshot.registry}


def agent_display_name(snapshot: SessionSnapshot, agent_id: str) -> str:
    """Captured registry display name for an agent ID, falling back to the ID."""
    agent = _registry_by_id(snapshot).get(agent_id)
    return agent.name if agent is not None else agent_id


def build_agent_options(snapshot: SessionSnapshot) -> tuple[AgentOption, ...]:
    """``All agents`` followed by detected agent IDs in sorted order."""
    options = [AgentOption(None, ALL_AGENTS)]
    options.extend(
        AgentOption(agent_id, agent_display_name(snapshot, agent_id))
        for agent_id in detected_agent_ids(snapshot)
    )
    return tuple(options)


def filter_home_rows(
    rows: Sequence[HomeRow],
    query: str,
    agent_id: str | None,
) -> tuple[HomeRow, ...]:
    """Apply the combined case-insensitive text and agent filters."""
    needle = query.strip().casefold()
    return tuple(
        row
        for row in rows
        if (not needle or needle in row.search_text)
        and (agent_id is None or agent_id in row.agents)
    )


def resolution_text(report: ResolutionReport, row_key: str) -> str:
    """Per-copy state text for one row, never a name-wide headline.

    Candidates are matched by installation canonical path.  For an unresolved
    copy (dangling link, cycle) the row key is the entrypoint path, so that is
    used as the fallback.  Several entrypoints of one installation can yield
    different states; all distinct labels are shown rather than choosing a
    synthetic winner.
    """
    matches = [
        candidate
        for candidate in report.candidates
        if candidate.installation.canonical_path == row_key
    ]
    if not matches:
        matches = [
            candidate
            for candidate in report.candidates
            if candidate.installation.entrypoint_path == row_key
        ]
    if not matches:
        return "unknown"
    states: list[str] = []
    for candidate in matches:
        state = candidate.state.value
        if state not in states:
            states.append(state)
    return ", ".join(states)


def preview_text(row: HomeRow, snapshot: SessionSnapshot) -> str:
    """Plain literal metadata preview for one selected row."""
    agent_names = [agent_display_name(snapshot, agent_id) for agent_id in row.agents]
    agents = ", ".join(agent_names) if agent_names else "none"
    variant = row.variant_label or "-"
    description = row.description if row.description is not None else "(no description)"
    return "\n".join(
        [
            f"Name: {row.name}",
            f"Scope: {row.scope_label}",
            f"Path: {row.display_path}",
            f"Agents: {agents} ({len(agent_names)})",
            f"Hash: {row.content_hash or 'none'}",
            f"Parse: {row.parse_status} ({row.parse_mark})",
            f"Variant: {variant}",
            f"Health: {row.health_label}",
            "",
            "Description:",
            description,
        ]
    )


def _cell(value: str) -> Content:
    """A literal cell value that can never be interpreted as Rich markup."""
    return Content.from_text(value, markup=_LITERAL_CELL_MARKUP)


def _display_width(value: str) -> int:
    """Terminal cell width of a literal string (wide-character aware).

    ``Content`` is deliberately not measurable by Textual's ``measure``
    helper (it exposes no ``__rich_measure__``), so DataTable auto-width leaves
    literal cells at the header width.  We size columns explicitly from this.
    """
    return Content.from_text(value, markup=_LITERAL_CELL_MARKUP).cell_length


class HomeScreen(Screen[None]):
    """The U3 read-only Home screen: skill table, preview, filters and status."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("slash", "focus_filter", "Filter", show=False),
        Binding("a", "cycle_agent", "Agent", show=False),
        Binding("escape", "clear_filter", "Clear filter", show=False),
        Binding("enter", "open_why", "Why", show=False),
    ]

    DEFAULT_CSS = """
    HomeScreen {
        layout: vertical;
    }
    #home-title {
        height: 1;
        padding: 0 1;
        text-style: bold;
    }
    #filter-strip {
        height: auto;
        layout: horizontal;
        padding: 0 1;
    }
    #filter-input {
        width: 1fr;
    }
    #agent-filter {
        width: auto;
        min-width: 22;
        padding: 0 1;
    }
    #legend {
        height: auto;
        padding: 0 1;
        color: $text-muted;
    }
    #home-body {
        height: 1fr;
        layout: horizontal;
    }
    #skill-table {
        width: 3fr;
        height: 1fr;
    }
    #preview-scroll {
        width: 2fr;
        height: 1fr;
        padding: 0 1;
        border-left: solid $primary;
    }
    #preview-pane {
        width: 1fr;
        height: auto;
    }
    #empty-state {
        height: auto;
        padding: 0 1;
        color: $warning;
    }
    #catalog-note {
        height: auto;
        padding: 0 1;
        color: $warning;
    }
    #status-text {
        height: auto;
        padding: 0 1;
    }
    #error-details {
        height: auto;
        padding: 0 1;
    }
    #removal-notice {
        height: auto;
        padding: 0 1;
        color: $warning;
    }
    #footer-help {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    HomeScreen.narrow #home-body {
        layout: vertical;
    }
    HomeScreen.narrow #skill-table {
        width: 1fr;
    }
    HomeScreen.narrow #preview-scroll {
        width: 1fr;
        height: 1fr;
        border-left: none;
        border-top: solid $primary;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._controller: SessionController | None = None
        self._generation: int | None = None
        self._rows: tuple[HomeRow, ...] = ()
        self._visible: tuple[HomeRow, ...] = ()
        self._entry_by_key: dict[str, DiscoveredEntry] = {}
        self._agent_options: tuple[AgentOption, ...] = (AgentOption(None, ALL_AGENTS),)
        self._agent_index = 0
        self._agent_id: str | None = None
        self._lookup_by_key: dict[str, str] = {}
        self._groups: dict[str, _Group] = {}
        self._inflight: _OwnedWhy | None = None
        self._syncing = False
        self._last_query = ""
        self._suspended = False
        self._removal_notice: str | None = None

    # -- lifecycle ---------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Skill Lens Home", id="home-title", markup=False)
        with Vertical(id="filter-strip"):
            yield Input(placeholder="Filter by name or description  (/)", id="filter-input")
            yield Static(f"Agent: {ALL_AGENTS}", id="agent-filter", markup=False)
        yield Static(
            "Parse: * valid, x invalid.  State appears only while an agent filter is active.",
            id="legend",
            markup=False,
        )
        with Horizontal(id="home-body"):
            yield DataTable(id="skill-table")
            with VerticalScroll(id="preview-scroll"):
                yield Static("", id="preview-pane", markup=False)
        yield Static("", id="empty-state", markup=False)
        yield Static("", id="catalog-note", markup=False)
        yield Static("Initializing...", id="status-text", markup=False)
        yield Static("", id="error-details", markup=False)
        yield Static("", id="removal-notice", markup=False)
        yield Static(
            "q: Quit   r: Refresh   /: Filter   a: Agent   Enter: Why   Tab: Focus",
            id="footer-help",
            markup=False,
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#skill-table", DataTable)
        table.cursor_type = "row"
        table.focus()
        self._apply_width(self.size.width)
        self.sync_from_controller()
        self._host._update_ui()

    def on_resize(self, event: events.Resize) -> None:
        self._apply_width(event.size.width)

    def _apply_width(self, width: int) -> None:
        """Stack the panes on narrow terminals so every control stays usable."""
        self.set_class(width < 80, "narrow")

    def on_unmount(self) -> None:
        self._cancel_owned_why()

    # -- app integration ---------------------------------------------------

    @property
    def _host(self) -> _ReportHost:
        return cast(_ReportHost, self.app)

    def _controller_or_none(self) -> SessionController | None:
        return getattr(self._host, "controller", None)

    def suspend_why(self) -> None:
        """Suspend Home screen activity while detail screen is active."""
        self._suspended = True
        self._cancel_owned_why()

    def on_screen_resume(self) -> None:
        """Handle Textual ScreenResume event when detail screen pops."""
        if self._suspended:
            self.resume_why()
        else:
            try:
                table = self.query_one("#skill-table", DataTable)
                table.focus()
            except NoMatches:
                pass

    def resume_why(self) -> None:
        """Resume Home screen activity after returning from detail."""
        self._suspended = False
        if not self.is_mounted:
            return
        self.sync_from_controller()
        if self.app.screen is self:
            try:
                table = self.query_one("#skill-table", DataTable)
                table.focus()
            except NoMatches:
                pass

    def set_removal_notice(self, notice: str | None) -> None:
        """Set the notice displayed when a detail installation was removed."""
        self._removal_notice = notice
        with contextlib.suppress(NoMatches):
            self.query_one("#removal-notice", Static).update(notice or "")

    def clear_removal_notice(self) -> None:
        """Clear removal notice on explicit user navigation or action."""
        self._clear_removal_notice()

    def _clear_removal_notice(self) -> None:
        """Clear removal notice on explicit user navigation or action."""
        if self._removal_notice is not None:
            self._removal_notice = None
            with contextlib.suppress(NoMatches):
                self.query_one("#removal-notice", Static).update("")

    def sync_from_controller(self) -> None:
        """Reconcile the screen with the controller's published session."""
        if not self.is_mounted or self._suspended:
            return
        controller = self._controller_or_none()
        if controller is None:
            return
        self._controller = controller
        snapshot = controller.current
        if snapshot is None:
            self._visible = ()
            self._rows = ()
            self._clear_table()
            self._update_empty_state()
            self._update_preview()
            self._update_catalog_note()
            return

        if snapshot.generation != self._generation:
            self._reset_for_generation(snapshot)
        else:
            self._ensure_selection()
            self._update_preview()
            self._update_empty_state()
            self._update_catalog_note()
            self._drive()

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
        """Consume an accepted Home Why result, or merely wake after rejection."""
        if not self.is_mounted or self._suspended or view != "why":
            return
        controller = self._controller_or_none()
        if controller is None:
            return
        owned = self._inflight
        if owned is not None:
            request = owned.request
            identity_matches = (
                request.request_id == request_id
                and request.generation == generation
                and request.view == view
                and request.arguments == arguments
            )
            if identity_matches:
                group = self._groups.get(owned.lookup_name)
                if accepted and isinstance(report, ResolutionReport):
                    if group is not None:
                        group.report = report
                        group.status = "done"
                    self._inflight = None
                elif accepted:
                    if group is not None:
                        group.report = None
                        group.status = "unavailable"
                    self._inflight = None
                else:
                    # A rejected owned request no longer belongs to any newer
                    # token.  Clear it only if the controller really dropped it.
                    active = controller.active_requests.get("why")
                    if active is None or active != request:
                        if group is not None and group.status == "loading":
                            group.status = "pending"
                        self._inflight = None
                self._render_group_cells(owned.lookup_name)
            elif not accepted:
                # Rejected data for someone else's token must never clear or
                # mark the newer owned token.
                pass
        self._drive()

    # -- generation / filtering -------------------------------------------

    def _reset_for_generation(self, snapshot: SessionSnapshot) -> None:
        controller = self._host.controller
        self._generation = snapshot.generation
        self._rows = build_home_rows(snapshot)
        self._entry_by_key = {canonical_key(entry): entry for entry in snapshot.index.entries}
        self._agent_options = build_agent_options(snapshot)
        self._inflight = None
        self._groups = {}
        self._lookup_by_key = {}
        self._agent_index = self._resolve_agent_index()
        self._agent_id = self._agent_options[self._agent_index].agent_id
        self._refresh_lookup_map()
        self._apply_filters(reason="generation")
        # The controller's publication already chose a row; keep it only when
        # the current filter still shows it.
        if controller.selected_key not in {row.key for row in self._visible}:
            new_key = self._visible[0].key if self._visible else None
            controller.set_selected_key(new_key)
        self._abandon_invalid_token()
        self._sync_table_cursor()
        self._update_preview()
        self._update_empty_state()
        self._update_catalog_note()
        self._update_agent_widgets()
        self._drive()

    def _resolve_agent_index(self) -> int:
        if self._agent_id is None:
            return 0
        for index, option in enumerate(self._agent_options):
            if option.agent_id == self._agent_id:
                return index
        return 0

    def _refresh_lookup_map(self) -> None:
        self._lookup_by_key = {}
        if self._agent_id is None:
            return
        snapshot = self._host.controller.current
        if snapshot is None:
            return
        agents = _registry_by_id(snapshot)
        agent = agents.get(self._agent_id)
        if agent is None:
            return
        for row in self._visible:
            entry = self._entry_by_key.get(row.key)
            if entry is None:
                continue
            self._lookup_by_key[row.key] = lookup_name_for_entry(entry, agent)

    def _apply_filters(self, *, reason: str) -> None:
        if self._suspended:
            return
        controller = self._host.controller
        query_widget = self.query_one("#filter-input", Input)
        query = query_widget.value
        self._last_query = query
        self._visible = filter_home_rows(self._rows, query, self._agent_id)
        self._refresh_lookup_map()
        self._ensure_groups()
        previous = controller.selected_key
        visible_keys = {row.key for row in self._visible}
        if previous not in visible_keys:
            controller.set_selected_key(self._visible[0].key if self._visible else None)
        self._rebuild_table()
        self._abandon_invalid_token()
        if reason == "agent":
            self._update_agent_widgets()
        self._sync_table_cursor()
        self._update_preview()
        self._update_empty_state()
        self._update_catalog_note()
        self._drive()

    def _ensure_groups(self) -> None:
        if self._agent_id is None:
            self._groups = {}
            return
        visible_groups: dict[str, str] = {}
        for row in self._visible:
            lookup = self._lookup_by_key.get(row.key)
            if lookup is None:
                continue
            if lookup not in visible_groups:
                visible_groups[lookup] = row.key
        for lookup, representative in visible_groups.items():
            group = self._groups.get(lookup)
            if group is None:
                self._groups[lookup] = _Group(lookup, representative)
            else:
                group.representative_key = representative
        for lookup in tuple(self._groups):
            if lookup not in visible_groups:
                group = self._groups[lookup]
                if (
                    group.status == "loading"
                    and self._inflight is not None
                    and self._inflight.lookup_name == lookup
                ):
                    self._cancel_owned_why()
                if group.status != "done":
                    del self._groups[lookup]

    def _ensure_selection(self) -> None:
        if self._suspended:
            return
        controller = self._host.controller
        visible_keys = {row.key for row in self._visible}
        selected = controller.selected_key
        if selected in visible_keys:
            return
        new_key = self._visible[0].key if self._visible else None
        controller.set_selected_key(new_key)

    # -- table -------------------------------------------------------------

    def _clear_table(self) -> None:
        try:
            table = self.query_one("#skill-table", DataTable)
        except NoMatches:
            # The table is only absent while the screen is being torn down.
            return
        self._syncing = True
        try:
            table.clear(columns=True)
        finally:
            self._syncing = False

    def _rebuild_table(self) -> None:
        table = self.query_one("#skill-table", DataTable)
        widths = self._column_widths()
        self._syncing = True
        try:
            table.clear(columns=True)
            table.add_column("Name", width=widths["name"], key="name")
            table.add_column("Scope", width=widths["scope"], key="scope")
            table.add_column("Parse", width=widths["parse"], key="parse")
            if self._agent_id is not None:
                table.add_column("State", width=widths["state"], key="state")
            for row in self._visible:
                cells = [
                    _cell(row.name),
                    _cell(row.scope_label),
                    _cell(row.parse_mark),
                ]
                if self._agent_id is not None:
                    cells.append(_cell(self._group_mark(row.key)))
                table.add_row(*cells, key=row.key)
        finally:
            self._syncing = False
        self._update_agent_widgets()

    def _column_widths(self) -> dict[str, int]:
        """Explicit column widths so literal cells are never header-clipped.

        DataTable auto-width cannot measure ``Content`` cells, so we compute the
        widest label/value ourselves.  A wider-than-viewport table scrolls
        horizontally, which is the honest way to show genuinely long data.
        """
        widths = {
            "name": _display_width("Name"),
            "scope": _display_width("Scope"),
            "parse": _display_width("Parse"),
            "state": _display_width("State"),
        }
        for row in self._visible:
            widths["name"] = max(widths["name"], _display_width(row.name))
            widths["scope"] = max(widths["scope"], _display_width(row.scope_label))
            widths["parse"] = max(widths["parse"], _display_width(row.parse_mark))
            if self._agent_id is not None:
                widths["state"] = max(widths["state"], _display_width(self._group_mark(row.key)))
        return widths

    def _sync_table_cursor(self) -> None:
        table = self.query_one("#skill-table", DataTable)
        if table.row_count == 0:
            return
        selected = self._host.controller.selected_key
        index = next(
            (position for position, row in enumerate(self._visible) if row.key == selected),
            0,
        )
        if table.cursor_row != index:
            self._syncing = True
            try:
                table.move_cursor(row=index)
            finally:
                self._syncing = False
        self._syncing = True
        try:
            table.refresh_row(index)
        finally:
            self._syncing = False

    def _group_mark(self, row_key: str) -> str:
        lookup = self._lookup_by_key.get(row_key)
        if lookup is None:
            return "unknown"
        group = self._groups.get(lookup)
        if group is None:
            return "pending"
        if group.status == "done" and group.report is not None:
            return resolution_text(group.report, row_key)
        if group.status == "unavailable":
            return "unavailable"
        if group.status == "loading":
            return "pending"
        return "pending"

    def _set_state_cell(self, row_key: str, value: str) -> None:
        table = self.query_one("#skill-table", DataTable)
        if self._agent_id is None or value == "":
            return
        grew = self._grow_state_column(value)
        try:
            # ``update_width`` is only needed when the column grew, which keeps
            # the dimension recompute off the per-result hot path.
            table.update_cell(row_key, "state", _cell(value), update_width=grew)
        except CellDoesNotExist:
            # Expected: the row or state column was filtered out or rebuilt
            # between the report event and this update.  Any other exception is
            # an unexpected fault and must reach the app's containment path.
            return

    def _grow_state_column(self, value: str) -> bool:
        """Grow the fixed State column so a newer, longer label stays readable."""
        table = self.query_one("#skill-table", DataTable)
        needed = _display_width(value)
        for column_key, column in table.columns.items():
            if column_key == "state":
                if needed > column.width:
                    column.width = needed
                    return True
                return False
        return False

    def _render_group_cells(self, lookup_name: str) -> None:
        for row in self._visible:
            if self._lookup_by_key.get(row.key) == lookup_name:
                self._set_state_cell(row.key, self._group_mark(row.key))

    # -- preview / empty states -------------------------------------------

    def _selected_row(self) -> HomeRow | None:
        selected = self._host.controller.selected_key
        for row in self._visible:
            if row.key == selected:
                return row
        return None

    def _update_preview(self) -> None:
        preview = self.query_one("#preview-pane", Static)
        row = self._selected_row()
        snapshot = self._host.controller.current
        if row is None or snapshot is None:
            preview.update("")
            return
        preview.update(preview_text(row, snapshot))

    def _update_empty_state(self) -> None:
        empty = self.query_one("#empty-state", Static)
        controller = self._host.controller
        if not self._rows:
            if controller.current is None or controller.status in {
                "idle",
                "loading",
                "retry",
                "refused",
                "error",
            }:
                empty.update("")
            else:
                empty.update("No skills discovered in this session. Press r to refresh.")
            return
        if not self._visible:
            empty.update("No skills match the current filter.")
            return
        empty.update("")

    def _update_catalog_note(self) -> None:
        note = self.query_one("#catalog-note", Static)
        snapshot = self._host.controller.current
        if snapshot is None:
            note.update("")
            return
        unreadable = snapshot.scan.unreadable
        if not unreadable:
            note.update("")
            return
        parts = []
        for item in unreadable:
            agent = item.get("agent", "?")
            root = item.get("root", "?")
            path = item.get("path", "?")
            detail = item.get("detail", "unreadable")
            parts.append(f"{agent}/{root} {path} ({detail})")
        note.update("Unreadable roots: " + "; ".join(parts))

    def _update_agent_widgets(self) -> None:
        agent_widget = self.query_one("#agent-filter", Static)
        legend = self.query_one("#legend", Static)
        if self._agent_id is None:
            if len(self._agent_options) <= 1:
                agent_widget.update(f"Agent: {ALL_AGENTS} (no agents detected)")
                legend.update(_NO_AGENT_MESSAGE)
            else:
                agent_widget.update(f"Agent: {ALL_AGENTS}")
                legend.update(
                    "Parse: * valid, x invalid.  State appears only while an "
                    "agent filter is active."
                )
            return
        label = self._agent_options[self._agent_index].label
        agent_widget.update(f"Agent: {label} ({self._agent_id})")
        legend.update("State: per-agent resolution for this filter.  Parse: * valid, x invalid.")

    # -- Why queue ---------------------------------------------------------

    def _drive(self) -> None:
        """Dispatch the next pending group while at most one request is active."""
        if not self.is_mounted or self._suspended or self._agent_id is None:
            return
        controller = self._host.controller
        if controller.current is None or controller.is_closed:
            return
        self._abandon_invalid_token()
        if self._inflight is not None:
            return
        for lookup in self._queue_order():
            group = self._groups.get(lookup)
            if group is None or group.status != "pending":
                continue
            arguments = (group.representative_key, self._agent_id)
            cached = controller.get_cached_report("why", arguments)
            if cached is not None and isinstance(cached, ResolutionReport):
                group.report = cached
                group.status = "done"
                self._render_group_cells(lookup)
                continue
            result = self._host.request_report("why", arguments)
            if result is not None and isinstance(result, ResolutionReport):
                group.report = result
                group.status = "done"
                self._render_group_cells(lookup)
                continue
            request = controller.active_requests.get("why")
            if (
                request is not None
                and request.view == "why"
                and request.arguments == arguments
                and request.generation == controller.current.generation
            ):
                group.status = "loading"
                group.representative_key = arguments[0]
                self._inflight = _OwnedWhy(lookup, request)
                self._render_group_cells(lookup)
                return
            # Could not start work (closed/current changed).  Leave the group
            # pending; a later accepted event may retry, but a redraw alone
            # never loops.
            return

    def _queue_order(self) -> list[str]:
        order: list[str] = []
        seen: set[str] = set()
        selected = self._host.controller.selected_key
        if selected is not None:
            selected_lookup = self._lookup_by_key.get(selected)
            if selected_lookup is not None:
                order.append(selected_lookup)
                seen.add(selected_lookup)
        for row in self._visible:
            lookup = self._lookup_by_key.get(row.key)
            if lookup is None or lookup in seen:
                continue
            group = self._groups.get(lookup)
            if group is None or group.status != "pending":
                continue
            order.append(lookup)
            seen.add(lookup)
        return order

    def _abandon_invalid_token(self) -> None:
        if self._inflight is None:
            return
        controller = self._host.controller
        active = controller.active_requests.get("why")
        if active is not None and active == self._inflight.request:
            return
        group = self._groups.get(self._inflight.lookup_name)
        if group is not None and group.status == "loading":
            group.status = "pending"
        self._render_group_cells(self._inflight.lookup_name)
        self._inflight = None

    def _cancel_owned_why(self) -> None:
        owned = self._inflight
        self._inflight = None
        if owned is None:
            return
        controller = self._controller_or_none()
        if controller is None:
            return
        active = controller.active_requests.get("why")
        if active is not None and active == owned.request:
            controller.invalidate_view("why")
        group = self._groups.get(owned.lookup_name)
        if group is not None and group.status == "loading":
            group.status = "pending"

    # -- events / actions --------------------------------------------------

    def on_key(self, event: events.Key) -> None:
        if self._suspended:
            return
        if event.key in ("down", "up", "j", "k", "slash", "a", "escape", "enter", "r"):
            self._clear_removal_notice()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if self._syncing or self._suspended:
            return
        key = event.row_key.value
        table = self.query_one("#skill-table", DataTable)
        if table.row_count == 0:
            return
        cursor_index = table.cursor_row
        if cursor_index < 0 or cursor_index >= len(self._visible):
            return
        if self._visible[cursor_index].key != key:
            # A queued highlight from a previous table generation.
            return
        controller = self._host.controller
        if controller.selected_key == key:
            return
        controller.set_selected_key(key)
        self._abandon_invalid_token()
        self._update_preview()
        self._drive()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if self._suspended:
            return
        self.action_open_why()

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._suspended:
            return
        if event.input.id != "filter-input":
            return
        if event.value == self._last_query:
            return
        self._clear_removal_notice()
        self._apply_filters(reason="text")
        self._update_agent_widgets()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self._suspended:
            return
        if event.input.id != "filter-input":
            return
        self.query_one("#skill-table", DataTable).focus()

    def action_focus_filter(self) -> None:
        if self._suspended:
            return
        self.query_one("#filter-input", Input).focus()

    def action_clear_filter(self) -> None:
        if self._suspended:
            return
        self._clear_removal_notice()
        query = self.query_one("#filter-input", Input)
        if query.value:
            query.value = ""
        self.query_one("#skill-table", DataTable).focus()

    def action_cycle_agent(self) -> None:
        if self._suspended:
            return
        self._clear_removal_notice()
        if len(self._agent_options) <= 1:
            self._update_agent_widgets()
            return
        self._cancel_owned_why()
        self._groups = {}
        self._agent_index = (self._agent_index + 1) % len(self._agent_options)
        self._agent_id = self._agent_options[self._agent_index].agent_id
        self._lookup_by_key = {}
        self._apply_filters(reason="agent")

    def action_cursor_down(self) -> None:
        if self._suspended:
            return
        self._clear_removal_notice()
        self.query_one("#skill-table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        if self._suspended:
            return
        self._clear_removal_notice()
        self.query_one("#skill-table", DataTable).action_cursor_up()

    def action_open_why(self) -> None:
        """Open Why detail screen for the selected row."""
        if self._suspended:
            return
        table = self.query_one("#skill-table", DataTable)
        if not table.has_focus or table.row_count == 0:
            return
        cursor_index = table.cursor_row
        if cursor_index < 0 or cursor_index >= len(self._visible):
            return
        key = self._visible[cursor_index].key
        self._host.open_why(key, self._agent_id)

    def action_noop_enter(self) -> None:
        """Backward compatibility alias for enter action."""
        self.action_open_why()

    def action_refresh(self) -> None:
        """Clear removal notice on explicit refresh and request refresh."""
        if self._suspended:
            return
        self._clear_removal_notice()
        refresh_action = getattr(self.app, "action_refresh", None)
        if callable(refresh_action):
            refresh_action()


__all__ = [
    "ALL_AGENTS",
    "AgentOption",
    "HomeRow",
    "HomeScreen",
    "build_agent_options",
    "build_home_rows",
    "detected_agent_ids",
    "filter_home_rows",
    "preview_text",
    "resolution_text",
]
