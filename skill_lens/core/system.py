"""Live-filesystem adapter: the guarded bridge between the engine and real disk.

Everything above this module is pure -- it takes a ``home``/``cwd`` and returns
models. This module is the only place that asks *where the user actually is*
(:func:`skill_lens.core.paths` resolves ``$HOME`` at call time, never at
import), and the only place that touches the filesystem defensively: a real
home contains directories macOS TCC refuses to list and files that are
symlinks to nothing, and an ``OSError`` from one directory must never abort a
diagnostic run.

Read-only is absolute here: every call is ``iterdir`` / ``read_text`` /
``stat``. Skill Lens never creates, moves, or deletes anything it probes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from skill_lens.core import paths
from skill_lens.core.discovery import DiscoveryIndex, discover
from skill_lens.models.parsing import ERR_PERMISSION_DENIED
from skill_lens.registry.loader import AgentDefinition


def shared_library(home: Path | None = None) -> Path:
    """Return ``$HOME/.agents/skills``: the library symlink farms point into.

    Resolved per call from the effective home (sandbox or real), never at
    import time (AGENTS.md rule 3).
    """
    root = home if home is not None else paths.home()
    return root / ".agents" / "skills"


def installer_lockfile(home: Path | None = None) -> Path:
    """Return the installer lockfile path (``$HOME/.agents/.skill-lock.json``)."""
    root = home if home is not None else paths.home()
    return root / ".agents" / ".skill-lock.json"


#: Outcome codes returned by :func:`read_json_guarded` alongside the
#: ERR_* constants it can reuse from :mod:`skill_lens.models.parsing`.
ERR_MISSING_FILE = "missing"
ERR_NOT_JSON = "not_json"


#: ``errno`` values that mean "the OS refused us", not "the file is absent".
_PERMISSION_ERRNOS = frozenset({1, 13})  # EPERM, EACCES


def read_json_guarded(path: Path) -> tuple[Any | None, str | None]:
    """Read a JSON file without letting a refusal raise.

    Returns ``(value, None)`` on success, ``(None, error)`` where ``error`` is
    :data:`~skill_lens.models.parsing.ERR_PERMISSION_DENIED` for an OS
    refusal, :data:`ERR_NOT_JSON` for a file that is not valid JSON, or
    :data:`ERR_MISSING_FILE` when the path is absent. A missing lockfile is
    not a defect -- the user may never have run an installer -- so callers
    report it, they do not invent it.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None, ERR_NOT_JSON
    except FileNotFoundError:
        return None, ERR_MISSING_FILE
    except PermissionError:
        return None, ERR_PERMISSION_DENIED
    except OSError as exc:
        # A symlink to a target we cannot open surfaces as ENOENT/EACCES here;
        # both mean "there is content we cannot read", not "there is no file".
        if exc.errno in _PERMISSION_ERRNOS:
            return None, ERR_PERMISSION_DENIED
        return None, ERR_NOT_JSON
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        return None, ERR_NOT_JSON


def live_discovery(
    cwd: Path | None = None,
    registry: dict[str, AgentDefinition] | None = None,
) -> DiscoveryIndex:
    """Run a full discovery pass against the live (or sandboxed) environment.

    ``cwd`` defaults to the terminal folder; the sandbox switch in
    :mod:`skill_lens.core.paths` decides whether "live" means the real
    ``$HOME`` or a mock one, so this is the single entry point both ``doctor``
    and ``compare`` use. All OSError guarding lives in the walk it delegates
    to -- one unreadable directory produces a tagged
    :class:`~skill_lens.core.discovery.UnreadableRoot`, not a traceback.
    """
    home = paths.home()
    working_dir = cwd if cwd is not None else paths.terminal_cwd()
    return discover(home, working_dir, registry)
