# Plan: design a bounded full-TUI premature-completion capture

Status: Agreed
Authorization: User, 2026-10-22: “ok go on with the recommended procedures.” Prepare the bounded diagnostic design and required review/freeze. This draft does not authorize instrumentation code, a rebuild, installation, settings edits, a service start/restart, a worker trial or formal smoke. Those actions need concrete approval after their method and target are settled.
Reference: pending
Surface: omp; native Tern coordinator, external Herdr workers, no silent transport fallback.
Risk and review: High: observes lifecycle authority, session ownership and completion timing. Two independent fresh planning critics; final review also requires two if instrumentation is later implemented. Distinct families need evidence or explicit acceptance of the named pair's unverified upstream identity.
Roster: Sol requested/configured `openai-codex/gpt-6.1-sol`, thinking `high`, OMP 18.12.6, no fallback, active session `01a164fa-42dc-7045-ade8-6dc9090ac15b`. User selected Antigravity “Gemini 3.8 Flash High” and OpenCode “Deepseek V4.1 F Max.” Fresh Antigravity 1.4.5 launch argv/catalog/UI confirm `gemini-3.8-flash-high`, Plan, displayed high, no extra effort override. Fresh OpenCode 2.0.32 catalog/UI confirm `opencode/deepseek-v4.1-flash-free`, displayed `max`, switched from Build to Plan using advertised shift+tab before submission. User-started Herdr `default` is verified. Upstream identity remains independently unverified. Diagnostic-worker selection is separate; no automatic inheritance or fallback.
Expected child tasks: two planning reviewers; after separate instrumentation authorization, one edit-only implementer and two fresh final reviewers; after a separate capture authorization, exactly one full-TUI read-only diagnostic worker, no descendants. No launch is implied by this proposal.

## Outcome and evidence limit

Capture which event or reporter first supplies the authoritative idle that lets Herdr return before the matching response finishes. Distinguish selection/cache initialization, a real execution event and competing/stale reporters. Do not select a full-TUI fix until that boundary is measured.

The [diagnosis](../validation/omp-coordinator/2026-10-22-herdr-investigation/diagnosis.md) proves two early returns from saved receipts but does not contain the original reporter frames or upstream event stream. A new trace can explain a newly observed failure; it cannot reconstruct the absent historical event or prove an old in-memory reporter revision.

## Fresh prerequisites

- Checkout baseline `67f3e7db95ffcb84b475d6c1c7869b2b137f6650`; preserve all three recorded pre-existing user changes and the immutable investigation folder.
- Current binaries report Herdr 0.9.5 and OpenCode 2.0.32. Initial continuation discovery found all three known sessions stopped; after the owner started Herdr and said “ready,” fresh discovery and socket/server verification established compatible `default` on protocol 22. Historical panes and session permissions were not reused.
- The historical MiniMax alias is absent from the current OpenCode catalog. The owner has now selected the reviewer pair recorded above; verify their exact configured identities/settings before submission. Choose the diagnostic worker separately. Do not claim a new model reproduces MiniMax-specific behavior.
- Pinned source: Herdr v0.9.5 commit `2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01`, archive/source checksums in the preserved [manifest](../validation/omp-coordinator/2026-10-22-herdr-investigation/source/source-files-manifest.json).
- Source `src/logging.rs` reads `HERDR_LOG`. Existing API logging records request IDs/methods and generic success/error; it does not record the complete state/sequence/session payload or reducer rejection reason. Merely enabling debug logs is not an adequate capture design.
- The preserved reporter's `requestOnce` sends state/session/sequence frames but treats receipt of any socket data as delivery, without interpreting the response. A client-side delivery flag is therefore not proof that the server accepted a state mutation.

## Scope and approval boundaries

Now: write this proposal and the [Mini plan](2026-10-22-herdr-mini-detection-fix.md), inspect saved sources and non-mutating help/catalog/session metadata, run required repository health gates. No runtime instrumentation or experiment.

Recommended future setup: an owned, isolated copy of the pinned source and a dedicated temporary diagnostic server/session, rather than editing installed integrations or restarting the user's normal server. This requires explicit approval for the separate source directory, instrumentation/build and later server startup; those approvals are not bundled into approval of a trace run. Isolation removes old shared-server state, so a non-reproduction would remain inconclusive for the competing-reporter hypothesis.

