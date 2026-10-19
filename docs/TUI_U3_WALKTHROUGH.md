# Skill Lens 0.2 — Home Browsing Screen Walkthrough (U3)

> **Status:** Technically accepted by Sol on 2026-10-19 after independent MiniMax
> final R2 PASS. See [acceptance and delivery evidence](validation/u3/acceptance.md).
> Human visual approval and 0.2 publishing are not claimed.
> **Scope:** Full-Screen TUI Assignment U3 (`FULL_SCREEN_TUI.md` §§8.2–8.3, 8.5,
> 9–10, Step 3, §21.7 and §22 U3).
> **Reference Plan:** [docs/plans/2026-10-19-tui-u3-home.md](plans/2026-10-19-tui-u3-home.md)
> @ frozen commit `ce86db945fc44569f3a5cd4f0fb66a111a5d00f2`
> (plan SHA-256 `114f532917d995e7f7980e5425c6f552a440c52aaff57ea18b17777371d5e45a`).
> **Implementing base:** `main` @ `b250576de87820762289b6a6bf9100ce54d6e4be`.

---

## 1. What changed, in plain English

U2 left a placeholder screen that only printed the status line. U3 replaces it
with the real Home screen: a live table of every discovered skill, a metadata
panel that follows the highlighted row, a text filter, an agent filter, an
optional per-agent resolution ("Why") column, and honest loading/empty/error
messages. It stays completely read-only — it browses the frozen snapshot the
worker already captured, and never reads your skill files while you navigate.

The placeholder name `PlaceholderHomeScreen` is kept as a thin subclass of the
new `HomeScreen`, so existing checks that ask "is this the Home screen?" keep
working without maintaining two copies of the screen.

- **`skill_lens/tui/home.py`** (new): the `HomeScreen`, its pure row/preview/
  filter helpers, and the one-agent Why queue.
- **`skill_lens/tui/app.py`**: mounts `HomeScreen` as the default screen, feeds
  Home accepted/rejected report outcomes, and gives Ctrl-C priority so it quits
  even while the filter box has selected text.
- **`tests/test_tui_home.py`** (new): 33 headless tests.
- **`tests/test_tui_app.py`**, **`tests/test_tui_read_only.py`**: focused
  integration and target-preservation extensions only.

No core, model, registry, presentation, render, CLI, dependency or lock changes.
No snapshot or golden was regenerated.

---

## 2. Delivered files and responsibilities

