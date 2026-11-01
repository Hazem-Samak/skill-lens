I have completed the review. Here is my report.

## EFFECTIVE_MODEL

**Requested:** MiniMax 3.1 F, max effort, through MCode (owner request recorded in the mission; `--effort max`, distinct from the earlier planning `xhigh`).

**Configured identity/settings actually visible to me:** the runtime reports `Model: MiniMax-M3.1-Flash`, assistant `MiniMax Code`, routing id `mavis`, session `mvs_55bb9ef829b24b608cb8921275570d93` (agent-context). I inspected the supplied launch receipt `minimax-launch.json` (only `window_id`/`block_ids`/`revision`) and `minimax-diagnostics/execution.json` (only `schemaVersion`/`sessionId`/`turnId`/`runId`/`startedAt`) — **neither records a model, provider or effort level**.

**Runtime/modes/evidence:** single read-only review turn; no delegation, no file writes, no test/gate/runtime execution, no git mutations. Every manifest path was re-hashed (2417/2417 identical), and all 86 Python fingerprints in `docs/validation/u5/mutations/round2.json` match the current tree byte-for-byte, so the mutation campaign ran against exactly the bytes I reviewed.

**Upstream:** **unverified** — no provider-side attestation is visible to me, and the effort level `max` is a *requested* setting I cannot confirm was effective.

## VERDICT

`changes_required` — one medium blocker in the primary lens (cross-screen focus state). No data-corruption, exit-code, JSON-byte, or CLI-regression defect found.

## BLOCKERS

**1. [MEDIUM] Returning from Diff to Why discards the remembered focus control; the two resume paths are not idempotent for focus.**

