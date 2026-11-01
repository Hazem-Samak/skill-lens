# U5 final council — combined disposition and correction brief

Date: 30 October 2026. **Changes required; U5 is not accepted.** This is the single combined handoff requested by the owner after collecting both independent final reviews. The reviewers did not edit product/tests. No product commit or push.

## Council and integrity

| Reviewer requested by owner | Effective configured route evidence | Verdict |
| --- | --- | --- |
| MiniMax 3.1 F / max through MCode | Exact run `mvs_55bb9ef829b24b608cb8921275570d93`: `minimax`, `MiniMax-M3.1-Flash`, `thinkingLevel: max`, `anthropic-messages`; process exit 0, substantive report. | changes_required — one medium blocker |
| GLM 5.3 / max through Qoder | Exact session `53e040d7-34df-4fc1-8118-4ca1a526481d`: startup model `GLM-5.3`, runtime alias `gmodel`, `reasoning_effort=max`; built-in Plan requested; process exit 0, substantive report. | pass — no blockers, two suggestions |

The reports' original identity limitations are preserved; the coordinator obtained the exact-run configured receipts separately. Upstream serving identity is unverified. Advertised MiniMax/GLM families have no advertised overlap with the OpenAI coordinator or owner-identified DeepSeek implementer. This roster belongs to this U5 mission only.

Complete original reports: [MiniMax](minimax-report.md), [GLM](glm-report.md). Exact briefs, result receipts and configured identity/launch records are retained beside them. Both reviewed base `fb85ddb91ef518ed86b7af84ffb0e87ae69f4afd` plus its uncommitted U5 implementation, including the four new files. The complete scoped patch is `review.patch.gz`.

Before/after reviewer tree fingerprints are identical: `affd59ea93813acddac180051b545b625a6dbfbb50cc1ed45b7c5fa8758a4784`. All **2417** tracked/untracked manifest entries and git status were unchanged during the wave. The input manifest is `input-manifest.json.gz`; integrity receipts are in `execution.json`. The guard/Plan mode was instruction-based protection, not an OS sandbox claim.

## FR1 — Accepted blocker: restore Why focus idempotently after Diff

Source: MiniMax B1. Severity: medium. **Coordinator reproduced**, not merely inferred from source.

Locations:
- `skill_lens/tui/why.py:340–392`: lifecycle handlers, `suspend_detail`, `resume_detail`, `_restore_detail_focus`.
- `skill_lens/tui/app.py:256–276`: `close_diff` explicitly resumes the revealed Why after popping Diff.
- `tests/test_tui_diff.py` / `tests/test_tui_why.py`: appropriate behavioral regression seam.

Actual result of real Textual key navigation using isolated synthetic HOME:

| Terminal size | Focus before opening Diff | Focus after Esc back to Why | Original control still mounted |
| --- | --- | --- | --- |
| 100x30 | Candidate `CollapsibleTitle` | `Button#why-agent-claude` | Yes |
| 100x30 | `VerticalScroll#why-body` | `Button#why-agent-claude` | Yes |
| 60x24 | Candidate `CollapsibleTitle` | `Button#why-agent-claude` | Yes |
| 60x24 | `VerticalScroll#why-body` | `Button#why-agent-claude` | Yes |

One throwaway command exercised all four cases in 4.46 seconds and exited 1 on `Diff -> Why did not preserve the valid ordinary focus control`; every app quit normally with exit 0 after collecting its observed state. The probe used `SkillLensApp.run_test`, existing scenario/helper functions, actual Tab/d/Esc/q keys, and compared the actual focused widget object with the original mounted widget. No product or test source was modified.

Mechanism: `suspend_detail` saves `_detail_focus`. App-driven `close_diff` pops and explicitly calls `resume_detail`; Textual also posts `ScreenResume`, which calls the same method later. The first `_restore_detail_focus` clears `_detail_focus`. The second resume sees no remembered control and calls `_update_strip_focus`, replacing the restored focus with the selected agent button. Deferred focus operations make the later fallback win.

This violates frozen plan navigation line 51 (preserve Why focus when still valid) and lifecycle line 80 (resume effectively idempotent across app/Textual callbacks). GLM's statement that the topmost guard prevents double resume is contradicted by this observed sequence: both callbacks can execute while Why is topmost. Its passing verdict does not override the reproduced blocker.

### Required correction

