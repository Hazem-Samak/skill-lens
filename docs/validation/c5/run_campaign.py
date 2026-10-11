#!/usr/bin/env python3
"""Reproducible Step 0 (C5) Mutation Testing Campaign Harness.

Covers all five required categories from FULL_SCREEN_TUI.md §21.6 and C5 plan:
1. Explicit-empty inputs
2. Captured diff branch (outer/inner)
3. Identity translation (helper/service/real consumer)
4. Capture validation (captured-byte, second discovery validation, second config validation)
5. No-live-read boundary

All mutations execute strictly in an owned disposable copy outside the repo checkout.
For every pytest run:
- scratch CWD
- explicit copy-first PYTHONPATH
- exclude/clear __pycache__ and bytecode
- executing pytest process asserts and logs resolved skill_lens.__file__ and test module __file__
- normalization of /tmp vs /private/tmp
- fail-closed classification of genuine assertion kills vs invalid runs or survivors
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PYTHON = str(ROOT / ".venv" / "bin" / "python")

MUTATIONS: list[dict[str, Any]] = [
    {
        "id": "MUT-01",
        "category": "explicit-empty inputs",
        "name": "resolver_empty_overrides_treated_as_falsy",
        "description": "resolve_skill treats empty frozenset() as falsy and falls back to loader",
        "file": "skill_lens/core/resolver.py",
        "before": (
            "    overrides = (\n"
            "        disabled_overrides\n"
            "        if disabled_overrides is not None\n"
            "        else _load_disabled_overrides(agent, Path(index.home))\n"
            "    )"
        ),
        "after": (
            "    overrides = (\n"
            "        disabled_overrides\n"
            "        if disabled_overrides\n"
            "        else _load_disabled_overrides(agent, Path(index.home))\n"
            "    )"
        ),
        "selector": (
            "tests/test_phase2_gate.py::"
            "test_resolver_explicit_empty_overrides_keeps_enabled_without_settings_read"
        ),
        "expected_failure_substr": "Live settings loader must not be called",
    },
    {
        "id": "MUT-02",
        "category": "explicit-empty inputs (settings key)",
        "name": "disabled_overrides_hardcodes_shipped_key",
        "description": (
            "disabled_overrides_from_bytes hardcodes 'skillOverrides' "
            "instead of respecting agent.disabled_key"
        ),
        "file": "skill_lens/core/resolver.py",
        "before": "    override = parsed.get(agent.disabled_key)",
        "after": '    override = parsed.get("skillOverrides")',
        "selector": (
            "tests/test_snapshot_inputs.py::test_disabled_overrides_respects_configured_key"
        ),
        "expected_failure_substr": "disabled-by-shipped",
    },
    {
        "id": "MUT-03",
        "category": "captured diff branch (outer)",
        "name": "diff_outer_bypasses_captured_files_for_baseline",
        "description": "build_diff_report passes captured_files=None to baseline _copy_files call",
        "file": "skill_lens/core/diff.py",
        "before": (
            "        if baseline_files is None:\n"
            "            baseline_files = _copy_files(baseline, captured_files=captured_files)"
        ),
        "after": (
            "        if baseline_files is None:\n"
            "            baseline_files = _copy_files(baseline, captured_files=None)"
        ),
        "selector": (
            "tests/test_phase3_gate.py::"
            "test_diff_falsey_mapping_exercises_captured_branch_without_live_reads"
        ),
        "expected_failure_substr": "Path.is_dir banned",
    },
    {
        "id": "MUT-04",
        "category": "captured diff branch (inner)",
        "name": "diff_inner_copy_files_checks_truthiness_of_captured_files",
        "description": "_copy_files treats falsey mapping as None, bypassing captured files",
        "file": "skill_lens/core/diff.py",
        "before": ("    if captured_files is not None:\n        key = canonical_key(entry)"),
        "after": ("    if captured_files:\n        key = canonical_key(entry)"),
        "selector": (
            "tests/test_phase3_gate.py::"
            "test_diff_falsey_mapping_exercises_captured_branch_without_live_reads"
        ),
        "expected_failure_substr": "Path.is_dir banned",
    },
    {
        "id": "MUT-05",
        "category": "identity translation (real consumer)",
        "name": "resolver_identity_names_directory_only_for_hybrid_and_either",
        "description": (
            "_identity_names returns only directory_name for hybrid and either policies"
        ),
        "file": "skill_lens/core/resolver.py",
        "before": (
            '    if agent.identity_source == "frontmatter_name":\n'
            "        return {frontmatter_name}\n"
            "    return {directory_name, frontmatter_name}"
        ),
        "after": (
            '    if agent.identity_source == "frontmatter_name":\n'
            "        return {frontmatter_name}\n"
            "    return {directory_name}"
        ),
        "selector": "tests/test_phase2_gate.py::test_hybrid_and_either_resolver_identity",
        "expected_failure_substr": "assert rep_declared_ag.found is True",
    },
    {
        "id": "MUT-06",
        "category": "identity translation (helper)",
        "name": "lookup_name_for_entry_ignores_frontmatter_policy",
        "description": (
            "lookup_name_for_entry always selects directory_name regardless of agent policy"
        ),
        "file": "skill_lens/core/resolver.py",
        "before": (
            "    chosen = frontmatter_name if agent.identity_source == "
            '"frontmatter_name" else directory_name'
        ),
        "after": "    chosen = directory_name",
        "selector": "tests/test_snapshot_inputs.py::test_selected_entry_uses_agent_identity",
        "expected_failure_substr": "assert chosen in _identity_names(agent, entry)",
    },
    {
        "id": "MUT-07",
        "category": "identity translation (service)",
        "name": "snapshot_why_uses_raw_directory_name",
        "description": "snapshot_why bypasses lookup_name_for_entry and passes entry.name directly",
        "file": "skill_lens/core/snapshot.py",
        "before": (
            "    agent = registry_dict[agent_id]\n"
            "    lookup_name = lookup_name_for_entry(entry, agent)"
        ),
        "after": ("    agent = registry_dict[agent_id]\n    lookup_name = entry.name"),
        "selector": "tests/test_session_snapshot.py::test_snapshot_reports_match_live_reports",
        "expected_failure_substr": "assert snap_why.to_dict() == live_why.to_dict()",
    },
    {
        "id": "MUT-08",
        "category": "capture validation (captured-byte)",
        "name": "capture_session_bypasses_source_reparse_check",
        "description": (
            "capture_session suppresses reparsed.to_dict() / body comparison against entry.parse"
        ),
        "file": "skill_lens/core/snapshot.py",
        "before": (
            "            if (\n"
            "                reparsed.to_dict() != entry.parse.to_dict()\n"
            "                or reparsed.body != entry.parse.body\n"
            "                or reparsed.frontmatter != entry.parse.frontmatter\n"
            "            ):"
        ),
        "after": (
            "            if False and (\n"
            "                reparsed.to_dict() != entry.parse.to_dict()\n"
            "                or reparsed.body != entry.parse.body\n"
            "                or reparsed.frontmatter != entry.parse.frontmatter\n"
            "            ):"
        ),
        "selector": "tests/test_session_snapshot.py::test_change_during_capture_is_rejected",
        "expected_failure_substr": "Failed: DID NOT RAISE SnapshotChanged",
    },
    {
        "id": "MUT-09",
        "category": "capture validation (second-pass discovery)",
        "name": "capture_session_bypasses_second_discovery_hash_check",
        "description": (
            "capture_session suppresses second-discovery content_hash drift check in second pass"
        ),
        "file": "skill_lens/core/snapshot.py",
        "before": "e1.content_hash != e2.content_hash",
        "after": "False and e1.content_hash != e2.content_hash",
        "selector": "tests/test_session_snapshot.py::test_change_during_capture_is_rejected",
        "expected_failure_substr": "Failed: DID NOT RAISE SnapshotChanged",
    },
    {
        "id": "MUT-10",
        "category": "capture validation (second-pass config)",
        "name": "capture_session_bypasses_config_reread_comparison",
        "description": (
            "capture_session suppresses the reread config validation comparison in second pass"
        ),
        "file": "skill_lens/core/snapshot.py",
        "before": (
            "    for path_str, ci in config_inputs.items():\n"
            "        new_ci = _read_input_guarded(Path(path_str), cancelled=cancelled)\n"
            "        if ci != new_ci:"
        ),
        "after": (
            "    for path_str, ci in config_inputs.items():\n"
            "        new_ci = _read_input_guarded(Path(path_str), cancelled=cancelled)\n"
            "        if False and ci != new_ci:"
        ),
        "selector": "tests/test_session_snapshot.py::test_change_during_capture_is_rejected",
        "expected_failure_substr": "Failed: DID NOT RAISE SnapshotChanged",
    },
    {
        "id": "MUT-11",
        "category": "no-live-read boundary (display paths)",
        "name": "snapshot_path_calls_live_paths_display",
        "description": (
            "snapshot_path falls back to live paths.display rather than stored mapping"
        ),
        "file": "skill_lens/core/snapshot.py",
        "before": (
            "def snapshot_path(snapshot: SessionSnapshot, path: str) -> str:\n"
            '    """Return stored display path or the literal string unchanged."""\n'
            "    return snapshot.display_paths.get(path, path)"
        ),
        "after": (
            "def snapshot_path(snapshot: SessionSnapshot, path: str) -> str:\n"
            '    """Return stored display path or the literal string unchanged."""\n'
            "    return paths.display(Path(path))"
        ),
        "selector": "tests/test_session_snapshot.py::test_navigation_has_no_filesystem_fallback",
        "expected_failure_substr": "Forbidden live probe invoked during navigation",
    },
    {
        "id": "MUT-12",
        "category": "no-live-read boundary (same location)",
        "name": "snapshot_same_location_calls_live_paths_probe",
        "description": "snapshot_same_location falls back to live paths.same_location probe",
        "file": "skill_lens/core/snapshot.py",
        "before": (
            "def snapshot_same_location(snapshot: SessionSnapshot, a: str, b: str) -> bool:\n"
            '    """Return whether two paths refer to the same location without disk probes."""\n'
            "    return a == b or (a, b) in snapshot.same_locations"
        ),
        "after": (
            "def snapshot_same_location(snapshot: SessionSnapshot, a: str, b: str) -> bool:\n"
            '    """Return whether two paths refer to the same location without disk probes."""\n'
            "    return paths.same_location(Path(a), Path(b))"
        ),
        "selector": "tests/test_session_snapshot.py::test_navigation_has_no_filesystem_fallback",
        "expected_failure_substr": "Forbidden live probe invoked during navigation",
    },
]


def clear_bytecode(directory: Path) -> None:
    """Recursively remove __pycache__ and *.pyc files."""
    for p in list(directory.rglob("__pycache__")):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
    for p in list(directory.rglob("*.pyc")):
        with contextlib.suppress(OSError):
            p.unlink()


def hash_file(path: Path) -> str:
    """Return SHA256 of file contents."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def create_scratch_copy() -> tuple[Path, Path]:
    """Create owned disposable copy outside git checkout and unique evidence directory."""
    scratch = Path(tempfile.mkdtemp(prefix="c5-mutations-", dir="/tmp")).resolve()
    evidence_dir = Path(tempfile.mkdtemp(prefix="c5-evidence-", dir="/tmp")).resolve()

    # Copy skill_lens and tests
    for name in ("skill_lens", "tests"):
        shutil.copytree(
            ROOT / name,
            scratch / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )

    # Copy other tracked files
    tracked = (
        subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    )
    for rel in tracked:
        if rel and not rel.startswith(("skill_lens/", "tests/")):
            src = ROOT / rel
            dst = scratch / rel
            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

    # Synthetic HOME
    (scratch / "home").mkdir(parents=True, exist_ok=True)

    # Hook conftest.py in scratch to enforce executing-process provenance & execution reporting
    conftest_hook = """
# --- Mutation Testing In-Process Provenance & Execution Guard ---
import json as _prov_json
import os as _prov_os
from pathlib import Path as _ProvPath
import pytest as _prov_pytest
import sys as _prov_sys

@_prov_pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    import skill_lens
    pkg = _ProvPath(skill_lens.__file__).resolve()
    expected = _ProvPath(_prov_os.environ["MUTATION_SCRATCH_DIR"]).resolve()
    assert pkg.is_relative_to(expected), f"Package imported from {pkg}, not {expected}"

@_prov_pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    log_path = _prov_os.environ.get("MUTATION_RUN_LOG")
    if log_path:
        import skill_lens
        pkg = _ProvPath(skill_lens.__file__).resolve()
        expected = _ProvPath(_prov_os.environ["MUTATION_SCRATCH_DIR"]).resolve()

        mod_obj = getattr(item, "module", None)
        mod_file = _ProvPath(getattr(mod_obj, "__file__", "")).resolve() if mod_obj else None

        assert pkg.is_relative_to(expected), f"Package {pkg} outside scratch {expected}"
        assert mod_file is not None and mod_file.is_relative_to(expected), (
            f"Test module {mod_file} outside scratch {expected}"
        )

        exc_type = call.excinfo.typename if call.excinfo else None
        exc_msg = str(call.excinfo.value) if call.excinfo else None

        entry = {
            "nodeid": item.nodeid,
            "when": rep.when,
            "outcome": rep.outcome,
            "skill_lens_file": str(pkg),
            "test_module_file": str(mod_file),
            "exc_type": exc_type,
            "exc_message": exc_msg,
            "longrepr": str(rep.longrepr) if rep.failed else None,
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(_prov_json.dumps(entry) + "\\n")
"""
    conftest_path = scratch / "tests" / "conftest.py"
    conftest_text = conftest_path.read_text(encoding="utf-8")
    conftest_path.write_text(conftest_text + conftest_hook, encoding="utf-8")

    clear_bytecode(scratch)
    return scratch, evidence_dir


