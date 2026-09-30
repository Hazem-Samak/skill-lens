"""Phase 3 snapshot harness: pin the terminal output of ``scan``, ``why``, ``diff``.

Rich output varies with terminal width, colour support and environment, so every
snapshot is rendered into a console with all of that pinned, then compared as
plain text. The fixed width is **asserted, not assumed**: a snapshot recorded at
one width and compared at another would prove nothing.

Regenerate after an intentional change to the presentation layer:

    pytest tests/test_render_snapshots.py --update-snapshots

The goldens are plain text under ``tests/fixtures/snapshots/``, so no new dev
dependency is introduced. Each snapshot is also checked for machine-specific
content, so a snapshot can never smuggle in the path of whoever generated it.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from rich.console import Console

import skill_lens.core.diff as diff_module
from skill_lens.core.diff import build_diff_report
from skill_lens.core.resolver import resolve_skill
from skill_lens.core.scanner import build_scan_report
from skill_lens.render import render_diff, render_scan, render_why
from tests.fixtures.builders import make_skill
from tests.fixtures.scenarios import build_scenario

SNAPSHOT_DIR = Path(__file__).parent / "fixtures" / "snapshots"

#: The single width every snapshot is recorded and compared at.
SNAPSHOT_WIDTH = 100


def _render(renderer: Callable[..., None], model: object) -> str:
    """Render ``model`` with everything that varies pinned, and return the text."""
    console = Console(
        record=True,
        width=SNAPSHOT_WIDTH,
        no_color=True,
        force_terminal=False,
        highlight=False,
    )
    # Asserted, not assumed: without this Rich would silently fall back to the
    # real terminal's width and the snapshot would depend on where it ran.
    assert console.width == SNAPSHOT_WIDTH
    renderer(model, console)
    return console.export_text()


def _check(name: str, update: bool, render: Callable[[], str], home: Path) -> str:
    """Compare a rendered snapshot against its golden, or rewrite the golden."""
    path = SNAPSHOT_DIR / f"{name}.txt"
    rendered = render()
    if update:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        return rendered
    assert path.exists(), f"missing snapshot {path.name}; run with --update-snapshots"
    assert rendered == path.read_text(encoding="utf-8"), (
        f"snapshot {path.name} changed. Review the difference, then re-run with "
        "--update-snapshots if the new output is correct."
    )
    assert str(home) not in rendered, "a snapshot must not embed a machine path"
    return rendered


# --- scan ------------------------------------------------------------------


def test_scan_snapshot(mock_home: Path, update_snapshots: bool) -> None:
    build_scenario("variant_hash_detection", mock_home)
    home = mock_home.resolve()
    _check(
        "scan_variant_hash_detection",
        update_snapshots,
        lambda: _render(render_scan, build_scan_report(home, home)),
        home,
    )


# --- why -------------------------------------------------------------------


def test_why_snapshot(mock_home: Path, update_snapshots: bool) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    home = mock_home.resolve()
    _check(
        "why_claude_personal_beats_project",
        update_snapshots,
        lambda: _render(render_why, resolve_skill("deploy", "claude", home / "project", home)),
        home,
    )


# --- diff ------------------------------------------------------------------


def test_diff_snapshot(mock_home: Path, update_snapshots: bool) -> None:
    build_scenario("variant_hash_detection", mock_home)
    home = mock_home.resolve()
    _check(
        "diff_variant_hash_detection",
        update_snapshots,
        lambda: _render(render_diff, build_diff_report("deploy", home, home)),
        home,
    )


def test_diff_no_differences_snapshot(mock_home: Path, update_snapshots: bool) -> None:
    """One canonical library reached by three symlinks: nothing to diff."""
    build_scenario("symlink_farm_multi_agent", mock_home)
    home = mock_home.resolve()
    _check(
        "diff_no_differences",
        update_snapshots,
        lambda: _render(render_diff, build_diff_report("shared", home, home)),
        home,
    )


def test_diff_not_found_snapshot(mock_home: Path, update_snapshots: bool) -> None:
    build_scenario("claude_personal_beats_project", mock_home)
    home = mock_home.resolve()
    _check(
        "diff_not_found",
        update_snapshots,
        lambda: _render(render_diff, build_diff_report("nope", home, home)),
        home,
    )


def test_diff_invalid_copy_snapshot(mock_home: Path, update_snapshots: bool) -> None:
    """A readable copy that fails validation is diffed but carries no letter."""
    home = mock_home.resolve()
    make_skill(
        home / ".claude" / "skills" / "broken",
        "broken",
        "Valid copy.",
        body="# Instructions\n\nGood body.\n",
    )
    (home / ".agents" / "skills" / "broken").mkdir(parents=True)
    (home / ".agents" / "skills" / "broken" / "SKILL.md").write_text(
        "---\nname: broken\n---\n# Body without a description.\n", encoding="utf-8"
    )
    _check(
        "diff_invalid_copy",
        update_snapshots,
        lambda: _render(render_diff, build_diff_report("broken", home, home)),
        home,
    )


def test_diff_unreadable_copy_snapshot(mock_home: Path, update_snapshots: bool) -> None:
    """An unreadable copy must still be listed, not hidden behind "no differences"."""
    build_scenario("symlink_cycle_guard", mock_home)
    home = mock_home.resolve()
    rendered = _check(
        "diff_unreadable_copy",
        update_snapshots,
        lambda: _render(render_diff, build_diff_report("cycle_a", home, home)),
        home,
    )
    assert "cannot be read: symlink cycle" in rendered
    assert "cycle_a" in rendered


def test_diff_truncation_notice_snapshot(
    mock_home: Path, update_snapshots: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The truncation notices, at budgets small enough to keep the golden short.

    The real budgets (400 changed lines, 20,000 characters) are exercised by the
    Phase 3 gate; here only the wording of the notice is pinned.
    """
    monkeypatch.setattr(diff_module, "MAX_CHANGED_LINES_PER_COPY", 6)
    monkeypatch.setattr(diff_module, "MAX_CHARS_PER_REPORT", 400)
    home = mock_home.resolve()
    make_skill(home / ".claude" / "skills" / "long", "long", "Copy A.")
    make_skill(home / ".agents" / "skills" / "long", "long", "Copy B.")
    for root, prefix in ((".claude/skills", "old"), (".agents/skills", "new")):
        (home / root / "long" / "body.txt").write_text(
            "".join(f"{prefix} {index}\n" for index in range(20)), encoding="utf-8"
        )
    _check(
        "diff_truncated",
        update_snapshots,
        lambda: _render(render_diff, build_diff_report("long", home, home)),
        home,
    )


def test_diff_snapshot_keeps_markup_in_content_literal(
    mock_home: Path, update_snapshots: bool
) -> None:
    """File content can never inject Rich markup (spec section 6, command 5).

    If Rich had interpreted the tags they would be *consumed*, so their literal
    presence in the rendered text is the proof that they were not.
    """
    home = mock_home.resolve()
    make_skill(home / ".claude" / "skills" / "evil", "evil", "[bold red]PWNED[/]")
    make_skill(
        home / ".agents" / "skills" / "evil",
        "evil",
        "harmless",
        body="# Instructions\n\n[link=http://example.test]click[/link]\n",
    )
    rendered = _check(
        "diff_markup_is_literal",
        update_snapshots,
        lambda: _render(render_diff, build_diff_report("evil", home, home)),
        home,
    )
    assert "[bold red]PWNED[/]" in rendered
    assert "[link=http://example.test]click[/link]" in rendered
