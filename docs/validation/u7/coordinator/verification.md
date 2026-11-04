# U7 coordinator review and verification — 4 November 2026

Status: Locally technically verified on the final implementation/test tree.
At this technical-verification checkpoint, no commit, staging, push, release or
publishing was authorized or performed, and HEAD was
`f62f654f8ad95ecb1e7171e1e9e921be686dd949`. The owner later authorized a fresh
recheck followed by commit and push; see [delivery recheck](precommit/verification.md).

## Authorization and execution

The owner selected one native `gpt-6-luna` subagent at xHigh to implement the
approved frozen U7 plan, followed by this coordinator's own review and tests.
The session-specific loop waiver remains in force. No extra reviewer agents
or external workers were dispatched. This is parent review of a separate
implementer's work, not the ordinary council process.

Dispatch configuration: [native-authorization.md](native-authorization.md).
Worker changes/checks: [implementation report](../implementation/implementation-report.md).
The requested model/effort was accepted by the native dispatch tool; an independent
runtime-routing readback is unavailable. The worker did not claim one.

## Standards review

Passed on the final tree. The coordinator inspected the tracked diff and new
Doctor/test files against AGENTS.md, DEVELOPMENT, the relevant Phase 4 findings
and read-only rules. Engines, controller, public models, CLI/Rich rendering,
registry, dependencies, expected output files and the frozen plan are unchanged.
The UI uses captured values and neutral Textual content; no target-file probes,
process/editor/clipboard operations or repair actions were added.

Initial draft corrections resolved a mismatched active-screen method name,
duplicate context rendering, unnecessary empty-state space, and stale deferred
focus callbacks. The evidence runner's long literal strings were wrapped and
formatted by the coordinator; its Python executable syntax tree is identical
before and after. This did not change any mutation or product behavior. The
initial lint output and correction are retained in the gate records.

## Specification review

Passed against [the frozen U7 plan](../../../plans/2026-11-04-tui-u7-doctor.md).
No unresolved in-scope product or test blocker remains.

- Home `h` opens Doctor only in the allowed focus/context. Doctor reads the
  published report in stored order and displays every finding field literally.
  Empty, info-only and no-session states remain distinct.
- Absolute/displayed/alias/canonical paths use captured relationships; names,
  parent roots, missing paths and ambiguous display strings never guess a row.
- Successful Enter queues Home's intent before pop, clears blocking filters,
  then aligns selection/cursor/preview/focus after generation reconciliation.
  Plain Back preserves filters. Old instances, old row events and old generations
  cannot redirect a newer view or clear a newer owned request.
- Raw JSON equals the existing CLI serializer on the same inputs. Hidden actions
  cannot jump. Refresh, retained data, expected refusal/retry, unexpected faults,
  sticky exit 3, scroll preservation/removal reset and quit during work pass.
- The full synthetic lifecycle preserves target bytes, modes and symlink targets.
  The recursive source guard includes Doctor, with existing guard-category
  mutations still enabled. No snapshot or golden was regenerated.

## Coordinator-authored acceptance checks

The parent independently authored and ran **16 external Pilot cases**. They cover
100×30 and 60×24 frozen first-open alias jumps after deleting targets, text/agent
filter clearing, cursor/preview/focus, ordinary Back and stale close, ambiguity,
actual CLI JSON equality, newest capture winning, held initial capture, old focus
callbacks, internal fault/recovery, refusal/retry/error with and without a prior
snapshot, valid-key stale generation, actual detail/JSON scroll and slow-work quit.
Final result: **16 passed in 12.95 seconds**.
Source: [independent-checks.py.txt](independent-checks.py.txt).
Output: [independent-ui.log](independent-ui.log).

The parent also added four permanent app tests in `tests/test_tui_app.py` for
host-route context/focus/JSON, stale exact-instance calls, rejected/invalidated
Home handoff, delayed row events and late Enter requiring a second confirmation.
Luna adapted the parent's valid-key stale-generation and scroll scenarios into
permanent Doctor tests. All are included in the final full run.

Replay the external cases by copying their source to a temporary test file with
baseline `tests/conftest.py` beside it, then using the command in [gates.json](gates.json)
with the checkout on PYTHONPATH. Their fixtures patch HOME and isolate system roots.
No live home-directory skills serve as fixtures. These are semantic headless
checks, not human visual approval.

## Full repository gate

Commands, output hashes, timings and input hashes:
[gates.json](gates.json), [inputs.json](inputs.json).

| Command | Final observed result |
| --- | --- |
| `.venv/bin/pytest --cov=skill_lens` | 1,238 passed, 1 skipped in 293.62 seconds; 90.02% combined coverage with branch measurement and TUI included. |
| `.venv/bin/mypy` | Passed, 45 source files. |
| `.venv/bin/ruff check .` | Passed. |
| `.venv/bin/ruff format --check .` | Passed, 413 files already formatted. |

All final commands exited 0. The coverage success line explicitly reaches the
unchanged 90% threshold. Source, tests and configuration remained byte-identical
during the final run. The existing skip requires a case-sensitive filesystem.
This is the combined statement/branch score, not a branch-only percentage.
Logs: [pytest](pytest.log), [mypy](mypy.log), [lint](ruff-check.log),
[format](ruff-format-check.log).

The first whole-suite run passed its tests but measured **89.60%**, and printed a
coverage failure despite exit zero. It remains failed evidence under
[first-full-run/](first-full-run/parent-gates.json). Required state/scroll/route/race
regression tests were added before the final rerun; no coverage setting, measured
file or threshold was changed. Intermediate appended-coverage diagnostics are
retained separately and are not represented as full acceptance runs.

Parent probe-development failures are retained too: a matrix initially used the
wrong constructor shape for SnapshotTooLarge; an app test initially checked focus
before Textual had applied it. Corrected test setup only, then reran the cases.
Worker development/harness corrections are recorded in
[failed-attempts.md](../implementation/failed-attempts.md).

## Mutation evidence and preservation

Luna's isolated campaign caught **16/16** deliberate failures, with passing
control-before and restored-control runs for every case. The coordinator checked
actual failed assertions, including valid-key stale generation, hidden raw Enter,
blocking agent filter and stale rejection canceling a newer Why token. The cases
ran in disposable archive copies, not the reviewed checkout. The parent inspected
[the runner](../implementation/mutation_campaign.py),
[full worker logs](../implementation/mutations/summary.md) and retained its own
[review receipt](mutation-review.json). Unchanged cases were not rerun merely to
produce duplicate evidence after formatting.

[baseline.json](baseline.json) records the initial tracked/unrelated file hashes.
[final-integrity.json](final-integrity.json) records unchanged excluded areas,
frozen plan/planning evidence and unrelated files, plus final HEAD/index state.
No human visual approval, hosted CI acceptance, Git delivery, U8/U9 or release
is claimed by local technical acceptance. The implementation was left uncommitted
at this checkpoint. The subsequent owner-authorized delivery recheck is recorded
[separately](precommit/verification.md).
