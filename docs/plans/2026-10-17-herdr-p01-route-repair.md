# Plan: repair the P01 coordinator launch

Status: Agreed — bounded repair authorized; live P01 remains pending
Authorization: User, 2026-10-17: "ok fix the remaining issues please, authorized".
Reference: Pending two-commit freeze.
Risk and review: High, because the pilot execution contract changes. MiniMax/mcode
xhigh reviews authorization and boundaries; Pi/WorkBuddy DeepSeek high reviews
behavior and proof. Their upstream identities remain unverified under the previously
accepted named-pair policy. The earlier DeepSeek waiver does not apply here.
Expected child tasks: two planning critics and two final critics. No product code or
tests are planned, so no implementer dispatch is needed. Gemini remains the sole
product-code/test implementer if a source change becomes necessary.

## Outcome

Give the human a working, direct Hermes launch for a fresh P01-only retry, using
the approved Sol model and existing authenticated local Caveman proxy. Resolve or
expose stale Herdr registration using Herdr's existing checked reporting operation.
Actual P01 acceptance still requires a genuine human-started Herdr session.

This amends only the coordinator entry procedure in the frozen base plan
`2026-10-17-two-surface-orchestration.md` @
`58d48cea483804b22767b381c6edd8274fe6ad44` and the setup/handoff derived from it.
The critic amendment @ `b99e212a55b20757eeda8605db4edcc59aad6107` stays operative.

## Verified current state

- The original coordinator attempt failed fresh-context isolation. The user's
  diagnostic retry subsequently passed that check with `--ignore-rules --toolsets
  terminal,file`, but reported HTTP 401 through `/w/hermes/v1/chat/completions`.
  Those are user-supplied historical results; the named temporary evidence is no
  longer present and must not be represented as newly inspected.
- Caveman's native integration replaced the former `openai-codex` provider and
  direct Codex URL with `custom` and `/w/hermes/v1`. Installed Hermes treats that
  loopback custom route as chat completions, despite persisted `codex_responses`.
- Caveman already provides `/chatgpt` for Codex subscription traffic. With the
  existing Hermes credential, authenticated `GET /chatgpt/models` returned 200.
- The backend rejects `gpt-6.1-sol-900k` with HTTP 400: "The 'gpt-6.1-sol-900k'
  model is not supported when using Codex with a ChatGPT account."
- An explicit `openai-codex` runtime at `http://127.0.0.1:8787/chatgpt`, requesting
  `gpt-6.1-sol` with high reasoning, returned HTTP
  200, `response.completed`, response model `gpt-6.1-sol`, and the expected exact
  reply `ROUTE_OK`. This is a routing smoke check, not proof of upstream weights,
  context capacity, Hermes interactive behavior, or Herdr readiness.
- Herdr's Hermes integration has source marker `HERDR_INTEGRATION_VERSION=5`
  (`__init__.py:4`; its plugin manifest separately says version 1.0), is enabled,
  and passes native
  `hermes plugins doctor herdr-agent-state`. Both Hermes hooks supply platform and
  session ID. Its reporting subprocess hides nonzero exits and exceptions; the
  historical stale-record cause remains unproved. Do not patch it by guesswork.
  These are current coordinator source/config/doctor observations, not recovered
  historical pilot artifacts. The source's one-second timeout, swallowed exit
  errors, and missing pane-environment early return are possible causes only.
- The earlier `/tmp/skill-lens-herdr-execution-20261017-cg7iv351` directory is gone.

## Scope and boundaries

Allowed repository changes: this plan and a new append-only P01 repair record under
`docs/validation/two-surface-orchestration/2026-10-17/implementation/p01-repair/`.
Add a clear current-status pointer to setup.md and pilot.md; retain historical text.
Leave `.path`, product code/tests, process docs, frozen prior plans, and older evidence
untouched. No global credentials, provider settings, plugin source, proxy service,
memory, or shell configuration changes. No new service or API key. No direct route
fallback. Do not run Herdr live-control commands from T3 or fabricate `HERDR_ENV`.

The model identifier changes explicitly from the rejected `gpt-6.1-sol-900k` to
`gpt-6.1-sol` under the current repair authorization. This is a new Hermes mapping,
not a claim that the previous Hermes mapping already approved this identifier.
It stays within the user's named reliable Sol model choice. It amends base §5's
"without printing secrets or changing a model alias" restriction for this exact
correction. No 900k context guarantee is carried forward.
The existing proxy's subscription endpoint replaces its incompatible API-key
endpoint. User authorization to repair the remaining issues covers this bounded
correction; it does not authorize model-family or reviewer substitutions.

## Implementation

1. Freeze this reviewed amendment before changing the pilot procedure.
2. Prepare a new exclusively-created temporary fixture root. Explicitly create
   `<new-fixture-root>/synthetic-checkout/` and place `fixture.txt` inside that
   directory. Verify both exist before handing over the launch command. Record
   the full paths, original repository HEAD/status/fingerprint, and the file containing exactly
   `pilot status: pending\n` with SHA256
   `462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e`.
   Provide empty pilot-artifacts, pilot-home, and pilot-xdg directories. HOME/XDG
   directories are for command-local **fixture/product test commands only**;
   Hermes keeps its normal HOME and authentication. Do not export fake HOME/XDG
   for the agent process. `--in` sets its working directory, not filesystem
   containment. Fresh-context proof is separate from HOME confinement. Do not
   reconstruct or overwrite vanished historical evidence.
