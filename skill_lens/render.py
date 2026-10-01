"""Rich presentation layer.

Formatting only: every function here takes an already-computed model and turns
it into terminal output. Descriptions are escaped with
``rich.markup.escape`` so skill text can never inject markup.
"""

from __future__ import annotations

from collections.abc import Sequence

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from skill_lens.core import paths
from skill_lens.core.scanner import ScanReport
from skill_lens.models.compare import CompareReport
from skill_lens.models.diff import DiffCopy, DiffFile, DiffReport
from skill_lens.models.doctor import DoctorReport
from skill_lens.models.enums import CompareRelation, HeadlineState, Scope, Severity
from skill_lens.models.parsing import (
    ERR_DANGLING_SYMLINK,
    ERR_PERMISSION_DENIED,
    ERR_SYMLINK_CYCLE,
)
from skill_lens.models.resolution import ResolutionReport
from skill_lens.registry.loader import AgentDefinition

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
        f"[bold]Canonical Library:[/bold] {summary.canonical_skill_count} skills "
        f"([bold]{summary.symlink_entrypoints}[/bold] symlink entrypoints)\n"
        f"[bold]Local Project Skills:[/bold] {summary.project_skills}  "
        f"[bold]System/Bundled:[/bold] {summary.system_skills}  "
        f"[bold]Plugin Skills:[/bold] {summary.plugin_skills}"
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

    if not report.candidates:
        console.print(
            "[yellow]No copies of this skill name were found in any of "
            f"{escape(report.agent_name)}'s search roots.[/yellow]"
        )
        console.print()

    for candidate in report.candidates:
        style = _STATE_STYLE[candidate.state]
        mark = _STATE_MARK[candidate.state]
        installation = candidate.installation
        title = Text()
        title.append(f"{mark} ", style=style)
        title.append(f"[{candidate.state.value}]", style=style)
        if installation.variant_label:
            title.append(f"  Variant {installation.variant_label}", style=style)
        console.print(title)
        console.print(f"  Path:   {escape(paths.display(installation.canonical_path))}")
        # Only worth a second line when the entrypoint is genuinely a *different*
        # path -- comparing resolved paths avoids printing a link to the same
        # file twice when a parent directory is a symlink.
        if not paths.same_location(installation.entrypoint_path, installation.canonical_path):
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


def render_agents(agents: Sequence[AgentDefinition], console: Console | None = None) -> None:
    """Render the known agent definitions as a table.

    Lives here rather than in ``cli.py`` so that every Rich layout in the tool
    sits in one module and the command layer stays presentation-free.
    """
    console = console or Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Agent")
    table.add_column("ID")
    table.add_column("Collision Policy")
    table.add_column("Evidence")
    table.add_column("Roots", justify="right")
    for agent in agents:
        table.add_row(
            escape(agent.name),
            escape(agent.id),
            escape(agent.collision_policy),
            agent.policy_evidence.value,
            str(len(agent.roots)),
        )
    console.print(table)


# --- diff ------------------------------------------------------------------

_UNREADABLE_REASON = {
    ERR_SYMLINK_CYCLE: "symlink cycle",
    ERR_DANGLING_SYMLINK: "dangling symlink",
    ERR_PERMISSION_DENIED: "permission denied",
}


def _range_text(start: int, count: int) -> str:
    """Format one side of a unified hunk header the way ``difflib`` does."""
    return str(start) if count == 1 else f"{start},{count}"


def _unified_text(file: DiffFile) -> str:
    """The unified diff body for one file, ready for Rich's ``diff`` lexer."""
    lines = [f"--- {file.path}", f"+++ {file.path}"]
    for hunk in file.hunks:
        old = _range_text(hunk.old_start, hunk.old_count)
        new = _range_text(hunk.new_start, hunk.new_count)
        lines.append(f"@@ -{old} +{new} @@")
        lines.extend(hunk.lines)
    return "\n".join(lines)


def _unreadable_reason(copy: DiffCopy) -> str:
    return _UNREADABLE_REASON.get(copy.error or "", "no readable content")


