# Plan: U6 — Agents and Compare

Status: Agreed — owner authorized freeze and commit on 3 November 2026 after two sole-planner self-revision passes.
Authorization: The owner requested U6 planning on 3 November 2026, selected this
Codex session as sole planner, and waived the usual planning and implementation
loops for this phase only. The owner explicitly chose comparison of any two
known agents, including agents with no installed skills. The owner subsequently
approved freezing/committing and specified owner-managed implementation in a new
Luna session, without delegation from this planner.
Reference: `17f92ab0bebcf64e2ec8bf46950613649da06aec` (operative frozen plan; subsequent reference-only commit changes this line only).
Baseline: `198f56e83cb698f4d34f5c8ef736278986cd3bf9` on `main`.

## Outcome

Add two read-only destinations to the terminal interface:

- **Agents:** browse the captured agent definitions, then inspect their policy,
  evidence, source and search-root rules.
- **Compare:** choose two known agents and inspect their shared, diverged and
  one-sided skills, using the same comparison service and JSON as the CLI.

All browsing uses the published session. Only explicit refresh (`r`) captures
new inputs. The line-oriented CLI keeps its output and behavior.

## U6-only execution agreement

- This session writes the plan and performs two thorough self-revision passes.
  There are no planning critics, subagents or council waves. Self-review is not
  described as independent review.
- The owner-selected future implementer is **GPT Luna 6**, exactly as requested.
  The owner starts a new session, selects Luna and its settings there, then tells
  it to implement this frozen plan. This planner does not delegate, launch or
  manage that session. No provider/effort roster or worker dispatch from this
  planning session is a prerequisite to that owner-managed handoff.
- Planning ends with the owner-approved plan freeze and its commits. Product
  implementation starts only when the owner instructs the new Luna session.
- That implementation session carries out the bounded implementation and checks
  directly, including its own corrections, and returns a completion report. The
  normal loop's mandatory independent critic waves are waived for U6. Product
  correctness, isolated tests and the four gates still apply. The owner controls
  subsequent acceptance and Git delivery and may request a separate verification.
- Shared process files and `AGENTS.md` stay unchanged. The exception expires
  with U6; U7 and later phases use their applicable process and authorizations.

## Verified starting point

Read before implementation: [AGENTS.md](../../AGENTS.md),
[the TUI contract](../../FULL_SCREEN_TUI.md) §§8, 9, 10, 21.5–21.7 and 22,
[the CLI specification](../../SKILL_LENS_SPECIFICATION.md) agents/compare sections,
[DEVELOPMENT](../../DEVELOPMENT.md),
[Phase 3 findings](../archive/PHASE3_FINDINGS.md),
[Phase 4 findings](../archive/PHASE4_FINDINGS.md), and
[U5 acceptance](../validation/u5/acceptance.md).

- `SessionSnapshot.registry` already contains captured `AgentDefinition` values;
  `scan`, display paths and the frozen discovery index are also available.
- `snapshot_compare(snapshot, a, b)` validates IDs and calls the existing engine
  with both the captured index and registry. No new comparison algorithm is needed.
- `SessionController` and `SkillLensApp.request_report` already support ordered
  `("compare", (agent_a, agent_b))` requests, generation caches and worker messages.
  Active-screen notifications and synchronization currently handle Home/Why/Diff.
- `agents --json` currently builds its small payload in `cli.py`; comparison
  relation labels live privately in `render.py`. Extract only these shared
  presentation pieces so the new screens do not duplicate or import Rich rendering.
- `JsonView` already displays canonical serialized documents read-only. Reuse it.
- Home already supports suspension/resumption of its Why preview requests. New
  destinations must use this path rather than leave hidden Home work running.
- Existing `.path` and `docs/validation/2026-10-25/` are unrelated untracked work.
  Preserve them and exclude them from this phase's commits.

This is a high-risk UI integration because keyboard focus, background work and
refresh publication interact. The risk is addressed by explicit state rules,
behavioral tests and the two self-revisions requested by the owner.

## Allowed scope

