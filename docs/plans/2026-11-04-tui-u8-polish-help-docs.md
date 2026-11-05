# Plan: U8 — Help, keyboard polish and user documentation

Status: FROZEN — planning only; implementation awaits a later owner instruction.
Date: 5 November 2026.
Baseline: `8edca36b93f8e717f61f82184e6edcf54884a2a2` on `main`.
Reference: `b59478404a9d20d2670fb12a731c703f53eee798` (operative frozen plan; the reference-only follow-up changes this line only).
Roster: coordinator — current Qoder host / owner-selected Kimi-K3.1-Pro / high
 effort, from the `/model` readback; planning critics — none by explicit owner
 instruction; implementer and final critics — pending later owner selection.
Risk and review: High, because Help changes covered-screen worker ownership,
 refresh/focus reconciliation and preservation of sticky exit status and read-only
 behavior. The owner authorized one coordinator self-revision and no planning
 reviewers as a mission-specific exception to independent planning review. This is
 not independent review or a guarantee of zero defects. Shared process files and
 AGENTS.md remain unchanged.
Expected child tasks: zero for planning. A later High-risk implementation normally
 needs one implementer plus two final critics before corrections; no implementation
 roster, host, review waiver or worker launch is selected by this plan.

## Authorization and delivery boundary

The owner appointed this session as the new orchestrator, asked it to revise and
complete the existing U8 draft, authorized exactly one self-revision after that
completion draft, and authorized freezing and committing the result. No other
planner, reviewer, subagent or external worker is used. The owner's no-reviewer
instruction applies to this planning mission only; it does not waive later
implementation review or select another session's process.

This mission changes only this plan and evidence in `docs/validation/u8/planning/`.
Use the normal two-commit freeze after verification; no push is requested. Product
implementation requires a later owner instruction. Obtain missing user selections
before any later delegation. Preserve unrelated `.path`, `.qoder/` and
`docs/validation/2026-10-25/` content and exclude it from every planning commit.

## Outcome and authority

Finish the browsing experience with an accessible Help overlay, a documented
keyboard map matching actual behavior, understandable empty/error states, and
accurate development documentation. Keep the CLI primary and the TUI optional,
offline, read-only and driven by captured inputs.

Scope comes from `FULL_SCREEN_TUI.md` §8.2, §8.5, §9.1, §10, Step 8, §12–13 and
§22 U8. U7 is delivered at the baseline. Its local technical evidence is recorded
in `docs/validation/u7/coordinator/precommit/verification.md`; hosted CI acceptance
and human visual approval are not established by that evidence. U9 versioning,
packaging and release preparation remain separate work.

## Verified starting facts

- App routes worker messages only to its current screen. Covering it with a new
  modal without lifecycle handling can strand a pending report.
- Home suspends Why work explicitly and resumes by synchronizing and focusing
  its skill table. Why has suspend/resume hooks, remembered focus and exact-token
  cancellation. Diff and Compare own tokens but have no cover/reveal lifecycle.
- Agents and Doctor read stored data without report workers. All six browsing
  screens have raw JSON modes; Compare additionally has picker/result modes.
- Textual's declared minimum and installed baseline version are both 8.2.8.
  Modal bindings stop ordinary non-priority app bindings at the modal; Help must
  explicitly expose Refresh and Quit. Input consumes printable characters, so
  non-priority `?` preserves filter typing. Priority keys need explicit toggle
  semantics because they are checked before modal bindings.
- The controller keeps an old usable snapshot after failed refresh. Refusal,
  retry, unexpected fault, loading and empty success are distinct. An accepted
  internal fault remains sticky and normal Quit subsequently exits 3.
- Coverage is measured across `skill_lens`, including `tui/`, with branches
  enabled and an unchanged 90% combined score threshold. U7's recorded 90.02%
  leaves little margin; add meaningful behavior coverage rather than exclusions.
- README still describes U6–U9 as future work; the specification calls Phase 7
  "planned, not built". Current documents must distinguish published 0.1.1 from
  development implementation without rewriting dated historical records.