3. Record a P01-only brief and this direct human-operated command, substituting
   only the newly recorded fixture path:

   ```bash
   test "${HERDR_ENV:-}" = 1 &&
   HERMES_CODEX_BASE_URL=http://127.0.0.1:8787/chatgpt \
   hermes --cli --ignore-rules --toolsets terminal,file \
     --provider openai-codex --pass-session-id \
     --in <new-fixture-root>/synthetic-checkout -m gpt-6.1-sol --reasoning high
   ```

   The command-local native `HERMES_CODEX_BASE_URL` override was resolved with
   the installed runtime to `openai-codex`, `codex_responses`, the exact loopback
   URL, and an existing credential. Do not use `--base-url` on this interactive
   entrypoint. Native `--in` is consumed by `main.py:_apply_in_dir` before agent
   creation; record actual runtime working directory during P01 as well.

4. In genuine Herdr only, the fresh coordinator explicitly reads `herdr --skill`,
   verifies the actual named session/pane and fresh-context evidence, and obtains
   its current Hermes conversation ID from the `Session ID:` trailer in its own
   system prompt, supplied by native `--pass-session-id`. Verify this was a fresh
   direct launch with initial system/user context, no resume flags, and no reset.
   Never reuse the historical IDs or infer the ID solely from a pane record.
5. Check Herdr's recorded conversation against that actual current ID. If stale,
   perform exactly one native `herdr pane report-agent-session` for the verified
   owned pane, source `herdr:hermes`, agent `hermes`, fresh `time.time_ns()` sequence,
   actual `--agent-session-id`, and `--session-start-source startup`. Here startup
   describes the verified fresh direct launch, not the time of the repair report.
   A resumed/reset/uncertain-origin session fails this P01 fresh-start gate and
   must stop rather than be relabelled. Capture exit
   status and sanitized response/errors rather than suppressing them, then query
   the pane and require exact ID equality. No reporting operation runs from T3.
   An explicit repair is evidence of native registration only, not proof that
   automatic hooks work. If it fails, stop with that error; no retry loop or patch.
6. Record route/model/context/registration evidence outside the repository. Stop
   after P01 and await T3 inspection. Do not launch workers or advance P02–P09.

## Acceptance and delivery

- Coordinator verifies the complete allowed-file diff and retains the successful
  authenticated routing smoke evidence without secrets or raw request dumps.
- Run `pytest --cov=skill_lens`, `mypy`, `ruff check .`, and
  `ruff format --check .`; use temporary output/cache locations and the existing
  synthetic-HOME test conventions. Do not add tests that mirror document text.
- Both selected reviewers inspect the final prepared repair/handoff and report;
  reproduce blockers and resolve them within at most two review rounds.
- Commit and immediately push each authorized commit; verify local HEAD,
  origin/main, and remote main. Leave `.path` untouched.
- The delivered state is **repair prepared; live P01 awaiting human restart**.
  Registration repair and Hermes interactive route remain unverified until the
  live retry supplies evidence. Full migration, automatic restart behavior,
  P02–P09, and Phase C remain unaccepted.

## Review decisions

- MiniMax round 1: accepted three clarifications: distinguish fixture-command
  HOME/XDG from agent HOME/auth; prove fresh origin before reporting startup;
  name the exact base alias restriction amended under current authorization.
- DeepSeek round 1: pass, with ID-source and source-version suggestions addressed.
  Its report incorrectly self-labelled mcode/MiniMax; T3 dispatch/configuration
  records identify Pi/WorkBuddy DeepSeek high. Upstream identity stays unverified.
- Coordinator correction: replace interactive `--base-url` with command-local
  native `HERMES_CODEX_BASE_URL`; add native `--pass-session-id` for authoritative
  current-session identity. Both critics must recheck this revised entry contract.
- Rejected factual suggestions: the original draft was already fingerprinted in
  review-before.json; integration marker 5 is present in source; native `--in` is
  implemented in `main.py:_apply_in_dir`. The earlier not-yet-finished pytest
  observation is superseded by its completed exit-0 receipt (1048 passed,
  one expected case-insensitive-filesystem skip, coverage 91.11%).
- MiniMax round 2: all round-1 blockers resolved; one literal path omission:
  explicitly create synthetic-checkout and put fixture.txt there. Applied its
  exact requested administrative clarification above; no requirement dispute or
  broader review wave. Verify the actual directory and hash at preparation.
- DeepSeek round 2 ended without a verdict; its bounded report-completion retry
  returned pass, no operative blockers, on the clarified fixture procedure.
- No unresolved requirement disagreement remains. MiniMax's exact one-clause
  fixture correction was applied administratively; final handoff review must
  inspect the actual created path and file hash. No third broad planning wave.
