# Plan: capture the missing P01 request evidence

Status: Agreed
Authorization: The user's 2026-10-17 instruction "ok fix the remaining issues please,
authorized", continued by "so what's next ??". This authorizes a bounded repair
of evidence capture, not a waiver of P01 or a change of coordinator model/route.
Reference: a9bcda8b6f1e2ac7de15b13eefbdfa299adb830f
Risk and review: High (private-data handling and pilot entry contract). MiniMax/mcode
xhigh and Pi/WorkBuddy DeepSeek high review plan and final implementation. Retain
their previously accepted unverified-upstream-identity policy; no earlier waiver.
Expected child tasks: two plan critics, one Gemini implementer, two final critics.

## Outcome and observed failure

Keep the successful model/route, fresh-context restriction, and automatic current
conversation registration. Capture the actual API-mode field and HTTP request URL
for the same request, without storing prompts, credentials, headers, or bodies.
The human performs one fresh P01-only retry after offline verification and reviews.

The current live result at
`/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts/p01-retry-nymmgj98/result.json`
is **unverified**, not failed connectivity and not accepted P01. It records fresh
context, correct conversation registration without a write, expected provider,
model, base URL and high reasoning, unchanged repository/fixture, and no workers.
Explicit API mode and actual HTTP request URL were absent. Existing proxy log
entries could not be correlated by exact session or response ID. Preserve that
historical result unchanged; do not infer the missing fields from defaults.

Installed Hermes `agent/codex_runtime.py:run_codex_stream(agent, api_kwargs, ...)`
receives the live agent exposing session ID, current API-request ID, provider,
model, base URL and actual API mode. It calls `active_client.responses.create`
through a Relay callback, consuming the stream before returning. Relay captures
the caller ContextVars and explicitly re-enters a copied context in its callback
(`agent/relay_llm.py:92,100-112`). HTTPX request/response event hooks expose each
actual HTTP exchange, including redirects. Prove their correlation offline.
Hermes' existing full request-dump option is unsuitable because it stores content.

Installed source root (read-only): `/Users/corvette/.hermes/hermes-agent`.
Source SHA256 pins, rechecked by the coordinator before completion review:

- `agent/codex_runtime.py`: `88bbcfb34e4a7ab4aadf50ea6409eb35a5a6a615dd821a322768215864756f30`
- `agent/relay_llm.py`: `9a2a0242bdafdf33c1bf8f38219a7aba318d87c6ea65657b7d888c55ae9b85ea`
- `hermes_cli/_launchers.py`: `9cf612547558a28a7840544a44c5f5ab866ee527a05f96000aefdf51cd7fcbcd`

## Scope and preserved boundaries

Add only this plan and
`docs/validation/two-surface-orchestration/2026-10-17/implementation/p01-capture/`:
a small disposable observer/launcher, focused offline tests, human brief, sanitized
evidence, and reports. Add current-status pointers to setup.md/pilot.md and the
prior repair README/brief; preserve prior operative text and evidence below them.
No Skill Lens product/source/test changes, no installed Hermes/Caveman/Herdr
patches, no persistent plugin or configuration changes, no new services/keys,
and no global HOME/PYTHONPATH replacement. Preserve pre-existing empty `.path`.

This amends only the P01 entry/capture procedure of repair plan
`2026-10-17-herdr-p01-route-repair.md` @
`6a038523e57c217b2b1a3afa64713da6a4ff2d17`. Its base plan @
`58d48cea483804b22767b381c6edd8274fe6ad44` and critic amendment @
`b99e212a55b20757eeda8605db4edcc59aad6107` remain operative. The only new
execution mechanism is an explicit **temporary, in-process observer launcher**;
no persistent shim/plugin installation is authorized. The normal native Hermes
bootstrap/authentication must remain in use. Existing repair authority covers
this bounded observation addition; it does not permit changing request behavior.

## Implementation

1. Freeze this reviewed amendment before code. Gemini 3.8 Flash High via
   Antigravity is the sole writer of observer code/tests; Sol verifies/commits.
2. Implement a small process-only wrapper around the installed
   `agent.codex_runtime.run_codex_stream` function before importing/starting the
   normal CLI. Read whitelisted scalars directly from its actual agent argument
   and API kwargs. Set request context on that caller thread around the original
   function and reset it in `finally`; call the original function exactly once
   with unchanged arguments/results/exceptions. No lifecycle/plugin hook changes
   or extra first-party observability callbacks. Verify the installed caller
   resolves this function at runtime; unsupported source/signature stops startup.
