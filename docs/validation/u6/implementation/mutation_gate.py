"""Run the U6 behavior mutations in a disposable copy of the checkout."""

from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PYTEST = ROOT / ".venv" / "bin" / "pytest"
EVIDENCE = Path(__file__).resolve().parent
PYTHON = ROOT / ".venv" / "bin" / "python"


@dataclass(frozen=True)
class Mutation:
    name: str
    target: str
    selected: tuple[str, ...]
    edits: tuple[tuple[str, str, str], ...]
    occurrences: tuple[int, ...] = ()


MUTATIONS: tuple[Mutation, ...] = (
    Mutation(
        "filter letters open Agents",
        "tests/test_tui_agents.py::test_home_shortcuts_preserve_filter_typing_and_open_empty_catalog_screens",
        (),
        (
            (
                "skill_lens/tui/home.py",
                """        with contextlib.suppress(NoMatches):
            if self.query_one("#filter-input", Input).has_focus:
                return
        self._clear_removal_notice()
        self._host.open_agents()
""",
                """        self._clear_removal_notice()
        self._host.open_agents()
""",
            ),
        ),
    ),
    Mutation(
        "picker filters to detected agents",
        "tests/test_tui_compare.py::test_compare_empty_skill_home_still_offers_all_registry_choices",
        (),
        (
            (
                "skill_lens/tui/compare.py",
                "            self._on_generation(snapshot.registry, snapshot.generation)\n",
                "            detected = set(snapshot.scan.summary.detected_agents)\n"
                "            registry = tuple(\n"
                "                agent for agent in snapshot.registry if agent.id in detected\n"
                "            )\n"
                "            self._on_generation(registry, snapshot.generation)\n",
            ),
        ),
    ),
    Mutation(
        "first visit rereads a captured skill file",
        "tests/test_tui_compare.py::test_compare_first_visit_uses_frozen_files_and_registry_only",
        (),
        (
            (
                "skill_lens/tui/compare.py",
                "from __future__ import annotations\n",
                "from __future__ import annotations\n\nfrom pathlib import Path\n",
            ),
            (
                "skill_lens/tui/compare.py",
                "        counts = report.counts_by_relation()\n",
                "        counts = report.counts_by_relation()\n"
                "        Path(snapshot.home, '.agents/skills/identical/SKILL.md').read_text(\n"
                "            encoding='utf-8'\n"
                "        )\n",
            ),
        ),
    ),
    Mutation(
        "ordered pair is reversed",
        "tests/test_tui_compare.py::test_compare_all_registry_agents_keyboard_picker_and_exact_cli_json",
        (),
        (
            (
                "skill_lens/tui/compare.py",
                "        arguments = pair\n",
                "        arguments = tuple(reversed(pair))\n",
            ),
        ),
    ),
    Mutation(
        "stale success enters the report cache",
        "tests/test_tui_compare.py::test_compare_rejects_late_old_pair_completion_after_cached_pair_reopens",
        ("success",),
        (
            (
                "skill_lens/tui/session.py",
                """        active = self.active_requests.get(view)
        if active is None:
            return False
        if (
            active.request_id != request_id
            or active.generation != generation
            or active.arguments != arguments
        ):
""",
                """        active = self.active_requests.get(view)
        if active is None:
            self.cache[(generation, view, arguments)] = result
            return True
        if (
            active.request_id != request_id
            or active.generation != generation
            or active.arguments != arguments
        ):
""",
            ),
        ),
        occurrences=(0,),
    ),
    Mutation(
        "stale error poisons controller failure state",
        "tests/test_tui_compare.py::test_compare_rejects_late_old_pair_completion_after_cached_pair_reopens",
        ("error",),
        (
            (
                "skill_lens/tui/session.py",
                """        active = self.active_requests.get(view)
        if active is None:
            return False
        if (
            active.request_id != request_id
            or active.generation != generation
            or active.arguments != arguments
        ):
""",
                """        active = self.active_requests.get(view)
        if active is None:
            self.failed = True
            self.last_error_details = "synthetic stale error"
            return True
        if (
            active.request_id != request_id
            or active.generation != generation
            or active.arguments != arguments
        ):
""",
            ),
        ),
        occurrences=(1,),
    ),
    Mutation(
        "old screen cleanup cancels a newer token",
        "tests/test_tui_compare.py::test_compare_close_and_old_token_cleanup_are_instance_checked",
        (),
        (
            (
                "skill_lens/tui/compare.py",
                """        active = self._host.controller.active_requests.get("compare")
        if active == owned:
            self._host.controller.invalidate_view("compare")
""",
                """        active = self._host.controller.active_requests.get("compare")
        if active is not None:
            self._host.controller.invalidate_view("compare")
""",
            ),
        ),
    ),
    Mutation(
        "raw refresh leaves the old report and JSON visible",
        "tests/test_tui_compare.py::test_compare_refresh_keeps_valid_raw_mode_and_clears_old_json_while_loading",
        (),
        (
            (
                "skill_lens/tui/compare.py",
                """        controller = self._host.controller
        snapshot = controller.current
""",
                """        controller = self._host.controller
        if self._json_mode:
            return
        snapshot = controller.current
""",
            ),
        ),
        occurrences=(0,),
    ),
    Mutation(
        "missing choice dispatches a report worker",
        "tests/test_tui_compare.py::test_compare_input_errors_are_inline_and_dispatch_no_worker",
        (),
        (
            (
                "skill_lens/tui/compare.py",
                """        if self._selected_a is None:
            self._input_error = "Choose an agent for A."
            self._focus_side("a")
            self._refresh_picker()
            return
""",
                """        if self._selected_a is None:
            self._input_error = "Choose an agent for A."
            self._focus_side("a")
            self._refresh_picker()
            self._request_pair(("claude", "codex"))
            return
""",
            ),
        ),
    ),
    Mutation(
        "redraw retries a failed report",
        "tests/test_tui_compare.py::test_compare_error_is_sticky_but_redraw_never_retries",
        (),
        (
            (
                "skill_lens/tui/compare.py",
                """        self._refresh_result()
        if self._json_mode:
            self._refresh_json()

    def _on_generation(
""",
                """        self._refresh_result()
        if self._report_state == "error" and self._submitted_pair is not None:
            self._request_pair(self._submitted_pair)
        if self._json_mode:
            self._refresh_json()

    def _on_generation(
""",
            ),
        ),
    ),
    Mutation(
        "delayed close pops the current screen regardless of owner",
        "tests/test_tui_compare.py::test_compare_close_and_old_token_cleanup_are_instance_checked",
        (),
        (
            (
                "skill_lens/tui/app.py",
                '''    def close_compare(self, expected: CompareScreen) -> None:
        """Close only the expected Compare instance and resume Home."""
        if self.screen is not expected:
            return
        expected._cancel_owned_token()
''',
                '''    def close_compare(self, expected: CompareScreen) -> None:
        """Close only the expected Compare instance and resume Home."""
        expected._cancel_owned_token()
''',
            ),
        ),
    ),
    Mutation(
        "raw-mode cursor actions move hidden picker controls",
        "tests/test_tui_compare.py::test_compare_result_layout_and_raw_mode_keep_hidden_picker_inert",
        (),
        (
            (
                "skill_lens/tui/compare.py",
                """    def action_cursor_down(self) -> None:
        if self._json_mode or self._mode != "picker":
            return
        focused = self.app.focused
        if isinstance(focused, DataTable) and focused.id in {
            "compare-a-table",
            "compare-b-table",
        }:
            focused.action_cursor_down()
""",
                """    def action_cursor_down(self) -> None:
        table = self.query_one("#compare-a-table", DataTable)
        table.action_cursor_down()
""",
            ),
        ),
    ),
    Mutation(
        "comparison diagnostic text is parsed as markup",
        "tests/test_tui_compare.py::test_compare_report_uses_engine_relations_paths_counts_and_literal_notes",
        (),
        (
            (
                "skill_lens/tui/compare.py",
                "    return Content.from_text(text, markup=False)\n",
                "    return Content.from_text(text)\n",
            ),
        ),
    ),
)

