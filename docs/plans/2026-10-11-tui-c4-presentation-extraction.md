# Plan: C4 shared presentation extraction

Status: Agreed
Authorization: User instruction on 2026-10-11 to start C4; Gemini 3.8 Flash High through Agy implements, Step 5 Preview Free through OpenCode is the only reviewer. User selected High reasoning for both reviews.
Reference: 476478ac2d3c9792c3c3f9dc7609007474e309d8
Risk and review: High because the Phase 3 presentation behavior is load-bearing (AGENTS.md section 4). The user's explicit one-reviewer-only instruction overrides the usual two-critic roster for this session; retain all behavior checks and use Step 5 for both planning and final code review. Do not claim verified family diversity.
Expected child tasks: 3 before corrections: planning critic, sole implementer, final critic.

## Outcome

Expose plain content and state mappings for the future optional TUI while keeping
all existing CLI output unchanged. Implement only C4 in FULL_SCREEN_TUI.md sections
21.5, 21.6 (presentation acceptance), and 22.

## Current state

- Clean root checkout on `main`; T3 worktree binding is null. The root has local
  commits ahead of origin; preserve them. No isolation or dependency install needed.
- `skill_lens/render.py` owns three private state/scope dictionaries and six diff
  content helpers. `_copy_heading` mixes content with Rich formatting and live path
  display; `_no_differences_message` mixes notice wording with Rich tags.
- All 17 pinned output files exist under `tests/fixtures/snapshots/`.
- `models/diff.py` supplies frozen report objects. No model/engine changes are needed.
- Phase 3 findings D-03 and D-04 require honest no-baseline wording and correct
  truncation notices. Preserve those branches and existing unified range formatting.
- Live T3 catalog confirms Antigravity model `gemini-3.8-flash-high` and
  OpenCode model `opencode/step-5-preview-free` with `variant=high`, Full access available.
- Refreshed coordinator baseline: 542 passed, one case-insensitive-filesystem skip,
  94.19% coverage; strict mypy clean over 28 source files, Ruff lint/format clean.

## Scope and boundaries

Product edits are limited to `skill_lens/presentation/__init__.py`, `state.py`,
`text.py`, `skill_lens/render.py`, and `tests/test_presentation.py`.
The coordinator owns this plan and append-only execution/acceptance records.
Do not edit models, core services, CLI, registry, packaging, dependencies, existing
tests, snapshots or goldens. No C5 audit, mutation campaign, screens, Textual,
launch changes, publishing or remote push. Workers do not commit or delegate.

## Implementation steps

1. Move `_STATE_STYLE`, `_STATE_MARK`, `_SCOPE_LABEL` to public `STATE_STYLE`,
   `STATE_MARK`, `SCOPE_LABEL` in `presentation/state.py`, preserving keys/values.
   Renderers import the shared dictionaries; no duplicate definitions remain.
2. Add frozen, slotted `HeadingParts(mark, style, path, variant, scope,
   parse_status, status)` and `NoticeParts(label, style, body)` in `text.py`.
   Extract `range_text`, `unified_text`, `unreadable_reason`, `needs_listing`
   with their existing algorithms and no filesystem or formatting dependency.
   Move `_UNREADABLE_REASON` with `unreadable_reason`; importing the existing
   `ERR_*` constants from `models/parsing.py` is permitted.
3. `copy_heading(copy, *, baseline_exists, display_path)` returns plain fields.
   Preserve branch priority: baseline, unreadable, differing files, no baseline,
   identical. Preserve variant's leading space and scope/parse status strings.
   `no_differences_message(report)` returns existing wording split into label,
   style and body; body retains the leading space after the label.
4. Re-export all three dictionaries, both dataclasses and six helpers through
   `presentation/__init__.py`. Shared code imports no Rich, Textual, Console,
   renderer, or filesystem/path service. It only consumes supplied models/text.
5. Keep small private Rich adapters where useful in `render.py`. Live CLI calls
   `paths.display()` before passing the path; escape literal fields at the Rich
   boundary, retain styling there, and keep Syntax diff bodies unescaped as now.
   Escape path, variant, scope, parse status and status separately; preserve the
   existing two-space gap before status. Render consumes shared content without
   duplicating status/wording logic.
