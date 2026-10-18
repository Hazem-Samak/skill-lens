# One Herdr planning and implementation cycle

State: prepared under the frozen plan; start only from T3's delivered human instructions.
Surface: herdr (T3 prepares and later reads evidence).
Authority: `docs/plans/2026-10-18-herdr-single-cycle-trial.md`
@ `ad19c3115f518b8f10d1ab2ef23c04254196886b` (frozen operative contract).
Provenance-only reference commit: `1aab76b5d5e4af90c37ebf23d3341e7588ac9c27`.
An unresolved reference prohibits use.
This is a separate practical trial. Old P01 remains unverified; P02-P09 are paused.

## Boundaries and task

You are Sol/Hermes, coordinator. Use native Herdr for all trial child work.
Original repository (read-only): `/Users/corvette/Documents/Projects Coding/Skill Lens`.
Trial root:
`/private/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts/simple-loop-trial-dkn9ufiu`.
Checkout: `TRIAL_ROOT/checkout`; evidence: `TRIAL_ROOT/evidence`.
Replace TRIAL_ROOT with the literal path above. Work only in that checkout and
owned evidence directories. Agent HOME/auth stays normal; synthetic HOME/XDG is
for fixture test commands only. No installs, global settings, services or remotes.

Implement `status_reader.py:read_status(path) -> str`, standard library only.
Read UTF-8; accept exactly `pilot status: pending\n` or `pilot status: complete\n`
and return `pending` or `complete`. Other decoded contents raise ValueError;
I/O and Unicode decoding errors propagate. Never write the input. No CLI.
Gemini also writes `test_status_reader.py` covering both valid values,
empty/malformed input, missing file and unchanged input bytes. Use temporary files.
Only Gemini creates/edits Python code and tests; you write plans, inspect and verify.

## Entry

Before starting, read the authority plan's Reference and verify that exact Git
commit contains the approved narrowed trial contract. Current operative text must
match that frozen text except the reference/provenance record. Stop on an absent,
pending or mismatched reference. Later, Gemini must verify the fixture plan's
frozen commit before writing code; include its exact hash in the implementer brief.

1. Require inherited HERDR_ENV=1; explicitly read `herdr --skill`. Never fabricate
   the environment. Confirm actual session `skill-lens-pilot-20261017` and owned
   pane with native JSON status/current-pane queries. Discover syntax from help.
2. Require a fresh initial conversation without resumed history, preloaded rules,
   memory/profile or discovered skills. Explicit reading of this brief, approved
   process docs and Herdr skill is allowed. Read your actual system Session ID.
   Record configured `openai-codex`, `gpt-6.1-sol`, high, and approved `/chatgpt`
   base; record upstream identity unverified. Do not run an HTTP observer/probe.
3. Query the verified pane's conversation ID. If stale, allow exactly one checked
   native `report-agent-session` with current ID, fresh sequence and startup source,
   bounded to ten seconds as in the prior repair. Requery exact equality; stop on
   failure. Matching needs no write. This is not automatic-hook/restart proof.
4. Verify physical cwd is CHECKOUT. Exclusively create EVIDENCE/entry.json;
   an existing entry/result means stop and preserve that prior attempt.
   Take fresh original-repository HEAD/status and
   full tracked/nonignored-untracked file SHA256 manifest, including `.path`.
   Preserve the fixture's exact initial bytes/hash. Record entry in evidence.

## Run the ordinary loops

Use the sequence and role separation in the repository's planning-loop.md and
implementation-loop.md, with native Herdr dispatch replacing T3 delegate_task
for this trial only. Use the trial amendment instead of the old P01-P09 matrix.
Do not modify those process documents or execute product commands in the original
repository. Scope all plan/code commits and fixture checks to the new checkout.

1. Write a short `plan.md` with task, allowed files, observable acceptance and
   verification commands. Review the plan through the two Pi critics below.
   Resolve blockers, then make a local plan-only commit; put its full hash in the
   plan's reference field and make a provenance-only commit before implementation.
2. Start one fresh Gemini implementer with the reviewed plan and exact commit.
   Allowed edits: `status_reader.py` and `test_status_reader.py` only. Send the
   complete task, constraints and council implementer schema. No nested delegation,
   review, commit, push, dependency/config changes or writes to original repository.
3. Inspect every changed/untracked file. Run the four fixture checks below.
4. Materialize the complete diff (including new files) as
   `EVIDENCE/final-diff.patch`; record its SHA256. Send two fresh Pi critics the
   final plan, that exact artifact path/hash and checks. They have no shell to
   reconstruct a Git diff. Bind each report
   to unique token, target path and SHA256 manifest of the complete reviewed target.
   Collect both full reports, reproduce blockers and resolve them through Gemini.
   Fresh affected reviews are required after substantive corrections. Stop after
   two rounds without agreement. Optional polish does not block completion.
