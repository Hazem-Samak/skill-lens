# U1 Behavioral Mutation Campaign Results

Conducted across 17 distinct mutations in an outside disposable copy
with strict import provenance, pre-execution compilation checks, and source restoration.
Full execution output logs are persisted in `docs/validation/u1/logs/`.

- **Platform:** Darwin arm64 Python 3.11.16
- **Date:** 2026-10-11
- **Total Mutations:** 17
- **Mutants Killed:** 17
- **Survivors:** 0

| ID | Guard Category | Target File | Test Module | Outcome | Targeted Assertion | Log |
| --- | --- | --- | --- | :---: | --- | :---: |
| `MUT-01` | terminal conjunction | `skill_lens/cli.py` | `tests/test_tui_routing.py` | **KILLED** | `assert len(called_with) == 0` | [`log`](logs/MUT-01_mutant.log) |
| `MUT-02` | plain override | `skill_lens/cli.py` | `tests/test_tui_routing.py` | **KILLED** | `assert len(called_with) == 0` | [`log`](logs/MUT-02_mutant.log) |
| `MUT-03` | missing-extra statuses/tip | `skill_lens/cli.py` | `tests/test_tui_routing.py` | **KILLED** | `assert result.exit_code == int(ExitCode.USAGE)` | [`log`](logs/MUT-03_mutant.log) |
| `MUT-04` | command bypass | `skill_lens/cli.py` | `tests/test_tui_routing.py` | **KILLED** | `assert '"skills":' in result.stdout` | [`log`](logs/MUT-04_mutant.log) |
| `MUT-05` | specific import-fault handling | `skill_lens/cli.py` | `tests/test_tui_routing.py` | **KILLED** | `assert result.exit_code == int(ExitCode.INTERNAL)` | [`log`](logs/MUT-05_mutant.log) |
| `MUT-06` | sandbox containment | `skill_lens/cli.py` | `tests/test_tui_routing.py` | **KILLED** | `--cwd must stay inside --sandbox` | [`log`](logs/MUT-06_mutant.log) |
| `MUT-07` | launch return propagation | `skill_lens/cli.py` | `tests/test_tui_routing.py` | **KILLED** | `assert result.exit_code == int(ExitCode.INTERNAL)` | [`log`](logs/MUT-07_mutant.log) |
| `MUT-08A` | base runtime dependency isolation | `pyproject.toml` | `tests/test_tui_packaging.py` | **KILLED** | `base dependencies must not include Textual` | [`log`](logs/MUT-08A_mutant.log) |
| `MUT-08B` | optional [tui] extra floor | `pyproject.toml` | `tests/test_tui_packaging.py` | **KILLED** | `[tui] extra must declare textual>=8.2.8` | [`log`](logs/MUT-08B_mutant.log) |
| `MUT-08C` | dev extra floor | `pyproject.toml` | `tests/test_tui_packaging.py` | **KILLED** | `[dev] extra must declare textual>=8.2.8` | [`log`](logs/MUT-08C_mutant.log) |
| `MUT-08D` | lockfile textual pin | `uv.lock` | `tests/test_tui_packaging.py` | **KILLED** | `textual must be pinned to 8.2.8` | [`log`](logs/MUT-08D_mutant.log) |
| `MUT-08E` | lockfile rich pin | `uv.lock` | `tests/test_tui_packaging.py` | **KILLED** | `rich must be pinned to 15.0.0` | [`log`](logs/MUT-08E_mutant.log) |
| `MUT-08F` | tui command registration | `skill_lens/cli.py` | `tests/test_tui_packaging.py` | **KILLED** | `must be a registered CLI command` | [`log`](logs/MUT-08F_mutant.log) |
| `MUT-09A` | base CI exit code guard | `.github/workflows/ci.yml` | `tests/test_tui_packaging.py` | **KILLED** | `CI packaging job must assert explicit tui exit code 2` | [`log`](logs/MUT-09A_mutant.log) |
| `MUT-09B` | CI [tui] lane provenance guard | `.github/workflows/ci.yml` | `tests/test_tui_packaging.py` | **KILLED** | `CI packaging job must assert skill_lens.__file__ is inside installed lane` | [`log`](logs/MUT-09B_mutant.log) |
| `MUT-10` | tip forced into noninteractive/plain fallback | `skill_lens/cli.py` | `tests/test_tui_routing.py` | **KILLED** | `assert "Tip:" not in result.stdout` | [`log`](logs/MUT-10_mutant.log) |
| `MUT-11` | installed-extra output parity | `skill_lens/render.py` | `tests/test_tui_packaging.py` | **KILLED** | `snapshot scan_variant_hash_detection.txt changed` | [`log`](logs/MUT-11_mutant.log) |

## Execution Summary

1. **Compilation Guard:** Every Python mutant is compiled via `compile(..., 'exec')`
   before execution to guarantee syntactic validity.
2. **Provenance Guard:** Pytest executes within the disposable tree with isolated
   `HOME` and `PYTHONPATH`. Import provenance is verified to point to the disposable copy.
3. **Receipt Cycle:** Each mutation cycle proves:
   - Clean control run (Exit 0) with full log persisted
   - Mutant execution resulting in pytest test failure (Exit 1) matching the targeted assertion
     without collection errors, with full log persisted
   - Source restoration executed in a `finally` block
   - Passing restoration rerun (Exit 0) with full log persisted
4. **Survivors:** Zero survivors detected across routing branches, dependency declarations,
   packaging metadata, CI workflow assertions, and output parity.
