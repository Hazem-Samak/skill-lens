# Plan: TUI visual polish — make the Skill Lens browser beautiful

Status: Agreed
Authorization: user instruction, 2026-11-08 — "make my TUI looks beautiful … It's
functional and it's good right now … It's in a stable version and stable
condition. I don't want you to change anything regarding the back end or how it
works. I just want the TUI to look beautiful … polished, not as simple as it is
now … keep the ease of use. You will be the orchestrator and the implementer.
You will have one reviewer: River deepseek V4.1 1017 max from OMP … Don't ask me
about anything. You have a goal and you have control. Make this application look
beautiful"

Roster:
- coordinator: `minimax/MiniMax-M3.1-Flash` — the session running this plan
  (requested by the user; configured identity confirmed by the session banner).
- implementer: `minimax/MiniMax-M3.1-Flash` — the same session. The user
  explicitly assigned "orchestrator and the implementer" to one agent for this
  mission, which is the permitted exception to council §1 role separation. The
  implementer does not review its own work; the OMP critic is a separate process.
- plan critic and final critic: `river/deepseek-ai/DeepSeek-V4.1-Flash-1017`,
  thinking `max`, via the `omp` CLI (`omp models find deepseek` shows exactly one
  river entry with thinking levels `low,high,max`; `omp models` confirms the id).
  Requested by the user; confirmed from the relay receipt at dispatch.

Reference: `c085e2284b3b4aab34690c27c8b0c336b0ea6bec` — the freeze commit for
this plan. The second commit records only this reference; it does not change
the frozen contract.

Risk and review: **Normal** (council §5). The change is presentation-only inside
`skill_lens/tui/`: colours, typography, borders, padding and span styling. It
does not touch `core/`, `models/`, `registry/`, `render.py`, `cli.py`,
`presentation/`, the resolver, the discovery rules, the snapshot service, the
exit-code contract or any file on the user's disk. Normal risk therefore needs
one independent critic at plan stage and one at implementation stage — exactly
the single-reviewer roster the user named.

Expected child tasks: 3 — plan critic (OMP, read-only) + implementer (this
session) + final critic (OMP, read-only). The plan critic has already run and
its findings are resolved below; a correction round, if the final critic needs
one, stays inside this phase.

---

## Outcome

The full-screen browser looks like a finished product instead of a first
working draft: one coherent dark theme, a clear visual hierarchy (title →
toolbar → content → status → key hints), semantic colour used only where it
carries meaning, and readable detail panes instead of walls of identical
monospace text.

Nothing about *how it works* changes. The same keys do the same things, the
same screens open, the same text is shown, the same JSON is produced, and the
same exit codes are returned.

## Current state

Verified by reading the source and by rendering the running app to SVG and
rasterising it (screenshots at 140×42, kept in `docs/validation/tui-polish/`).

**Screens** (all under `skill_lens/tui/`): `home.py` (1665 lines), `why.py`
(1252), `compare.py` (1102), `doctor.py` (902), `diff.py` (880), `agents.py`
(612), `help.py` (325), `session.py` (378), `json_view.py` (138),
`app.py` (711). Every screen carries its own `DEFAULT_CSS` block; there is no
shared stylesheet and no registered Textual theme.

**What the interface looks like today**

