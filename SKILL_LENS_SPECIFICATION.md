# Skill Lens — Definitive Product Specification & Implementation Blueprint

> **"Your AI skills, in one place. And why each one is there."**

**Technical Positioning:** A local diagnostics and resolution engine for AI agent capabilities (`SKILL.md`).  
**Primary Interface:** Line-oriented Python CLI with `Rich` terminal formatting (explicitly NO full-screen TUI).  
**Supported Platforms:** macOS and Linux (Windows is out of scope for v1).  
**Target Audience:** Developers using AI coding agents (OpenAI Codex, Claude Code, Antigravity CLI, OpenCode).  
**Execution Strategy:** 100% Vibe-Coding Ready — Modular, Golden Fixture-Driven, Zero Systems-Language Overhead.

---

## 1. Executive Summary & Core Thesis

As developers adopt multiple AI coding agents, their workstations accumulate capability directories (`SKILL.md` folders) scattered across global user directories, project repositories, monorepo subdirectories, and tool plugins.

Today, developers face three compounding frustrations:
1. **Capability Blindness:** "What skills exist on my machine, and which agents can access them?"
2. **Shadowing & Precedence Drift:** "Why did Claude run an outdated global `browser` prompt instead of the custom skill in my repository?"
3. **Variant Divergence:** "Do these three folders named `deploy` contain the same instructions, or did one branch silently diverge?"

**Skill Lens** is the `which` and `brew doctor` for AI agent skills. It discovers, fingerprints, and explains agent skill resolution on a developer's machine using 100% local, offline, deterministic logic.

---

## 2. Core Mental Model & Resolution States

Skill Lens rejects the assumption that a skill permanently "belongs" to a single agent. Instead, it models capability execution as:

```text
       Skill Name
           ↓
   Physical Installation (folder on disk containing SKILL.md)
           ↓
    Runtime Resolution   (computed for: Agent + Working Directory + Settings)
           ↓
      Target Agent
```

### Resolution Outcomes (`skill-lens why`)
For any query: `skill-lens why <skill_name> --agent <agent> [--cwd <path>]`, the Resolver assigns each discovered installation one of seven mutually exclusive states:

1. **`[ACTIVE]`**: The eligible winning copy for this skill name, for this specific agent and directory. (Does not guarantee execution; indicates this copy wins the name).
2. **`[SHADOWED]`**: A valid copy that this agent searches, but was suppressed because another copy of the same name outranks it under this agent's precedence rules.
3. **`[DISABLED]`**: Exists in an active discovery path, but is explicitly switched off by the agent's configuration or CLI settings.
4. **`[UNSEARCHED]`**: Discovered in another agent's root or a user-added source, but this specific agent's search rules never look in that location.
5. **`[INVALID]`**: Found in a searched path, but rejected by parser/rules (malformed YAML frontmatter, missing required description, or illegal directory/name mismatch).
6. **`[AMBIGUOUS]`**: Two copies tie in precedence rank or the agent's documentation does not specify a deterministic winner.
7. **`[COEXISTS]`**: Same short name, but non-colliding namespace (e.g., Claude plugin skills that load as `/plugin-name:skill-name`).

### Identity, Symlinks, and Fingerprinting Rules
- **Identity:** The skill name is taken from frontmatter `name` if present; otherwise defaults to the parent directory name. Doctor reports any mismatch.
- **Symlinks (Shortcuts):**
  - **Resolution Precedence** evaluates the **entrypoint path** (e.g. a project symlink pointing to a global skill retains project-level precedence).
  - **Fingerprinting & Inventory** evaluates the **canonical target path** (one canonical skill with multiple entrypoints, never counted as duplicate installations).
  - **Cycles & Dangling Links:** Tracked via a visited-inode set. Cycles and broken symlinks are flagged as `[INVALID]` in `doctor`, never causing infinite loops or crashes.
- **Content Fingerprint:**
  - Sorted relative file paths.
  - Text files normalized to `\n` line endings. Binaries hashed raw.
  - Ignored: `.git/`, `.DS_Store`, AppleDouble `._*`, `node_modules/`.
  - File size cap: Files > 1 MiB are hashed up to 1 MiB and marked `truncated`.
- **Variants vs. Versions:** If two installations share the same name but have different hashes, they are labeled `Variant A` and `Variant B` (with diff support). A version number is displayed only if explicitly declared in frontmatter.

---

## 3. Technology Stack & Vibe-Coding Guardrails

- **Language:** **Python 3.11+** (Clean type hints, universal across Unix, zero compiler friction).
- **CLI Framework:** **`Typer`** (Ergonomic command structure, automated `--help`).
- **Terminal Formatting:** **`Rich`** (Line-oriented tables, panels, syntax diffs. Strings escaped with `rich.markup.escape()`).
- **Data & Parsing:** **`tomllib`** (Standard library TOML) + **`PyYAML`** (`yaml.safe_load` on the initial frontmatter block only).
- **Code Quality:** **`ruff`** (Auto-formatting and linting) + **`pytest`** (Golden fixture-based testing).
- **Distribution:** Standard `pyproject.toml` (Executable directly via `pip` or `uvx skill-lens`).

