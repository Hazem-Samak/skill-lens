"""The Phase 0.5 acceptance sandbox: a synthetic multi-agent skill farm.

This mirrors the topology described in the specification (section 1) at a
small, deterministic scale: one canonical library fanned out to several agent
symlink roots, plus system, project and plugin skills. The structural
reconciliation test uses it to prove that a future ``scan`` groups canonical
libraries rather than counting every symlink as a separate installation.
"""

from __future__ import annotations

from pathlib import Path

from tests.fixtures.builders import make_skill, relative_symlink

CANONICAL_SKILLS: tuple[str, ...] = ("alpha", "beta", "gamma", "delta", "epsilon")
AGENT_FARMS: tuple[str, ...] = (".claude/skills", ".pi/agent/skills", ".qoder/skills")
SYSTEM_SKILL = "omega"
PROJECT_SKILL = "projskill"
PLUGIN_SKILL = "plugskill"


def build_acceptance_farm(home: Path) -> None:
    """Materialize the canonical library and every consumer root in ``home``."""
    canonical_root = home / ".agents" / "skills"
    for name in CANONICAL_SKILLS:
        make_skill(canonical_root / name, name, f"Canonical {name} capability.")

    for root in AGENT_FARMS:
        for name in CANONICAL_SKILLS:
            # Relative targets, exactly as a real farm is built, so the
            # canonical path must be normalized for these to merge.
            relative_symlink(canonical_root / name, home / root / name)

    make_skill(
        home / ".codex" / "skills" / ".system" / SYSTEM_SKILL,
        SYSTEM_SKILL,
        "Bundled Codex system skill.",
    )
    make_skill(
        home / "project" / ".agents" / "skills" / PROJECT_SKILL,
        PROJECT_SKILL,
        "Project-scoped skill.",
    )
    make_skill(
        home / ".codex" / ".tmp" / "plugins" / "plug" / "skills" / PLUGIN_SKILL,
        PLUGIN_SKILL,
        "Plugin-downloaded skill.",
    )


def canonical_entrypoint_count() -> int:
    """Total symlink entrypoints expected across the agent farms."""
    return len(CANONICAL_SKILLS) * len(AGENT_FARMS)
