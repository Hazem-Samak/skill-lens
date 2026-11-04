# U6 mutation harness attempt record

This file preserves harness problems and the decisions made while building the
disposable-copy campaign. It is not a final mutation acceptance receipt; the
complete result is written separately by `mutation_gate.py`.

## Attempt history

| Attempt | Observation | Disposition |
| --- | --- | --- |
| Initial disposable copy | `copytree` followed the unrelated `.workbuddy-ai` link tree and hit `Errno 62` before tests ran. | Exclude `.workbuddy-ai`, preserved dated validation data, and U6 evidence from the copy; copy symlinks without following them. |
| First source selector | The controller's active-request guard text occurs twice, in success and error acceptance. A selector expecting one match stopped the harness before the mutation test. | Record explicit occurrence indexes for stale-success and stale-error mutations; the source-only preflight now checks each chosen index. |
| Redundant JSON refresh probe | Removing one `_refresh_json()` call from pair submission survived because generation and loading transitions already clear or refresh the document. | Treat this as a redundant-protection probe, not a killed behavior mutant. Replace it with the raw-refresh reconciliation mutation, which skips new-generation work while JSON is open and leaves the old report/document even though the captured inputs changed. |
| Reversed pair probe | Reversing `(A, B)` caused the controlled screen to wait for an accepted report because the report request no longer matched the selected ordered pair. | The intended failure marker is the bounded UI handoff predicate `accepted comparison report`; the failure output also names the timed-out wait. The mutant is only counted if that handoff marker appears, alongside the test failure and passing control/restoration. |
| First visit target-read probe | The final matrix's first run reached the frozen-target guard during result rendering. The process traceback included `first visit accessed captured target through Path.read_text` and the synthetic HOME path; the harness had mistakenly expected a handoff timeout. | Change the evidence matcher to the exact target-read assertion emitted by the traceback. This is a matcher correction only; no product or test file changed. |
| Temporary-copy provenance | The first check compared a symlinked `/private` path with a `/var` spelling and did not use an absolute `__file__` for the test module. | Resolve paths before comparison; preflight now records `skill_lens.__file__` and both Agents/Compare test module `__file__` values from the disposable copy. |
| Partial first-seven campaign | A prior process printed seven `PASS` summaries before the raw-refresh selector stopped on ambiguity. Its full per-mutant output was not written to a durable receipt. | Retain this only as a partial attempt; do not count it as the final matrix. Preflight all 13 source edits before a final run. |
| Reproduction interrupted | A duplicate targeted-coverage process was stopped after the parent began its own reproduction. Its partial `FFF` output is retained in `targeted-coverage-partial-interrupted.log`. | Not a coverage result; use the parent's separately captured reproduction and full combined gate. |
| First checkpointed 13-case campaign | Case 9 survived because an illicit report worker completed before `active_requests` was checked. Case 10's retry mutant starved the Textual message pump before the call-count assertion. Case 12 failed at the hidden-picker cursor equality with observed `(2, 2) == (1, 2)`, but the marker did not match the rendered assertion output. | Keep the complete original receipt in `mutations-first-complete-run.json`. Strengthen the invalid-choice and retry tests so they assert request allocation/call count directly; adjudicate case 12 from its captured tuple mismatch without rerunning it. |

## Mutation interpretation

Each final kill must show all three facts in `mutations.json`: the clean-copy
control passed, the mutated process failed at the recorded intended assertion,
and the restored-copy test passed. A nonzero exit by itself is insufficient.

The redundant JSON-refresh survival is intentionally not described as a product
gap. Removing a repeated redraw call does not violate a visible behavior when
other state transitions enforce the contract. The replacement mutation tests
that a real registry refresh removes stale result and raw JSON state.
