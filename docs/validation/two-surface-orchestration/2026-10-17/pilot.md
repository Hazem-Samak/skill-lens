# Two-Surface Orchestration: Pilot Evidence & Status (Phase B)

> Current direction (2026-10-18): the user approved one small disposable
> [planning/implementation cycle](./implementation/single-cycle/README.md).
> Further observer work is stopped. P01 remains unverified and P02-P09 are
> paused. The new trial uses its own accepted brief and acceptance conditions;
> none of the historical cases below is retrospectively passed.

> Latest P01 capture checkpoint (2026-10-18): the repaired live retry proved
> fresh context and current registration but lacked correlated actual API-mode
> and HTTP request-URL proof. P01 remains unverified. The temporary observer and
> new fixture passed offline checks and both final reviews. Use [the new P01-only brief](./implementation/p01-capture/P01-only-brief.md).
> The earlier startup commands below are historical and must not be repeated.

> Current status (2026-10-17): the human reported P01 failure, then a diagnostic
> retry that passed fresh-context checks but failed the approved route and left
> session registration unverified. P02–P09 were not run. The original temporary
> artifacts are now absent. A corrected P01-only retry is prepared in
> [the repair record](./implementation/p01-repair/README.md); its
> [current brief](./implementation/p01-repair/P01-only-brief.md) supersedes the
> historical startup/path instructions below. P01 has not been accepted.

