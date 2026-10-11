# Plan: C5 Step 0 audit

Status: Agreed
Authorization: User instruction on 2026-10-11 to start C5, with Gemini 3.8 Flash High through Antigravity as implementer and MiniMax Code (mcode) as the only planning council member and independent reviewer. User selected High thinking effort for both reviews.
Reference: 3665e7a38a9b7366c259da61c87f8b0cab656947
Risk and review: High assurance audit of load-bearing captured inputs, identity and read boundaries. The explicit one-reviewer-only instruction overrides the usual two-critic roster for this session. MiniMax independently checks contract coverage and mutation evidence; Sol inspects and verifies. No claim of verified two-critic family diversity.
Expected child tasks: 3 before corrections: planning critic, sole implementer, final critic.

## Outcome

Prove whether C1-C4 satisfy the Step 0 contract before optional TUI installation
begins. Add only needed acceptance tests and a factual walkthrough, with
reproducible evidence that deliberately broken behavior is detected. Complete
C5 only; U1 and later assignments remain separate.

## Current state

- Clean root checkout on `main` at `343e2f1`; T3 binding has no separate worktree.
  C4 is accepted in its dated plan. Preserve all preceding local commits.
- C1-C4 provide byte helpers, injected engine inputs, capture and navigation
  services, immutable outer containers with owned nested report data, and shared
  plain presentation helpers. Capture reads and validates twice; navigation uses
  captured inputs. Live CLI defaults remain available in engines/renderers.
- `FULL_SCREEN_TUI.md` sections 21.1-21.6 and the C5 row of section 22 are the
  audit authority. Existing tests cover most acceptance rows; verify their actual
  assertions rather than relying on names or old acceptance reports.
- Planning review identified two concrete test gaps: reducing the real resolver's
  hybrid/either identity to directory-only, and replacing `agent.disabled_key`
  with the hard-coded shipped key both leave the existing full suite green.
  New named guards for both regressions are required, not optional. These are
  test gaps: the restored product behavior already satisfies the contract.
- Coordinator baseline on the current tree, using `.venv` and temporary HOME:
  561 passed, 1 case-insensitive-filesystem skip, 94.58% coverage; strict mypy
  clean on 31 source files; Ruff lint/format clean. Logs are under
  `/tmp/skill-lens-c5-cv7cl74b/baseline-{0,1,2,3}.log`.
- Live T3 catalog exposes `antigravity/gemini-3.8-flash-high` and
  `mcode/m:minimax:MiniMax-M3.1-Flash-Preview:v:thinking`. Reviewer options:
  `thinkingEffort=high`, `permissionMode=bypassPermissions`; Full access/plan.
  Older council/machine notes deferring mcode are stale and do not override the
  user's explicit roster or live catalog. Do not rewrite shared process docs.

## Scope and boundaries

Allowed implementation edits: relevant acceptance tests in
`tests/test_snapshot_inputs.py`, `tests/test_session_snapshot.py`,
`tests/test_presentation.py`, `tests/test_phase2_gate.py`,
`tests/test_phase3_gate.py`, `tests/test_compare.py`, `tests/test_doctor.py`,
and other existing engine test files only where a section 21.6 gap belongs;
`docs/TUI_STEP0_WALKTHROUGH.md`; one small reproducible mutation harness and
machine-readable result artifact under `docs/validation/c5/` if needed.
Sol owns this plan and append-only execution records.

No persistent production-code changes, new features, UI, dependencies, packaging,
registry edits, CLI changes, snapshots/goldens regeneration, remote push or
publishing. Do not modify source in the active checkout for mutations. Use an
owned disposable copy outside the repo and synthetic HOME/fixtures. Run one
mutation at a time and restore its source before the next. Workers do not
commit, delegate or independently expand scope. A reproduced production defect
or operative contract mismatch must be reported to Sol before affected work
continues; C5 cannot claim completion with a surviving relevant mutation.

## Implementation steps

1. Map every section 21.6 acceptance row to actual tests and source. Record
   delivered files, current API signatures, dependency direction, capture-only
   reads, explicit-input rejection, and navigation/presentation boundaries.
   Read Phase 2/3/4 findings for the relevant engines and preserve public JSON,
   precedence, grouping, hash/parser rules, diff limits and pinned output.
