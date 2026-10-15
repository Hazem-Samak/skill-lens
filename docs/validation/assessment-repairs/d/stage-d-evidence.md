# Stage D Evidence Record: Supported Agent Rules, Identity, and Configuration Alignment

**Date:** 2026-10-13  
**Status:** Implementation Complete  
**Scope:** Stage D (F01, F02) — Truthful Supported-Version Lookup/Loadability and Configuration-Controlled Resolution  
**Implementer:** Antigravity (`gemini-3.8-flash-high`, full-access, default interaction mode)

---

## 1. Registry Evidence & Specification Matrix (All Ten Agents)

This evidence table documents all ten agents in `skill_lens/registry/agents/*.toml`. Every row links to an authoritative primary source section and verification date. Generic homepage URLs and unverified assumptions are strictly excluded.

| Agent ID | Declared Surface & Version Range | Identity Resolution Policy | Search Roots & Formats | Recursion Contract | Collision & Precedence Policy | Configuration & Permission Controls | Primary Source URL & Section | Verification Date | Proved vs. Unknown Boundaries |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`claude`** | Claude Code CLI (official documentation snapshot 2026-10-13) | **Hybrid**: Frontmatter `name` sets command name (`/name`); directory name can also invoke it (`/dirname`). | Native user `~/.claude/skills` (rank 100, `directory`) and project `.claude/skills` (rank 50, `directory`). Subdirectory project roots supported. | Non-recursive for native skills (`<skill>/SKILL.md`). Project subdirectories support `.claude/skills` (`dir:cmd` namespace). | **Personal > Project**: User outranks Project at repo root (`claude_personal_beats_project`). Nested project coexists as qualified `dir:cmd`. | `skillOverrides` across settings stack: Local (`.claude/settings.local.json`) > Project (`.claude/settings.json`) > User (`~/.claude/settings.json`). Values: `"on"`, `"name-only"`, `"user-invocable-only"`, `"off"`, plus legacy boolean `false`/`true`. Settings apply to declared command identity. Frontmatter `disable-model-invocation: true`, `user-invocable: false`. Description optional (body-line fallback). | `https://code.claude.com/docs/en/skills` (Where skills live, How a skill gets its command name, Override skill visibility); `https://code.claude.com/docs/en/settings` (Settings precedence) | 2026-10-13 | **Proved**: CLI command naming, settings override stack, 4 visibility states, optional description. **Unknown/Unmodelled**: Enterprise MDM managed settings, cloud sync `~/.claude/skills/synced/`. |
| **`codex`** | OpenAI Codex CLI / ChatGPT Developer | **Frontmatter Name** (`frontmatter_name`), fallback to directory. | `~/.codex/skills` (rank 85), `~/.agents/skills` (rank 80), `.agents/skills` (rank 90), `~/.codex/skills/.system` (rank 55), `/etc/codex/skills` (rank 75), `.codex/.tmp/plugins` (rank 10, recursive). All `directory`. | Non-recursive for conventional roots (`<skill>/SKILL.md`). Recursive only for plugin roots. | **Merge / Coexistence**: Coexists across roots with project ancestor walk (`coexist_policy = "merge"`). | `~/.codex/config.toml` contains `[[skills.config]]` tables with absolute `path = "/path/to/skill/SKILL.md"` and `enabled = false`. Description required per Agent Skills standard. Relative paths have no documented base and are flagged unsupported in notes. | `https://learn.chatgpt.com/docs/build-skills` (Enable or disable local Codex skills, Directory Structure) | 2026-10-13 | **Proved**: Absolute path-based `[[skills.config]]` disable in `config.toml`, directory format. **Unknown/Unmodelled**: Relative path base resolution, Desktop app `agents/openai.yaml` UI metadata and remote catalogs. |
| **`pi`** | Pi Coding Agent (`@earendil-works/pi`) | **Frontmatter Name** (`frontmatter_name`) with parent directory fallback (`frontmatterName \|\| parentDirName`). | Documented user default `~/.pi/agent/skills` (rank 95, `qualified_standalone_md`), inferred legacy `~/.pi/skills` (rank 90, `qualified_standalone_md`), project `.pi/skills` (rank 70), and shared `.agents/skills` (rank 65). | Stop at declared skill directory: if directory contains `SKILL.md`, do not recurse further. Otherwise, recurses into subdirectories up to depth 16 (`MAX_PI_WALK_DEPTH = 16`) and loads direct `.md` files in root. | **User > Project**: In `loadSkills()`, user defaults load before project defaults. First loaded wins (`existing` wins, later is collision loser). | Frontmatter `disable-model-invocation: true` excludes from prompt (manual `/skill:name` only). Description is strictly required (`if (!hasDescription) return { skill: null }`). No file-based config disable. | `https://github.com/earendil-works/pi/blob/main/packages/coding-agent/src/core/skills.ts` (`loadSkills`, `loadSkillFromFile`) | 2026-10-13 | **Proved**: Frontmatter fallback, User > Project load order, collision diagnostics, description requirement, stop-at-skill recursion. **Unknown/Unmodelled**: Inferred `~/.pi/skills` root vendor support, `.gitignore` traversal handling, CLI `--skill` flag paths. |
| **`qoder`** | Qoder CLI | **Frontmatter Name** (`frontmatter_name`) with directory fallback. | `~/.qoder/skills` (rank 95, `directory`), `.qoder/skills` (rank 70, `directory`), `.agents/skills` (rank 65, `standalone_md` compatibility, loadability: unknown). | Non-recursive under `skills/`: directory bundles `{skill-name}/SKILL.md`. | **User > Project**: Official docs explicitly state: **User-level skills override project-level skills**. | Unmodelled in local CLI; documented as unmodelled. Valid frontmatter required. | `https://docs.qoder.com/cli/Skills` (Where Skills live, Choose Storage Location, Multiple Skills Conflict) | 2026-10-13 | **Proved**: User-over-project precedence, directory bundle structure. **Unknown/Unmodelled**: Retained `.agents/skills` compatibility root vendor loadability is unverified (`UNKNOWN`), Cloud Agent and Remote Control ACP configurations. |
| **`antigravity`** | Google Antigravity CLI (`agy`) | **Hybrid**: Directory name or frontmatter name. | `~/.gemini/antigravity-cli/skills` (rank 75, `standalone_md`, documented CLI global), `~/.gemini/config/skills` (rank 70, `standalone_md`, Antigravity 2.0/IDE legacy, loadability: unknown), `.agents/skills` (rank 90, loadability: unknown), `.agent/skills` (rank 85, loadability: unknown), `.gemini/antigravity/builtin/skills` (rank 30). | Non-recursive for conventional roots; directory bundles and standalone `.md`. | **Project > User > Builtin**: Project outranks CLI global, which outranks legacy IDE global, which outranks builtin. | TUI slash command conversion. Configuration controls unmodelled. | `https://antigravity.google/docs/skills` (Skills by surface: Antigravity CLI vs Antigravity 2.0) | 2026-10-13 | **Proved**: CLI root `~/.gemini/antigravity-cli/skills` vs IDE root `~/.gemini/config/skills`. **Unknown/Unmodelled**: Retained compatibility roots (`~/.gemini/config/skills`, `.agents/skills`) vendor loadability is unverified (`UNKNOWN`), Antigravity CLI plugins under `~/.gemini/antigravity-cli/plugins`, cross-surface CLI/IDE precedence. |
| **`omp`** | Oh My Pi CLI (`omp`) | **Frontmatter Name** (`frontmatter_name`), directory fallback. | `.omp/skills` (rank 95, `directory`), `.agents/skills` (rank 90, `directory`), `~/.agents/skills` (rank 70, `directory`), `~/.omp/agent/managed-skills` (rank 45, `directory`, documented managed), `.omp/agent` (rank 40, `standalone_md`, retained legacy compatibility, loadability: unknown). | Non-recursive for conventional provider roots (`<root>/skills/<skill>/SKILL.md`). | **Authored > Managed**: Authored provider skills outrank managed skills (managed resolved dead-last at priority 5). Coexistence across foreign providers. | Frontmatter `enabled: false` disables skill (`DISABLED` headline). Frontmatter `hide: true` / `disableModelInvocation: true` sets `user_only` invocation. Native `.omp` provider requires description; foreign providers (Claude, Codex, agents, OpenCode) do not. | `https://raw.githubusercontent.com/can1357/oh-my-pi/main/docs/skills.md` (Built-in skill providers, Directory layout, Source toggles) | 2026-10-13 | **Proved**: Managed path `~/.omp/agent/managed-skills`, provider priority, per-provider description requirements, `enabled: false`. **Unknown/Unmodelled**: Legacy `.omp/agent` vendor loadability (unknown), Skillshare store, custom directories array. |
| **`opencode`** | OpenCode V2 ONLY (V1 explicitly unsupported) | **Path-Derived ID** (`directory_name`): file stem for `.md`, parent directory name for `SKILL.md`. Frontmatter `name` is display label only. | In increasing precedence: `.claude/skills` (user: rank 50, project: rank 55), `.agents/skills` (user: rank 60, project: rank 65), `~/.config/opencode/skills` (rank 70), `.opencode/skills` (rank 80). Format: `opencode_v2`. | Root-level `*.md` files plus recursive `**/SKILL.md` up to `MAX_OPENCODE_WALK_DEPTH = 32`, finding nested SKILL.md without stopping at parent skill. Truncation past depth 32 is guarded. | **Later-Source Precedence**: Later-registered source outranks earlier-registered source for same skill ID (`Shadow (Later-registered source wins)`). Child project source outranks parent ancestor project source. | Config files: Direct configs (farthest->closest), THEN hidden `.opencode` directory configs (farthest->closest) outrank direct. Permissions: `{"action": "skill", "resource": "<id|\*>", "effect": "deny"\|"allow"\|"ask"}`. Wildcards treat only `*` and `?` as special (ordered last-match). `deny` sets `DISABLED`. Frontmatter `opencode/autoinvoke: false` or missing description sets `user_only`. All frontmatter optional at runtime. Unsupported V1 `permission` or agent-specific configs disclosed in notes. | `https://opencode.ai/v2/docs/skills/` (Discovery, Sources, IDs, Precedence, Frontmatter); `https://opencode.ai/v2/docs/permissions/` (Skills); `https://opencode.ai/v2/docs/config/` (Precedence, Locations) | 2026-10-13 | **Proved**: OpenCode V2 path-derived IDs, recursive discovery, `.claude` roots, later-source precedence, permissions schema, hidden outranking direct configs. **Unknown/Unmodelled**: OpenCode V1 rules (unsupported), agent-specific permissions, HTTP catalogs, web remote sync. |
| **`dsh`** | DeepSeek Harness CLI | **Directory Name** (`directory_name`) or flat file stem. | `.dsh/skills` (rank 95), `.agents/skills` (rank 90), `~/.dsh/skills` (rank 70), `~/.agents/skills` (rank 65), `.dsh/profiles` (rank 40, plugin container). Format: `standalone_md`. | Non-recursive for native skill roots; accepts directory bundles and flat `.md` files. Plugin container is recursive. | **Project > User**: Project roots outrank user roots (`Shadow (Project > User)`). | Local CLI controls unmodelled. Directory bundle or flat `.md` with valid frontmatter. | `https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/docs/subsystems/skills.md` (lines 83–85) | 2026-10-13 | **Proved**: Native flat + directory bundle format, Project > User precedence. **Unknown/Unmodelled**: `customSkillDirs` and `bundledSkillDir`. |
| **`grok`** | Grok Build CLI (`xai-grok-pager`) | **Frontmatter Name** (`frontmatter_name`) with directory fallback. | `~/.grok/skills` (rank 70, `directory`), `.grok/bundled/skills` (rank 30, `standalone_md` compatibility, loadability: unknown), `.agents/skills` (rank 90, `standalone_md` compatibility, loadability: unknown). | Non-recursive under `skills/`: directory bundles `<skill>/SKILL.md`. | **Project > Global**: Project roots outrank global roots. | Local CLI controls unmodelled. Valid frontmatter required. | `https://raw.githubusercontent.com/xai-org/grok-build/main/crates/codegen/xai-grok-pager/docs/user-guide/08-skills.md` (lines 47–59) | 2026-10-13 | **Proved**: Native directory bundle format. **Unknown/Unmodelled**: Retained compatibility roots (`.grok/bundled/skills`, `.agents/skills`) vendor loadability is unverified (`UNKNOWN`). |
| **`windsurf`** | Windsurf CLI / IDE (Cascade) | **Hybrid**: Directory name or frontmatter name. | `~/.codeium/windsurf/skills` (rank 70, `directory`), `.windsurf/skills` (rank 90, `directory` legacy, loadability: unknown), `.agents/skills` (rank 85, `standalone_md` compatibility, loadability: unknown). | Non-recursive under `skills/`: directory bundles `<skill>/SKILL.md`. | **Project > Global**: Workspace roots outrank global roots. | Local CLI controls unmodelled. Directory bundle with `SKILL.md` required. | `https://docs.windsurf.com/windsurf/cascade/skills` (redirects to `https://docs.devin.ai/desktop/cascade/skills`) | 2026-10-13 | **Proved**: Global and workspace directory bundle paths. Distinct from Devin desktop. **Unknown/Unmodelled**: Retained compatibility roots (`.windsurf/skills` legacy, `.agents/skills`) vendor loadability is unverified (`UNKNOWN`). |

