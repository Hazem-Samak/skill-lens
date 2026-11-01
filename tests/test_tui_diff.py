"""Headless U5 Diff screen tests: navigation, fidelity, ownership, refresh.

Specification reference: ``FULL_SCREEN_TUI.md`` §8.2, §8.5, §9.1, Step 5,
§21.5–21.7 and §22 U5.

Every test uses the synthetic ``mock_home`` fixture (temporary HOME plus the
protected-system-root isolation installed by ``tests/conftest.py``); a live
``~/.claude`` is never read or written. Keys are driven through real Textual
Pilot events, and controlled races use threading events with bounded waits so a
hang fails the test instead of stalling the run.
"""

from __future__ import annotations

import asyncio
import builtins
import os
import shutil
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from textual.containers import Vertical, VerticalScroll
from textual.widgets import DataTable, Footer, Static

from skill_lens.core.diff import build_diff_report
from skill_lens.core.exitcodes import ExitCode
from skill_lens.core.scanner import build_scan_report
from skill_lens.core.snapshot import (
    SnapshotChanged,
    capture_session,
    snapshot_compare,
    snapshot_diff,
    snapshot_path,
    snapshot_why,
)
from skill_lens.core.system import live_discovery
from skill_lens.models import dumps
from skill_lens.models.diff import DiffChange, DiffCopy, DiffFile, DiffHunk, DiffReport
from skill_lens.models.enums import Scope
from skill_lens.presentation import copy_heading, unified_text
from skill_lens.registry.loader import load_registry
from skill_lens.tui.app import SkillLensApp, ViewReportComplete, ViewReportFailed
from skill_lens.tui.diff import DiffScreen
from skill_lens.tui.home import HomeScreen
from skill_lens.tui.json_view import JsonView
from skill_lens.tui.why import WhyScreen
from tests.fixtures.builders import make_skill, write_skill
from tests.fixtures.scenarios import build_scenario

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _wait_until(pilot: Any, predicate: Any, label: str, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        await pilot.pause(0.01)
    raise AssertionError(f"timed out waiting for {label}")


async def _wait_ready(pilot: Any, app: SkillLensApp) -> None:
    await _wait_until(
        pilot,
        lambda: (
            app.controller.current is not None
            and app.controller.status == "ready"
            and isinstance(app.screen, HomeScreen)
            and (
                len(app.controller.current.scan.skills) == 0
                or app.screen.query_one("#skill-table", DataTable).row_count > 0
            )
        ),
        "initial capture and home table ready",
    )
    await pilot.pause(0.02)


async def _wait_diff_report(pilot: Any, app: SkillLensApp) -> DiffScreen:
    await _wait_until(
        pilot,
        lambda: isinstance(app.screen, DiffScreen) and app.screen.report is not None,
        "diff report accepted",
    )
    await pilot.pause(0.02)
    screen = app.screen
    assert isinstance(screen, DiffScreen)
    return screen


def _row_keys(app: SkillLensApp) -> list[str]:
    table = app.query_one("#skill-table", DataTable)
    return [str(table.coordinate_to_cell_key((i, 0)).row_key.value) for i in range(table.row_count)]


async def _select_row_containing(pilot: Any, app: SkillLensApp, needle: str) -> str:
    """Select Home's first row whose canonical key contains ``needle``."""
    key = next(key for key in _row_keys(app) if needle in key)
    await _select_key(pilot, app, key)
    return key


async def _select_key(pilot: Any, app: SkillLensApp, key: str) -> None:
    """Move Home's cursor to the row whose canonical key is ``key``."""
    table = app.query_one("#skill-table", DataTable)
    index = _row_keys(app).index(key)
    for _ in range(table.row_count):
        if table.cursor_row == index:
            break
        await pilot.press("down" if table.cursor_row < index else "up")
    await pilot.pause(0.02)
    assert table.cursor_row == index
    assert app.controller.selected_key == key


def _body_text(app: SkillLensApp) -> str:
    """Every mounted report block, in the order the screen shows them."""
    content = app.screen.query_one("#diff-content", Vertical)
    return "\n".join(str(widget.content) for widget in content.query(Static))


def _rendered_text(app: SkillLensApp) -> str:
    """The actual compositor output as plain text (what a terminal shows)."""
    strips = app.screen._compositor.render_strips()
    return "\n".join(strip.text for strip in strips)


def _build_three_change_copy_fixture(home: Path) -> Path:
    """Two copies of ``asset`` differing by one modified, added and removed file."""
    project = home / "project"
    (project / ".git").mkdir(parents=True, exist_ok=True)
    global_dir = home / ".claude" / "skills" / "asset"
    project_dir = project / ".claude" / "skills" / "asset"
    make_skill(global_dir, "asset", "Global asset.", body="# Instructions\n\nGlobal body.\n")
    make_skill(project_dir, "asset", "Project asset.", body="# Instructions\n\nProject body.\n")
    (global_dir / "added.txt").write_text("only in the global copy\n", encoding="utf-8")
    (project_dir / "removed.txt").write_text("only in the project copy\n", encoding="utf-8")
    for directory, payload in (
        (global_dir, b"\xff\xfeGLOBAL-BINARY-PAYLOAD\x00\x01"),
        (project_dir, b"\xff\xfePROJECT-BINARY-PAYLOAD\x00\x02"),
    ):
        (directory / "assets").mkdir(exist_ok=True)
        (directory / "assets" / "blob.bin").write_bytes(payload)
    return project


def _build_frontmatter_name_fixture(home: Path) -> tuple[Path, str]:
    """A codex skill whose folder name differs from its declared name.

    Returns ``(project_dir, translated_lookup_name)``. The two copies live in
    ``.codex/skills`` (user) and ``project/.agents/skills`` (project); the tests
    find the user-scope row by its path suffix instead of guessing its key.
    """
    project = home / "project"
    (project / ".git").mkdir(parents=True, exist_ok=True)
    global_dir = home / ".codex" / "skills" / "folder-key"
    project_dir = project / ".agents" / "skills" / "folder-key"
    write_skill(
        global_dir,
        "---\nname: declared-key\ndescription: Global copy.\n---\n# Instructions\n\nGlobal.\n",
    )
    write_skill(
        project_dir,
        "---\nname: declared-key\ndescription: Project copy.\n---\n# Instructions\n\nProject.\n",
    )
    return project, "declared-key"


# ---------------------------------------------------------------------------
# Home → Diff → back
# ---------------------------------------------------------------------------


def test_home_d_opens_diff_for_the_selected_canonical_installation(mock_home: Path) -> None:
    """``d`` opens Diff for the selected row and returns without losing place."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            # A filter that still matches both copies, then back to the table.
            await pilot.press("slash")
            await pilot.press("d", "e", "p")
            assert app.query_one("#filter-input").value == "dep"
            await pilot.press("enter")
            table = app.query_one("#skill-table", DataTable)
            assert table.has_focus

            await pilot.press("up")
            cursor_before = table.cursor_row
            selected = app.controller.selected_key
            assert selected is not None
            assert selected == _row_keys(app)[cursor_before]

            await pilot.press("d")
            await pilot.pause()
            diff = app.screen
            assert isinstance(diff, DiffScreen)
            assert diff.opening_key == selected
            report = (await _wait_diff_report(pilot, app)).report
            assert report is not None and report.found
            assert report.skill_name == "deploy"

            await pilot.press("escape")
            await pilot.pause()
            home = app.screen
            assert isinstance(home, HomeScreen)
            assert app.controller.selected_key == selected
            assert home.query_one("#filter-input").value == "dep"
            assert home.query_one("#skill-table", DataTable).cursor_row == cursor_before
            assert home.query_one("#skill-table", DataTable).has_focus

            # Backspace is the same return path, not a second stacked screen.
            await pilot.press("d")
            await pilot.pause()
            assert isinstance(app.screen, DiffScreen)
            await pilot.press("backspace")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            assert not any(isinstance(s, DiffScreen) for s in app.screen_stack)

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_home_filter_typing_is_ordinary_text_and_never_opens_diff(mock_home: Path) -> None:
    """``d`` and ``J`` typed into the filter stay text; no Diff is pushed."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            await pilot.press("slash")
            await pilot.press("d", "J")
            assert app.query_one("#filter-input").value == "dJ"
            assert isinstance(app.screen, HomeScreen)
            assert app.controller.active_requests.get("diff") is None

            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            await pilot.press("q")

    asyncio.run(_run())


def test_home_d_is_inert_when_the_table_is_empty(mock_home: Path) -> None:
    """No Diff is dispatched from an empty catalog."""

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            assert app.query_one("#skill-table", DataTable).row_count == 0
            await pilot.press("d")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            assert app.controller.active_requests.get("diff") is None
            await pilot.press("q")

    asyncio.run(_run())


def test_home_d_is_inert_when_the_table_is_not_focused(mock_home: Path) -> None:
    """``d`` needs the focused skill table, exactly like Enter needs it."""
    make_skill(mock_home / ".claude" / "skills" / "alpha", "alpha", "Alpha skill.")

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            table = app.query_one("#skill-table", DataTable)
            assert table.has_focus
            for _ in range(3):
                await pilot.press("tab")
                if not table.has_focus:
                    break
            assert not table.has_focus
            await pilot.press("d")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            assert app.controller.active_requests.get("diff") is None
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Why → Diff → Why
# ---------------------------------------------------------------------------


def test_why_d_uses_folder_name_for_diff_and_translated_name_for_why(mock_home: Path) -> None:
    """Diff groups on the folder name; Why resolves the declared name."""
    project, lookup_name = _build_frontmatter_name_fixture(mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            user_key = await _select_row_containing(pilot, app, "/.codex/skills/folder-key")

            await pilot.press("enter")
            await _wait_until(
                pilot,
                lambda: isinstance(app.screen, WhyScreen) and app.screen._report is not None,
                "why report",
            )
            why = app.screen
            assert isinstance(why, WhyScreen)
            assert why._agent_id == "codex"
            assert why._report is not None
            assert why._report.skill_name == lookup_name
            collapsed_before = [item.collapsed for item in why.query("Collapsible")]

            await pilot.press("d")
            diff = await _wait_diff_report(pilot, app)
            assert diff.opening_key == user_key
            assert diff.report is not None
            # The folder name, never the translated lookup name.
            assert diff.report.skill_name == "folder-key"

            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is why
            assert why._agent_id == "codex"
            assert why._report is not None and why._report.skill_name == lookup_name
            assert [item.collapsed for item in why.query("Collapsible")] == collapsed_before
            assert app.controller.failed is False
            await pilot.press("q")

    asyncio.run(_run())


def test_why_without_any_agent_still_opens_diff(mock_home: Path) -> None:
    """A skill no agent reaches has no Why report but still has a Diff."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            current = app.controller.current
            assert current is not None
            zero_agents = tuple(replace(row, agents=()) for row in current.scan.skills)
            app.controller.current = replace(
                current, scan=replace(current.scan, skills=zero_agents)
            )
            key = app.controller.selected_key
            assert key is not None

            await pilot.press("enter")
            await pilot.pause(0.05)
            why = app.screen
            assert isinstance(why, WhyScreen)
            assert why._agent_options == ()
            assert app.controller.active_requests.get("why") is None

            await pilot.press("d")
            diff = await _wait_diff_report(pilot, app)
            assert diff.report is not None and diff.report.found
            assert diff.report.skill_name == "deploy"

            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is why
            await pilot.press("q")

    asyncio.run(_run())


def test_pending_why_report_is_requested_again_after_diff(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Covering a pending Why and returning produces a current report, not a spinner."""
    build_scenario("claude_personal_beats_project", mock_home)

    started = threading.Event()
    gate = threading.Event()
    real_why = snapshot_why

    def controlled_why(snapshot: Any, key: str, agent: str) -> Any:
        started.set()
        gate.wait(timeout=5.0)
        return real_why(snapshot, key, agent)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", controlled_why)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_until(pilot, started.is_set, "why worker started")
            why = app.screen
            assert isinstance(why, WhyScreen)
            assert app.controller.active_requests.get("why") is not None

            # Open Diff while Why is genuinely pending.
            await pilot.press("d")
            await _wait_diff_report(pilot, app)
            assert isinstance(app.screen, DiffScreen)

            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is why
            gate.set()

            await _wait_until(pilot, lambda: why._report is not None, "why report after resume")
            assert why._owned_request is None
            assert app.controller.active_requests.get("why") is None
            report_status = str(why.query_one("#why-report-status", Static).content)
            assert "Loading report" not in report_status
            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_covered_why_is_suspended_and_its_stale_result_rejected(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C2: covering Why must stop its report activity, not merely defer it.

    Why's request A is genuinely pending when Diff covers it. While Diff is active
    Why must be suspended, A's cancellation event set and no hidden replacement
    work started. Releasing A behind the covering screen must be a rejected
    outcome, never a cached or displayed report; returning must obtain a current
    report through the normal cache/owned-token/dedup path.
    """
    build_scenario("claude_personal_beats_project", mock_home)
    started = threading.Event()
    gate = threading.Event()
    calls = {"count": 0}
    processed: list[tuple[str, int, bool]] = []
    real_why = snapshot_why

    def controlled_why(snapshot: Any, key: str, agent: str) -> Any:
        calls["count"] += 1
        if calls["count"] == 1:
            started.set()
            gate.wait(timeout=5.0)
        return real_why(snapshot, key, agent)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", controlled_why)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        original_accept = app.controller.accept_view_result

        def recording_accept(
            view: Any,
            request_id: int,
            generation: int,
            arguments: tuple[str, ...],
            result: Any,
        ) -> bool:
            accepted = original_accept(view, request_id, generation, arguments, result)
            processed.append((view, request_id, accepted))
            return accepted

        app.controller.accept_view_result = recording_accept  # type: ignore[method-assign]

        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_until(pilot, started.is_set, "why request A started")
            why = app.screen
            assert isinstance(why, WhyScreen)
            token_a = why._owned_request
            assert token_a is not None
            event_a = app.controller._report_events[token_a.request_id]
            assert not event_a.is_set()
            assert app.controller.active_requests.get("why") == token_a
            assert why._suspended is False

            # Diff covers the pending detail.
            await pilot.press("d")
            await _wait_diff_report(pilot, app)

            # Covered state, asserted while Diff is the active screen.
            assert why._suspended is True, "covered Why must be suspended"
            assert why._owned_request is None, "covered Why must drop its owned token"
            assert event_a.is_set(), "covering Why must cancel its owned request"
            assert app.controller.active_requests.get("why") is None
            assert calls["count"] == 1, "no replacement Why work may start while covered"

            # The obsolete result is released while still covered. Waiting on the
            # recorded acceptance proves the outcome reached the controller.
            gate.set()
            await _wait_until(
                pilot,
                lambda: any(
                    view == "why" and rid == token_a.request_id for view, rid, _ in processed
                ),
                "obsolete Why outcome processed by the controller",
            )
            stale = [
                ok for view, rid, ok in processed if view == "why" and rid == token_a.request_id
            ]
            assert stale == [False], "the obsolete Why result must be rejected"
            assert calls["count"] == 1, "a rejected stale result must not start new work"
            assert not any(key[1] == "why" for key in app.controller.cache), (
                "a rejected stale result must never be cached"
            )
            assert why._report is None

            # Returning reconciles through the normal deduplicated request path.
            await pilot.press("escape")
            await _wait_until(pilot, lambda: why._report is not None, "why report after resume")
            assert app.screen is why
            assert calls["count"] == 2, "resume must re-request exactly once"
            assert why._owned_request is None
            assert app.controller.active_requests.get("why") is None
            assert app.controller.get_cached_report("why", (why._opening_key, why._agent_id)) is (
                why._report
            )
            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_refresh_published_while_why_is_covered_rebinds_on_return(mock_home: Path) -> None:
    """A capture published under Diff is reconciled by the revealed Why."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            first_generation = app.controller.current.generation
            await pilot.press("enter")
            await _wait_until(
                pilot,
                lambda: isinstance(app.screen, WhyScreen) and app.screen._report is not None,
                "why report",
            )
            why = app.screen
            assert isinstance(why, WhyScreen)

            await pilot.press("d")
            await _wait_diff_report(pilot, app)

            # Change the content on disk, then refresh while Diff is topmost.
            write_skill(
                mock_home / ".claude" / "skills" / "deploy",
                "---\nname: deploy\ndescription: Personal deploy helper.\n---\n"
                "# Instructions\n\nRefreshed personal body.\n",
            )
            await pilot.press("r")
            await _wait_until(
                pilot,
                lambda: (
                    app.controller.current is not None
                    and app.controller.current.generation != first_generation
                    and app.controller.status == "ready"
                    and isinstance(app.screen, DiffScreen)
                    and app.screen.report is not None
                ),
                "diff rebound to the new generation",
            )

            await pilot.press("escape")
            await _wait_until(
                pilot,
                lambda: isinstance(app.screen, WhyScreen) and app.screen._report is not None,
                "why report for the new generation",
            )
            assert app.screen is why
            assert why._generation == app.controller.current.generation
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Report fidelity
# ---------------------------------------------------------------------------


def test_diff_shows_summary_headings_hunks_and_every_file_change(mock_home: Path) -> None:
    """Baseline, copy order, headings and per-file labels all follow the model."""
    project = _build_three_change_copy_fixture(mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            snapshot = app.controller.current
            assert snapshot is not None
            await pilot.press("d")
            diff = await _wait_diff_report(pilot, app)
            report = diff.report
            assert report is not None and report.found
            text = _body_text(app)

            assert f"Diff: '{report.skill_name}'" in _rendered_text(app)
            assert f"Copies: {len(report.copies)}" in text
            baseline = next(copy for copy in report.copies if copy.is_baseline)
            assert report.baseline_path is not None
            baseline_display = snapshot_path(snapshot, baseline.path)
            assert f"Baseline: {baseline_display}" in text
            assert f"(Variant {baseline.variant_label})" in text

            # Copy blocks appear in report order with their heading status.
            positions = [text.index(snapshot_path(snapshot, copy.path)) for copy in report.copies]
            assert positions == sorted(positions)
            for copy in report.copies:
                parts = copy_heading(
                    copy,
                    baseline_exists=True,
                    display_path=snapshot_path(snapshot, copy.path),
                )
                assert parts.status in text
                assert f"({parts.scope}, {parts.parse_status})" in text

            # Every differing file is labelled, all three changes are present,
            # and every retained hunk body matches the model exactly.
            labels = set()
            for copy in report.copies:
                for file in copy.files:
                    labels.add(file.change.value)
                    assert f"{file.path} {file.change.value}" in text
                    if file.is_binary:
                        assert f"{file.path} {file.change.value} binary" in text
                    else:
                        assert unified_text(file) in text
            assert {"added", "removed", "modified"} <= labels

            # Binary payloads never reach the screen, and no binary file gets a
            # printed hunk body -- only its path, change and marker are shown.
            assert "GLOBAL-BINARY-PAYLOAD" not in text
            assert "PROJECT-BINARY-PAYLOAD" not in text
            for copy in report.copies:
                for file in copy.files:
                    if file.is_binary:
                        assert f"+++ {file.path}" not in text

            await pilot.press("q")

    asyncio.run(_run())


def test_supplied_report_never_prints_binary_payload_or_hunkless_noise(
    mock_home: Path,
) -> None:
    """Even a malformed supplied report suppresses binary payloads and empty hunks."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            snapshot = app.controller.current
            assert snapshot is not None
            key = app.controller.selected_key
            assert key is not None

            baseline = DiffCopy(
                path=str(mock_home / "baseline"),
                scope=Scope.USER,
                parse_status="valid",
                is_valid=True,
                is_readable=True,
                is_baseline=True,
                variant_label="A",
            )
            other = DiffCopy(
                path=str(mock_home / "other"),
                scope=Scope.PROJECT,
                parse_status="valid",
                is_valid=True,
                is_readable=True,
                variant_label="B",
                files=(
                    DiffFile(
                        path="payload.bin",
                        change=DiffChange.MODIFIED,
                        is_binary=True,
                        hunks=(DiffHunk(0, 1, 0, 1, ("+SECRET-BINARY-PAYLOAD",)),),
                    ),
                    DiffFile(path="quiet.txt", change=DiffChange.ADDED, hunks=()),
                ),
            )
            supplied = DiffReport(
                skill_name="supplied",
                home=str(snapshot.home),
                cwd=str(snapshot.cwd),
                found=True,
                baseline_path=baseline.path,
                copies=(baseline, other),
            )
            app.controller.cache[(snapshot.generation, "diff", (key,))] = supplied

            await pilot.press("d")
            diff = await _wait_diff_report(pilot, app)
            assert diff.report is supplied
            text = _body_text(app)
            assert "SECRET-BINARY-PAYLOAD" not in text
            assert "payload.bin modified binary" in text
            assert "+++ payload.bin" not in text, "binary hunk bodies are never printed"
            assert "quiet.txt added" in text
            assert "+++ quiet.txt" not in text, "a hunkless file prints no body"
            await pilot.press("q")

    asyncio.run(_run())


def test_diff_distinguishes_identical_copies_from_a_missing_baseline(mock_home: Path) -> None:
    """Identical copies and no-baseline copies are different visible answers."""
    project = mock_home / "project"
    (project / ".git").mkdir(parents=True, exist_ok=True)
    same_body = "---\nname: same\ndescription: Identical copy.\n---\n# Instructions\n\nSame.\n"
    write_skill(mock_home / ".claude" / "skills" / "same", same_body)
    write_skill(project / ".claude" / "skills" / "same", same_body)
    broken = "---\nname: broken\n---\n# No description, so no baseline.\n"
    write_skill(mock_home / ".claude" / "skills" / "broken", broken)
    write_skill(project / ".claude" / "skills" / "broken", broken)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            snapshot = app.controller.current
            assert snapshot is not None

            same_key = next(key for key in _row_keys(app) if key.endswith("/same"))
            await _select_key(pilot, app, same_key)
            await pilot.press("d")
            diff = await _wait_diff_report(pilot, app)
            report = diff.report
            assert report is not None and not report.has_differences
            assert report.baseline_path is not None
            identical_text = _body_text(app)
            assert "identical" in identical_text.lower()
            assert "not compared" not in identical_text.lower()
            await pilot.press("escape")
            await pilot.pause()

            broken_key = next(key for key in _row_keys(app) if key.endswith("/broken"))
            await _select_key(pilot, app, broken_key)
            await pilot.press("d")
            diff = await _wait_diff_report(pilot, app)
            report = diff.report
            assert report is not None
            assert report.baseline_path is None
            text = _body_text(app)
            assert "Not compared:" in text
            assert "Baseline: none (no copy passed validation)" in text
            assert "identical" not in text.lower()
            # The same copies shown as a match would be a different claim.
            assert text != identical_text
            # Every copy is still listed with its path, even though none was compared.
            for copy in report.copies:
                assert copy.path in text or snapshot_path(snapshot, copy.path) in text
            await pilot.press("q")

    asyncio.run(_run())


def test_diff_lists_an_unreadable_copy_with_its_reason(mock_home: Path) -> None:
    """A copy that cannot be read is listed with its reason and no content."""
    project = mock_home / "project"
    (project / ".git").mkdir(parents=True, exist_ok=True)
    dangling = mock_home / ".claude" / "skills" / "ghosted"
    dangling.parent.mkdir(parents=True, exist_ok=True)
    dangling.symlink_to(mock_home / "missing-target", target_is_directory=True)
    make_skill(project / ".claude" / "skills" / "ghosted", "ghosted", "Project copy.")

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await _select_key(pilot, app, next(key for key in _row_keys(app) if "ghosted" in key))
            await pilot.press("d")
            diff = await _wait_diff_report(pilot, app)
            report = diff.report
            assert report is not None
            unreadable = [copy for copy in report.copies if not copy.is_readable]
            assert unreadable, "fixture must produce an unreadable copy"
            text = _body_text(app)
            assert "cannot be read" in text
            assert "No content to compare" in text
            await pilot.press("q")

    asyncio.run(_run())


def test_diff_shows_a_supplied_not_found_report_with_the_existing_explanation(
    mock_home: Path,
) -> None:
    """A not-found report is displayed, not turned into a live read or a crash."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            snapshot = app.controller.current
            assert snapshot is not None
            key = app.controller.selected_key
            assert key is not None
            ghost = DiffReport(
                skill_name="ghost",
                home=str(snapshot.home),
                cwd=str(snapshot.cwd),
                found=False,
                notes=("No copy of this skill name was found in any search root.",),
            )
            app.controller.cache[(snapshot.generation, "diff", (key,))] = ghost

            await pilot.press("d")
            diff = await _wait_diff_report(pilot, app)
            assert diff.report is ghost
            assert "No copies of 'ghost' were found in any search root." in _body_text(app)
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Truncation and literal text
# ---------------------------------------------------------------------------


def test_line_budget_truncation_shows_the_omitted_line_total(mock_home: Path) -> None:
    """A copy exceeding the changed-line budget reports how many lines it dropped."""
    project = mock_home / "project"
    (project / ".git").mkdir(parents=True, exist_ok=True)
    global_dir = mock_home / ".claude" / "skills" / "long-lines"
    project_dir = project / ".claude" / "skills" / "long-lines"
    make_skill(
        global_dir,
        "long-lines",
        "Global.",
        body="".join(f"line {i}\n" for i in range(450)),
    )
    make_skill(
        project_dir,
        "long-lines",
        "Project.",
        body="".join(f"modified {i}\n" for i in range(450)),
    )

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("d")
            diff = await _wait_diff_report(pilot, app)
            report = diff.report
            assert report is not None
            truncated = [copy for copy in report.copies if copy.omitted_lines]
            assert truncated, "fixture must exceed the changed-line budget"
            text = _body_text(app)
            for copy in truncated:
                assert f"Truncated: {copy.omitted_lines} changed lines omitted." in text
                assert copy.truncated is True
            # The last retained hunk is the model's last hunk, not a fabricated one.
            for copy in report.copies:
                if copy.files:
                    assert unified_text(copy.files[-1]) in text
            await pilot.press("q")

    asyncio.run(_run())


def test_character_budget_truncation_never_claims_zero_omitted_lines(mock_home: Path) -> None:
    """A character-only cut points at the report total instead of a line count.

    The emitted body is over the 20,000-character report budget while the changed
    lines stay well under the 400-line budget. The cut lands on the long trailing
    context lines, so every changed line survived (``omitted_lines == 0``) and
    only characters were dropped -- the D-04 case.
    """
    project = mock_home / "project"
    (project / ".git").mkdir(parents=True, exist_ok=True)
    global_dir = mock_home / ".claude" / "skills" / "wide"
    project_dir = project / ".claude" / "skills" / "wide"
    make_skill(global_dir, "wide", "Same description.", body="# Body\n")
    make_skill(project_dir, "wide", "Same description.", body="# Body\n")

    lead = ["lead " + "c" * 16 for _ in range(3)]
    old_block = [f"old {index:02d} " + "x" * 400 for index in range(24)]
    new_block = [f"new {index:02d} " + "y" * 400 for index in range(24)]
    tail = ["tail " + "t" * 995 for _ in range(3)]
    (global_dir / "body.txt").write_text(
        "\n".join([*lead, *old_block, *tail]) + "\n", encoding="utf-8"
    )
    (project_dir / "body.txt").write_text(
        "\n".join([*lead, *new_block, *tail]) + "\n", encoding="utf-8"
    )

    # The fixture must really exceed the character budget with a cut that keeps
    # every changed line: prefix cost <= 20,000, and the next tail line overflows.
    prefix_cost = sum(len(f" {line}") + 1 for line in lead)
    prefix_cost += sum(len(f"-{line}") + 1 for line in old_block)
    prefix_cost += sum(len(f"+{line}") + 1 for line in new_block)
    tail_cost = sum(len(f" {line}") + 1 for line in tail)
    assert prefix_cost <= 20_000, "changed lines must all fit inside the budget"
    assert prefix_cost + len(f" {tail[0]}") + 1 > 20_000, "cut must land on trailing context"
    assert 48 < 400, "changed lines stay far below the per-copy line budget"
    assert prefix_cost + tail_cost > 20_000

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("d")
            diff = await _wait_diff_report(pilot, app)
            report = diff.report
            assert report is not None
            assert report.truncated is True
            assert report.omitted_chars > 0
            char_only = [copy for copy in report.copies if copy.truncated and copy.omitted_lines]
            assert not char_only, "the line budget must not be the reason for the cut"
            character_cut = [copy for copy in report.copies if copy.truncated]
            assert character_cut, "fixture must hit the character budget"
            text = _body_text(app)
            assert "0 changed lines omitted" not in text
            assert "part of this diff was omitted" in text
            assert f"{report.omitted_chars} characters" in text

            # The omitted total is a positive character count, not a line count.
            assert str(report.omitted_chars) in text
            await pilot.press("q")

    asyncio.run(_run())


def test_literal_text_stays_literal_in_the_diff_body(mock_home: Path) -> None:
    """Brackets, closing tags, backslashes and Unicode are shown, never parsed."""
    project = mock_home / "project"
    (project / ".git").mkdir(parents=True, exist_ok=True)
    global_dir = mock_home / ".claude" / "skills" / "literal"
    project_dir = project / ".claude" / "skills" / "literal"
    make_skill(global_dir, "literal", "Global literal.")
    make_skill(project_dir, "literal", "Project literal.")
    literal_line = "[bold red]not markup[/bold red] C:\\temp\\path ünïcode ✓"
    (global_dir / "body.txt").write_text("plain line\n", encoding="utf-8")
    (project_dir / "body.txt").write_text(literal_line + "\n", encoding="utf-8")

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("d")
            await _wait_diff_report(pilot, app)
            text = _body_text(app)
            assert literal_line in text
            assert "C:\\temp\\path" in text
            assert "ünïcode ✓" in text
            rendered = _rendered_text(app)
            assert "not markup" in rendered
            await pilot.press("q")

    asyncio.run(_run())


def test_diff_content_is_reachable_at_both_terminal_sizes(mock_home: Path) -> None:
    """Long reports stay reachable by keyboard scrolling at 100x30 and 60x24."""
    project = mock_home / "project"
    (project / ".git").mkdir(parents=True, exist_ok=True)
    global_dir = mock_home / ".claude" / "skills" / "tall"
    project_dir = project / ".claude" / "skills" / "tall"
    make_skill(global_dir, "tall", "Global tall.")
    make_skill(project_dir, "tall", "Project tall.")
    # The project copy is the Variant A baseline, so the marker goes in the other
    # copy: it is then emitted as the final "+" line of the retained diff.
    baseline_lines = [f"row {index:02d} " + "a" * 40 for index in range(60)]
    other_lines = [f"row {index:02d} " + "b" * 40 for index in range(59)]
    other_lines.append("TAIL-MARKER-UNIQUE")
    (global_dir / "body.txt").write_text("\n".join(other_lines) + "\n", encoding="utf-8")
    (project_dir / "body.txt").write_text("\n".join(baseline_lines) + "\n", encoding="utf-8")

    async def _run(size: tuple[int, int]) -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=size) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("d")
            diff = await _wait_diff_report(pilot, app)
            report = diff.report
            assert report is not None
            body = app.screen.query_one("#diff-body", VerticalScroll)
            await _wait_until(pilot, lambda: body.has_focus, "diff body focus")
            assert body.max_scroll_y > 0
            for _ in range(20):
                await pilot.press("down")
            await pilot.press("end")
            await pilot.pause(0.1)
            assert body.scroll_offset.y == body.max_scroll_y

            # The marker is the model's last retained line, and it is visible.
            last_file = next(copy for copy in report.copies if copy.files).files[-1]
            assert unified_text(last_file).splitlines()[-1] == "+TAIL-MARKER-UNIQUE"
            assert "TAIL-MARKER-UNIQUE" in _rendered_text(app)

            await pilot.press("pageup")
            await pilot.pause(0.05)
            assert body.scroll_offset.y < body.max_scroll_y
            await pilot.press("home")
            await pilot.pause(0.05)
            assert body.scroll_offset.y == 0
            assert "Copies:" in _rendered_text(app)
            await pilot.press("q")

    asyncio.run(_run((100, 30)))
    asyncio.run(_run((60, 24)))


def _build_long_metadata_fixture(home: Path) -> tuple[Path, str]:
    """Two copies of one valid skill with a very long name and a deep project path.

    Sized so that the wrapped metadata alone is taller than a 60x24 viewport: the
    regression this fixture covers only appears when the title really is enormous.
    """
    name = "skill-" + "n" * 234
    deep = home / "project"
    # Fill the platform path budget with nested components so the captured path
    # is as long as the filesystem allows without ever being unwritable.
    fixed = len(str(deep / ".claude" / "skills" / name))
    budget = 1000 - fixed
    components = 8
    per_component = budget // components - 13
    assert per_component >= 30, "synthetic home path leaves too little room for the fixture"
    for index in range(components):
        deep = deep / (f"component-{index}-" + "d" * per_component)
    (deep / ".git").mkdir(parents=True, exist_ok=True)
    global_dir = home / ".claude" / "skills" / name
    project_dir = deep / ".claude" / "skills" / name
    make_skill(global_dir, name, "Global long-name copy.")
    make_skill(project_dir, name, "Project long-name copy.")
    (global_dir / "body.txt").write_text("LONG-METADATA-OTHER\n", encoding="utf-8")
    (project_dir / "body.txt").write_text("LONG-METADATA-BASELINE\n", encoding="utf-8")
    assert len(str(project_dir)) <= 1010, "fixture path must stay inside the platform limit"
    return deep, name


def test_long_metadata_never_hides_the_report_or_the_footer(mock_home: Path) -> None:
    """A valid 186-character name and deep path must not push the body off screen.

    The whole metadata block lives inside the report's scroll area, so the body
    and footer keep their space and both the metadata and the report stay
    keyboard-reachable. Raw JSON must stay usable under the same metadata.
    """
    project, name = _build_long_metadata_fixture(mock_home)

    async def _run(size: tuple[int, int], *, min_title_rows: int) -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=size) as pilot:
            await _wait_ready(pilot, app)
            # Select the deeply nested project copy: its captured path is the one
            # that makes the Diff metadata enormous.
            deep_key = next(key for key in _row_keys(app) if "/component-" in key)
            await _select_key(pilot, app, deep_key)
            await pilot.press("d")
            diff = await _wait_diff_report(pilot, app)
            report = diff.report
            assert report is not None
            body = app.screen.query_one("#diff-body", VerticalScroll)
            footer = app.screen.query_one(Footer)
            await _wait_until(pilot, lambda: body.has_focus, "diff body focus")

            # The body owns a usable region above the footer; nothing overlaps it.
            assert body.region.height >= 8, f"body squashed to {body.region.height} rows"
            assert body.region.bottom <= footer.region.y
            assert footer.region.height >= 1
            assert footer.region.y + footer.region.height <= app.size.height

            # The report is reachable at the end of the scroll.
            assert body.max_scroll_y > 0
            await pilot.press("end")
            await pilot.pause(0.1)
            assert body.scroll_offset.y == body.max_scroll_y
            last_file = next(copy for copy in report.copies if copy.files).files[-1]
            assert unified_text(last_file).splitlines()[-1] in _rendered_text(app)

            # The long metadata itself is reachable by scrolling back up.
            await pilot.press("home")
            await pilot.pause(0.1)
            assert body.scroll_offset.y == 0
            title = diff.query_one("#diff-title", Static)
            title_text = str(title.content)
            assert name in title_text
            # The defect needs a title taller than the viewport on its own.
            assert title.virtual_size.height >= min_title_rows, (
                f"fixture metadata only wraps to {title.virtual_size.height} rows"
            )
            assert body.virtual_size.height > body.region.height, "metadata must scroll, not clip"
            assert title_text.splitlines()[-1][-20:] in _rendered_text(app)

            # Raw JSON stays usable under the same long metadata.
            await pilot.press("J")
            await pilot.pause()
            view = app.screen.query_one("#diff-json", JsonView)
            await _wait_until(pilot, lambda: view.has_focus, "json view focus")
            assert view.display
            assert view.region.height >= 5
            assert view.region.bottom <= footer.region.y
            assert view.document is not None
            assert name in view.document
            await pilot.press("q")

    # At 60x24 the wrapped metadata alone is taller than the viewport, which is
    # the case that used to push the report under the footer.
    asyncio.run(_run((100, 30), min_title_rows=6))
    asyncio.run(_run((60, 24), min_title_rows=14))


# ---------------------------------------------------------------------------
# Ownership, caching and generations
# ---------------------------------------------------------------------------


def test_reopening_a_cached_diff_never_dispatches_again(mock_home: Path) -> None:
    """A cached report reopens without a second worker request."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("d")
            diff = await _wait_diff_report(pilot, app)
            first = diff.report
            assert first is not None
            await pilot.press("escape")
            await pilot.pause()

            await pilot.press("d")
            second = await _wait_diff_report(pilot, app)
            assert second.report is first
            assert app.controller.active_requests.get("diff") is None
            assert app.controller.current is not None
            cache_key = (app.controller.current.generation, "diff", (second.opening_key,))
            assert app.controller.cache.get(cache_key) is first
            await pilot.press("q")

    asyncio.run(_run())


def test_stale_diff_result_and_error_are_rejected(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Foreign tokens cannot publish a report or poison the sticky fault state."""
    build_scenario("claude_personal_beats_project", mock_home)
    started = threading.Event()
    gate = threading.Event()
    real_diff = snapshot_diff

    def controlled_diff(snapshot: Any, key: str) -> Any:
        started.set()
        gate.wait(timeout=5.0)
        return real_diff(snapshot, key)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            key = app.controller.selected_key
            assert key is not None
            await pilot.press("d")
            await _wait_until(pilot, started.is_set, "diff worker started")
            diff = app.screen
            assert isinstance(diff, DiffScreen)
            current = app.controller.current
            assert current is not None
            generation = current.generation
            owned = diff._owned_request
            assert owned is not None

            foreign = DiffReport(
                skill_name="foreign",
                home=str(current.home),
                cwd=str(current.cwd),
                found=True,
            )
            app.on_view_report_complete(
                ViewReportComplete("diff", owned.request_id + 500, generation, (key,), foreign)
            )
            app.on_view_report_failed(
                ViewReportFailed(
                    "diff",
                    owned.request_id + 501,
                    generation,
                    (key,),
                    RuntimeError("stale diff failure"),
                )
            )
            await pilot.pause()
            assert diff.report is None
            assert "Loading report" in _body_text(app)
            assert app.controller.failed is False

            gate.set()
            report = (await _wait_diff_report(pilot, app)).report
            assert report is not None and report.skill_name == "deploy"
            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_diff", controlled_diff)
    asyncio.run(_run())


def test_leaving_diff_cancels_only_its_own_token(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An abandoned Diff cannot cancel or overwrite the newer owner's work."""
    build_scenario("claude_personal_beats_project", mock_home)
    started = threading.Event()
    gate = threading.Event()
    calls = {"count": 0}
    real_diff = snapshot_diff

    def controlled_diff(snapshot: Any, key: str) -> Any:
        calls["count"] += 1
        if calls["count"] == 1:
            started.set()
            gate.wait(timeout=5.0)
        return real_diff(snapshot, key)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        processed: list[tuple[str, int, bool]] = []
        original_accept = app.controller.accept_view_result

        def recording_accept(
            view: Any,
            request_id: int,
            generation: int,
            arguments: tuple[str, ...],
            result: Any,
        ) -> bool:
            accepted = original_accept(view, request_id, generation, arguments, result)
            processed.append((view, request_id, accepted))
            return accepted

        app.controller.accept_view_result = recording_accept  # type: ignore[method-assign]
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("d")
            await _wait_until(pilot, started.is_set, "first diff worker started")
            first = app.screen
            assert isinstance(first, DiffScreen)
            token_a = first._owned_request
            assert token_a is not None

            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            assert app.controller.active_requests.get("diff") is None

            await pilot.press("d")
            second = await _wait_diff_report(pilot, app)
            assert second._owned_request is None
            accepted = second.report
            assert accepted is not None

            # Release the abandoned first worker and wait until the app has really
            # processed its outcome; only then assert it changed nothing.
            gate.set()
            await _wait_until(
                pilot,
                lambda: any(
                    view == "diff" and request_id == token_a.request_id
                    for view, request_id, _ in processed
                ),
                "abandoned result processed by the app",
            )
            abandoned = [
                ok
                for view, request_id, ok in processed
                if view == "diff" and request_id == token_a.request_id
            ]
            assert abandoned == [False], "the abandoned result must be rejected"
            assert second.report is accepted
            assert app.controller.active_requests.get("diff") is None
            assert app.controller.failed is False
            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_diff", controlled_diff)
    asyncio.run(_run())


def test_old_diff_screen_cleanup_cannot_cancel_a_newer_owner(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C1: a screen still holding superseded token A must never cancel the active B.

    Two real requests exist at once: the open Diff screen owns A (still pending)
    while the ordinary report adapter creates the newer B, which supersedes A.
    Closing the old screen then runs its real cleanup path. The equality guard
    there is the only thing keeping B's token, its cancellation event and its
    eventual report alive; without it the cleanup would invalidate B and its
    completed report would be rejected instead of cached and reusable.
    """
    build_scenario("claude_personal_beats_project", mock_home)
    started: dict[int, threading.Event] = {1: threading.Event(), 2: threading.Event()}
    gates: dict[int, threading.Event] = {1: threading.Event(), 2: threading.Event()}
    calls = {"count": 0}
    real_diff = snapshot_diff

    def controlled_diff(snapshot: Any, key: str) -> Any:
        calls["count"] += 1
        index = calls["count"]
        started[index].set()
        gates[index].wait(timeout=5.0)
        return real_diff(snapshot, key)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_diff", controlled_diff)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        try:
            async with app.run_test(size=(100, 30)) as pilot:
                await _wait_ready(pilot, app)
                key = app.controller.selected_key
                assert key is not None

                await pilot.press("d")
                await _wait_until(pilot, started[1].is_set, "diff request A started")
                old_screen = app.screen
                assert isinstance(old_screen, DiffScreen)
                token_a = old_screen._owned_request
                assert token_a is not None
                event_a = app.controller._report_events[token_a.request_id]
                assert not event_a.is_set()

                # The newer request B is created through the same public adapter
                # every screen uses. The controller supersedes A with it.
                assert app.request_report("diff", (key,)) is None
                await _wait_until(pilot, started[2].is_set, "diff request B started")
                token_b = app.controller.active_requests.get("diff")
                assert token_b is not None and token_b != token_a
                event_b = app.controller._report_events[token_b.request_id]
                assert event_a.is_set(), "superseding B must cancel A"
                assert not event_b.is_set(), "creating B must not cancel B"
                assert old_screen._owned_request == token_a, (
                    "the old screen must still be holding its stale token A here"
                )

                # Closing the old screen runs its real cleanup (close_diff ->
                # _cancel_owned_token). It must leave B untouched.
                await pilot.press("escape")
                await pilot.pause()
                assert isinstance(app.screen, HomeScreen)
                assert old_screen._owned_request is None
                assert app.controller.active_requests.get("diff") == token_b, (
                    "old-owner cleanup removed the newer owner's request"
                )
                assert not event_b.is_set(), "old-owner cleanup cancelled the newer owner"

                # B completes, is accepted, cached and reusable without a third worker.
                gates[2].set()
                current = app.controller.current
                assert current is not None
                cache_key = (current.generation, "diff", (key,))
                await _wait_until(
                    pilot,
                    lambda: app.controller.cache.get(cache_key) is not None,
                    "newer owner's report accepted into the cache",
                )
                accepted = app.controller.cache[cache_key]
                await pilot.press("d")
                reopened = await _wait_diff_report(pilot, app)
                assert reopened.report is accepted
                assert calls["count"] == 2, "the cached report must not re-dispatch"
                await pilot.press("q")
                assert app.return_code == int(ExitCode.OK)
        finally:
            gates[1].set()
            gates[2].set()

    asyncio.run(_run())


def test_refresh_replaces_report_and_never_mixes_generations(mock_home: Path) -> None:
    """A published refresh invalidates the old report before the new one arrives."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("d")
            diff = await _wait_diff_report(pilot, app)
            first = diff.report
            assert first is not None
            current = app.controller.current
            assert current is not None
            first_generation = current.generation

            write_skill(
                mock_home / ".claude" / "skills" / "deploy",
                "---\nname: deploy\ndescription: Personal deploy helper.\n---\n"
                "# Instructions\n\nFresh body after refresh.\n",
            )
            await pilot.press("r")
            await _wait_until(
                pilot,
                lambda: (
                    app.controller.current is not None
                    and app.controller.current.generation != first_generation
                    and isinstance(app.screen, DiffScreen)
                    and app.screen.report is not None
                    and app.screen.report is not first
                ),
                "new generation report",
            )
            assert isinstance(app.screen, DiffScreen)
            assert app.screen._generation == app.controller.current.generation
            assert "Fresh body after refresh." in _body_text(app)
            await pilot.press("q")

    asyncio.run(_run())


def test_failed_capture_keeps_the_last_usable_report(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An expected capture refusal keeps the report and shows the retry message."""
    build_scenario("claude_personal_beats_project", mock_home)
    calls = {"count": 0}
    real_capture = capture_session

    def flaky_capture(*args: Any, **kwargs: Any) -> Any:
        calls["count"] += 1
        if calls["count"] == 1:
            return real_capture(*args, **kwargs)
        raise SnapshotChanged()

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("d")
            diff = await _wait_diff_report(pilot, app)
            kept = diff.report
            assert kept is not None

            await pilot.press("r")
            await _wait_until(
                pilot, lambda: app.controller.retry_message is not None, "retry message"
            )
            assert app.controller.failed is False
            assert diff.report is kept
            status = str(diff.query_one("#diff-status", Static).content)
            assert "Files changed while scanning" in status
            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    monkeypatch.setattr("skill_lens.tui.app.capture_session", flaky_capture)
    asyncio.run(_run())


def test_accepted_diff_fault_is_plain_english_and_exits_three(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An accepted unexpected fault keeps details in memory and exits 3 on quit."""

    def failing_diff(snapshot: Any, key: str) -> Any:
        raise RuntimeError("accepted diff fault")

    monkeypatch.setattr("skill_lens.tui.app.snapshot_diff", failing_diff)
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("d")
            await _wait_until(
                pilot,
                lambda: isinstance(app.screen, DiffScreen) and app.controller.failed,
                "accepted diff fault",
            )
            diff = app.screen
            assert isinstance(diff, DiffScreen)
            status = str(diff.query_one("#diff-status", Static).content)
            details = str(diff.query_one("#diff-error-details", Static).content)
            assert "Error: Unexpected internal fault. Details in memory only." in status
            assert "accepted diff fault" in details
            await pilot.press("q")
            assert app.return_code == int(ExitCode.INTERNAL)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Refresh and removal
# ---------------------------------------------------------------------------


def test_removal_under_diff_over_why_returns_home_with_notice(mock_home: Path) -> None:
    """Diff pops first, the revealed Why closes itself, and Home shows the notice."""
    make_skill(mock_home / ".claude" / "skills" / "skill-a", "skill-a", "Skill A.")
    make_skill(mock_home / ".claude" / "skills" / "skill-b", "skill-b", "Skill B.")

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await _select_key(
                pilot, app, next(key for key in _row_keys(app) if key.endswith("skill-a"))
            )
            await pilot.press("enter")
            await _wait_until(
                pilot,
                lambda: isinstance(app.screen, WhyScreen) and app.screen._report is not None,
                "why report",
            )
            await pilot.press("d")
            diff = await _wait_diff_report(pilot, app)
            removed_key = diff.opening_key

            shutil.rmtree(mock_home / ".claude" / "skills" / "skill-a")
            await pilot.press("r")
            await _wait_until(pilot, lambda: isinstance(app.screen, HomeScreen), "return to home")
            home = app.screen
            assert isinstance(home, HomeScreen)
            assert home._removal_notice is not None
            assert removed_key in home._removal_notice
            # Neither detail screen is left stranded in the stack.
            assert not any(isinstance(s, (DiffScreen, WhyScreen)) for s in app.screen_stack)
            assert removed_key in str(home.query_one("#removal-notice", Static).content)

            await pilot.press("down")
            await pilot.pause(0.02)
            assert home._removal_notice is None
            await pilot.press("q")

    asyncio.run(_run())


def test_removal_under_diff_over_home_shows_the_removal_notice(mock_home: Path) -> None:
    """A Diff opened straight from Home reports the removal itself."""
    make_skill(mock_home / ".claude" / "skills" / "solo", "solo", "Solo skill.")
    make_skill(mock_home / ".claude" / "skills" / "other", "other", "Other skill.")

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await _select_key(pilot, app, next(key for key in _row_keys(app) if "solo" in key))
            await pilot.press("d")
            diff = await _wait_diff_report(pilot, app)
            removed_key = diff.opening_key

            shutil.rmtree(mock_home / ".claude" / "skills" / "solo")
            await pilot.press("r")
            await _wait_until(pilot, lambda: isinstance(app.screen, HomeScreen), "return to home")
            home = app.screen
            assert isinstance(home, HomeScreen)
            assert home._removal_notice is not None
            assert removed_key in home._removal_notice
            assert not any(isinstance(s, DiffScreen) for s in app.screen_stack)
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Frozen first visit under input changes (R5)
# ---------------------------------------------------------------------------


def _forbid_all_reads(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    """Ban every live read/probe the browsing path could fall back to.

    The target-scoped file guards only raise for paths inside the synthetic home,
    so Textual's own incidental reads elsewhere stay allowed. The discovery,
    registry, filesystem-walk and paths helpers are banned outright: browsing must
    not call them at all.
    """

    target_prefixes = {os.path.abspath(str(home)), str(home.resolve())}

    def _is_target(value: Any) -> bool:
        try:
            text = os.fspath(value)
        except TypeError:
            return False
        if isinstance(text, bytes):
            text = text.decode("utf-8", "surrogateescape")
        absolute = os.path.abspath(text)
        return any(
            absolute == prefix or absolute.startswith(prefix + os.sep) for prefix in target_prefixes
        )

    originals = {
        name: getattr(Path, name) for name in ("open", "read_text", "read_bytes", "resolve")
    }
    builtin_open = builtins.open

    def _guarded(original: Any, label: str) -> Any:
        def wrapper(target: Any, *args: Any, **kwargs: Any) -> Any:
            if _is_target(target):
                raise AssertionError(f"Forbidden synthetic-target read during browsing: {label}")
            return original(target, *args, **kwargs)

        return wrapper

    def forbid(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Forbidden live discovery/registry/probe during browsing")

    monkeypatch.setattr("skill_lens.core.system.live_discovery", forbid)
    monkeypatch.setattr("skill_lens.core.discovery.discover", forbid)
    monkeypatch.setattr("skill_lens.registry.loader.load_registry", forbid)
    monkeypatch.setattr("skill_lens.registry.loader.list_agents", forbid)
    monkeypatch.setattr("skill_lens.core.snapshot.load_registry", forbid)
    monkeypatch.setattr("skill_lens.core.diff.load_registry", forbid)
    monkeypatch.setattr("skill_lens.core.diff.iter_files", forbid)
    monkeypatch.setattr("skill_lens.core.diff.hash_file", forbid)
    monkeypatch.setattr("skill_lens.core.paths.home", forbid)
    monkeypatch.setattr("skill_lens.core.paths.display", forbid)
    monkeypatch.setattr("skill_lens.core.paths.same_location", forbid)
    monkeypatch.setattr(Path, "open", _guarded(originals["open"], "Path.open"))
    monkeypatch.setattr(Path, "read_text", _guarded(originals["read_text"], "Path.read_text"))
    monkeypatch.setattr(Path, "read_bytes", _guarded(originals["read_bytes"], "Path.read_bytes"))
    monkeypatch.setattr(Path, "resolve", _guarded(originals["resolve"], "Path.resolve"))
    monkeypatch.setattr(builtins, "open", _guarded(builtin_open, "builtins.open"))


def test_first_diff_visit_is_frozen_after_captured_inputs_change(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Diff and its JSON stay on the captured inputs, then refresh publishes new data.

    A real shortcut is seeded *before* the independent expectations and the
    capture, then the same shortcut is retargeted to a different existing target
    after publication. Frozen first visits must keep the captured canonical
    identity, entrypoint count and content; an explicit refresh must see the new
    target.
    """
    project = _build_three_change_copy_fixture(mock_home)
    global_dir = mock_home / ".claude" / "skills" / "asset"
    project_dir = project / ".claude" / "skills" / "asset"

    # A third real skill outside every agent root: only reachable through the
    # shortcut, and the destination that shortcut is retargeted to later.
    variant_dir = mock_home / "elsewhere" / "asset-variant"
    make_skill(variant_dir, "asset", "Variant asset.", body="# Variant body\n")

    # Seed the shortcut BEFORE the oracle and the capture.
    shortcut = mock_home / ".agents" / "skills" / "asset"
    shortcut.parent.mkdir(parents=True, exist_ok=True)
    shortcut.symlink_to(global_dir, target_is_directory=True)

    registry = load_registry()
    index = live_discovery(cwd=project, registry=registry)
    expected = build_diff_report(
        "asset", Path(index.cwd), Path(index.home), index=index, registry=registry
    )
    expected_document = dumps(expected.to_dict())
    expected_scan = dumps(
        build_scan_report(Path(index.home), Path(index.cwd), index, registry).to_dict()
    )
    # The seeded shortcut is part of the frozen input: the global copy is reached
    # both directly and through the link.
    frozen_row = next(
        row
        for row in build_scan_report(Path(index.home), Path(index.cwd), index, registry).skills
        if row.canonical_path == str(global_dir)
    )
    assert frozen_row.entrypoint_count == 2, "the seeded shortcut must be captured"
    assert str(variant_dir) not in {copy.path for copy in expected.copies}
    assert len(expected.copies) == 2

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            # Retarget the SAME pre-existing shortcut to a different existing
            # target, and change content and settings after the capture.
            shortcut.unlink()
            shortcut.symlink_to(variant_dir, target_is_directory=True)
            write_skill(
                global_dir,
                "---\nname: asset\ndescription: Edited after capture.\n---\n# Edited body\n",
            )
            (project_dir / "removed.txt").unlink()
            (project_dir / "brand.txt").write_text("added after capture\n", encoding="utf-8")
            settings = mock_home / ".claude" / "settings.json"
            settings.write_text('{"skillOverrides": {"asset": "off"}}', encoding="utf-8")

            with monkeypatch.context() as mp:
                _forbid_all_reads(mp, mock_home)
                # Prove the bans are live, so a fallback read cannot pass silently.
                with pytest.raises(AssertionError):
                    (global_dir / "SKILL.md").read_text(encoding="utf-8")

                await pilot.press("d")
                diff = await _wait_diff_report(pilot, app)
                report = diff.report
                assert report is not None
                assert report.to_dict() == expected.to_dict(), "first Diff visit read live inputs"
                assert dumps(report.to_dict()) == expected_document
                # Captured canonical identity, not the retargeted one.
                assert {copy.path for copy in report.copies} == {str(global_dir), str(project_dir)}
                assert "asset-variant" not in _body_text(app), (
                    "the retargeted shortcut must not appear on a frozen first visit"
                )

                await pilot.press("J")
                await pilot.pause()
                view = app.screen.query_one("#diff-json", JsonView)
                assert view.document == expected_document
                assert "Edited after capture" not in (view.document or "")
                assert "brand.txt" not in (view.document or "")

            # A Home JSON first visit is frozen too: the captured entrypoint count
            # still reflects the shortcut as it was when the session was captured.
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("escape")
            await _wait_until(pilot, lambda: isinstance(app.screen, HomeScreen), "back home")
            await pilot.press("J")
            await pilot.pause()
            home_view = app.screen.query_one("#home-json", JsonView)
            assert home_view.document == expected_scan

            # Bans lifted: an explicit refresh publishes the new captured inputs.
            await pilot.press("r")
            await _wait_until(
                pilot,
                lambda: (
                    app.controller.current is not None
                    and "asset-variant" in (home_view.document or "")
                ),
                "refreshed Home JSON sees the retargeted shortcut",
            )
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("d")
            await _wait_until(
                pilot,
                lambda: (
                    isinstance(app.screen, DiffScreen)
                    and app.screen.report is not None
                    and app.screen.report.to_dict() != expected.to_dict()
                ),
                "refreshed diff report",
            )
            refreshed = app.screen._report
            assert refreshed is not None
            assert len(refreshed.copies) == 3, "the retargeted shortcut adds the variant copy"
            assert str(variant_dir) in {copy.path for copy in refreshed.copies}
            text = _body_text(app)
            assert "removed.txt" not in text
            assert "brand.txt" in text
            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Real ordering, blocked workers and cache takeover (R5)
# ---------------------------------------------------------------------------


def test_older_capture_completing_last_cannot_replace_the_newer_generation(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Diff/JSON keeps the newest capture when an older one finishes afterwards."""
    build_scenario("claude_personal_beats_project", mock_home)
    real_capture = capture_session
    started: dict[int, threading.Event] = {2: threading.Event(), 3: threading.Event()}
    gates: dict[int, threading.Event] = {2: threading.Event(), 3: threading.Event()}

    def controlled_capture(*, generation: int, home: Path, cwd: Path, **kwargs: Any) -> Any:
        snapshot = real_capture(generation=generation, home=home, cwd=cwd, **kwargs)
        if generation in started:
            started[generation].set()
            gates[generation].wait(timeout=5.0)
        return snapshot

    monkeypatch.setattr("skill_lens.tui.app.capture_session", controlled_capture)

    def _write_body(marker: str) -> None:
        write_skill(
            mock_home / ".claude" / "skills" / "deploy",
            f"---\nname: deploy\ndescription: Personal deploy helper.\n---\n# {marker}\n",
        )

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        captures: list[tuple[int, bool]] = []
        original_accept_capture = app.controller.accept_capture

        def recording_accept_capture(snapshot: Any, generation: int) -> bool:
            accepted = original_accept_capture(snapshot, generation)
            captures.append((generation, accepted))
            return accepted

        app.controller.accept_capture = recording_accept_capture  # type: ignore[method-assign]
        try:
            async with app.run_test(size=(100, 30)) as pilot:
                await _wait_ready(pilot, app)
                await pilot.press("d")
                await _wait_diff_report(pilot, app)
                await pilot.press("J")
                await pilot.pause()
                view = app.screen.query_one("#diff-json", JsonView)

                # Generation 2 captures FIRST-EDIT and then blocks.
                _write_body("FIRST-EDIT")
                await pilot.press("r")
                await _wait_until(pilot, started[2].is_set, "generation 2 captured")

                # Generation 3 captures SECOND-EDIT and then blocks.
                _write_body("SECOND-EDIT")
                await pilot.press("r")
                await _wait_until(pilot, started[3].is_set, "generation 3 captured")

                # The newer capture publishes first.
                gates[3].set()
                await _wait_until(
                    pilot,
                    lambda: (
                        app.controller.current is not None
                        and app.controller.current.generation == 3
                        and "SECOND-EDIT" in (view.document or "")
                    ),
                    "generation 3 published",
                )

                # The older capture finishes last. Wait until the app has actually
                # processed its outcome, then assert it was rejected.
                gates[2].set()
                await _wait_until(
                    pilot,
                    lambda: any(generation == 2 for generation, _ in captures),
                    "older capture outcome processed by the app",
                )
                assert [ok for generation, ok in captures if generation == 2] == [False], (
                    "the older capture must be rejected, not published"
                )
                assert [ok for generation, ok in captures if generation == 3] == [True]
                assert app.controller.current is not None
                assert app.controller.current.generation == 3
                assert app.controller.pending_generation is None
                assert "FIRST-EDIT" not in (view.document or "")
                assert "SECOND-EDIT" in (view.document or "")
                diff = app.screen
                assert isinstance(diff, DiffScreen)
                assert diff._generation == 3
                assert diff.report is not None
                await pilot.press("q")
                assert app.return_code == int(ExitCode.OK)
        finally:
            gates[2].set()
            gates[3].set()

    asyncio.run(_run())


def test_quit_while_a_diff_report_worker_is_blocked(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Quitting from a pending Diff report returns 0 and takes no late update."""
    build_scenario("claude_personal_beats_project", mock_home)
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    real_diff = snapshot_diff

    def blocking_diff(snapshot: Any, key: str) -> Any:
        started.set()
        release.wait(5.0)
        try:
            return real_diff(snapshot, key)
        finally:
            finished.set()

    monkeypatch.setattr("skill_lens.tui.app.snapshot_diff", blocking_diff)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        try:
            async with app.run_test(size=(100, 30)) as pilot:
                await _wait_ready(pilot, app)
                await pilot.press("d")
                await _wait_until(pilot, started.is_set, "diff worker started")
                diff = app.screen
                assert isinstance(diff, DiffScreen)
                assert diff.report is None

                await pilot.press("q")
                assert app.return_code == int(ExitCode.OK)
                assert app.controller.closed is True
        finally:
            release.set()
            assert finished.wait(5.0)

        # The late worker result is dropped: no accepted report, no fault.
        assert app.controller.failed is False
        assert app.controller.cache == {}
        assert app.controller.active_requests == {}

    asyncio.run(_run())


def test_cache_hit_diff_does_not_disturb_another_views_request(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reopening Diff from cache must not cancel or replace an unrelated request."""
    build_scenario("symlink_farm_multi_agent", mock_home)
    started = threading.Event()
    release = threading.Event()
    real_compare = snapshot_compare

    def blocking_compare(snapshot: Any, agent_a: str, agent_b: str) -> Any:
        started.set()
        release.wait(timeout=5.0)
        return real_compare(snapshot, agent_a, agent_b)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_compare", blocking_compare)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        try:
            async with app.run_test(size=(100, 30)) as pilot:
                await _wait_ready(pilot, app)
                await pilot.press("d")
                first = await _wait_diff_report(pilot, app)
                cached = first.report
                assert cached is not None
                await pilot.press("escape")
                await pilot.pause()

                # An unrelated view request is now in flight.
                assert app.request_report("compare", ("claude", "pi")) is None
                await _wait_until(pilot, started.is_set, "compare worker started")
                compare_token = app.controller.active_requests.get("compare")
                assert compare_token is not None

                # Reopening Diff is a pure cache hit.
                await pilot.press("d")
                second = await _wait_diff_report(pilot, app)
                assert second.report is cached
                assert app.controller.active_requests.get("compare") == compare_token
                assert app.controller.active_requests.get("diff") is None
                await pilot.press("q")
                assert app.return_code == int(ExitCode.OK)
        finally:
            release.set()

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Why focus preservation across Diff (FR1)
# ---------------------------------------------------------------------------


async def _settle_focus(pilot: Any, app: SkillLensApp) -> None:
    """Wait until the focused widget stops changing across consecutive turns.

    Focus restoration is deferred by Textual, so the final target only exists
    after the pending callbacks have run. This observes stability instead of
    sleeping for a guessed duration.
    """
    last = app.focused
    stable = 0
    for _ in range(200):
        await pilot.pause(0.01)
        if app.focused is last:
            stable += 1
            if stable >= 3:
                return
        else:
            last = app.focused
            stable = 0
    raise AssertionError("focus never settled")


async def _focus_why_control(pilot: Any, app: SkillLensApp, target: str) -> Any:
    """Reach one of Why's ordinary controls using real Tab navigation."""

    def is_target(widget: Any) -> bool:
        if widget is None:
            return False
        if target == "body":
            return getattr(widget, "id", None) == "why-body"
        return type(widget).__name__ == "CollapsibleTitle"

    for _ in range(12):
        if is_target(app.focused):
            return app.focused
        await pilot.press("tab")
    raise AssertionError(f"Tab navigation never reached the {target} control")


@pytest.mark.parametrize("size", [(100, 30), (60, 24)])
@pytest.mark.parametrize("focus_target", ["candidate", "body"])
@pytest.mark.parametrize("back_key", ["escape", "backspace"])
def test_returning_from_diff_restores_the_originating_why_focus(
    mock_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    size: tuple[int, int],
    focus_target: str,
    back_key: str,
) -> None:
    """FR1: Why → Diff → Why must keep the still-valid originating focus control.

    Both resume routes really run: the host's explicit resume from ``close_diff``
    and Textual's own ``ScreenResume``. Whichever runs last must not move focus to
    the agent strip when the remembered control is still mounted and usable.
    Agent selection, candidate expansion, ordinary scroll and request dedup must
    all survive the round trip.
    """
    build_scenario("claude_personal_beats_project", mock_home)

    workers = {"count": 0}
    real_why = snapshot_why

    def counting_why(snapshot: Any, key: str, agent: str) -> Any:
        workers["count"] += 1
        return real_why(snapshot, key, agent)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", counting_why)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=size) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_until(
                pilot,
                lambda: isinstance(app.screen, WhyScreen) and app.screen._report is not None,
                "why report",
            )
            why = app.screen
            assert isinstance(why, WhyScreen)

            target = await _focus_why_control(pilot, app, focus_target)
            assert app.focused is target
            body = why.query_one("#why-body", VerticalScroll)
            if focus_target == "candidate":
                # Give the ordinary scroll a non-zero position to preserve.
                await pilot.press("down")
                await pilot.pause(0.05)
                await _focus_why_control(pilot, app, focus_target)
                assert app.focused is target
            agent_before = why._agent_id
            expanded_before = [item.collapsed for item in why.query("Collapsible")]
            scroll_before = body.scroll_offset.y
            workers_before = workers["count"]

            resumes: list[int] = []
            original_resume = why.resume_detail

            def recording_resume() -> None:
                resumes.append(1)
                original_resume()

            why.resume_detail = recording_resume  # type: ignore[method-assign]

            for trip in (1, 2):
                await pilot.press("d")
                await _wait_diff_report(pilot, app)
                await pilot.press(back_key)
                await _wait_until(pilot, lambda: app.screen is why, f"back on Why ({trip})")
                await _wait_until(
                    pilot,
                    lambda trip=trip: len(resumes) >= 2 * trip,
                    f"both resume routes ran ({trip})",
                )
                await _settle_focus(pilot, app)

                assert target.is_mounted and target.display, (
                    "the originating control must still be mounted"
                )
                assert app.focused is target, (
                    f"round trip {trip} replaced the originating {focus_target} focus with "
                    f"{type(app.focused).__name__} {getattr(app.focused, 'id', None)!r}"
                )

            # Nothing else moved: agent, expansion, ordinary scroll and request count.
            assert why._agent_id == agent_before
            assert [item.collapsed for item in why.query("Collapsible")] == expanded_before
            assert body.scroll_offset.y == scroll_before
            assert workers["count"] == workers_before, "a cached report must not be re-requested"
            assert why._report is not None
            assert why._owned_request is None
            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())


def test_resume_after_a_covered_refresh_falls_back_to_a_valid_control(
    mock_home: Path,
) -> None:
    """A remembered control rebuilt by refresh is dropped, not resurrected.

    The focus restoration is idempotent while the control is valid, but a new
    generation recreates the candidate widgets. Returning then has to land on a
    valid ordinary control instead of a stale, unmounted widget.
    """
    build_scenario("claude_personal_beats_project", mock_home)
    global_dir = mock_home / ".claude" / "skills" / "deploy"

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_until(
                pilot,
                lambda: isinstance(app.screen, WhyScreen) and app.screen._report is not None,
                "why report",
            )
            why = app.screen
            assert isinstance(why, WhyScreen)
            stale = await _focus_why_control(pilot, app, "candidate")

            await pilot.press("d")
            await _wait_diff_report(pilot, app)

            # Change the captured inputs and refresh while Diff is covering.
            write_skill(
                global_dir,
                "---\nname: deploy\ndescription: Personal deploy helper.\n---\n"
                "# Instructions\n\nRefreshed body while covered.\n",
            )
            generation_before = app.controller.current.generation
            await pilot.press("r")
            await _wait_until(
                pilot,
                lambda: (
                    app.controller.current is not None
                    and app.controller.current.generation != generation_before
                    and app.controller.status == "ready"
                    and isinstance(app.screen, DiffScreen)
                    and app.screen.report is not None
                ),
                "diff rebound after the covered refresh",
            )

            await pilot.press("escape")
            await _wait_until(
                pilot,
                lambda: isinstance(app.screen, WhyScreen) and app.screen._report is not None,
                "why report for the new generation",
            )
            await _settle_focus(pilot, app)
            assert app.screen is why
            assert why._generation == app.controller.current.generation
            assert why._detail_focus is None, "a stale remembered control must be dropped"
            focused = app.focused
            assert focused is not None
            assert focused.is_mounted and focused.can_focus and focused.display
            assert focused is not stale, "the rebuilt generation must not resurrect a stale widget"
            assert why._report is not None
            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())
