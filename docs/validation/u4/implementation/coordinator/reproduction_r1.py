import asyncio
from dataclasses import replace

from textual.widgets import Button, Collapsible

from skill_lens.core import paths
from skill_lens.tui.app import SkillLensApp
from tests.fixtures.scenarios import build_scenario
from tests.test_tui_why import _wait_ready, _wait_why_idle


def test_redraw_preserves_candidate_focus_and_expansion(mock_home, monkeypatch):
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def run():
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test(size=(100, 30)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            screen = app.screen
            block = list(screen.query(Collapsible))[0]
            block.collapsed = True
            block.query_one("CollapsibleTitle").focus()
            await pilot.pause()
            app._update_ui()
            await pilot.pause()
            newblock = list(screen.query(Collapsible))[0]
            print("AFTER REDRAW: collapsed=", newblock.collapsed, "focus=", app.focused)
            assert newblock.collapsed, "Session redraw reset user candidate expansion"
            assert (
                app.focused is not None and app.focused.__class__.__name__ == "CollapsibleTitle"
            ), "Session redraw stole candidate focus"

    asyncio.run(run())


def test_agent_button_renders_captured_label_literally(mock_home, monkeypatch):
    monkeypatch.setattr(paths, "home", lambda: mock_home)
    build_scenario("claude_personal_beats_project", mock_home)

    async def run():
        app = SkillLensApp(home=mock_home, cwd=mock_home)
        async with app.run_test() as pilot:
            await _wait_ready(pilot, app)
            snap = app.controller.current
            app.controller.current = replace(
                snap,
                registry=tuple(
                    replace(a, name="[red]Agent[/red]\\label") if a.id == "claude" else a
                    for a in snap.registry
                ),
            )
            await pilot.press("enter")
            await _wait_why_idle(pilot, app)
            button = app.screen.query_one("#why-agent-claude", Button)
            print("AGENT LABEL:", button.label)
            assert "[red]Agent[/red]" in button.label.plain, (
                "Captured agent name interpreted as markup"
            )

    asyncio.run(run())
