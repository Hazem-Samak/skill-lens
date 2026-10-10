# The Implementation Loop

**What this is.** How a frozen plan becomes committed, verified code. One phase at a time.

**Who does what.** **Antigravity writes the code and the tests.** The coordinator (**Sol / Codex `gpt-6.1-sol`**) never writes product code — it dispatches, inspects diffs, runs the four gates, dispatches independent reviews, judges, accepts, and commits.

Read first: [`council.md`](./council.md) (roles, guards, and permissions), [`profiles/project-profile.md`](./profiles/project-profile.md) (the four gates and project rules), and [`profiles/machine-profile.md`](./profiles/machine-profile.md) (live machine facts).

---

## Usable Start-Implementation Prompt Example

To initiate an implementation turn as coordinator in T3 Code:

```text
Act as coordinator Sol (Codex gpt-6.1-sol). We are implementing <phase/feature> from docs/plans/<slug>.md @ <commit_hash>.
Verify the baseline against git rev-parse HEAD and run the four gates on the clean root checkout.
Follow docs/process/implementation-loop.md, council.md, and profiles.
Preflight runtime mode and dispatch sole implementer Antigravity (Gemini 3.8 Flash High) with an explicit phase brief.
```

---

## Step 1 — Baseline

Verify the plan and its frozen commit hash:

```bash
cd "/Users/corvette/Documents/Projects Coding/Skill Lens"
git rev-parse HEAD
git log --oneline -1
```

**Verify the frozen plan reference:**
- Confirm that `Reference:` in `docs/plans/<slug>.md` points to the frozen behavior commit.
- **Implementer verification:** The implementer must check that the commit hash specified in `Reference:` contains every approved operative amendment before implementation starts.
- **Amendments require re-freeze:** Any change to behavior, scope, permissions, or the execution contract is an operative amendment requiring explicit user authorization and a new two-commit freeze before affected implementation begins.
- **Post-freeze records cannot change contract:** Ordinary post-freeze append-only records (execution roster selections, provenance hash commits, acceptance records) cannot alter the operative contract.
- **Authoritative contract:** Never treat an arbitrary newest plan commit as authoritative over `Reference:`. The frozen reference commit recorded in the provenance commit is the authority. Do not invent an unverified `git log` override rule.

**Workspace check:**
- If the checkout is clean, work directly in the project root (`worktreePath: null`). Respect existing caller binding; do not assume every clean checkout is project root.
- If an isolated worktree is needed:
  1. Inspect `t3_worktree_status` and inspect the project setup script BEFORE calling handoff.
  2. Note that an already-attached thread cannot handoff (`t3_worktree_handoff` moves the calling thread, not another thread, and cannot move a thread already attached to a worktree).
  3. Call `t3_worktree_handoff` with explicit `branch`, `baseRef`, `startFromOrigin: false` (to base on local commits) or `true` (from origin), explicitly pass `runSetupScript: true` (the live `t3_worktree_handoff` tool description notes it runs the setup script by default, though no default is declared in the schema field; pass the argument explicitly), and provide `continuationPrompt` as the last tool action of the turn.
  4. After resumption, verify both setup and continuation outcomes; if either fails, stop and report the error rather than skipping.

**Run the four gates first on baseline:**

```bash
pytest --cov=skill_lens
mypy
ruff check .
ruff format --check .
```

If the baseline fails, resolve pre-existing issues before dispatching implementation.

---

## Step 2 — Dispatch One Phase

**One phase at a time.** Never dispatch an entire multi-phase plan in one task.

Every brief must state explicitly:

| Field | Meaning |
|---|---|
| **Target** | The exact file(s) and function(s) to modify |
| **Change** | The intended behaviour in plain English |
| **Constraints** | Project rules binding this change (e.g. read-only product, monkeypatched HOME) |
| **Allowed edits** | The exact file paths permitted |
| **Acceptance checks** | Specific tests and gate outputs proving completion |
| **Commit owner** | Coordinator Sol (workers do not commit) |
| **Plan reference** | Plan path and its frozen commit hash |

### Dispatch procedure

