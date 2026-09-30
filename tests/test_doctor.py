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
from skill_lens.core.doctor import CODEX_CONTEXT_BUDGET_CHARS, build_doctor_report
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
