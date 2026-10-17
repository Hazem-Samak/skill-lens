# Two-Surface Orchestration: Herdr + cmux Setup Proposal

**Date:** 2026-10-17  
**Status:** Proposal / Preflight Complete — Pending User Approval  
**Plan Reference:** [`docs/plans/2026-10-17-two-surface-orchestration.md`](../../../plans/2026-10-17-two-surface-orchestration.md) @ frozen commit [`58d48cea483804b22767b381c6edd8274fe6ad44`](https://github.com/Hazem-Samak/skill-lens/commit/58d48cea483804b22767b381c6edd8274fe6ad44)  
**Surface Context:** T3 Code (Outside Herdr; `HERDR_ENV` absent)

---

## 1. Overview and Authorization Bounds

This setup proposal establishes the concrete machine configuration, installed CLI readiness, proposed role mapping, session lifecycle, and human startup procedure for Phase B of the two-surface orchestration plan.

Under the frozen plan:
- **T3 Ownership:** Migration ownership remains T3 end-to-end. This dispatch is read-only preflight and setup proposal only.
- **Outside Herdr Boundary:** The current execution environment has no `HERDR_ENV`. In accordance with Herdr skill rules and frozen bounds, no out-of-Herdr inspection or live control of any focused Herdr session is performed.
- **No Unapproved Action:** No live Herdr sessions, background daemons, or pilot agents have been launched. No credentials, tokens, or personal configurations have been modified.
- **Explicit Stop:** Work stops at the boundary requiring explicit user approval of session names, startup procedures, and role mappings.

---

## 2. Machine & CLI Readiness Inventory

Read-only discovery was executed on 2026-10-17 against the local machine. Results:

| Component | Target Version / Status | Verified Path / Source | Read-Only Help / Status |
|---|---|---|---|
| **Hermes** | v0.22.2 (2026.9.24) `d923a5eb487a` | `/Users/corvette/.local/bin/hermes` | Help verified (`--cli`, `-m`, `--reasoning`, `--yolo`, `-z`, `--in`, `--ignore-rules`) |
| **agy** | 1.4.0 | `/Users/corvette/.local/bin/agy` | Help verified; `gemini-3.8-flash-high` available in `agy models`; `--sandbox` terminal restrictions noted |
| **pi** | 1.3.0 | `/Users/corvette/.local/bin/pi` | Help verified (`--provider`, `--model`, `--thinking`, `--tools`, `--no-mcp`, `--no-extensions`, `-e`, `--no-skills`, `--no-context-files`, `--session-dir`) |
| **Herdr** | 0.9.5 | `/Users/corvette/.local/bin/herdr` | Help verified (`agent`, `pane`, `workspace`, `tab`, `session`, `integration`) |
| **cmux** | 0.65.2 (111) `[9d01f956c]` | `/Applications/cmux.app/Contents/Resources/bin/cmux` | Binary help verified. Absolute path invocation verified working. **Not in `$PATH`** (`which cmux` fails); persistent `$PATH` edit optional |
| **opencode** (optional) | v2.0.32 | `/Users/corvette/.opencode/bin/opencode` | Verified; optional kind, marked untested/unavailable |
| **mcode** (MiniMax) | 0.6.12 | `/Users/corvette/.minimax-code/bin/mcode` | Verified CLI; **unsupported as a native Herdr kind** (not in Herdr's 24-kind list) |
| **Sol Proxy** | Listening on TCP 127.0.0.1:8787 | `http://127.0.0.1:8787/w/hermes/v1` | TCP connect successful (port open); upstream model identity unverified |

### Critical Environment Observations

1. **`cmux` Absolute Invocation vs. PATH:**
   - The verified CLI wrapper binary is `/Applications/cmux.app/Contents/Resources/bin/cmux`. Executing it with `--version` succeeds cleanly (`cmux 0.65.2 (111) [9d01f956c]`).
   - The directory `/Applications/cmux.app/Contents/Resources/bin` is not currently in `$PATH`. Absolute invocation is fully sufficient for all scripts and proposed commands; adding the directory to `$PATH` is optional.
   - *Warning:* Calling `/Applications/cmux.app/Contents/MacOS/cmux` directly launches the macOS GUI application bundle, not the CLI wrapper.
2. **MiniMax (`mcode`) Native Kind Gap:**
   - Herdr 0.9.5 defines 24 supported agent kinds in its CLI argument parser (`herdr agent start --help`):
     ```text
     pi, claude, codex, gemini, cursor, devin, agy, cline, omp, mastracode, opencode, copilot, kimi, kiro, droid, amp, grok, hermes, kilo, qodercli, qwen, letta, maki, muse
     ```
   - Neither `mcode` nor `minimax` is among the 24 supported kinds. (Note: `mastracode` is a distinct canonical executable from Mastra at `mastra.ai`, not a MiniMax alias; `which mastracode` fails).
   - Inspected configs for existing supported kinds show no pre-configured fallback route: `~/.hermes/config.yaml` has `minimax` sections explicitly disabled (`enabled: false`), and `~/.pi/agent/models.json` configures no MiniMax provider.
   - *Scope of finding:* This native kind gap is scoped strictly to the installed Herdr 0.9.5 kind enum and inspected local configurations, not a proof of global impossibility. Under frozen rules (Section 4.4), the orchestrator must not substitute an unapproved kind. Unvalidated alternative routes require explicit user decision and formal plan amendment.

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

The plan requires proposing exact kind, model, and native launch settings for each role in the orchestration council:

| Role | Planned Candidate | Proposed Herdr Kind | Executable & Native Launch Arguments | Readiness / Blocker Status |
|---|---|---|---|---|
| **Coordinator** | Hermes (Sol route) | `hermes` | `herdr agent start coord --kind hermes --pane <pane-id> -- --cli --ignore-rules --in /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout -m gpt-6.1-sol-900k --reasoning high` | **Proposal Ready** (RPC syntax example only; a separate control pane would be required. Operator startup uses only the direct interactive flow in Section 6; pending user approval) |
| **Implementer** | agy (Gemini 3.8 Flash High) | `agy` | `herdr agent start worker --kind agy --pane <pane-id> -- --model gemini-3.8-flash-high --effort high --sandbox` | **PROPOSED UNTESTED MAPPING** (To approve/validate; `--sandbox` provides advertised terminal restrictions with no filesystem containment guarantees) |
| **Critic 1** | MiniMax (mcode) | *None* | *None* (No supported Herdr launch proposed) | **BLOCKED:** Herdr 0.9.5 kind enum does not support `mcode` or `minimax`. No substitution permitted without plan amendment. |
| **Critic 2** | DeepSeek (Pi / WorkBuddy) | `pi` | `herdr agent start critic_deepseek --kind pi --pane <pane-id> -- --provider workbuddy --model deepseek-v4.1-flash --thinking high --tools read,grep,find,ls --no-mcp --no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts --no-skills --no-context-files --session-dir /tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/pi-sessions` | **Proposal Ready** (Built-in read-only tools + MCP suppression; Herdr state extension explicitly retained) |

### Tool and Isolation Boundaries
- **Pi Critic Tool Boundary:** Passing `--tools read,grep,find,ls` drops built-in `bash`, `write`, and `edit`, and enables `grep`, `find`, and `ls`. Because `--tools` alone keeps MCP tools, `--no-mcp` is explicitly added to disable built-in MCP server connections. To prevent loading untrusted or extraneous extensions while preserving Herdr agent state observation (`~/.pi/agent/extensions/herdr-agent-state.ts`), we propose `--no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts`.
  *Honest boundary note:* This is a tool-level restriction and MCP suppression, not universal filesystem sandboxing. Any unavailable temporary-file output under a read-only configuration must remain unavailable rather than silently adding write tools.
- **Hermes Coordinator Boundaries:** Hermes has no native per-command read-only tool confinement flag (its `-t file` allows editing/writing, and `-t terminal` allows shell commands). Confinement to intended coordinator behavior relies on session policy and prompt instructions. `--ignore-rules` skips `AGENTS.md`, `SOUL.md`, `.cursorrules`, memories, and preloaded skills. `--in DIR` changes working directory to `DIR` before starting; it is directory selection, not a path jail.
- **agy Implementer Boundaries:** `agy --add-dir` adds directories to the workspace (widening scope) and `--project` specifies a project name/ID; neither confines path access. agy provides `--sandbox` ("terminal restrictions enabled"), which is an advertised terminal restriction, not an empirically certified sandbox.

### Distinction Between Reviewer Contexts
- **Migration Council Reviewers (T3 Code):** Selected directly by T3 `delegate_task` (`mcode` instance with `MiniMax-M3.1-Flash-Preview:v:thinking`, and `pi` instance with `workbuddy/deepseek-v4.1-flash`). These operate within T3 and reviewed the planning draft and preflight evidence.
- **Pilot Role Choices (Herdr):** Subject to Herdr native kind support. While `pi` is natively supported by Herdr, `mcode` is not. Eventual pilot role choices require user approval and either a Herdr kind addition, an approved native wrapper route, or an authorized plan amendment.

---

## 5. Proposed Session Names & Lifecycle

In accordance with section 4.4 of the plan:
- **Dedicated Project Session Name:** `skill-lens`
- **Isolated Pilot Session Name:** `skill-lens-pilot-20261017`

### Human-Owned Lifecycle Rules
1. **No Autonomous Server Control:** T3 agents running outside Herdr must never launch background Herdr servers, attach sockets, or send simulated inputs.
2. **User-Operated Startup:** The user starts the isolated named session in a separate terminal.
3. **Safe Restart Procedure:** If a restart is tested during the pilot (P08), the human operator restarts only the owned test session (`skill-lens-pilot-20261017`). The shared daily server or machine must never be stopped by automated scripts.

---

## 6. Human Startup Handoff & Exact Commands

When authorized, the human operator conducts startup. All commands below are **unrun proposals** awaiting explicit user decision.

### Recommended Flow: Direct Interactive Hermes Launch (Unrun)

This is the sole documented direct interactive startup procedure. It avoids single-pane self-occupation, avoids relying on untested Herdr RPC prompt submission mechanisms, and minimizes failure paths:

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

## 8. Unresolved Prerequisites Summary

Before the pilot (Phase B execution) can begin:
1. **User Approval:** Explicit user approval is required for:
   - Dedicated session name `skill-lens` and pilot session name `skill-lens-pilot-20261017`.
   - Proposed human-managed startup commands (direct interactive Hermes flow).
   - Addressing the MiniMax (`mcode`) Herdr native kind gap. This gap is scoped to the installed Herdr 0.9.5 kind enum (24 kinds) and inspected local configurations, not global impossibility. Unvalidated future-choice alternatives requiring explicit user authorization and formal plan amendment include:
     - *Unvalidated Alternative 1:* Potential Hermes custom provider configuration route (currently disabled in `~/.hermes/config.yaml`, unproven working).
     - *Unvalidated Alternative 2:* Two-surface division retaining MiniMax critic in T3 Code while executing single-surface pilot in Herdr.
     - *Unvalidated Alternative 3:* Council role kind substitution with a native Herdr kind (e.g. `claude`, `codex`, `opencode`) via formal plan amendment.
     - *Unvalidated Alternative 4:* Upstream Herdr kind addition or custom wrapper.
     None of these alternatives is currently validated or proven working; any modification requires an explicit user amendment.
2. **cmux Accessibility:** Absolute invocation `/Applications/cmux.app/Contents/Resources/bin/cmux` is fully functional; persistent `$PATH` edit is optional.
3. **No Paper Pass:** All pilot cases P01–P09 remain in `PENDING` state until live execution is conducted within Herdr.
