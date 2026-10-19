#!/usr/bin/env python3
"""Reproducible U3 Home benchmark (FULL_SCREEN_TUI.md §22 U3).

Creates ``--skills`` standard-library synthetic skills in a temporary ``$HOME``
outside the checkout, mounts the real Textual Home screen, and drives it with
real Pilot key/input events.  Every run is *explicitly isolated*: the sandbox,
``HOME``/``XDG_CONFIG_HOME``, the capture/why wrappers and the discovery
directory guard are installed for that run only and restored on success or
failure, with a fail-closed assertion that absolute system roots such as
``/etc/codex`` can never be read.

Measured, from real accepted events rather than polling guesses:

* capture time (wrapped ``capture_session``)
* publication (accepted ``accept_capture``) to the instrumented Home rebuild
  that first carries every row, and separately to a benchmark-only
  post-refresh callback that runs after Textual has refreshed the screen (the
  honest "first usable list" boundary)
* full startup to both of those points
* a controlled injected rebuild delay, proving the usable interval is real
* arrow-key navigation, text-filter and agent-filter input-to-visible result
* the whole serial resolution queue divided by resolved rows, and a separate
  real per-cell update cost
* navigation/filter/quit responsiveness while 600 resolutions are active
* the number of Why worker calls versus the number of distinct lookup groups
* prompt quit latency while a capture worker is deliberately blocked

It also records an independent before/after byte + mode + symlink/inventory
manifest of the synthetic fixtures and fails if any fixture changed.

Writes a JSON receipt under ``docs/validation/u3/implementation/`` and prints
it.  No release threshold is asserted: the measured numbers and their
limitations are reported as-is.

Usage (from the repository root)::

    .venv/bin/python docs/validation/u3/benchmark_home.py --runs 3 --skills 600
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import os
import platform
import statistics
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from textual.widgets import DataTable, Input  # noqa: E402

import skill_lens.core.discovery as discovery  # noqa: E402
import skill_lens.tui.app as app_module  # noqa: E402
from skill_lens.core import paths  # noqa: E402
from skill_lens.tui.home import HomeScreen  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_skills(home: Path, count: int) -> None:
    """Materialize ``count`` minimal skills; all setup happens outside timing."""
    skills_root = home / ".claude" / "skills"
    xdg = home / ".config"
    xdg.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        name = f"skill-{index:04d}"
        directory = skills_root / name
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Benchmark {name}.\n---\n# Body\n{name}\n",
            encoding="utf-8",
        )


def _manifest(root: Path) -> dict[str, tuple[str, int, str]]:
    """Independent byte/mode/inventory snapshot of every fixture entry."""
    entries: dict[str, tuple[str, int, str]] = {}
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            entries[relative] = ("symlink", 0, os.readlink(path))
        elif path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            entries[relative] = (digest, path.stat().st_mode & 0o777, "")
        else:
            entries[relative] = ("dir", path.stat().st_mode & 0o777, "")
    return entries


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------


def _assert_fail_closed(home: Path) -> None:
    """Prove the run cannot read absolute system roots such as ``/etc/codex``."""
    assert paths.get_sandbox() is not None, "benchmark sandbox was not set"
    assert paths.home() == home, "paths.home() is not the synthetic sandbox"
    assert not discovery._absolute_roots_allowed(home), (
        "absolute system roots (e.g. /etc/codex) would be read live"
    )


@contextlib.contextmanager
def _isolated(home: Path) -> Iterator[None]:
    """Set sandbox/HOME/XDG for one run and restore the prior state either way."""
    prior_sandbox = paths.get_sandbox()
    prior_env = {name: os.environ.get(name) for name in ("HOME", "XDG_CONFIG_HOME")}
    paths.set_sandbox(home)
    os.environ["HOME"] = str(home)
    os.environ["XDG_CONFIG_HOME"] = str(home / ".config")
    try:
        _assert_fail_closed(home)
        yield
    finally:
        paths.set_sandbox(prior_sandbox)
        for name, value in prior_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _directory_guard(
    home: Path, original: Callable[..., list[tuple[Path, bool]]]
) -> Callable[..., list[tuple[Path, bool]]]:
    """Fail-closed wrapper: every concrete discovered directory stays in ``home``."""
    root = os.path.realpath(home)

    def guarded(
        home_arg: Path, cwd: Path, agent_root: Any, boundary: Any
    ) -> list[tuple[Path, bool]]:
        result = original(home_arg, cwd, agent_root, boundary)
        for path, _recursive in result:
            candidate = os.path.realpath(path)
            assert candidate == root or candidate.startswith(root + os.sep), (
                f"discovery escaped the synthetic home: {candidate}"
            )
        return result

    return guarded


# ---------------------------------------------------------------------------
# Instrumented app (no production hooks; benchmark-only subclasses)
# ---------------------------------------------------------------------------


class _BenchScreen(HomeScreen):
    """HomeScreen with timing-only overrides used exclusively by this harness."""

    _usable_scheduled = False

    def _rebuild_table(self) -> None:
        app = self.app
        marks = app.marks
        pending = marks["published"] is not None and marks["first_usable"] is None
        if pending and not app.delay_applied and app.rebuild_delay_ms:
            app.delay_applied = True
            time.sleep(app.rebuild_delay_ms / 1000.0)
        super()._rebuild_table()
        if pending:
            table = self.query_one("#skill-table", DataTable)
            if app.count and table.row_count >= app.count:
                if marks["rows_populated"] is None:
                    marks["rows_populated"] = time.perf_counter()
                if not self._usable_scheduled:
                    self._usable_scheduled = True
                    # Benchmark-only: Textual refreshes the screen after this
                    # rebuild; only then is the list actually laid out/painted
                    # and therefore usable.  No product hook is involved.
                    self.call_after_refresh(self._mark_first_usable)

    def _mark_first_usable(self) -> None:
        marks = self.app.marks
        if marks["first_usable"] is None:
            marks["first_usable"] = time.perf_counter()

    def _set_state_cell(self, row_key: str, value: str) -> None:
        started = time.perf_counter()
        super()._set_state_cell(row_key, value)
        if value:
            self.app.cell_ms.append((time.perf_counter() - started) * 1000.0)


class _BenchApp(app_module.SkillLensApp):
    """SkillLensApp carrying benchmark marks and the instrumented Home screen."""

    def __init__(
        self,
        *args: Any,
        count: int = 0,
        rebuild_delay_ms: float = 0.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.count = count
        self.rebuild_delay_ms = rebuild_delay_ms
        self.delay_applied = False
        self.cell_ms: list[float] = []
        self.marks: dict[str, float | None] = {
            "start": None,
            "published": None,
            "rows_populated": None,
            "first_usable": None,
        }

    def get_default_screen(self) -> Any:
        return _BenchScreen()


def _install_publication_mark(app: _BenchApp) -> None:
    """Record the instant ``accept_capture`` first returns True (pre-Home-sync)."""
    controller = app.controller
    original = controller.accept_capture

    def wrapped(snapshot: Any, generation: int) -> bool:
        accepted = original(snapshot, generation)
        if accepted and app.marks["published"] is None:
            app.marks["published"] = time.perf_counter()
        return accepted

    controller.accept_capture = wrapped  # type: ignore[method-assign]


# ---------------------------------------------------------------------------
# Measurement helpers
# ---------------------------------------------------------------------------


def _table(app: Any) -> DataTable:
    return app.query_one("#skill-table", DataTable)


def _state_values(app: Any) -> list[str]:
    table = _table(app)
    labels = [str(column.label) for column in table.columns.values()]
    if "State" not in labels:
        return []
    index = labels.index("State")
    return [str(table.get_row_at(row)[index]) for row in range(table.row_count)]


def _queue_settled(app: Any) -> bool:
    """True only when every group has a final result (no pending/loading)."""
    groups = app.screen._groups
    return bool(groups) and all(
        group.status in ("done", "unavailable") for group in groups.values()
    )


async def _wait_until(pilot: Any, predicate: Any, timeout: float = 60.0) -> float:
    """Wait for ``predicate`` and return the elapsed seconds."""
    deadline = time.monotonic() + timeout
    started = time.perf_counter()
    while time.monotonic() < deadline:
        if predicate():
            return time.perf_counter() - started
        await pilot.pause(0.002)
    raise AssertionError("benchmark wait timed out")


# ---------------------------------------------------------------------------
# One run
# ---------------------------------------------------------------------------


async def _run_once(
    home: Path,
    count: int,
    run_index: int,
    *,
    probe: bool = False,
    rebuild_delay_ms: float = 0.0,
) -> dict[str, Any]:
    original_capture = app_module.capture_session
    original_why = app_module.snapshot_why
    original_directories = discovery._directories_for_root
    capture_ms: list[float] = []

    def timed_capture(**kwargs: Any) -> Any:
        started = time.perf_counter()
        snapshot = original_capture(**kwargs)
        capture_ms.append((time.perf_counter() - started) * 1000.0)
        return snapshot

    app_module.capture_session = timed_capture
    discovery._directories_for_root = _directory_guard(home, original_directories)
    try:
        app = _BenchApp(
            home=home,
            cwd=home,
            count=count,
            rebuild_delay_ms=rebuild_delay_ms,
        )
        _install_publication_mark(app)
        app.marks["start"] = time.perf_counter()

        async with app.run_test(size=(120, 40)) as pilot:
            await _wait_until(
                pilot,
                lambda: app.marks["first_usable"] is not None,
                timeout=120.0,
            )
            table = _table(app)
            assert table.row_count == count, (table.row_count, count)
            assert table.cursor_row >= 0
            published = app.marks["published"]
            rows_populated = app.marks["rows_populated"]
            first_usable = app.marks["first_usable"]
            started_at = app.marks["start"]
            assert (
                published is not None
                and rows_populated is not None
                and first_usable is not None
                and started_at is not None
            )
            assert rows_populated <= first_usable
            publication_to_rows_ms = (rows_populated - published) * 1000.0
            publication_to_usable_ms = (first_usable - published) * 1000.0
            startup_to_rows_ms = (rows_populated - started_at) * 1000.0
            startup_to_usable_ms = (first_usable - started_at) * 1000.0

            if rebuild_delay_ms:
                # A controlled injected delay must appear in the usable interval.
                assert publication_to_usable_ms >= rebuild_delay_ms * 0.8, publication_to_usable_ms
                await pilot.press("q")
                return {
                    "run": run_index,
                    "kind": "injected-delay",
                    "rebuild_delay_ms": rebuild_delay_ms,
                    "publication_to_rows_populated_ms": publication_to_rows_ms,
                    "publication_to_first_usable_ms": publication_to_usable_ms,
                    "startup_to_first_usable_ms": startup_to_usable_ms,
                    "return_code": app.return_code,
                }

            if probe:
                return await _probe_active(pilot, app, table, count, run_index)

            # --- arrow-key navigation -------------------------------------
            table.focus()
            navigation_ms: list[float] = []
            for _ in range(5):
                before = table.cursor_row
                started = time.perf_counter()
                await pilot.press("down" if before < count - 1 else "up")
                await _wait_until(pilot, lambda before=before: table.cursor_row != before)
                navigation_ms.append((time.perf_counter() - started) * 1000.0)
                assert table.cursor_row != before

            # --- text filter ----------------------------------------------
            await pilot.press("slash")
            expected = min(count, 100)
            started = time.perf_counter()
            await pilot.press(*"skill-00")
            await _wait_until(pilot, lambda: table.row_count == expected)
            text_filter_ms = (time.perf_counter() - started) * 1000.0
            assert table.row_count == expected
            await pilot.press("enter")
            await pilot.press("escape")
            await _wait_until(pilot, lambda: table.row_count == count)

            # --- agent filter: one clean, uncancelled pass ----------------
            why_calls = {"count": 0}

            def counting_why(snapshot: Any, key: str, agent: str) -> Any:
                why_calls["count"] += 1
                return original_why(snapshot, key, agent)

            app_module.snapshot_why = counting_why
            started = time.perf_counter()
            await pilot.press("a")
            await _wait_until(pilot, lambda: _queue_settled(app), timeout=900.0)
            agent_filter_ms = (time.perf_counter() - started) * 1000.0
            app_module.snapshot_why = original_why

            states = _state_values(app)
            assert len(states) == count
            assert all(state and state != "pending" for state in states), [
                (index, value)
                for index, value in enumerate(states)
                if not value or value == "pending"
            ][:10]
            resolved = len(states)
            distinct_groups = len(set(app.screen._lookup_by_key.values()))
            assert why_calls["count"] == distinct_groups, (
                why_calls["count"],
                distinct_groups,
            )
            per_cell_update_ms = statistics.median(app.cell_ms) if app.cell_ms else None

            # --- controlled slow-capture quit ------------------------------
            blocked_started = threading.Event()
            release_capture = threading.Event()

            def blocked_capture(**kwargs: Any) -> Any:
                if kwargs.get("generation", 1) >= 2:
                    blocked_started.set()
                    release_capture.wait(15.0)
                return original_capture(**kwargs)

            app_module.capture_session = blocked_capture
            try:
                await pilot.press("r")
                await _wait_until(pilot, blocked_started.is_set, timeout=10.0)
                started = time.perf_counter()
                await pilot.press("q")
                await _wait_until(pilot, lambda: app.return_code is not None, timeout=10.0)
                slow_capture_quit_ms = (time.perf_counter() - started) * 1000.0
                return_code = app.return_code
            finally:
                release_capture.set()
                app_module.capture_session = original_capture

            return {
                "run": run_index,
                "kind": "clean",
                "capture_ms": capture_ms[0] if capture_ms else None,
                "publication_to_rows_populated_ms": publication_to_rows_ms,
                "publication_to_first_usable_ms": publication_to_usable_ms,
                "startup_to_rows_populated_ms": startup_to_rows_ms,
                "startup_to_first_usable_ms": startup_to_usable_ms,
                "navigation_ms": navigation_ms,
                "text_filter_ms": text_filter_ms,
                "agent_filter_ms": agent_filter_ms,
                "amortized_queue_ms_per_resolved_row": agent_filter_ms / resolved,
                "per_cell_update_ms": per_cell_update_ms,
                "why_calls": why_calls["count"],
                "distinct_lookup_groups": distinct_groups,
                "resolved_cells": resolved,
                "slow_capture_quit_ms": slow_capture_quit_ms,
                "return_code": return_code,
            }
    finally:
        app_module.capture_session = original_capture
        app_module.snapshot_why = original_why
        discovery._directories_for_root = original_directories


def _pending(app: Any) -> int:
    """Number of lookup groups still awaiting a first result."""
    return sum(1 for group in app.screen._groups.values() if group.status == "pending")


async def _probe_active(
    pilot: Any,
    app: _BenchApp,
    table: DataTable,
    count: int,
    run_index: int,
) -> dict[str, Any]:
    """Measure navigation, filtering and quit while resolutions are active.

    Navigation and quit use real Pilot key presses. The filter is driven by
    setting the ``Input`` value, which emits exactly the ``Changed`` message a
    keystroke produces; a real ``Pilot.press`` for the filter waits for the whole
    app to drain and would outlast the resolution queue.
    """
    await pilot.press("a")
    await _wait_until(
        pilot,
        lambda: (
            sum(
                1
                for group in app.screen._groups.values()
                if group.status in ("done", "unavailable")
            )
            >= 20
        ),
        timeout=300.0,
    )
    pending_at_start = _pending(app)

    active_navigation_ms: list[float] = []
    if _pending(app) > 0:
        before = table.cursor_row
        started = time.perf_counter()
        await pilot.press("down" if before < count - 1 else "up")
        await _wait_until(pilot, lambda before=before: table.cursor_row != before, timeout=10.0)
        active_navigation_ms.append((time.perf_counter() - started) * 1000.0)

    active_filter_ms: list[float] = []
    if _pending(app) > 0:
        filter_input = app.screen.query_one("#filter-input", Input)
        filter_input.focus()
        started = time.perf_counter()
        filter_input.value = "5"
        await _wait_until(pilot, lambda: table.row_count < count, timeout=15.0)
        active_filter_ms.append((time.perf_counter() - started) * 1000.0)

    pending_before_quit = _pending(app)
    started = time.perf_counter()
    await pilot.press("ctrl+c")
    await _wait_until(pilot, lambda: app.return_code is not None, timeout=10.0)
    active_quit_ms = (time.perf_counter() - started) * 1000.0

    assert pending_at_start > 0, "probe started with no active resolutions"
    assert pending_before_quit > 0, "probe drained before it could measure active work"

    return {
        "run": run_index,
        "kind": "active-resolution-probe",
        "pending_at_start": pending_at_start,
        "pending_before_quit": pending_before_quit,
        "active_navigation_ms": active_navigation_ms,
        "active_filter_ms": active_filter_ms,
        "active_quit_ms": active_quit_ms,
        "return_code": app.return_code,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _summary(values: list[float]) -> dict[str, float]:
    return {
        "median": round(statistics.median(values), 3),
        "max": round(max(values), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="U3 Home benchmark")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--skills", type=int, default=600)
    parser.add_argument("--injected-delay-ms", type=float, default=50.0)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/validation/u3/implementation/benchmark_home.json"),
    )
    args = parser.parse_args()

    scratch = Path(tempfile.mkdtemp(prefix="skill-lens-u3-bench-")).resolve()
    home = scratch / "home"
    home.mkdir()

    # File writes are deliberately outside every timed region.
    _write_skills(home, args.skills)
    skill_files = sorted(home.rglob("SKILL.md"))
    assert len(skill_files) == args.skills, (len(skill_files), args.skills)
    before = _manifest(home)

    runs: list[dict[str, Any]] = []
    for index in range(1, args.runs + 1):
        with _isolated(home):
            runs.append(asyncio.run(_run_once(home, args.skills, index)))

    with _isolated(home):
        probe = asyncio.run(_run_once(home, args.skills, args.runs + 1, probe=True))

    with _isolated(home):
        delay = asyncio.run(
            _run_once(
                home,
                args.skills,
                args.runs + 2,
                rebuild_delay_ms=args.injected_delay_ms,
            )
        )

    after = _manifest(home)
    assert before == after, "synthetic fixture files changed during the benchmark"

    clean = [run for run in runs if run["kind"] == "clean"]
    per_cell = [run["per_cell_update_ms"] for run in clean if run["per_cell_update_ms"]]

    report: dict[str, Any] = {
        "schema": "skill-lens/u3-benchmark-home/3",
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "textual": getattr(__import__("textual"), "__version__", "unknown"),
        },
        "parameters": {
            "runs": args.runs,
            "skills": args.skills,
            "injected_delay_ms": args.injected_delay_ms,
        },
        "isolation": {
            "sandbox_set_per_run": True,
            "home_and_xdg_set_per_run": True,
            "restored_on_success_and_failure": True,
            "fail_closed_absolute_roots_allowed": False,
            "directory_guard": "every concrete discovery directory must stay under synthetic HOME",
            "fixture_manifest_preserved": before == after,
            "fixture_entries": len(before),
            "skill_count": len(skill_files),
        },
        "runs": [*runs, probe, delay],
        "summary": {
            "capture_ms": _summary([run["capture_ms"] for run in clean if run["capture_ms"]]),
            "publication_to_rows_populated_ms": _summary(
                [run["publication_to_rows_populated_ms"] for run in clean]
            ),
            "publication_to_first_usable_ms": _summary(
                [run["publication_to_first_usable_ms"] for run in clean]
            ),
            "startup_to_rows_populated_ms": _summary(
                [run["startup_to_rows_populated_ms"] for run in clean]
            ),
            "startup_to_first_usable_ms": _summary(
                [run["startup_to_first_usable_ms"] for run in clean]
            ),
            "navigation_ms": _summary([value for run in clean for value in run["navigation_ms"]]),
            "text_filter_ms": _summary([run["text_filter_ms"] for run in clean]),
            "agent_filter_ms": _summary([run["agent_filter_ms"] for run in clean]),
            "amortized_queue_ms_per_resolved_row": _summary(
                [run["amortized_queue_ms_per_resolved_row"] for run in clean]
            ),
            "per_cell_update_ms": _summary(per_cell),
            "why_calls": sorted({run["why_calls"] for run in clean}),
            "distinct_lookup_groups": sorted({run["distinct_lookup_groups"] for run in clean}),
            "slow_capture_quit_ms": _summary([run["slow_capture_quit_ms"] for run in clean]),
            "active_navigation_ms": _summary(probe["active_navigation_ms"]),
            "active_filter_ms": _summary(probe["active_filter_ms"]),
            "active_quit_ms": round(probe["active_quit_ms"], 3),
            "injected_delay_publication_to_usable_ms": round(
                delay["publication_to_first_usable_ms"], 3
            ),
        },
        "limitations": [
            "Single machine, single Python/Textual build; numbers are not a "
            "portable release target.",
            "capture_ms measures the capture worker only (wrapped "
            "capture_session); mount/compose overhead is excluded from it but "
            "included in both startup_to_* figures.",
            "publication_to_rows_populated_ms spans accepted capture on the UI "
            "thread to the end of the instrumented Home rebuild that first "
            "carries every row, before Textual lays out and paints. "
            "publication_to_first_usable_ms spans the same start to a "
            "benchmark-only callback scheduled with call_after_refresh, which "
            "runs after the screen has been refreshed; that is the figure to "
            "read as time-until-usable. Both are wall-clock on the shared event "
            "loop and include worker/message scheduling.",
            "The injected-delay run demonstrates the publication-to-first-usable "
            "interval tracks real work; the requested delay is "
            f"{args.injected_delay_ms} ms.",
            "per_cell_update_ms is the real cost of one Home state-cell "
            "update. amortized_queue_ms_per_resolved_row is the whole serial "
            "queue wall time divided by resolved rows: it folds together "
            "snapshot_why worker execution, worker/message scheduling, the "
            "per-group Home cell updates and their redraws. The harness does "
            "not attribute the total to any one of those components.",
            "active_navigation_ms/active_filter_ms/active_quit_ms are measured "
            "while hundreds of resolutions are still pending (the probe records "
            "pending_at_start and pending_before_quit). Navigation and quit use "
            "real Pilot key presses; the filter is driven through the Input's "
            "Changed event because Pilot's press waits for the app to drain and "
            "would outlast the queue. That Input.Changed path is not a physical "
            "key press, so no physical key-to-paint latency is claimed for the "
            "filter figure. Navigating, filtering and the queued re-drive all "
            "leave that probe unsuitable for the why_call/group equality "
            "assertion.",
            "The superseded schema-2 receipt "
            "docs/validation/u3/implementation/historical/benchmark-home-r2.json "
            "labelled its row-population boundary 'publication_to_first_list_ms' "
            "and described it as laid out/paint; that wording was too strong. It "
            "is preserved as history, not relabelled valid, and is superseded "
            "by this schema-3 receipt, which separates row population from "
            "post-refresh usability.",
            "The superseded receipt "
            "docs/validation/u3/implementation/historical/benchmark-home-r1.json "
            "is invalid and unsafe (its sandbox was cleared after run 1, so "
            "later runs allowed absolute system roots, and its publication "
            "boundary measured a near-zero predicate check). It is preserved "
            "as history and is not relabelled valid.",
        ],
    }

    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text + "\n", encoding="utf-8")
    print(f"\nwrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
