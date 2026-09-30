"""Fixture builders for golden scenarios.

These helpers materialize *mock homes* under ``tmp_path``. They must never
touch a real ``$HOME`` -- see AGENTS.md rule 2.
"""

from __future__ import annotations

import os
from pathlib import Path

FRONTMATTER_DELIM = "---"


def skill_markdown(
    name: str,
    description: str,
    body: str = "# Instructions\n\nDo the thing.\n",
    extra: dict[str, str] | None = None,
) -> str:
    """Render a well-formed ``SKILL.md`` document with YAML frontmatter."""
    lines = [FRONTMATTER_DELIM, f"name: {name}", f"description: {description}"]
    for key, value in (extra or {}).items():
        lines.append(f"{key}: {value}")
    lines.append(FRONTMATTER_DELIM)
    return "\n".join(lines) + "\n" + body


def write_skill(
    directory: Path,
    markdown: str,
    filename: str = "SKILL.md",
) -> Path:
    """Write a skill document into ``directory`` (created if needed)."""
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename
    target.write_text(markdown, encoding="utf-8")
    return target


def make_skill(
    directory: Path,
    name: str,
    description: str,
    body: str = "# Instructions\n\nDo the thing.\n",
    extra: dict[str, str] | None = None,
) -> Path:
    """Convenience: build and write a full ``SKILL.md`` in one call."""
    return write_skill(directory, skill_markdown(name, description, body, extra))


def symlink(target: Path, link: Path) -> Path:
    """Create a directory symlink at ``link`` pointing to ``target``.

    Relative targets are preserved verbatim so the farm mirrors the real
    ``~/.agents/skills`` layout used on developer machines.
    """
    link.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(target, link, target_is_directory=True)
    return link


def write_text(path: Path, content: str) -> Path:
    """Write UTF-8 text, creating parent directories as required."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
