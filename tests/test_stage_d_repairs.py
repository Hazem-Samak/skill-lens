"""Stage D (F01/F02) authoritative regression suite.

Covers:
1. Proved Claude command identities (hybrid: frontmatter name and directory invocation).
2. Claude configuration stack (local > project > user) and 4-state skillOverrides
   (off/false, on/true, user-invocable-only, name-only).
3. Claude loadability: optional description with body-line fallback.
4. Codex path-based [[skills.config]] disabled controls.
5. OpenCode V2 sources, path-derived IDs, recursive discovery, permissions (deny/ask/allow/*),
   optional frontmatter, and optional description.
6. Pi frontmatter name with folder fallback, stop-at-skill, and User > Project precedence.
7. Qoder User > Project precedence.
8. Antigravity CLI global ~/.gemini/antigravity-cli/skills vs IDE roots.
9. Oh My Pi (OMP) managed skills root, frontmatter enabled: false, provider loadability rules.
10. Snapshot capture-time configuration resolution, zero report-time disk reads, deep immutability,
    and CLI/captured parity.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from skill_lens.core import paths
from skill_lens.core.config import (
    ResolvedAgentControls,
    decode_claude_settings,
    decode_claude_settings_with_status,
    decode_codex_config,
    decode_codex_config_with_status,
    decode_opencode_permissions,
    decode_opencode_permissions_with_status,
    is_loadable_for_agent,
    resolve_agent_controls,
    resolve_candidate_controls,
    resolve_claude_settings,
)
from skill_lens.core.discovery import discover
from skill_lens.core.resolver import resolve_skill
from skill_lens.core.snapshot import (
    canonical_key,
    capture_session,
    snapshot_diff,
    snapshot_why,
)
from skill_lens.models.enums import (
    HeadlineState,
    InvocationPolicy,
    LoadabilityStatus,
    PermissionEffect,
    Scope,
)
from skill_lens.registry.loader import load_agent, load_registry
from tests.fixtures.builders import make_skill, write_skill

# ============================================================================
# 1. Claude Tests: Hybrid Identity, 4-State Overrides, Settings Precedence
# ============================================================================


def test_claude_hybrid_identity_matches_frontmatter_and_folder(tmp_path: Path) -> None:
    """Claude matches skills by declared frontmatter name AND folder name."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    skill_dir = tmp_path / ".claude" / "skills" / "my_folder"
    make_skill(skill_dir, "my_command", "Claude deploy tool")

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)

    # 1. Matches by frontmatter name
    res_cmd = resolve_skill(
        "my_command", "claude", cwd=tmp_path, home=tmp_path, index=idx, registry=reg
    )
    assert res_cmd.found is True
    assert res_cmd.headline is HeadlineState.ACTIVE

    # 2. Matches by directory name
    res_dir = resolve_skill(
        "my_folder", "claude", cwd=tmp_path, home=tmp_path, index=idx, registry=reg
    )
    assert res_dir.found is True
    assert res_dir.headline is HeadlineState.ACTIVE


def test_claude_settings_decoders_and_precedence(tmp_path: Path) -> None:
    """Claude settings decoders respect local > project > user precedence."""
    user_bytes = b'{"skillOverrides": {"s1": false, "s2": "on", "s3": "user-invocable-only"}}'
    proj_bytes = b'{"skillOverrides": {"s1": true, "s4": "name-only"}}'
    local_bytes = b'{"skillOverrides": {"s1": "off"}}'

    user_cfg = decode_claude_settings(user_bytes)
    assert user_cfg == {"s1": False, "s2": "on", "s3": "user-invocable-only"}

    proj_cfg = decode_claude_settings(proj_bytes)
    assert proj_cfg == {"s1": True, "s4": "name-only"}

    local_cfg = decode_claude_settings(local_bytes)
    assert local_cfg == {"s1": "off"}

    merged = resolve_claude_settings(user_cfg, proj_cfg, local_cfg)
    # s1 was False in user, True in proj, 'off' in local -> local wins ('off')
    assert merged["s1"] == "off"
    assert merged["s2"] == "on"
    assert merged["s3"] == "user-invocable-only"
    assert merged["s4"] == "name-only"


@pytest.mark.parametrize(
    ("override_val", "expected_state", "expected_inv", "expected_perm"),
    [
        (False, HeadlineState.DISABLED, InvocationPolicy.NONE, PermissionEffect.DENY),
        ("off", HeadlineState.DISABLED, InvocationPolicy.NONE, PermissionEffect.DENY),
        (True, HeadlineState.ACTIVE, InvocationPolicy.ALL, PermissionEffect.ALLOW),
        ("on", HeadlineState.ACTIVE, InvocationPolicy.ALL, PermissionEffect.ALLOW),
        (
            "user-invocable-only",
            HeadlineState.ACTIVE,
            InvocationPolicy.USER_ONLY,
            PermissionEffect.ALLOW,
        ),
        ("name-only", HeadlineState.ACTIVE, InvocationPolicy.NAME_ONLY, PermissionEffect.ALLOW),
    ],
)
def test_claude_4_state_overrides_in_resolution(
    tmp_path: Path,
    override_val: bool | str,
    expected_state: HeadlineState,
    expected_inv: InvocationPolicy,
    expected_perm: PermissionEffect,
) -> None:
    """Claude resolution honors the 4-state skillOverrides."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    skill_dir = tmp_path / ".claude" / "skills" / "target"
    make_skill(skill_dir, "target", "Target skill")

    settings_file = tmp_path / ".claude" / "settings.json"
    settings_file.write_text(json.dumps({"skillOverrides": {"target": override_val}}))

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)
    res = resolve_skill("target", "claude", cwd=tmp_path, home=tmp_path, index=idx, registry=reg)

    assert res.headline is expected_state
    cand = res.candidates[0]
    assert cand.state is expected_state
    assert cand.invocation is expected_inv
    assert cand.permission is expected_perm


def test_claude_loadability_with_missing_description(tmp_path: Path) -> None:
    """Claude Code accepts skills with missing description using body-line fallback."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    skill_dir = tmp_path / ".claude" / "skills" / "nodesc"
    write_skill(skill_dir, "---\nname: nodesc\n---\n# Step 1: Run fallback\n")

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)
    res = resolve_skill("nodesc", "claude", cwd=tmp_path, home=tmp_path, index=idx, registry=reg)

    assert res.headline is HeadlineState.ACTIVE
    assert res.candidates[0].loadability is LoadabilityStatus.LOADABLE


# ============================================================================
# 2. Codex Tests: Path-Based [[skills.config]] Disabled Controls
# ============================================================================


def test_codex_path_based_disabled_config(tmp_path: Path) -> None:
    """Codex [[skills.config]] per-path enabled = false disables matched skill."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    skill_dir = tmp_path / ".codex" / "skills" / "calculator"
    make_skill(skill_dir, "calculator", "Math helper")

    # Disable by absolute path to SKILL.md per primary documentation
    abs_skill_md = str((skill_dir / "SKILL.md").resolve())
    codex_cfg = tmp_path / ".codex" / "config.toml"
    codex_cfg.parent.mkdir(parents=True, exist_ok=True)
    codex_cfg.write_text(f'[[skills.config]]\npath = "{abs_skill_md}"\nenabled = false\n')

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)
    res = resolve_skill("calculator", "codex", cwd=tmp_path, home=tmp_path, index=idx, registry=reg)

    assert res.headline is HeadlineState.DISABLED
    cand = res.candidates[0]
    assert cand.state is HeadlineState.DISABLED
    assert cand.invocation is InvocationPolicy.NONE
    assert cand.permission is PermissionEffect.DENY
    assert cand.rule_id == "codex_skills_config_disabled"

    # Relative paths without primary evidence are disclosed as unsupported in notes
    codex_cfg.write_text(
        '[[skills.config]]\npath = ".codex/skills/calculator/SKILL.md"\nenabled = false\n'
    )
    res_rel = resolve_skill(
        "calculator", "codex", cwd=tmp_path, home=tmp_path, index=idx, registry=reg
    )
    assert any("Relative path in Codex config is unsupported" in n for n in res_rel.notes)


def test_decode_codex_config_invalid_and_empty() -> None:
    """Codex config decoder safely handles missing, empty, or non-toml bytes."""
    assert decode_codex_config(None) == {}
    assert decode_codex_config(b"") == {}
    assert decode_codex_config(b"not a valid toml [[[[") == {}
    assert decode_codex_config(b'foo = "bar"') == {}


# ============================================================================
# 3. OpenCode V2 Tests: Sources, Precedence, Permissions, Discovery
# ============================================================================


def test_opencode_v2_source_registration_precedence(tmp_path: Path) -> None:
    """OpenCode V2 later-registered source wins across all 6 search roots."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    # Create same skill in all 6 roots with unique descriptions
    # Ranks:
    # 1. ~/.claude/skills (50)
    # 2. .claude/skills (55)
    # 3. ~/.agents/skills (60)
    # 4. .agents/skills (65)
    # 5. ~/.config/opencode/skills (70)
    # 6. .opencode/skills (80)
    roots = [
        (tmp_path / ".claude" / "skills" / "shared_tool", "claude_user"),
        (tmp_path / ".git_dummy" / ".claude" / "skills" / "shared_tool", "claude_proj"),
        (tmp_path / ".agents" / "skills" / "shared_tool", "agents_user"),
        (tmp_path / ".git_dummy" / ".agents" / "skills" / "shared_tool", "agents_proj"),
        (tmp_path / ".config" / "opencode" / "skills" / "shared_tool", "opencode_user"),
        (tmp_path / ".git_dummy" / ".opencode" / "skills" / "shared_tool", "opencode_proj"),
    ]
    for r, desc in roots:
        r.parent.mkdir(parents=True, exist_ok=True)
        make_skill(r, "shared_tool", desc)

    cwd = tmp_path / ".git_dummy"
    (cwd / ".git").mkdir()

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=cwd, registry=reg)
    res = resolve_skill("shared_tool", "opencode", cwd=cwd, home=tmp_path, index=idx, registry=reg)

    assert res.headline is HeadlineState.ACTIVE
    # Highest rank root is .opencode/skills (project, rank 80)
    winner = res.candidates[0]
    assert winner.state is HeadlineState.ACTIVE
    assert ".opencode/skills" in winner.installation.entrypoint_path
    assert winner.rank == 80


