# Plan: U7 — Doctor

Status: FROZEN — planning only; implementation awaits a later owner instruction.
Date: 4 November 2026.
Baseline: `01748933f7108703b796c01e15e85bd0918cc6d7` on `main`.

## Authorization and stop point

The owner requested planning the next phase, appointed this Codex session as the
sole planner, requested two separate revisions, and authorized freezing and
committing the resulting plan. The owner explicitly waived the planning and
implementation loops for this session. This is a mission-specific override;
shared process files and AGENTS.md are unchanged. No other planner, critic,
subagent or external worker is launched. The two passes below are self-reviews
by one planner, not independent-agent review or a guarantee of zero defects.

This mission changes only this plan and its evidence under
`docs/validation/u7/planning/`. Commit and push the planning files under the
owner's standing delivery preference. Implementation starts only after a later
owner instruction. This plan does not select an implementer or future reviewer,
a provider/model/effort roster, or a worker host. If workers are later requested,
obtain any missing owner selections before dispatch. The loop waiver in this
session must not be assumed to authorize a different future session's process.

## Outcome and source of truth

Add a read-only Doctor screen showing the complete `DoctorReport` already stored
in the published `SessionSnapshot`. Users can read findings, inspect their full
details, view exact canonical JSON, and select a matching skill in Home. No
health checks run merely because the user opens or browses Doctor.

Authoritative scope: `FULL_SCREEN_TUI.md` §8.6, §8.8, §9.1, §10, Step 7 and
§22 U7. U6 is delivered at the baseline; its local verification is recorded in
`docs/validation/u6/coordinator/verification.md`. No hosted CI or human visual
acceptance is inferred from that record. U8 help/general polish and U9 release
preparation remain separate work.

Verified implementation facts to preserve:

- `core/snapshot.py:capture_session()` constructs and validates Doctor before
  publication; `SessionSnapshot.doctor` is the report to show.
- `core/doctor.py` already orders findings by error, warning, info, then code
  and path. Render the stored tuple in its existing order; do not re-sort it or
  repeat the severity ranking in UI code. Messages and details are model data.
- `DoctorReport.healthy` allows informational findings. An empty findings tuple
  and a nonempty info-only report are different valid states.
- `DoctorFinding.path` is optional and is often a preformatted `~/...` string.
  Entry paths and `canonical_key(entry)` identify captured catalog rows.
  `snapshot_path()` uses a stored lookup, and `snapshot_same_location()` uses
  string equality or stored pairs; neither probes the machine.
- The controller's report-worker types cover Why, Diff and Compare only. Doctor
  needs no worker, cache entry, `ViewName`, or controller/model/core change.
- Home explicitly suspends its Why queue before another screen covers it.
  `ScreenResume` resumes Home; close paths also perform an idempotent resume and
  status refresh. Home can change selection if filters hide a requested key.
- Reuse `JsonView` and `session_explanation()`. Existing CLI rendering and public
  report dictionaries remain unchanged.

## Allowed implementation scope

| File | Permitted change |
| --- | --- |
| `skill_lens/tui/doctor.py` (new) | Doctor widgets, literal text, frozen path matching, selection, raw JSON and session reconciliation. |
| `skill_lens/tui/app.py` | Import/export screen, explicit Home-only open/exact-instance close/jump routing, active-screen synchronization. |
| `skill_lens/tui/home.py` | Doctor entry binding and host protocol; a small, explicit pending-jump handoff consumed during Home resume. |
| `tests/test_tui_doctor.py` (new) | Model parity, path matching, keyboard flow, refresh, JSON and fault tests. |
| `tests/test_tui_home.py`, `tests/test_tui_app.py`, `tests/test_tui_json.py`, `tests/test_tui_read_only.py` | Bounded integration, lifecycle, JSON and full browsing preservation coverage. |
| `FULL_SCREEN_TUI.md`, `DEVELOPMENT.md`, `CHANGELOG.md` | Factual U7 keymap/status/evidence updates after implementation. |
| `docs/validation/u7/` | Implementation results, mutation records and acceptance evidence. |

