"""Run U7 Doctor mutations in a disposable copy of the baseline checkout."""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / "mutations"
PYTEST = REPO / ".venv" / "bin" / "pytest"
PARENT_PROBE = REPO / "docs/validation/u7/coordinator/independent-checks.py.txt"


@dataclass(frozen=True)
class Mutation:
    name: str
    selector: str
    replacements: tuple[tuple[str, str, str], ...]
    expected_text: str


MUTATIONS = (
    Mutation(
        "reverse_findings",
        "tests/test_tui_doctor.py::test_real_captured_findings_keep_model_order_and_cli_json",
        (
            (
                "skill_lens/tui/doctor.py",
                "for finding in findings:",
                "for finding in reversed(findings):",
            ),
        ),
        "At index 0 diff",
    ),
    Mutation(
        "drop_message",
        "tests/test_tui_doctor.py::test_real_captured_findings_keep_model_order_and_cli_json",
        (("skill_lens/tui/doctor.py", "_literal(finding.message),", '_literal(""),'),),
        "At index 0 diff",
    ),
    Mutation(
        "drop_detail",
        "tests/test_tui_doctor.py::test_doctor_shows_literal_fields_and_full_detail_at_both_widths",
        (
            (
                "skill_lens/tui/doctor.py",
                'f"Detail: {finding.detail if finding.detail is not None else _NONE}",',
                'f"Detail: {_NONE}",',
            ),
        ),
        "assert long_text in detail",
    ),
    Mutation(
        "alter_evidence",
        "tests/test_tui_doctor.py::test_doctor_shows_literal_fields_and_full_detail_at_both_widths",
        (
            (
                "skill_lens/tui/doctor.py",
                'f"Evidence: {finding.evidence.value}",',
                '"Evidence: unknown",',
            ),
        ),
        "Evidence: documented",
    ),
    Mutation(
        "recompute_doctor",
        "tests/test_tui_doctor.py::test_doctor_first_visit_stays_froz"
        "en_after_synthetic_tree_changes",
        (
            (
                "skill_lens/tui/doctor.py",
                "        snapshot = self._host.controller.current\n        if snapshot is None:",
                "        snapshot = self._host.controller.current\n"
                "        from skill_lens.core import snapshot as snapshot_module\n"
                "        snapshot_module.run_doctor()\n"
                "        if snapshot is None:",
            ),
        ),
        "doctor recomputed",
    ),
    Mutation(
        "disable_reverse_display_path",
        "tests/test_tui_doctor.py::test_finding_catalog_keys_use_only_exact_captured_identity",
        (
            (
                "skill_lens/tui/doctor.py",
                "    candidates = {path}\n"
                "    candidates.update(\n"
                "        raw_path\n"
                "        for raw_path, display_path in snapshot.display_paths.items()\n"
                "        if display_path == path\n"
                "    )",
                "    candidates = {path}",
            ),
        ),
        "finding_catalog_keys(snapshot, _finding(path=displayed)) == (first_key,)",
    ),
    Mutation(
        "match_by_basename",
        "tests/test_tui_doctor.py::test_finding_catalog_keys_use_only_exact_captured_identity",
        (
            (
                "skill_lens/tui/doctor.py",
                "            candidate == entry_path or "
                "snapshot_same_location(snapshot, candidate, entry_path)",
                "            candidate == entry_path\n"
                "            or snapshot_same_location(snapshot, candidate, entry_path)\n"
                '            or candidate.rsplit("/", 1)[-1] == entry_path.rsplit("/", 1)[-1]',
            ),
        ),
        "Left contains one more item",
    ),
    Mutation(
        "select_first_ambiguous_candidate",
        "tests/test_tui_doctor.py::test_finding_catalog_keys_use_only_exact_captured_identity",
        (
            (
                "skill_lens/tui/doctor.py",
                "return tuple(sorted(keys))",
                "return tuple(sorted(keys))[:1]",
            ),
        ),
        "ambiguous_snapshot",
    ),
    Mutation(
        "retain_blocking_text_filter",
        "tests/test_tui_doctor.py::test_doctor_first_visit_stays_froz"
        "en_after_synthetic_tree_changes",
        (
            (
                "skill_lens/tui/home.py",
                '            query.value = ""',
                "            query.value = query.value",
            ),
        ),
        'assert home.query_one("#filter-input", Input).value == ""',
    ),
    Mutation(
        "retain_blocking_agent_filter",
        "tests/test_independent_u7.py::test_parent_first_open_frozen_alias_jump_clears_filters",
        (
            (
                "skill_lens/tui/home.py",
                "        self._agent_id = None\n",
                "        self._agent_id = self._agent_id\n",
            ),
        ),
        "home._agent_id is None",
    ),
    Mutation(
        "skip_why_suspension",
        "tests/test_tui_doctor.py::test_doctor_entry_suspends_home_wh"
        "y_and_old_completion_keeps_new_owner",
        (
            (
                "skill_lens/tui/app.py",
                "        home.suspend_why()\n        self.push_screen(DoctorScreen())",
                "        self.push_screen(DoctorScreen())",
            ),
        ),
        "assert home._suspended",
    ),
    Mutation(
        "invalidate_newer_owned_request_on_stale_rejection",
        "tests/test_tui_doctor.py::test_doctor_entry_suspends_home_wh"
        "y_and_old_completion_keeps_new_owner",
        (
            (
                "skill_lens/tui/home.py",
                "            elif not accepted:\n"
                "                # Rejected data for someone else's token must never clear or\n"
                "                # mark the newer owned token.\n"
                "                pass",
                "            elif not accepted:\n"
                "                # Rejected data for someone else's token must never clear or\n"
                "                # mark the newer owned token.\n"
                "                self._cancel_owned_why()",
            ),
        ),
        'assert app.controller.active_requests.get("why") == second_request',
    ),
    Mutation(
        "retain_stale_doctor_and_json_on_refresh",
        "tests/test_tui_doctor.py::test_doctor_refresh_preserves_dupl"
        "icate_occurrence_and_replaces_raw_document",
        (
            (
                "skill_lens/tui/doctor.py",
                "        elif snapshot.generation != self._generation:\n      "
                "      self._replace_snapshot(snapshot)",
                "        elif snapshot.generation != self._generation:\n"
                "            if snapshot.generation == 1:\n"
                "                self._replace_snapshot(snapshot)\n"
                "            else:\n"
                "                self._generation = snapshot.generation",
            ),
        ),
        "timed out waiting for raw Doctor refresh",
    ),
    Mutation(
        "serialize_ui_derived_json",
        "tests/test_tui_doctor.py::test_real_captured_findings_keep_model_order_and_cli_json",
        (
            (
                "skill_lens/tui/doctor.py",
                "            view.show_document(dumps(snapshot.doctor.to_dict()))",
                "            "
                "view.show_document(dumps({**snapshot.doctor.to_dict(), "
                '"selection": "ui"}))',
            ),
        ),
        "view.document == expected_document",
    ),
    Mutation(
        "accept_stale_generation_with_valid_key",
        "tests/test_tui_doctor.py::test_stale_generation_with_valid_catalog_key_does_not_jump",
        (
            (
                "skill_lens/tui/app.py",
                "        snapshot = self.controller.current\n        if (\n    "
                "        snapshot is None",
                "        snapshot = self.controller.current\n"
                "        if snapshot is not None:\n"
                "            generation = snapshot.generation\n"
                "        if (\n            snapshot is None",
            ),
        ),
        "assert not app.jump_from_doctor",
    ),
    Mutation(
        "allow_hidden_enter_in_json",
        "tests/test_independent_u7.py::test_parent_first_open_frozen_alias_jump_clears_filters",
        (
            (
                "skill_lens/tui/doctor.py",
                "identity = self._selected_from_table()\n        if identity is not None:",
                "identity = self._selected\n        if identity is not None:",
            ),
            (
                "skill_lens/tui/doctor.py",
                "            or self._json_mode\n            or identity.generation",
                "            or identity.generation",
            ),
            (
                "skill_lens/tui/doctor.py",
                "        identity = self._selected_from_table()\n        if "
                "identity is None or identity.generation != generation:",
                "        identity = self._selected\n        if identity is "
                "None or identity.generation != generation:",
            ),
        ),
        "hidden Enter must not jump",
    ),
)


