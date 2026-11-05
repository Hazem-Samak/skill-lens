# U8 acceptance matrix — test mapping

Frozen plan: `docs/plans/2026-11-04-tui-u8-polish-help-docs.md` at
`b59478404a9d20d2670fb12a731c703f53eee798` (SHA-256
`01f6f250be358ed2168170e06513c1908ef616208a204d8f50f9dfa03f0c26de`).

All new tests are in `tests/test_tui_help.py` unless another file is named.
They drive real Textual `Pilot` key events and assert widget state, focus,
stack identity and content; no text-grid screenshots are pinned.

## A1 — Help over every screen, mode, state and both sizes

| Requirement | Tests |
| --- | --- |
| One Help over Home, Why, Diff, Agents, Compare picker and Doctor | `test_help_opens_and_dismisses_from_each_ordinary_screen[home|why|diff|agents|compare-picker|doctor]` |
| One Help over every raw JSON mode, including Compare result | `test_help_opens_over_raw_json_modes[home|why|diff|agents|compare-result|doctor]` |
| Initial loading state | `test_help_opens_during_initial_loading_and_no_session` |
| No-session state | `test_help_opens_during_initial_loading_and_no_session`, `test_help_no_session_over_agents_and_compare_picker` |
| 100×30 and 60×24 reachability, full body and visible Close | `test_help_body_and_close_are_reachable_at_both_sizes[size0|size1]`, `test_every_screen_and_help_remains_usable_at_both_sizes[size0|size1]` |
| Named, context-specific section and stack identity | all A1 tests assert `context.origin`, the section heading and `screen_stack[-2]` |

## A2 — Input typing, F1 toggle, exact restoration, hidden keys

| Requirement | Tests |
| --- | --- |
| `?qrahdgc/J` types literally | `test_home_filter_typing_is_literal_and_f1_preserves_text_and_cursor` |
| Cursor, left/right and Backspace remain Input behaviour | same test |
| F1 opens and closes the exact Help while typing | `test_f1_toggles_help_while_typing_and_does_not_lose_priority`, `test_home_filter_typing_is_literal_and_f1_preserves_text_and_cursor` |
| Plain `?` opens Help outside the filter | `test_plain_question_mark_opens_help_only_outside_the_filter_input` |
| Every dismiss route restores text, cursor and focus | `test_every_dismiss_route_restores_exact_input_focus_text_and_cursor[escape|backspace|question_mark|f1|close]` |
| Table focus and preview scroll restoration | `test_every_dismiss_route_restores_table_focus_and_preview_scroll` |
| JSON and detail scroll restoration on all screens | `test_help_restores_raw_json_scroll_on_every_screen[...]`, `test_help_restores_ordinary_detail_scroll_on_supported_screens[...]` |
| Hidden table/screen actions cannot leak | `test_hidden_screen_actions_cannot_leak_through_help[home|why|diff|agents|compare-picker|doctor]` |
| No stacking; stale close cannot pop a newer Help | `test_help_does_not_stack_and_stale_instance_cannot_close_a_newer_help` |
| Tab/Shift+Tab stay inside Help; Enter on body is inert | `test_tab_and_shift_tab_stay_inside_help_and_enter_on_body_does_nothing` |
| Body scroll keys and Close button | `test_help_body_scroll_keys_and_explicit_close_route` |

## A3 — Delayed work, exact ownership, old outcomes

| Requirement | Tests |
| --- | --- |
| Home Why suspension, cancellation, one replacement and cache reuse | `test_home_why_job_is_suspended_and_restarted_once` |
| Why detail suspension/resume (native + explicit) and cache reuse | `test_why_detail_job_is_suspended_and_restarted_once` |
| Diff suspension/resume and one replacement | `test_diff_job_is_suspended_and_restarted_once` |
| Compare suspension/resume and one replacement | `test_compare_job_is_suspended_and_restarted_once` |
| Cancel only the covered screen's own token | `test_help_cancels_only_the_covered_screens_own_token` |
| Old successes/errors before and after close; sticky current fault | `test_old_successes_and_errors_cannot_affect_newer_work_or_sticky_state` |

## A4 — Capture/refresh states and exits

| Requirement | Tests |
| --- | --- |
| Held initial capture, live Help status, deferred Home | `test_help_during_held_initial_capture_defers_home_and_updates_status` |
| Out-of-order refreshes, newest wins, deferred reveal | `test_out_of_order_refreshes_keep_help_open_and_newest_wins` |
| Why installation removed during covered refresh | `test_help_over_why_survives_removal_and_closes_why_on_reveal` |
| Diff installation removed during covered refresh | `test_help_over_diff_survives_removal_and_closes_diff_on_reveal` |
| Compare ID removed during covered refresh | `test_help_over_compare_result_survives_removed_agent_and_returns_to_picker` |
| Loading JSON never shows stale document | `test_help_over_loading_json_never_shows_a_stale_document`, `test_help_over_home_json_refresh_replaces_the_document_without_stale_data` |
| Refusal/retry/fault without prior data, literal details, exits 0/3 | `test_help_status_without_prior_data_is_literal_and_exit_is_correct[refused|retry|fault]` |
| Refusal/retry/fault with retained data, exits 0/3 | `test_help_status_with_prior_data_keeps_retained_wording_and_data[refused|retry|fault]` |
| Prompt cooperative quit during slow work | `test_quit_during_slow_work_through_help_is_prompt_and_cooperative` |