---

## 2. Proved Identity, Precedence, and Recursion Rules

1. **Claude Command Identity**:
   - Primary command name is determined by frontmatter `name` when present (`/name`).
   - The directory name provides an invocation alias (`/dirname`).
   - `claude.toml` is configured with `identity_source = "hybrid"`, enabling both frontmatter command names and directory names to match without guessing.
   - Settings overrides (`skillOverrides`) match the skill's declared command identity, not unrelated folder names.
   - Collision behavior between personal and project roots follows documented `Personal > Project` precedence.

2. **Pi Frontmatter Fallback & Recursion Rules**:
   - Identity: `frontmatterName || parentDirName` from upstream `skills.ts`. Configured with `identity_source = "frontmatter_name"`, which uses frontmatter name when present and falls back to parent directory name.
   - Recursion: Stop at declared skill directory: for subdirectories, if a directory contains `SKILL.md`, it is a skill boundary and traversal does not recurse deeper into it. Implemented in discovery engine for Pi roots with depth limit `MAX_PI_WALK_DEPTH = 16`. Subdirectories without `SKILL.md` are descended to find nested `SKILL.md` files, skipping dot-files and `node_modules`. Nested `.gitignore` handling is an unmodelled limitation.
   - Collision: Upstream `loadSkills()` loads User skills (`~/.pi/agent/skills`, `~/.pi/skills`) first, then Project skills (`.pi/skills`). In `addSkills()`, the first loaded entry wins and later copies are flagged as collisions. Ranks reflect `User > Project` (`Shadow (User > Project)`).