| Paths | Permitted change |
| --- | --- |
| `skill_lens/tui/agents.py` (new) | Agents table, captured detail pane and JSON mode. |
| `skill_lens/tui/compare.py` (new) | Two-agent picker, comparison result, ownership and JSON mode. |
| `skill_lens/tui/app.py` | Home-only open/close adapters, new-screen sync and Compare outcome routing. |
| `skill_lens/tui/home.py` | `g`/`c` actions and discoverable footer hints; preserve existing filters and preview behavior. |
| `skill_lens/presentation/agents.py` (new), `presentation/state.py`, `presentation/text.py`, `presentation/__init__.py` | Canonical agents summary payload, shared comparison labels/styles and empty-result text. |
| `skill_lens/cli.py`, `skill_lens/render.py` | Narrow imports/calls for the shared extraction; preserve existing output exactly. |
| `tests/test_tui_agents.py`, `tests/test_tui_compare.py` (new) | New consumer behavior and controlled-race tests. |
| `tests/test_tui_json.py`, `tests/test_tui_home.py`, `tests/test_tui_app.py`, `tests/test_tui_read_only.py`, `tests/test_presentation.py`, `tests/test_cli.py`, `tests/test_render_snapshots.py` | Focused integration, parity and safety coverage where it belongs. |
| `FULL_SCREEN_TUI.md`, `DEVELOPMENT.md`, `CHANGELOG.md`, `docs/validation/u6/` | Clarify §8.7 and the §22 U6 gate to count registry choices; document `g`/`c`, factual delivered state and evidence. |

Engines, controller, snapshot/model contracts, registry TOMLs, dependencies,
packaging, version numbers and existing snapshot/golden files are outside scope.
Doctor, general help/polish and release work remain U7–U9. A required change to an
excluded contract is reported before expanding scope.

## Screen and keyboard contract

### Home entry and return

- Add `g` for Agents and `c` for Compare to Home's ordinary browsing mode.
  Both work even with an empty skill table or before the first capture; the new
  screen then explains the session state. Neither requires a selected skill.
- Actions are inert while Home is suspended or displaying JSON. A focused text
  filter receives typed `g`/`c` normally. Do not use priority bindings that steal
  these letters from the input. Other screens gain no global entry shortcut.
- Open from Home only; a repeated open cannot stack another destination. Suspend
  Home before pushing. The new host close adapters receive/check the expected
  screen instance, not merely its class: an old delayed callback cannot close a
  later instance. Clean up only that instance's request before popping, then
  resume Home and synchronize through the existing lifecycle. Explicit resume
  and Textual's `ScreenResume` must be harmless when both occur.
- Return preserves Home's query, agent filter, canonical selection and usable
  scroll position. A refresh while Home was covered uses its existing generation
  reconciliation; a removed selection follows the current Home fallback.

### Agents

- One `AgentsScreen` contains a registry table and a scrollable detail pane.
  List definitions sorted by agent ID, including agents with no detected skills.
  Columns match CLI summary facts: name, ID, collision policy, policy evidence,
  root count. Empty registry has an explanatory empty state.
- Selecting a row updates details from that captured definition. Show identity
  source, collision/coexistence policies, policy evidence, source URL as literal
  text, walk boundary, unsearched/disabled/ambiguous rule metadata when present,
  and every root in stored order. Root details show ID, kind, literal path
  template, scope, rank, rule IDs, evidence, base, entry format, recursion and
  optional loadability. Include each root's optional nested/file rule IDs and the
  agent's literal disabled-settings/key metadata. Label absent optional fields
  plainly; retain the registry's evidence values without strengthening them.
- A root template is a definition, not evidence that a directory exists. Display
  it literally; no expansion, existence probe, link resolution or browser launch.
- Up/down and `j`/`k` navigate the focused list. Enter transfers focus to details;
  Tab/Shift+Tab reach both panes. Esc/Backspace from details returns focus to the
  list; from the list closes to Home. A scrollable details pane uses its own
  scrolling keys rather than moving the hidden list.
