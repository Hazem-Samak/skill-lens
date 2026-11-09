"""Headless U6 Compare tests for picker behavior, frozen data, and request ownership."""

from __future__ import annotations

import asyncio
import builtins
import json
import os
import threading
import time
from dataclasses import replace
from pathlib import Path
from stat import S_IMODE
from typing import Any, Literal

import pytest
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Static
from typer.testing import CliRunner

import skill_lens.tui.app as app_module
from skill_lens.cli import app as cli_app
from skill_lens.core import compare as compare_engine
from skill_lens.core import discovery, system
from skill_lens.core import snapshot as snapshot_service
from skill_lens.core.compare import validate_compare_agents
from skill_lens.core.snapshot import SnapshotTooLarge
from skill_lens.core.snapshot_models import FrozenDiscoveryIndex
from skill_lens.models import CompareRelation
from skill_lens.presentation import RELATION_LABEL
from skill_lens.tui.agents import AgentsScreen
from skill_lens.tui.app import SkillLensApp
from skill_lens.tui.compare import CompareScreen, _fit_cell
from skill_lens.tui.home import HomeScreen
from skill_lens.tui.json_view import JsonView
from tests.fixtures.builders import make_skill, symlink

runner = CliRunner()


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
        lambda: app.controller.current is not None and app.controller.pending_generation is None,
        "published initial session",
    )
    await pilot.pause()


async def _wait_compare(pilot: Any, app: SkillLensApp) -> CompareScreen:
    await _wait_until(
        pilot,
        lambda: (
            isinstance(app.screen, CompareScreen)
            and app.screen.report is not None
            and app.screen._report_state == "ready"
        ),
        "accepted comparison report",
    )
    await pilot.pause()
    screen = app.screen
    assert isinstance(screen, CompareScreen)
    return screen


def _row_ids(table: DataTable) -> list[str]:
    return [
        str(table.coordinate_to_cell_key((index, 1)).row_key.value)
        for index in range(table.row_count)
    ]


async def _highlight_id(pilot: Any, table: DataTable, agent_id: str) -> None:
    target = _row_ids(table).index(agent_id)
    table.focus()
    for _ in range(table.row_count + 1):
        if table.cursor_row == target:
            break
        await pilot.press("down" if table.cursor_row < target else "up")
    await pilot.pause(0.02)
    assert table.cursor_row == target


def _build_pair_fixture(home: Path, *, many: int = 0) -> Path:
    """Build shared, identical, diverged, and one-sided Claude/Codex skills."""
    project = home / "project"
    (project / ".git").mkdir(parents=True, exist_ok=True)
    shared = home / ".agents" / "skills" / "shared-link-target"
    make_skill(shared, "shared-link", "One canonical copy reached through a link.")
    symlink(shared, home / ".claude" / "skills" / "shared-link")

    make_skill(
        home / ".claude" / "skills" / "identical",
        "identical",
        "Independent copies with equal content.",
        body="# Instructions\n\nSame bytes.\n",
    )
    make_skill(
        home / ".agents" / "skills" / "identical",
        "identical",
        "Independent copies with equal content.",
        body="# Instructions\n\nSame bytes.\n",
    )
    make_skill(
        home / ".claude" / "skills" / "diverged",
        "diverged",
        "Claude version.",
        body="# Instructions\n\nClaude body.\n",
    )
    make_skill(
        home / ".agents" / "skills" / "diverged",
        "diverged",
        "Codex version.",
        body="# Instructions\n\nCodex body.\n",
    )
    make_skill(home / ".claude" / "skills" / "only-a", "only-a", "Claude only.")
    make_skill(home / ".agents" / "skills" / "only-b", "only-b", "Codex only.")
    for index in range(many):
        make_skill(
            home / ".claude" / "skills" / f"long-{index:02d}",
            f"long-{index:02d}",
            f"Long note {index}.",
        )
        make_skill(
            home / ".agents" / "skills" / f"long-{index:02d}",
            f"long-{index:02d}",
            f"Long note {index}.",
        )
    return project


