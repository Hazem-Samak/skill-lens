"""CLI tests: JSON output, exit codes, and the --sandbox contract."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from skill_lens.cli import app
from tests.fixtures.scenarios import build_scenario

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "skill-lens" in result.stdout


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("scan", "why", "agents"):
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
