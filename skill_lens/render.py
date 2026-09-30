"""Rich presentation layer.

Formatting only: every function here takes an already-computed model and turns
it into terminal output. Descriptions are escaped with
``rich.markup.escape`` so skill text can never inject markup.
"""

from __future__ import annotations

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from skill_lens.core import paths
from skill_lens.core.resolver import ResolutionReport
from skill_lens.core.scanner import ScanReport
from skill_lens.models.enums import HeadlineState, Scope

_STATE_STYLE = {
    HeadlineState.ACTIVE: "bold green",
    HeadlineState.COEXISTS: "bold cyan",
    HeadlineState.SHADOWED: "yellow",
    HeadlineState.DISABLED: "dim",
    HeadlineState.UNSEARCHED: "dim",
    HeadlineState.INVALID: "bold red",
    HeadlineState.AMBIGUOUS: "bold magenta",
}

_STATE_MARK = {
    HeadlineState.ACTIVE: "*",
    HeadlineState.COEXISTS: "+",
    HeadlineState.SHADOWED: "o",
    HeadlineState.DISABLED: "-",
    HeadlineState.UNSEARCHED: ".",
    HeadlineState.INVALID: "x",
    HeadlineState.AMBIGUOUS: "?",
}

_SCOPE_LABEL = {
    Scope.USER: "Global",
    Scope.PROJECT: "Project",
    Scope.SYSTEM: "System",
    Scope.PLUGIN: "Plugin",
}


def _short(path: str) -> str:
    """Collapse the effective home directory to ``~`` for display."""
    return paths.display(path)


def render_scan(report: ScanReport, console: Console | None = None) -> None:
    """Render a scan report as a summary panel plus a table."""
    console = console or Console()
    summary = report.summary
    agents = ", ".join(summary.detected_agents) or "none"
    body = (
        f"[bold]Detected Agents:[/bold] {escape(agents)}\n"
        f"[bold]Canonical Skills:[/bold] {summary.canonical_skill_count} "
        f"([bold]{summary.symlink_entrypoints}[/bold] symlink entrypoints)\n"
        f"[bold]Global:[/bold] {summary.user_skills}  "
        f"[bold]Project:[/bold] {summary.project_skills}  "
        f"[bold]System:[/bold] {summary.system_skills}  "
        f"[bold]Plugin:[/bold] {summary.plugin_skills}"
    )
    console.print(Panel(body, title="Skill Lens: Discovered Skills", expand=False))

    table = Table(show_header=True, header_style="bold")
    table.add_column("Skill Name")
    table.add_column("Scope")
    table.add_column("Canonical Path", overflow="fold")
    table.add_column("Active Entrypoints")
    for skill in report.skills:
        table.add_row(
            escape(skill.name),
            _SCOPE_LABEL.get(skill.scope, skill.scope.value),
            escape(_short(skill.canonical_path)),
            escape(", ".join(skill.agents)),
        )
    console.print(table)

    if report.unreadable:
        console.print("[yellow]Unreadable roots:[/yellow]")
        for item in report.unreadable:
            console.print(f"  [yellow]![/yellow] {escape(item['path'])} ({item['detail']})")


def render_why(report: ResolutionReport, console: Console | None = None) -> None:
    """Render a resolution report as a header panel plus one block per copy."""
    console = console or Console()
    header = (
        f"[bold]Agent:[/bold] {escape(report.agent_name)}\n"
        f"[bold]Working Dir:[/bold] {escape(paths.display(report.cwd))}\n"
        f"[bold]Collision Policy:[/bold] {escape(report.collision_policy)} "
        f"({report.policy_evidence.value})"
    )
    console.print(
        Panel(
            header,
            title=f"Resolution: '{escape(report.skill_name)}' for {escape(report.agent_name)}",
            expand=False,
        )
    )
    console.print(f"Headline: [{_STATE_STYLE[report.headline]}]{report.headline.value}[/]")
    console.print()

    for candidate in report.candidates:
        style = _STATE_STYLE[candidate.state]
        mark = _STATE_MARK[candidate.state]
        installation = candidate.installation
        title = Text()
        title.append(f"{mark} ", style=style)
        title.append(f"[{candidate.state.value}]", style=style)
        console.print(title)
        console.print(f"  Path:   {escape(paths.display(installation.canonical_path))}")
        if installation.entrypoint_path != installation.canonical_path:
            console.print(f"  Link:   {escape(paths.display(installation.entrypoint_path))}")
        console.print(f"  Reason: {escape(candidate.reason)}")
        console.print(
            f"  Rule:   {escape(candidate.rule_id)} (Evidence: {candidate.evidence.value})"
        )
        if installation.content_hash:
            console.print(f"  Hash:   {escape(installation.content_hash[:23])}...")
        console.print()

    for note in report.notes:
        console.print(f"[yellow]Note:[/yellow] {escape(note)}")
