# Two-Surface Orchestration Proposal — T3 Code + cmux/Herdr

**Status:** Draft proposal for external review. NOT a frozen plan. NOT reviewed under the
project's planning loop yet. NOT committed to the repository.
**Date:** 2026-10-17
**Prepared by:** the coordinator session running inside cmux (OpenCode harness) at Hazem's request.
**Prepared for:** Hazem and review agents of any model family, so everyone can agree on the same terms.
**Scope:** Adding a second orchestration surface (cmux + Herdr) to the Skill Lens development
process, running side by side with the existing T3 Code surface, under one shared process contract.

---

## 0. How to read and review this document

- This document describes **every proposed change** for adding the cmux + Herdr workflow:
  the concept, the new document architecture, per-file change specifications, exact proposed
  text for the key passages, the machine setup, the verification plan, the risks, and the
  open questions.
- It is written to be **self-contained**: a reviewer who has never seen the related
  conversation can understand and judge it.
- **Verified facts** are labeled as such with dated evidence (Appendix B lists the commands).
  Everything else is a **proposal**.
- This document does **not** start the project's planning loop or implementation loop. When
  Hazem authorizes the migration, its agreed content feeds a frozen migration plan
  (`docs/plans/<date>-two-surface-orchestration.md`) created through the existing
  planning-loop procedure (draft → review → two-commit freeze), and only then are repository
  files edited.
- Reviewers are asked to answer the questions in **§10 (Open questions)**. Everything else
  can be reviewed freely, but §10 is the agreement checklist.

---

## 1. Outcome (the target end state)

1. Skill Lens supports **two orchestration surfaces** with **one shared contract**:
   - **T3 Code surface** — what exists today: native T3 orchestration, `delegate_task`,
     task ledger, runtime modes, live model catalog.
   - **cmux + Herdr surface** — new: the human works in the cmux terminal; coding agents live
     in Herdr panes; the coordinator drives workers through the `herdr` CLI.
2. Opening T3 Code runs the T3 workflow; opening cmux + Herdr runs the Herdr workflow.
   Both obey the same roles, the same review principles, the same risk levels, the same
   verbatim read-only guard, the same two-commit freeze, and the same four gates.
3. The coordinator "Sol" on the Herdr surface runs **via Hermes** (personal assistant harness,
   kind `hermes` in Herdr) instead of the Codex harness. The model identity stays "Sol"
   (OpenAI family), so the council's family-diversity rules keep working unchanged.
4. The T3 surface is **not retired, not archived, not changed in behavior**. T3 process
   documents are restructured (mechanics moved into a surface profile file), never deleted
   or frozen as history.
5. Each frozen plan declares its surface once (`Surface:` field); every task runs
   **end-to-end on one surface**; surfaces never mix inside one task's review rounds.

---

## 2. User decisions already made (2026-10-17)

These are recorded as settled requirements from Hazem; reviewers should treat them as fixed
unless a genuine correctness problem is found.

| # | Decision |
|---|---|
| D1 | Herdr surface coordinator = **Sol via Hermes**. T3 surface coordinator stays **native Codex** (`codex` provider). |
| D2 | **One task end-to-end on one surface**, with a `Surface:` line in the plan header. Agreed. |
| D3 | **Both surfaces are kept indefinitely.** No retirement, no archive of T3 process documents for now. ("No retiring the plan for now, I will keep using both.") |

---

## 3. Current state

### 3.1 The process today (T3 Code surface)

The active process lives in `docs/process/` and is entirely T3-native:

| File | Role | T3-specific content today |
|---|---|---|
| `docs/process/planning-loop.md` | How a request becomes a frozen plan | Start prompt names Sol/Codex; Step 3 dispatches critics via `delegate_task` with `runtimeMode=full-access`, `interactionMode=plan`; Done-When checks `hasPendingChildRuns=false` |
| `docs/process/implementation-loop.md` | How a frozen plan becomes committed work | Start prompt; Step 1 verifies checkout binding; Step 2 dispatches Antigravity via `delegate_task(providerInstanceId=antigravity, model=gemini-3.8-flash-high, …)`; Step 5 preflights Full access; Step 7 cleanup checklist uses T3 task states |
| `docs/process/council.md` | Roles, guard, permissions, lifecycle, report schemas, risk levels | Roster with T3 provider IDs; §2 Full-access/runtime modes and `t3_thread_configuration` preflight; §3 "T3 Task Lifecycle and Ledger" (`delegate_task`, `taskId`/`childRunId`/`childThreadId`, `hasPendingChildRuns`, `task_cancel`, terminal states); §4 evidence channels mention `t3_thread_configuration` |
| `docs/process/profiles/machine-profile.md` | Environment facts for this Mac | T3 build `0.0.46-nightly.20261010.2935`; native provider IDs; permission-mode mappings; asar source paths; T3 worktree/thread tools (`t3_worktree_status`, `t3_thread_read`, `t3_thread_launch`, `create_threads`) |
| `docs/process/profiles/project-profile.md` | What "correct" means in this repo | **Surface-neutral** — no T3 references. (Verified; unchanged by this proposal.) |
| `AGENTS.md` | Repo entry rules | Points at both loop files by path; **never names T3**. Paths stay the same, so no edit is needed (same conclusion as the Orca→T3 migration). |

Historical records (`docs/plans/`, `docs/validation/`, `docs/archive/`) are untouched. The
current documents have no Herdr or cmux references anywhere (verified by grep across `*.md`).

### 3.2 Verified machine facts (2026-10-17)

Evidence commands are listed in Appendix B; this is a snapshot — live discovery wins at
implementation time.

**cmux** (the terminal the human works in):

- Installed and running; app at `/Applications/cmux.app`; version `cmux 0.65.2 (111) [9d01f956c]`.
- The current session is inside cmux (environment carries `CMUX_*` variables: workspace/tab/
  surface IDs, socket path `~/.local/state/cmux/cmux.sock`).
- cmux ships CLI-agent wrapper shims (claude, codex, pi, hermes, amp) active in this
  environment — interaction with Herdr-started agents must be checked in the pilot (§8.2).

**Herdr** (the agent runtime that will run inside cmux):

- Installed: `herdr 0.9.5` at `~/.local/bin/herdr`; config `~/.config/herdr/config.toml`;
  logs `~/.config/herdr/herdr.log`.
- Server is **not currently running** (`no herdr server is running at ~/.config/herdr/herdr.sock`);
  session list shows the `default` session `stopped`. It starts when the user runs `herdr`.
- Command families available: `workspace`, `tab`, `pane`, `agent`, `worktree`,
  `notification`, `session`, `integration`, `api`, `machine`, `server`.
