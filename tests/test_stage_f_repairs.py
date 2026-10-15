"""Targeted verification tests for Stage F repairs (F15, F16, F11 agents rendering).

Covers:
- F15: Diff newline explanation and hunks preserving trailing newline information
- F16: Resolver causal winner carried to shadow reason, rule, and evidence
- F11: Render agents pinned output and Rich markup escaping
"""

from __future__ import annotations

import builtins
import io
import os
import shutil
from pathlib import Path

import pytest
from rich.console import Console

from skill_lens.core import paths
from skill_lens.core.diff import (
    NO_NEWLINE_MARKER,
    _count_changed,
    _count_chars,
    _fit_hunk,
    _hunks,
    _recount,
    _split_lines,
    build_diff_report,
)
from skill_lens.core.discovery import canonical_key, discover
from skill_lens.core.resolver import resolve_skill
from skill_lens.core.snapshot import capture_session, snapshot_diff, snapshot_why
from skill_lens.models.diff import DiffChange, DiffCopy, DiffFile, DiffHunk, DiffReport
from skill_lens.models.enums import Evidence, HeadlineState, Scope
from skill_lens.registry.loader import AgentDefinition, AgentRoot, load_registry
from skill_lens.render import render_agents, render_diff
from tests.fixtures.builders import make_skill
from tests.test_render_snapshots import EXPECTED_AGENTS_TABLE, EXPECTED_MARKUP_AGENT_TABLE

# =============================================================================
# F15: Diff final-newline preservation and hunk construction tests
# =============================================================================


def test_split_lines_preserves_final_newline_semantics() -> None:
    """_split_lines splits on \\n only, keeping newlines and treating lone CR as content."""
    assert _split_lines("") == []
    assert _split_lines("\n") == ["\n"]
    assert _split_lines("\n\n") == ["\n", "\n"]
    assert _split_lines("line") == ["line"]
    assert _split_lines("line\n") == ["line\n"]
    assert _split_lines("first\nsecond") == ["first\n", "second"]
    assert _split_lines("first\nsecond\n") == ["first\n", "second\n"]
    assert _split_lines("lone\rreturn\n") == ["lone\rreturn\n"]


def test_diff_explains_final_newline_removal(mock_home: Path) -> None:
    """When baseline has final newline and copy B lacks newline, hunks explain the removal."""
    home = mock_home.resolve()
    assert paths.home() == home
    assert paths.get_sandbox() == home

    make_skill(home / ".claude" / "skills" / "eol", "eol", "Personal copy.")
    (home / ".claude" / "skills" / "eol" / "data.txt").write_text("alpha\n", encoding="utf-8")

    make_skill(home / ".agents" / "skills" / "eol", "eol", "Shared copy.")
    (home / ".agents" / "skills" / "eol" / "data.txt").write_text("alpha", encoding="utf-8")

    report = build_diff_report("eol", home, home)
    assert report.found is True
    assert report.has_differences is True

    copy_b = next(c for c in report.copies if not c.is_baseline)
    data_diff = next(f for f in copy_b.files if f.path == "data.txt")
    assert data_diff.change is DiffChange.MODIFIED
    assert len(data_diff.hunks) == 1

    hunk = data_diff.hunks[0]
    assert hunk.old_count == 1
    assert hunk.new_count == 1
    assert hunk.lines == ("-alpha", "+alpha", NO_NEWLINE_MARKER)

    # Terminal rendering must display the marker
    console = Console(record=True, width=100, no_color=True, force_terminal=False)
    render_diff(report, console)
    rendered = console.export_text()
    assert r"\ No newline at end of file" in rendered


