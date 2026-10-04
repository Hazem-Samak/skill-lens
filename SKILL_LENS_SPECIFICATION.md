# Skill Lens — Definitive Product Specification & Implementation Blueprint

> **"Your AI skills, in one place. And why each one is there."**

**Technical Positioning:** A local diagnostics and resolution engine for AI agent capabilities (`SKILL.md` and file-based skills).  
**Primary Interface:** Line-oriented Python CLI with `Rich` terminal formatting. From **0.2**, an additive, optional full-screen TUI (Textual) may be layered on top as a browsing surface; the line-oriented CLI remains the primary interface. Bare `skill-lens` opens the TUI when Textual is installed and both stdin and stdout (terminal input and output) are interactive; `--plain`, either stream being non-interactive, or missing Textual prints help instead.<br>
**Supported Platforms:** macOS and Linux (Windows is out of scope for v1).  
**Target Audience:** Multi-agent developers using AI coding assistants (Codex, Claude Code, Antigravity, OpenCode, Pi, Grok, Qoder, Windsurf, OMP, DSH).  
**Execution Strategy:** Built for AI-assisted development — Modular, Provenance-Tagged, Golden Fixture-Driven, Zero Systems Overhead.

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
| **Oh My Pi (`omp`)** | `~/.agents/skills`, `~/.omp/agent/` (managed, lowest priority) | `.omp/skills`, `.agents/skills` | Upstream keeps other copies reachable under prefixed names; Skill Lens reports `ambiguous` until that behaviour is modelled | Frontmatter `name` | Git repository root | `documented` ([vendor skills guide](https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md)); Phase 6 correction |
| **DSH** | `~/.dsh/skills`, `~/.agents/skills`, `~/.dsh/profiles` (plugin traversal) | `.dsh/skills`, `.agents/skills` | **Shadow** (Project `.dsh` > Project `.agents` > User `.dsh` > User `.agents`) | Directory Name | Git repository root | Native roots/policy `documented` ([vendor skills guide](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md)); plugin traversal remains `inferred` |

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
- ❌ **NO Full-Screen TUI / Textual:** v1 is strictly line-oriented CLI. **Amended for 0.2:** an optional, additive, read-only full-screen TUI is permitted from 0.2 as the `[tui]` extra; the line-oriented CLI stays primary. See [`FULL_SCREEN_TUI.md`](./FULL_SCREEN_TUI.md).
- ❌ **NO Write Operations:** Zero file installations, deletions, or modifications.
- ❌ **NO Script Execution:** Never runs executable scripts inside skill folders.
- ❌ **NO Unbounded Crawling:** Strictly registry roots and `$HOME/.*/skills` up to depth 4.

---

## 6. CLI Command Specifications

Every existing report command supports `--json` returning structured data models.
Exit codes follow the Phase 6 contract: `0` means the command ran and no findings
reached the chosen threshold (including "nothing found" and "no differences");
`1` means findings reached the `--fail-on` threshold on `scan` or `doctor`;
`2` means a usage error or an unknown agent. `--fail-on` defaults to `never`, so
findings alone do not change the exit status. Code `3` is reserved for an
unexpected internal fault; the planned TUI uses it as specified in its plan.

### 1. `skill-lens scan [--sandbox <dir>] [--cwd <dir>] [--json]`
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

### 3. `skill-lens agents [--json]`
Lists the known agent definitions with their collision policy, provenance evidence and
root count. Shipped in Phase 2.

### 4. `skill-lens compare --agent <agent_a> --agent <agent_b> [--cwd <dir>] [--json]`
Compares capability surfaces between two agents. Pinpoints which skills are shared via symlink farms vs where their capabilities diverge.

### 5. `skill-lens diff <skill_name> [--sandbox <dir>] [--cwd <dir>] [--json]`
Unified syntax diff between the differing variants that share one name.

- **Inputs.** Built from `DiscoveryIndex` entries, which are already deduplicated by
  canonical target: one library reached through N symlink entrypoints is one copy, so
  symlinked copies of a target can never produce a diff. `diff` must not re-implement
  that grouping.
