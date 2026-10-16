"""Deterministic unit tests for SessionController (Assignment U2).

Specification reference: FULL_SCREEN_TUI.md §21.7.
Covers all required transition tests:
- Refresh 3 before 2 (out-of-order arrival and rejection of stale capture)
- Report 2 before 1 (out-of-order arrival and rejection of stale report)
- Selection and agent changes invalidating active requests
- Leaving/returning to view invalidating requests and rejecting late results
- Cache separation across generations and views, and cache invalidation on publication
- Generation mismatch rejection
- Newest failure with and without an existing snapshot
- Expected consistency error (SnapshotChanged) exposing retry message without failed flag
- Silent cancellation (CaptureCancelled) without failed flag
- Superseded exceptions rejected without altering controller state
- Sticky failure behavior (exit 3)
- Quit before completion setting all events and invalidating requests
- Atomic single-transition publication
- Monotonic allocation of generation and request IDs
- Invalidation on switching to cached arguments (rejecting both late success and late error)
"""

from __future__ import annotations

from pathlib import Path

from skill_lens.core.cancellation import CaptureCancelled
from skill_lens.core.discovery import (
    CanonicalResult,
    CanonicalStatus,
    DiscoveredEntry,
    RootHit,
)
from skill_lens.core.exitcodes import ExitCode
from skill_lens.core.scanner import ScanReport, ScanSummary
from skill_lens.core.snapshot import SnapshotChanged, SnapshotTooLarge
from skill_lens.core.snapshot_models import FrozenDiscoveryIndex, SessionSnapshot
from skill_lens.models.compare import CompareReport
from skill_lens.models.diff import DiffReport
from skill_lens.models.doctor import DoctorReport
from skill_lens.models.enums import (
    Collision,
    Evidence,
    HeadlineState,
    ParseStatus,
    Scope,
    Visibility,
)
from skill_lens.models.installation import SkillInstallation
from skill_lens.models.resolution import CandidateResolution, ResolutionReport
from skill_lens.registry.loader import AgentDefinition
from skill_lens.tui.session import SessionController


def _make_dummy_snapshot(
    generation: int,
    *,
    canonical_keys: tuple[str, ...] = ("skill-a", "skill-b"),
) -> SessionSnapshot:
    """Build a synthetic in-memory SessionSnapshot with zero disk access."""
    entries: list[DiscoveredEntry] = []
    for key in canonical_keys:
        entries.append(
            DiscoveredEntry(
                entrypoint_path=f"/tmp/fake/{key}",
                name=key,
                is_file=False,
                is_symlink=False,
                canonical=CanonicalResult(
                    status=CanonicalStatus.OK,
                    entrypoint_path=f"/tmp/fake/{key}",
                    resolved_path=key,
                    is_symlink=False,
                ),
                parse=None,
                content_hash="sha256:dummy",
                hits=(
                    RootHit(
                        agent_id="claude",
                        root_id="claude_user",
                        rank=1,
                        rule_id="test",
                        evidence="documented",
                        scope=Scope.USER,
                    ),
                ),
            )
        )

    index = FrozenDiscoveryIndex(
        home="/tmp/fake",
        cwd="/tmp/fake",
        entries=tuple(entries),
        unreadable_roots=(),
    )
    scan = ScanReport(
        home="/tmp/fake",
        cwd="/tmp/fake",
        summary=ScanSummary(
            detected_agents=("claude",),
            user_skills=len(canonical_keys),
            project_skills=0,
            system_skills=0,
            plugin_skills=0,
            canonical_skill_count=len(canonical_keys),
            symlink_entrypoints=0,
        ),
        skills=(),
        unreadable=(),
    )
    doctor = DoctorReport(home="/tmp/fake", cwd="/tmp/fake", findings=())

    return SessionSnapshot(
        generation=generation,
        home=Path("/tmp/fake"),
        cwd=Path("/tmp/fake"),
        registry=(
            AgentDefinition(
                id="claude",
                name="Claude",
                identity_source="frontmatter_name",
                collision_policy="Inferred",
                policy_evidence=Evidence.DOCUMENTED,
                coexist_policy="ambiguous",
                walk_boundary="git_root",
                unsearched_rule_id="none",
            ),
        ),
        index=index,
        files={},
        config_inputs={},
        disabled_overrides={},
        display_paths={},
        same_locations=frozenset(),
        scan=scan,
        doctor=doctor,
    )


