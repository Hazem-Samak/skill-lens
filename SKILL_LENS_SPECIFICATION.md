# Skill Lens — Definitive Product Specification & Implementation Blueprint

> **"Your AI skills, in one place. And why each one is there."**

**Technical Positioning:** A local diagnostics and resolution engine for AI agent capabilities (`SKILL.md` and file-based skills).  
**Primary Interface:** Line-oriented Python CLI with `Rich` terminal formatting (explicitly NO full-screen TUI).  
**Supported Platforms:** macOS and Linux (Windows is out of scope for v1).  
**Target Audience:** Multi-agent developers using AI coding assistants (Codex, Claude Code, Antigravity, OpenCode, Pi, Grok, Qoder, Windsurf, OMP, DSH).  
**Execution Strategy:** 100% Vibe-Coding Ready — Modular, Provenance-Tagged, Golden Fixture-Driven, Zero Systems Overhead.

---

## 1. Executive Summary & The Empirical Truth

As developers adopt multiple AI coding agents, their machines accumulate skill capabilities. On modern developer workstations, skills are not isolated silos—they form **symlink farms**.

On the reference machine, live inspection reveals the real topology:
* **1 Canonical Skill Library:** `~/.agents/skills` (83 skills).
* **8 Active Consumer Symlink Roots:** 526 entrypoints mapped into `~/.claude/skills`, `~/.pi/agent/skills`, `~/.grok/skills`, `~/.qoder/skills`, `~/.codeium/windsurf/skills`, `~/.commandcode/skills`, `~/.gemini/config/skills`, and `~/.pi/skills`.
* **Bundled & System Skills:** `~/.codex/skills/.system` (5 system skills), `~/.gemini/antigravity/builtin/skills`, `~/.grok/bundled/skills`.
* **Plugin Skills:** Over 600 dynamically downloaded plugin skills (e.g., in `~/.codex/.tmp/plugins`).

Developers face three core problems:
1. **Capability Blindness:** "What skills exist on my machine, which are user-authored vs bundled vs plugin, and which agents can access them?"
2. **Precedence & Collision Confusion:** "Why is Claude running an outdated global skill, while Codex warns that context is full?"
3. **Symlink Farm & Variant Divergence:** "Is this skill an identical symlink to my shared library, or did someone edit a local copy in this project?"

**Skill Lens** is the `which`, `brew doctor`, and capability inspector for AI agent skills. It discovers, fingerprints, and explains agent skill resolution using 100% local, offline, deterministic logic grounded in empirical agent behavior.

---

## 2. Core Mental Model & The 3-Axis Resolver

Skill Lens models capability execution dynamically:

```text
       Skill Identifier (Directory Name or Frontmatter Name)
                               ↓
   Physical Installation (Folder with SKILL.md or standalone .md file)
                               ↓
    Runtime Resolution   (Computed for: Agent + Working Directory + Settings)
                               ↓
                          Target Agent
```

### The 3-Axis Resolution Model
Underneath the UI, Skill Lens evaluates every discovered skill installation along three independent axes, deriving a deterministic headline state:

```text
Parse Status   (valid | malformed_yaml | missing_description | unreadable)
      ×
Visibility     (active_root | unsearched_root | outside_walk_boundary | disabled)
      ×
Collision      (winning_entry | suppressed_shadow | coexisting_merged | qualified_namespace | ambiguous_tie | unverified_policy)
```

### Derived Headline Output States (`skill-lens why`)
1. **`[ACTIVE]`**: The eligible winning copy for this name under the agent's precedence rules.
2. **`[SHADOWED]`**: Valid copy in a searched path, but suppressed because a higher-priority location outranked it (e.g., Claude personal over project, or Antigravity project over global).
3. **`[COEXISTS]`**: Multiple copies share a name and both are actively available:
   - **Qualified / Namespaced:** The agent distinguishes them by path or plugin prefix (e.g. Claude `apps/web:deploy` or `/plugin:skill`).
   - **Merged:** Discovered across roots with no documented winner; both remain accessible in selectors.
