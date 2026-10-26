# OMP implementation loop

The coordinator delivers one authorized frozen phase. Product code/tests belong to the implementer the user named for this mission; the coordinator inspects, verifies, reviews, accepts and commits. Use the [OMP roles, review policy and lifecycle](./README.md), not T3 APIs.

## Start prompt

```text
Mission roster (named by the user; read it from the frozen plan's Roster field;
nothing here has a standing model):
  coordinator:   <provider>/<model>/<effort>
  implementer:   <provider>/<model>/<effort>
  final critics: <provider>/<model>/<effort> per risk level

Act as OMP coordinator. Implement <phase> from
docs/plans/<dated-slug>.md @ <full frozen hash>.
Follow docs/process/omp/implementation-loop.md. Verify active identity,
authorization, operative amendments, checkout ownership and baseline evidence.
Delegate product code/tests to the implementer named in the roster.
Children edit only and SKIP gates/formatters. Coordinate verification,
fresh independent review, acceptance and authorized commit/push yourself.
If a roster entry is missing or a named model is unavailable, ask once;
substitute nothing.
```

## 1. Establish contract and baseline

Inspect actual checkout/branch, current commit, and `git status --porcelain`; account for tracked and untracked user changes without overwriting or staging them. Use separate checkouts/branches if T3 and OMP will write concurrently; assign integration ownership. Never reset user work to get a clean baseline.

