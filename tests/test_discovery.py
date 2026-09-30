"""Tests for filesystem discovery and agent-root tagging."""

from __future__ import annotations

from pathlib import Path

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
