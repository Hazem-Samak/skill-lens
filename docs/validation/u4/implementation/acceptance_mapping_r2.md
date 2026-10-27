# U4 Acceptance Criterion-to-Test Mapping (Revision 2)

**Author:** Sole implementer Antigravity (Gemini 3.8 Flash High) under owner authorization.  
**Operative Reference Plan:** `docs/plans/2026-10-26-tui-u4-why.md` @ `684cdb7aa0e3a28e5bb722bf65e4f3953edc6f76`.  
**Scope:** Verification of coordinator findings C1–C7 and full frozen acceptance criteria.

---

## 1. Coordinator Findings Resolution (C1–C7)

| Item | Finding Summary | Product Fix Location | Test Coverage Evidence |
| :--- | :--- | :--- | :--- |
| **C1** | Candidate collapse state & Title focus stolen on redraw / `app._update_ui` | `skill_lens/tui/why.py`: `_CandidateBlock` preserves `state: HeadlineState` & `title`; container `#why-candidates` only rebuilt when context (`_rendered_candidate_context`) changes; in-place button updates in `_refresh_strip` | `tests/test_tui_why.py::test_c1_regression_collapse_and_title_focus_preserved_on_update_ui`; coordinator reproduction: `docs/validation/u4/implementation/coordinator/reproduction_r1.py` |
| **C2** | Agent names/tags interpreted as markup in Button creation & label updates | `skill_lens/tui/why.py`: literal `Content.from_text(option.label, markup=False)` at both creation and update boundaries; all static titles, body, and status widgets use literal Content | `tests/test_tui_why.py::test_c2_regression_agent_button_label_and_update_literal_markup`, `test_literal_rendering_markup_false`, `test_agent_button_renders_captured_label_literally` |
| **C3** | Missing controlled `threading.Event` races, pilot pop races, and U3 rejection branch | `skill_lens/tui/why.py`, `home.py`, `app.py`: proper token lifecycle, `_cancel_owned_token`, `suspend_why`/`resume_why` | `tests/test_tui_why.py`:<br>• `test_real_worker_race_blocked_home_to_detail_agent_change_and_stale_callbacks`<br>• `test_real_worker_detail_a_to_b_while_b_running`<br>• `test_pending_blocked_capture_plus_detail_report`<br>• `test_non_capture_accepted_event_synchronization_does_not_cancel_or_dispatch_home`<br>• `test_real_pop_delayed_detail_callback_protects_resumed_home`<br>• `test_u3_identity_matching_rejection_branch`<br>• `test_detail_agent_switch_a_to_b_while_a_completes` |
| **C4** | Missing refresh matrix on All filter, changed eligibility, retry, fault, normal/sticky exits | `skill_lens/tui/why.py`: `sync_from_controller`, `_rebuild_from_snapshot`, removal notice propagation | `tests/test_tui_why.py`:<br>• `test_refresh_changed_eligibility_no_agent_explanation`<br>• `test_refresh_empty_replacement_catalog_closes_to_home_with_notice`<br>• `test_refresh_retained_filter_excluding_fallback_selection`<br>• `test_real_capture_refusal_retry_and_fault_paths`<br>• `test_all_filter_return_matrix_across_lifecycle_events`<br>• `test_why_screen_quit_exit_codes_normal_and_sticky` |
| **C5** | Target fixture alteration before visit, broad read sentinels (Path/os open, resolve, stat, lstat, readlink), manifest lifecycle | `skill_lens/tui/why.py`: strictly uses `snapshot_path`, `snapshot_same_location`, immutable report | `tests/test_tui_why.py::test_broad_read_sentinels_and_target_preservation_manifest` (guarded by `sys.monitoring` and broad monkeypatches; verifies parity across file deletion/mutation/retargeting before visit and full manifest) |
| **C6** | Identity cases (directory/frontmatter/differing/invalid/missing/unresolved/multiple entrypoints), `STATE_STYLE`, `snapshot_path`, mixed unknown+known agents, 100x30 and 60x24 controls | `skill_lens/tui/why.py`: `snapshot_path` for header, `STATE_STYLE` styling via `Content.assemble`, unknown agent explanation in status | `tests/test_tui_why.py`:<br>• `test_identity_cases_frontmatter_directory_unresolved_entrypoints_and_order`<br>• `test_mixed_unknown_and_known_agent_ids_explained`<br>• `test_terminal_dimensions_100x30_and_60x24_controls_and_wrapping`<br>• `test_candidate_no_matches_shows_notice` |
| **C7** | Factual errors in docs (U5 label, stale ownership sentence, contradictory status, walkthrough winner/fields/link) | Corrected `FULL_SCREEN_TUI.md`, `docs/TUI_U4_WALKTHROUGH.md`, `README.md`, `DEVELOPMENT.md`, `CHANGELOG.md`; preserved historical receipts; generated `mutation_gate_r2.json` | Review of updated markdown documents; all doc mismatches resolved. |

