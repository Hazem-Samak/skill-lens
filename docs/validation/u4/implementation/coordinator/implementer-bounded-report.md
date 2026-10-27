### Council Report

#### EFFECTIVE_MODEL
- **Configured / Provider**: Antigravity / `gemini-3.8-flash-high`
- **Execution Mode**: Direct sole implementer (authorized bounded U4 continuation; no delegation, no commits, no push)
- **Runtime Mode / Interaction Mode**: T3 Code Default interaction mode

---

#### OUTCOME
**SUCCESS**. All three bounded deliverables authorized by the owner in [bounded-continuation-authorization.md](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/coordinator/bounded-continuation-authorization.md) were implemented and verified with zero regressions.

---

#### FILES_CHANGED
- [skill_lens/tui/why.py](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/skill_lens/tui/why.py): Wrapped screen contents in `VerticalScroll(id="why-body")` with `#why-body { height: 1fr; }` and `#why-candidates { height: auto; }`. Preserved existing IDs, literal rendering (`markup=False`), C1 focus/expansion semantics, P2 DOM order, and Textual containers.
- [tests/test_tui_why.py](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/tests/test_tui_why.py): Expanded discriminating assertions across Deliverables 1, 2, and 3 without introducing sleep-only waits or private product-code compositors.
- [docs/validation/u4/implementation/mutation_gate.py](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/mutation_gate.py): Administrative docstring correction from "Ten gates" to "Eleven gates" documenting mutant 11 (`stale error marking controller failed`).
- [docs/TUI_U4_WALKTHROUGH.md](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/TUI_U4_WALKTHROUGH.md): Updated layout section describing `#why-body`, test counts (41 AST functions / 42 pytest cases), and synchronous pop behavior.
- [docs/validation/u4/implementation/acceptance_mapping_r4.md](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/acceptance_mapping_r4.md): Created R4 acceptance mapping mapping each frozen plan requirement to AST test selectors, exact assertions, and receipts.
- [docs/validation/u4/implementation/mutation_gate_r4.json](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/mutation_gate_r4.json): Generated fresh R4 mutation gate receipt verifying 11/11 mutants killed and 8/8 controls passed.

---

#### CHECKS
- **pytest (full repository with coverage)**:
  `.venv/bin/pytest --cov=skill_lens`
  - Output: `1127 passed, 1 skipped in 115.90s`
  - Total coverage: `90.83%` (Why module coverage: `91%`, required >= 90.0%)
- **pytest (targeted Why test suite)**:
  `.venv/bin/pytest tests/test_tui_why.py`
  - Output: `42 passed in 26.62s`
- **mypy**:
  `.venv/bin/mypy`
  - Output: `Success: no issues found in 39 source files`
- **ruff check**:
  `.venv/bin/ruff check .`
  - Output: `All checks passed!`
- **ruff format**:
  `.venv/bin/ruff format --check .`
  - Output: `377 files already formatted`
- **mutation gate (fresh R4 receipt)**:
  `.venv/bin/python docs/validation/u4/implementation/mutation_gate.py --out docs/validation/u4/implementation/mutation_gate_r4.json`
  - Output: `11/11 mutants killed (100.0%), 8/8 controls passed, 11/11 restores passed (restored_identical: true)`

---