- `J` shows the complete agents summary array, not the selected definition or an
  invented detailed-agent schema. Keep ordinary selection/scroll/focus for return.
  A captured empty registry honestly serializes as `[]`; no captured session has
  no document and shows its actual session explanation.

### Compare picker and result

- One `CompareScreen` has picker and result modes. The picker has two labeled
  columns A and B, each listing every captured registry ID in sorted order.
  Highlighted rows and confirmed selections are distinct; show the confirmed
  name/ID for each side. Initial selections are unset.
- Enter in A confirms that row and moves focus to B. Enter in B confirms that
  row and attempts comparison. A keyboard-reachable Compare button also submits
  the selected pair. Tab/Shift+Tab move between controls; up/down and `j`/`k`
  operate the focused list only.
- Both IDs must be present in the current captured registry and distinct before
  any worker request. Missing selections explain which side is needed. A duplicate
  shows `Pick two different agents.` inline. Unknown IDs use the existing CLI
  error body from `validate_compare_agents` (`exc.args[0]`, without Python's
  extra exception quotes). These input errors keep normal quit at exit 0.
- The owner settled the §8.7 ambiguity: detection is not an eligibility filter.
  A registry with at least two known agents permits comparison even with zero
  detected agents. Fewer than two **registry definitions** shows available names
  and how many more are needed; submission is unavailable. An empty comparison
  remains a valid report: `Neither agent has any skills installed.`
- A valid submission enters result mode, requests the ordered pair and shows
  loading until accepted. Clear previous report/JSON before a different pair is
  labeled or requested, including a new pair in the same generation. The result
  shows A/B names and IDs, all four relation
  counts, the model's entries in their existing order, each name/relation/path
  A/path B and all diagnostic notes. Missing paths display `-`; present paths
  use `snapshot_path`. Never infer sharing from names or paths in the UI.
- Verified shared content, genuine differences, unreadable/unverifiable content
  and one-sided entries retain engine meaning. Preserve notes that explain why
  an unverifiable entry is labeled diverged. Reverse A/B is a different ordered
  request and JSON report.
- In result mode, Esc/Backspace cancels only owned pending work and returns to
  the picker with its choices retained. From the picker it returns to Home.
  Returning to the same pair can use the current-generation cache.
- On return to the picker, focus B for correcting or resubmitting the pair. Invalid
  submissions keep the picker and its choices visible; focus the first missing or
  unknown side, or B for duplicates. Clear a superseded input error when the user
  confirms a replacement choice or a new generation changes eligibility.
- `J` toggles JSON in result mode, including its loading/error explanation.
  In the picker it is inert because no report is selected. Raw mode freezes
  hidden picker/list actions. Esc/Backspace leaves raw mode first; the next
  press performs the ordinary back action.

### Shared modes and layout

- New screens use `q`/Ctrl-C and `r` through the current app contracts. Render all
  dynamic text literally, with formatting applied separately. No terminal prints,
  renderer imports, export, clipboard, editor, subprocess or network actions.
- Retain ordinary widgets while JSON is visible. Hide them from display and
  keyboard focus, focus `JsonView`, then restore a still-mounted visible focus
  target on return, with a safe pane fallback if refresh rebuilt that target.
  Status-only updates and unchanged data must not remount the content or reset
  scroll/focus. Agents JSON does not change as ordinary row selection changes.
- Both screens remain usable at 100×30 and 60×24. At narrow width, stack panes;
  names, long paths/root definitions and notes stay reachable by scrolling.
  Header/footer and error/status messages must not bury the controls.

## Captured data, serialization and worker ownership

1. Add one pure `agents_payload(definitions)` helper in `presentation/agents.py`,
   accepting captured definitions and sorting by ID. Preserve the exact CLI
   keys/types: `id`, `name`, `collision_policy`, `policy_evidence`, `roots` (count).
   Use it from the existing CLI JSON branch and Agents JSON. It performs no reads
   or registry loading. Keep its public types explicit and free of `Any` escapes.
   Move `_RELATION_LABEL` unchanged to `RELATION_LABEL` in `presentation/state.py`
   and re-export it; both adapters consume it without Rich/Textual in that package.
   Extract the existing empty-comparison sentence to `COMPARE_EMPTY_TEXT` in
   `presentation/text.py`, re-export it and use it in both renderers. Leave
   relation classification, counts and note generation in the existing model/engine.
