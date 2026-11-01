"""Headless U5 raw JSON tests: mappings, byte equality, mode and focus.

Specification reference: ``FULL_SCREEN_TUI.md`` §8.8, §9.1, Step 5, §21.7 and
§22 U5.

Every test uses the synthetic ``mock_home`` fixture (temporary HOME plus the
protected-system-root isolation installed by ``tests/conftest.py``). The JSON
oracles are independent CLI builders run on the same unchanged fixture, and the
byte check compares the widget's backing document with the real CLI emitter
output including its single final line feed.
"""

from __future__ import annotations

import asyncio
import json
import re
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import DataTable, Input, Static
from typer.testing import CliRunner

from skill_lens.cli import app as cli_app
from skill_lens.core.diff import build_diff_report
from skill_lens.core.discovery import canonical_key
from skill_lens.core.exitcodes import ExitCode
from skill_lens.core.resolver import lookup_name_for_entry, resolve_skill
from skill_lens.core.scanner import build_scan_report
from skill_lens.core.snapshot import capture_session, snapshot_why
from skill_lens.core.system import live_discovery
from skill_lens.models import dumps
from skill_lens.registry.loader import load_registry
from skill_lens.tui.app import SkillLensApp
from skill_lens.tui.diff import DiffScreen
from skill_lens.tui.home import HomeScreen
from skill_lens.tui.json_view import JsonView
from skill_lens.tui.why import WhyScreen
from tests.fixtures.builders import make_skill, write_skill
from tests.fixtures.scenarios import build_scenario

_ANSI_ESCAPE = re.compile(rb"\x1b\[[0-9;]*m")


class _PlainRunner(CliRunner):
    """A runner whose captured output has ANSI styling stripped."""

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        result = super().invoke(*args, **kwargs)
        result.stdout_bytes = _ANSI_ESCAPE.sub(b"", result.stdout_bytes or b"")
        result.stderr_bytes = _ANSI_ESCAPE.sub(b"", result.stderr_bytes or b"")
        return result


runner = _PlainRunner()

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


def _raw_view(app: SkillLensApp, selector: str) -> JsonView:
    return app.screen.query_one(selector, JsonView)


def _raw_text(app: SkillLensApp, selector: str) -> str:
    """The literal text the JSON widget actually renders."""
    view = _raw_view(app, selector)
    return str(view.query_one(".json-document", Static).content)


def _cli_json(*args: str) -> str:
    result = runner.invoke(cli_app, [*args, "--json"])
    assert result.exit_code == 0, result.stdout
    return result.stdout


def _scan_oracle(home: Path, cwd: Path) -> str:
    registry = load_registry()
    index = live_discovery(cwd=cwd, registry=registry)
    report = build_scan_report(Path(index.home), Path(index.cwd), index, registry)
    return dumps(report.to_dict())


def _why_oracle(home: Path, cwd: Path, key: str, agent_id: str) -> str:
    registry = load_registry()
    index = live_discovery(cwd=cwd, registry=registry)
    entry = next(e for e in index.entries if canonical_key(e) == key)
    lookup_name = lookup_name_for_entry(entry, registry[agent_id])
    report = resolve_skill(
        lookup_name,
        agent_id,
        Path(index.cwd),
        Path(index.home),
        index=index,
        registry=registry,
        disabled_overrides=frozenset(),
    )
    return dumps(report.to_dict())


def _diff_oracle(home: Path, cwd: Path, name: str) -> str:
    registry = load_registry()
    index = live_discovery(cwd=cwd, registry=registry)
    report = build_diff_report(
        name,
        Path(index.cwd),
        Path(index.home),
        index=index,
        registry=registry,
    )
    return dumps(report.to_dict())


def _live_key(cwd: Path, needle: str) -> str:
    """The canonical key of the first discovered entry whose path contains ``needle``."""
    registry = load_registry()
    index = live_discovery(cwd=cwd, registry=registry)
    return next(canonical_key(entry) for entry in index.entries if needle in entry.entrypoint_path)


