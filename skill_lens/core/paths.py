"""Lazy, call-time environment and path resolution.

Golden rule: **never** expand ``~`` or read ``$HOME`` at import time. Every
function here resolves environment state on each call so tests can freely
monkeypatch ``HOME`` / ``XDG_CONFIG_HOME`` and so ``--sandbox`` can redirect
the entire tool at a mock home directory.
"""

from __future__ import annotations

import os
from pathlib import Path

# Populated by ``use_sandbox`` (the ``--sandbox`` CLI flag). When set, every
# path helper resolves relative to this mock home instead of the real one.
_SANDBOX: Path | None = None


def set_sandbox(root: str | os.PathLike[str] | None) -> None:
    """Redirect all path resolution into ``root`` (a mock ``$HOME``).

    Passing ``None`` clears the sandbox and restores real-environment
    resolution. This is the single switch used by tests and safe demos.
    """
    global _SANDBOX
    _SANDBOX = Path(root).expanduser().resolve() if root is not None else None


def get_sandbox() -> Path | None:
    """Return the active sandbox root, or ``None`` when unset."""
    return _SANDBOX


def home() -> Path:
    """Resolve the effective home directory at call time."""
    if _SANDBOX is not None:
        return _SANDBOX
    return Path(os.environ.get("HOME", "~")).expanduser()


def xdg_config_home() -> Path:
    """Resolve ``$XDG_CONFIG_HOME``, defaulting to ``~/.config`` at call time."""
    env = os.environ.get("XDG_CONFIG_HOME")
    if env:
        return Path(env).expanduser()
    return home() / ".config"


def resolve(*parts: str | os.PathLike[str]) -> Path:
    """Join ``parts`` onto the effective home directory (lazy, not expanded)."""
    path = home()
    for part in parts:
        path = path / part
    return path


def display(path: str | os.PathLike[str]) -> str:
    """Render ``path`` with the effective home collapsed to ``~`` for output.

    Keeps terminal output readable without ever exposing full absolute paths
    for the common case.
    """
    target = Path(path)
    try:
        relative = target.relative_to(home())
    except ValueError:
        return str(target)
    return "~" if relative == Path(".") else f"~/{relative}"
