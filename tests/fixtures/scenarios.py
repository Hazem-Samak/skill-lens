"""The 12 golden fixture scenarios from the specification (section 7).

Each scenario is a *builder* that materializes a mock ``$HOME`` tree. The
hand-written expectations live beside them in ``golden/<name>.json`` and are
the source of truth the tests verify against.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from tests.fixtures.builders import (
    make_skill,
    skill_markdown,
    symlink,
    write_skill,
    write_text,
)

# --- 1. claude_personal_beats_project -------------------------------------


def claude_personal_beats_project(home: Path) -> None:
    """Personal ``~/.claude/skills`` copy overrides the project copy."""
    (home / "project" / ".git").mkdir(parents=True, exist_ok=True)
    make_skill(home / ".claude" / "skills" / "deploy", "deploy", "Personal deploy helper.")
    make_skill(
        home / "project" / ".claude" / "skills" / "deploy",
        "deploy",
        "Project deploy helper.",
        body="# Instructions\n\nProject-specific deploy.\n",
    )


# --- 2. claude_nested_qualification ---------------------------------------


def claude_nested_qualification(home: Path) -> None:
    """A monorepo subdirectory skill loads as ``dir:skill`` alongside personal."""
    (home / "project" / ".git").mkdir(parents=True, exist_ok=True)
    make_skill(home / ".claude" / "skills" / "deploy", "deploy", "Personal deploy helper.")
    make_skill(
        home / "project" / "apps" / "web" / ".claude" / "skills" / "deploy",
        "deploy",
        "Web app deploy helper.",
        body="# Instructions\n\nDeploy the web app only.\n",
    )


# --- 3. symlink_farm_multi_agent ------------------------------------------


def symlink_farm_multi_agent(home: Path) -> None:
    """One canonical library, three agent entrypoints via symlink."""
    canonical = home / ".agents" / "skills" / "shared"
    make_skill(canonical, "shared", "Shared capability.")
    for root in (".claude/skills", ".pi/agent/skills", ".qoder/skills"):
        symlink(canonical, home / root / "shared")


# --- 4. symlink_cycle_guard -----------------------------------------------


def symlink_cycle_guard(home: Path) -> None:
    """A two-node symlink cycle is flagged ``[INVALID]`` without hanging."""
    skills = home / ".agents" / "skills"
    symlink(skills / "cycle_b", skills / "cycle_a")
    symlink(skills / "cycle_a", skills / "cycle_b")


# --- 5. antigravity_file_based --------------------------------------------


def antigravity_file_based(home: Path) -> None:
    """Antigravity loads a standalone ``.md`` skill beside directory skills."""
    root = home / ".gemini" / "config" / "skills"
    write_skill(root, skill_markdown("deploy", "Standalone deploy skill."), filename="deploy.md")
    make_skill(root / "other", "other", "Another skill.")


# --- 6. tcc_permission_error ----------------------------------------------


def tcc_permission_error(home: Path) -> None:
    """A permission-blocked directory is recorded unreadable; scan continues."""
    make_skill(home / ".claude" / "skills" / "ok", "ok", "Accessible skill.")
    blocked = home / ".claude" / "skills" / "blocked"
    blocked.mkdir(parents=True, exist_ok=True)
    make_skill(blocked, "blocked", "Should be unreadable.")
    os.chmod(blocked, 0o000)


def restore_tcc_permission_error(home: Path) -> None:
    """Restore permissions so tmp_path cleanup can remove the tree."""
    blocked = home / ".claude" / "skills" / "blocked"
    if blocked.exists():
        os.chmod(blocked, 0o755)


# --- 7. opencode_ambiguous -------------------------------------------------


def opencode_ambiguous(home: Path) -> None:
    """Two same-rank searched roots collide with no documented winner."""
    make_skill(home / ".config" / "opencode" / "skills" / "dup", "dup", "OpenCode native dup.")
    make_skill(home / ".agents" / "skills" / "dup", "dup", "Shared dup.")


# --- 8. variant_hash_detection --------------------------------------------


def variant_hash_detection(home: Path) -> None:
    """Differing bytes for one name produce Variant A / Variant B labels.

    The descriptions deliberately do not claim a letter: the label is assigned
    by scope, not by the order they are written here.
    """
    make_skill(
        home / ".agents" / "skills" / "deploy",
        "deploy",
        "Shared-library deploy.",
        body="# Instructions\n\nShared-library body.\n",
    )
    make_skill(
        home / ".claude" / "skills" / "deploy",
        "deploy",
        "Personal deploy.",
        body="# Instructions\n\nPersonal body.\n",
    )


# --- 9. worktree_dotgit_file ----------------------------------------------


def worktree_dotgit_file(home: Path) -> None:
    """``.git`` as a file (linked worktree) still bounds the upward walk."""
    write_text(
        home / "project" / ".git",
        "gitdir: /tmp/elsewhere/.git/worktrees/project\n",
    )
    make_skill(home / "project" / ".agents" / "skills" / "wt", "wt", "Worktree skill.")


# --- 10. system_container_traversal ---------------------------------------


def system_container_traversal(home: Path) -> None:
    """Hidden ``.system/`` is a transparent container, not a skill name."""
    make_skill(
        home / ".codex" / "skills" / ".system" / "imagegen",
        "imagegen",
        "Bundled imagegen.",
    )


# --- 11. disabled_override -------------------------------------------------


def disabled_override(home: Path) -> None:
    """Agent settings explicitly disable a discovered skill."""
    make_skill(home / ".claude" / "skills" / "legacy", "legacy", "Legacy skill.")
    write_text(
        home / ".claude" / "settings.json",
        '{\n  "skillOverrides": {"legacy": false}\n}\n',
    )


# --- 12. malformed_frontmatter --------------------------------------------


def malformed_frontmatter(home: Path) -> None:
    """Invalid YAML and a missing required description both yield ``[INVALID]``."""
    write_skill(
        home / ".claude" / "skills" / "broken",
        "---\nname: [unclosed\ndescription: nope\n---\nbody\n",
    )
    write_skill(
        home / ".claude" / "skills" / "nodesc",
        "---\nname: nodesc\n---\n# Body without a description.\n",
    )


# --- 13. project_beats_global ---------------------------------------------


def project_beats_global(home: Path) -> None:
    """A project copy outranks the global copy for every agent that says so.

    Regression scenario for the inverted-rank defect: six agents declare
    ``Shadow (Project > Global)`` in their own registry, so each of them must
    resolve the *project* copy ACTIVE. Each agent gets its own skill name so
    every resolution has exactly two clean candidates and cannot be confused
    with another agent's roots.
    """
    (home / "project" / ".git").mkdir(parents=True, exist_ok=True)
    # (global root, project root, skill name) -- the agent's *real* roots.
    cases: tuple[tuple[str, str, str], ...] = (
        (".gemini/config/skills", ".agents/skills", "pg_antigravity"),
        (".pi/agent/skills", ".pi/skills", "pg_pi"),
        (".grok/skills", ".agents/skills", "pg_grok"),
        (".qoder/skills", ".qoder/skills", "pg_qoder"),
        (".codeium/windsurf/skills", ".windsurf/skills", "pg_windsurf"),
        (".omp/agent", ".omp/skills", "pg_omp"),
    )
    for global_root, project_root, name in cases:
        make_skill(
            home / global_root / name,
            name,
            "Global copy.",
            body="# Instructions\n\nGlobal body.\n",
        )
        make_skill(
            home / "project" / project_root / name,
            name,
            "Project copy.",
            body="# Instructions\n\nProject body.\n",
        )


# --- Registry --------------------------------------------------------------

_SCENARIOS: dict[str, Callable[[Path], None]] = {
    "claude_personal_beats_project": claude_personal_beats_project,
    "claude_nested_qualification": claude_nested_qualification,
    "symlink_farm_multi_agent": symlink_farm_multi_agent,
    "symlink_cycle_guard": symlink_cycle_guard,
    "antigravity_file_based": antigravity_file_based,
    "tcc_permission_error": tcc_permission_error,
    "opencode_ambiguous": opencode_ambiguous,
    "variant_hash_detection": variant_hash_detection,
    "worktree_dotgit_file": worktree_dotgit_file,
    "system_container_traversal": system_container_traversal,
    "disabled_override": disabled_override,
    "malformed_frontmatter": malformed_frontmatter,
    "project_beats_global": project_beats_global,
}

_TEARDOWN: dict[str, Callable[[Path], None]] = {
    "tcc_permission_error": restore_tcc_permission_error,
}

SCENARIO_NAMES: tuple[str, ...] = tuple(_SCENARIOS)


def build_scenario(name: str, home: Path) -> None:
    """Materialize scenario ``name`` into ``home`` (a mock ``$HOME``)."""
    if name not in _SCENARIOS:
        raise KeyError(f"unknown scenario: {name}")
    _SCENARIOS[name](home)


def teardown_scenario(name: str, home: Path) -> None:
    """Undo any permission changes so fixture directories remain removable."""
    _TEARDOWN.get(name, lambda _home: None)(home)
