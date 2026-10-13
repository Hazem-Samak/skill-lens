# Stage C Evidence Record: Parser, Discovery, and Registry Repairs

**Date:** 2026-10-13  
**Status:** Approved Compatibility Consistency Completed (Source Provenance & Baseline Compatibility Preserved)  
**Scope:** Stage C Focused Corrections (F05, F06, F07)  
**Implementer:** Antigravity (gemini-3.8-flash-high, full-access, default interaction mode)

---

## 1. OpenCode Multi-Source Contract Clarification

- **Vendor Model Contract:** OpenCode V2 specifies discovery across native `.opencode/skills`, shared `.agents/skills`, and Claude-compatible `.claude/skills` repositories.
- **Stage C Registry Boundary:** In the current Stage C registry (`skill_lens/registry/agents/opencode.toml`), only native (`.opencode/skills`) and shared (`.agents/skills`) project/global roots are configured.
- **Stage D Demarcation:** The addition of `.claude` roots to OpenCode's registry configuration represents new root surface introduction and is formally demarked as **Stage D work**, adhering to strict stage boundary isolation.
- **Format Support in C:** OpenCode V2 roots support root-level `*.md` files (with frontmatter name) and exact recursive `SKILL.md` directories up to `MAX_WALK_DEPTH = 4`.

---

## 2. Same-Path Same-Agent Precedence (Rank-Max Integrity)

- **Problem:** When an agent defines multiple roots that resolve to the exact same physical directory (e.g. DSH project root rank 95 and user root rank 70 both resolving to `<home>/.dsh/skills` when `<home>` is a `.git` boundary), root iteration order must not determine the winning candidate.
- **Resolution:** The resolver groups candidates by resolved entrypoint path per agent and retains the candidate with the highest rank (`max(candidates, key=rank)`).
- **Regression Guard:** `test_same_path_same_agent_precedence_rankmax` verifies that reversing root iteration order in the agent definition preserves rank 95 (`dsh_documented_project`) over rank 70 (`dsh_documented_user`).

---

## 3. Entrypoint Alias & Discovery Decoupling from File Suffix

- **Problem:** In pre-correction logic, an entrypoint directory whose name happened to end in `.md` (such as `.pi/agent/skills/shortcut.md/`) had its alias erroneously stem-truncated to `shortcut` instead of retaining the full directory name `shortcut.md`.
- **Resolution:** `entrypoint_alias` and discovery name assignment are strictly conditioned on `is_file`:
  - Files (`is_file=True`) take `entrypoint.stem` as their alias/name.
  - Directories (`is_file=False`) retain `entrypoint.name` (or `parse.directory_name`), preserving `.md` endings intact.
- **Regression Guard:** `test_entrypoint_alias_and_discovery_for_dot_md_named_directory` verifies cross-consumer consistency across `resolve_skill`, `why`, `diff`, `compare`, `scan`, and session snapshots.

---

## 4. OpenAI Codex (learn.chatgpt.com/docs/build-skills)

- **Source Reference:** `learn.chatgpt.com/docs/build-skills`
- **Evidence Date:** 2026-10-12
- **Surface & Semantics:**
  - Skill directory requires `SKILL.md` file.
  - Conventional global (`~/.codex/skills`) and project (`.codex/skills`) roots are directory-only, matching plugin roots.
  - Directory-only roots ignore file targets, regardless of metadata or name.
  - Incidental markdown files like `README.md` within plugin/skills directories are ignored rather than failing parsing or causing doctor/scan errors.
  - Malformed real `SKILL.md` declarations fail validation and produce doctor/parser errors (`--fail-on error`).

---

## 5. Casing, Depth, and Traversal Boundaries

- **Casing compatibility:** Permissive generic directory matching for both `SKILL.md` and lowercase `skill.md` (`parser._SKILL_FILENAMES`) is retained for unconstrained directory formats as existing parser compatibility, not proven vendor semantics. Strict exact `SKILL.md` is enforced specifically for Pi and OpenCode V2 where authoritative sources mandate it.
- **Traversal depth policy:** OpenCode V2 recursive tree walk inherits the engine-wide `MAX_WALK_DEPTH = 4` bounded depth policy (to bound filesystem traversal and protect against unbounded descent or cycles). This inherited engine policy must be distinguished from vendor specifications that state recursive discovery without an explicit depth ceiling.
- **Current traversal limitations:**
  - *No recursive traversal through symlink container without own SKILL.md:* Traversal follows symlinked skill directories containing their own exact `SKILL.md`, but does not recursively descend through intermediate symlinked directory containers that lack their own `SKILL.md`.
  - *Stop at declared skill directory:* Once a directory is identified as a declared skill directory (containing `SKILL.md`), recursive search stops at that declared skill directory boundary and does not descend into its nested child directories for additional nested skill declarations.
