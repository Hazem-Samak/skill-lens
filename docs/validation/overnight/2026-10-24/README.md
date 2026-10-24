# Overnight closure — evidence

Date: 2026-10-24/25. Branch: `fix/overnight-closure-20261024` (draft PR #3).
Plan: [2026-10-24-overnight-closure.md](../../../plans/2026-10-24-overnight-closure.md).
Morning report: [REPORT.md](REPORT.md).

## Contents

- `ci/` — the two CI failures, root cause and fix state.
- `deployment.json`, `fixtures/` — manifest `2026.10.23.1` installed as a local
  override in the everyday Herdr, with verification and rollback. No installed
  binary, remote manifest or upstream publication changed.
- `smoke/` — bounded Mini-route dispatch on the everyday session: **pass**,
  with scope limits (not the Sol formal smoke).
- `trace/` — full-TUI capture: selection-derived idle measured; the waiter
  replay is the source-backed return mechanism; the exact waiter boundary was
  not reproduced in one run. No fix implemented.
- `trace/instrumentation.patch` — diagnostic-only instrumentation, not proposed
  for merge.

## One-paragraph summary

The Linux-only test failure is fixed. The packaging lane was a genuine Python
3.13 test-timing hang, not a timeout; both it and a 3.13 symlink-cycle
regression are fixed, and CI run 40136543801 is green on all nine jobs
(Ubuntu and macOS 3.11-3.14 plus packaging). The accepted footer rule is live in the everyday Herdr and a
read-only worker completed end-to-end with the wait returning after native
completion. The full-TUI trace found the idle frame that can satisfy the
settled wait (selection path, accepted before working) and named why the waiter
can return early; it did not reproduce that return in a single run. No main
merge, no upstream publication, no product feature work.
