"""Stage C verification tests: F05, F06, F07.

Discriminating tests covering:
1. CLI cwd user input resolution (live terminal-relative with patched HOME vs
   sandboxed, escape guards).
2. OpenCode XDG config root containment and lazy resolution.
3. Root-hit dedup identity with multiple plugin shortcuts, actual why consumer resolution,
   exact duplicate hits dedup, root/agent order invariant aliases, wrong-alias negative checks,
   per-hit aliases (DSH vs Claude), alias-specific disabled matching, synthetic frontmatter-name
   != folder-alias override => DISABLED, and snapshot agreement without live reads.
4. Entry-format metadata controls (Codex plugin README.md incidental, real malformed SKILL.md fails,
   Pi qualified standalone .md vs incidental without description, OpenCode V2 root *.md,
   root SKILL.md
   single-file ID SKILL, nested exact SKILL.md without direct child duplication,
   and historical F17 symlink to standalone target outside scanned root under supported Pi root).
"""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from skill_lens.cli import app
from skill_lens.core import paths
from skill_lens.core.compare import run_compare
from skill_lens.core.diff import build_diff_report
from skill_lens.core.discovery import canonical_key, discover
from skill_lens.core.doctor import run_doctor
from skill_lens.core.resolver import entrypoint_alias, resolve_skill
from skill_lens.core.snapshot import capture_session, snapshot_diff, snapshot_why
from skill_lens.models.enums import (
    EntryFormat,
    Evidence,
    HeadlineState,
    RootBase,
    Scope,
    Severity,
)
from skill_lens.models.parsing import ERR_DANGLING_SYMLINK, ERR_SYMLINK_CYCLE
from skill_lens.registry.loader import AgentDefinition, AgentRoot, _parse_root, load_registry

runner = CliRunner()


def _make_skill(path: Path, name: str, description: str, body: str = "# Body\n") -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n{body}",
        encoding="utf-8",
    )


# --- 1. CLI CWD Tests (F05) ------------------------------------------------


def test_cli_cwd_live_terminal_relative(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """In live execution, relative --cwd is resolved relative to the terminal cwd."""
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    paths.set_sandbox(None)

    terminal = tmp_path / "term"
    child = terminal / "sub"
    child.mkdir(parents=True)
    (child / ".git").mkdir()
    monkeypatch.setattr(paths, "terminal_cwd", lambda: terminal)

    _make_skill(child / ".claude" / "skills" / "test_live", "test_live", "Desc")

    # Relative child path
    cmd = ["why", "test_live", "--agent", "claude", "--cwd", "sub", "--json"]
    result = runner.invoke(app, cmd)
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["cwd"] == str(child.resolve())
    assert payload["found"] is True
    assert len(payload["candidates"]) == 1
    assert payload["candidates"][0]["state"] == "ACTIVE"
    assert payload["candidates"][0]["installation"]["name"] == "test_live"

    # Relative dot path
    monkeypatch.setattr(paths, "terminal_cwd", lambda: child)
    cmd_dot = ["why", "test_live", "--agent", "claude", "--cwd", ".", "--json"]
    result_dot = runner.invoke(app, cmd_dot)
    assert result_dot.exit_code == 0
    payload_dot = json.loads(result_dot.stdout)
    assert payload_dot["cwd"] == str(child.resolve())
    assert payload_dot["found"] is True
    assert len(payload_dot["candidates"]) == 1
    assert payload_dot["candidates"][0]["state"] == "ACTIVE"
    assert payload_dot["candidates"][0]["installation"]["name"] == "test_live"

    # Default cwd (omitted --cwd) equals --cwd .
    cmd_default = ["why", "test_live", "--agent", "claude", "--json"]
    result_default = runner.invoke(app, cmd_default)
    assert result_default.exit_code == 0
    payload_default = json.loads(result_default.stdout)
    assert payload_default == payload_dot

    # Isolation assertions: no real HOME reads
    assert paths.home() == fake_home
    assert not (fake_home / ".claude").exists()


def test_cli_cwd_sandboxed_relative_and_escape_rejection(mock_home: Path) -> None:
    """Under sandbox, relative --cwd is sandbox-relative; escapes fail with exit 2."""
    sb = mock_home.resolve()
    child = sb / "project"
    child.mkdir(parents=True, exist_ok=True)
    (child / ".git").mkdir()
    _make_skill(child / ".claude" / "skills" / "demo", "demo", "Demo")

    # Child
    res_child = runner.invoke(
        app, ["why", "demo", "--agent", "claude", "--cwd", "project", "--json"]
    )
    assert res_child.exit_code == 0
    child_payload = json.loads(res_child.stdout)
    assert child_payload["cwd"] == str(child)
    assert child_payload["found"] is True

    # Dot
    res_dot = runner.invoke(app, ["why", "demo", "--agent", "claude", "--cwd", ".", "--json"])
    assert res_dot.exit_code == 0
    dot_payload = json.loads(res_dot.stdout)
    assert dot_payload["cwd"] == str(sb)

    # Absolute inside sandbox
    res_abs = runner.invoke(
        app, ["why", "demo", "--agent", "claude", "--cwd", str(child), "--json"]
    )
    assert res_abs.exit_code == 0
    abs_payload = json.loads(res_abs.stdout)
    assert abs_payload["cwd"] == str(child)
    assert abs_payload["found"] is True

    # Escape attempt via ..
    res_escape = runner.invoke(app, ["why", "demo", "--agent", "claude", "--cwd", "..", "--json"])
    assert res_escape.exit_code == 2
    assert "must stay inside" in res_escape.output.lower()

    # Escape attempt via absolute path outside sandbox
    outside = sb.parent / "outside"
    outside.mkdir(exist_ok=True)
    res_abs_esc = runner.invoke(
        app, ["why", "demo", "--agent", "claude", "--cwd", str(outside), "--json"]
    )
    assert res_abs_esc.exit_code == 2
    assert "must stay inside" in res_abs_esc.output.lower()


def test_cli_cwd_reported_consistently_across_commands(mock_home: Path) -> None:
    """All commands report identical absolute cwd across ., .., child, and absolute paths."""
    sb = mock_home.resolve()
    proj = sb / "myproj"
    sub = proj / "sub"
    sub.mkdir(parents=True, exist_ok=True)
    (proj / ".git").mkdir(exist_ok=True)
    _make_skill(proj / ".claude" / "skills" / "sync", "sync", "Sync skill")

    expected_cwd = str(proj)

    # 1. Child relative path across commands
    for cmd_args in [
        ["scan", "--cwd", "myproj", "--json"],
        ["why", "sync", "--agent", "claude", "--cwd", "myproj", "--json"],
        ["doctor", "--cwd", "myproj", "--json"],
        ["diff", "sync", "--cwd", "myproj", "--json"],
        ["compare", "--agent", "claude", "--agent", "pi", "--cwd", "myproj", "--json"],
    ]:
        res = runner.invoke(app, cmd_args)
        assert res.exit_code == 0, f"Command {cmd_args} failed: {res.output}"
        data = json.loads(res.stdout)
        assert data["cwd"] == expected_cwd, (
            f"Cmd {cmd_args} reported {data['cwd']} != {expected_cwd}"
        )

    # 2. Relative path with '..' inside sandbox
    res_sub_up = runner.invoke(app, ["scan", "--cwd", "myproj/sub/..", "--json"])
    assert res_sub_up.exit_code == 0
    assert json.loads(res_sub_up.stdout)["cwd"] == expected_cwd

    # 3. Absolute path inside sandbox
    res_abs = runner.invoke(app, ["scan", "--cwd", expected_cwd, "--json"])
    assert res_abs.exit_code == 0
    assert json.loads(res_abs.stdout)["cwd"] == expected_cwd


# --- 2. OpenCode XDG Config Root Tests (F05) -------------------------------


def test_xdg_config_home_sandboxed_containment(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sandbox prevents inheriting external XDG_CONFIG_HOME; falls back or honours contained."""
    sb = mock_home.resolve()
    external_xdg = sb.parent / "external_xdg"
    external_xdg.mkdir(exist_ok=True)

    # 1. External XDG is ignored under sandbox -> falls back to sandbox / .config
    monkeypatch.setenv("XDG_CONFIG_HOME", str(external_xdg))
    assert paths.xdg_config_home() == sb / ".config"

    # 2. Contained XDG inside sandbox is honoured
    contained_xdg = sb / "custom_config"
    contained_xdg.mkdir(exist_ok=True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(contained_xdg))
    assert paths.xdg_config_home() == contained_xdg

    # 3. Unset XDG defaults to sandbox / .config
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert paths.xdg_config_home() == sb / ".config"


def test_opencode_discovery_via_xdg_config_home(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OpenCode native root discovers skills under paths.xdg_config_home()."""
    sb = mock_home.resolve()
    contained_xdg = sb / "my_xdg"
    opencode_skills = contained_xdg / "opencode" / "skills"
    _make_skill(opencode_skills / "helper", "helper", "OpenCode Helper")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(contained_xdg))
    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    opencode_entries = [e for e in idx.entries if "helper" in e.entrypoint_path]
    assert len(opencode_entries) == 1
    assert any(h.agent_id == "opencode" for h in opencode_entries[0].hits)


# --- 3. Root-Hit Dedup & Per-Hit Aliases Tests (F06) -----------------------


def test_multiple_plugin_shortcuts_in_same_recursive_root_retained(mock_home: Path) -> None:
    """Two distinct plugin shortcuts reaching the same canonical skill produce two
    candidates in why.
    """
    sb = mock_home.resolve()
    canonical = sb / "shared_plugins" / "my_skill"
    _make_skill(canonical, "canonical_name", "Plugin canonical")

    # Create two shortcuts under .codex/.tmp/plugins
    p1 = sb / ".codex" / ".tmp" / "plugins" / "plugin_a" / "skills" / "shortcut_a"
    p2 = sb / ".codex" / ".tmp" / "plugins" / "plugin_b" / "skills" / "shortcut_b"
    p1.parent.mkdir(parents=True, exist_ok=True)
    p2.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(canonical, p1)
    os.symlink(canonical, p2)

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    # Consumer test: resolve_skill produces 2 candidates
    rep = resolve_skill("canonical_name", "codex", cwd=sb, home=sb, index=idx, registry=reg)
    assert rep.found is True
    assert len(rep.candidates) == 2
    cand_paths = {c.installation.entrypoint_path for c in rep.candidates}
    assert str(p1) in cand_paths
    assert str(p2) in cand_paths

    entry = next(e for e in idx.entries if e.canonical_path == str(canonical.resolve()))
    hit_paths = {h.entrypoint_path for h in entry.hits if h.agent_id == "codex"}
    assert str(p1) in hit_paths
    assert str(p2) in hit_paths
    assert len(hit_paths) == 2


def test_exact_duplicate_hits_dedup(mock_home: Path) -> None:
    """Exact identical (path, agent, root, nested) hits are deduped to one hit and candidate."""
    sb = mock_home.resolve()
    canonical = sb / "skills_lib" / "single_skill"
    _make_skill(canonical, "single_skill", "Single skill")

    link = sb / ".codex" / "skills" / "single_link"
    link.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(canonical, link)

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)
    rep = resolve_skill("single_skill", "codex", cwd=sb, home=sb, index=idx, registry=reg)
    assert rep.found is True
    assert len(rep.candidates) == 1


