> Superseded by [acceptance_mapping_r4.md](acceptance_mapping_r4.md); this historical record retains its documented coverage gaps.

# U4 Acceptance Criterion-to-Test Mapping (Revision 3)

**Author:** Sole implementer Antigravity (Gemini 3.8 Flash High) under owner authorization.  
**Operative Reference Plan:** `docs/plans/2026-10-26-tui-u4-why.md` @ `684cdb7aa0e3a28e5bb722bf65e4f3953edc6f76`.  
**Consolidated Adjudication Reference:** `docs/validation/u4/implementation/coordinator/combined-adjudication-r1.md`.  
**Scope:** Complete verification of all adjudicated items P1–P3, E1–E8, D1–D2, and frozen acceptance criteria. Every test name below was discovered and verified directly via AST.

---

## 1. Adjudicated Findings Resolution (P1–P3, E1–E8, D1–D2)

| Item | Finding / Requirement Summary | Resolution Location | Exact AST-Verified Test Selector |
| :--- | :--- | :--- | :--- |
| **P1** | Removal notice not cleared on Home explicit refresh `r` | `skill_lens/tui/home.py`: added `action_refresh` and public `clear_removal_notice`; updated `on_key` to include `"r"`; `app.py`: `action_refresh` calls `home._clear_removal_notice()` | `tests/test_tui_why.py::test_notice_cleared_on_explicit_refresh` |
| **P2** | Adding earlier eligible agents appends DOM strip out of model scan order; Left/Right wrap broken | `skill_lens/tui/why.py`: `_refresh_strip` uses `strip.mount(btn, before=f"#{next_id}")` and public `Widget.move_child`; reconciles focus; deterministic Left/Right wrapping | `tests/test_tui_why.py::test_agent_dom_order_after_eligibility_refresh` |
| **P3** | Horizontal overflow on long title/path/reason/note at 100x30 and 60x24 | `skill_lens/tui/why.py`: `WhyScreen CollapsibleTitle { max-width: 100%; width: 100%; height: auto; }`; `VerticalScroll(id="why-candidates", can_focus=False)` for clean focus | `tests/test_tui_why.py::test_terminal_dimensions_100x30_and_60x24_controls_and_wrapping` |
| **E1** | Ownership and cancellation proof with real workers, events, tokens, Home cells, and callbacks | `skill_lens/tui/why.py`, `home.py`, `app.py`: cancellation events checked, unowned tokens preserved, Home suspended guards, stale callbacks suppressed | `tests/test_tui_why.py`:<br>• `test_real_worker_race_blocked_home_to_detail_agent_change_and_stale_callbacks[success]`<br>• `test_real_worker_race_blocked_home_to_detail_agent_change_and_stale_callbacks[error]`<br>• `test_home_suspended_drive_and_outcome_guards_prevent_hidden_dispatch`<br>• `test_cancellation_guards_kill_mutants`<br>• `test_real_worker_detail_a_to_b_while_b_running`<br>• `test_detail_agent_switch_a_to_b_while_a_completes`<br>• `test_pending_blocked_capture_plus_detail_report`<br>• `test_real_pop_delayed_detail_callback_protects_resumed_home` |
| **E2** | Accepted non-capture report event synchronization with active request registered | `skill_lens/tui/why.py`, `app.py`: actual active `diff` request registered in controller; outcome posted, accepted into cache; active detail token and suspended Home cells remain unchanged | `tests/test_tui_why.py::test_non_capture_accepted_event_synchronization_does_not_cancel_or_dispatch_home` |
| **E3** | Frozen-data target alteration before visit; broad read sentinels across all app actions | `skill_lens/tui/why.py`: immutable snapshot models; target deletion, modification, symlink retarget asserted before first visit; broad read sentinels (Path/os open, read_text, stat, lstat, readlink, builtins.open) active across detail, switch, toggle, back, refresh, quit | `tests/test_tui_why.py::test_broad_read_sentinels_and_target_preservation_manifest` |
| **E4** | Real agent-identity fixtures through capture and `snapshot_why` oracle parity | `skill_lens/tui/why.py`: differing directory vs frontmatter name, multi-entrypoint symlinks, shadowed project state tested against `snapshot_why` oracle; visible title and candidate blocks verified | `tests/test_tui_why.py::test_identity_cases_frontmatter_directory_unresolved_entrypoints_and_order` |
| **E5** | All-filter return matrix across real pending, refusal, retry, fault, count change, and removal | `skill_lens/tui/why.py`, `home.py`, `app.py`: real `SnapshotTooLarge`, `SnapshotChanged`, and `RuntimeError` exceptions; status and error details preserved on Home return; quit exit codes 0 and 3 verified | `tests/test_tui_why.py::test_all_filter_return_matrix_active_home_status` |
| **E6** | Constructed-snapshot all-unknown agent IDs and missing opening key predispatch validation | `skill_lens/tui/why.py`: sorted unavailable agent IDs listed in status; zero requests dispatched; `controller.failed` is False; exit code 0; missing opening key closes Why with zero dispatch | `tests/test_tui_why.py`:<br>• `test_defensive_unknown_agent_in_constructed_snapshot`<br>• `test_missing_key_predispatch_zero_calls` |
| **E7** | Viewport wrapping, scroll geometry and keyboard reachability | `skill_lens/tui/why.py`: `VerticalScroll(id="why-candidates", can_focus=False)`; `CollapsibleTitle` wraps (height >= 2 at 60x24); Tab moves directly to candidates; vertical scroll reaches max_scroll_y | `tests/test_tui_why.py::test_terminal_dimensions_100x30_and_60x24_controls_and_wrapping` |
| **E8** | Eleven disposable mutation gates covering original + reviewer ownership mutations | `docs/validation/u4/implementation/mutation_gate.py`: runs on isolated disposable copy; 11/11 mutants killed with intended assertion failures; before/after SHA256 hashes strictly verified | `docs/validation/u4/implementation/mutation_gate_r3.json` |
| **D1** | AST-discovered test names, removal of invented 85% floor and sys.monitoring claims | Created `acceptance_mapping_r3.md` using exact AST-parsed test functions; historical receipts preserved | `docs/validation/u4/implementation/acceptance_mapping_r3.md` |
| **D2** | Factual walkthrough update, removal of fragile counts, preserved historical receipts | Updated `docs/TUI_U4_WALKTHROUGH.md` with factual behavior and exact references; reverted unrelated catalog-note color churn and table height churn | `docs/TUI_U4_WALKTHROUGH.md` |