EXPECTED_ASSERTIONS: dict[str, str] = {
    "filter letters open Agents": "assert app.screen is home",
    "picker filters to detected agents": "row_count == 10",
    "first visit rereads a captured skill file": "first visit accessed captured target",
    "ordered pair is reversed": "timed out waiting for accepted comparison report",
    "stale success enters the report cache": 'get_cached_report("compare", ("codex", "claude"))',
    "stale error poisons controller failure state": "assert not app.controller.failed",
    "old screen cleanup cancels a newer token": 'active_requests.get("compare") == new_token',
    "raw refresh leaves the old report and JSON visible": "new-generation comparison worker",
    "missing choice dispatches a report worker": "assert report_calls == []",
    "redraw retries a failed report": "assert calls == 1",
    "delayed close pops the current screen regardless of owner": "assert app.screen is second",
    "raw-mode cursor actions move hidden picker controls": "(2, 2) == (1, 2)",
    "comparison diagnostic text is parsed as markup": "Diagnostic [red]literal[/red] note.",
}

SOURCE_ASSERTIONS: dict[str, str] = {
    "first visit rereads a captured skill file": "first visit accessed captured target",
    "ordered pair is reversed": "accepted comparison report",
    "raw refresh leaves the old report and JSON visible": "new-generation comparison worker",
    "raw-mode cursor actions move hidden picker controls": ") == hidden_cursors",
}


