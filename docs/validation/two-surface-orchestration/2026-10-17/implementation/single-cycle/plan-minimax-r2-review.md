# MiniMax R2 critic review — Herdr single-cycle trial draft

## Summary

Goal: targeted second-round critic review of one bounded HIGH-risk execution-contract
amendment and its native handoff, answering only whether the two R1 blockers (missing
`Surface:` declaration; missing explicit frozen-reference verification) are resolved by the
added declaration plus the fail-closed Entry-gate procedure, with actual hash substitution
checked at final review.

Scope: read-only review of two draft documents and their process constraints. No code, no
process-document change, no live Herdr, no delegation, no P01-P09 hardening reinstated as a
trial gate, and no demand for a commit hash that does not exist until the freeze commits are
made.

Key decision: both R1 blockers are resolved by text that is present and operative, so the
verdict is `pass`. Two residual items are recorded as non-blocking suggestions (the reviewed
text no longer matches the recorded pre-R2 snapshot hash; the Entry gate names the authority
plan's frozen text but does not explicitly name the handoff brief in the same comparison).

This plan authorizes no implementation. It is the critic's review record.

## Reviewed artifacts (fingerprints of the exact text reviewed)

- `docs/plans/2026-10-18-herdr-single-cycle-trial.md` — SHA256 `35c74fe2f3adb12f014b54c0b06f6b5a2c976fae76c2a24fd2ed5e0a42dff3a4`
- `docs/validation/two-surface-orchestration/2026-10-17/implementation/single-cycle/coordinator-brief.md` — SHA256 `214e390abe1d036b63f1dbc2dd420c1744a9b7b3d682cbbc73eb9d298366404b`
- Baseline: HEAD `9a1e78c`; `git status --porcelain` = `?? .path`, the plan file, the `single-cycle/` record directory — matching `preparation-review-before.json:2-3`.
- `preparation-review-before.json:48` and `:739` record `d6b92831…` / `b4f432dc…` — the pre-R2 text, not the R2 text.
- Process constraints read: `docs/process/council.md` (§2 guard, §4 report/EFFECTIVE_MODEL, §5 high-risk counts, §6 receipt), `docs/process/planning-loop.md`, `docs/process/implementation-loop.md`.

## R1 blocker disposition

| R1 blocker | Current evidence | Status |
|---|---|---|
| Missing `Surface:` declaration | plan `:4` `Surface: t3 (preparation and evidence review); herdr (the disposable live trial).`; brief `:4` `Surface: herdr (T3 prepares and later reads evidence).`; brief `:146` result.json `surface=herdr` | resolved |
| Missing explicit frozen-reference verification | plan `:8` reference pending until two-commit freeze; brief `:5-7` reference pending, T3 must insert full frozen commit after provenance commit and before final review/delivery, unresolved reference prohibits live use; brief `:31-35` Entry gate reads the authority plan's Reference, verifies that exact commit contains the approved narrowed trial contract, requires current operative text to match frozen text except the reference/provenance record, stops on absent/pending/mismatched reference; brief `:34-35` Gemini must verify the fixture plan's frozen commit; plan `:119-120` hash filled after freeze before final handoff review | resolved |

Fail-closed property verified: the pending reference is a prohibition, not a soft note, and
both the coordinator Entry gate and T3's pre-live substitution step carry it.

## Residual items (non-blocking, coordinator-owned)

1. Refresh the preparation snapshot so the recorded manifest pins the R2 text (`35c74fe2…` /
   `214e390a…`) rather than the pre-R2 hashes; otherwise the acceptance record anchors to text
   that was superseded.
2. Optional one-clause tightening: name the handoff brief alongside the plan in the Entry-gate
   comparison, so a post-freeze edit of the brief is detected by the same `git show` check.
   Mitigated today by T3's allowed-file diff verification and the coordinator's own
   original-repository manifest.

## Acceptance criteria for the coordinator's final preparation

- Exact R2 text frozen in the two-commit sequence; full hash substituted into plan Reference and brief `:5-7` before final review/delivery.
- Both `Surface:` declarations present in frozen text and repeated in `result.json`.
- Four product gates rerun on the final preparation; original repository unchanged apart from the allowed files; `.path` preserved.
- DeepSeek's completion remains the behavior/test axis; its first task without a verdict is not approval.

## Unresolved decisions / risks

- Upstream served model identity for every named pair (MiniMax, Qwen AnyModel, DeepSeek WorkBuddy, Gemini/agy, `gpt-6.1-sol`) stays unverified under the user-accepted named-pair policy; carried forward unchanged, not a trial gate.
- `preparation-review-before.json` currently pins superseded hashes (see Residual item 1).
- Two-round non-convergence escalation still applies; no third broad wave.

## Constraints carried into any later execution

Read-only for this turn: no repository file created, edited, moved, deleted or renamed; no
formatter, linter `--fix`, install, git mutation, snapshot/golden regeneration, or test run
writing into the checkout. No delegation, no control of live Herdr, no ccr recovery calls. If
a change is required, it is reported, not made.