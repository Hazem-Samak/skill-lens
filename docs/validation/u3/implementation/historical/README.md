# Superseded U3 receipts

## `benchmark-home-r1.json` — invalid and unsafe

The candidate-R1 receipt. It is kept for history and must not be cited as valid
evidence.

Why it is invalid (coordinator finding F3):

- The harness set the sandbox once and cleared it in the first run's `finally`, so
  runs 2 and 3 ran with a synthetic `HOME` while absolute system roots (for
  example `/etc/codex`) were allowed and could be read live.
- `publication_to_first_list_ms` measured a near-zero polling predicate rather
  than the accepted-publication-to-render interval.

## `benchmark-home-r2.json` — superseded, wording too strong

The candidate-R2 receipt (schema `skill-lens/u3-benchmark-home/2`). It was
produced by the per-run-isolated harness and its sandbox, manifest and fail-closed
guards are sound, so it is *not* marked invalid. It is superseded only because its
metric boundary and wording were too strong (coordinator finding F7):

- It marked "first list" immediately after `_rebuild_table` populated rows, before
  Textual laid out and painted the screen, yet its documentation described that as
  a laid-out/paint/first-usable interval.
- It attributed the serial queue wall time to resolution computation without
  measuring that attribution.

The current receipt is `../benchmark_home.json` (schema
`skill-lens/u3-benchmark-home/3`), produced by the per-run-isolated harness with a
fail-closed absolute-root assertion, a discovery directory guard and an
independent before/after fixture byte + mode + symlink/inventory manifest. It
separates row population (`publication_to_rows_populated_ms`) from a
benchmark-only post-refresh usable point (`publication_to_first_usable_ms`) and
describes the queue number by the components it includes rather than attributing
it to any one of them.

## `mutation-gate-r1.json` — superseded, five-case receipt

The mutation-gate receipt the final-R1 independent review inspected (schema
`skill-lens/u3-mutation-gate/3`, five mutant categories). It is kept for history
and is honest for what it measured, but it is superseded and **must not be cited
as the current gate evidence**: it had no case covering the rejected-outcome /
newer-owned-token invariant (`skill_lens/tui/home.py` rejected branch), so a
mutant that cleared the owned token on any rejected outcome survived it
(final-R1 blocker, test-only).

The current receipt is `../mutation_gate.json` (schema
`skill-lens/u3-mutation-gate/4`): the same five categories plus a sixth that
plants `self._inflight = None` in the rejected-outcome branch and is caught by
`tests/test_tui_home.py::test_home_rejected_old_outcome_preserves_newer_owned_token`.
Both receipts were produced on a disposable copy with before/after hashes of the
real checkout's `home.py`.
