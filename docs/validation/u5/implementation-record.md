# U5 implementation record — Diff and raw JSON views

> **This is not a verification record and not an acceptance record.** It records
> what an edit-only implementer session changed under the frozen plan
> [`docs/plans/2026-10-29-tui-u5-diff-json.md`](../../plans/2026-10-29-tui-u5-diff-json.md)
> at `af8c65836974aa17eaaec1e7d520a10d8ef63b80`, in the "One-round execution
> exception — 30 October 2026" arrangement. No test, coverage run, type check,
> linter, formatter, UI exercise, smoke check or mutation experiment was executed
> for this work. Independent review and the four repository gates are still
> outstanding, so U5 is **not accepted**.

## What was implemented

1. **Diff screen** (`skill_lens/tui/diff.py`, new). One read-only unified
   `DiffReport` per canonical installation key, reached with `d` from Home
   (focused, nonempty skill table) or from an ordinary Why screen. It shows the
   summary (`Copies:`, `Baseline:` with captured path/Variant or the
   no-baseline form), copy headings in report order, per-file change labels,
   the model's unified hunks, per-copy truncation notices, the report-wide
   truncated-character notice and the existing not-found explanation. Binary
   payloads and hunkless text bodies are never printed; only the existing
   notices are shown. The screen owns at most one `ViewRequest` for `(key,)` and
   follows the U4 cache → owned-token → dispatch sequence.
2. **Raw JSON mode** (`skill_lens/tui/json_view.py`, new). A focusable,
   read-only `VerticalScroll` that displays a supplied document verbatim with
   markup disabled and no editor/copy/export action. `J` toggles it on Home
   (skill table focused), ordinary Why and Diff. The backing document is
   `models.dumps(report.to_dict())`, unmodified, so document plus one final line
   feed equals the CLI `_emit_json` output for the same report. When no honest
   payload exists (no captured session, refused/failed capture, pending report,
   no eligible agent) the view shows an explanation and its backing document is
   `None`, so a placeholder can never be mistaken for report data.
3. **Lifecycle wiring** (`tui/app.py`, `tui/home.py`, `tui/why.py`).
   `open_diff`/`close_diff` push at most one Diff over its origin, suspend the
   origin first and reconcile it on return. Why gained
   `on_screen_suspend`/`on_screen_resume` plus explicit
   `suspend_detail`/`resume_detail`; resume reconciles the current generation and
   re-requests through Why's existing cache/owned-token guard, so a report
   cancelled while covered is re-requested instead of leaving a spinner. A
   removed installation pops Diff first and lets the revealed screen report the
   removal (Home through its existing notice receiver, Why through its own
   detection).
4. **Shared plain notices** (`presentation/text.py`, `presentation/__init__.py`,
   `render.py`). The renderer-only copy/file/truncation sentences are now small
   pure helpers consumed by both `render.py` and the TUI: baseline-reference,
   unreadable-copy reason, identical vs not-compared body, binary suppression,
   hunkless text, per-copy changed-line/character-only truncation and the
   report-wide omitted-character notice, plus the `Copies:`/`Baseline:`/`Note:`
   labels, the binary marker and the three baseline-summary forms.
   `render.py` was rewired to consume them; the intent is byte-identical CLI
   output, which the existing snapshots must confirm without regeneration.

## Files

| File | Change |
| --- | --- |
| `skill_lens/tui/diff.py` | New Diff screen, host protocol, request ownership. |
| `skill_lens/tui/json_view.py` | New reusable read-only JSON widget and the session-state explanation helper. |
| `skill_lens/tui/app.py` | `open_diff`/`close_diff`, Diff routing in report notifications and `_update_ui`. |
| `skill_lens/tui/home.py` | `d`, `J`, raw-JSON mode, JSON-mode action guards, focus/state preservation, footer hint. |
| `skill_lens/tui/why.py` | `d`, `J`, raw-JSON mode, suspend/resume lifecycle, JSON-mode guards. |
| `skill_lens/tui/__init__.py` | Export `DiffScreen`, `JsonView`, `session_explanation`. |
| `skill_lens/presentation/text.py`, `presentation/__init__.py` | New pure copy/file/truncation notice helpers and labels. |
| `skill_lens/render.py` | Consumes the shared helpers; no intended visible change. |
| `tests/test_tui_diff.py` | New Diff navigation/fidelity/ownership/refresh tests. |
| `tests/test_tui_json.py` | New raw-JSON mapping/byte-equality/mode tests. |
| `tests/test_presentation.py` | Focused additions for the extracted notices; the public-export enumeration was extended. |
| `FULL_SCREEN_TUI.md`, `DEVELOPMENT.md`, `README.md`, `CHANGELOG.md` | Factual status/control updates stating U5 is implemented but unverified. |
| `docs/validation/u5/implementation-record.md` | This record. |

## Checks not run (edit-only restriction)

Not executed by this session, and therefore unproven:

