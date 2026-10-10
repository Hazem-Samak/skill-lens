# The Implementation Loop

How a frozen plan becomes verified, committed work, one phase at a time. Antigravity writes product code and tests. Sol inspects, verifies, obtains independent review, accepts, and commits; small administrative corrections follow [council §6](./council.md#6-review-efficiency-without-weaker-acceptance).

Read [project-profile.md](./profiles/project-profile.md) for project constraints and gates, council §§1–4 before dispatch, and [machine-profile.md §5](./profiles/machine-profile.md#5-workspace-and-worktree-handling) before workspace preparation. Council §6 defines compact briefs, batched corrections, and execution receipts.

## Start-Implementation Prompt

```text
Act as coordinator Sol (Codex gpt-6.1-sol). Implement <phase> from
docs/plans/<dated-slug>.md @ <frozen_commit_hash>.
Verify authorization, frozen amendments, checkout binding, and baseline gates.
Follow docs/process/implementation-loop.md. Dispatch sole implementer Antigravity
(Gemini 3.8 Flash High), verify the final files, review by risk, then commit.
```

## Step 1 — Baseline

Inspect `git status --porcelain`, current commit, and the caller's actual checkout binding. Preserve pre-existing user work. A clean root checkout needs no new worktree; an already-bound checkout remains the working location. If isolation is needed, follow the machine profile's handoff/setup procedure before dispatch.

Verify `Authorization:` and the plan's `Reference:` against [planning-loop.md Step 5](./planning-loop.md#step-5--freeze-two-commit-procedure). Both coordinator and implementer must confirm that the referenced frozen commit contains every approved operative amendment. Later roster/acceptance records cannot override it.

Run the four gates on the baseline. An existing receipt within this session can satisfy this baseline check only if the inspected tree, environment, and commands are unchanged and the results are available. Otherwise rerun:

```bash
pytest --cov=skill_lens
mypy
ruff check .
ruff format --check .
```

Resolve baseline failures before implementation; investigate pre-existing issues without silently expanding scope. Respect the project's synthetic-HOME test rule and review snapshot/golden differences before regeneration.

## Step 2 — Dispatch One Phase

Send one coherent phase, with:

| Brief field | Required content |
|---|---|
| Target and change | Exact files/functions and intended behavior |
| Constraints and allowed edits | Applicable project rules and permitted paths |
| Acceptance | Meaningful tests and required gate evidence |
| Plan reference | Plan path and exact frozen commit hash |
| Commit owner | Sol; workers do not commit |

Use the compact briefing rules in council §6. Verify active coordinator Full access mode, then call `delegate_task` with `providerInstanceId=antigravity`, `model=gemini-3.8-flash-high`, `runtimeMode=full-access`, `interactionMode=default`, `role=implementation`, `mode=async`, and a stable request ID for that task.

Retain `taskId` and nullable `childRunId`; refresh an initially null run ID by status readback. Follow council §3 for reactive waiting, task identity, questions, terminal states, and pending-child checks. Do not duplicate active work.

## Step 3 — Implement

Antigravity edits code/tests, runs relevant checks, and returns the [council §4 implementer report](./council.md#4-report-formats), including effective-model evidence, changed files, checks, tests, deviations, and blockers. It does not delegate, review, or commit.

A requirement conflict or plan defect returns to Sol before scope expands.

## Step 4 — Verify Before Review

The coordinator inspects the entire diff and actual files against the frozen plan:

1. Account for tracked and untracked changes; enforce allowed paths and report unexpected edits.
2. Check applicable links, JSON examples, report fields, guard text, and source-backed API claims. Correct mechanical errors before independent review.
3. Read changed code with its consumers and constraints; passing assertions alone do not prove correct behavior. Inspect snapshot/golden changes before accepting them.
4. Run affected tests during correction work. Once the batch is ready, run **all four gates** directly and retain logs tied to that inspected tree. Worker self-reports do not replace coordinator verification.

Provide current gate evidence to critics. If the verified files or environment change, update the evidence; all four gates must pass on the final tree before acceptance.

## Step 5 — Review Independently

Use the risk level from the plan and [council §5](./council.md#5-review-risk-levels-and-escalation): zero critics for genuinely Low risk, one for Normal, two for High.

Follow council §§1–4 and §6: reuse user-selected models/settings, satisfy family requirements, preflight Full access, supply evidence-first briefs with the exact guard/report schema, capture status/fingerprints, dispatch the whole wave, and collect all reports. Each review round is a fresh `delegate_task` with a distinct stable request ID; never continue reviews through the backing child thread.

Point reviewers to the frozen plan, exact diff base/current revision, relevant files, and gate logs. Supply the complete diff through one source rather than duplicating it inline and on disk. Critics must be able to inspect all relevant dependencies.

Verify no reviewer changed files; unexpected edits follow council §2's preserve/inspect/stop rule.

## Step 6 — Rework

Collect and reproduce the coordinator's and all reviewers' findings. Send Antigravity one short correction brief covering confirmed product-code/test defects and required checks. Sol may handle only the administrative corrections allowed by council §6.

Run relevant checks while correcting, then all four gates on the ready final tree before acceptance. Resolve every in-scope blocker with evidence; defer only proved outside-scope points or non-blocking suggestions.

Dispatch fresh targeted follow-ups to affected critics under council §6, including the original brief and prior findings/responses/unresolved objections. Broaden review when shared contracts, dependencies, or acceptance changed. Required independent acceptance still applies; unchanged verdicts require a verified unchanged scope. Two rounds without agreement require user escalation, not a third broad wave.

## Step 7 — Accept and Commit

Accept only when:

- [ ] Work satisfies the authorized frozen contract and every operative amendment.
- [ ] All four gates pass on the final tree, with current coordinator evidence.
- [ ] Required independent reviews complete; every in-scope blocker resolved.
- [ ] Only allowed files changed; planned documentation is updated.
- [ ] Implementer report agrees with observed results; execution receipt is recorded.
- [ ] Every child task is terminal (`completed`, `failed`, `cancelled`, or `interrupted`) with `hasPendingChildRuns=false`.

An unchanged final tree with valid gate/review evidence needs no duplicate verification wave. If evidence is invalidated by a change, repeat the affected review and required final checks.

Stage only allowed paths and commit as coordinator:

```bash
git add <allowed paths>
git commit -m "<type>(<scope>): <summary of change>"
```

Complete council §3 cleanup: confirm terminal/no-pending task states, and remove only owned, unused worktrees after checking bindings and preserving user edits. Report what changed, why, verification, commit, and any remaining decision in plain English.

## Plan-Change Table

| Situation | Action |
|---|---|
| Implementation fails the agreed contract | Fix implementation. |
| Technical detail changes without changing behavior or boundaries | Record it; amend the plan only if the implementation contract changes. |
| Behavior, scope, compatibility, permissions, the user's machine, or execution contract changes | Stop affected work, present the concrete amendment, verify explicit user authorization, then re-freeze. |

Use [planning-loop.md Step 5](./planning-loop.md#step-5--freeze-two-commit-procedure) for the two-commit amendment procedure. Existing authorization applies when it already covers the concrete action; do not ask for the same permission again. Append-only execution records do not change the frozen contract.
