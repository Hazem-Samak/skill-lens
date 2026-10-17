> Coordinator annotation: This is a historical, verbatim worker report. Its Pi confinement and blanket route claims are superseded by preflight-adjudication-r1.md. Do not treat it as current setup instructions.

# Technical Investigation Report: Herdr 0.9.5, Critic Routing, and Execution Preflight

**Investigator:** Gemini 3.8 Flash High (Read-Only Technical Research Sub-agent)  
**Date:** 2026-10-17  
**Frozen Plan:** [`docs/plans/2026-10-17-two-surface-orchestration.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/plans/2026-10-17-two-surface-orchestration.md) @ `58d48cea483804b22767b381c6edd8274fe6ad44`  
**Inspected Proposals:** [`setup.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/two-surface-orchestration/2026-10-17/setup.md) & [`implementation/preflight.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/two-surface-orchestration/2026-10-17/implementation/preflight.md) under `docs/validation/two-surface-orchestration/2026-10-17/`  
**Research Notes:** Saved outside the repository to `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/research/investigation-findings.md`

---

## 1. Observed Facts & Installed CLI Metadata

### A. Herdr 0.9.5 Agent Kinds vs. MiniMax `mcode`
- **Herdr Version & Binary:** `herdr 0.9.5` at `/Users/corvette/.local/bin/herdr`.
- **Supported Kinds (24):** Inspected via `herdr agent start --help`:
  ```text
  pi, claude, codex, gemini, cursor, devin, agy, cline, omp, mastracode, opencode, copilot, kimi, kiro, droid, amp, grok, hermes, kilo, qodercli, qwen, letta, maki, muse
  ```
  Neither `mcode` nor `minimax` is an accepted kind. Passing either causes `herdr agent start` argument validation to fail.
- **`mastracode` vs. `mcode` Distinction:**
  - `mcode` is **MiniMax Code CLI** (v0.6.12) installed at `/Users/corvette/.minimax-code/bin/mcode`. Config resides in `~/.minimax-code/`.
  - Herdr kind `mastracode` maps to canonical executable `mastracode` (from the Mastra agent framework, `mastra.ai`). `herdr integration status` reports its hook path as `/Users/corvette/.mastracode/hooks/herdr-agent-state.sh`. `mastracode` is **not installed** (`which mastracode` exits `1`).
  - `mastracode` and `mcode` are distinct binaries from different vendors. Aliasing or declaring `--kind mastracode` for `mcode` would invoke a missing binary and falsely report the agent kind.
- **Verdict:** Herdr 0.9.5 **cannot** run `mcode`/MiniMax natively without adding a provider/model route, custom wrapper/plugin, aliasing another executable, changing global config, or falsely declaring a different kind.

### B. Pre-Configured MiniMax Routes in Existing Supported Kinds
Only safe identifier fields (excluding auth/tokens) were inspected in existing agent configs:
- **Hermes (`/Users/corvette/.hermes/config.yaml`):**
  - Contains sections `minimax:` and `minimax-cn:`, but both are explicitly marked `enabled: false`.
  - Configured active providers are `custom` (Sol proxy `gpt-6.1-sol-900k`), `openai-codex`, `openrouter`, `orcarouter`, `river`, `workbuddy`, `anymodel`, `kiosapi`, `nine-router`, and `xkiro`. None route to MiniMax.
- **Pi (`/Users/corvette/.pi/agent/models.json`):**
  - Configured providers: `anymodel`, `kiosapi`, `nine-router`, `openrouter`, `orcarouter`, `river`, `tokenharbor`, `xkiro`, `workbuddy`, `llama-cpp`.
  - No MiniMax provider or model endpoint is configured.
- **Verdict:** There is **no pre-existing compliant native route** for MiniMax configured in Hermes or Pi. Running MiniMax via Hermes or Pi requires modifying global configuration files to enable the provider.

### C. `cmux` Absolute Invocation vs. PATH Edits
- **Binary Locations:**
  - CLI wrapper: `/Applications/cmux.app/Contents/Resources/bin/cmux`
  - App bundle binary: `/Applications/cmux.app/Contents/MacOS/cmux`
- **Execution Proof:** Invoking `/Applications/cmux.app/Contents/Resources/bin/cmux --version` succeeded with exit code `0` (`cmux 0.65.2 (111) [9d01f956c]`).
- **Verdict:** Absolute invocation of `/Applications/cmux.app/Contents/Resources/bin/cmux` is **fully sufficient** and requires **zero PATH edits**.
- *Caution:* Invoking `/Applications/cmux.app/Contents/MacOS/cmux` directly starts the macOS GUI application and control server instead of the CLI wrapper.

### D. Hermes and Pi Native Flags: Context Skipping, Tool Confinement, and Herdr Integration

#### 1. Pi (`/Users/corvette/.local/bin/pi`)
- **Herdr Integration Mechanism:** `pi` integrates via an extension file at `/Users/corvette/.pi/agent/extensions/herdr-agent-state.ts` (`herdr integration status`).
- **Context Skipping:** `--no-skills` (`-ns`) and `--no-context-files` (`-nc`) disable discovery of `~/.pi/agent/skills`, `AGENTS.md`, and `CLAUDE.md`.
- **Preflight Defect:** The preflight proposal recommends `--no-extensions` (`-ne`). However, `--no-extensions` disables all extension discovery, which **disables `herdr-agent-state.ts`**, completely severing Herdr agent state updates.
- **Correction:** To disable external extensions while retaining Herdr integration, pass:
  ```bash
  --no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts --no-skills --no-context-files
  ```
- **Tool Confinement:** Pi natively supports `--tools read,grep,find,ls` to strictly confine the agent to read-only tools without file edits or bash.

#### 2. Hermes (`/Users/corvette/.local/bin/hermes`)
- **Herdr Integration Mechanism:** Hermes integrates via a plugin at `/Users/corvette/.hermes/plugins/herdr-agent-state/__init__.py`.
- **Context Skipping:** `--ignore-rules` skips auto-injection of `AGENTS.md`, `SOUL.md`, `.cursorrules`, memories, and preloaded skills.
- **Integration Preservation:** Using `--safe-mode` would disable all plugins, severing Herdr integration. Using `--ignore-rules` alone preserves plugins (retaining Herdr integration) while skipping repository rules.
- **Tool Confinement Limitation:** Hermes **cannot** restrict tools to specific read-only commands via native flags. Hermes only provides `-t, --toolsets <toolsets>` (e.g., `-t file`). The `file` toolset includes write/edit capabilities, and `-t terminal` allows arbitrary shell execution. Confinement to read-only actions for Hermes must rely on prompt instructions or session policy, not CLI flags.

---

## 2. Claims Remaining Unverified
1. **Upstream Model Identities:** Non-mutating TCP connectivity to Sol (`127.0.0.1:8787`) was verified, but upstream model generation and identity remain unverified (network model calls are strictly prohibited outside authorized execution).
2. **WorkBuddy Route (`127.0.0.1:8788`):** Upstream model delivery of `deepseek-v4.1-flash` is unverified by live generation.
3. **Live Herdr Server Session State:** No live Herdr server queries or socket sessions were run outside a genuine `HERDR_ENV`.

---

## 3. Concrete Corrections to Preflight Proposals (`setup.md` & `preflight.md`)

| Section | Current Preflight Claim | Concrete Correction |
|---|---|---|
| **Pi Flags** (`setup.md` §7, `preflight.md` §7) | Recommends `--no-skills --no-extensions` to isolate the environment. | **Incorrect:** `--no-extensions` disables `herdr-agent-state.ts`. Must be corrected to: `--no-skills --no-context-files --no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts`. |
| **`cmux` Requirement** (`setup.md` §2, §8) | States user must add directory to `$PATH` or use absolute path. | **Clarification:** Absolute path `/Applications/cmux.app/Contents/Resources/bin/cmux` works cleanly without PATH edits. Explicitly warn against calling `Contents/MacOS/cmux`. |
| **Critic 1 Role** (`setup.md` §4, `preflight.md` §5) | Flags MiniMax `mcode` as blocked without an explicit list of options. | **Correction:** Explicitly note that `mastracode` is not `mcode`, and no pre-configured fallback route exists in `hermes` or `pi` configs without config edits. |
| **Hermes Confinement** (`setup.md` §4) | Implies role confinement is equivalent across agents. | **Correction:** Explicitly note that unlike Pi's `--tools read,grep,find,ls`, Hermes cannot restrict tools to read-only via native flags. |

---

## 4. Minimum User Decision Required

Because current Herdr 0.9.5 cannot run `mcode`/MiniMax without violating the frozen constraints, the user must choose one of the following four paths before proceeding to Phase B execution:

1. **Option A (Hermes Config Route):** Authorize modifying `/Users/corvette/.hermes/config.yaml` to set `minimax.enabled: true` (using existing credentials in `~/.hermes/.env`), allowing Critic 1 to run through Herdr kind `hermes` with `-m minimax/<model>`.
2. **Option B (Two-Surface Division):** Retain MiniMax critic reviews inside T3 Code via native `delegate_task` (where `mcode` with `MiniMax-M3.1-Flash-Preview:v:thinking` is natively supported), while restricting the Herdr runtime pilot strictly to supported kinds (`hermes` coordinator, `agy` implementer, `pi` critic).
3. **Option C (Critic Engine Substitution):** Amend the Herdr pilot council roster to substitute Critic 1 with an already-configured, supported Herdr kind (e.g., a second `pi` instance routing to an active provider, or `opencode`).
4. **Option D (Custom Wrapper):** Authorize adding a custom agent integration/wrapper script under `~/.config/herdr/` or an executable shim to route a supported Herdr kind name to `mcode`.
