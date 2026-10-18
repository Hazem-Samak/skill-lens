"""Focused test runner for P01 request capture offline verification.

Runs:
1. test_capture_offline.py (focused offline capture tests)
2. mutation_tests.py (guard sensitivity mutation tests)

Default output path is strictly external (/tmp/skill-lens-p01-capture-test-results.json)
to prevent mutating the git checkout.
Accepts an optional --output <path> argument or P01_TEST_RESULTS_PATH env var.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Any

# Ensure paths
HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

HERMES_ROOT = Path("/Users/corvette/.hermes/hermes-agent")
if str(HERMES_ROOT) not in sys.path:
    sys.path.insert(0, str(HERMES_ROOT))

# Ensure pycache and bytecode are strictly external
os.environ["PYTHONPYCACHEPREFIX"] = os.environ.get("PYTHONPYCACHEPREFIX", "/tmp/skill-lens-pycache")
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import hermes_bootstrap  # noqa: F401, E402
import mutation_tests  # noqa: E402
import test_capture_offline  # noqa: E402

DEFAULT_EXTERNAL_RESULTS_PATH = Path(
    "/private/tmp/skill-lens-p01-capture-20261018-qurnpsjs/test-results.json"
    if Path("/private/tmp/skill-lens-p01-capture-20261018-qurnpsjs").exists()
    else "/tmp/skill-lens-p01-capture-test-results.json"
)


def run_all_tests(output_path: Path | None = None) -> dict[str, Any]:
    """Run all focused unit and mutation tests and return summary dict."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Load suites
    capture_suite = loader.loadTestsFromModule(test_capture_offline)
    mutation_suite = loader.loadTestsFromModule(mutation_tests)
    suite.addTests(capture_suite)
    suite.addTests(mutation_suite)

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    duration = time.time() - start_time

    summary: dict[str, Any] = {
        "tests_run": result.testsRun,
        "errors": len(result.errors),
        "failures": len(result.failures),
        "skipped": len(result.skipped),
        "was_successful": result.wasSuccessful(),
        "duration_seconds": round(duration, 3),
        "capture_tests_count": capture_suite.countTestCases(),
        "mutation_tests_count": mutation_suite.countTestCases(),
        "mutation_records": list(mutation_tests.MUTATION_RECORD),
        "error_details": [
            {"test": str(t), "err": str(e).splitlines()[-1]} for t, e in result.errors
        ],
        "failure_details": [
            {"test": str(t), "fail": str(f).splitlines()[-1]} for t, f in result.failures
        ],
    }

    target_results_file = (
        output_path
        or Path(os.environ.get("P01_TEST_RESULTS_PATH", str(DEFAULT_EXTERNAL_RESULTS_PATH)))
    ).resolve()

    target_results_file.parent.mkdir(parents=True, exist_ok=True)
    target_results_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="P01 Capture Offline Test Runner")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Path for output JSON results. Defaults to external /tmp path.",
    )
    args = parser.parse_args()

    summary = run_all_tests(args.output)
    print("\n" + "=" * 60)
    print("P01 CAPTURE OFFLINE VERIFICATION SUMMARY")
    print(f"Total Tests Run: {summary['tests_run']}")
    print(f"  - Focused Capture Tests: {summary['capture_tests_count']}")
    print(f"  - Mutation Tests: {summary['mutation_tests_count']}")
    print(f"Failures: {summary['failures']}")
    print(f"Errors: {summary['errors']}")
    print(f"Duration: {summary['duration_seconds']}s")
    print(f"Status: {'PASSED' if summary['was_successful'] else 'FAILED'}")
    print("=" * 60)

    if not summary["was_successful"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