### Strict Non-Goals (Forbidden in v1)
- ❌ **NO Full-Screen TUI / Textual:** Strictly line-oriented CLI.
- ❌ **NO Write Operations:** Zero file installation, deletion, moving, or updating. 100% read-only.
- ❌ **NO Script Execution:** Never executes bash/python scripts found inside skills.
- ❌ **NO Full-Disk Crawling:** Scans are strictly bounded to registry roots and `$HOME/.*/skills/` (depth 1).
- ❌ **NO Windows Support in v1:** macOS and Linux only.
- ❌ **NO Cloud / Telemetry / AI APIs:** 100% offline and private.

---

## 4. Agent Discovery Registry

Discovery rules live in modular TOML files in `skill_lens/registry/agents/*.toml`. Each agent defines its own precedence ordering, upward search behavior, and explicit blind spots.

### Initial Supported Agents (Tier 1)
1. **OpenAI Codex:**
   - Precedence: Project `.agents/skills` (searches upward to git root) > Global `~/.agents/skills` > Admin `/etc/codex/skills`.
   - Environment overrides: `CODEX_HOME`.
2. **Claude Code:**
   - Precedence: Enterprise > Personal `~/.claude/skills` > Project `.claude/skills`.
   - Plugin skills coexist via namespacing.
   - Stop walk: Stops at git worktree boundary.
3. **Antigravity CLI (Modern Gemini CLI replacement):**
   - Precedence: Project `.agents/skills` > User `~/.gemini/antigravity-cli/skills` > Plugin skills.
   - Stop walk: Git repository root.
4. **OpenCode:**
   - Searches `.opencode/skills`, `.claude/skills`, `.agents/skills` upward to git worktree.
   - Duplicate names in same tier produce `[AMBIGUOUS]`.
5. **Legacy Gemini CLI:** Maintained as `experimental`.

### Registry Schema (`skill_lens/registry/agents/codex.toml`)
```toml
id = "codex"
name = "OpenAI Codex"
status = "verified"
evidence_url = "https://platform.openai.com/docs/guides/agent-skills"
verified_at = "2026-09-29"

[detection]
executable = "codex"
config_dir = "~/.codex"
env_override = "CODEX_HOME"

[search_behavior]
walk_rule = "git-root"  # Stop at git root; cwd-only if no git

[[sources]]
path = ".agents/skills"
scope = "project"
agent_rank = 100

[[sources]]
path = "~/.agents/skills"
scope = "global"
agent_rank = 50

[[sources]]
path = "/etc/codex/skills"
scope = "system"
agent_rank = 10

[disable_rules]
mode = "config_entry"
config_path = "~/.codex/config.toml"

[blind_spots]
items = [
  "Built-in system skills compiled into the binary",
  "Session-specific CLI flags (--add-dir)"
]
```

---

## 5. CLI Command Specifications

All commands support both human-friendly `Rich` output and machine-readable `--json` output.

### 1. `skill-lens scan [--sandbox <dir>] [--json]`
Inventories skills across detected agents. Note: Does **not** report "shadowed" counts, because shadowing is relative to a specific agent and working directory.
```text
$ skill-lens scan

╭─────────────────────────── Skill Lens: Discovered Skills ───────────────────────────╮
│ Detected Agents: Codex, Claude Code, Antigravity CLI, OpenCode                      │
│ Unique Skills: 18  •  Total Installations: 24  •  Variants: 3  •  Invalid: 1        │
╰─────────────────────────────────────────────────────────────────────────────────────╯

┌────────────────────┬──────────┬───────────────────────────────┬─────────────────────┐
│ Skill Name         │ Scope    │ Path                          │ Found In Roots      │
├────────────────────┼──────────┼───────────────────────────────┼─────────────────────┤
│ browser            │ Project  │ ./my-app/.agents/skills/bro…  │ Codex, Antigravity  │
│ browser [Var B]    │ Global   │ ~/.agents/skills/browser      │ Codex, Antigravity  │
│ playwright-expert  │ Global   │ ~/.claude/skills/playwright   │ Claude Code         │
│ deploy [INVALID]   │ Global   │ ~/.claude/skills/deploy       │ Missing description │
└────────────────────┴──────────┴───────────────────────────────┴─────────────────────┘
```

### 2. `skill-lens why <skill_name> --agent <agent_id> [--cwd <dir>] [--json]`
The core resolver. Explains which copy wins in a directory and why. Requires `--agent`. Defaults `--cwd` to current working directory.
```text
$ skill-lens why browser --agent codex --cwd ~/Projects/my-app

╭──────────────────────── Resolution: 'browser' for Codex ─────────────────────────╮
│ Agent:        OpenAI Codex                                                        │
│ Working Dir:  /Users/dev/Projects/my-app                                          │
╰───────────────────────────────────────────────────────────────────────────────────╯

● [ACTIVE] (Winning Copy)
  Path:   /Users/dev/Projects/my-app/.agents/skills/browser
  Reason: Project-level skill (.agents/skills) outranks global (Rank 100 > 50).
  Hash:   sha256:7f83b1...

○ [SHADOWED]
  Path:   /Users/dev/.agents/skills/browser
  Reason: Suppressed by project-level copy. Different content (Variant B).
  Hash:   sha256:1a49c2...

○ [UNSEARCHED]
  Path:   /Users/dev/.claude/skills/browser
  Reason: Exists on disk, but Codex search rules never scan ~/.claude/skills.
```

