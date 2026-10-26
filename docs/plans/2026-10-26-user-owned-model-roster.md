# Plan: User-owned model roster across the process docs
Status: Agreed
Authorization: The user's verbatim instruction of 2026-10-26 — "remove any model selection for any rule, leaving it completely open... State that the user will select the model for every rule, in each session, or according to each mission. When I start any mission or task I will name the model name, effort and provider." — plus the working note `docs/HANDOFF-2026-10-26-user-owned-roster.md` and four decisions the user made in-session on 2026-10-26 (recorded under Review decisions).
Roster: coordinator: qoder/Qwen3.8-Max/unchanged (user set it with `/model` this session; requested = configured per session evidence; upstream identity unverified). Critics, both named by the user; wave 1 dispatched 2026-10-26 21:10 — critic A: pi 1.4.0 / river/deepseek-ai/DeepSeek-V4.1-Flash-1017 / thinking high; requested `river/deepseek-ai/DeepSeek-V4.1-Flash-1017:high`, configured per relay readback: provider `river`, model `deepseek-ai/DeepSeek-V4.1-Flash-1017`, read-only tool surface; upstream identity unverified (the critic attests it cannot self-verify from inside the sandbox). critic B: agy 1.4.7 / gemini-3.8-flash-high / High encoded in the model label, no separate effort option; requested `gemini-3.8-flash-high`, configured per relay and live process evidence (`--model gemini-3.8-flash-high --sandbox`); upstream identity unverified (same attestation limit). Implementer: not applicable — this is a documentation-only change; the correction work is coordinator authorship under the user's explicit in-session decisions (council §6: an explicit user instruction authorizes the exception to the usual workflow).
Reference: 18be0dc4ec5ea72e4ebd0fe1b14003c2639116ca
Risk and review: High (council §5) — this rewrites the workflow contract and the selection/permission rules, which are load-bearing for every future mission. Two user-named critics review this plan and, later, the final diff. Family disclosure (council §1): coordinator family Qwen (Alibaba); critic A family DeepSeek; critic B family Google (Gemini). No critic shares the coordinator's or another critic's family; overlap check passed, and the user's acceptance of this named set is recorded in Review decisions. Critic A's question: does the change fully satisfy the user's intent — no role in any live process doc names a provider, model, or effort as fixed/default/standing/inherited/preferred, and every loop start has open roster slots with an ask-once rule? Critic B's question: does the change introduce contradictions, stale references, broken cross-references, or unintended behaviour mandates (especially around commit/push authority and the live-vs-historical evidence boundary)?
Expected child tasks: 5 before corrections — 2 plan critics + coordinator correction work (the doc edits already exist; corrections from the review are the implementer-equivalent) + 2 final critics.

## Outcome

Every live process doc (`docs/process/`, plus the routing note in `AGENTS.md`) is model-agnostic. No role — coordinator, implementer, critic, follow-up worker — carries a fixed, default, preferred, standing, or inherited provider, model, or effort. When a mission starts (planning loop or implementation loop, on either the T3 or the OMP surface), the start prompt presents open roster slots — `<provider>/<model>/<effort>` per role — that the user fills in. A missing entry always means: ask once, with the live choices; never default, infer, or substitute. Roles keep binding behaviour (who may write code, who may review, who may commit); they no longer bind models.

## Current state

