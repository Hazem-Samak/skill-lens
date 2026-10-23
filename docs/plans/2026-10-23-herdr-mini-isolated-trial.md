# Plan: one isolated live validation of the Mini correction

Status: Agreed
Authorization: Owner, 2026-10-23: “go ahead with what is needed to be done,” following the recommendation to prepare and run the isolated Mini trial. This authorizes planning/review/freeze, the temporary pinned build environment, the named isolated Herdr server, a credential-free private OpenCode backend, one diagnostic Mini prompt and bounded owned cleanup. It does not authorize replacing the installed Herdr, changing/restarting the user's normal services or settings, copying credentials, the full-TUI trace/fix, formal smoke or publication. Execution starts only after verified freeze and the preflight gates below; a preflight that needs a new credential or compatibility choice returns that choice to the owner.
Reference: 1ab5297debea785b2f4de069f18ebb40c578dc44
Surface: omp; Sol remains native in Tern; review workers use the existing authorized Herdr route.
Risk and review: High: temporary process/server creation, isolation, lifecycle timing and cleanup. Two fresh independent planning critics and two fresh final evidence critics. Reuse the owner's selected Gemini 3.8 Flash High / Plan and OpenCode DeepSeek V4.1 Flash Free / max / Plan pair; upstream served identities remain unverified, as previously disclosed and accepted. Broad reviews use fresh contexts; targeted follow-ups may reuse the affected critic, as recorded in Review decisions. No silent substitutions.
Roster: Coordinator requested/configured openai-codex/gpt-6.1-sol, thinking high. Proposed diagnostic worker is opencode/deepseek-v4.1-flash-free#max, native Mini, Plan with every tool permission denied. This reuses the owner's selected provider/model rather than the unavailable historical MiniMax alias; it is not a new model selection. Verify private-profile availability and effective model/variant before sending the sole prompt. No WorkBuddy attempt or coding implementer is needed: apply the already accepted patch unchanged; Sol owns operational verification, not new product code.
Expected child tasks: two planning critics; zero source-code implementers; after verified freeze and preflight, one Mini diagnostic worker; two fresh final evidence critics. A failed/inconclusive trial does not authorize a second prompt or corrective code.

## Outcome

Determine whether the delivered Mini correction works during one real generation in a disposable environment, without changing the user's normal Herdr/OpenCode services. Preserve enough evidence to distinguish a genuine pass, a failure and an inconclusive run. This is not formal smoke acceptance or proof of general Herdr reliability.

## Current state and evidence

- Repository `main` at `6ce458afe9302e3d5869f293203dda7f3ca43f10`. The accepted correction is commit `5a044803c2cdd22063442411062b25aa9e1ee6b2`; the later commit records cleanup. Preserve the modified historical `docs/validation/omp-coordinator/2026-10-20/herdr-dispatch.md`, untracked `.path` and untracked 2026-10-19 coordinator plan, unchanged and unstaged.
- [Accepted patch](../validation/omp-coordinator/2026-10-22-herdr-mini-detection-fix/correction.patch), SHA-256 `f22d2d7edf26dd8e308394de143b015b37cf58f17148a45ca3c12889b8c6efe8`, applies to Herdr v0.9.5 commit `2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01`. [Archive](../validation/omp-coordinator/2026-10-22-herdr-investigation/source/herdr-v0.9.5.tar.gz) SHA-256 `5c745bf712aee3320ed88a665c39a9143cbd6b7ce4376e0ae0f0c07988576c13`. Only four maintained source paths change; no new source correction is proposed.
- The delivered evidence includes 100 focused tests, Clippy/format checks, 29 actual CLI cases, loader selection over an older remote cache, priority/symbol mutation proofs and two fresh final passes. The old build/tools directory was removed. Rebuilding requires a new owned environment; do not assume an old executable still exists.
- Installed Herdr remains 0.9.5, SHA-256 `fb77c2232a05a8035421382c894392f4174e4e38a18e48af3dd0290157c3a7e2`. User-started `default` is responding, protocol 22, compatible at `/Users/corvette/.config/herdr/herdr.sock`. Planning-base `wG:p1` was freshly discovered, original shell PID 45632, sole focused pane with 55 rows; recheck identity/layout before reviewer control.
- Installed OpenCode now reports **2.1.4**, SHA-256 `d8a65dd253dbea759ae0dd829792ff219b40178c7decffea822430a4d1ccadb3`, at `/Users/corvette/.opencode/bin/opencode`. This is a newly observed machine fact, not the earlier 2.1.3 runtime or the original 2.0.32 incident. No claim that the old incident was reproduced on 2.1.4. If the executable changes before execution, stop for an explicit compatibility/baseline decision; do not silently roll the trial forward.
- The user's shared OpenCode service is currently running at `http://127.0.0.1:49374` (observed through `opencode service status`). The trial must not create sessions on, send prompts to or stop that service. All trial traffic targets the private loopback backend and its recorded port, which is why the preflight must prove the selected model is available without the shared service's credentials.
- [Diagnosis](../validation/omp-coordinator/2026-10-22-herdr-investigation/diagnosis.md): Mini missed its active `esc stop` footer; full TUI returned early from a different integration-authority problem. The latter's producing event remains unknown. The separate [full-TUI capture plan](2026-10-22-herdr-full-tui-capture.md) stays design-only.

