# Synthetic Pilot Human Handoff Brief

**Plan Reference (Absolute Read-Only):** [`/Users/corvette/Documents/Projects Coding/Skill Lens/docs/plans/2026-10-17-two-surface-orchestration.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/plans/2026-10-17-two-surface-orchestration.md) @ frozen commit [`58d48cea483804b22767b381c6edd8274fe6ad44`](https://github.com/Hazem-Samak/skill-lens/commit/58d48cea483804b22767b381c6edd8274fe6ad44)  
**Pilot Matrix Reference (Absolute Read-Only):** [`/Users/corvette/Documents/Projects Coding/Skill Lens/docs/validation/two-surface-orchestration/2026-10-17/pilot.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/two-surface-orchestration/2026-10-17/pilot.md)  
**Status:** Prepared Handoff / Execution Pending User Approval & Startup  
**Canonical Synthetic Checkout:** `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout`  
**Target Fixture File:** `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt` (Initial SHA256: `462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e`)  
**Owned Artifacts Directory:** `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts`  

---

## Operator Startup Instructions

This document is a **human startup handoff**, not automated execution. It contains the exact prompt to paste into the interactive Hermes CLI once the human operator has approved the setup proposal and initiated the isolated Herdr session.

### Step 1: Open Terminal and Launch Herdr Test Session
```bash
herdr --session skill-lens-pilot-20261017
```

### Step 2: Confirm Herdr Environment Gate
Inside the shell pane spawned by Herdr, verify environment injection:
```bash
test "${HERDR_ENV:-}" = 1 && echo "HERDR_ENV confirmed: $HERDR_PANE_ID" || echo "NOT in Herdr"
```

### Step 3: Enter Synthetic Checkout
```bash
cd /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout
```

### Step 4: Launch Hermes Coordinator Interactively
```bash
hermes --cli --ignore-rules --in /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout -m gpt-6.1-sol-900k --reasoning high
```

### Step 5: Paste Pilot Brief
When the Hermes prompt (`> `) is ready, copy and paste the brief below into the session.

---

## Coordinator Prompt / Brief to Paste into Hermes

```text
You are coordinator Sol operating inside approved Herdr session "skill-lens-pilot-20261017".
Your role is to orchestrate the Phase B synthetic pilot for the Skill Lens two-surface orchestration plan.

CONTEXT & ISOLATION BOUNDS:
1. Working Directory: /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout
2. Allowed Implementation Target: fixture.txt (Initial SHA256: 462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e)
3. Fixture Command Isolation:
   - Use command-local env prefixes for fixture commands (e.g., HOME=/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-home XDG_CONFIG_HOME=/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-xdg <command>).
   - Do NOT run shell-wide export of HOME/XDG in the parent shell.
   - Owned Artifacts Directory: /tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts
4. Original Repository & Environment Bounds:
   - Original Repository strictly READ-ONLY: /Users/corvette/Documents/Projects Coding/Skill Lens must NOT be modified. Do not write to, stage, commit, or push in the original repository.
   - CLI auth stays in standard user paths (~/.hermes, ~/.pi, ~/.gemini); do NOT globally overwrite HOME for parent agent processes.
   - Do NOT touch live user skills under ~/.pi/agent/skills or ~/.gemini/skills.
   - Do NOT edit active process files or the frozen plan.
   - Report Output Exception: Writes are permitted strictly and exclusively to the owned artifact directory /tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/ (outside the fixture path).

PILOT EXERCISE EXECUTION:
Execute the pilot test matrix P01 through P09 by reading the absolute read-only matrix in the original repository:
/Users/corvette/Documents/Projects Coding/Skill Lens/docs/validation/two-surface-orchestration/2026-10-17/pilot.md
(Relative paths from the synthetic checkout will not resolve; keep the original repo strictly read-only.)

- P01: Coordinator Entry & Context
  - Verify observed documented fields HERDR_ENV=1 and HERDR_PANE_ID.
  - Do NOT require an unevidenced HERDR_SESSION_NAME environment variable. Derive real session identity using installed documented in-Herdr status/readback (e.g. `herdr status --json`, whose help is verified; live fields are unverified) and retain raw evidence, or mark session identity unverified.
  - Verify active model route (gpt-6.1-sol-900k via Sol proxy on 127.0.0.1:8787).
  - Use correlation token: HERDR-PILOT-20261017-P01.

- P02: Two Independent Critics in One Wave
  - Critic 1 Blocker Gate: STOP execution before P02 dispatch if an authorized Herdr-native mapping for Critic 1 is missing. No native selected MiniMax/mcode route is currently approved in Herdr 0.9.5. Never mix T3 critics into this pilot, install wrappers, enable unverified routes, or substitute kinds based on suggestions. Unknown proposed remedies require separate user authorization/amendment; none is proven working.
  - Critic 2: Pi on workbuddy/deepseek-v4.1-flash with flags:
    --tools read,grep,find,ls --no-mcp --no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts --no-skills --no-context-files
  - Dispatch concurrent review prompts before collecting results only if both critics are authorized and ready. Ensure distinct correlation tokens and target fingerprints.

- P03: Implementer Execution
  - Dispatch synthetic modification of fixture.txt to agy (gemini-3.8-flash-high) using proposed untested mapping with --sandbox (noting that --sandbox is an advertised terminal restriction, not certified filesystem containment).
  - Independently verify diff before/after without committing.

- P04: Full-Screen / Long Report Fallback
  - Verify report capture or temporary Markdown file fallback in owned artifact directory.

- P05: Permission & Question Handling
  - Exercise denied-write probe to verify tool enforcement boundaries.

- P06: Fast Completion & Stale-Delivery Reconciliation
  - Verify single report acceptance without duplicate or stale-report pickup.

- P07: Cancellation & Negative Guard Verification
  - Stop active background process; confirm unresolved liveness blocks acceptance.
  - Inject corrupted token (e.g. HERDR-CORRUPTED-TOKEN-999); confirm coordinator rejection.

- P08: Controlled Restart
  - Human operator restarts only the owned test session (skill-lens-pilot-20261017).

- P09: cmux Verification
  - Use absolute path /Applications/cmux.app/Contents/Resources/bin/cmux.

OUTPUT CONTRACT:
For each exercise, record reproducible log evidence strictly into owned artifact directory:
/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/
Do NOT write to or update files in the original repository (/Users/corvette/Documents/Projects Coding/Skill Lens). T3 Sol will later inspect the owned artifact directory and retain sanitized results in allowed repo files. Never paper-pass any unexecuted case.
```
