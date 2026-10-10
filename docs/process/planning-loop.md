# The Planning Loop

**What this is.** How a request becomes a frozen, committed plan. Nothing is coded until the plan is committed.

**Who does what.** The coordinator (**Sol / Codex `gpt-6.1-sol`**) runs this loop and never writes product code. Independent critics (**Pi / Grok / OpenCode pool**, selected by USER per session) review the plan under instruction-based read-only restraint. Antigravity implements the plan later, in `implementation-loop.md`.

Read first: [`council.md`](./council.md) (roles, guards, and permissions), [`profiles/project-profile.md`](./profiles/project-profile.md) (what "correct" means here), and [`profiles/machine-profile.md`](./profiles/machine-profile.md) (live machine facts and provider policies).

---

## Usable Start-Planning Prompt Example

To initiate a planning turn as coordinator in T3 Code:

```text
Act as coordinator Sol (Codex gpt-6.1-sol). Inspect the user request for <feature/bug>.
Read AGENTS.md §4, SKILL_LENS_SPECIFICATION.md, and relevant findings.
Follow docs/process/planning-loop.md, council.md, and profiles.
Draft docs/plans/<slug>.md, preflight runtime mode, and dispatch independent critics from the review pool.
```

---

## Step 1 — Inspect

Read before writing anything:

1. `AGENTS.md` — especially **§4**, which names load-bearing findings files.
2. The request, and the relevant parts of `SKILL_LENS_SPECIFICATION.md` (and `FULL_SCREEN_TUI.md` if touching TUI).
3. The source: engine, model, CLI commands, and registry TOML.
4. The tests, including gate tests and snapshots.
5. Any findings file from `AGENTS.md` §4 covering the target area.

Then **write down what you do not know** under `## Current state` or `## Open questions`.

**Ask the user only about requirement choices** — where multiple readings are plausible and lead to different behaviors. Ask in plain English, one question at a time, with a recommendation.

---

## Step 2 — Draft

Write the plan to `docs/plans/<slug>.md` using this template:

```markdown
# Plan: <name>
Status: Draft | Agreed
Authorization: <existing user instruction, or "pending">
Reference: <filled in at Step 5 with the frozen commit hash>

## Outcome
What the user can do after this change that they cannot do now.

## Current state
Relevant facts, file:line references, known limitations, open questions.

## Scope and boundaries
What changes. What does not. Constraints.

## Implementation steps
Small coherent steps with the expected files.

## Acceptance
Observable behaviour, the edge cases that matter, and the four gates.

## Review decisions
Accepted, rejected and deferred findings, with one-line reasons.
```

`<slug>` is short, kebab-case, and dated: `2026-10-10-feature-name.md`.

**Decide the review level now** (`council.md` §5):
- Low risk: Coordinator plans alone (strictly limited to obvious low-impact work, typos, formatting/docs). Internal refactors touching load-bearing behavior remain High risk; substantive refactors are at least Normal risk.
- Normal risk: 1 independent critic.
- High risk: 2 independent critics from verified different model families (or explicit user acceptance of named pair with unverified family).

---

## Step 3 — Review

Independent critics check the draft before any code is written.

1. **Per-session model and settings selection by USER:** The human user explicitly selects critic models AND settings (options) from the live catalog (`orchestrator_capabilities`). If choices are missing, present an ask-once menu showing the live pool and options with recommended risk-sized choices. Reuse authorized choices across rounds within the session; do not silently substitute unapproved models or options.
   - **Context independence:** Running a critic in a fresh delegated task provides role and context independence (isolated subagent context, dedicated prompt, separate reasoning chain). Avoid categorical claims that same-family models cannot provide independent context.
   - **Family diversity requirement:** High-risk reviews strictly require verified distinct model families when established. Sharing a coordinator (OpenAI) or implementer (Google) family does not satisfy the requirement. Different providers alone do not prove different model families; unknown family identity stays unverified.
   - **Unverified-family operational path:** If a selected model family cannot be verified, disclose which identity is unverified and obtain explicit user acceptance of the named pair for that session before proceeding. Never claim verified family diversity when unverified.
   - **Session evidence (2026-10-10 migration):** OpenCode was selected with `opencode/space-bunny-free` (`variant=max`), and Pi was selected with `tokenharbor/deepseek-v4.1-flash:free` (`thinking=max`). Because Space Bunny's upstream model family could not be verified, this session operated under an explicit user-accepted exception ("Keep the selected pair and record the unverified family") rather than verified family diversity. This is an explicit session-specific accepted exception, not a permanent default or blanket future waiver. USER model and settings choice per session remains mandatory.
