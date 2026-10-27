Review complete. The repository is byte-identical to its starting state, and all evidence was gathered in a disposable copy outside the checkout.

**EFFECTIVE_MODEL**
- provider/model: `minimax / MiniMax-M3.1-Flash`
- settings: thinking variant enabled; no separate effort control exposed to this seat (owner-requested critic effort `High` is not observable in the session's model token → effort mapping **unverified**)
- runtimeMode: `Plan` (T3 Code interaction mode — Plan)
- interactionMode: `plan` (Plan Mode active; no implementation performed)
- evidence — **requested** (owner): MiniMax M3.1 Flash via MCode + DeepSeek V4.1 Flash 1017 via River/Pi as critics; coordinator Codex gpt-6.1-sol Medium; implementer Antigravity Gemini 3.8 Flash High. **configured/observed**: session runs `m:minimax:MiniMax-M3.1-Flash:v:thinking`, Plan runtime mode, plan interaction mode, zero delegation. **provider-confirmed**: only the harness-reported session model id. **unverified**: DeepSeek V4.1 Flash 1017, Codex gpt-6.1-sol, Gemini 3.8 Flash — named families differ and catalogue identity is not upstream attestation. Tool results (mypy/ruff/pytest/mutation harness) are tool-verified, not model-attested.

**VERDICT**: `changes_required`

**BLOCKERS**

1. **`skill_lens/tui/home.py:982-986`, `:480-483`, `skill_lens/tui/app.py:203-209` — removal notice survives an explicit Home refresh (product defect).**
   *Problem:* the notice clears only for `down/up/j/k/slash/a/escape/enter`; the app refresh binding is `"r"` → `action_refresh`, and no path clears the notice there. *Expected (frozen §5 step 5):* "clearing it on the next explicit Home navigation/filter/refresh action." *Evidence:* runtime probe in a disposable copy — after a removal returned to Home, a further explicit `r` left `_removal_notice` set and `#removal-notice` still rendering the stale text. `docs/TUI_U4_WALKTHROUGH.md:32` documents the narrowed behaviour instead of the frozen requirement.

2. **`skill_lens/tui/why.py:440-465` — agent strip DOM order breaks the frozen sorted-order contract after refresh (product defect).**
   *Problem:* `_refresh_strip` updates surviving buttons in place and `mount()`s new ones appended; it never reorders, while model order comes from `ScanEntry.agents` (`skill_lens/core/scanner.py:138-139`, sorted). *Expected (frozen §3 item 3):* strip options "preserving the scan's sorted agent-ID order"; §3 item 4 "wrap deterministically". *Evidence:* runtime probe — model `['claude','codex','dsh','omp','opencode','pi','qoder']` vs DOM `['codex','dsh','omp','opencode','pi','qoder','claude']` (`order_matches: False`), so Left/Right no longer follow the visible strip. `tests/test_tui_why.py:382-423` checks only the model, never the DOM, never after a refresh.

3. **`tests/test_tui_why.py:1313-1413` — frozen §5 step 7 (data freeze / preservation) is unproven; the only mutation is dead code.**
   *Problem:* the sole mutation targets `~/.claude/skills/deploy/SKILL.md` (`:1368-1370`) guarded by `if skill_md.exists()`; the built scenario `symlink_farm_multi_agent` creates only `~/.agents/skills/shared/SKILL.md`. No assertion the mutation happened, no deletion, no shortcut retarget, no after-manifest (`before` at `:1325`, only `assert len(before) > 0` at `:1413`), no parity assertion. *Expected:* "edit/delete skill files/settings and retarget shortcuts before first detail/agent visit… Extend target manifests (bytes, modes, shortcut targets) through detail, agent changes, expand/collapse, back, refresh and quit." *Evidence:* probe — target `exists: False`; only SKILL.md present is `.agents/skills/shared/SKILL.md`.

4. **`tests/test_tui_why.py:782-821` — the "accepted non-capture report event" is actually rejected.**
   *Problem:* the test seeds the **cache** (`:805`) but never an **active** diff request, so `SessionController.accept_view_result` returns `False` at `skill_lens/tui/session.py:264-266` before the screens see it; the assertions then hold trivially. *Expected (frozen §5 step 5):* "an **accepted non-capture report event**." *Evidence:* instrumented replay recorded `[('diff', 123, ('key',), False)]` — accepted = `False`.

5. **`tests/test_tui_why.py:496-608` — frozen §5 step 5 race coverage omits the error outcomes and never asserts cancellation events.**
   *Problem:* the docstring claims "stale Home success/**error** … stale detail success/**error**", but the controlled workers only return successful reports; no error outcome is produced, and no cancellation-event assertion (`_report_events[…].is_set()`) exists anywhere in the file. *Expected:* "Assert **cancellation events**, full token ownership, no hidden Home dispatch, no stale rendering/cache/failure, and immediate resumed progress without releasing the cancelled worker."

6. **`tests/test_tui_why.py:1236-1305` — frozen §5 step 6 return matrix is incomplete and asserts no exit code.**
   *Problem:* four of five frozen states, omitting **"successful refresh with a changed count"**; the four present states are written directly into controller fields rather than produced by the real capture paths (the real ones exist only while the detail is still open, `:1179-1233`). No exit-result assertion. *Expected:* "return through the real back action after each of: capture still pending, size refusal, consistency retry, accepted unexpected fault, and successful refresh with a changed count… fault shows details and **quits 3**; other cases **quit 0**." *Evidence:* the product behaviour is correct (probe: Home rows 2→3 on a real refresh; exit 3 after fault, 0 normally) — this is an **evidence gap, not a product defect**.

7. **`tests/test_tui_why.py:1421-1501` — frozen §5 step 4 identity coverage is synthetic.**
   *Problem:* two hand-built `CandidateResolution` objects with fake `/mock/path/…` paths are assigned to `why._report` (`:1465`); no real directory/frontmatter/unresolved resolution, no differing-name fixture, and no comparison against `snapshot_why` output (the only `snapshot_why` call is in the helper-branch test at `:1833`). *Expected:* "Displayed values/order must agree with `snapshot_why` and model candidates."

8. **`docs/validation/u4/implementation/acceptance_mapping_r2.md:13-18, 26-33, 39, 60-75` — 16 cited test selectors do not exist.**
   *Problem:* resolving every cited `test_*` against the real tree leaves 16 unmatched (e.g. `test_c1_regression_collapse_and_title_focus_preserved_on_update_ui`, `test_why_screen_header_display`, `test_all_filter_return_matrix_across_lifecycle_events`, `test_why_screen_quit_exit_codes_normal_and_sticky`). Two frozen criteria have **no** counterpart at all: the dedicated exit-code test and a dedicated header-display test. *Evidence:* scripted diff of the mapping's `test_*` tokens against `^def (test_[a-z0-9_]+)` across `tests/test_*.py`.

9. **`docs/TUI_U4_WALKTHROUGH.md:30, 34, 93-96, 107` — factual drift (coordinator finding C7 class, still open).**
   *Problem/evidence:* claims 824 lines for `why.py` (actual **820**); 2066 lines for the test file (actual **2077**, 36 tests); "Combined coverage: 90.89%" (reproduced **90.87%**, coordinator receipt 90.84%); "in 103.54s" (reproduced **104.70s**, coordinator 104.75s); "why.py coverage: 90% (floor: 85%)" — no per-file floor exists, `pyproject.toml:89-90` defines a single `fail_under = 90`; "361 files already formatted" (whole-repo `ruff format --check .` → **363**).

10. **`tests/test_tui_why.py:1553-1595` — frozen §5 step 8 layout coverage tests no long content and no reachability.**
    *Problem:* ordinary short fixture; after `Tab` only `app.focused is not None` is asserted (`:1572`, `:1591`) — never *which* control, never the Enter toggle result, no viewport/scroll geometry; no long-path/long-reason fixture exists. *Expected:* "long content wrapping, keyboard reachability"; "Long paths/reasons wrap or scroll, with usable keyboard controls at both 100×30 and 60×24."

**SUGGESTIONS** (non-blocking)
- `skill_lens/tui/home.py:1014`, `:1023`, `:1033` — `on_input_changed`, `on_input_submitted`, `action_clear_filter` lack the `_suspended` guard every other Home handler uses. Latent, not user-reachable today (Home's bindings are inactive and its `Input` unfocused while the detail is up); `action_clear_filter` would steal focus to Home's table if it ever were reached.
- `#catalog-note` recoloured `$warning` → `$text-muted` in Home's `DEFAULT_CSS` — unrelated to U4; benign out-of-scope churn.
- Report notes render in the header *and* inside every candidate body (duplicate display).
- `WhyScreen.action_quit` (`skill_lens/tui/why.py:~731`) is dead code — the `q` binding targets `app.quit`.
- `_refresh_candidates` dedupes on `id(self._report)`; CPython may reuse an id after GC, which could suppress a rebuild.
- `on_button_pressed` uses `next(...)` with no default — a hypothetical empty agent id would raise `StopIteration` in an event handler.
- Coverage fell from the planning baseline 91.16% to 90.84–90.87% against a `fail_under = 90` gate; the new 820-line `why.py` sits at 90%.
- `docs/TUI_U4_WALKTHROUGH.md:32` narrows the frozen "navigation/filter/refresh" to "navigation" — fix together with Blocker 1.

**FILES_AT_RISK**
- `skill_lens/tui/why.py` (new, 820 lines) — Blocker 2
- `skill_lens/tui/home.py` — Blocker 1
- `skill_lens/tui/app.py` — Blocker 1
- `tests/test_tui_why.py` (new, 2077 lines, 36 tests) — Blockers 3–7, 10
- `docs/validation/u4/implementation/acceptance_mapping_r2.md` — Blocker 8
- `docs/TUI_U4_WALKTHROUGH.md` — Blockers 1, 9
- Read-only dependencies inspected, not modified: `skill_lens/tui/session.py`, `skill_lens/tui/__init__.py`, `skill_lens/core/{scanner,discovery,snapshot}.py`, `skill_lens/cli.py`, `tests/fixtures/{scenarios,builders}.py`, `tests/conftest.py`, `tests/test_tui_home.py`, `pyproject.toml`
- Untouched user work, out of scope: `.path`, `docs/plans/2026-10-26-omp-native-asyncio-trial.md`, `docs/validation/2026-10-25/`, `docs/validation/omp-native-asyncio/`

**CONCEDED**
- **Gates reproduced independently in a disposable copy:** `pytest --cov=skill_lens` → 1121 passed, 1 skipped, 90.87% combined, `why.py` 90%, `home.py` 90%, gate met, 104.70s; `mypy` → clean, 39 source files; `ruff check .` → "All checks passed!"; `ruff format --check .` → 363 files formatted. No writes to the checkout.
- **Mutation gate independently re-run** (`--out` to an external path only): 5/5 mutants killed (`mutant_rc=1`), all 5 controls and restores pass (`rc=0`), `restored_identical: True`, `why.py` SHA-256 `85d8ec0…a408` unchanged before and after. The coordinator receipt is substantiated. Scope limit: the `target_read` mutant proves the read-sentinel half of C5, not the target-alteration/manifest-parity half (Blocker 3).
- Fingerprints: all 11 reviewed files match `coordinator/verification-r1.json` SHA-256 exactly; `review-r1.diff` covers exactly the 13 expected paths.
- **C1 fixed** — collapse state and `CollapsibleTitle` focus survive `app._update_ui()` (`tests/test_tui_why.py:152`).
- **C2 fixed** — `Content.from_text(..., markup=False)` at both button creation and update; body/title/status literal.
- **Identity key mapping is consistent end to end** — `ScanEntry.canonical_path` (`core/scanner.py:175`) equals `canonical_key(entry)`; Home passes it; detail validates against `{canonical_key(e) for e in current.index.entries}` before every dispatch.
- **Optional-import contract preserved** — `skill_lens.cli` imports with Textual blocked; `skill_lens.tui` raises `ImportError` (correct for an optional extra); the CLI gates on `find_spec("textual")` and imports lazily (`skill_lens/cli.py:58-91`).
- **Exit-code contract holds** — detail `q` after an accepted fault → `return_code == 3`; normal quit → `0`.
- **Refresh core behaviours correct** — surviving install, removed install → Home with notice, changed eligibility, no-agent replacement, empty catalog, retained filter excluding controller fallback.
- **C7 doc corrections partly landed** — `FULL_SCREEN_TUI.md` now labels U5 "Diff and JSON" and states U4 is pending review (lines 6-9, 29-31, 41-43); the walkthrough header claims no acceptance; the frozen walkthrough requirement on re-deriving the entry from the new snapshot is met (§1 item 4).

<media type="file" src="/Users/corvette/.minimax/v2/sessions/2026/10/27/09-21-21-524-session_bXZzXzhiNmEzYmZiYzY1YTQyZWQ5MzU5NGQwODQ4NWU4MTg2/artifacts/plan.md" caption="U4 independent critic review R1 — full review record (plan file)" />