## Allowed future implementation files

| Area | Allowed changes |
| --- | --- |
| `skill_lens/tui/help.py` (new) | Pure help content and one read-only modal, scroll/focus and literal status text. |
| `skill_lens/tui/app.py` | Help entry/exit, explicit origin ownership, modal-aware UI routing and guarded focus restoration. |
| `skill_lens/tui/home.py`, `why.py`, `diff.py`, `agents.py`, `compare.py`, `doctor.py` | Bounded Help lifecycle hooks, final binding/footer clarity, local empty/error explanations and focus/layout corrections required by this plan. |
| `skill_lens/tui/json_view.py` | Only an evidenced Help focus/scroll integration correction; JSON serialization unchanged. |
| `tests/test_tui_help.py` (new), existing `tests/test_tui_*.py` | Help, keymap, lifecycle, state, end-to-end and read-only preservation coverage. |
| `README.md`, `DEVELOPMENT.md`, `CHANGELOG.md`, `SKILL_LENS_SPECIFICATION.md`, `FULL_SCREEN_TUI.md` | Current user/contributor instructions, delivered keymap and factual status/evidence references. |
| `docs/validation/u8/` | Planning and later implementation/verification records, reproducible probes and mutation evidence. |

Excluded: core engines/snapshot capture, controller state machine, public models,
registry, CLI/Rich renderers, dependencies/lockfile, CI/release scripts, coverage
configuration, expected snapshots/goldens, process/agent instruction files,
archive/history rewrites, new themes, mouse-only actions, clipboard/export,
network/process/editor/repair operations and version/release/publishing changes.
A blocker requiring changes outside this scope needs an explicit scope amendment.

## Help content and keyboard contract

1. App non-priority `?` opens one `HelpScreen` over the current Home, Why, Diff,
   Agents, Compare or Doctor instance, including raw JSON and no-session states.
   In Home's text input, `?` remains filter text. Add one app-level priority `F1`
   toggle usable while typing: it opens Help from those six origins, or closes the
   exact active Help through the same guarded path as every other dismissal. Do
   not create a competing lower-priority modal action that the app priority key
   would preempt. This additive key is documented everywhere.
2. Help is a scrollable Textual modal with a title, concise common keys, a named
   current-screen section, explanations of captured data/refresh/read-only
   limits, live session status and a visible Close button. Show current status
   and existing in-memory fault details literally; distinguish a pending refresh
   with retained data from initial loading. Use unique `help-*` IDs and no
   imported Rich or CLI renderer. Add no log file.
3. `Esc`, `Backspace`, `?` and Close dismiss only this exact Help instance; `F1`
   uses the app-level toggle above. `q` and `Ctrl-C` quit through the existing app
   path; `r` requests the existing refresh. Help explicitly binds its dismiss,
   refresh and quit keys. `J`, `Enter` on body text, `d`, `h`, `g`, `c`, `/`, `a`
   and arrow keys cannot operate the covered screen. Enter on Close dismisses.
   Tab/Shift+Tab traverse only body and Close; arrows, PageUp/PageDown and
   Home/End scroll the focused help body.
4. Repeated opens cannot stack Help; stale callbacks cannot close a newer modal,
   pop its origin or restore focus to another screen. Opening Help never invokes
   capture, report computation, filesystem lookup or a write.
5. Prefer a small pure context-to-content function with shared common rows and
   explicit per-screen rows. Do not infer availability merely from a binding:
   focus, raw JSON and Compare picker/result mode change what a key can do.
   Show conditional instructions rather than promising every key works everywhere.
6. Preserve all existing non-Help shortcuts. Document Home `/` and `a` as Home
   controls; `d` opens Diff from a focused nonempty Home table or ordinary Why;
   Home `h` requires the focused ordinary table, while `g` and `c` work in
   ordinary Home outside the filter input rather than requiring table focus. Why
   left/right changes agents only on its strip. `J` is uppercase and shows the
   whole current report, not a filtered payload. It requires the focused Home
   table, an Agents/Doctor ordinary table or details pane, or Compare result
   mode; Why and Diff toggle their current report view. Agents has an array
   instead of a single report.