def _make_dummy_why_report(skill: str, agent: str) -> ResolutionReport:
    inst = SkillInstallation(
        name=skill,
        entrypoint_path=f"/tmp/fake/{skill}",
        canonical_path=f"/tmp/fake/{skill}",
        scope=Scope.USER,
        parse_status=ParseStatus.VALID,
    )
    cand = CandidateResolution(
        state=HeadlineState.ACTIVE,
        visibility=Visibility.ACTIVE_ROOT,
        collision=Collision.WINNING_ENTRY,
        rule_id="test_rule",
        evidence=Evidence.DOCUMENTED,
        reason="test reason",
        rank=1,
        installation=inst,
    )
    return ResolutionReport(
        skill_name=skill,
        agent=agent,
        agent_name="Claude",
        cwd="/tmp/fake",
        collision_policy="Inferred",
        policy_evidence=Evidence.DOCUMENTED,
        headline=HeadlineState.ACTIVE,
        candidates=(cand,),
        notes=(),
        found=True,
    )


def _make_dummy_diff_report(skill: str) -> DiffReport:
    return DiffReport(
        skill_name=skill,
        home="/tmp/fake",
        cwd="/tmp/fake",
        found=True,
    )


def _make_dummy_compare_report(a: str, b: str) -> CompareReport:
    return CompareReport(
        agent_a=a,
        agent_b=b,
        agent_a_name="Agent A",
        agent_b_name="Agent B",
        home="/tmp/fake",
        cwd="/tmp/fake",
        entries=(),
        notes=(),
    )


# ---------------------------------------------------------------------------
# Transition Tests
# ---------------------------------------------------------------------------


def test_initial_controller_state() -> None:
    ctrl = SessionController()
    assert ctrl.current is None
    assert ctrl.next_generation == 1
    assert ctrl.pending_generation is None
    assert ctrl.next_request_id == 1
    assert ctrl.active_requests == {}
    assert ctrl.cache == {}
    assert ctrl.selected_key is None
    assert not ctrl.is_failed
    assert not ctrl.is_closed
    assert ctrl.status == "idle"


def test_monotonic_generation_allocation() -> None:
    ctrl = SessionController()
    req1 = ctrl.request_refresh()
    assert req1 is not None
    gen1, ev1 = req1
    assert gen1 == 1
    assert ctrl.pending_generation == 1
    assert not ev1.is_set()

    # Second refresh supersedes first
    req2 = ctrl.request_refresh()
    assert req2 is not None
    gen2, ev2 = req2
    assert gen2 == 2
    assert ctrl.pending_generation == 2
    assert ev1.is_set()  # Prior event superseded
    assert not ev2.is_set()


def test_refresh_3_before_2_out_of_order_arrival() -> None:
    """If refresh 3 completes before refresh 2, refresh 2 is rejected as stale."""
    ctrl = SessionController()
    req1 = ctrl.request_refresh()
    assert req1 is not None
    gen1, _ = req1

    req2 = ctrl.request_refresh()
    assert req2 is not None
    gen2, _ = req2

    req3 = ctrl.request_refresh()
    assert req3 is not None
    gen3, _ = req3

    assert ctrl.pending_generation == 3

    snap3 = _make_dummy_snapshot(gen3, canonical_keys=("skill-3",))
    assert ctrl.accept_capture(snap3, gen3) is True
    assert ctrl.current is snap3
    assert ctrl.selected_key == "skill-3"
    assert ctrl.pending_generation is None

    # Late arrival of generation 2
    snap2 = _make_dummy_snapshot(gen2, canonical_keys=("skill-2",))
    assert ctrl.accept_capture(snap2, gen2) is False
    assert ctrl.current is snap3  # Unchanged!
    assert ctrl.selected_key == "skill-3"

    # Late arrival of generation 1
    snap1 = _make_dummy_snapshot(gen1, canonical_keys=("skill-1",))
    assert ctrl.accept_capture(snap1, gen1) is False
    assert ctrl.current is snap3


