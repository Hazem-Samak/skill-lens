# Skill Lens U4 — Independent Critic R2 Review Plan (MiniMax M3.1 Flash / MCode, High)

## Summary

**Goal.** Complete the second independent implementation review wave for Skill Lens U4 ("Why resolution
screen") against the frozen authority `docs/plans/2026-10-26-tui-u4-why.md` @ `684cdb7aa0e3a28e5bb722bf65e4f3953edc6f76`,
plus the appended user authorization / implementer-replacement record. Produce a read-only critic verdict
(verdict + blockers + suggestions + files at risk + concessions) that the coordinator can act on.

**Scope.** Review only. No repository file is created, edited, moved, deleted or renamed. No formatter,
linter-with-fix, install, commit/checkout/stash, snapshot/golden regeneration, or test run that writes
into the checkout.

**Explicit user instruction recorded at plan review (2026-10-27):** "The task is a read-only review, not
implementation. User authorization already covers this review; implementation/editing by the reviewer remains
unauthorized." The correction wave below is therefore a hand-off specification for a separately authorised
implementer — this seat performs no implementation, and the repository is left byte-identical.

**Key design decisions for the remaining correction wave.**

1. **One blocker survives: the 60×24 narrow-viewport layout.** The frozen acceptance requires long paths/reasons
   to "wrap or scroll, with usable keyboard controls at both 100×30 and 60×24"
   (`docs/plans/2026-10-26-tui-u4-why.md:255-256`). The current implementation wraps the *title text* but gives
   the auto-height header unbounded vertical space, so at 60×24 the candidate container and the agent strip are
   laid out **below the bottom of the screen** and are never displayed. The acceptance test passes because it
   asserts model geometry (`ct.size.height >= 2`, `max_scroll_y`) rather than viewport containment.
2. **The correction is a layout fix plus a viewport-containment assertion**, not a re-scope. No new behaviour,
   scope or permission amendment is requested.
3. **Everything else from R1 is closed and independently re-verified** (P1, P2, E1–E6, E8, D1, D2, C1, C2,
   read-only/optional-import contracts, preservation of all unrelated user work).
4. **Documentation must be corrected alongside the fix** — the walkthrough and the acceptance mapping currently
   assert a viewport outcome the product does not deliver.

**Non-goals.** No live-skill demos, no network access, no delegation, no release/publish, no changes to the
frozen plan's behaviour, no new visual design system.

**User tool/test/network/delegation/write restrictions (must be preserved by whoever implements this).**

- Read-only critic task. Repository writes are forbidden for the reviewer.
- Probes may only run on a disposable external source copy with synthetic fixtures and monkeypatched
  `HOME`/XDG/protected roots; no cache/coverage output into the checkout.
- The existing mutation harness may run **only** with `--out` pointing at an external path.
- No live skill demos. Green full gates never override missing frozen acceptance.
- No delegation by this seat.
- Unrelated user work (`.path`, `docs/plans/2026-10-26-omp-native-asyncio-trial.md`,
  `docs/validation/2026-10-25/`, `docs/validation/omp-native-asyncio/`) is out of scope and must stay untouched.
- Every implementation change must be preceded by a committed plan in `docs/plans/` per `AGENTS.md` and
  `docs/process/planning-loop.md`; the frozen U4 plan is already committed, so this correction cycle needs its
  own committed plan entry.

## Current implementation and affected components

Base: `main` @ `e29fca9`, root shared checkout, U4 uncommitted (13 relevant paths; `coordinator/review-r2.diff`
is the single complete diff source). All 13 file SHA-256 values match
`coordinator/verification-r2.json`; all 2361 files in `coordinator/pre-review-r2-manifest.json` still match;
`git status --porcelain` matches the recorded manifest status byte for byte.

| Component | Role | R2 state |
| --- | --- | --- |
| `skill_lens/tui/why.py` (new, 862 lines) | `WhyScreen`, strip reconciliation, candidate collapsibles, token ownership | **Blocker 1 (layout CSS `:219-252`)**; P2 `move_child` reconciliation `:496-503` correct |
| `skill_lens/tui/home.py` | Home integration, suspension guards, removal notice | P1 closed; D2 cleanup landed |
| `skill_lens/tui/app.py` | `open_why`/`close_why`, active-screen status routing | P1 closed; private-attribute access (suggestion) |
| `tests/test_tui_why.py` (new, 2890 lines, 41 AST test functions → 42 pytest items) | U4 acceptance evidence | **Blocker 1 (false-positive viewport assertion at `:2300-2403`)** |
| `docs/TUI_U4_WALKTHROUGH.md` | Factual walkthrough | **Blocker 1 claim at `:21`; minor drift at `:31`, `:35`, `:75`** |
| `docs/validation/u4/implementation/acceptance_mapping_r3.md` | Criterion→test mapping | **Blocker 1 overstatement at `:16`, `:23`, `:59`** |
| `docs/validation/u4/implementation/mutation_gate.py` | 11-mutant harness | Correct; docstring says "Ten gates" (suggestion) |

## Reproduced evidence (independent, read-only)

Gates re-run by this reviewer against the disposable external copy `/tmp/u4r2/src`:

- `pytest --cov=skill_lens` → **1127 passed, 1 skipped** (expected case-insensitive-FS skip), **90.78 %** total,
  `why.py` **91 %**, 112.19 s. Matches `coordinator/review-r2-pytest.log`.
- `mypy` → clean, 39 source files. `ruff check .` → "All checks passed!". `ruff format --check .` → all formatted.
- Mutation harness re-run with `--out /tmp/u4r2/mutation_r2_independent.json` → **11/11 mutants killed**
  (`mutant_rc=1`), 8/8 controls `rc=0`, every restore `rc=0`, `restored_identical: true`; repo SHA-256 of
  `why.py`/`app.py`/`home.py` unchanged after the run.
- Optional-import contract: with `textual` blocked by a meta-path finder, `import skill_lens.cli` succeeds and
  `import skill_lens.tui` raises `ImportError`.
- P1 probe: removal notice contains both the captured display name (`'skill-a'`) and the captured key; survives
  `resume_why()` + `app._update_ui()`; cleared by an explicit `r` (widget emptied).
- P2 probe: after an eligibility refresh that both **adds** and **removes** an agent, DOM order equals model
  order; when the focused agent is removed, focus and selection move to the selected eligible agent; Left/Right
  follow the visible strip and wrap.
- Enter handling: pressing Enter on Home pushes exactly one `WhyScreen` (stack depth 2, no double-push).

### Blocker 1 — 60×24 narrow viewport: agent strip and candidates are laid out off-screen

Root cause: `skill_lens/tui/why.py:223-227` gives `#why-title` `height: auto` with no maximum height and no
scroll container, while `#why-candidates` is `height: 1fr` (`:241-243`). In a `layout: vertical` screen, the
auto-height header absorbs all surplus height, so the candidates row is pushed past the bottom edge and clipped;
the screen itself has no scroll container.

Reproduced geometry (Pilot, `size=(60, 24)`, synthetic fixture in a temp `HOME`):

| Fixture | `#why-title` height | strip region | candidates region | candidates inside viewport? |
| --- | --- | --- | --- | --- |
| short (10-char name) | 7 | y=8 | y=17, h=6 | yes |
| 1 nested dir + 40-char name | 16 | y=17 | y=24, h=1 | **no** |
| 2 nested dirs + 50-char name | 18 | y=19 | y=27, h=1 | **no** |
| repo acceptance-test fixture (3 nested dirs + 87-char name) | 22 | y=23 | y=31, h=1 | **no** |

Visible compositor rows at 60×24 with the repository's own acceptance fixture contain only the header
(rows 1–22) and the footer (row 23). The agent strip button row (`OpenCode V2`) and the entire candidate block
(collapsible title, `Canonical:`, `Rule:`, `Evidence:`, `Reason:`, hash) are absent from the screen. At 100×30
the same fixture renders the strip at y=13, the candidate title at y=21 and the body from y=24, scrollable —
so the defect is narrow-viewport-specific, not content-specific.

Expected (frozen `docs/plans/2026-10-26-tui-u4-why.md:255-256`; adjudication P3; E7 "real long viewport
geometry/focus destination/toggle/scroll checks"): long paths/reasons must wrap or scroll, with usable keyboard
controls, at **both** 100×30 and 60×24.

## Proposed architecture and end-to-end flow for the correction

Minimal, in-scope change confined to the Why screen's layout and its acceptance evidence.

1. **Bound the header.** In `WhyScreen.DEFAULT_CSS`, stop the title block from consuming the viewport:
   - keep `#why-title` literal and `text-style: bold`;
   - give the title region a bounded height that still wraps (`height: auto` with `max-height`, or place the
     title inside a scrollable/`auto`-height region with a viewport-relative cap) so a long installation path
     wraps within the header instead of expanding without bound;
   - ensure the agent strip (`#why-agent-strip`) and `#why-candidates` remain inside the screen at 60×24;
   - keep `#why-candidates { height: 1fr }` as the flexible row so it always receives the remaining height.
   - Preferred shape: make the *whole* screen body (title + strip + candidates) a single `VerticalScroll`
     region, or cap the header so `#why-candidates` always gets ≥ 1 row inside the viewport. Either satisfies
     "wrap or scroll" while keeping the existing focused-widget and focus-preservation behaviour
     (`tests/test_tui_why.py:161-193`).
2. **Do not disturb ownership, cancellation or literal-rendering contracts.** The change must not touch
   `_cancel_owned_token`, `identity_matches`, `markup=False` boundaries, the `move_child` strip reconciliation,
   or the Home suspension guards.
3. **Preserve the frozen presentation.** No new visual design system; the fix is layout only.

## State, ownership, concurrency, failure and recovery semantics (must be unchanged)

- Detail request ownership stays exact: only a request whose token equals the controller's active `why` token
  may be invalidated (`why.py` `_cancel_owned_token`); unowned tokens are never cancelled.
- Home remains suspended while the detail screen is active; `suspend_why`/`resume_why`/`on_screen_resume` and the
  `_suspended` guards in `_drive`, `_apply_filters`, `_ensure_selection`, `note_report_outcome`, selection and
  input handlers stay in place.
- Stale Home/detail outcomes (success **and** error) are rejected by the controller and must not mark
  `controller.failed`, cancel a newer token, or dispatch hidden Home work.
- Pre-dispatch validation for unknown agents and a missing opening key keeps making zero invalid calls,
  leaves `controller.failed` false and exits 0.
- The removal notice is captured (display name + key) and survives automatic resume; it clears only on an
  explicit Home navigation/filter/refresh action.
- Live filesystem reads stay forbidden: the detail screen renders only from the frozen `SessionSnapshot` and the
  immutable `ResolutionReport`.
- Exit codes: normal quit 0; accepted unexpected fault 3.

## Tests and acceptance criteria

**New/updated test (tests/test_tui_why.py, `test_terminal_dimensions_100x30_and_60x24_controls_and_wrapping`):**

1. Build the long-path fixture at **both** 100×30 and 60×24.
2. Assert the agent strip is inside the viewport: `strip.region.y + strip.region.height <= screen.size.height`.
3. Assert the candidates container is inside the viewport:
   `scroll.region.y + scroll.region.height <= screen.size.height` and `scroll.region.height >= 1`.
4. Assert the candidate content is actually rendered on screen, not merely present in the DOM — e.g. the
   candidate title and `Canonical:`/`Rule:`/`Reason:` appear in the composited visible rows
   (`screen._compositor.render_strips()`), or the candidates region is scrolled into view via a user-reachable
   path.
5. Keep the existing assertions: no horizontal overflow (`scroll.max_scroll_x == 0`), title wraps
   (`ct.size.height >= 2`), Tab reaches the `CollapsibleTitle` specifically, Enter toggles it, and vertical
   scrolling reaches `max_scroll_y`.
6. Retain the "no live read" property: the new geometry assertions must not read the target tree.

**Documentation corrections (must land with the fix):**

- `docs/TUI_U4_WALKTHROUGH.md:21` — restate the wrapping/scrolling claim only for what the fixed build actually
  delivers at both viewports.
- `docs/validation/u4/implementation/acceptance_mapping_r3.md:16`, `:23`, `:59` — replace "viewport wrapping …
  without horizontal scroll" / "vertical scroll reaches max_scroll_y" with the viewport-containment criterion
  that is actually asserted.
- `docs/TUI_U4_WALKTHROUGH.md:35` — state the AST-discovered function count (41) and the pytest item count (42)
  explicitly, so the D1 invented-count defect cannot reappear.
- `docs/validation/u4/implementation/mutation_gate.py:7` — the module docstring says "Ten gates" while the
  harness runs 11 mutants.

**Full verification gate (unchanged by this review):**

```
pytest --cov=skill_lens
mypy
ruff check .
ruff format --check .
```

plus the mutation harness with `--out` on an external path, and a re-run of the manifest/fingerprint check to
prove the checkout was not mutated by the review.

**Acceptance criteria for the correction wave:** the layout blocker is fixed at both viewport sizes; the
viewport-containment assertions exist and are meaningful (they must fail against the current build); all four
whole-repo gates pass; documentation matches observed behaviour; the pre-review manifest is refreshed and the
historical receipts are preserved with explicit errata.

## Optional, non-blocking suggestions (implementer discretion)

- `skill_lens/tui/app.py:206` and `:448` use the private `HomeScreen._clear_removal_notice()` / `._removal_notice`
  although the public `HomeScreen.clear_removal_notice()` exists (`home.py:479-481`); add a public accessor and
  use it from the app.
- `skill_lens/tui/home.py:1092-1100` `HomeScreen.action_refresh` is unreachable (Home has no `"r"` binding; the
  app binding wins) — remove or route through it consistently.
- `skill_lens/tui/why.py:497` the `hasattr(strip, "move_child")` guard is unnecessary: `Widget.move_child` is
  public Textual 8.2.8 API (verified), so the guard can mask a future breakage.
- `docs/TUI_U4_WALKTHROUGH.md:31` — mention the public `move_child` reordering alongside the before-mount
  insertion.
- `docs/TUI_U4_WALKTHROUGH.md:75` — "screen pop is asynchronous" is imprecise: `App.pop_screen` pops the stack
  synchronously and only the screen replacement is deferred.
- Report notes render in the header **and** in every candidate body (duplicate display).

## Unresolved decisions and risks

- **Header treatment is an implementer choice** (bounded `max-height` vs. a screen-level scroll region). Both are
  acceptable; the acceptance criteria above are what matter. The coordinator should confirm the chosen shape
  against the frozen "no new visual design system" rule.
- **Blast radius of the layout change.** Moving `#why-title` into a scroll container could affect the existing
  focus-preservation and expansion-preservation assertions (`tests/test_tui_why.py:161-193`) and the
  candidate-focus assertions. The implementer must re-verify C1 and the P2 focus target after the change.
- **No upstream serving attestation.** The named roster families (Codex gpt-6.1-sol, Gemini 3.8 Flash,
  DeepSeek V4.1 Flash 1017) differ from the session's model token; identity is not attested upstream. Tool
  results (mypy/ruff/pytest/mutation harness) are tool-verified, not model-attested.
- **Count drift in receipts is not a defect.** `ruff format --check` counts differ by one file between runs
  (371 vs 372) and per-run timing/coverage differ by design; each receipt labels its own execution and must not
  be compared across runs for equality.