1. *Three stacked identity lines.* Textual's `Header` renders `⭘  Skill Lens —
   0.2.0`, and each screen then adds its own bold title line (`Skill Lens
   Home`, `Agents`, `Doctor`, …). The result says "Skill Lens" three times.
2. *No theme.* The stock Textual dark theme is in force: a saturated blue
   primary, a heavy blue scrollbar, one background colour for everything.
3. *No hierarchy.* Headings, field labels, values, paths and hashes are all the
   same bold monospace in the same colour. A detail pane is a wall of
   `Label: value` lines with nothing to separate it.
4. *Unstructured tables.* Column headers are plain; rows have no zebra, no
   padding, and cells are clipped mid-word (`Antig`, `empirica`, `document`).
   Semantic values (parse mark, severity, resolution state) are not coloured.
5. *Loud separators.* Pane splits are a solid `$primary` vertical rule; scroll
   bars are thick saturated blue blocks that dominate the right edge.
6. *Wasted space and duplicated chrome.* The Home table leaves most of the
   pane empty, the preview pane has a large void below its content, and Home
   carries both a hand-written keymap line and the Textual `Footer`, so the
   bottom of the screen shows two competing key bars.
7. *Status lines float.* `Ready: 9 skills discovered` sits unstyled above the
   footer.

### The behaviour contract (from the source and the test-suite)

**Every widget id, widget type and composition stays.** Only CSS and
markup-free span styling change. The test-pinned ids include
`#skill-table`, `#preview-pane`, `#preview-scroll`, `#status-text`,
`#legend`, `#agent-filter`, `#empty-state`, `#catalog-note`,
`#error-details`, `#removal-notice`, `#doctor-jump-notice`, `#filter-input`,
`#footer-help`, `#home-body`, `#home-json`, `#why-body`, `#why-title`,
`#why-agent-strip`, `#why-status`, `#why-report-status`, `#why-candidates`,
`#why-json`, `#diff-body`, `#diff-title`, `#diff-content`, `#diff-status`,
`#diff-error-details`, `#diff-json`, `#agents-body`, `#agents-table`,
`#agents-detail`, `#agents-detail-scroll`, `#agents-empty`, `#agents-status`,
`#agents-json`, `#compare-picker`, `#compare-columns`, `#compare-a-table`,
`#compare-b-table`, `#compare-selection`, `#compare-registry-message`,
`#compare-input-error`, `#compare-submit`, `#compare-result`,
`#compare-status`, `#compare-json`, `#doctor-body`, `#doctor-findings`,
`#doctor-detail`, `#doctor-detail-scroll`, `#doctor-summary`,
`#doctor-context`, `#doctor-navigation`, `#doctor-empty`, `#doctor-status`,
`#doctor-json`, `#help-frame`, `#help-title`, `#help-body`, `#help-content`,
`#help-session`, `#help-close`, and the JSON views.

**No widget is added, removed or re-parented.** In particular:

- `#agent-filter` stays a non-focusable `Static` with its exact text
  (`"Agent: All agents"`, `"Agent: <label> (<id>)"`) — it never becomes a
  Button, so the three-Tab route to the preview is untouched.
- `#footer-help` stays a `Static` and keeps naming the keys it names today.
  It is restyled, not deleted; the Textual `Footer` stays too.
- The Why agent strip stays a `Horizontal` of `Button`s with ids
  `why-agent-<id>`. It is never replaced by a `Tabs` widget, and the focused
  widget stays the exact `#why-agent-<id>` button.
- The Help body stays one `#help-content` `Static`; no DataTable, no extra
  focusable child, and the `"r — "` row format stays.
- The Diff title stays the first `Static` **inside** `#diff-body`; no new
  scroll structure, so long metadata still scrolls instead of pushing the
  footer off screen.
- The `narrow` and `json-mode` rules of every screen stay as they are.

**Pure builders keep returning `str`.** `preview_text`, `agent_detail_text`,
`finding_detail_text`, `doctor_summary` and `build_help_body` are compared
against exact strings by the tests, so they keep their signature and their
characters. Styling is applied in the *screen adapter*, on the string the
builder produced. Where a screen needs a styled preview, a second helper
(`preview_content`) returns the styled `Content` and `preview_text` stays
`str(preview_content(...))` — one source of truth, same characters.

**No glyph, prefix, indent or extra line is added to any reported text.**
Rules and separators are CSS borders, never characters.

**Read-only is untouched.** No new write, no `subprocess`, no file access
beyond the capture that already exists. The app keeps neutralizing
`save_screenshot`, `action_screenshot` and `deliver_*`.

**Tooling available:** Textual 8.2.8 (custom `Theme` objects,
`App.register_theme`, component classes such as `datatable--header`,
`datatable--cursor`, `datatable--odd-row`, `Content` / `Content.assemble` /
`Content.styled` for markup-free styling), and the existing `.venv` with
`pytest`, `mypy`, `ruff`.

## Scope and boundaries

**Allowed to change**

- `skill_lens/tui/theme.py` (new): the brand theme and the shared, markup-free
  styling helpers used by every screen.
- `skill_lens/tui/app.py`: register the theme, restyle the app-level chrome
  (`format_title`), no change to navigation, workers, controller or exit codes.
- `skill_lens/tui/home.py`, `why.py`, `diff.py`, `agents.py`, `compare.py`,
  `doctor.py`, `help.py`, `json_view.py`: stylesheet, layout and content
  styling only.
- `tests/test_tui_visual.py` (new): tests for the visual layer.
- `tests/test_tui_packaging.py` and `scripts/smoke_wheel.py`: **manifest
  bookkeeping only** — add `skill_lens/tui/theme.py` to `EXPECTED_TUI_MODULES`
  / `REQUIRED_TUI_MODULES` and `tests/test_tui_visual.py` to
  `EXPECTED_INSTALLED_TEST_SUITES` / `INSTALLED_TUI_TEST_SUITES`, so the two
  closed manifests stay equal and the new module and test ship in the wheel.
  No other line of either file changes.
