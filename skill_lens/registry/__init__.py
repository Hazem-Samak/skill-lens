"""Agent definitions for Skill Lens.

Each agent is described by a TOML file in ``agents/``. Every root and rule
carries an ``evidence`` tag (documented, empirical, inferred) and a stable
``rule_id`` so resolution reasons are machine-checkable and never invented.
"""

from __future__ import annotations

from pathlib import Path

REGISTRY_DIR = Path(__file__).parent / "agents"

__all__ = ["REGISTRY_DIR"]