#### TESTS_ADDED
No new loose test functions were added; existing in-scope test functions in [tests/test_tui_why.py](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/tests/test_tui_why.py) were enhanced with discriminating assertions matching the 41 AST test definitions:
- `test_redraw_preserves_candidate_focus_and_expansion`
- `test_agent_button_renders_captured_label_literally`
- `test_notice_cleared_on_explicit_refresh`
- `test_agent_dom_order_after_eligibility_refresh`
- `test_enter_on_focused_nonempty_table_opens_why_screen`
- `test_enter_on_empty_table_or_filtered_empty_list_is_noop`
- `test_enter_on_filter_input_submits_filter_does_not_open_why`
- `test_backspace_returns_to_home_preserving_filter_and_selection` *(enhanced for Deliverable 3: nonzero cursor row, filter, and focus preservation)*
- `test_priority_ctrl_c_and_q_quit_from_why`
- `test_agent_strip_options_and_deterministic_switching`
- `test_zero_agent_skill_shows_explanation_and_zero_requests` *(parameterized: 2 pytest cases)*
- `test_defensive_unknown_agent_in_constructed_snapshot`
- `test_missing_key_predispatch_zero_calls`
- `test_real_worker_race_blocked_home_to_detail_agent_change_and_stale_callbacks`
- `test_home_suspended_drive_and_outcome_guards_prevent_hidden_dispatch`
- `test_cancellation_guards_kill_mutants`
- `test_real_worker_detail_a_to_b_while_b_running`
- `test_detail_agent_switch_a_to_b_while_a_completes`
- `test_pending_blocked_capture_plus_detail_report` *(enhanced for Deliverable 2: 3 distinct skills, Home worker blocked before Enter, nonempty pending queue, exact pre-r token snapshot, zero hidden Home calls during refresh, release detail only, release capture, clean quit)*
- `test_non_capture_accepted_event_synchronization_does_not_cancel_or_dispatch_home`
- `test_real_pop_delayed_detail_callback_protects_resumed_home`
- `test_u3_identity_matching_rejection_branch`
- `test_refresh_on_detail_surviving_installation`
- `test_refresh_on_detail_removed_installation_returns_to_home_with_notice`
- `test_refresh_on_detail_changed_agent_eligibility`
- `test_refresh_on_detail_no_agent_replacement`
- `test_refresh_on_detail_empty_replacement_catalog`
- `test_refresh_on_detail_retained_home_filter_excludes_controller_fallback`
- `test_refresh_actual_refusal_retry_and_fault_paths`
- `test_all_filter_return_matrix_active_home_status`
- `test_broad_read_sentinels_and_target_preservation_manifest`
- `test_identity_cases_frontmatter_directory_unresolved_entrypoints_and_order` *(enhanced for Deliverable 3: exact snapshot_path equality on header and candidates)*
- `test_mixed_unknown_and_known_agent_ids_explained`
- `test_terminal_dimensions_100x30_and_60x24_controls_and_wrapping` *(enhanced for Deliverable 1: 60x24 and 100x30 dimensions, multi-agent strip left/right, candidate Tab, size.height >= 4, PageDown scrolling, and composited text visibility)*
- `test_cache_hit_and_redraw_deduplication`
- `test_accepted_report_fault_does_not_retry_loop`
- `test_candidate_collapsibles_expanded_and_collapsed` *(enhanced for Deliverable 3: STATE_STYLE span assertions for ACTIVE and SHADOWED states; unstyled literal name tags)*
- `test_candidate_no_matches_shows_notice`
- `test_literal_rendering_markup_false`
- `test_why_helpers_coverage` *(enhanced for Deliverable 3: same-location entrypoint suppression with differing strings vs different locations)*
- `test_why_screen_unit_branches`

---

#### DEVIATIONS_FROM_PLAN
None. All edits strictly respected the allowed file scope and the frozen reference plan (`684cdb7aa0e3a28e5bb722bf65e4f3953edc6f76`). Unrelated files, prior historical receipts (R1/R2/R3), and coordinator files were preserved unchanged.

---

#### BLOCKED_ON
None.

---

### Concrete 3-Item Assertion & Evidence Map

1. **Deliverable 1: Why Narrow Layout Usability (60x24 & 100x30)**
   - *Problem*: Previously, with `Screen` holding header elements and `#why-candidates` having `height: 1fr`, a long header consumed ~22 rows, compressing candidates into a 1-row viewport (`size.height == 1`) where Textual's scroll viewport was trapped.
   - *Resolution in Code*: In [skill_lens/tui/why.py](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/skill_lens/tui/why.py), screen children are enclosed within `VerticalScroll(id="why-body")` with CSS `#why-body { height: 1fr; }` and `#why-candidates { height: auto; }`. The candidate container expands to accommodate its contents naturally while `#why-body` handles unified vertical scrolling.
   - *Verification in Test*: `test_terminal_dimensions_100x30_and_60x24_controls_and_wrapping` tests both 100x30 and 60x24 using a long header/path fixture and 2 agent options. It exercises `focus_previous` / `focus_next` across the agent strip, tabs to candidates, asserts `candidate_list.size.height >= 4` and title wrapping (`size.height >= 2` at 60x24), scrolls via `page_down`, and inspects composited visible lines across the screen (`Canonical:`, `Hash:`, `Reason:`, `Rule:`, `Evidence:`, `Ready:` / `Report:`).

