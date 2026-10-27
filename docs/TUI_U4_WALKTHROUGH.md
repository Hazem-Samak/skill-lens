# Skill Lens 0.2 — Why Resolution Screen Walkthrough (U4)

> **Status:** Implemented by Gemini 3.8 Flash High through Antigravity under explicit owner authorization.
> Technically accepted locally after MiniMax MCode High and DeepSeek River-Pi High reviews, followed by coordinator verification of the owner-authorized final test corrections. See [acceptance](validation/u4/acceptance.md).
> Human visual approval and 0.2 publishing are not claimed.
> **Scope:** Full-Screen TUI Assignment U4 (`FULL_SCREEN_TUI.md` §§8.4, 9.1, 21.7 and 22 U4).
> **Reference Plan:** [docs/plans/2026-10-26-tui-u4-why.md](plans/2026-10-26-tui-u4-why.md)
> @ frozen commit `684cdb7aa0e3a28e5bb722bf65e4f3953edc6f76`.
> **Consolidated Adjudication Reference:** [docs/validation/u4/implementation/coordinator/combined-adjudication-r1.md](validation/u4/implementation/coordinator/combined-adjudication-r1.md).
> **Implementing base:** `main` @ `e29fca9`.

---

## 1. What changed, in plain English

U3 delivered the Home browsing screen, which presents the catalog of installed skills with inline preview and agent cycling. U4 delivers the dedicated **Why Resolution Screen** (`WhyScreen`), accessible by pressing `Enter` on a focused, nonempty Home skill row.

The Why screen provides complete insight into how an agent resolves candidate skill entrypoints for a specific skill:
1. **Header & Context:** Displays canonical installation path (relativized/tilde-formatted via `snapshot_path`), skill name, active working directory, selected agent display name, lookup skill name, collision policy (and documented policy evidence), and the report-wide headline.
2. **Agent Switching Strip:** An interactive button strip at the top allows switching between all registered agents eligible for the selected skill. DOM button order strictly preserves model scan sorted agent-ID order even when new eligible agents are introduced across refreshes. Left and Right keys navigate and wrap deterministically across agents.
3. **Candidate Collapsibles & Viewport Wrapping:** Every candidate considered during resolution is presented in a keyboard-accessible Textual `Collapsible` widget in deterministic resolution order. The candidate corresponding to the selected installation (matching the opening installation key) is initially expanded by default, while shadowed or alternate candidates remain collapsed. Candidate titles and content wrap cleanly without horizontal overflow at terminal dimensions 100x30 and 60x24. The screen body is laid out in a coherent vertical scroll container (`#why-body`), ensuring that candidate collapsibles and their details (canonical/entrypoint paths, hash, reason, rule, evidence, and notes) remain readable with candidates container height >= 4, and reachable via keyboard navigation (PageDown/PageUp/Tab/Shift+Tab/Enter). The focusable `#why-body` scroll area participates in the Tab cycle and supports PageDown/PageUp.
4. **Honest Status & Error Reporting:** Dedicated status widgets (`#why-status`, `#why-error-details`, `#why-report-status`) separate background engine lifecycle from report loading state and internal faults. If a background scan refresh finishes while the detail screen is open, the detail screen transparently re-derives its entry from the new snapshot; if the installation was removed during refresh, the detail screen closes back to Home and displays a persistent removal notice (`Installation '<name>' (<key>) was removed during refresh.`), which is cleared on explicit navigation or explicit refresh (`r`).
5. **Exact Token Lifecycle & Zero Live Reads:** Detail screens maintain explicit token identity for asynchronous report requests. An unmount or agent switch cancels only the detail's own active request, never invalidating resumed Home tokens or unrelated workers. Live filesystem reads are completely forbidden; detail rendering operates strictly on the frozen `SessionSnapshot` and immutable `ResolutionReport`.

---

## 2. Delivered files and responsibilities

