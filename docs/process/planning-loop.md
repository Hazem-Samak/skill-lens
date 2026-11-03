# The Planning Loop

> **Sequence shared by all four surfaces; command examples use T3 Code.** Keep the steps, review risk, and two-commit freeze below. Replace only host-specific dispatch, catalog, permissions, waiting, and cleanup with [BB](./bb.md), [Rex](./rex.md), or [Herdr](./herdr.md) mechanics when running there.

How a request becomes a reviewed, frozen plan before implementation. The coordinator drives; review roles and risk levels are defined in [council.md](./council.md).

Read [project-profile.md](./profiles/project-profile.md) for correctness, gates, and sensitive areas. Before dispatch, read council §§1–4 for model choices, permissions, the exact critic guard, reports, and task lifecycle. On T3, consult [machine-profile.md](./profiles/machine-profile.md) for provider or workspace facts; elsewhere use the host adapter above. Do not call T3-only tools from another host.

## Start-Planning Prompt

Name the roster first. The user gives provider, model, and effort for every role at mission start; the prompt itself carries no model choice ([council §1](./council.md#1-the-roster-and-roles)).

```text
Mission roster (named by the user, this mission only):
  coordinator:   <provider>/<model>/<effort>
  plan critics:  <provider>/<model>/<effort> per risk level, or none for Low
  implementer:   <provider>/<model>/<effort>
  final critics: <provider>/<model>/<effort>

Act as coordinator. Plan <feature/bug>.
Read AGENTS.md §4, the relevant specification, source, tests, and findings.
Follow docs/process/planning-loop.md. Choose the risk level and review scope,
resolve findings, and freeze docs/plans/<dated-slug>.md before implementation.
If a needed roster entry is missing, ask once with the live catalog; choose no model yourself.
```

## Step 1 — Inspect

Read the request, `AGENTS.md`, relevant specification sections (`FULL_SCREEN_TUI.md` for TUI work), target source and its dependencies, relevant tests/snapshots, and the findings named in `AGENTS.md` §4.

Record verified current behavior and unknowns. Ask about requirement choices only when plausible interpretations lead to different behavior; use existing authorization where it already settles the choice.

## Step 2 — Draft

Write a short, sufficient plan to `docs/plans/<dated-slug>.md`, for example `2026-10-11-feature-name.md`:

```markdown
# Plan: <name>
Status: Draft | Agreed
Authorization: <existing user instruction, or "pending">
Roster: <user-named provider/model/effort per role; requested vs configured evidence>
Reference: <pending until Step 5>
Risk and review: <council §5 level, reason, reviewer questions>
Expected child tasks: <planning + implementation + final review; before corrections>

## Outcome
Observable result for the user.

## Current state
Verified facts, source references, limitations, and open questions.

## Scope and boundaries
Allowed files, constraints, and excluded work.

## Implementation steps
Coherent steps with files, interfaces, and dependencies needed to implement them.

## Acceptance
Required behavior, meaningful edge cases/tests, and the four project gates.

## Review decisions
Finding, evidence, accepted/rejected/deferred, and reason.
```

Choose risk and expected task count under [council §5](./council.md#5-review-risk-levels-and-escalation). File type alone does not establish low risk. Keep the plan precise enough to implement without inventing requirements; expand only where the contract needs detail.

## Step 3 — Review

For the chosen risk level:

1. Check applicable draft fields, references/links, and source-backed claims before dispatch.
2. Reuse the roster the user named for this mission and any fallback they already authorized. If an entry is missing, use the council's live-catalog ask-once procedure; choose no model yourself and waive no family disclosure-and-acceptance duty (council §1).
3. On T3, verify the coordinator's active Full access mode; elsewhere verify the host's native permissions. Prepare each critic's evidence-first brief under [council §6](./council.md#6-review-efficiency-without-weaker-acceptance), including the verbatim guard and report schema.
4. Capture status/fingerprints before dispatch. Launch the whole wave before waiting. On T3, use `delegate_task` with explicit user-selected target/options, `runtimeMode=full-access`, `interactionMode=plan`, `role=review`, `mode=async`, `isolation="shared"` for an uncommitted draft, and a stable request ID distinct per round. On other hosts use the adapter's native launch.
5. Track task/run identity and use council §3 on T3, or the active host adapter elsewhere, for waiting, readback, cancellation, and cleanup. Collect every report and verify that critics left the files unchanged.

Low risk needs no critic dispatch. Every other level needs its required independent review before freeze.

## Step 4 — Resolve

Combine the coordinator's findings and all critic reports into one decision list. Reproduce reported defects before accepting them. Record each finding as:

- **Accepted:** Correct the draft and explain why.
- **Rejected:** Give the evidence and a short reason.
- **Deferred:** Only a proved outside-scope issue or non-blocking suggestion; an in-scope blocker stays unresolved until fixed.

Batch corrections. Where independent follow-up is needed, use fresh targeted tasks with the original brief, prior findings, responses, and unresolved objections. Follow council §6 to determine affected critics and when broader review is required. Two rounds without agreement trigger council §5 escalation; do not start a third broad wave.

Resolve every requirement question and blocker affecting the frozen scope before marking the plan agreed.

## Step 5 — Freeze (Two-Commit Procedure)

A commit cannot contain its own future hash:

1. Verify `Authorization:` and all required review decisions. Set `Status: Agreed`, leave `Reference:` pending, and commit only the agreed plan.
   ```bash
   git add docs/plans/<dated-slug>.md
   git commit -m "docs: freeze plan <dated-slug>"
   git rev-parse HEAD
   ```
2. Put that exact full hash in `Reference:` and make a second plan-only provenance commit:
   ```bash
   git add docs/plans/<dated-slug>.md
   git commit -m "docs: record plan <dated-slug> frozen reference"
   ```

The second commit changes only the reference; it must not change the frozen contract. A commit records a version, not human authorization.

Before affected implementation, both coordinator and implementer verify that the referenced frozen commit includes every approved operative amendment. Changing behavior, scope, permissions, or the execution contract requires explicit user authorization and a new two-commit freeze. Reuse authorization that already covers the concrete amendment.

Append-only execution records may log authorized session roster choices, review/acceptance evidence, and the council §6 receipt. They cannot alter the operative contract. The recorded frozen reference is authority; an arbitrary newer plan commit is not an override.

## Done When

- [ ] Requirements and all in-scope blockers resolved; acceptance is observable.
- [ ] Risk justified, required independent reviews complete, and decisions recorded.
- [ ] Authorization verified; two-commit freeze complete; exact reference checked.
- [ ] All dispatched work settled and owned resources handled. On T3: child tasks terminal with `hasPendingChildRuns=false`, cleanup under council §3. Other hosts: verify native completion and cleanup under their adapter.

Only then proceed to [implementation-loop.md](./implementation-loop.md).
