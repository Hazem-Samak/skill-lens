# Errata: Historical Implementer Combined Correction Report & Pre-R2 Gap Proofs

## 1. Context & Purpose
In the previous implementation handback report (`docs/validation/u4/implementation/coordinator/implementer-combined-correction-report.md`), a speculative/guessed 41-item test name list was inadvertently included under Section "FILES_CHANGED" / "TEST_FUNCTIONS" (containing names such as `test_why_screen_help_overlay_toggle`, `test_focus_ring_and_tab_navigation`, etc.).

Per coordinator directive in `docs/validation/u4/implementation/coordinator/pre-review-r2-gaps.md` (Observation 5):
- The raw historical report `implementer-combined-correction-report.md` is preserved untouched.
- This errata document is authored to formally correct the record and provide the true AST-verified list of 41 test functions (producing 42 pytest items) in `tests/test_tui_why.py`.
- Concrete receipts, proof locations, and verification logs for all 5 pre-R2 coordinator gaps are documented below.

---

## 2. True AST-Discovered Test Function List in `tests/test_tui_why.py`

Every function below was extracted directly via Python AST from `tests/test_tui_why.py` and matches `docs/validation/u4/implementation/acceptance_mapping_r3.md` with zero divergence:

1. `test_redraw_preserves_candidate_focus_and_expansion`
2. `test_agent_button_renders_captured_label_literally`
3. `test_notice_cleared_on_explicit_refresh`
4. `test_agent_dom_order_after_eligibility_refresh`
5. `test_enter_on_focused_nonempty_table_opens_why_screen`
6. `test_enter_on_empty_table_or_filtered_empty_list_is_noop`
7. `test_enter_on_filter_input_submits_filter_does_not_open_why`
8. `test_backspace_returns_to_home_preserving_filter_and_selection`
9. `test_priority_ctrl_c_and_q_quit_from_why`
10. `test_agent_strip_options_and_deterministic_switching`
11. `test_zero_agent_skill_shows_explanation_and_zero_requests`
12. `test_defensive_unknown_agent_in_constructed_snapshot`
13. `test_missing_key_predispatch_zero_calls`
14. `test_real_worker_race_blocked_home_to_detail_agent_change_and_stale_callbacks`
15. `test_home_suspended_drive_and_outcome_guards_prevent_hidden_dispatch`
16. `test_cancellation_guards_kill_mutants`
17. `test_real_worker_detail_a_to_b_while_b_running`
18. `test_detail_agent_switch_a_to_b_while_a_completes`
19. `test_pending_blocked_capture_plus_detail_report`
20. `test_non_capture_accepted_event_synchronization_does_not_cancel_or_dispatch_home`
21. `test_real_pop_delayed_detail_callback_protects_resumed_home`
22. `test_u3_identity_matching_rejection_branch`
23. `test_refresh_on_detail_surviving_installation`
24. `test_refresh_on_detail_removed_installation_returns_to_home_with_notice`
25. `test_refresh_on_detail_changed_agent_eligibility`
26. `test_refresh_on_detail_no_agent_replacement`
27. `test_refresh_on_detail_empty_replacement_catalog`
28. `test_refresh_on_detail_retained_home_filter_excludes_controller_fallback`
29. `test_refresh_actual_refusal_retry_and_fault_paths`
30. `test_all_filter_return_matrix_active_home_status`
31. `test_broad_read_sentinels_and_target_preservation_manifest`
32. `test_identity_cases_frontmatter_directory_unresolved_entrypoints_and_order`
33. `test_mixed_unknown_and_known_agent_ids_explained`
34. `test_terminal_dimensions_100x30_and_60x24_controls_and_wrapping`
35. `test_cache_hit_and_redraw_deduplication`
36. `test_accepted_report_fault_does_not_retry_loop`
37. `test_candidate_collapsibles_expanded_and_collapsed`
38. `test_candidate_no_matches_shows_notice`
39. `test_literal_rendering_markup_false`
40. `test_why_helpers_coverage`
41. `test_why_screen_unit_branches`

*Note:* Pytest item count is 42 because `test_real_worker_race_blocked_home_to_detail_agent_change_and_stale_callbacks` is parametrized for success and error outcomes.

---

## 3. Resolution Receipts for Pre-R2 Coordinator Gaps

### Gap 1 (E4 Identity Proof)
- **Problem:** Previous test opened Claude twice, lacking directory-only, frontmatter-only, invalid/missing frontmatter, unresolved canonical symlinks, or multi-entrypoint >1 candidate assertions.
- **Resolution:** Fully expanded in `tests/test_tui_why.py::test_identity_cases_frontmatter_directory_unresolved_entrypoints_and_order`.
  - Directory-name agent (`opencode` on `diff_dir` / `diff_declared`) asserts resolution to directory name.
  - Frontmatter-name agent (`codex` on `diff_dir` / `diff_declared`) asserts resolution to frontmatter name.
  - Hybrid agent (`claude` on `claude_diff`) asserts hybrid resolution behavior.
  - Frontmatter fallback (`codex` on `missing_fm`) asserts fallback to directory name when frontmatter is absent.
  - Malformed frontmatter (`codex` on `malformed_fm`) asserts graceful handling and directory fallback.
  - Dangling symlink (`broken_link`) asserts canonical resolution failure handling without crash.
  - Multiple-entrypoint scenario on `opencode` (canonical directory + symlink) asserts `len(candidates) > 1`, asserts multiple candidate blocks expanded, and validates rendered candidate ordering against live `snapshot_why(...)` oracle.