7. Explain layered Back: Help first, then JSON, then Compare result to picker or
   child screen to origin. Agents Back additionally leaves its details pane for
   the table before closing. Home Esc clears the text filter; it does not quit.
   Retain input editing keys and ordinary typing, including `q`, `r`, `h`, `?`.
   Show the actual narrower key scope where a screen's behavior differs.
8. Help explains that external edits appear after a successful `r`; a failed
   refresh can retain the previous catalog. Doctor Enter on a finding selects a
   matching captured row in Home; it never opens a file or another application.
   There are no edits, file opening, copying, saving or repair actions.

## Cover/reveal and worker contract

Use explicit cover/reveal handling, not routing a report to whichever screen
happens to be visible. Remember one exact origin plus its generation, mode,
selection, focused widget and scroll positions when Help opens.

- Suspend Home/Why using their existing exact-owner mechanisms. Add bounded,
  idempotent suspend/resume hooks for Diff and Compare. Cancel only the covered
  screen's own pending token if it still owns it; keep accepted reports/caches.
  Add active/suspended guards to affected callbacks and report-request paths.
- Agents/Doctor need no report cancellation. Prevent covered-screen selection,
  action and deferred focus callbacks from affecting Help. Do not change the
  controller or invent a new report view for Help.
- Capture continues through the normal app handlers while Help is open. `_update_ui`
  updates Help's status, not the origin's widgets. Defer origin reconciliation
  until reveal, so removal during refresh cannot pop Help accidentally.
- Cancelled/superseded report successes and errors still go through existing
  controller acceptance gates; they cannot mark the run failed or mutate Help.
  Covered screens cannot initiate replacement requests. Keep exact request IDs,
  generations and arguments; a rejected old result cannot cancel newer work.
- On close, pop only the expected Help, reconcile the actual revealed origin
  against the current controller, resume needed work once, and then restore focus.
  Coordinate native ScreenResume and explicit close paths idempotently. Do not
  let Home's default table focus override the saved filter-input focus.
- If the generation and content identity are unchanged, restore mode, selection,
  filter text/cursor, details/JSON scroll and focus. If refreshed, retain only
  still-valid selections and controls under that screen's existing rules. Removed
  Why/Diff keys close through existing notices; invalid Compare choices return to
  its picker. Re-check the actual top screen after each reconciliation before
  restoring focus. Never resurrect removed widgets or stale JSON.
- Help remains usable during initial loading, slow refresh, refusal/retry and
  internal faults. Quit keeps cooperative cancellation and exits promptly; do
  not claim that a running thread or blocked file read can be forcibly stopped.

## Empty/error polish boundary

Audit every screen at 100×30 and 60×24 through keyboard-driven semantic tests.
Use existing model/presentation wording and `session_explanation()` where suitable.
Keep full literal text accessible in scrollable content; do not silently truncate
facts to fit. Keep ordinary focus traversal usable with no selected rows.

| State | Required distinction |
| --- | --- |
| Initial capture pending, no snapshot | Honest scanning indication, no invented count, Help/Refresh/Quit usable. |
| Successful empty catalog | Explain no skills were found; Home remains navigable. |
| Home filters hide all rows | Explain no matches and how to clear the filter; preserve full Home JSON. |
| No detected agents vs no registry definitions | Detection is not comparison eligibility; Agents lists known definitions. |
| Why/Diff has no eligible data | Existing missing/unreadable/no-difference model answer stays readable. |
| Compare has fewer than two definitions, same agent, removed choice | Explain the exact condition; no fabricated comparison or fault exit. |
| Doctor empty vs info-only report | Preserve healthy/findings distinction and all stored findings. |
| Unreadable root | Display captured unreadable/diagnostic information; continue browsing. |
| Refused oversized capture | Explain refusal/budget; never promise retrying unchanged inputs fixes it. |
| Snapshot changed/incomplete | Show expected retry guidance without sticky failure. |
| Accepted unexpected fault | Plain error and in-memory details, retained usable data where available, sticky exit 3. |