3. **Qoder Priority Correction**:
   - Official Qoder documentation explicitly establishes that **user-level skills override project-level skills**.
   - `qoder_global` (`~/.qoder/skills`) is assigned rank 95, outranking `qoder_project` (`.qoder/skills`, rank 70).
   - Collision policy is corrected to `Shadow (User > Project)` with `documented` evidence.

4. **Antigravity CLI vs. IDE Locations**:
   - Upstream Antigravity documentation defines distinct locations per surface:
     - Antigravity CLI: `~/.gemini/antigravity-cli/skills` (global) and `<workspace>/.agents/skills` (project).
     - Antigravity 2.0 / IDE: `~/.gemini/config/skills` (global) and `<workspace>/.agents/skills` (project).
   - `antigravity.toml` adds `antigravity_cli_global` (`~/.gemini/antigravity-cli/skills`, rank 75) as the primary CLI global root, while retaining `antigravity_global` (`~/.gemini/config/skills`, rank 70) and `.agents/skills` project roots as legacy/compatibility locations whose vendor loadability is designated as unverified `UNKNOWN`.

5. **Oh My Pi (`omp`) Managed Skills Path**:
   - Authoritative documentation in `can1357/oh-my-pi` specifies that managed skills are located at `~/.omp/agent/managed-skills` (layout: `<skill-name>/SKILL.md`), registered dead-last at priority 5.
   - `omp.toml` adds `omp_managed` (`~/.omp/agent/managed-skills`, rank 45, `directory`) with `documented` evidence.
   - The legacy `omp_agent` (`.omp/agent`, rank 40, `standalone_md`) is retained for backward compatibility, with vendor loadability designated as unverified.

