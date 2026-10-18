# P01 request capture: preparation and verification

This temporary observer supplies the two fields missing from the latest live
P01 result: actual API mode and actual HTTP request URL/status for the same
session and request. Live P01 remains unverified; P02–P09 remain paused.

The [frozen capture plan](../../../../../plans/2026-10-17-herdr-p01-request-capture.md)
at `a9bcda8b6f1e2ac7de15b13eefbdfa299adb830f` is the operative contract.
See [preparation.json](./preparation.json) for the exclusive fresh fixture,
temporary script copies and their hashes. The human alone starts the real
coordinator using [P01-only-brief.md](./P01-only-brief.md), after the recorded final acceptance.

The original repository and current live session were left untouched. The prior
temporary fixtures, deployment and external logs were found missing on 2026-10-18;
no historical evidence was recreated. A new exclusive fixture and deployment were
prepared for this checkpoint. No installed source, service, authentication or persistent
configuration was changed. Gemini's [report](./report.md) is an implementer
self-report; coordinator evidence and final reviews decide acceptance.

Current status: offline observer and handoff accepted; both final R2 reviewers pass.
Live P01 remains unverified. See [acceptance.md](./acceptance.md) and the retained
[execution receipt](./execution-receipt.json).
Preparing this handoff does not accept live routing, upstream model identity,
restart behavior, P02–P09, Phase C or the overall migration.

For a new T3 chat, the assistant should read [NEW-CHAT-HANDOFF.md](./NEW-CHAT-HANDOFF.md).
The human need not open files. A byte-identical deployment was refreshed again
after temporary-file expiry; see [the refresh receipt](./handoff-refresh/receipt.json)
and the current preparation paths. Live P01 remains unverified.