def run_pytest(
    scratch: Path,
    selector: str,
    evidence_log: Path,
    run_log: Path,
) -> tuple[int, str, list[dict[str, Any]]]:
    """Execute focused pytest in scratch with provenance and execution recording."""
    clear_bytecode(scratch)
    if run_log.exists():
        run_log.unlink()

    env = os.environ.copy()
    env["HOME"] = str((scratch / "home").resolve())
    env["PYTHONPATH"] = str(scratch.resolve())
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MUTATION_SCRATCH_DIR"] = str(scratch.resolve())
    env["MUTATION_RUN_LOG"] = str(run_log.resolve())
    env.pop("XDG_CONFIG_HOME", None)

    cmd = [
        PYTHON,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        selector,
    ]

    proc = subprocess.run(
        cmd,
        cwd=scratch,
        env=env,
        text=True,
        capture_output=True,
    )
    combined_output = proc.stdout + "\n" + proc.stderr
    evidence_log.write_text(combined_output, encoding="utf-8")

    entries: list[dict[str, Any]] = []
    if run_log.exists():
        for line in run_log.read_text(encoding="utf-8").strip().splitlines():
            if line:
                entries.append(json.loads(line))

    return proc.returncode, combined_output, entries


def nodeid_matches_selector(nodeid: str, selector: str) -> bool:
    """Check if executed nodeid matches the expected selector."""
    if not selector or nodeid == selector:
        return True
    if "::" in selector and not selector.endswith("]") and nodeid.startswith(f"{selector}["):
        return True
    return bool("::" not in selector and nodeid.startswith(f"{selector}::"))


