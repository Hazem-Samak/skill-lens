# Two-surface migration status — live pilot pending

Date: 2026-10-17
Overall status: Incomplete; live pilot and process migration are NOT verified.
Current native-mapping documentation checkpoint: accepted by explicit user instruction; DeepSeek findings waived for this round. See the final user-acceptance section below.
Base frozen reference: `58d48cea483804b22767b381c6edd8274fe6ad44`
Reference-recording commit: `a0ffa9edee8226d7d8b981002b265510bced8a16`
Operative amendment frozen reference: `b99e212a55b20757eeda8605db4edcc59aad6107`

This record audits the full approved outcome. A correct preflight/handoff is progress,
not a replacement for the Herdr pilot, process extraction or final implementation acceptance.

## Requirement-by-requirement state

| Requirement | Current evidence | Status |
|---|---|---|
| Approved plan, two-commit freeze, push | Planning evidence commit fe8500b; plan-only freeze 58d48ce; Reference-only commit a0ffa9e; local/origin/remote equality verified | Verified |
| Sole Gemini worker and retained MiniMax/DeepSeek council | T3 dispatch/configuration receipts; preflight and correction tasks; first-round critic reports | Verified configured selections; upstream identity unverified |
| Source baseline gates | implementation/baseline: 1048 passed, 1 expected skip, 91.11%; mypy37; Ruff clean, 187 formatted | Passed baseline; not runtime proof |
| Accurate setup and human handoff | setup.md, preflight.md/JSON, human-pilot-brief.md; initial findings corrected by Gemini; both round-2 checkpoint reviews pass | Verified checkpoint only |
| Native role/session approvals | User approved session `skill-lens`, pilot `skill-lens-pilot-20261017`, direct Hermes startup/restart, and existing Hermes/Gemini/DeepSeek settings; user approved adoption/freeze of amendment `b99e212a55b20757eeda8605db4edcc59aad6107` (Pi on native provider=anymodel / model=qwen/qwen3.8-max high + Pi on native provider=workbuddy / model=deepseek-v4.1-flash high with distinct empty session dirs) | Verified approved & frozen; live execution pending human startup |
| P01 Hermes inside genuine Herdr, context/model route | No live session/agent started; current T3 lacks HERDR_ENV; proxy TCP listening only | Unexecuted |
| P02 two native independent critics/wave | Operative mapping approved & frozen under amendment `b99e212a55b20757eeda8605db4edcc59aad6107`; both critics use native Pi CLI with distinct empty per-dispatch session directories and unique lowercase tokens; pre-edit baseline wave | Unexecuted; pending human session startup |
| P03 real agy synthetic implementation/report | External fixture.txt prepared; no model task launched inside Herdr; post-implementation review wave with fresh critics required | Unexecuted |
| P04 complete long/full-screen report or fallback | CLI help and proposed tool controls only; Pi read-only critics cannot write fallback files | Unexecuted |
| P05 blocked permission UI/denied write | Native flags inspected; no live dialog/probe | Unexecuted |
| P06 fast/stalled delivery and stale-token rejection | Planned negative case only | Unexecuted |
| P07 cancellation/background stop proof and rejection guard | Planned negative case only | Unexecuted |
| P08 detach and owned test restart | No human-operated session lifecycle | Unexecuted |
| P09 cmux runtime/wrappers/cleanup | Absolute CLI --version works; wrapper/focus/owned cleanup not exercised live | Unexecuted |
| T3 no-loss profile extraction | Active council/loops/machine profile unchanged; surfaces/t3.md not implemented | Missing |
| Herdr mechanics profile from observed pilot | surfaces/herdr.md not implemented; required pilot outcomes absent | Missing |
| Required independent final migration reviews | Current reviews cover preflight evidence and amendment drafting only, never full migration/runtime | Missing |
| Final gates/diff/scope/terminal proof for accepted migration | Checkpoint four gates passed; full migration verification still incomplete | Incomplete |
| Accepted migration commit/push | Only plan/evidence freeze commits delivered; no migration acceptance commit | Missing |
| Later bounded real Herdr task and supported status | Separate authorization/plan remains required | Not started; not authorized by this migration |

