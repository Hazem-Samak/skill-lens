# Machine Profile — this Mac

**What this is.** Environment facts and provider capabilities on this computer: live T3 Code orchestration, model configurations, permission modes, and workspace behavior.

**This file records live machine facts.** When this file and live discovery disagree, **the live catalog wins.** Run `orchestrator_capabilities` and inspect `t3_thread_configuration` rather than relying on stale text.

---

## 1. T3 Code Orchestrator

T3 Code provides the product-native collaborative orchestration environment on this Mac.

- **Observed point-in-time build:** `0.0.46-nightly.20261010.2935`.
- **Live authority:** The live catalog (`orchestrator_capabilities`) is the authority for installed providers and active models.
- **Archived legacy workflow:** The Orca-based workflow was archived on 2026-10-10 under `docs/archive/orca-process-2026-10-10/`. This records repository process history and does not imply the external Orca application was uninstalled or decommissioned beyond the scope of this repository's documentation. Active workflows operate natively in T3 Code without assuming an Orca workflow fallback.

---

## 2. Models and Providers

| Role | Provider / Agent | Configured Model | Family | Dispatch Policy |
|---|---|---|---|---|
| **Coordinator** | `codex` | `gpt-6.1-sol` (default reasoning `high`) | OpenAI | **Fixed coordinator.** Never writes product code. (Replaces historical `gpt-6.1-sol-900k`). |
| **Implementer** | `antigravity` | `gemini-3.8-flash-high` | Google | **Sole implementer.** Never reviews or commits. |
| **Critic Pool** | `pi`, `grok`, `opencode` | Chosen per session | Varies | **USER selects models AND settings per session** from live catalog. Coordinator asks once if missing. |
| **Deferred** | MCode | MiniMax M3.1 Flash | MiniMax | Future ACP integration only; not native in T3. |

### Session model evidence vs defaults

- **Coordinator default:** Use `reasoningEffort=high`. The migration session used `xhigh` as a session override; its historical receipts remain unchanged.
- **USER selection:** Critic models AND settings (options) are selected by the user per session from the live catalog. If choices are missing, the coordinator presents an ask-once menu showing live options with recommended risk-sized choices. Authorized choices are reused across rounds within the session.
- **Model family diversity and evidence:** Distinguish role and context independence (separate prompt, separate subagent turn) from verified family diversity. Avoid categorical claims that same-family models cannot provide independent context. High-risk reviews strictly require verified distinct model families when established. Sharing coordinator or implementer family does not satisfy the requirement. Different providers do not automatically prove different model families (unknown family identity stays unverified).
- **Unverified family operational path:** If a selected model family cannot be verified, disclose which identity is unverified and obtain explicit user acceptance of the named pair for that session before proceeding. Never claim verified family diversity when unverified.
- **Session evidence (2026-10-10 migration):**
  - OpenCode ran `opencode/space-bunny-free` with `variant=max`.
  - Pi ran `tokenharbor/deepseek-v4.1-flash:free` with `thinking=max` (authorized fallback after Grok hit usage limits).
  - Because Space Bunny's upstream model family could not be verified, this session operated under an explicit user-accepted exception ("Keep the selected pair and record the unverified family") rather than verified family diversity. This is an explicit session-specific accepted exception, not a permanent default or blanket future waiver. USER model and settings choice per session remains mandatory.
- **Not permanent defaults:** Reviewer models are selected per session from the live catalog. Reuse selected choices within the session; do not ask repeatedly.
- **No silent substitution:** If a model becomes unavailable or exhausts quota, ask the user once or use an authorized fallback. Never silently switch models.
- **Evidence channels:** Always pass explicit `providerInstanceId`, `model`, and options in `delegate_task`. Distinguish requested vs configured vs provider-confirmed/unverified:
  - Task receipts and `task_status` show target provider/model.
  - `t3_thread_configuration` readback shows configured options and modes.
  - Provider banner/session output corroborates effective use when available (otherwise unverified).
  - Catalog `currentValue` reflects live catalog configuration, NOT task execution evidence.

---

## 3. Permission Modes and Preflight

### Operational standing preference

Hazem explicitly authorized **Full access (`runtimeMode=full-access`)** for both planning and implementation loops to eliminate routine approval prompts. This standing preference is reused until changed.

### Caller-mode preflight

T3 Code prevents privilege escalation:
- If a child task is dispatched with a broader runtime mode than its parent (for example, child `full-access` when parent is `auto`), T3 Code rejects the dispatch with:
  ```text
  runtime_mode_escalation_denied / Child runtime mode full-access is broader than parent mode auto
  ```
