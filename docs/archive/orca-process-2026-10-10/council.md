# The Critic Council

**What this is.** The council is the set of *other* AI agents the coordinator asks to
check a plan or a change. They read and report. They never edit the project.

- A **critic** (also called a reviewer) is an agent given read-only access to check
  somebody else's work.
- The **coordinator** is Sol/Hermes, the agent that plans, dispatches, checks and
  accepts. It never writes product code.
- The **implementer** is Antigravity, the agent that writes code and tests.

Read this file together with `profiles/project-profile.md` (what "correct" means here)
and `profiles/machine-profile.md` (which agents exist on this machine).

---

## 1. The roster

The roster that matters in practice is small: **Hermes coordinates, Antigravity
implements, OpenCode and MCode review.** Cline and Pi are installed but not in use —
adding a critic is the user's decision.

| Critic | Model | Model family | Installed |
|---|---|---|---|
| Antigravity | Gemini 3.8 Flash High | Google | yes (`agy`) |
| Cline | `cline-free/mimo-v2.6-flash`, thinking `xhigh` | Xiaomi / MiMo | yes |
| OpenCode | Space Bunny Max, fallback Muse 1.3 Free Max | Space Bunny / Muse | yes |
| MCode | Minimax M3.1F | minimax | yes — **not native to Orca**, see §5 |
| Pi | chosen at dispatch | varies | yes |
| Hermes | `gpt-6.1-sol-900k` | OpenAI | yes — **this is the coordinator** |

### What each critic is for

- **Antigravity — feasibility.** It is also our implementer, but in `--mode plan` it
  answers a different question: *can this actually be built, and what breaks if we do?*
  Its verdicts are the only ones that carry a `FEASIBILITY:` line.
- **Cline — the strict reader.** Different family, deliberately hostile by default: it
  has to agree before it may touch anything.
- **OpenCode — the second pair of eyes.** A cheap second opinion on structure and
  naming.
- **MCode — a third family** that has never seen this project's history.
- **Pi — the wildcard.** Whatever it is at dispatch time; record which one.

Do not give every critic the same question. Give each one a **different** review
question (project rules vs behaviour vs test gaps), or you get five copies of the
same opinion.

### Why the coordinator is not on this list

Two reasons, both hard:

1. **It cannot be.** Sol/Hermes is the top-level coordinator of the run. Dispatched as
   a worker it hits Orca's `nested_worker_depth_exceeded` and cannot spawn a council
   at all. Sol coordinates; it never works.
2. **It would not be independent.** A critic on the same model as the coordinator is
   the same mind reviewing itself. Model diversity is not a guarantee of independence,
   but sharing a model is a guarantee of *not* getting it.

**Rule: if a critic turns out to be running the coordinator's model, the review is
void.** Stop the run, fix the agent's own config, restart.

---

## 2. Read-only, per critic

Read-only means read-only. **No critic can be made read-only by a flag on
`worker-start`** — that command has no agent-argument forwarding at all. Verified
against Orca 1.4.221.

`worker-start` accepts exactly these flags:

```text
--help --json --pairing-code --environment --task --spec --task-title --deps --parent
--on --worktree --name --repo --base-branch --display-name --comment --setup --agent
--model --effort --terminal --retry-of --timeout-ms --run --from --retry-request
```

So `--mode plan` and `--plan --auto-approve false` **cannot be passed here** — Orca
would reject them as unknown flags. To get a CLI's own read-only mode you must launch
that CLI yourself in a terminal and attach the worker with `--terminal` (§5).

| Critic | How read-only is actually achieved | Roster status |
|---|---|---|
| Antigravity | launch `agy --mode plan` yourself in a terminal, attach with `--terminal` | **in use — implementer + feasibility critic** |
| OpenCode | the guard text below, then check files afterwards | **in use — critic** |
| MCode | the guard text below, then check files afterwards | **in use — critic** |
| Cline | would need `--plan --auto-approve false` via the terminal route | **not in the current roster** |
| Pi / OMP | guard text only; no CLI read-only flag | **not in the current roster** |

**Pi's `-p` does NOT make it read-only.** It is *print mode* and still has every write
tool. Never describe it as read-only.

**The roster is explicit.** Per the C2 and C3 plans: *"do not silently add Cline, MCode,
Pi or a different OpenCode model."* Adding a critic is a user decision, not a default.

### The guard text — copy this into every critic task

The CLI enforces nothing for most agents, so the instruction has to be in the task, not
in your head. Paste this block verbatim into the `--spec` of every critic dispatch:

```text
READ-ONLY CRITIC TASK. You are reviewing, not implementing.

Do NOT create, edit, move, delete or rename any file in the repository. Do NOT run
any command that writes: no formatters, no linters with --fix, no install, no
git commit/checkout/stash, no snapshot or golden regeneration, no test runs that
write into the checkout. Test output, if you need it, goes only to a temporary
directory outside the repository.

If you believe a change is required, do not make it. Report it instead.

Return only the report format below. Nothing else.
```

### After every critic dispatch, check

```bash
cd "/Users/corvette/Documents/Projects Coding/Skill Lens"
git status --porcelain        # must be identical before and after the dispatch
```