def evaluate_control_run(
    rc: int,
    combined_output: str,
    entries: list[dict[str, Any]],
    expected_selector: str,
    scratch: Path,
    expected_count: int = 1,
) -> dict[str, Any]:
    """Evaluate control/restored run. Must pass cleanly with valid scratch provenance."""
    if rc != 0:
        return {
            "status": "INVALID",
            "reason": f"nonzero_exit_code_{rc}",
            "details": combined_output[-500:],
        }

    # Reject non-call failures (setup, teardown, etc.)
    non_call_failures = [
        e for e in entries if e.get("when") != "call" and e.get("outcome") == "failed"
    ]
    if non_call_failures:
        ncf = non_call_failures[0]
        when = ncf.get("when", "non_call")
        return {
            "status": "INVALID",
            "reason": f"{when}_phase_failed",
            "details": ncf.get("exc_message"),
        }

    call_entries = [e for e in entries if e.get("when") == "call"]
    if not call_entries:
        return {
            "status": "INVALID",
            "reason": "no_tests_executed",
            "details": combined_output[-500:],
        }

    # Reject duplicate call records
    nodeids = [e.get("nodeid") for e in call_entries]
    if len(nodeids) != len(set(nodeids)):
        return {
            "status": "INVALID",
            "reason": "duplicate_call_records",
            "details": nodeids,
        }

    if len(call_entries) != expected_count:
        return {
            "status": "INVALID",
            "reason": f"call_count_mismatch_{len(call_entries)}_expected_{expected_count}",
            "details": nodeids,
        }

    # Verify EXACT selected nodeid for nonparameterized campaign selectors
    for e in call_entries:
        nid = e.get("nodeid", "")
        if not nodeid_matches_selector(nid, expected_selector):
            return {
                "status": "INVALID",
                "reason": f"selector_mismatch_got_{nid}_expected_{expected_selector}",
                "details": nid,
            }

    scratch_res = scratch.resolve()
    for e in call_entries:
        pkg = Path(e.get("skill_lens_file", "")).resolve()
        mod = Path(e.get("test_module_file", "")).resolve()
        if not (pkg.is_relative_to(scratch_res) and mod.is_relative_to(scratch_res)):
            return {
                "status": "INVALID",
                "reason": "provenance_outside_scratch",
                "pkg": str(pkg),
                "mod": str(mod),
            }
        outcome = e.get("outcome")
        if outcome != "passed":
            return {
                "status": "INVALID",
                "reason": f"test_did_not_pass_{outcome}",
                "details": e.get("exc_message"),
            }

    return {
        "status": "PASS",
        "count": len(call_entries),
        "provenance": {
            "nodeid": call_entries[0]["nodeid"],
            "skill_lens_file": call_entries[0]["skill_lens_file"],
            "test_module_file": call_entries[0]["test_module_file"],
        },
    }


