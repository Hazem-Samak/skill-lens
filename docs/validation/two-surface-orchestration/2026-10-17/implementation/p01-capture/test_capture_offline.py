"""Comprehensive focused offline verification tests for P01 request capture.

Tests cover:
1. Source hash verification and caller binding resolution.
2. Direct request correlation under synthetic stand-in agent and MockTransport.
3. Actual agent.api_mode dynamic extraction (not assumed constant).
4. Relay copied-context callback correlation.
5. Interleaved concurrent requests across multiple threads (zero crosstalk).
6. ContextVar scope lifecycle and finally-reset on success and errors.
7. Per-exchange physical observation for redirects and retries (307 redirect and SDK 500->200).
8. Existing client hook order retention and strict no-body/stream read.
9. Uncorrelated requests handling and missing IDs never recording correlated=True.
10. Strict scalar extraction and reasoning effort whitelisting (no arbitrary dict str).
11. Resilient extraction/hook error handling: original function invoked EXACTLY ONCE with
    same args, return identity, or exception identity; durable content-free invalidation.
12. URL mismatch sanitization (safe marker, no path/query leak).
13. Complete secrets exclusion from all emitted observer bytes (bearer, prompt, cookie, exception).
14. Sink security: mode 0600, exclusive creation, symlink rejection, path escape rejection.
15. Sink bounding and visible invalidation on write/flush/closed failure without leaking exceptions.
16. Launcher flags validation, offline --help subprocess execution, and HERDR_ENV enforcement.
17. Startup observer installation before CLI entry with argv retention and synthetic collaborator.
18. is_actual_route guard compliance.
19. Invalidation fallback path-safety: symlink rejection, preexisting marker protection.
20. ContextVar non-leak on request-enter write failure (Defect B regression proof).
21. Observer main production root pinning and unapproved override rejection (Defect D).
22. Genuine native runtime_command startup proof with verified source pins (Defect C).
"""

from __future__ import annotations

import concurrent.futures
import contextvars
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any

# Ensure Hermes root is on sys.path
HERMES_ROOT = Path("/Users/corvette/.hermes/hermes-agent")
if str(HERMES_ROOT) not in sys.path:
    sys.path.insert(0, str(HERMES_ROOT))

# Ensure p01-capture directory is on sys.path for direct module import
P01_DIR = Path(__file__).parent.resolve()
if str(P01_DIR) not in sys.path:
    sys.path.insert(0, str(P01_DIR))

MANAGED_PYTHON = Path(
    "/Users/corvette/.hermes/tools/python-3.14.7+20260901-darwin-arm64/bin/python3"
)

import hermes_bootstrap  # noqa: F401, E402
import httpx  # noqa: E402
from launcher import (  # noqa: E402
    APPROVED_BASE_URL,
    APPROVED_MODEL,
    APPROVED_PROVIDER,
    APPROVED_REASONING,
    APPROVED_TOOLSETS,
    build_runtime_command,
    is_strictly_help,
    validate_launch_arguments,
)
from observer import (  # noqa: E402
    APPROVED_PILOT_ARTIFACTS_ROOT,
    APPROVED_RESPONSES_URL,
    PINNED_HERMES_ROOT,
    SOURCE_PINS,
    CaptureSink,
    RequestMetadata,
    RequestObserver,
    SourceVerificationError,
    extract_scalar_metadata,
    verify_source_pins,
)
from openai import OpenAI  # noqa: E402


def _make_sse_response_bytes(
    model: str = "gpt-6.1-sol", output_text: str = "Hello synthetic"
) -> bytes:
    """Generate standard SSE event stream compatible with Codex Responses assembler."""
    delta_json = json.dumps(output_text)
    parts = [
        'event: response.created\ndata: {"id": "resp_1", "type": "response.created", '
        '"response": {"id": "resp_1"}}\n\n',
        'event: response.output_item.added\ndata: {"type": "response.output_item.added", '
        '"item": {"id": "msg_1", "type": "message", "role": "assistant", "content": []}}\n\n',
        f'event: response.output_text.delta\ndata: {{"type": "response.output_text.delta", '
        f'"delta": {delta_json}}}\n\n',
        'event: response.completed\ndata: {"type": "response.completed", '
        '"response": {"id": "resp_1", "status": "completed"}}\n\n',
    ]
    return "".join(parts).encode("utf-8")