Excluded: engines, controller, public models, registry, CLI/Rich renderers,
dependencies/lockfile, snapshot capture policy, shared process/agent instructions,
existing expected snapshots/goldens, help overlay, general redesign, version
bumps, release or publishing. If a required correction exceeds these bounds,
report the mismatch and obtain an explicit scope amendment before changing it.

## Screen and keyboard contract

### Entry, exit and focus

- Home lowercase `h` opens **Doctor** (health); retain `d` for Diff. Advertise
  Doctor in the Home footer and the delivered keymap. Open only from ordinary
  Home when the skill table has focus; a selected skill or nonempty table is
  not required. Typing `h` in the filter remains text. Home JSON mode cannot
  open Doctor. Existing `g`, `c`, `d`, `J`, refresh and quit behavior stays intact.
- `SkillLensApp.open_doctor()` accepts Home only, suspends Home before pushing
  one `DoctorScreen`, and rejects repeated or covered-screen calls. The screen
  synchronizes on mount, including a capture that completed before mount.
- Doctor has a title, summary/context, focusable findings table, scrollable
  selected-finding details, a local navigation notice, existing `JsonView`,
  session status/error details and a footer. Use unique `doctor-*` widget IDs.
  Add Doctor only to the app's active-screen `_update_ui()` synchronization; it
  needs no `note_report_outcome()` callback or worker-message routing.
- Table columns: Severity, Code, Message, Path. No clipping may make full data
  inaccessible: the details pane contains the entire selected finding; wide
  tables can scroll. Below 80 terminal columns, stack list and details like
  Agents. Verify 100×30 and 60×24 layouts semantically.
- Initial focus is the findings table even for zero findings. `Tab` and
  `Shift+Tab` traverse the table and scrollable details. Up/down and `j`/`k`
  move table selection only when the table is focused; when details are
  focused, scroll details. Do not drive the hidden table in raw mode.
- Ordinary `Esc`/`Backspace` closes this exact Doctor instance and resumes Home.
  Plain Back preserves Home's text filter, agent filter and valid selection.
  A delayed callback from an earlier Doctor cannot pop a different screen.
- `Enter` on the focused findings table attempts an in-app jump. It does not
  open Why, Diff, an editor, Finder, a browser, a shell or a file. Elsewhere it
  has no jump action. Failed matching stays in Doctor with a literal notice.
- `r` uses the existing app refresh action, `q`/`Ctrl-C` use existing quit.
  Doctor owns no report requests or private background work.

### Findings and text

- All findings are shown, independently of Home's filters/detected agents.
  Use their tuple order and one stable row per finding, including duplicates.
  Row identities carry generation plus full finding value and duplicate occurrence
  (or an opaque token mapped to those values), not only a numeric index. Ignore
  selection/activation events from an older table generation. Each handler also
  checks that this Doctor is still the active screen; hidden or closed instances
  cannot change selection or initiate a jump.
- Summary uses `counts_by_severity()` and `healthy`, and displays captured Home
  and Cwd through `snapshot_path()`. Do not claim an info-only report has zero
  findings. Empty report: `Skill folders look healthy.` with no selected finding.
- Details show Severity, Code, Message, Path, Detail, Rule ID and Evidence. Use
  the original values unchanged; a missing path/detail is an explicit `(none)`
  placeholder, never a fabricated path or diagnosis. Styling is separate from
  strings. Brackets and markup-like input remain literal in cells, details,
  notices, context and errors; do not import Rich or `skill_lens.render`.
- The screen may add navigation instructions but cannot rewrite engine findings,
  change severity/evidence or infer extra diagnoses. No repair action or clipboard.

## Frozen path matching and Home jump

Implement a small pure helper in `tui/doctor.py`, conceptually
`finding_catalog_keys(snapshot, finding) -> tuple[str, ...]`:

1. A missing/empty path returns no candidates. Never parse paths out of message
   or detail text.
2. Start with the finding's literal path. Add **every** raw key in
   `snapshot.display_paths` whose stored display value exactly equals it.
   This reverses captured `~` presentation without `expanduser()` or live HOME.
   Preserve all reverse matches; a dictionary that stores only one raw path per
   display string would hide ambiguity.