def test_atomic_publication_swaps_snapshot_and_clears_cache_and_requests() -> None:
    """Publication swaps current, cancels active requests, clears cache in one transition."""
    ctrl = SessionController()
    gen1, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap1 = _make_dummy_snapshot(gen1, canonical_keys=("skill-a", "skill-b"))
    assert ctrl.accept_capture(snap1, gen1) is True
    ctrl.set_selected_key("skill-b")

    # Issue a report request and populate cache
    req, ev, _ = ctrl.request_view("why", ("skill-b", "claude"))
    assert req is not None
    assert ev is not None
    why_rep = _make_dummy_why_report("skill-b", "claude")
    ok = ctrl.accept_view_result("why", req.request_id, gen1, ("skill-b", "claude"), why_rep)
    assert ok is True
    assert len(ctrl.cache) == 1

    # Issue an active report request that hasn't completed yet
    req2, ev2, _ = ctrl.request_view("diff", ("skill-b",))
    assert req2 is not None
    assert ev2 is not None
    assert not ev2.is_set()
    assert "diff" in ctrl.active_requests

    # Now refresh arrives with gen 2
    gen2, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap2 = _make_dummy_snapshot(gen2, canonical_keys=("skill-b", "skill-c"))
    assert ctrl.accept_capture(snap2, gen2) is True

    # Check atomic update
    assert ctrl.current is snap2
    assert ctrl.selected_key == "skill-b"  # Preserved because skill-b exists in snap2
    assert len(ctrl.cache) == 0  # Cache cleared
    assert len(ctrl.active_requests) == 0  # Active requests cleared
    assert ev2.is_set()  # Superseded request cancelled


def test_selection_preserved_or_first_canonical_or_none() -> None:
    ctrl = SessionController()
    gen1, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap1 = _make_dummy_snapshot(gen1, canonical_keys=("x", "y"))
    ctrl.accept_capture(snap1, gen1)
    ctrl.set_selected_key("y")
    assert ctrl.selected_key == "y"

    # Snap 2 still has y -> preserved
    gen2, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap2 = _make_dummy_snapshot(gen2, canonical_keys=("z", "y"))
    ctrl.accept_capture(snap2, gen2)
    assert ctrl.selected_key == "y"

    # Snap 3 does not have y -> picks first row ("z")
    gen3, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap3 = _make_dummy_snapshot(gen3, canonical_keys=("z", "w"))
    ctrl.accept_capture(snap3, gen3)
    assert ctrl.selected_key == "z"

    # Snap 4 is empty -> picks None
    gen4, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap4 = _make_dummy_snapshot(gen4, canonical_keys=())
    ctrl.accept_capture(snap4, gen4)
    assert ctrl.selected_key is None


def test_generation_mismatch_rejection() -> None:
    ctrl = SessionController()
    gen, _ = ctrl.request_refresh()  # type: ignore[misc]
    # Snapshot generation doesn't match passed generation
    snap = _make_dummy_snapshot(gen + 99)
    assert ctrl.accept_capture(snap, gen) is False
    assert ctrl.current is None
    assert ctrl.pending_generation == gen


def test_report_2_before_1_out_of_order_arrival() -> None:
    """When a view request is superseded, out of order result arrival is rejected."""
    ctrl = SessionController()
    gen, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap = _make_dummy_snapshot(gen)
    ctrl.accept_capture(snap, gen)

    # First why request
    req1, ev1, _ = ctrl.request_view("why", ("skill-a", "claude"))
    assert req1 is not None
    assert req1.request_id == 1

    # Second why request supersedes first
    req2, ev2, _ = ctrl.request_view("why", ("skill-a", "codex"))
    assert req2 is not None
    assert req2.request_id == 2
    assert ev1.is_set()  # Prior request cancelled

    why2 = _make_dummy_why_report("skill-a", "codex")
    assert ctrl.accept_view_result("why", req2.request_id, gen, ("skill-a", "codex"), why2) is True
    assert ctrl.get_cached_report("why", ("skill-a", "codex")) is why2

    # Late arrival of request 1
    why1 = _make_dummy_why_report("skill-a", "claude")
    ok1 = ctrl.accept_view_result("why", req1.request_id, gen, ("skill-a", "claude"), why1)
    assert ok1 is False
    assert ctrl.get_cached_report("why", ("skill-a", "claude")) is None


