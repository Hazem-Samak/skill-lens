# Fresh P01-only repair retry

> Latest P01 capture checkpoint (2026-10-18): the repaired live retry proved
> fresh context and current registration but lacked correlated actual API-mode
> and HTTP request-URL proof. P01 remains unverified. The temporary observer and
> new fixture passed offline checks and both final reviews. Use [the new P01-only brief](../p01-capture/P01-only-brief.md).
> The earlier startup commands below are historical and must not be repeated.

Status: prepared; live execution not yet run.
Repair plan: `docs/plans/2026-10-17-herdr-p01-route-repair.md`
@ `6a038523e57c217b2b1a3afa64713da6a4ff2d17`.
Read that plan and the operative base/critic amendment it names.

## Human steps

Exit the old Hermes conversation; keep Herdr open. Use the owned session
`skill-lens-pilot-20261017`. If it is closed, the human opens it with
`herdr --session skill-lens-pilot-20261017`. In its genuine Herdr shell:

```bash
test "${HERDR_ENV:-}" = 1 &&
test -f /tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/synthetic-checkout/fixture.txt &&
HERMES_CODEX_BASE_URL=http://127.0.0.1:8787/chatgpt \
hermes --cli --ignore-rules --toolsets terminal,file \
  --provider openai-codex --pass-session-id \
  --in /tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/synthetic-checkout \
  -m gpt-6.1-sol --reasoning high
```

Then paste:

> Read /Users/corvette/Documents/Projects Coding/Skill Lens/docs/validation/two-surface-orchestration/2026-10-17/implementation/p01-repair/P01-only-brief.md and perform only its P01 repair retry. Stop after P01 and report the evidence path. Do not launch workers.

## Coordinator instructions inside genuine Herdr only

1. Verify `HERDR_ENV=1` without setting it yourself. Explicitly read
   `herdr --skill`, then use its native status/current-pane queries to verify
   actual session `skill-lens-pilot-20261017` and the owned coordinator pane.
   If session/pane cannot be verified, stop. No neighboring panes or sessions.
2. Verify the operative frozen repair and the original two plans. Keep the original
   repository strictly read-only. Capture a **fresh live entry** HEAD/status and
   SHA256 manifest of its tracked and nonignored untracked files (including
   pre-existing `.path`), and compare the same scope at exit. Preparation HEAD in
   preparation.json is historical; it is not the live baseline.
3. Verify working directory is the same filesystem directory as
   `/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/synthetic-checkout`.
   Compare resolved paths or use `Path.samefile()`: macOS reports `/private/tmp/`
   for the `/tmp/` shortcut. Record both spellings; they must refer to the same
   directory, and an unrelated directory must fail the check.
   The only fixture file is `fixture.txt`, bytes `pilot status: pending\n`,
   SHA256 `462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e`.
   Preserve it unchanged throughout P01. Do not run the product, pytest, or any
   original-repository mutation. Fixture/product tests, when later authorized,
   use command-local synthetic HOME/XDG; never export fake HOME/XDG for Hermes.
4. Read the actual `Session ID:` trailer in your current system prompt, injected
   by `--pass-session-id`. Require fresh initial system/user context: no resume
   flags, reset, prior conversation, memory/profile blocks, repository rules, or
   automatically discovered/preloaded skills. Do not quote private blocks into
   evidence. Explicitly reading the approved Herdr skill and these plans is allowed.
   A missing ID or uncertain fresh origin is a failure; do not infer it from Herdr.
5. Verify the **actual** provider/model/API mode/base URL and high reasoning using
   your own current-session runtime/request metadata, sanitized to those fields.
   Require `openai-codex`, `gpt-6.1-sol`, `codex_responses`, and
   `http://127.0.0.1:8787/chatgpt` (request suffix `/responses`).
   The environment, source defaults, configuration, this brief, and the coordinator's
   earlier routing smoke are requested/observed evidence, not proof of this live
   conversation. If actual request-route proof is unavailable, mark it unverified
   and stop. No fallback, model switch, second agent, or authentication repair.
   Upstream weight identity remains unverified even if the endpoint reports the ID.
6. Query this owned pane using `herdr pane get <verified-pane-id>`. Compare its
   recorded Hermes conversation ID against your actual system-prompt session ID.
   If they already match, record that and make no registration write.
   If stale, after confirming the fresh-start origin in step 4, make **one** native
   registration report with these fields:

   ```text
   herdr pane report-agent-session <verified-owned-pane-id>
     --source herdr:hermes --agent hermes
     --seq <fresh Python time.time_ns()>
     --agent-session-id <actual-current-Hermes-session-id>
     --session-start-source startup
   ```

   These angle-bracket fields must come from your verified current runtime.
   `startup` describes the proven fresh direct launch, not the report's later time.
   Capture its exit code and sanitized stdout/stderr. Bound it to ten seconds;
   on timeout/nonzero exit, stop and retain the error. Do not rerun it, alter a
   config/plugin, or release lifecycle authority.
   Query the same pane once more and require exact conversation-ID equality.
   Record whether registration matched automatically or needed this explicit
   repair, plus source fields before/after. A later automatic `resume` source
   label for the same ID does not by itself prove the conversation was resumed.
   This explicit report does not certify automatic-hook or restart reliability.
7. Write only to the owned directory
   `/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts/`.
   Create a fresh per-attempt evidence directory exclusively; no overwrites.
   Retain result.json with requested vs actual route fields, session/pane,
   fresh-context booleans and provenance, current session ID, registration
   command/result (if used), comparison proof, and P01 pass/fail/unverified.
   Retain before/after fixture SHA256 and original-repository HEAD/status/manifest
   comparison. Do not copy raw prompts, request dumps, secrets, or profile contents.
8. **Stop after P01 even if it passes.** No workers, critics, P02–P09,
   detach/restart experiments, service changes, plugin fixes, or Phase C.
   Return a concise result and the exact evidence directory to the human/T3.

Any failed or unavailable required proof stops this attempt. No exploratory loop.
