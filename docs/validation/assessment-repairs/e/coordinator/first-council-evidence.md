# Stage E — first council evidence

Frozen plan: docs/plans/2026-10-12-assessment-repairs.md @ fe6f89bc55eb3f4f04187567b968dd96ae9c86c1, Stage E F08/F09/F14/R03. Base f0cf52684dfcc638a2f5a49509a5be80faddc951 is accepted Stage D. Current Stage E remains unaccepted/uncommitted.

Coordinator read complete product/old-test/new-test diff and consumers, allowed-file scope and correction delta. Product changes are four files only: cli.py, core/compare.py, core/snapshot.py, tui/__init__.py. No registry, renderer, model, dependency, CI or output fixture change. .path preserved.

Original implementation reported green gates, but coordinator reproduced ambient-HOME use in the comparison mirror test and two ineffective loop assertions with actual production mutations surviving 0/0/0. Gemini correction modified only the new test and evidence; product hashes are unchanged. Current tests use mock_home, nonempty four-relation mirror assertions, owned-loop closure and exact no-current-loop postconditions. Both formerly surviving mutations now fail on 3.11 and 3.14. No coordinator-reproduced blocker remains before council.

Direct final gates: 967 passed, one filesystem skip,90.53% coverage; mypy36; Ruff134 clean. Targeted Python3.14:37 passed with skill_lens.tui DeprecationWarning filter. Its existing external environment lacks pytest-cov, so initial --no-cov option rejection was a harness mismatch, corrected by omitting that flag; not a product failure.

Independent mutation controls:13 distinct mutations/15 interpreter executions, all0/1/0. Exact diffs/provenance/source hashes/logs in mutations.json; worker receipts remain separate. Direct CLI consumers now exit2 with literal stderr/empty stdout. Local macOS3.11 and targeted3.14 only; no unexecuted Linux/full3.14 CI claim. Existing slow-worker quit and fault tests remain in the full suite; no executor-join change.

Known nonblocking limits: duplicate test examples/long test module; generic disabled-reason cleanup from Stage D remains outside E. Existing placeholder UI has no comparison selection screen; service and adapter validation must agree without building U7. The change from explicit CLI terminal bypass is authorized F08 and explicitly preserves internal headless runner. get_event_loop preserves the existing no-explicit-loop policy behavior on older versions; only deprecated direct policy lookup is removed.

Full diff through one source: /Users/corvette/.t3/userdata/skill-lens-repair-checkpoints/2026-10-15-stage-e-work/complete-product-test.diff. Original implementation and correction briefs/results/baseline reproductions and discarded weak-guard proofs remain in that directory. Both implementation tasks are terminal with no pending children; configured full-access/default readbacks override worker mode wording. No council wave has occurred for Stage E.
