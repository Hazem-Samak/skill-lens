"""Tests for the shared presentation package (C4).

Verifies public exports, state dictionaries, frozen dataclasses, pure text helpers,
branch priority and wording, literal string handling, binary content suppression,
isolation from live filesystem calls, and import dependency direction.
"""

from __future__ import annotations

import ast
import io
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from rich.console import Console

from skill_lens.models.diff import DiffChange, DiffCopy, DiffFile, DiffHunk, DiffReport
from skill_lens.models.enums import HeadlineState, Scope
from skill_lens.models.parsing import (
    ERR_DANGLING_SYMLINK,
    ERR_PERMISSION_DENIED,
    ERR_SYMLINK_CYCLE,
)
from skill_lens.presentation import (
    SCOPE_LABEL,
    STATE_MARK,
    STATE_STYLE,
    HeadingParts,
    NoticeParts,
    copy_heading,
    needs_listing,
    no_differences_message,
    range_text,
    unified_text,
    unreadable_reason,
)
from skill_lens.render import _copy_heading, _render_file, render_diff

# --- 1. Public exports and dictionaries ------------------------------------


def test_public_exports() -> None:
    """The presentation package re-exports exactly the expected 11 public symbols."""
    import skill_lens.presentation as presentation

    expected = {
        "HeadingParts",
        "NoticeParts",
        "SCOPE_LABEL",
        "STATE_MARK",
        "STATE_STYLE",
        "copy_heading",
        "needs_listing",
        "no_differences_message",
        "range_text",
        "unified_text",
        "unreadable_reason",
    }
    assert set(presentation.__all__) == expected
    for name in expected:
        assert hasattr(presentation, name)


def test_state_style_mapping() -> None:
    """STATE_STYLE maps every HeadlineState to its expected terminal style."""
    for state in HeadlineState:
        assert state in STATE_STYLE
    assert STATE_STYLE[HeadlineState.ACTIVE] == "bold green"
    assert STATE_STYLE[HeadlineState.COEXISTS] == "bold cyan"
    assert STATE_STYLE[HeadlineState.SHADOWED] == "yellow"
    assert STATE_STYLE[HeadlineState.DISABLED] == "dim"
    assert STATE_STYLE[HeadlineState.UNSEARCHED] == "dim"
    assert STATE_STYLE[HeadlineState.INVALID] == "bold red"
    assert STATE_STYLE[HeadlineState.AMBIGUOUS] == "bold magenta"


def test_state_mark_mapping() -> None:
    """STATE_MARK maps every HeadlineState to its expected status mark."""
    for state in HeadlineState:
        assert state in STATE_MARK
    assert STATE_MARK[HeadlineState.ACTIVE] == "*"
    assert STATE_MARK[HeadlineState.COEXISTS] == "+"
    assert STATE_MARK[HeadlineState.SHADOWED] == "o"
    assert STATE_MARK[HeadlineState.DISABLED] == "-"
    assert STATE_MARK[HeadlineState.UNSEARCHED] == "."
    assert STATE_MARK[HeadlineState.INVALID] == "x"
    assert STATE_MARK[HeadlineState.AMBIGUOUS] == "?"


def test_scope_label_mapping() -> None:
    """SCOPE_LABEL maps all Scope values to their human-readable labels."""
    for scope in Scope:
        assert scope in SCOPE_LABEL
    assert SCOPE_LABEL[Scope.USER] == "Global"
    assert SCOPE_LABEL[Scope.PROJECT] == "Project"
    assert SCOPE_LABEL[Scope.SYSTEM] == "System"
    assert SCOPE_LABEL[Scope.PLUGIN] == "Plugin"


# --- 2. Frozen slotted dataclasses -----------------------------------------


