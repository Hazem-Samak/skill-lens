"""Skill Lens full-screen terminal UI entry points (Assignment U2).

Specification reference: FULL_SCREEN_TUI.md §9.1, §10, Step 2, and §21.7.
Lazily exposes `run(home, cwd) -> int` for CLI launch, using an owned
asyncio event loop so synchronous quit does not join or wait for
ThreadPoolExecutor worker threads.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from skill_lens.core.exitcodes import ExitCode
from skill_lens.core.snapshot import DEFAULT_MAX_SNAPSHOT_BYTES
from skill_lens.tui._textual_compat import get_unhandled_fault
from skill_lens.tui.app import (
    CaptureComplete,
    CaptureFailed,
    PlaceholderHomeScreen,
    SkillLensApp,
    ViewReportComplete,
    ViewReportFailed,
)
from skill_lens.tui.session import (
    ReportValue,
    SessionController,
    ViewName,
    ViewRequest,
)


def run(
    home: Path,
    cwd: Path,
    *,
    headless: bool = False,
    auto_pilot: Any = None,
    max_snapshot_bytes: int | None = DEFAULT_MAX_SNAPSHOT_BYTES,
) -> int:
    """Run the Skill Lens full-screen terminal UI.

    Uses an owned asyncio event loop to ensure synchronous shutdown
    does not block waiting for ThreadPoolExecutor worker joins.

    Args:
        home: Resolved effective user HOME path.
        cwd: Resolved effective working directory path.
        headless: If True, run without terminal output (for headless tests).
        auto_pilot: Optional coroutine callback for autopilot driving.
        max_snapshot_bytes: Capture payload budget in bytes; ``None`` or ``0``
            means unbounded. A home above the budget is refused, not truncated.

    Returns:
        0 on normal quit, or 3 on accepted unexpected internal faults.
    """
    loop = asyncio.new_event_loop()
    prev_loop: asyncio.AbstractEventLoop | None = None
    try:
        try:
            prev_loop = asyncio.get_event_loop()
        except Exception:
            prev_loop = None

        asyncio.set_event_loop(loop)
        app: SkillLensApp | None = None
        try:
            app = SkillLensApp(
                home=home,
                cwd=cwd,
                max_snapshot_bytes=max_snapshot_bytes,
            )
            code = app.run(
                loop=loop,
                headless=headless,
                auto_pilot=auto_pilot,
            )
            unhandled_exc = get_unhandled_fault(app)
            if unhandled_exc is not None:
                raise unhandled_exc
            if code is not None:
                return int(code)
            return int(ExitCode.INTERNAL if app.controller.failed else ExitCode.OK)
        finally:
            if app is not None:
                app.controller.close()
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    finally:
        try:
            loop.close()
        finally:
            if prev_loop is not None and not prev_loop.is_closed():
                asyncio.set_event_loop(prev_loop)
            else:
                asyncio.set_event_loop(None)


__all__ = [
    "CaptureComplete",
    "CaptureFailed",
    "PlaceholderHomeScreen",
    "ReportValue",
    "SessionController",
    "SkillLensApp",
    "ViewName",
    "ViewReportComplete",
    "ViewReportFailed",
    "ViewRequest",
    "run",
]
