"""Read-only canonical JSON presentation widget for the U5 screens.

Specification reference: ``FULL_SCREEN_TUI.md`` §8.8, §10, Step 5 and §22 U5.

The widget shows one already-serialized document. It never computes a report,
reads a file or rewrites the string: the caller supplies the exact text and the
widget renders it literally with markup parsing disabled. An owning screen keeps
its ordinary widgets mounted while this view is shown, so toggling the JSON view
never rebuilds filters, tables or collapsibles.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.content import Content
from textual.css.query import NoMatches
from textual.widgets import Static

from skill_lens.tui.session import SessionController


def session_explanation(controller: SessionController) -> str:
    """A plain sentence for what the session currently holds.

    JSON mode must never dress a refusal, a fault or a pending capture up as a
    report, and must never call an error "loading". The wording therefore follows
    the same states the screens already show in their status bars, in the same
    order of precedence: a standing refusal and a retry prompt outrank a pending
    capture, and an internal fault stays visible over both.
    """
    status = controller.status
    if status == "refused":
        return controller.refusal_message or "Snapshot refused."
    if status == "retry":
        return controller.retry_message or "Files changed while scanning. Press r to retry."
    if status == "error":
        return "Error: Unexpected internal fault. Details in memory only."
    if status == "loading":
        return "Scanning skills..."
    if controller.current is not None:
        return f"Ready: {len(controller.current.index.entries)} skills discovered"
    return "No session captured."


class JsonView(VerticalScroll):
    """A focusable, read-only scroll area for one canonical JSON document.

    :attr:`document` is the exact string the owner supplied. When the owner has
    nothing to serialize -- no captured session, a refused or failed capture, an
    agent with no report yet -- the view shows a literal explanation instead and
    :attr:`document` stays ``None``, so a placeholder can never be mistaken for
    report data or reach a JSON consumer.
    """

    DEFAULT_CSS = """
    JsonView {
        width: 1fr;
        height: 1fr;
        padding: 0 1;
    }
    JsonView > Static {
        width: 1fr;
        height: auto;
    }
    """

    def __init__(self, *, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(id=id, classes=classes)
        self._document: str | None = None
        self._text: str = ""

    def compose(self) -> ComposeResult:
        yield Static(
            Content(self._text, strip_control_codes=False),
            classes="json-document",
            markup=False,
        )

    # -- content -----------------------------------------------------------

    @property
    def document(self) -> str | None:
        """The exact document supplied by the owner, or ``None`` when none was."""
        return self._document

    @property
    def displayed_text(self) -> str:
        """The literal text on screen: the document itself, or an explanation."""
        return self._text

    @property
    def shows_document(self) -> bool:
        """True when the view currently shows canonical JSON rather than an explanation."""
        return self._document is not None

    def show_document(self, document: str) -> None:
        """Display one supplied canonical document verbatim.

        Re-publishing the *same* document is a no-op: an unchanged status, report
        or session synchronization must not rewrite the widget or move the
        reader's scroll position. A genuinely different document is written once
        and its pane returns to the top.
        """
        if self._document == document:
            return
        self._document = document
        self._text = document
        self._render_text()

    def show_explanation(self, explanation: str) -> None:
        """Display a literal explanation instead of a document.

        The backing :attr:`document` is cleared first: old JSON must never survive
        into a state that no longer owns it. Repeating the same explanation is a
        no-op, for the same reason as :meth:`show_document`.
        """
        if self._document is None and self._text == explanation:
            return
        self._document = None
        self._text = explanation
        self._render_text()

    # -- internals ---------------------------------------------------------

    def _render_text(self) -> None:
        try:
            widget = self.query_one(".json-document", Static)
        except NoMatches:
            # Not composed yet; ``compose`` renders the stored text on mount.
            return
        widget.update(Content(self._text, strip_control_codes=False))
        # Reset here even while the pane is hidden: a document that changes in
        # ordinary mode must not re-open at the previous document's position.
        self.scroll_home(animate=False, immediate=True)


__all__ = ["JsonView", "session_explanation"]