## A5 — Complete browsing flow and captured-data boundary

| Requirement | Tests |
| --- | --- |
| Home → Why → Diff → Agents → Compare picker/result → Doctor → Home selection, with Help and JSON | `test_complete_keyboard_browsing_flow_with_help_json_filters_and_refresh` |
| Filtering, empty input, unreadable captured root, literal markup-like text, successful refresh | same test |
| Edited/deleted fixture targets never leak into views before refresh | `test_views_stay_on_captured_data_until_refresh_after_fixture_edits` |
| Doctor Enter selects a captured Home row, never a file | `test_complete_keyboard_browsing_flow_with_help_json_filters_and_refresh` (Doctor step) and existing `tests/test_tui_doctor.py` jump tests |

## A6 — JSON equality and read-only preservation

| Requirement | Tests |
| --- | --- |
| All six JSON views equal the CLI serializer on the same inputs | `test_all_six_json_views_match_the_cli_serializer_on_same_inputs`; existing per-screen oracle tests in `tests/test_tui_json.py`, `tests/test_tui_agents.py`, `tests/test_tui_compare.py`, `tests/test_tui_doctor.py` |
| Existing snapshots/goldens unchanged | full suite (no snapshot or golden regenerated) |
| Recursive AST guard includes the new module | `tests/test_tui_read_only.py::test_shipped_tui_code_has_zero_read_only_violations`, `::test_actual_package_discovery_finds_all_tui_modules` |
| Before/after bytes, modes and symlink targets across Help, navigation, refresh, fault and quit | `tests/test_tui_read_only.py::test_u8_synthetic_target_preservation_across_help_navigation_fault_and_quit`; existing U6 preservation tests retained |

## A7 — Empty and error states

| Requirement | Tests |
| --- | --- |
| Initial capture pending versus successful empty catalog | `test_help_opens_during_initial_loading_and_no_session`, `test_empty_catalog_filter_hint_and_unreadable_root_note[size0|size1]` |
| Home filters hide every row, with clear instruction | `tests/test_tui_home.py::test_home_text_filter_focus_enter_escape_and_empty_states`; `test_empty_catalog_filter_hint_and_unreadable_root_note` keeps the empty-catalog distinction |
| No detected agents versus no registry definitions | `test_no_detected_agents_is_not_no_registry_definitions[size0|size1]`, `test_no_registry_definitions_and_compare_shortfall[size0|size1]` |
| Why/Diff missing, unreadable or no-difference answers stay readable | existing `tests/test_tui_why.py::test_missing_key_predispatch_zero_calls`, `tests/test_tui_diff.py::test_diff_shows_a_supplied_not_found_report_with_the_existing_explanation`, `::test_diff_lists_an_unreadable_copy_with_its_reason`, `::test_diff_distinguishes_identical_copies_from_a_missing_baseline`; new `test_diff_single_copy_no_difference_answer_stays_readable` |
| Compare fewer than two definitions, duplicate and removed choice | `test_no_registry_definitions_and_compare_shortfall`, `test_compare_duplicate_choice_is_rejected_inline_and_in_help`, `test_help_over_compare_result_survives_removed_agent_and_returns_to_picker` |
| Doctor empty versus info-only healthy report | `test_doctor_empty_versus_info_only_healthy_report[size0-empty|size0-info|size1-empty|size1-info]`; existing `tests/test_tui_doctor.py::test_duplicate_finding_identity_and_summary_distinguish_info_from_empty` |
| Captured unreadable roots | `test_empty_catalog_filter_hint_and_unreadable_root_note[size0|size1]`; existing `tests/test_tui_home.py::test_home_unreadable_root_note_is_shown` |
| Oversized refusal without retry guidance | `test_help_status_without_prior_data_is_literal_and_exit_is_correct[refused]`, `test_help_status_with_prior_data_keeps_retained_wording_and_data[refused]` |
| Snapshot changed/incomplete retry state without sticky failure | the `[retry]` cases above |
| Unexpected fault with retained data and sticky exit 3 | the `[fault]` cases above; `test_old_successes_and_errors_cannot_affect_newer_work_or_sticky_state` |

## A8 — Mutation evidence

12/12 planted defects caught, with passing control before, meaningful mutant
failure and passing restored control. See
[`mutations/summary.md`](mutations/summary.md) and
[`mutations/results.json`](mutations/results.json). Categories: duplicate Help,
covered-key leakage, lost Input focus, ignored Diff suspension, ignored Compare
suspension, stranded report after reveal, stale callback popping a newer screen,
stale JSON after refresh, fault hidden while Help is open, fault status reset
while Help is open, banned import and a write in the new module.

## A9 — Final gates

Commands, outputs, exit statuses, coverage and counts are retained in
[`gates.json`](gates.json) and the four `final-*.log` files in this directory.
The coverage gate is the unchanged 90% combined statement/branch threshold with
`tui/` measured.

## A10 — Evidence and limitations

- Frozen plan hash and commits: [`inputs.json`](inputs.json).
- Complete changed-file list: [`changed-files.txt`](changed-files.txt).
- Implementer report and honest limitations: [`implementation-report.md`](implementation-report.md).
- Self-review record and failed attempts: [`self-review.md`](self-review.md), [`failed-attempts.md`](failed-attempts.md).
- Local checks establish local technical readiness only. Coordinator verification,
  independent review, built-wheel qualification, hosted CI, human visual approval
  and U9/publishing remain separate.