@pytest.mark.parametrize(
    ("perm_val", "expected_state", "expected_inv", "expected_perm"),
    [
        ("deny", HeadlineState.DISABLED, InvocationPolicy.NONE, PermissionEffect.DENY),
        ("ask", HeadlineState.ACTIVE, InvocationPolicy.ALL, PermissionEffect.ASK),
        ("allow", HeadlineState.ACTIVE, InvocationPolicy.ALL, PermissionEffect.ALLOW),
    ],
)
def test_opencode_v2_permissions_resolution(
    tmp_path: Path,
    perm_val: str,
    expected_state: HeadlineState,
    expected_inv: InvocationPolicy,
    expected_perm: PermissionEffect,
) -> None:
    """OpenCode V2 skill permissions: deny, ask, allow."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    skill_dir = tmp_path / ".config" / "opencode" / "skills" / "query"
    make_skill(skill_dir, "query", "Query tool")

    cfg_file = tmp_path / ".config" / "opencode" / "opencode.json"
    cfg_file.parent.mkdir(parents=True, exist_ok=True)
    cfg_file.write_text(
        json.dumps({"permissions": [{"action": "skill", "resource": "query", "effect": perm_val}]})
    )

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)
    res = resolve_skill("query", "opencode", cwd=tmp_path, home=tmp_path, index=idx, registry=reg)

    assert res.headline is expected_state
    cand = res.candidates[0]
    assert cand.state is expected_state
    assert cand.invocation is expected_inv
    assert cand.permission is expected_perm


def test_opencode_v2_wildcard_permission(tmp_path: Path) -> None:
    """OpenCode V2 wildcard '*' permission applies when skill is not named directly."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    skill_dir = tmp_path / ".config" / "opencode" / "skills" / "tool_a"
    make_skill(skill_dir, "tool_a", "Tool A")

    cfg_file = tmp_path / ".config" / "opencode" / "opencode.json"
    cfg_file.parent.mkdir(parents=True, exist_ok=True)
    cfg_file.write_text(
        json.dumps({"permissions": [{"action": "skill", "resource": "*", "effect": "ask"}]})
    )

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)
    res = resolve_skill("tool_a", "opencode", cwd=tmp_path, home=tmp_path, index=idx, registry=reg)

    assert res.headline is HeadlineState.ACTIVE
    assert res.candidates[0].permission is PermissionEffect.ASK


def test_opencode_v2_loadability_with_missing_frontmatter(tmp_path: Path) -> None:
    """OpenCode V2 accepts skills with no frontmatter."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    skill_file = tmp_path / ".config" / "opencode" / "skills" / "plain.md"
    skill_file.parent.mkdir(parents=True, exist_ok=True)
    skill_file.write_text("# Plain markdown skill without frontmatter\n")

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)
    res = resolve_skill("plain", "opencode", cwd=tmp_path, home=tmp_path, index=idx, registry=reg)

    assert res.found is True
    assert res.headline is HeadlineState.ACTIVE
    assert res.candidates[0].loadability is LoadabilityStatus.LOADABLE


def test_opencode_v2_recursive_discovery_skips_non_skill_md(tmp_path: Path) -> None:
    """OpenCode V2 recursive walk finds nested skills but stops at the skill container."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    root = tmp_path / ".opencode" / "skills"
    # Deeply nested skill: category/sub/my_skill/SKILL.md
    nested_skill = root / "category" / "sub" / "my_skill"
    make_skill(nested_skill, "my_skill", "Deeply nested skill")

    # Extra file inside my_skill/assets/doc.md must NOT be discovered as a separate skill
    extra_asset = nested_skill / "assets" / "doc.md"
    extra_asset.parent.mkdir(parents=True, exist_ok=True)
    extra_asset.write_text("---\nname: asset\ndescription: Not a skill\n---\n")

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)

    # Only my_skill is discovered, not asset
    skill_entries = [e for e in idx.entries if "my_skill" in e.entrypoint_path]
    assert len(skill_entries) == 1
    assert not any("asset" in e.entrypoint_path for e in idx.entries)


# ============================================================================
# 4. Pi Tests: Frontmatter / Folder Fallback, User > Project Precedence
# ============================================================================


def test_pi_user_beats_project_precedence(tmp_path: Path) -> None:
    """Pi user roots outrank project roots per upstream skills.ts behavior."""
    paths.set_sandbox(tmp_path)
    (tmp_path / "project" / ".git").mkdir(parents=True)
    user_skill = tmp_path / ".pi" / "agent" / "skills" / "conflict"
    proj_skill = tmp_path / "project" / ".pi" / "skills" / "conflict"
    make_skill(user_skill, "conflict", "User copy")
    make_skill(proj_skill, "conflict", "Project copy")

    cwd = tmp_path / "project"
    reg = load_registry()
    idx = discover(home=tmp_path, cwd=cwd, registry=reg)
    res = resolve_skill("conflict", "pi", cwd=cwd, home=tmp_path, index=idx, registry=reg)

    assert res.headline is HeadlineState.ACTIVE
    by_scope = {c.installation.scope: c for c in res.candidates}
    assert by_scope[Scope.USER].state is HeadlineState.ACTIVE
    assert by_scope[Scope.PROJECT].state is HeadlineState.SHADOWED
    assert by_scope[Scope.USER].rank > by_scope[Scope.PROJECT].rank


def test_pi_fallback_to_directory_name_when_frontmatter_name_absent(tmp_path: Path) -> None:
    """Pi uses folder name when frontmatter name is not specified."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    skill_dir = tmp_path / ".pi" / "agent" / "skills" / "folder_name_tool"
    write_skill(skill_dir, "---\ndescription: Has description but no name.\n---\n# Body\n")

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)
    res = resolve_skill(
        "folder_name_tool", "pi", cwd=tmp_path, home=tmp_path, index=idx, registry=reg
    )

    assert res.found is True
    assert res.headline is HeadlineState.ACTIVE
    assert res.candidates[0].installation.name == "folder_name_tool"


# ============================================================================
# 5. Qoder Tests: User > Project Precedence
# ============================================================================


def test_qoder_user_beats_project_precedence(tmp_path: Path) -> None:
    """Qoder user root ~/.qoder/skills outranks project root .qoder/skills."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    user_skill = tmp_path / ".qoder" / "skills" / "deploy"
    proj_skill = tmp_path / "project" / ".qoder" / "skills" / "deploy"
    (tmp_path / "project" / ".git").mkdir(parents=True)
    make_skill(user_skill, "deploy", "User deploy")
    make_skill(proj_skill, "deploy", "Project deploy")

    cwd = tmp_path / "project"
    reg = load_registry()
    idx = discover(home=tmp_path, cwd=cwd, registry=reg)
    res = resolve_skill("deploy", "qoder", cwd=cwd, home=tmp_path, index=idx, registry=reg)

    assert res.headline is HeadlineState.ACTIVE
    by_scope = {c.installation.scope: c for c in res.candidates}
    assert by_scope[Scope.USER].state is HeadlineState.ACTIVE
    assert by_scope[Scope.PROJECT].state is HeadlineState.SHADOWED


# ============================================================================
# 6. Antigravity Tests: CLI Global Root vs IDE Legacy
# ============================================================================


def test_antigravity_cli_global_root_rank(tmp_path: Path) -> None:
    """Antigravity CLI global ~/.gemini/antigravity-cli/skills has rank 75 > IDE (70)."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    cli_skill = tmp_path / ".gemini" / "antigravity-cli" / "skills" / "sync"
    ide_skill = tmp_path / ".gemini" / "config" / "skills" / "sync"
    make_skill(cli_skill, "sync", "CLI sync")
    make_skill(ide_skill, "sync", "IDE sync")

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)
    res = resolve_skill("sync", "antigravity", cwd=tmp_path, home=tmp_path, index=idx, registry=reg)

    assert res.headline is HeadlineState.ACTIVE
    winner = res.candidates[0]
    assert winner.state is HeadlineState.ACTIVE
    assert "antigravity-cli" in winner.installation.entrypoint_path
    assert winner.rank == 75


# ============================================================================
# 7. Oh My Pi (OMP) Tests: Managed Root, Frontmatter Enabled, Loadability
# ============================================================================


def test_omp_managed_skills_root_discovery(tmp_path: Path) -> None:
    """OMP discovers managed skills under ~/.omp/agent/managed-skills at rank 45."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    managed_skill = tmp_path / ".omp" / "agent" / "managed-skills" / "managed_tool"
    make_skill(managed_skill, "managed_tool", "Managed skill")

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)
    res = resolve_skill("managed_tool", "omp", cwd=tmp_path, home=tmp_path, index=idx, registry=reg)

    assert res.found is True
    assert res.headline is HeadlineState.ACTIVE
    assert res.candidates[0].rank == 45
    assert res.candidates[0].rule_id == "omp_documented_managed_last"


def test_omp_frontmatter_enabled_false_disables_skill(tmp_path: Path) -> None:
    """OMP frontmatter enabled: false disables the skill."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    skill_dir = tmp_path / ".omp" / "skills" / "disabled_omp"
    write_skill(
        skill_dir, "---\nname: disabled_omp\ndescription: Disabled\nenabled: false\n---\n# Body\n"
    )

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)
    res = resolve_skill("disabled_omp", "omp", cwd=tmp_path, home=tmp_path, index=idx, registry=reg)

    assert res.headline is HeadlineState.DISABLED
    assert res.candidates[0].invocation is InvocationPolicy.NONE
    assert res.candidates[0].permission is PermissionEffect.DENY
    assert res.candidates[0].rule_id == "omp_frontmatter_disabled"


def test_omp_provider_loadability_rules(tmp_path: Path) -> None:
    """Native OMP roots require description; foreign provider roots allow optional description."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    # Native OMP project root without description -> INVALID
    native_skill = tmp_path / ".omp" / "skills" / "nodesc_native"
    write_skill(native_skill, "---\nname: nodesc_native\n---\n# Body\n")

    # Foreign shared root without description -> LOADABLE
    foreign_skill = tmp_path / ".agents" / "skills" / "nodesc_foreign"
    write_skill(foreign_skill, "---\nname: nodesc_foreign\n---\n# Body\n")

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)

    res_nat = resolve_skill(
        "nodesc_native", "omp", cwd=tmp_path, home=tmp_path, index=idx, registry=reg
    )
    assert res_nat.headline is HeadlineState.INVALID

    res_for = resolve_skill(
        "nodesc_foreign", "omp", cwd=tmp_path, home=tmp_path, index=idx, registry=reg
    )
    assert res_for.headline is HeadlineState.ACTIVE


# ============================================================================
# 8. Snapshot & CLI Parity: Capture-Time Resolution, Zero Disk Reads
# ============================================================================


