# Second pre-council correction — implementer report (candidate R2 → R3)

## EFFECTIVE_MODEL
`opencode/deepseek-v4.1-flash-free` (variant `high`), Full access / default
interaction — the same authorized OpenCode implementation session.

## OUTCOME
Both reproduced defects from `docs/validation/u3/coordinator/candidate-r2-findings.md`
are corrected inside the authorized files; F1/F2/core safety are unchanged. No
commit, push or delegation.

- **F6 fixed.** `HomeScreen._set_state_cell` now catches only
  `CellDoesNotExist`, the documented filtered/stale-row condition, so an
  unexpected `DataTable.update_cell` fault propagates to the app's existing
  containment path (sticky failure, exit 3, no terminal traceback). The two other
  new broad catches in the Home integration were tightened to their documented
  exceptions (`_clear_table` → `NoMatches`; `_home_screen` →
  `ScreenStackError`/`UnknownModeError`). The controller was not changed. Two
  regressions added: the unexpected-fault containment route and the still-quiet
  expected stale-row case.
- **F7 fixed.** The benchmark now records two honest boundaries —
  `publication_to_rows_populated_ms` (rows added, before layout/paint) and
  `publication_to_first_usable_ms` (a benchmark-only `call_after_refresh`
  callback after Textual refreshes the screen) — retaining the real
  accepted-publication timestamp and the controlled 50 ms delay proof. The
  unsupported "dominated by resolution computation" attribution was removed and
  replaced with a description of the components the wall time includes; the
  active-filter `Input.Changed` deviation is disclosed as not a physical
  key-to-paint measure. Receipt schema is now `/3`.

## FILES_CHANGED
Modified (product):
- `skill_lens/tui/home.py` — F6: narrow `_set_state_cell` catch to
  `CellDoesNotExist` (import `from textual.widgets.data_table import
  CellDoesNotExist`), narrow `_clear_table` to `NoMatches`.
- `skill_lens/tui/app.py` — F6: `_home_screen` catches only
  `(ScreenStackError, UnknownModeError)`.

Modified (tests):
- `tests/test_tui_home.py` — +2 F6 regressions.

Modified (records):
- `docs/validation/u3/benchmark_home.py` — F7 boundary split + wording; schema /3.
- `docs/validation/u3/implementation/benchmark_home.json` — regenerated, schema /3.
- `docs/validation/u3/implementation/mutation_gate.py` — +case 5; schema /3.
- `docs/validation/u3/implementation/mutation_gate.json` — regenerated.
- `docs/validation/u3/implementation/historical/README.md` — labels r2 superseded
  (not invalid) and r1 invalid/unsafe.
- `docs/TUI_U3_WALKTHROUGH.md` — corrected counts, benchmark boundaries/table,
  gates, and §11 (F6/F7 record). §10 (F1–F5) left as history.

Preserved: `docs/validation/u3/implementation/historical/benchmark-home-r2.json`
(the schema-2 receipt, copied before measurement; verified byte-identical to the
then-current v2 receipt) and `historical/benchmark-home-r1.json` (invalid/unsafe).
Sol's `docs/validation/u3/coordinator/` and `planning/` records were not edited;
the untracked empty `.path` is preserved.

## CHECKS
Run on the final tree (`.venv`, macOS/Python 3.11, Textual 8.2.8):

| Gate | Result |
| --- | --- |
| `.venv/bin/pytest --cov=skill_lens` | **1081 passed**, 1 expected case-insensitive-FS skip; **91.08%** combined (floor 90%); `skill_lens/tui/home.py` 90% |
| `.venv/bin/mypy` | **Success**, 38 source files (strict) |
| `.venv/bin/ruff check .` | **All checks passed** |
| `.venv/bin/ruff format --check .` | **258 files already formatted** (environment-sensitive count) |

Focused: the five F1/F2/F6 tests pass repeatedly (3×); the Home/App/read-only
suites pass 198/198.

Benchmark (`--runs 3 --skills 600`, EXIT 0, schema `/3`, 600 skills, 1,203-entry
manifest preserved; medians):
capture ~831 ms; publication→rows-populated ~6.5 ms; publication→first-usable
~21.3 ms; startup→first-usable ~857 ms; idle navigation ~84.5 ms; text filter
~672 ms; agent filter ~7.61 s; whole-queue per resolved row ~12.7 ms; per-cell
state update ~0.017 ms; slow-capture quit ~42.8 ms; `why_calls == distinct
lookup groups == 600`. Probe had 426 pending at start / 132 before quit (nav
~2.05 s, filter ~47 ms, quit ~63 ms). Controlled 50 ms delay → 78.4 ms
publication→first-usable (62.2 ms to rows populated).