2. Run focused existing tests. Add `test_hybrid_and_either_resolver_identity`
   in `tests/test_phase2_gate.py`: a synthetic skill has differing directory and
   declared names; feed the lookup helper's chosen name into the real resolver
   and also resolve the declared name directly, for shipped hybrid Antigravity
   and a supplied registry definition using `identity_source="either"`.
   Assert the selected canonical installation and meaningful resolution state,
   using `mock_home` isolation. Add `test_disabled_overrides_respects_configured_key`
   in `tests/test_snapshot_inputs.py`: replace an agent's configured key with a
   distinct key, include conflicting shipped-key data, and assert only the
   configured-key entries are disabled. Add other guards only for demonstrated
   section 21.6 gaps. Use controlled hooks rather than sleep races and construct
   expected reports before banning reads.
3. Mutation-test the five required categories from section 21.6: empty-input
   handling, the captured diff branch, identity translation, capture validation,
   and the no-live-read boundary. Choose concrete branches and named protecting
   tests; include outer/inner diff selection, helper/service identity where
   relevant, and both captured-byte and second-pass validation. Ensure a
   regression is behaviorally exercised, not killed by syntax/import errors.
   Mutate every newly added guard as required by the project profile.
   In particular mutate `_identity_names` to directory-only and the settings
   decoder to `parsed.get("skillOverrides")`; the two new named tests above
   must fail respectively. Existing baseline selectors include
   `test_resolver_explicit_empty_overrides_keeps_enabled_without_settings_read`,
   `test_diff_falsey_mapping_exercises_captured_branch_without_live_reads`,
   `test_change_during_capture_is_rejected`, and
   `test_navigation_has_no_filesystem_fallback`.
4. Retain a compact reproducible harness/results with mutation IDs, exact
   source change, protecting test selector, clean control pass, mutant failure
   assertion/trace, restoration pass, and observed survivors. Use the repo's
   existing interpreter/dependencies without installing anything. Every child
   command must use the disposable copy as CWD and put it first on the import
   path. Record resolved `skill_lens.__file__` and test-module provenance from
   the executing test process; require both to belong to the disposable copy
   (resolve `/tmp` aliases before comparing). Exclude copied bytecode and clear
   `__pycache__` before each run so stale cached code cannot mask a mutation.
   Wrong import provenance is an invalid run, never a survivor or kill. Keep
   transient logs and caches outside the repo. Do not build a general framework.
   Verify clean-copy collection matches the active tree's current collection
   after new tests are added; do not mistake an incomplete copy for a passing
   control. Record focused selectors/counts for each run.
5. Write the factual Step 0 walkthrough: every section 21.6 row mapped to actual
   test names (including rows realized by several engine tests), delivered
   files/APIs/read boundaries, mutation outcomes, current four gates, snapshot
   parity, known skip/limitations, and pending independent-review status.
   Distinguish observed results from historical records. Explain that capture
   validation is not a filesystem transaction and nested report objects are
   owned, not recursively immutable. Do not claim later UI acceptance.
6. Sol inspects all edits and reproduces the retained mutation campaign, runs
   the four gates on the final tree, and supplies evidence to the sole MiniMax
   reviewer. Resolve confirmed test/evidence gaps in one batched correction.
   Mark Step 0 complete only after independent review and final acceptance.

## Acceptance

- All section 21.6 requirements have source-backed, meaningful test evidence.
  Directory/frontmatter/either identity tests exercise the real consumer;
  the new hybrid/either test proves both helper-selected and declared-name
  resolution reach the selected installation, and the new distinct settings-key
  test proves the configured key governs disabling despite conflicting data;
  explicitly supplied emptiness never triggers live reads; frozen inputs reject
  omitted required arguments; every browsing service remains captured-only.
- Every required and newly added guard mutation is caught by its named test,
  with passing controls before and after restoration. Surviving in-scope
  mutations block completion; syntax errors, missing dependencies and wrong
  import provenance do not count as kills. Record any limitations honestly.
- Synthetic targets remain unchanged in bytes/modes/symlink targets. No tests
  inspect real skills, settings or locks; shared presentation has no Rich,
  Textual or filesystem dependency. Existing JSON and all 17 snapshots remain
  unchanged; no golden/snapshot files are edited.
- Final coordinator gates: `pytest --cov=skill_lens` (90% threshold), `mypy`,
  `ruff check .`, `ruff format --check .`, using `.venv` and temporary HOME.
  Record current totals/coverage and explain skips rather than copying history.
- Walkthrough names concrete files/APIs and the capture/navigation read split,
  with reproducible mutation outcomes and limitations. Independent review is
  complete, fingerprints unchanged, all in-scope blockers resolved, only
  allowed paths changed, and all tasks terminal with no pending child runs.
- Sol records task/model/configuration evidence and execution receipt, commits
  only accepted files, and stops at C5.

## Review decisions

- MiniMax round 1: `changes_required`. Before/after fingerprints match; task
  completed with no pending child runs. T3 receipts confirm selected model,
  High thinking, Full access/plan; critic runtime confirmed the thinking model,
  but did not independently confirm effort/permission settings.