## Scope and isolation

Planning writes: this plan; scoped planning evidence under `docs/validation/omp-coordinator/2026-10-23-herdr-mini-isolated-trial/`; owned external planning receipts. Frozen old plans and investigation evidence remain unchanged. Sol owns these records and integration.

Future execution, after verified freeze and the preflight gates below:

The numbered steps are chronological. Do not download/build or start either server before step 2's model preflight passes.

1. Create one fresh owned directory with prefix `/tmp/skill-lens-herdr-mini-live-20261023-`; record the returned path, ownership and every child PID. Never reuse an existing directory. It contains source, temporary tools/build caches, harmless workspace, separate Herdr/OpenCode homes/configuration/state/cache/runtime/logs and receipts. No branch/worktree or user-skill access is needed.
2. **Preflight model availability before any build.** With the installed OpenCode binary and a synthetic HOME/XDG profile inside the owned root, run `opencode models --standalone` (the documented private-server mode) and prove the exact `opencode/deepseek-v4.1-flash-free` model and `max` variant are listed without the normal shared service's credentials. Record the command, effective config/catalog output, and stop the owned preflight server. Bound the preflight to 60 seconds; on a hang, terminate only the owned preflight process and stop. If the model is absent, requires authentication or exposes a different effective variant, stop before downloading or building and return the credential/model choice to the owner. Do not copy `auth.json`, reuse the shared service or substitute a model.
3. Reuse the official pinned Rust 1.96.1 and Zig 0.16.0 package URLs/checksums from [toolchain provenance](../validation/omp-coordinator/2026-10-22-herdr-mini-detection-fix/provenance.json). Verify official package checksums before execution. Install/unpack only under the owned prefix, no Homebrew/system installation, persistent PATH edit or ldconfig. All compiler/tests' HOME, XDG roots, Cargo/Rustup homes, Zig caches, target and temporary paths remain inside it. Locked dependency downloads and two Cargo build jobs are permitted under this plan's authorization after freeze.
4. Extract the pinned archive and apply the accepted patch unchanged. Verify all four output hashes against [reconstruction](../validation/omp-coordinator/2026-10-22-herdr-mini-detection-fix/bounded-reconstruction.json). No waiter, plugin, detector or test edits. A required code change stops this plan.
5. Build the corrected **debug** binary with the isolated toolchain/caches and run the real `detect::` filter, Clippy with denied warnings, format check and the 29 preserved actual-CLI inputs. Preserve complete outputs. Do not rerun the original incident/control or add permanent tests. A failure here stops before any server starts; do not rebuild after these checks.
6. Run the corrected **debug** Herdr server directly in the foreground as a supervised owned process, using an explicit new named session `mini`, synthetic HOME (an empty temporary user folder), dedicated XDG configuration/state/cache/runtime directories and a recorded temporary config file. Write `R` for the returned owned root and keep Herdr's XDG config directory short: `R/hc`. The debug namespace is `herdr-dev`; the expected API socket is `R/hc/herdr-dev/sessions/mini/herdr.sock`. Before startup, require its canonical UTF-8 pathname to be at most 100 bytes, below macOS's Unix-socket limit. Discover and verify the actual socket; never guess pane IDs. Set only this temporary Herdr config's `[update] version_check=false, manifest_check=false` and headless size 148×55. Use `/bin/sh`, an empty synthetic home and no inherited shell-startup overrides. Do not set inherited socket/pane/session hints or the macOS daemon-context marker; direct startup does not request a persistent user-service context.
7. This is a narrow future execution exception to the adapter's existing-session-only startup rule, solely for the approved isolated root/session. After startup, require discovery of that running session, matching Unix socket, responding compatible server, expected process/root and selected corrected bundled manifest before any worker control. Every test command uses the corrected executable, its recorded isolation environment, explicit `--session mini` and actual returned IDs. Never retarget the installed/default server. The ordinary adapter still governs planning/final reviewers in `default`.
8. Before starting any private OpenCode backend, check the documented machine-wide configuration directory, managed preference files and every workspace ancestor for non-owned OpenCode config/plugin discovery roots. Inspect existence/source metadata only, not credential contents. Any present or inaccessible non-owned source stops setup before backend startup; a synthetic home alone does not suppress system settings. Then run one **private OpenCode backend**, supervised and bound to `127.0.0.1` on an OS-selected available port; record its actual PID and listening URL. Use the installed version/hash pinned above but a separate synthetic HOME/XDG profile and harmless workspace, not the normal shared service. A clean allowlisted environment excludes inherited API keys, credentials, proxy/provider overrides, OpenCode/Herdr routing hints and automatic context. Do not read, copy or forward real auth files. New temporary global OpenCode config sets `update: "disable"`, the exact selected model, Plan agent permissions `action:"*", resource:"*", effect:"deny"`, and snapshots off. New temporary CLI config keeps default `block-soft-slide`, `mono:false`, footer shown, replay off and reasoning hidden. These are owned fixture settings, not edits to installed/user configuration. Require actual effective config/model/permissions and native backend version to agree; extra configuration, plugins/MCP startup, model unavailability or required authentication stops setup without a prompt or fallback.
9. With the private backend already started per step 8, create the single empty native session through the private API's documented session.create operation and derive its actual ID from the response. Then start `opencode mini --server <verified-loopback-URL> --session <actual-native-ID> --model opencode/deepseek-v4.1-flash-free#max --agent plan --no-replay` in the owned test pane. If the installed Mini parser rejects `#max`, set the documented session/model variant through the private API and verify the effective selection before the prompt; do not silently drop `max`. No `opencode service start/stop/restart/set`, auto-approval flag, login, pairing or persistent integration setup. Verify that Mini uses exactly the created session. No user/assistant prompt is sent during setup. Step 2's credential-free model preflight remains the availability authority; prior successful use in the normal profile is not proof.