def _cli_compare(home: Path, project: Path, agent_a: str = "claude", agent_b: str = "codex") -> str:
    result = runner.invoke(
        cli_app,
        [
            "compare",
            "--agent",
            agent_a,
            "--agent",
            agent_b,
            "--sandbox",
            str(home),
            "--cwd",
            str(project),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.stdout
    return result.stdout


async def _select_pair_by_keys(
    pilot: Any,
    screen: CompareScreen,
    agent_a: str,
    agent_b: str,
    *,
    submit_b: bool = True,
) -> None:
    table_a = screen.query_one("#compare-a-table", DataTable)
    await _highlight_id(pilot, table_a, agent_a)
    await pilot.press("enter")
    await pilot.pause(0.02)
    assert screen._selected_a == agent_a
    assert app_focused_id(screen) == "compare-b-table"
    table_b = screen.query_one("#compare-b-table", DataTable)
    await _highlight_id(pilot, table_b, agent_b)
    if submit_b:
        await pilot.press("enter")
        await pilot.pause(0.02)


def app_focused_id(screen: CompareScreen) -> str | None:
    focused = screen.app.focused
    return focused.id if focused is not None else None


@pytest.mark.parametrize(
    ("text", "width", "expected"),
    [
        ("short", 10, "short"),
        ("abcdefghij", 7, "abc…hij"),
        ("abcdefghij", 1, "…"),
        ("abcdefghij", 0, ""),
    ],
)
def test_compare_fit_cell_middle_truncates_to_the_column(
    text: str, width: int, expected: str
) -> None:
    """A truncated cell keeps both ends and never exceeds its column."""
    assert _fit_cell(text, width) == expected


def test_compare_all_registry_agents_keyboard_picker_and_exact_cli_json(mock_home: Path) -> None:
    """Two known, undetected agents can be compared; screen JSON matches CLI bytes."""
    project = mock_home
    cli_ab = _cli_compare(mock_home, project)
    cli_ba = _cli_compare(mock_home, project, "codex", "claude")
    assert cli_ab.endswith("\n") and cli_ba.endswith("\n")
    assert json.loads(cli_ab)["entries"] == []
    assert json.loads(cli_ba)["agent_a"] == "codex"

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            assert app.controller.current is not None
            assert app.controller.current.scan.summary.detected_agents == ()
            await pilot.press("c")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, CompareScreen)
            registry_ids = sorted(agent.id for agent in app.controller.current.registry)
            assert _row_ids(screen.query_one("#compare-a-table", DataTable)) == registry_ids
            assert _row_ids(screen.query_one("#compare-b-table", DataTable)) == registry_ids
            assert screen.selected_pair is None
            table_a = screen.query_one("#compare-a-table", DataTable)
            table_a.focus()
            first_row = table_a.cursor_row
            await pilot.press("j")
            assert table_a.cursor_row == first_row + 1
            await pilot.press("k")
            assert table_a.cursor_row == first_row

            await _select_pair_by_keys(pilot, screen, "claude", "codex")
            screen = await _wait_compare(pilot, app)
            assert screen.report is not None
            assert screen.report.agent_a == "claude"
            assert screen.report.agent_b == "codex"
            assert "Neither agent has any skills installed." in "\n".join(
                str(item.content)
                for item in screen.query_one("#compare-result", Vertical).query(Static)
            )
            await pilot.press("J")
            await pilot.pause()
            view = screen.query_one("#compare-json", JsonView)
            assert screen.json_mode
            assert view.document == cli_ab.rstrip("\n")
            assert view.document + "\n" == cli_ab
            assert json.loads(view.document)["agent_a"] == "claude"
            request_id = app.controller.next_request_id

            await pilot.press("escape")
            await pilot.pause()
            assert screen.mode == "result" and not screen.json_mode
            await pilot.press("escape")
            await pilot.pause()
            assert screen.mode == "picker"
            assert screen.selected_pair == ("claude", "codex")
            assert app_focused_id(screen) == "compare-b-table"
            await pilot.press("tab", "enter")
            await pilot.pause()
            assert screen.mode == "result"
            assert screen.report is not None
            assert app.controller.next_request_id == request_id

            # A/B order is part of cache identity and the canonical JSON.
            await pilot.press("escape")
            await pilot.pause()
            screen.query_one("#compare-a-table", DataTable).focus()
            await _highlight_id(pilot, screen.query_one("#compare-a-table", DataTable), "codex")
            await pilot.press("enter")
            await pilot.pause()
            await _highlight_id(pilot, screen.query_one("#compare-b-table", DataTable), "claude")
            await pilot.press("enter")
            screen = await _wait_compare(pilot, app)
            assert screen.report is not None and (screen.report.agent_a, screen.report.agent_b) == (
                "codex",
                "claude",
            )
            await pilot.press("J")
            assert screen.query_one("#compare-json", JsonView).document == cli_ba.rstrip("\n")
            await pilot.press("q")

    asyncio.run(_run())


def test_compare_report_uses_engine_relations_paths_counts_and_literal_notes(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Widgets show model classifications and paths without inferring from appearance."""
    project = _build_pair_fixture(mock_home)
    oracle = _cli_compare(mock_home, project)
    original_compare = app_module.snapshot_compare

    def compare_with_literal_note(snapshot: Any, agent_a: str, agent_b: str) -> Any:
        report = original_compare(snapshot, agent_a, agent_b)
        return replace(report, notes=("Diagnostic [red]literal[/red] note.",))

    monkeypatch.setattr(app_module, "snapshot_compare", compare_with_literal_note)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("c")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, CompareScreen)
            await _select_pair_by_keys(pilot, screen, "claude", "codex")
            screen = await _wait_compare(pilot, app)
            report = screen.report
            assert report is not None
            assert {entry.relation for entry in report.entries} == {
                CompareRelation.SHARED,
                CompareRelation.DIVERGED,
                CompareRelation.ONLY_A,
                CompareRelation.ONLY_B,
            }
            actual_counts = report.counts_by_relation()
            statics = "\n".join(
                str(item.content)
                for item in screen.query_one("#compare-result", Vertical).query(Static)
            )
            for relation in (
                CompareRelation.SHARED,
                CompareRelation.DIVERGED,
                CompareRelation.ONLY_A,
                CompareRelation.ONLY_B,
            ):
                assert actual_counts[relation.value] > 0

            table = screen.query_one("#compare-table", DataTable)
            assert [str(column.label) for column in table.columns.values()] == [
                "Skill",
                "Relation",
                "Path A",
                "Path B",
            ]
            assert table.row_count == len(report.entries)
            assert table.virtual_size.width <= table.size.width
            assert table.virtual_size.height == table.row_count + 1
            assert table.size.height == table.row_count + 1
            for column in table.columns.values():
                assert column.width >= len(str(column.label))
            rendered_relations: set[str] = set()
            for index, entry in enumerate(report.entries):
                expected_label, _style = RELATION_LABEL[entry.relation]
                expected_a = (
                    app.controller.current.display_paths.get(entry.path_a, entry.path_a)
                    if entry.path_a
                    else "-"
                )
                expected_b = (
                    app.controller.current.display_paths.get(entry.path_b, entry.path_b)
                    if entry.path_b
                    else "-"
                )
                row = [str(cell) for cell in table.get_row_at(index)]
                assert row == [entry.name, expected_label, expected_a, expected_b]
                rendered_relations.add(row[1])
            assert rendered_relations == {"shared", "diverged", "A only", "B only"}
            assert "Diagnostic [red]literal[/red] note." in statics
            assert "Diagnostic literal note." not in statics
            assert "shared-link" in oracle
            await pilot.press("q")

    asyncio.run(_run())


def test_compare_input_errors_are_inline_and_dispatch_no_worker(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing, duplicate and stale unknown IDs keep the normal exit status."""
    report_calls: list[tuple[str, tuple[str, ...]]] = []
    original_request_report = SkillLensApp.request_report

    def record_request_report(
        self: SkillLensApp,
        view: Literal["why", "diff", "compare"],
        arguments: tuple[str, ...],
    ) -> Any:
        report_calls.append((view, arguments))
        return original_request_report(self, view, arguments)

    monkeypatch.setattr(SkillLensApp, "request_report", record_request_report)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("c")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, CompareScreen)
            request_id_before = app.controller.next_request_id
            cache_before = dict(app.controller.cache)

            def assert_no_report_dispatch() -> None:
                assert report_calls == []
                assert app.controller.next_request_id == request_id_before
                assert dict(app.controller.cache) == cache_before
                assert app.controller.active_requests.get("compare") is None
                assert screen.mode == "picker"
                assert screen.report is None

            # Missing A remains a picker error and cannot allocate a request.
            await pilot.press("tab", "tab", "enter")
            await pilot.pause()
            assert "Choose an agent for A." in str(
                screen.query_one("#compare-input-error", Static).content
            )
            assert_no_report_dispatch()

            # A selected A with no B is equally blocked before request allocation.
            screen._selected_a = "claude"
            screen._selected_b = None
            screen._submit_selected()
            assert "Choose an agent for B." in str(
                screen.query_one("#compare-input-error", Static).content
            )
            assert_no_report_dispatch()

            # Pick the same known row on both sides.
            table_a = screen.query_one("#compare-a-table", DataTable)
            await _highlight_id(pilot, table_a, "claude")
            await pilot.press("enter")
            await pilot.pause()
            table_b = screen.query_one("#compare-b-table", DataTable)
            await _highlight_id(pilot, table_b, "claude")
            await pilot.press("enter")
            await pilot.pause()
            assert "Pick two different agents." in str(
                screen.query_one("#compare-input-error", Static).content
            )
            assert_no_report_dispatch()
            assert not app.controller.failed

            # A queued event from a previous registry is represented by a stale
            # confirmed id. Validation uses the current captured map and CLI wording.
            screen._selected_a = "unknown-u6-agent"
            screen._selected_b = "codex"
            screen.query_one("#compare-submit", Button).focus()
            await pilot.press("enter")
            await pilot.pause()
            with pytest.raises(KeyError) as validation_error:
                validate_compare_agents(
                    "unknown-u6-agent",
                    "codex",
                    {a.id: a for a in app.controller.current.registry},
                )
            error = str(validation_error.value.args[0])
            assert str(screen.query_one("#compare-input-error", Static).content) == error
            assert "Known agents:" in error
            assert_no_report_dispatch()
            assert not app.controller.failed
            await pilot.press("q")
            assert app.return_code == 0

    asyncio.run(_run())


@pytest.mark.parametrize("registry_count", [0, 1])
def test_compare_shortfall_counts_registry_definitions_not_detections(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch, registry_count: int
) -> None:
    """A known registry shortfall blocks submit; zero detected agents do not."""
    original_capture = app_module.capture_session

    def capture_small_registry(**kwargs: Any) -> Any:
        snapshot = original_capture(**kwargs)
        registry = tuple(sorted(snapshot.registry, key=lambda item: item.id)[:registry_count])
        return replace(snapshot, registry=registry)

    monkeypatch.setattr(app_module, "capture_session", capture_small_registry)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(60, 24)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("c")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, CompareScreen)
            assert screen.query_one("#compare-a-table", DataTable).row_count == registry_count
            assert screen.query_one("#compare-b-table", DataTable).row_count == registry_count
            note = str(screen.query_one("#compare-registry-message", Static).content)
            if registry_count == 0:
                assert "No known agent definitions are available: none." in note
            else:
                assert "Only one known agent definition is available:" in note
            assert f"Need {2 - registry_count} more" in note
            assert screen.query_one("#compare-submit", Button).disabled
            await pilot.press("q")

    asyncio.run(_run())