def _build_mismatch_fixture(home: Path) -> tuple[Path, str]:
    """A codex skill whose folder name differs from its declared name."""
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


def _row_keys(app: SkillLensApp) -> list[str]:
    table = app.query_one("#skill-table", DataTable)
    return [str(table.coordinate_to_cell_key((i, 0)).row_key.value) for i in range(table.row_count)]


async def _select_key(pilot: Any, app: SkillLensApp, key: str) -> None:
    table = app.query_one("#skill-table", DataTable)
    index = _row_keys(app).index(key)
    for _ in range(table.row_count):
        if table.cursor_row == index:
            break
        await pilot.press("down" if table.cursor_row < index else "up")
    await pilot.pause(0.02)
    assert app.controller.selected_key == key


# ---------------------------------------------------------------------------
# The three mappings
# ---------------------------------------------------------------------------


def test_home_json_is_the_full_captured_scan_even_under_filters(mock_home: Path) -> None:
    """Home's document is the whole ``scan --json`` report, never the filtered table."""
    build_scenario("claude_personal_beats_project", mock_home)
    make_skill(mock_home / ".claude" / "skills" / "other", "other", "Other skill.")
    project = mock_home / "project"
    expected = _scan_oracle(mock_home, project)
    emitted = _cli_json("scan", "--sandbox", str(mock_home), "--cwd", str(project))

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            # A filter that hides the third row and the preview.
            await pilot.press("slash")
            await pilot.press("d", "e", "p")
            await pilot.press("enter")
            table = app.query_one("#skill-table", DataTable)
            assert table.row_count == 2
            assert table.has_focus

            await pilot.press("J")
            await pilot.pause()
            home = app.screen
            assert isinstance(home, HomeScreen)
            assert home.json_mode is True
            view = _raw_view(app, "#home-json")
            assert view.document == expected
            assert view.document is not None
            assert view.document + "\n" == emitted

            payload = json.loads(view.document)
            names = sorted(entry["name"] for entry in payload["skills"])
            assert names == ["deploy", "deploy", "other"]
            assert _raw_text(app, "#home-json") == view.document
            await pilot.press("q")

    asyncio.run(_run())


def test_why_json_is_the_selected_agents_report_with_the_translated_name(
    mock_home: Path,
) -> None:
    """Why serializes the chosen agent's report under its translated lookup name."""
    project, lookup_name = _build_mismatch_fixture(mock_home)
    key = _live_key(project, "/.codex/skills/folder-key")
    expected = _why_oracle(mock_home, project, key, "codex")
    emitted = _cli_json(
        "why",
        lookup_name,
        "--agent",
        "codex",
        "--sandbox",
        str(mock_home),
        "--cwd",
        str(project),
    )

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await _select_key(pilot, app, key)
            await pilot.press("enter")
            await _wait_until(
                pilot,
                lambda: isinstance(app.screen, WhyScreen) and app.screen._report is not None,
                "why report",
            )
            await pilot.press("J")
            await pilot.pause()
            why = app.screen
            assert isinstance(why, WhyScreen)
            assert why.json_mode is True
            view = _raw_view(app, "#why-json")
            assert view.document == expected
            assert view.document is not None
            assert view.document + "\n" == emitted
            payload = json.loads(view.document)
            assert payload["skill_name"] == lookup_name
            assert payload["agent"] == "codex"
            assert _raw_text(app, "#why-json") == view.document
            await pilot.press("q")

    asyncio.run(_run())


def test_diff_json_is_the_exact_report_document(mock_home: Path) -> None:
    """Diff serializes the very report the ordinary view shows."""
    project, _lookup = _build_mismatch_fixture(mock_home)
    key = _live_key(project, "/.codex/skills/folder-key")
    expected = _diff_oracle(mock_home, project, "folder-key")
    emitted = _cli_json(
        "diff",
        "folder-key",
        "--sandbox",
        str(mock_home),
        "--cwd",
        str(project),
    )

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await _select_key(pilot, app, key)
            await pilot.press("d")
            await _wait_until(
                pilot,
                lambda: isinstance(app.screen, DiffScreen) and app.screen.report is not None,
                "diff report",
            )
            await pilot.press("J")
            await pilot.pause()
            diff = app.screen
            assert isinstance(diff, DiffScreen)
            assert diff.json_mode is True
            view = _raw_view(app, "#diff-json")
            assert view.document == expected
            assert view.document is not None
            assert view.document + "\n" == emitted
            assert json.loads(view.document)["skill_name"] == "folder-key"
            assert _raw_text(app, "#diff-json") == view.document
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Mode, focus and inert keys
# ---------------------------------------------------------------------------


