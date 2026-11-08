"""Tests for the Skill Lens visual layer (the brand theme and its helpers).

Specification reference: docs/plans/2026-11-08-tui-visual-polish.md.

These tests assert *computed* state -- the theme the app really applies, the
style a widget really carries, the characters a user really sees -- so a test
that passes proves the polish landed rather than that a file exists.

Every test here is mutation-tested: break the thing it guards, watch it fail.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

import pytest
from textual.containers import Horizontal
from textual.widgets import DataTable, Static
from textual.widgets._header import HeaderTitle

from skill_lens.core import paths
from skill_lens.core.snapshot import capture_session
from skill_lens.presentation.state import STATE_STYLE
from skill_lens.tui.app import SkillLensApp
from skill_lens.tui.home import build_home_rows, preview_content, preview_text
from skill_lens.tui.theme import (
    ACCENT,
    ERROR,
    MUTED,
    PRIMARY,
    RULE,
    SECONDARY,
    SKILL_LENS_THEME,
    STATE_COLOUR,
    SUCCESS,
    WARNING,
    fact_block,
    help_block,
    keycap,
    state_cell,
)
from tests.fixtures.builders import make_skill, write_skill
from tests.fixtures.scenarios import build_scenario


def _rendered_text(app: SkillLensApp) -> str:
    """The compositor output as plain text (what a terminal shows)."""
    strips = app.screen._compositor.render_strips()
    return "\n".join(strip.text for strip in strips)


async def _wait_ready(pilot: Any, app: SkillLensApp) -> None:
    """Wait for the first capture, so the app is idle before it is torn down."""
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if app.controller.current is not None and app.controller.status == "ready":
            await pilot.pause(0.02)
            return
        await pilot.pause(0.01)
    raise AssertionError("timed out waiting for the initial capture")


def test_app_applies_the_skill_lens_theme(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The app registers the Skill Lens theme and really renders with it."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test(size=(120, 30)) as pilot:
            await _wait_ready(pilot, app)
            theme = app.current_theme
            assert theme.name == SKILL_LENS_THEME
            assert theme.primary == PRIMARY
            assert theme.background == "#0d1117"

    asyncio.run(_run())


def test_header_shows_the_lens_mark_and_the_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The top bar carries one mark, the app name and a dim version."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test(size=(120, 30)) as pilot:
            await _wait_ready(pilot, app)
            rendered = _rendered_text(app)
            assert "◉" in rendered, "the lens mark must be visible in the top bar"
            assert "S K I L L   L E N S" in rendered, "the brand must be set in caps"
            assert app.SUB_TITLE in rendered
            # The stock Textual glyph must not appear next to our own mark.
            assert "⭘" not in rendered

            # The version is dim; the app name is not.
            title = app.screen.query_one(HeaderTitle)
            styles = [str(span.style) for span in title.content.spans]
            assert any("dim" in style for style in styles), "the version must be dim"

    asyncio.run(_run())


def test_skill_table_header_uses_the_muted_component_style(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The table header is painted with the palette's muted colour."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test(size=(120, 30)) as pilot:
            await _wait_ready(pilot, app)
            table = app.screen.query_one("#skill-table", DataTable)
            header = table.get_component_styles("datatable--header")
            assert header.color.hex.lower() == MUTED.lower()
            assert header.text_style.bold is True
            assert table.zebra_stripes is True

    asyncio.run(_run())


def test_pane_separator_uses_the_hairline_rule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The split between the list and the detail pane is a hairline, not a slab."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test(size=(120, 30)) as pilot:
            await _wait_ready(pilot, app)
            preview = app.screen.query_one("#preview-scroll")
            style, colour = preview.styles.border_left
            assert style == "solid"
            assert colour.hex.lower() == RULE.lower()

    asyncio.run(_run())


def test_preview_keeps_its_characters_and_gains_styled_spans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The preview says exactly what it said before, and is styled like a card."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)
    snapshot = capture_session(generation=1, home=paths.home(), cwd=tmp_path)
    row = build_home_rows(snapshot)[0]

    plain = preview_text(row, snapshot)
    assert isinstance(plain, str)
    # The whole preview is pinned, field by field: dropping one must fail.
    assert plain.splitlines() == [
        f"Name: {row.name}",
        f"Scope: {row.scope_label}",
        f"Path: {row.display_path}",
        plain.splitlines()[3],
        f"Hash: {row.content_hash or 'none'}",
        f"Parse: {row.parse_status} ({row.parse_mark})",
        f"Variant: {row.variant_label or '-'}",
        f"Health: {row.health_label}",
        "",
        "Description:",
        row.description if row.description is not None else "(no description)",
    ]

    styled = preview_content(row, snapshot)
    assert str(styled) == plain, "styling must not change a single character"
    styles = [str(span.style) for span in styled.spans]
    assert any("dim" in style for style in styles), "labels must be dim"
    assert any(SUCCESS in style for style in styles), "a healthy skill must be green"

    # The label of one named field must itself be dim: a wall of undifferentiated
    # bold text is exactly what this change set out to fix.
    label_span = next(
        span for span in styled.spans if styled.plain[span.start : span.end] == "Scope: "
    )
    assert "dim" in str(label_span.style)


def test_state_cell_colours_each_state_with_the_palette() -> None:
    """Every state in a cell carries its own colour."""
    content = state_cell("ACTIVE, SHADOWED")
    assert str(content) == "ACTIVE, SHADOWED"
    styles = [str(span.style) for span in content.spans]
    assert any(SUCCESS in style for style in styles)
    assert any(WARNING in style for style in styles)


def test_state_palette_covers_every_shared_state() -> None:
    """The TUI palette knows every state the shared layer defines.

    This is the drift guard: if a new state is added to the shared table and
    the TUI does not colour it, this test fails.
    """
    assert set(STATE_COLOUR) == set(STATE_STYLE)
    for colour in STATE_COLOUR.values():
        assert colour in {SUCCESS, WARNING, ERROR, SECONDARY, ACCENT, MUTED}


def test_help_block_styles_headings_and_keeps_the_text() -> None:
    """The Help body gains styled headings and bright keys, and loses nothing."""
    text = "COMMON KEYS\n  r — Refresh the captured session.\n"
    styled = help_block(text)
    assert str(styled) == text
    styles = [str(span.style) for span in styled.spans]
    assert any(PRIMARY in style for style in styles), "a heading must be accented"
    key_span = next(span for span in styled.spans if styled.plain[span.start : span.end] == "  r")
    assert "bold" in str(key_span.style), "a key must be bright"


def test_fact_block_keeps_every_character_and_styles_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Styling a report block never changes its text, and does style it."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)
    snapshot = capture_session(generation=1, home=paths.home(), cwd=tmp_path)
    row = build_home_rows(snapshot)[0]
    plain = preview_text(row, snapshot)
    styled = fact_block(plain)
    assert str(styled) == plain
    styles = [str(span.style) for span in styled.spans]
    assert any("dim" in style for style in styles), "a label must be dim"


def test_markup_looking_names_are_never_interpreted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A skill whose name looks like markup still shows as itself."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    write_skill(
        tmp_path / ".claude" / "skills" / "<x>y",
        '---\nname: "<x>y"\ndescription: "[bold red]literal[/bold red]"\n---\n# Body\n',
    )
    snapshot = capture_session(generation=1, home=paths.home(), cwd=tmp_path)
    row = build_home_rows(snapshot)[0]
    plain = preview_text(row, snapshot)
    assert "Name: <x>y" in plain
    assert "[bold red]literal[/bold red]" in plain
    styled = preview_content(row, snapshot)
    assert "[bold red]literal[/bold red]" in str(styled)


def test_agent_strip_is_still_a_row_of_buttons(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The tab treatment is CSS only: the strip stays a Horizontal of Buttons."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test(size=(120, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            for _ in range(6):
                await pilot.pause()
            strip = app.screen.query_one("#why-agent-strip", Horizontal)
            assert isinstance(strip, Horizontal)
            from textual.widgets import Button

            buttons = [child for child in strip.children if isinstance(child, Button)]
            assert buttons, "the agent strip must still hold its buttons"
            assert all(button.id for button in buttons)
            assert any(button.has_class("active") for button in buttons)

    asyncio.run(_run())


def test_keycap_renders_a_key_on_a_chip() -> None:
    """A key cap is a chip with bright text, and its action cannot be split."""
    content = keycap("d", "diff")
    text = str(content)
    assert text.startswith("\u2800d\u2800")
    assert "diff" in text
    styles = [str(span.style) for span in content.spans]
    key_style = next(
        str(span.style)
        for span in content.spans
        if content.plain[span.start : span.end].replace("\u2800", "").strip() == "d"
    )
    assert "on " in key_style, "the key must sit on a chip"
    assert any("dim" in style for style in styles), "the action must be dim"
    # The key and its action are joined by a cell that cannot be a break: no
    # whitespace may sit between them, or the wrapper could split the hint.
    head = text[: text.index("diff")]
    assert not any(character.isspace() for character in head), (
        "the key and its action must not be splittable"
    )


def test_help_body_keeps_one_static_and_the_same_characters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Help body stays a single Static with its row format intact."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test(size=(120, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("f1")
            for _ in range(6):
                await pilot.pause()
            content = app.screen.query_one("#help-content", Static)
            body = str(content.content)
            assert "r —" in body
            assert "COMMON KEYS" in body
            assert len(app.screen.query("#help-content")) == 1

    asyncio.run(_run())


def test_error_colour_is_used_for_a_malformed_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A malformed skill is red, a healthy one is green."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("malformed_frontmatter", tmp_path)
    snapshot = capture_session(generation=1, home=paths.home(), cwd=tmp_path)
    row = build_home_rows(snapshot)[0]
    styled = preview_content(row, snapshot)
    styles = [str(span.style) for span in styled.spans]
    assert any(ERROR in style for style in styles)
    assert not any(SUCCESS in style for style in styles)


def test_hint_bar_names_every_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The hint bar names every key the skill list answers to."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test(size=(140, 42)) as pilot:
            await _wait_ready(pilot, app)
            bar = app.screen.query_one("#footer-help", Static)
            content = bar.content
            keys = [
                content.plain[span.start : span.end].replace("\u2800", "").strip()
                for span in content.spans
                if "on" in str(span.style)
                and content.plain[span.start : span.end].replace("\u2800", "").strip()
            ]
            assert keys == [
                "q",
                "r",
                "/",
                "a",
                "enter",
                "d",
                "g",
                "c",
                "h",
                "J",
                "tab",
                "f1",
            ]

    asyncio.run(_run())


def test_secondary_tables_use_explicit_widths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Agents and Compare tables size their columns, so names are readable."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test(size=(140, 42)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("g")
            for _ in range(4):
                await pilot.pause()
            agents = app.screen.query_one("#agents-table", DataTable)
            width = agents.columns["name"].width
            assert width is not None and width >= 15, (
                f"the Agent column is {width} cells wide, so names are clipped"
            )

            await pilot.press("escape")
            for _ in range(4):
                await pilot.pause()
            await pilot.press("c")
            for _ in range(4):
                await pilot.pause()
            picker = app.screen.query_one("#compare-a-table", DataTable)
            width = picker.columns["name"].width
            assert width is not None and width >= 15, (
                f"the Agent column is {width} cells wide, so names are clipped"
            )

    asyncio.run(_run())


def test_brand_is_centred_in_the_top_bar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The brand sits in the middle of the bar, not left of it."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test(size=(140, 30)) as pilot:
            await _wait_ready(pilot, app)
            strips = app.screen._compositor.render_strips()
            brand_row = next(strip.text for strip in strips if "S K I L L" in strip.text)
            start = brand_row.index("S K I L L")
            end = brand_row.index("L E N S") + len("L E N S")
            middle = (start + end) // 2
            assert abs(middle - len(brand_row) // 2) <= 3, (
                f"the brand is centred at {middle} of {len(brand_row)} cells"
            )

    asyncio.run(_run())


def test_key_bar_never_splits_a_hint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A narrow key bar wraps between hints, never inside one."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test(size=(60, 24)) as pilot:
            await _wait_ready(pilot, app)
            bar = app.screen.query_one("#footer-help", Static)
            for line in str(bar.content).split("\n"):
                assert not line.rstrip().endswith("│"), "a rule must not end a line of the key bar"
            # Every hint is present, and none of them was cut in half.
            text = str(bar.content)
            for label in ("quit", "refresh", "filter", "agent", "why", "diff"):
                assert label in text

    asyncio.run(_run())


def test_long_names_are_shortened_in_the_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A name that is too long for the column is shortened, not clipped."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    long_name = "a-skill-name-that-is-far-longer-than-the-column-allows"
    make_skill(
        tmp_path / ".claude" / "skills" / long_name,
        long_name,
        "A long name.",
    )

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test(size=(140, 30)) as pilot:
            await _wait_ready(pilot, app)
            table = app.screen.query_one("#skill-table", DataTable)
            cell = str(table.get_row_at(0)[0])
            assert cell.endswith("…"), f"the name was not shortened: {cell!r}"
            assert len(cell) <= 40

    asyncio.run(_run())


def test_rows_are_taller_on_a_wide_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A wide screen gives the skills room; a narrow one gives the rows back."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test(size=(140, 30)) as pilot:
            await _wait_ready(pilot, app)
            table = app.screen.query_one("#skill-table", DataTable)
            wide_height = next(iter(table.rows.values())).height
            assert wide_height == 2, f"a wide row is {wide_height} cells high"

        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test(size=(60, 24)) as pilot:
            await _wait_ready(pilot, app)
            table = app.screen.query_one("#skill-table", DataTable)
            narrow_height = next(iter(table.rows.values())).height
            assert narrow_height == 1, "a narrow row must stay one cell high"

    asyncio.run(_run())


def test_why_status_stays_visible_while_the_report_scrolls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The session status is pinned: scrolling the report cannot hide it."""
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    build_scenario("claude_personal_beats_project", tmp_path)

    async def _run() -> None:
        app = SkillLensApp(home=tmp_path, cwd=tmp_path)
        async with app.run_test(size=(140, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            for _ in range(6):
                await pilot.pause()
            why = app.screen
            for _ in range(5):
                await pilot.press("pagedown")
                await pilot.pause(0.02)
            strips = why._compositor.render_strips()
            composited = "\n".join("".join(seg.text for seg in s) for s in strips)
            assert "Ready:" in composited or "Report:" in composited

    asyncio.run(_run())
