# Skill Lens 0.2 — Worker Controller & TUI Skeleton Walkthrough (U2)

> **Status:** Accepted by coordinator Sol after direct verification and independent Muse and MiMo reviews, including the targeted correction round.
> **Scope:** Full-Screen TUI Assignment U2 (`FULL_SCREEN_TUI.md` §9.1, §10, Step 2, §21.7, §22 U2).
> **Reference Plan:** [docs/plans/2026-10-12-tui-u2-controller-skeleton.md](plans/2026-10-12-tui-u2-controller-skeleton.md) @ frozen commit `4badd02fa48a59ce3971f6c1ed1c8ff47bb0d55e`.
> **Root Checkout:** `main`; clean baseline before U2 implementation.

---

## 1. Executive Summary

Assignment U2 establishes the core state controller, background worker architecture, and terminal user interface skeleton for Skill Lens 0.2, fulfilling all architectural mandates from `FULL_SCREEN_TUI.md`:

1. **Textual-Free Session Controller (`skill_lens/tui/session.py`):**
   - Implements the complete state machine described in Section 21.7 without importing Textual.
   - Manages monotonic integer IDs for capture generations and view requests.
   - Provides atomic publication: swapping snapshots clears report caches, invalidates pending report requests, and signals their cancellation events in a single UI-thread transition.
   - Handles cache-hit switching: switching to a cached view argument immediately cancels any in-flight uncached request for that view, setting its cancellation event and rejecting subsequent late success or late error arrivals.
   - Distinguishes expected transient errors (`SnapshotChanged` exposes its retry message without marking failed; `CaptureCancelled` remains quiet) from unexpected internal faults (marks sticky `failed = True`, records memory-only traceback details, and exits 3).

2. **Placeholder App & UI Thread Marshalling (`skill_lens/tui/app.py`):**
   - Subclasses Textual's `App[int]` with `PlaceholderHomeScreen` displaying status text, in-memory error details, and dynamic package version (`__version__` from `skill_lens`).
   - Runs initial capture and refresh in Textual thread workers with `exit_on_error=False`, passing explicit validated `home`, `cwd`, and `event` parameters rather than referencing widget state.
   - Implements a report adapter querying snapshot services (`snapshot_why`, `snapshot_diff`, `snapshot_compare`) in background thread workers.
   - Marshals results to the UI thread via custom Textual messages (`CaptureComplete`, `CaptureFailed`, `ViewReportComplete`, `ViewReportFailed`).
   - **Gated Widget Updates:** Message handlers check `is_closed` and only update widgets when `accept_*` confirms accepted publication; rejected stale or closed callbacks never alter mounted widgets.
   - **Exception Containment:** Overrides Textual's `_handle_exception` to contain unexpected UI faults, setting sticky exit code 3 while suppressing terminal tracebacks.

3. **Owned Event Loop & Prompt Quit Teardown (`skill_lens/tui/__init__.py`):**
   - Exposes lazy `run(home, cwd) -> int` using an owned `asyncio` event loop passed directly to Textual's `app.run(loop=...)`.
   - On shutdown, cancels pending asyncio tasks on the owned loop and gathers them, then closes the loop and restores the caller's preexisting event loop policy without joining `ThreadPoolExecutor` worker threads.
   - Protects the complete lifecycle in `try / finally`, ensuring constructor and cleanup faults bubble to the CLI boundary (exiting 3 with a plain-English message) while closing the controller on every path.

4. **Section 10 Recursive AST Source Guard (`tests/test_tui_read_only.py`):**
   - Recursively inspects the entire `skill_lens/tui/` package using `ReadOnlyASTVisitor`.
   - Strictly prohibits banned root imports (`shutil`, `subprocess`, `tempfile`, `sqlite3`, `socket`, `requests`, `httpx`), Rich/render imports (including aliases and relative imports), OS destructive and process execution calls (`remove`, `unlink`, `rmdir`, `rename`, `replace`, `system`, `popen` and aliases), Path write methods, and terminal writes (`print`, `sys.stdout.write`, `Console.print`).
   - Resolves module-qualified `builtins.open`, `io.open`, `_io.open` and their imported aliases using mode positional index 1, while preserving instance `Path.open` mode positional index 0, preventing filenames from being misread as modes.
   - Rejects positional or keyword write modes, non-literal modes, `*args`, and unresolved `**kwargs` modes. An explicit literal read mode with extra kwargs stays safe: a duplicate `mode` raises `TypeError` before any file can open.
   - 55 valid read patterns (e.g. `open('x')`, `open('data.md', 'r')`, `builtins.open('x', 'rb')`, `io.open('data.md')`, `Path.open('r')`, `os.stat('data.md')`) are tested and confirmed to produce 0 false-positive violations.