def test_snapshot_capture_time_resolution_zero_disk_reads(tmp_path: Path) -> None:
    """Session snapshot captures config overrides and evaluates why/diff with zero disk reads."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    skill_dir = tmp_path / ".claude" / "skills" / "review"
    make_skill(skill_dir, "review", "Code reviewer")

    # Claude settings disabling the skill
    settings_file = tmp_path / ".claude" / "settings.json"
    settings_file.write_text(json.dumps({"skillOverrides": {"review": False}}))

    reg = load_registry()
    snapshot = capture_session(generation=1, home=tmp_path, cwd=tmp_path, registry=reg)

    entry = next(e for e in snapshot.index.entries if "review" in e.entrypoint_path)
    ckey = canonical_key(entry)

    # Now delete the settings file and the skill directory from disk!
    settings_file.unlink()
    (skill_dir / "SKILL.md").unlink()
    skill_dir.rmdir()

    # snapshot_why must evaluate cleanly without reading disk, using captured overrides
    snap_why = snapshot_why(snapshot, ckey, "claude")
    assert snap_why.found is True
    assert snap_why.headline is HeadlineState.DISABLED
    assert snap_why.candidates[0].state is HeadlineState.DISABLED

    # snapshot_diff must also work from snapshot without disk reads
    snap_diff = snapshot_diff(snapshot, ckey)
    assert snap_diff.found is True


def test_resolve_candidate_controls_unit_coverage() -> None:
    """Direct unit tests for resolve_candidate_controls covering edge cases."""
    from skill_lens.core.discovery import DiscoveredEntry, RootHit
    from skill_lens.models.enums import ParseStatus
    from skill_lens.models.parsing import ParseResult

    agent = load_agent("claude")
    entry = DiscoveredEntry(
        entrypoint_path="/home/test/.claude/skills/demo",
        name="demo",
        is_file=False,
        is_symlink=False,
        canonical=None,
        parse=ParseResult(
            status=ParseStatus.VALID,
            directory_name="demo",
            body="body",
            frontmatter_name="demo",
            description="desc",
            source_path="/home/test/.claude/skills/demo/SKILL.md",
            errors=(),
            frontmatter={"disable-model-invocation": True},
        ),
        content_hash="sha256:123",
        hits=(),
    )
    hit = RootHit(
        agent_id="claude",
        root_id="claude_personal",
        rank=90,
        rule_id="claude_personal",
        evidence="documented",
        scope=Scope.USER,
        nested=False,
        file_rule_id=None,
        nested_rule_id=None,
        specificity=2,
        entrypoint_path="/home/test/.claude/skills/demo",
        is_file=False,
    )

    # Manual invocation flag in frontmatter
    ctrls = resolve_candidate_controls(agent, entry, hit, {"demo"})
    assert ctrls.invocation is InvocationPolicy.USER_ONLY
    assert ctrls.is_disabled is False


def test_decode_claude_settings_edge_cases() -> None:
    assert decode_claude_settings(None) == {}
    assert decode_claude_settings(b"") == {}
    assert decode_claude_settings(b"not json") == {}
    assert decode_claude_settings(b"[1, 2, 3]") == {}
    assert decode_claude_settings(b'{"otherKey": 123}') == {}
    assert decode_claude_settings(b'{"skillOverrides": "not a dict"}') == {}
    data = json.dumps({"skillOverrides": {"": True, "valid": "on", "invalid_val": "maybe"}}).encode(
        "utf-8"
    )
    assert decode_claude_settings(data) == {"valid": "on"}


def test_decode_codex_config_edge_cases() -> None:
    assert decode_codex_config(None) == {}
    assert decode_codex_config(b"") == {}
    assert decode_codex_config(b"invalid toml [") == {}
    assert decode_codex_config(b'key = "value"') == {}
    assert decode_codex_config(b'skills = "not a dict"') == {}
    assert decode_codex_config(b'[skills]\nconfig = "not a list"') == {}
    toml_bytes = b"""
[skills]
[[skills.config]]
path = "   "
enabled = true

[[skills.config]]
path = "/valid/path"
enabled = "not a bool"

[[skills.config]]
path = "/path/disabled"
enabled = false
"""
    assert decode_codex_config(toml_bytes) == {"/path/disabled": False}


def test_decode_opencode_permissions_edge_cases() -> None:
    assert decode_opencode_permissions(None) == []
    assert decode_opencode_permissions(b"") == []
    assert decode_opencode_permissions(b"invalid json") == []
    assert decode_opencode_permissions(b"[]") == []

    jsonc_data = b"""
    // This is a comment
    {
        /* multi-line
           comment */
        "permissions": [
            {"action": "skill", "resource": "format1_a", "effect": "ALLOW"},
            {"action": "skill", "resource": "format1_b", "effect": "deny"},
            {"action": "unrelated", "resource": "ignore_me"},
            {"action": "skill", "resource": "invalid_effect", "effect": "unknown"}
        ]
    }
    """
    rules = decode_opencode_permissions(jsonc_data)
    rule_map = {r.resource: r.effect for r in rules}
    assert rule_map.get("format1_a") == "allow"
    assert rule_map.get("format1_b") == "deny"
    assert "ignore_me" not in rule_map
    assert "invalid_effect" not in rule_map

    v1_data = b'{"permission": {"skill": "DENY"}}'
    v1_rules, v1_unsupp, _ = decode_opencode_permissions_with_status(v1_data)
    assert len(v1_rules) == 0
    assert len(v1_unsupp) > 0


def test_loadability_agent_specific_rules() -> None:
    from skill_lens.core.discovery import DiscoveredEntry, RootHit
    from skill_lens.models.enums import ParseStatus
    from skill_lens.models.parsing import ParseResult

    claude_agent = load_agent("claude")
    opencode_agent = load_agent("opencode")
    omp_agent = load_agent("omp")
    codex_agent = load_agent("codex")

    entry_nodesc = DiscoveredEntry(
        entrypoint_path="/test/skill",
        name="nodesc",
        is_file=False,
        is_symlink=False,
        canonical=None,
        parse=ParseResult(
            status=ParseStatus.MISSING_DESCRIPTION,
            directory_name="nodesc",
            body="body",
            frontmatter_name="nodesc",
            description="",
            source_path="/test/skill/SKILL.md",
            errors=("missing_description",),
        ),
        content_hash="sha256:1",
        hits=(),
    )
    st, _ = is_loadable_for_agent(claude_agent, entry_nodesc)
    assert st is LoadabilityStatus.LOADABLE
    st, _ = is_loadable_for_agent(opencode_agent, entry_nodesc)
    assert st is LoadabilityStatus.LOADABLE

    hit_omp_native = RootHit(
        agent_id="omp",
        root_id="omp_project",
        rank=50,
        rule_id="omp_project",
        evidence="documented",
        scope=Scope.PROJECT,
        nested=False,
        file_rule_id=None,
        nested_rule_id=None,
        specificity=2,
        entrypoint_path="/test/skill",
        is_file=False,
    )
    st, _ = is_loadable_for_agent(omp_agent, entry_nodesc, hit_omp_native)
    assert st is LoadabilityStatus.INVALID

    hit_omp_foreign = RootHit(
        agent_id="omp",
        root_id="agent_project",
        rank=50,
        rule_id="agent_project",
        evidence="documented",
        scope=Scope.PROJECT,
        nested=False,
        file_rule_id=None,
        nested_rule_id=None,
        specificity=2,
        entrypoint_path="/test/skill",
        is_file=False,
    )
    st, _ = is_loadable_for_agent(omp_agent, entry_nodesc, hit_omp_foreign)
    assert st is LoadabilityStatus.LOADABLE

    st, _ = is_loadable_for_agent(codex_agent, entry_nodesc)
    assert st is LoadabilityStatus.INVALID

    entry_nofm = DiscoveredEntry(
        entrypoint_path="/test/skill2",
        name="nofm",
        is_file=False,
        is_symlink=False,
        canonical=None,
        parse=ParseResult(
            status=ParseStatus.MALFORMED_YAML,
            directory_name="nofm",
            body="body",
            frontmatter_name=None,
            description=None,
            source_path="/test/skill2/SKILL.md",
            errors=("missing_frontmatter",),
        ),
        content_hash="sha256:2",
        hits=(),
    )
    st, _ = is_loadable_for_agent(opencode_agent, entry_nofm)
    assert st is LoadabilityStatus.LOADABLE
    st, _ = is_loadable_for_agent(claude_agent, entry_nofm)
    assert st is LoadabilityStatus.INVALID

    entry_unreadable = DiscoveredEntry(
        entrypoint_path="/test/skill3",
        name="unreadable",
        is_file=False,
        is_symlink=False,
        canonical=None,
        parse=None,
        content_hash="sha256:3",
        hits=(),
    )
    st, _ = is_loadable_for_agent(claude_agent, entry_unreadable)
    assert st is LoadabilityStatus.INVALID

    entry_valid = DiscoveredEntry(
        entrypoint_path="/test/skill4",
        name="valid",
        is_file=False,
        is_symlink=False,
        canonical=None,
        parse=ParseResult(
            status=ParseStatus.VALID,
            directory_name="valid",
            body="body",
            frontmatter_name="valid",
            description="A valid skill",
            source_path="/test/skill4/SKILL.md",
            errors=(),
        ),
        content_hash="sha256:4",
        hits=(),
    )
    hit_inferred = RootHit(
        agent_id="claude",
        root_id="claude_inferred",
        rank=10,
        rule_id="claude_inferred",
        evidence="inferred",
        scope=Scope.PROJECT,
        nested=False,
        file_rule_id=None,
        nested_rule_id=None,
        specificity=1,
        entrypoint_path="/test/skill4",
        is_file=False,
    )
    st, _ = is_loadable_for_agent(claude_agent, entry_valid, hit_inferred)
    assert st is LoadabilityStatus.UNKNOWN


def test_config_remaining_branches() -> None:
    assert decode_codex_config(b'skills = "invalid"') == {}

    rules, _, _ = decode_opencode_permissions_with_status(
        b'{"permissions": [{"action": "skill", "resource": "tool_a", "effect": "deny"}]}'
    )
    assert rules[0].effect == "deny"

    from skill_lens.core.discovery import DiscoveredEntry, RootHit
    from skill_lens.models.enums import ParseStatus
    from skill_lens.models.parsing import CanonicalResult, CanonicalStatus, ParseResult

    claude_agent = load_agent("claude")
    entry_mal = DiscoveredEntry(
        entrypoint_path="/test/mal",
        name="mal",
        is_file=False,
        is_symlink=False,
        canonical=None,
        parse=ParseResult(
            status=ParseStatus.MALFORMED_YAML,
            directory_name="mal",
            body="body",
            frontmatter_name="mal",
            description="desc",
            source_path="/test/mal/SKILL.md",
            errors=("malformed_yaml: bad syntax",),
        ),
        content_hash="sha256:m",
        hits=(),
    )
    st, _ = is_loadable_for_agent(claude_agent, entry_mal)
    assert st is LoadabilityStatus.INVALID

    entry_canon = DiscoveredEntry(
        entrypoint_path="/test/symlink",
        name="symlink",
        is_file=False,
        is_symlink=True,
        canonical=CanonicalResult(
            status=CanonicalStatus.OK,
            entrypoint_path="/test/symlink",
            resolved_path="/real/path/symlink",
            is_symlink=True,
        ),
        parse=ParseResult(
            status=ParseStatus.VALID,
            directory_name="symlink",
            body="body",
            frontmatter_name="symlink",
            description="desc",
            source_path="/real/path/symlink/SKILL.md",
            errors=(),
        ),
        content_hash="sha256:c",
        hits=(),
    )
    hit_c = RootHit(
        agent_id="claude",
        root_id="claude_personal",
        rank=90,
        rule_id="claude_personal",
        evidence="documented",
        scope=Scope.USER,
        nested=False,
        file_rule_id=None,
        nested_rule_id=None,
        specificity=2,
        entrypoint_path="/test/symlink",
        is_file=False,
    )
    ctrls_canon = resolve_candidate_controls(
        claude_agent,
        entry_canon,
        hit_c,
        {"symlink"},
        captured_disabled_overrides=frozenset(["/real/path/symlink"]),
    )
    assert ctrls_canon.is_disabled is True

    codex_agent = load_agent("codex")
    ctrls_codex = resolve_candidate_controls(
        codex_agent,
        entry_canon,
        hit_c,
        {"symlink"},
        codex_disabled_paths={"path/symlink": False},
    )
    # Suffix matching is forbidden; exact normalized path required
    assert ctrls_codex.is_disabled is False

    ctrls_codex_exact = resolve_candidate_controls(
        codex_agent,
        entry_canon,
        hit_c,
        {"symlink"},
        codex_disabled_paths={"/real/path/symlink": False},
    )
    assert ctrls_codex_exact.is_disabled is True


# ============================================================================
# 11. Coordinator R1 Regression Tests (All 10 Failing Cases & Edge Controls)
# ============================================================================


def test_coordinator_r1_repro_1_codex_frozen_is_dir_pure_lexical(tmp_path: Path) -> None:
    """1. Frozen Codex controls evaluate purely lexically with zero filesystem probes."""
    from unittest.mock import patch

    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    skill_p = tmp_path / ".codex" / "skills" / "deploy"
    make_skill(skill_p, "deploy", "desc")
    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    skill_md_str = str(skill_p / "SKILL.md")
    cfg.write_text(f"""[[skills.config]]