Alternative, only if the owner specifically chooses it: observe an authorized existing environment with an approved non-invasive method that supplies all required fields. No such stock method has been demonstrated by the saved evidence; do not promise that changing a log level or exporting final messages will suffice.

No Mini launch, model fallback, production install/update, installed plugin edit, service restart, settings/credential change, raw socket routing override, waiter fix, idle suppression, sleeps or timeout workaround. No formal smoke or claim of general worker support.

## Proposed instrumentation, requiring separate implementation approval

Add diagnostic-only structured records in the owned upstream source copy. Use a unique `herdr_capture_20261022` target/tag, one capture ID, process identity, wall-clock UTC and a per-process monotonic timestamp. Log only the target pane/session after they are known. Record startup fingerprints before pane selection so reporter provenance is not lost. Do not change state selection, delivery ordering, retries, waits or report semantics.

| Boundary | Named source | Required record |
|---|---|---|
| TUI selection/cache and event receipt | `src/integration/assets/opencode/herdr-tui-session.js`, `setup.syncSelection`, `setup.receive` | Selected/root session, route/generation, cache status, event type, execution/message IDs when actually present, prior/next state, emit reason; distinguish initialization from execution terminal events. |
| Reporter send and response | Same file, `enqueue` and `requestOnce` | Request ID, source, pane, session, state, sequence, reporter PID/code checksum, send/receive timestamps and allowlisted response envelope. Generic `Ok` is transport receipt, not reducer acceptance; obtain acceptance from the reducer record. |
| Server report handling | `src/app/api/panes.rs`, existing report handlers | Target-scoped incoming lifecycle fields, request ID and actual response; raw accepted/rejected frame metadata, excluding message/prompt bodies. |
| State routing and reduction | `src/terminal/state.rs`, `set_hook_authority_at`, its routing/sequence checks, and selection/session paths `set_agent_session_ref_for_session_start` / `set_agent_session_ref`; `src/app/actions.rs` dispatch | Accept/ignore decision and branch reason; previous/new authority, source, session owner, sequence, effective state and mutation for state and selection reports. Capture every source affecting the target pane, not only the expected plugin. |
| Completion sequence and activity gate | `src/app/actions.rs` state transitions and `src/api/wait.rs` | State/completion sequences, authority/session owner, actual working/blocked event consumed, snapshots considered and precise return predicate for the matching prompt request. |
| Native worker completion | Supported OpenCode session metadata/export, not invented event fields | Matching unique request token, session, final assistant finish timestamp and descendant state; keep this independent of Herdr idle/done. |

Missing IDs must be recorded as unavailable, not synthesized or inferred from a timestamp. Preserve enough allowlisted protocol data to distinguish sender/ordering and acceptance without collecting credentials, environment dumps, prompt bodies, tool arguments or unrelated transcripts. On any possible secret leakage, stop capture and quarantine the private raw file; sanitize before durable delivery.

The later instrumentation/loading contract must resolve how correlation crosses events without an API request ID and specify finite log-volume/rotation settings before live approval. Do not invent an execution/request identity or silently add state-changing instrumentation to carry it. This design does not prescribe or implement a new runtime quota.

Instrumentation needs a focused offline rehearsal before live approval: verify each decision branch emits its truthful reason and ordering, and compare state/response behavior with instrumentation disabled. This only proves the observer works; a fabricated sequence is not evidence of the historical cause. If a required server/reporter boundary remains unobservable, do not launch the diagnostic worker.

## Proposed one-run capture contract, not yet executable

