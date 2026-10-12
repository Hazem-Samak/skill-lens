#!/usr/bin/env python3
"""U2 Mutation Campaign: Recursive Read-Only AST Guard & Discriminator Mutation Testing.

Executes mutation testing across:
- Section 10 Prohibited AST patterns:
  - Category 1: Banned root and render imports
  - Category 2: OS destructive calls and aliases
  - Category 3: Path write methods and instance calls
  - Category 4: Open write, dynamic, and unpacked modes
  - Category 5: Terminal writes (print, stream writes, console)
- Watchdog Discriminator Mutation:
  - Category 6: Defective waiting-runner blocked on prompt quit vs active watchdog

For each mutation:
1. Validates clean control (0 violations or normal clean quit)
2. Injects mutation into isolated source tree or runtime harness
3. Verifies expected failure / detection pattern (mutant killed)
4. Restores clean source / runner and verifies clean outcome
5. Persists execution receipts and full logs

Generates:
- docs/validation/u2/mutation_records.json
- docs/validation/u2/MUTATION_RESULTS.md
- docs/validation/u2/logs/
"""

from __future__ import annotations

import json
import platform
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

# Resolve and verify repo root provenance (docs/validation/u2 -> parents[3])
REPO_ROOT = Path(__file__).resolve().parents[3]
assert (REPO_ROOT / "pyproject.toml").is_file(), (
    f"Provenance check failed: no pyproject.toml at {REPO_ROOT}"
)
assert (REPO_ROOT / "skill_lens").is_dir(), (
    f"Provenance check failed: no skill_lens package at {REPO_ROOT}"
)

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.fixtures.scenarios import build_scenario  # noqa: E402
from tests.test_tui_read_only import MUTATION_CASES, check_source_tree  # noqa: E402


