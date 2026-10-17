# Round-2 independent critic review — native-mapping documentation checkpoint

## Summary

Read-only second substantive review round of the six changed substantive files under
`docs/validation/two-surface-orchestration/2026-10-17/` (`setup.md`, `pilot.md`,
`acceptance.md`, `implementation/preflight-receipt.json`,
`implementation/human-pilot-brief.md`, plus the untracked
`implementation/native-mapping-application-report.md` as administrative evidence).

Goal: judge preservation of frozen authority, exact approved routes/permissions,
critic context independence, and the two round-1 blockers (B1 worker dispatch,
B2 post-edit critic wave) plus the shared handoff contract.

Verdict: **pass** — no blockers. B1 and B2 are withdrawn on inspected content, not on
coordinator self-report. Three non-blocking documentation items are listed.

Scope is this documentation/handoff checkpoint only. Full migration remains incomplete:
P01–P09 stay pending until genuine live execution inside a human-started Herdr pane,
and Phase C is unstarted.

Restrictions honoured by this review: no file in the repository was created, edited,
moved, deleted or renamed; no formatter, linter-with-fix, install, git mutation,
snapshot/golden regeneration, or writing test run; no live Herdr, agent, model or
service was started and no machine configuration was changed; delegation was not used.
Only read-only shell inspection, static installed `--help` / `--skill` output, and file
reads were performed. Test output was not re-run; existing gate logs were read only.

## Verified evidence (independent, not coordinator-reported)

1. Byte identity of the primary bundle. SHA-256 recomputed on disk matches the supplied
   bundle exactly: `setup.md 5cf3468…`, `pilot.md c22fd3c…`, `acceptance.md c022824…`,
   `preflight-receipt.json 662247c…`, `human-pilot-brief.md 27d7bc4…`. `git rev-parse HEAD`
   = `0c9991439309b1ce819abc4eb007664b872cc45b`. `git status --porcelain` shows exactly five
   modified tracked files, all under the checkpoint directory, plus untracked evidence and
   a preserved `.path`. `git diff HEAD --stat` = 5 files, 708 insertions / 192 deletions;
   no Python, test, config, registry or process file changed.
2. Frozen guard preserved. The fenced critic block in `docs/process/council.md` §2 is 541
   chars and is byte-identical at baseline commit `2d9637054aea969fb2ec575cf28e48ed0ec1a800`
   and at HEAD. The four critic prompts in the brief (`PROMPT_QWEN`, `PROMPT_DEEPSEEK`,
   `PROMPT_QWEN_P03`, `PROMPT_DEEPSEEK_P03`) each begin with that exact block as a
   character-for-character prefix (verified programmatically; 4 occurrences total, and
   `WORKER_PROMPT` correctly does not carry the critic guard).
3. Routes match the frozen amendment. `docs/plans/2026-10-17-herdr-native-pilot-critic-amendment.md`
   §3 pins `provider=anymodel` / `model=qwen/qwen3.8-max` / thinking high and
   `provider=workbuddy` / `model=deepseek-v4.1-flash` / thinking high, with read-only
   tools, `--no-mcp`, `--no-extensions -e …/herdr-agent-state.ts`, `--no-skills`,
   `--no-context-files`, per-dispatch empty session dir, no continue/resume. All four
   operational files carry the same two routes and the same native flags. No Grok, XKiro,
   wrapper, T3-critic substitution or serial fallback appears in any executable instruction
   (both strings appear only in the Herdr kind enum list and in the recorded exclusion history).
4. Static CLI surface matches the handoff (installed help, nothing started):
   `herdr agent prompt <TARGET> <TEXT> --wait --until <STATUS> --timeout <MS>` with
   documented `agent_prompt_stalled` at 5000 ms, turn-agnostic settle matching, and CLI
   errors as JSON on stderr with exit status 1 (server) / 2 (syntax) — the brief captures
   exit codes per submission. `herdr agent read <TARGET> --source recent-unwrapped --lines N`
   matches. `herdr pane split --current --direction right|down --cwd <PATH> --no-focus`
   matches, and the installed `--skill` documents that control commands return JSON with the
   new pane at `.result.pane.pane_id` — exactly the key the brief parses. `herdr agent
   send-keys <TARGET> ctrl+c` is documented in `--skill`. `herdr --skill`, `herdr status
   --json`, `herdr session stop|attach`, `herdr agent get`, and the 24-kind enum
   (including `pi` and `agy`, excluding `mcode`) all match the documents. `pi --help`
   documents every flag used (`--provider`, `--model`, `--thinking high`, `--tools`
   allowlist that keeps MCP unless suppressed, `--no-mcp`, `--no-extensions` with explicit
   `-e` still working, `--no-skills`, `--no-context-files`, `--session-dir`).
   `hermes --help` confirms `--cli --ignore-rules --in DIR -m MODEL --reasoning`.
   `agy --help` confirms `--model --effort --sandbox` and describes `--sandbox` verbatim as
   "terminal restrictions enabled", matching the "advertised restriction, not a filesystem
   jail" wording.
