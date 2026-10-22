# Herdr 0.9.5: recorded lifecycle failures and smallest fix proposal

Date: 2026-10-22. Status: investigation complete within the available evidence; **no fix implemented or proved**.

Authorization: preserve the three incidents, inspect matching source read-only, and save a diagnosis/proposal. No freeze, commit, implementation, build, install, new worker, smoke, repair, settings edit or service restart. This instruction is narrower than “go ahead with the fix” and governs this work.

## Result

There are **two different problems**, not one generic bad wait:

- Mini has a demonstrated screen-rule compatibility gap: its active footer says `esc stop`; Herdr's active rule does not recognize that shape. The waiter reports failure to observe activity; it does not falsely report successful completion.
- Both full-TUI incidents returned an integration-authoritative idle/done state before the task finished. The source explains how that state becomes a completion sequence and satisfies the waiter. The exact integration callback that supplied the premature idle is **not recorded**. A source-level candidate is identified below, but selecting a causal patch now would require guessing.

No new trial was needed to establish those conclusions. Choosing and proving a full-TUI fix remains blocked by the missing reporter/event trace. A new live capture, if ultimately needed after offline work, requires separate authorization; none ran here.

## 1. Evidence preserved first

Everything created by this investigation stays in this dated folder and is uncommitted. Originals were not moved, edited or deleted.

- Latest final-review incident: all **14** files in its temporary receipt directory were copied byte-for-byte to [incidents/final-review/](incidents/final-review/) and verified with SHA-256, a file-content checksum. This includes its complete report, native sanitized session export, completion metadata, lifecycle ledger, source gates, exact brief/diff, and pre/post fingerprints.
- Older Mini and full-TUI temporary directories are **missing**, not silently recreated. Their exact paths are in [preservation-inventory.json](preservation-inventory.json). A second search of the original temporary parent found only the newer planning/implementation directories. Those vanished original receipt files cannot be claimed recovered in full.
- Preserved the current canonical historical record and Desktop handoff byte-for-byte under [shared/](shared/), including the handoff's embedded historical snapshot. The pre-existing uncommitted canonical record remains untouched.
- Recovered all tool-result receipts and assistant tool-call records in each incident's fixed UTC window from the saved OMP coordinator sessions: Mini **102** records; earlier full TUI **74**; latest final review **78**. These are labelled `recovered-coordinator-receipts.jsonl`, with original source line numbers and timestamps, **not** presented as the original vanished temporary files. Assistant reasoning messages and credential-pin records were excluded.
- Also preserved asynchronous wait-return notifications separately and scoped server/client log windows. Server windows contain **39 / 31 / 27** entries respectively. The source logs do not contain the actual `pane.report_agent` payloads for these incidents. No unrelated full application log or private settings file was copied.
- [recovery-provenance.json](recovery-provenance.json) records the windows, original paths, line numbers, capture-time session checksums and recovery counts. The current coordinator session is append-only, so its capture-time checksum is not a claim that the live file will remain unchanged later.
- [incident-signals.json](incident-signals.json) contains the audited signal/timestamp facts. Copies of the exact release metadata, source archive, selected source files, installed reporter code and active remote manifest are under [source/](source/). [integrity-manifest.json](integrity-manifest.json) records the final durable file checksums, excluding itself.

The two 2026-10-20 incident labels are the saved record dates. Their live trials occurred on **2026-10-19 UTC**; that is not a date discrepancy.

## 2. Source identity: matching the installed build

The installed `/Users/corvette/.local/bin/herdr` is the macOS ARM executable and reports `0.9.5`. Its SHA-256 is:

```text
fb77c2232a05a8035421382c894392f4174e4e38a18e48af3dd0290157c3a7e2
```

That is an **exact match** for the official immutable v0.9.5 release's `herdr-macos-aarch64` asset digest in the preserved [release metadata](source/release-v0.9.5.json), independently fetched from the [official release API](https://api.github.com/repos/herdrdev/herdr/releases/tags/v0.9.5).

The [tag reference](source/tag-ref-v0.9.5.json) resolves to annotated tag object `7573e821895d32c8d1f78b3f6c9a2f85a46df4ac`; its [tag object](source/tag-object-v0.9.5.json) identifies source commit **`2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01`**. The retained upstream archive and verbatim source snapshots come from that release, not current main. This matches the distributed release; no reproducible-build claim is made, and no build ran. Historical receipts report server 0.9.5/protocol 22, but do not contain an independent checksum of the old running server image.

Both installed OpenCode reporter files exactly match that release's bundled sources, including version marker **13**. Installed and bundled checksums are in [installed-integration-provenance.json](source/installed-integration-provenance.json). The installed V2 loader re-exports the shared TUI plugin. Disk-code identity does **not** prove which revision a long-running shared OpenCode server had loaded in memory during an older incident.