def evaluate_mutant_run(
    rc: int,
    combined_output: str,
    entries: list[dict[str, Any]],
    expected_substr: str,
    expected_count: int,
    scratch: Path,
    expected_selector: str = "",
) -> dict[str, Any]:
    """Evaluate mutant run fail-closed.

    Only clean scratch provenance and a genuine named-test call-phase AssertionError
    or pytest Failed matching expected_substr count as a kill.
    All syntax errors, import errors, internal errors, missing/wrong provenance,
    setup/teardown failures, duplicate records, or non-assertion exceptions
    are classified as INVALID.
    """
    if rc not in (0, 1):
        return {
            "status": "INVALID",
            "verdict": f"invalid_process_exit_{rc}",
            "killed": False,
            "reason": f"pytest_abnormal_exit_code_{rc}",
            "details": combined_output[-500:],
        }

    # Check for syntax/import/module errors in output
    for err_name in ("SyntaxError", "ImportError", "ModuleNotFoundError"):
        if err_name in combined_output:
            return {
                "status": "INVALID",
                "verdict": f"invalid_{err_name.lower()}",
                "killed": False,
                "reason": f"detected_{err_name}",
                "details": combined_output[-500:],
            }

    if not entries:
        return {
            "status": "INVALID",
            "verdict": "invalid_missing_provenance_and_run_log",
            "killed": False,
            "reason": "no_tests_logged",
            "details": combined_output[-500:],
        }

    # Fail any non-call setup/teardown/collection error rather than count as kill
    non_call_failures = [
        e for e in entries if e.get("when") != "call" and e.get("outcome") == "failed"
    ]
    if non_call_failures:
        ncf = non_call_failures[0]
        when = ncf.get("when", "non_call")
        exc_type = ncf.get("exc_type")
        return {
            "status": "INVALID",
            "verdict": f"invalid_{when}_failure_{exc_type}",
            "killed": False,
            "reason": f"{when}_phase_failed",
            "details": ncf.get("exc_message"),
        }

    call_entries = [e for e in entries if e.get("when") == "call"]
    if not call_entries:
        return {
            "status": "INVALID",
            "verdict": "invalid_no_call_phase_executed",
            "killed": False,
            "reason": "no_call_entries",
            "details": combined_output[-500:],
        }

    # Reject duplicate call records
    nodeids = [e.get("nodeid") for e in call_entries]
    if len(nodeids) != len(set(nodeids)):
        return {
            "status": "INVALID",
            "verdict": "invalid_duplicate_call_records",
            "killed": False,
            "reason": "duplicate_call_records",
            "details": nodeids,
        }

    if len(call_entries) != expected_count:
        return {
            "status": "INVALID",
            "verdict": "invalid_test_count_mismatch",
            "killed": False,
            "reason": f"executed_{len(call_entries)}_expected_{expected_count}",
            "details": nodeids,
        }

    # Verify EXACT selected nodeid for nonparameterized campaign selectors
    if expected_selector:
        for e in call_entries:
            nid = e.get("nodeid", "")
            if not nodeid_matches_selector(nid, expected_selector):
                return {
                    "status": "INVALID",
                    "verdict": "invalid_selector_mismatch",
                    "killed": False,
                    "reason": f"selector_mismatch_got_{nid}_expected_{expected_selector}",
                    "details": nid,
                }

    scratch_res = scratch.resolve()
    for e in call_entries:
        pkg = Path(e.get("skill_lens_file", "")).resolve()
        mod = Path(e.get("test_module_file", "")).resolve()
        if not (pkg.is_relative_to(scratch_res) and mod.is_relative_to(scratch_res)):
            return {
                "status": "INVALID",
                "verdict": "invalid_provenance_mismatch",
                "killed": False,
                "reason": "provenance_outside_scratch",
                "pkg": str(pkg),
                "mod": str(mod),
            }

    # If rc == 0: must be survivor if all tests passed; rc 0 with any failed call is invalid
    if rc == 0:
        if all(e.get("outcome") == "passed" for e in call_entries):
            return {
                "status": "SURVIVOR",
                "verdict": "survived",
                "killed": False,
                "reason": "all_tests_passed_under_mutant",
                "provenance": {
                    "nodeid": call_entries[0]["nodeid"],
                    "skill_lens_file": call_entries[0]["skill_lens_file"],
                    "test_module_file": call_entries[0]["test_module_file"],
                },
                "test_count": len(call_entries),
            }
        return {
            "status": "INVALID",
            "verdict": "invalid_zero_exit_with_call_failure",
            "killed": False,
            "reason": "rc_is_0_but_call_recorded_failure",
            "details": combined_output[-500:],
        }

    # Mutant rc 1 is strictly required for kill
    if rc != 1:
        return {
            "status": "INVALID",
            "verdict": f"invalid_process_exit_{rc}",
            "killed": False,
            "reason": f"kill_requires_rc_1_got_{rc}",
            "details": combined_output[-500:],
        }

    # Locate failed call entry
    failed_calls = [e for e in call_entries if e.get("outcome") == "failed"]
    if not failed_calls:
        return {
            "status": "INVALID",
            "verdict": "invalid_non_call_failure",
            "killed": False,
            "reason": "rc_is_1_but_no_call_marked_failed",
            "details": combined_output[-500:],
        }

    failed_call = failed_calls[0]
    exc_type = failed_call.get("exc_type")

    # Genuine test assertions in pytest are AssertionError or pytest.Failed (e.g. DID NOT RAISE)
    if exc_type not in ("AssertionError", "Failed"):
        return {
            "status": "INVALID",
            "verdict": f"invalid_non_assertion_error_{exc_type}",
            "killed": False,
            "reason": f"exception_type_{exc_type}_is_not_an_assertion",
            "details": failed_call.get("exc_message"),
        }

    # Marker evidence should belong to the failed named call, not arbitrary full process output
    msg = failed_call.get("exc_message") or ""
    longrepr = failed_call.get("longrepr") or ""
    found_expected = expected_substr in msg or expected_substr in longrepr

    if not found_expected:
        return {
            "status": "INVALID",
            "verdict": "invalid_mismatched_failure_marker",
            "killed": False,
            "reason": f"expected_substr_{expected_substr}_not_found",
            "actual_message": msg,
            "details": combined_output[-500:],
        }

    return {
        "status": "KILLED",
        "verdict": "killed_by_expected_assertion",
        "killed": True,
        "exc_type": exc_type,
        "expected_substr": expected_substr,
        "found_expected_substr": True,
        "provenance": {
            "nodeid": failed_call["nodeid"],
            "skill_lens_file": failed_call["skill_lens_file"],
            "test_module_file": failed_call["test_module_file"],
        },
        "test_count": len(call_entries),
        "tail_output": combined_output[-1000:],
    }


