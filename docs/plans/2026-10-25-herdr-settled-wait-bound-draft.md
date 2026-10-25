# Plan — diagnose Herdr premature prompt-wait completion

Status: Agreed — revision 2; owner authorized freeze and Stage 1 preparation
Authorization: Owner, 2026-10-25: “Approved: freeze the revised diagnosis-first draft (2026-10-25-herdr-settled-wait-bound-draft) per the repo's two-commit procedure, and start stage 1 (prepare and verify the diagnostic observer).” This authorizes A0 isolated observer preparation, build/offline verification and required final review. Stage 2/A1 live diagnosis remains separately unauthorized until the owner approves its exact worker, session, prompts and limits. B fixes, deployment and upstream publication remain unauthorized. Select the named implementer before instrumentation edits.
Reference: 6cff4c73957431a90c5c0da5e1cc81d86e5d749a
Surface: isolated Herdr investigation; Skill Lens documentation only
Risk and review: High — timing-sensitive completion and compatibility behavior. Two fresh independent planning critics; two fresh final critics for any later instrumentation or fix implementation.
Roster: Sol coordinates and owns verification. Owner selected a fresh River/OMP `deepseek-ai/DeepSeek-V4.1-Flash-1017` session with `--thinking max` as the Stage 1 edit-only implementer. Planning and fresh final critics use the named pair: River/OMP `deepseek-ai/DeepSeek-V4.1-Flash-1017` with `--thinking max`, and Qoder CLI `Qwen3.8-Flash` with `--reasoning-effort max`; final sessions must not reuse the author session or its hidden context. Verify configured model/settings and disclose unverified upstream identity/effort; no substitution. The later live diagnostic-worker identity requires separate selection/approval.
Expected child tasks: this revision: two planning critics. Later, only after separate approval: one edit-only instrumentation implementer and two fresh final critics; bounded diagnostic workers as specified below. Any supported fix requires a concrete amendment, separately authorized implementer and two fresh final critics. Sol owns verification; no child runs gates or commits.

## 1. Outcome and approval stages

First identify the **actual successful return branch and the state it checked** when `agent prompt --wait` returns before the corresponding native full-TUI response finishes. Preserve correct fast completions, intentional Blocked/custom-until returns, timeouts and lifecycle handling.

This is not approval of a sequence-bound fix. Diagnostic success can be a supported mechanism, a contradiction of candidate 1, or an honest inconclusive result. Only the first of those that also supports a specific consumer-only correction may open fix planning; none automatically opens implementation.

| Stage | Permission and exit |
| --- | --- |
| Now | Owner approved the two-commit freeze and A0/Stage 1 observer preparation. No A1/Stage 2 live launch or B fix is authorized. |
| A0 — diagnostic preparation | Owner must approve/freeze the instrumentation contract before code/build work. No failure reproduction is required to freeze a diagnostic-only contract. Complete observer rehearsal and its independent final review before requesting live permission. |
| A1 — bounded live diagnosis | Separate owner approval must name the isolated root/session, exact instrumentation/build/runtime hashes, diagnostic worker/model/mode, harmless prompt, bounds and cleanup. No installed/everyday Herdr changes. |
| A2 — classify and stop | Deliver the diagnosis or inconclusive/contradictory evidence. Ask the owner to review it. No automatic fix. |
| B — conditional fix | Only if A establishes a mechanism and supports an in-scope correction: draft the exact correction, obtain independent review and the owner's explicit authorization/new freeze. Otherwise this phase remains closed. |

This removes the old circular requirement to reproduce before obtaining permission to run the diagnostic. The [earlier frozen capture design](2026-10-22-herdr-full-tui-capture.md) supplies observation/privacy principles, not an authorization to reuse its old sessions, models or one-run allowance for this new experiment.

## 2. Evidence: facts, differences and unknowns

Sources: [first review/adjudication](../validation/2026-10-25/waiter-plan-review/README.md), [original submitted draft](../validation/2026-10-25/waiter-plan-review/submitted-draft.md), [historical incident](../validation/omp-coordinator/2026-10-20/herdr-dispatch.md), [raw trace](../validation/overnight/2026-10-24/trace/capture.jsonl), [trace build](../validation/overnight/2026-10-24/trace/build.json).

