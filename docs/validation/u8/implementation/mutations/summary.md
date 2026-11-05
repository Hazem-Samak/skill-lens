# U8 mutation campaign

Command:

```bash
.venv/bin/python docs/validation/u8/implementation/mutations/run_mutations.py
```

Each case ran in a fresh disposable copy outside the reviewed checkout. For each case:

1. the targeted test passed on the unmutated copy (control-before);
2. the planted defect made the same test fail with the expected assertion (mutant);
3. restoring the original file made it pass again (control-after).

The reviewed checkout was never edited; the temporary copy was deleted afterwards.
The campaign was re-run on the final test tree after the coverage additions.

Result: **12/12 caught**, no survivors.

| # | Category | Test | control-before | mutant | control-after | Result |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Duplicate Help stacking | `tests/test_tui_help.py::test_help_does_not_stack_and_stale_instance_cannot_close_a_newer_help` | 0 | 1 | 0 | caught |
| 2 | Covered-key leakage | `tests/test_tui_help.py::test_hidden_screen_actions_cannot_leak_through_help` | 0 | 1 | 0 | caught |
| 3 | Lost Input focus | `tests/test_tui_help.py::test_home_filter_typing_is_literal_and_f1_preserves_text_and_cursor` | 0 | 1 | 0 | caught |
| 4 | Ignored Diff suspension | `tests/test_tui_help.py::test_diff_job_is_suspended_and_restarted_once` | 0 | 1 | 0 | caught |
| 5 | Ignored Compare suspension | `tests/test_tui_help.py::test_compare_job_is_suspended_and_restarted_once` | 0 | 1 | 0 | caught |
| 6 | Stranded report after reveal | `tests/test_tui_help.py::test_diff_job_is_suspended_and_restarted_once` | 0 | 1 | 0 | caught |
| 7 | Stale callback popping a newer screen | `tests/test_tui_help.py::test_help_does_not_stack_and_stale_instance_cannot_close_a_newer_help` | 0 | 1 | 0 | caught |
| 8 | Stale JSON after refresh | `tests/test_tui_help.py::test_help_over_home_json_refresh_replaces_the_document_without_stale_data` | 0 | 1 | 0 | caught |
| 9 | Fault state hidden while Help is open | `tests/test_tui_help.py::test_help_status_with_prior_data_keeps_retained_wording_and_data[fault]` | 0 | 1 | 0 | caught |
| 10 | Fault state reset while Help is open | `tests/test_tui_help.py::test_help_status_with_prior_data_keeps_retained_wording_and_data[fault]` | 0 | 1 | 0 | caught |
| 11 | Banned import in the new Help module | `tests/test_tui_read_only.py::test_shipped_tui_code_has_zero_read_only_violations` | 0 | 1 | 0 | caught |
| 12 | Write in the new Help module | `tests/test_tui_read_only.py::test_shipped_tui_code_has_zero_read_only_violations` | 0 | 1 | 0 | caught |

## Evidence files

Each case retains `NN-case.control-before.log`, `NN-case.mutant.log` and
`NN-case.control-after.log` in this directory. `results.json` records the exact
mutation text, commands, exit statuses, expected failure text and timings.
`run.log` is the final campaign's console transcript.

## Notes

- The mutant run must exit non-zero, contain the expected meaningful assertion,
  and must not be a syntax, import or collection error. The runner checks all
  three conditions.
- The two Help-fault cases prove different defects: hiding the accepted fault
  section, and leaving the live session section stale because `_update_ui` no
  longer refreshes it.
- The read-only cases plant both a banned `subprocess` import and a
  `Path.write_text` call in the new Help module; the existing recursive AST
  guard detects each.
- These are local mutation results from one implementer. They do not replace
  independent review or acceptance.
