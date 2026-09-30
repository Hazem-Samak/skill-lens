"""Phase 2 gate: the 3-axis resolver must match every golden fixture exactly.

This is the machine-checkable acceptance gate from the specification: semantic
JSON output (``json.dumps(sort_keys=True)``) must reproduce the hand-written
golden resolutions across all 13 fixtures, including derived headline states,
per-candidate states, canonical paths, entrypoint paths, visibility, collision,
variant labels, human reasons and ``rule_id`` provenance.

Every field a candidate can get wrong is compared. An earlier version of this
gate checked only ``(state, canonical_path, rule_id)``, which is why a
``agent_entrypoints`` contract break and a permanently-empty ``variant_label``
both passed unnoticed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_lens.core.resolver import resolve_skill
from skill_lens.core.scanner import build_scan_report
from skill_lens.models.enums import Evidence, HeadlineState, Scope
from tests.fixtures.builders import make_skill, skill_markdown, symlink, write_skill
from tests.fixtures.scenarios import (
    SCENARIO_NAMES,
    build_scenario,
    teardown_scenario,
)

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"

# Fields compared for every candidate, in a fixed order for readable diffs.
_COMPARED_CANDIDATE_FIELDS = (
    "state",
    "canonical_path",
    "entrypoint_path",
    "scope",
    "visibility",
    "collision",
    "variant_label",
    "rule_id",
    "reason",
)


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


def _observed(candidate, home: Path) -> dict:
    installation = candidate.installation
    return {
        "state": candidate.state.value,
        "canonical_path": _rel(installation.canonical_path, home),
        "entrypoint_path": _rel(installation.entrypoint_path, home),
        "scope": installation.scope.value,
        "visibility": candidate.visibility.value,
        "collision": candidate.collision.value,
        "variant_label": installation.variant_label,
        "rule_id": candidate.rule_id,
        "reason": candidate.reason,
    }


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

        got = [_observed(candidate, home) for candidate in report.candidates]
        want = resolution["candidates"]
        assert len(got) == len(want), f"candidate count {len(got)} != {len(want)}"
        for observed, expected in zip(got, want, strict=True):
            for field in _COMPARED_CANDIDATE_FIELDS:
                assert field in expected, (
                    f"golden {scenario} is missing the '{field}' field, "
                    "which would silently skip the gate"
                )
                assert observed[field] == expected[field], (
                    f"{scenario}:{resolution['skill']}@{resolution['agent']} "
                    f"candidate {expected['canonical_path']}: {field} "
                    f"{observed[field]!r} != {expected[field]!r}"
                )
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


def test_gate_compares_every_field_that_can_be_wrong() -> None:
    """The gate's own field list must not be quietly narrowed.

    An earlier gate compared three fields and missed a broken model contract
    and an always-empty field. Cutting the list below would leave every other
    test green, so the list itself is pinned here.
    """
    assert set(_COMPARED_CANDIDATE_FIELDS) == {
        "state",
        "canonical_path",
        "entrypoint_path",
        "scope",
        "visibility",
        "collision",
        "variant_label",
        "rule_id",
        "reason",
    }


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


def test_reported_entrypoint_belongs_to_the_requested_agent(mock_home: Path) -> None:
    """F-04 regression: ``why --agent pi`` must show *Pi's* path, not the first walked.

    The three entrypoints are walked in alphabetical agent order, so Claude's
    path used to be reported for every agent.
    """
    build_scenario("symlink_farm_multi_agent", mock_home)
    home = mock_home.resolve()
    expected = {
        "claude": ".claude/skills/shared",
        "pi": ".pi/agent/skills/shared",
        "qoder": ".qoder/skills/shared",
    }
    for agent_id, suffix in expected.items():
        report = resolve_skill("shared", agent_id, home, home)
        assert len(report.candidates) == 1
        installation = report.candidates[0].installation
        assert installation.entrypoint_path.endswith(suffix), agent_id
        # The canonical library is shared, so identity is unchanged.
        assert installation.canonical_path.endswith(".agents/skills/shared"), agent_id


def test_agent_entrypoints_are_paths_not_agent_ids(mock_home: Path) -> None:
    """F-11 regression: the Phase 0 contract defines this field as paths."""
    build_scenario("symlink_farm_multi_agent", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("shared", "pi", home, home)
    entrypoints = report.candidates[0].installation.agent_entrypoints
    assert {Path(p).name for p in entrypoints} == {"shared"}
    assert all(Path(p).is_absolute() for p in entrypoints)
    assert not any(p in {"claude", "pi", "qoder"} for p in entrypoints)


def test_project_shortcut_and_global_copy_stay_separate_candidates(mock_home: Path) -> None:
    """F-02 regression: precedence is judged on the entrypoint path.

    A project shortcut pointing at the global library and the global library
    itself used to collapse into one candidate, losing the shadowed copy.
    """
    home = mock_home.resolve()
    (home / "project" / ".git").mkdir(parents=True)
    library = home / ".agents" / "skills" / "deploy"
    make_skill(library, "deploy", "Shared library.")
    symlink(library, home / "project" / ".agents" / "skills" / "deploy")

    report = resolve_skill("deploy", "codex", home / "project", home)
    entrypoints = {c.installation.entrypoint_path for c in report.candidates}
    assert entrypoints == {
        str(library),
        str(home / "project/.agents/skills/deploy"),
    }
    by_path = {c.installation.entrypoint_path: c for c in report.candidates}
    project = by_path[str(home / "project/.agents/skills/deploy")]
    assert project.state is HeadlineState.ACTIVE
    assert project.rank > by_path[str(library)].rank


def test_codex_merge_policy_is_honoured(mock_home: Path) -> None:
    """F-03 regression: ``coexist_policy = "merge"`` must not fall through."""
    home = mock_home.resolve()
    (home / "project" / ".git").mkdir(parents=True)
    make_skill(home / ".codex" / "skills" / "deploy", "deploy", "Codex global copy.")
    make_skill(
        home / "project" / ".agents" / "skills" / "deploy",
        "deploy",
        "Project copy.",
        body="# Instructions\n\nProject body.\n",
    )
    report = resolve_skill("deploy", "codex", home / "project", home)
    assert report.headline is HeadlineState.COEXISTS
    states = {c.state for c in report.candidates}
    assert HeadlineState.SHADOWED not in states
    assert states == {HeadlineState.ACTIVE, HeadlineState.COEXISTS}


def test_broken_skill_is_findable_by_its_frontmatter_name(mock_home: Path) -> None:
    """F-05 regression: a skill missing ``description`` is still findable."""
    write_skill(
        mock_home / ".codex" / "skills" / "custom_folder",
        "---\nname: my-skill\n---\n# Body without a description.\n",
    )
    home = mock_home.resolve()
    report = resolve_skill("my-skill", "codex", home, home)
    assert report.found
    assert report.headline is HeadlineState.INVALID
    assert len(report.candidates) == 1
    assert report.candidates[0].installation.frontmatter_name == "my-skill"


def test_identity_source_still_governs_which_name_matches(mock_home: Path) -> None:
    """Codex identifies skills by frontmatter name, so the folder name is not a key.

    Before the fix, an *invalid* copy was matched on its folder name regardless
    of the agent's identity source, which disagreed with the valid-copy path.
    """
    write_skill(
        mock_home / ".codex" / "skills" / "custom_folder",
        "---\nname: my-skill\n---\n# Body without a description.\n",
    )
    home = mock_home.resolve()
    # frontmatter_name identity: only the declared name resolves.
    assert resolve_skill("custom_folder", "codex", home, home).found is False


def test_directory_name_agent_matches_a_broken_skill_by_folder(mock_home: Path) -> None:
    """A directory-name agent (Claude) still finds the same copy by folder name."""
    write_skill(
        mock_home / ".claude" / "skills" / "custom_folder",
        "---\nname: my-skill\n---\n# Body without a description.\n",
    )
    home = mock_home.resolve()
    report = resolve_skill("custom_folder", "claude", home, home)
    assert report.found
    assert report.headline is HeadlineState.INVALID


def test_symlinked_markdown_keeps_the_standalone_file_rule(mock_home: Path) -> None:
    """F-06 regression: a symlinked ``.md`` skill is a file skill, not a directory.

    The real file is placed *outside* the scanned root on purpose. If it sat
    beside the link, discovery would find both entries and merging them would
    supply ``is_file`` anyway -- which is exactly why an earlier version of
    this test passed with the bug still present.
    """
    outside = mock_home / "shared" / "library"
    write_skill(outside, skill_markdown("deploy", "Standalone deploy."), filename="real.md")
    link = mock_home / ".gemini" / "config" / "skills" / "deploy.md"
    symlink(outside / "real.md", link)
    assert not link.parent.samefile(outside.parent)  # target is outside the root

    home = mock_home.resolve()
    report = resolve_skill("deploy", "antigravity", home, home)
    assert len(report.candidates) == 1
    assert report.candidates[0].rule_id == "antigravity_standalone_md"
    assert report.candidates[0].installation.entrypoint_path == str(link)


def test_shadowed_reason_names_the_winner_not_the_loser(mock_home: Path) -> None:
    """F-07 regression: the shadowed copy's reason quoted its own description."""
    build_scenario("project_beats_global", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("pg_grok", "grok", home / "project", home)
    shadowed = next(c for c in report.candidates if c.state is HeadlineState.SHADOWED)
    # The loser's own description must not be quoted as the suppressing cause.
    assert "Global copy." not in shadowed.reason
    assert "the project root .agents/skills" in shadowed.reason
    # And the rule cited is the winning copy's rule, which explains the loss.
    assert shadowed.rule_id == "grok_project_shadow"


def test_shadowed_rule_cites_the_winning_root(mock_home: Path) -> None:
    """A shadow must be traceable to the rule that caused it."""
    build_scenario("project_beats_global", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("pg_windsurf", "windsurf", home / "project", home)
    shadowed = next(c for c in report.candidates if c.state is HeadlineState.SHADOWED)
    assert shadowed.rule_id == "windsurf_project_shadow"
    assert shadowed.collision.value == "suppressed_shadow"


def test_scan_and_why_agree_on_variant_labels_across_scopes(mock_home: Path) -> None:
    """F-16 regression: a library reachable at two scopes must be labelled once.

    One library is reached as a *user* root by Claude and as a *project* root by
    Grok. ``scan`` and ``why`` once disagreed on the label for it, because
    ``scan`` passed the most project-specific scope any root assigns while
    ``why`` passed the scope of the one root the requested agent uses. The
    scope must be a property of the entry, not of whoever is asking.
    """
    home = mock_home.resolve()
    (home / "project" / ".git").mkdir(parents=True)
    library = home / "shared" / "deploy"
    make_skill(library, "deploy", "Shared library.", body="# Instructions\n\nShared.\n")
    symlink(library, home / ".claude" / "skills" / "deploy")  # claude: user scope
    symlink(library, home / "project" / ".agents" / "skills" / "deploy")  # grok: project
    # A second, differing copy so the labels are actually A and B.
    make_skill(
        home / "project" / ".claude" / "skills" / "deploy",
        "deploy",
        "Project deploy.",
        body="# Instructions\n\nProject body.\n",
    )

    scanned = {
        Path(skill.canonical_path).relative_to(home).as_posix(): skill.variant_label
        for skill in build_scan_report(home, home / "project").skills
        if skill.name == "deploy"
    }
    for agent in ("claude", "grok"):
        report = resolve_skill("deploy", agent, home / "project", home)
        resolved = {
            Path(c.installation.canonical_path).relative_to(home).as_posix(): (
                c.installation.variant_label
            )
            for c in report.candidates
        }
        shared = set(scanned) & set(resolved)
        assert shared, f"{agent}: no shared copies to compare"
        for path in shared:
            assert resolved[path] == scanned[path], (
                f"{agent}: {path} is {resolved[path]!r} in why but {scanned[path]!r} in scan"
            )


def test_variant_labels_are_populated(mock_home: Path) -> None:
    """F-08 regression: ``variant_label`` was permanently ``None``."""
    build_scenario("variant_hash_detection", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("deploy", "claude", home, home)
    labels = {c.state: c.installation.variant_label for c in report.candidates}
    # The winning copy is Variant A; the copy it beats is Variant B.
    assert labels[HeadlineState.ACTIVE] == "A"
    assert labels[HeadlineState.UNSEARCHED] == "B"


def test_byte_identical_copies_share_one_variant_label(mock_home: Path) -> None:
    """Two paths onto the same bytes are one variant, not two."""
    build_scenario("symlink_farm_multi_agent", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("shared", "claude", home, home)
    assert {c.installation.variant_label for c in report.candidates} == {"A"}


def test_invalid_skills_are_not_labelled_as_variants(mock_home: Path) -> None:
    """A broken copy has no content to compare, so it gets no variant label."""
    build_scenario("malformed_frontmatter", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("broken", "claude", home, home)
    assert report.candidates[0].installation.variant_label is None


def test_scan_reports_variant_labels(mock_home: Path) -> None:
    build_scenario("variant_hash_detection", mock_home)
    home = mock_home.resolve()
    report = build_scan_report(home, home)
    assert {skill.variant_label for skill in report.skills if skill.name == "deploy"} == {
        "A",
        "B",
    }


@pytest.mark.parametrize(
    ("agent", "skill"),
    [
        ("antigravity", "pg_antigravity"),
        ("pi", "pg_pi"),
        ("grok", "pg_grok"),
        ("qoder", "pg_qoder"),
        ("windsurf", "pg_windsurf"),
        ("omp", "pg_omp"),
    ],
)
def test_project_beats_global_for_every_shadow_agent(
    agent: str, skill: str, mock_home: Path
) -> None:
    """F-01 regression: project roots must outrank global roots for all 6.

    ``omp`` is the honest exception on the *loser's* state: its policy is only
    inferred, so the losing copy is reported COEXISTS rather than SHADOWED. The
    project copy must still be the winner.
    """
    build_scenario("project_beats_global", mock_home)
    home = mock_home.resolve()
    report = resolve_skill(skill, agent, home / "project", home)
    by_scope = {c.installation.scope: c for c in report.candidates}
    assert by_scope[Scope.PROJECT].state is HeadlineState.ACTIVE
    assert by_scope[Scope.USER].state in {HeadlineState.SHADOWED, HeadlineState.COEXISTS}
    assert by_scope[Scope.PROJECT].rank > by_scope[Scope.USER].rank


def test_claude_personal_still_beats_project(mock_home: Path) -> None:
    """The F-01 inversion must not flip Claude, whose documented rule is inverse."""
    build_scenario("claude_personal_beats_project", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("deploy", "claude", home / "project", home)
    by_scope = {c.installation.scope: c for c in report.candidates}
    assert by_scope[Scope.USER].state is HeadlineState.ACTIVE
    assert by_scope[Scope.PROJECT].state is HeadlineState.SHADOWED


def test_opencode_ties_stay_ambiguous(mock_home: Path) -> None:
    """Intentional ties must not be 'fixed' into a winner."""
    build_scenario("opencode_ambiguous", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("dup", "opencode", home, home)
    assert report.headline is HeadlineState.AMBIGUOUS


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


def test_unknown_skill_is_not_found_rather_than_unsearched(mock_home: Path) -> None:
    """F-10 regression: "nowhere on disk" is not the same as "outside the roots"."""
    build_scenario("claude_personal_beats_project", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("no-such-skill", "claude", home, home)
    assert report.candidates == ()
    assert report.found is False
    assert report.notes, "a not-found answer must explain itself"
    assert report.to_dict()["found"] is False


def test_copy_outside_the_agents_roots_is_found_but_unsearched(mock_home: Path) -> None:
    """The genuine UNSEARCHED case still reports ``found``."""
    build_scenario("variant_hash_detection", mock_home)
    home = mock_home.resolve()
    report = resolve_skill("deploy", "claude", home, home)
    assert report.found is True
    assert any(c.state is HeadlineState.UNSEARCHED for c in report.candidates)


def test_unknown_agent_raises(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    home = mock_home.resolve()
    with pytest.raises(KeyError):
        resolve_skill("deploy", "not-an-agent", home, home)
