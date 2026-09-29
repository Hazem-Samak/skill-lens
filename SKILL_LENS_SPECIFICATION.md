# Skill Lens — Project Specification & Implementation Plan

> **"Your AI skills, in one place. And why each one is there."**

**Technical Positioning:** A local diagnostics and resolution engine for AI agent capabilities (`SKILL.md`).  
**Primary Interface:** Python CLI & Terminal UI (powered by `Typer` + `Rich`).  
**Architecture Model:** Agent-Agnostic, Registry-Driven, Read-Only Diagnostics First.  
**Execution Strategy:** 100% Vibe-Coding Ready (Modular, Test-Driven Sandbox, Zero Systems-Language Overhead).

---

## 1. Executive Summary & Vision

As developers adopt multiple AI coding agents (Claude Code, OpenAI Codex, Gemini CLI, OpenCode, Cursor, GitHub Copilot), their machines become cluttered with capability files (`SKILL.md` folders) scattered across global directories, monorepo subdirectories, and tool plugins.

Today, developers face three compounding frustrations:
1. **Blindness:** "What skills exist on my machine, and which agents can access them?"
2. **Shadowing / Drift:** "Why is Claude using an outdated `browser` skill instead of the one in my current project repository?"
3. **Duplication & Divergence:** "Do I have 4 identical copies of this skill, or did one branch diverge with custom edits?"

**Skill Lens** is the `which` / `brew doctor` for AI agent skills. It discovers, fingerprints, and explains agent skill resolution on a developer's machine with 100% local, explainable, and deterministic logic.

---

## 2. Core Mental Model & Terminology

Skill Lens rejects the naive assumption that a skill permanently "belongs" to a single agent. Instead, it models capability execution as:

```text
       Skill Name
           ↓
   Physical Installation (folder with SKILL.md on disk)
           ↓
    Runtime Resolution   (computed for: Agent + Working Directory + Settings)
           ↓
      Target Agent
```

### Resolution Output States
For any given query: `skill-lens why <skill_name> --agent <agent> --cwd <dir>`, the Resolver assigns each discovered copy one of four states:

1. **`[ACTIVE]`**: The exact copy the agent will load and execute in the target directory.
2. **`[SHADOWED]`**: A valid copy that the agent *would* recognize, but is hidden by a higher-priority copy (e.g. project `.agents/skills` overriding global `~/.agents/skills`).
3. **`[DISABLED]`**: Exists in an active discovery path, but turned off via agent configuration or CLI flag.
4. **`[UNSEARCHED]`**: Exists on disk, but this specific agent's search rules never look in that location.

### Identity, Fingerprints, and Variants
- **Symlinks are NOT duplicates:** A symbolic link pointing to a skill directory is counted as **1 installation with multiple entrypoints**, never as duplicate copies.
- **Content Fingerprint:** A SHA-256 hash computed over all non-ignored files in the skill directory (ignoring line endings `\r\n` vs `\n`, `.git`, and `.DS_Store`).
- **Variants vs. Versions:** If two skills share the name `browser` but have different hashes, they are flagged as `Variant A` and `Variant B` (with diffing support), rather than guessing which one is "newer".

---

## 3. Technology Stack & Vibe-Coding Architecture

To enable rapid, zero-friction AI pair-programming (vibe-coding) without compiler fights, the technology stack is intentionally chosen for readability, rich standard libraries, and instant feedback.

### The Stack
- **Language:** **Python 3.11+** (English-like syntax, rock-solid AI generation, universal across macOS/Linux/Windows).
- **CLI Framework:** **`Typer`** (type-hint driven command parsing, auto-generated `--help`, zero boilerplate).
- **Terminal UI & Output:** **`Rich`** (out-of-the-box colored tables, markdown rendering, status spinners, side-by-side diffs, and trees).
- **Data & Config:** **`tomllib`** (Python standard library for TOML) + **`PyYAML`** (for parsing `SKILL.md` frontmatter).
- **Testing & Verification:** **`pytest`** (fixture-based sandbox testing for 100% safe verification).
- **Packaging:** Standard `pyproject.toml` (compatible with `pip`, `uv`, and `uvx` for zero-install execution).

