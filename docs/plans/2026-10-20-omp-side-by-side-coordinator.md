# Plan: OMP coordinator alongside T3 Code

Status: Agreed
Authorization: User, 2026-10-20, explicitly requests completing the coordinator migration quickly: OMP replaces Hermes, Sol 6.1 coordinates implementers/reviewers, OMP has its own planning and implementation loops, and T3 Code remains active, not archived. Sol drafts, creates and checks this documentation migration, helped by one reviewer: OpenCode MiniMax M3.1 Flash Free. This explicitly replaces the old two-critic/Antigravity execution requirement for this migration only.
Reference: 216cea31cc0ac1c0ad8b1557441bf59aec141031
Surface: omp; t3 remains independently active.
Risk and review: High (workflow contract), with the user's explicit one-reviewer exception for this bounded migration. Use opencode/minimax-m3.1-flash-free, default model settings, fresh read-only plan and final review sessions. Requested/configured model identity is evidence, not independent upstream identity proof. No substitute without asking.
Expected child tasks: two Sol documentation-author tasks for disjoint files, one OpenCode plan review, one fresh OpenCode final review; corrections only if needed. Sol owns verification and commits.

## Outcome

Opening T3 Code uses the existing T3 workflow. Opening OMP uses an OMP-specific coordinator entry point and planning/implementation loops. OMP's coordinator is GPT-6.1 Sol and dispatches other implementers and reviewers using the session's authorized runtime/model choices. Hermes is no longer the current alternative coordinator. Neither application is archived, uninstalled or reconfigured.

## Current state

- Main at ff58deab6c57760edc6d1489f74e15c76a973959. Preserve pre-existing untracked `.path` and the 2026-10-19 coordinator draft.
- Existing docs/process/{planning-loop,implementation-loop,council}.md are active T3-specific documents; preserve their operative rules and add only surface-routing notices.
- The 2026-10-19 Herdr/OMP draft has no frozen reference and proposed changing shared T3 role policy. This new plan supersedes that proposal: separate workflows, no shared T3 roster rewrite, no Herdr prerequisite.
- Installed OMP 18.12.3 help supports --model, --cwd, --no-prewalk, @file input and native task delegation. `omp models find gpt-6.1-sol` lists openai-codex/gpt-6.1-sol. A fresh `omp --model openai-codex/gpt-6.1-sol --no-prewalk --no-extensions --no-skills --no-rules --no-tools --no-session --no-title -p` smoke returned exactly `OMP_SOL_COORDINATOR_OK` (exit 0, 3.35 seconds). Startup documentation uses --thinking high, the existing coordinator default. This supersedes the old missing-catalog observation, not a claim of independently verified upstream model identity.
- OpenCode 2.0.32 lists opencode/minimax-m3.1-flash-free. Its installed help supports run --model --agent --format and models without a provider positional argument.

## Scope and boundaries

Allowed paths:
- This plan and docs/validation/omp-coordinator/2026-10-20/{acceptance.md,plan-review.txt,final-review.txt}.
- New docs/process/omp/{README.md,planning-loop.md,implementation-loop.md}.
- Additive routing notices only in docs/process/{planning-loop.md,implementation-loop.md,council.md}.
- Additive status notice only in docs/validation/two-surface-orchestration/2026-10-17/implementation/single-cycle/README.md. Leave the pre-existing 2026-10-19 draft byte-for-byte unchanged and untracked; this tracked plan explicitly supersedes its entire proposed replacement contract.

No product code/tests, AGENTS.md, registry, dependencies, provider/authentication settings, credentials, installed packages, services, Herdr panes, historical report bodies or T3 operative policy changes. No U4 or release work. No proxy, Hermes session repair, observer, or P01-P09 trial. Start OMP directly; Herdr is not a dependency. Existing historical trial records remain historical, not accepted OMP proof.

## Implementation steps