## 3. Exactly which signal was wrong?

| Incident | Directly recorded wrong signal | What the waiter returned | Worker-side completion first? |
|---|---|---|---|
| Mini | Standalone `agent get`: `idle`, state sequence `8`, while captured UI was still generating with `esc stop`. Offline classification of that captured footer also returned idle. | `agent_prompt_stalled`: no observed working/blocked activity within 5000 ms; command exited 1. | No prior completion report is captured. Versioned docs state V2 Mini does not run the pane-local TUI reporter. This is a missed-busy observation, not evidence of a worker completion callback. |
| Earlier full TUI | `agent prompt --wait` response: `idle`, `completion_seq=18`, `state_change_seq=18`, `screen_detection_skipped=true`; subsequent `agent get` correctly showed working sequence `19`. | Returned at `22:29:29.093933Z`; actual final assistant completion was `22:29:36.003Z`: **6.909067 seconds early**. Final settled sequence was `20`. | **Source-derived [INFERENCE]: integration idle authority was already effective at return.** This does not prove that OpenCode emitted an execution-completed event first; the original report frame/callback is missing. |
| Latest final review | `agent prompt --wait` response: `done`, completion/state sequence `5`, `screen_detection_skipped=true`; subsequent `agent get` correctly showed working sequence `6`. | Returned at `00:46:33.941543Z`; native final assistant completion was `00:50:41.778Z`: **247.836457 seconds early**. Actual settled sequence was `7`. | The same source-derived [INFERENCE]: an accepted integration idle authority was effective before return. `done` is an idle presentation, not a distinct “this request completed” message. The exact reporter event is absent. |

These conclusions concern CLI/API responses and effective state transitions. No separate receipt proves what a human TUI client's badge displayed at those exact instants. Do not convert the word `done` in the API response into an observed screenshot/badge change. The later working readbacks were correct; there is no need to invent an additional independent readback failure for the full-TUI cases.

### Why “integration idle first” is a deduction, not an invented event