def test_diff_explains_final_newline_addition(mock_home: Path) -> None:
    """When baseline has no final newline and copy B has a newline, hunks explain the addition."""
    home = mock_home.resolve()
    assert paths.home() == home
    assert paths.get_sandbox() == home

    make_skill(home / ".claude" / "skills" / "eol", "eol", "Personal copy.")
    (home / ".claude" / "skills" / "eol" / "data.txt").write_text("alpha", encoding="utf-8")

    make_skill(home / ".agents" / "skills" / "eol", "eol", "Shared copy.")
    (home / ".agents" / "skills" / "eol" / "data.txt").write_text("alpha\n", encoding="utf-8")

    report = build_diff_report("eol", home, home)
    copy_b = next(c for c in report.copies if not c.is_baseline)
    data_diff = next(f for f in copy_b.files if f.path == "data.txt")

    hunk = data_diff.hunks[0]
    assert hunk.old_count == 1
    assert hunk.new_count == 1
    assert hunk.lines == ("-alpha", NO_NEWLINE_MARKER, "+alpha")


def test_diff_both_files_no_newline_with_diff() -> None:
    """When both files lack a final newline, both - and + changes report the marker."""
    old_lines = _split_lines("alpha")
    new_lines = _split_lines("beta")
    hunks = _hunks(old_lines, new_lines)
    assert len(hunks) == 1
    assert hunks[0].old_count == 1
    assert hunks[0].new_count == 1
    assert hunks[0].lines == ("-alpha", NO_NEWLINE_MARKER, "+beta", NO_NEWLINE_MARKER)


def test_diff_context_line_no_newline_at_eof() -> None:
    """When both files lack final newline and end on identical context, marker follows context."""
    old_lines = _split_lines("diff_old\nshared_eof")
    new_lines = _split_lines("diff_new\nshared_eof")
    hunks = _hunks(old_lines, new_lines)
    assert len(hunks) == 1
    assert hunks[0].lines == (
        "-diff_old",
        "+diff_new",
        " shared_eof",
        NO_NEWLINE_MARKER,
    )


def test_diff_empty_vs_single_newline() -> None:
    """Diffing empty file vs single newline file produces a 1-line hunk with no marker."""
    empty_lines = _split_lines("")
    nl_lines = _split_lines("\n")

    # Empty -> newline
    hunks_add = _hunks(empty_lines, nl_lines)
    assert len(hunks_add) == 1
    assert hunks_add[0].old_start == 0
    assert hunks_add[0].old_count == 0
    assert hunks_add[0].new_start == 1
    assert hunks_add[0].new_count == 1
    assert hunks_add[0].lines == ("+",)

    # Newline -> empty
    hunks_del = _hunks(nl_lines, empty_lines)
    assert len(hunks_del) == 1
    assert hunks_del[0].old_start == 1
    assert hunks_del[0].old_count == 1
    assert hunks_del[0].new_start == 0
    assert hunks_del[0].new_count == 0
    assert hunks_del[0].lines == ("-",)


def test_diff_empty_vs_non_empty_without_newline() -> None:
    """Diffing empty file vs non-empty file without newline carries the marker."""
    empty_lines = _split_lines("")
    text_lines = _split_lines("hello")

    hunks_add = _hunks(empty_lines, text_lines)
    assert len(hunks_add) == 1
    assert hunks_add[0].old_start == 0
    assert hunks_add[0].old_count == 0
    assert hunks_add[0].new_start == 1
    assert hunks_add[0].new_count == 1
    assert hunks_add[0].lines == ("+hello", NO_NEWLINE_MARKER)

    hunks_del = _hunks(text_lines, empty_lines)
    assert len(hunks_del) == 1
    assert hunks_del[0].old_start == 1
    assert hunks_del[0].old_count == 1
    assert hunks_del[0].new_start == 0
    assert hunks_del[0].new_count == 0
    assert hunks_del[0].lines == ("-hello", NO_NEWLINE_MARKER)