## Concrete blocking conditions

The frozen plan sections 4.4–5 require explicit approval of actual session names/startup and
native role mapping, and human-owned startup/restart. The current session is T3 outside
Herdr. Do not inject fake HERDR_ENV or operate a live focused session from outside a real
Herdr pane.

The native Critic 1 mapping is resolved under operative amendment `b99e212a55b20757eeda8605db4edcc59aad6107`
(Pi on native provider=anymodel / model=qwen/qwen3.8-max high), and session storage for both critics
is resolved to distinct newly created empty per-dispatch directories. The user explicitly authorized adoption and freeze.
The migration council in T3 remains MiniMax/mcode xhigh and Pi/WorkBuddy DeepSeek high.

The remaining blocker for pilot execution is human-operated startup of `skill-lens-pilot-20261017`
and launching Hermes coordinator inside a genuine Herdr pane (`HERDR_ENV=1`).
All P01–P09 cases remain required, unexecuted, and unverified.

## Next valid sequence

1. Complete and deliver the native-mapping documentation application checkpoint.
2. Human starts the approved isolated Herdr session (`herdr --session skill-lens-pilot-20261017`);
   coordinator runs from inside its genuine pane and executes P01–P09.
3. Resume Gemini Phase C only on adequate pilot evidence; coordinator verifies full diff,
   all gates, two final independent reviews and task terminality before migration commit/push.
4. Separately authorize the later real Herdr task before any supported-status claim.

No broad runtime guarantee is established by green Python gates, a model self-report,
a listening proxy port, an idle pane, or a proposed command.

## Reviewed preflight checkpoint closeout

Both independent round-2 reviewers passed the bounded checkpoint with no blockers:
[MiniMax report](implementation/reviews/preflight-minimax-r2.md) and
[DeepSeek report](implementation/reviews/preflight-deepseek-r2.md).
These are preflight reviews, not the final full-migration reviews required in Phase D.
[Round-2 receipts](implementation/preflight-review-r2-receipts.json) retain prompts,
configured settings, terminal outcomes and run identities. The complete
[execution receipt](implementation/checkpoint-execution-receipt.json) confirms all eight
execution/preflight child tasks completed, no pending questions or child runs.

[Final checkpoint gate logs](implementation/final-checkpoint-gates/) show 1048 tests passed,
1 expected case-insensitive-filesystem skip, 91.11% coverage; mypy clean on 37 source files;
Ruff check clean and Ruff format 197 files already formatted. The baseline log count remains
187 and historical planning count 184. These are distinct observed runs. HOME/XDG and cache/
coverage output were external; the disposable runner remains outside the repository.
No source change occurred after these source checks.

The [review-window receipt](implementation/preflight-review-r2-window.json) records zero
repository changes during round 2. Subsequent coordinator edits only retained reports and
receipts, added historical/supersession labels, clarified an already-present alternate RPC
example, and completed this audit. No native launch arguments, frozen contract, runtime
outcome or active process behavior changed. The possible direct-Hermes state-observation
sub-check suggested by MiniMax remains part of the unexecuted P01 context/integration proof;
it is not asserted to work.

The checkpoint is approved for retention and delivery as preflight evidence. Full migration
acceptance remains blocked on the concrete conditions above. No task has been restarted or
replaced to manufacture agreement. Current T3 process remains operational and unchanged.
Delivery verification for this checkpoint must compare its resulting commit with origin/main
and the GitHub remote main ref; the coordinator reports the observed hash after pushing.

## Setup approval update

The user approved the existing session/lifecycle and Hermes/Gemini/DeepSeek proposal
after the reviewed checkpoint. See the [approval record](implementation/setup-approval-20261017.md).
That approval prerequisite is resolved for those exact items. The user chose to consider
a separately reviewed native-pilot-critic amendment; exact replacement selection, controls,
operative approval/freeze, human startup and P01-P09 remain outstanding (superseded by adoption and freeze in the final section below). The earlier
missing-approval statements above describe the historical checkpoint, not a request to
approve the same setup again. Full migration is still incomplete.

