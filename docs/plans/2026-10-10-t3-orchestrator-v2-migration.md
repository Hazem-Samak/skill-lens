# Plan: migrate the process from Orca to T3 Orchestrator V2

Status: Agreed
Authorization: Hazem approved the reviewed findings and requested migration on 2026-10-10. Sol 6.1 coordinates; Antigravity Gemini 3.8 Flash High is the sole implementer; Pi, Grok and OpenCode are the native planning/review pool with models chosen per session. MCode MiniMax M3.1 Flash is a future ACP addition, not part of this migration. No push, release, provider reconfiguration or C4 work is authorized.
Reference: pending amended-plan freeze; record the exact commit in a following plan-only provenance commit before further implementation.
Previous reference: `bd3b1e2fc6ef2a250506bb3ff93a65c3512ad991` (original frozen plan, retained in Git history).
Source baseline: `5c03d11` on `main`, clean working tree.

## Outcome

An agent in this T3 thread can follow the repository's planning and implementation
loops without opening Orca. Plans remain reviewed and committed before implementation;
Sol verifies and commits accepted changes. Completed phase records stay unchanged.

## Current state

- The four active process documents embed Orca commands, terminal identity, launch
  routes and the former fixed reviewer roster. `AGENTS.md` already points to the
  loops without naming Orca; it needs no edit.
- The attached brainstorming proposal agrees on preserving the method and archiving
  Orca. Its blanket read-only downgrade, worktree security claim and use of
  `t3_thread_launch` for a current-thread handoff need the accepted corrections.
- Current Orca council/machine docs explicitly used instruction-only protection for
  OpenCode, MCode and Pi; Orca was not a universal filesystem boundary.
- Installed T3 is `0.0.46-nightly.20261010.2935`. Live discovery exposes child tasks,
  async completion, cancellation, and runnable `antigravity`, `opencode`, `grok`,
  `pi` providers; `codex` is also runnable. Antigravity model
  `gemini-3.8-flash-high` is available.
- T3 access modes and interaction/Plan mode are distinct. Provider policy handling
  differs; Supervised is approval gating, not a cross-provider immutable checkout.
  Verification will distinguish static mappings, observed behavior and untested
  adversarial enforcement. Worktrees share access and are not a security boundary.
- This thread is bound to the project root on `main`, with no attached worktree.
  The clean tree needs no handoff. The app's origin-start default is true; future
  local worktree handoffs must choose their base and origin policy explicitly.
- `profiles/project-profile.md` has incorrect relative links to root findings/build
  records. Its policy stays unchanged; repair those pointers as a bounded migration
  dependency so fresh reviewers can reach the required sources.

## Models for this phase

- Coordinator: native `codex`, `gpt-6.1-sol`, configured reasoning `xhigh`.
  Evidence: coordinator's own `t3_thread_configuration` on 2026-10-10 returned
  this provider/model and `reasoningEffort=xhigh`, runtime `auto`, interaction
  `default`. Replace the historical `gpt-6.1-sol-900k` identifier in active docs.
- Sole implementer: native Antigravity, `gemini-3.8-flash-high`.
- Planning and final reviewers: Hazem selected OpenCode `opencode/space-bunny-free`
  with `variant=max`, and Grok `grok-4.7` with `reasoningEffort=high`.
  Grok's first planning task failed with "Grok usage limit reached. Try again later."
  Hazem explicitly authorized its replacement with Pi
  `tokenharbor/deepseek-v4.1-flash:free`; use the live catalog's default
  `thinking=max`. OpenCode and Pi now cover separate questions in fresh tasks.
- MCode is documented as pending ACP support only. Model/provider identity and
  options must be explicit in every dispatch. Read `t3_thread_configuration` for
  configured options; task receipts show provider/model, and provider session
  evidence corroborates effective use where available. Catalog `currentValue`
  is not proof of the running task's options. Distinguish requested, configured,
  provider-confirmed and unverified settings without inventing a contradiction.

## Scope and boundaries

Allowed repository changes:

- This plan: coordinator drafting, decisions, freeze provenance and acceptance.
- `docs/process/planning-loop.md`.
- `docs/process/implementation-loop.md`.
- `docs/process/council.md`.
- `docs/process/profiles/machine-profile.md`.
- `docs/process/profiles/project-profile.md`: relative-link repairs only.
- `docs/archive/orca-process-2026-10-10/`: byte-identical copies of all five
  baseline process documents in their original subdirectory layout, plus a README
  giving the source commit, checksums, original link context and active-workflow link.

