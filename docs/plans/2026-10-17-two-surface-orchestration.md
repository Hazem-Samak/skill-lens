# Plan: add cmux + Herdr alongside T3 Code

Status: Agreed — approved for freeze and implementation on 2026-10-17
Surface: t3
Authorization: User, 2026-10-17: "Okay approve this plan commit and freeze it / And implement it /
worker will be gemini 3.8 flash high from agy / The two reviewers will stay the same."
This authorizes the two-commit freeze, bounded implementation/pilot within this plan,
Antigravity Gemini 3.8 Flash High as sole implementer, and the same session-selected
MiniMax/mcode xhigh and Pi/WorkBuddy DeepSeek high reviewers. Required explicit pilot
session/lifecycle and role-mapping approvals remain governed by sections 4.4–5. The later
separately frozen real Herdr task remains outside this migration's authorization.
Earlier drafting authorization: "Okay now you can draft a plan which is 100% solid and agreed?"
Standing delivery source: the [U2 plan authorization](2026-10-12-tui-u2-controller-skeleton.md),
recorded 2026-10-12, states: "Earlier instruction requires pushing every coordinator commit
to GitHub." This governs delivery only after a commit/freeze is separately authorized;
the current user instruction above now separately authorizes these migration commits/pushes.
Reference: pending
Risk and review: High — changes orchestration, permissions, independent-review evidence,
and the development execution contract. Two independent planning critics and two final
implementation critics are required under the existing council rules.
Expected child tasks: 5 for a separately implemented migration before corrections:
2 formal plan critics + 1 Antigravity implementer + 2 final critics. The earlier proposal
debate used 4 additional tasks. Synthetic pilot agents are separate, recorded actual
launches; this estimate never permits skipping a required role or check.

## 1. Outcome and completion boundary

Keep T3 Code and cmux + Herdr indefinitely, with one shared process and two mechanics
profiles. T3 continues using native Codex/Sol; Herdr uses Sol through Hermes inside a
Herdr-managed pane. Antigravity remains the sole product-code/test implementer.
Each task uses one surface end-to-end; concurrent tasks use separate checkouts.

The migration is accepted only after its isolated pilot, document changes, four gates,
and independent final review pass on T3. That establishes **trial-ready** Herdr support
for the tested roles/capabilities, not proof of routine operational success. A later,
separately authorized and frozen real task on `Surface: herdr` confirms operation;
only after its independent acceptance is the tested capability set marked **supported**.
This later task is not authorized or implemented by drafting this plan.

No plan can guarantee unknown runtime behavior. This plan fixes the required behavior,
evidence, permitted scope, and failure response; it does not turn an unrun pilot into
a passing result.

## 2. Current state and evidence

Baseline inspected 2026-10-17: `main` at
`2d9637054aea969fb2ec575cf28e48ed0ec1a800`; pre-existing untracked `.path` is user work.
Recheck before future execution; this is not a permanently clean-tree claim.

- [Planning loop](../process/planning-loop.md), [implementation loop](../process/implementation-loop.md),
  [council](../process/council.md), and [machine profile](../process/profiles/machine-profile.md)
  contain the active T3 process. [Project profile](../process/profiles/project-profile.md)
  is surface-neutral. AGENTS.md points at unchanged loop paths.
- Original proposal and both rounds of the proposal debate are retained under
  [planning evidence](../validation/two-surface-orchestration/2026-10-17/planning/README.md).
  Both final proposal reviews passed. Those verdicts reviewed the proposal, not this exact file
  or a working Herdr installation.
- Live T3 catalog/configuration verified the session selections: MiniMax
  `m:minimax:MiniMax-M3.1-Flash-Preview:v:thinking` via `mcode`,
  `thinkingEffort=xhigh`; DeepSeek `workbuddy/deepseek-v4.1-flash` via `pi`,
  `thinking=high`. Both permit child review tasks. Catalog/defaults and receipts prove
  configured selections, not independently confirmed upstream family identity.
- Read-only `herdr --version` reports `0.9.5`. Its installed `--skill` states that control
  commands require `HERDR_ENV=1`; prompt/wait state does not identify individual turns;
  Antigravity/Grok may appear idle while background work continues. No server was launched
  or controlled for drafting.
- The attachment's installed versions, integration currency, proxy configuration and
  restart/resume claims remain dated observations until rechecked in the authorized pilot.
  In particular, `gpt-6.1-sol` on T3 and a configured Hermes `-900k` alias are separate
  routes; neither implies the other is wrong.