---

## 2. Frozen Acceptance Criteria Mapping

| Acceptance Criterion | Verification Method & Test Selector |
| :--- | :--- |
| **1. Enter Navigation & Focus** | |
| Enter on focused nonempty table opens WhyScreen | `tests/test_tui_why.py::test_why_screen_opens_on_enter_press_nonempty_table` |
| Enter on empty table or filter empty state is no-op | `tests/test_tui_why.py::test_enter_on_empty_table_or_empty_filter_is_noop` |
| Double Enter deduplication | `tests/test_tui_why.py::test_double_enter_deduplicated_no_second_push` |
| Backspace and Escape pop back to Home | `tests/test_tui_why.py::test_escape_and_backspace_pop_to_home` |
| Preserves Home filter text, cursor, selection, and focus | `tests/test_tui_why.py::test_escape_preserves_home_state_and_focus` |
| **2. Header & Identity Display** | |
| Header displays canonical path, agent, lookup name, policy evidence, headline | `tests/test_tui_why.py::test_why_screen_header_display` |
| Identity cases: directory, frontmatter, differing names, invalid/missing frontmatter, unresolved key, multiple entrypoints | `tests/test_tui_why.py::test_identity_cases_frontmatter_directory_unresolved_entrypoints_and_order` |
| Header uses `snapshot_path` (relativized / tilde) | `tests/test_tui_why.py::test_why_screen_header_display`, `test_identity_cases_frontmatter_directory_unresolved_entrypoints_and_order` |
| Notice shown when no candidates match | `tests/test_tui_why.py::test_candidate_no_matches_shows_notice` |
| **3. Agent Strip & Selection** | |
| Strip buttons in deterministic order | `tests/test_tui_why.py::test_agent_strip_options_and_deterministic_switching` |
| Left/Right keys navigate/wrap strip | `tests/test_tui_why.py::test_agent_strip_options_and_deterministic_switching` |
| Explanation for zero-agent skill (zero requests) | `tests/test_tui_why.py::test_zero_agent_skill_shows_explanation_and_zero_requests` |
| Explanation for mixed unknown + known agent IDs | `tests/test_tui_why.py::test_mixed_unknown_and_known_agent_ids_explained` |
| Literal Button label rendering and updating (`markup=False`) | `tests/test_tui_why.py::test_c2_regression_agent_button_label_and_update_literal_markup`, `test_agent_button_renders_captured_label_literally` |
| **4. Candidate Collapsibles & Rendering** | |
| Report candidate order preserved | `tests/test_tui_why.py::test_candidate_collapsibles_expanded_and_collapsed` |
| Candidate matching opening key initially expanded, others collapsed | `tests/test_tui_why.py::test_candidate_collapsibles_expanded_and_collapsed` |
| Shared `STATE_STYLE` styling applied to marks and tags | `tests/test_tui_why.py::test_candidate_collapsibles_expanded_and_collapsed`, `test_c1_regression_collapse_and_title_focus_preserved_on_update_ui` |
| Literal body rendering (markup=False, no tag interpretation) | `tests/test_tui_why.py::test_literal_rendering_markup_false` |
| Controls and focus preserved on UI update / redraw | `tests/test_tui_why.py::test_c1_regression_collapse_and_title_focus_preserved_on_update_ui` |
| Redundant entrypoint lines suppressed via `snapshot_same_location` | `tests/test_tui_why.py::test_candidate_collapsibles_expanded_and_collapsed` |
| **5. Token Concurrency, Screen Ownership & Races** | |
| Blocked Home -> detail -> agent change -> stale Home -> back -> stale detail | `tests/test_tui_why.py::test_real_worker_race_blocked_home_to_detail_agent_change_and_stale_callbacks` |
| Detail A -> B switch while B running; late A outcome rejected | `tests/test_tui_why.py::test_real_worker_detail_a_to_b_while_b_running`, `test_detail_agent_switch_a_to_b_while_a_completes` |
| Detail report + refresh capture both blocked; detail completes while capture pending | `tests/test_tui_why.py::test_pending_blocked_capture_plus_detail_report` |
| Accepted non-capture report event does not cancel/dispatch hidden Home | `tests/test_tui_why.py::test_non_capture_accepted_event_synchronization_does_not_cancel_or_dispatch_home` |
| Real-pop delayed detail callback protects resumed Home token | `tests/test_tui_why.py::test_real_pop_delayed_detail_callback_protects_resumed_home` |
| U3 identity-matching rejection branch in Home | `tests/test_tui_why.py::test_u3_identity_matching_rejection_branch` |
| Cache hit and redraw deduplication | `tests/test_tui_why.py::test_cache_hit_and_redraw_deduplication` |
| **6. Refresh Matrix & Active Status** | |
| Session refresh rebuilds options and preserves display | `tests/test_tui_why.py::test_session_refresh_rebuilds_options_and_preserves_display` |
| Removed installation closes detail with persistent removal notice on Home | `tests/test_tui_why.py::test_session_refresh_removed_skill_closes_detail_with_removal_notice` |
| Changed eligibility & no-agent explanation after refresh | `tests/test_tui_why.py::test_refresh_changed_eligibility_no_agent_explanation` |
| Empty replacement catalog closes to Home with notice | `tests/test_tui_why.py::test_refresh_empty_replacement_catalog_closes_to_home_with_notice` |
| Retained filter excluding fallback selection | `tests/test_tui_why.py::test_refresh_retained_filter_excluding_fallback_selection` |
| Real capture refusal (`SnapshotTooLarge`), retry (`SnapshotChanged`), and internal fault (`RuntimeError`) | `tests/test_tui_why.py::test_real_capture_refusal_retry_and_fault_paths` |
| All-filter return matrix across pending, refusal, retry, fault, count, and removal | `tests/test_tui_why.py::test_all_filter_return_matrix_across_lifecycle_events` |
| Normal exit code 0 vs sticky-3 exit code on quit | `tests/test_tui_why.py::test_why_screen_quit_exit_codes_normal_and_sticky` |
| Accepted report fault does not retry loop | `tests/test_tui_why.py::test_accepted_report_fault_does_not_retry_loop` |
| **7. Data Freeze & Read Sentinels** | |
| Target file alteration/deletion/retargeting before visit; full manifest parity | `tests/test_tui_why.py::test_broad_read_sentinels_and_target_preservation_manifest` |
| Broad read probes (open, read_text, read_bytes, resolve, stat, lstat, readlink) fail | `tests/test_tui_why.py::test_broad_read_sentinels_and_target_preservation_manifest` |
| Synthetic HOME/XDG and protected system roots | `tests/test_tui_why.py::test_broad_read_sentinels_and_target_preservation_manifest` |
| AST read-only guard (no prohibited modules/operations) | `tests/test_tui_read_only.py::test_shipped_tui_code_has_zero_read_only_violations` |
| **8. Layout & Usability** | |
| 100x30 and 60x24 layout, long content wrapping, keyboard reachability | `tests/test_tui_why.py::test_terminal_dimensions_100x30_and_60x24_controls_and_wrapping` |