- **Comparability.** Every *readable* copy is a diff participant — including copies that
  fail frontmatter validation (malformed YAML, missing `description`), because a broken
  copy is usually the one worth inspecting. The content hash is computed as soon as the
  symlink resolves, so such a copy is still hashable and diffable. Two rules keep this
  consistent with `scan` and `why`: a copy that failed validation is **flagged as invalid
  and given no Variant letter** (only `discovery.variant_labels`'s valid set is labelled),
  and it is **never the baseline**. Copies that cannot be read at all — dangling symlinks,
  cycles, permission-denied roots — have no content and are listed with no diff.
- **Baseline.** The copy `discovery.variant_labels` labels **Variant A** (scope
  specificity via `discovery.entry_scope`, then discovery order). Every other distinct
  copy — valid or invalid — is diffed against it; an invalid copy is never itself the
  baseline. Copies past A–F are reported unlabelled, never with an invented letter.
- **File comparison.** Directory skills are compared over exactly `hasher.iter_files()`
  (the same sorted, forward-slash relative set, with `.git/`, `.DS_Store` and AppleDouble
  `._*` excluded) **and with the same normalization** as `hash_file` (UTF-8 decode,
  `\r\n` → `\n`). Two copies that differ only by line endings therefore share a content
  hash and must produce no diff — a raw byte comparison here would contradict the hash
  and repeat finding F-16. Files match by relative path, so added, removed and renamed
  files appear as such. Standalone `.md` (file) skills are compared as a single file.
- **Binary files** are reported as differing; their contents are never printed.
- **Outcomes.** Zero copies → clear message, `found: false`, exit code `0` (matching
  `why`, finding F-10). Exactly one distinct copy, or all copies identical → "no
  differences", exit code `0`. Neither is an error.
- **Truncation.** 400 changed lines per copy and 20,000 characters per report; the JSON
  carries `truncated: true` and the terminal states how much was omitted.
- **Escaping.** All file content and paths pass through `rich.markup.escape()` before
  display.

> **v1 is a unified diff, not side-by-side.** Rich has no native side-by-side diff, and a
> hand-built two-column layout is width-sensitive and brittle to snapshot. v1 renders a
> unified diff (standard-library `difflib` plus Rich `Syntax` with the `"diff"` lexer);
> side-by-side is a deferred enhancement. `Pygments` arrives transitively via Rich and is
> **not** added to `pyproject.toml`.

### 6. `skill-lens doctor [--json]`
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

### Phase 3: Rich Terminal Presentation Layer & `diff`

**Already shipped in Phase 2 — do not rebuild:** the Rich formatters for `scan` and `why`
(`render_scan`, `render_why` in `skill_lens/render.py`) and safe markup escaping
(`rich.markup.escape`) for every description, path and diff body, covered by
`test_markup_is_escaped_in_output`. Phase 3 therefore covers the work below.

- **Step 1 — models first.** Add frozen dataclasses in `skill_lens/models/diff.py`
  (`DiffReport`, `DiffCopy`, `DiffFile`, `DiffHunk`), each with `to_dict()`, and export
  them from `skill_lens/models/__init__.py`. `skill-lens diff --json` emits
  `dumps(DiffReport)` (sorted keys) and is pinned by a golden
  `tests/fixtures/golden/diff_*.json` **before** any Rich renderer exists (AGENTS.md
  rule 4).
- **Step 2 — pure computation.** `skill_lens/core/diff.py` builds the `DiffReport` from
  `DiscoveryIndex` entries and imports **no `rich`**.
- **Step 3 — presentation.** `render_diff(report, console)` in `skill_lens/render.py`
  formats an already-complete model and prints nothing else. Move the `agents` table out
  of `cli.py` into `render.py` as `render_agents(...)`, so `cli.py` holds no Rich layout
  code.
- **Step 4 — snapshot harness.** Plain-text goldens under `tests/fixtures/snapshots/`
  (no new dev dependency). Every snapshot renders into
  `Console(record=True, width=<fixed>, no_color=True, force_terminal=False,
  highlight=False)` and is compared via `export_text()`; the fixed width is asserted,
  not assumed. Regeneration is a documented in-repo switch (e.g.
  `pytest tests/test_render_snapshots.py --update-snapshots`). Cover `scan`, `why` and
  `diff`.
- **Boundaries.** `doctor`, multi-agent `compare` and the live scanner
  (`skill_lens/core/system.py`) stay in Phase 4. No new *declared* dependencies: the
  unified diff uses the standard-library `difflib` plus Rich's existing `Syntax`
  (`Pygments` arrives transitively via Rich and is not added to `pyproject.toml`). No
  full-screen TUI in Phase 3 (AGENTS.md rule 5 as it stood then). The optional TUI is
  new scope for 0.2 — see [`FULL_SCREEN_TUI.md`](./FULL_SCREEN_TUI.md).
- **Gate:** `pytest` green — including the new snapshot tests and a `diff` golden
  scenario built on the existing `variant_hash_detection` fixture — `ruff check .` clean
  and `ruff format .` clean.

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

### Phase 6: Enforceable Findings & Evidence Integrity

> **Added after 0.1.0, by owner decision.** Phases 0–5 above are the original
> roadmap and are all complete. This phase is new scope chosen after the Phase 5
> review, which found that a live run of the tool exposed two gaps: its findings
> could not change an exit status, and two registry entries had no citation.
> See `docs/archive/PHASE6_PLAN.md` for the plan and
> `docs/archive/PHASE6_WALKTHROUGH.md` for what shipped.

- Implement an explicit **exit-code contract** in a pure core module
  (`skill_lens/core/exitcodes.py`), which imports no Typer and no Rich:
  | Code | Meaning |
  | --- | --- |
  | `0` | The command ran; nothing reached the threshold. |
  | `1` | The command ran; findings reached the threshold. |
  | `2` | The command could not run: bad usage or unknown agent. |
  | `3` | Reserved for an unexpected internal fault. |
- Add `--fail-on {never,error,warning,info}` to `doctor` and `scan`.
  - **Default `never`**, which preserves every pre-Phase-6 exit status exactly.
  - A threshold is a comparison, never a count.
  - The report is always printed *before* the non-zero exit, so a gate can never
    hide the evidence that tripped it.
  - `--fail-on` is deliberately absent from `why`, `diff`, `compare` and
    `agents`: a missing skill is an answer, not a fault.
- **Evidence integrity.** Every agent definition claiming `documented` or
  `empirical` evidence must carry a citable `source`. This becomes an enforced
  invariant rather than a convention (AGENTS.md rule 6).
- **Correct any registry entry contradicted by primary vendor documentation**,
  and record what remains genuinely unknown rather than guessing it.
- **Gate:** `pytest`, `ruff check .` and `ruff format --check .` clean; every new
  guard mutation-tested; every changed golden or snapshot reviewed and explained.

### Phase 7 (0.2): Interactive Full-Screen TUI — planned, not built

> **New scope after 0.1.x, owner decision.** Overturns the v1 "no full-screen
> TUI" rule for 0.2. The full design — purpose, vision, screens, phasing and
> gates — lives in [`FULL_SCREEN_TUI.md`](./FULL_SCREEN_TUI.md). This section is
> only the pointer; the plan is authoritative.

- Add an **optional** `textual` dependency as the `[tui]` extra; the base install
  gains no new runtime dependency.
- Ship `skill-lens tui` as a strictly **read-only, presentation-only** browsing
  layer over the existing frozen models. No new engine, no new data fields.
- Keep every existing command, flag, JSON shape and exit code unchanged.
- **Gate:** see the plan's success criteria — read-only guard test, no new base
  dependency, full repository gate green, snapshots reviewed.

---

## 8. Safety & Explainability Contract

1. **Strictly Read-Only:** Skill Lens never modifies, creates, moves, or deletes user files.
2. **Deterministic & Machine-Checkable:** Every resolution reason cites a specific `rule_id` and provenance level (`documented`, `empirical`, `inferred`).
3. **Transparent Divergence:** Skill Lens clearly flags documented vs observed agent quirks rather than making false claims of perfection.