- Accepted B1/B2: make the hybrid/either real-consumer and distinct settings-key
  guards required. The proposed mutations change correct product behavior while
  evading old tests; tests-only remediation stays inside C5 authorization.
- Accepted B3: replace conditional gap wording with named tests/mutations and
  explicit acceptance assertions. Acceptance describes the required final state,
  not a claim that the current suite already satisfies it.
- Accepted B4: make scratch CWD, explicit import path, executing-process package
  and test provenance, normalized path comparison and bytecode cleanup mandatory.
- Accepted suggestion: the walkthrough must enumerate every section 21.6 row;
  reuse existing strong tests rather than adding duplicate guards.
- MiniMax round 2: `pass`, no blockers; confirmed B1-B4 resolved. Before/after
  fingerprints match; task completed with no pending child runs. Coordinator
  receipts confirm round 2 High/bypassPermissions and Full access/plan; the
  critic reported provider-side effort/permission confirmation as unverified.
- Coordinator reproduction: both mutants pass all 561 old tests (1 skipped)
  despite direct probes showing wrong resolver/decoder behavior; clean/restored
  copies pass and return correct results. Evidence is in the temporary baseline
  directory above. An initial incomplete copy and `/tmp` alias comparison were
  corrected; those diagnostic attempts are not mutation acceptance evidence.
- Accepted round 2 suggestions as clarifications: verify complete clean-copy
  test collection, require provenance from the actual test process, and enumerate
  every acceptance row using realized test names. No contract scope expanded.


## Execution and acceptance record — 2026-10-11

This appendix records execution evidence and the coordinator's acceptance. It
adds no operative amendment to the frozen contract above.

- **Decision:** Sol accepts C5. MiniMax's final independent verdict was `pass`
  with no blockers. Sol inspected the full diff and actual files, independently
  reproduced the campaign and runner guard faults, and evaluated the review;
  the review was evidence for the decision, not an automatic approval.
- **Authority:** User authorized C5 and the named sole-reviewer roster. The
  two-commit freeze is `3665e7a38a9b7366c259da61c87f8b0cab656947` followed by
  reference-only commit `6030c3dea99fbb97738378c16a669787dcc2b453`. No later
  contract amendment was made. The user's clarification retains Sol as final
  judge and orchestrator, with evidence-based debate when reviewers disagree.
- **Roster and provenance:** Sol/Codex `gpt-6.1-sol`, reasoning High;
  Antigravity `gemini-3.8-flash-high` is the sole implementer;
  mcode `m:minimax:MiniMax-M3.1-Flash-Preview:v:thinking`, `thinkingEffort=high`,
  `permissionMode=bypassPermissions` is the only planning/final reviewer.
  T3 dispatch/configuration receipts confirm targets and options, Full access
  for every task, plan interaction for critics and default for implementers.
  Child reports corroborate model identities; provider-side effort/permission
  confirmation remains unverified. Gemini's last report labelled runtime mode
  `default`; the T3 configuration receipt confirms `full-access` and default
  **interaction** mode. The receipt, not that mislabeled field, records the mode.
- **Delivered:** Two tests close the hybrid/either real-resolver and distinct
  settings-key gaps. The walkthrough maps all 16 acceptance rows to actual tests,
  documents files/APIs/read boundaries, and records limitations. The single
  standalone campaign script and JSON artifact reproduce 12 specified faults.
  No persistent production, CLI, registry, dependency, UI, golden or snapshot
  change occurred. All 17 snapshot bytes and documented hashes match `6030c3d`.
- **Corrections judged by Sol:** Both planning gaps were independently reproduced
  before acceptance. The first runner could accept invalid runs; a later version
  missed selector/outcome consistency and rewrote the retained artifact despite
  external output. Sol reproduced those failures and Gemini corrected them in
  two batches. The initial walkthrough's invented snapshot names and incorrect
  source descriptions/signature were corrected against actual files.
- **Coordinator proof:** All 12 mutants fail through the expected named behavior;
  all 12 controls and restorations pass, with source bytes restored and loaded
  package/test-module provenance in the disposable copy. Collection parity is
  564 items. Retained artifact and coordinator rerun match on inspected hashes,
  selectors and outcomes: 12 caught, zero survivors, zero invalids. External
  output left checkout hashes/status unchanged. Fifteen classifier scenarios
  pass; deliberately breaking seven rejection/survivor outcomes makes the
  protecting self-tests fail, then all pass restored.
