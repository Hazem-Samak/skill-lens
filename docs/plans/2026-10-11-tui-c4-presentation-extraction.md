# Plan: C4 shared presentation extraction

Status: Agreed
Authorization: User instruction on 2026-10-11 to start C4; Gemini 3.8 Flash High through Agy implements, Step 5 Preview Free through OpenCode is the only reviewer. User selected High reasoning for both reviews.
Reference: pending
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