path = "{skill_md_str}"
enabled = false
""")

    reg = load_registry()
    snap = capture_session(generation=1, home=tmp_path, cwd=tmp_path, registry=reg)
    e = next(entry for entry in snap.index.entries if entry.entrypoint_path == str(skill_p))

    # All filesystem probes blocked
    with (
        patch.object(Path, "is_dir", side_effect=AssertionError("report-time is_dir probe")),
        patch.object(Path, "resolve", side_effect=AssertionError("report-time resolve probe")),
    ):
        r = snapshot_why(snap, canonical_key(e), "codex")
        assert r.headline is HeadlineState.DISABLED


def test_coordinator_r1_repro_2_intermediate_live_frozen(tmp_path: Path) -> None:
    """2. Single collector captures intermediate ancestor configs for live/frozen agreement."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    cwd = tmp_path / "middle" / "deep"
    cwd.mkdir(parents=True)
    p = cwd / ".opencode" / "skills" / "deploy"
    make_skill(p, "deploy", "desc")
    (tmp_path / "middle" / "opencode.json").write_text(
        '{"permissions":[{"action":"skill","resource":"deploy","effect":"deny"}]}'
    )

    reg = load_registry()
    live = resolve_skill("deploy", "opencode", cwd, tmp_path)
    snap = capture_session(generation=1, home=tmp_path, cwd=cwd, registry=reg)
    e = next(entry for entry in snap.index.entries if entry.entrypoint_path == str(p))
    frozen = snapshot_why(snap, canonical_key(e), "opencode")

    assert live.headline is HeadlineState.DISABLED
    assert frozen.headline is HeadlineState.DISABLED
    assert str(tmp_path / "middle" / "opencode.json") in snap.config_inputs


def test_coordinator_r1_repro_3_opencode_layer_order_hidden_after_direct(tmp_path: Path) -> None:
    """3. All direct configs farthest->closest, THEN all .opencode configs farthest->closest."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    cwd = tmp_path / "child"
    cwd.mkdir()
    make_skill(cwd / ".opencode" / "skills" / "deploy", "deploy", "desc")
    (tmp_path / ".opencode").mkdir()
    (tmp_path / ".opencode" / "opencode.json").write_text(
        '{"permissions":[{"action":"skill","resource":"deploy","effect":"deny"}]}'
    )
    (cwd / "opencode.json").write_text(
        '{"permissions":[{"action":"skill","resource":"deploy","effect":"allow"}]}'
    )

    r = resolve_skill("deploy", "opencode", cwd, tmp_path)
    assert r.headline is HeadlineState.DISABLED


def test_coordinator_r1_repro_4_claude_settings_declared_command_identity(tmp_path: Path) -> None:
    """4. Claude settings overrides match declared command identity, not unrelated folder name."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    make_skill(tmp_path / ".claude" / "skills" / "folder", "declared", "desc")
    (tmp_path / ".claude" / "settings.json").write_text('{"skillOverrides":{"folder":"off"}}')

    r = resolve_skill("declared", "claude", tmp_path, tmp_path)
    assert r.headline is HeadlineState.ACTIVE
    assert r.candidates[0].invocation is InvocationPolicy.ALL

    # When the declared name is overridden, it disables
    (tmp_path / ".claude" / "settings.json").write_text('{"skillOverrides":{"declared":"off"}}')
    r_off = resolve_skill("declared", "claude", tmp_path, tmp_path)
    assert r_off.headline is HeadlineState.DISABLED


def test_coordinator_r1_repro_5_opencode_hit_id_permissions(tmp_path: Path) -> None:
    """5. OpenCode permissions evaluate on exact hit path ID, not merged canonical name."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    target = tmp_path / "library" / "skill"
    make_skill(target, "display", "desc")

    c = tmp_path / ".claude" / "skills" / "c-alias"
    c.parent.mkdir(parents=True, exist_ok=True)
    c.symlink_to(target, target_is_directory=True)

    o = tmp_path / ".opencode" / "skills" / "o-alias"
    o.parent.mkdir(parents=True, exist_ok=True)
    o.symlink_to(target, target_is_directory=True)

    (tmp_path / "opencode.json").write_text(
        '{"permissions":[{"action":"skill","resource":"o-alias","effect":"deny"}]}'
    )

    r = resolve_skill("o-alias", "opencode", tmp_path, tmp_path)
    assert r.headline is HeadlineState.DISABLED
    assert r.candidates[0].permission is PermissionEffect.DENY


def test_coordinator_r1_repro_6_opencode_closest_source_ancestor_collision(tmp_path: Path) -> None:
    """6. OpenCode ancestor specificity: child closest source is ACTIVE, parent SHADOWED."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    cwd = tmp_path / "sub"
    cwd.mkdir()
    make_skill(tmp_path / ".opencode" / "skills" / "deploy", "deploy", "parent")
    make_skill(cwd / ".opencode" / "skills" / "deploy", "deploy", "child")

    r = resolve_skill("deploy", "opencode", cwd, tmp_path)
    assert r.headline is HeadlineState.ACTIVE
    child_cand = next(c for c in r.candidates if "sub" in c.installation.entrypoint_path)
    parent_cand = next(c for c in r.candidates if "sub" not in c.installation.entrypoint_path)
    assert child_cand.state is HeadlineState.ACTIVE
    assert parent_cand.state is HeadlineState.SHADOWED


def test_coordinator_r1_repro_7_omp_doctor_foreign_provider_description(tmp_path: Path) -> None:
    """7. Doctor does not falsely say OMP foreign roots reject missing description."""
    from skill_lens.core.doctor import run_doctor

    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    write_skill(
        tmp_path / ".agents" / "skills" / "deploy",
        """---
name: deploy
---
body
""",
    )

    r = run_doctor(tmp_path)
    desc_findings = [f.message for f in r.findings if f.code == "malformed_frontmatter"]
    assert len(desc_findings) == 1
    assert "accepted at runtime by omp" in desc_findings[0]
    assert "omp will skip" not in desc_findings[0]


def test_coordinator_r1_repro_8_unsupported_v1_config_disclosed(tmp_path: Path) -> None:
    """8. Unsupported OpenCode V1 config is disclosed in notes and sets UNKNOWN permission."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    make_skill(tmp_path / ".opencode" / "skills" / "deploy", "deploy", "desc")
    (tmp_path / "opencode.json").write_text('{"permission":{"skill":"deny"}}')

    r = resolve_skill("deploy", "opencode", tmp_path, tmp_path)
    assert r.candidates[0].permission is PermissionEffect.UNKNOWN
    assert any("V1 'permission' key is unsupported" in n for n in r.notes)


def test_coordinator_r1_repro_9_invalid_override_value_status() -> None:
    """9. Non-boolean, non-string Claude override values return malformed status."""
    settings, err = decode_claude_settings_with_status(b'{"skillOverrides":{"deploy":[]}}')
    assert err == "malformed"


def test_coordinator_r1_repro_10_invalid_v2_effect_status() -> None:
    """10. Invalid OpenCode V2 permission effect returns malformed status and unsupported notes."""
    rules, unsup, err = decode_opencode_permissions_with_status(
        b'{"permissions":[{"action":"skill","resource":"deploy","effect":"maybe"}]}'
    )
    assert err == "malformed"
    assert any("Invalid permission effect" in u for u in unsup)
    assert not any("maybe" in u for u in unsup)


def test_opencode_wildcard_special_characters_only() -> None:
    """OpenCode resource wildcards treat ONLY * and ? as special; brackets [] are literal."""
    rules, _, _ = decode_opencode_permissions_with_status(
        b'{"permissions":['
        b'  {"action":"skill","resource":"test[1]","effect":"deny"},'
        b'  {"action":"skill","resource":"wild*","effect":"ask"}'
        b"]}"
    )
    ctrls = ResolvedAgentControls(
        agent_id="opencode",
        opencode_rules=tuple(rules),
    )
    # Literal test[1] matches
    assert ctrls.evaluate_opencode_permission("test[1]") is PermissionEffect.DENY
    # test1 does not match (brackets are literal, not fnmatch character class)
    assert ctrls.evaluate_opencode_permission("test1") is PermissionEffect.ALLOW
    # wild* matches wildcard
    assert ctrls.evaluate_opencode_permission("wildcard") is PermissionEffect.ASK


def test_empty_json_config_treated_as_malformed() -> None:
    """Empty existing JSON configuration files (0 bytes) are malformed, not absent."""
    assert decode_claude_settings_with_status(b"")[1] == "malformed"
    assert decode_opencode_permissions_with_status(b"")[2] == "malformed"
    assert decode_codex_config_with_status(b"")[2] == "malformed"


def test_session_snapshot_typed_immutable_resolved_controls(tmp_path: Path) -> None:
    """SessionSnapshot has typed immutable MappingProxyType resolved_controls without hasattr."""
    from types import MappingProxyType

    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()
    reg = load_registry()
    snap = capture_session(generation=1, home=tmp_path, cwd=tmp_path, registry=reg)

    assert isinstance(snap.resolved_controls, MappingProxyType)
    assert "claude" in snap.resolved_controls
    assert isinstance(snap.resolved_controls["claude"], ResolvedAgentControls)


# ============================================================================
# 12. Council Round 1 Blocker Regressions (A through J)
# ============================================================================


def test_codex_symlink_parent_and_extra_aliases_parity(tmp_path: Path) -> None:
    """A. Codex symlink parent and extra alias live vs frozen parity; deleting original."""
    from unittest.mock import patch

    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    skill_dir = tmp_path / ".agents" / "skills" / "my_skill"
    make_skill(skill_dir, "my_skill", "My skill description")

    parent_symlink = tmp_path / "sym_parent"
    parent_symlink.symlink_to(tmp_path / ".agents" / "skills", target_is_directory=True)

    symlink_skill_md = parent_symlink / "my_skill" / "SKILL.md"
    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(f"""[[skills.config]]