def test_compare_empty_skill_home_still_offers_all_registry_choices(mock_home: Path) -> None:
    """A large known registry remains eligible even when no agent is detected."""

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            assert app.controller.current is not None
            assert app.controller.current.scan.summary.detected_agents == ()
            await pilot.press("c")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, CompareScreen)
            assert screen.query_one("#compare-a-table", DataTable).row_count == 10
            assert not screen.query_one("#compare-submit", Button).disabled
            assert "Only 0 known" not in str(
                screen.query_one("#compare-registry-message", Static).content
            )
            await pilot.press("q")

    asyncio.run(_run())


def test_compare_open_before_initial_capture_and_refusal_shows_real_session_state(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No snapshot is never presented as a captured empty registry or report."""
    started = threading.Event()
    release = threading.Event()

    def blocked_refusal(**kwargs: Any) -> Any:
        started.set()
        if not release.wait(timeout=3):
            raise AssertionError("refusal test release timed out")
        raise SnapshotTooLarge(total_bytes=99, limit_bytes=1)

    monkeypatch.setattr(app_module, "capture_session", blocked_refusal)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home, max_snapshot_bytes=1)
        async with app.run_test() as pilot:
            await _wait_until(pilot, started.is_set, "blocked first capture")
            await pilot.press("c")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, CompareScreen)
            assert app.controller.current is None
            assert screen.query_one("#compare-a-table", DataTable).row_count == 0
            assert screen.query_one("#compare-registry-message", Static).content.plain == ""
            assert "Scanning skills" in str(screen.query_one("#compare-status", Static).content)
            assert screen.query_one("#compare-submit", Button).disabled
            screen._submit_selected()
            assert "Scanning skills" in str(
                screen.query_one("#compare-input-error", Static).content
            )
            assert app.controller.active_requests.get("compare") is None
            release.set()
            await _wait_until(pilot, lambda: app.controller.status == "refused", "initial refusal")
            await pilot.pause()
            assert "Snapshot refused" in str(screen.query_one("#compare-status", Static).content)
            assert screen.report is None
            screen._submit_selected()
            assert "Snapshot refused" in str(
                screen.query_one("#compare-input-error", Static).content
            )
            assert app.controller.active_requests.get("compare") is None
            await pilot.press("J")
            assert not screen.json_mode  # JSON is inert in the picker.
            await pilot.press("q")
            assert app.return_code == 0

    try:
        asyncio.run(_run())
    finally:
        release.set()


def test_compare_button_submits_the_selected_ordered_pair(mock_home: Path) -> None:
    """The visible Compare button uses the same validated picker submission."""
    project = _build_pair_fixture(mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("c")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, CompareScreen)
            await _select_pair_by_keys(pilot, screen, "claude", "codex")
            screen = await _wait_compare(pilot, app)
            next_request_id = app.controller.next_request_id
            await pilot.press("escape")
            await pilot.pause()
            assert screen.mode == "picker"
            assert screen.selected_pair == ("claude", "codex")
            await pilot.click("#compare-submit")
            screen = await _wait_compare(pilot, app)
            assert screen.report is not None
            assert (screen.report.agent_a, screen.report.agent_b) == ("claude", "codex")
            assert app.controller.next_request_id == next_request_id
            assert screen.mode == "result"
            await pilot.press("q")

    asyncio.run(_run())


@pytest.mark.parametrize("raw", [False, True])
def test_compare_removed_agent_refresh_returns_to_visible_picker(
    mock_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw: bool,
) -> None:
    """A removed selected ID is cleared without substitution, including raw mode."""
    project = _build_pair_fixture(mock_home)
    original_capture = app_module.capture_session

    def capture_without_codex(**kwargs: Any) -> Any:
        snapshot = original_capture(**kwargs)
        if kwargs["generation"] > 1:
            return replace(
                snapshot,
                registry=tuple(agent for agent in snapshot.registry if agent.id != "codex"),
            )
        return snapshot

    monkeypatch.setattr(app_module, "capture_session", capture_without_codex)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("c")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, CompareScreen)
            await _select_pair_by_keys(pilot, screen, "claude", "codex")
            screen = await _wait_compare(pilot, app)
            if raw:
                await pilot.press("J")
                await pilot.pause()
                assert screen.json_mode
                assert screen.query_one("#compare-json", JsonView).document is not None
            await pilot.press("r")
            await _wait_until(
                pilot,
                lambda: (
                    app.controller.current is not None
                    and app.controller.current.generation == 2
                    and screen.mode == "picker"
                ),
                "new registry publication",
            )
            await pilot.pause()
            assert not screen.has_class("result-mode")
            assert screen.query_one("#compare-picker", Vertical).display
            assert not screen.json_mode
            assert screen.query_one("#compare-json", JsonView).document is None
            assert screen._selected_a == "claude"
            assert screen._selected_b is None
            assert "'codex' was removed during refresh" in str(
                screen.query_one("#compare-input-error", Static).content
            )
            assert app.controller.active_requests.get("compare") is None
            await pilot.press("q")

    asyncio.run(_run())


def test_compare_refresh_keeps_valid_raw_mode_and_clears_old_json_while_loading(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valid ordered pair stays in JSON mode while its new generation loads."""
    project = _build_pair_fixture(mock_home)
    original_capture = app_module.capture_session
    original_compare = app_module.snapshot_compare
    second_started = threading.Event()
    release_second = threading.Event()

    def capture_mutated(**kwargs: Any) -> Any:
        return original_capture(**kwargs)

    compare_calls = 0

    def controlled_compare(snapshot: Any, agent_a: str, agent_b: str) -> Any:
        nonlocal compare_calls
        compare_calls += 1
        if compare_calls == 2:
            second_started.set()
            if not release_second.wait(timeout=4):
                raise AssertionError("second comparison release timed out")
        return original_compare(snapshot, agent_a, agent_b)

    monkeypatch.setattr(app_module, "capture_session", capture_mutated)
    monkeypatch.setattr(app_module, "snapshot_compare", controlled_compare)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("c")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, CompareScreen)
            await _select_pair_by_keys(pilot, screen, "claude", "codex")
            screen = await _wait_compare(pilot, app)
            await pilot.press("J")
            await pilot.pause()
            first_doc = screen.query_one("#compare-json", JsonView).document
            assert first_doc is not None

            # Change the synthetic target only after the first report is accepted.
            (mock_home / ".agents" / "skills" / "identical" / "SKILL.md").write_text(
                "---\nname: identical\ndescription: Updated Codex copy.\n---\nUpdated.\n",
                encoding="utf-8",
            )
            await pilot.press("r")
            await _wait_until(pilot, second_started.is_set, "new-generation comparison worker")
            assert app.controller.current is not None and app.controller.current.generation == 2
            assert screen.mode == "result" and screen.json_mode
            assert screen.report is None
            view = screen.query_one("#compare-json", JsonView)
            assert view.document is None
            assert "Loading comparison" in view.displayed_text
            release_second.set()
            await _wait_until(pilot, lambda: screen.report is not None, "refreshed report")
            await pilot.pause()
            assert screen.json_mode
            new_doc = view.document
            assert new_doc is not None and new_doc != first_doc
            old_payload = json.loads(first_doc)
            new_payload = json.loads(new_doc)
            old_identical = next(
                item for item in old_payload["entries"] if item["name"] == "identical"
            )
            new_identical = next(
                item for item in new_payload["entries"] if item["name"] == "identical"
            )
            assert old_identical["relation"] == "shared"
            assert new_identical["relation"] == "diverged"
            await pilot.press("q")

    try:
        asyncio.run(_run())
    finally:
        release_second.set()