def test_switching_to_cached_args_invalidates_prior_in_flight_request() -> None:
    """When Why args A is cached, starting uncached Why B, then requesting cached A:
    B's in-flight request is immediately invalidated and its event is set.
    Late completion of B (both late success and late error) is rejected.
    """
    ctrl = SessionController()
    gen, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap = _make_dummy_snapshot(gen)
    ctrl.accept_capture(snap, gen)

    # 1. Populate cache for args A ("skill-a", "claude")
    req_a, _, _ = ctrl.request_view("why", ("skill-a", "claude"))
    assert req_a is not None
    why_a = _make_dummy_why_report("skill-a", "claude")
    ctrl.accept_view_result("why", req_a.request_id, gen, ("skill-a", "claude"), why_a)
    assert ctrl.get_cached_report("why", ("skill-a", "claude")) is why_a

    # 2. Start uncached request for args B ("skill-a", "codex")
    req_b, ev_b, cached_b = ctrl.request_view("why", ("skill-a", "codex"))
    assert req_b is not None
    assert ev_b is not None
    assert cached_b is None
    assert not ev_b.is_set()
    assert ctrl.active_requests.get("why") == req_b

    # 3. Now request cached args A again
    req_a2, ev_a2, cached_a = ctrl.request_view("why", ("skill-a", "claude"))
    assert req_a2 is None
    assert ev_a2 is None
    assert cached_a is why_a

    # B's request MUST have been invalidated!
    assert ev_b.is_set(), "B's cancellation event must be set when switching to cached args A"
    assert ctrl.active_requests.get("why") is None

    # Late success for B must be rejected
    why_b = _make_dummy_why_report("skill-a", "codex")
    ok_b = ctrl.accept_view_result("why", req_b.request_id, gen, ("skill-a", "codex"), why_b)
    assert ok_b is False
    assert ctrl.get_cached_report("why", ("skill-a", "codex")) is None

    # Now verify late error behavior as well:
    # Start uncached request for C ("skill-b", "codex")
    req_c, ev_c, _ = ctrl.request_view("why", ("skill-b", "codex"))
    assert req_c is not None
    assert ev_c is not None
    assert not ev_c.is_set()

    # Switch back to cached args A
    _, _, cached_a3 = ctrl.request_view("why", ("skill-a", "claude"))
    assert cached_a3 is why_a
    assert ev_c.is_set(), "C's event must be set on switch to cached A"
    assert ctrl.active_requests.get("why") is None

    # Late error for C must be rejected without marking failed
    err_c = RuntimeError("late C error")
    ok_c = ctrl.accept_view_error("why", req_c.request_id, gen, ("skill-b", "codex"), err_c)
    assert ok_c is False
    assert not ctrl.is_failed
    assert ctrl.last_error_details is None


def test_selection_changes_invalidate_associated_requests() -> None:
    ctrl = SessionController()
    gen, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap = _make_dummy_snapshot(gen)
    ctrl.accept_capture(snap, gen)

    req_why, ev_why, _ = ctrl.request_view("why", ("skill-a", "claude"))
    req_diff, ev_diff, _ = ctrl.request_view("diff", ("skill-a",))
    assert not ev_why.is_set()
    assert not ev_diff.is_set()

    # Changing selection invalidates why and diff requests
    ctrl.set_selected_key("skill-b")
    assert ev_why.is_set()
    assert ev_diff.is_set()
    assert "why" not in ctrl.active_requests
    assert "diff" not in ctrl.active_requests