- **Preflight rule:** The coordinator must verify its own active mode via `t3_thread_configuration` before dispatching children.
- **Narrow parent remedy:** Do not dispatch a broader child or silently downgrade child permissions (silent lowering is forbidden). Reuse existing Full access authorization without repeatedly asking for already approved choices. If the coordinator is not in Full access, request that the user switch to Full access in the composer to activate the authorized mode, and verify active mode via `t3_thread_configuration` readback on the subsequent turn. If the surface cannot operate in the authorized mode, report the actual needed human step.
- **Composer readback:** Selecting Full access in the composer applies to the subsequent turn; readback via `t3_thread_configuration` is required to verify the active turn configuration.

### Protection realities under Full access

- **Writes permitted at provider level:** Full access removes provider permission prompts. Reviewer restraint is instruction-based (the verbatim guard).
- **Plan mode is interaction guidance:** `interactionMode=plan` guides turn structure; it does not block file edits.
- **Worktrees are not security boundaries:** Worktrees share user permissions and filesystem access.
- **Fingerprint verification:** The coordinator takes SHA-256 fingerprints before and after reviewer runs to detect edits. Never claim hard enforced read-only reviews under Full access.
- **Automatic approval review:** Full access does not disable automatic approval review. If an action is rejected by automatic review, narrow the action or report the limitation.
- **Supervised mode contrast:** In Supervised mode (`runtimeMode=approval-required`), provider actions trigger prompts. MCP question tools cannot approve permissions; native app controls must be used if available.

---

## 4. Provider Policy and Source Mapping Evidence

Inspected provider policies show different static mappings:

- **OpenCode:** In Supervised mode (`approval-required`), maps reads to `allow` and edits/bash to `ask`. Constant always-allowed tools: `question`, `read`, `glob`, `grep`, `lsp`, `todowrite`, `task`, `skill`. Restricted tools: `bash`, `edit`, `webfetch`, `websearch`, `codesearch`, `external_directory`, `doom_loop`.
- **Codex:** In Supervised mode, maps untrusted user approvals with a `readOnly` sandbox.
- **Pi:** Inspected source symbol `PI_T3_MCP_EXTENSION_SOURCE` in installed bundle `/Applications/T3 Code (Nightly).app/Contents/Resources/app.asar!/apps/server/dist/binCli-DBAO6Yxt.mjs` for build `0.0.46-nightly.20261010.2935` reveals deferred-tool/`tool_search` discovery and native allowance for `read`, `grep`, `find`, `ls`. (A temporary inspection receipt `installed-policy-2.txt` outside the repository is not retained and not authoritative). Other tools map to prompts even in Auto.
- **Grok:** Inspected installed source symbol `grokAcpSpawnArgs` in `/Applications/T3 Code (Nightly).app/Contents/Resources/app.asar!/apps/server/dist/binCli-DBAO6Yxt.mjs` for build `0.0.46-nightly.20261010.2935` proves:
  - `approval-required` (Supervised) uses `[--permission-mode, default, agent, stdio]`
  - `auto` uses `[--permission-mode, auto, agent, stdio]`
  - `full-access` uses `[agent, --always-approve, stdio]`

*Evidence qualification:* These are static policy mappings and observed ordinary read behaviors from build `0.0.46-nightly.20261010.2935`. Both Pi and Grok bundle chunk mappings (`binCli-DBAO6Yxt.mjs`) are build-specific and must be re-derived after T3 upgrades per the live-catalog-wins rule. These static code observations are not live adversarial security proofs. Hard adversarial write prevention remains unverified.

---

## 5. Workspace and Worktree Handling

- **Current checkout binding:** The current coordinator thread is bound to the project root on `main` (`worktreePath: null`). Respect existing caller binding; do not assume every clean checkout is project root. A clean root checkout requires no worktree creation.
- **Worktree handoff procedure:** If an isolated worktree is required:
  1. Inspect `t3_worktree_status` AND inspect the project setup script BEFORE calling handoff.
  2. Note that an already-attached thread cannot handoff (`t3_worktree_handoff` moves the calling thread, not another thread, and cannot move a thread already attached to a worktree).
  3. Call `t3_worktree_handoff` with explicit `branch`, `baseRef`, `startFromOrigin: false` (to base on local commits) or `true` (from origin), explicitly pass `runSetupScript: true` (the live `t3_worktree_handoff` tool description notes it runs the setup script by default, though no default is declared in the schema field; pass the argument explicitly), and provide `continuationPrompt` as the last tool action of the turn.
  4. Inspect setup and continuation outcomes upon resumption. If setup or continuation fails, stop and report that outcome instead of treating failure as skipped.
- **Worktree persistence and cleanup:** Worktrees survive thread deletion. Record ownership, and clean up only owned, unused worktrees after checking bindings and absence of uncommitted user edits.
- **Top-level threads:** Use `t3_thread_launch` only when the user explicitly requests a separate top-level conversation. State `t3_thread_launch` must have explicit `workspaceStrategy` on user-requested top-level work; omission chooses project root, not caller worktree. `t3_thread_launch` has no idempotency key; inspect `t3_thread_list` before retrying lost responses. `create_threads` inherits the caller's checkout with no workspace override. No unrequested top-level launch.