def test_heading_parts_frozen_and_slotted() -> None:
    """HeadingParts is slotted and immutable."""
    parts = HeadingParts(
        mark="=",
        style="bold cyan",
        path="~/.agents/skills/demo",
        variant=" [Variant A]",
        scope="user",
        parse_status="valid",
        status="baseline (no diff shown)",
    )
    assert parts.mark == "="
    assert parts.style == "bold cyan"
    assert parts.path == "~/.agents/skills/demo"
    assert parts.variant == " [Variant A]"
    assert parts.scope == "user"
    assert parts.parse_status == "valid"
    assert parts.status == "baseline (no diff shown)"

    # Slots verify: no __dict__ attribute, __slots__ is present
    assert not hasattr(parts, "__dict__")
    assert set(parts.__slots__) == {
        "mark",
        "style",
        "path",
        "variant",
        "scope",
        "parse_status",
        "status",
    }

    with pytest.raises(FrozenInstanceError):
        parts.status = "mutated"  # type: ignore[misc]

    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        parts.non_existent = "val"  # type: ignore[attr-defined]


def test_notice_parts_frozen_and_slotted() -> None:
    """NoticeParts is slotted and immutable."""
    notice = NoticeParts(
        label="No differences:",
        style="green",
        body=" all 2 readable copies are identical.",
    )
    assert notice.label == "No differences:"
    assert notice.style == "green"
    assert notice.body == " all 2 readable copies are identical."

    # Slots verify: no __dict__ attribute, __slots__ is present
    assert not hasattr(notice, "__dict__")
    assert set(notice.__slots__) == {"label", "style", "body"}

    with pytest.raises(FrozenInstanceError):
        notice.body = "mutated"  # type: ignore[misc]

    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        notice.non_existent = "val"  # type: ignore[attr-defined]


# --- 3. Pure helper algorithms ---------------------------------------------


def test_range_text() -> None:
    """range_text formats unified diff range counts per difflib standard."""
    assert range_text(1, 1) == "1"
    assert range_text(10, 1) == "10"
    assert range_text(1, 0) == "1,0"
    assert range_text(0, 0) == "0,0"
    assert range_text(5, 12) == "5,12"


def test_unified_text_formatting() -> None:
    """unified_text formats diff headers, hunks and lines into standard unified diff."""
    # Zero hunks
    file_no_hunks = DiffFile(path="README.md", change=DiffChange.MODIFIED, hunks=())
    assert unified_text(file_no_hunks) == "--- README.md\n+++ README.md"

    # Single hunk
    hunk1 = DiffHunk(
        old_start=1,
        old_count=1,
        new_start=1,
        new_count=2,
        lines=("-old line", "+new line 1", "+new line 2"),
    )
    file_one_hunk = DiffFile(path="SKILL.md", change=DiffChange.MODIFIED, hunks=(hunk1,))
    expected_one = "--- SKILL.md\n+++ SKILL.md\n@@ -1 +1,2 @@\n-old line\n+new line 1\n+new line 2"
    assert unified_text(file_one_hunk) == expected_one

    # Multiple hunks
    hunk2 = DiffHunk(
        old_start=10,
        old_count=3,
        new_start=11,
        new_count=1,
        lines=(" context", "-removed", "+added"),
    )
    file_multi = DiffFile(path="SKILL.md", change=DiffChange.MODIFIED, hunks=(hunk1, hunk2))
    expected_multi = (
        "--- SKILL.md\n"
        "+++ SKILL.md\n"
        "@@ -1 +1,2 @@\n"
        "-old line\n"
        "+new line 1\n"
        "+new line 2\n"
        "@@ -10,3 +11 @@\n"
        " context\n"
        "-removed\n"
        "+added"
    )
    assert unified_text(file_multi) == expected_multi


def test_unreadable_reason() -> None:
    """unreadable_reason maps parsing errors or returns fallback."""
    copy_cycle = DiffCopy(
        path="/path",
        scope=Scope.USER,
        parse_status="error",
        is_valid=False,
        is_readable=False,
        error=ERR_SYMLINK_CYCLE,
    )
    assert unreadable_reason(copy_cycle) == "symlink cycle"

    copy_dangling = DiffCopy(
        path="/path",
        scope=Scope.USER,
        parse_status="error",
        is_valid=False,
        is_readable=False,
        error=ERR_DANGLING_SYMLINK,
    )
    assert unreadable_reason(copy_dangling) == "dangling symlink"

    copy_permission = DiffCopy(
        path="/path",
        scope=Scope.USER,
        parse_status="error",
        is_valid=False,
        is_readable=False,
        error=ERR_PERMISSION_DENIED,
    )
    assert unreadable_reason(copy_permission) == "permission denied"

    copy_other = DiffCopy(
        path="/path",
        scope=Scope.USER,
        parse_status="error",
        is_valid=False,
        is_readable=False,
        error="ERR_UNKNOWN",
    )
    assert unreadable_reason(copy_other) == "no readable content"

    copy_none = DiffCopy(
        path="/path",
        scope=Scope.USER,
        parse_status="error",
        is_valid=False,
        is_readable=False,
        error=None,
    )
    assert unreadable_reason(copy_none) == "no readable content"