5. **Behavioral Mutation Campaign & Target Preservation:**
   - 70 distinct AST mutation cases spanning all five guard categories, aliases, relative render imports, process calls, and open mode unpacking were executed in isolated temporary trees, alongside 3 runtime discriminators (waiting-runner quit watchdog, palette/screenshot write sentinel, and status display precedence). All 73 mutants were detected and killed (0 survivors).
   - An active watchdog proof validates that synchronous `run()` exits cleanly on `q` before blocked worker threads finish.
   - A complete lifecycle test against a synthetic `mock_home` with seeded symlinks and custom permissions confirms 100% byte equality, mode equality, and symlink target preservation across launch, navigation, error injection, refresh, and quit.

---

## 2. Delivered Files & Responsibilities

| File | Changes & Responsibilities |
| --- | --- |
| `skill_lens/tui/__init__.py` | Exported `run(home, cwd) -> int` with owned asyncio event loop, loop restoration, full lifecycle try/finally, and controller closing on all shutdown paths. Helper SHA-256 verified at `633235ce2a0fe9844f7ac8da116e9ae7dfbc8d8d8a531164d48e642d3ed5825a`. |
| `skill_lens/tui/session.py` | Textual-free `SessionController`, `ViewRequest`, `ViewName`, and `ReportValue` types implementing all Section 21.7 state transitions, monotonic IDs, atomic snapshot swap, retry display precedence, selection invalidation via `set_selected_key`, and cache-hit in-flight invalidation. |
| `skill_lens/tui/app.py` | `SkillLensApp(App[int])` and `PlaceholderHomeScreen` with `__version__` display, `q`/`r` bindings, thread workers (`exit_on_error=False`), report adapter for why/diff/compare, gated message handlers, `NoMatches` selector containment, and `_handle_exception` traceback suppression. |
| `tests/test_tui_session.py` | 21 deterministic unit tests covering out-of-order refreshes, out-of-order reports, argument switching invalidation, stale rejection, silent cancellation, sticky exit 3, atomic publication, report-error-during-refresh precedence, and unexpected-fault -> SnapshotChanged -> view fault precedence sequences. |
| `tests/test_tui_app.py` | 27 headless integration tests covering open/quit, why/diff/compare report caching, report worker error handoff, refresh and report worker races with actual old snapshots and late stale errors, in-flight report invalidation via `set_selected_key`, constructor loop closure verification, report error during pending refresh widget precedence, startup and event handler CLI plain-English fault propagation, prompt quit watchdog, closed mounted callback guards, command palette / screenshot neutralization, write spy sentinel, and widget status precedence rendering. |
| `tests/test_tui_read_only.py` | 130 tests covering recursive AST inspection, 70 AST mutation cases, 55 positive read controls with filenames `x` and `data.md`, structural palette and screenshot neutralization, deep package discovery, and target preservation with seeded symlinks and permissions. |
| `tests/test_tui_routing.py` | Updated U1 routing test simulating missing `skill_lens.tui` via targeted `importlib.import_module` failure and `--sandbox` / `mock_home` isolation across all 38 CLI routing tests. |
| `docs/validation/u2/run_mutations.py` | Standalone reproducible runner using verified repo root (`parents[3]`), executing the 73-case mutation campaign (70 AST guard mutations + 1 waiting-runner quit watchdog mutation + 1 palette/screenshot write discriminator mutation + 1 status display precedence discriminator mutation) with dynamic summary and nonzero exit on survivors. |
| `docs/validation/u2/mutation_records.json` | Machine-readable receipt of all 73 killed mutants with platform metadata and execution timings. |
| `docs/validation/u2/MUTATION_RESULTS.md` | Audit table documenting all 73 mutations, snippets, targeted assertions, outcomes, and log paths. |
| `docs/validation/u2/logs/` | Persisted execution logs for control, mutant detection, and clean restore across all 73 mutations. |
| `docs/TUI_U2_WALKTHROUGH.md` | This document: comprehensive audit walkthrough of Assignment U2. |

---

## 3. Session Controller State Machine (§21.7)

