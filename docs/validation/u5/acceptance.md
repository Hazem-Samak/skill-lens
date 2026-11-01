# U5 — local technical acceptance

Date: 1 November 2026. **Accepted in development.** Home and Why can open a read-only unified Diff, and Home, Why and Diff can show their exact canonical JSON. Browsing uses the published capture; only explicit refresh reads a new session. U6–U9, human visual approval, hosted CI for this change and 0.2 publication are not claimed or authorized by this receipt.

## Contract and authority

- Frozen plan: `docs/plans/2026-10-29-tui-u5-diff-json.md`, operative reference `69a477ba9054a21030d038ed98a62962a1862d88`; reference-only/implementation base `fb85ddb91ef518ed86b7af84ffb0e87ae69f4afd`.
- Coordinator: the owner-retained OMP OpenAI Codex / GPT-6.1 Sol session and existing effort; numeric effort is not exposed. No coordinator product/test edits.
- Implementer: owner-identified River / DeepSeek 4.1 1017 Flash / max effort in the DeepSeek Harness desktop GUI. Runtime/upstream identity is unverified.
- Final critics: owner-selected MiniMax M3.1 Flash / max through MCode and GLM-5.3 / max through Qoder Plan. Exact-run configured receipts match; upstream serving identity is unverified. Advertised families do not overlap the coordinator or implementer families; this is the owner-approved roster, not a future default.
- The manual GUI implementation and implementer self-check permissions were **U5-only**. This round is now closed; future loops use the unchanged shared process rules and a newly selected roster. No next phase or push is authorized.

## Independent review and corrections

The [first full council disposition](final-review/round1/disposition.md) preserved both original reports and combined all accepted corrections into one DeepSeek handoff. MiniMax's focus blocker was reproduced; GLM's original passing claim about double resume did not override observed behavior.

- **FR1 resolved:** Why keeps the valid originating focus reference across both the app's explicit resume and Textual's `ScreenResume`. A generation rebuild clears it, retaining safe fallback instead of resurrecting a stale candidate. Request ownership, generation reconciliation and resume re-request remain unchanged.
- **FR2 resolved:** the new actual-screen regression forces an initial capture refusal with a tiny positive budget and observes meaningful Home JSON explanation, no fabricated document, no sticky internal fault and normal quit.
- The implementer's eight parameter rows failed at the focus assertion before the fix and passed afterward. The coordinator's independent original four-case smoke also changed from failing to passing. The full original red log was lost with OS temporary files; its inspected result survives in the implementation appendix and recovered evidence. It is not represented as a retained full log.

| Fresh targeted reviewer | Exact configured receipt | Verdict |
| --- | --- | --- |
| MCode MiniMax | Session `mvs_0e361de053834f78bd4988a5ad4cd1fc`; `minimax`, `MiniMax-M3.1-Flash`, `thinkingLevel=max`, `anthropic-messages` | pass; no blockers |
| Qoder GLM | Session `91a0edeb-4e6b-487e-8755-70e1cbdc4cb4`; configured `GLM-5.3`, runtime alias `gmodel`, `reasoning_effort=max`, Plan requested | pass; no blockers |

Complete original reports, briefs, result/usage receipts, exact configured identity evidence and input manifest: [final-review/round2](final-review/round2/). Both processes exited 0 with substantive reports and no live child; their owned panes were closed. Guard/Plan restraint was instruction-based, not an OS sandbox guarantee.

Both critics suggested optionally proving a positive ordinary scroll offset rather than relying on equality from a possibly zero offset. The coordinator exercised that stronger scenario in a real terminal: **offset 8 remained 8**, with body focus preserved, through both Esc and Backspace. No additional product/test correction is required. MiniMax separately verified that the existing resume counter observes the only two real call sites and requires no change. Earlier rejected/deferred suggestions remain as adjudicated in round 1.

## Checkout integrity and execution accounting