def test_needs_listing() -> None:
    """needs_listing returns True when multiple copies exist or any copy is unreadable."""
    c_read = DiffCopy(
        path="/a", scope=Scope.USER, parse_status="valid", is_valid=True, is_readable=True
    )
    c_unread = DiffCopy(
        path="/b",
        scope=Scope.USER,
        parse_status="error",
        is_valid=False,
        is_readable=False,
        error=ERR_DANGLING_SYMLINK,
    )

    # Empty report
    assert not needs_listing(
        DiffReport(skill_name="foo", home="/home", cwd="/cwd", found=True, copies=())
    )

    # Single readable copy: does not need listing
    assert not needs_listing(
        DiffReport(skill_name="foo", home="/home", cwd="/cwd", found=True, copies=(c_read,))
    )

    # Single unreadable copy: needs listing
    assert needs_listing(
        DiffReport(skill_name="foo", home="/home", cwd="/cwd", found=True, copies=(c_unread,))
    )

    # Multiple readable copies: needs listing
    assert needs_listing(
        DiffReport(skill_name="foo", home="/home", cwd="/cwd", found=True, copies=(c_read, c_read))
    )


# --- 4. copy_heading branches, priority, and literal text -------------------


def test_copy_heading_branches_and_priority() -> None:
    """copy_heading respects branch priority: baseline, unreadable, diff, no baseline, identical."""
    # 1. Baseline
    c_base = DiffCopy(
        path="/home/skill",
        scope=Scope.USER,
        parse_status="valid",
        is_valid=True,
        is_readable=True,
        is_baseline=True,
        variant_label="A",
    )
    parts = copy_heading(c_base, baseline_exists=True, display_path="~/skill")
    assert parts == HeadingParts(
        mark="=",
        style="bold cyan",
        path="~/skill",
        variant=" [Variant A]",
        scope="user",
        parse_status="valid",
        status="baseline (no diff shown)",
    )

    # 2. Unreadable (takes precedence even if files or baseline_exists flag present)
    c_unread = DiffCopy(
        path="/home/unread",
        scope=Scope.PROJECT,
        parse_status="dangling_symlink",
        is_valid=False,
        is_readable=False,
        error=ERR_DANGLING_SYMLINK,
    )
    parts = copy_heading(c_unread, baseline_exists=True, display_path="~/unread")
    assert parts == HeadingParts(
        mark="x",
        style="bold red",
        path="~/unread",
        variant="",
        scope="project",
        parse_status="dangling_symlink",
        status="cannot be read: dangling symlink",
    )

    # 3. Differing files
    diff_file = DiffFile(path="SKILL.md", change=DiffChange.MODIFIED)
    c_diff = DiffCopy(
        path="/home/differ",
        scope=Scope.SYSTEM,
        parse_status="valid",
        is_valid=True,
        is_readable=True,
        variant_label="B",
        files=(diff_file,),
    )
    parts = copy_heading(c_diff, baseline_exists=True, display_path="~/differ")
    assert parts == HeadingParts(
        mark="*",
        style="bold yellow",
        path="~/differ",
        variant=" [Variant B]",
        scope="system",
        parse_status="valid",
        status="1 file(s) differ",
    )

    # Multiple differing files
    diff_file2 = DiffFile(path="other.txt", change=DiffChange.ADDED)
    c_diff2 = DiffCopy(
        path="/home/differ",
        scope=Scope.PLUGIN,
        parse_status="valid",
        is_valid=True,
        is_readable=True,
        variant_label=None,
        files=(diff_file, diff_file2),
    )
    parts = copy_heading(c_diff2, baseline_exists=True, display_path="~/differ")
    assert parts == HeadingParts(
        mark="*",
        style="bold yellow",
        path="~/differ",
        variant="",
        scope="plugin",
        parse_status="valid",
        status="2 file(s) differ",
    )

    # 4. No baseline (readable, no differing files, but baseline_exists=False)
    c_no_base = DiffCopy(
        path="/home/nobase",
        scope=Scope.USER,
        parse_status="missing_description",
        is_valid=False,
        is_readable=True,
        files=(),
    )
    parts = copy_heading(c_no_base, baseline_exists=False, display_path="~/nobase")
    assert parts == HeadingParts(
        mark="-",
        style="dim",
        path="~/nobase",
        variant="",
        scope="user",
        parse_status="missing_description",
        status="not compared: no baseline",
    )

    # 5. Identical to baseline (readable, no differing files, baseline_exists=True)
    c_identical = DiffCopy(
        path="/home/copy2",
        scope=Scope.USER,
        parse_status="valid",
        is_valid=True,
        is_readable=True,
        variant_label="A",
        files=(),
    )
    parts = copy_heading(c_identical, baseline_exists=True, display_path="~/copy2")
    assert parts == HeadingParts(
        mark="=",
        style="dim",
        path="~/copy2",
        variant=" [Variant A]",
        scope="user",
        parse_status="valid",
        status="identical to the baseline",
    )


