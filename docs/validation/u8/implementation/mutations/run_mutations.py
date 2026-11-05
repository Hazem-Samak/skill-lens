#!/usr/bin/env python3
"""U8 mutation campaign runner.

Every case runs in a disposable copy outside the reviewed checkout:

    control before  -> expected pass
    mutation        -> expected meaningful assertion failure
    restore         -> expected pass

The reviewed checkout is never edited. Logs, commands, exit statuses and the
exact mutation text are written beside this script.

Run from the repository root with the project virtual environment:

    .venv/bin/python docs/validation/u8/implementation/mutations/run_mutations.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[5]
OUTPUT_DIR = Path(__file__).resolve().parent
PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
COPY_ITEMS = ("skill_lens", "tests", "pyproject.toml")


@dataclass(frozen=True)
class Edit:
    path: str
    old: str
    new: str


@dataclass(frozen=True)
class MutationCase:
    case_id: str
    category: str
    edits: tuple[Edit, ...]
    test: str
    expected_failure: str


CASES: tuple[MutationCase, ...] = (
    MutationCase(
        case_id="duplicate-help-stacking",
        category="Duplicate Help stacking",
        edits=(
            Edit(
                "skill_lens/tui/app.py",
                """        if isinstance(self.screen, HelpScreen):
            return
        origin = self.screen
""",
                """        if isinstance(self.screen, HelpScreen):
            self.push_screen(HelpScreen(self.screen.context, self.controller))
            return
        origin = self.screen
""",
            ),
        ),
        test="tests/test_tui_help.py::test_help_does_not_stack_and_stale_instance_cannot_close_a_newer_help",
        expected_failure="assert app.screen is first",
    ),
    MutationCase(
        case_id="covered-key-leakage",
        category="Covered-key leakage",
        edits=(
            Edit(
                "skill_lens/tui/help.py",
                """        Binding("r", "app.refresh", "Refresh", show=True),
""",
                """        Binding("r", "app.refresh", "Refresh", show=True),
        Binding("j", "leak_down", "Leak", show=False),
""",
            ),
            Edit(
                "skill_lens/tui/help.py",
                """    def action_dismiss_help(self) -> None:
""",
                """    def action_leak_down(self) -> None:
        key = self.app.controller.selected_key
        if key is not None:
            self.app.open_why(key, None)

    def action_dismiss_help(self) -> None:
""",
            ),
        ),
        test="tests/test_tui_help.py::test_hidden_screen_actions_cannot_leak_through_help",
        expected_failure="assert app.controller.selected_key == selection_before",
    ),
    MutationCase(
        case_id="lost-input-focus",
        category="Lost Input focus",
        edits=(
            Edit(
                "skill_lens/tui/home.py",
                """        target = self._help_focus
        if target is not None and target.can_focus and target.is_mounted and target.display:
            target.focus()
        elif table.can_focus and table.display:
            table.focus()
""",
                """        table.focus()
""",
            ),
        ),
        test="tests/test_tui_help.py::test_home_filter_typing_is_literal_and_f1_preserves_text_and_cursor",
        expected_failure="assert app.focused is filter_input",
    ),
    MutationCase(
        case_id="ignored-diff-suspension",
        category="Ignored Diff suspension",
        edits=(
            Edit(
                "skill_lens/tui/diff.py",
                """        view = self._json_view_or_none()
        self._help_json_scroll = int(view.scroll_offset.y) if view is not None else 0
        self._cancel_owned_token()
""",
                """        view = self._json_view_or_none()
        self._help_json_scroll = int(view.scroll_offset.y) if view is not None else 0
""",
            ),
        ),
        test="tests/test_tui_help.py::test_diff_job_is_suspended_and_restarted_once",
        expected_failure="assert event.is_set()",
    ),
    MutationCase(
        case_id="ignored-compare-suspension",
        category="Ignored Compare suspension",
        edits=(
            Edit(
                "skill_lens/tui/compare.py",
                """        view = self._json_view_or_none()
        self._help_json_scroll = int(view.scroll_offset.y) if view is not None else 0
        self._cancel_owned_token()
""",
                """        view = self._json_view_or_none()
        self._help_json_scroll = int(view.scroll_offset.y) if view is not None else 0