- **Proof:** All 7 identity sub-cases pass; `snapshot_why` oracles match UI rendered fields.

### Gap 2 (E3 Data-Freeze Parity)
- **Problem:** Previous test selected `scan.skills[0]` (`extra`), which was subsequently deleted, rendering mutations on `shared` inoperative; used length-only comparisons; did not mutate settings; lacked manifest comparison across refresh.
- **Resolution:** Overhauled in `tests/test_tui_why.py::test_broad_read_sentinels_and_target_preservation_manifest`.
  - Operative installation `shared` is explicitly selected and verified to exist.
  - Pre-captures true `snapshot_why` oracles for all 3 agents (`claude`, `codex`, `opencode`) *before* applying mutations.
  - Applies intentional mutations: edits `shared/SKILL.md`, deletes `extra`, retargets symlink to `retargeted_shared`, writes Claude settings disabling `shared`.
  - Computes `baseline_manifest` post-mutations. Under broad filesystem read sentinels (`builtins.open`, `Path.open`, `Path.read_bytes`, `Path.read_text`, `Path.stat`, `os.stat`, `os.lstat`, `os.readlink`), visits Detail screen for the first time.
  - Verifies exact report equality against pre-mutation oracle, visible title/blocks, agent switching, candidate toggle, and backspace navigation back to Home.
  - Triggers explicit refresh `r`: proves generation advances (1 -> 2), catalog reflects deletion of `extra`, control reflects settings mutation (`shared` disabled), and Why report changes (status `DISABLED`, hash changes).
  - Asserts safe snapshot manifest equality `safe_snapshot(mock_home) == baseline_manifest` across refresh and upon quit (`q`).
- **Proof:** Test passes completely without triggering read sentinels during pre-refresh inspection; manifest equality verified.

### Gap 3 (E1 Callback Assertions & Stale-Error Mutant)
- **Problem:** Real worker tests relied on `await pilot.pause(0.05)` after releasing gates rather than ACK events; pending refresh test did not assert filtered Home state; non-capture test lacked cell/queue assertions; mutation gate lacked a stale-error mutant.
- **Resolution:**
  - In `test_real_worker_race_blocked_home_to_detail_agent_change_and_stale_callbacks`, wrapped `controller.accept_view_result` and `controller.accept_view_error` with async ACK hooks. Polled predicates with `_wait_until` to verify stale outcomes are delivered to the controller and properly rejected (`accepted is False`) without blocking the Textual UI thread.
  - In `test_pending_blocked_capture_plus_detail_report`, verified on filtered Home that pending refresh preserves cell counts, group states, and request queue across `r` and detail report delivery.
  - In `test_non_capture_accepted_event_synchronization_does_not_cancel_or_dispatch_home`, verified exact cell parity, group statuses, queue contents, and detail worker token before and after a non-Why diff event.
  - Added mutant #11 (`reviewer_mutant_6_stale_error_marks_controller_failed`) to `docs/validation/u4/implementation/mutation_gate.py`.
- **Proof:** All 11 mutants killed; all 8 control tests passed (`rc: 0`); results saved in `docs/validation/u4/implementation/mutation_gate_r3.json`.

### Gap 4 (P2 Public Reordering API)
- **Problem:** `WhyScreen._refresh_strip` relied on private `strip._nodes._sort` with a `hasattr` fallback.
- **Resolution:** Replaced private DOM sorting in `skill_lens/tui/why.py` with Textual's public API:
  ```python
  strip.move_child(target_btn, before=target_idx)
  ```
  Iterates over sorted eligible agent IDs and moves the child button to its target index if its current index differs. Fully preserves model scan order, same-context button focus, and Left/Right key navigation wrapping.
- **Proof:** Clean `mypy` typing; `test_agent_dom_order_after_eligibility_refresh` and all strip interaction tests pass.

### Gap 5 (Accurate Reporting & Zero Fabricated Assertions)
- **Problem:** Speculative test names in historical report.
- **Resolution:** Preserved historical report; established this errata; confirmed 100% agreement between AST scan of `tests/test_tui_why.py` and `docs/validation/u4/implementation/acceptance_mapping_r3.md`.
- **Proof:** Automated AST script executed and confirmed zero divergence.

---

## 4. Technical Gates Summary
- **Pytest & Coverage:** 1127 passed, 1 skipped in 111.09s. Total repo coverage: 90.83% (>= 90.0% floor met). `skill_lens/tui/why.py` coverage: 91% (informational; the 90.0% gate applies to combined package coverage).
- **Mypy:** 0 issues found in 39 source files.
- **Ruff Check:** All checks passed.
- **Ruff Format:** 370 files already formatted.
- **Mutation Gate:** 11 mutants killed, 8 controls passed, 0 failures, all target files verified with SHA256 integrity restoration.