- `docs/validation/tui-polish/`: before/after screenshots and the notes that
  accompany them.

**Must not change**

- Any file outside `skill_lens/tui/`, `tests/`, `docs/` and the two manifest
  files named above — in particular `core/`, `models/`, `registry/`,
  `presentation/`, `render.py`, `cli.py`.
- Any key binding, action, screen, message, worker, cache or generation rule.
- Any displayed text, and any widget id, type or composition.
- The read-only guarantee.

**Out of scope**

- New features (grouping the Home list by scope, a light theme, a theme
  switcher, mouse support, icons). The user asked for beauty and ease of use,
  not new capability.

## Implementation steps

### 1. `skill_lens/tui/theme.py` — the design system

- A `Theme` named `skill-lens`, registered by the app, with one coherent
  palette. `Theme.variables` keys are **bare names** (Textual resolves them as
  `$name`), never `--name`:

  | role | value | used for |
  |---|---|---|
  | `background` | `#0d1117` | the app canvas |
  | `surface` | `#161b23` | header, footer, status strip |
  | `panel` | `#1c2430` | table headers, chips |
  | `foreground` | `#c8d3e0` | primary text |
  | `primary` | `#4ec9c4` | the lens teal: active tab, rules, title |
  | `secondary` | `#7aa2f7` | informational accents |
  | `success` | `#57ab5a` | active / valid / ok |
  | `warning` | `#d29922` | shadowed / warning / needs attention |
  | `error` | `#e5534b` | invalid / error |
  | `accent` | `#b083f0` | ambiguous, secondary highlight |
  | `boost` | `#232d3a` | hover surfaces |
  | `muted` (variable) | `#8b98a8` | labels and captions (≈5.4:1 on the canvas) |
  | `rule` (variable) | `#31415a` | hairline separators (≈1.9:1 on the surface) |
  | `keycap` (variable) | `#2b3644` | keycap chips |
  | `block-cursor-background` | `#1f3b3d` | the selected row: a dark teal tint |
  | `block-cursor-foreground` | `#d8f3f1` | the selected row's text |

  The selected row is a *tint*, not the bright accent: light text on a dark
  teal surface keeps ≈8:1 contrast, where the bright accent as a background
  would drop to ≈1.3:1.

- A **state palette** for the TUI: `HeadlineState` → the palette above
  (`ACTIVE` success, `COEXISTS` secondary, `SHADOWED` warning, `DISABLED` /
  `UNSEARCHED` muted, `INVALID` error, `AMBIGUOUS` accent). The shared
  `presentation.STATE_STYLE` table keeps the *meaning*; the TUI maps that
  meaning onto its own colours so the CLI and the TUI cannot drift, and no
  Rich palette name leaks into the terminal.

- Markup-free helpers, all built on `Content`, so nothing is ever parsed as
  Rich markup:
  - `literal(text)` → `Content.from_text(text, markup=False)`.
  - `field(label, value, style)` → dim label + bright value, the same
    characters as the plain `"Label: value"` string.
  - `styled_line(text)` → one `"Label: value"` line, with a note in yellow and
    the report headline in its state colour.
  - `fact_block(text)` → a block of such lines, characters unchanged.
  - `help_block(text)` → the Help body: section headings in the accent, the
    key part of a row in bright text.
  - `state_cell(text)` → each state name in a comma separated list in its own
    colour.
  - `keycap(key, label)` → a key on a chip, the action dim.
  - `notice(text)`, `heading(text)`, `muted(text)`.

- A shared `APP_CSS` with the chrome every screen uses: the top bar, the
  bottom key bar, tables (header, zebra, cursor), inputs, tabs and scrollbars
  — so the seven screens stop each carrying a private copy of the same rules.
  Zebra striping needs `DataTable.zebra_stripes = True`; the CSS alone is
  inert.

### 2. `app.py` — chrome

- Register the theme in `__init__` and set `self.theme = "skill-lens"`.
- Override `format_title` so the header reads `◉ Skill Lens` with the version
  dimmed. The stock `⭘` glyph is hidden with `HeaderIcon { display: none; }` —
  the lens glyph comes from the title, so exactly one mark is shown.
- Apply `APP_CSS` to the app so every screen inherits the same look.
- Keep `Header`, `Footer`, the bindings, the worker machinery and the exit
  path exactly as they are.

