"""Model contract tests: frozen, hashable, JSON round-trippable."""

from __future__ import annotations

import dataclasses
import json

import pytest

from skill_lens.models import (
    CandidateResolution,
    Collision,
    DoctorFinding,
    Evidence,
    HeadlineState,
    ParseStatus,
    ResolutionReport,
    Scope,
    Severity,
    SkillInstallation,
    Visibility,
    dumps,
)


@pytest.fixture
def installation() -> SkillInstallation:
    return SkillInstallation(
        name="deploy",
        entrypoint_path="/home/.claude/skills/deploy",
        canonical_path="/home/.agents/skills/deploy",
        scope=Scope.USER,
        parse_status=ParseStatus.VALID,
        content_hash="sha256:abc",
        description="Deploy things.",
        is_symlink=True,
        agent_entrypoints=("/home/.claude/skills/deploy",),
        variant_label="A",
    )


def test_enums_are_str_serializable() -> None:
    assert json.dumps({"state": HeadlineState.ACTIVE}) == '{"state": "ACTIVE"}'
    assert Scope.USER == "user"


def test_installation_is_frozen(installation: SkillInstallation) -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        installation.name = "other"  # type: ignore[misc]


def test_installation_is_hashable(installation: SkillInstallation) -> None:
    assert isinstance(hash(installation), int)


def test_installation_round_trip(installation: SkillInstallation) -> None:
    assert SkillInstallation.from_dict(installation.to_dict()) == installation


def test_resolution_round_trip(installation: SkillInstallation) -> None:
    candidate = CandidateResolution(
        state=HeadlineState.SHADOWED,
        visibility=Visibility.ACTIVE_ROOT,
        collision=Collision.SUPPRESSED_SHADOW,
        rule_id="claude_personal_beats_project",
        evidence=Evidence.DOCUMENTED,
        reason="Personal wins.",
        rank=1,
        installation=installation,
    )
    report = ResolutionReport(
        skill_name="deploy",
        agent="claude",
        agent_name="Claude Code",
        cwd="/home/project",
        collision_policy="Personal > Project",
        policy_evidence=Evidence.DOCUMENTED,
        headline=HeadlineState.ACTIVE,
        candidates=(candidate,),
        notes=("nested copies qualify",),
    )
    assert ResolutionReport.from_dict(report.to_dict()) == report


def test_doctor_round_trip() -> None:
    finding = DoctorFinding(
        code="dangling_symlink",
        severity=Severity.ERROR,
        message="Broken link",
        rule_id="symlink_integrity",
        evidence=Evidence.EMPIRICAL,
        path="/home/.claude/skills/x",
    )
    assert DoctorFinding.from_dict(finding.to_dict()) == finding


def test_dumps_is_canonical(installation: SkillInstallation) -> None:
    """sort_keys makes output byte-stable for golden comparison."""
    output = dumps(installation.to_dict())
    assert output == json.dumps(installation.to_dict(), sort_keys=True, indent=2)
