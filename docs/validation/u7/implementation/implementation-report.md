# U7 Doctor implementation report

## Outcome

The TUI now has a read-only Doctor screen that displays the already-published report, exposes its canonical JSON, and can select a matching Home row using only the captured session's path map. Doctor opens from Home with `h`; entering it does not run diagnostics or start a Doctor worker. This is implementation evidence only, not a release decision.

## Model and effort

The requested native model was **gpt-6-luna at xHigh**. The execution surface does not expose independent model-routing or effort readback, so I can report the requested configuration but cannot claim runtime routing was independently verified.

## Behavior implemented

- Home `h` opens one Doctor screen only from ordinary Home with the skill table focused. Filter typing, raw Home JSON, a covered Home, and repeated opens cannot create another screen. Back returns to Home without changing its filters or valid selection.
- Doctor reads the `DoctorReport` from one published `SessionSnapshot`. It preserves the report's tuple order and all model fields, gives repeated equal findings distinct generation/value/occurrence identities, shows literal full details, distinguishes an empty report from an info-only report, and keeps missing session data honest.
- The findings table and scrollable detail pane adapt to wide and narrow terminal sizes. `Tab`/`Shift+Tab`, Up/Down and `j`/`k` follow focus; raw JSON hides and disables table navigation, shows the existing model serializer output, and restores valid focus and scroll state.
- Enter uses only captured display-path reverse matches, entrypoint aliases, hits, canonical paths and captured same-location pairs. It rejects zero or ambiguous matches with a local notice. A valid target queues a bounded Home handoff before the screen pop, clears Home filters only for that successful jump, selects the frozen target after Home rebuild, and restores cursor, preview and focus. Stale generation, duplicate close, hidden JSON Enter, late row events and stale completion ownership are guarded.
- Refresh replaces the report, lookup state and JSON together. It preserves the selected finding plus duplicate occurrence when present, resets selection/detail state when removed, retains prior data on refusal or fault, and leaves existing sticky exit-3 behavior intact. Doctor creates no worker and adds no CLI, core-engine, model, dependency or snapshot change.

## Changed files

Implementation source and tests:

- `skill_lens/tui/doctor.py` — new Doctor screen, literal rendering, model identity, JSON and frozen path matching.
- `skill_lens/tui/app.py` — Home-only Doctor routing, exact-instance close/jump, and active-screen synchronization.
- `skill_lens/tui/home.py` — Home binding/footer and the pending validated jump consumed on resume.
- `tests/test_tui_doctor.py` — report parity, empty/no-session states, path matching, keyboard, refresh, raw JSON, scroll, stale generation and worker ownership.
- `tests/test_tui_read_only.py` — recursive module inclusion and synthetic before/after preservation through Doctor, JSON and matched/unmatched navigation.
- `tests/test_tui_app.py` — four parent-authored app integration tests for entry/focus/JSON, stale close/jump, refused/stale handoff and delayed row messages; coordinator-owned changes.

Documentation and durable evidence:

- `FULL_SCREEN_TUI.md`, `DEVELOPMENT.md`, `CHANGELOG.md` — current U7 keymap/status/evidence, while keeping U8–U9 and release separate.
- `docs/validation/u7/implementation/implementation-report.md`, `failed-attempts.md`, `mutation_campaign.py`, `mutation-campaign-run.log`, `targeted-tests.log`, and `mutations/` — implementation and verification records.

The frozen plan and `docs/validation/u7/planning/` are unchanged. `.path` and `docs/validation/2026-10-25/` remain as found. Parent-owned `docs/validation/u7/coordinator/` was not edited by this implementer.

## Checks and evidence

- Targeted Doctor, recursive read-only mutation-category and lifecycle preservation checks: **88 passed** before the final empty-report UI test was added. The empty-report UI test then passed separately (**1 passed**). The app integration tests were authored and run by the parent.
- Modified-code lint and strict type check: Ruff passed; mypy passed with **45 source files**.
- Isolated mutation campaign: **16/16** minimum and ownership/path/JSON mutations failed for the expected assertions; each includes passing control-before and restored-control runs. Full logs are in `mutations/`. The existing recursive source-guard categories are also exercised in the targeted 88-test run.
- Parent's independent UI acceptance suite passed **16/16**. Its reusable probe source is at `docs/validation/u7/coordinator/independent-checks.py.txt`; parent-authored permanent app checks are in `tests/test_tui_app.py`.
- Parent's first full gate on the earlier pinned tree recorded `1231 passed, 1 skipped`; its process exit was zero but the observed combined coverage was **89.60%**, below the unchanged 90% threshold. The failed evidence is retained and described in `failed-attempts.md`.
- Incremental diagnostics rose from **89.62%**, to **89.93%**, then **90.02%** after adding scroll, stale-generation, app-lifecycle and empty-report checks. These were diagnostic runs only, without exclusions; the final full suite and four gates were still running at this report's handoff. The parent owns and will record their final observed coverage and results under `docs/validation/u7/coordinator/`. Do not treat an incremental figure as final acceptance.

## Acceptance boundaries

No human visual review, hosted CI, release, commit or push is claimed. The final result should be read with the parent-owned U7 coordinator verification, which will record the final full suite and checks.

Coordinator follow-up: the subsequent [final parent verification](../coordinator/verification.md)
records 1,238 passing tests, 1 skip, 90.02% combined coverage and all four final
gates passed. This follow-up does not change which checks the implementer ran.