### Explicit Non-Goals for Initial Phases
- **NO Rust or GPUI:** Avoids the borrow-checker, unstable pre-1.0 crate APIs, and GUI layout debugging.
- **NO Cloud Backend / Telemetry:** 100% local-first and private.
- **NO File Modifications (Read-Only):** Skill Lens does not install, delete, or sync skills in v1. It diagnoses and explains.

---

## 4. Agent Discovery Registry

Discovery rules live in clean, declarative TOML files under `skill_lens/registry/agents/`. Adding support for a new agent requires adding a single configuration file, not modifying core discovery code.

### Registry Schema Example (`codex.toml`)
```toml
id = "codex"
name = "OpenAI Codex"
status = "verified"
evidence_url = "https://platform.openai.com/docs/guides/agent-skills"
verified_at = "2026-09-29"

[detection]
executable = "codex"
config_dir = "~/.codex"

[search_behavior]
walk_up_parents = true       # Walks up directory hierarchy until git root

# Precedence: higher number wins
[[sources]]
path = ".agents/skills"
scope = "project"
precedence = 100

[[sources]]
path = "~/.agents/skills"
scope = "global"
precedence = 50

[[sources]]
path = "/etc/codex/skills"
scope = "system"
precedence = 10
```

### Initial Target Agent Matrix
1. **OpenAI Codex:** Global `~/.agents/skills`, Project `.agents/skills` (searches upward to git root).
2. **Claude Code:** Global `~/.claude/skills`, Project `.claude/skills`, plugin-bundled skills.
3. **Gemini CLI:** Global `~/.gemini/skills`, `~/.agents/skills`, Project `.gemini/skills`, `.agents/skills`.
4. **OpenCode:** Global `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills`, Project `.opencode/skills`.
5. **Universal Fallback:** Scans any directory containing subfolders with `SKILL.md`.

---

## 5. CLI Command Specifications

### 1. `skill-lens scan`
Scans known agent paths and project directories, outputting an executive summary.
```text
$ skill-lens scan

╭─────────────────────────── Skill Lens: Discovered Skills ───────────────────────────╮
│ Detected Agents: Codex, Claude Code, Gemini CLI, OpenCode                           │
│ Total Skills: 24  •  Unique Names: 18  •  Variants: 3  •  Shadowed: 4               │
╰─────────────────────────────────────────────────────────────────────────────────────╯

┌────────────────────┬──────────┬─────────┬───────────────────────────────┬───────────┐
│ Skill Name         │ Scope    │ Origin  │ Path                          │ Agents    │
├────────────────────┼──────────┼─────────┼───────────────────────────────┼───────────┤
│ browser            │ Project  │ Local   │ ./my-app/.agents/skills/bro…  │ Codex, …  │
│ browser [Var B]    │ Global   │ Shared  │ ~/.agents/skills/browser      │ Codex, …  │
│ playwright-expert  │ Global   │ Claude  │ ~/.claude/skills/playwright   │ Claude    │
│ sql-optimizer      │ Global   │ Gemini  │ ~/.gemini/skills/sql-opt      │ Gemini    │
└────────────────────┴──────────┴─────────┴───────────────────────────────┴───────────┘
```

### 2. `skill-lens why <skill_name> [--agent <name>] [--cwd <path>]`
The signature diagnostic command. Explains why a specific skill copy wins in a directory.
```text
$ skill-lens why browser --agent codex --cwd ~/Projects/my-app

╭──────────────────────── Resolution: 'browser' for Codex ─────────────────────────╮
│ Target Agent: OpenAI Codex                                                        │
│ Working Dir:  /Users/dev/Projects/my-app                                          │
╰───────────────────────────────────────────────────────────────────────────────────╯

● [ACTIVE] (Winning Copy)
  Path:   /Users/dev/Projects/my-app/.agents/skills/browser
  Reason: Project-level skill (.agents/skills) has precedence (100) > global (50).
  Hash:   sha256:7f83b1...

○ [SHADOWED]
  Path:   /Users/dev/.agents/skills/browser
  Reason: Hidden by project-level copy above. Contains different content (Variant B).
  Hash:   sha256:1a49c2...

○ [UNSEARCHED]
  Path:   /Users/dev/.claude/skills/browser
  Reason: Discovered on disk, but Codex does not search ~/.claude/skills.
```

