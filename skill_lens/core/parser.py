"""Frontmatter parsing, identity extraction and symlink canonicalization.

This module is intentionally free of any agent-specific precedence logic --
that is the resolver's job (Phase 2). Here we only answer two questions:

1. *What does this skill document say about itself?*  (parsing + identity)
2. *What real thing does this entrypoint point at?*     (canonicalization)
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import yaml

from skill_lens.models.enums import ParseStatus
from skill_lens.models.parsing import (
    ERR_DANGLING_SYMLINK,
    ERR_MALFORMED_YAML,
    ERR_MISSING_DESCRIPTION,
    ERR_MISSING_FRONTMATTER,
    ERR_PERMISSION_DENIED,
    ERR_SYMLINK_CYCLE,
    ERR_UNDECODABLE_TEXT,
    CanonicalResult,
    CanonicalStatus,
    ParseResult,
)

FRONTMATTER_DELIM = "---"
_SKILL_FILENAMES = ("SKILL.md", "skill.md")


# --- Discovery -------------------------------------------------------------


def find_skill_document(entrypoint: Path) -> Path | None:
    """Locate the markdown document for an entrypoint.

    Supports both directory skills (``name/SKILL.md``) and Antigravity's
    standalone file skills (``name.md``). Returns ``None`` when neither exists.
    """
    if entrypoint.is_dir():
        for filename in _SKILL_FILENAMES:
            candidate = entrypoint / filename
            if candidate.is_file():
                return candidate
        return None
    if entrypoint.is_file() and entrypoint.suffix.lower() == ".md":
        return entrypoint
    return None


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Split a document into ``(frontmatter_text, body)``.

    ``frontmatter_text`` is ``None`` when the document does not open with a
    ``---`` fence, or when the closing fence is missing. A leading UTF-8 BOM
    is tolerated.
    """
    stripped = text.lstrip("\ufeff")
    if not stripped.startswith(FRONTMATTER_DELIM):
        return None, stripped

    lines = stripped.splitlines()
    # The first line must be exactly the delimiter (allow trailing whitespace).
    if lines[0].strip() != FRONTMATTER_DELIM:
        return None, stripped

    for index in range(1, len(lines)):
        if lines[index].strip() == FRONTMATTER_DELIM:
            frontmatter = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1 :])
            if body and not body.endswith("\n"):
                body += "\n"
            return frontmatter, body
    return None, stripped


def _coerce_description(value: object) -> str | None:
    """Normalise a description value into a non-empty string, or ``None``."""
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def parse_skill_document(path: Path) -> ParseResult:
    """Parse one skill document into a :class:`ParseResult`.

    Never raises: unreadable files become ``UNREADABLE`` results so a single
    bad file can never abort a scan.
    """
    directory_name = path.parent.name if path.name.lower() in _SKILL_FILENAMES else path.stem

    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ParseResult(
            status=ParseStatus.UNREADABLE,
            directory_name=directory_name,
            body="",
            source_path=str(path),
            errors=(ERR_UNDECODABLE_TEXT,),
        )
    except OSError:
        return ParseResult(
            status=ParseStatus.UNREADABLE,
            directory_name=directory_name,
            body="",
            source_path=str(path),
            errors=(ERR_PERMISSION_DENIED,),
        )

    frontmatter_text, body = split_frontmatter(raw)
    if frontmatter_text is None:
        return ParseResult(
            status=ParseStatus.MALFORMED_YAML,
            directory_name=directory_name,
            body=body,
            source_path=str(path),
            errors=(ERR_MISSING_FRONTMATTER,),
        )

    try:
        loaded = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError:
        return ParseResult(
            status=ParseStatus.MALFORMED_YAML,
            directory_name=directory_name,
            body=body,
            source_path=str(path),
            errors=(ERR_MALFORMED_YAML,),
        )

    if not isinstance(loaded, dict):
        return ParseResult(
            status=ParseStatus.MALFORMED_YAML,
            directory_name=directory_name,
            body=body,
            source_path=str(path),
            errors=(ERR_MALFORMED_YAML,),
        )

    frontmatter = {str(key): value for key, value in loaded.items()}
    name_value = loaded.get("name")
    frontmatter_name = (
        str(name_value).strip() if isinstance(name_value, (str, int, float)) else None
    )
    if not frontmatter_name:
        frontmatter_name = None

    description = _coerce_description(loaded.get("description"))
    if description is None:
        return ParseResult(
            status=ParseStatus.MISSING_DESCRIPTION,
            directory_name=directory_name,
            body=body,
            frontmatter_name=frontmatter_name,
            source_path=str(path),
            errors=(ERR_MISSING_DESCRIPTION,),
            frontmatter=frontmatter,
        )

    return ParseResult(
        status=ParseStatus.VALID,
        directory_name=directory_name,
        body=body,
        frontmatter_name=frontmatter_name,
        description=description,
        source_path=str(path),
        frontmatter=frontmatter,
    )