2. Agents reads only `controller.current.registry`; it never allocates a report
   request. Compare uses `app.request_report("compare", (a, b))`, which calls the
   existing snapshot service off the UI thread. Reuse `JsonView` and `models.dumps`.
   Compare JSON is exactly `dumps(accepted_report.to_dict())`, with no added
   serialized counts/fields. CLI byte comparisons include the emitter's final LF.
   Agents/Compare synchronize after composition using the established mounting
   guard/post-mount update pattern; a fast initial capture must not leave an
   uninitialized screen or attempt to update widgets before they exist.
3. Compare owns at most one complete `ViewRequest`: generation, request ID, view
   and ordered arguments. Read the cache first; deduplicate an already owned active
   request before dispatch. On a cache hit, cancel any previous owned request before
   displaying the cached pair. Release/cancel only when the controller's full active
   token still equals the screen's owned token. Inspect the full token before
   cleanup on submit, back, close or unmount. Ordering `(a, b)` is never sorted
   or normalized into an unordered cache key.
4. Extend both success/error app notification routes to Compare after controller
   acceptance. The screen accepts data only for its matching full token and current
   pair. Late completions/errors after back, pair change, refresh or quit cannot
   change a new screen, cache, display or sticky failure state.
5. While capture is pending, old published data remains usable with an honest
   scanning status. A failed/changed/refused capture retains old data and its
   existing explanation. With no published snapshot, display the actual loading,
   refused, retry, error or idle state; do not fabricate an empty registry/report.
6. On publication, reconcile new registry IDs before rendering. Agents preserves
   its selected ID when available, otherwise chooses the first or the empty state.
   Compare clears old report/JSON and token references, preserves still-valid
   ordered choices and recomputes a previously submitted valid pair for the new
   generation. If a chosen ID disappeared, clear that side's confirmed choice,
   retain the other valid side, return to the picker and explain the missing ID;
   never silently compare a different pair. An open picker stays a picker.
   If this invalidates a raw result, clear its document, leave JSON mode and focus
   the picker in that same transition. A still-valid submitted pair stays in its
   current ordinary/JSON mode while its new-generation report is loading.
   Rebuild suppression must ignore queued row-selection events from old widgets.
7. Keep report loading/failure distinct from capture status. An accepted unexpected
   report fault uses the existing in-memory error path, leaves no fake report and
   yields sticky exit 3. Avoid a redraw-driven retry loop after failure. Ordinary
   input errors are resolved before dispatch; do not change the controller's generic
   worker-error policy to turn internal faults into user input errors. Track local
   report state (`idle`, `loading`, `ready`, `error`) for its generation/pair;
   `error` never auto-requests on sync. Retry requires back-and-submit or publication
   of a new capture. Sticky exit-3 state remains sticky even if a retry succeeds.

## Implementation sequence after freeze

1. In the owner-started Luna session, read this frozen contract and verify its
   reference and checkout. Report visible model/settings honestly; mark unavailable
   identity details as unverified. Establish passing baseline gates, preserve
   unrelated work, and inspect the referenced source/tests. Construct synthetic
   fixtures and independent CLI oracles before capturing or editing fixture inputs.
2. Extract the agents payload and comparison relation map. Verify unchanged CLI
   agents JSON and render output; add only meaningful shared-consumer checks.
3. Add Agents and its Home-only navigation, registry reconciliation and JSON.
4. Add Compare picker/result states, existing worker adapter integration, exact
   ownership/cancellation, generation reconciliation and JSON.
5. Exercise the acceptance matrix below; run targeted mutation experiments in
   disposable copies. Correct product/test findings in that same implementation session.