def _copy_heading(copy: DiffCopy, *, baseline_exists: bool) -> str:
    """One copy's heading line: marker, Variant letter, path, scope, status."""
    if copy.is_baseline:
        mark, style, status = "=", "bold cyan", "baseline (no diff shown)"
    elif not copy.is_readable:
        mark, style, status = "x", "bold red", f"cannot be read: {_unreadable_reason(copy)}"
    elif copy.files:
        mark, style, status = "*", "bold yellow", f"{len(copy.files)} file(s) differ"
    elif not baseline_exists:
        # Nothing was compared, so claiming identity would be a lie.
        mark, style, status = "-", "dim", "not compared: no baseline"
    else:
        mark, style, status = "=", "dim", "identical to the baseline"

    variant = f" [Variant {copy.variant_label}]" if copy.variant_label else ""
    return (
        f"[{style}]{mark}[/] {escape(paths.display(copy.path))}{escape(variant)}"
        f" [dim]({escape(copy.scope.value)}, {escape(copy.parse_status)})[/dim]"
        f"  [{style}]{escape(status)}[/]"
    )


def _render_file(file: DiffFile, console: Console) -> None:
    kind = " [red]binary[/red]" if file.is_binary else ""
    console.print(f"  [bold]{escape(file.path)}[/bold] [yellow]{file.change.value}[/yellow]{kind}")
    if file.is_binary:
        console.print("    [dim]Binary content differs and is never printed.[/dim]")
        return
    if not file.hunks:
        console.print("    [dim]No printable content.[/dim]")
        return
    # ``Syntax`` hands the body to Pygments and never parses Rich markup, so file
    # content cannot inject markup -- the guarantee ``escape()`` provides for the
    # paths above. Escaping here instead would print literal backslashes, because
    # Pygments treats them as ordinary characters.
    console.print(
        Syntax(
            _unified_text(file),
            "diff",
            background_color="default",
            indent_guides=False,
        )
    )


def _no_differences_message(report: DiffReport) -> str:
    """The headline when nothing differs -- which is not the same as "identical".

    With no baseline nothing was compared at all, so the honest headline is that
    no comparison happened, not that the copies match.
    """
    if report.baseline_path is None:
        return "[yellow]Not compared:[/yellow] no copy could serve as a baseline."
    readable = [copy for copy in report.copies if copy.is_readable]
    if len(report.copies) == 1:
        return (
            "[green]No differences:[/green] only one copy exists, so there is nothing to compare."
        )
    if len(readable) < 2:
        return "[green]No differences:[/green] fewer than two copies could be read."
    return f"[green]No differences:[/green] all {len(readable)} readable copies are identical."


def _needs_listing(report: DiffReport) -> bool:
    """True when the copies must be listed even though nothing differs.

    A second copy, or a copy that could not be read at all, is itself a finding:
    printing only "no differences" would hide it.
    """
    return len(report.copies) > 1 or any(not copy.is_readable for copy in report.copies)


def _print_notes(report: DiffReport, console: Console) -> None:
    for note in report.notes:
        console.print(f"[yellow]Note:[/yellow] {escape(note)}")


def render_diff(report: DiffReport, console: Console | None = None) -> None:
    """Render a diff report: a summary panel, then one block per copy.

    Formatting only -- every decision (which copy is the baseline, what differs,
    what was truncated) is already recorded in the model.
    """
    console = console or Console()

    if not report.found:
        # The model's note says the same thing for ``--json`` consumers, where it
        # travels with the data; printing it here as well would just repeat this.
        console.print(
            f"[yellow]No copies of '{escape(report.skill_name)}' were found in any "
            "search root.[/yellow]"
        )
        return

    baseline = next((copy for copy in report.copies if copy.is_baseline), None)
    if baseline is None:
        baseline_text = "none (no copy passed validation)"
    else:
        variant = f" (Variant {baseline.variant_label})" if baseline.variant_label else ""
        baseline_text = f"{paths.display(baseline.path)}{variant}"
    header = (
        f"[bold]Copies:[/bold] {len(report.copies)}\n[bold]Baseline:[/bold] {escape(baseline_text)}"
    )
    console.print(
        Panel(
            header,
            title=f"Diff: '{escape(report.skill_name)}'",
            expand=False,
        )
    )
    console.print()

    # A report with no baseline states its reason in the headline below, and the
    # model's note says the same thing for ``--json`` consumers -- so the terminal
    # skips it rather than repeating itself.
    show_notes = report.baseline_path is not None

    if not report.has_differences:
        console.print(_no_differences_message(report))
        if not _needs_listing(report):
            if show_notes:
                _print_notes(report, console)
            return
        console.print()

    baseline_exists = report.baseline_path is not None
    for copy in report.copies:
        console.print(_copy_heading(copy, baseline_exists=baseline_exists))
        if copy.is_baseline:
            console.print("  [dim]Reference copy; every diff below is against it.[/dim]")
        elif not copy.is_readable:
            console.print(
                f"  [dim]No content to compare ({escape(_unreadable_reason(copy))}).[/dim]"
            )
        elif not copy.files:
            if baseline_exists:
                console.print("  [dim]No differences from the baseline.[/dim]")
            else:
                console.print("  [dim]Not compared: there is no baseline.[/dim]")
        else:
            for file in copy.files:
                _render_file(file, console)
        if copy.omitted_lines:
            console.print(
                f"  [yellow]Truncated:[/yellow] {copy.omitted_lines} changed lines omitted."
            )
        elif copy.truncated:
            # Only the character budget bit, so quoting a line count would read as
            # "0 changed lines omitted" -- which is worse than saying nothing.
            console.print(
                "  [yellow]Truncated:[/yellow] part of this diff was omitted; see the "
                "report total below."
            )
        console.print()

    if report.truncated:
        console.print(
            f"[yellow]Truncated:[/yellow] {report.omitted_chars} characters of diff body "
            "were omitted to keep this report readable."
        )
    if show_notes:
        _print_notes(report, console)