---

## 2. Frozen Acceptance Criteria to AST-Verified Test Function Mapping

| Frozen Acceptance Section | Requirement Summary | AST-Discovered Test Function in `tests/test_tui_why.py` |
| :--- | :--- | :--- |
| **§1. Enter Navigation & Focus** | Enter on focused nonempty table opens WhyScreen | `test_enter_on_focused_nonempty_table_opens_why_screen` |
| | Enter on empty table or filter empty state is no-op | `test_enter_on_empty_table_or_filtered_empty_list_is_noop` |
| | Enter on filter input submits filter, does not open Why | `test_enter_on_filter_input_submits_filter_does_not_open_why` |
| | Repeated Enter deduplication (at most 1 detail screen) | `test_enter_on_focused_nonempty_table_opens_why_screen` |
| | Backspace and Escape pop back to Home | `test_backspace_returns_to_home_preserving_filter_and_selection` |
| | Preserves Home filter text, cursor, selection, and focus | `test_backspace_returns_to_home_preserving_filter_and_selection` |
| | Priority Ctrl-C and q cleanly quit with controller exit code | `test_priority_ctrl_c_and_q_quit_from_why` |
| **§2. Header & Identity Display** | Installation canonical display, agent label, lookup name, policy evidence, headline | `test_identity_cases_frontmatter_directory_unresolved_entrypoints_and_order` |
| | Identity cases: directory, frontmatter, differing, unresolved, multi-entrypoint | `test_identity_cases_frontmatter_directory_unresolved_entrypoints_and_order` |
| | Relative / tilde paths via `snapshot_path` | `test_identity_cases_frontmatter_directory_unresolved_entrypoints_and_order` |
| | Clear notice when no candidates match selected installation | `test_candidate_no_matches_shows_notice` |
| **§3. Agent Strip & Selection** | Preserves scan sorted agent-ID order | `test_agent_strip_options_and_deterministic_switching` |
| | Left/Right keys navigate and wrap deterministically | `test_agent_strip_options_and_deterministic_switching` |
| | DOM order preserved on eligibility-adding refresh | `test_agent_dom_order_after_eligibility_refresh` |
| | Zero-agent skill shows clear explanation and zero Why requests | `test_zero_agent_skill_shows_explanation_and_zero_requests` |
| | Mixed unknown + known agent IDs explained in status and title | `test_mixed_unknown_and_known_agent_ids_explained` |
| | Defensive constructed all-unknown agent IDs explained, exit code 0 | `test_defensive_unknown_agent_in_constructed_snapshot` |
| | Missing key predispatch validation with zero requests | `test_missing_key_predispatch_zero_calls` |
| | Literal Button label rendering (`markup=False`) | `test_agent_button_renders_captured_label_literally` |
| **§4. Candidate Collapsibles & Rendering** | Report candidate order preserved | `test_candidate_collapsibles_expanded_and_collapsed` |
| | Candidate matching opening key initially expanded, others collapsed | `test_candidate_collapsibles_expanded_and_collapsed` |
| | Shared `STATE_STYLE` styling applied to marks and tags | `test_candidate_collapsibles_expanded_and_collapsed` |
| | Redundant entrypoint lines suppressed via `snapshot_same_location` | `test_candidate_collapsibles_expanded_and_collapsed` |
| | Literal body rendering (`markup=False`, backslashes/brackets preserved) | `test_literal_rendering_markup_false` |
| | Controls, expansion, and focus preserved on redraw (`_update_ui`) | `test_redraw_preserves_candidate_focus_and_expansion` |
| | Viewport wrapping at 100x30 and 60x24 without horizontal scroll | `test_terminal_dimensions_100x30_and_60x24_controls_and_wrapping` |
| **§5. Token Concurrency & Races** | Blocked Home worker race to detail agent change, stale success/error ignored | `test_real_worker_race_blocked_home_to_detail_agent_change_and_stale_callbacks` |
| | Suspended Home `_drive` and `note_report_outcome` guards prevent hidden dispatch | `test_home_suspended_drive_and_outcome_guards_prevent_hidden_dispatch` |
| | Ownership cancellation guards kill mutations on suspend, token switch, pop | `test_cancellation_guards_kill_mutants` |
| | Detail A -> B switch while B running; late A outcome rejected | `test_real_worker_detail_a_to_b_while_b_running` |
| | Detail agent switch A -> B while A completes | `test_detail_agent_switch_a_to_b_while_a_completes` |
| | Pending blocked capture plus detail report | `test_pending_blocked_capture_plus_detail_report` |
| | Accepted non-capture report event does not cancel or dispatch Home | `test_non_capture_accepted_event_synchronization_does_not_cancel_or_dispatch_home` |
| | Real-pop delayed detail callback protects resumed Home token | `test_real_pop_delayed_detail_callback_protects_resumed_home` |
| | U3 identity-matching rejection branch in HomeScreen | `test_u3_identity_matching_rejection_branch` |
| | Cache hit and redraw deduplication | `test_cache_hit_and_redraw_deduplication` |
| | Accepted report fault does not retry loop | `test_accepted_report_fault_does_not_retry_loop` |
| **§6. Refresh Matrix & Active Status** | Refresh on detail with surviving installation | `test_refresh_on_detail_surviving_installation` |
| | Removed installation returns to Home with notice (named + keyed) | `test_refresh_on_detail_removed_installation_returns_to_home_with_notice` |
| | Removal notice cleared on explicit Home r and action_refresh | `test_notice_cleared_on_explicit_refresh` |
| | Refresh with changed agent eligibility updates strip | `test_refresh_on_detail_changed_agent_eligibility` |
| | Refresh with no agent replacement shows explanation | `test_refresh_on_detail_no_agent_replacement` |
| | Refresh with empty replacement catalog closes to empty Home with notice | `test_refresh_on_detail_empty_replacement_catalog` |
| | Retained Home filter excludes controller fallback selection (0 rows) | `test_refresh_on_detail_retained_home_filter_excludes_controller_fallback` |
| | Real capture refusal, retry, and fault exception paths | `test_refresh_actual_refusal_retry_and_fault_paths` |
| | All-filter return matrix across lifecycle states (pending, refusal, retry, fault, changed count, removal) | `test_all_filter_return_matrix_active_home_status` |
| | Broad read sentinels and target preservation manifest across all app actions | `test_broad_read_sentinels_and_target_preservation_manifest` |
| **§7. Unit & Helper Coverage** | View model and helper functions coverage | `test_why_helpers_coverage` |
| | Screen lifecycle, status formatting, and focus delegation branches | `test_why_screen_unit_branches` |