@pytest.mark.parametrize("stale_kind", ["success", "error"])
def test_compare_rejects_late_old_pair_completion_after_cached_pair_reopens(
    mock_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    stale_kind: Literal["success", "error"],
) -> None:
    """The ordered cache hit cancels another owned pair; its late outcome stays stale."""
    project = _build_pair_fixture(mock_home)
    original_compare = app_module.snapshot_compare
    slow_started = threading.Event()
    slow_finished = threading.Event()
    release_slow = threading.Event()
    stale_handoff = threading.Event()
    stale_request_id: list[int] = []
    call_lock = threading.Lock()
    call_count = 0
    original_complete = SkillLensApp.on_view_report_complete
    original_failed = SkillLensApp.on_view_report_failed

    def note_stale_complete(self: SkillLensApp, message: app_module.ViewReportComplete) -> None:
        original_complete(self, message)
        if stale_request_id and message.request_id == stale_request_id[0]:
            stale_handoff.set()

    def note_stale_failed(self: SkillLensApp, message: app_module.ViewReportFailed) -> None:
        original_failed(self, message)
        if stale_request_id and message.request_id == stale_request_id[0]:
            stale_handoff.set()

    monkeypatch.setattr(SkillLensApp, "on_view_report_complete", note_stale_complete)
    monkeypatch.setattr(SkillLensApp, "on_view_report_failed", note_stale_failed)

    def slow_second_pair(snapshot: Any, agent_a: str, agent_b: str) -> Any:
        nonlocal call_count
        with call_lock:
            call_count += 1
            current = call_count
        if current == 2:
            slow_started.set()
            if not release_slow.wait(timeout=4):
                raise AssertionError("stale comparison release timed out")
            try:
                if stale_kind == "error":
                    raise RuntimeError("late stale compare fault")
                return original_compare(snapshot, agent_a, agent_b)
            finally:
                slow_finished.set()
        return original_compare(snapshot, agent_a, agent_b)

    monkeypatch.setattr(app_module, "snapshot_compare", slow_second_pair)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("c")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, CompareScreen)
            await _select_pair_by_keys(pilot, screen, "claude", "codex")
            await _wait_compare(pilot, app)
            cached_report = screen.report
            assert cached_report is not None

            # Start a different ordered pair and keep its worker pending.
            await pilot.press("escape")
            await pilot.pause()
            screen._selected_a = "codex"
            screen._selected_b = "claude"
            screen._submit_selected()
            await _wait_until(pilot, slow_started.is_set, "second pair worker")
            slow_token = screen.owned_request
            assert slow_token is not None and slow_token.arguments == ("codex", "claude")
            stale_request_id.append(slow_token.request_id)

            # Reopen the cached (A, B) pair while (B, A) is still pending. The
            # old request's cancellation and late result/error cannot alter it.
            screen._submitted_pair = ("claude", "codex")
            screen._report_pair = ("codex", "claude")
            screen._mode = "result"
            screen._request_pair(("claude", "codex"))
            assert screen.report is cached_report
            assert screen.owned_request is None
            active = app.controller.active_requests.get("compare")
            assert active is None
            assert not app.controller.failed
            release_slow.set()
            await _wait_until(pilot, slow_finished.is_set, "stale worker completion")
            await _wait_until(pilot, stale_handoff.is_set, "stale UI message handoff")
            assert screen.report is cached_report
            assert not app.controller.failed
            assert app.controller.get_cached_report("compare", ("claude", "codex")) is cached_report
            assert app.controller.get_cached_report("compare", ("codex", "claude")) is None
            await pilot.press("q")

    try:
        asyncio.run(_run())
    finally:
        release_slow.set()


