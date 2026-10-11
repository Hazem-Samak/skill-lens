"""TUI routing and launch tests for Skill Lens 0.2 (Assignment U1).

Validates the full terminal/plain/extra stream matrix, fallback behavior,
explicit command launch, sandbox/cwd validation, fault handling,
traceback suppression, lazy loader contracts, and optional import bypass.
"""

from __future__ import annotations

import importlib
import importlib.util
import re
import sys
import types
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import skill_lens.cli as cli
from skill_lens.cli import app
from skill_lens.core import paths
from skill_lens.core.exitcodes import ExitCode
from tests.fixtures.scenarios import build_scenario

_ANSI_ESCAPE = re.compile(rb"\x1b\[[0-9;]*m")


class _PlainRunner(CliRunner):
    """CLI runner that strips ANSI escape codes from captured output."""

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        result = super().invoke(*args, **kwargs)
        result.stdout_bytes = _ANSI_ESCAPE.sub(b"", result.stdout_bytes or b"")
        result.stderr_bytes = _ANSI_ESCAPE.sub(b"", result.stderr_bytes or b"")
        return result


runner = _PlainRunner()


def _install_fake_tui(monkeypatch: pytest.MonkeyPatch, runner_func: Any) -> types.ModuleType:
    """Install a fake ``skill_lens.tui`` module into sys.modules exposing ``run``."""
    fake_mod = types.ModuleType("skill_lens.tui")
    fake_mod.run = runner_func  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "skill_lens.tui", fake_mod)
    return fake_mod


# --- Full Stream / Plain / Extra Matrix -----------------------------------


@pytest.mark.parametrize("stdin_tty", [True, False])
@pytest.mark.parametrize("stdout_tty", [True, False])
@pytest.mark.parametrize("plain", [True, False])
@pytest.mark.parametrize("textual_available", [True, False])
def test_bare_invocation_stream_matrix(
    monkeypatch: pytest.MonkeyPatch,
    stdin_tty: bool,
    stdout_tty: bool,
    plain: bool,
    textual_available: bool,
) -> None:
    """Validate all 16 bare-invocation combinations of stream interactivity,
    the ``--plain`` flag, and Textual availability.

    Only interactive input AND interactive output AND plain=False AND Textual
    present triggers TUI launch.
    Only interactive input AND interactive output AND plain=False AND Textual
    absent prints help plus the one-line install tip (exit 0).
    All other 14 fallback cases print help without the tip (exit 0).
    """
    called_with: list[tuple[Path, Path]] = []

    def fake_runner(home: Path, cwd: Path) -> int:
        called_with.append((home, cwd))
        return 0

    _install_fake_tui(monkeypatch, fake_runner)
    monkeypatch.setattr(cli, "_is_textual_available", lambda: textual_available)

    def fake_isatty(stream: object) -> bool:
        if stream is sys.stdin:
            return stdin_tty
        if stream is sys.stdout:
            return stdout_tty
        return False

    monkeypatch.setattr(cli, "_stream_isatty", fake_isatty)

    args = ["--plain"] if plain else []
    result = runner.invoke(app, args)

    is_both_tty = stdin_tty and stdout_tty

    if is_both_tty and not plain and textual_available:
        # Full interactive launch
        assert result.exit_code == 0
        assert len(called_with) == 1
        assert called_with[0][0] == paths.home()
        assert called_with[0][1] == paths.terminal_cwd()
    elif is_both_tty and not plain and not textual_available:
        # Interactive fallback without Textual: help + tip, exit 0
        assert result.exit_code == 0
        assert len(called_with) == 0
        assert "Usage: skill-lens" in result.stdout
        expected_tip = "Tip: Install the terminal UI with: pip install 'skill-lens-cli[tui]'"
        assert expected_tip in result.stdout
        assert result.stderr == ""
    else:
        # All other 14 fallback combinations: help without tip, exit 0
        assert result.exit_code == 0
        assert len(called_with) == 0
        assert "Usage: skill-lens" in result.stdout
        assert "Tip:" not in result.stdout
        assert "skill-lens-cli[tui]" not in result.stdout
        assert result.stderr == ""


