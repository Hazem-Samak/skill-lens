# BB Surface — native threads, environments, and workflows

Read the installed **`bb-council` skill** (`~/.bb/skills/bb-council/SKILL.md` on this
Mac) for worker mechanics. This adapter records project-specific boundaries and
installed-version corrections; it does not replace the skill. [Council](./council.md)
owns roster, roles, guard, report schemas, risk, and acceptance. Follow the shared
[planning](./planning-loop.md) and [implementation](./implementation-loop.md) steps
using BB mechanics, not T3 APIs.

## 1. Inspect the actual installation

Inside a BB thread, prefer its `BB_CLI` executable when bare `bb` resolves wrongly.
`BB_PROJECT_ID`, `BB_THREAD_ID`, and `BB_ENVIRONMENT_ID` identify inherited context;
verify with `bb status`. Outside BB, resolve the intended project, environment,
and parent explicitly rather than inventing those IDs.

```bash
bb guide
bb guide threads
bb guide thread-inspection
bb guide thread-messaging
bb guide thread-lifecycle
bb guide providers
bb guide environments
bb guide commands thread
```

Checked 2026-11-03: `/Applications/bb.app` bundles **0.48.1**. Bare `bb` was absent
from this session's PATH, but the app and bundled CLI were present. Its bundled
CLI help/guides ran with the app's Electron Node runtime and
`app.asar/node_modules/bb-app/dist/bb.js`; the default BB server was not running.
This proves command contracts, not a successful live worker dispatch.