- DeepSeek's proposal-round-two report mislabels its own identity as MiniMax. Preserve
  the report unedited; T3 task/configuration receipts identify its configured Pi/WorkBuddy
  route. Never use that self-report as upstream execution proof.

The current council/machine-profile roster still labels MCode deferred; live T3 availability
and the user's named selection are a session exception, not a permanent pool expansion.
The user-selected critic pair/settings are reused for this session's exact-file review;
they do not become permanent defaults or amend the standing pool. Unknown upstream identity
is disclosed, with the user's continued named-pair selection after that disclosure serving
as session authorization. Future sessions follow the existing selection/family procedure.

## 3. Scope and allowed paths

Only the draft plan and its planning evidence may be written during this drafting task.
Everything else below is a **future implementation allow-list**, conditional on explicit
implementation authorization and a valid freeze.

| Path | Required future change |
|---|---|
| `docs/plans/2026-10-17-two-surface-orchestration.md` | This operative plan; later append-only execution/acceptance records |
| `docs/validation/two-surface-orchestration/2026-10-17/planning/**` | Original proposal, debate/review evidence, receipts and decisions; no credentials |
| `docs/process/council.md` | Keep shared rules once; move tool mechanics; surface-neutral evidence wording |
| `docs/process/planning-loop.md` | Declare surface before review, profile preflight/dispatch/cleanup pointers; retain sequence/freeze |
| `docs/process/implementation-loop.md` | Surface-specific readiness/dispatch/terminal evidence; retain role and acceptance rules |
| `docs/process/surfaces/t3.md` | New complete extraction of current T3 mechanics, preserving semantics |
| `docs/process/surfaces/herdr.md` | New observed Herdr mechanics and readiness limits |
| `docs/process/profiles/machine-profile.md` | Dated facts by surface; model routes, permissions, integration versions and evidence pointers |
| `docs/validation/two-surface-orchestration/2026-10-17/setup.md` | Actual authorized setup changes, versions, roles/settings and rollback limits |
| `docs/validation/two-surface-orchestration/2026-10-17/pilot.md` | Pilot matrix and reproducible pass/fail/unverified evidence |
| `docs/validation/two-surface-orchestration/2026-10-17/acceptance.md` | Final scope, gate logs, review dispositions, readiness and delivery receipt |
| `docs/validation/two-surface-orchestration/2026-10-17/implementation/**` | Sanitized implementer/final critic receipts, reports, fingerprints and gate logs |
| `docs/archive/orca-process-2026-10-10/README.md` | Optional active-workflow pointer only |

No changes to AGENTS.md, project-profile.md, product code/tests, snapshots, registry,
specifications, packaging, CI, or historical record bodies. Preserve unrelated changes.
Do not install a new orchestration service, validator framework, provider, model route,
or personal plugin. Temporary pilot scripts/fixtures live outside the repository.

## 4. Fixed process contract

### 4.1 Shared rules and surface selection

Keep roles, family/independence rules, verbatim critic guard, report fields, risk levels,
two-round escalation, authorization, freeze, and four gates shared. Each surface supplies
mechanics rather than a copied process. Keep the coordinator out of product code/tests;
Antigravity never reviews, delegates, or commits.

New drafts declare `Surface: t3 | herdr` before dispatch. Freeze it with the operative
contract; receipts repeat it. Changing surface follows the current authorized amendment
and two-commit procedure, confirmed stop of old work, and fresh target-surface review rounds.
Unavailability never authorizes a silent replacement or continuation.

Do not rewrite legacy frozen plans. Resolve surface from explicit operative mechanics or
authoritative execution receipts; a roster only corroborates an unambiguous reading.
Never infer from age, filename, model brand alone, or today's default. Ask once before
affected work if evidence conflicts or remains ambiguous.

Use existing frozen references, checkout revisions and receipts. Optional profile hashes
are evidence only; no mandatory pinning mechanism or amendment per factual version refresh.
A live profile/fact update cannot silently replace a frozen permission/execution contract.

### 4.2 Herdr dispatch, context and evidence

Every worker receives a unique per-dispatch token and exact target revision/fingerprint.
Record session/server, pane ID, unique agent name, kind, native arguments, submitted brief,
submission/wait results, complete report, observed outcome, and cleanup/stop evidence.
A report envelope echoes the token and target while preserving the existing report fields.
Accept a report only after matching both. Tokens do not provide server-side idempotency.