1. The owner approves the exact instrumentation/build separately. Review and freeze those implementation paths and runtime-loading details first. Do not modify the preserved source snapshots. Record toolchain/build, executable and loaded reporter checksums; loading the copied plugin must be isolated and explicitly approved, never a silent edit to the installed plugin.
2. The owner approves the exact diagnostic server/session, startup method, worker/model/settings and target/base pane selection. The proposed isolated-session name is `skill-lens-herdr-trace-20261022`; verify absence before any approved creation and do not reuse a session someone else owns. Creating this session is a separate permission from the existing-session connection gate.
3. After authorized startup, apply the normal [external connection gate](../process/omp/herdr.md): discover, verify named session/socket and protocol/version, then use the same explicit session prefix and returned pane IDs throughout. No historical IDs, focus-based defaults or socket environment overrides. Record base layout/focus, cwd, foreground shell and pre-capture fingerprints.
4. In the approved owned pane, start exactly one fresh full-TUI OpenCode worker, verify the selected model and Plan/read-only mode, loaded reporter and session identity before prompting. No resume, duplicate submission, descendants or paid-model switch. Preserve user focus.
5. Submit one harmless evidence-review task with the exact OMP read-only guard, unique capture/request token and complete report schema. Use a real bounded read-only task, not synthetic sleeps or a forced fake response. Exact brief and expected matching report must be approved and saved before launch. No initial file-output request to bypass normal readback.
6. Proposed fixed bounds: startup 30000 ms, prompt wait 600000 ms, overall observation 720000 ms. Check installed help first; retain these preselected bounds without extension. Record waiter output and underlying events concurrently. A first idle/done return is evidence, not acceptance. Do not keep submitting until a failure appears.
7. If the waiter returns early, inspect the same worker and continue the already-approved capture window using event-driven instrumentation and bounded readback; no resend, replacement, blanket polling loop or timeout escalation. If blocked/approval UI appears, stop and ask; do not answer it. A timeout means inspect and, under the approved cleanup policy, cancel only the owned task—not assume it vanished.
8. At native final completion or the fixed deadline, preserve the matching complete report, native completion/descendant evidence, raw allowlisted report/event records, activity-gate decisions, command/result receipts and source/runtime fingerprints. If the deadline expires, mark the capture incomplete and preserve evidence before owned cancellation.
9. Clean up only owned worker/pane and, if explicitly authorized in its startup contract, the owned diagnostic server/session after checking saved evidence and absence of owned descendants. Never stop an existing user session. Preserve original focus/layout and compare pre/post fingerprints. No installed files/settings are changed or restored because none were authorized for mutation.
10. Classify the result once: measured selection-derived idle, measured upstream terminal event, measured other reporter, or inconclusive/missing boundary. Absence of a failure in one isolated run is not a repair or proof of an earlier callback. Any further run or causal patch requires a new concrete authorization and regression plan.

## Outputs and acceptance

Proposed durable output folder, created only after the capture is authorized: `docs/validation/omp-coordinator/2026-10-22-herdr-full-tui-capture/`. Keep private raw material outside the checkout; commit only sanitized allowlisted evidence under applicable delivery authorization.

Required outputs: `authorization.md`, source/runtime fingerprint manifest, lifecycle ledger, exact guarded brief, timestamped reporter/server/gate JSONL records, CLI receipts, complete report, native completion receipt, state/event timeline, cleanup/preservation receipt and a checksum manifest. Evidence filenames and permissions must be settled in the instrumented implementation freeze; this list does not create empty placeholder files.

Capture passes evidence collection only if the critical report is correlated from producer/cache/event through server accept/reject and effective authority to the waiter decision, with independent final-message timing. Otherwise label the missing boundary and stop. A successful diagnostic capture is not formal smoke acceptance, a proved fix, implementation-worker support or permission to deploy.

Required repository gates remain `uv run pytest --cov=skill_lens`, `uv run mypy`, `uv run ruff check .`, `uv run ruff format --check .`. Instrumented-source checks and an actual bounded runtime capture are additional evidence only after their separate approvals; repository tests do not validate the Herdr observer.

## Decisions blocking review/freeze and live work

- Reviewer choice and pre-submission configured checks are resolved: Antigravity Gemini 3.8 Flash High in Plan and OpenCode DeepSeek V4.1 Flash Free with `max` in Plan. This is the user-selected pair, not the initially suggested DeepSeek/GLM pair. Exact upstream served identities remain unverified; no fallback or persistent settings edit.
- User-authorized `default` review connection passed: matching Unix socket, compatible Herdr 0.9.5/protocol 22 and corroborated default identity. An available shell was rediscovered in this checkout; two owned sibling reviewer panes were created and both fresh reviewers started with original focus preserved. Exact requested model/settings and Plan modes were verified before substantive submission. Sol did not start a server or use an alternate transport.
- Review this design before authorizing instrumented-source preparation. Then approve instrumentation/build and loading separately from the exact one-run worker/session capture. The diagnostic worker model may remain unselected until that later capture approval; it must be concrete before launch.
- Required planning approvals are now complete: retained DeepSeek R1 content review on the unchanged operative scope and a fresh compliant Antigravity replacement pass on both clarified drafts. The original Antigravity no-write claim remains invalidated and does not count. This agrees a design only; instrumentation/build/loading and an exact live capture remain separately unauthorized.

