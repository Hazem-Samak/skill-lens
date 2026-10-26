# The Critic Council

> **Surface: T3 Code (active).** This T3 council and workflow remain unchanged. In OMP / Oh My Pi, use the [OMP entry and separate roles/review policy](./omp/README.md). OMP policy takes precedence only on OMP.

**What this is.** The council is the independent review system in T3 Code for Skill Lens. Other AI models check plans and code diffs before work is frozen or accepted. They read and report; they never edit the project.

- A **critic** (or reviewer) is an agent dispatched with read-only instructions to inspect a plan or diff.
- The **coordinator** plans, dispatches, inspects, runs verification gates, judges, and commits. It may make small administrative document corrections (see §6). It never writes product code or tests.
- The **implementer** writes code and tests, runs checks, and reports. It never reviews, never delegates, and never commits.

**No role owns a model.** Roles bind behaviour only. The provider, model, and effort for every role come from the user's selection for that mission (§1).

"Sol" is a legacy label that appears in dated evidence records. It names no model and creates no requirement; live documents say "the coordinator".

Read this together with `profiles/project-profile.md` (what "correct" means here) and `profiles/machine-profile.md` (live environment and provider facts).

---

## 1. The Roster and Roles

**The user selects every model.** No role has a fixed, default, preferred, standing, or inherited provider, model, or effort. At the start of each mission the user names the roster; each entry gives provider, model, and effort/settings.

| Role | Selected by | Named per | Behaviour bound to the role |
|---|---|---|---|
| **Coordinator** | User | Mission | Plans, dispatches, verifies, judges, commits. Never writes product code. |
| **Implementer** | User | Mission or phase | Writes code/tests, reports. Never reviews, delegates, or commits. |
| **Critic / reviewer** | User | Review round | Inspects read-only, reports. Never edits. |
| **Follow-up worker** | User | Dispatch | Carries a targeted correction or later round. |

### Selection rules

1. **No silent choice.** When a needed selection is missing, ask once with the live catalog (`orchestrator_capabilities`) and a risk-sized effort recommendation. Never default, infer, accept an application's own default as the user's choice, or substitute.
2. **Scoped to the mission.** A named selection applies to that mission or session only. Reuse across rounds inside the mission is allowed under the same authorization. It never becomes a future default or a permanent waiver.
3. **No silent substitute.** If a named model becomes unavailable or exhausts quota, stop and ask the user, or use a fallback the user already authorized for that case.
4. **Verified identity.** Before dispatch, confirm the running identity matches the user's naming through readback or session evidence. On disagreement, stop and report; never continue under a different model.
5. **Recorded roster.** Record the roster in the plan (`Roster:`) and in the execution receipt, keeping requested, configured, and confirmed identity separate (§4).
6. **Post-freeze record.** Logging a roster or updating a selection under existing mission authorization is an append-only execution record. It never rewrites frozen behavior.
7. **Historical rosters are evidence only.** Rosters in [the migration record](../plans/2026-10-10-t3-orchestrator-v2-migration.md) and other dated records show what a past session ran, including any accepted exception. They select nothing now and waive nothing later.

### Role and family independence

1. **Strict role independence:** the coordinator judges and commits; the implementer writes code; critics review. No participant reviews its own implementation.
2. **Context independence is not family diversity.** Distinguish the two:
   - **Context independence:** a critic in a fresh delegated task has role and context independence (isolated subagent context, dedicated prompt, separate reasoning chain). Avoid claims that same-family models cannot provide independent context.
   - **Family diversity:** different provider labels alone do not prove different model families (e.g. multiple providers wrapping open weights or upstream APIs). Unknown family identity stays unverified; never claim verified diversity when identity is unverified.
3. **Family overlap is disclosed, not preselected.** State each participant's model family from evidence and flag any critic that shares the coordinator's or the implementer's family. Whether a review wave must use distinct families is the user's decision for that mission, recorded with the acceptance of the named set. This process requires the disclosure and the recorded acceptance; it prescribes no pool.

---

## 2. Read-Only Protection and Permissions

Reviewers must inspect plans and diffs without modifying repository files.

