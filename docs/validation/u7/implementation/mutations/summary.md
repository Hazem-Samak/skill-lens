# U7 isolated mutation campaign

All variants ran in a disposable archive of HEAD with the current in-scope U7 source/tests overlaid. The real checkout was never mutated. Each case used control → mutation → restored control. HOME and CODEX_HOME pointed at a fresh temporary sandbox; tests use their `mock_home` fixture for synthetic systems. The parent-authored independent probe was copied read-only beside the isolated test tree for the hidden-Enter case.

| Mutation | Test | Control before | Mutant | Restore control | Result |
| --- | --- | ---: | --- | ---: | --- |
| reverse_findings | `tests/test_tui_doctor.py::test_real_captured_findings_keep_model_order_and_cli_json` | 0 | nonzero, expected assertion | 0 | PASS |
| drop_message | `tests/test_tui_doctor.py::test_real_captured_findings_keep_model_order_and_cli_json` | 0 | nonzero, expected assertion | 0 | PASS |
| drop_detail | `tests/test_tui_doctor.py::test_doctor_shows_literal_fields_and_full_detail_at_both_widths` | 0 | nonzero, expected assertion | 0 | PASS |
| alter_evidence | `tests/test_tui_doctor.py::test_doctor_shows_literal_fields_and_full_detail_at_both_widths` | 0 | nonzero, expected assertion | 0 | PASS |
| recompute_doctor | `tests/test_tui_doctor.py::test_doctor_first_visit_stays_frozen_after_synthetic_tree_changes` | 0 | nonzero, expected assertion | 0 | PASS |
| disable_reverse_display_path | `tests/test_tui_doctor.py::test_finding_catalog_keys_use_only_exact_captured_identity` | 0 | nonzero, expected assertion | 0 | PASS |
| match_by_basename | `tests/test_tui_doctor.py::test_finding_catalog_keys_use_only_exact_captured_identity` | 0 | nonzero, expected assertion | 0 | PASS |
| select_first_ambiguous_candidate | `tests/test_tui_doctor.py::test_finding_catalog_keys_use_only_exact_captured_identity` | 0 | nonzero, expected assertion | 0 | PASS |
| retain_blocking_text_filter | `tests/test_tui_doctor.py::test_doctor_first_visit_stays_frozen_after_synthetic_tree_changes` | 0 | nonzero, expected assertion | 0 | PASS |
| retain_blocking_agent_filter | `tests/test_independent_u7.py::test_parent_first_open_frozen_alias_jump_clears_filters` | 0 | nonzero, expected assertion | 0 | PASS |
| skip_why_suspension | `tests/test_tui_doctor.py::test_doctor_entry_suspends_home_why_and_old_completion_keeps_new_owner` | 0 | nonzero, expected assertion | 0 | PASS |
| invalidate_newer_owned_request_on_stale_rejection | `tests/test_tui_doctor.py::test_doctor_entry_suspends_home_why_and_old_completion_keeps_new_owner` | 0 | nonzero, expected assertion | 0 | PASS |
| retain_stale_doctor_and_json_on_refresh | `tests/test_tui_doctor.py::test_doctor_refresh_preserves_duplicate_occurrence_and_replaces_raw_document` | 0 | nonzero, expected assertion | 0 | PASS |
| serialize_ui_derived_json | `tests/test_tui_doctor.py::test_real_captured_findings_keep_model_order_and_cli_json` | 0 | nonzero, expected assertion | 0 | PASS |
| accept_stale_generation_with_valid_key | `tests/test_tui_doctor.py::test_stale_generation_with_valid_catalog_key_does_not_jump` | 0 | nonzero, expected assertion | 0 | PASS |
| allow_hidden_enter_in_json | `tests/test_independent_u7.py::test_parent_first_open_frozen_alias_jump_clears_filters` | 0 | nonzero, expected assertion | 0 | PASS |

Temporary isolated checkout: `/var/folders/tf/jsdyxcts6y72fs98s7wl3dfm0000gn/T/skill-lens-u7-mutations-jywj5vx7/checkout`. Per-case full output is retained in this folder.