def test_home_json_preserves_state_and_escape_never_clears_the_filter(
    mock_home: Path,
) -> None:
    """``J`` is a mode: filters, selection and focus survive; Esc only exits it."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("slash")
            await pilot.press("d", "e", "p")
            await pilot.press("enter")
            table = app.query_one("#skill-table", DataTable)
            rows_before = _row_keys(app)
            selected_before = app.controller.selected_key
            assert selected_before is not None
            assert table.has_focus

            await pilot.press("J")
            await pilot.pause()
            home = app.screen
            assert isinstance(home, HomeScreen)
            assert home.json_mode is True
            await _wait_until(
                pilot, lambda: _raw_view(app, "#home-json").has_focus, "json view focus"
            )
            assert not home.query_one("#home-body").display
            assert not home.query_one("#filter-strip").display

            # Ordinary navigation is inert while raw JSON is visible.
            await pilot.press("j")
            await pilot.press("k")
            await pilot.press("a")
            await pilot.press("slash")
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            assert home.json_mode is True
            assert app.controller.selected_key == selected_before
            assert app.query_one("#filter-input", Input).value == "dep"
            assert not any(isinstance(s, WhyScreen) for s in app.screen_stack)
            assert app.controller.active_requests.get("diff") is None

            # Esc leaves JSON mode and leaves the filter alone.
            await pilot.press("escape")
            await pilot.pause()
            assert home.json_mode is False
            assert app.query_one("#filter-input", Input).value == "dep"
            assert app.controller.selected_key == selected_before
            assert _row_keys(app) == rows_before
            assert app.query_one("#skill-table", DataTable).has_focus

            # A second toggle round trip leaks nothing to the hidden widgets.
            await pilot.press("J")
            await pilot.pause()
            await pilot.press("backspace")
            await pilot.pause()
            assert home.json_mode is False
            assert app.query_one("#filter-input", Input).value == "dep"
            assert app.query_one("#skill-table", DataTable).has_focus
            await pilot.press("q")

    asyncio.run(_run())


def test_why_json_blocks_hidden_agent_navigation_and_diff(mock_home: Path) -> None:
    """Left/right and ``d`` are inert while Why shows raw JSON."""
    build_scenario("symlink_farm_multi_agent", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
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
            agent_before = why._agent_id
            assert len(why._agent_options) > 1

            await pilot.press("J")
            await pilot.pause()
            assert why.json_mode is True
            await _wait_until(
                pilot, lambda: _raw_view(app, "#why-json").has_focus, "json view focus"
            )

            await pilot.press("right")
            await pilot.press("left")
            await pilot.press("d")
            await pilot.pause()
            assert app.screen is why
            assert why._agent_id == agent_before
            assert app.controller.active_requests.get("diff") is None
            assert not any(isinstance(s, DiffScreen) for s in app.screen_stack)

            await pilot.press("escape")
            await pilot.pause()
            assert why.json_mode is False
            assert why._agent_id == agent_before
            assert why._report is not None
            await pilot.press("q")

    asyncio.run(_run())


def test_why_json_loading_then_report_and_no_agent_explanation(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pending work and no-agent states are explanations, never fabricated JSON."""
    build_scenario("claude_personal_beats_project", mock_home)
    started = threading.Event()
    gate = threading.Event()
    real_why = snapshot_why

    def controlled_why(snapshot: Any, key: str, agent: str) -> Any:
        started.set()
        gate.wait(timeout=5.0)
        return real_why(snapshot, key, agent)

    monkeypatch.setattr("skill_lens.tui.app.snapshot_why", controlled_why)

    async def _run_loading() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_until(pilot, started.is_set, "why worker started")
            why = app.screen
            assert isinstance(why, WhyScreen)

            await pilot.press("J")
            await pilot.pause()
            view = _raw_view(app, "#why-json")
            assert view.document is None
            assert "Loading report" in _raw_text(app, "#why-json")

            gate.set()
            await _wait_until(pilot, lambda: why._report is not None, "why report in JSON mode")
            await pilot.pause(0.05)
            assert view.document is not None
            assert json.loads(view.document)["skill_name"] == "deploy"
            await pilot.press("q")

    async def _run_no_agent() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            current = app.controller.current
            assert current is not None
            zero_agents = tuple(replace(row, agents=()) for row in current.scan.skills)
            app.controller.current = replace(
                current, scan=replace(current.scan, skills=zero_agents)
            )
            await pilot.press("enter")
            await pilot.pause(0.05)
            why = app.screen
            assert isinstance(why, WhyScreen)
            assert why._agent_options == ()

            await pilot.press("J")
            await pilot.pause()
            view = _raw_view(app, "#why-json")
            assert view.document is None
            assert "No agent reaches this installation." in _raw_text(app, "#why-json")
            assert app.controller.active_requests.get("why") is None
            await pilot.press("q")

    asyncio.run(_run_loading())
    asyncio.run(_run_no_agent())


