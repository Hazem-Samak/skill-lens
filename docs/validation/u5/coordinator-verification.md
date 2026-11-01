# U5 coordinator verification — 30 October 2026

> **Superseded for final status:** U5 was locally technically accepted on
> 1 November 2026 after the Why-focus correction and both passing targeted
> independent follow-ups. See [U5 acceptance](acceptance.md). The coordinator-stage
> evidence below remains historical; it does not describe outstanding work.

**Coordinator inspection complete; ready for two independent final reviews. U5 is not finally accepted.** No independent reviewer was selected/dispatched by this verification, and no product commit, push, release or hosted CI success is claimed.

## Authority and scope

- Frozen contract: `docs/plans/2026-10-29-tui-u5-diff-json.md` at `69a477ba9054a21030d038ed98a62962a1862d88`; reference-only commit `fb85ddb`.
- Owner-managed GUI implementer: River / DeepSeek 4.1 1017 Flash / max effort, as identified by the owner. Runtime/upstream identity remains unverified. The U5-only handoff/self-check exception is not a future workflow default.
- Coordinator findings and correction decisions remain in `coordinator-review-round1.md` (R1–R7) and `coordinator-review-round2.md` (C1–C4). They are historical findings, not outstanding blockers after the verification below.
- Compared SHA-256 fingerprints of 86 source/test Python files against the prior coordinator-verified tree: only `tests/test_tui_diff.py` and `tests/test_tui_read_only.py` changed. All product Python files and other tests match. Reviewed the changed tests and the appended implementation record. No product/test source edits were made by the coordinator.

## Final gate evidence

Inspected the implementer's final-tree outputs under `/tmp/u5r2/`. Full output is retained in [`mutations/round2.json`](mutations/round2.json), with provenance explicitly distinguished from coordinator-executed tests.

| Command | Result |
| --- | --- |
| `.venv/bin/pytest --cov=skill_lens` | Exit 0; 1182 passed, 1 skipped in 188.94 seconds; 90.13% combined coverage with branch measurement. |
| `.venv/bin/mypy` | Exit 0; no issues in 41 source files. |
| `.venv/bin/ruff check .` | Exit 0; all checks passed. |
| `.venv/bin/ruff format --check .` | Exit 0; 396 files already formatted. |

The existing skip requires a case-sensitive filesystem. No snapshot/golden regeneration or coverage exclusion/threshold change. The focused implementer run recorded 186 passes. These final gates were not rerun merely to confirm unchanged valid supplied evidence. The previous coordinator-executed full gates and live terminal smoke remain valid for the byte-unchanged product; final test changes were inspected and exercised directly below.

## C1–C4 closure and direct coordinator checks

- **C1:** the new old-screen cleanup test holds request A while B owns the active Diff slot, closes the old screen through real navigation, and verifies B's token/event, accepted cache result and cached reopen without another worker. Removing ownership equality now fails on `old-owner cleanup removed the newer owner's request`.
- **C2:** the covered-Why test asserts suspension and cancellation while Diff is active, waits for the real obsolete outcome, verifies rejection/no cache/no hidden replacement, and obtains exactly one report on resume. A no-op suspension now fails on `covered Why must be suspended`.
- **C3:** the target-preservation lifecycle positively observes populated Home, accepted Diff/Why reports, their JSON modes/documents and return transitions before comparing target bytes/modes/link targets. No-op Diff entry now fails at `lifecycle traversal stalled: accepted Diff report`.
- **C4:** inspected and executed the corrected pre-capture shortcut fixture and explicit-refresh transition. The same shortcut is retargeted after capture; frozen documents retain their original copy set/entrypoint count, and refresh publishes the new target. Stale capture/report tests now observe actual controller processing and assert rejection, instead of using fixed sleeps as proof of completion.

The coordinator ran a clean grouped control of all six relevant tests: **6 passed**. It then ran four mutations in disposable copies: the three former survivors plus the live-collection mutation whose fixture changed. Every mutant failed at its intended behavioral boundary, and restoring each copy made its test pass. No syntax/import/collection failure was counted as success.

| Mutation | Injected failure observed | Restored control |
| --- | --- | --- |
| M02 live Diff collection | First-visit report cannot complete under live-read bans. | Passed |
| M05 cancel another owner's request | Active B removed by old-owner cleanup. | Passed |
| M06 hidden Why remains active | Covered Why is not suspended. | Passed |
| M23 no-op Diff traversal | Target-preservation lifecycle never reaches accepted Diff. | Passed |

Exact transforms, commands, complete outputs, source fingerprints and source-preservation receipt: [`mutations/round2.json`](mutations/round2.json). The earlier campaign's unchanged passing scope is retained in [`mutations/round1.json`](mutations/round1.json). Across the original campaign plus supplemental traversal case, **23 mutation scenarios are accounted for with no remaining survivors**; the targeted rechecks replace the earlier survivor verdicts rather than count them again. No unnecessary broad campaign rerun.

## Runtime and preservation evidence

The preceding coordinator round launched the actual CLI TUI through Rex against temporary synthetic HOME and exercised long names/deep paths, Diff, JSON, refresh, return navigation and quit at 100x30/60x24. Terminal captures showed reachable report tails and literal JSON above the footer; exit 0. The owned pane was closed and its temporary fixtures removed. All product Python bytes still match that smoke-tested tree, so no new terminal launch was needed for test-only corrections. Implementer headless compositor checks are additional evidence, not physical-terminal or human visual approval.

Coordinator mutation copies were isolated, deleted after each trial and never applied to the working checkout. Fingerprints before/after the recheck confirm no source/test modification. Unrelated existing work remains excluded: `.path`, `docs/plans/2026-10-26-omp-native-asyncio-trial.md`, `docs/validation/2026-10-25/`, `docs/validation/omp-native-asyncio/`.

## Next gate

No coordinator correction request remains. The owner must name both final reviewers' provider/model/effort and runtime/harness before dispatch. Apply the existing High-risk family disclosure/acceptance policy to that named roster; do not inherit past choices. Reviewers receive the exact frozen contract, scoped diff/source fingerprints, gate/mutation evidence and required read-only guard. Their independent verdicts, any resulting corrections and final coordinator acceptance/commit remain required.
