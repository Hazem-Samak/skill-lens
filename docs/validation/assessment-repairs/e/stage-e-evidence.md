# Stage E Implementation Evidence — Command Boundaries and Compatibility

**Stage:** Stage E (F08, F09, F14, R03)  
**Date:** 15 October 2026  
**Base Commit:** `f0cf52684dfcc638a2f5a49509a5be80faddc951`  
**Implementer:** Antigravity `gemini-3.8-flash-high`  
**Status:** Verification complete; all gates clean; 10 worker-selected controls + 2 coordinator guard mutations killed (12/12).

---

## 1. Summary of Repairs

### F08 — Explicit interactive TUI launch requires terminal streams
- **Defect:** Bare invocation checked both input and output interactivity, but explicit `skill-lens tui` only checked Textual availability. When invoked without an interactive terminal (such as piped stdin/stdout in scripts or automated runners), Textual hung waiting for terminal events (timed out at 2.0s in baseline reproduction).
- **Repair:** In `skill_lens/cli.py`, `tui()` enforces deterministic validation ordering:
  1. If Textual is not available, emit the existing install hint to stderr and exit 2 (`ExitCode.USAGE`).
  2. If either `sys.stdin` or `sys.stdout` is non-interactive (`not (_stream_isatty(sys.stdin) and _stream_isatty(sys.stdout))`), print `"Error: The terminal UI requires an interactive terminal."` to stderr with `markup=False, highlight=False` and exit 2 (`ExitCode.USAGE`).
  3. Never import or call the TUI runner when streams are non-interactive.
  4. Bare fallback help (exit 0) on non-interactive streams and `--plain` remain intact.
  5. Internal headless runner (`skill_lens.tui.run(..., headless=True, auto_pilot=...)`) remains fully usable without a terminal.

### F09 — Shared distinct known agent validation for comparisons
- **Defect:** `compare --agent claude --agent claude` was previously accepted by the CLI, returning an all-shared report and exit 0, while `snapshot_compare(..., "claude", "claude")` rejected self-comparison with `ValueError`.
- **Repair:**
  1. Added `validate_compare_agents(agent_a, agent_b, agents)` in `skill_lens/core/compare.py`. It requires two distinct known agents, validating both agent IDs against the registry before performing any filesystem walk, discovery, or I/O.
  2. Unknown agent IDs raise `KeyError(f"unknown agent '{agent_id}'. Known agents: {known}")`.
  3. Comparing an agent with itself raises `ValueError(f"cannot compare agent '{agent_a}' with itself")`.
  4. Both `build_compare_report` and `run_compare` in `skill_lens/core/compare.py`, and `snapshot_compare` in `skill_lens/core/snapshot.py`, share this validation.
  5. The CLI `compare` command catches `ValueError` as well as `KeyError`, emitting `Error: <msg>` to stderr with exit 2. In `--json` mode, stdout remains completely empty.
  6. Normal and reversed comparisons (`A vs B` and `B vs A`) preserve exact shapes, values, and mirror relations.

### F14 — Literal CLI error formatting without Rich markup interpretation
- **Defect:** Dynamic error messages in `skill_lens/cli.py` (`why` and `compare`) interpolated user-controlled agent strings into Rich markup strings (`f"[red]Error:[/red] {exc.args[0]}"`). When user inputs contained closing tags such as `[/]` or formatting brackets like `[bold]`, Rich crashed with `MarkupError` (exit code 1) instead of the intended usage error (exit code 2).
- **Repair:**
  1. In `skill_lens/cli.py`, updated `why()` and `compare()` exception handlers to emit literal error strings to `error_console`:
     ```python
     error_console.print(
         f"Error: {exc.args[0]}",
         soft_wrap=True,
         markup=False,
         highlight=False,
     )
     ```
  2. Sibling handlers in `cli.py` were audited; all error paths now consistently pass `soft_wrap=True, markup=False, highlight=False`.
  3. Inputs like `[/]`, `[red]`, `[link=...]` produce clean, literal stderr output and exit 2. No tracebacks are emitted, stdout remains unpolluted (empty in `--json`), and the known-agents list remains intact.

