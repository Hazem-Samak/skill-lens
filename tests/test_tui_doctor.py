"""Headless U7 Doctor tests using captured sessions and synthetic homes."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest
from textual.containers import VerticalScroll
from textual.widgets import DataTable, Input, Static
from typer.testing import CliRunner

import skill_lens.tui.app as app_module
from skill_lens.cli import app as cli_app
from skill_lens.core import paths
from skill_lens.core.discovery import canonical_key
from skill_lens.core.snapshot import capture_session
from skill_lens.models import dumps
from skill_lens.models.doctor import DoctorFinding, DoctorReport
from skill_lens.models.enums import Evidence, Severity
from skill_lens.tui.app import SkillLensApp
from skill_lens.tui.doctor import (
    DoctorScreen,
    doctor_summary,
    finding_catalog_keys,
    finding_detail_text,
    finding_identities,
)
from skill_lens.tui.home import HomeScreen
from skill_lens.tui.json_view import JsonView
from tests.fixtures.builders import make_skill, symlink
from tests.fixtures.scenarios import build_scenario

runner = CliRunner()


def _finding(
    code: str = "literal_code",
    *,
    severity: Severity = Severity.ERROR,
    message: str = "[bold]literal[/bold] message",
    path: str | None = None,
    detail: str | None = "detail [red]literal[/red]",
    rule_id: str = "doctor_literal_rule",
    evidence: Evidence = Evidence.EMPIRICAL,
) -> DoctorFinding:
    return DoctorFinding(
        code=code,
        severity=severity,
        message=message,
        path=path,
        detail=detail,
        rule_id=rule_id,
        evidence=evidence,
    )


async def _wait_until(pilot: Any, predicate: Any, label: str, timeout: float = 6.0) -> None:
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
            and app.controller.pending_generation is None
            and app.controller.status == "ready"
        ),
        "captured session",
    )
    await pilot.pause(0.02)


def _table_rows(table: DataTable) -> list[list[str]]:
    return [[str(value) for value in table.get_row_at(index)] for index in range(table.row_count)]


def test_finding_catalog_keys_use_only_exact_captured_identity(mock_home: Path) -> None:
    """Captured aliases match; names, roots and unrelated paths never guess."""
    canonical = mock_home / ".claude" / "skills" / "same-name"
    make_skill(canonical, "same-name", "First copy.")
    alias = mock_home / ".agents" / "skills" / "alias"
    symlink(canonical, alias)
    other = mock_home / ".codex" / "skills" / "same-name"
    make_skill(other, "same-name", "Second copy.")
    snapshot = capture_session(generation=1, home=paths.home(), cwd=mock_home)

    first = next(
        entry for entry in snapshot.index.entries if entry.canonical_path == str(canonical)
    )
    first_key = canonical_key(first)
    expected_paths = {
        first.entrypoint_path,
        *first.entrypoint_paths,
        *(hit.entrypoint_path for hit in first.hits),
        first.canonical_path,
    }
    for path in expected_paths:
        assert path is not None
        assert finding_catalog_keys(snapshot, _finding(path=path)) == (first_key,)

    displayed = snapshot.display_paths[first.entrypoint_path]
    assert finding_catalog_keys(snapshot, _finding(path=displayed)) == (first_key,)
    assert finding_catalog_keys(snapshot, _finding(path="same-name")) == ()
    assert (
        finding_catalog_keys(snapshot, _finding(path=str(mock_home / ".claude" / "skills"))) == ()
    )
    assert finding_catalog_keys(snapshot, _finding(path=None)) == ()
    assert finding_catalog_keys(snapshot, _finding(path="/outside/lock.json")) == ()
    lock_display = snapshot.display_paths[str(mock_home / ".agents" / ".skill-lock.json")]
    assert finding_catalog_keys(snapshot, _finding(path=lock_display)) == ()

    distinct = [entry for entry in snapshot.index.entries if canonical_key(entry) != first_key]
    second_key = canonical_key(distinct[0])
    collision = "~/synthetic/ambiguous"
    display_paths = dict(snapshot.display_paths)
    display_paths[first.entrypoint_path] = collision
    display_paths[distinct[0].entrypoint_path] = collision
    ambiguous_snapshot = replace(snapshot, display_paths=MappingProxyType(display_paths))
    assert finding_catalog_keys(ambiguous_snapshot, _finding(path=collision)) == tuple(
        sorted((first_key, second_key))
    )


def test_duplicate_finding_identity_and_summary_distinguish_info_from_empty() -> None:
    duplicate = _finding("same")
    rows = finding_identities(4, (duplicate, duplicate))
    assert rows[0].generation == rows[1].generation == 4
    assert rows[0].finding == rows[1].finding == duplicate
    assert (rows[0].occurrence, rows[1].occurrence) == (0, 1)

    empty = DoctorReport(home="/tmp/home", cwd="/tmp/work", findings=())
    info = DoctorReport(
        home="/tmp/home",
        cwd="/tmp/work",
        findings=(_finding("info_note", severity=Severity.INFO),),
    )
    assert empty.healthy and info.healthy
    assert doctor_summary(empty) == "Skill folders look healthy."
    assert "1 findings" in doctor_summary(info)
    assert "1 info" in doctor_summary(info)
    assert "Status: healthy" in doctor_summary(info)


def test_real_captured_findings_keep_model_order_and_cli_json(mock_home: Path) -> None:
    """A real report with all severities renders in stored order and exact JSON."""
    build_scenario("malformed_frontmatter", mock_home)
    farm = mock_home / ".agents" / "skills" / "shared"
    make_skill(farm, "shared", "Shared library.")
    for root in (".claude/skills", ".pi/agent/skills", ".qoder/skills"):
        symlink(farm, mock_home / root / "shared")
    symlink(mock_home / "missing-target", mock_home / ".claude" / "skills" / "ghost")
    lock = mock_home / ".agents" / ".skill-lock.json"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_bytes(b"\xff\xfe")

    cli = runner.invoke(
        cli_app,
        ["doctor", "--json", "--sandbox", str(mock_home), "--cwd", str(mock_home)],
    )
    assert cli.exit_code == 0
    expected_document = cli.stdout.removesuffix("\n")
    expected_report = DoctorReport.from_dict(json.loads(expected_document))
    assert [finding.severity for finding in expected_report.findings] == [
        Severity.ERROR,
        Severity.ERROR,
        Severity.ERROR,
        Severity.WARNING,
        Severity.INFO,
    ]
    assert [finding.code for finding in expected_report.findings] == [
        "dangling_symlink",
        "malformed_frontmatter",
        "malformed_frontmatter",
        "installer_lockfile",
        "symlink_farm",
    ]
    dangling = expected_report.findings[0]
    assert dangling.path == "~/.claude/skills/ghost"
    assert dangling.message == (
        "'~/.claude/skills/ghost' links to a target that does not exist "
        "-- claude, opencode cannot load 'ghost'."
    )
    lock_warning = expected_report.findings[3]
    assert lock_warning.message == (
        "'~/.agents/.skill-lock.json' is not valid JSON -- the installer may mis-read it."
    )
    assert lock_warning.detail == "not_json"

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("h")
            screen = app.screen
            assert isinstance(screen, DoctorScreen)
            table = screen.query_one("#doctor-findings", DataTable)
            assert table.row_count == len(expected_report.findings)
            assert _table_rows(table) == [
                [
                    finding.severity.value,
                    finding.code,
                    finding.message,
                    finding.path if finding.path is not None else "(none)",
                ]
                for finding in expected_report.findings
            ]
            assert screen.query_one("#doctor-summary", Static).content.plain == doctor_summary(
                expected_report
            )
            await pilot.press("J")
            view = screen.query_one("#doctor-json", JsonView)
            assert view.document == expected_document
            assert view.document + "\n" == cli.stdout
            await pilot.press("escape")
            assert not screen.json_mode
            snapshot = app.controller.current
            assert snapshot is not None
            ghost = next(entry for entry in snapshot.index.entries if entry.name == "ghost")
            assert finding_catalog_keys(snapshot, dangling) == (canonical_key(ghost),)
            await pilot.press("enter")
            assert isinstance(app.screen, HomeScreen)
            assert app.controller.selected_key == canonical_key(ghost)
            await pilot.press("q")

    asyncio.run(_run())


def test_doctor_shows_literal_fields_and_full_detail_at_both_widths(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Markup-like values stay literal; long details remain reachable when narrow."""
    make_skill(mock_home / ".claude" / "skills" / "target", "target", "Target skill.")
    original_capture = app_module.capture_session
    long_text = "[bold]literal[/bold] " + "long detail line\n" * 40
    findings = (
        _finding(
            "literal_path",
            message="[red]message[/red] " + "m" * 140,
            path="[green]literal/path[/green] " + "p" * 140,
            detail=long_text,
            rule_id="[rule]literal[/rule]",
            evidence=Evidence.DOCUMENTED,
        ),
        _finding("duplicate", severity=Severity.WARNING, path=None, detail=None),
        _finding("duplicate", severity=Severity.WARNING, path=None, detail=None),
    )

    def captured(**kwargs: Any) -> Any:
        snapshot = original_capture(**kwargs)
        report = DoctorReport(
            home="[blue]context[/blue]",
            cwd="[yellow]working[/yellow]",
            findings=findings,
        )
        return replace(snapshot, doctor=report)

    monkeypatch.setattr(app_module, "capture_session", captured)

    async def _run(size: tuple[int, int]) -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=size) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("h")
            screen = app.screen
            assert isinstance(screen, DoctorScreen)
            assert screen.has_class("narrow") is (size[0] < 80)
            table = screen.query_one("#doctor-findings", DataTable)
            assert table.row_count == 3
            assert _table_rows(table)[0][2] == findings[0].message
            assert _table_rows(table)[0][3] == findings[0].path
            detail = screen.query_one("#doctor-detail", Static).content.plain
            assert finding_detail_text(findings[0]) == detail
            assert long_text in detail
            assert "Rule ID: [rule]literal[/rule]" in detail
            assert "Path: [green]literal/path[/green]" in detail
            assert "Evidence: documented" in detail
            assert findings[0].detail is not None
            assert f"Detail: {findings[0].detail}" in detail
            context = screen.query_one("#doctor-context", Static).content.plain
            assert "Home: [blue]context[/blue]" in context
            assert "Cwd: [yellow]working[/yellow]" in context
            await pilot.press("enter")
            assert screen.navigation_notice == (
                f"No matching catalog entry for this path: {findings[0].path}"
            )
            assert not app.controller.is_failed

            table.move_cursor(row=1, column=0, animate=False)
            await pilot.pause()
            selected_occurrence = screen.selected_identity
            assert selected_occurrence is not None and selected_occurrence.occurrence == 0
            null_detail = screen.query_one("#doctor-detail", Static).content.plain
            assert "Path: (none)" in null_detail
            assert "Detail: (none)" in null_detail
            await pilot.press("enter")
            assert screen.navigation_notice == "This finding has no path to select in Home."
            await pilot.press("down")
            await pilot.pause()
            assert screen.selected_identity is not None
            assert screen.selected_identity.occurrence == 1
            assert screen.query_one("#doctor-detail", Static).content.plain == finding_detail_text(
                findings[2]
            )

            table.move_cursor(row=0, column=0, animate=False)
            await pilot.pause()
            await pilot.press("tab")
            detail_scroll = screen.query_one("#doctor-detail-scroll", VerticalScroll)
            assert app.focused is detail_scroll
            cursor_before = table.cursor_row
            await pilot.press("enter")
            assert table.cursor_row == cursor_before
            assert isinstance(app.screen, DoctorScreen)
            await pilot.press("j")
            await pilot.pause()
            assert table.cursor_row == cursor_before
            await pilot.press("shift+tab")
            await pilot.pause()
            assert app.focused is table

            await pilot.press("J")
            view = screen.query_one("#doctor-json", JsonView)
            assert view.document is not None
            assert findings[0].message in view.document
            assert findings[0].path in view.document
            assert "healthy" not in view.document
            document_value = json.loads(view.document)
            assert set(document_value) == {"home", "cwd", "findings"}
            assert set(document_value["findings"][0]) == {
                "code",
                "severity",
                "message",
                "rule_id",
                "evidence",
                "path",
                "detail",
            }
            assert screen.query_one("#doctor-body").display is False
            cursor_before = table.cursor_row
            await pilot.press("down")
            await pilot.press("enter")
            assert table.cursor_row == cursor_before
            assert isinstance(app.screen, DoctorScreen)
            await pilot.press("escape")
            assert not screen.json_mode
            await pilot.press("escape")
            await pilot.press("q")

    asyncio.run(_run((100, 30)))
    asyncio.run(_run((60, 24)))


