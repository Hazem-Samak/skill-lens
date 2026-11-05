#!/usr/bin/env python3
"""Mutation-check the U9 packaging guards in disposable copies outside the checkout.

Every mutation follows the repo's clean/mutant/restored discipline:

1. *clean* — run the selected tests against a pristine export of the working tree
   and require exit 0.
2. *mutant* — apply one deliberate breakage in a fresh disposable copy, run the
   same selection, and require a non-zero exit whose failure is the **behavioural
   assertion** this guard exists for (never an import, syntax or collection error).
3. *restored* — restore the exact pristine bytes in that same copy, verify the
   file hash matches, and require exit 0 again.

Usage:
    .venv/bin/python docs/validation/u9/implementation/run_mutations.py \
        --out docs/validation/u9/implementation/mutations \
        --work /tmp/u9-mutations

The export contains only Git-tracked files from the working tree, so unrelated
untracked content is never copied or executed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
PYTEST = REPO_ROOT / ".venv" / "bin" / "pytest"

SMOKE = "scripts/smoke_wheel.py"
PACKAGING_TESTS = "tests/test_tui_packaging.py"
HELP_TESTS = "tests/test_tui_help.py"

NEW_TUI_MODULES = (
    "home.py",
    "why.py",
    "diff.py",
    "json_view.py",
    "agents.py",
    "compare.py",
    "doctor.py",
    "help.py",
)

NEW_SELECTIONS = (
    "tests/test_tui_routing.py",
    "tests/test_tui_help.py::test_complete_keyboard_browsing_flow_with_help_json_filters_and_refresh",
    "tests/test_tui_help.py::test_views_stay_on_captured_data_until_refresh_after_fixture_edits",
    "tests/test_tui_help.py::test_all_six_json_views_match_the_cli_serializer_on_same_inputs",
    "tests/test_tui_help.py::test_every_screen_and_help_remains_usable_at_both_sizes",
)

MANIFEST_SELECTION = [
    PACKAGING_TESTS,
    "-k",
    "manifest or missing_tui_module",
]
SELECTION_SELECTION = [
    PACKAGING_TESTS,
    "-k",
    "selection or manifest or missing_tui_module",
]
SDIST_SELECTION = [PACKAGING_TESTS, "-k", "sdist"]
LOCK_SELECTION = [PACKAGING_TESTS, "-k", "uv_lock"]


@dataclass(frozen=True)
class Mutation:
    id: str
    title: str
    path: str
    old: str
    new: str
    tests: list[str]
    expect: str


def _manifest_mutations() -> list[Mutation]:
    mutations: list[Mutation] = []
    for module in NEW_TUI_MODULES:
        entry = f'    "skill_lens/tui/{module}",\n'
        mutations.append(
            Mutation(
                id=f"manifest-omit-{Path(module).stem}",
                title=f"remove the {module} entry from the required archive manifest",
                path=SMOKE,
                old=entry,
                new="",
                tests=MANIFEST_SELECTION,
                expect="drifted from the independent U9 expectation",
            )
        )
    return mutations


def _selection_mutations() -> list[Mutation]:
    mutations: list[Mutation] = []
    for selection in NEW_SELECTIONS:
        entry = f'    "{selection}",\n'
        mutations.append(
            Mutation(
                id=f"selection-drop-{selection.split('/')[-1].replace('.py::', '-')[:52]}",
                title=f"remove the installed selection {selection}",
                path=SMOKE,
                old=entry,
                new="",
                tests=SELECTION_SELECTION,
                expect="INSTALLED_TUI_TEST_SUITES drifted from the independent",
            )
        )
    return mutations


def _other_mutations() -> list[Mutation]:
    size_decorator_both = '@pytest.mark.parametrize("size", [(100, 30), (60, 24)])\n'
    size_decorator_one = '@pytest.mark.parametrize("size", [(100, 30)])\n'
    size_function = "def test_every_screen_and_help_remains_usable_at_both_sizes("
    regex_prefix = '_PYTEST_SUMMARY_RE = re.compile(r"=+\\s*([^=\\n]*?)\\s+in\\s+[\\d.]+s'
    regex_with_elapsed = regex_prefix + '(?:\\s*\\([^)]*\\))?\\s*=+")'
    regex_without_elapsed = regex_prefix + '\\s*=+")'
    legacy_parser = (
        "\n".join(
            (
                "    _summary = re.search("
                r'"=+\\s*(.*?)\\s+in\\s+[\\d\\.]+s\\s*=+"'
                ", test_res.stdout)",
                '    _text = _summary.group(1) if _summary else ""',
                r'    _passed = re.search(r"(\d+)\s+passed", _text)',
                r'    _skipped = re.search(r"(\d+)\s+skipped", _text)',
                "    test_count = int(_passed.group(1)) if _passed else 0",
                "    skip_count = int(_skipped.group(1)) if _skipped else 0",
            )
        )
        + "\n"
    )
    zero_guard = (
        "\n".join(
            (
                "    if test_count <= 0:",
                "        raise AssertionError(",
                '            f"Installed test suites reported no passed tests for endpoint '
                '{endpoint_name!r}; "',
                '            f"the selection must execute:\\n{test_res.stdout[-4000:]}"',
                "        )",
            )
        )
        + "\n"
    )
    sdist_module_loop = (
        "    for mod in REQUIRED_TUI_MODULES:\n"
        '        target = f"{prefix}{mod}"\n'
        "        if target not in names:\n"
        "            missing.append(mod)\n"
    )
    sdist_module_ignored = (
        "    for mod in REQUIRED_TUI_MODULES:\n"
        '        target = f"{prefix}{mod}"\n'
        "        if target not in names:\n"
        "            pass  # mutation: omission not recorded\n"
    )
    return [
        Mutation(
            id="subprocess-filter-injected",
            title="leave a -k filter on the installed pytest command line",
            path=SMOKE,
            old='    test_cmd = [str(pytest_exe), *INSTALLED_TUI_TEST_SUITES, "-ra"]',
            new=(
                "    test_cmd = [\n"
                "        str(pytest_exe),\n"
                '        "-k",\n'
                '        "not test_every_screen",\n'
                "        *INSTALLED_TUI_TEST_SUITES,\n"
                '        "-ra",\n'
                "    ]"
            ),
            tests=[PACKAGING_TESTS, "-k", "expanded_installed_selection or override"],
            expect="does not carry the expected selection",
        ),
        Mutation(
            id="subprocess-selection-truncated",
            title="silently drop the last selection before the pytest call",
            path=SMOKE,
            old='    test_cmd = [str(pytest_exe), *INSTALLED_TUI_TEST_SUITES, "-ra"]',
            new='    test_cmd = [str(pytest_exe), *INSTALLED_TUI_TEST_SUITES[:-1], "-ra"]',
            tests=[PACKAGING_TESTS, "-k", "expanded_installed_selection or override"],
            expect="does not carry the expected selection",
        ),
        Mutation(
            id="sdist-module-loop-removed",
            title="stop checking required TUI modules in the source archive",
            path=SMOKE,
            old=sdist_module_loop,
            new="    # mutation: source-archive module loop removed\n",
            tests=SDIST_SELECTION,
            expect="DID NOT RAISE",
        ),
        Mutation(
            id="sdist-module-missing-not-collected",
            title="detect a missing sdist module but never record it",
            path=SMOKE,
            old=sdist_module_loop,
            new=sdist_module_ignored,
            tests=SDIST_SELECTION,
            expect="DID NOT RAISE",
        ),
        Mutation(
            id="selected-node-renamed",
            title="rename the selected browsing-flow test in the source suite",
            path=HELP_TESTS,
            old="def test_complete_keyboard_browsing_flow_with_help_json_filters_and_refresh(",
            new="def test_complete_keyboard_browsing_flow_renamed(",
            tests=[PACKAGING_TESTS, "-k", "installed_selection or manifest"],
            expect="resolves_to_a_real_test_node",
        ),
        Mutation(
            id="size-parametrization-shrunk",
            title="run the selected size case at one terminal size only",
            path=HELP_TESTS,
            old=size_decorator_both + size_function,
            new=size_decorator_one + size_function,
            tests=[PACKAGING_TESTS, "-k", "size_case or size_coverage"],
            expect="size_case_covers_both_terminal_sizes",
        ),
        Mutation(
            id="receipt-modern-summary-rejected",
            title="drop the elapsed parenthetical from the pytest summary pattern",
            path=SMOKE,
            old=regex_with_elapsed,
            new=regex_without_elapsed,
            tests=[PACKAGING_TESTS, "-k", "summary or counts_and_duration"],
            expect="could not find a pytest summary line",
        ),
        Mutation(
            id="receipt-legacy-parser-restored",
            title="restore the old parser that defaulted unknown summaries to zero",
            path=SMOKE,
            old="    test_count, skip_count = parse_pytest_summary(test_res.stdout)\n",
            new=legacy_parser,
            tests=[PACKAGING_TESTS, "-k", "unparsable or counts_and_duration"],
            expect="Installed test suites reported no passed tests",
        ),
        Mutation(
            id="receipt-zero-test-accepted",
            title="accept a lane whose summary reports no passed tests",
            path=SMOKE,
            old=zero_guard,
            new="    # mutation: positive-count guard removed\n",
            tests=[PACKAGING_TESTS, "-k", "passed_no_tests"],
            expect="DID NOT RAISE",
        ),
        Mutation(
            id="lock-root-version-stale",
            title="leave the lock root package at the previous version",
            path="uv.lock",
            old='[[package]]\nname = "skill-lens-cli"\nversion = "0.2.0"',
            new='[[package]]\nname = "skill-lens-cli"\nversion = "0.1.1"',
            tests=LOCK_SELECTION,
            expect="uv.lock records skill-lens-cli",
        ),
    ]


def build_mutations() -> list[Mutation]:
    return [*_manifest_mutations(), *_selection_mutations(), *_other_mutations()]


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_tracked_tree(dest: Path) -> dict[str, Any]:
    """Copy every Git-tracked file from the working tree into ``dest``."""
    listing = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z"],
        check=True,
        capture_output=True,
    ).stdout
    paths = [name for name in listing.split(b"\0") if name]
    digest = hashlib.sha256()
    copied = 0
    for raw in paths:
        relative = raw.decode("utf-8")
        source = REPO_ROOT / relative
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        digest.update(raw + b"\0")
        digest.update(file_sha256(source).encode("ascii"))
        copied += 1
    return {"files": copied, "sha256": digest.hexdigest()}


def run_pytest(tree: Path, selection: list[str], log_path: Path, tmp_home: Path) -> dict[str, Any]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(tmp_home),
        "XDG_CONFIG_HOME": str(tmp_home / ".config"),
        "PYTHONUNBUFFERED": "1",
        "PYTHONNOUSERSITE": "1",
    }
    command = [str(PYTEST), *selection, "-q", "-p", "no:cacheprovider"]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=str(tree),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    elapsed = time.monotonic() - started
    log_path.write_text(
        f"$ {' '.join(command)}\n(cwd={tree}, HOME={tmp_home})\n"
        f"exit={completed.returncode} elapsed={elapsed:.2f}s\n"
        f"--- STDOUT ---\n{completed.stdout}\n--- STDERR ---\n{completed.stderr}\n",
        encoding="utf-8",
    )
    return {
        "command": command,
        "exit_code": completed.returncode,
        "elapsed_seconds": round(elapsed, 2),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "log": log_path.name,
    }


def first_failure(stdout: str) -> list[str]:
    """Return the summary lines that name failing tests."""
    lines = [line.strip() for line in stdout.splitlines()]
    return [line for line in lines if line.startswith("FAILED ")]


def failure_kind(stdout: str, stderr: str) -> str:
    """Classify how a mutant run failed so collection/import errors are rejected."""
    combined = f"{stdout}\n{stderr}"
    if "ERROR collecting" in combined or "errors during collection" in combined:
        return "collection-error"
    if "SyntaxError" in combined:
        return "syntax-error"
    if "ModuleNotFoundError" in combined or "ImportError" in combined:
        return "import-error"
    if " failed" in combined or "DID NOT RAISE" in combined or "assert" in combined:
        return "behavioral-assertion"
    return "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Directory for logs and receipt.")
    parser.add_argument("--work", type=Path, default=None, help="Scratch directory outside repo.")
    parser.add_argument(
        "--only", type=str, default=None, help="Run only mutations whose id contains this."
    )
    args = parser.parse_args(argv)

    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    work_root = (
        Path(args.work).resolve()
        if args.work is not None
        else Path(tempfile.mkdtemp(prefix="u9-mutations-"))
    )
    work_root.mkdir(parents=True, exist_ok=True)

    pristine = work_root / "tree"
    if pristine.exists():
        shutil.rmtree(pristine)
    pristine.mkdir(parents=True)
    export_manifest = export_tracked_tree(pristine)

    mutations = build_mutations()
    if args.only:
        mutations = [m for m in mutations if args.only in m.id]

    receipt: list[dict[str, Any]] = []
    overall_ok = True
    for index, mutation in enumerate(mutations, start=1):
        mutant_tree = work_root / "runs" / mutation.id
        if mutant_tree.exists():
            shutil.rmtree(mutant_tree)
        mutant_tree.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(pristine, mutant_tree)

        target = mutant_tree / mutation.path
        pristine_bytes = (pristine / mutation.path).read_bytes()
        pristine_hash = hashlib.sha256(pristine_bytes).hexdigest()
        source_text = pristine_bytes.decode("utf-8")
        if source_text.count(mutation.old) != 1:
            raise SystemExit(
                f"{mutation.id}: pattern must appear exactly once in {mutation.path}; "
                f"found {source_text.count(mutation.old)}"
            )

        home = work_root / "homes" / mutation.id
        home.mkdir(parents=True, exist_ok=True)

        clean = run_pytest(
            pristine, mutation.tests, out_dir / f"{index:02d}-{mutation.id}.clean.log", home
        )

        target.write_text(source_text.replace(mutation.old, mutation.new), encoding="utf-8")
        mutant_hash = file_sha256(target)
        mutant = run_pytest(
            mutant_tree, mutation.tests, out_dir / f"{index:02d}-{mutation.id}.mutant.log", home
        )
        kind = failure_kind(mutant["stdout"], mutant["stderr"])
        expected_message_seen = mutation.expect in (mutant["stdout"] + mutant["stderr"])

        target.write_bytes(pristine_bytes)
        restored_hash = file_sha256(target)
        restored = run_pytest(
            mutant_tree, mutation.tests, out_dir / f"{index:02d}-{mutation.id}.restored.log", home
        )

        ok = (
            clean["exit_code"] == 0
            and mutant["exit_code"] != 0
            and kind == "behavioral-assertion"
            and expected_message_seen
            and restored["exit_code"] == 0
            and restored_hash == pristine_hash
            and mutant_hash != pristine_hash
        )
        overall_ok = overall_ok and ok
        receipt.append(
            {
                "id": mutation.id,
                "title": mutation.title,
                "file": mutation.path,
                "clean_exit": clean["exit_code"],
                "mutant_exit": mutant["exit_code"],
                "restored_exit": restored["exit_code"],
                "mutant_failure_kind": kind,
                "expected_message_seen": expected_message_seen,
                "expected_message": mutation.expect,
                "failing_tests": first_failure(mutant["stdout"]),
                "tests": mutation.tests,
                "pristine_sha256": pristine_hash,
                "mutant_sha256": mutant_hash,
                "restored_sha256": restored_hash,
                "logs": {
                    "clean": clean["log"],
                    "mutant": mutant["log"],
                    "restored": restored["log"],
                },
                "disposition": "caught" if ok else "NOT CAUGHT",
            }
        )
        print(f"[{index:02d}/{len(mutations)}] {mutation.id}: {'caught' if ok else 'NOT CAUGHT'}")

    summary = {
        "repo_root": str(REPO_ROOT),
        "python": sys.executable,
        "pytest": str(PYTEST),
        "work_root": str(work_root),
        "pristine_tree": export_manifest,
        "mutations": receipt,
        "total": len(receipt),
        "caught": sum(1 for item in receipt if item["disposition"] == "caught"),
        "all_caught": overall_ok,
        "claim_boundary": (
            "These deliberate breakages prove the named guards are load-bearing in disposable "
            "copies of the working tree. They are not exhaustive correctness evidence."
        ),
    }
    (out_dir / "mutations.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"caught {summary['caught']}/{summary['total']} mutations")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