No product code, tests, packaging, registry, specification, AGENTS.md, previous plans
or phase records are edited. No global settings, ACP bridge, scheduled task or new
top-level conversation is created. The coordinator owns plan and final commits.

## Implementation steps

1. Recheck source, live catalog, permission distinctions and baseline gates. Select
   the review roster once from the user's answer; do not silently select/fallback.
2. Dispatch both read-only plan reviewers through T3 before waiting. Give one
   lifecycle/model/workspace semantics, the other project guarantees and protection
   proof. Use `runtimeMode=approval-required` and `interactionMode=plan`; preserve
   task IDs and stable per-round request IDs; pass role=review and explicit target
   provider/model/options. An async dispatch is not a completed review: end the turn
   for completion notifications, or use a bounded wait when needed. Read both
   terminal results before Step 3; timeout does not cancel or authorize replacement.
   Inspect status and file fingerprints around their work, with no concurrent
   checkout mutations. Hazem authorized coordinator handling of routine read
   approvals: use supported app controls when available, inspect each action and
   approve only permitted reads. T3 question-response tools cannot approve
   permissions. Deny critic edits and do not switch to full access to avoid prompts.
3. Resolve findings, then commit only the agreed plan. Record its full commit hash
   in a following plan-only provenance commit; commit identity is not authorization.
4. Delegate the permitted document implementation to Antigravity with the frozen
   plan reference. It archives the exact originals before replacing active content,
   repairs project-profile pointers and does not commit. It reads the new role rules
   but relies on the explicit migration brief for this bootstrap assignment. Use
   role=implementation, explicit antigravity/gemini-3.8-flash-high, runtimeMode=auto,
   interactionMode=default. Its listed document writes are authorized; the
   coordinator may approve those scoped actions when the provider prompts.
   Reviewer approval is restricted to permitted reads; implementer approval also
   covers the listed migration writes. Neither role gets blanket full access.
5. The active loops retain Inspect/Draft/Resolve/Freeze and baseline/dispatch/verify/
   review/rework/accept. Add the per-session model menu; keep the fixed coordinator
   and implementer, user-selected critics/settings, and risk-scaled one/two critics.
   Rewrite Freeze to the explicit two-commit procedure: commit the agreed plan,
   read its full hash, then make a plan-only provenance commit recording that hash.
   Explain that a commit cannot contain its own future hash; the provenance commit
   must not change frozen behavior. Verify the frozen reference before implementation.
   Retain a named Waiting rules section and the implementation-loop cross-reference:
   answer questions first (separate permissions), match task/run identity, inspect
   stalled work once rather than blind polling, never treat silence as failure or
   approval, never duplicate active work, and verify cancellation actually settled.
   The implementation roster is an authorized append-only execution record, not an
   unreviewed change to the frozen behavior contract. Different providers alone do
   not establish different model families. Unknown family identity stays unverified.
6. `council.md` is the authority for roles, model selection, guard/report formats,
   T3 task lifecycle and permission protection. Remove Antigravity reviewer duties
   and FEASIBILITY field. Keep the existing guard verbatim, explicitly reject
   review edits, and use status plus fingerprints. Detect changes without blindly
   restoring user work. Keep two-round non-convergence and approval boundaries.
7. Document T3 semantics accurately: async completion wakes the parent; status is
   used when needed mid-turn; a wait timeout never cancels; fresh review rounds use
   new tasks/request IDs with complete prior findings. Child backing thread IDs are
   not continuation targets. Cancel/inspect remaining child work on completion;
   there is no Orca worker-release substitute. No unrequested top-level threads.
   Current-thread worktree isolation uses `t3_worktree_status` then handoff with an
   explicit branch, base, origin policy and continuationPrompt as the last tool
   action of a turn. Inspect the project setup script and explicitly choose
   runSetupScript (default true); inspect setup/continuation outcomes after resuming.
   If setup or continuation fails, stop and report that outcome instead of treating
   failure as skipped. No shell-only worktree switch. Child tasks in this run were observed on the
   caller's main checkout; inspect live binding instead of claiming universal
   isolation. Worktrees survive thread deletion: record ownership, and clean up
   only owned, unused worktrees after checking for user edits and active bindings.
   Do not create one for this already suitable root checkout. If the user requests
   a separate top-level conversation, use t3_thread_launch with explicit workspace
   strategy (omission selects project root); create_threads inherits the caller's
   checkout. Launch has no idempotency key: inspect thread_list before retrying a
   lost response. Respect mode-narrowing restrictions. Cancellation retries retain
   their own stable clientRequestId; cancel_requested is not terminal proof.