1. Sol drafts this bounded plan. Obtain one read-only review from the exact user-selected free MiniMax model through OpenCode. Resolve in-scope blockers and freeze with the standard plan-only commit followed by a reference-only commit. Push each authorized commit with `git push origin main`; verify `git rev-parse HEAD`, `git rev-parse origin/main` and `git ls-remote origin refs/heads/main` agree. The standing delivery source is docs/plans/2026-10-17-two-surface-orchestration.md lines 13–16, citing the U2 authorization; this plan makes the delivery procedure explicit rather than relying on that pointer.
2. First establish the four-gate baseline; pre-existing failures are reported, not silently fixed. In parallel, two Sol documentation authors create disjoint files: author A owns the three new docs/process/omp files; author B owns notices in the three existing docs/process loop/council files and the single-cycle README. Request model openai-codex/gpt-6.1-sol and record configured identity separately from independently unverified upstream identity. Authors edit only; they do not run gates/formatters, delegate, review, commit or push. Stage only this plan at freeze; at implementation stage only the seven enumerated workflow/notice files and the three enumerated validation files. Never stage `.path`, the old draft, or any other untracked user work.
3. OMP README defines surface selection, fixed Sol model, session-selected workers, role separation, read-only review precautions, actual process completion/report checks, file ownership, checkout isolation and the absence of a sandbox guarantee. Include a working installed-help-backed startup command and prompts; never inherit T3-only API requirements.
4. OMP loops preserve source inspection, authorized scope, frozen plans with exact full hashes, meaningful acceptance, four project gates, independent review, correction and sole-coordinator acceptance/commit. Product code remains delegated to session-selected implementers; Sol may write process documentation for this migration. Select worker settings when needed, record actual identity/evidence and stop on unavailable choices rather than substitute. Keep one reviewer for this migration; future review follows risk (normal one, high two independent reviewers unless explicitly authorized otherwise).
5. Verify the routing links and startup flags. The exact selected reviewer route is an OMP bash tool invoking the installed OpenCode relay, which launches `opencode run --model opencode/minimax-m3.1-flash-free --agent plan --format json` with a 10-minute relay timeout, no --auto and no --pure (unsupported in OpenCode 2.0.32). Read its external result.json and complete finalMessage, require exit 0 and an actual verdict, and retain the report in the named validation record. This is OMP-orchestrated external CLI delegation, not OMP-native task delegation and not the different OpenRouter MiniMax route. No OMP setting change is required; if one becomes necessary, stop and ask. That proves this selected reviewer route, not every possible implementer provider. Run all four project gates on the final tree, obtain a fresh review by the same MiniMax model, resolve blockers, record evidence and commit/push the bounded migration.

## Acceptance

- T3 stays active: existing loop/council bodies are unchanged except routing notices; no T3 archive or removal.
- OMP users have direct entry instructions plus complete planning and implementation loops, using Sol gpt-6.1-sol, with no Hermes/Herdr/T3-only tool prerequisites.
- Other implementers/reviewers are selected per session and dispatched through tools actually available on OMP; example OpenCode review uses the exact discovered free model. Reports distinguish actual observed completion from requested identity.
- Reviewers receive the existing verbatim read-only guard. No hard-sandbox claim. Preserve unexpected/user edits; never blindly restore.
- Concurrency uses disjoint file ownership or separate checkouts; the same branch is not concurrently modified by T3 and OMP.
- Plan freeze precedes workflow edits. All affected relative links resolve. Startup is checked with installed help; the selected worker route actually completes. Unexercised provider routes are not claimed tested.
- pytest --cov=skill_lens, mypy, ruff check ., ruff format --check . pass. No new permanent tests for document wiring.
- One plan and one final review by the user-selected MiniMax model, blockers resolved, no active child work, concise acceptance receipt, focused commits pushed and verified.

## Review decisions

MiniMax plan R1: accepted the route-ambiguity finding and pinned the external OpenCode CLI/relay route, flags, timeout and result evidence. Accepted the untracked-draft finding: the old draft is now explicitly excluded from all edits and staging. The missing-standing-instruction claim is rejected: docs/plans/2026-10-17-two-surface-orchestration.md lines 13–16 already cite it; nevertheless the exact main/origin push and equality procedure is now stated directly. Accepted compact clarifications for baseline checks, child ownership and startup identity. Baseline passed: 1082 tests, one filesystem-dependent skip, coverage 91.16%, mypy clean, Ruff lint/format clean. The user-selected named pair is Sol/OpenAI and OpenCode MiniMax; upstream identity behind the selected alias remains unverified, not a verified-family claim. The user's latest instruction explicitly authorizes this named pair and one reviewer for this migration. This does not silently waive product safety or the four gates.

MiniMax targeted plan R2 passed with no blockers (OpenCode session ses_ea9e43356ffeIkWeErXWRZnaha). The unsupported --pure observation is grounded in the first failed launch's explicit CLI error, not inferred from help. All plan blockers are resolved before freeze; full reports are retained in the execution record.