5. Confirm final checks and diff, original-repository manifest equality and no
   running task-owned commands. Keep evidence and idle worker panes; do not close
   the coordinator or touch unrelated panes. Commit only the two accepted fixture
   files locally. No fixture push or remote. Return result.json and STOP.

Use existing Git identity if configured; if absent, command-local
`git -c user.name='Skill Lens trial' -c user.email='trial@localhost' commit ...`
avoids editing personal configuration. Never change machine Git settings.

## Native launch and report collection

Read installed help. Split only the owned coordinator pane with `--cwd CHECKOUT
--no-focus`; parse actual pane IDs from JSON and confirm available shells.
Every agent name uses a fresh lowercase UUID token and matches
`^[a-z][a-z0-9_-]{0,31}$`. Retain own pane/agent/process/session IDs. Never reuse
an existing conversation or start two agents in one occupied pane.

For each Pi dispatch exclusively create a new directory under EVIDENCE and an
empty `sessions` subdirectory (mkdir without -p). Use different panes, processes,
tokens and session directories for each critic and round:

```text
herdr agent start critic-qwen-TOKEN --kind pi --pane PANE -- --provider anymodel --model qwen/qwen3.8-max --thinking high --tools read,grep,find,ls --no-mcp --no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts --no-skills --no-context-files --session-dir NEW_EMPTY_SESSIONS
herdr agent start critic-deepseek-TOKEN --kind pi --pane OTHER_PANE -- --provider workbuddy --model deepseek-v4.1-flash --thinking high --tools read,grep,find,ls --no-mcp --no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts --no-skills --no-context-files --session-dir OTHER_NEW_EMPTY_SESSIONS
herdr agent start worker-TOKEN --kind agy --pane WORKER_PANE -- --model gemini-3.8-flash-high --effort high --sandbox
```

Native controls are not T3 permission modes or a universal filesystem sandbox.
Keep the named models; do not substitute when unavailable. Upstream identities and
families are unverified under the user-accepted named-pair policy.

Build two complete independent critic prompts before submission. Each includes
the EXACT guard and report fields from council.md §§2/4, its token and full target
manifest, plan/task requirements, evidence paths and ONE question: Qwen checks
role/scope/process compliance; DeepSeek checks behavior/tests and missing proof.
Require `TOKEN`, `TARGET` and `TARGET_SHA256` plus EFFECTIVE_MODEL, VERDICT,
BLOCKERS, SUGGESTIONS, FILES_AT_RISK, CONCEDED, with start/end report markers.
Supply the report template explicitly; reviewers have only read/grep/find/ls.
In native EFFECTIVE_MODEL fields use runtimeMode=N/A, interactionMode=N/A and
record the actual native model/thinking/tool/context controls instead.

Start BOTH `herdr agent prompt ... --wait` submission jobs before waiting for
either result (e.g. separate Python subprocess.Popen calls). Retain each job's
exit/output independently. `--wait` observes UI state, not turn identity. Read the
complete terminal report via `herdr agent read NAME --source recent-unwrapped
--lines N --format text`; raise N if needed. Accept only matching token/target/hash,
start/end markers and all fields. Pi cannot write a fallback report. Preserve
recovered reports yourself in evidence. Missing/truncated reports, uncertain
delivery, unavailable model or wider permission dialog stop this attempt; inspect
current owned state, never blindly resend or launch replacement work.

## Fixture verification and result

Use `/Users/corvette/Documents/Projects Coding/Skill Lens/.venv/bin/python` for
pytest/mypy and `.venv/bin/ruff` for Ruff. Run from CHECKOUT, with command-local
HOME/XDG and cache/output paths inside TRIAL_ROOT, never agent-wide replacement:

```text
python -B -m pytest -p no:cacheprovider --cov=status_reader --cov-branch --cov-fail-under=90 --cov-report=term-missing
python -B -m mypy --strict --cache-dir EXTERNAL_CACHE status_reader.py
ruff check --no-cache status_reader.py test_status_reader.py
ruff format --check --no-cache status_reader.py test_status_reader.py
```

Set COVERAGE_FILE and PYTHONPYCACHEPREFIX under EVIDENCE; retain each command,
exit and output. Tests use temp files and synthetic HOME/XDG. Do not add a new
framework, install packages, regenerate product snapshots or run Skill Lens scans.

Save result.json: surface=herdr; verdict pass/failed/unverified; reason; actual trial/session/pane;
configured roster and identity limits; plan and final local commit IDs; task/token/
pane/session ledger; complete report paths; check commands/exits/coverage; original
repository entry/exit comparison; fixture before/after hashes; no active task-owned
commands; owned resources left intact. Retain source/diff/check/report artifacts
for T3 inspection, excluding credentials, private profile content and raw HTTP.
Passing proves only this normal cycle. Full migration, restart, cancellation and
P01-P09 acceptance remain unverified. Give the human verdict and evidence path.
