"""Read-only Help overlay and pure content for Skill Lens (Assignment U8).

Specification reference: ``FULL_SCREEN_TUI.md`` §8.2, §8.5, §9.1, §10,
Step 8 and §22 U8.

The module has two halves:

* :class:`HelpContext` plus :func:`build_help_body` and
  :func:`build_help_status` are pure: they turn explicit screen state and the
  session controller into literal text. No screen is imported here, so every
  screen can supply its own named, focus-aware section without a cycle.
* :class:`HelpScreen` is one read-only modal. It composes a scrollable body, a
  live session section and a visible Close button. It never starts capture,
  report computation or filesystem discovery; the only actions it performs are
  dismissal, refresh and quit through the existing application paths.

Text is rendered with markup disabled, so captured names, paths and in-memory
tracebacks stay literal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Protocol, cast

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical, VerticalScroll
from textual.content import Content
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Static

from skill_lens.tui.session import SessionController

_COMMON_ROWS: tuple[tuple[str, str], ...] = (
    (
        "q / Ctrl+C",
        "Quit through the normal application path. Quit is cooperative and returns 0, "
        "or 3 after an accepted internal fault.",
    ),
    (
        "r",
        "Refresh the captured session. External edits appear only after a successful "
        "refresh; a failed refresh can keep the previous catalog.",
    ),
    (
        "? / Esc / Backspace",
        "Close this Help. ? is non-priority, so it stays ordinary filter text while "
        "the Home filter input is focused.",
    ),
    (
        "F1",
        "Toggle Help: open it from Home, Why, Diff, Agents, Compare or Doctor, or close "
        "this exact Help, even while typing.",
    ),
    (
        "Tab / Shift+Tab",
        "Move focus between this Help body and the Close button.",
    ),
    (
        "↑ ↓ / PageUp / PageDown / Home / End",
        "Scroll this Help body.",
    ),
    (
        "Enter",
        "Activate Close when the Close button has focus.",
    ),
)


@dataclass(frozen=True, slots=True)
class HelpRow:
    """One documented key and its real, contextual effect."""

    keys: str
    action: str


@dataclass(frozen=True, slots=True)
class HelpContext:
    """Everything one covered screen wants its Help section to say."""

    origin: str
    mode: str
    focus: str
    rows: tuple[HelpRow, ...]
    notes: tuple[str, ...] = ()


class _HelpHost(Protocol):
    """The small application surface this modal uses."""

    controller: SessionController

    def close_help(self, expected: HelpScreen) -> None:
        """Close this exact Help instance and reconcile the origin."""
        ...


def _row_text(keys: str, action: str) -> str:
    return f"  {keys} — {action}"


def build_help_body(context: HelpContext) -> str:
    """Render the static Help content for one explicit screen context."""
    lines = [
        f"Covered screen: {context.origin} — {context.mode}",
        f"Current focus: {context.focus}",
        "",
        "COMMON KEYS",
    ]
    lines.extend(_row_text(keys, action) for keys, action in _COMMON_ROWS)
    lines.extend(["", f"{context.origin.upper()} — {context.mode.upper()}"])
    lines.extend(_row_text(row.keys, row.action) for row in context.rows)
    if context.notes:
        lines.extend(["", "SCREEN NOTES"])
        lines.extend(f"  {note}" for note in context.notes)
    lines.extend(
        [
            "",
            "CAPTURED DATA",
            "  Every screen reads one captured session snapshot held in memory. Browsing"
            " does not read skill files or live agent configuration, so external edits"
            " appear only after a successful refresh (r).",
            "  An initial scan has no captured data yet. A failed refresh can retain the"
            " last successful catalog; refusal, retry and unexpected-fault states are"
            " reported literally in the session status below.",
            "  Capture budget: 256 MiB of total skill payload by default."
            " --max-snapshot-bytes changes the limit and 0 disables it. An oversized"
            " capture is refused for this home; retrying unchanged inputs cannot help.",
            "",
            "READ-ONLY",
            "  Skill Lens never writes, creates, moves or deletes files, never opens an"
            " editor, never runs processes and never uses the network. Opening Help"
            " starts no capture, no report computation and no filesystem discovery.",
            "  Doctor Enter selects a matching captured row in Home; it never opens the"
            " file or another application.",
        ]
    )
    return "\n".join(lines)


def _status_sentence(controller: SessionController) -> str:
    status = controller.status
    current = controller.current
    if status == "refused":
        return controller.refusal_message or "Snapshot refused."
    if status == "retry":
        return controller.retry_message or "Files changed while scanning. Press r to retry."
    if status == "error":
        return "Unexpected internal fault accepted. Details are kept in memory only."
    if status == "loading":
        if current is None:
            return "Initial scan in progress: no catalog has been captured yet."
        return (
            "Refresh in progress: a new catalog is being captured. The previous"
            f" captured data from generation {current.generation} remains displayed"
            " until the new capture is accepted."
        )
    if current is not None:
        return f"Ready: {len(current.index.entries)} skills discovered."
    return "No session captured yet."


def build_help_status(controller: SessionController) -> str:
    """Render live status and literal in-memory fault details."""
    current = controller.current
    status = controller.status
    lines = ["SESSION STATUS", f"  {_status_sentence(controller)}"]
    if current is not None:
        lines.append(
            f"  Captured generation {current.generation}: {len(current.index.entries)} skills."
        )
    if current is not None and status in {"loading", "refused", "retry", "error"}:
        lines.append(
            "  Retained data: the last successful capture is still displayed; it is not"
            " a result of the current request."
        )
    if status == "refused":
        lines.append(
            "  A refused capture publishes nothing. Use the command line for this home"
            " or raise --max-snapshot-bytes; retrying unchanged inputs cannot help."
        )
    if status == "retry":
        lines.append(
            "  This is an expected capture inconsistency, not an internal fault. Press r to retry."
        )
    if controller.is_failed:
        lines.extend(
            [
                "",
                "ACCEPTED INTERNAL FAULT (sticky; Quit exits 3):",
                controller.last_error_details or "(no details were recorded)",
            ]
        )
    return "\n".join(lines)


class HelpScreen(ModalScreen[None]):
    """One read-only Help modal with a scrollable body and a visible Close button."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "dismiss_help", "Close", show=True),
        Binding("backspace", "dismiss_help", "Close", show=False),
        Binding("question_mark", "dismiss_help", "Close", show=False),
        Binding("tab", "focus_next", "Next", show=False),
        Binding("shift+tab", "focus_previous", "Previous", show=False),
        Binding("q", "app.quit", "Quit", show=True),
        Binding("r", "app.refresh", "Refresh", show=True),
        Binding("ctrl+c", "app.quit", "Quit", show=False, priority=True),
    ]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
        background: $background 60%;
    }
    #help-frame {
        width: 95%;
        max-width: 110;
        height: 90%;
        layout: vertical;
        background: $surface;
        border: solid $primary;
    }
    #help-title {
        height: auto;
        padding: 0 1;
        text-style: bold;
    }
    #help-body {
        height: 1fr;
        padding: 0 1;
    }
    #help-content {
        width: 1fr;
        height: auto;
    }
    #help-session {
        width: 1fr;
        height: auto;
        padding-top: 1;
        border-top: solid $primary;
    }
    #help-close {
        width: auto;
        min-width: 12;
        margin: 0 1;
    }
    """

    def __init__(self, context: HelpContext, controller: SessionController) -> None:
        super().__init__()
        self.context = context
        self._controller = controller

    @property
    def _host(self) -> _HelpHost:
        return cast(_HelpHost, self.app)

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="help-frame"):
            yield Static(
                f"Help — {self.context.origin}",
                id="help-title",
                markup=False,
            )
            with VerticalScroll(id="help-body"):
                yield Static(
                    build_help_body(self.context),
                    id="help-content",
                    markup=False,
                )
                yield Static(
                    build_help_status(self._controller),
                    id="help-session",
                    markup=False,
                )
            yield Button("Close", id="help-close", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        body = self.query_one("#help-body", VerticalScroll)
        body.can_focus = True
        body.focus()

    def update_session(self, controller: SessionController) -> None:
        """Refresh only the live session section; the static body keeps its scroll."""
        if not self.is_mounted:
            return
        try:
            session = self.query_one("#help-session", Static)
        except NoMatches:
            return
        session.update(Content.from_text(build_help_status(controller), markup=False))

    # -- actions ------------------------------------------------------------

    def action_dismiss_help(self) -> None:
        """Dismiss this exact Help instance through the guarded host path."""
        self._host.close_help(self)

    def action_focus_next(self) -> None:
        """Tab stays inside the Help body and Close button."""
        self.focus_next()

    def action_focus_previous(self) -> None:
        """Shift+Tab stays inside the Help body and Close button."""
        self.focus_previous()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "help-close":
            event.stop()
            self.action_dismiss_help()


__all__ = [
    "HelpContext",
    "HelpRow",
    "HelpScreen",
    "build_help_body",
    "build_help_status",
]