6. Add focused presentation tests using synthetic model objects and temporary
   home fixtures where needed. Check public exports, dictionary contents,
   immutable/slotted parts, each heading/notice branch, unreadable fallback,
   zero/one/many range counts and unified text. Verify literal brackets, closing
   tags and backslashes, and absence of binary payload in rendering.
   Exercise all shared helpers with live path/filesystem boundaries patched to
   raise, using already-constructed reports. Check import dependency direction
   using parsed imports. Keep tests about observable behavior rather than source
   layout beyond the required dependency guard.

## Acceptance

- All 17 existing snapshots pass byte-for-byte without regeneration or edits.
- All six helpers and both frozen/slotted parts are available from the public
  package, and dictionaries retain current values.
- Literal user text remains literal in shared parts and rendered output; no
  escaping or Rich markup is added in shared content. Binary content stays hidden
  by the existing renderer guard; do not change the unified-text algorithm.
- Shared helpers perform no live reads, home lookup, path resolution or display.
- No duplicate status/notice algorithm remains in render; no backwards dependency
  from models/core/shared presentation to render; no Rich/Textual in shared code.
- Baseline and final coordinator checks use the repo `.venv` and synthetic HOME:
  `pytest --cov=skill_lens`, `mypy`, `ruff check .`, `ruff format --check .`.
  Coverage must meet the configured 90% threshold. Review all skips/failures.
- Coordinator inspects the full diff and allowed paths; reviewer fingerprints
  match before/after; every in-scope blocker is resolved; all child tasks terminal
  with `hasPendingChildRuns=false` before acceptance.

## Review decisions

- Step 5 Preview Free (High) planning review passed with no blockers. Requested
  target matches task/configuration receipts; provider execution identity remains
  unverified. Before/after repository fingerprints match.
- Accepted three non-blocking clarifications: explicitly move unreadable-reason
  map and allow model error constants; document per-field Rich escaping and exact
  spacing already required by output parity; record refreshed baseline figures.
  These clarify the existing contract without changing behavior or scope; no
  additional broad review is needed under council section 6.
- The original review was cancelled before a verdict; its partial analysis is
  not acceptance evidence. The completed fresh task supplies acceptance.
- User authorization covers C4 and the named one-reviewer roster; no additional
  scope is authorized. C5 remains a separate assignment.

## Execution and acceptance record — 2026-10-11

This appendix records execution evidence; it does not amend the frozen contract.

- Coordinator: Codex `gpt-6.1-sol`, reasoning High, Full access/default.
  Implementer: Antigravity `gemini-3.8-flash-high`, Full access/default.
  Sole reviewer: OpenCode `opencode/step-5-preview-free`, `variant=high`,
  Full access/plan, as explicitly selected by the user. Targets/options/modes
  were checked using T3 dispatch and child configuration receipts. Provider-side
  execution identity was not independently verified; no family-diversity claim.
- The two-commit freeze is `476478ac2d3c9792c3c3f9dc7609007474e309d8` plus
  reference-only record `897aa77`. Both implementer rounds verified the authority.
- Five product files changed: shared package `__init__.py`, `state.py`, `text.py`,
  `render.py`, and `tests/test_presentation.py`. No other product files, models,
  engines, CLI, registry, snapshots, goldens, dependencies or screens changed.
- Coordinator found and reproduced the new renderer test's missing temporary-home
  fixture: `_copy_heading` reaches `paths.home()` through `paths.display()`.
  Gemini corrected that test to use `mock_home` and assert the shortened path;
  the literal-parts test also uses the exact contract test name. No product
  behavior changed during correction.
- Coordinator final verification: **561 passed, 1 skipped, 94.58% coverage**;
  strict mypy clean across 31 source files; Ruff lint and format checks clean.
  Skip reason: case-insensitive filesystem cannot hold two distinct case-only
  filenames. All 17 existing render snapshots pass and their SHA-256 hashes
  match the pre-implementation files. Nineteen presentation tests were added.