## Native critic amendment review closeout

The user delegated choosing within an exclusive eleven-model/provider list and excluded
Grok/XKiro. The exact proposed Herdr pair is Pi/AnyModel Qwen 3.8 Max high (native provider=anymodel / model=qwen/qwen3.8-max) and
Pi/WorkBuddy DeepSeek high (native provider=workbuddy / model=deepseek-v4.1-flash), with explicit separate empty per-dispatch session directories
for both. Both configured T3 amendment reviewers passed corrected content with no blockers.
See [final adjudication](implementation/native-critic-amendment-adjudication-r2.md) and
[execution receipt](implementation/native-critic-amendment-execution-receipt.json).
DeepSeek's self-identity mislabel is preserved and adjudicated; requested/configured routes
are corroborated by T3 receipts, upstream identities remain unverified. These are amendment
content reviews, not final full-migration/runtime acceptance. Exact amendment adoption and
freeze remain pending (superseded by adoption and freeze in the following section). All P01-P09 remain unexecuted and Phase C remains gated on the pilot.

## Native mapping documentation application checkpoint — pending review

On 2026-10-17, the user explicitly answered **"Approve adoption and freeze"** to the exact
reviewed amendment. The amendment was frozen at `b99e212a55b20757eeda8605db4edcc59aad6107`.
Operative sections 1–7 of the amendment match `implementation/native-critic-amendment-reviewed-draft.txt`
byte-for-byte; only the reference and review/adoption history record provenance.

[Native-mapping application checkpoint gate logs](implementation/native-mapping-application-gates/) show 1048 tests passed,
1 expected case-insensitive-filesystem skip, 91.11% coverage; mypy clean on 37 source files;
Ruff check clean and Ruff format 216 files already formatted (executed by coordinator at 13:18).
These are distinguished from the baseline log count 215 (under [native-mapping-application-baseline/](implementation/native-mapping-application-baseline/)),
previous amendment count 205 (under [pilot-critic-amendment-gates/](implementation/pilot-critic-amendment-gates/)),
preflight final checkpoint count 197 (under [final-checkpoint-gates/](implementation/final-checkpoint-gates/)),
baseline count 187, and historical planning count 184 as separate historical runs, never reconciled into one.
HOME/XDG and cache/coverage output were external; the disposable runner remains outside the repository.
Final post-correction source gates have not yet been run; coordinator will execute them after inspection.

Under this documentation application:
1. `setup.md`, `pilot.md`, `acceptance.md`, `preflight-receipt.json`, and `human-pilot-brief.md`
   consistently apply native `provider=anymodel` / `model=qwen/qwen3.8-max` with thinking high (Critic 1)
   and native `provider=workbuddy` / `model=deepseek-v4.1-flash` with thinking high (Critic 2).
2. Both critics are configured with unique lowercase short tokens matching Herdr regex `^[a-z][a-z0-9_-]{0,31}$`
   and distinct newly created empty per-dispatch session directories created exclusively without `-p`
   under `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/`.
3. The executable coordinator brief (`human-pilot-brief.md`) has been revised into a complete
   copy/paste briefing with approved human startup, genuine `HERDR_ENV` check, explicit `herdr --skill`
   reading (compensating for Hermes `--ignore-rules`), ready shell-pane IDs parsed from actual JSON with
   explicit non-empty and distinctness assertions against the coordinator pane, exact verbatim critic guard from
   council baseline §2, required critic report schema with `DISPATCH_TOKEN` and `TARGET` envelope (including exact SHA256,
   `runtimeMode=N/A, interactionMode=N/A` with native controls recorded and unverified upstream identity, and token+target-path+hash match),
   complete independent supplied briefs defined before submission, parallel background submission prior to collection,
   separate prompt results including exit codes, P04 read-only Pi capture policy (no fallback file generation, no write/shell tools granted),
   P03 unique regex-valid worker name (`worker-<token>`), complete literal executable implementer prompt with full constraints, output authority,
   and implementer schema, own prompt submission and result capture, token+path+hash response acceptance, independent Sol diff verification,
   full executable preparation, dispatch, and collection for the post-implementation review wave with two fresh Pi critics (new tokens,
   new exclusive session dirs, nonempty distinct ready shell panes, separate process readiness, complete literal prompts with revised target SHA256,
   concurrent background submissions, exit code tracking, report envelope binding, and clean repository content fingerprints),
   original repo fingerprint protection before/after, P05 blocked UI observation and harmless denied-write probe,
   P06 false-settle and stalled/delayed reconciliation, P07 active command interrupt, process evidence, and synthetic rejection guards,
   P08 separate human detach and owned session stop/relaunch, and P09 cmux CLI wrapper interaction proof and protected cleanup.
