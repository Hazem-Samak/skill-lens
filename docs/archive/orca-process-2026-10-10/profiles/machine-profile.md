# Machine Profile — this Mac

**What this is.** Everything about *this* computer: where Orca lives, which agents are
installed, which flags actually block writes, which model each one really uses.

**This file goes stale.** Machines get reinstalled, agents get upgraded, flags move.
**When this file and the live command help disagree, the live command help wins.**
Check `orca <command> --help` and the agent's own config rather than trusting anything
written here.

Nothing in this file belongs in `AGENTS.md` or in the project specification. Live paths,
installed binaries and model names are machine facts, not project rules.

---

## 1. The Orca executable

```
/Applications/Orca.app/Contents/Resources/bin/orca
```

Not on `PATH`. Create the symlink once per session, before anything else:

```bash
ln -sf /Applications/Orca.app/Contents/Resources/bin/orca ~/.local/bin/orca
```

Then confirm it resolves and the app is actually up:

```bash
~/.local/bin/orca open --json && ~/.local/bin/orca status --json
```

Expect `app.running: true` and `runtime.reachable: true`.

- **Last confirmed:** version **1.4.221**, runtime `connected`. The read-only flags, launch
  routes and model rules in §2–§5 were re-verified against this version's live
  `agent-context` schema on **2026-10-07**, after the C2 and C3 runs.
- If `orca status` says not running, run `orca open --json` and retry once.
- If it still fails, **report the exact error**. Do not go hunting for another
  executable or another tool.
- If you get `orca: command not found`, the symlink is missing — redo §1.

`orca status --json` is also the cheapest way to confirm the runtime version matches
what these documents assume. If Orca was upgraded, re-verify §2 and §3 before trusting
them.

---

## 2. The agent roster

**As actually used** — this is what the C2 and C3 plans ran, with models read back from
each agent's own banner and session metadata:

| Role | Agent | Verified model | Family | Launch |
|---|---|---|---|---|
| **Coordinator** | Hermes | `gpt-6.1-sol-900k` | OpenAI | runs **inside an Orca terminal** |
| Implementer + feasibility critic | Antigravity (`agy`) | `gemini-3.8-flash-high` | Google | native `--agent` |
| Critic | OpenCode | `opencode/space-bunny-free`, variant `max` | Space Bunny / Muse | native `--agent` |
| Critic | MCode | `minimax/MiniMax-M3.1-Flash-Preview`, effort `xhigh` | minimax | Route C only |

Also installed, **not in the current roster** — do not add them without the user asking:

| Agent | Note |
|---|---|
| Cline | Would need `--plan --auto-approve false` via the terminal route |
| Pi / OMP | No read-only flag; OMP takes `--model` but not `--effort` |

Four different families across coordinator, implementer and two critics — that is the
point. A critic on the coordinator's model is not an independent check.

Other installed CLIs: the `*-delegate` skills wrap these same binaries and are a
different, simpler route. The loops use Orca directly, because Orca gives task
ownership, completion tracking and worker cleanup.

---

## 3. Read-only flags, per critic

**Verified on Orca 1.4.221: `worker-start` has no agent-argument forwarding.** These
flags cannot be passed to it and will be rejected:

```text
--mode plan                     # Antigravity
--plan --auto-approve false     # Cline
```

To deliver an agent's own read-only flag, launch its CLI in a terminal yourself and
attach with `--terminal` — see `../council.md` §5.

| Critic | Enforcing flags | How to reach it |
|---|---|---|
| Antigravity | `--mode plan` | `orca terminal create --command "agy --mode plan"`, then `worker-start --terminal` |
| Cline | `--plan --auto-approve false` | same terminal route (**both** required; `auto-approve` defaults to **true**) |
| OpenCode | *(none)* | guard text + `git status` afterwards |
| MCode | *(none)* | guard text + `git status` afterwards |
| Pi / OMP | *(none)* | guard text + `git status` afterwards |

**Pi's `-p` is not read-only.** It is print mode with full write tools. Never describe
it otherwise.

Cline's config already sets `planActMode: "plan"` as a second safety layer.

**Flag placement has changed between Orca versions.** Confirm with
`orca orchestration worker-start --help` before the first dispatch of a session.

---

## 4. Which agent is on which model

**Most agents read their own config, not Orca's arguments.**

- **`--model` is honoured only for** Claude, Codex, Cursor, Antigravity and Muse
  provider model ids. **OMP takes `--model` but not `--effort`.**
- **Everything else — OpenCode, ZCode, MCode and the rest** — launches on whatever its
  own config says. Changing an Orca argument changes nothing for them.

**Therefore: record the effective model in every report.** Read it back from the agent's
own banner or session metadata, as the C2/C3 plans did. Never infer it from the dispatch
command. A council that silently ran the wrong model has no review value at all — if you
discover this happened, the review is void: stop, fix that agent's own config, restart.

Keep the coordinator and the critics in **different model families on purpose.**

---

## 5. Launch routes

### Antigravity and OpenCode — native

```bash
orca orchestration worker-start --task <task_id> --worktree current --agent antigravity --json
orca orchestration worker-start --task <task_id> --worktree current --agent opencode --json
```

### Antigravity in plan mode — terminal you launch, then attach

```bash
orca terminal create --worktree current --title "agy-critic" --command "agy --mode plan" --json
orca orchestration worker-start --task <task_id> --terminal <handle> --worktree current --json
```