### The verbatim guard text

Paste this block **verbatim** into the prompt of every critic dispatch:

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

### Operational permission mode (Hazem's standing authorization)

The user (Hazem) explicitly authorized **Full access (`runtimeMode=full-access`)** for both planning and implementation loops to eliminate routine approval prompts. This standing preference is reused until changed:

- **Reviewer tasks:** Dispatched with `runtimeMode=full-access`, `interactionMode=plan`, and `role=review`.
- **Implementer tasks:** Dispatched with `runtimeMode=full-access`, `interactionMode=default`, and `role=implementation`.

### Protection realities and safeguards

1. **Caller-mode preflight:** Before each dispatch wave, verify the coordinator's active Full access mode via `t3_thread_configuration`; repeat if the turn or configuration changes. T3 rejects broader children (`runtime_mode_escalation_denied`). Reuse standing authorization; never silently downgrade. If the caller is narrower, have the user activate Full access in the composer and verify readback on the subsequent turn. This activates an approved choice, rather than asking for the same authorization again. Report the needed human step if the surface cannot activate it.
2. **Instruction-based restraint under Full access:** Full access permits writes at the provider layer. Reviewer restraint is instruction-based (the verbatim guard). `interactionMode=plan` is interaction guidance, not hard write prevention. Worktree isolation is not a security boundary. Never claim an enforced read-only guarantee.
3. **Detection via fingerprints:** The coordinator records `git status --porcelain` and SHA-256 fingerprints before and after every critic dispatch.
4. **Safeguard against blind restore:** If a critic touches files, the coordinator does **not** blindly run `git restore`. The coordinator detects, inspects, attributes, and preserves user work. It reports the unexpected modification and stops.
5. **Automatic approval review:** Full access eliminates routine provider prompts, but does not disable automatic approval review. If an action is rejected by automatic review, narrow the action or report the specific limitation; do not attempt a bypass.
6. **Supervised mode contrast:** In Supervised mode (`runtimeMode=approval-required`), provider actions trigger prompts. MCP question tools cannot approve permissions; native app controls must be used if available. Critics must avoid broad scans and focus on named files.

---

## 3. T3 Task Lifecycle and Ledger

T3 Code provides product-native app orchestration. Child tasks must be driven accurately:

### Structured dispatch example

To dispatch a critic via `delegate_task`:

```json
{
  "task": "<prompt with verbatim guard and review brief>",
  "target": {
    "providerInstanceId": "<provider named by the user for this round>",
    "model": "<model named by the user>",
    "options": {
      "variant": "<effort/option named by the user>"
    }
  },
  "role": "review",
  "runtimeMode": "full-access",
  "interactionMode": "plan",
  "mode": "async",
  "clientRequestId": "<stable id, distinct per round>"
}
```

Field names show valid JSON shape only. Every angle-bracket value comes from the user's roster for this mission (§1); nothing here is a default, and no historical target implies the next one.

### Lifecycle and ledger rules