def parse_skill(entrypoint: Path) -> ParseResult | None:
    """Discover and parse the document behind ``entrypoint``.

    Returns ``None`` when the entrypoint holds no skill document at all. A
    directory that exists but cannot be listed (e.g. blocked by macOS TCC) is
    reported as ``UNREADABLE`` rather than silently dropped.
    """
    document = find_skill_document(entrypoint)
    if document is None:
        if is_unreadable_directory(entrypoint):
            return ParseResult(
                status=ParseStatus.UNREADABLE,
                directory_name=entrypoint.name,
                body="",
                source_path=str(entrypoint),
                errors=(ERR_PERMISSION_DENIED,),
            )
        return None
    return parse_skill_document(document)


def is_unreadable_directory(path: Path) -> bool:
    """True when ``path`` is a directory that cannot be listed.

    Used to record permission-blocked roots (macOS TCC) as ``unreadable``
    instead of failing the whole walk.
    """
    if not path.is_dir():
        return False
    try:
        os.listdir(path)
    except OSError:
        return True
    return False


# --- Symlink canonicalization ---------------------------------------------


def _physical(path: Path) -> str:
    """The fully resolved physical path, normalized.

    A symlink farm commonly uses *relative* targets
    (``~/.pi/agent/skills/../.agents/skills/x``), so the walked path still
    contains ``..`` segments. Without normalization every agent's link into the
    same shared library yields a different string, and the library stops being
    reported as one canonical skill with N entrypoints. ``realpath`` also
    resolves any remaining symlinked parent directories.
    """
    return os.path.realpath(str(path))


def canonicalize(entrypoint: Path) -> CanonicalResult:
    """Follow ``entrypoint`` to its real target, guarding against cycles.

    Only **symlink** nodes are tracked (via ``lstat``), so a legitimate chain
    that ends at a real directory reports ``OK`` while a circular chain of
    links is caught and reported as ``CYCLE`` instead of hanging. Broken links
    report ``BROKEN``; permission failures report ``UNREADABLE``.
    """
    path = Path(entrypoint)
    is_symlink = path.is_symlink()
    visited: set[tuple[int, int]] = set()

    for _ in range(64):  # hard stop; real chains are far shorter
        try:
            link_stat = path.lstat()
        except FileNotFoundError:
            return CanonicalResult(
                status=CanonicalStatus.BROKEN,
                entrypoint_path=str(entrypoint),
                resolved_path=None,
                is_symlink=is_symlink,
                error=ERR_DANGLING_SYMLINK,
            )
        except OSError:
            return CanonicalResult(
                status=CanonicalStatus.UNREADABLE,
                entrypoint_path=str(entrypoint),
                resolved_path=None,
                is_symlink=is_symlink,
                error=ERR_PERMISSION_DENIED,
            )

        if not stat.S_ISLNK(link_stat.st_mode):
            return CanonicalResult(
                status=CanonicalStatus.OK,
                entrypoint_path=str(entrypoint),
                resolved_path=_physical(path),
                is_symlink=is_symlink,
            )

        key = (link_stat.st_dev, link_stat.st_ino)
        if key in visited:
            return CanonicalResult(
                status=CanonicalStatus.CYCLE,
                entrypoint_path=str(entrypoint),
                resolved_path=None,
                is_symlink=is_symlink,
                error=ERR_SYMLINK_CYCLE,
            )
        visited.add(key)

        try:
            target = os.readlink(path)
        except OSError:
            return CanonicalResult(
                status=CanonicalStatus.UNREADABLE,
                entrypoint_path=str(entrypoint),
                resolved_path=None,
                is_symlink=True,
                error=ERR_PERMISSION_DENIED,
            )
        path = Path(target) if os.path.isabs(target) else path.parent / target

    return CanonicalResult(
        status=CanonicalStatus.CYCLE,
        entrypoint_path=str(entrypoint),
        resolved_path=None,
        is_symlink=is_symlink,
        error=ERR_SYMLINK_CYCLE,
    )
