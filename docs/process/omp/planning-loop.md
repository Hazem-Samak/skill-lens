# OMP planning loop

Sol turns a concrete request into an authorized frozen contract. Follow the [OMP entry and role/review rules](./README.md); this is not the T3 workflow. Read [project-profile.md](../profiles/project-profile.md) for correctness and gates, and [machine-profile.md](../profiles/machine-profile.md) only for relevant environment facts, not T3-only APIs.

## Start prompt

```text
Act as OMP coordinator Sol (openai-codex/gpt-6.1-sol, thinking high).
Plan <concrete request>. Verify active configured identity; do not substitute.
Read AGENTS.md, relevant specification, sources, tests, and findings.
Follow docs/process/omp/planning-loop.md. Resolve requirements and blockers,
obtain risk-sized independent review, and freeze the authorized dated plan.
Do not begin implementation automatically.
```

## 1. Inspect before deciding

Read the request, `AGENTS.md` (especially sensitive-area findings), relevant specifications (`FULL_SCREEN_TUI.md` for TUI work), source/dependencies, tests, and snapshots. Record observed behavior, evidence, and unknowns. Inspect current checkout/status; preserve user work. Ask only about unresolved choices that change behavior; reuse existing concrete authorization.

## 2. Draft the contract

Write `docs/plans/<YYYY-MM-DD-slug>.md` with:

```markdown
# Plan: <name>
Status: Draft | Agreed
Authorization: <concrete user instruction, or pending>
Reference: <pending until freeze>
Surface: omp
Risk and review: <level, reason, independent questions, explicit exceptions>
Roster: <authorized runtimes/models/settings; requested vs configured evidence>
Expected child tasks: <plan reviewers + implementers + final reviewers>

## Outcome
Observable user result.
## Current state
Verified behavior, sources, baseline evidence, unknowns.
## Scope and boundaries
Allowed paths, exclusions, ownership and checkout isolation.
## Implementation steps
Coherent phases, interfaces, dependencies and integration owner.
## Acceptance
Behavior, meaningful edge cases/tests, four project gates and delivery authority.
## Review decisions
Findings, evidence, dispositions and reasons.
```

Use the [OMP risk policy](./README.md#review-policy): Normal one reviewer, High two unless explicitly excepted. Permissions/workflow documents can be High risk. Select workers/settings per session; no unavailable-model substitute. Keep scope sufficient to implement without invented requirements. Plan product access as read-only; tests use synthetic HOME, never the user's real application state. Inspect changed snapshot/golden evidence before any regeneration.

## 3. Review independently

First inspect draft fields, relative links, allowed paths, and source-backed claims. Prepare compact evidence-first briefs using the README's exact guard and report schema. Include one clear question per critic, relevant named sources, draft revision/fingerprint, and review criteria. Verify configured runtime/model/settings match authorization; disclose upstream identity limits.

Select the dispatch route before starting any critic: inside a genuine Herdr-managed OMP pane, follow the [Herdr adapter](./herdr.md) for worker startup, prompts, waits and report readback. Do not silently replace Herdr dispatch with native tasks or standalone relays. Outside Herdr, use the standalone route unless Herdr was requested; then ask for a genuine Herdr-pane continuation, without fabricating caller context.

Capture status/fingerprints, dispatch all required reviewers before waiting, and retain the README lifecycle ledger. Each round uses a fresh independent session, not a resumed author conversation. Inspect the complete reports and post-review fingerprints. Require a substantive verdict, not idle/exit-only success; unexpected edits trigger preserve/inspect/stop. Low risk needs no critic dispatch.

## 4. Resolve before freezing

Collect coordinator and reviewer findings into one decision list. Investigate concrete evidence; user-reported failures are ground truth, not a reason to rerun merely to confirm them. Record accepted findings and corrections, rejected findings with evidence, and deferred findings only when proved outside scope or non-blocking. No in-scope blocker can remain.

Use fresh targeted follow-ups for affected review questions, carrying the original brief and prior findings/responses. Broaden review when the contract changes; unchanged conclusions require verified unchanged scope. Two non-convergent rounds require user escalation, not a third broad wave. Set `Status: Agreed` only after requirements, authorization and required independent review are settled.

## 5. Freeze in two commits

Only Sol commits. A commit cannot include its own future hash:

1. Leave `Reference:` pending and commit **only** the agreed plan:
   ```bash
   git add docs/plans/<YYYY-MM-DD-slug>.md
   git commit -m "docs: freeze plan <slug>"
   git rev-parse HEAD
   ```
2. Put that exact **full** first-commit hash into `Reference:`. Commit only this provenance change:
   ```bash
   git add docs/plans/<YYYY-MM-DD-slug>.md
   git commit -m "docs: record plan <slug> frozen reference"
   ```

The second commit cannot change the operative contract. Commit presence is not human authorization. Push only under applicable user authorization; the current migration explicitly requires `git push origin main` for each commit and agreement of `git rev-parse HEAD`, `git rev-parse origin/main`, and `git ls-remote origin refs/heads/main`.

Before affected implementation, **both coordinator and implementer** inspect the referenced frozen version and confirm every approved operative amendment is included. Behavior, scope, compatibility, permissions, machine changes, or execution-contract amendments require explicit applicable authorization and a new two-commit freeze. Reuse authorization already covering the concrete action. An arbitrary newer plan commit cannot override the frozen reference.

Append-only execution records may log authorized roster choices, evidence and receipts; they cannot amend operative behavior. Finish with all reviewers terminal and owned resources cleaned up. Only after the freeze is verified and implementation authorized, proceed to the [OMP implementation loop](./implementation-loop.md).
