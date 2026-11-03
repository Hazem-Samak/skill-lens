# Machine Profile — T3 Code on this Mac

This is the **T3 adapter**, not a model roster. [Council policy](../council.md) and the
[shared loops](../planning-loop.md) own roles and acceptance. For other hosts use
[BB](../bb.md), [Rex](../rex.md), or [Herdr](../herdr.md).

## 1. T3 Code Orchestrator

Checked **2026-11-03** against the installed `/Applications/T3 Code (Nightly).app`:

- Version: `0.1.7-nightly.20261102.4080`; packaged source commit `47f2c8d29e98`.
- Evidence: `Contents/Resources/app.asar:package.json` and the bundled server MCP
  definitions. Archive member notation here means a file inside `app.asar`.
- `apps/server/dist/server-IjwUrgAx.mjs` defines `t3_thread_configure` and
  `t3_thread_launch`; `ManagedEndpointRuntime-DBOrUhfY.mjs` contains the delegation
  contracts. Hashed chunk names change on upgrades; rediscover them, do not assume
  an old filename still exists.

Live tool schemas and readback win over this snapshot. Recheck after upgrades.
A source inspection proves the API contract, not a successful live delegation.

## 2. Models and Providers

Call `orchestrator_capabilities` before the first dispatch; discover the user's
provider instance, exact model ID, and supported options there. Repeat after a
relevant catalog error or provider change. A built-in provider driver is not
proof that a configured instance is authenticated or available.

The user names every role's provider/model/effort for the mission. No catalog
default, old roster, template, or remembered project selection chooses it for them.
Record requested, configured, and provider-confirmed/unverified identity separately.

For configured evidence, call **`t3_thread_configure` without `modelSelection`**:

```json
{}
```

This reads the current thread. For a local child, pass the delegation receipt's
`childThreadId` as the tool's `threadId`. For a remote child, use the receipt's
`remoteChild.threadId` and `remoteChild.environmentId`; its local `childThreadId`
can be null. The result includes `modelSelection`, `runtimeMode`, and
`interactionMode`. Supplying `modelSelection` changes settings; a readback must omit it.

## 3. Permission Modes and Preflight

The existing T3 Full access authorization is in [council §2](../council.md#2-read-only-protection-and-permissions).
Verify the caller's active mode before dispatch. `runtimeMode` supports
`approval-required`, `auto-accept-edits`, `auto`, and `full-access`;
`interactionMode` supports `default` and `plan`. Requested child modes cannot
exceed the caller's permitted modes.

If the caller is too narrow, have the user activate the authorized mode in the
composer, then verify readback on the next turn. Do not change permissions through
an unrelated tool or silently substitute another mode.

Plan mode, role labels, and worktrees are not enforced read-only boundaries.
Critics retain the exact guard, report schema, and before/after fingerprints.
`hasPendingQuestion` and `pendingApproval` are different: answer questions through
`t3_pending_request`; permission approval belongs to the user/native app controls.

## 4. Provider Policy and Source Mapping Evidence

Use the [official permission guide](https://github.com/pingdotgg/t3code/blob/47f2c8d29e98/docs/user/permission-modes.md)
for provider-specific limits. Full access is not a promise that every provider
suppresses every approval or safety rejection; Auto also differs by provider.
The old 2026-10-10 bundle mappings are not current security evidence.

For an operational claim, prefer the current tool schema, then configured
readback, then the provider's actual banner or result. Record missing execution
or adversarial write-prevention evidence as unverified. Never infer served model
identity or family diversity from catalog labels alone.

## 5. Workspace and Worktree Handling

Inspect the caller with `t3_worktree_status`; inspect child branch/worktree metadata
with `t3_thread_read`. A clean root needs no new worktree. Preserve existing bindings
and user edits; shell `cd` and `git worktree add` do not bind a T3 thread.

Choose the right native operation:

| Need | Native operation | Important boundary |
|---|---|---|
| Delegate on the inspected checkout | `delegate_task` with `isolation:"shared"` | Default; includes current uncommitted files. Use for review of an uncommitted diff. |
| Give a child its own checkout | `delegate_task` with `isolation:"worktree"` | Prepared from the parent commit; uncommitted edits stay out. Record the returned branch/path and setup outcome. |
| Move this coordinator into a worktree | `t3_worktree_handoff` | Ends this live session; `continuationPrompt` resumes next turn. |
| User-requested new top-level conversation | `t3_thread_launch` | Explicit `workspaceStrategy`; not a substitute for delegation. |

For caller handoff, inspect status and the setup script first. Pass explicit
`branch`, `baseRef`, `startFromOrigin` (`false` for local parent commits), and
`runSetupScript:true`. Include `continuationPrompt` and call handoff last in the
turn. It fails if the caller already has a worktree. Verify setup and continuation
after resumption; preserve a failure instead of claiming success.

For `t3_thread_launch`, `workspaceStrategy` is an **object**, for example:

```json
{"type":"root"}
```

```json
{"type":"worktree","baseRef":"<local-parent-ref>","startFromOrigin":false}
```

```json
{"type":"existing_worktree","worktreePath":"<absolute-project-worktree-path>"}
```

Omission selects the project root, not the caller's worktree. Supply a stable
`clientRequestId`; after an error or lost reply, retry the same call with the same
ID, not a new key. Retain `threadId` and inspect with `t3_thread_read` or
`t3_thread_wait`. `create_threads` is a user-requested top-level batch inheriting
the caller's checkout; it has no per-thread workspace override.

Worktrees survive thread deletion. Remove only owned, unused worktrees after
checking bindings, setup outcomes, and uncommitted user work. Apply or merge a
child's accepted work deliberately; a child finishing is not integration.

## Sources and capability discovery

- [Official source at the installed commit](https://github.com/pingdotgg/t3code/tree/47f2c8d29e98).
- [Delegation schemas](https://github.com/pingdotgg/t3code/blob/47f2c8d29e98/packages/contracts/src/orchestratorMcp.ts): targets, isolation, task receipts, questions, and cancellation.
- [Worktree handoff contract](https://github.com/pingdotgg/t3code/blob/47f2c8d29e98/packages/contracts/src/worktreeMcp.ts).
- [Outside agents and host CLI](https://github.com/pingdotgg/t3code/blob/47f2c8d29e98/docs/user/outside-agents.md): external MCP access needs user-approved authentication. Do not configure it as a fallback without authorization.
- Native linked-environment tools (`t3_environment_links`, and user-authorized `t3_environment_link`) support another machine. Preserve returned environment IDs, query its catalog, and pass `target.environmentId` for a remote delegate; local provider availability does not prove remote availability.
