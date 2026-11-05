# U8 implementer self-review

Date: 5 November 2026.
Repository HEAD: `a9d67b808ce235a543e63fba40b478da2a96c3e3` (unchanged).
Frozen plan: `docs/plans/2026-11-04-tui-u8-polish-help-docs.md` at
`b59478404a9d20d2670fb12a731c703f53eee798`.

This is the implementer's own review. It is not independent review or
acceptance.

## Scope and preservation

- Every changed path is within the frozen plan's allowed set: the new
  `skill_lens/tui/help.py`, `app.py`, bounded lifecycle changes in the six
  screens, `tests/test_tui_help.py`, bounded updates to `tests/test_tui_home.py`
  and `tests/test_tui_read_only.py`, the five documentation files, and
  `docs/validation/u8/`.
- `skill_lens/tui/session.py` and the controller state machine are untouched.
- Core engines, models, registry, CLI, Rich renderers, dependencies, lockfile,
  packaging, CI, coverage configuration, snapshots and goldens are untouched.
  `final-integrity.json` records empty diffs for those areas.
- `.path`, `.qoder/` and `docs/validation/2026-10-25/` were untracked before and
  after; they were not opened for modification or staged. Hashes are recorded in
  `final-integrity.json`.
- No commit, push, delegation, release or publishing action was performed.

## Code read with its consumers

- **App/Help ownership.** Read `push_screen`/`pop_screen` and Textual 8.2.8
  binding dispatch to confirm: priority app bindings run before the modal,
  non-priority app bindings stop at the modal, and `Input` consumes printable
  keys. That is why `?` is non-priority, `F1` is one app priority toggle, and
  Help explicitly binds `q` and `r`.
- **Home.** Reviewed `suspend_why`, `resume_why`, `on_screen_resume`, Why queue
  ownership, filter/selection reconciliation and JSON mode. Added a separate
  Help path because `resume_why` intentionally focuses the table; Help restores
  the exact saved widget, including the filter input.
- **Why.** Reused `suspend_detail`/`resume_detail`, which already remember the
  exact focused widget, cancel only their owned token and reconcile idempotently.
  Help only adds scroll capture and the reveal path.
- **Diff and Compare.** Added bounded `_suspended` guards to synchronization,
  report requests, outcome handlers and deferred focus. Both cancel only their
  own token if still active and restore accepted reports from the controller
  cache. Resume asks at most once on a genuine miss.
- **Agents and Doctor.** No report workers. Added suspend guards to row events,
  actions and deferred focus; a removed details pane falls back to the table.
- **JSON.** `JsonView` serialization was not changed. New tests prove a document
  accepted behind Help reaches the view only on reveal and that a refresh
  replaces old bytes.

## Behaviour checked by inspection and tests

- Help opens exactly once from all six screens, all raw JSON modes, Compare
  picker/result, initial loading and no-session states; `screen_stack[-2]` is the
  exact origin.
- Repeated opens do not stack; a stale instance cannot close a newer Help.
- `Esc`, `Backspace`, `?`, `F1` and Close dismiss only the expected instance;
  `Tab`/`Shift+Tab` cycle body and Close; body keys scroll; Enter on body is
  inert; Enter on Close dismisses.
- Home filter typing keeps `?qrahdgc/J`, `q`, `r`, `h`, `d`, `g`, `c`, `a` and
  `/` literal; F1 preserves text, cursor and focus.
- Hidden screen keys do not act while Help is open; a planted leak is caught by
  the mutation campaign.
- Delayed Home Why, Why detail, Diff and Compare work is cancelled only when the
  screen still owns the token; old results/errors are rejected before and after
  reveal; current accepted faults stay sticky and visible.
- Initial capture, out-of-order refreshes, Why/Diff removals, Compare ID
  removals, loading JSON, refusal, retry and unexpected faults all reconcile only
  after reveal; Help stays open until dismissed.
- Exit 0 on normal/refusal/retry and exit 3 after an accepted internal fault.
- All six JSON views equal the CLI serializer on the same captured inputs.
- A recursive read-only fixture check covers Help, navigation, refresh, a fault
  and quit; bytes, modes and symlink targets are identical before and after.
- Empty/error distinctions remain separate: empty catalog, hidden filter,
  no-detected-agents versus no-definitions, Compare shortfall/duplicate/removal,
  Doctor empty versus info-only, unreadable root, refusal/retry/fault.

## Documentation review

- README's Interactive mode is explicitly a development-checkout instruction
  (`pip install -e '.[tui]'` in an already prepared virtual environment), not a
  published-package claim. It documents both-terminal bare launch, `--plain`,
  explicit `tui`, missing-extra exits, main keys, refresh, capture budget and
  TUI exits 0/3.
- Every README link is absolute; there are no same-page relative links. The
  Phase 5 link gate passes. Relative links in the other changed documents resolve
  to tracked files (`doc-link-verification.txt`).
- Claims were checked against the CLI implementation (`_launch_tui`, the `tui`
  command and its missing-extra/non-interactive errors) and the tests above.
- No 0.2 release, hosted CI acceptance, built-wheel verification, human visual
  approval or publishing claim was added. U9 remains future work.
- Historical dated records were not rewritten.

## Formatting and generated output

- Only changed Python files were formatted. No whole-repository write formatter
  was used to force the gate.
- No snapshot or golden was regenerated. `tests/fixtures` has no diff.

## Remaining limitations

- All checks are headless `Textual` `Pilot`/`run_test` checks on macOS with
  Python 3.11.16 and Textual 8.2.8. No human visual approval, real-terminal
  manual pass, Linux lane, Python 3.12–3.14 lane, hosted CI run, built-wheel
  smoke or publishing check was executed.
- Quit is cooperative. A blocked file read or already-running worker thread is
  not forcibly stopped; the tests only prove the app returns without waiting.
- Help's static body describes the screen mode and focus captured when it
  opened. The live session section updates while it stays open; covered screens
  do not change mode behind it.
- Home's captured unreadable-root note is an auto-height literal line; very long
  values wrap and consume vertical space rather than being truncated. No fact is
  removed, but there is no dedicated scroll region for that note.
- Coverage is 90.10%, above the unchanged 90% gate but with a small margin.
  The remaining uncovered lines are largely existing defensive branches in the
  six screens.
- Mutation proof covers the required defect categories; it is not an exhaustive
  proof of every possible implementation error.
