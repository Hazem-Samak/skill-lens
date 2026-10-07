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
from skill_lens.core.discovery import DiscoveredEntry
from skill_lens.core.snapshot_models import CapturedFile
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

    Otherwise the printed diff would advertise counts it does not contain. The
    starts matter as much as the counts: a range that truncation emptied must
    name the line *before* it, so for a diff beginning at line 1 an emptied side
    starts at 0, never at 1.
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
            if hunk.old_count == 0:
                assert hunk.old_start == 0, "an empty old range names the line before it"
            if hunk.new_count == 0:
                assert hunk.new_start == 0, "an empty new range names the line before it"


def test_recount_steps_back_when_truncation_empties_a_range() -> None:
    """A range emptied by truncation must name the line before it.

    The stored start was computed for the original count. Leaving it alone renders
    a truncated all-deletions hunk as ``+1,0``, which a standard diff reader
    rejects; the correct header is ``+0,0``.
    """
    hunk = DiffHunk(
        old_start=1,
        old_count=2,
        new_start=1,
        new_count=2,
        lines=("-old1", "-old2", "+new1", "+new2"),
    )

    kept = diff_module._recount(hunk, ["-old1", "-old2"])  # the added lines were cut
    assert (kept.old_start, kept.old_count) == (1, 2)
    assert (kept.new_start, kept.new_count) == (0, 0)

    intact = diff_module._recount(hunk, list(hunk.lines))
    assert (intact.old_start, intact.old_count) == (1, 2)
    assert (intact.new_start, intact.new_count) == (1, 2)


def test_recount_does_not_step_back_a_range_that_was_already_empty() -> None:
    """Only a range *emptied by truncation* moves back -- never one that was empty."""
    hunk = DiffHunk(old_start=0, old_count=0, new_start=1, new_count=1, lines=("+new",))
    kept = diff_module._recount(hunk, ["+new"])
    assert (kept.old_start, kept.old_count) == (0, 0)
    assert (kept.new_start, kept.new_count) == (1, 1)


