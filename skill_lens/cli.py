"""Skill Lens command-line interface.

Line-oriented Typer commands. Every command supports ``--json`` and returns
machine-readable output; the Rich layer is presentation only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from skill_lens import __version__
from skill_lens.core import paths
from skill_lens.core.resolver import resolve_skill
from skill_lens.core.scanner import build_scan_report
from skill_lens.models import dumps
from skill_lens.registry.loader import list_agents
from skill_lens.render import render_scan, render_why

app = typer.Typer(
    name="skill-lens",
    help="Local, read-only diagnostics and resolution for AI agent skills.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()
error_console = Console(stderr=True)


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


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version."),
    ] = False,
) -> None:
    """Skill Lens: know what skills you have, and why each one wins."""


def _apply_sandbox(sandbox: Path | None) -> None:
    if sandbox is not None:
        paths.set_sandbox(sandbox)


def _effective_home() -> Path:
    return paths.home()


def _effective_cwd(cwd: Path | None) -> Path:
    if cwd is None:
        return _effective_home()
    return cwd


@app.command()
def scan(
    sandbox: Annotated[
        Path | None,
        typer.Option("--sandbox", help="Treat this directory as a mock $HOME."),
    ] = None,
    cwd: Annotated[
        Path | None,
        typer.Option("--cwd", help="Working directory (defaults to $HOME)."),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
) -> None:
    """Inventory skills across every detected agent."""
    _apply_sandbox(sandbox)
    home = _effective_home()
    working_dir = _effective_cwd(cwd)
    report = build_scan_report(home, working_dir)
    if as_json:
        _emit_json(report.to_dict())
        return
    render_scan(report, console)


@app.command()
def why(
    skill_name: Annotated[str, typer.Argument(help="Skill name to resolve.")],
    agent: Annotated[str, typer.Option("--agent", help="Target agent id (e.g. claude).")],
    cwd: Annotated[
        Path | None,
        typer.Option("--cwd", help="Working directory (defaults to $HOME)."),
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
    working_dir = _effective_cwd(cwd)
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

    from rich.table import Table

    table = Table(show_header=True, header_style="bold")
    table.add_column("Agent")
    table.add_column("ID")
    table.add_column("Collision Policy")
    table.add_column("Evidence")
    table.add_column("Roots", justify="right")
    for agent in definitions:
        table.add_row(
            agent.name,
            agent.id,
            agent.collision_policy,
            agent.policy_evidence.value,
            str(len(agent.roots)),
        )
    console.print(table)


if __name__ == "__main__":  # pragma: no cover
    app()