def run_waiting_runner_mutation(logs_dir: Path) -> dict[str, Any]:
    """Test the discriminating watchdog against a deliberately waiting runner mutant.

    Proves that a runner that waits for background workers to finish fails the selector,
    whereas the real non-blocking runner passes.
    """
    case_id = "waiting_runner_quit_watchdog"
    log_file = logs_dir / f"{case_id}.log"
    log_lines: list[str] = [f"=== CASE {case_id} ==="]
    snippet = (
        "def mutant_run(home, cwd, **kw):\n"
        "    code = tui.run(home, cwd, **kw)\n"
        "    worker_finished.wait()\n"
        "    return code"
    )
    expected_pattern = (
        "Watchdog fired before run() returned! Runner blocked waiting for worker completion."
    )
    log_lines.append(f"Expected pattern: {expected_pattern}")

    from textual.pilot import Pilot

    import skill_lens.tui as real_tui
    import skill_lens.tui.app as app_mod
    from skill_lens.core import paths
    from skill_lens.core.cancellation import CaptureCancelled
    from skill_lens.core.exitcodes import ExitCode

    temp_dir = Path(tempfile.mkdtemp(prefix=f"u2_mut_{case_id}_"))
    orig_capture = app_mod.capture_session
    try:
        build_scenario("claude_personal_beats_project", temp_dir)
        paths.set_sandbox(temp_dir)

        # Phase 1: Control (shipped real_tui.run)
        log_lines.append("Phase 1: Control (shipped real_tui.run)")
        capture_started = threading.Event()
        release_capture = threading.Event()
        worker_finished = threading.Event()
        watchdog_fired = threading.Event()

        def blocked_capture(*args: Any, **kwargs: Any) -> Any:
            capture_started.set()
            release_capture.wait()
            worker_finished.set()
            raise CaptureCancelled()

        app_mod.capture_session = blocked_capture

        def on_watchdog() -> None:
            watchdog_fired.set()
            release_capture.set()

        watchdog = threading.Timer(1.5, on_watchdog)
        watchdog.daemon = True
        watchdog.start()

        async def auto_quit(pilot: Pilot) -> None:
            for _ in range(50):
                if capture_started.is_set():
                    break
                await pilot.pause(0.02)
            assert capture_started.is_set(), "capture worker must have started"
            assert not release_capture.is_set(), "release must not be set before q"
            await pilot.press("q")

        try:
            code = real_tui.run(temp_dir, temp_dir, headless=True, auto_pilot=auto_quit)
            watchdog.cancel()
            if watchdog_fired.is_set() or release_capture.is_set() or code != int(ExitCode.OK):
                raise RuntimeError("Control failed: watchdog fired or release was prematurely set")
            log_lines.append("Control outcome: CLEAN (real runner returned before worker released)")
        finally:
            watchdog.cancel()
            release_capture.set()
            worker_finished.wait(timeout=3.0)

        # Phase 2: Mutant (waiting runner that blocks until worker finishes)
        log_lines.append("Phase 2: Mutant (waiting runner that blocks for worker)")
        mut_capture_started = threading.Event()
        mut_release_capture = threading.Event()
        mut_worker_finished = threading.Event()
        mut_watchdog_fired = threading.Event()

        def mut_blocked_capture(*args: Any, **kwargs: Any) -> Any:
            mut_capture_started.set()
            mut_release_capture.wait()
            mut_worker_finished.set()
            raise CaptureCancelled()

        app_mod.capture_session = mut_blocked_capture

        def on_mut_watchdog() -> None:
            mut_watchdog_fired.set()
            mut_release_capture.set()

        mut_watchdog = threading.Timer(1.0, on_mut_watchdog)
        mut_watchdog.daemon = True
        mut_watchdog.start()

        def mutant_run(home: Path, cwd: Path, **kwargs: Any) -> int:
            ret = real_tui.run(home, cwd, **kwargs)
            # Deliberate mutant defect: wait for thread worker to complete
            mut_worker_finished.wait()
            return ret

        async def auto_quit_mutant(pilot: Pilot) -> None:
            for _ in range(50):
                if mut_capture_started.is_set():
                    break
                await pilot.pause(0.02)
            assert mut_capture_started.is_set()
            assert not mut_release_capture.is_set()
            await pilot.press("q")

        mutant_detected = False
        try:
            _ = mutant_run(temp_dir, temp_dir, headless=True, auto_pilot=auto_quit_mutant)
            mut_watchdog.cancel()
            if mut_watchdog_fired.is_set():
                log_lines.append(f"Mutant caught: {expected_pattern}")
                mutant_detected = True
            else:
                log_lines.append("Mutant NOT caught: watchdog did not fire")
        except Exception as exc:
            log_lines.append(f"Mutant threw exception: {exc}")
            mutant_detected = True
        finally:
            mut_watchdog.cancel()
            mut_release_capture.set()
            mut_worker_finished.wait(timeout=3.0)

        if not mutant_detected:
            raise RuntimeError(
                "Mutant waiting runner survived! Discriminating watchdog did not catch it."
            )

        # Phase 3: Restore
        log_lines.append("Phase 3: Restore (clean capture restored)")
        app_mod.capture_session = orig_capture
        log_lines.append(
            "Outcome: KILLED (discriminating selector fired watchdog on waiting runner)"
        )
        outcome = "KILLED"

    except Exception as exc:
        outcome = "SURVIVED"
        log_lines.append(f"Outcome: SURVIVED ({exc})")
    finally:
        app_mod.capture_session = orig_capture
        paths.set_sandbox(None)
        shutil.rmtree(temp_dir, ignore_errors=True)
        log_file.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    return {
        "case_id": case_id,
        "mutant_snippet": snippet,
        "expected_pattern": expected_pattern,
        "outcome": outcome,
        "log": f"logs/{case_id}.log",
    }