path = \"{symlink_skill_md}\"
enabled = false
""")

    reg = load_registry()
    live_res = resolve_skill("my_skill", "codex", tmp_path, tmp_path, registry=reg)
    assert live_res.headline is HeadlineState.DISABLED

    snap = capture_session(generation=1, home=tmp_path, cwd=tmp_path, registry=reg)
    entry = next(e for e in snap.index.entries if "my_skill" in e.entrypoint_path)
    ckey = canonical_key(entry)

    cfg.unlink()
    parent_symlink.unlink()

    with (
        patch.object(Path, "is_dir", side_effect=AssertionError("report-time is_dir probe")),
        patch.object(Path, "resolve", side_effect=AssertionError("report-time resolve probe")),
    ):
        frozen_res = snapshot_why(snap, ckey, "codex")
        assert frozen_res.headline is HeadlineState.DISABLED


def test_explicit_disabled_overrides_alias_intersection(tmp_path: Path) -> None:
    """B. disabled_overrides= preserves alias intersections across all candidate identities."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    skill_dir = tmp_path / ".claude" / "skills" / "folder_name"
    make_skill(skill_dir, "declared_name", "Description")

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)

    res_dec = resolve_skill(
        "declared_name",
        "claude",
        tmp_path,
        tmp_path,
        index=idx,
        registry=reg,
        disabled_overrides=frozenset(["declared_name"]),
    )
    assert res_dec.headline is HeadlineState.DISABLED

    res_fol = resolve_skill(
        "declared_name",
        "claude",
        tmp_path,
        tmp_path,
        index=idx,
        registry=reg,
        disabled_overrides=frozenset(["folder_name"]),
    )
    assert res_fol.headline is HeadlineState.DISABLED


def test_doctor_portability_and_loadability_consistency(tmp_path: Path) -> None:
    """C. Doctor reports portability finding without falsely saying OpenCode skips plain skills."""
    from skill_lens.core.doctor import run_doctor

    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    plain_dir = tmp_path / ".opencode" / "skills" / "plain"
    plain_dir.mkdir(parents=True)
    (plain_dir / "SKILL.md").write_text("# Plain Skill\nNo YAML frontmatter at all.\n")

    doc_res = run_doctor(tmp_path)
    plain_findings = [f.message for f in doc_res.findings if "plain" in f.message]
    assert len(plain_findings) == 1
    assert "portable agents will skip 'plain'" in plain_findings[0]
    assert "accepted at runtime by opencode" in plain_findings[0]
    assert "opencode will skip" not in plain_findings[0]


def test_unknown_retained_roots_vs_dsh_native(tmp_path: Path) -> None:
    """D. Retained unverified roots report unknown loadability, vs DSH native roots."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    qoder_skill = tmp_path / ".agents" / "skills" / "qskill"
    make_skill(qoder_skill, "qskill", "Qoder skill")

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)

    q_res = resolve_skill("qskill", "qoder", tmp_path, tmp_path, index=idx, registry=reg)
    assert q_res.headline is HeadlineState.ACTIVE
    assert q_res.candidates[0].loadability is LoadabilityStatus.UNKNOWN
    assert any("vendor loadability is unverified" in n for n in q_res.notes)

    dsh_res = resolve_skill("qskill", "dsh", tmp_path, tmp_path, index=idx, registry=reg)
    assert dsh_res.headline is HeadlineState.ACTIVE
    assert dsh_res.candidates[0].loadability is LoadabilityStatus.LOADABLE
    assert not any("vendor loadability is unverified" in n for n in dsh_res.notes)


def test_opencode_invocation_and_permission_deny(tmp_path: Path) -> None:
    """E. OpenCode invocation policy and permission deny distinct reason."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    s1 = tmp_path / ".opencode" / "skills" / "no_desc_auto"
    write_skill(s1, "---\nname: no_desc_auto\nautoinvoke: true\n---\n# Body\n")

    s2 = tmp_path / ".opencode" / "skills" / "with_desc_auto"
    write_skill(
        s2,
        "---\nname: with_desc_auto\ndescription: Desc\nautoinvoke: true\n---\n# Body\n",
    )

    s3 = tmp_path / ".opencode" / "skills" / "invalid_auto"
    write_skill(
        s3,
        "---\nname: invalid_auto\ndescription: Desc\nautoinvoke: invalid_str\n---\n# Body\n",
    )

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)

    r1 = resolve_skill("no_desc_auto", "opencode", tmp_path, tmp_path, index=idx, registry=reg)
    assert r1.candidates[0].invocation is InvocationPolicy.USER_ONLY

    r2 = resolve_skill("with_desc_auto", "opencode", tmp_path, tmp_path, index=idx, registry=reg)
    assert r2.candidates[0].invocation is InvocationPolicy.ALL

    r3 = resolve_skill("invalid_auto", "opencode", tmp_path, tmp_path, index=idx, registry=reg)
    assert r3.candidates[0].invocation is InvocationPolicy.UNKNOWN

    perm_json = '{"permissions":[{"action":"skill","resource":"with_desc_auto","effect":"deny"}]}'
    (tmp_path / "opencode.json").write_text(perm_json)
    r_deny = resolve_skill(
        "with_desc_auto", "opencode", tmp_path, tmp_path, index=idx, registry=reg
    )
    assert r_deny.headline is HeadlineState.DISABLED
    assert r_deny.candidates[0].permission is PermissionEffect.DENY
    assert "Denied by OpenCode skill permission" in r_deny.candidates[0].reason


