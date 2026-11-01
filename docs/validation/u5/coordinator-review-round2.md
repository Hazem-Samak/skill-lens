# U5 coordinator inspection — round 2, 30 October 2026

Verdict: **changes required — remaining acceptance-test gaps**. The corrected product tree passes the ordinary gates. The frozen plan explicitly blocks acceptance when a required in-scope mutation survives. No independent final reviewers were dispatched, no product/test code was edited by the coordinator, and no product commit or push was made.

Authority: `docs/plans/2026-10-29-tui-u5-diff-json.md` at `69a477ba9054a21030d038ed98a62962a1862d88`, reference-only commit `fb85ddb`. The U5-only implementer self-check permission still applies. Owner-provided implementer identity remains River / DeepSeek 4.1 1017 Flash / max effort, without runtime/upstream attestation.

## Verified improvements

- Reviewed the corrected mount guard, idempotent JSON publication, scrollable Diff metadata, JSON focus exclusion, corrected fixtures and added behavioral tests against the original R1–R7 findings.
- Independently ran `.venv/bin/pytest --cov=skill_lens`, `.venv/bin/mypy`, `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .`: **1180 passed, 1 skipped, 90.10% combined coverage with branch measurement**; type/lint/format checks passed. Test duration 188.53 seconds. Session output: `artifact://40`. The existing filesystem skip remains; CLI snapshots passed without regeneration.
- Ran the actual CLI TUI in an owned background Rex terminal against a temporary synthetic HOME, including long-name/deep-path Diff content, Home return, raw JSON, refresh and quit at 60x24/100x30. Captures showed the report tail and literal JSON above the footer, including the deeply nested project installation. Exit 0; the owned pane was closed. No human visual approval is inferred.
- Mutation experiments used disposable copies only. Initial and restored grouped controls each passed 22 selected tests. **Twenty required/extra mutants were detected and two required mutants survived.** Both survivors were then checked against all six TUI lifecycle test files: **179 tests passed with each defect injected**. A separate target-preservation traversal mutation also survived its intended test.
- SHA-256 comparison of 86 source/test Python files showed no source-checkout changes during the campaign. Each temporary mutant tree was deleted. Full exact mutations, selected tests, control/restored logs, failure outputs, source fingerprints and broader-survivor outputs are retained in [`mutations/round1.json`](mutations/round1.json).

The detected mutations cover wrong Diff identity, first-visit live collection, stale result, stale error, missing Why resume request, incorrect removal unwind, lost direct-Home notice, filtered Home JSON, wrong-agent JSON, old-generation JSON, changed canonical serialization, missing CLI final line feed, markup interpretation, binary payload exposure, lost character-only truncation notice, JSON navigation guard, JSON back handling and focus traversal. Additional mount and scroll regressions were also detected. Failure outputs were inspected; no syntax/import/collection failure was counted as a detected behavioral mutant.

## C1 — Diff's foreign-request cancellation guard is not protected

Current product code is correct at `skill_lens/tui/diff.py:354–365`. However, changing:

```python
if active is not None and active == owned:
```

to:

```python
if active is not None:
```

lets an old screen cancel a newer request it does not own. Mutation `M05_cancel_foreign_owner` passed both targeted tests and the broader 179-test lifecycle suite.

The current leave/reopen test cancels A while A is still the active request; after reopening, its later assertions do not exercise cleanup by a screen still holding A while B is active. The new cache-hit test protects an unrelated **compare** request, not a newer request in the same **diff** slot.

Required correction: add a deterministic behavioral test with two real Diff requests. The old screen retains owned token A while the controller's active Diff token is B. Closing/cleaning up the old screen must leave B and its cancellation event intact; B must complete and remain usable/cached/displayable. Test full token identity, event state and the resulting consumer-visible report/cache reuse, not just that a mocked method was called. Removing the equality guard must fail that test for the ownership assertion; the restored tree must pass. Do not remove or relax the correct product guard.

## C2 — Covered Why suspension is not protected

Current product code is correct at `skill_lens/tui/why.py:348–358`. Replacing the entire `WhyScreen.suspend_detail()` body with `return` leaves Why's report active while Diff covers it. Mutation `M06_hidden_why_continues` passed both targeted pending/resume/covered-refresh tests and all 179 lifecycle tests.