4. **`[DISABLED]`**: Discovered in an active path, but explicitly turned off by agent configuration (e.g. Claude `skillOverrides`, Antigravity `/skills disable`, or Codex `skills.config enabled=false`). If disable state is not persisted in readable config, Skill Lens reports `unknown`.
5. **`[UNSEARCHED]`**: Exists on disk, but this specific agent's search rules never look in that location.
6. **`[INVALID]`**: Discovered in a searched path, but rejected by parser rules (malformed YAML, missing required description, or unknown frontmatter keys where strictly validated).
7. **`[AMBIGUOUS]`**: Two copies tie in rank or the agent's collision policy is undocumented.

---

## 3. Provenance-Tagged Agent Discovery Matrix

*Every root and precedence rule carries an explicit evidence tag (`documented`, `empirical`, or `inferred`) with source URLs and verification dates.*

| Agent | Global Roots | Project Roots | Collision Policy | Identity Source | Walk Boundary | Evidence / Status |
|---|---|---|---|---|---|---|
| **OpenAI Codex** | `~/.codex/skills`, `~/.agents/skills`, `/etc/codex/skills` | `.agents/skills` (ancestor walk) | **Unverified / Merged** (Both listed; 8,000 char budget warning) | Frontmatter `name` | `project_root_markers` (fallback `.git`) | `empirical` + `documented` (`developers.openai.com/codex/skills`) |
| **Claude Code** | `~/.claude/skills` (Personal), Enterprise managed | `.claude/skills` | **Personal > Project** (Personal wins `/cmd`; nested qualify as `dir:cmd`) | **Directory Name** (frontmatter `name` is display label) | Git worktree root | `documented` (`code.claude.com/docs/en/skills.md`) |
| **Antigravity CLI** | `~/.gemini/config/skills/`, `builtin/skills/` | `.agents/skills`, `.agent/skills` (legacy) | **Shadow** (Project > User > Builtin; supports standalone `.md`) | Hybrid | Git repository root | `empirical` (25 live skills) + `documented` |
| **Pi Agent (`pi`)** | `~/.pi/agent/skills` (live 83-link farm), `~/.pi/skills` | `.pi/skills`, `.agents/skills` | **Shadow** (Project `.pi` > Project `.agents` > Global) | Directory Name | Git repository root | `empirical` (83 symlinks verified) |
| **Grok CLI** | `~/.grok/skills` (live 83-link farm), `bundled/skills` | `.agents/skills` | **Shadow** (Project > Global) | Frontmatter `name` | Git repository root | `empirical` (83 symlinks + 28 bundled) |
| **Qoder CLI** | `~/.qoder/skills` (live 83-link farm) | `.qoder/skills`, `.agents/skills` | **Shadow** (Project > Global) | Frontmatter `name` | Git repository root | `empirical` (83 symlinks verified) |
| **Windsurf** | `~/.codeium/windsurf/skills` (live 83-link farm) | `.windsurf/skills`, `.agents/skills` | **Shadow** (Project > Global) | Hybrid | Git repository root | `empirical` (83 symlinks verified) |
| **OpenCode** | `~/.config/opencode/skills/`, `~/.agents/skills` | `.opencode/skills`, `.agents/skills` | **Ambiguous** on duplicate; searches upward | Frontmatter `name` | Git worktree root | `empirical` (1 native skill verified) |
| **Oh My Pi (`omp`)** | `~/.omp/agent/`, `~/.agents/skills` | `.omp/skills`, cross-agent roots | **Inferred** | Frontmatter `name` | Git repository root | `inferred` (Tier 2) |
| **DSH** | `~/.dsh/profiles/node_modules/` | `.dsh/skills`, `.agents/skills` | **Inferred** | Directory Name | Git repository root | `inferred` (Tier 2) |