Each critic round uses a fresh agent session, not merely a new pane. Prevent automatic
import of prior reviewer conversations/recall; explicitly supply the original brief and
relevant debate history. Use session-scoped controls, never silently edit personal/global
memory or plugin settings. If fresh context cannot be established, that kind is not ready.

Use the installed help/skill for command syntax. A new worker starts from an available
shell pane and confirmed ready state. Parse IDs from JSON; preserve cwd and human focus.
Submit all critic prompts before the coordinator collects completion; capture independent
submission-job results. Validate the actual parallel pattern through pilot evidence.
No serial fallback within this contract. A change to that policy needs an authorized
amendment. On uncertain delivery, inspect and reconcile; never blindly resend or launch
a replacement while the original may still be active.

Use full report readback, with temporary Markdown output outside the repository only if
the completed response cannot be recovered. Pre-authorize that fallback in the brief but
do not demand initial file output. Long-report/full-screen capability remains unverified
until tested for the actual kind. Record artifact content/hash in durable evidence;
a temporary path alone is not an acceptance record.

### 4.3 Worker outcomes, acceptance and cancellation

Succeeded/failed/interrupted/unknown is outcome bookkeeping, separate from coordinator
acceptance. Idle/done means UI readiness. Interrupted may close a task record; it cannot
satisfy a required successful review or implementation result.

Before final verification/acceptance, establish that task-owned commands/background children
have stopped using integration evidence plus bounded owned process/job readback.
Ctrl+C, a closed pane, a report, or a settled UI alone is insufficient. Do not demand
control of every machine process. Prohibit nested implementer delegation as today.
If liveness cannot be resolved, preserve the workspace and record unknown/interrupted;
block affected acceptance and replacement dispatch until the old activity is resolved.

Close only owned resources. Exempt the continuing coordinator pane and user resources.
Remove only owned, unused, clean worktrees after checking bindings and preserving results.
Neither ownership nor a cleanup checklist requires deleting unfinished work.

### 4.4 Permissions, identities and session policy

The native role envelope is fixed: critics may inspect relevant repository/dependencies
and write only permitted temporary reports; implementer may edit allowed target files,
run checks and report, but not delegate/review/commit; coordinator may run orchestration,
inspect, verify and commit only authorized paths. Do not interpret T3 Full access as a
Herdr flag or hard read-only protection.

Derive native settings from each CLI's installed help plus controlled disposable probes,
record the chosen Herdr kind/model/arguments/settings per role in setup.md, and obtain
the user's once-per-session role-mapping
approval before real work. Only isolated tests of a proposed mapping may precede that
approval under a later authorized pilot. A deny-write probe proves its tested boundary,
not an adversarial sandbox; retain guard and fingerprints regardless. No wider persistent
permission, trust, or global default may be introduced as an empirical syntax correction.

Inspect blocked dialogs before deliberately answering routine reads already covered by
authorization. Do not blindly send keys. Unknown dialogs, writes outside scope or wider
permissions stop for the user. This future explicit policy governs delegation approvals;
it does not authorize this T3 session to control Herdr from outside a Herdr pane.

Keep requested/configured/provider-confirmed-or-unverified identity/settings separate.
T3-only mode fields retain their meaning on T3; mark them N/A on Herdr and record native
controls in the same evidence field. Integration currency is lifecycle evidence, not
served-model proof. Record T3 and Hermes aliases per surface; no automatic normalization.
Unproved upstream family stays unverified under the existing user-accepted named-pair path.

Proposed session policy: a dedicated project session, with a separate named pilot session
and human-controlled startup. The execution user must approve actual names/startup and
role settings once before the authorized pilot uses them. Notifications are optional
unless pilot evidence shows attention delivery is necessary; no new hooks in this scope.

## 5. Future machine-action bounds

Nothing here is activated by drafting. A later authorization/freeze may permit:
- Verify installed help/versions/integration state and existing proxy availability/routing,
  without printing secrets or changing a model alias.
- Update only stale integrations for selected required kinds, recording before/after.
  Do not upgrade the Herdr app/CLI, install providers, or update unused kinds.
- Start a named isolated pilot session after the user approves its lifecycle. All control
  commands run from a Herdr pane with `HERDR_ENV=1`; an outside T3 observer reads evidence
  and coordinates the migration, not neighboring live panes.
- Use per-launch/session settings and disposable synthetic fixtures. No persistent personal
  plugin, memory, shell-shim, trust, model, proxy, or service changes.
- A user-operated restart of the **owned test session** may be observed from an external
  control point. Do not run `herdr server stop` from its active driving pane, stop a shared
  daily server, or reboot the machine.