def test_home_json_before_a_capture_explains_instead_of_inventing_a_report(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No published session means an honest explanation, then an atomic switch."""
    build_scenario("claude_personal_beats_project", mock_home)
    expected = _scan_oracle(mock_home, mock_home / "project")
    release = threading.Event()
    real_capture = capture_session

    def blocked_capture(*args: Any, **kwargs: Any) -> Any:
        release.wait(timeout=5.0)
        return real_capture(*args, **kwargs)

    monkeypatch.setattr("skill_lens.tui.app.capture_session", blocked_capture)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.05)
            assert app.controller.current is None
            home = app.screen
            assert isinstance(home, HomeScreen)
            home.query_one("#skill-table", DataTable).focus()
            await pilot.pause()

            await pilot.press("J")
            await pilot.pause()
            view = _raw_view(app, "#home-json")
            assert view.document is None
            assert "Scanning skills" in _raw_text(app, "#home-json")
            assert app.controller.refusal_message is None

            release.set()
            await _wait_until(
                pilot,
                lambda: app.controller.current is not None and view.document is not None,
                "atomic scan document",
            )
            assert view.document == expected
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Literal text and frozen content
# ---------------------------------------------------------------------------


def test_json_renders_literal_brackets_backslashes_and_unicode(mock_home: Path) -> None:
    """The visible text is the document byte for byte; nothing is parsed or added."""
    write_skill(
        mock_home / ".claude" / "skills" / "literal",
        '---\nname: literal\ndescription: "[bold red]not markup[/bold red] C:\\\\temp ünï"\n'
        "---\n# Body\n",
    )
    expected = _scan_oracle(mock_home, mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("J")
            await pilot.pause()
            view = _raw_view(app, "#home-json")
            assert view.document == expected
            rendered = _raw_text(app, "#home-json")
            assert rendered == view.document
            assert "[bold red]not markup[/bold red]" in rendered
            assert "C:\\\\temp" in rendered
            assert "\\u00fcn\\u00ef" in rendered
            await pilot.press("q")

    asyncio.run(_run())


def test_first_json_visit_after_fixture_changes_shows_the_captured_document(
    mock_home: Path,
) -> None:
    """Browsing serializes the captured session, not a new live read."""
    build_scenario("claude_personal_beats_project", mock_home)
    project = mock_home / "project"
    expected = _scan_oracle(mock_home, project)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)

            # Change the fixtures after the capture was published.
            write_skill(
                mock_home / ".claude" / "skills" / "deploy",
                "---\nname: deploy\ndescription: Edited after capture.\n---\n# Body\n",
            )
            make_skill(mock_home / ".claude" / "skills" / "brand-new", "brand-new", "New skill.")

            await pilot.press("J")
            await pilot.pause()
            view = _raw_view(app, "#home-json")
            assert view.document == expected
            assert "Edited after capture" not in (view.document or "")
            assert "brand-new" not in (view.document or "")

            # An explicit refresh publishes the new data, still in JSON mode.
            await pilot.press("r")
            await _wait_until(
                pilot,
                lambda: view.document is not None and "brand-new" in (view.document or ""),
                "refreshed document",
            )
            assert "Edited after capture" in (view.document or "")
            await pilot.press("q")

    asyncio.run(_run())


def test_diff_json_never_mixes_old_document_with_a_new_generation(mock_home: Path) -> None:
    """After a refresh the raw view holds only the new generation's document."""
    build_scenario("claude_personal_beats_project", mock_home)
    project = mock_home / "project"

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("d")
            await _wait_until(
                pilot,
                lambda: isinstance(app.screen, DiffScreen) and app.screen.report is not None,
                "diff report",
            )
            await pilot.press("J")
            await pilot.pause()
            diff = app.screen
            assert isinstance(diff, DiffScreen)
            view = _raw_view(app, "#diff-json")
            first = view.document
            assert first is not None
            current = app.controller.current
            assert current is not None
            first_generation = current.generation

            write_skill(
                mock_home / ".claude" / "skills" / "deploy",
                "---\nname: deploy\ndescription: Personal deploy helper.\n---\n"
                "# Instructions\n\nRaw JSON refresh body.\n",
            )
            await pilot.press("r")
            await _wait_until(
                pilot,
                lambda: (
                    app.controller.current is not None
                    and app.controller.current.generation != first_generation
                    and view.document is not None
                    and view.document != first
                ),
                "new generation document",
            )
            assert diff._generation == app.controller.current.generation
            assert "Raw JSON refresh body." in (view.document or "")
            assert diff.report is not None
            assert view.document == dumps(diff.report.to_dict())
            # The covered Home screen kept its ordinary view.
            home = next(s for s in app.screen_stack if isinstance(s, HomeScreen))
            assert home.json_mode is False
            await pilot.press("q")

    asyncio.run(_run())


def test_json_view_is_read_only_without_editor_or_export(mock_home: Path) -> None:
    """The JSON mode is a focusable literal scroll area, never an editor."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("J")
            await pilot.pause()
            view = _raw_view(app, "#home-json")
            assert isinstance(view, VerticalScroll)
            assert view.can_focus
            await _wait_until(pilot, lambda: view.has_focus, "json view focus")
            assert not view.query("Input")
            assert not view.query("TextArea")
            declared: list[Any] = []
            for cls in type(view).__mro__:
                declared.extend(getattr(cls, "BINDINGS", []))
            view_actions = {binding.action for binding in declared if isinstance(binding, Binding)}
            for action in view_actions:
                for forbidden in ("save", "export", "clipboard", "write"):
                    assert forbidden not in action.lower()
            assert view_actions  # the scroll bindings exist; the check is not vacuous
            await pilot.press("q")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Unchanged publication must not move the reader (R3)
# ---------------------------------------------------------------------------


async def _enter_json_and_scroll(pilot: Any, app: SkillLensApp, selector: str) -> JsonView:
    """Toggle into JSON mode and scroll to the end of the document."""
    view = _raw_view(app, selector)
    await pilot.press("J")
    await _wait_until(pilot, lambda: view.has_focus, "json view focus")
    await pilot.press("end")
    await pilot.pause(0.05)
    assert view.max_scroll_y > 0, "fixture document must be taller than the pane"
    assert view.scroll_offset.y == view.max_scroll_y
    return view


def test_unchanged_home_json_publication_preserves_scroll(mock_home: Path) -> None:
    """An unchanged session synchronization must not rewrite the pane or scroll it."""
    build_scenario("claude_personal_beats_project", mock_home)
    make_skill(mock_home / ".claude" / "skills" / "other", "other", "Other skill.")

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(60, 24)) as pilot:
            await _wait_ready(pilot, app)
            view = await _enter_json_and_scroll(pilot, app, "#home-json")
            document = view.document
            offset = view.scroll_offset.y
            static = view.query_one(".json-document", Static)
            content = static.content

            # An ordinary status/report synchronization with the same session.
            app._update_ui()
            await pilot.pause(0.1)

            assert view.document == document
            assert view.scroll_offset.y == offset
            assert static.content is content, "unchanged text must not be rewritten"

            # A genuine document change publishes the new text and starts at the top.
            write_skill(
                mock_home / ".claude" / "skills" / "other",
                "---\nname: other\ndescription: Edited after capture.\n---\n# Body\n",
            )
            await pilot.press("r")
            await _wait_until(
                pilot,
                lambda: view.document is not None and "Edited after capture" in view.document,
                "refreshed home document",
            )
            await pilot.pause(0.05)
            assert view.document != document
            assert view.scroll_offset.y == 0
            await pilot.press("q")

    asyncio.run(_run())


def test_unchanged_why_json_publication_preserves_scroll(mock_home: Path) -> None:
    """The Why JSON pane keeps its position while the same report is re-published."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(60, 24)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_until(
                pilot,
                lambda: isinstance(app.screen, WhyScreen) and app.screen._report is not None,
                "why report",
            )
            view = await _enter_json_and_scroll(pilot, app, "#why-json")
            document = view.document
            offset = view.scroll_offset.y
            assert document is not None

            # Re-publishing the accepted report through the ordinary redraw path.
            why = app.screen
            assert isinstance(why, WhyScreen)
            why._update_display()
            app._update_ui()
            await pilot.pause(0.1)

            assert view.document == document
            assert view.scroll_offset.y == offset

            # Switching agent is a genuine document transition.
            await pilot.press("escape")
            await pilot.pause()
            why._change_agent(1)
            await _wait_until(pilot, lambda: why._owned_request is None, "agent report")
            await pilot.press("J")
            await _wait_until(pilot, lambda: view.has_focus, "json view focus")
            await pilot.pause(0.05)
            assert view.document != document
            assert view.scroll_offset.y == 0
            await pilot.press("q")

    asyncio.run(_run())