- The historical wait returned idle about **6.909 s early**, with API state-change and completion sequence 18; a later read saw Working19. The missing historical producer/gate records cannot be reconstructed by a new run.
- The startup trace recorded selection Idle publish at `21:29:55.071Z`, Working publish at `.072Z`, Idle send at `.183Z`, Idle reducer acceptance at `.290Z`, and Working at `.402Z`. Native completion followed at `21:30:03.430Z`. This turn used OpenCode's startup `--prompt`, not Herdr's prompt waiter.
- That trace's logger printed the **old** state sequence before outer publication. Raw rows 421–433 support post-mutation API **Idle19 → Working20**, not the logged old18/old19. The startup idle had `completion_seq=null`; the historical early response had completion18. Their cause is not established to be the same.
- In pinned `src/api/wait.rs:305-306,428-483`, the settled wait disables transient-status acceptance: replay wakes a current-state probe rather than directly accepting the old Idle event. The earlier report's claim that replay itself proves the cause is withdrawn.
- The activity gate can return a current snapshot with a replayed Working status substituted (`476-479`). Its state sequence need not belong to that Working event; blindly using it as a floor can exclude a fast turn's already-real completion.
- Activity may be considered observed without running the gate (`211-212,244-253`); the immediate success at `291-293` and released-agent path at `403-410` bypass the proposed settled-construction change. None is diagnosed as the historical cause yet.
- Four traced waiter runs returned after native completion (+0.159–0.197 s). Those are reference samples, not a failure reproduction or same-environment performance controls.

Use four distinct fields in analysis: hook-report `seq`, EventHub replay sequence, API `state_change_seq`, and API `completion_seq`. Do not compare different sequence domains or invent missing IDs. Three private-helper calls exist in `wait.rs`: standalone wait154, activity266 and settled295. Output/event waits are separate interfaces; no other correction is assumed necessary.

## 3. Hypotheses, not decisions

1. Original candidate 1: a settled-wait bound might reject an incorrectly eligible state **if** diagnosis shows that exact predicate caused the premature success and a trustworthy sequence carrier exists. It does not distinguish every false completion after Working.
2. Qwen's uniform prompt-response bound is unproved: it can precede a false idle and does not automatically cover an earlier return branch.
3. DeepSeek's fresh Working probe or extended outcome carrier is unproved: a Working-only probe may miss fast completed turns; a carrier needs precise semantics and scope review.
4. Gate-skipped/immediate-return, post-working false completion, and competing/late reporter hypotheses remain alternatives to test against branch evidence—not replacement root-cause claims.

Reporter suppression and server suppression remain **out of implementation scope**. The exact previously proposed rules were not justified for the measured pre-working ordering; that is not proof that every producer/server design is impossible. Neither failed reproduction nor reviewer preference authorizes reopening them.

## 4. Isolation, source and allowed changes

Use a newly owned execution root for A; never modify the preserved snapshots or reuse a review worker as the diagnostic worker. Synthetic HOME, XDG config/state/cache/runtime, Cargo/Rustup/target and temp paths stay inside that root. Use an explicitly named isolated Herdr session/socket and returned pane IDs. Record absence/ownership before creation; never control the everyday server, installed binary/plugins, local footer override, unrelated panes, services or credentials. No upstream traffic except explicitly authorized existing model-provider use/dependency fetches; no upstream publication, main merge, tag or release.

### Reproducible source stack

- Herdr v0.9.5 commit `2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01`.
- [Source manifest/archive](../validation/omp-coordinator/2026-10-22-herdr-investigation/source/source-files-manifest.json): archive SHA-256 `5c745bf712aee3320ed88a665c39a9143cbd6b7ce4376e0ae0f0c07988576c13`; verify all 16 selected snapshot hashes and record full-tree fingerprints.
- Match the trace's baseline stack: accepted Mini patch SHA-256 `f22d2d7edf26dd8e308394de143b015b37cf58f17148a45ca3c12889b8c6efe8`; accepted OpenCode214 footer patch `e6e649ec3e6e07b2a52d1c40c52c73de88d2763c759c55ca2a4f54f9e60fdf95`.
- Old observation patch SHA-256 `dad01f3ffdc9a713195715074366ff22eb7095fa1881472d40d4fc917001ae75` is a starting reference, **not sufficient instrumentation**. Preserve it; record a new, separately reviewed observation patch/hash. Old diagnostic binary `27b933577f5f1f801269b3506f71dd52e164d4ddf2925c8199ecd0c90503b842` is provenance, not an expected reproducible digest for the changed observer.
- Rust1.96.1 with rustfmt/clippy, Zig0.16.0, Bun1.3.14, Cargo.lock unchanged. Record verified tool archives, full versions for just/cargo-nextest/OpenCode, OS/architecture, commands, environment allowlist and every built binary/loaded reporter hash before live authorization. The two Mini/footer patches are parity controls, not claimed full-TUI causes.

### A: diagnostic-only allowlist