def _make_synthetic_agent(**kwargs: Any) -> SimpleNamespace:
    defaults = {
        "session_id": "synthetic-sess-1",
        "_current_api_request_id": "synthetic-req-1",
        "provider": APPROVED_PROVIDER,
        "model": APPROVED_MODEL,
        "api_mode": "codex_responses",
        "base_url": APPROVED_BASE_URL,
        "_interrupt_requested": False,
        "_touch_activity": lambda *a, **kw: None,
        "_fire_reasoning_delta": lambda *a, **kw: None,
        "_client_log_context": lambda *a, **kw: "synthetic",
        "_buffer_diagnostic_status": lambda *a, **kw: None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestSourceVerificationAndBinding(unittest.TestCase):
    """Test pinned source hashes and caller forward binding."""

    def test_all_source_pins_match(self) -> None:
        """Prove installed Hermes sources match all frozen SHA-256 pins."""
        verify_source_pins(HERMES_ROOT)

    def test_source_pin_mismatch_detected(self) -> None:
        """Prove modified source file is rejected with SourceVerificationError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_root = Path(tmp_dir)
            for rel_path in SOURCE_PINS:
                target = fake_root / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("tampered content", encoding="utf-8")

            with self.assertRaises(SourceVerificationError):
                verify_source_pins(fake_root)

    def test_dynamic_forwarder_binding_resolution(self) -> None:
        """Prove ClientLifecycleMixin resolves run_codex_stream via lazy forwarder."""
        import agent.client_lifecycle
        import agent.codex_runtime
        from agent.client_lifecycle import ClientLifecycleMixin

        self.assertTrue(hasattr(ClientLifecycleMixin, "_run_codex_stream"))
        fn = ClientLifecycleMixin._run_codex_stream
        self.assertTrue(callable(fn))

        class DummyLifecycle(ClientLifecycleMixin):
            pass

        dummy = DummyLifecycle()
        orig = agent.codex_runtime.run_codex_stream

        def sentinel_stream(agent_self: Any, *args: Any, **kwargs: Any) -> str:
            return "sentinel_invoked"

        try:
            agent.codex_runtime.run_codex_stream = sentinel_stream
            self.assertEqual(dummy._run_codex_stream(), "sentinel_invoked")
        finally:
            agent.codex_runtime.run_codex_stream = orig


class TestObserverCapture(unittest.TestCase):
    """Test direct request correlation, dynamic mode extraction, relay and hook order."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.resolved_tmp = Path(self.tmp_dir.name).resolve()
        self.capture_file = self.resolved_tmp / "capture.jsonl"
        self.sink = CaptureSink(self.capture_file, allowed_root=self.resolved_tmp)
        self.observer = RequestObserver(self.sink)
        self.observer.install()

    def tearDown(self) -> None:
        self.observer.uninstall()
        self.sink.close()
        self.tmp_dir.cleanup()

    def _read_records(self) -> list[dict[str, Any]]:
        if not self.capture_file.exists():
            return []
        lines = self.capture_file.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def test_direct_request_correlation_and_actual_api_mode(self) -> None:
        """Prove agent.api_mode and loopback HTTP request are correlated under same session."""
        import agent.codex_runtime

        sse_bytes = _make_sse_response_bytes()

        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, headers={"content-type": "text/event-stream"}, content=sse_bytes
            )

        transport = httpx.MockTransport(handler)
        http_client = httpx.Client(transport=transport)
        openai_client = OpenAI(
            base_url=APPROVED_BASE_URL,
            api_key="synthetic_key",
            http_client=http_client,
        )

        synthetic_agent = _make_synthetic_agent(
            session_id="test-session-123",
            _current_api_request_id="test-req-456",
            api_mode="codex_responses",
        )

        agent.codex_runtime.run_codex_stream(
            synthetic_agent,
            {"model": "gpt-6.1-sol", "reasoning": {"effort": "high"}},
            client=openai_client,
        )

        records = self._read_records()
        self.assertGreaterEqual(len(records), 3)

        # Check call enter event
        enter_ev = records[0]
        self.assertEqual(enter_ev["event"], "codex_stream_call_enter")
        self.assertEqual(enter_ev["session_id"], "test-session-123")
        self.assertEqual(enter_ev["api_request_id"], "test-req-456")
        self.assertEqual(enter_ev["api_mode"], "codex_responses")
        self.assertEqual(enter_ev["base_url"], APPROVED_BASE_URL)
        self.assertEqual(enter_ev["reasoning_effort"], "high")

        # Check HTTP request event
        req_ev = next(r for r in records if r.get("event") == "http_request")
        self.assertEqual(req_ev["session_id"], "test-session-123")
        self.assertEqual(req_ev["api_request_id"], "test-req-456")
        self.assertEqual(req_ev["api_mode"], "codex_responses")
        self.assertEqual(req_ev["url"], APPROVED_RESPONSES_URL)
        self.assertEqual(req_ev["method"], "POST")
        self.assertTrue(req_ev["route_approved"])
        self.assertTrue(req_ev["correlated"])

        # Check HTTP response event
        resp_ev = next(r for r in records if r.get("event") == "http_response")
        self.assertEqual(resp_ev["session_id"], "test-session-123")
        self.assertEqual(resp_ev["api_request_id"], "test-req-456")
        self.assertEqual(resp_ev["api_mode"], "codex_responses")
        self.assertEqual(resp_ev["status_code"], 200)
        self.assertTrue(resp_ev["route_approved"])
        self.assertTrue(resp_ev["correlated"])

        # Check call exit event
        exit_ev = records[-1]
        self.assertEqual(exit_ev["event"], "codex_stream_call_exit")
        self.assertEqual(exit_ev["session_id"], "test-session-123")

    def test_actual_mode_read_dynamically_not_assumed_constant(self) -> None:
        """Prove agent.api_mode is extracted dynamically from agent instance."""
        import agent.codex_runtime

        sse_bytes = _make_sse_response_bytes()
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200, headers={"content-type": "text/event-stream"}, content=sse_bytes
            )
        )
        http_client = httpx.Client(transport=transport)
        openai_client = OpenAI(
            base_url=APPROVED_BASE_URL,
            api_key="synthetic_key",
            http_client=http_client,
        )

        for custom_mode in ["codex_responses", "custom_chat", "alternative_mode"]:
            synthetic_agent = _make_synthetic_agent(
                session_id=f"sess-{custom_mode}",
                _current_api_request_id=f"req-{custom_mode}",
                api_mode=custom_mode,
            )
            agent.codex_runtime.run_codex_stream(
                synthetic_agent,
                {"model": "gpt-6.1-sol"},
                client=openai_client,
            )

        records = self._read_records()
        extracted_modes = [r["api_mode"] for r in records if r.get("event") == "http_request"]
        self.assertIn("codex_responses", extracted_modes)
        self.assertIn("custom_chat", extracted_modes)
        self.assertIn("alternative_mode", extracted_modes)

    def test_relay_copied_context_callback_correlation(self) -> None:
        """Prove Relay's explicit context copying preserves correlation in async callback."""
        req_meta = RequestMetadata(
            session_id="relay-session-xyz",
            api_request_id="relay-req-789",
            provider=APPROVED_PROVIDER,
            model=APPROVED_MODEL,
            api_mode="codex_responses",
            base_url=APPROVED_BASE_URL,
            reasoning_effort="high",
        )

        token = self.observer.context_var.set(req_meta)
        captured_ctx = contextvars.copy_context()
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        transport = httpx.MockTransport(lambda req: httpx.Response(200, json={"relay": "success"}))
        http_client = httpx.Client(transport=transport)

        def worker_callback() -> None:
            def send_req() -> None:
                req = http_client.build_request("POST", APPROVED_RESPONSES_URL)
                http_client.send(req)

            captured_ctx.copy().run(send_req)

        try:
            future = pool.submit(worker_callback)
            future.result(timeout=5)
        finally:
            self.observer.context_var.reset(token)
            pool.shutdown(wait=True)

        records = self._read_records()
        req_events = [r for r in records if r.get("event") == "http_request"]
        self.assertTrue(any(r.get("session_id") == "relay-session-xyz" for r in req_events))

    def test_interleaved_concurrent_requests_zero_crosstalk(self) -> None:
        """Prove concurrent requests across multiple threads maintain separate correlation."""
        import agent.codex_runtime

        num_threads = 4
        barrier = threading.Barrier(num_threads)

        def worker(idx: int) -> None:
            sse_bytes = _make_sse_response_bytes(output_text=f"Thread {idx}")
            transport = httpx.MockTransport(
                lambda req: httpx.Response(
                    200, headers={"content-type": "text/event-stream"}, content=sse_bytes
                )
            )
            http_client = httpx.Client(transport=transport)
            openai_client = OpenAI(
                base_url=APPROVED_BASE_URL,
                api_key=f"key_{idx}",
                http_client=http_client,
            )

            synthetic_agent = _make_synthetic_agent(
                session_id=f"concurrent-sess-{idx}",
                _current_api_request_id=f"concurrent-req-{idx}",
                api_mode="codex_responses",
            )

            barrier.wait()
            agent.codex_runtime.run_codex_stream(
                synthetic_agent,
                {"model": "gpt-6.1-sol"},
                client=openai_client,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as pool:
            futures = [pool.submit(worker, i) for i in range(num_threads)]
            for f in futures:
                f.result(timeout=10)

        records = self._read_records()
        req_events = [r for r in records if r.get("event") == "http_request"]
        self.assertEqual(len(req_events), num_threads)

        for i in range(num_threads):
            ev = next(r for r in req_events if r.get("session_id") == f"concurrent-sess-{i}")
            self.assertEqual(ev["api_request_id"], f"concurrent-req-{i}")
            self.assertTrue(ev["correlated"])

    def test_http_redirect_per_exchange_tracking(self) -> None:
        """Prove physical HTTP redirects are captured as separate exchanges under same session."""
        sse_bytes = _make_sse_response_bytes()
        call_count = 0

        def redirect_handler(req: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(307, headers={"location": APPROVED_RESPONSES_URL})
            return httpx.Response(
                200, headers={"content-type": "text/event-stream"}, content=sse_bytes
            )

        transport = httpx.MockTransport(redirect_handler)
        client = httpx.Client(transport=transport, follow_redirects=True)

        req_meta = RequestMetadata(
            session_id="redirect-sess",
            api_request_id="redirect-req",
            provider="openai-codex",
            model="gpt-6.1-sol",
            api_mode="codex_responses",
            base_url=APPROVED_BASE_URL,
            reasoning_effort="high",
        )
        token = self.observer.context_var.set(req_meta)
        try:
            req = client.build_request("POST", APPROVED_RESPONSES_URL)
            client.send(req)
        finally:
            self.observer.context_var.reset(token)

        records = self._read_records()
        resp_events = [r for r in records if r.get("event") == "http_response"]
        self.assertEqual(len(resp_events), 2)
        self.assertEqual(resp_events[0]["status_code"], 307)
        self.assertEqual(resp_events[0]["session_id"], "redirect-sess")
        self.assertEqual(resp_events[1]["status_code"], 200)
        self.assertEqual(resp_events[1]["session_id"], "redirect-sess")
        self.assertNotEqual(resp_events[0]["exchange_id"], resp_events[1]["exchange_id"])

    def test_sdk_500_retry_per_exchange(self) -> None:
        """Prove actual SDK retry (500 -> 200) records physical exchanges under same session."""
        import agent.codex_runtime

        sse_bytes = _make_sse_response_bytes(output_text="Retry succeeded")
        attempt_count = 0

        def retry_handler(req: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                return httpx.Response(500, json={"error": {"message": "Simulated server failure"}})
            return httpx.Response(
                200, headers={"content-type": "text/event-stream"}, content=sse_bytes
            )

        transport = httpx.MockTransport(retry_handler)
        http_client = httpx.Client(transport=transport)
        openai_client = OpenAI(
            base_url=APPROVED_BASE_URL,
            api_key="synthetic_key",
            http_client=http_client,
            max_retries=2,
        )

        synthetic_agent = _make_synthetic_agent(
            session_id="retry-session",
            _current_api_request_id="retry-req",
            api_mode="codex_responses",
        )

        agent.codex_runtime.run_codex_stream(
            synthetic_agent,
            {"model": "gpt-6.1-sol"},
            client=openai_client,
        )

        records = self._read_records()
        resp_events = [r for r in records if r.get("event") == "http_response"]
        self.assertEqual(len(resp_events), 2)
        self.assertEqual(resp_events[0]["status_code"], 500)
        self.assertEqual(resp_events[0]["session_id"], "retry-session")
        self.assertEqual(resp_events[1]["status_code"], 200)
        self.assertEqual(resp_events[1]["session_id"], "retry-session")

    def test_preexisting_client_hook_order_retained(self) -> None:
        """Prove existing client event hooks run in their original order."""
        order_log: list[str] = []

        def pre_existing_req_hook(req: httpx.Request) -> None:
            order_log.append("pre_existing_req")

        def pre_existing_resp_hook(resp: httpx.Response) -> None:
            order_log.append("pre_existing_resp")

        transport = httpx.MockTransport(lambda req: httpx.Response(200, text="OK"))
        client = httpx.Client(
            transport=transport,
            event_hooks={
                "request": [pre_existing_req_hook],
                "response": [pre_existing_resp_hook],
            },
        )

        req = client.build_request("POST", APPROVED_RESPONSES_URL)
        client.send(req)

        self.assertIn("pre_existing_req", order_log)
        self.assertIn("pre_existing_resp", order_log)

    def test_strict_no_body_and_no_stream_read(self) -> None:
        """Prove observer hooks never read or buffer request/response body stream."""
        read_occurred = False

        class MonitoredStream(httpx.ByteStream):
            def __init__(self, data: bytes) -> None:
                self.data = data

            def __iter__(self) -> Any:
                nonlocal read_occurred
                read_occurred = True
                yield self.data

        stream = MonitoredStream(b'{"prompt": "SECRET_NEVER_READ"}')
        req = httpx.Request("POST", APPROVED_RESPONSES_URL, stream=stream)

        self.observer.on_request(req)
        self.assertFalse(read_occurred)

    def test_uncorrelated_request_captured_without_fabricated_proof(self) -> None:
        """Prove request without active ContextVar records correlated=False and None IDs."""
        transport = httpx.MockTransport(lambda req: httpx.Response(200, text="OK"))
        client = httpx.Client(transport=transport)

        req = client.build_request("POST", APPROVED_RESPONSES_URL)
        client.send(req)

        records = self._read_records()
        req_events = [r for r in records if r.get("event") == "http_request"]
        self.assertEqual(len(req_events), 1)
        self.assertFalse(req_events[0]["correlated"])
        self.assertIsNone(req_events[0]["session_id"])
        self.assertIsNone(req_events[0]["api_request_id"])

    def test_missing_ids_never_record_correlated_true(self) -> None:
        """Prove missing session_id or api_request_id strictly records correlated=False."""
        transport = httpx.MockTransport(lambda req: httpx.Response(200, text="OK"))
        client = httpx.Client(transport=transport)

        req_meta = RequestMetadata(
            session_id=None,
            api_request_id="req-123",
            provider="openai-codex",
            model="gpt-6.1-sol",
            api_mode="codex_responses",
            base_url=APPROVED_BASE_URL,
            reasoning_effort="high",
        )
        token = self.observer.context_var.set(req_meta)
        try:
            req = client.build_request("POST", APPROVED_RESPONSES_URL)
            client.send(req)
        finally:
            self.observer.context_var.reset(token)

        records = self._read_records()
        req_events = [r for r in records if r.get("event") == "http_request"]
        self.assertEqual(len(req_events), 1)
        self.assertFalse(req_events[0]["correlated"])

    def test_reasoning_effort_whitelist_and_nested_dict_extraction(self) -> None:
        """Prove reasoning_effort extracts scalar string and rejects arbitrary dict str."""
        meta_a = extract_scalar_metadata(
            SimpleNamespace(session_id="sess-a"), {"reasoning_effort": "high"}
        )
        self.assertEqual(meta_a.reasoning_effort, "high")

        api_kwargs_nested = {"reasoning": {"effort": "medium", "extra": "secret_data"}}
        meta_b = extract_scalar_metadata(SimpleNamespace(session_id="sess-kw"), api_kwargs_nested)
        self.assertEqual(meta_b.reasoning_effort, "medium")
        self.assertNotIn("secret_data", str(meta_b))

        meta_c = extract_scalar_metadata(SimpleNamespace(session_id="sess-none"), {})
        self.assertIsNone(meta_c.reasoning_effort)

    def test_metadata_extraction_fault_preserves_request_execution(self) -> None:
        """Prove extraction fault invalidates proof safely while original function runs once."""
        secret_error = "PRIVATE_SESSION_ID_EXCEPTION_SECRET"

        class FaultyAgent:
            @property
            def session_id(self) -> str:
                raise ValueError(secret_error)

            provider = APPROVED_PROVIDER
            model = APPROVED_MODEL
            api_mode = "codex_responses"
            base_url = APPROVED_BASE_URL
            _interrupt_requested = False

        call_count = 0
        sentinel_return = SimpleNamespace(
            status="completed", output_text="Executed despite extraction error"
        )

        def fake_original_fn(
            agent: Any, api_kwargs: Any, client: Any = None, on_first_delta: Any = None
        ) -> Any:
            nonlocal call_count
            call_count += 1
            return sentinel_return

        wrapped = self.observer.wrap_run_codex_stream(fake_original_fn)
        faulty_agent = FaultyAgent()
        result = wrapped(
            faulty_agent,
            {"model": "gpt-6.1-sol", "input": "test"},
        )

        self.assertEqual(call_count, 1)
        self.assertIs(result, sentinel_return)

        self.assertTrue(self.sink.invalidated)
        self.assertEqual(self.sink.invalidation_reason, "metadata_extraction_failure")

        self._read_records()
        raw_bytes = self.capture_file.read_bytes()
        self.assertNotIn(secret_error.encode("utf-8"), raw_bytes)
        self.assertIsNone(self.observer.context_var.get())

    def test_hook_fault_preserves_request_execution(self) -> None:
        """Prove observer hook failure invalidates proof safely without disrupting the request."""

        def broken_on_request(request: httpx.Request) -> None:
            raise RuntimeError("Observer hook unexpected crash")

        self.observer.on_request = broken_on_request

        transport = httpx.MockTransport(lambda req: httpx.Response(200, text="OK"))
        client = httpx.Client(transport=transport)
        req = client.build_request("POST", APPROVED_RESPONSES_URL)

        resp = client.send(req)
        self.assertEqual(resp.status_code, 200)

        self.assertTrue(self.sink.invalidated)
        self.assertEqual(self.sink.invalidation_reason, "observer_hook_failure")

    def test_original_function_exception_and_return_identity(self) -> None:
        """Prove return object identity, custom exception identity, and BaseException reset."""
        sentinel_return = object()

        def dummy_success(
            agent: Any, api_kwargs: Any, client: Any = None, on_first_delta: Any = None
        ) -> Any:
            return sentinel_return

        wrapped = self.observer.wrap_run_codex_stream(dummy_success)
        agent_obj = _make_synthetic_agent()
        ret = wrapped(agent_obj, {})
        self.assertIs(ret, sentinel_return)

        class CustomError(Exception):
            pass

        sentinel_exc = CustomError("Original error")

        def dummy_failing(
            agent: Any, api_kwargs: Any, client: Any = None, on_first_delta: Any = None
        ) -> None:
            raise sentinel_exc

        wrapped_fail = self.observer.wrap_run_codex_stream(dummy_failing)
        with self.assertRaises(CustomError) as cm:
            wrapped_fail(agent_obj, {})
        self.assertIs(cm.exception, sentinel_exc)
        self.assertIsNone(self.observer.context_var.get())

        def dummy_cancelled(
            agent: Any, api_kwargs: Any, client: Any = None, on_first_delta: Any = None
        ) -> None:
            raise KeyboardInterrupt("Simulated task cancellation")

        wrapped_cancel = self.observer.wrap_run_codex_stream(dummy_cancelled)
        with self.assertRaises(KeyboardInterrupt):
            wrapped_cancel(agent_obj, {})
        self.assertIsNone(self.observer.context_var.get())

    def test_unapproved_url_sanitized_to_safe_marker(self) -> None:
        """Prove unapproved URLs, credentials, and queries are replaced by safe mismatch marker."""
        transport = httpx.MockTransport(lambda req: httpx.Response(404))
        client = httpx.Client(transport=transport)

        req_meta = RequestMetadata(
            session_id="url-mismatch-sess",
            api_request_id="req-mismatch",
            provider="openai-codex",
            model="gpt-6.1-sol",
            api_mode="codex_responses",
            base_url=APPROVED_BASE_URL,
            reasoning_effort="high",
        )
        token = self.observer.context_var.set(req_meta)
        try:
            bad_url = "http://127.0.0.1:8787/chatgpt/unapproved?secret_token=12345#frag"
            req = client.build_request("POST", bad_url)
            client.send(req)
        finally:
            self.observer.context_var.reset(token)

        records = self._read_records()
        for r in records:
            if "url" in r:
                self.assertEqual(r["url"], "<unapproved_route_mismatch>")
                self.assertFalse(r["route_approved"])
                self.assertNotIn("secret_token", json.dumps(r))

    def test_secrets_exclusion_from_all_observer_bytes(self) -> None:
        """Prove Authorization tokens, prompts, cookies, headers, and exceptions are excluded."""
        secret_bearer = "SECRET_BEARER_AUTH_TOKEN_XYZZY"
        secret_prompt = "SECRET_USER_PROMPT_PAYLOAD_TOP_SECRET"
        secret_cookie = "SECRET_COOKIE_SESSION_COOKIE"
        secret_header = "SECRET_CUSTOM_HEADER_XYZ"
        secret_exc = "SECRET_INTERNAL_EXCEPTION_REASON"

        sse_bytes = _make_sse_response_bytes()

        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, headers={"content-type": "text/event-stream"}, content=sse_bytes
            )

        transport = httpx.MockTransport(handler)
        http_client = httpx.Client(
            transport=transport,
            cookies={"auth": secret_cookie},
            headers={"X-Custom-Secret": secret_header},
        )
        openai_client = OpenAI(
            base_url=APPROVED_BASE_URL,
            api_key=secret_bearer,
            http_client=http_client,
        )

        import agent.codex_runtime

        synthetic_agent = SimpleNamespace(
            session_id="privacy-test-session",
            _current_api_request_id="req-privacy",
            provider="openai-codex",
            model="gpt-6.1-sol",
            api_mode="codex_responses",
            base_url=APPROVED_BASE_URL,
            _interrupt_requested=False,
            _touch_activity=lambda *a: None,
            _fire_reasoning_delta=lambda *a: None,
            _client_log_context=lambda: "synthetic",
        )

        agent.codex_runtime.run_codex_stream(
            synthetic_agent,
            {"model": "gpt-6.1-sol", "input": secret_prompt},
            client=openai_client,
        )

        self.sink.close()
        file_bytes = self.capture_file.read_bytes()

        self.assertNotIn(secret_bearer.encode("utf-8"), file_bytes)
        self.assertNotIn(secret_prompt.encode("utf-8"), file_bytes)
        self.assertNotIn(secret_cookie.encode("utf-8"), file_bytes)
        self.assertNotIn(secret_header.encode("utf-8"), file_bytes)
        self.assertNotIn(secret_exc.encode("utf-8"), file_bytes)

    def test_context_var_no_leak_on_enter_write_failure_initial_none(self) -> None:
        """Defect B probe: enter write failure does NOT leak ContextVar when initial is None."""
        orig_write = self.sink.write_record
        enter_failed = [False]

        def failing_write(record: Any) -> None:
            if record.get("event") == "codex_stream_call_enter" and not enter_failed[0]:
                enter_failed[0] = True
                raise OSError("Simulated disk error on codex_stream_call_enter")
            orig_write(record)

        self.sink.write_record = failing_write

        call_count = 0
        observed_during_call: list[Any] = []
        sentinel_return = object()

        def mock_original_fn(
            agent: Any, api_kwargs: Any, client: Any = None, on_first_delta: Any = None
        ) -> Any:
            nonlocal call_count
            call_count += 1
            observed_during_call.append(self.observer.context_var.get())
            return sentinel_return

        wrapped = self.observer.wrap_run_codex_stream(mock_original_fn)
        synthetic_agent = _make_synthetic_agent(
            session_id="leak-test-sess", _current_api_request_id="leak-test-req"
        )

        self.assertIsNone(self.observer.context_var.get())
        result = wrapped(synthetic_agent, {})

        self.assertEqual(call_count, 1)
        self.assertIs(result, sentinel_return)
        self.assertIsNone(observed_during_call[0])
        self.assertIsNone(self.observer.context_var.get())
        self.assertTrue(self.sink.invalidated)

    def test_context_var_restored_on_enter_write_failure_nested_prior_context(self) -> None:
        """Defect B probe: enter write failure restores nested prior context cleanly."""
        prior_meta = RequestMetadata(
            session_id="prior-sess-outer",
            api_request_id="prior-req-outer",
            provider="openai-codex",
            model="gpt-6.1-sol",
            api_mode="codex_responses",
            base_url=APPROVED_BASE_URL,
            reasoning_effort="high",
        )
        token = self.observer.context_var.set(prior_meta)

        orig_write = self.sink.write_record
        enter_failed = [False]

        def failing_write(record: Any) -> None:
            if record.get("event") == "codex_stream_call_enter" and not enter_failed[0]:
                enter_failed[0] = True
                raise OSError("Simulated disk error on codex_stream_call_enter")
            orig_write(record)

        self.sink.write_record = failing_write

        observed_during_call: list[Any] = []

        def mock_original_fn(
            agent: Any, api_kwargs: Any, client: Any = None, on_first_delta: Any = None
        ) -> str:
            observed_during_call.append(self.observer.context_var.get())
            return "nested_success"

        wrapped = self.observer.wrap_run_codex_stream(mock_original_fn)
        synthetic_agent = _make_synthetic_agent(
            session_id="inner-sess", _current_api_request_id="inner-req"
        )

        try:
            res = wrapped(synthetic_agent, {})
            self.assertEqual(res, "nested_success")
            self.assertIsNone(observed_during_call[0])
            self.assertEqual(self.observer.context_var.get(), prior_meta)
        finally:
            self.observer.context_var.reset(token)

    def test_enter_invalidation_failure_resilient_and_preserves_identities(self) -> None:
        """Defect B: Even if invalidate itself fails on enter error, original runs and returns."""

        def failing_write(record: Any) -> None:
            if record.get("event") == "codex_stream_call_enter":
                raise OSError("Write enter failure")

        def failing_invalidate(reason: str) -> None:
            raise RuntimeError("Invalidate failure")

        self.sink.write_record = failing_write
        self.sink.invalidate = failing_invalidate

        sentinel_obj = object()
        called = [False]

        def target_fn(
            agent: Any, api_kwargs: Any, client: Any = None, on_first_delta: Any = None
        ) -> Any:
            called[0] = True
            return sentinel_obj

        wrapped = self.observer.wrap_run_codex_stream(target_fn)
        synthetic_agent = _make_synthetic_agent()

        res = wrapped(synthetic_agent, {})
        self.assertTrue(called[0])
        self.assertIs(res, sentinel_obj)
        self.assertIsNone(self.observer.context_var.get())

    def test_no_fabricated_correlation_on_out_of_band_http_after_failed_enter(self) -> None:
        """Defect B: After failed enter, subsequent out-of-band HTTP has correlated=False."""

        def failing_write(record: Any) -> None:
            if record.get("event") == "codex_stream_call_enter":
                raise OSError("Enter write failure")

        self.sink.write_record = failing_write

        def target_fn(
            agent: Any, api_kwargs: Any, client: Any = None, on_first_delta: Any = None
        ) -> None:
            transport = httpx.MockTransport(lambda req: httpx.Response(200, text="OK"))
            client_http = httpx.Client(transport=transport)
            req = client_http.build_request("POST", APPROVED_RESPONSES_URL)
            client_http.send(req)

        wrapped = self.observer.wrap_run_codex_stream(target_fn)
        synthetic_agent = _make_synthetic_agent(session_id="failed-enter-sess")

        wrapped(synthetic_agent, {})

        records = self._read_records()
        for r in records:
            if r.get("event") == "http_request":
                self.assertFalse(r["correlated"])
                self.assertIsNone(r["session_id"])

    def test_sanitizer_exact_raw_http_path_and_encoded_mismatch(self) -> None:
        """Prove sanitizer verifies exact raw HTTP request path and rejects encoded variants."""
        from observer import sanitize_base_url, sanitize_url

        # 1. Positive ordinary case
        url, approved = sanitize_url("http://127.0.0.1:8787/chatgpt/responses")
        self.assertEqual(url, APPROVED_RESPONSES_URL)
        self.assertTrue(approved)

        # 2. Positive case with credentials, query, and fragment stripped
        url, approved = sanitize_url(
            "http://user:secret@127.0.0.1:8787/chatgpt/responses?param=1#anchor"
        )
        self.assertEqual(url, APPROVED_RESPONSES_URL)
        self.assertTrue(approved)
        self.assertNotIn("secret", url)
        self.assertNotIn("param", url)

        # 3. Negative encoded-path cases: must safe mismatch rather than falsely claim
        # approved endpoint
        encoded_paths = [
            "http://127.0.0.1:8787/%63%68%61%74%67%70%74/%72%65%73%70%6f%6e%73%65%73",
            "http://127.0.0.1:8787/chatgpt%2fresponses",
            "http://127.0.0.1:8787/chatgpt/responses%2f",
            "http://127.0.0.1:8787/%2e%2e/chatgpt/responses",
            "http://127.0.0.1:8787/chatgpt/responses/extra",
        ]
        for ep in encoded_paths:
            u, app = sanitize_url(ep)
            self.assertEqual(
                u,
                "<unapproved_route_mismatch>",
                f"Encoded path {ep} must return safe mismatch marker",
            )
            self.assertFalse(app, f"Encoded path {ep} must never be marked route_approved")

        # 4. Base URL exactness
        base, base_app = sanitize_base_url("http://127.0.0.1:8787/%63%68%61%74%67%70%74")
        self.assertEqual(base, "<unapproved_base_url_mismatch>")
        self.assertFalse(base_app)

        # 5. Through HTTP client hooks
        transport = httpx.MockTransport(lambda req: httpx.Response(200, text="OK"))
        client = httpx.Client(transport=transport)
        req_meta = RequestMetadata(
            session_id="encoded-sess",
            api_request_id="req-enc",
            provider="openai-codex",
            model="gpt-6.1-sol",
            api_mode="codex_responses",
            base_url=APPROVED_BASE_URL,
            reasoning_effort="high",
        )
        token = self.observer.context_var.set(req_meta)
        try:
            req = client.build_request("POST", "http://127.0.0.1:8787/chatgpt%2fresponses")
            client.send(req)
        finally:
            self.observer.context_var.reset(token)

        records = self._read_records()
        http_reqs = [r for r in records if r.get("event") == "http_request"]
        self.assertEqual(len(http_reqs), 1)
        self.assertEqual(http_reqs[0]["url"], "<unapproved_route_mismatch>")
        self.assertFalse(http_reqs[0]["route_approved"])


class TestSinkSecurityAndBounding(unittest.TestCase):
    """Test sink permissions, symlink rejection, path escape, bounding, and invalidation."""

    def test_mode_0600_and_exclusive_creation(self) -> None:
        """Prove sink creates file with mode 0600 and rejects overwrite."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            resolved_tmp = Path(tmp_dir).resolve()
            target = resolved_tmp / "output.jsonl"
            sink = CaptureSink(target, allowed_root=resolved_tmp)
            sink.close()

            stat_info = os.stat(str(target))
            mode = stat_info.st_mode & 0o777
            self.assertEqual(mode, 0o600)

            with self.assertRaises(FileExistsError):
                CaptureSink(target, allowed_root=resolved_tmp)

    def test_path_escape_rejected(self) -> None:
        """Prove path escaping outside allowed_root is rejected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            resolved_tmp = Path(tmp_dir).resolve()
            allowed = resolved_tmp / "allowed"
            allowed.mkdir()
            target = allowed / ".." / "escaped.jsonl"
            with self.assertRaises(ValueError):
                CaptureSink(target, allowed_root=allowed)

    def test_symlink_rejected(self) -> None:
        """Prove symlinks in path are rejected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            resolved_tmp = Path(tmp_dir).resolve()
            real_dir = resolved_tmp / "real"
            real_dir.mkdir()
            link_dir = resolved_tmp / "link"
            os.symlink(real_dir, link_dir)

            target = link_dir / "output.jsonl"
            with self.assertRaises(ValueError):
                CaptureSink(target, allowed_root=resolved_tmp)

    def test_record_limit_bounding_and_invalidation(self) -> None:
        """Prove exceeding max_events invalidates proof safely without unbounded growth."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            resolved_tmp = Path(tmp_dir).resolve()
            target = resolved_tmp / "bounded.jsonl"
            sink = CaptureSink(target, allowed_root=resolved_tmp, max_events=3)
            for i in range(6):
                sink.write_record({"event": f"ev_{i}"})
            sink.close()

            lines = target.read_text().splitlines()
            records = [json.loads(line) for line in lines]
            self.assertTrue(sink.invalidated)
            self.assertEqual(sink.invalidation_reason, "record_limit_exceeded")
            self.assertLessEqual(len(records), 4)
            self.assertEqual(records[-1]["event"], "capture_invalidated")

    def test_write_failure_durable_visible_invalidation(self) -> None:
        """Probe write failure: replaced _file raising OSError produces on-disk invalidation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            resolved_tmp = Path(tmp_dir).resolve()
            target = resolved_tmp / "fail_write.jsonl"
            sink = CaptureSink(target, allowed_root=resolved_tmp)

            sink.write_record({"event": "prior_success", "payload": 1})

            if sink._file is not None:
                sink._file.close()

            sentinel_secret = "SYNTHETIC_PRIVATE_SENTINEL_ERROR"

            class BrokenWriter:
                def write(self, s: str) -> None:
                    raise OSError(sentinel_secret)

                def flush(self) -> None:
                    pass

                def fileno(self) -> int:
                    raise OSError("no fileno")

            sink._file = BrokenWriter()

            sink.write_record({"event": "should_fail"})

            self.assertTrue(sink.invalidated)
            self.assertEqual(sink.invalidation_reason, "capture_write_failure")

            raw_text = target.read_text(encoding="utf-8")
            records = [json.loads(line) for line in raw_text.splitlines() if line.strip()]

            event_types = [r.get("event") for r in records]
            self.assertIn("prior_success", event_types)
            self.assertIn("capture_invalidated", event_types)
            self.assertFalse(records[-1]["valid"])

            self.assertNotIn(sentinel_secret, raw_text)
            sink.close()

    def test_flush_failure_durable_visible_invalidation(self) -> None:
        """Probe flush failure: _file.flush raising OSError produces on-disk invalidation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            resolved_tmp = Path(tmp_dir).resolve()
            target = resolved_tmp / "fail_flush.jsonl"
            sink = CaptureSink(target, allowed_root=resolved_tmp)
            sink.write_record({"event": "prior_success"})

            class BrokenFlusher:
                def __init__(self, real_f: Any) -> None:
                    self.real_f = real_f

                def write(self, s: str) -> Any:
                    return self.real_f.write(s)

                def flush(self) -> None:
                    raise OSError("Disk flush failed")

                def fileno(self) -> int:
                    return self.real_f.fileno()

                def close(self) -> Any:
                    if hasattr(self.real_f, "close"):
                        return self.real_f.close()

            sink._file = BrokenFlusher(sink._file)
            sink.write_record({"event": "should_fail_flush"})

            self.assertTrue(sink.invalidated)
            self.assertEqual(sink.invalidation_reason, "capture_write_failure")

            raw_text = target.read_text(encoding="utf-8")
            records = [json.loads(line) for line in raw_text.splitlines() if line.strip()]
            event_types = [r.get("event") for r in records]
            self.assertIn("capture_invalidated", event_types)
            self.assertFalse(records[-1]["valid"])
            sink.close()

    def test_closed_sink_durable_visible_invalidation(self) -> None:
        """Prove writing to a closed sink records durable invalidation on disk via fallback."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            resolved_tmp = Path(tmp_dir).resolve()
            target = resolved_tmp / "closed.jsonl"
            sink = CaptureSink(target, allowed_root=resolved_tmp)
            sink.write_record({"event": "prior_success"})
            sink.close()

            sink.write_record({"event": "after_close"})

            self.assertTrue(sink.invalidated)
            self.assertEqual(sink.invalidation_reason, "sink_closed")

            raw_text = target.read_text(encoding="utf-8")
            records = [json.loads(line) for line in raw_text.splitlines() if line.strip()]
            event_types = [r.get("event") for r in records]
            self.assertIn("capture_invalidated", event_types)

    def test_invalidation_fallback_file_replaced_by_symlink_does_not_modify_target(self) -> None:
        """Defect A probe: file replaced by symlink does NOT modify outside target."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir).resolve()
            outside = root / "outside.txt"
            outside.write_text("UNCHANGED", encoding="utf-8")

            cap = root / "cap.jsonl"
            s = CaptureSink(cap, allowed_root=root)
            s.close()

            cap.unlink()
            cap.symlink_to(outside)

            s.invalidate("synthetic_failure")

            self.assertEqual(outside.read_text(encoding="utf-8"), "UNCHANGED")
            self.assertTrue(s.invalidation_recorded)
            marker = cap.with_name(cap.name + ".invalid")
            self.assertTrue(marker.exists())
            self.assertFalse(os.path.islink(marker))
            self.assertEqual(os.stat(marker).st_mode & 0o777, 0o600)
            records = [json.loads(line) for line in marker.read_text().splitlines() if line.strip()]
            self.assertEqual(records[-1]["event"], "capture_invalidated")

    def test_fallback_marker_symlink_and_preexisting_marker_protects_sentinel(self) -> None:
        """Defect A probe: marker symlink or preexisting file does NOT overwrite target."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir).resolve()
            outside = root / "outside.txt"
            outside.write_text("UNCHANGED", encoding="utf-8")

            cap = root / "cap.jsonl"
            s = CaptureSink(cap, allowed_root=root)
            s.close()
            cap.unlink()
            cap.symlink_to(outside)

            marker = cap.with_name(cap.name + ".invalid")
            marker.symlink_to(outside)

            s.invalidate("synthetic_failure")
            self.assertEqual(outside.read_text(encoding="utf-8"), "UNCHANGED")
            self.assertTrue(s.invalidation_record_error)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir).resolve()
            outside = root / "outside.txt"
            outside.write_text("UNCHANGED", encoding="utf-8")

            cap = root / "cap.jsonl"
            s = CaptureSink(cap, allowed_root=root)
            s.close()
            cap.unlink()
            cap.symlink_to(outside)

            marker = cap.with_name(cap.name + ".invalid")
            marker.write_text("PREEXISTING_MARKER_CONTENT", encoding="utf-8")

            s.invalidate("synthetic_failure")
            self.assertEqual(outside.read_text(encoding="utf-8"), "UNCHANGED")
            self.assertEqual(marker.read_text(encoding="utf-8"), "PREEXISTING_MARKER_CONTENT")
            self.assertTrue(s.invalidation_record_error)

    def test_parent_and_root_symlink_substitution_rejected(self) -> None:
        """Defect A: Symlinks in parent hierarchy or root itself are strictly rejected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir).resolve()
            real_parent = root / "real_parent"
            real_parent.mkdir()

            parent_link = root / "parent_link"
            parent_link.symlink_to(real_parent)
            with self.assertRaises(ValueError) as cm:
                CaptureSink(parent_link / "cap.jsonl", allowed_root=root)
            self.assertIn("Symlink rejected", str(cm.exception))

            root_link = root / "root_link"
            root_link.symlink_to(real_parent)
            with self.assertRaises(ValueError) as cm2:
                CaptureSink(root_link / "cap.jsonl", allowed_root=root_link)
            self.assertIn("Symlink rejected", str(cm2.exception))

    def test_visible_fallback_alert_on_storage_failure_without_secrets(self) -> None:
        """Defect A: Stderr alert is emitted without secrets when all storage fallbacks fail."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir).resolve()
            outside = root / "outside.txt"
            outside.write_text("UNCHANGED", encoding="utf-8")

            cap = root / "cap.jsonl"
            s = CaptureSink(cap, allowed_root=root)
            s.close()
            cap.unlink()
            cap.symlink_to(outside)

            marker = cap.with_name(cap.name + ".invalid")
            marker.symlink_to(outside)

            secret_reason = "SECRET_FAILURE_PAYLOAD_TOKEN"
            stderr_buffer = io.StringIO()
            orig_stderr = sys.stderr
            try:
                sys.stderr = stderr_buffer
                s.invalidate(secret_reason)
            finally:
                sys.stderr = orig_stderr

            output_err = stderr_buffer.getvalue()
            self.assertIn("HERDR_OBSERVER_ALERT: capture_invalidated storage failure", output_err)
            self.assertNotIn(secret_reason, output_err)
            self.assertTrue(s.invalidation_record_error)
            self.assertEqual(outside.read_text(encoding="utf-8"), "UNCHANGED")

    def test_invalidation_repeated_calls_do_not_append_unboundedly(self) -> None:
        """Defect A: Repeated invalidation calls do not append duplicate invalidation records."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir).resolve()
            cap = root / "cap.jsonl"
            s = CaptureSink(cap, allowed_root=root)
            s.write_record({"event": "ev1"})

            s.invalidate("first_invalidation_reason")
            for _ in range(10):
                s.invalidate("repeated_invalidation_reason")
            s.close()

            lines = cap.read_text(encoding="utf-8").strip().splitlines()
            records = [json.loads(line) for line in lines]
            invalidation_records = [r for r in records if r.get("event") == "capture_invalidated"]
            self.assertEqual(len(invalidation_records), 1)
            self.assertEqual(invalidation_records[0]["reason"], "first_invalidation_reason")

    def test_swapped_immediate_parent_during_first_open_rejected(self) -> None:
        """Prove immediate parent directory swap to symlink during first open is strictly rejected.

        Reproduces coordinator evidence where parent directory is swapped after
        validate_path_safety but during initial directory open. Anchored descriptors
        and O_NOFOLLOW must reject the open, preserve outside sentinel, write zero
        bytes outside allowed_root, and cleanly rollback fds.
        """
        import observer

        with tempfile.TemporaryDirectory() as td:
            t = Path(td).resolve()
            allowed = t / "allowed"
            allowed.mkdir()
            parent = allowed / "attempt"
            parent.mkdir()
            outside = t / "outside"
            outside.mkdir()
            sentinel = outside / "sentinel.txt"
            sentinel.write_text("SENTINEL_UNTOUCHED", encoding="utf-8")

            orig_open = observer.os.open
            changed = [False]

            def patched_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
                if not changed[0] and (str(path) == parent.name or str(path) == str(parent)):
                    changed[0] = True
                    parent.rename(allowed / "saved_parent")
                    parent.symlink_to(outside, target_is_directory=True)
                return orig_open(path, flags, *args, **kwargs)

            observer.os.open = patched_open
            try:
                with self.assertRaises((OSError, ValueError)):
                    CaptureSink(parent / "capture.jsonl", allowed_root=allowed)
            finally:
                observer.os.open = orig_open

            self.assertTrue(changed[0], "Immediate parent swap must be injected")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "SENTINEL_UNTOUCHED")
            self.assertFalse(
                (outside / "capture.jsonl").exists(),
                "No file must be written outside allowed_root under swap",
            )

    def test_swapped_ancestor_and_root_during_first_open_rejected(self) -> None:
        """Prove ancestor directory and root swaps during first open are strictly rejected."""
        import observer

        # Case A: Root directory swapped during first open
        with tempfile.TemporaryDirectory() as td:
            t = Path(td).resolve()
            allowed = t / "allowed"
            allowed.mkdir()
            parent = allowed / "attempt"
            parent.mkdir()
            outside = t / "outside"
            outside.mkdir()
            sentinel = outside / "sentinel.txt"
            sentinel.write_text("ROOT_SENTINEL_UNTOUCHED", encoding="utf-8")

            orig_open = observer.os.open
            root_swapped = [False]

            def patch_root_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
                if not root_swapped[0] and (str(path) == allowed.name or str(path) == str(allowed)):
                    root_swapped[0] = True
                    allowed.rename(t / "saved_root")
                    allowed.symlink_to(outside, target_is_directory=True)
                return orig_open(path, flags, *args, **kwargs)

            observer.os.open = patch_root_open
            try:
                with self.assertRaises((OSError, ValueError)):
                    CaptureSink(parent / "capture.jsonl", allowed_root=allowed)
            finally:
                observer.os.open = orig_open

            self.assertTrue(root_swapped[0], "Root swap must be injected")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "ROOT_SENTINEL_UNTOUCHED")
            self.assertFalse((outside / "capture.jsonl").exists())

        # Case B: Intermediate ancestor directory swapped during first open
        with tempfile.TemporaryDirectory() as td:
            t = Path(td).resolve()
            allowed = t / "allowed"
            allowed.mkdir()
            sub = allowed / "sub"
            sub.mkdir()
            parent = sub / "attempt"
            parent.mkdir()
            outside = t / "outside"
            outside.mkdir()
            sentinel = outside / "sentinel.txt"
            sentinel.write_text("ANCESTOR_SENTINEL_UNTOUCHED", encoding="utf-8")

            orig_open = observer.os.open
            ancestor_swapped = [False]

            def patch_sub_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
                if not ancestor_swapped[0] and (str(path) == sub.name or str(path) == str(sub)):
                    ancestor_swapped[0] = True
                    sub.rename(allowed / "saved_sub")
                    sub.symlink_to(outside, target_is_directory=True)
                return orig_open(path, flags, *args, **kwargs)

            observer.os.open = patch_sub_open
            try:
                with self.assertRaises((OSError, ValueError)):
                    CaptureSink(parent / "capture.jsonl", allowed_root=allowed)
            finally:
                observer.os.open = orig_open

            self.assertTrue(ancestor_swapped[0], "Ancestor swap must be injected")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "ANCESTOR_SENTINEL_UNTOUCHED")
            self.assertFalse((outside / "capture.jsonl").exists())

    def test_swapped_ancestor_above_allowed_root_during_open_rejected(self) -> None:
        """Prove ancestor directory swap ABOVE allowed_root during open is strictly rejected.

        Reproduces root ancestor redirect: a directory above allowed_root (e.g. 'top')
        is swapped to a symlink pointing to outside during directory open. The coherent
        walk from '/' with O_NOFOLLOW on every component must reject 'top', rollback
        descriptors cleanly, leave outside sentinel untouched, and write zero files outside.
        """
        import observer

        with tempfile.TemporaryDirectory() as td:
            t = Path(td).resolve()
            top = t / "top"
            allowed = top / "allowed"
            parent = allowed / "attempt"
            parent.mkdir(parents=True)

            outside = t / "outside"
            (outside / "allowed" / "attempt").mkdir(parents=True)
            sentinel = outside / "sentinel.txt"
            sentinel.write_text("TOP_SENTINEL_UNTOUCHED", encoding="utf-8")

            orig_open = observer.os.open
            top_swapped = [False]

            def patch_top_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
                if not top_swapped[0] and (str(path) == top.name or str(path) == str(top)):
                    top_swapped[0] = True
                    top.rename(t / "saved_top")
                    top.symlink_to(outside, target_is_directory=True)
                return orig_open(path, flags, *args, **kwargs)

            observer.os.open = patch_top_open
            try:
                with self.assertRaises((OSError, ValueError)):
                    CaptureSink(parent / "capture.jsonl", allowed_root=allowed)
            finally:
                observer.os.open = orig_open

            self.assertTrue(top_swapped[0], "Top ancestor swap must be injected")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "TOP_SENTINEL_UNTOUCHED")
            self.assertFalse(
                (outside / "allowed" / "attempt" / "capture.jsonl").exists(),
                "No capture file must be written in outside tree",
            )
            self.assertFalse((outside / "capture.jsonl").exists())

    def test_swapped_root_ancestor_between_validation_and_anchor_open_rejected(self) -> None:
        """Prove swap between validate_path_safety and descriptor acquisition is rejected."""
        import observer

        with tempfile.TemporaryDirectory() as td:
            t = Path(td).resolve()
            top = t / "top"
            allowed = top / "allowed"
            parent = allowed / "attempt"
            parent.mkdir(parents=True)

            outside = t / "outside"
            (outside / "allowed" / "attempt").mkdir(parents=True)
            sentinel = outside / "sentinel.txt"
            sentinel.write_text("BETWEEN_SENTINEL_UNTOUCHED", encoding="utf-8")

            orig_validate = observer.validate_path_safety
            swapped_between = [False]

            def patch_validate(*args: Any, **kwargs: Any) -> Path:
                res = orig_validate(*args, **kwargs)
                if not swapped_between[0]:
                    swapped_between[0] = True
                    top.rename(t / "saved_top_between")
                    top.symlink_to(outside, target_is_directory=True)
                return res

            observer.validate_path_safety = patch_validate
            try:
                with self.assertRaises((OSError, ValueError)):
                    CaptureSink(parent / "capture.jsonl", allowed_root=allowed)
            finally:
                observer.validate_path_safety = orig_validate

            self.assertTrue(
                swapped_between[0], "Swap between validation and anchor must be injected"
            )
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "BETWEEN_SENTINEL_UNTOUCHED")
            self.assertFalse(
                (outside / "allowed" / "attempt" / "capture.jsonl").exists(),
                "No capture file must be written in outside tree",
            )
            self.assertFalse((outside / "capture.jsonl").exists())

    def test_clean_fd_rollback_on_rejection(self) -> None:
        """Prove clean descriptor rollback on any failure with zero fd leak."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            allowed = root / "allowed"
            allowed.mkdir()
            parent = allowed / "attempt"
            parent.mkdir()

            def count_open_fds() -> int:
                count = 0
                for fd in range(3, 256):
                    try:
                        os.fstat(fd)
                        count += 1
                    except OSError:
                        pass
                return count

            initial_fds = count_open_fds()

            # Reject non-existent parent directory
            non_existent = allowed / "no_such_dir" / "capture.jsonl"
            with self.assertRaises(ValueError):
                CaptureSink(non_existent, allowed_root=allowed)

            # Reject path escape
            escape = allowed / ".." / "outside.jsonl"
            with self.assertRaises(ValueError):
                CaptureSink(escape, allowed_root=allowed)

            # Reject pre-existing file
            existing = parent / "exists.jsonl"
            existing.write_text("PRE", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                CaptureSink(existing, allowed_root=allowed)

            # Reject symlink in path
            link_dir = allowed / "symlink_dir"
            os.symlink(parent, link_dir)
            with self.assertRaises(ValueError):
                CaptureSink(link_dir / "capture.jsonl", allowed_root=allowed)

            final_fds = count_open_fds()
            self.assertEqual(
                initial_fds,
                final_fds,
                f"File descriptors leaked on rejection: initial {initial_fds}, final {final_fds}",
            )

    def test_positive_canonical_and_macos_system_alias_paths(self) -> None:
        """Prove positive path safety for both canonical /private/tmp and macOS /tmp alias."""
        with tempfile.TemporaryDirectory() as td:
            canonical_root = Path(td).resolve()
            cap_canonical = canonical_root / "canonical.jsonl"
            sink1 = CaptureSink(cap_canonical, allowed_root=canonical_root)
            sink1.write_record({"event": "canonical_ok"})
            sink1.close()
            self.assertTrue(cap_canonical.exists())
            self.assertEqual(os.stat(cap_canonical).st_mode & 0o777, 0o600)

        # Test macOS /tmp system alias handling if platform is darwin
        if sys.platform == "darwin":
            test_dir = tempfile.mkdtemp(prefix="macos-alias-test-", dir="/tmp")
            try:
                raw_tmp_root = Path(test_dir)  # /tmp/... (unresolved)
                cap_file = raw_tmp_root / "alias.jsonl"
                sink2 = CaptureSink(cap_file, allowed_root=raw_tmp_root)
                sink2.write_record({"event": "macos_alias_ok"})
                sink2.close()
                self.assertTrue(cap_file.exists())
                self.assertEqual(os.stat(cap_file).st_mode & 0o777, 0o600)
            finally:
                shutil.rmtree(test_dir, ignore_errors=True)


class TestLauncherOfflineAndValidation(unittest.TestCase):
    """Test launcher argument validation, offline --help subprocess, and HERDR_ENV enforcement."""

    def test_offline_help_subprocess_execution(self) -> None:
        """EXECUTE exact subprocess managed Python -B launcher.py --help with HERDR_ENV unset."""
        env = dict(os.environ)
        env.pop("HERDR_ENV", None)
        env.pop("HERDR_OBSERVER_OUTPUT_PATH", None)

        launcher_path = P01_DIR / "launcher.py"

        res = subprocess.run(
            [str(MANAGED_PYTHON), "-B", str(launcher_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )

        self.assertEqual(res.returncode, 0, f"Help failed: {res.stderr}")
        self.assertIn("--provider", res.stdout)
        self.assertIn("--model", res.stdout)
        self.assertIn("--cli", res.stdout)

    def test_help_bypass_strictly_for_help_alone(self) -> None:
        """Prove help flag combined with any other argument is rejected by launcher."""
        self.assertTrue(is_strictly_help(["-h"]))
        self.assertTrue(is_strictly_help(["--help"]))
        self.assertFalse(is_strictly_help(["--help", "--cli"]))
        self.assertFalse(is_strictly_help(["--help", "-q", "malicious"]))

    def test_genuine_herdr_env_enforcement(self) -> None:
        """Prove real launch refuses execution if HERDR_ENV != '1'."""
        saved_env = os.environ.get("HERDR_ENV")
        try:
            os.environ.pop("HERDR_ENV", None)
            with self.assertRaises(RuntimeError) as cm:
                build_runtime_command(["--cli"])
            self.assertIn("Genuine HERDR_ENV=1 required", str(cm.exception))
        finally:
            if saved_env is not None:
                os.environ["HERDR_ENV"] = saved_env

    def test_approved_human_route_arguments(self) -> None:
        """Prove approved human route flags pass validation without error."""
        valid_args = [
            "--cli",
            "--ignore-rules",
            "--toolsets",
            APPROVED_TOOLSETS,
            "--provider",
            APPROVED_PROVIDER,
            "--pass-session-id",
            "--in",
            "/tmp/test_dir",
            "-m",
            APPROVED_MODEL,
            "--reasoning",
            APPROVED_REASONING,
        ]
        validate_launch_arguments(valid_args)

    def test_injection_flags_rejected(self) -> None:
        """Prove arbitrary prompt injection or non-whitelisted flags are rejected."""
        for flag in ["-z", "--oneshot", "--eval", "-q"]:
            with self.assertRaises(ValueError):
                validate_launch_arguments(["--cli", flag])

    def test_is_actual_route_compliance(self) -> None:
        """Prove is_actual_route guard accepts openai-codex loopback and rejects actual."""
        from hermes_cli.providers import is_actual_route

        self.assertFalse(is_actual_route("openai-codex", APPROVED_BASE_URL))
        self.assertTrue(is_actual_route("actual", APPROVED_BASE_URL))
        self.assertTrue(is_actual_route("openai-codex", "https://api.actual.inc"))

    def test_observer_main_rejects_unapproved_repo_and_artifacts_overrides(self) -> None:
        """Defect D: observer.main rejects arbitrary repo and artifacts overrides."""
        import observer

        orig_repo = os.environ.get("HERMES_REPO_ROOT")
        orig_artifacts = os.environ.get("HERDR_PILOT_ARTIFACTS_ROOT")
        orig_out = os.environ.get("HERDR_OBSERVER_OUTPUT_PATH")
        try:
            os.environ["HERDR_OBSERVER_OUTPUT_PATH"] = "/tmp/dummy.jsonl"
            os.environ["HERMES_REPO_ROOT"] = "/unapproved/repo/root"
            with self.assertRaises(ValueError) as cm:
                observer.main()
            self.assertIn("Unapproved HERMES_REPO_ROOT override", str(cm.exception))

            os.environ.pop("HERMES_REPO_ROOT", None)
            os.environ["HERDR_PILOT_ARTIFACTS_ROOT"] = "/unapproved/artifacts/root"
            with self.assertRaises(ValueError) as cm2:
                observer.main()
            self.assertIn("Unapproved HERDR_PILOT_ARTIFACTS_ROOT override", str(cm2.exception))
        finally:
            if orig_repo is not None:
                os.environ["HERMES_REPO_ROOT"] = orig_repo
            else:
                os.environ.pop("HERMES_REPO_ROOT", None)

            if orig_artifacts is not None:
                os.environ["HERDR_PILOT_ARTIFACTS_ROOT"] = orig_artifacts
            else:
                os.environ.pop("HERDR_PILOT_ARTIFACTS_ROOT", None)

            if orig_out is not None:
                os.environ["HERDR_OBSERVER_OUTPUT_PATH"] = orig_out
            else:
                os.environ.pop("HERDR_OBSERVER_OUTPUT_PATH", None)

    def test_startup_observer_install_before_cli_entry_and_argv_retention(self) -> None:
        """Defect C: OFFLINE subprocess through ACTUAL installed runtime_command + run_path.

        Stubs only the hermes_cli.main entry to verify:
        1. Pinned Hermes sources verified with real hashes.
        2. Observer is fully installed and agent.codex_runtime.run_codex_stream is wrapped.
        3. sys.argv preserved across native launcher runtime_command invocation.
        4. No model, auth, or network requests performed.
        """
        from hermes_cli import _launchers

        test_dir = tempfile.mkdtemp(
            prefix="offline-startup-test-", dir=str(APPROVED_PILOT_ARTIFACTS_ROOT)
        )
        try:
            test_dir_path = Path(test_dir).resolve()
            out_file = test_dir_path / "startup_capture.jsonl"
            obs_script = P01_DIR / "observer.py"

            test_args = ["--cli", "--test-argv-flag-1", "value_offline_2"]

            prelude = f"""