def test_diff_added_and_removed_files_without_newline(mock_home: Path) -> None:
    """Added or removed single-sided files without trailing newline carry the marker."""
    home = mock_home.resolve()
    assert paths.home() == home
    assert paths.get_sandbox() == home

    dir_a = home / ".claude" / "skills" / "onesided"
    make_skill(dir_a, "onesided", "Copy A.")
    (dir_a / "removed.txt").write_text("gone", encoding="utf-8")

    dir_b = home / ".agents" / "skills" / "onesided"
    make_skill(dir_b, "onesided", "Copy B.")
    (dir_b / "added.txt").write_text("new", encoding="utf-8")

    report = build_diff_report("onesided", home, home)
    copy_b = next(c for c in report.copies if not c.is_baseline)

    added_file = next(f for f in copy_b.files if f.path == "added.txt")
    assert added_file.change is DiffChange.ADDED
    assert added_file.hunks[0].lines == ("+new", NO_NEWLINE_MARKER)
    assert added_file.hunks[0].old_count == 0
    assert added_file.hunks[0].new_count == 1

    removed_file = next(f for f in copy_b.files if f.path == "removed.txt")
    assert removed_file.change is DiffChange.REMOVED
    assert removed_file.hunks[0].lines == ("-gone", NO_NEWLINE_MARKER)
    assert removed_file.hunks[0].old_count == 1
    assert removed_file.hunks[0].new_count == 0


def test_diff_crlf_lf_equivalence_preserved(mock_home: Path) -> None:
    """CRLF vs LF normalization produces identical fingerprints and no diff."""
    home = mock_home.resolve()
    assert paths.home() == home
    assert paths.get_sandbox() == home

    dir_a = home / ".claude" / "skills" / "crlf"
    make_skill(dir_a, "crlf", "Same description.", body="# Content\nLine 1\nLine 2\n")

    dir_b = home / ".agents" / "skills" / "crlf"
    make_skill(dir_b, "crlf", "Same description.", body="# Content\r\nLine 1\r\nLine 2\r\n")

    report = build_diff_report("crlf", home, home)
    copy_b = next(c for c in report.copies if not c.is_baseline)
    assert copy_b.files == ()
    assert report.has_differences is False


def test_diff_truncation_budget_rules() -> None:
    """Markers consume character budget but never changed lines or old/new line counts."""
    hunk = DiffHunk(
        old_start=1,
        old_count=1,
        new_start=1,
        new_count=1,
        lines=("-old_line", NO_NEWLINE_MARKER, "+new_line", NO_NEWLINE_MARKER),
    )

    # 1. Changed count does not include markers
    assert _count_changed([hunk]) == 2

    # 2. Character count includes markers + newlines
    expected_chars = sum(len(line) + 1 for line in hunk.lines)
    assert _count_chars([hunk]) == expected_chars

    # 3. Fit hunk with changed_budget = 1 keeps only the first change and its marker atomically
    lines, changed, chars = _fit_hunk(hunk, changed_budget=1, char_budget=10_000)
    assert changed == 1
    assert lines == ["-old_line", NO_NEWLINE_MARKER]
    assert chars == len("-old_line") + 1 + len(NO_NEWLINE_MARKER) + 1

    # 4. Fit hunk with char_budget too small for line + marker breaks before orphaning
    cost_first_pair = len("-old_line") + 1 + len(NO_NEWLINE_MARKER) + 1
    lines_tight, changed_tight, _ = _fit_hunk(
        hunk, changed_budget=10, char_budget=cost_first_pair - 1
    )
    assert lines_tight == []
    assert changed_tight == 0

    # 5. Recount on truncated lines: markers never increase line counts
    recounted = _recount(hunk, lines)
    assert recounted.old_count == 1
    assert recounted.new_count == 0
    assert recounted.lines == ("-old_line", NO_NEWLINE_MARKER)


