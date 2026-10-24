# Plan: overnight closure of CI, local Herdr deployment, trace, smoke and housekeeping

Status: Agreed
Authorization: Owner, 2026-10-24: “Overnight goal: close out every open fix on the skill-lens loop and product tracks, and leave me a morning report I can act on.” The same instruction names the five items (CI repair, local Mini footer deployment, full-TUI capture, formal end-to-end smoke, housekeeping), requires repo-held reviewable evidence, limits deployment to the everyday Herdr with no upstream publication, forbids new product work and main merges, and requires unresolved owner decisions to be listed rather than decided.
Reference: 0f024f6ceb8972685a8b58e30cca1ef2f499d219
Surface: product (CI test/packaging only) and omp/herdr (deployment, trace, smoke).
Risk and review: High: live worker control, a local configuration write and CI changes. This is an owner-directed overnight run. No independent critic wave is dispatched or claimed; the plan states that deviation explicitly and the morning report repeats it. No product behaviour changes.
Roster: This operator session only. No Sol identity and no independent-model review are claimed. Workers used for the smoke are session-selected and recorded by their configured identities; upstream identity remains unverified.
Expected child tasks: zero delegated authors. Reviewer/implements workers only inside the separately bounded smoke, if it is reached.

## Outcome

Leave `main` untouched and produce, on a review branch:

1. a CI gate that passes on the full GitHub matrix, with the Linux-only test failure and the packaging timeout explained by evidence;
2. manifest `2026.10.23.1` installed as a local override in the everyday Herdr, with rollback and verification;
3. a bounded full-TUI capture attempt that either names the premature-idle source or records a precise, evidence-backed inconclusive result;
4. a bounded end-to-end worker smoke result (pass or honest failure), not a forced green;
5. the pending Herdr evidence append and the superseded draft closed;
6. a morning report listing what ran, what did not, and every owner decision.

## Baseline

- Branch `fix/overnight-closure-20261024` from `main` at `c6c842c10db533b2520266df89cdf736775eec63`. Nothing merges to `main`.
- Local product gate at baseline: 1082 passed, 1 skipped, 91.16% coverage, mypy clean on 38 files, Ruff clean.
- GitHub CI: last success `c45e654` (2026-10-04). Since then the `ubuntu-latest / py3.11` suite fails at `tests/test_session_snapshot.py::test_cancelled_capture_does_not_publish` and the packaging min-endpoint lane exceeds its 180 s bound. Fail-fast cancels the remaining matrix jobs.
- Cause established by source reading: block 9 of that test needs the case-insensitive-filesystem fallback. `find_skill_document()` probes `SKILL.md` first, which resolves to the lowercase `skill.md` on APFS; capture records the real name `skill.md`, so the parser's `SKILL.md` key misses and the `samefile` fallback runs. On a case-sensitive Linux filesystem the lowercase document is found directly, the fallback never runs, and no cancellation checkpoint can fire.
- Packaging min lane reproduced locally: 44.6 s end to end, passed. The CI timeout is therefore either a slower runner or a genuine hang and must be measured after a bounded increase.
- Installed Herdr 0.9.5 (`fb77c223…`), OpenCode 2.1.4 (`d8a65dd2…`). No local override exists; the active remote OpenCode manifest is still `2026.06.10.1`. Everyday session `default` is running at `/Users/corvette/.config/herdr/herdr.sock`.
- The accepted rule and patch are in `docs/validation/omp-coordinator/2026-10-23-herdr-opencode-214-footer/`; the lap proof is in `docs/validation/omp-coordinator/2026-10-23-herdr-mini-lap-live/`. The pinned source archive is in the investigation folder.
- Pre-existing user work: modified `docs/validation/omp-coordinator/2026-10-20/herdr-dispatch.md`, untracked `.path`, untracked `docs/plans/2026-10-19-herdr-omp-coordinator.md`. Preserve until their own housekeeping commits.

## Scope and boundaries

- CI edits: `tests/test_session_snapshot.py` and `scripts/smoke_wheel.py` only. No product behaviour change.
- Evidence: new dated records under `docs/validation/overnight/2026-10-24/`; the pending append to the 2026-10-20 record; the archived draft.
- Deployment: write only `<config_dir>/agent-detection/opencode.toml` in the user's everyday Herdr (`~/.config/herdr/agent-detection/opencode.toml`), after recording that no override existed. Back up nothing because nothing exists; rollback is deleting the file and reloading.
- Trace: an owned temporary source/tools root, instrumented from the pinned v0.9.5 archive only. No installed binary, settings, service or integration is modified. No upstream publication.
- Smoke: worker panes created only inside the verified `default` session with explicit pane IDs and bounded waits; owned panes are closed afterwards. No unrelated pane is touched.
- No main merge, no tag, no release, no new product feature, no loop-document redesign.
- No raw-socket state mutation except the official `server.reload_agent_manifests` method, used solely to make the local override effective without restarting the user's server. If that method is unavailable or fails, the restart choice goes to the report.

