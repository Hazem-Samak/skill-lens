I have completed a thorough review of the exact draft (verified SHA256 `bf7d0ab7...`, HEAD `2d963705...`), all three governing process docs, the prior debate evidence including final-adjudication.md, the D1–D3 definitions, the gate receipts under `/tmp`, and the working-tree state.

---

# FORMAL PLAN REVIEW — ROUND 1

**EFFECTIVE_MODEL:** workbuddy/deepseek-v4.1-flash via `pi`, configured `thinking=high`; `runtimeMode=full-access`, `interactionMode=plan`; requested by this session's delegated review target. Evidence channel: **configured** from the dispatching task/receipt (`instanceId=pi`, model `workbuddy/deepseek-v4.1-flash`, `options=[{thinking:high}]`). **Upstream family/identity unverified** — no provider banner observed; configured-only. My own target is DeepSeek/Pi, **not** MiniMax; I have not copied the counterpart's identity. I do not treat my configured route as proof of upstream served family, and DeepSeek self-labels are known unreliable (matches the R2 mislabel noted in the draft).

**VERDICT:** pass

The draft is a sufficient, coherent, proportional implementation contract for *planning review*. It honors D1–D3, does not bootstrap itself, does not assert unsafe/unbounded permissions, and does not claim empirical success it has not measured. My axis (operational behavior/acceptance) finds no blocker requiring changes before the freeze step.

**BLOCKERS:** None.

I actively checked each operational sub-axis and none produced a concrete conflicting contract:

- **Herdr entry/control boundary** (lines ~140, 165, 238–241): control commands are constrained to a Herdr pane with `HERDR_ENV=1`; the T3 observer "reads evidence and coordinates the migration, not neighboring live panes." This directly matches the recalled `--skill` fact that control requires `HERDR_ENV=1`, and it closes the exact hole the brief warns about (a T3 session controlling Herdr from outside a pane). §4.4 restates "does not authorize this T3 session to control Herdr from outside a Herdr pane." Consistent, bounded.
- **Synthetic isolation vs CLI auth** (P02/P04, Phase B): fixtures must stay in the synthetic checkout, CLI auth may use existing authorized credentials, and "Record which native session controls establish that separation; if it cannot be established, stop." This is honest: it does not assert that using real credentials is the same as isolation. No unsafe equivalence claimed.
- **Executable pilot ordering** (Phase A→B→C→D): freeze/baseline precedes bounded setup/synthetic pilot, which precedes documentation migration, which precedes final acceptance. This fixes the ordering defect flagged in final-adjudication.md ("both first-round sequences had setup/pilot before authorized freeze"). §1 and §5 keep *setup, activation, and real task* outside drafting.
- **Token/turn identity** (§4.2): per-dispatch unique token + exact target revision; acceptance only after both match; explicit "Tokens do not provide server-side idempotency"; "prompt/wait state does not identify individual turns" recorded as a limit; P06 exercises false-settle/ambiguous delivery and requires proving rejection guards can fail. This correctly treats UI readiness (idle/done) as distinct from task identity and acceptance.
- **Bounded cancellation/background work** (§4.3, P07): requires integration evidence *plus bounded owned process/job readback*; "Ctrl+C, a closed pane, a report, or a settled UI alone is insufficient"; unresolved liveness blocks acceptance and replacement; "Do not demand control of every machine process." This is the correction final-adjudication.md demanded (interrupted = bookkeeping, not acceptance). Bounded, not overreaching.
- **Permissions/remaining decisions** (§4.4): native role envelope fixed; native settings derived from installed help + controlled disposable probes; once-per-session user role-mapping approval before real work; deny-write probe "proves its tested boundary, not an adversarial sandbox"; wider persistent permission/trust/global default prohibited as a "syntax correction." Remaining decisions (session names/startup, role mapping) are explicitly named as user-approved future steps, not silently assumed.
- **Failure cases/rollback** (§8): revert restores T3 authority but does not roll back integrations/proxy; requires retaining sanitized setup evidence; "stop with T3 available rather than partially activate Herdr"; missing evidence ⇒ unavailable/unverified. Honest and bounded.

**Self-bootstrapping check:** The draft does not approve or freeze itself. `Status: Draft`, `Reference: pending`, §9 states exact-file reviews are pending and "No claim of unanimous review applies until both actual reports and coordinator adjudication support the final operative text," and ends "Stop after drafting/review." §6 Phase A requires explicit freeze authorization and forbids inferring it from a commit. No exit-plan/approval tool use is prescribed. Good.

**Unresolved-choice deception check:** I found none that makes the draft deceptive. Requirement *choices* are resolved (architecture, scope, acceptance, role set, risk level High, gate set). What remains open is explicitly labeled as **future implementation authorization, empirical pilot results, or user-approved session parameters** — exactly the separation the brief asks for. §5's machine-action bounds are conditional ("Nothing here is activated by drafting"), §6 is "(not started)", §9 defers the production trial. This is correct, not deceptive.

**Gate evidence cross-check (draft §7 vs actual):** I read the receipts — ruff-check exit 0 ("All checks passed!"), ruff-format exit 0 ("182 files already formatted"), mypy exit 0 ("Success: no issues found in 37 source files"), pytest exit 0 (1048 passed, 1 skipped; coverage **91.11%** ≥ required 90.0%). The draft's §7 gates and the brief's stated metrics agree. The draft correctly states these "do not prove the future pilot or migration."

**CONCEDED:** As a fresh independent reviewer, I have no prior-round positions to narrow. Relative to the earlier debate, I expressly decline to reopen the architecture, and I do not raise the rejected items (mandatory profile hashes, blanket grep bans, automatic alias rename, silent serial fallback, all-kinds certification). I agree with final-adjudication.md that "interrupted is valid terminal bookkeeping, not acceptance" and require no change to that disposition.

**SUGGESTIONS (nonblocking):**
1. §7 line 321 requires the shared guard "byte-identical to the baseline," but the draft references the guard rather than embedding it (bumping that risk). Since the operative guard lives in council.md and only its *placement* moves, consider adding a one-line pointer in §7 to the exact baseline source of the guard text (council.md §2 block) so the byte-identity check has a named comparator without a duplicate paste. This is clarity only; not required before freeze.
2. §6 Phase C step 3 assigns `surfaces/herdr.md` content "from pilot results"; since pilot viability may be partial (P01/P03/P05 can fail), consider one clause noting the Herdr profile may be written as **observed-and-limited** if some P-cases are `unverified`. The draft already implies this ("capability readiness from pilot results," "missing evidence means unavailable/unverified"), so this is phrasing only.
3. The `docs/process/surfaces/` directory does not yet exist (confirmed MISS) — correct as a future new path; no action, noted only so the implementer does not treat it as a stale link.

**FILES_AT_RISK (allow-list implicated; no writes performed by me):**
- `docs/plans/2026-10-17-two-surface-orchestration.md` (this draft; unchanged by me)
- `docs/process/council.md`, `docs/process/planning-loop.md`, `docs/process/implementation-loop.md`
- `docs/process/surfaces/t3.md`, `docs/process/surfaces/herdr.md` (future new)
- `docs/process/profiles/machine-profile.md`
- `docs/validation/two-surface-orchestration/2026-10-17/{setup,pilot,acceptance}.md`, `.../implementation/**`
- `docs/archive/orca-process-2026-10-10/README.md` (optional pointer)
- Pre-existing untracked `.path`: **untouched**, as required.

*Review-only. No files written, no delegation, no machine actions, no exit-plan tool. Verdict pass is my exact-file opinion for planning review only; it carries no implementation or freeze authorization.*