- If the existing proxy is absent/broken, the user starts/repairs it under separate authority;
  no autonomous service installation, route rewrite, or fallback is permitted.

Record actual setup changes in setup.md. If a required capability needs a prohibited
machine action, stop and amend before proceeding. These bounds make pilot failure an
allowed result; they do not promise the installed stack can pass.

## 6. Implementation sequence (not started)

### Phase A — authorized freeze and T3 baseline

After this draft's exact-file reviews, resolve blockers and record decisions. Freeze only
after explicit authorization to freeze/adopt, using the existing two-commit procedure.
Do not infer implementation permission from the commit. Push and verify every authorized
local commit under the user's standing GitHub instruction.

On later implementation authorization, Sol verifies frozen reference/amendments, current
checkout binding, allowed scope, session roster/settings and baseline four gates. Store
logs externally first and retain sanitized evidence under the allowed implementation path.
Preserve pre-existing work; do not create a worktree unnecessarily.

Migration ownership remains T3 end-to-end. Herdr pilot agents are the system under test,
not substitutes for this migration's T3 planning/final council. The pilot brief explicitly
permits controlled Herdr experiment topology and disposable targets. No activation uses
unverified Herdr to approve its own process migration.

### Phase B — bounded setup and synthetic pilot

Sol coordinates the user-present setup within section 5, then supplies a synthetic pilot
brief. The Herdr coordinator operates inside the owned test session. Tests use synthetic
HOME/XDG and fixtures, never live user skills. CLI authentication can use existing authorized
credentials, but fixtures/discovery must stay confined to the synthetic checkout. Record
which native session controls establish that separation; if it cannot be established, stop.

| ID | Exercise | Required evidence and failure consequence |
|---|---|---|
| P01 | Hermes coordinator entry and context | HERDR_ENV gate, actual session/model route and scoped shell commands; fresh context proved or role unavailable |
| P02 | Two independent critics in one wave | All submissions before parent completion collection; distinct tokens/targets, complete reports, clean before/after fingerprints |
| P03 | Actual agy/Antigravity implementer | Intended model/config evidence; tiny allow-listed synthetic edit, implementer report, independent coordinator comparison, handoff to critics; no commit/delegation |
| P04 | Full-screen/long report and fallback | Actual selected kind recovers long response or temporary-file fallback with matching token/target; untested kind cannot advertise capability |
| P05 | Permission/question handling | Observe blocked UI, authorized read response and harmless denied-write probe; record actual boundary, no universal-sandbox claim |
| P06 | Fast completion and ambiguous delivery | Deliberately exercise false-settle, delayed/stalled or timed-out observation; reconcile one submission without duplicates or stale-report acceptance |
| P07 | Active cancellation/background activity | Stop representative owned work, bounded job/process evidence, preserved output, unresolved liveness blocks acceptance/replacement |
| P08 | Detach and controlled restart | Observe separately; external human controller restarts only owned test session; no inference from layout restoration to worker termination or fresh context |
| P09 | cmux interaction and cleanup | Wrappers work or required role blocked; no focus theft/user resource edits; coordinator/dirty-worktree exemptions work |

Record each case as pass/fail/unverified in pilot.md with versions, inputs, commands,
report content and relevant readbacks. Include one intentional mismatched-token/stale-report
rejection and one unresolved-liveness rejection to prove these new acceptance guards can fail.
Use synthetic evidence to demonstrate rejection; never mutate product code to test process
guards. No machine reboot, uncontrolled process orphan, or live user configuration write
is required. Mark undemonstrated reboot guarantees unverified.

The minimum trial-ready role set is Hermes + actual agy + the user-selected two independent
critic roles. A role is ready only for its tested launch/model/permission/readback/control
configuration. Full-screen opencode, Codex, Grok, and other optional kinds are unavailable
for untested capabilities; do not certify all advertised kinds.

A required-case failure leaves T3 available and blocks trial-ready status. Do not silently
change flags, proxy, model family, surface, or permission policy to make a test pass.
Ordinary evidence/CLI spelling within the frozen envelope is recorded, while scope,
permission and execution-contract changes follow authorization/refreeze.

### Phase C — substantive documentation migration

Dispatch Antigravity on T3 with the exact frozen plan and allowed paths. It implements
the process documentation; Sol handles only allowed administrative records/corrections.
Workers never commit. Preserve temporary pilot behavior as evidence until the new
documents describe only the demonstrated contract.