6. **OpenCode V2 ONLY Specification**:
   - OpenCode V1 is explicitly unsupported; V1 rules (such as ambiguous duplicate collision) are superseded by V2.
   - Identity: Path-derived ID (`identity_source = "directory_name"`). File stem for `<name>.md`, parent directory name for `<name>/SKILL.md`. Frontmatter `name` is purely a display label.
   - Sources & Compatibility Roots: Supports `.claude/skills` (user and project), `.agents/skills` (user and project), `~/.config/opencode/skills`, and `.opencode/skills`.
   - Precedence: Later-registered source precedence:
     `Project .opencode > ~/.config/opencode > Project .agents > Global .agents > Project .claude > Global .claude`.
   - Ancestor Precedence: Within project roots, child directories (closer to working directory) outrank parent ancestor directories.
   - Format: `entry_format = "opencode_v2"` (root-level `*.md` + recursive `**/SKILL.md` up to depth 32, not stopping at parent skill).

---

## 3. Pure Configuration Decoders & Precedence Architecture

1. **Claude Settings (`.claude/settings.json`, `.claude/settings.local.json`)**:
   - Pure decoder: `decode_claude_settings(data: bytes | None) -> dict[str, str | bool]`.
   - Error-preserving decoder: `decode_claude_settings_with_status(data) -> tuple[dict, str | None]`. Empty files and invalid types return `"malformed"`.
   - Precedence resolution: `resolve_claude_settings(user_data, project_data, local_data)`.
   - Stack: Local overrides Project, Project overrides User.
   - States:
     - `"off"` or `false`: Disabled (`HeadlineState.DISABLED`, `PermissionEffect.DENY`).
     - `"user-invocable-only"`: User manual invocation only (`InvocationPolicy.USER_ONLY`).
     - `"name-only"`: Model sees name only, not description/body (`InvocationPolicy.NAME_ONLY`).
     - `"on"` or `true`: Fully enabled (`InvocationPolicy.ALL`, `PermissionEffect.ALLOW`).

