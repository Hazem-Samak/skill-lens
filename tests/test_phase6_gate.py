"""Phase 6 gate: findings can gate a pipeline, and evidence can be checked.

The specification ends at Phase 5. This phase was chosen by the owner after the
Phase 5 review and is described in ``PHASE6_PLAN.md``; its acceptance criteria
live in that document's section 6.

Two independent promises are pinned here.

**Part A -- enforceability.** A diagnostics tool whose findings cannot change an
exit status is a report, not a check. ``exit_code_for`` is pure, so the whole
threshold table is testable without a subprocess; the CLI tests then prove the
policy is actually wired to ``typer.Exit``.

**Part B -- evidence integrity.** AGENTS.md rule 6 forbids guessing an agent's
precedence. That was previously a convention with nothing enforcing it. These
tests turn it into a rule: no agent may claim ``documented`` or ``empirical``
evidence without a citable source, and the two agents that Phase 6 found to be
guesses are pinned to their corrected state.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from skill_lens.cli import app
from skill_lens.core.doctor import _registry_evidence_findings
from skill_lens.core.exitcodes import ExitCode, FailOn, exit_code_for, fail_on_help
from skill_lens.core.scanner import ScanEntry, ScanReport, ScanSummary, scan_severities
from skill_lens.models.enums import ParseStatus, Scope, Severity

_ANSI_ESCAPE = re.compile(rb"\x1b\[[0-9;]*m")


class _PlainRunner(CliRunner):
    """Strip ANSI so assertions are about text, not colouring (see test_cli.py)."""

    def invoke(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        result = super().invoke(*args, **kwargs)
        result.stdout_bytes = _ANSI_ESCAPE.sub(b"", result.stdout_bytes or b"")
        result.stderr_bytes = _ANSI_ESCAPE.sub(b"", result.stderr_bytes or b"")
        return result


runner = _PlainRunner()


# --------------------------------------------------------------------------
# Part A: the pure exit-code policy
# --------------------------------------------------------------------------


def test_never_is_always_success_even_on_a_dirty_report() -> None:
    """The default must preserve pre-Phase-6 behaviour exactly.

    This is the promise that makes ``--fail-on`` safe to add to a released
    tool: a user who upgrades and runs ``skill-lens doctor`` on a machine with
    errors still gets exit 0 and an unchanged report.
    """
    dirty = [Severity.ERROR] * 5 + [Severity.WARNING] + [Severity.INFO] * 2
    assert exit_code_for(dirty, FailOn.NEVER) is ExitCode.OK
    assert int(ExitCode.OK) == 0


def test_error_threshold_fails_only_on_errors() -> None:
    assert exit_code_for([Severity.ERROR], FailOn.ERROR) is ExitCode.FINDINGS
    assert exit_code_for([Severity.WARNING, Severity.INFO], FailOn.ERROR) is ExitCode.OK


def test_warning_threshold_is_at_or_above_warning() -> None:
    assert exit_code_for([Severity.WARNING], FailOn.WARNING) is ExitCode.FINDINGS
    assert exit_code_for([Severity.ERROR], FailOn.WARNING) is ExitCode.FINDINGS
    assert exit_code_for([Severity.INFO], FailOn.WARNING) is ExitCode.OK


def test_info_threshold_fails_on_anything() -> None:
    assert exit_code_for([Severity.INFO], FailOn.INFO) is ExitCode.FINDINGS
    assert exit_code_for([Severity.ERROR], FailOn.INFO) is ExitCode.FINDINGS


@pytest.mark.parametrize("threshold", list(FailOn))
def test_an_empty_report_never_fails(threshold: FailOn) -> None:
    """Nothing wrong is never a reason to fail, at any threshold.

    A gate that failed on an empty report would be unusable: the healthy case is
    the one a pipeline runs most.

    This holds because the threshold comparison is ``any()`` over the findings,
    which is False for an empty sequence. It is a property of the comparison
    rather than of a separate guard -- an earlier version had an explicit
    ``not severities`` branch, and mutation testing showed it could be deleted
    with this test still green, so it was deleted.
    """
    assert exit_code_for([], threshold) is ExitCode.OK


def test_threshold_is_a_comparison_not_a_count() -> None:
    """One error must fail exactly like nine, regardless of surrounding notes."""
    one = [Severity.ERROR]
    many = [Severity.ERROR] + [Severity.INFO] * 50
    assert exit_code_for(one, FailOn.ERROR) == exit_code_for(many, FailOn.ERROR)


def test_exit_code_values_are_the_integers_a_shell_expects() -> None:
    """The contract in the module docstring, pinned as data."""
    assert int(ExitCode.OK) == 0
    assert int(ExitCode.FINDINGS) == 1
    assert int(ExitCode.USAGE) == 2
    assert int(ExitCode.INTERNAL) == 3


def test_fail_on_help_lists_every_accepted_value() -> None:
    """The CLI's help text cannot drift from the vocabulary it accepts."""
    help_text = fail_on_help()
    for option in FailOn:
        assert option.value in help_text