## Execution and one-prompt evidence

After verified freeze and the preflight gates above:

1. Capture checkout/status/file fingerprints, installed binary checksums, the normal `default` session/socket/base pane/process/layout and owned process ledger. Inspect this frozen reference and all approved amendments. Stop if user work changed unexpectedly; never reset it.
2. Verify the scope-step-5 build and check evidence and the built binary hash; do not rebuild after those checks. Reuse Skill Lens's 1082-pass/1-skip, 91.16%-coverage, mypy-38-files and Ruff gate evidence only if its product/checker/test inputs and environment remain unchanged; otherwise run the affected four gates under the project rules.
3. Start the two isolated owned servers and one test pane/worker only after the connection/isolation gates. Record binary/config/patch hashes, native backend identity/path, actual session and pane IDs, effective model/variant/Plan/deny-all-tools and initial Herdr idle. Before any prompt, use the private API to require **zero user messages and zero assistant messages** in the new native session. Verify Mini shows a ready prompt and no onboarding/approval modal. Verify the planned live evidence commands (`agent prompt`, `agent wait --until working`, `agent explain`, `agent get`, `agent read`) against installed 0.9.5 help and the idle isolated pane. If Mini unexpectedly has integration-authoritative lifecycle state (`screen_detection_skipped=true`), stop as a mismatched experiment rather than disable an integration or claim screen-rule proof.
4. Before the sole model prompt, verify private API completion endpoints respond and establish the native timestamp unit, resolution and clock relationship. The v2 schema types `time.completed` as a number without promising a unit. Record the coordinator UTC bracket around the empty-session creation, compare its midpoint with native `time.created`, and derive `offset = native_clock - coordinator_clock`; record whether native values are epoch milliseconds or seconds. Require the bracket half-width ≤ 250 ms and `|offset| ≤ 2 s`; otherwise do not prompt (pre-prompt setup blocker). If such a breach is discovered only after the prompt, the run is inconclusive. Define `timing_band` as one native timestamp unit, with a floor of 50 ms for millisecond data and 1000 ms for second data; define `step_threshold = max(250 ms, bracket_half_width)` as the tolerated coordinator wall/monotonic divergence; define `pass_margin = timing_band + bracket_half_width + step_threshold`, so even a tolerated step cannot turn an early return into a pass. Convert native completion to coordinator time as `completed_c = native_completed - offset` before comparing. Immediately before submission and at wait return, record coordinator UTC and monotonic values; if their elapsed values differ by more than `step_threshold`, treat it as a wall-clock step and the run as inconclusive. Missing timestamps or unresolved unit/offset make the run a setup blocker. No raw transcript export or search of old agent sessions.
5. Run the **one** unique-token, no-tool task through corrected Herdr `agent prompt <actual-pane> --wait --timeout 120000` as a supervised background process: “REQUEST_TOKEN <fresh-token>. Do not use tools, delegate, read files or change anything. In about 500 words, explain how a public library lends and returns books, using plain English. Start with BEGIN <fresh-token> and finish with END <fresh-token>.” Record the fresh token in the ledger, plus its PID, exact command, stdout/stderr, exit code, returned status, and the pre-submission and return UTC/monotonic brackets. The pre-submission bracket follows step 4's offset measurement. This is harmless generated text, not repository inspection. No second submission is permitted.
6. Immediately after that supervised submission, and before the prompt wait returns, make one bounded `agent wait <actual-pane> --until working --timeout 10000`, then capture the current detection/visible footer and live `agent explain`/`agent get` evidence. If the prompt wait has already returned before this observation starts, record the run as inconclusive; do not resend, lengthen the prompt, add a delay or increase timeouts. Require real activity, corrected bundled version `2026.10.22.1`, the new footer rule and screen-based authority. Preserve the active stop footer only, not reasoning. No unbounded waits, sleeps or repeated polling.
7. After the original wait returns, obtain the complete matching final text and bounded metadata from the **one private native session**: session.get; session.message.list for all messages; session.active; and a bounded child-session check. Require the wait process to have exited zero with a settled `idle` or `done` result — not `blocked`, `agent_prompt_stalled`, `timeout`, `unknown` or another error. Require exactly one user message containing the fresh token, exactly one matching final assistant message, and no other user/assistant turns. Retain final text, actual model/variant, finish, completed timestamp, outcome, message counts and active/child counts, excluding reasoning/tool arguments/system prompts. The final answer must contain the BEGIN/END markers and substantive explanatory prose; a marker-only or truncated answer fails. A later recovered final answer does not turn an early wait or a failed wait status into a pass.
8. Compare timing in coordinator units using `completed_c`. If `wait_return - completed_c` is negative, the run fails. If it is non-negative but smaller than `pass_margin`, the run is **inconclusive** because the timestamp resolution, bracket uncertainty and tolerated step cannot prove ordering. Only `wait_return - completed_c >= pass_margin` can satisfy the timing criterion. Any timeout, stalled delivery, blocked/approval UI, wrong model, unexpected authority, duplicate or missing delivery, early idle, marker-only answer, offset outside the 2 s limit, drift/step beyond `step_threshold`, or still-active native work prevents a pass. Inspect the same target before any cleanup; never resubmit or start a replacement trial. Preserve the failure/inconclusive evidence and stop affected work. Cleanup may interrupt only the owned active task. Do not select a speculative fix or expand into the full-TUI trace.