def test_plain_parts_preserve_literal_text() -> None:
    """copy_heading preserves literal brackets, closing tags and backslashes without escaping."""
    special_path = "~/[red]evil[bold]tag[/bold][/red]\\slash"
    c_special = DiffCopy(
        path=special_path,
        scope=Scope.USER,
        parse_status="valid",
        is_valid=True,
        is_readable=True,
        variant_label="[X]",
    )
    parts = copy_heading(c_special, baseline_exists=True, display_path=special_path)
    # The fields in HeadingParts must contain the raw literal strings, not Rich markup or escapes
    assert parts.path == special_path
    assert parts.variant == " [Variant [X]]"


# --- 5. no_differences_message branches and wording -------------------------


def test_no_differences_message_all_branches() -> None:
    """no_differences_message covers all 4 branches with exact label, style and body."""
    c1 = DiffCopy(
        path="/a", scope=Scope.USER, parse_status="valid", is_valid=True, is_readable=True
    )
    c2 = DiffCopy(
        path="/b", scope=Scope.USER, parse_status="valid", is_valid=True, is_readable=True
    )
    c_unread = DiffCopy(
        path="/c",
        scope=Scope.USER,
        parse_status="error",
        is_valid=False,
        is_readable=False,
        error=ERR_SYMLINK_CYCLE,
    )

    # Branch 1: baseline_path is None (D-03)
    rep_no_baseline = DiffReport(
        skill_name="demo",
        home="/home",
        cwd="/cwd",
        found=True,
        baseline_path=None,
        copies=(c1, c2),
    )
    notice1 = no_differences_message(rep_no_baseline)
    assert notice1 == NoticeParts(
        label="Not compared:",
        style="yellow",
        body=" no copy could serve as a baseline.",
    )
    assert notice1.body.startswith(" ")

    # Branch 2: only one copy exists
    rep_one_copy = DiffReport(
        skill_name="demo",
        home="/home",
        cwd="/cwd",
        found=True,
        baseline_path="/a",
        copies=(c1,),
    )
    notice2 = no_differences_message(rep_one_copy)
    assert notice2 == NoticeParts(
        label="No differences:",
        style="green",
        body=" only one copy exists, so there is nothing to compare.",
    )
    assert notice2.body.startswith(" ")

    # Branch 3: fewer than two readable copies (e.g. 2 copies, but only 1 readable)
    rep_fewer_readable = DiffReport(
        skill_name="demo",
        home="/home",
        cwd="/cwd",
        found=True,
        baseline_path="/a",
        copies=(c1, c_unread),
    )
    notice3 = no_differences_message(rep_fewer_readable)
    assert notice3 == NoticeParts(
        label="No differences:",
        style="green",
        body=" fewer than two copies could be read.",
    )
    assert notice3.body.startswith(" ")

    # Branch 4: all readable copies are identical
    rep_all_identical = DiffReport(
        skill_name="demo",
        home="/home",
        cwd="/cwd",
        found=True,
        baseline_path="/a",
        copies=(c1, c2),
    )
    notice4 = no_differences_message(rep_all_identical)
    assert notice4 == NoticeParts(
        label="No differences:",
        style="green",
        body=" all 2 readable copies are identical.",
    )
    assert notice4.body.startswith(" ")