""",
            ),
        ),
        test="tests/test_tui_help.py::test_compare_job_is_suspended_and_restarted_once",
        expected_failure="assert event.is_set()",
    ),
    MutationCase(
        case_id="stranded-report-after-reveal",
        category="Stranded report after reveal",
        edits=(
            Edit(
                "skill_lens/tui/diff.py",
                """        if self._report is None:
            active = controller.active_requests.get("diff")
            if self._owned_request is not None and active != self._owned_request:
                self._owned_request = None
            if self._owned_request is None and not controller.is_failed:
                self._request_report()
        self._restore_help_view(same_generation)
""",
                """        self._restore_help_view(same_generation)
""",
            ),
        ),
        test="tests/test_tui_help.py::test_diff_job_is_suspended_and_restarted_once",
        expected_failure="reveal must resume Diff work",
    ),
    MutationCase(
        case_id="stale-callback-pops-newer-screen",
        category="Stale callback popping a newer screen",
        edits=(
            Edit(
                "skill_lens/tui/app.py",
                """        if self.screen is not expected:
            return
        tracked = self._help_origin
""",
                """        tracked = self._help_origin
""",
            ),
        ),
        test="tests/test_tui_help.py::test_help_does_not_stack_and_stale_instance_cannot_close_a_newer_help",
        expected_failure="assert app.screen is second",
    ),
    MutationCase(
        case_id="stale-json-after-refresh",
        category="Stale JSON after refresh",
        edits=(
            Edit(
                "skill_lens/tui/json_view.py",
                """        if self._document == document:
            return
        self._document = document
""",
                """        if self._document is not None:
            return
        self._document = document
""",
            ),
        ),
        test="tests/test_tui_help.py::test_help_over_home_json_refresh_replaces_the_document_without_stale_data",
        expected_failure="assert view.document != old_document",
    ),
    MutationCase(
        case_id="fault-hidden-while-help-open",
        category="Fault state hidden while Help is open",
        edits=(
            Edit(
                "skill_lens/tui/help.py",
                """    if controller.is_failed:
        lines.extend(
            [
                "",
                "ACCEPTED INTERNAL FAULT (sticky; Quit exits 3):",
                controller.last_error_details or "(no details were recorded)",
            ]
        )
    return "\\n".join(lines)
""",
                """    return "\\n".join(lines)
""",
            ),
        ),
        test="tests/test_tui_help.py::test_help_status_with_prior_data_keeps_retained_wording_and_data[fault]",
        expected_failure="AssertionError: assert 'ACCEPTED INTERNAL FAULT' in",
    ),
    MutationCase(
        case_id="fault-reset-while-help-open",
        category="Fault state reset while Help is open",
        edits=(
            Edit(
                "skill_lens/tui/help.py",
                """    def update_session(self, controller: SessionController) -> None:
        \"\"\"Refresh only the live session section; the static body keeps its scroll.\"\"\"
        if not self.is_mounted:
            return
""",
                """    def update_session(self, controller: SessionController) -> None:
        \"\"\"Refresh only the live session section; the static body keeps its scroll.\"\"\"
        return
""",
            ),
        ),
        test="tests/test_tui_help.py::test_help_status_with_prior_data_keeps_retained_wording_and_data[fault]",
        expected_failure="AssertionError: assert 'Retained data' in",
    ),
    MutationCase(
        case_id="banned-import-in-help-module",
        category="Banned import in the new Help module",
        edits=(
            Edit(
                "skill_lens/tui/help.py",
                """from skill_lens.tui.session import SessionController
""",
                """import subprocess

from skill_lens.tui.session import SessionController
""",
            ),
        ),
        test="tests/test_tui_read_only.py::test_shipped_tui_code_has_zero_read_only_violations",
        expected_failure="Banned import 'subprocess'",
    ),
    MutationCase(
        case_id="write-in-help-module",
        category="Write in the new Help module",
        edits=(
            Edit(
                "skill_lens/tui/help.py",
                """from skill_lens.tui.session import SessionController
""",
                """from pathlib import Path

from skill_lens.tui.session import SessionController

