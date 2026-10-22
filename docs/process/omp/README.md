# OMP coordinator

OMP (Oh My Pi) is the alternative coordinator replacing Hermes. T3 Code remains active with its [own workflow](../planning-loop.md). Route by the application actually open: OMP uses this directory; T3 uses its existing process loops and council. Neither Hermes, Herdr, nor T3 is an OMP prerequisite. No installation, service, credential, proxy, or permanent OMP settings change is required by this workflow.

## Start directly

From the repository root:

```bash
omp --model openai-codex/gpt-6.1-sol --thinking high --no-prewalk @docs/process/omp/README.md
```

Before planning or dispatch, inspect the active runtime's model/settings readback or session evidence: coordinator must be `openai-codex/gpt-6.1-sol`, thinking `high` unless explicitly authorized otherwise. Record requested and effective configured identity separately; a catalog entry or launch argument alone does not prove execution or upstream identity. Stop if Sol is unavailable or readback disagrees; never silently switch. This entry does not resume a session, invent a goal, run plan-yolo, invoke an advisor, or automatically transition to implementation. Take the user's concrete request into the [planning loop](./planning-loop.md), then the [implementation loop](./implementation-loop.md) only after authorization and freeze.

### Herdr workers from native Tern

When the user requests Herdr dispatch, keep Sol/OMP native in Tern and use the [Herdr worker adapter](./herdr.md) for planning reviewers, implementers and final reviewers. Sol and these loops stay in charge; Herdr supplies worker panes, startup, prompts, waits and readback. Verify an authorized named session and its socket before worker operations; missing or ambiguous connection stops this route, not running outside Herdr. The adapter records the user-approved narrow exception to the installed skill's inside-Herdr gate; no installed skill/settings change is needed. Use explicit pane IDs, bounded waits and inspect-before-resend. Never silently substitute native tasks or standalone relays for requested Herdr dispatch. When Herdr is not requested, retain the standalone routes below.

**Status:** external dispatch documented/unverified; end-to-end acceptance is unsatisfied. Prior trials established Mini busy-detection failure and a full-TUI wait returning about 6.91 seconds before actual completion; both remain unresolved in the [historical evidence](../../validation/omp-coordinator/2026-10-20/herdr-dispatch.md). Native Tern placement fixes neither. A live smoke requires separate authorization.

## Roles and session choices

- **Sol coordinates:** inspect sources, plan, dispatch, verify, judge, accept, commit, and deliver. Delegate product code and tests; Sol may make administrative documentation corrections. The current documentation migration explicitly authorizes Sol to author its process documents.
- **Implementers write; reviewers inspect:** neither reviews its own implementation, delegates further, commits, or pushes. Assign one coherent implementer or genuinely independent slices with explicit non-overlapping file ownership and an integration owner.
- **Workers are session-selected:** reuse the user's authorized runtime/model/settings choices and fallback. If missing, inspect the live available choices and ask once with risk-sized recommendations. No fixed implementer roster, silent defaults, or silent substitutes.
- Native tasks may use only actual catalog-supported models **and** an effective configured model/settings matching session authorization. The current task interface rejects explicit `model` for ordinary workers (`model is only accepted for seance`); do not fabricate that argument or treat an inherited default as the user's selection. If configuration cannot be verified, use a supported external CLI with an explicit selected model, or ask. Do not edit permanent settings to force a match.
- Record requested model/settings, configured readback, runtime/modes, and provider/session evidence when available for every participant. Mark upstream identity unverified unless independently established. Different provider labels do not prove family diversity. This migration's native documentation-author dispatch inherited configuration; requested Sol identity is not proof of that effective identity.

Assign paths before any shared-checkout dispatch. T3 and OMP must not write concurrently in the same checkout/branch: use separate checkouts/branches with explicit integration ownership. Isolation prevents collisions, not malicious access. Preserve all pre-existing user edits and untracked files.

## Review policy

Classify behavior, not file extension. Low risk means obvious low-impact typos/links/formatting: coordinator inspection and gates suffice. Normal work needs one independent reviewer at planning and final review. High risk (permissions, workflow contracts, compatibility, data formats, path resolution, exit codes, or load-bearing behavior) needs two independent reviewers at both stages unless the user explicitly authorizes an exception. Use fresh contexts and separate roles; for High risk require verified distinct model families, or disclose unverified identities and obtain explicit acceptance of the named pair. Current migration is High risk with the user's one-reviewer exception: `opencode/minimax-m3.1-flash-free`, default settings, fresh plan and final sessions. It is not a future default or waiver.

