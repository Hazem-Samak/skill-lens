"""Phase 2 gate: the 3-axis resolver must match every golden fixture exactly.

This is the machine-checkable acceptance gate from the specification: semantic
JSON output (``json.dumps(sort_keys=True)``) must reproduce the hand-written
golden resolutions across all 12 fixtures, including derived headline states,
per-candidate states, canonical paths and ``rule_id`` provenance.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_lens.core.resolver import resolve_skill
from skill_lens.models.enums import Evidence, HeadlineState
from tests.fixtures.scenarios import (
    SCENARIO_NAMES,
    build_scenario,
    teardown_scenario,
)

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"


def _golden(name: str) -> dict:
    return json.loads((GOLDEN_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _rel(path: str, home: Path) -> str:
    return Path(path).relative_to(home).as_posix() if str(path).startswith(str(home)) else path


def _resolutions() -> list[tuple[str, dict, dict]]:
    cases: list[tuple[str, dict, dict]] = []
    for name in SCENARIO_NAMES:
        for resolution in _golden(name)["resolutions"]:
            cases.append((name, _golden(name), resolution))
    return cases


CASES = _resolutions()


@pytest.mark.parametrize(
    ("scenario", "resolution"),
    [(case[0], case[2]) for case in CASES],
    ids=[f"{case[0]}:{case[2]['skill']}@{case[2]['agent']}" for case in CASES],
)
def test_resolution_matches_golden(scenario: str, resolution: dict, mock_home: Path) -> None:
    build_scenario(scenario, mock_home)
    try:
        home = mock_home.resolve()
        cwd = (home / resolution["cwd"]).resolve()
        report = resolve_skill(resolution["skill"], resolution["agent"], cwd, home)

        assert report.headline.value == resolution["headline"], (
            f"headline {report.headline.value} != {resolution['headline']}"
        )

        got = [
            (
                candidate.state.value,
                _rel(candidate.installation.canonical_path, home),
                candidate.rule_id,
            )
            for candidate in report.candidates
        ]
        want = [
            (candidate["state"], candidate["canonical_path"], candidate["rule_id"])
            for candidate in resolution["candidates"]
        ]
        assert got == want
    finally:
        teardown_scenario(scenario, mock_home)


@pytest.mark.parametrize("case", CASES, ids=[f"{c[0]}:{c[2]['skill']}" for c in CASES])
def test_every_reason_is_provenance_tagged(case: tuple, mock_home: Path) -> None:
    scenario, _golden_data, resolution = case
    build_scenario(scenario, mock_home)
    try:
        home = mock_home.resolve()
        cwd = (home / resolution["cwd"]).resolve()
        report = resolve_skill(resolution["skill"], resolution["agent"], cwd, home)
        for candidate in report.candidates:
            assert candidate.rule_id, "missing rule_id"
            assert candidate.evidence in set(Evidence)
            assert candidate.reason, "missing human reason"
            assert candidate.visibility.value
            assert candidate.collision.value
    finally:
        teardown_scenario(scenario, mock_home)


# --- Behavioural guarantees ------------------------------------------------


def test_json_is_deterministic(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    home = mock_home.resolve()
    cwd = home / "project"
    first = resolve_skill("deploy", "claude", cwd, home).to_dict()
    second = resolve_skill("deploy", "claude", cwd, home).to_dict()
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_claude_personal_wins_and_project_shadowed(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("deploy", "claude", home / "project", home)
    assert report.headline is HeadlineState.ACTIVE
    states = {c.state for c in report.candidates}
    assert states == {HeadlineState.ACTIVE, HeadlineState.SHADOWED}


def test_nested_copy_coexists(mock_home: Path) -> None:
    build_scenario("claude_nested_qualification", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("deploy", "claude", home / "project" / "apps" / "web", home)
    assert report.headline is HeadlineState.COEXISTS
    assert any(c.state is HeadlineState.COEXISTS for c in report.candidates)


def test_unsearched_is_reported_for_other_agent_root(mock_home: Path) -> None:
    """A copy only reachable via another agent's root is UNSEARCHED here."""
    build_scenario("variant_hash_detection", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("deploy", "claude", home, home)
    unsearched = [c for c in report.candidates if c.state is HeadlineState.UNSEARCHED]
    assert unsearched
    assert unsearched[0].rule_id == "claude_search_roots"


def test_symlink_farm_resolves_to_canonical(mock_home: Path) -> None:
    build_scenario("symlink_farm_multi_agent", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("shared", "pi", home, home)
    assert report.headline is HeadlineState.ACTIVE
    assert len(report.candidates) == 1
    assert report.candidates[0].installation.canonical_path.endswith(".agents/skills/shared")


def test_opencode_ambiguous_headline(mock_home: Path) -> None:
    build_scenario("opencode_ambiguous", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("dup", "opencode", home, home)
    assert report.headline is HeadlineState.AMBIGUOUS
    assert all(c.state is HeadlineState.AMBIGUOUS for c in report.candidates)
    assert report.notes


def test_disabled_override(mock_home: Path) -> None:
    build_scenario("disabled_override", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("legacy", "claude", home, home)
    assert report.headline is HeadlineState.DISABLED


def test_malformed_is_invalid(mock_home: Path) -> None:
    build_scenario("malformed_frontmatter", mock_home)
    home = mock_home.resolve()
    for skill in ("broken", "nodesc"):
        report = resolve_skill(skill, "claude", home, home)
        assert report.headline is HeadlineState.INVALID


def test_cycle_is_invalid_not_hang(mock_home: Path) -> None:
    build_scenario("symlink_cycle_guard", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("cycle_a", "codex", home, home)
    assert report.headline is HeadlineState.INVALID
    assert report.candidates[0].rule_id == "symlink_cycle_guard"


def test_unknown_skill_returns_unsearched(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("no-such-skill", "claude", home, home)
    assert report.headline is HeadlineState.UNSEARCHED
    assert report.candidates == ()


def test_unknown_agent_raises(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    home = mock_home.resolve()
    with pytest.raises(KeyError):
        resolve_skill("deploy", "not-an-agent", home, home)