A critic that edited files is not a disaster — it is a broken brief or a missing flag.
Verify **which** files, `git restore` them, then fix the brief or the flags before
retrying. A copy of the project does not protect the rest of your machine; checking
afterwards detects the edit, it does not prevent it.

---

## 3. Report format — critic

Every critic returns exactly these fields. A missing field is an incomplete report.

```text
VERDICT:       pass | changes_required | unverified
FEASIBILITY:   sound | risky | infeasible      (Antigravity only)
BLOCKERS:      [ location, problem, expected behaviour, evidence ]
SUGGESTIONS:   [ ... ]        non-blocking
FILES_AT_RISK: [ ... ]
CONCEDED:      [ ... ]        points withdrawn after argument
```

Rules for the fields:

- **Every blocker needs four things**: where it is (`path:line`), what is wrong, what
  should happen instead, and a real example or failing test. A blocker missing the
  evidence is a suggestion.
- **Anything you did not confirm stays a concern**, labelled as one. Do not promote a
  hunch to a blocker because it sounds right.
- **`unverified`** is an honest verdict. It means you could not check. It is more
  useful than a confident `pass`.

---

## 4. Report format — implementer

Antigravity (and any future implementer) returns:

```text
OUTCOME:               succeeded | failed
FILES_CHANGED:         [ ... ]
CHECKS:                pytest= mypy= ruff-check= ruff-format=
TESTS_ADDED:           [ ... ]
DEVIATIONS_FROM_PLAN:  [ ... ]   empty, or each explained
BLOCKED_ON:            [ ... ]
```

The coordinator verifies the report against the actual files and actual check results.
**Do not trust a report. Read the files, and run the gates yourself.**

---

## 5. Launch routes — verified

Two different routes. Pick by critic.

### Route A — native `--agent` launch

Antigravity and OpenCode both launch natively:

```bash
orca orchestration worker-start --task <task_id> --worktree current --agent antigravity --json
orca orchestration worker-start --task <task_id> --worktree current --agent opencode --json
```

`--agent` takes an Orca agent id — `claude, codex, cursor, antigravity, muse, zcode,
opencode, opencode2` are documented examples, and the list is **not exhaustive**. Do not
assume an id works; try it and read the error.

### Route B — terminal you launch, then attach

Use this when a critic needs its own CLI flags, because `worker-start` cannot carry
them. This is how Antigravity gets `--mode plan`:

```bash
orca terminal create --worktree current --title "agy-critic" --command "agy --mode plan" --json
orca orchestration worker-start --task <task_id> --terminal <handle> --worktree current --json
```

The `--command` text is typed into the terminal, so the agent's own read-only flag
finally reaches it. Verified on Orca 1.4.221 — this is the route the C2 plan used.

### MCode — Route B fails, use Route C

Recorded on 2026-10-07: **`worker-start --terminal` on MCode's terminal is rejected as
`agent_unconfigured`.** The working low-level route:

```bash
orca orchestration task-create --spec "<critic task, including the guard text>" --json
orca orchestration dispatch --task <task_id> --to <handle> --return-preamble --json
orca terminal send --terminal <handle> --text "<exact returned preamble>" --enter --json
```

Note `dispatch` runs **without** `--inject`, and the preamble Orca returns is sent
literally into the verified-idle terminal.

**MCode's lane is unsupervised.** Orca owns no terminal resource for it, and `release`
returns `retained / no_owned_resource / processAction none`. Never claim supervised
cleanup for MCode. The Task/Dispatch pair and `worker_done` remain authoritative.

`--model` is not portable either: it is accepted for Claude, Codex, Cursor, Antigravity
and Muse ids; **OMP takes `--model` but not `--effort`**; everything else (OpenCode,
ZCode, …) launches on whatever its own config says.

---

## 6. How many critics

Do not run five agents on a typo fix.

| Change type | Planning review | Implementation review |
|---|---|---|
| Obvious, low impact | none — the coordinator plans alone | the four gates + coordinator's own reading |
| Normal feature or bug fix | 1 independent critic | 1 independent critic |
| **High risk** | **2 critics, different families** | **2 critics, different families** |

**High risk** = touching path resolution, public data formats, registry TOML,
permissions, exit codes, compatibility, or anything `AGENTS.md` §4 flags as
load-bearing. On Skill Lens this is often true.

Expand review when the evidence warrants it, never by standing habit.

**As actually practised:** C2 and C3 each ran **two critics from different model
families** — OpenCode `space-bunny-free` (Space Bunny/Muse) and MCode
`minimax/MiniMax-M3.1-Flash-Preview` (minimax), with Antigravity
`gemini-3.8-flash-high` (Google) as feasibility reviewer and implementer, and Hermes
`gpt-6.1-sol-900k` (OpenAI) coordinating — a fourth family. No five-agent council has
been run, and none is needed for this risk profile.

---

## 7. Before you trust any of this

- **Record the effective model in every report.** `--model` is only honoured for Claude,
  Codex, Cursor, Antigravity and Muse provider ids; **OMP takes `--model` but not
  `--effort`**; everything else — OpenCode, ZCode and the rest — launches on whatever
  its own config says. Never claim a model from the dispatch arguments; read back what
  the agent actually used, from its own banner or session metadata. A council quietly
  running the wrong model has destroyed the point of having a council.
- **Read current config and command help, not these files, when they disagree.**
- Machines change. An agent roster written down last month is a guess.