1. Preflight coordinator mode with `t3_thread_configuration` (confirm Full access).
2. Dispatch Antigravity via `delegate_task`:\
   - `runtimeMode: "full-access"`\
   - `interactionMode: "default"`\
   - `role: "implementation"`\
   - `mode: "async"`\
   - Target: `providerInstanceId: "antigravity"`, `model: "gemini-3.8-flash-high"`\
   - Stable `clientRequestId` per round.
3. Calling `delegate_task` returns `taskId` and `childRunId` (which is `string | null` and may be null until assigned by the runner). Retain both in the task ledger to match the original delegated run; if `childRunId` is initially null, refresh via `task_status` readback once assigned rather than treating it as a missing ledger failure. Distinguish `workState=waiting_for_children` from terminal `result_available`, and check `hasPendingChildRuns` on later turns. A completed turn alone is not task acceptance.
4. End turn to await completion via reactive wakeup, or inspect status using bounded `task_status` checks.

---

## Step 3 — Implement

Antigravity makes the edits and writes tests, runs local checks, and reports using the implementer format (`council.md` §4):

```text
EFFECTIVE_MODEL:       [ provider/model, settings, runtimeMode, interactionMode | evidence: requested vs configured vs confirmed/unverified ]
OUTCOME:               succeeded | failed
FILES_CHANGED:         [ ... ]
CHECKS:                pytest= mypy= ruff-check= ruff-format=
TESTS_ADDED:           [ ... ]
DEVIATIONS_FROM_PLAN:  [ ... ]   empty, or each explained
BLOCKED_ON:            [ ... ]
```

*Format specification:* Follow `council.md` §4 for `EFFECTIVE_MODEL` components and evidence channels (task/status receipts for provider/model, `t3_thread_configuration` for configured options/modes, provider banner/session when available; catalog `currentValue` is not task evidence) to ensure consistency without schema drifting.

**Antigravity does not commit.**
**A requirement conflict or plan defect returns to the coordinator before scope expands.**

---

## Step 4 — Verify

**The coordinator inspects the entire diff and runs all four gates directly:**

```bash
cd "/Users/corvette/Documents/Projects Coding/Skill Lens"
git status --porcelain          # check every touched file, including untracked files
git diff
pytest --cov=skill_lens
mypy
ruff check .
ruff format --check .
```

- **Account for all files:** Verify that only allowed paths were modified.
- **Read code as a whole:** Tests passing proves assertions hold, not that architecture is sound.
- **Inspect snapshot/golden diffs:** If rendering shifted, verify the change before accepting.
- **Do not rely on self-reports:** Read the actual files and run the gates.

---

## Step 5 — Review Independently

Independent critics check the diff and the plan:

1. **Evidence-first brief:** Provide the actual `git diff`, gate output, and the frozen plan path. Do not state coordinator conclusions first.
2. **Reviewer settings:**
   - Reviewer pool: `pi`, `grok`, or `opencode` (selected by USER per session from live catalog; coordinator presents ask-once menu if missing).
   - Target: explicit user-selected provider, model, and options (see structured dispatch example in `council.md` §3).
   - `runtimeMode: "full-access"`, `interactionMode: "plan"`, `role: "review"`, `mode: "async"`.
   - Paste verbatim read-only guard (`council.md` §2).
   - Fresh review round: Call `delegate_task` with a distinct `clientRequestId`. The call returns a fresh `taskId`. Do not imply passing `taskId` into dispatch.
   - Distinguish role/context independence from verified family diversity. High-risk reviews strictly require verified distinct model families when established. If a selected model family cannot be verified, disclose which identity is unverified and obtain explicit user acceptance of the named pair for that session before proceeding; never claim verified family diversity.
3. **Pre/post verification:** Take SHA-256 fingerprints and check `git status --porcelain` before and after dispatch. If a critic touches files, do **not** run blind `git restore`: detect, inspect, attribute, and preserve user work.

---

## Step 6 — Rework

Confirmed defects return to the implementer as a **short correction brief**: what is wrong, the evidence, and the needed fix.

