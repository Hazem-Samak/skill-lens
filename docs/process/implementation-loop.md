# The Implementation Loop

> **Sequence shared by all four surfaces; command examples use T3 Code.** Keep baseline, verification, rework, and acceptance below. Replace host-specific dispatch, permissions, waiting, and cleanup with [BB](./bb.md), [Rex](./rex.md), or [Herdr](./herdr.md) mechanics when running there.

How a frozen plan becomes verified, committed work, one phase at a time. The implementer named by the user writes product code and tests. The coordinator inspects, verifies, obtains independent review, accepts, and commits; small administrative corrections follow [council §6](./council.md#6-review-efficiency-without-weaker-acceptance).

Read [project-profile.md](./profiles/project-profile.md) for project constraints and gates, and council §§1–4 before dispatch. On T3, read [machine-profile.md §5](./profiles/machine-profile.md#5-workspace-and-worktree-handling) before workspace preparation; elsewhere use the host adapter. Council §6 defines briefs, batched corrections, and execution receipts.

## Start-Implementation Prompt

```text
Mission roster (named by the user; read it from the frozen plan's Roster field):
  coordinator:   <provider>/<model>/<effort>
  implementer:   <provider>/<model>/<effort>
  final critics: <provider>/<model>/<effort> per risk level

Act as coordinator. Implement <phase> from
docs/plans/<dated-slug>.md @ <frozen_commit_hash>.
Verify authorization, frozen amendments, checkout binding, and baseline gates.
Follow docs/process/implementation-loop.md. Dispatch the named implementer,
verify the final files, review by risk, then commit.
If a roster entry is missing or a named model is unavailable, ask once; substitute nothing.
```

## Step 1 — Baseline

Inspect `git status --porcelain`, current commit, and the host's actual checkout binding. Preserve pre-existing user work. A clean root checkout needs no new worktree; an already-bound checkout remains the working location. On T3, child isolation uses `delegate_task.isolation:"worktree"`; moving the coordinator itself uses the machine profile's handoff procedure. Fresh worktrees exclude uncommitted edits, so share the inspected checkout when a critic needs to review those edits.

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
| Commit owner | Coordinator; workers do not commit |

Use council §6's briefing rules. On T3, verify active coordinator Full access mode, then call `delegate_task` with the user-named `providerInstanceId`, `model`, and `options` ([council §1](./council.md#1-the-roster-and-roles)), plus `runtimeMode=full-access`, `interactionMode=default`, `role=implementation`, `mode=async`, the deliberately chosen `isolation`, and a stable request ID. Verify configured identity against the roster. Other hosts use their native adapter and record equivalent evidence.

On T3, retain `taskId` and nullable `childRunId`; refresh an initially null run ID after a wake/readback. Follow council §3 for task identity, questions, terminal states, and pending-child checks. Other hosts retain their returned native IDs and completion evidence. Do not duplicate active work.

## Step 3 — Implement

The implementer edits code/tests, runs relevant checks, and returns the [council §4 implementer report](./council.md#4-report-formats), including effective-model evidence, changed files, checks, tests, deviations, and blockers. It does not delegate, review, or commit.

A requirement conflict or plan defect returns to the coordinator before scope expands.

## Step 4 — Verify Before Review

The coordinator inspects the entire diff and actual files against the frozen plan:

1. Account for tracked and untracked changes; enforce allowed paths and report unexpected edits.
2. Check applicable links, JSON examples, report fields, guard text, and source-backed API claims. Correct mechanical errors before independent review.
3. Read changed code with its consumers and constraints; passing assertions alone do not prove correct behavior. Inspect snapshot/golden changes before accepting them.
4. Run affected tests during correction work. Once the batch is ready, run **all four gates** directly and retain logs tied to that inspected tree. Worker self-reports do not replace coordinator verification.

Provide current gate evidence to critics. If the verified files or environment change, update the evidence; all four gates must pass on the final tree before acceptance.

## Step 5 — Review Independently

Use the risk level from the plan and [council §5](./council.md#5-review-risk-levels-and-escalation): zero critics for genuinely Low risk, one for Normal, two for High.

Follow council §§1–4 and §6: reuse the user-named roster, disclose each reviewer's model family and record the user's acceptance, verify host permissions, supply the exact guard/report schema, capture status/fingerprints before dispatch, launch the whole wave, and collect all reports. Every review round needs a fresh context and the original brief plus prior findings. On T3 use a fresh `delegate_task` and distinct stable request ID, not the backing child thread; on other hosts follow their adapter's fresh-review mechanism.

Point reviewers to the frozen plan, exact diff base/current revision, relevant files, and gate logs. Supply the complete diff through one source rather than duplicating it inline and on disk. Critics must be able to inspect all relevant dependencies.

Verify no reviewer changed files; unexpected edits follow council §2's preserve/inspect/stop rule.

## Step 6 — Rework

Collect and reproduce the coordinator's and all reviewers' findings. Send the assigned implementer one short correction brief covering confirmed product-code/test defects and required checks. The coordinator may handle only the administrative corrections allowed by council §6.

Run relevant checks while correcting, then all four gates on the ready final tree before acceptance. Resolve every in-scope blocker with evidence; defer only proved outside-scope points or non-blocking suggestions.

Dispatch fresh targeted follow-ups to affected critics under council §6, including the original brief and prior findings/responses/unresolved objections. Broaden review when shared contracts, dependencies, or acceptance changed. Required independent acceptance still applies; unchanged verdicts require a verified unchanged scope. Two rounds without agreement require user escalation, not a third broad wave.

## Step 7 — Accept and Commit

Accept only when:

- [ ] Work satisfies the authorized frozen contract and every operative amendment.
- [ ] All four gates pass on the final tree, with current coordinator evidence.
- [ ] Required independent reviews complete; every in-scope blocker resolved.
- [ ] Only allowed files changed; planned documentation is updated.
- [ ] Implementer report agrees with observed results; execution receipt is recorded.
- [ ] All owned work has settled under the native host's lifecycle rules. On T3 every child task is terminal (`completed`, `failed`, `cancelled`, or `interrupted`) with `hasPendingChildRuns=false`.

An unchanged final tree with valid gate/review evidence needs no duplicate verification wave. If evidence is invalidated by a change, repeat the affected review and required final checks.

Stage only allowed paths and commit as coordinator:

```bash
git add <allowed paths>
git commit -m "<type>(<scope>): <summary of change>"
```

Complete the active host's cleanup procedure (council §3 on T3). Remove only owned, unused worktrees after checking bindings and preserving user edits. Report what changed, why, verification, commit, and any remaining decision in plain English.

## Plan-Change Table

| Situation | Action |
|---|---|
| Implementation fails the agreed contract | Fix implementation. |
| Technical detail changes without changing behavior or boundaries | Record it; amend the plan only if the implementation contract changes. |
| Behavior, scope, compatibility, permissions, the user's machine, or execution contract changes | Stop affected work, present the concrete amendment, verify explicit user authorization, then re-freeze. |

Use [planning-loop.md Step 5](./planning-loop.md#step-5--freeze-two-commit-procedure) for the two-commit amendment procedure. Existing authorization applies when it already covers the concrete action; do not ask for the same permission again. Append-only execution records do not change the frozen contract.