- `pytest --cov=skill_lens`, `mypy`, `ruff check .`, `ruff format --check .`;
- any real Textual Pilot run, CLI TUI launch, snapshot/golden comparison or
  regeneration;
- the mutation list in the frozen plan's acceptance section;
- independent review of the final scoped change.

## Known limitations of this record

- The tests are authored against the Textual 8.2.8 API by reading its source;
  they have not been executed.
- Two branches cannot be produced by the live engine and are exercised with a
  supplied report: a not-found `DiffReport` and a non-binary file with no hunks
  (plus a malformed binary file that carries hunks). This matches the frozen
  plan's instruction to test those branches without inventing a live-read
  fallback.
- `DiffReport` copy paths are displayed through `snapshot_path`; the JSON
  documents keep the captured absolute paths exactly as the CLI emits them.

---

## Correction round 1 — 30 October 2026

> Appended after coordinator inspection round 1. The section above is retained
> unchanged as the historical edit-only session record. This appendix reports the
> implementer's own corrections and self-checks; it is **not** coordinator
> verification, **not** mutation verification and **not** independent review, and
> U5 remains unaccepted.

The owner authorized this round's implementer to run focused tests, all four
project gates, scoped formatting and isolated UI checks. Product scope, allowed
paths and acceptance requirements are unchanged.

### Finding dispositions

| Finding | Disposition |
| --- | --- |
| R1 early-capture Home reconciliation | Fixed in product code: `HomeScreen.on_mount` reconciles under a `_mounting` flag because `is_mounted` only flips after the mount handler returns (same convention `WhyScreen` already used). New regression `test_early_capture_is_reconciled_by_the_mount_itself` suppresses the deferred host update entirely and fails without the fix. The original early-capture test now waits on the populated table rather than a fixed pause. |
| R2 incorrect fixtures | `test_character_budget_truncation_never_claims_zero_omitted_lines` now emits a body that exceeds the 20,000-character report budget while keeping changed lines far below 400, so the cut lands on trailing context and `omitted_lines` stays 0. `test_diff_content_is_reachable_at_both_terminal_sizes` puts the marker in the non-baseline copy so it is the final retained `+` line, and asserts the model's last line is visible at 100x30 and 60x24. |
| R3 JSON scroll reset | `JsonView.show_document`/`show_explanation` are now idempotent for identical text, and a changed document resets the pane even while hidden. Three real-screen tests (Home, Why, Diff) scroll to the end, trigger an unchanged `_update_ui()`/redraw, and assert the offset is preserved; they also assert a genuine document transition starts at the top. |
| R4 long metadata overlap | The Diff title, status and error details moved inside the report's own `VerticalScroll`, and the collapsed body is no longer a Tab stop in JSON mode. New `test_long_metadata_never_hides_the_report_or_the_footer` builds a valid skill with a 240-character name and a filesystem-length-limited deep project path, asserts the title alone wraps past the 60x24 viewport, and requires the body region to stay clear of the footer with report and metadata reachable at both sizes; it fails on the previous layout. |
| R5 missing acceptance cases | Added: frozen first Diff/JSON visit with scoped reader/probe bans and an explicit-refresh transition; Tab/Shift+Tab plus scroll/J/Esc/Backspace in all three JSON owners; older-capture-completes-last with Diff in JSON mode; quit while a Diff report worker is blocked; cache-hit takeover that leaves another view's request running; extended synthetic target-preservation lifecycle through Home JSON, Diff, Diff JSON, Why and Why JSON. |
| R6 incidental assertions | The `__all__` export-inventory test was removed, and the new helper tests plus the Diff screen tests no longer compare results to exported prose constants. They assert distinctions and consumer-visible meaning instead (identity vs not-compared, unreadable reason, payload suppression, omitted totals, baseline forms). |
| R7 coverage and formatting | Scoped `ruff format` applied to the changed files only. Final gates on the final tree: 1180 passed, 1 skipped, 90.10% combined coverage with branch measurement; mypy clean; `ruff check .` and `ruff format --check .` clean. |

### Implementer self-check evidence (not acceptance)

Commands, logs and exit statuses are recorded in the round-1 correction report
the implementer returned to the coordinator. Logs were kept outside the
repository and outside the synthetic skill HOME. No snapshot or golden was
regenerated, no coverage setting changed, and no test assertion was weakened to
reach the gate.

---

## Correction round 2 — 30 October 2026

> Appended after coordinator inspection round 2. Earlier sections are retained
> unchanged as historical session records. This appendix reports acceptance-test
> corrections only; it is **not** coordinator mutation verification, **not**
> independent review and **not** acceptance.

Round 2 found no new product defect: the corrected implementation already behaves
correctly, but required mutation checks survived because the tests did not pin
the protected behaviour. **No product code changed in this round**; the guards
under test are untouched.