## Continuation verification, 2026-10-22

Coordinator source-health run: `uv run pytest --cov=skill_lens` **1082 passed, 1 skipped**, **91.16% coverage**, 78.94 seconds; skip is the case-insensitive-filesystem case. `uv run mypy`: clean on 38 source files. `uv run ruff check .`: passed. `uv run ruff format --check .`: 282 files already formatted. Combined elapsed time 80.04 seconds, tool output `artifact://8` (session-local receipt, not promised durable storage).

No worker, subagent, trace, build, installation, integration edit, settings change, service control, Mini trial or formal smoke has run. Current work is planning only; project gates are not proof of a Herdr repair.

Draft navigation check: all seven distinct relative link targets across these two plans exist. Pre-existing user-file checksums and the pinned upstream archive checksum were checked after drafting and remain unchanged; exact values are recorded in the companion Mini plan's continuation receipt. No staging, commit or push was performed.

Roster follow-up before the user's “ready”: native installed help confirmed Herdr kinds `agy`/`opencode` and Antigravity `--mode plan`. OpenCode's headless run help supports `provider/model#variant`; full-TUI selection and Max availability still need verification before submission. Sessions were stopped at that earlier checkpoint, not after the subsequent successful connection gate.

Review preparation after “ready”: the companion Mini plan records the verified current session, owned panes, pre-launch fingerprint and temporary ledger location. Both selected runtime startups were issued with 30000 ms readiness limits. No substantive review task had yet been submitted at this checkpoint, and no diagnostic capture or implementation was started.

## R1 stopped-review receipt

The companion [Mini plan](2026-10-22-herdr-mini-detection-fix.md) records the complete incident, exact native Antigravity command, sessions, source checksum, evidence location and cleanup. R1 fingerprint comparison found one new file, `herdrdev-herdr-7573e82/src/detect/manifest/tests.rs`, created by Antigravity's attempted stdout inspection of the archive; its no-write completion claim is contradicted. Both pass reports are preserved but not accepted for freeze. All pre-existing fingerprinted files and HEAD were unchanged.

The file is preserved in place and copied outside the checkout; no deletion or remediation was performed. Both owned workers/process groups and shells are gone; only their panes were closed, leaving the original focused `wF:p1` at 148×55 with no splits. No active owned work, source implementation, instrumentation, trace, installation, service operation, freeze, commit or push remains underway. Owner decision on exact artifact cleanup and fresh compliant replacement review is required before proceeding.

## Approved recovery and review dispositions

The owner approved removal of the exact extracted artifact/empty directories and a fresh Antigravity replacement review with shell/archive commands prohibited. That cleanup is complete; the pinned archive and matching external evidence copy remain preserved. The companion Mini plan records every R1 suggestion and disposition. Accepted changes here clarify existing receipt-versus-acceptance and selection-reducer requirements; the title is administrative. No execution, new runtime policy or approval boundary is added. DeepSeek's original substantive design review is retained; the invalidated Antigravity no-write claim is not counted toward freeze.

## Final design-only planning acceptance

The companion Mini plan's final acceptance receipt records the complete independent model/session evidence, report checksums, reviewed draft hashes, clean replacement fingerprint manifest, final four passing project gates and owned cleanup. Both accepted critics passed this capture **design only**; the fresh Gemini reviewer used native file reads only, with no shell/archive commands and no checkout changes. No in-scope design blocker remains.

Source inspection, offline observer preparation and the exact one-run capture are still separate gates: resolve the logging/correlation/loading details in an authorized instrumentation contract, obtain its required reviews/freeze, and separately approve the exact worker/model/session/pane, outputs and cleanup before any live run. The agreed design does not authorize a rebuild, install, settings edit, service/session creation, restart, diagnostic worker or smoke. A single isolated non-reproduction remains inconclusive for competing/stale reporters.

Freeze this plan in its own two-commit procedure, with the exact first hash recorded only afterward in `Reference:`. Apply the same standing delivery/preservation rules recorded in the Mini receipt; commit only the agreed plan and its later reference update, leave original user work unstaged, and stop after verified delivery.