Observation-only records may be added in `src/api/wait.rs`, `src/app/api/panes.rs`, `src/terminal/state.rs`, `src/app/actions.rs`, the copied `src/integration/assets/opencode/herdr-tui-session.js`, and an isolated logging helper/module registration. These are permission to observe, **not** to alter reporter send order/content/retries, state selection, reducer acceptance, completion assignment or server hook-authority behavior.

Any scheduling perturbation must be a separately recorded **waiter-side test-only barrier** in `src/api/wait.rs`, enabled only for the named diagnostic request in the isolated root. It may pause the consumer at a named boundary for at most500 ms; it cannot manufacture/report states, reset sequences, alter the predicate, change responses, delay the producer send path or pretend native completion occurred. Keep identical scheduling controls in paired comparisons. No producer/reducer timing hooks or transport rewrites are authorized by this plan. If this scope cannot expose the race, stop and report the missing permission rather than widen it.

### B: possible future correction boundary

Only `src/api/wait.rs` and meaningful Herdr tests may be proposed initially. Private carrier/helper changes within that file are not pre-approved; the amendment must specify them and all affected consumers. A needed schema, producer, server-state-machine, manifest or other behavior change closes B under this contract and requires separate owner-approved scope. No Python product, dependency, CI, snapshot or golden changes in Skill Lens; documentation evidence only here.

## 5. A0 — prepare a truthful observer before live work

Sol first records the concrete authorization, ownership and model roster. An edit-only implementer prepares instrumentation; Sol builds/rehearses it, runs gates and obtains two fresh read-only final reviews. Do not launch a live worker until the observer contract is demonstrated.

Correlate each target request through these boundaries:

| Boundary | Required facts |
| --- | --- |
| Reporter | Selected session/generation, native event/execution/message IDs when available, selection versus execution reason, prior/next status, source/PID/code hash, actual request/report sequence, send and interpreted response metadata. A transport delivery flag is not reducer acceptance. |
| Server/reducer/publication | Incoming request/source/session, accept/ignore reason, prior/new effective authority/state, mutation, **post-assignment** state/completion sequences and emitted event/hub sequence. Observe every source affecting the owned target pane. |
| Prompt and activity decision | `before_prompt`, prompted snapshot and their status/identity/state/completion sequences; `prompt_started_working`, `prompt_activity_observed`, captured EventHub baseline, gate skip/run reason, filter/floor and actual outcome. |
| Every waiter success/error | Exact branch: initial match, current probe, transient match, release/final-status, deadline probe, identity/disappearance, timeout or connection stop. Record both the matched event's actual fields and the unmodified current snapshot, then the returned snapshot and applied predicate/floor. Never label a substituted status's sequence as the event's sequence. |
| Native completion | Unique harmless request token, actual session and execution identity if exposed, full matching assistant response, terminal finish/outcome and timestamps independent of Herdr idle. Record descendants/tool events and clock provenance. |

Use UTC wall time and process-local monotonic time; monotonic values from different processes are not directly comparable. Record same-host clock correlation and an uncertainty interval. A return/native interval overlapping uncertainty is **indeterminate**, not counted as early or safely late. An absent execution ID stays unavailable; if the single-turn/session/token and native metadata cannot unambiguously correlate the response, the run is incomplete.

Proposed capture limits, subject to owner approval:16KiB per allowlisted record,16MiB per process per run,64MiB total per run; no silent truncation/rotation. On overflow, missing boundary, decode error or clock ambiguity, record an independent bounded failure marker, preserve existing bytes, stop the run and classify it incomplete. Do not change the worker's behavior to make the log fit. Capture no credentials/environment dumps, unrelated transcripts or prompt bodies beyond the approved harmless brief; quarantine and sanitize any suspected secret before repo delivery.

Offline rehearsal must exercise observer branches using the existing Herdr harness and show source/runtime behavior equivalence with logging off versus on. Manufactured fixture events prove observer coverage only, **not** reproduction of the live failure. Record missing fields truthfully; no inferred/synthetic execution IDs. A waiter-side barrier is a separate diagnostic patch, absent from the observer-only baseline.

## 6. A1 — bounded diagnostic matrix, not failure fishing

Live authorization must select one exact available full-TUI OpenCode model/effort/read-only mode, runtime/backend arrangement and approved harmless, no-tool prompt. Selection is deliberately pending here; neither critic is automatically the live worker. No paid-model switch, fallback, resume or permanent settings change. If the required pipeline is unavailable, stop before launch.

Proposed immutable run contract for later approval:

