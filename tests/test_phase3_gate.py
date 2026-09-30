"""Phase 3 gate: the ``diff`` data contract, pinned by a golden fixture.

The specification requires the machine-readable model to exist *before* any Rich
renderer: ``diff --json`` emits ``dumps(DiffReport)`` and a golden
``diff_*.json`` records exactly what it says. These tests therefore compare the
whole structure -- every field, at every level -- rather than a hand-picked
subset, so a silently dropped or renamed field cannot pass unnoticed.

The behavioural tests below pin the rules the specification states explicitly:
the index is already deduplicated, the fingerprint (not raw bytes) decides what
differs, only the valid set gets a Variant letter, an invalid copy is never the
baseline, unreadable copies are listed with no diff, and both truncation budgets
report what they dropped.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import pytest

import skill_lens.core.diff as diff_module
from skill_lens.core import paths
from skill_lens.core.diff import (
    MAX_CHANGED_LINES_PER_COPY,
    MAX_CHARS_PER_REPORT,
    build_diff_report,
)
from skill_lens.models import dumps
from skill_lens.models.diff import (
    DiffChange,
    DiffCopy,
    DiffFile,
    DiffHunk,
    DiffReport,
)
from skill_lens.models.enums import Scope
from skill_lens.models.parsing import ERR_DANGLING_SYMLINK, ERR_SYMLINK_CYCLE
from tests.fixtures.builders import make_skill, skill_markdown, write_skill, write_text
from tests.fixtures.scenarios import build_scenario, teardown_scenario

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"
GOLDEN_DIFF = GOLDEN_DIR / "diff_variant_hash_detection.json"


def _rel(value: object, home: Path) -> object:
    """Rewrite an absolute path as home-relative so a golden can pin it."""
    if isinstance(value, str) and value.startswith(str(home)):
        return Path(value).relative_to(home).as_posix()
    return value


def _normalize(payload: dict, home: Path) -> dict:
    """Home-relative form of a report, so the golden holds no machine paths."""
    normalized = dict(payload)
    for field in ("home", "cwd", "baseline_path"):
        normalized[field] = _rel(normalized[field], home)
    normalized["copies"] = [
        {**copy, "path": _rel(copy["path"], home)} for copy in payload["copies"]
    ]
    return normalized


def _changed_lines(copy: DiffCopy) -> int:
    return sum(
        1
        for file in copy.files
        for hunk in file.hunks
        for line in hunk.lines
        if line[:1] in ("-", "+")
    )


def _body_chars(report: DiffReport) -> int:
    return sum(
        len(line) + 1
        for copy in report.copies
        for file in copy.files
        for hunk in file.hunks
        for line in hunk.lines
    )


def _other(report: DiffReport) -> DiffCopy:
    """The first non-baseline copy of a report."""
    return next(copy for copy in report.copies if not copy.is_baseline)


# --- The golden contract ---------------------------------------------------


def test_diff_matches_the_golden(mock_home: Path) -> None:
    """The whole DiffReport, field by field, against the hand-written golden."""
    golden = json.loads(GOLDEN_DIFF.read_text(encoding="utf-8"))
    build_scenario("variant_hash_detection", mock_home)
    try:
        home = mock_home.resolve()
        report = build_diff_report("deploy", home, home)
        assert _normalize(report.to_dict(), home) == golden["diff"]
    finally:
        teardown_scenario("variant_hash_detection", mock_home)


def test_diff_json_is_canonical_and_sorted(mock_home: Path) -> None:
    """``dumps`` output is stable JSON with sorted keys, as the gate requires."""
    build_scenario("variant_hash_detection", mock_home)
    home = mock_home.resolve()
    text = dumps(build_diff_report("deploy", home, home).to_dict())
    assert text == json.dumps(json.loads(text), sort_keys=True, indent=2)


def test_diff_is_deterministic(mock_home: Path) -> None:
    build_scenario("variant_hash_detection", mock_home)
    home = mock_home.resolve()
    first = dumps(build_diff_report("deploy", home, home).to_dict())
    second = dumps(build_diff_report("deploy", home, home).to_dict())
    assert first == second


def test_diff_models_round_trip_through_dict() -> None:
    """Every model must survive ``to_dict`` -> ``from_dict`` unchanged."""
    report = DiffReport(
        skill_name="deploy",
        home="/home/dev",
        cwd="/home/dev",
        found=True,
        baseline_path="/home/dev/.claude/skills/deploy",
        copies=(
            DiffCopy(
                path="/home/dev/.claude/skills/deploy",
                scope=Scope.USER,
                parse_status="valid",
                is_valid=True,
                is_readable=True,
                is_baseline=True,
                variant_label="A",
                content_hash="sha256:aa",
            ),
            DiffCopy(
                path="/home/dev/.agents/skills/deploy",
                scope=Scope.USER,
                parse_status="valid",
                is_valid=True,
                is_readable=True,
                variant_label="B",
                content_hash="sha256:bb",
                files=(
                    DiffFile(
                        path="SKILL.md",
                        change=DiffChange.MODIFIED,
                        hunks=(DiffHunk(1, 1, 1, 1, ("-old", "+new")),),
                    ),
                ),
            ),
        ),
    )
    assert DiffReport.from_dict(report.to_dict()) == report


def test_the_diff_engine_imports_no_rich() -> None:
    """Step 2 of the plan: computation is pure, Rich is presentation only.

    Checked through the import statements rather than a text search, so the
    module may still *describe* the split in its docstring.
    """
    source = Path(diff_module.__file__).read_text(encoding="utf-8")
    imported: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert [name for name in imported if name.split(".")[0] == "rich"] == []


# --- Outcomes --------------------------------------------------------------


def test_a_name_that_exists_nowhere_is_not_an_error(mock_home: Path) -> None:
    """F-10, as ``why`` reports it: nothing found is a fact, not a failure."""
    build_scenario("claude_personal_beats_project", mock_home)
    home = mock_home.resolve()
    report = build_diff_report("no-such-skill", home, home)
    assert report.found is False
    assert report.copies == ()
    assert report.baseline_path is None
    assert report.notes, "a not-found answer must explain itself"
    assert report.has_differences is False


def test_one_canonical_copy_reached_by_symlinks_is_one_copy(mock_home: Path) -> None:
    """A three-link farm is one library, so there is nothing to diff.

    The index is already deduplicated by canonical target and ``diff`` must not
    re-implement that grouping.
    """
    build_scenario("symlink_farm_multi_agent", mock_home)
    home = mock_home.resolve()
    report = build_diff_report("shared", home, home)
    assert report.found is True
    assert len(report.copies) == 1
    assert report.copies[0].files == ()
    assert report.has_differences is False


def test_identical_copies_produce_no_diff(mock_home: Path) -> None:
    """Two distinct copies with the same bytes are not a difference."""
    home = mock_home.resolve()
    for root in (".claude/skills", ".agents/skills"):
        make_skill(home / root / "same", "same", "Identical copy.")
    report = build_diff_report("same", home, home)
    assert len(report.copies) == 2
    assert {copy.content_hash for copy in report.copies}.__len__() == 1
    assert report.has_differences is False


def test_line_endings_alone_do_not_produce_a_diff(mock_home: Path) -> None:
    """The fingerprint normalises ``\\r\\n``, so the diff must agree with it.

    A raw byte comparison here would report a difference that ``scan`` and
    ``why`` deny -- the F-16 contradiction, in a new place.
    """
    home = mock_home.resolve()
    body = "# Instructions\n\nDo the thing.\n"
    lf = skill_markdown("eol", "Line endings.", body)
    crlf = lf.replace("\n", "\r\n")
    write_skill(home / ".agents" / "skills" / "eol", lf)
    write_skill(home / ".claude" / "skills" / "eol", crlf)
    report = build_diff_report("eol", home, home)
    assert len(report.copies) == 2
    assert len({copy.content_hash for copy in report.copies}) == 1, (
        "the two copies must share one fingerprint"
    )
    assert report.has_differences is False


# --- Baseline --------------------------------------------------------------


def test_the_baseline_follows_scope_specificity(mock_home: Path) -> None:
    """Variant A is chosen by scope specificity: the project copy wins.

    Both copies are discovered, so the choice is real and not an artefact of one
    of them being invisible.
    """
    home = mock_home.resolve()
    (home / "project" / ".git").mkdir(parents=True)
    make_skill(home / ".claude" / "skills" / "scoped", "scoped", "Global copy.")
    make_skill(
        home / "project" / ".claude" / "skills" / "scoped",
        "scoped",
        "Project copy.",
        body="# Instructions\n\nProject body.\n",
    )
    report = build_diff_report("scoped", home / "project", home)
    assert len(report.copies) == 2
    assert report.baseline_path == str(home / "project" / ".claude" / "skills" / "scoped")
    baseline = next(copy for copy in report.copies if copy.is_baseline)
    assert baseline.scope is Scope.PROJECT
    assert baseline.variant_label == "A"
    assert report.copies[0].is_baseline, "the baseline leads the report"


def test_a_readable_but_invalid_copy_is_diffed_without_a_letter(mock_home: Path) -> None:
    """A broken copy is the one worth inspecting, so it takes part in the diff.

    It still gets no Variant letter -- only the valid set is labelled -- and it
    is never the baseline.
    """
    home = mock_home.resolve()
    make_skill(
        home / ".claude" / "skills" / "broken",
        "broken",
        "Valid copy.",
        body="# Instructions\n\nGood body.\n",
    )
    write_skill(
        home / ".agents" / "skills" / "broken",
        "---\nname: broken\n---\n# Body without a description.\n",
    )
    report = build_diff_report("broken", home, home)
    baseline = next(copy for copy in report.copies if copy.is_baseline)
    assert baseline.is_valid is True
    assert baseline.variant_label == "A"

    invalid = _other(report)
    assert invalid.is_valid is False
    assert invalid.is_readable is True, "a readable copy is a diff participant"
    assert invalid.variant_label is None, "an invalid copy gets no Variant letter"
    assert invalid.files, "the invalid copy must actually be diffed"


def test_no_baseline_is_reported_when_no_copy_is_valid(mock_home: Path) -> None:
    """With no valid copy there is no Variant A, so nothing is invented."""
    home = mock_home.resolve()
    for root in (".claude/skills", ".agents/skills"):
        write_skill(home / root / "junk", "---\nname: junk\n---\n# no description\n")
    report = build_diff_report("junk", home, home)
    assert report.found is True
    assert report.baseline_path is None
    assert report.notes, "the missing baseline must be explained"
    assert all(copy.variant_label is None for copy in report.copies)
    assert report.has_differences is False


# --- Unreadable copies -----------------------------------------------------


def test_a_symlink_cycle_is_listed_with_no_diff(mock_home: Path) -> None:
    build_scenario("symlink_cycle_guard", mock_home)
    home = mock_home.resolve()
    report = build_diff_report("cycle_a", home, home)
    assert report.found is True
    copy = report.copies[0]
    assert copy.is_readable is False
    assert copy.error == ERR_SYMLINK_CYCLE
    assert copy.files == ()


def test_a_dangling_symlink_reports_the_machine_readable_code(mock_home: Path) -> None:
    home = mock_home.resolve()
    link = home / ".claude" / "skills" / "ghost"
    link.parent.mkdir(parents=True)
    os.symlink(home / "nowhere", link, target_is_directory=True)
    report = build_diff_report("ghost", home, home)
    copy = report.copies[0]
    assert copy.is_readable is False
    assert copy.error == ERR_DANGLING_SYMLINK
    assert copy.files == ()


# --- File-level behaviour --------------------------------------------------


def test_added_removed_and_modified_files_are_all_reported(mock_home: Path) -> None:
    """Files match by relative path, so a rename shows up as removed + added."""
    home = mock_home.resolve()
    baseline = home / ".claude" / "skills" / "extra"
    other = home / ".agents" / "skills" / "extra"
    make_skill(baseline, "extra", "Copy A.")
    make_skill(other, "extra", "Copy B.", body="# Instructions\n\nDifferent.\n")
    write_text(baseline / "notes.md", "Only the baseline has this.\n")
    write_text(other / "fresh.md", "Only the other copy has this.\n")

    report = build_diff_report("extra", home, home)
    changes = {file.path: file.change for file in _other(report).files}
    assert changes["SKILL.md"] == DiffChange.MODIFIED
    assert changes["notes.md"] == DiffChange.REMOVED
    assert changes["fresh.md"] == DiffChange.ADDED


def test_added_text_files_show_their_content(mock_home: Path) -> None:
    """A unified diff of a new file is all-added lines, not an empty hunk list."""
    home = mock_home.resolve()
    make_skill(home / ".claude" / "skills" / "grow", "grow", "Copy A.")
    make_skill(home / ".agents" / "skills" / "grow", "grow", "Copy A.")
    write_text(home / ".agents" / "skills" / "grow" / "added.txt", "line one\nline two\n")
    report = build_diff_report("grow", home, home)
    added = next(file for file in _other(report).files if file.path == "added.txt")
    assert added.change is DiffChange.ADDED
    assert [line for hunk in added.hunks for line in hunk.lines] == [
        "+line one",
        "+line two",
    ]


def test_binary_files_are_reported_but_never_printed(mock_home: Path) -> None:
    home = mock_home.resolve()
    baseline = home / ".claude" / "skills" / "blob"
    other = home / ".agents" / "skills" / "blob"
    make_skill(baseline, "blob", "Copy A.")
    make_skill(other, "blob", "Copy B.", body="# Instructions\n\nDifferent.\n")
    (baseline / "asset.bin").write_bytes(b"\xff\xfe\x00\x01")
    (other / "asset.bin").write_bytes(b"\xff\xfe\x00\x02")

    report = build_diff_report("blob", home, home)
    binary = next(file for file in _other(report).files if file.path == "asset.bin")
    assert binary.is_binary is True
    assert binary.hunks == (), "binary content is never printed"


def test_identical_binary_files_are_not_a_difference(mock_home: Path) -> None:
    home = mock_home.resolve()
    for root in (".claude/skills", ".agents/skills"):
        make_skill(home / root / "blobsame", "blobsame", "Copy.")
        (home / root / "blobsame" / "asset.bin").write_bytes(b"\xff\xfe\x00\x01")
    report = build_diff_report("blobsame", home, home)
    assert report.has_differences is False


# --- Truncation ------------------------------------------------------------


def test_the_per_copy_line_budget_truncates_and_reports_what_it_dropped(
    mock_home: Path,
) -> None:
    home = mock_home.resolve()
    lines = 600
    make_skill(home / ".claude" / "skills" / "big", "big", "Copy A.")
    make_skill(home / ".agents" / "skills" / "big", "big", "Copy B.")
    write_text(
        home / ".claude" / "skills" / "big" / "body.txt",
        "".join(f"old {index}\n" for index in range(lines)),
    )
    write_text(
        home / ".agents" / "skills" / "big" / "body.txt",
        "".join(f"new {index}\n" for index in range(lines)),
    )

    report = build_diff_report("big", home, home)
    other = _other(report)
    emitted = _changed_lines(other)
    assert emitted <= MAX_CHANGED_LINES_PER_COPY
    # SKILL.md's description differs too: one removed and one added line.
    assert emitted + other.omitted_lines == 2 + 2 * lines
    assert other.truncated is True
    assert report.truncated is True
    assert report.omitted_chars > 0


def test_the_report_character_budget_truncates_the_whole_report(mock_home: Path) -> None:
    """Few changed lines but very long ones: only the character budget can bite."""
    home = mock_home.resolve()
    lines = 100
    make_skill(home / ".claude" / "skills" / "wide", "wide", "Copy A.")
    make_skill(home / ".agents" / "skills" / "wide", "wide", "Copy B.")
    write_text(
        home / ".claude" / "skills" / "wide" / "wide.txt",
        "".join("o" * 250 + f"{index}\n" for index in range(lines)),
    )
    write_text(
        home / ".agents" / "skills" / "wide" / "wide.txt",
        "".join("n" * 250 + f"{index}\n" for index in range(lines)),
    )

    report = build_diff_report("wide", home, home)
    assert _body_chars(report) <= MAX_CHARS_PER_REPORT
    assert report.truncated is True
    assert report.omitted_chars > 0
    assert _other(report).truncated is True


def test_a_truncated_hunk_still_adds_up(mock_home: Path) -> None:
    """A truncated hunk's header must describe the lines that survived.

    Otherwise the printed diff would advertise counts it does not contain.
    """
    home = mock_home.resolve()
    lines = 600
    make_skill(home / ".claude" / "skills" / "counted", "counted", "Copy A.")
    make_skill(home / ".agents" / "skills" / "counted", "counted", "Copy B.")
    write_text(
        home / ".claude" / "skills" / "counted" / "body.txt",
        "".join(f"old {index}\n" for index in range(lines)),
    )
    write_text(
        home / ".agents" / "skills" / "counted" / "body.txt",
        "".join(f"new {index}\n" for index in range(lines)),
    )

    report = build_diff_report("counted", home, home)
    for file in _other(report).files:
        for hunk in file.hunks:
            assert hunk.old_count == sum(1 for line in hunk.lines if line[:1] in (" ", "-"))
            assert hunk.new_count == sum(1 for line in hunk.lines if line[:1] in (" ", "+"))


def test_an_ordinary_diff_is_not_truncated(mock_home: Path) -> None:
    """The budgets must not touch a small, ordinary diff."""
    build_scenario("variant_hash_detection", mock_home)
    home = mock_home.resolve()
    report = build_diff_report("deploy", home, home)
    assert report.truncated is False
    assert report.omitted_chars == 0
    assert all(copy.truncated is False for copy in report.copies)
    assert all(copy.omitted_lines == 0 for copy in report.copies)


@pytest.mark.parametrize("name", ["symlink_farm_multi_agent", "variant_hash_detection"])
def test_diff_never_writes_to_the_filesystem(name: str, mock_home: Path) -> None:
    """Skill Lens is read-only (AGENTS.md rule 1): a diff changes nothing."""
    build_scenario(name, mock_home)
    before = sorted(path.relative_to(mock_home).as_posix() for path in mock_home.rglob("*"))
    home = mock_home.resolve()
    for skill in ("shared", "deploy"):
        build_diff_report(skill, home, home)
    after = sorted(path.relative_to(mock_home).as_posix() for path in mock_home.rglob("*"))
    assert before == after
    paths.set_sandbox(None)