Every review brief includes risk/question, authorized scope, plan/reference or draft revision, exact diff base/tree fingerprint, named sources and gate logs, prior findings when applicable, and this **verbatim** guard:

```text
READ-ONLY CRITIC TASK. You are reviewing, not implementing.

Do NOT create, edit, move, delete or rename any file in the repository. Do NOT run
any command that writes: no formatters, no linters with --fix, no install, no
git commit/checkout/stash, no snapshot or golden regeneration, no test runs that
write into the checkout. Test output, if you need it, goes only to a temporary
directory outside the repository.

If you believe a change is required, do not make it. Report it instead.

Return only the report format below. Nothing else.
```

Require `EFFECTIVE_MODEL` (requested/configured/settings/modes/evidence; upstream verified or unverified), `VERDICT` (`pass | changes_required | unverified`), `BLOCKERS` (location, problem, expected behavior, evidence), `SUGGESTIONS`, `FILES_AT_RISK`, and `CONCEDED`. Implementers report effective-model evidence, outcome, files changed, tests added, checks **not run**, deviations, and blockers. Unsupported evidence stays unverified, never inferred from the requested model.

Capture `git status --porcelain` and SHA-256 fingerprints of scoped tracked/untracked files before and after every reviewer wave, accounting for additions/deletions. These detect changes; the guard and plan/read-only modes are **not a sandbox guarantee**. If files change unexpectedly, inspect, attribute, preserve user work, report, and stop. Never blindly restore. Respect actual runtime approval restrictions; do not bypass them.

## Dispatch and completion evidence

Use tools actually available in OMP, not T3-only orchestration APIs. Retain a ledger of brief, allowed paths/ownership, task/process/session IDs, selected/configured model/settings, start/end/status, complete result/report and evidence paths. For native children retain returned IDs and actual terminal status; for external tools retain process/session and result receipts. An idle terminal, completed turn, silence, timeout, or exit zero alone is not acceptance. Require a substantive report matching the assigned acceptance criteria and inspect the delivered files/evidence.

If delivery is uncertain, inspect the original task/process and result before doing anything else; do not blindly resend or launch duplicates. A wait timeout does not establish cancellation. Confirm terminal completion/cancellation and absence of active descendants before acceptance. Clean up owned terminals/processes and only owned unused checkouts after checking for user edits; do not kill unrelated work.

### Tested external OpenCode review route

OMP can invoke this through its bash tool; create a fresh brief and unique output directory outside the checkout for each review. The brief contains the guard and required report above. Example (replace the brief and unique output paths):

```bash
node "$HOME/.agents/skills/opencode-delegate/scripts/relay.mjs" \
  --brief /tmp/BRIEF.txt \
  --model opencode/minimax-m3.1-flash-free \
  --read-only --timeout 10m --out-dir /tmp/UNIQUE-DIR
```

This tested route launches OpenCode `run --model opencode/minimax-m3.1-flash-free --agent plan --format json`; installed OpenCode 2.0.32 supports `opencode models` without a provider positional argument. Do not add `--auto` or unsupported `--pure`. Inspect the external `/tmp/UNIQUE-DIR/result.json`: require `status: completed`, `exitCode: 0`, and read the **complete** `finalMessage` for an actual verdict and model evidence. Retain that report in the dated execution record; resolve its blockers before acceptance. Use a fresh session per round. Failure/unverified output is not a pass.

This exact alias is an external CLI route, not an OMP-native task catalog entry or an interchangeable OpenRouter route. The selected external reviewer route completed successfully; that does not prove all implementer/provider routes work or independently verify upstream identity. No OMP configuration change is required.

Collect all findings into one correction brief. Follow-ups are fresh independent tasks targeting changed areas and unresolved objections; broaden review if dependencies or acceptance change. Unchanged verdicts remain valid only for verified unchanged scope. After two non-convergent rounds, stop and escalate the disagreement/evidence/options to the user, rather than launch a third broad wave.
