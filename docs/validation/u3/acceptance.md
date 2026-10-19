# U3 Home technical acceptance — 19 October 2026

Sol accepts U3 against `docs/plans/2026-10-19-tui-u3-home.md`, operative frozen
commit `ce86db945fc44569f3a5cd4f0fb66a111a5d00f2`. Implementation base was
`b250576de87820762289b6a6bf9100ce54d6e4be`. The later roster and execution
appendices do not change the frozen contract.

Home now shows the captured skill catalog, a keyboard-accessible scrollable
metadata preview, text and agent filters, and optional per-agent resolution
states. Selection uses installation identity; late worker results cannot replace
newer context. Navigation uses captured data. The CLI, controller, core engines,
models, registry, dependencies, snapshots and goldens are unchanged.

## Verification and independent review

- Direct coordinator gates: **1082 passed, one expected macOS case-insensitive
  filesystem skip, 91.16% combined coverage** (Home 91%). Strict mypy passed on
  38 source files; Ruff lint and formatting passed. Logs and exact reviewed
  source hashes: [review-ready-r2](coordinator/review-ready-r2/verification.json).
  Final checks after administrative acceptance edits are recorded separately in
  `coordinator/final-gates/commands.json` and its four logs.
- The synthetic benchmark mounts the actual Home widgets with 600 skills and
  checks fixture preservation, one Why call per distinct lookup group, active
  navigation/filter/quit and an injected-delay measurement. Coordinator and
  reviewer independently reproduced its evidence. This is one-machine evidence
  with no invented speed threshold; see the [walkthrough](../../TUI_U3_WALKTHROUGH.md).
- All six planted mutations fail on intended assertions; all unmodified and
  restored controls pass. [Coordinator receipt](coordinator/review-ready-r2/mutations.json).
  The final added case proves a rejected old outcome preserves the exact newer
  owned request while that request is still running, then proves queue recovery.
- [MiniMax final R1](coordinator/minimax-final-r1.md) found that missing test
  category; Sol independently reproduced it and DeepSeek corrected it without
  changing product code. [MiniMax final R2](coordinator/minimax-final-r2.md)
  returned **PASS, no blockers**, independently reproduced all four gates and
  all six mutations, and confirmed repeated clean/mutant test discrimination.
- Sol compared all **1138 protected files**, HEAD and Git status before and after
  R2: no changed, missing or added files. The critic's Full access mode relied on
  instructions and verification, not an enforced read-only filesystem.

## Adjudication and limits

The plan's acceptance criteria are satisfied. The F1–F7 coordinator findings and
the final-review test gap are resolved. The authorized status edits now describe
U1–U3 as complete development work and identify U4 as next; operative sections
21–22 and historical measurements remain unchanged.

Nonblocking follow-ups are recorded for U4: coverage of the identity-matching
rejected-request branch at `home.py:495–499`, the unused `error` parameter, and
the package's U2-era header/exports. No known behavior defect is being deferred,
and the uncovered branch is not claimed to be unreachable. The mutation harness
keeps its receipt-regenerating default; read-only reviewers must supply an
external `--out` path. Historical implementer hashes describe their report-time
snapshot; Sol subsequently refreshed walkthrough §5 and acceptance status, so
the reviewed hash belongs to `review-ready-r2/verification.json`.

Human visual approval, unexecuted CI lanes, release tags and 0.2 publishing are
not claimed. The benchmark's active filter uses `Input.Changed`; Pilot key round
trips include event-queue overhead. The default payload budget does not bound
discovery's earlier source parsing. U4 must explicitly address Home and the
dedicated Why screen sharing the controller's single active Why request.

## Roster, execution and delivery

Sol `codex/gpt-6.1-sol` High coordinated, verified and accepted. DeepSeek
`opencode/deepseek-v4.1-flash-free`, `variant=high`, implemented; MiniMax
`opencode/minimax-m3.1-flash-free`, `variant=high`, independently reviewed.
The owner authorized this sole-reviewer roster and the fallback from Pi after
three unsuccessful runs. Upstream model-family identity remains unverified.

The [task ledger](coordinator/task-ledger.json) records **11 explicit launches**
against an initial expectation of three: planning R2, failed Pi attempts,
OpenCode fallback and batched corrections, and final targeted review R2 account
for the difference. Three automatic background resumptions in the OpenCode
implementation thread are separate from explicit launches. All tasks are
terminal with no pending children or questions; no owned worktree needs cleanup.
Planning launch to acceptance audit was approximately **3 h 5 min**, including
provider waits and interruptions, not active compute time. Billed tokens and
active compute time are unavailable; no cost or efficiency claim is made.

Sol owns the feature commit and push. Identify the delivery commit with
`git log -1 -- docs/validation/u3/acceptance.md`; local HEAD, `origin/main` and
GitHub's main ref are compared after push. The pre-existing empty untracked
`.path` is preserved and excluded from delivery. No U4 implementation is started.