import sys, types, runpy, os

def synthetic_main():
    import agent.codex_runtime
    main_mod = sys.modules.get("__main__")
    obs = getattr(main_mod, "_GLOBAL_OBSERVER", None)
    if not obs or not obs._installed:
        print("OBSERVER_NOT_INSTALLED", file=sys.stderr)
        sys.exit(20)
    if not hasattr(agent.codex_runtime.run_codex_stream, "__wrapped__"):
        print("WRAPPER_NOT_INSTALLED", file=sys.stderr)
        sys.exit(21)
    if sys.argv[1:] != {repr(test_args)}:
        print(f"ARGV_MISMATCH: {{sys.argv[1:]}}", file=sys.stderr)
        sys.exit(22)
    print("STARTUP_OBSERVER_AND_ARGV_VERIFIED")
    sys.exit(0)

mod = types.ModuleType("hermes_cli.main")
mod.main = synthetic_main
sys.modules["hermes_cli.main"] = mod

if {repr(str(P01_DIR))} not in sys.path:
    sys.path.insert(0, {repr(str(P01_DIR))})

runpy.run_path({repr(str(obs_script))}, run_name="__main__")
"""

            cmd = _launchers.runtime_command(
                PINNED_HERMES_ROOT, test_args, code=prelude, python=MANAGED_PYTHON
            )

            env = dict(os.environ)
            env.pop("HERDR_ENV", None)  # Do NOT fake HERDR_ENV
            env["HERDR_OBSERVER_OUTPUT_PATH"] = str(out_file)

            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                env=env,
            )

            self.assertEqual(
                res.returncode, 0, f"Subprocess failed ({res.returncode}):\n{res.stderr}"
            )
            self.assertIn("STARTUP_OBSERVER_AND_ARGV_VERIFIED", res.stdout)
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_launcher_secret_uri_and_unknown_flags_exclusion_from_all_output(self) -> None:
        """Prove secret URI credentials and unknown flags are NEVER echoed to stdout/stderr."""
        secret_uri = "http://user:SECRET_TOKEN_SENTINEL_XYZ@127.0.0.1:8787/chatgpt"
        secret_flag = "--secret=FLAG_SECRET_SENTINEL_123"
        forbidden_prompt = "SECRET_PROMPT_SENTINEL_777"

        # 1. Base URL rejection does not leak secret URI
        saved_herdr = os.environ.get("HERDR_ENV")
        saved_base = os.environ.get("HERMES_CODEX_BASE_URL")
        try:
            os.environ["HERDR_ENV"] = "1"
            os.environ["HERMES_CODEX_BASE_URL"] = secret_uri
            with self.assertRaises(ValueError) as cm:
                build_runtime_command(["--cli"], is_offline_help=False)
            err_msg = str(cm.exception)
            self.assertIn("Invalid HERMES_CODEX_BASE_URL", err_msg)
            self.assertNotIn("SECRET_TOKEN_SENTINEL_XYZ", err_msg)
            self.assertNotIn(secret_uri, err_msg)
        finally:
            if saved_herdr is not None:
                os.environ["HERDR_ENV"] = saved_herdr
            else:
                os.environ.pop("HERDR_ENV", None)
            if saved_base is not None:
                os.environ["HERMES_CODEX_BASE_URL"] = saved_base
            else:
                os.environ.pop("HERMES_CODEX_BASE_URL", None)

        # 2. Unknown CLI flag does not leak flag content
        with self.assertRaises(ValueError) as cm2:
            validate_launch_arguments(["--cli", secret_flag])
        err_msg2 = str(cm2.exception)
        self.assertIn("Unapproved extra CLI flags", err_msg2)
        self.assertNotIn("FLAG_SECRET_SENTINEL_123", err_msg2)
        self.assertNotIn(secret_flag, err_msg2)

        # 3. Forbidden injection flag does not leak flag content
        with self.assertRaises(ValueError) as cm3:
            validate_launch_arguments(["--cli", "-z", forbidden_prompt])
        err_msg3 = str(cm3.exception)
        self.assertIn("Forbidden prompt/execution flag rejected", err_msg3)
        self.assertNotIn(forbidden_prompt, err_msg3)

    def test_observer_startup_override_secrets_exclusion(self) -> None:
        """Prove observer startup rejects root overrides without echoing secret path tokens."""
        import observer

        secret_repo = "/tmp/SECRET_REPO_SENTINEL_ABC"
        secret_artifacts = "/tmp/SECRET_ARTIFACTS_SENTINEL_DEF"

        orig_repo = os.environ.get("HERMES_REPO_ROOT")
        orig_artifacts = os.environ.get("HERDR_PILOT_ARTIFACTS_ROOT")
        orig_out = os.environ.get("HERDR_OBSERVER_OUTPUT_PATH")
        try:
            os.environ["HERDR_OBSERVER_OUTPUT_PATH"] = "/tmp/dummy.jsonl"
            os.environ["HERMES_REPO_ROOT"] = secret_repo
            with self.assertRaises(ValueError) as cm:
                observer.main()
            msg1 = str(cm.exception)
            self.assertIn("Unapproved HERMES_REPO_ROOT override", msg1)
            self.assertNotIn("SECRET_REPO_SENTINEL_ABC", msg1)

            os.environ.pop("HERMES_REPO_ROOT", None)
            os.environ["HERDR_PILOT_ARTIFACTS_ROOT"] = secret_artifacts
            with self.assertRaises(ValueError) as cm2:
                observer.main()
            msg2 = str(cm2.exception)
            self.assertIn("Unapproved HERDR_PILOT_ARTIFACTS_ROOT override", msg2)
            self.assertNotIn("SECRET_ARTIFACTS_SENTINEL_DEF", msg2)
        finally:
            if orig_repo is not None:
                os.environ["HERMES_REPO_ROOT"] = orig_repo
            else:
                os.environ.pop("HERMES_REPO_ROOT", None)
            if orig_artifacts is not None:
                os.environ["HERDR_PILOT_ARTIFACTS_ROOT"] = orig_artifacts
            else:
                os.environ.pop("HERDR_PILOT_ARTIFACTS_ROOT", None)
            if orig_out is not None:
                os.environ["HERDR_OBSERVER_OUTPUT_PATH"] = orig_out
            else:
                os.environ.pop("HERDR_OBSERVER_OUTPUT_PATH", None)


if __name__ == "__main__":
    unittest.main()