def test_home_h_binding_filter_json_empty_and_plain_back(mock_home: Path) -> None:
    """Home opens Doctor only from its table and ordinary Back preserves filters."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home = app.screen
            assert isinstance(home, HomeScreen)
            await pilot.press("slash")
            await pilot.press("h")
            await pilot.pause()
            assert app.screen is home
            query = home.query_one("#filter-input", Input)
            assert query.value == "h"
            await pilot.press("escape")
            await pilot.press("a")
            await pilot.press("a")
            await pilot.pause()
            table = home.query_one("#skill-table", DataTable)
            if table.row_count > 1:
                await pilot.press("down")
            selected = app.controller.selected_key
            status = str(home.query_one("#status-text", Static).content)
            agent_id = home._agent_id
            await pilot.press("slash")
            await pilot.press(*"deploy")
            await pilot.press("enter")
            await pilot.press("h")
            screen = app.screen
            assert isinstance(screen, DoctorScreen)
            assert app.focused is screen.query_one("#doctor-findings", DataTable)
            await pilot.press("escape")
            assert app.screen is home
            assert query.value == "deploy"
            assert home._agent_id == agent_id
            assert app.controller.selected_key == selected
            assert str(home.query_one("#status-text", Static).content) == status
            assert home.query_one("#skill-table", DataTable).has_focus

            await pilot.press("J")
            assert home.json_mode
            await pilot.press("h")
            assert app.screen is home and home.json_mode
            await pilot.press("J")
            await pilot.press("q")

    asyncio.run(_run())


def test_doctor_can_open_before_initial_capture_and_never_fabricates_health(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A delayed first capture leaves Doctor honest and then publishes in place."""
    started = threading.Event()
    release = threading.Event()
    original_capture = app_module.capture_session

    def delayed_capture(**kwargs: Any) -> Any:
        started.set()
        if not release.wait(timeout=4):
            raise AssertionError("initial capture was not released")
        return original_capture(**kwargs)

    monkeypatch.setattr(app_module, "capture_session", delayed_capture)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_until(pilot, started.is_set, "blocked initial capture")
            await pilot.press("h")
            screen = app.screen
            assert isinstance(screen, DoctorScreen)
            assert app.controller.current is None
            assert "Scanning skills" in screen.query_one("#doctor-summary", Static).content.plain
            await pilot.press("J")
            view = screen.query_one("#doctor-json", JsonView)
            assert view.document is None
            assert "Scanning skills" in view.displayed_text
            release.set()
            await _wait_until(
                pilot,
                lambda: app.controller.current is not None and view.document is not None,
                "first Doctor report publication",
            )
            assert view.document == json.dumps(
                app.controller.current.doctor.to_dict(), sort_keys=True, indent=2
            )
            await pilot.press("q")

    try:
        asyncio.run(_run())
    finally:
        release.set()