### Bounds and rollback

- Server startup/readiness: 30 seconds per owned server. Worker startup: 30000 ms. Working observation: 10000 ms. Sole prompt/wait: 120000 ms. Native HTTP reads: 10 seconds each, bounded page sizes. No timeout increase after failure. The live stage, including observation, has a five-minute ceiling; source download/build time is outside that live-stage bound.
- Stop/rollback means returning to the untouched normal environment, not replacing a binary back. Preserve outputs first; verify native task completion or explicitly cancel that owned task; exit Mini to its shell; close only owned test panes. Stop the exact isolated Herdr server with the corrected binary/isolation prefix, never installed `herdr server stop` against `default`. Terminate only the recorded private OpenCode backend/owned descendants, with 10-second bounded graceful waits; any escalation targets verified owned PIDs only. No global process-name kills or unrelated service commands.
- Require owned task/process termination, no active descendants and removed owned sockets; normal session/base pane/user files/installed binaries must match their baseline. Unexpected writes or uncertain ownership means preserve and report, not blind deletion/restoration.
- After evidence is durably committed/pushed and all owned processes are absent, remove only the exact unused owned execution root after checking no worktree binding/user edits. Retain the pinned source archive and delivered correction unchanged. Planning/final reviewer cleanup follows the existing adapter and preserves the user's base pane/focus.