### R03 — Event loop compatibility without deprecated asyncio policy call
- **Defect:** `skill_lens/tui/__init__.py` called `asyncio.get_event_loop_policy().get_event_loop()`. On Python 3.14+, `asyncio.get_event_loop_policy` emits a `DeprecationWarning` slated for removal in Python 3.16.
- **Repair:**
  1. Replaced `asyncio.get_event_loop_policy().get_event_loop()` with standard `asyncio.get_event_loop()`.
  2. When no event loop exists in the thread, `asyncio.get_event_loop()` raises `RuntimeError` (caught and handled as `prev_loop = None`), avoiding deprecated policy calls.
  3. When an existing non-running event loop was set by the caller, `asyncio.get_event_loop()` returns that exact loop, and the `finally` block restores it via `asyncio.set_event_loop(prev_loop)`.
  4. When an existing closed loop was set, it is not restored as active (event loop is set to `None`).
  5. When constructor, execution, or cleanup fails, the owned loop is closed and the previous loop is safely restored.
  6. Does not call `asyncio.run` or `Runner`, preserving synchronous prompt shutdown without blocking on background executor worker joins.

---

## 2. Pre-Council Correction Batch (Round 1)

Following coordinator inspection, three batched corrections were completed:

1. **Test Isolation (`test_f09_reversed_comparisons_retain_shapes_and_mirrors`):**
   - Switched fixture from unisolated `tmp_path` to standard `mock_home: Path`, redirecting `HOME` to a throwaway fixture directory and establishing sandbox protection.
   - Added synthetic project cwd (`mock_home / "project"`) matching the scenario layout.
   - Preserved `claude_personal_beats_project` scenario content while populating codex, shared, and diverged skills so that both reports are guaranteed non-empty and all four mirror relations (`SHARED`, `ONLY_A`, `ONLY_B`, `DIVERGED`) are explicitly verified in both directions.
   - Confirmed single-test execution (`pytest tests/test_stage_e_repairs.py::test_f09_reversed_comparisons_retain_shapes_and_mirrors -v`) passes cleanly without reading ambient `HOME`.

2. **Strengthened Closed-Prior Loop Guard (`test_r03_tui_run_handles_closed_prior_loop`):**
   - Replaced weak assertion (`assert current is not closed_loop or current.is_closed()`), which previously accepted the closed loop being restored.
   - Added `spy_new_event_loop` to prove the owned loop created by `tui.run` was properly closed (`assert len(created_loops) == 1 and created_loops[0].is_closed()`).
   - Replaced getter assertion with `with pytest.raises(RuntimeError, match="no current event loop"): asyncio.get_event_loop()`, proving that the closed prior loop is not restored as active and no current event loop remains in the thread.

3. **Strengthened No-Prior Loop Guard (`test_r03_tui_run_no_prior_loop`):**
   - Replaced weak assertion (`assert current.is_closed() or not current.is_running()`), which previously accepted a leaked closed owned loop.
   - Added `spy_new_event_loop` to prove the owned loop was closed.
   - Added `with pytest.raises(RuntimeError, match="no current event loop"): asyncio.get_event_loop()`, proving the owned loop is not leaked and no loop is left in the thread.

4. **Killed Coordinator Guard Mutations:**
   - Evaluated both mutations in verified disposable source copies (`/Users/corvette/.t3/userdata/skill-lens-repair-checkpoints/2026-10-15-stage-e-work/disposable-mutations/`) across both Python 3.11 and Python 3.14.
   - Demonstrated exact `clean: 0 -> mutant: 1 (Killed) -> restored: 0` lifecycle on both interpreters.

---

## 3. Verification and Gates

### Primary Environment (Python 3.11.16)
- **Pytest:** **967 passed, 1 skipped** (case-insensitive volume check) in 53.22s.
- **Coverage:** **90.53%** overall statement/branch coverage (threshold: 90.0%).
- **Mypy:** 36 source files checked; **0 type errors** found (`strict = true`).
- **Ruff:** Lint clean (`ruff check .`), format clean (`ruff format --check .`, 134 files checked).

### Python 3.14 Environment (CPython 3.14.7)
- Executed in external disposable virtualenv (`py314-disposable-venv`) targeting `/Users/corvette/.local/bin/python3.14`.
- **Targeted suite (`tests/test_stage_e_repairs.py`):** **37 passed** in 0.89s with zero deprecation warnings under `-W error::DeprecationWarning:skill_lens.tui`.

---

## 4. Disposable Source Mutation Results

Mutations were executed on verified disposable source copies in an isolated directory (`/Users/corvette/.t3/userdata/skill-lens-repair-checkpoints/2026-10-15-stage-e-work/disposable-mutations/`). The live repository checkout remained unmutated.

*Disclaimer: These receipts document targeted mutations for specific Stage E repairs. They do not constitute an exhaustive mutation score or claim all arbitrary guards across the codebase are proved.*