With no prior snapshot, never show a healthy empty success or serialize fabricated
reports. With a prior snapshot, label retained data accurately. Do not unify all
states into one misleading "nothing found" panel. Restrict fixes to demonstrated
UI gaps; preserve report message, severity, evidence, ordering and JSON bytes.

## Documentation completion

- README: add a short Interactive mode section with development-checkout install
  `pip install -e '.[tui]'` in an already prepared virtual environment; this is
  not a published package instruction. Explain both-terminal bare launch,
  `--plain`, explicit `tui`, bare missing-extra help/tip with exit 0 versus
  explicit-command missing-extra hint with exit 2, main keys, capture/refresh,
  budget limits and TUI exits 0/3. Keep every README link an absolute URL,
  including same-page links, as required by DEVELOPMENT. Distinguish the six
  released CLI commands from development TUI screens and U9 future work.
- DEVELOPMENT: link the U8 plan/results and final gate evidence; describe how
  semantic tests, read-only checks and covered-worker tests are replayed. Preserve
  historical measurements and the separate release checklist.
- CHANGELOG: record only implemented U8 behavior under Unreleased; preserve
  published headings, version and historical entries. No claim of a 0.2 release.
- Specification and full TUI design: reconcile current implementation status,
  actual contextual keys and launch rules; keep historical design rationale,
  agent precedence/evidence and CLI contracts intact. Correct an inaccurate
  current statement rather than rewriting a dated acceptance record.
- Check edited links against tracked paths and anchors; use existing links for
  unchanged evidence. Record measured limits and unexecuted platform checks.
  No human visual, installed-wheel or hosted CI claim from headless local tests.

## Implementation order after later authorization

1. Read this frozen plan, baseline sources, U7 acceptance and relevant existing
   lifecycle/read-only tests. Both coordinator and implementer verify that
   `Reference:` names the frozen commit containing this entire operative contract.
   Inspect checkout binding, preserve unrelated work and run all four baseline
   gates. Inventory state/key coverage; reproduce gaps in isolated fixtures before
   changing behavior. Confirm scope before wider fixes. The later owner-named
   implementer writes product code/tests but does not review, delegate or commit.
2. Add shared help content and modal; establish exact-origin open/close, worker
   suspend/resume, capture status and focus/scroll handling. Add focused tests.
3. Audit/polish empty/error states and footer discoverability with bounded edits;
   preserve every existing key and model contract. Complete the full browsing flow.
4. Update current documentation to the tested behavior; retain historical records.
5. Run targeted checks, mutation-test new acceptance guards in disposable copies,
   inspect the complete diff, run final full gates, inspect preservation hashes
   and record limitations. Coordinator verification, required final review,
   acceptance and any commit/delivery follow the later owner's roster and instruction.

## Acceptance and evidence

A1. Real Pilot keys open/dismiss one Help from all six screens, Compare picker and
result, ordinary/JSON modes, loading and no-session states. Cover 100×30 and
60×24 with all help text/controls reachable. Assert context content, focus,
scroll and stack identity, not full-screen pixel/text-grid snapshots.

A2. Input typing (including `?qrahdgc/J`), cursor/backspace behavior and Help via
F1 preserve text. F1 both opens and closes the exact Help while typing and
elsewhere without stacking or losing priority to a modal binding. Every dismiss
route restores the actual prior input, cursor and scroll; plain `?` elsewhere
opens Help. Hidden table shortcuts cannot activate behind it.

A3. Delay Home Why, Why detail, Diff and Compare jobs. Open Help during each;
verify exact-owner cancellation, no hidden replacement work, no stuck loading on
reveal, cached reports reused and at most one replacement request on a miss.
Deliver old successes/errors both before and after close; they cannot affect
newer tokens, display or sticky status. Test native and explicit resume paths.