**Date:** 2026-10-17
**Status:** Pre-Pilot / All Cases PENDING — Setup and Amendment Approved and Frozen; Awaiting Human Startup
**Operative Base Plan Reference:** [`docs/plans/2026-10-17-two-surface-orchestration.md`](../../../plans/2026-10-17-two-surface-orchestration.md) @ frozen commit [`58d48cea483804b22767b381c6edd8274fe6ad44`](https://github.com/Hazem-Samak/skill-lens/commit/58d48cea483804b22767b381c6edd8274fe6ad44)
**Operative Amendment Reference:** [`docs/plans/2026-10-17-herdr-native-pilot-critic-amendment.md`](../../../plans/2026-10-17-herdr-native-pilot-critic-amendment.md) @ frozen commit [`b99e212a55b20757eeda8605db4edcc59aad6107`](https://github.com/Hazem-Samak/skill-lens/commit/b99e212a55b20757eeda8605db4edcc59aad6107)
**Surface Context:** T3 Code (Outside Herdr; `HERDR_ENV` absent)

---

## 1. Pilot Execution Policy

Under Section 6 Phase B of the frozen plan and operative amendment:
- **No Paper Pass:** Pilot setup is not pilot execution. No case is marked passed without reproducible live evidence captured inside an owned Herdr session.
- **Outside Herdr Invariant:** T3 cannot simulate, inject, or automate Herdr execution from outside `HERDR_ENV`.
- **Negative Case Requirement:** To validate that process guards function, pilot evidence must include:
  1. An intentional mismatched-token / stale-report rejection.
  2. An intentional unresolved-liveness rejection.
- **Role Set Requirement:** The trial-ready role set comprises Hermes coordinator (Sol route), agy implementer (Gemini 3.8 Flash High; unique regex-valid name `worker-<token>`), Critic 1 Pi/AnyModel (native `provider=anymodel` / `model=qwen/qwen3.8-max`, `--thinking high`), and Critic 2 Pi/WorkBuddy (native `provider=workbuddy` / `model=deepseek-v4.1-flash`, `--thinking high`). Both critics and implementer use unique lowercase short tokens matching `^[a-z][a-z0-9_-]{0,31}$`, distinct newly created empty per-dispatch session directories (created exclusively without `-p` for critics), distinct actual shell panes parsed from JSON, and separate processes with no `--continue`/`--resume` flags. Observed runtime independence requires retaining actual distinct process and session IDs.
- **P04 Reporting Policy for Pi Critics:** Because built-in `write` and `edit` are excluded and MCP is suppressed, these read-only Pi critics **cannot** write Markdown fallback files. P04 requires complete native response capture via Herdr terminal inspection (`herdr agent read ...`) or marking the capability unavailable and stopping. Write or shell tools must NOT be granted to rescue capture. The coordinator may retain recovered report text in the external artifacts directory under its own role authority.
- **Strict Output Boundary:** The pilot coordinator operating inside Herdr treats the original repository (`/Users/corvette/Documents/Projects Coding/Skill Lens`) as strictly **READ-ONLY**. Fingerprints of the original repository are recorded before and after operations to verify that zero writes occurred. All pilot evidence is written exclusively to the owned artifact directory (`/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/`). T3 Sol later inspects and records sanitized outcomes.

---

## 2. Pilot Test Matrix (P01–P09)

Every case is currently **PENDING / UNVERIFIED**. The table below records the exercise, planned evidence, blocking prerequisites, and current status:

| ID | Exercise | Required Evidence & Failure Consequence | Blocking Prerequisites | Current Status |
|---|---|---|---|---|
| **P01** | Hermes coordinator entry and context | `HERDR_ENV` gate check (`HERDR_ENV=1`, `HERDR_PANE_ID`); proof of fresh context (Hermes `--ignore-rules` suppresses repo `AGENTS.md`, `SOUL.md`, memories, and skills); actual session/model route verification (`gpt-6.1-sol-900k` via Sol proxy 8787); scoped shell commands; derive real session identity via documented in-Herdr status/readback (`herdr status --json`) without requiring unevidenced `HERDR_SESSION_NAME`; explicit `herdr --skill` read; integration proof via Herdr runtime interaction. *Failure blocks coordinator readiness.* | Human launch of `skill-lens-pilot-20261017` session; user interactive entry into Hermes. | **PENDING** (Unexecuted) |
| **P02** | Two independent critics in one wave (Pre-edit baseline) | Concurrent prompt submission before parent collection; unique lowercase short tokens matching `^[a-z][a-z0-9_-]{0,31}$`; exclusive nonexisting dispatch roots created without `-p` with fresh empty sessions subdirs; distinct process and session IDs retained; complete independent supplied briefs defined before submission; separate prompt results including exit codes; TARGET envelope with exact SHA256; exact token+path+hash match; clean target fingerprints; never mix T3 critics into pilot, install wrappers, or substitute kinds without amendment. Both launch templates approved under frozen amendment `b99e212a55b20757eeda8605db4edcc59aad6107` (native `provider=anymodel` / `model=qwen/qwen3.8-max` and `provider=workbuddy` / `model=deepseek-v4.1-flash`). *Failure blocks multi-critic wave.* | Human launch of session; available shell panes parsed from actual JSON. | **PENDING** (Unexecuted) |
| **P03** | Actual agy / Antigravity implementer & post-edit review wave | Model/config verification (`gemini-3.8-flash-high`); allow-listed synthetic edit in fixture checkout (`/tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt`, baseline SHA256 `462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e`); unique regex-valid implementer name (`worker-<token>`); literal complete independent implementer prompt with full constraints and report schema (no delegation, no review, no commit, no push; native controls recorded, runtime/interaction N/A, upstream identity unverified); own prompt submission, result capture, and token+target-path+hash response acceptance; independent Sol diff verification on fixture; post-implementation review wave with full executable preparation, dispatch, and collection for two fresh Pi critics with revised target SHA256 and new tokens/empty dirs/processes; verify original repo fingerprint unchanged before/after; zero writes to repo. *Failure blocks implementer role.* | Session startup; available shell pane parsed from JSON. | **PENDING** (Unexecuted) |
| **P04** | Full-screen / long report and fallback | Deliberately long response (numbered payload 1..100 or structured multi-section report with explicit `===REPORT_START===` / `===REPORT_END===` markers containing token + target hash); completeness validation checking end marker and token+hash match; increase supported `--lines` if truncated; read-only Pi critics cannot write fallback files; Pi capture-only or stop; other kinds fallback only if permitted; no write/shell tools granted to rescue capture; coordinator may retain recovered text in external artifacts. *Missing required Pi capture blocks readiness; no file fallback for Pi.* | Live agent prompt execution in Herdr pane. | **PENDING** (Unexecuted) |
| **P05** | Permission and question handling | Observe actual blocked question UI; inspect and respond only to authorized narrow reads; UNKNOWN/wider dialog stops immediately; harmless denied-write probe; unchanged fingerprints for fixture and original repo; record exact boundary without universal sandbox claim. *Failure restricts autonomous tools.* | Interactive pane monitoring during live agent run. | **PENDING** (Unexecuted) |
| **P06** | Fast completion and ambiguous delivery | Deliberate exercise of false-settle, delayed, or timed-out observation (`agent_prompt_stalled` within 5000ms or caller timeout); reconcile single submission without duplicate prompt sends or accepting stale reports. *Failure blocks fast-settle reliance.* | Synthetic timeout/race fixture in Herdr pane. | **PENDING** (Unexecuted) |
| **P07** | Active cancellation / background activity | Stop representative owned active/background command in pane via `ctrl+c`; bounded PID/job evidence after interrupt confirming no uncontrolled orphan; unresolved-liveness synthetic rejection; deliberate stale/corrupted token rejection (`corrupted-token-999`). *Failure blocks safe cancellation.* | Live background process execution inside Herdr. | **PENDING** (Unexecuted) |
| **P08** | Detach and controlled restart | Separate human detach from human controlled owned-session stop (`herdr session stop skill-lens-pilot-20261017`) and relaunch (`herdr --session skill-lens-pilot-20261017`); only external human may stop owned test session after saved evidence and owned stop checks; no agent outside Herdr controls; no stopping shared server; keep continuing coordinator and dirty/user resources safe; fresh human Hermes startup/brief and clean context verification; no restored-layout inference. *Failure marks restart guarantees unverified.* | User-operated restart of test session. | **PENDING** (Unexecuted) |
| **P09** | cmux interaction and cleanup | Actual cmux wrapper interaction proof beyond `--version` (actual workspace/surface inspection after reading `--help`, via absolute CLI wrapper `/Applications/cmux.app/Contents/Resources/bin/cmux`); no focus theft; proof of protected cleanup strictly exempting user work, coordinator pane, and dirty worktrees. *Failure marks cmux integration unavailable.* | Absolute invocation of verified binary path; session startup. | **PENDING** (Unexecuted) |

---

## 3. Negative Guard Verification Design

When pilot execution is authorized, two synthetic failure cases will be injected to demonstrate that Herdr coordinator guards actively reject invalid results:

1. **Synthetic Token Mismatch:**
   - A mock reviewer report will be submitted echoing a corrupted token (e.g. `corrupted-token-999` instead of the expected dispatch token).
   - Expected coordinator behavior: Outright rejection of the report; round remains unaccepted.
2. **Synthetic Unresolved Liveness:**
   - An agent task will leave a background sleep process running in its pane.
   - Expected coordinator behavior: Inspection reveals active process; task state marked `interrupted/unknown`; replacement dispatch blocked until the old activity is cleared.

---

## 4. Pilot Preflight Findings Summary

- **Installed Stack:**
  - Hermes (`0.22.2`), agy (`1.4.0`), pi (`1.3.0`), Herdr (`0.9.5`), opencode (`2.0.32`), mcode (`0.6.12`).
  - cmux (`0.65.2`) is present and verified at `/Applications/cmux.app/Contents/Resources/bin/cmux`; absolute invocation is functional, `$PATH` entry is optional.
- **Prepared Synthetic Fixture:**
  - Canonical path: `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout`
  - Target file: `fixture.txt` (SHA256: `462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e`, content `pilot status: pending\n`)
  - Fixture environment: Command-local HOME at `/tmp/.../pilot-home`, XDG at `/tmp/.../pilot-xdg`
  - Owned artifacts directory: `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/` (sole report output destination; original repository preserved read-only)
- **Resolved Role Mapping:**
  - Operative amendment `b99e212a55b20757eeda8605db4edcc59aad6107` resolves the Critic 1 native mapping by adopting native `pi` via AnyModel (native `provider=anymodel` / `model=qwen/qwen3.8-max`, `--thinking high`) and updating both critics to use unique lowercase tokens, distinct newly created empty per-dispatch session directories (without `-p`), and separate processes/session IDs.
  - The human user approved adoption and freeze on 2026-10-17 under the unverified-family policy.
- **Next Steps:**
  - Human initiation of `herdr --session skill-lens-pilot-20261017`.
  - Execution of P01–P09 under live Herdr environment.
