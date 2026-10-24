# Full-TUI premature-idle trace — what was measured

Date: 2026-10-24/25. Method: the frozen design in
[2026-10-22-herdr-full-tui-capture.md](../../../../plans/2026-10-22-herdr-full-tui-capture.md).
Result classification: **selection-derived idle**, with the settled-wait replay
as the premature-return mechanism. This is a measured ordering plus a
source-backed mechanism; no single run exercised both boundaries.

## Setup

- Pinned Herdr v0.9.5 source, both accepted manifest patches, plus a
  diagnostic-only JSONL capture at the reporter and server boundaries.
  The instrumentation patch is [instrumentation.patch](instrumentation.patch);
  it is not proposed for merge.
- Owned temporary root, synthetic HOME/XDG, isolated `mini` Herdr session on a
  short socket, private OpenCode backend on loopback, full TUI in one owned pane.
- Model: `opencode/deepseek-v4.1-flash-free`, Plan, variant `default`.
  Upstream identity unverified. No user service, config or pane was used.

## Measured sequence (auto-submitted prompt at TUI startup)

| UTC | Event |
| --- | --- |
| 21:29:55.047 | user message accepted |
| 21:29:55.070 | reporter publishes `idle` from the selection path |
| 21:29:55.289 | server accepts `Idle`, state sequence `18` |
| 21:29:55.401 | server accepts `Working`, state sequence `19` |
| 21:30:03.430 | native assistant finishes (8.4 s after the accepted idle) |

The 2026-10-19 incident has the same ordering: the waiter returned `idle` with
completion sequence `18` at 22:29:29.093, a working read followed at 22:29:32.281
(sequence `19`), and native completion was at 22:29:36.003 — 6.909 s late.

## Return mechanism

`prompt_agent` runs two waits. The activity gate uses
`after_state_change_seq = Some(prompt_state_change_seq)` and correctly ignores
the pre-working idle. The settled wait then starts from `last_event_sequence`
(captured **before** submission) with `after_state_change_seq: None`. That
replay includes the idle accepted just after submission, so it matches `idle`
and returns. The later working report proves the turn was still running.

## What was not reproduced

`agent prompt --wait` can only submit after the TUI is registered. By then the
selection idle is already before the submission baseline, so it is not replayed.
Four waiter runs returned **after** native completion (+0.159 s, +0.159 s,
+0.197 s, +0.183 s). The TUI's own `--prompt` starts before selection sync and
reproduces the ordering, but bypasses the waiter. That is the named missing
boundary.

## Candidate fixes (not implemented)

1. Settled wait: require a state change after the working/blocked sequence
   consumed by the activity gate.
2. Reporter: do not publish an idle selection state while an execution is
   starting for that session.
3. Server: suppress idle reports whose sequence predates the last accepted
   working report.

Choosing among these is an owner decision; no fix was implemented or verified.

## Evidence

- [capture.jsonl](capture.jsonl) — 663 structured records from the reporter and server.
- `evidence/` — prompt texts, waiter logs, screens, native session export,
  startup receipts.
- [result.json](result.json) — classification, timing, limits and fix candidates.
- [build.json](build.json) — pinned toolchain and binary provenance.