---

## 4. Filesystem, Symlinks, & Fingerprinting Rules

### Symlinks: Entrypoint vs. Canonical Target
On modern developer setups, agents share a canonical library via symlinks (e.g. `~/.pi/agent/skills/* -> ~/.agents/skills/*`).
* **Precedence & Collision:** Evaluated against the **entrypoint path** (a project symlink `./.agents/skills/deploy` wins project precedence even if pointing to a global file).
* **Inventory & Identity:** Evaluated against the **canonical target path** (an 83-link symlink farm is reported as **1 canonical library with N active agent entrypoints**, never 249 duplicate installations).
* **Cycle & Exhaustion Guard:** Traversal tracks visited `(st_dev, st_ino)` tuples. Cycles and broken symlinks are flagged as `[INVALID]` dangling links without crashing or hanging.

### Streaming Content Fingerprint (SHA-256)
* Sorted relative file paths with forward slashes `/`.
* **Text normalization:** Text files decoded as UTF-8 with `\r\n` normalized to `\n`.
* **Binaries:** Hashed raw without alteration.
* **Streamed full-file hashing:** Hashes the entire file in chunks to eliminate false prefix collisions (no 1 MiB truncation).
* **Exclusions:** Excludes `.git/`, `.DS_Store`, AppleDouble `._*`.

### Scopes: User vs. System vs. Plugin
* **`scope: user`**: Skills authored or symlinked in global agent directories.
* **`scope: project`**: Skills located in workspace repositories.
* **`scope: system`**: Skills bundled into CLI runtimes (e.g. `~/.codex/skills/.system`). Hidden directories (`.system/`) are treated as transparent containers, not skill names.
* **`scope: plugin`**: Skills downloaded by plugins (e.g. `~/.codex/.tmp/plugins`). These are indexed separately and not mixed into the primary user catalog count.

### macOS TCC & Walk Resilience
* All filesystem walks catch `OSError` at the **per-directory iteration layer**.
* If a protected directory (Desktop/Documents) is denied by macOS TCC permissions, Skill Lens records that root as `unreadable` and continues scanning remaining paths.

---

## 5. Technology Stack & Architecture

- **Language:** **Python 3.11+**
- **CLI Framework:** **`Typer`**
- **Terminal UI & Output:** **`Rich`** (line-oriented tables, trees, syntax diffs. Descriptions escaped with `rich.markup.escape()`).
- **Data & Config:** Standard library **`tomllib`** + **`PyYAML`** (`yaml.safe_load`).
- **Path Isolation:** Central `skill_lens/core/paths.py` resolving `os.environ["HOME"]` at call-time (enables 100% leak-proof test monkeypatching).
- **Code Quality:** **`ruff`** + **`pytest`** (placed in `[project.optional-dependencies] dev`).

### Forbidden in v1
- ❌ **NO Full-Screen TUI / Textual:** Strictly line-oriented CLI.
- ❌ **NO Write Operations:** Zero file installations, deletions, or modifications.
- ❌ **NO Script Execution:** Never runs executable scripts inside skill folders.
- ❌ **NO Unbounded Crawling:** Strictly registry roots and `$HOME/.*/skills` up to depth 4.

---

## 6. CLI Command Specifications

Every command supports `--json` returning structured data models.