def test_leaving_view_invalidates_request_and_rejects_late_result() -> None:
    ctrl = SessionController()
    gen, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap = _make_dummy_snapshot(gen)
    ctrl.accept_capture(snap, gen)

    req, ev, _ = ctrl.request_view("diff", ("skill-a",))
    assert req is not None
    assert not ev.is_set()

    # Leaving view
    ctrl.invalidate_view("diff")
    assert ev.is_set()
    assert "diff" not in ctrl.active_requests

    # Late result arrival
    diff_rep = _make_dummy_diff_report("skill-a")
    assert ctrl.accept_view_result("diff", req.request_id, gen, ("skill-a",), diff_rep) is False
    assert ctrl.get_cached_report("diff", ("skill-a",)) is None


def test_cache_separation_across_generations_and_views() -> None:
    ctrl = SessionController()
    gen1, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap1 = _make_dummy_snapshot(gen1)
    ctrl.accept_capture(snap1, gen1)

    req1, _, _ = ctrl.request_view("diff", ("skill-a",))
    assert req1 is not None
    diff1 = _make_dummy_diff_report("skill-a")
    ctrl.accept_view_result("diff", req1.request_id, gen1, ("skill-a",), diff1)
    assert ctrl.get_cached_report("diff", ("skill-a",)) is diff1

    # Requesting same view and arguments returns cached report without new request
    req_cached, ev_cached, val_cached = ctrl.request_view("diff", ("skill-a",))
    assert req_cached is None
    assert ev_cached is None
    assert val_cached is diff1

    # Gen 2 invalidates cache
    gen2, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap2 = _make_dummy_snapshot(gen2)
    ctrl.accept_capture(snap2, gen2)
    assert ctrl.get_cached_report("diff", ("skill-a",)) is None


def test_expected_consistency_error_snapshot_changed() -> None:
    """SnapshotChanged retains data, exposes retry message, does NOT set failed."""
    ctrl = SessionController()
    gen1, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap1 = _make_dummy_snapshot(gen1)
    ctrl.accept_capture(snap1, gen1)

    gen2, _ = ctrl.request_refresh()  # type: ignore[misc]
    err = SnapshotChanged()
    assert ctrl.accept_capture_error(gen2, err) is True

    assert ctrl.current is snap1  # Retains previous data!
    assert not ctrl.is_failed  # Does not set failed!
    assert ctrl.retry_message == "Files changed while scanning. Press r to retry."
    assert ctrl.status == "retry"


def test_silent_cancellation_capture_cancelled() -> None:
    """CaptureCancelled is quiet, keeps previous data, does not set failed or retry message."""
    ctrl = SessionController()
    gen1, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap1 = _make_dummy_snapshot(gen1)
    ctrl.accept_capture(snap1, gen1)

    gen2, _ = ctrl.request_refresh()  # type: ignore[misc]
    assert ctrl.accept_capture_error(gen2, CaptureCancelled()) is True
    assert ctrl.current is snap1
    assert not ctrl.is_failed
    assert ctrl.retry_message is None
    assert ctrl.status == "ready"


def test_newest_failure_without_old_snapshot() -> None:
    """Unexpected failure on initial capture sets sticky failed, current is None."""
    ctrl = SessionController()
    gen, _ = ctrl.request_refresh()  # type: ignore[misc]
    err = RuntimeError("Disk IO fault")
    assert ctrl.accept_capture_error(gen, err) is True
    assert ctrl.current is None
    assert ctrl.is_failed
    assert "Disk IO fault" in (ctrl.last_error_details or "")
    assert ctrl.status == "error"


def test_newest_failure_with_old_snapshot() -> None:
    """Unexpected failure during refresh keeps old snapshot and sets sticky failed."""
    ctrl = SessionController()
    gen1, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap1 = _make_dummy_snapshot(gen1)
    ctrl.accept_capture(snap1, gen1)

    gen2, _ = ctrl.request_refresh()  # type: ignore[misc]
    err = RuntimeError("Unexpected permission fault")
    assert ctrl.accept_capture_error(gen2, err) is True
    assert ctrl.current is snap1  # Retained!
    assert ctrl.is_failed
    assert "Unexpected permission fault" in (ctrl.last_error_details or "")
    assert ctrl.status == "error"