The recovered original asynchronous full-TUI response and latest response both include `screen_detection_skipped=true`. `agent_info` obtains that flag from `terminal.full_lifecycle_hook_authority_active()` ([agents.rs:370–402](https://github.com/herdrdev/herdr/blob/2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01/src/app/agents.rs#L370-L402)). A live full lifecycle authority suppresses screen-blocker overrides, and effective state then comes from the accepted hook authority, not the screen fallback ([state.rs:2074–2099](https://github.com/herdrdev/herdr/blob/2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01/src/terminal/state.rs#L2074-L2099), [2404–2435](https://github.com/herdrdev/herdr/blob/2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01/src/terminal/state.rs#L2404-L2435)).

The hook reducer stores the supplied state ([state.rs:701–812](https://github.com/herdrdev/herdr/blob/2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01/src/terminal/state.rs#L701-L812)). The app records a completion sequence for a working/blocked → idle transition ([actions.rs:22–28](https://github.com/herdrdev/herdr/blob/2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01/src/app/actions.rs#L22-L28), [1753–1762](https://github.com/herdrdev/herdr/blob/2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01/src/app/actions.rs#L1753-L1762)). Public status maps idle + unseen to `done`, idle + seen to `idle` ([api_helpers.rs:96–106](https://github.com/herdrdev/herdr/blob/2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01/src/app/api_helpers.rs#L96-L106)). Changing the display label cannot fix either premature return.

That chain establishes the **wrong integration-derived state boundary**. It does not reveal the original hook request's timestamp, sender, payload sequence, upstream callback or execution identity. Those facts were not logged and must not be fabricated.

## 4. Cause per incident

### A. Mini: demonstrated compatibility gap

Original receipts include the failed prompt result and a live UI/get pair, plus the earlier authorized offline control:

- Captured busy footer → idle, no matched rule, `default_known_agent_idle_fallback`.
- Change **only** `esc stop` to `esc to interrupt` in the control fixture → working, `interrupt_hint_working`, priority 110.

Those saved results are at original coordinator source lines **159 and 173** in the Mini recovered receipt file; the live failure/get pair is at source lines **73 and 76**, timestamps `22:16:53.927Z` / `22:16:56.637Z`. Source-line numbers are provenance fields, not this recovery file's physical line numbering.

The active remote manifest and bundled/distributed manifest are version `2026.06.10.1`. Its working hints recognize interrupt wording or progress-bar glyphs, not the observed Mini footer ([opencode.toml:18–37](https://github.com/herdrdev/herdr/blob/2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01/src/detect/manifests/opencode.toml#L18-L37)). No rule match defaults a known agent to idle ([manifest.rs:543–563](https://github.com/herdrdev/herdr/blob/2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01/src/detect/manifest.rs#L543-L563)). The official [integration documentation](source/files/docs/next/website/src/content/docs/integrations.mdx) at lines 194–202 explicitly excludes V2 Mini/headless from pane-local TUI lifecycle reporting. Merely reinstalling the current integration would not supply that missing Mini lifecycle source.

**Limit:** the previous offline control proves the captured screen-rule mismatch. The original live detector's exact input and decision at the stalled-return instant were not saved; do not claim that every internal live step was captured. This investigation did not rerun that control or Mini.

### B–C. Full TUI: premature authoritative idle; exact producing callback unresolved

The waiter is not a request-completion protocol. In [wait.rs:177–321](https://github.com/herdrdev/herdr/blob/2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01/src/api/wait.rs#L177-L321), it first seeks observed working/blocked activity, then accepts a current idle/done/blocked status. The activity phase may accept a transient event and overwrite the returned status on a current snapshot ([364–483](https://github.com/herdrdev/herdr/blob/2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01/src/api/wait.rs#L364-L483)). The settled phase is not bound to an execution/turn ID; identity checks use terminal/name/agent, not `agent_session` ([537–559](https://github.com/herdrdev/herdr/blob/2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01/src/api/wait.rs#L537-L559)).

Thus an accepted working → premature idle transition is sufficient for this implementation to return successfully. It does not verify the final assistant message, substantive report, or absence of descendants. This explains **how the recorded false return passes the current mechanism**, not which callback first caused the bad idle. The fresh-session IDs and final native completion records rule out accepting the early response as the actual finished report.

The matching V2 reporter has these distinct idle-producing paths in [herdr-tui-session.js](source/files/src/integration/assets/opencode/herdr-tui-session.js):

- `setup.syncSelection`, lines **509–532**: initialize selected-session state from cache; anything other than `"running"` becomes `"idle"`; then enqueue selection identity and publish state.
- `setup.receive`, lines **572–580**: execution-start sets working; succeeded/interrupted sets idle. The payload's execution identity is not carried in the Herdr state report.
- `enqueue`/`requestOnce`, lines **13–33, 440–450**: send session identity/state/sequence under `herdr:opencode`, not a request-bound finished-turn receipt.

**Ranked hypotheses, not established causes:**

1. **[INFERENCE] Selection/cache handoff:** an initial cache-derived idle overtakes or follows startup screen-working evidence, before the real execution-start event. Prediction: the premature raw report is a TUI initialization/selection publish, not a terminal execution event. The very early return plus unchanged `OpenCode` title are consistent with this, not proof.
2. **[INFERENCE] Upstream lifecycle semantics/order:** a real succeeded/interrupted or intermediate execution event precedes later work for the same request. Prediction: the raw TUI event stream itself contains the early terminal event, so suppressing cache initialization alone would not fix it.
3. **[INFERENCE] Another reporter or stale loaded integration:** a shared server's older reporter publishes the same `herdr:opencode` authority while the pane-local reporter is active. Prediction: the premature request has a different sender/request-ID shape or loaded-code provenance. Current matching disk files do not prove old in-memory code. Versioned docs explicitly warn that old shared-server reporters can overwrite pane-local state after an integration update; that warning is not proof it happened here.

No hypothesis was tested against a new worker, instrumented runtime or rebuilt source. Existing V2 tests cover start/terminal events and selection churn, but their `v2Api` status cache is fixed to idle and they do not join reporter startup, detector acquisition and the real waiter in one consumer-visible scenario ([test fixture:241–277](https://github.com/herdrdev/herdr/blob/2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01/src/integration/assets/opencode/herdr-tui-session.test.ts#L241-L277), [V2 tests:552–625](https://github.com/herdrdev/herdr/blob/2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01/src/integration/assets/opencode/herdr-tui-session.test.ts#L552-L625)). Their passing status was neither assumed nor checked here.

## 5. Exact missing evidence

For **each full-TUI premature completion**, the retained INFO server log shows prompt start/end but not these necessary boundary records:

1. Raw `pane.report_agent` and `pane.report_agent_session` frames immediately before/through the early completion: receive/accept time, source, request ID, pane, session, state and sequence; whether each was accepted or rejected.
2. The corresponding pane-local OpenCode events and cache/route values: session/execution/message identity, `session.execution.started|succeeded|interrupted|failed`, status-cache value, selection/hydration branch and emission order.
3. The effective-state transitions consumed by the activity gate: their authority and session/turn owner, especially the working transition immediately before sequence 18 or 5.
4. Loaded reporter identity at incident time, sufficient to distinguish pane-local V2 plugin from stale/shared-server reporting. No provider credentials, prompt bodies or private configuration are needed.

The complete native final-review export proves actual finished-message timing and no active review descendants; it does **not** contain the earlier UI/cache callback stream. Re-reading the final report cannot recover it. A source review or fabricated event sequence cannot turn that absence into a measured causal diagnosis.

## 6. Smallest fix proposal — not authorization to implement

### Mini: a concrete, independently scoped change

Update the OpenCode working-footer rule in `src/detect/manifests/opencode.toml` and its distributed counterpart `distribution/agent-detection/opencode.toml` to recognize the captured **active Mini footer**. Match the footer shape narrowly, not any arbitrary `esc stop` text in the transcript; preserve blocked-rule priority and idle behavior. Give the published manifest a newer valid version so the cached remote manifest cannot silently continue winning. No local override or blanket idle fallback change is proposed.

After separate authorization, verify with the already-recorded busy fixture using the real detector; add negative fixtures for the idle footer, approval UI and a transcript merely quoting `esc stop`. Preserve existing full-TUI interrupt/progress matches. Only after offline verification would a separately authorized Mini trial establish live behavior. This change does not fix the two full-TUI incidents.

### Full TUI: do not select a speculative patch

The smallest responsible proposal is **one reporter/wait boundary correction selected by a pinned offline regression**, not an immediate change to every idle rule:

- If hypothesis 1 is established, change `setup.syncSelection` / `enqueue` in `src/integration/assets/opencode/herdr-tui-session.js` so selection identity/cache initialization is not asserted as completion of newly submitted work before the authoritative execution state is reconciled. Use the existing selection-only report where appropriate; preserve truthful idle for an actually settled existing session. Add the regression beside `herdr-tui-session.test.ts`.
- If hypothesis 2 is established, fix the actual upstream execution-event producer or turn aggregation; a Herdr footer rule or sleep cannot correct a faithfully forwarded premature upstream event. The corresponding OpenCode 2.0.32 source/event contract would then be a prerequisite before naming its patch file.
- If hypothesis 3 is established, correct the proven reporting-ownership/loading boundary. Do not patch the current on-disk plugin or restart services merely because the official docs mention that possibility.

At the consumer seam, extend `tests/cli/agents.rs` (existing prompt-wait cases at lines 428–469) with the identified **real multi-authority sequence**, connected to the reporter/detector behavior rather than only fake status echoes. The required observation is that a new request cannot be accepted complete on selection/hydration or another owner's state; it must still accept a genuinely fast completed turn and legitimate blocked result. A future stronger request-bound wait may require matching session/authority/execution generation, but a generic waiter redesign is **not** justified by these missing traces alone.

In particular, merely setting a different `after_state_change_seq`, rejecting all fast idle transitions, adding sleeps, extending timeouts, relabelling `done`, or increasing polling is not a proved fix. The current activity gate already rejects idle-only churn; it cannot validate a bad authoritative working/idle pair. Preserve that distinction.

### Verification once separately authorized

1. Turn the relevant captured transition sequence into an offline, deterministic failing regression in the matching source. Assert the early wait **does not** complete at the premature idle, then assert completion only on the matching final execution; include true fast-turn, blocked, stale-session and cross-authority cases. Do not claim a made-up sequence proves this incident's exact cause.
2. Apply only the selected correction and run the relevant detector/plugin/waiter regression suites in an isolated source checkout. No change to the installed app yet.
3. Obtain separate permission for any installation/reload/restart needed to deploy that correction.
4. Only with separate live-trial authorization, run one bounded owned-worker check with raw event/report receipts and substantive final-message/descendant proof. Then, separately, exercise an implementation/review task. Neither the earlier reviewer verdict nor this investigation grants general support.

**If the existing records cannot supply the missing trace and offline work cannot decide between the hypotheses, stop and request authorization for the narrowly instrumented capture. Do not run one under this investigation.**

## 7. Scope and verification of this investigation

Read-only analysis used the saved receipts/log windows, official release metadata and exact source snapshots. Python data processing audited/cross-checked the recorded timestamps, copied-file checksums and signal ordering; it did not execute Herdr/OpenCode integration code or replay a trial. This is evidence verification, not a reproduced-before/fixed-after result.

No new worker, subagent, model call, smoke, build, test suite, installation, patch, settings edit, server start/stop/restart, plan freeze, git staging, commit or push occurred. The only Herdr executable invocation was version metadata (`herdr --version`); no pane/session control or live state query was used. Source archive extraction is a file copy, not a build or installation. No new permanent tests or fixes were added. Historical evidence and all existing repo files remain as they were; only this dated evidence/diagnosis folder is new. Final preservation/scope checks are recorded in [verification.json](verification.json).
