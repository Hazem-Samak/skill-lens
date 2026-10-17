> Historical raw research; not approved launch instructions. The coordinator reproduced errors about /tmp sandbox writes, fail-open sandbox behavior and impossible file fallback. See the forthcoming correction/adjudication before using this report. Researcher is Gemini; its EFFECTIVE_MODEL candidate labels are not execution identity proof.

# Grok Native Candidate Controls for Pilot Critic Amendment

**Date:** 2026-10-17  
**Status:** Research / Preflight Evidence (Read-Only; Unrun Proposal)  
**Target Amendment:** Replace unmapped MiniMax (`mcode`) Critic 1 with native Herdr `grok` kind in isolated pilot session `skill-lens-pilot-20261017`  
**Reference Plan:** `docs/plans/2026-10-17-two-surface-orchestration.md` Sections 4.2–5, 6B, 7  
**Validation Setup:** `docs/validation/two-surface-orchestration/2026-10-17/setup.md`  

---

## 1. Effective Model Identity

- **Requested Candidate:** Grok critic role (Critic 1) replacing MiniMax `mcode`. Model: `grok-4.7`. Reasoning effort: pending user choice (`none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`; local config default: `medium`).
- **Configured Identity (`~/.grok/config.toml`):**
  - `models.default`: `"grok-4.7"`
  - `models.default_reasoning_effort`: `"medium"`
  - `ui.permission_mode`: `"always-approve"` (requires session-scoped command-line override)
- **Provider-Confirmed Status:**
  - `grok models` execution verifies account login with `grok.com`, default model `grok-4.7`, available model `* grok-4.7 (default)`.
  - In accordance with Section 4.4 and plan rules, upstream served-model identity remains unverified at runtime until live evaluation.

---

## 2. Verified Command, Help & Integration Evidence

### A. CLI Binary & Help
- **Path & Version:** `/Users/corvette/.grok/bin/grok` reports `grok 1.0.62 (1474f9cbdd91) [stable]`.
- **Advertised CLI Options (`grok --help`):**
  - Model & Reasoning: `-m, --model <MODEL>`, `--reasoning-effort <EFFORT>` (aliases: `--effort`).
  - Tool Controls: `--tools <TOOLS>`, `--disallowed-tools <TOOLS>`, `--allow <RULE>`, `--deny <RULE>`.
  - Subagent Controls: `--no-subagents` ("Disable subagent spawning").
  - Web Controls: `--disable-web-search` ("Disable web search and web fetch tools").
  - Execution Scope: `--cwd <CWD>`, `-s, --session-id <SESSION_ID>` (new conversation UUID without resume).
  - Safety & Sandbox: `--permission-mode <MODE>` (`default`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, `plan`), `--sandbox <PROFILE>` (`off`, `workspace`, `devbox`, `read-only`, `strict`).
  - Terminal Rendering: `--minimal` (native scrollback), `--no-alt-screen` (inline), `--fullscreen`.
  - System Prompt & Rules: `--system-prompt-override <PROMPT>`, `--rules <RULES>`.

### B. Herdr Integration Evidence
- **Kind Support:** `/Users/corvette/.local/bin/herdr agent start --help` enumerates `grok` in its 24 supported kinds:
  `pi, claude, codex, gemini, cursor, devin, agy, cline, omp, mastracode, opencode, copilot, kimi, kiro, droid, amp, grok, hermes, kilo, qodercli, qwen, letta, maki, muse`.
- **Installed State Hook:**
  - File: `/Users/corvette/.grok/hooks/herdr.json` configures `SessionStart` command: `sh '/Users/corvette/.grok/hooks/herdr-agent-state.sh' session`.
  - Script: `/Users/corvette/.grok/hooks/herdr-agent-state.sh` (`HERDR_INTEGRATION_ID=grok`, `HERDR_INTEGRATION_VERSION=2`) connects to `HERDR_SOCKET_PATH` over Unix domain socket when `HERDR_ENV=1` and reports `pane.report_agent_session` with `agent: "grok"`, `pane_id`, and `agent_session_id`.
  - Herdr Binary Strings: Matches terminal title regex `(?:^| - )grok$`.

### C. Local Documentation Evidence (`~/.grok/docs/user-guide/`)
- **Tool Filtering (`14-headless-mode.md`):**
  - `--tools` provides an allowlist of built-in tool IDs: `read_file,grep,list_dir`.
  - `--disallowed-tools` removes tools: `run_terminal_cmd,web_search,web_fetch,write,search_replace,Agent`.
  - Explicit confirmation: `--tools`, `--disallowed-tools`, `--reasoning-effort`, `--permission-mode`, `--allow`, and `--deny` work in both interactive TUI and headless modes.
- **Permission Rules (`22-permissions-and-safety.md`):**
  - `deny` rules take highest precedence over allow and default modes (`deny > ask > allow`).
  - Rules `--deny 'Bash(*)'`, `--deny 'Edit(*)'`, and `--deny 'MCPTool(*)'` unconditionally reject shell commands, file edits, and MCP invocations.
