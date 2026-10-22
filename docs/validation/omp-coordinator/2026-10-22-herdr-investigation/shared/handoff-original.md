# Skill Lens — OMP / Herdr handoff

**Saved:** 20 October 2026. **Status: PAUSED BY THE USER.**

The user wants to sleep and resume tomorrow. This is a handoff, not an instruction to launch workers or continue investigating tonight. Do not interpret historical authorization in the evidence appendix as authorization for a new repair or smoke run.

## 1. Read this first

- OMP/Sol coordination documents are delivered and pushed. T3 Code remains active and was not archived.
- There are three launch approaches but two development workflows: T3 uses its own loops; standalone OMP and OMP inside Herdr share the OMP loops with different worker dispatch.
- **OMP inside Herdr is NOT accepted end-to-end.** Two live trials reached the worker and recovered the right response, but lifecycle waiting failed in different ways.
- The newest blocker is **full OpenCode TUI: `agent prompt --wait` returned idle before later working activity and actual final completion**.
- Do not rerun Mini or repeat either failed trial just to confirm the reported failures. They are established evidence.
- The next investigation was suggested but **not executed**. The user explicitly deferred it. No detection repair, code patch, settings change, installation or extra smoke is authorized by this handoff.
- Preserve the uncommitted evidence update. Do not restore, discard, regenerate or silently commit it.

## 2. Repository and exact saved checkout state

Repository: `/Users/corvette/Documents/Projects Coding/Skill Lens`

```text
branch: main
HEAD:        6b77388003ca8c411b19452d94528344bb8e1007
origin/main: 6b77388003ca8c411b19452d94528344bb8e1007

 M docs/validation/omp-coordinator/2026-10-20/herdr-dispatch.md
?? .path
?? docs/plans/2026-10-19-herdr-omp-coordinator.md
```

The evidence file has **420 uncommitted added lines** relative to HEAD. `.path` and the old coordinator draft are pre-existing user files, not new handoff work. Leave both untouched and unstaged. Recheck the actual checkout when resuming; these are saved observations, not permanent state.

This Desktop file embeds the complete 489-line evidence record as a snapshot in the appendix. It protects the current uncommitted findings without changing or committing the repository.

## 3. Intended setup and approved roles

| Approach | Coordinator | Worker dispatch | Current status |
| --- | --- | --- | --- |
| T3 Code | Sol 6.1 in T3 | T3-native orchestration | Existing workflow remains active and unchanged, apart from routing notices |
| Standalone OMP | Sol 6.1 in OMP | OMP tasks and explicit-model external CLI routes | Sol startup, Sol documentation authors and OpenCode reviewer route exercised |
| OMP inside Herdr | Sol 6.1 in OMP | Herdr worker panes, agent startup, prompt/wait and readback | Documents delivered; live lifecycle acceptance FAILED |

Coordinator: `openai-codex/gpt-6.1-sol`, thinking `high`, no silent fallback.

This coordinator migration's selected reviewer is `opencode/minimax-m3.1-flash-free`, default settings, read-only Plan mode. The user explicitly allowed ONE reviewer for this migration and Sol-authored process documentation. This is not a blanket waiver for future high-risk work. Other implementers/reviewers are selected per session, not permanently assigned. The full-TUI export recorded variant `max` as the effective configured variant; do not invent a separate human selection or claim independently verified upstream identity.

Installed versions observed in live trials: OMP `18.12.3`; Herdr client/server `0.9.5`, protocol `22`; OpenCode `2.0.32` at `/Users/corvette/.opencode/bin/opencode`. Revalidate relevant capabilities when resuming, without upgrading/installing automatically.

## 4. Delivered files and important commits

OMP workflow files:
- `docs/process/omp/README.md`
- `docs/process/omp/planning-loop.md`
- `docs/process/omp/implementation-loop.md`
- `docs/process/omp/herdr.md`

Existing T3 workflow remains at `docs/process/{planning-loop,implementation-loop,council}.md`. OMP routing notices do not replace the T3 policy.

Frozen plans:
- `docs/plans/2026-10-20-omp-side-by-side-coordinator.md`, reference `216cea31cc0ac1c0ad8b1557441bf59aec141031`.
- `docs/plans/2026-10-20-omp-herdr-dispatch.md`, reference `2656a6a1efb687b0d23c9679fdc2222cc18c07b0`.

Delivered implementation commits:
- `84162645f9114a16f745c14a179658783ce85cae`: separate OMP coordination alongside active T3.
- `6b77388003ca8c411b19452d94528344bb8e1007`: Herdr dispatch adapter and OMP-loop routing, explicitly gated on a live check.

Validation folder: `docs/validation/omp-coordinator/2026-10-20/`.
It contains the earlier acceptance and MiniMax plan/final reviews, plus Herdr-specific plan/final reviews and the live evidence record. Those document reviews passed; **they do not override either failed live trial**.

## 5. First trial — OpenCode Mini missed busy detection

The genuine live caller was workspace `wF`, tab `wF:t1`, coordinator pane `wF:p1`. These are historical IDs, NOT targets to reuse tomorrow without fresh discovery.

One fresh owned worker, one prompt, no duplicates:
- Worker: `omp-herdr-smoke-221618`; pane `wF:p2`.
- Startup: `herdr agent start omp-herdr-smoke-221618 --kind opencode --pane wF:p2 -- mini --model opencode/minimax-m3.1-flash-free --agent plan`.
- Token: `herdr-smoke-20261019T221618Z`.
- Session: `ses_ea9c34288ffeXOYWxzPRBNf1tr`.
- `prompt --wait --timeout 120000` failed after about 5.41 seconds with `agent_prompt_stalled`, even while the worker visibly generated the matching response.
- The same worker's completed report was recovered without resubmission.