3. For each captured entry, inspect its primary entrypoint, all entrypoint aliases,
   all hit entrypoints, and its non-null canonical path. Match if any candidate
   string equals one of these paths or `snapshot_same_location(snapshot, a, b)`
   proves equality. Canonicalize the resulting row identity with
   `canonical_key(entry)` and deduplicate keys. Return a deterministic sorted tuple.
4. Do not use basename/skill-name matching, path-prefix matching, descendant
   guesses, `Path.resolve`, `stat`, `samefile`, `exists`, live `paths.display`,
   `paths.same_location`, discovery or doctor execution. A path naming a root,
   lockfile or external target does not select an arbitrary child.

Matching outcomes are:

| Candidate keys | Behavior |
| --- | --- |
| One | Revalidate current generation and key, then reveal that Home row. |
| Zero, path absent | Stay in Doctor: `This finding has no path to select in Home.` |
| Zero, path present | Stay in Doctor: `No matching catalog entry for this path.` and show the literal path. |
| Multiple | Stay in Doctor: `This path matches more than one catalog entry; no skill was selected.` and show the literal path. |

A broken link or unreadable installation that *is* a catalog entry can be
selected. The examples in §8.6 do not mean every broken-link finding must be
unmatched. A stored alias may match one row; two aliases for the same canonical
key are one candidate. Genuine ambiguous display mappings are never guessed.

The app's jump method receives the expected Doctor instance, displayed
snapshot generation, and candidate key. Before any filter/selection/stack
mutation, confirm the expected screen is active, `controller.current` exists,
the generation still matches, the selected finding is current, and that finding
still matches exactly that key. If stale, reconcile Doctor and require a new
Enter; never follow an old table index into a newer report.

For a successful jump:

- Queue `(generation, key)` on Home through a bounded method such as
  `prepare_doctor_jump()`, while Home remains suspended. This method validates
  ownership/data and records intent without requesting reports or changing
  hidden Home widgets. Both Textual `ScreenResume` during pop and the app's
  explicit close callback call `resume_why()`; both must consume through this
  same handoff-aware path. Do not schedule the jump only after `pop_screen()`.
- Pop Doctor only after that handoff succeeds. Consume the handoff at the
  **start** of Home's existing resume path, before its normal reconciliation
  can apply old filters. Clear the text filter, reset agent filter to All agents,
  and set the validated key. Rebuild Home from the current snapshot before
  applying the key if its own generation is old. Apply the final key after that
  rebuild, then synchronize cursor/preview so the generation-reset fallback
  cannot silently win. Clear obsolete local notices, focus the skill table and
  refresh session status. Duplicate resume calls are harmless; consume intent once.
- Guard programmatic Input/table events while doing this handoff so deferred
  events cannot restore filters or select a different row. Home is the only
  owner of its filters and widgets; Doctor must not reach into them directly.
- Recheck the generation/key when consuming. If no longer valid, clear the
  handoff and show Home's explicit stale/unavailable notice without inventing
  a replacement jump. The controller's existing ordinary selection fallback
  remains valid, but must not be described as a successful Doctor jump.

## Refresh, unavailable data and errors

Use one published snapshot for findings, lookup candidates, context and JSON.
Never mix Doctor from one generation with a newer catalog.

- Same generation/status-only synchronization retains selection, detail scroll,
  JSON mode/focus and JSON scroll. Do not rebuild unchanged tables or documents.
- On successful publication, replace the complete Doctor view and lookup data.
  Preserve selected finding by the full finding value plus its duplicate
  occurrence number, if it still exists; otherwise select the first new finding
  or none. Never retain a numeric row index as identity. Reset detail scroll
  only when the selected finding/value changes. Clear obsolete local notices.
- Pending/changed/refused/failed refresh retains the last published report when
  available, with the existing session status/explanation and in-memory error
  details. No automatic retries or live doctor reruns. A rejected stale capture
  cannot replace findings or matching data.
