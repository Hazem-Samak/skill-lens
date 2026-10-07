# The Planning Loop

**What this is.** How a request becomes a frozen, committed plan. Nothing is coded until
the plan is committed.

**Who does what.** The coordinator (**Sol / Hermes**) runs this loop and never writes
product code. Critics review the plan, read-only. Antigravity implements it later, in
`implementation-loop.md`.

Read first: [`council.md`](./council.md) (who the critics are), and
`profiles/project-profile.md` (what "correct" means here) plus
`profiles/machine-profile.md` (what this machine can run).

---

## Step 1 — Inspect

Read before you write anything.

1. `AGENTS.md` — especially **§4**, which names the findings files that are
   load-bearing. Skipping this is the easiest way to break something already fixed.
2. The request, and the relevant part of `SKILL_LENS_SPECIFICATION.md`.
3. The source: the engine, the model, the CLI surface, the registry TOML.
4. The tests, including the gate tests and the snapshots.
5. Any findings file from `AGENTS.md` §4 that covers the area.

Then **write down what you do not know.** Put it in the plan under `## Open questions`
or `## Current state`. An unknown you noticed is manageable; one you forgot is a defect
with your name on it.

**Ask the user only about requirement choices** — where two readings are both
reasonable and they lead to different behaviour. Everything else you resolve yourself.
Ask in plain language, one question at a time, with a recommendation.

---

## Step 2 — Draft

Write the plan to `docs/plans/<slug>.md`. Use the template.

```markdown
# Plan: <name>
Status: Draft | Agreed
Authorization: <existing user instruction, or "pending">
Reference: <filled in at Step 5 with the commit hash>

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

`<slug>` is short, kebab-case, and dated when it matters:
`2026-10-06-exit-code-contract.md`.

Keep it proportional. A one-line fix does not need four pages. A change to the resolver
does.

**Decide the review level now**, using `council.md` §6. High risk = path resolution,
public data formats, registry TOML, permissions, exit codes, compatibility, or anything
`AGENTS.md` §4 calls load-bearing. For Skill Lens this is often.

---

## Step 3 — Review

One independent critic, or **two critics from different model families** for high-risk
work. Do not stand up a five-agent council; expand when evidence warrants it.

**Everyone read-only.** Paste the guard text from `council.md` §2 into every critic
task.

**Give each critic a different question.** One checks project rules and compatibility.
Another checks behaviour, failure cases and test gaps. Two critics given one question
return two copies of the same opinion.

**Give the critic the evidence before you state your own conclusion**, so it can judge
independently.

**Dispatch every critic before you wait on any of them.** Sequential dispatch wastes
the wall-clock time the review was supposed to save.

```bash
orca status --json

orca orchestration run-create --objective "Review the plan at docs/plans/<slug>.md" --json
orca orchestration task-create --spec "<critic task, including the read-only guard>" --json
orca orchestration task-list --ready --brief --json

orca orchestration worker-start --task <task_id> --worktree current --agent opencode --json

orca orchestration check --wait --types "worker_done,escalation,question" --timeout-ms 900000 --json
```

**The second critic (MCode) cannot use `worker-start --terminal`** — it is rejected as
`agent_unconfigured`. Use Route C from `machine-profile.md` §5: `task-create`, then
`orchestration dispatch --return-preamble` without `--inject`, then `terminal send` the
returned preamble.

Antigravity, when reviewing for feasibility, needs `--mode plan` and therefore the
terminal route too — see `council.md` §5.

The coordinator is **never** dispatched as a worker, and must run inside an Orca
terminal — see `machine-profile.md` §7a.

---

## Step 4 — Resolve

For every finding, in the critic's report format:

- **Accept** — the plan changes. Say why in one line.
- **Reject** — say why in one line. Disagreement is a normal outcome, not a failure.
- **Defer** — name what it depends on and when it comes back.

**Reproduce any reported defect before you believe it.** A false alarm costs exactly as
much as a missed bug. Read the file, run the command, write the failing test. If it
reproduces, it is real. If it does not, say so and record it.

**Every blocker must be resolved before the plan can be frozen.** "Deferred" is allowed
only if it genuinely does not affect the change.

Record all of it in the plan's `## Review decisions` section.

---

## Step 5 — Freeze

Update the plan's `Status:`, fill in `Reference:`, then commit **only the plan**:

```bash
cd "/Users/corvette/Documents/Projects Coding/Skill Lens"
git add docs/plans/<slug>.md
git commit -m "docs: freeze plan <slug>"
git rev-parse HEAD
```

**Record that commit hash in the plan and in your report.** It is how the implementation
loop knows exactly which plan it is building.

A commit records the plan's version. It is **not** human approval — check
`Authorization:` yourself, and ask when the project profile requires it.

---

## Waiting rules — the part people get wrong

```bash
orca orchestration check --wait --types "worker_done,escalation,question" --timeout-ms 900000 --json
```

1. **Answer questions and escalations before acknowledging anything.** A worker blocked
   on a question is not making progress.
2. **Validate every completion against the active task.** A `worker_done` for the wrong
   task id is not your task finishing.
3. **Three empty waits in a row → run `worker-list` and inspect.** Do not keep waiting
   blind, and do not assume the worst.
4. **Silence is never proof of failure, and never permission to move on.**
5. **Never launch a duplicate worker.** That doubles the cost and can produce two
   conflicting answers.
6. **Only positive proof a worker exited allows you to stop it.** A budget limit that
   blocks a new dispatch says nothing about the running one.

---

## Done when

- [ ] Requirements settled; every question answered
- [ ] Every blocker resolved or genuinely deferred
- [ ] Acceptance defined — the observable behaviour, not "looks right"
- [ ] Review level chosen and justified
- [ ] `## Review decisions` filled in
- [ ] Plan committed, and the **commit hash recorded**
- [ ] No worker is still holding this plan

Only then open `implementation-loop.md`.