2. **Codex Configuration (`~/.codex/config.toml`)**:
   - Pure decoder: `decode_codex_config(data: bytes | None) -> dict[str, bool]`.
   - Normalization: Normalized once during live acquisition into pure frozen data. Evaluation at snapshot time is 100% lexical with zero filesystem I/O.
   - Parses TOML `[[skills.config]]` tables. Absolute paths matching candidate entrypoint, canonical, or `SKILL.md` path with `enabled = false` set `HeadlineState.DISABLED`.
   - Relative paths without documented primary base are flagged as unsupported in notes.

3. **OpenCode V2 Permissions & Bounded Modeling (`opencode.json`, `opencode.jsonc`)**:
   - Pure decoder: `decode_opencode_permissions(data: bytes | None) -> list[OpenCodePermissionRule]`.
   - Returns immutable `OpenCodePermissionRule(resource, effect)` dataclasses preserving file order.
   - Layer Order: All direct project configs (farthest->closest), THEN all hidden `.opencode` directory configs (farthest->closest) outrank direct configs.
   - Wildcards: Evaluates using pure string matching where only `*` (0+ chars) and `?` (1 char) are wildcards; brackets `[]` and other regex characters are literal. Last matching rule wins.
   - If effective effect is `"deny"`: Disabled (`HeadlineState.DISABLED`, `PermissionEffect.DENY`).
   - If effective effect is `"ask"`: Permission prompt required (`PermissionEffect.ASK`).
   - **Bounded Production Disclosure (`OPENCODE_BOUNDED_DISCLOSURE_NOTE`)**:
     OpenCode evaluation explicitly discloses omitted system/managed configuration locations (`/etc/opencode/`, macOS managed preferences), system skills, existing-session selections, and agent-specific policies. It declares the base `build` agent assumption.
   - **Agent Selection Confidence**:
     Non-default `default_agent` (e.g. `default_agent: "plan"`) or non-default builtins mark applicable permission confidence as `UNKNOWN` rather than asserting unrestricted runtime `ALLOW`. Explicit modelled `deny` permissions retain precedence as `DISABLED`.

4. **Security & Privacy Guardrails (Strict Diagnostic Redaction)**:
   - Decoders only parse skill-related keys (`skillOverrides`, `skills.config`, `permissions`, `default_agent`).
   - **Diagnostic Secret Redaction**: Decoders, diagnostics, and resolution notes never interpolate raw configuration values (effect strings, agent identifiers, resource patterns, or relative path tokens) into reportable error or unsupported strings. Only the containing config file path location is cited, preventing synthetic secret leaks (`SYNTHETIC_SECRET_42`) in live and captured reports.
   - Missing, malformed, and unreadable files are distinctly categorized without disclosing unmodelled content.

