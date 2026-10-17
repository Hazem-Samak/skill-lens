<task>
You are the sole implementer Antigravity, explicitly selected Gemini 3.8 Flash High. Implement only the preflight/setup-proposal portion of Phase B of docs/plans/2026-10-17-two-surface-orchestration.md @ frozen commit 58d48cea483804b22767b381c6edd8274fe6ad44. Current checkout main HEAD a0ffa9edee8226d7d8b981002b265510bced8a16; plan freeze is pushed and remote-verified. Read the frozen file with git show and verify current operative text differs from that frozen version only in Reference. Read AGENTS.md and current process/council/implementation-loop.
Full migration is authorized, but this bounded dispatch MUST NOT perform Phase C process edits before the required pilot. This T3 environment is outside Herdr (HERDR_ENV absent); you may not inspect/control a focused Herdr session from here. The Sol proxy port 127.0.0.1:8787 is listening (TCP probe only, no actual request/model identity confirmed).
</task>
<goal>
Produce a concrete, reviewable setup proposal and human startup handoff within the frozen bounds, plus honest pending pilot evidence. Establish the exact installed CLI launch/permission controls through read-only help and targeted config reads. Stop at the explicit session/lifecycle + native role-mapping approval and Herdr-inside-entry boundary. Do NOT claim a pilot pass or migration completion.
</goal>
<allowed_writes>
docs/validation/two-surface-orchestration/2026-10-17/setup.md
docs/validation/two-surface-orchestration/2026-10-17/pilot.md
docs/validation/two-surface-orchestration/2026-10-17/implementation/preflight.md
docs/validation/two-surface-orchestration/2026-10-17/implementation/preflight-receipt.json
Temporary command/test output outside repository under /tmp/skill-lens-herdr-execution-20261017-cg7iv351/worker-preflight.
Do not edit frozen plan, planning evidence, active process files, sources/tests/specs/packaging, AGENTS.md, or pre-existing untracked .path.
</allowed_writes>
<preflight_requirements>
- Verify actual versions and CLI help for required Hermes, agy, pi, Herdr and cmux; include optional opencode only to distinguish unavailable/untested capability.
- herdr --version/--skill/--help and command-group help are read-only metadata. Do not run bare herdr, server/session lifecycle or pane/agent/status inventory commands from outside a real Herdr pane. Integration status may be read only if it inspects installed plugin files without live-session interaction; otherwise mark pending.
- Read ONLY whitelisted model/config fields needed for current route/default/native policy. Never dump config/auth files or credentials, emit tokens, change aliases, install/update plugins/providers, change global policies, or create persistent hooks. Record source path/version and safe values; upstream identity stays unverified.
- agy help/models already succeeded, intended model label gemini-3.8-flash-high is available. Live T3 target antigravity model has no separate options. Existing session-standing Full access applies to T3; do not pretend it is a Herdr CLI flag.
- Propose exact kind/model/native launch settings for Hermes coordinator, agy implementer, and two critic roles that can use the user's selected MiniMax (mcode) and Pi/WorkBuddy DeepSeek settings. If no supported Herdr kind/native route can execute an intended reviewer, do not substitute. Clearly distinguish T3-selected reviewers for migration council from eventual pilot role choices needing approval. A future named-pair/mode or unsupported-kind issue is a concrete unresolved prerequisite.
- Propose dedicated project session name skill-lens and isolated pilot name skill-lens-pilot-20261017; these are proposals, not approved/launched. Plan requires user approval of actual names/startup and role mapping before pilot use.
- Provide exact user-run startup commands backed by installed help, including how Hermes running inside an owned Herdr pane gets the pilot brief. No fake HERDR_ENV injection, wrapper to evade entry gate, automated out-of-Herdr live control, service startup/repair or server restart. Human must own startup and planned test-server restart under frozen bounds.
- Pre-authorize no report success: pilot.md lists P01-P09 pending/unverified with the actual blocking prerequisites and evidence needed. Setting up the proposal is not conducting the pilot.
- Explain synthetic checkout/HOME/XDG fixture isolation separately from using existing CLI auth. No need to copy auth or user skill directories. If installed controls cannot support this safely, record exact limitation and stop.
- Report any true plan contradiction; do not amend contract or silently implement a workaround. No delegation, no nested council agents.
</preflight_requirements>
<verification_loop>
The coordinator reran baseline gates on the frozen tree; logs are /tmp/skill-lens-herdr-execution-20261017-cg7iv351/{pytest,mypy,ruff-check,ruff-format}.{log,json}. Read results, do not invent success. Required project commands are pytest --cov=skill_lens, mypy, ruff check ., ruff format --check . using repository .venv. If you run checks, isolate HOME/XDG, coverage/cache output externally and never test against live skills or regenerate pinned output. For this preflight evidence slice verify links, valid JSON, no secret content, allowed scope and no machine mutation; don't claim these certify unrun runtime. Coordinator will independently verify actual files and required final gates later.
</verification_loop>
<action_safety>
No git add/commit/push, checkout/reset/clean/stash or branch changes. Preserve every pre-existing file. Read-only checks plus the four named evidence files only. No machine mutation, server/agent launch, integration update, remote messaging or trial start. This is not permission to relax frozen policy because the full migration is authorized.
</action_safety>
<structured_output_contract>
Return the council implementer schema:
EFFECTIVE_MODEL: provider/model/settings and requested/configured/confirmed-or-unverified evidence
OUTCOME: succeeded | failed (for this preflight slice only)
FILES_CHANGED:
CHECKS: pytest= mypy= ruff-check= ruff-format=; separate own execution from coordinator evidence
TESTS_ADDED: none expected
DEVIATIONS_FROM_PLAN:
BLOCKED_ON: concrete remaining pilot approvals/actions, proposed exact mapping and commands, no runtime acceptance claimed
End with a full actionable report, not narration of what you will read next. If blocked, make the four allowed evidence files useful and return the precise boundary.
</structured_output_contract>