- Supported agent kinds (24): `pi|claude|codex|gemini|cursor|devin|agy|cline|omp|mastracode|opencode|copilot|kimi|kiro|droid|amp|grok|hermes|kilo|qodercli|qwen|letta|maki|muse`.
- Herdr's agent-facing contract (`herdr --skill`) requires the driving agent to run **inside a
  Herdr pane** (`HERDR_ENV=1`) and to refuse control from outside. This is why the coordinator
  itself must live in a Herdr pane on this surface.
- Integration status today (`herdr integration status`):

| Kind | Status |
|---|---|
| `pi` | **current (v9)** |
| `opencode` | **current (v13)** |
| `hermes` | **current (v5)** |
| `omp` | current (v10) |
| `codex` | **outdated (v9 < v10)** — update before use |
| `antigravity-cli` | **outdated (v3 < v4)** — update before use |
| `grok` | **outdated (v2 < v3)** — update before use |
| claude, copilot, devin, droid, kimi, kilo, qodercli, qwen, cursor, mastracode | not installed |
| letta | experimental, not installed |

**Hermes** (the proposed coordinator harness for the Herdr surface):

- Installed: `Hermes Agent v0.22.2 (2026.9.24) · stable · local d923a5eb487a`; git install at
  `~/.hermes/hermes-agent`; Python 3.14.7.
- **Already configured with the Sol model**: default `gpt-6.1-sol-900k`, provider `custom`,
  base URL `http://127.0.0.1:8787/w/hermes/v1`, `api_mode: codex_responses`. Whether that
  proxy process is running was not probed; it is a dependency to record and verify (§7).
- Herdr ↔ Hermes state plugin installed and current (`~/.hermes/plugins/herdr-agent-state`, v5),
  so Herdr receives Hermes' `idle`/`working`/`blocked` states directly (not screen-scraped).
- Plugin directory also contains personal plugins (`caveman_native`, `homeassistant`) and a
  left-over `orca-status` (historical; harmless).

**T3 Code** (the existing surface): still installed (`t3` binary at `/opt/homebrew/bin/t3`;
T3 Code Nightly app referenced by the machine profile). Untouched by this proposal.

### 3.3 Already true vs. must be verified in a pilot

**Already true (verified above):** Hermes is a supported Herdr kind; its state and resume
integrations are current; Hermes is configured with the Sol model; T3 is fully intact; the
project has no existing Herdr/cmux coupling to break.

**Must be verified by the pilot (§8.2) before the Herdr surface is declared live:**
1. Starting Sol (`kind hermes`) in a Herdr pane, and the coordinator driving `herdr`
   commands from inside its pane.
2. The wave-dispatch pattern (§5.4 H4; §10 Q2).
3. `blocked` detection on a real approval dialog and the read-only-approval policy (§5.4 H6).
4. Long-transcript readback for full-screen agents (opencode) and the temp-file fallback (§5.4 H5).
5. cmux wrapper-shim interaction with Herdr-started agents.
6. Session resume after a Herdr server restart for the kinds in use.
7. The Sol proxy (port 8787) is running, and the model identifier is reconciled (§10 Q3).

---

## 4. The two-surface model

### 4.1 Terms (glossary — the "same terms" to agree on)

| Term | Meaning |
|---|---|
| **Surface** | The tool environment a task runs on: `t3` (T3 Code) or `herdr` (cmux + Herdr). |
| **Surface profile** | A document that defines one surface's mechanics (dispatch, waiting, permissions, worktrees, evidence). New concept; two files. |
| **Shared contract** | The surface-neutral rules: roles, guard, report schemas, risk levels, escalation, freeze, gates. Lives once, in `council.md` + the two loop files. |
| **Coordinator** | Sol. Plans, dispatches, verifies, judges, commits. Never writes product code. |
| **Implementer** | Antigravity. Sole writer of product code and tests. Never reviews, never commits. |
| **Critic / reviewer** | Independent reviewer agent (pool: pi, grok, opencode) dispatched read-only per review round. |
| **Wave** | All critics for one review round, dispatched before any waiting begins. |
| **Dispatched agent** | A worker created for a task: a T3 child task, or a Herdr agent in a pane. |
| **Settle state** | Herdr lifecycle states where an agent is ready for input: `idle`, `done`. `blocked` means it needs an answer. |
| **Owned pane / owned worktree** | Something the coordinator (or the task itself) created. Only owned resources may be closed/removed. |
| **Integration** | Herdr's per-agent plugin that reports state and enables session resume after a server restart. |
| **Ledger / receipt** | The record of every dispatch: identities, launch arguments, outcomes. T3 uses task IDs; Herdr uses pane IDs + agent names. |
| **HERDR_ENV gate** | Herdr's rule that an agent may drive Herdr only from inside a Herdr pane (`HERDR_ENV=1`). |

### 4.2 The rule set

- **R1 — Surface declaration.** Every frozen plan declares `Surface: t3` or `Surface: herdr`
  in its header. The migration plan that implements this proposal is itself executed on the
  **T3** surface (the one whose rules are already validated), unless the user says otherwise.
- **R2 — End-to-end rule.** One task runs entirely on one surface: planning reviews,
  implementation dispatch, final reviews, cleanup. No mixing.
- **R3 — Switching rule.** Changing a plan's surface mid-task is a plan amendment (stop
  in-flight work; re-dispatch fresh rounds under the target surface; existing authorization
  rules apply). It is never silently done.
- **R4 — Concurrency rule.** One task per checkout at a time (existing fingerprint and
  "no concurrent checkout mutation" rules stay). Parallel work across surfaces is allowed
  only in separate worktrees.
- **R5 — Fallback rule.** If a surface is unavailable (server down, quota, broken
  integration), the coordinator stops and presents options; a fallback requires user
  authorization and fresh dispatches — never continuation of in-flight rounds.
- **R6 — Authority rule.** The frozen plan + surface profile are contract; `machine-profile.md`
  is environment facts (updated as facts change, same governance as today). The shared contract
  is written once and never duplicated per surface.
- **R7 — Honesty rule.** Neither surface provides enforced read-only critics: restraint is
  instruction-based plus detection. Never claim otherwise.
- **R8 — Freshness rule.** Live discovery wins over snapshots. Surface facts are re-verified
  after upgrades (T3 nightly builds; Herdr updates; CLI versions).

### 4.3 What stays identical across surfaces (the guarantee)