| ID | Classification | Guard Protected | File | Clean (3.11 / 3.14) | Mutant (3.11 / 3.14) | Restored (3.11 / 3.14) | Result |
|---|---|---|---|---|---|---|---|
| **M01** | Worker-selected control | F08 explicit tui stream interactivity check | `skill_lens/cli.py` | PASS (0 / -) | FAILED (1 / -) | PASS (0 / -) | KILLED |
| **M02** | Worker-selected control | F08 explicit tui requires BOTH stdin & stdout | `skill_lens/cli.py` | PASS (0 / -) | FAILED (1 / -) | PASS (0 / -) | KILLED |
| **M03** | Worker-selected control | F09 validate_compare_agents ValueError on self-compare | `skill_lens/core/compare.py` | PASS (0 / -) | FAILED (1 / -) | PASS (0 / -) | KILLED |
| **M04** | Worker-selected control | F09 build_compare_report enforces shared validation | `skill_lens/core/compare.py` | PASS (0 / -) | FAILED (1 / -) | PASS (0 / -) | KILLED |
| **M05** | Worker-selected control | F09 CLI compare catches ValueError and exits 2 | `skill_lens/cli.py` | PASS (0 / -) | FAILED (1 / -) | PASS (0 / -) | KILLED |
| **M06** | Worker-selected control | F14 why handler literal printing without Rich markup | `skill_lens/cli.py` | PASS (0 / -) | FAILED (1 / -) | PASS (0 / -) | KILLED |
| **M07** | Worker-selected control | F14 compare handler literal printing without Rich markup | `skill_lens/cli.py` | PASS (0 / -) | FAILED (1 / -) | PASS (0 / -) | KILLED |
| **M08** | Worker-selected control | R03 tui.run avoids deprecated policy lookup (Py 3.14) | `skill_lens/tui/__init__.py` | PASS (- / 0) | FAILED (- / 1) | PASS (- / 0) | KILLED |
| **M09** | Worker-selected control | R03 tui.run does not use get_running_loop (preserves borrowed) | `skill_lens/tui/__init__.py` | PASS (0 / -) | FAILED (1 / -) | PASS (0 / -) | KILLED |
| **M10** | Worker-selected control | R03 tui.run restores borrowed event loop in finally | `skill_lens/tui/__init__.py` | PASS (0 / -) | FAILED (1 / -) | PASS (0 / -) | KILLED |
| **M11** | Coordinator guard mutation | R03 closed prior event loop is not restored as active | `skill_lens/tui/__init__.py` | PASS (0 / 0) | FAILED (1 / 1) | PASS (0 / 0) | KILLED |
| **M12** | Coordinator guard mutation | R03 owned loop is closed and not leaked when no prior loop | `skill_lens/tui/__init__.py` | PASS (0 / 0) | FAILED (1 / 1) | PASS (0 / 0) | KILLED |

Detailed receipts with pre/post SHA256 hashes, commands, diffs, and retained failure logs are preserved in `docs/validation/assessment-repairs/e/mutation-receipts.json`.


## 5. Independent coordinator verification before council

After the test-proof correction, the coordinator directly reran all four project gates: 967 passed/one filesystem skip, 90.53% combined coverage, mypy clean on 36 files, Ruff lint/format clean on 134 files. The Python 3.14 targeted suite passed 37 tests. Logs and commands are in `coordinator/gates.json` and adjacent files. No product/test changes occurred during verification.

The coordinator independently executed 13 distinct production mutations in a freshly copied source tree, with 15 interpreter executions because the two repaired loop guards were tested on both Python 3.11 and 3.14. Every clean/mutant/restored sequence returned 0/1/0 with matching import provenance/source hashes and intended assertion failures. Exact mutation diffs, commands and logs are in `coordinator/mutations.json` and adjacent logs. These are independent coordinator controls, not a relabeling of the worker receipts above, and do not establish an exhaustive mutation score.

Direct subprocess reproductions now give exit 2, empty stdout and plain stderr for piped explicit TUI, duplicate comparison and markup-like unknown agents. The isolated reversed-comparison test passes independently with mock HOME and explicit non-empty coverage of all four mirror relations.

Loop claim qualification: Python 3.14 raises when no loop is current. On older supported Pythons, a fresh thread/main-thread policy can implicitly create a loop; this patch preserves previous behavior there. The no-prior regression explicitly starts with `set_event_loop(None)` and proves no current loop afterward. Exact borrowed non-running loop restoration is separately guarded. Worker labels naming coordinator-designed mutations describe who selected the defects; the independent coordinator executions are the separately retained receipts above.
