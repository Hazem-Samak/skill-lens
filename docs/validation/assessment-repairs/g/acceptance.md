# Stage G accepted — 15 October 2026

Coordinator accepts Stage G (F10/R02) under frozen assessment `fe6f89bc55eb3f4f04187567b968dd96ae9c86c1`, following accepted Stage F `491f9ce5902f98a7dd687c03418c308dcb88bcfd`. The owner authorized starting Stage G after delivery of D/E/F. Antigravity Gemini 3.8 Flash High remained the sole product/test implementer; MiniMax M3.1 Flash through mcode and Muse Spark 1.3 Free through OpenCode remained independent critics, both at the owner's selected xHigh setting.

## What now works

- One canonical archive/install harness checks required TUI modules, all ten registry definitions and the typing marker in fresh wheel/sdist artifacts. Tests exercise those actual validators; removing required content makes them fail.
- CI has separate archive, base, minimum and latest dependency checks. Clean base installation verifies Textual is absent and preserves bare-help/explicit-TUI behavior. Separate extra installations execute real TUI lifecycle, session, fault, shutdown and output-parity suites outside the checkout, with installed-module origin checks and no copied source package.
- The private Textual fault attributes and hook are accessed through one narrow adapter. Missing/non-callable hooks and unusable notification events fail explicitly; first-fault recording, notification, internal exit behavior and prompt shutdown are exercised.
- Existing `textual>=8.2.8` policy is retained. A constrained minimum install and a separately resolved unconstrained latest install both currently select **8.2.8**. This overlap is disclosed; it provides two installation checks, not two-version coverage or a guarantee about future Textual releases.

## Acceptance evidence

Coordinator inspected the complete eight-file product/tool/test diff and consumers. Allowed changes: `.github/workflows/ci.yml`, `scripts/smoke_wheel.py`, `skill_lens/tui/{__init__.py,app.py,_textual_compat.py}`, `tests/{test_tui_packaging.py,test_tui_read_only.py,test_stage_g_repairs.py}`. No core, registry, public JSON/model, dependency declaration, lock, snapshot or golden changes. Administrative evidence and an append-only plan execution record were added afterward.

Final direct source gates: **1021 passed, one existing case-insensitive-filesystem skip, 91.16% combined coverage**, exceeding 90.0%; strict mypy clean on 37 source files; Ruff lint/format clean on 148 files. [Exact commands and logs](coordinator/gates.json). Coverage is the combined score with branch measurement enabled, not branch-only coverage.

The coordinator freshly built wheel/sdist into an external output directory, verified packaged source bytes and corrected test/harness bytes, and invoked the real harness with relative paths from outside the checkout. Base Textual absence passed; separate minimum/latest installations each passed **353 tests with zero skips**, including unchanged snapshots/goldens. Installed package/TUI origins were inside their respective environments. [Installed receipt](coordinator/installed-receipt.json), [build/run receipt](coordinator/installed-run.json), [build log](coordinator/build.log) and [installed log](coordinator/installed.log).

Reviewed wheel SHA-256: `59707ca7bc191c051ad98556bc6246b81e0199333a600902e1f4dd4ea170ef32`.
Reviewed sdist SHA-256: `273ef448502ffcd3a0f08f1e4fcdc5ed52bf9920d7ccde3b80e0ce3194ee9dc1`.
These are verification artifacts built before the acceptance documents were added, not release artifacts. The original local `dist/` files remain unchanged.

Twenty independent disposable production/CI mutations each have clean/mutant/restored exits **0/1/0**, with source hashes, exact diffs, commands, imported-source provenance and behavioral failure logs in [mutation receipts](coordinator/mutations.json). The original fourteen were rerun after the final correction; six more independently cover base origin, each endpoint origin branch, Textual absence, installed-suite failure and copied-source rejection. Raw runner: [run_mutations.py.txt](coordinator/run_mutations.py.txt). Selected mutations prove those guards, not exhaustive correctness.

Both round-two critics returned **pass/no blockers** after the four first-round assurance gaps were independently reproduced and corrected by Gemini. Only `tests/test_tui_packaging.py` changed after the first council. MiniMax independently reproduced the six corrected guards and full suite; its complete verdict was recovered from its external report because the task summary omitted it. All **602 repository fingerprints and Git status** matched through both reviews. [Combined adjudication and limits](coordinator/council-r2-adjudication.md).

Expected initial three child tasks became eight: one implementation, two pre-council corrections, two first-round reviews, one test-only council correction and two targeted follow-up reviews. All eight completed with no pending child runs or questions; no extra worktree was created. [Execution receipt](coordinator/execution-receipt.json), [terminal task ledger](coordinator/terminal-task-receipts.json), [wall times](coordinator/task-timings.json). Active compute time and billed tokens are unavailable. Configured targets/options/modes are corroborated; upstream served identities, effective effort and family diversity remain unverified under the owner-selected named pair.

## Preservation and delivery boundary

An early correction worker deleted the pre-existing empty untracked `.path` contrary to its instructions. Coordinator checked its baseline empty hash and restored the exact bytes using exclusive creation; [preservation receipt](coordinator/path-restoration-receipt.json). Final `.path` and original wheel/sdist hashes match baseline. `.path` remains excluded from the commit.

Local commit is coordinator-owned and authorized by the frozen implementation loop. The later push instruction delivered accepted D/E/F; the frozen no-push boundary still applies to this Stage G commit. No publishing, tagging, old artifact replacement or Stage H work is included. Stage H is the next authorized-plan stage, but requires a separate start instruction. Local evidence covers macOS/Python 3.11; Linux, CI execution and the complete Python matrix were not independently run for this stage.
