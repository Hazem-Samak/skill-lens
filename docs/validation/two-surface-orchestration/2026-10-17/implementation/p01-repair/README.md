# P01 repair: prepared, awaiting human restart

> Latest P01 capture checkpoint (2026-10-18): the repaired live retry proved
> fresh context and current registration but lacked correlated actual API-mode
> and HTTP request-URL proof. P01 remains unverified. The temporary observer and
> new fixture passed offline checks and both final reviews. Use [the new P01-only brief](../p01-capture/P01-only-brief.md).
> The earlier startup commands below are historical and must not be repeated.

The corrected coordinator route was checked successfully through the existing
Caveman proxy using the existing Hermes login. Live P01 has not run.

Operative repair plan: [2026-10-17-herdr-p01-route-repair.md](../../../../../plans/2026-10-17-herdr-p01-route-repair.md)
@ frozen commit `6a038523e57c217b2b1a3afa64713da6a4ff2d17`.
The base and native-critic amendment remain operative as scoped by that repair.
The user authorized fixing the remaining issues on 2026-10-17.

## What was corrected

- Use native `openai-codex` with a command-local
  `HERMES_CODEX_BASE_URL=http://127.0.0.1:8787/chatgpt`. The former Caveman native
  `custom` route spoke chat completions to an API-key endpoint, incompatible
  with this subscription login. No proxy service or global configuration was changed.
- Request `gpt-6.1-sol` high. The former `gpt-6.1-sol-900k` identifier was rejected
  by the backend with HTTP 400. The replacement returned HTTP 200,
  `response.completed`, response model `gpt-6.1-sol`, and exact `ROUTE_OK`.
  This proves the observed route/reply, not upstream weights or 900k capacity.
- Keep the historically successful context restriction:
  `--ignore-rules --toolsets terminal,file`. Add native `--pass-session-id` so
  the coordinator sees its own current ID in the system prompt.
- If Herdr still shows the previous conversation, make one checked native report
  from the genuine owned Herdr pane and require exact ID readback. The plugin's
  current silent reporting mechanism is unchanged; its historical failure cause
  and automatic restart reliability remain unverified.

## Human handoff

1. Exit the old Hermes conversation. Leave the owned Herdr pilot session open.
2. In its shell, run the command in [P01-only-brief.md](./P01-only-brief.md).
3. Paste the short instruction from that brief into the new Hermes conversation.
4. Bring its final P01 result back to T3. It must stop after P01.

If the new temporary fixture is gone, stop and have T3 prepare another fixture.
Do not reuse the vanished historical path or substitute an ordinary project checkout.

See [preparation.json](./preparation.json) for the fresh paths and fixture hash,
[routing-observation.json](./routing-observation.json) for sanitized routing evidence,
and [gates/](./gates/) for the four project checks. Historical failures below were
reported by the user; the old /tmp artifacts were absent during this repair.
No raw requests, tokens, or profile contents are retained here.

## Acceptance limits

This delivery prepares the bounded repair and human handoff. It does not accept
live P01, automatic hooks, detach/restart, P02–P09, Phase C, or the migration.
Fixture-command HOME/XDG directories do not isolate the Hermes agent process:
Hermes retains normal authentication HOME, and `--in` only sets its working
directory. The live retry must separately prove fresh context, actual route,
conversation registration, and unchanged original repository/fixture.

Planning review: MiniMax R1 changes required; R2 resolved prior blockers and
requested one explicit fixture-directory clause, applied exactly. Its canonical
R2 report is retained. DeepSeek R1 pass; R2 ended incomplete; a bounded report
completion returned pass on the clarified entry contract. DeepSeek R1's mistaken
self-identification as MiniMax is superseded by the actual T3 dispatch/configuration
records. Upstream reviewer identities remain unverified. The earlier user waiver
was not used for this repair. Final handoff review is recorded separately.

Final handoff review: MiniMax **pass**, with physical fixture-path/hash checks in
[its complete report](./final-minimax-r1-report.md). DeepSeek **pass** in
[its completed report](./final-deepseek-r1-completion.json), using its prior direct
inspections and clearly labelled coordinator-supplied pointer-diff evidence after
its original turn ended without a verdict. Both accept the prepared handoff only.
See [execution receipt](./execution-receipt.json),
[review fingerprint](./review-before.json), and
[gate checkout binding](./gates/binding.json). Administrative retention suggestions
were applied after review; no operative command or acceptance condition changed.
The working-directory check also names macOS's `/tmp` → `/private/tmp` shortcut:
the coordinator directly verified both paths identify the same fixture directory.
Use filesystem identity rather than rejecting that equivalent spelling.
