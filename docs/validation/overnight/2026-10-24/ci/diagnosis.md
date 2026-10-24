# CI repair — diagnosis and result

Branch: `fix/overnight-closure-20261024`. No merge to `main`.

## 1. Linux cancellation test

**Symptom:** `tests/test_session_snapshot.py::test_cancelled_capture_does_not_publish`
failed only on `ubuntu-latest / py3.11` with `DID NOT RAISE CaptureCancelled`
at what was then block 9. macOS py3.11 passed. Fail-fast cancelled the rest.

**Cause (source):** block 9 exercised the step-4 `samefile` fallback. That
fallback is reachable only on a case-insensitive filesystem: discovery asks for
`SKILL.md`, APFS resolves it to the real lowercase `skill.md`, capture records
the real name, and the relative-name lookup misses. On case-sensitive Linux the
lowercase document is found directly (`_SKILL_FILENAMES = ("SKILL.md",
"skill.md")`), so the fallback never runs and no cancellation checkpoint fires.

**Fix:** split that phase into
`test_cancelled_capture_during_case_insensitive_samefile_fallback`, with a
runtime skip carrying that exact reason on case-sensitive filesystems. The other
nine phases remain in the main test. No product code changed.

**Result:** `ubuntu-latest / py3.11` now passes on run `40132660052`; macOS
py3.11 also passes. Local 3.11 gate: 1083 passed, 1 skipped, 91.16% coverage.

## 2. Minimum-endpoint lane: a real Python 3.13 hang

**Symptom:** the packaging job failed at
`Verify minimum endpoint (textual==8.2.8)` with a timeout. Raising 180 s to
600 s did not help; the 600 s run expired with empty partial output. The nine
files passed individually on Python 3.11 in 50 s, and the grouped run on 3.11
passed in 44.35 s, so the lane was not slow.

**Cause:** the packaging job runs `uv run python scripts/smoke_wheel.py` with
Python 3.13, so the lane's venv is 3.13. On 3.13,
`test_prompt_quit_does_not_block_on_worker` (stage G) and the equivalent
`test_synchronous_run_quit_proof_before_blocked_capture_release`
(`test_tui_app.py`) press `q` before the mounted screen installs its bindings.
The key press is dropped, the headless app never exits, and pytest waits
forever. A thread dump showed the main thread in
`textual/app.py::run` inside `run_until_complete`, with the capture worker still
blocked. The same test passed on 3.11 by timing luck.

**Fix:** after confirming the capture worker is blocked, the autopilot pauses
0.2 s before pressing `q`. The proof is unchanged: the watchdog is 1.5–2.0 s
and the test still asserts it never fired and the worker was never released.

**Result:** on Python 3.13 the stage G + TUI app files pass (43 passed, 7.2 s),
and the full suite passes: 1083 passed, 1 skipped, 65 s.

## 3. Python 3.13 symlink-cycle regression

**Symptom:** on 3.13, `test_cyclic_symlink_config_error_containment`
(`test_stage_d_repairs.py`) failed:
`"Unresolvable path in Codex config is unsupported"` was absent from
`unsupported_controls`.

**Cause:** `Path.resolve(strict=False)` stopped raising `RuntimeError` for
symlink loops on 3.13; it returns the unresolved symlink path. The Codex config
reader relied on that exception to classify the path as unsupported.

**Fix:** `_resolve_config_path()` resolves strictly first (a loop still raises
`OSError`/`RuntimeError` on every supported version) and falls back to
non-strict resolution only for `FileNotFoundError`, preserving missing-path
behaviour. Verified on 3.13 and in the default 3.11 gate.

## 4. Matrix caveat

The original run used fail-fast, so the Python 3.12–3.14 jobs were cancelled
after the packaging failure. Their real failure was the same 3.13 hang plus the
cycle failure, now fixed locally on 3.13 and 3.14. A clean push is required to
prove the full matrix.

## Verified locally

| Environment | Result |
| --- | --- |
| Python 3.11 (project venv, coverage gate) | 1083 passed, 1 skipped, 91.16% |
| Python 3.13, locked `[dev]`, Textual 8.2.8 | 1083 passed, 1 skipped, 65 s |
| Python 3.14, locked `[dev]`, Textual 8.2.8 | 1083 passed, 1 skipped, 65 s |