| Finding | Disposition |
| --- | --- |
| C1 foreign Diff ownership | New `test_old_diff_screen_cleanup_cannot_cancel_a_newer_owner` creates two real requests: the open Diff screen still holds its superseded token A while the adapter's newer token B is the controller's active Diff request. It asserts full token identity and both cancellation events, then closes the old screen (its real `close_diff` cleanup) and requires B's token, event and completed report to survive, be accepted into the cache and be reused on reopen without a third worker. In a disposable copy, replacing the `active == owned` equality with `active is not None` fails this test on the ownership assertion. |
| C2 covered Why suspension | New `test_covered_why_is_suspended_and_its_stale_result_rejected` starts Why request A behind a gate, covers it with Diff, and asserts *while covered* that Why is suspended, its owned token is dropped, A's event is set and no replacement Why work started. A's release is observed through a recorded `accept_view_result` call, proving the obsolete outcome reached the controller and was rejected without being cached. Returning then obtains the report through the normal deduplicated path (exactly one new request). Making `suspend_detail()` a no-op fails the covered-state assertion, not a timeout. |
| C3 traversal proof | `test_synthetic_target_preservation_across_lifecycle` now waits for a populated Home table, the Diff screen plus its accepted report, and the actual JSON documents of Home, Diff and Why, asserting mode/focus/return transitions at each step, while keeping the before/after byte, mode and symlink-target comparison. Making `action_open_diff` a no-op now fails the traversal at "accepted Diff report". |
| C4 exact frozen input and completion order | The frozen-visit test now seeds a real `.agents/skills/asset` shortcut **before** the independent oracle and capture (asserting it is part of the captured input via the scan's entrypoint count), retargets that same shortcut to a different existing synthetic target after publication, and requires the frozen Diff/JSON/scan documents to keep the captured identity and content while an explicit refresh publishes the third copy. Both the older-capture-completes-last test and the abandoned-owner test now wait for the *observed* outcome (recorded `accept_capture` / `accept_view_result` call) before asserting rejection; the fixed `0.2 s`/`0.3 s` sleeps are gone. |

### Implementer spot-checks (not the coordinator's campaign)

Three single-mutant checks were run in disposable copies outside the checkout
(never in the working tree) to confirm the new tests fail for their intended
assertions: `M05_cancel_foreign_owner`, `M06_hidden_why_continues`, and the
no-op `action_open_diff` traversal mutant. Each failed on its intended
assertion; the copies were deleted. The coordinator retains the authoritative
rechecks.

---

## Independent-review correction round 1 (FR1, FR2) — 31 October 2026

> Appended after the combined final-review disposition
> (`docs/validation/u5/final-review/round1/disposition.md`). Earlier sections are
> retained unchanged. This appendix reports the implementer's corrections and
> self-checks only: it is **not** the follow-up review gate and **not** acceptance.

Only the two accepted items were implemented; every suggestion the disposition
deferred or rejected was left untouched.

| Item | Disposition |
| --- | --- |
| FR1 Why focus after Diff | Fixed locally in `skill_lens/tui/why.py`. `_restore_detail_focus` now keeps the remembered control while it is still a valid focus target, so the second resume route (`close_diff`'s explicit resume and Textual's `ScreenResume`) re-focuses the same widget instead of falling back to the agent strip. The reference is dropped when it is no longer usable, and `_rebuild_from_snapshot` clears it because a new generation recreates the candidate widgets. No controller, navigation or ownership change; the resume re-request and token guards are untouched. |
| FR2 first-capture refusal in Home JSON | New bounded regression in `tests/test_tui_json.py` (`test_first_capture_refusal_is_an_honest_home_json_explanation`): a tiny positive capture budget refuses the first capture of synthetic skills; the test waits for the real `refused` state, focuses the Home table and presses `J`, then requires `JsonView.document is None`, a refusal explanation that is not a loading state and not a fabricated `ScanReport`, `failed is False`, and a normal `0` quit. |

### Failing-before / passing-after evidence (FR1)

`test_returning_from_diff_restores_the_originating_why_focus` is parametrized
over both originating controls (a candidate `CollapsibleTitle` and
`#why-body`) × both terminal sizes (100×30, 60×24) × both return keys
(Esc, Backspace), and performs two real push/pop round trips per case. On the
uncorrected tree **all 8 cases failed at the focus assertion**, each reporting
that round trip 1 replaced the originating control with
`Button 'why-agent-claude'`; after the fix all 8 pass, together with a companion
test that a control rebuilt by a covered refresh is dropped and a valid
ordinary control receives focus instead.

### Follow-up gate

The coordinator's correction verification and the fresh targeted follow-ups from
both named reviewers remain pending. U5 is not accepted.

## Coordinator closure — 1 November 2026

Both fresh targeted final-review follow-ups passed with no blockers. FR1/FR2
are resolved; actual-terminal focus and positive-scroll preservation were
verified by the coordinator. U5 is locally technically accepted in development;
see [acceptance](acceptance.md) and [the complete follow-up records](final-review/round2/).
This supersedes the historical pending status above, not the original session
reports. The U5-only GUI/self-check exception is closed; shared process rules
and future loops are unchanged. No next phase, push or release is authorized.