## Acceptance and reporting

**Live Mini pass requires all:** actual busy footer and working state observed while the prompt wait is outstanding; corrected bundled rule/version with screen authority; the wait process exited zero with a settled `idle`/`done` result after native completion; the timing difference `wait_return - completed_c` is at least `pass_margin`; exactly one token-bearing user message and one matching final assistant message with no other turns; full BEGIN/END markers plus substantive explanatory prose; native succeeded/finish-stop and no active/child task work; isolation/preservation and owned cleanup proved. Both fresh final critics must also return a substantive `pass` on the same frozen evidence package, naming its manifest SHA-256. One `changes_required` or `unverified` blocks acceptance and triggers targeted resolution/escalation; a single pass is not acceptance.

| Result | Required evidence |
|---|---|
| **pass** | Every pass criterion above, including both critic passes. |
| **failure** | Early wait; nonzero/blocked/stalled/timeout/unknown wait status; wrong model or authority; duplicate or missing delivery; marker-only answer; still-active work; isolation or preservation breach. |
| **inconclusive** | Busy snapshot missed; `wait_return - completed_c` later than zero but below `pass_margin`; post-prompt discovery of offset beyond 2 s or bracket half-width over 250 ms; drift/wall-clock step beyond `step_threshold`; unresolved unit; required native metadata unavailable. A pre-prompt offset/bracket breach is a setup blocker, not a run. An inconclusive run is not replayed without owner authorization. |

**Execution complete can instead report failure/inconclusive:** one bounded attempt, honest cause/evidence, no repeated trial or unapproved fix, preserved user environment and completed owned cleanup. Do not relabel negative evidence as validation success. An unverified final review blocks acceptance but does not convert a trial result into a pass.

Before final review, freeze one immutable evidence package: list every result, check, native metadata and cleanup file; build a canonical manifest of sorted relative paths plus each file's SHA-256 in deterministic JSON (excluding raw transcripts and credentials) and record the manifest SHA-256. Include that exact hash and file list in both final-critic briefs and require each report to name it; any evidence change requires a new manifest and both critics to re-review. Two fresh final critics assess that frozen package, not manufacture a passing trial. Capture pre/post fingerprints, actual configured settings, complete matching reports, each critic's own native completion/no-active-work evidence (Herdr idle/done alone is insufficient, especially on the full-TUI OpenCode route), process completion and blocker/suggestion dispositions. Two nonconvergent rounds trigger owner escalation. No product implementation is delegated or authorized.

Deliver allowed plan/evidence only; every authorized Skill Lens commit is pushed to `origin/main` and local/tracking/remote hashes checked under the existing standing delivery rule. Freeze this plan in two commits: the first plan-only, the second reference-only. No build/server/prompt merely because it is committed. The owner's 2026-10-23 go-ahead covers temporary pinned tools/downloads/build, the named isolated Herdr server, credential-free private OpenCode backend, exact diagnostic model/max, one Mini prompt and bounded owned cleanup. Execution follows verified freeze and the preflight gates, not a second user approval, unless a preflight introduces a new credential or compatibility choice. No normal installation, full-TUI instrumentation, formal smoke or upstream publication is bundled.