5. Tool names are real. In the installed `@earendil-works/pi-coding-agent` 1.3.0 bundle,
   built-in tools are registered by name including `bash` and `grep`; `read`, `edit` and
   `write` are stated in pi's own usage line. So the frozen `--tools read,grep,find,ls`
   allowlist does drop shell/write/edit. Per-name attribution for `ls` and `find`
   individually is not separable from static grep (at least one of `find`/`ls`/`list`/`glob`
   is registered); a wrong name can only narrow, never widen, permissions.
6. Fingerprint helper is real and matches its documented contract.
   `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/snapshot_tree.py` exists (1142 bytes);
   `save`/`compare` write/read a JSON envelope of `head`, `git status --porcelain=v1 -uall`
   and per-path sha256/symlink targets for tracked plus nonignored untracked files; `compare`
   prints `changed_paths`, `head_unchanged`, `status_unchanged` on stdout and does not signal
   differences with a non-zero exit — precisely what the brief asserts. It writes only to the
   supplied destination under the owned artifacts root, and the brief `cd`s to the repo root
   first because the helper uses `Path.cwd()`.
7. Fixture and environment are real. `synthetic-checkout/fixture.txt` exists and its SHA-256 is
   `462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e`, matching the pinned
   value used for token/path/hash binding in every prompt. `pilot-artifacts/` exists and is
   empty, so the `tempfile.mkdtemp(..., dir=ARTIFACT_ROOT)` dispatch roots will succeed.
8. B1 (implementer dispatch) is fixed in content. `WORKER_NAME="worker-${WORKER_TOKEN}"` with
   uuid hex12 and the same regex validation as the critics (brief lines 217–221); a complete
   literal `WORKER_PROMPT` (line 241) carrying read-only repository constraint, no delegation /
   no review / no commit / no push, single permitted fixture edit, artifacts-only output, and
   a full implementer report schema with `DISPATCH_TOKEN`, `TARGET_PATH`, `TARGET_SHA256` and
   N/A T3 fields; real submission with log redirect and `EXIT_WORKER` capture (line ~257);
   report readback via `herdr agent read`; strict token+path+hash acceptance; independent Sol
   verification via `git -C … diff fixture.txt` and a recomputed `TARGET_REVISED_SHA256`;
   then repo-fingerprint compare requiring `changed_paths=[] AND head_unchanged=true AND
   status_unchanged=true`.
9. B2 (post-edit critic wave) is fixed in content. Fresh `TOKEN3`/`TOKEN4` with cross-wave
   collision checks, fresh regex-valid names, two new panes asserted non-empty, distinct from
   each other, from the coordinator pane and from PANE1–PANE3, fresh exclusive `mkdtemp` roots
   with `mkdir` **without** `-p` for sessions dirs, the exact frozen native start commands,
   `herdr agent get` readiness with distinct PIDs/session IDs and no continue/resume, two
   complete literal briefs carrying the revised `${TARGET_REVISED_SHA256}`, both submits
   backgrounded with `&` **before** any `wait`, separate exit codes written to separate
   `.result` files, envelope binding on token+path+hash, and a post-wave repo fingerprint
   compare. `mkdir -p` appears once in the brief and only inside the prohibition sentence.
10. Other acceptance elements hold. Empty fresh per-dispatch sessions and processes; distinct
    ready panes; every prompt submission issued before collection; human-only lifecycle
    (`herdr session stop skill-lens-pilot-20261017` by the external human, `herdr server stop`
    prohibited, `--skill` line 212 concurs); restart framed as continuation with retained
    evidence, not blind replay; original repository read-only with external content-hash
    fingerprints and no writes to the repo; P04 capture-or-stop with no write fallback and no
    tools granted to rescue capture; P07 bounded owned stop with PID/job evidence plus the two
    synthetic rejections; P09 runtime cmux via the absolute CLI wrapper (with the GUI-bundle
    path warning); native restrictions described as restrictions, not a jail; P01–P09 all
    recorded PENDING in `pilot.md` and `preflight-receipt.json`; Phase C unstarted.
