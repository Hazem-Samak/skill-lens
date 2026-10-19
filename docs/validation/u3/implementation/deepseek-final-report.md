All work is terminal. F6 and F7 are corrected, the affected tests and all four gates pass, and the benchmark/mutation receipts were regenerated. Nothing committed or pushed.

## EFFECTIVE_MODEL
`opencode/deepseek-v4.1-flash-free` (variant `high`), same authorized OpenCode implementation session.

## OUTCOME
- **F6 (containment) fixed.** `HomeScreen._set_state_cell` now catches only `CellDoesNotExist` (the documented filtered/stale-row condition). An unexpected `DataTable.update_cell` fault now propagates to the app's existing containment path — sticky failure, `status == "error"`, exit 3, no rendered traceback — instead of being swallowed. Per the instruction, the two other new broad catches in the Home integration were tightened to their documented exceptions: `_clear_table` → `NoMatches`, `_home_screen` → `ScreenStackError`/`UnknownModeError`. The controller was not changed; F1/F2/core safety intact.
- **F7 (evidence boundary) fixed.** The benchmark now records `publication_to_rows_populated_ms` (rows added, before layout/paint) **and** `publication_to_first_usable_ms` (benchmark-only `call_after_refresh` callback after Textual refreshes), plus both startup figures; the accepted-publication timestamp and the controlled 50 ms delay proof are retained. The unsupported "dominated by resolution computation" claim was removed and replaced with a description of the components included; the `Input.Changed` probe deviation is disclosed as not a physical key-to-paint measure. Receipt schema is now `/3`.

## FILES_CHANGED
- Product: `skill_lens/tui/home.py`, `skill_lens/tui/app.py`
- Tests: `tests/test_tui_home.py` (+2 regressions)
- Records: `docs/validation/u3/benchmark_home.py`, `docs/validation/u3/implementation/benchmark_home.json`, `docs/validation/u3/implementation/mutation_gate.py`, `docs/validation/u3/implementation/mutation_gate.json`, `docs/validation/u3/implementation/historical/README.md`, `docs/TUI_U3_WALKTHROUGH.md` (§5/§6/§7/§11), `docs/validation/u3/implementation/deepseek-r2-correction-report.md`
- Preserved (untouched): `docs/validation/u3/implementation/historical/benchmark-home-r2.json` (schema-2 receipt, verified byte-identical to the pre-measurement v2), `historical/benchmark-home-r1.json`, Sol's `coordinator/` + `planning/` records, untracked empty `.path`.

## CHECKS
| Gate | Result |
| --- | --- |
| `pytest --cov=skill_lens` | **1081 passed**, 1 expected case-insensitive-FS skip; **91.08%** combined (floor 90%); `home.py` 90% |
| `mypy` | **Success**, 38 files (strict) |
| `ruff check .` | **All checks passed** |
| `ruff format --check .` | **258 files already formatted** (env-sensitive count; rose 256→258 from two added Markdown files, one of them Sol's) |

Benchmark (`--runs 3 --skills 600`, EXIT 0, schema `/3`, 600 skills, 1,203-entry manifest preserved; medians): capture ~831 ms; publication→rows-populated ~6.5 ms; publication→first-usable ~21.3 ms; startup→first-usable ~857 ms; idle nav ~84.5 ms; text filter ~672 ms; agent filter ~7.61 s; queue per resolved row ~12.7 ms; per-cell ~0.017 ms; slow-capture quit ~42.8 ms; `why_calls == distinct groups == 600`. Probe: 426 pending at start / 132 before quit (nav ~2.05 s, filter ~47 ms, quit ~63 ms). Injected 50 ms delay → 78.4 ms usable (62.2 ms to rows).

Mutation gate (EXIT 0, schema `/3`): 5/5 mutants detected, 5/5 restored copies pass, repo/work `home.py` byte-identical. New case: widening the cell catch back to `except Exception` fails the containment test with `timed out waiting for contained fault`.

## TESTS_ADDED
- `test_home_unexpected_cell_update_fault_routes_to_containment_and_exit3`
- `test_home_state_cell_suppresses_only_expected_stale_row`
- Plus mutation case `cell_update_containment_detects_swallowed_fault`.

## DEVIATIONS_FROM_PLAN
1. F6 review extended to two further broad catches (`_clear_table`, `_home_screen`) per the instruction, narrowed to documented exceptions; controller untouched.
2. Mutation/benchmark receipts schema-bumped to `/3`; old receipts preserved, not relabelled valid.
3. U3 status docs (`FULL_SCREEN_TUI.md`, README, `DEVELOPMENT.md`, `CHANGELOG.md`) remain deferred; the commanded README byte-budget correction stands.
4. Ruff count 256→258 is from added Markdown files, not source changes.

## BLOCKED_ON
Nothing. Awaiting Sol's adjudication and the MiniMax final review before any status-doc flip. No commits, pushes, snapshot/golden regeneration, dependency/lock, or shared-process changes.

### Hashes
- `skill_lens/tui/home.py` `36acf73aa416f7cefa1ae00dff1c9d4e297677a76becb6344e8dae4381393652`
- `skill_lens/tui/app.py` `cb790ad1c5381a8a4f75869c2c07b6960c43ad0430057c7543edd5850be6c411`
- `tests/test_tui_home.py` `bc7f416ab237581e8220743aecad25a30e6bc8fecddf1000147fc28a439ffa59`
- `docs/TUI_U3_WALKTHROUGH.md` `b4d50b28f70a0818d75ff0b8738eb3d538cdc27fdf6b046d0b6d28df89fb8bec`
- `docs/validation/u3/benchmark_home.py` `eda15271400ffa61d6f840a28835ad545e236565dce9a6df4c7b193b9739b35f`
- `docs/validation/u3/implementation/benchmark_home.json` `4b57cb260a4b967262aa99600868281ee11bb1d8e43decf76d15090a01643b9e`
- `docs/validation/u3/implementation/mutation_gate.py` `97e9549dca6b44853a483176c60e254b8a5aeda2794e490f0dce7ce7195c7e22`
- `docs/validation/u3/implementation/mutation_gate.json` `f4b1e6dfc05d5ea260af0ecb1c2dad1bacbc8ace9e6e53fa8576a9b296e00f25`
- `historical/benchmark-home-r2.json` `bb77927823399fa766d00b1e0428528205966f49d71bf945263c7e6c5f1e7cd8`
- `historical/benchmark-home-r1.json` `fb1b669ae190109d2f56927c297c3674b894ed656e020dd1f739461e7dba39c6`
- `historical/README.md` `f0eccb304f5c21c82f36aba6f099a7797931e0380bba286ce444eba09e452a8b`
- Base HEAD `b250576de87820762289b6a6bf9100ce54d6e4be` (nothing committed)