def test_unchanged_diff_json_publication_preserves_scroll(mock_home: Path) -> None:
    """The Diff JSON pane keeps its position until the report really changes."""
    project = mock_home / "project"
    (project / ".git").mkdir(parents=True, exist_ok=True)
    global_dir = mock_home / ".claude" / "skills" / "deep"
    project_dir = project / ".claude" / "skills" / "deep"
    make_skill(global_dir, "deep", "Global deep.", body="# Body\n")
    make_skill(project_dir, "deep", "Project deep.", body="# Body\n")
    (global_dir / "body.txt").write_text(
        "\n".join(f"global {index:02d} " + "a" * 40 for index in range(60)) + "\n",
        encoding="utf-8",
    )
    (project_dir / "body.txt").write_text(
        "\n".join(f"project {index:02d} " + "b" * 40 for index in range(60)) + "\n",
        encoding="utf-8",
    )

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(60, 24)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("d")
            diff = await _wait_until_screen(pilot, app)
            view = await _enter_json_and_scroll(pilot, app, "#diff-json")
            document = view.document
            offset = view.scroll_offset.y
            assert document is not None

            app._update_ui()
            await pilot.pause(0.1)
            assert view.document == document
            assert view.scroll_offset.y == offset

            # A refresh that changes the captured content is a real transition.
            write_skill(
                global_dir,
                "---\nname: deep\ndescription: Global deep.\n---\n# Body\n\nChanged.\n",
            )
            await pilot.press("r")
            await _wait_until(
                pilot,
                lambda: view.document is not None and view.document != document,
                "refreshed diff document",
            )
            await pilot.pause(0.05)
            assert diff._generation == app.controller.current.generation
            assert view.scroll_offset.y == 0
            await pilot.press("q")

    asyncio.run(_run())


