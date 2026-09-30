"""The physical side of the model: a discovered skill installation on disk."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from skill_lens.models.enums import ParseStatus, Scope


@dataclass(frozen=True, slots=True)
class SkillInstallation:
    """A single physical installation of a skill (a directory or standalone file).

    Identity is deliberately split in two, per the specification:

    * ``entrypoint_path`` is what the agent literally resolves (a symlink wins
      project precedence), and
    * ``canonical_path`` is the real target used for inventory deduplication.

    A symlink farm therefore reports one canonical library with many
    ``agent_entrypoints`` rather than N duplicate installations.
    """

    name: str
    entrypoint_path: str
    canonical_path: str
    scope: Scope
    parse_status: ParseStatus
    content_hash: str | None = None
    description: str | None = None
    frontmatter_name: str | None = None
    is_symlink: bool = False
    agent_entrypoints: tuple[str, ...] = field(default_factory=tuple)
    variant_label: str | None = None
    errors: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "entrypoint_path": self.entrypoint_path,
            "canonical_path": self.canonical_path,
            "scope": self.scope.value,
            "parse_status": self.parse_status.value,
            "content_hash": self.content_hash,
            "description": self.description,
            "frontmatter_name": self.frontmatter_name,
            "is_symlink": self.is_symlink,
            "agent_entrypoints": list(self.agent_entrypoints),
            "variant_label": self.variant_label,
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillInstallation:
        return cls(
            name=data["name"],
            entrypoint_path=data["entrypoint_path"],
            canonical_path=data["canonical_path"],
            scope=Scope(data["scope"]),
            parse_status=ParseStatus(data["parse_status"]),
            content_hash=data.get("content_hash"),
            description=data.get("description"),
            frontmatter_name=data.get("frontmatter_name"),
            is_symlink=bool(data.get("is_symlink", False)),
            agent_entrypoints=tuple(data.get("agent_entrypoints", ())),
            variant_label=data.get("variant_label"),
            errors=tuple(data.get("errors", ())),
        )