The loop **step sequence**, role separation and independence, family-diversity rules, the
verbatim read-only guard, fingerprint detection around critic work, report schemas
(`EFFECTIVE_MODEL`, `VERDICT`, `BLOCKERS`, …), risk levels and expected task counts, the
two-round non-convergence escalation, the two-commit freeze, the four gates, authorization
rules, and all product guarantees (read-only product, provenance, snapshot discipline).

**Honest limit:** the exact commands differ by surface (that is the point of surface
profiles). "Same mechanism" means *same contract and same step sequence*, with mechanics
supplied by the active profile — not two copied documents, which would drift apart.

---

## 5. Proposed document architecture

### 5.1 File map: before → after

| Path | Change | Nature |
|---|---|---|
| `docs/process/council.md` | Restructure: shared contract stays; T3 mechanics move out to the T3 profile; pointers added | Edit |
| `docs/process/surfaces/t3.md` | **New** — complete T3 mechanics profile (moved + clarified, semantics unchanged) | New file |
| `docs/process/surfaces/herdr.md` | **New** — complete Herdr mechanics profile | New file |
| `docs/process/planning-loop.md` | Start prompt parameterized by surface; Step 3 dispatch generalized + profile pointers; Done-When checks per surface | Edit |
| `docs/process/implementation-loop.md` | Same treatment; Step 1 surface readiness; Step 7 per-surface cleanup/accept | Edit |
| `docs/process/profiles/machine-profile.md` | Restructured into two environment sections (T3 / Herdr+cmux) + surface facts; mechanics removed to profiles, evidence stays | Edit |
| `docs/archive/orca-process-2026-10-10/README.md` | Optional: one-line active-workflow pointer update ("T3 Code and cmux + Herdr") | Edit (optional) |
| `AGENTS.md` | None — verified it only references loop paths that do not change | No change |
| `docs/process/profiles/project-profile.md` | None — verified surface-neutral by design | No change |
| Product code, tests, registry, specs, packaging, historical records | None | No change |

### 5.2 `council.md` — section-by-section change spec

**Intro.** "The council is the independent review system **for Skill Lens**. It runs on one of
two supported surfaces — T3 Code or cmux + Herdr — declared per task in the plan." (Today it
says "in T3 Code".)

**§1 Roster and roles.** Roles unchanged. Changes:
- The roster table gains a surface column or note: Coordinator Sol — T3 surface: native
  `codex` provider (`gpt-6.1-sol`); Herdr surface: **Hermes agent (`kind hermes` in a Herdr
  pane) running the Sol model** through the local proxy. Implementer (Antigravity) and critic
  pool (pi, grok, opencode) keep their identities on both surfaces: T3 native providers vs
  Herdr CLI kinds.
- "USER selects critic models AND settings from the live T3 catalog (`orchestrator_capabilities`)"
  becomes surface-parameterized: **user selects per session from the active surface's live
  sources** — T3: `orchestrator_capabilities` catalog; Herdr: installed kinds + each CLI's
  own model setup. The ask-once procedure, reuse-within-session, and no-silent-substitution
  rules stay verbatim in spirit.
- Family rules unchanged. Note added: changing the coordinator *harness* (Codex → Hermes)
  does not change the coordinator's model family; if the Sol proxy's underlying model were
  ever swapped to another family, §1's family rules must be re-checked.

**§2 Read-only protection and permissions.** Split into:
- **Shared, unchanged:** the verbatim guard text (byte-identical), the honesty rules
  (instruction-based restraint; worktrees are not a security boundary; never claim an
  enforced read-only guarantee), fingerprint detection (`git status --porcelain` + SHA-256
  before/after), the preserve-inspect-stop rule for unexpected critic edits, and the
  standing authorization statement re-expressed for both surfaces (T3: runtime modes;
  Herdr: per-CLI launch flags — see profile H9 and §10 Q1).
- **Moved to profiles:** T3 runtime-mode mechanics and `t3_thread_configuration` preflight,
  escalation-denial example, supervised-mode contrast, automatic-approval-review notes →
  `surfaces/t3.md` T4; every Herdr equivalent (no modes; per-CLI flags; HERDR_ENV preflight;
  blocked-dialog policy) → `surfaces/herdr.md` H9/H6.
- A two-line pointer block ends each subsection: "T3: surfaces/t3.md §T4 · Herdr: surfaces/herdr.md §H9".