| File | Change |
| --- | --- |
| `skill_lens/tui/why.py` | Implements `WhyScreen(Screen[None])`, `_WhyHost` protocol, pure helpers (`_eligible_agent_options`, `_unavailable_agent_ids`, `_entry_for_key`, `_build_candidate_blocks`), sorted agent button strip with before-mount insertion and public `Widget.move_child` reordering, coherent `#why-body` vertical scroll container with auto-height collapsible candidate container `#why-candidates`, pre-dispatch UI validation, exact token lifecycle management (`_cancel_owned_token`), title wrapping CSS, and strict literal rendering (`markup=False`). |
| `skill_lens/tui/home.py` | Integrated `HomeScreen`: bound `DataTable.RowSelected` and `action_open_why` so Enter opens `WhyScreen` only on a focused nonempty table; explicit `suspend_why` guards against hidden selection/sync/filter/drive mutations; `resume_why` and `on_screen_resume` restore Home table focus and sync upon returning; persistent `#removal-notice` displays removal feedback until explicit navigation or explicit refresh (`r`); reverted catalog-note color and narrow table height churn. |
| `skill_lens/tui/app.py` | Implemented `open_why` and `close_why` with exact token cleanup before pop and Home resumption; `action_refresh` clears removal notice on explicit refresh; active-screen status queries target `#why-status` / `#why-error-details` on `WhyScreen` vs `#status-text` / `#error-details` on `HomeScreen`; report outcome notifications route to the current browsing screen with controller-accept first. |
| `skill_lens/tui/__init__.py` | Exported `WhyScreen`. |
| `tests/test_tui_why.py` | 41 AST-discovered test functions yielding 42 collected pytest items: comprehensive event-controlled tests covering navigation, double-Enter deduplication, backspace/escape returns, agent strip switching, DOM button order preservation, defensive unknown/zero-agent explanations, token ownership isolation, agent switch races, cache hits, sticky report faults, refresh survival and removal, candidate collapsibles, literal rendering (`markup=False`), narrow 60x24 layout, target preservation sentinels, and unit branch coverage. |
| `docs/validation/u4/implementation/acceptance_mapping_r4.md` | AST-discovered acceptance criterion-to-test mapping covering all P1–P3, E1–E8, and D1–D2 requirements with exact AST selectors and discriminating assertions. |
| `docs/validation/u4/implementation/mutation_gate.py` | Reproducible mutation harness verifying that 11 planted defects across Why screen, Home screen, and App orchestration are caught by test assertions on a disposable copy outside the checkout. |
| `docs/validation/u4/implementation/mutation_gate_r5.json` | Machine-readable receipt verifying 14/14 mutants killed with exit code 1 and matching specific assertion failures. |

---

## 3. Key Invariants & Architecture

### 3.1 Enter Key Routing & Focus Invariants
- On `HomeScreen`, `Enter` on the filter `Input` submits the filter without opening the detail screen.
- `Enter` on the `DataTable` triggers `DataTable.RowSelected` only when the table is nonempty and has focus, invoking `open_why`.
- On an empty table or filtered empty state, pressing `Enter` is a safe no-op.
- Double-pressing `Enter` does not mount duplicate Why screens.
- Pressing `Escape` or `Backspace` on `WhyScreen` pops the screen and returns to Home, fully preserving Home's filter text, cursor position, selection, and table focus.

### 3.2 Suspension & Exact Token Lifecycle
```
[Home Screen (Active)]
     │
     │ user presses Enter on table
     ▼
[Home: suspend_why()] ── guards all hidden sync, drive, selection, filter
     │
     ▼
[App: push_screen(WhyScreen)]
     │
     ▼
[WhyScreen Mounted] ── pre-dispatch validation of (canonical_key, agent_id)
     │
     │ agent switch or close requested
     ▼
[Why: _cancel_owned_token()] ── exact token ownership check: active == owned
     │
     ▼
[App: pop_screen()]
     │
     ▼
[Home: resume_why() / on_screen_resume()] ── reconciles snapshot & restores focus
```
- In Textual, `App.pop_screen` pops the screen stack synchronously while screen replacement occurs: `_cancel_owned_token` runs before `pop_screen`, ensuring stale detail workers do not deliver results into a resumed Home screen.
- Only if the controller's active request matches the detail's owned token (`active == owned`) does detail cancellation invalidate the controller slot. An unowned token (such as a newly dispatched Home token) is never canceled.

### 3.3 Candidate Collapsibles & Literal Rendering
- Every candidate from `ResolutionReport.candidates` is mapped to a `Collapsible`.
- Title displays: `[▾/▸] [*|x|?] <name> (<STATE>)` using Textual's `Content.from_text(..., markup=False)` to guarantee brackets, backslashes, and style tags render literally without markup interpretation.
- Body displays: state mark and name/variant, canonical path, entrypoint path (when distinct from canonical location), content hash, reason, rule ID and evidence type, and report notes.
- The candidate matching the selected installation canonical key is initially expanded by default; all others are collapsed.
- If no candidates match, an explicit notice (`#why-no-match-notice`) informs the user.

---

## 4. Quality Gates & Verification Evidence

All four verification gates pass cleanly on the finished tree:

1. **Test Suite:**
   ```bash
   .venv/bin/pytest --cov=skill_lens
   ```
2. **Type Checking:**
   ```bash
   .venv/bin/mypy
   ```
3. **Linter & Formatter:**
   ```bash
   .venv/bin/ruff check .
   .venv/bin/ruff format --check .
   ```
4. **Mutation Harness:**
   ```bash
   .venv/bin/python docs/validation/u4/implementation/mutation_gate.py --out docs/validation/u4/implementation/mutation_gate_r5.json
   ```

Final verification correction: navigation assertions now explicitly check candidate-focused arrows, backward traversal, and focus following agent selection at both terminal sizes. The Tab search is bounded. See mutation_gate_r5.json for the expanded fourteen-case evidence; r4 remains a historical receipt.