1. **council.md:** keep shared roles/guard/risk/report/authorization once. Generalize lifecycle
   identities, terminal proof and requested/configured/confirmed channels. Add surface
   pointers. Describe this session's mcode selection as a named exception, not a permanent
   pool expansion or an assertion that deferred machine-profile facts are current.
2. **surfaces/t3.md:** retain full current preflight, dispatch JSON/options/modes, task/run
   identities, async waits, cancellation/pending children, fresh rounds, live selection,
   worktree/thread ownership and evidence/cleanup semantics. Compare source passages to
   destinations; reconcile demonstrably stale tool observations with live catalog/help
   through the existing contract-change rule rather than silently dropping rules.
3. **surfaces/herdr.md:** entry/HERDR_ENV, kind/session identity, dispatch/wave/readback,
   token binding, blocked dialogs, native permissions, owned stop evidence, cleanup,
   contexts/model evidence, failure recovery and capability readiness from pilot results.
   Keep Hermes internal delegation, gateway and cron off the council path. The profile
   may document observed-and-limited behavior; a failed required pilot case still blocks
   trial-ready status, regardless of the existence of documentation.
4. **loops:** add Surface to draft template/start prompts; parameterize readiness, dispatch
   and terminal evidence through profile pointers. Retain sequence, two-commit freeze,
   role separation, baseline/final gates and acceptance independent from terminality.
5. **machine-profile.md:** dated separate surface facts, independent route aliases,
   approved native settings/versions, recorded ownership/session and evidence pointers.
   Procedures belong in profiles, not duplicated fact tables.
6. **archive README:** optional active pointer only. Do not rewrite historical contract copies.

### Phase D — final acceptance and trial handoff

Sol inspects the full diff/actual files and performs section 7. Dispatch two independent
T3 final critics of the required risk/family configuration, using fresh tasks and fingerprints.
Resolve every in-scope blocker; target follow-up to affected reviewers and escalate after
two non-converging rounds. Record outcomes and capability limits in acceptance.md, including
the council execution-receipt fields: expected versus actual launches (failed/interrupted
included), reasons for extra rounds, elapsed time, and token usage or explicitly unavailable.

On success, mark only the tested set trial-ready. Commit allowed changes as Sol, push and
verify local HEAD, tracking ref and remote ref; report delivery failure plainly.
Do not mark unsupported capabilities live or auto-launch a production trial.

The next real Herdr task gets its own authorization, `Surface: herdr` plan/freeze and normal
review/gates. On its acceptance, append a dated supported-status receipt and update current
readiness facts only within that task's allowed scope. A failed trial stops affected Herdr
use; any switch to T3 requires an authorized surface amendment.

## 7. Acceptance and verification

- [ ] Only allowed paths changed; existing user work preserved.
- [ ] Shared guard byte-identical to the fenced critic block in council.md section 2 at
      baseline commit 2d9637054aea969fb2ec575cf28e48ed0ec1a800; roles, family rules, freeze, gates and
      escalation preserved. New process guard examples actually reject bad synthetic evidence.
- [ ] T3 source-to-profile no-loss comparison complete; live tool differences are recorded,
      with any operative changes separately authorized.
- [ ] Links/anchors and JSON/examples resolve; no duplicate shared contract.
      Check semantic placement instead of banning tool strings from shared schemas.
      Any string-sweep exceptions must be explicit, not an entire unchecked document section.
- [ ] Surface declaration, legacy resolution, correlation, fresh context, native modes,
      cancellation evidence and protected cleanup match section 4.
- [ ] P01–P09 required role cases pass with reproducible evidence. Optional/unverified
      capabilities are visibly unavailable; pilot failure never becomes a paper pass.
- [ ] Coordinator ran all four gates even though this is a documentation-only migration,
      on baseline and final inspected tree, with logs and
      coverage above configured 90% threshold, not exit codes alone:
      `pytest --cov=skill_lens`, `mypy`, `ruff check .`, `ruff format --check .`.
      Use repository virtualenv and synthetic-HOME rules. Review snapshot/golden diffs
      before any action; regeneration is out of this scope.
- [ ] Implementer report matches observed allowed changes; two required independent final
      reviews pass; no unresolved in-scope blocker.
- [ ] Every migration child task terminal, `hasPendingChildRuns=false`; pilot task-owned
      work stopped or migration acceptance blocked. Preserve coordinator/user resources.
- [ ] setup.md, pilot.md and acceptance.md agree with observed machine state and checkout.
      Trial-ready is distinct from supported; no unrun real task claimed.
