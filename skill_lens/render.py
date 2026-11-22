"""Rich presentation layer.

Formatting only: every function here takes an already-computed model and turns
it into terminal output. Descriptions are escaped with
``rich.markup.escape`` so skill text can never inject markup.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from rich import box
from rich.cells import cell_len
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from skill_lens.core import paths
from skill_lens.core.scanner import ScanReport
from skill_lens.core.search import refit
from skill_lens.models.compare import CompareReport
from skill_lens.models.diff import DiffCopy, DiffFile, DiffReport
from skill_lens.models.doctor import DoctorReport
from skill_lens.models.enums import Severity
from skill_lens.models.resolution import ResolutionReport
from skill_lens.models.search import LookupState, SearchHit, SearchReport
from skill_lens.presentation import (
    BASELINE_LABEL,
    BINARY_MARKER,
    COMPARE_EMPTY_TEXT,
    COPIES_LABEL,
    NOTE_LABEL,
    RELATION_LABEL,
    SCOPE_LABEL,
    STATE_MARK,
    STATE_STYLE,
    NoticeParts,
    baseline_text,
    copy_body,
    copy_heading,
    copy_truncation_notice,
    file_notice,
    needs_listing,
    no_differences_message,
    not_found_message,
    report_truncation_notice,
    unified_text,
)
from skill_lens.registry.loader import AgentDefinition


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
    table.add_column("Status")
    table.add_column("Canonical Path", overflow="fold")
    table.add_column("Active Entrypoints")
    for skill in report.skills:
        if skill.traversal_complete and skill.parse_status == "valid":
            status_text = "valid"
        elif not skill.traversal_complete:
            reason = skill.error_reason or "denied"
            status_text = f"unreadable ({reason})"
        else:
            reason = (
                f" ({skill.error_reason})"
                if skill.error_reason and skill.error_reason != skill.parse_status
                else ""
            )
            status_text = f"{skill.parse_status}{reason}"
        table.add_row(
            escape(skill.name),
            SCOPE_LABEL.get(skill.scope, skill.scope.value),
            escape(status_text),
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
    console.print(f"Headline: [{STATE_STYLE[report.headline]}]{report.headline.value}[/]")
    console.print()

    if not report.candidates:
        console.print(
            "[yellow]No copies of this skill name were found in any of "
            f"{escape(report.agent_name)}'s search roots.[/yellow]"
        )
        console.print()

    for candidate in report.candidates:
        style = STATE_STYLE[candidate.state]
        mark = STATE_MARK[candidate.state]
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


def _copy_heading(copy: DiffCopy, *, baseline_exists: bool) -> str:
    """One copy's heading line: marker, Variant letter, path, scope, status."""
    parts = copy_heading(
        copy,
        baseline_exists=baseline_exists,
        display_path=paths.display(copy.path),
    )
    return (
        f"[{parts.style}]{parts.mark}[/] {escape(parts.path)}{escape(parts.variant)}"
        f" [dim]({escape(parts.scope)}, {escape(parts.parse_status)})[/dim]"
        f"  [{parts.style}]{escape(parts.status)}[/]"
    )


def _render_file(file: DiffFile, console: Console) -> None:
    kind = f" [red]{BINARY_MARKER}[/red]" if file.is_binary else ""
    console.print(f"  [bold]{escape(file.path)}[/bold] [yellow]{file.change.value}[/yellow]{kind}")
    notice = file_notice(file)
    if notice is not None:
        # A binary payload and a text file with no printable hunk both stop here:
        # the notice says why, and the content is never printed.
        console.print(f"    [dim]{escape(notice)}[/dim]")
        return
    # ``Syntax`` hands the body to Pygments and never parses Rich markup, so file
    # content cannot inject markup -- the guarantee ``escape()`` provides for the
    # paths above. Escaping here instead would print literal backslashes, because
    # Pygments treats them as ordinary characters.
    console.print(
        Syntax(
            unified_text(file),
            "diff",
            background_color="default",
            indent_guides=False,
        )
    )


