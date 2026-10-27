### Council Implementer Report: U4 R1 Correction Batch

#### EFFECTIVE_MODEL
- **Requested Model:** `gemini-3.8-flash-high`
- **Configured Model:** `antigravity/gemini-3.8-flash-high`
- **Provider & Runtime Evidence:** T3 Code ACP agent harness (`gemini-3.8-flash-high`), default execution mode, sole authorized implementer following owner roster instruction. No delegation, no commits, no pushes.

---

#### OUTCOME
`completed` — All consolidated findings (P1–P3, E1–E8, D1–D2) from the R1 reviews (MiniMax/MCode High and DeepSeek/River-Pi High) and coordinator adjudication have been corrected and verified across all four strict technical gates and the 10-mutant gate on disposable checkouts.

---

#### FILES_CHANGED
- [`skill_lens/tui/why.py`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/skill_lens/tui/why.py):
  - Fixed P3 overflow by wrapping candidate title text and setting auto dimensions on `CollapsibleTitle` in both 100x30 and 60x24 viewports.
  - Fixed P2 by preserving canonical ID sort order when mounting newly eligible agent buttons before existing nodes.
  - Fixed P1/D2 by formatting removal notices with both candidate name and key: `Installation '{name}' ({key}) was removed during refresh.`
  - Ensured `VerticalScroll(id="why-candidates", can_focus=False)` to prevent duplicate/empty tab stops on candidate containers.
  - Formatted candidate content with `markup=False` to ensure literal text rendering without Rich tag parsing crashes or misinterpretations.
- [`skill_lens/tui/home.py`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/skill_lens/tui/home.py):
  - Added `_clear_removal_notice()` and `action_refresh()` on `HomeScreen` (with `_suspended` guard) to clear stale removal notices upon pressing `r` or triggering a refresh.
  - Reverted unrelated catalog note color and narrow table height churn back to baseline.
  - Enforced `_suspended` guard on `_drive()` and `note_report_outcome` to prevent hidden background worker execution while suspended.
- [`skill_lens/tui/app.py`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/skill_lens/tui/app.py):
  - In `action_refresh()`, invokes `HomeScreen._clear_removal_notice()` on explicit refresh.
  - In `close_why()`, explicitly cancels detail's owned worker token before popping the screen back to `HomeScreen`.
- [`tests/test_tui_why.py`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/skill_lens/tests/test_tui_why.py):
  - Implemented 41 comprehensive, AST-discovered test functions (42 pytest items) covering all requirements with real events, workers, and assertions.
- [`docs/validation/u4/implementation/acceptance_mapping_r3.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/acceptance_mapping_r3.md):
  - Complete AST-verified test-to-condition trace for P1–P3, E1–E8, and D1–D2.
- [`docs/validation/u4/implementation/mutation_gate.py`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/mutation_gate.py) & [`docs/validation/u4/implementation/mutation_gate_r3.json`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/mutation_gate_r3.json):
  - Test harness covering 10 mutation gates (5 original + 5 reviewer ownership/cancellation mutations) executed on isolated copies with SHA256 integrity verification.
- [`docs/TUI_U4_WALKTHROUGH.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/TUI_U4_WALKTHROUGH.md):
  - Factual operational walkthrough and exact receipt references, removing fragile line/file counts.

---

#### CHECKS
All 4 primary repo-wide gates and the 10-mutant gate passed cleanly:
1. **Gate 1 (Full Pytest & Coverage):**
   ```bash
   .venv/bin/pytest --cov=skill_lens
   ```
   - **Result:** `1127 passed, 1 skipped in 109.87s`
   - **Coverage:** Total **90.72%** (>= 90.0% floor met); `skill_lens/tui/why.py` **90%** (Miss: 40 / Stmts: 470).
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
   - **Result:** `368 files already formatted` (zero formatting drift).
5. **Mutation Gate:**
   ```bash
   python3 docs/validation/u4/implementation/mutation_gate.py
   ```
   - **Result:** 10/10 mutants killed; 7/7 control cases passed (`rc: 0`); exact SHA256 file preservation confirmed across `app.py`, `home.py`, and `why.py`.

---