def run(project: Path, selector: str, log: Path, sandbox_home: Path) -> tuple[int, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project)
    env["HOME"] = str(sandbox_home)
    env["CODEX_HOME"] = str(sandbox_home / ".codex")
    command = [str(PYTEST), "-q", "-o", "addopts=", selector]
    completed = subprocess.run(command, cwd=project, env=env, capture_output=True, text=True)
    output = completed.stdout + completed.stderr
    log.write_text(
        "$ " + " ".join(command) + f"\ncwd={project}\nexit_code={completed.returncode}\n\n{output}",
        encoding="utf-8",
    )
    return completed.returncode, output


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(["git", "archive", "HEAD"], cwd=REPO, check=True, capture_output=True)
    temp_root = Path(tempfile.mkdtemp(prefix="skill-lens-u7-mutations-"))
    project = temp_root / "checkout"
    project.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as tar:
        tar.extractall(project, filter="data")

    overlay = (
        "skill_lens/tui/app.py",
        "skill_lens/tui/home.py",
        "skill_lens/tui/doctor.py",
        "tests/test_tui_doctor.py",
        "tests/test_tui_read_only.py",
    )
    for relative in overlay:
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / relative, target)
    independent_test = project / "tests" / "test_independent_u7.py"
    shutil.copy2(PARENT_PROBE, independent_test)
    shutil.copy2(REPO / "tests" / "conftest.py", project / "tests" / "conftest.py")
    sandbox_home = temp_root / "home"
    sandbox_home.mkdir()

    rows: list[str] = []
    for mutation in MUTATIONS:
        case_dir = OUT / mutation.name
        case_dir.mkdir(parents=True, exist_ok=True)
        saved: dict[str, str] = {}
        for relative, _, _ in mutation.replacements:
            saved[relative] = (project / relative).read_text(encoding="utf-8")

        control_before, control_output = run(
            project, mutation.selector, case_dir / "control-before.log", sandbox_home
        )
        if control_before != 0:
            raise RuntimeError(f"{mutation.name}: control-before failed; see {case_dir}")

        for relative, old, new in mutation.replacements:
            content = (project / relative).read_text(encoding="utf-8")
            count = content.count(old)
            if count < 1:
                raise RuntimeError(f"{mutation.name}: no mutation point found: {old!r}")
            (project / relative).write_text(content.replace(old, new, 1), encoding="utf-8")

        mutant_code, mutant_output = run(
            project, mutation.selector, case_dir / "mutant.log", sandbox_home
        )
        if mutant_code == 0 or mutation.expected_text not in mutant_output:
            raise RuntimeError(
                f"{mutation.name}: mutant did not fail for the expected assertion; see {case_dir}"
            )

        for relative, content in saved.items():
            (project / relative).write_text(content, encoding="utf-8")
        control_after, _ = run(
            project, mutation.selector, case_dir / "control-after.log", sandbox_home
        )
        if control_after != 0:
            raise RuntimeError(f"{mutation.name}: restored control failed; see {case_dir}")

        rows.append(
            f"| {mutation.name} | `{mutation.selector}` | "
            "0 | nonzero, expected assertion | 0 | PASS |"
        )

    summary = [
        "# U7 isolated mutation campaign",
        "",
        "All variants ran in a disposable archive of HEAD with the "
        "current in-scope U7 source/tests overlaid. The real "
        "checkout was never mutated. Each case used control → "
        "mutation → restored control. HOME and CODEX_HOME pointed at "
        "a fresh temporary sandbox; tests use their `mock_home` "
        "fixture for synthetic systems. The parent-authored "
        "independent probe was copied read-only beside the isolated "
        "test tree for the hidden-Enter case.",
        "",
        "| Mutation | Test | Control before | Mutant | Restore control | Result |",
        "| --- | --- | ---: | --- | ---: | --- |",
        *rows,
        "",
        f"Temporary isolated checkout: `{project}`. "
        "Per-case full output is retained in this folder.",
        "",
    ]
    (OUT / "summary.md").write_text("\n".join(summary), encoding="utf-8")
    print(f"PASS: {len(rows)} isolated mutations; evidence: {OUT / 'summary.md'}")


if __name__ == "__main__":
    main()
