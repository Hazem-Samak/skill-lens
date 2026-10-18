# Final council report — Herdr single-cycle trial preparation / handoff review

**This document is a review artifact, not an implementation plan. It authorizes no
implementation, no file change, no live Herdr control, no model traffic, and no
trial start. Every finding below is reported for the coordinator to action or accept.**

## Summary

Scope: read-only verification of the prepared handoff for the one authorized disposable
Herdr development cycle — the frozen plan, the allowed diff, the single-cycle record, and
the concrete preparation receipt on disk. No deferred experiment (observer work,
P02-P09, restart/cancellation, Phase C) was reinstated, and no third-party model identity
is claimed.

Verdict: **changes_required** — one narrow, record-integrity blocker. The trial contract
itself is sound: the allowed diff is exactly the three permitted files, the frozen plan and
provenance commit are real and pushed, the disposable checkout matches the receipt
byte-for-byte, the 1046 protected original-repository files are byte-identical to `9a1e78c`,
and all four product gates match their recorded logs. The blocker is confined to a
repository acceptance record (`preparation-agreed-snapshot.json`) whose two recorded
hashes are both superseded while the file self-describes as holding current ones. It does
not affect the Entry gate, the roster, the boundaries, or trial execution safety; it
affects the honesty of the permanent evidence a later auditor would read.

---

EFFECTIVE_MODEL: MiniMax-M3.1-Flash-Preview (thinking) — configured/runtime target
`m:minimax:MiniMax-M3.1-Flash-Preview:v:thinking` in T3 Code via acpRegistry, Plan
interaction mode, full-access parent runtime. T3 receipts corroborate the configured
MiniMax/mcode reviewer pair; the upstream served model/provider identity is unverified and
is not attested here. Settings and modes are stated as configured, not independently
attested. Operated as a read-only critic: no repository write other than this canonical
review artifact, no live Herdr or Hermes control, no delegation, no model traffic, no
gate re-run.

VERDICT: changes_required

BLOCKERS:

1. `docs/validation/two-surface-orchestration/2026-10-17/implementation/single-cycle/preparation-agreed-snapshot.json:5` and `:6` — both recorded file hashes are superseded, while `:9` declares the file holds the "current revised hashes here".

   Evidence (reproduced independently, read-only):
   - Line 5 records the plan as `9ae3fcd1bee80343f8493e4c10a2ef1a2527d38b7a83d4d9d5796115ab8e813f`. That is the plan blob **at the freeze commit `ad19c31`**. The plan on disk now hashes `d8b2d24c5f959f488ca9fcfe4a3eeeb7d6c633629b6c012c01b4b37d7dc26027` — they differ by exactly the `Reference:` line (`Reference: Pending two-commit freeze.` → `Reference: ad19c3115f518b8f10d1ab2ef23c04254196886b`), filled by provenance commit `1aab76b`.
   - Line 6 records the brief as `214e390abe1d036b63f1dbc2dd420c1744a9b7b3d682cbbc73eb9d298366404b`. That is the text MiniMax R2 reviewed. The brief on disk now hashes `e16d5b97ca464442decb456088d36d4af89e35daa0d9d4c51ec23d43e7ef66f3`.
   - The change was **mandated, not drift**: `plan-minimax-r2-review.md:53` requires "full hash substituted into plan Reference and brief `:5-7` before final review/delivery." Brief lines 6-7 now carry the frozen hash and the provenance commit. The substitution happened at 23:45:09, after this snapshot was written at 23:44:16.
   - Therefore the snapshot was never refreshed after the substitution it was itself waiting on. MiniMax R2 residual item 1 (`plan-minimax-r2-review.md:43-45`) asked exactly for this refresh; it is unaddressed in substance. The frozen plan's own claim at `docs/plans/2026-10-18-herdr-single-cycle-trial.md:130` — "a new snapshot pins the revised agreed text" — is currently inaccurate.
   - Impact is record integrity, not execution. Nothing in the trial reads this file: the brief's Entry gate (`coordinator-brief.md:31-35`) resolves the plan's `Reference:` to `ad19c31`, which is correct. The live anchors are already right — `preparation.json:19` `brief_sha256 = e16d5b97…` (current) and the external `final-review-before.json` pins plan `d8b2d24c…` and brief `e16d5b97…` (both current, verified).
   - Required fix (coordinator-owned, already inside allowed prep scope): update line 5 to the current plan hash `d8b2d24c5f959f488ca9fcfe4a3eeeb7d6c633629b6c012c01b4b37d7dc26027` and line 6 to the current brief hash `e16d5b97ca464442decb456088d36d4af89e35daa0d9d4c51ec23d43e7ef66f3`, or — preferably — re-derive both from the actual files and re-pin the snapshot as the last step before the coordinator commit. If the intent is instead to pin the *frozen* text deliberately, rename the keys to say so and drop the "current revised hashes here" wording at line 9.

SUGGESTIONS (nonblocking):