def _copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = {
        ".git",
        ".venv",
        ".path",
        ".pytest_cache",
        ".workbuddy-ai",
        ".DS_Store",
        "__pycache__",
        "2026-10-25",
        "u6",
    }
    return set(names) & ignored


def _run(worktree: Path, mutation: Mutation) -> subprocess.CompletedProcess[str]:
    command = [str(PYTEST), "-q", mutation.target, "--tb=short"]
    command.extend(("-k", " and ".join(mutation.selected)) if mutation.selected else ())
    return subprocess.run(
        command,
        cwd=worktree,
        env={**os.environ, "PYTHONPATH": str(worktree)},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _provenance(worktree: Path) -> dict[str, str]:
    test_paths = {
        "agents_test_module": (worktree / "tests" / "test_tui_agents.py").resolve(),
        "compare_test_module": (worktree / "tests" / "test_tui_compare.py").resolve(),
    }
    script = (
        "import runpy, skill_lens; "
        f"agents = runpy.run_path({str(test_paths['agents_test_module'])!r}, "
        "run_name='u6_agents_test_module_provenance'); "
        f"compare = runpy.run_path({str(test_paths['compare_test_module'])!r}, "
        "run_name='u6_compare_test_module_provenance'); "
        "print('skill_lens=' + str(skill_lens.__file__)); "
        "print('agents_test_module=' + str(agents['__file__'])); "
        "print('compare_test_module=' + str(compare['__file__']))"
    )
    result = subprocess.run(
        [str(PYTHON), "-c", script],
        cwd=worktree,
        env={**os.environ, "PYTHONPATH": str(worktree)},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"temporary source provenance failed\n{result.stdout}{result.stderr}")
    lines = dict(line.split("=", 1) for line in result.stdout.strip().splitlines())
    expected_package = str((worktree / "skill_lens" / "__init__.py").resolve())
    expected = {
        "skill_lens": expected_package,
        **{key: str(path) for key, path in test_paths.items()},
    }
    if any(lines.get(key) != path for key, path in expected.items()):
        raise SystemExit(f"temporary copy imported unexpected files: {lines}")
    return lines


def _preflight(worktree: Path) -> list[dict[str, object]]:
    """Validate selectors and exact restoration without running a test process."""
    records: list[dict[str, object]] = []
    for mutation in MUTATIONS:
        target_file, target_function = mutation.target.split("::", maxsplit=1)
        target_source = (worktree / target_file).read_text(encoding="utf-8")
        if f"def {target_function}(" not in target_source:
            raise AssertionError(f"{mutation.name}: test target missing: {mutation.target}")
        expected_assertion = SOURCE_ASSERTIONS.get(
            mutation.name, EXPECTED_ASSERTIONS[mutation.name]
        )
        if expected_assertion not in target_source:
            raise AssertionError(
                f"{mutation.name}: intended test assertion missing: {expected_assertion}"
            )

        originals: dict[Path, bytes] = {}
        for edit_index, (relative, before, after) in enumerate(mutation.edits):
            path = worktree / relative
            originals.setdefault(path, path.read_bytes())
            source = path.read_text(encoding="utf-8")
            count = source.count(before)
            selected = (
                mutation.occurrences[edit_index] if edit_index < len(mutation.occurrences) else 0
            )
            if selected >= count:
                raise AssertionError(
                    f"{mutation.name}: source selector {selected} missing in {relative}; "
                    f"found {count} matches"
                )
            if count != 1 and edit_index >= len(mutation.occurrences):
                raise AssertionError(
                    f"{mutation.name}: ambiguous source selector in {relative}; "
                    f"found {count} matches"
                )
            _edit_one(worktree, mutation, edit_index, restore=False)
            changed_source = path.read_text(encoding="utf-8")
            if after not in changed_source:
                raise AssertionError(f"{mutation.name}: mutation replacement was not applied")

        for path in originals:
            if path.suffix == ".py":
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        _edit(worktree, mutation, restore=True)
        for path, original in originals.items():
            if path.read_bytes() != original:
                raise AssertionError(f"{mutation.name}: preflight failed to restore {path.name}")

        records.append(
            {
                "name": mutation.name,
                "test": mutation.target,
                "intended_test_assertion": expected_assertion,
                "runtime_failure_marker": EXPECTED_ASSERTIONS[mutation.name],
                "edits": [
                    {
                        "file": relative,
                        "before_matches": (worktree / relative)
                        .read_text(encoding="utf-8")
                        .count(before),
                        "selected_occurrence": (
                            mutation.occurrences[index] if index < len(mutation.occurrences) else 0
                        ),
                        "replacement_fragment": after,
                    }
                    for index, (relative, _before, after) in enumerate(mutation.edits)
                ],
                "ast_valid_after_mutation": True,
                "restored_bytes_exactly": True,
            }
        )
    return records


def _edit_one(worktree: Path, mutation: Mutation, edit_index: int, *, restore: bool) -> None:
    relative, before, after = mutation.edits[edit_index]
    path = worktree / relative
    source = path.read_text(encoding="utf-8")
    old, new = (after, before) if restore else (before, after)
    positions: list[int] = []
    start = 0
    while True:
        position = source.find(old, start)
        if position < 0:
            break
        positions.append(position)
        start = position + len(old)
    occurrence = 0
    if not restore and edit_index < len(mutation.occurrences):
        occurrence = mutation.occurrences[edit_index]
    if occurrence >= len(positions):
        raise AssertionError(
            f"{mutation.name}: occurrence {occurrence} missing in {relative}; "
            f"found {len(positions)} matches for selected fragment"
        )
    position = positions[occurrence]
    source = source[:position] + new + source[position + len(old) :]
    path.write_text(source, encoding="utf-8")


def _edit(worktree: Path, mutation: Mutation, *, restore: bool) -> None:
    indices = range(len(mutation.edits))
    if restore:
        indices = reversed(indices)
    for edit_index in indices:
        _edit_one(worktree, mutation, edit_index, restore=restore)


def _short(result: subprocess.CompletedProcess[str]) -> str:
    output = (result.stdout + result.stderr).strip()
    return output[-4500:]


def _write_receipt(
    path: Path,
    records: list[dict[str, object]],
    provenance: dict[str, str],
    *,
    complete: bool,
) -> None:
    non_kills = [item["name"] for item in records if item["status"] != "killed"]
    receipt = {
        "runner": str(PYTEST),
        "checkout": "temporary copy of the frozen working tree; deleted after the run",
        "temporary_copy_provenance": provenance,
        "mutations": records,
        "total": len(MUTATIONS),
        "completed": len(records),
        "complete": complete,
        "non_kills": non_kills,
    }
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="check every source selector and exact restoration without running tests",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        choices=[mutation.name for mutation in MUTATIONS],
        help="rerun selected cases and merge them into the existing full receipt",
    )
    args = parser.parse_args()
    if not PYTEST.is_file():
        raise SystemExit(f"missing test runner at {PYTEST}")

    if args.preflight_only:
        with tempfile.TemporaryDirectory(prefix="skill-lens-u6-mutation-preflight-") as temporary:
            worktree = Path(temporary) / "checkout"
            shutil.copytree(ROOT, worktree, ignore=_copy_ignore, symlinks=True)
            provenance = _provenance(worktree)
            records = _preflight(worktree)
        receipt = {
            "checkout": "temporary copy; deleted after source-only preflight",
            "test_processes_run": 0,
            "temporary_copy_provenance": provenance,
            "mutations": records,
            "total": len(records),
            "result": (
                "all source selectors and intended test markers resolved; "
                "all files restored exactly"
            ),
        }
        (EVIDENCE / "mutation-preflight.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"PREFLIGHT {len(records)} mutations: source fragments, AST and restoration passed")
        print(f"skill_lens={provenance['skill_lens']}")
        print(f"agents_test_module={provenance['agents_test_module']}")
        print(f"compare_test_module={provenance['compare_test_module']}")
        return 0

    records: list[dict[str, object]] = []
    receipt_path = EVIDENCE / "mutations.json"
    selected_names = set(args.only or ())
    if selected_names:
        if not receipt_path.is_file():
            raise SystemExit("--only requires the existing full mutations.json receipt")
        previous = json.loads(receipt_path.read_text(encoding="utf-8"))
        previous_records = previous.get("mutations", [])
        previous_names = {str(item.get("name")) for item in previous_records}
        if not selected_names <= previous_names:
            raise SystemExit("--only requested a mutation not present in the existing receipt")
        records = [item for item in previous_records if item.get("name") not in selected_names]
    with tempfile.TemporaryDirectory(prefix="skill-lens-u6-mutations-") as temporary:
        worktree = Path(temporary) / "checkout"
        shutil.copytree(ROOT, worktree, ignore=_copy_ignore, symlinks=True)
        provenance = _provenance(worktree)
        _write_receipt(receipt_path, records, provenance, complete=False)
        for index, mutation in enumerate(MUTATIONS, start=1):
            if selected_names and mutation.name not in selected_names:
                continue
            record: dict[str, object] = {
                "index": index,
                "name": mutation.name,
                "test": mutation.target,
                "selection": list(mutation.selected),
                "source_assertion": SOURCE_ASSERTIONS.get(
                    mutation.name, EXPECTED_ASSERTIONS[mutation.name]
                ),
                "runtime_failure_marker": EXPECTED_ASSERTIONS[mutation.name],
            }
            try:
                control = _run(worktree, mutation)
            except Exception as error:
                record.update(
                    {
                        "status": "control_runner_error",
                        "control_error": repr(error),
                    }
                )
                records.append(record)
                _write_receipt(receipt_path, records, provenance, complete=False)
                print(f"RECORDED {index}/{len(MUTATIONS)} {mutation.name}: control runner error")
                continue
            record["control_exit"] = control.returncode
            record["control_output"] = control.stdout + control.stderr
            if control.returncode != 0:
                record["status"] = "control_failed"
                records.append(record)
                _write_receipt(receipt_path, records, provenance, complete=False)
                print(f"RECORDED {index}/{len(MUTATIONS)} {mutation.name}: control failed")
                continue

            mutant: subprocess.CompletedProcess[str] | None = None
            mutant_error: str | None = None
            restored: subprocess.CompletedProcess[str] | None = None
            try:
                _edit(worktree, mutation, restore=False)
                try:
                    mutant = _run(worktree, mutation)
                except Exception as error:
                    mutant_error = repr(error)
            except Exception as error:
                mutant_error = f"source mutation failed: {error!r}"
            finally:
                try:
                    _edit(worktree, mutation, restore=True)
                    restored = _run(worktree, mutation)
                except Exception as error:
                    record["restore_error"] = repr(error)

            if mutant is not None:
                combined = mutant.stdout + mutant.stderr
                record["mutant_exit"] = mutant.returncode
                record["mutant_output"] = combined
                expected_failure = (
                    mutant.returncode != 0
                    and "FAILED" in combined
                    and mutation.target.split("::", maxsplit=1)[1] in combined
                )
                assertion_reached = EXPECTED_ASSERTIONS[mutation.name] in combined
                record["mutant_failed_test"] = expected_failure
                record["intended_assertion_reached"] = assertion_reached
            else:
                expected_failure = False
                assertion_reached = False
            if mutant_error is not None:
                record["mutant_error"] = mutant_error
            if restored is not None:
                record["restored_exit"] = restored.returncode
                record["restored_output"] = restored.stdout + restored.stderr

            if (
                expected_failure
                and assertion_reached
                and restored is not None
                and restored.returncode == 0
            ):
                record["status"] = "killed"
            elif mutant is not None and not expected_failure:
                record["status"] = "survived_or_wrong_test_failed"
            elif expected_failure and not assertion_reached:
                record["status"] = "marker_mismatch"
            elif restored is None or restored.returncode != 0:
                record["status"] = "restoration_failed"
            else:
                record["status"] = "mutation_runner_error"

            records.append(record)
            _write_receipt(receipt_path, records, provenance, complete=False)
            print(
                f"RECORDED {index}/{len(MUTATIONS)} {mutation.name}: "
                f"{record['status']} control={record['control_exit']} "
                f"mutant={record.get('mutant_exit', 'n/a')} "
                f"restored={record.get('restored_exit', 'n/a')}"
            )

    records.sort(key=lambda item: int(item["index"]))
    complete = len(records) == len(MUTATIONS)
    _write_receipt(receipt_path, records, provenance, complete=complete)
    lines = [
        "# U6 behavioral mutation checks",
        "",
        (
            "Every experiment ran in a temporary copy of the frozen working tree. "
            "The receipt was updated after each case with complete test output, "
            "runtime assertion markers and exact exit codes. The temporary copy "
            "was deleted afterward."
        ),
        "",
        f"Runner: `{PYTEST}`",
        (
            f"Temporary imports: `{provenance['skill_lens']}`, "
            f"`{provenance['agents_test_module']}`, and "
            f"`{provenance['compare_test_module']}`"
        ),
        "",
        "| Behavior guarded | Status | Control | Mutant | Restored | Assertion reached |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    lines.extend(
        f"| {item['name']} | {item['status']} | {item.get('control_exit', 'n/a')} | "
        f"{item.get('mutant_exit', 'n/a')} | {item.get('restored_exit', 'n/a')} | "
        f"{item.get('intended_assertion_reached', False)} |"
        for item in records
    )
    killed = sum(item["status"] == "killed" for item in records)
    non_kills = [item["name"] for item in records if item["status"] != "killed"]
    lines.extend(
        [
            "",
            (
                f"**Result:** {killed}/{len(records)} mutants killed; "
                f"unresolved cases: {len(non_kills)}."
            ),
            "",
        ]
    )
    (EVIDENCE / "mutations.md").write_text("\n".join(lines), encoding="utf-8")
    return 0 if len(records) == len(MUTATIONS) and not non_kills else 1


if __name__ == "__main__":
    raise SystemExit(main())
