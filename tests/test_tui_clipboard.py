"""Headless clipboard-copy tests for the TUI ``y`` action (OSC 52).

Every test uses the synthetic ``mock_home`` fixture and the protected-system-root
guard from ``tests/conftest.py``; no real ``$HOME`` is read.  Clipboard tests pin
``TMUX`` and ``TERM`` explicitly (except the deliberately missing-key case) and
never read or set ``TERM_PROGRAM``.  The OSC 52 payload is captured by spying on
the instance driver, so no real terminal clipboard is involved.

The Why and Diff expected strings are authored from the frozen plan's recipes,
not captured from the implementation's own output, and each is asserted against
a screen-equivalence oracle reading the mounted widgets.
"""

from __future__ import annotations

import asyncio
import base64
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Collapsible, DataTable, Static
from typer.testing import CliRunner

import skill_lens.tui.app as app_module
from skill_lens.cli import app as cli_app
from skill_lens.core.snapshot import snapshot_path
from skill_lens.models.diff import DiffChange, DiffCopy, DiffFile, DiffHunk, DiffReport
from skill_lens.models.doctor import DoctorFinding, DoctorReport
from skill_lens.models.enums import (
    Collision,
    Evidence,
    HeadlineState,
    ParseStatus,
    Scope,
    Severity,
    Visibility,
)
from skill_lens.models.installation import SkillInstallation
from skill_lens.models.resolution import CandidateResolution, ResolutionReport
from skill_lens.presentation import (
    BASELINE_LABEL,
    BINARY_MARKER,
    COPIES_LABEL,
    NOTE_LABEL,
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
from skill_lens.presentation.state import STATE_MARK
from skill_lens.tui import clipboard
from skill_lens.tui.agents import AgentsScreen
from skill_lens.tui.app import SkillLensApp
from skill_lens.tui.compare import CompareScreen
from skill_lens.tui.diff import DiffScreen
from skill_lens.tui.doctor import DoctorScreen, finding_detail_text
from skill_lens.tui.help import HelpScreen
from skill_lens.tui.home import HomeScreen
from skill_lens.tui.json_view import JsonView
from skill_lens.tui.why import WhyScreen
from tests.fixtures.scenarios import build_scenario

runner = CliRunner()

OSC52_PREFIX = "\x1b]52;c;"


@pytest.fixture(autouse=True)
def _pin_clipboard_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the two environment keys the decision reads, in both branches."""
    monkeypatch.setenv("TMUX", "")
    monkeypatch.setenv("TERM", "xterm-256color")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _until(pilot: Any, predicate: Any, label: str, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        await pilot.pause(0.01)
    raise AssertionError(f"timed out waiting for {label}")


async def _wait_ready(pilot: Any, app: SkillLensApp) -> None:
    await _until(
        pilot,
        lambda: (
            app.controller.current is not None
            and app.controller.pending_generation is None
            and app.controller.status == "ready"
        ),
        "ready session",
    )
    await pilot.pause(0.02)


def _spy_writes(app: SkillLensApp, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Capture exactly what ``App.copy_to_clipboard`` writes to the driver."""
    writes: list[str] = []
    driver = app._driver
    assert driver is not None
    monkeypatch.setattr(driver, "write", writes.append)
    return writes


def _decode_osc52(payload: str) -> str:
    assert payload.startswith(OSC52_PREFIX), payload[:20]
    assert payload.endswith("\a")
    encoded = payload[len(OSC52_PREFIX) : -1]
    return base64.b64decode(encoded).decode("utf-8")


def _notice(screen: Any) -> str:
    return str(screen.query_one("#copy-notice", Static).content)


def _notice_shown(screen: Any) -> bool:
    return bool(screen.query_one("#copy-notice", Static).display)


def _bar_keys(content: Any) -> list[str]:
    keys: list[str] = []
    for span in content.spans:
        text = content.plain[span.start : span.end].replace("\u2800", "").strip()
        if text and "on" in str(span.style):
            keys.append(text)
    return keys


def _why_expected(
    report: ResolutionReport,
    snapshot: Any,
    key: str,
    agent_id: str | None,
) -> str:
    """Independent implementation of the plan's one-string Why recipe."""
    entry = next((row for row in snapshot.scan.skills if row.canonical_path == key), None)
    agent_name = next(
        (agent.name for agent in snapshot.registry if agent.id == agent_id),
        agent_id or "—",
    )
    lines = [f"Installation: {snapshot_path(snapshot, key)}"]
    if entry is not None:
        lines.append(f"Name: {entry.name}")
    lines.append(f"Working directory: {snapshot_path(snapshot, str(snapshot.cwd))}")
    lines.append(f"Agent: {agent_name}")
    lines.extend(
        [
            f"Lookup name: {report.skill_name}",
            f"Collision policy: {report.collision_policy} ({report.policy_evidence.value})",
            f"Report-wide headline: {report.headline.value}",
        ]
    )
    lines.extend(f"Note: {note}" for note in report.notes)
    title = "\n".join(lines)
    if not report.candidates:
        return title
    parts = [title]
    for candidate in report.candidates:
        inst = candidate.installation
        variant = f"  [{inst.variant_label}]" if inst.variant_label else ""
        block = [
            f"{STATE_MARK[candidate.state]} {inst.name}{variant}",
            f"  Canonical: {snapshot_path(snapshot, inst.canonical_path)}",
        ]
        if inst.canonical_path != inst.entrypoint_path:
            block.append(f"  Entrypoint: {snapshot_path(snapshot, inst.entrypoint_path)}")
        block.append(
            f"  Hash: {inst.content_hash[:23]}..." if inst.content_hash else "  Hash: none"
        )
        block.append(f"Reason: {candidate.reason}")
        block.append(f"Rule: {candidate.rule_id}  Evidence: {candidate.evidence.value}")
        block.extend(f"  Note: {note}" for note in report.notes)
        title_line = (
            f"{STATE_MARK[candidate.state]} {inst.name}{variant}  ({candidate.state.value})"
        )
        parts.append(title_line + "\n" + "\n".join(block))
    return "\n\n".join(parts)


def _why_oracle(screen: WhyScreen) -> str:
    """The same string, read back from the mounted widgets."""
    title = str(screen.query_one("#why-title", Static).content)
    container = screen.query_one("#why-candidates", VerticalScroll)
    collapsibles = [child for child in container.children if isinstance(child, Collapsible)]
    if not collapsibles:
        return title
    parts = [title]
    for collapsible in collapsibles:
        body = next(widget for widget in collapsible.query(Static) if type(widget) is Static)
        parts.append(f"{collapsible.title}\n{body.content}")
    return "\n\n".join(parts)


def _diff_expected(report: DiffReport, snapshot: Any) -> str:
    """Independent implementation of the plan's one-string Diff recipe."""
    if not report.found:
        return not_found_message(report)
    blocks: list[str] = []
    baseline = next((copy for copy in report.copies if copy.is_baseline), None)
    display = snapshot_path(snapshot, baseline.path) if baseline is not None else None
    blocks.append(
        f"{COPIES_LABEL} {len(report.copies)}\n"
        f"{BASELINE_LABEL} {baseline_text(baseline, display_path=display)}"
    )
    listing = True
    if not report.has_differences:
        notice = no_differences_message(report)
        blocks.append(f"{notice.label}{notice.body}")
        listing = needs_listing(report)
    if listing:
        baseline_exists = report.baseline_path is not None
        for copy in report.copies:
            parts = copy_heading(
                copy,
                baseline_exists=baseline_exists,
                display_path=snapshot_path(snapshot, copy.path),
            )
            lines = [
                f"{parts.mark} {parts.path}{parts.variant} "
                f"({parts.scope}, {parts.parse_status})  {parts.status}"
            ]
            body = copy_body(copy, baseline_exists=baseline_exists)
            if body is not None:
                lines.append(f"  {body}")
            else:
                for file in copy.files:
                    marker = f" {BINARY_MARKER}" if file.is_binary else ""
                    lines.append(f"  {file.path} {file.change.value}{marker}")
                    notice = file_notice(file)
                    if notice is not None:
                        lines.append(f"    {notice}")
                    else:
                        lines.extend(unified_text(file).split("\n"))
            truncation = copy_truncation_notice(copy)
            if truncation is not None:
                lines.append(f"  {truncation.label}{truncation.body}")
            blocks.append("\n".join(lines))
        truncation = report_truncation_notice(report)
        if truncation is not None:
            blocks.append(f"{truncation.label}{truncation.body}")
    if report.baseline_path is not None:
        blocks.append("\n".join(f"{NOTE_LABEL} {note}" for note in report.notes))
    return "\n\n".join(blocks)


def _diff_oracle(screen: DiffScreen) -> str:
    content = screen.query_one("#diff-content")
    return "\n\n".join(str(widget.content) for widget in content.query(Static))


def _cli_document(*args: str) -> str:
    result = runner.invoke(cli_app, [*args, "--json"])
    assert result.exit_code == 0, result.output
    return result.stdout.removesuffix("\n")


async def _choose_table_key(pilot: Any, table: DataTable, key: str) -> None:
    target = next(
        index
        for index in range(table.row_count)
        if str(table.coordinate_to_cell_key((index, 0)).row_key.value) == key
    )
    for _ in range(table.row_count + 1):
        if table.cursor_row == target:
            break
        await pilot.press("down" if table.cursor_row < target else "up")
        await pilot.pause(0.01)
    await pilot.press("enter")
    await pilot.pause()


def _candidate(
    *,
    state: HeadlineState,
    canonical: str,
    entrypoint: str | None = None,
    variant: str | None = None,
    content_hash: str | None = None,
    reason: str,
    rule_id: str,
    evidence: Evidence,
    scope: Scope = Scope.PROJECT,
) -> CandidateResolution:
    return CandidateResolution(
        state=state,
        visibility=Visibility.ACTIVE_ROOT,
        collision=Collision.WINNING_ENTRY,
        rule_id=rule_id,
        evidence=evidence,
        reason=reason,
        rank=1,
        installation=SkillInstallation(
            name="deploy",
            entrypoint_path=entrypoint or canonical,
            canonical_path=canonical,
            scope=scope,
            parse_status=ParseStatus.VALID,
            content_hash=content_hash,
            variant_label=variant,
        ),
    )


def _why_report(*candidates: CandidateResolution, notes: tuple[str, ...] = ()) -> ResolutionReport:
    return ResolutionReport(
        skill_name="deploy",
        agent="claude",
        agent_name="Claude Code",
        cwd="/mock/cwd",
        collision_policy="prefer_user",
        policy_evidence=Evidence.DOCUMENTED,
        headline=HeadlineState.SHADOWED,
        candidates=candidates,
        notes=notes,
    )


def _diff_report(snapshot: Any, *, kind: str = "full") -> tuple[DiffReport, str, str]:
    entry = next(row for row in snapshot.scan.skills if row.name == "deploy")
    raw = entry.canonical_path
    display = snapshot_path(snapshot, raw)
    if kind == "not_found":
        return (
            DiffReport(
                skill_name="ghost",
                home=str(snapshot.home),
                cwd=str(snapshot.cwd),
                found=False,
            ),
            raw,
            display,
        )
    baseline = DiffCopy(
        path=raw,
        scope=entry.scope,
        parse_status=entry.parse_status,
        is_valid=True,
        is_readable=True,
        is_baseline=True,
    )
    if kind == "no_differences":
        other = DiffCopy(
            path="/mock/other/deploy",
            scope=Scope.PROJECT,
            parse_status=ParseStatus.VALID.value,
            is_valid=True,
            is_readable=True,
        )
        report = DiffReport(
            skill_name="deploy",
            home=str(snapshot.home),
            cwd=str(snapshot.cwd),
            found=True,
            baseline_path=raw,
            copies=(baseline, other),
            notes=("Both copies match.",),
        )
        return report, raw, display
    other = DiffCopy(
        path="/mock/other/deploy",
        scope=Scope.PROJECT,
        parse_status=ParseStatus.VALID.value,
        is_valid=True,
        is_readable=True,
        variant_label="B",
        files=(
            DiffFile(
                path=raw,
                change=DiffChange.MODIFIED,
                hunks=(
                    DiffHunk(
                        old_start=1,
                        old_count=1,
                        new_start=1,
                        new_count=2,
                        lines=(" context", "-old", "+new", "+extra"),
                    ),
                ),
            ),
            DiffFile(path="logo.png", change=DiffChange.ADDED, is_binary=True),
            DiffFile(path="notes.txt", change=DiffChange.ADDED),
        ),
        truncated=True,
        omitted_lines=2,
    )
    unreadable = DiffCopy(
        path="/mock/unreadable/deploy",
        scope=Scope.USER,
        parse_status=ParseStatus.UNREADABLE.value,
        is_valid=False,
        is_readable=False,
        error="dangling_symlink",
    )
    report = DiffReport(
        skill_name="deploy",
        home=str(snapshot.home),
        cwd=str(snapshot.cwd),
        found=True,
        baseline_path=raw,
        copies=(baseline, other, unreadable),
        truncated=True,
        omitted_chars=42,
        notes=("First note.", "Second note."),
    )
    return report, raw, display


# ---------------------------------------------------------------------------
# Pure decision
# ---------------------------------------------------------------------------


def test_pure_decision_blocks_tmux_and_screen_before_the_size_guard() -> None:
    exact = "é" * (clipboard.MAX_COPY_BYTES // 2)
    assert len(exact.encode("utf-8")) == clipboard.MAX_COPY_BYTES
    too_big = exact + "a"
    assert len(too_big.encode("utf-8")) == clipboard.MAX_COPY_BYTES + 1

    assert (
        clipboard.copy_decision("text", {"TERM": "xterm-256color"}) is clipboard.CopyDecision.SENT
    )
    assert (
        clipboard.copy_decision("text", {"TMUX": "session", "TERM": "xterm-256color"})
        is clipboard.CopyDecision.BLOCKED
    )
    assert (
        clipboard.copy_decision("text", {"TMUX": "", "TERM": "screen-256color"})
        is clipboard.CopyDecision.BLOCKED
    )
    assert (
        clipboard.copy_decision(too_big, {"TMUX": "session", "TERM": "screen-256color"})
        is clipboard.CopyDecision.BLOCKED
    )
    assert clipboard.copy_decision(exact, {"TERM": "xterm-256color"}) is clipboard.CopyDecision.SENT
    assert (
        clipboard.copy_decision(too_big, {"TERM": "xterm-256color"})
        is clipboard.CopyDecision.TOO_LARGE
    )
    # Missing keys are not blockers.
    assert clipboard.copy_decision("text", {}) is clipboard.CopyDecision.SENT


@pytest.mark.parametrize(
    "screen_type",
    [HomeScreen, WhyScreen, DiffScreen, DoctorScreen, AgentsScreen, CompareScreen],
)
def test_copy_binding_is_non_priority_and_named_copy(screen_type: type[Any]) -> None:
    """Input must keep consuming y as filter text; the action is named copy."""
    binding = next(
        binding
        for binding in screen_type.BINDINGS
        if isinstance(binding, Binding) and binding.key == "y"
    )
    assert binding.action == "copy"
    assert binding.priority is False


def test_readme_states_the_clipboard_key_and_its_limits() -> None:
    """The user-facing README carries the same limitation as Help notes."""
    text = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "`y` copies the focused content through the terminal clipboard (OSC 52)" in normalized
    assert clipboard.CLIPBOARD_LIMITATION in normalized


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------


def test_home_copies_the_raw_canonical_path_and_emits_one_osc52(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home = app.screen
            assert isinstance(home, HomeScreen)
            key = app.controller.selected_key
            assert key is not None and key.startswith("/")
            display = app.controller.current.display_paths[key]
            assert display != key, "the preview path must be shortened for this assertion"

            writes = _spy_writes(app, monkeypatch)
            await pilot.press("y")
            await pilot.pause()

            assert len(writes) == 1
            assert _decode_osc52(writes[0]) == key
            assert app.clipboard == key
            assert _notice(home) == "Copied skill path"
            assert _notice_shown(home)
            await pilot.press("q")

    asyncio.run(_run())


def test_home_empty_table_copies_nothing(mock_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            writes = _spy_writes(app, monkeypatch)
            await pilot.press("y")
            await pilot.pause()
            assert writes == []
            assert _notice(app.screen) == "Nothing to copy yet."
            assert _notice_shown(app.screen)
            await pilot.press("q")

    asyncio.run(_run())


def test_home_json_round_trip_still_copies_the_canonical_path(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home = app.screen
            assert isinstance(home, HomeScreen)
            key = app.controller.selected_key
            assert key is not None

            await pilot.press("J")
            await pilot.pause()
            view = home.query_one("#home-json", JsonView)
            stale_document = view.document
            assert stale_document is not None
            await pilot.press("escape")
            await pilot.pause()
            assert home.json_mode is False
            assert view.document == stale_document

            writes = _spy_writes(app, monkeypatch)
            await pilot.press("y")
            await pilot.pause()
            assert len(writes) == 1
            assert _decode_osc52(writes[0]) == key
            assert app.clipboard != stale_document
            assert _notice(home) == "Copied skill path"
            await pilot.press("q")

    asyncio.run(_run())


def test_home_explanation_json_copies_nothing(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Home's JSON view may show an explanation; copying it is still nothing."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home = app.screen
            assert isinstance(home, HomeScreen)
            home.enter_json_mode()
            await pilot.pause()
            view = home.query_one("#home-json", JsonView)
            view.show_explanation("No document.")
            assert view.shows_document is False

            writes = _spy_writes(app, monkeypatch)
            await pilot.press("y")
            await pilot.pause()
            assert writes == []
            assert _notice(home) == "Nothing to copy yet."
            assert _notice_shown(home)
            await pilot.press("q")

    asyncio.run(_run())


def test_missing_tmux_and_term_keys_do_not_block(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            monkeypatch.delenv("TMUX")
            monkeypatch.delenv("TERM")
            writes = _spy_writes(app, monkeypatch)
            await pilot.press("y")
            await pilot.pause()
            assert len(writes) == 1
            assert app.clipboard == app.controller.selected_key
            await pilot.press("q")

    asyncio.run(_run())


@pytest.mark.parametrize(
    ("variable", "value"),
    [("TMUX", "tmux-session"), ("TERM", "screen-256color")],
)
def test_blocked_terminal_emits_nothing_and_shows_the_exact_notice(
    mock_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
    value: str,
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            monkeypatch.setenv(variable, value)
            writes = _spy_writes(app, monkeypatch)
            await pilot.press("y")
            await pilot.pause()
            assert writes == []
            assert app.clipboard == ""
            assert _notice(app.screen) == "Clipboard not supported in this terminal"
            await pilot.press("q")

    asyncio.run(_run())


def test_size_guard_uses_utf8_bytes_and_blocked_still_outranks_it(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home = app.screen
            assert isinstance(home, HomeScreen)
            home.enter_json_mode()
            await pilot.pause()
            view = home.query_one("#home-json", JsonView)

            exact = "é" * (clipboard.MAX_COPY_BYTES // 2)
            assert len(exact.encode("utf-8")) == clipboard.MAX_COPY_BYTES
            view._document = exact
            view._text = exact
            writes = _spy_writes(app, monkeypatch)
            await pilot.press("y")
            await pilot.pause()
            assert len(writes) == 1
            assert _decode_osc52(writes[0]) == exact
            assert _notice(home) == "Copied JSON"

            too_big = exact + "a"
            view._document = too_big
            view._text = too_big
            writes.clear()
            await pilot.press("y")
            await pilot.pause()
            assert writes == []
            assert _notice(home) == "Too large to copy via terminal clipboard"

            monkeypatch.setenv("TMUX", "tmux-session")
            writes.clear()
            await pilot.press("y")
            await pilot.pause()
            assert writes == []
            assert _notice(home) == "Clipboard not supported in this terminal"
            await pilot.press("q")

    asyncio.run(_run())


def test_notice_timer_is_replaced_and_expires(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    monkeypatch.setattr(clipboard, "COPY_NOTICE_SECONDS", 0.4)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home = app.screen
            await pilot.press("y")
            await pilot.pause()
            assert _notice(home) == "Copied skill path"

            await asyncio.sleep(0.27)
            await pilot.pause()
            await pilot.press("y")
            await pilot.pause()
            await asyncio.sleep(0.2)
            await pilot.pause()
            assert _notice(home) == "Copied skill path", "the first timer must have been stopped"

            await asyncio.sleep(0.5)
            await pilot.pause()
            assert _notice(home) == ""
            assert not _notice_shown(home)
            await pilot.press("q")

    asyncio.run(_run())


def test_home_notice_clears_when_a_detail_covers_it(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home = app.screen
            assert isinstance(home, HomeScreen)
            await pilot.press("y")
            await pilot.pause()
            assert _notice(home) == "Copied skill path"

            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            await pilot.pause()
            assert _notice(home) == ""
            assert not _notice_shown(home)
            assert home._copy_notice_timer is None

            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")
            assert _notice(home) == ""
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Why
# ---------------------------------------------------------------------------


def test_why_copy_matches_the_recipe_and_the_screen_oracle(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            snapshot = app.controller.current
            key = app.controller.selected_key
            assert key is not None
            report = _why_report(
                _candidate(
                    state=HeadlineState.SHADOWED,
                    canonical="/mock/alpha",
                    variant="B",
                    content_hash="a" * 40,
                    reason="a project copy wins",
                    rule_id="rule-shadow",
                    evidence=Evidence.EMPIRICAL,
                ),
                _candidate(
                    state=HeadlineState.ACTIVE,
                    canonical="/mock/beta",
                    entrypoint="/mock/beta-link",
                    reason="the only copy",
                    rule_id="rule-active",
                    evidence=Evidence.DOCUMENTED,
                    scope=Scope.USER,
                ),
                notes=("Shared report note.",),
            )
            monkeypatch.setattr(app_module, "snapshot_why", lambda snap, k, a: report)
            expected = _why_expected(report, snapshot, key, "claude")

            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            why = app.screen
            await _until(pilot, lambda: why._report is not None, "Why report")
            writes = _spy_writes(app, monkeypatch)
            await pilot.press("y")
            await pilot.pause()

            assert len(writes) == 1
            assert _decode_osc52(writes[0]) == expected
            assert app.clipboard == expected
            assert _why_oracle(why) == expected
            assert _notice(why) == "Copied resolution explanation"
            assert "o deploy  [B]  (SHADOWED)" in expected
            assert "o deploy  [B]\n  Canonical: /mock/alpha" in expected
            assert "Rule: rule-shadow  Evidence: empirical" in expected
            await pilot.press("q")

    asyncio.run(_run())


def test_why_zero_candidate_report_is_the_title_alone(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            snapshot = app.controller.current
            key = app.controller.selected_key
            assert key is not None
            report = _why_report(notes=("Still report data.",))
            monkeypatch.setattr(app_module, "snapshot_why", lambda snap, k, a: report)
            expected = _why_expected(report, snapshot, key, "claude")

            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            why = app.screen
            await _until(pilot, lambda: why._report is not None, "Why report")
            writes = _spy_writes(app, monkeypatch)
            await pilot.press("y")
            await pilot.pause()

            assert len(writes) == 1
            assert _decode_osc52(writes[0]) == expected
            assert _why_oracle(why) == expected
            assert not expected.endswith("\n")
            assert "No candidates evaluated" not in expected
            assert "No copies of this skill name" not in expected
            await pilot.press("q")

    asyncio.run(_run())


def test_why_pending_report_and_explanation_json_copy_nothing(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            why = app.screen
            await _until(pilot, lambda: why._report is not None, "Why report")
            why._report = None
            why._owned_request = object()  # type: ignore[assignment]
            app.controller.cache.clear()
            writes = _spy_writes(app, monkeypatch)
            await pilot.press("y")
            await pilot.pause()
            assert writes == []
            assert _notice(why) == "Nothing to copy yet."

            await pilot.press("J")
            await pilot.pause()
            view = why.query_one("#why-json", JsonView)
            assert view.shows_document is False
            writes.clear()
            await pilot.press("y")
            await pilot.pause()
            assert writes == []
            assert _notice(why) == "Nothing to copy yet."
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["full", "no_differences", "not_found"])
def test_diff_copy_matches_the_recipe_and_the_screen_oracle(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            snapshot = app.controller.current
            report, raw, display = _diff_report(snapshot, kind=kind)
            monkeypatch.setattr(app_module, "snapshot_diff", lambda snap, key: report)
            expected = _diff_expected(report, snapshot)

            await pilot.press("d")
            await _until(pilot, lambda: isinstance(app.screen, DiffScreen), "Diff")
            diff = app.screen
            await _until(pilot, lambda: diff.report is not None, "Diff report")
            writes = _spy_writes(app, monkeypatch)
            await pilot.press("y")
            await pilot.pause()

            assert len(writes) == 1
            assert _decode_osc52(writes[0]) == expected
            assert app.clipboard == expected
            assert _diff_oracle(diff) == expected
            assert _notice(diff) == "Copied diff"
            if kind == "full":
                assert "  logo.png added binary" in expected
                assert "    Binary content differs and is never printed." in expected
                assert "[ binary]" not in expected
                assert f"  {raw} modified" in expected
                assert f"  {display} modified" not in expected
                assert "  Truncated: 2 changed lines omitted." in expected
                assert "\n\nTruncated: 42 characters" in expected
                assert "\n\nNote: First note.\nNote: Second note." in expected
            elif kind == "no_differences":
                assert "No differences: all 2 readable copies are identical." in expected
            else:
                assert expected == not_found_message(report)
            await pilot.press("q")

    asyncio.run(_run())


def test_diff_pending_report_copies_nothing(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("d")
            await _until(pilot, lambda: isinstance(app.screen, DiffScreen), "Diff")
            diff = app.screen
            await _until(pilot, lambda: diff.report is not None, "Diff report")
            diff._report = None
            diff._owned_request = object()  # type: ignore[assignment]
            writes = _spy_writes(app, monkeypatch)
            await pilot.press("y")
            await pilot.pause()
            assert writes == []
            assert _notice(diff) == "Nothing to copy yet."
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------


def _doctor_capture(finding: DoctorFinding | None):
    real_capture = app_module.capture_session

    def capture_with_doctor(**kwargs: Any) -> Any:
        snapshot = real_capture(**kwargs)
        findings = () if finding is None else (finding,)
        report = DoctorReport(snapshot.doctor.home, snapshot.doctor.cwd, findings)
        return replace(snapshot, doctor=report)

    return capture_with_doctor


def test_doctor_copies_the_selected_finding_details(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    finding = DoctorFinding(
        code="clipboard_finding",
        severity=Severity.WARNING,
        message="A captured warning.",
        rule_id="clipboard_rule",
        evidence=Evidence.EMPIRICAL,
        path="/mock/path",
        detail="Literal detail.",
    )
    monkeypatch.setattr(app_module, "capture_session", _doctor_capture(finding))

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("h")
            await _until(pilot, lambda: isinstance(app.screen, DoctorScreen), "Doctor")
            doctor = app.screen
            expected = finding_detail_text(finding)
            writes = _spy_writes(app, monkeypatch)
            await pilot.press("y")
            await pilot.pause()
            assert len(writes) == 1
            assert _decode_osc52(writes[0]) == expected
            assert app.clipboard == expected
            assert _notice(doctor) == "Copied finding details"
            await pilot.press("q")

    asyncio.run(_run())


def test_doctor_with_no_findings_copies_nothing(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    monkeypatch.setattr(app_module, "capture_session", _doctor_capture(None))

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("h")
            await _until(pilot, lambda: isinstance(app.screen, DoctorScreen), "Doctor")
            writes = _spy_writes(app, monkeypatch)
            await pilot.press("y")
            await pilot.pause()
            assert writes == []
            assert _notice(app.screen) == "Nothing to copy yet."
            assert _notice_shown(app.screen)
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Agents and Compare
# ---------------------------------------------------------------------------


def test_agents_and_compare_copy_nothing_with_exact_notices(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            await pilot.press("g")
            await _until(pilot, lambda: isinstance(app.screen, AgentsScreen), "Agents")
            agents = app.screen
            await pilot.pause()
            writes = _spy_writes(app, monkeypatch)
            await pilot.press("y")
            await pilot.pause()
            assert writes == []
            assert _notice(agents) == "Nothing to copy here. Press J for JSON, then y."
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")

            await pilot.press("c")
            await _until(pilot, lambda: isinstance(app.screen, CompareScreen), "Compare")
            compare = app.screen
            await pilot.pause()
            writes.clear()
            await pilot.press("y")
            await pilot.pause()
            assert writes == []
            assert _notice(compare) == ("Nothing to copy in the picker. Choose two agents first.")

            await _choose_table_key(
                pilot, compare.query_one("#compare-a-table", DataTable), "claude"
            )
            await _choose_table_key(
                pilot, compare.query_one("#compare-b-table", DataTable), "codex"
            )
            await _until(pilot, lambda: compare.report is not None, "Compare report")
            assert compare.json_mode is False
            assert compare.query_one("#compare-json", JsonView).document is not None
            await pilot.pause()
            writes.clear()
            await pilot.press("y")
            await pilot.pause()
            assert writes == []
            assert _notice(compare) == "Nothing to copy here. Press J for JSON, then y."
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# JSON mode on all six screens
# ---------------------------------------------------------------------------


def test_all_six_json_views_copy_the_cli_document(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    project = mock_home / "project"

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            writes = _spy_writes(app, monkeypatch)

            await pilot.press("J")
            await pilot.pause()
            home_document = app.screen.query_one("#home-json", JsonView).document
            cli_home = _cli_document("scan", "--sandbox", str(mock_home), "--cwd", str(project))
            assert home_document == cli_home
            writes.clear()
            await pilot.press("y")
            await pilot.pause()
            assert len(writes) == 1
            assert app.clipboard == cli_home
            assert _decode_osc52(writes[0]) == cli_home
            await pilot.press("escape")

            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            why = app.screen
            await _until(pilot, lambda: why._report is not None, "Why report")
            why_cli = _cli_document(
                "why",
                "deploy",
                "--agent",
                str(why._agent_id),
                "--sandbox",
                str(mock_home),
                "--cwd",
                str(project),
            )
            await pilot.press("J")
            await pilot.pause()
            assert why.query_one("#why-json", JsonView).document == why_cli
            writes.clear()
            await pilot.press("y")
            await pilot.pause()
            assert len(writes) == 1
            assert app.clipboard == why_cli
            assert _decode_osc52(writes[0]) == why_cli

            await pilot.press("J")
            await pilot.pause()
            await pilot.press("d")
            await _until(pilot, lambda: isinstance(app.screen, DiffScreen), "Diff")
            diff = app.screen
            await _until(pilot, lambda: diff.report is not None, "Diff report")
            diff_cli = _cli_document(
                "diff", "deploy", "--sandbox", str(mock_home), "--cwd", str(project)
            )
            await pilot.press("J")
            await pilot.pause()
            assert diff.query_one("#diff-json", JsonView).document == diff_cli
            writes.clear()
            await pilot.press("y")
            await pilot.pause()
            assert len(writes) == 1
            assert app.clipboard == diff_cli
            assert _decode_osc52(writes[0]) == diff_cli
            await pilot.press("escape")
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")

            await pilot.press("c")
            await _until(pilot, lambda: isinstance(app.screen, CompareScreen), "Compare")
            compare = app.screen
            await _choose_table_key(
                pilot, compare.query_one("#compare-a-table", DataTable), "claude"
            )
            await _choose_table_key(
                pilot, compare.query_one("#compare-b-table", DataTable), "codex"
            )
            await _until(pilot, lambda: compare.report is not None, "Compare report")
            compare_cli = _cli_document(
                "compare",
                "--agent",
                "claude",
                "--agent",
                "codex",
                "--sandbox",
                str(mock_home),
                "--cwd",
                str(project),
            )
            await pilot.press("J")
            await pilot.pause()
            assert compare.query_one("#compare-json", JsonView).document == compare_cli
            writes.clear()
            await pilot.press("y")
            await pilot.pause()
            assert len(writes) == 1
            assert app.clipboard == compare_cli
            assert _decode_osc52(writes[0]) == compare_cli
            await pilot.press("escape")
            await pilot.press("escape")
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")

            await pilot.press("h")
            await _until(pilot, lambda: isinstance(app.screen, DoctorScreen), "Doctor")
            doctor = app.screen
            doctor_cli = _cli_document("doctor", "--sandbox", str(mock_home), "--cwd", str(project))
            await pilot.press("J")
            await pilot.pause()
            assert doctor.query_one("#doctor-json", JsonView).document == doctor_cli
            writes.clear()
            await pilot.press("y")
            await pilot.pause()
            assert len(writes) == 1
            assert app.clipboard == doctor_cli
            assert _decode_osc52(writes[0]) == doctor_cli
            await pilot.press("escape")
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")

            await pilot.press("g")
            await _until(pilot, lambda: isinstance(app.screen, AgentsScreen), "Agents")
            agents = app.screen
            agents_cli = _cli_document("agents")
            await pilot.press("J")
            await pilot.pause()
            agents_document = agents.query_one("#agents-json", JsonView).document
            assert agents_document is not None
            assert agents_document == agents_cli
            writes.clear()
            await pilot.press("y")
            await pilot.pause()
            assert len(writes) == 1
            assert app.clipboard == agents_cli
            assert _decode_osc52(writes[0]) == agents_cli
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Notice clearing through every suspend route
# ---------------------------------------------------------------------------


def test_why_notice_clears_for_help_and_for_diff(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            why = app.screen
            await _until(pilot, lambda: why._report is not None, "Why report")

            await pilot.press("y")
            await pilot.pause()
            assert _notice(why) == "Copied resolution explanation"
            await pilot.press("f1")
            await _until(pilot, lambda: isinstance(app.screen, HelpScreen), "Help")
            assert _notice(why) == ""
            await pilot.press("f1")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            assert _notice(why) == ""

            await pilot.press("y")
            await pilot.pause()
            await pilot.press("d")
            await _until(pilot, lambda: isinstance(app.screen, DiffScreen), "Diff")
            assert _notice(why) == ""
            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            assert _notice(why) == ""
            await pilot.press("q")

    asyncio.run(_run())


def test_detail_screens_clear_their_notice_when_help_covers_them(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            for opened_with, expected_type in (
                ("d", DiffScreen),
                ("h", DoctorScreen),
                ("g", AgentsScreen),
                ("c", CompareScreen),
            ):
                await pilot.press(opened_with)
                await _until(
                    pilot,
                    lambda expected_type=expected_type: isinstance(app.screen, expected_type),
                    expected_type.__name__,
                )
                screen = app.screen
                if isinstance(screen, DiffScreen):
                    await _until(
                        pilot,
                        lambda screen=screen: screen.report is not None,
                        "Diff report",
                    )
                await pilot.press("y")
                await pilot.pause()
                assert _notice(screen) != ""
                assert _notice_shown(screen)

                await pilot.press("f1")
                await _until(pilot, lambda: isinstance(app.screen, HelpScreen), "Help")
                assert _notice(screen) == ""
                assert not _notice_shown(screen)
                await pilot.press("f1")
                await _until(pilot, lambda screen=screen: app.screen is screen, "origin")
                assert _notice(screen) == ""
                assert not _notice_shown(screen)

                if isinstance(screen, CompareScreen):
                    # Compare result Back returns to the picker; the second Back
                    # closes the screen.
                    await pilot.press("escape")
                    await pilot.pause()
                await pilot.press("escape")
                await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")

            await pilot.press("q")

    asyncio.run(_run())


def test_unmount_is_the_backstop_for_a_popped_detail(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _until(pilot, lambda: isinstance(app.screen, WhyScreen), "Why")
            why = app.screen
            await _until(pilot, lambda: why._report is not None, "Why report")
            await pilot.press("y")
            await pilot.pause()
            assert why._copy_notice_timer is not None

            await pilot.press("escape")
            await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")
            assert why._copy_notice_timer is None
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Key bar
# ---------------------------------------------------------------------------


def test_every_detail_key_bar_shows_y(mock_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(140, 42)) as pilot:
            await _wait_ready(pilot, app)
            seen: list[str] = []
            for opened_with, expected_type in (
                ("enter", WhyScreen),
                ("d", DiffScreen),
                ("h", DoctorScreen),
                ("g", AgentsScreen),
                ("c", CompareScreen),
            ):
                if not isinstance(app.screen, HomeScreen):
                    await _until(pilot, lambda: isinstance(app.screen, HomeScreen), "Home")
                await pilot.press(opened_with)
                await _until(
                    pilot,
                    lambda expected_type=expected_type: isinstance(app.screen, expected_type),
                    expected_type.__name__,
                )
                screen = app.screen
                bar = screen.query_one(".key-bar", Static)
                keys = _bar_keys(bar.content)
                assert "y" in keys, f"{expected_type.__name__} key bar lacks y: {keys}"
                seen.append(expected_type.__name__)
                await pilot.press("escape")
                await pilot.pause()
                if isinstance(screen, CompareScreen):
                    await pilot.press("escape")
                    await pilot.pause()
                if isinstance(screen, WhyScreen):
                    await pilot.press("escape")
                    await pilot.pause()
            assert seen == [
                "WhyScreen",
                "DiffScreen",
                "DoctorScreen",
                "AgentsScreen",
                "CompareScreen",
            ]
            await pilot.press("q")

    asyncio.run(_run())
