# Machine Profile — this Mac

Environment and provider facts for T3 Code on this computer. [council.md](../council.md) owns role, model-selection, permission, review, and task-lifecycle rules; the loop documents own the sequence of work.

Live discovery wins over this snapshot: use `orchestrator_capabilities` for installed providers/models/options and `t3_thread_configuration` for active model/options/modes.

## 1. T3 Code Orchestrator

Observed build: `0.0.46-nightly.20261010.2935`. Recheck after upgrades.

The active workflow uses native T3 orchestration. The [Orca process archive](../../archive/orca-process-2026-10-10/README.md) preserves earlier repository instructions; it does not imply the external Orca app was removed. The [dated migration plan](../../plans/2026-10-10-t3-orchestrator-v2-migration.md) retains session history and its accepted exceptions.

## 2. Models and Providers

**This profile binds no role to any model.** The user names the roster for each mission ([council §1](../council.md#1-the-roster-and-roles)). What follows is only what this machine can run.

Provider IDs observed in this build: `codex`, `antigravity`, `pi`, `grok`, `opencode`. This is a capability snapshot, not a suggestion. Use `orchestrator_capabilities` for what is selectable now; installed models change between upgrades.

Effort or option values from any past session — a coordinator override, a reviewer maximum, or a named model in a dated receipt — are historical evidence only. Nothing from a previous mission is a default for the next one.

For actual execution evidence use [council §4](../council.md#4-report-formats): distinguish requested, configured, and provider-confirmed/unverified values. Catalog defaults do not prove what a task ran.

## 3. Permission Modes and Preflight

Follow [council §2](../council.md#2-read-only-protection-and-permissions) before dispatch: Hazem's standing preference is Full access for coordinator and workers; critics retain the exact report-only guard, fingerprint detection, and automatic-review limits.

Observed narrower-parent rejection:

```text
runtime_mode_escalation_denied / Child runtime mode full-access is broader than parent mode auto
```

Composer selection applies on the subsequent turn. If activation is needed, reuse existing authorization, then verify active mode by `t3_thread_configuration` readback. Plan mode and worktrees do not enforce file-write prevention.

## 4. Provider Policy and Source Mapping Evidence

These are static observations from build `0.0.46-nightly.20261010.2935`, not adversarial security proof. Re-derive bundle mappings after upgrades; enforced adversarial write prevention remains unverified.

- **OpenCode:** Supervised (`approval-required`) maps reads to `allow` and edits/bash to `ask`. Always-allowed tools: `question`, `read`, `glob`, `grep`, `lsp`, `todowrite`, `task`, `skill`. Restricted: `bash`, `edit`, `webfetch`, `websearch`, `codesearch`, `external_directory`, `doom_loop`.
- **Codex:** Supervised maps untrusted approvals with a `readOnly` sandbox.
- **Pi:** `PI_T3_MCP_EXTENSION_SOURCE` shows deferred-tool/`tool_search` discovery and native allowance for `read`, `grep`, `find`, `ls`; other tools can prompt even in Auto.
- **Grok:** `grokAcpSpawnArgs` maps Supervised to `[--permission-mode, default, agent, stdio]`, Auto to `[--permission-mode, auto, agent, stdio]`, and Full access to `[agent, --always-approve, stdio]`.

Pi/Grok source for that build: `/Applications/T3 Code (Nightly).app/Contents/Resources/app.asar!/apps/server/dist/binCli-DBAO6Yxt.mjs`. The former temporary inspection receipt is not retained or authoritative.

## 5. Workspace and Worktree Handling

The migration observed root checkout `main`, `worktreePath: null`; this is history, not a permanent binding. Inspect the caller with `t3_worktree_status`. Inspect child branch/worktree metadata with `t3_thread_read`. Respect existing bindings; a clean root needs no new worktree. Delegated children share the caller's checkout.

If the calling thread needs isolation:

1. Inspect caller status and the project setup script before `t3_worktree_handoff`. Handoff moves the caller; an already-attached thread cannot handoff.
2. Pass explicit `branch`, `baseRef`, and `startFromOrigin`: false for local parent commits, true when fetching/starting from origin. Uncommitted edits are not copied.
3. Pass `runSetupScript: true` explicitly. The observed tool description says setup runs by default; its schema field does not declare a default.
4. Include `continuationPrompt` and make handoff the last tool action of the turn. After resumption, check setup and continuation outcomes; stop/report either failure.

For a user-requested separate top-level conversation, use `t3_thread_launch` with explicit `workspaceStrategy` (`root`, `worktree`, or `existing_worktree`). Omission chooses project root, not caller binding. It has no idempotency key: retain `threadId`, inspect preparation via `t3_thread_read`/`t3_thread_wait`, and check `t3_thread_list` before retrying a lost response. `create_threads` is only for an explicitly requested batch sharing the caller's checkout; it has no workspace override. A prompt's `cd` or `git worktree add` does not change T3 binding.

Worktrees survive thread deletion. Follow council §3 cleanup: remove only owned, unused worktrees after checking bindings and uncommitted user edits.
