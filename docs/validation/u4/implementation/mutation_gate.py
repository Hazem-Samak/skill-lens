#!/usr/bin/env python3
"""U4 mutation gate: planted mutant fails, restored copy passes.

Runs on a disposable copy of ``skill_lens/`` + ``tests/`` in a temp directory,
so the checkout is never modified (hashes recorded before and after and must be identical).

Fourteen gates are exercised across Why screen, Home screen, and App orchestration:

1. Read-only AST guard: ``import rich`` planted in ``why.py`` must fail the
   shipped-tree guard (reusing the existing U2/U3 guard and mutation categories).
2. Target-read sentinel: a direct ``Path(...).read_text()`` of a synthetic
   target skill file planted in ``WhyScreen._update_display`` must fail the
   target-specific sentinel test.
3. Detail token guard: removing the token ownership guard in ``_cancel_owned_token``
   (blindly invalidating the active view) must fail the token discrimination test.
4. Agent switch cancellation: removing arguments check in identity_matches in
   ``note_report_outcome`` must fail the agent switch race test.
5. Literal markup rendering: changing ``markup=False`` to ``markup=True`` in
   candidate collapsible blocks must fail the literal markup test.
6. Reviewer mutant 1 (DeepSeek B3): removing Home ``_drive`` suspended guard
   must fail the suspended hidden dispatch prevention test.
7. Reviewer mutant 2 (DeepSeek B3): removing Home ``note_report_outcome`` suspended guard
   must fail the suspended hidden dispatch prevention test.
8. Reviewer mutant 3 (DeepSeek B3): omitting Home ``suspend_why`` cancellation
   must fail the cancellation guards test.
9. Reviewer mutant 4 (DeepSeek B3): omitting detail matching owned token cancellation
   must fail the cancellation guards test.
10. Reviewer mutant 5 (DeepSeek B3): omitting pre-pop detail token cancellation
    in ``close_why`` must fail the cancellation guards test.
11. Reviewer mutant 6: stale error marking controller failed
    must fail the stale error test.
12. Removing backward traversal must fail the Shift+Tab assertion.
13. Switching agents outside the strip must fail candidate-focused arrow assertions.
14. Removing focus updates must fail selected-agent button focus assertions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PYTHON = REPO / ".venv" / "bin" / "python"
DEFAULT_OUT = Path(__file__).resolve().parent / "mutation_gate_r5.json"

READ_ONLY_TEST = "tests/test_tui_read_only.py::test_shipped_tui_code_has_zero_read_only_violations"
TARGET_READ_TEST = (
    "tests/test_tui_why.py::test_broad_read_sentinels_and_target_preservation_manifest"
)
DETAIL_TOKEN_TEST = (
    "tests/test_tui_why.py::test_real_pop_delayed_detail_callback_protects_resumed_home"
)
AGENT_SWITCH_TEST = "tests/test_tui_why.py::test_detail_agent_switch_a_to_b_while_a_completes"
LITERAL_MARKUP_TEST = "tests/test_tui_why.py::test_literal_rendering_markup_false"
SUSPENDED_DRIVE_OUTCOME_TEST = (
    "tests/test_tui_why.py::test_home_suspended_drive_and_outcome_guards_prevent_hidden_dispatch"
)
CANCELLATION_GUARDS_TEST = "tests/test_tui_why.py::test_cancellation_guards_kill_mutants"
STALE_ERROR_TEST = (
    "tests/test_tui_why.py::"
    "test_real_worker_race_blocked_home_to_detail_agent_change_and_stale_callbacks[error]"
)


NAVIGATION_TEST = (
    "tests/test_tui_why.py::test_terminal_dimensions_100x30_and_60x24_controls_and_wrapping"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(work: Path, selector: str) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(work)
    proc = subprocess.run(
        [str(PYTHON), "-m", "pytest", selector, "-q", "-p", "no:cacheprovider"],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr)[-4000:]


def failing_assertion(output: str) -> str:
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith(("AssertionError", "E ")) and "AssertionError" in stripped:
            return stripped[:200]
    for line in output.splitlines():
        if line.strip().startswith("E "):
            return line.strip()[:200]
    return ""


def main(out: Path) -> int:
    work = Path(tempfile.mkdtemp(prefix="skill-lens-u4-mutation-")).resolve()
    for item in ("skill_lens", "tests"):
        shutil.copytree(
            REPO / item,
            work / item,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    shutil.copy2(REPO / "pyproject.toml", work / "pyproject.toml")

    why_py = work / "skill_lens" / "tui" / "why.py"
    home_py = work / "skill_lens" / "tui" / "home.py"
    app_py = work / "skill_lens" / "tui" / "app.py"

    orig_why = why_py.read_text(encoding="utf-8")
    orig_home = home_py.read_text(encoding="utf-8")
    orig_app = app_py.read_text(encoding="utf-8")

    repo_why = REPO / "skill_lens" / "tui" / "why.py"
    repo_home = REPO / "skill_lens" / "tui" / "home.py"
    repo_app = REPO / "skill_lens" / "tui" / "app.py"

    receipt: dict[str, object] = {
        "schema": "skill-lens/u4-mutation-gate/2",
        "work_copy": str(work),
        "preservation": {
            "repo_why_sha256_before": sha256(repo_why),
            "repo_home_sha256_before": sha256(repo_home),
            "repo_app_sha256_before": sha256(repo_app),
            "work_why_sha256": sha256(why_py),
            "work_home_sha256": sha256(home_py),
            "work_app_sha256": sha256(app_py),
        },
        "cases": [],
    }

    # Control
    control = {
        "read_only": run(work, READ_ONLY_TEST),
        "target_read": run(work, TARGET_READ_TEST),
        "detail_token": run(work, DETAIL_TOKEN_TEST),
        "agent_switch": run(work, AGENT_SWITCH_TEST),
        "literal_markup": run(work, LITERAL_MARKUP_TEST),
        "suspended_guards": run(work, SUSPENDED_DRIVE_OUTCOME_TEST),
        "cancellation_guards": run(work, CANCELLATION_GUARDS_TEST),
        "stale_error": run(work, STALE_ERROR_TEST),
        "navigation": run(work, NAVIGATION_TEST),
    }
    receipt["control"] = {name: res[0] for name, res in control.items()}
    for name, res in control.items():
        assert res[0] == 0, f"{name} control failed:\n{res[1]}"

    def exercise_file(
        target_file: Path,
        original_text: str,
        name: str,
        mutant: str,
        selector: str,
        pattern: str,
        restore_selector: str | None = None,
    ) -> None:
        assert mutant != original_text, f"{name}: mutation did not apply"
        target_file.write_text(mutant, encoding="utf-8")
        rc, output = run(work, selector)
        assert rc != 0, f"{name}: mutant survived"
        assert pattern in output, f"{name}: pattern {pattern!r} missing:\n{output}"
        target_file.write_text(original_text, encoding="utf-8")
        restored = run(work, restore_selector or selector)
        assert restored[0] == 0, f"{name}: restored copy failed:\n{restored[1]}"
        receipt["cases"].append(  # type: ignore[union-attr]
            {
                "name": name,
                "selector": selector,
                "mutant_rc": rc,
                "mutant_detected_pattern": pattern,
                "mutant_failing_assertion": failing_assertion(output),
                "restored_rc": restored[0],
            }
        )

    # 1. Banned rich import
    exercise_file(
        why_py,
        orig_why,
        "read_only_guard_detects_rich_import_in_why",
        orig_why + "\nimport rich  # U4 mutation\n",
        READ_ONLY_TEST,
        "rich",
    )

    # 2. Target read during update_display
    target_read_mutant = orig_why.replace(
        "    def _update_display(self) -> None:\n",
        "    def _update_display(self) -> None:\n"
        "        from pathlib import Path as _MutationPath\n"
        '        _MutationPath(self._opening_key, "SKILL.md").read_text()\n',
        1,
    )
    exercise_file(
        why_py,
        orig_why,
        "target_read_sentinel_detects_direct_path_read",
        target_read_mutant,
        TARGET_READ_TEST,
        "Forbidden synthetic-target filesystem read",
    )

    # 3. Detail token unowned invalidation
    detail_token_mutant = orig_why.replace(
        "        if active is not None and active == owned:\n"
        '            controller.invalidate_view("why")',
        '        if active is not None:\n            controller.invalidate_view("why")',
        1,
    )
    exercise_file(
        why_py,
        orig_why,
        "detail_token_guard_detects_unowned_invalidation",
        detail_token_mutant,
        DETAIL_TOKEN_TEST,
        "AssertionError",
    )

    # 4. Agent switch arguments check removal
    agent_switch_mutant = orig_why.replace(
        "                and owned.arguments == arguments\n",
        "",
        1,
    )
    exercise_file(
        why_py,
        orig_why,
        "agent_switch_detects_arguments_mismatch_bypass",
        agent_switch_mutant,
        AGENT_SWITCH_TEST,
        "AssertionError",
    )

    # 5. Literal markup
    literal_markup_mutant = orig_why.replace(
        "Static(block.body, markup=False)",
        "Static(block.body, markup=True)",
        1,
    )
    exercise_file(
        why_py,
        orig_why,
        "literal_markup_detects_enabled_markup_in_candidate_body",
        literal_markup_mutant,
        LITERAL_MARKUP_TEST,
        "AssertionError",
    )

    # 6. Reviewer mutant 1: remove Home _drive suspended guard
    home_drive_mutant = orig_home.replace(
        "if not self.is_mounted or self._suspended or self._agent_id is None:\n            return",
        "if not self.is_mounted or self._agent_id is None:\n            return",
        1,
    )
    exercise_file(
        home_py,
        orig_home,
        "reviewer_mutant_1_remove_home_drive_suspended_guard",
        home_drive_mutant,
        SUSPENDED_DRIVE_OUTCOME_TEST,
        "AssertionError",
    )

    # 7. Reviewer mutant 2: remove Home note_report_outcome suspended guard
    home_outcome_mutant = orig_home.replace(
        'if not self.is_mounted or self._suspended or view != "why":\n            return',
        'if not self.is_mounted or view != "why":\n            return',
        1,
    )
    exercise_file(
        home_py,
        orig_home,
        "reviewer_mutant_2_remove_home_outcome_suspended_guard",
        home_outcome_mutant,
        SUSPENDED_DRIVE_OUTCOME_TEST,
        "AssertionError",
    )

    # 8. Reviewer mutant 3: omit Home suspend_why cancellation
    h_header = (
        "    def suspend_why(self) -> None:\n"
        '        """Suspend Home screen activity while detail screen is active."""\n'
        "        self._suspended = True"
    )
    home_suspend_mutant = orig_home.replace(
        h_header + "\n        self._cancel_owned_why()",
        h_header,
        1,
    )
    exercise_file(
        home_py,
        orig_home,
        "reviewer_mutant_3_omit_home_suspend_cancellation",
        home_suspend_mutant,
        CANCELLATION_GUARDS_TEST,
        "AssertionError",
    )

    # 9. Reviewer mutant 4: omit detail matching owned token cancellation
    detail_cancel_mutant = orig_why.replace(
        "        if active is not None and active == owned:\n"
        '            controller.invalidate_view("why")',
        "        if active is not None and active == owned:\n            pass",
        1,
    )
    exercise_file(
        why_py,
        orig_why,
        "reviewer_mutant_4_omit_detail_owned_cancellation",
        detail_cancel_mutant,
        CANCELLATION_GUARDS_TEST,
        "AssertionError",
    )

    # 10. Reviewer mutant 5: omit pre-pop detail token cancellation
    app_prepop_mutant = orig_app.replace(
        "        why._cancel_owned_token()\n"
        "        prev_screen = self.screen_stack[-2] if len(self.screen_stack) >= 2 else None",
        "        prev_screen = self.screen_stack[-2] if len(self.screen_stack) >= 2 else None",
        1,
    )
    exercise_file(
        app_py,
        orig_app,
        "reviewer_mutant_5_omit_pre_pop_detail_cancellation",
        app_prepop_mutant,
        CANCELLATION_GUARDS_TEST,
        "AssertionError",
    )

    # 11. Reviewer mutant 6: stale error marking controller failed
    stale_error_mutant = orig_app.replace(
        "        accepted = self.controller.accept_view_error(\n",
        "        self.controller.failed = True  # mutant: stale error marks controller failed\n"
        "        accepted = self.controller.accept_view_error(\n",
        1,
    )
    exercise_file(
        app_py,
        orig_app,
        "reviewer_mutant_6_stale_error_marks_controller_failed",
        stale_error_mutant,
        STALE_ERROR_TEST,
        "AssertionError",
    )

    # Navigation regressions identified by the bounded final review.
    navigation_mutations = (
        (
            "navigation_backward_traversal_removed",
            orig_why.replace("        self.focus_previous()", "        pass", 1),
            "Shift+Tab must leave the candidate title",
        ),
        (
            "navigation_agent_switch_outside_strip",
            orig_why.replace(
                "    def action_next_agent(self) -> None:\n"
                '        """Switch to the next agent while the strip is focused."""\n'
                "        if not self._is_strip_focused() or not self._agent_options:",
                "    def action_next_agent(self) -> None:\n"
                '        """Switch to the next agent while the strip is focused."""\n'
                "        if not self._agent_options:",
                1,
            ),
            "Candidate-focused arrows must not change the agent",
        ),
        (
            "navigation_selected_button_focus_removed",
            orig_why.replace(
                '        """Move focus to the button for the currently selected agent."""',
                '        """Move focus to the button for the currently selected agent."""\n'
                "        return",
                1,
            ),
            "Strip focus must follow selected agent",
        ),
    )
    for name, mutant, pattern in navigation_mutations:
        exercise_file(why_py, orig_why, name, mutant, NAVIGATION_TEST, pattern)

    receipt["preservation"]["work_why_sha256_after_restore"] = sha256(why_py)  # type: ignore[index]
    receipt["preservation"]["work_home_sha256_after_restore"] = sha256(home_py)  # type: ignore[index]
    receipt["preservation"]["work_app_sha256_after_restore"] = sha256(app_py)  # type: ignore[index]
    receipt["preservation"]["repo_why_sha256_after"] = sha256(repo_why)  # type: ignore[index]
    receipt["preservation"]["repo_home_sha256_after"] = sha256(repo_home)  # type: ignore[index]
    receipt["preservation"]["repo_app_sha256_after"] = sha256(repo_app)  # type: ignore[index]

    receipt["preservation"]["restored_identical"] = (  # type: ignore[index]
        sha256(why_py) == sha256(repo_why)
        and sha256(home_py) == sha256(repo_home)
        and sha256(app_py) == sha256(repo_app)
    )
    assert receipt["preservation"]["restored_identical"] is True  # type: ignore[index]

    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="receipt path (default: next to this script)",
    )
    raise SystemExit(main(parser.parse_args().out))