The `SessionController` manages UI state independently of Textual:

```text
               ┌────────────────────────────────────────────────────────┐
               │                                                        │
               ▼                                                        │
         [ Initializing ]                                               │
               │                                                        │
               │ request_refresh() -> gen 1                             │
               ▼                                                        │
          [ Loading ] <──────────────────────────┐                      │
          (pending_gen)                          │                      │
           /         \                           │                      │
Capture   /           \  CaptureFailed           │                      │
Complete /             \                         │                      │
        ▼               ▼                        │                      │
    [ Ready ]       [ Error ] ──(SnapshotChanged)┘                      │
  (current snap)   (sticky failed                │ (r pressed: gen n+1) │
        │           details in mem)              │                      │
        │                  │                     │                      │
        └──────────────────┴─────────────────────┘                      │
                           │                                            │
                           │ close()                                    │
                           ▼                                            │
                       [ Closed ] ──────────────────────────────────────┘
                    (events set,
                   requests cancelled)
```

### 3.1 Monotonic IDs & Generation Invalidation
- Capture generation counter `_next_generation` begins at 1 and increments on every `request_refresh()`.
- Request counter `_next_request_id` begins at 1 and increments on every `request_view()`.
- When generation $N$ completes while generation $N+1$ is pending, generation $N$ is rejected immediately.
- When generation $N+1$ completes, it publishes atomically: `current` becomes snapshot $N+1$, `pending_generation` becomes `None`, `cache` is cleared, and all in-flight report cancellation events are set.

### 3.2 Cache-Hit Argument Switching Invalidation
When view arguments $A$ are cached, starting uncached request $B$ places $B$ in `active_requests`. If the user immediately navigates back to cached $A$:
1. `request_view(view, A)` detects a cache hit and returns `(None, None, cached_report)`.
2. It detects that active request $B$ is superseded, cancels $B$'s cancellation event (`event.set()`), and removes $B$ from `active_requests`.
3. If $B$'s worker finishes late (either with success or error), `accept_view_result` and `accept_view_error` reject $B$ because $B$'s request ID does not match active requests.
4. $B$'s late arrival does not enter the cache and does not mark the session failed.

### 3.3 Display Precedence & Sticky Failure Contract (§21.7)
The state machine balances competing display priorities with strict error preservation:
1. **Status Property Ordering (`retry -> failed -> pending -> ready -> idle`):**
   - **`retry`:** Expected concurrency retries (`SnapshotChanged`) take first precedence so the user sees `"Files changed while scanning. Press r to retry."`, even if an earlier fault occurred.
   - **`failed`:** Accepted unexpected internal faults take precedence over in-flight background operations (`pending_generation`), ensuring that when a report or capture worker encounters an unexpected fault, the error panel and traceback are immediately displayed rather than hidden behind `"Scanning skills..."`.
   - **`pending`:** While normal unfailed refreshes are running, `"loading"` is returned to show `"Scanning skills..."`.
   - **`ready`:** When a snapshot is published and no faults are active, `"ready"` displays skill counts.
2. **Sticky Failure Exit Code:** Any accepted unexpected internal fault permanently marks `is_failed = True` so that closing the session returns exit code 3 (`ExitCode.INTERNAL`), regardless of subsequent retry refreshes.
3. **Clearing Older Retry on Fresh Faults:** When a later unexpected view or capture fault is accepted, older retry messages are explicitly cleared (`retry_message = None`), immediately restoring the error panel for the newest fault.
4. **Stale Error Rejection:** Stale or out-of-order errors (from superseded generations or invalidated view requests) return `False` and have zero effect on `failed`, `last_error_details`, or `retry_message`.
5. **Concrete Regressions:** Verified by `test_unexpected_fault_then_snapshot_changed_then_view_fault_sequence`, `test_report_error_during_refresh_regression`, and `test_headless_report_error_during_refresh_widgets`.

---

## 4. Textual App & Headless Worker Architecture

### 4.1 Thread Workers & UI Marshalling
- Workers use Textual's `@work(thread=True, exit_on_error=False)`.
- Workers receive explicit `home: Path`, `cwd: Path`, and `event: threading.Event`. They do not access UI widgets or app state.
- Worker completion posts messages (`CaptureComplete`, `CaptureFailed`, `ViewReportComplete`, `ViewReportFailed`) to the Textual message pump.
- Message handlers run on the UI thread:
  ```python
  def on_capture_complete(self, message: CaptureComplete) -> None:
      if self.controller.is_closed:
          return
      if self.controller.accept_capture(message.snapshot, message.generation):
          self._update_ui()
  ```
  This ensures that rejected, stale, or post-close callbacks never update mounted widgets.