- Make the **focus restoration**, not just report dispatch, idempotent across both real resume routes. Preserve the valid originating control after Why → Diff → Why, without letting a later redundant resume force focus to the agent strip.
- Keep a safe ordinary fallback when a remembered control is no longer mounted/visible/usable after refresh. Do not blindly retain a stale widget forever, skip necessary generation reconciliation, remove the resume re-request, or weaken topmost/token guards.
- Keep agent selection, expansion and ordinary scroll stable for an unchanged generation. Reconcile refreshed candidates normally instead of resurrecting stale widgets.
- Add discriminating tests **before** the fix: open Why, reach a candidate title or the ordinary body by real Tab navigation, press `d`, then Esc/Backspace, let normal lifecycle/deferred events settle, and assert focus is the same still-valid widget. Cover both 100x30 and 60x24 and repeated round trips. The current agent-button-only/default-focus paths do not catch this defect.
- Exercise actual push/pop plus app/lifecycle callbacks; do not call only one resume function directly or assert source text/call forwarding. Retain existing pending-Why, covered-refresh, cancellation/cache, JSON-mode focus and removal tests.
- Keep the fix local to the existing lifecycle/focus mechanisms; no generic navigation framework or controller changes.

## FR2 — Accepted small test suggestion: first-capture refusal in raw JSON

Source: GLM S1. **Non-blocking suggestion accepted for this correction batch**, within the already frozen no-fabricated-JSON/accurate-refusal contract. No new feature or state-summary redesign.

Add one bounded actual-screen regression in `tests/test_tui_json.py`: force the **initial** capture to be refused using a tiny positive capture budget against synthetic skills (or an existing controlled `SnapshotTooLarge` fixture). Wait for the actual refused state, not the helper that waits for a successful ready session. With no published snapshot, focus the Home table and enter `J` using keys. Require a meaningful refusal explanation, `JsonView.document is None`, no fabricated empty ScanReport, no incorrect loading explanation and no unexpected sticky internal fault. Quit should retain the normal expected-refusal exit behavior. Do not allocate a huge fixture or read real installed skills/settings. Do not pin incidental prose or compare a helper's constant with itself.

## Other suggestions — adjudicated, not additional correction work

| Source | Decision | Reason |
| --- | --- | --- |
| MiniMax S1: replace `id(report)` render keys | Not adopted | Reviewer found no reachable collision path. A speculative counter/cache redesign is not needed for this defect. |
| MiniMax S2: clear removal notice on `d` | Deferred, non-blocking | Cosmetic key inconsistency; the frozen contract does not require this behavior change. |
| MiniMax S3: remove unreachable screen quit methods | Deferred, non-blocking | No quit defect demonstrated; the bindings correctly use `app.quit`, and Why's method predates U5. Do not mix unrelated cleanup into the focus correction. |
| MiniMax S4: missing export inventory | Not adopted | The frozen plan/R6 explicitly excludes incidental export inventories. Do not restore the deleted test. |
| GLM S2: shared controller-state summary abstraction | Not adopted | No current semantic drift or defect demonstrated; a new abstraction is unnecessary for the bounded correction. |

All findings from both critics have been considered. This brief intentionally includes only the accepted blocker and the accepted bounded test improvement, rather than blindly implementing conflicting or speculative suggestions.

## Implementation and return rules

Use the same amended frozen plan at `69a477ba9054a21030d038ed98a62962a1862d88`. The owner-managed DeepSeek Harness correction route and U5-only self-check permission remain active. The implementer is owner-identified as River / DeepSeek 4.1 1017 Flash / max effort; runtime/upstream identity must not be invented.

Allowed edits: the existing Why lifecycle/focus implementation; app integration only if actually necessary; focused Diff/Why/JSON regression tests; factual allowed U5 documentation/implementation record. Do not rewrite original reviewer reports, council receipts, this disposition, the frozen plan or shared process rules. Product scope/exclusions and read-only target behavior remain unchanged. No controller/engine/model/serializer/registry/dependency/settings/coverage/snapshot/golden/release changes, delegation, reviewer launches, staging, commits or push. Preserve all unrelated work.

Author the focus regression, observe its failure at the specific focus assertion, fix the cause and observe it pass. Run affected suites and all four final gates, fixing in-scope failures before returning:

```bash
.venv/bin/pytest tests/test_tui_diff.py tests/test_tui_why.py tests/test_tui_json.py
.venv/bin/pytest --cov=skill_lens
.venv/bin/mypy
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Format only exact changed allowed Python paths. Retain the 90% combined coverage gate with branch measurement and existing snapshots/goldens. Keep logs outside the checkout and outside the synthetic skill HOME. Use bounded state/event observations rather than longer sleeps. Do not repeat the known PTY failure merely to confirm it; use the available real-screen headless path and report that visual limit. The coordinator will verify the correction and arrange fresh targeted follow-ups from **both** named critics on the affected focus/lifecycle/test scope; unchanged positive review/mutation scope may remain valid.

Return: FR1/FR2 dispositions, changed files, failing-before/passing-after focus evidence, first-capture-refusal evidence, exact final commands/exit statuses/test totals/coverage/log paths, runtime/visual limits, and remaining blockers/deviations. U5 remains unaccepted until the follow-up review gate and final coordinator acceptance are complete.
