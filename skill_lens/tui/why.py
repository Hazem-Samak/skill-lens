"""Read-only Why screen for Skill Lens (Assignment U4).

Specification reference: FULL_SCREEN_TUI.md §8.4, §21.7 and §22 U4.

The screen explains how one chosen agent resolves one captured installation.
It never reads files, resolves paths or runs discovery while browsing.  All
data comes from the published :class:`~skill_lens.core.snapshot_models.SessionSnapshot`
and the :class:`~skill_lens.tui.session.SessionController`.

The screen owns at most one complete :class:`~skill_lens.tui.session.ViewRequest`.
On agent change it clears incompatible display immediately, cancels only a
matching owned active token, checks the controller cache first, and dispatches
only on a true miss.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Any, ClassVar, Protocol, cast

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, VerticalScroll
from textual.content import Content
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import Button, Collapsible, Footer, Header, Static

from skill_lens.core.discovery import canonical_key
from skill_lens.core.exitcodes import ExitCode
from skill_lens.core.scanner import ScanEntry
from skill_lens.core.snapshot import snapshot_path, snapshot_same_location
from skill_lens.core.snapshot_models import SessionSnapshot
from skill_lens.models.enums import HeadlineState, ParseStatus, Scope
from skill_lens.models.resolution import CandidateResolution, ResolutionReport
from skill_lens.presentation.state import STATE_MARK, STATE_STYLE
from skill_lens.tui.home import AgentOption, agent_display_name
from skill_lens.tui.session import ReportValue, SessionController, ViewName, ViewRequest

_NO_AGENT_EXPLANATION = "No agent reaches this installation."
_UNKNOWN_AGENT_HINT = "Unknown agent IDs: {}"


class _WhyHost(Protocol):
    """The small part of :class:`SkillLensApp` the Why screen needs."""

    controller: SessionController

    def request_report(self, view: ViewName, arguments: tuple[str, ...]) -> ReportValue | None:
        """Return a cached report or start the existing report worker."""
        ...

    def close_why(self, removal_notice: str | None = None) -> None:
        """Close the Why screen and return to Home."""
        ...

    def _update_ui(self) -> None:
        """Ask the host app to refresh its status/error presentation."""
        ...

    def action_refresh(self) -> None:
        """Request a session refresh."""
        ...


@dataclass(frozen=True, slots=True)
class _CandidateBlock:
    """View model for one candidate collapsible block."""

    key: str
    title_name: str
    state: HeadlineState
    body: str
    expanded: bool

    @property
    def title(self) -> str:
        """Construct full plain title string for compatibility."""
        mark = _state_mark(self.state)
        return f"{mark} {self.title_name}  ({self.state.value})"


def _eligible_agent_options(snapshot: SessionSnapshot, key: str) -> tuple[AgentOption, ...]:
    """Agent IDs that reach the selected installation and have registry definitions.

    Preserves the scan's sorted agent-ID order.  Agents listed by the scan but
    absent from the captured registry are excluded and reported separately by
    the caller.
    """
    entry = _entry_for_key(snapshot, key)
    if entry is None:
        return ()
    registry_ids = {agent.id for agent in snapshot.registry}
    eligible = [agent_id for agent_id in entry.agents if agent_id in registry_ids]
    return tuple(
        AgentOption(agent_id, agent_display_name(snapshot, agent_id)) for agent_id in eligible
    )


def _unavailable_agent_ids(snapshot: SessionSnapshot, key: str) -> tuple[str, ...]:
    """Agent IDs the scan attributes to the installation but the registry lacks."""
    entry = _entry_for_key(snapshot, key)
    if entry is None:
        return ()
    registry_ids = {agent.id for agent in snapshot.registry}
    return tuple(sorted(agent_id for agent_id in entry.agents if agent_id not in registry_ids))


def _entry_for_key(snapshot: SessionSnapshot, key: str) -> ScanEntry | None:
    """Return the scan row for the selected canonical key, or None."""
    for row in snapshot.scan.skills:
        if row.canonical_path == key:
            return row
    for entry in snapshot.index.entries:
        if canonical_key(entry) == key:
            agents = tuple(sorted({hit.agent_id for hit in entry.hits}))
            scope = entry.hits[0].scope if entry.hits else Scope.USER
            desc = entry.parse.description if entry.parse else None
            parse_status = entry.parse.status.value if entry.parse else ParseStatus.UNREADABLE.value
            return ScanEntry(
                name=entry.name,
                scope=scope,
                canonical_path=canonical_key(entry),
                parse_status=parse_status,
                agents=agents,
                entrypoint_count=len(entry.entrypoint_paths) or len(entry.hits),
                is_symlink=entry.is_symlink,
                content_hash=entry.content_hash,
                description=desc,
                variant_label=entry.variant_label,
            )
    return None


def _matching_key(candidate: CandidateResolution, key: str) -> bool:
    """True if a candidate resolves the selected installation.

    Uses canonical path with entrypoint fallback for unresolved copies, matching
    the key derivation used by ``canonical_key`` and the scan rows.
    """
    inst = candidate.installation
    return inst.canonical_path == key or (
        inst.canonical_path is None and inst.entrypoint_path == key
    )


def _state_mark(state: HeadlineState) -> str:
    """Return the shared state glyph for a headline state."""
    return STATE_MARK.get(state, "?")


def _build_candidate_blocks(
    report: ResolutionReport, snapshot: SessionSnapshot, key: str
) -> list[_CandidateBlock]:
    """Build one collapsible block per candidate in report order.

    Candidates matching the selected key are initially expanded; all others are
    collapsed.  Paths are displayed through ``snapshot_path`` and never probed
    on disk.  Redundant entrypoint lines are suppressed via
    ``snapshot_same_location``.
    """
    blocks: list[_CandidateBlock] = []
    for candidate in report.candidates:
        inst = candidate.installation
        canonical_display = (
            snapshot_path(snapshot, inst.canonical_path) if inst.canonical_path else "none"
        )
        entrypoint_display = snapshot_path(snapshot, inst.entrypoint_path)
        mark = _state_mark(candidate.state)
        variant = f"  [{inst.variant_label}]" if inst.variant_label else ""
        hash_text = f"  Hash: {inst.content_hash[:23]}..." if inst.content_hash else "  Hash: none"
        reason_line = f"Reason: {candidate.reason}"
        rule_line = f"Rule: {candidate.rule_id}  Evidence: {candidate.evidence.value}"
        lines: list[str] = [
            f"{mark} {inst.name}{variant}",
            f"  Canonical: {canonical_display}",
        ]
        if not inst.canonical_path or not snapshot_same_location(
            snapshot, inst.canonical_path, inst.entrypoint_path
        ):
            lines.append(f"  Entrypoint: {entrypoint_display}")
        lines.append(hash_text)
        lines.append(reason_line)
        lines.append(rule_line)
        for note in report.notes:
            lines.append(f"  Note: {note}")
        body = "\n".join(lines)
        expanded = _matching_key(candidate, key)
        title_name = f"{inst.name}{variant}"
        blocks.append(
            _CandidateBlock(
                key=str(inst.canonical_path or inst.entrypoint_path),
                title_name=title_name,
                state=candidate.state,
                body=body,
                expanded=expanded,
            )
        )
    return blocks


class WhyScreen(Screen[None]):
    """Read-only skill detail screen: one installation, one agent, captured report."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("tab", "focus_next", "Next", show=False),
        Binding("shift+tab", "focus_previous", "Previous", show=False),
        Binding("left", "previous_agent", "Left", show=False),
        Binding("right", "next_agent", "Right", show=False),
        Binding("escape", "close_why", "Back", show=True),
        Binding("backspace", "close_why", "Back", show=False),
        Binding("q", "app.quit", "Quit", show=True),
        Binding("ctrl+c", "app.quit", "Quit", show=False, priority=True),
        Binding("r", "app.refresh", "Refresh", show=True),
    ]

    DEFAULT_CSS = """
    WhyScreen {
        layout: vertical;
    }
    #why-body {
        height: 1fr;
    }
    #why-title {
        height: auto;
        padding: 0 1;
        text-style: bold;
    }
    #why-agent-strip {
        height: auto;
        layout: horizontal;
        padding: 0 1;
    }
    #why-agent-strip Button {
        min-width: 14;
        margin: 0 1;
    }
    #why-status, #why-error-details, #why-report-status {
        height: auto;
        padding: 0 1;
    }
    #why-candidates {
        height: auto;
    }
    WhyScreen CollapsibleTitle {
        max-width: 100%;
        width: 100%;
        height: auto;
    }
    WhyScreen.narrow #why-agent-strip {
        layout: vertical;
    }
    """

    def __init__(self, key: str, agent_id: str | None) -> None:
        super().__init__()
        self._opening_key = key
        self._key = key
        self._agent_id = agent_id
        self._agent_options: tuple[AgentOption, ...] = ()
        self._agent_index = 0
        self._report: ResolutionReport | None = None
        self._owned_request: ViewRequest | None = None
        self._generation: int | None = None
        self._unavailable: tuple[str, ...] = ()
        self._syncing = False
        self._rendered_candidate_context: tuple[Any, ...] | None = None
        self._captured_name: str | None = None

    # -- host integration ---------------------------------------------------

    @property
    def _host(self) -> _WhyHost:
        return cast(_WhyHost, self.app)

    def _controller_or_none(self) -> SessionController | None:
        return getattr(self._host, "controller", None)

    # -- lifecycle ----------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="why-body"):
            yield Static("", id="why-title", markup=False)
            yield Horizontal(id="why-agent-strip")
            yield Static("", id="why-status", markup=False)
            yield Static("", id="why-error-details", markup=False)
            yield Static("", id="why-report-status", markup=False)
            yield VerticalScroll(id="why-candidates", can_focus=False)
        yield Footer()

    def on_mount(self) -> None:
        strip = self.query_one("#why-agent-strip", Horizontal)
        strip.can_focus = True
        strip.focus()
        self._mounting = True
        try:
            self.sync_from_controller()
        finally:
            self._mounting = False
        self._update_strip_focus()

    def on_resize(self, event: events.Resize) -> None:
        self.set_class(event.size.width < 80, "narrow")

    # -- synchronization ----------------------------------------------------

    def sync_from_controller(self) -> bool:
        """Reconcile the screen with the controller's published session.

        Returns True if the screen should close (the detail's opening key was
        removed from the catalog), in which case the host calls ``close_why``.
        """
        if not self.is_mounted and not getattr(self, "_mounting", False):
            return False
        controller = self._controller_or_none()
        if controller is None:
            return False
        snapshot = controller.current
        if snapshot is None:
            self._clear_display()
            return False

        if self._captured_name is None and (entry := _entry_for_key(snapshot, self._opening_key)):
            self._captured_name = entry.name

        if snapshot.generation != self._generation:
            current_keys = {canonical_key(e) for e in snapshot.index.entries}
            if self._opening_key not in current_keys:
                # Detail's installation was removed -- return to Home.
                if self._captured_name and self._captured_name != self._opening_key:
                    notice = (
                        f"Installation '{self._captured_name}' ({self._opening_key})"
                        " was removed during refresh."
                    )
                else:
                    notice = f"Installation '{self._opening_key}' was removed during refresh."
                self._host.close_why(removal_notice=notice)
                return True
            self._generation = snapshot.generation
            self._rebuild_from_snapshot(snapshot)

        self._update_display()
        return False

    def _rebuild_from_snapshot(self, snapshot: SessionSnapshot) -> None:
        """Re-derive agent choices and request context from a new snapshot."""
        self._cancel_owned_token()
        if entry := _entry_for_key(snapshot, self._opening_key):
            self._captured_name = entry.name
        self._agent_options = _eligible_agent_options(snapshot, self._opening_key)
        self._unavailable = _unavailable_agent_ids(snapshot, self._opening_key)

        # Initial agent: Home's active agent if eligible, otherwise first option.
        if self._agent_id is not None and any(
            o.agent_id == self._agent_id for o in self._agent_options
        ):
            self._agent_index = next(
                i for i, o in enumerate(self._agent_options) if o.agent_id == self._agent_id
            )
        elif self._agent_options:
            self._agent_index = 0
            self._agent_id = self._agent_options[0].agent_id
        else:
            self._agent_index = 0
            self._agent_id = None

        self._owned_request = None
        self._report = None
        self._refresh_strip()
        self._request_report()

    def _request_report(self) -> None:
        """Request the Why report for the current key/agent, or show an explanation."""
        controller = self._controller_or_none()
        if controller is None or controller.current is None:
            return

        # Pre-dispatch validation: key must exist in the current catalog.
        current_keys = {canonical_key(e) for e in controller.current.index.entries}
        if self._opening_key not in current_keys:
            # Missing key: return to Home, no dispatch, no failure.
            self._host.close_why()
            return

        # Zero-agent skill: clear explanation, zero Why requests.
        if not self._agent_options:
            self._report = None
            self._cancel_owned_token()
            self._update_display()
            return

        # Invalid agent: show unavailable inline, no dispatch, no failure.
        if self._agent_id is None or self._agent_id not in {
            o.agent_id for o in self._agent_options
        }:
            self._report = None
            self._cancel_owned_token()
            self._update_display()
            return

        arguments = (self._opening_key, self._agent_id)

        # Use the public adapter: cache hit returns immediately, miss dispatches.
        cached = controller.get_cached_report("why", arguments)
        if cached is not None and isinstance(cached, ResolutionReport):
            self._report = cached
            self._cancel_owned_token()
            self._update_display()
            return

        # Redraw deduplication: if identical request is already active, keep it!
        active = controller.active_requests.get("why")
        if (
            self._owned_request is not None
            and active is not None
            and active == self._owned_request
            and active.arguments == arguments
            and active.generation == controller.current.generation
        ):
            return

        # Dispatch miss through host adapter
        self._cancel_owned_token()
        result = self._host.request_report("why", arguments)
        if result is not None and isinstance(result, ResolutionReport):
            self._report = result
            self._owned_request = None
            self._update_display()
            return

        # Cache miss: worker was dispatched by request_report.  Track the owned
        # request from the controller's active slot.
        active_now = controller.active_requests.get("why")
        if (
            active_now is not None
            and active_now.arguments == arguments
            and active_now.generation == controller.current.generation
        ):
            self._owned_request = active_now
            self._report = None
            self._update_display()

    def _cancel_owned_token(self) -> None:
        """Cancel detail's owned Why request token if it is still active."""
        owned = self._owned_request
        self._owned_request = None
        if owned is None:
            return
        controller = self._controller_or_none()
        if controller is None:
            return
        active = controller.active_requests.get("why")
        if active is not None and active == owned:
            controller.invalidate_view("why")

    # -- display ------------------------------------------------------------

    def _refresh_strip(self) -> None:
        """Rebuild or update the agent strip buttons from current options in sorted order."""
        strip = self.query_one("#why-agent-strip", Horizontal)
        focused = self.app.focused
        strip_had_focus = (focused is strip) or (focused is not None and focused in strip.children)
        focused_id = getattr(focused, "id", None) if strip_had_focus else None

        desired_options = self._agent_options
        desired_ids = [f"why-agent-{option.agent_id or 'none'}" for option in desired_options]
        current_buttons = [c for c in strip.children if isinstance(c, Button)]
        existing_by_id = {btn.id: btn for btn in current_buttons}

        for btn in current_buttons:
            if btn.id not in desired_ids:
                btn.remove()

        for idx, option in enumerate(desired_options):
            btn_id = f"why-agent-{option.agent_id or 'none'}"
            if btn_id in existing_by_id:
                btn = existing_by_id[btn_id]
                btn.label = Content.from_text(option.label, markup=False)
                btn.set_class(option.agent_id == self._agent_id, "active")
            else:
                btn = Button(
                    Content.from_text(option.label, markup=False),
                    id=btn_id,
                )
                if option.agent_id == self._agent_id:
                    btn.add_class("active")
                next_id = next(
                    (nid for nid in desired_ids[idx + 1 :] if nid in existing_by_id),
                    None,
                )
                if next_id is not None:
                    strip.mount(btn, before=f"#{next_id}")
                else:
                    strip.mount(btn)
                existing_by_id[btn_id] = btn

        # Reorder strip buttons in scan-ID order using Textual public move_child API
        if hasattr(strip, "move_child"):
            for target_idx, desired_id in enumerate(desired_ids):
                target_btn = existing_by_id.get(desired_id)
                if target_btn is not None and target_btn in strip.children:
                    current_idx = list(strip.children).index(target_btn)
                    if current_idx != target_idx:
                        strip.move_child(target_btn, before=target_idx)

        if strip_had_focus and focused_id not in desired_ids:
            self._update_strip_focus()

    def _update_strip_focus(self) -> None:
        """Move focus to the button for the currently selected agent."""
        if self._agent_id is None:
            strip = self.query_one("#why-agent-strip", Horizontal)
            strip.focus()
            return
        try:
            button = self.query_one(f"#why-agent-{self._agent_id}", Button)
            button.focus()
        except NoMatches:
            strip = self.query_one("#why-agent-strip", Horizontal)
            strip.focus()

    def _update_display(self) -> None:
        """Rewrite title, strip, status, error and candidate panels from state."""
        self._refresh_title()
        self._refresh_strip()
        self._refresh_status()
        self._refresh_candidates()

    def _refresh_title(self) -> None:
        title = self.query_one("#why-title", Static)
        controller = self._controller_or_none()
        snapshot = controller.current if controller is not None else None
        agent_label = (
            agent_display_name(snapshot, self._agent_id)
            if (snapshot is not None and self._agent_id is not None)
            else (self._agent_id or "—")
        )
        installation_display = (
            snapshot_path(snapshot, self._opening_key)
            if snapshot is not None
            else self._opening_key
        )
        lines = [f"Installation: {installation_display}"]
        if snapshot is not None:
            entry = _entry_for_key(snapshot, self._opening_key)
            if entry is not None:
                lines.append(f"Name: {entry.name}")
            lines.append(f"Working directory: {snapshot_path(snapshot, str(snapshot.cwd))}")
        lines.append(f"Agent: {agent_label}")
        if self._unavailable:
            lines.append(f"Unavailable agent IDs: {', '.join(self._unavailable)}")
        if self._report is not None:
            lines.append(f"Lookup name: {self._report.skill_name}")
            lines.append(
                f"Collision policy: {self._report.collision_policy} "
                f"({self._report.policy_evidence.value})"
            )
            lines.append(f"Report-wide headline: {self._report.headline.value}")
            for note in self._report.notes:
                lines.append(f"Note: {note}")
        title.update(Content.from_text("\n".join(lines), markup=False))

    def _refresh_status(self) -> None:
        controller = self._controller_or_none()
        status_widget = self.query_one("#why-status", Static)
        error_widget = self.query_one("#why-error-details", Static)
        report_widget = self.query_one("#why-report-status", Static)

        if controller is None or controller.current is None:
            status_widget.update(Content.from_text("Idle", markup=False))
            error_widget.update(Content.from_text("", markup=False))
            report_widget.update(Content.from_text("No session captured.", markup=False))
            return

        status = controller.status
        if status == "loading":
            status_widget.update(Content.from_text("Scanning skills...", markup=False))
            error_widget.update(Content.from_text("", markup=False))
        elif status == "ready":
            count = len(controller.current.index.entries)
            status_widget.update(
                Content.from_text(f"Ready: {count} skills discovered", markup=False)
            )
            error_widget.update(Content.from_text("", markup=False))
        elif status == "refused":
            msg = controller.refusal_message or "Snapshot refused."
            status_widget.update(Content.from_text(msg, markup=False))
            error_widget.update(Content.from_text("", markup=False))
        elif status == "retry":
            msg = controller.retry_message or "Files changed while scanning. Press r to retry."
            status_widget.update(Content.from_text(msg, markup=False))
            error_widget.update(Content.from_text("", markup=False))
        elif status == "error":
            status_widget.update(
                Content.from_text(
                    "Error: Unexpected internal fault. Details in memory only.", markup=False
                )
            )
            error_widget.update(
                Content.from_text(controller.last_error_details or "", markup=False)
            )
        else:
            status_widget.update(Content.from_text("Idle", markup=False))
            error_widget.update(Content.from_text("", markup=False))

        # Report-specific status
        if not self._agent_options:
            if self._unavailable:
                report_widget.update(
                    Content.from_text(
                        f"Unavailable agent IDs: {', '.join(self._unavailable)}",
                        markup=False,
                    )
                )
            else:
                report_widget.update(Content.from_text(_NO_AGENT_EXPLANATION, markup=False))
        elif (
            self._unavailable
            and self._agent_id is not None
            and self._agent_id not in {o.agent_id for o in self._agent_options}
        ):
            report_widget.update(
                Content.from_text(
                    _UNKNOWN_AGENT_HINT.format(", ".join(self._unavailable)),
                    markup=False,
                )
            )
        elif self._owned_request is not None:
            report_widget.update(Content.from_text("Loading report…", markup=False))
        elif self._report is not None:
            report_text = f"Report: {self._report.skill_name} for {self._report.agent_name}"
            if self._unavailable:
                report_text += f" (Unavailable agent IDs: {', '.join(self._unavailable)})"
            report_widget.update(Content.from_text(report_text, markup=False))
        else:
            report_widget.update(Content.from_text("No report available.", markup=False))

    def _refresh_candidates(self) -> None:
        controller = self._controller_or_none()
        snapshot = controller.current if controller is not None else None

        current_context = (
            self._opening_key,
            self._agent_id,
            id(self._report) if self._report is not None else None,
            self._owned_request is not None,
            self._unavailable,
            len(self._agent_options),
        )
        if self._rendered_candidate_context == current_context:
            return

        container = self.query_one("#why-candidates", VerticalScroll)
        container.remove_children()

        if self._report is None:
            if not self._agent_options:
                if self._unavailable:
                    msg = (
                        f"Unavailable agent IDs: {', '.join(self._unavailable)} "
                        "— no registered agent reaches this installation."
                    )
                else:
                    msg = _NO_AGENT_EXPLANATION
                container.mount(Static(msg, markup=False))
            elif (
                self._unavailable
                and self._agent_id is not None
                and self._agent_id not in {o.agent_id for o in self._agent_options}
            ):
                msg = (
                    f"Unavailable agent: {', '.join(self._unavailable)} "
                    "— no Why report can be produced for this selection."
                )
                container.mount(Static(msg, markup=False))
            elif self._owned_request is not None:
                container.mount(Static("Loading report…", markup=False))
            else:
                container.mount(Static("No report available.", markup=False))
            self._rendered_candidate_context = current_context
            return

        if not self._report.candidates:
            if not self._report.found:
                msg = "No copies of this skill name were found in any search roots."
            else:
                msg = f"No candidates evaluated. Headline: {self._report.headline.value}"
            container.mount(Static(msg, markup=False))
            self._rendered_candidate_context = current_context
            return

        assert snapshot is not None
        blocks = _build_candidate_blocks(self._report, snapshot, self._opening_key)
        has_match = any(b.expanded for b in blocks)
        if not has_match:
            container.mount(
                Static(
                    "No candidate matches the selected installation.",
                    id="why-no-match-notice",
                    markup=False,
                )
            )

        for block in blocks:
            style = STATE_STYLE.get(block.state, "")
            mark = _state_mark(block.state)
            title_content = Content.assemble(
                Content.styled(f"{mark} ", style) if style else f"{mark} ",
                Content.from_text(block.title_name, markup=False),
                Content.styled(f"  ({block.state.value})", style)
                if style
                else f"  ({block.state.value})",
            )
            collapsible = Collapsible(
                Static(block.body, markup=False),
                title=title_content,  # type: ignore[arg-type]
                collapsed=not block.expanded,
            )
            container.mount(collapsible)
        self._rendered_candidate_context = current_context

    def _clear_display(self) -> None:
        self._rendered_candidate_context = None
        with contextlib.suppress(NoMatches):
            self.query_one("#why-title", Static).update(Content.from_text("", markup=False))
            self.query_one("#why-status", Static).update(Content.from_text("", markup=False))
            self.query_one("#why-error-details", Static).update(Content.from_text("", markup=False))
            self.query_one("#why-report-status", Static).update(Content.from_text("", markup=False))
            self.query_one("#why-candidates", VerticalScroll).remove_children()

    # -- agent switching ----------------------------------------------------

    def action_previous_agent(self) -> None:
        """Switch to the previous agent while the strip is focused."""
        if not self._is_strip_focused() or not self._agent_options:
            return
        self._change_agent(-1)

    def action_next_agent(self) -> None:
        """Switch to the next agent while the strip is focused."""
        if not self._is_strip_focused() or not self._agent_options:
            return
        self._change_agent(1)

    def _is_strip_focused(self) -> bool:
        focused = self.app.focused
        if focused is None:
            return False
        try:
            strip = self.query_one("#why-agent-strip", Horizontal)
        except NoMatches:
            return False
        return focused is strip or focused in strip.children

    def _change_agent(self, delta: int) -> None:
        """Change the selected agent by delta, wrapping deterministically."""
        if not self._agent_options:
            return
        self._agent_index = (self._agent_index + delta) % len(self._agent_options)
        self._agent_id = self._agent_options[self._agent_index].agent_id
        self._cancel_owned_token()
        self._report = None
        self._update_display()
        self._update_strip_focus()
        self._request_report()

    # -- actions ------------------------------------------------------------

    def action_close_why(self) -> None:
        """Close the Why screen and return to Home."""
        self._host.close_why()

    def action_quit(self) -> None:
        """Quit the application with the controller's exit code."""
        controller = self._controller_or_none()
        code = controller.close() if controller is not None else int(ExitCode.OK)
        self.app.exit(code, return_code=code)

    def action_refresh(self) -> None:
        """Request a session refresh through the host app."""
        self._host.action_refresh()

    def action_focus_next(self) -> None:
        """Move focus to the next focusable area."""
        self.focus_next()

    def action_focus_previous(self) -> None:
        """Move focus to the previous focusable area."""
        self.focus_previous()

    # -- outcome handling ---------------------------------------------------

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
        """Consume an accepted Why result, or merely wake after rejection."""
        if not self.is_mounted or view != "why":
            return
        controller = self._controller_or_none()
        if controller is None:
            return
        owned = self._owned_request
        if owned is not None:
            identity_matches = (
                owned.request_id == request_id
                and owned.generation == generation
                and owned.view == view
                and owned.arguments == arguments
            )
            if identity_matches:
                if accepted:
                    if isinstance(report, ResolutionReport):
                        self._report = report
                    else:
                        self._report = None
                    self._owned_request = None
                    self._update_display()
                else:
                    active = controller.active_requests.get("why")
                    if active is None or active != owned:
                        self._owned_request = None
                    self._update_display()
                    self._request_report()
            elif not accepted:
                # Rejected data for someone else's token must never clear or
                # mark the newer owned token.
                pass

    # -- event handlers -----------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle agent button presses from the strip."""
        button = event.button
        button_id = button.id or ""
        if button_id.startswith("why-agent-"):
            agent_id = button_id[len("why-agent-") :] or None
            if agent_id != self._agent_id:
                self._agent_id = agent_id
                self._agent_index = next(
                    (i for i, o in enumerate(self._agent_options) if o.agent_id == agent_id),
                    0,
                )
                self._cancel_owned_token()
                self._report = None
                self._update_display()
                self._request_report()
        event.stop()

    def on_unmount(self) -> None:
        self._cancel_owned_token()


__all__ = [
    "WhyScreen",
]
