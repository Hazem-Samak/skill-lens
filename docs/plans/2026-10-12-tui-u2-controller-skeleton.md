# Plan: U2 worker controller and TUI skeleton

Status: Agreed
Authorization: User on 2026-10-12 instructed start U2 in Synara with GPT 6.1 Sol High coordinating/planning/judging, Antigravity Gemini 3.8 Flash High implementing, OpenCode Muse Spark 1.3 free and Pi/9 Router MiMo V2.6 Flash free reviewing; Sol chooses critic effort by task value. Earlier instruction requires pushing every coordinator commit to GitHub. This authorizes the Synara execution adaptation below and U2 only.
Reference: 4badd02fa48a59ce3971f6c1ed1c8ff47bb0d55e
Risk and review: High: cancellation/publication, internal-error exits and read-only protection. Two fresh independent planning reviews and two fresh final reviews. User explicitly selected the named pair; model-family identity beyond catalog labels remains unverified and no verified diversity claim is made.
Expected child tasks: 5 before corrections: Muse plan review, MiMo plan review, Gemini implementation, Muse final review, MiMo final review. Additional targeted rounds only for affected unresolved findings; escalate after two non-converging rounds.

## Outcome

The optional terminal interface opens a placeholder Home screen, captures a
read-only session in background work, refreshes with `r`, and quits with `q`.
It keeps the last usable capture after errors and returns 0 normally or 3 after
an accepted unexpected fault. Implement the complete internal controller for
future Why/Diff/Compare requests, without adding those screens or Home browsing.

## Current state

- Clean root checkout `main` at d3b26f2596c81e787e7231ecb938d6470c3811cc,
  synchronized with origin. U1 accepted; C1-C5 core and presentation contracts exist.
- Textual 8.2.8 is installed in `.venv`; its `work(thread=True)` supports
  `exit_on_error=False`. Workers use the event loop executor. Thread cancellation
  cannot forcibly stop a filesystem read; return/publication safety needs its
  own event and identity checks, not only Textual cancellation.
- `cli._load_tui_runner()` lazily expects `skill_lens.tui.run(home, cwd) -> int`.
  `_launch_tui()` already converts import/run faults to a plain-English error/3.
  Existing routing/packaging tests exercise a fake runner. `tui/` does not exist.
- `capture_session(generation=, home=, cwd=, cancelled=)` supplies complete owned
  `SessionSnapshot`; `snapshot_why`, `snapshot_diff`, `snapshot_compare` consume it.
  Capture validates supplied home against `paths.home()`. Workers must not mutate
  sandbox globals; the CLI owns setup, tests use temporary HOME through paths.py.
- Authority: FULL_SCREEN_TUI.md sections 7.1, 9.1, 10, Step 2, 21.7 and 22 U2.
  DEVELOPMENT.md, Phase 6 exit record, U1 plan/walkthrough and current source read.
  No engine, registry or frozen capture-contract changes are needed.
- Baseline receipt from this conversation on unchanged tree/environment:
  605 passed, 1 case-insensitive-filesystem skip, 94.67% coverage; strict mypy,
  ruff check and format check passed. Fresh logs: `/tmp/skill-lens-u2-baseline-`
  `pytest.log`, `mypy.log`, `ruff.log`, `format.log` (same prefix for each).
  Coordinator rechecks tree before dispatch.

## Scope and boundaries

Product: new `skill_lens/tui/__init__.py`, `app.py`, `session.py`, and only small
additional TUI modules if the same responsibility requires them and Sol confirms
the boundary. `cli.py` only
if the existing launch boundary needs a concrete integration correction.
Tests: new `tests/test_tui_session.py`, `test_tui_app.py`, `test_tui_read_only.py`,
and focused updates to `tests/test_tui_routing.py` as necessary.
Records: this plan, `docs/TUI_U2_WALKTHROUGH.md`, focused evidence under
`docs/validation/u2/`. Shared process-file migration is excluded: the native
execution instructions below apply only to this explicitly authorized U2 session.

Exclude U3-U9 screens, list/filter/detail widgets, UI polish, dependencies/lock,
core/model/registry/presentation/render changes, snapshot/golden regeneration,
version bump, publishing, real skill-root demos and unrelated cleanup. Gemini
writes product code/tests, never delegates or commits. Sol owns plans, process
documents, verification, acceptance and commits/pushes.