def test_root_and_agent_order_invariant_aliases(mock_home: Path) -> None:
    """Resolution and aliases are invariant to registry agent order and root order.

    Exercises the same canonical target reached under at least two distinct roots of the
    same agent through different aliases (DSH native .dsh/skills vs shared .agents/skills),
    verifying native rank vs shared rank precedence and invariance when roots and
    agents are reversed.
    """
    sb = mock_home.resolve()
    canonical = sb / "lib" / "canonical_body"
    _make_skill(canonical, "fm_name", "Shared capability")

    # Root 1 of DSH: native root (.dsh/skills) with alias "original" (rank 70)
    dsh_root = sb / ".dsh" / "skills"
    dsh_root.mkdir(parents=True, exist_ok=True)
    os.symlink(canonical, dsh_root / "original")

    # Root 2 of DSH: shared global root (.agents/skills) with alias "shared_alias" (rank 65)
    agents_root = sb / ".agents" / "skills"
    agents_root.mkdir(parents=True, exist_ok=True)
    os.symlink(canonical, agents_root / "shared_alias")

    # Claude root: .claude/skills with alias "alternate" (rank 100)
    claude_root = sb / ".claude" / "skills"
    claude_root.mkdir(parents=True, exist_ok=True)
    os.symlink(canonical, claude_root / "alternate")

    reg = load_registry()
    # Actually permute AgentDefinition.roots and agent dictionary
    permuted_reg = {
        k: replace(agent, roots=tuple(reversed(agent.roots)))
        for k, agent in reversed(list(reg.items()))
    }

    idx1 = discover(home=sb, cwd=sb, registry=reg)
    idx2 = discover(home=sb, cwd=sb, registry=permuted_reg)

    # 1. DSH resolution under native root alias "original" (native rank 70)
    res1_dsh_orig = resolve_skill("original", "dsh", cwd=sb, home=sb, index=idx1, registry=reg)
    res2_dsh_orig = resolve_skill(
        "original", "dsh", cwd=sb, home=sb, index=idx2, registry=permuted_reg
    )
    assert res1_dsh_orig.found == res2_dsh_orig.found is True
    assert (
        res1_dsh_orig.candidates[0].installation.name
        == res2_dsh_orig.candidates[0].installation.name
        == "original"
    )
    assert (
        res1_dsh_orig.candidates[0].state
        == res2_dsh_orig.candidates[0].state
        == HeadlineState.ACTIVE
    )
    assert (
        res1_dsh_orig.candidates[0].rule_id
        == res2_dsh_orig.candidates[0].rule_id
        == "dsh_documented_user"
    )
    assert res1_dsh_orig.candidates[0].rank == res2_dsh_orig.candidates[0].rank == 70

    # 2. DSH resolution under shared root alias "shared_alias" (shared rank 65)
    res1_dsh_shared = resolve_skill(
        "shared_alias", "dsh", cwd=sb, home=sb, index=idx1, registry=reg
    )
    res2_dsh_shared = resolve_skill(
        "shared_alias", "dsh", cwd=sb, home=sb, index=idx2, registry=permuted_reg
    )
    assert res1_dsh_shared.found == res2_dsh_shared.found is True
    assert (
        res1_dsh_shared.candidates[0].installation.name
        == res2_dsh_shared.candidates[0].installation.name
        == "shared_alias"
    )
    assert (
        res1_dsh_shared.candidates[0].state
        == res2_dsh_shared.candidates[0].state
        == HeadlineState.ACTIVE
    )
    assert (
        res1_dsh_shared.candidates[0].rule_id
        == res2_dsh_shared.candidates[0].rule_id
        == "dsh_documented_shared"
    )
    assert res1_dsh_shared.candidates[0].rank == res2_dsh_shared.candidates[0].rank == 65

    # 3. Claude resolution under "alternate"
    res1_claude = resolve_skill("alternate", "claude", cwd=sb, home=sb, index=idx1, registry=reg)
    res2_claude = resolve_skill(
        "alternate", "claude", cwd=sb, home=sb, index=idx2, registry=permuted_reg
    )
    assert res1_claude.found == res2_claude.found is True
    assert (
        res1_claude.candidates[0].installation.name
        == res2_claude.candidates[0].installation.name
        == "alternate"
    )
    assert (
        res1_claude.candidates[0].state == res2_claude.candidates[0].state == HeadlineState.ACTIVE
    )
    assert (
        res1_claude.candidates[0].rule_id
        == res2_claude.candidates[0].rule_id
        == "claude_personal_beats_project"
    )
    assert res1_claude.candidates[0].rank == res2_claude.candidates[0].rank == 100

    # 4. Cross check / wrong alias negative controls:
    # DSH cannot resolve Claude's alias
    assert (
        resolve_skill("alternate", "dsh", cwd=sb, home=sb, index=idx1, registry=reg).found is False
    )
    assert (
        resolve_skill("alternate", "dsh", cwd=sb, home=sb, index=idx2, registry=permuted_reg).found
        is False
    )
    # Claude cannot resolve DSH's native alias
    assert (
        resolve_skill("original", "claude", cwd=sb, home=sb, index=idx1, registry=reg).found
        is False
    )
    assert (
        resolve_skill(
            "original", "claude", cwd=sb, home=sb, index=idx2, registry=permuted_reg
        ).found
        is False
    )
    # Claude cannot resolve DSH's shared alias
    assert (
        resolve_skill("shared_alias", "claude", cwd=sb, home=sb, index=idx1, registry=reg).found
        is False
    )
    assert (
        resolve_skill(
            "shared_alias", "claude", cwd=sb, home=sb, index=idx2, registry=permuted_reg
        ).found
        is False
    )
    # Non-existent alias fails across both indices and agents
    assert (
        resolve_skill(
            "nonexistent", "dsh", cwd=sb, home=sb, index=idx2, registry=permuted_reg
        ).found
        is False
    )
    assert (
        resolve_skill(
            "nonexistent", "claude", cwd=sb, home=sb, index=idx2, registry=permuted_reg
        ).found
        is False
    )

    # 5. Snapshot parity across root/agent order permutation
    s1 = capture_session(home=sb, cwd=sb, generation=1, registry=reg)
    s2 = capture_session(home=sb, cwd=sb, generation=1, registry=permuted_reg)
    key = str(canonical.resolve())
    w1_dsh = snapshot_why(s1, key, "dsh")
    w2_dsh = snapshot_why(s2, key, "dsh")
    assert w1_dsh.found == w2_dsh.found is True
    assert w1_dsh.headline == w2_dsh.headline == HeadlineState.ACTIVE
    assert (
        w1_dsh.candidates[0].installation.name
        == w2_dsh.candidates[0].installation.name
        == "original"
    )
    assert w1_dsh.candidates[0].rule_id == w2_dsh.candidates[0].rule_id == "dsh_documented_user"
    assert w1_dsh.candidates[0].rank == w2_dsh.candidates[0].rank == 70

    w1_claude = snapshot_why(s1, key, "claude")
    w2_claude = snapshot_why(s2, key, "claude")
    assert w1_claude.found == w2_claude.found is True
    assert w1_claude.headline == w2_claude.headline == HeadlineState.ACTIVE
    assert (
        w1_claude.candidates[0].installation.name
        == w2_claude.candidates[0].installation.name
        == "alternate"
    )
    assert (
        w1_claude.candidates[0].rule_id
        == w2_claude.candidates[0].rule_id
        == "claude_personal_beats_project"
    )
    assert w1_claude.candidates[0].rank == w2_claude.candidates[0].rank == 100

    assert s1.files[key] == s2.files[key]


def test_wrong_alias_negative_check(mock_home: Path) -> None:
    """Resolving with a non-matching alias fails to find the skill."""
    sb = mock_home.resolve()
    canonical = sb / "lib" / "skill"
    _make_skill(canonical, "fm_name", "Desc")

    dsh_root = sb / ".dsh" / "skills"
    dsh_root.mkdir(parents=True, exist_ok=True)
    os.symlink(canonical, dsh_root / "original")

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    res_wrong = resolve_skill("alternate", "dsh", cwd=sb, home=sb, index=idx, registry=reg)
    assert res_wrong.found is False
    assert len(res_wrong.candidates) == 0