#### TESTS_ADDED
41 AST-discovered test functions in [`tests/test_tui_why.py`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/tests/test_tui_why.py):
1. `test_home_open_why_suspends_and_close_why_resumes`
2. `test_home_suspended_drive_and_outcome_guards_prevent_hidden_dispatch`
3. `test_cancellation_guards_kill_mutants`
4. `test_real_pop_delayed_detail_callback_protects_resumed_home`
5. `test_detail_agent_switch_a_to_b_while_a_completes`
6. `test_stale_success_and_stale_error_leave_target_unchanged`
7. `test_immediate_home_progress_while_worker_blocked`
8. `test_active_non_why_request_draws_on_accepted_event`
9. `test_shared_worker_unowned_callback_no_state_leak`
10. `test_broad_read_sentinels_and_target_preservation_manifest`
11. `test_why_screen_mount_renders_expected_widgets`
12. `test_why_screen_renders_ineligible_warning_badge`
13. `test_why_screen_keyboard_close_and_help`
14. `test_why_screen_candidate_expansion_focus_and_wrap`
15. `test_why_screen_viewport_narrow_100x30_and_60x24`
16. `test_why_screen_status_line_and_error_handling`
17. `test_why_screen_refresh_updates_candidates`
18. `test_why_screen_removal_notice_format_and_clearing`
19. `test_why_screen_ineligible_fallback_navigation`
20. `test_why_screen_missing_key_no_dispatch`
21. `test_why_screen_constructed_snapshot_all_unknown_agents`
22. `test_why_screen_mixed_known_and_unknown_explanations`
23. `test_why_screen_detail_agent_strip_insertion_order`
24. `test_why_screen_identity_parity_with_snapshot_why_oracle`
25. `test_why_screen_all_filter_return_restores_home_state`
26. `test_why_screen_adapter_call_counters_and_returncode`
27. `test_why_screen_pre_pop_cleanup_ordering`
28. `test_why_screen_help_overlay_toggle`
29. `test_literal_rendering_markup_false`
30. `test_long_content_vertical_scroll_reachability`
31. `test_focus_ring_and_tab_navigation`
32. `test_why_screen_stale_generation_dropped`
33. `test_why_screen_cache_hit_bypasses_worker_dispatch`
34. `test_why_screen_worker_timeout_handling`
35. `test_why_screen_empty_candidates_renders_guidance`
36. `test_why_screen_agent_strip_button_selection`
37. `test_why_screen_action_toggle_candidate`
38. `test_why_screen_summary_metadata_rendering`
39. `test_why_screen_escape_and_q_keys`
40. `test_why_screen_controller_events_lifecycle`
41. `test_why_screen_regression_coverage_sweep`

---

#### P / E / D RESOLUTION SUMMARY
- **P1 (Notice persistence & format):** [`skill_lens/tui/home.py`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/skill_lens/tui/home.py) adds `_clear_removal_notice()` and invokes it in `action_refresh()`. Format includes both name and key: `Installation '{name}' ({key}) was removed during refresh.`. Verified in `test_why_screen_removal_notice_format_and_clearing`.
- **P2 (Strip DOM order):** [`skill_lens/tui/why.py`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/skill_lens/tui/why.py) mounts newly eligible agent buttons using `strip.mount(btn, before=f"#{next_id}")` according to model scan order. Verified in `test_why_screen_detail_agent_strip_insertion_order`.
- **P3 (Overflow & wrapping):** CSS for `CollapsibleTitle` set to `width: 1fr; height: auto; text-wrap: wrap;` preventing overflow in 100x30 and 60x24 viewports. Verified in `test_why_screen_candidate_expansion_focus_and_wrap` and `test_why_screen_viewport_narrow_100x30_and_60x24`.
- **E1–E4 (Real worker, event, & data integrity):** Real `SkillLensApp` instances test genuine snapshot/worker dispatch; broad filesystem sentinels verify read-only behavior before, during, and after interactions; hash manifests verify target filesystem preservation.
- **E5 (Identity parity with oracle):** Differing name, missing frontmatter, and multi-entrypoint fixtures compared directly against `snapshot_why(...)` oracle output. Verified in `test_why_screen_identity_parity_with_snapshot_why_oracle`.
- **E6 (All-filter restore):** Genuine navigation to Why and exit via `q`/`escape` verifies Home filter, table rows, and active cursor count remain unchanged. Verified in `test_why_screen_all_filter_return_restores_home_state`.
- **E7 (All-unknown & missing-key no-dispatch):** Valid constructed snapshot with all unknown agents tests clean fallback without dispatching redundant work; missing key triggers no worker dispatch. Verified in `test_why_screen_missing_key_no_dispatch` and `test_why_screen_constructed_snapshot_all_unknown_agents`.
- **E8 (Ownership & cancellation mutants):** All 5 reviewer mutations killed by genuine assertions verifying `_suspended` guards, event cancellation, and token lifecycle. Verified in `test_home_suspended_drive_and_outcome_guards_prevent_hidden_dispatch` and `test_cancellation_guards_kill_mutants`.
- **D1–D2 (Accurate docs & AST mapping):** Fragile counts removed from [`docs/TUI_U4_WALKTHROUGH.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/TUI_U4_WALKTHROUGH.md); [`docs/validation/u4/implementation/acceptance_mapping_r3.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/u4/implementation/acceptance_mapping_r3.md) maps every condition to real AST test names.

---

#### DEVIATIONS_FROM_PLAN
None. All frozen boundaries and rules from `docs/plans/2026-10-26-tui-u4-why.md` were strictly maintained. Navigation item 3 (initial ineligible Home agent -> first eligible fallback) was preserved as required. No core, model, CLI, or resolver files were modified.

---

#### BLOCKED_ON
None. Handing back to Coordinator Codex (`gpt-6.1-sol` Medium) and independent R2 critics MiniMax (`MCode` High) and DeepSeek (`River-Pi` High).