Authorized read-only diagnosis established:
- Captured Mini busy footer contained `esc stop`.
- Offline `herdr agent explain` classified that captured footer as `idle`, no matching rule, `default_known_agent_idle_fallback`.
- In a separate temporary control fixture, changing ONLY `esc stop` to `esc to interrupt` produced `working`, rule `interrupt_hint_working`, priority `110`.
- Active remote OpenCode manifest version `2026.06.10.1` was reported current, with no local override; its known busy hints did not match the captured wording.
- OpenCode integration was reported current `v13`, but Herdr's documentation explicitly says V2 Mini/headless clients do not run the pane-local TUI lifecycle plugin.
- Therefore a screen compatibility gap is demonstrated. The original live detector's exact internal authority/decision was not captured; do not claim every internal step was proved.

No Mini fix was applied and no Mini rerun occurred. Worker process and owned sibling pane were cleaned up; coordinator and unrelated resources preserved.

## 6. Second trial — full TUI reported activity, but wait returned early

The user separately authorized one bounded full-TUI trial, not a Herdr patch.

Exact exercised route:
- Worker: `omp-full-tui-222755`; pane `wF:p3`.
- `herdr agent start omp-full-tui-222755 --kind opencode --pane wF:p3` launched plain `opencode`, the full TUI, not Mini or headless run.
- Initial Build/DeepSeek state was NOT prompted. Supported session-local controls selected Plan and the exact MiniMax model: `shift+tab`, then `ctrl+p` → “Switch model” → search `MiniMax` → Enter.
- Session export confirmed `agent="plan"`, `providerID="opencode"`, model `minimax-m3.1-flash-free`, variant `max`; no persistent configuration change.
- Token: `herdr-full-tui-20261019T222755Z`.
- Session: `ses_ea9b747a6ffe8CEZTfZL5D4BXT`.
- One launch and one task submission; no duplicate, Mini rerun, native task, standalone relay or increased timeout.

All times below are **UTC on 19 October**; the handoff date is 20 October. Do not reinterpret them as contradictory local dates.

| Observation | UTC time | State sequence |
| --- | --- | --- |
| Server receives prompt | 22:29:28.478226 | Submission begins |
| `prompt --wait` returns idle | 22:29:29.093933 | 18 |
| Herdr subsequently reports working | 22:29:32.281817 | 19 |
| Export records actual assistant completion | 22:29:36.003 | Finished stop / succeeded |
| Recovered matching report and final settled idle | 22:29:39.962950 | 20 |

During sequence 19, live detection explicitly reported `screen_detection_skipped=true` and `screen_detection_skip_reason="full_lifecycle_hook_authority"`.

The full-TUI route therefore supplies lifecycle activity, unlike the Mini screen gap. However, the wait returned about **6.91 seconds before actual completion**. The report's `pass` verdict evaluated only the supplied read-only rule, not the transport/wait contract.

Recovered session export showed a completed matching text response, no tool/delegation events, no attached agents and outcome `succeeded`. These observations do not explain the early sequence-18 idle event. It could involve waiter state binding, reporter ordering or an intermediate transition; **none is established as the cause yet**.

All 1,164 tracked/untracked non-ignored file fingerprints matched before/after the worker, including earlier uncommitted evidence. Seven checked config/integration files were unchanged. Worker exited and its direct children were absent; only its owned pane was closed. Final observed layout retained the coordinator alone, with no owned background work.

## 7. Evidence to preserve

Canonical uncommitted record:
`docs/validation/omp-coordinator/2026-10-20/herdr-dispatch.md`

Live coordinator session:
`01a1563b-7671-73a3-8fc5-a3290a7b017f`

Mini / offline diagnostic receipts:
`/var/folders/tf/jsdyxcts6y72fs98s7wl3dfm0000gn/T/omp-herdr-smoke-20261020-rknrggrh/`

Full-TUI receipts:
`/var/folders/tf/jsdyxcts6y72fs98s7wl3dfm0000gn/T/omp-herdr-full-tui-20261020-v7s2oo1j/`

Important full-TUI artifacts include `prompt-dispatch.txt`, pre/during/after-wait state/UI receipts, `during-prompt-explain.json`, `session-export.json`, `final-state.json`, `final-report.json`, preservation manifests, config receipts and cleanup receipts. The complete appendix lists them precisely.

Temporary directories may disappear. If they still exist tomorrow, preserve a scoped, redacted durable copy before any cleanup; do not delete originals or publish credentials/private config. The embedded appendix preserves the written record, not every raw temporary artifact.

Primary references:
- https://raw.githubusercontent.com/herdrdev/herdr/v0.9.5/docs/next/website/src/content/docs/integrations.mdx
- https://raw.githubusercontent.com/herdrdev/herdr/v0.9.5/docs/next/website/src/content/docs/agents.mdx
- https://raw.githubusercontent.com/herdrdev/herdr/v0.9.5/docs/next/website/src/content/docs/cli-reference.mdx

## 8. Verification already available

