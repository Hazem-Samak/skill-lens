# Full Screen TUI Implementation Walkthrough

This document records the step-by-step walkthrough of implementing the Full-Screen TUI (Skill Lens 0.2.0) as specified in `FULL_SCREEN_TUI.md`.

---

## 1. Baseline Verification

Before starting any code changes, the entire test suite and all quality gates were executed against the initial repository state (commit `09d5f62`):

- **Test Suite:** 471 tests passing (`uv run pytest --cov=skill_lens`).
- **Branch Coverage:** 92.67% (above the 90.0% coverage floor).
- **Type Checking:** Strict `mypy` passed with zero errors across 25 source files.
- **Code Style & Formatting:** `ruff check .` and `ruff format --check .` passed cleanly.

---

## 2. Phase P1 — Settings Robustness

### Problem
In `skill_lens/core/resolver.py`, `_load_disabled_overrides()` parsed settings JSON files (such as `~/.claude/settings.json`) using `json.loads()`. If the file contained a non-dictionary top-level value (for example `[]`, `null`, `"string"`, or `42`), calling `data.get(agent.disabled_key)` resulted in an unhandled `AttributeError`, crashing the skill resolution engine.

### Implementation Steps
1. **Reproduction Tests:** Added `test_non_object_settings_are_ignored` to `tests/test_phase2_gate.py` parametrized with `"[]"`, `"null"`, `'"string"'`, and `"42"`. Verified that all 4 test cases failed with `AttributeError`.
2. **Code Fix:** Added a defensive check `if not isinstance(data, dict): return set()` in `skill_lens/core/resolver.py` inside `_load_disabled_overrides()` before accessing `data.get()`.
3. **Verification:**
   - All 4 test cases passed.
   - Valid settings (e.g. `{"skillOverrides": {"legacy": false}}`) continued to disable skills as expected.
   - Full suite passed: 475 tests, 92.68% branch coverage, strict `mypy` clean, `ruff` clean.
4. **Git Commit:** Committed as `c2ff913` (`fix(resolver): ignore non-object settings JSON (P1)`).

### Files Changed
- `skill_lens/core/resolver.py`: Added top-level `dict` check in `_load_disabled_overrides()`.
- `tests/test_phase2_gate.py`: Added `test_non_object_settings_are_ignored()`.

---

## 3. Phase P2 — Lockfile Decoding Robustness

### Problem
In `skill_lens/core/system.py`, `read_json_guarded()` reads JSON files defensively. However, `path.read_text(encoding="utf-8")` was executed without catching `UnicodeDecodeError` (which inherits from `ValueError`, not `OSError`). If an installer lockfile (`~/.agents/.skill-lock.json`) contained invalid UTF-8 bytes, `UnicodeDecodeError` escaped unhandled, causing `doctor` commands to crash rather than reporting a diagnostic warning.

### Implementation Steps
1. **Reproduction Tests:**
   - Added `test_non_utf8_lock_reports_invalid_json` in `tests/test_doctor.py`, writing non-UTF-8 bytes (`b"\xff\xfe\x00\x00not utf-8"`) to the lockfile path and asserting that `read_json_guarded` returns `(None, ERR_NOT_JSON)` and `build_doctor_report` produces a `Severity.WARNING` finding with `detail="not_json"`.
   - Verified that the test failed before the fix with `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte`.
   - Added an assertion in `tests/test_phase4_gate.py` under `test_read_json_guarded_never_raises()`.
2. **Code Fix:** Added `except UnicodeDecodeError: return None, ERR_NOT_JSON` at the file-read boundary in `read_json_guarded()` in `skill_lens/core/system.py`.
3. **Verification:**
   - All 476 tests passed.
   - Total branch coverage remained 92.68% (threshold 90.0%).
   - Strict `mypy` clean across all files.
   - `ruff check` and `ruff format --check` clean.
4. **Git Commit:** Committed as `b11e93d` (`fix(system): catch UnicodeDecodeError when reading JSON files (P2)`).

