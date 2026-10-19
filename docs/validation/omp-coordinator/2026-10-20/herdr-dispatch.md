# OMP Herdr dispatch: documentation ready, live check blocked

Frozen amendment: [2026-10-20-omp-herdr-dispatch.md](../../../plans/2026-10-20-omp-herdr-dispatch.md) at `2656a6a1efb687b0d23c9679fdc2222cc18c07b0`; reference-only provenance `c4aa2273f0cae0b54e9c90f3ab0c2baf0bc64a97`. Each pushed to origin/main with full local/tracking/remote equality.

## What changed

- Added the [Herdr dispatch adapter](../../../process/omp/herdr.md) and route-selection links in OMP's entry, planning loop and implementation loop. Genuine Herdr-managed OMP runs use Herdr worker panes/startup/prompts/waits/readback; standalone OMP retains its existing routes. No silent substitution for requested Herdr dispatch.
- Existing Sol identity, user-selected workers, reviewer guard, independent review, read-only product policy and coordinator-owned verification remain intact. T3 process documents, product/tests, settings, authentication, services and installed agents are unchanged.
- Existing `.path` and the untracked 2026-10-19 coordinator draft remain untouched and unstaged.

## Evidence and limits

The caller's inherited context was actually checked:

```text
HERDR_ENV=
HERDR_WORKSPACE_ID=
HERDR_TAB_ID=
HERDR_PANE_ID=
```

Therefore **live verification is blocked**. No Herdr CLI session discovery or pane control was attempted; no environment context was fabricated. Syntax guidance comes from the loaded installed `herdr` skill. Installed CLI help, supported agent kinds, native model arguments, actual detection, prompt submission and report readback must still be verified inside Herdr. No guessed MiniMax startup command is advertised as executable.

Coordinator validation found 18 relative links/anchors resolving and the existing reviewer guard unchanged. No LSP diagnostics apply to Markdown/text-only changes. A no-tools OMP launch checks instruction loading only; it is not a live Herdr dispatch test. Four-gate and smoke outcomes are appended after completion.

## Review and execution receipt

Reuse the migration's selected Sol 6.1 author/coordinator and one OpenCode MiniMax M3.1 Flash Free reviewer, default settings. Independently verified upstream identity is not claimed. [Plan report](./herdr-plan-review.txt): pass, no blockers; OpenCode session `ses_ea9cce0d3ffeyDu2fUNMinRPMB`, completed/exit 0, 35.72 seconds, reported cost USD 0. Review ran through the standalone external CLI, not Herdr; it proves document review only. Expected two reviewer launches (plan and fresh final), no delegated authors or product implementers; Sol makes the small document edits. Billed token counts are unavailable in relay result.json.

## Human step needed for live acceptance

Open a real Herdr shell pane at this repository and run:

```bash
omp --model openai-codex/gpt-6.1-sol --thinking high --no-prewalk @docs/process/omp/README.md
```

Then ask:

> Continue the authorized Herdr smoke from docs/plans/2026-10-20-omp-herdr-dispatch.md and docs/process/omp/herdr.md. Verify the real inherited caller and installed support, run one harmless unique-token task through the selected OpenCode MiniMax reviewer in one owned sibling pane, inspect its matching report and actual completion, preserve unrelated panes, and append evidence here. Stop and ask on missing support or model mismatch; do not install, repair detection or substitute models.

The documentation can be committed, but the requested end-to-end integration remains incomplete until that live check passes. No claim of verified Herdr support is made by this record.

## Coordinator checks

- `uv run pytest --cov=skill_lens`: 1082 passed, 1 filesystem-dependent skip; 91.16% coverage; 79.40 seconds.
- `uv run mypy`: clean, 38 source files.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 277 files already formatted.
- Full gate chain: 80.50 seconds; session output `artifact://40`. Existing unchanged session evidence supplied the pre-edit baseline.
- No-tools instruction-loading smoke: Sol loaded the updated OMP entry and Herdr adapter and correctly reported stopping Herdr inspection/dispatch with unset context, using Herdr workers inside a genuine pane, and preserving T3. Exit 0, 3.63 seconds. This checks instructions only, not Herdr execution.
- Each existing OMP document has exactly one insertion; all original policy lines remain intact. The new adapter's local links resolve; the original guard and user-file fingerprints remain unchanged.

## Documentation acceptance and remaining blocker

MiniMax's fresh [final review](./herdr-final-review.txt) passed with no blockers, session `ses_ea9c98be2ffe4xFREzSFsThQeL`, completed/exit 0, 83.29 seconds, reported cost USD 0. Actual reviewer launches: two, both completed; no active child work remains. Requested/configured model is the selected OpenCode MiniMax alias; upstream identity remains unverified. Final review ran from `2026-10-19T22:09:31.585Z` to `2026-10-19T22:10:54.834Z` (UTC).

All nine scoped pre-review fingerprints and exact repository status matched after review. The checked/reviewed operative document SHA-256 values are retained below; no operative edits followed the gate/smoke run or review. Only append-only evidence was completed afterward.

```text
103f2a044c8ba2feed272e209f648326b9d779580cfe2729731d85553d1af950  docs/process/omp/README.md
3c3fa695f5ea96051ad8f89c6c04e66cc21804675f6e97ae0abfda520de3d7de  docs/process/omp/planning-loop.md
10da25a2dedb5e792eed21247454b82264d92ccc3a486957766521a4363264c4  docs/process/omp/implementation-loop.md
7f5cb6aa83f6aaa0a4536fb246626e8d47933841338f8c3d471e9b36e835a721  docs/process/omp/herdr.md
```

Optional reviewer notes: retained operative hashes and review timestamps for evidence binding; no policy edit required for model settings because the adapter explicitly retains authorized settings and links the entry's exact `--thinking high` launch. Agent-name validation remains the installed CLI/skill's responsibility; templates deliberately require discovered supported names/arguments, rather than claiming unverified runtime execution.

**Accepted documents only; live check still blocked.** The human startup/continuation instructions above are the exact remaining prerequisite. Do not mark end-to-end Herdr orchestration complete until a genuine Herdr-managed OMP session records the successful worker run.