- Coordinator document checks: relative links resolve, exact reviewer guard preserved, original OMP policy retained, T3 unchanged; independent MiniMax document reviews passed.
- Latest recorded live-continuation project gates: `uv run pytest --cov=skill_lens` **1082 passed, 1 skipped, 91.16% coverage**, 78.45 seconds; `uv run mypy` clean on 38 source files; Ruff lint and format checks passed (277 files). The skip is the existing case-insensitive-filesystem case.
- Full-TUI continuation changed only append-only evidence. Existing gate results were retained, not redundantly rerun. Passing project gates do not validate Herdr lifecycle waiting.
- This Desktop handoff performs no new live trial, investigation, repair, test run, repo edit, commit or push.

## 9. Tomorrow's recommended next decision

Resume with the agent inside a genuine Herdr-managed OMP pane if live inspection is needed. Do not control Herdr from an ordinary outside session or fabricate `HERDR_ENV`/pane IDs. Re-discover actual caller and resource ownership; old pane IDs are historical.

The next proposed action is a **bounded read-only investigation of the full-TUI early-idle event** using existing evidence and the matching installed/versioned source. The user has NOT authorized or executed it after deciding to pause. Ask for that concrete go-ahead tomorrow; do not restart a generic approval/planning loop for already established facts.

Investigation questions:
1. Which event produced idle/completion sequence 18 for this submission?
2. What submission baseline, session/pane identity and working-state evidence did Herdr's waiter require before returning?
3. Was sequence 18 stale state, an early reporter transition, an intermediate transition or reordered delivery? Correlate recorded evidence before choosing a theory.
4. Which exact component needs the smallest correction: waiter, integration reporter or another proved boundary?
5. What deterministic regression scenario catches this precise premature-return failure?

Return a concrete diagnosis or the exact missing evidence, a minimal repair proposal, a regression scenario, and the exact files/permissions needed. Do not patch installed code, settings or detection rules, restart services, rerun workers, extend timeouts, add sleeps or relax acceptance without separate authorization.

Success eventually requires request-bound observed working activity, correct prompt/wait completion after the actual matching turn ends, substantive matching report, no active descendants, preservation and owned cleanup. A settled badge or worker verdict alone is insufficient. Keep Mini's detection defect separate. Do not claim FULL-TUI-ONLY support merely because full-TUI activity reports exist.

## 10. Starting prompt for tomorrow

```text
Read /Users/corvette/Desktop/Skill-Lens-OMP-Herdr-Handoff-2026-10-20.md.

We paused OMP/Herdr work for the night. Do not rerun either failed smoke,
repair/install/reconfigure anything, alter detection rules, restart services,
commit existing evidence, or claim end-to-end acceptance.

First inspect the current checkout without discarding changes and read the
canonical evidence record. Treat both reported failures as established.
Confirm what remains blocked and propose the bounded read-only investigation
of the full-TUI sequence 18 -> 19 -> 20 ordering. Wait for my go-ahead before
starting that new investigation. Reuse the existing Sol 6.1 coordinator and
selected MiniMax reviewer choices where applicable; do not invent a roster.

If live Herdr inspection is needed, first establish genuine inherited caller
context. Do not reuse historical pane IDs as live targets or fabricate context.
Return findings/results when authorized, not another generic task brief.
```

---

## Appendix — complete uncommitted live evidence snapshot

The content between the markers below is an exact UTF-8 snapshot of the canonical evidence record at handoff creation. It contains historical status sections followed by newer evidence; the newest full-TUI failure is the current operational status. Historical authorizations in this appendix do not authorize new work tonight.

Source: `docs/validation/omp-coordinator/2026-10-20/herdr-dispatch.md`

Source bytes: **30487**; lines: **489**; SHA-256: `09899b046779e614fa8cd071d5b2bfa2f58fc158dc4c958eca8f27a900018aee`.

<!-- BEGIN EXACT HERDR EVIDENCE SNAPSHOT -->

# OMP Herdr dispatch: documentation ready, live check blocked

Frozen amendment: [2026-10-20-omp-herdr-dispatch.md](../../../plans/2026-10-20-omp-herdr-dispatch.md) at `2656a6a1efb687b0d23c9679fdc2222cc18c07b0`; reference-only provenance `c4aa2273f0cae0b54e9c90f3ab0c2baf0bc64a97`. Each pushed to origin/main with full local/tracking/remote equality.

## What changed

- Added the [Herdr dispatch adapter](../../../process/omp/herdr.md) and route-selection links in OMP's entry, planning loop and implementation loop. Genuine Herdr-managed OMP runs use Herdr worker panes/startup/prompts/waits/readback; standalone OMP retains its existing routes. No silent substitution for requested Herdr dispatch.
- Existing Sol identity, user-selected workers, reviewer guard, independent review, read-only product policy and coordinator-owned verification remain intact. T3 process documents, product/tests, settings, authentication, services and installed agents are unchanged.
- Existing `.path` and the untracked 2026-10-19 coordinator draft remain untouched and unstaged.

## Evidence and limits

The caller's inherited context was actually checked:

```text
HERDR_ENV=
HERDR_WORKSPACE_ID=
HERDR_TAB_ID=
HERDR_PANE_ID=
```

Therefore **live verification is blocked**. No Herdr CLI session discovery or pane control was attempted; no environment context was fabricated. Syntax guidance comes from the loaded installed `herdr` skill. Installed CLI help, supported agent kinds, native model arguments, actual detection, prompt submission and report readback must still be verified inside Herdr. No guessed MiniMax startup command is advertised as executable.