def test_doctor_first_visit_stays_frozen_after_synthetic_tree_changes(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Doctor and matching use the publication even after files change or vanish."""
    target = mock_home / ".claude" / "skills" / "frozen"
    make_skill(target, "frozen", "Before capture.")
    original_capture = app_module.capture_session

    def captured(**kwargs: Any) -> Any:
        snapshot = original_capture(**kwargs)
        entry = next(item for item in snapshot.index.entries if item.name == "frozen")
        finding = _finding("captured_path", path=entry.entrypoint_path, message="frozen message")
        return replace(
            snapshot,
            doctor=DoctorReport(snapshot.doctor.home, snapshot.doctor.cwd, (finding,)),
        )

    monkeypatch.setattr(app_module, "capture_session", captured)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home = app.screen
            assert isinstance(home, HomeScreen)
            await pilot.press("a")
            await pilot.press("slash")
            await pilot.press(*"no-match")
            await pilot.press("enter")
            assert home._agent_id is not None
            assert home.query_one("#skill-table", DataTable).row_count == 0
            snapshot = app.controller.current
            assert snapshot is not None
            entry = next(item for item in snapshot.index.entries if item.name == "frozen")
            key = canonical_key(entry)
            (target / "SKILL.md").write_text("Changed after capture.", encoding="utf-8")
            for child in target.iterdir():
                child.unlink()
            target.rmdir()
            make_skill(mock_home / ".claude" / "skills" / "new", "new", "Added later.")
            monkeypatch.setattr(
                "skill_lens.core.snapshot.live_discovery",
                lambda *a, **kw: (_ for _ in ()).throw(AssertionError("live discovery ran")),
            )
            monkeypatch.setattr(
                "skill_lens.core.snapshot.run_doctor",
                lambda *a, **kw: (_ for _ in ()).throw(AssertionError("doctor recomputed")),
            )
            await pilot.press("h")
            screen = app.screen
            assert isinstance(screen, DoctorScreen)
            assert app.controller.current is snapshot
            assert screen.selected_finding is not None
            assert screen.selected_finding.message == "frozen message"
            assert screen.selected_finding.path == entry.entrypoint_path
            assert finding_catalog_keys(snapshot, screen.selected_finding) == (key,)
            await pilot.press("enter")
            await _wait_until(
                pilot, lambda: isinstance(app.screen, HomeScreen), "frozen catalog jump"
            )
            assert app.controller.current is snapshot
            assert app.controller.selected_key == key
            home = app.screen
            assert isinstance(home, HomeScreen)
            assert key in {row.key for row in home._rows}
            assert all(row.name != "new" for row in home._rows)
            assert home.query_one("#filter-input", Input).value == ""
            assert home._agent_id is None
            await pilot.press("q")

    asyncio.run(_run())


def test_ambiguous_display_mapping_stays_in_doctor_without_selecting(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two raw paths with one captured display string never select the first."""
    make_skill(mock_home / ".claude" / "skills" / "one", "one", "One.")
    make_skill(mock_home / ".claude" / "skills" / "two", "two", "Two.")
    original_capture = app_module.capture_session
    collision = "~/synthetic/shared-display"

    def captured(**kwargs: Any) -> Any:
        snapshot = original_capture(**kwargs)
        entries = tuple(snapshot.index.entries)
        paths = {entries[0].entrypoint_path: collision, entries[1].entrypoint_path: collision}
        display_paths = dict(snapshot.display_paths)
        display_paths.update(paths)
        finding = _finding("ambiguous", path=collision)
        report = DoctorReport(snapshot.doctor.home, snapshot.doctor.cwd, (finding,))
        return replace(
            snapshot,
            display_paths=MappingProxyType(display_paths),
            doctor=report,
        )

    monkeypatch.setattr(app_module, "capture_session", captured)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            initial_selection = app.controller.selected_key
            await pilot.press("h")
            screen = app.screen
            assert isinstance(screen, DoctorScreen)
            await pilot.press("enter")
            assert app.screen is screen
            assert screen.navigation_notice == (
                "This path matches more than one catalog entry; no skill was selected. "
                f"Path: {collision}"
            )
            assert app.controller.selected_key == initial_selection
            assert not app.controller.is_failed
            await pilot.press("q")

    asyncio.run(_run())


def test_doctor_keeps_published_report_on_refusal_and_sticky_fault_recovery(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed refresh preserves the report; explicit recovery keeps exit 3 sticky."""
    make_skill(mock_home / ".claude" / "skills" / "target", "target", "Target skill.")
    original_capture = app_module.capture_session
    calls: list[int] = []

    def controlled_capture(**kwargs: Any) -> Any:
        calls.append(int(kwargs["generation"]))
        if len(calls) == 2:
            raise RuntimeError("captured Doctor refresh fault")
        return original_capture(**kwargs)

    monkeypatch.setattr(app_module, "capture_session", controlled_capture)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            published = app.controller.current
            assert published is not None
            await pilot.press("h")
            screen = app.screen
            assert isinstance(screen, DoctorScreen)
            await pilot.press("J")
            view = screen.query_one("#doctor-json", JsonView)
            published_document = view.document
            assert published_document is not None

            await pilot.press("r")
            await _wait_until(
                pilot,
                lambda: app.controller.status == "error",
                "accepted Doctor refresh fault",
            )
            assert len(calls) == 2, "an accepted fault must not trigger an automatic retry"
            assert app.controller.current is published
            assert view.document == published_document
            assert screen.query_one("#doctor-status", Static).content.plain.startswith("Error:")
            assert (
                "captured Doctor refresh fault"
                in screen.query_one("#doctor-error-details", Static).content.plain
            )
            assert app.controller.is_failed

            await pilot.press("r")
            await _wait_until(
                pilot,
                lambda: (
                    app.controller.current is not None
                    and app.controller.current.generation == 3
                    and app.controller.pending_generation is None
                ),
                "explicit Doctor refresh recovery",
            )
            assert len(calls) == 3
            assert app.controller.is_failed
            assert app.controller.status == "error"
            assert screen.json_mode and view.document is not None
            await pilot.press("q")
            assert app.return_code == 3

    asyncio.run(_run())


def test_doctor_refresh_preserves_duplicate_occurrence_and_replaces_raw_document(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refresh preserves a full finding occurrence and replaces stale JSON atomically."""
    make_skill(mock_home / ".claude" / "skills" / "target", "target", "Target skill.")
    duplicate = _finding("duplicate", severity=Severity.WARNING, path=None)
    reports = {
        1: DoctorReport("/home", "/cwd", (_finding("before", path=None), duplicate, duplicate)),
        2: DoctorReport("/home", "/cwd", (_finding("first_new", path=None), duplicate, duplicate)),
        3: DoctorReport("/home", "/cwd", (_finding("replacement", path=None),)),
    }
    original_capture = app_module.capture_session

    def captured(**kwargs: Any) -> Any:
        snapshot = original_capture(**kwargs)
        return replace(snapshot, doctor=reports[snapshot.generation])

    monkeypatch.setattr(app_module, "capture_session", captured)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("h")
            screen = app.screen
            assert isinstance(screen, DoctorScreen)
            table = screen.query_one("#doctor-findings", DataTable)
            table.move_cursor(row=2, column=0, animate=False)
            await pilot.pause()
            assert screen.selected_identity is not None
            assert (screen.selected_identity.finding, screen.selected_identity.occurrence) == (
                duplicate,
                1,
            )

            await pilot.press("r")
            await _wait_until(
                pilot,
                lambda: (
                    app.controller.current is not None
                    and app.controller.current.generation == 2
                    and screen._generation == 2
                ),
                "ordinary Doctor refresh",
            )
            assert screen.selected_identity is not None
            assert (screen.selected_identity.finding, screen.selected_identity.occurrence) == (
                duplicate,
                1,
            )
            home_selection = app.controller.selected_key
            assert not app.jump_from_doctor(screen, 1, "/stale/key")
            assert app.screen is screen
            assert app.controller.selected_key == home_selection
            assert "report changed" in screen.navigation_notice

            await pilot.press("J")
            view = screen.query_one("#doctor-json", JsonView)
            expected_second = json.dumps(reports[2].to_dict(), sort_keys=True, indent=2)
            assert view.document == expected_second
            await pilot.press("r")
            await _wait_until(
                pilot,
                lambda: (
                    app.controller.current is not None
                    and app.controller.current.generation == 3
                    and view.document == json.dumps(reports[3].to_dict(), sort_keys=True, indent=2)
                ),
                "raw Doctor refresh",
            )
            assert screen.json_mode
            assert screen.query_one("#doctor-findings", DataTable).row_count == 1
            assert screen.selected_finding == reports[3].findings[0]
            await pilot.press("escape")
            await pilot.press("q")

    asyncio.run(_run())


def test_doctor_entry_suspends_home_why_and_old_completion_keeps_new_owner(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Home stops driving Why while covered; an old result cannot clear a new token."""
    make_skill(mock_home / ".claude" / "skills" / "one", "one", "One skill.")
    symlink(mock_home / ".claude" / "skills" / "one", mock_home / ".codex" / "skills" / "one")
    original_why = app_module.snapshot_why
    first_started = threading.Event()
    first_release = threading.Event()
    second_started = threading.Event()
    second_release = threading.Event()
    first_completion_handled = threading.Event()
    first_request_id: int | None = None
    call_lock = threading.Lock()
    call_count = 0

    def controlled_why(snapshot: Any, key: str, agent_id: str) -> Any:
        nonlocal call_count
        with call_lock:
            call_count += 1
            number = call_count
        if number == 1:
            first_started.set()
            if not first_release.wait(timeout=5):
                raise AssertionError("first Why call was not released")
        elif number == 2:
            second_started.set()
            if not second_release.wait(timeout=5):
                raise AssertionError("second Why call was not released")
        return original_why(snapshot, key, agent_id)

    monkeypatch.setattr(app_module, "snapshot_why", controlled_why)
    original_complete = app_module.SkillLensApp.on_view_report_complete

    def observe_completion(app: SkillLensApp, message: Any) -> None:
        original_complete(app, message)
        if first_request_id == message.request_id:
            first_completion_handled.set()

    monkeypatch.setattr(app_module.SkillLensApp, "on_view_report_complete", observe_completion)

    async def _run() -> None:
        nonlocal first_request_id
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            home = app.screen
            assert isinstance(home, HomeScreen)
            requests: list[tuple[str, tuple[str, ...]]] = []
            original_request_report = app.request_report

            def track_request(view: str, arguments: tuple[str, ...]) -> Any:
                requests.append((view, arguments))
                return original_request_report(view, arguments)

            monkeypatch.setattr(app, "request_report", track_request)
            await pilot.press("a")
            await _wait_until(pilot, first_started.is_set, "first owned Why worker")
            first_request = app.controller.active_requests.get("why")
            assert first_request is not None
            first_request_id = first_request.request_id
            assert len(requests) == 1

            await pilot.press("h")
            assert isinstance(app.screen, DoctorScreen)
            assert app.controller.active_requests.get("why") is None
            assert home._suspended
            await pilot.pause(0.05)
            assert len(requests) == 1, "Doctor browsing must not dispatch any report request"

            await pilot.press("escape")
            assert app.screen is home
            await _wait_until(pilot, second_started.is_set, "new owned Why worker")
            second_request = app.controller.active_requests.get("why")
            assert second_request is not None and second_request != first_request
            assert home._inflight is not None and home._inflight.request == second_request

            first_release.set()
            await _wait_until(pilot, first_completion_handled.is_set, "stale first result handoff")
            assert app.controller.active_requests.get("why") == second_request
            assert home._inflight is not None and home._inflight.request == second_request
            second_release.set()
            await _wait_until(
                pilot,
                lambda: app.controller.active_requests.get("why") is None,
                "new Why worker completion",
            )
            await pilot.press("q")

    try:
        asyncio.run(_run())
    finally:
        first_release.set()
        second_release.set()


def test_stale_generation_with_valid_catalog_key_does_not_jump(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An older Doctor event cannot navigate even when its key still exists."""
    make_skill(mock_home / ".agents" / "skills" / "target", "same-name", "Target.")
    symlink(
        mock_home / ".agents" / "skills" / "target",
        mock_home / ".claude" / "skills" / "alias",
    )
    make_skill(mock_home / ".codex" / "skills" / "other", "other", "Other.")
    base = capture_session(generation=1, home=paths.home(), cwd=mock_home)
    report = DoctorReport(
        home=str(mock_home),
        cwd=str(mock_home),
        findings=(_finding("stale_alias", path="~/.claude/skills/alias"),),
    )
    base = replace(base, doctor=report)
    key = next(
        canonical_key(entry)
        for entry in base.index.entries
        if entry.canonical_path == str(mock_home / ".agents" / "skills" / "target")
    )
    monkeypatch.setattr(
        app_module,
        "capture_session",
        lambda **kwargs: replace(base, generation=kwargs["generation"]),
    )

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            home = app.screen
            assert isinstance(home, HomeScreen)
            await pilot.press("slash")
            home.query_one("#filter-input", Input).value = "other"
            await pilot.pause()
            await pilot.press("enter", "h", "r")
            await _wait_until(
                pilot,
                lambda: (
                    app.controller.current is not None and app.controller.current.generation == 2
                ),
                "second captured generation",
            )
            screen = app.screen
            assert isinstance(screen, DoctorScreen)
            assert screen.selected_finding == report.findings[0]
            selected_before = app.controller.selected_key
            assert not app.jump_from_doctor(screen, 1, key)
            assert app.screen is screen
            assert app.controller.selected_key == selected_before
            assert home.query_one("#filter-input", Input).value == "other"
            assert "report changed" in screen.navigation_notice
            await pilot.press("q")

    asyncio.run(_run())


def test_doctor_detail_and_json_scroll_survive_refresh_then_reset_on_removal(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same-finding refresh preserves both scroll positions; removal resets them."""
    make_skill(mock_home / ".claude" / "skills" / "target", "target", "Target.")
    long_finding = _finding(
        "long_finding",
        path=None,
        message="Long finding",
        detail="[literal]\n" + "scrollable detail line\n" * 90,
    )
    other_finding = _finding("replacement", path=None, message="Replacement")
    initial = DoctorReport(str(mock_home), str(mock_home), (long_finding, other_finding))
    entered = threading.Event()
    release = threading.Event()
    original_capture = app_module.capture_session

    def captured(**kwargs: Any) -> Any:
        generation = int(kwargs["generation"])
        if generation == 4:
            entered.set()
            if not release.wait(timeout=8):
                raise AssertionError("held refresh was not released")
        snapshot = original_capture(**kwargs)
        report = initial if generation < 3 else replace(initial, findings=(other_finding,))
        return replace(snapshot, doctor=report)

    monkeypatch.setattr(app_module, "capture_session", captured)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(60, 24)) as pilot:
            try:
                await _wait_ready(pilot, app)
                await pilot.press("h", "tab", "end")
                await pilot.pause()
                screen = app.screen
                assert isinstance(screen, DoctorScreen)
                detail = screen.query_one("#doctor-detail-scroll", VerticalScroll)
                assert app.focused is detail
                detail_offset = detail.scroll_offset.y
                assert detail_offset > 0 and detail.max_scroll_y > 0

                app._update_ui()
                await pilot.pause()
                assert detail.scroll_offset.y == detail_offset

                await pilot.press("J", "end")
                await pilot.pause()
                view = screen.query_one("#doctor-json", JsonView)
                json_offset = view.scroll_offset.y
                assert json_offset > 0
                app._update_ui()
                await pilot.pause()
                assert view.scroll_offset.y == json_offset

                await pilot.press("escape")
                await pilot.pause()
                assert app.focused is detail
                assert detail.scroll_offset.y == detail_offset

                await pilot.press("r")
                await _wait_until(
                    pilot,
                    lambda: (
                        app.controller.current is not None
                        and app.controller.current.generation == 2
                    ),
                    "same-finding refresh",
                )
                await pilot.pause()
                assert screen.selected_finding == long_finding
                assert detail.scroll_offset.y == detail_offset

                await pilot.press("J", "end", "r")
                await _wait_until(
                    pilot,
                    lambda: (
                        app.controller.current is not None
                        and app.controller.current.generation == 3
                    ),
                    "selected finding removal refresh",
                )
                await pilot.pause()
                assert screen.selected_finding == other_finding
                assert view.scroll_offset.y == 0
                await pilot.press("backspace")
                await pilot.pause()
                assert detail.scroll_offset.y == 0

                await pilot.press("r")
                await _wait_until(pilot, entered.is_set, "held refresh before quit")
                await pilot.press("q")
                assert app.controller.closed
            finally:
                release.set()

    asyncio.run(_run())


def test_empty_doctor_report_is_healthy_without_selection_or_jump(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty captured report is healthy, has no jump target, and keeps exact JSON."""
    original_capture = app_module.capture_session

    def captured(**kwargs: Any) -> Any:
        snapshot = original_capture(**kwargs)
        report = DoctorReport(snapshot.doctor.home, snapshot.doctor.cwd, ())
        return replace(snapshot, doctor=report)

    monkeypatch.setattr(app_module, "capture_session", captured)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("h")
            screen = app.screen
            assert isinstance(screen, DoctorScreen)
            assert app.focused is screen.query_one("#doctor-findings", DataTable)
            assert screen.query_one("#doctor-findings", DataTable).row_count == 0
            assert screen.selected_finding is None
            assert screen.query_one("#doctor-summary", Static).content.plain == (
                "Skill folders look healthy."
            )
            assert screen.query_one("#doctor-detail", Static).content.plain == (
                "No finding selected."
            )
            await pilot.press("enter")
            assert app.screen is screen
            assert screen.navigation_notice == ""
            snapshot = app.controller.current
            assert snapshot is not None
            await pilot.press("J")
            view = screen.query_one("#doctor-json", JsonView)
            assert view.document == dumps(snapshot.doctor.to_dict())
            assert json.loads(view.document or "null")["findings"] == []
            await pilot.press("escape", "q")

    asyncio.run(_run())