def test_compare_error_is_sticky_but_redraw_never_retries(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An accepted internal fault is shown once and repeated syncs do not redispatch."""
    project = _build_pair_fixture(mock_home)
    calls = 0
    calls_lock = threading.Lock()
    retry_started = threading.Event()
    release_retry = threading.Event()

    def faulting_compare(snapshot: Any, agent_a: str, agent_b: str) -> Any:
        nonlocal calls
        with calls_lock:
            calls += 1
            attempt = calls
        if attempt > 1:
            retry_started.set()
            if not release_retry.wait(timeout=4):
                raise AssertionError("unexpected retry worker release timed out")
        raise RuntimeError("synthetic compare fault")

    monkeypatch.setattr(app_module, "snapshot_compare", faulting_compare)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("c")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, CompareScreen)
            request_id_before = app.controller.next_request_id
            await _select_pair_by_keys(pilot, screen, "claude", "codex")
            await _wait_until(pilot, lambda: app.controller.failed, "accepted report fault")
            await pilot.pause()
            if app.controller.next_request_id > request_id_before + 1:
                await _wait_until(pilot, retry_started.is_set, "unexpected retry worker")
            assert calls == 1
            assert app.controller.next_request_id == request_id_before + 1
            assert screen.report is None
            assert "Unexpected internal fault" in screen._result_text()
            assert "synthetic compare fault" in (app.controller.last_error_details or "")
            for _ in range(5):
                screen.sync_from_controller()
                app._update_ui()
            await pilot.pause(0.05)
            assert calls == 1
            assert app.controller.failed
            await pilot.press("J")
            assert screen.query_one("#compare-json", JsonView).document is None
            assert (
                "Unexpected internal fault"
                in screen.query_one("#compare-json", JsonView).displayed_text
            )
            await pilot.press("q")
            assert app.return_code == 3

    try:
        asyncio.run(_run())
    finally:
        release_retry.set()


def test_compare_explicit_retry_can_succeed_but_keeps_exit_code_three(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Returning to the picker retries an accepted fault without clearing failure."""
    project = _build_pair_fixture(mock_home)
    original_compare = app_module.snapshot_compare
    calls = 0

    def fail_once(snapshot: Any, agent_a: str, agent_b: str) -> Any:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("first comparison attempt failed")
        return original_compare(snapshot, agent_a, agent_b)

    monkeypatch.setattr(app_module, "snapshot_compare", fail_once)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("c")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, CompareScreen)
            await _select_pair_by_keys(pilot, screen, "claude", "codex")
            await _wait_until(
                pilot, lambda: screen._report_state == "error", "first attempt failure"
            )
            assert calls == 1
            assert app.controller.failed
            await pilot.press("escape")
            await pilot.pause()
            assert screen.mode == "picker"
            assert screen.selected_pair == ("claude", "codex")
            await pilot.click("#compare-submit")
            screen = await _wait_compare(pilot, app)
            assert calls == 2
            assert screen.report is not None
            assert screen.selected_pair == ("claude", "codex")
            assert app.controller.failed
            await pilot.press("q")
            assert app.return_code == 3

    asyncio.run(_run())