2. **Deliverable 2: Genuinely Pending Home Queue During Refresh**
   - *Problem*: DeepSeek R2 blocker noted that previous refresh test fixtures had empty pending queues (`groups{'deploy': 'done'}, pending[]`), rendering comparisons vacuous.
   - *Resolution in Test*: `test_pending_blocked_capture_plus_detail_report` constructs 3 distinct skill lookup groups (`deploy`, `test`, `build`) and blocks the Home worker (`home_blocked.wait()`) *before* pressing Enter. When Why opens, Home's suspension cancels its owned token and places its group back into pending, leaving `>= 3` genuinely pending groups.
   - *Verification*:
     - Asserts `len(home_view.pending_lookup_keys) >= 3` and `home_screen.controller.pending_queue` is non-empty before `r`.
     - Logs adapter `request_report` calls by `(context, screen, key, token)`.
     - Snapshots token, Home cell texts, group statuses, and queue length.
     - Presses `r` to start refresh capture (holding capture blocked).
     - Asserts zero extra adapter calls to Home, zero Home cell changes, zero Home queue alterations, and unchanged detail token.
     - Releases detail report only; waits asynchronously via `_wait_until` predicate for detail report to render composited text while capture remains pending.
     - Asserts hidden Home still has received zero calls and undergone zero state mutations.
     - Releases capture gate; verifies clean pop back to Home and quits.

3. **Deliverable 3: Truthful Acceptance Mapping & Discriminating Assertions**
   - *Entrypoint Suppression*: In `test_why_helpers_coverage`, verified that `same_locations` suppresses redundant `Entrypoint:` lines when canonical and entrypoint paths resolve to the same location even if expressed as different strings (e.g. `(("/canon/path", "/entry/path"),)`), while differing paths display `Entrypoint: /entry/path`.
   - *Shared STATE_STYLE Spans*: In `test_candidate_collapsibles_expanded_and_collapsed`, asserted that candidate collapsible headers apply `STATE_STYLE[ACTIVE]` (`"bold green"`) to `[active]` and `STATE_STYLE[SHADOWED]` (`"bold yellow"`) to `[shadowed]`, while the literal skill name tag (`deploy`) remains unstyled.
   - *Exact snapshot_path formatting*: In `test_identity_cases_frontmatter_directory_unresolved_entrypoints_and_order`, asserted that header installation and candidate canonical/entrypoint labels equal exact `snapshot_path(current_dir, path)` rather than substring checks.
   - *Nonzero Home Cursor Row & Filter*: In `test_backspace_returns_to_home_preserving_filter_and_selection`, set filter to `deploy` (matching 2 items), moved table cursor to row 1 (`table.cursor_row == 1`), opened Why, pressed Backspace, and asserted that `table.cursor_row == 1`, `filter_input.value == "deploy"`, `controller.selected_key` matches row 1, and `table.has_focus` is True.
   - *Receipts & Docstring*: Created [acceptance_mapping_r4.md](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/acceptance_mapping_r4.md) with exact AST selectors and assertion references. Corrected `mutation_gate.py` docstring from "Ten gates" to "Eleven gates". Generated [mutation_gate_r4.json](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/mutation_gate_r4.json) with 11/11 mutants killed and all controls/restores passing.

---

#### Residual Concerns
None. The implementation satisfies the bounded continuation authorization criteria, maintains full test suite passing status with 90.83% coverage, zero type/lint errors, and is ready for coordinator direct verification and targeted re-check.