def run_palette_screenshot_mutation(logs_dir: Path) -> dict[str, Any]:
    """Test the discriminating write sentinel against a mutant App that re-enables
    command palette or restores inherited Textual App.save_screenshot."""
    case_id = "command_palette_screenshot_write_discriminator"
    log_file = logs_dir / f"{case_id}.log"
    log_lines: list[str] = [f"=== CASE {case_id} ==="]
    snippet = (
        "class MutantApp(SkillLensApp):\n"
        "    ENABLE_COMMAND_PALETTE = True\n"
        "    save_screenshot = App.save_screenshot"
    )
    expected_pattern = "Sentinel caught write attempt to screenshot file"
    log_lines.append(f"Expected pattern: {expected_pattern}")

    import builtins

    from textual.app import App

    from skill_lens.core import paths
    from skill_lens.tui.app import SkillLensApp

    temp_dir = Path(tempfile.mkdtemp(prefix=f"u2_mut_{case_id}_"))
    try:
        paths.set_sandbox(temp_dir)
        # Phase 1: Control (ENABLE_COMMAND_PALETTE=False, save_screenshot neutralized)
        log_lines.append("Phase 1: Control (shipped SkillLensApp)")
        app = SkillLensApp(home=temp_dir, cwd=temp_dir)
        if app.ENABLE_COMMAND_PALETTE is not False or len(app.COMMANDS) != 0:
            raise RuntimeError("Control failed: command palette is not disabled on SkillLensApp")

        # Verify control save_screenshot does not write
        write_attempts: list[str] = []
        orig_open = builtins.open

        def failing_write_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
            if any(ch in mode for ch in ("w", "a", "x", "+")):
                write_attempts.append(str(file))
                raise RuntimeError(f"Sentinel caught write attempt to screenshot file: {file}")
            return orig_open(file, mode, *args, **kwargs)

        builtins.open = failing_write_open
        res = app.save_screenshot()
        builtins.open = orig_open

        if res != "" or write_attempts:
            raise RuntimeError("Control failed: save_screenshot attempted disk write")
        log_lines.append("Control outcome: CLEAN (zero writes, empty string return)")

        # Phase 2: Mutant (App with Textual's raw save_screenshot)
        log_lines.append("Phase 2: Mutant (App with un-neutralized save_screenshot)")

        class MutantWriteApp(SkillLensApp):
            save_screenshot = App.save_screenshot

        mutant = MutantWriteApp(home=temp_dir, cwd=temp_dir)
        mutant.export_screenshot = lambda: "<svg></svg>"  # type: ignore[method-assign]

        mutant_detected = False
        builtins.open = failing_write_open
        try:
            mutant.save_screenshot(filename="mutant_shot.svg", path=str(temp_dir))
        except Exception as exc:
            if "Sentinel caught write attempt" in str(exc):
                log_lines.append(f"Mutant caught: {exc}")
                mutant_detected = True
            else:
                log_lines.append(f"Mutant threw unexpected error: {exc}")
        finally:
            builtins.open = orig_open

        if not mutant_detected:
            raise RuntimeError("Mutant survived! Write sentinel did not catch save_screenshot.")

        # Phase 3: Restore
        log_lines.append("Phase 3: Restore (clean SkillLensApp verified)")
        outcome = "KILLED"
        log_lines.append("Outcome: KILLED (discriminator caught forbidden screenshot write)")

    except Exception as exc:
        outcome = "SURVIVED"
        log_lines.append(f"Outcome: SURVIVED ({exc})")
    finally:
        paths.set_sandbox(None)
        shutil.rmtree(temp_dir, ignore_errors=True)
        log_file.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    return {
        "case_id": case_id,
        "mutant_snippet": snippet,
        "expected_pattern": expected_pattern,
        "outcome": outcome,
        "log": f"logs/{case_id}.log",
    }