2. **Preflight caller mode:** Check coordinator configuration with `t3_thread_configuration`. Confirm caller is in Full access before launching children; child mode cannot exceed parent mode (`runtime_mode_escalation_denied`). Never dispatch broader children or silently downgrade child permissions (silent lowering is forbidden). Reuse existing user Full access authorization without repeatedly asking for already approved choices. If the caller is not in Full access, request that the user switch to Full access in the composer to activate the authorized mode, and verify via readback on the subsequent turn. If the surface cannot operate in the authorized mode, report the actual needed human step.
3. **Dispatch settings:** Dispatch critics via `delegate_task`:
   - `runtimeMode: "full-access"` (Hazem's standing preference)
   - `interactionMode: "plan"`
   - `role: "review"`
   - `mode: "async"`
   - Target: explicit `providerInstanceId`, `model`, and `options` (placeholders representing user-selected choices; see structured example in `council.md` §3).
   - Stable `clientRequestId` per round.
   - Calling `delegate_task` returns `taskId` and `childRunId` (which is `string | null` and may be null until assigned by the runner). Retain both in the ledger to match the original delegated run; if `childRunId` is initially null, refresh via `task_status` readback once assigned rather than treating it as a missing ledger failure.
4. **Verbatim guard:** Paste the exact read-only guard text from `council.md` §2 into every critic prompt.
5. **Distinct review questions:** Give each critic a different question (e.g. project rules/compatibility vs behavior/test gaps). Give the critic the evidence before stating coordinator conclusions.
6. **Asynchronous barrier:** Dispatch all critics before waiting on any of them. End the turn for reactive wakeup, or use bounded status checks. Never treat silence as failure or approval. Distinguish `workState=waiting_for_children` from terminal `result_available`. A completed turn alone is not task acceptance.
7. **Pre/post fingerprints:** Take SHA-256 fingerprints and `git status --porcelain` before and after dispatch. If a critic touches files, do **not** run blind `git restore`: detect, inspect, attribute, and preserve user work.

---

## Step 4 — Resolve

For every finding in the critic's report format (including `EFFECTIVE_MODEL`):
- **Accept:** Update the plan and note why.
- **Reject:** Note the reason in one line.
- **Defer:** Permitted ONLY for points proved outside current scope or non-blocking suggestions. No unresolved blocker affecting frozen or accepted work may be deferred.

**Reproduce reported defects before believing them.** Read the file, run the command, or write the test. A false alarm costs as much as a missed bug.

**Two-round non-convergence limit:** If two review rounds do not reach agreement, stop and escalate the decision to the human user.

Record all decisions in the plan's `## Review decisions` section.

---

## Step 5 — Freeze (Two-Commit Procedure)

A commit cannot contain its own future hash. Freezing requires an explicit two-commit sequence:

1. **Commit the agreed plan:**
   Set `Status: Agreed` in `docs/plans/<slug>.md`, leaving `Reference:` pending. Commit only the plan:
   ```bash
   cd "/Users/corvette/Documents/Projects Coding/Skill Lens"
   git add docs/plans/<slug>.md
   git commit -m "docs: freeze plan <slug>"
   git rev-parse HEAD
   ```
2. **Record the provenance hash:**
   Read the full commit hash from `git rev-parse HEAD`. Update `Reference:` with that exact hash, and commit the reference in a second plan-only provenance commit:
   ```bash
   git add docs/plans/<slug>.md
   git commit -m "docs: record plan <slug> frozen reference"
   ```

**Important rules for Freeze:**
- The provenance commit must **never** amend or alter the frozen behavior or plan content.
- **Implementer verification:** The implementer must check that the commit hash specified in `Reference:` contains every approved operative amendment before starting implementation.
- **Amendments require re-freeze:** Any amendment altering behavior, scope, permissions, or the execution contract requires explicit user authorization and a new two-commit freeze before affected implementation begins.
- **Post-freeze execution records:** Ordinary post-freeze append-only records (roster selections, provenance hash commits, acceptance records) cannot alter the operative contract. Changing or selecting model choices under existing per-session authorization is an authorized operational execution record, not rewriting frozen behavior.
- **Authoritative contract:** Never treat an arbitrary newest plan commit as authority. The frozen reference commit recorded in the provenance commit is the authoritative contract. Do not invent an unverified `git log` override rule.
- A commit records versioning; it is **not** human authorization. Verify `Authorization:` explicitly.

---

## Waiting Rules — The Part People Get Wrong

Cross-referenced with `implementation-loop.md`:

1. **Answer questions first:** A worker waiting on a question is paused; answer questions promptly. Note that MCP question tools are separate from permission approval controls.
2. **Match task and run identity:** Validate notifications and completions against the active `taskId`, `childRunId`, and `clientRequestId`. An event from an unrelated task is not your task finishing. Distinguish `workState=waiting_for_children` from terminal `result_available`, and check `hasPendingChildRuns` on later turns. A completed turn alone is not task acceptance.
3. **Inspect stalled work once:** If an expected notification is delayed, run bounded `task_status` checks to inspect the state. Do not poll or query in an infinite loop.
4. **Silence is never failure:** Do not treat silence as a task crash or permission to move on.
5. **Never launch duplicate workers:** A duplicate dispatch wastes resources and creates conflicting outputs.
6. **Wait timeout never cancels:** A timeout on a wait call simply returns control; it does not cancel the underlying task.
7. **Cancellation and terminal states:** `task_cancel` accepts its own stable `clientRequestId`, distinct from the dispatch `delegate_task` request ID. `task_cancel` may return `cancel_requested` (non-terminal) or an existing terminal status; `task_status`/pending run readback remains required. Task terminal states include `completed`, `failed`, `cancelled`, and `interrupted` (actual cancellation yielded `interrupted` with `hasPendingChildRuns=false`). Continue bounded `task_status` checks until one of the terminal states (`completed`, `failed`, `cancelled`, `interrupted`) is confirmed and `hasPendingChildRuns=false`.

---

## Done When

- [ ] Requirements settled; every open question resolved
- [ ] Every blocker resolved (no unresolved blocker affecting frozen scope; deferral only for points proved outside scope or non-blocking suggestions)
- [ ] Acceptance criteria defined with observable behaviors
- [ ] Review level justified; independent review completed
- [ ] `## Review decisions` filled in
- [ ] Plan frozen via the **two-commit provenance procedure**
- [ ] Actual frozen commit hash verified
- [ ] All child tasks confirmed in terminal state (`completed`, `failed`, `cancelled`, `interrupted`) with `hasPendingChildRuns=false`

Only then proceed to [`implementation-loop.md`](./implementation-loop.md).
