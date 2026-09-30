"""Data contracts for parsing and symlink canonicalization (Phase 1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from skill_lens.models.enums import ParseStatus


class CanonicalStatus(StrEnum):
    """Outcome of resolving a possibly-symlinked entrypoint to a real path."""

    OK = "ok"
    BROKEN = "broken"
    CYCLE = "cycle"
    UNREADABLE = "unreadable"


# --- Error codes -----------------------------------------------------------
# Stable, machine-checkable identifiers. Never embed free-text messages here;
# the golden fixtures compare against these exact strings.
ERR_MISSING_FRONTMATTER = "missing_frontmatter"
ERR_MALFORMED_YAML = "malformed_yaml"
ERR_MISSING_DESCRIPTION = "missing_description"
ERR_UNDECODABLE_TEXT = "undecodable_text"
ERR_SYMLINK_CYCLE = "symlink_cycle"
ERR_DANGLING_SYMLINK = "dangling_symlink"
ERR_PERMISSION_DENIED = "permission_denied"


def _jsonable(value: Any) -> Any:
    """Coerce YAML values into JSON-serializable primitives."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return str(value)


@dataclass(frozen=True, slots=True)
class CanonicalResult:
    """The result of following a symlink chain to its canonical target."""

    status: CanonicalStatus
    entrypoint_path: str
    resolved_path: str | None
    is_symlink: bool
    error: str | None = None

    @property
    def is_ok(self) -> bool:
        return self.status is CanonicalStatus.OK

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "entrypoint_path": self.entrypoint_path,
            "resolved_path": self.resolved_path,
            "is_symlink": self.is_symlink,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class ParseResult:
    """Everything the parser learned from one skill document.

    ``directory_name`` and ``frontmatter_name`` are kept separate because
    agents disagree on identity: Claude uses the directory name while Codex
    uses the frontmatter ``name``. The resolver picks between them.
    """

    status: ParseStatus
    directory_name: str
    body: str
    frontmatter_name: str | None = None
    description: str | None = None
    source_path: str | None = None
    errors: tuple[str, ...] = ()
    frontmatter: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    @property
    def is_valid(self) -> bool:
        return self.status is ParseStatus.VALID

    @property
    def identity(self) -> str:
        """Best-effort display identity (frontmatter name wins when present)."""
        return self.frontmatter_name or self.directory_name

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "directory_name": self.directory_name,
            "frontmatter_name": self.frontmatter_name,
            "description": self.description,
            "source_path": self.source_path,
            "identity": self.identity,
            "errors": list(self.errors),
            "frontmatter": {key: _jsonable(value) for key, value in self.frontmatter.items()},
        }
