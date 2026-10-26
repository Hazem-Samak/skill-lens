# Plan: Smoke-wheel TimeoutExpired regression test

Status: Agreed
Authorization: User instruction on 2026-10-26: add the missing test for the `TimeoutExpired` branch in `scripts/smoke_wheel.py`; Qoder implements, GLM and MiniMax review, same OMP-coordinated pattern as the trial, trial branch only, no merge without the user's word. If Qoder fails to run, report and stop.
Reference: 087c370b130bb526b56e0e1b8f4f561149a65d4d (agreed plan freeze; this line is recorded in a following plan-only provenance commit)
Surface: omp; no Herdr
Risk and review: Low risk for product behavior — the change is test-only and adds no runtime path. The user explicitly selected two independent final reviewers, GLM and MiniMax, so both review the implemented test. No planning critic is dispatched under the Low-risk policy; Sol inspects the draft and source. Configured model identities are recorded; upstream identity remains unverified.
Roster: Sol coordinator; implementer Qwen 3.8 Flash via Qoder CLI; final reviewer 1 GLM 5.3 Flash free via OpenCode; final reviewer 2 MiniMax M3.1 Flash via mcode. No silent model, provider, paid-seat, or Herdr substitution.
Expected child tasks: Three before corrections: one implementer, two final reviewers. The waiter track remains parked.

## Outcome

`tests/test_tui_packaging.py` contains a deterministic regression test proving
`verify_tui_endpoint_install()` converts a `subprocess.TimeoutExpired` from the
installed-suite run into an `AssertionError` that names the timeout bound and
preserves partial stdout and stderr. The test must fail if that handler is
removed. This proves the previously untested error path without changing
product behavior.

## Current state

- Base commit: `4e14de3d9e04910bd768598ba34926d816ebc1b3`; branch
  `trial/omp-native-asyncio-20261026`.
- `scripts/smoke_wheel.py:532-556` runs the installed suites under a bounded
  `subprocess.run(..., timeout=timeout_seconds)` and catches
  `subprocess.TimeoutExpired`. It decodes either string or bytes partial output
  and raises an `AssertionError` chained from the timeout.
- `tests/test_tui_packaging.py` already covers invalid provenance, Textual
  present in the base lane, nonzero suite exit, and source copied into the test
  lane. Its `_make_packaging_subprocess_runner()` helper returns a
  `CompletedProcess` for the `pytest` invocation and has no timeout simulation,
  so the `TimeoutExpired` branch has no test.
- Product/test baseline from the immediately preceding unchanged-tree gate run:
  1,083 passed, 1 skipped; 91.16% combined coverage; mypy clean on 38 files;
  Ruff lint and format clean. Only documentation/evidence has been added since;
  product and test files are unchanged.
- Qoder's live catalog printed `Qwen3.8-Flash` but the catalog command did not
  exit before its 20-second bound. Install evidence is not execution evidence.

## Scope and boundaries

- Allowed product/test path for Qoder: `tests/test_tui_packaging.py` only.
- Do not change `scripts/smoke_wheel.py`, application code, snapshots, goldens,
  dependencies, CI, process policy, or unrelated tests.
- The test helper may gain a narrow timeout-simulation parameter; existing
  helper behavior and existing tests must remain unchanged.
- Sol owns verification, gate logs, review receipts, and commits. Qoder does not
  commit, run gates/tests/formatters, delegate, or change settings.
- Final reviewers are fresh, read-only, independent sessions; neither receives
  the other's report before its initial verdict. The verbatim OMP critic guard
  and report schema apply.
- No Herdr commands, panes, waiter, manifest, everyday-Herdr, push, or merge.
  User-owned untracked `.path` and `docs/validation/2026-10-25/` remain
  preserved and unstaged.

## Implementation steps

1. Freeze this plan in two plan-only commits on the trial branch; both Sol and
   the implementer verify the full frozen hash before product/test edits.
2. Qoder edits only `tests/test_tui_packaging.py`:
   - Extend the packaging subprocess runner with an explicit option that raises
     `subprocess.TimeoutExpired(cmd, timeout=..., output=..., stderr=...)` for
     the `pytest` invocation, after the earlier install/provenance calls.
   - Add one parametrized regression test over string and bytes partial output.
     It must invoke `verify_tui_endpoint_install()` and assert:
     the raised exception is `AssertionError`; its text names the configured
     timeout bound and command; it contains both partial streams; and
     `exc.__cause__` is the original `subprocess.TimeoutExpired`.
   - Keep the existing helper's defaults and all existing tests unchanged.
3. Sol inspects the full diff. Run the new test directly, then all four gates
   on the ready tree. Prove the test is load-bearing by removing only the
   production `except subprocess.TimeoutExpired` handling in a disposable copy
   (or an equivalent isolated mutation) and confirming the new test fails;
   restore and confirm it passes. Do not mutate the live checkout.
4. Dispatch fresh GLM and MiniMax final reviews through OMP background commands,
   using the same routes as the prior trial. Provide the frozen plan/hash, exact
   test diff, current gate evidence, and the guard/report schema. Compare scoped
   fingerprints before and after each wave.
5. Resolve genuine blockers, rerun affected checks, and record the final receipt.
   Accept and make a local trial-branch commit only if all four gates and both
   independent verdicts support the test. Do not push or merge.

## Acceptance

- The new test exercises the real catch/decode/raise path and fails if the
  `TimeoutExpired` handler is removed. It is deterministic, uses `tmp_path` and
  synthetic paths, and does not access the real home directory.
- Existing TUI packaging tests remain unchanged in behavior and continue to pass.
- All four gates pass on the final tree, run by Sol:
  `uv run --no-sync pytest --cov=skill_lens`, `uv run --no-sync mypy`,
  `uv run --no-sync ruff check .`, `uv run --no-sync ruff format --check .`.
- Two independent final review reports are substantive and terminal; configured
  identities are recorded and upstream identity is not overclaimed. No reviewer
  writes appear in fingerprints.
- The Qoder dispatch receipt records requested/verified model, process/session,
  terminal status, elapsed time, touched files, and report. A launch failure or
  unsupported route stops the trial; no substitution.
- Cost/visibility evidence is recorded like the prior trial: free/seat labels
  are not audited billing; missing token/charge data is `unavailable`, not zero.
- No merge, push, or Herdr action occurs; the trial branch remains the only
  delivery surface.

## Review decisions

- **Accepted — Low risk:** the change is test-only and cannot alter runtime
  behavior. Coordinator inspection confirmed the target branch and its existing
  coverage gap. No planning critic is required under the OMP Low-risk policy.
  The user's explicit two-reviewer roster is applied to the implemented test.
- **Accepted — source evidence:** `scripts/smoke_wheel.py:532-556` already
  contains the catch/decode/raise path; only regression coverage is missing.
- **Pending:** implementation diff, both final reviewers' findings, and
  coordinator dispositions will be recorded here before the final acceptance
  commit.