4. All P01–P09 cases remain strictly **PENDING / UNVERIFIED**. No runtime success or completed
   pilot claim is made. No Phase C work has been started.
5. This checkpoint is prepared and pending coordinator inspection and independent critic review.
   It is not accepted, approved, or complete until coordinator and council verification are finished.

Coordinator verification after round-1 corrections: all four source gates passed on the corrected source tree. [Post-correction logs](implementation/native-mapping-application-r2-gates/) record 1048 passed, 1 expected filesystem skip, 91.11% coverage; mypy 37 clean; Ruff check clean and Ruff format 216 already formatted. This is a separate run from the application baseline (215) and earlier checkpoint run (216). Four verbatim guards, five complete literal prompt assignments, valid agent names, pending-case JSON, frozen operative equality and unchanged fixture were checked. Fresh required council review remains pending; no live pilot or migration acceptance is implied.

## Review round-2 escalation checkpoint

MiniMax passes the corrected mapping/handoff checkpoint and withdraws its earlier blockers; its complete report was recovered from a saved native review artifact. DeepSeek returns changes_required. See [adjudication](implementation/native-mapping-review-adjudication-r2.md) and [exact proposed resolution](implementation/native-mapping-proposed-resolution.md). The coordinator accepts an explicit intended-edit guard and an every-report freshness clarification, and rejects two allegations already covered by the source. The checkpoint remains unaccepted and uncommitted pending the council two-round escalation decision. All nine child tasks are completed with no pending work/questions; all P01-P09 remain pending and Phase C remains unstarted. No third review wave or live pilot has been launched.

## User decision after escalation — checkpoint accepted

The user explicitly instructed: **"no we are good, skip Deepseek findings for this round, proceed with the final drafted plan accepted"**. See the [exact acceptance record](implementation/native-mapping-user-acceptance-20261017.md). This supersedes the earlier pending/escalation state for the native-mapping documentation checkpoint only. The user accepted the existing reviewed handoff and waived the remaining DeepSeek findings; the proposed additional corrections are not applied and no third review wave is launched.

MiniMax's recovered round-2 report passes and withdraws both earlier blockers. DeepSeek's substantive round-2 report remains changes_required and is retained verbatim; acceptance is by explicit user override, not unanimous review or a claim that the waived findings were fixed. The handoff content is unchanged from the reviewed snapshot. The frozen base and amendment, model choices and permissions remain in force. All nine child tasks are terminal without pending work/questions.

The coordinator will deliver this accepted documentation checkpoint under the existing commit/push authorization after final checks. All P01-P09 remain pending, Phase C remains unstarted, and full migration remains incomplete. The approved next step is human-operated direct Hermes startup in the isolated Herdr pilot, followed by actual pilot evidence. Later phases retain their required review and acceptance gates.

Final coordinator checks after user acceptance passed: **1048 tests passed, 1 expected filesystem skip, 91.11% coverage**; mypy clean on 37 files; Ruff check clean; Ruff format **221** files already formatted for this run. [Final source logs](implementation/native-mapping-user-accepted-final-gates/) and [execution receipt](implementation/native-mapping-checkpoint-execution-receipt.json) retain results, limits, task accounting and the explicit reviewer waiver. The only format correction was to the retained, unadopted proposal example. Source code, tests, active process files, both frozen plans and the reviewed handoff remain unchanged. These results authorize checkpoint delivery under the recorded user acceptance; they do not prove Herdr runtime readiness.