---

## 4. Portability Parsing vs. Agent Loadability

1. **Parser Portability Status** (Generic Axis 1):
   - Remains strictly file-level: `VALID`, `MISSING_DESCRIPTION`, `MALFORMED_YAML`, `UNREADABLE`.
   - Evaluates general standards compliance independently of any specific agent.

2. **Agent-Specific Loadability**:
   - **Claude**: Optional description (falls back to body line). Missing description does NOT make a skill `INVALID`; it loads successfully as `LOADABLE`.
   - **OpenCode V2**: All frontmatter is optional at runtime. A skill without description or without frontmatter loads successfully as `LOADABLE`; it is registered and manually invokable by ID, but not advertised to the model (`user_only` invocation).
   - **OMP**: Native root `.omp/skills` requires description (`INVALID` if missing); foreign roots (`.agents/skills`, `.claude/skills`) do not require description (`LOADABLE`).
   - **Pi**: Description is strictly required (`INVALID` if missing).
   - **Codex**: Valid frontmatter and description required (`INVALID` if missing).

3. **Invocation and Visibility States**:
   - Distinguishes `ALL` (both model and user), `USER_ONLY` (manual `/command` only, not advertised to model), `MODEL_ONLY`, `NAME_ONLY` (Claude name-only visibility), and `NONE` (disabled).
   - Distinguishes permission effects: `ALLOW`, `DENY`, `ASK`, and `UNKNOWN`.
   - Discloses unmodelled controls or unverified root loadability in resolution notes, ensuring that unknown behavior never yields an unqualified confident `ACTIVE`.

---

## 5. Council Round 1 Corrections & Verifications

The following corrections resolve all accepted blocker items from Council Round 1 adjudication:

1. **A. Codex Symlink Configuration Parity**:
   - Live acquisition and session capture normalize config paths symmetrically during acquisition.
   - Session snapshot resolution is 100% lexical with zero filesystem reads or probes (`is_dir`, `resolve` blocked).
   - Changing or deleting config files or skill directories on disk after capture does not alter frozen snapshot resolution.
   - Suffix matching is strictly rejected; exact normalized path matching is enforced.

2. **B. Explicit `disabled_overrides=` API**:
   - Preserves candidate hit identity and alias intersection across all supported candidate identities (frontmatter command name, directory name, entrypoint path, canonical path).
   - Keeps source-backed settings-file command matching deliberate for Claude declared command identity.
   - Fully supports custom/hybrid agents, supplied `DiscoveryIndex`, and `FrozenDiscoveryIndex`.

3. **C. Doctor Portability & Loadability Consistency**:
   - Plain frontmatter-less OpenCode skills are classified as `ParseStatus.MALFORMED_YAML` with `missing_frontmatter`.
   - Doctor reports portability warning without claiming runtime skip: `portable agents will skip '<name>' (accepted at runtime by opencode)`.
   - Stage A/B severity agreement is preserved; doctor distinguishes raw portability findings from agent loadability.
   - Foreign provider optional description for OMP and unknown retained root loadability are properly diagnosed.

4. **D. Unknown Retained Roots**:
   - Unverified compatibility roots (`qoder_project_agents`, `grok_bundled`, `grok_project`, `windsurf_project_agents`, `antigravity_global`, `antigravity_project_agents`) are designated with `loadability = "unknown"`.
   - Resolution marks candidate loadability as `UNKNOWN` and attaches explanatory notes disclosing that vendor loadability is unverified.
   - DSH native roots (`.agents/skills`, `.dsh/skills`) remain native `loadable` based on primary documentation.

5. **E. OpenCode Invocation & Permission Discrimination**:
   - Missing description precludes model advertisement even when `autoinvoke: true` is set (`user_only`).
   - `metadata.opencode/autoinvoke: true` outranks `disable-model-invocation: true` only when description exists (`all`).
   - Non-boolean `autoinvoke` values resolve to `unknown` invocation policy.
   - Permission `deny` sets headline `DISABLED` with distinct candidate reason `"Denied by OpenCode skill permission"`.

6. **F. OpenCode Config Extent**:
   - OpenCode ancestor walk for `opencode.json`/`opencode.jsonc` searches all directory ancestors up to the filesystem/sandbox root, independent of `.git` project boundaries.
   - Enforces layer ordering: all direct project configs (farthest->closest), followed by all hidden `.opencode` directory configs (farthest->closest).