def test_superseded_exceptions_rejected() -> None:
    """Stale exceptions from superseded generations do not alter controller state."""
    ctrl = SessionController()
    gen1, _ = ctrl.request_refresh()  # type: ignore[misc]
    gen2, _ = ctrl.request_refresh()  # type: ignore[misc]

    # Error from gen1 arrives while gen2 is pending
    stale_err = RuntimeError("stale gen 1 fault")
    assert ctrl.accept_capture_error(gen1, stale_err) is False
    assert not ctrl.is_failed
    assert ctrl.last_error_details is None
    assert ctrl.pending_generation == gen2


def test_view_error_acceptance_and_rejection() -> None:
    ctrl = SessionController()
    gen, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap = _make_dummy_snapshot(gen)
    ctrl.accept_capture(snap, gen)

    req1, _, _ = ctrl.request_view("compare", ("claude", "codex"))
    assert req1 is not None

    req2, _, _ = ctrl.request_view("compare", ("claude", "grok"))
    assert req2 is not None

    # Stale error from req1
    err1 = RuntimeError("old err")
    ok1 = ctrl.accept_view_error("compare", req1.request_id, gen, ("claude", "codex"), err1)
    assert ok1 is False
    assert not ctrl.is_failed

    # Active error from req2
    err2 = RuntimeError("active err")
    ok2 = ctrl.accept_view_error("compare", req2.request_id, gen, ("claude", "grok"), err2)
    assert ok2 is True
    assert ctrl.is_failed
    assert "active err" in (ctrl.last_error_details or "")


def test_sticky_failure_persists_across_subsequent_events() -> None:
    """Once failed=True, subsequent actions never clear failed=True."""
    ctrl = SessionController()
    gen1, _ = ctrl.request_refresh()  # type: ignore[misc]
    ctrl.accept_capture_error(gen1, RuntimeError("fatal"))
    assert ctrl.is_failed

    # Even if next capture succeeds
    gen2, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap2 = _make_dummy_snapshot(gen2)
    ctrl.accept_capture(snap2, gen2)
    assert ctrl.is_failed  # Still failed!

    # Even if next capture has SnapshotChanged
    gen3, _ = ctrl.request_refresh()  # type: ignore[misc]
    ctrl.accept_capture_error(gen3, SnapshotChanged())
    assert ctrl.is_failed  # Still failed!

    # Close returns exit code 3
    assert ctrl.close() == int(ExitCode.INTERNAL)


def test_quit_before_completion_cancels_workers_and_sets_closed() -> None:
    ctrl = SessionController()
    gen, ev_cap = ctrl.request_refresh()  # type: ignore[misc]
    snap = _make_dummy_snapshot(gen)
    ctrl.accept_capture(snap, gen)

    req, ev_rep, _ = ctrl.request_view("why", ("skill-a", "claude"))
    gen2, ev_cap2 = ctrl.request_refresh()  # type: ignore[misc]

    assert not ev_rep.is_set()
    assert not ev_cap2.is_set()

    code = ctrl.close()
    assert code == int(ExitCode.OK)
    assert ctrl.is_closed
    assert ev_rep.is_set()
    assert ev_cap2.is_set()
    assert ctrl.pending_generation is None
    assert len(ctrl.active_requests) == 0

    # Callbacks after close are ignored
    assert ctrl.accept_capture(snap, gen2) is False
    assert ctrl.accept_capture_error(gen2, RuntimeError("late")) is False
    assert ctrl.request_refresh() is None
    assert ctrl.request_view("why", ("skill-a", "claude")) == (None, None, None)