# --- 6. Live filesystem isolation -------------------------------------------


def test_shared_helpers_do_not_access_filesystem() -> None:
    """Shared presentation helpers never call paths services or filesystem operations."""
    c = DiffCopy(
        path="/mock/path/skill",
        scope=Scope.USER,
        parse_status="valid",
        is_valid=True,
        is_readable=True,
        is_baseline=True,
        variant_label="A",
    )
    rep = DiffReport(
        skill_name="skill",
        home="/home",
        cwd="/cwd",
        found=True,
        baseline_path="/mock/path/skill",
        copies=(c,),
    )
    diff_file = DiffFile(
        path="SKILL.md",
        change=DiffChange.MODIFIED,
        hunks=(DiffHunk(1, 1, 1, 1, lines=("-a", "+b")),),
    )

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("Forbidden filesystem / paths call during pure presentation!")

    with (
        patch("skill_lens.core.paths.display", side_effect=forbidden),
        patch("skill_lens.core.paths.home", side_effect=forbidden),
        patch("skill_lens.core.paths.same_location", side_effect=forbidden),
        patch("pathlib.Path.resolve", side_effect=forbidden),
        patch("pathlib.Path.read_bytes", side_effect=forbidden),
        patch("pathlib.Path.read_text", side_effect=forbidden),
        patch("pathlib.Path.stat", side_effect=forbidden),
        patch("os.walk", side_effect=forbidden),
        patch("os.scandir", side_effect=forbidden),
    ):
        # All 6 public helpers operate cleanly without touching the patched boundaries
        parts = copy_heading(c, baseline_exists=True, display_path="~/skill")
        assert parts.path == "~/skill"

        notice = no_differences_message(rep)
        assert notice.label == "No differences:"

        assert not needs_listing(rep)
        assert range_text(1, 1) == "1"
        assert "--- SKILL.md" in unified_text(diff_file)
        assert unreadable_reason(c) == "no readable content"


# --- 7. Rich rendering adapter tests: literal text & binary suppression ----


def test_render_adapter_literal_markup_and_backslashes(mock_home: Path) -> None:
    """Renderer escapes paths and labels at Rich boundary so brackets and slashes are literal."""
    special_path = str(mock_home / "[bold red]evil[/bold red]\\dir")
    copy = DiffCopy(
        path=special_path,
        scope=Scope.USER,
        parse_status="valid",
        is_valid=True,
        is_readable=True,
        is_baseline=True,
        variant_label="[A]",
    )

    heading = _copy_heading(copy, baseline_exists=True)
    # The heading returned by _copy_heading has escaped markup for path and variant
    console = Console(file=io.StringIO(), force_terminal=False, width=120, color_system=None)
    console.print(heading)
    output = console.file.getvalue()  # type: ignore[attr-defined]

    # Literal strings survive in terminal output without being parsed as Rich tags
    assert "~/[bold red]evil[/bold red]\\dir" in output
    assert str(mock_home) not in output
    assert "[bold red]evil[/bold red]\\dir" in output
    assert "[Variant [A]]" in output


def test_render_diff_binary_suppression_and_syntax() -> None:
    """Binary files never have their payload printed, while text diff syntax is unescaped."""
    binary_file = DiffFile(
        path="payload.png",
        change=DiffChange.MODIFIED,
        is_binary=True,
        hunks=(DiffHunk(1, 1, 1, 1, lines=("\x00\x01\x02SECRET_BINARY",)),),
    )
    text_file = DiffFile(
        path="code.py",
        change=DiffChange.MODIFIED,
        is_binary=False,
        hunks=(DiffHunk(1, 1, 1, 1, lines=("-[red]old[/red]\\slash", "+[green]new[/green]")),),
    )

    console = Console(file=io.StringIO(), force_terminal=False, width=120, color_system=None)
    _render_file(binary_file, console)
    binary_out = console.file.getvalue()  # type: ignore[attr-defined]

    # Binary guard triggered: content is never printed
    assert "Binary content differs and is never printed." in binary_out
    assert "SECRET_BINARY" not in binary_out

    # Text diff printed with Rich Syntax (literal non-markup handling)
    console_text = Console(file=io.StringIO(), force_terminal=False, width=120, color_system=None)
    _render_file(text_file, console_text)
    text_out = console_text.file.getvalue()  # type: ignore[attr-defined]

    assert "[red]old[/red]\\slash" in text_out
    assert "[green]new[/green]" in text_out


