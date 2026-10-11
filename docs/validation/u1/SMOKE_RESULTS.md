# U1 Wheel Smoke Test Receipts

- **Date:** 2026-10-11
- **Platform:** Darwin arm64
- **Python:** 3.11.16
- **Wheel:** `skill_lens_cli-0.1.1-py3-none-any.whl`
- **Wheel SHA-256:** `1bcc4b2b46feac61dfbda10f6d333b8f81971d2aa42be886892c6d9a256805b7`
- **Wheel Registry Files Inspected (10 files):**
  - `skill_lens/registry/agents/antigravity.toml`
  - `skill_lens/registry/agents/claude.toml`
  - `skill_lens/registry/agents/codex.toml`
  - `skill_lens/registry/agents/dsh.toml`
  - `skill_lens/registry/agents/grok.toml`
  - `skill_lens/registry/agents/omp.toml`
  - `skill_lens/registry/agents/opencode.toml`
  - `skill_lens/registry/agents/pi.toml`
  - `skill_lens/registry/agents/qoder.toml`
  - `skill_lens/registry/agents/windsurf.toml`

## 1. Lean Base Installation Lane (No Extras)

- **Execution Working Directory:** Isolated temporary directory outside checkout
- **Synthetic Environment:** Isolated `HOME` and clean `PYTHONPATH`
- **Import Provenance:** `/Users/corvette/.t3/userdata/antigravity-tmp/ac0a3dfd6ddd/run-35stmw/skill-lens-smoke-base-bd38y6rj/venv/lib/python3.14/site-packages/skill_lens/__init__.py`
- **Textual Absence:** Confirmed (`find_spec('textual') is None`)
- **Bare Noninteractive Invocation:** Exit `0`,
  usage help printed, install tip omitted.
- **Explicit `tui` Invocation:** Exit `2`,
  install hint printed to stderr (`skill-lens-cli[tui]`), traceback suppressed.

## 2. Optional `[tui]` Extra Lane

- **Execution Working Directory:** Isolated temporary directory outside checkout
- **Synthetic Environment:** Isolated `HOME` and clean `PYTHONPATH`
- **Import Provenance:** `/Users/corvette/.t3/userdata/antigravity-tmp/ac0a3dfd6ddd/run-35stmw/skill-lens-smoke-tui-6y_h17ao/venv/lib/python3.14/site-packages/skill_lens/__init__.py`
- **Installed Textual:** `Textual 8.2.8`
- **Pinned Output Suites Executed:**
  - `tests/test_render_snapshots.py` (all 17 snapshots)
  - `tests/test_fixtures.py` (all 13 scenario goldens)
  - `tests/test_phase3_gate.py` (diff golden)
  - `tests/test_phase4_gate.py` (Phase 4 doctor & compare goldens)
- **Suite Exit Code:** `0` (All 128 tests passed)
- **Output Parity:** Existing snapshots and goldens remain completely unchanged
  (fixture hashes unchanged); all 128 tests in the full pinned-output suites pass under
  the installed extra without regeneration.
