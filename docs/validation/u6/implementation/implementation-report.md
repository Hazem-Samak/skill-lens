# U6 implementation report

## Outcome

Implemented the U6 Agents browser and Compare picker/result screens. Both read
the captured session only, keep registry definitions visible even when no
installations are detected, and preserve ordered comparison pairs through
cached and asynchronous report requests. The implementation includes JSON
views, refresh handling, stale-result rejection, literal text rendering,
read-only traversal coverage, and the planned documentation updates.

This report records implementer evidence. It is not owner acceptance, parent
review approval, human visual approval, hosted CI, or release approval.

## Frozen plan and execution evidence

- Operative frozen plan commit: `17f92ab0bebcf64e2ec8bf46950613649da06aec`.
- Reference-only plan commit: `3da918b662a05dcdbdd82e2095316dfe9f583006`.
- Starting checkout `HEAD`: `3a266b4986f5b9bd6838e773a298b2a862904a08`.
- The frozen plan was compared with the working plan; its content matched
  except for the reference-only `Reference:` line. The frozen plan was left
  unchanged.
- Requested execution identity: native `gpt-6-luna`, Max effort. The user and
  coordinator selected that configuration; upstream runtime identity and
  effort-label routing were not independently observable, so this report does
  not claim them as verified facts.
- No files were staged or committed, and nothing was pushed or installed.

## Changed product, test, and project-documentation files

- `skill_lens/tui/agents.py` — new captured-registry list, selected-agent
  details, raw JSON mode, refresh reconciliation, and focus/scroll restoration.
- `skill_lens/tui/compare.py` — new two-column picker, ordered pair submission,
  captured report rendering, JSON mode, refresh reconciliation, full-token
  ownership, cancellation, and stale-result/error rejection.
- `skill_lens/presentation/agents.py` — pure shared Agents JSON payload.
- `skill_lens/presentation/__init__.py`, `state.py`, and `text.py` — shared
  comparison relation labels, empty-state text, and payload exports.
- `skill_lens/tui/app.py` and `home.py` — bounded route/close/refresh
  integration and `g`/`c` shortcuts that preserve filter typing.
- `skill_lens/cli.py` and `render.py` — narrow CLI and renderer calls into the
  shared presentation helpers; existing CLI JSON shape and snapshots remain
  unchanged.
- `tests/test_tui_agents.py` — captured definitions and details, literal text,
  empty/no-capture states, JSON, keyboard/focus/scroll behavior, refresh
  reconciliation, and Agents routing.
- `tests/test_tui_compare.py` — registry-eligible picker, ordered pair JSON
  oracle, result relations, refresh states, request-race barriers, no-retry and
  explicit retry behavior, button submission, stale-token ownership, and raw
  mode behavior.
- `tests/test_tui_read_only.py` — synthetic-HOME before/after target tree
  preservation across Agents, Compare, raw JSON, and refresh traversal.
- `FULL_SCREEN_TUI.md`, `DEVELOPMENT.md`, and `CHANGELOG.md` — factual U6 status,
  key bindings, gate wording, and change record.

The unrelated untracked `.path`, `docs/validation/2026-10-25/`, and parent-owned
`docs/validation/u6/coordinator/` were preserved.

## Behavior checks and safety boundaries

- Agents JSON is compared byte-for-byte with an independently constructed CLI
  oracle. Compare JSON is compared with the CLI output for both `(A, B)` and
  `(B, A)`.
- Test screens cover `100x30` and `60x24`, positive scroll restoration, literal
  dynamic text, `j`/`k`, Enter, Escape, Backspace, Tab, JSON focus, and picker
  button activation.
- Compare can choose any two captured registry definitions regardless of
  detected installations. It uses only the captured registry, index, paths, and
  bytes until refresh.
- The controlled race tests cover stale success and stale error handoffs, full
  ordered-token ownership, close-instance ownership, no redraw-driven retry,
  and an explicit retry while keeping exit status 3 sticky.
- The synthetic target-preservation traversal checks before/after file bytes,
  modes, inventory, and symlink targets. It does not use the developer's live
  skills as test data.
- No engine, controller, snapshot model/service, registry, dependency/version,
  or expected-output fixture was changed.

## Implementer verification

### Full gates before the last test-only assertion strengthening

These commands ran on the implementation tree before the final strengthening of
two test assertions. The product code was identical to the tree now awaiting
the parent's final run.

| Command | Result |
| --- | --- |
| `.venv/bin/pytest --cov=skill_lens` | Exit 0; **1220 passed, 1 skipped**; coverage explicitly printed `Required test coverage of 90.0% reached` at **90.09%**. |
| `.venv/bin/mypy` | Exit 0; no issues in 44 source files. |
| `.venv/bin/ruff check .` | Exit 0; all checks passed. |
| `.venv/bin/ruff format --check .` | Exit 0; 401 files already formatted. |

The complete stdout for that run is in `pytest.log`, `mypy.log`,
`ruff-check.log`, and `ruff-format.log`. The test-only correction that followed
adds stronger request-count checks and a bounded retry-worker barrier; its clean
tests and mutations were rerun below. Parent final gates are the acceptance
evidence for the final test tree.

### Focused behavior and mutation checks on the final test tree

- The U6 Agents/Compare focused suite passed **27 tests** before the last two
  test-only assertion changes. The two affected tests then passed individually
  before that batch.
- The final corrected missing-choice and redraw-retry tests each passed a clean
  control, failed under their intended source mutant, and passed after source
  restoration. Focused Ruff check and format check passed after the final test
  edits.
- `mutation_gate.py --preflight-only` passed for all **13** selectors, intended
  test markers, Python AST checks, exact source restoration, and temporary-copy
  provenance.
- Final mutation receipt: **13/13 killed**, all controls exit 0, each mutant
  failed at its recorded assertion (exit 1), and each restored test exited 0.
  `mutations.json` contains complete per-case stdout/stderr and records the
  imported paths for `skill_lens`, `test_tui_agents.py`, and
  `test_tui_compare.py` inside the disposable copy. `mutations.md` is the table
  summary.
- Case 12 was not rerun after its marker mismatch. The saved mutant traceback
  directly showed `(2, 2) == (1, 2)` for the hidden picker cursors during raw
  JSON mode; the final receipt records that observed assertion as the kill.
- `mutations-first-complete-run.json`, `mutation-run.log`,
  `mutation-run-final.log`, `mutation-recovery.log`, and
  `mutation-matcher-attempt.log` retain the original survivor, marker mismatch,
  correction, and recovery history.
- The probe that removed only a redundant JSON refresh call survived because
  other state transitions already clear the document. It is documented as a
  redundant-guard survival, not a product failure; it was replaced by the
  behavior-breaking raw-refresh reconciliation mutation.

The separate focused-coverage command using dotted `--cov` source names
triggered a Python `asyncio.CancelledError` class-identity split during
coverage's import cleanup and produced `WaitForScreenTimeout` failures. It was
not treated as product coverage evidence. The reproduction and diagnosis are
recorded by the coordinator under `docs/validation/u6/coordinator/`; the normal
whole-package coverage gate above passed.

## Parent verification and remaining acceptance

At report creation the parent had started the final four gates against the
corrected test tree. The product hashes still matched the parent's six passing
independent UI checks. Parent gate outcomes and acceptance must be recorded by
the parent; this implementation report does not claim them in advance.

Human visual approval, hosted CI, release, staging, commit, and push were not
part of this implementation checkpoint.
