# Two-Surface Orchestration: Herdr + cmux Setup Proposal

> Latest P01 capture checkpoint (2026-10-18): the repaired live retry proved
> fresh context and current registration but lacked correlated actual API-mode
> and HTTP request-URL proof. P01 remains unverified. The temporary observer and
> new fixture passed offline checks and both final reviews. Use [the new P01-only brief](./implementation/p01-capture/P01-only-brief.md).
> The earlier startup commands below are historical and must not be repeated.

> Current P01 repair handoff (2026-10-17): the human reported two stopped P01
> attempts. The corrected subscription route and fresh fixture are prepared under
> [the frozen repair amendment](../../../plans/2026-10-17-herdr-p01-route-repair.md).
> Follow the [current P01-only brief](./implementation/p01-repair/P01-only-brief.md)
> for the next attempt. The startup instructions and temporary paths below are
> retained as historical evidence. Live P01 and the migration remain unaccepted.

**Date:** 2026-10-17
**Status:** Setup and Critic 1 Native Amendment Approved and Frozen; Live Pilot Execution Pending Human Startup
**Operative Base Plan Reference:** [`docs/plans/2026-10-17-two-surface-orchestration.md`](../../../plans/2026-10-17-two-surface-orchestration.md) @ frozen commit [`58d48cea483804b22767b381c6edd8274fe6ad44`](https://github.com/Hazem-Samak/skill-lens/commit/58d48cea483804b22767b381c6edd8274fe6ad44)
**Operative Amendment Reference:** [`docs/plans/2026-10-17-herdr-native-pilot-critic-amendment.md`](../../../plans/2026-10-17-herdr-native-pilot-critic-amendment.md) @ frozen commit [`b99e212a55b20757eeda8605db4edcc59aad6107`](https://github.com/Hazem-Samak/skill-lens/commit/b99e212a55b20757eeda8605db4edcc59aad6107)
**Surface Context:** T3 Code (Outside Herdr; `HERDR_ENV` absent)

**Approval Record:** The user explicitly approved the dedicated session name `skill-lens`, isolated pilot session name `skill-lens-pilot-20261017`, human-operated direct Hermes startup/restart, and existing Hermes/Gemini/DeepSeek settings (see [setup approval record](./implementation/setup-approval-20261017.md)). On 2026-10-17, the user further approved **adoption and freeze** of the exact reviewed amendment adopting Pi/AnyModel Qwen 3.8 Max high and Pi/WorkBuddy DeepSeek high with distinct empty per-dispatch session directories despite unverified upstream model/family identities. That resolves the earlier missing-critic1 mapping and approval-pending gates. The pilot itself has not yet run; live execution of P01–P09 inside genuine Herdr remains pending human session startup.

---

## 1. Overview and Authorization Bounds

This setup proposal establishes the concrete machine configuration, installed CLI readiness, proposed role mapping, session lifecycle, and human startup procedure for Phase B of the two-surface orchestration plan.

Under the frozen plan and operative amendment:
- **T3 Ownership:** Migration ownership remains T3 end-to-end. This dispatch is read-only preflight and documentation application only.
- **Outside Herdr Boundary:** The current execution environment has no `HERDR_ENV`. In accordance with Herdr skill rules and frozen bounds, no out-of-Herdr inspection or live control of any focused Herdr session is performed.
- **No Unapproved Action:** No live Herdr sessions, background daemons, or pilot agents have been launched. No credentials, tokens, or personal configurations have been modified.
- **Preserved Boundaries:** Historical reports, baseline evidence under `implementation/native-mapping-application-baseline/`, active process docs, and pre-existing repository files remain protected.

---

## 2. Machine & CLI Readiness Inventory

Read-only discovery was executed against the local machine. Results:

| Component | Target Version / Status | Verified Path / Source | Read-Only Help / Status |
|---|---|---|---|
| **Hermes** | v0.22.2 (2026.9.24) `d923a5eb487a` | `/Users/corvette/.local/bin/hermes` | Help verified (`--cli`, `-m`, `--reasoning`, `--yolo`, `-z`, `--in`, `--ignore-rules`) |
| **agy** | 1.4.0 | `/Users/corvette/.local/bin/agy` | Help verified; `gemini-3.8-flash-high` available in `agy models`; `--sandbox` terminal restrictions noted |
| **pi** | 1.3.0 | `/Users/corvette/.local/bin/pi` | Help verified (`--provider`, `--model`, `--thinking`, `--tools`, `--no-mcp`, `--no-extensions`, `-e`, `--no-skills`, `--no-context-files`, `--session-dir`); AnyModel route verified in `~/.pi/agent/models.json` |
| **Herdr** | 0.9.5 | `/Users/corvette/.local/bin/herdr` | Help verified (`agent`, `pane`, `workspace`, `tab`, `session`, `integration`) |
| **cmux** | 0.65.2 (111) `[9d01f956c]` | `/Applications/cmux.app/Contents/Resources/bin/cmux` | Binary help verified. Absolute path invocation verified working. **Not in `$PATH`** (`command -v cmux` fails); persistent `$PATH` edit optional |
| **opencode** (optional) | v2.0.32 | `/Users/corvette/.opencode/bin/opencode` | Verified; optional kind, marked untested/unavailable |
| **mcode** (MiniMax) | 0.6.12 | `/Users/corvette/.minimax-code/bin/mcode` | Verified CLI; **unsupported as a native Herdr kind** (not in Herdr's 24-kind list; resolved for pilot by approved Pi/AnyModel Qwen amendment) |
| **Sol Proxy** | Listening on TCP 127.0.0.1:8787 | `http://127.0.0.1:8787/w/hermes/v1` | TCP connect successful (port open); upstream model identity unverified |

### Critical Environment Observations

1. **`cmux` Absolute Invocation vs. PATH:**
   - The verified CLI wrapper binary is `/Applications/cmux.app/Contents/Resources/bin/cmux`. Executing it with `--version` succeeds cleanly (`cmux 0.65.2 (111) [9d01f956c]`).
   - The directory `/Applications/cmux.app/Contents/Resources/bin` is not currently in `$PATH`. Absolute invocation is fully sufficient for all scripts and proposed commands; adding the directory to `$PATH` is optional.
   - *Warning:* Calling `/Applications/cmux.app/Contents/MacOS/cmux` directly launches the macOS GUI application bundle, not the CLI wrapper.
2. **MiniMax (`mcode`) Native Kind Gap Resolution:**
   - Herdr 0.9.5 defines 24 supported agent kinds in its CLI argument parser (`herdr agent start --help`):
     ```text
     pi, claude, codex, gemini, cursor, devin, agy, cline, omp, mastracode, opencode, copilot, kimi, kiro, droid, amp, grok, hermes, kilo, qodercli, qwen, letta, maki, muse
     ```
   - Neither `mcode` nor `minimax` is among the 24 supported kinds. (Note: `mastracode` is a distinct canonical executable from Mastra at `mastra.ai`, not a MiniMax alias; `command -v mastracode` fails).
   - This native kind gap is resolved for the Herdr pilot by operative amendment [`docs/plans/2026-10-17-herdr-native-pilot-critic-amendment.md`](../../../plans/2026-10-17-herdr-native-pilot-critic-amendment.md) @ `b99e212a55b20757eeda8605db4edcc59aad6107`, adopted and frozen by explicit user authorization. Critic 1 is mapped to native `pi` via AnyModel (`provider=anymodel`, `model=qwen/qwen3.8-max`, `--thinking high`).
   - The migration council in T3 Code continues to use MiniMax/mcode xhigh and Pi/WorkBuddy DeepSeek high.

---

## 3. Whitelisted Configuration Reads

Only whitelisted routing, model, and option settings were inspected. No secret tokens, credentials, or personal keys were accessed or recorded.

### Hermes (`~/.hermes/config.yaml`)
- `model.default`: `gpt-6.1-sol-900k`
- `model.provider`: `custom`
- `model.base_url`: `http://127.0.0.1:8787/w/hermes/v1`
- `agent.reasoning_effort`: `high`
- `agent.reasoning_overrides`: `{}`
- MiniMax sections: `minimax.enabled: false`, `minimax-cn.enabled: false`

### Pi (`~/.pi/agent/models.json` & `settings.json`)
- `providers.workbuddy.baseUrl`: `http://127.0.0.1:8788/v1`
- `providers.workbuddy.models`: `['deepseek-v4.1-flash']`
- `providers.anymodel.baseUrl`: `https://anymodel.org/v1`
- `providers.anymodel.models`: `['qwen/qwen3.8-max']` (reasoning enabled)
- `settings.json`: `defaultProvider: openrouter`, `theme: dark`

### Herdr (`~/.config/herdr/config.toml`)
- `onboarding`: `false`
- `[theme] name`: `"gruvbox"`, `auto_switch`: `false`
- `[ui] status_indicators`: `"symbols"`
- `[ui.toast] delivery`: `"system"`

### agy
- Target model: `gemini-3.8-flash-high` confirmed available in `agy models`.
- Terminal restriction option: `--sandbox` ("terminal restrictions enabled").

---

## 4. Role Mapping Proposal

Under the operative base plan and amendment, the approved native launch templates for the pilot council are:

| Role | Approved Candidate | Proposed Herdr Kind | Executable & Native Launch Arguments | Readiness / Blocker Status |
|---|---|---|---|---|
| **Coordinator** | Hermes (Sol route) | `hermes` | `cd /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout && hermes --cli --ignore-rules --in /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout -m gpt-6.1-sol-900k --reasoning high`<br>*(Historical alternate, explicitly NONEXECUTABLE in single-pane startup without a separate control pane: `herdr agent start coord --kind hermes --pane <pane-id> -- ...`)* | **Approved Mapping** (Sole approved executable procedure is Direct Interactive Human Startup in Section 6; single-pane `agent start` is a nonexecutable historical alternate) |
| **Implementer** | agy (Gemini 3.8 Flash High) | `agy` | `herdr agent start worker-<token> --kind agy --pane <available-shell-pane-id> -- --model gemini-3.8-flash-high --effort high --sandbox` | **Approved Untested Mapping** (Name regex `^[a-z][a-z0-9_-]{0,31}$`; unique per-dispatch token; `--sandbox` provides advertised terminal restrictions with no filesystem containment guarantees) |
| **Critic 1** | Pi / AnyModel (Qwen 3.8 Max) | `pi` | `herdr agent start critic-qwen-<token> --kind pi --pane <available-shell-pane-id> -- --provider anymodel --model qwen/qwen3.8-max --thinking high --tools read,grep,find,ls --no-mcp --no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts --no-skills --no-context-files --session-dir /tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/pi-critic-qwen-<token>/sessions` | **Approved & Frozen Amendment Mapping** (Adopted at `b99e212a55b20757eeda8605db4edcc59aad6107`; name regex `^[a-z][a-z0-9_-]{0,31}$`; native `provider=anymodel` / `model=qwen/qwen3.8-max`; unrun; unverified upstream identity; read-only tools) |
| **Critic 2** | Pi / WorkBuddy (DeepSeek v4.1 Flash) | `pi` | `herdr agent start critic-deepseek-<token> --kind pi --pane <second-available-shell-pane-id> -- --provider workbuddy --model deepseek-v4.1-flash --thinking high --tools read,grep,find,ls --no-mcp --no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts --no-skills --no-context-files --session-dir /tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/pi-critic-deepseek-<token>/sessions` | **Approved & Frozen Amendment Mapping** (Adopted at `b99e212a55b20757eeda8605db4edcc59aad6107`; name regex `^[a-z][a-z0-9_-]{0,31}$`; native `provider=workbuddy` / `model=deepseek-v4.1-flash`; per-dispatch session dir; unrun; unverified upstream identity; read-only tools) |

### Tool and Isolation Boundaries
- **Pi Critic Tool Boundary:** Passing `--tools read,grep,find,ls` drops built-in `bash`, `write`, and `edit`, and enables `grep`, `find`, and `ls`. Because `--tools` alone keeps MCP tools, `--no-mcp` is explicitly added to disable built-in MCP server connections. To prevent loading untrusted or extraneous extensions while preserving Herdr agent state observation (`~/.pi/agent/extensions/herdr-agent-state.ts`), we specify `--no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts`. Discovery suppression is enforced via `--no-skills --no-context-files`.
- **Agent Name Regex & Token Generation:** In accordance with Herdr requirements, agent names must match `^[a-z][a-z0-9_-]{0,31}$` (lowercase start, lowercase alphanumeric, underscore, hyphen, maximum 32 characters). Generated tokens must be unique lowercase short strings (e.g. uuid hex12 via Python), resulting in compliant names such as `worker-<hex12>` (19 chars), `critic-qwen-<hex12>` (24 chars), and `critic-deepseek-<hex12>` (28 chars).
- **Per-Dispatch Session Storage Delta:** Under the frozen amendment, both critics use distinct, newly created empty per-dispatch session directories under `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/`. Exclusive directory creation (without `-p`) is required to prevent accidental reuse or collision.
- **Distinguishing Template from Observed Runtime Independence:** The launch templates configure distinct parameters (`--session-dir`, `--provider`, `--model`, `--thinking high`). Runtime independence requires observed proof: distinct foreground shell panes parsed from actual JSON output (`test "$PANE1_ID" != "$PANE2_ID"`), successful start and idle readiness verified via `herdr agent get`, distinct process IDs (PID) and session IDs recorded from the runtime, and independent log files.
- **P04 Reporting Policy for Pi Critics:** Because built-in `write` and `edit` are excluded and MCP is suppressed, these read-only Pi critics **cannot** write Markdown fallback files. P04 requires complete native response capture via Herdr terminal inspection (`herdr agent read ...`) or marking the capability unavailable and stopping. Write or shell tools must NOT be granted to rescue capture. The coordinator may retain recovered report text in the external artifacts directory under its own role authority.
- **Hermes Coordinator Boundaries:** Hermes has no native per-command read-only tool confinement flag (its `-t file` allows editing/writing, and `-t terminal` allows shell commands). Confinement to intended coordinator behavior relies on session policy and prompt instructions. `--ignore-rules` skips `AGENTS.md`, `SOUL.md`, `.cursorrules`, memories, and preloaded skills. `--in DIR` changes working directory to `DIR` before starting; it is directory selection, not a path jail.
- **agy Implementer Boundaries:** `agy --add-dir` adds directories to the workspace (widening scope) and `--project` specifies a project name/ID; neither confines path access. agy provides `--sandbox` ("terminal restrictions enabled"), which is an advertised terminal restriction, not an empirically certified sandbox.

### Distinction Between Reviewer Contexts
- **Migration Council Reviewers (T3 Code):** Selected directly by T3 `delegate_task` (`mcode` instance with `MiniMax-M3.1-Flash-Preview:v:thinking`, and `pi` instance with `workbuddy/deepseek-v4.1-flash`). These operate within T3 and reviewed the planning draft, preflight evidence, and the native critic amendment.
- **Pilot Role Choices (Herdr):** Run natively inside Herdr panes. Critic 1 uses native `pi` via AnyModel (`provider=anymodel`, `model=qwen/qwen3.8-max`, `--thinking high`); Critic 2 uses native `pi` via WorkBuddy (`provider=workbuddy`, `model=deepseek-v4.1-flash`, `--thinking high`). Upstream identities/families remain unverified; this exact pair was explicitly approved by the user under the unverified-family policy.

---

## 5. Proposed Session Names & Lifecycle

In accordance with section 4.4 of the base plan and approved by the user:
- **Dedicated Project Session Name:** `skill-lens`
- **Isolated Pilot Session Name:** `skill-lens-pilot-20261017`

### Human-Owned Lifecycle Rules
1. **No Autonomous Server Control:** T3 agents running outside Herdr must never launch background Herdr servers, attach sockets, or send simulated inputs.
2. **User-Operated Startup:** The user starts the isolated named session in a separate terminal.
3. **Separate Human Detach vs. Controlled Owned-Session Stop/Relaunch Exercises:**
   - **Human Detach:** The operator detaches their client from the running session using documented Herdr UI controls (retaining the actual UI action taken). The session and background agents continue running undisturbed.
   - **Controlled Owned-Session Stop:** Only the external human operator may stop the exact owned test session after saving evidence and verifying owned stop checks (`herdr session stop skill-lens-pilot-20261017`). No agent outside Herdr controls this. The shared daily server (`herdr server stop`) is strictly prohibited to keep continuing coordinator and user resources safe.
   - **Controlled Owned-Session Relaunch:** The human restarts only the owned session (`herdr --session skill-lens-pilot-20261017` or `herdr session attach skill-lens-pilot-20261017`), launches a fresh Hermes coordinator, supplies the brief, and verifies fresh context. No inference is drawn from restored window/pane layout to worker termination or task continuity.

---

## 6. Human Startup Handoff & Exact Commands

The human operator conducts startup. All commands below represent the approved procedure awaiting user execution:

### Approved Flow: Direct Interactive Hermes Launch

This is the documented direct interactive startup procedure. It avoids single-pane self-occupation, avoids relying on untested Herdr RPC prompt submission mechanisms, and minimizes failure paths:

1. **Launch Isolated Pilot Session:**
   From a clean user terminal:
   ```bash
   herdr --session skill-lens-pilot-20261017
   ```
2. **Confirm Entry Gate in Pane:**
   Inside the Herdr-managed shell pane, confirm Herdr environment presence:
   ```bash
   test "${HERDR_ENV:-}" = 1 && echo "HERDR_ENV confirmed: $HERDR_PANE_ID" || echo "NOT in Herdr"
   ```
3. **Navigate to Prepared Synthetic Checkout:**
   ```bash
   cd /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout
   ```
4. **Launch Hermes Coordinator Interactively:**
   ```bash
   hermes --cli --ignore-rules --in /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout -m gpt-6.1-sol-900k --reasoning high
   ```
5. **Supply Pilot Brief Interactively:**
   At the Hermes interactive prompt, paste the complete synthetic pilot brief prepared in [`docs/validation/two-surface-orchestration/2026-10-17/implementation/human-pilot-brief.md`](./implementation/human-pilot-brief.md).

---

## 7. Synthetic Fixture & Environment Isolation

The pilot tests synthetic checkout and fixture behavior while keeping live user skills and the original repository protected:

1. **Prepared Synthetic Checkout:**
   The canonical external checkout is prepared at:
   `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout`
   It contains baseline target `fixture.txt` (initial content `pilot status: pending\n`, SHA256 `462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e`).
2. **Command-Local HOME and XDG for Fixture Commands:**
   To prevent accidental redirection of subsequent parent agent authentication or extension contexts, shell-wide `export HOME` and `export XDG_CONFIG_HOME` are strictly avoided. Instead, test commands against the synthetic fixture use per-command local environment prefixing:
   ```bash
   HOME="/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-home" XDG_CONFIG_HOME="/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-xdg" <command>
   ```
3. **CLI Authentication & Extension Preservation:**
   - Existing CLI authentication (`~/.pi/agent/auth.json`, `~/.hermes/.env`, `~/.gemini`) remains in the user's real home directory. Fake HOME is not exported in parent agent shells, preserving authentication and extension integrity.
   - For `pi`, running with `--no-skills --no-context-files` suppresses discovery of `~/.pi/agent/skills`, `AGENTS.md`, and `CLAUDE.md`. `--no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts` disables untrusted extension loading while explicitly preserving Herdr state monitoring.
   - For `hermes`, `--ignore-rules` skips auto-injection of repo `AGENTS.md`, `SOUL.md`, memories, and skills; `--in <path>` sets working directory.
   - For `agy`, `--sandbox` enables terminal restrictions.
4. **Original Repository Read-Only Protection & Output Destination:**
   - The original repository (`/Users/corvette/Documents/Projects Coding/Skill Lens`) is strictly preserved as **READ-ONLY** for the pilot coordinator.
   - Pilot logs and evidence must be written exclusively to the owned artifacts directory:
     `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/`
   - T3 Sol later inspects and sanitizes the artifact directory output and updates repository records.

---

## 8. Prerequisites and Status Summary

1. **User Approvals Resolved:**
   - Dedicated session name `skill-lens` and pilot session name `skill-lens-pilot-20261017` approved.
   - Human-managed direct interactive Hermes startup approved.
   - Operative amendment adopting Pi/AnyModel Qwen 3.8 Max high (native `provider=anymodel` / `model=qwen/qwen3.8-max`) and per-dispatch session storage for both critics approved and frozen at `b99e212a55b20757eeda8605db4edcc59aad6107`.
2. **Current Remaining Prerequisite:**
   - Human operator executes Step 1 (`herdr --session skill-lens-pilot-20261017`) and launches coordinator in Herdr to begin live execution.
3. **cmux Accessibility:** Absolute invocation `/Applications/cmux.app/Contents/Resources/bin/cmux` is fully functional; persistent `$PATH` edit is optional.
4. **No Paper Pass:** All pilot cases P01–P09 remain in `PENDING` state until live execution is conducted within Herdr.