| File | Change |
| --- | --- |
| `skill_lens/tui/home.py` | New (994 lines). `HomeScreen(Screen[None])` with a `DataTable` of skills, a scrollable metadata preview pane, filter `Input`, agent-cycle strip, optional state column, empty/catalog notes and status widgets. Pure helpers build rows, preview text and resolution labels so they are unit-testable without Textual. Literal cells are measured with `Content.cell_length` and columns sized explicitly (DataTable's auto-width cannot measure `Content`). `_set_state_cell` suppresses only the documented missing/stale-cell condition (`CellDoesNotExist`); any other fault reaches the app's containment path (F6). |
| `skill_lens/tui/app.py` | `PlaceholderHomeScreen` becomes a subclass of `HomeScreen`; app default screen is `HomeScreen`; accepted/rejected report handlers call `home.note_report_outcome(...)`; `_update_ui` calls `home.sync_from_controller()`; `ctrl+c` binding gains `priority=True`; `_home_screen` narrows its teardown guard to `ScreenStackError`/`UnknownModeError` (F6). |
| `tests/test_tui_home.py` | New (1692 lines, 33 tests): pure helpers, duplicates/variants, filters/focus/empty states, no-agent view, literal markup, rendered column geometry, focusable/scrolling preview, broken/unresolved rows, Why grouping/counts/cache, races (including the event-controlled rejected-outcome/newer-token invariant), refresh retention, size refusal, generation ordering, a target-specific no-live-read sentinel, and unexpected-cell-fault containment vs. the expected stale-cell condition (F6). |
| `tests/test_tui_app.py` | Added `test_headless_home_screen_reflects_capture`: the mounted default screen is a `HomeScreen` and its table reflects a stubbed capture. |
| `tests/test_tui_read_only.py` | The existing lifecycle test now also drives Home filter/agent/navigation while the read-only AST guard and mutation suite are unchanged in strength. |
| `docs/TUI_U3_WALKTHROUGH.md` | This document. |
| `docs/validation/u3/benchmark_home.py` | Reproducible synthetic benchmark (600 skills, mounted Home/DataTable, real Pilot events). |
| `docs/validation/u3/implementation/benchmark_home.json` | Machine-readable benchmark receipt. |
| `docs/validation/u3/implementation/mutation_gate.py` | Reproducible new-gate mutation harness on a disposable source copy. |
| `docs/validation/u3/implementation/mutation_gate.json` | Machine-readable mutation receipt. |

Environment: Python 3.11.16, Textual 8.2.8, macOS-27.0.1-arm64.

---

## 3. Design decisions worth recording

- **Literal file-derived text.** Names, descriptions, paths and empty-state text
  render with `Content.from_text(value, markup=False)` (or `Static(markup=False)`).
  A skill literally named `[bold]x[/bold]` shows the brackets, not bold. This
  avoids any Rich import in `tui/` — the read-only guard forbids it.
- **Library-provided navigation.** Textual's `DataTable` owns arrow-key/Enter
  cursor handling and `Input` owns printable typing, so `q/r/a/j/k` typed into
  the filter box are text, not commands. No custom key engine was added.
- **Ctrl-C priority.** The app-level `ctrl+c` binding is `priority=True` so it
  quits even while the filter input owns focus and has a selection. This is the
  plan's explicit "quit from any focus" requirement.
- **Responsive layout without `@media`.** Textual 8.2.8 rejects `@media` CSS, so
  the screen toggles a `.narrow` class in `on_resize` to stack the two panes at
  small widths. Verified at 100×30 and 60×24.
- **Canonical identity everywhere.** Row keys are
  `discovery.canonical_key` (canonical path, or entrypoint path for a broken
  shortcut). Selection, filtering and preview all key off that, never a name or
  row number, so same-name copies stay distinct.
- **Why is grouped by the real lookup name.** Groups use the pure
  `resolver.lookup_name_for_entry(entry, agent)` helper against the captured
  index/registry, never `ScanEntry.name`, because aliases and frontmatter means a
  display name and a lookup name can differ.
- **One owned Why slot.** The screen holds at most one in-flight token, copied
  from `controller.active_requests["why"]` after dispatch (including its request
  id). It peeks `get_cached_report` before requesting, applies one name-wide
  report to every visible copy in the group, updates completed cells with
  `DataTable.update_cell`, and clears its token when the controller invalidates
  it. `request_view` cancels prior work even on a cache hit, so a cache peek is
  mandatory before dispatch.
- **Host callbacks for reports.** The app's existing accepted/rejected report
  handlers now notify Home by request id, generation, view and arguments. A
  rejected outcome only wakes the queue — it never renders report data or an
  error, and never clears a newer owned token. An accepted failure marks that
  group unavailable in addition to the sticky panel and exit 3, and is not
  retried in the same pass.
- **`on_mount` sync.** Home calls the host `_update_ui()` after its own sync so
  the status line is correct even when the app's `on_mount` ran before the screen
  was queryable.

---

## 4. Behavior verified by headless tests

The 33 tests in `tests/test_tui_home.py` assert rendered rows/preview/counts, not
just private helper return values:

- **Rows and identity:** table order follows `snapshot.scan.skills`; one row per
  canonical installation; name, shared scope label and parse mark (`*` valid,
  `x` invalid) shown; duplicate same-name copies and distinct variant labels
  stay separate and selectable; broken/unresolved rows keep entrypoint identity.
- **Preview:** captured name, description, display path, scope, agent names,
  hash, parse status, captured variant label and health explanation; missing
  description gets a placeholder; markup-looking values render literally.
- **Filters and focus:** case-insensitive substring filter over name+description;
  `Enter` returns to the list, `Escape` clears and returns focus; `q/r/a/j/k`
  are text in the input; Ctrl-C quits; empty catalog and no-match are distinct
  messages; text and agent filters combine; agent cycle is deterministic and
  combined with text filter restricts rows; no-agent view keeps All with an
  explanation.
- **Why correctness and counts:** no agent filter makes zero Why calls; an agent
  filter makes exactly M calls for M distinct lookup names; same-name copies
  share one report but show their own states; grouping uses the actual lookup
  name (tested with agent alias/frontmatter differences); the no-live-read
  sentinel proves navigation/filtering never touch the filesystem after capture.
- **Races and liveness:** selection change re-drives the queue immediately and
  rejects the late result even while the cancelled worker stays blocked; a
  superseded request's *rejected* outcome delivered while a newer request is
  still blocked in its worker leaves the newer owned token and the controller's
  active request untouched, and the queue still drains (an event-controlled
  regression: no bare sleep establishes the ordering); a cache
  peek does not cancel an unrelated active request; agent change clears marks and
  requests the new agent; an accepted failure marks the group unavailable without
  a retry loop; unmount discards a late report; refresh retains old rows, then a
  replacement rebuilds and clears stale marks; a failed refresh retains rows and
  exits 3; a size refusal retains rows and exits 0; refresh 3 wins over stale 2.
- **Target preservation:** the read-only lifecycle test keeps fixture bytes,
  modes and symlink targets identical across capture, navigation, filtering,
  report completion, refresh and quit, using synthetic HOME isolation.
- **Rendered geometry (candidate-R1 correction F1):** column widths are asserted
  from the compositor's `Column.get_render_width`, not just stored row values,
  and the actual compositor text is asserted to carry the full long name, a
  markup-looking literal (uninterpreted), and a state label wider than the
  initial column. Verified at 100×30 and 60×24.
- **Keyboard preview access (F2):** `Tab` and `Shift-Tab` both reach a focusable
  `VerticalScroll` preview pane; the compatibility `#preview-pane` `Static` stays
  a non-focusable `Static`. At 60×24 the clipped `Variant:` metadata is proven
  absent before scrolling and present after, with the description reachable at
  the end; at 100×30 the whole preview is visible without scrolling.
- **Target-read sentinel (F5):** navigation and agent filtering are driven while
  `Path.open/read_text/read_bytes/resolve` and `builtins.open` are wrapped to
  raise only for paths under the synthetic target home, so a direct read of a
  target skill file cannot hide behind a high-level helper patch.
- **Unexpected cell-update containment (F6):** with `DataTable.update_cell`
  patched to raise `RuntimeError`, selecting an agent routes the fault to the
  app's containment path — sticky failure (`controller.status == "error"`), exit
  3, and no rendered traceback — instead of being swallowed. A companion test
  proves the documented stale/missing-row condition (`CellDoesNotExist`) is still
  tolerated quietly.

---

## 5. Verification gates

Sol independently reran these gates after the final-R1 test-only correction
(`.venv`, macOS/Python 3.11); logs are under
`docs/validation/u3/coordinator/review-ready-r2/`:

| Gate | Result |
| --- | --- |
| `.venv/bin/pytest --cov=skill_lens` | 1082 passed, 1 expected case-insensitive-filesystem skip; 91.16% combined (floor 90%). `skill_lens/tui/home.py` measured at 91%. |
| `.venv/bin/mypy` | Success, no issues in 38 source files (strict). |
| `.venv/bin/ruff check .` | All checks passed. |
| `.venv/bin/ruff format --check .` | All files already formatted (the file count is deliberately not restated here; this Ruff build also covers Markdown, so the count tracks the evidence inventory rather than source). |

Baseline before this work (unchanged product) was 1048 passed, 1 skip, 91.11%
combined.

This gate-execution inventory is historical: the counts and percentages are what
the four commands reported on the final candidate tree at the moment they were
last run for this batch, not a live property of the tree now. Later evidence-only
edits — a new test, a regenerated receipt, this document — can change the Ruff
file count without touching one line of product source, so the counts here are a
timestamped log rather than a claim about the current file set.

---

## 6. Benchmark (`docs/validation/u3/benchmark_home.py`)

The harness creates 600 standard-library synthetic skills outside the checkout,
mounts the real `HomeScreen`/`DataTable` under a per-run temporary HOME/XDG, and
drives real Pilot key/input events; it asserts row/cursor outcomes. Every run is
sandboxed and restored on success *and* failure, an independent before/after
byte + mode + symlink/inventory manifest of the 1,203 fixture entries is
compared, and a fail-closed check proves absolute system roots (e.g. `/etc/codex`)
are never allowed. The numbers live in the immutable named receipt —
`implementation/benchmark_home.json`, schema `skill-lens/u3-benchmark-home/3`
(three clean runs plus the active-resolution probe and the injected-delay run,
median and max per measure). This document deliberately does not copy the values:
they move between runs on one machine, so a table of numbers here would go stale
against the receipt it cites. The receipt records, per measure, `capture_ms`,
`publication_to_rows_populated_ms`, `publication_to_first_usable_ms`,
`startup_to_rows_populated_ms`, `startup_to_first_usable_ms`, `navigation_ms`,
`text_filter_ms`, `agent_filter_ms`, `amortized_queue_ms_per_resolved_row`,
`per_cell_update_ms` and `slow_capture_quit_ms`; the active-resolution probe run
records `active_navigation_ms`, `active_filter_ms`, `active_quit_ms`,
`pending_at_start` and `pending_before_quit`; the injected-delay run records
`rebuild_delay_ms` and both publication boundaries.

Two publication boundaries are recorded honestly.
`publication_to_rows_populated_ms` ends when the instrumented Home rebuild has
added every row, before Textual lays out and paints.
`publication_to_first_usable_ms` ends at a benchmark-only `call_after_refresh`
callback that runs after the screen has been refreshed; that is the figure to read
as time-until-usable. The gap between the two is the layout/paint cost the earlier
population-only boundary omitted.

The active-resolution probe replays navigation, a filter and a prompt Ctrl-C quit
while hundreds of groups are still resolving; the receipt records the pending
counts at probe start and just before quit for that run. A controlled injected
50 ms rebuild delay is reflected in the injected-delay run's
`publication_to_first_usable_ms`, proving that boundary tracks real work.

Why-call count is 600 = one per distinct lookup name for that agent, and the
clean pass asserts `why_calls ==` distinct lookup groups with no cell left
pending. **These are single-machine measurements, not a release target**; no
performance threshold is invented. The agent-filter number is wall-clock for the
whole serial queue — it folds together `snapshot_why` worker execution,
worker/message scheduling, and the per-group Home cell updates and redraws; the
harness does not attribute the total to any one component. The navigation figure
is a `Pilot.press` round trip, which waits for the app's event queues to drain
under load, so it is a coarse upper bound rather than pure user-perceived
latency; the responsive Ctrl-C quit is the cleanest signal. The active-filter
figure is driven through `Input.Changed` rather than a physical key press, so it
is not a physical key-to-paint latency.

---

## 7. Mutation gate for the new safety/liveness guards

Run on a disposable copy of the source tree with `PYTHONPATH` pointing at the
copy, with before/after hashes of the real checkout recorded (receipt:
`implementation/mutation_gate.json`, schema
`skill-lens/u3-mutation-gate/4`; the superseded five-case receipt is preserved at
`implementation/historical/mutation-gate-r1.json`). The harness takes an optional
`--out PATH` so a reviewer can write the receipt outside the checkout. It reuses
the U2 guard framework rather than rebuilding it; each case records the mutant's
return code, the detected pattern and the failing assertion text:

1. A planted `import rich` in `home.py` is detected by the read-only AST guard
   (pattern `rich`); the restored copy passes.
2. A planted live `paths.home()` probe in `sync_from_controller` is detected by
   the no-live-read sentinel (pattern `Forbidden live filesystem probe`); the
   restored copy passes.
3. A planted direct `Path(...).read_text()` of a synthetic target skill file in
   `_update_preview` is detected by the target-specific sentinel (pattern
   `Forbidden synthetic-target filesystem read`) — the read the high-level
   helper patches never saw; the restored copy passes.
4. Suppressing the post-selection and post-report `_drive()` re-drive is
   detected by the event-controlled liveness test (pattern `timed out waiting
   for second group and re-driven first group`); the restored copy passes.
5. Widening `_set_state_cell`'s `except CellDoesNotExist` to `except Exception`
   is detected by the containment test, which then waits forever for the sticky
   failure that no longer happens (pattern `timed out waiting for contained
   fault`); the restored copy passes.
6. Replacing the rejected-outcome branch's `pass` with `self._inflight = None`
   is detected by the event-controlled race test — an old rejected outcome then
   clears the newer owned token (pattern `the newer owned Why token was cleared
   by a rejected outcome`); the restored copy passes. This is the case the
   final-R1 review found missing.

All unmodified controls pass, all six mutants die with a real failing assertion, and
the repository and disposable work copy end byte-identical: `home.py` SHA-256
`36acf73aa416f7cefa1ae00dff1c9d4e297677a76becb6344e8dae4381393652` before and
after. The liveness case also hardened the test's blocked worker to a 30 s
release (far beyond the 5 s wait) so a stalled queue is reported as the intended
timeout instead of racing the release.

---

## 8. Limitations and boundaries

- **Read-only.** Skill Lens never writes, moves or deletes user skills; Home only
  presents the frozen snapshot.
- **Single UI Why slot.** Home deliberately owns one in-flight resolution request.
  U4 (the dedicated Why screen) will contend with Home for the controller's one
  active `why` request. That contention is **deferred to the U4 plan** and is not
  solved here; Home's contract is only that it never overwrites newer work and
  re-drives its own queue after invalidation.
- **Cancellation is cooperative.** An in-progress blocking kernel read cannot be
  aborted mid-read; workers stop at the next checkpoint. Quit stays prompt because
  teardown does not join worker threads.
- **Source guard limits.** The AST guard covers named imports/calls and aliases;
  it does not prove every indirect dependency is read-only.
- **Human visual approval.** Evidence here is technical and headless. No human
  terminal-screenshot approval is claimed, and no 0.2 publishing is implied.

---

## 9. Review status

MiniMax final R2 returned PASS with no blockers. Sol verified that all 1,138
protected files, HEAD and Git status were unchanged during review, accepted the
frozen U3 contract, and updated the four authorized current-status documents.
The full reports and disposition are in `docs/validation/u3/coordinator/`;
[acceptance](validation/u3/acceptance.md) records checks and remaining limits.

Nonblocking follow-ups for U4: exercise the identity-matching rejected-request
branch (`home.py:495–499`, still uncovered); revisit the unused `error` parameter
and U2-era package header/exports. No unreachable-code claim or known product
defect is being deferred. Read-only reviewers must run the mutation harness with
`--out` pointing outside the checkout; its default intentionally regenerates the
implementer's receipt. Product and test source are unchanged after R2 review.

---

## 10. Pre-council correction batch (candidate R1 → R2)

The coordinator reproduced five defects that the passing R1 tests did not catch
and returned them as one batched correction. All five are fixed inside the
authorized files; no core, controller, dependency or lock file changed.

- **F1 — literal cell sizing (was blocking).** `DataTable` auto-width measures
  with Rich's `__rich_measure__`, which `Content` does not expose, so literal
  cells stayed clipped at the header width (`a-lo`, `Globa`). Columns are now
  sized explicitly from `Content.cell_length` at rebuild, and the `State` column
  grows in place when a longer label (e.g. `AMBIGUOUS`) arrives — no per-result
  table rebuild. GENUINELY long data scrolls horizontally, which is the honest
  behaviour. Proven by compositor geometry/text assertions at 100×30 and 60×24.
- **F2 — keyboard preview access (was blocking).** The preview `Static` was not
  focusable, so a narrow pane's lower metadata (hash/parse/variant/description)
  could not be read with the keyboard. The pane is now a focusable
  `VerticalScroll` (`#preview-scroll`) wrapping the unchanged `#preview-pane`
  `Static`, so `Tab`/`Shift-Tab` reach it and `down`/`end` scroll it. Verified at
  60×24 (clipped then revealed) and 100×30 (fully visible).
- **F3 — benchmark sandbox escape (was blocking).** The R1 harness set the
  sandbox once and cleared it in the first run's `finally`, so runs 2/3 had a
  synthetic `HOME` with absolute system roots allowed. Every run is now isolated
  (sandbox + `HOME`/`XDG_CONFIG_HOME` set per run, restored on success *and*
  failure) with a fail-closed `_absolute_roots_allowed` assertion, a directory
  guard that rejects any concrete directory outside the synthetic home, and an
  independent before/after byte+mode+symlink manifest of the fixtures. The
  superseded R1 receipt is preserved at
  `implementation/historical/benchmark-home-r1.json` and explicitly labelled
  invalid and unsafe; it is **not** relabelled valid.
- **F4 — measurement boundaries (was blocking).** `publication → first list` is
  now measured from a real accepted `accept_capture` on the UI thread to the
  instrumented Home rebuild that first carries every row, not from a near-zero
  polling predicate; full startup-to-first-list is recorded too. A controlled
  injected rebuild delay is reflected in the measured interval, proving the
  boundary is real. The queue number is now labelled
  `amortized_queue_ms_per_resolved_row`, a separate real `per_cell_update_ms` is
  measured, and navigation/filter/quit are measured while hundreds of resolutions
  are genuinely still pending (the probe records `pending_at_start` and
  `pending_before_quit`). The clean pass asserts `why_calls ==`
  distinct lookup groups and non-pending rendered states. The confirmed
  redundant all-rows state-cell rewrite (`_refresh_visible_metadata`) was removed
  from the same-generation sync path; no other behaviour changed.
- **F5 — guard evidence (was blocking acceptance gap).** The no-live-read test now
  wraps `Path.open/read_text/read_bytes/resolve` and `builtins.open` with a
  sentinel that raises only for paths under the synthetic target home, and the
  mutation gate plants a direct target `read_text` that it catches. A second new
  mutation suppresses the post-selection *and* post-report re-drive; it is caught
  by the event-controlled liveness test, whose blocked worker was lengthened to
  30 s so a stalled queue reliably reports the intended timeout. Existing
  guards/tests are unchanged in strength.

---

## 11. Second pre-council correction batch (candidate R2 → R3)

The coordinator reproduced two further defects on the corrected R2 candidate
while confirming F1/F2 fixed. Both are fixed inside the authorized files; still
no core, controller, dependency or lock change, and F1/F2/core safety are
untouched.

- **F6 — unexpected rendering faults were swallowed (was blocking).**
  `_set_state_cell` wrapped `DataTable.update_cell` in `except Exception`, so a
  synthetic `RuntimeError` from a real cell update was discarded: the app stayed
  `Ready`, `controller.failed` stayed `False`, and Ctrl-C exited `0` instead of
  the existing sticky-failure/exit-3 contract. The catch is now
  `except CellDoesNotExist` — the documented filtered/stale-row condition — so
  every other fault propagates to the app's containment path. The two other new
  broad catches in the integration were tightened the same way: `_clear_table`
  now catches only `NoMatches`, and `_home_screen` only
  `ScreenStackError`/`UnknownModeError` (teardown). Two regressions were added:
  the fault path asserts sticky failure, `status == "error"`, exit 3 and no
  rendered traceback; the companion test asserts the genuine stale-row case is
  still tolerated quietly. The controller was not changed.
- **F7 — measurement wording overstated the boundary and causality (was
  blocking).** The R2 harness marked `first_list` immediately after
  `_rebuild_table` populated rows and called it laid-out/paint/first-usable. It
  now records two honest boundaries: `publication_to_rows_populated_ms` (rows
  added, before layout/paint) and `publication_to_first_usable_ms` (a
  benchmark-only `call_after_refresh` callback that runs after Textual refreshes
  the screen), plus both full-startup figures. The controlled 50 ms delay is
  preserved and is asserted against the usable interval. The unsupported claim
  that the queue wall time is "dominated by resolution computation" was removed
  and replaced with a description of the components the number includes (no new
  causal claim). The active-filter probe still drives `Input.Changed` rather than
  a physical key press, and the text now says so explicitly and no longer implies
  a measured physical key-to-paint latency. The superseded schema-2 receipt is
  preserved at `implementation/historical/benchmark-home-r2.json` and labelled
  superseded, not invalid. The benchmark receipt is now schema `/3`.
- **Mutation coverage.** A fifth mutation widens the F6 catch back to
  `except Exception`; the containment test then fails with
  `timed out waiting for contained fault`. The gate is schema `/3`, 5/5 mutants
  detected, 5/5 restored copies pass, repo/work `home.py` byte-identical
  (SHA-256 `36acf73a…93652`).

---

## 12. Third (test-only) correction batch (final-R1 evidence gap)

The final independent review found no behavioural defect: an independent probe
confirmed the shipped source satisfies the plan-mandated invariant that a
rejected outcome for a superseded request must not clear a newer owned token.
The gap was **evidence**, not behaviour. The shipped race test released the old
worker only after the queue was idle, so a mutant that cleared the owned token on
any rejected outcome survived the entire test suite and the five-case gate. This
batch closes that gap. No product file changed: `home.py` and `app.py` are
byte-identical to the reviewed candidate (`home.py` SHA-256 `36acf73a…93652`).

- **New regression (test-only).**
  `tests/test_tui_home.py::test_home_rejected_old_outcome_preserves_newer_owned_token`
  is an event-controlled race: the first request is held in its worker, the
  selection moves so it is cancelled and a newer request is dispatched and also
  held, then only the *old* worker is released, so its rejected outcome is
  delivered while the newer request is still owned and in flight. It asserts the
  newer owned token **object** is preserved (not merely non-`None`), that the
  controller still tracks the newer request, and that the queue drains once the
  newer request is released — proving the superseded group was left resolvable
  rather than stranded on `pending`. Ordering is established by threading events,
  never by a bare sleep, and both release events are set in `finally`.
- **Sixth mutation category.** `mutation_gate.py` now replaces the
  rejected-outcome branch's `pass` with `self._inflight = None`; the new test
  dies on the intended assertion and the restored copy passes. The gate is schema
  `skill-lens/u3-mutation-gate/4`, 6/6 mutants detected, 6/6 restored copies
  pass, repo/work `home.py` byte-identical. The superseded five-case receipt is
  preserved at `implementation/historical/mutation-gate-r1.json` and labelled
  superseded, not invalid; the coordinator's immutable review-ready evidence was
  not touched.
- **`--out` flag.** The harness takes an optional `--out PATH` so a reviewer can
  write the receipt outside the checkout; verified by writing one receipt to a
  temp directory and regenerating the in-repo receipt with the same command.
- **Documentation truthfulness (§5, §6).** The current verification summary no
  longer restates a volatile Ruff file count (this Ruff build also covers
  Markdown, so the count tracks the evidence inventory rather than source), and
  the benchmark section links the immutable named receipt instead of copying
  numbers that drift between runs. Both are wording changes; no benchmark was
  re-run because the product and the benchmark itself are unchanged.
