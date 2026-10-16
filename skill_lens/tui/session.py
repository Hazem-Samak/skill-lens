"""Textual-free session controller for Skill Lens 0.2 full-screen TUI.

Specification reference: FULL_SCREEN_TUI.md §21.7.
Implements the entire internal controller state machine and transitions
independently of Textual, including generation tracking, monotonic request
allocation, report caching, atomic publication, worker cancellation events,
and sticky internal-fault handling.
"""

from __future__ import annotations

import threading
import traceback
from dataclasses import dataclass
from typing import Literal

from skill_lens.core.cancellation import CaptureCancelled
from skill_lens.core.discovery import canonical_key
from skill_lens.core.exitcodes import ExitCode
from skill_lens.core.hasher import IncompleteTreeError
from skill_lens.core.snapshot import SnapshotChanged, SnapshotTooLarge
from skill_lens.core.snapshot_models import SessionSnapshot
from skill_lens.models.compare import CompareReport
from skill_lens.models.diff import DiffReport
from skill_lens.models.resolution import ResolutionReport

ViewName = Literal["why", "diff", "compare"]
ReportValue = ResolutionReport | DiffReport | CompareReport


@dataclass(frozen=True, slots=True)
class ViewRequest:
    """A single view report computation request."""

    generation: int
    request_id: int
    view: ViewName
    arguments: tuple[str, ...]


