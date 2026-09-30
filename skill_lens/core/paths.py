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


def terminal_cwd() -> Path:
    """The folder the user is standing in, for the default ``--cwd``.

    Under a sandbox the real terminal folder is meaningless -- it would point
    outside the mock home and let a sandboxed run read the real filesystem --
    so the sandbox root is used instead. Resolved at call time, never at import.
    """
    if _SANDBOX is not None:
        return _SANDBOX
    try:
        return Path.cwd()
    except OSError:  # pragma: no cover - deleted cwd is vanishingly rare
        return home()


def resolve(*parts: str | os.PathLike[str]) -> Path:
    """Join ``parts`` onto the effective home directory (lazy, not expanded)."""
    path = home()
    for part in parts:
        path = path / part
    return path


def _home_variants() -> tuple[Path, ...]:
    """The effective home as written, and as fully resolved.

    A home directory can sit behind a symlink (macOS ``/tmp`` is
    ``/private/tmp``). ``canonicalize()`` returns resolved paths while
    entrypoints keep the path as written, so both forms are needed to collapse
    either one to ``~``.
    """
    root = home()
    resolved = root.resolve()
    return (root,) if resolved == root else (root, resolved)


def display(path: str | os.PathLike[str]) -> str:
    """Render ``path`` with the effective home collapsed to ``~`` for output.

    Keeps terminal output readable without ever exposing full absolute paths
    for the common case. Both sides are tried as-written and fully resolved,
    so a path reached through a symlinked home still collapses.
    """
    target = Path(path)
    try:
        resolved = target.resolve()
    except OSError:  # pragma: no cover - unresolvable path
        resolved = target
    targets = (target,) if resolved == target else (target, resolved)
    for root in _home_variants():
        for candidate in targets:
            try:
                relative = candidate.relative_to(root)
            except ValueError:
                continue
            return "~" if relative == Path(".") else f"~/{relative}"
    return str(target)


def same_location(left: str | os.PathLike[str], right: str | os.PathLike[str]) -> bool:
    """True when two paths name the same place on disk.

    Compares resolved paths, so an entrypoint and its canonical target are
    recognised as one file even when one of them still carries symlinked
    parent directories.
    """
    try:
        return Path(left).resolve() == Path(right).resolve()
    except OSError:  # pragma: no cover - unresolvable path
        return False
