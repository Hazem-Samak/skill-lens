# OMP coordinator migration acceptance

Surface: omp; T3 Code remains separately active.
Frozen plan: [2026-10-20-omp-side-by-side-coordinator.md](../../../plans/2026-10-20-omp-side-by-side-coordinator.md) at `216cea31cc0ac1c0ad8b1557441bf59aec141031`; reference-only provenance `3edd82ab8d73e59233eb22db5d5d9f0fe9a44f98`. Both commits pushed with local/tracking/remote equality.

## Delivered scope

- [OMP entry](../../../process/omp/README.md) and dedicated [planning](../../../process/omp/planning-loop.md) / [implementation](../../../process/omp/implementation-loop.md) loops. Fixed coordinator `openai-codex/gpt-6.1-sol`; workers selected in the session, not a fixed implementer roster.
- Existing T3 planning, implementation and council documents remain active. Each receives exactly one additive routing blockquote; an exact original-line comparison found no deletion or replacement.
- The old single-cycle Hermes/Herdr trial receives only a historical-status pointer. No trial is claimed passed, and no Herdr pilot is required for OMP.
- Product code, tests, dependencies, registry, installed runtimes, services, credentials and persistent settings unchanged. Existing `.path` and the untracked 2026-10-19 coordinator draft are preserved and excluded from staging.

## Direct evidence

- OMP 18.12.3 help and catalog identify `openai-codex/gpt-6.1-sol`; OpenCode 2.0.32 lists `opencode/minimax-m3.1-flash-free`.
- Fresh exact-Sol OMP no-tools launch returned `OMP_SOL_COORDINATOR_OK`, exit 0, 3.35 seconds. No provider configuration/authentication change was needed.
- OMP bash → installed OpenCode relay → exact free MiniMax CLI route completed with real reports. This is external CLI delegation, not an OMP-native model alias. Full plan reports and session receipts: [plan-review.txt](./plan-review.txt).
- Native documentation authors `OmpWorkflowAuthor` and `SurfaceRoutingAuthor` completed with disjoint ownership; runtime contexts identify configured `openai-codex/gpt-6.1-sol`. Independently verified upstream identity is not claimed. They ran no gates/formatters and did not commit.
- Scoped validation: 34 local links/anchors resolved; OMP read-only guard matched the T3 guard verbatim; preserved user-file hashes matched. No LSP diagnostics are applicable: only Markdown/text files changed.

- Documented startup was also exercised with `--thinking high` and `@docs/process/omp/README.md` in a fresh no-tools print session. It returned the exact requested coordinator ID, `OMP_WORKFLOW=docs/process/omp/planning-loop.md`, and `T3=active and separate`, exit 0, 2.78 seconds.

## Verification

Baseline, directly run by coordinator before author dispatch:

```text
uv run pytest --cov=skill_lens  1082 passed, 1 skipped; 91.16% combined coverage
uv run mypy                   clean (38 source files)
uv run ruff check .           passed
uv run ruff format --check .   270 files already formatted
```

The skip is the existing case-insensitive-filesystem scenario. Final coordinator run after all workflow/notice edits also passed: **1082 passed, 1 skipped; 91.16% coverage**, mypy clean (38 files), Ruff lint clean, Ruff format clean (274 files). Pytest took 79.47 seconds; the complete gate chain took 80.29 seconds. Raw session evidence: `artifact://24` (baseline `artifact://11`). Final review passed against these unchanged operative files; append-only acceptance/report evidence does not alter their contract or invalidate these checks.

## Execution receipt

Expected: two Sol author tasks, one plan reviewer, one fresh final reviewer.
Actual: two completed Sol author tasks and four OpenCode launch attempts (one CLI flag failure, two completed plan reviews, one completed fresh final review). The first launch used unsupported `--pure`; it failed before any review and was retried without that flag. Plan R1 exposed route/staging ambiguity; corrected in one batch, targeted R2 passed. The initial task call's explicit model field was rejected before any agents launched; the successful author batch inherited configured Sol, reported as such. This API mismatch was reported to the tool maintainers.

Reviewer's requested/configured route is OpenCode MiniMax, default settings, `plan` agent; upstream identity remains independently unverified. Completed plan relay receipts each report cost USD 0; billed token counts are not supplied in result.json. Plan R1 took 173.83 seconds; targeted R2 took 39.32 seconds. Sol author durations: 107 seconds and 17 seconds. No claim of measured savings or broader provider support.

## Preservation fingerprints

```text
.path: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
2026-10-19-herdr-omp-coordinator.md: 7eb7720a8b2d4531b04b284bf7ac677787561e2d36dd6c7db10055fecf178f11
```

## Final acceptance

Accepted: the bounded OMP coordinator migration is complete; T3 remains independently active. MiniMax's fresh final review passed with no blockers: [complete report and receipt](./final-review.txt), OpenCode session `ses_ea9deef00ffei77VWFgstG6wHN`, exit 0, 255.57 seconds, reported cost USD 0. All 12 pre-review file fingerprints and exact repository status matched after review. Both author tasks and every launched external process completed; no active child work remains.

Non-blocking suggestions require no operative change: the author exception is already explicitly tied to the current migration; the unsupported flag warning is about the installed OpenCode command, and its exact failed-launch stderr is now retained in final-review.txt; the machine-profile link already excludes T3-only APIs. No provider route other than the demonstrated Sol/native-author and external OpenCode reviewer paths is claimed tested. No upstream model identity verification is claimed.

Only this acceptance receipt and the retained final report were added after the green checks and review; all seven operative workflow/notice files remain identical to the reviewed tree. Stage only the ten authorized workflow/notice/evidence files. The coordinator commits and pushes the accepted result under the frozen delivery contract; the final chat records the resulting commit. No human configuration action is required.
