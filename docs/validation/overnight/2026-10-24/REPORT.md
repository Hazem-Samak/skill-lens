# Morning report — overnight closure

Date: 2026-10-25. Branch: `fix/overnight-closure-20261024` (draft PR #3).
`main` is untouched. Nothing was published upstream.

## Bottom line

| Item | State |
| --- | --- |
| Linux CI test failure | **Fixed**; Ubuntu 3.11 and macOS 3.11 pass |
| Packaging lane | **Fixed and green**: Python 3.13 test-timing hang, not slowness |
| Python 3.12–3.14 matrix | **Green** on Ubuntu and macOS after the timing and symlink-cycle fixes |
| Footer rule in everyday Herdr | **Deployed and active** (`2026.10.23.1`, local override, no restart) |
| Bounded worker smoke | **Pass** for the Mini route; wait returned after native completion |
| Full-TUI early-idle trace | **Cause identified** at the state-ordering level; exact waiter boundary not reproduced in one run |
| Housekeeping | **Done**: evidence append committed; stale draft archived |
| Formal Sol-coordinator smoke | **Not run**; owner decision |

## 1. CI

The Linux failure was a test that could only pass on a case-insensitive
filesystem. The step-4 `samefile` fallback is reached only when `SKILL.md`
resolves to a real lowercase `skill.md` entry; on Linux the parser reads
`skill.md` directly, so the checkpoint never runs. That phase is now its own
test with a precise runtime skip. The other nine cancellation phases still run
on both platforms.

The packaging lane was a different story, and not a timeout. Raising the bound
to 600 s also expired with **empty** output. The packaging job runs the lane
with Python 3.13, and on 3.13 the blocked-capture teardown tests pressed `q`
before the mounted screen installed its bindings; the key was dropped and the
headless app never exited. Two tests now pause 0.2 s after confirming the worker
is blocked. The watchdog proof is unchanged: it fires at 1.5–2.0 s and still
must not fire.

The full matrix also failed on Python 3.13 for a second reason:
`Path.resolve(strict=False)` stopped raising on symlink loops, so Codex config
cycles were no longer classified as unsupported. `_resolve_config_path()`
resolves strictly first and falls back to non-strict only for missing paths.

Local results before the run: Python 3.11 gate 1083 passed, 1 skipped, 91.16%
coverage; Python 3.13 and 3.14 each 1083 passed, 1 skipped in about 65 s.

**Final CI run [40136543801](https://github.com/Hazem-Samak/skill-lens/actions/runs/40136543801)
is green:** all four Ubuntu versions, all four macOS versions and the packaging
job passed. The packaging job took 98 s; the minimum endpoint
(`textual==8.2.8`) passed in about 43 s against the 300 s bound. The verified
code commit is `d06c8b3`; later commits are documentation only.
Receipt: [ci/run-40136543801.json](ci/run-40136543801.json).
Full details: [ci/diagnosis.md](ci/diagnosis.md).

## 2. Everyday Herdr deployment

- File: `~/.config/herdr/agent-detection/opencode.toml`, SHA-256
  `d86463927f13191fb8123a6fe0efe3435e9e4832a9c7cd6123ee7bfe02857104`.
- Built from the pinned v0.9.5 archive plus both accepted patches; the digest
  matches the isolated lap proof.
- No override existed before. The installed binary and the remote
  `2026.06.10.1` file are unchanged; the remote file is shadowed.
- The running server was reloaded with the official
  `server.reload_agent_manifests` method. `herdr server agent-manifests` now
  shows `opencode  local override  active 2026.10.23.1`.
- Captured busy frames classify `working`; the finished frame and quoted/
  prefixed copies classify `idle`.
- Rollback: delete that one file and reload; no restart required.
- Evidence: [deployment.json](deployment.json), [fixtures/](fixtures/).

## 3. Bounded smoke

One read-only Mini worker in the verified `default` session, one owned pane,
`opencode mini --model opencode/deepseek-v4.1-flash-free#max --agent plan`.
Detection matched the new rule at `2026.10.23.1`; the wait returned **0.512 s
after** native completion, not early; the native session recorded one user turn,
one assistant turn, `finish=stop`, zero tool parts; the owned pane was closed and
the layout restored. Details and limits: [smoke/README.md](smoke/README.md).

This is not the original Sol-coordinator formal smoke. It proves the deployed
rule, worker startup, prompt delivery, screen detection, wait ordering and
native completion for the Mini route. It does not validate full-TUI waiting.

## 4. Full-TUI trace

A diagnostic build of the pinned source captured reporter and server records.
The measured order, with an auto-submitted prompt at TUI startup:

| UTC | Event |
| --- | --- |
| 21:29:55.047 | user message |
| 21:29:55.070 | reporter publishes `idle` from selection |
| 21:29:55.289 | server accepts idle, state sequence 18 |
| 21:29:55.401 | server accepts working, state sequence 19 |
| 21:30:03.430 | native assistant finishes |

The 2026-10-19 incident has the same order: waiter returned idle (completion 18),
then working 19, then native completion 6.909 s later. The settled wait starts
from the pre-submission event sequence with no lower bound and replays that
idle, so it can return before the turn's first working report.

**Limit:** I did not reproduce the early return through `agent prompt --wait` in
one run. The waiter can only submit after the TUI is registered, by which time
the selection idle is already before its baseline. Four waiter runs returned
0.159–0.197 s **after** native completion. The ordering and the return
mechanism are measured/source-backed; the single-run waiter boundary is not.
No fix was implemented. Candidate fixes are listed in
[trace/result.json](trace/result.json); choosing one is your call.

## 5. Housekeeping

- The two failed live-trial records are committed at their canonical path. They
  were already byte-identical to the preserved investigation copy.
- The never-frozen `2026-10-19` coordinator draft is archived with a
  supersession pointer; its body is unchanged.
- `.path` remains untouched (empty, untracked, pre-existing).
- The instrumented source and temporary roots were removed after the evidence
  was pushed.

## Decisions for you

1. **Merge the branch:** the gate is green on the verified code commit
   `d06c8b3`; review PR #3. Later commits are documentation only.
2. **Trace fix:** choose a sorted-wait bound, reporter suppression, or server
   suppression (see `trace/result.json`). I did not implement one.
3. **Formal smoke:** decide whether the Mini-route pass is enough for the loop,
   or require a Sol-coordinator run after the full-TUI fix.
4. **Upstream publication:** untouched; the rule remains a local override.
5. **Packaging bound:** now 300 s (measured ~98 s job, ~43 s min lane). Say if
   you want it tighter or looser.

## Deviations and limits

- No independent critic wave was dispatched; the overnight instruction is the
  authority. This is stated in the frozen plan.
- The trace used a private OpenCode backend and an isolated Herdr session; the
  everyday server was not touched by it.
- Upstream model identity is unverified in every run.
- The 600 s diagnostic timeout was not treated as a fix; the real cause was the
  Python 3.13 key-timing hang.
- The branch tip adds documentation after the verified `d06c8b3` code commit;
  those later commits are not a second product verification.