## Source-backed controls

- Preserved Herdr v0.9.5 archive: `src/config/io.rs:22–39,195–199` (debug namespace and XDG roots; config-path override alone does not relocate all state); `src/session.rs:159–186` (session socket paths); `src/server/headless/bootstrap.rs:8–96` (direct headless startup); `src/platform/macos/bootstrap.rs:10–49` (one-shot daemon context marker and direct-start behavior); `src/config/model.rs:29–45` (`update.version_check`/`manifest_check`). Do not invent environment-variable controls.
- [OpenCode v2 CLI](https://opencode.ai/v2/docs/cli): private `--standalone`/explicit `--server` versus shared-service discovery. Installed 2.1.4 `mini --help`, `serve --help`, `api --help` and `models --help` are command-syntax authority; `models --help` confirms `--standalone`, while `mini --help` confirms `--model`, `--agent`, `--session` and `--no-replay`. The old `/docs/cli/` page is v1 and is not used for v2 flags.
- [CLI settings](https://opencode.ai/v2/docs/cli/config): XDG CLI settings, Mini default spinner/mono/footer and replay controls; hiding tools is presentation, not a permission restriction.
- [Configuration](https://opencode.ai/v2/docs/config), [agents](https://opencode.ai/v2/docs/agents), [models](https://opencode.ai/v2/docs/models): isolated global update control, ordered deny-all permission rules, session-selected models/variants and availability limits. Root model alone does not preserve a variant; verify the actual session selection.
- [Native API](https://opencode.ai/v2/docs/api): `/api/info`, session.create/get, assistant-filtered session.message.list, session.active and parent-filtered session.list. Native assistant finish/completed and session outcome are completion evidence; Herdr idle/done alone is not. Inspect actual response shapes; do not invent fields or rely on old export schemas.

## Review decisions

Round 1 planning reviews ran against draft SHA-256 `af7d0eed50db41e96b3c1937350d5ec748d324f1bd73a83dde0b13ecc90b064d`.

- **Gemini 3.8 Flash High / Plan**, native session `2650ed26-5e7b-4340-b6d9-fc8cbd544b2c`: **pass**, no blockers; 160.50 s bounded wait. Its suggestions were none. Configured model/settings were observed in the native UI; upstream identity remains unverified.
- **OpenCode DeepSeek V4.1 Flash Free / max / Plan**, native session `ses_e9770becfffeaFz02oO5eZpULU`: **changes_required**; 377.46 s bounded wait. The coordinator observed the footer showing DeepSeek/max/Plan; the reviewer did not independently read the `max` variant. Upstream identity remains unverified.
- No reviewer wrote to the checkout: pre/post status, HEAD, 1,305 tracked/untracked file fingerprints, the plan hash and the three original user-file hashes matched. Both reports were read from terminal output; no report file was created by a critic.

Accepted blockers and corrections:

1. **Timing was not operational.** Added native unit/resolution/offset establishment, a two-second clock-offset limit, `timing_band` (one unit, floor 50 ms or 1000 ms), and a pass rule requiring the wait to return at least one band after completion. Inside the band is inconclusive, not pass.
2. **Wait result status was missing.** Pass now requires a zero-exit wait that returns settled `idle`/`done`; `blocked`, `agent_prompt_stalled`, `timeout`, `unknown` or another error is failure/inconclusive.
3. **Exactly-one delivery was asserted, not proved.** Added pre-prompt zero user/assistant counts and post-prompt exactly one token-bearing user message, one matching final assistant and no other turns.
4. **Prompt/observer concurrency was undefined.** The sole prompt wait is now a supervised background process with PID, command, streams, exit status and start/return UTC/monotonic times; the single observer must start before that wait returns or the run is inconclusive.
5. **Preflight order contradicted the build.** Scope steps are now chronological: model availability preflight (step 2) strictly precedes tool download/build (steps 3–5), server startup (step 6) and Mini setup (step 9).
6. **Final critics were not an acceptance condition.** Live pass now requires both fresh final critics to return substantive `pass` on the same frozen evidence; one `changes_required`/`unverified` blocks acceptance and escalates.

Accepted suggestions: explicit pass/failure/inconclusive table; live evidence-command syntax check; substantive answer rather than markers alone; plan-only then reference-only commit wording; fresh token in the ledger; UTC/monotonic brackets; ready-prompt/no-onboarding check. All are incorporated.

Process note: the OpenCode critic used a broad read-only search that surfaced a preserved receipt file outside its named evidence. It reports that no transcript content was used or quoted, and no credentials/raw transcripts were read. The checkout was unchanged. This is recorded as a review-scope deviation, not a plan blocker.

Round 2 targeted follow-up ran against corrected draft SHA-256 `5a592255d41c7dd3fd4b59860d4812c03c665a93c7c462ae1907c81441fd2abe`:

- **Gemini**, same native session: **pass**; all six prior blockers resolved; 50.81 s bounded wait.
- **OpenCode**, same native session: **changes_required**; 231.69 s bounded wait. It conceded prior blockers 2–6 resolved, but found one residual in prior blocker 1 and one new blocker:
  - **Residual:** the measured offset was allowed but never applied. A 1.9 s offset could make an early wait appear late, or a late wait appear early. The offset/step table also contradicted the two-second allowance.
  - **New:** “same frozen evidence” had no manifest or dispatch check, so two critics could review different evidence sets and both pass.
- No reviewer wrote: pre/post status, HEAD, 1,305 file fingerprints, the plan hash and the three original user-file hashes matched.

Corrections:

1. **Offset now applied.** Step 4 derives `offset = native_clock - coordinator_clock` from a creation bracket, requires a bracket half-width ≤ 250 ms and `|offset| ≤ 2 s`, converts completion to `completed_c = native_completed - offset`, and measures coordinator UTC/monotonic before submission and at return. Step 8 requires `wait_return >= completed_c + pass_margin`; drift/step beyond `step_threshold` is inconclusive. The table now names those exact conditions.
2. **Evidence freeze gate added.** Reporting now requires one immutable evidence package, a canonical file manifest and SHA-256, the same hash and file list in both final-critic briefs, each report naming it, and re-review after any evidence change. Each critic's own native completion/no-active-work evidence is also required; Herdr idle/done alone is insufficient.
3. **Narrow suggestions incorporated:** `agent prompt`/`--until working` added to the syntax check; installed `models --help` cited; native session created before Mini starts; duplicate backend-start wording removed; “targeted follow-ups may reuse the affected critic” stated explicitly.

Round 3 targeted confirmation ran against corrected draft SHA-256 `d077406313009bcbadaedb9209a0fbbad4bbe182c755c1fccf0838a9a1b09396`:

- **Gemini**, same native session: **pass**; both corrections verified; 30.96 s bounded wait.
- **OpenCode**, same native session: **changes_required**; 72.34 s bounded wait. It verified the evidence-freeze gate and the offset application, but found one residual: the creation-bracket half-width (allowed up to 250 ms) was not added to the 50 ms pass margin. A wait 50 ms after `completed_c` could still precede true completion by up to 200 ms. It also noted that the step-detection threshold and the pass margin were conflated.
- No reviewer wrote: HEAD was unchanged, the plan was the only changed file (coordinator edits), no files were added/removed, and the three original user files remained unchanged.

Final margin correction:

- `pass_margin = timing_band + bracket_half_width + step_threshold`; acceptance and the timing rule now require `wait_return - completed_c >= pass_margin`.
- `step_threshold = max(250 ms, bracket_half_width)` is used only for wall-clock-versus-monotonic drift; a step beyond it is inconclusive.
- The table now uses `pass_margin` for timing and `step_threshold` for drift/step, removing the threshold mismatch.
- The evidence manifest is specified as sorted relative paths plus per-file SHA-256 in deterministic JSON, excluding raw transcripts and credentials.

Round 4 final narrow confirmation ran against draft SHA-256 `3964f5d1813e56236b7657733ecc4c6dc72f4a63247ecf0e519b55ff2b2f1e20`:

- **OpenCode**, same native session: **changes_required**; 298.06 s bounded wait. It confirmed the bracket half-width is now inside `pass_margin` and the table labels are consistent, but found one remaining hole: a tolerated wall-clock step within `step_threshold` (e.g. 200 ms with a 250 ms threshold) could still turn a slightly early return into a pass. Its suggestions also asked for explicit subtraction order and clearer setup-versus-inconclusive categories.

Final conservative correction:

- `pass_margin = timing_band + bracket_half_width + step_threshold`, so even a maximum tolerated step cannot turn an early return into a pass.
- Step 8 and acceptance now state `wait_return - completed_c` explicitly; the table separates pre-prompt setup blockers from post-prompt inconclusive conditions.
- This is the reviewer's own conservative alternative. It can only make the run more likely to be inconclusive, never more likely to pass.

The owner reviewed this residual and explicitly selected **“Accept and freeze”** on 2026-10-23. The accepted correction is the reviewer's own conservative alternative: it adds the tolerated step to the pass margin, so it can only make a pass harder, never easier. Gemini passed every round it reviewed; OpenCode verified the evidence-freeze gate, the offset application, the bracket margin and the threshold labels, with this final conservative margin as the only residual. No fifth review was authorized or launched.

Status is now Agreed. The two-commit freeze records the plan-only commit and then this exact reference. No build, server, Mini prompt or full-TUI capture has run; execution remains gated on the frozen reference and preflight.

## Execution receipt (append-only)

This receipt records execution evidence only. It does not alter the frozen reference
`1ab5297debea785b2f4de069f18ebb40c578dc44` or its reference commit
`2033b5999dcc37944788aa025570498531b5c9a3`.

- **Preflight passed.** The credential-free private profile listed
  `opencode/deepseek-v4.1-flash-free` with variants `low`, `high` and `max`. No
  user credential was copied. The isolated toolchain downloads matched all
  official SHA-256 values; the accepted patch reproduced all four hashes.
- **Build and offline checks passed.** Corrected debug binary built; 100 detector
  tests passed; Clippy with denied warnings and `cargo fmt --check` passed;
  **29/29** preserved real-CLI cases passed. The Skill Lens health gates were
  reused on unchanged product/checker/test inputs.
- **Live trial failed.** One supervised prompt produced
  `agent_prompt_stalled` (~10.44 s) and the bounded observer timed out
  (~10.30 s). Herdr evaluated the screen as `idle` with no matched rule; the
  corrected bundled manifest was `2026.10.22.1` and screen detection was active.
  The model itself completed successfully in about 9.8 s with a 2,933-byte
  BEGIN/END answer; native metadata shows DeepSeek V4.1 Flash Free `max`,
  `finish: stop`, session `succeeded`, exactly one user and one assistant, no
  active or child work. The wait returned
  `wait_return - completed_c = +309.17 ms`, below the frozen `pass_margin` of
  334.18 ms, so timing alone would be inconclusive; the stalled wait status is
  the failure. The active 2.1.4 footer shape was not captured.
- **Final evidence reviews passed.** Both fresh critics passed the immutable
  22-file evidence manifest `b0e2d809ddc6631d36015928d06d750eb08b0c39ead97417ac0e8593425c4976`.
  Gemini corrected its own model-evidence line; OpenCode's first `done` was
  rejected as premature and its complete report was recovered without a resend.
  Their non-blocking wording suggestions were deferred because the evidence is
  immutable. No reviewer wrote to the checkout or evidence package.
- **Cleanup completed.** The Mini worker and private backend exited, the isolated
  Herdr session stopped, and no owned process remained. The normal `default`
  service, installed binaries, shared OpenCode service and three pre-existing
  user files were unchanged. Base `wG:p1` remains the only focused pane
  (`55` rows, shell PID `45632`). The owned temporary root is removed only after
  the final-review evidence is committed and pushed.
- **Next step requires separate authorization.** The correction did not validate
  live; the exact active-footer shape is unknown. No resend, code fix,
  installation, full-TUI trace or formal smoke was performed or is authorized.
  A diagnostic capture of the active footer or a new correction plan needs the
  owner's explicit approval.