- **Stage D Carryover:** Full vendor identity resolution (including Pi vendor lookup ID policy), full Antigravity CLI root/surface alignment, config loadability vs validity integration (Stage D step 5), disabled setting decoders, traversal limitation reviews, and final precedence matrix alignment are carried forward to Stage D evidence tables.

---

## 6. Explicit Root Entry Formats and Evidence Table (Affected Six Agents)

### 6.1 Correction Notice & Provenance Correction

The previous Stage C correction report contained two significant provenance errors:
1. **DSH format error:** The previous report asserted that all DSH roots were "backed by primary docs" as `directory`-only. This assertion was false and directly contradicted primary documentation: DeepSeek Harness documentation (`docs/subsystems/skills.md` lines 83–85) explicitly states that the local provider accepts directory bundles (`<name>/SKILL.md`) AND flat Markdown files (`<name>.md`). Native DSH roots have now been corrected to `standalone_md`. Retained plugin root `dsh_profiles` has also been set to `standalone_md` to preserve baseline discovery compatibility, with vendor loadability noted as unresolved for Stage D.
2. **Dead URLs:** The previous report cited URLs that return HTTP 404 (`docs.x.ai/grok-cli/skills`, `docs.qoder.com/skills`, `docs.codeium.com/windsurf/skills`). These dead URLs have been replaced with verified, authoritative primary sources fetched and verified on 2026-10-13.
3. **Retained Root Count:** There are exactly **20 retained roots** across the six affected agents (Claude: 2, DSH: 5, Grok: 3, Qoder: 3, OMP: 4, Windsurf: 3), not 18.
4. **Baseline Compatibility Preservation for Unverified/Non-Native Roots:** As authorized by Stage C principles, retained roots whose vendor format is unverified or non-native (`dsh_profiles`, `grok_bundled`, `grok_project`, `qoder_project_agents`, `omp_agent`, `windsurf_project_agents`) explicitly declare `entry_format = "standalone_md"` to preserve the observed pre-C baseline discovery surface (both directory bundles and flat Markdown files). Unknown root flat acceptance is **Skill Lens compatibility**, NOT proven vendor support/loadability; vendor loadability remains an unresolved Stage D carryover. Documented native directory roots (`claude_personal`, `claude_project`, `grok_global`, `qoder_global`, `qoder_project`, `omp_project`, `omp_project_agents`, `omp_shared_global`, `windsurf_global`, `windsurf_project`) strictly enforce `entry_format = "directory"`.

Format evidence is strictly independent from existing root precedence evidence: empirical roots remain empirical; no root ranks, collision policies, or disabled controls were altered.

### 6.2 Primary Source Receipts & Verification (2026-10-13)

| Canonical Primary Source URL | HTTP Status | Document Section | Verified Fact |
| :--- | :--- | :--- | :--- |
| `https://code.claude.com/docs/en/skills` | 200 OK | Skill Location & Directory Structure | Skills live in directories containing `SKILL.md` (`~/.claude/skills/<skill>/SKILL.md` and `.claude/skills/<skill>/SKILL.md`). Legacy `.claude/commands/*.md` are separate command roots, not standalone skills under `.claude/skills`. |
| `https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/docs/subsystems/skills.md` | 200 OK | Section "Skill identity" lines 83–85 | "The local provider accepts directory bundles (`<name>/SKILL.md`) and flat Markdown files (`<name>.md`). Nested recursive `**/SKILL.md` discovery is not supported." Native roots support directory bundles and flat Markdown files. |
| `https://raw.githubusercontent.com/xai-org/grok-build/main/crates/codegen/xai-grok-pager/docs/user-guide/08-skills.md` | 200 OK | Section "Directory Structure" lines 47–59 | "Each skill lives in its own directory with a `SKILL.md` file: `~/.grok/skills/<skill>/SKILL.md`". (Old URL `https://docs.x.ai/grok-cli/skills` 404). |
| `https://docs.qoder.com/cli/Skills` | 200 OK | Sections "Where Skills live" & "Organize Directory Structure" | Skills live at `~/.qoder/skills/{skill-name}/SKILL.md` (user) and `.qoder/skills/{skill-name}/SKILL.md` (project). Every skill requires a `SKILL.md` file in its directory. (Old URL `https://docs.qoder.com/cli/skills` 404). |
| `https://raw.githubusercontent.com/can1357/oh-my-pi/main/docs/skills.md` | 200 OK | Section "Required layout and SKILL.md expectations" lines 23–28 | For conventional roots (native/Claude/Codex/Agents/plugins), skills are discovered one level under `skills/`: `<skills-root>/<skill-name>/SKILL.md`. Managed skills actual path is `~/.omp/agent/managed-skills`. |
| `https://docs.windsurf.com/windsurf/cascade/skills` (redirects to `https://docs.devin.ai/desktop/cascade/skills`) | 200 OK (301 redirect) | "How to Create a Skill" & "SKILL.md File Format" | Global skills live at `~/.codeium/windsurf/skills/<skill-name>/SKILL.md` and workspace at `.windsurf/skills/<skill-name>/SKILL.md` (legacy path). Directory bundles containing `SKILL.md`. Shared `.agents/skills` is undocumented by vendor. (Old `docs.codeium.com` 404). |

