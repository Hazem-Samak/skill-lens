# New-chat handoff: Skill Lens Herdr/cmux P01

Read this before assessing the human's pasted Hermes result. The human explicitly
requested saving the session so the results can be reviewed in a new T3 chat.
They want instructions inline in chat; do not ask them to open other files.

## Current checkpoint

- Repository: `/Users/corvette/Documents/Projects Coding/Skill Lens`, branch `main`.
- Accepted observer delivery: `f15384ea34f7ac2bebd9fa412ff9bcf9d53f6c9e`, pushed
  and verified against GitHub. Subsequent handoff changes are administrative;
  accepted Python implementation bytes have not changed.
- Offline observer and human handoff accepted by Sol and both final R2 reviewers:
  MiniMax and DeepSeek pass, no blockers. All 14 delegated tasks are terminal,
  without pending questions/children. Do not reopen old tasks or restart review
  waves merely because this is a new conversation.
- Proof: 58 unique offline tests; five deliberately broken guards caught by
  unchanged assertions; native bootstrap/observer entry and launcher help pass.
  Project gates: 1048 passed, one expected macOS skip, 91.11% coverage, mypy37,
  Ruff lint/format clean. Retained records are in this directory.
- Live P01 is still **unverified**. P02–P09, detach/restart experiments, Phase C
  and migration acceptance are paused. An offline pass is not live acceptance.
- Pre-existing empty untracked `.path` is user work: preserve it, never stage it.
  Product source/tests were unchanged by the observer preparation.

## Authority and frozen references

The user authorized repairing the remaining issues, implementation/review loops,
committing and pushing. The human alone starts/restarts real Herdr/Hermes.
Read `AGENTS.md` and the repository planning/implementation/council process before
any nontrivial new change. Existing authorization does not waive phase gates.

| Operative plan under docs/plans | Frozen commit |
|---|---|
| `2026-10-17-two-surface-orchestration.md` | `58d48cea483804b22767b381c6edd8274fe6ad44` |
| `2026-10-17-herdr-native-pilot-critic-amendment.md` | `b99e212a55b20757eeda8605db4edcc59aad6107` |
| `2026-10-17-herdr-p01-route-repair.md` | `6a038523e57c217b2b1a3afa64713da6a4ff2d17` |
| `2026-10-17-herdr-p01-request-capture.md` | `a9bcda8b6f1e2ac7de15b13eefbdfa299adb830f` |

The original attachment/proposal and chat are not needed to reconstruct authority;
these frozen plans, acceptance record and task receipts are the durable record.

## Exact roster and boundaries

- T3 coordinator: Sol/Codex `gpt-6.1-sol`, high.
- Sole code/test implementer: Antigravity `gemini-3.8-flash-high`.
- T3 reviewers: mcode `m:minimax:MiniMax-M3.1-Flash-Preview:v:thinking`,
  `thinkingEffort=xhigh`; Pi `workbuddy/deepseek-v4.1-flash`, `thinking=high`.
- Future native pilot critics under the approved amendment: Pi/AnyModel Qwen
  3.8 Max high alongside Pi/WorkBuddy DeepSeek high, separate fresh session
  directories and panes. This is distinct from the T3 reviewer pair.
- No silent provider/model substitutions; no Grok or XKiro. Upstream model/family
  identities remain unverified under the user-accepted named-pair policy.
  Several reviewer reports misidentified their model/role; T3 task/configuration
  receipts establish requested/configured identity, not upstream weights.
- T3 must not drive live Herdr, fabricate HERDR_ENV, or globally replace agent
  HOME/XDG/auth. No new services, keys, plugins, persistent shims or installed
  source/config changes. Synthetic HOME/XDG is only for fixture/product commands.
- Every authorized coordinator commit is immediately pushed; verify HEAD,
  origin/main and the GitHub remote. Never force-push or stage `.path`.

## Fresh launch and durable evidence

`preparation.json` and `P01-only-brief.md` beside this file contain the CURRENT
attempt, deployment, fixture and capture paths. The previous `/tmp` deployment
expired more than once. On 2026-10-18 at approximately 19:34 UTC, another absent
deployment was replaced with a fresh exclusive copy of the exact accepted
Python bytes. Never assume temporary paths remain present.

Verify current paths, source hashes, fixture hash and unused output before giving
startup instructions. If missing, re-prepare identical accepted bytes under the
approved pilot-artifacts root and update records; do not invent historical proof
or ask the human for another blind restart. No new implementation/review wave is
needed solely for an identical fresh copy. A changed implementation requires the
usual frozen-scope verification and independent review.

Approved project session: `skill-lens`. Pilot session:
`skill-lens-pilot-20261017`. The human opens cmux/Herdr and runs the tested native
launcher. Hermes uses normal authentication, `--cli --ignore-rules`, terminal/file
tools, native session-ID injection, Sol high and command-local proxy base URL
`http://127.0.0.1:8787/chatgpt`. Never use the earlier custom/900k route.

## What the new chat must verify from the pasted P01 result

1. Read actual external `result.json` and evidence, not just the human's pasted
   summary. Require genuine Herdr pilot session/current owned pane; fresh initial
   context without memory/profile/rules/preloaded skills; actual system-prompt
   session ID; correct physical fixture directory and unchanged fixture hash.
2. Read observer metadata for that EXACT session and one unambiguous request ID:
   actual `codex_responses`, `openai-codex`, `gpt-6.1-sol`, high, approved base,
   actual POST `http://127.0.0.1:8787/chatgpt/responses`, paired exchange IDs,
   terminal HTTP200 and call exit. Earlier approved retry exchanges may exist.
   Reject missing/ambiguous/malformed/truncated/invalidated capture, `.invalid`
   marker, observer alerts or any unexpected route. Requested configuration,
   environment, source defaults and another session are not live proof.
3. Require the owned pane's Hermes ID to equal the actual system-prompt ID.
   Already matching requires no write. Only the frozen stale-only, one checked
   native report with ten-second bound is allowed if repair is necessary.
4. Compare fresh live entry/exit repository HEAD/status/full nonignored file
   manifests and fixture bytes. Preparation HEAD is historical, not the live
   baseline. `/tmp` and `/private/tmp` can identify the same directory; use
   physical identity. Preserve all prior evidence; retain sanitized metadata only.
5. Accept or reject P01 with evidence and explain the result plainly. Do not
   automatically launch workers/P02–P09 or treat a pasted success as migration
   acceptance. Consult the frozen phase plan and human boundaries before any next
   step. On failure, diagnose narrowly before changing anything.

Useful saved records: `acceptance.md`, `coordinator-verification.json`, `gates/`,
`execution-receipt.json`, `terminal-task-ledger.json`, `delegated-reports.json`,
the two `final-*-r2.json` reports, `preparation.json` and `P01-only-brief.md`.
All user-facing instructions should be pasted inline, including the actual
startup command. The agent may read these files; the user need not open them.
