"""Targeted regression and contract tests for Stage G repairs.

Covers:
1. Audited Textual private fault adapter in skill_lens.tui._textual_compat:
   - App class and instance shape audits
   - Loud failure on missing or non-callable private hooks / attributes (no false success)
   - Rejection of unusable _exception_event (missing or non-callable set() notification)
   - Proper fault recording, return code setting, and exception extraction
   - First-fault preservation
2. Preserved fault containment without terminal tracebacks:
   - SkillLensApp._handle_exception routes through centralized adapter
   - Sticky exit 3 on unexpected faults
   - CLI prints plain-English message and exits 3
3. Fast exit 2 on explicit non-interactive TUI launch
4. Textual version compatibility and contract assertions (floor 8.2.8 / latest 8.2.8)
5. Headless runner prompt shutdown while background worker is blocked:
   - Bounded active watchdog timer
   - Exact started and unfinished assertions
   - Proves synchronous teardown never joins or waits for ThreadPoolExecutor workers
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pytest
import textual
from textual.app import App
from textual.pilot import Pilot
from typer.testing import CliRunner

import skill_lens
import skill_lens.tui as tui
from skill_lens.cli import app as cli_app
from skill_lens.core.cancellation import CaptureCancelled
from skill_lens.core.exitcodes import ExitCode
from skill_lens.tui._textual_compat import (
    REQUIRED_APP_ATTRIBUTES,
    audit_textual_app_contract,
    get_unhandled_fault,
    record_unhandled_fault,
)
from skill_lens.tui.app import SkillLensApp
from tests.fixtures.scenarios import build_scenario


def test_textual_version_meets_declared_floor() -> None:
    """Installed Textual version must satisfy the declared >=8.2.8 floor."""
    version_tuple = tuple(int(x) for x in textual.__version__.split(".")[:3])
    assert version_tuple >= (8, 2, 8), (
        f"Textual must be >= 8.2.8; installed is {textual.__version__}"
    )


def test_textual_installed_contract_audits_cleanly(mock_home: Path) -> None:
    """The installed Textual App class and instance must audit cleanly."""
    # Class audit
    audit_textual_app_contract(App)
    # Instance audit
    dummy = App()
    audit_textual_app_contract(dummy)
    # SkillLensApp audit under isolated synthetic home and project cwd
    cwd = mock_home / "project"
    cwd.mkdir(parents=True, exist_ok=True)
    dummy_skill = SkillLensApp(home=mock_home, cwd=cwd)
    audit_textual_app_contract(dummy_skill)


def test_adapter_detects_missing_class_method() -> None:
    """If a future Textual version removes _handle_exception, the audit must raise RuntimeError."""

    class IncompatibleApp:
        pass

    with pytest.raises(RuntimeError, match="Incompatible Textual App class"):
        audit_textual_app_contract(IncompatibleApp)  # type: ignore[arg-type]


def test_adapter_detects_non_callable_class_method() -> None:
    """If _handle_exception exists on class but is not callable, audit must raise RuntimeError."""

    class NonCallableHookApp:
        _handle_exception = None

    with pytest.raises(RuntimeError, match="missing or non-callable method '_handle_exception'"):
        audit_textual_app_contract(NonCallableHookApp)  # type: ignore[arg-type]


@pytest.mark.parametrize("missing_attr", REQUIRED_APP_ATTRIBUTES)
def test_adapter_detects_missing_instance_attribute(missing_attr: str) -> None:
    """If an App instance is missing any required fault attribute, audit raises RuntimeError."""

    class MockAppWithMissingAttr:
        def _handle_exception(self, error: Exception) -> None:
            pass

    app = MockAppWithMissingAttr()
    for attr in REQUIRED_APP_ATTRIBUTES:
        if attr != missing_attr:
            if attr == "_exception_event":
                setattr(app, attr, threading.Event())
            else:
                setattr(app, attr, None)

    with pytest.raises(RuntimeError, match="Incompatible Textual App instance"):
        audit_textual_app_contract(app)

    with pytest.raises(RuntimeError, match="Incompatible Textual App instance"):
        record_unhandled_fault(app, RuntimeError("fault"))

    with pytest.raises(RuntimeError, match="Incompatible Textual App instance"):
        get_unhandled_fault(app)


def test_adapter_detects_unusable_event_notification() -> None:
    """If _exception_event lacks callable set(), audit and record_unhandled_fault must reject it."""

    class BadEventApp:
        def _handle_exception(self, error: Exception) -> None:
            pass

        _return_code = 0
        _exception = None
        _exception_event = object()

    app = BadEventApp()
    with pytest.raises(
        RuntimeError, match="_exception_event does not support callable set\\(\\) notification"
    ):
        audit_textual_app_contract(app)

    with pytest.raises(
        RuntimeError, match="_exception_event does not support callable set\\(\\) notification"
    ):
        record_unhandled_fault(app, RuntimeError("probe fault"))


def test_coordinator_shape_probe_is_rejected() -> None:
    """The coordinator's shape probe object with None hook and object event must be rejected."""

    class CoordinatorProbe:
        _handle_exception = None
        _return_code = 0
        _exception = None
        _exception_event = object()

    probe = CoordinatorProbe()
    with pytest.raises(RuntimeError, match="Incompatible Textual App class"):
        audit_textual_app_contract(probe)

    with pytest.raises(RuntimeError, match="Incompatible Textual App class"):
        record_unhandled_fault(probe, RuntimeError("probe"))


