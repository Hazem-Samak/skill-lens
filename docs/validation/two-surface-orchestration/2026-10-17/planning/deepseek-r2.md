Confirmed: the shared council text embeds `runtimeMode`/`interactionMode` in the schema (council.md:97-98, 127, 140, 151) and the loops carry them at planning-loop.md:62/106 and implementation-loop.md:46/94. This is strong evidence for the F5b/P10 semantic-boundary resolution and against a blanket grep ban. Also confirmed: no plan file contains `Surface:`, and there are 9 plans. I have enough to adjudicate.

---

EFFECTIVE_MODEL: Own target only. Requested: MiniMax M3.1 Flash Preview, `m:minimax:MiniMax-M3.1-Flash-Preview:v:thinking`, thinkingEffort=xhigh via mcode; coordinator T3 readback reports permissionMode=bypassPermissions, `_t3/session-mode=plan`, runtimeMode full-access, interactionMode plan. This is **configuration evidence**, not upstream-family proof: I did not call `orchestrator_capabilities`/`t3_thread_configuration` myself, did not probe credentials, and cannot confirm the served upstream model/family from an alias string. Family corroborated only by repo text (council.md listing "MCode (MiniMax M3.1 Flash)"). For the counterpart: DeepSeek target workbuddy/deepseek-v4.1-flash is configured at thinking=high because **WorkBuddy's live options stop at high**, unlike Pi/other routes that go to max; I take the coordinator's readback as configuration evidence, not family proof. My own settings (thinkingEffort, session-mode) remain **unverified at the upstream level**.

VERDICT: pass

BLOCKERS: none. The two candidate clauses I initially read as blocker-grade are now resolved inside the candidate itself, so nothing remains in-scope blocking *adoption of the proposal*:

- Prior F5b tension (§8.1 blanket bans vs the schema/loop text that must retain `runtimeMode`/`interactionMode`/`hasPendingChildRuns`) is **resolved by candidate P10**: it explicitly replaces "blanket forbidden-word grep" with "semantic placement of mechanics," keeps shared guard byte-identical, keeps "T3 fields retain meaning," and lets Herdr mark T3-only modes N/A. Verified against the live tree: `runtimeMode`/`interactionMode` are embedded in the required `modes` component (council.md:127,140,151) and required in loop text (planning-loop.md:62,106; implementation-loop.md:46,94). Any replacement wording must keep that schema block and those loop lines legal; P10 already does.
- Prior F2/P5 terminality-vs-acceptance is **resolved by candidate P5**: `succeeded/failed/interrupted/unknown outcome bookkeeping` is explicitly separated from coordinator acceptance; `idle/done` is "only UI readiness"; stop-or-fail-closed bounded to task-owned resources; Ctrl+C/pane-close "alone is not termination proof"; coordinator pane and user resources exempt. Minimal replacement wording if tightening is wanted: "An `interrupted`/`cancelled`/`idle`/`done` observation is never acceptance and never proves task-owned background work stopped."

F6 mandatory profile pinning is likewise **resolved by P7/P3/P11**: no mandatory per-profile hash or amendment per factual version bump; only execution/permission-contract changes re-freeze; optional blob hash is evidence only. No blocker.