- At most **9 diagnostic attempts**: three scenario groups, at most3 attempts each. At most **3 fresh unperturbed healthy controls** in addition:12 attempted runs. Each run uses a fresh isolated native session and one measured prompt; Group3 alone may have one additional approved active-turn seed prompt per run, so the absolute cap is **15 prompts**, including seeds. Every failed startup/submission consumes its run slot; a failed seed consumes that run, not a free retry. Inspect uncertain delivery before any next launch, never resend blindly.
- Bounds per attempt: startup30s, `agent prompt --wait` timeout120s, concurrent observation180s from submission. One live matrix deadline3600s from its first startup; all per-run bounds remain in force. No automatic extension or replacing failed attempts outside these limits.
- Freeze the scenario order, prompt, barrier location/duration and run ledger before the first submission. Do not tune after seeing a result. If offline rehearsal cannot establish a safe consumer-only scheduling recipe, do not launch; return that prerequisite instead.
- Group1: ready/initially Idle, observe whether selection-derived Idle precedes activity and whether **Herdr's actual prompt waiter** returns. Startup `--prompt` ordering alone cannot satisfy this group.
- Group2: target a naturally observed completion-bearing false-idle shape, distinguishing post-Working/Blocked Idle before native completion from Unknown-to-Idle. Do not fake prior work or accepted frames. If the shape does not occur in3 runs, record non-reproduction.
- Group3: already-working/gate-skipped or prompt-response-already-active path. If needed, submit the one approved harmless seed prompt on the new owned worker, observe its real Working state, then send the measured continuation once. Both prompts/turns must be approved in the live brief and correlated separately. Existing documented active-turn semantics may allow completion of the seed turn to satisfy the continuation's wait; do not misclassify that as premature completion of the new turn. Without trustworthy identity or an approved setup, mark this group unavailable, not a defect. No existing user worker is reused.
- Controls: ordinary successful idle/done completion without the timing barrier, same model/environment/observer, three runs. Record latency and bounds, not just success.

For a suspected early return, continue observing the **same** native turn only within its original180s window, save the full native completion and do not resend. Stop on approval UI, unexpected tools/descendants, identity change, secret exposure or evidence overflow; do not answer prompts or expand permissions. A timeout is not evidence the child stopped: preserve evidence, cancel/stop only owned processes per approved cleanup, confirm terminal/no descendants and remove only owned panes/session. Preserve everyday focus/layout and unrelated files.

## 7. A2 — diagnosis gate and honest stop rule

An evidence-complete failure requires all of:

1. Real `agent prompt --wait` returns normal idle/done success, not a Blocked/custom-until/lifecycle outcome whose earlier return is allowed by the existing contract.
2. Native correlation proves the applicable turn was unfinished at return, outside the measured clock-uncertainty interval.
3. The successful branch, all inputs to its predicate, gate path, source/session authority and distinct sequence domains are captured end-to-end. An idle/working ordering or a small sequence number alone is insufficient.
4. Source analysis plus the run explains why the observed branch permitted the failure and distinguishes the startup null-completion shape from the historical completion-bearing shape.

At least **2 of the3 predeclared attempts in one group** must show the same evidence-complete failing mechanism before this plan can support a correction proposal. A single complete incident is valuable evidence but insufficient to open B here. New experiments beyond the matrix require new approval.

Classify once after the bounded matrix:

- **Supported consumer mechanism:** at least the repeated complete failures above, with an identified in-scope predicate/branch and a falsifiable correction hypothesis. This opens **amendment drafting only**, not B implementation.
- **Failure measured, different mechanism:** preserve it, explicitly reject/withdraw candidate1 if its predicate was not causal or its floor cannot exclude the failing state. Stop; propose a new plan only within separately approved scope.
- **Inconclusive/non-reproduction:** no repeated complete failure, missing correlation/boundary, unavailable scenario, all waiter runs healthy, exhausted bounds or observer perturbation dominating the result. Report exactly what ran, what failed to reproduce and what permission/evidence is missing. No fix or green claim.

Do not force the original pre-working theory, silently weaken the acceptance threshold, treat an alternative bound as proven, or broaden to reporter/server suppression. Diagnostic completion is delivery of evidence and cleanup, not a repair or whole-loop smoke acceptance.

## 8. B — conditional correction and proof, still unauthorized

If diagnosis supports a consumer-only correction, return a concrete amendment naming the actual branch, precise carrier/floor semantics, affected return paths and why it rejects the measured failure without rejecting real completion. If a sequence is used, establish its real source; a transient gate result's sequence is not presumed valid. Define the no-gate/already-working and no-state-consumed cases explicitly, with evidence rather than automatic fallback to `None`.

That amendment needs its own two-critic planning review and the owner's explicit agreement/freeze before implementation. If the supported correction cannot fit `wait.rs` plus tests, seek separate scope approval; do not extend this allowlist implicitly. Critics' alternative bounds/probes/carriers remain hypotheses until then.