Path("u8-mutant.txt").write_text("should never run", encoding="utf-8")
""",
            ),
        ),
        test="tests/test_tui_read_only.py::test_shipped_tui_code_has_zero_read_only_violations",
        expected_failure="write_text",
    ),
)


def _run(test: str, workdir: Path) -> tuple[int, str, str, float]:
    command = [
        str(PYTHON),
        "-m",
        "pytest",
        test,
        "-q",
        "--no-header",
        "-p",
        "no:cacheprovider",
    ]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=workdir,
        capture_output=True,
        text=True,
        timeout=240,
        env={**__import__("os").environ, "PYTHONPATH": str(workdir)},
    )
    elapsed = round(time.monotonic() - started, 2)
    output = f"$ {' '.join(command)}\n{completed.stdout}{completed.stderr}"
    return completed.returncode, completed.stdout + completed.stderr, output, elapsed


def _prepare_copy() -> Path:
    root = Path(tempfile.mkdtemp(prefix="skill-lens-u8-mutations-"))
    for item in COPY_ITEMS:
        source = REPO_ROOT / item
        target = root / item
        if source.is_dir():
            shutil.copytree(
                source,
                target,
                ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"),
            )
        else:
            shutil.copy2(source, target)
    return root


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    copy_root = _prepare_copy()
    results: list[dict[str, Any]] = []
    survivors: list[str] = []
    try:
        for index, case in enumerate(CASES, start=1):
            prefix = f"{index:02d}-{case.case_id}"
            originals: dict[str, str] = {}
            mutation_text: list[str] = []
            for edit in case.edits:
                path = copy_root / edit.path
                original = path.read_text(encoding="utf-8")
                assert edit.old in original, f"{case.case_id}: snippet missing in {edit.path}"
                originals.setdefault(edit.path, original)
                mutation_text.append(
                    f"--- {edit.path}\n- {edit.old.strip()}\n+ {edit.new.strip()}\n"
                )

            control_code, _, control_log, control_time = _run(case.test, copy_root)
            (OUTPUT_DIR / f"{prefix}.control-before.log").write_text(control_log, encoding="utf-8")

            for edit in case.edits:
                path = copy_root / edit.path
                path.write_text(
                    path.read_text(encoding="utf-8").replace(edit.old, edit.new, 1),
                    encoding="utf-8",
                )

            mutant_code, mutant_output, mutant_log, mutant_time = _run(case.test, copy_root)
            (OUTPUT_DIR / f"{prefix}.mutant.log").write_text(mutant_log, encoding="utf-8")

            for relative, original in originals.items():
                (copy_root / relative).write_text(original, encoding="utf-8")
            restore_code, _, restore_log, restore_time = _run(case.test, copy_root)
            (OUTPUT_DIR / f"{prefix}.control-after.log").write_text(restore_log, encoding="utf-8")

            syntax_error = any(
                marker in mutant_output
                for marker in (
                    "SyntaxError",
                    "ModuleNotFoundError",
                    "ImportError while loading conftest",
                    "ERROR collecting",
                )
            )
            meaningful_failure = (
                mutant_code != 0 and case.expected_failure in mutant_output and not syntax_error
            )
            passed = control_code == 0 and meaningful_failure and restore_code == 0
            if not passed:
                survivors.append(case.case_id)
            results.append(
                {
                    "case": case.case_id,
                    "category": case.category,
                    "test": case.test,
                    "expected_failure": case.expected_failure,
                    "mutation": "\n".join(mutation_text),
                    "control_before_exit": control_code,
                    "mutant_exit": mutant_code,
                    "control_after_exit": restore_code,
                    "mutant_meaningful_failure": meaningful_failure,
                    "syntax_or_import_error": syntax_error,
                    "passed": passed,
                    "seconds": {
                        "control_before": control_time,
                        "mutant": mutant_time,
                        "control_after": restore_time,
                    },
                }
            )
            print(
                f"{case.case_id}: control={control_code} mutant={mutant_code} "
                f"restore={restore_code} meaningful={meaningful_failure} "
                f"{'PASS' if passed else 'SURVIVOR'}"
            )
    finally:
        shutil.rmtree(copy_root, ignore_errors=True)

    payload = {
        "python": str(PYTHON),
        "cases": len(results),
        "survivors": survivors,
        "results": results,
    }
    (OUTPUT_DIR / "results.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"\n{len(results) - len(survivors)}/{len(results)} caught")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
