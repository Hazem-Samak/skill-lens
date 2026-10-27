### Council Implementer Report: Pre-R2 Proof Gaps Resolution

#### EFFECTIVE_MODEL
- **Requested Model:** `gemini-3.8-flash-high`
- **Configured Model:** `antigravity/gemini-3.8-flash-high`
- **Provider & Runtime Evidence:** T3 Code ACP agent harness (`gemini-3.8-flash-high`), default execution mode, sole authorized implementer following owner roster instruction. No delegation, no commits, no pushes.

---

#### OUTCOME
`completed` — All five bounded pre-review R2 proof gaps detailed in [`pre-review-r2-gaps.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/coordinator/pre-review-r2-gaps.md) have been systematically closed and verified against live oracle captures, deterministic ACK callback synchronization, public Textual APIs, whole-repo quality gates, and an expanded 11-mutant test harness.

---

#### FILES_CHANGED
- [`skill_lens/tui/why.py`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/skill_lens/tui/why.py):
  - **Gap 4 Fix:** Eliminated private `strip._nodes._sort` and replaced it with Textual's public [`Widget.move_child(child, *, before=...)`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/skill_lens/tui/why.py#L740-L755) API inside `_refresh_strip`, strictly preserving model scan-ID sort order, same-context focus, and Left/Right key navigation.
- [`tests/test_tui_why.py`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/tests/test_tui_why.py):
  - **Gap 1 Overhaul:** Expanded [`test_identity_cases_frontmatter_directory_unresolved_entrypoints_and_order`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/tests/test_tui_why.py#L930-L1065) across 7 representative live identity fixture visits:
    1. `directory_name` agent (`opencode` on differing directory vs declared name -> resolves to directory name);
    2. `frontmatter_name` agent (`codex` on differing name -> resolves to declared name);
    3. `hybrid` agent (`claude` on `claude_diff`);
    4. Missing frontmatter fallback (`codex` on `missing_fm` -> falls back to directory name);
    5. Malformed frontmatter (`codex` on `malformed_fm` -> falls back to directory name);
    6. Unresolved canonical fallback / dangling symlink (`broken_link` -> gracefully handled);
    7. Multi-entrypoint scenario on `opencode` (canonical directory + symlink) asserting `len(candidates) > 1`, multiple candidate container expansion, and candidate order against live [`snapshot_why`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/skill_lens/core/snapshot.py#L500-L580) oracles.
  - **Gap 2 Overhaul:** Overhauled [`test_broad_read_sentinels_and_target_preservation_manifest`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/tests/test_tui_why.py#L800-L928) with:
    1. Explicit selection of operative mutated install `shared`;
    2. True `snapshot_why` oracles pre-captured for all 3 agents (`claude`, `codex`, `opencode`) *prior* to applying disk edits;
    3. Explicit disk mutations executed before first detail visit (edits `shared/SKILL.md`, deletes `extra`, retargets symlink to `retargeted_shared`, writes Claude settings disabling `shared`);
    4. Post-mutation `baseline_manifest` computation;
    5. First detail visit executed under broad read sentinels (`builtins.open`, `Path.open`, `Path.read_bytes`, `Path.read_text`, `Path.stat`, `os.stat`, `os.lstat`, `os.readlink`), asserting exact report equality against pre-mutation oracles, visible titles/blocks, agent switches, toggle, and escape back to Home;
    6. Explicit `r` refresh proving generation advances (1 -> 2), deleted `extra` is gone from catalog, `shared` is disabled in controls, Why report status updates to `DISABLED` and hash changes;
    7. Exact manifest equality `safe_snapshot(mock_home) == baseline_manifest` across refresh and upon quit (`q`).
  - **Gap 3 Hardening:**
    1. In [`test_real_worker_race_blocked_home_to_detail_agent_change_and_stale_callbacks`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/tests/test_tui_why.py#L365-L425), replaced `pilot.pause(0.05)` with asynchronous polling of wrapped ACK hooks on [`controller.accept_view_result`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/skill_lens/tui/why.py#L250) and `controller.accept_view_error`, proving stale outcomes are rejected without blocking the Textual UI thread;
    2. In [`test_pending_blocked_capture_plus_detail_report`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/tests/test_tui_why.py#L505-L550), filtered Home and asserted exact cell states, group counts, and request queue across `r` and detail report delivery;
    3. In [`test_non_capture_accepted_event_synchronization_does_not_cancel_or_dispatch_home`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/tests/test_tui_why.py#L552-L600), verified exact unchanged cell, queue, and detail token parity before and after non-Why diff delivery.
- [`docs/validation/u4/implementation/mutation_gate.py`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/mutation_gate.py) & [`docs/validation/u4/implementation/mutation_gate_r3.json`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/mutation_gate_r3.json):
  - Added mutant #11 (`reviewer_mutant_6_stale_error_marks_controller_failed`) testing stale-error policy. All 11 mutants killed; all 8 controls passed (`rc: 0`); exact SHA256 file restoration verified.
- [`docs/validation/u4/implementation/coordinator/errata-historical-report.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/coordinator/errata-historical-report.md):
  - Formally noted the inaccurate speculative 41-test list in historical `implementer-combined-correction-report.md` without modifying raw historical reports. Provided the exact AST test list and gap-by-gap receipts.