### 1. `skill-lens scan [--sandbox <dir>] [--json]`
Inventories skills across detected agents, separating canonical user skills from plugins.
```text
$ skill-lens scan

╭─────────────────────────── Skill Lens: Discovered Skills ───────────────────────────╮
│ Detected Agents: Codex, Claude Code, Antigravity, Pi, Grok, Qoder, Windsurf         │
│ Canonical Library: 83 skills (in ~/.agents/skills across 7 symlink farms)            │
│ Local Project Skills: 3  •  System/Bundled: 12  •  Plugin Skills: 600               │
╰─────────────────────────────────────────────────────────────────────────────────────╯

┌────────────────────┬──────────┬───────────────────────────────┬─────────────────────┐
│ Skill Name         │ Scope    │ Canonical Path                │ Active Entrypoints  │
├────────────────────┼──────────┼───────────────────────────────┼─────────────────────┤
│ agent-browser      │ Global   │ ~/.agents/skills/agent-br…    │ Claude, Pi, Grok, … │
│ supabase           │ Project  │ ./my-app/.agents/skills/su…   │ Codex, Antigravity  │
│ imagegen           │ System   │ ~/.codex/skills/.system/im…   │ Codex               │
└────────────────────┴──────────┴───────────────────────────────┴─────────────────────┘
```

### 2. `skill-lens why <skill_name> --agent <agent_id> [--cwd <dir>] [--json]`
Explains runtime resolution for a specific agent and directory.
```text
$ skill-lens why supabase --agent claude --cwd ~/Projects/my-app

╭──────────────────────── Resolution: 'supabase' for Claude ────────────────────────╮
│ Agent:            Claude Code                                                     │
│ Working Dir:      /Users/dev/Projects/my-app                                      │
│ Collision Policy: Personal > Project (Documented)                                 │
╰───────────────────────────────────────────────────────────────────────────────────╯

● [ACTIVE] (Winning Copy)
  Path:   /Users/dev/.claude/skills/supabase
  Reason: Personal user skill takes precedence over project repository skill.
  Rule:   claude_personal_beats_project (Evidence: documented)
  Hash:   sha256:7f83b1...

○ [SHADOWED]
  Path:   /Users/dev/Projects/my-app/.claude/skills/supabase
  Reason: Suppressed by personal copy above. Different content (Variant B).
  Rule:   claude_project_skills
  Hash:   sha256:1a49c2...
```

### 3. `skill-lens compare --agent <agent_a> --agent <agent_b> [--cwd <dir>] [--json]`
Compares capability surfaces between two agents. Pinpoints which skills are shared via symlink farms vs where their capabilities diverge.

### 4. `skill-lens diff <skill_name> [--json]`
Side-by-side terminal syntax diff between differing variants sharing the same name.

### 5. `skill-lens doctor [--json]`
Performs hygiene and ecosystem health diagnostics:
- ❌ Dangling symlinks and symlink cycles.
- ❌ Malformed frontmatter (invalid YAML or missing required `description`).
- ⚠️ Codex Context Budget: Warns if total skill descriptions exceed ~8,000 characters, causing Codex to silently omit skills.
- ⚠️ TCC permission-blocked search roots.
- ⚠️ Traversal hazards (e.g. `node_modules/**/SKILL.md`).
- ℹ️ Symlink farm health and installer lockfile (`~/.agents/.skill-lock.json`) status.

---

## 7. Implementation Roadmap & Acceptance Gates

Development follows a strict test-first protocol. Tests run against mock fixtures inside `tmp_path`.

### Phase 0: Contracts, Frozen Models & Fixtures
- Setup `pyproject.toml` with `typer`, `rich`, `pyyaml`, and dev dependencies (`ruff`, `pytest`).
- Create `skill_lens/core/paths.py` with lazy, call-time resolution of `os.environ["HOME"]` and `os.environ["XDG_CONFIG_HOME"]` (for OpenCode `~/.config/opencode`).
- Define `--sandbox <dir>` explicitly as a mock `$HOME` directory root for tests and safe demos.
- Define frozen dataclasses in `skill_lens/models/`:
  - `SkillInstallation`, `CandidateResolution`, `ResolutionReport`, `DoctorFinding`.