- **Cross-Session Memory (`13-memory.md`):**
  - Memory is disabled by default in Grok. No `[memory]` section exists in `~/.grok/config.toml`.
  - Process force-disable supported via `GROK_MEMORY=0` and hidden/unadvertised CLI flag `--no-memory` (verified exit code 0 on CLI).
- **Sandbox Profile (`18-sandbox.md`):**
  - Built-in `read-only` profile uses macOS Seatbelt: FS Read everywhere, FS Write restricted to `~/.grok/` and `/tmp` + `/var/tmp`. Blocks writes to project working directory.
  - *Boundary fact:* Child-process network blocking is Linux-only (seccomp). On macOS Seatbelt does not block network; network isolation relies on tool restriction (`--disable-web-search`, denying `run_terminal_cmd`/`Bash`).

---

## 3. Proposed Native Launch Command (UNRUN)

In accordance with Herdr syntax `herdr agent start <NAME> --kind grok --pane <PANE_ID> [OPTIONS] [-- [AGENT_ARG]...]`:

```bash
# UNRUN PROPOSAL: Launch Grok as Critic 1 in existing Herdr shell pane
herdr agent start critic_grok --kind grok --pane <available-shell-pane-id> -- \
  --model grok-4.7 \
  --reasoning-effort <effort-choice> \
  --cwd /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout \
  --session-id <freshly-generated-uuid4> \
  --tools "read_file,grep,list_dir" \
  --disallowed-tools "run_terminal_cmd,web_search,web_fetch,write,search_replace,Agent" \
  --no-subagents \
  --disable-web-search \
  --deny "Bash(*)" \
  --deny "Edit(*)" \
  --deny "MCPTool(*)" \
  --permission-mode default \
  --sandbox read-only \
  --no-memory
```

*Note on Environment:* In the pane prior to launch or in pane setup, `GROK_MEMORY=0` and `GROK_SUBAGENTS=0` can be exported to ensure defense-in-depth against automatic memory recall or background delegation.

---

## 4. Exact Unresolved Controls & Pilot Stop Conditions

1. **Interactive TUI Argument Parsing of Tool Allowlist:**
   - *Evidence:* Docs confirm `--tools` works in TUI, but runtime behavior inside Herdr pane is unvalidated.
   - *Stop Condition:* If Grok fails to initialize with `--tools` or prints tool-loading errors, halt. Do not remove tool restrictions to force startup.
2. **Override of Global `ui.permission_mode = "always-approve"`:**
   - *Evidence:* `~/.grok/config.toml` sets `permission_mode = "always-approve"`. CLI options `--permission-mode default` and `--deny` rules are documented to override config.
   - *Stop Condition:* P05 probe must verify that an attempted write to `fixture.txt` is rejected. If Grok executes an edit under always-approve, halt immediately.
3. **macOS Sandbox Network Limitation:**
   - *Evidence:* Seatbelt `read-only` does not restrict child network on macOS.
   - *Resolution:* Bounded by tool removal (`--disable-web-search` and disabling `run_terminal_cmd` / `Bash`).
4. **Complete Response Capture (P04):**
   - *Evidence:* Grok interactive TUI uses alt-screen by default. Pane screen-scraping may truncate long reports.
   - *Resolution:* Per Section 4.2, report recovery must be verified. If TUI readback is truncated, the pre-authorized temporary Markdown output (`/tmp/.../pilot-artifacts/grok-report.md`) is used as fallback. Untested kinds cannot claim full-screen readback without P04 proof.

---

## 5. Impact on Pilot Cases P01–P09

- **P01 (Hermes coordinator entry):** Unchanged. Hermes operates inside `skill-lens-pilot-20261017`.
- **P02 (Two independent critics in one wave):** DIRECT BENEFIT. Replaces blocked MiniMax (`mcode`) with natively supported Herdr kind `grok`. Evaluates Grok and Pi (DeepSeek) concurrently with distinct tokens and targets.
- **P03 (agy implementer):** Unchanged.
- **P04 (Full-screen/long report and fallback):** Directly exercises Grok's report output in Herdr pane, validating native readback vs. temporary file fallback.
- **P05 (Permission/question handling):** Directly exercises Grok's read-only boundary via denied-write probe to synthetic fixture.
- **P06 (Fast completion and ambiguous delivery):** Exercises Grok's `SessionStart` hook (`herdr-agent-state.sh`) and pane state lifecycle.
- **P07 (Active cancellation / background activity):** Tests clean termination of Grok process and child commands in pane without leaving orphans.
- **P08 (Detach and controlled restart):** Tests human restart of `skill-lens-pilot-20261017` with Grok session restoration or clean restart.
- **P09 (cmux interaction and cleanup):** Unchanged.

---

## 6. Permissions and Non-Widening Guarantee

- **No Widening:** No global configuration edits (`~/.grok/config.toml` is unedited), no proxy modifications, no credential exposure, and no persistent shell shims.
- **Confined Bounds:** Execution is confined to `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout` with reports directed to external pilot artifacts. Original repository remains strictly read-only.