def test_compare_close_and_old_token_cleanup_are_instance_checked(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale screen instance cannot pop a newer instance or cancel its token."""
    project = _build_pair_fixture(mock_home)
    original_compare = app_module.snapshot_compare
    first_started = threading.Event()
    second_started = threading.Event()
    release_first = threading.Event()
    release_second = threading.Event()
    first_finished = threading.Event()
    second_finished = threading.Event()

    def held_compare(snapshot: Any, agent_a: str, agent_b: str) -> Any:
        pair = (agent_a, agent_b)
        if pair == ("claude", "codex"):
            started, release, finished = first_started, release_first, first_finished
        else:
            started, release, finished = second_started, release_second, second_finished
        started.set()
        try:
            if not release.wait(timeout=4):
                raise AssertionError(f"held comparison release timed out for {pair}")
            return original_compare(snapshot, agent_a, agent_b)
        finally:
            finished.set()

    monkeypatch.setattr(app_module, "snapshot_compare", held_compare)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("c")
            await pilot.pause()
            first = app.screen
            assert isinstance(first, CompareScreen)
            first._selected_a = "claude"
            first._selected_b = "codex"
            first._submit_selected()
            await _wait_until(pilot, first_started.is_set, "first blocked worker")
            await _wait_until(
                pilot,
                lambda: first.owned_request is not None,
                "first owned token",
            )
            old_token = first.owned_request
            assert old_token is not None
            old_event = app.controller._report_events[old_token.request_id]
            # Return to Home, open a distinct instance, and let it own a new token.
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            assert old_event.is_set()
            await pilot.press("c")
            await pilot.pause()
            second = app.screen
            assert isinstance(second, CompareScreen) and second is not first
            second._selected_a = "codex"
            second._selected_b = "claude"
            second._submit_selected()
            await _wait_until(pilot, second_started.is_set, "second blocked worker")
            await _wait_until(pilot, lambda: second.owned_request is not None, "new owned token")
            new_token = second.owned_request
            assert new_token is not None and new_token != old_token
            active_before = app.controller.active_requests.get("compare")
            assert active_before == new_token

            first._owned_request = old_token
            first._cancel_owned_token()
            app.close_compare(first)
            assert app.screen is second
            assert app.controller.active_requests.get("compare") == new_token
            assert app.controller._report_events[new_token.request_id].is_set() is False
            release_first.set()
            release_second.set()
            await _wait_until(pilot, first_finished.is_set, "first worker completion")
            await _wait_until(pilot, second_finished.is_set, "second worker completion")
            await _wait_until(
                pilot, lambda: second.report is not None, "newer token result handoff"
            )
            assert app.controller.get_cached_report("compare", ("codex", "claude")) is second.report
            await pilot.press("q")

    try:
        asyncio.run(_run())
    finally:
        release_first.set()
        release_second.set()


def test_compare_result_layout_and_raw_mode_keep_hidden_picker_inert(mock_home: Path) -> None:
    """Both terminal sizes remain navigable and raw mode ignores picker actions."""
    project = _build_pair_fixture(mock_home, many=18)

    async def _run() -> None:
        for size in ((100, 30), (60, 24)):
            app = SkillLensApp(home=mock_home, cwd=project)
            async with app.run_test(size=size) as pilot:
                await _wait_ready(pilot, app)
                await pilot.press("c")
                await pilot.pause()
                screen = app.screen
                assert isinstance(screen, CompareScreen)
                assert screen.query_one("#compare-a-table", DataTable).display
                assert screen.query_one("#compare-b-table", DataTable).display
                await _select_pair_by_keys(pilot, screen, "claude", "codex")
                screen = await _wait_compare(pilot, app)
                table = screen.query_one("#compare-table", DataTable)
                assert screen.report is not None
                assert table.row_count == len(screen.report.entries)
                assert table.virtual_size.width <= table.size.width
                assert table.virtual_size.height == table.row_count + 1
                assert table.size.height == table.row_count + 1
                for column in table.columns.values():
                    assert column.width >= len(str(column.label))
                assert table.can_focus is False
                result_scroll = screen.query_one("#compare-result-scroll", VerticalScroll)
                result_scroll.focus()
                await pilot.press(*(["down"] * 30))
                await pilot.pause()
                offset = result_scroll.scroll_offset.y
                assert offset > 0
                await pilot.press("J")
                await pilot.pause()
                selected = screen.selected_pair
                hidden_cursors = (
                    screen.query_one("#compare-a-table", DataTable).cursor_row,
                    screen.query_one("#compare-b-table", DataTable).cursor_row,
                )
                await pilot.press("j", "k", "down", "up", "enter")
                assert screen.selected_pair == selected
                assert (
                    screen.query_one("#compare-a-table", DataTable).cursor_row,
                    screen.query_one("#compare-b-table", DataTable).cursor_row,
                ) == hidden_cursors
                assert app.focused is screen.query_one("#compare-json", JsonView)
                await pilot.press("escape")
                await pilot.pause()
                assert result_scroll.scroll_offset.y == offset
                await pilot.press("q")

    asyncio.run(_run())


def test_compare_narrow_table_truncates_paths_but_json_keeps_them(mock_home: Path) -> None:
    """The table may shorten a path, but `J` keeps the exact stored path."""
    project = _build_pair_fixture(mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(60, 24)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("c")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, CompareScreen)
            await _select_pair_by_keys(pilot, screen, "claude", "codex")
            screen = await _wait_compare(pilot, app)
            assert screen.report is not None
            entry = next(item for item in screen.report.entries if item.name == "shared-link")
            assert entry.path_b is not None
            table = screen.query_one("#compare-table", DataTable)
            row: list[str] | None = None
            for index in range(table.row_count):
                cells = [str(cell) for cell in table.get_row_at(index)]
                if cells[0] == "shared-link":
                    row = cells
                    break
            assert row is not None
            assert "…" in row[3]
            assert entry.path_b not in row[3]

            await pilot.press("J")
            await pilot.pause()
            document = screen.query_one("#compare-json", JsonView).document
            assert document is not None
            assert entry.path_b in document
            await pilot.press("q")

    asyncio.run(_run())


def test_compare_long_skill_name_keeps_its_identity_at_wide_widths(
    mock_home: Path,
) -> None:
    """A long skill name gets width before paths, and is disclosed when shortened."""
    project = _build_pair_fixture(mock_home)
    long_name = "long-skill-name-that-needs-space"
    make_skill(mock_home / ".claude" / "skills" / long_name, long_name, "Long name.")
    make_skill(mock_home / ".agents" / "skills" / long_name, long_name, "Long name.")

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("c")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, CompareScreen)
            await _select_pair_by_keys(pilot, screen, "claude", "codex")
            screen = await _wait_compare(pilot, app)
            table = screen.query_one("#compare-table", DataTable)
            name_column = next(
                column for column in table.columns.values() if str(column.label) == "Skill"
            )
            assert name_column.width >= len(long_name)
            row: list[str] | None = None
            for index in range(table.row_count):
                cells = [str(cell) for cell in table.get_row_at(index)]
                if cells[0] == long_name:
                    row = cells
                    break
            assert row is not None

            await pilot.resize_terminal(60, 24)
            await pilot.pause(0.1)
            narrow = screen.query_one("#compare-table", DataTable)
            narrow_name_column = next(
                column for column in narrow.columns.values() if str(column.label) == "Skill"
            )
            assert narrow_name_column.width < len(long_name)
            shortened: list[str] | None = None
            for index in range(narrow.row_count):
                cells = [str(cell) for cell in narrow.get_row_at(index)]
                if "…" in cells[0]:
                    shortened = cells
                    break
            assert shortened is not None
            assert long_name not in shortened[0]
            await pilot.press("J")
            await pilot.pause()
            document = screen.query_one("#compare-json", JsonView).document
            assert document is not None
            assert long_name in document
            await pilot.press("q")

    asyncio.run(_run())


def test_compare_resize_rebuilds_widths_then_falls_back_when_too_narrow(
    mock_home: Path,
) -> None:
    """A resize reflows the table, and an impossible width keeps full paths."""
    project = _build_pair_fixture(mock_home, many=18)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("c")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, CompareScreen)
            await _select_pair_by_keys(pilot, screen, "claude", "codex")
            screen = await _wait_compare(pilot, app)
            assert screen.report is not None
            wide = screen.query_one("#compare-table", DataTable)
            wide_widths = [column.width for column in wide.columns.values()]

            await pilot.resize_terminal(60, 24)
            await pilot.pause(0.1)
            narrow = screen.query_one("#compare-table", DataTable)
            narrow_widths = [column.width for column in narrow.columns.values()]
            assert narrow_widths != wide_widths
            assert narrow.row_count == wide.row_count
            assert narrow.virtual_size.width <= narrow.size.width
            for column in narrow.columns.values():
                assert column.width >= len(str(column.label))

            await pilot.resize_terminal(56, 20)
            await pilot.pause(0.1)
            boundary = screen.query_one("#compare-table", DataTable)
            assert boundary.display is True
            assert boundary.virtual_size.width <= boundary.size.width
            for column in boundary.columns.values():
                assert column.width >= len(str(column.label))

            await pilot.resize_terminal(55, 20)
            await pilot.pause(0.1)
            assert screen.query_one("#compare-table", DataTable).display is False
            fallback = screen.query_one("#compare-fallback", Static)
            assert fallback.display is True
            rendered = str(fallback.content)
            assert "Terminal too narrow for the table; showing full paths." in rendered
            assert "Path B: ~/.agents/skills/shared-link-target" in rendered

            await pilot.resize_terminal(100, 30)
            await pilot.pause(0.1)
            restored = screen.query_one("#compare-table", DataTable)
            assert restored.display is True
            assert restored.row_count == wide.row_count
            assert restored.virtual_size.width <= restored.size.width
            await pilot.press("q")

    asyncio.run(_run())


def test_compare_first_visit_uses_frozen_files_and_registry_only(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After capture, first visits use only the published index, bytes and registry."""
    project = _build_pair_fixture(mock_home)
    before = _cli_compare(mock_home, project)
    skill_file = mock_home / ".agents" / "skills" / "identical" / "SKILL.md"
    skill_bytes = skill_file.read_bytes()
    skill_mode = S_IMODE(skill_file.stat().st_mode)
    link = mock_home / ".claude" / "skills" / "shared-link"
    target_before = os.readlink(link)
    original_run_compare = snapshot_service.run_compare

    def frozen_run_compare(*args: Any, **kwargs: Any) -> Any:
        index = kwargs.get("index")
        registry = kwargs.get("registry")
        assert isinstance(index, FrozenDiscoveryIndex)
        assert registry is not None
        return original_run_compare(*args, **kwargs)

    monkeypatch.setattr(snapshot_service, "run_compare", frozen_run_compare)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            # Change synthetic content and retarget a link after capture.
            skill_file.write_text(
                (
                    "---\nname: identical\ndescription: Changed after capture.\n---\n"
                    "Different bytes.\n"
                ),
                encoding="utf-8",
            )
            link.unlink()
            link.symlink_to(mock_home / ".agents" / "skills" / "only-b", target_is_directory=True)

            def forbidden(*args: Any, **kwargs: Any) -> Any:
                raise AssertionError(
                    "browsing touched a live registry, discovery or compare entry point"
                )

            monkeypatch.setattr("skill_lens.registry.loader.load_registry", forbidden)
            monkeypatch.setattr(system, "live_discovery", forbidden)
            monkeypatch.setattr(discovery, "discover", forbidden)
            monkeypatch.setattr(snapshot_service, "load_registry", forbidden)
            monkeypatch.setattr(snapshot_service, "live_discovery", forbidden)
            monkeypatch.setattr(compare_engine, "load_registry", forbidden)
            monkeypatch.setattr(compare_engine, "live_discovery", forbidden)
            monkeypatch.setattr(compare_engine, "discover", forbidden)

            def is_mock_home(path: Path) -> bool:
                return path == mock_home or mock_home in path.parents

            def guarded_path_method(name: str, original: Any) -> Any:
                def guarded(path: Path, *args: Any, **kwargs: Any) -> Any:
                    if is_mock_home(path):
                        raise AssertionError(
                            f"first visit accessed captured target through Path.{name}: {path}"
                        )
                    return original(path, *args, **kwargs)

                return guarded

            def guarded_os_path_method(name: str, original: Any) -> Any:
                def guarded(path: Any, *args: Any, **kwargs: Any) -> Any:
                    try:
                        candidate = Path(os.fspath(path))
                    except (TypeError, ValueError):
                        return original(path, *args, **kwargs)
                    if not candidate.is_absolute():
                        candidate = Path.cwd() / candidate
                    if is_mock_home(candidate):
                        raise AssertionError(
                            f"first visit accessed captured target through os.{name}: {path}"
                        )
                    return original(path, *args, **kwargs)

                return guarded

            path_methods = (
                "open",
                "read_text",
                "read_bytes",
                "write_text",
                "write_bytes",
                "exists",
                "is_file",
                "is_dir",
                "is_symlink",
                "stat",
                "lstat",
                "iterdir",
                "resolve",
                "unlink",
                "symlink_to",
            )
            os_path_methods = ("open", "stat", "lstat", "scandir", "listdir", "readlink")

            with monkeypatch.context() as target_guard:
                for name in path_methods:
                    target_guard.setattr(Path, name, guarded_path_method(name, getattr(Path, name)))
                for name in os_path_methods:
                    if hasattr(os, name):
                        target_guard.setattr(
                            os, name, guarded_os_path_method(name, getattr(os, name))
                        )
                target_guard.setattr(
                    builtins,
                    "open",
                    guarded_os_path_method("open", builtins.open),
                )

                await pilot.press("g")
                await pilot.pause()
                agents = app.screen
                assert isinstance(agents, AgentsScreen)
                assert agents.query_one("#agents-table", DataTable).row_count == 10
                await pilot.press("escape")
                await pilot.pause()
                await pilot.press("c")
                await pilot.pause()
                screen = app.screen
                assert isinstance(screen, CompareScreen)
                await _select_pair_by_keys(pilot, screen, "claude", "codex")
                screen = await _wait_compare(pilot, app)
                assert screen.report is not None
                assert screen.report.to_dict() == json.loads(before)
                await pilot.press("q")

    try:
        asyncio.run(_run())
    finally:
        skill_file.write_bytes(skill_bytes)
        skill_file.chmod(skill_mode)
        link.unlink()
        link.symlink_to(target_before, target_is_directory=True)
    assert skill_file.read_bytes() == skill_bytes
    assert S_IMODE(skill_file.stat().st_mode) == skill_mode
    assert os.readlink(link) == target_before
