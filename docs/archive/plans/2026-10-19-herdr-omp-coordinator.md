# Plan: replace Hermes with Oh My Pi as the Herdr coordinator host

Status: Superseded (archived 2026-10-25; never frozen or implemented)
Superseded by: docs/plans/2026-10-20-omp-side-by-side-coordinator.md,
docs/plans/2026-10-20-omp-herdr-dispatch.md and
docs/plans/2026-10-22-omp-herdr-external-control.md. Kept unchanged below as
the historical draft that preceded the delivered OMP process documents.
Surface: t3 (preparation and review); herdr (future human-operated trial).
Authorization: The user explicitly requested "Yes please replace Hermes with Oh my Pi"
on 2026-10-19, following discussion of Sol coordinating inside OMP inside Herdr.
The user then clarified that GPT-6.1 Sol is the only fixed model. Implementers,
reviewers, providers and their settings are selected in each session when needed;
no implementer or reviewer selection is requested for this draft.
Reference: pending
Risk and review: High; changes the coordinator runtime and the frozen trial entry
contract. Two independent critics are required before freeze and final acceptance.
Their providers/models/settings are deliberately unspecified in this draft;
selection occurs in the session that performs each required review, before dispatch.
Any required unverified-family acceptance belongs to that named session roster.
Expected child tasks when executed: two plan critics, one session-selected
implementer, two final critics, before corrections. Sol owns acceptance and commits.

## Outcome

OMP replaces Hermes as the intended host for Sol inside Herdr. Preserve T3 as the
active preparation/review environment and fallback. Deliver an OMP-specific trial
entry point and coordinator instructions. Distinguish documented preparation from
actual Sol connectivity and a completed live Herdr cycle.
Use one shared role policy across T3 and Herdr: only the orchestrator model is fixed;
all worker providers/models/settings are selected for the session when needed.

## Current state

- Existing active process documents remain T3-specific. The two-surface migration
  and its full P01-P09 acceptance have not completed.
- Those documents currently fix Antigravity as implementer and refer to named
  critic pools. The user's latest instruction supersedes those roster assignments
  for the new workflow; their wording needs amendment before routine execution.
- The latest narrowed trial is `2026-10-18-herdr-single-cycle-trial.md`, frozen at
  `ad19c3115f518b8f10d1ab2ef23c04254196886b`. Its handoff is under
  `docs/validation/two-surface-orchestration/2026-10-17/implementation/single-cycle/`.
  It prepares one disposable status-reader task, with no observer prerequisite.
- Its current coordinator instructions require Hermes. They cannot be reused by
  replacing executable names: Hermes-only context/session flags and identity
  repair are not OMP controls.
- Repository baseline: `ff58dea`, root checkout `main`; preserve untracked `.path`.
- Installed OMP reports `18.12.2`. Its configured catalog has no Sol match; the
  user configuration disables `openai-codex` and filters enabled models. A temporary
  catalog-only overlay enabling that provider still returned no Sol entry. No
  provider request, authentication change, or global settings edit was performed.
- This coordinator is outside Herdr. No live session inspection or control is
  authorized from here. Herdr's existing setup record lists `omp` as a known kind;
  current OMP detection and registration remain live-unverified.

## Scope and boundaries

Allowed edits:

- This amendment and its append-only review/execution record.
- Role-selection wording in `docs/process/council.md`, `planning-loop.md`,
  `implementation-loop.md` and `profiles/machine-profile.md`: remove fixed worker
  assignments and provider-pool restrictions, keep Sol as fixed orchestrator model,
  and use explicit session-selected targets in dispatch instructions. Preserve
  the existing sequence, risk-sized review, report schemas, exact critic guard,
  frozen-reference verification and acceptance checks.
- A new `docs/validation/two-surface-orchestration/2026-10-19/omp-coordinator/`
  directory containing README, human instructions, coordinator brief, readiness
  record, and acceptance/review evidence.
- Additive supersession notices in the 2026-10-17 `setup.md`, `pilot.md`,
  `implementation/single-cycle/README.md`, `human-instructions.md`, and
  `coordinator-brief.md`, and `implementation/p01-capture/NEW-CHAT-HANDOFF.md`.

Old plan contracts, reports, captures, manifests, launch bodies, and preparation
JSON remain historical evidence. Notices redirect current readers; old checksums
continue to describe the old snapshots, not the notice-bearing current files.
Do not modify product code/tests, registry, unrelated process rules, installed agents,
credentials, persistent OMP settings, services, or proxy routing. Do not start any
model-backed session, trial, worker pane, or live Herdr command in this amendment.
No replacement model, fabricated identity, or automatic fallback is permitted.

## Replacement contract

1. GPT-6.1 Sol (`gpt-6.1-sol`) is the only fixed model. OMP replaces Hermes as its
   intended Herdr host. The orchestrator's provider/route and reasoning settings
   are established in the execution session; existing high reasoning is a default,
   not another fixed-model requirement. T3 remains active during preparation.