8. Machine profile records observed build/capabilities, exact fixed model IDs and
   pool providers, live-preflight rules and MCode future integration requirements.
   Do not claim untested spawn depths, global CLI floors, zero threads, hard
   read-only guarantees or working Orca fallback from installation alone. Name Pi's
   deferred-tool/tool_search discovery and native read/grep/find/ls allowance as
   installed-source evidence in installed-policy-2.txt, not verified Auto behavior;
   the source maps other tools to prompts even in Auto. Plan mode is interaction guidance, not
   permission enforcement. If a selected model disappears or exhausts its quota,
   use an already authorized fallback or ask once; never silently substitute.
9. Verify static invariants and archive checksums, all active Markdown links, role
   consistency, permitted-file scope, and all four gates. No permanent gate/test is
   added; disposable checks and logs go under a unique `/private/tmp` directory.
10. Verify a controlled synthetic permission fixture without using real skills or
    allowing a checkout write. Read the provider policy mappings and run ordinary
    read-only review tasks. If an attempted-write probe requires human permission,
    leave it pending or cancel it; do not approve a critic mutation. Record the
    observed approval/block versus any untested guarantee honestly. Never describe
    source inspection or an unchanged checkout as adversarial enforcement proof.
11. Dispatch fresh independent final reviews against the frozen plan and complete
    diff, without priming their conclusions. Resolve confirmed findings, rerun
    affected checks/gates as needed, record actual task/model/protection evidence,
    and commit accepted documentation. C4 remains the next separate assignment.

## Acceptance

- Active loops/council/machine profile drive T3 V2 child tasks; no executable Orca
  dependency remains. The archive README labels/links the historical workflow and
  provides the forward pointer; prior frozen plans and records remain unchanged.
- Fixed coordinator/sole implementer and Pi/Grok/OpenCode session-selected reviewer
  pool are consistent everywhere. MCode ACP integration is deferred explicitly.
- Planning and implementation menus ask once when missing, reuse already provided
  choices, never silently dispatch unresolved/default critic models, and record
  effective provider/model/settings and evidence without silently refreezing scope.
- Reviews use the guard, explicit Supervised/Plan settings, pre/post status and
  fingerprints. Docs separate approval gating, detection, workspace isolation and
  hard write prevention. Probes never mutate the project or real home.
- Child task IDs, idempotent retries, async wakeup, timeouts, fresh review rounds,
  pending child runs, stop/cleanup and worktree binding are described accurately.
- Frozen-plan authorization/hash provenance, one phase at a time, independent
   evidence-first review, four gates, 90% coverage, read-only product execution,
  synthetic HOME tests, snapshot/golden discipline and two-round limit survive.
- Archive originals match `5c03d11` bytes; all active pointers resolve; AGENTS.md,
  previous records and all product/test/config files match the baseline.
- Coordinator inspects the whole diff and receives both selected independent
  planning/final verdicts, resolves blockers and reruns all four project gates.
- Final report states what is proven versus conditional/unverified, commits and
  exact scope. No push, publication or C4 implementation.

## Review decisions

OpenCode first round: changes_required. Grok first round: failed due to usage
limit; no review verdict. Pi replaces it under Hazem's explicit instruction.

- Accepted OpenCode findings 1, 2, 4 and 5: explicit terminal-result barrier,
  Waiting rules, exact dispatch identities/fallback handling, and worktree setup,
  continuation and ownership/cleanup requirements are now specified above.
- Accepted the evidence-source concern in finding 3. Rejected its assertion that
  no settings readback exists and that Medium contradicts this task's Max setting:
  `t3_thread_configuration` returned `variant=max` for the actual OpenCode child.
  The catalog's default/currentValue is not session-specific evidence. Configured
  Max is confirmed; provider execution beyond the available receipt stays qualified.