## Synara execution adaptation

For this authorized session, native Synara procedures replace the T3-specific
commands in the loops. Preserve review guard, role separation, allowed paths,
fingerprints, scope/acceptance gates and two-commit freeze. No shared process
contract is edited by this product phase.

Use synara_context/capabilities and thread readback for caller, catalog and
checkout evidence. Dispatch fresh standalone critics with synara_create_threads
(stable requestId, explicit projectId, target/options, environment=local and
runtimeMode=full-access). Roles are in prompts: Synara does not accept T3's
role/interactionMode fields. Retain thread/run/request ids; pin turns with
synara_wait_for_threads, then read complete reports with pagination. Wait
timeouts are progress, not retries. Creator notifications are passive, not a
guaranteed wakeup. Respect the catalog's one-creation-plan-per-active-turn limit:
the observed creation_plan_locked rejection explicitly requires a new user turn
before another batch. Do not use self-messages or role-changing follow-ups to
bypass it. The user subsequently explicitly instructed autonomous implementation
and both final reviews without further permission. For that instruction, reserve
the worker and two dedicated final-review threads, plus the focused scheduling
critic, in one exact four-thread native batch. Dedicated means single-purpose
standalone threads, not automation reuse or reused completed-review contexts.
Their initial turn is a preparation handshake only: no product edits or review.
After this scheduling amendment is independently reviewed and two-commit frozen,
activate the implementer using the new frozen reference. After coordinator diff
inspection and all four passing gates, activate the reserved critics with exact
tree identity, full guard and complementary review briefs. These are fresh final
review contexts: their only preceding message is administrative readiness, with
no planning findings, implementation reasoning or early source inspection.
Use queue-mode synara_send_message for worker activation/corrections and first
activation of reserved critics. Subsequent review rounds still require new
contexts, never reuse a completed review thread. If fresh additional contexts
cannot be created, report the native limit rather than waive review or bypass it.
Carry original human contextMessageIds when delegating a
prior turn. Interrupt/read back terminal states if necessary. Before acceptance,
list/read all owned threads and confirm settled turns and no owned active or
queued work; do not invent T3's hasPendingChildRuns field. Keep exact critic guard,
status/SHA-256 detection and preserve/inspect/stop on any unexpected reviewer edit.

Live exact targets:
- Sol: codex / gpt-6.1-sol, requested reasoningEffort=high.
- Implementer: antigravity / Gemini 3.8 Flash, reasoningEffort=high.
- Muse: opencode / opencode/muse-spark-1.3-contributor-free, options omitted:
  live catalog has no variant values. Do not claim a configured High option.
- MiMo: pi / nine-router/cl/cline-free/mimo-v2.6-flash, thinkingLevel=high:
  races, stale errors and safety proof warrant deeper review.

Critics receive complementary questions: Muse checks architecture, repository
constraints and runtime adaptation; MiMo checks race/error/quit behavior and
test adequacy. This requested pair is accepted operationally without claiming
provider-confirmed family identity. Requested/configured/actual model evidence
is recorded separately. Caller identity comes from synara_context; inspect
synara_read_thread for configured model/options if present. Missing evidence is
unverified, never replaced by catalog defaults. Full access is already authorized.

## Implementation steps

1. Create a small Textual-free `tui/session.py` implementing every transition
   in section 21.7. Use frozen slots ViewRequest, ViewName and ReportValue types;
   controller owns current, counters, pending generation, active requests,
   cache, selected canonical key, failed/closed and worker cancellation events.
   Each capture and report gets its own Event and immutable arguments; workers
   retain their captured snapshot. Allocate monotonically, never reuse ids.
2. Capture publication requires open state, matching pending and returned
   generation. Swap once, clear cache/requests, cancel superseded work, preserve
   existing selected key or first canonical entry/None. Failed newest capture
   keeps previous data. SnapshotChanged exposes its exact retry message without
   setting failed; CaptureCancelled is quiet. Accepted unexpected errors retain
   data, set sticky failed and keep optional traceback details only in memory.
   Reject stale successes AND errors before they affect any state.
