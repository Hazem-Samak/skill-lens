# TUI visual polish — evidence

**Mission:** make the Skill Lens full-screen browser beautiful, without changing
anything about how it works.

**Plan:** [`docs/plans/2026-11-08-tui-visual-polish.md`](../../plans/2026-11-08-tui-visual-polish.md)
(frozen at `c085e2284b3b4aab34690c27c8b0c336b0ea6bec`).

**Scope:** presentation only — `skill_lens/tui/**` plus the two closed
packaging manifests. No change to `core/`, `models/`, `registry/`,
`presentation/`, `render.py` or `cli.py`; no change to any key binding, screen,
report field, JSON shape or exit code.

## What changed

Two rounds of visual work are shown here.  The "before" pictures are the
original interface; the "after" pictures are the current tree, which carries
both rounds.

| Area | Before | After |
|---|---|---|
| Theme | the stock Textual dark theme: saturated blue primary, heavy blue scrollbars, one background for everything | one registered `skill-lens` theme: a deep canvas, two surfaces, a lens teal accent and a semantic palette (green / amber / red / violet) |
| Top bar | `⭘  Skill Lens — 0.2.0` in the default style | `◉ Skill Lens 0.2.0` — one mark, the name, a dim version |
| Screen titles | the same bold monospace as everything else | a centred, dim, upper-case eyebrow under the brand bar |
| Tables | plain headers, no zebra, cells clipped mid-word (`Antig`, `empirica`) | muted header band, zebra rows, an accent-tinted selected row, padded cells, explicit column widths so names are never clipped, coloured parse marks and severity values |
| Detail panes | a wall of identical bold `Label: value` lines | dim labels, bright values, muted paths and hashes, a set-apart description |
| Separators | a solid accent rule between panes | a hairline, and one-column scrollbars in a muted colour |
| Status and hints | `Ready: 9 skills discovered` floating above the key line | a status band, and one key bar: keycaps grouped by purpose and separated by a rule.  The six full screens draw their bar from the screen's own bindings plus the app's, so the bar cannot hide a key the screen answers to; Home keeps its hand-written grouped map, and a test pins that map to the bindings.  The bar wraps instead of clipping on a narrow terminal |
| Help | a plain box of monospace | a rounded modal, accented section headings, bright keys, a real Close button |
| Title bar | `⭘ Skill Lens — 0.2.0`, left aligned, three stacked identity lines | one centred brand lockup over a hairline rule, with a centred page eyebrow under it.  A terminal cannot enlarge its type, so the lockup is set in spaced capitals instead |
| Long names | one 54-character skill name stretched the Name column and pushed the other columns away | names longer than 40 cells are shortened with an ellipsis in the table; the full name is in the preview and the filter still matches it |
| Row spacing | one line per skill | the skill list on Home gives each skill a blank line on a wide terminal, and keeps the rows one cell high on a narrow one so the list stays useful |

## Before and after

Home, 140×42 — the list, the preview card, the agent chip, the hint bar:

| Before | After |
|---|---|
| ![Home before](home-140x42-before.png) | ![Home after](home-140x42-after.png) |

Skill detail (Why), 140×42 — the report facts, the agent tab, the candidates:

| Before | After |
|---|---|
| ![Why before](why-140x42-before.png) | ![Why after](why-140x42-after.png) |

Home at 60×24 — the narrow layout still stacks the panes and still works:

| Before | After |
|---|---|
| ![Home 60x24 before](home-60x24-before.png) | ![Home 60x24 after](home-60x24-after.png) |

The other screens after the change, at 140×42:

| Screen | |
|---|---|
| Diff | ![Diff](diff-140x42-after.png) |
| Agents | ![Agents](agents-140x42-after.png) |
| Compare | ![Compare](compare-140x42-after.png) |
| Doctor | ![Doctor](doctor-140x42-after.png) |
| Help | ![Help](help-140x42-after.png) |

The narrow layout (60×24) of the detail and the help overlay:

| Screen | |
|---|---|
| Why at 60×24 | ![Why 60x24](why-60x24-after.png) |
| Help at 60×24 | ![Help 60x24](help-60x24-after.png) |

## How the pictures were made

Both pictures of a pair come from the same harness, run against the same
synthetic scenario; only the code differs.

1. The "before" tree is `git archive HEAD` of the commit before the change
   (`01fcf01`), unpacked outside the checkout.
2. The harness builds a synthetic home from the project's own fixtures
   (`tests/fixtures/scenarios.py`), monkeypatches `paths.home`, and runs the app
   headless with Textual's `Pilot`, opening each screen with deterministic key
   presses. The real `~/.claude`, `~/.agents` and `~/.codex` are never read.
3. `App.export_screenshot()` writes the SVG (the app deliberately neutralizes
   `save_screenshot` for the read-only guarantee), and macOS `qlmanage`
   rasterises it to PNG.
4. The paths shown in the pictures are the synthetic fixture home
   (`/tmp/skill-lens-demo/home`), not anyone's real machine.

The harness lives outside the repository on purpose: it is a review tool, not a
shipped artifact.

## What did not move

- Every key does what it did before.  The Home bar names the keys the skill
  list answers to -- detail, diff, agents, compare, doctor, filter, agent,
  JSON, focus, quit and refresh; the cursor keys and the escape keys are left
  to the screen itself, as they were before.  The bar wraps between hints on a
  narrow terminal and never splits a key from its action.
- Every report says the same words in the same order: the styling is applied
  with markup-free `Content` spans, so the plain text of every widget is
  byte-for-byte what it was. `tests/test_tui_visual.py` proves this for the
  preview, the Help body and the report blocks.
- The read-only guarantee is untouched: no new write, no subprocess, no
  network, no log file.
- The CLI, its JSON and its exit codes are untouched.

## Pre-push correction (2026-11-09)

A pre-push review found that the key bar was built from Textual's live binding
chain.  A focused table shadows a screen key, and a modal cuts the chain before
the app's keys, so the Doctor's `enter` and the Help overlay's `f1` were
missing.  The inner bar was also pinned to one row, so a narrow terminal
clipped the second line instead of wrapping.

The bar is now built from the screen's own declarations plus the app's, with
the screen winning a shared key, and its height is automatic.  Three new guards
pin the result, and each was mutation-tested (a dropped `enter`, a dropped
`f1`, and a restored one-row bar were all caught).  The mutation report now
lists 23 mutations.

The Doctor (140×42) and Help (140×42 and 60×24) screenshots were captured
before this correction, so their key bars do not show the restored `enter` and
`f1`.  The harness lived outside the repository and is no longer available, so
they were not recaptured; the corrected bars are pinned by
`tests/test_tui_visual.py` instead.  No other image is affected.

## Verification

- `pytest --cov=skill_lens` — the whole suite, coverage gate honoured. The raw
  logs are in [`gates/`](gates/).
- `mypy` — no issues.
- `ruff check .` and `ruff format --check .` — clean.
- `tests/test_tui_visual.py` — new, and mutation-tested: twenty-three deliberate
  mutations were applied to the code it guards, and every one was caught. The
  report is in
  [`mutations/mutation-report.txt`](mutations/mutation-report.txt).
