"""A minimal test-only filesystem walk over fixture homes.

This is **not** the Phase 4 live scanner. It exists so fixture tests can locate
skill entrypoints deterministically without depending on agent precedence
rules. It deliberately does not follow symlinked directories: a symlink entry
is itself the installation, and its target is what we canonicalize.
"""

from __future__ import annotations

import os
from pathlib import Path

from skill_lens.core.parser import find_skill_document
from skill_lens.registry.loader import load_registry


def _candidate_roots(home: Path) -> list[Path]:
    """Directories that may hold skill entrypoints, in deterministic order.

    Two sources, because a real agent root is not always called ``skills``:
    every directory named ``skills``, plus every home-relative global root the
    registry declares (e.g. ``~/.omp/agent``). Project roots are already covered
    by the ``skills`` directories beneath the fixture's project tree.
    """
    roots = {p for p in home.rglob("skills") if p.is_dir() and not p.is_symlink()}
    for agent in load_registry().values():
        for root in agent.roots:
            if root.is_project or root.is_absolute:
                continue
            candidate = home / root.path
            if candidate.is_dir() and not candidate.is_symlink():
                roots.add(candidate)
    return sorted(roots)


def list_skill_entrypoints(home: Path) -> list[Path]:
    """Return every skill entrypoint (dir or standalone file) under ``home``.

    ``.system`` is treated as a transparent container: the skills *inside* it
    are entrypoints, but ``.system`` itself is not a skill name. A directory
    that holds a skill document, or that cannot be read at all, is an
    entrypoint. Permission errors never abort the walk.
    """
    entries: list[Path] = []
    for root in _candidate_roots(home):
        for child in _safe_list(root):
            if child.is_symlink():
                entries.append(child)
            elif child.is_dir():
                if child.name == ".system":
                    entries.extend(_safe_list(child))
                elif find_skill_document(child) is not None or blocked_by_permissions(child):
                    entries.append(child)
            elif child.suffix.lower() == ".md":
                entries.append(child)
    return entries


def _safe_list(directory: Path) -> list[Path]:
    try:
        return sorted(directory.iterdir(), key=lambda p: p.name)
    except OSError:
        return []


def is_under(path: Path, ancestor: Path) -> bool:
    """True when ``path`` lies within ``ancestor``."""
    try:
        path.relative_to(ancestor)
    except ValueError:
        return False
    return True


def blocked_by_permissions(path: Path) -> bool:
    """True when a directory exists but cannot be listed (e.g. macOS TCC)."""
    if not path.is_dir():
        return False
    try:
        os.listdir(path)
    except OSError:
        return True
    return False
