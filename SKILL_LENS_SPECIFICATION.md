# Skill Lens — Definitive Product Specification & Implementation Blueprint

> **"Your AI skills, in one place. And why each one is there."**

**Technical Positioning:** A local diagnostics and resolution engine for AI agent capabilities (`SKILL.md` and file-based skills).  
**Primary Interface:** Line-oriented Python CLI with `Rich` terminal formatting (explicitly NO full-screen TUI).  
**Supported Platforms:** macOS and Linux (Windows is out of scope for v1).  
**Target Audience:** Multi-agent developers using AI coding assistants (Codex, Claude Code, Antigravity, OpenCode, Pi, OMP, DSH, Cursor).  
**Execution Strategy:** 100% Vibe-Coding Ready — Modular, Golden Fixture-Driven, Zero Systems-Language Overhead.

---

## 1. Executive Summary & Core Thesis

As developers adopt multiple AI coding agents, their machines accumulate skill capabilities scattered across global directories, project roots, monorepo subdirectories, and tool plugins.

Developers face three critical problems:
1. **Capability Blindness:** "What skills exist on my machine, and which agents can actually access them?"
2. **Precedence & Collision Confusion:** "Why is Claude running an outdated global skill, while Codex is listing two copies of the same prompt?"
3. **Symlink Farm & Variant Divergence:** "Is this skill an identical symlink to my shared library, or did someone edit a local copy?"

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
Collision      (winning_entry | suppressed_shadow | coexisting_merged | qualified_namespace | ambiguous_tie)
```

### Derived Headline Output States (`skill-lens why`)
1. **`[ACTIVE]`**: The eligible winning copy for this name under the agent's precedence rules.
2. **`[SHADOWED]`**: Valid copy in a searched path, but suppressed because a higher-priority location outranked it (e.g. Antigravity project over global).
3. **`[COEXISTS]`**: Multiple copies share a name and both are actively available:
   - **Merged:** The agent displays both in its picker (e.g. OpenAI Codex).
   - **Qualified / Namespaced:** The agent distinguishes them by path or plugin prefix (e.g. Claude `apps/web:deploy` or `/plugin:skill`).
4. **`[DISABLED]`**: Discovered in an active path, but explicitly turned off by agent configuration (e.g. Claude `skillOverrides`, Antigravity `/skills disable`, or Codex `skills.config enabled=false`).
5. **`[UNSEARCHED]`**: Exists on disk, but this specific agent's search rules never look in that location.
6. **`[INVALID]`**: Discovered in a searched path, but rejected by parser rules (malformed YAML, missing required description, or unknown frontmatter keys where strictly validated).
7. **`[AMBIGUOUS]`**: Two copies tie in rank and the agent's published documentation does not specify a winner (e.g. OpenCode duplicate names in same tier).

---

## 3. Ground-Truth Agent Discovery Matrix

*Verified empirically against live CLI binaries and agent configurations on macOS.*

| Agent | Global Search Roots | Project Search Roots | Collision Policy | Identity Source | Walk Boundary |
|---|---|---|---|---|---|
| **OpenAI Codex** | `~/.codex/skills`, `~/.agents/skills`, `/etc/codex/skills` | `.agents/skills` (upward traversal) | **Merge** (both appear in picker; rank sets display order) | Frontmatter `name` | Git root (`.git` dir or file) |
| **Claude Code** | `~/.claude/skills` (Personal), Enterprise managed | `.claude/skills` | **Personal > Project** (Personal wins `/command`; nested qualify as `dir:cmd`) | **Directory Name** (frontmatter `name` is display label) | Git worktree root |
| **Antigravity CLI** | `~/.gemini/config/skills/`, `~/.gemini/antigravity-cli/skills/` | `.agents/skills`, `.agent/skills` (legacy) | **Shadow** (Project > User > Plugins; supports standalone `.md`) | Hybrid | Git repository root |
| **OpenCode** | `~/.config/opencode/skills/`, `~/.claude/skills`, `~/.agents/skills` | `.opencode/skills`, `.claude/skills`, `.agents/skills` | **Ambiguous** on duplicate; searches upward | Frontmatter `name` | Git worktree root |
| **Pi Agent (`pi`)** | `~/.pi/agent/skills` (live 83-link farm), `~/.pi/skills` | `.pi/skills`, `.agents/skills` | **Shadow** (Project `.pi` > Project `.agents` > Global) | Directory Name | Git repository root |
| **Oh My Pi (`omp`)** | `~/.omp/agent/managed-skills`, `~/.agents/skills` | `.omp/skills`, `.agents/skills`, `.claude/skills`, `.codex/skills` | **Shadow** (Project `.omp` > Cross-agent project > Global) | Frontmatter `name` | Git repository root |
| **DeepSeek Harness (`dsh`)** | `~/.dsh/skills`, profile plugin modules | `.dsh/skills`, `.agents/skills` | **Shadow** (Project > Global) | Directory Name | Git repository root |
| **Cursor (Tier 2)** | `~/.cursor/skills`, `~/.agents/skills` | `.cursor/skills`, `.agents/skills` | Shadow | Hybrid | Git repository root |

---

## 4. Filesystem, Symlinks, & Fingerprinting Rules

### Symlinks: Entrypoint vs. Canonical Target
On modern developer setups, agents frequently share a canonical library via symlinks (e.g. `~/.pi/agent/skills/* -> ~/.agents/skills/*`).
* **Precedence & Collision:** Evaluated against the **entrypoint path** (a project symlink `./.agents/skills/deploy` wins project precedence even if pointing to a global file).
* **Inventory & Identity:** Evaluated against the **canonical target path** (an 83-link symlink farm is reported as **1 canonical library with 3 agent entrypoints**, never 249 duplicate installations).
* **Cycle & Exhaustion Guard:** Traversal tracks visited `(st_dev, st_ino)` tuples. Cycles and broken symlinks are flagged as `[INVALID]` dangling links without crashing or hanging.

### Streaming Content Fingerprint (SHA-256)
* Sorted relative file paths with forward slashes `/`.
* **Text normalization:** Text files decoded as UTF-8 with `\r\n` normalized to `\n`.
* **Binaries:** Hashed raw without alteration.
* **Streamed full-file hashing:** Hashes the entire file in chunks to eliminate false prefix collisions (no 1 MiB truncation).
* **Exclusions:** Excludes `.git/`, `.DS_Store`, AppleDouble `._*`.

### Discovery vs. Hashing Rule for `node_modules/`
* **During Fingerprinting:** `node_modules/` is strictly ignored so dependency churn does not alter skill identity.
* **During Discovery (`doctor`):** The scanner inspects project directories to flag recursive nested `SKILL.md` files (the known Codex traversal limit bug) and reports them in `skill-lens doctor`.

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
- ❌ **NO Unbounded Crawling:** Strictly registry roots and `$HOME/.*/skills` / `$HOME/.*/config/skills`.

---

## 6. CLI Command Specifications

Every command supports `--json` returning structured data models.

### 1. `skill-lens scan [--sandbox <dir>] [--json]`
Inventories skills across detected agents and reports canonical counts.
```text
$ skill-lens scan

