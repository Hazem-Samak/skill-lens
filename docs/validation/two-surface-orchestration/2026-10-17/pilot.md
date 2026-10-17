# Two-Surface Orchestration: Pilot Evidence & Status (Phase B)
**Date:** 2026-10-17  
**Status:** Pre-Pilot / All Cases PENDING — Bounded Preflight Completed  
**Plan Reference:** [`docs/plans/2026-10-17-two-surface-orchestration.md`](../../../plans/2026-10-17-two-surface-orchestration.md) @ frozen commit [`58d48cea483804b22767b381c6edd8274fe6ad44`](https://github.com/Hazem-Samak/skill-lens/commit/58d48cea483804b22767b381c6edd8274fe6ad44)  
**Surface Context:** T3 Code (Outside Herdr; `HERDR_ENV` absent)

---

## 1. Pilot Execution Policy

Under Section 6 Phase B of the frozen plan:
- **No Paper Pass:** Pilot setup is not pilot execution. No case is marked passed without reproducible live evidence captured inside an owned Herdr session.
- **Outside Herdr Invariant:** T3 cannot simulate, inject, or automate Herdr execution from outside `HERDR_ENV`.
- **Negative Case Requirement:** To validate that process guards function, pilot evidence must include:
  1. An intentional mismatched-token / stale-report rejection.
  2. An intentional unresolved-liveness rejection.
- **Role Set Requirement:** The minimum trial-ready role set requires Hermes coordinator, agy implementer, and two independent critic roles.
- **Strict Output Boundary:** The pilot coordinator operating inside Herdr treats the original repository (`/Users/corvette/Documents/Projects Coding/Skill Lens`) as strictly **READ-ONLY**. All pilot evidence is written exclusively to the owned artifact directory (`/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/`). T3 Sol later inspects and records sanitized outcomes.

---

## 2. Pilot Test Matrix (P01–P09)

Every case is currently **PENDING / UNVERIFIED**. The table below records the exercise, planned evidence, blocking prerequisites, and current status:

| ID | Exercise | Required Evidence & Failure Consequence | Blocking Prerequisites | Current Status |
|---|---|---|---|---|
| **P01** | Hermes coordinator entry and context | `HERDR_ENV` gate check; actual session/model route verification (`gpt-6.1-sol-900k` via Sol proxy 8787); scoped shell commands; proof of fresh context; derive real session identity via documented in-Herdr status/readback without requiring unevidenced `HERDR_SESSION_NAME`. *Failure blocks coordinator readiness.* | Human launch of `skill-lens-pilot-20261017` session; user approval of startup handoff. | **PENDING** (Unexecuted) |
| **P02** | Two independent critics in one wave | Concurrent prompt submission before parent collection; distinct correlation tokens & target fingerprints; complete reports; clean before/after fingerprints. Blocker gate: STOP before dispatch if authorized Herdr-native Critic 1 mapping is missing; never mix T3 critics into pilot, install wrappers, or substitute kinds without amendment. *Failure blocks multi-critic wave.* | Resolution of Critic 1 native kind gap in Herdr (unsupported in Herdr 0.9.5 kind enum; requires user decision/amendment); session startup. | **PENDING** (Unexecuted) |
| **P03** | Actual agy / Antigravity implementer | Model/config verification (`gemini-3.8-flash-high`); allow-listed synthetic edit in fixture checkout (`/tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt`, baseline SHA256 `462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e`); proposed untested `--sandbox` mapping (advertised terminal restrictions, no containment guarantee); implementer report; independent coordinator comparison; handoff to critics; no commit/delegation. *Failure blocks implementer role.* | Session startup; user approval of role mappings and session names. | **PENDING** (Unexecuted) |
| **P04** | Full-screen / long report and fallback | Selected kinds recover full report or execute temporary Markdown fallback with matching token/target in owned artifact directory; untested kinds marked unavailable. *Failure restricts reporting to file-fallback.* | Live agent prompt execution in Herdr pane. | **PENDING** (Unexecuted) |
| **P05** | Permission and question handling | Observe blocked UI state; authorized read response; harmless denied-write probe; record exact boundary without universal sandbox claim. *Failure restricts autonomous tools.* | Interactive pane monitoring during live agent run. | **PENDING** (Unexecuted) |
| **P06** | Fast completion and ambiguous delivery | Deliberate exercise of false-settle, delayed, or timed-out observation; reconcile one submission without duplicates or stale-report acceptance. *Failure blocks fast-settle reliance.* | Synthetic timeout/race fixture in Herdr pane. | **PENDING** (Unexecuted) |
| **P07** | Active cancellation / background activity | Stop representative owned work; bounded job/process evidence; preserved output; verify that unresolved liveness blocks acceptance/replacement. *Failure blocks safe cancellation.* | Live background process execution inside Herdr. | **PENDING** (Unexecuted) |
| **P08** | Detach and controlled restart | External human operator restarts only owned test session (`skill-lens-pilot-20261017`); verify no inference from layout restoration to worker termination. *Failure marks restart guarantees unverified.* | User-operated restart of test session. | **PENDING** (Unexecuted) |
| **P09** | cmux interaction and cleanup | cmux wrappers work or required role blocked; no focus theft or user resource edits; coordinator/dirty-worktree exemptions work. *Failure marks cmux integration unavailable.* | Absolute invocation of `/Applications/cmux.app/Contents/Resources/bin/cmux` or user PATH edit; session startup. | **PENDING** (Unexecuted) |

---

## 3. Negative Guard Verification Design

When pilot execution is authorized, two synthetic failure cases will be injected to demonstrate that Herdr coordinator guards actively reject invalid results:

1. **Synthetic Token Mismatch:**
   - A mock reviewer report will be submitted echoing a corrupted token (e.g. `HERDR-CORRUPTED-TOKEN-999` instead of the expected dispatch token).
   - Expected coordinator behavior: Outright rejection of the report; round remains unaccepted.
2. **Synthetic Unresolved Liveness:**
   - An agent task will leave a background sleep process running in its pane.
   - Expected coordinator behavior: Inspection reveals active process; task state marked `interrupted/unknown`; replacement dispatch blocked until the old activity is cleared.

---

## 4. Pilot Preflight Findings Summary

- **Installed Stack:**
  - Hermes (`0.22.2`), agy (`1.4.0`), pi (`1.3.0`), Herdr (`0.9.5`), opencode (`2.0.32`), mcode (`0.6.12`).
  - cmux (`0.65.2`) is present and verified at `/Applications/cmux.app/Contents/Resources/bin/cmux`; absolute invocation is functional, `$PATH` entry is optional.
- **Prepared Synthetic Fixture:**
  - Canonical path: `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout`
  - Target file: `fixture.txt` (SHA256: `462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e`)
  - Fixture environment: Command-local HOME at `/tmp/.../pilot-home`, XDG at `/tmp/.../pilot-xdg`
  - Owned artifacts directory: `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/` (sole report output destination; original repository preserved read-only)
- **Known Blocker for Full Council:**
  - Herdr 0.9.5 does not have native support for `mcode` (MiniMax) in its 24-kind argument enum, and inspected local configs configure no active route. This native kind gap is scoped to the installed enum and inspected configs, not global impossibility. Unvalidated future alternatives require explicit user decision and formal plan amendment; no substitute kind may be unilaterally adopted.
- **Next Steps:**
  - User review and approval of [`setup.md`](./setup.md).
  - Human initiation of `herdr --session skill-lens-pilot-20261017`.
  - Execution of P01–P09 under live Herdr environment.