def test_synthetic_identity_source_disabled_overrides_matching(mock_home: Path) -> None:
    """Disabled overrides match actual per-hit supported identity names:
    - frontmatter_name identity: matches declared frontmatter name (synth_fm), not folder alias.
    - directory_name identity: matches relevant hit alias (synth_folder), not frontmatter name.
    - hybrid/either identity: matches either synonym.
    """
    sb = mock_home.resolve()
    skill_dir = sb / ".agents" / "skills" / "synth_folder"
    _make_skill(skill_dir, "synth_fm", "Synthetic frontmatter skill")

    # 1. Frontmatter identity agent:
    fm_root = AgentRoot(
        id="fm_root",
        kind="global",
        path=".agents/skills",
        scope=Scope.USER,
        rank=80,
        rule_id="fm_root_rule",
        evidence=Evidence.DOCUMENTED,
    )
    fm_agent = AgentDefinition(
        id="synth_fm_agent",
        name="Synth FM Agent",
        identity_source="frontmatter_name",
        collision_policy="Shadow",
        policy_evidence=Evidence.DOCUMENTED,
        coexist_policy="shadow",
        walk_boundary="git_root",
        unsearched_rule_id="synth_unsearched",
        roots=(fm_root,),
    )
    dir_agent = AgentDefinition(
        id="synth_dir_agent",
        name="Synth Dir Agent",
        identity_source="directory_name",
        collision_policy="Shadow",
        policy_evidence=Evidence.DOCUMENTED,
        coexist_policy="shadow",
        walk_boundary="git_root",
        unsearched_rule_id="synth_unsearched",
        roots=(fm_root,),
    )
    hybrid_agent = AgentDefinition(
        id="synth_hybrid_agent",
        name="Synth Hybrid Agent",
        identity_source="hybrid",
        collision_policy="Shadow",
        policy_evidence=Evidence.DOCUMENTED,
        coexist_policy="shadow",
        walk_boundary="git_root",
        unsearched_rule_id="synth_unsearched",
        roots=(fm_root,),
    )
    custom_reg = {
        "synth_fm_agent": fm_agent,
        "synth_dir_agent": dir_agent,
        "synth_hybrid_agent": hybrid_agent,
    }

    idx = discover(home=sb, cwd=sb, registry=custom_reg)

    # FM override -> DISABLED
    res_fm_dis = resolve_skill(
        "synth_fm",
        "synth_fm_agent",
        cwd=sb,
        home=sb,
        index=idx,
        registry=custom_reg,
        disabled_overrides=frozenset({"synth_fm"}),
    )
    assert res_fm_dis.found is True
    assert res_fm_dis.candidates[0].state is HeadlineState.DISABLED

    # Folder override -> stays ACTIVE for frontmatter_name identity
    res_fm_act = resolve_skill(
        "synth_fm",
        "synth_fm_agent",
        cwd=sb,
        home=sb,
        index=idx,
        registry=custom_reg,
        disabled_overrides=frozenset({"synth_folder"}),
    )
    assert res_fm_act.found is True
    assert res_fm_act.candidates[0].state is HeadlineState.ACTIVE

    # Folder override -> DISABLED
    res_dir_dis = resolve_skill(
        "synth_folder",
        "synth_dir_agent",
        cwd=sb,
        home=sb,
        index=idx,
        registry=custom_reg,
        disabled_overrides=frozenset({"synth_folder"}),
    )
    assert res_dir_dis.found is True
    assert res_dir_dis.candidates[0].state is HeadlineState.DISABLED

    # FM override -> stays ACTIVE for directory_name identity
    res_dir_act = resolve_skill(
        "synth_folder",
        "synth_dir_agent",
        cwd=sb,
        home=sb,
        index=idx,
        registry=custom_reg,
        disabled_overrides=frozenset({"synth_fm"}),
    )
    assert res_dir_act.found is True
    assert res_dir_act.candidates[0].state is HeadlineState.ACTIVE

    custom_hyb_reg = custom_reg

    # Both synonyms disable:
    res_hyb_1 = resolve_skill(
        "synth_fm",
        "synth_hybrid_agent",
        cwd=sb,
        home=sb,
        index=idx,
        registry=custom_hyb_reg,
        disabled_overrides=frozenset({"synth_fm"}),
    )
    assert res_hyb_1.candidates[0].state is HeadlineState.DISABLED

    res_hyb_2 = resolve_skill(
        "synth_folder",
        "synth_hybrid_agent",
        cwd=sb,
        home=sb,
        index=idx,
        registry=custom_hyb_reg,
        disabled_overrides=frozenset({"synth_folder"}),
    )
    assert res_hyb_2.candidates[0].state is HeadlineState.DISABLED