def test_diff_captured_and_live_equivalence_for_final_newline(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Capture session proves frozen diff and why preserve newline hunks and causal winners."""
    home = mock_home.resolve()
    assert paths.home() == home
    assert paths.get_sandbox() == home

    # Setup skills with final-newline differences in BOTH directions:
    # Skill 'eol-both':
    # Copy A (baseline) in .claude/skills/eol-both:
    #   - nl_removed.txt: "alpha\n" (has newline in baseline)
    #   - nl_added.txt: "beta" (lacks newline in baseline)
    # Copy B in .agents/skills/eol-both:
    #   - nl_removed.txt: "alpha" (lacks newline in B -> newline removed)
    #   - nl_added.txt: "beta\n" (has newline in B -> newline added)
    dir_a = home / ".claude" / "skills" / "eol-both"
    make_skill(dir_a, "eol-both", "Baseline copy.")
    (dir_a / "nl_removed.txt").write_text("alpha\n", encoding="utf-8")
    (dir_a / "nl_added.txt").write_text("beta", encoding="utf-8")

    dir_b = home / ".agents" / "skills" / "eol-both"
    make_skill(dir_b, "eol-both", "Copy B.")
    (dir_b / "nl_removed.txt").write_text("alpha", encoding="utf-8")
    (dir_b / "nl_added.txt").write_text("beta\n", encoding="utf-8")

    # Setup causal why test skill with contrasting winner/loser evidence and nested_rule_id:
    # Agent 'synthetic_causal' with two roots:
    #   - Winner root: path '.high', rank 10, rule_id 'rule_causal_winner', evidence DOCUMENTED
    #   - Loser root: path '.low', rank 1, rule_id 'rule_causal_loser',
    #     nested_rule_id 'loser_nested_rule', evidence EMPIRICAL
    s_high = home / ".high" / "causal-skill"
    make_skill(s_high, "causal-skill", "High copy")
    s_low = home / ".low" / "causal-skill"
    make_skill(s_low, "causal-skill", "Low copy")

    root_high = AgentRoot(
        id="high",
        kind="user",
        path=".high",
        scope=Scope.USER,
        rank=10,
        rule_id="rule_causal_winner",
        evidence=Evidence.DOCUMENTED,
    )
    root_low = AgentRoot(
        id="low",
        kind="user",
        path=".low",
        scope=Scope.USER,
        rank=1,
        rule_id="rule_causal_loser",
        nested_rule_id="loser_nested_rule",
        evidence=Evidence.EMPIRICAL,
    )
    agent = AgentDefinition(
        id="synthetic_causal",
        name="Synthetic Causal",
        identity_source="test",
        collision_policy="precedence",
        policy_evidence=Evidence.DOCUMENTED,
        coexist_policy="shadow",
        walk_boundary="project_root",
        unsearched_rule_id="unsearched",
        roots=(root_high, root_low),
    )
    registry = dict(load_registry())
    registry["synthetic_causal"] = agent

    # 1. Pre-capture live equivalence:
    live_diff = build_diff_report("eol-both", home, home, registry=registry)
    assert live_diff.has_differences is True
    copy_b = next(c for c in live_diff.copies if not c.is_baseline)
    diff_removed = next(f for f in copy_b.files if f.path == "nl_removed.txt")
    diff_added = next(f for f in copy_b.files if f.path == "nl_added.txt")
    assert diff_removed.hunks[0].lines == ("-alpha", "+alpha", NO_NEWLINE_MARKER)
    assert diff_added.hunks[0].lines == ("-beta", NO_NEWLINE_MARKER, "+beta")

    live_why = resolve_skill("causal-skill", "synthetic_causal", home, home, registry=registry)
    assert len(live_why.candidates) == 2
    live_winner = next(c for c in live_why.candidates if c.state is HeadlineState.ACTIVE)
    live_shadowed = next(c for c in live_why.candidates if c.state is HeadlineState.SHADOWED)
    assert live_winner.rule_id == "rule_causal_winner"
    assert live_shadowed.rule_id == "rule_causal_winner"
    assert live_shadowed.evidence is Evidence.DOCUMENTED
    assert "~/.high" in live_shadowed.reason

    # 2. Capture session
    snapshot = capture_session(generation=1, home=home, cwd=home, registry=registry)

    entry_diff = next(e for e in snapshot.index.entries if e.name == "eol-both")
    key_diff = canonical_key(entry_diff)

    entry_why = next(e for e in snapshot.index.entries if e.name == "causal-skill")
    key_why = canonical_key(entry_why)

    # 3. Post-capture disk change / deletion:
    shutil.rmtree(dir_a)
    shutil.rmtree(dir_b)
    shutil.rmtree(s_high)
    shutil.rmtree(s_low)

    # 4. Appropriate filesystem/environment-read tripwires during frozen calls
    def forbid_fs(*args: object, **kwargs: object) -> object:
        raise AssertionError("Forbidden disk read invoked during frozen snapshot operation")

    with monkeypatch.context() as mp:
        mp.setattr(Path, "read_bytes", forbid_fs)
        mp.setattr(Path, "read_text", forbid_fs)
        mp.setattr(Path, "open", forbid_fs)
        mp.setattr(builtins, "open", forbid_fs)
        mp.setattr(io, "open", forbid_fs)
        mp.setattr(os, "open", forbid_fs)
        mp.setattr(os, "scandir", forbid_fs)
        mp.setattr(os, "walk", forbid_fs)
        mp.setattr(os, "listdir", forbid_fs)
        mp.setattr("skill_lens.core.hasher.iter_files", forbid_fs)

        frozen_diff = snapshot_diff(snapshot, key_diff)
        frozen_why = snapshot_why(snapshot, key_why, "synthetic_causal")

    # Verify JSON preservation and parity
    assert frozen_diff.to_dict() == live_diff.to_dict()
    assert frozen_why.to_dict() == live_why.to_dict()

    # Verify frozen snapshot_why preserves causal winner rule, evidence, and reason
    frozen_shadowed = next(c for c in frozen_why.candidates if c.state is HeadlineState.SHADOWED)
    assert frozen_shadowed.rule_id == "rule_causal_winner"
    assert frozen_shadowed.evidence is Evidence.DOCUMENTED
    assert "~/.high" in frozen_shadowed.reason

    # 5. Visible terminal explanation from actual adapter report outside tripwires
    console = Console(record=True, width=100, no_color=True, force_terminal=False)
    render_diff(frozen_diff, console)
    rendered = console.export_text()
    assert r"\ No newline at end of file" in rendered
    assert "-alpha" in rendered
    assert "+beta" in rendered


def test_diff_json_schema_round_trip_with_marker() -> None:
    """Diff models with markers round-trip through to_dict and from_dict unchanged."""
    hunk = DiffHunk(
        old_start=1,
        old_count=1,
        new_start=1,
        new_count=1,
        lines=("-alpha", NO_NEWLINE_MARKER, "+beta", NO_NEWLINE_MARKER),
    )
    diff_file = DiffFile(path="test.txt", change=DiffChange.MODIFIED, hunks=(hunk,))
    copy = DiffCopy(
        path="/home/dev/.agents/skills/s",
        scope=Scope.USER,
        parse_status="valid",
        is_valid=True,
        is_readable=True,
        files=(diff_file,),
    )
    report = DiffReport(
        skill_name="s",
        home="/home/dev",
        cwd="/home/dev",
        found=True,
        copies=(copy,),
    )
    d = report.to_dict()
    reconstructed = DiffReport.from_dict(d)
    assert reconstructed.to_dict() == d
    # Ensure public keys are preserved
    assert set(d.keys()) == {
        "skill_name",
        "home",
        "cwd",
        "found",
        "baseline_path",
        "copies",
        "truncated",
        "omitted_chars",
        "notes",
    }


# =============================================================================
# F16: Resolver causal winner tests
# =============================================================================


def test_nested_precedence_winner_explains_shadow(mock_home: Path) -> None:
    """F16 reproduction: winning nested copy carries its causal rule/reason into shadows."""
    home = mock_home.resolve()
    assert paths.home() == home
    assert paths.get_sandbox() == home

    proj = (home / "project").resolve()
    cwd = (proj / "sub").resolve()
    cwd.mkdir(parents=True)
    (proj / ".git").mkdir()

    # Nested project copy: project/sub/.skills/my_skill
    nested_skill = cwd / ".skills" / "my_skill"
    nested_skill.mkdir(parents=True)
    (nested_skill / "SKILL.md").write_text(
        "---\nname: my_skill\ndescription: nested\n---\n", encoding="utf-8"
    )

    # Global user copy: home/.skills/my_skill
    global_skill = home / ".skills" / "my_skill"
    global_skill.mkdir(parents=True)
    (global_skill / "SKILL.md").write_text(
        "---\nname: my_skill\ndescription: global\n---\n", encoding="utf-8"
    )

    root_nested = AgentRoot(
        id="synthetic_nested",
        kind="project",
        path=".skills",
        scope=Scope.PROJECT,
        rank=10,
        rule_id="synthetic_nested_wins",
        evidence=Evidence.DOCUMENTED,
    )
    root_global = AgentRoot(
        id="synthetic_global",
        kind="user",
        path=".skills",
        scope=Scope.USER,
        rank=1,
        rule_id="synthetic_losing_root",
        nested_rule_id="losing_nested_rule",
        evidence=Evidence.EMPIRICAL,
    )
    agent = AgentDefinition(
        id="synthetic",
        name="Synthetic",
        identity_source="test",
        collision_policy="precedence",
        policy_evidence=Evidence.DOCUMENTED,
        coexist_policy="shadow",
        walk_boundary="project_root",
        unsearched_rule_id="unsearched",
        roots=(root_nested, root_global),
    )
    registry = {"synthetic": agent}

    report = resolve_skill("my_skill", "synthetic", cwd, home, registry=registry)
    assert len(report.candidates) == 2

    nested_cand = next(c for c in report.candidates if c.installation.scope is Scope.PROJECT)
    assert nested_cand.state is HeadlineState.COEXISTS
    assert nested_cand.rule_id == "synthetic_nested_wins"

    shadowed_cand = next(c for c in report.candidates if c.installation.scope is Scope.USER)
    assert shadowed_cand.state is HeadlineState.SHADOWED
    # MUST cite the winning copy's rule and evidence, not the losing root's
    assert shadowed_cand.rule_id == "synthetic_nested_wins"
    assert shadowed_cand.evidence == Evidence.DOCUMENTED
    assert "project root .skills" in shadowed_cand.reason


def test_ambiguous_tie_does_not_fabricate_winner(mock_home: Path) -> None:
    """When candidates tie in rank and precedence is ambiguous, no winner is fabricated."""
    home = mock_home.resolve()
    assert paths.home() == home
    assert paths.get_sandbox() == home
    cwd = home

    s1 = home / ".r1" / "skill"
    s1.mkdir(parents=True)
    (s1 / "SKILL.md").write_text("---\nname: skill\ndescription: A\n---\n", encoding="utf-8")

    s2 = home / ".r2" / "skill"
    s2.mkdir(parents=True)
    (s2 / "SKILL.md").write_text("---\nname: skill\ndescription: B\n---\n", encoding="utf-8")

    r1 = AgentRoot(
        id="r1",
        kind="user",
        path=".r1",
        scope=Scope.USER,
        rank=5,
        rule_id="r1",
        evidence=Evidence.DOCUMENTED,
    )
    r2 = AgentRoot(
        id="r2",
        kind="user",
        path=".r2",
        scope=Scope.USER,
        rank=5,
        rule_id="r2",
        evidence=Evidence.DOCUMENTED,
    )
    agent = AgentDefinition(
        id="syn_tie",
        name="SynTie",
        identity_source="test",
        collision_policy="undocumented",
        policy_evidence=Evidence.INFERRED,
        coexist_policy="shadow",
        walk_boundary="project_root",
        unsearched_rule_id="unsearched",
        ambiguous_rule_id="ambiguous_tie_rule",
        roots=(r1, r2),
    )
    report = resolve_skill("skill", "syn_tie", cwd, home, registry={"syn_tie": agent})
    assert report.headline is HeadlineState.AMBIGUOUS
    for c in report.candidates:
        assert c.state is HeadlineState.AMBIGUOUS
        assert c.rule_id == "ambiguous_tie_rule"


def test_merged_policy_does_not_fabricate_winner(mock_home: Path) -> None:
    """When coexist_policy is 'merge', all candidates coexist and no winner is fabricated."""
    home = mock_home.resolve()
    assert paths.home() == home
    assert paths.get_sandbox() == home
    cwd = home

    s1 = home / ".m1" / "skill"
    s1.mkdir(parents=True)
    (s1 / "SKILL.md").write_text("---\nname: skill\ndescription: A\n---\n", encoding="utf-8")

    s2 = home / ".m2" / "skill"
    s2.mkdir(parents=True)
    (s2 / "SKILL.md").write_text("---\nname: skill\ndescription: B\n---\n", encoding="utf-8")

    r1 = AgentRoot(
        id="m1",
        kind="user",
        path=".m1",
        scope=Scope.USER,
        rank=10,
        rule_id="m1_rule",
        evidence=Evidence.DOCUMENTED,
    )
    r2 = AgentRoot(
        id="m2",
        kind="user",
        path=".m2",
        scope=Scope.USER,
        rank=1,
        rule_id="m2_rule",
        evidence=Evidence.DOCUMENTED,
    )
    agent = AgentDefinition(
        id="syn_merge",
        name="SynMerge",
        identity_source="test",
        collision_policy="merge",
        policy_evidence=Evidence.DOCUMENTED,
        coexist_policy="merge",
        walk_boundary="project_root",
        unsearched_rule_id="unsearched",
        roots=(r1, r2),
    )
    report = resolve_skill("skill", "syn_merge", cwd, home, registry={"syn_merge": agent})
    assert report.headline is HeadlineState.COEXISTS
    states = {c.state for c in report.candidates}
    assert HeadlineState.SHADOWED not in states
    coexists_cand = next(c for c in report.candidates if c.state is HeadlineState.COEXISTS)
    assert "merges all roots" in coexists_cand.reason


def test_opencode_specificity_tiebreaker_carries_causal_winner(mock_home: Path) -> None:
    """OpenCode specificity tie-breaker carries the higher-specificity causal winner."""
    home = mock_home.resolve()
    assert paths.home() == home
    assert paths.get_sandbox() == home

    proj = (home / "project").resolve()
    cwd = (proj / "deep" / "nested").resolve()
    cwd.mkdir(parents=True)
    (proj / ".git").mkdir()

    # Two copies in project roots with same rank but different directory depth
    s_deep = cwd / ".skills" / "spec_test"
    s_deep.mkdir(parents=True)
    (s_deep / "SKILL.md").write_text(
        "---\nname: spec_test\ndescription: deep\n---\n", encoding="utf-8"
    )

    s_root = proj / ".skills" / "spec_test"
    s_root.mkdir(parents=True)
    (s_root / "SKILL.md").write_text(
        "---\nname: spec_test\ndescription: root\n---\n", encoding="utf-8"
    )

    r_proj = AgentRoot(
        id="oc_proj",
        kind="project",
        path=".skills",
        scope=Scope.PROJECT,
        rank=5,
        rule_id="opencode_proj_rule",
        evidence=Evidence.DOCUMENTED,
    )
    agent = AgentDefinition(
        id="opencode",
        name="OpenCode",
        identity_source="test",
        collision_policy="shadow",
        policy_evidence=Evidence.DOCUMENTED,
        coexist_policy="shadow",
        walk_boundary="project_root",
        unsearched_rule_id="unsearched",
        roots=(r_proj,),
    )
    report = resolve_skill("spec_test", "opencode", cwd, home, registry={"opencode": agent})
    assert len(report.candidates) == 2
    active = next(c for c in report.candidates if c.state is HeadlineState.ACTIVE)
    shadowed = next(c for c in report.candidates if c.state is HeadlineState.SHADOWED)
    assert active.installation.canonical_path.endswith("deep/nested/.skills/spec_test")
    assert shadowed.rule_id == "opencode_proj_rule"


def test_disabled_high_ranked_candidate_cannot_be_causal_winner(mock_home: Path) -> None:
    """A disabled high-ranked candidate cannot win or suppress a lower-ranked valid candidate."""
    home = mock_home.resolve()
    assert paths.home() == home
    assert paths.get_sandbox() == home
    cwd = home

    s_high = home / ".high" / "myskill"
    make_skill(s_high, "myskill", "High copy")

    s_low = home / ".low" / "myskill"
    make_skill(s_low, "myskill", "Low copy")

    agent = AgentDefinition(
        id="syn_disabled",
        name="SynDisabled",
        identity_source="test",
        collision_policy="precedence",
        policy_evidence=Evidence.DOCUMENTED,
        coexist_policy="shadow",
        walk_boundary="project_root",
        unsearched_rule_id="unsearched",
        roots=(
            AgentRoot(
                id="high",
                kind="user",
                path=".high",
                scope=Scope.USER,
                rank=10,
                rule_id="high_rule",
                evidence=Evidence.DOCUMENTED,
            ),
            AgentRoot(
                id="low",
                kind="user",
                path=".low",
                scope=Scope.USER,
                rank=1,
                rule_id="low_rule",
                evidence=Evidence.DOCUMENTED,
            ),
        ),
    )
    registry = {"syn_disabled": agent}
    index = discover(home, home, registry)
    disabled_overrides = frozenset({str(s_high.resolve())})

    report = resolve_skill(
        "myskill",
        "syn_disabled",
        cwd,
        home,
        index=index,
        registry=registry,
        disabled_overrides=disabled_overrides,
    )
    assert len(report.candidates) == 2
    high_cand = next(
        c for c in report.candidates if c.installation.canonical_path.endswith(".high/myskill")
    )
    low_cand = next(
        c for c in report.candidates if c.installation.canonical_path.endswith(".low/myskill")
    )
    assert high_cand.state is HeadlineState.DISABLED
    assert low_cand.state is HeadlineState.ACTIVE


def test_invalid_high_ranked_candidate_cannot_be_causal_winner(mock_home: Path) -> None:
    """An invalid frontmatter candidate cannot be the causal winner or suppress valid copies."""
    home = mock_home.resolve()
    assert paths.home() == home
    assert paths.get_sandbox() == home
    cwd = home

    # Invalid copy in higher-rank root
    s_high = home / ".high" / "broken"
    s_high.mkdir(parents=True)
    (s_high / "SKILL.md").write_text("---\nname: [invalid\n---\n", encoding="utf-8")

    # Valid copy in lower-rank root
    s_low = home / ".low" / "broken"
    make_skill(s_low, "broken", "Valid description")

    r_high = AgentRoot(
        id="high",
        kind="user",
        path=".high",
        scope=Scope.USER,
        rank=10,
        rule_id="high_rule",
        evidence=Evidence.DOCUMENTED,
    )
    r_low = AgentRoot(
        id="low",
        kind="user",
        path=".low",
        scope=Scope.USER,
        rank=1,
        rule_id="low_rule",
        evidence=Evidence.DOCUMENTED,
    )
    agent = AgentDefinition(
        id="syn_validity",
        name="SynValidity",
        identity_source="test",
        collision_policy="precedence",
        policy_evidence=Evidence.DOCUMENTED,
        coexist_policy="shadow",
        walk_boundary="project_root",
        unsearched_rule_id="unsearched",
        roots=(r_high, r_low),
    )
    report = resolve_skill("broken", "syn_validity", cwd, home, registry={"syn_validity": agent})
    low_cand = next(
        c for c in report.candidates if c.installation.canonical_path.endswith(".low/broken")
    )
    high_cand = next(
        c for c in report.candidates if c.installation.canonical_path.endswith(".high/broken")
    )
    assert low_cand.state is HeadlineState.ACTIVE
    assert high_cand.state is HeadlineState.INVALID


# =============================================================================
# F11: Agents rendering tests
# =============================================================================


def test_render_agents_pins_real_registry_output(mock_home: Path) -> None:
    """render_agents at width 100 outputs the pinned full literal table for all known agents."""
    agents = list(load_registry().values())
    console = Console(record=True, width=100, no_color=True, force_terminal=False, highlight=False)
    render_agents(agents, console)
    output = console.export_text()
    assert output == EXPECTED_AGENTS_TABLE


def test_render_agents_markup_escaping() -> None:
    """Unusual agent names, IDs, and collision policies containing Rich markup stay literal."""
    markup_agent = AgentDefinition(
        id="[evil_id]",
        name="[bold red]Evil Agent[/]",
        identity_source="test",
        collision_policy="[green]Custom Policy[/]",
        policy_evidence=Evidence.DOCUMENTED,
        coexist_policy="shadow",
        walk_boundary="project_root",
        unsearched_rule_id="unsearched",
    )
    console = Console(record=True, width=100, no_color=True, force_terminal=False, highlight=False)
    render_agents([markup_agent], console)
    output = console.export_text()
    assert output == EXPECTED_MARKUP_AGENT_TABLE