class SessionController:
    """State machine controller governing session lifecycle and report cache.

    Owns published snapshot state, generation monotonicity, worker cancellation
    events, report requests and cache invalidation, and sticky failure tracking.
    This class is completely independent of Textual and operates strictly on
    the UI thread (all background worker handoffs are marshaled before calling
    controller transition methods).
    """

    def __init__(self) -> None:
        self.current: SessionSnapshot | None = None
        self.next_generation: int = 1
        self.pending_generation: int | None = None
        self.next_request_id: int = 1
        self.active_requests: dict[ViewName, ViewRequest] = {}
        self.cache: dict[tuple[int, ViewName, tuple[str, ...]], ReportValue] = {}
        self.selected_key: str | None = None
        self.failed: bool = False
        self.closed: bool = False

        self.retry_message: str | None = None
        self.refusal_message: str | None = None
        self.last_error_details: str | None = None

        self._capture_events: dict[int, threading.Event] = {}
        self._report_events: dict[int, threading.Event] = {}

    @property
    def is_closed(self) -> bool:
        """Return True if the controller has been closed."""
        return self.closed

    @property
    def is_failed(self) -> bool:
        """Return True if an accepted unexpected internal fault occurred."""
        return self.failed

    @property
    def status(self) -> str:
        """Return a human-readable controller status token."""
        if self.refusal_message is not None:
            return "refused"
        if self.retry_message is not None:
            return "retry"
        if self.failed:
            return "error"
        if self.pending_generation is not None:
            return "loading"
        if self.current is not None:
            return "ready"
        return "idle"

    def request_refresh(self) -> tuple[int, threading.Event] | None:
        """Allocate a new generation for capture and return its ID and cancellation event.

        Supersedes any prior pending capture generation by setting its event.
        Returns None if closed.
        """
        if self.closed:
            return None

        gen = self.next_generation
        self.next_generation += 1

        # Supersede prior pending capture(s)
        if self.pending_generation is not None:
            prior_event = self._capture_events.pop(self.pending_generation, None)
            if prior_event is not None:
                prior_event.set()

        event = threading.Event()
        self._capture_events[gen] = event
        self.pending_generation = gen
        self.retry_message = None
        self.refusal_message = None
        return gen, event

    def accept_capture(self, snapshot: SessionSnapshot, generation: int) -> bool:
        """Atomically publish a completed snapshot.

        Must match pending generation and the returned snapshot's generation.
        Clears report cache, cancels active view requests, preserves selected
        canonical key if still present (or chooses first entry/None).
        Returns True if published, False if rejected as stale or closed.
        """
        if self.closed:
            return False
        if (
            snapshot is None
            or self.pending_generation != generation
            or snapshot.generation != generation
        ):
            return False

        self.pending_generation = None
        self.current = snapshot
        self.retry_message = None
        self.refusal_message = None

        # Clean up capture event
        self._capture_events.pop(generation, None)

        # Invalidate/cancel active report requests and clear cache
        for event in list(self._report_events.values()):
            event.set()
        self._report_events.clear()
        self.active_requests.clear()
        self.cache.clear()

        # Preserve selected key if still exists; otherwise pick first canonical entry or None
        available_keys = {canonical_key(e) for e in snapshot.index.entries}
        if self.selected_key is not None and self.selected_key in available_keys:
            pass
        elif snapshot.index.entries:
            self.selected_key = canonical_key(snapshot.index.entries[0])
        else:
            self.selected_key = None

        return True

    def accept_capture_error(self, generation: int, error: Exception) -> bool:
        """Accept an error from a capture worker.

        Rejects stale errors before affecting any state.
        A size refusal (``SnapshotTooLarge``) sets a dedicated refusal message and
        never gains retry guidance, because retrying an unchanged oversized home
        cannot help.
        Expected SnapshotChanged and IncompleteTreeError display retry message
        without setting failed.
        CaptureCancelled is quiet.
        Unexpected errors keep previous usable data, set sticky failed=True, and
        keep traceback details in memory only.
        Returns True if accepted, False if rejected as stale or closed.
        """
        if self.closed:
            return False
        if self.pending_generation != generation:
            return False

        self.pending_generation = None
        self._capture_events.pop(generation, None)

        if isinstance(error, SnapshotTooLarge):
            # Permanent for this home: show the reason, never "press r to retry".
            self.refusal_message = str(error)
            self.retry_message = None
            return True
        if isinstance(error, (SnapshotChanged, IncompleteTreeError)):
            msg = str(error)
            if "retry" not in msg.lower():
                msg = f"{msg}. Press r to retry."
            self.retry_message = msg
            return True
        if isinstance(error, CaptureCancelled):
            return True

        # Unexpected error: retain data, set sticky failed=True, record details in memory
        self.failed = True
        self.last_error_details = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        self.retry_message = None
        return True

    def request_view(
        self, view: ViewName, arguments: tuple[str, ...]
    ) -> tuple[ViewRequest | None, threading.Event | None, ReportValue | None]:
        """Request a report value for a specific view and arguments.

        Always invalidates and cancels any prior active request for this view
        (even on cache hit) so that switching arguments immediately cancels
        in-flight work and rejects late results or errors.
        Returns (None, None, cached_value) on cache hit.
        Returns (request, event, None) on cache miss if open and current snapshot exists.
        Returns (None, None, None) if closed or current is None.
        """
        if self.closed or self.current is None:
            return None, None, None

        # Always cancel any prior in-flight request for this view
        self.invalidate_view(view)

        cache_key = (self.current.generation, view, arguments)
        if cache_key in self.cache:
            return None, None, self.cache[cache_key]

        req_id = self.next_request_id
        self.next_request_id += 1

        event = threading.Event()
        self._report_events[req_id] = event

        req = ViewRequest(
            generation=self.current.generation,
            request_id=req_id,
            view=view,
            arguments=arguments,
        )
        self.active_requests[view] = req
        return req, event, None

    def accept_view_result(
        self,
        view: ViewName,
        request_id: int,
        generation: int,
        arguments: tuple[str, ...],
        result: ReportValue,
    ) -> bool:
        """Accept a completed view report from a worker.

        Rejects stale results that do not match current generation, active
        request ID, view, or arguments.
        Returns True if accepted and cached, False otherwise.
        """
        if self.closed:
            return False
        if self.current is None or self.current.generation != generation:
            return False

        active = self.active_requests.get(view)
        if active is None:
            return False
        if (
            active.request_id != request_id
            or active.generation != generation
            or active.arguments != arguments
        ):
            return False

        self.active_requests.pop(view, None)
        self._report_events.pop(request_id, None)

        self.cache[(generation, view, arguments)] = result
        return True

    def accept_view_error(
        self,
        view: ViewName,
        request_id: int,
        generation: int,
        arguments: tuple[str, ...],
        error: Exception,
    ) -> bool:
        """Accept an error from a view report worker.

        Rejects stale errors that do not match current generation, active
        request ID, view, or arguments.
        Sets sticky failed=True on unexpected errors without destroying usable data.
        Returns True if accepted, False if rejected as stale or closed.
        """
        if self.closed:
            return False
        if self.current is None or self.current.generation != generation:
            return False

        active = self.active_requests.get(view)
        if active is None:
            return False
        if (
            active.request_id != request_id
            or active.generation != generation
            or active.arguments != arguments
        ):
            return False

        self.active_requests.pop(view, None)
        self._report_events.pop(request_id, None)

        if isinstance(error, CaptureCancelled):
            return True

        self.failed = True
        self.last_error_details = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        self.retry_message = None
        return True

    def invalidate_view(self, view: ViewName) -> None:
        """Invalidate and cancel any active background request for the given view."""
        active = self.active_requests.pop(view, None)
        if active is not None:
            event = self._report_events.pop(active.request_id, None)
            if event is not None:
                event.set()

    def set_selected_key(self, key: str | None) -> None:
        """Update selected canonical key.

        Changing selection invalidates associated requests (why and diff).
        """
        if self.selected_key != key:
            self.selected_key = key
            self.invalidate_view("why")
            self.invalidate_view("diff")

    def get_cached_report(self, view: ViewName, arguments: tuple[str, ...]) -> ReportValue | None:
        """Retrieve cached report if available for the current generation."""
        if self.current is None:
            return None
        return self.cache.get((self.current.generation, view, arguments))

    def close(self) -> int:
        """Mark controller closed, cancel all worker events, and return exit code.

        Returns ExitCode.INTERNAL (3) if failed, otherwise ExitCode.OK (0).
        """
        if self.closed:
            return int(ExitCode.INTERNAL) if self.failed else int(ExitCode.OK)

        self.closed = True

        for event in self._capture_events.values():
            event.set()
        self._capture_events.clear()

        for event in self._report_events.values():
            event.set()
        self._report_events.clear()

        self.pending_generation = None
        self.active_requests.clear()

        return int(ExitCode.INTERNAL) if self.failed else int(ExitCode.OK)


__all__ = [
    "ReportValue",
    "SessionController",
    "ViewName",
    "ViewRequest",
]
