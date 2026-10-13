"""Tests for filesystem discovery and agent-root tagging."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import skill_lens.core.discovery as discovery_module
from skill_lens.core.cancellation import CaptureCancelled
from skill_lens.core.discovery import (
    discover,
    find_walk_boundary,
    normalize_cwd,
)
from tests.fixtures.scenarios import build_scenario, teardown_scenario


def test_discover_finds_global_skill(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    index = discover(mock_home, mock_home)
    names = {entry.name for entry in index.entries}
    assert "deploy" in names


def test_project_root_is_not_nested(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    index = discover(mock_home, mock_home / "project")
    project_entries = [entry for entry in index.entries if "project" in entry.entrypoint_path]
    assert project_entries, "project skill not discovered"
    for entry in project_entries:
        for hit in entry.hits:
            if hit.root_id == "claude_project":
                assert hit.nested is False


def test_nested_monorepo_copy_is_flagged_nested(mock_home: Path) -> None:
    build_scenario("claude_nested_qualification", mock_home)
    index = discover(mock_home, mock_home / "project" / "apps" / "web")
    nested = [entry for entry in index.entries if "apps/web" in entry.entrypoint_path]
    assert nested, "nested copy not discovered"
    assert any(hit.nested for entry in nested for hit in entry.hits)


def test_symlink_farm_merges_to_one_entry(mock_home: Path) -> None:
    build_scenario("symlink_farm_multi_agent", mock_home)
    index = discover(mock_home, mock_home)
    shared = [entry for entry in index.entries if entry.name == "shared"]
    assert len(shared) == 1
    agents = {hit.agent_id for hit in shared[0].hits}
    assert {"claude", "pi", "qoder"} <= agents
    # All reaching entrypoint paths are retained for accurate counting.
    assert len(shared[0].entrypoint_paths) == 4


def test_relative_symlinks_still_merge_to_one_canonical_library(mock_home: Path) -> None:
    """Regression: an unnormalized canonical path splits one library into many.

    Real farms use relative targets (``x -> ../../../.agents/skills/x``). The
    walked path still contained ``..``, so every agent's link hashed to a
    different "canonical" string and the farm stopped being reported as one
    library with N entrypoints -- on a live machine this reported 502 global
    skills where only 84 distinct libraries exist.
    """
    from tests.fixtures.builders import make_skill, relative_symlink

    canonical = mock_home / ".agents" / "skills" / "shared"
    make_skill(canonical, "shared", "Shared capability.")
    for root in (".claude/skills", ".pi/agent/skills", ".qoder/skills"):
        relative_symlink(canonical, mock_home / root / "shared")

    index = discover(mock_home, mock_home)
    shared = [entry for entry in index.entries if entry.name == "shared"]
    assert len(shared) == 1, f"library split into {len(shared)} canonical skills"
    assert shared[0].canonical_path == str(canonical.resolve())
    assert len(shared[0].entrypoint_paths) == 4  # 3 links + the library itself


def test_symlink_entrypoint_count_counts_paths_not_hits(mock_home: Path) -> None:
    """Regression: the count must equal real symlinks, not (agent, root) hits.

    Several agent roots reach the same physical path, so counting hits
    inflated the number. Assert the reported count equals the symlinks on disk.
    """
    from skill_lens.core.scanner import build_scan_report

    build_scenario("symlink_farm_multi_agent", mock_home)
    report = build_scan_report(mock_home, mock_home)
    actual = sum(1 for path in mock_home.rglob("*") if path.is_symlink())
    assert report.summary.symlink_entrypoints == actual


def test_cycle_entry_has_error_code(mock_home: Path) -> None:
    build_scenario("symlink_cycle_guard", mock_home)
    index = discover(mock_home, mock_home)
    assert any(entry.error_code == "symlink_cycle" for entry in index.entries)


def test_system_skill_scope_is_system(mock_home: Path) -> None:
    build_scenario("system_container_traversal", mock_home)
    index = discover(mock_home, mock_home)
    imagegen = [entry for entry in index.entries if entry.name == "imagegen"]
    assert imagegen
    scopes = {hit.scope.value for hit in imagegen[0].hits}
    assert scopes == {"system"}
    assert imagegen[0].parse is not None
    assert imagegen[0].parse.status.value == "valid"


def test_tcc_blocked_skill_is_discovered_unreadable(mock_home: Path) -> None:
    build_scenario("tcc_permission_error", mock_home)
    try:
        index = discover(mock_home, mock_home)
        names = {entry.name for entry in index.entries}
        assert "ok" in names
        blocked = [entry for entry in index.entries if entry.name == "blocked"]
        assert blocked, "blocked skill dir was silently dropped"
        assert blocked[0].parse_status == "unreadable"
    finally:
        teardown_scenario("tcc_permission_error", mock_home)


def test_absolute_roots_skipped_under_sandbox(sandbox: Path) -> None:
    """``/etc/codex/skills`` must never be read during a sandboxed scan."""
    index = discover(sandbox, sandbox)
    for entry in index.entries:
        assert not entry.entrypoint_path.startswith("/etc/"), entry.entrypoint_path


def test_normalize_relative_cwd_stays_in_home(mock_home: Path) -> None:
    resolved = normalize_cwd(Path("."), mock_home)
    assert resolved == mock_home.resolve()


def test_find_walk_boundary_dotgit_dir(mock_home: Path) -> None:
    project = mock_home / "project"
    (project / ".git").mkdir(parents=True)
    assert find_walk_boundary(project, "git_root") == project


def test_find_walk_boundary_dotgit_file(mock_home: Path) -> None:
    build_scenario("worktree_dotgit_file", mock_home)
    project = mock_home / "project"
    assert find_walk_boundary(project, "git_root") == project


def test_find_walk_boundary_walks_up(mock_home: Path) -> None:
    project = mock_home / "project"
    deep = project / "apps" / "web"
    (project / ".git").mkdir(parents=True)
    deep.mkdir(parents=True)
    assert find_walk_boundary(deep, "git_root") == project


# --- Cancellation -----------------------------------------------------------


def test_discover_cancelled_immediately(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    with pytest.raises(CaptureCancelled):
        discover(mock_home, mock_home, cancelled=lambda: True)


def test_discover_cancelled_between_roots(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    visited_roots: list[str] = []

    orig_dirs_for_root = discovery_module._directories_for_root

    def tracking_dirs_for_root(*args: object, **kwargs: object) -> object:
        root = args[2]
        visited_roots.append(root.id)
        return orig_dirs_for_root(*args, **kwargs)  # type: ignore[arg-type]

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(discovery_module, "_directories_for_root", tracking_dirs_for_root)

        def cancel_after_first_root() -> bool:
            return len(visited_roots) >= 1

        with pytest.raises(CaptureCancelled):
            discover(mock_home, mock_home, cancelled=cancel_after_first_root)

    assert len(visited_roots) == 1, "Expected cancellation immediately after first root"


def test_discover_cancelled_during_recursive_listing(mock_home: Path) -> None:
    rec_root = mock_home / "plugins"
    (rec_root / "sub1" / "sub2").mkdir(parents=True)

    walk_steps = 0

    def cancel_on_second_walk_step() -> bool:
        nonlocal walk_steps
        walk_steps += 1
        return walk_steps >= 2

    with pytest.raises(CaptureCancelled):
        discovery_module._list_recursive_entries(rec_root, cancelled=cancel_on_second_walk_step)

    assert walk_steps >= 2, "Expected walk loop to be entered before cancellation"

    # Also prove discover() forwards cancelled into _list_recursive_entries
    codex_plugins = mock_home / ".codex" / ".tmp" / "plugins"
    (codex_plugins / "sub1" / "skills" / "nested_skill").mkdir(parents=True)

    rec_calls: list[object] = []
    orig_list_rec = discovery_module._list_recursive_entries

    def tracking_list_rec(
        base: Path, *, cancelled: object = None, **kwargs: Any
    ) -> list[tuple[Path, bool]]:
        assert cancelled is not None, "_list_recursive_entries must receive forwarded cancelled"
        rec_calls.append(cancelled)
        return orig_list_rec(base, cancelled=cancelled, **kwargs)  # type: ignore[arg-type]

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(discovery_module, "_list_recursive_entries", tracking_list_rec)

        def cancel_in_rec() -> bool:
            return len(rec_calls) >= 1

        with pytest.raises(CaptureCancelled):
            discover(mock_home, mock_home, cancelled=cancel_in_rec)

    assert len(rec_calls) >= 1, "Expected _list_recursive_entries to be called during discover"


def test_discover_cancelled_during_entry_listing(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    listed_dirs: list[Path] = []

    orig_list_entries = discovery_module._list_entries

    def tracking_list_entries(
        base: Path, *, cancelled: object = None, **kwargs: Any
    ) -> list[tuple[Path, bool]]:
        assert cancelled is not None, "_list_entries must receive forwarded cancelled"
        listed_dirs.append(base)
        return orig_list_entries(base, cancelled=cancelled, **kwargs)  # type: ignore[arg-type]

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(discovery_module, "_list_entries", tracking_list_entries)

        def cancel_in_list_entries() -> bool:
            return len(listed_dirs) >= 1

        with pytest.raises(CaptureCancelled):
            discover(mock_home, mock_home, cancelled=cancel_in_list_entries)

    assert len(listed_dirs) >= 1, "Expected entry listing to be entered before cancellation"


def test_discover_cancelled_during_hashing(mock_home: Path) -> None:
    build_scenario("symlink_farm_multi_agent", mock_home)
    parsed_skills: list[str] = []
    hash_calls: list[str] = []

    orig_parse_skill = discovery_module.parse_skill
    orig_hash_path = discovery_module.hash_path

    def tracking_parse_skill(p: Path) -> object:
        parsed_skills.append(p.name)
        return orig_parse_skill(p)

    def tracking_hash_path(p: Path, *, cancelled: object = None) -> str:
        assert cancelled is not None, "hash_path must receive forwarded cancelled predicate"
        hash_calls.append(p.name)
        return orig_hash_path(p, cancelled=cancelled)  # type: ignore[arg-type]

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(discovery_module, "parse_skill", tracking_parse_skill)
        mp.setattr(discovery_module, "hash_path", tracking_hash_path)

        def cancel_on_hash() -> bool:
            # Let parsing happen, then cancel when hashing starts
            return len(hash_calls) >= 1

        with pytest.raises(CaptureCancelled):
            discover(mock_home, mock_home, cancelled=cancel_on_hash)

    assert len(parsed_skills) >= 1, "Expected parse_skill to succeed before hashing"
    assert len(hash_calls) == 1, "Expected hash_path to be entered before cancellation"


def test_build_entry_cancellation_separation(mock_home: Path) -> None:
    """_build_entry lets CaptureCancelled from hash_path propagate.

    It must not catch it as OSError or swallow into content_hash=None.
    """
    from skill_lens.core import hasher as hasher_module
    from skill_lens.core.discovery import RootHit, _build_entry
    from tests.fixtures.builders import make_skill

    skill_dir = mock_home / ".claude" / "skills" / "sep_skill"
    make_skill(skill_dir, "sep_skill", "Test cancellation separation")

    hit = RootHit(
        agent_id="claude",
        root_id="claude_user",
        rank=100,
        rule_id="claude_user_skills",
        evidence="documented",
        scope="user",
        nested=False,
        file_rule_id=None,
        nested_rule_id=None,
        specificity=3,
        entrypoint_path=str(skill_dir),
    )

    hashing_entered = False
    orig_hash_file = hasher_module.hash_file

    def tracking_hash_file(p: Path, *, cancelled: object = None) -> str:
        nonlocal hashing_entered
        hashing_entered = True
        return orig_hash_file(p, cancelled=cancelled)  # type: ignore[arg-type]

    def cancel_during_hash() -> bool:
        return hashing_entered

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(hasher_module, "hash_file", tracking_hash_file)
        # Direct private helper check: must propagate CaptureCancelled rather than catching
        # and returning an entry with content_hash=None
        with pytest.raises(CaptureCancelled):
            _build_entry(skill_dir, False, hit, cancelled=cancel_during_hash)

    assert hashing_entered, "Expected hasher to be entered before cancellation"

    # Integration check: single-entry discover() also propagates CaptureCancelled rather than
    # returning an index with content_hash=None
    hashing_entered = False
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(hasher_module, "hash_file", tracking_hash_file)
        with pytest.raises(CaptureCancelled):
            discover(mock_home, mock_home, cancelled=cancel_during_hash)

    assert hashing_entered
