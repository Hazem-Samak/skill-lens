# OMP workers through Herdr

Use this dispatch adapter when Sol/OMP runs natively in Tern and the user requests Herdr workers. Keep the [OMP roles, review guard and acceptance rules](./README.md), [planning loop](./planning-loop.md) and [implementation loop](./implementation-loop.md); Herdr hosts and controls implementation/review workers, not Sol's display or the development policy. T3 stays separate. Hermes is not required.

**Live status:** external dispatch documented/unverified; end-to-end acceptance is unsatisfied. Two earlier inside-Herdr trials ran: Mini missed busy detection, and full-TUI `prompt --wait` returned about 6.91 seconds before actual completion. Both failures remain unresolved in the [historical evidence](../../validation/omp-coordinator/2026-10-20/herdr-dispatch.md). Moving Sol to Tern fixes neither; standalone relay or document-review results are not Herdr lifecycle proof.

## 1. Verify the external connection

Sol stays native in Tern. Retain the coordinator model/settings check in [Start directly](./README.md#start-directly): `openai-codex/gpt-6.1-sol`, with authorized settings; no silent fallback.

**Approved authority:** the user-authorized [external-control amendment](../../plans/2026-10-22-omp-herdr-external-control.md) @ `988d3917890ddf56b48b950afa2c162dd84c8c4e` and this adapter govern this repo's external OMP route. Read the installed `herdr` skill, but its inside-Herdr/`HERDR_ENV` location gate and caller-relative defaults do not apply to this route. Keep all non-conflicting safety rules. This narrow exception does not override system/runtime restrictions, widen approvals, authorize installed-skill/settings edits, or change other projects. If the runtime prohibits the approved connection, stop and report it.

Discover installed syntax and existing sessions without launching or attaching Herdr:

```bash
herdr --help
herdr agent
herdr pane
herdr session list --json
```

1. Select an existing named server/session in the task's authorized context; explicitly record `default` if it is the selected default session. Missing authorization, multiple plausible targets or ambiguous identity means stop and ask for the exact target. A lone running session is not permission to use its panes.
2. Require its discovery entry to report running and expose `socket_path`. Verify that path is a Unix-domain socket, not merely a file, then query that existing session's server status. The commands below are **templates**, not ready-to-run commands; substitute verified values:

   ```text
   test -S "<discovered-socket-path>"
   herdr --session <verified-existing-session> status server --json
   ```

   Require a responding compatible server and match its reported socket/session to discovery. Herdr 0.9.5 reports the default session as `session:null`; normalize that only when the selected discovery row has `name:"default"`, `default:true`, and the identical socket. Arbitrary missing identity is not default. Missing, stale, inaccessible, incompatible or inconsistent identity/socket stops dispatch.
3. Record the selected session, socket, server version/protocol and compatibility inside the ledger's existing evidence/receipt entries; no new ledger fields. Keep the same explicit `--session <verified-existing-session>` prefix for every later session-scoped discovery, pane and agent command. The CLI resolves that verified session's socket; do not invent socket flags, override socket environment variables, fall back to another machine/session, or follow UI focus.
4. If identity/socket changes or connection fails, re-establish this gate before more work. Inspect the original target before retrying an uncertain mutation. Root `--session` can use **or create** a session: discovery must establish an existing running entry first. Do not create/attach a session, start/repair/upgrade a service, manufacture `HERDR_ENV`/pane context, or reuse historical IDs.

Discover live panes only after the gate passes. All pane and agent operations use explicit pane IDs parsed from that selected server's responses, never sidebar order, `--current`, inherited `HERDR_PANE_ID`, omitted/focused targets or agent-name substitutes. Unique worker names are ledger labels. If a required operation cannot target a pane ID, stop and report it. Unavailable agent kind or model/settings mismatch also stops dispatch.

## 2. Start the selected worker

Use Herdr for reviewer **and** implementer dispatch in this mode, rather than invisible native tasks or standalone CLI relays. Reuse the session's authorized kind/provider/model/settings; verify supported kinds using `herdr agent` and native arguments using the selected runtime's installed help. Herdr kind is the CLI integration, not the model. No guessed OpenCode/MiniMax startup arguments and no unapproved model substitution.

Choose an explicitly authorized existing shell/base pane within the selected workspace/tab, in the same checkout/cwd. Native Tern is not a Herdr pane. If the base pane or placement is ambiguous, ask before touching a user's pane. Inspect that pane's foreground shell, prompt, cwd and layout using explicit IDs:

```text
herdr --session <verified-existing-session> pane process-info --pane <authorized-base-pane-id>
herdr --session <verified-existing-session> pane layout --pane <authorized-base-pane-id>
```

Default to one sibling in the selected tab, preserving user focus. Choose right for a wide base pane or down for a narrow/tall one. Wide-case template:

```text
herdr --session <verified-existing-session> pane split --pane <authorized-base-pane-id> --direction right --cwd <verified-checkout-cwd> --no-focus
```

Read the new ID from `.result.pane.pane_id`, record ownership, and verify an available foreground shell at its prompt. Choose a unique live worker name. Startup and task templates:

```text
herdr --session <verified-existing-session> agent start <unique-worker-name> --kind <supported-kind> --pane <returned-pane-id> --timeout 30000 -- <verified-native-model-and-agent-arguments>
herdr --session <verified-existing-session> agent prompt <returned-pane-id> "<guarded task and unique request token>" --wait --timeout 120000
herdr --session <verified-existing-session> agent get <returned-pane-id>
herdr --session <verified-existing-session> agent read <returned-pane-id> --source recent-unwrapped --lines 120
```

Every wait must have an explicit positive finite `--timeout` in milliseconds, including startup readiness, prompt `--wait`, standalone `agent wait`, `pane wait-output` and any other installed wait command used. The sample durations are bounded examples, subject to each command's installed help and any documented limits; do not invent undocumented maxima, wait indefinitely or increase timeouts to disguise the known defects. Additional wait templates:

```text
herdr --session <verified-existing-session> agent wait <returned-pane-id> --timeout 120000
herdr --session <verified-existing-session> pane wait-output <returned-pane-id> --match "<request-specific-output>" --timeout 120000
```

`agent start` uses an existing pane; it does not create layout. Require actual readiness before prompting. Verify the worker's configured provider/model/settings match authorization and reviewers use their supported review/plan mode plus the exact OMP read-only guard. Do not guess equivalent permission flags. Keep prompts within the installed terminal/runtime's input limits; a rejected long submission is not permission to switch transports silently.

Before parallel starts, assign disjoint paths or approved separate checkouts and one integration owner; dispatch all independent reviewers before collecting results. Do not create new workspaces/tabs or choose a different cwd/checkout unless authorized. Children remain edit-only or read-only by role and skip all gates/formatters; Sol verifies.

## 3. Read, verify, and finish

Keep the name, returned pane IDs, request token, allowed paths, model/settings evidence, reports and timestamps in the task ledger. A successful prompt submission, settled `idle`/`done` state or terminal badge is not acceptance and may describe another turn. Require the matching complete report and actual owned turn/background-work completion, with no active child work; inspect files and run the coordinator checks required by the loops.

On timeout, `agent_prompt_stalled`, `blocked`, `unknown`, connection loss or other uncertain delivery, inspect the same worker with `agent get` and `agent read`, using its explicit pane ID and verified session, before any retry. Do not blindly resend or launch a duplicate. A wait timeout does not cancel work or prove non-delivery. If an approval/question is shown, ask the human rather than answer it automatically. Antigravity/Grok may look idle while background tasks remain active; obtain real completion evidence. A rejected `recent-unwrapped` read such as `agent_not_idle` is incomplete readback, not completion, resend authority or permission to bypass readiness.

If a completed report is missing, first request more recent-unwrapped output. Only if that still cannot recover it, ask the same worker to save the report outside the repository and return its path. Read that file on the same machine; do not initially require file output merely to work around scrollback.

Preserve the coordinator, unrelated panes and user work. Clean up only owned workers/panes after completion and any unsaved work is preserved, using installed help for the correct termination/close commands, explicit pane IDs and the same verified session prefix. Never stop the Herdr server, close the session or kill unrelated processes. After pane moves, use the returned new pane ID, not a stale ID or a name-based substitute.

## Live check requires separate authorization

Documentation implementation does **not** authorize a live smoke. The [2026-10-20 smoke plan](../../plans/2026-10-20-omp-herdr-dispatch.md) retains its history; its dated external-control note supersedes the inside-Herdr setup, including historical human-startup guidance in the evidence record.

Only after the user separately authorizes a smoke, start OMP natively in Tern at this repository using the [Sol launch command](./README.md#start-directly). Follow the amended smoke setup: verify the authorized existing session/socket, select an explicitly authorized base pane, create one owned worker pane and use its returned ID throughout. Submit one harmless read-only unique-token task to the session-selected supported reviewer, with bounded waits; inspect the matching report, actual turn/background completion, preservation and owned cleanup. No historical IDs, product writes, installs, detection/wait repairs, Mini rerun, model substitution, sleeps or weaker acceptance.

Preserve the original completion/wait-correctness criteria: a report recovered after premature waiter return does not make the wait pass. Until separately authorized evidence meets every criterion, report **external Herdr dispatch documented/unverified; established lifecycle failures unresolved**, not end-to-end support verified. A reviewer-only task cannot establish implementation-worker capability or general support.