Coordinator validation found 18 relative links/anchors resolving and the existing reviewer guard unchanged. No LSP diagnostics apply to Markdown/text-only changes. A no-tools OMP launch checks instruction loading only; it is not a live Herdr dispatch test. Four-gate and smoke outcomes are appended after completion.

## Review and execution receipt

Reuse the migration's selected Sol 6.1 author/coordinator and one OpenCode MiniMax M3.1 Flash Free reviewer, default settings. Independently verified upstream identity is not claimed. [Plan report](./herdr-plan-review.txt): pass, no blockers; OpenCode session `ses_ea9cce0d3ffeyDu2fUNMinRPMB`, completed/exit 0, 35.72 seconds, reported cost USD 0. Review ran through the standalone external CLI, not Herdr; it proves document review only. Expected two reviewer launches (plan and fresh final), no delegated authors or product implementers; Sol makes the small document edits. Billed token counts are unavailable in relay result.json.

## Human step needed for live acceptance

Open a real Herdr shell pane at this repository and run:

```bash
omp --model openai-codex/gpt-6.1-sol --thinking high --no-prewalk @docs/process/omp/README.md
```

Then ask:

> Continue the authorized Herdr smoke from docs/plans/2026-10-20-omp-herdr-dispatch.md and docs/process/omp/herdr.md. Verify the real inherited caller and installed support, run one harmless unique-token task through the selected OpenCode MiniMax reviewer in one owned sibling pane, inspect its matching report and actual completion, preserve unrelated panes, and append evidence here. Stop and ask on missing support or model mismatch; do not install, repair detection or substitute models.

The documentation can be committed, but the requested end-to-end integration remains incomplete until that live check passes. No claim of verified Herdr support is made by this record.

## Coordinator checks

- `uv run pytest --cov=skill_lens`: 1082 passed, 1 filesystem-dependent skip; 91.16% coverage; 79.40 seconds.
- `uv run mypy`: clean, 38 source files.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 277 files already formatted.
- Full gate chain: 80.50 seconds; session output `artifact://40`. Existing unchanged session evidence supplied the pre-edit baseline.
- No-tools instruction-loading smoke: Sol loaded the updated OMP entry and Herdr adapter and correctly reported stopping Herdr inspection/dispatch with unset context, using Herdr workers inside a genuine pane, and preserving T3. Exit 0, 3.63 seconds. This checks instructions only, not Herdr execution.
- Each existing OMP document has exactly one insertion; all original policy lines remain intact. The new adapter's local links resolve; the original guard and user-file fingerprints remain unchanged.

## Documentation acceptance and remaining blocker

MiniMax's fresh [final review](./herdr-final-review.txt) passed with no blockers, session `ses_ea9c98be2ffe4xFREzSFsThQeL`, completed/exit 0, 83.29 seconds, reported cost USD 0. Actual reviewer launches: two, both completed; no active child work remains. Requested/configured model is the selected OpenCode MiniMax alias; upstream identity remains unverified. Final review ran from `2026-10-19T22:09:31.585Z` to `2026-10-19T22:10:54.834Z` (UTC).

All nine scoped pre-review fingerprints and exact repository status matched after review. The checked/reviewed operative document SHA-256 values are retained below; no operative edits followed the gate/smoke run or review. Only append-only evidence was completed afterward.

```text
103f2a044c8ba2feed272e209f648326b9d779580cfe2729731d85553d1af950  docs/process/omp/README.md
3c3fa695f5ea96051ad8f89c6c04e66cc21804675f6e97ae0abfda520de3d7de  docs/process/omp/planning-loop.md
10da25a2dedb5e792eed21247454b82264d92ccc3a486957766521a4363264c4  docs/process/omp/implementation-loop.md
7f5cb6aa83f6aaa0a4536fb246626e8d47933841338f8c3d471e9b36e835a721  docs/process/omp/herdr.md
```

Optional reviewer notes: retained operative hashes and review timestamps for evidence binding; no policy edit required for model settings because the adapter explicitly retains authorized settings and links the entry's exact `--thinking high` launch. Agent-name validation remains the installed CLI/skill's responsibility; templates deliberately require discovered supported names/arguments, rather than claiming unverified runtime execution.

**Accepted documents only; live check still blocked.** The human startup/continuation instructions above are the exact remaining prerequisite. Do not mark end-to-end Herdr orchestration complete until a genuine Herdr-managed OMP session records the successful worker run.

## Live continuation, 2026-10-20: dispatch reached worker; lifecycle check failed

**Outcome: partial live proof, not end-to-end acceptance.** The genuine Herdr
caller, sibling creation, selected model startup, prompt delivery and report
recovery were exercised. The required prompt/wait lifecycle check failed:
`agent_prompt_stalled`, although the original request was visibly generating a
response. No retry, detection repair, installation, model substitution or
standalone relay was attempted. The historical blocked-state evidence above is
unchanged; this section records the new attempt.

### Caller, authorization and configured identities

- Continued frozen plan `2656a6a1efb687b0d23c9679fdc2222cc18c07b0`, live step 6,
  on `main` at `6b77388003ca8c411b19452d94528344bb8e1007`.
- Inherited `HERDR_ENV=1`, workspace `wF`, tab `wF:t1`, pane `wF:p1`.
  `herdr pane current --current` independently resolved that same OMP caller
  and repository working directory.
