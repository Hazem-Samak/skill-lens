# P01 only: observe the actual request route

Status: offline preparation accepted on 2026-10-18; live P01 remains unverified.
Both final reviewers returned pass; T3 accepted this prepared handoff.
Use only while the pinned temporary directory still exists and its checks pass.

Operative capture plan: `docs/plans/2026-10-17-herdr-p01-request-capture.md`
@ `a9bcda8b6f1e2ac7de15b13eefbdfa299adb830f`.
It amends the P01 entry procedure in the route-repair plan
@ `6a038523e57c217b2b1a3afa64713da6a4ff2d17`. Read its base plan and native
critic amendment too. No change to model, route, roles, context isolation, or stop rules.

## Human steps after T3 accepts the prepared handoff

1. Exit the old Hermes conversation. Keep the owned Herdr pilot session open.
   If needed, the human opens it using `herdr --session skill-lens-pilot-20261017`.
   T3 never starts, restarts, or drives this live session.
2. In that genuine Herdr shell, paste the command below. It checks the inherited
   environment and pinned script bytes. Never set HERDR_ENV yourself.
3. Paste the instruction below into the fresh Hermes conversation.
4. Bring its P01 result and evidence directory back to T3. Stop after P01.

```bash
test "${HERDR_ENV:-}" = 1 &&
cd /private/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts/p01-capture-prepared-izqwkulo/observer &&
shasum -a 256 -c SHA256SUMS &&
test -f /private/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts/p01-capture-prepared-izqwkulo/synthetic-checkout/fixture.txt &&
test ! -e /private/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts/p01-capture-prepared-izqwkulo/capture.jsonl &&
test ! -L /private/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts/p01-capture-prepared-izqwkulo/capture.jsonl &&
test ! -e /private/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts/p01-capture-prepared-izqwkulo/capture.jsonl.invalid &&
test ! -L /private/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts/p01-capture-prepared-izqwkulo/capture.jsonl.invalid &&
HERMES_CODEX_BASE_URL=http://127.0.0.1:8787/chatgpt \
HERDR_OBSERVER_OUTPUT_PATH=/private/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts/p01-capture-prepared-izqwkulo/capture.jsonl \
/Users/corvette/.hermes/tools/python-3.14.7+20260901-darwin-arm64/bin/python3 -B \
  /private/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts/p01-capture-prepared-izqwkulo/observer/launcher.py \
  --cli --ignore-rules --toolsets terminal,file \
  --provider openai-codex --pass-session-id \
  --in /private/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts/p01-capture-prepared-izqwkulo/synthetic-checkout \
  -m gpt-6.1-sol --reasoning high
```

Paste into Hermes:

> Read /Users/corvette/Documents/Projects Coding/Skill Lens/docs/validation/two-surface-orchestration/2026-10-17/implementation/p01-capture/P01-only-brief.md and perform only its P01 capture retry. Stop after P01 and report the evidence path. Do not launch workers or change configuration.

The artifacts root and ordinary parent directories must contain no symlinked
components; the native walk rejects them. Standard macOS /tmp aliases are handled.

If the prepared directory is missing, any hash fails, output/marker already exists,
or inherited HERDR_ENV is absent, stop and return to T3. Do not reuse a previous
capture, delete old evidence, fabricate the environment, or substitute a checkout.

## Instructions for the coordinator inside genuine Herdr

1. Verify inherited HERDR_ENV=1 without setting it. Explicitly read `herdr --skill`.
   Use native status/current-pane queries to prove actual session
   `skill-lens-pilot-20261017` and your owned pane. No neighboring sessions/panes.
2. Verify operative frozen plans. Keep the original repository strictly read-only:
   `/Users/corvette/Documents/Projects Coding/Skill Lens`.
   Take fresh live entry and exit HEAD/status/SHA256 manifests of tracked and
   nonignored untracked files, including pre-existing `.path`. Compare the same
   scope. Preparation HEAD is historical, never the live baseline.
3. Require your working directory to be the same physical directory as
   `/private/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts/p01-capture-prepared-izqwkulo/synthetic-checkout`.
   Resolve macOS /tmp aliases or use Path.samefile(); unrelated directories fail.
   Preserve fixture.txt, exactly `pilot status: pending\n`, SHA256
   `462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e`.
   No product/tests execution. No fake HOME/XDG for Hermes; normal authentication
   remains. Reading the approved brief/plans/Herdr skill explicitly is allowed.
4. Read the actual Session ID trailer in your current system prompt. Require a
   fresh initial system/user conversation: no resume/reset/prior conversation,
   persistent memory/profile blocks, repository rules, or automatically
   discovered/preloaded skills. Record booleans/provenance, never private content.
   A missing ID or uncertain fresh origin stops the attempt.
5. Read only the metadata capture at `/private/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts/p01-capture-prepared-izqwkulo/capture.jsonl`.
   It is written by the pinned observer; never modify it. The records for your
   exact system-prompt session ID must show one unambiguous request ID with
   actual `api_mode=codex_responses`, provider `openai-codex`, model
   `gpt-6.1-sol`, high reasoning, base URL
   `http://127.0.0.1:8787/chatgpt`, and paired actual HTTP POST
   `http://127.0.0.1:8787/chatgpt/responses` with terminal HTTP 200.
   Require correlated=true, matching exchange IDs and an observed call exit
   for that request. Earlier retry exchanges may share the request ID.
   Every observed route must remain approved. A requested configuration, source
   default, environment variable, old proxy log, or another session is not proof.
6. Reject missing/truncated/malformed records, absent or ambiguous correlation,
   any route mismatch, capture_invalidated records, an existing
   `capture.jsonl.invalid` marker, or any HERDR_OBSERVER_ALERT. If capture
   reliability is uncertain, stop as unverified. No inference, fallback/model
   switch, second agent, auth repair, plugin/config/service edit, or exploration.
   Upstream model identity remains unverified even when the endpoint names Sol.
7. Query your verified owned pane using `herdr pane get <verified-pane-id>`.
   Compare its Hermes conversation ID with your actual system-prompt session ID.
   Already matching means no registration write. If stale, retain the prior
   repair's ONE checked native report rule:
   `herdr pane report-agent-session <verified-owned-pane-id> --source herdr:hermes --agent hermes --seq <fresh Python time.time_ns()> --agent-session-id <actual-current-ID> --session-start-source startup`.
   Only after fresh-start proof, bound the command to ten seconds; retain exit
   code and sanitized output. On timeout/nonzero stop; no retry/config repair.
   Query the same pane once more and require exact ID equality. Record whether
   automatic match or manual repair occurred. This proves no restart reliability.
8. Create a fresh exclusive result subdirectory inside
   `/private/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts/p01-capture-prepared-izqwkulo`. Write result.json, sanitized correlated route evidence,
   context/registration provenance, and repository/fixture entry/exit comparisons.
   Preserve capture and all historical evidence. Do not retain headers, bodies,
   prompts, credentials, profile contents, or arbitrary exception messages.
9. STOP after P01 even on pass. No workers, pilot critics, P02–P09, detach/restart,
   product tests, Phase C or migration acceptance. Return concise pass/fail/
   unverified with evidence directory and any reason for stopping.

Any failed or unavailable required proof stops this attempt without an exploratory loop.