def test_opencode_config_above_git_root(tmp_path: Path) -> None:
    """F. OpenCode config walk continues to filesystem/sandbox root above .git boundary."""
    paths.set_sandbox(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    cwd = repo / "nested"
    cwd.mkdir()

    skill = cwd / ".opencode" / "skills" / "target_skill"
    make_skill(skill, "target_skill", "Desc")

    perm_json = '{"permissions":[{"action":"skill","resource":"target_skill","effect":"deny"}]}'
    (tmp_path / "opencode.json").write_text(perm_json)

    r = resolve_skill("target_skill", "opencode", cwd, tmp_path)
    assert r.headline is HeadlineState.DISABLED
    assert r.candidates[0].permission is PermissionEffect.DENY


def test_bounded_discovery_depth_cap_disclosure(tmp_path: Path) -> None:
    """G. Bounded discovery discloses depth cap truncation in index and notes."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    deep_path = tmp_path / ".opencode" / "skills"
    for i in range(35):
        deep_path = deep_path / f"d{i}"
    deep_path.mkdir(parents=True)
    make_skill(deep_path / "deep_skill", "deep_skill", "Deep skill")

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)

    assert any(u.detail == "depth_limit_truncated" for u in idx.unreadable_roots)

    r = resolve_skill("nonexistent", "opencode", tmp_path, tmp_path, index=idx, registry=reg)
    assert any("truncated by depth limit" in n for n in r.notes)


def test_nontarget_nested_regression_coexistence(tmp_path: Path) -> None:
    """H. Base nested copy coexistence for non-OpenCode profiles."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    s1 = tmp_path / ".claude" / "skills" / "tool_a"
    make_skill(s1, "tool_a", "Tool A")
    s2 = tmp_path / ".claude" / "skills" / "tool_b"
    make_skill(s2, "tool_b", "Tool B")

    reg = load_registry()
    idx = discover(home=tmp_path, cwd=tmp_path, registry=reg)

    ra = resolve_skill("tool_a", "claude", tmp_path, tmp_path, index=idx, registry=reg)
    assert ra.headline is HeadlineState.ACTIVE

    rb = resolve_skill("tool_b", "claude", tmp_path, tmp_path, index=idx, registry=reg)
    assert rb.headline is HeadlineState.ACTIVE


def test_claude_live_frozen_command_identity_parity(tmp_path: Path) -> None:
    """1. Positive/negative live/capture parity for Claude command identity
    and settings overrides."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    # Skill folder named 'folder' with frontmatter name 'declared'
    skill_dir = tmp_path / ".claude" / "skills" / "folder"
    write_skill(
        skill_dir,
        """---
name: declared
description: desc
---
# Instructions
Do work.
""",
    )

    reg = load_registry()

    # Case A: declared is off -> both live and captured return DISABLED
    settings_file = tmp_path / ".claude" / "settings.json"
    settings_file.write_text('{"skillOverrides": {"declared": "off"}}', encoding="utf-8")

    live_idx_a = discover(home=tmp_path, cwd=tmp_path, registry=reg)
    live_res_a = resolve_skill(
        "declared", "claude", tmp_path, tmp_path, index=live_idx_a, registry=reg
    )
    assert live_res_a.headline is HeadlineState.DISABLED
    assert live_res_a.candidates[0].state is HeadlineState.DISABLED

    snap_a = capture_session(generation=1, home=tmp_path, cwd=tmp_path)
    entry_a = next(e for e in snap_a.index.entries if "folder" in e.entrypoint_path)
    key_a = canonical_key(entry_a)
    snap_res_a = snapshot_why(snap_a, key_a, "claude")
    assert snap_res_a.headline is HeadlineState.DISABLED
    assert snap_res_a.candidates[0].state is HeadlineState.DISABLED

    # Report-time filesystem guard: delete directory on disk;
    # frozen snapshot resolution is unchanged
    shutil.rmtree(skill_dir)
    snap_res_a_del = snapshot_why(snap_a, key_a, "claude")
    assert snap_res_a_del.headline is HeadlineState.DISABLED

    # Re-create skill folder for Case B
    write_skill(
        skill_dir,
        """---
name: declared
description: desc
---
# Instructions
Do work.
""",
    )

    # Case B: unrelated folder is off -> both live and captured return ACTIVE
    settings_file.write_text('{"skillOverrides": {"folder": "off"}}', encoding="utf-8")
    live_idx_b = discover(home=tmp_path, cwd=tmp_path, registry=reg)
    live_res_b = resolve_skill(
        "declared", "claude", tmp_path, tmp_path, index=live_idx_b, registry=reg
    )
    assert live_res_b.headline is HeadlineState.ACTIVE
    assert live_res_b.candidates[0].state is HeadlineState.ACTIVE

    snap_b = capture_session(generation=2, home=tmp_path, cwd=tmp_path)
    entry_b = next(e for e in snap_b.index.entries if "folder" in e.entrypoint_path)
    key_b = canonical_key(entry_b)
    snap_res_b = snapshot_why(snap_b, key_b, "claude")
    assert snap_res_b.headline is HeadlineState.ACTIVE
    assert snap_res_b.candidates[0].state is HeadlineState.ACTIVE

    # Case C: explicit caller disabled_overrides API honours alias and path intersections
    exp_alias = resolve_skill(
        "declared",
        "claude",
        tmp_path,
        tmp_path,
        index=live_idx_b,
        registry=reg,
        disabled_overrides=frozenset({"folder"}),
    )
    assert exp_alias.headline is HeadlineState.DISABLED

    exp_path = resolve_skill(
        "declared",
        "claude",
        tmp_path,
        tmp_path,
        index=live_idx_b,
        registry=reg,
        disabled_overrides=frozenset({str(skill_dir)}),
    )
    assert exp_path.headline is HeadlineState.DISABLED

    # Case D: settings precedence Local > Project > User
    user_settings = tmp_path / "user_home" / ".claude" / "settings.json"
    user_settings.parent.mkdir(parents=True, exist_ok=True)
    user_settings.write_text('{"skillOverrides": {"declared": "off"}}', encoding="utf-8")
    project_settings = tmp_path / ".claude" / "settings.json"
    project_settings.write_text('{"skillOverrides": {"declared": "on"}}', encoding="utf-8")

    live_prec_1 = resolve_skill(
        "declared", "claude", tmp_path, tmp_path / "user_home", registry=reg
    )
    assert live_prec_1.headline is HeadlineState.ACTIVE  # Project outranks User

    local_settings = tmp_path / ".claude" / "settings.local.json"
    local_settings.write_text('{"skillOverrides": {"declared": "off"}}', encoding="utf-8")
    live_prec_2 = resolve_skill(
        "declared", "claude", tmp_path, tmp_path / "user_home", registry=reg
    )
    assert live_prec_2.headline is HeadlineState.DISABLED  # Local outranks Project


def test_opencode_bounded_disclosure_and_default_agent_confidence(tmp_path: Path) -> None:
    """2. OpenCode bounded disclosure of omitted system/managed sources
    and default_agent confidence."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    make_skill(tmp_path / ".opencode" / "skills" / "deploy", "deploy", "Deploy skill")
    reg = load_registry()

    # Scenario A: empty config {}
    cfg_path = tmp_path / "opencode.json"
    cfg_path.write_text("{}", encoding="utf-8")

    live_res = resolve_skill("deploy", "opencode", tmp_path, tmp_path, registry=reg)
    assert live_res.headline is HeadlineState.ACTIVE
    assert live_res.candidates[0].permission is PermissionEffect.ALLOW
    assert any("OpenCode evaluation assumes base 'build' agent" in n for n in live_res.notes)

    # No-candidate report includes the disclosure note as well
    no_cand = resolve_skill("nonexistent", "opencode", tmp_path, tmp_path, registry=reg)
    assert any("No copy of this skill name was found" in n for n in no_cand.notes)
    assert any("OpenCode evaluation assumes base 'build' agent" in n for n in no_cand.notes)

    # Captured snapshot has identical disclosure
    snap = capture_session(generation=1, home=tmp_path, cwd=tmp_path)
    entry = next(e for e in snap.index.entries if "deploy" in e.entrypoint_path)
    snap_res = snapshot_why(snap, canonical_key(entry), "opencode")
    assert snap_res.headline is HeadlineState.ACTIVE
    assert snap_res.candidates[0].permission is PermissionEffect.ALLOW
    assert any("OpenCode evaluation assumes base 'build' agent" in n for n in snap_res.notes)

    # Scenario B: non-default agent (default_agent: "plan") -> permission UNKNOWN
    cfg_path.write_text('{"default_agent": "plan"}', encoding="utf-8")
    live_plan = resolve_skill("deploy", "opencode", tmp_path, tmp_path, registry=reg)
    assert live_plan.headline is HeadlineState.ACTIVE
    assert live_plan.candidates[0].permission is PermissionEffect.UNKNOWN
    assert any(
        "Non-default OpenCode agent selection ('default_agent') is unmodelled" in n
        for n in live_plan.notes
    )

    snap_plan = capture_session(generation=2, home=tmp_path, cwd=tmp_path)
    snap_plan_res = snapshot_why(snap_plan, canonical_key(entry), "opencode")
    assert snap_plan_res.candidates[0].permission is PermissionEffect.UNKNOWN

    # Scenario C: default_agent: "build" -> matches base model assumption, permission is ALLOW
    cfg_path.write_text('{"default_agent": "build"}', encoding="utf-8")
    live_build = resolve_skill("deploy", "opencode", tmp_path, tmp_path, registry=reg)
    assert live_build.candidates[0].permission is PermissionEffect.ALLOW

    # Scenario D: modeled deny rule with default_agent: "plan" -> deny takes precedence as DISABLED
    cfg_path.write_text(
        '{"default_agent": "plan", "permissions": ['
        '{"action": "skill", "resource": "deploy", "effect": "deny"}]}',
        encoding="utf-8",
    )
    live_deny = resolve_skill("deploy", "opencode", tmp_path, tmp_path, registry=reg)
    assert live_deny.headline is HeadlineState.DISABLED
    assert live_deny.candidates[0].state is HeadlineState.DISABLED
    assert "Denied by OpenCode skill permission" in live_deny.candidates[0].reason


def test_privacy_synthetic_secrets_not_leaked(tmp_path: Path) -> None:
    """3. Verify synthetic secrets are never interpolated into error/diagnostic notes or reports."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    make_skill(tmp_path / ".opencode" / "skills" / "deploy", "deploy", "Deploy skill")
    reg = load_registry()

    secret_effect = "SYNTHETIC_SECRET_EFFECT_42"
    secret_agent = "SYNTHETIC_SECRET_AGENT_99"
    secret_pattern = "SYNTHETIC_SECRET_PATTERN_77"
    secret_codex = "SYNTHETIC_SECRET_CODEX_PATH_88"

    # OpenCode config containing secret values in invalid effect, agent-specific key, and pattern
    cfg_path = tmp_path / "opencode.json"
    cfg_path.write_text(
        json.dumps(
            {
                "agents": {
                    secret_agent: {
                        "permissions": [{"action": "skill", "resource": "*", "effect": "deny"}]
                    }
                },
                "permissions": [
                    {"action": "skill", "resource": "deploy", "effect": secret_effect},
                    {"action": "skill", "pattern": secret_pattern, "effect": "allow"},
                ],
            }
        ),
        encoding="utf-8",
    )

    # Codex config containing relative path with secret token
    codex_cfg = tmp_path / ".codex" / "config.toml"
    codex_cfg.parent.mkdir(parents=True, exist_ok=True)
    codex_cfg.write_text(
        f'[[skills.config]]\npath = "{secret_codex}"\nenabled = false\n', encoding="utf-8"
    )

    # 1. Test OpenCode live and captured resolution
    res_opencode = resolve_skill("deploy", "opencode", tmp_path, tmp_path, registry=reg)
    assert res_opencode.candidates[0].permission is PermissionEffect.UNKNOWN
    opencode_json_str = json.dumps(res_opencode.to_dict())
    assert secret_effect not in opencode_json_str
    assert secret_agent not in opencode_json_str
    assert secret_pattern not in opencode_json_str

    snap = capture_session(generation=1, home=tmp_path, cwd=tmp_path)
    entry = next(e for e in snap.index.entries if "deploy" in e.entrypoint_path)
    snap_opencode = snapshot_why(snap, canonical_key(entry), "opencode")
    snap_json_str = json.dumps(snap_opencode.to_dict())
    assert secret_effect not in snap_json_str
    assert secret_agent not in snap_json_str
    assert secret_pattern not in snap_json_str

    # 2. Test Codex relative-path diagnostic
    res_codex = resolve_skill("deploy", "codex", tmp_path, tmp_path, registry=reg)
    codex_json_str = json.dumps(res_codex.to_dict())
    assert secret_codex not in codex_json_str
    assert any("Relative path in Codex config is unsupported" in n for n in res_codex.notes)


def test_doctor_mixed_root_loadability_and_unknown_discipline(tmp_path: Path) -> None:
    """4. Doctor preserves LOADABLE, INVALID, and UNKNOWN categories
    separately without false skips."""
    from skill_lens.core.doctor import run_doctor

    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    # Skill with frontmatter but missing description placed under shared .agents/skills
    shared_skill = tmp_path / ".agents" / "skills" / "deploy"
    write_skill(
        shared_skill,
        """---
name: deploy
---
# Instructions
Missing description body.
""",
    )

    doc_res = run_doctor(tmp_path)
    desc_findings = [f.message for f in doc_res.findings if "deploy" in f.message]
    assert len(desc_findings) == 1
    msg = desc_findings[0]

    # Codex, DSH, Pi require description on verified roots -> will skip
    assert "codex, dsh will skip 'deploy'" in msg
    assert "pi will skip" not in msg
    # OMP and OpenCode tolerate missing description -> accepted at runtime
    assert "accepted at runtime by omp, opencode" in msg

    # Unverified retained roots (Antigravity, Grok, Qoder, Windsurf)
    # MUST NOT be falsely reported as skipping
    assert "antigravity will skip" not in msg
    assert "grok will skip" not in msg
    assert "qoder will skip" not in msg
    assert "windsurf will skip" not in msg
    assert "antigravity, codex" not in msg

    # Missing frontmatter test
    plain_skill = tmp_path / ".agents" / "skills" / "plain"
    plain_skill.mkdir(parents=True)
    (plain_skill / "SKILL.md").write_text(
        "# Plain Skill\nNo frontmatter at all.\n", encoding="utf-8"
    )

    doc_res_2 = run_doctor(tmp_path)
    plain_findings = [f.message for f in doc_res_2.findings if "plain" in f.message]
    assert len(plain_findings) == 1
    plain_msg = plain_findings[0]

    assert "codex, dsh, omp will skip 'plain'" in plain_msg
    assert "pi will skip" not in plain_msg
    assert "accepted at runtime by opencode" in plain_msg
    assert "antigravity will skip" not in plain_msg
    assert "grok will skip" not in plain_msg
    assert "qoder will skip" not in plain_msg
    assert "windsurf will skip" not in plain_msg

    # Frozen doctor parity assertion
    snap = capture_session(generation=1, home=tmp_path, cwd=tmp_path)
    snap_findings = [
        f.message for f in snap.doctor.findings if "deploy" in f.message or "plain" in f.message
    ]
    assert len(snap_findings) == 2
    assert desc_findings[0] in snap_findings
    assert plain_findings[0] in snap_findings


def test_cyclic_symlink_config_error_containment(tmp_path: Path) -> None:
    """Boundary A: Cyclic symlink in [[skills.config]] path must not raise RuntimeError,
    must preserve lexical matching, must diagnose uncertainty, and must not leak secrets."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    # Synthetic symlink cycle: cycle-a -> cycle-b -> cycle-a
    cycle_a = tmp_path / "cycle-a"
    cycle_b = tmp_path / "cycle-b"
    cycle_a.symlink_to(cycle_b)
    cycle_b.symlink_to(cycle_a)

    cyclic_skill_md = str(cycle_a / "SKILL.md")
    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        f"""[[skills.config]]
path = "{cyclic_skill_md}"
enabled = false
""",
        encoding="utf-8",
    )

    # Normal skill in project
    normal_skill = tmp_path / ".agents" / "skills" / "deploy"
    make_skill(normal_skill, "deploy", "Normal deploy skill")

    reg = load_registry()

    # 1. Live resolve_agent_controls must not raise RuntimeError on Python 3.11/3.12
    codex_agent = reg["codex"]
    ctrls = resolve_agent_controls(codex_agent, tmp_path, tmp_path)
    assert cyclic_skill_md in ctrls.disabled_names or str(cycle_a) in ctrls.disabled_names
    assert "Unresolvable path in Codex config is unsupported" in ctrls.unsupported_controls
    assert any("Path in Codex config could not be resolved" in n for n in ctrls.notes)

    # 2. Live resolve_skill for normal skill must succeed without crash
    res = resolve_skill("deploy", "codex", tmp_path, tmp_path, registry=reg)
    assert res.found is True
    assert res.headline is HeadlineState.ACTIVE
    # Uncertainty is propagated: permission confidence is UNKNOWN due to unsupported config path
    assert res.candidates[0].permission is PermissionEffect.UNKNOWN
    assert any("Path in Codex config could not be resolved" in n for n in res.notes)
    # No arbitrary config secrets leaked in notes
    assert cyclic_skill_md not in "\n".join(res.notes)

    # 3. capture_session and snapshot_why must succeed without crash
    snap = capture_session(generation=1, home=tmp_path, cwd=tmp_path, registry=reg)
    entry = next(e for e in snap.index.entries if "deploy" in e.entrypoint_path)
    ckey = canonical_key(entry)

    frozen_res = snapshot_why(snap, ckey, "codex")
    assert frozen_res.found is True
    assert frozen_res.headline is HeadlineState.ACTIVE
    assert frozen_res.candidates[0].permission is PermissionEffect.UNKNOWN
    assert any("Path in Codex config could not be resolved" in n for n in frozen_res.notes)


