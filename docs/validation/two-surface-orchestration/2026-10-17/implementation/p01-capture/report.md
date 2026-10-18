# P01 Request Capture Implementation & Council Report

## Fields Summary

- **EFFECTIVE_MODEL**: `antigravity/gemini3.8flashhigh` (full-access/default, provider identity unverified)
- **OUTCOME**: `SUCCESS` — Root-cause correction implemented and verified; root ancestor symlink redirects rejected atomically via descriptor walk from filesystem root `/`; 58/58 tests passed with 0 failures and 5/5 mutation guards killed with 0 survivors.
- **FILES_CHANGED**:
  - `docs/validation/two-surface-orchestration/2026-10-17/implementation/p01-capture/observer.py`
  - `docs/validation/two-surface-orchestration/2026-10-17/implementation/p01-capture/test_capture_offline.py`
  - `docs/validation/two-surface-orchestration/2026-10-17/implementation/p01-capture/run_offline_tests.py`
  - `docs/validation/two-surface-orchestration/2026-10-17/implementation/p01-capture/test-results.json`
  - `docs/validation/two-surface-orchestration/2026-10-17/implementation/p01-capture/report.md`
- **CHECKS**:
  - `ruff check --fix`: Passed cleanly, 0 errors, 0 warnings.
  - `ruff format`: Formatted cleanly, 0 errors.
  - `run_offline_tests.py`: 58 tests passed in 1.708s (52 capture tests + 6 mutation tests), 0 failures, 0 errors.
  - `launcher.py --help`: Subprocess executed with `-B` and `HERDR_ENV` unset, exited code 0 cleanly.
- **TESTS_ADDED**:
  - `test_swapped_ancestor_above_allowed_root_during_open_rejected`: Reproduces synthetic root ancestor swap (`top` component swapped to external symlink during directory open), asserting injection occurred, atomic rejection, outside sentinel untouched, and zero bytes written outside.
  - `test_swapped_root_ancestor_between_validation_and_anchor_open_rejected`: Injects swap between `validate_path_safety` and anchor acquisition, asserting injection occurred and walk cleanly rejects symlink.
  - Extended `test_clean_fd_rollback_on_rejection` to verify symlink rejection has zero descriptor leaks.
  - Adapted `test_swapped_immediate_parent_during_first_open_rejected` and `test_swapped_ancestor_and_root_during_first_open_rejected` to relative component opens.
- **DEVIATIONS_FROM_PLAN**: None. Authorized scope strictly maintained under frozen plan `docs/plans/2026-10-17-herdr-p01-request-capture.md @ a9bcda8b6f1e2ac7de15b13eefbdfa299adb830f`.
- **BLOCKED_ON**: None. Live pilot execution is intentionally reserved exclusively for the human operator.

## Executive Summary

As Sole Implementer (Antigravity Gemini 3.8 Flash High) under frozen contract `docs/plans/2026-10-17-herdr-p01-request-capture.md @ a9bcda8b6f1e2ac7de15b13eefbdfa299adb830f`, this bounded root-cause correction batch eliminates the ROOT ANCESTOR redirect vulnerability documented in `/private/tmp/skill-lens-p01-capture-20261018-qurnpsjs/root-anchor-finding.json`.

All modifications remain strictly confined within `docs/validation/two-surface-orchestration/2026-10-17/implementation/p01-capture/`. No product sources, tests, dependencies, installed packages, credentials, configurations, or untracked repository files (such as `.path`) were modified or committed. No live P01 pilot attempt was executed, and no background workers were launched.

> [!IMPORTANT]
> **Human Role Clarification**: In accordance with the project contract and safety boundaries, the **HUMAN operator alone starts real Herdr / Hermes** for the live pilot retry. The T3 / Antigravity agent exclusively prepares implementation files, executes offline tests, and inspects recorded evidence.

## Root Cause & Defect Resolution

### Root Cause Analysis
In the previous implementation, `open_anchored_parent_descriptor` performed `os.stat(str(root_resolved))` followed by `os.open(str(root_resolved), O_RDONLY | O_DIRECTORY | O_NOFOLLOW)`. Because `str(root_resolved)` is an absolute path, POSIX kernel path resolution follows symbolic links in all intermediate ancestor components leading up to `root_resolved`, applying `O_NOFOLLOW` only to the final component of the path. Consequently, if an ancestor directory (such as `top` in `top/allowed`) was swapped to a symlink pointing to an external directory, the open succeeded and anchored the sink in the external directory (`capture_written_outside_allowed_root = true`).

### Unified Descriptor Walk Architecture (`open_anchored_parent_descriptor`)
1. **Lexical Normalization without Resolution**:
   - `normalize_lexical_path` uses lexical path resolution (`os.path.normpath(os.path.abspath(...))`) without resolving symlinks via `Path.resolve()`.
   - Explicitly normalizes macOS system aliases (`/tmp` -> `/private/tmp`, `/var` -> `/private/var`, `/etc` -> `/private/etc`) lexically, preserving standard positive alias paths while preventing attacker symlinks from redefining approved roots.