### 3. Screens — one shared anatomy

Every screen becomes: **header bar → screen title → content → status → key
hints**, with the content area split into a list pane and a detail pane that
are separated by a hairline rather than a loud blue rule.

- **Home**: the toolbar becomes a real search field (an underlined input) plus
  an agent chip on the right; the legend becomes a dim caption; the table
  gains a muted header, zebra rows, an accent cursor row and a coloured parse
  mark; the preview pane becomes a card — dim labels, bright values, the path
  and hash muted, the description set apart; `#footer-help` becomes a keycap
  hint bar that still names every key it names today.
- **Why**: the report block keeps every line and its exact characters, with
  dim labels and bright values; the agent strip reads as a row of tabs with
  the current one highlighted; the candidate bodies get the same field
  treatment.
- **Diff**: the title and the `Copies:` / `Baseline:` facts stay inside the
  scroll body and gain a rule; each copy heading keeps its mark, path, variant
  and status; the unified diff keeps its existing line colours.
- **Agents**: the table is styled like the Home table; the detail pane uses
  the same field treatment.
- **Compare**: the two pickers get card-like headers; the selection line and
  the registry message are styled by severity.
- **Doctor**: the summary is styled, the severity column is coloured (error /
  warning / info), and the detail pane uses the same field treatment.
- **Help**: the modal gets a rounded border, a dimmed backdrop, a styled title
  and styled section headings inside the existing single `Static`.
- **JSON views**: monospace, muted chrome, the same surface treatment.

### 4. Row budget

No screen may lose rows that the tests measure. The header and the footer keep
their current height unless a test proves otherwise, and every rule that costs
a row is checked against:

- `#why-candidates` height `>= 4` at 60×24,
- `#diff-body` region height `>= 8` and `body.virtual_size.height >
  body.region.height`,
- Home's preview fully visible without scrolling in the wide case, and
  reachable after six `down` presses in the clipped case.

Vertical separators (a hairline between two panes) cost a column, not a row,
and are preferred over horizontal rules.

### 5. Verification harness

- A screenshot harness **outside the repository** (`/tmp`) that builds a
  synthetic home from the project's own `tests/fixtures/scenarios.py`,
  monkeypatches `paths.home`, and runs the app headless at 140×42, 100×30 and
  60×24. It uses `App.export_screenshot()` — never `save_screenshot`, which the
  app neutralizes for the read-only guarantee — writes the SVG outside the
  checkout, and rasterises it to PNG with macOS `qlmanage` for review.
  Committed evidence is scrubbed of absolute paths.
- Every screen is opened through deterministic Pilot key presses on the
  synthetic scenario.

## Acceptance

- `pytest --cov=skill_lens`, `mypy`, `ruff check .`, `ruff format --check .`
  all pass on the final tree, with the evidence produced by the coordinator.
- Every existing TUI test passes unchanged — no test is edited to make a
  visual change pass.
- The two closed manifests stay equal, and the wheel ships the new module and
  the new test: `tests/test_tui_packaging.py` and `scripts/smoke_wheel.py`
  agree on `EXPECTED_TUI_MODULES == REQUIRED_TUI_MODULES` and
  `EXPECTED_INSTALLED_TEST_SUITES == INSTALLED_TUI_TEST_SUITES`.
- New `tests/test_tui_visual.py` proves the layer is real, not decorative, by
  asserting **computed** state rather than mere presence:
  `app.current_theme.name` and `app.current_theme.primary` are the palette's,
  a preview `Static`'s content carries a styled span while its plain text is
  unchanged, a `DataTable`'s `datatable--header` component style carries the
  muted colour, and the agent strip is still a `Horizontal` of `Button`s.
  Each new guard is **mutation-tested**: break it on purpose, watch it fail,
  restore it (AGENTS.md §4: "a test that cannot fail is worse than no test").
- Visual evidence: before/after screenshots of Home, Why, Diff, Agents,
  Compare, Doctor and Help at 140×42, plus Home, Why and Help at 60×24 to
  prove the narrow layout still works.
- Manual check of ease of use: every key that works today still works, the
  filter and agent cycle still respond, the tables still scroll, and the hint
  bar still names the keys.

## Review decisions

Plan critic: `river/deepseek-ai/DeepSeek-V4.1-Flash-1017`, thinking `max`, via
OMP, read-only. Verdict `changes_required`, 12 blockers. Each finding is
recorded below with its disposition. The critic's model family is disclosed:
`river/deepseek-ai/DeepSeek-V4.1-Flash-1017` differs from the coordinator's
(`minimax/MiniMax-M3.1-Flash`).