3. Implement per-view request/cache identity `(generation, view, arguments)` and
   request id. Selection/agent changes and leaving a view invalidate/cancel
   associated requests. Check current snapshot, view, id and arguments on
   result/error acceptance; only matching results enter cache. Controller
   methods expose usable seams to future screens without creating those screens.
4. Build `SkillLensApp(App[int])` and a placeholder Home screen with `q` quit,
   `r` refresh, loading/ready/retry/error state and an optional in-memory error
   details display. Untrusted error/details strings use markup=False. Initial
   capture and refresh run in Textual thread workers with exit_on_error=False;
   pass explicit validated home/cwd and event.is_set, never widget state.
   Report adapter uses snapshot services and same controller protocol; expose
   adapter methods for headless tests/future screens, no visible report screen.
   Marshal completion via thread-safe Textual messages or call_from_thread;
   all controller/widget updates happen on the UI thread.
5. Quit sets closed, all events, invalidates pending and report requests, cancels
   owned Textual workers, exits 3 if failed else 0. Ignore late callbacks after
   close. Implement `run(home,cwd)->int` for existing lazy CLI adapter. Capture
   unexpected app/launch faults at the existing CLI boundary without terminal
   traceback. Prevent Textual's default unhandled-error renderer from bypassing
   this boundary; inspect installed App._handle_exception, contain relevant UI faults
   and test the actual path. Account for synchronous event-loop/executor teardown
   so `run()` does not wait for an entire controlled scan on quit. Textual 8.2.8
   App.run accepts an explicit loop; use an owned loop and close it after app
   shutdown instead of asyncio.run's default-executor join. Keep mandated
   Textual thread workers and prove the actual synchronous path. Do not promise
   forcible termination of an in-progress file read; document the limitation.
6. Add meaningful deterministic controller tests for refresh 3 before 2, report
   2 before 1, selection/agent changes, leaving/returning, cache separation and
   invalidation, generation mismatch, newest failure with/without old snapshot,
   expected consistency error, silent cancellation, superseded exceptions,
   sticky failure and quit before completion. Assert publication swaps snapshot
   and invalidates cache/requests in one UI-thread transition. Use Event/barriers and explicit
   handoff, no sleep-based ordering. Construct reports/captures from synthetic
   fixtures or reused model factories, not real HOME.
7. Add headless `run_test()` integration using real widgets/workers/messages:
   open/quit, refresh race, report race/invalidation, newest and stale errors,
   prompt controlled-slow-scan quit, callbacks after close, literal markup,
   and exact 0/3. Also invoke CLI `tui --sandbox <tmp fixture>` through the real
   lazy runner with controlled headless launch/autopilot; injecting a fake
   `tui.run` alone is not end-to-end proof. Include synchronous runner prompt
   quit and launch/UI fault proof; release controlled threads in finally blocks.
   Put a hard timeout/watchdog on blocked-quit tests. Cover late completion after
   loop teardown, including call_from_thread RuntimeError if that adapter is used.
   Assert q/r handling while capture is loading as placeholder responsiveness.
   Use asyncio.run in pytest test wrappers; no new pytest async dependency.
   Wrapper loops and the synchronous runner's owned loop are separate objects;
   do not run the synchronous launcher inside an already-running wrapper loop.
8. Add a dedicated recursive AST source guard for section 10. Reject banned
   imports of shutil, subprocess, tempfile, sqlite3, socket, requests and httpx
   (including aliases/submodules), os destructive calls via aliases,
   Path writes/instance methods, positional/keyword write modes on builtin,
   Path and io open, and unresolved modes. Reject rich/render imports, Console
   terminal writes and bare print; include direct stdout/stderr writes and
   known process/network/db imports as appropriate to the stated categories.
   Resolve imported aliases and conservatively reject unsafe instance spelling.
   Guard is a known-source check, not an adversarial sandbox claim.
9. Mutation-test every guard category, alias and write-mode branch using
   temporary source trees outside the checkout fed to the exact same recursive
   source checker. Demonstrate clean control, detected mutation, clean restore;
   test actual package discovery so it cannot silently skip files. Pair with
   before/after synthetic target checks (bytes, file modes, symlink targets)
   across launch, refresh, errors, placeholder navigation and quit. No logging
   or output files in the target. Record mutation inventory/results and limits.