- Accepted suggestions on provider IDs, role=review, cancellation request identity,
  observed workspace sharing, top-level-thread defaults/retries/mode limits, Pi
  discovery and permission prompts, and no silent Antigravity model fallback.
- Completed source receipt with the OpenCode always-allowed permission constant
  in the disposable mapping probe. This is static mapping evidence, not proof that
  a live adversarial write was denied.
- Hazem additionally authorized coordinator handling of routine worker approvals.
  The exposed question-response MCP tools cannot approve permission requests;
  supported native app controls are usable.
  Inspect exact operations, allow routine reads/authorized implementation actions,
  deny reviewer mutations, and report an unavailable approval surface honestly.

OpenCode second round and Pi replacement first round: changes_required, with
earlier lifecycle/settings objections withdrawn and preserved guarantees confirmed.
The coordinator reproduced and resolved the remaining documentary findings:

- Accepted OpenCode's Freeze requirement: Step 5 now explicitly requires the
  two-commit provenance procedure in the migrated loop, matching existing C3 practice.
- Accepted Pi's implementation-approval finding: Step 4 now names modes and
  scoped write authority separately from critic read-only approval in Step 2.
- Accepted both reviewers' coordinator-evidence concern: the coordinator's own
  configuration receipt confirms codex/gpt-6.1-sol/xhigh/Auto/default; recorded above.
- Accepted suggestions to qualify Pi source evidence, name literal provider IDs,
  distinguish questions from permissions consistently, stop on failed worktree
  preparation, and locate the forward pointer in the new archive README.
- Deliberately replace blind git restore after reviewer edits with attribution,
  inspection and preservation of user work; detection does not grant restoration
  authority. Remove the old Orca nested-depth justification for coordinator roles.
- Source-mapping probes and live ordinary read approvals have different evidence
  strength. Bash and external-directory reads can prompt in Supervised mode.
  Coordinator owns fingerprints so critics need no approval-heavy shell checks.
- Automatic approval review rejected the initial TokenHarbor payload until Hazem
  explicitly approved the migration draft/workflow/findings destination. That
  authorized retry succeeded. It also rejected broad search/directory access;
  reviewers were steered to named evidence and inline mappings. Do not bypass
  automatic rejection; narrow the action, or report the specific unmet approval.
- Retain task cancellation/remaining-child checks without inventing an Orca release
  command or claiming completed threads have no persistent resources.

No unresolved behavioral blocker remains. Coordinator verification of these narrow
text corrections is sufficient before freeze; no third broad planning wave is
required. Existing accepted decisions retain fixed roles, archive preservation,
future-only MCode and unchanged product/phase scope.

## Permission amendment — 2026-10-10

Authorization: Hazem explicitly requested, "I don't want to click approve for anyone
else please, make them yolo or give them full access."

This operational choice supersedes Step 2's Supervised dispatch requirement,
Step 4's Auto dispatch requirement, the prohibition on blanket Full access, and
the matching mode-specific acceptance language for the remaining migration work.
The frozen document scope, roles, model choices, independence, gates, archive
preservation and read-only product guarantee are unchanged.

- Dispatch every remaining migration worker with runtimeMode=full-access;
  reviewers retain interactionMode=plan and role=review, and Antigravity retains
  interactionMode=default and role=implementation. Do not silently lower the mode
  and leave the user handling repeated permission prompts.
- Antigravity's first task was cancelled before any repository edit. Confirmed
  terminal status: interrupted, hasPendingChildRuns=false. Restart it once with
  the complete original brief, this amendment and a distinct request/task ID.
- Critics still receive the verbatim read-only guard and report-only assignments.
  Full access permits writes at the permission layer: reviewer restraint is now
  instruction-based, with coordinator status/fingerprints for detection. Plan
  interaction mode does not prevent writes. Never claim enforced read-only review.
- Record this as Hazem's standing workflow permission preference in active docs;
  both loops reuse existing authorization until the user changes it. Model/settings
  choices remain per-session. Explain Full access and Supervised accurately;
  preserve explicit user choice rather than silently widening permissions.
