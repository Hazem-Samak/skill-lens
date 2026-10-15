# Stage F accepted — 15 October 2026

Coordinator accepts Stage F (F15/F16 and F11 agents rendering) under frozen assessment `fe6f89bc55eb3f4f04187567b968dd96ae9c86c1`, following accepted Stage E `3762f1059fe34e79a0c1e93fc5032600bb648b78`. Owner explicitly authorized Stage F with sole Gemini 3.8 Flash High implementer and independent MiniMax M3.1 Flash/mcode plus Muse Spark 1.3 Free/OpenCode, both xHigh.

## What now works

- Adding or removing a final newline produces conventional “No newline at end of file” markers in live and captured diff models/JSON and terminal output. Added/removed files and empty-versus-single-newline cases are covered. CRLF/LF equivalence and lone-CR semantics are preserved.
- Markers consume character budget, never changed-line or old/new hunk counts, and stay attached to the line they explain during truncation. Range starts, omitted counts and no-context-only-hunk behavior stay correct.
- Suppressed copies cite the actual winning root/rule/evidence even when a nested winner is displayed COEXISTS. The causal winner comes from precedence, not presentation state. Ambiguous/merged policies do not acquire fabricated suppression. Disabled/invalid eligibility and OpenCode specificity remain intact.
- Full real-registry agents output and literal unusual agent labels are pinned at fixed width by real rendering tests.

## Acceptance proof

Coordinator inspected the complete five-file product/test change and its consumers, source-matched all guard mutations, and verified allowed-file accounting. Product edits are core/diff.py, core/resolver.py and marker documentation in models/diff.py; tests are new test_stage_f_repairs.py and test_render_snapshots.py. Public JSON keys are unchanged. No existing snapshot/golden changed.

Direct final gates: **989 passed, one existing filesystem skip, 91.11% combined coverage** against 90.0%; mypy strict clean on 36 files; Ruff lint/format clean on 138 files. [Exact gate commands/results](coordinator/gates.json). Fourteen independently executed disposable production mutations each have clean/mutant/restored0/1/0 with exact diffs, hashes, source provenance and failure logs in [mutation receipts](coordinator/mutations.json). Additional coordinator evidence covers 4235 generated budget cases and a true nested COEXISTS-winner snapshot_why after source deletion with disk/path/environment-helper tripwires. No full Linux/CI/version-matrix or exhaustive-correctness claim.

MiniMax and Muse both pass/no blockers. All 515 hashes and Git status stayed unchanged throughout the review wave; administrative records were added afterward. The two pre-council assurance failures were reproduced and corrected by Gemini before review. No product/test change followed the final direct gates or reviews. [Council adjudication](coordinator/council-r1-adjudication.md) records complete report delivery, identity/format limitations and every non-blocking disposition. Reports and original briefs are adjacent.

Expected three launches, actual four due to one pre-council proof correction. One substantive council wave. All four tasks completed/no pending; [execution receipt](coordinator/execution-receipt.json) records wall time and exact task identity/timing. Active compute and billed tokens unavailable. No extra worktree created. Pre-existing empty `.path` preserved/excluded.

## Delivery boundary

Local commit is authorized and coordinator-owned. Frozen plan excludes push/publish/tag/dist replacement. Stage G is next and has not started. Commit identity is reported after creation; this file cannot contain its own future commit hash. Optional review suggestions are retained without expanding this accepted batch.