## Steps

1. **CI.** Split the case-insensitive samefile block into its own test with a runtime skip on case-sensitive filesystems and a precise reason; keep the other nine cancellation phases in the main test. Raise the packaging lane's bounded timeout from 180 s to a measured ceiling (600 s) and include partial output on timeout so a future failure is diagnosable. Run the four local gates, push the branch, and read the full run. Iterate only on evidence.
2. **Deployment.** Apply the accepted correction patch to a fresh extraction, verify the four source hashes and the manifest digest `d8646392…`, install it as `~/.config/herdr/agent-detection/opencode.toml`, verify parsing and detection with `herdr agent explain` on the captured footer, then call `server.reload_agent_manifests` and record the response. Prove the installed binary and remote cache are unchanged.
3. **Trace.** Follow the frozen design: owned source copy, pinned verified toolchains, structured records at the named boundaries, build, isolated server/session, one full-TUI worker, one harmless prompt, bounded observation, classify as selection-derived idle, upstream terminal event, other reporter, or inconclusive. Missing boundary = inconclusive, not a guess.
4. **Smoke.** If the deployed rule and a trustworthy wait path exist, run one bounded read-only worker dispatch with a unique token, verify the matching complete report and native completion, preserve unrelated panes, and record pass or failure against the existing acceptance criteria. A Sol-coordinator identity claim is not made.
5. **Housekeeping.** Commit the append-only `herdr-dispatch.md` sections (byte-identical to the already-committed investigation copy), and move the superseded 2026-10-19 draft into `docs/archive/plans/` with a one-line supersession note. Leave `.path` untouched and report it.
6. **Report.** Write `docs/validation/overnight/2026-10-24/REPORT.md` with evidence paths, CI run IDs, deployment state, trace classification, smoke outcome, deviations, and owner decisions.

## Acceptance

- Full GitHub matrix green on the branch, including packaging; the two original failures explained by the recorded diagnosis.
- Local override active and verified; rollback documented; no installed-binary or remote-manifest change.
- Trace result is classified from recorded evidence, or explicitly inconclusive with the missing boundary named.
- Smoke result is pass or an honest failure with the failed criterion named; no early completion is normalised into success.
- No unexpected user-file changes; no main merge; no upstream publication.
- Morning report is sufficient for the owner to decide merge, restart, trace fix and formal smoke acceptance.

## Review decisions

No independent review round was run under this overnight instruction. That is a recorded process deviation, not an exemption claimed by this plan. The owner reviews the branch and evidence in the morning.

## Execution receipt (append-only)

- **CI.** Split the case-insensitive `samefile` phase into its own test with a
  precise skip; the Linux 3.11 and macOS 3.11 jobs passed. The packaging lane
  was not a timeout: at 600 s it still produced no output. The lane runs on
  Python 3.13, where two blocked-capture teardown tests pressed `q` before the
  mounted screen installed its bindings; the app never exited. A bounded 0.2 s
  pause after confirming the blocked worker restores the proof. A second 3.13
  regression (symlink loops no longer raising under `Path.resolve(strict=False)`)
  was fixed with a strict-first resolver. Local: 3.11 gate 1083 passed/1 skipped,
  91.16%; 3.13 and 3.14 each 1083 passed/1 skipped in ~65 s. Final CI run
  `40136543801` is green on all nine jobs.
- **Deployment.** Manifest `2026.10.23.1` installed at
  `~/.config/herdr/agent-detection/opencode.toml` (SHA-256 `d8646392…`), no
  prior override; the running `default` server reloaded and reports the local
  override active. Installed binary and remote `2026.06.10.1` unchanged.
- **Trace.** Full-TUI capture classified as selection-derived idle; the settled
  wait replays the pre-working idle. The exact waiter boundary was not
  reproduced in one run; no fix implemented. Instrumentation patch and 663
  records preserved under `docs/validation/overnight/2026-10-24/trace/`.
- **Smoke.** One read-only Mini worker passed; wait returned 0.512 s after
  native completion; owned pane closed and layout restored. Not the Sol formal
  smoke.
- **Housekeeping.** The two failed-trial records are committed; the 2026-10-19
  draft is archived with a supersession pointer; `.path` left untouched.
- **Deviation.** No independent critic wave; recorded in the report. Temporary
  diagnostic workflows and roots were removed; no main merge; no upstream
  publication.