### 6.3 Explicit Root Entry Format Table (All 20 Retained Roots)

| Agent | Root ID | Path | Scope | Root Precedence Evidence | Declared Entry Format | Format Evidence | Primary Source / Basis | Verification Date | Supported Form & Omission |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Claude** | `claude_personal` | `.claude/skills` | `user` | `documented` | `directory` | `documented` | `https://code.claude.com/docs/en/skills` | 2026-10-13 | Documented native directory `<skill>/SKILL.md` supported; standalone `.md` omitted |
| **Claude** | `claude_project` | `.claude/skills` | `project` | `documented` | `directory` | `documented` | `https://code.claude.com/docs/en/skills` | 2026-10-13 | Documented native directory `<skill>/SKILL.md` supported; standalone `.md` omitted |
| **DSH** | `dsh_project` | `.dsh/skills` | `project` | `documented` | `standalone_md` | `documented` | DeepSeek Harness docs line 85 | 2026-10-13 | Documented native directory `<name>/SKILL.md` AND flat `<name>.md` supported; non-md / nested flat omitted |
| **DSH** | `dsh_project_agents` | `.agents/skills` | `project` | `documented` | `standalone_md` | `documented` | DeepSeek Harness docs line 85 | 2026-10-13 | Documented native directory `<name>/SKILL.md` AND flat `<name>.md` supported; non-md / nested flat omitted |
| **DSH** | `dsh_profiles` | `.dsh/profiles` | `plugin` | `inferred` | `standalone_md` | `inferred` | Inferred compatibility root; preserves pre-C baseline discovery surface | 2026-10-13 | Compatibility: directory bundles AND flatfiles in nested skills container supported; non-md omitted. Vendor loadability unresolved (Stage D) |
| **DSH** | `dsh_user` | `.dsh/skills` | `user` | `documented` | `standalone_md` | `documented` | DeepSeek Harness docs line 85 | 2026-10-13 | Documented native directory `<name>/SKILL.md` AND flat `<name>.md` supported; non-md / nested flat omitted |
| **DSH** | `dsh_shared_global` | `.agents/skills` | `user` | `documented` | `standalone_md` | `documented` | DeepSeek Harness docs line 85 | 2026-10-13 | Documented native directory `<name>/SKILL.md` AND flat `<name>.md` supported; non-md / nested flat omitted |
| **Grok** | `grok_global` | `.grok/skills` | `user` | `empirical` | `directory` | `documented` | Grok build user guide 08-skills.md lines 47–59 | 2026-10-13 | Documented native directory `<skill>/SKILL.md` supported; standalone `.md` omitted |
| **Grok** | `grok_bundled` | `.grok/bundled/skills` | `system` | `empirical` | `standalone_md` | `inferred` | Inferred compatibility root; preserves pre-C baseline discovery surface | 2026-10-13 | Compatibility: directory `<skill>/SKILL.md` AND flat `<skill>.md` supported; non-md omitted. Vendor loadability unresolved (Stage D) |
| **Grok** | `grok_project` | `.agents/skills` | `project` | `empirical` | `standalone_md` | `inferred` | Inferred compatibility root; preserves pre-C baseline discovery surface | 2026-10-13 | Compatibility: directory `<skill>/SKILL.md` AND flat `<skill>.md` supported; non-md omitted. Vendor loadability unresolved (Stage D) |
| **Qoder** | `qoder_global` | `.qoder/skills` | `user` | `empirical` | `directory` | `documented` | `https://docs.qoder.com/cli/Skills` | 2026-10-13 | Documented native directory `~/.qoder/skills/{skill}/SKILL.md` supported; standalone `.md` omitted |
| **Qoder** | `qoder_project` | `.qoder/skills` | `project` | `empirical` | `directory` | `documented` | `https://docs.qoder.com/cli/Skills` | 2026-10-13 | Documented native directory `.qoder/skills/{skill}/SKILL.md` supported; standalone `.md` omitted |
| **Qoder** | `qoder_project_agents` | `.agents/skills` | `project` | `empirical` | `standalone_md` | `inferred` | Inferred compatibility root; preserves pre-C baseline discovery surface | 2026-10-13 | Compatibility: directory `<skill>/SKILL.md` AND flat `<skill>.md` supported; non-md omitted. Vendor loadability unresolved (Stage D) |
| **OMP** | `omp_project` | `.omp/skills` | `project` | `documented` | `directory` | `documented` | Oh My Pi skills.md lines 23–28 | 2026-10-13 | Documented native directory `<skills-root>/<skill>/SKILL.md` supported; standalone `.md` omitted |
| **OMP** | `omp_project_agents` | `.agents/skills` | `project` | `documented` | `directory` | `documented` | Oh My Pi skills.md lines 23–28 | 2026-10-13 | Documented native directory `<skills-root>/<skill>/SKILL.md` supported; standalone `.md` omitted |
| **OMP** | `omp_shared_global` | `.agents/skills` | `user` | `documented` | `directory` | `documented` | Oh My Pi skills.md lines 23–28 | 2026-10-13 | Documented native directory `<skills-root>/<skill>/SKILL.md` supported; standalone `.md` omitted |
| **OMP** | `omp_agent` | `.omp/agent` | `user` | `documented` | `standalone_md` | `inferred` | Inferred compatibility root (upstream managed skills path differs); preserves pre-C baseline discovery surface | 2026-10-13 | Compatibility: directory `<skill>/SKILL.md` AND flat `<skill>.md` supported; non-md omitted. Vendor loadability/managed path alignment unresolved (Stage D) |
| **Windsurf** | `windsurf_global` | `.codeium/windsurf/skills` | `user` | `empirical` | `directory` | `documented` | Devin/Windsurf docs (legacy path) | 2026-10-13 | Documented native directory `<skill>/SKILL.md` supported; standalone `.md` omitted |
| **Windsurf** | `windsurf_project` | `.windsurf/skills` | `project` | `empirical` | `directory` | `documented` | Devin/Windsurf docs (legacy path) | 2026-10-13 | Documented native directory `<skill>/SKILL.md` supported; standalone `.md` omitted |
| **Windsurf** | `windsurf_project_agents` | `.agents/skills` | `project` | `empirical` | `standalone_md` | `inferred` | Inferred compatibility root; preserves pre-C baseline discovery surface | 2026-10-13 | Compatibility: directory `<skill>/SKILL.md` AND flat `<skill>.md` supported; non-md omitted. Vendor loadability unresolved (Stage D) |

### 6.4 Non-Native and Shared Root Compatibility Policy

For retained non-native roots (`dsh_profiles`, `grok_bundled`, `grok_project`, `qoder_project_agents`, `omp_agent`, `windsurf_project_agents`), vendor documentation either does not specify format or specifies a different container path. Consistent with authorized Stage C principles:
1. Baseline discovery compatibility is preserved explicitly rather than silently narrowed. Exactly these six unverified/non-native roots declare `entry_format = "standalone_md"` to preserve the observed pre-C baseline discovery surface (both directory bundles and flat Markdown files).
2. Unknown root flat acceptance is **Skill Lens compatibility**, NOT proven vendor support/loadability.
3. Inferred format evidence is transparently designated as `inferred` (or `unverified`).
4. Actual vendor loadability is acknowledged as unresolved and explicitly carried over to Stage D validation.
5. Documented native directory roots (`claude_personal`, `claude_project`, `grok_global`, `qoder_global`, `qoder_project`, `omp_project`, `omp_project_agents`, `omp_shared_global`, `windsurf_global`, `windsurf_project`) remain strictly `directory`-only, while DSH native roots maintain documented directory bundle + flat Markdown support.
6. No root ranks, collision policies, or precedence classifications were modified.