### 4.2 Discriminating Watchdog & Prompt Quit
To prove that `tui.run` does not block waiting for worker threads on quit:
- `test_synchronous_run_quit_proof_before_blocked_capture_release` starts a worker that blocks on `release_capture.wait()`.
- An active watchdog timer starts with a 2.0s deadline.
- When `q` is pressed, `tui.run` returns promptly (< 0.1s).
- The test asserts:
  - `assert not watchdog_fired.is_set()` (watchdog never fired).
  - `assert not release_capture.is_set()` (run returned while worker was still blocked).
- In a disposable mutant where `run()` was modified to wait on threads, the worker blocked, the watchdog fired at 2.0s setting `release_capture`, and the test failed with an `AssertionError`.
- In `finally`, `release_capture.set()` and `worker_finished.wait(timeout=5.0)` ensure background threads terminate cleanly before fixture HOME cleanup.

### 4.3 Routing & Module Import Isolation (Hang Prevention)
In Assignment U1 tests, `test_tui_missing_u2_module_with_textual_present_exits_3_no_traceback` asserted that when `skill_lens.tui` is absent, the CLI exits with code 3 without traceback. When U2 introduced `skill_lens/tui/` on disk, an unpatched import resolved the real module and started an interactive non-headless Textual app waiting on stdin.
- **Root Cause:** Deleting `skill_lens.tui` from `sys.modules` allowed Python to re-import the package from the newly created disk directory.
- **Resolution:** Explicitly monkeypatched `importlib.import_module` to raise `ModuleNotFoundError` targeted strictly to `"skill_lens.tui"`, combined with `mock_home` and `--sandbox` fixtures across all launcher routing tests.
- **Result:** The import-fault / exit 3 / no-traceback contract is verified in <0.02s without starting an interactive UI or reading live skill roots.

### 4.4 Inherited Command Palette & Screenshot Write Neutralization (§10)
Textual's base `App` enables a command palette by default (`ENABLE_COMMAND_PALETTE = True`) accessible via `ctrl+p`. Among its built-in system commands is `Screenshot`, routing to `deliver_screenshot` / `save_screenshot` which writes SVG files to disk. Because inherited framework writes cannot be detected by source AST analysis alone, `SkillLensApp` explicitly neutralizes these routes:
1. **Disabled Palette:** `ENABLE_COMMAND_PALETTE: ClassVar[bool] = False` and `COMMANDS: ClassVar[set[Any]] = set()`.
2. **Action Neutralization:** Overrides `action_command_palette` as a no-op, preventing `ctrl+p` or action dispatch from opening the palette.
3. **Empty System Commands:** Overrides `get_system_commands` to return an empty iterable `()`, preventing discovery of `Screenshot` or other inherited commands.
4. **I/O Neutralization:** Overrides `action_screenshot`, `deliver_screenshot`, `save_screenshot`, `deliver_binary`, and `deliver_text` as no-ops returning `None` or `""`.
5. **Discriminator & Write Sentinel Verification:** Verified by real headless key tests (`test_command_palette_and_ctrl_p_inaccessible`), an active write spy sentinel intercepting `builtins.open` (`test_neutralized_screenshot_methods_no_write_with_sentinel`), and discriminating mutation proofs (`test_discriminating_mutation_enabled_palette_or_unneutralized_screenshot_fails` and mutation campaign case 50).

### 4.5 Startup & Event Handler Plain-English CLI Fault Propagation
When an unhandled exception occurs inside Textual's event loop (such as `SkillLensApp.on_mount` raising during startup, or an action handler crashing):
1. Textual invokes `SkillLensApp._handle_exception(error)`, which stores `self._exception = error` and exits the app with return code 3.
2. `skill_lens.tui.run()` checks `getattr(app, "_exception", None)`. If present, it executes its `finally` teardown (closing the controller and cancelling/gathering owned event loop tasks) and raises `unhandled_exc`.
3. In `skill_lens.cli._launch_tui`, the exception is caught, formatted as a plain-English error message (`Error: Failed to start the terminal UI: <message>`), and emitted to `error_console` (stderr) before raising `typer.Exit(code=3)` without any terminal traceback.
4. By contrast, background worker errors that are handled in-app and displayed via the TUI fault panel leave `app._exception = None`, so quitting with `q` exits code 3 cleanly without duplicate stderr output.
5. Verified by `test_startup_handler_fault_via_cli` and `test_actual_textual_event_handler_fault_via_cli`.