7. **G. Bounded Discovery & Truncation Disclosure**:
   - Exact-cap leaf inspection before pruning: directories at the exact depth cap (`MAX_OPENCODE_WALK_DEPTH = 32`, `MAX_PI_WALK_DEPTH = 16`, `MAX_WALK_DEPTH = 4`) are inspected for `SKILL.md` before pruning child directories. Leaf directories at the cap without child subdirectories are discovered without emitting synthetic truncation warnings.
   - Child subdirectories extending past the depth cap are pruned, truthfully recording `depth_limit_truncated` in `unreadable_roots`.
   - Resolution reports disclose directory truncation in `notes`, preventing false authoritative absence for pruned candidates, and doctor emits `depth_limit_truncated` warnings.

8. **H. Non-Target Nested Coexistence**:
   - Base nested copy coexistence restored for non-OpenCode profiles.
   - Ancestor specificity tie-breaking restricted to OpenCode; `Collision.QUALIFIED_NAMESPACE` restricted to documented namespace rules (Claude `dir:cmd`, OMP).
   - Restored `__all__` and load-bearing comments in `skill_lens/core/resolver.py`.

9. **I. OpenCode Local Inputs, Bounded Disclosure & Agent Selection**:
   - Attached `OPENCODE_BOUNDED_DISCLOSURE_NOTE` disclosing omitted system/managed locations, system skills, existing-session selections, agent policies, and declaring the base `build` agent assumption.
   - Detected non-default `default_agent` (e.g. `"plan"`), marking permission confidence as `UNKNOWN` with explanatory notes while explicit `deny` rules retain precedence as `DISABLED`.
   - Maintained detection for unsupported V1 `permission` and local skills arrays.

10. **J. Privacy Secret Redaction & Maintainability Cleanliness**:
    - Redacted arbitrary raw configuration values (effects, agent keys, patterns, relative path values) from error/unsupported strings and diagnostics in `skill_lens/core/config.py`.
    - Preserved containing config file paths for diagnostic utility without token leakage.
    - Removed dead helpers, fixed typed doctor signature, and resolved formatting/cleanliness items across core modules.

---

## 6. Confirmed Final Boundaries & Verification Receipts

### Final A through J Disposition Map

| Item | Problem / Finding | Operative Disposition & Implementation |
| :--- | :--- | :--- |
| **A** | Codex symlink parent and alias normalization divergence | Symmetrically normalized config paths during live acquisition and session capture; zero-probe lexical snapshot resolution. |
| **B** | Caller-facing `disabled_overrides` API and Claude command identity | Preserved explicit caller candidate alias/path intersections; separated captured normalized controls from caller-facing explicit overrides; settings overrides apply to declared command name. |
| **C** | Doctor frontmatter vs. description discrimination | Separated `ParseStatus.MALFORMED_YAML` with `missing_frontmatter` from missing description; doctor reports portability warnings without claiming false runtime skips. |
| **D** | Retained compatibility roots vendor loadability | Classified unverified compatibility roots (`qoder_project_agents`, `grok_bundled`, `grok_project`, `windsurf_project_agents`, `antigravity_global`, `antigravity_project_agents`) as `loadability = "unknown"`; resolution marks loadability `UNKNOWN` with explanatory notes. |
| **E** | OpenCode invocation policy and permission denial reason | Missing description precludes model advertisement even with `autoinvoke: true` (`user_only`); `metadata.opencode/autoinvoke` outranks `disable-model-invocation` when description exists; distinct deny reason `"Denied by OpenCode skill permission"`. |
| **F** | OpenCode config search extent | Searches all directory ancestors up to filesystem/sandbox boundary; applies layer ordering: direct project configs farthest->closest, then hidden `.opencode` directory configs farthest->closest. |
| **G** | Bounded discovery depth limit disclosure | OpenCode (depth 32), Pi (depth 16), and standard recursive roots (depth 4) inspect exact-limit leaf skills before pruning descendants; pruned subdirectories record `depth_limit_truncated` in `unreadable_roots`; resolution reports disclose directory truncation in `notes`, eliminating false unqualified absence without synthetic warnings for fully inspected leaves. |
| **H** | Nested copy coexistence and rule precision | Restored base nested copy coexistence for non-OpenCode profiles; restricted ancestor specificity tie-breaking to OpenCode; preserved documented namespace rules (`dir:cmd`, OMP). |
| **I** | OpenCode bounded disclosure and agent selection | Added `OPENCODE_BOUNDED_DISCLOSURE_NOTE` disclosing unmodelled system/managed sources; non-default `default_agent` marks permission confidence as `UNKNOWN`. |
| **J** | Privacy diagnostic redaction and code cleanliness | Redacted raw secret config values from error/unsupported strings; removed dead helpers; clean type signatures. |
| **Boundary A** | Cyclic symlink in [[skills.config]] path (`cycle-a -> cycle-b -> cycle-a`) | Contained path normalization failure under `(OSError, RuntimeError)`; preserves lexical path matching without fabricated canonical paths or crash; diagnoses uncertainty truthfully. |
| **Boundary B** | Report-time filesystem probes during truncated snapshot navigation | Precomputed `ur.display_path` at discovery time; pure lexical collapse fallback in `resolver.py` without calling `paths.display`, `paths.home`, or `Path.resolve`; snapshot navigation executes under full prohibited-boundary filesystem guards. |