SUGGESTIONS (P1–P12):
- P1 ACCEPT. Preserves D1–D3, fixed user choices, byte-identical guard; one-surface-per-task; no new framework.
- P2 ACCEPT. Correct scope, `Surface: t3` migration plan under existing loop, unrelated artifacts untouched, no freeze here.
- P3 ACCEPT. `Surface:` fixed at freeze, echoed in receipt, changes via amendment; legacy plans not edited, explicit mechanics/receipts resolve, otherwise ask once. Verified: none of the 9 `docs/plans/` files contains `Surface:`, so a documented resolution rule is genuinely needed — non-blocking polish if surfaced later.
- P4 ACCEPT. Token+fingerprint binding, fresh sessions, no imported critic context, no silent serial, inspect-don't-resend, tokens not claimed as idempotency keys. Directly answers F1/B2.
- P5 ACCEPT. See blocker note.
- P6 ACCEPT. Per-role kind verification, N/A for T3-only fields on Herdr, requested/configured/confirmed-unverified kept distinct, no alias rewrite from a banner. Answers F4.
- P7 ACCEPT. Freeze-before-setup-before-pilot; pilot bounds inside the plan; failed pilot leaves T3 available and Herdr limited. Correctly resolves "pilot-before-freeze" ordering.
- P8 ACCEPT. Synthetic-only matrix, includes agy (c), cancel/false-settle/ambiguous-delivery (e,f), detach/restart/reboot from outside the driving pane (g), opencode fallback (b), cmux cleanup (h). Add-later optional kinds need focused verification, not a wholesale re-pilot — right proportionality.
- P9 ACCEPT. Readiness limited to tested kinds/roles; one bounded real trial; supported status only after independently accepted trial. This resolves "first-use activation circularity" without circularity.
- P10 ACCEPT. Central repair.
- P11 ACCEPT. Repo rollback ≠ machine revert; setup receipt; no blind shared-config overwrite. Answers F5d.
- P12 ACCEPT. Choices deferred to the authorized pilot; consensus ≠ approval.
- Optional simplification: P12's notification-polish deferral and P3's legacy-resolution could be one combined "deferred polish" paragraph — cosmetic only.

AGREED CORE: staged, proportional adoption of P1–P12 as the revision of the original; keep T3 + cmux/Herdr; freeze an authorized High-risk `Surface: t3` migration plan via the existing two-commit procedure before any machine setup; run the P8 synthetic pilot and P9 bounded trial as prerequisites to declaring Herdr supported; never weaken the T3 contract, guard, or schemas. Separate **document-proposal agreement** (this report: all three can recommend the candidate) from **runtime acceptance** (not established — Herdr is unverified until the authorized pilot and trial; "supported" is a post-trial status, not a debate output).

UNRESOLVED OBJECTIONS: none blocking. One disclosed residual disagreement is narrowed, not dead: the coordinator frames the historical Hermes `-900k` alias as something a configured proxy "may legitimately accept" and counsels recording both requested/configured and evidenced upstream route rather than renaming from docs alone — I agree renaming from documentation is unsafe; the residual divergence is only whether P4/P6 should additionally require the *upstream route* be evidenced (else hard `unverified`) rather than merely recorded. I read P6 as already satisfying this ("do not infer upstream identity… retain existing user-accepted unverified-family path"). Not blocking. Per instructions, no third wave, no consensus fabrication, no request for plan approval.

FILES_AT_RISK: read-only inspection only; no files edited. Authority docs: `/tmp/.../original-proposal.md`, `round1-brief.md`, `coordinator-findings.md`, `minimax-r1.md`, `deepseek-r1.md`, `round2-candidate.md`. Live contract checks: `docs/process/council.md` (62-151), `docs/process/planning-loop.md` (62,106), `docs/process/implementation-loop.md` (46,94). Repo state verified clean at HEAD `2d9637054aea969fb2ec575cf28e48ed0ec1a800`, pre-existing untracked `.path` untouched; `docs/plans/` contains 9 files, none with `Surface:`. Allowed future targets per P2 unchanged from the original list.

CONCEDED:
- I narrow my own earlier instinct to read P10/§8.1 as a fresh blocker: once P10's semantic-placement wording is adopted, the grep conflict is repaired inside the candidate, so it does not block recommending adoption.
- I narrow the F2/F5 terminality framing to task-owned resources plus preserved user work, coordinator pane exempt — the coordinator's "task-owned, not every machine process" bound is correct and I withdraw the stronger all-process reading.
- I accept the coordinator's correction that the two-critic wave and coordinator-drives-Herdr were already in §8.2 (items 2,5); my blocker concerns narrow to agy implementer coverage plus cancel/false-settle negatives and per-capability readiness, not a wholesale pilot omission.
- I withdraw any implication that the `-900k` alias must be removed based on docs alone; I keep only the narrower requirement that upstream route identity be recorded and left `unverified` unless evidenced.
- I accept that MiniMax named-pair use here is authorized for this review without amending the permanent roster, and that a `Deferred` catalog listing is not by itself an in-scope blocker to this debate.
