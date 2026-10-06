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

Ten agents are installed here; Orca knows 44. Six matter to us.

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

Read-only means read-only. Each CLI spells it differently, and **each critic has a
different flag** — this is the single most common way a council fails.

| Critic | What actually blocks writes |
|---|---|
| Antigravity | launch flag `--mode plan` |
| Cline | launch flags `--plan --auto-approve false` ← **both. `auto-approve` defaults to true.** |
| OpenCode | the guard text in §3, then check files afterwards |
| MCode | the guard text in §3, then check files afterwards |
| Pi | the guard text in §3, then check files afterwards |

**Pi's `-p` does NOT make it read-only.** It is *print mode* and still has every write
tool. Never describe it as read-only.

Cline's own config already has `planActMode: "plan"`, which is a second safety layer
behind the two flags above.

### The guard text — copy this into every critic task

Five flags are enforced by the CLI. The rest are enforced only by instruction, so the
instruction has to be in the task, not in your head. Paste this block verbatim into
the `--spec` of every critic dispatch:

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

## 5. The one escape hatch: MCode

MCode is installed but Orca cannot launch it natively with `--agent mcode`. Create a
terminal by hand and attach the worker to it:

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

Add `--mode plan` for Antigravity and `--plan --auto-approve false` for Cline. Flag
*placement* has changed between Orca versions — confirm with
`orca orchestration worker-start --help` at dispatch time rather than trusting this
file. See `profiles/machine-profile.md`.

---

## 6. How many critics

Do not run five agents on a typo fix.

| Change type | Planning review | Implementation review |
|---|---|---|
| Obvious, low impact | none — the coordinator plans alone | the four gates + coordinator's own reading |
| Normal feature or bug fix | 1 independent critic | 1 independent critic |
| **High risk** | **full council: Antigravity, Cline, OpenCode, MCode, Pi** | **2 critics, from different families** |

**High risk** = touching path resolution, public data formats, registry TOML,
permissions, exit codes, compatibility, or anything `AGENTS.md` §4 flags as
load-bearing. On Skill Lens this is often true.

Expand review when the evidence warrants it, never by standing habit.

---

## 7. Before you trust any of this

- **Record the effective model in every report.** Only Antigravity takes `--model` from
  Orca; Cline, OpenCode and Pi read their own config. Never claim a model from the
  dispatch arguments — read back what the agent actually used. A council quietly
  running the wrong model has destroyed the point of having a council.
- **Read current config and command help, not these files, when they disagree.**
- Machines change. An agent roster written down last month is a guess.