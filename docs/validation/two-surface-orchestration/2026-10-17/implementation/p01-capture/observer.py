"""In-process disposable observer for P01 request evidence capture.

Observes:
- Actual agent.api_mode from the live agent argument.
- Actual HTTP request URL, method, and response status from httpx event hooks.
- Request-local correlation using ContextVar and weak references per exchange.
- Exclusive 0600 JSONL output with path-safety, bounding, and fail-safe invalidation.
- Zero credential, body, header, prompt, or arbitrary exception text retention.
"""

from __future__ import annotations

import contextlib
import contextvars
import errno
import functools
import hashlib
import inspect
import itertools
import json
import os
import stat
import sys
import threading
import weakref
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

# Approved route constants
APPROVED_LOOPBACK_ORIGIN = "http://127.0.0.1:8787"
APPROVED_BASE_URL = "http://127.0.0.1:8787/chatgpt"
APPROVED_RESPONSES_URL = "http://127.0.0.1:8787/chatgpt/responses"
UNAPPROVED_ROUTE_MARKER = "<unapproved_route_mismatch>"
UNAPPROVED_BASE_URL_MARKER = "<unapproved_base_url_mismatch>"

# Pinned production roots
PINNED_HERMES_ROOT = Path("/Users/corvette/.hermes/hermes-agent")
APPROVED_PILOT_ARTIFACTS_ROOT = Path(
    "/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts"
)

# Source SHA-256 pins from frozen contract
SOURCE_PINS: Mapping[str, str] = {
    "agent/codex_runtime.py": "88bbcfb34e4a7ab4aadf50ea6409eb35a5a6a615dd821a322768215864756f30",
    "agent/relay_llm.py": "9a2a0242bdafdf33c1bf8f38219a7aba318d87c6ea65657b7d888c55ae9b85ea",
    "hermes_cli/_launchers.py": "9cf612547558a28a7840544a44c5f5ab866ee527a05f96000aefdf51cd7fcbcd",
    "agent/client_lifecycle.py": "4e8a80556184c415256934c50e6191b840910867fe68d36efc263440ea7b7dd2",
    "agent/lazy_forward.py": "c5dcd627dd7cb4490128208a1220fb1edeac3d0ccbe4b91d8406ed20d3f3cdf7",
    "agent/chat_completion_helpers.py": (
        "d7b982ddeabe7bb02cb92fd905d213ecba3b2d21672e249510f760fff27ec8a1"
    ),
}


class SourceVerificationError(RuntimeError):
    """Raised when installed Hermes sources or signatures deviate from pinned contracts."""


def verify_source_pins(repo_root: Path | str) -> None:
    """Verify that installed sources match the pinned SHA-256 hashes."""
    root = Path(repo_root).resolve()
    for rel_path, expected_hash in SOURCE_PINS.items():
        target = root / rel_path
        if not target.exists():
            raise SourceVerificationError(f"Required source file missing: {rel_path}")
        content = target.read_bytes()
        actual_hash = hashlib.sha256(content).hexdigest()
        if actual_hash != expected_hash:
            raise SourceVerificationError(
                f"Source hash mismatch for {rel_path}: expected {expected_hash}, got {actual_hash}"
            )


def sanitize_url(raw_url: str | httpx.URL) -> tuple[str, bool]:
    """Strip credentials, query, and fragments. Return approved URL or safe mismatch marker."""
    try:
        parsed = httpx.URL(raw_url)
        # Check raw request path directly to prevent decoded alternative paths from passing
        raw_target = parsed.raw_path.split(b"?")[0].split(b"#")[0]
        if raw_target != b"/chatgpt/responses":
            return UNAPPROVED_ROUTE_MARKER, False
        netloc = f"{parsed.host}:{parsed.port}" if parsed.port else (parsed.host or "")
        path_str = raw_target.decode("ascii")
        cleaned = f"{parsed.scheme}://{netloc}{path_str}"
        if cleaned == APPROVED_RESPONSES_URL:
            return cleaned, True
        return UNAPPROVED_ROUTE_MARKER, False
    except Exception:
        return UNAPPROVED_ROUTE_MARKER, False


