# Two-Surface Orchestration: Phase B Implementation Preflight Report

**Date:** 2026-10-17  
**Author / Implementer:** Antigravity (Gemini 3.8 Flash High)  
**Role:** Implementation Sub-agent (Sole Implementer)  
**Task Scope:** Phase B Preflight / Setup-Proposal Only (No live Herdr pilot, no Phase C process edits)  
**Plan Reference:** [`docs/plans/2026-10-17-two-surface-orchestration.md`](../../../../plans/2026-10-17-two-surface-orchestration.md) @ frozen commit [`58d48cea483804b22767b381c6edd8274fe6ad44`](https://github.com/Hazem-Samak/skill-lens/commit/58d48cea483804b22767b381c6edd8274fe6ad44)  
**Current Checkout HEAD:** `a0ffa9edee8226d7d8b981002b265510bced8a16`  
**Surface Context:** T3 Code (`HERDR_ENV` absent)

---

## 1. Frozen Plan Verification & Reference Check

In accordance with Step 1 of `docs/process/implementation-loop.md`:
1. `git diff 58d48cea483804b22767b381c6edd8274fe6ad44..HEAD -- docs/plans/2026-10-17-two-surface-orchestration.md` was inspected.
2. The operative text of the plan between the frozen commit `58d48cea483804b22767b381c6edd8274fe6ad44` and HEAD `a0ffa9edee8226d7d8b981002b265510bced8a16` differs **strictly and only in the Reference header**:
   ```diff
   -Reference: pending
   +Reference: 58d48cea483804b22767b381c6edd8274fe6ad44
   ```
   All operative sections 1 through 8 are bit-for-bit identical to the frozen plan approved by the user and reviewed by independent critics.
3. Relevant process and architecture documents were read:
   - [`AGENTS.md`](../../../../../AGENTS.md)
   - [`docs/process/council.md`](../../../../process/council.md)
   - [`docs/process/implementation-loop.md`](../../../../process/implementation-loop.md)
   - [`docs/process/profiles/machine-profile.md`](../../../../process/profiles/machine-profile.md)

---

## 2. Baseline Gate Verification

The coordinator reran all four project gates on the clean baseline tree prior to this dispatch. The results and logs were inspected under `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/` and match the retained baseline logs in `implementation/baseline/`:

| Gate | Command | Exit Code | Duration | Result / Coverage | Log Path |
|---|---|---|---|---|---|
| **pytest** | `.venv/bin/pytest --cov=skill_lens -o cache_dir=/tmp/.../pytest-cache` | `0` | 54.05s | 1048 passed, 1 skipped; **91.11% coverage** (threshold >= 90%) | `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pytest.log` |
| **mypy** | `.venv/bin/mypy --cache-dir /tmp/.../mypy-cache` | `0` | 1.76s | Success: no issues found in 37 source files | `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/mypy.log` |
| **ruff check** | `.venv/bin/ruff check . --no-cache` | `0` | 0.08s | All checks passed! | `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/ruff-check.log` |
| **ruff format** | `.venv/bin/ruff format --check . --no-cache` | `0` | 0.08s | 187 files already formatted | `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/ruff-format.log` |

All baseline gates pass cleanly on the virtual environment without mutation. (Note: the 187 file count matches the authoritative baseline log; 184 was an earlier drafting-tree figure). The four source gates already pass; no rerun is required absent new source concerns.

---

## 3. Installed CLI & Proxy Inventory

All required and relevant CLIs were verified via read-only `--version` and `--help` invocations:

1. **Hermes:**
   - Version: `Hermes Agent v0.22.2 (2026.9.24) · stable · local d923a5eb487a` (Python 3.14.7, OpenAI SDK 2.24.0)
   - Binary: `/Users/corvette/.local/bin/hermes`
   - Help output verified: `--cli`, `-m`, `--provider`, `--reasoning`, `--yolo`, `-z/--oneshot`, `--in`, `--ignore-rules`.
   - Tool boundary note: Hermes has no native per-command read-only tool confinement flag (its `-t file` allows editing/writing, and `-t terminal` allows shell commands).
2. **agy:**
   - Version: `1.4.0`
   - Binary: `/Users/corvette/.local/bin/agy`
   - Available models verified via `agy models`: `gemini-3.8-flash-high` is present and ready.
   - Isolation note: `--sandbox` provides help-advertised terminal restrictions; `--add-dir` adds workspace directories (widening scope); neither constitutes certified path confinement.
3. **pi:**
   - Version: `1.3.0`
   - Binary: `/Users/corvette/.local/bin/pi`
   - Help verified: `--provider`, `--model`, `--thinking`, `--tools`, `--no-mcp`, `--no-extensions`, `-e`, `--no-skills`, `--no-context-files`, `--session-dir`.
   - Tool boundary note: `--tools read,grep,find,ls` drops built-in `bash`, `write`, and `edit`, and enables `grep`, `find`, and `ls`. `--tools` alone keeps MCP tools, so `--no-mcp` is necessary to suppress MCP support.
   - Herdr integration note: `--no-extensions` suppresses all extension discovery. To preserve Herdr state updates (`~/.pi/agent/extensions/herdr-agent-state.ts`), it must be retained with `-e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts`.
4. **Herdr:**
   - Version: `herdr 0.9.5`
   - Binary: `/Users/corvette/.local/bin/herdr`
   - Help verified for command groups: `agent`, `pane`, `workspace`, `tab`, `session`, `integration`.
   - Supported agent kinds in `herdr agent start --help` (24 kinds total):
     `pi, claude, codex, gemini, cursor, devin, agy, cline, omp, mastracode, opencode, copilot, kimi, kiro, droid, amp, grok, hermes, kilo, qodercli, qwen, letta, maki, muse`.
5. **cmux:**
   - Version: `cmux 0.65.2 (111) [9d01f956c]`
   - Binary: `/Applications/cmux.app/Contents/Resources/bin/cmux`
   - App: `/Applications/cmux.app`
   - Binary execution verified. Absolute invocation is fully sufficient. **Not currently in `$PATH`** (`which cmux` fails); persistent `$PATH` edit is optional.
   - *Warning:* Direct execution of `/Applications/cmux.app/Contents/MacOS/cmux` launches the GUI app bundle, not the CLI wrapper.
6. **opencode (optional):**
   - Version: `opencode v2.0.32`
   - Binary: `/Users/corvette/.opencode/bin/opencode`
   - Verified present; marked untested and unavailable for required council roles.
7. **mcode (MiniMax Code):**
   - Version: `0.6.12`
   - Binary: `/Users/corvette/.minimax-code/bin/mcode`
   - **Critical finding:** `mcode` and `minimax` are **not among the 24 supported kinds** in Herdr 0.9.5's CLI argument parser. (Note: `mastracode` is a distinct binary from Mastra at `mastra.ai`, not a MiniMax alias).
   - This native kind gap is scoped strictly to the installed Herdr 0.9.5 kind enum and inspected local configurations, not global impossibility.
8. **Sol Proxy:**
   - Listening port verified via non-mutating TCP probe (`connect_ex(('127.0.0.1', 8787)) == 0`). Upstream model identity remains unverified.

---

## 4. Whitelisted Configuration Reads

In strict compliance with preflight requirements:
- **No credential or token dumps:** Only routing and model keys were read.
- **Hermes:** `~/.hermes/config.yaml` configures:
  - `model.default`: `gpt-6.1-sol-900k`
  - `model.provider`: `custom`
  - `model.base_url`: `http://127.0.0.1:8787/w/hermes/v1`
  - `agent.reasoning_effort`: `high`
  - MiniMax providers: `minimax.enabled: false`, `minimax-cn.enabled: false`
- **Pi:** `~/.pi/agent/models.json` configures:
  - Provider `workbuddy` with `baseUrl`: `http://127.0.0.1:8788/v1`
  - Model: `deepseek-v4.1-flash`
  - No MiniMax provider is configured.
- **Herdr:** `~/.config/herdr/config.toml` contains only safe UI preferences:
  - `onboarding`: `false`
  - `[theme] name`: `"gruvbox"`, `auto_switch`: `false`
  - `[ui] status_indicators`: `"symbols"`
  - `[ui.toast] delivery`: `"system"`

---

## 5. Role Mapping Proposal & Blocker Identification

We propose the following exact kind, model, and native settings for the Herdr execution environment:

1. **Hermes Coordinator:**
   - Herdr Kind: `hermes`
   - Native launch arguments: `--cli --ignore-rules --in /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout -m gpt-6.1-sol-900k --reasoning high`
   - Command: `herdr agent start coord --kind hermes --pane <id> -- --cli --ignore-rules --in /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout -m gpt-6.1-sol-900k --reasoning high` (RPC syntax example only; a separate control pane would be required. Operator startup uses only direct interactive launch per Section 6)
2. **agy Implementer:**
   - Herdr Kind: `agy`
   - Native launch arguments: `--model gemini-3.8-flash-high --effort high --sandbox`
   - Command: `herdr agent start worker --kind agy --pane <id> -- --model gemini-3.8-flash-high --effort high --sandbox`
   - Boundary note: PROPOSED UNTESTED MAPPING. `--sandbox` is an advertised terminal restriction, not certified filesystem containment.
3. **Critic 2 (Pi / WorkBuddy DeepSeek):**
   - Herdr Kind: `pi`
   - Native launch arguments: `--provider workbuddy --model deepseek-v4.1-flash --thinking high --tools read,grep,find,ls --no-mcp --no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts --no-skills --no-context-files --session-dir /tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/pi-sessions`
   - Command: `herdr agent start critic_deepseek --kind pi --pane <id> -- --provider workbuddy --model deepseek-v4.1-flash --thinking high --tools read,grep,find,ls --no-mcp --no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts --no-skills --no-context-files --session-dir /tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/pi-sessions`
   - Boundary note: Read-only built-in tools + `--no-mcp` is a tool-level restriction and MCP suppression, not universal filesystem sandboxing.
4. **Critic 1 (MiniMax / mcode) — UNRESOLVED PREREQUISITE:**
   - Herdr 0.9.5 has no `mcode` or `minimax` kind in its argument validator.
   - Inspected configs show no pre-configured active MiniMax route in `hermes` or `pi`.
   - No supported Herdr launch command is proposed; no command invocation is guessed.
   - Per frozen rules, the orchestrator cannot substitute an unapproved kind or model.
   - The pilot prompt must STOP before P02 dispatch if an authorized Herdr-native mapping is missing; never mix T3 critics into this pilot, install wrappers, enable unverified routes, or substitute based on suggestions.
   - Clearly distinguish contexts: Migration review council uses T3 `delegate_task` (`mcode` with `MiniMax-M3.1-Flash-Preview:v:thinking`), which works natively. The Herdr runtime pilot role is separate and requires explicit user decision before pilot launch.

---

## 6. Proposed Sessions & Human Startup Handoff

- **Dedicated Project Session:** `skill-lens`
- **Isolated Pilot Test Session:** `skill-lens-pilot-20261017`

### Recommended Direct Human Startup Sequence (Interactive, Unrun)
1. User launches: `herdr --session skill-lens-pilot-20261017`
2. Inside the pane, verify `test "${HERDR_ENV:-}" = 1 && echo "HERDR_ENV confirmed: $HERDR_PANE_ID"`. Derive real session identity via documented in-Herdr status/readback (`herdr status --json`, whose help is verified; live fields are unverified) without requiring unevidenced `HERDR_SESSION_NAME`.
3. Change into the prepared synthetic fixture:
   ```bash
   cd /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout
   ```
4. Launch Hermes coordinator directly at the shell prompt:
   ```bash
   hermes --cli --ignore-rules --in /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout -m gpt-6.1-sol-900k --reasoning high
   ```
5. Supply the explicit pilot brief interactively from [`docs/validation/two-surface-orchestration/2026-10-17/implementation/human-pilot-brief.md`](./human-pilot-brief.md).

*(Note: The optional alternate RPC startup flow via `herdr agent start` was removed to eliminate unneeded failure paths and preserve a simple, documented direct interactive flow).*

---

## 7. Synthetic Fixture & Environment Isolation Plan

To ensure test isolation without copying auth or user skill directories:
- **Prepared Synthetic Checkout:** Located at `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout` with baseline `fixture.txt` (SHA256: `462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e`).
- **Command-Local HOME and XDG for Fixture Commands:**
  Fixture commands use per-command prefixing:
  ```bash
  HOME="/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-home" XDG_CONFIG_HOME="/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-xdg" <command>
  ```
  Shell-wide export of fake `HOME` or `XDG` in parent agent shells is strictly avoided, preventing accidental redirection of subsequent parent agent auth, extension contexts, and settings.
- **Original Repository Read-Only Preservation:**
  The original repository (`/Users/corvette/Documents/Projects Coding/Skill Lens`) is strictly preserved as **READ-ONLY** for the pilot coordinator.
- **Owned Artifacts Directory:**
  All pilot evidence and logs are written exclusively to:
  `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/`
  T3 Sol subsequently inspects and retains sanitized results in allowed repository records.
- **Scoping Controls:**
  - `pi`: `--tools read,grep,find,ls --no-mcp --no-skills --no-context-files --no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts`.
  - `hermes`: `--ignore-rules --in /tmp/.../synthetic-checkout`.
  - `agy`: `--sandbox` for terminal restrictions.

---

## 8. Stopping Boundary

Work on this dispatch is strictly complete at the preflight boundary:
- Allowed evidence and proposal files updated.
- Synthetic pilot handoff brief updated at `implementation/human-pilot-brief.md` with absolute read-only paths and owned artifact output contract.
- No live Herdr sessions created or controlled.
- No pilot cases (P01–P09) executed or claimed; all remain PENDING.
- No Phase C documentation edits made.
- Next action: Hand off setup proposal to user and coordinator Sol for approval.