def test_resolver_per_hit_aliases_and_disabled_overrides(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Shared canonical library has different aliases under DSH vs Claude roots.

    Captured aliases agree with live resolution, and snapshot_why performs zero disk reads.
    """
    sb = mock_home.resolve()
    canonical = sb / "lib" / "canonical_body"
    _make_skill(canonical, "fm_name", "Shared capability")

    # DSH link named 'original'
    dsh_root = sb / ".dsh" / "skills"
    dsh_root.mkdir(parents=True, exist_ok=True)
    os.symlink(canonical, dsh_root / "original")

    # Claude link named 'alternate'
    claude_root = sb / ".claude" / "skills"
    claude_root.mkdir(parents=True, exist_ok=True)
    os.symlink(canonical, claude_root / "alternate")

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    # DSH searches 'original'
    dsh_rep = resolve_skill("original", "dsh", cwd=sb, home=sb, index=idx, registry=reg)
    assert dsh_rep.found is True
    assert len(dsh_rep.candidates) == 1
    assert dsh_rep.candidates[0].state is HeadlineState.ACTIVE
    assert dsh_rep.candidates[0].installation.name == "original"

    # Claude searches 'alternate'
    claude_rep = resolve_skill("alternate", "claude", cwd=sb, home=sb, index=idx, registry=reg)
    assert claude_rep.found is True
    assert len(claude_rep.candidates) == 1
    assert claude_rep.candidates[0].state is HeadlineState.ACTIVE
    assert claude_rep.candidates[0].installation.name == "alternate"

    # Disabled override on 'original' disables DSH resolution but not Claude
    dsh_disabled = resolve_skill(
        "original",
        "dsh",
        cwd=sb,
        home=sb,
        index=idx,
        registry=reg,
        disabled_overrides=frozenset({"original"}),
    )
    assert dsh_disabled.candidates[0].state is HeadlineState.DISABLED

    # Captured session snapshot agreement
    snap = capture_session(generation=1, home=sb, cwd=sb)
    target_entry = next(
        e
        for e in snap.index.entries
        if "original" in e.entrypoint_path or "alternate" in e.entrypoint_path
    )
    key = canonical_key(target_entry)

    # Guard against disk reads during snapshot_why
    def forbidden_io(*args: object, **kwargs: object) -> object:
        raise AssertionError("Disk read attempted during snapshot_why")

    monkeypatch.setattr(Path, "read_bytes", forbidden_io)
    monkeypatch.setattr(Path, "read_text", forbidden_io)

    snap_why_dsh = snapshot_why(snap, key, "dsh")
    assert snap_why_dsh.found is True
    assert snap_why_dsh.candidates[0].installation.name == "original"

    snap_why_claude = snapshot_why(snap, key, "claude")
    assert snap_why_claude.found is True
    assert snap_why_claude.candidates[0].installation.name == "alternate"


# --- 4. Entry Format Metadata Controls (F07) -------------------------------


def test_codex_plugin_readme_is_incidental_not_error(mock_home: Path) -> None:
    """Codex plugin skills/README.md is incidental documentation, not an error."""
    sb = mock_home.resolve()
    plugin_skills = sb / ".codex" / ".tmp" / "plugins" / "my_plugin" / "skills"
    plugin_skills.mkdir(parents=True, exist_ok=True)
    (plugin_skills / "README.md").write_text(
        "# Documentation\n\nThis is a readme.\n", encoding="utf-8"
    )

    # Real skill in the plugin
    _make_skill(plugin_skills / "real_skill", "real_skill", "Real plugin skill")

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    # README.md should NOT be discovered as a skill entry
    discovered_paths = [e.entrypoint_path for e in idx.entries]
    assert not any("README.md" in p for p in discovered_paths)
    assert any("real_skill" in p for p in discovered_paths)

    # scan and doctor with --fail-on error exit 0 because README.md is not treated as an error
    res_scan = runner.invoke(app, ["scan", "--cwd", str(sb), "--fail-on", "error"])
    assert res_scan.exit_code == 0
    res_doc = runner.invoke(app, ["doctor", "--cwd", str(sb), "--fail-on", "error"])
    assert res_doc.exit_code == 0

    # Opposite control: malformed real declaration fails doctor with error
    bad_skill = plugin_skills / "bad_skill"
    bad_skill.mkdir(parents=True, exist_ok=True)
    (bad_skill / "SKILL.md").write_text("---\nname: [unclosed yaml list\n---\n", encoding="utf-8")
    bad_idx = discover(home=sb, cwd=sb, registry=reg)
    bad_doc = run_doctor(sb, index=bad_idx, registry=reg)
    assert any(
        "bad_skill" in f.message or (f.path and "bad_skill" in f.path) for f in bad_doc.findings
    )
    res_bad_doc = runner.invoke(app, ["doctor", "--cwd", str(sb), "--fail-on", "error"])
    assert res_bad_doc.exit_code != 0


def test_pi_qualified_standalone_md_skips_incidental_without_description(mock_home: Path) -> None:
    """Pi skips incidental standalone .md files without description, keeps declared SKILL.md."""
    sb = mock_home.resolve()
    pi_skills = sb / ".pi" / "agent" / "skills"
    pi_skills.mkdir(parents=True, exist_ok=True)

    # Incidental markdown with no frontmatter / description
    (pi_skills / "incidental.md").write_text("# Plain doc without frontmatter\n", encoding="utf-8")

    # Qualified standalone markdown with valid description
    (pi_skills / "qualified.md").write_text(
        "---\nname: qualified\ndescription: Qualified Pi skill.\n---\n# Content\n",
        encoding="utf-8",
    )

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    paths_found = [e.entrypoint_path for e in idx.entries]
    assert not any("incidental.md" in p for p in paths_found)
    assert any("qualified.md" in p for p in paths_found)


def test_opencode_v2_root_md_and_nested_exact_skill_md(mock_home: Path) -> None:
    """OpenCode V2 discovers root *.md files (including root SKILL.md as ID SKILL) and
    recursive exact nested SKILL.md without child duplicates.
    """
    sb = mock_home.resolve()
    oc_root = sb / ".config" / "opencode" / "skills"
    oc_root.mkdir(parents=True, exist_ok=True)

    # Root *.md
    (oc_root / "root_tool.md").write_text(
        "---\nname: root_tool\ndescription: Tool at root\n---\n", encoding="utf-8"
    )

    # Root SKILL.md (should be single-file skill with ID SKILL)
    (oc_root / "SKILL.md").write_text(
        "---\nname: root_skill\ndescription: Root skill\n---\n", encoding="utf-8"
    )

    # Direct child skill directory
    direct_child = oc_root / "direct_tool"
    direct_child.mkdir(parents=True, exist_ok=True)
    (direct_child / "SKILL.md").write_text(
        "---\nname: direct_tool\ndescription: Direct child\n---\n", encoding="utf-8"
    )

    # Nested exact SKILL.md at depth 2
    nested_dir = oc_root / "deep" / "nested_tool"
    nested_dir.mkdir(parents=True, exist_ok=True)
    (nested_dir / "SKILL.md").write_text(
        "---\nname: nested_tool\ndescription: Nested tool\n---\n", encoding="utf-8"
    )

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    oc_entries = [e for e in idx.entries if any(h.agent_id == "opencode" for h in e.hits)]
    oc_paths = [e.entrypoint_path for e in oc_entries]
    assert any("root_tool.md" in p for p in oc_paths)
    assert any("nested_tool" in p for p in oc_paths)

    # Root SKILL.md found as single-file skill
    root_skill_entry = next(
        e
        for e in oc_entries
        if e.entrypoint_path.endswith("SKILL.md")
        and "nested" not in e.entrypoint_path
        and "direct" not in e.entrypoint_path
    )
    assert root_skill_entry.is_file is True
    assert entrypoint_alias(root_skill_entry.entrypoint_path, True) == "SKILL"

    # Direct child tool must NOT be duplicated
    direct_matches = [e for e in oc_entries if "direct_tool" in e.entrypoint_path]
    assert len(direct_matches) == 1


def test_historical_f17_symlink_standalone_target_outside_scanned_root(mock_home: Path) -> None:
    """Symlink standalone target OUTSIDE scanned roots discovered via supported Pi
    qualified root.
    """
    sb = mock_home.resolve()
    outside = sb / "completely_outside_roots"
    outside.mkdir(parents=True, exist_ok=True)
    target = outside / "real_standalone.md"
    target.write_text(
        "---\nname: real_standalone\ndescription: Target outside root\n---\n# Content\n",
        encoding="utf-8",
    )

    # Use supported Pi qualified root (.pi/agent/skills)
    link = sb / ".pi" / "agent" / "skills" / "symlink_standalone.md"
    link.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(target, link)

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    entry = next(e for e in idx.entries if "symlink_standalone.md" in e.entrypoint_path)
    assert entry.canonical_path == str(target.resolve())
    assert entry.is_file is True
    assert entry.content_hash is not None
    assert any(h.agent_id == "pi" for h in entry.hits)


def test_codex_directory_only_root_ignores_symlink_to_file(mock_home: Path) -> None:
    """Directory-only roots ignore file targets, regardless of frontmatter metadata/name.

    Coordinator reproduction: .codex/skills/document-link -> outside/document.md with valid
    frontmatter must NOT be discovered as Codex skill. Broken shortcuts remain diagnostic.
    """
    sb = mock_home.resolve()
    outside = sb / "outside"
    outside.mkdir(parents=True, exist_ok=True)
    doc_file = outside / "document.md"
    doc_file.write_text(
        """---
name: document_skill
description: Document skill.
---
# Content
""",
        encoding="utf-8",
    )

    codex_skills = sb / ".codex" / "skills"
    codex_skills.mkdir(parents=True, exist_ok=True)
    symlink_file = codex_skills / "document-link"
    os.symlink(doc_file, symlink_file)

    # Broken directory shortcut
    broken_shortcut = codex_skills / "broken-dir-link"
    os.symlink(outside / "nonexistent_dir", broken_shortcut)

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    codex_entries = [e for e in idx.entries if any(h.agent_id == "codex" for h in e.hits)]
    codex_paths = [e.entrypoint_path for e in codex_entries]

    # File symlink MUST be ignored
    assert not any("document-link" in p for p in codex_paths)

    # Broken shortcut is preserved as diagnostic
    assert any("broken-dir-link" in p for p in codex_paths)
    broken_entry = next(e for e in codex_entries if "broken-dir-link" in e.entrypoint_path)
    assert broken_entry.error_code == ERR_DANGLING_SYMLINK

    # Doctor report confirms broken shortcut is reported,
    # while ignored document-link causes no finding
    doc_rep = run_doctor(sb, index=idx, registry=reg)
    broken_findings = [f for f in doc_rep.findings if "broken-dir-link" in f.message]
    assert len(broken_findings) >= 1
    doc_findings = [f for f in doc_rep.findings if "document-link" in f.message]
    assert len(doc_findings) == 0


def test_pi_exact_skill_md_directory_discovery_and_case_sensitivity(mock_home: Path) -> None:
    """Pi requires exact SKILL.md for directories and symlink targets across filesystems.

    - Positive exact directory: .pi/agent/skills/exact/SKILL.md -> discovered.
    - Negative lowercase directory: .pi/agent/skills/lower/skill.md -> NOT discovered.
    - Negative dot directory: .pi/agent/skills/dot/.skill.md -> NOT discovered.
    - Positive exact symlink: .pi/agent/skills/sym_exact -> target with SKILL.md -> discovered.
    - Negative lowercase symlink: target with skill.md -> NOT discovered.
    - Root-level standalone: skill.md with description -> discovered (is_file=True).
    - Incidental root markdown: .pi/agent/skills/notes.md without description -> ignored.
    - Declared malformed SKILL: .pi/agent/skills/bad_decl/SKILL.md -> discovered with error.
    """
    sb = mock_home.resolve()
    pi_root = sb / ".pi" / "agent" / "skills"
    pi_root.mkdir(parents=True, exist_ok=True)

    # 1. Positive exact directory
    exact_dir = pi_root / "exact_dir"
    _make_skill(exact_dir, "exact_tool", "Exact tool")

    # 2. Negative lowercase directory
    lower_dir = pi_root / "lower_dir"
    lower_dir.mkdir(parents=True, exist_ok=True)
    (lower_dir / "skill.md").write_text(
        """---
name: lower_tool
description: Lower tool
---
""",
        encoding="utf-8",
    )

    # 3. Negative dot directory
    dot_dir = pi_root / "dot_dir"
    dot_dir.mkdir(parents=True, exist_ok=True)
    (dot_dir / ".skill.md").write_text(
        """---
name: dot_tool
description: Dot tool
---
""",
        encoding="utf-8",
    )

    # 4. Outside targets for symlinks
    outside = sb / "outside_pi"
    outside.mkdir(parents=True, exist_ok=True)
    out_exact = outside / "out_exact"
    _make_skill(out_exact, "sym_exact", "Sym exact")
    out_lower = outside / "out_lower"
    out_lower.mkdir(parents=True, exist_ok=True)
    (out_lower / "skill.md").write_text(
        """---
name: sym_lower
description: Sym lower
---
""",
        encoding="utf-8",
    )

    os.symlink(out_exact, pi_root / "link_exact")
    os.symlink(out_lower, pi_root / "link_lower")

    # 5. Root-level standalone skill.md with valid description
    (pi_root / "skill.md").write_text(
        """---
name: root_standalone
description: Root standalone Pi skill
---
""",
        encoding="utf-8",
    )

    # 6. Root-level incidental notes.md without description
    (pi_root / "notes.md").write_text("# Incidental notes\n", encoding="utf-8")

    # 7. Declared malformed SKILL.md inside directory
    bad_dir = pi_root / "bad_dir"
    bad_dir.mkdir(parents=True, exist_ok=True)
    (bad_dir / "SKILL.md").write_text("---\nname: [unclosed yaml\n---\n", encoding="utf-8")

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    pi_entries = [e for e in idx.entries if any(h.agent_id == "pi" for h in e.hits)]
    pi_paths = [e.entrypoint_path for e in pi_entries]

    # Positives
    assert any("exact_dir" in p for p in pi_paths)
    assert any("link_exact" in p for p in pi_paths)
    assert any("bad_dir" in p for p in pi_paths)

    # Negatives
    assert not any("lower_dir" in p for p in pi_paths)
    assert not any("dot_dir" in p for p in pi_paths)
    assert not any("link_lower" in p for p in pi_paths)
    assert not any("notes.md" in p for p in pi_paths)

    # Root standalone skill.md is discovered with is_file=True
    standalone_entry = next(e for e in pi_entries if e.entrypoint_path.endswith("/skill.md"))
    assert standalone_entry.is_file is True

    # Declared malformed SKILL.md remains doctor ERROR
    doc_rep = run_doctor(sb, index=idx, registry=reg)
    bad_finding = next(
        f for f in doc_rep.findings if "bad_dir" in f.message or "bad_dir" in (f.path or "")
    )
    assert bad_finding.severity is Severity.ERROR


def test_metadata_enum_validation() -> None:
    """Invalid metadata declarations for base or entry_format fail clearly with ValueError."""
    valid_raw = {
        "id": "test_root",
        "kind": "global",
        "path": ".test/skills",
        "scope": "user",
        "rank": 50,
        "rule_id": "test_rule",
        "evidence": "documented",
    }
    # Valid default
    root = _parse_root(valid_raw)
    assert root.base is RootBase.HOME
    assert root.entry_format is EntryFormat.DIRECTORY

    # Valid explicit
    root_explicit = _parse_root(
        {**valid_raw, "base": "xdg_config_home", "entry_format": "opencode_v2"}
    )
    assert root_explicit.base is RootBase.XDG_CONFIG_HOME
    assert root_explicit.entry_format is EntryFormat.OPENCODE_V2

    # Invalid base raises ValueError
    with pytest.raises(ValueError):
        _parse_root({**valid_raw, "base": "invalid_base"})

    # Invalid entry_format raises ValueError
    with pytest.raises(ValueError):
        _parse_root({**valid_raw, "entry_format": "invalid_format"})


def test_root_level_standalone_skill_md_naming_parity(mock_home: Path) -> None:
    """Discovery entry name and per-hit alias agree for root-level standalone SKILL.md.

    Cross-check parity across scan, why, diff, compare, snapshot_why, and snapshot_diff
    for OpenCode V2, Pi, and Antigravity standalone roots, while preserving directory bundles.
    """
    sb = mock_home.resolve()

    # 1. Native OpenCode V2 root SKILL.md
    oc_root = sb / ".config" / "opencode" / "skills"
    oc_root.mkdir(parents=True, exist_ok=True)
    (oc_root / "SKILL.md").write_text(
        "---\ndescription: OpenCode root skill.\n---\n# OpenCode Body\n",
        encoding="utf-8",
    )

    # 2. Pi root SKILL.md
    pi_root = sb / ".pi" / "agent" / "skills"
    pi_root.mkdir(parents=True, exist_ok=True)
    (pi_root / "SKILL.md").write_text(
        "---\nname: pi_skill\ndescription: Pi root skill.\n---\n# Pi Body\n",
        encoding="utf-8",
    )

    # 3. Antigravity standalone root SKILL.md
    ag_root = sb / ".gemini" / "config" / "skills"
    ag_root.mkdir(parents=True, exist_ok=True)
    (ag_root / "SKILL.md").write_text(
        "---\nname: ag_skill\ndescription: Antigravity root skill.\n---\n# Antigravity Body\n",
        encoding="utf-8",
    )

    # 4. Directory bundle controls: parent name must be preserved
    bundle_dir = oc_root / "bundle_tool"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "SKILL.md").write_text(
        "---\nname: bundle_tool\ndescription: Directory bundle.\n---\n# Bundle Body\n",
        encoding="utf-8",
    )
    skills_dir = oc_root / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    (skills_dir / "SKILL.md").write_text(
        "---\nname: skills_bundle\ndescription: Skills named bundle.\n---\n# Skills Body\n",
        encoding="utf-8",
    )

    # 5. External file reached by shortcut symlink
    outside = sb / "outside_lib"
    outside.mkdir(parents=True, exist_ok=True)
    ext_target = outside / "target.md"
    ext_target.write_text(
        "---\nname: target_skill\ndescription: External target.\n---\n# Ext Body\n",
        encoding="utf-8",
    )
    shortcut = pi_root / "shortcut.md"
    os.symlink(ext_target, shortcut)

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    # Standalone entries must have name == "SKILL"
    root_entries = [e for e in idx.entries if e.entrypoint_path.endswith("/SKILL.md") and e.is_file]
    assert len(root_entries) >= 1
    for entry in root_entries:
        assert entry.name == "SKILL"
        assert entry.is_file is True

    # Directory bundles preserve parent name
    bundle_entry = next(e for e in idx.entries if e.entrypoint_path.endswith("bundle_tool"))
    assert bundle_entry.name == "bundle_tool"
    assert bundle_entry.is_file is False

    skills_entry = next(e for e in idx.entries if e.entrypoint_path.endswith("/skills"))
    assert skills_entry.name == "skills"
    assert skills_entry.is_file is False

    # Shortcut retains its own alias
    shortcut_entry = next(e for e in idx.entries if "shortcut.md" in e.entrypoint_path)
    assert shortcut_entry.name == "shortcut"

    # Parity check: why for pi resolves SKILL
    res_pi = resolve_skill("pi_skill", "pi", cwd=sb, home=sb, index=idx, registry=reg)
    assert res_pi.found is True
    assert res_pi.candidates[0].installation.name == "SKILL"

    # Parity check: why for opencode resolves SKILL
    res_oc = resolve_skill("SKILL", "opencode", cwd=sb, home=sb, index=idx, registry=reg)
    assert res_oc.found is True
    assert res_oc.candidates[0].installation.name == "SKILL"

    # Parity check: diff accepts and finds SKILL
    diff_pi = build_diff_report("SKILL", sb, sb, index=idx, registry=reg)
    assert diff_pi.found is True
    assert diff_pi.skill_name == "SKILL"

    # Parity check: compare handles SKILL
    comp_rep = run_compare("opencode", "pi", cwd=sb, index=idx, registry=reg)
    sk_row = next((r for r in comp_rep.entries if r.name == "SKILL"), None)
    assert sk_row is not None

    # Parity check: scan lists SKILL
    res_scan = runner.invoke(app, ["scan", "--cwd", str(sb), "--json"])
    assert res_scan.exit_code == 0
    scan_json = json.loads(res_scan.stdout)
    scan_names = [s["name"] for s in scan_json["skills"]]
    assert "SKILL" in scan_names

    # Parity check: frozen session snapshot why and diff
    snapshot = capture_session(generation=1, home=sb, cwd=sb, registry=reg)
    snap_root_entry = next(
        e for e in snapshot.index.entries if e.entrypoint_path.endswith("/SKILL.md") and e.is_file
    )
    snap_key = canonical_key(snap_root_entry)

    snap_why = snapshot_why(snapshot, snap_key, "pi")
    assert snap_why.found is True
    assert snap_why.candidates[0].installation.name == "SKILL"

    snap_diff = snapshot_diff(snapshot, snap_key)
    assert snap_diff.found is True
    assert snap_diff.skill_name == "SKILL"


def test_opencode_v2_nested_symlink_directory_discovery(mock_home: Path) -> None:
    """OpenCode V2 discovers nested symlinked skill directories up to depth limit with
    cycle protection.
    """
    sb = mock_home.resolve()
    base = sb / ".config" / "opencode" / "skills"
    base.mkdir(parents=True, exist_ok=True)
    deep = base / "deep"
    deep.mkdir(parents=True, exist_ok=True)

    # Outside external targets
    store = sb / "store"
    store.mkdir(parents=True, exist_ok=True)

    # Valid depth 0 target
    (store / "top").mkdir(parents=True, exist_ok=True)
    (store / "top" / "SKILL.md").write_text(
        "---\nname: top_skill\ndescription: Top skill.\n---\n# Content\n", encoding="utf-8"
    )
    (base / "top_link").symlink_to(store / "top", target_is_directory=True)

    # Valid depth 1 target
    (store / "deeper").mkdir(parents=True, exist_ok=True)
    (store / "deeper" / "SKILL.md").write_text(
        "---\nname: deeper_skill\ndescription: Deeper skill.\n---\n# Content\n", encoding="utf-8"
    )
    (deep / "deep_link").symlink_to(store / "deeper", target_is_directory=True)

    # Negative control: wrong casing (skill.md lowercase)
    (store / "wrong_case").mkdir(parents=True, exist_ok=True)
    (store / "wrong_case" / "skill.md").write_text(
        "---\nname: wrong\ndescription: Lowercase.\n---\n# Content\n", encoding="utf-8"
    )
    (deep / "wrong_link").symlink_to(store / "wrong_case", target_is_directory=True)

    # Negative control: no SKILL.md declaration
    (store / "no_decl").mkdir(parents=True, exist_ok=True)
    (store / "no_decl" / "README.md").write_text("# Not a skill\n", encoding="utf-8")
    (deep / "no_decl_link").symlink_to(store / "no_decl", target_is_directory=True)

    # Broken symlink remains diagnostic
    broken_link = deep / "broken_link"
    os.symlink(store / "nonexistent", broken_link)

    # Symlink cycle remains diagnostic
    cycle_link = deep / "cycle_link"
    os.symlink(cycle_link, cycle_link)

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    entry_paths = [e.entrypoint_path for e in idx.entries]

    # Positive controls
    assert any("top_link" in p for p in entry_paths)
    assert any("deep_link" in p for p in entry_paths)

    top_entry = next(e for e in idx.entries if "top_link" in e.entrypoint_path)
    assert top_entry.is_file is False
    assert top_entry.canonical_path == str((store / "top").resolve())

    deep_entry = next(e for e in idx.entries if "deep_link" in e.entrypoint_path)
    assert deep_entry.is_file is False
    assert deep_entry.canonical_path == str((store / "deeper").resolve())

    # Negative controls: wrong-case and no-declaration must NOT be discovered
    assert not any("wrong_link" in p for p in entry_paths)
    assert not any("no_decl_link" in p for p in entry_paths)

    # Broken link diagnosed with ERR_DANGLING_SYMLINK
    assert any("broken_link" in p for p in entry_paths)
    broken_entry = next(e for e in idx.entries if "broken_link" in e.entrypoint_path)
    assert broken_entry.error_code == ERR_DANGLING_SYMLINK

    # Cycle diagnosed with ERR_SYMLINK_CYCLE
    assert any("cycle_link" in p for p in entry_paths)
    cycle_entry = next(e for e in idx.entries if "cycle_link" in e.entrypoint_path)
    assert cycle_entry.error_code == ERR_SYMLINK_CYCLE


def test_antigravity_builtin_root_format_compatibility(mock_home: Path) -> None:
    """Antigravity builtin root discovers both directory skills and standalone .md files."""
    sb = mock_home.resolve()
    builtin_root = sb / ".gemini" / "antigravity" / "builtin" / "skills"
    builtin_root.mkdir(parents=True, exist_ok=True)

    # Directory skill under builtin root
    _make_skill(builtin_root / "dir_tool", "dir_tool", "Builtin directory tool")

    # Standalone .md skill under builtin root
    (builtin_root / "standalone_tool.md").write_text(
        "---\nname: standalone_tool\ndescription: Builtin standalone tool.\n---\n# Content\n",
        encoding="utf-8",
    )

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    ag_builtin_hits = [
        e
        for e in idx.entries
        if any(h.agent_id == "antigravity" and h.root_id == "antigravity_builtin" for h in e.hits)
    ]
    assert len(ag_builtin_hits) == 2

    dir_hit = next(e for e in ag_builtin_hits if "dir_tool" in e.entrypoint_path)
    assert dir_hit.is_file is False

    file_hit = next(e for e in ag_builtin_hits if "standalone_tool.md" in e.entrypoint_path)
    assert file_hit.is_file is True


def test_root_hit_is_file_per_hit_provenance(mock_home: Path) -> None:
    """RootHit.is_file drives rule attribution and installation alias per hit."""
    sb = mock_home.resolve()
    ag_root = sb / ".gemini" / "config" / "skills"
    ag_root.mkdir(parents=True, exist_ok=True)

    # Direct file skill
    (ag_root / "direct_file.md").write_text(
        "---\nname: direct_file\ndescription: Direct file.\n---\n# Content\n",
        encoding="utf-8",
    )

    # Direct directory skill
    _make_skill(ag_root / "direct_dir", "direct_dir", "Direct directory")

    # Outside file reached by symlink
    outside = sb / "outside_store"
    outside.mkdir(parents=True, exist_ok=True)
    real_ext = outside / "real.md"
    real_ext.write_text(
        "---\nname: real_ext\ndescription: External real file.\n---\n# Content\n",
        encoding="utf-8",
    )
    os.symlink(real_ext, ag_root / "sym_link.md")

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    # Standalone file must report file_rule_id
    res_file = resolve_skill("direct_file", "antigravity", cwd=sb, home=sb, index=idx, registry=reg)
    assert res_file.found is True
    assert res_file.candidates[0].rule_id == "antigravity_standalone_md"
    assert res_file.candidates[0].installation.name == "direct_file"

    # Directory skill must report rule_id
    res_dir = resolve_skill("direct_dir", "antigravity", cwd=sb, home=sb, index=idx, registry=reg)
    assert res_dir.found is True
    assert res_dir.candidates[0].rule_id == "antigravity_global_skills"
    assert res_dir.candidates[0].installation.name == "direct_dir"

    # Symlinked file must report file_rule_id
    res_sym = resolve_skill("sym_link", "antigravity", cwd=sb, home=sb, index=idx, registry=reg)
    assert res_sym.found is True
    assert res_sym.candidates[0].rule_id == "antigravity_standalone_md"
    assert res_sym.candidates[0].installation.name == "sym_link"


def test_opencode_v2_shared_root_recursive_discovery(mock_home: Path) -> None:
    """OpenCode V2 applies root *.md and exact recursive SKILL.md to shared roots."""
    sb = mock_home.resolve()
    shared_root = sb / ".agents" / "skills"
    shared_root.mkdir(parents=True, exist_ok=True)

    # Root-level *.md under shared root
    (shared_root / "shared_root_tool.md").write_text(
        "---\nname: shared_root_tool\ndescription: Shared root tool.\n---\n# Content\n",
        encoding="utf-8",
    )

    # Nested exact SKILL.md under shared root
    nested_dir = shared_root / "subgroup" / "shared_nested_tool"
    nested_dir.mkdir(parents=True, exist_ok=True)
    (nested_dir / "SKILL.md").write_text(
        "---\nname: shared_nested_tool\ndescription: Shared nested tool.\n---\n# Content\n",
        encoding="utf-8",
    )

    # Incidental non-SKILL file in nested directory is NOT discovered
    (nested_dir / "notes.md").write_text("# Incidental notes\n", encoding="utf-8")

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    oc_entries = [
        e
        for e in idx.entries
        if any(h.agent_id == "opencode" and "shared" in h.root_id for h in e.hits)
    ]
    oc_paths = [e.entrypoint_path for e in oc_entries]

    assert any("shared_root_tool.md" in p for p in oc_paths)
    assert any("shared_nested_tool" in p for p in oc_paths)
    assert not any("notes.md" in p for p in oc_paths)

    # Resolve under opencode
    res_root = resolve_skill(
        "shared_root_tool", "opencode", cwd=sb, home=sb, index=idx, registry=reg
    )
    assert res_root.found is True
    assert res_root.candidates[0].installation.name == "shared_root_tool"

    res_nested = resolve_skill(
        "shared_nested_tool", "opencode", cwd=sb, home=sb, index=idx, registry=reg
    )
    assert res_nested.found is True
    assert res_nested.candidates[0].installation.name == "shared_nested_tool"


# --- Stage C Correction Regressions (Alias, Same-Path Precedence, Explicit Formats) ---


def test_same_path_same_agent_precedence_rankmax(mock_home: Path) -> None:
    """When multiple roots of the same agent reach the exact same entrypoint path,
    the highest-ranked rule represents that path regardless of root iteration order.
    """
    (mock_home / ".git").mkdir()
    sb = mock_home.resolve()
    paths.set_sandbox(sb)

    # DSH has both dsh_project (rank 95, rule "dsh_documented_project") and
    # dsh_user (rank 70, rule "dsh_documented_user") resolving to sb / ".dsh" / "skills"
    # when sb is a git project root.
    collision_dir = sb / ".dsh" / "skills" / "collision"
    _make_skill(collision_dir, "declared_name", "Same path collision skill")

    reg = load_registry()
    permuted_reg = {k: replace(a, roots=tuple(reversed(a.roots))) for k, a in reg.items()}

    idx1 = discover(home=sb, cwd=sb, registry=reg)
    idx2 = discover(home=sb, cwd=sb, registry=permuted_reg)

    res1 = resolve_skill("collision", "dsh", cwd=sb, home=sb, index=idx1, registry=reg)
    res2 = resolve_skill("collision", "dsh", cwd=sb, home=sb, index=idx2, registry=permuted_reg)

    assert res1.found is True
    assert res2.found is True
    assert len(res1.candidates) == 1
    assert len(res2.candidates) == 1

    assert res1.candidates[0].rank == 95
    assert res2.candidates[0].rank == 95
    assert res1.candidates[0].rule_id == "dsh_documented_project"
    assert res2.candidates[0].rule_id == "dsh_documented_project"


def test_entrypoint_alias_and_discovery_for_dot_md_named_directory(mock_home: Path) -> None:
    """Directory ending in .md and symlink-to-directory ending in .md keep directory name as alias,
    while supported standalone .md file keeps stem as alias, with cross-consumer agreement.
    """
    sb = mock_home.resolve()
    paths.set_sandbox(sb)

    # 1. Real directory ending in .md under Pi root (.pi/agent/skills)
    pi_root = sb / ".pi" / "agent" / "skills"
    real_md_dir = pi_root / "shortcut.md"
    _make_skill(real_md_dir, "shortcut.md", "Skill in .md-named dir")

    # 2. Symlink-to-directory ending in .md
    ext_dir = sb / "outside_store" / "external_skill"
    _make_skill(ext_dir, "symlink_dir.md", "External target skill")
    sym_dir_link = pi_root / "symlink_dir.md"
    os.symlink(ext_dir, sym_dir_link)

    # 3. Supported standalone .md file (opposite control)
    standalone_file = pi_root / "standalone.md"
    standalone_file.write_text(
        "---\nname: standalone_skill\ndescription: Standalone description.\n---\n# Body\n",
        encoding="utf-8",
    )

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    # Check discovered entries
    sc_entry = next(e for e in idx.entries if e.entrypoint_path.endswith("shortcut.md"))
    assert sc_entry.name == "shortcut.md"
    assert sc_entry.is_file is False

    sym_entry = next(e for e in idx.entries if e.entrypoint_path.endswith("symlink_dir.md"))
    assert sym_entry.name == "symlink_dir.md"
    assert sym_entry.is_file is False

    sa_entry = next(e for e in idx.entries if e.entrypoint_path.endswith("standalone.md"))
    assert sa_entry.name == "standalone"
    assert sa_entry.is_file is True

    # Check resolver, diff, compare, and scan agreement
    # 'shortcut.md' lookup:
    why_sc_full = resolve_skill("shortcut.md", "pi", cwd=sb, home=sb, index=idx, registry=reg)
    diff_sc_full = build_diff_report("shortcut.md", sb, sb, index=idx, registry=reg)
    assert why_sc_full.found is True
    assert diff_sc_full.found is True
    assert why_sc_full.candidates[0].installation.name == "shortcut.md"

    # 'shortcut' lookup (stem) must NOT find 'shortcut.md' (why and diff agreement):
    why_sc_stem = resolve_skill("shortcut", "pi", cwd=sb, home=sb, index=idx, registry=reg)
    diff_sc_stem = build_diff_report("shortcut", sb, sb, index=idx, registry=reg)
    assert why_sc_stem.found is False
    assert diff_sc_stem.found is False

    # 'symlink_dir.md' lookup:
    why_sym = resolve_skill("symlink_dir.md", "pi", cwd=sb, home=sb, index=idx, registry=reg)
    diff_sym = build_diff_report("symlink_dir.md", sb, sb, index=idx, registry=reg)
    assert why_sym.found is True
    assert diff_sym.found is True
    assert why_sym.candidates[0].installation.name == "symlink_dir.md"

    # 'standalone' lookup (stem of standalone.md file):
    why_sa = resolve_skill("standalone_skill", "pi", cwd=sb, home=sb, index=idx, registry=reg)
    diff_sa = build_diff_report("standalone", sb, sb, index=idx, registry=reg)
    assert why_sa.found is True
    assert diff_sa.found is True
    assert why_sa.candidates[0].installation.name == "standalone"

    # Compare handles shortcut.md (distinct agents to avoid Stage E single-agent rejection):
    comp_rep = run_compare("pi", "antigravity", cwd=sb, index=idx, registry=reg)
    comp_names = {r.name for r in comp_rep.entries}
    assert "shortcut.md" in comp_names
    assert "symlink_dir.md" in comp_names
    assert "standalone" in comp_names

    # Scan agreement:
    res_scan = runner.invoke(app, ["scan", "--cwd", str(sb), "--json"])
    assert res_scan.exit_code == 0
    scan_json = json.loads(res_scan.stdout)
    scan_names = {s["name"] for s in scan_json["skills"]}
    assert "shortcut.md" in scan_names
    assert "symlink_dir.md" in scan_names
    assert "standalone" in scan_names

    # Frozen session snapshot why and diff agreement:
    snapshot = capture_session(generation=1, home=sb, cwd=sb, registry=reg)
    snap_sc_entry = next(
        e for e in snapshot.index.entries if e.entrypoint_path.endswith("shortcut.md")
    )
    sc_key = canonical_key(snap_sc_entry)
    snap_why = snapshot_why(snapshot, sc_key, "pi")
    snap_diff = snapshot_diff(snapshot, sc_key)
    assert snap_why.found is True
    assert snap_diff.found is True
    assert snap_why.candidates[0].installation.name == "shortcut.md"


def test_all_shipped_agent_roots_declare_explicit_entry_format(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every root of the six affected agents explicitly declares entry_format in raw TOML.

    Total of 21 retained roots across claude (2), dsh (5), grok (3), qoder (3), omp (5),
    windsurf (3).
    Evaluated by root ID:
    - Documented native directory roots declare entry_format = "directory"
    - DSH native roots and the six unverified/non-native compatibility roots
      declare entry_format = "standalone_md"
    """
    import tomllib

    import skill_lens.registry

    monkeypatch.chdir(tmp_path)
    agents_dir = skill_lens.registry.REGISTRY_DIR
    expected_root_formats = {
        "claude": {
            "claude_personal": "directory",
            "claude_project": "directory",
        },
        "dsh": {
            "dsh_project": "standalone_md",
            "dsh_project_agents": "standalone_md",
            "dsh_profiles": "standalone_md",
            "dsh_user": "standalone_md",
            "dsh_shared_global": "standalone_md",
        },
        "grok": {
            "grok_global": "directory",
            "grok_bundled": "standalone_md",
            "grok_project": "standalone_md",
        },
        "qoder": {
            "qoder_global": "directory",
            "qoder_project": "directory",
            "qoder_project_agents": "standalone_md",
        },
        "omp": {
            "omp_project": "directory",
            "omp_project_agents": "directory",
            "omp_shared_global": "directory",
            "omp_managed": "directory",
            "omp_agent": "standalone_md",
        },
        "windsurf": {
            "windsurf_global": "directory",
            "windsurf_project": "directory",
            "windsurf_project_agents": "standalone_md",
        },
    }
    total_roots = 0
    for agent_name, root_map in expected_root_formats.items():
        toml_path = agents_dir / f"{agent_name}.toml"
        assert toml_path.is_file(), f"Missing agent file: {toml_path}"
        data = tomllib.loads(toml_path.read_text("utf-8"))
        roots = data.get("roots", [])
        assert len(roots) == len(root_map), (
            f"Agent {agent_name} expected {len(root_map)} roots, got {len(roots)}"
        )
        total_roots += len(roots)
        for root in roots:
            root_id = root.get("id")
            assert root_id in root_map, f"Unexpected root {root_id} for agent {agent_name}"
            assert "entry_format" in root, (
                f"Agent {agent_name} root {root_id} lacks explicit entry_format declaration"
            )
            expected_format = root_map[root_id]
            assert root["entry_format"] == expected_format, (
                f"Agent {agent_name} root {root_id} expected "
                f"entry_format='{expected_format}', got '{root.get('entry_format')}'"
            )
    assert total_roots == 21, (
        f"Expected 20 retained roots across 6 affected agents, found {total_roots}"
    )


def test_explicit_directory_format_supported_forms_and_standalone_omission(mock_home: Path) -> None:
    """Documented native directory roots discover valid directory skills and
    intentionally omit standalone .md files under declared entry_format = 'directory'.

    Omission assertions are strictly agent-specific so that shared roots (like .agents/skills)
    discovered by compatibility agents do not cause false test failures, while real native
    omission remains strictly verified.
    """
    (mock_home / ".git").mkdir()
    sb = mock_home.resolve()
    paths.set_sandbox(sb)

    # Documented native directory roots to test and their primary test roots under sb:
    agent_roots = [
        ("claude", sb / ".claude" / "skills"),
        ("grok", sb / ".grok" / "skills"),
        ("qoder", sb / ".qoder" / "skills"),
        ("omp", sb / ".omp" / "skills"),
        ("windsurf", sb / ".codeium" / "windsurf" / "skills"),
    ]

    for agent_id, root_dir in agent_roots:
        skill_name = f"{agent_id}_dir_skill"
        dir_skill = root_dir / skill_name
        _make_skill(dir_skill, skill_name, f"Valid {agent_id} directory skill")

        incidental_file = root_dir / f"{agent_id}_incidental.md"
        incidental_file.write_text(
            f"---\nname: {agent_id}_incidental\ndescription: Incidental file.\n---\n# Body\n",
            encoding="utf-8",
        )

    # Shared .agents/skills root with flatfile: omp native directory format omits it
    shared_root = sb / ".agents" / "skills"
    shared_root.mkdir(parents=True, exist_ok=True)
    omp_shared_dir = shared_root / "omp_shared_dir_skill"
    _make_skill(omp_shared_dir, "omp_shared_dir_skill", "Valid OMP shared directory skill")
    shared_flat = shared_root / "omp_shared_flat.md"
    shared_flat.write_text(
        "---\nname: omp_shared_flat\ndescription: Shared flat file.\n---\n# Body\n",
        encoding="utf-8",
    )

    # Also add an agent that DOES support standalone (Antigravity) as positive control
    ag_root = sb / ".gemini" / "config" / "skills"
    ag_standalone = ag_root / "ag_standalone.md"
    ag_standalone.parent.mkdir(parents=True, exist_ok=True)
    ag_standalone.write_text(
        "---\nname: ag_standalone\ndescription: Antigravity supported standalone.\n---\n# Body\n",
        encoding="utf-8",
    )

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    for agent_id, _root_dir in agent_roots:
        # Valid directory skill must be discovered
        dir_entry = next(
            (e for e in idx.entries if e.entrypoint_path.endswith(f"{agent_id}_dir_skill")),
            None,
        )
        assert dir_entry is not None, f"{agent_id} valid directory skill not discovered"
        assert dir_entry.is_file is False
        assert any(h.agent_id == agent_id for h in dir_entry.hits)
        res = resolve_skill(
            f"{agent_id}_dir_skill", agent_id, cwd=sb, home=sb, index=idx, registry=reg
        )
        assert res.found is True
        assert res.headline == HeadlineState.ACTIVE

        # Incidental standalone .md file must NOT be hit by the directory-only agent
        # (agent-specific check)
        incidental_entries = [
            e for e in idx.entries if e.entrypoint_path.endswith(f"{agent_id}_incidental.md")
        ]
        for entry in incidental_entries:
            assert not any(h.agent_id == agent_id for h in entry.hits), (
                f"{agent_id} incidental .md unexpectedly hit by {agent_id}"
            )
        res_incidental = resolve_skill(
            f"{agent_id}_incidental", agent_id, cwd=sb, home=sb, index=idx, registry=reg
        )
        # Deliberate Stage C assertion: incidental .md file is either not in the discovery index
        # at all (found is False) or, if indexed via another agent root, classified as UNSEARCHED
        # for this agent. In neither case is it active.
        assert res_incidental.found is False or res_incidental.headline == HeadlineState.UNSEARCHED

    # OMP native directory format on .agents/skills:
    # Directory skill is hit by omp
    omp_dir_entry = next(
        (e for e in idx.entries if e.entrypoint_path.endswith("omp_shared_dir_skill")),
        None,
    )
    assert omp_dir_entry is not None
    assert any(h.agent_id == "omp" for h in omp_dir_entry.hits)

    # Flat file in .agents/skills is NOT hit by omp, even if compatibility agents hit it!
    shared_flat_entry = next(
        (e for e in idx.entries if e.entrypoint_path.endswith("omp_shared_flat.md")),
        None,
    )
    assert shared_flat_entry is not None  # Hit by compatibility agents (grok/qoder/windsurf/dsh)
    assert not any(h.agent_id == "omp" for h in shared_flat_entry.hits), (
        "OMP native directory format unexpectedly hit flatfile in .agents/skills"
    )
    res_omp_flat = resolve_skill("omp_shared_flat", "omp", cwd=sb, home=sb, index=idx, registry=reg)
    assert res_omp_flat.headline == HeadlineState.UNSEARCHED
    assert res_omp_flat.candidates[0].rule_id == "omp_search_roots"

    # Positive control: Antigravity standalone file is discovered
    ag_entry = next(
        (e for e in idx.entries if e.entrypoint_path.endswith("ag_standalone.md")),
        None,
    )
    assert ag_entry is not None
    assert ag_entry.is_file is True


@pytest.mark.parametrize(
    (
        "agent_id",
        "root_id",
        "root_relpath",
        "is_recursive",
        "expected_id_policy",
        "expected_rule_id",
        "expected_rank",
    ),
    [
        (
            "grok",
            "grok_bundled",
            ".grok/bundled/skills",
            False,
            "frontmatter_name",
            "grok_bundled",
            30,
        ),
        (
            "grok",
            "grok_project",
            ".agents/skills",
            False,
            "frontmatter_name",
            "grok_project_shadow",
            90,
        ),
        (
            "qoder",
            "qoder_project_agents",
            ".agents/skills",
            False,
            "frontmatter_name",
            "qoder_project_shadow",
            65,
        ),
        (
            "omp",
            "omp_agent",
            ".omp/agent",
            False,
            "frontmatter_name",
            "omp_documented_managed_last",
            40,
        ),
        (
            "windsurf",
            "windsurf_project_agents",
            ".agents/skills",
            False,
            "hybrid",
            "windsurf_project_shadow",
            85,
        ),
        (
            "dsh",
            "dsh_profiles",
            ".dsh/profiles",
            True,
            "directory_name",
            "dsh_inferred_profiles",
            40,
        ),
    ],
)
def test_compatibility_roots_behavioral_positive_controls(
    mock_home: Path,
    agent_id: str,
    root_id: str,
    root_relpath: str,
    is_recursive: bool,
    expected_id_policy: str,
    expected_rule_id: str,
    expected_rank: int,
) -> None:
    """Parametrized behavioral positive controls for the six unverified/non-native
    compatibility roots:
    - grok_bundled (.grok/bundled/skills)
    - grok_project (.agents/skills)
    - qoder_project_agents (.agents/skills)
    - omp_agent (.omp/agent)
    - windsurf_project_agents (.agents/skills)
    - dsh_profiles (.dsh/profiles, nested skills container)

    Verifies:
    1. Valid directory skill discovered with is_file=False and hit for (agent_id, root_id).
    2. Valid flatfile skill (.md) discovered with is_file=True and hit for (agent_id, root_id).
       (Shared path discovery by another agent does not count.)
    3. Non-md negative control is omitted (no discovery / no hit).
    4. Actual why resolution resolves with declared vs alias appropriate to current agent policy.
    """
    (mock_home / ".git").mkdir(exist_ok=True)
    sb = mock_home.resolve()
    paths.set_sandbox(sb)

    if is_recursive:
        # For dsh_profiles plugin container: skills must reside in a nested skills directory
        container = sb / root_relpath / f"profile_{root_id}" / "skills"
    else:
        container = sb / root_relpath
    container.mkdir(parents=True, exist_ok=True)

    # 1. Valid directory skill
    dir_name_alias = f"dir_{root_id}"
    dir_fm_name = f"declared_fm_dir_{root_id}"
    dir_path = container / dir_name_alias
    _make_skill(dir_path, dir_fm_name, f"Valid {root_id} directory skill")

    # 2. Valid flatfile skill
    flat_name_alias = f"flat_{root_id}"
    flat_fm_name = f"declared_fm_flat_{root_id}"
    flat_file = container / f"{flat_name_alias}.md"
    flat_file.write_text(
        f"---\nname: {flat_fm_name}\ndescription: Valid {root_id} flat skill\n---\n# Body\n",
        encoding="utf-8",
    )

    # 3. Non-md negative control
    nonmd_file = container / f"negative_{root_id}.txt"
    nonmd_file.write_text("Incidental non-markdown file\n", encoding="utf-8")

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    # 1. Directory skill assertion
    dir_entry = next(
        (e for e in idx.entries if e.entrypoint_path.endswith(dir_name_alias)),
        None,
    )
    assert dir_entry is not None, f"Directory skill under {root_id} was not discovered"
    assert dir_entry.is_file is False
    assert any(h.agent_id == agent_id and h.root_id == root_id for h in dir_entry.hits), (
        f"RootHit for ({agent_id}, {root_id}) missing on directory skill; "
        f"other agent hit does not count"
    )

    # 2. Flatfile skill assertion (INTENDED MISSING-FLAT ASSERTION when mutated to directory)
    flat_entry = next(
        (e for e in idx.entries if e.entrypoint_path.endswith(f"{flat_name_alias}.md")),
        None,
    )
    assert flat_entry is not None, (
        f"Flatfile skill under {root_id} was not discovered (missing flatfile entry)"
    )
    assert flat_entry.is_file is True
    assert any(h.agent_id == agent_id and h.root_id == root_id for h in flat_entry.hits), (
        f"RootHit for ({agent_id}, {root_id}) missing on flatfile; other agent hit does not count"
    )

    # 3. Non-md negative control assertion
    nonmd_entry = next(
        (e for e in idx.entries if f"negative_{root_id}.txt" in e.entrypoint_path),
        None,
    )
    assert nonmd_entry is None, f"Non-md file under {root_id} was unexpectedly discovered as skill"

    # 4. Actual why resolution under agent identity policy
    if expected_id_policy == "directory_name":
        # Resolves by alias (stem / folder name)
        res_alias = resolve_skill(
            flat_name_alias, agent_id, cwd=sb, home=sb, index=idx, registry=reg
        )
        assert res_alias.found is True
        assert res_alias.headline == HeadlineState.ACTIVE
        assert any(
            c.rule_id == expected_rule_id and c.rank == expected_rank for c in res_alias.candidates
        )
        assert res_alias.candidates[0].installation.name == flat_name_alias

        # Declared frontmatter name does not resolve under directory_name policy
        res_fm = resolve_skill(flat_fm_name, agent_id, cwd=sb, home=sb, index=idx, registry=reg)
        assert res_fm.found is False

    elif expected_id_policy == "frontmatter_name":
        # Resolves by declared frontmatter name
        res_fm = resolve_skill(flat_fm_name, agent_id, cwd=sb, home=sb, index=idx, registry=reg)
        assert res_fm.found is True
        assert res_fm.headline == HeadlineState.ACTIVE
        assert any(
            c.rule_id == expected_rule_id and c.rank == expected_rank for c in res_fm.candidates
        )
        assert res_fm.candidates[0].installation.name == flat_name_alias
        assert res_fm.candidates[0].installation.frontmatter_name == flat_fm_name

        # Stem alias does not resolve under frontmatter_name policy when different
        res_alias = resolve_skill(
            flat_name_alias, agent_id, cwd=sb, home=sb, index=idx, registry=reg
        )
        assert res_alias.found is False

    elif expected_id_policy == "hybrid":
        # Resolves by both declared frontmatter name and alias
        res_fm = resolve_skill(flat_fm_name, agent_id, cwd=sb, home=sb, index=idx, registry=reg)
        assert res_fm.found is True
        assert res_fm.headline == HeadlineState.ACTIVE
        assert any(
            c.rule_id == expected_rule_id and c.rank == expected_rank for c in res_fm.candidates
        )
        assert res_fm.candidates[0].installation.name == flat_name_alias
        assert res_fm.candidates[0].installation.frontmatter_name == flat_fm_name

        res_alias = resolve_skill(
            flat_name_alias, agent_id, cwd=sb, home=sb, index=idx, registry=reg
        )
        assert res_alias.found is True
        assert res_alias.headline == HeadlineState.ACTIVE
        assert any(
            c.rule_id == expected_rule_id and c.rank == expected_rank for c in res_alias.candidates
        )
        assert res_alias.candidates[0].installation.name == flat_name_alias
        assert res_alias.candidates[0].installation.frontmatter_name == flat_fm_name


def test_dsh_standalone_md_supported_forms_and_omissions(mock_home: Path) -> None:
    """DSH native roots support directory bundles and flat files, omitting non-md and nested."""
    (mock_home / ".git").mkdir()
    sb = mock_home.resolve()
    paths.set_sandbox(sb)

    dsh_root = sb / ".dsh" / "skills"
    # 1. Supported directory bundle
    dsh_bundle = dsh_root / "dsh_dir_skill"
    _make_skill(dsh_bundle, "dsh_dir_skill", "Valid DSH directory skill")

    # 2. Supported flat Markdown file
    dsh_flat = dsh_root / "dsh_flat_skill.md"
    dsh_flat.write_text(
        "---\nname: dsh_flat_skill\ndescription: Valid DSH flat markdown skill.\n---\n# Body\n",
        encoding="utf-8",
    )

    # 3. Unsupported non-markdown file
    dsh_txt = dsh_root / "dsh_notes.txt"
    dsh_txt.write_text("Not a skill file", encoding="utf-8")

    # 4. Unsupported nested flat file under native root (nested recursive unsupported)
    nested_dir = dsh_root / "nested"
    nested_dir.mkdir(parents=True, exist_ok=True)
    nested_flat = nested_dir / "nested_flat.md"
    nested_flat.write_text(
        "---\nname: nested_flat\ndescription: Nested flat skill.\n---\n# Body\n",
        encoding="utf-8",
    )

    reg = load_registry()
    idx = discover(home=sb, cwd=sb, registry=reg)

    # Supported directory skill discovered
    entry_dir = next(
        (e for e in idx.entries if e.entrypoint_path.endswith("dsh_dir_skill")),
        None,
    )
    assert entry_dir is not None
    assert entry_dir.is_file is False
    res_dir = resolve_skill("dsh_dir_skill", "dsh", cwd=sb, home=sb, index=idx, registry=reg)
    assert res_dir.found is True

    # Supported flat skill discovered with filename stem shortcut
    entry_flat = next(
        (e for e in idx.entries if e.entrypoint_path.endswith("dsh_flat_skill.md")),
        None,
    )
    assert entry_flat is not None
    assert entry_flat.is_file is True
    assert entry_flat.name == "dsh_flat_skill"
    res_flat = resolve_skill("dsh_flat_skill", "dsh", cwd=sb, home=sb, index=idx, registry=reg)
    assert res_flat.found is True
    diff_flat = build_diff_report("dsh_flat_skill", sb, sb, index=idx, registry=reg)
    assert diff_flat.found is True

    # Unsupported non-md not discovered
    entry_txt = next((e for e in idx.entries if e.entrypoint_path.endswith("dsh_notes.txt")), None)
    assert entry_txt is None

    # Unsupported nested flat not discovered
    entry_nested = next(
        (e for e in idx.entries if e.entrypoint_path.endswith("nested_flat.md")),
        None,
    )
    assert entry_nested is None


def test_loader_fallback_entry_format_from_file_rule_id() -> None:
    """Loader falls back to standalone_md when file_rule_id is provided, else directory."""
    raw_with_rule = {
        "id": "fallback_root_rule",
        "kind": "global",
        "path": ".test/skills",
        "scope": "user",
        "rank": 50,
        "rule_id": "test_rule",
        "evidence": "empirical",
        "file_rule_id": "test_file_rule",
    }
    parsed_rule = _parse_root(raw_with_rule)
    assert parsed_rule.entry_format == EntryFormat.STANDALONE_MD

    raw_no_rule = {
        "id": "fallback_root_dir",
        "kind": "global",
        "path": ".test/skills",
        "scope": "user",
        "rank": 50,
        "rule_id": "test_rule",
        "evidence": "empirical",
    }
    parsed_dir = _parse_root(raw_no_rule)
    assert parsed_dir.entry_format == EntryFormat.DIRECTORY

    raw_explicit = {
        "id": "explicit_root",
        "kind": "global",
        "path": ".test/skills",
        "scope": "user",
        "rank": 50,
        "rule_id": "test_rule",
        "evidence": "empirical",
        "entry_format": "qualified_standalone_md",
    }
    parsed_explicit = _parse_root(raw_explicit)
    assert parsed_explicit.entry_format == EntryFormat.QUALIFIED_STANDALONE_MD
