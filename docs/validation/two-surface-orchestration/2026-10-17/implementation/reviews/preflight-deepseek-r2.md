Confirmed: HEAD `a0ffa9e`, no tracked files modified, `.path` present untracked and unchanged (0 bytes, Oct 16), setup.md now uses the direct-interactive Hermes flow and explicitly avoids single-pane self-occupation. I have everything needed.

---

EFFECTIVE_MODEL: Pi / WorkBuddy DeepSeek (`workbuddy/deepseek-v4.1-flash`) via `pi`, thinking=high, read-only critic tools. This is my configured target per the brief. Configured selection only; upstream vendor family identity is unverified and, per the frozen plan, a self-report is never upstream execution proof.

VERDICT: **PASS for the bounded preflight checkpoint.** The current documents are accurate, scoped, and safe to retain/commit as preflight evidence only. Every round-1 blocker I can independently reproduce is fixed, and the round-2 corrections the coordinator claims are present in the live files. This approval covers the handoff/checkpoint text, **not** runtime, trial-readiness, pilot acceptance, or the full migration. Unresolved human runtime prerequisites (session/mapping approval, Critic-1 native route, P01–P09 execution) are correctly left open and correctly labeled as such.

BLOCKERS: none outstanding for the checkpoint. Verified against the live tree:

1. **Ruff-format count corrected to 187.** `implementation/preflight.md:40` now reads `187 files already formatted`, with `:42` explicitly noting "184 was an earlier drafting-tree figure." `preflight-receipt.json:115` is `"filesFormatted": 187`. The authoritative baseline log is `187 files already formatted`; `final-checkpoint-gates/ruff-format.log` correctly shows `197` in the later run, and `coordinator-checkpoint-notes.md:8` explicitly separates 197 (this run) / 187 (baseline) / 184 (drafting). No conflation. Good.

2. **Commit links now resolve to the real repo.** `setup.md:5`, `pilot.md:4`, `preflight.md:7` all link `https://github.com/Hazem-Samak/skill-lens/commit/58d48ce…`. I independently confirmed `git remote -v` → `https://github.com/Hazem-Samak/skill-lens.git` and `git cat-file -t 58d48ce…` → `commit`. Frozen hash exists and is the correct one.

3. **Single canonical fixture path; no placeholder.** No `skill-lens-synthetic-fixture` reference remains (grep clean). Everything points at `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout`; the checkout exists with `.git` and `fixture.txt` (22 bytes), and `fixture-manifest.json` carries the baseline hash. Output is confined to `pilot-artifacts/`.

4. **Pi read-only claim now honest.** `setup.md:92,96` and `preflight.md:64,131` state `--tools read,grep,find,ls` drops bash/write/edit but that `--tools` alone keeps MCP, so `--no-mcp` is added; `--no-extensions -e …/herdr-agent-state.ts` retains Herdr state observation; wording is explicitly "tool-level restriction and MCP suppression, not universal filesystem sandboxing." This matches installed help and resolves the overclaim.

5. **Isolation claims no longer overclaimed.** `setup.md:97` states `--in DIR` "is directory selection, not a path jail"; `--ignore-rules` is scoped to skipping rule/memory/skill injection; agy `--sandbox` is called an advertised terminal restriction, and `--add-dir`/`--project` are not described as confinement. No path-jail claim survives.

6. **Startup is now a viable control path.** `setup.md:114,125` use the direct interactive Hermes launch in a real Herdr shell ("avoids single-pane self-occupation"), and the untested RPC flow is stripped. This resolves the one-pane self-occupation defect without asserting an unproven mechanism.

7. **cmux / kind-gap / scope integrity.** cmux absolute path is used, PATH edit marked optional (`setup.md`), `Contents/MacOS/cmux` warning retained. The mcode/minimax gap is stated as scoped to the installed 24-kind enum and inspected configs, explicitly *not* global impossibility, with no silent substitute. No tracked file is modified (`git diff --name-only` empty), HEAD `a0ffa9e` matches, and the frozen plan diff is confined to the `Reference:` line. `.path` remains untracked, 0 bytes, unchanged.

SUGGESTIONS:
- `setup.md:89` coordinator row and `preflight.md:129-130` still present the `herdr agent start … --pane <id>` form as "Proposal Ready." Since §6 now adopts direct interactive launch, add one clause that the `agent start` row is an alternate RPC form requiring a second control pane — otherwise a reader may re-introduce the self-occupation path. Cosmetic; not a blocker.
- `coordinator-checkpoint-notes.md` correctly separates the three counts; consider citing the exact log path per number so a future reader cannot re-conflate.
- The prior-round reports (`reviews/preflight-*-r1.md`) and `checkpoint-task-ledger.json` retain the *old* 184/`herdr session status` text as historical evidence. That is correct per "preserve raw report," but the ledger should be labeled historical so it is not read as current state.

FILES_AT_RISK:
- `docs/validation/two-surface-orchestration/2026-10-17/setup.md`, `pilot.md`, `implementation/preflight.md`, `implementation/preflight-receipt.json`, `implementation/human-pilot-brief.md`, `acceptance.md`, `implementation/coordinator-checkpoint-notes.md` — untracked evidence; corrections validated. Reviewed only.
- Frozen `docs/plans/2026-10-17-two-surface-orchestration.md` (diff = Reference line only) and `docs/process/**` — unchanged; must stay so.
- Pre-existing untracked `.path` — verified preserved (untracked, 0 bytes).
- No product code, tests, snapshots, or registry touched.

CONCEDED:
- **Observation A:** `mcode`/`minimax` absent from the 24-kind enum — confirmed, and correctly kept as a scoped prerequisite, not proof of global impossibility, with no demanded roster amendment.
- **Observation B:** cmux absent from PATH; absolute invocation sufficient, no persistent shell edit needed — confirmed and honestly stated.
- **Observation C:** single-pane `agent start` self-occupation — confirmed against help; the fix (direct interactive launch) is present.
- **Observation D:** `--tools` keeps MCP unless `mcp__` allowlisted; `--no-extensions` would suppress Herdr integration unless `-e` retained — confirmed; the proposal now does exactly this.
- **Observation E:** `--ignore-rules`/`--in`/`agy --add-dir/--project` are not path sandboxes — confirmed; "strictly confined" wording removed.
- **Observation F:** old fixture path nonexistent — confirmed; single canonical prepared path now used.
- **Observation G:** bare github.com links and 184-vs-187 — confirmed fixed; real repo links, 187 authoritative.
- **Observation H:** P01–P09 all PENDING; the overnight instruction does not repeal explicit human startup/restart/session+mapping approvals — confirmed. Exact safe checkpoint: retain/commit this corrected preflight evidence → user approves session names, startup, and Critic-1 route/mapping → human starts the session inside `HERDR_ENV=1` → P01–P09 run live. No independent work product remains before that; Phase-C process edits stay gated on the pilot.
- Scope integrity: I made no writes, no delegation, no approval call, no test run in the checkout; no live Herdr session inspected or controlled.

A pass here approves only accurate preflight evidence and handoff — never runtime or trial-ready status.