def verify_collection_parity(scratch: Path) -> dict[str, Any]:
    """Verify clean-copy collection matches the active tree's current collection."""
    env_root = os.environ.copy()
    env_root["HOME"] = str((scratch / "home").resolve())
    env_root.pop("XDG_CONFIG_HOME", None)

    proc_root = subprocess.run(
        [PYTHON, "-m", "pytest", "--collect-only", "-q"],
        cwd=ROOT,
        env=env_root,
        text=True,
        capture_output=True,
        check=True,
    )
    root_lines = [line.strip() for line in proc_root.stdout.splitlines() if "::" in line]

    env_scratch = os.environ.copy()
    env_scratch["HOME"] = str((scratch / "home").resolve())
    env_scratch["PYTHONPATH"] = str(scratch.resolve())
    env_scratch["PYTHONDONTWRITEBYTECODE"] = "1"
    env_scratch["MUTATION_SCRATCH_DIR"] = str(scratch.resolve())
    env_scratch.pop("XDG_CONFIG_HOME", None)

    proc_scratch = subprocess.run(
        [PYTHON, "-m", "pytest", "--collect-only", "-q"],
        cwd=scratch,
        env=env_scratch,
        text=True,
        capture_output=True,
        check=True,
    )
    scratch_lines = [line.strip() for line in proc_scratch.stdout.splitlines() if "::" in line]

    assert root_lines == scratch_lines, (
        f"Collection mismatch: {len(root_lines)} vs {len(scratch_lines)}"
    )
    return {
        "status": "matched",
        "collected_count": len(root_lines),
    }