- Build `tests/fixtures/` with hand-written golden `expected.json` files for 12 core scenarios:
  1. `claude_personal_beats_project`: Personal directory copy overrides project copy (empirically grounded).
  2. `claude_nested_qualification`: Monorepo subdirectory skill loads as `dir:skill`.
  3. `symlink_farm_multi_agent`: 1 canonical target with 3 entrypoints.
  4. `symlink_cycle_guard`: Circular link flagged `[INVALID]` without infinite loop.
  5. `antigravity_file_based`: Standalone `.md` skill loaded alongside directory skills.
  6. `tcc_permission_error`: Blocked directory logged as `unreadable` without scan failure.
  7. `opencode_ambiguous`: Two identical rank locations flag `[AMBIGUOUS]`.
  8. `variant_hash_detection`: Differing bytes produce Variant A/B labels.
  9. `worktree_dotgit_file`: Walk stops correctly when `.git` is a worktree file.
  10. `system_container_traversal`: Hidden container `.system/` parsed transparently.
  11. `disabled_override`: Agent settings file turns off a skill, resulting in `[DISABLED]`.
  12. `malformed_frontmatter`: Invalid YAML syntax or missing required `description`, resulting in `[INVALID]`.
- **Phase 0.5 Acceptance Gate (Fixture Inventory Reconciliation):**
  - Run `scan --sandbox <fixture-farm> --json` proving the tool accurately groups canonical libraries vs entrypoints.

### Phase 1: Metadata Parser & Streaming Hasher
- Implement `skill_lens/core/parser.py`:
  - Frontmatter extraction via `yaml.safe_load`.
  - Directory-based and frontmatter-based identity extraction.
  - Streaming SHA-256 hasher with newline normalization.
  - Symlink canonicalization with visited-inode tracking.
- **Gate:** Parser passes 100% of unit tests against all mock fixtures.

### Phase 2: Registry Loader & 3-Axis Resolver
- Implement TOML loader reading `skill_lens/registry/agents/*.toml` with provenance fields.
- Implement `skill_lens/core/resolver.py`:
  - Upward directory walk stopping at git root / worktree.
  - 3-axis resolution engine emitting `ACTIVE`, `COEXISTS`, `SHADOWED`, `DISABLED`, `UNSEARCHED`, `INVALID`, `AMBIGUOUS`.
  - Machine-checkable `rule_id` and `evidence` attached to every candidate resolution reason.
- Build CLI commands:
  - `skill-lens why <skill> --agent <agent> [--cwd <dir>] --json`
  - `skill-lens scan --sandbox <dir> --json`
- **Gate:** Semantic JSON output (`json.dumps(sort_keys=True)`) matches golden `expected.json` across all fixtures.

### Phase 3: Rich Terminal Presentation Layer
- Build Rich output formatters for `scan` and `why`.
- Implement safe markup escaping (`rich.markup.escape()`) for descriptions.
- Add Rich diff renderer for `skill-lens diff`.
- **Gate:** Rich snapshot tests pass with clean formatting.

### Phase 4: Doctor, Multi-Agent Compare & Safe Live Adapter
- Implement `skill_lens/core/doctor.py`:
  - Broken symlink detection, TCC unreadable reporting, Codex context budget check.
- Implement `skill-lens compare --agent A --agent B`.
- Implement `skill_lens/core/system.py`:
  - Live discovery adapter querying actual user directories with per-directory `OSError` guards.
- **Gate:** Live smoke test monkeypatching `HOME` to fixtures runs with zero regressions.

### Phase 5: Packaging & Release
- Setup console script entrypoint `skill-lens`.
- Verify execution via `pip install .` and `uvx --from . skill-lens --help`.
- Create repository `AGENTS.md` documenting architecture rules.
- **Gate:** `ruff check .` passes with zero warnings, 100% green `pytest`.

---

## 8. Safety & Explainability Contract

1. **Strictly Read-Only:** Skill Lens never modifies, creates, moves, or deletes user files.
2. **Deterministic & Machine-Checkable:** Every resolution reason cites a specific `rule_id` and provenance level (`documented`, `empirical`, `inferred`).
3. **Transparent Divergence:** Skill Lens clearly flags documented vs observed agent quirks rather than making false claims of perfection.