---

#### CHECKS
All 4 whole-repo technical gates and the expanded 11-mutant gate passed cleanly:
1. **Gate 1 (Full Pytest & Coverage):**
   ```bash
   .venv/bin/pytest --cov=skill_lens
   ```
   - **Result:** `1127 passed, 1 skipped in 111.09s`
   - **Coverage:** Total **90.83%** (>= 90.0% floor met); `skill_lens/tui/why.py` **91%** (>= 90% floor met).
2. **Gate 2 (Mypy Static Typing):**
   ```bash
   .venv/bin/mypy
   ```
   - **Result:** `Success: no issues found in 39 source files` (zero errors).
3. **Gate 3 (Ruff Linting):**
   ```bash
   .venv/bin/ruff check .
   ```
   - **Result:** `All checks passed!` (zero lint errors).
4. **Gate 4 (Ruff Formatting):**
   ```bash
   .venv/bin/ruff format --check .
   ```
   - **Result:** `371 files already formatted` (clean, zero diff).
5. **Mutation Gate (11 Mutants / 8 Controls):**
   ```bash
   .venv/bin/python docs/validation/u4/implementation/mutation_gate.py
   ```
   - **Result:** 11 of 11 mutants killed (100% kill rate); 8 of 8 controls passed (`rc: 0`); all SHA256 hashes restored identically.

---

#### AST_VERIFIED_TEST_NAMES
Every test name below is directly verified via Python AST from [`tests/test_tui_why.py`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/tests/test_tui_why.py) and matches [`acceptance_mapping_r3.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/acceptance_mapping_r3.md) 1:1 (total: 41 test functions, 42 pytest items):

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

---

#### GAP_BY_GAP_PROOF_LOCATIONS

| Gap # | Category / Item | Resolution & Proof Receipt | Exact Proof Location |
|---|---|---|---|
| **1** | **E4 Identity Proof** | Tested 7 distinct identity fixtures: `directory_name` (`opencode`), `frontmatter_name` (`codex`), `hybrid` (`claude`), missing frontmatter, malformed frontmatter, broken symlink, and multi-entrypoint. Asserted `len(candidates) > 1`, multiple expanded blocks, and exact UI vs [`snapshot_why`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/skill_lens/core/snapshot.py#L500-L580) oracle field parity. | [`tests/test_tui_why.py::test_identity_cases_frontmatter_directory_unresolved_entrypoints_and_order`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/tests/test_tui_why.py#L930-L1065) |
| **2** | **E3 Data-Freeze Parity** | Chose operative installation `shared`. Pre-captured snapshot oracles for all agents. Applied real edits, deletions, symlink retargeting, and settings changes before first visit. Visited Detail under broad read sentinels verifying report equality and UI rendering. Triggered refresh `r`, proving generation advance, catalog deletion, control disablement, and report status/hash mutations. Proved safe snapshot manifest equality across refresh and quit. | [`tests/test_tui_why.py::test_broad_read_sentinels_and_target_preservation_manifest`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/tests/test_tui_why.py#L800-L928) |
| **3** | **E1 Callback Assertions & Stale-Error Mutant** | Replaced pause-based assertions with deterministic async ACK hooks on controller handlers verifying stale outcome rejection without UI thread blocks. Verified filtered Home cell states, group counts, and queue across `r` and detail delivery. Verified non-Why diff does not cancel or modify cells/queue. Added mutant #11 (`reviewer_mutant_6_stale_error_marks_controller_failed`) verifying stale error policy. | [`tests/test_tui_why.py`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/tests/test_tui_why.py#L365-L600), [`docs/validation/u4/implementation/mutation_gate.py`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/mutation_gate.py), [`docs/validation/u4/implementation/mutation_gate_r3.json`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/mutation_gate_r3.json) |
| **4** | **P2 Public Reordering API** | Replaced private `strip._nodes._sort` with Textual's supported public API [`Widget.move_child(target_btn, before=target_idx)`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/skill_lens/tui/why.py#L740-L755) in `_refresh_strip`. Preserves scan-ID sort order, same-context focus, and Left/Right key navigation. | [`skill_lens/tui/why.py`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/skill_lens/tui/why.py#L740-L755) |
| **5** | **Accurate Reporting & Zero Fabricated Assertions** | Authored errata document noting historical report inaccuracies without touching raw files. Verified 100% agreement between AST scan and acceptance mapping. All assertions backed by concrete pytest and mutation receipts. | [`docs/validation/u4/implementation/coordinator/errata-historical-report.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/coordinator/errata-historical-report.md), [`docs/validation/u4/implementation/acceptance_mapping_r3.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/acceptance_mapping_r3.md) |

---

#### DEVIATIONS_FROM_PLAN
None. Scope was strictly limited to authorized U4 paths (`skill_lens/tui/why.py`, `tests/test_tui_why.py`, `docs/validation/u4/`). All frozen plan boundaries, fallback requirements, and council guidelines were strictly followed.

---

#### BLOCKED_ON
None. Handing back for coordinator verification and subsequent independent R2 review dispatch to MiniMax (`MCode` High) and DeepSeek (`River-Pi` High).