- Requested coordinator: `openai-codex/gpt-6.1-sol`, thinking `high`.
  Foreground process readback showed the exact authorized launch arguments.
  Active OMP session `01a1563b-7671-73a3-8fc5-a3290a7b017f` recorded
  `model_change` to `openai-codex/gpt-6.1-sol`, `resolvedModelIsFallback=false`,
  and `thinking_level_change` to `high`; runtime version `18.12.3`.
- Herdr client/server `0.9.5`, protocol `22`, endpoint and private protocol
  compatible, no restart needed and no stale server binary.
- Installed OpenCode: `/Users/corvette/.opencode/bin/opencode`, `v2.0.32`.
  `herdr agent` listed kind `opencode`; `opencode models` listed the selected
  `opencode/minimax-m3.1-flash-free`. Installed `mini --help` supported explicit
  `--model` and `--agent`; `debug agents` confirmed primary `plan` mode.
  Discovery also established that `opencode agent list` is unsupported here;
  no installation or configuration change was made.
- Requested worker: OpenCode MiniMax, default settings, fresh Plan session.
  Configured startup footer: `Plan / MiniMax M3.1 Flash Free [max] /
  Default / OpenCode`; process arguments matched the requested alias and mode.
  Worker self-report identified provider `opencode` and model
  `minimax-m3.1-flash-free`. Independently verified upstream identity is
  unavailable for both coordinator and worker.

### Dispatch ledger and observed result

- Expected/actual worker launches: **one/one**; prompt submissions: **one**;
  duplicate submissions, relays and native task dispatches: **zero**.
- Caller layout was 149 columns by 47 rows, so the owned sibling was split
  right in the same tab/cwd using `--current --no-focus`.
  Returned pane `wF:p2`, terminal `term_65e38dcef83b94`; caller remained focused.
  Foreground shell `zsh`, PID `14383`, and its visible prompt were verified
  before startup.
- Worker name `omp-herdr-smoke-221618`; exact startup:
  `herdr agent start omp-herdr-smoke-221618 --kind opencode --pane wF:p2 -- mini --model opencode/minimax-m3.1-flash-free --agent plan`.
  Startup returned `interactive_ready=true`, `idle`, in 3.92 seconds.
  Worker foreground PID was `14422`.
- Unique request token: `herdr-smoke-20261019T221618Z` (UTC).
  The brief contained the verbatim OMP read-only critic guard, frozen reference,
  current HEAD, whole-checkout fingerprint, prior review/gate references,
  selected identity and required report fields. Allowed repository writes:
  **none**. The harmless question supplied the rule “Skill Lens must never
  modify user skills” and asked whether replying without tools complies.
  It explicitly forbade tools, file access, commands, delegation and background
  work. It was not a new review of the process documents.
- Submitted through `herdr agent prompt ... --wait --timeout 120000`.
  Exit 1 after 5.41 seconds:
  `agent_prompt_stalled: agent prompt produced no observed working or blocked state within 5000 ms; current status is idle`.
- Inspected the **same** worker with `agent get`, `agent read` and pane process
  readback, without resending. The UI showed the submitted unique-token brief,
  active response generation and `esc stop`, while Herdr still reported
  `idle`, revision `0`, state-change sequence `8`. This demonstrates that the
  lifecycle observation did not match visible activity in this attempt; its
  underlying cause was not investigated or repaired.
- A later `recent-unwrapped` read recovered the matching final report and the
  restored input prompt. Worker verdict: `pass` **for the supplied rule only**.
  The report explained that a text-only reply does not modify skills, declared
  no tools/files/commands/child tasks/background work, and stated
  `This request is complete`. The UI reported 15.5 seconds for the response.
  It included identity evidence, blockers, suggestions, files at risk,
  concessions and completion. The rendered identity heading appeared as
  `EFFIVE_MODEL`; terminal captures also clipped some right-edge characters.
  These rendering limits are not silently corrected or treated as exact
  machine-readable report output. Worker suggestions were not executed.
- Final OpenCode session receipt:
  `ses_ea9c34288ffeXOYWxzPRBNf1tr`. Billed tokens, cost and independently
  attested upstream identity were not exposed by this route.

### File preservation, receipts and cleanup

Before and after the worker, all **1,164 tracked/untracked non-ignored file
fingerprints** and exact `git status --porcelain` matched. No additions,
deletions or changed file fingerprints were found. Both serialized manifests
had SHA-256:

```text
40eecb36fede21214f453ba353e5acde5b23c3f186d2f9fa26209029b235e37e
```

The unchanged pre/post status contained only the pre-existing `.path` and
`docs/plans/2026-10-19-herdr-omp-coordinator.md`. Product files, tests, target
skills, settings and unrelated panes were not modified by this smoke.

Local raw receipts are retained outside the checkout at:

```text
/var/folders/tf/jsdyxcts6y72fs98s7wl3dfm0000gn/T/omp-herdr-smoke-20261020-rknrggrh/
  brief.txt
  prompt-result.txt
  pre-worker.json
  post-worker.json
  worker-final.json
  worker-state.json
  worker-process.json
  cleanup-shell.json
  cleanup-scroll.json
```

`worker-final.json` retains the full recovered terminal capture, including its
rendering limitations, rather than only the worker's verdict. These are local
temporary evidence paths, not portable or guaranteed permanent storage.

After report recovery, the owned worker was exited using Ctrl+C; the first
keypress displayed “Press ctrl+c again to exit”, then subsequent keypresses
returned to its original foreground `zsh` prompt. PID `14422` and direct children
were absent from process readback. Only owned pane `wF:p2` was closed.
Final layout again contained only focused coordinator pane `wF:p1`, 149 by 47;
the agent list contained only the coordinator. No active owned child work was
reported or observed.

