# OMP workers through Herdr

Use this dispatch adapter when Sol/OMP runs inside Herdr. Keep the [OMP roles, review guard and acceptance rules](./README.md), [planning loop](./planning-loop.md) and [implementation loop](./implementation-loop.md); Herdr manages worker terminals, not the development policy. T3 stays separate. Hermes is not required.

**Live status:** instructions prepared; OMP-to-Herdr worker dispatch has not yet been exercised. The authoring session was outside Herdr. The standalone OpenCode relay proof is not Herdr proof.

## 1. Establish the real caller

Before any Herdr inspection/control, check inherited context:

```bash
test "${HERDR_ENV:-}" = 1
```

If this fails, stop Herdr operations and ask the human to launch OMP in a genuine Herdr shell pane. Never manufacture context with `export HERDR_ENV=1`, select the user's focused session from outside, or treat an ordinary terminal as a managed pane. Standalone OMP may use its existing routes; it must not silently substitute them for a requested Herdr run.

Inside Herdr, load the installed `herdr` skill, then discover actual syntax and live capability:

```bash
herdr --help
herdr agent
herdr pane
herdr status
herdr pane current --current
herdr agent list
herdr pane layout --pane "$HERDR_PANE_ID"
```

Record inherited workspace/tab/pane context and the actual caller resolved by `--current`. IDs are opaque; parse responses, never derive IDs from examples or sidebar order. Confirm the coordinator remains `openai-codex/gpt-6.1-sol`, with authorized settings. Missing/ambiguous caller identity, unavailable agent kind or incompatible server stops dispatch; do not repair, upgrade or start a service automatically.

## 2. Start the selected worker

Use Herdr for reviewer **and** implementer dispatch in this mode, rather than invisible native tasks or standalone CLI relays. Reuse the session's authorized kind/provider/model/settings; verify supported kinds using `herdr agent` and native arguments using the selected runtime's installed help. Herdr kind is the CLI integration, not the model. No guessed OpenCode/MiniMax startup arguments and no unapproved model substitution.

Default to one sibling pane in the current tab, same checkout/cwd, preserving user focus. From caller geometry choose right for a wide pane or down for a narrow/tall pane. Example for the wide case:

```bash
herdr pane split --current --direction right --cwd "$PWD" --no-focus
```

Read the new ID from `.result.pane.pane_id`; verify the new pane is an available foreground shell at its prompt. Choose a unique live agent name. The following are **templates**, not ready-to-run commands; replace each angle-bracket value with discovered/authorized values:

```text
herdr agent start <unique-worker-name> --kind <supported-kind> --pane <returned-pane-id> -- <verified-native-model-and-agent-arguments>
herdr agent prompt <unique-worker-name> "<guarded task and unique request token>" --wait --timeout 120000
herdr agent get <unique-worker-name>
herdr agent read <unique-worker-name> --source recent-unwrapped --lines 120
```

`agent start` uses an existing pane; it does not create layout. Require actual readiness before prompting. Verify the worker's configured provider/model/settings match authorization and reviewers use their supported review/plan mode plus the exact OMP read-only guard. Do not guess equivalent permission flags. Keep prompts within the installed terminal/runtime's input limits; a rejected long submission is not permission to switch transports silently.

Before parallel starts, assign disjoint paths or approved separate checkouts and one integration owner; dispatch all independent reviewers before collecting results. Do not create new workspaces/tabs or choose a different cwd/checkout unless authorized. Children remain edit-only or read-only by role and skip all gates/formatters; Sol verifies.

## 3. Read, verify, and finish

Keep the name, returned pane IDs, request token, allowed paths, model/settings evidence, reports and timestamps in the task ledger. A successful prompt submission, settled `idle`/`done` state or terminal badge is not acceptance and may describe another turn. Require the matching complete report and actual owned turn/background-work completion, with no active child work; inspect files and run the coordinator checks required by the loops.

On timeout, `agent_prompt_stalled`, `blocked`, or `unknown`, inspect the same worker with `agent get` and `agent read` before any retry. Do not blindly resend. A wait timeout does not cancel work. If an approval/question is shown, ask the human rather than answer it automatically. Antigravity/Grok may look idle while background tasks remain active; obtain real completion evidence.

If a completed report is missing, first request more recent-unwrapped output. Only if that still cannot recover it, ask the same worker to save the report outside the repository and return its path. Read that file on the same machine; do not initially require file output merely to work around scrollback.

Preserve the coordinator, unrelated panes and user work. Clean up only owned workers/panes after completion and any unsaved work is preserved, using installed help for the correct termination/close commands. Never stop the Herdr server, close the session or kill unrelated processes. After pane moves, use the returned new pane ID or live agent name, not a stale ID.

## Live check still required

In a real Herdr shell pane at this repository, start OMP using the [existing Sol launch command](./README.md#start-directly). Ask Sol:

> Continue the authorized Herdr smoke from docs/plans/2026-10-20-omp-herdr-dispatch.md. Read docs/process/omp/herdr.md. Verify inherited caller context and installed support, then use one owned sibling pane for the selected OpenCode MiniMax reviewer. Submit a harmless read-only unique-token task, inspect the matching report and actual completion, preserve unrelated panes, and append evidence to docs/validation/omp-coordinator/2026-10-20/herdr-dispatch.md. Do not change product files, install anything, repair detection, substitute models or claim success if unsupported.

Until that succeeds, report **Herdr dispatch documented; live verification blocked**, not end-to-end support verified.