The [official PATH guidance](https://github.com/get-bb/bb/blob/main/docs/configuration.md#the-bb-command-on-path)
explains the app's launcher and optional Settings → General → Command line install.
Missing PATH does not mean missing BB. Do not install a command, start/restart the
app/server, enable plugins, or change configuration merely to hide a failed check.
Use an already available launcher, or report the needed human step. A deliberate
external connection uses the intended `BB_SERVER_URL`; do not probe unrelated hosts.

## 2. Explicit roster and checkout

```bash
bb provider list --json
bb provider models <provider-id> --environment <environment-id> --project <project-id> --json
bb environment show <environment-id> --json
```

Catalogs can be cached; a valid model label is not proof of authenticated execution.
Ask once for missing user selections. Supply provider, model, reasoning, service
tier/options, and authorized permission mode explicitly; BB's defaults select
nothing for a Skill Lens mission.

Prepare `brief_file` outside the checkout with the exact council guard + critic
schema (or implementer schema), scope, frozen plan/draft revision, evidence, no
further delegation, and return instructions. Then launch with the selected values:

```bash
bb thread spawn --project "$BB_PROJECT_ID" --environment "$BB_ENVIRONMENT_ID" \
  --parent-self --visibility hidden --parent-notifications auto \
  --provider "$provider" --model "$model" --reasoning-level "$effort" \
  --permission-mode "$permission_mode" --title "$role_title" \
  --prompt-file "$brief_file" --json
```

The variables above must be resolved first; outside a BB parent thread replace
`--parent-self` with the verified `--parent-thread <id>`, or omit parenting for an
explicitly independent thread. Add only the user's supported `--service-tier` and
repeatable `--option <id>=<value>` selections. Full permission is instruction-based
reviewer restraint, not a read-only sandbox. T3's Full access authorization is not
a new BB permission grant; retain the already authorized BB mode from the skill
and mission. Inspect any approval before acting.

**Environment correction to the installed skill:** explicitly select the inspected
`--environment` for reviewers of uncommitted work. Omitting environment flags can
create a fresh managed worktree; omission does **not** reliably share the parent's
checkout. For deliberate isolation, use `--new-environment worktree` and an exact
base ref, then verify provisioning and binding. The installed guide's branch
selection can prefer a remote ref; `refs/heads/<branch>` forces the local branch.
Fresh worktrees do not automatically contain the parent's uncommitted changes.

`--plan` is a provider-declared plan action, not a universal read-only mode. A
provider without that action rejects it. Use `bb provider models`/`bb thread
commands`/`bb thread options` to distinguish provider session options from the plan
action; do not assume `--option mode=plan` and `--plan` are interchangeable.

## 3. Dispatch a wave, wait, steer, and verify

Launch every independent critic before waiting. Retain each returned **`id`**,
parent/environment/machine, explicit settings, and launch time. A fresh critic
round uses a new `thread spawn`, not a fork inheriting the implementer's history.
Capture Git status and scoped SHA-256 fingerprints before/after each review wave.

```bash
bb thread wait <id> --status idle --timeout 20m --json
bb thread show <id> --json
bb thread output <id> --json
bb thread log <id> --all --json
bb thread list --include-hidden --parent-thread <parent-id> --json
```

`idle` alone is not acceptance: inspect activity, queued/background work,
interactions, and the actual complete report. Parent notifications report turn
outcomes/blockers, not a guaranteed accepted result. A wait timeout does not cancel.
Read BB's JSON error envelope (`ok:false`) even when output parses as JSON.
Spawn has no documented `clientRequestId`; after a lost reply inspect known IDs,
parent-linked threads, and environment state before retrying to avoid duplicates.

Use files/stdin for messages; double-quoted inline shell text expands backticks and
`$(...)` before BB sees it:

```bash
bb thread tell <id> --message-file <path> --mode auto --json
bb thread interactions list <id> --json
bb thread interactions show <interaction-id> <id> --json
```

`auto` steers a running turn or starts an idle one; `queue` defers a non-urgent
follow-up. Inspect `delivery`, `queuedMessage`, and `waitingOn`; an interaction-held
message is queued, not lost, so do not resend it. Match the user's specific answer
to the native `approve`, `deny`, `grant`, `answer`, or `respond` interaction type.
No blanket approval to keep a wave unattended. A stopped/interrupted provider
session is not a review verdict; inspect its actual lifecycle/result.

## 4. Visibility, persistent terminals, and optional workflows

- `bb thread open <id> --split right` displays an existing worker thread; it does
  not require spawning a second worker. Use only when visibility is requested.
  `bb thread pane` controls an already-open pane. Keep hidden critics hidden.
- `bb terminal` owns persistent PTYs for long-running commands. Read `bb guide
  terminals` and `bb terminal --help`; explicitly target the intended thread,
  environment, or machine and retain the terminal ID. A thread is not a PTY.
- The **Workflows plugin** adds durable fan-out, dependencies, structured output,
  stop/resume, and history. Check `bb plugin list` and `bb workflows --help` before
  using the skill's `wave.js`. Validate with the installed plugin's own command
  before running; record run/worker IDs and inspect complete results. Missing
  plugin/server/context is a prerequisite, not permission to enable it or fall
  back to arbitrary JavaScript. `bb guide commands` is core discovery; plugin
  help/skills own plugin commands. Use ordinary native threads for a single wave
  unless durable execution or schema validation is actually needed.

## 5. Accept without losing the environment

Use the shared two-commit freeze, baseline, final checks, and risk-required reviews
(Low 0 / Normal 1 / High 2). Implementers run relevant checks; the coordinator runs
all four gates on the final tree, including after rework: `pytest --cov=skill_lens`
(coverage at least 90%), `mypy`, `ruff check .`, `ruff format --check .`.

After reading accepted reports, `bb thread stop <id>` releases a worker runtime;
confirm it settled with `thread show`. Stop does not cascade to ordinary child
threads, so account for every owned worker. Do not delete evidence or assume a
stop removed the thread/environment.

**Archive is not harmless cleanup:** archiving the last live thread of a managed
worktree starts retirement and can remove uncommitted files and stop processes
using that worktree. Preserve/integrate accepted work and check all environment
users before archiving/deleting. Inspect `bb environment show` until intended
cleanup settles. Never archive unrelated/user-owned work to make the sidebar tidy.

## Sources

- [Official BB source and entry points](https://github.com/get-bb/bb).
- [Official CLI/guide ownership](https://github.com/get-bb/bb/blob/main/docs/cli-guide-and-skill.md): installed `bb guide` chapters are the core manual; plugin skills own plugin APIs.
- [Official worktree lifecycle](https://github.com/get-bb/bb/blob/main/docs/worktrees.md).
- Installed `bb-council` is project mechanics, not upstream API evidence. Compare it with the installed 0.48.1 help; the environment/plan-action corrections above take precedence over stale examples.
