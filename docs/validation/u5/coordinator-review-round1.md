# U5 coordinator inspection — round 1, 30 October 2026

Verdict: **changes required**. This is the coordinator's inspection, not either of the two independent final reviews. No product/test files were edited by the coordinator. No implementation commit, push or final acceptance.

## Authority and identity

- Frozen plan: `docs/plans/2026-10-29-tui-u5-diff-json.md` at `af8c65836974aa17eaaec1e7d520a10d8ef63b80`; reference-only commit `a8b86ed`.
- Owner identifies the manual GUI implementer as **River / DeepSeek 4.1 1017 Flash / max effort**. This is owner-provided identity, not runtime readback or upstream attestation. The implementer's original report correctly states that its tools exposed no provider/model/effort evidence. Do not rewrite that report to claim verification.
- The owner requested another manual GUI correction handoff and will return for coordinator verification. Implementer remains edit-only. Independent reviewers are not yet selected or dispatched.
- Pre-existing unrelated work remains excluded: `.path`, `docs/plans/2026-10-26-omp-native-asyncio-trial.md`, `docs/validation/2026-10-25/`, `docs/validation/omp-native-asyncio/`.

## Executed verification

Commands were run once on the delivered implementation:

| Command | Observed result |
| --- | --- |
| `.venv/bin/pytest --cov=skill_lens` | 3 failed, 1166 passed, 1 skipped; 150.60 seconds. Coverage gate failed: 89.94%, required 90%. |
| `.venv/bin/mypy` | Passed: no issues in 41 source files. |
| `.venv/bin/ruff check .` | Passed. |
| `.venv/bin/ruff format --check .` | Failed: `tests/test_tui_diff.py` and `tests/test_tui_json.py` would be reformatted. |

Complete session outputs: `artifact://23` (test/coverage gate), `artifact://10` (static gates). Existing CLI snapshot tests passed without regeneration. The one skip is the existing case-sensitive-filesystem requirement.

A real CLI `tui --sandbox ... --cwd ...` was launched in a new background Rex pane with temporary synthetic HOME. Captures showed ordinary Diff at 100x30, literal Diff JSON at 60x24, return to Why, then Diff over Why at 60x24. Quit returned 0; the owned pane was closed. This is smoke evidence, not complete acceptance or human visual approval. The first smoke invocation mistakenly placed `--sandbox` on the root command, which correctly rejected it with exit 2; it was corrected to the `tui` subcommand. No product defect is attributed to that setup error.

Separate throwaway scripts exercised the actual mounted Textual app for the scroll and long-metadata defects below. Their temporary fixture directories were automatically removed. Mutation verification has not started: fix failing controls and missing behavioral cases first. No coverage exclusions, lowered threshold, snapshot regeneration or fabricated acceptance are permitted.

## Corrections required

### R1 — Existing startup regression test fails

Observed failure: `tests/test_tui_home.py::test_initial_capture_completing_before_home_mount_still_populates_table`, line 1748. The early-capture ordering assertion passed (`mount_statuses == ["ready"]`), but the Home table still contained zero rows instead of the captured `alpha` installation.

Inspect `HomeScreen.on_mount`, its mounted guard/deferred host reconciliation, and the existing test's synchronization. The source alone does not establish whether this is delayed reconciliation or permanently stranded content; that cause remains unresolved. Keep the real early-capture scenario and its nonempty-table/selected-skill outcome. Make post-mount publication reliable. If the test needs synchronization, use a bounded wait for the actual reconciliation event/state while preserving the required early-capture ordering; do not merely increase sleeps, remove assertions, require manual refresh or weaken the scenario.

### R2 — Two new test fixtures do not exercise their claimed conditions

1. `tests/test_tui_diff.py::test_character_budget_truncation_never_claims_zero_omitted_lines`, lines 772–805: `report.truncated` is false. The fixture changes just one 250-character line in an otherwise long file, so the unified diff body does not exceed 20,000 characters. Make the **emitted changed/context body** exceed the character budget without exceeding the 400-changed-line budget. Keep assertions for character-only truncation, positive omitted characters and the meaningful screen notice; do not change the engine or fake truncation flags.
2. `test_diff_content_is_reachable_at_both_terminal_sizes`, lines 837–872: End reaches `max_scroll_y`, but the asserted `TAIL-MARKER-UNIQUE` is not there. A service probe confirmed the fixture's project copy is the baseline, and the marker is emitted as `-TAIL-MARKER-UNIQUE` with **60 diff lines after it**. Place the marker in the actual final retained displayed content (or navigate to its actual location) and retain meaningful compositor-visible keyboard reachability assertions at both sizes. Do not change comparison order or remove the visible-content assertion to make it pass.