6. Run all four gates on the final integrated tree. Inspect the actual diff against
   this contract and return retained check evidence, mutation outcomes and any
   limitations to the owner. Update delivered-state docs only when their claims
   are established; distinguish implementer verification from later owner acceptance.

The implementer may edit only allowed paths, run focused/full checks, format only
explicit changed Python paths and exercise the UI with synthetic inputs. It returns
a report and leaves staging, commits and delivery for separate owner authorization.
An out-of-scope prerequisite is reported; it does not authorize dependency
installation, settings changes, permission bypasses or a replacement implementer.

## Acceptance matrix

All UI tests use real Textual Pilot key/focus events and temporary HOME via the
existing fixtures, sandbox and protected-system-root guard. Synchronize races
with bounded events/predicates. Create CLI expected results on the same unchanged
synthetic inputs before capture. Do not use the new helper as its own sole oracle.

| Area | Evidence required |
| --- | --- |
| Home navigation | `g`/`c` work with rows, empty table and initial capture pending. Typed letters stay in the filter; JSON/suspended Home cannot launch screens. Back retains filters, key and meaningful scroll; repeated entry never stacks duplicates. |
| Agents facts | All registry definitions sorted by ID; correct summary and full root/policy/evidence details, including optional and absent fields. Known-but-undetected agents remain visible; empty registry is distinguished from no capture. |
| Picker | Actual A/B keyboard selection, button submit, same-ID and missing/unknown-ID input errors; zero/one registry definitions explain the shortfall. Zero/one detected agents with a larger registry still permit comparison. Unknown-ID tests exercise a controlled stale selection/event against a changed captured registry; ordinary UI never offers an unknown ID. Validation failure dispatches no worker and keeps `failed` false. |
| Report fidelity | Actual widgets show all four relation types/counts, mirrored A/B order, per-agent paths, notes, empty report and unverifiable-content explanations. Preserve independent identical copies as shared; no UI reclassification. |
| JSON | Agents array and Compare document match independent existing CLI semantics and actual emitter bytes including final LF; Unicode/brackets/long paths remain literal. Picker has no report JSON; loading/fault/refusal explains instead of fabricating JSON. |
| Raw-mode navigation | JSON owns focus; ordinary widgets cannot act while hidden; Tab/Shift+Tab and scroll keys work. Back exits raw mode before navigating; list/picker/scroll/focus restore safely. Use content large enough to establish an asserted positive scroll offset before checking its restoration. |
| Frozen first visits | After capture, edit skill bytes/settings and retarget a synthetic link, then first visit both new screens. Original results remain until explicit refresh. Change only a synthetic registry fixture/provider to test frozen definitions. Block live registry/discovery/display helpers and target-specific reads/probes during navigation; leave framework/package reads and explicit capture available. |
| Ownership/cache | Repeated redraw does not restart work, including after an accepted fault; reopen cached pair while a different pair is pending and reject that pair's late success/error; reverse ordered pair; A/B results complete out of order; back/reopen and old-screen cleanup cannot cancel or overwrite a newer token or close a new screen instance. Stale errors cannot poison exit state. |
| Refresh | Refresh in Agents details/JSON and Compare picker/result/JSON; publication clears old report/JSON before new generation appears. Preserve valid choices; invalidation exits raw result mode into the explanatory picker; handle removed IDs without substitution. A still-valid raw result stays raw while loading its replacement. Retain usable data after failed/refused capture. Cover initial refusal/fault without a capture and older capture finishing last. Covered Home reconciles when returned to. |
| Fault/quit | Accepted unexpected fault produces plain-English status, in-memory details and exit 3; stale faults remain harmless. Quit during capture/Compare is prompt under existing bounded tests, exits 0 normally and ignores late callbacks. |
| Layout/safety | Both terminal sizes, keyboard access to long details/notes, recursive existing source guard includes new modules, and target fixture bytes/modes/link targets remain unchanged. Existing CLI snapshots/goldens need no regeneration. |

Primary new tests belong in `test_tui_agents.py` and `test_tui_compare.py`.
Extend existing JSON, Home/app and target-preservation suites only where those
consumers are involved; retain U3–U5 regression coverage.