async def _wait_until_screen(pilot: Any, app: SkillLensApp) -> DiffScreen:
    await _wait_until(
        pilot,
        lambda: isinstance(app.screen, DiffScreen) and app.screen.report is not None,
        "diff report",
    )
    screen = app.screen
    assert isinstance(screen, DiffScreen)
    return screen


# ---------------------------------------------------------------------------
# Keyboard ownership in every JSON owner (R5)
# ---------------------------------------------------------------------------


def _build_tall_diff_fixture(home: Path) -> Path:
    """Two copies of one skill whose body diff is far taller than a pane."""
    project = home / "project"
    (project / ".git").mkdir(parents=True, exist_ok=True)
    global_dir = home / ".claude" / "skills" / "tall"
    project_dir = project / ".claude" / "skills" / "tall"
    make_skill(global_dir, "tall", "Global tall.", body="# Body\n")
    make_skill(project_dir, "tall", "Project tall.", body="# Body\n")
    (global_dir / "body.txt").write_text(
        "\n".join(f"global {index:02d} " + "a" * 40 for index in range(60)) + "\n",
        encoding="utf-8",
    )
    (project_dir / "body.txt").write_text(
        "\n".join(f"project {index:02d} " + "b" * 40 for index in range(60)) + "\n",
        encoding="utf-8",
    )
    return project


