# Stage H accepted — 16 October 2026

Coordinator Sol accepts Stage H (F13/R01; documents R04 and accepted limitations) under frozen assessment Section 6 @ `fe6f89bc55eb3f4f04187567b968dd96ae9c86c1`, following delivered Stage G and documentation base `9faffb34a1de045e0ca25fbd79fe85116fd037da`. The owner authorized starting Stage H and selected OpenCode Nemotron 3.5 Super VL Free as sole implementer, DeepSeek V4.1 Flash Free through OpenCode as reviewer, and MiniMax M3.1 Flash through MCode when additional review was needed. All three used the owner's selected **High** setting. No product-code/test authorship was transferred to the coordinator.

## Outcome

- README, DEVELOPMENT, CHANGELOG current/unreleased content, the TUI current header/handoff and AGENTS architecture/pointers now distinguish published **0.1.1** (six line-oriented commands, no TUI extra) from current development (**C1–C5 and U1–U2 complete**, optional TUI entrypoint/controller/placeholder). **U3–U9 and 0.2 publishing remain future work.** Current verification is linked as dated evidence; coverage is accurately labeled combined, not branch-only.
- Historical phase records, released changelog entries, numerical evidence, TUI operative Sections 21–22 and old distribution artifacts are preserved. The five current documentation surfaces changed; the plan has append-only execution records and `h/` contains new measurement/review evidence.
- A reproducible benchmark measures real source `capture_session()` with byte-heavy synthetic fixtures, including largest-file size and old/new generation overlap. The [resource report](resource-risk.md) states the tracing method, observations and limitations, and documents R04 same-process sandbox state, OMP namespacing, unknown rules, frozen service use and prior Textual endpoint overlap.

## Measurements and decision

Both the worker and coordinator ran all three fixtures three times. Each used fresh synthetic HOME/XDG/sandbox inputs, exact capture-count/payload/generation checks and before/after SHA-256/mode/inventory preservation. Timed runs are untraced; traced runs begin before old-generation allocation and retain old while capturing new. These are simulated raw capture overlaps, not controller or installed-wheel benchmarks.

| Synthetic assets | Captured payload | Largest file | Retained, one generation | Retained, two generations | Transient refresh peak |
| --- | ---: | ---: | ---: | ---: | ---: |
| 8 × 2 MiB | 16,778,912 bytes | 2 MiB | ~16.04 MiB | ~32.07 MiB | ~38.08 MiB |
| 8 × 8 MiB | 67,110,560 bytes | 8 MiB | ~64.04 MiB | ~128.07 MiB | ~152.09 MiB |
| 1 × 16 MiB | 16,777,429 bytes | 16 MiB | ~16.02 MiB | ~32.03 MiB | ~80.05 MiB |

Memory is traced Python allocations, excluding pre-trace registry objects, total process RSS and native allocations. Config payload is reported separately (zero in these fixtures). The worker and coordinator agree to about 0.01 MiB on memory; timings vary and remain fixture-specific observations. [Worker raw run](benchmark-results.json), [coordinator raw run](coordinator/benchmark-results.json), [coordinator summary](coordinator/benchmark-summary.json).

**R01 remains an unbounded resource risk, not a reproduced out-of-memory failure. No memory limit, refusal, warning feature, lazy disk read, cache, database or truncation policy was added.** Future behavior changes require a separately approved policy and preservation of the frozen-generation contract. A benchmark and documentation do not bound memory. R04 is documented, not fixed; normal separate shell processes do not share its global state.

## Acceptance evidence

Coordinator inspected the entire allowed-file diff and benchmark/dependencies. Direct final local gates passed: **1,021 passed, one existing case-insensitive-filesystem skip, 91.16% combined coverage**, exceeding 90%; strict mypy clean on 37 source files; Ruff lint/format clean. [Final commands/logs](coordinator/final-gates.json), [earlier review-ready gate receipt](coordinator/gates.json).

Thirteen disposable coordinator guard/control cases exercised the actual final script, including same-size byte/mode changes, suppressed walk failures, missing/corrupt traced captures, wrong generations, capture-error state restoration, an already-active tracer and existing-output preservation. A further identity probe rejected reused old-generation buffers and then passed its restored clean control. [Guard receipts](coordinator/probe_guards.json), [raw probe](coordinator/probe_guards.py.txt), [identity receipt](coordinator/identity-probe.json). These are bounded failure/control proofs, not exhaustive correctness or a new product test framework.

DeepSeek and MiniMax both passed with no blockers in the first independent wave. All 783 repository fingerprints and full Git status matched before/after review. [Adjudication, report provenance corrections and optional suggestions](coordinator/review-adjudication.md). Configured targets/settings/modes are corroborated; upstream identity, effective effort and family diversity remain unverified. Full-access review used instruction guards and observed fingerprints, not enforced write prevention.

Two pre-council correction batches were required after coordinator reproduction of invalid retention labels, incomplete preservation/assertion checks, suppressed walk errors and stale status claims. Superseded raw outputs remain in [historical evidence](historical/STATUS.md). The worker briefly created a four-log directory outside the allow-list; its contents were inspected and preserved externally, and the deviation is recorded. `.path` remained empty, preserved and excluded throughout. Product, tests, CI, dependency declarations, lock, snapshots, goldens and original `dist/` hashes are unchanged. [Preservation receipt](coordinator/preservation.json).

Expected initial three tasks became **five**: one implementation, two pre-council corrections and two independent reviewers. All five are terminal with no pending child runs/questions; no extra worktree was created. [Terminal ledger](coordinator/terminal-task-receipts.json), [execution receipt](coordinator/execution-receipt.json). Elapsed wall time is recorded; active compute time and billed tokens are unavailable. Post-review changes are administrative acceptance/status/evidence clarifications only; the benchmark and measured artifacts are unchanged.

## Delivery and limits

Coordinator local commit is authorized by the frozen implementation loop. **No push, publication, tag or old-artifact replacement is authorized for Stage H.** Earlier Stage G delivery authorization does not extend to this commit. No new installed-wheel build or remote CI matrix run is claimed: product/test/packaging configuration matches the previous dated Stage G installed-wheel evidence. Current execution is macOS/Python 3.11 only; Linux and other Python lanes were not rerun here.

This completes the assessment repair stages A–H under their stated limits. The next feature assignment is U3 under `FULL_SCREEN_TUI.md` §22, requiring a separate start instruction. Any snapshot resource policy and 0.2 release remain separate owner decisions.
