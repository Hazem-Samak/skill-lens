"""CLI tests: JSON output, exit codes, and the --sandbox contract."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from skill_lens.cli import app
from tests.fixtures.scenarios import build_scenario

runner = CliRunner()


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
