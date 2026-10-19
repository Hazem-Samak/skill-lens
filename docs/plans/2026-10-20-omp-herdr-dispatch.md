# Plan: Herdr dispatch for the OMP coordinator

Status: Agreed
Authorization: User, 2026-10-20: “ok do this remaining small change”, accepting the proposed Herdr dispatch section plus a live check inside Herdr. Reuse this coordinator migration's explicit Sol documentation authorship and single OpenCode MiniMax reviewer selection.
Reference: pending
Surface: omp; optional Herdr-managed execution; T3 remains active and unchanged.
Risk and review: High workflow amendment; existing user-authorized one-reviewer exception for this migration. Reviewer opencode/minimax-m3.1-flash-free, default settings, fresh plan/final sessions. Upstream identity remains unverified.
Expected child tasks: one plan review and one final review; Sol makes these small process-document edits directly. Native agent startup for the live smoke requires an inherited Herdr context.

## Outcome and current state

OMP inside Herdr uses Herdr for worker panes, agent startup, prompts, waits and report readback, while retaining the existing OMP planning/implementation policy. Standalone OMP retains its current dispatch routes. Hermes is not required. T3 is untouched.

Current main is 84162645f9114a16f745c14a179658783ce85cae. Only `.path` and the old 2026-10-19 coordinator draft are untracked; preserve both. This caller has empty HERDR_ENV, HERDR_WORKSPACE_ID, HERDR_TAB_ID and HERDR_PANE_ID. No live Herdr commands may be issued or environment context fabricated from this session. This is an actual blocker to the live check, not a reason to withhold reachable documentation work or claim success.

## Scope and implementation

Allowed: this plan; docs/process/omp/herdr.md (new adapter); narrow route/link insertions in docs/process/omp/README.md, planning-loop.md and implementation-loop.md; docs/validation/omp-coordinator/2026-10-20/herdr-dispatch.md plus herdr-plan-review.txt and herdr-final-review.txt. No T3 files, product code/tests, old evidence bodies, settings, auth, installs, services, proxy or Herdr session repair.

1. Review this bounded amendment with the existing selected MiniMax reviewer. Resolve blockers and perform the standard two-commit freeze; push each authorized commit to origin/main and verify full local/tracking/remote hash equality. Existing unchanged session gate evidence satisfies baseline; run all four gates after the edits.
2. Add a compact Herdr adapter based on the loaded installed `herdr` skill. Require inherited HERDR_ENV=1 and actual caller-pane readback; outside Herdr stop Herdr operations, never export fabricated context or target the focused session. Inside, learn current installed help/status and supported agent kinds before control. Retain Sol identity and existing role/guard/risk/file-ownership rules. No creation of workspaces, tabs or different checkouts unless separately authorized.
3. For worker dispatch default to a same-cwd sibling pane with --current/--no-focus and geometry chosen from caller layout. Parse returned opaque IDs. Start the session-selected supported agent kind and explicit authorized native model/agent arguments after --, learned from installed runtime help. No guessed MiniMax Herdr startup command. Wait for actual readiness, submit guarded named work through herdr agent prompt --wait with bounded timeout, inspect agent get/read, and retain uniquely bound substantive reports. Never substitute OMP-native tasks or hidden CLI relays for requested Herdr dispatch without asking. Retain fallback only when standalone or explicitly authorized.
4. Document timeout/blocked/unknown handling, no blind resubmission, no auto-answering approvals, no idle-only completion (including background implementer work), cleanup only of owned resources. Link the adapter from the OMP entry and both loops without rewriting policy.
5. Validate links/guard policy and exercise the updated entry via a no-tools Sol smoke outside Herdr; run pytest --cov=skill_lens, mypy, ruff check ., ruff format --check .; get fresh MiniMax final review. Record and commit the document work, preserving user files. Label live Herdr operation unverified until actually exercised.
6. Live acceptance requires the human to launch Sol/OMP in a genuine Herdr pane using the existing startup command, then continue this authorized smoke there: discover the actual CLI/kinds and current pane; create one owned sibling; start the selected OpenCode MiniMax reviewer only if that installed kind/model is supported; submit a harmless read-only unique-token task and inspect matching report and actual turn completion. If detection or model startup fails, ask rather than repair/install/substitute. No target skill access or product writes. Preserve the user's coordinator pane and unrelated panes; retain the evidence in the new validation record.

## Acceptance

- Herdr-backed dispatch is selected before reviewer/implementer dispatch whenever OMP is run inside Herdr; standalone OMP still works, T3 unchanged.
- No invented runtime arguments, caller context, model identity, report or successful live run. Runtime-specific controls come from installed help in the live session. Preserve exact reviewer guard, existing safety/review/commit rules and user files.
- Relative links and startup smoke pass; all four project gates pass; independent documentation review has no blockers.
- Documents may be delivered while the live check is explicitly blocked, but the end-to-end request stays incomplete until that check succeeds. The final report must name the blocker and exact human startup step rather than say Herdr integration is verified.

## Review decisions

MiniMax plan review passed with no blockers (session ses_ea9cce0d3ffeyDu2fUNMinRPMB). Accepted the smoke limitation: a no-tools launch checks instruction loading only, never actual Herdr dispatch. Existing migration authorization and delivery explicitly use origin/main; unchanged. Rejected citing the untracked 2026-10-19 draft as frozen authority: the applicable completed migration is 2026-10-20-omp-side-by-side-coordinator.md at 216cea31cc0ac1c0ad8b1557441bf59aec141031. The exact new frozen reference is filled only after the plan commit. No Herdr operational proof is claimed.
