> Raw Gemini correction report. Coordinator qualification: these sources establish advertised controls and a local preflight gap, not global impossibility or 100% runtime readiness. Optional compatibility scans have per-process toggles. The second Pi route remains a user-selection proposal, never an authorized fallback. See pilot-critic-research-adjudication.md.

# Primary-Source Corrections & Missing-Control Analysis: Grok Pilot Critic

**Date:** 2026-10-17  
**Status:** Focused Primary-Source Correction & Gap Report (Read-Only Research)  
**Destination Path:** `/tmp/skill-lens-herdr-critic-amendment-20261017/grok-native-controls-corrections.md`  
**Reference Plan:** `docs/plans/2026-10-17-two-surface-orchestration.md` Sections 4.2–5, 6B, 7  
**Validation Setup:** `docs/validation/two-surface-orchestration/2026-10-17/setup.md`  

---

## 1. Primary-Source Corrections to Task 1 Findings

### A. Sandbox Write Scope & Degradation Behavior (`18-sandbox.md`)
- **Correction on `/tmp` Write Grants:** In [`18-sandbox.md:31`](file:///Users/corvette/.grok/docs/user-guide/18-sandbox.md#L31) (Built-in Profiles table) and [`18-sandbox.md:46`](file:///Users/corvette/.grok/docs/user-guide/18-sandbox.md#L46) (Profile Details), the built-in `read-only` profile explicitly grants filesystem write access to `~/.grok/` and temporary directories (`/tmp`, `/var/tmp`, plus macOS temporary directories). Because the pilot's synthetic checkout resides at `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout`, **the Seatbelt OS-level sandbox explicitly allows writes to the fixture directory**. It does *not* block fixture writes at the OS layer and does *not* confine writes to owned subdirectories.
- **Correction on Sandbox Degradation:** [`18-sandbox.md:201`](file:///Users/corvette/.grok/docs/user-guide/18-sandbox.md#L201) documents: *"If a built-in profile fails to apply, Grok warns and continues without enforcement..."* Under the frozen plan, an un-enforced degradation cannot be accepted. The pilot must halt immediately upon any sandbox warning.
- **Evidence Separation:** Tool-level deny rules and before/after file fingerprints are distinct evidence from kernel sandboxing; no claim of universal filesystem isolation may be made.

### B. Read-Only Tools Preclude Report-File Output (`14-headless-mode.md`)
- **Correction on File Fallback:** If Grok is launched with `--tools "read_file,grep,list_dir"` and deny rules on `Edit(*)`, `write`, and `search_replace`, the agent has **zero file writing capability**. Prescribing an external Markdown report fallback (`/tmp/.../grok-report.md`) is impossible without widening permissions to add write tools.
- **P04 Consequence:** In accordance with Section 4.2 and P04, if complete report readback from the native Herdr pane / TUI cannot be recovered, **P04 must be marked unavailable and execution halted**. No permission widening (e.g. enabling file writes) is permitted to manufacture a pass.

### C. Researcher Identity vs. Candidate Model Identity (EFFECTIVE_MODEL)
- **Researcher Sub-Agent (Self):**
  - *Requested / Configured:* Gemini 3.8 Flash High (T3 harness worker dispatch).
  - *Status:* Upstream served model identity unverified (T3 receipt).
- **Candidate Pilot Critic Model:**
  - *Requested:* Grok critic candidate (`grok-4.7`), reasoning effort pending user decision.
  - *Configured (`~/.grok/config.toml`):* `models.default = "grok-4.7"`, `default_reasoning_effort = "medium"`.
  - *Provider-Confirmed:* `grok models` reports `grok-4.7` logged in with `grok.com`. Upstream served identity remains unverified at runtime.

---

## 2. Discovery & Context Isolation Gap Analysis

Section 6B (Phase B) mandates: *"Tests use synthetic HOME/XDG and fixtures, never live user skills... Record which native session controls establish that separation; if it cannot be established, stop."*

### A. Automatic Rule Import (`12-project-rules.md`)
- **Discovery Mechanism:** [`12-project-rules.md:35-43`](file:///Users/corvette/.grok/docs/user-guide/12-project-rules.md#L35-L43) and [`12-project-rules.md:62-66`](file:///Users/corvette/.grok/docs/user-guide/12-project-rules.md#L62-L66) state that Grok unconditionally scans and auto-loads home-level rules from `$GROK_HOME/rules/` (`~/.grok/rules/`), as well as compatibility sources (`~/.claude/rules/`, `~/.cursor/rules/`, and home `CLAUDE.md`).
- **Missing CLI Control:** Grok has no `--no-rules`, `--no-context-files`, or `--ignore-rules` flag. The advertised `--rules <RULES>` option only appends rules; it does not suppress auto-loading. `--system-prompt-override` only replaces the base prompt body, leaving rule injection intact.

### B. Automatic Personal Skill Discovery (`08-skills.md`)
- **Discovery Mechanism:** [`08-skills.md:27`](file:///Users/corvette/.grok/docs/user-guide/08-skills.md#L27) states Grok automatically discovers user skills from `~/.grok/skills/` (and commands), `~/.claude/skills/`, and `~/.cursor/skills/`.
- **Missing CLI Control:** There is no `--no-skills` flag in Grok. Hiding skills requires editing `[skills] ignore` in `~/.grok/config.toml` ([`08-skills.md:37`](file:///Users/corvette/.grok/docs/user-guide/08-skills.md#L37)), which is prohibited by frozen bounds (no global configuration changes).

### C. Ineffectiveness of `GROK_CONFIG` Overlay (`05-configuration.md`)
- **Overlay Choke Point:** [`05-configuration.md:30`](file:///Users/corvette/.grok/docs/user-guide/05-configuration.md#L30) specifies: *"The overlay is confined, fail-closed, to an allowlist of soft settings (`models`, `features`, a narrowed `toolset`, and a `shell_environment_policy`...); every other table is dropped at the choke point, so the overlay cannot spawn commands, set auth policy, redirect network traffic, elevate trust, or add a discovery source."*
- Consequently, `GROK_CONFIG` cannot inject `[skills]` or `[paths]` tables to suppress discovery.

### D. The Isolation vs. Integration Conflict
- Redirecting `$GROK_HOME` or `$HOME` to an external empty directory breaks the installed Herdr integration (`~/.grok/hooks/herdr.json` and `herdr-agent-state.sh`) and drops CLI authentication (`~/.grok/auth.json`).
- Copying credentials or hooks into a custom directory is prohibited by setup rules.
- **Finding:** Grok has **no existing process- or session-scoped mechanism** to suppress auto-import of live user skills and home rules while preserving Herdr hooks and auth. This constitutes a **true pre-pilot missing-control gap** under Section 6B.

---

## 3. MCP Meta-Tools & Network Surface

- **Tool Preservation:** [`14-headless-mode.md:123`](file:///Users/corvette/.grok/docs/user-guide/14-headless-mode.md#L123) confirms: *"The final toolset retains requested tools plus always-on MCP meta-tools."* Passing `--tools` leaves MCP meta-tools present.
- **Invocation vs. Startup/Network:** Adding `--deny 'MCPTool(*)'` rejects tool execution by the model, but does not guarantee MCP daemon processes are not spawned or that background network connections / hooks are inhibited. No network isolation guarantee exists on macOS under the `read-only` profile.

---

## 4. Comparison with Pre-Configured Pi Native Alternative

Because Grok exhibits a demonstrable missing-control gap for discovery isolation, we compare the single already-configured native alternative: a second independent **Pi** agent instance.

### A. Whitelisted Configuration Evidence (`~/.pi/agent/models.json`)
Inspection of non-secret provider metadata in `~/.pi/agent/models.json` confirms:
- **Provider `xkiro`:** `baseUrl = "https://api.xkiro.com/v1"`, models include `"qwen/qwen3.8-max:free"` and `"qwen/qwen3.8-omni-flash:free"`.
- **Provider `anymodel` (fallback):** `baseUrl = "https://anymodel.org/v1"`, models include `"qwen/qwen3.8-max"`.

### B. Native Control Comparison

| Capability / Requirement | Grok Candidate (`grok-4.7`) | Pi Alternative (`xkiro/qwen/qwen3.8-max:free`) |
|---|---|---|
| **Herdr Native Kind** | Supported (`grok`) | Supported (`pi`) |
| **Herdr State Hook** | Preserved via `~/.grok/hooks/herdr.json` | Preserved via `-e ~/.pi/agent/extensions/herdr-agent-state.ts` |
| **Suppress Live Skills** | **BLOCKED:** No `--no-skills` flag; requires global config edit | **PROVEN:** Supported natively via `--no-skills` |
| **Suppress Rule / Context Import** | **BLOCKED:** No `--no-rules` or `--no-context-files` flag | **PROVEN:** Supported natively via `--no-context-files` |
| **MCP Suppression** | Denies `MCPTool(*)`; meta-tools remain; daemon startup unblocked | **PROVEN:** Supported natively via `--no-mcp` |
| **Read-Only Tool Enforcement** | `--tools "read_file,grep,list_dir"` + `--deny 'Bash(*)'` | **PROVEN:** `--tools read,grep,find,ls` (drops bash/write/edit) |
| **Session Isolation** | `--session-id <UUID>` (writes to `~/.grok/sessions/`) | **PROVEN:** `--session-dir <external-dir>` |
| **Upstream Verification** | Unverified at runtime | Unverified at runtime |

### C. Proposed Pi Critic 1 Command (UNRUN Alternative)

```bash
# UNRUN PROPOSAL: Second independent native Pi critic using pre-configured xkiro Qwen model
herdr agent start critic_qwen --kind pi --pane <available-shell-pane-id> -- \
  --provider xkiro \
  --model qwen/qwen3.8-max:free \
  --thinking high \
  --tools read,grep,find,ls \
  --no-mcp \
  --no-extensions \
  -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts \
  --no-skills \
  --no-context-files \
  --session-dir /tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/pi-critic-qwen-sessions
```

*Note:* Herdr does not require distinct kinds for distinct agents; two independent `pi` agents (Critic 1 on `xkiro/qwen3.8-max:free` and Critic 2 on `workbuddy/deepseek-v4.1-flash`) satisfy the independent-critic requirement under Section 4.4 without any missing controls.

---

## 5. Summary Conclusion for Amendment

1. **Grok Status:** Grok possesses native Herdr kind support and working state hooks, but suffers from an unresolvable **pre-pilot missing-control gap** regarding live skill/rule discovery suppression under Section 6B.
2. **Alternative Ready:** The pre-configured `pi` instance on `xkiro/qwen/qwen3.8-max:free` provides 100% of required native isolation controls (`--no-skills`, `--no-context-files`, `--no-mcp`, `--session-dir`) with zero configuration edits.
3. **User Decision Boundary:** This comparison is research evidence for the user's consideration, not an autonomous choice. No model or effort choice has been adopted or executed.
