"""Structural checks for the golden fixture scenarios and acceptance farm.

These tests assert the *shape* of every fixture so Phase 1/2 have a stable,
verified foundation. They also validate the hand-written golden JSON files.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from tests.fixtures import farm
from tests.fixtures.scenarios import SCENARIO_NAMES, build_scenario, teardown_scenario

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"


def _identity(entry, home: Path) -> tuple[str, Path]:
    """The (name, home-relative canonical path) key of a discovered entry."""
    target = entry.canonical_path or entry.entrypoint_path
    return (entry.name, Path(target).relative_to(home))


@pytest.mark.parametrize("name", SCENARIO_NAMES)
def test_scenario_builds_without_error(name: str, mock_home: Path) -> None:
    build_scenario(name, mock_home)
    teardown_scenario(name, mock_home)
    assert any(mock_home.iterdir())


@pytest.mark.parametrize("name", SCENARIO_NAMES)
def test_scenario_never_escapes_mock_home(name: str, mock_home: Path) -> None:
    build_scenario(name, mock_home)
    teardown_scenario(name, mock_home)
    for path in mock_home.rglob("*"):
        assert str(path).startswith(str(mock_home))


def test_all_scenarios_present() -> None:
    assert len(SCENARIO_NAMES) == 13
    # ``diff_*.json`` goldens pin the Phase 3 diff contract and are keyed by the
    # scenario they are built on, so they are not scenario goldens themselves.
    golden = {p.stem for p in GOLDEN_DIR.glob("*.json") if not p.stem.startswith("diff_")}
    assert golden == set(SCENARIO_NAMES)


def test_every_diff_golden_names_a_real_scenario() -> None:
    """A ``diff_<scenario>.json`` golden must be built on a scenario that exists.

    Otherwise the golden would pin a fixture nobody can rebuild, and the diff it
    documents could drift away from the tree it claims to describe.
    """
    goldens = sorted(GOLDEN_DIR.glob("diff_*.json"))
    assert goldens, "no diff golden found"
    for path in goldens:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["scenario"] in SCENARIO_NAMES, path.name
        assert data["schema_version"] == 1, path.name
        assert "diff" in data, path.name
        assert path.stem == f"diff_{data['scenario']}", path.name


@pytest.mark.parametrize("name", SCENARIO_NAMES)
def test_golden_file_is_valid_and_named(name: str) -> None:
    data = json.loads((GOLDEN_DIR / f"{name}.json").read_text(encoding="utf-8"))
    assert data["scenario"] == name
    assert data["schema_version"] == 1
    assert "installations" in data and "resolutions" in data


@pytest.mark.parametrize("name", SCENARIO_NAMES)
def test_golden_installations_match_the_scan(name: str, mock_home: Path) -> None:
    """The golden ``installations`` blocks must agree with a real scan.

    Otherwise they are documentation that can drift: the ``agent_entrypoints``
    path contract and the variant labels are both stated there, and both were
    wrong for a long time without any test noticing.
    """
    from skill_lens.core import paths
    from skill_lens.core.discovery import discover
    from skill_lens.core.scanner import build_scan_report

    data = json.loads((GOLDEN_DIR / f"{name}.json").read_text(encoding="utf-8"))
    build_scenario(name, mock_home)
    try:
        home = mock_home.resolve()
        cwd = (home / data["resolutions"][0]["cwd"]).resolve()
        report = build_scan_report(home, cwd)
        index = discover(home, cwd)

        rows = {
            (row.name, Path(row.canonical_path).relative_to(home)): row for row in report.skills
        }
        for expected in data["installations"]:
            key = (expected["name"], Path(expected["canonical_path"]))
            assert key in rows, f"{name}: {key} missing from scan output"
            row = rows[key]
            assert row.scope.value == expected["scope"], key
            assert row.is_symlink == expected["is_symlink"], key
            assert row.variant_label == expected["variant_label"], key
            # Every entrypoint is a *path*, never an agent id (F-11 contract).
            for endpoint in expected["agent_entrypoints"]:
                assert "/" in endpoint, f"{name}: {endpoint} is not a path"
                # A standalone-file skill's entrypoint is ``<name>.md``.
                assert Path(endpoint).name in {expected["name"], f"{expected['name']}.md"}, (
                    f"{name}: {endpoint}"
                )
            # And every path the golden claims really does reach this library.
            reached = {
                str(Path(p).relative_to(home))
                for entry in index.entries
                for p in (entry.entrypoint_paths or (entry.entrypoint_path,))
                if _identity(entry, home) == key
            }
            assert set(expected["agent_entrypoints"]) <= reached, (
                f"{name}: {key} claims entrypoints that do not reach it"
            )
        # Every installation the golden claims must be one the scanner found.
        assert {k for k in rows} >= {
            (i["name"], Path(i["canonical_path"])) for i in data["installations"]
        }
    finally:
        teardown_scenario(name, mock_home)
        paths.set_sandbox(None)


def test_claude_precedence_fixture_shape(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    assert (mock_home / ".claude/skills/deploy/SKILL.md").is_file()
    assert (mock_home / "project/.claude/skills/deploy/SKILL.md").is_file()


def test_nested_qualification_fixture_shape(mock_home: Path) -> None:
    build_scenario("claude_nested_qualification", mock_home)
    assert (mock_home / "project/apps/web/.claude/skills/deploy/SKILL.md").is_file()


def test_symlink_farm_is_three_links_one_target(mock_home: Path) -> None:
    build_scenario("symlink_farm_multi_agent", mock_home)
    canonical = (mock_home / ".agents/skills/shared").resolve()
    links = [
        mock_home / ".claude/skills/shared",
        mock_home / ".pi/agent/skills/shared",
        mock_home / ".qoder/skills/shared",
    ]
    for link in links:
        assert link.is_symlink()
        assert link.resolve() == canonical


def test_symlink_cycle_fixture_is_a_cycle(mock_home: Path) -> None:
    build_scenario("symlink_cycle_guard", mock_home)
    a = mock_home / ".agents/skills/cycle_a"
    b = mock_home / ".agents/skills/cycle_b"
    assert a.is_symlink() and b.is_symlink()
    assert os.readlink(a) == str(b)
    assert os.readlink(b) == str(a)
    assert not a.exists()  # unresolved cycle


def test_antigravity_file_and_directory(mock_home: Path) -> None:
    build_scenario("antigravity_file_based", mock_home)
    assert (mock_home / ".gemini/config/skills/deploy.md").is_file()
    assert (mock_home / ".gemini/config/skills/other/SKILL.md").is_file()


def test_tcc_fixture_sets_and_restores_permissions(mock_home: Path) -> None:
    build_scenario("tcc_permission_error", mock_home)
    blocked = mock_home / ".claude/skills/blocked"
    mode = stat.S_IMODE(blocked.stat().st_mode)
    assert mode == 0o000
    with pytest.raises(PermissionError):
        os.listdir(blocked)
    teardown_scenario("tcc_permission_error", mock_home)
    assert stat.S_IMODE(blocked.stat().st_mode) == 0o755


def test_worktree_dotgit_is_a_file(mock_home: Path) -> None:
    build_scenario("worktree_dotgit_file", mock_home)
    dotgit = mock_home / "project/.git"
    assert dotgit.is_file()
    assert dotgit.read_text().startswith("gitdir:")


def test_system_container_is_hidden_dir(mock_home: Path) -> None:
    build_scenario("system_container_traversal", mock_home)
    assert (mock_home / ".codex/skills/.system/imagegen/SKILL.md").is_file()


def test_disabled_override_writes_settings(mock_home: Path) -> None:
    build_scenario("disabled_override", mock_home)
    settings = json.loads((mock_home / ".claude/settings.json").read_text())
    assert settings["skillOverrides"]["legacy"] is False


def test_malformed_fixture_contains_both_failures(mock_home: Path) -> None:
    build_scenario("malformed_frontmatter", mock_home)
    broken = (mock_home / ".claude/skills/broken/SKILL.md").read_text()
    nodesc = (mock_home / ".claude/skills/nodesc/SKILL.md").read_text()
    assert "[unclosed" in broken
    nodesc_frontmatter = nodesc.split("---")[1]
    assert "description" not in nodesc_frontmatter


def test_project_beats_global_fixture_uses_real_roots(mock_home: Path) -> None:
    """Each agent's global and project copy must sit in that agent's *own* roots.

    An early check of the inverted-rank defect appeared to pass because the
    "global" copy was placed in ``.agents/skills``, which is not the global root
    for those agents. The fixture therefore names each agent's real roots.
    """
    build_scenario("project_beats_global", mock_home)
    expected = (
        ".gemini/config/skills/pg_antigravity",
        ".pi/agent/skills/pg_pi",
        ".grok/skills/pg_grok",
        ".qoder/skills/pg_qoder",
        ".codeium/windsurf/skills/pg_windsurf",
        ".omp/agent/pg_omp",
    )
    for relative in expected:
        assert (mock_home / relative / "SKILL.md").is_file(), relative
    assert (mock_home / "project/.git").is_dir()


# --- Acceptance farm -------------------------------------------------------


def test_acceptance_farm_groups_canonical_library(mock_home: Path) -> None:
    """Phase 0.5 gate: 1 canonical library with N entrypoints, not N installs."""
    farm.build_acceptance_farm(mock_home)
    canonical_root = mock_home / ".agents/skills"
    assert {p.name for p in canonical_root.iterdir()} == set(farm.CANONICAL_SKILLS)

    links = [p for p in mock_home.rglob("*") if p.is_symlink()]
    assert len(links) == farm.canonical_entrypoint_count()

    resolved = {p.resolve() for p in links}
    assert len(resolved) == len(farm.CANONICAL_SKILLS)


def test_acceptance_farm_separates_scopes(mock_home: Path) -> None:
    farm.build_acceptance_farm(mock_home)
    assert (mock_home / ".codex/skills/.system" / farm.SYSTEM_SKILL).is_dir()
    assert (mock_home / "project/.agents/skills" / farm.PROJECT_SKILL).is_dir()
    plugin = mock_home / ".codex/.tmp/plugins/plug/skills" / farm.PLUGIN_SKILL
    assert plugin.is_dir()
    assert ".tmp/plugins" in str(plugin)
