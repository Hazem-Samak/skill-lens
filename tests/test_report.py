"""Tests for the combined diagnostic report (issue #6).

Every fixture lives inside the synthetic ``mock_home``; no real ``$HOME`` is
read. The one-pass proof spies on the discovery bindings the code actually
calls, because ``discover`` is copied into consumer namespaces at import time.
Goldens and Markdown snapshots pin an injected clock and platform token.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

import skill_lens.core.compare as compare_module
import skill_lens.core.doctor as doctor_module
import skill_lens.core.report as report_module
import skill_lens.core.scanner as scanner_module
from skill_lens import __version__
from skill_lens.cli import app
from skill_lens.core import paths
from skill_lens.core.report import assemble_report, build_report, run_report, utc_timestamp
from skill_lens.core.system import live_discovery
from skill_lens.models import dumps
from skill_lens.models.compare import CompareEntry, CompareReport
from skill_lens.models.doctor import DoctorFinding, DoctorReport
from skill_lens.models.enums import CompareRelation, Evidence, Severity
from skill_lens.models.report import ReportMeta, ReportModel
from skill_lens.presentation.report import escape_markdown, markdown_text
from skill_lens.registry.loader import AgentDefinition
from tests.fixtures.builders import make_skill
from tests.fixtures.farm import build_acceptance_farm

runner = CliRunner()

FIXED_GENERATED_AT = datetime(2026, 11, 19, 14, 20, tzinfo=UTC)
FIXED_PLATFORM = "TestPlatform-1.0"
GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden" / "report"
SNAPSHOT_DIR = Path(__file__).parent / "fixtures" / "snapshots"


def _fixed_model(home: Path, *, compare_agents: tuple[str, str] | None = None) -> ReportModel:
    return build_report(
        home,
        home,
        compare_agents=compare_agents,
        generated_at=FIXED_GENERATED_AT,
        platform_text=FIXED_PLATFORM,
    )


class _Counts:
    """Call counters for the discovery bindings under test."""

    def __init__(self) -> None:
        self.live = 0
        self.scanner = 0
        self.doctor = 0
        self.compare = 0


def _arm_discovery_spies(
    monkeypatch: pytest.MonkeyPatch,
    counts: _Counts,
) -> None:
    """Wrap the exact bindings the production code calls.

    ``discover`` is copied into each consumer namespace at import time, so
    patching ``skill_lens.core.discovery.discover`` would observe nothing.
    """

    def wrap(module: object, name: str, attribute: str):
        original = getattr(module, name)

        def spy(*args, **kwargs):
            setattr(counts, attribute, getattr(counts, attribute) + 1)
            return original(*args, **kwargs)

        monkeypatch.setattr(module, name, spy)

    wrap(report_module, "live_discovery", "live")
    wrap(scanner_module, "discover", "scanner")
    wrap(doctor_module, "discover", "doctor")
    wrap(compare_module, "discover", "compare")


# ---------------------------------------------------------------------------
# Escaper
# ---------------------------------------------------------------------------


def test_escaper_matches_the_published_oracle() -> None:
    """The exact input/output pair from the frozen plan, byte for byte."""
    source = "a\\b_c]d>e|f`g[h*i<j\r\nk\n\nl"
    expected = "a\\\\b\\_c\\]d\\>e\\|f\\`g\\[h\\*i\\<j k  l"
    assert escape_markdown(source) == expected


def test_escaper_is_single_pass() -> None:
    """Inserted backslashes are never re-escaped."""
    assert escape_markdown("\\_") == "\\\\\\_"
    assert escape_markdown("a\r\nb\nc") == "a b c"


def test_escaper_flattens_standalone_carriage_returns() -> None:
    assert escape_markdown("a\rb\r\nc\nd") == "a b c d"


# ---------------------------------------------------------------------------
# Timestamp
# ---------------------------------------------------------------------------


def test_utc_timestamp_converts_an_aware_value_to_utc() -> None:
    plus_two = timezone(timedelta(hours=2))
    value = datetime(2026, 11, 19, 16, 20, 0, tzinfo=plus_two)
    assert utc_timestamp(value) == "2026-11-19T14:20:00+00:00"


def test_utc_timestamp_rejects_a_naive_value() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        utc_timestamp(datetime(2026, 11, 19, 14, 20, 0))


# ---------------------------------------------------------------------------
# Goldens
# ---------------------------------------------------------------------------


def _rel(value: str, home: Path) -> str:
    """One string as a home-relative golden token.

    Handles the absolute prefix, the resolved spelling and an already
    collapsed ``~/...`` display form, exactly like the Phase 4 rule.
    """
    for root in (str(home), str(home.resolve())):
        if value == root:
            return "."
        prefix = root + os.sep
        if value.startswith(prefix):
            return Path(value).relative_to(root).as_posix()
    shown = paths.display(value)
    if shown == "~":
        return "."
    if shown.startswith("~/"):
        return shown[2:]
    return value


def _normalize(value: object, home: Path) -> object:
    """Recursively rewrite every string in a report payload."""
    if isinstance(value, dict):
        return {key: _normalize(item, home) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item, home) for item in value]
    if isinstance(value, str):
        return _rel(value, home)
    return value


def _assert_no_machine_path(text: str, home: Path, label: str) -> None:
    """Reject both the as-written and resolved spellings of the mock home.

    On macOS ``/tmp`` and ``/private/tmp`` can name the same directory, so a
    fixture built from the unresolved path must check both forms.
    """
    assert str(home) not in text, f"{label} embeds the mock home"
    assert str(home.resolve()) not in text, f"{label} embeds the resolved mock home"


def _check_golden(name: str, payload: dict[str, object], home: Path, update: bool) -> dict:
    normalized = _normalize(payload, home)
    assert isinstance(normalized, dict)
    path = GOLDEN_DIR / f"{name}.json"
    if update:
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(dumps(normalized), encoding="utf-8")
    assert path.exists(), f"missing golden {path.name}; review the output before --update-goldens"
    text = path.read_text(encoding="utf-8")
    expected = json.loads(text)
    assert normalized == expected
    assert text == json.dumps(expected, sort_keys=True, indent=2), name
    _assert_no_machine_path(text, home, name)
    return expected


def test_report_golden_on_the_acceptance_farm(mock_home: Path, update_goldens: bool) -> None:
    """The farm report is pinned with a fixed clock and platform token."""
    home = mock_home.resolve()
    build_acceptance_farm(home)
    model = _fixed_model(home)
    expected = _check_golden("report_farm", model.to_dict(), home, update_goldens)
    assert expected["compare"] is None
    assert expected["meta"] == {
        "generated_at": "2026-11-19T14:20:00+00:00",
        "skill_lens_version": __version__,
        "platform": FIXED_PLATFORM,
    }
    detected = expected["scan"]["summary"]["detected_agents"]
    assert {"claude", "codex"} <= set(detected)
    assert len(expected["agents"]) == 10
    assert expected["scan"]["summary"]["total_skills"] == 7


def test_report_compare_golden_on_the_acceptance_farm(
    mock_home: Path, update_goldens: bool
) -> None:
    """claude vs codex is pinned, with shared counts derived at render time."""
    home = mock_home.resolve()
    build_acceptance_farm(home)
    model = _fixed_model(home, compare_agents=("claude", "codex"))
    expected = _check_golden(
        "report_compare_claude_vs_codex", model.to_dict(), home, update_goldens
    )
    compare = expected["compare"]
    assert compare is not None
    assert compare["agent_a"] == "claude"
    assert compare["agent_b"] == "codex"
    relations = {entry["name"]: entry["relation"] for entry in compare["entries"]}
    assert all(
        relations[name] == "shared" for name in ("alpha", "beta", "gamma", "delta", "epsilon")
    )
    assert relations["plugskill"] == "only_b"
    assert "counts_by_relation" not in compare


@pytest.mark.parametrize("name", ["report_farm", "report_compare_claude_vs_codex"])
def test_report_dict_from_dict_round_trip(name: str) -> None:
    payload = json.loads((GOLDEN_DIR / f"{name}.json").read_text(encoding="utf-8"))
    model = ReportModel.from_dict(payload)
    assert isinstance(model.agents, tuple)
    assert model.to_dict() == payload


@pytest.mark.parametrize("pair", [None, ("claude", "codex")])
def test_report_model_round_trips_through_its_dict(
    mock_home: Path, pair: tuple[str, str] | None
) -> None:
    home = mock_home.resolve()
    build_acceptance_farm(home)
    model = _fixed_model(home, compare_agents=pair)
    assert ReportModel.from_dict(model.to_dict()) == model


def test_report_compare_key_is_always_present() -> None:
    payload = json.loads((GOLDEN_DIR / "report_farm.json").read_text(encoding="utf-8"))
    assert "compare" in payload and payload["compare"] is None
    with_pair = json.loads(
        (GOLDEN_DIR / "report_compare_claude_vs_codex.json").read_text(encoding="utf-8")
    )
    assert with_pair["compare"] is not None


# ---------------------------------------------------------------------------
# Markdown snapshots
# ---------------------------------------------------------------------------


def _check_markdown(name: str, text: str, home: Path, update: bool) -> str:
    path = SNAPSHOT_DIR / f"{name}.txt"
    if update:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return text
    assert path.exists(), f"missing snapshot {path.name}; run with --update-snapshots"
    expected = path.read_text(encoding="utf-8")
    assert text == expected, f"snapshot {name} changed; review the diff before updating"
    _assert_no_machine_path(text, home, f"snapshot {name}")
    return text


def test_report_markdown_snapshot_on_the_farm(mock_home: Path, update_snapshots: bool) -> None:
    home = mock_home.resolve()
    build_acceptance_farm(home)
    text = markdown_text(_fixed_model(home), paths.display)
    rendered = _check_markdown("report/report_farm", text, home, update_snapshots)
    assert "## Compare highlights" not in rendered
    assert "Plugin" in rendered
    assert "0.2.1" in rendered or __version__ in rendered


def test_report_markdown_snapshot_with_compare(mock_home: Path, update_snapshots: bool) -> None:
    home = mock_home.resolve()
    build_acceptance_farm(home)
    text = markdown_text(_fixed_model(home, compare_agents=("claude", "codex")), paths.display)
    rendered = _check_markdown(
        "report/report_compare_claude_vs_codex", text, home, update_snapshots
    )
    assert "## Compare highlights" in rendered
    assert "| shared | 5 |" in rendered


def test_report_markdown_snapshot_empty_home(mock_home: Path, update_snapshots: bool) -> None:
    home = mock_home.resolve()
    text = markdown_text(_fixed_model(home), paths.display)
    _check_markdown("report/report_empty", text, home, update_snapshots)


def test_absence_check_rejects_the_resolved_spelling_of_an_unresolved_home(
    tmp_path: Path,
) -> None:
    """Exercise the resolved-home branch with two genuinely distinct spellings."""
    real = tmp_path / "real-home"
    real.mkdir()
    link = tmp_path / "link-home"
    link.symlink_to(real, target_is_directory=True)
    assert str(link) != str(link.resolve())

    _assert_no_machine_path("a clean report", link, "probe")
    with pytest.raises(AssertionError, match="resolved mock home"):
        _assert_no_machine_path(f"leak {link.resolve()}", link, "probe")
    with pytest.raises(AssertionError, match="embeds the mock home"):
        _assert_no_machine_path(f"leak {link}", link, "probe")


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------


def test_empty_home_has_all_headings_and_no_compare_section(mock_home: Path) -> None:
    home = mock_home.resolve()
    model = _fixed_model(home)
    text = markdown_text(model, paths.display)
    for heading in (
        "# Skill Lens Report",
        "## Detected agents",
        "## Known agents and precedence",
        "## Canonical library summary",
        "## Per-agent skill inventory",
        "## Doctor findings",
    ):
        assert heading in text
    assert "## Compare highlights" not in text
    assert "No agents detected on this machine." in text
    assert "No skills detected on this machine." in text
    assert "| Canonical library (user-scope skills) | 0 |" in text
    assert "| Total skills (all scopes) | 0 |" in text
    detected_section = text.split("## Detected agents", 1)[1].split(
        "## Known agents and precedence", 1
    )[0]
    assert "antigravity" not in detected_section


def test_inventory_uses_plugin_label_and_scope_then_name_order(mock_home: Path) -> None:
    home = mock_home.resolve()
    build_acceptance_farm(home)
    text = markdown_text(_fixed_model(home), paths.display)
    assert "| plugskill | Plugin |" in text
    codex = text.split("### codex", 1)[1].split("\n### ", 1)[0].split("\n## ", 1)[0]
    order = [line.split("|")[1].strip() for line in codex.splitlines() if line.startswith("| ")]
    order = [name for name in order if name not in {"Name", "---"}]
    assert order == ["alpha", "beta", "delta", "epsilon", "gamma", "omega", "plugskill"]


def test_detected_agents_are_in_the_pinned_order(mock_home: Path) -> None:
    home = mock_home.resolve()
    build_acceptance_farm(home)
    model = _fixed_model(home)
    detected = model.scan["summary"]["detected_agents"]
    headings = [
        line.removeprefix("### ")
        for line in markdown_text(model, paths.display).splitlines()
        if line.startswith("### ")
    ]
    assert headings == detected


def test_hostile_name_description_and_doctor_message_stay_table_safe(mock_home: Path) -> None:
    home = mock_home.resolve()
    make_skill(
        home / ".claude" / "skills" / "evil|name",
        "evil|name",
        "desc | with [brackets] and *stars*",
    )
    blocked = home / ".claude" / "skills" / "blocked|pipe"
    make_skill(blocked, "blocked", "Blocked.")
    os.chmod(blocked, 0o000)
    try:
        text = markdown_text(_fixed_model(home), paths.display)
    finally:
        os.chmod(blocked, 0o755)
    assert "evil\\|name" in text
    assert "desc \\| with \\[brackets\\] and \\*stars\\*" in text
    hostile_line = next(line for line in text.splitlines() if "blocked\\|pipe" in line)
    assert "unreadable\\_skill" in hostile_line
    assert "| unreadable\\_root |" not in hostile_line


def test_unreadable_root_is_reported_and_paths_are_collapsed(mock_home: Path) -> None:
    home = mock_home.resolve()
    root = home / ".claude" / "skills"
    root.mkdir(parents=True)
    os.chmod(root, 0o000)
    try:
        with pytest.raises(OSError):
            list(root.iterdir())
        model = _fixed_model(home)
        text = markdown_text(model, paths.display)
    finally:
        os.chmod(root, 0o755)
    # The renderer escapes every dynamic string, so an underscore in a rule id
    # is printed as ``\_`` (the reader still sees doctor_tcc).
    assert "doctor\\_tcc" in text
    assert "| warning |" in text
    assert "~/.claude/skills" in text
    assert str(home) not in text
    findings = model.to_dict()["doctor"]["findings"]
    tcc = [finding for finding in findings if finding["rule_id"] == "doctor_tcc"]
    assert tcc and tcc[0]["path"].startswith(str(home))
    unreadable = model.to_dict()["scan"]["unreadable"]
    assert unreadable
    assert {"agent", "root", "path", "detail"} <= set(unreadable[0])
    assert unreadable[0]["path"].startswith(str(home))


def test_none_path_finding_renders_an_empty_cell_without_calling_display(
    mock_home: Path,
) -> None:
    home = mock_home.resolve()
    base = _fixed_model(home)
    finding = DoctorFinding(
        code="registry_uncited_agent",
        severity=Severity.INFO,
        message="Skill Lens cannot cite an agent.",
        rule_id="doctor_registry_evidence",
        evidence=Evidence.INFERRED,
        path=None,
        detail="uncited=x",
    )
    doctor = DoctorReport(home=str(home), cwd=str(home), findings=(finding,))
    model = assemble_report(base.scan, doctor, base.agents, None, base.meta)
    seen: list[str] = []

    def display(value: str) -> str:
        seen.append(value)
        return value

    text = markdown_text(model, display)
    assert all(value is not None for value in seen)
    line = next(line for line in text.splitlines() if "registry\\_uncited\\_agent" in line)
    assert "None" not in line
    assert line.count("|") == 8, line


def test_compare_notes_and_non_shared_rows_are_rendered(mock_home: Path) -> None:
    home = mock_home.resolve()
    base = _fixed_model(home)
    compare = CompareReport(
        agent_a="a",
        agent_b="b",
        agent_a_name="Agent A",
        agent_b_name="Agent B",
        home=str(home),
        cwd=str(home),
        entries=(
            CompareEntry(name="shared-skill", relation=CompareRelation.SHARED),
            CompareEntry(
                name="diverged-skill",
                relation=CompareRelation.DIVERGED,
                path_a=str(home / "a"),
                path_b=str(home / "b"),
            ),
            CompareEntry(name="only-a-skill", relation=CompareRelation.ONLY_A, path_a="/a"),
        ),
        notes=("Could not verify a | b because both copies are unreadable.",),
    )
    model = assemble_report(base.scan, base.doctor, base.agents, compare, base.meta)
    text = markdown_text(model, paths.display)
    assert "diverged-skill" in text
    assert "only-a-skill" in text
    assert "shared-skill" not in text
    assert "Counts are derived" not in text
    assert "Could not verify a \\| b" in text
    assert "| shared | 1 |" in text


def _sparse_meta() -> ReportMeta:
    return ReportMeta(
        generated_at="2026-11-19T14:20:00+00:00",
        skill_lens_version="test",
        platform="TestPlatform-1.0",
    )


def test_renderer_handles_sparse_and_unknown_values() -> None:
    """Defensive branches: unknown skills, missing fields and no findings."""
    model = assemble_report(
        scan_payload={
            "home": None,
            "cwd": None,
            "summary": {"detected_agents": ["ghost", "other"]},
            "skills": [
                {
                    "name": "mystery",
                    "agents": ["ghost"],
                    "scope": "unmapped",
                    "variant_label": None,
                    "parse_status": None,
                    "health_status": "ok",
                    "description": None,
                    "canonical_path": None,
                }
            ],
        },
        doctor=DoctorReport(home="", cwd="", findings=()),
        agents=(),
        compare=None,
        meta=_sparse_meta(),
    )
    text = markdown_text(model, lambda value: value)
    assert "| ghost |  |  |  |  |" in text
    assert "| mystery | unmapped |" in text
    assert "No skills for this agent." in text
    assert "No findings." in text


def test_renderer_tolerates_a_malformed_scan_payload() -> None:
    for summary in ("not-a-dict", {"detected_agents": "not-a-list"}):
        model = assemble_report(
            scan_payload={
                "home": 1,
                "cwd": 2,
                "summary": summary,
                "skills": "not-a-list",
            },
            doctor=DoctorReport(home="", cwd="", findings=()),
            agents=(),
            compare=None,
            meta=_sparse_meta(),
        )
        text = markdown_text(model, lambda value: value)
        assert "No agents detected on this machine." in text
        assert "No skills detected on this machine." in text
        assert "| Canonical library (user-scope skills) |  |" in text


def test_compare_with_only_shared_entries_has_no_row_table() -> None:
    compare = CompareReport(
        agent_a="a",
        agent_b="b",
        agent_a_name="A",
        agent_b_name="B",
        home="/h",
        cwd="/h",
        entries=(CompareEntry(name="shared-skill", relation=CompareRelation.SHARED),),
    )
    model = assemble_report(
        scan_payload={"summary": {"detected_agents": []}, "skills": []},
        doctor=DoctorReport(home="", cwd="", findings=()),
        agents=(),
        compare=compare,
        meta=_sparse_meta(),
    )
    text = markdown_text(model, lambda value: value)
    assert "| shared | 1 |" in text
    assert "| Skill | Relation | Path A | Path B |" not in text
    assert "Notes:" not in text


# ---------------------------------------------------------------------------
# Read-only and one pass
# ---------------------------------------------------------------------------


def _tree(root: Path) -> list[tuple[str, bool, bytes, str | None]]:
    entries: list[tuple[str, bool, bytes, str | None]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries.append((relative, path.is_dir(), b"", os.readlink(path)))
        elif path.is_dir():
            entries.append((relative, True, b"", None))
        else:
            entries.append((relative, False, path.read_bytes(), None))
    return entries


def test_report_engines_never_modify_the_fixture(mock_home: Path) -> None:
    home = mock_home.resolve()
    build_acceptance_farm(home)
    before = _tree(home)
    build_report(home, home, generated_at=FIXED_GENERATED_AT, platform_text=FIXED_PLATFORM)
    after_build = _tree(home)
    run_report(cwd=home, generated_at=FIXED_GENERATED_AT, platform_text=FIXED_PLATFORM)
    after_run = _tree(home)
    assert before == after_build == after_run


def test_run_report_one_live_discovery_with_a_pair(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = mock_home.resolve()
    build_acceptance_farm(home)
    counts = _Counts()
    _arm_discovery_spies(monkeypatch, counts)
    model = run_report(
        cwd=home,
        compare_agents=("claude", "codex"),
        generated_at=FIXED_GENERATED_AT,
        platform_text=FIXED_PLATFORM,
    )
    assert counts.live == 1
    assert (counts.scanner, counts.doctor, counts.compare) == (0, 0, 0)
    assert model.compare is not None
    assert (
        model.to_dict()["scan"]
        == build_report(
            home,
            home,
            index=live_discovery(home),
            generated_at=FIXED_GENERATED_AT,
            platform_text=FIXED_PLATFORM,
        ).to_dict()["scan"]
    )


def test_build_report_supplied_index_makes_no_discovery_calls(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = mock_home.resolve()
    build_acceptance_farm(home)
    index = live_discovery(home)
    counts = _Counts()
    _arm_discovery_spies(monkeypatch, counts)
    model = build_report(
        home,
        home,
        compare_agents=("claude", "codex"),
        index=index,
        generated_at=FIXED_GENERATED_AT,
        platform_text=FIXED_PLATFORM,
    )
    assert (counts.live, counts.scanner, counts.doctor, counts.compare) == (0, 0, 0, 0)
    assert model.compare is not None


@pytest.mark.parametrize("pair", [("nope", "codex"), ("claude", "claude")])
def test_run_report_rejects_a_bad_pair_before_discovery(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch, pair: tuple[str, str]
) -> None:
    home = mock_home.resolve()
    build_acceptance_farm(home)
    counts = _Counts()
    _arm_discovery_spies(monkeypatch, counts)
    expected = KeyError if pair[0] == "nope" else ValueError
    with pytest.raises(expected):
        run_report(cwd=home, compare_agents=pair)
    assert (counts.live, counts.scanner, counts.doctor, counts.compare) == (0, 0, 0, 0)


def test_agents_payload_receives_registry_values_not_dict_keys(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = mock_home.resolve()
    build_acceptance_farm(home)
    received: list[object] = []
    original = report_module.agents_payload

    def spy(definitions):
        received.append(definitions)
        return original(definitions)

    monkeypatch.setattr(report_module, "agents_payload", spy)
    build_report(home, home, generated_at=FIXED_GENERATED_AT, platform_text=FIXED_PLATFORM)
    assert len(received) == 1
    assert not isinstance(received[0], dict)
    assert all(isinstance(item, AgentDefinition) for item in received[0])


# ---------------------------------------------------------------------------
# Parity with the single-command JSON payloads
# ---------------------------------------------------------------------------


def test_nested_payloads_are_byte_identical_to_command_json(mock_home: Path) -> None:
    home = mock_home.resolve()
    build_acceptance_farm(home)
    report = runner.invoke(app, ["report", "--sandbox", str(home), "--json"])
    assert report.exit_code == 0
    payload = json.loads(report.stdout)
    agents = runner.invoke(app, ["agents", "--json"])
    scan = runner.invoke(app, ["scan", "--sandbox", str(home), "--json"])
    doctor = runner.invoke(app, ["doctor", "--sandbox", str(home), "--json"])
    assert dumps(payload["agents"]) == dumps(json.loads(agents.stdout))
    assert dumps(payload["scan"]) == dumps(json.loads(scan.stdout))
    assert dumps(payload["doctor"]) == dumps(json.loads(doctor.stdout))
    assert payload["compare"] is None

    paired = runner.invoke(
        app,
        [
            "report",
            "--sandbox",
            str(home),
            "--json",
            "--agent",
            "claude",
            "--agent",
            "codex",
        ],
    )
    compare = runner.invoke(
        app,
        [
            "compare",
            "--sandbox",
            str(home),
            "--json",
            "--agent",
            "claude",
            "--agent",
            "codex",
        ],
    )
    assert dumps(json.loads(paired.stdout)["compare"]) == dumps(json.loads(compare.stdout))


# ---------------------------------------------------------------------------
# Registry-first import cycle probe
# ---------------------------------------------------------------------------


def test_registry_first_import_has_no_cycle() -> None:
    """models/ must not import the registry at runtime (TYPE_CHECKING only)."""
    import subprocess
    import sys

    code = (
        "import skill_lens.registry.loader\n"
        "import skill_lens.models.agents\n"
        "from skill_lens.models.agents import agents_payload\n"
        "from skill_lens.registry.loader import list_agents\n"
        "print(len(agents_payload(list_agents())))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "10"