A4. Hold initial capture; open Help, then publish. Repeat with two refreshes
finishing newest first, removals of Why/Diff installations and Compare IDs,
loading JSON, and refusal/retry/unexpected faults with/without prior data. Help
stays open until dismissed; its literal status/fault details and retained-data
wording stay accurate, and reveal reconciles correctly with no stale focus or old
JSON. Add slow-work quit, normal exit 0 and sticky-fault exit 3 checks.

A5. Drive keyboard flow Home → Why → Diff → Why → Home → Agents → Home → Compare
picker/result → Home → Doctor → in-app Home selection, exercising Help and raw
JSON at meaningful points. Include filtering, empty input, unreadable fixtures,
literal markup-like text and a successful refresh. Assert real focus and report
content; run after fixture targets are edited/deleted to detect live fallbacks.

A6. On identical inputs and arguments, compare all six JSON views with existing
CLI serializer oracles. Preserve existing golden/snapshot files byte-for-byte.
Recursive read-only guards include the new module; extend before/after synthetic
fixture checks across Help, refresh, faults, full navigation and quit, preserving
bytes, modes and symlink targets. No tests use real HOME/agent skills; reuse
`mock_home`, sandbox and protected-system-root guards from `tests/conftest.py`.

A7. Add tests for each demonstrated empty/error correction in the table above.
Retain coverage of unchanged states through existing tests, with an explicit
mapping to test names; do not create implementation-mirroring assertions merely
to increase coverage. Capture complete output, exit status and tested inputs.

A8. Mutate new behavior guards in disposable checkout copies: duplicate Help;
covered key leakage; lost input focus; ignored Diff/Compare suspension; stranded
report after reveal; stale callback popping a newer screen; stale JSON after
refresh; fault hidden/reset while Help is open; a write/import in the new module.
Each case needs a passing control, a meaningful failing assertion with the defect,
and a passing restored control. Do not accept timeout, syntax/import error or
exit zero alone as evidence. Reuse unchanged guard-category mutation coverage.

A9. Run all four final gates on the final implementation tree:

```bash
.venv/bin/pytest --cov=skill_lens
.venv/bin/mypy
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Require successful test completion and the explicit coverage-success result at
≥90% including `tui/`, plus clean type/lint/format checks. Never lower the gate,
exclude code, regenerate expected output or use whole-repository write formatting
to force a pass. If formatting is needed, scope it to changed Python files.

A10. Record the frozen plan hash, source/test/configuration identities, complete
reviewed diff, test/mutation results, state/keymap mapping and limitations under
`docs/validation/u8/`. Include the implementer's model/settings evidence, changed
files, checks, tests, deviations and blockers, plus the execution receipt and any
required final-review decisions. Local checks establish local technical readiness
only. U9, built-wheel qualification, platform matrix/hosted CI, human visual
approval and publishing remain separate unless explicitly authorized later.

## Self-revision and freeze record

The completion draft was prepared from the current source, tests, specification
and U7 evidence on 5 November 2026. Exactly one formal self-revision is now
complete. It checked modal key priority, actual key context, request ownership,
refresh/reveal behavior, scope, acceptance evidence, implementation handoff and
freeze mechanics. Corrections clarified the Textual version fact, `J`/Back
context, F1 dismissal evidence, fault/retained-data evidence, frozen-reference
and baseline checks, and implementation reporting. No in-scope blocker remains.
No second revision pass or independent review occurred. Detailed decisions and
before/after plan hashes are in the [revision record](../validation/u8/planning/revision.json).

The recorded starting gates passed: 1,238 tests passed, 1 skipped, 90.02%
combined statement/branch coverage with TUI measured; mypy passed over 45 source
files, and Ruff lint/format passed. On 5 November all 1,807 tracked-file hashes
in `baseline.json` were rechecked with no mismatch. These facts validate the
starting point, not unimplemented U8 behavior.

Use the two-commit freeze. The first frozen-plan commit is authoritative; the
second changes only `Reference:` to that commit's full hash. Planning evidence is
committed separately without altering the operative contract. Implementation
must not start in this planning mission.