### 3. `skill-lens diff <skill_name> [--json]`
Renders a side-by-side terminal diff between two detected variants of the same skill name.

### 4. `skill-lens doctor [--json]`
Performs hygiene and integrity diagnostics:
- ❌ Broken symlinks (links pointing to missing directories).
- ❌ Malformed frontmatter (invalid YAML or missing required `description`).
- ⚠️ Skill name and directory name mismatches.
- ⚠️ Shadowing warnings where a global skill differs in content from a winning project skill.
- ℹ️ Permission / TCC unreadable directories (reported without crashing).

---

## 6. Implementation Roadmap & Acceptance Gates

Development follows a strict test-first protocol. **Tests never touch the real `$HOME` directory.** All testing uses monkeypatched `tmp_path` fixtures with golden `expected.json` validation.

### Phase 1: Foundation, Dataclasses & Golden Fixtures
- Setup `pyproject.toml` with pinned dependencies (`typer`, `rich`, `pyyaml`, `ruff`, `pytest`).
- Freeze core data structures (`SkillInstallation`, `CandidateResolution`, `ResolutionReport`, `DoctorFinding`).
- Build `tests/fixtures/` with isolated scenarios and golden `expected.json` files:
  1. `codex_project_over_global`: Project copy beats global for Codex.
  2. `claude_personal_over_project`: Personal copy beats project for Claude Code.
  3. `two_project_levels`: Subdirectory skill beats parent monorepo skill.
  4. `symlink_entrypoint_and_canonical`: Project symlink wins precedence; canonical path dedupes hash.
  5. `symlink_cycle_and_dangling`: Cycle detected safely; broken link flagged `[INVALID]`.
  6. `variant_detection`: Same name, differing content hashes labeled Variant A/B.
  7. `opencode_ambiguous`: Two identical rank locations flag `[AMBIGUOUS]`.
  8. `tcc_unreadable_root`: Permission error logs unreadable status without scan crash.
- **Gate:** `pytest` passes validating that test harnesses load fixtures cleanly.

### Phase 2: Metadata Parser & Fingerprint Engine
- Implement `skill_lens/core/parser.py`:
  - `yaml.safe_load` on the first frontmatter block.
  - Identity rules (frontmatter name vs directory name).
  - Normalized SHA-256 fingerprint (newline normalization, binary passthrough, skip `.git`/`.DS_Store`).
  - Symlink canonicalization with visited-inode cycle detection.
- **Gate:** Parser passes 100% of unit tests against all mock `SKILL.md` fixtures.

### Phase 3: Registry Loader & The Resolver (`why` & `scan --sandbox`)
- Implement `skill_lens/registry/` TOML loader.
- Implement `skill_lens/core/resolver.py`:
  - Directory upward walk honoring `walk_rule` (`git-root`, `git-worktree`, `cwd-only`).
  - Precedence evaluation emitting `ACTIVE`, `SHADOWED`, `DISABLED`, `UNSEARCHED`, `INVALID`, `AMBIGUOUS`.
- Build CLI commands:
  - `skill-lens why <skill> --agent <agent> --cwd <dir> --json`
  - `skill-lens scan --sandbox <dir> --json`
  - Add `Rich` formatting over JSON models.
- **Gate:** JSON output from `why` and `scan --sandbox` matches golden `expected.json` files character-for-character.

### Phase 4: Doctor, Diff & Safe Live System Adapter
- Implement `skill_lens/core/doctor.py`:
  - Evaluate resolver results for broken links, malformed metadata, and content divergences.
- Implement `skill_lens/core/differ.py`: Side-by-side terminal diff of variants.
- Implement `skill_lens/core/system.py`:
  - Safe adapter reading real user home paths (`~/.agents/skills`, etc.).
  - Wrapped in `try/except PermissionError` for macOS TCC resilience.
- **Gate:** Live smoke test monkeypatching `HOME` to fixtures succeeds without touching real configurations.

### Phase 5: Packaging & Release
- Verify installation via `pip install .` and `uvx --from . skill-lens --help`.
- Document commands and explicit agent blind spots in `README.md`.
- **Gate:** Clean lint pass with `ruff check .` and 100% green `pytest`.

---

## 7. Safety & Trust Contract

1. **Strictly Read-Only:** Skill Lens never modifies, creates, moves, or deletes user files.
2. **Deterministic & Explainable:** Every resolution reason cites the matching agent rule and rank.
3. **Transparent Blind Spots:** Skill Lens openly reports uninspected vectors (like built-ins) rather than making false claims of completeness.
