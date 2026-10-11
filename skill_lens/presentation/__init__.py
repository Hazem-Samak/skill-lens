"""Shared presentation interfaces and helpers for Skill Lens."""

from __future__ import annotations

from skill_lens.presentation.state import SCOPE_LABEL, STATE_MARK, STATE_STYLE
from skill_lens.presentation.text import (
    HeadingParts,
    NoticeParts,
    copy_heading,
    needs_listing,
    no_differences_message,
    range_text,
    unified_text,
    unreadable_reason,
)

__all__ = [
    "HeadingParts",
    "NoticeParts",
    "SCOPE_LABEL",
    "STATE_MARK",
    "STATE_STYLE",
    "copy_heading",
    "needs_listing",
    "no_differences_message",
    "range_text",
    "unified_text",
    "unreadable_reason",
]
