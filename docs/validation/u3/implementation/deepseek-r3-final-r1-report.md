# Final-R1 test-only correction — implementer report (candidate R3)

## EFFECTIVE_MODEL
`opencode/deepseek-v4.1-flash-free` (variant `high`), Full access / default
interaction — the same authorized OpenCode implementation session.

## OUTCOME
The final independent review's sole blocker (`docs/validation/u3/coordinator/minimax-final-r1.md`)
was an **evidence** gap, not a behaviour defect: the plan-mandated "a rejected
outcome must not clear a newer owned token" invariant had no failing-planted
mutation proof, because the shipped race test released the old worker only after
the queue was idle. That gap is closed **test-only**. No product file changed.
No commit, push or delegation.

- **New deterministic regression.** `test_home_rejected_old_outcome_preserves_newer_owned_token`
  blocks the first request's worker, moves the selection so it is cancelled and a
  newer request is dispatched and also blocked, then releases only the *old*
  worker so its rejected outcome is delivered while the newer request is still
  owned and in flight. It asserts the newer owned token **object** is preserved,
  the controller still tracks the newer request, and the queue drains once the
  newer request is released. Ordering is established by threading events (a
  `resolved` callback spy marks delivery), never a bare sleep; both release events
  are set in `finally`.
- **Sixth mutation category.** `mutation_gate.py` replaces the rejected-outcome
  branch's `pass` with `self._inflight = None`; the new test dies on the intended
  assertion and the restored copy passes. Gate schema is now
  `skill-lens/u3-mutation-gate/4`.
- **`--out` flag.** The harness takes an optional `--out PATH` so a reviewer can
  write the receipt outside the checkout; verified both ways.
- **Documentation truthfulness.** §5 no longer restates a volatile Ruff file
  count; §6 links the immutable named benchmark receipt instead of copying
  drifting numbers. No benchmark was re-run (product and benchmark unchanged).

## FILES_CHANGED
Changed (tests):
- `tests/test_tui_home.py` — import `HomeScreen`; +1 regression
  (`test_home_rejected_old_outcome_preserves_newer_owned_token`). 33 tests now.

Changed (validation harness + receipts):
- `docs/validation/u3/implementation/mutation_gate.py` — sixth case, `--out`
  flag (argparse), schema `/4`, control entry.
- `docs/validation/u3/implementation/mutation_gate.json` — regenerated `/4`
  receipt (6/6).
- `docs/validation/u3/implementation/historical/mutation-gate-r1.json` — the
  superseded five-case (`/3`) receipt the final-R1 review inspected, preserved
  unchanged (SHA-256 `f4b1e6df…9b296e00f25`).
- `docs/validation/u3/implementation/historical/README.md` — labels the preserved
  receipt superseded (not invalid) with the reason.
- `docs/TUI_U3_WALKTHROUGH.md` — §2/§4 test counts and the new race; §5 removes
  the volatile Ruff file count; §6 links the benchmark receipt; §7 adds case 6 and
  schema `/4`; new §12 records this batch.

Added (report):
- `docs/validation/u3/implementation/deepseek-r3-final-r1-report.md` (this file).

**Unchanged / byte-identical product (verified):**
- `skill_lens/tui/home.py` `36acf73aa416f7cefa1ae00dff1c9d4e297677a76becb6344e8dae4381393652`
- `skill_lens/tui/app.py` `cb790ad1c5381a8a4f75869c2c07b6960c43ad0430057c7543edd5850be6c411`
- `tests/test_tui_app.py` `364c35e84c50d7405c6217d308bc364ed71c9bed2fab8a1ff122cb228ecd19b1`
- `tests/test_tui_read_only.py` `008d3cc5529df11c3c785d9604e550d82894e2abe24d2f1f32fa541dac79ad5a`
- `README.md` `69b2dcc2f270784c8227a537258531a74e2d44826fe3ce783b1aaeb986f1c0d7`
- `docs/validation/u3/benchmark_home.py` `eda15271400ffa61d6f840a28835ad545e236565dce9a6df4c7b193b9739b35f`
- `docs/validation/u3/implementation/benchmark_home.json` `4b57cb260a4b967262aa99600868281ee11bb1d8e43decf76d15090a01643b9e`
- `.path` (empty) `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

Coordinator evidence under `docs/validation/u3/coordinator/` (including
`review-ready/`) was not touched. The frozen plan was not touched.

## CHECKS
- **New focused test:** pass (5/5 consecutive runs on the shipped source).
- **Mutation gate** (`mutation_gate.py`, schema `/4`): 6/6 mutants detected with
  real failing assertions, 6/6 restored controls pass, 6/6 controls pass, repo and
  disposable work `home.py` byte-identical (`36acf73a…93652`). `--out` verified
  writing the receipt outside the checkout.
- **Four project gates on the final tree:**
  - `pytest --cov=skill_lens` — **1082 passed, 1 skipped** (macOS
    case-insensitivity), **91.16%** combined; `skill_lens/tui/home.py` 91%.
  - `mypy` — Success, no issues in 38 source files (strict).
  - `ruff check .` — All checks passed.
  - `ruff format --check .` — All files already formatted (count intentionally
    not asserted; it tracks the Markdown/evidence inventory, see walkthrough §5).

## TESTS_ADDED
- `tests/test_tui_home.py::test_home_rejected_old_outcome_preserves_newer_owned_token`

## DEVIATIONS_FROM_PLAN
- None in scope or behaviour. This batch is test-only plus receipts/documentation,
  exactly as authorized; no product hook, threshold, dependency or lock change.
- Minor: the walkthrough's Ruff file count is now deliberately omitted rather than
  restated (the review and this run measured different counts on trees that differ
  only in evidence inventory), per the correction's instruction to remove volatile
  claims from the current summary. Historical logs are untouched.

## BLOCKED_ON
Nothing. Awaiting Sol's acceptance and the status-doc flips.

## ARTIFACT HASHES (this batch)
- `tests/test_tui_home.py` `50651480d73c67a821083b1a9e40c8f5d0825296c32eab27acdb8961febb8115`
- `docs/validation/u3/implementation/mutation_gate.py` `e91bb428c0408cf30797f7f36ab89308d0f5493aad13b12ddb6258aaffedde32`
- `docs/validation/u3/implementation/mutation_gate.json` `138a1082df2b05836ea8871f4bf63df50b70266c7648167678177a11e6873631`
- `docs/validation/u3/implementation/historical/mutation-gate-r1.json` `f4b1e6dfc05d5ea260af0ecb1c2dad1bacbc8ace9e6e53fa8576a9b296e00f25`
- `docs/validation/u3/implementation/historical/README.md` `7ef5c3158c4751c31004dd01e0ebe899124d999a4c254681917cb0f59ea4cda1`
- `docs/TUI_U3_WALKTHROUGH.md` `878ed901a01ed76b9e76ee38b20536036095d67dd8d0a2390b1c1fe360be129a`


Coordinator provenance note (2026-10-19): hashes and pending-status text above describe the implementer report-time snapshot. Sol later refreshed walkthrough section 5 before R2 (reviewed hash da0157110d7b3f89b0ece48e662079d1d3b2a55de22d42d3194fc99d19088c7b), then its acceptance status after PASS. Current delivery hashes are recorded in coordinator/final-gates/source-sha256.json. Product source did not change.