After rework, re-run:
- Affected tests specifically
- **All four gates**
- `git status --porcelain` for stray files

**Two rounds without convergence → stop and ask the user.** Escalate to the human rather than launching a third broad wave.

---

## Step 7 — Accept

Accept the work only when all criteria are met:

- [ ] Code strictly satisfies the frozen plan
- [ ] **All four gates pass on the final tree**
- [ ] Every review blocker is resolved (no unresolved blocker affecting accepted work; deferral permitted ONLY for points proved outside scope or non-blocking suggestions)
- [ ] No unplanned file was touched
- [ ] Documentation required by the plan is updated
- [ ] Implementer report matches observed verification results
- [ ] A completed turn alone is not task acceptance

Then commit:

```bash
cd "/Users/corvette/Documents/Projects Coding/Skill Lens"
git add <allowed paths>
git commit -m "<type>(<scope>): <summary of change>"
```

**Task cleanup:**
- Verify `hasPendingChildRuns=false`.
- Confirm all child tasks reached terminal states (`completed`, `failed`, `cancelled`, `interrupted`).
- Clean up any remaining child tasks.
- Clean up owned, unused worktrees after checking bindings and absence of uncommitted user edits.

---

## Plan-Change Table

| What happened | Do this |
|---|---|
| Code failed an agreed plan | **Fix the code.** |
| A technical detail changed, but behaviour and boundaries did not | **Record it.** Update the plan only if the implementation contract changed. |
| The plan was wrong, or the change affects behaviour, scope, compatibility, or the user's machine | **Stop. Present the concrete amendment. Get user approval. Re-freeze.** |

**Never silently change a frozen plan.** Re-freezing requires the two-commit provenance procedure (`planning-loop.md` §5): obtain explicit user authorization, commit agreed plan changes, read the new commit hash, and record the new hash in a provenance commit before affected implementation begins.

**Post-freeze execution record:** Log the implementation-session roster as an append-only execution record after freeze. Changing or selecting model choices under existing per-session authorization is an authorized operational execution record, not silently rewriting frozen behavior. Never treat an arbitrary newest plan commit as authority over the frozen reference.

---

## Waiting Rules — The Part People Get Wrong

Cross-referenced with `planning-loop.md`:

1. **Answer questions first:** Address any worker questions promptly. Question tools are distinct from permission approval controls.
2. **Match task and run identity:** Validate notifications against active `taskId`, `childRunId`, and `clientRequestId`. Distinguish `workState=waiting_for_children` from terminal `result_available`, and check `hasPendingChildRuns` on later turns. A completed turn alone is not task acceptance.
3. **Inspect stalled work once:** Check `task_status` with bounded checks if a task stalls; do not poll in an infinite loop.
4. **Silence is never failure:** Silence does not mean a task failed or that you may proceed.
5. **Never launch duplicate workers:** Duplicates waste resources and cause conflicting state.
6. **Wait timeout never cancels:** A timeout returns control to the caller; the task continues.
7. **Cancellation and terminal states:** `task_cancel` accepts its own stable `clientRequestId`, distinct from the dispatch `delegate_task` request ID. `task_cancel` may return `cancel_requested` (non-terminal) or an existing terminal status; `task_status`/pending run readback remains required. Task terminal states include `completed`, `failed`, `cancelled`, and `interrupted` (actual cancellation yielded `interrupted` with `hasPendingChildRuns=false`). Continue bounded `task_status` checks until one of the terminal states (`completed`, `failed`, `cancelled`, `interrupted`) is confirmed and `hasPendingChildRuns=false`.

---

## Done When

- [ ] Change meets the frozen plan
- [ ] All four gates pass cleanly on the final tree
- [ ] Every blocker resolved (no unresolved blocker affecting accepted work; deferral only for points proved outside scope or non-blocking suggestions)
- [ ] Changes committed by the coordinator
- [ ] All child tasks in terminal states (`completed`, `failed`, `cancelled`, `interrupted`) with `hasPendingChildRuns=false`
- [ ] Report delivered in plain English: what changed, why, test results, and next decisions
