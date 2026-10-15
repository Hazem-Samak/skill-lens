# Stage F implementer brief

Only implement Stage F (F15, F16, F11 agents rendering) from docs/plans/2026-10-12-assessment-repairs.md @ fe6f89bc55eb3f4f04187567b968dd96ae9c86c1, Section 6 Stage F and original finding descriptions. Confirm that frozen reference contains this operative contract before edits. User explicitly authorized Stage F; no new planning loop. Base is 3762f10 (full hash in base.txt beside this file). Read AGENTS.md, implementation-loop, relevant specification, PHASE2/PHASE3 findings. Sole implementer Gemini 3.8 Flash High; no delegation, review, commit, push, release or installs.

Targets:
- core/diff.py: preserve final-newline information through hunk construction. Conventional \ No newline at end of file markers in existing hunk lines should explain removal/addition in live and captured JSON/terminal reports. Preserve public JSON keys. Marker lines consume character budget but never old/new line counts or changed-line budget. Truncation must preserve truthful marker association, valid range starts/counts, no context-only hunks, and honest omitted counts. Keep CRLF/LF equivalent, lone CR/other separators as ordinary content. Cover empty vs single-newline and added/removed files too.
- core/resolver.py: carry the actual unique causal winner from precedence calculation into shadow reason/rule/evidence, independent of ACTIVE vs COEXISTS display state. Do not arbitrarily select a coexisting candidate. Preserve existing role/state/ordering semantics, tie and OpenCode specificity rules, disabled/invalid eligibility, merged/ambiguous policies without fabricated suppression/winners. Use a controlled synthetic registry fixture, not an obsolete vendor behavior. Coordinator baseline reproduction is adjacent baseline-reproductions.json.
- Pin real render_agents output at fixed width, all normal rows plus unusual names/IDs/policy strings containing markup. Existing escape handling should stay correct; actual rendering assertions/snapshots must fail if output is missing or escaping breaks.

Allowed product files: skill_lens/core/diff.py, skill_lens/core/resolver.py; skill_lens/models/diff.py for documentation of marker semantics only (no keys/schema changes); skill_lens/render.py and skill_lens/presentation/text.py only if necessary to faithfully display existing hunk model (inspect actual presentation filename before using). Allowed tests: tests/test_stage_f_repairs.py (new), tests/test_phase2_gate.py, tests/test_phase3_gate.py, tests/test_render_snapshots.py, corresponding intentional new/changed tests/fixtures/snapshots/*.txt. No goldens expected to change; if an existing golden answer must change, report exact reason BEFORE regeneration. Do not edit registry TOML, config, discovery, paths, snapshot/controller/services, dependencies, CI, README/CHANGELOG or plan/admin records. If a necessary file is outside allow-list, return blocker without editing it. Preserve pre-existing untracked .path.

Tests must use mock_home/tmp_path, patched HOME/XDG and sandbox isolation; frozen report calls must read no disk/environment after capture. Use existing snapshot capture adapters to prove live/captured equivalence plus frozen content preservation. Verify JSON round-trip without schema changes, terminal marker display and causal winner display. Review snapshot differences BEFORE updating; don't regenerate unchanged historical snapshots. Keep unchanged outputs stable except intentional fixes.

Required checks via .venv/bin tools: pytest --cov=skill_lens, mypy, ruff check ., ruff format --check . (format allowed files as needed). Cache/logs outside checkout, under worker/ beside this brief. Add discriminating tests for regressions and boundary behavior. Mutation-test new guards only in disposable copies, clean/mutant/restored controls with exact diff/commands/logs. Never mutate shared checkout for proof. Coordinator will independently inspect diff, run gates and selected production mutations before MiniMax/Muse independent review. Worker reports are evidence, not acceptance.

Return exact report:
EFFECTIVE_MODEL: [provider/model, settings, runtimeMode, interactionMode | requested vs configured vs provider-confirmed/unverified]
OUTCOME: succeeded | failed
FILES_CHANGED: [...]
CHECKS: pytest= mypy= ruff-check= ruff-format= (commands/log paths and counts)
TESTS_ADDED: [...]
DEVIATIONS_FROM_PLAN: [...]
BLOCKED_ON: [...]
Include mutation proof paths and any snapshot difference review in appropriate fields. Active compute/billed tokens unavailable unless exposed.