2. Implementers and reviewers have roles, not permanent model/provider assignments.
   The user chooses each role's provider, model and settings in the session when
   that role is needed, before its dispatch. Discover current availability then.
   Record choices and authorized fallbacks in an append-only session record;
   do not freeze named workers into reusable plans or inherit historical choices.
   Reuse a session's authorized choice while it remains applicable; ask only for
   roles actually needed, at their dispatch boundary. No selection is needed to
   draft this amendment. Missing selections at dispatch stop that dispatch, not
   independent drafting or inspection. Selection within this policy is an execution
   record, not a new scope amendment.
3. Preserve the narrowed disposable trial's task, single active implementer,
   independent read-only critics, report binding, two-commit freeze, four fixture
   gates, and sole-Sol acceptance. Apply the existing family-diversity rule against
   the actual selected implementer family, not a hard-coded Google assumption.
   Unknown identities remain unverified; obtain any required acceptance for the
   actual named session pair at selection time. Prior named-pair waivers and
   mappings remain historical and do not authorize a new session roster.
4. Use Herdr for all trial worker dispatch. Derive worker startup/tool/context
   controls from the selected runtime's installed help; existing Pi/agy templates
   are historical examples, not mandatory targets. OMP native task delegation, advisor,
   automatic model switching, and automatic plan-to-implementation transitions
   are outside this trial; explicitly disable supported controls or stop if
   effective settings cannot be established. No second implementer is allowed.
5. Derive OMP flags and context controls from installed help and upstream primary
   documentation. Do not reuse Hermes `--ignore-rules`, `--pass-session-id`,
   `HERMES_CODEX_BASE_URL`, system-prompt session identity, or registration repair.
   OMP context discovery, extensions, MCP, sessions, and native Herdr integration
   need their own stated controls and remaining limits.
6. Human alone starts fresh OMP in genuine Herdr. Verify inherited environment,
   actual owned session/pane, physical checkout, fresh OMP conversation, configured
   exact Sol model, session-selected provider/settings, and available OMP session
   identity. Correlate the
   live coordinator with the owned pane without assuming Hermes's hook protocol.
   Missing identity/detection evidence stops; no improvised repair or installation.
7. Preserve two parallel critic waves, complete uniquely bound reports and actual
   owned-process completion checks. OMP/Herdr idle state alone is not acceptance.
8. Until an exact Sol provider/route is configured and verified, label readiness
   `blocked: Sol provider/model connection unverified`. Do not publish a runnable
   trial launch command with a guessed provider, URL, credential, model alias, or
   expired fixture path. Provide a clearly non-executable launch shape and exact
   prerequisite instead. Authentication/configuration and fresh fixture preparation
   require a later bounded step once the connection is settled.
9. Full migration, P01-P09, observer, restart/cancellation experiments and product
   implementation stay outside this amendment. Successful document checks prove
   preparation only, not model connectivity, Herdr integration or live acceptance.

## Implementation steps

1. When the user is ready to perform the required independent review, select that
   session's critics and settings. Review this complete amendment, resolve blockers,
   freeze it with the prescribed
   two plan-only commits, and push/verify each Skill Lens commit.
2. Select the implementation-session worker when implementation is ready to start.
   That implementer creates the OMP documentation/readiness record and narrowly
   scoped supersession notices, and updates the named shared process documents
   to the role-selection policy above. Include primary-source links, installed
   CLI evidence, identity/context limitations, and an explicit next human step.
3. Sol checks the complete diff, local links, examples and source-backed flags;
   ensure all current entry points clearly redirect and historical evidence is
   preserved. Run the four project gates on the final tree with retained logs.
4. Use the applicable session-selected critics, with fresh review contexts, to
   inspect the full handoff and amendment. Resolve
   confirmed blockers, record verdicts and task terminal/no-pending evidence.
5. Sol accepts documentation scope only, commits, immediately pushes and verifies
   local/tracking/remote equality. Report OMP replacement and the connection blocker.

## Acceptance

- Current Herdr coordinator instructions name OMP and explicitly supersede Hermes.
- No Hermes-specific flags, environment or identity-repair procedure is presented
  as executable OMP guidance. Historical occurrences remain clearly historical.
- Only the orchestrator model is fixed. No Antigravity, Gemini, Pi, MiniMax,
  DeepSeek, or other worker/provider assignment is a reusable default. Select
  providers/models/settings when each role is needed in its session, with the
  actual selected implementer family used for review independence.
- Role separation, review independence, bounded task, read-only original repository
  and four fixture gates are preserved. OMP's own workers cannot silently replace them.
- Sol readiness is honestly blocked; no live-success claim or guessed command.
- Allowed-file diff, valid links, complete independent reviews and unchanged
  product/test/registry files; pre-existing `.path` remains unstaged.
- `pytest --cov=skill_lens`, `mypy`, `ruff check .`, `ruff format --check .` pass.
- Planning freeze and final delivery are pushed with local/tracking/remote checks.

## Review decisions

The user's clarification is applied: worker selection is deliberately deferred to
the session and point of need, and GPT-6.1 Sol is the only fixed model. Removed the
draft's fixed Antigravity assignment and inherited native Pi/Qwen/DeepSeek roster.
Added the shared process documents to scope so the policy is consistent across
T3 and Herdr. No worker was selected, dispatched or treated as having reviewed this
draft. Independent review, freeze and implementation remain future execution steps;
this draft does not waive the review gates or claim migration acceptance.