- **B1 — the closed TUI module manifest.** **Accepted.** `theme.py` is added
  to `EXPECTED_TUI_MODULES` and `REQUIRED_TUI_MODULES`, and the new test suite
  to `EXPECTED_INSTALLED_TEST_SUITES` and `INSTALLED_TUI_TEST_SUITES`. The
  plan's scope now permits exactly those two manifest files and no other line
  in them.
- **B2 — the header glyph.** **Accepted and already true in the
  implementation.** `Header.compose` always yields `HeaderIcon`, so the stock
  `⭘` is hidden with `HeaderIcon { display: none; }` and the lens mark comes
  from `format_title`; the rendered bar shows exactly one mark.
- **B3 — cursor contrast.** **Accepted.** The selected row is a dark teal
  tint (`#1f3b3d`) with light text (`#d8f3f1`), not the bright accent as a
  background. The plan now names the values.
- **B4 — the Diff title must stay inside the scroll body.** **Accepted.** The
  title stays the first `Static` inside `#diff-body`; the rule is a CSS
  border, and no new scroll structure is introduced.
- **B5 — the Help body must stay one `Static`.** **Accepted.** The plan drops
  the "two-column key table" idea: the Help body keeps its single
  `#help-content` `Static` and its `"keys — action"` format, and only the
  spans inside it change.
- **B6 — the Why agent strip.** **Accepted.** The strip stays a `Horizontal`
  of `Button`s; the tab treatment is CSS only, and no vertical rows are added.
- **B7 — `#agent-filter` and `#footer-help`.** **Accepted.** `#agent-filter`
  stays a non-focusable `Static` with its exact text, and `#footer-help` is
  kept and restyled, still naming every key it names today.
- **B8 — the "must not move" list was incomplete.** **Accepted.** The plan now
  lists every test-pinned id, states that no widget is added, removed or
  re-parented, and states that the pure builders keep returning `str` with
  their exact characters; styling happens in the screen adapters.
- **B9 — the screenshot API.** **Accepted.** The harness uses
  `App.export_screenshot()` and writes outside the checkout; the neutralized
  `save_screenshot` stays neutralized.
- **B10 — the harness must not touch the real `$HOME`.** **Accepted.** The
  harness builds a synthetic home from the project's own scenario fixtures and
  monkeypatches `paths.home`; committed evidence is scrubbed of absolute paths.
- **B11 — 80×24 is not the narrow layout.** **Accepted.** The narrow layout is
  `width < 80`; the narrow evidence is taken at 60×24, and every screen is
  checked there, not only Home and Help.
- **B12 — `Theme.variables` keys.** **Accepted.** The keys are bare names
  (`rule`, `muted`, `keycap`), resolved as `$rule`, `$muted`, `$keycap`. The
  plan's `--name` spelling was wrong and is corrected.
- **S1 — zebra striping needs `zebra_stripes = True`.** **Accepted.**
- **S2 — `STATE_STYLE` carries Rich palette names.** **Accepted.** The TUI
  maps `HeadlineState` onto its own palette; the shared table keeps the
  meaning.
- **S3 — contrast.** **Accepted.** `muted` is lightened to `#8b98a8` and used
  on the canvas; `rule` is lightened to `#31415a` so a one-cell separator is
  visible on a low-contrast terminal.
- **S4 — the new test must be able to fail.** **Accepted.** It asserts
  computed styles (theme name, theme primary, a content span, a table
  component style) and is registered in both manifests.
- **S5 — `export_screenshot` returns SVG.** **Accepted.** The plan names the
  converter (macOS `qlmanage`) and accepts SVG-only evidence.
- **S6 — keep the `narrow` and `json-mode` rules.** **Accepted.**
- **S7 — the row budget.** **Accepted.** Written into the plan as its own step
  with the three measured assertions.
- **S8 — evidence for the empty and error states.** **Accepted in part.** The
  loading, empty-catalog, filtered-empty and JSON states are captured; the
  refused/retry/fault states are covered by the existing tests rather than by
  new screenshots, because they are text states and the visual change does not
  touch their layout.
- **S9 — `Reference:` is a hard gate.** **Accepted.** The plan is frozen and
  committed before implementation, with the reference recorded in the second
  commit.
- **S10 — the Help border against the 60×24 body tests.** **Accepted.** The
  Help body is checked at 60×24 before the border is kept.