- [ ] Authorized commit/push verified; failed delivery reported. Drafting alone has no
      freeze, commit, machine setup or implementation completion claim.

Current drafting verification: static plan/reference/scope checks and read-only repository
inspection. Required project gates may run for the drafting record; they do not prove
the future pilot or migration. Exact-file review evidence is recorded below when available.

## 8. Rollback and maintenance

A repository revert restores T3 process authority; it does not roll back installed
integrations or proxy state. Retain sanitized setup evidence before revert and explicitly
report facts the revert makes historical. Never present an old machine snapshot as current.
Machine changes are reversed only with authorization and conflict checks; no blind restore
of shared configuration or deletion of results. If the migration cannot meet acceptance,
stop with T3 available rather than partially activate Herdr.

Reverify affected kinds/capabilities after CLI/integration, proxy-route, permission or
context behavior changes. Focus checks on affected roles; do not invent a new full
migration for every optional kind. Missing evidence means unavailable/unverified capability.
Notification polish and persistent configuration changes remain outside this scope.

## 9. Review decisions and drafting receipt

The proposal debate settled the architecture, not runtime readiness:
- Accepted: correlation envelope; actual agy coverage; negative failure cases; bounded
  owned-stop proof; coordinator/dirty-worktree exemptions; legacy resolution; honest rollback.
- Corrected: interrupted is valid terminal bookkeeping, not acceptance. The original already
  contained a two-critic wave/coordinator path; additions are agy and negative cases.
- Rejected: mandatory profile hashes; blanket grep bans; automatic alias renaming;
  silent serial fallback; setup/pilot before authorization/freeze; all-kinds certification.
- Deferred outside this scope: production trial, optional kinds/hooks, global plugin/proxy
  reconfiguration. Native settings/route behavior are acceptance facts to measure under
  the fixed policy, not permission to invent broader behavior.

Exact-file review round 1 inspected SHA-256
bf7d0ab78b89743987963a967018e4d4e9a8184853009b647168948e33299891:
- MiniMax/xhigh: changes_required, one blocker: cite the standing push authorization.
  Reproduced the missing citation, verified the U2 authorization source, and added it above.
  Incorporated its non-blocking receipt/role-setting/gate-clarity suggestions.
- Pi/WorkBuddy DeepSeek/high: pass, no operational blockers. Incorporated its exact guard
  comparator and observed-and-limited profile clarifications without relaxing pilot readiness.
- Before/after review fingerprints: no changed repository paths across the review wave.

Targeted round 2 inspected corrected draft SHA-256
826eaf321de632183e6616fba56ea270340ed788cf774f1e214b15f0be2ac064:
- MiniMax/xhigh: pass, no blockers; explicitly withdrew its uncited-authorization blocker.
- Pi/WorkBuddy DeepSeek/high: pass, no blockers; explicitly confirmed the citation and
  preservation of its accepted operational scope. Its first round-2 task returned only
  reading narration, without a verdict; it was not counted as acceptance. One replacement
  completion task returned the complete passing report, with no intervening draft change.
- Coordinator adjudication: all in-scope findings resolved; optional wording suggestions
  do not change requirements. Only the Status line and this review record were updated
  after the final reviewed operative draft. All operative sections 1–8 are unchanged.
- Before/after fingerprints: zero repository changes during both reviewer windows,
  including the incomplete-result recovery. No reviewer edits were accepted.

Formal planning receipt: 5 launches across two review rounds, including 1 incomplete-result
replacement; the proposal debate used 4 earlier launches. Extra round: citation/evidence
corrections after the first exact-file review. Elapsed total and token usage: unavailable.
All task/run identities, configured settings, terminal/no-pending evidence, complete reports,
incomplete stub and dispositions are retained in the planning evidence path. Reviewers and
coordinator agree on planning content; upstream model identity and future runtime remain
unverified as disclosed above.

Drafting gates: 1048 passed, 1 expected case-insensitive-filesystem skip, 91.11% coverage;
mypy clean on 37 source files; Ruff check clean; final Ruff format: 184 files already formatted.
Test HOME/XDG and cache/coverage artifacts were isolated under an external temporary
directory. These checks verify the inspected repository, not future Herdr runtime behavior.

Historical drafting stop: no freeze or implementation was performed during drafting.
The user's 2026-10-17 approval recorded above now authorizes freeze and bounded implementation.
This approval updates authorization/status only; reviewed operative sections 1–8 are unchanged.