- No captured session is distinct from an empty healthy report. Show
  `session_explanation(controller)`, no fabricated counts/health verdict and no
  jump. It remains possible to go back, refresh or quit.
- Follow existing sticky internal-fault semantics: normal diagnostic errors or
  unmatched findings do not set failure/exit 3. An accepted unexpected internal
  fault remains exit 3 even after later recovery. Quit during refresh cancels
  through the existing controller/app; Doctor adds no cleanup jobs.

## Raw JSON

`J` toggles the existing in-screen `JsonView`, showing exactly
`dumps(controller.current.doctor.to_dict())`. Preserve original report ordering
and optional/null fields. Do not serialize UI selection, filtered findings,
formatted path labels, counts, health verdict or navigation notices.

Use `show_document()` for a report, `show_explanation()` when there is no
published session. Preserve same-document scroll; a changed document resets
according to `JsonView`. Save ordinary detail scroll with its finding identity;
a refresh that changes/removes that finding invalidates saved scroll rather than
restoring an old offset over a newly selected finding. Hide ordinary table/details
and disable their actions in raw mode. `J`, `Esc` or `Backspace` restores the
ordinary view first, with valid previous focus/selection/scroll or a table fallback; a second Back closes.
Refresh/quit remain usable. Equality with actual CLI output means the same
captured inputs, using the CLI's normal final newline separately from the JSON
document. Never compare to a later live run over changed fixtures.

## Implementation sequence after authorization

1. Recheck baseline, frozen plan and checkout; preserve unrelated `.path` and
   `docs/validation/2026-10-25/`. Read the relevant project records and the U6
   verification. Stop on a behavioral mismatch outside the allowed scope.
2. Add discriminating tests for stored report/order/messages, all matching
   outcomes, duplicate finding identity and raw serialization before wiring
   navigation. Use synthetic `tmp_path`/mock HOME and existing fixtures only.
3. Add Doctor, then explicit app entry/close/status integration and the bounded
   Home pending-jump resume path. Preserve Home's request ownership contract.
4. Exercise real Pilot key events for entry, Back, filtered/alias jumps, raw mode,
   refresh success/failure and return. Assert selected key, cursor, preview,
   focus, filters and controller state together; helper tests alone are insufficient.
5. Run mutations and all four project checks, inspect the complete diff, and
   write factual acceptance/docs. Preserve all failed attempts and corrections.
   Stop after the authorized implementation checkpoint; do not begin U8/U9.

## Acceptance matrix

| ID | Required evidence |
| --- | --- |
| D01 | Home `h` with focused empty/nonempty table opens one Doctor; filter typing and Home JSON do not open; covered/repeated calls do not stack. Plain Back preserves filters/selection and status/focus. |
| D02 | Real captured fixture produces error/warning/info findings in exact report order and exact message/detail values; all model fields inspectable. Empty, info-only, no-session and zero-skills-with-findings differ. Duplicate rows are retained. |
| D03 | Literal brackets/markup in message/path/detail/rule/context/error survive table/details/notices/JSON. Long values accessible at 100×30 and 60×24, focus/scroll work with Tab/Shift+Tab and keys. |
| D04 | Absolute, displayed-tilde, entrypoint, captured alias and canonical paths match the correct key; dedup same-key aliases; two different rows with the same skill name cannot cross-select. Missing, unmatched, root, lockfile and ambiguous paths stay inline. Broken catalog entry remains selectable. |
| D05 | Real Enter returns to Home with target visible despite prior text and agent filters; All agents, cleared query, selected key, cursor, preview and table focus agree. No Why auto-open. Normal Back preserves filters. Duplicate/delayed close and stale generation/row events cannot alter a newer screen/selection. |
| D06 | Change/delete/add synthetic target files after capture, then open Doctor for the first time; findings/JSON/matching stay frozen. With read probes/doctor/discovery patched to fail after capture, navigation and helper matching still work. |
| D07 | Controlled refresh changes findings and catalog atomically in ordinary and raw modes; matching finding+duplicate occurrence preserved, removed finding falls back deterministically. Late capture rejected; stale Enter never jumps to removed/replaced key. |
| D08 | Pending/retry/refusal/internal-error states, with and without prior snapshot, show honest status and retain published data. No automatic retry; normal unmatched selection remains exit 0, unexpected accepted fault remains exit 3 after recovery. Quit during slow refresh works. |
| D09 | Actual `doctor --json` in the sandbox on unchanged inputs equals Doctor document plus CLI newline; independent expected schema asserts null fields/order and absence of derived/UI data. Raw Back precedence, hidden-action suppression, focus/scroll, selected-finding removal while raw, and refresh document replacement pass. |
| D10 | Home Why requests are canceled exactly on entry, covered Home does not drive/handle results, old callbacks cannot clear newer ownership, and return resumes the correct Home state. Doctor creates no report worker. Retain U3–U6 tests. |
| D11 | Existing recursive source read-only guard includes new module. Full synthetic browsing lifecycle including Doctor/JSON/matched/unmatched jump/refresh/quit preserves target bytes, modes and symlinks; process/editor/network/clipboard actions absent. |