10. Gemini returns implementer report and factual walkthrough/evidence. Sol
    inspects full diff and consumers, runs all four gates, fingerprints the
    reviewed tree and dispatches fresh Muse/MiMo final critics. Reproduce and
    resolve every in-scope blocker; targeted follow-up to affected critics.
    After acceptance, record task/run identities, effort/effective-model
    evidence, elapsed time, tokens if exposed (otherwise unavailable), final
    checks and limitations. Commit allowed files, push and verify remote HEAD.

## Acceptance

- All section 21.7 transitions are implemented/tested independently of Textual;
  headless adapter proves actual workers obey them, not only helper tests.
- CLI reaches real placeholder app with validated sandbox paths; q returns 0,
  accepted unexpected worker/UI/launch faults return 3 without terminal traceback.
  Expected consistency errors/cancellation and stale errors do not set failed.
- Quit publishes closed before cancellation; pending work cannot touch UI/cache;
  controlled synchronous launch returns before blocked work is released.
- Recursive guard rejects every section 10 category, aliases, instance and
  keyword/unresolved modes; mutation proofs fail when the protected rule is
  broken. Target bytes/modes/links unchanged throughout exercised lifecycle.
- No U3 screens, dependency or public output/JSON changes. Existing snapshots
  and goldens unchanged. Strict mypy applies to entire tui package immediately.
- Coordinator directly runs pytest --cov=skill_lens (>=90%), mypy, ruff check .,
  ruff format --check . on final tree. Two independent final verdicts accepted,
  blockers resolved, allowed paths only, all created turns terminal with no
  owned live follow-ups/descendants. Every commit pushed and remote verified.

## Review decisions

Round 1 completed with both reviewer turns settled and 210 tracked/untracked
file fingerprints unchanged (`/tmp/skill-lens-u2-plan-fingerprints.json`).

- Muse scope blocker accepted: remove proposed shared process-file migration;
  this plan alone records the expressly authorized U2 execution procedure.
- Muse roster blocker rejected with current evidence: the user explicitly says
  Sol decides reviewer effort; Synara's live catalog returns Gemini 3.8 Flash
  reasoningEffort low/medium/high and Pi's exact thinkingLevel key/values. The
  old machine profile explicitly describes a T3 build, not this runtime.
  Creation receipts corroborate requested exact critic slugs/settings and
  readback confirms model/provider/main/local. Sol High remains requested:
  thread metadata supplies model but no effort readback. Provider-confirmed
  model use stays unverified; no catalog default is used as execution proof.
- Both critics' suggestions accepted: name all seven forbidden import roots,
  constrain extra modules to coordinator-confirmed scope, attach gate logs,
  assert atomic publication, bound blocked-quit tests, test callbacks after
  loop teardown, and assert placeholder key handling while loading.
- MiMo pass retained for unchanged product design/acceptance. Its executor
  hazard reproduced in installed code, but suggested daemon-thread deviation
  rejected: Textual App.run(loop=...) explicitly supports an owned event loop,
  avoiding asyncio.run executor join while preserving section 21.7 workers.
  Direct synchronous prompt-quit proof remains required. Ordinary Python
  process shutdown may still wait for an uninterruptible read; do not claim
  forcibly stopping a read, as the specification explicitly forbids that claim.
- Fresh targeted Muse round 2: pass, no blockers; confirms prior scope/roster
  blockers resolved against current catalog and canonical user instructions.
  Non-blocking suggestions accepted as clarifications of existing proof:
  name installed App._handle_exception and keep pytest-wrapper and synchronous
  runner loops distinct. Product scope and acceptance remain unchanged.
- Coordinator accepts both planning verdicts. Round-2 fingerprints unchanged;
  all three reviewer turns completed and listing shows no owned active work.
  No product code until both freeze commits/pushes.

## Execution record

Planning round 1: Muse thread agent-8603007c52f5d7b5e9ae754b59a6bf24,
run opencode-turn-022f4c77-d1fa-4dcf-88aa-a7a48cc4b4c1 (changes_required);
MiMo thread agent-b0aa690c6a1c6fa31a1a3076b980a1dc,
run 03fbcea5-d0cc-4a5a-9c10-1a91f193a3cd (pass). Both completed, no pending turns.
Session roster above is explicit user authorization, not a future default.