11. Gate-log claims verified by reading the retained logs: `pytest.log` ends
    "1048 passed, 1 skipped" with "Required test coverage of 90.0% reached. Total coverage:
    91.11%", the single skip being the documented case-insensitive-filesystem case;
    `mypy.log` "Success: no issues found in 37 source files"; `ruff-check.log`
    "All checks passed!"; `ruff-format.log` "216 files already formatted". `environment.json`
    shows synthetic HOME/XDG and external cache/coverage paths outside the checkout. These
    prove source health only, as every document states.

## Findings

No blockers.

B1 and B2 are withdrawn: the corrected content is present, complete and internally
consistent, and every external dependency the handoff relies on was verified to exist with
the asserted contract. Nothing in the corrected text restates the original defects.

## Non-blocking suggestions (coordinator-owned, no route or scope change)

1. `docs/validation/two-surface-orchestration/2026-10-17/acceptance.md:135` still states
   "Final post-correction source gates have not yet been run; coordinator will execute them
   after inspection", while line 165 of the same file records the completed post-correction run
   and links `implementation/native-mapping-application-r2-gates/`. The file already uses an
   explicit "superseded by" convention elsewhere; apply it here so an auditor reading the
   checkpoint section cannot read two contradictory answers to "did the gates run?".
2. `docs/validation/two-surface-orchestration/2026-10-17/implementation/preflight-receipt.json:290`
   keeps the note "Final post-correction gates will be run by coordinator after inspection".
   A JSON reader has no later paragraph to consult; point that note at
   `native-mapping-application-r2-gates/` with its counts, or add a sibling supersession key,
   while keeping the historical values in `historicalPreflightProvenance` untouched.
3. Placeholder spelling differs across the frozen and applied records without a note:
   amendment §3 uses `critic_qwen_<dispatch-token>` and
   `pi-critic-qwen-<dispatch-token>/sessions`; `setup.md` uses `critic-qwen-<hex12>` and
   `pi-critic-qwen-<token>/sessions`; `preflight-receipt.json:168,196` uses
   `pi-critic-qwen-<token>-<dir>/sessions` to reflect `mkdtemp`. All are regex-valid and
   semantically equivalent, and the receipt explains its suffix; one line in `setup.md`
   recording that `mkdtemp` appends a random suffix would remove any chance of an operator or
   transcriber mixing the three forms.
4. Optional strengthening inside fixed permissions, derived from amendment §3/§5 ("Stop if
   prohibited tools/extensions/context appear, a denied-write request modifies the fixture, or
   native settings do not take effect"; "Missing separation stops the role"): the brief
   currently proves readiness and captures reports, but has no explicit step that reads back
   the observed native tool/context set and stops the role if `bash`/`write`/`edit`, MCP, or
   discovered skills/context files are present. The critic prompts already ask for native
   controls in `EFFECTIVE_MODEL`; adding a coordinator-side check plus a stop rule would make
   the separation failure mode executable rather than only reported.

## Residual risk and unresolved decisions (for the coordinator, not blockers)

- Whether pi 1.3.0 honours the individual `ls` and `find` names in the frozen `--tools`
  allowlist cannot be settled without running pi. Both outcomes preserve the read-only
  intent: unknown names can only narrow the tool set, and the brief already stops on a failed
  `agent start`. Treat the actual startup line in P02 as the measurement point.
- `--wait` matches settle states, not turn identity, and `--lines` cannot always recover
  alternate-screen rows (documented in the installed `--skill`). P04 already fails closed to
  "mark capability unavailable and stop"; naming that documented recovery limit as a stop
  reason before escalating `--lines` would make the decision faster and less improvised.
- If a second substantive round fails to converge with the other reviewer, council.md §5
  requires escalation to the user rather than a third wave.
- Whether the downstream fix is applied in this checkpoint or folded into the post-pilot
  documentation pass is the coordinator's call; suggestions 1 and 2 are cheap now and
  suggestion 4 is naturally paired with the first live pilot evidence.