def sanitize_base_url(raw_base: Any) -> tuple[str, bool]:
    """Strip credentials/query/fragments. Return approved base or mismatch marker."""
    if not raw_base:
        return "", False
    try:
        parsed = httpx.URL(str(raw_base))
        raw_target = parsed.raw_path.split(b"?")[0].split(b"#")[0].rstrip(b"/")
        if raw_target != b"/chatgpt":
            return UNAPPROVED_BASE_URL_MARKER, False
        netloc = f"{parsed.host}:{parsed.port}" if parsed.port else (parsed.host or "")
        path_str = raw_target.decode("ascii")
        cleaned = f"{parsed.scheme}://{netloc}{path_str}"
        if cleaned == APPROVED_BASE_URL:
            return cleaned, True
        return UNAPPROVED_BASE_URL_MARKER, False
    except Exception:
        return UNAPPROVED_BASE_URL_MARKER, False


def _extract_scalar(val: Any) -> str | None:
    """Extract a scalar string only if val is str, int, or float.

    Never converts a dict, list, set, or arbitrary object to string.
    """
    if val is None or isinstance(val, (bool, dict, list, set, tuple)):
        return None
    if isinstance(val, (str, int, float)):
        s = str(val).strip()
        return s if s else None
    return None


@dataclass(frozen=True)
class RequestMetadata:
    """Strict scalar whitelist extracted from agent and api_kwargs."""

    session_id: str | None
    api_request_id: str | None
    provider: str | None
    model: str | None
    api_mode: str | None
    base_url: str | None
    reasoning_effort: str | None


def extract_scalar_metadata(
    agent: Any, api_kwargs: Mapping[str, Any], client: Any = None
) -> RequestMetadata:
    """Extract scalar metadata without retaining agent, args, prompts, or credentials."""
    raw_session = getattr(agent, "session_id", None)
    session_id = _extract_scalar(raw_session)

    raw_req_id = getattr(agent, "_current_api_request_id", None) or api_kwargs.get("api_request_id")
    api_request_id = _extract_scalar(raw_req_id)

    raw_provider = getattr(agent, "provider", None)
    provider = _extract_scalar(raw_provider)

    raw_model = getattr(agent, "model", None) or api_kwargs.get("model")
    model = _extract_scalar(raw_model)

    raw_api_mode = getattr(agent, "api_mode", None)
    api_mode = _extract_scalar(raw_api_mode)

    raw_base = getattr(client, "base_url", None) or getattr(agent, "base_url", None)
    base_url, _ = sanitize_base_url(raw_base)

    effort: str | None = None
    if "reasoning_effort" in api_kwargs:
        effort = _extract_scalar(api_kwargs["reasoning_effort"])
    elif "reasoning" in api_kwargs and isinstance(api_kwargs["reasoning"], Mapping):
        effort = _extract_scalar(api_kwargs["reasoning"].get("effort"))
    elif hasattr(agent, "reasoning_effort") and not isinstance(
        getattr(agent, "reasoning_effort", None), (dict, list)
    ):
        effort = _extract_scalar(agent.reasoning_effort)
    elif hasattr(agent, "reasoning_config") and isinstance(
        getattr(agent, "reasoning_config", None), Mapping
    ):
        effort = _extract_scalar(agent.reasoning_config.get("effort"))
    elif hasattr(agent, "reasoning"):
        raw_r = getattr(agent, "reasoning", None)
        if isinstance(raw_r, Mapping):
            effort = _extract_scalar(raw_r.get("effort"))
        elif isinstance(raw_r, (str, int, float)):
            effort = _extract_scalar(raw_r)

    return RequestMetadata(
        session_id=session_id,
        api_request_id=api_request_id,
        provider=provider,
        model=model,
        api_mode=api_mode,
        base_url=base_url if base_url else None,
        reasoning_effort=effort,
    )


def normalize_lexical_path(raw: Path | str) -> Path:
    """Normalize path lexically to absolute normalized path.

    Preserves standard macOS /tmp -> /private/tmp, /var -> /private/var,
    and /etc -> /private/etc system aliases without following arbitrary symlinks.
    """
    norm = os.path.normpath(os.path.abspath(str(raw)))
    if sys.platform == "darwin":
        if (
            norm == "/tmp"
            or norm.startswith("/tmp/")
            or norm == "/var"
            or norm.startswith("/var/")
            or norm == "/etc"
            or norm.startswith("/etc/")
        ):
            norm = "/private" + norm
    return Path(norm)