def test_unexpected_fault_then_snapshot_changed_then_view_fault_sequence() -> None:
    """§21.7 display precedence: unexpected fault -> SnapshotChanged -> later view fault.

    1. Initial snapshot published (gen1).
    2. gen2 fails with unexpected RuntimeError -> sets sticky failed=True, status='error',
       retaining gen1 snapshot.
    3. gen3 fails with expected SnapshotChanged -> sets retry_message, status becomes 'retry'
       (displaying expected retry message while preserving sticky failed=True and exit 3).
    4. Stale errors from superseded gen or non-matching view request have zero effect.
    5. Active view request on retained snapshot fails with unexpected RuntimeError ->
       clears retry_message, updates last_error_details with view fault, status becomes 'error',
       and sticky failed=True exit 3 is preserved.
    """
    ctrl = SessionController()
    gen1, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap1 = _make_dummy_snapshot(gen1)
    assert ctrl.accept_capture(snap1, gen1) is True
    assert ctrl.status == "ready"
    assert not ctrl.is_failed

    # Step 2: gen2 fails with unexpected RuntimeError
    gen2, _ = ctrl.request_refresh()  # type: ignore[misc]
    assert ctrl.status == "loading"
    assert ctrl.accept_capture_error(gen2, RuntimeError("scan disk fault")) is True
    assert ctrl.current is snap1  # Retained
    assert ctrl.is_failed is True
    assert ctrl.status == "error"
    assert "scan disk fault" in (ctrl.last_error_details or "")
    assert ctrl.retry_message is None

    # Step 3: gen3 fails with SnapshotChanged
    gen3, _ = ctrl.request_refresh()  # type: ignore[misc]
    assert ctrl.status == "error"  # Accepted unexpected fault outranks pending loading!
    retry_msg = "Files changed while scanning. Press r to retry."
    assert ctrl.accept_capture_error(gen3, SnapshotChanged(retry_msg)) is True
    assert ctrl.current is snap1  # Retained
    assert ctrl.is_failed is True  # Sticky failed preserved!
    assert ctrl.retry_message == retry_msg
    assert ctrl.status == "retry"  # Display shows retry rather than error!

    # Step 4: Stale errors have zero effect
    assert ctrl.accept_capture_error(gen2, RuntimeError("stale capture")) is False
    assert ctrl.accept_capture_error(999, RuntimeError("nonexistent gen")) is False
    assert (
        ctrl.accept_view_error("why", 999, gen1, ("skill-a", "claude"), RuntimeError("stale view"))
        is False
    )
    assert ctrl.status == "retry"
    assert ctrl.retry_message == retry_msg
    assert ctrl.is_failed is True

    # Step 5: Active view request fails with unexpected RuntimeError
    req, _, _ = ctrl.request_view("why", ("skill-a", "claude"))
    assert req is not None
    assert (
        ctrl.accept_view_error(
            "why",
            req.request_id,
            req.generation,
            req.arguments,
            RuntimeError("view database fault"),
        )
        is True
    )
    assert ctrl.retry_message is None  # Older retry indication cleared!
    assert ctrl.is_failed is True  # Sticky failed preserved!
    assert ctrl.status == "error"  # Status returns to error to show fault panel!
    assert "view database fault" in (ctrl.last_error_details or "")
    assert "scan disk fault" not in (ctrl.last_error_details or "")

    # Close returns exit code 3
    assert ctrl.close() == int(ExitCode.INTERNAL)


def test_report_error_during_refresh_regression() -> None:
    """§21.7 display precedence regression: capture1 accepted; start Why request1;
    start refresh2 (old snapshot/report remain usable by §21.7);
    accept request1 RuntimeError while current is still gen1.
    failed=True, pending_generation=2, and status MUST be 'error' (not 'loading')
    so that the accepted unexpected error panel is displayed rather than hidden.
    """
    ctrl = SessionController()
    gen1, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap1 = _make_dummy_snapshot(gen1)
    assert ctrl.accept_capture(snap1, gen1) is True
    assert ctrl.status == "ready"
    assert not ctrl.is_failed

    # Start Why request1 for active gen1
    req1, _, _ = ctrl.request_view("why", ("skill-a", "claude"))
    assert req1 is not None

    # Start refresh2 (pending_generation = 2; gen1 snapshot remains usable)
    gen2, _ = ctrl.request_refresh()  # type: ignore[misc]
    assert gen2 == 2
    assert ctrl.pending_generation == 2
    assert ctrl.status == "loading"

    # Accept request1 RuntimeError while current is still gen1 and refresh2 is pending
    view_err = RuntimeError("Disk fault during why calculation")
    assert (
        ctrl.accept_view_error("why", req1.request_id, req1.generation, req1.arguments, view_err)
        is True
    )
    assert ctrl.is_failed is True
    assert ctrl.pending_generation == 2
    # status MUST be 'error', outranking pending loading!
    assert ctrl.status == "error"
    assert "Disk fault during why calculation" in (ctrl.last_error_details or "")

    # Close returns exit code 3
    assert ctrl.close() == int(ExitCode.INTERNAL)