╭─────────────────────────── Skill Lens: Discovered Skills ───────────────────────────╮
│ Detected Agents: Codex, Claude Code, Antigravity, OpenCode, Pi, OMP, DSH            │
│ Unique Skills: 28  •  Canonical Installations: 31  •  Variants: 2  •  Invalid: 1    │
│ Symlink Farms: 1 detected (~/.agents/skills shared across Claude, Pi, Antigravity)  │
╰─────────────────────────────────────────────────────────────────────────────────────╯

┌────────────────────┬──────────┬───────────────────────────────┬─────────────────────┐
│ Skill Name         │ Scope    │ Canonical Path                │ Active Entrypoints  │
├────────────────────┼──────────┼───────────────────────────────┼─────────────────────┤
│ browser            │ Project  │ ./my-app/.agents/skills/bro…  │ Codex, Antigravity  │
│ browser [Var B]    │ Global   │ ~/.agents/skills/browser      │ Codex, Pi, Claude   │
│ playwright-expert  │ Global   │ ~/.claude/skills/playwright   │ Claude Code         │
│ deploy [INVALID]   │ Global   │ ~/.claude/skills/deploy       │ Missing description │
└────────────────────┴──────────┴───────────────────────────────┴─────────────────────┘
```

### 2. `skill-lens why <skill_name> --agent <agent_id> [--cwd <dir>] [--json]`
Explains runtime resolution for a specific agent and directory.
```text
$ skill-lens why browser --agent codex --cwd ~/Projects/my-app

╭──────────────────────── Resolution: 'browser' for Codex ─────────────────────────╮
│ Agent:            OpenAI Codex                                                    │
│ Working Dir:      /Users/dev/Projects/my-app                                      │
│ Collision Policy: Merge (both entries remain accessible in picker)               │
╰───────────────────────────────────────────────────────────────────────────────────╯

● [ACTIVE] (Primary Display Copy)
  Path:   /Users/dev/Projects/my-app/.agents/skills/browser
  Reason: Project-level skill (.agents/skills) has higher display priority.
  Rule:   codex_project_agents_skills (Rank 100)
  Hash:   sha256:7f83b1...