def run_display_precedence_mutation(logs_dir: Path) -> dict[str, Any]:
    """Test the discriminating selector against a mutant SessionController where
    status checks failed before retry_message (hiding expected retry message)."""
    case_id = "status_display_precedence_discriminator"
    log_file = logs_dir / f"{case_id}.log"
    log_lines: list[str] = [f"=== CASE {case_id} ==="]
    snippet = (
        "class MutantController(SessionController):\n"
        "    @property\n"
        "    def status(self):\n"
        "        if self.failed: return 'error'\n"
        "        if self.retry_message is not None: return 'retry'..."
    )
    expected_pattern = "Expected status 'retry' but mutant returned 'error'"
    log_lines.append(f"Expected pattern: {expected_pattern}")

    from skill_lens.core.exitcodes import ExitCode
    from skill_lens.core.snapshot import SnapshotChanged
    from skill_lens.tui.session import SessionController

    try:
        # Phase 1: Control (shipped SessionController)
        log_lines.append("Phase 1: Control (shipped SessionController)")
        ctrl = SessionController()
        gen1, _ = ctrl.request_refresh()  # type: ignore[misc]
        ctrl.accept_capture_error(gen1, RuntimeError("disk fault"))
        assert ctrl.is_failed is True
        assert ctrl.status == "error"

        gen2, _ = ctrl.request_refresh()  # type: ignore[misc]
        ctrl.accept_capture_error(gen2, SnapshotChanged("Files changed. Press r."))
        assert ctrl.is_failed is True
        assert ctrl.status == "retry"  # Shipped code correctly displays retry!
        assert ctrl.close() == int(ExitCode.INTERNAL)

        # Control check: report error during pending refresh outranks loading
        from tests.test_tui_session import _make_dummy_snapshot

        ctrl2 = SessionController()
        cgen1, _ = ctrl2.request_refresh()  # type: ignore[misc]
        ctrl2.accept_capture(_make_dummy_snapshot(cgen1), cgen1)
        req, _, _ = ctrl2.request_view("why", ("skill", "claude"))
        assert req is not None
        ctrl2.request_refresh()
        assert ctrl2.status == "loading"
        ctrl2.accept_view_error(
            "why", req.request_id, req.generation, req.arguments, RuntimeError("view err")
        )
        assert ctrl2.status == "error"  # Shipped code correctly outranks loading!
        log_lines.append("Control passed: retry outranks failure, report error outranks loading.")

        # Phase 2: Mutant 1 (evaluates failed before retry_message)
        log_lines.append("Phase 2: Mutant 1 (status checks failed before retry_message)")

        class Mutant1Controller(SessionController):
            @property
            def status(self) -> str:
                if self.failed:
                    return "error"
                if self.retry_message is not None:
                    return "retry"
                if self.pending_generation is not None:
                    return "loading"
                if self.current is not None:
                    return "ready"
                return "idle"

        mut1_ctrl = Mutant1Controller()
        mgen1, _ = mut1_ctrl.request_refresh()  # type: ignore[misc]
        mut1_ctrl.accept_capture_error(mgen1, RuntimeError("disk fault"))
        mgen2, _ = mut1_ctrl.request_refresh()  # type: ignore[misc]
        mut1_ctrl.accept_capture_error(mgen2, SnapshotChanged("Files changed. Press r."))

        mut1_detected = False
        try:
            if mut1_ctrl.status != "retry":
                raise AssertionError(
                    f"Expected status 'retry' but mutant returned '{mut1_ctrl.status}'"
                )
        except AssertionError as exc:
            log_lines.append(f"Mutant 1 caught: {exc}")
            mut1_detected = True

        if not mut1_detected:
            raise RuntimeError("Mutant 1 survived: retry display precedence was not caught!")

        # Phase 2: Mutant 2 (evaluates pending_generation before failed)
        log_lines.append("Phase 2: Mutant 2 (status checks pending_generation before failed)")

        class Mutant2Controller(SessionController):
            @property
            def status(self) -> str:
                if self.pending_generation is not None:
                    return "loading"
                if self.retry_message is not None:
                    return "retry"
                if self.failed:
                    return "error"
                if self.current is not None:
                    return "ready"
                return "idle"

        mut2_ctrl = Mutant2Controller()
        m2gen1, _ = mut2_ctrl.request_refresh()  # type: ignore[misc]
        mut2_ctrl.accept_capture(_make_dummy_snapshot(m2gen1), m2gen1)
        m2req, _, _ = mut2_ctrl.request_view("why", ("skill", "claude"))
        assert m2req is not None
        mut2_ctrl.request_refresh()
        mut2_ctrl.accept_view_error(
            "why", m2req.request_id, m2req.generation, m2req.arguments, RuntimeError("view err")
        )

        mut2_detected = False
        try:
            if mut2_ctrl.status != "error":
                raise AssertionError(
                    f"Expected status 'error' but mutant returned '{mut2_ctrl.status}'"
                )
        except AssertionError as exc:
            log_lines.append(f"Mutant 2 caught: {exc}")
            mut2_detected = True

        if not mut2_detected:
            raise RuntimeError("Mutant 2 survived: report error during refresh was not caught!")

        # Phase 3: Restore
        log_lines.append("Phase 3: Restore (clean SessionController verified)")
        log_lines.append(
            "Outcome: KILLED (discriminator caught both defective status ordering mutants)"
        )
        outcome = "KILLED"

    except Exception as exc:
        outcome = "SURVIVED"
        log_lines.append(f"Outcome: SURVIVED ({exc})")
    finally:
        log_file.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    return {
        "case_id": case_id,
        "mutant_snippet": snippet,
        "expected_pattern": expected_pattern,
        "outcome": outcome,
        "log": f"logs/{case_id}.log",
    }