### 4.6 Real-Worker Out-of-Order Races & Late Event Rejection
`test_real_worker_refresh3_finishes_before_refresh2_publishes_newest` and `test_real_worker_refresh3_finishes_before_refresh2_stale_error_rejected` deterministically verify out-of-order worker arrivals with actual snapshots and errors:
1. **Late Successful Snapshot:** In the refresh 3 before 2 test, the controlled worker verifies that generation 2 received a valid cancellation predicate (initially `False`), waits for generation 3 to trigger cancellation, and then deliberately produces an actual completed `SessionSnapshot` for generation 2. When released after generation 3 has published, generation 2's late `CaptureComplete` message is safely rejected by the controller, leaving generation 3 as current.
2. **Late Stale Error:** In the stale error test, generation 2 raises a late background error after generation 3 has published. The controller rejects the stale error, preserving generation 3, leaving `failed = False`, and allowing the user to quit cleanly with exit code 0.
3. **Late Report Arrival on Selection Change:** In `test_real_worker_selection_change_invalidates_in_flight_report`, the worker produces a valid `ResolutionReport` using the real `snapshot_why` service. Changing selection clears the active request and cancels its event before the worker completes; upon release, the controller safely rejects the late report without error or cache pollution.
4. All worker race tests run against synthetic `mock_home` and release all barrier events in `finally` blocks, eliminating timing-only arrival assumptions.

---

## 5. Read-Only AST Guard & Mutation Evidence (§10)

`ReadOnlyASTVisitor` recursively scans all Python files in `skill_lens/tui/` and asserts 0 violations.

### 5.1 Guard Coverage Matrix

| Category | Targeted Rules & Banned Operations | Detection Mechanism |
| --- | --- | --- |
| **1. Imports** | `shutil`, `subprocess`, `tempfile`, `sqlite3`, `socket`, `requests`, `httpx`, `rich`, `skill_lens.render` | `visit_Import` and `visit_ImportFrom` root and submodule checks, including aliases and relative imports (`..render`). |
| **2. OS Calls** | `os.remove`, `unlink`, `rmdir`, `rename`, `replace`, `system`, `popen` | Alias tracking (`os as custom_os`, `from os import system as sys_exec`) and attribute call checks. |
| **3. Path Writes** | `write_text`, `write_bytes`, `unlink`, `mkdir`, `touch`, `rename`, `rmdir` | Direct method call checks on any instance attribute. |
| **4. Open Modes** | Write modes `"w"`, `"a"`, `"x"`, `"+"`; non-literal or dynamic modes; `*args` / `**kwargs` unpacking | Keyword argument `mode=...`, positional arguments, constant literal checks, module vs instance mode positional index resolution (1 vs 0), and unpacking checks. |
| **5. Terminal Writes** | `print(...)`, `sys.stdout.write`, `sys.stderr.write`, `Console.print` | Bare call tracking, `print` alias tracking (`from builtins import print as p`), stream alias tracking, and attribute inspection. |

### 5.2 Mutation Campaign Results
The complete mutation campaign defined in `docs/validation/u2/run_mutations.py` was executed across 73 distinct cases (70 Section 10 AST guard mutations across imports, aliases, OS destructive calls, OS process execution calls, Path write methods, and open mode unpacking, plus 1 waiting-runner quit watchdog mutation, plus 1 command palette & screenshot write discriminator mutation, plus 1 status display precedence discriminator mutation):
- Clean control: verified clean baseline / non-blocking prompt quit / zero writes / retry display precedence.
- Mutant injection: detected matching expected failure pattern.
- Clean restore: verified clean restoration.
- Result: **73/73 killed, 0 survivors**. Audit receipts are persisted in `docs/validation/u2/MUTATION_RESULTS.md` and `docs/validation/u2/logs/`.

---

## 6. Target Directory Preservation Suite

`test_synthetic_target_preservation_across_lifecycle` tests target immutability:
1. Materializes scenario `claude_personal_beats_project` under `mock_home`.
2. Seeds a synthetic relative symlink (`symlink_doc.txt -> SKILL.md`) and custom file mode (`0o640`).
3. Takes an initial snapshot of all relative paths, bytes, file permissions (`st_mode`), and symlink targets.
4. Executes the full TUI lifecycle:
   - Initial capture scan
   - Key navigation (`down`, `up`)
   - Refresh (`r`)
   - Report query (`why`)
   - Error injection and status display
   - Retry refresh
   - Normal quit (`q`)
