# U8 implementer report

Date: 5 November 2026.
Repository: `Skill Lens` at HEAD `a9d67b808ce235a543e63fba40b478da2a96c3e3`
(unchanged; no commit or push).
Frozen plan: `docs/plans/2026-11-04-tui-u8-polish-help-docs.md`,
operative commit `b59478404a9d20d2670fb12a731c703f53eee798`, SHA-256
`01f6f250be358ed2168170e06513c1908ef616208a204d8f50f9dfa03f0c26de`.

EFFECTIVE_MODEL:       provider/model not exposed by this runtime; requested: not named in the implementer brief; configured: not readable; provider-confirmed: unverified. Settings/reasoning effort: not exposed. Native permission/interaction modes: n/a (non-T3 session); the harness reported approval policy "never" (user-changed) and full file access. No identity or model claim is fabricated.
OUTCOME:               succeeded
FILES_CHANGED:         skill_lens/tui/help.py (new); skill_lens/tui/app.py; skill_lens/tui/home.py; skill_lens/tui/why.py; skill_lens/tui/diff.py; skill_lens/tui/agents.py; skill_lens/tui/compare.py; skill_lens/tui/doctor.py; tests/test_tui_help.py (new); tests/test_tui_home.py; tests/test_tui_read_only.py; README.md; DEVELOPMENT.md; CHANGELOG.md; SKILL_LENS_SPECIFICATION.md; FULL_SCREEN_TUI.md; docs/validation/u8/implementation/** (evidence only)
CHECKS:                pytest=1338 passed, 1 skipped, 90.10% combined coverage (exit 0) mypy=pass, 46 source files ruff-check=pass ruff-format=pass, 422 files
TESTS_ADDED:           tests/test_tui_help.py — 99 tests covering A1–A7 and the A8 controls: Help over six screens, all JSON modes, Compare picker/result, loading/no-session; input typing/cursor/F1; every dismiss route and exact focus/scroll restoration; hidden keys; stacking/stale instances; delayed Home Why/Why detail/Diff/Compare ownership, cancellation, cache reuse and one replacement; old outcomes; held capture; out-of-order refresh; removals; loading JSON; refusal/retry/fault with and without retained data; exits 0/3; slow-work quit; complete browsing flow; no live fallback; all six CLI JSON oracles; empty/error distinctions at 100×30 and 60×24; teardown/stale-callback safety; scroll restoration. tests/test_tui_read_only.py — one new lifecycle preservation test plus help.py discovery. tests/test_tui_home.py — updated the exact no-match filter sentence.
DEVIATIONS_FROM_PLAN:  none
BLOCKED_ON:            none

## Acceptance status

- **A1 — complete.** `test_help_opens_and_dismisses_from_each_ordinary_screen`,
  `test_help_opens_over_raw_json_modes`,
  `test_help_body_and_close_are_reachable_at_both_sizes`,
  `test_help_opens_during_initial_loading_and_no_session`,
  `test_help_no_session_over_agents_and_compare_picker`,
  `test_every_screen_and_help_remains_usable_at_both_sizes`.
- **A2 — complete.** `test_home_filter_typing_is_literal_and_f1_preserves_text_and_cursor`,
  `test_plain_question_mark_opens_help_only_outside_the_filter_input`,
  `test_every_dismiss_route_restores_exact_input_focus_text_and_cursor`,
  `test_every_dismiss_route_restores_table_focus_and_preview_scroll`,
  `test_hidden_screen_actions_cannot_leak_through_help`,
  `test_help_does_not_stack_and_stale_instance_cannot_close_a_newer_help`,
  `test_f1_toggles_help_while_typing_and_does_not_lose_priority`,
  `test_tab_and_shift_tab_stay_inside_help_and_enter_on_body_does_nothing`,
  `test_help_restores_raw_json_scroll_on_every_screen`,
  `test_help_restores_ordinary_detail_scroll_on_supported_screens`.
- **A3 — complete.** `test_home_why_job_is_suspended_and_restarted_once`,
  `test_why_detail_job_is_suspended_and_restarted_once`,
  `test_diff_job_is_suspended_and_restarted_once`,
  `test_compare_job_is_suspended_and_restarted_once`,
  `test_help_cancels_only_the_covered_screens_own_token`,
  `test_old_successes_and_errors_cannot_affect_newer_work_or_sticky_state`.
- **A4 — complete.** `test_help_during_held_initial_capture_defers_home_and_updates_status`,
  `test_out_of_order_refreshes_keep_help_open_and_newest_wins`,
  `test_help_over_why_survives_removal_and_closes_why_on_reveal`,
  `test_help_over_diff_survives_removal_and_closes_diff_on_reveal`,
  `test_help_over_compare_result_survives_removed_agent_and_returns_to_picker`,
  `test_help_over_loading_json_never_shows_a_stale_document`,
  `test_help_over_home_json_refresh_replaces_the_document_without_stale_data`,
  `test_help_status_without_prior_data_is_literal_and_exit_is_correct`,
  `test_help_status_with_prior_data_keeps_retained_wording_and_data`,
  `test_quit_during_slow_work_through_help_is_prompt_and_cooperative`.
- **A5 — complete.** `test_complete_keyboard_browsing_flow_with_help_json_filters_and_refresh`,
  `test_views_stay_on_captured_data_until_refresh_after_fixture_edits`.
- **A6 — complete.** `test_all_six_json_views_match_the_cli_serializer_on_same_inputs`;
  existing per-screen CLI oracle tests retained; no snapshot/golden changed;
  `tests/test_tui_read_only.py::test_u8_synthetic_target_preservation_across_help_navigation_fault_and_quit`.
- **A7 — complete.** `test_empty_catalog_filter_hint_and_unreadable_root_note`,
  `test_no_detected_agents_is_not_no_registry_definitions`,
  `test_no_registry_definitions_and_compare_shortfall`,
  `test_compare_duplicate_choice_is_rejected_inline_and_in_help`,
  `test_doctor_empty_versus_info_only_healthy_report`,
  `test_diff_single_copy_no_difference_answer_stays_readable`; existing Why/Diff
  missing/unreadable/no-difference tests retained. Full mapping in
  [`acceptance-matrix.md`](acceptance-matrix.md).
- **A8 — complete.** 12/12 mutations caught with control-before, meaningful
  failure and restored control; see [`mutations/summary.md`](mutations/summary.md).
- **A9 — complete.** All four gates passed on the final tree:
  `.venv/bin/pytest --cov=skill_lens` (1338 passed, 1 skipped, 90.10%, exit 0),
  `.venv/bin/mypy` (46 files), `.venv/bin/ruff check .`, and
  `.venv/bin/ruff format --check .`. Logs and hashes in [`gates.json`](gates.json).
- **A10 — complete.** Frozen hash, commits, source/test/config hashes,
  changed-file list, diff review, mutation evidence, failed attempts,
  limitations and the self-review are all in this directory.

## Mutation results

12/12 caught, no survivors: duplicate Help stacking; covered-key leakage; lost
input focus; ignored Diff suspension; ignored Compare suspension; stranded
report after reveal; stale callback popping a newer screen; stale JSON after
refresh; fault hidden while Help is open; fault status reset while Help is open;
banned import in the new module; write in the new module. Each case retains the
exact mutation text, commands, exit statuses and logs.

## Coverage and counts

Final full run: **1,338 passed, 1 skipped, 90.10%** combined statement/branch
coverage with `tui/` measured and the unchanged 90% threshold. The skip is the
pre-existing case-sensitive-filesystem guard. New Help module coverage: 99%.
Final targeted Help suite: **99 passed**.

## Remaining limitations

- Headless local checks only: macOS, Python 3.11.16, Textual 8.2.8. No human
  visual approval, real-terminal manual pass, Linux/Python 3.12–3.14 lane,
  hosted CI run, built-wheel smoke or publishing check.
- Quit is cooperative; a blocked read or running thread is not forcibly stopped.
- Help's static body reflects the focus/mode captured at open; the live session
  section updates while open. Covered screens are not reconciled until reveal.
- Home's unreadable-root note is auto-height literal text; very long values wrap
  and use vertical space rather than being truncated.
- Coverage margin is 0.10 points above the gate; remaining uncovered lines are
  mostly existing defensive branches in the six screens.
- Local mutation evidence is not exhaustive and does not replace independent
  review.

## Confirmations

No commit, push, staging, delegation, subagent launch, release or publishing
occurred. No test used a real `$HOME`; all fixtures are synthetic `tmp_path`
homes protected by `tests/conftest.py`. No snapshot or golden was regenerated.
No controller, core engine, model, registry, CLI, Rich renderer, dependency,
lockfile, packaging, CI, coverage-configuration or out-of-scope file was
changed. `.path`, `.qoder/` and `docs/validation/2026-10-25/` are preserved;
their hashes are in [`final-integrity.json`](final-integrity.json).