- Full access does not expand the task's authorized file/data scope, authorize
  critic edits, global configuration, commits by workers, publishing, C4 or ACP
  integration. The coordinator continues to own acceptance and commits.
- Provider prompts and automatic approval review are separate. Full access is
  intended to remove provider permission prompts, but does not disable automatic
  approval review. If T3 refuses this mode or automatic review rejects an action,
  report the exact limitation and narrow the action when possible; do not bypass
  that rejection or promise an unavailable approval-free guarantee.
- Verify each new child with t3_thread_configuration. Record configured mode and
  distinguish it from provider behavior. Independent final reviews check these
  amended permission statements along with the original frozen migration contract.

## Review-standard amendment — 2026-10-10

Authorization: after disclosure that Space Bunny's underlying model family could
not be verified, Hazem explicitly chose, "Keep the selected pair and record the
unverified family."

- High-risk review ordinarily requires two critics from verified different model
  families. If a selected family cannot be verified, disclose the limitation and
  proceed only after the user explicitly accepts the named pair for that session.
  Record the acceptance and the unverified identity; never claim verified family
  diversity. A different provider alone does not establish a different family.
- This migration retains OpenCode `opencode/space-bunny-free`, `variant=max`, and
  Pi `tokenharbor/deepseek-v4.1-flash:free`, `thinking=max`, under that explicitly
  accepted path. Space Bunny's upstream family remains unverified. This is a
  session-specific exception, not permanent reviewer defaults or a future waiver.
- Fresh delegated critic tasks retain role/context independence. Verified family
  diversity is a separate claim. Sharing the coordinator's or implementer's family
  does not satisfy the verified-family requirement, even with a separate context.
- Re-freeze this complete plan, including the already-authorized Full access
  amendment and this review-standard amendment, using two plan-only commits.
  The new `Reference:` must contain every operative amendment. Preserve the
  original freeze and permission-amendment commits as historical evidence.
- Teach the same provenance rule in the active loops: approved changes to the
  frozen execution contract require a new two-commit freeze before affected work.
  Ordinary execution-roster, provenance and acceptance records cannot silently
  change that contract. An arbitrary newer plan commit is not fresh authorization.

## Final review, round 1 — adjudication

OpenCode: changes_required. Pi: pass. Both tasks are completed/result_available
with `hasPendingChildRuns=false`. The coordinator verified that all 135 captured
tracked/untracked file fingerprints and repository status were unchanged during
the reviews.

- Accepted OpenCode's family-rule blocker. The explicit user choice above resolves
  the review-standard decision; Antigravity will document the unknown-family path.
- Accepted OpenCode's frozen-reference blocker as a provenance clarity defect.
  Re-freeze all approved amendments before the next correction task. Do not make
  the newest arbitrary plan-only commit the execution authority.
- Accepted both reviewers' literal `\\n` prompt correction and source-path clarity
  suggestions. Record the Pi extension symbol, installed build and archive path;
  qualify disposable receipts as not retained, and re-derive mappings on upgrades.
- Accepted OpenCode's preflight remedy, nullable `childRunId`, distinct cancellation
  request identity and non-terminal `cancel_requested` clarification. Preserve
  observed caller/child checkout binding without inventing a security boundary.
- Rejected OpenCode's claim that the setup-script default lacks tool support:
  the live `t3_worktree_handoff` description explicitly says it runs the project
  setup script by default. Qualify the description source and still pass the option
  explicitly; do not claim the schema itself declares a default.
- Rejected Pi's suggestion to dispatch at a narrowed caller mode. Hazem's standing
  Full access choice forbids silent downgrades. Activate the already-authorized
  mode and verify a following-turn readback, or report the actual activation limit.
- Pi's shorthand file total is not a manifest. Coordinator scope verification is
  authoritative: five modified active docs and seven new files (plan plus six
  archive files) relative to `5c03d11`; every other baseline file is unchanged.
- Antigravity owns the narrow active-document corrections; the coordinator owns
  this plan, freeze/provenance, gates, final acceptance and commit. No product,
  global setting, ACP, C4, push or publication scope is added.

## Verification and acceptance record

Pending execution. Record baseline/final gate results, reviewer task IDs and actual
model/settings, archive/link/scope checks, permission observations, limitations and
task cleanup here. Do not mark migration complete from an implementer's self-report.
