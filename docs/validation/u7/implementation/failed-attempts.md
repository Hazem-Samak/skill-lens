# U7 implementation attempts retained

This record preserves failed checks and the corrections made. A failed assertion listed as a fixture expectation was a test-authoring correction; it did not reproduce a product defect.

## Test development

| Attempt | Failure | Correction |
| --- | --- | --- |
| First Doctor report fixture expected a `registry_uncited_agent` info finding. | The captured report did not produce that finding in this fixture. | Expected the literal five findings actually emitted by the unchanged CLI and asserted their code/order. |
| First dangling-symlink message expectation used the wrong agent list. | The engine message named `claude, opencode` for the captured scenario. | Updated the expected CLI-backed message. |
| First installer-lock detail expectation used `invalid_json`. | The engine's current detail value is `not_json`. | Updated the literal model assertion. |
| Initial Why ownership race test used timing that did not establish which completion had been handled. | The assertion could run before the old completion reached the UI handler. | Replaced timing inference with controlled start/release events and an explicit `ViewReportComplete` handler event; a report-request spy now proves Doctor dispatches none. |
| Initial fault recovery wait expected controller status `ready`. | Sticky internal-fault state intentionally remains `error` after an explicit successful recovery. | Wait for generation 3 and no pending capture; assert the sticky error and exit 3 remain. |
| First mypy pass rejected a tuple passed to `DataTable.coordinate_to_cell_key`. | The API requires a `Coordinate`. | Imported `Coordinate` and passed the typed value; mypy now passes all 45 source files. |

## Mutation harness attempts

| Attempt | Failure | Correction |
| --- | --- | --- |
| Invoked the mutation harness as `python ...`. | This shell has no `python` command. | Used `.venv/bin/python`. |
| First detail mutant run was rejected by the harness. | The mutant did fail the test; the harness looked for a detail label while the test first failed at `assert long_text in detail`. | Matched the actual failing assertion text. |
| First recomputation mutant setup stopped before tests. | The chosen source excerpt appeared twice. | Made the replacement target the first matching read in controller synchronization, which is the Doctor publish path under test. |
| First basename mutant was rejected by the harness. | The mutant failed as intended by adding a second matching catalog key; the expected-output matcher looked for a later assertion. | Matched the actual “Left contains one more item” assertion result. |
| First empty-report UI run raised `NameError` for `dumps`. | The new test used the production serializer assertion without importing it. | Imported `dumps`; reran the test successfully (1 passed). |
| Parent's first app focus test invoked the Doctor route before deferred Textual focus had landed. | The test checked focus synchronously after `focus()`. | Parent changed the probe to wait for the input to become actually focused; the four parent-authored app checks then passed. |
| First stale-refresh mutant failed on the initial Doctor mount. | It skipped snapshot replacement for every generation, so the test never reached refresh behavior. | Kept generation 1 normal and mutated only later replacement, so the test exercises stale report/JSON after refresh. |
| First owned-token mutant setup found no source match. | The rejected-result guard was an `elif not accepted`, not the different `else` branch initially targeted. | Targeted the exact stale-result branch and replaced its no-op with cancellation of the newer owned request. |
| First stale-generation mutant was rejected by the harness. | The test failed correctly when `jump_from_doctor` returned `True`; only the expected-output string was stale. | Matched `assert not app.jump_from_doctor`. |

The final campaign passed all 16 cases; see [mutation summary](mutations/summary.md) and each case's three retained logs.

## Repository gate attempt

The parent ran the full pinned tree before the two follow-up Doctor tests and app integration tests: `1231 passed, 1 skipped`, all three static checks passed, but observed whole-package branch coverage was **89.60%**, below the unchanged 90% threshold. Pytest returned process exit code 0 while printing the coverage failure, so the run is retained as failed acceptance evidence. Parent-owned full output is retained at [first-full-run/pytest.log](../coordinator/first-full-run/pytest.log); it is not edited here. Follow-up tests now cover scroll/focus across raw and same-finding refresh, removal reset, valid-key stale generation, app route/close guards, rejected Home handoff, and late row events. The subsequent [parent final verification](../coordinator/verification.md) records the fresh full-suite result.