### Verification Receipts: Worker vs. Coordinator

- **Coordinator Independent Baseline Gates (post-Round-1):**
  - Pytest: 916 passed, 1 skipped (case-insensitive filesystem test)
  - Coverage: **91.10%** (required >= 90.0%)
  - Mypy: 36 source files clean (exit 0)
  - Ruff Check: clean (0 errors)
  - Ruff Format: 130 files already formatted (exit 0)
  - Receipt: `/var/folders/tf/jsdyxcts6y72fs98s7wl3dfm0000gn/T/skill-lens-stage-d-20261015-jr3bm9wg/coordinator-final/gates.json` (coordinator commands and logs; the implementation terminal report is worker evidence).

- **Prior boundary correction: implementer-reported gates (before the exact-depth fix):**
  - Format Check: `.venv/bin/ruff format --check .` (exit 0, 130 files formatted)
  - Linter Check: `.venv/bin/ruff check .` (exit 0, all checks passed)
  - Type Check: `.venv/bin/mypy` (exit 0, 36 source files clean)
  - Test Suite & Coverage: `.venv/bin/pytest --cov=skill_lens` (worker-reported exit 0, 919 passed, 1 skipped, 90.69% combined coverage; this is above the 90.0% threshold).
  - Mutation Proofs: Clean / Mutant / Restored proofs for all guards recorded in `/var/folders/tf/jsdyxcts6y72fs98s7wl3dfm0000gn/T/skill-lens-stage-d-20261015-jr3bm9wg/gemini-correction/proofs.json`.

- **Coordinator verification after the exact-depth fix, 15 October 2026:**
  - 922 tests passed, one case-insensitive-filesystem skip, **90.50% combined coverage** with branch measurement (threshold 90.0%). Strict mypy is clean on 36 files; Ruff lint and format checks are clean (130 files).
  - Thirteen actual production mutations in a verified disposable source copy failed their targeted tests and passed before and after restoration. Receipt includes source hashes, mutation diffs, import provenance, commands, and logs; this is not an exhaustive mutation score.
  - Current receipt and logs: `/var/folders/tf/jsdyxcts6y72fs98s7wl3dfm0000gn/T/skill-lens-stage-d-20261015-jr3bm9wg/coordinator-council-r2-final/`. These are coordinator evidence; all verification used synthetic HOME/XDG and protected system-root fixtures.
  - The coordinator read the allowed tracked/untracked source, test, registry and output changes. Golden/snapshot changes reflect the selected V2 support, optional Claude description, documented Pi/Qoder priority, and newly searched Claude compatibility roots. No output was regenerated by the coordinator.
  - `git diff --check` reports two trailing spaces on wrapped Rich snapshot lines. These are pinned rendering output, not unreviewed source edits; no blind trimming was performed. Remaining non-blocking cleanup includes duplicate frontmatter predicates, unused helper parameters and defensive handling of `canonical=None` in a synthetic custom-snapshot test.
  - **Safe stop at the owner's request: coordinator review complete; council round two NOT dispatched; Stage D remains unaccepted and uncommitted.** Fresh resume must compare fingerprints and collect both independent reviews before acceptance.
