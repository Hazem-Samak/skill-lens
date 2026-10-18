# Plan: demonstrate one complete Herdr development cycle

Status: Agreed
Surface: t3 (preparation and evidence review); herdr (the disposable live trial).
Authorization: The user agreed to simplify the remaining work to one small,
disposable end-to-end task using the chosen roles/models: "I agree with this,
let's start, how we can do it ?" (2026-10-18).
Reference: ad19c3115f518b8f10d1ab2ef23c04254196886b
Risk and review: High because this replaces pilot entry/acceptance requirements.
T3 preparation reviewers remain MiniMax/mcode xhigh and Pi/WorkBuddy DeepSeek high;
the previously accepted unverified-upstream-identity limitation remains explicit.
Expected child tasks: two preparation critics and two final handoff critics in T3;
inside Herdr, two planning critics, one Gemini implementer, two fresh final critics.

## Outcome

Demonstrate planning, independent review, implementation, verification and final
review through native Herdr, using a tiny Python task in a disposable Git repository.
Deliver the human one launch command and one coordinator prompt directly in chat.
T3 prepares and later inspects evidence; only the human starts real Herdr/Hermes.

## Current state

P01 remains unverified. Its capture contains both successful correlated model
calls and unexplained HTTP records. The observer investigation is stopped here.
Neither that capture nor the already passing product tests prove Herdr workflow
delivery. No workers or P02-P09 cases have been run. The original repository is
at 9a1e78c with pre-existing untracked `.path` to preserve.

## Scope and explicit amendment

This authorizes one separate practical trial. For this trial only, the cycle below
replaces the P01 capture/registration acceptance prerequisite and the requirement
to complete P01-P09 before trying the ordinary workflow. It uses direct native
Hermes startup without the temporary HTTP observer. Requested/configured routing
and a functioning conversation suffice for trial entry; packet-level correlation,
independent process-argv proof and upstream model identity are not trial gates.
Actual owned-session/pane identity, fresh conversation and model settings remain
required. Stale registration may use the prior one-shot checked repair; it is not
required to resume observer work. The new trial is not a retrospective P01 pass.

The earlier plans at 58d48cea, b99e212a, 6a038523 and a9bcda8b remain historical
authority for unaffected boundaries. P02-P09, restart/recovery experiments and
Phase C remain paused. A passing cycle proves only the demonstrated normal path;
it does not mark the full migration supported or change active process documents.
T3 will report the result and recommend any remaining minimal process adaptation.

Allowed repository edits: this plan; a new
`docs/validation/two-surface-orchestration/2026-10-17/implementation/single-cycle/`
record; and additive current-status pointers in setup.md and pilot.md.
No product/test/registry/process changes, installed-source changes, credentials,
configuration, new services, model substitutions or manipulation of live Herdr by
T3. Keep normal agent HOME/auth. Test commands alone use synthetic HOME/XDG.

## Trial

1. Freeze this amendment, then prepare a fresh directory under the existing
   approved pilot-artifacts root. Preserve all old captures and fixtures.
   The disposable checkout begins with `fixture.txt` containing exactly
   `pilot status: pending\n`. No implementation/test code is prewritten by Sol.
2. Human starts fresh Hermes inside `skill-lens-pilot-20261017`, using Sol high,
   `openai-codex`, command-local `HERMES_CODEX_BASE_URL=http://127.0.0.1:8787/chatgpt`,
   `--cli --ignore-rules --toolsets terminal,file --pass-session-id --in CHECKOUT`.
3. Hermes explicitly reads native `herdr --skill`, confirms inherited HERDR_ENV,
   actual pilot session and owned pane, current system-prompt session ID, fresh
   context and actual configured provider/model/reasoning. On uncertain identity,
   unexpected private context or settings mismatch, stop with the exact blocker.
4. Hermes writes a short plan for `status_reader.py:read_status(path) -> str` and
   `test_status_reader.py`. Coordinator-written plan/evidence are separate from
   Gemini's exclusive ownership of Python code/tests. Accept only exact UTF-8 contents
   `pilot status: pending\n` or `pilot status: complete\n`; return the status word,
   raise ValueError for other decoded contents, propagate I/O/Unicode errors,
   never write the input. No CLI or dependencies. Tests cover both valid values,
   malformed/empty input, missing file and preservation of input bytes.
5. Use two independent fresh native Pi critics in one submission wave, Qwen
   AnyModel high and DeepSeek WorkBuddy high, with their approved read-only tool
   controls, distinct processes/panes/empty session directories. Resolve evidenced
   blockers; freeze the fixture plan with a local plan commit plus reference commit.
6. Start Gemini/agy `gemini-3.8-flash-high --effort high --sandbox` in an owned
   shell pane. Only it creates the two code/test files. It may not delegate,
   review, commit or push. Sol inspects the actual diff and runs fixture tests
   with coverage >=90%, strict mypy on the module, Ruff lint and format check,
   using installed project tools and external caches. No installation is needed.
7. Two new Pi critics inspect the final target in a second parallel wave. Sol
   reproduces blockers and sends at most one coherent correction batch to Gemini;
   affected reviews are fresh. Two non-converging rounds stop for the human.
8. Sol accepts only complete token/target-bound reports, passing checks, allowed
   edits and resolved owned task activity. Commit the fixture result locally,
   retain full reports/checks/diff in external artifacts, and stop for T3 readback.

Fixture commits are disposable local evidence and are never pushed. This is an
explicit exception only for that new repository, not Skill Lens: every authorized
Skill Lens coordinator commit is immediately pushed and verified as before.

## Acceptance and preparation proof

Passing means one real native Herdr cycle with the exact roster, two fresh review
waves submitted before collection, Gemini-only code/test edits, complete matching
reports, current passing fixture gates, original-repository manifest equality,
unchanged fixture.txt and fixture code changes confined to the two allowed files.
Herdr idle/done alone is insufficient;
retain owned process readback showing task commands finished. Keep coordinator,
user resources and evidence; uncertain delivery/liveness stops rather than resends.
Do not deliberately create cancellation, restart, denied-write or stale-report
experiments. Unknown/wider permission requests stop without changing settings.

T3 preparation uses the existing planning/implementation/council rules: review the
complete plan and handoff, freeze before fixture preparation, run all four product
gates with external output, obtain final independent handoff review and verify the
allowed-file diff. No new observer code, helpers, test framework or runtime model
request is required. Final delivery is "trial prepared; human run pending".

## Review decisions

DeepSeek's supplied-snapshot completion passed with no blockers; its first task
ended without a verdict and is not approval. Its self-label included both council
models; T3 configuration identifies Pi/WorkBuddy DeepSeek high, upstream unverified.
MiniMax R1 accepted the narrowed scope and identified missing Surface declarations
and explicit frozen-reference verification. Both were reproduced and corrected;
the exact hash is filled after the two-commit freeze, before final handoff review.
Accepted small clarifications: native modes N/A, an actual readable diff artifact,
and separate coordinator plan/evidence versus Gemini code/test ownership.
No historical failure is waived as success; no full migration claim is made.
MiniMax's targeted R2 passed: both blockers resolved, no unresolved requirement
disagreement. Its native plan mode ended after saving the complete review rather
than emitting the requested final schema; the coordinator read and retained that
external review artifact, including the explicit pass and blocker dispositions.
T3 receipts corroborate MiniMax/mcode xhigh full-access/plan. No repository writes
by critics were found. The original R1 snapshot remains historical; a new snapshot
pins the revised agreed text. DeepSeek's unaffected behavior verdict is retained;
the added declarations/freeze gate do not change the reviewed task or workflow.
