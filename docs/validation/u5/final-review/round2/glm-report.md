# U5 Round-2 Targeted Follow-Up — Fresh Critic Report

## EFFECTIVE_MODEL

**Requested/configured:** GLM-5.3, max effort, through Qoder (built-in Plan agent, read-only critic mode) — the owner-selected route for this mission, same advertised GLM family as owner-approved round 1. This session explicitly requests max effort; I have not confused it with the historical planning `xhigh`.

**Modes:** one read-only review turn. No delegation, no workers, no test/gate/runtime execution, no repository writes, no snapshot/golden regeneration. Byte-level patch-reconstruction checks ran only in a throwaway directory outside the checkout (deleted afterward).

**Evidence and upstream limits:** the identity above is what the mission configuration shows me; I cannot verify upstream serving identity from inside the session and stopped identity research there. No advertised overlap with the OpenAI coordinator or the owner-identified DeepSeek implementer. Runtime receipts for the exact run are the coordinator's separate responsibility.

## VERDICT

**pass** — FR1 and FR2 are resolved; no concrete newly introduced in-scope blocker found.

Independent verification performed (source-level, no execution):
- **Byte-level correction integrity:** I reconstructed the first-final bytes of all three changed files myself — HEAD `fb85ddb` + the round-1 `review.patch.gz` U5 diff + the supplied `correction.patch` reproduces the current `skill_lens/tui/why.py`, `tests/test_tui_diff.py` and `tests/test_tui_json.py` **byte-identically** (SHA-256 equal). The correction is exactly the two described `why.py` hunks plus the two appended tests plus one import; nothing else changed in these files. `app.py`, `json_view.py` and all other product files match the supplied current-tree manifest (`cf1584f3…`, 2428 paths) and are unchanged since the full council.
- **FR1 mechanism:** `close_diff` (app.py:274–276) still explicitly calls `resume_detail()` after `pop_screen()`, and `on_screen_resume` (why.py:344–346) still delivers the Textual `ScreenResume`; both run while Why is topmost, so the topmost guard does not dedupe them (confirming the coordinator's reproduction and contradicting round-1 GLM's "no double resume" claim). The fixed `_restore_detail_focus` (why.py:386–402) re-focuses the remembered widget on *both* calls while `can_focus/is_mounted/display` hold, making the restore idempotent; the reference is dropped only when invalid, and `_rebuild_from_snapshot` (why.py:449–451) clears it on generation replacement, so a rebuilt candidate can never be resurrected. Stale-risk corners check out: covered agent/JSON/`d` actions are all `_suspended`-guarded (why.py:956–1009), so no remembered control can become semantically wrong while covered except via generation rebuild, which clears it; `suspend_detail` re-saves on every suspend, so the memory never outlives the user's own navigation; the removal path returns from `sync_from_controller` before any restore.
- **No collateral damage:** the resume re-request, cache/dedup guard, `_cancel_owned_token` ownership equality guard, `sync_from_controller` generation reconciliation and `_update_strip_focus` fallback are untouched; expansion is preserved by the unchanged `_refresh_candidates` context early-return.
- **FR1 tests:** 8 rows (candidate-title/body × 100×30/60×24 × Esc/Backspace), two real `d`/back-key push/pop trips per row, real Tab navigation to the originating widget, and the discriminating assertion is actual focus identity (`app.focused is target`, with `target.is_mounted and target.display`). Agent, expansion, scroll, worker count (`snapshot_why` call count), `_owned_request is None` and exit 0 are retained-state assertions. The `resumes >= 2*trip` wait proves both real resume routes executed before the behavioral assertion — a lifecycle-ordering observation that complements, not replaces, the focus assertion. The covered-refresh companion verifies stale-drop (`_detail_focus is None`, `focused is not stale`, valid ordinary target) on a real generation change while Diff covers. Before/after: 8/8 rows failed at the originating-focus assertion on the uncorrected tree (button `why-agent-claude` reported), 8/8 pass after; the coordinator's independent real-key smoke on the corrected tree preserves focus in all four size/origin cases (exit 0).
- **FR2:** `max_snapshot_bytes` is a pre-existing `SkillLensApp` parameter (app.py:176–186) — no product semantics were added. With budget 1, `capture_session` raises `SnapshotTooLarge` pre-flight, `accept_capture_error` sets `refusal_message` without `failed`; the test waits for the real `refused` controller state, focuses the Home table, presses real `J`, and observes the actual screen (`JsonView.document is None`, rendered text present, not "Scanning", not a fabricated `"skills"` ScanReport, not JSON-shaped, contains the actual refusal message, same refusal on `#status-text`, `failed is False`, normal exit 0). The assertions check consumer-visible meaning, not pinned prose. Synthetic `mock_home` only.

## BLOCKERS

None.

## SUGGESTIONS

1. (Non-blocking, FR1 test only) In the candidate rows, the test presses `down` intending a non-zero body scroll to preserve, but never asserts `scroll_before > 0`; at 100×30 the two-candidate scenario may fit, leaving the scroll-preservation equality vacuously true in that row. A one-line precondition or a direct body scroll would make the guarantee non-trivial in all rows. Correctness is unaffected either way.

## FILES_AT_RISK

- `skill_lens/tui/why.py` — `_restore_detail_focus` / `_rebuild_from_snapshot`; retained-reference semantics matter to any future reader of `_detail_focus`.
- `skill_lens/tui/app.py` — `close_diff`'s explicit resume (unchanged consumer of the fixed path).
- `tests/test_tui_diff.py`, `tests/test_tui_json.py` — the new regressions; existing Why/JSON focus and covered-refresh suites are the neighboring guards (all green per supplied gate evidence).

## CONCEDED

- **FR1 resolved**, **FR2 resolved** as detailed above; both stay within the frozen plan's navigation line ("preserves … focus when still valid; after refresh reconcile … rather than resurrecting old candidates"), lifecycle line ("resume must be effectively idempotent across Textual lifecycle/app callbacks, without rebuilding unchanged expansion/focus state") and JSON clause ("never fabricate a scan report or label a refusal/fault as loading").
- **Prior concerns ruled out:** GLM round-1's "topmost guard prevents double resume" is contradicted by source and the coordinator's four-case reproduction — the correction addresses the real mechanism. MiniMax S1–S4 and GLM S2 were adjudicated out of this correction in the disposition and remain untouched, as required; I did not re-audit them. The unchanged positive full-review and mutation scope (coordinator-verification.md, mutations/round1-2.json) still applies to the untouched bytes.
- **Checks not run by me:** pytest/mypy/ruff gates, the mutation campaign, the TUI at runtime, and real-terminal smoke — per mission boundaries I relied on the supplied coordinator-inspected evidence (1192 passed / 1 skip, 90.15% branch coverage, mypy clean in 41 files, ruff clean; 8/8 before-fix focus failures and 8/8 after-fix passes; 4/4 coordinator real-key smoke preserved, exit 0). Evidence limits: the original full before-fix log was lost with OS temporary files — its inspected 8/8 result survives only as the recovered summary in `correction-evidence.json` and the implementer appendix; no physical-terminal or human visual approval is claimed for the latest headless checks, and source evidence is not proof of upstream model identity.
- No coordinator product/test edits were found; unrelated native-asyncio/2026-10-25 work and `.path` are preserved in the manifest.