5. Takes a post-lifecycle snapshot and verifies 100% key set equality, byte equality, mode equality, and symlink target equality.

---

## 7. Verification Gates

All four repository verification gates were executed and passed cleanly:

1. **Test Suite & Coverage:**
   ```bash
   .venv/bin/pytest --cov=skill_lens
   # 785 passed, 1 skipped (case-insensitive filesystem test). Coverage: 94.30% (Gate: >=90.0%).
   ```
2. **Type Checker:**
   ```bash
   .venv/bin/mypy
   # Success: no issues found in 34 source files (strict mode).
   ```
3. **Linter:**
   ```bash
   .venv/bin/ruff check .
   # All checks passed!
   ```
4. **Formatter:**
   ```bash
   .venv/bin/ruff format --check .
   # 117 files already formatted in the final delivery check.
   ```

---

## 8. Limitations & Boundaries

1. **Read-Only Target Execution:** Skill Lens never modifies user skills. The TUI is purely an observational lens.
2. **Uninterruptible OS File Reads:** Cancellation signals worker threads via `threading.Event`, allowing them to abort between steps. An in-progress blocking kernel read cannot be forcibly aborted from Python user-space; workers terminate upon completion of that read. Textual thread workers run in standard `ThreadPoolExecutor` threads. Teardown of the owned asyncio event loop avoids joining them so `tui.run()` returns promptly on `q`, but final interpreter process exit can wait for thread termination if an uninterruptible OS read is in progress.
3. **Scope Boundary:** Assignment U2 provides the session controller, background worker adapter, and placeholder home screen. Future assignments are Home browsing (U3), Why (U4), Diff and JSON (U5), Agents and Compare (U6), Doctor (U7), polish including help (U8), and release preparation (U9).
4. **Source Guard Limits:** The syntax checker covers the named operations, imports and aliases. It does not prove that every indirect dependency call is read-only; reflection and unknown dynamic receivers require separate review. Inherited Textual screenshot and file-delivery routes receive direct behavioral checks in addition to the source guard.

## 9. Independent Review and Correction Record

Muse passed the first final review. MiMo required a correction to the checker:
module-qualified `builtins.open` and `_io.open` were treated as Path instance
calls, so the filename could be mistaken for the mode. The coordinator reproduced
both the missed write and the false-positive read before Gemini corrected them.
The expanded campaign detects 73/73 mutations and 55 positive read controls pass.

Gemini also strengthened the actual worker error, Diff/Compare and selection
handoff tests, and asserted owned-loop closure after a constructor fault.
The selection test now calls the public `set_selected_key` method. All production
files remained unchanged, preserving the synchronous quit proof's source hash.
The coordinator independently reran all four gates: 785 passed, 1 existing
filesystem skip, 94.30% coverage, strict mypy over 34 files, and clean ruff checks.
Fresh reproduction and gate logs are in [coordinator/round2](validation/u2/coordinator/round2).
The original reports and integrity receipt remain in [coordinator](validation/u2/coordinator).
Fresh targeted Muse and MiMo reviews both passed with no blockers. The coordinator
verified identical before/after hashes for all 310 reviewed files and confirmed
all nine owned U2 threads idle with their runs terminal before acceptance.
Full round-2 reports and the integrity receipt are in
[coordinator/round2](validation/u2/coordinator/round2).

The coordinator accepts U2 within the frozen scope. Medium effort was requested
for the bounded follow-up under the user's effort policy; the native creation
receipts corroborate the configured model/provider/options, while actual
provider execution of those options and model-family identity stay unverified.
The first broad reviews retain their verdicts for unchanged production code.

MiMo's non-blocking suggestion to use bounded waits instead of a single pilot
pause in the fast report adapter test is deferred as future test hardening; the
current actual-worker checks passed, and no timing failure was reproduced.
Its receipt suggestion is addressed: guard_reproduction.json now includes the
exact source snippets used by the coordinator, alongside the observed outcomes.
U3 Home browsing remains the next assignment and has not started.
The final four-gate delivery check also passed; logs are retained in
[coordinator/final](validation/u2/coordinator/final).