**Remaining blocker:** Herdr's required prompt/wait activity detection did not
recognize this OpenCode MiniMax turn. Prompt transport and report recovery are
proved; reliable lifecycle waiting and end-to-end Herdr dispatch acceptance
are **not**. Any detection investigation, repair or rerun needs a separate
user decision; this continuation did not expand into that work.

### Coordinator gates for this continuation

- `uv run pytest --cov=skill_lens`: **1082 passed, 1 skipped**, 91.16% coverage,
  78.45 seconds. The skip was the existing case-insensitive-filesystem limit.
- `uv run mypy`: passed, 38 source files.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 277 files already formatted.
- Full chain: 79.26 seconds; complete output `artifact://28` in coordinator
  session `01a1563b-7671-73a3-8fc5-a3290a7b017f`.

Only this append-only execution record changed after the worker fingerprint
comparison. No operative policy, code or test change needs a fresh critic wave;
the existing documentation reviews remain unchanged. The failed live lifecycle
check is not waived by the passing project gates. This continuation is recorded
without committing or pushing an end-to-end acceptance claim.

## Authorized read-only detection investigation

After the failed smoke, the user selected “Investigate detection read-only”:
inspect the cause without repairs, installs, settings changes or a worker rerun.
No further worker was started or prompted. The following probes used retained
screen text and the installed diagnostic CLI, not fabricated live activity.

### Findings

1. **The installed screen rules do not recognize Mini's captured busy hint.**
   Recovered the original active-turn capture from coordinator tool-result
   `0fa92920`, including the footer:
   `🯧 esc stop · Plan · MiniMax M3.1 Flash Free [max] · Default / OpenCode`.
   Running `herdr agent explain --file <active-screen.txt> --agent opencode --json`
   classified it as `idle`, `matched_rule=null`,
   `visible_working=false`, and
   `fallback_reason=default_known_agent_idle_fallback`.
   `screen_detection_skipped=false`. The same result held for a minimized
   fixture containing only that captured footer.
2. **A one-phrase offline control isolates the mismatch.** Changed only
   `esc stop` to `esc to interrupt` in a separate temporary fixture.
   The same diagnostic returned `working`, matching
   `interrupt_hint_working`, priority `110`. This is a diagnostic control,
   not a live fix or proof of a repaired installation.
3. **The active manifest has no Mini-specific working hint.** Running-server
   inventory and local replay both identified
   `remote:/Users/corvette/.local/state/herdr/agent-detection/remote/opencode.toml`,
   version `2026.06.10.1`, reported `current`, with
   `local_override_shadowing_remote=false`. Its working rules recognize
   `esc to interrupt`, `ctrl+c to interrupt`, `press esc to interrupt`,
   an OpenCode/interrupt line pattern, or four progress-bar glyphs.
   None recognizes the captured `esc stop` footer. No update or reload was run.
4. **A current integration does not provide V2 Mini lifecycle reporting.**
   `herdr integration status` reported OpenCode integration `current (v13)`.
   Herdr's versioned integration documentation explicitly says V2 Mini and
   headless clients do not run the TUI plugin and do not provide its lifecycle
   reporting. The installed server entrypoint's `ownsLocalLifecycle()`
   (`plugins/herdr-agent-state.js:121–142`) retains the legacy `run`/`--mini`
   gate, not a V2 `mini` subcommand case. Thus “integration installed” does not
   establish lifecycle coverage for the client used in this smoke.

### Evidence and limits

The read-only server log independently places startup at
`2026-10-19T22:16:23.237Z`, recognition of foreground OpenCode PID `14422` at
`22:16:23.696Z`, prompt receipt at `22:16:48.541Z`, and prompt failure at
`22:16:53.919Z`. Original tool evidence shows visible generation after that
failure while the reported state-change sequence remained `8`.

Ranked hypotheses were: Mini lacks lifecycle reports and its busy hint misses
screen rules; a stale/local rule override; or a transient observation window.
Offline replay directly demonstrates the first hypothesis's screen mismatch.
Current/no-override inventory does not support a local override explanation.
A transient timing issue alone cannot explain deterministic misclassification
of the captured busy screen.

No live `agent explain` was captured before the worker was closed. Offline
replay uses retained `recent-unwrapped` text, not the exact original live
bottom-buffer snapshot; the current running-server manifest matches the replay
version, but the original authority selection was not directly recorded.
Therefore the **screen compatibility gap is demonstrated**; every internal
runtime step of the failed turn is not claimed proven.

Diagnostic fixtures and JSON results are retained in the same external
temporary evidence directory recorded above:

```text
active-screen.txt
active-bottom.txt
active-explain.json
manifest-inventory.json
busy-footer.txt
captured-mini-busy.json
supported-hint-control.txt
wording-control-only.json
final-checkout.json
```

Sources:

- [Herdr 0.9.5 agent-state and detection behavior](https://raw.githubusercontent.com/herdrdev/herdr/v0.9.5/docs/next/website/src/content/docs/agents.mdx)
- [Herdr 0.9.5 OpenCode integration and V2 Mini limitation](https://raw.githubusercontent.com/herdrdev/herdr/v0.9.5/docs/next/website/src/content/docs/integrations.mdx)
- [Herdr 0.9.5 CLI reference](https://raw.githubusercontent.com/herdrdev/herdr/v0.9.5/docs/next/website/src/content/docs/cli-reference.mdx)
- Installed active manifest, integration lifecycle guard, read-only integration
  status, running-server manifest inventory and original coordinator receipts.

No repair, install, configuration write, server reload/restart, live input,
new worker or further model execution occurred during this investigation.
Only temporary diagnostic artifacts and this append-only evidence were written.
The four project gates above remain applicable: no code, tests or operative
policy changed, and no redundant gate run was performed.

**Next decision:** separately authorize a bounded remedy before another live
check. Candidates are a verified full-TUI route with lifecycle reporting, or
an upstream correction to Mini screen detection. Neither route is implemented,
verified as a fix, or authorized by this investigation. End-to-end live
acceptance remains blocked; the evidence update is uncommitted and unpushed.

## Authorized full-TUI trial: activity reporting works; wait returns too early

**Result: not accepted end-to-end.** The user explicitly authorized execution
of one full-TUI smoke without another plan or approval request. The full
OpenCode TUI ran the exact MiniMax model in Plan mode and Herdr observed its
working state through lifecycle reports. However, `agent prompt --wait`
returned an early idle event about 6.91 seconds before the actual turn ended.
This fails the requested wait-correctness check. No operative workflow
amendment or full-TUI-only support claim was made.

### Capability discovery and exact exercised startup

- Rechecked inherited `HERDR_ENV=1`, workspace `wF`, tab `wF:t1`, caller
  `wF:p1`. `pane current --current` and foreground-process readback resolved
  that same genuine OMP caller and repository cwd.
- Coordinator session evidence still recorded
  `openai-codex/gpt-6.1-sol`, no fallback, thinking `high`; foreground arguments
  matched. Upstream identity remains unverified.
- Herdr client/server `0.9.5`, protocol `22`, compatible, no restart needed.
  OpenCode `/Users/corvette/.opencode/bin/opencode`, `v2.0.32`.
  Root help and generated completions did not expose root `--model` or
  `--agent` flags; no such flags were invented. The exact selected alias
  remained available in `opencode models`; `debug agents` confirmed Plan.
  Installed `opencode2` was only a wrapper executing the same binary.
- Created one right sibling, same tab/cwd, `--current --no-focus`.
  Returned pane `wF:p3`, terminal `term_65e3906b7c84f5`; foreground `zsh`
  PID `17328` and its prompt were confirmed before startup.
- Exact startup:
  `herdr agent start omp-full-tui-222755 --kind opencode --pane wF:p3`.
  Herdr launched `argv=["opencode"]`, the actual full TUI, with foreground PID
  `17437`. Startup returned `idle`, `interactive_ready=true`, in 3.82 seconds.
  No installation was required.
- Initial UI showed Build/DeepSeek. **No prompt or model request was submitted
  in that state.** Used the UI's displayed controls: `shift+tab` switched to
  Plan; `ctrl+p` opened Commands; Enter selected the visible “Switch model”
  command; typed `MiniMax` into the model selector; its single matching
  MiniMax M3.1 Flash Free entry was selected with Enter.
- Before submission, the actual footer read
  `Plan · MiniMax M3.1 Flash Free Default / OpenCode · max`.
  The later exported session independently recorded `agent="plan"`,
  `providerID="opencode"`, model `minimax-m3.1-flash-free`, variant `max`.
  No permanent config was edited to select the model or mode.

### Single request and lifecycle evidence

- Worker `omp-full-tui-222755`; fresh session
  `ses_ea9b747a6ffe8CEZTfZL5D4BXT`.
- Exactly one launch and one task submission; no Mini rerun, alternative
  worker, duplicate prompt, relay, native task or increased timeout.
- Request token: `herdr-full-tui-20261019T222755Z`.
  The brief included the exact OMP read-only critic guard, frozen reference,
  inspected HEAD/fingerprint and requested identity. The task supplied only
  the read-only rule and forbade tools, commands, repository/skill access,
  writes, tests, delegation and background work.
- Submission used `herdr agent prompt omp-full-tui-222755 <brief> --wait --timeout 120000`.
  Coordinator tool job: `bg_7`; submission did not return a lifecycle error.
  Nevertheless, the observed state order below prevents acceptance.

| Observation | UTC time | Herdr state / sequence |
| --- | --- | --- |
| Before prompt | Pre-submission receipt | `idle`, state-change sequence `16`, no session reported yet |
| Server receives prompt | 2026-10-19 22:29:28.478226 | `agent.prompt` starts |
| Prompt/wait returns | 2026-10-19 22:29:29.093933 | `idle`, state-change and completion sequence `18`, same new session |
| Direct read after that return | 2026-10-19 22:29:32.281817 | `working`, state-change sequence `19`, same session |
| Session export records actual final idle | 2026-10-19 22:29:36.003 | Assistant finished `stop`; session outcome `succeeded` |
| Recovered report and actual settled state | 2026-10-19 22:29:39.962950 | `idle`, state-change and completion sequence `20` |

While state `19` was working, live `agent explain --json` returned:

```json
{
  "agent": "opencode",
  "state": "working",
  "screen_detection_skipped": true,
  "screen_detection_skip_reason": "full_lifecycle_hook_authority"
}
```

Thus full-TUI working detection was directly observed, unlike the established
Mini screen mismatch. The prompt/wait response's completion sequence `18`
preceded both this observed activity and actual completion sequence `20`.
The server log independently records the prompt returning in about 0.616
seconds, while the exported assistant turn completed at `22:29:36.000`.
The exact cause of the early idle event was not diagnosed or repaired.

A recent-history read attempted during working was correctly rejected with
`agent_not_idle`, because alternate-screen history recovery requires idle.
No prompt was resent. After actual idle, `recent-unwrapped --lines 220`
recovered the matching report and restored input prompt. A later 250-line
receipt retained the report. No report-file fallback was needed.

### Recovered worker report

The following preserves the recovered wording with terminal wraps joined:

```text
REQUEST_TOKEN: herdr-full-tui-20261019T222755Z

EFFECTIVE_MODEL: requested opencode/minimax-m3.1-flash-free / configured minimax-m3.1-flash-free (per harness-declared model: MiniMax M3.1 Flash Free) / settings default / mode Plan / evidence: session-declared model metadata only; upstream provider identity unverified.

VERDICT: pass — A worker replying without tools complies with the evaluated rule because "never modify user skills" is satisfied by performing no writes at all; a no-tool reply performs zero modifications, and the task scope explicitly permits zero file writes. Evidence is behavioral (no tools invoked, no files touched), so the rule holds regardless of upstream model identity.

BLOCKERS: none.

SUGGESTIONS: none required for this smoke; if a future trial needs stronger evidence, capture a tool-call log proving zero filesystem-mutating calls rather than relying on reply content alone.

FILES_AT_RISK: none — no repository file was created, edited, moved, deleted or renamed; no writes of any kind occurred in or outside the checkout.

CONCEDED: upstream model identity remains unverified (declared metadata only, no provider handshake performed); prior Mini mismatch is not re-tested per instruction and is treated as established; reference doc docs/plans/2026-10-20-omp-herdr-dispatch.md was not opened, per instruction that references are not permission to read files; HEAD 6b77388003ca8c411b19452d94528344bb8e1007 and pre-trial manifest SHA-256 23e7763fdd5a7946ddf7a82e15f1b5d33d0ec0287ff3b0de23113de7fb617e15 are reported as supplied and were not independently verified by file access.

COMPLETION: complete. No tools, commands, repository or skill access, file writes, delegation, child tasks, network calls, or background work were used; no tests were executed and no test execution is claimed.
```

This `pass` evaluates the supplied rule, **not the Herdr wait operation**.
The worker's “no writes” wording describes its tool behavior; OpenCode's own
normal session/history persistence is not a promise of zero runtime disk writes.
The UI reported 7.1 seconds and 64.2 tokens/second. Coordinator-side
`opencode session export --sanitize <session-id>` confirmed one user turn,
an assistant response containing only a text item, `finish="stop"`, no attached
agents, and final `idle`/`outcome="succeeded"`. No tool or delegation event
appeared in that export. Export reported cost `0`, input tokens `16668`,
output `465`, reasoning `172`, cache-read `2416`, cache-write `0`; these are
runtime-reported counts, not independently verified billing.

### Preservation, evidence and cleanup

Before startup and after the worker, all 1,164 tracked/untracked non-ignored
file fingerprints, HEAD and exact repository status matched. This includes
the already-uncommitted evidence from the earlier Mini attempt and diagnosis.
Both serialized manifests had SHA-256:

```text
23e7763fdd5a7946ddf7a82e15f1b5d33d0ec0287ff3b0de23113de7fb617e15
```

The pre-existing evidence edit, `.path` and the untracked 2026-10-19 draft
were preserved. Checks of seven installed OpenCode config/integration files
after UI selection and after the turn matched; their recorded modification
times all predated this trial. No config edit, integration install, detection
change, service restart/reload or timeout increase was performed.

Raw receipts are retained outside the checkout at:

```text
/var/folders/tf/jsdyxcts6y72fs98s7wl3dfm0000gn/T/omp-herdr-full-tui-20261020-v7s2oo1j/
```

This contains `pre-trial.json`, `post-trial.json`, `config-receipt.json`,
`brief.txt`, `prompt-dispatch.txt`, `pre-prompt-state.json`,
`pre-prompt-ui.json`, `during-prompt-state.json`, `during-prompt-explain.json`,
`during-prompt-ui.json` (including its working-state read error),
`after-wait-state.json`, `after-wait-ui.json`, `session-export.json`,
`final-state.json`, `final-report.json`, `cleanup-shell.json` and
`cleanup-scroll.json`. These are local temporary receipts, not guaranteed
permanent or portable storage. The exact prompt-return response and live
observations are also retained in coordinator session
`01a1563b-7671-73a3-8fc5-a3290a7b017f`.

After actual completed-turn evidence was obtained, Ctrl+C exited the owned
full TUI to its original foreground `zsh` prompt. PID `17437` and its direct
children were absent from process readback. Only owned pane `wF:p3` was
closed. Final layout contained only focused coordinator `wF:p1`, 149 by 47;
the agent list contained only the coordinator. No active owned background work
was reported or observed.

Only this evidence section was appended afterward. No product, test or
operative workflow changed; the existing four passing project gates remain
applicable and were not redundantly rerun. No commit or push was made.

**Concrete remaining prerequisite:** authorization for a separate bounded
investigation of the full-TUI early-idle/lifecycle ordering, followed by any
explicitly approved remedy and a separately authorized new live check.
Reliable request-bound waiting is not established by this run. The conditional
review/freeze amendment is not started because the trial did not meet every
acceptance check. Mini detection remains unchanged and its correction remains
separate from this full-TUI result.

<!-- END EXACT HERDR EVIDENCE SNAPSHOT -->