def validate_path_safety(raw_path: Path | str, allowed_root: Path | str | None = None) -> Path:
    """Validate lexical path safety and containment within allowed_root.

    Returns the lexically normalized absolute path without resolving symlinks.
    The atomic O_NOFOLLOW descriptor walk enforces physical confinement during open.
    """
    target = normalize_lexical_path(raw_path)
    if allowed_root is not None:
        root = normalize_lexical_path(allowed_root)
        if target == root:
            raise ValueError(f"Target capture file cannot be the allowed root: {target}")
        try:
            target.relative_to(root)
        except ValueError as err:
            raise ValueError(
                f"Path escape rejected: {target} is outside allowed root {root}"
            ) from err
    return target


def open_anchored_parent_descriptor(
    target_path: Path | str, allowed_root: Path | str | None = None
) -> int:
    """Open parent directory descriptor securely anchored from filesystem root.

    Performs a single coherent directory-descriptor walk from filesystem root '/'
    through every root ancestor and then descendants with O_DIRECTORY|O_NOFOLLOW
    on each component relative to trusted previous dir_fd.
    Never obtains anchor via os.open(fullroot) or os.stat(fullroot).
    Descriptor anchors own actual directories; later renames/symlinks cannot
    redirect file writes. Intermediate fds are cleanly closed on all paths.
    """
    target_norm = normalize_lexical_path(target_path)
    parent_norm = target_norm.parent

    if allowed_root is not None:
        root_norm = normalize_lexical_path(allowed_root)
        if target_norm == root_norm:
            raise ValueError(f"Target capture file cannot be the allowed root: {target_norm}")
        try:
            parent_norm.relative_to(root_norm)
        except ValueError as err:
            raise ValueError(
                f"Path escape rejected: {parent_norm} is outside allowed root {root_norm}"
            ) from err
        try:
            target_norm.relative_to(root_norm)
        except ValueError as err:
            raise ValueError(
                f"Path escape rejected: {target_norm} is outside allowed root {root_norm}"
            ) from err

    parts = [p for p in parent_norm.parts if p and p not in ("/", ".")]
    dir_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)

    root_fd = os.open("/", os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    opened_fds: list[int] = [root_fd]
    curr_fd = root_fd

    try:
        for comp in parts:
            try:
                next_fd = os.open(comp, dir_flags, dir_fd=curr_fd)
            except OSError as err:
                is_link = False
                try:
                    os.readlink(comp, dir_fd=curr_fd)
                    is_link = True
                except OSError:
                    pass
                if is_link or err.errno == errno.ELOOP:
                    raise ValueError(f"Symlink rejected: {comp}") from err
                if err.errno == errno.ENOENT:
                    raise ValueError(f"Parent directory does not exist: {parent_norm}") from err
                raise ValueError(f"Failed to open directory component {comp}: {err}") from err

            opened_fds.append(next_fd)
            st = os.fstat(next_fd)
            if not stat.S_ISDIR(st.st_mode):
                raise ValueError(f"Path component is not a directory: {comp}")
            curr_fd = next_fd

        final_fd = curr_fd
        for fd in opened_fds:
            if fd != final_fd:
                with contextlib.suppress(Exception):
                    os.close(fd)
        return final_fd
    except Exception:
        for fd in opened_fds:
            with contextlib.suppress(Exception):
                os.close(fd)
        raise


class CaptureSink:
    """Exclusive mode-0600 JSONL writer with path protection, record bounding, and invalidation."""

    def __init__(
        self,
        output_path: Path | str,
        *,
        allowed_root: Path | str | None = None,
        max_events: int = 200,
    ) -> None:
        self.output_path_raw = Path(output_path)
        self.allowed_root_raw = Path(allowed_root) if allowed_root is not None else None
        self.target_path = validate_path_safety(
            self.output_path_raw, allowed_root=self.allowed_root_raw
        )
        self.allowed_root = (
            normalize_lexical_path(self.allowed_root_raw)
            if self.allowed_root_raw is not None
            else None
        )
        self.max_events = max_events
        self.lock = threading.Lock()
        self.event_count = 0
        self.invalidated = False
        self.invalidation_reason: str | None = None
        self.invalidation_recorded = False
        self.invalidation_record_error = False
        self._file: Any | None = None
        self._parent_fd: int | None = None

        self._parent_fd = open_anchored_parent_descriptor(
            self.target_path, allowed_root=self.allowed_root_raw
        )

        # Exclusive creation with mode 0600 and O_NOFOLLOW
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(self.target_path.name, flags, 0o600, dir_fd=self._parent_fd)
            self._file = os.fdopen(fd, "w", encoding="utf-8")
        except FileExistsError as err:
            if self._parent_fd is not None:
                with contextlib.suppress(Exception):
                    os.close(self._parent_fd)
                self._parent_fd = None
            self.close()
            msg = f"Target capture file already exists: {self.target_path}"
            raise FileExistsError(msg) from err
        except Exception:
            if self._parent_fd is not None:
                with contextlib.suppress(Exception):
                    os.close(self._parent_fd)
                self._parent_fd = None
            self.close()
            raise

        # Confirm permissions and record inode/device
        stat_info = os.fstat(self._file.fileno())
        if not stat.S_ISREG(stat_info.st_mode):
            self.close()
            raise ValueError(f"Target capture file is not a regular file: {self.target_path}")

        if (stat_info.st_mode & 0o777) != 0o600:
            os.fchmod(self._file.fileno(), 0o600)
            stat_info = os.fstat(self._file.fileno())

        self._ino = stat_info.st_ino
        self._dev = stat_info.st_dev

    def write_record(self, record: Mapping[str, Any]) -> None:
        """Serialize a whitelisted record under lock without leaking exceptions or payload."""
        with self.lock:
            if self.invalidated:
                return

            if self._file is None:
                self.invalidated = True
                self.invalidation_reason = "sink_closed"
                self._write_invalidation_record("sink_closed")
                return

            self.event_count += 1
            if self.event_count > self.max_events:
                self.invalidated = True
                self.invalidation_reason = "record_limit_exceeded"
                self._write_invalidation_record("record_limit_exceeded")
                return

            try:
                line = json.dumps(record, sort_keys=True) + "\n"
                self._file.write(line)
                self._file.flush()
            except Exception:
                self.invalidated = True
                self.invalidation_reason = "capture_write_failure"
                self._write_invalidation_record("capture_write_failure")

    def invalidate(self, reason: str) -> None:
        """Explicitly invalidate proof with a safe content-free reason."""
        with self.lock:
            if self.invalidated and (self.invalidation_recorded or self.invalidation_record_error):
                return
            self.invalidated = True
            if self.invalidation_reason is None:
                self.invalidation_reason = reason
            self._write_invalidation_record(reason)

    def _write_invalidation_record(self, reason: str) -> None:
        """Durably write content-free invalidation record reusing secure owned anchor."""
        if self.invalidation_recorded or self.invalidation_record_error:
            return

        record = {
            "event": "capture_invalidated",
            "reason": reason,
            "valid": False,
        }
        line = json.dumps(record, sort_keys=True) + "\n"
        line_bytes = line.encode("utf-8")

        wrote = False

        # 1. Try writing to existing open self._file verifying inode
        if self._file is not None:
            try:
                fd_num = self._file.fileno()
                st = os.fstat(fd_num)
                if (
                    stat.S_ISREG(st.st_mode)
                    and st.st_ino == self._ino
                    and st.st_dev == self._dev
                    and (st.st_mode & 0o777) == 0o600
                ):
                    self._file.write(line)
                    self._file.flush()
                    wrote = True
            except Exception:
                wrote = False

        # 2. Fallback: direct append to target_path using secure owned anchor descriptor
        if not wrote and self._parent_fd is not None:
            try:
                flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
                fd = os.open(self.target_path.name, flags, dir_fd=self._parent_fd)
                try:
                    st = os.fstat(fd)
                    if (
                        stat.S_ISREG(st.st_mode)
                        and st.st_ino == self._ino
                        and st.st_dev == self._dev
                        and (st.st_mode & 0o777) == 0o600
                    ):
                        os.write(fd, line_bytes)
                        wrote = True
                finally:
                    os.close(fd)
            except Exception:
                wrote = False

        # 3. Fallback: write invalidation companion file exclusively with mode 0600 and O_NOFOLLOW
        if not wrote and self._parent_fd is not None:
            try:
                marker_name = self.output_path_raw.name + ".invalid"
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
                fd = os.open(marker_name, flags, 0o600, dir_fd=self._parent_fd)
                try:
                    st = os.fstat(fd)
                    if stat.S_ISREG(st.st_mode) and (st.st_mode & 0o777) == 0o600:
                        os.write(fd, line_bytes)
                        wrote = True
                finally:
                    os.close(fd)
            except Exception:
                wrote = False

        if wrote:
            self.invalidation_recorded = True
            if self._file is None and self._parent_fd is not None:
                with contextlib.suppress(Exception):
                    os.close(self._parent_fd)
                self._parent_fd = None
        else:
            self.invalidation_record_error = True
            if self._file is None and self._parent_fd is not None:
                with contextlib.suppress(Exception):
                    os.close(self._parent_fd)
                self._parent_fd = None
            with contextlib.suppress(Exception):
                sys.stderr.write("HERDR_OBSERVER_ALERT: capture_invalidated storage failure\n")

    def close(self) -> None:
        """Close the underlying file handle and directory descriptor."""
        with self.lock:
            if self._file is not None:
                with contextlib.suppress(Exception):
                    self._file.close()
                self._file = None
            if self.invalidated and self._parent_fd is not None:
                with contextlib.suppress(Exception):
                    os.close(self._parent_fd)
                self._parent_fd = None

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            if self._parent_fd is not None:
                os.close(self._parent_fd)
                self._parent_fd = None


@dataclass
class PairedExchange:
    exchange_id: int
    req_meta: RequestMetadata
    sanitized_url: str
    route_approved: bool
    method: str


class RequestObserver:
    """Coordinates ContextVar request tracking and HTTPX client hooks."""

    def __init__(self, sink: CaptureSink) -> None:
        self.sink = sink
        self.context_var: contextvars.ContextVar[RequestMetadata | None] = contextvars.ContextVar(
            "p01_active_request_context", default=None
        )
        self.pending_exchanges: weakref.WeakKeyDictionary[httpx.Request, PairedExchange] = (
            weakref.WeakKeyDictionary()
        )
        self.exchange_counter = itertools.count(1)
        self._exchange_lock = threading.Lock()
        self._orig_run_codex_stream: Callable[..., Any] | None = None
        self._orig_httpx_client_init: Callable[..., Any] | None = None
        self._installed = False

    def on_request(self, request: httpx.Request) -> None:
        """HTTPX request hook."""
        try:
            method = str(request.method).upper()
            sanitized_url, route_approved = sanitize_url(request.url)
            if method != "POST":
                route_approved = False

            req_meta = self.context_var.get()
            is_correlated = bool(
                req_meta is not None and req_meta.session_id and req_meta.api_request_id
            )

            with self._exchange_lock:
                exchange_id = next(self.exchange_counter)
                if is_correlated and req_meta is not None:
                    paired = PairedExchange(
                        exchange_id=exchange_id,
                        req_meta=req_meta,
                        sanitized_url=sanitized_url,
                        route_approved=route_approved,
                        method=method,
                    )
                    self.pending_exchanges[request] = paired

            if is_correlated and req_meta is not None:
                self.sink.write_record(
                    {
                        "event": "http_request",
                        "exchange_id": exchange_id,
                        "session_id": req_meta.session_id,
                        "api_request_id": req_meta.api_request_id,
                        "api_mode": req_meta.api_mode,
                        "provider": req_meta.provider,
                        "model": req_meta.model,
                        "base_url": req_meta.base_url,
                        "reasoning_effort": req_meta.reasoning_effort,
                        "method": method,
                        "url": sanitized_url,
                        "route_approved": route_approved,
                        "correlated": True,
                    }
                )
            else:
                self.sink.write_record(
                    {
                        "event": "http_request",
                        "exchange_id": exchange_id,
                        "session_id": None,
                        "api_request_id": None,
                        "api_mode": None,
                        "provider": None,
                        "model": None,
                        "base_url": None,
                        "reasoning_effort": None,
                        "method": method,
                        "url": sanitized_url,
                        "route_approved": route_approved,
                        "correlated": False,
                    }
                )
        except Exception:
            with contextlib.suppress(Exception):
                self.sink.invalidate("observer_hook_failure")

    def on_response(self, response: httpx.Response) -> None:
        """HTTPX response hook."""
        try:
            request = getattr(response, "request", None)
            with self._exchange_lock:
                paired = self.pending_exchanges.pop(request, None) if request is not None else None

            status_code = int(response.status_code)
            resp_url_sanitized, resp_route_approved = sanitize_url(response.url)

            is_correlated = bool(
                paired is not None and paired.req_meta.session_id and paired.req_meta.api_request_id
            )

            if is_correlated and paired is not None:
                route_approved = paired.route_approved and resp_route_approved
                self.sink.write_record(
                    {
                        "event": "http_response",
                        "exchange_id": paired.exchange_id,
                        "session_id": paired.req_meta.session_id,
                        "api_request_id": paired.req_meta.api_request_id,
                        "api_mode": paired.req_meta.api_mode,
                        "provider": paired.req_meta.provider,
                        "model": paired.req_meta.model,
                        "base_url": paired.req_meta.base_url,
                        "reasoning_effort": paired.req_meta.reasoning_effort,
                        "method": paired.method,
                        "url": paired.sanitized_url,
                        "status_code": status_code,
                        "route_approved": route_approved,
                        "correlated": True,
                    }
                )
            else:
                self.sink.write_record(
                    {
                        "event": "http_response",
                        "exchange_id": None,
                        "session_id": None,
                        "api_request_id": None,
                        "api_mode": None,
                        "provider": None,
                        "model": None,
                        "base_url": None,
                        "reasoning_effort": None,
                        "method": (
                            str(getattr(request, "method", "")).upper()
                            if request is not None
                            else ""
                        ),
                        "url": resp_url_sanitized,
                        "status_code": status_code,
                        "route_approved": resp_route_approved,
                        "correlated": False,
                    }
                )
        except Exception:
            with contextlib.suppress(Exception):
                self.sink.invalidate("observer_hook_failure")

    def wrap_run_codex_stream(self, original_fn: Callable[..., Any]) -> Callable[..., Any]:
        """Wrap agent.codex_runtime.run_codex_stream with ContextVar scope."""

        @functools.wraps(original_fn)
        def run_codex_stream_wrapper(
            agent: Any, api_kwargs: dict[str, Any], client: Any = None, on_first_delta: Any = None
        ) -> Any:
            outer_token: contextvars.Token[RequestMetadata | None] | None = None
            req_meta: RequestMetadata | None = None
            enter_success = False
            try:
                try:
                    req_meta = extract_scalar_metadata(agent, api_kwargs, client=client)
                    outer_token = self.context_var.set(req_meta)
                    self.sink.write_record(
                        {
                            "event": "codex_stream_call_enter",
                            "session_id": req_meta.session_id,
                            "api_request_id": req_meta.api_request_id,
                            "api_mode": req_meta.api_mode,
                            "provider": req_meta.provider,
                            "model": req_meta.model,
                            "base_url": req_meta.base_url,
                            "reasoning_effort": req_meta.reasoning_effort,
                        }
                    )
                    enter_success = True
                except Exception:
                    with contextlib.suppress(Exception):
                        self.sink.invalidate("metadata_extraction_failure")
                    if outer_token is None:
                        with contextlib.suppress(Exception):
                            outer_token = self.context_var.set(None)
                    else:
                        with contextlib.suppress(Exception):
                            self.context_var.set(None)
                    req_meta = None

                # Original function MUST be called exactly once
                return original_fn(agent, api_kwargs, client=client, on_first_delta=on_first_delta)
            finally:
                if outer_token is not None:
                    with contextlib.suppress(Exception):
                        self.context_var.reset(outer_token)
                if enter_success and req_meta is not None:
                    with contextlib.suppress(Exception):
                        self.sink.write_record(
                            {
                                "event": "codex_stream_call_exit",
                                "session_id": req_meta.session_id,
                                "api_request_id": req_meta.api_request_id,
                            }
                        )

        return run_codex_stream_wrapper

    def install(self) -> None:
        """Install runtime patches into agent.codex_runtime and httpx.Client."""
        if self._installed:
            return

        import agent.codex_runtime

        sig = inspect.signature(agent.codex_runtime.run_codex_stream)
        params = list(sig.parameters.keys())
        if params[:2] != ["agent", "api_kwargs"]:
            raise SourceVerificationError(
                f"Unexpected run_codex_stream signature: {sig} (expected agent, api_kwargs, ...)"
            )

        self._orig_run_codex_stream = agent.codex_runtime.run_codex_stream
        agent.codex_runtime.run_codex_stream = self.wrap_run_codex_stream(
            self._orig_run_codex_stream
        )

        self._orig_httpx_client_init = httpx.Client.__init__
        observer_self = self

        def patched_client_init(client_instance: httpx.Client, *args: Any, **kwargs: Any) -> None:
            observer_self._orig_httpx_client_init(client_instance, *args, **kwargs)

            def req_hook(request: httpx.Request) -> None:
                try:
                    observer_self.on_request(request)
                except Exception:
                    with contextlib.suppress(Exception):
                        observer_self.sink.invalidate("observer_hook_failure")

            def resp_hook(response: httpx.Response) -> None:
                try:
                    observer_self.on_response(response)
                except Exception:
                    with contextlib.suppress(Exception):
                        observer_self.sink.invalidate("observer_hook_failure")

            client_instance.event_hooks["request"].append(req_hook)
            client_instance.event_hooks["response"].append(resp_hook)

        httpx.Client.__init__ = patched_client_init
        self._installed = True

    def uninstall(self) -> None:
        """Restore original functions."""
        if not self._installed:
            return
        if self._orig_run_codex_stream is not None:
            import agent.codex_runtime

            agent.codex_runtime.run_codex_stream = self._orig_run_codex_stream
            self._orig_run_codex_stream = None

        if self._orig_httpx_client_init is not None:
            httpx.Client.__init__ = self._orig_httpx_client_init
            self._orig_httpx_client_init = None

        self._installed = False


_GLOBAL_OBSERVER: RequestObserver | None = None


def setup_observer(
    output_path: Path | str,
    repo_root: Path | str = PINNED_HERMES_ROOT,
    allowed_root: Path | str | None = None,
    verify_pins: bool = True,
) -> RequestObserver:
    """Verify source pins, create exclusive sink, and install observer hooks."""
    global _GLOBAL_OBSERVER
    if verify_pins:
        verify_source_pins(repo_root)

    sink = CaptureSink(output_path, allowed_root=allowed_root)
    observer = RequestObserver(sink)
    observer.install()
    _GLOBAL_OBSERVER = observer
    if "observer" in sys.modules:
        sys.modules["observer"]._GLOBAL_OBSERVER = observer
    return observer


def main() -> None:
    """Observer entrypoint called via runtime_command and runpy.run_path."""
    args = sys.argv[1:]
    # If strictly help flag is passed, pass through directly to hermes CLI without observer output
    if args and set(args).issubset({"-h", "--help"}):
        from hermes_cli.main import main as hermes_main

        hermes_main()
        return

    output_env = os.environ.get("HERDR_OBSERVER_OUTPUT_PATH")
    if not output_env:
        raise RuntimeError("HERDR_OBSERVER_OUTPUT_PATH environment variable is required")

    # Real entry must be pinned installed root and approved existing pilot-artifacts root.
    # Production env must not silently grant writes elsewhere.
    env_repo = os.environ.get("HERMES_REPO_ROOT")
    if env_repo is not None and Path(env_repo).resolve() != PINNED_HERMES_ROOT.resolve():
        raise ValueError(f"Unapproved HERMES_REPO_ROOT override (must be {PINNED_HERMES_ROOT})")

    env_artifacts = os.environ.get("HERDR_PILOT_ARTIFACTS_ROOT")
    if (
        env_artifacts is not None
        and Path(env_artifacts).resolve() != APPROVED_PILOT_ARTIFACTS_ROOT.resolve()
    ):
        raise ValueError(
            "Unapproved HERDR_PILOT_ARTIFACTS_ROOT override "
            f"(must be {APPROVED_PILOT_ARTIFACTS_ROOT})"
        )

    repo_root = PINNED_HERMES_ROOT
    allowed_root = APPROVED_PILOT_ARTIFACTS_ROOT

    setup_observer(output_env, repo_root=repo_root, allowed_root=allowed_root, verify_pins=True)

    # Launch standard Hermes CLI with remaining arguments
    from hermes_cli.main import main as hermes_main

    hermes_main()


if __name__ == "__main__":
    main()