- **Gates:** Coordinator verified 563 passed, one expected case-insensitive
  filesystem skip, 94.58% coverage; strict mypy clean over 31 source files;
  Ruff lint and format clean (93 files). Current logs, campaign rerun and guard
  fault evidence reside under `/tmp/skill-lens-c5-cv7cl74b/`. These are temporary
  session evidence; the committed harness/artifact/walkthrough preserve the
  reproducible audit, not a promise that temporary logs remain available.
- **Reviewer protection:** Before/after status and SHA-256 fingerprints match
  for both planning rounds and final review. All six tasks are `completed` with
  `hasPendingChildRuns=false`. No separate worktree was created or needs cleanup.
- **Optional review suggestions:** Defer disabling root collection's ignored
  pytest/bytecode caches: those are development artifacts, no skill target or
  tracked file is changed; critics were instructed not to run the harness in
  the active checkout. Defer replacing MUT-06's product-invariant failure marker
  with a test-owned marker: its actual named test call genuinely fails on the
  behavioral regression, so current proof is valid. Defer splitting hybrid and
  either tests: controls verify both consumers and the shared mutated branch is
  caught; independently killing each policy is not a frozen acceptance condition.
  These are follow-up suggestions, not unresolved C5 blockers.
- **Execution receipt:** Expected 3 launches; actual 6. Extra launches: one focused
  planning correction review and two batched implementer evidence corrections.
  First dispatch 10:08:29 UTC; final review completed 11:14:57 UTC: approximately
  1 hour 6 minutes, including coordinator work and turn handoffs. Final review
  took approximately 5 minutes. Token/cost metrics are unavailable; no savings
  claim is made. C5 is complete; U1 has not started.

### Task ledger

- Planning review round 1: task `node:delegated-task:command%3Amcp%3Aba3341d2-357d-46da-87ed-2eba81c974e7%3Adelegate-task%3Ac5-20261011-plan-mcode-r1`; run `run:thread:thread%3Adelegated-task%3Acommand%253Amcp%253Aba3341d2-357d-46da-87ed-2eba81c974e7%253Adelegate-task%253Ac5-20261011-plan-mcode-r1:ordinal:1`; `completed`, `hasPendingChildRuns=false`.

- Planning corrections round 2: task `node:delegated-task:command%3Amcp%3Aba3341d2-357d-46da-87ed-2eba81c974e7%3Adelegate-task%3Ac5-20261011-plan-mcode-r2`; run `run:thread:thread%3Adelegated-task%3Acommand%253Amcp%253Aba3341d2-357d-46da-87ed-2eba81c974e7%253Adelegate-task%253Ac5-20261011-plan-mcode-r2:ordinal:1`; `completed`, `hasPendingChildRuns=false`.

- C5 implementation: task `node:delegated-task:command%3Amcp%3Aba3341d2-357d-46da-87ed-2eba81c974e7%3Adelegate-task%3Ac5-20261011-agy-implementation-r1`; run `run:thread:thread%3Adelegated-task%3Acommand%253Amcp%253Aba3341d2-357d-46da-87ed-2eba81c974e7%253Adelegate-task%253Ac5-20261011-agy-implementation-r1:ordinal:1`; `completed`, `hasPendingChildRuns=false`.

- Evidence corrections round 1: task `node:delegated-task:command%3Amcp%3Aba3341d2-357d-46da-87ed-2eba81c974e7%3Adelegate-task%3Ac5-20261011-agy-evidence-corrections-r1`; run `run:thread:thread%3Adelegated-task%3Acommand%253Amcp%253Aba3341d2-357d-46da-87ed-2eba81c974e7%253Adelegate-task%253Ac5-20261011-agy-evidence-corrections-r1:ordinal:1`; `completed`, `hasPendingChildRuns=false`.

- Evidence corrections round 2: task `node:delegated-task:command%3Amcp%3Aba3341d2-357d-46da-87ed-2eba81c974e7%3Adelegate-task%3Ac5-20261011-agy-evidence-corrections-r2`; run `run:thread:thread%3Adelegated-task%3Acommand%253Amcp%253Aba3341d2-357d-46da-87ed-2eba81c974e7%253Adelegate-task%253Ac5-20261011-agy-evidence-corrections-r2:ordinal:1`; `completed`, `hasPendingChildRuns=false`.

- Final independent review: task `node:delegated-task:command%3Amcp%3Aba3341d2-357d-46da-87ed-2eba81c974e7%3Adelegate-task%3Ac5-20261011-final-mcode-r1`; run `run:thread:thread%3Adelegated-task%3Acommand%253Amcp%253Aba3341d2-357d-46da-87ed-2eba81c974e7%253Adelegate-task%253Ac5-20261011-final-mcode-r1:ordinal:1`; `completed`, `hasPendingChildRuns=false`.
