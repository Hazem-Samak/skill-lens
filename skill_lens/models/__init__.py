"""Frozen, machine-readable data contracts for Skill Lens.

Presentation (Rich) is always a layer on top of these models -- never the
other way around.
"""

from __future__ import annotations

import json
from typing import Any

from skill_lens.models.diff import (
    DiffChange,
    DiffCopy,
    DiffFile,
    DiffHunk,
    DiffReport,
)
from skill_lens.models.doctor import DoctorFinding
from skill_lens.models.enums import (
    Collision,
    Evidence,
    HeadlineState,
    ParseStatus,
    Scope,
    Severity,
    Visibility,
)
from skill_lens.models.installation import SkillInstallation
from skill_lens.models.parsing import (
    CanonicalResult,
    CanonicalStatus,
    ParseResult,
)
from skill_lens.models.resolution import CandidateResolution, ResolutionReport

__all__ = [
    "CandidateResolution",
    "CanonicalResult",
    "CanonicalStatus",
    "Collision",
    "DiffChange",
    "DiffCopy",
    "DiffFile",
    "DiffHunk",
    "DiffReport",
    "DoctorFinding",
    "Evidence",
    "HeadlineState",
    "ParseResult",
    "ParseStatus",
    "ResolutionReport",
    "Scope",
    "Severity",
    "SkillInstallation",
    "Visibility",
    "dumps",
]


def dumps(value: Any) -> str:
    """Serialize a model (or container of models) to canonical JSON.

    Uses ``sort_keys=True`` so output is byte-stable and directly comparable
    against golden ``expected.json`` fixtures.
    """
    return json.dumps(value, sort_keys=True, indent=2)
