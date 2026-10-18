# Accepted: offline P01 observer and human handoff

Sol accepted this bounded preparation on 2026-10-18 after both final R2 reviewers
returned **pass with no blockers**. This accepts the temporary observer, its
offline proof, the fresh pinned deployment and the P01-only human brief. Live P01
is still **unverified**. P02–P09, detach/restart, Phase C and migration acceptance
remain paused.

Authority: the user authorized fixing the remaining issues and Git delivery.
The capture plan was frozen at `a9bcda8b6f1e2ac7de15b13eefbdfa299adb830f`, followed
by reference-only commit `46be718cb7991e3914f6feef6e716f3d0c772cb8`. Its base,
native-critic amendment and route-repair references remain operative.

## Evidence and scope

- Coordinator verification: 58 unique offline test methods (52 capture and six
  mutation methods); five mutation guards caught by unchanged normal assertions,
  zero survivors. The pinned deployed copy also passes all 58 tests and native
  startup/help checks. Actual startup proof uses native bootstrap and observer
  entry, stubbing only the CLI entry to avoid a real agent request.
- Project gates: 1048 passed, one expected case-insensitive-macOS skip, 91.11%
  coverage; mypy clean on 37 source files; Ruff lint and format checks clean.
- The reproduced root-ancestor swap is rejected, with injection confirmed and
  no outside capture created. Filesystem-root directory descriptors, one
  no-follow component walk and owned fallback descriptors close the redirection
  gap. No extra service, persistent shim, plugin or installed-source change.
- Only this capture directory and four prior-document status pointers changed.
  Product source/tests and pre-existing empty `.path` remain untouched.
- R2 before/after fingerprints match. Subsequent changes are administrative
  acceptance records, status text and a clarification of the existing symlink
  precondition; source, tests, operative command and deployed script hashes stay
  identical to the independently reviewed snapshot.
- All 14 child tasks are terminal with no pending children or questions. See the
  [task ledger](./terminal-task-ledger.json), [execution receipt](./execution-receipt.json),
  [coordinator verification](./coordinator-verification.json), [gate logs](./gates/),
  [review window](./review-window.json) and retained delegated reports.

The previous temporary evidence and deployment disappeared before the 2026-10-18
resume. They were recorded as missing, never recreated as historical results.
Fresh current logs and an exclusively created fixture/deployment support this
acceptance. [preparation.json](./preparation.json) records the current paths and
SHA256 pins; [P01-only-brief.md](./P01-only-brief.md) is the current handoff.

## Review dispositions and provenance

MiniMax R1 passed its assigned axis but missed the initial-root opening race;
coordinator reproduction overruled that incomplete conclusion. DeepSeek R1 ended
without a verdict and was not counted. Both final R2 reports pass the corrected
version; all reproduced blockers have been resolved.

T3 receipts confirm MiniMax/mcode thinking **xhigh**, Pi/WorkBuddy DeepSeek
**high**, full-access/plan review modes, and Antigravity Gemini 3.8 Flash High as
sole implementer. Reviewer self-reports contain inaccurate role/runtime/model
labels; they are preserved in the raw reports and do not override live task and
configuration receipts. Upstream model/family identity remains unverified under
the user-accepted named-pair policy. Verified family diversity is not claimed.

Nonblocking suggestions were adjudicated without changing the frozen contract:

- Scalar length/character limits and a stricter public invalidation-reason type
  are deferred hardening for unexpected future callers; current internal reasons
  are literals and metadata comes from the pinned runtime fields.
- A separate `status_ok` field is unnecessary: routing approval and HTTP status
  are distinct evidence. The human requires terminal HTTP 200; earlier approved
  retry legs may return 500. Changing routing approval based on response status
  would distort that distinction.
- Full-signature assertion and extra launcher directory restrictions are not
  required for this pinned source/command. Source hashes guard version drift,
  and live physical-directory/fixture proof is mandatory in the brief.
- Root symlink precondition is now stated explicitly in the brief; the code
  already rejects it. Inline requested base URL is not actual-route proof; the
  brief continues to demand the correlated observed URL. Duplicate environment
  assertions add no proof.
- A constant message for unexpected bootstrap-import exceptions is deferred:
  current validated configuration errors suppress sensitive supplied values,
  while supported native startup is tested. No universal guarantee about every
  future third-party exception is made.

No further review wave is required for these unchanged implementation bytes.
The next authorized action is a **human-operated fresh P01-only retry**, not an
automatic continuation into P02–P09. Missing, ambiguous, invalid or mismatched
capture must stop as unverified; offline tests cannot certify the live route.
