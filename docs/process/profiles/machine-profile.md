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

- **Last confirmed:** version **1.4.221**, runtime `connected`.
- If `orca status` says not running, run `orca open --json` and retry once.
- If it still fails, **report the exact error**. Do not go hunting for another
  executable or another tool.
- If you get `orca: command not found`, the symlink is missing — redo §1.

`orca status --json` is also the cheapest way to confirm the runtime version matches
what these documents assume. If Orca was upgraded, re-verify §2 and §3 before trusting
them.

---

## 2. The agent roster

Orca knows 44 agents; 10 are installed here. Six are used by the loops.

| Critic | Model | Family | Installed |
|---|---|---|---|
| Antigravity | Gemini 3.8 Flash High | Google | yes (`agy`) |
| Cline | `cline-free/mimo-v2.6-flash`, thinking `xhigh` | Xiaomi / MiMo | yes |
| OpenCode | Space Bunny Max, fallback Muse 1.3 Free Max | Space Bunny / Muse | yes |
| MCode | Minimax M3.1F | minimax | yes — **not native to Orca** |
| Pi | chosen at dispatch | varies | yes |
| Hermes | `gpt-6.1-sol-900k` | OpenAI | yes — **the coordinator** |

Other installed CLIs: the `*-delegate` skills in this workspace wrap these same
binaries (`agy`, `cline`, `opencode`, `mcode`, `pi`) and are a different, simpler
route. The loops in `../planning-loop.md` and `../implementation-loop.md` use Orca
directly, because Orca gives task ownership, completion tracking and worker cleanup.

---

## 3. Read-only flags, per critic

Each CLI enforces read-only differently. See `../council.md` §2 for the guard text that
covers the three agents that have no enforcing flag.

| Critic | Enforcing flags | Notes |
|---|---|---|
| Antigravity | `--mode plan` | native launch works |
| Cline | `--plan --auto-approve false` | **both are required.** `auto-approve` defaults to **true**. |
| OpenCode | *(none)* | guard text + `git status` check afterwards |
| MCode | *(none)* | guard text + `git status` check afterwards |
| Pi | *(none)* | guard text + `git status` check afterwards |

**Pi's `-p` is not read-only.** It is print mode with full write tools. Never describe
it otherwise.

Cline's config already sets `planActMode: "plan"` as a second safety layer.

**Flag placement has changed between Orca versions.** Confirm with
`orca orchestration worker-start --help` before the first dispatch of a session.

---

## 4. Which agent is on which model

**Most agents read their own config, not Orca's arguments.**

- **Antigravity** — the only agent that takes `--model` from Orca.
- **Cline, OpenCode, Pi** — read their own CLI config. Changing Orca's argument changes
  nothing for them.
- **MCode** — whatever its own config says.

**Therefore: record the effective model in every report.** Read it back from the agent
or its output. Never infer it from the dispatch command. A council that silently ran
the wrong model has no review value at all — if you discover this happened, the review
is void: stop, fix that agent's own config, restart.

Keep the coordinator and the critics in **different model families on purpose.**

---

## 5. MCode: the escape hatch

MCode is installed but Orca cannot start it with `--agent mcode`. Make a terminal by
hand, then attach the worker:

```bash
orca terminal create --worktree active --title "mcode-critic" --command "mcode" --json
orca orchestration worker-start --task <task_id> --terminal <handle> --worktree active --json
```

Every other critic launches natively:

```bash
orca orchestration worker-start --task <task_id> --worktree current --agent antigravity --json
orca orchestration worker-start --task <task_id> --worktree current --agent cline --json
orca orchestration worker-start --task <task_id> --worktree current --agent opencode --json
orca orchestration worker-start --task <task_id> --worktree current --agent pi --json
```

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
| `orca status` reports not running | app closed | `orca open --json`, retry, report the exact error |
| Cline exits 137, no output | the shim was skipped | `zsh -l -c 'command -v cline'` (§6) |
| `nested_worker_depth_exceeded` | Sol was dispatched as a worker | Sol is the coordinator; it never works (§8) |
| A critic edited files | missing flag or weak brief | verify which files, `git restore`, fix the brief or flags |
| A critic ran the wrong model | the agent read its own config | stop the run; the review is void |
| A worker never reports | usually nothing | see the waiting rules in `../planning-loop.md` §5 |

---

## 8. Sol is never a worker

Sol/Hermes runs as the **top-level coordinator** of the whole run. Dispatched as a
worker, Orca's nested-depth limit stops it from spawning a council at all
(`nested_worker_depth_exceeded`).

Sol plans, dispatches, checks and judges. It does not type product code.

---

## 9. When to distrust this file

- Orca was upgraded or reinstalled
- an agent CLI was upgraded globally (`npm i -g`, `brew upgrade`)
- a model name here disagrees with what an agent reports
- a flag in §3 is rejected by the CLI

In all four cases: read the current config and `--help`, fix this file, and note that
you did.