def run_runner_self_test(scratch: Path) -> list[dict[str, Any]]:
    """Self-test demonstrating runner fail-closed rejection of defects and survivors."""
    probe_scratch = scratch.resolve()
    scenarios: list[dict[str, Any]] = [
        {
            "name": "syntax_error_rejection",
            "rc": 1,
            "output": "SyntaxError: invalid syntax in injected mutant",
            "entries": [],
            "expected_substr": "some_marker",
            "expected_status": "INVALID",
            "expected_killed": False,
        },
        {
            "name": "pytest_internal_error_rejection",
            "rc": 3,
            "output": "INTERNALERROR> pytest crash",
            "entries": [],
            "expected_substr": "some_marker",
            "expected_status": "INVALID",
            "expected_killed": False,
        },
        {
            "name": "missing_provenance_rejection",
            "rc": 1,
            "output": "AssertionError: failed without provenance log",
            "entries": [],
            "expected_substr": "some_marker",
            "expected_status": "INVALID",
            "expected_killed": False,
        },
        {
            "name": "provenance_outside_scratch_rejection",
            "rc": 1,
            "output": "AssertionError: failed",
            "entries": [
                {
                    "nodeid": "tests/test_x.py::test_y",
                    "when": "call",
                    "outcome": "failed",
                    "skill_lens_file": "/other/path/skill_lens/__init__.py",
                    "test_module_file": str(probe_scratch / "tests" / "test_x.py"),
                    "exc_type": "AssertionError",
                    "exc_message": "failed marker",
                }
            ],
            "expected_substr": "failed marker",
            "expected_status": "INVALID",
            "expected_killed": False,
        },
        {
            "name": "non_assertion_error_rejection",
            "rc": 1,
            "output": "KeyError: missing key",
            "entries": [
                {
                    "nodeid": "tests/test_x.py::test_y",
                    "when": "call",
                    "outcome": "failed",
                    "skill_lens_file": str(probe_scratch / "skill_lens" / "__init__.py"),
                    "test_module_file": str(probe_scratch / "tests" / "test_x.py"),
                    "exc_type": "KeyError",
                    "exc_message": "missing key",
                }
            ],
            "expected_substr": "missing key",
            "expected_status": "INVALID",
            "expected_killed": False,
        },
        {
            "name": "mismatched_failure_marker_rejection",
            "rc": 1,
            "output": "AssertionError: unexpected message",
            "entries": [
                {
                    "nodeid": "tests/test_x.py::test_y",
                    "when": "call",
                    "outcome": "failed",
                    "skill_lens_file": str(probe_scratch / "skill_lens" / "__init__.py"),
                    "test_module_file": str(probe_scratch / "tests" / "test_x.py"),
                    "exc_type": "AssertionError",
                    "exc_message": "unexpected message",
                }
            ],
            "expected_substr": "expected_marker_not_here",
            "expected_status": "INVALID",
            "expected_killed": False,
        },
        {
            "name": "marker_only_in_process_output_rejection",
            "rc": 1,
            "output": "Process log: expected_marker found in random stdout",
            "entries": [
                {
                    "nodeid": "tests/test_x.py::test_y",
                    "when": "call",
                    "outcome": "failed",
                    "skill_lens_file": str(probe_scratch / "skill_lens" / "__init__.py"),
                    "test_module_file": str(probe_scratch / "tests" / "test_x.py"),
                    "exc_type": "AssertionError",
                    "exc_message": "actual assertion message without marker",
                }
            ],
            "expected_substr": "expected_marker",
            "expected_status": "INVALID",
            "expected_killed": False,
        },
        {
            "name": "wrong_mutant_selector_rejection",
            "rc": 1,
            "output": "AssertionError: expected_marker",
            "expected_selector": "tests/test_expected.py::test_expected",
            "entries": [
                {
                    "nodeid": "tests/test_wrong.py::test_wrong",
                    "when": "call",
                    "outcome": "failed",
                    "skill_lens_file": str(probe_scratch / "skill_lens" / "__init__.py"),
                    "test_module_file": str(probe_scratch / "tests" / "test_wrong.py"),
                    "exc_type": "AssertionError",
                    "exc_message": "expected_marker",
                }
            ],
            "expected_substr": "expected_marker",
            "expected_status": "INVALID",
            "expected_killed": False,
        },
        {
            "name": "zero_exit_with_failure_rejection",
            "rc": 0,
            "output": "AssertionError: expected_marker",
            "expected_selector": "tests/test_x.py::test_y",
            "entries": [
                {
                    "nodeid": "tests/test_x.py::test_y",
                    "when": "call",
                    "outcome": "failed",
                    "skill_lens_file": str(probe_scratch / "skill_lens" / "__init__.py"),
                    "test_module_file": str(probe_scratch / "tests" / "test_x.py"),
                    "exc_type": "AssertionError",
                    "exc_message": "expected_marker",
                }
            ],
            "expected_substr": "expected_marker",
            "expected_status": "INVALID",
            "expected_killed": False,
        },
        {
            "name": "call_failure_and_teardown_error_rejection",
            "rc": 1,
            "output": "AssertionError: expected_marker\nERROR at teardown",
            "expected_selector": "tests/test_x.py::test_y",
            "entries": [
                {
                    "nodeid": "tests/test_x.py::test_y",
                    "when": "call",
                    "outcome": "failed",
                    "skill_lens_file": str(probe_scratch / "skill_lens" / "__init__.py"),
                    "test_module_file": str(probe_scratch / "tests" / "test_x.py"),
                    "exc_type": "AssertionError",
                    "exc_message": "expected_marker",
                },
                {
                    "nodeid": "tests/test_x.py::test_y",
                    "when": "teardown",
                    "outcome": "failed",
                    "skill_lens_file": str(probe_scratch / "skill_lens" / "__init__.py"),
                    "test_module_file": str(probe_scratch / "tests" / "test_x.py"),
                    "exc_type": "OSError",
                    "exc_message": "teardown failed",
                },
            ],
            "expected_substr": "expected_marker",
            "expected_status": "INVALID",
            "expected_killed": False,
        },
        {
            "name": "mutant_test_count_mismatch_rejection",
            "rc": 1,
            "output": "AssertionError: expected_marker",
            "expected_count": 1,
            "expected_selector": "tests/test_x.py::test_y",
            "entries": [
                {
                    "nodeid": "tests/test_x.py::test_y",
                    "when": "call",
                    "outcome": "failed",
                    "skill_lens_file": str(probe_scratch / "skill_lens" / "__init__.py"),
                    "test_module_file": str(probe_scratch / "tests" / "test_x.py"),
                    "exc_type": "AssertionError",
                    "exc_message": "expected_marker",
                },
                {
                    "nodeid": "tests/test_x.py::test_z",
                    "when": "call",
                    "outcome": "passed",
                    "skill_lens_file": str(probe_scratch / "skill_lens" / "__init__.py"),
                    "test_module_file": str(probe_scratch / "tests" / "test_x.py"),
                },
            ],
            "expected_substr": "expected_marker",
            "expected_status": "INVALID",
            "expected_killed": False,
        },
        {
            "name": "duplicate_call_records_rejection",
            "rc": 1,
            "output": "AssertionError: expected_marker",
            "expected_count": 2,
            "expected_selector": "tests/test_x.py::test_y",
            "entries": [
                {
                    "nodeid": "tests/test_x.py::test_y",
                    "when": "call",
                    "outcome": "failed",
                    "skill_lens_file": str(probe_scratch / "skill_lens" / "__init__.py"),
                    "test_module_file": str(probe_scratch / "tests" / "test_x.py"),
                    "exc_type": "AssertionError",
                    "exc_message": "expected_marker",
                },
                {
                    "nodeid": "tests/test_x.py::test_y",
                    "when": "call",
                    "outcome": "failed",
                    "skill_lens_file": str(probe_scratch / "skill_lens" / "__init__.py"),
                    "test_module_file": str(probe_scratch / "tests" / "test_x.py"),
                    "exc_type": "AssertionError",
                    "exc_message": "expected_marker",
                },
            ],
            "expected_substr": "expected_marker",
            "expected_status": "INVALID",
            "expected_killed": False,
        },
        {
            "name": "wrong_control_selector_rejection",
            "type": "control",
            "rc": 0,
            "output": "1 passed",
            "expected_selector": "tests/test_expected.py::test_expected",
            "entries": [
                {
                    "nodeid": "tests/test_wrong.py::test_wrong",
                    "when": "call",
                    "outcome": "passed",
                    "skill_lens_file": str(probe_scratch / "skill_lens" / "__init__.py"),
                    "test_module_file": str(probe_scratch / "tests" / "test_wrong.py"),
                }
            ],
            "expected_status": "INVALID",
            "expected_killed": False,
        },
        {
            "name": "genuine_survivor_detection",
            "rc": 0,
            "output": "1 passed in 0.1s",
            "expected_selector": "tests/test_x.py::test_y",
            "entries": [
                {
                    "nodeid": "tests/test_x.py::test_y",
                    "when": "call",
                    "outcome": "passed",
                    "skill_lens_file": str(probe_scratch / "skill_lens" / "__init__.py"),
                    "test_module_file": str(probe_scratch / "tests" / "test_x.py"),
                }
            ],
            "expected_substr": "expected_marker",
            "expected_status": "SURVIVOR",
            "expected_killed": False,
        },
        {
            "name": "genuine_kill_acceptance",
            "rc": 1,
            "output": "AssertionError: expected_marker",
            "expected_selector": "tests/test_x.py::test_y",
            "entries": [
                {
                    "nodeid": "tests/test_x.py::test_y",
                    "when": "call",
                    "outcome": "failed",
                    "skill_lens_file": str(probe_scratch / "skill_lens" / "__init__.py"),
                    "test_module_file": str(probe_scratch / "tests" / "test_x.py"),
                    "exc_type": "AssertionError",
                    "exc_message": "expected_marker",
                }
            ],
            "expected_substr": "expected_marker",
            "expected_status": "KILLED",
            "expected_killed": True,
        },
    ]

    results: list[dict[str, Any]] = []
    for sc in scenarios:
        if sc.get("type") == "control":
            res = evaluate_control_run(
                sc["rc"],
                sc["output"],
                sc["entries"],
                sc["expected_selector"],
                probe_scratch,
                expected_count=sc.get("expected_count", 1),
            )
            assert res["status"] == sc["expected_status"], (
                f"Self-test {sc['name']}: expected {sc['expected_status']}, got {res['status']}"
            )
            results.append(
                {
                    "scenario": sc["name"],
                    "result_status": res["status"],
                    "killed": False,
                    "verdict": res.get("reason"),
                    "passed_validation": True,
                }
            )
        else:
            res = evaluate_mutant_run(
                sc["rc"],
                sc["output"],
                sc["entries"],
                sc["expected_substr"],
                sc.get("expected_count", 1),
                probe_scratch,
                expected_selector=sc.get("expected_selector", "tests/test_x.py::test_y"),
            )
            assert res["status"] == sc["expected_status"], (
                f"Self-test {sc['name']}: expected {sc['expected_status']}, got {res['status']}"
            )
            assert res["killed"] == sc["expected_killed"], (
                f"Self-test {sc['name']}: expected killed={sc['expected_killed']}, "
                f"got {res['killed']}"
            )
            results.append(
                {
                    "scenario": sc["name"],
                    "result_status": res["status"],
                    "killed": res["killed"],
                    "verdict": res.get("verdict"),
                    "passed_validation": True,
                }
            )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run C5 mutation testing campaign.")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=ROOT / "docs" / "validation" / "c5" / "results.json",
        help="Output path for results JSON artifact.",
    )
    parser.add_argument(
        "--validate-runner",
        action="store_true",
        help="Run only the runner self-test validating fail-closed defect rejection.",
    )
    args = parser.parse_args()

    print("Starting C5 mutation testing campaign against disposable scratch copy...")
    scratch, evidence_dir = create_scratch_copy()
    print(f"Scratch copy initialized at: {scratch}")
    print(f"Unique evidence directory: {evidence_dir}")

    # Inspect key source hashes for provenance metadata
    git_rev = (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode("utf-8").strip()
    )
    inspected_files = [
        "skill_lens/core/resolver.py",
        "skill_lens/core/diff.py",
        "skill_lens/core/snapshot.py",
        "tests/test_phase2_gate.py",
        "tests/test_snapshot_inputs.py",
        "tests/test_session_snapshot.py",
        "docs/validation/c5/run_campaign.py",
    ]
    file_hashes = {rel: hash_file(ROOT / rel) for rel in inspected_files if (ROOT / rel).is_file()}

    results_data: dict[str, Any] = {
        "scratch_directory": str(scratch),
        "evidence_directory": str(evidence_dir),
        "python_interpreter": PYTHON,
        "provenance_metadata": {
            "git_revision": git_rev,
            "plan_reference": "3665e7a38a9b7366c259da61c87f8b0cab656947",
            "inspected_file_hashes": file_hashes,
        },
        "collection_parity": {},
        "runner_self_test": [],
        "mutations": [],
        "summary": {},
    }

    try:
        # Run self-test first
        self_test_results = run_runner_self_test(scratch)
        results_data["runner_self_test"] = self_test_results
        print(f"Runner self-test passed: {len(self_test_results)} scenarios verified fail-closed.")

        if args.validate_runner:
            print("Validation mode completed successfully.")
            return

        parity = verify_collection_parity(scratch)
        results_data["collection_parity"] = parity
        print(f"Collection parity verified: {parity['collected_count']} items match exactly.")

        survivors: list[str] = []
        invalids: list[str] = []

        for mut in MUTATIONS:
            m_id = mut["id"]
            target_file = scratch / mut["file"]
            original_bytes = target_file.read_bytes()
            original_text = original_bytes.decode("utf-8")
            before_str = mut["before"]
            after_str = mut["after"]
            selector = mut["selector"]
            expected_substr = mut["expected_failure_substr"]

            assert original_text.count(before_str) == 1, (
                f"{m_id}: before_str occurs {original_text.count(before_str)} "
                f"times in {mut['file']}"
            )

            print(f"Running {m_id} ({mut['category']}): {mut['name']}...")

            # 1. Control Run (clean)
            c_log = evidence_dir / f"{m_id}-control.log"
            c_run_log = evidence_dir / f"{m_id}-control-run.jsonl"
            c_rc, c_out, c_entries = run_pytest(scratch, selector, c_log, c_run_log)
            c_eval = evaluate_control_run(c_rc, c_out, c_entries, selector, scratch)
            assert c_eval["status"] == "PASS", f"{m_id} control failed: {c_eval['reason']}\n{c_out}"
            expected_count = c_eval["count"]

            # 2. Mutant Run inside try/finally to guarantee immediate and byte-verified restoration
            m_eval: dict[str, Any] = {}
            m_rc = -1
            m_out = ""
            try:
                mutated_text = original_text.replace(before_str, after_str, 1)
                target_file.write_text(mutated_text, encoding="utf-8")

                m_log = evidence_dir / f"{m_id}-mutant.log"
                m_run_log = evidence_dir / f"{m_id}-mutant-run.jsonl"
                m_rc, m_out, m_entries = run_pytest(scratch, selector, m_log, m_run_log)
                m_eval = evaluate_mutant_run(
                    m_rc,
                    m_out,
                    m_entries,
                    expected_substr,
                    expected_count,
                    scratch,
                    expected_selector=selector,
                )
            finally:
                target_file.write_bytes(original_bytes)
                restored_bytes = target_file.read_bytes()
                assert restored_bytes == original_bytes, f"Failed to restore {target_file}"

            # 3. Restored Run
            r_log = evidence_dir / f"{m_id}-restored.log"
            r_run_log = evidence_dir / f"{m_id}-restored-run.jsonl"
            r_rc, r_out, r_entries = run_pytest(scratch, selector, r_log, r_run_log)
            r_eval = evaluate_control_run(
                r_rc,
                r_out,
                r_entries,
                selector,
                scratch,
                expected_count=expected_count,
            )
            assert r_eval["status"] == "PASS", (
                f"{m_id} restored run failed: {r_eval['reason']}\n{r_out}"
            )
            assert r_eval["count"] == expected_count, (
                f"{m_id} restored count mismatch: {r_eval['count']} != {expected_count}"
            )

            # Record outcome
            if m_eval["status"] == "KILLED":
                is_killed = True
            elif m_eval["status"] == "SURVIVOR":
                is_killed = False
                survivors.append(m_id)
            else:
                is_killed = False
                invalids.append(m_id)

            mut_record = {
                "id": m_id,
                "category": mut["category"],
                "name": mut["name"],
                "description": mut["description"],
                "file": mut["file"],
                "before": before_str,
                "after": after_str,
                "selector": selector,
                "control": {
                    "exit_code": c_rc,
                    "status": c_eval["status"],
                    "provenance": c_eval["provenance"],
                    "test_count": c_eval["count"],
                },
                "mutant": {
                    "exit_code": m_rc,
                    "status": m_eval["status"],
                    "verdict": m_eval.get("verdict"),
                    "killed": m_eval["killed"],
                    "expected_substr": expected_substr,
                    "found_expected_substr": m_eval.get("found_expected_substr", False),
                    "exc_type": m_eval.get("exc_type"),
                    "provenance": m_eval.get("provenance"),
                    "test_count": m_eval.get("test_count", 0),
                    "reason": m_eval.get("reason"),
                    "tail_output": m_out[-1000:],
                },
                "restored": {
                    "exit_code": r_rc,
                    "status": r_eval["status"],
                    "bytes_restored_verified": True,
                    "provenance": r_eval["provenance"],
                    "test_count": r_eval["count"],
                },
            }
            results_data["mutations"].append(mut_record)
            print(f"  -> Result: {m_eval['verdict']} (killed={is_killed})")

        overall_status = (
            "PASS"
            if (not survivors and not invalids and len(results_data["mutations"]) == len(MUTATIONS))
            else "FAIL"
        )

        results_data["summary"] = {
            "total_mutations": len(MUTATIONS),
            "killed_count": sum(1 for m in results_data["mutations"] if m["mutant"]["killed"]),
            "survivors": survivors,
            "invalids": invalids,
            "status": overall_status,
        }

        output_path = args.output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        results_json_str = json.dumps(results_data, indent=2)
        output_path.write_text(results_json_str, encoding="utf-8")
        print(f"Results written to: {output_path}")

        print(f"Summary: {results_data['summary']}")

        if survivors or invalids:
            print(f"ERROR: Campaign failed! Survivors: {survivors}, Invalids: {invalids}")
            sys.exit(1)
        else:
            print(
                "All mutations killed successfully with genuine behavioral failures "
                "and verified provenance."
            )

    finally:
        # Clean up disposable scratch copy
        shutil.rmtree(scratch, ignore_errors=True)
        print(f"Scratch copy {scratch} cleaned up.")


if __name__ == "__main__":
    main()
