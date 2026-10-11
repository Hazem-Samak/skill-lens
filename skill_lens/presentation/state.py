"""Shared state styling, marks, and scope labels for CLI and future TUI."""

from __future__ import annotations

from skill_lens.models.enums import HeadlineState, Scope

STATE_STYLE: dict[HeadlineState, str] = {
    HeadlineState.ACTIVE: "bold green",
    HeadlineState.COEXISTS: "bold cyan",
    HeadlineState.SHADOWED: "yellow",
    HeadlineState.DISABLED: "dim",
    HeadlineState.UNSEARCHED: "dim",
    HeadlineState.INVALID: "bold red",
    HeadlineState.AMBIGUOUS: "bold magenta",
}

STATE_MARK: dict[HeadlineState, str] = {
    HeadlineState.ACTIVE: "*",
    HeadlineState.COEXISTS: "+",
    HeadlineState.SHADOWED: "o",
    HeadlineState.DISABLED: "-",
    HeadlineState.UNSEARCHED: ".",
    HeadlineState.INVALID: "x",
    HeadlineState.AMBIGUOUS: "?",
}

SCOPE_LABEL: dict[Scope, str] = {
    Scope.USER: "Global",
    Scope.PROJECT: "Project",
    Scope.SYSTEM: "System",
    Scope.PLUGIN: "Plugin",
}

__all__ = [
    "SCOPE_LABEL",
    "STATE_MARK",
    "STATE_STYLE",
]