_SEVERITY_STYLE = {
    Severity.ERROR: "red",
    Severity.WARNING: "yellow",
    Severity.INFO: "dim",
}

_SEVERITY_MARK = {
    Severity.ERROR: "✗",
    Severity.WARNING: "!",
    Severity.INFO: "i",
}

_RELATION_LABEL = {
    CompareRelation.SHARED: ("shared", "green"),
    CompareRelation.DIVERGED: ("diverged", "yellow"),
    CompareRelation.ONLY_A: ("A only", "cyan"),
    CompareRelation.ONLY_B: ("B only", "magenta"),
}


def render_doctor(report: DoctorReport, console: Console | None = None) -> None:
    """Render a doctor report: one line per finding, sorted by severity.

    Formatting only -- the model already sorted findings and phrased every
    message; this chooses colours and marks.
    """
    console = console or Console()
    counts = report.counts_by_severity()
    verdict = (
        "No problems found."
        if report.healthy
        else (f"{counts['error']} error(s), {counts['warning']} warning(s), {counts['info']} info.")
    )
    header = (
        f"[bold]Home:[/bold] {escape(paths.display(report.home))}\n"
        f"[bold]Cwd:[/bold] {escape(paths.display(report.cwd))}\n"
        f"[bold]{escape(verdict)}[/bold]"
    )
    console.print(Panel(header, title="Skill Lens: Doctor", expand=False))
    console.print()

    if not report.findings:
        console.print("[green]Skill folders look healthy.[/green]")
    for finding in report.findings:
        style = _SEVERITY_STYLE[finding.severity]
        mark = _SEVERITY_MARK[finding.severity]
        location = f" [dim]{escape(finding.path)}[/dim]" if finding.path else ""
        detail = f" [dim]({escape(finding.detail)})[/dim]" if finding.detail else ""
        console.print(f"[{style}]{mark}[/] {escape(finding.message)}{location}{detail}")


def render_compare(report: CompareReport, console: Console | None = None) -> None:
    """Render a pairwise capability comparison as a table grouped by relation."""
    console = console or Console()
    counts = report.counts_by_relation()
    header = (
        f"[bold]A:[/bold] {escape(report.agent_a_name)} ({escape(report.agent_a)})  "
        f"[bold]B:[/bold] {escape(report.agent_b_name)} ({escape(report.agent_b)})\n"
        f"[bold]Shared:[/bold] {counts['shared']}  "
        f"[bold]Diverged:[/bold] {counts['diverged']}  "
        f"[bold]A only:[/bold] {counts['only_a']}  "
        f"[bold]B only:[/bold] {counts['only_b']}"
    )
    console.print(
        Panel(
            header,
            title=(f"Skill Lens: Compare {escape(report.agent_a)} vs {escape(report.agent_b)}"),
            expand=False,
        )
    )
    console.print()

    if not report.entries:
        console.print("[dim]Neither agent has any skills installed.[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Skill Name")
    table.add_column("Relation")
    table.add_column("Path A", overflow="fold")
    table.add_column("Path B", overflow="fold")
    for entry in report.entries:
        label, style = _RELATION_LABEL[entry.relation]
        table.add_row(
            escape(entry.name),
            f"[{style}]{label}[/]",
            escape(_short(entry.path_a)) if entry.path_a else "-",
            escape(_short(entry.path_b)) if entry.path_b else "-",
        )
    console.print(table)

    for note in report.notes:
        console.print(f"[yellow]Note:[/yellow] {escape(note)}")