The minimum future behavior matrix exercises the real composed waiter, not just `agent_wait_matches`:

- Measured failure branch: failing-before/passing-after using unchanged real report pipeline and the same approved timing control.
- Current Working plus a replayed old Idle: no transient-idle success.
- Fast Working→Idle before the activity probe: real completion still succeeds; no newer-than-completion floor deadlock.
- Already-working/gate-skipped and prompt-response-already-active submission; respect documented active-turn semantics.
- Immediate Blocked/default wait and explicit `--until` status: preserve intentional early success where contracted.
- Genuine idle/done completion, deadline final probe, timeout/stalled error, release/final-status, identity change/disappearance and connection stop: preserve existing success/error distinctions. Add meaningful consumer tests where existing coverage is insufficient, not one test per private line.
- Standalone `agent wait` immediate match and unrelated output/event wait behavior stay unchanged; test affected shared semantics if the helper changes.

Future live proof must repeat the diagnosed scenario at least3 times post-fix with zero premature successes, plus3 paired fresh healthy controls pre/post in the same environment. Timing controls and observation patch are identical; the permanent correction patch contains neither. Predeclare an upper completion-to-return budget of1.0s plus measured timing uncertainty for each ordinary successful idle/done control, with no minimum latency. If baseline controls cannot meet that proposed budget, stop and return the measured mismatch for owner approval, do not widen it silently. Record every run, counts and worst latency; a bounded pass is not a universal 'never' guarantee.

Prove consumer-only scope by clean baseline-versus-fixed full-tree hashes and an explicit source-diff allowlist. Compare normalized lifecycle source/session/order/payload meaning, not exact text-delta counts or event-kind-for-event-kind stream identity. A changed producer decision, server acceptance or permanent observer/hook in the correction fails scope even if tests pass.

## 9. Gates, evidence and delivery

Before any later live authorization, pin tools and run the appropriate clean-baseline and instrumented-source checks in the synthetic root. Herdr source contracts: `rust-toolchain.toml`, `justfile:32-52,121-129`, `.github/workflows/ci.yml:13,94-96,171-181`:

```text
cargo build --locked -p herdr --bin herdr
cargo fmt --check
cargo clippy --all-targets --locked -- -D warnings
just ci-tests 'not binary(live_handoff)'
just docs-contract-test
```

This is the macOS CI filter, not a claim about Linux/Windows/release qualification. Record focused waiter/observer checks as additional evidence; do not suppress baseline failures or remove a failing gate. Any missing tool or failing dependency/gate blocks live work until resolved within approved setup. Tool installation/build outside the owned root requires fresh permission. A supported fix must pass these gates on the final correction tree and the real changed-path smoke after removal of scaffolding.

Skill Lens documentation batches retain its four coordinator gates:
`uv run pytest --cov=skill_lens`, `uv run mypy`, `uv run ruff check .`, `uv run ruff format --check .`. Those prove repository health, not doc-only scope or a Herdr fix; use pre/post status and tracked/untracked fingerprints for scope proof.

This revision's review evidence belongs under `docs/validation/2026-10-25/waiter-plan-review-r2/`. Future authorized execution uses a separate dated `waiter-diagnosis/` folder: authorization, source/patch/tool/runtime hashes, observer rehearsal/final reviews, fixed run ledger and exact brief, allowlisted raw captures, command receipts, complete matching reports, native completion and clock-correlation evidence, branch/predicate timeline, classification, gate logs, and cleanup receipt. Create no fake outputs or empty proof placeholders. Keep secrets out of the repo; preserve original historical evidence.

Only Sol accepts/commits. The owner has authorized the plan's two-commit freeze and A0 preparation only. Stop after verified Stage 1 evidence and the Stage 2 approval packet; do not start A1/live diagnosis or B, deploy, merge, tag, release or publish without the relevant later explicit authorization.

## 10. Review status

Revision1 was rejected by Sol and both named critics; the owner accepted revision rather than freeze. This revision addresses the four blockers: unproved replay mechanism, different historical/startup transitions, unsafe sequence carrier, and incomplete path/proof/approval boundaries. Its own independent critic wave is required before delivery. Findings, dispositions and exact reviewed hashes will be recorded in the revision2 review folder; review completion does not authorize a freeze.

Owner approval, 2026-10-25: freeze this independently reviewed revision and start A0/Stage 1. The two planning critics passed the operative diagnostic-only design; their complete opinions and nonblocking prerequisites remain in the revision2 review folder. This approval does not extend to Stage 2/A1 live work.
