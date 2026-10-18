"""Mutation proof tests for P01 request capture guards.

Proves test sensitivity by running UNCHANGED focused unit tests against mutated guards:
1. Baseline check: the targeted unchanged test passes on unmutated code.
2. Mutation application: deliberately break the security, privacy, correlation, or route guard.
3. Execution: run the EXACT UNCHANGED targeted test against the mutated code.
4. Proof of sensitivity: assert that the targeted test FAILS (raises AssertionError).
5. Restoration: revert mutation in finally block, ensuring clean environment.
6. Mutation results recorded with target, name, failing error, and zero survivors.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from typing import Any

# Ensure paths
HERMES_ROOT = Path("/Users/corvette/.hermes/hermes-agent")
if str(HERMES_ROOT) not in sys.path:
    sys.path.insert(0, str(HERMES_ROOT))

P01_DIR = Path(__file__).parent.resolve()
if str(P01_DIR) not in sys.path:
    sys.path.insert(0, str(P01_DIR))

import hermes_bootstrap  # noqa: F401, E402
import httpx  # noqa: E402
import observer  # noqa: E402
import test_capture_offline  # noqa: E402

MUTATION_RECORD: list[dict[str, Any]] = []


def _run_test_method(case_class: type[unittest.TestCase], method_name: str) -> None:
    """Instantiate and execute a single unchanged test method, running setUp and tearDown."""
    suite = unittest.TestSuite()
    suite.addTest(case_class(method_name))
    result = unittest.TestResult()
    suite.run(result)
    if result.errors:
        _, err_msg = result.errors[0]
        raise RuntimeError(f"Unexpected error in test {method_name}:\n{err_msg}")
    if result.failures:
        _, fail_msg = result.failures[0]
        # Extract first line of failure
        raise AssertionError(fail_msg.strip().splitlines()[-1])


class MutationTests(unittest.TestCase):
    """Prove that breaking each guard causes UNCHANGED focused assertions to FAIL."""

    def test_m1_break_correlation_guard_causes_normal_test_failure(self) -> None:
        """M1: Breaking correlation causes unchanged test_direct_request_correlation to fail."""
        target_method = "test_direct_request_correlation_and_actual_api_mode"

        # 1. Baseline: target test must PASS on clean code
        _run_test_method(test_capture_offline.TestObserverCapture, target_method)

        # 2. Mutate: break ContextVar correlation in RequestObserver.on_request
        orig_on_request = observer.RequestObserver.on_request

        def mutated_on_request(self_obs: observer.RequestObserver, request: httpx.Request) -> None:
            # Deliberately ignore ContextVar and emit uncorrelated request
            self_obs.sink.write_record(
                {
                    "event": "http_request",
                    "exchange_id": 999,
                    "session_id": None,
                    "api_request_id": None,
                    "api_mode": None,
                    "provider": None,
                    "model": None,
                    "base_url": None,
                    "reasoning_effort": None,
                    "method": request.method,
                    "url": str(request.url),
                    "route_approved": False,
                    "correlated": False,
                }
            )

        orig_on_response = observer.RequestObserver.on_response

        def mutated_on_response(
            self_obs: observer.RequestObserver, response: httpx.Response
        ) -> None:
            self_obs.sink.write_record(
                {
                    "event": "http_response",
                    "exchange_id": 999,
                    "session_id": None,
                    "api_request_id": None,
                    "api_mode": None,
                    "provider": None,
                    "model": None,
                    "base_url": None,
                    "reasoning_effort": None,
                    "method": "POST",
                    "url": str(response.url),
                    "status_code": response.status_code,
                    "route_approved": False,
                    "correlated": False,  # Broken correlation
                }
            )

        try:
            observer.RequestObserver.on_request = mutated_on_request
            observer.RequestObserver.on_response = mutated_on_response

            # 3. Running UNCHANGED target test against mutated guard MUST fail
            with self.assertRaises(AssertionError) as ctx:
                _run_test_method(test_capture_offline.TestObserverCapture, target_method)

            failing_err = str(ctx.exception)
            MUTATION_RECORD.append(
                {
                    "mutation_id": "M1",
                    "guard": "ContextVar request correlation",
                    "target_test": target_method,
                    "status": "KILLED",
                    "failing_assertion": failing_err,
                }
            )
        finally:
            # 4. Restore normal code
            observer.RequestObserver.on_request = orig_on_request
            observer.RequestObserver.on_response = orig_on_response

        # Re-verify baseline is restored
        _run_test_method(test_capture_offline.TestObserverCapture, target_method)

    def test_m2_break_privacy_guard_causes_normal_test_failure(self) -> None:
        """M2: Leaking Authorization header causes unchanged test_secrets_exclusion to fail."""
        target_method = "test_secrets_exclusion_from_all_observer_bytes"

        # 1. Baseline: target test must PASS on clean code
        _run_test_method(test_capture_offline.TestObserverCapture, target_method)

        # 2. Mutate: leak request headers into sink
        orig_write = observer.CaptureSink.write_record

        def mutated_write_record(
            self_sink: observer.CaptureSink, record: observer.Mapping[str, Any]
        ) -> None:
            # Mutate record by adding Authorization header if http_request
            mutated = dict(record)
            # Inject fake leaked header or grab from environment
            mutated["leaked_header"] = "SECRET_BEARER_AUTH_TOKEN_XYZZY"
            orig_write(self_sink, mutated)

        try:
            observer.CaptureSink.write_record = mutated_write_record

            # 3. Running UNCHANGED target test against mutated guard MUST fail
            with self.assertRaises(AssertionError) as ctx:
                _run_test_method(test_capture_offline.TestObserverCapture, target_method)

            failing_err = str(ctx.exception)
            MUTATION_RECORD.append(
                {
                    "mutation_id": "M2",
                    "guard": "Secrets exclusion from observer bytes",
                    "target_test": target_method,
                    "status": "KILLED",
                    "failing_assertion": failing_err,
                }
            )
        finally:
            # 4. Restore normal code
            observer.CaptureSink.write_record = orig_write

        # Re-verify baseline is restored
        _run_test_method(test_capture_offline.TestObserverCapture, target_method)

    def test_m3_break_route_guard_causes_normal_test_failure(self) -> None:
        """M3: Accepting unapproved URL causes unchanged test_unapproved_url_sanitized to fail."""
        target_method = "test_unapproved_url_sanitized_to_safe_marker"

        # 1. Baseline: target test must PASS on clean code
        _run_test_method(test_capture_offline.TestObserverCapture, target_method)

        # 2. Mutate: sanitize_url returns raw URL and True
        orig_sanitize = observer.sanitize_url

        def mutated_sanitize_url(raw_url: Any) -> tuple[str, bool]:
            return str(raw_url), True  # Broken guard: passes unapproved route as approved

        try:
            observer.sanitize_url = mutated_sanitize_url

            # 3. Running UNCHANGED target test against mutated guard MUST fail
            with self.assertRaises(AssertionError) as ctx:
                _run_test_method(test_capture_offline.TestObserverCapture, target_method)

            failing_err = str(ctx.exception)
            MUTATION_RECORD.append(
                {
                    "mutation_id": "M3",
                    "guard": "Loopback URL and route sanitization guard",
                    "target_test": target_method,
                    "status": "KILLED",
                    "failing_assertion": failing_err,
                }
            )
        finally:
            # 4. Restore normal code
            observer.sanitize_url = orig_sanitize

        # Re-verify baseline is restored
        _run_test_method(test_capture_offline.TestObserverCapture, target_method)

    def test_m4_break_sink_mode_guard_causes_normal_test_failure(self) -> None:
        """M4: Setting mode 0666 causes unchanged test_mode_0600_and_exclusive_creation to fail."""
        target_method = "test_mode_0600_and_exclusive_creation"

        # 1. Baseline: target test must PASS on clean code
        _run_test_method(test_capture_offline.TestSinkSecurityAndBounding, target_method)

        # 2. Mutate: chmod to 0666 instead of 0600 in CaptureSink.__init__
        orig_init = observer.CaptureSink.__init__

        def mutated_init(self_sink: observer.CaptureSink, *args: Any, **kwargs: Any) -> None:
            orig_init(self_sink, *args, **kwargs)
            os.chmod(str(self_sink.target_path), 0o666)  # Broken permissions

        try:
            observer.CaptureSink.__init__ = mutated_init

            # 3. Running UNCHANGED target test against mutated guard MUST fail
            with self.assertRaises(AssertionError) as ctx:
                _run_test_method(test_capture_offline.TestSinkSecurityAndBounding, target_method)

            failing_err = str(ctx.exception)
            MUTATION_RECORD.append(
                {
                    "mutation_id": "M4",
                    "guard": "Sink exclusive mode 0600 permissions",
                    "target_test": target_method,
                    "status": "KILLED",
                    "failing_assertion": failing_err,
                }
            )
        finally:
            # 4. Restore normal code
            observer.CaptureSink.__init__ = orig_init

        # Re-verify baseline is restored
        _run_test_method(test_capture_offline.TestSinkSecurityAndBounding, target_method)

    def test_m5_break_dynamic_api_mode_guard_causes_normal_test_failure(self) -> None:
        """M5: Hardcoding api_mode causes test_actual_mode_read_dynamically to fail."""
        target_method = "test_actual_mode_read_dynamically_not_assumed_constant"

        # 1. Baseline: target test must PASS on clean code
        _run_test_method(test_capture_offline.TestObserverCapture, target_method)

        # 2. Mutate: hardcode api_mode to codex_responses in extract_scalar_metadata
        orig_extract = observer.extract_scalar_metadata

        def mutated_extract(
            agent: Any, api_kwargs: Any, client: Any = None
        ) -> observer.RequestMetadata:
            meta = orig_extract(agent, api_kwargs, client=client)
            # Mutate to constant codex_responses, ignoring actual agent.api_mode
            return observer.RequestMetadata(
                session_id=meta.session_id,
                api_request_id=meta.api_request_id,
                provider=meta.provider,
                model=meta.model,
                api_mode="codex_responses",  # Broken: assumed constant
                base_url=meta.base_url,
                reasoning_effort=meta.reasoning_effort,
            )

        try:
            observer.extract_scalar_metadata = mutated_extract

            # 3. Running UNCHANGED target test against mutated guard MUST fail
            with self.assertRaises(AssertionError) as ctx:
                _run_test_method(test_capture_offline.TestObserverCapture, target_method)

            failing_err = str(ctx.exception)
            MUTATION_RECORD.append(
                {
                    "mutation_id": "M5",
                    "guard": "Dynamic agent.api_mode extraction (not assumed constant)",
                    "target_test": target_method,
                    "status": "KILLED",
                    "failing_assertion": failing_err,
                }
            )
        finally:
            # 4. Restore normal code
            observer.extract_scalar_metadata = orig_extract

        # Re-verify baseline is restored
        _run_test_method(test_capture_offline.TestObserverCapture, target_method)

    def test_z_all_mutations_killed_with_zero_survivors(self) -> None:
        """Ensure all 5 mutations were registered and killed with zero survivors."""
        killed_ids = {m["mutation_id"] for m in MUTATION_RECORD}
        expected_ids = {"M1", "M2", "M3", "M4", "M5"}
        self.assertEqual(killed_ids, expected_ids)
        for m in MUTATION_RECORD:
            self.assertEqual(m["status"], "KILLED")
            self.assertTrue(len(m["failing_assertion"]) > 0)


if __name__ == "__main__":
    unittest.main()