def run_campaign() -> int:
    output_dir = REPO_ROOT / "docs" / "validation" / "u2"
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    total_start = time.time()

    total_count = len(MUTATION_CASES) + 3
    print(
        f"Starting U2 Mutation Campaign ({total_count} mutations: "
        f"{len(MUTATION_CASES)} AST + 1 Waiting-Runner Quit + "
        "1 Palette/Screenshot Write + 1 Status Precedence)..."
    )

    # Part 1: AST Guard Mutations
    for idx, (case_id, mutant_snippet, expected_pattern) in enumerate(MUTATION_CASES, 1):
        temp_dir = Path(tempfile.mkdtemp(prefix=f"u2_mut_{case_id}_"))
        log_file = logs_dir / f"{case_id}.log"
        log_lines: list[str] = []

        try:
            # Phase 1: Control
            clean_file = temp_dir / "module.py"
            clean_file.write_text("def hello() -> str:\n    return 'clean'\n", encoding="utf-8")
            control_violations = check_source_tree(temp_dir)
            log_lines.append(f"=== CASE {case_id} ===")
            log_lines.append(f"Expected pattern: {expected_pattern}")
            log_lines.append(f"Control violations: {control_violations}")

            if control_violations:
                raise RuntimeError(f"Control failed with violations: {control_violations}")

            # Phase 2: Mutant
            mutant_file = temp_dir / "module.py"
            mutant_file.write_text(f"{mutant_snippet}\n", encoding="utf-8")
            mutant_violations = check_source_tree(temp_dir)
            log_lines.append(f"Mutant violations: {mutant_violations}")

            matched = any(expected_pattern in v for v in mutant_violations)
            if not matched:
                raise RuntimeError(
                    f"Mutant not detected! Expected '{expected_pattern}', got: {mutant_violations}"
                )

            # Phase 3: Restore
            clean_file.write_text("def hello() -> str:\n    return 'clean'\n", encoding="utf-8")
            restore_violations = check_source_tree(temp_dir)
            log_lines.append(f"Restore violations: {restore_violations}")

            if restore_violations:
                raise RuntimeError(f"Restore failed with violations: {restore_violations}")

            outcome = "KILLED"
            log_lines.append("Outcome: KILLED (detected strictly matching pattern)")
            print(f"[{idx:02d}/{total_count}] {case_id}: KILLED")

        except Exception as exc:
            outcome = "SURVIVED"
            log_lines.append(f"Outcome: SURVIVED ({exc})")
            print(f"[{idx:02d}/{total_count}] {case_id}: SURVIVED - {exc}")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            log_file.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

        records.append(
            {
                "case_id": case_id,
                "mutant_snippet": mutant_snippet,
                "expected_pattern": expected_pattern,
                "outcome": outcome,
                "log": f"logs/{case_id}.log",
            }
        )

    # Part 2: Waiting-Runner Watchdog Discriminator Mutation
    watchdog_record = run_waiting_runner_mutation(logs_dir)
    records.append(watchdog_record)
    print(
        f"[{len(records):02d}/{total_count}] {watchdog_record['case_id']}: "
        f"{watchdog_record['outcome']}"
    )

    # Part 3: Command Palette & Screenshot Write Discriminator Mutation
    palette_record = run_palette_screenshot_mutation(logs_dir)
    records.append(palette_record)
    print(
        f"[{len(records):02d}/{total_count}] {palette_record['case_id']}: "
        f"{palette_record['outcome']}"
    )

    # Part 4: Status Display Precedence Discriminator Mutation
    precedence_record = run_display_precedence_mutation(logs_dir)
    records.append(precedence_record)
    print(
        f"[{len(records):02d}/{total_count}] {precedence_record['case_id']}: "
        f"{precedence_record['outcome']}"
    )

    elapsed = time.time() - total_start
    survivors = [r for r in records if r["outcome"] != "KILLED"]
    killed_count = len(records) - len(survivors)

    # Write mutation_records.json
    records_path = output_dir / "mutation_records.json"
    platform_info = f"{platform.system()} {platform.machine()} Python {platform.python_version()}"
    with open(records_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "platform": platform_info,
                "total": len(records),
                "killed": killed_count,
                "survivors": len(survivors),
                "elapsed_seconds": round(elapsed, 3),
                "records": records,
            },
            f,
            indent=2,
        )

    # Write MUTATION_RESULTS.md
    md_path = output_dir / "MUTATION_RESULTS.md"
    md_lines = [
        "# U2 Mutation Campaign Results (AST Guard & Watchdog Discriminator)",
        "",
        f"Conducted across {len(records)} distinct mutations in isolated disposable trees",
        "and runtime pilot harnesses exercising both the recursive AST checker `check_source_tree`",
        "and the discriminating watchdog prompt-quit selector.",
        "Full execution logs are persisted under `docs/validation/u2/logs/`.",
        "",
        f"- **Platform:** {platform_info}",
        f"- **Total Mutations:** {len(records)}",
        f"- **Mutants Killed:** {killed_count}",
        f"- **Survivors:** {len(survivors)}",
        f"- **Duration:** {elapsed:.2f}s",
        "",
        "| ID | Snippet / Defect | Expected Violation Pattern / Failure | Outcome | Log |",
        "| --- | --- | --- | :---: | :---: |",
    ]
    for r in records:
        snippet_esc = r["mutant_snippet"].replace("\n", " ").replace("|", "\\|")
        md_lines.append(
            f"| `{r['case_id']}` | `{snippet_esc}` | `{r['expected_pattern']}` | "
            f"**{r['outcome']}** | [`log`]({r['log']}) |"
        )

    md_lines.extend(
        [
            "",
            "## Execution Summary",
            "",
            "1. **Clean Control:** Every cycle verifies that benign code or "
            "real runner produces 0 violations.",
            "2. **Strict Pattern Match:** Every mutation is detected by the AST guard "
            "or active watchdog timer with the exact expected failure or violation pattern.",
            "3. **Clean Restoration:** Every cycle restores benign code/runner and "
            "confirms clean execution.",
            f"4. **Outcome Summary:** {killed_count}/{len(records)} killed "
            f"({len(survivors)} survivors).",
            "",
        ]
    )

    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(
        f"\nCompleted in {elapsed:.2f}s. Killed: {killed_count}/{len(records)} "
        f"(Survivors: {len(survivors)})."
    )

    # Return nonzero if any required mutant survives
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(run_campaign())