Mutation evidence must prove that relevant acceptance tests fail when: navigation
steals filter input; the picker wrongly filters to detected agents; first visits
reload live registry/files; A/B are reordered; stale result or error is accepted;
old-owner cleanup cancels a newer token; refresh retains old JSON under new data;
invalid choices dispatch a worker; redraw automatically retries a report fault;
a delayed close pops another screen instance; raw-mode actions move hidden
controls; or dynamic text is parsed as markup. Treat stale success and stale
error as separate mutants. Record a passing control, intended behavioral
failure and restored pass for each, with no live target or developer-tree mutations.
Surviving in-scope mutations block acceptance.

Required full gates, with existing thresholds and expected outputs:

```bash
.venv/bin/pytest --cov=skill_lens
.venv/bin/mypy
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Coverage remains at least 90% combined coverage with branch measurement enabled
and `tui/` included. Format only explicit changed Python files when needed.
No install, coverage exclusion, snapshot/golden regeneration or unrelated repair
is authorized by a test failure. Document blockers rather than weaken checks.

## Planning revisions and verification

- Initial draft: written from the current captured-service, controller, CLI and
  UI contracts; owner resolved the known-versus-detected picker ambiguity.
- Self-revision 1 — source/lifecycle and scope audit completed. Added instance-based
  close guards, mount-safe first synchronization, explicit root/disabled metadata,
  ordered cache identity, old-pair clearing, removed-ID reconciliation and terminal
  report-error state with explicit retry. Checked these decisions against
  `app.py`, `home.py`, `diff.py`, `session.py`, `snapshot.py`, registry/model fields
  and the existing UI/controller tests; no controller/engine change is needed.
  A standalone synthetic-home smoke confirmed ten captured registry definitions,
  zero detected agents and a successful empty Claude/Codex comparison, the existing
  agents JSON keys/order and both existing validation messages. The initial smoke
  used positional arguments for keyword-only `capture_session`; correcting the
  call made it pass without changing product code.
- Self-revision 2 — acceptance, keyboard/error and handoff audit completed. Added
  shared empty-result wording, precise picker error/back focus, empty-registry JSON,
  unchanged-data scroll preservation, raw-mode exit when refresh invalidates a pair,
  nonzero-scroll evidence, target-scoped read bans, explicit worker edit/check/report
  permissions and the spec/keymap clarification. Checked final UI transitions
  against the acceptance matrix and separated stale-success/error mutations.
  No independent reviewer or implementation agent was launched.
- Owner freeze clarification — 3 November 2026: freeze/commit is authorized;
  the owner will create the implementation session and select Luna. Removed
  planner-dispatch/route-confirmation and automatic coordinator-handoff assumptions.
  Product behavior, allowed scope and acceptance checks are unchanged.
- Fresh planning baseline on 3 November 2026: all four commands exited 0;
  **1192 passed, 1 skipped**, **90.15% combined coverage**, mypy clean over 41 source
  files, Ruff lint clean and 392 Python files already formatted. The skip requires
  a case-sensitive filesystem. Product/test code still matches the baseline commit.
  Complete command outputs and the existing-service smoke are retained in the
  [planning verification record](../validation/u6/planning/verification.md).
  These checks validate the starting point, not the unimplemented U6 screens.

## Freeze and later delivery

The owner approved freeze and commit on 3 November 2026. Commit the agreed plan,
then fill `Reference:` with that first full hash in a reference-only commit. Keep
planning evidence in a separate scoped commit so the operative contract and its
reference remain clear. Preserve unrelated work. Push the authorized planning
commits under the owner's existing delivery preference and verify local, tracking
and remote references. No product implementation or worker launch is part of this freeze.

Later implementation reports configured model/settings, changed files, exact
check commands/results, mutation outcomes, deviations and remaining limitations.
Any later owner-requested independent verification is separate from that report. Neither a
plan freeze nor local technical acceptance claims human visual approval, hosted
CI acceptance, release/publishing, or permission to begin U7.