### R3 — Repeated unchanged JSON publication loses the reading position

Location: `skill_lens/tui/json_view.py:97–123`, with callers in Home/Why/Diff refresh paths.

Every `show_document`/`show_explanation` rewrites the widget and `_render_text()` calls `scroll_home()` whenever it is displayed, even if the document is identical. In a mounted 60x24 app: enter Home JSON, press End, call the ordinary `app._update_ui()` with the same session/report, and the scroll offset changes **53 → 0**. The same Diff JSON sequence changes **262 → 0**. Both probes quit 0.

Make unchanged publication idempotent: preserve scroll/focus for identical text and avoid needless widget updates. Reset or reconcile scroll only when the owning document/explanation really changes. Do not cache stale report data or weaken generation/agent ownership. Add real-screen regressions covering Home, Why and Diff, including an unchanged status/report synchronization and a genuine document transition.

### R4 — Long valid metadata makes the Diff body invisible under the footer

Locations: `skill_lens/tui/diff.py:152–181,223–231,410–421`.

The full name/path is in an unbounded `height: auto` title outside the report's scrollable area. A valid macOS fixture with a 200-character skill folder name and nine nested project path components (each approximately 72 characters) produces a 22-line title at 60x24. After End:

- Focused Diff body: `Region(x=0, y=23, width=58, height=1)`.
- Footer: the same `y=23`, overlapping the body.
- Body scroll reaches 184/184, but no report line is visible; the title/status occupies the surface.

Keep full metadata keyboard-reachable without letting it consume/overlap the usable body/footer. Prefer the existing scrollable-content layout, not truncating away required information or adding a new navigation framework. Ensure raw JSON also remains usable under the same long metadata. Add compositor-visible reachability tests using valid long names/paths at 60x24 and 100x30; assert meaningful content/focus/footer access, not just positive scroll dimensions.

### R5 — Frozen acceptance scenarios are still missing or weaker than required

The current tests and existing target-preservation lifecycle do not cover these U5 paths sufficiently. Add focused behavioral cases rather than copies of engine/controller tests:

- First **Diff** visit after captured files are edited/deleted, captured settings change, and a fixture symlink is retargeted. Precompute independent same-input expectations before capture/input mutation. Scope filesystem-reader/probe bans to browsing; verify actual Diff/JSON screens stay frozen, then restore the bans and show explicit refresh publishes consistent new data. The current first-JSON-visit test exercises Home JSON after an edit/add only, with no reader/probe bans.
- Real Tab/Shift+Tab focus traversal, scroll keys, `J` return and Esc/Backspace behavior in **all three** JSON owners, especially Diff. Hidden controls must remain excluded/inert and ordinary focus/state must return. Current Diff JSON tests enter then quit, leaving its exit/focus restoration unexercised.
- Controlled old/new capture completion reversal while Diff/JSON is active; a normal refresh-to-next-generation test alone does not exercise the frozen acceptance's older-capture-completes-last transition. Reuse existing synchronization conventions; do not duplicate pure controller coverage.
- Quit while an actual Diff report worker is blocked, with bounded exit and no late result/error update. Existing slow-capture quit proof does not exercise the new Diff worker/screen lifetime.
- Extend the existing synthetic target-preservation lifecycle to traverse Diff and Home/Why/Diff JSON, retaining before/after byte, mode and symlink-target checks. The current lifecycle never opens the new views.
- Cover cache-hit takeover/old-owner cleanup and actual result ordering where existing tests do not. Preserve full generation/request/argument checks. The existing foreign-token test is useful but not itself proof of every real ownership transition.

Use bounded events/observed UI states, not fixed sleeps as proof that a worker completed. These are frozen acceptance obligations, not optional work added to raise coverage. The coordinator will run each control and the plan's separate mutants after corrections.

### R6 — Remove incidental wiring/constant-equality assertions

`tests/test_presentation.py:57–93` expands an exact `__all__` inventory. New helper tests at lines 831–870 and 905–913 include direct equality to imported prose constants. These conflict with the frozen plan's explicit exclusion of forwarding/constant-equality/incidental-wording tests and the project testing rules.

