# Stage G council adjudication — 15 October 2026

Both fresh second-round critics pass with no blockers. Coordinator accepts their evidence after reproducing the material first-round findings, inspecting the tests-only correction and verifying the final unchanged product/test tree. Passing reports alone did not determine acceptance.

## Review identity, delivery and protection

MiniMax: `mcode`, `m:minimax:MiniMax-M3.1-Flash-Preview:v:thinking`, `thinkingEffort=xhigh`. Muse: `opencode`, `opencode/muse-spark-1.3-contributor-free`, `variant=xhigh`. Both rounds used Full access, plan interaction mode, separate fresh task IDs, the verbatim critic guard and exact requested report schema in their prompts. T3 configuration readbacks are in [round-one configurations](review-r1-configurations.json) and [round-two launch/configuration receipts](review-r2-launch-receipts.json). This is instruction-based read-only restraint, not an enforced write sandbox. Upstream served identity, actual effort and family diversity remain unverified under the owner's selected named pair.

Complete reports: [MiniMax round one](review-r1-minimax-report.txt), [Muse round one](review-r1-muse-report.txt), [MiniMax round two](review-r2-minimax-report.md), [Muse round two](review-r2-muse-report.txt). Original round-one and round-two briefs are adjacent. MiniMax's native plan-mode wrapper wrote the full report externally and ended with a generic summary. Coordinator recovered the report from the exact artifact named by the task timeline; [recovery receipt](review-r2-minimax-recovery.json) records the file hash, provenance, completed run and cancelled native plan-exit question. That question was no longer pending; no implementation approval or continuation was sent.

All 602 hashes and Git status match before/after review. [Before fingerprints](before-review-fingerprints.json), [after fingerprints](after-review-fingerprints.json), [before status](before-review-status.txt), [after status](after-review-status.txt). Only administrative acceptance/evidence files were added afterward.

## Confirmed first-round findings and correction

Both first-round reviewers passed. MiniMax nevertheless demonstrated four new-gate assurance gaps as suggestions. Coordinator reproduced all four as clean/mutant/restored **0/0/0**, then required correction under the project's new-gate mutation rule. Their label did not justify deferral. Historical proof is retained in [reproduced-proof-gaps.json](historical/coordinator-council-r1/reproduced-proof-gaps.json).

| Confirmed gap | Correction and final proof |
|---|---|
| Removing installed-origin assertions still passed | Tests reject outside base origin and separately reject package/TUI endpoint origin. Independent split-branch mutations each fail the corresponding single-outside case. |
| Removing base Textual absence assertion still passed | Test executes the actual generated Python check with Textual present and requires its real child failure. MiniMax additionally changed the assertion message and module lookup to verify real execution. |
| Ignoring failed installed pytest still passed | Test requires failure on a nonzero installed-suite exit. The corresponding mutation fails with `DID NOT RAISE`, not an unrelated import error. |
| Removing the copied-source guard still passed | Test deliberately contaminates the temporary test directory and requires the actual source-presence assertion to fail. |

Gemini changed only the packaging tests after round one. [Focused delta](correction-only.diff); [complete product/test delta](complete-product-test.diff). The final direct gates, actual fresh installed checks and all twenty production/CI mutations match the reviewed bytes. MiniMax independently repeated all six new mutations against the full packaging test file, each with one intended failure, restored the hash and obtained 24 passing packaging tests. It independently obtained the same full-suite 1021/one-skip/91.16% result. Muse checked both branch independence and failure provenance. No unresolved in-scope blocker remains; two rounds converged and no third wave was launched.

Pre-council corrections and historical failures remain in the original briefs and `historical/`: duplicated validators, weak executor-join proof, malformed private adapter shape, missing constrained minimum lane, machine-specific artifact assertions, relative-path normalization and synthetic-HOME isolation. The `.path` preservation incident is explicitly recorded rather than described as uninterrupted preservation.

## Non-blocking suggestions and limits

| Suggestion | Coordinator disposition |
|---|---|
| Minimum/latest both select 8.2.8 | Disclosed in receipt and acceptance. Separate installations genuinely ran; no version diversity or future compatibility is claimed. No arbitrary dependency cap added. |
| Private adapter cannot prove future Textual semantics | Accepted limitation. Current shape/fault/notification/first-fault/exit/shutdown behavior is tested against the available version; semantic drift in future releases remains unverified. |
| Evidence is macOS/Python 3.11 | Retained limitation. CI configuration is inspected, not claimed executed; no Linux/full Python matrix result is asserted. |
| Byte equality is coordinator evidence, not a harness feature | Correct. Fresh artifacts/source bytes were compared by the coordinator and independently by MiniMax. The canonical harness promises archive completeness and installed execution, not a persistent source-byte comparison feature. |
| Base-Textual test assumes Textual in its interpreter | Current declared `dev` extra includes Textual; source CI installs that extra and both endpoint suites install Textual. Lean base smoke does not execute these suites. A missing development dependency produces a failure, not silent success. Explicit precondition wording is optional clarity. |
| Source-copy guard uses `assert`, disabled by optimized Python | Supported CI/harness commands use ordinary Python. Optimization flags were not an agreed execution endpoint; no optimized-interpreter assurance is claimed. Optional hardening, not a demonstrated supported-workflow defect. |
| Substring dispatch in test double | Both positive controls and intended negative failures verified; MiniMax's real-child probes and split-branch mutations support current proof. Future generated-command changes must maintain these tests. Optional explanatory comment does not change acceptance. |
| Cold-cache install timeout, inherited PATH | Actual clean installs succeeded within limits. Lane Python/pytest/console executables are explicit environment paths; future slower networks and PATH changes remain bounded operational risks, not current false-pass evidence. |
| Exact registry count, unused convenience flag, copied test bytecode, version docstring, fallback import | Optional hygiene. Current exact ten-definition contract and source-unshadowing checks pass. No acceptance-driven cleanup needed. |

## Evidence portability

Raw receipts/logs/diffs are preserved verbatim and may contain external absolute paths and trailing whitespace. Their `coordinator-r2` paths map to this directory; historical reproduction directories map to `historical/`. Mutation runner source is stored as `.py.txt` to preserve it without introducing new executable project code or changing formatter inputs. Environments, caches and verification artifacts remain outside the checkout at the recorded evidence root. The durable records include artifact hashes and exact commands; the old user `dist/` artifacts were never replaced.