- The core rewrite already exists uncommitted in the working tree, across 8 files under `docs/process/` (council.md, planning-loop.md, implementation-loop.md, profiles/machine-profile.md, omp/README.md, omp/planning-loop.md, omp/implementation-loop.md, omp/herdr.md), as described in the handoff note. All four gates passed on that tree per the handoff; they will be re-run before landing.
- The coordinator reviewed the full diff on 2026-10-26: zero model IDs survive in `docs/process/`; every T3 start prompt carries the mission roster block; council §1 states "No role owns a model" with 7 selection rules; both plan templates carry a `Roster:` field; all anchor links resolve.
- Corrections from the user's four decisions were applied on 2026-10-26 (see Review decisions): the five stale "current migration" sentences fixed — including the two that read as a standing mandate to push every commit to `origin/main` (omp/planning-loop.md, omp/implementation-loop.md); both OMP start prompts now carry the full mission roster block; ~19 live uses of "Sol" renamed to "the coordinator" (council.md keeps one sentence declaring "Sol" a legacy label that appears in dated evidence records and names no model); the herdr.md idle-reporting warning is now vendor-neutral; `AGENTS.md` gained a header note that the user names the roster per mission.
- The working tree also contains the user's unrelated in-progress TUI work (modified: CHANGELOG.md, DEVELOPMENT.md, FULL_SCREEN_TUI.md, README.md, docs/plans/2026-10-26-tui-u4-why.md, skill_lens/tui/*; untracked: .path, docs/TUI_U4_WALKTHROUGH.md, docs/plans/2026-10-26-omp-native-asyncio-trial.md, docs/validation/*, skill_lens/tui/why.py, tests/test_tui_why.py). None of it may be staged, reverted, or stashed.
- Review wave 1 (plan wave) ran 2026-10-26 with both user-named critics; both returned `changes_required` converging on one blocker (project-profile.md §7's stale distinct-family mandate). Corrections were applied the same day: the blocker fix, both adopted convergent suggestions, and four adopted single-critic suggestions (dispositions under Review decisions). Pre/post wave-1 fingerprints were identical — no critic edited any file. A targeted follow-up wave on the corrections is the next step.

## Scope and boundaries

- Allowed paths for the final change commit (10): the 8 `docs/process/` files listed above, `docs/process/profiles/project-profile.md` (added by the wave-1 blocker: its §7 carried the retired distinct-family mandate), and `AGENTS.md`.
- This plan file is committed separately by the two-commit freeze procedure only.
- Excluded and untouched: `docs/archive/`, `docs/validation/`, historical `docs/plans/` records, `SKILL_LENS_SPECIFICATION.md`, product code, tests, and all of the user's TUI WIP. Historical documents keep their dated rosters — they are evidence of what past sessions ran and select nothing now.
- No model ID may be added to any live doc. Placeholder form is `<provider>/<model>/<effort>`.
- The `Roster:` field name stays identical across the T3 plan template, the OMP plan template, and council §1 rule 5.
- No commit, stage, or push without the user's explicit authorization; the final commit stages exactly the 10 allowed paths.

## Implementation steps

1. Core rewrite of the 8 `docs/process/` files — done (pre-existing in the working tree, per the handoff note).
2. Corrections from the user's four decisions — done (2026-10-26, this session).
3. Review wave: dispatch the two user-named critics as fresh read-only sessions with the council §2 verbatim guard and §4 report schema; capture `git status --porcelain` and SHA-256 fingerprints of the scoped files before and after; verify no critic edited anything.
4. Resolve findings: reproduce every reported defect before accepting it; batch corrections into one brief; two non-convergent rounds escalate to the user instead of a third wave.
5. Freeze this plan: `Status: Agreed`, commit only this file, record the full first-commit hash in `Reference:`, commit the provenance change.
6. Land: re-run the four gates on the final tree, stage exactly the 10 allowed paths, commit `docs(process): make model selection user-owned per mission`.
7. Record the execution receipt (expected vs actual launches, requested vs configured identity, elapsed time) appended to this plan.

## Acceptance

- No role in any live process doc names a provider, model, or effort as fixed, default, standing, inherited, or preferred; grep for historical model IDs (`gpt-6.1-sol`, `gemini-3.8-flash-high`, `minimax`, `space-bunny`) returns nothing in `docs/process/` and `AGENTS.md`.
- Every loop start (T3 planning, T3 implementation, OMP planning, OMP implementation, OMP direct entry) presents open roster slots and states the ask-once rule for missing entries.
- Both plan templates and council §1 rule 5 use the identical `Roster:` field.
- No live doc instructs pushing without explicit per-push user authorization.
- "Sol" appears in live docs only in council.md's legacy-label declaration; historical docs are untouched.
- All internal anchor links resolve.
- All four gates pass on the final tree: `uv run pytest --cov=skill_lens`, `uv run mypy`, `uv run ruff check .`, `uv run ruff format --check .`.
- Two independent critic reports received (plan wave and final wave), every in-scope blocker resolved with evidence, and no critic edits detected by fingerprints.
- The final commit stages exactly the 10 allowed paths; the user's TUI WIP remains untouched in the working tree.
- Execution receipt recorded in this plan.

## Review decisions

User decisions of 2026-10-26 (this session, answering the handoff's *Decisions still owed*):

1. **Family diversity** — keep the landed rule: the coordinator discloses each participant's model family, flags overlap, and the user accepts per mission. No hard distinct-family requirement is restored. This is the one real safety relaxation in the change, and it is now explicitly user-confirmed.
2. **Stale "current migration" sentences** — fix all of them (four were counted in the handoff; a fifth of the same kind was found at omp/implementation-loop.md §6 during review and fixed too). Push language now requires explicit per-push authorization with a user-named destination.
3. **OMP start prompts** — add the full mission roster block (coordinator + implementer + critics), symmetric with the T3 prompts.
4. **Surviving names** — rename "Sol" to "the coordinator" throughout live docs (historical records untouched); strip Antigravity/Grok from the herdr.md idle warning (now vendor-neutral); add the "user names the roster" note to `AGENTS.md`. The machine-profile provider-ID list stays as a capability snapshot ("not a suggestion") — the user did not choose to strip it.

Deliberate keeps (not defects):

- "Mini" in herdr.md's live-status paragraph and the Hermes app name in omp/README.md are historical trial/application references tied to linked evidence records; they select no model.
- Role *behaviour* rules stay closed (coordinator never writes product code; implementer never reviews/commits; critics never edit; one implementer per phase). Only *selection* was opened.

Critic findings and dispositions:

**Round 1 (plan wave, 2026-10-26; critic A = pi/DeepSeek V4.1 Flash 1017 thinking high, critic B = agy/Gemini 3.8 Flash High; both verdicts `changes_required`):**

- **Blocker, convergent (both critics) — reproduced, confirmed, fixed.** `docs/process/profiles/project-profile.md:168-169` still imposed "two critics from different model families" on high-risk work, contradicting council §1/§5 and decision 1; the handoff's file list had missed it. Fixed: §7 now requires two critics *named by the user*, with family disclosure, overlap flagging, and recorded acceptance, linking council §1/§5. The file joins the allowed paths (10 total).
- **Suggestion, convergent (both critics) — adopted.** `implementation-loop.md` Step 5 "satisfy family requirements" was a leftover of the retired hard rule; reworded to "disclose each reviewer's model family and record the user's acceptance (council §1)".
- **Suggestion (critic A) — adopted.** OMP direct entry's ask-once covered only the coordinator; widened to any role needed before the first dispatch, with a pointer to the loop-start roster blocks (omp/README.md).
- **Suggestion (critic A) — adopted.** omp/planning-loop.md §2 "Select workers/settings per session" had no subject and could read as coordinator selection; now "The user names workers/settings per session".
- **Suggestion (critic A) — adopted.** The AGENTS.md roster note now also points to `docs/process/omp/README.md` for the OMP surface, since council §1's ask-once names the T3-only live catalog.
- **Suggestion (critic B) — adopted in part.** The OMP plan template's `Roster:` placeholder was harmonized to "<user-named runtimes/models/settings per role; ...>", keeping OMP's runtime vocabulary; the field name itself was already identical in all three references and stays unchanged.
- **Suggestion (critic A) — adopted.** This plan's `Roster:` field now records the confirmed wave-1 identities (requested vs configured vs upstream-unverified) from relay readback.
- **Note (critic A) — out of scope, surfaced to the user.** `docs/TUI_U4_WALKTHROUGH.md:4` (the user's untracked TUI WIP) names a roster; it was not touched. If the "live process docs" scope is ever widened beyond `docs/process/` + `AGENTS.md`, that line needs the same treatment.
- **Delivery anomaly (receipt).** Critic A's pi turn finalized (`agent_end`/`agent_settled` events) and its complete report was captured within ~2 minutes, but the CLI process lingered, so the relay's 30m watchdog fired (status `timeout`, SIGTERM). The report is complete and accepted as round-1 evidence. Critic B ran clean (`completed`, exit 0, `readOnlyViolation: false`).

**Round 2 (targeted follow-up on the corrections, 2026-10-26; same user-named critics, fresh sessions, roster unchanged under council §1 rule 2):**

- **Critic B verdict: `pass`.** Zero blockers, zero suggestions; its CONCEDED field verifies the round-1 blocker resolved and every correction landed faithfully. Clean run (`completed`, exit 0, `readOnlyViolation: false`).
- **Critic A verdict: `changes_required` — one undisputed blocker, located in this plan document, not in the change files.** Two operative lines (the Scope bullet and Step 6) still said "9 allowed paths" while the enumeration, acceptance criterion, and disposition said 10; a literal landing could therefore have dropped the round-1 blocker fix (`project-profile.md`) or `AGENTS.md` from the commit. Reproduced and confirmed by the coordinator. Fixed under council §6 as administrative execution-record corrections: both lines now say 10. No disagreement existed at any point; the fix aligns the text with the already-agreed round-1 disposition.
- **Critic A suggestions — adopted.** (1) omp/README.md's ask-once pointer said "the loop start prompts below" but the roster blocks live in the two loop docs, not the README; it now names and links both. (2) planning-loop.md Step 3 item 2 now reads "waive no family disclosure-and-acceptance duty (council §1)", aligning with implementation-loop.md Step 5's recorded-acceptance wording.
- **Critic A verified the change itself clean:** all six round-1 dispositions landed as described; no live doc imposes any model/family/effort constraint beyond the disclosure-and-acceptance duty; all five loop starts carry open roster slots plus an ask-once rule; no historical model ID survives.
- **Identity disclosure (council §1 rule 3 / §4).** Critic A's self-attestation claimed a "Claude-family" model while the relay readback confirms configured identity `river` / `deepseek-ai/DeepSeek-V4.1-Flash-1017` (requested == configured; upstream unverified — an in-sandbox self-attestation is not evidence and is recorded as conflicting). Family labels for the wave: coordinator Qwen (Alibaba) per session configuration; critic A DeepSeek per catalog label (upstream unverified, conflicting self-attestation noted); critic B Google/Gemini (upstream unverified). Under either attestation reading, no critic shares a family label with the coordinator or the other critic.
- **Delivery anomaly (receipt, round 2).** Critic A's relay again hit its watchdog (15m) after a completed turn (`agent_end`/`agent_settled`; full report captured); critic B ran clean. Pre/post round-2 fingerprints identical — no critic edits in either wave.
- **Two-round rule.** Per council §5, no third broad wave was started. The round-2 corrections (plan numerals, README pointer, planning-loop wording) were accepted on 2026-10-26 by explicit user decision ("accept with my verification"): the coordinator showed grep evidence that every operative reference now says "10 allowed paths" (lines 23, 28, 37, 50) — the only surviving mention of "9 allowed paths" is the quoted disposition history above — and that the README pointer and planning-loop wording corrections landed as described. The same user decision authorized the freeze and the final 10-path commit; no push was authorized.