Mutation gate (`mutation_gate.py`, disposable copy, `PYTHONPATH` redirect;
EXIT 0, schema `/3`): 5/5 mutants detected (rich import; `paths.home()` probe;
direct synthetic-target read; suppressed re-drive; widened cell catch), 5/5
restored copies pass, 5/5 controls pass, repo/work `home.py` byte-identical.

## TESTS_ADDED
2 tests in `tests/test_tui_home.py`:
- `test_home_unexpected_cell_update_fault_routes_to_containment_and_exit3`
- `test_home_state_cell_suppresses_only_expected_stale_row`
Plus a fifth mutation case (`cell_update_containment_detects_swallowed_fault`) in
`docs/validation/u3/implementation/mutation_gate.py`.

## DEVIATIONS_FROM_PLAN
1. **F6 review extended beyond the one flagged line.** Per the instruction to
   review other new broad `Exception` catches in the Home integration, I also
   narrowed `_clear_table` (`NoMatches`) and `_home_screen`
   (`ScreenStackError`/`UnknownModeError`). Both are the documented expected
   conditions; the controller and all other lifecycle behavior are unchanged.
2. **Mutation/receipt schema bumped to `/3`** to record the added containment
   case; old receipts are preserved, not relabelled.
3. **No status docs flipped.** `FULL_SCREEN_TUI.md`, `README.md`,
   `DEVELOPMENT.md` and `CHANGELOG.md` U3 status lines remain deferred to
   acceptance (the already-commanded README byte-budget correction stands).
4. Ruff's file count rose 256 → 258 across this batch because this Ruff build
   also covers Markdown, and two Markdown files were added: the coordinator's
   `candidate-r2-findings.md` (256 → 257) and this batch's implementation report
   (257 → 258). No product source file was added.

## BLOCKED_ON
Nothing. Awaiting Sol's adjudication and the MiniMax final review before any U3
status-doc flip. No commits, pushes, snapshot/golden regeneration, dependency or
lock changes, or shared-process changes.

### Hashes
- `skill_lens/tui/home.py` — `36acf73aa416f7cefa1ae00dff1c9d4e297677a76becb6344e8dae4381393652`
- `skill_lens/tui/app.py` — `cb790ad1c5381a8a4f75869c2c07b6960c43ad0430057c7543edd5850be6c411`
- `tests/test_tui_home.py` — `bc7f416ab237581e8220743aecad25a30e6bc8fecddf1000147fc28a439ffa59`
- `docs/TUI_U3_WALKTHROUGH.md` — `b4d50b28f70a0818d75ff0b8738eb3d538cdc27fdf6b046d0b6d28df89fb8bec`
- `docs/validation/u3/benchmark_home.py` — `eda15271400ffa61d6f840a28835ad545e236565dce9a6df4c7b193b9739b35f`
- `docs/validation/u3/implementation/benchmark_home.json` — `4b57cb260a4b967262aa99600868281ee11bb1d8e43decf76d15090a01643b9e`
- `docs/validation/u3/implementation/mutation_gate.py` — `97e9549dca6b44853a483176c60e254b8a5aeda2794e490f0dce7ce7195c7e22`
- `docs/validation/u3/implementation/mutation_gate.json` — `f4b1e6dfc05d5ea260af0ecb1c2dad1bacbc8ace9e6e53fa8576a9b296e00f25`
- `docs/validation/u3/implementation/historical/benchmark-home-r2.json` — `bb77927823399fa766d00b1e0428528205966f49d71bf945263c7e6c5f1e7cd8`
- `docs/validation/u3/implementation/historical/benchmark-home-r1.json` — `fb1b669ae190109d2f56927c297c3674b894ed656e020dd1f739461e7dba39c6`
- `docs/validation/u3/implementation/historical/README.md` — `f0eccb304f5c21c82f36aba6f099a7797931e0380bba286ce444eba09e452a8b`
- Base HEAD — `b250576de87820762289b6a6bf9100ce54d6e4be` (nothing committed)