The original targeted attempt was interrupted mid-tool-call, with **no final verdict from either critic**. Its two old process IDs were absent before retry; the old MiniMax pane had become the coordinator pane and was preserved. No duplicate running workers were launched.

All **2428** tracked/nonignored untracked entries, file modes, shortcut targets and additions/deletions matched before/after the successful wave, and git status matched. The recovered fingerprint also exactly matched the interrupted attempt's pre-wave fingerprint:

`cf1584f34c43be32695c8baee96d1c473d97fc37686098ae9156dae35502fe50`

Compared with the first full council, only `skill_lens/tui/why.py`, `tests/test_tui_diff.py` and `tests/test_tui_json.py` changed among product/test Python files, plus the factual implementation appendix. The correction patch was rebuilt from SHA-256-verified original review bytes; GLM independently reconstructed it byte-for-byte. Unchanged positive full-review and mutation scope remains valid.

Expected substantive final reviews: two full reviews, then two targeted follow-ups after correction. Actual final-review launches: **six** — two full reviews, two interrupted targeted attempts, two successful fresh targeted retries. This was not a third broad review wave. Successful targeted durations and provider-exposed usage are retained in `round2/execution.json` and result receipts; interrupted usage/elapsed totals are not fully available. No cost or token savings are claimed.

## Verification

The implementer's final-tree logs were inspected by the coordinator and recovered losslessly from the interrupted Qoder transcript's file-read result. Complete recovered outputs are retained in [correction-evidence.json](final-review/round2/correction-evidence.json), not merely copied claims from the handoff.

| Final implementer command | Observed result |
| --- | --- |
| `.venv/bin/pytest --cov=skill_lens` | Exit 0; **1192 passed, 1 skipped**; **90.15% combined coverage**, with branch measurement enabled; 208.76 seconds |
| `.venv/bin/mypy` | Exit 0; no issues in 41 source files |
| `.venv/bin/ruff check .` | Exit 0; all checks passed |
| `.venv/bin/ruff format --check .` | Exit 0; 400 files already formatted |
| Affected Diff/Why/JSON suites | Exit 0; 101 passed |

The existing skip requires a case-sensitive filesystem. Coverage is not a branch-only percentage. No threshold/exclusion, snapshot or golden change; CLI snapshots passed without regeneration.

The earlier coordinator campaign and targeted rechecks account for **23 mutation scenarios with no remaining survivors**: [round 1](mutations/round1.json), [round 2](mutations/round2.json). The [coordinator-stage record](coordinator-verification.md) remains historical evidence, superseded here for final status.

The coordinator additionally ran the corrected app in a **real Rex PTY using Textual's LinuxDriver**, against temporary synthetic HOME through `paths.set_sandbox`: candidate title/body × 100×30/60×24 × Esc/Backspace, two actual push/pop round trips per case. **All eight cases / sixteen round trips preserved focus; exit 0.** The supplemental nonzero-scroll scenario passed both return keys at 60×24. Terminal grid receipts, focus/scroll results and nine actual terminal captures are preserved in `round2/`; all owned smoke panes and temporary synthetic homes were removed. These are terminal-rendering checks, not human visual approval.

No real installed skills/settings were used. Unrelated `.path`, the native-asyncio plan/evidence and `docs/validation/2026-10-25/` remain excluded from the U5 delivery. No version, release, dependency, engine, controller, serializer, registry or shared-process change belongs to this acceptance.

### Coordinator final gates after documentation integration

The coordinator then ran all four gates on the documentation-integrated tree:
**1192 passed, 1 skipped in 203.98 seconds; 90.15% combined coverage**,
mypy clean over 41 source files, Ruff lint clean and **403 files already formatted**.
All commands exited 0. Complete outputs and input fingerprint:
[coordinator-final-gates.json](final-review/round2/coordinator-final-gates.json).
The product/test files still match the reviewed bytes; only the enumerated
acceptance/status documents and new U5 evidence records changed afterward.