### 3. `skill-lens diff <skill_name>`
Shows a side-by-side terminal diff of differing variants bearing the same name.
```text
$ skill-lens diff browser
# Renders a side-by-side Rich Syntax diff between Variant A and Variant B
```

### 4. `skill-lens doctor`
Performs automated hygiene and health checks:
- ❌ Dangling symlinks (links pointing to deleted skill folders).
- ⚠️ Frontmatter syntax errors in `SKILL.md` (invalid YAML, missing name/description).
- ⚠️ Dangerous permissions (executable bash/python scripts without execute bits or unexpected binaries).
- ℹ️ Multi-variant divergence warnings.

---

## 6. Implementation Roadmap (The Agent-Executable Plan)

Each phase is self-contained, tested against a local mock sandbox, and committed to git before proceeding.

### Phase 1: Test Sandbox & Foundation
- Setup standard Python project structure with `pyproject.toml` (Typer, Rich, PyYAML).
- Create `tests/fixtures/mock_environment/` simulating:
  - Global `~/.agents/skills/browser`
  - Global `~/.claude/skills/browser` (different content)
  - Project `./project_alpha/.agents/skills/browser`
  - Broken symlink `./project_alpha/.agents/skills/broken-link`
  - Malformed `SKILL.md` (missing description)
- Write unit tests proving directory simulation works cleanly without reading real home folders.

### Phase 2: Metadata Parser & Scanner Engine
- Implement `skill_lens/core/parser.py`:
  - Extract YAML frontmatter (`name`, `description`, `version`, `tags`).
  - Calculate normalized SHA-256 fingerprint of the skill directory.
  - Follow symlinks to canonical paths.
- Implement `skill_lens/core/scanner.py`:
  - Traverse search roots safely with depth limits.
  - Return structured `SkillInstallation` objects.
- Build initial CLI command: `skill-lens scan --sandbox <path>` with formatted `Rich` tables.

### Phase 3: The Precedence Resolver (`skill-lens why`)
- Implement `skill_lens/registry/` loading agent TOML definitions.
- Implement `skill_lens/core/resolver.py`:
  - Given `(skill_name, agent_id, cwd)`:
  - Identify matching candidate installations.
  - Sort by agent precedence (project upward search > global agent > universal shared).
  - Categorize candidates into `[ACTIVE]`, `[SHADOWED]`, and `[UNSEARCHED]`.
- Implement `skill-lens why` CLI command with detailed Rich explanation panels.

### Phase 4: Real-System Detection & Doctor Diagnostics
- Connect scanner to actual Mac user locations (`~/.agents/skills`, `~/.claude/skills`, etc.) with permission-safe error handling.
- Implement `skill-lens doctor`:
  - Check YAML validity.
  - Detect broken symlinks.
  - Flag shadowing conflicts and variant divergence.
- Implement `skill-lens diff` using Rich diff renderer.

### Phase 5: Packaging & Distribution
- Add `uvx` / `pip` installation support.
- Add `--json` output flag to all commands for machine-readable piping to other AI agents.
- Produce comprehensive documentation and command reference.

---

## 7. Safety, Verification, and Trust Contract

1. **Strictly Read-Only:** Skill Lens never writes, moves, modifies, or deletes any files in user skill folders.
2. **Zero Code Execution:** Skill Lens never executes scripts found inside skill folders (`scripts/run.sh`, etc.). It only inspects file metadata and text.
3. **No Network Reliance:** Core scanning and resolving function 100% offline without telemetry or API calls.