def test_record_and_get_unhandled_fault() -> None:
    """record_unhandled_fault and get_unhandled_fault store, notify,
    and extract exception correctly."""
    app = App()
    assert get_unhandled_fault(app) is None

    err = ValueError("test unhandled fault")
    record_unhandled_fault(app, err, return_code=3)

    assert app._return_code == 3
    assert app._exception is err
    assert app._exception_event.is_set()
    assert get_unhandled_fault(app) is err

    # First-fault semantics: second call does not overwrite first exception
    second_err = RuntimeError("second fault")
    record_unhandled_fault(app, second_err, return_code=3)
    assert app._exception is err


def test_skill_lens_app_handle_exception_containment(mock_home: Path) -> None:
    """SkillLensApp._handle_exception contains UI faults, sets sticky exit 3,
    and suppresses rich tracebacks."""
    cwd = mock_home / "project"
    cwd.mkdir(parents=True, exist_ok=True)
    app = SkillLensApp(home=mock_home, cwd=cwd)
    err = RuntimeError("injected direct fault")

    app._handle_exception(err)

    assert app.controller.is_failed
    assert app._return_code == int(ExitCode.INTERNAL)
    assert get_unhandled_fault(app) is err
    # Rich traceback suppressed
    assert len(app._exit_renderables) == 0


def test_explicit_non_interactive_tui_exits_2(mock_home: Path) -> None:
    """Explicit 'tui' invocation in a non-interactive terminal exits 2 without traceback."""
    cwd = mock_home / "project"
    cwd.mkdir(parents=True, exist_ok=True)
    runner = CliRunner()
    result = runner.invoke(cli_app, ["tui", "--sandbox", str(mock_home), "--cwd", str(cwd)])
    assert result.exit_code == int(ExitCode.USAGE)
    assert "Error: The terminal UI requires an interactive terminal." in result.stderr
    assert "Traceback" not in result.stderr


def test_prompt_quit_does_not_block_on_worker(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Quitting the TUI via tui.run() returns cleanly BEFORE a blocked background
    worker is released, guarded by an active watchdog timer."""
    cwd = mock_home / "project"
    cwd.mkdir(parents=True, exist_ok=True)
    build_scenario("claude_personal_beats_project", mock_home)

    capture_started = threading.Event()
    release_capture = threading.Event()
    worker_finished = threading.Event()
    watchdog_fired = threading.Event()

    def blocked_capture(
        *,
        generation: int,
        home: Path,
        cwd: Path,
        max_snapshot_bytes: Any = None,
        cancelled: Any = None,
    ) -> Any:
        capture_started.set()
        # Block indefinitely until release_capture is explicitly set
        release_capture.wait()
        worker_finished.set()
        raise CaptureCancelled()

    monkeypatch.setattr("skill_lens.tui.app.capture_session", blocked_capture)

    # Active watchdog: fires after 1.5s if runner is stuck waiting for worker join
    def on_watchdog() -> None:
        watchdog_fired.set()
        release_capture.set()

    watchdog = threading.Timer(1.5, on_watchdog)
    watchdog.daemon = True
    watchdog.start()

    run_completed = False
    try:

        async def auto_quit(pilot: Pilot) -> None:
            for _ in range(50):
                if capture_started.is_set():
                    break
                await pilot.pause(0.02)
            assert capture_started.is_set(), "capture worker must have started"
            assert not release_capture.is_set(), "capture worker must still be blocked"
            await pilot.press("q")

        code = tui.run(mock_home, cwd, headless=True, auto_pilot=auto_quit)
        run_completed = True

        # Assert watchdog never fired and worker never finished before runner returned
        assert not watchdog_fired.is_set(), (
            "Watchdog fired! Runner blocked waiting for background worker completion."
        )
        assert not release_capture.is_set(), "tui.run() returned after worker was released!"
        assert not worker_finished.is_set(), "worker finished before tui.run() returned!"
        assert code == int(ExitCode.OK)
    finally:
        watchdog.cancel()
        release_capture.set()
        worker_finished.wait(timeout=5.0)

    assert run_completed is True


def test_installed_module_provenance() -> None:
    """skill_lens and skill_lens.tui must resolve to the same package root."""
    assert skill_lens.__file__ is not None
    assert tui.__file__ is not None
    root_parent = Path(skill_lens.__file__).resolve().parent
    tui_parent = Path(tui.__file__).resolve().parent.parent
    assert root_parent == tui_parent, (
        f"Package mismatch: skill_lens at {root_parent}, tui at {tui_parent}"
    )