**§3 Task lifecycle and ledger.** Retitled "Task lifecycle and ledger (per surface)". Split:
- **Shared, new wording:** dispatch discipline (one wave before waiting; never duplicate a
  worker; never treat a wait timeout as cancellation or authorization); identity retention
  (keep the dispatch identity of every worker for the receipt); fresh review rounds with
  isolated context; question handling (answer deliberately; never blind-retry); cleanup
  (only owned resources; worktrees only if owned); terminal-state discipline ("a settled or
  quiet UI state is not acceptance; acceptance requires recorded outcome + terminal evidence
  for the active surface").
- **Moved to profiles:** all concrete mechanics. T3 (`surfaces/t3.md` T3): the current
  `delegate_task` JSON example, `taskId`/`childRunId`/`childThreadId` ledger,
  `hasPendingChildRuns`, terminal states (`completed`/`failed`/`cancelled`/`interrupted`),
  `task_cancel`, top-level thread rules. Herdr (`surfaces/herdr.md` H2–H8).
- Pointers per subsection.

**§4 Report formats.** Schemas unchanged (both loops). `EFFECTIVE_MODEL` evidence channels
become surface-parameterized:
- T3: unchanged (task receipts, `t3_thread_configuration`, provider banner).
- Herdr: recorded `agent start` response + the exact native arguments + the agent's own
  model indicator readback (e.g., Hermes `/status`) + integration version; unverified is
  still an honest value.

**§5 Risk levels and escalation.** **Unchanged entirely** (verified surface-neutral).

**§6 Review efficiency without weaker acceptance.** Mostly unchanged. Adds:
- Herdr notes: briefs are submitted via `agent prompt` (bracketed-paste capable), not
  `pane run` (macOS canonical line-input limit); long transcripts use
  `--source recent-unwrapped` with the temp-file report fallback pre-authorized in the brief.
- The execution-receipt definition generalizes from "task launches" to "dispatch launches
  (T3 tasks / Herdr agents), including failed/interrupted ones".

### 5.3 NEW `docs/process/surfaces/t3.md` — content spec

This file is **the current T3 mechanics, preserved**. Explicitly listed so reviewers can
confirm nothing is lost:

- **T1 Preconditions:** active Full-access verification loop (as today: caller-mode preflight
  via `t3_thread_configuration`, `runtime_mode_escalation_denied`, composer activation steps).
- **T2 Dispatch:** the `delegate_task` call shape (target provider/model/options, role,
  runtimeMode, interactionMode, mode=async, stable `clientRequestId`), returned
  `taskId`/`childRunId`/`childThreadId`, heartbeat rules, no workspace override.
- **T3 Ledger and lifecycle:** ledger tracking rules; `waiting_for_children` vs
  `result_available`; `hasPendingChildRuns`; terminal states; `task_cancel` semantics;
  bounded `task_status` readback; "never continue reviews through the backing child thread".
- **T4 Permissions:** reviewer tasks (`runtimeMode=full-access`, `interactionMode=plan`) and
  implementer tasks (`full-access` + default interaction) under Hazem's standing
  authorization; supervised-mode contrast; automatic approval review limits.
- **T5 Model selection:** critic selection from the live catalog (`orchestrator_capabilities`),
  ask-once procedure, fallback rules.
- **T6 Workspace/worktree mechanics:** `t3_worktree_status`, `t3_thread_read`,
  `t3_worktree_handoff`, `t3_thread_launch`/`create_threads` rules (moved from
  machine-profile §5 — mechanics live in profiles now).
- **T7 Evidence:** T3 rows of the `EFFECTIVE_MODEL` channels.
- **T8 Cleanup:** task terminal checks + owned-worktree cleanup (as today).

All semantics identical to the current documents; this is a move plus explicit organization,
not a behavior change. The migration reviewers must diff the profile against the current
texts and confirm nothing was dropped (acceptance item, §8.1).

### 5.4 NEW `docs/process/surfaces/herdr.md` — content spec

The full Herdr mechanics, organized in stable subsections (H1–H13) so council and loops can
point precisely.

**H1 — Preconditions and entry.**
- The human opens cmux, starts or attaches Herdr (persistent server; a named session is
  allowed). The server keeps panes running when the client detaches; pane **processes** do
  not survive a machine restart, and layout/session resume depends on integrations.
- The coordinator pane: Sol runs as a Herdr agent (`kind hermes`) in a pane named e.g. `sol`.
  The human talks to Sol there; cmux rings / Herdr notifications surface attention needs.
- Coordinator preflight before any dispatch: confirm `HERDR_ENV=1` (inside a Herdr pane);
  load the Herdr skill (`herdr --skill`); check `herdr status`; confirm integration currency
  for every kind it will start (`herdr integration status`).
- Never stop the Herdr server from an active session; use a named test session
  (`herdr --session <name>`) for pilots or experiments.

**H2 — Coordinator harness (Sol via Hermes).**
- Launch (exact working command to be recorded after the pilot): split a pane, then
  `herdr agent start sol --kind hermes --pane <pane-id> [-- …]`; model comes from the Hermes
  config default (`gpt-6.1-sol-900k` via the local proxy at `127.0.0.1:8787`; identifier to
  be reconciled, §10 Q3).
- Hermes features kept **off the review path**: Hermes' own `delegate_task` subagents,
  messaging gateway, and cron are not used for council work — all dispatch goes through
  Herdr panes so every worker is visible, guarded, and cleanable. (Revisiting this needs an
  explicit authorization and process change.)
- Project context: Hermes reads `AGENTS.md`; the coordinator follows the loop documents and
  this profile.
- Evidence: Hermes `/status` + launch arguments + `herdr agent get` identity.

**H3 — Layout and dispatch (one worker).**
1. Choose direction (wide pane → right, narrow/tall → down); keep focus:
   `herdr pane split --current --direction right --cwd "$PWD" --no-focus`;
   read the new pane ID from `.result.pane.pane_id`.
   - For isolated work: create/reuse a worktree first (`herdr worktree create|open`) and use
     its path as `--cwd`. Only owned worktrees; `--trust-repository` only after the user has
     verified the repository.
2. Start the agent: `herdr agent start <name> --kind <kind> --pane <id> [--timeout <ms>] [-- <native args>]`.
   - Names: `[a-z][a-z0-9_-]{0,31}`, unique among live agents.
   - `agent start` requires an available shell pane at its prompt; it never creates layout.
   - On `agent_not_ready` (blocked during startup): do not prompt; inspect with
     `agent get`/`agent read`; wait for `idle`.
   - Native args (model/options/flags) are passed only after `--`.
3. Submit the brief: `herdr agent prompt <name> "<brief>" --wait --timeout <ms>` (single
   worker), honoring the wave rules in H4 for critic waves.
   - `agent prompt` rejects an already-`blocked` agent (`agent_blocked`) without sending
     input — inspect the dialog instead (H6).
   - `agent_prompt_stalled` / `timeout` do **not** prove the prompt was not delivered;
     inspect before any retry. Never blind-resend.

**H4 — Wave dispatch and waiting (critic rounds).**
- The shared rule is unchanged: dispatch the whole wave before waiting.
- Because `agent prompt --wait` blocks until settle, the wave needs one of these patterns
  (pilot decides; default recommendation first):
  - **(a) Parallel submissions — recommended:** run each `herdr agent prompt <name> … --wait
    --timeout <ms>` as a background job (one per critic), each writing its JSON result to a
    temp file outside the repo; collect all results; then wait/collect per agent.
  - **(b) Submit-then-observe:** `agent prompt` without `--wait` for every critic, then per
    agent confirm activity (`agent wait <name> --until working --timeout <short>`) and then
    the settle wait. Known hazard: a very fast round can settle before we observe `working`;
    a timed-out activity wait must trigger inspection, not a resend.
  - **(c)** Serial `prompt --wait` per agent (correct but slower; fallback).
- Waiting semantics: `agent wait <name> [--until blocked] --timeout <ms>`; default settle
  states are `idle`, `done`, `blocked`. `idle` and `done` both mean "ready for input" — they
  are not proof the desired turn completed. `unknown` is not completion. Standalone
  `agent wait` returns immediately if the state already matches — the activity confirmation
  in H4a/H4b exists to avoid false settles.
- Antigravity and Grok can be idle while background tasks/subagents continue: a settled
  state is never accepted as proof of finished work for those kinds; acceptance requires
  the recorded outcome (H5).
- A wait timeout **never** cancels a worker and **never** authorizes a replacement — the
  shared rule carries over unchanged.

**H5 — Reading reports and evidence.**
- Read: `herdr agent read <name> --source recent-unwrapped --lines <N>` (preferred for logs
  and transcripts); `visible` for the viewport; `--format ansi` only when styling is evidence.
- Full-screen agents (opencode, claude) render in the alternate screen; long reads use the
  agent's own scroll interface automatically. If a completed response cannot be recovered,
  use the pre-authorized fallback: ask the agent to write its report as Markdown to a
  temporary directory **outside the repository** and reply with the path; read that file.
  The temp-file fallback must be stated in the brief so it needs no mid-round negotiation.
- Receipt fields per dispatched agent (Herdr analog of T3 task IDs):
  agent name; kind; pane ID; exact native args; submit result JSON; wait results; read
  output (or artifact path); fingerprints before/after the critic wave; final state;
  cleanup confirmation. Round labels serve as the `clientRequestId` analog for receipts.
- `EFFECTIVE_MODEL` evidence channels: launch args (requested) + `herdr agent get`/banner
  readback (configured/confirmed) + `/status`-type model indicator where the CLI offers one
  (confirmed) + integration version; unverified remains honest.

**H6 — Blocked states and approvals.**
- `blocked` means Herdr recognized an approval or question UI. Inspect first
  (`agent get`, `agent read`), never answer blind.
- Policy for critic tasks: allow routine **read** approvals; **deny** any request to write,
  edit, install, format, commit, or regenerate — that is the guard, enforced at the dialog.
  Answer via `herdr agent send-keys <name> esc|enter|…` deliberately.
- Anything consequential (scope, permission widening, ambiguous dialogs) escalates to the
  user in Sol's pane. Approval interactions are never bypassed.
- For the implementer: approvals follow its user-selected autonomy flags (H9); anything that
  would exceed the frozen plan stops and returns to the coordinator.

**H7 — Cancellation and interruption.**
- Cancel a worker: `herdr agent send-keys <name> ctrl+c`, or close the owned pane
  (`herdr pane close <pane-id>`). Confirm the stop via `agent list`/`get` and record the
  outcome as failed/interrupted in the receipt.
- A Herdr server restart or machine restart interrupts panes; layout is restored and
  sessions resume only where integrations are current. After any interruption: verify state;
  if a worker's outcome cannot be confirmed, record the interruption and re-dispatch a
  **fresh** round (never resume a previous critic's conversation).
- `herdr agent explain <name>` diagnoses wrong-looking detection states.

**H8 — Cleanup.**
- Close only panes the task created; remove only worktrees the task created (after checking
  bindings and uncommitted edits, as today).
- Verify `herdr agent list` shows no leftover task agents; never touch user-owned panes,
  workspaces, or the server itself.

**H9 — Permissions and autonomy flags.**
- Herdr has **no permission modes**. The autonomy envelope is set by each CLI's own launch
  flags/config at `agent start`. Therefore:
  - The T3 standing "Full access" authorization is re-expressed as a **per-CLI, per-role
    autonomy mapping** (coordinator / implementer / critics), verified from each CLI's own
    `--help` and a controlled test, approved once by the user, recorded in
    `machine-profile.md` §3B. No flag is baked into the profile before it is verified.
  - Critics: most restrained configuration compatible with reading the repository and
    producing a report; the guard remains the behavioral contract; fingerprints remain the
    detection net.
  - Implementer: write-capable per its user-selected configuration.
  - Coordinator: shell-capable (it must run `herdr` commands).
- Honesty rules unchanged: nothing here is an enforced sandbox; worktree/pane isolation is
  not a security boundary.

**H10 — Model selection procedure (Herdr).**
- Ask-once per session: the coordinator presents installed kinds (`herdr agent` group) and
  each candidate CLI's configured model options; the user selects model + settings per role.
- Choices are passed as native arguments at `agent start` (or via each CLI's own config) and
  recorded in the receipt; no silent defaults or substitutions; quota fallbacks only per the
  shared fallback rules (user authorization).

**H11 — Human attention (cmux + Herdr).**
- cmux: notification rings / unread badges on the coordinator pane when Sol needs the human;
  optional `cmux notify` hooks; the sidebar shows branch/directory context. Herdr:
  notifications (`herdr notification show`) and the Herdr sidebar state roll-up. The exact
  wiring is optional polish, decided at setup (§7), and recorded.

**H12 — Failure modes and recovery.**
- Server not running / stopped: start or attach `herdr`; never let the coordinator start a
  server restart mid-task without user awareness.
- Version drift (client vs server after updates): check `herdr status` before relying on a
  feature; a missing method is not permission to stop or upgrade a server.
- Integration outdated/not installed for a kind: update with
  `herdr integration install <kind>` **before** starting that kind for real review work.
- Detection confusion: `herdr agent explain`; never treat `unknown` as success.

**H13 — Safety rules (always on).**
- `--no-focus` for background work; never steal the human's keyboard.
- Parse IDs from JSON responses; use `--current` or explicit pane IDs; never derive IDs from
  sidebar order.
- Close only owned resources; never `herdr server stop` from an active session; named test
  sessions for experiments; `--trust-repository` only after the user verified the repo;
  `herdr machine add/remove` only when the user asks.

### 5.5 `planning-loop.md` — step-by-step change spec

- **Start-Planning prompt:** gains the `Surface:` line (see §6.2 for exact proposed text).
- **Step 3 (Review), point 3:** "Verify the coordinator's active Full access mode" becomes
  surface-specific: T3 → unchanged (`t3_thread_configuration` preflight; see profile T1);
  Herdr → "confirm the coordinator is inside a Herdr pane, integrations are current, and the
  per-role launch mapping was user-approved" (profile H1/H9).
- **Step 3, point 4:** "Use `delegate_task` with …" becomes "Dispatch the whole wave per the
  active surface profile (T3: profile T2; Herdr: profile H3–H4); keep the shared rules
  (fingerprints before dispatch; dispatch all before waiting; stable per-round labels)".
- **Step 4 (Resolve), point 5:** "fresh targeted tasks" gains "(T3 task / Herdr agent in a
  fresh pane — never a resumed conversation)".
- **Step 5 (Freeze):** unchanged, except the plan header template gains `Surface:` (§6.1).
- **Done When checklist:** per-surface formulations (§6.4).

### 5.6 `implementation-loop.md` — step-by-step change spec

- **Start-Implementation prompt:** gains the `Surface:` line (§6.3).
- **Step 1 (Baseline):** adds surface readiness checks. T3: as today. Herdr: `HERDR_ENV=1`
  confirmed; `herdr status`; `herdr integration status` for the kinds in this task; the Sol
  proxy reachable; worktree decision per profile H3/T6. Gates (four) unchanged; run on
  baseline as today.
- **Step 2 (Dispatch one phase):** the `delegate_task(providerInstanceId=antigravity …)`
  sentence becomes "Dispatch the sole implementer (Antigravity) per the active surface
  profile (T3: profile T2; Herdr: profile H3, with the per-role launch mapping recorded)".
  The brief table ("Commit owner: Sol; workers do not commit") is unchanged.
- **Step 4 (Verify before review):** unchanged (pure verification discipline). Note added:
  under Herdr, the coordinator runs gates in its own shell; worker self-reports still do
  not substitute.
- **Step 5 (Review independently):** dispatch wording per profile (T3: T2/T3; Herdr: H3–H5);
  the "supply the complete diff through one source" rule stays — the diff artifact goes to
  a temp location outside the repo, which works on both surfaces.
- **Step 6 (Rework):** "Dispatch fresh targeted follow-ups to affected critics" gains the
  same never-resume clause as planning Step 4. Two-round escalation unchanged.
- **Step 7 (Accept and commit):** checklist items 6 and the cleanup paragraph get per-surface
  formulations (§6.4). Commit procedure unchanged.

### 5.7 `machine-profile.md` — restructure spec

New principle: **machine-profile holds environment facts and evidence only; process
mechanics live in surface profiles.** New structure:

- **§1 Surfaces on this Mac**
  - §1A T3 Code: build facts (recheck after upgrades), provider IDs (unchanged content).
  - §1B cmux + Herdr: cmux version; Herdr version; config/log paths; socket path; session
    policy (which session the project uses — decided at setup, §7); how the coordinator pane
    is started; HERDR_ENV facts.
- **§2 Models and providers**
  - §2A T3 native catalog facts (unchanged).
  - §2B Herdr kinds + per-CLI model selection facts; **Hermes = coordinator harness** with
    the Sol model via the local proxy (`127.0.0.1:8787`, `codex_responses`), identifier
    reconciliation note.
- **§3 Permission modes and preflight**
  - §3A T3 observed modes + escalation-denial evidence (facts kept; mechanics move to
    profile T4).
  - §3B Herdr: per-CLI autonomy flag mapping (per role) — populated only after §10 Q1 is
    answered and verified; evidence dates + CLI versions; "static observations, not
    adversarial proof".
- **§4 Provider policy and source mapping evidence**
  - §4A T3 mappings (unchanged, historical evidence disclaimers kept).
  - §4B Herdr: per-CLI flag evidence collected at setup (each CLI's `--help` + controlled
    test), with versions and dates.
- **§5 Workspace and worktree handling**
  - §5A T3 tools (facts/evidence only; mechanics to profile T6).
  - §5B Herdr: `herdr worktree list|create|open|remove`, pane `--cwd`, ownership/cleanup
    rules, `--trust-repository` rule.
- **§6 Integrations and attention (new)**: the integration-status table + update procedure;
  cmux notification/attention wiring; the cmux shim interaction note.

### 5.8 Files that do not change (and why)

- **`AGENTS.md`** — verified: it references the two loop files by unchanged path and never
  names T3 or a surface. No edit needed. (Same conclusion as the Orca→T3 migration.)
- **`docs/process/profiles/project-profile.md`** — verified surface-neutral: it states what
  "correct" means (gates, read-only guarantee, provenance, snapshots) and does not mention
  T3. It stays the shared project truth for both surfaces.
- **Product code, tests, snapshots, registry, `SKILL_LENS_SPECIFICATION.md`,
  `FULL_SCREEN_TUI.md`, packaging** — no surface touches these. The four gates and snapshot
  discipline are unaffected.
- **Historical records** — `docs/plans/*`, `docs/validation/*`, `docs/archive/*` stay
  byte-unchanged as history. (One optional exception below.)

### 5.9 Optional minor item

`docs/archive/orca-process-2026-10-10/README.md` §"Active Workflow Pointers" says the active
workflow is "driven through T3 Code". With two live surfaces, that line would better read
"driven through T3 Code and cmux + Herdr". It is a one-line pointer in an archive README, not
a historical record copy — propose updating it; reviewers may veto.

---

## 6. Proposed exact text (for reviewer agreement)

### 6.1 Plan header with the Surface field

```markdown
# Plan: <name>
Status: Draft | Agreed
Surface: t3 | herdr
Authorization: <existing user instruction, or "pending">
Reference: <pending until Step 5>
Risk and review: <council §5 level, reason, reviewer questions>
Expected child tasks: <planning + implementation + final review; before corrections>
```

`Surface:` is fixed at freeze; changing it later follows R3 (plan amendment).

### 6.2 Start-Planning prompt (parameterized)

```text
Act as coordinator Sol. Surface: <t3 | herdr>.
Read AGENTS.md §4, the relevant specification, source, tests, and findings.
Follow docs/process/planning-loop.md and the active surface profile
(docs/process/surfaces/<t3|herdr>.md). Choose the risk level and review scope,
resolve findings, and freeze docs/plans/<dated-slug>.md before implementation.
```

(T3 sessions run this under Codex `gpt-6.1-sol`; Herdr sessions run it under Sol-in-Hermes
inside a Herdr pane. Roster lines below the prompt stay as today.)

### 6.3 Start-Implementation prompt (parameterized)

```text
Act as coordinator Sol. Surface: <t3 | herdr>.
Implement <phase> from docs/plans/<dated-slug>.md @ <frozen_commit_hash>.
Verify authorization, frozen amendments, checkout binding, and baseline gates.
Follow docs/process/implementation-loop.md and the active surface profile
(docs/process/surfaces/<t3|herdr>.md). Dispatch the sole implementer Antigravity
per that profile, verify the final files, review by risk, then commit.
```

### 6.4 Done-When / acceptance checklist replacements

Planning loop "Done When" final item:

- T3: `All child tasks terminal with hasPendingChildRuns=false; cleanup follows council §3.` (unchanged)
- Herdr: `Every dispatched agent has a recorded outcome; no task-owned pane or worktree remains; herdr agent list shows no leftover task agents; the server is left running.`

Implementation loop Step 7, checklist item 6 and cleanup:

- T3: `Every child task is terminal (completed, failed, cancelled, or interrupted) with hasPendingChildRuns=false.` (unchanged)
- Herdr: `Every dispatched agent's outcome is recorded (report read, or interruption recorded); only task-owned panes/worktrees were closed/removed; no user-owned resource was touched.`

---

## 7. Operational setup (machine, outside the repository)

Done when the migration is authorized and implemented; none of this is a repo edit. All
items are user-present actions.

1. **Update Herdr integrations before real use:** `codex` (v9→v10), `antigravity-cli`
   (v3→v4), `grok` (v2→v3). Confirm `pi`, `opencode`, `hermes` stay current.
2. **Confirm the Sol proxy** (`127.0.0.1:8787`, Hermes provider `custom`) is running and
   meant to stay up; record it as the coordinator's dependency in `machine-profile` §2B.
3. **Reconcile the Sol model identifier:** docs say `gpt-6.1-sol`; Hermes config says
   `gpt-6.1-sol-900k`. Record the truth (§10 Q3).
4. **Agree and verify the per-CLI autonomy flag mapping** per role (§10 Q1).
5. **Record the exact coordinator launch command** (pane split + `herdr agent start sol
   --kind hermes -- …`) after the pilot confirms it.
6. **Session policy:** decide which Herdr session the project uses (the `default` session or
   a dedicated one), and who starts the server. Record in `machine-profile` §1B.
7. **cmux wiring:** check the wrapper-shim interaction with Herdr-started agents; decide
   whether to wire `cmux notify`/Herdr notifications for Sol's attention needs (§5.4 H11).

---

## 8. Verification and acceptance (for when this is implemented)

### 8.1 Document-level acceptance

1. All files in §5.1 exist with the specified structure; all cross-references resolve.
2. **Grep sweeps** (proposed, checkable):
   - T3-only mechanics terms (`delegate_task`, `hasPendingChildRuns`, `t3_`,
     `runtimeMode`, `interactionMode`, `orchestrator_capabilities`) appear only in
     `surfaces/t3.md`, the designated `machine-profile` fact sections, and historical
     records — never in the shared council text or the loops.
   - Herdr-only mechanics terms (`herdr `, `HERDR_ENV`, pane IDs) appear only in
     `surfaces/herdr.md` and the designated `machine-profile` sections.
3. **No-loss review of the T3 profile:** reviewers diff `surfaces/t3.md` against the current
   documents and confirm every current T3 rule survives with unchanged semantics.
4. **No-duplication review:** confirm the shared contract exists once (no forked copies of
   the guard, schemas, or risk levels).
5. The four gates run on baseline and final tree (docs-only change, but the project rule
   stands). Snapshot/golden files are untouched.
6. The final commit stages only the allowed paths listed for the migration plan.

### 8.2 Herdr pilot exercises (before declaring the surface live)

Run in a **named test session** (`herdr --session <name>`) so the daily session is untouched:

1. Start the server; `herdr status`; confirm `HERDR_ENV=1` inside the coordinator pane.
2. Split a pane from the coordinator; start a `pi` critic; submit a trivially safe
   guard-style review brief; observe states; read the report; close the pane. This validates
   H3–H5 and the chosen wave pattern (single-worker first, then a 2-critic wave).
3. Trigger a real approval dialog deliberately; verify `blocked` detection; verify the
   inspect-then-answer policy (allow read, deny write) via `send-keys`.
4. Repeat a readback test with `opencode` (full-screen) and exercise the temp-file fallback.
5. Start Sol via `hermes` in a pane; ask it to run `herdr agent list` itself — proving the
   coordinator can drive Herdr from inside.
6. Restart the server; confirm layout restore and session resume for `hermes`, `pi`,
   `opencode`.
7. Record the entire pilot as the first Herdr execution receipt (round labels, outputs,
   fingerprints, cleanup).

### 8.3 Rollback

Revert the migration commits (docs-only) — the T3 surface is untouched throughout, so the
project's process remains fully valid at every point. Pilot actions create no repository
changes; they only start/stop panes in a test session.

---

## 9. Risks, failure modes, mitigations

| # | Risk | Mitigation |
|---|---|---|
| 1 | Dual-surface docs drift (two mechanics sets go stale unevenly) | Shared contract written once; profiles are the only mechanics; R6; grep sweep acceptance |
| 2 | False settles on Herdr (permissive waits; `unknown`; fast rounds) | Activity confirmation before settle waits (H4); timeout ⇒ inspect, never resend; `unknown` never = success |
| 3 | "Settled" implementer (Antigravity/Grok) still running background tasks | Settled state never equals acceptance; acceptance requires the recorded outcome (H4/H5) |
| 4 | Long transcripts unrecoverable (full-screen agents) | `recent-unwrapped` + pre-authorized temp-file report fallback (H5) |
| 5 | Sol proxy single point of failure (coordinator cannot run) | Record dependency; surface-unavailable rule (R5): stop, present options, no silent fallback |
| 6 | Per-CLI autonomy mapping wrong or unverified | §10 Q1: verify from each CLI + controlled test; populate machine-profile §3B with evidence; critics stay most-restrained |
| 7 | Screen-detection/detection confusion for some kinds | `herdr agent explain`; integrations current before use; pilot items |
| 8 | cmux wrapper shims interfering with Herdr-started agents | Pilot item; if broken, start the Herdr server outside the shim environment or adjust |
| 9 | Cross-surface continuations / mixed evidence (ledger confusion) | R2/R3/R5; fresh rounds only; receipts are per-surface |
| 10 | Concurrent use of both surfaces on one checkout | R4; separate worktrees; existing fingerprint rules |
| 11 | Migration itself changing the execution contract | It goes through the planning loop: High risk proposed; 2 plan critics (different families) + implementer + 2 final critics (§10 Q7) |

---

## 10. Open questions for agreement

**Q1 — Per-CLI autonomy flags (the Herdr counterpart of the standing Full-access
authorization).** Proposal: verify each role's flags from each CLI's own `--help` plus a
controlled test; the user approves the coordinator/implementer/critic mapping once; record in
`machine-profile` §3B with dates and versions; critics get the most restrained reading
configuration. *Reviewers: is this the right principle, and is anything missing (e.g., a
required "deny writes" test)?*

**Q2 — Wave-dispatch pattern.** Candidate patterns in §5.4 H4. Proposal: pilot decides
between (a) parallel background submissions, (b) submit-then-observe, (c) serial fallback;
the acceptance criterion is "all wave prompts submitted before any settle wait; no false
settle accepted". *Reviewers: agree the criterion; flag any hole in (a)/(b).*

**Q3 — Sol model identity and coordinator evidence.** Reconcile `gpt-6.1-sol` vs
`gpt-6.1-sol-900k`; confirm the family stays OpenAI (so §1 family rules are untouched);
define Hermes `EFFECTIVE_MODEL` evidence (launch args + `/status` readback + integration
version). *Reviewers: confirm sufficiency.*

**Q4 — Surface pointers inside `council.md`.** Proposal: shared text stays; each mechanics
subsection ends with "T3: surfaces/t3.md §… · Herdr: surfaces/herdr.md §…". *Reviewers:
confirm, or propose an alternative that avoids duplication.*

**Q5 — `Surface:` semantics.** Fixed at freeze (§6.1); repeated in the execution receipt;
change = amendment (R3). *Reviewers: confirm.*

**Q6 — Pilot scope.** Minimum: `pi`, `opencode`, `hermes` drive-through, blocked-dialog
test, resume test, shim check. Later kinds (`agy`, `codex`, `grok`) only after integration
updates. *Reviewers: add or remove items?*

**Q7 — Risk classification of the migration plan itself.** Proposed: **High** (permissions +
execution contract + review system). *Reviewers: confirm level and the resulting review
waves.*

---

## 11. Out of scope / deferred

- No changes to product code, tests, snapshots, registry, specifications, packaging,
  `AGENTS.md`, or `project-profile.md`.
- No retirement of either surface; no archive of T3 process documents (D3). Revisiting
  retirement later is allowed; it is simply not part of this change.
- No changes to T3 mechanics; no attempt to run Hermes inside T3 (until/unless the T3 live
  catalog is checked and the user asks).
- Hermes' internal delegation, messaging gateway, and cron stay off the review path (§5.4 H2).
- No concurrent dual-surface work on one checkout (R4); separate worktrees only.
- No release/publish steps; no CI changes.

---

## Appendix A — T3 ↔ Herdr mechanics mapping

| Concern | T3 surface | Herdr surface |
|---|---|---|
| Dispatch | `delegate_task` (provider/model/options, modes, role, async, request label) | `pane split` → `agent start <name> --kind … -- <args>` → `agent prompt <name> …` |
| Identity / ledger | `taskId`, `childRunId`, `childThreadId` | Pane ID (`w1:p1`) + unique agent name (+ coordinator round label) |
| Waiting | Async wake / `task_status`; `waiting_for_children` → terminal | `agent wait` / `prompt --wait`; states `idle`/`done`/`blocked`; `unknown` ≠ success |
| Reading results | Task result payload | `agent read --source recent-unwrapped`; temp-file fallback |
| Cancellation | `task_cancel` (+ bounded readback) | `send-keys ctrl+c` / close owned pane; confirm and record |
| Permissions | `runtimeMode` + `interactionMode`; caller-mode preflight | No modes; per-CLI launch flags; HERDR_ENV gate; blocked-dialog policy |
| Model selection | Live catalog (`orchestrator_capabilities`), ask-once | Kinds + per-CLI model setup, passed as native args, ask-once |
| Workspace / worktree | `t3_worktree_status/read/handoff`, thread rules | `herdr worktree list/create/open/remove`; pane `--cwd`; ownership rules |
| Evidence | Task receipts + `t3_thread_configuration` + banner | `agent start` response + native args + banner/`/status` + integration version |
| Cleanup proof | All tasks terminal + `hasPendingChildRuns=false` | Outcomes recorded; no leftover task agents/panes; owned worktrees removed |
| Human attention | T3 app UI | cmux rings/badges + Herdr notifications |
| Coordinator harness | Codex (`gpt-6.1-sol`) | Sol via Hermes (`kind hermes`), local proxy |

---

## Appendix B — Evidence log (2026-10-17)

Commands were run read-only; outputs summarized. Live discovery wins at implementation time.

| Command | Result summary |
|---|---|
| `herdr --version` | `herdr 0.9.5` |
| `herdr --help` | Command families incl. `workspace`, `tab`, `pane`, `agent`, `worktree`, `notification`, `session`, `integration`; config `~/.config/herdr/config.toml`; logs `~/.config/herdr/herdr.log` |
| `herdr --skill` | Agent contract: requires `HERDR_ENV=1`; refuses control from outside; panes/agents semantics; `agent start` needs an available shell pane; safe-close and server rules |
| `herdr agent` (group) | Kinds: `pi|claude|codex|gemini|cursor|devin|agy|cline|omp|mastracode|opencode|copilot|kimi|kiro|droid|amp|grok|hermes|kilo|qodercli|qwen|letta|maki|muse` |
| `herdr agent list` | `server_not_running` at `~/.config/herdr/herdr.sock` |
| `herdr session list` | `default` — `stopped` |
| `herdr integration status` | pi current (v9); omp current (v10); opencode current (v13); hermes current (v5); codex outdated v9<v10; antigravity-cli outdated v3<v4; grok outdated v2<v3; others not installed; letta experimental/not installed |
| `hermes --version` | `Hermes Agent v0.22.2 (2026.9.24) · stable · local d923a5eb487a`; git install at `~/.hermes/hermes-agent`; Python 3.14.7 |
| `hermes config get model` | default `gpt-6.1-sol-900k`; provider `custom`; base URL `http://127.0.0.1:8787/w/hermes/v1`; `api_mode: codex_responses` |
| `ls ~/.hermes/plugins` | `caveman_native`, `herdr-agent-state`, `homeassistant`, `orca-status` |
| `cmux --version` | `cmux 0.65.2 (111) [9d01f956c]` |
| Environment (`env`) | cmux session variables present (`CMUX_*`), including wrapper shims for claude/codex/pi/hermes/amp; `TERM_PROGRAM=ghostty` |
| Repo grep | No `herdr`/`cmux`/`HERDR` references in any `*.md`; `AGENTS.md` only references the loop paths (unchanged) |

---

## Appendix C — Herdr lifecycle semantics that shaped this design (reference)

- States: `working`, `blocked`, `idle`, `done`, `unknown`. `idle`/`done` = ready for input
  (seen-state differs; reads do not mark seen, focus does). `blocked` = recognized
  approval/question UI. `unknown` = present but unclassified; never proof of success.
- `agent prompt --wait`: submits text + Enter as one ordered submission; waits up to five
  seconds to observe `working`/`blocked` activity (else `agent_prompt_stalled`); after
  activity, waits for a settled state; does not track individual turns (an already-working
  agent's current turn may satisfy the wait); rejects an already-`blocked` agent with
  `agent_blocked` without sending; caller timeout includes submission time.
- Standalone `agent wait` returns immediately if the current state already matches — hence
  the activity-confirmation requirement in the wave pattern.
- `agent read` sources: `visible`, `recent`, `recent-unwrapped`, `detection`; alternate-screen
  agents (full-screen TUIs) may need the app-owned scroll collection or the temp-file fallback.
- `pane run`/`agent start` reject over-long commands on macOS (canonical line-input limit);
  `pane wait-output` matches text that may already be present (stale matches possible).
- Restart: layout restored, sessions resumed only with current integrations; pane processes
  do not survive a machine restart.
- Safety: `--no-focus` for background work; close only what you created; never
  `herdr server stop` from an active session; named test sessions for experiments;
  `--trust-repository` only after the user verified the repository; parse IDs from JSON.