---

## 3. Mutation Gate Evidence

Run using `.venv/bin/python docs/validation/u4/implementation/mutation_gate.py --out docs/validation/u4/implementation/mutation_gate_r2.json`.

| Mutant | Description | Test Selector | Result | Detected Pattern |
| :--- | :--- | :--- | :--- | :--- |
| **1. Read-Only Guard** | `import rich` planted in `why.py` | `tests/test_tui_read_only.py::test_shipped_tui_code_has_zero_read_only_violations` | **Killed** (rc=1) | `rich` |
| **2. Target Read Sentinel** | Direct `Path(...).read_text()` in `_update_display` | `tests/test_tui_why.py::test_broad_read_sentinels_and_target_preservation_manifest` | **Killed** (rc=1) | `Forbidden synthetic-target filesystem read` |
| **3. Detail Token Guard** | Remove token check in `_cancel_owned_token` | `tests/test_tui_why.py::test_real_pop_delayed_detail_callback_protects_resumed_home` | **Killed** (rc=1) | `AssertionError: Unowned Home token was invalidated by delayed detail callback!` |
| **4. Arguments Check** | Remove arguments check in `note_report_outcome` | `tests/test_tui_why.py::test_detail_agent_switch_a_to_b_while_a_completes` | **Killed** (rc=1) | `AssertionError: assert ResolutionReport...` |
| **5. Literal Markup** | Enable `markup=True` in candidate body | `tests/test_tui_why.py::test_literal_rendering_markup_false` | **Killed** (rc=1) | `AssertionError` |

- **Controls:** All 5 pass on unmodified code (rc=0).
- **Restoration:** Hash of `why.py` before and after identical; checkout never modified.
- **Historical receipt:** Preserved untouched at `docs/validation/u4/implementation/mutation_gate.json`.
