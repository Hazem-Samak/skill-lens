"""Cooperative cancellation for TUI capture (Assignment C3).

Specification reference: FULL_SCREEN_TUI.md §21.4.
"""

from __future__ import annotations

from collections.abc import Callable


class CaptureCancelled(Exception):
    """Raised when a cooperative cancellation predicate returns True."""


def check_cancelled(cancelled: Callable[[], bool] | None) -> None:
    """Check the cancellation predicate and raise CaptureCancelled if set.

    None or a predicate returning False returns normally; True raises
    CaptureCancelled.
    """
    if cancelled is not None and cancelled():
        raise CaptureCancelled()


__all__ = [
    "CaptureCancelled",
    "check_cancelled",
]