1. **Task dispatch:** Calling `delegate_task` returns `taskId` and nullable `childRunId`; these are results, not dispatch arguments. Children inherit the caller's active checkout; dispatch has no workspace override. Inspect the caller binding with `t3_worktree_status`, and child branch/worktree metadata with `t3_thread_read`. Use `t3_thread_configuration` for model/options/modes, not workspace binding. Follow [machine-profile.md §5](./profiles/machine-profile.md#5-workspace-and-worktree-handling) if workspace preparation is needed.
2. **Ledger tracking:** Retain both `taskId` and `childRunId` in the task ledger to match the original delegated run. If `childRunId` is initially null, retain the null receipt and refresh via `task_status` readback once assigned; do not treat an initial null `childRunId` as a missing ledger failure. Distinguish `workState=waiting_for_children` (while children are active) from terminal `result_available`, and check `hasPendingChildRuns` on later turns. A completed turn alone is not task acceptance. The returned `childThreadId` is backing storage for the subagent, **not** a target for continuing review rounds (`t3_thread_send` is not used).
3. **Fresh review rounds:** For every review round, call `delegate_task` again with a fresh task and distinct `clientRequestId`. Include the original brief, prior findings, responses, and unresolved objections. The call returns a new `taskId`.
4. **Waiting and barriers:** Dispatch all critics in a wave before waiting. Async tasks wake the parent on completion; end the turn to wait reactively. Address worker questions promptly; question tools are distinct from permission controls. Use bounded `task_status` checks if stalled. Match notifications against task/run/request IDs, never launch duplicate workers, and never treat silence as failure or approval. A wait timeout **never** cancels a task.
5. **Cancellation and terminal states:** `task_cancel` accepts its own stable `clientRequestId`, distinct from the dispatch `delegate_task` request ID. `task_cancel` may return `cancel_requested` (non-terminal) or an existing terminal status; `task_status`/pending run readback remains required. Task terminal states include `completed`, `failed`, `cancelled`, and `interrupted` (actual cancellation yielded `interrupted` with `hasPendingChildRuns=false`). Continue bounded `task_status` checks until one of the terminal states (`completed`, `failed`, `cancelled`, `interrupted`) is confirmed and `hasPendingChildRuns=false`.
6. **Cleanup:** On completion, inspect `hasPendingChildRuns=false`. Cancel and clean up remaining child tasks. Worktrees survive thread deletion: clean up only owned, unused worktrees after checking bindings and absence of uncommitted user edits.
7. **Top-level threads:** Use `t3_thread_launch` only when the user explicitly requests a separate top-level conversation, and always provide an explicit `workspaceStrategy` (omission selects project root). `create_threads` inherits caller's checkout with no workspace override. No unrequested top-level launch.

---

## 4. Report Formats

Critic and implementer formats both require `EFFECTIVE_MODEL` for execution provenance.

### Critic report format

Every critic must return exactly these fields:

```text
EFFECTIVE_MODEL: [ provider/model, settings, runtimeMode, interactionMode | evidence: requested vs configured vs confirmed/unverified ]
VERDICT:         pass | changes_required | unverified
BLOCKERS:        [ location, problem, expected behaviour, evidence ]
SUGGESTIONS:     [ ... ]        non-blocking
FILES_AT_RISK:   [ ... ]
CONCEDED:        [ ... ]        points withdrawn after argument
```

### Implementer report format

The implementer returns:

```text
EFFECTIVE_MODEL:       [ provider/model, settings, runtimeMode, interactionMode | evidence: requested vs configured vs confirmed/unverified ]
OUTCOME:               succeeded | failed
FILES_CHANGED:         [ ... ]
CHECKS:                pytest= mypy= ruff-check= ruff-format=
TESTS_ADDED:           [ ... ]
DEVIATIONS_FROM_PLAN:  [ ... ]   empty, or each explained
BLOCKED_ON:            [ ... ]
```

### Format rules and EFFECTIVE_MODEL specification

- **Required components:** `provider/model`, `settings` (options such as reasoning/thinking/variant), and `modes` (`runtimeMode` and `interactionMode`).
- **Evidence channels:** Must distinguish requested vs configured vs provider-confirmed/unverified:
  - Task dispatch and `task_status` receipts corroborate target provider and model.
  - `t3_thread_configuration` corroborates configured options and runtime/interaction modes.
  - Provider banner / session output corroborates actual model use when available (otherwise marked unverified).
  - Catalog `currentValue` reflects catalog defaults, NOT task execution evidence.
- **Blockers require evidence:** Location (`path:line`), problem, expected behaviour, and concrete evidence (command output or failing test). Without evidence, it is a suggestion.
- **Blocker discipline:** No unresolved blocker affecting frozen or accepted work may be deferred. Deferral is permitted only for points proved outside current scope or non-blocking suggestions.
- **`unverified`:** An honest verdict when conditions prevent verification.
- **No FEASIBILITY line:** the implementer does not review; feasibility lines are removed.

---

## 5. Review Risk Levels and Escalation