- `preparation.json:9` records `provenance_commit` as the bare `1aab76b` while the plan (`:8`) and brief (`:7`) use the full `1aab76b5d5e4af90c37ebf23d3341e7588ac9c27`. Already raised by the other final reviewer. Readability/consistency only; the Entry gate requires the frozen reference commit, not this field.
- `final-review-before.json` predates three files now on disk: the declared coordinator-owned `human-instructions.md`, plus `final-deepseek-r1.json` and `plan-minimax-r2-terminal.json` (both 23:46:45, coordinator-retained task-result dumps). The brief declares only `human-instructions.md` as post-snapshot. Listing the other two explicitly keeps the manifest-vs-disk story complete for a later auditor. This is consistent with the existing retention pattern, not a critic repository write — both critics were read-only.
- `coordinator-brief.md:102-104` hardcodes the named-pair roster. A one-line "these are the exact named roster; no substitution" note would harden the launch against accidental drift. `brief:108` already states this, so this is belt-and-braces.
- `human-instructions.md:18` correctly uses command-local `HERMES_CODEX_BASE_URL=` inline. An explicit "do not export globally" clause for the human would remove any doubt, since an accidental export would alter agent-wide auth behaviour.

FILES_AT_RISK:

- Original Skill Lens repository — read-only boundary **verified intact**. `git diff --name-status 9a1e78c HEAD` shows only `A docs/plans/2026-10-18-herdr-single-cycle-trial.md`; `git diff HEAD` shows only the two additive pointer edits. Independent manifest check: 1045 protected tracked files byte-identical to `9a1e78c` (the "FULL SCREEN TUI Implementation Walkthrough.md" flag in my first pass was a quoting artifact of its space, verified unchanged directly), plus `.path` = 0 bytes, `e3b0c442…` — exactly the claimed 1046. HEAD `1aab76b…` equals `origin`, so both frozen commits are pushed and remote-verified. No product, test, process or registry file changed.
- `preparation-agreed-snapshot.json` — the one file at risk of a false permanent record (blocker above).
- Disposable checkout `…/simple-loop-trial-dkn9ufiu/checkout` — matches the receipt exactly: HEAD `589537f2419fd455ae57ef720e5fcbf06fe04599`, clean status, only tracked file `fixture.txt`, no remotes, evidence dir empty, `fixture.txt` exactly `pilot status: pending\n` (22 bytes) hashing `462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e` (independently reproduced via `printf 'pilot status: pending\n' | shasum -a 256`). No `status_reader.py` or `test_status_reader.py` prewritten, satisfying "no implementation/test code is prewritten."
- External trial root — holds only caches/artifacts (`gates/`, `mypy-cache/`, `pytest-tmp/`, `ruff-cache/`, `command-home/`, `test-home/`), all outside the checkout. Consistent with "external output"; no product writes.

CONCEDED:

- Upstream model/provider identity for every named pair (MiniMax, Qwen AnyModel, DeepSeek WorkBuddy, Gemini/agy, `gpt-6.1-sol`) is unverified under the user-accepted named-pair policy. Not a trial gate; no third-party identity is claimed by this review.
- The plan's self-reference to `ad19c31` cannot be satisfied inside that commit — a commit cannot contain its own hash. The two-commit freeze/provenance split is the correct resolution, and `coordinator-brief.md:32-33` explicitly exempts "the reference/provenance record" from the frozen-text comparison, making the Entry gate satisfiable and fail-closed.
- Native permission modes are N/A (`brief:118-119`); `--tools read,grep,find,ls`, `--no-mcp`, `--no-skills`, `--no-context-files` and fresh empty session dirs are recorded as the native controls. `brief:107` correctly states these are not T3 permission modes or a universal sandbox.
- P01 remains unverified; observer work, P02-P09, restart/recovery, cancellation and Phase C remain paused. No deferred experiment is reinstated by this review, and no historical failure is treated as success.
- The trial-only exception is faithful and bounded: fixture commits are local-only in a repository with no remote (`plan:91-93`, `brief:83`), while every authorized Skill Lens coordinator commit stays immediately pushed — verified here, HEAD matches `origin`. No dependencies added, no config/registry/credential change, no new helper/observer/runtime code, no service.
- Product gates match their recorded logs exactly: pytest `1048 passed, 1 skipped`, coverage `91.11%` (≥90 required); mypy `Success: no issues found in 37 source files`; ruff check `All checks passed!`; ruff format `240 files already formatted`. Only documentation changed after the gates, so "no source/config change since passing gates" holds.
- The launch command in `human-instructions.md:12-22` matches `plan:61-63` flag-for-flag and is fail-closed (requires `HERDR_ENV=1`, fixture present, `entry.json`/`result.json` absent), preserving the human-control boundary: only the human starts Herdr/Hermes.

---

**Authorization statement:** this review authorizes no implementation. The single blocker is
reported for the coordinator to fix or consciously waive; no other action is sanctioned.