def _no_differences_message(report: DiffReport) -> str:
    """The headline when nothing differs -- which is not the same as 'identical'.

    With no baseline nothing was compared at all, so the honest headline is that
    no comparison happened, not that the copies match.
    """
    notice = no_differences_message(report)
    return f"[{notice.style}]{escape(notice.label)}[/{notice.style}]{escape(notice.body)}"


def _notice_line(notice: NoticeParts, *, indent: str = "") -> str:
    """One notice banner, styled by its part and never parsing its body."""
    label = f"[{notice.style}]{escape(notice.label)}[/{notice.style}]"
    return f"{indent}{label}{escape(notice.body)}"


def _print_notes(report: DiffReport, console: Console) -> None:
    for note in report.notes:
        console.print(f"[yellow]{NOTE_LABEL}[/yellow] {escape(note)}")


def render_diff(report: DiffReport, console: Console | None = None) -> None:
    """Render a diff report: a summary panel, then one block per copy.

    Formatting only -- every decision (which copy is the baseline, what differs,
    what was truncated) is already recorded in the model.
    """
    console = console or Console()

    if not report.found:
        # The model's note says the same thing for ``--json`` consumers, where it
        # travels with the data; printing it here as well would just repeat this.
        console.print(f"[yellow]{escape(not_found_message(report))}[/yellow]")
        return

    baseline = next((copy for copy in report.copies if copy.is_baseline), None)
    baseline_display = paths.display(baseline.path) if baseline is not None else None
    header = (
        f"[bold]{COPIES_LABEL}[/bold] {len(report.copies)}\n"
        f"[bold]{BASELINE_LABEL}[/bold] "
        f"{escape(baseline_text(baseline, display_path=baseline_display))}"
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
        if not needs_listing(report):
            if show_notes:
                _print_notes(report, console)
            return
        console.print()

    baseline_exists = report.baseline_path is not None
    for copy in report.copies:
        console.print(_copy_heading(copy, baseline_exists=baseline_exists))
        body = copy_body(copy, baseline_exists=baseline_exists)
        if body is not None:
            console.print(f"  [dim]{escape(body)}[/dim]")
        else:
            for file in copy.files:
                _render_file(file, console)
        truncation = copy_truncation_notice(copy)
        if truncation is not None:
            console.print(_notice_line(truncation, indent="  "))
        console.print()

    truncation = report_truncation_notice(report)
    if truncation is not None:
        console.print(_notice_line(truncation))
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
        console.print(f"[dim]{COMPARE_EMPTY_TEXT}[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Skill Name")
    table.add_column("Relation")
    table.add_column("Path A", overflow="fold")
    table.add_column("Path B", overflow="fold")
    for entry in report.entries:
        label, style = RELATION_LABEL[entry.relation]
        table.add_row(
            escape(entry.name),
            f"[{style}]{label}[/]",
            escape(_short(entry.path_a)) if entry.path_a else "-",
            escape(_short(entry.path_b)) if entry.path_b else "-",
        )
    console.print(table)

    for note in report.notes:
        console.print(f"[yellow]Note:[/yellow] {escape(note)}")


#: Control characters (C0, DEL, C1), ESC included. Rich ``Text`` keeps them, so
#: they are replaced before any search text reaches the terminal.
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _safe(value: str) -> str:
    """Skill-derived text with control characters shown as ``?``, never emitted."""
    return _CONTROL_CHARS.sub("?", value)


def _widest_line(cell: Text) -> int:
    """Display width of the longest line in a possibly multi-line cell."""
    return max((cell_len(line) for line in cell.plain.split("\n")), default=0)


def _state_cell(report: SearchReport, hit: SearchHit) -> Text:
    """The State or Agents/States cell, keeping aliases distinguishable.

    A selected agent's ordinary single-name answer stays the familiar compact
    state. When the copy resolves differently through several aliases, each
    alias name is shown, because a bare list of states would hide which name
    produced which answer. Without ``--agent``, one alias per agent keeps the
    compact ``agent: STATE`` form; several aliases are all named.
    """
    if report.agent is not None:
        selected = [state for state in hit.states if state.agent == report.agent]
        if len({state.state for state in selected}) > 1:
            return Text("\n".join(_safe(f"{state.name}: {state.state}") for state in selected))
        return Text(_safe(hit.state or "unknown"))
    if not hit.states:
        return Text(_safe(", ".join(hit.agents)) or "-")
    lines: list[str] = []
    by_agent: dict[str, list[LookupState]] = {}
    for state in hit.states:
        by_agent.setdefault(state.agent, []).append(state)
    for agent, aliases in by_agent.items():
        if len(aliases) == 1:
            lines.append(_safe(f"{agent}: {aliases[0].state}"))
        else:
            lines.extend(_safe(f"{agent}: {alias.name} {alias.state}") for alias in aliases)
    return Text("\n".join(lines))


def render_search(report: SearchReport, console: Console | None = None) -> None:
    """Render search results as a summary panel plus one table row per matching copy.

    Every piece of skill text, every path and the query itself goes into a
    ``Text`` object, never a markup string, so nothing a skill file contains can
    restyle the output or reach the terminal as an escape sequence. Excerpts
    are cut to the column width and state cells can use more than one line.
    Control characters (an ESC sequence hidden in a folder name, say) are
    replaced by ``?`` first, because ``Text`` alone would pass them through.
    """
    console = console or Console()
    counts = report.counts()
    header = Text()
    header.append("Matches: ", style="bold")
    header.append(
        f"{report.total}  (name {counts['name']}, description {counts['description']}, "
        f"body {counts['body']})"
    )
    if report.agent is not None:
        header.append("\n")
        header.append("Agent: ", style="bold")
        header.append(_safe(f"{report.agent_name or report.agent} ({report.agent})"))
    query = _safe(report.query)
    title = Text.assemble("Skill Lens: Search '", query, "'")
    console.print(Panel(header, title=title, expand=False, box=box.SQUARE))
    console.print()

    if not report.results:
        console.print(Text.assemble("No skills match '", query, "'.", style="dim"))
    else:
        rows: list[tuple[Text, Text, Text, Text, str]] = []
        for hit in report.results:
            skill = Text(_safe(hit.name))
            if hit.frontmatter_name is not None:
                skill.append(_safe(f" ({hit.frontmatter_name})"), style="dim")
            fourth = _state_cell(report, hit)
            rows.append(
                (
                    skill,
                    Text(hit.match.value),
                    Text(SCOPE_LABEL.get(hit.scope, hit.scope.value)),
                    fourth,
                    hit.snippet,
                )
            )
        fourth_header = "State" if report.agent is not None else "Agents / States"
        # Short columns get what their content needs, with the skill column capped
        # only where the frontmatter suffix can be abbreviated. The agent/state
        # column has no permanent cap: at a narrow width it folds, so every
        # reachable agent and state stays visible instead of disappearing behind
        # an ellipsis.
        widths = [
            min(24, max(len("Skill"), *(r[0].cell_len for r in rows))),
            max(len("description"), *(r[1].cell_len for r in rows)),
            max(len("Project"), *(r[2].cell_len for r in rows)),
        ]
        fourth_width = max(len(fourth_header), *(_widest_line(r[3]) for r in rows))
        borders = 3 * 5 + 1
        available = console.width - sum(widths) - borders - 12
        fourth_width = max(1, min(fourth_width, available))
        excerpt = max(12, console.width - sum(widths) - borders - fourth_width)
        table = Table(show_header=True, header_style="bold", box=box.SQUARE)
        for heading, width in zip(("Skill", "Match", "Scope"), widths, strict=True):
            table.add_column(heading, no_wrap=True, overflow="ellipsis", width=width)
        table.add_column(
            fourth_header,
            no_wrap=False,
            overflow="fold",
            width=fourth_width,
        )
        table.add_column("Excerpt", no_wrap=True, overflow="ellipsis", width=excerpt)
        for skill_cell, match_cell, scope_cell, fourth_cell, excerpt_text in rows:
            table.add_row(
                skill_cell,
                match_cell,
                scope_cell,
                fourth_cell,
                Text(_safe(refit(excerpt_text, report.query, excerpt)), style="dim"),
            )
        console.print(table)

    if report.unreadable:
        console.print(Text("Unreadable roots (not searched):", style="yellow"))
        for item in report.unreadable:
            line = Text("  ! ", style="yellow")
            line.append(_safe(f"{item['path']} ({item['detail']})"))
            console.print(line)