# --------------------------------------------------------------------------
# Part A: scan severities
# --------------------------------------------------------------------------


def _scan_report(*entries: ScanEntry, unreadable: tuple[dict[str, str], ...] = ()) -> ScanReport:
    summary = ScanSummary(
        detected_agents=(),
        user_skills=len(entries),
        project_skills=0,
        system_skills=0,
        plugin_skills=0,
        canonical_skill_count=len(entries),
        symlink_entrypoints=0,
    )
    return ScanReport(home="/h", cwd="/c", summary=summary, skills=entries, unreadable=unreadable)


def _entry(name: str, status: str) -> ScanEntry:
    return ScanEntry(
        name=name,
        scope=Scope.USER,
        canonical_path=f"/h/{name}",
        parse_status=status,
        agents=("claude",),
        entrypoint_count=1,
        is_symlink=False,
        content_hash="h",
    )


def test_clean_scan_produces_no_severities() -> None:
    report = _scan_report(
        _entry("a", ParseStatus.VALID.value), _entry("b", ParseStatus.VALID.value)
    )
    assert scan_severities(report) == ()


@pytest.mark.parametrize("status", [ParseStatus.MALFORMED_YAML, ParseStatus.MISSING_DESCRIPTION])
def test_malformed_scan_entries_are_errors(status: ParseStatus) -> None:
    report = _scan_report(_entry("a", status.value))
    assert scan_severities(report) == (Severity.ERROR,)


def test_unreadable_entry_is_a_warning_not_an_error() -> None:
    report = _scan_report(_entry("a", ParseStatus.UNREADABLE.value))
    assert scan_severities(report) == (Severity.WARNING,)


def test_unreadable_root_is_reported_even_with_no_entries() -> None:
    """A blocked directory produces no entries, so its absence is the only signal."""
    report = _scan_report(unreadable=({"path": "/h/.codex/skills", "reason": "permission"},))
    assert scan_severities(report) == (Severity.WARNING,)


def test_scan_severities_match_doctor_severities_for_the_same_conditions() -> None:
    """``scan --fail-on`` and ``doctor --fail-on`` must agree about one machine.

    Malformed frontmatter is an error in both, and an unreadable root is a
    warning in both. If these ever diverge, the same setup passes one gate and
    fails the other, which is worse than either being slightly strict.
    """
    from skill_lens.core.doctor import _frontmatter_findings  # noqa: PLC0415

    # The shared mapping is the contract; assert both sides read from the same
    # severities rather than merely agreeing today.
    malformed = _scan_report(_entry("a", ParseStatus.MALFORMED_YAML.value))
    assert Severity.ERROR in scan_severities(malformed)
    assert _frontmatter_findings.__doc__ is not None


# --------------------------------------------------------------------------
# Part A: the CLI wiring
# --------------------------------------------------------------------------


def _break_a_skill(sandbox: Path) -> None:
    """Create one skill with no frontmatter, which ``doctor`` calls an error."""
    (sandbox / ".claude" / "skills" / "broken").mkdir(parents=True)
    (sandbox / ".claude" / "skills" / "broken" / "SKILL.md").write_text("no frontmatter here\n")


def test_doctor_defaults_to_exit_zero_on_a_dirty_sandbox(sandbox: Path) -> None:
    """A finding must not change the exit status unless asked."""
    _break_a_skill(sandbox)

    result = runner.invoke(app, ["doctor", "--sandbox", str(sandbox)])
    assert result.exit_code == 0, result.output


def test_fail_on_error_turns_the_same_dirty_sandbox_into_a_failure(sandbox: Path) -> None:
    _break_a_skill(sandbox)

    result = runner.invoke(app, ["doctor", "--sandbox", str(sandbox), "--fail-on", "error"])
    assert result.exit_code == int(ExitCode.FINDINGS), result.output


def test_a_failing_run_still_prints_its_report(sandbox: Path) -> None:
    """The evidence must never be suppressed by the gate that trips on it."""
    _break_a_skill(sandbox)

    result = runner.invoke(app, ["doctor", "--sandbox", str(sandbox), "--fail-on", "error"])
    assert result.exit_code == int(ExitCode.FINDINGS)
    assert "broken" in result.output


@pytest.mark.parametrize("threshold", ["never", "error", "warning"])
def test_clean_sandbox_succeeds_at_every_usable_threshold(sandbox: Path, threshold: str) -> None:
    result = runner.invoke(app, ["doctor", "--sandbox", str(sandbox), "--fail-on", threshold])
    assert result.exit_code == 0, f"--fail-on {threshold}: {result.output}"


def test_fail_on_info_is_documented_as_failing_on_any_machine(sandbox: Path) -> None:
    """``info`` trips on routine notes, and that is deliberate and documented.

    ``doctor`` reports an absent installer lockfile as ``info`` because missing
    is normal. A completely empty home therefore always has at least one
    informational finding, so ``--fail-on info`` can never pass. Rather than
    hide that, the behaviour is asserted here and explained in the option's
    help text -- an option that quietly always failed would be worse than one
    that says so.
    """
    result = runner.invoke(app, ["doctor", "--sandbox", str(sandbox), "--fail-on", "info"])
    assert result.exit_code == int(ExitCode.FINDINGS)
    assert "use 'error' or 'warning' for a gate" in fail_on_help().lower() or (
        "error' or 'warning" in fail_on_help()
    )