# --- Command Help / Version / Bypass ---------------------------------------


def test_root_help_without_textual(monkeypatch: pytest.MonkeyPatch) -> None:
    """Root --help works without Textual and never attempts launch."""
    monkeypatch.setattr(cli, "_is_textual_available", lambda: False)
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage: skill-lens" in result.stdout
    assert "tui" in result.stdout
    assert "Tip:" not in result.stdout


def test_root_version_without_textual(monkeypatch: pytest.MonkeyPatch) -> None:
    """Root --version works without Textual."""
    monkeypatch.setattr(cli, "_is_textual_available", lambda: False)
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "skill-lens" in result.stdout


def test_tui_help_without_textual(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit `tui --help` works without Textual and documents options."""
    monkeypatch.setattr(cli, "_is_textual_available", lambda: False)
    result = runner.invoke(app, ["tui", "--help"])
    assert result.exit_code == 0
    assert "Usage: skill-lens tui" in result.stdout
    assert "--sandbox" in result.stdout
    assert "--cwd" in result.stdout


def test_plain_tui_explicitly_launches(monkeypatch: pytest.MonkeyPatch) -> None:
    """`--plain tui` ignores root --plain and still explicitly dispatches tui."""
    called_with: list[tuple[Path, Path]] = []

    def fake_runner(home: Path, cwd: Path) -> int:
        called_with.append((home, cwd))
        return 0

    _install_fake_tui(monkeypatch, fake_runner)
    monkeypatch.setattr(cli, "_is_textual_available", lambda: True)

    result = runner.invoke(app, ["--plain", "tui"])
    assert result.exit_code == 0
    assert len(called_with) == 1


def test_plain_subcommand_bypass(mock_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Root --plain is ignored when an explicit subcommand is provided."""
    build_scenario("claude_personal_beats_project", mock_home)
    result = runner.invoke(app, ["--plain", "scan", "--sandbox", str(mock_home), "--json"])
    assert result.exit_code == 0
    assert '"skills":' in result.stdout


def test_bypass_no_optional_probe_or_import_for_line_and_fallback(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Line commands, help, version, --plain, and noninteractive fallback must never
    probe Textual availability or attempt to import skill_lens.tui.
    """
    probed: list[str] = []

    orig_find_spec = importlib.util.find_spec

    def spy_find_spec(name: str, *args: Any, **kwargs: Any) -> Any:
        probed.append(name)
        return orig_find_spec(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", spy_find_spec)

    # Make streams non-interactive to test fallback without probe
    monkeypatch.setattr(cli, "_stream_isatty", lambda s: False)

    # 1. Bare non-interactive invocation
    res = runner.invoke(app, [])
    assert res.exit_code == 0
    assert "textual" not in probed

    # 2. --plain invocation
    probed.clear()
    res = runner.invoke(app, ["--plain"])
    assert res.exit_code == 0
    assert "textual" not in probed

    # 3. Root --help and --version
    probed.clear()
    runner.invoke(app, ["--help"])
    runner.invoke(app, ["--version"])
    assert "textual" not in probed

    # 4. Line commands
    probed.clear()
    build_scenario("claude_personal_beats_project", mock_home)
    runner.invoke(app, ["scan", "--sandbox", str(mock_home), "--json"])
    runner.invoke(app, ["why", "--sandbox", str(mock_home), "super-skill", "--agent", "claude"])
    assert "textual" not in probed


# --- Explicit tui Command Routing & Validation ----------------------------


def test_explicit_tui_launches_without_terminal_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit `skill-lens tui` bypasses terminal isatty checks."""
    called: list[bool] = []

    def fake_runner(home: Path, cwd: Path) -> int:
        called.append(True)
        return 0

    # Ensure streams report false to prove explicit command bypasses them
    monkeypatch.setattr(cli, "_stream_isatty", lambda s: False)
    monkeypatch.setattr(cli, "_is_textual_available", lambda: True)
    _install_fake_tui(monkeypatch, fake_runner)

    result = runner.invoke(app, ["tui"])
    assert result.exit_code == 0
    assert called == [True]


def test_explicit_tui_missing_textual_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit `skill-lens tui` without Textual outputs install hint to stderr and exits 2."""
    monkeypatch.setattr(cli, "_is_textual_available", lambda: False)
    result = runner.invoke(app, ["tui"])
    assert result.exit_code == int(ExitCode.USAGE)
    assert "Error:" in result.stderr
    assert "skill-lens-cli[tui]" in result.stderr
    clean_stderr = " ".join(result.stderr.split())
    assert "pip install 'skill-lens-cli[tui]'" in clean_stderr
    assert "Traceback" not in result.stderr


def test_explicit_tui_forwards_sandbox_and_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit `tui` validates and forwards sandbox home and cwd to runner."""
    received: list[tuple[Path, Path]] = []

    def fake_runner(home: Path, cwd: Path) -> int:
        received.append((home, cwd))
        return 0

    sandbox = tmp_path / "custom_home"
    sandbox.mkdir()
    working_dir = sandbox / "project"
    working_dir.mkdir()

    monkeypatch.setattr(cli, "_is_textual_available", lambda: True)
    _install_fake_tui(monkeypatch, fake_runner)

    result = runner.invoke(app, ["tui", "--sandbox", str(sandbox), "--cwd", str(working_dir)])
    assert result.exit_code == 0
    assert len(received) == 1
    assert paths.same_location(received[0][0], sandbox)
    assert paths.same_location(received[0][1], working_dir)


def test_explicit_tui_escaped_cwd_rejected_before_availability_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An escaped cwd must fail with BadParameter (2) before checking Textual."""
    availability_checked: list[bool] = []

    def spy_available() -> bool:
        availability_checked.append(True)
        return False

    monkeypatch.setattr(cli, "_is_textual_available", spy_available)

    sandbox = tmp_path / "sandbox_home"
    sandbox.mkdir()
    outside = tmp_path / "outside_dir"
    outside.mkdir()

    result = runner.invoke(app, ["tui", "--sandbox", str(sandbox), "--cwd", str(outside)])
    assert result.exit_code == 2
    msg = "--cwd must stay inside --sandbox"
    assert msg in result.stderr or msg in result.stdout
    assert availability_checked == [], "Availability should not be checked on cwd failure"


# --- Exit Code Propagation & Fault Boundaries ------------------------------


def test_tui_runner_exit_code_0_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Runner returning 0 exits process with 0."""
    monkeypatch.setattr(cli, "_is_textual_available", lambda: True)
    _install_fake_tui(monkeypatch, lambda h, c: 0)
    result = runner.invoke(app, ["tui"])
    assert result.exit_code == 0


def test_tui_runner_exit_code_3_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Runner returning 3 exits process with 3."""
    monkeypatch.setattr(cli, "_is_textual_available", lambda: True)
    _install_fake_tui(monkeypatch, lambda h, c: 3)
    result = runner.invoke(app, ["tui"])
    assert result.exit_code == int(ExitCode.INTERNAL)


def test_tui_runner_unexpected_exception_exits_3_no_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runner throwing an unexpected exception prints plain error to stderr and exits 3."""

    def exploding_runner(h: Path, c: Path) -> int:
        raise RuntimeError("Terminal device disconnected unexpectedly")

    monkeypatch.setattr(cli, "_is_textual_available", lambda: True)
    _install_fake_tui(monkeypatch, exploding_runner)

    result = runner.invoke(app, ["tui"])
    assert result.exit_code == int(ExitCode.INTERNAL)
    clean_err = " ".join(result.stderr.split())
    assert (
        "Error: Failed to start the terminal UI: Terminal device disconnected unexpectedly"
        in clean_err
    )
    assert "Traceback" not in result.stderr


def test_tui_missing_u2_module_with_textual_present_exits_3_no_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When Textual is present but `skill_lens.tui` does not exist (U1 state),
    launch fails as internal fault (3) rather than missing extra (2), with no traceback.
    """
    monkeypatch.setattr(cli, "_is_textual_available", lambda: True)
    monkeypatch.delitem(sys.modules, "skill_lens.tui", raising=False)

    result = runner.invoke(app, ["tui"])
    assert result.exit_code == int(ExitCode.INTERNAL)
    assert "Error: Failed to start the terminal UI:" in result.stderr
    assert "skill_lens.tui" in result.stderr
    assert "Traceback" not in result.stderr
    assert "skill-lens-cli[tui]" not in result.stderr


def test_tui_bad_or_missing_callable_exits_3_no_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When `skill_lens.tui` exists but does not export a callable `run`, exit 3."""
    monkeypatch.setattr(cli, "_is_textual_available", lambda: True)

    fake_mod = types.ModuleType("skill_lens.tui")
    fake_mod.run = "not_a_callable"
    monkeypatch.setitem(sys.modules, "skill_lens.tui", fake_mod)

    result = runner.invoke(app, ["tui"])
    assert result.exit_code == int(ExitCode.INTERNAL)
    assert "Error: Failed to start the terminal UI:" in result.stderr
    clean_err = " ".join(result.stderr.split())
    assert "does not expose a callable 'run'" in clean_err
    assert "Traceback" not in result.stderr


def test_tui_unrelated_dependency_import_error_exits_3_no_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When importing `skill_lens.tui` fails due to an unrelated dependency import failure,
    exit 3.
    """
    monkeypatch.setattr(cli, "_is_textual_available", lambda: True)

    def failing_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "skill_lens.tui":
            raise ImportError("No module named 'unrelated_dependency'")
        return importlib.__import__(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", failing_import)

    result = runner.invoke(app, ["tui"])
    assert result.exit_code == int(ExitCode.INTERNAL)
    assert (
        "Error: Failed to start the terminal UI: No module named 'unrelated_dependency'"
        in result.stderr
    )
    assert "Traceback" not in result.stderr


def test_textual_availability_exception_exits_3_plain_english(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When find_spec raises an unexpected exception (e.g. ValueError / OSError),
    it must be reported as internal fault (3) in plain English without traceback.
    """

    def broken_find_spec(name: str) -> Any:
        raise ValueError("Corrupted package metadata [spec_invalid]")

    monkeypatch.setattr(importlib.util, "find_spec", broken_find_spec)

    # 1. Test explicit tui command
    res_explicit = runner.invoke(app, ["tui"])
    assert res_explicit.exit_code == int(ExitCode.INTERNAL)
    clean_err = " ".join(res_explicit.stderr.split())
    assert (
        "Error: Failed to check Textual availability: Corrupted package metadata [spec_invalid]"
        in clean_err
    )
    assert "Traceback" not in res_explicit.stderr

    # 2. Test interactive bare invocation
    monkeypatch.setattr(cli, "_stream_isatty", lambda s: True)
    res_bare = runner.invoke(app, [])
    assert res_bare.exit_code == int(ExitCode.INTERNAL)
    clean_err = " ".join(res_bare.stderr.split())
    assert (
        "Error: Failed to check Textual availability: Corrupted package metadata [spec_invalid]"
        in clean_err
    )
    assert "Traceback" not in res_bare.stderr


def test_literal_bracket_details_rendered_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exception messages containing square brackets must be rendered literally
    without crashing or being parsed as Rich markup.
    """

    def bracket_exploding_runner(h: Path, c: Path) -> int:
        raise RuntimeError("[tag:error] device [127.0.0.1:8080] failed [fatal]")

    monkeypatch.setattr(cli, "_is_textual_available", lambda: True)
    _install_fake_tui(monkeypatch, bracket_exploding_runner)

    result = runner.invoke(app, ["tui"])
    assert result.exit_code == int(ExitCode.INTERNAL)
    clean_err = " ".join(result.stderr.split())
    assert "[tag:error] device [127.0.0.1:8080] failed [fatal]" in clean_err
    assert "Traceback" not in result.stderr


def test_stream_isatty_exception_resilience() -> None:
    """_stream_isatty safely handles streams without isatty or throwing errors."""

    class BrokenStream:
        def isatty(self) -> bool:
            raise OSError("Stream pipe broken")

    assert not cli._stream_isatty(None)
    assert not cli._stream_isatty(object())
    assert not cli._stream_isatty(BrokenStream())


def test_is_textual_available_real_environment() -> None:
    """In the test environment, Textual was installed via the dev extra."""
    assert cli._is_textual_available() is True
