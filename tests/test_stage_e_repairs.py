"""Stage E focused regression tests (F08, F09, F14, R03).

Covers:
- F08: Explicit interactive launch requires interactive stdin/stdout,
       fails fast with exit 2 on pipes, keeps bare fallback and missing extra.
- F09: Shared distinct agent validation across build_compare_report, run_compare,
       and snapshot_compare, validating before discovery/IO and exiting 2 with empty stdout in JSON.
- F14: Literal CLI error messages without Rich markup crashes on user tokens like [/].
- R03: Event loop compatibility without deprecated asyncio.get_event_loop_policy,
       preserving non-running borrowed loops, failure restoration, and clean shutdown.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import types
import warnings
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from textual.pilot import Pilot
from typer.testing import CliRunner

import skill_lens.cli as cli
import skill_lens.tui as tui
from skill_lens.cli import app
from skill_lens.core import paths
from skill_lens.core.compare import build_compare_report, run_compare, validate_compare_agents
from skill_lens.core.exitcodes import ExitCode
from skill_lens.core.snapshot import capture_session, snapshot_compare
from skill_lens.models.enums import CompareRelation
from skill_lens.registry.loader import load_registry
from skill_lens.tui.app import SkillLensApp
from tests.fixtures.builders import make_skill
from tests.fixtures.scenarios import build_scenario

runner = CliRunner()


def _install_fake_tui(monkeypatch: pytest.MonkeyPatch, runner_func: Any) -> types.ModuleType:
    fake_mod = types.ModuleType("skill_lens.tui")
    fake_mod.run = runner_func  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "skill_lens.tui", fake_mod)
    return fake_mod


# =============================================================================
# F08: Explicit TUI launch requires interactive terminal streams
# =============================================================================


@pytest.mark.parametrize(
    "stdin_tty,stdout_tty",
    [
        (False, True),
        (True, False),
        (False, False),
    ],
)
def test_f08_explicit_tui_noninteractive_streams_exits_2_no_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stdin_tty: bool,
    stdout_tty: bool,
) -> None:
    called = False

    def fake_runner(home: Path, cwd: Path, *, max_snapshot_bytes: Any = None) -> int:
        nonlocal called
        called = True
        return 0

    def fake_isatty(stream: object) -> bool:
        if stream is sys.stdin:
            return stdin_tty
        if stream is sys.stdout:
            return stdout_tty
        return False

    monkeypatch.setattr(cli, "_stream_isatty", fake_isatty)
    monkeypatch.setattr(cli, "_is_textual_available", lambda: True)
    _install_fake_tui(monkeypatch, fake_runner)

    result = runner.invoke(app, ["tui", "--sandbox", str(tmp_path)])
    assert result.exit_code == int(ExitCode.USAGE)
    assert "Error: The terminal UI requires an interactive terminal." in result.stderr
    assert not called


def test_f08_explicit_tui_both_interactive_launches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def fake_runner(home: Path, cwd: Path, *, max_snapshot_bytes: Any = None) -> int:
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(cli, "_stream_isatty", lambda s: True)
    monkeypatch.setattr(cli, "_is_textual_available", lambda: True)
    _install_fake_tui(monkeypatch, fake_runner)

    result = runner.invoke(app, ["tui", "--sandbox", str(tmp_path)])
    assert result.exit_code == 0
    assert called is True


def test_f08_explicit_tui_missing_textual_precedes_stream_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def fake_runner(home: Path, cwd: Path, *, max_snapshot_bytes: Any = None) -> int:
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(cli, "_stream_isatty", lambda s: False)
    monkeypatch.setattr(cli, "_is_textual_available", lambda: False)
    _install_fake_tui(monkeypatch, fake_runner)

    result = runner.invoke(app, ["tui", "--sandbox", str(tmp_path)])
    assert result.exit_code == int(ExitCode.USAGE)
    assert "Error: The terminal UI requires 'skill-lens-cli[tui]'." in result.stderr
    assert "pip install 'skill-lens-cli[tui]'" in result.stderr
    assert not called


def test_f08_bare_noninteractive_fallback_prints_help(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "_stream_isatty", lambda s: False)
    monkeypatch.setattr(cli, "_is_textual_available", lambda: True)

    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Usage: " in result.stdout
    assert "Tip:" not in result.stdout


def test_f08_bare_plain_flag_prints_help(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "_stream_isatty", lambda s: True)
    monkeypatch.setattr(cli, "_is_textual_available", lambda: True)

    result = runner.invoke(app, ["--plain"])
    assert result.exit_code == 0
    assert "Usage: " in result.stdout


def test_f08_bounded_subprocess_timeout(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "skill_lens.cli", "tui", "--sandbox", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=5.0,
    )
    assert proc.returncode == 2
    assert "Error: The terminal UI requires an interactive terminal." in proc.stderr
    assert "Traceback" not in proc.stderr


# =============================================================================
# F09: Shared validation requiring two distinct known agents
# =============================================================================


def test_f09_validate_compare_agents_helper() -> None:
    registry = load_registry()
    def_a, def_b = validate_compare_agents("claude", "codex", registry)
    assert def_a.id == "claude"
    assert def_b.id == "codex"

    with pytest.raises(KeyError, match="unknown agent 'nonexistent'"):
        validate_compare_agents("nonexistent", "codex", registry)

    with pytest.raises(KeyError, match="unknown agent 'nonexistent'"):
        validate_compare_agents("claude", "nonexistent", registry)

    with pytest.raises(ValueError, match="cannot compare agent 'claude' with itself"):
        validate_compare_agents("claude", "claude", registry)


def test_f09_build_compare_report_same_agent_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot compare agent 'claude' with itself"):
        build_compare_report("claude", "claude", tmp_path, tmp_path)


def test_f09_run_compare_same_agent_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot compare agent 'claude' with itself"):
        run_compare("claude", "claude", cwd=tmp_path)


def test_f09_snapshot_compare_same_agent_raises(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    snapshot = capture_session(generation=1, home=mock_home, cwd=mock_home)
    with pytest.raises(ValueError, match="cannot compare agent 'claude' with itself"):
        snapshot_compare(snapshot, "claude", "claude")


def test_f09_validation_happens_before_discovery_and_io(tmp_path: Path) -> None:
    with (
        patch(
            "skill_lens.core.compare.live_discovery",
            side_effect=AssertionError("live_discovery must not be called"),
        ),
        patch(
            "skill_lens.core.compare.discover",
            side_effect=AssertionError("discover must not be called"),
        ),
    ):
        with pytest.raises(ValueError, match="cannot compare agent 'claude' with itself"):
            run_compare("claude", "claude", cwd=tmp_path)
        with pytest.raises(ValueError, match="cannot compare agent 'claude' with itself"):
            build_compare_report("claude", "claude", tmp_path, tmp_path)


def test_f09_cli_compare_same_agent_human_mode_exits_2(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["compare", "--agent", "claude", "--agent", "claude", "--sandbox", str(tmp_path)],
    )
    assert result.exit_code == 2
    assert "Error: cannot compare agent 'claude' with itself" in result.stderr
    assert "Traceback" not in result.stderr


def test_f09_cli_compare_same_agent_json_mode_exits_2_empty_stdout(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["compare", "--agent", "claude", "--agent", "claude", "--sandbox", str(tmp_path), "--json"],
    )
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "Error: cannot compare agent 'claude' with itself" in result.stderr
    assert "Traceback" not in result.stderr


def test_f09_reversed_comparisons_retain_shapes_and_mirrors(mock_home: Path) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    # Exercise all mirror relations with guaranteed non-empty reports
    make_skill(mock_home / ".codex" / "skills" / "format", "format", "Codex format helper.")
    make_skill(mock_home / ".claude" / "skills" / "shared-tool", "shared-tool", "Shared tool.")
    make_skill(mock_home / ".codex" / "skills" / "shared-tool", "shared-tool", "Shared tool.")
    make_skill(
        mock_home / ".claude" / "skills" / "diverged-tool",
        "diverged-tool",
        "Claude diff.",
        body="# Instructions\n\nClaude variant\n",
    )
    make_skill(
        mock_home / ".codex" / "skills" / "diverged-tool",
        "diverged-tool",
        "Codex diff.",
        body="# Instructions\n\nCodex variant\n",
    )

    project_cwd = mock_home / "project"
    report_ab = run_compare("claude", "codex", cwd=project_cwd)
    report_ba = run_compare("codex", "claude", cwd=project_cwd)

    assert report_ab.agent_a == "claude" and report_ab.agent_b == "codex"
    assert report_ba.agent_a == "codex" and report_ba.agent_b == "claude"
    assert len(report_ab.entries) > 0
    assert len(report_ba.entries) > 0

    names_ab = [e.name for e in report_ab.entries]
    names_ba = [e.name for e in report_ba.entries]
    assert names_ab == names_ba

    relations_seen: set[CompareRelation] = set()
    for entry_ab, entry_ba in zip(report_ab.entries, report_ba.entries, strict=True):
        assert entry_ab.name == entry_ba.name
        relations_seen.add(entry_ab.relation)
        if entry_ab.relation is CompareRelation.SHARED:
            assert entry_ba.relation is CompareRelation.SHARED
            assert entry_ab.canonical_a == entry_ba.canonical_b
            assert entry_ab.canonical_b == entry_ba.canonical_a
        elif entry_ab.relation is CompareRelation.ONLY_A:
            assert entry_ba.relation is CompareRelation.ONLY_B
        elif entry_ab.relation is CompareRelation.ONLY_B:
            assert entry_ba.relation is CompareRelation.ONLY_A
        elif entry_ab.relation is CompareRelation.DIVERGED:
            assert entry_ba.relation is CompareRelation.DIVERGED

    assert CompareRelation.SHARED in relations_seen
    assert CompareRelation.ONLY_A in relations_seen
    assert CompareRelation.ONLY_B in relations_seen
    assert CompareRelation.DIVERGED in relations_seen


# =============================================================================
# F14: Literal CLI errors without Rich markup interpretation
# =============================================================================


@pytest.mark.parametrize(
    "token",
    [
        "[/]",
        "[/red]",
        "[bold red]",
        "[link=http://evil.com]pwn[/link]",
        "brackets[inside]here",
        "[[double]]",
    ],
)
def test_f14_why_unknown_agent_markup_tokens_rendered_literally(
    tmp_path: Path,
    token: str,
) -> None:
    build_scenario("claude_personal_beats_project", tmp_path)
    result = runner.invoke(
        app,
        ["why", "deploy", "--agent", token, "--sandbox", str(tmp_path)],
    )
    assert result.exit_code == 2
    assert "Traceback" not in result.stderr
    assert "MarkupError" not in result.stderr
    assert f"Error: unknown agent '{token}'. Known agents:" in result.stderr


@pytest.mark.parametrize(
    "token",
    [
        "[/]",
        "[bold red]",
    ],
)
def test_f14_why_unknown_agent_json_mode_unpolluted_stdout(
    tmp_path: Path,
    token: str,
) -> None:
    build_scenario("claude_personal_beats_project", tmp_path)
    result = runner.invoke(
        app,
        ["why", "deploy", "--agent", token, "--sandbox", str(tmp_path), "--json"],
    )
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert "MarkupError" not in result.stderr
    assert f"Error: unknown agent '{token}'. Known agents:" in result.stderr


@pytest.mark.parametrize(
    "token",
    [
        "[/]",
        "[/red]",
        "[bold red]",
        "[link=http://evil.com]pwn[/link]",
        "brackets[inside]here",
    ],
)
def test_f14_compare_unknown_agent_first_position_markup_tokens_literal(
    tmp_path: Path,
    token: str,
) -> None:
    result = runner.invoke(
        app,
        ["compare", "--agent", token, "--agent", "claude", "--sandbox", str(tmp_path)],
    )
    assert result.exit_code == 2
    assert "Traceback" not in result.stderr
    assert "MarkupError" not in result.stderr
    assert f"Error: unknown agent '{token}'. Known agents:" in result.stderr


def test_f14_compare_unknown_agent_second_position_markup_tokens_literal(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        ["compare", "--agent", "claude", "--agent", "[/]", "--sandbox", str(tmp_path)],
    )
    assert result.exit_code == 2
    assert "Traceback" not in result.stderr
    assert "MarkupError" not in result.stderr
    assert "Error: unknown agent '[/]'. Known agents:" in result.stderr


def test_f14_compare_unknown_agent_json_mode_unpolluted_stdout(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        ["compare", "--agent", "[/]", "--agent", "claude", "--sandbox", str(tmp_path), "--json"],
    )
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert "MarkupError" not in result.stderr
    assert "Error: unknown agent '[/]'. Known agents:" in result.stderr


# =============================================================================
# R03: Event loop compatibility without deprecated asyncio.get_event_loop_policy
# =============================================================================


def test_r03_tui_run_no_prior_loop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    build_scenario("claude_personal_beats_project", tmp_path)
    monkeypatch.setattr(paths, "home", lambda: tmp_path)

    created_loops: list[asyncio.AbstractEventLoop] = []
    real_new_event_loop = asyncio.new_event_loop

    def spy_new_event_loop() -> asyncio.AbstractEventLoop:
        loop = real_new_event_loop()
        created_loops.append(loop)
        return loop

    monkeypatch.setattr(asyncio, "new_event_loop", spy_new_event_loop)
    asyncio.set_event_loop(None)

    async def auto_quit(pilot: Pilot) -> None:
        await pilot.pause()
        await pilot.press("q")

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        code = tui.run(tmp_path, tmp_path, headless=True, auto_pilot=auto_quit)

    assert code == 0
    policy_warnings = [w for w in captured if "get_event_loop_policy" in str(w.message)]
    assert policy_warnings == []

    # Owned loop was closed
    assert len(created_loops) == 1
    assert created_loops[0].is_closed()

    # After run, no loop remains active in thread
    with pytest.raises(RuntimeError, match="no current event loop"):
        asyncio.get_event_loop()


def test_r03_tui_run_preserves_and_restores_borrowed_non_running_loop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    build_scenario("claude_personal_beats_project", tmp_path)
    monkeypatch.setattr(paths, "home", lambda: tmp_path)

    borrowed_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(borrowed_loop)
    try:

        async def auto_quit(pilot: Pilot) -> None:
            await pilot.pause()
            await pilot.press("q")

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            code = tui.run(tmp_path, tmp_path, headless=True, auto_pilot=auto_quit)

        assert code == 0
        policy_warnings = [w for w in captured if "get_event_loop_policy" in str(w.message)]
        assert policy_warnings == []

        # Exact borrowed loop is restored!
        current = asyncio.get_event_loop()
        assert current is borrowed_loop
        assert not current.is_closed()
        assert not current.is_running()
    finally:
        borrowed_loop.close()
        asyncio.set_event_loop(None)


def test_r03_tui_run_handles_closed_prior_loop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    build_scenario("claude_personal_beats_project", tmp_path)
    monkeypatch.setattr(paths, "home", lambda: tmp_path)

    closed_loop = asyncio.new_event_loop()
    closed_loop.close()
    asyncio.set_event_loop(closed_loop)

    created_loops: list[asyncio.AbstractEventLoop] = []
    real_new_event_loop = asyncio.new_event_loop

    def spy_new_event_loop() -> asyncio.AbstractEventLoop:
        loop = real_new_event_loop()
        created_loops.append(loop)
        return loop

    monkeypatch.setattr(asyncio, "new_event_loop", spy_new_event_loop)

    try:

        async def auto_quit(pilot: Pilot) -> None:
            await pilot.pause()
            await pilot.press("q")

        code = tui.run(tmp_path, tmp_path, headless=True, auto_pilot=auto_quit)
        assert code == 0

        # Owned loop was closed
        assert len(created_loops) == 1
        assert created_loops[0].is_closed()

        # Closed prior loop is not restored as active loop, and no loop remains set
        with pytest.raises(RuntimeError, match="no current event loop"):
            asyncio.get_event_loop()
    finally:
        asyncio.set_event_loop(None)


def test_r03_tui_run_constructor_failure_restores_borrowed_loop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    borrowed_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(borrowed_loop)

    try:

        def exploding_init(self: Any, *args: Any, **kwargs: Any) -> None:
            raise ValueError("Simulated constructor failure")

        monkeypatch.setattr(SkillLensApp, "__init__", exploding_init)

        with pytest.raises(ValueError, match="Simulated constructor failure"):
            tui.run(tmp_path, tmp_path, headless=True)

        current = asyncio.get_event_loop()
        assert current is borrowed_loop
        assert not current.is_closed()
    finally:
        borrowed_loop.close()
        asyncio.set_event_loop(None)


def test_r03_tui_run_cleanup_failure_restores_borrowed_loop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    build_scenario("claude_personal_beats_project", tmp_path)
    monkeypatch.setattr(paths, "home", lambda: tmp_path)

    borrowed_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(borrowed_loop)

    try:

        def exploding_all_tasks(loop: Any) -> Any:
            raise RuntimeError("Simulated cleanup fault")

        monkeypatch.setattr(asyncio, "all_tasks", exploding_all_tasks)

        async def auto_quit(pilot: Pilot) -> None:
            await pilot.pause()
            await pilot.press("q")

        with pytest.raises(RuntimeError, match="Simulated cleanup fault"):
            tui.run(tmp_path, tmp_path, headless=True, auto_pilot=auto_quit)

        current = asyncio.get_event_loop()
        assert current is borrowed_loop
        assert not current.is_closed()
    finally:
        borrowed_loop.close()
        asyncio.set_event_loop(None)


def test_r03_tui_run_inside_running_loop_raises_and_preserves_running_loop(
    tmp_path: Path,
) -> None:
    async def run_inside() -> None:
        running = asyncio.get_running_loop()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            with pytest.raises(RuntimeError, match="Cannot run the event loop while another loop"):
                tui.run(tmp_path, tmp_path, headless=True)
        assert asyncio.get_running_loop() is running

    asyncio.run(run_inside())