Native scheduling boundary: round-2 Muse dispatch request
skill-lens-u2-plan-review-r2-muse-20261012 created no thread. Synara returned
creation_plan_locked for the already committed round-1 creation operation
gateway:create:39c6e6bb75056eec336feb2c0d023889 and said a new user turn is
required. At that boundary the next action was the fresh focused Muse review;
no product code or commits existed yet.

Planning round 2: request skill-lens-u2-plan-r2-muse-resume-20261012,
thread agent-ad85d095129c9e80175ac4890a5f30d7,
run opencode-turn-c8635410-81bd-47fd-ac1c-f113ce1e937d (pass). Reviewer-file
fingerprints unchanged (/tmp/skill-lens-u2-plan-r2-fingerprints.json).
Planning launches: 3, one extra targeted Muse follow-up to resolve scope/roster
findings; one rejected creation attempt launched no work. Reviewer turn elapsed:
Muse round 1 approximately 71s, MiMo round 1 approximately 620s, Muse round 2
approximately 18s from returned creation/completion timestamps. Token metrics
unavailable; no cost/savings claim. Configured model/provider identities are
corroborated by native receipts/readback; options are requested and present in
creation targets, with no independent provider-confirmed effort evidence.

Coordinator pre-freeze gates on unchanged product tree: 605 passed, 1 existing
filesystem skip, 94.67% coverage; strict mypy clean over 31 files; ruff check
and format check passed. Logs /tmp/skill-lens-u2-freeze-{pytest,mypy,ruff,format}.log.
Only this dated plan differed from base at the first freeze. The first frozen
product contract is b696b28813b99702b80c1dd18adfb83eeba932da, recorded by
646e352ca0dac3f028691e04f5b3e5d0bceb996c; both were pushed and verified.

## Execution scheduling amendment

Authorization: the user's subsequent explicit instruction to start implementation
and then both independent reviews, continuing without additional permission.
Only preparation/activation timing changes as described above. Preserve named
providers, role independence, no code before freeze, coordinator verification,
guard/fingerprints and independent final acceptance. Product scope, permission
settings, algorithms and acceptance are unchanged.
Risk: Normal operational amendment; one fresh Muse critic reviews scheduling and
context independence before its two-commit freeze. Retain accepted High-risk
product-plan verdicts. The worker and two final critics perform only a readiness
handshake before activation; they do not inspect or edit product sources early.
Expected extra launch: one focused scheduling critic. No product work until the
new frozen reference is recorded and pushed.

Scheduling review: Muse pass, no blockers, thread
agent-535517b777674f295364e032bef0a8f9, run
opencode-turn-8ac6dc0b-d34d-497b-bd04-a1ec538b1b05. Accepted wording suggestions:
explicit four-thread batch and single-purpose standalone context. Rejected the
suggestion to treat the scheduling critic as readiness-only: that critic must
read this amendment; only worker and final-review preparation turns are inert.
Its report incorrectly says no source read: native activity records confirm
read calls, and its preceding message reports amendment inspection. Native
identity receipts supersede its mixed-role EFFECTIVE_MODEL field. Provider-
confirmed use remains unverified. Before/after 209-file fingerprints unchanged.
Baseline gates repeated: 605 passed, 1 existing skip, 94.67%; mypy/ruff/format green.

Batch request skill-lens-u2-autonomous-implementation-review-batch-20261012,
operation gateway:create:b92fe9aa21dd2997062e7f6ec812f40c. Prepared worker:
agent-44c2d346e57e5b479374648afb9ae3ed, initial run
9b042b9d-9c17-4826-afab-6448a0d5f909. Prepared final Muse:
agent-7e8d8d9ed9a16500042a416258338151, initial run
opencode-turn-5a2635cb-2c69-4656-a6a1-246e371bb3e4. Prepared final MiMo:
agent-141af8854ec19adaf1791f93710423f2, initial run
927ad9f6-8a8e-4fed-addd-af0160f6d578. All three initial turns settled with READY,
not completion/acceptance. No product inspection or edits occurred in preparation.
Actual implementation and final review run ids will be recorded on activation.