def test_truncated_snapshot_navigation_without_filesystem_probes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Boundary B: Truncated snapshot navigation executes under full prohibited-boundary
    filesystem guards with zero filesystem probes, preserves visible truncation warnings,
    and agrees between live and frozen reports even after source deletion."""
    import builtins
    import io
    import os

    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    # 1. OpenCode setup: normal deploy skill + >32 deep nested skill causing walk depth truncation
    opencode_root = tmp_path / ".opencode" / "skills"
    make_skill(opencode_root / "deploy", "deploy", "OpenCode deploy skill")

    deep_opencode = opencode_root
    for i in range(35):
        deep_opencode = deep_opencode / f"deep_{i}"
    deep_opencode.mkdir(parents=True)
    make_skill(deep_opencode / "hidden_tool", "hidden_tool", "Deep tool")

    # 2. Pi setup: normal deploy skill + >16 deep nested skill causing Pi walk depth truncation
    pi_root = tmp_path / ".pi" / "skills"
    make_skill(pi_root / "pideploy", "pideploy", "Pi deploy skill")

    deep_pi = pi_root
    for i in range(18):
        deep_pi = deep_pi / f"pideep_{i}"
    deep_pi.mkdir(parents=True)
    make_skill(deep_pi / "pi_hidden", "pi_hidden", "Pi deep tool")

    reg = load_registry()

    # Verify live resolutions contain depth limit truncation notes
    live_oc = resolve_skill("deploy", "opencode", tmp_path, tmp_path, registry=reg)
    assert any("truncated by depth limit; inventory may be incomplete" in n for n in live_oc.notes)
    oc_trunc_note = next(n for n in live_oc.notes if "truncated by depth limit" in n)

    live_pi = resolve_skill("pideploy", "pi", tmp_path, tmp_path, registry=reg)
    assert any("truncated by depth limit; inventory may be incomplete" in n for n in live_pi.notes)
    pi_trunc_note = next(n for n in live_pi.notes if "truncated by depth limit" in n)

    # 3. Capture session snapshot
    snap = capture_session(generation=1, home=tmp_path, cwd=tmp_path, registry=reg)
    entry_oc = next(
        e
        for e in snap.index.entries
        if "deploy" in e.entrypoint_path and ".opencode" in e.entrypoint_path
    )
    key_oc = canonical_key(entry_oc)

    entry_pi = next(
        e
        for e in snap.index.entries
        if "pideploy" in e.entrypoint_path and ".pi" in e.entrypoint_path
    )
    key_pi = canonical_key(entry_pi)

    # 4. Mutate filesystem: delete source directories on disk entirely
    shutil.rmtree(opencode_root)
    shutil.rmtree(pi_root)

    # 5. Forbid ALL filesystem access, path resolution, and live helpers during navigation
    def forbid(*args: object, **kwargs: object) -> object:
        raise AssertionError("report-time filesystem probe forbidden during navigation")

    with monkeypatch.context() as mp:
        mp.setattr("skill_lens.core.paths.home", forbid)
        mp.setattr("skill_lens.core.paths.display", forbid)
        mp.setattr("skill_lens.core.paths.same_location", forbid)
        mp.setattr(Path, "resolve", forbid)
        mp.setattr(Path, "stat", forbid)
        mp.setattr(Path, "lstat", forbid)
        mp.setattr(Path, "read_bytes", forbid)
        mp.setattr(Path, "read_text", forbid)
        mp.setattr(Path, "open", forbid)
        mp.setattr(Path, "iterdir", forbid)
        mp.setattr(Path, "readlink", forbid)
        mp.setattr(os, "walk", forbid)
        mp.setattr(os, "listdir", forbid)
        mp.setattr(os, "stat", forbid)
        mp.setattr(os, "lstat", forbid)
        mp.setattr(os.path, "realpath", forbid)
        mp.setattr(os.path, "samefile", forbid)
        mp.setattr(builtins, "open", forbid)
        mp.setattr(io, "open", forbid)
        mp.setattr(os, "open", forbid)
        mp.setattr(os, "scandir", forbid)

        frozen_oc = snapshot_why(snap, key_oc, "opencode")
        assert frozen_oc.found is True
        assert frozen_oc.headline is HeadlineState.ACTIVE
        assert any(
            "truncated by depth limit; inventory may be incomplete" in n for n in frozen_oc.notes
        )
        frozen_oc_note = next(n for n in frozen_oc.notes if "truncated by depth limit" in n)
        # Live and frozen notes agree exactly
        assert frozen_oc_note == oc_trunc_note

        frozen_pi = snapshot_why(snap, key_pi, "pi")
        assert frozen_pi.found is True
        assert frozen_pi.headline is HeadlineState.ACTIVE
        assert any(
            "truncated by depth limit; inventory may be incomplete" in n for n in frozen_pi.notes
        )
        frozen_pi_note = next(n for n in frozen_pi.notes if "truncated by depth limit" in n)
        assert frozen_pi_note == pi_trunc_note


def test_legacy_custom_snapshot_compatibility(tmp_path: Path) -> None:
    """Verify snapshot_why backward compatibility for custom/legacy SessionSnapshot
    instances that only supply disabled_overrides without resolved_controls."""
    from skill_lens.core.discovery import DiscoveredEntry, RootHit
    from skill_lens.core.snapshot_models import (
        CapturedFile,
        CapturedInput,
        FrozenDiscoveryIndex,
        SessionSnapshot,
    )
    from skill_lens.models.enums import ParseStatus
    from skill_lens.models.parsing import ParseResult

    claude_def = load_agent("claude")
    fm_parse = ParseResult(
        status=ParseStatus.VALID,
        directory_name="deploy",
        body="body",
        frontmatter_name="deploy",
        description="A deploy skill",
        source_path="/test/deploy/SKILL.md",
        errors=(),
        frontmatter={},
    )
    hit = RootHit(
        agent_id="claude",
        root_id="claude_personal",
        rank=90,
        rule_id="claude_personal",
        evidence="documented",
        scope=Scope.USER,
        nested=False,
        file_rule_id=None,
        nested_rule_id=None,
        specificity=2,
        entrypoint_path="/test/deploy",
        is_file=False,
    )
    entry = DiscoveredEntry(
        entrypoint_path="/test/deploy",
        name="deploy",
        is_file=False,
        is_symlink=False,
        canonical=None,
        parse=fm_parse,
        content_hash="sha256:test",
        hits=(hit,),
    )
    frozen_idx = FrozenDiscoveryIndex(
        home="/test_home",
        cwd="/test_cwd",
        entries=(entry,),
    )
    cf = CapturedFile(
        relative_path="SKILL.md", data=b"---\nname: deploy\n---\nbody", fingerprint="sha256:test"
    )
    ci = CapturedInput(path="/test_home/.claude/settings.json", data=None, error="missing")

    # Construct legacy SessionSnapshot without passing resolved_controls
    legacy_snap = SessionSnapshot(
        generation=1,
        home=Path("/test_home"),
        cwd=Path("/test_cwd"),
        registry=(claude_def,),
        index=frozen_idx,
        files={"/test/deploy": (cf,)},
        config_inputs={"/test_home/.claude/settings.json": ci},
        disabled_overrides={"claude": frozenset({"deploy"})},
        display_paths={"/test_home": "~"},
        same_locations=frozenset([("/test/deploy", "/test/deploy")]),
        scan=None,  # type: ignore[arg-type]
        doctor=None,  # type: ignore[arg-type]
    )

    # snapshot_why must fall back to disabled_overrides and resolve DISABLED
    res = snapshot_why(legacy_snap, "/test/deploy", "claude")
    assert res.found is True
    assert res.headline is HeadlineState.DISABLED
    assert res.candidates[0].state is HeadlineState.DISABLED


# ============================================================================
# 13. Recursion Cap Boundary Tests (OpenCode, Pi, Standard Roots)
# ============================================================================


def test_opencode_recursion_cap_boundaries(tmp_path: Path) -> None:
    """G. OpenCode recursion cap boundaries: leaf at exact cap (depth 32) discovered,
    control below cap (depth 31) discovered, pruned deeper child (depth 33) discloses
    depth_limit_truncated truthfully without unqualified absence, and doctor warns."""
    from unittest.mock import patch

    from skill_lens.core.doctor import run_doctor

    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    oc_base = tmp_path / ".opencode" / "skills"

    # 1. Below cap: depth 31
    p_below = oc_base
    for i in range(30):
        p_below = p_below / f"b{i}"
    p_below = p_below / "oc_below"
    make_skill(p_below, "oc_below", "OpenCode below cap")

    # 2. Leaf at exact cap: depth 32
    p_exact = oc_base
    for i in range(31):
        p_exact = p_exact / f"e{i}"
    p_exact = p_exact / "oc_exact"
    make_skill(p_exact, "oc_exact", "OpenCode leaf at exact cap")

    reg = load_registry()

    # Discover with only below and exact cap (no deeper children)
    idx_clean = discover(tmp_path, tmp_path, registry=reg)
    assert len(idx_clean.unreadable_roots) == 0

    res_below = resolve_skill(
        "oc_below", "opencode", tmp_path, tmp_path, index=idx_clean, registry=reg
    )
    assert res_below.found is True
    assert res_below.headline is HeadlineState.ACTIVE
    assert not any("truncated by depth limit" in n for n in res_below.notes)

    res_exact = resolve_skill(
        "oc_exact", "opencode", tmp_path, tmp_path, index=idx_clean, registry=reg
    )
    assert res_exact.found is True
    assert res_exact.headline is HeadlineState.ACTIVE
    assert not any("truncated by depth limit" in n for n in res_exact.notes)

    # 3. Add deeper child at depth 33 under a branch at depth 32
    p_branch = oc_base
    for i in range(31):
        p_branch = p_branch / f"br{i}"
    p_branch = p_branch / "oc_branch"
    make_skill(p_branch, "oc_branch", "OpenCode branch at exact cap")
    p_child = p_branch / "oc_deeper_child"
    make_skill(p_child, "oc_deeper_child", "OpenCode child beyond cap")

    idx_trunc = discover(tmp_path, tmp_path, registry=reg)
    assert any(u.detail == "depth_limit_truncated" for u in idx_trunc.unreadable_roots)

    # Skill at cap is discovered
    res_branch = resolve_skill(
        "oc_branch", "opencode", tmp_path, tmp_path, index=idx_trunc, registry=reg
    )
    assert res_branch.found is True
    assert res_branch.headline is HeadlineState.ACTIVE
    assert any(
        "truncated by depth limit; inventory may be incomplete" in n for n in res_branch.notes
    )

    # Deeper child is not found, but truncation is truthfully disclosed (no unqualified absence)
    res_child = resolve_skill(
        "oc_deeper_child", "opencode", tmp_path, tmp_path, index=idx_trunc, registry=reg
    )
    assert res_child.found is False
    assert any(
        "truncated by depth limit; inventory may be incomplete" in n for n in res_child.notes
    )

    # Doctor warns on truncated root
    doc = run_doctor(tmp_path)
    assert any(f.code == "depth_limit_truncated" and "opencode" in f.message for f in doc.findings)

    # Snapshot parity: zero-probe snapshot_why matches live resolution
    snap = capture_session(generation=1, home=tmp_path, cwd=tmp_path, registry=reg)
    e_exact = next(e for e in snap.index.entries if "oc_exact" in e.entrypoint_path)
    ckey_exact = canonical_key(e_exact)

    with (
        patch.object(Path, "is_dir", side_effect=AssertionError("report-time is_dir probe")),
        patch.object(Path, "resolve", side_effect=AssertionError("report-time resolve probe")),
    ):
        snap_exact = snapshot_why(snap, ckey_exact, "opencode")
        assert snap_exact.found is True
        assert snap_exact.headline is HeadlineState.ACTIVE


def test_pi_recursion_cap_boundaries(tmp_path: Path) -> None:
    """G. Pi recursion cap boundaries: leaf at exact cap (depth 16) discovered,
    control below cap (depth 15) discovered, deeper child (depth 17) pruned with
    truthful disclosure in resolver notes and doctor findings."""
    from unittest.mock import patch

    from skill_lens.core.doctor import run_doctor

    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    pi_base = tmp_path / ".pi" / "skills"

    # 1. Below cap: depth 15
    p_below = pi_base
    for i in range(14):
        p_below = p_below / f"pb{i}"
    p_below = p_below / "pi_below"
    make_skill(p_below, "pi_below", "Pi below cap")

    # 2. Leaf at exact cap: depth 16
    p_exact = pi_base
    for i in range(15):
        p_exact = p_exact / f"pe{i}"
    p_exact = p_exact / "pi_exact"
    make_skill(p_exact, "pi_exact", "Pi leaf at exact cap")

    reg = load_registry()

    # Discover with only below and exact cap (no deeper children)
    idx_clean = discover(tmp_path, tmp_path, registry=reg)
    assert len(idx_clean.unreadable_roots) == 0

    res_below = resolve_skill("pi_below", "pi", tmp_path, tmp_path, index=idx_clean, registry=reg)
    assert res_below.found is True
    assert res_below.headline is HeadlineState.ACTIVE
    assert not any("truncated by depth limit" in n for n in res_below.notes)

    res_exact = resolve_skill("pi_exact", "pi", tmp_path, tmp_path, index=idx_clean, registry=reg)
    assert res_exact.found is True
    assert res_exact.headline is HeadlineState.ACTIVE
    assert not any("truncated by depth limit" in n for n in res_exact.notes)

    # 3. Add deeper child at depth 17 under a non-skill directory at depth 16
    p_non_skill = pi_base
    for i in range(15):
        p_non_skill = p_non_skill / f"pbr{i}"
    p_non_skill = p_non_skill / "non_skill_dir"
    p_deep = p_non_skill / "pi_deep_child"
    make_skill(p_deep, "pi_deep_child", "Pi child beyond cap")

    idx_trunc = discover(tmp_path, tmp_path, registry=reg)
    assert any(u.detail == "depth_limit_truncated" for u in idx_trunc.unreadable_roots)

    # Deep child is not found, but truncation is truthfully disclosed (no unqualified absence)
    res_deep = resolve_skill(
        "pi_deep_child", "pi", tmp_path, tmp_path, index=idx_trunc, registry=reg
    )
    assert res_deep.found is False
    assert any("truncated by depth limit; inventory may be incomplete" in n for n in res_deep.notes)

    # Doctor warns on truncated root
    doc = run_doctor(tmp_path)
    assert any(f.code == "depth_limit_truncated" and "pi" in f.message for f in doc.findings)

    # Snapshot parity: zero-probe snapshot_why matches live resolution
    snap = capture_session(generation=1, home=tmp_path, cwd=tmp_path, registry=reg)
    e_exact = next(e for e in snap.index.entries if "pi_exact" in e.entrypoint_path)
    ckey_exact = canonical_key(e_exact)

    with (
        patch.object(Path, "is_dir", side_effect=AssertionError("report-time is_dir probe")),
        patch.object(Path, "resolve", side_effect=AssertionError("report-time resolve probe")),
    ):
        snap_exact = snapshot_why(snap, ckey_exact, "pi")
        assert snap_exact.found is True
        assert snap_exact.headline is HeadlineState.ACTIVE


def test_standard_recursive_roots_cap_boundaries(tmp_path: Path) -> None:
    """G. Standard recursive roots (e.g. Codex plugins): skills dir at exact cap (depth 4)
    discovered without false truncation; non-skills dir at depth 4 with subdirectories
    records truncation and deeper skills disclose truncation truthfully."""
    paths.set_sandbox(tmp_path)
    (tmp_path / ".git").mkdir()

    codex_plugins = tmp_path / ".codex" / ".tmp" / "plugins"

    # 1. Exact cap (depth 4): plugins / p1 / p2 / p3 / skills
    p_exact = codex_plugins / "p1" / "p2" / "p3" / "skills" / "exact_plugin_skill"
    make_skill(p_exact, "exact_plugin_skill", "Codex plugin leaf at exact cap")

    reg = load_registry()
    idx_clean = discover(tmp_path, tmp_path, registry=reg)
    assert len(idx_clean.unreadable_roots) == 0

    res_exact = resolve_skill(
        "exact_plugin_skill", "codex", tmp_path, tmp_path, index=idx_clean, registry=reg
    )
    assert res_exact.found is True
    assert res_exact.headline is HeadlineState.ACTIVE
    assert not any("truncated by depth limit" in n for n in res_exact.notes)

    # 2. Deeper than cap (depth 5): plugins / p1 / p2 / p3 / p4 / skills
    p_deep = codex_plugins / "p1" / "p2" / "p3" / "p4" / "skills" / "deep_plugin_skill"
    make_skill(p_deep, "deep_plugin_skill", "Codex plugin deeper than cap")

    idx_trunc = discover(tmp_path, tmp_path, registry=reg)
    assert any(u.detail == "depth_limit_truncated" for u in idx_trunc.unreadable_roots)

    res_deep = resolve_skill(
        "deep_plugin_skill", "codex", tmp_path, tmp_path, index=idx_trunc, registry=reg
    )
    assert res_deep.found is False
    assert any("truncated by depth limit; inventory may be incomplete" in n for n in res_deep.notes)
