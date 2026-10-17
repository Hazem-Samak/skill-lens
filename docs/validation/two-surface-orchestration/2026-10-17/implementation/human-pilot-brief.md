# Synthetic Pilot Human Handoff Brief

**Operative Base Plan Reference (Absolute Read-Only):** [`/Users/corvette/Documents/Projects Coding/Skill Lens/docs/plans/2026-10-17-two-surface-orchestration.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/plans/2026-10-17-two-surface-orchestration.md) @ frozen commit [`58d48cea483804b22767b381c6edd8274fe6ad44`](https://github.com/Hazem-Samak/skill-lens/commit/58d48cea483804b22767b381c6edd8274fe6ad44)
**Operative Amendment Reference (Absolute Read-Only):** [`/Users/corvette/Documents/Projects Coding/Skill Lens/docs/plans/2026-10-17-herdr-native-pilot-critic-amendment.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/plans/2026-10-17-herdr-native-pilot-critic-amendment.md) @ frozen commit [`b99e212a55b20757eeda8605db4edcc59aad6107`](https://github.com/Hazem-Samak/skill-lens/commit/b99e212a55b20757eeda8605db4edcc59aad6107)
**Pilot Matrix Reference (Absolute Read-Only):** [`/Users/corvette/Documents/Projects Coding/Skill Lens/docs/validation/two-surface-orchestration/2026-10-17/pilot.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/two-surface-orchestration/2026-10-17/pilot.md)
**Setup Proposal Reference (Absolute Read-Only):** [`/Users/corvette/Documents/Projects Coding/Skill Lens/docs/validation/two-surface-orchestration/2026-10-17/setup.md`](file:///Users/corvette/Documents/Projects%20Coding/Skill%20Lens/docs/validation/two-surface-orchestration/2026-10-17/setup.md)
**Status:** Prepared Handoff / Setup & Amendment Approved and Frozen / Execution Pending Human Startup
**Canonical Synthetic Checkout:** `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout`
**Target Fixture File:** `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt` (Initial SHA256: `462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e`)
**Owned Artifacts Directory:** `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts`

---

## Operator Startup Instructions

This document is a **human startup handoff**, not automated execution. It contains the approved interactive startup sequence and the exact coordinator brief to paste into the interactive Hermes CLI once the human operator has initiated the isolated Herdr session:

### Step 1: Open Terminal and Launch Herdr Test Session
From a clean user terminal outside Herdr:
```bash
herdr --session skill-lens-pilot-20261017
```

### Step 2: Confirm Genuine Herdr Environment Gate in Pane
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

### Step 5: Supply Pilot Brief Interactively
When the Hermes prompt (`> `) is ready, copy and paste the complete coordinator brief below into the session.

---

## Coordinator Prompt / Brief to Paste into Hermes

```text
You are coordinator Sol operating inside approved Herdr session "skill-lens-pilot-20261017".
Your role is to orchestrate the Phase B synthetic pilot for the Skill Lens two-surface orchestration plan.

INITIAL CONTEXT STEP:
Before any Herdr control, verify test "${HERDR_ENV:-}" = 1; if it fails STOP. Explicitly read these two read-only operative plans and obey both:
  /Users/corvette/Documents/Projects Coding/Skill Lens/docs/plans/2026-10-17-two-surface-orchestration.md @ 58d48cea483804b22767b381c6edd8274fe6ad44
  /Users/corvette/Documents/Projects Coding/Skill Lens/docs/plans/2026-10-17-herdr-native-pilot-critic-amendment.md @ b99e212a55b20757eeda8605db4edcc59aad6107
Because Hermes was launched with --ignore-rules (which suppresses AGENTS.md, SOUL.md, memories, and auto-loaded skills), you MUST explicitly read the Herdr skill into your context by running:
  herdr --skill
Read and follow its rules for controlling panes, agents, and parsing JSON output.

CONTEXT & ISOLATION BOUNDS:
1. Working Directory: /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout
2. Allowed Implementation Target: fixture.txt (Initial SHA256: 462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e, content "pilot status: pending\n")
3. Fixture Command Isolation:
   - Use command-local env prefixes for fixture commands:
     HOME="/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-home" XDG_CONFIG_HOME="/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-xdg" <command>
   - Do NOT run shell-wide export of HOME/XDG in the parent shell.
   - Owned Artifacts Directory: /tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts
4. Original Repository & Environment Bounds:
   - Original Repository strictly READ-ONLY: /Users/corvette/Documents/Projects Coding/Skill Lens must NOT be modified. Do not write to, stage, commit, or push in the original repository.
   - Capture fingerprint of original repository before and after operations to verify zero writes occurred.
   - CLI auth stays in standard user paths (~/.hermes, ~/.pi, ~/.gemini); do NOT globally overwrite HOME for parent agent processes.
   - Do NOT touch live user skills under ~/.pi/agent/skills or ~/.gemini/skills.
   - Do NOT edit active process files or the frozen plan.
   - No live control from outside Herdr, fake env, neighboring sessions, provider substitution, global config/routes/plugins/credentials/services/app changes.
   - Report Output Exception: Writes are permitted strictly and exclusively to the owned artifact directory /tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/ (outside the fixture path).

PILOT EXERCISE EXECUTION (P01–P09):
Read the pilot test matrix in the original repository:
  /Users/corvette/Documents/Projects Coding/Skill Lens/docs/validation/two-surface-orchestration/2026-10-17/pilot.md
(Relative paths from the synthetic checkout will not resolve; keep the original repo strictly read-only.)

- P01: Coordinator Entry & Context
  - Verify observed documented fields HERDR_ENV=1 and HERDR_PANE_ID.
  - Verify fresh-context: confirm that Hermes --ignore-rules suppressed repository AGENTS.md, SOUL.md, memories, and auto-loaded skills.
  - Derive real session identity using installed documented in-Herdr status/readback without requiring an unevidenced HERDR_SESSION_NAME:
      herdr status --json
    Parse session info from the JSON response and retain raw evidence, or mark session identity unverified.
  - Verify active model route (gpt-6.1-sol-900k via Sol proxy on 127.0.0.1:8787; upstream identity unverified).
  - Explicitly run `herdr --skill` to read the Herdr tool/pane guidelines into coordinator context.
  - Integration proof: demonstrate interaction with Herdr runtime (e.g. read status, list panes).
  - Record correlation token: herdr-pilot-20261017-p01.

- P02: Two Independent Critics in One Wave (Pre-Edit Baseline Wave)
  - Both native critic launch templates are approved and frozen under amendment b99e212a55b20757eeda8605db4edcc59aad6107:
      Critic 1: Pi on native provider=anymodel / model=qwen/qwen3.8-max with thinking high
      Critic 2: Pi on native provider=workbuddy / model=deepseek-v4.1-flash with thinking high
  - Obtain two distinct available interactive shell panes by splitting or listing panes:
      PANE1_ID=$(herdr pane split --current --direction right --cwd "$PWD" --no-focus | python3 -c 'import sys, json; print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')
      PANE2_ID=$(herdr pane split --current --direction down --cwd "$PWD" --no-focus | python3 -c 'import sys, json; print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')
    Verify non-empty pane IDs and distinctness against each other and coordinator pane:
      test -n "$PANE1_ID" || { echo "Failed to parse PANE1_ID: empty split result"; exit 1; }
      test -n "$PANE2_ID" || { echo "Failed to parse PANE2_ID: empty split result"; exit 1; }
      test "$PANE1_ID" != "$PANE2_ID" || { echo "Pane collision between pane 1 and pane 2: $PANE1_ID"; exit 1; }
      test "$PANE1_ID" != "$HERDR_PANE_ID" || { echo "PANE1_ID collides with coordinator pane: $PANE1_ID"; exit 1; }
      test "$PANE2_ID" != "$HERDR_PANE_ID" || { echo "PANE2_ID collides with coordinator pane: $PANE2_ID"; exit 1; }
    Parse ready shell-pane IDs strictly from actual JSON output. Do NOT guess or hardcode pane IDs. Ensure both panes are ready at interactive foreground shell prompts before agent start. STOP on failed split, failed start, or failed prompt rather than falling back to empty ID or focused pane. Handle failure logs, preserve uncertain delivered state; no blind resend.
  - Generate unique lowercase short tokens (uuid hex12 via Python) per critic, strictly matching Herdr name regex ^[a-z][a-z0-9_-]{0,31}$:
      TOKEN1=$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')
      TOKEN2=$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')
      test "$TOKEN1" != "$TOKEN2" || { echo "Token collision"; exit 1; }
      CRITIC1_NAME="critic-qwen-${TOKEN1}"
      CRITIC2_NAME="critic-deepseek-${TOKEN2}"
      python3 -c 'import re, sys; p = re.compile(r"^[a-z][a-z0-9_-]{0,31}$"); [sys.exit(1) for n in sys.argv[1:] if not p.match(n)]' "$CRITIC1_NAME" "$CRITIC2_NAME" || { echo "Regex validation failed"; exit 1; }
  - Exclusive dispatch root and fresh empty sessions subdirectories:
    Do NOT use date+%s or mkdir -p (which permit directory reuse). Require nonexisting dispatch roots created exclusively via tempfile.mkdtemp inside owned artifact root, and create empty fresh sessions subdirs with mkdir WITHOUT -p:
      ARTIFACT_ROOT="/tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts"
      CRITIC1_DIR=$(python3 -c "import tempfile; print(tempfile.mkdtemp(prefix='pi-critic-qwen-${TOKEN1}-', dir='${ARTIFACT_ROOT}'))")
      SESS_DIR1="${CRITIC1_DIR}/sessions"
      mkdir "${SESS_DIR1}"  # Fails if already exists; ensures empty fresh directory

      CRITIC2_DIR=$(python3 -c "import tempfile; print(tempfile.mkdtemp(prefix='pi-critic-deepseek-${TOKEN2}-', dir='${ARTIFACT_ROOT}'))")
      SESS_DIR2="${CRITIC2_DIR}/sessions"
      mkdir "${SESS_DIR2}"  # Fails if already exists; ensures empty fresh directory
  - Launch Critic 1 in pane 1:
      herdr agent start "$CRITIC1_NAME" --kind pi --pane "$PANE1_ID" -- --provider anymodel --model qwen/qwen3.8-max --thinking high --tools read,grep,find,ls --no-mcp --no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts --no-skills --no-context-files --session-dir "$SESS_DIR1"
  - Launch Critic 2 in pane 2:
      herdr agent start "$CRITIC2_NAME" --kind pi --pane "$PANE2_ID" -- --provider workbuddy --model deepseek-v4.1-flash --thinking high --tools read,grep,find,ls --no-mcp --no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts --no-skills --no-context-files --session-dir "$SESS_DIR2"
  - Confirm successful start and readiness before prompting:
      herdr agent get "$CRITIC1_NAME"
      herdr agent get "$CRITIC2_NAME"
    Retain actual process IDs (PID) and session IDs. Confirm distinct PIDs, distinct session IDs, distinct agent names, and no --continue/--resume flags. Distinguish template parameters from observed runtime independence.
  - Target Fingerprint: Record SHA256 of /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt before review (expected initial: 462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e).
  - Complete Independent Supplied Briefs Defined Before Submission:
    Define PROMPT_QWEN and PROMPT_DEEPSEEK as complete independent supplied briefs before submission:

    PROMPT_QWEN="READ-ONLY CRITIC TASK. You are reviewing, not implementing.

Do NOT create, edit, move, delete or rename any file in the repository. Do NOT run
any command that writes: no formatters, no linters with --fix, no install, no
git commit/checkout/stash, no snapshot or golden regeneration, no test runs that
write into the checkout. Test output, if you need it, goes only to a temporary
directory outside the repository.

If you believe a change is required, do not make it. Report it instead.

Return only the report format below. Nothing else.
Note: T3 permission and interaction fields are N/A on Herdr; record native controls instead and leave upstream model identity unverified.

Target: /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt
Inspect the fixture file and report its status.

DISPATCH_TOKEN:   ${TOKEN1}
TARGET_PATH:      /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt
TARGET_SHA256:    462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e
EFFECTIVE_MODEL:  [ provider/model, settings, runtimeMode=N/A, interactionMode=N/A, native controls | evidence: requested vs configured vs confirmed/unverified ]
VERDICT:          pass | changes_required | unverified
BLOCKERS:         [ location, problem, expected behaviour, evidence ]
SUGGESTIONS:      [ ... ]        non-blocking
FILES_AT_RISK:    [ ... ]
CONCEDED:         [ ... ]        points withdrawn after argument"

    PROMPT_DEEPSEEK="READ-ONLY CRITIC TASK. You are reviewing, not implementing.

Do NOT create, edit, move, delete or rename any file in the repository. Do NOT run
any command that writes: no formatters, no linters with --fix, no install, no
git commit/checkout/stash, no snapshot or golden regeneration, no test runs that
write into the checkout. Test output, if you need it, goes only to a temporary
directory outside the repository.

If you believe a change is required, do not make it. Report it instead.

Return only the report format below. Nothing else.
Note: T3 permission and interaction fields are N/A on Herdr; record native controls instead and leave upstream model identity unverified.

Target: /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt
Inspect the fixture file and report its status.

DISPATCH_TOKEN:   ${TOKEN2}
TARGET_PATH:      /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt
TARGET_SHA256:    462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e
EFFECTIVE_MODEL:  [ provider/model, settings, runtimeMode=N/A, interactionMode=N/A, native controls | evidence: requested vs configured vs confirmed/unverified ]
VERDICT:          pass | changes_required | unverified
BLOCKERS:         [ location, problem, expected behaviour, evidence ]
SUGGESTIONS:      [ ... ]        non-blocking
FILES_AT_RISK:    [ ... ]
CONCEDED:         [ ... ]        points withdrawn after argument"

  - Concurrent Prompt Submission Requirement:
    Both native prompt submission jobs must start BEFORE parent completion collection!
    Inspect existing blocked/working state before sends (herdr agent get); ensure both agents are idle.
    Launch prompt submissions in background jobs to ensure concurrent dispatch:
      herdr agent prompt "$CRITIC1_NAME" "$PROMPT_QWEN" --wait --timeout 180000 > "${ARTIFACT_ROOT}/prompt-qwen-${TOKEN1}.log" 2>&1 &
      PID_QWEN=$!
      herdr agent prompt "$CRITIC2_NAME" "$PROMPT_DEEPSEEK" --wait --timeout 180000 > "${ARTIFACT_ROOT}/prompt-deepseek-${TOKEN2}.log" 2>&1 &
      PID_DEEPSEEK=$!

    Wait for both jobs and record separate prompt results including each exit code, not only logs:
      wait $PID_QWEN
      EXIT_QWEN=$?
      wait $PID_DEEPSEEK
      EXIT_DEEPSEEK=$?
      echo "Qwen prompt exit code: $EXIT_QWEN" | tee -a "${ARTIFACT_ROOT}/prompt-qwen-${TOKEN1}.result"
      echo "DeepSeek prompt exit code: $EXIT_DEEPSEEK" | tee -a "${ARTIFACT_ROOT}/prompt-deepseek-${TOKEN2}.result"

    Note on Lifecycle Waits:
    Native `agent prompt --wait` tracks settled states (idle/done/blocked), not turn identity. If timeout or stalled, inspect `herdr agent get` and `herdr agent read` before deciding what to do; do not duplicate sends on uncertainty.

    Read reports via:
      herdr agent read "$CRITIC1_NAME" --source recent-unwrapped --lines 150
      herdr agent read "$CRITIC2_NAME" --source recent-unwrapped --lines 150

    Report Envelope Binding:
    Require exact token + target-path + hash match!
    Bind reports strictly by matching DISPATCH_TOKEN, TARGET_PATH, and TARGET_SHA256.
    Verify target fixture SHA256 remains unchanged after review.

- P03: Implementer Execution (agy) & Post-Implementation Review Wave
  - Unique implementer token and regex-valid name:
      WORKER_TOKEN=$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')
      WORKER_NAME="worker-${WORKER_TOKEN}"
      python3 -c 'import re, sys; p = re.compile(r"^[a-z][a-z0-9_-]{0,31}$"); [sys.exit(1) for n in sys.argv[1:] if not p.match(n)]' "$WORKER_NAME" || { echo "Worker name regex validation failed"; exit 1; }
  - Target Path: /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt
  - Target Initial SHA256: 462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e
  - Original Repository Fingerprint Before Edit:
    Record fingerprint of /Users/corvette/Documents/Projects Coding/Skill Lens before implementer execution:
      (cd "/Users/corvette/Documents/Projects Coding/Skill Lens" && python3 /tmp/skill-lens-herdr-execution-20261017-cg7iv351/snapshot_tree.py save "${ARTIFACT_ROOT}/repo-fingerprint-before-p03.json")
    This existing external helper records HEAD, status and SHA256 of every tracked and nonignored untracked file plus symlink targets; status alone cannot detect an edit to an already-dirty file. Never write fingerprint artifacts inside the repository.
  - Obtain a ready shell pane parsed from JSON and launch agy:
      PANE3_ID=$(herdr pane split --current --direction down --cwd "$PWD" --no-focus | python3 -c 'import sys, json; print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')
      test -n "$PANE3_ID" || { echo "Failed to parse PANE3_ID: empty split result"; exit 1; }
      test "$PANE3_ID" != "$HERDR_PANE_ID" || { echo "PANE3_ID collides with coordinator pane"; exit 1; }
      test "$PANE3_ID" != "$PANE1_ID" && test "$PANE3_ID" != "$PANE2_ID" || { echo "PANE3_ID collides with previous wave panes"; exit 1; }
    Ensure pane 3 is ready at an interactive foreground shell prompt before agent start. STOP on failed split.
      herdr agent start "$WORKER_NAME" --kind agy --pane "$PANE3_ID" -- --model gemini-3.8-flash-high --effort high --sandbox
    (Note: --sandbox is an advertised terminal restriction, not certified filesystem containment.)
  - Confirm successful start and readiness before prompting:
      herdr agent get "$WORKER_NAME"
    Retain actual PID and session ID. Confirm agent is running, idle, and not resuming prior worker sessions (no automatic prior worker session resume).
  - Complete Independent Implementer Prompt Defined Before Submission:
    Define WORKER_PROMPT with strict constraints, output authority, and implementer schema:

    WORKER_PROMPT="SYNTHETIC IMPLEMENTATION TASK. You are sole implementer.

Do NOT create, edit, move, delete or rename any file in the repository /Users/corvette/Documents/Projects Coding/Skill Lens.
Do NOT delegate to any subagent. Do NOT review code. Do NOT run git commit. Do NOT run git push.
Output authority: You are permitted ONLY to make one tiny synthetic edit to the specified fixture file:
  /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt
Change the content of that file from:
pilot status: pending
to:
pilot status: synthetic implementation complete
Do NOT touch any other file or directory. Any test or temporary output must go strictly to /tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts.

Return only the implementer report schema below. Echo DISPATCH_TOKEN, TARGET_PATH, and TARGET_SHA256 exactly as supplied.
T3 permission/interaction fields are N/A on Herdr; record native controls instead and leave upstream model identity unverified.

DISPATCH_TOKEN:   ${WORKER_TOKEN}
TARGET_PATH:      /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt
TARGET_SHA256:    462b045a567486e8acd32f21f3861cb101a4b9c6ccbbb18613615c2ec707014e
EFFECTIVE_MODEL:  [ provider/model, settings, runtimeMode=N/A, interactionMode=N/A, native controls | evidence: requested vs configured vs provider-confirmed/unverified ]
OUTCOME:          succeeded | failed
FILES_CHANGED:    [ fixture.txt ]
CHECKS:           [ ... ]
TESTS_ADDED:      [ none ]
DEVIATIONS_FROM_PLAN: [ none ]
BLOCKED_ON:       [ none ]"

  - Prompt Send, Result Capture & Response Acceptance:
    Send prompt to agy implementer, capturing logs and exit code:
      herdr agent prompt "$WORKER_NAME" "$WORKER_PROMPT" --wait --timeout 180000 > "${ARTIFACT_ROOT}/prompt-worker-${WORKER_TOKEN}.log" 2>&1
      EXIT_WORKER=$?
      echo "Worker prompt exit code: $EXIT_WORKER" | tee -a "${ARTIFACT_ROOT}/prompt-worker-${WORKER_TOKEN}.result"

    Read implementer report via:
      herdr agent read "$WORKER_NAME" --source recent-unwrapped --lines 150

    Bind and accept implementer report strictly by matching DISPATCH_TOKEN ($WORKER_TOKEN), TARGET_PATH, and TARGET_SHA256 (initial 462b045a...). If timeout or stalled, inspect `herdr agent get "$WORKER_NAME"` and `herdr agent read "$WORKER_NAME"`; do not duplicate sends on uncertainty; stop on failure.

  - Sol Independent Verification:
    Sol independently verifies git diff on synthetic checkout without committing:
      git -C /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout diff fixture.txt
    Calculate revised SHA256 of fixture.txt:
      TARGET_REVISED_SHA256=$(python3 -c "import hashlib; print(hashlib.sha256(open('/tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt', 'rb').read()).hexdigest())")
      echo "Target revised SHA256: $TARGET_REVISED_SHA256"

  - Verify Original Repository Untouched:
      (cd "/Users/corvette/Documents/Projects Coding/Skill Lens" && python3 /tmp/skill-lens-herdr-execution-20261017-cg7iv351/snapshot_tree.py compare "${ARTIFACT_ROOT}/repo-fingerprint-before-p03.json") > "${ARTIFACT_ROOT}/repo-fingerprint-after-p03.json"
    Parse that comparison JSON; require changed_paths=[] AND head_unchanged=true AND status_unchanged=true. The helper prints evidence and does not signal differences with an error exit code. Any difference stops the pilot; preserve evidence and never blindly restore.

  - Post-Implementation Review Wave with FRESH Critics:
    P02 pre-edit round does not prove post-implementation review. Hand the revised fixture to FRESH critics with NEW tokens (TOKEN3, TOKEN4), NEW empty session directories created exclusively, and separate processes/panes:
    - Generate unique lowercase short tokens (uuid hex12 via Python) per fresh critic, strictly matching Herdr name regex ^[a-z][a-z0-9_-]{0,31}$:
        TOKEN3=$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')
        TOKEN4=$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')
        test "$TOKEN3" != "$TOKEN4" || { echo "Token collision between TOKEN3 and TOKEN4"; exit 1; }
        test "$TOKEN3" != "$TOKEN1" && test "$TOKEN3" != "$TOKEN2" && test "$TOKEN3" != "$WORKER_TOKEN" || { echo "Token collision with prior tokens"; exit 1; }
        test "$TOKEN4" != "$TOKEN1" && test "$TOKEN4" != "$TOKEN2" && test "$TOKEN4" != "$WORKER_TOKEN" || { echo "Token collision with prior tokens"; exit 1; }
        CRITIC3_NAME="critic-qwen-${TOKEN3}"
        CRITIC4_NAME="critic-deepseek-${TOKEN4}"
        python3 -c 'import re, sys; p = re.compile(r"^[a-z][a-z0-9_-]{0,31}$"); [sys.exit(1) for n in sys.argv[1:] if not p.match(n)]' "$CRITIC3_NAME" "$CRITIC4_NAME" || { echo "Fresh critic regex validation failed"; exit 1; }
    - Obtain two distinct available interactive shell panes:
        PANE4_ID=$(herdr pane split --current --direction right --cwd "$PWD" --no-focus | python3 -c 'import sys, json; print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')
        PANE5_ID=$(herdr pane split --current --direction down --cwd "$PWD" --no-focus | python3 -c 'import sys, json; print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')
      Verify non-empty pane IDs and distinctness against coordinator and all prior panes:
        test -n "$PANE4_ID" || { echo "Failed to parse PANE4_ID: empty split result"; exit 1; }
        test -n "$PANE5_ID" || { echo "Failed to parse PANE5_ID: empty split result"; exit 1; }
        test "$PANE4_ID" != "$PANE5_ID" || { echo "Pane collision between pane 4 and pane 5: $PANE4_ID"; exit 1; }
        test "$PANE4_ID" != "$HERDR_PANE_ID" && test "$PANE5_ID" != "$HERDR_PANE_ID" || { echo "Pane collides with coordinator pane"; exit 1; }
        test "$PANE4_ID" != "$PANE1_ID" && test "$PANE4_ID" != "$PANE2_ID" && test "$PANE4_ID" != "$PANE3_ID" || { echo "PANE4_ID collides with prior wave panes"; exit 1; }
        test "$PANE5_ID" != "$PANE1_ID" && test "$PANE5_ID" != "$PANE2_ID" && test "$PANE5_ID" != "$PANE3_ID" || { echo "PANE5_ID collides with prior wave panes"; exit 1; }
      Ensure both panes are ready interactive foreground shell prompts before agent start. STOP on failed split.
    - Exclusive dispatch root and fresh empty session directories created exclusively without -p:
        CRITIC3_DIR=$(python3 -c "import tempfile; print(tempfile.mkdtemp(prefix='pi-critic-qwen-${TOKEN3}-', dir='${ARTIFACT_ROOT}'))")
        SESS_DIR3="${CRITIC3_DIR}/sessions"
        mkdir "${SESS_DIR3}"  # Fails if already exists; ensures empty fresh directory

        CRITIC4_DIR=$(python3 -c "import tempfile; print(tempfile.mkdtemp(prefix='pi-critic-deepseek-${TOKEN4}-', dir='${ARTIFACT_ROOT}'))")
        SESS_DIR4="${CRITIC4_DIR}/sessions"
        mkdir "${SESS_DIR4}"  # Fails if already exists; ensures empty fresh directory
    - Launch fresh Critic 1 in pane 4:
        herdr agent start "$CRITIC3_NAME" --kind pi --pane "$PANE4_ID" -- --provider anymodel --model qwen/qwen3.8-max --thinking high --tools read,grep,find,ls --no-mcp --no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts --no-skills --no-context-files --session-dir "$SESS_DIR3"
    - Launch fresh Critic 2 in pane 5:
        herdr agent start "$CRITIC4_NAME" --kind pi --pane "$PANE5_ID" -- --provider workbuddy --model deepseek-v4.1-flash --thinking high --tools read,grep,find,ls --no-mcp --no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts --no-skills --no-context-files --session-dir "$SESS_DIR4"
    - Confirm successful start and readiness before prompting:
        herdr agent get "$CRITIC3_NAME"
        herdr agent get "$CRITIC4_NAME"
      Retain actual PIDs and session IDs. Confirm distinct PIDs, distinct session IDs, distinct agent names, and no --continue/--resume flags.
    - Complete Independent Supplied Briefs Defined Before Submission with REVISED target SHA256:
        PROMPT_QWEN_P03="READ-ONLY CRITIC TASK. You are reviewing, not implementing.

Do NOT create, edit, move, delete or rename any file in the repository. Do NOT run
any command that writes: no formatters, no linters with --fix, no install, no
git commit/checkout/stash, no snapshot or golden regeneration, no test runs that
write into the checkout. Test output, if you need it, goes only to a temporary
directory outside the repository.

If you believe a change is required, do not make it. Report it instead.

Return only the report format below. Nothing else.
Note: T3 permission and interaction fields are N/A on Herdr; record native controls instead and leave upstream model identity unverified.

Target: /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt
Inspect the revised fixture file and report its post-implementation status.

DISPATCH_TOKEN:   ${TOKEN3}
TARGET_PATH:      /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt
TARGET_SHA256:    ${TARGET_REVISED_SHA256}
EFFECTIVE_MODEL:  [ provider/model, settings, runtimeMode=N/A, interactionMode=N/A, native controls | evidence: requested vs configured vs confirmed/unverified ]
VERDICT:          pass | changes_required | unverified
BLOCKERS:         [ location, problem, expected behaviour, evidence ]
SUGGESTIONS:      [ ... ]        non-blocking
FILES_AT_RISK:    [ ... ]
CONCEDED:         [ ... ]        points withdrawn after argument"

        PROMPT_DEEPSEEK_P03="READ-ONLY CRITIC TASK. You are reviewing, not implementing.

Do NOT create, edit, move, delete or rename any file in the repository. Do NOT run
any command that writes: no formatters, no linters with --fix, no install, no
git commit/checkout/stash, no snapshot or golden regeneration, no test runs that
write into the checkout. Test output, if you need it, goes only to a temporary
directory outside the repository.

If you believe a change is required, do not make it. Report it instead.

Return only the report format below. Nothing else.
Note: T3 permission and interaction fields are N/A on Herdr; record native controls instead and leave upstream model identity unverified.

Target: /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt
Inspect the revised fixture file and report its post-implementation status.

DISPATCH_TOKEN:   ${TOKEN4}
TARGET_PATH:      /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt
TARGET_SHA256:    ${TARGET_REVISED_SHA256}
EFFECTIVE_MODEL:  [ provider/model, settings, runtimeMode=N/A, interactionMode=N/A, native controls | evidence: requested vs configured vs confirmed/unverified ]
VERDICT:          pass | changes_required | unverified
BLOCKERS:         [ location, problem, expected behaviour, evidence ]
SUGGESTIONS:      [ ... ]        non-blocking
FILES_AT_RISK:    [ ... ]
CONCEDED:         [ ... ]        points withdrawn after argument"

    - Concurrent Prompt Submission Requirement:
      Both native prompt submission jobs must start BEFORE parent completion collection!
      Inspect existing blocked/working state before sends (herdr agent get); ensure both agents are idle.
      Launch prompt submissions in background jobs to ensure concurrent dispatch:
        herdr agent prompt "$CRITIC3_NAME" "$PROMPT_QWEN_P03" --wait --timeout 180000 > "${ARTIFACT_ROOT}/prompt-qwen-${TOKEN3}.log" 2>&1 &
        PID_QWEN_P03=$!
        herdr agent prompt "$CRITIC4_NAME" "$PROMPT_DEEPSEEK_P03" --wait --timeout 180000 > "${ARTIFACT_ROOT}/prompt-deepseek-${TOKEN4}.log" 2>&1 &
        PID_DEEPSEEK_P03=$!

      Wait for both jobs and record separate prompt results including each exit code:
        wait $PID_QWEN_P03
        EXIT_QWEN_P03=$?
        wait $PID_DEEPSEEK_P03
        EXIT_DEEPSEEK_P03=$?
        echo "Qwen P03 prompt exit code: $EXIT_QWEN_P03" | tee -a "${ARTIFACT_ROOT}/prompt-qwen-${TOKEN3}.result"
        echo "DeepSeek P03 prompt exit code: $EXIT_DEEPSEEK_P03" | tee -a "${ARTIFACT_ROOT}/prompt-deepseek-${TOKEN4}.result"

      Read reports via:
        herdr agent read "$CRITIC3_NAME" --source recent-unwrapped --lines 150
        herdr agent read "$CRITIC4_NAME" --source recent-unwrapped --lines 150

      Report Envelope Binding:
      Require exact token + target-path + hash match!
      Bind reports strictly by matching DISPATCH_TOKEN ($TOKEN3 and $TOKEN4), TARGET_PATH, and TARGET_SHA256 ($TARGET_REVISED_SHA256).
      Verify target fixture SHA256 remains unchanged after review wave.

    - Verify Original Repository Untouched After Post-Implementation Wave:
        (cd "/Users/corvette/Documents/Projects Coding/Skill Lens" && python3 /tmp/skill-lens-herdr-execution-20261017-cg7iv351/snapshot_tree.py compare "${ARTIFACT_ROOT}/repo-fingerprint-before-p03.json") > "${ARTIFACT_ROOT}/repo-fingerprint-after-p03-post-review.json"
      Parse comparison JSON; require changed_paths=[] AND head_unchanged=true AND status_unchanged=true. Any difference stops the pilot; preserve evidence and never blindly restore. Repeat this content-fingerprint comparison across the full pilot.

- P04: Deliberately Long Response & Completeness Validation
  - Deliberately Long Response:
    Prompt critic for a structured, multi-section response containing numbered items (e.g. 1..100) or detailed findings with explicit markers:
      ===REPORT_START===
      DISPATCH_TOKEN: ...
      TARGET_SHA256: ...
      [numbered payload]
      ===REPORT_END===
  - Completeness Validation:
    Coordinator must recover the actual generated assistant response, not the echoed input prompt. Verify every expected numbered item exactly once and in order plus start/end markers and matching token, target path and hash. An end marker alone does not prove an untruncated middle. Keep the existing report fields and add the numbered payload within an existing field. Record native control fields as N/A where T3-only and leave upstream identity unverified.
  - If truncated in viewport/recent read, increase supported --lines (e.g. --lines 300 or --lines 500).
  - Pi Reporting Policy:
    Built-in write and edit tools are excluded, and MCP is disabled (--no-mcp). These read-only Pi critics CANNOT write fallback markdown files.
    P04 requires complete native response capture via Herdr terminal inspection (`herdr agent read ...`) OR marking capability unavailable and stopping!
    Other agent kinds fallback only if permitted.
    Do NOT grant write or shell tools to rescue capture!
    Coordinator may retain recovered report text in /tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/ under coordinator authority.

- P05: Permission & Question Handling
  - Observe actual blocked question UI:
    Observe whether Herdr actually detects an interactive question/approval UI as `blocked`; detection is an unverified pilot assertion, not a guaranteed result.
    Inspect blocked state via `herdr agent get <name>` and `herdr agent read <name>`.
    Inspect and respond only to authorized narrow reads. If an UNKNOWN or wider dialog appears, STOP immediately.
  - Harmless Denied-Write Probe:
    Submit prompt asking read-only critic to write/touch a scratch file. Observe tool rejection / lack of write capability.
    Verify target fixture and original repository fingerprints remain completely unchanged.
    Record exact boundary: refusal alone is not universal sandbox enforcement.

- P06: Fast Completion & Stale-Delivery Reconciliation
  - Deliberate false-settle and fast/stalled/uncertain reconciliation:
    Exercise deliberate false-settle observation (e.g. agent appears idle before completing, or completes exceptionally fast, or `agent_prompt_stalled` occurs when no activity is observed within 5000ms, or caller timeout).
    Inspect `herdr agent get` and `herdr agent read`.
    Reconcile single submission without duplicate prompt sends or accepting stale reports.

- P07: Active Cancellation, Process Evidence & Negative Guards
  - Representative Owned Active/Background Command:
    Launch an owned command in an agent/shell pane (e.g. long-running background sleep or calculation).
  - Send interrupt:
      herdr agent send-keys <target> ctrl+c
  - Collect explicit bounded PID/job evidence after interrupt: inspect ps / pane output to verify process actually terminated; confirm NO uncontrolled orphan processes remain!
  - Unresolved-Liveness Synthetic Rejection:
    If a background process remains active, coordinator marks state interrupted/unknown and rejects new task dispatch until the liveness is cleared.
  - Synthetic Token Mismatch Rejection:
    Submit a synthetic report echoing DISPATCH_TOKEN: corrupted-token-999; verify coordinator outright rejects the report.

- P08: Detach and Controlled Restart
  - Human detach vs human controlled owned-session stop/relaunch are SEPARATE exercises.
  - 1. Human Detach Exercise:
    Instruct human operator to detach from the running session using documented Herdr UI (use documented UI and retain the actual action taken, rather than inventing unverified shortcuts).
    Observe and record whether the owned session and worker processes continue in background; do not infer that they do from the detached UI. Save identities for comparison.
  - 2. Human Controlled Owned-Session Stop & Relaunch:
    Read installed help: `herdr session stop <NAME>` and `herdr session attach <NAME>`.
    ONLY external HUMAN may stop the exact owned pilot session after saved evidence and owned stop checks:
      herdr session stop skill-lens-pilot-20261017
    NO agent outside Herdr controls!
    NO stopping shared server (`herdr server stop` is strictly prohibited; keep continuing coordinator and dirty/user resources safe).
    Fresh Human Hermes Startup & Brief:
      herdr --session skill-lens-pilot-20261017
    Inside pane, launch fresh Hermes coordinator using the approved direct command, verify the genuine gate and clean context, and supply a continuation brief with retained evidence and the remaining P08/P09 steps. Do not blindly replay this full brief or repeat completed edits/probes. Record the earlier coordinator as intentionally ended by the human-owned restart; cleanup must preserve the new continuing coordinator.
    No Restored-Layout Inference: Do NOT infer from layout/window restoration that worker processes or task state persisted.

- P09: cmux Interaction & Protected Cleanup
  - cmux Interaction Proof:
    --version alone is insufficient!
    Invoke cmux via absolute CLI wrapper:
      /Applications/cmux.app/Contents/Resources/bin/cmux --help
    Execute actual wrapper command/query (e.g. workspace/surface inspection) without focus theft.
  - Protected Cleanup Proof:
    Exercise cleanup logic; verify user work, coordinator pane, and dirty worktrees are strictly exempt from cleanup.

OUTPUT CONTRACT:
For each exercise, record reproducible log evidence strictly into owned artifact directory:
  /tmp/skill-lens-herdr-execution-20261017-cg7iv351/pilot-artifacts/
Do NOT write to or update files in the original repository (/Users/corvette/Documents/Projects Coding/Skill Lens). T3 Sol will later inspect the owned artifact directory and retain sanitized results in allowed repo files. Never paper-pass any unexecuted case.
```