The existing tests check that Why eventually has a report after returning, but do not prove that its request was cancelled and its hidden activity stopped while covered. Continuing the original request can therefore satisfy their final assertions.

Required correction: start Why report A behind a controlled gate, capture its complete token/event, open Diff and positively assert that Why is suspended, A's event is set and its active request is absent **while Diff is active**. Release A while still covered and wait for its actual outcome to be processed; it must not enter the accepted cache or trigger hidden replacement work. On return, Why must obtain its accepted current-generation report through the normal cache/owned-token/dedup path. Retain same-generation resume and covered-refresh scenarios. Making suspension a no-op must fail the new covered-state assertions, not merely a timeout caused by bad test setup.

## C3 — Target-preservation traversal can skip Diff without failing

`tests/test_tui_read_only.py:test_synthetic_target_preservation_across_lifecycle` sends the new keys but checks only that the sequence ends on Home before its later byte/mode/link comparison.

A supplemental mutation made `HomeScreen.action_open_diff()` return without opening any screen. The target-preservation test still passed (**1 passed in 4.34 seconds**). Its sequence therefore does not prove that the preserved target was actually exercised through Diff.

Required correction: positively observe each intended screen and JSON mode during that lifecycle. Wait for the populated Home table, accepted Diff/Why reports, actual JSON documents and expected focus/return transitions before continuing. Keep the before/after target bytes, modes and symlink-target comparisons. The same no-op-Diff mutation must fail on the missing Diff transition; the real implementation must pass. Use bounded predicates/events, not a final Home assertion or keypresses alone as proof of traversal.

## C4 — Finish the frozen-input and completion-order proof precisely

Two source-inspection gaps remain in the new R5 tests:

1. `tests/test_tui_diff.py:1439–1443` creates `.agents/skills/asset` as a **new symlink after capture**. Nothing existed there before capture, so this is not the pre-existing captured symlink being retargeted required by the frozen acceptance. Seed a meaningful shortcut before the independent expected reports/capture, then unlink/recreate that same shortcut to a different existing synthetic target after publication. Prove that the first Diff/JSON visits keep the captured canonical/display identity/content and explicit refresh sees the new target. Keep the edit/delete/settings changes, independent pre-change oracle and live-reader/probe bans; do not fabricate report fields.
2. The older-capture-completes-last test releases generation 2 and waits `pilot.pause(0.3)` before asserting it did not overwrite generation 3. The old-report leave/reopen test similarly uses `pilot.pause(0.2)`. These delays do not prove that the obsolete outcome was actually consumed before asserting its rejection. Observe the real old worker/outcome reaching the app/controller through a bounded event/predicate, then assert current report/generation/cache/fault state is unchanged. Do not merely increase sleeps. Apply the same observed-completion convention in the new C1/C2 tests.

These are the existing frozen acceptance requirements, not new feature scope. The coordinator has not observed a new failure in the corrected product behavior; these tests must demonstrate that the required protections cannot silently regress.

## Correction and return protocol

Read this record and the full amended frozen plan. Correct C1–C4 in allowed test paths; product changes are only justified if those stronger tests expose an actual in-scope defect. Do not rewrite coordinator records, mutate the working checkout for mutation experiments, weaken existing assertions, expand scope, change dependencies/settings/coverage/snapshots, delegate, stage, commit or push.

For this U5 round the implementer may run focused tests, scoped formatting, isolated synthetic UI smoke and all four full gates and fix failures before returning. The coordinator retains the disposable-copy mutation campaign: the supplied exact mutations explain what the new tests must protect, not permission to mutate the working checkout or claim coordinator acceptance.

Suggested focused check after the test corrections:

```bash
.venv/bin/pytest tests/test_tui_diff.py tests/test_tui_json.py tests/test_tui_read_only.py
```

Then establish all four final gates:

```bash
.venv/bin/pytest --cov=skill_lens
.venv/bin/mypy
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Do not rerun unchanged known-surviving mutants merely to confirm this report. After the stronger tests return, the coordinator will verify that C1/C2/C3 mutants fail for their intended assertions and clean/restored copies pass. Passing evidence for unchanged mutation scope remains reusable; no unnecessary broad campaign rerun.

Return C1–C4 dispositions, changed files, exact test/gate commands and exit statuses, totals/coverage, full log locations, UI verification limits and remaining blockers. Mark coordinator mutation rechecks and both independent final reviews pending. No acceptance claim.
