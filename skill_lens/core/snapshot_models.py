"""Inert snapshot data structures for TUI session capture (Assignment C2).

Specification reference: FULL_SCREEN_TUI.md §21.2.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from skill_lens.core.discovery import DiscoveredEntry, UnreadableRoot
from skill_lens.registry.loader import AgentDefinition

if TYPE_CHECKING:
    from skill_lens.core.scanner import ScanReport
    from skill_lens.models.doctor import DoctorReport


@dataclass(frozen=True, slots=True)
class CapturedFile:
    """A captured file belonging to a skill installation."""

    relative_path: str
    data: bytes
    fingerprint: str


@dataclass(frozen=True, slots=True)
class CapturedInput:
    """Captured configuration or lockfile input."""

    path: str
    data: bytes | None
    error: Literal["missing", "unreadable"] | None


@dataclass(frozen=True, slots=True)
class FrozenDiscoveryIndex:
    """Tuple-backed frozen discovery index."""

    home: str
    cwd: str
    entries: tuple[DiscoveredEntry, ...] = ()
    unreadable_roots: tuple[UnreadableRoot, ...] = ()

    def all_agents(self) -> set[str]:
        """Return the set of agent IDs reached by hits across all entries."""
        return {hit.agent_id for entry in self.entries for hit in entry.hits}


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    """An inert published capture of an entire inspection session."""

    generation: int
    home: Path
    cwd: Path
    registry: tuple[AgentDefinition, ...]
    index: FrozenDiscoveryIndex
    files: Mapping[str, tuple[CapturedFile, ...]]
    config_inputs: Mapping[str, CapturedInput]
    disabled_overrides: Mapping[str, frozenset[str]]
    display_paths: Mapping[str, str]
    same_locations: frozenset[tuple[str, str]]
    scan: ScanReport
    doctor: DoctorReport


__all__ = [
    "CapturedFile",
    "CapturedInput",
    "FrozenDiscoveryIndex",
    "SessionSnapshot",
]