- **Location:** `skill_lens/tui/why.py:360-392` (`resume_detail`, `_restore_detail_focus`) and `skill_lens/tui/why.py:602-613` (`_update_strip_focus`), reached from `skill_lens/tui/app.py:274-276` (`close_diff` → `prev_screen.resume_detail()`).
- **Actual behavior:** after Why → `d` → Diff → `Esc`, the Why's keyboard focus ends on the selected agent's strip button (`#why-agent-<id>`), not on the control that had focus when `d` was pressed (e.g. a candidate's `CollapsibleTitle`, or `#why-body`).
- **Expected behavior:** the remembered control is restored and left alone when still valid.
- **Mechanism (traced from source, Textual 8.2.8):** `suspend_detail()` records `self._detail_focus = self.app.focused` (`why.py:357`). `close_diff` pops the Diff then calls `resume_detail()` synchronously; `_restore_detail_focus()` restores the widget **and clears `_detail_focus` (`why.py:388`)**. But `App.pop_screen()` posts `events.ScreenResume` to the revealed Why *before* `close_diff` runs its explicit resume (`textual/app.py:3112-3115`); that message is dispatched later to `WhyScreen.on_screen_resume` (`why.py:344-346`) → `resume_detail()` again. The second call finds `_detail_focus is None`, so `_restore_detail_focus()` falls through to `_update_strip_focus()` and moves focus to the agent button. Because `Widget.focus()` defers through `app.call_later` (FIFO), the later-queued agent-button focus wins. In the default case (focus already on the agent button) the two agree, so the defect is invisible; it manifests only when the user tabbed off the strip first — which `tests/test_tui_why.py:2448-2464` proves is reachable.
- **Contract:** plan `docs/plans/2026-10-29-tui-u5-diff-json.md:51` ("Returning from Diff to Why preserves the agent, candidate expansion, scroll **and focus** when still valid") and `:80` ("Resume must be **effectively idempotent** across Textual lifecycle/app callbacks, without rebuilding unchanged expansion/**focus** state"). `resume_detail`'s own docstring (`why.py:363-368`) claims idempotence but reasons only about the request path, not the focus path.
- **Discriminating test gap:** `tests/test_tui_diff.py:305-344` asserts the agent, the report and the `Collapsible` expansion state across the Why → Diff → Why round trip but never the focus; `tests/test_tui_diff.py` contains no assertion on `app.focused` after returning to the Why (the only `focus` assertions there are Home's table and the Diff body's own focus). A test that opens the Why, tabs to a candidate's `CollapsibleTitle`, presses `d`, presses `escape`, then asserts `app.focused is that CollapsibleTitle` would fail today.
- **Smallest correction:** make the focus restore idempotent — e.g. do not null `_detail_focus` when it is restored (so the second resume re-applies the same widget), or in `resume_detail` only call `_restore_detail_focus()` when the current focus is not already a valid, mounted focusable widget, keeping `_update_strip_focus()` strictly as the "nothing valid focused" fallback.

## SUGGESTIONS

All non-blocking; none is tied to an unmet in-scope contract.

1. `skill_lens/tui/diff.py:460-466` and `skill_lens/tui/why.py:850-857` use `id(self._report)` as a render-cache key. `id()` is reusable after an object is freed, so a same-generation report swap that landed on a recycled address would silently skip a re-render. The generation field and the `id(None)` sentinel intervene today, so I found no reachable path — a monotonic counter or the report's own identity would be safer.
2. `skill_lens/tui/home.py:1215` (`action_open_diff`) does not clear the removal notice, while `HomeScreen.on_key` (`home.py:1108-1112`) clears it for `down/up/j/k/slash/a/escape/enter/r`. A notice therefore survives a `d` round trip but is cleared by `enter`. Cosmetic inconsistency only; the plan does not require clearing on `d`.
3. `DiffScreen.action_quit` (`diff.py:699-703`) and `WhyScreen.action_quit` (`why.py:999-1003`) are unreachable — both screens bind `q`/`ctrl+c` to `app.quit`, which resolves to `App.action_quit` (`app.py:198`, confirmed via Textual's `_dispatch_action`). The App version additionally calls `workers.cancel_all()`. Harmless dead code, but the two screen methods read as if they were the quit path and omit worker cancellation.
4. `tests/test_presentation.py` dropped `test_public_exports`, leaving the `skill_lens.presentation` public surface (now 25 symbols, up from 11) without an inventory guard. The plan explicitly says export inventories are not a required guard, so this is acceptable; noted only because the surface grew.

## FILES_AT_RISK

- `skill_lens/tui/why.py` — `resume_detail` / `_restore_detail_focus` / `_update_strip_focus` (focus restore path).
- `skill_lens/tui/app.py` — `close_diff` (the host-explicit resume that pairs with Textual's `ScreenResume`).
- `tests/test_tui_diff.py` — missing focus assertion across the Why → Diff → Why round trip (the discriminating test belongs here).
- `tests/test_tui_why.py` — the natural home for a resume-idempotence focus test.

No other file in the reviewed scope carries an unresolved risk.

## CONCEDED

Prior concerns and evidence I checked and ruled out:

- **Mutation-evidence soundness.** I re-verified that `round1.json`'s eight TUI product fingerprints still match the current tree exactly, so round 1's other 20 mutation results apply to the reviewed bytes; `round2.json`'s 86-file fingerprint set matches the current tree with zero mismatches. Round 1's M05/M06/M23 "survivor" verdicts are superseded by round 2's detected/restored-pass receipts, which I read (each mutant exits 1 at its intended assertion; each restored copy passes). All 14 named transitions the plan requires (plan `:117`) map to a distinct mutant. The evidence discriminates real transitions; I found no surviving in-scope mutation.
- **Tree integrity.** The supplied manifest's `tree_fingerprint` equals the stated SHA `affd59ea…`; all 2417 paths re-hash identically to the manifest, so the reviewed tree is exactly the manifested tree. The unrelated untracked work (`.path`, `docs/plans/2026-10-26-omp-native-asyncio-trial.md`, `docs/validation/2026-10-25/`, `docs/validation/omp-native-asyncio/`) is untouched and out of scope.
- **Markup/binary literal rendering.** `Content.__init__` and `Content.assemble` treat plain strings literally in Textual 8.2.8 — no markup parsing path exists; every `Content.from_text` call site passes `markup=False` explicitly, and `JsonView` uses the raw `Content(...)` constructor. The `markup=True` default of `Content.from_text` is not reached.
- **"J"/"d" versus filter typing.** `Input._on_key` (`textual/widgets/_input.py`) calls `event.stop()`/`prevent_default()` for printable characters, so `J` and `d` typed into the Home filter are ordinary text and never reach the screen bindings. `HomeScreen.action_toggle_json` additionally requires `table.has_focus`.
- **JSON-mode focus hand-off.** `add_class`/`remove_class` → `update_node_styles` → `Stylesheet.update_nodes` applies `display` synchronously, so the deferred `focus()` in `enter_json_mode`/`leave_json_mode` lands on a legal target; `display:none` widgets are excluded from Textual's focus chain, and `body.can_focus = False` removes the Why/Diff body as a Tab stop.
- **Refresh/removal unwind.** Diff-over-Why removal pops the Diff first, then the revealed Why detects its missing key and calls `close_why` while it is topmost (`close_why` correctly refuses a non-topmost Why); Diff-over-Home produces the notice from its captured opening name/key and hands it to `HomeScreen.set_removal_notice` before `resume_why()`, and `_reset_for_generation` does not clear that notice.
- **Ownership/cancellation.** `_cancel_owned_token` in both `diff.py:354-365` and `why.py:536-547` guards on `active == owned` before invalidating; `accept_view_result`/`accept_view_error` reject stale generations, request ids and arguments, and `accept_capture` clears the cache and cancels active report events, so stale results and stale faults change neither the display nor the sticky failure flag.
- **CLI output unchanged.** The `render.py` extraction is a pure move of the enumerated notice branches into `presentation/text.py`; the existing CLI snapshot suite pins it and no snapshot was regenerated.

Limitations of this review: per the mission I ran no tests, gates, or the TUI, so the blocker above is a source-traced defect (mechanism given in full) rather than an observed one; I performed no human visual approval; the coordinator's live smoke (Rex, synthetic HOME, 100×30 and 60×24) is reused as supplied and I did not re-derive it; there is no hosted-CI or release evidence and none is claimed.