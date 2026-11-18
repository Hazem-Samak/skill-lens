"""Pure copy decision for the TUI's OSC 52 clipboard action.

This module is deliberately free of Textual imports: the decision can be tested
without a running application, and every screen shares one rule.  The screen
wrapper reads ``os.environ`` at call time and passes it here; only the ``SENT``
decision reaches Textual's ``App.copy_to_clipboard``.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum

#: Largest payload emitted through OSC 52, in UTF-8 bytes.
#:
#: 75,000 bytes is a conservative stand-in for the roughly 100,000-base64-
#: character terminal cap (75,000 x 4/3 = 100,000), not an exact reading of the
#: cited limit.
MAX_COPY_BYTES = 75_000

#: How long a copy confirmation remains on screen, in seconds.
#:
#: Screens read this through the module (``clipboard.COPY_NOTICE_SECONDS``) so
#: tests can scale it without replacing the screen's binding.
COPY_NOTICE_SECONDS = 3.0

#: One sentence stating the limit of the confirmation and fallback, shared by
#: every screen's Help notes and repeated in README.
CLIPBOARD_LIMITATION = (
    "Copy sends one OSC 52 terminal escape sequence (no file, process or network"
    " write); the terminal may ignore it, and tmux or GNU screen block it, so the"
    " clipboard can stay unchanged."
)


class CopyDecision(Enum):
    """What one copy request should do."""

    SENT = "sent"
    BLOCKED = "blocked"
    TOO_LARGE = "too_large"


def copy_decision(text: str, env: Mapping[str, str]) -> CopyDecision:
    """Decide whether ``text`` may be emitted, using an explicit environment.

    ``TMUX`` being present and non-empty marks a tmux session, whose default
    ``set-clipboard external`` mode forbids inner applications from setting the
    clipboard.  A ``TERM`` beginning with ``screen`` marks GNU screen, which
    forwards only short device-control strings.  Missing keys mean "not blocked"
    -- the caller's live environment is never inspected here.

    Precedence is deliberate: ``BLOCKED`` is decided before ``TOO_LARGE``, so a
    blocked terminal reports its specific reason even for an oversized payload.
    """
    if env.get("TMUX") or env.get("TERM", "").startswith("screen"):
        return CopyDecision.BLOCKED
    if len(text.encode("utf-8")) > MAX_COPY_BYTES:
        return CopyDecision.TOO_LARGE
    return CopyDecision.SENT


__all__ = [
    "CLIPBOARD_LIMITATION",
    "COPY_NOTICE_SECONDS",
    "MAX_COPY_BYTES",
    "CopyDecision",
    "copy_decision",
]