- Step 5 final verdict: **pass**, no blockers. Reviewer reported 30 old/new
  renderer comparisons with identical output and supplemental isolated mutation
  checks (21 of 28 caught). These are supplemental reviewer observations, not
  completion of the separate C5 audit. Planning and final reviewer before/after
  repository fingerprints match; neither completed review changed project files.
- Optional suggestions deferred: stronger real-tag cases for variant/parse-status
  escaping, styled-output assertions, and a wider static dependency guard. The
  current implementation preserves each escape/style operation; source inspection,
  required tests and unchanged output support acceptance. Some fields are fixed
  strings or enums, and unused hypothetical filesystem code is not a current live
  read. These are test-hardening suggestions, not unresolved behavior defects.
  The unrelated docstring quote change is harmless and retained to avoid another
  correction round. No current acceptance blocker is deferred.
- Expected launches: 3; actual: 5. Extra tasks were the restarted cancelled plan
  review and the test-isolation correction. Elapsed wall time from first review
  dispatch at 07:51:38 UTC to final review completion at 09:47:10 UTC: about
  1 hour 56 minutes, including the user interruption. Final review itself took
  about 53 minutes. Token usage is unavailable from the retained T3 receipts;
  no token/cost savings claim is made.
- All five tasks are terminal with `hasPendingChildRuns=false`. No worktree was
  created; the original root checkout and preceding local commits are preserved.
  C4 is accepted; C5 remains the next separately authorized assignment.

### Task ledger

1. Task `node:delegated-task:command%3Amcp%3A9623ff41-db65-40bb-9c29-04c59cb4ac66%3Adelegate-task%3Ac4-20261011-plan-step5-r1`; run `run:thread:thread%3Adelegated-task%3Acommand%253Amcp%253A9623ff41-db65-40bb-9c29-04c59cb4ac66%253Adelegate-task%253Ac4-20261011-plan-step5-r1:ordinal:1`;
   status `cancelled`, `hasPendingChildRuns=false`.
2. Task `node:delegated-task:command%3Amcp%3A6c73761f-2aaa-4d4b-a710-f95db38b0476%3Adelegate-task%3Ac4-20261011-plan-step5-retry-r1`; run `run:thread:thread%3Adelegated-task%3Acommand%253Amcp%253A6c73761f-2aaa-4d4b-a710-f95db38b0476%253Adelegate-task%253Ac4-20261011-plan-step5-retry-r1:ordinal:1`;
   status `completed`, `hasPendingChildRuns=false`.
3. Task `node:delegated-task:command%3Amcp%3A6c73761f-2aaa-4d4b-a710-f95db38b0476%3Adelegate-task%3Ac4-20261011-agy-implementation-r1`; run `run:thread:thread%3Adelegated-task%3Acommand%253Amcp%253A6c73761f-2aaa-4d4b-a710-f95db38b0476%253Adelegate-task%253Ac4-20261011-agy-implementation-r1:ordinal:1`;
   status `completed`, `hasPendingChildRuns=false`.
4. Task `node:delegated-task:command%3Amcp%3A6c73761f-2aaa-4d4b-a710-f95db38b0476%3Adelegate-task%3Ac4-20261011-agy-test-isolation-r1`; run `run:thread:thread%3Adelegated-task%3Acommand%253Amcp%253A6c73761f-2aaa-4d4b-a710-f95db38b0476%253Adelegate-task%253Ac4-20261011-agy-test-isolation-r1:ordinal:1`;
   status `completed`, `hasPendingChildRuns=false`.
5. Task `node:delegated-task:command%3Amcp%3A6c73761f-2aaa-4d4b-a710-f95db38b0476%3Adelegate-task%3Ac4-20261011-final-step5-r1`; run `run:thread:thread%3Adelegated-task%3Acommand%253Amcp%253A6c73761f-2aaa-4d4b-a710-f95db38b0476%253Adelegate-task%253Ac4-20261011-final-step5-r1:ordinal:1`;
   status `completed`, `hasPendingChildRuns=false`.