Remove the export-inventory test rather than re-pin it again. Remove/rework new assertions that only compare a helper's returned prose with its own exported constant. Preserve meaningful behavioral tests for baseline/identical/not-compared distinctions, unreadable reasons, binary payload suppression, literal paths/variants and omitted totals at the consumer boundary. Do not replace them with source-text tests or copied wording.

### R7 — Restore the required coverage and formatting gates without weakening them

Coverage is 89.94%; the final tree must meet 90% combined statement/branch measurement, including `tui/`. The omitted lifecycle, mode-return and focus scenarios above are meaningful missing coverage. Do not add bare-not-throw, mock echoes, incidental defaults, pragmas or coverage exclusions to pad the score.

The formatter's requested edits are small and may be made by hand under the edit-only restriction:

- Collapse the `_row_keys` list comprehension to one line in both new test files.
- In the literal JSON fixture, use a single-quoted outer Python string for the frontmatter line containing double quotes.
- Collapse `view_actions = {binding.action for binding in declared if isinstance(binding, Binding)}` to one line.

Do not run a formatter or gate in the GUI correction session; the coordinator reruns verification afterward. Fix any newly authored formatting in the same style.

## Correction handoff rules

Keep the complete frozen product scope. Correct only allowed implementation/test/documentation paths; no engine, controller, serializer, registry, dependency, settings, snapshot/golden, release or workflow-rule changes. Product-code fixes and tests belong to the owner-launched implementer; coordinator records/plan are not editing targets. Preserve the original implementation record as historical session evidence; append a clearly labelled correction report if needed, without claiming tests passed.

Edit only: no tests, linters, formatters, runtime checks, mutation experiments, delegation, independent review, staging, commits or push. Report each R1–R7 disposition, changed files, authored tests, checks not run, remaining blockers and visible identity evidence. Do not suppress a failure or weaken acceptance. If a required fix truly needs excluded scope, report the concrete prerequisite before changing it.

## Reviewed source fingerprints (SHA-256)

```text
d9df38486a9536f18de7f1d2bd8329942cb6061eb18c3c7e1911f79fbdc4ba79  skill_lens/tui/app.py
f8dcda7f0fb74a48484b8295fc99cc0e1863d2ea8112172fc306ec35d0a09841  skill_lens/tui/home.py
bd1beef254cddbebbdf9a3048e92a39d21a22d1a409662de4e8747bfceccddfe  skill_lens/tui/why.py
b636ada01528460b35eba1d3b0c5fc97808c8c08aef53239464aaddcdc24e438  skill_lens/tui/diff.py
e606b4a7fd5ecf24b20231340978f7ecb822552ba08d891c3c624beb1611fb90  skill_lens/tui/json_view.py
37f3903518a6be163f2d5794a78d048659e3efeae4def5787dfb44101477743a  skill_lens/tui/__init__.py
b7459f74745b82f5e477e705816293e522c4ee10291763366f63aa4899028a64  skill_lens/presentation/text.py
58d6941599976292075bcd2e2fd8a2662784f697e43d4dd530734a69653a12b1  skill_lens/presentation/__init__.py
5ae6b974f012e0d49e18e208bb72e2831492ba5419f54b9cbcd75704eafd9bf4  skill_lens/render.py
fa853025f1080c5c6fafff28bc11b73081e3754ca3d21f23371827c5ee27bc1e  tests/test_tui_diff.py
f00b0528d0d19d6f39742b76779ab5b5c5c849fb6eed66c18a1cce6745484008  tests/test_tui_json.py
972c260e11825528a687dc8ede77dc93babd013a52dcaf29b137195d777e81fe  tests/test_presentation.py
ce410ff4b85aa397a87b65201a4952012ce29165da61d684b1dd82a069bd75fa  FULL_SCREEN_TUI.md
07d96c7066adcf341a06641bae7fdc517533c40b3a56c29fee2a2e8a81f7f5c5  DEVELOPMENT.md
c4eea74ed19a14b8b3bcc06068e0b01579d57f85cef67536d09708f91b7d7414  README.md
9cb887404714f2a32f233db9840dceb7174cea45f24fe727060488b5912c20a4  CHANGELOG.md
39e37f418a522705b3924491627ce17d657d1302a25c172373f333d635a21205  docs/validation/u5/implementation-record.md
```