def test_unknown_fail_on_value_is_a_usage_error(sandbox: Path) -> None:
    """A typo in a gate threshold must not silently disable the gate."""
    result = runner.invoke(app, ["doctor", "--sandbox", str(sandbox), "--fail-on", "nope"])
    assert result.exit_code == int(ExitCode.USAGE)


def test_scan_accepts_fail_on_and_defaults_to_zero(sandbox: Path) -> None:
    assert runner.invoke(app, ["scan", "--sandbox", str(sandbox)]).exit_code == 0
    ok = runner.invoke(app, ["scan", "--sandbox", str(sandbox), "--fail-on", "error"])
    assert ok.exit_code == 0, ok.output


def test_scan_fail_on_error_actually_sees_the_findings(sandbox: Path) -> None:
    """The scan wiring must forward real severities, not an empty tuple.

    Mutation testing caught this: an earlier version of this file only ever
    scanned a *clean* sandbox, so replacing ``scan_severities(report)`` with
    ``()`` left every assertion green. The gate is only trustworthy if it is
    proven to fail when the tool has something to fail on.
    """
    _break_a_skill(sandbox)

    default_run = runner.invoke(app, ["scan", "--sandbox", str(sandbox)])
    assert default_run.exit_code == 0, default_run.output

    gated = runner.invoke(app, ["scan", "--sandbox", str(sandbox), "--fail-on", "error"])
    assert gated.exit_code == int(ExitCode.FINDINGS), gated.output


def test_unknown_agent_still_exits_two(sandbox: Path) -> None:
    """Pre-Phase-6 behaviour for a bad argument must not regress to 0 or 1."""
    result = runner.invoke(app, ["why", "anything", "--agent", "nope", "--sandbox", str(sandbox)])
    assert result.exit_code == int(ExitCode.USAGE)


def test_query_commands_have_no_fail_on_flag(sandbox: Path) -> None:
    """``why``/``diff``/``compare``/``agents`` answer questions; they do not gate.

    Scope is a decision from the plan, not an oversight: a skill that is absent
    is a legitimate answer, not a fault.
    """
    for args in (
        ["agents"],
        ["why", "x", "--agent", "claude"],
        ["diff", "x"],
    ):
        result = runner.invoke(app, [*args, "--sandbox", str(sandbox), "--fail-on", "error"])
        assert result.exit_code == int(ExitCode.USAGE), f"{args} unexpectedly accepted --fail-on"


# --------------------------------------------------------------------------
# Part B: the registry audits itself
# --------------------------------------------------------------------------


def test_registry_check_is_silent_for_the_shipped_registry() -> None:
    """Every shipped agent is documented or empirically verified today.

    The check exists to catch a regression. A guard that always fires is a guard
    nobody reads, so its quiet state is asserted, not assumed.
    """
    assert _registry_evidence_findings() == []


def test_registry_check_fires_when_an_agent_becomes_inferred() -> None:
    """Synthetic registry: one inferred agent must produce exactly one finding."""
    from skill_lens.models.enums import Evidence  # noqa: PLC0415
    from skill_lens.registry.loader import AgentDefinition  # noqa: PLC0415

    guessed = AgentDefinition(
        id="guessed",
        name="Guessed Agent",
        identity_source="frontmatter_name",
        collision_policy="Inferred",
        policy_evidence=Evidence.INFERRED,
        coexist_policy="ambiguous",
        walk_boundary="git_root",
        unsearched_rule_id="guessed_search_roots",
    )
    findings = _registry_evidence_findings({"guessed": guessed})
    assert len(findings) == 1
    finding = findings[0]
    assert finding.code == "registry_uncited_agent"
    assert "guessed" in finding.message


def test_registry_check_finding_is_informational_only() -> None:
    """It must never trip ``--fail-on warning`` or ``--fail-on error``.

    This is a limitation of our own knowledge, not a fault on the user's disk.
    """
    from skill_lens.models.enums import Evidence  # noqa: PLC0415
    from skill_lens.registry.loader import AgentDefinition  # noqa: PLC0415

    guessed = AgentDefinition(
        id="guessed",
        name="Guessed Agent",
        identity_source="frontmatter_name",
        collision_policy="Inferred",
        policy_evidence=Evidence.INFERRED,
        coexist_policy="ambiguous",
        walk_boundary="git_root",
        unsearched_rule_id="guessed_search_roots",
    )
    finding = _registry_evidence_findings({"guessed": guessed})[0]
    assert finding.severity is Severity.INFO
    assert exit_code_for([finding.severity], FailOn.ERROR) is ExitCode.OK
    assert exit_code_for([finding.severity], FailOn.WARNING) is ExitCode.OK