| Risk Level | Trigger | Planning Review | Implementation Review | Expected child tasks for one separately planned phase, before corrections |
|---|---|---|---|---|
| **Low** | Obvious low-impact typos, links, and formatting | Coordinator plans alone | Coordinator reading + 4 gates | 0 administrative; 1 if product code/tests require the implementer |
| **Normal** | Features, substantive refactors, non-load-bearing fixes | 1 independent critic | 1 independent critic | 3: plan critic + implementer + final critic |
| **High** | Path resolution, data formats, registry TOML, exit codes, permissions, load-bearing areas (`AGENTS.md` §4), internal refactors touching load-bearing behavior | **2 critics named by the user**, family overlap disclosed and accepted (§1) | **2 critics named by the user**, family overlap disclosed and accepted (§1) | 5: 2 plan critics + implementer + 2 final critics |

*Risk policy notes:*
- Classify by what changes, not file type: a document changing permissions or a load-bearing contract is High risk. Low risk is strictly limited to obvious low-impact work.
- Internal refactors touching load-bearing behavior remain High risk.
- Substantive refactors are at least Normal risk.
- Family disclosure, and the user's decision whether a wave needs distinct families, are defined in §1. Task counts are expectations, not caps that allow skipping required checks or unresolved blockers.

### Two-round non-convergence escalation

If two rounds of review between the coordinator and critics do not converge on agreement:
- **Stop immediately.** Do not start a third broad wave of reviews.
- **Escalate to the user:** Present the disagreement, evidence, and options in plain English. Non-convergence indicates a specification ambiguity or plan issue requiring human decision.

---

## 6. Review Efficiency Without Weaker Acceptance

### Briefs and effort

Give each critic one explicit question; for two critics, use complementary questions such as project rules/compatibility and behavior/test gaps. Supply evidence before coordinator conclusions. Each brief contains:

- The verbatim guard (§2), critic report schema (§4), risk level, and review question.
- Plan path and frozen reference (or draft revision), acceptance criteria, exact files/symbols, and diff base/current revision for implementation review (use a fingerprint for uncommitted changes).
- Where to read the complete relevant evidence: named paths and a diff command or external temporary artifact. Include only useful excerpts inline; do not paste a full diff and also require rereading the same diff. Scope the initial reads, while permitting additional named dependencies when needed to prove a concern.
- Current check results and log paths, known limitations, and, for follow-ups, the original brief plus a concise ledger of prior findings, responses, and unresolved objections (§3).

Reuse already-read unchanged references; revisit relevant sections when a finding needs proof. Recommend effort suited to the review question using live options; explain why a higher setting is needed rather than automatically recommending the maximum. The user still selects every reviewer model and setting, and an authorized selection stays fixed for that mission (§1).

### Checks and corrections

Before independent review, the coordinator checks applicable plan/report fields, allowed file scope, links, JSON examples, source-backed API claims, exact guard text, and required verification evidence. Use small disposable checks where useful; a new validation framework is unnecessary.

Collect the coordinator's and all critics' findings before sending one correction brief. Reproduce reported defects, resolve blocking findings, and keep optional polish separate. The coordinator may directly correct typos, links, formatting, examples of an already agreed API, and administrative execution records. Product code and tests remain with the implementer the user named for this mission. A change to behavior, scope, permissions, or the frozen contract follows the plan-change procedure; only an explicit user instruction can authorize an exception to the usual workflow.

Follow-up reviews are fresh tasks (§3) focused on the changed areas and unresolved findings. Send them to every critic whose review question is affected; if the fix changes a shared contract or both questions, both critics must review it. An unaffected verdict remains evidence only after the coordinator verifies its scope is unchanged. Broaden review when dependencies, acceptance criteria, or wider behavior changed. Every blocker needs a recorded disposition and the required independent acceptance; targeted review never waives that requirement or the two-round escalation limit.

### Execution receipt

Record the expected task count at planning and, at acceptance, actual launches (including failed/interrupted ones), reasons for extra rounds, elapsed time, and token usage if the provider exposes it. Put the receipt in the existing dated plan/execution record; for an administrative task without a plan, use the final report. Mark unavailable metrics as unavailable. Prompt characters and task counts are useful measurements but are not billed tokens; claim savings only after comparable runs provide evidence.