● [COEXISTS] (Merged Secondary Copy)
  Path:   /Users/dev/.agents/skills/browser
  Reason: Codex collision policy is 'merge'; global copy remains available.
  Rule:   codex_global_agents_skills (Rank 50)
  Hash:   sha256:1a49c2... (Variant B)
```

### 3. `skill-lens compare --agent <agent_a> --agent <agent_b> [--cwd <dir>] [--json]`
Compares capability surfaces between two agents. Pinpoints which skills are shared via symlink farms vs where their capabilities diverge.

### 4. `skill-lens diff <skill_name> [--json]`
Side-by-side terminal syntax diff between differing variants sharing the same name.

### 5. `skill-lens doctor [--json]`
Performs hygiene and ecosystem health diagnostics:
- ❌ Dangling symlinks and symlink cycles.
- ❌ Malformed frontmatter (invalid YAML or missing required `description`).
- ⚠️ TCC permission-blocked search roots.
- ⚠️ Nested traversal hazards (e.g. `node_modules/**/SKILL.md` poisoning Codex).
- ℹ️ Multi-agent symlink farm health and installer lockfile (`.skill-lock.json`) status.

---

## 7. Implementation Roadmap & Acceptance Gates

Development follows a strict test-first protocol. Tests run against mock fixtures inside `tmp_path`.

### Phase 0: Contracts, Frozen Models & Fixtures
- Setup `pyproject.toml` with `typer`, `rich`, `pyyaml`, and dev dependencies (`ruff`, `pytest`).
- Create `skill_lens/core/paths.py` with lazy, monkeypatch-safe path resolution.
- Define frozen dataclasses in `skill_lens/models/`:
  - `SkillInstallation`, `CandidateResolution`, `ResolutionReport`, `DoctorFinding`.
- Build `tests/fixtures/` with hand-written golden `expected.json` files for 10 core scenarios:
  1. `codex_merge_policy`: Project and global both co-exist with rank-ordered display.
  2. `claude_personal_beats_project`: Personal directory copy overrides project copy.
  3. `claude_nested_qualification`: Monorepo subdirectory skill loads as `dir:skill`.
  4. `symlink_farm_multi_agent`: 1 canonical target with 3 entrypoints.
  5. `symlink_cycle_guard`: Circular link flagged `[INVALID]` without infinite loop.
  6. `antigravity_file_based`: Standalone `.md` skill loaded alongside directory skills.
  7. `tcc_permission_error`: Blocked directory logged as `unreadable` without scan failure.
  8. `opencode_ambiguous`: Two identical rank locations flag `[AMBIGUOUS]`.
  9. `variant_hash_detection`: Differing bytes produce Variant A/B labels.
  10. `worktree_dotgit_file`: Walk stops correctly when `.git` is a worktree file.
- **Gate:** Tests verify all 10 fixture environments exist and load expected JSON contracts.

### Phase 1: Metadata Parser & Streaming Hasher
- Implement `skill_lens/core/parser.py`:
  - Frontmatter extraction via `yaml.safe_load`.
  - Directory-based and frontmatter-based identity extraction.
  - Streaming SHA-256 hasher with newline normalization.
  - Symlink canonicalization with visited-inode tracking.
- **Gate:** Parser passes 100% of unit tests against all mock fixtures.

### Phase 2: Registry Loader & 3-Axis Resolver
- Implement TOML loader reading `skill_lens/registry/agents/*.toml`.
- Implement `skill_lens/core/resolver.py`:
  - Upward directory walk stopping at git root / worktree.
  - 3-axis resolution engine emitting `ACTIVE`, `COEXISTS`, `SHADOWED`, `DISABLED`, `UNSEARCHED`, `INVALID`, `AMBIGUOUS`.
  - Machine-checkable `rule_id` attached to every candidate resolution reason.
- Build CLI commands:
  - `skill-lens why <skill> --agent <agent> [--cwd <dir>] --json`
  - `skill-lens scan --sandbox <dir> --json`
- **Gate:** Semantic JSON output (`json.dumps(sort_keys=True)`) matches golden `expected.json` across all 10 fixtures.

### Phase 3: Rich Terminal Presentation Layer
- Build Rich output formatters for `scan` and `why`.
- Implement safe markup escaping (`rich.markup.escape()`) for descriptions.
- Add Rich diff renderer for `skill-lens diff`.
- **Gate:** Rich snapshot tests pass with clean formatting.

### Phase 4: Doctor, Multi-Agent Compare & Safe Live Adapter
- Implement `skill_lens/core/doctor.py`:
  - Broken symlink detection, TCC unreadable reporting, nested `node_modules` warnings.
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
2. **Deterministic & Machine-Checkable:** Every resolution reason cites a specific `rule_id` from the verified registry.
3. **Transparent Divergence:** Skill Lens clearly flags documented vs observed agent quirks rather than making false claims of perfection.
