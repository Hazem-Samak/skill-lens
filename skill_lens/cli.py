"""Skill Lens command-line interface.

Line-oriented Typer commands (scan, why, agents, diff, doctor, compare).
Every command supports ``--json`` and returns machine-readable output; the
Rich layer is presentation only.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Annotated, Protocol, cast

import typer
from rich.console import Console

from skill_lens import __version__
from skill_lens.core import paths
from skill_lens.core.compare import run_compare
from skill_lens.core.diff import build_diff_report
from skill_lens.core.discovery import normalize_cwd
from skill_lens.core.doctor import run_doctor
from skill_lens.core.exitcodes import ExitCode, FailOn, exit_code_for, fail_on_help
from skill_lens.core.hasher import IncompleteTreeError
from skill_lens.core.resolver import resolve_skill
from skill_lens.core.scanner import build_scan_report, scan_severities
from skill_lens.models import dumps
from skill_lens.models.enums import Severity
from skill_lens.registry.loader import list_agents
from skill_lens.render import (
    render_agents,
    render_compare,
    render_diff,
    render_doctor,
    render_scan,
    render_why,
)

app = typer.Typer(
    name="skill-lens",
    help="Local, read-only diagnostics and resolution for AI agent skills.",
    no_args_is_help=False,
    add_completion=False,
)

console = Console()
error_console = Console(stderr=True)


class TuiRunner(Protocol):
    """Callable interface for the TUI entry point."""

    def __call__(self, home: Path, cwd: Path) -> int: ...


def _is_textual_available() -> bool:
    """Return True if the optional Textual library is installed and available.

    Only find_spec returning None indicates Textual is absent.
    Any exception encountered while checking availability is treated as an
    internal fault (exit code 3) in plain English.
    """
    try:
        spec = importlib.util.find_spec("textual")
    except Exception as exc:
        error_console.print(
            f"Error: Failed to check Textual availability: {exc}",
            soft_wrap=True,
            markup=False,
            highlight=False,
        )
        raise typer.Exit(code=int(ExitCode.INTERNAL)) from None
    return spec is not None


def _stream_isatty(stream: object) -> bool:
    """Return True if the stream is an interactive terminal."""
    try:
        return bool(stream is not None and hasattr(stream, "isatty") and stream.isatty())
    except Exception:
        return False


def _load_tui_runner() -> TuiRunner:
    """Lazily load the TUI runner callable."""
    mod = importlib.import_module("skill_lens.tui")
    runner = getattr(mod, "run", None)
    if not callable(runner):
        raise ImportError("skill_lens.tui does not expose a callable 'run'")
    return cast(TuiRunner, runner)


def _launch_tui(home: Path, cwd: Path) -> None:
    """Launch the terminal UI through the lazy adapter boundary."""
    try:
        runner = _load_tui_runner()
        code = runner(home, cwd)
    except typer.Exit:
        raise
    except Exception as exc:
        error_console.print(
            f"Error: Failed to start the terminal UI: {exc}",
            soft_wrap=True,
            markup=False,
            highlight=False,
        )
        raise typer.Exit(code=int(ExitCode.INTERNAL)) from None

    if code != int(ExitCode.OK):
        raise typer.Exit(code=int(code))


def _emit_json(payload: object) -> None:
    """Print canonical JSON without wrapping, markup or highlighting.

    Rich's default word-wrap would insert newlines inside JSON strings and
    corrupt the output, so wrapping and markup are disabled explicitly.
    """
    console.print(dumps(payload), soft_wrap=True, markup=False, highlight=False)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"skill-lens {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version."),
    ] = False,
    plain: Annotated[
        bool,
        typer.Option(
            "--plain",
            help="Print help instead of opening the terminal UI on bare invocation.",
        ),
    ] = False,
) -> None:
    """Skill Lens: know what skills you have, and why each one wins."""
    if ctx.invoked_subcommand is not None:
        return

    is_interactive = _stream_isatty(sys.stdin) and _stream_isatty(sys.stdout)
    if plain or not is_interactive:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=int(ExitCode.OK))

    if not _is_textual_available():
        typer.echo(ctx.get_help())
        typer.echo("\nTip: Install the terminal UI with: pip install 'skill-lens-cli[tui]'")
        raise typer.Exit(code=int(ExitCode.OK))

    home = _effective_home()
    working_dir = _effective_cwd(None, None)
    _launch_tui(home, working_dir)


def _apply_sandbox(sandbox: Path | None) -> None:
    if sandbox is not None:
        paths.set_sandbox(sandbox)


def _effective_home() -> Path:
    return paths.home()


def _effective_cwd(cwd: Path | None, sandbox: Path | None) -> Path:
    """Resolve the working directory, clamped to the sandbox when there is one.

    ``$HOME`` is usually not inside a repository, so defaulting there silently
    skipped every project root -- hence the terminal folder. A *relative*
    ``--cwd`` keeps its documented meaning under ``--sandbox``: home-relative,
    never process-relative, so a sandboxed run can never be walked from the
    folder the user happens to be standing in.
    """
    if cwd is None:
        return paths.terminal_cwd()
    if sandbox is None:
        return cwd
    return normalize_cwd(cwd, sandbox)


def _assert_inside_sandbox(cwd: Path, sandbox: Path) -> None:
    """Refuse a ``--cwd`` that points out of the sandbox.

    Relative values are clamped first (see :func:`_effective_cwd`), but an
    *absolute* one was accepted verbatim and let a sandboxed run read any
    directory on the machine. Resolving both sides means the check still holds
    when the sandbox itself sits behind a symlink (macOS ``/tmp``).
    """
    if paths.same_location(cwd, sandbox):
        return
    try:
        cwd.resolve().relative_to(sandbox.resolve())
    except ValueError:
        raise typer.BadParameter(f"--cwd must stay inside --sandbox {sandbox}; got {cwd}") from None


_CWD_HELP = "Working directory (defaults to the current terminal folder)."


def _finish(severities: tuple[Severity, ...], fail_on: FailOn) -> None:
    """Exit with the status the threshold implies, once output is already sent.

    Called only *after* the report has been printed, so a failing run still
    shows the user everything that caused the failure. An exit raised before the
    report would make ``--fail-on`` a way to hide the evidence.
    """
    code = exit_code_for(severities, fail_on)
    if code is not ExitCode.OK:
        raise typer.Exit(code=int(code))


@app.command()
def tui(
    sandbox: Annotated[
        Path | None,
        typer.Option("--sandbox", help="Treat this directory as a mock $HOME."),
    ] = None,
    cwd: Annotated[
        Path | None,
        typer.Option("--cwd", help=_CWD_HELP),
    ] = None,
) -> None:
    """Open the interactive terminal UI."""
    _apply_sandbox(sandbox)
    home = _effective_home()
    working_dir = _effective_cwd(cwd, sandbox)
    if sandbox is not None:
        _assert_inside_sandbox(working_dir, home)
    if not _is_textual_available():
        error_console.print(
            "Error: The terminal UI requires 'skill-lens-cli[tui]'. "
            "Install it with: pip install 'skill-lens-cli[tui]'",
            soft_wrap=True,
            markup=False,
            highlight=False,
        )
        raise typer.Exit(code=int(ExitCode.USAGE))
    _launch_tui(home, working_dir)


@app.command()
def scan(
    sandbox: Annotated[
        Path | None,
        typer.Option("--sandbox", help="Treat this directory as a mock $HOME."),
    ] = None,
    cwd: Annotated[
        Path | None,
        typer.Option("--cwd", help=_CWD_HELP),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
    fail_on: Annotated[
        FailOn,
        typer.Option("--fail-on", help=fail_on_help()),
    ] = FailOn.NEVER,
) -> None:
    """Inventory skills across every detected agent."""
    _apply_sandbox(sandbox)
    home = _effective_home()
    working_dir = _effective_cwd(cwd, sandbox)
    if sandbox is not None:
        _assert_inside_sandbox(working_dir, home)
    report = build_scan_report(home, working_dir)
    if as_json:
        _emit_json(report.to_dict())
    else:
        render_scan(report, console)
    _finish(scan_severities(report), fail_on)


@app.command()
def why(
    skill_name: Annotated[str, typer.Argument(help="Skill name to resolve.")],
    agent: Annotated[str, typer.Option("--agent", help="Target agent id (e.g. claude).")],
    cwd: Annotated[
        Path | None,
        typer.Option("--cwd", help=_CWD_HELP),
    ] = None,
    sandbox: Annotated[
        Path | None,
        typer.Option("--sandbox", help="Treat this directory as a mock $HOME."),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
) -> None:
    """Explain how a skill resolves for one agent, and why."""
    _apply_sandbox(sandbox)
    home = _effective_home()
    working_dir = _effective_cwd(cwd, sandbox)
    if sandbox is not None:
        _assert_inside_sandbox(working_dir, home)
    try:
        report = resolve_skill(skill_name, agent, working_dir, home)
    except KeyError as exc:
        error_console.print(f"[red]Error:[/red] {exc.args[0]}")
        raise typer.Exit(code=2) from None
    if as_json:
        _emit_json(report.to_dict())
        return
    render_why(report, console)


@app.command()
def agents(
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
) -> None:
    """List the known agent definitions and their precedence policy."""
    definitions = list_agents()
    if as_json:
        payload = [
            {
                "id": agent.id,
                "name": agent.name,
                "collision_policy": agent.collision_policy,
                "policy_evidence": agent.policy_evidence.value,
                "roots": len(agent.roots),
            }
            for agent in definitions
        ]
        _emit_json(payload)
        return
    render_agents(definitions, console)


@app.command()
def diff(
    skill_name: Annotated[str, typer.Argument(help="Skill name whose variants to diff.")],
    sandbox: Annotated[
        Path | None,
        typer.Option("--sandbox", help="Treat this directory as a mock $HOME."),
    ] = None,
    cwd: Annotated[
        Path | None,
        typer.Option("--cwd", help=_CWD_HELP),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
) -> None:
    """Unified diff between the differing variants that share one name."""
    _apply_sandbox(sandbox)
    home = _effective_home()
    working_dir = _effective_cwd(cwd, sandbox)
    if sandbox is not None:
        _assert_inside_sandbox(working_dir, home)
    try:
        report = build_diff_report(skill_name, working_dir, home)
    except IncompleteTreeError as exc:
        error_console.print(
            f"Error: {exc}",
            soft_wrap=True,
            markup=False,
            highlight=False,
        )
        raise typer.Exit(code=int(ExitCode.USAGE)) from None
    if as_json:
        _emit_json(report.to_dict())
        return
    render_diff(report, console)


@app.command()
def doctor(
    sandbox: Annotated[
        Path | None,
        typer.Option("--sandbox", help="Treat this directory as a mock $HOME."),
    ] = None,
    cwd: Annotated[
        Path | None,
        typer.Option("--cwd", help=_CWD_HELP),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
    fail_on: Annotated[
        FailOn,
        typer.Option("--fail-on", help=fail_on_help()),
    ] = FailOn.NEVER,
) -> None:
    """Check skill hygiene: broken links, bad frontmatter, budget risks."""
    _apply_sandbox(sandbox)
    home = _effective_home()
    working_dir = _effective_cwd(cwd, sandbox)
    if sandbox is not None:
        _assert_inside_sandbox(working_dir, home)
    # The CLI goes through the live adapter (system.py) so the OSError-
    # guarded bridge is the production path, not a test-only helper.
    report = run_doctor(cwd=working_dir)
    if as_json:
        _emit_json(report.to_dict())
    else:
        render_doctor(report, console)
    _finish(tuple(finding.severity for finding in report.findings), fail_on)


@app.command()
def compare(
    agents: Annotated[
        list[str],
        typer.Option("--agent", help="Agent id to compare. Pass exactly two."),
    ],
    sandbox: Annotated[
        Path | None,
        typer.Option("--sandbox", help="Treat this directory as a mock $HOME."),
    ] = None,
    cwd: Annotated[
        Path | None,
        typer.Option("--cwd", help=_CWD_HELP),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
) -> None:
    """Compare which skills two agents can reach: shared, diverged, one-sided."""
    if len(agents) != 2:
        raise typer.BadParameter(
            f"pass --agent exactly twice (two agents to compare); got {len(agents)}."
        )
    _apply_sandbox(sandbox)
    home = _effective_home()
    working_dir = _effective_cwd(cwd, sandbox)
    if sandbox is not None:
        _assert_inside_sandbox(working_dir, home)
    try:
        report = run_compare(agents[0], agents[1], cwd=working_dir)
    except KeyError as exc:
        error_console.print(f"[red]Error:[/red] {exc.args[0]}")
        raise typer.Exit(code=2) from None
    if as_json:
        _emit_json(report.to_dict())
        return
    render_compare(report, console)


if __name__ == "__main__":  # pragma: no cover
    app()
