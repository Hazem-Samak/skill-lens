# Handoff: native Tern OMP / Herdr investigation

Saved: 2026-10-22. **Status: PAUSED BY THE USER. Start nothing automatically.**

## Where we stopped tonight

The layout documentation is implemented and pushed. The separate read-only investigation is complete within the evidence available; its diagnosis and fix proposals are saved here. **No Mini fix or full-TUI fix has been implemented or proved.**

The owner has now authorized only this handoff and committing/pushing this investigation folder, then stopping. That permission does not authorize another investigation, worker, trace run, repair or smoke. Earlier “go ahead with the fix” wording was explicitly narrowed to investigation only; it is not standing implementation permission.

The last owned reviewer was completed and its pane cleaned up during the earlier documentation task. Cleanup receipts record no active owned work and preservation of the original pane/focus. That is a recorded observation, not a fresh live-session inspection. All pane/session IDs in these receipts are historical; rediscover and obtain the required authorization before future control.

## Decided, frozen and pushed

- **Layout:** Sol/OMP stays native in Tern. Herdr hosts and controls implementation/review workers through its CLI/socket; OMP does not run inside Herdr. Sol remains `openai-codex/gpt-6.1-sol`, thinking `high`, no silent fallback. Other workers remain session-selected.
- **Frozen amendment:** [2026-10-22-omp-herdr-external-control.md](../../../plans/2026-10-22-omp-herdr-external-control.md) @ **`988d3917890ddf56b48b950afa2c162dd84c8c4e`** (`988d3917`). Its reference-recording commit was `321e5693f9d8e528bb350e465fab80655d3d1922`. Both were pushed.
- **Documentation implementation:** **`34966b39f815d2f6b8d530bc46b4f2febc3ecdae`** (`34966b3`), pushed to `origin/main`; local/tracking/remote hashes matched. It updated the [Herdr adapter](../../../process/omp/herdr.md), OMP README and both OMP loops, appended the history-preserving change to the [2026-10-20 smoke plan](../../../plans/2026-10-20-omp-herdr-dispatch.md), and recorded execution in the amendment plan.
- The external connection gate verifies an authorized existing session and socket; commands use explicit pane IDs, finite wait timeouts and inspect-before-resend. The repo's user-approved authority narrowly supersedes the installed skill's outside-control ban, without changing installed skills/settings. Guard, ledger, review and acceptance rules remain unchanged.
- The fresh documentation review really ran through Herdr, not the old relay. It passed, but its first completion signal was premature; actual report/session completion was verified separately. That does **not** establish reliable waiting or formal smoke acceptance. The implementation receipt rejects the reviewer's mistaken relay assertion using the direct transport evidence.

## Investigation outcome

Read [diagnosis.md](diagnosis.md) first for the evidence, source citations, precise limits and proposed verification.

### Mini: demonstrated cause and a proposal, not a fix

The active busy footer says `esc stop`; Herdr's matching OpenCode detection rules do not recognize it. Saved live readback showed idle during generation; the waiter returned `agent_prompt_stalled`, not successful completion. The previously recorded offline one-phrase control isolated the mismatch. No Mini trial was repeated during this investigation.

The proposed small fix is a narrowly matched active-Mini-footer rule in the upstream bundled/distributed OpenCode manifests, with an appropriate newer manifest version and negative fixtures for idle, approval UI and quoted transcript text. A broad `esc stop` substring match or blanket idle change is not proposed. **The owner has not authorized implementing, installing or testing this fix.** It would not fix the full-TUI problem.

### Full TUI: exact cause unknown; event trace required before choosing a fix

The two full-TUI incidents returned idle/done before the actual response finished. Matching Herdr 0.9.5 source plus `screen_detection_skipped=true` support the deduction that premature integration-derived idle authority already existed when the waiter returned. `done` is the public presentation of unseen idle, not independent proof that this request finished.

**The exact callback/event producing that idle remains unknown.** The missing trace must distinguish selection/cache initialization, an upstream execution event, and another/stale reporter. Raw accepted/rejected `pane.report_agent` frames, matching OpenCode execution/cache/route events, and the activity gate's authority/session ownership were not captured. Existing final-message exports cannot reconstruct them. Hypotheses in the diagnosis are not proved causes.

