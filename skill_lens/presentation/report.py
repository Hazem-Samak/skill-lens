"""Pure Markdown rendering for the combined ``skill-lens report`` document.

No Rich, no Typer, no writes: the renderer turns one :class:`ReportModel` into
plain Markdown. Rich is deliberately avoided: this text is copied verbatim to
stdout or a file, and Rich would wrap it and consume Markdown escapes.

All interpolated values pass through :func:`escape_markdown`, a single-pass
CommonMark backslash escaper. It is intentionally not Rich's escaper: Rich
leaves ``|`` intact, which would break a Markdown table cell.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from skill_lens.models.compare import CompareReport
from skill_lens.models.enums import CompareRelation
from skill_lens.models.report import ReportModel
from skill_lens.presentation.state import SCOPE_LABEL

_ESCAPE_CHARS = frozenset("\\`*_[]<>|")
_SCOPE_LABELS = {scope.value: label for scope, label in SCOPE_LABEL.items()}


def escape_markdown(value: str) -> str:
    """Escape the Markdown-significant characters in one dynamic string.

    Each line ending becomes one space, including a standalone carriage return.
    The replacement backslashes are never re-scanned, so the operation is one
    pass: escaping an already escaped string would double its slashes.
    """
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", " ")
    return "".join("\\" + char if char in _ESCAPE_CHARS else char for char in normalized)


def _cell(value: object) -> str:
    """One escaped table cell; ``None`` renders as an empty cell."""
    if value is None:
        return ""
    return escape_markdown(str(value))


def _shown_path(raw: object, display: Callable[[str], str]) -> str:
    """A display-collapsed, escaped path; ``None`` never reaches ``display``."""
    if raw is None:
        return ""
    return escape_markdown(display(str(raw)))


def _table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def _detected_ids(scan: dict[str, Any]) -> tuple[str, ...]:
    summary = scan.get("summary")
    if not isinstance(summary, dict):
        return ()
    raw = summary.get("detected_agents")
    if not isinstance(raw, (list, tuple)):
        return ()
    return tuple(str(agent_id) for agent_id in raw)


def _skills(scan: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    raw = scan.get("skills")
    if not isinstance(raw, (list, tuple)):
        return ()
    return tuple(skill for skill in raw if isinstance(skill, dict))


def _metadata_lines(model: ReportModel, display: Callable[[str], str]) -> list[str]:
    scan = model.scan
    rows = [
        ("Generated (UTC)", _cell(model.meta.generated_at)),
        ("Skill Lens version", _cell(model.meta.skill_lens_version)),
        ("Platform", _cell(model.meta.platform)),
        ("Home", _shown_path(scan.get("home"), display)),
        ("Cwd", _shown_path(scan.get("cwd"), display)),
    ]
    return _table(("Field", "Value"), rows)


def _detected_agent_lines(model: ReportModel, detected: tuple[str, ...]) -> list[str]:
    lines = ["## Detected agents", ""]
    if not detected:
        lines.append("No agents detected on this machine.")
        return lines
    summaries = {str(agent["id"]): agent for agent in model.agents}
    rows: list[tuple[str, ...]] = []
    for agent_id in detected:
        summary = summaries.get(agent_id)
        if summary is None:
            rows.append((_cell(agent_id), "", "", "", ""))
            continue
        rows.append(
            (
                _cell(summary["id"]),
                _cell(summary["name"]),
                _cell(summary["collision_policy"]),
                _cell(summary["policy_evidence"]),
                _cell(summary["roots"]),
            )
        )
    lines.extend(_table(("Agent", "Name", "Collision policy", "Evidence", "Roots"), rows))
    return lines


def _known_agent_lines(model: ReportModel, detected: tuple[str, ...]) -> list[str]:
    rows = [
        (
            _cell(agent["id"]),
            _cell(agent["name"]),
            _cell(agent["collision_policy"]),
            _cell(agent["policy_evidence"]),
            _cell(agent["roots"]),
            "yes" if str(agent["id"]) in detected else "no",
        )
        for agent in model.agents
    ]
    return [
        "## Known agents and precedence",
        "",
        *_table(
            ("Agent", "Name", "Collision policy", "Evidence", "Roots", "Detected"),
            rows,
        ),
    ]


def _library_lines(model: ReportModel) -> list[str]:
    summary = model.scan.get("summary")
    values: dict[str, Any] = summary if isinstance(summary, dict) else {}
    rows = [
        ("Canonical library (user-scope skills)", _cell(values.get("canonical_skill_count"))),
        ("Project skills", _cell(values.get("project_skills"))),
        ("System skills", _cell(values.get("system_skills"))),
        ("Plugin skills", _cell(values.get("plugin_skills"))),
        ("Total skills (all scopes)", _cell(values.get("total_skills"))),
        ("Symlink entrypoints", _cell(values.get("symlink_entrypoints"))),
    ]
    return ["## Canonical library summary", "", *_table(("Measure", "Value"), rows)]


def _state_cell(skill: dict[str, Any]) -> str:
    parse_status = str(skill.get("parse_status") or "")
    health_status = str(skill.get("health_status") or "")
    if health_status in ("", "ok"):
        return _cell(parse_status)
    return _cell(f"{parse_status} ({health_status})")


def _inventory_lines(model: ReportModel, display: Callable[[str], str]) -> list[str]:
    detected = _detected_ids(model.scan)
    skills = _skills(model.scan)
    lines = ["## Per-agent skill inventory"]
    if not detected:
        lines.extend(["", "No skills detected on this machine."])
        return lines
    for agent_id in detected:
        owned = [skill for skill in skills if agent_id in (skill.get("agents") or ())]
        lines.extend(["", f"### {escape_markdown(agent_id)}", ""])
        if not owned:
            lines.append("No skills for this agent.")
            continue
        rows = [
            (
                _cell(skill.get("name")),
                _cell(_SCOPE_LABELS.get(str(skill.get("scope") or ""), skill.get("scope"))),
                _cell(skill.get("variant_label")),
                _state_cell(skill),
                _cell(skill.get("description")),
                _shown_path(skill.get("canonical_path"), display),
            )
            for skill in owned
        ]
        lines.extend(
            _table(
                (
                    "Name",
                    "Scope",
                    "Variant",
                    "State",
                    "Description",
                    "Canonical path",
                ),
                rows,
            )
        )
    return lines


def _doctor_lines(model: ReportModel, display: Callable[[str], str]) -> list[str]:
    findings = model.doctor.findings
    lines = ["## Doctor findings", ""]
    if not findings:
        lines.append("No findings.")
        return lines
    rows = [
        (
            _cell(finding.severity.value),
            _cell(finding.evidence.value),
            _cell(finding.rule_id),
            _cell(finding.code),
            _cell(finding.message),
            _shown_path(finding.path, display),
            _cell(finding.detail),
        )
        for finding in findings
    ]
    lines.extend(
        _table(
            ("Severity", "Evidence", "Rule", "Code", "Message", "Path", "Detail"),
            rows,
        )
    )
    return lines


def _compare_lines(compare: CompareReport, display: Callable[[str], str]) -> list[str]:
    counts = compare.counts_by_relation()
    count_rows = [
        (_cell(relation.value), _cell(counts[relation.value])) for relation in CompareRelation
    ]
    lines = [
        "## Compare highlights",
        "",
        f"Comparing **{_cell(compare.agent_a_name)}** ({_cell(compare.agent_a)})"
        f" with **{_cell(compare.agent_b_name)}** ({_cell(compare.agent_b)}).",
        "",
        *_table(("Relation", "Count"), count_rows),
    ]
    rows = [
        (
            _cell(entry.name),
            _cell(entry.relation.value),
            _shown_path(entry.path_a, display),
            _shown_path(entry.path_b, display),
        )
        for entry in compare.entries
        if entry.relation is not CompareRelation.SHARED
    ]
    if rows:
        lines.extend(["", *_table(("Skill", "Relation", "Path A", "Path B"), rows)])
    if compare.notes:
        lines.extend(["", "Notes:", *(f"- {_cell(note)}" for note in compare.notes)])
    return lines


def markdown_text(model: ReportModel, display: Callable[[str], str]) -> str:
    """Render one report as Markdown, without a trailing newline.

    The emission layer adds exactly one trailing newline; appending one here
    would produce two. ``display`` collapses a path for sharing and must be
    given only real paths (``None`` is handled before the call).
    """
    detected = _detected_ids(model.scan)
    lines = ["# Skill Lens Report", "", *_metadata_lines(model, display), ""]
    lines.extend(_detected_agent_lines(model, detected))
    lines.append("")
    lines.extend(_known_agent_lines(model, detected))
    lines.append("")
    lines.extend(_library_lines(model))
    lines.append("")
    lines.extend(_inventory_lines(model, display))
    lines.append("")
    lines.extend(_doctor_lines(model, display))
    if model.compare is not None:
        lines.append("")
        lines.extend(_compare_lines(model.compare, display))
    return "\n".join(lines)


__all__ = ["escape_markdown", "markdown_text"]
