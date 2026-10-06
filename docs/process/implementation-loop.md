# The Implementation Loop

**What this is.** How a frozen plan becomes committed, verified code. One phase at a
time.

**Who does what.** **Antigravity writes the code and the tests.** The coordinator
(Sol/Hermes) never writes product code — it dispatches, reads, runs the gates, judges,
and accepts. That is the whole point: expensive tokens go on judgment, not typing.

Read first: [`council.md`](./council.md),
[`profiles/project-profile.md`](./profiles/project-profile.md) (the four gates and the
project rules), [`profiles/machine-profile.md`](./profiles/machine-profile.md).

---

## Step 1 — Baseline

Find the plan and its frozen commit hash:

```bash
cd "/Users/corvette/Documents/Projects Coding/Skill Lens"
ls docs/plans/
git rev-parse HEAD
git log --oneline -1
```

The plan's `Reference:` line must match. If the tree has moved past it, decide
deliberately whether you are building the plan as written or whether it needs
re-freezing — do not discover this mid-phase.

**Isolated worktree if the tree is dirty.** Never make the user clean up their checkout
to start work:

```bash
orca terminal create --worktree active --title "skill-lens-impl" --json
```

**Run the four gates first**, on the baseline. If they already fail, you are not looking
at your change's failure — you are looking at pre-existing breakage. Find out which it
is before dispatching anything.

---

## Step 2 — Dispatch one phase

**One phase at a time.** Not the whole plan in one worker.

Every brief must state, explicitly:

| Field | Meaning |
|---|---|
| **Target** | the exact file(s) and function(s) to change |
| **Change** | the intended behaviour, in plain English |
| **Constraints** | the project rules that bind this change |
| **Allowed edits** | the exact paths permitted. Nothing else. |
| **Acceptance checks** | the specific tests and gate results that prove it worked |
| **Commit owner** | who commits — almost always the coordinator, not the worker |
| **Plan reference** | the plan path and its frozen commit hash |

Plus the read-only guard if this is a critic rather than an implementer
(`council.md` §2).

Include enough that the implementer does not have to guess. Do not paste the whole
project history into the brief.

```bash
orca status --json
orca orchestration run-create --objective "Implement <phase> from docs/plans/<slug>.md @ <hash>" --json
orca orchestration task-create --spec "<the phase brief>" --json
orca orchestration worker-start --task <task_id> --worktree current --agent antigravity --json
orca orchestration check --wait --types "worker_done,escalation,question" --timeout-ms 900000 --json
```

Wait by the rules in `planning-loop.md` §"Waiting rules". Silence is not failure.

---

## Step 3 — Implement

Antigravity makes the change and its tests, runs the appropriate checks, and reports in
the implementer format (`council.md` §4).

**Antigravity does not commit.** The coordinator commits after acceptance, so the commit
message and the contents can be checked against the plan.

**A requirement conflict or plan defect comes back to the coordinator before scope
expands.** The implementer does not get to reinterpret the plan.

---

## Step 4 — Verify

**The coordinator reads the whole change, then runs all four gates itself.**

```bash
cd "/Users/corvette/Documents/Projects Coding/Skill Lens"
git status --porcelain          # every file touched, including NEW files
git diff
git diff --cached
pytest --cov=skill_lens
mypy
ruff check .
ruff format --check .
```

- **Account for changed *and* new files.** A new module that no gate covers is exactly
  how untracked files ship broken.
- **Read the new code as a whole.** Passing tests prove the assertions hold, not that
  the behaviour is right. Read the diff the way a reviewer would.
- **A snapshot diff is a finding, not a nuisance.** If `scan`/`why`/`diff` output moved,
  work out why before accepting it.
- **Do not trust the report. Read the files. Run the gates.**

---

## Step 5 — Review independently

The critic sees **the actual diff** and **the plan** — not a summary of either.

**Give the critic the evidence before you state your own conclusion.** If you tell the
critic "this looks correct" first, you have replaced an independent check with an
endorsement. Hand over the diff, the plan, and the gate output, then let it judge.

```bash
orca orchestration task-create --spec "Review this diff against docs/plans/<slug>.md. Read-only. Evidence: <diff>, <gate output>." --json
orca orchestration worker-start --task <task_id> --worktree current --agent <critic> --json
orca orchestration check --wait --types "worker_done,escalation,question" --timeout-ms 900000 --json
cd "/Users/corvette/Documents/Projects Coding/Skill Lens" && git status --porcelain
```

That last line is the read-only check. It must be unchanged.

**How many:** one independent critic normally; **two critics from different model
families** for high-risk work. Use a fresh reviewer context when independence matters.
Critic roles: **Antigravity** checks feasibility, **the others** give independent
critique.

---

## Step 6 — Rework

Confirmed defects go back to the implementer as a **short correction brief**: what is
wrong, where, the evidence, and the fix. Not a new phase.

Recheck:

- the affected behaviour specifically
- **all four gates**, again, on the new tree
- `git status --porcelain` for stray files

**Two rounds without convergence → stop and ask the user.** Do not start a third broad
wave. Non-convergence means the plan or the understanding is wrong, and that is a
decision for the human, not another agent.

---

## Step 7 — Accept

Only when all of this holds:

- [ ] the change meets the frozen plan
- [ ] **all four gates pass on the final tree**
- [ ] every blocker from Step 5 is resolved or explicitly deferred with a reason
- [ ] no unplanned file was touched
- [ ] documentation the plan required is updated
- [ ] the worker's report matches what you read

Then commit:

```bash
cd "/Users/corvette/Documents/Projects Coding/Skill Lens"
git add <exactly the paths the plan allows>
git commit -m "<type>(<scope>): <what the plan required>"
```

**Release the workers.** Explicitly reuse, retain, or release each one. Workers left
attached hold terminals and worktrees open.

---

## Plan-change table — the rule that stops silent drift

| What happened | Do this |
|---|---|
| Code failed an agreed plan | **Fix the code.** |
| A technical detail changed, but behaviour and boundaries did not | **Record it.** Update the plan only if it changed the implementation contract. |
| The plan was wrong, or the change affects behaviour, scope, compatibility, or the user's machine | **Stop. Present the concrete amendment. Get user approval. Re-freeze.** |

The third row is the one that matters. **Never silently change a frozen plan.** A plan
that has drifted from reality without anyone noticing is worse than no plan, because it
looks like a guarantee.

Re-freezing means: update `docs/plans/<slug>.md`, set `Status: Agreed`, commit again,
record the **new** commit hash, and tell anyone implementing the old hash that it is
obsolete.

---

## Done when

- [ ] The change meets the frozen plan
- [ ] All four gates pass on the final tree
- [ ] Every blocker resolved
- [ ] Committed, and the docs the plan required are updated
- [ ] Every worker released — no orphan terminals, no orphan worktrees
- [ ] Reported in plain English: what changed, why, whether it works, what the user
      needs to decide