# --- R01 refusal budget ----------------------------------------------------


def test_size_refusal_sets_dedicated_refusal_message() -> None:
    """A budget refusal is reported as a refusal, never as a retryable change."""
    ctrl = SessionController()
    gen1, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap1 = _make_dummy_snapshot(gen1)
    ctrl.accept_capture(snap1, gen1)

    gen2, _ = ctrl.request_refresh()  # type: ignore[misc]
    err = SnapshotTooLarge(total_bytes=300 * 1024 * 1024, limit_bytes=256 * 1024 * 1024)
    assert ctrl.accept_capture_error(gen2, err) is True

    assert ctrl.current is snap1  # Previous generation is preserved!
    assert ctrl.is_failed is False  # A refusal is not an internal fault!
    assert ctrl.retry_message is None  # Never uses the retry surface!
    assert ctrl.refusal_message == str(err)
    assert ctrl.status == "refused"
    assert "Press r to retry" not in (ctrl.refusal_message or "")


def test_refusal_is_cleared_by_a_later_refresh() -> None:
    """A new refresh clears a standing refusal."""
    ctrl = SessionController()
    gen, _ = ctrl.request_refresh()  # type: ignore[misc]
    ctrl.accept_capture_error(gen, SnapshotTooLarge(total_bytes=2, limit_bytes=1))
    assert ctrl.status == "refused"

    ctrl.request_refresh()
    assert ctrl.refusal_message is None
    assert ctrl.status == "loading"


def test_refusal_is_cleared_by_a_successful_capture() -> None:
    """A successful capture supersedes a standing refusal."""
    ctrl = SessionController()
    gen1, _ = ctrl.request_refresh()  # type: ignore[misc]
    ctrl.accept_capture_error(gen1, SnapshotTooLarge(total_bytes=2, limit_bytes=1))

    gen2, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap2 = _make_dummy_snapshot(gen2)
    assert ctrl.accept_capture(snap2, gen2) is True
    assert ctrl.refusal_message is None
    assert ctrl.status == "ready"


def test_stale_refusal_is_rejected() -> None:
    """A refusal from a superseded generation must not affect state."""
    ctrl = SessionController()
    gen1, _ = ctrl.request_refresh()  # type: ignore[misc]
    gen2, _ = ctrl.request_refresh()  # type: ignore[misc]
    assert gen1 != gen2

    assert ctrl.accept_capture_error(gen1, SnapshotTooLarge(total_bytes=2, limit_bytes=1)) is False
    assert ctrl.refusal_message is None


def test_internal_fault_clears_a_standing_refusal() -> None:
    """An accepted internal fault must stay visible, not be masked by a refusal."""
    ctrl = SessionController()
    gen1, _ = ctrl.request_refresh()  # type: ignore[misc]
    snap1 = _make_dummy_snapshot(gen1)
    ctrl.accept_capture(snap1, gen1)

    gen2, _ = ctrl.request_refresh()  # type: ignore[misc]
    ctrl.accept_capture_error(gen2, SnapshotTooLarge(total_bytes=2, limit_bytes=1))
    assert ctrl.status == "refused"

    req, _event, _cached = ctrl.request_view("why", ("skill-a", "claude"))
    assert req is not None
    assert (
        ctrl.accept_view_error(
            "why", req.request_id, req.generation, req.arguments, RuntimeError("report fault")
        )
        is True
    )

    assert ctrl.is_failed is True
    assert ctrl.refusal_message is None
    assert ctrl.status == "error"
    assert "report fault" in (ctrl.last_error_details or "")