def test_home_json_keyboard_traversal_and_scroll(mock_home: Path) -> None:
    """Home's JSON pane owns Tab, Shift+Tab and the scroll keys while visible."""
    build_scenario("claude_personal_beats_project", mock_home)
    make_skill(mock_home / ".claude" / "skills" / "other", "other", "Other skill.")

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(60, 24)) as pilot:
            await _wait_ready(pilot, app)
            view = await _enter_json_and_scroll(pilot, app, "#home-json")
            table = app.query_one("#skill-table", DataTable)
            assert not app.screen.query_one("#home-body").display
            assert table not in app.screen.focus_chain, "hidden table must not be a Tab stop"

            for _ in range(3):
                await pilot.press("tab")
                assert view.has_focus
            for _ in range(3):
                await pilot.press("shift+tab")
                assert view.has_focus

            await pilot.press("home")
            await pilot.pause(0.05)
            assert view.scroll_offset.y == 0
            await pilot.press("down")
            await pilot.pause(0.05)
            assert 0 < view.scroll_offset.y < view.max_scroll_y
            await pilot.press("pagedown")
            await pilot.pause(0.05)
            assert view.scroll_offset.y > 0
            await pilot.press("q")

    asyncio.run(_run())


def test_why_json_keyboard_traversal_and_return(mock_home: Path) -> None:
    """Why's JSON pane owns Tab/Shift+Tab and scroll keys; Esc/Backspace restore it."""
    build_scenario("claude_personal_beats_project", mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=mock_home / "project")
        async with app.run_test(size=(60, 24)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_until(
                pilot,
                lambda: isinstance(app.screen, WhyScreen) and app.screen._report is not None,
                "why report",
            )
            why = app.screen
            assert isinstance(why, WhyScreen)
            view = await _enter_json_and_scroll(pilot, app, "#why-json")
            agent_before = why._agent_id

            for _ in range(3):
                await pilot.press("tab")
                assert view.has_focus, "Tab must not reach a hidden control"
            for _ in range(3):
                await pilot.press("shift+tab")
                assert view.has_focus

            await pilot.press("home")
            await pilot.pause(0.05)
            assert view.scroll_offset.y == 0
            await pilot.press("down")
            await pilot.pause(0.05)
            assert 0 < view.scroll_offset.y < view.max_scroll_y

            # Esc leaves JSON mode and keeps the detail screen and its agent.
            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is why
            assert why.json_mode is False
            assert why._agent_id == agent_before
            strip = why.query_one("#why-agent-strip")
            assert why._report is not None and strip.display

            # Backspace does the same on a second round trip.
            await pilot.press("J")
            await _wait_until(pilot, lambda: view.has_focus, "json view focus")
            await pilot.press("backspace")
            await pilot.pause()
            assert why.json_mode is False
            assert app.screen is why
            await pilot.press("q")

    asyncio.run(_run())


def test_diff_json_keyboard_traversal_and_return(mock_home: Path) -> None:
    """Diff's JSON pane owns Tab/Shift+Tab and scroll keys; Esc/Backspace return."""
    project = _build_tall_diff_fixture(mock_home)

    async def _run() -> None:
        app = SkillLensApp(home=mock_home, cwd=project)
        async with app.run_test(size=(60, 24)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("d")
            diff = await _wait_until_screen(pilot, app)
            view = await _enter_json_and_scroll(pilot, app, "#diff-json")
            body = app.screen.query_one("#diff-body", VerticalScroll)
            assert not app.screen.query_one("#diff-content").display
            assert body not in app.screen.focus_chain, "collapsed metadata must not be a Tab stop"

            for _ in range(3):
                await pilot.press("tab")
                assert view.has_focus, "Tab must not reach the hidden report"
            for _ in range(3):
                await pilot.press("shift+tab")
                assert view.has_focus

            await pilot.press("home")
            await pilot.pause(0.05)
            assert view.scroll_offset.y == 0
            await pilot.press("down")
            await pilot.pause(0.05)
            assert 0 < view.scroll_offset.y < view.max_scroll_y
            await pilot.press("pagedown")
            await pilot.pause(0.05)
            assert view.scroll_offset.y > 0

            # Esc restores the ordinary report and never pops the screen.
            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is diff
            assert diff.json_mode is False
            assert app.screen.query_one("#diff-content").display
            assert body.has_focus

            # J re-enters; Backspace leaves again with the body focused.
            await pilot.press("J")
            await _wait_until(pilot, lambda: view.has_focus, "json view focus")
            await pilot.press("backspace")
            await pilot.pause()
            assert diff.json_mode is False
            assert app.screen is diff
            assert body.has_focus
            await pilot.press("q")

    asyncio.run(_run())


def test_first_capture_refusal_is_an_honest_home_json_explanation(mock_home: Path) -> None:
    """FR2: a refused first capture must never masquerade as an empty scan.

    With no published session the Home raw view has to explain the refusal, keep
    its backing document unset, avoid a loading or fabricated-ScanReport message
    and leave the sticky internal-fault state alone; quitting stays normal.
    """
    make_skill(mock_home / ".claude" / "skills" / "alpha", "alpha", "Alpha skill.")
    make_skill(mock_home / ".claude" / "skills" / "beta", "beta", "Beta skill.")

    async def _run() -> None:
        # A tiny positive budget refuses the very first capture of these skills.
        app = SkillLensApp(home=mock_home, cwd=mock_home, max_snapshot_bytes=1)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_until(
                pilot,
                lambda: app.controller.status == "refused",
                "first capture refused",
            )
            assert app.controller.current is None, "a refused capture publishes nothing"
            assert app.controller.failed is False, "a refusal is not an internal fault"
            assert app.controller.refusal_message is not None

            home = app.screen
            assert isinstance(home, HomeScreen)
            home.query_one("#skill-table", DataTable).focus()
            await pilot.pause()

            await pilot.press("J")
            await _wait_until(
                pilot,
                lambda: isinstance(app.screen, HomeScreen) and app.screen.json_mode,
                "Home JSON mode",
            )
            view = _raw_view(app, "#home-json")
            assert view.document is None, "a refusal must never fabricate a document"

            explanation = _raw_text(app, "#home-json")
            assert explanation.strip(), "the refusal needs a visible explanation"
            assert "Scanning" not in explanation, "a refusal is not a loading state"
            assert '"skills"' not in explanation, "no empty ScanReport may be fabricated"
            assert not explanation.lstrip().startswith("{"), "the explanation is not JSON"
            assert app.controller.refusal_message in explanation

            # The ordinary status line reports the same refusal, not idle/loading.
            status = str(home.query_one("#status-text", Static).content)
            assert app.controller.refusal_message in status
            assert app.controller.failed is False

            await pilot.press("q")
            assert app.return_code == int(ExitCode.OK)

    asyncio.run(_run())
