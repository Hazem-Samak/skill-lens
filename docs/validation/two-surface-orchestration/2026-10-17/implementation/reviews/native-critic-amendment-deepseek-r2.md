I have all evidence needed. Round 2 targeted question: **Is my earlier concern (per-dispatch empty session dirs promised for both critics but DeepSeek using fixed dir) resolved?** 

**Yes.** The corrected draft:
- Line 14: explicitly gives **both** critics separate newly-empty per-dispatch session dirs
- Line 54: supplies the **full** DeepSeek native template, replacing only `pi-sessions` → `pi-critic-deepseek-<dispatch-token>/sessions`, retaining all provider/model/thinking/tool/context flags
- Line 48: Qwen uses a separate `pi-critic-qwen-<dispatch-token>/sessions`
- Line 59: distinct panes, distinct tokens/names, both-submit-before-collect
- Lines 69/73/100: still staged as **P02-pending runtime proof**, never assumed; independence is not overstated

Verified against installed help (all flags real), authorization (exact authorized pair), base §4.2/P02/P04 coherence, and staging (no premature adoption; setup.md:94 fixed path untouched; only 3 administrative diffs). No remaining blocker.

---

EFFECTIVE_MODEL
Provider/model: `m:minimax:MiniMax-M3.1-Flash-Preview:v:thinking` (mcode / MiniMax M3.1 Flash), the unchanged council first critic. Configured/requested council setting `thinkingEffort=xhigh` (base plan:59–60); actual executed effort not observable from inside → **unverified**. runtimeMode=full-access, interactionMode=plan. Confirmed only: executing on the m:minimax route under plan interaction with full-access provider mode. Upstream served identity/family **unverified** and never treated as execution proof.

VERDICT
pass

BLOCKERS
None. MiniMax's round-1 blocker is resolved. Evidence:
- **DeepSeek fixed path replaced.** setup.md:94 originally used `--session-dir /tmp/.../pilot-artifacts/pi-sessions` (fixed). Current draft line 54 supplies full DeepSeek template using `.../pi-critic-deepseek-<dispatch-token>/sessions`, retaining `--provider workbuddy --model deepseek-v4.1-flash --thinking high --tools read,grep,find,ls --no-mcp --no-extensions -e .../herdr-agent-state.ts --no-skills --no-context-files`. Only the storage dir changed.
- **Both critics get fresh empty dirs.** Line 14: "both pilot critics separate, newly empty per-dispatch session directories"; line 48 Qwen `pi-critic-qwen-<dispatch-token>/sessions`; line 54 DeepSeek `pi-critic-deepseek-<dispatch-token>/sessions` — distinct, tokenized, no resume/continue flags.
- **Topology.** Line 59: "two distinct available shell-pane IDs," different tokens/names/panes, "submit both briefs before collecting completion. Do not try to start two agents in one occupied pane."
- **Staged, not assumed.** Lines 69/73/100 keep independence as P02 runtime proof; "The shared executable proves neither success nor failure of independence."
- **Flags real.** `pi --help`: `--session-dir` (:30), `--no-extensions/-ne` explicit `-e` still works (:44), `--no-mcp` (:45), `--no-skills` (:47), `--no-context-files/-nc` (:53), `--thinking high` and `--tools read,grep,find,ls` allowlist example.
- **Authorized pair.** Reliable-model-authorization: `anymodel/qwen/qwen3.8-max`; command `--provider anymodel --model qwen/qwen3.8-max --thinking high` matches; migration council remains MiniMax/mcode xhigh + Pi/WorkBuddy DeepSeek high; Grok/XKiro excluded.
- **P04 coherence.** No-write Pi mappings cannot emit a temp-Markdown fallback; draft correctly requires complete native recovery or unavailable/stop and scopes this as a consequence of tool exclusions, not a universal removal of base §4.2 fallback for other kinds — not a silent P04 waiver.
- **Staging clean.** HEAD b6d5a172 (matches); base 58d48ce… is a valid frozen commit; draft untracked; `.path` 0 bytes untracked; only 3 administrative diffs (setup.md, acceptance.md, preflight-receipt.json) recording already-granted approval with `nativeCritic1AmendmentStatus: ...review_and_adoption_pending` — no native-argument change; setup.md:94 fixed path intentionally untouched pre-freeze; §6 restricts pre-adoption edits to draft+evidence and applies Qwen+both templates only "under both freezes."

SUGGESTIONS (nonblocking)
1. Line 59 correctly states two distinct panes; optionally also note P02 must record both pane IDs and prove distinctness at runtime.
2. §7 line 97 requires "both amendment critics pass" — for round 2 that holds only once this and the DeepSeek round-2 report both land PASS; ensure adjudication records both.
3. Keep the per-run gate labeling ("IN THAT RUN") distinct from base's varying format counts (184/187/197) for later auditors.

FILES_AT_RISK
- `docs/plans/2026-10-17-herdr-native-pilot-critic-amendment.md` (untracked, SHA-256 `011648051eb7…d1c3`, unchanged by this review) — the only pre-adoption editable file.
- Post-freeze allow-list edits: `…/setup.md` (esp. :94 DeepSeek template), `…/acceptance.md`, `…/pilot.md`, `…/implementation/preflight-receipt.json`, `…/implementation/human-pilot-brief.md`.
- Read-only machine ref embedded in executable text: `/Users/corvette/.pi/agent/extensions/herdr-agent-state.ts` — retention via `-e` mandatory; must not be edited/dropped.
- Historical Grok research files — must not leak into executable instructions (amendment:92 forbids); no `.path`/product/test/registry change.

CONCEDED
Verified current draft SHA-256 `011648051eb7cd77a3b5d9fa4100cf1c9b9facbf5a8471d19b761132739ad1c3`, HEAD b6d5a172, base commit resolve, draft untracked, `.path` 0 bytes untracked. Confirmed both-critic storage delta now explicit and complete: Qwen `pi-critic-qwen-<dispatch-token>/sessions` and DeepSeek `pi-critic-deepseek-<dispatch-token>/sessions`, replacing the fixed `pilot-artifacts/pi-sessions`, retaining all original provider/model/thinking/tool/context flags. Confirmed two distinct panes, distinct tokens/names, both-submit-before-collect, and that independence remains a P02 runtime-proof obligation, not a claimed guarantee. Confirmed installed Pi help backs every flag in both templates; AnyModel qwen/qwen3.8-max high is exactly one authorized pair from the closed eleven-list; Grok/XKiro excluded with no fallback. Confirmed P04 write-excluded collapse is a coherent consequence, not a silent waiver, with base §4.2 fallback preserved for other kinds. Confirmed staging: only administrative diffs present, no premature adoption, `.path` preserved, full-pilot acceptance (P01–P09 pending) unwaived. This verdict approves draft **content** for later user adoption only — it approves no runtime, no freeze, no served-identity, and waives no pilot evidence.
