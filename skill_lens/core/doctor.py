"""``skill-lens doctor``: hygiene and ecosystem-health findings.

Pure diagnostics -- no Rich, no writes, no repairs. Like the rest of the
engine the module takes a finished :class:`~skill_lens.core.discovery.
DiscoveryIndex` (or builds one) and emits frozen models; the walk it reports
on already swallowed every per-directory ``OSError`` into tagged unreadable
roots, so nothing here can crash on a hostile home folder.

Provenance rule (AGENTS.md rule 6): every finding carries its ``rule_id`` and
``evidence`` level. Checks that rest on vendor documentation -- only the Codex
context budget -- are tagged ``documented`` with their source; everything else
here is observed on disk and tagged ``empirical``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from skill_lens.core import paths
from skill_lens.core.discovery import DiscoveredEntry, DiscoveryIndex, discover
from skill_lens.core.system import (
    ERR_MISSING_FILE,
    ERR_NOT_JSON,
    installer_lockfile,
    live_discovery,
    read_json_guarded,
    shared_library,
)
from skill_lens.models.doctor import DoctorFinding, DoctorReport
from skill_lens.models.enums import Evidence, ParseStatus, Severity
from skill_lens.models.parsing import (
    ERR_DANGLING_SYMLINK,
    ERR_PERMISSION_DENIED,
    ERR_SYMLINK_CYCLE,
)

#: Codex prepends every skill description to the model context. Vendor docs
#: describe a budget of roughly 8,000 characters; past it Codex is documented
#: to omit skills silently. Source: https://developers.openai.com/codex/skills
#: (spec section 6, check 4). Module-level so tests can lower the threshold.
CODEX_CONTEXT_BUDGET_CHARS = 8_000

#: The agent whose context budget is known to be shared across skill
#: descriptions. Others are excluded until they document the same mechanism.
_BUDGET_AGENT = "codex"

#: Any path component named this is a traversal hazard: agent search rules
#: that recurse through installed dependency trees pick up third-party skill
#: files nobody authored (spec section 6, check 5 -- observed live).
_TRAVERSAL_MARKER = "node_modules"

#: Discovery's symlink error tag -> (finding code, message clause). The engine
#: only translates tags it already saw, so a new tag needs a row here -- and
#: the ERROR severity is deliberate: an entrypoint that reaches nothing is
#: exactly as un-loadable as a malformed file, whatever the reason.
_SYMLINK_CLAUSES = {
    ERR_DANGLING_SYMLINK: ("dangling_symlink", "links to a target that does not exist"),
    ERR_SYMLINK_CYCLE: ("symlink_cycle", "is part of a symlink loop"),
}


def build_doctor_report(
    home: Path,
    cwd: Path,
    index: DiscoveryIndex | None = None,
    registry: Any | None = None,
) -> DoctorReport:
    """Run every hygiene check over one discovery pass.

    ``index`` lets callers reuse the walk ``scan`` already paid for; when it
    is ``None`` a live discovery runs first. Order of findings is fixed
    (errors, then warnings, then info) so output is stable across runs.
    """
    discovery = index if index is not None else discover(home, cwd, registry)

    findings: list[DoctorFinding] = []
    findings.extend(_symlink_findings(discovery))
    findings.extend(_frontmatter_findings(discovery))
    findings.extend(_unreadable_findings(discovery))
    findings.extend(_codex_budget_findings(discovery))
    findings.extend(_traversal_findings(discovery))
    findings.extend(_farm_findings(discovery))
    findings.extend(_lockfile_findings(home))

    findings.sort(key=_severity_order)
    return DoctorReport(home=str(home), cwd=str(cwd), findings=tuple(findings))


def _severity_order(finding: DoctorFinding) -> tuple[int, str, str]:
    rank = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}[finding.severity]
    return (rank, finding.code, finding.path or "")


def _entrypoint(entry: DiscoveredEntry) -> str:
    """The path to show: the entrypoint as written, collapsed to ``~``."""
    return paths.display(entry.entrypoint_path)


def _symlink_findings(index: DiscoveryIndex) -> list[DoctorFinding]:
    """Broken links, cycles, and refusals: an entrypoint that reaches nothing (❌).

    Discovery already tagged every symlink it could not resolve -- this only
    groups those tags into findings, so a link that is broken for one agent
    is never judged healthy by another. A refusal comes in two shapes: the
    link's *target* is off-limits (``ERR_PERMISSION_DENIED`` on the entry) or
    the path resolves but the file inside is refused (an ``UNREADABLE`` parse
    -- how a chmod-000 skill directory under a readable root arrives). Same
    finding either way: the agent cannot open this skill.
    """
    findings: list[DoctorFinding] = []
    for entry in index.entries:
        code = entry.error_code
        detail: str | None = code
        if code in _SYMLINK_CLAUSES:
            finding_code, clause = _SYMLINK_CLAUSES[code]
        elif code == ERR_PERMISSION_DENIED:
            finding_code, clause = ("unreadable_skill", "exists but the OS refuses to open it")
        elif entry.parse is not None and entry.parse.status is ParseStatus.UNREADABLE:
            finding_code, clause = ("unreadable_skill", "exists but the OS refuses to open it")
            detail = ERR_PERMISSION_DENIED
        else:
            continue
        shown = _entrypoint(entry)
        findings.append(
            DoctorFinding(
                code=finding_code,
                severity=Severity.ERROR,
                message=f"'{shown}' {clause} -- {_reached_by(entry)} cannot load '{entry.name}'.",
                rule_id="doctor_symlink_health",
                evidence=Evidence.EMPIRICAL,
                path=shown,
                detail=detail,
            )
        )
    return findings


def _reached_by(entry: DiscoveredEntry) -> str:
    agents = sorted({hit.agent_id for hit in entry.hits})
    return ", ".join(agents) if agents else "no agent"


def _frontmatter_findings(index: DiscoveryIndex) -> list[DoctorFinding]:
    """Skills whose document will be rejected by any parser (❌).

    Discovery resolves the frontmatter state per *canonical target*; several
    agents reach it through the farm, so one finding names the library and
    lists who is affected.
    """
    findings: list[DoctorFinding] = []
    for entry in index.entries:
        status = entry.parse.status if entry.parse else None
        if status is ParseStatus.MALFORMED_YAML:
            message = (
                f"'{_entrypoint(entry)}' has no readable YAML frontmatter"
                f" -- {_reached_by(entry)} will skip '{entry.name}'."
            )
        elif status is ParseStatus.MISSING_DESCRIPTION:
            message = (
                f"'{_entrypoint(entry)}' is missing the required 'description' field"
                f" -- {_reached_by(entry)} will skip '{entry.name}'."
            )
        else:
            continue
        findings.append(
            DoctorFinding(
                code="malformed_frontmatter",
                severity=Severity.ERROR,
                message=message,
                rule_id="doctor_frontmatter",
                evidence=Evidence.EMPIRICAL,
                path=_entrypoint(entry),
                detail=(status.value if status else None),
            )
        )
    return findings


def _unreadable_findings(index: DiscoveryIndex) -> list[DoctorFinding]:
    """Roots macOS TCC (or mode bits) refuse to list (⚠️).

    This is the one finding a user cannot fix with their skills: the folder
    is there, agents are configured to read it, and the operating system says
    no. Full paths are intentional -- ``paths.display`` collapses to ``~``
    only when it is the *effective* home, so the report states exactly which
    directory was refused.
    """
    findings: list[DoctorFinding] = []
    for root in index.unreadable_roots:
        findings.append(
            DoctorFinding(
                code="unreadable_root",
                severity=Severity.WARNING,
                message=(
                    f"{root.agent_id}'s search path '{paths.display(root.path)}' "
                    "exists but cannot be read (macOS privacy protection or file "
                    "permissions) -- skills there are invisible to Skill Lens."
                ),
                rule_id="doctor_tcc",
                evidence=Evidence.EMPIRICAL,
                path=root.path,
                detail=root.detail,
            )
        )
    return findings


def _codex_budget_findings(index: DiscoveryIndex) -> list[DoctorFinding]:
    """The Codex context-budget check (⚠️, documented).

    Sums the description length of every *valid* skill description Codex
    reaches (any scope: personal, shared farm, project, system). Invalid
    skills are skipped by Codex itself, so they consume no budget and are
    honestly excluded -- the finding says what was counted.
    """
    total = 0
    counted = 0
    for entry in index.entries:
        if not any(hit.agent_id == _BUDGET_AGENT for hit in entry.hits):
            continue
        if entry.parse is None or entry.parse.status is not ParseStatus.VALID:
            continue
        if entry.parse.description:
            total += len(entry.parse.description)
            counted += 1
    if total <= CODEX_CONTEXT_BUDGET_CHARS:
        return []
    over = total - CODEX_CONTEXT_BUDGET_CHARS
    return [
        DoctorFinding(
            code="codex_context_budget",
            severity=Severity.WARNING,
            message=(
                f"{counted} Codex-reachable skill descriptions total {total:,} characters, "
                f"about {over:,} over the ~{CODEX_CONTEXT_BUDGET_CHARS:,} documented budget "
                "-- Codex may silently omit some skills."
            ),
            rule_id="doctor_codex_context_budget",
            evidence=Evidence.DOCUMENTED,
            detail=f"https://developers.openai.com/codex/skills; counted={total}",
        )
    ]


def _traversal_findings(index: DiscoveryIndex) -> list[DoctorFinding]:
    """Recursive roots that walk through dependency trees (⚠️).

    Observed live: a recursive plugin/profile root descended into
    ``node_modules`` and surfaced third-party skills nobody installed on
    purpose. One finding per agent that saw such an entrypoint.

    Scope note: discovery only descends into directories named ``skills``
    (spec section 5 forbids unbounded crawls), so a ``SKILL.md`` inside
    ``node_modules`` that is *not* under a ``skills/`` folder is never even
    collected -- the hazard this check reports is a recursive ``skills``
    root punching through a dependency tree, the realistic live shape.
    """
    findings: list[DoctorFinding] = []
    seen: set[tuple[str, str]] = set()
    for entry in index.entries:
        if _TRAVERSAL_MARKER not in Path(entry.entrypoint_path).parts:
            continue
        for hit in entry.hits:
            key = (hit.agent_id, hit.root_id)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                DoctorFinding(
                    code="traversal_hazard",
                    severity=Severity.WARNING,
                    message=(
                        f"{hit.agent_id}'s root '{hit.root_id}' recursed through a "
                        f"'{_TRAVERSAL_MARKER}' tree and found '{entry.name}' -- "
                        "third-party skill files may load unintentionally."
                    ),
                    rule_id="doctor_traversal_hazard",
                    evidence=Evidence.EMPIRICAL,
                    path=paths.display(entry.entrypoint_path),
                    detail=_TRAVERSAL_MARKER,
                )
            )
    return findings


def _farm_findings(index: DiscoveryIndex) -> list[DoctorFinding]:
    """Symlink farm health (info).

    The ecosystem pattern is one shared library (``~/.agents/skills``) linked
    into each agent's folder. A skill is "farmed" when its canonical target
    sits in that library and agents reach it through symlinked entrypoints
    stored elsewhere. This states the numbers plainly: N farmed skills behind
    K links. It is informational -- a farm is healthy by design -- but it
    explains why the same skill shows up under several agents in ``scan``.
    """
    # Resolve the library to a canonical path or a symlinked home (macOS
    # ``/tmp`` is ``/private/tmp``) would compare two spellings of one place.
    library = str(shared_library(Path(index.home)).resolve())
    farmed = 0
    link_count = 0
    for entry in index.entries:
        canonical = entry.canonical_path
        if not canonical or not _under(canonical, library):
            continue
        links = [
            path
            for path in (entry.entrypoint_paths or (entry.entrypoint_path,))
            if Path(path).is_symlink() and not _under(path, library)
        ]
        if not links:
            continue
        farmed += 1
        link_count += len(links)
    if not farmed:
        return []
    return [
        DoctorFinding(
            code="symlink_farm",
            severity=Severity.INFO,
            message=(
                f"{farmed} skills are shared through symlink farms "
                f"({link_count} links point into one library) -- that is the "
                "installer's normal layout, not a defect."
            ),
            rule_id="doctor_symlink_farm",
            evidence=Evidence.EMPIRICAL,
            detail=f"library={paths.display(library)}",
        )
    ]


def _under(path_str: str, parent_str: str) -> bool:
    """True when ``path_str`` sits inside ``parent_str`` (component-safe)."""
    try:
        Path(path_str).relative_to(parent_str)
    except ValueError:
        return False
    return True


def _lockfile_findings(home: Path) -> list[DoctorFinding]:
    """Installer lockfile status (ℹ️, or ⚠️ when unparseable).

    ``~/.agents/.skill-lock.json`` records how the shared library was
    installed. Missing is normal (no installer ever ran); invalid JSON means
    an installer wrote garbage and will mis-read it later, which is worth a
    warning; a readable file gets an informational line so the user knows
    Skill Lens saw it.
    """
    lockfile = installer_lockfile(home)
    value, error = read_json_guarded(lockfile)
    shown = paths.display(lockfile)
    if error == ERR_MISSING_FILE:
        return [
            DoctorFinding(
                code="installer_lockfile",
                severity=Severity.INFO,
                message=f"No installer lockfile at '{shown}' (normal if you never ran one).",
                rule_id="doctor_installer_lockfile",
                evidence=Evidence.EMPIRICAL,
                path=shown,
                detail=ERR_MISSING_FILE,
            )
        ]
    if error == ERR_PERMISSION_DENIED:
        return [
            DoctorFinding(
                code="installer_lockfile",
                severity=Severity.WARNING,
                message=f"'{shown}' exists but cannot be read (file permissions).",
                rule_id="doctor_installer_lockfile",
                evidence=Evidence.EMPIRICAL,
                path=shown,
                detail=error,
            )
        ]
    if error == ERR_NOT_JSON:
        return [
            DoctorFinding(
                code="installer_lockfile",
                severity=Severity.WARNING,
                message=f"'{shown}' is not valid JSON -- the installer may mis-read it.",
                rule_id="doctor_installer_lockfile",
                evidence=Evidence.EMPIRICAL,
                path=shown,
                detail=ERR_NOT_JSON,
            )
        ]
    entries = len(value) if isinstance(value, (list, dict)) else 0
    return [
        DoctorFinding(
            code="installer_lockfile",
            severity=Severity.INFO,
            message=f"Installer lockfile '{shown}' parses cleanly ({entries} top-level keys).",
            rule_id="doctor_installer_lockfile",
            evidence=Evidence.EMPIRICAL,
            path=shown,
            detail="ok",
        )
    ]


def run_doctor(cwd: Path | None = None) -> DoctorReport:
    """One-call entry point used by the CLI: live discovery, then report."""
    discovery = live_discovery(cwd)
    return build_doctor_report(Path(discovery.home), Path(discovery.cwd), discovery)