Use literal expected fixture values for representative severity/code/message/detail/
evidence and schema assertions. Do not derive every expected value by calling
the same new helper under test. Include explicit duplicate rows and synthetic
ambiguous display mappings; real captures alone may never produce those shapes.
Add a no-session opening test with controlled delayed first capture, not just
an empty report after successful capture. Use events/barriers for race tests
instead of sleep-based ordering, with bounded waits and owned worker cleanup.

Every new acceptance gate must detect a deliberate failure. Run isolated
control → mutation → restore → control checks with retained commands, failing
test names and outputs; every mutation must fail for the intended reason.
Minimum mutations: reverse findings; alter/drop message/detail/evidence; replace
stored Doctor with a recomputation; disable reverse display-path matching; match
by basename; select first candidate on ambiguity; keep blocking Home filters;
accept stale jump; break Home suspension/owned-token protection; keep stale
Doctor/JSON after refresh; serialize UI-derived data; let hidden Enter jump in
JSON. Existing source-guard category mutations remain mandatory. Mutate only
owned isolated test copies; never leave the reviewed checkout altered. Surviving
mutations block acceptance and require stronger tests or a justified scope repair.

Run in the existing repository environment, preserving full output and exit codes:

```bash
.venv/bin/pytest --cov=skill_lens
.venv/bin/mypy
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Verify the observed combined coverage is at least the unchanged 90% threshold
with `tui/` included, as well as exit codes and coverage failure text. U6 recorded
a coverage failure with a zero process exit once; zero alone is insufficient.
Use whole-package `--cov=skill_lens`, not dotted TUI coverage sources (U6 diagnosed
an asyncio import-identity problem with that instrumentation). Do not lower
coverage, omit files or regenerate snapshots/goldens to gain acceptance.
Human visual approval, hosted checks and local technical acceptance are distinct.

## Planning reviews, verification and freeze

Two separate self-review passes are complete and their corrections are applied.
Pass 1 checked source contracts, captured path identity, event generations and
Home ownership/resume. Pass 2 checked adversarial keyboard/refresh/raw states,
independent expected test values, ambiguity, duplicate findings and handoff clarity.
Both have no unresolved planning blockers. Review reports and exact revision
diffs are retained in `docs/validation/u7/planning/`.

Fresh baseline: 1,220 tests passed, 1 skipped, 90.09% combined coverage with TUI
measured; mypy passed over 44 files, Ruff lint and format checks passed. A separate
sandbox-only probe of existing Doctor serialization, stored alias/display paths,
broken-link row identity and frozen behavior passed. These checks validate the
starting contracts, not the unimplemented Doctor screen. See
[planning verification](../validation/u7/planning/verification.md) for commands,
full outputs, probe correction, plan hash and preservation evidence. The commit containing this frozen document is
the authoritative frozen revision; record its exact SHA in the delivery message
without introducing a self-referential commit field.

No product implementation, worker launch, release, publishing or U8 work is
part of this planning mission.
