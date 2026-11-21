"""CLI tests: JSON output, exit codes, and the --sandbox contract."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

import skill_lens.core.report as report_module
from skill_lens.cli import app
from skill_lens.core import paths
from skill_lens.core.report import build_report
from skill_lens.models import dumps
from skill_lens.presentation.report import markdown_text
from tests.fixtures.builders import write_skill
from tests.fixtures.farm import build_acceptance_farm
from tests.fixtures.scenarios import build_scenario

_ANSI_ESCAPE = re.compile(rb"\x1b\[[0-9;]*m")


class _PlainRunner(CliRunner):
    """A CLI runner whose captured output has ANSI styling removed.

    Some environments force colour (CI exports FORCE_COLOR). Rich then styles
    parts of a rendered message -- an option name comes out as ``-`` plus an
    escape code plus ``-agent`` -- so a plain substring check for ``--agent``
    fails there while passing on a normal terminal. Stripping the escapes once,
    here, keeps every assertion in this file about the *text*, never the
    colouring, whatever shell runs the suite.
    """

    def invoke(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        result = super().invoke(*args, **kwargs)
        result.stdout_bytes = _ANSI_ESCAPE.sub(b"", result.stdout_bytes or b"")
        result.stderr_bytes = _ANSI_ESCAPE.sub(b"", result.stderr_bytes or b"")
        return result


runner = _PlainRunner()


def _make_skill(directory, name, description):
    from tests.fixtures.builders import make_skill

    return make_skill(directory, name, description)


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "skill-lens" in result.stdout


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("scan", "why", "agents", "diff"):
        assert command in result.stdout


def test_scan_json_is_valid(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    result = runner.invoke(app, ["scan", "--sandbox", str(mock_home), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["home"]
    assert isinstance(payload["skills"], list)


def test_scan_uses_sandbox_home(mock_home: Path) -> None:
    build_scenario("symlink_farm_multi_agent", mock_home)
    result = runner.invoke(app, ["scan", "--sandbox", str(mock_home), "--json"])
    payload = json.loads(result.stdout)
    names = {skill["name"] for skill in payload["skills"]}
    assert "shared" in names
    assert payload["summary"]["detected_agents"]


def test_why_json_matches_model(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    result = runner.invoke(
        app,
        [
            "why",
            "deploy",
            "--agent",
            "claude",
            "--sandbox",
            str(mock_home),
            "--cwd",
            str(mock_home / "project"),
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["headline"] == "ACTIVE"
    assert payload["agent"] == "claude"
    assert {c["state"] for c in payload["candidates"]} == {"ACTIVE", "SHADOWED"}


def test_why_unknown_agent_exits_2(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    result = runner.invoke(app, ["why", "deploy", "--agent", "nope", "--sandbox", str(mock_home)])
    assert result.exit_code == 2


def test_agents_command_lists_all() -> None:
    result = runner.invoke(app, ["agents", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    ids = {agent["id"] for agent in payload}
    assert {"claude", "codex", "pi"} <= ids


def test_scan_human_output_mentions_skill(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    result = runner.invoke(app, ["scan", "--sandbox", str(mock_home)])
    assert result.exit_code == 0
    assert "deploy" in result.stdout
    assert "Detected Agents" in result.stdout


def test_why_human_output_shows_rule(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    result = runner.invoke(
        app,
        [
            "why",
            "deploy",
            "--agent",
            "claude",
            "--sandbox",
            str(mock_home),
            "--cwd",
            str(mock_home / "project"),
        ],
    )
    assert result.exit_code == 0
    assert "claude_personal_beats_project" in result.stdout
    assert "SHADOWED" in result.stdout


def test_markup_is_escaped_in_output(mock_home: Path) -> None:
    """A skill description containing Rich markup must not be interpreted."""
    from tests.fixtures.builders import make_skill

    make_skill(mock_home / ".claude" / "skills" / "evil", "evil", "[bold red]PWNED[/]")
    result = runner.invoke(app, ["scan", "--sandbox", str(mock_home)])
    assert result.exit_code == 0
    # No exception raised and the literal text survives.
    assert "evil" in result.stdout


def test_why_defaults_to_the_terminal_folder(mock_home: Path, monkeypatch) -> None:
    """F-09: without ``--cwd``, the project inside the current folder is found.

    Defaulting to ``$HOME`` meant project roots were silently skipped, because
    there is no git boundary at the home directory.

    The sandbox stays on (so ``/etc/codex`` remains unread, per AGENTS.md rule
    2) and only ``terminal_cwd`` is redirected -- the CLI's job is to use it,
    and ``tests/test_paths.py`` pins what it returns in each mode.
    """
    from skill_lens.core import paths
    from tests.fixtures.builders import make_skill

    project = mock_home / "project"
    (project / ".git").mkdir(parents=True)
    make_skill(mock_home / ".claude" / "skills" / "deploy", "deploy", "Personal copy.")
    make_skill(
        project / ".claude" / "skills" / "deploy",
        "deploy",
        "Project copy.",
        body="# Instructions\n\nProject body.\n",
    )
    monkeypatch.setattr(paths, "terminal_cwd", lambda: project)
    result = runner.invoke(app, ["why", "deploy", "--agent", "claude", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["cwd"] == str(project)
    assert {c["installation"]["scope"] for c in payload["candidates"]} == {"user", "project"}


def test_sandbox_refuses_a_cwd_outside_itself(mock_home: Path, tmp_path: Path) -> None:
    """A sandboxed run must not be walked outside its own directory.

    Relative ``--cwd`` values were already clamped; an absolute one was not.
    """
    outside = tmp_path / "outside"
    (outside / ".agents" / "skills" / "leak").mkdir(parents=True)
    _make_skill(outside / ".agents" / "skills" / "leak", "leak", "Must not be seen.")

    result = runner.invoke(
        app, ["scan", "--sandbox", str(mock_home), "--cwd", str(outside), "--json"]
    )
    assert result.exit_code != 0
    assert "sandbox" in result.stdout.lower() + result.stderr.lower()


def test_sandbox_allows_a_cwd_inside_itself(mock_home: Path) -> None:
    """The normal ``--sandbox H --cwd H/project`` invocation still works."""
    from tests.fixtures.builders import make_skill

    project = mock_home / "project"
    (project / ".git").mkdir(parents=True)
    make_skill(project / ".claude" / "skills" / "deploy", "deploy", "Project copy.")
    result = runner.invoke(
        app,
        ["why", "deploy", "--agent", "claude", "--sandbox", str(mock_home), "--cwd", str(project)],
    )
    assert result.exit_code == 0
    assert "Project copy." in result.stdout


def test_sandbox_refuses_an_outside_cwd_for_why_too(mock_home: Path, tmp_path: Path) -> None:
    """The guard covers ``why`` as well as ``scan``."""
    outside = tmp_path / "outside"
    outside.mkdir()
    result = runner.invoke(
        app, ["why", "x", "--agent", "claude", "--sandbox", str(mock_home), "--cwd", str(outside)]
    )
    assert result.exit_code != 0
    assert "sandbox" in (result.stdout + result.stderr).lower()


def test_relative_cwd_stays_inside_the_sandbox(mock_home: Path, monkeypatch) -> None:
    """A relative ``--cwd`` is home-relative under a sandbox, not process-relative.

    It is clamped into the sandbox rather than refused, so the documented
    ``--sandbox H --cwd project`` form keeps working, and it can never be
    resolved against the folder the user happens to be standing in.
    """
    from tests.fixtures.builders import make_skill

    project = mock_home / "project"
    (project / ".git").mkdir(parents=True)
    make_skill(project / ".claude" / "skills" / "deploy", "deploy", "Project copy.")

    elsewhere = mock_home.parent / "unrelated"
    elsewhere.mkdir(exist_ok=True)
    monkeypatch.chdir(elsewhere)  # a real folder that is *not* the sandbox

    result = runner.invoke(
        app,
        ["scan", "--sandbox", str(mock_home), "--cwd", "project", "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["cwd"] == str(project)
    assert not payload["cwd"].startswith(str(elsewhere))


def test_sandboxed_run_cannot_escape_into_the_real_terminal_folder(
    mock_home: Path, monkeypatch, tmp_path: Path
) -> None:
    """F-09 safety: ``--sandbox`` must not read the folder the test runs from."""
    elsewhere = tmp_path / "elsewhere"
    (elsewhere / ".git").mkdir(parents=True)
    monkeypatch.chdir(elsewhere)
    result = runner.invoke(app, ["scan", "--sandbox", str(mock_home), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["cwd"] == str(mock_home.resolve())
    assert not str(payload["cwd"]).startswith(str(elsewhere))


def test_why_reports_a_missing_skill_clearly(mock_home: Path) -> None:
    """F-10: a name that exists nowhere must not read as 'outside the roots'."""
    from tests.fixtures.builders import make_skill

    make_skill(mock_home / ".claude" / "skills" / "deploy", "deploy", "Personal copy.")
    result = runner.invoke(
        app, ["why", "nope", "--agent", "claude", "--sandbox", str(mock_home), "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["found"] is False
    assert payload["candidates"] == []
    assert payload["notes"]

    human = runner.invoke(app, ["why", "nope", "--agent", "claude", "--sandbox", str(mock_home)])
    assert "No copies of this skill name" in human.stdout


# --- diff ------------------------------------------------------------------


def test_diff_json_is_the_model(mock_home: Path) -> None:
    build_scenario("variant_hash_detection", mock_home)
    result = runner.invoke(
        app, ["diff", "deploy", "--sandbox", str(mock_home), "--cwd", str(mock_home), "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["skill_name"] == "deploy"
    assert payload["found"] is True
    assert payload["baseline_path"].endswith(".claude/skills/deploy")
    assert payload["copies"][1]["variant_label"] == "B"
    assert payload["copies"][1]["files"][0]["hunks"][0]["lines"]


def test_diff_human_output_shows_the_unified_diff(mock_home: Path) -> None:
    build_scenario("variant_hash_detection", mock_home)
    result = runner.invoke(
        app, ["diff", "deploy", "--sandbox", str(mock_home), "--cwd", str(mock_home)]
    )
    assert result.exit_code == 0
    assert "Variant B" in result.stdout
    assert "@@ -1,7 +1,7 @@" in result.stdout
    assert "+description: Shared-library deploy." in result.stdout


def test_diff_without_differences_exits_zero(mock_home: Path) -> None:
    """One canonical copy is not an error (spec section 6, command 5)."""
    build_scenario("symlink_farm_multi_agent", mock_home)
    result = runner.invoke(
        app, ["diff", "shared", "--sandbox", str(mock_home), "--cwd", str(mock_home), "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload["copies"]) == 1
    assert payload["copies"][0]["files"] == []


def test_diff_missing_skill_exits_zero(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    result = runner.invoke(
        app, ["diff", "nope", "--sandbox", str(mock_home), "--cwd", str(mock_home), "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["found"] is False
    assert payload["notes"]

    human = runner.invoke(
        app, ["diff", "nope", "--sandbox", str(mock_home), "--cwd", str(mock_home)]
    )
    assert human.exit_code == 0
    assert "No copies of 'nope'" in human.stdout


def test_diff_refuses_a_cwd_outside_the_sandbox(mock_home: Path, tmp_path: Path) -> None:
    """The sandbox guard covers ``diff`` as well as ``scan`` and ``why``."""
    outside = tmp_path / "outside"
    outside.mkdir()
    result = runner.invoke(
        app, ["diff", "x", "--sandbox", str(mock_home), "--cwd", str(outside), "--json"]
    )
    assert result.exit_code != 0
    assert "sandbox" in (result.stdout + result.stderr).lower()


# --- Phase 4: doctor ---------------------------------------------------------


def test_doctor_json_is_the_model(mock_home: Path) -> None:
    """``doctor --json`` emits exactly DoctorReport.to_dict()."""
    _make_skill(mock_home / ".claude" / "skills" / "good", "good", "Fine.")
    result = runner.invoke(app, ["doctor", "--sandbox", str(mock_home), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert set(payload) == {"home", "cwd", "findings"}
    assert payload["home"] == str(mock_home)


def test_doctor_exits_zero_even_with_findings(mock_home: Path) -> None:
    """Running is success; the findings are data, not exit codes (spec rule)."""
    broken = mock_home / ".claude" / "skills" / "broken"
    broken.mkdir(parents=True)
    (broken / "SKILL.md").write_text("---\nname: broken\ndescription: [\n---\n", "utf-8")
    result = runner.invoke(app, ["doctor", "--sandbox", str(mock_home)])
    assert result.exit_code == 0
    assert "broken" in result.stdout


def test_doctor_rejects_an_outside_cwd(mock_home: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    result = runner.invoke(app, ["doctor", "--sandbox", str(mock_home), "--cwd", str(outside)])
    assert result.exit_code != 0
    assert "sandbox" in (result.stdout + result.stderr).lower()


# --- Phase 4: compare --------------------------------------------------------


def test_compare_json_is_the_model(mock_home: Path) -> None:
    _make_skill(mock_home / ".claude" / "skills" / "solo", "solo", "One agent only.")
    result = runner.invoke(
        app,
        ["compare", "--agent", "claude", "--agent", "codex", "--sandbox", str(mock_home), "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["agent_a"] == "claude"
    assert payload["agent_b"] == "codex"
    entry = next(e for e in payload["entries"] if e["name"] == "solo")
    assert entry["relation"] == "only_a"


def test_compare_requires_exactly_two_agents(mock_home: Path) -> None:
    one = runner.invoke(app, ["compare", "--agent", "claude", "--sandbox", str(mock_home)])
    assert one.exit_code == 2
    assert "--agent" in (one.stdout + one.stderr)
    three = runner.invoke(
        app,
        [
            "compare",
            "--agent",
            "claude",
            "--agent",
            "codex",
            "--agent",
            "pi",
            "--sandbox",
            str(mock_home),
        ],
    )
    assert three.exit_code == 2
    zero = runner.invoke(app, ["compare", "--sandbox", str(mock_home)])
    assert zero.exit_code == 2


def test_compare_unknown_agent_exits_2(mock_home: Path) -> None:
    result = runner.invoke(
        app, ["compare", "--agent", "claude", "--agent", "nope", "--sandbox", str(mock_home)]
    )
    assert result.exit_code == 2
    assert "unknown agent 'nope'" in (result.stdout + result.stderr)
    assert "Known agents:" in (result.stdout + result.stderr)


def test_compare_same_agent_exits_2(mock_home: Path) -> None:
    result = runner.invoke(
        app, ["compare", "--agent", "claude", "--agent", "claude", "--sandbox", str(mock_home)]
    )
    assert result.exit_code == 2
    assert "cannot compare agent 'claude' with itself" in (result.stdout + result.stderr)

    json_res = runner.invoke(
        app,
        [
            "compare",
            "--agent",
            "claude",
            "--agent",
            "claude",
            "--sandbox",
            str(mock_home),
            "--json",
        ],
    )
    assert json_res.exit_code == 2
    assert json_res.stdout == ""
    assert "cannot compare agent 'claude' with itself" in json_res.stderr


def test_why_unknown_agent_with_markup_tokens_exits_2_no_crash(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    result = runner.invoke(app, ["why", "deploy", "--agent", "[/]", "--sandbox", str(mock_home)])
    assert result.exit_code == 2
    assert "Traceback" not in result.stderr
    assert "MarkupError" not in result.stderr
    assert "unknown agent '[/]'" in (result.stdout + result.stderr)


def test_compare_unknown_agent_with_markup_tokens_exits_2_no_crash(mock_home: Path) -> None:
    result = runner.invoke(
        app, ["compare", "--agent", "[/]", "--agent", "claude", "--sandbox", str(mock_home)]
    )
    assert result.exit_code == 2
    assert "Traceback" not in result.stderr
    assert "MarkupError" not in result.stderr
    assert "unknown agent '[/]'" in (result.stdout + result.stderr)


def test_compare_human_output_names_the_agents(mock_home: Path) -> None:
    library = mock_home / ".agents" / "skills" / "shared"
    _make_skill(library, "shared", "Shared library.")
    from tests.fixtures.builders import relative_symlink

    relative_symlink(library, mock_home / ".claude" / "skills" / "shared")
    result = runner.invoke(
        app, ["compare", "--agent", "claude", "--agent", "codex", "--sandbox", str(mock_home)]
    )
    assert result.exit_code == 0
    assert "shared" in result.stdout


def test_help_lists_the_phase4_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert "doctor" in result.stdout
    assert "compare" in result.stdout


# ---------------------------------------------------------------------------
# report (issue #6)
# ---------------------------------------------------------------------------

_FIXED_NOW = datetime(2026, 11, 19, 14, 20, tzinfo=UTC)


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):  # type: ignore[no-untyped-def]
        return _FIXED_NOW


def _freeze_report_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(report_module, "datetime", _FrozenDatetime)


def _scan_tree(root: Path) -> list[tuple[str, str]]:
    return [
        (path.relative_to(root).as_posix(), path.read_bytes().hex() if path.is_file() else "dir")
        for path in sorted(root.rglob("*"))
    ]


def test_report_default_markdown_is_plain_and_unwrapped(mock_home: Path) -> None:
    build_acceptance_farm(mock_home)
    description = "A deliberately long description " + "x" * 140
    _make_skill(mock_home / ".claude" / "skills" / "longdesc", "longdesc", description)
    result = runner.invoke(app, ["report", "--sandbox", str(mock_home)])
    assert result.exit_code == 0
    assert result.stdout.startswith("# Skill Lens Report\n")
    assert result.stdout.endswith("\n") and not result.stdout.endswith("\n\n")
    assert "\x1b" not in result.stdout
    assert description in result.stdout
    line = next(line for line in result.stdout.splitlines() if description in line)
    assert len(line) > 100
    assert line.count("|") >= 7


def test_report_explicit_format_md_matches_the_default(mock_home: Path) -> None:
    build_acceptance_farm(mock_home)
    result = runner.invoke(app, ["report", "--sandbox", str(mock_home), "--format", "md"])
    assert result.exit_code == 0
    assert result.stdout.startswith("# Skill Lens Report")


def test_report_json_is_canonical_and_overrides_format(mock_home: Path) -> None:
    build_acceptance_farm(mock_home)
    result = runner.invoke(app, ["report", "--sandbox", str(mock_home), "--json", "--format", "md"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["compare"] is None
    assert result.stdout_bytes == dumps(payload).encode("utf-8") + b"\n"
    assert b"\x1b" not in result.stdout_bytes


def test_report_output_writes_exact_stdout_bytes(
    mock_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_acceptance_farm(mock_home)
    _freeze_report_clock(monkeypatch)
    stdout_run = runner.invoke(app, ["report", "--sandbox", str(mock_home)])
    assert stdout_run.exit_code == 0
    target = tmp_path / "outside.md"
    file_run = runner.invoke(app, ["report", "--sandbox", str(mock_home), "--output", str(target)])
    assert file_run.exit_code == 0
    assert file_run.stdout_bytes == b""
    assert target.read_bytes() == stdout_run.stdout_bytes
    assert target.read_bytes().endswith(b"\n")
    assert not target.read_bytes().endswith(b"\n\n")


def test_report_json_output_writes_canonical_bytes(
    mock_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_acceptance_farm(mock_home)
    _freeze_report_clock(monkeypatch)
    target = tmp_path / "outside.json"
    result = runner.invoke(
        app,
        ["report", "--sandbox", str(mock_home), "--json", "--output", str(target)],
    )
    assert result.exit_code == 0
    assert result.stdout_bytes == b""
    text = target.read_text(encoding="utf-8")
    assert text == dumps(json.loads(text)) + "\n"
    assert text.endswith("\n") and not text.endswith("\n\n")


def test_report_rejects_a_non_md_format(mock_home: Path) -> None:
    result = runner.invoke(app, ["report", "--sandbox", str(mock_home), "--format", "html"])
    assert result.exit_code == 2
    assert "only 'md' is supported" in result.stderr


def test_report_agent_cardinality_sentence_is_exact(mock_home: Path) -> None:
    for count in (1, 3):
        agents = ["claude", "codex", "pi"][:count]
        args = ["report", "--sandbox", str(mock_home)]
        for agent in agents:
            args.extend(["--agent", agent])
        result = runner.invoke(app, args)
        assert result.exit_code == 2
        normalized = " ".join(re.sub(r"[│╭╮╰╯─]", " ", result.stderr).split())
        assert (
            "pass --agent zero times (no compare) or exactly twice "
            f"(two agents to compare); got {count}."
        ) in normalized


def test_report_zero_and_two_agents_are_legal(mock_home: Path) -> None:
    build_acceptance_farm(mock_home)
    zero = runner.invoke(app, ["report", "--sandbox", str(mock_home), "--json"])
    assert zero.exit_code == 0
    assert json.loads(zero.stdout)["compare"] is None
    two = runner.invoke(
        app,
        [
            "report",
            "--sandbox",
            str(mock_home),
            "--json",
            "--agent",
            "claude",
            "--agent",
            "codex",
        ],
    )
    assert two.exit_code == 0
    assert json.loads(two.stdout)["compare"] is not None


def test_report_unknown_and_duplicate_agents_use_the_shared_sentences(mock_home: Path) -> None:
    unknown = runner.invoke(
        app,
        ["report", "--sandbox", str(mock_home), "--agent", "nope", "--agent", "claude"],
    )
    assert unknown.exit_code == 2
    assert "Error: unknown agent 'nope'. Known agents:" in unknown.stderr
    duplicate = runner.invoke(
        app,
        ["report", "--sandbox", str(mock_home), "--agent", "claude", "--agent", "claude"],
    )
    assert duplicate.exit_code == 2
    assert "Error: cannot compare agent 'claude' with itself" in duplicate.stderr


def test_report_output_refusals(mock_home: Path, tmp_path: Path) -> None:
    existing = tmp_path / "existing.md"
    existing.write_text("keep me", encoding="utf-8")
    refused = runner.invoke(app, ["report", "--sandbox", str(mock_home), "--output", str(existing)])
    assert refused.exit_code == 2
    assert "already exists" in refused.stderr
    assert existing.read_text(encoding="utf-8") == "keep me"

    directory = tmp_path / "folder"
    directory.mkdir()
    refused = runner.invoke(
        app, ["report", "--sandbox", str(mock_home), "--output", str(directory)]
    )
    assert refused.exit_code == 2
    assert "is a directory" in refused.stderr
    assert list(directory.iterdir()) == []

    missing = tmp_path / "missing" / "report.md"
    refused = runner.invoke(app, ["report", "--sandbox", str(mock_home), "--output", str(missing)])
    assert refused.exit_code == 2
    assert "does not exist" in refused.stderr
    assert not missing.parent.exists()


def test_report_write_failure_exits_2(
    mock_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_write(self: Path, *args: object, **kwargs: object) -> int:
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    result = runner.invoke(
        app, ["report", "--sandbox", str(mock_home), "--output", str(tmp_path / "out.md")]
    )
    assert result.exit_code == 2
    assert "could not write the report: disk full" in result.stderr


def test_report_refusals_happen_before_discovery(
    mock_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Path | None] = []

    def spy(cwd=None, registry=None, *, cancelled=None):
        calls.append(cwd)
        raise AssertionError("discovery must not run for a refused invocation")

    monkeypatch.setattr(report_module, "live_discovery", spy)
    existing = tmp_path / "existing.md"
    existing.write_text("x", encoding="utf-8")
    directory = tmp_path / "folder"
    directory.mkdir()
    invocations = [
        ["--format", "html"],
        ["--agent", "claude"],
        ["--agent", "nope", "--agent", "claude"],
        ["--agent", "claude", "--agent", "claude"],
        ["--output", str(existing)],
        ["--output", str(directory)],
        ["--output", str(tmp_path / "missing" / "out.md")],
    ]
    for extra in invocations:
        result = runner.invoke(app, ["report", "--sandbox", str(mock_home), *extra])
        assert result.exit_code == 2, extra
    assert calls == []


def test_report_sandbox_clamps_reads_but_not_the_output(mock_home: Path, tmp_path: Path) -> None:
    build_acceptance_farm(mock_home)
    escaped = runner.invoke(app, ["report", "--sandbox", str(mock_home), "--cwd", "/etc"])
    assert escaped.exit_code == 2
    assert "--cwd must stay inside --sandbox" in escaped.stderr

    target = tmp_path / "outside-the-sandbox.md"
    result = runner.invoke(
        app, ["report", "--sandbox", str(mock_home), "--json", "--output", str(target)]
    )
    assert result.exit_code == 0
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["scan"]["home"] == str(mock_home.resolve())


def test_report_exits_zero_even_with_findings(mock_home: Path) -> None:
    build_scenario("malformed_frontmatter", mock_home)
    result = runner.invoke(app, ["report", "--sandbox", str(mock_home)])
    assert result.exit_code == 0
    assert "## Doctor findings" in result.stdout
    assert "malformed" in result.stdout or "invalid" in result.stdout


def test_report_is_read_only_around_the_fixture(mock_home: Path, tmp_path: Path) -> None:
    build_acceptance_farm(mock_home)
    before = _scan_tree(mock_home)
    result = runner.invoke(app, ["report", "--sandbox", str(mock_home)])
    assert result.exit_code == 0
    assert _scan_tree(mock_home) == before

    target = tmp_path / "outside-the-sandbox.md"
    before_outside = set(tmp_path.iterdir())
    result = runner.invoke(app, ["report", "--sandbox", str(mock_home), "--output", str(target)])
    assert result.exit_code == 0
    assert _scan_tree(mock_home) == before
    assert set(tmp_path.iterdir()) - before_outside == {target}
    assert target.read_bytes().startswith(b"# Skill Lens Report")


def _write_shortcode_skill(home: Path) -> None:
    """A valid skill whose description carries Rich shortcodes and a literal tab."""
    document = (
        "---\n"
        "name: shortcodes\n"
        "description: |-\n"
        "  Reaches :100: coverage and :smile: here\tand tab\n"
        "---\n"
        "# Instructions\n\n"
        "Do the thing.\n"
    )
    write_skill(home / ".claude" / "skills" / "shortcodes", document)


def test_report_stdout_bytes_equal_file_with_shortcodes_and_tab(
    mock_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rich must not rewrite report bytes: no emoji substitution, no tab expansion."""
    home = mock_home.resolve()
    build_acceptance_farm(home)
    _write_shortcode_skill(home)
    _freeze_report_clock(monkeypatch)
    monkeypatch.setattr(report_module.platform, "platform", lambda: "TestPlatform-1.0")
    model = build_report(
        home,
        home,
        generated_at=_FIXED_NOW,
        platform_text="TestPlatform-1.0",
    )
    raw_runner = CliRunner()
    expected_markdown = markdown_text(model, paths.display).encode("utf-8") + b"\n"

    stdout_run = raw_runner.invoke(app, ["report", "--sandbox", str(home)])
    assert stdout_run.exit_code == 0
    markdown_file = tmp_path / "shortcodes.md"
    file_run = raw_runner.invoke(
        app, ["report", "--sandbox", str(home), "--output", str(markdown_file)]
    )
    assert file_run.exit_code == 0
    assert file_run.stdout_bytes == b""
    assert stdout_run.stdout_bytes == expected_markdown
    assert markdown_file.read_bytes() == expected_markdown
    assert b"\x1b" not in stdout_run.stdout_bytes
    assert b":100:" in stdout_run.stdout_bytes
    assert b":smile:" in stdout_run.stdout_bytes
    assert b"\t" in stdout_run.stdout_bytes
    assert "💯".encode() not in stdout_run.stdout_bytes
    assert "😄".encode() not in stdout_run.stdout_bytes
    observed = next(line for line in stdout_run.stdout_bytes.splitlines() if b"Reaches" in line)
    assert len(observed) > 100, "the >80-column row must stay on one line"

    expected_json = dumps(model.to_dict()).encode("utf-8") + b"\n"
    json_stdout = raw_runner.invoke(app, ["report", "--sandbox", str(home), "--json"])
    assert json_stdout.exit_code == 0
    json_file = tmp_path / "shortcodes.json"
    json_file_run = raw_runner.invoke(
        app,
        ["report", "--sandbox", str(home), "--json", "--output", str(json_file)],
    )
    assert json_file_run.exit_code == 0
    assert json_file_run.stdout_bytes == b""
    assert json_stdout.stdout_bytes == expected_json
    assert json_file.read_bytes() == expected_json
    assert b":100:" in json_stdout.stdout_bytes
    assert b"\\t" in json_stdout.stdout_bytes
    assert "💯".encode() not in json_stdout.stdout_bytes