`--command` is typed into the terminal, so `agy --mode plan` finally reaches agy.
This is what the C2 plan used. Note `terminal create` is the right call for a fresh
agent in the current checkout — not `worktree create`.

### MCode — Route C, because Route B is rejected

`worker-start --terminal` against MCode's terminal fails with **`agent_unconfigured`**
(observed 2026-10-07). The working low-level route:

```bash
orca orchestration task-create --spec "<critic task, including the guard text>" --json
orca orchestration dispatch --task <task_id> --to <handle> --return-preamble --json
orca terminal send --terminal <handle> --text "<exact returned preamble>" --enter --json
```

`dispatch` runs **without** `--inject`; you send the returned preamble literally into
the verified-idle terminal.

**This lane is unsupervised.** Orca owns no terminal resource for it, and `release`
returns `retained / no_owned_resource / processAction none`. Never claim supervised
cleanup for MCode. The Task/Dispatch pair and `worker_done` stay authoritative.

Note on readiness: `worker-start` **exits 0 only when the worker is ready**. `failed` or
`outcome_unknown` exits 1, with `stage`/`failedStage`, `setup`, `effects`,
`residualResources` and recovery commands in the JSON.

---

## 6. Cline's repair wrapper — a known trap

Cline runs only through `~/.local/shims/cline`, which repairs an invalid macOS code
signature on Cline's Bun binary. **Skip the wrapper and Cline dies with exit 137 and no
output at all.**

Check it before relying on Cline:

```bash
zsh -l -c 'command -v cline'    # must print /Users/corvette/.local/shims/cline
```

**Re-check after any `npm install -g cline@latest`** — the global install is what
breaks the signature, so the shim must be reinstalled or repaired afterwards.

Confirmed working on this machine as of the last check.

---

## 7. Other known traps

| Symptom | Cause | Do this |
|---|---|---|
| `orca: command not found` | symlink missing | `ln -sf ... ~/.local/bin/orca` (§1) |
| `Could not read Orca runtime metadata` | app closed or quit | `orca open --json`, retry, report the exact error |
| `no_active_sender_terminal` | the command ran **outside** an Orca terminal | see §7a — the coordinator must run inside Orca |
| `agent_unconfigured` | `worker-start --terminal` used against MCode | use Route C (§5) |
| `unknown flag: --mode` / `--plan` | agent flags passed to `worker-start` | those flags do not exist there; use the terminal route (§3, §5) |
| Cline exits 137, no output | the shim was skipped | `zsh -l -c 'command -v cline'` (§6) |
| `nested_worker_depth_exceeded` | Hermes was dispatched as a worker | Hermes is the coordinator; it never works (§8) |
| A critic edited files | missing flag or weak brief | verify which files, `git restore`, fix the brief or flags |
| A critic ran the wrong model | the agent read its own config | stop the run; the review is void |
| A worker never reports | usually nothing | see the waiting rules in `../planning-loop.md` |
| Live terminals vanished between sessions | Orca restarted | Orca had quit; `terminal list` returns 0. Worker terminals do not survive a restart — treat any pre-restart worker handle as lost, and re-dispatch rather than polling a dead handle |

---

## 7a. The coordinator must run inside an Orca terminal

**Verified 2026-10-07.** Run `orca orchestration run-current` from an ordinary shell
whose working directory is the project, and Orca answers:

```text
no_active_sender_terminal — Could not determine the sender terminal for this
orchestration command. Pass --from with your own terminal's handle — another pane's
handle would act on its mailbox — or run the command inside a live Orca terminal
with ORCA_TERMINAL_HANDLE set.
```

So Orca identifies the calling agent by the **`ORCA_TERMINAL_HANDLE`** environment
variable, which exists only inside an Orca-managed terminal. Confirmed: that variable
is unset in a normal shell.

`run-list` shows the same thing from the other side — each Run records a
`coordinator_handle` that is an Orca terminal id (`term_…`).

What this means in practice:

| From an external shell | Works? |
|---|---|
| `status`, `agent-context`, `run-list`, `worker-list`, `terminal list` | yes — global reads |
| `run-current`, `check`, `task-create`, `worker-start`, any mailbox command | **no** — `no_active_sender_terminal` |

The `--from` escape hatch exists but it makes the caller act **as another terminal's
mailbox** — Orca's own message says so. That is impersonation, not integration. Do not
use it to fake a coordinator.

**Therefore: the coordinator runs in a terminal inside the Orca app.** A desktop
coordinator app that is not an Orca terminal cannot drive the loops.

---

## 8. Hermes is never a worker

Hermes (`gpt-6.1-sol-900k`, OpenAI) runs as the **top-level coordinator** of the whole
run, inside an Orca terminal (§7a). Dispatched as a worker, Orca's nested-depth limit
stops it from spawning a council at all (`nested_worker_depth_exceeded`).

Hermes plans, dispatches, checks and judges. It does not type product code.

Confirmed in use: the C3 plan names Hermes as the coordinating agent.

---

## 9. When to distrust this file

- Orca was upgraded or reinstalled
- an agent CLI was upgraded globally (`npm i -g`, `brew upgrade`)
- a model name here disagrees with what an agent reports
- a flag in §3 is rejected by the CLI

In all four cases: read the current config and `--help`, fix this file, and note that
you did.