Do not patch the waiter, suppress idle, add sleeps or extend timeouts by guesswork. The next proposed action is a narrowly instrumented capture of that missing boundary evidence; its logging/setup needs must be specified and approved first. **No trace run has been authorized or performed.** If deciding the cause requires a live trial, stop and ask rather than run one.

## Decisions reserved to the owner — NOT authorized

1. **Mini fix:** whether to plan/freeze/implement the proposed detection-rule correction, run its verification, and separately approve any deployment or Mini trial.
2. **Instrumented trace run:** whether to authorize one bounded diagnostic capture, including the exact logging method, worker/model, target session/pane, preserved outputs and cleanup. Do not bundle a rebuild, patch, installation, settings change or service restart into that approval.
3. **Formal smoke:** whether and when to authorize a new formal smoke after a correction is proved. Documentation approval, the earlier document review and this handoff do not authorize it. Preserve the original wait-correctness, substantive matching report, real completion/no-owned-descendants, preservation and cleanup criteria.

No permission is implied to launch new workers/subagents, repeat the failed trials merely to confirm them, install/update/repair anything, change settings/integrations, restart services, substitute models, or claim general implementation/review support.

## Evidence and navigation

- [Diagnosis and smallest fix proposal](diagnosis.md).
- [Audited incident signals and chronology](incident-signals.json) and [original asynchronous wait snapshots](audited-wait-returns.json).
- [Mini incident](incidents/mini/), [earlier full-TUI incident](incidents/full-tui/), [latest final-review incident](incidents/final-review/).
- [Preservation inventory](preservation-inventory.json) and [recovery provenance](recovery-provenance.json).
- [Shared original historical record and Desktop handoff copies](shared/). Those are historical evidence; their old inside-Herdr startup instructions are superseded, not current execution guidance.
- [Matching source and installed-code snapshots](source/), [release/build provenance](source/provenance.json), [source file checksums](source/source-files-manifest.json).
- [Investigation verification](verification.json) and [durable file-integrity manifest](integrity-manifest.json). The checksum manifest excludes itself and is extended to include this handoff.
- [OMP entry/roles](../../../process/omp/README.md), [planning loop](../../../process/omp/planning-loop.md), [implementation loop](../../../process/omp/implementation-loop.md).

All 14 latest temporary receipts were copied and checksum-verified. The two older temporary folders were already missing; recovered coordinator receipts and log windows are explicitly labelled and are not claimed to be complete copies of those vanished originals. The installed binary exactly matches the official 0.9.5 macOS ARM asset; the selected release source commit is `2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01`. Historical in-memory reporter provenance is still a limitation.

`diagnosis.md` and `verification.json` describe the investigation **before** this closeout, so their “uncommitted” / “no commits” statements are historical. This later user instruction authorizes committing/pushing this folder only; it changes no operative permission or finding. The actual closeout commit hash is reported after creation, not invented inside its own future commit.

## Checkout preservation and verification record

Before closeout, branch was `main` at `34966b39f815d2f6b8d530bc46b4f2febc3ecdae`. Preserve and leave unstaged:

- Modified original `docs/validation/omp-coordinator/2026-10-20/herdr-dispatch.md`.
- Untracked `.path`.
- Untracked `docs/plans/2026-10-19-herdr-omp-coordinator.md`.

The investigation's copy of that historical evidence belongs in this folder; the modified original does not belong in the closeout commit. Stage only `docs/validation/omp-coordinator/2026-10-22-herdr-investigation/`. Recheck actual checkout state in a fresh session; these are saved observations, not permanent bindings.

Last exercised source-health gates are retained in `incidents/final-review/gates.txt`: 1082 passed, 1 skipped, 91.16% coverage; mypy clean on 38 files; Ruff lint/format clean. Investigation changed no product/test/checker inputs and ran no new trial, build or test suite. Closeout verifies evidence checksums, handoff pointers, unchanged existing files and scoped delivery; it does not claim a repaired runtime or fresh smoke.

**Resume by reading this note and the diagnosis, then wait for the owner's concrete next authorization. Do not start the proposed work from this handoff.**
