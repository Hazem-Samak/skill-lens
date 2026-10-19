# Corrected-candidate coordinator findings

The original F1/F2 defects are reproduced as fixed in the mounted 60×24 Home:
Name width 19 for `a-long-literal-name`, Scope width 6 for Global; the full name
appears in compositor strips. Tab focuses `preview-scroll`; its scroll range is
37 rows for a long description, and End reveals description text. No product
source was modified by the coordinator probes.

Direct corrected-tree gates: 1079 passed, one expected case-insensitive-filesystem
skip, 91.05% combined; strict mypy clean on 38 files; Ruff lint/format clean,
256 Python files. These gates are evidence, not acceptance.

## F6 — unexpected rendering faults are swallowed

`HomeScreen._set_state_cell` catches `Exception` around `table.update_cell`.
Sol mounted a synthetic one-skill Home, patched `DataTable.update_cell` to raise
`RuntimeError('unexpected cell update fault')`, selected an agent and let its
report complete. Observed `controller.failed == False`, status still
`Ready: 1 skills discovered`, and Ctrl-C returned exit 0. This violates the
existing unexpected-internal-fault/exit-3 contract. Only a demonstrated expected
stale/missing-cell condition may be suppressed; unrelated errors must reach the
app's existing containment path. Add a regression proving sticky failure and
exit 3 without a terminal traceback. Do not change the controller contract.

## F7 — measurement wording still overstates the boundary and causality

The revised benchmark records `first_list` immediately after `_rebuild_table`
populates rows. It does not await Textual layout/refresh/paint, yet the harness
docstring and walkthrough call this a laid-out/paint interval. Record an actual
post-refresh usable-list point (a benchmark-only callback is sufficient), or
label row-population separately and add the required first-usable measure.
Keep the controlled delay proof.

The harness limitations and walkthrough also claim the queue is dominated by
resolution computation, although no attribution of compute versus scheduling
and UI work was measured. Remove this unsupported attribution; describe the
components included in the wall-clock number. Preserve numeric receipts and
label their actual boundaries rather than silently relabelling old evidence.

The disclosed active-filter probe uses Input.Changed rather than a Pilot key
press; keep that limitation explicit. It does not justify claiming a measured
physical key-to-paint latency. No new machine-speed threshold is requested.