### Files Changed
- `skill_lens/core/system.py`: Caught `UnicodeDecodeError` in `read_json_guarded()`.
- `tests/test_doctor.py`: Added `test_non_utf8_lock_reports_invalid_json()`.
- `tests/test_phase4_gate.py`: Added invalid UTF-8 assertion to `test_read_json_guarded_never_raises()`.

---

## 4. Phase P3 — Cost and Capture-Scope Review

### Objective
As required by `FULL_SCREEN_TUI.md` §9.2 and §22 before embarking on Step 0 contracts (C1–C5), execute a reproducible throwaway probe against synthetic test fixtures of 600+ skills to measure:
- Execution time of First Discovery, Byte Capture, Second Discovery (validation), and Report construction.
- Retained memory and peak memory (including holding an old snapshot during background refresh).
- Feasibility of Q9 Full Capture vs. a Selective Retention candidate.

### Implementation Steps
1. **Probe Script (`docs/p3_cost_probe.py`):**
   - Implemented synthetic fixture generators for:
     - **Scenario A (Mostly Unique):** 620 skills (500 shared in `.agents/skills`, 50 in Claude, 50 in Codex, 30 symlinks, 20 malformed, nested scripts, binary image assets up to 50 KiB).
     - **Scenario B (Heavily Duplicated):** 615 skills (200 distinct skill names duplicated across 3 agent roots = 600 copies, plus 15 malformed skills and binary assets up to 80 KiB).
   - Measured timings with `time.perf_counter()` and memory with `tracemalloc`.
   - Simulated background refresh (allocating a new session snapshot while retaining the old one).
2. **Execution & Results:**
   - Ran probe on macOS (Darwin arm64, Python 3.11.16).
   - Saved full report to `docs/P3_COST_PROBE_RESULTS.md`.
   - **Key Findings:**
     - Full byte capture of all files across 600+ skills took only **~58 ms (Scenario A)** and **~79 ms (Scenario B)**.
     - Total retained memory for captured files was only **1.09 MiB (Scenario A)** and **2.00 MiB (Scenario B)**.
     - Peak memory during refresh while retaining the old snapshot was only **5.81 MiB (Scenario A)** and **3.94 MiB (Scenario B)**.
     - Selective retention saved only ~22 ms of capture time while introducing complex conditional caching logic and view-drift risks.
3. **Architectural Decision Gate:**
   - Full Capture (Q9) is fast, lightweight (<10 MiB peak memory), and completely practical.
   - Retain the §21 Full Capture specification verbatim without redesign or scope reduction.
4. **Verification:**
   - `docs/p3_cost_probe.py` conforms strictly to `ruff check` (100 char line limit) and `ruff format`.
   - All 476 existing tests pass, 92.68% coverage, strict `mypy` clean.

### Files Created
- `docs/p3_cost_probe.py`: Reproducible synthetic benchmark harness.
- `docs/P3_COST_PROBE_RESULTS.md`: Detailed measurement tables and architectural decision record.

---

## 5. Summary of Files Created and Modified

| File | Action | Purpose |
| --- | --- | --- |
| `skill_lens/core/resolver.py` | Modified | Added top-level type validation in `_load_disabled_overrides()`. |
| `tests/test_phase2_gate.py` | Modified | Added tests for non-object settings JSON. |
| `skill_lens/core/system.py` | Modified | Added `UnicodeDecodeError` guard in `read_json_guarded()`. |
| `tests/test_doctor.py` | Modified | Added test for invalid UTF-8 lockfile warning in `doctor`. |
| `tests/test_phase4_gate.py` | Modified | Added test ensuring `read_json_guarded` never raises on non-UTF-8 bytes. |
| `docs/p3_cost_probe.py` | Created | Reproducible synthetic 600+ skill probe harness for §9.2. |
| `docs/P3_COST_PROBE_RESULTS.md` | Created | Benchmark results and Q9 capture-scope decision gate record. |
| `Full Screen TUI Implementation Walkthrough.md` | Created / Updated | Tracks implementation progress, decisions, changes, and verification gates. |