Verify authorization and the exact full `Reference:` using the [two-commit freeze](./planning-loop.md#5-freeze-in-two-commits). Both coordinator and implementer must inspect that frozen version and confirm all approved operative amendments are included. Later roster notes are not contract overrides.

The coordinator establishes these four baseline gates, from the project root:

```bash
uv run pytest --cov=skill_lens
uv run mypy
uv run ruff check .
uv run ruff format --check .
```

Reuse available session evidence only when the inspected tree, environment and commands are unchanged. Do not rerun unchanged evidence just to confirm it. Record baseline failures and resolve the authorization/scope decision before implementation; do not silently fix unrelated pre-existing failures. Product/application state is read-only: use synthetic HOME and isolated fixtures for tests, never real user configuration or data. Inspect changed snapshot/golden files and their cause **before** regeneration; regeneration is not a fix by itself.

## 2. Dispatch owned work

Prefer one coherent implementer for a phase. Parallelize only genuinely independent slices, each with explicit disjoint file ownership and shared interface contracts; appoint one integration owner. Never have apps/agents race on the same files or run parallel verification storms.

Each brief contains exact target/change, allowed paths, exclusions, source references, frozen plan/full hash, meaningful acceptance, ownership, and selected runtime/model/settings. Verify effective configured choices against authorization before dispatch; inherited native defaults do not establish the requested model (see [dispatch rules](./README.md#roles-and-session-choices)). Use a supported explicit-model external route when appropriate, or ask; never silently substitute.

Select the dispatch route before starting implementers or final reviewers: when Herdr is requested, keep the OMP coordinator native in Tern and follow the [external Herdr adapter](./herdr.md) for the verified named-session/socket gate, explicit worker pane IDs, bounded waits and inspect-before-resend. Missing or ambiguous connection stops that route; being outside Herdr does not. Never silently replace requested Herdr dispatch with native tasks or standalone relays. When Herdr is not requested, ordinary standalone OMP remains available.

Children must **SKIP ALL tests, gates, linters, formatters and runtime checks**, including mid-flight smoke runs. They edit and report only; no review, delegation, staging, commits, push or settings changes. The coordinator owns smoke checks and all final verification. Their report must include effective-model evidence (requested/configured/upstream unverified as applicable), changed paths, tests added, checks not run, outcome, deviations and blockers.

Retain task/process/session IDs and result paths. Follow the README's uncertain-delivery, terminal-state and cleanup rules; no blind resend, duplicate workers, idle-terminal acceptance or exit-only acceptance. A scope conflict returns to the coordinator before expansion.

## 3. Inspect and verify as coordinator

After all assigned edits land, inspect the entire diff and actual files against the frozen contract, including consumers/dependencies. Account for untracked changes, enforce allowed paths, preserve unexpected edits and investigate attribution. Check relevant links, API examples, report fields, exact guard and source-backed claims. Inspect snapshot/golden changes rather than accepting passing assertions blindly.

The coordinator runs focused smoke/affected checks where useful, then the four gates above on the ready batch, with logs tied to the inspected tree and environment. Worker self-reports do not replace direct coordinator evidence. Do not repeat gates on unchanged valid evidence. If changes invalidate evidence, run affected smoke checks and establish all four gates on the final tree; no check is waived merely because the edit is documentation.

## 4. Review independently and correct

Use the plan's risk level and explicit exceptions: Normal one independent reviewer, High two, Low coordinator inspection/gates only. Where the plan records a user-granted exception for this mission, apply exactly that exception and nothing further: it binds no other mission and selects no model for anyone.

Use fresh review sessions and the README's exact guard, report schema, fingerprints and actual completion checks. Supply frozen plan/full hash, exact diff base/current revision or uncommitted tree fingerprint, relevant files/dependencies and current gate logs through one complete evidence source. Verify requested/configured model/settings; disclose unverified upstream identity. Capture post-review fingerprints and preserve/inspect/stop on unexpected writes; read-only instructions are not sandbox enforcement.

Collect all findings into one correction brief. The coordinator may correct administrative documentation issues; product-code/test corrections go to the assigned implementer, still edit-only with no gates/formatters. Resolve every in-scope blocker with evidence. Defer only proved outside-scope issues or non-blocking suggestions. User-reported failures are ground truth, not something to rerun merely to confirm.

After corrections, update invalidated coordinator check evidence and request fresh targeted review from affected critics with the original brief, findings, responses and unresolved objections. Broaden review when dependencies, shared contracts or acceptance change. Verified unchanged scope may retain an unaffected verdict; no redundant broad review wave. Two non-convergent rounds require user escalation, not a third broad wave.

## 5. Handle amendments explicitly

| Situation | Action |
|---|---|
| Implementation violates the agreed contract | Correct implementation. |
| Technical detail changes without changed behavior/boundaries | Record evidence; amend only if the execution contract changes. |
| Behavior, scope, compatibility, permissions, machine state or execution contract changes | Stop affected work, verify concrete user authorization, then use the planning loop's new two-commit freeze. |

Reuse authorization already covering the concrete action. Coordinator and implementer verify the amended frozen reference before affected edits. Append-only execution/roster evidence cannot silently change the contract.

## 6. Accept, commit and deliver

Only the coordinator accepts, stages, commits and pushes. Require all of:

- Every authorized acceptance criterion and operative amendment satisfied; final files inspected.
- Four passing gates with valid coordinator evidence for the final tree/environment.
- Required independent verdicts complete, every in-scope blocker resolved, and no unexpected reviewer edits.
- Allowed paths only; required docs/callers/tests updated; user work preserved and excluded from staging.
- Observed delivery agrees with implementer reports; every child/process terminal, no active descendants, owned terminal/process cleanup complete.

Record a receipt in the dated plan/execution record: expected versus actual launches (including failed/interrupted ones), corrections/reasons, requested/configured identities/settings and upstream limits, result/report/log paths, elapsed time and tokens if exposed (otherwise unavailable). Never equate prompt characters or task count with billed tokens or unmeasured savings.

Stage explicit allowed paths only, then commit:

```bash
git add <allowed paths>
git commit -m "<type>(<scope>): <summary>"
```

Push only when the user explicitly authorized that push, to the destination they named; when a push is authorized, verify full hashes from `git rev-parse HEAD`, `git rev-parse origin/<branch>`, and `git ls-remote origin refs/heads/<branch>` agree. Report actual commit/push evidence, never assume delivery from an exit-only child receipt. Remove only owned unused checkouts after checking bindings and preserving user edits. Final receipt states what changed, why, actual checks/review evidence, commit/delivery status, deviations and any remaining user decision. Unchanged accepted evidence needs no duplicate verification wave.
