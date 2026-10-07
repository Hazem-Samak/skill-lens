"""Phase 4 doctor tests: every finding the hygiene checks must produce.

The engine is pure -- a discovery index in, a :class:`DoctorReport` out -- so
each test builds exactly the filesystem state that one check is meant to catch
and asserts the finding's machine-readable fields (code, severity, rule_id,
evidence, detail), not its prose. Presentation is pinned separately by the
render snapshots.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import skill_lens.core.doctor as doctor_module
from skill_lens.core.cancellation import CaptureCancelled
from skill_lens.core.doctor import CODEX_CONTEXT_BUDGET_CHARS, build_doctor_report
from skill_lens.core.system import ERR_NOT_JSON, live_discovery, read_json_guarded
from skill_lens.models import dumps
from skill_lens.models.doctor import DoctorFinding, DoctorReport
from skill_lens.models.enums import Evidence, Severity
from skill_lens.models.parsing import ERR_DANGLING_SYMLINK, ERR_SYMLINK_CYCLE
from tests.fixtures.builders import make_skill, symlink, write_text
from tests.fixtures.scenarios import build_scenario, teardown_scenario


def _codes(report: DoctorReport) -> list[str]:
    return [finding.code for finding in report.findings]


def _finding(report: DoctorReport, code: str) -> DoctorFinding:
    return next(finding for finding in report.findings if finding.code == code)


# --- Symlink health ---------------------------------------------------------


def test_a_dangling_symlink_is_an_error(mock_home: Path) -> None:
    home = mock_home.resolve()
    link = home / ".claude" / "skills" / "ghost"
    link.parent.mkdir(parents=True)
    symlink(home / "nowhere", link)
    report = build_doctor_report(home, home)
    finding = _finding(report, "dangling_symlink")
    assert finding.severity is Severity.ERROR
    assert finding.rule_id == "doctor_symlink_health"
    assert finding.evidence is Evidence.EMPIRICAL
    assert finding.detail == ERR_DANGLING_SYMLINK
    assert "claude" in finding.message
    assert not report.healthy


def test_a_symlink_cycle_is_an_error(mock_home: Path) -> None:
    build_scenario("symlink_cycle_guard", mock_home)
    home = mock_home.resolve()
    report = build_doctor_report(home, home)
    finding = _finding(report, "symlink_cycle")
    assert finding.severity is Severity.ERROR
    assert finding.detail == ERR_SYMLINK_CYCLE


def test_a_blocked_skill_directory_is_reported(mock_home: Path) -> None:
    """The TCC scenario blocks one skill *directory* under a readable root."""
    build_scenario("tcc_permission_error", mock_home)
    home = mock_home.resolve()
    try:
        report = build_doctor_report(home, home)
        assert _finding(report, "unreadable_skill").severity is Severity.ERROR
    finally:
        teardown_scenario("tcc_permission_error", home)


def test_an_unreadable_root_is_a_warning(mock_home: Path) -> None:
    home = mock_home.resolve()
    skills = home / ".claude" / "skills"
    make_skill(skills / "hidden", "hidden", "Behind the wall.")
    blocked = home / ".codex" / "skills"
    blocked.mkdir(parents=True)
    os.chmod(blocked, 0o000)
    try:
        report = build_doctor_report(home, home)
        finding = _finding(report, "unreadable_root")
        assert finding.severity is Severity.WARNING
        assert finding.rule_id == "doctor_tcc"
        assert finding.detail == "permission_denied"
        assert str(blocked) in finding.path
    finally:
        os.chmod(blocked, 0o755)


# --- Frontmatter ------------------------------------------------------------


def test_malformed_frontmatter_is_reported_per_skill(mock_home: Path) -> None:
    build_scenario("malformed_frontmatter", mock_home)
    home = mock_home.resolve()
    report = build_doctor_report(home, home)
    findings = [f for f in report.findings if f.code == "malformed_frontmatter"]
    assert len(findings) == 2
    details = {f.detail for f in findings}
    assert details == {"malformed_yaml", "missing_description"}
    assert all(f.severity is Severity.ERROR for f in findings)
    assert all(f.rule_id == "doctor_frontmatter" for f in findings)


def test_a_valid_skill_raises_no_frontmatter_finding(mock_home: Path) -> None:
    home = mock_home.resolve()
    make_skill(home / ".claude" / "skills" / "good", "good", "Fine.")
    report = build_doctor_report(home, home)
    assert "malformed_frontmatter" not in _codes(report)


# --- Codex context budget ----------------------------------------------------


def _codex_skills(home: Path, count: int, description: str) -> None:
    for index in range(count):
        make_skill(home / ".agents" / "skills" / f"cap{index}", f"cap{index}", description)


def test_budget_warning_when_descriptions_overflow(mock_home: Path, monkeypatch) -> None:
    home = mock_home.resolve()
    _codex_skills(home, 3, "x" * 40)
    monkeypatch.setattr(doctor_module, "CODEX_CONTEXT_BUDGET_CHARS", 100)
    report = build_doctor_report(home, home)
    finding = _finding(report, "codex_context_budget")
    assert finding.severity is Severity.WARNING
    assert finding.rule_id == "doctor_codex_context_budget"
    # The provenance of this check is the published Codex doc, not observation.
    assert finding.evidence is Evidence.DOCUMENTED
    assert "3" in finding.message
    assert finding.detail.startswith("https://developers.openai.com/codex/skills")


def test_budget_silent_when_under_the_limit(mock_home: Path) -> None:
    home = mock_home.resolve()
    _codex_skills(home, 3, "Short one.")
    report = build_doctor_report(home, home)
    assert "codex_context_budget" not in _codes(report)
    assert CODEX_CONTEXT_BUDGET_CHARS == 8_000


def test_budget_ignores_invalid_and_non_codex_skills(mock_home: Path, monkeypatch) -> None:
    """Invalid skills are skipped by Codex itself, so they cost no budget."""
    home = mock_home.resolve()
    _codex_skills(home, 1, "x" * 40)
    write_text(
        home / ".claude" / "skills" / "nodesc" / "SKILL.md",
        "---\nname: nodesc\n---\nbody\n",
    )
    monkeypatch.setattr(doctor_module, "CODEX_CONTEXT_BUDGET_CHARS", 30)
    report = build_doctor_report(home, home)
    finding = _finding(report, "codex_context_budget")
    assert "1 Codex-reachable" in finding.message


# --- Traversal hazard --------------------------------------------------------


def test_recursive_root_through_node_modules_is_a_warning(mock_home: Path) -> None:
    """``~/.dsh/profiles`` is a recursive plugin root; it descends into
    dependency trees and surfaces third-party skills nobody installed."""
    home = mock_home.resolve()
    buried = home / ".dsh" / "profiles" / "node_modules" / "pkg" / "skills" / "sneaky"
    make_skill(buried, "sneaky", "Found by the crawl.")
    report = build_doctor_report(home, home)
    finding = _finding(report, "traversal_hazard")
    assert finding.severity is Severity.WARNING
    assert finding.rule_id == "doctor_traversal_hazard"
    assert finding.detail == "node_modules"
    assert "dsh" in finding.message


def test_no_traversal_warning_without_node_modules(mock_home: Path) -> None:
    home = mock_home.resolve()
    make_skill(home / ".dsh" / "profiles" / "me" / "skills" / "own", "own", "Mine.")
    report = build_doctor_report(home, home)
    assert "traversal_hazard" not in _codes(report)


# --- Symlink farm and lockfile ----------------------------------------------


def test_farm_health_is_informational(mock_home: Path) -> None:
    build_scenario("symlink_farm_multi_agent", mock_home)
    home = mock_home.resolve()
    report = build_doctor_report(home, home)
    finding = _finding(report, "symlink_farm")
    assert finding.severity is Severity.INFO
    assert finding.rule_id == "doctor_symlink_farm"
    assert "shared through symlink farms" in finding.message
    # A farm is not a problem: the report is still healthy.
    assert report.healthy


def test_missing_lockfile_is_informational(mock_home: Path) -> None:
    home = mock_home.resolve()
    report = build_doctor_report(home, home)
    finding = _finding(report, "installer_lockfile")
    assert finding.severity is Severity.INFO
    assert finding.detail == "missing"
    assert finding.rule_id == "doctor_installer_lockfile"


def test_valid_lockfile_reports_its_size(mock_home: Path) -> None:
    home = mock_home.resolve()
    lock = home / ".agents" / ".skill-lock.json"
    lock.parent.mkdir(parents=True)
    lock.write_text('{"alpha": "1.0", "beta": "2.0"}\n', encoding="utf-8")
    report = build_doctor_report(home, home)
    finding = _finding(report, "installer_lockfile")
    assert finding.severity is Severity.INFO
    assert finding.detail == "ok"
    assert "2" in finding.message


def test_invalid_lockfile_is_a_warning(mock_home: Path) -> None:
    home = mock_home.resolve()
    lock = home / ".agents" / ".skill-lock.json"
    lock.parent.mkdir(parents=True)
    lock.write_text("{not json\n", encoding="utf-8")
    report = build_doctor_report(home, home)
    finding = _finding(report, "installer_lockfile")
    assert finding.severity is Severity.WARNING
    assert finding.detail == "not_json"
    assert not report.healthy


def test_non_utf8_lock_reports_invalid_json(mock_home: Path) -> None:
    home = mock_home.resolve()
    lock = home / ".agents" / ".skill-lock.json"
    lock.parent.mkdir(parents=True)
    lock.write_bytes(b"\xff\xfe\x00\x00not utf-8")
    data, error = read_json_guarded(lock)
    assert data is None
    assert error == ERR_NOT_JSON

    report = build_doctor_report(home, home)
    finding = _finding(report, "installer_lockfile")
    assert finding.severity is Severity.WARNING
    assert finding.detail == ERR_NOT_JSON
    assert not report.healthy


# --- Report shape ------------------------------------------------------------


def test_findings_are_sorted_by_severity(mock_home: Path) -> None:
    build_scenario("malformed_frontmatter", mock_home)
    home = mock_home.resolve()
    lock = home / ".agents" / ".skill-lock.json"
    lock.parent.mkdir(parents=True)
    lock.write_text("{broken\n", encoding="utf-8")
    report = build_doctor_report(home, home)
    # The engine's own sort key, not a re-typed copy of its rank map.
    ranks = [doctor_module._severity_order(finding)[0] for finding in report.findings]
    assert ranks == sorted(ranks)
    # two malformed skills (error) + one broken lockfile (warning), nothing else
    assert report.counts_by_severity() == {"error": 2, "warning": 1, "info": 0}


def test_report_round_trips_and_is_deterministic(mock_home: Path) -> None:
    build_scenario("malformed_frontmatter", mock_home)
    home = mock_home.resolve()
    first = build_doctor_report(home, home)
    second = build_doctor_report(home, home)
    assert dumps(first.to_dict()) == dumps(second.to_dict())
    assert DoctorReport.from_dict(first.to_dict()) == first


def test_doctor_json_is_canonical(mock_home: Path) -> None:
    home = mock_home.resolve()
    text = dumps(build_doctor_report(home, home).to_dict())
    assert text == json.dumps(json.loads(text), sort_keys=True, indent=2)


def test_an_empty_home_still_reports(mock_home: Path) -> None:
    """An empty home is a clean bill of health, not an error."""
    home = mock_home.resolve()
    report = build_doctor_report(home, home)
    assert report.healthy
    assert all(finding.severity is Severity.INFO for finding in report.findings)


# --- Presentation boundary ---------------------------------------------------


def test_the_doctor_engine_imports_no_rich() -> None:
    """Computation stays pure; Rich is presentation only (AGENTS.md rule 4)."""
    source = Path(doctor_module.__file__).read_text(encoding="utf-8")
    imported: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert [name for name in imported if name.split(".")[0] == "rich"] == []


def test_doctor_reports_home_relative_paths(mock_home: Path) -> None:
    """Findings collapse the effective home to ``~`` for display."""
    home = mock_home.resolve()
    link = home / ".claude" / "skills" / "ghost"
    link.parent.mkdir(parents=True)
    symlink(home / "nowhere", link)
    report = build_doctor_report(home, home)
    finding = _finding(report, "dangling_symlink")
    assert finding.path.startswith("~/")
    assert str(home) not in finding.path


# ---------------------------------------------------------------------------
# C2 Doctor Tests: wrapper inputs and registry evidence definitions (§21.3)
# ---------------------------------------------------------------------------


def test_doctor_wrapper_inputs_matrix_and_index_reuse(mock_home: Path, tmp_path: Path) -> None:
    """Exercise three distinct paths, index-only, registry-only, both, and complete dumps."""
    from unittest.mock import patch

    from skill_lens.core.discovery import discover
    from skill_lens.core.doctor import build_doctor_report, run_doctor
    from skill_lens.models import dumps
    from skill_lens.registry.loader import load_registry

    index_home = (mock_home / "doctor_index_home").resolve()
    index_home.mkdir()
    build_scenario("malformed_frontmatter", index_home)

    index_cwd = (tmp_path / "doctor_index_cwd").resolve()
    index_cwd.mkdir()

    wrapper_cwd = (tmp_path / "doctor_wrapper_cwd").resolve()
    wrapper_cwd.mkdir()

    registry = load_registry()
    index = discover(index_home, index_cwd, registry)

    # Prove the three paths are genuinely distinct
    assert str(index_home) != str(index_cwd)
    assert str(index_cwd) != str(wrapper_cwd)
    assert str(index_home) != str(wrapper_cwd)

    expected_rep = build_doctor_report(index_home, index_cwd, index=index, registry=registry)
    expected_dict = expected_rep.to_dict()
    expected_dumps = dumps(expected_dict)

    # 1. Both supplied with differing wrapper cwd: no live discovery, reuses index home/cwd
    with patch(
        "skill_lens.core.doctor.live_discovery",
        side_effect=AssertionError("live_discovery must not be called when index is provided"),
    ):
        rep_both = run_doctor(cwd=wrapper_cwd, index=index, registry=registry)
        assert rep_both.home == str(index_home)
        assert rep_both.cwd == str(index_cwd)
        assert rep_both.to_dict() == expected_dict
        assert dumps(rep_both.to_dict()) == expected_dumps

    # 2. Index only with differing wrapper cwd: reuses index home and cwd without discovery
    with patch(
        "skill_lens.core.doctor.live_discovery",
        side_effect=AssertionError("live_discovery must not be called when index is provided"),
    ):
        rep_idx = run_doctor(cwd=wrapper_cwd, index=index)
        assert rep_idx.home == str(index_home)
        assert rep_idx.cwd == str(index_cwd)
        assert rep_idx.to_dict() == expected_dict
        assert dumps(rep_idx.to_dict()) == expected_dumps

    # 3. Neither (live default) and registry only parity
    live_expected = run_doctor(cwd=index_home).to_dict()
    live_dumps = dumps(live_expected)
    assert run_doctor(cwd=index_home).to_dict() == live_expected
    assert dumps(run_doctor(cwd=index_home).to_dict()) == live_dumps
    assert run_doctor(cwd=index_home, registry=registry).to_dict() == live_expected
    assert dumps(run_doctor(cwd=index_home, registry=registry).to_dict()) == live_dumps


def test_doctor_wrapper_evidence_wiring_with_inferred_agent(mock_home: Path) -> None:
    """run_doctor forwards supplied registry to build_doctor_report and evidence findings."""
    from unittest.mock import patch

    from skill_lens.core.doctor import run_doctor
    from skill_lens.models.enums import Evidence, Severity
    from skill_lens.registry.loader import AgentDefinition

    guessed = AgentDefinition(
        id="inferred_agent",
        name="Inferred Agent",
        identity_source="directory_name",
        collision_policy="Inferred",
        policy_evidence=Evidence.INFERRED,
        coexist_policy="shadow",
        walk_boundary="git_worktree_root",
        unsearched_rule_id="r1",
    )

    with patch(
        "skill_lens.registry.loader.list_agents",
        side_effect=AssertionError("list_agents must not be called when registry is supplied"),
    ):
        rep = run_doctor(cwd=mock_home, registry={"inferred_agent": guessed})
        assert rep.home == str(mock_home)
        assert rep.cwd == str(mock_home)
        uncited = [f for f in rep.findings if f.code == "registry_uncited_agent"]
        assert len(uncited) == 1
        finding = uncited[0]
        assert finding.code == "registry_uncited_agent"
        assert finding.severity is Severity.INFO
        assert finding.rule_id == "doctor_registry_evidence"
        assert finding.evidence is Evidence.INFERRED
        assert (
            finding.message
            == "Skill Lens cannot cite primary documentation for 1 agent(s): inferred_agent. "
            "Their precedence is inferred, so treat resolution for them as an informed guess."
        )


def test_doctor_empty_registry_produces_no_skill_findings(mock_home: Path, tmp_path: Path) -> None:
    """Empty registry {} yields no skill findings; ban discovery.load_registry."""
    from unittest.mock import patch

    from skill_lens.core.doctor import run_doctor

    # Put a malformed skill and large budget skill on disk
    malformed_dir = mock_home / ".claude" / "skills" / "malformed"
    write_text(malformed_dir / "SKILL.md", "---\nname: [unclosed\n---\n")
    big_dir = mock_home / ".codex" / "skills" / "big"
    # Codex context budget checks description length (> 8000 chars), not markdown body
    write_text(big_dir / "SKILL.md", "---\nname: big\ndescription: " + "x" * 8500 + "\n---\n")

    home = mock_home.resolve()

    # Prove normal registry yields both the budget finding and malformed finding
    normal_rep = run_doctor(cwd=home)
    finding_codes = {f.code for f in normal_rep.findings}
    assert "malformed_frontmatter" in finding_codes
    assert "codex_context_budget" in finding_codes

    with patch(
        "skill_lens.core.discovery.load_registry",
        side_effect=AssertionError(
            "discovery.load_registry must not be called when registry is supplied"
        ),
    ):
        rep = run_doctor(cwd=home, registry={})
        # Empty registry means discovery found zero skills, so no skill findings
        skill_codes = {
            "dangling_symlink",
            "symlink_cycle",
            "malformed_frontmatter",
            "missing_description",
            "codex_context_budget",
            "traversal_outside_root",
            "unreadable_skill",
        }
        assert not any(f.code in skill_codes for f in rep.findings)


def test_doctor_evidence_definitions_bypass_list_agents() -> None:
    """Supplied dict/iterable bypasses list_agents(); inferred agent reports info."""
    from unittest.mock import patch

    from skill_lens.core.doctor import _registry_evidence_findings
    from skill_lens.models.enums import Evidence, Severity
    from skill_lens.registry.loader import AgentDefinition

    guessed = AgentDefinition(
        id="inferred_agent",
        name="Inferred Agent",
        identity_source="directory_name",
        collision_policy="Inferred",
        policy_evidence=Evidence.INFERRED,
        coexist_policy="shadow",
        walk_boundary="git_worktree_root",
        unsearched_rule_id="r1",
    )

    with patch(
        "skill_lens.registry.loader.list_agents",
        side_effect=AssertionError("list_agents must not be called when registry is supplied"),
    ):
        # Empty dict -> no findings, list_agents not called
        assert _registry_evidence_findings({}) == []
        # Empty list/iterable -> no findings, list_agents not called
        assert _registry_evidence_findings([]) == []
        assert _registry_evidence_findings(()) == []
        # Supplied dict with inferred agent -> finding produced
        findings_dict = _registry_evidence_findings({"inferred_agent": guessed})
        assert len(findings_dict) == 1
        assert findings_dict[0].code == "registry_uncited_agent"
        assert findings_dict[0].severity is Severity.INFO
        # Supplied iterable with inferred agent -> finding produced
        findings_list = _registry_evidence_findings([guessed])
        assert len(findings_list) == 1
        assert findings_list[0].code == "registry_uncited_agent"


def test_live_discovery_cancelled(mock_home: Path) -> None:
    """live_discovery forwards cancelled predicate and raises CaptureCancelled."""
    import pytest

    with pytest.raises(CaptureCancelled):
        live_discovery(cwd=mock_home, cancelled=lambda: True)