2. **Coherent Directory-Descriptor Walk from `/`**:
   - Begins strictly at filesystem root `"/"` with `root_fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)`.
   - Walks through every root ancestor and then descendant directory component using relative `os.open(comp, dir_flags, dir_fd=curr_fd)` with `os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW`.
   - Never obtains an anchor via `os.open(fullroot)` or `os.stat(fullroot)`.
   - Never performs a redundant direct full-parent open.
   - Detects symlink substitution atomically on every component: any symlink causes `os.open` to fail, verified via `os.readlink(comp, dir_fd=curr_fd)` or `errno.ELOOP`, raising `ValueError(f"Symlink rejected: {comp}")`.
3. **Owned Anchor and Descriptor Rollback**:
   - Descriptor anchors own the actual directory; later renames or symlink swaps cannot redirect file writes.
   - All intermediate directory descriptors are closed on success, retaining only `final_fd` as `self._parent_fd`.
   - On any exception or rejection, all opened descriptors are closed cleanly with zero fd leaks.
4. **Storage Fallback Ownership**:
   - `CaptureSink._write_invalidation_record` reuses the verified owned anchor descriptor `self._parent_fd` via `dir_fd=self._parent_fd`.
   - Fallback #2 appends to `target_path.name` using `dir_fd=self._parent_fd`.
   - Fallback #3 writes companion marker `target_path.name + ".invalid"` exclusively with mode 0600 and `O_CREAT | O_EXCL | O_NOFOLLOW` using `dir_fd=self._parent_fd`.
   - If unavailable storage occurs, constant stderr alert `HERDR_OBSERVER_ALERT: capture_invalidated storage failure\n` is emitted without attempting unanchored reopens.

## Test Disaggregation & Verification Results

Unique test counts across focused capture tests and mutation tests:
- **Focused Offline Capture Tests**: 52 unique test methods.
- **Mutation Sensitivity Tests**: 6 test methods (5 mutation guards M1–M5 + 1 zero-survivors verification).
- **Total Unique Tests**: 58 tests.

### Execution Command

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPYCACHEPREFIX=/tmp/skill-lens-pycache \
.venv/bin/python -B docs/validation/two-surface-orchestration/2026-10-17/implementation/p01-capture/run_offline_tests.py
```

### Output Summary

```text
Ran 58 tests in 1.708s

OK

============================================================
P01 CAPTURE OFFLINE VERIFICATION SUMMARY
Total Tests Run: 58
  - Focused Capture Tests: 52
  - Mutation Tests: 6
Failures: 0
Errors: 0
Duration: 1.708s
Status: PASSED
============================================================
```

### Mutation Guards Sensitivity Summary

All 5 mutation guards were verified KILLED with zero survivors:

| Mutation ID | Guard Description | Target Unchanged Test Method | Status | Failing Assertion Recorded |
|---|---|---|---|---|
| **M1** | ContextVar request correlation | `test_direct_request_correlation_and_actual_api_mode` | `KILLED` | `AssertionError: None != 'test-session-123'` |
| **M2** | Secrets exclusion from observer bytes | `test_secrets_exclusion_from_all_observer_bytes` | `KILLED` | `AssertionError: b'SECRET_BEARER_AUTH_TOKEN_XYZZY' unexpectedly found` |
| **M3** | Loopback URL & route sanitization | `test_unapproved_url_sanitized_to_safe_marker` | `KILLED` | `AssertionError: '+ <unapproved_route_mismatch>'` |
| **M4** | Sink exclusive mode 0600 permissions | `test_mode_0600_and_exclusive_creation` | `KILLED` | `AssertionError: 438 != 384` (mode 0666 != 0600) |
| **M5** | Dynamic `agent.api_mode` extraction | `test_actual_mode_read_dynamically_not_assumed_constant` | `KILLED` | `AssertionError: 'custom_chat' not found in ['codex_responses', ...]` |

## Static Verification & Environment State

- **Date**: 2026-10-18. All historical /tmp check/evidence/deployment directories vanished per schedule; no historical result was fabricated.
- **Artifact Bootstrap Directory**: Approved `/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts` is verified present and empty (mode 0700).
- **Ruff Batch Check & Format**: Executed `.venv/bin/ruff check --fix` and `.venv/bin/ruff format` across modified files with 0 errors and 0 warnings.
- **Launcher CLI Help**: Offline launcher `--help` executed cleanly with code 0:
  ```bash
  .venv/bin/python -B docs/validation/two-surface-orchestration/2026-10-17/implementation/p01-capture/launcher.py --help
  ```

## Review Status & Next Steps

1. **Council Review Round 2 (finalR2)**: Both MiniMax and DeepSeek reviewers can evaluate this corrected implementation against the frozen plan.
2. **Pilot Launch**: Once final reviews approve, the **HUMAN operator** will initiate the genuine live P01 pilot retry. Mutable repository files must not be executed during live P01; launcher and observer scripts should be executed from a verified temporary copy with `HERDR_OBSERVER_OUTPUT_PATH` directed to a new owned attempt directory under `APPROVED_PILOT_ARTIFACTS_ROOT`.