def test_render_diff_full_flow_with_shared_parts(mock_home: Path) -> None:
    """render_diff runs end-to-end using shared presentation parts and preserves output."""
    c_base = DiffCopy(
        path=str(mock_home / "skill_a"),
        scope=Scope.USER,
        parse_status="valid",
        is_valid=True,
        is_readable=True,
        is_baseline=True,
        variant_label="A",
    )
    c_other = DiffCopy(
        path=str(mock_home / "skill_b"),
        scope=Scope.PROJECT,
        parse_status="valid",
        is_valid=True,
        is_readable=True,
        variant_label="B",
        files=(
            DiffFile(
                path="SKILL.md",
                change=DiffChange.MODIFIED,
                hunks=(DiffHunk(1, 1, 1, 1, lines=("-old", "+new")),),
            ),
        ),
    )
    report = DiffReport(
        skill_name="test-skill",
        home=str(mock_home),
        cwd=str(mock_home),
        found=True,
        baseline_path=str(mock_home / "skill_a"),
        copies=(c_base, c_other),
    )

    console = Console(file=io.StringIO(), force_terminal=False, width=120, color_system=None)
    render_diff(report, console=console)
    output = console.file.getvalue()  # type: ignore[attr-defined]

    assert "Diff: 'test-skill'" in output
    assert "Copies: 2" in output
    assert "= ~/skill_a [Variant A] (user, valid)  baseline (no diff shown)" in output
    assert "* ~/skill_b [Variant B] (project, valid)  1 file(s) differ" in output
    assert "--- SKILL.md" in output
    assert "+++ SKILL.md" in output


# --- 8. Dependency direction guard -----------------------------------------


def _check_module_imports(source_path: Path) -> list[str]:
    """Inspect imports in a Python source file and return forbidden dependencies."""
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    forbidden_prefixes = (
        "rich",
        "textual",
        "skill_lens.render",
        "skill_lens.core.paths",
    )
    violations: list[str] = []

    def check_name(name: str) -> None:
        for prefix in forbidden_prefixes:
            if name == prefix or name.startswith(f"{prefix}."):
                violations.append(name)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                check_name(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            check_name(node.module)
            for alias in node.names:
                check_name(f"{node.module}.{alias.name}")
    return violations


def test_presentation_dependency_direction() -> None:
    """skill_lens.presentation modules must not import rich, textual, render, or paths."""
    presentation_dir = Path(__file__).resolve().parent.parent / "skill_lens" / "presentation"
    py_files = list(presentation_dir.glob("*.py"))
    assert len(py_files) >= 3, "Expected at least __init__.py, state.py, and text.py"

    all_violations: dict[str, list[str]] = {}
    for py_file in py_files:
        violations = _check_module_imports(py_file)
        if violations:
            all_violations[py_file.name] = violations

    assert not all_violations, f"Found forbidden imports in presentation: {all_violations}"


def test_dependency_guard_fails_on_mutation(tmp_path: Path) -> None:
    """Demonstrate the dependency guard fails when a forbidden import is added."""
    bad_code_rich = "import rich\n"
    file_rich = tmp_path / "bad_rich.py"
    file_rich.write_text(bad_code_rich, encoding="utf-8")
    assert "rich" in _check_module_imports(file_rich)

    bad_code_render = "from skill_lens.render import render_diff\n"
    file_render = tmp_path / "bad_render.py"
    file_render.write_text(bad_code_render, encoding="utf-8")
    assert "skill_lens.render" in _check_module_imports(file_render)

    bad_code_paths = "from skill_lens.core import paths\n"
    file_paths = tmp_path / "bad_paths.py"
    file_paths.write_text(bad_code_paths, encoding="utf-8")
    assert "skill_lens.core.paths" in _check_module_imports(file_paths)