def test_multi_hunk_truncation_never_emits_a_hunk_without_changes(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hunk with no changed lines is not a diff, so it must never be printed.

    When the changed-line budget is exhausted *exactly* at a hunk boundary, the
    next hunk's leading context lines still fit -- context costs no changed lines
    -- so a budget loop that only counts changes emits a hunk showing none.
    """
    monkeypatch.setattr(diff_module, "MAX_CHANGED_LINES_PER_COPY", 2)
    home = mock_home.resolve()
    # Identical descriptions, so only body.txt differs and the budget arithmetic
    # is not disturbed by the SKILL.md change.
    make_skill(home / ".claude" / "skills" / "multi", "multi", "Same.")
    make_skill(home / ".agents" / "skills" / "multi", "multi", "Same.")
    old = [f"line {index}" for index in range(40)]
    new = list(old)
    new[0] = "LINE 0"
    new[19] = "LINE 19"
    write_text(home / ".claude" / "skills" / "multi" / "body.txt", "\n".join(old) + "\n")
    write_text(home / ".agents" / "skills" / "multi" / "body.txt", "\n".join(new) + "\n")

    other = _other(build_diff_report("multi", home, home))
    hunks = [hunk for file in other.files for hunk in file.hunks]
    assert hunks, "the first hunk fits the budget and must be kept"
    for hunk in hunks:
        assert any(line[:1] in ("-", "+") for line in hunk.lines), (
            f"hunk at old line {hunk.old_start} shows no change: {list(hunk.lines)}"
        )
    # The second hunk was dropped, so its changes must be reported as omitted.
    assert other.truncated is True
    assert other.omitted_lines == 2


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


# ---------------------------------------------------------------------------
# C2 Diff Tests: captured files, explicit emptiness, completeness, falsey mapping
# ---------------------------------------------------------------------------


def _capture_entry_files(entry: DiscoveredEntry) -> tuple[CapturedFile, ...]:
    from skill_lens.core.hasher import hash_bytes, iter_files
    from skill_lens.core.snapshot_models import CapturedFile

    root = Path(entry.canonical_path or entry.entrypoint_path)
    if not root.exists():
        return ()
    if not root.is_dir():
        data = root.read_bytes()
        return (CapturedFile(relative_path=root.name, data=data, fingerprint=hash_bytes(data)),)
    files = []
    for rel in iter_files(root):
        data = (root / rel).read_bytes()
        files.append(
            CapturedFile(
                relative_path=rel.as_posix(),
                data=data,
                fingerprint=hash_bytes(data),
            )
        )
    return tuple(files)


def test_diff_captured_parity_matches_live_reports(mock_home: Path, tmp_path: Path) -> None:
    """Captured diff reports match live reports across binaries, CRLF, BOM, unreadable, etc."""
    from skill_lens.core.diff import _NO_BASELINE_NOTE
    from skill_lens.core.discovery import canonical_key, discover
    from skill_lens.core.snapshot_models import FrozenDiscoveryIndex
    from skill_lens.registry.loader import load_registry

    # 1. Differing directory copies: CRLF differing content, lone-CR, BOM bytes, NUL, binary
    dir_a = mock_home / ".claude" / "skills" / "complex-diff"
    make_skill(dir_a, name="complex-diff", description="Variant A", body="Line 1\nLine 2\nLine 3\n")
    (dir_a / "sub").mkdir(parents=True, exist_ok=True)
    (dir_a / "sub" / "crlf_diff.txt").write_bytes(b"nested content A\r\nCRLF ending\r\n")
    (dir_a / "lone_cr.txt").write_bytes(b"alpha\rbeta A\n")
    (dir_a / "bom.txt").write_bytes(b"\xef\xbb\xbfBOM header A\n")
    (dir_a / "nul.txt").write_bytes(b"Text with \x00 NUL A\n")
    (dir_a / "bin.dat").write_bytes(b"\xff\xfe\x00\x00Invalid UTF8 binary A")

    dir_b = mock_home / ".agents" / "skills" / "complex-diff"
    make_skill(
        dir_b,
        name="complex-diff",
        description="Variant B",
        body="Line 1\nLine 2 modified\nLine 3\n",
    )
    (dir_b / "sub").mkdir(parents=True, exist_ok=True)
    (dir_b / "sub" / "crlf_diff.txt").write_bytes(b"nested content B\r\nCRLF ending\r\n")
    (dir_b / "lone_cr.txt").write_bytes(b"alpha\rbeta B\n")
    (dir_b / "bom.txt").write_bytes(b"\xef\xbb\xbfBOM header B\n")
    (dir_b / "nul.txt").write_bytes(b"Text with \x00 NUL B\n")
    (dir_b / "extra.txt").write_bytes(b"extra file in B\n")
    (dir_b / "bin.dat").write_bytes(b"\xff\xfe\x00\x01Differing binary B")

    # 2. Standalone file skill
    sa_a = mock_home / ".claude" / "skills" / "standalone-diff.md"
    sa_a.write_text("---\nname: standalone-diff\ndescription: A\n---\nBody A\n", encoding="utf-8")
    sa_b = mock_home / ".agents" / "skills" / "standalone-diff.md"
    sa_b.write_text("---\nname: standalone-diff\ndescription: B\n---\nBody B\n", encoding="utf-8")

    # 3. No-baseline skill (both copies invalid frontmatter)
    nb_a = mock_home / ".claude" / "skills" / "nobaseline-diff"
    write_text(nb_a / "SKILL.md", "---\nname: [malformed\n---\n")
    nb_b = mock_home / ".agents" / "skills" / "nobaseline-diff"
    write_text(nb_b / "SKILL.md", "---\nname: [malformed2\n---\n")

    # 4. Unreadable / dangling symlink copy
    un_a = mock_home / ".claude" / "skills" / "unreadable-diff"
    un_a.symlink_to(mock_home / "nonexistent_target")
    un_b = mock_home / ".agents" / "skills" / "unreadable-diff"
    make_skill(un_b, name="unreadable-diff", description="Valid copy B")

    # 5. Line truncation budget (exceeds MAX_CHANGED_LINES_PER_COPY = 400)
    tr_lines_a = mock_home / ".claude" / "skills" / "trunc-lines"
    make_skill(
        tr_lines_a,
        name="trunc-lines",
        description="A",
        body="".join(f"line {i}\n" for i in range(450)),
    )
    tr_lines_b = mock_home / ".agents" / "skills" / "trunc-lines"
    make_skill(
        tr_lines_b,
        name="trunc-lines",
        description="B",
        body="".join(f"modified {i}\n" for i in range(450)),
    )

    # 6. Char truncation budget (exceeds MAX_CHARS_PER_REPORT = 20_000)
    tr_chars_a = mock_home / ".claude" / "skills" / "trunc-chars"
    make_skill(
        tr_chars_a,
        name="trunc-chars",
        description="A",
        body="".join(f"line {i:03d} " + "x" * 250 + "\n" for i in range(120)),
    )
    tr_chars_b = mock_home / ".agents" / "skills" / "trunc-chars"
    make_skill(
        tr_chars_b,
        name="trunc-chars",
        description="B",
        body="".join(f"line {i:03d} " + "y" * 250 + "\n" for i in range(120)),
    )

    registry = load_registry()
    index = discover(mock_home, tmp_path, registry)
    frozen_idx = FrozenDiscoveryIndex(
        home=str(mock_home), cwd=str(tmp_path), entries=tuple(index.entries), unreadable_roots=()
    )

    captured_files = {canonical_key(e): _capture_entry_files(e) for e in index.entries}

    skills_to_test = (
        "complex-diff",
        "standalone-diff",
        "nobaseline-diff",
        "unreadable-diff",
        "trunc-lines",
        "trunc-chars",
    )

    for skill_name in skills_to_test:
        live_rep = build_diff_report(
            skill_name, tmp_path, mock_home, index=index, registry=registry
        )
        captured_rep = build_diff_report(
            skill_name,
            tmp_path,
            mock_home,
            index=index,
            registry=registry,
            captured_files=captured_files,
        )
        frozen_rep = build_diff_report(
            skill_name,
            tmp_path,
            mock_home,
            index=frozen_idx,
            registry=registry,
            captured_files=captured_files,
        )

        assert captured_rep == live_rep
        assert frozen_rep == live_rep
        assert captured_rep.to_dict() == live_rep.to_dict()
        assert dumps(captured_rep.to_dict()) == dumps(live_rep.to_dict())

    # Specific assertion proofs for distinct paths:
    # No-baseline notes
    rep_nb = build_diff_report(
        "nobaseline-diff",
        tmp_path,
        mock_home,
        index=index,
        registry=registry,
        captured_files=captured_files,
    )
    assert _NO_BASELINE_NOTE in rep_nb.notes

    # Unreadable copy accounting
    rep_un = build_diff_report(
        "unreadable-diff",
        tmp_path,
        mock_home,
        index=index,
        registry=registry,
        captured_files=captured_files,
    )
    assert any(
        c.files == () and c.is_readable is False and c.error is not None for c in rep_un.copies
    )

    # Line truncation accounting
    rep_tl = build_diff_report(
        "trunc-lines",
        tmp_path,
        mock_home,
        index=index,
        registry=registry,
        captured_files=captured_files,
    )
    assert any(c.truncated is True and c.omitted_lines > 0 for c in rep_tl.copies)

    # Char truncation accounting
    rep_tc = build_diff_report(
        "trunc-chars",
        tmp_path,
        mock_home,
        index=index,
        registry=registry,
        captured_files=captured_files,
    )
    assert rep_tc.truncated is True and rep_tc.omitted_chars > 0

    # Assert no binary payload entered printable hunks
    rep_cd = build_diff_report(
        "complex-diff",
        tmp_path,
        mock_home,
        index=index,
        registry=registry,
        captured_files=captured_files,
    )
    for copy in rep_cd.copies:
        for diff_file in copy.files:
            for hunk in diff_file.hunks:
                for line in hunk.lines:
                    assert "\xff\xfe" not in line


def test_diff_explicit_empty_tuple_remains_empty_under_patched_collector(
    mock_home: Path, tmp_path: Path
) -> None:
    """Present empty tuple remains empty under a patched live collector."""
    from unittest.mock import patch

    from skill_lens.core.discovery import canonical_key, discover
    from skill_lens.registry.loader import load_registry

    dir_a = mock_home / ".claude" / "skills" / "empty-copy"
    make_skill(dir_a, name="empty-copy", description="Empty A")
    dir_b = mock_home / ".codex" / "skills" / "empty-copy"
    make_skill(dir_b, name="empty-copy", description="Empty B")

    registry = load_registry()
    index = discover(mock_home, tmp_path, registry)
    captured_files = {
        canonical_key(entry): () for entry in index.entries if entry.name == "empty-copy"
    }

    with patch(
        "skill_lens.core.diff._collect",
        side_effect=AssertionError("Live collector must not be called"),
    ):
        rep = build_diff_report(
            "empty-copy",
            tmp_path,
            mock_home,
            index=index,
            registry=registry,
            captured_files=captured_files,
        )
        assert rep.found is True
        assert len(rep.copies) == 2
        assert all(copy.files == () for copy in rep.copies)


def test_diff_missing_selected_copy_key_raises_value_error(mock_home: Path, tmp_path: Path) -> None:
    """An absent copy key raises ValueError, across all shortcut paths and unreadable copies."""
    from skill_lens.core.discovery import canonical_key, discover
    from skill_lens.registry.loader import load_registry

    # 1. Single copy shortcut
    dir_single = mock_home / ".claude" / "skills" / "single-skill"
    make_skill(dir_single, name="single-skill", description="Single")

    # 2. Equal hash shortcut (byte identical in two places)
    dir_eq1 = mock_home / ".claude" / "skills" / "equal-skill"
    make_skill(dir_eq1, name="equal-skill", description="Equal")
    dir_eq2 = mock_home / ".agents" / "skills" / "equal-skill"
    make_skill(dir_eq2, name="equal-skill", description="Equal")

    # 3. No baseline shortcut (both invalid, so no Variant A baseline)
    dir_nb1 = mock_home / ".claude" / "skills" / "nobaseline-skill"
    write_text(dir_nb1 / "SKILL.md", "---\nname: [unclosed\n---\n")
    dir_nb2 = mock_home / ".agents" / "skills" / "nobaseline-skill"
    write_text(dir_nb2 / "SKILL.md", "---\nname: [unclosed2\n---\n")

    # 4. Unreadable shortcut (dangling symlink)
    dir_dang1 = mock_home / ".claude" / "skills" / "dangling-skill"
    dir_dang1.symlink_to(mock_home / "nonexistent_target")
    dir_dang2 = mock_home / ".agents" / "skills" / "dangling-skill"
    make_skill(dir_dang2, name="dangling-skill", description="Valid Dangling Sibling")

    registry = load_registry()
    index = discover(mock_home, tmp_path, registry)

    # All these shortcut cases must raise ValueError when their key is missing from captured_files
    for skill_name in ("single-skill", "equal-skill", "nobaseline-skill", "dangling-skill"):
        entries = [e for e in index.entries if e.name == skill_name]
        assert entries
        all_captured = {canonical_key(e): _capture_entry_files(e) for e in entries}

        for target_entry in entries:
            target_key = canonical_key(target_entry)
            partial_captured = {k: v for k, v in all_captured.items() if k != target_key}
            with pytest.raises(ValueError, match="missing captured files"):
                build_diff_report(
                    skill_name,
                    tmp_path,
                    mock_home,
                    index=index,
                    registry=registry,
                    captured_files=partial_captured,
                )


def test_diff_empty_supplied_index_and_empty_files_returns_not_found(
    mock_home: Path, tmp_path: Path
) -> None:
    """Empty supplied index and {} files against populated disk returns not-found without reads."""
    from unittest.mock import patch

    from skill_lens.core.discovery import DiscoveryIndex
    from skill_lens.core.snapshot_models import FrozenDiscoveryIndex
    from skill_lens.registry.loader import load_registry

    skill_dir = mock_home / ".claude" / "skills" / "disk-skill"
    make_skill(skill_dir, name="disk-skill", description="On disk")

    registry = load_registry()
    empty_index = DiscoveryIndex(
        home=str(mock_home), cwd=str(tmp_path), entries=[], unreadable_roots=[]
    )
    frozen_idx = FrozenDiscoveryIndex(
        home=str(mock_home), cwd=str(tmp_path), entries=(), unreadable_roots=()
    )

    with (
        patch(
            "skill_lens.core.diff.load_registry", side_effect=AssertionError("load_registry banned")
        ),
        patch("skill_lens.core.diff.discover", side_effect=AssertionError("discover banned")),
        patch("skill_lens.core.diff._copy_files", side_effect=AssertionError("_copy_files banned")),
    ):
        rep = build_diff_report(
            "disk-skill",
            tmp_path,
            mock_home,
            index=empty_index,
            registry=registry,
            captured_files={},
        )
        assert rep.found is False

        # Companion input violations when captured_files is provided
        for cf_input in ({}, {"arbitrary_key": ()}):
            with pytest.raises(
                ValueError, match=r"^index must be supplied when captured_files is provided$"
            ):
                build_diff_report(
                    "disk-skill",
                    tmp_path,
                    mock_home,
                    index=None,
                    registry=registry,
                    captured_files=cf_input,
                )
            with pytest.raises(
                ValueError, match=r"^registry must be supplied when captured_files is provided$"
            ):
                build_diff_report(
                    "disk-skill",
                    tmp_path,
                    mock_home,
                    index=empty_index,
                    registry=None,
                    captured_files=cf_input,
                )

        # Frozen index violations
        with pytest.raises(
            ValueError,
            match=(
                r"^(registry|captured_files) must be supplied "
                r"when index is a FrozenDiscoveryIndex$"
            ),
        ):
            build_diff_report(
                "disk-skill",
                tmp_path,
                mock_home,
                index=frozen_idx,
                registry=None,
                captured_files=None,
            )
        with pytest.raises(
            ValueError,
            match=r"^captured_files must be supplied when index is a FrozenDiscoveryIndex$",
        ):
            build_diff_report(
                "disk-skill",
                tmp_path,
                mock_home,
                index=frozen_idx,
                registry=registry,
                captured_files=None,
            )


def test_diff_copy_files_private_contract(mock_home: Path, tmp_path: Path) -> None:
    """Unit test of _copy_files: missing key raises, present empty tuple returns {}, pinned hash."""
    from skill_lens.core.diff import _copy_files
    from skill_lens.core.discovery import canonical_key, discover
    from skill_lens.core.snapshot_models import CapturedFile
    from skill_lens.registry.loader import load_registry

    skill_dir = mock_home / ".claude" / "skills" / "private-copy-test"
    make_skill(skill_dir, name="private-copy-test", description="Test")

    registry = load_registry()
    index = discover(mock_home, tmp_path, registry)
    entry = next(e for e in index.entries if e.name == "private-copy-test")
    key = canonical_key(entry)

    # 1. Missing key raises ValueError
    with pytest.raises(ValueError, match=r"^missing captured files for key "):
        _copy_files(entry, captured_files={})

    # 2. Present empty tuple returns empty dict
    assert _copy_files(entry, captured_files={key: ()}) == {}

    # 3. CapturedFile uses cf.fingerprint without re-hashing
    cf = CapturedFile(relative_path="SKILL.md", data=b"hello world", fingerprint="pinned-fp-1234")
    out = _copy_files(entry, captured_files={key: (cf,)})
    assert "SKILL.md" in out
    assert out["SKILL.md"].fingerprint == "pinned-fp-1234"
    assert out["SKILL.md"].text == "hello world"


def test_diff_falsey_mapping_exercises_captured_branch_without_live_reads(
    mock_home: Path, tmp_path: Path
) -> None:
    """Populated Mapping with __bool__()==False on differing copies uses real _copy_files."""
    from unittest.mock import patch

    from skill_lens.core.discovery import canonical_key, discover
    from skill_lens.registry.loader import load_registry

    dir_a = mock_home / ".claude" / "skills" / "diff-skill"
    make_skill(dir_a, name="diff-skill", description="A", body="Line A\n")
    dir_b = mock_home / ".agents" / "skills" / "diff-skill"
    make_skill(dir_b, name="diff-skill", description="B", body="Line B\n")

    registry = load_registry()
    index = discover(mock_home, tmp_path, registry)
    entries = [e for e in index.entries if e.name == "diff-skill"]
    assert len(entries) == 2

    captured_files = {canonical_key(e): _capture_entry_files(e) for e in entries}

    class FalseyMap(dict):
        def __bool__(self) -> bool:
            return False

    falsey_files = FalseyMap(captured_files)
    assert bool(falsey_files) is False
    assert len(falsey_files) == 2

    expected_rep = build_diff_report(
        "diff-skill", tmp_path, mock_home, index=index, registry=registry
    )

    # Within report-call patch context, ban live collector/probe symbols.
    # DO NOT patch _copy_files itself: real new branch is under test!
    with (
        patch("skill_lens.core.diff._collect", side_effect=AssertionError("_collect banned")),
        patch(
            "skill_lens.core.diff._read_normalized",
            side_effect=AssertionError("_read_normalized banned"),
        ),
        patch("skill_lens.core.diff.iter_files", side_effect=AssertionError("iter_files banned")),
        patch("skill_lens.core.diff.hash_file", side_effect=AssertionError("hash_file banned")),
        patch("pathlib.Path.is_dir", side_effect=AssertionError("Path.is_dir banned")),
    ):
        rep = build_diff_report(
            "diff-skill",
            tmp_path,
            mock_home,
            index=index,
            registry=registry,
            captured_files=falsey_files,
        )
        assert rep == expected_rep


def test_diff_empty_registry_with_supplied_index_bans_load_registry(
    mock_home: Path, tmp_path: Path
) -> None:
    """Empty registry with supplied index must not call load_registry."""
    from unittest.mock import patch

    from skill_lens.core.discovery import canonical_key, discover

    dir_a = mock_home / ".claude" / "skills" / "reg-skill"
    make_skill(dir_a, name="reg-skill", description="A", body="Line A\n")
    dir_b = mock_home / ".agents" / "skills" / "reg-skill"
    make_skill(dir_b, name="reg-skill", description="B", body="Line B\n")

    index = discover(mock_home, tmp_path)
    entries = [e for e in index.entries if e.name == "reg-skill"]
    captured_files = {canonical_key(e): _capture_entry_files(e) for e in entries}

    expected_rep = build_diff_report(
        "reg-skill", tmp_path, mock_home, index=index, captured_files=captured_files, registry={}
    )

    with patch(
        "skill_lens.core.diff.load_registry", side_effect=AssertionError("load_registry banned")
    ):
        rep = build_diff_report(
            "reg-skill",
            tmp_path,
            mock_home,
            index=index,
            registry={},
            captured_files=captured_files,
        )
        assert rep == expected_rep