3. Keep only a strict whitelist of scalar runtime metadata: session/request IDs,
   provider, model, actual API mode, sanitized base URL, and actual reasoning
   effort if available from the API kwargs. Do not retain the agent, API kwargs,
   messages, bodies, headers, tokens, or user text. Use request-local ContextVar
   correlation, not a process-global last-session variable. Missing/ambiguous
   correlation yields no usable proof, never a fabricated session match.
4. Attach HTTPX's public request/response event hooks to synchronous clients
   created after observer installation, preserving pre-existing hooks and their
   order. This observes each physical exchange, including SDK retries and HTTP
   redirects, without replacing transport/send behavior. Pair request/response
   events by object identity with weak references, not copied/retained payloads;
   serialize the safe request-local metadata and local event ID. A response hook
   must preserve the current request's correlation when the sending context is
   copied into Relay threads. Do not consume or replace bodies or streams.
   Preserve original return identity, exceptions, retries and cancellation.
   Unobserved async/other transports remain explicitly unsupported/unverified.
5. Write metadata JSONL to a newly and exclusively created mode-0600 file in a
   new owned attempt directory under the existing pilot-artifacts root. Reject
   path escape, symlink redirection and existing outputs before agent startup.
   Strip URL credentials/query/fragment; retain the full URL only for the exact
   approved loopback origin and known Responses endpoint. Unexpected routes
   must produce a safe mismatch marker, not leak arbitrary path/query data or
   count as success. Serialize writes across threads. Bound retained records;
   exhaustion/write failure must invalidate proof visibly, not silently pass.
6. Preserve normal Hermes startup through the installed
   `hermes_cli._launchers.runtime_command(repo_root, args, code=...)` helper,
   with code calling standard-library `runpy.run_path` on the pinned temporary
   observer script. A small temporary launcher imports that native helper and
   execs its returned argv, without a shell or PYTHONPATH/HOME replacement.
   The helper selects Hermes' managed interpreter, invokes `hermes_bootstrap`,
   and settles normal HERMES_HOME/auth; then the observer calls the normal
   Hermes CLI with unchanged approved arguments. Do not use `--run-module runpy`
   with a filesystem path: that interprets the path as an importable module and
   was reproduced to fail. The native helper/run_path bootstrap probe passed
   offline (bootstrap loaded, HERMES_HOME set, CLI arguments preserved), with no
   agent/model launch. Observer lifetime is that
   single process; no prompt/tool injection or new model API calls by the observer.
   Human startup only; require genuine `HERDR_ENV=1` for real launch. Offline
   `--help`/tests may inspect parsing without starting an agent or fabricating
   HERDR_ENV. Copy observer/tests to a fresh owned temporary directory and pin
   SHA256 before handoff; do not execute mutable repository code during live P01.
7. Prepare a concrete human brief preserving `HERMES_CODEX_BASE_URL` at the existing
   proxy, `openai-codex`, `gpt-6.1-sol`, high reasoning, `--cli --ignore-rules`,
   `--toolsets terminal,file`, `--pass-session-id`, and a new exclusively created
   attempt/fixture directory beneath the existing owned pilot-artifacts root.
   Explicitly create its synthetic-checkout/fixture.txt with the unchanged bytes
   `pilot status: pending\n` and expected SHA256
   `462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e`.
   Preserve the existing active coordinator, old fixture and historical artifacts.
   Original repository remains read-only during live P01; take fresh before/after
   manifests. Actual directory comparison resolves macOS /tmp aliases.
8. The live coordinator must match observer records to its actual system-prompt
   conversation ID and require an unambiguous request with a terminal successful exchange showing actual
   `api_mode=codex_responses`, POST, exact loopback `/chatgpt/responses` URL, and
   HTTP 200. Earlier retries may share that request ID; every observed route must
   remain approved. Do not require exactly one physical exchange. Require the
   existing actual model/high-reasoning/context/registration
   proofs. Reject mismatches, missing proof, unsafe/truncated capture and any
   observed route change. Registration already matching needs no write. Keep
   the prior single checked stale-only native report rule if needed. Save only
   metadata evidence, stop after P01, no workers or P02–P09. T3 reads external
   evidence; it never drives live Herdr or fabricates HERDR_ENV.

## Acceptance and stop conditions

- First reproduce the evidence gap from the existing result, then prove the
  observer offline using synthetic agent metadata and HTTPX MockTransport. No
  provider requests or production credentials are needed for offline tests.
- Test the installed OpenAI SDK Responses request with HTTPX MockTransport inside
  the wrapper, and the installed Relay callback's copied-context execution using
  synthetic collaborators. Prove same-request capture for direct and copied-thread
  calls. Test interleaved requests, scope reset before/after callbacks,
  missing correlation, exact/mismatched URLs, secret sentinel exclusion from
  every emitted byte, restrictive/exclusive outputs and symlink/escape rejection,
  HTTP/stream return preservation, exceptions, capture failure and record limit.
  Break correlation/privacy/output guards deliberately in disposable copies and
  demonstrate their tests fail; retain the mutation results. No live HOME skills.
- Test native bootstrap/CLI `--help` without launching an agent. Pin and verify
  deployed observer bytes. Do not claim that offline tests prove live P01.
- Coordinator inspects full diff, runs focused tests and all four Skill Lens
  gates (`pytest --cov=skill_lens`, `mypy`, `ruff check .`, `ruff format --check .`)
  with external caches/output, then obtains both selected final reviews.
- Two substantive review rounds without agreement trigger the existing escalation
  rule; no broad investigation, extra services, or repeated blind human restarts.
  A requirement conflict or unsupported bootstrap/correlation stops the affected
  work with concrete evidence rather than widening the observer.
- Commit and immediately push each authorized commit; verify HEAD/origin/main/
  remote main. Deliver **observer prepared; live P01 still unverified**. No
  upstream-weight, context-capacity, restart, migration or P02–P09 acceptance.

## Review decisions

- MiniMax R1 requested changes. Accepted bootstrap failure (reproduced); replaced
  unsupported module-path invocation with the native runtime_command/code helper
  and run_path, verified offline. Accepted caller-thread/context propagation
  requirements; simplified to direct Codex runtime wrapper with scope reset,
  avoiding lifecycle-hook worker threads and first-party observer side effects.
  Named actual Responses SDK call and required SDK/Relay copied-context proof.
- Coordinator correction: HTTPX event hooks capture redirects as separate physical
  exchanges; an outer Client.send wrapper alone would not. No payload mutation.
- Accepted fresh fixture clarification, exception-message privacy, and exact
  caller binding/source-version checks. Reviewer suggestion for another user
  confirmation is not required: existing explicit repair authority covers this
  bounded temporary observer, and all new boundaries are stated in this amendment.
- DeepSeek R1 ended mid-inspection without a verdict; not counted as approval.
  The revised second round must provide its complete verdict, not more research.
- MiniMax R2: pass, no blockers, after independently reading the installed
  runtime, Relay, and launcher. Accepted clarification that a terminal HTTP 200
  may follow retries, while every observed route must remain approved. Accepted
  content-free exception handling, no lifecycle callbacks, and literal-path argv
  bootstrap proof as implementation checks.
- DeepSeek R2 initially unverified because it searched the wrong source location.
  A bounded source-verification completion supplied exact absolute paths/hashes;
  it independently read all three anchors and returned pass with no blockers.
  Its fingerprint objection was withdrawn after confirming the nested files map.
  Its requirement for implementation proof is retained after freeze, not waived.
  The adjacent is_actual_route guard remains unchanged and should be exercised
  by the offline SDK/runtime test. No extra design wave or scope expansion.
- Both selected reviewers approve the design only. Offline implementation tests,
  final independent reviews, and live P01 remain pending. Upstream model identity
  remains unverified. Coordinator verified unchanged review fingerprints.
- Planning receipt: five actual critic tasks (two R1, two R2, one bounded R2
  source-verification completion), versus two initially expected. Extra tasks
  addressed reproduced bootstrap/context defects and incomplete source access.
  All five are terminal with no pending children. Baseline gates: 1048 passed,
  one expected macOS skip, 91.11% coverage, mypy 37 files clean, Ruff checks clean;
  logs are under /tmp/skill-lens-p01-capture-checks-20261017-oe8rbrk3.
  Token counts unavailable; no token-savings claim. Exact task/run receipts and
  timestamps will be retained in the append-only implementation record.
