# Skill Lens 0.2 — Optional Installation & CLI Routing Walkthrough (U1)

> **Status:** U1 accepted by Sol on 2026-10-11 after direct verification and independent MiniMax/Muse reviews. Implemented by Antigravity Gemini 3.8 Flash High. U2 has not started.
> **Scope:** Full-Screen TUI Assignment U1 (`FULL_SCREEN_TUI.md` §6, §7, §9.1–9.2, §11 Step 1, §16, §22 U1).
> **Reference Plan:** [docs/plans/2026-10-11-tui-u1-optional-install.md](plans/2026-10-11-tui-u1-optional-install.md) @ frozen commit `e59993cad3cd1079dd040bf0831965f1a2fcbf2a`.
> **Root Checkout:** `main`; baseline was clean before implementation.

---

## 1. Executive Summary

Assignment U1 completes the optional dependency plumbing and command-line routing for the additive full-screen Terminal User Interface (TUI) while preserving existing line-command behavior, report output, and core models:

1. **Lean Base Package Guarantee:**
   - The base `skill-lens-cli` runtime dependencies remain strictly `typer>=0.12.0`, `rich>=13.0.0`, and `pyyaml>=6.0.0`.
   - Textual is declared exclusively under `[project.optional-dependencies] tui = ["textual>=8.2.8"]` and the development extra `dev`.
   - `uv.lock` resolves Textual at `8.2.8` while preserving Rich at `15.0.0` and all other dependency pins.
   - The base dependency closure completely excludes Textual.

2. **Strict CLI Routing & Terminal Sensing:**
   - Typer is configured with `no_args_is_help=False` and root callback `invoke_without_command=True`.
   - Explicit subcommands (`scan`, `why`, `agents`, `diff`, `doctor`, `compare`, `tui`) bypass bare logic immediately (`ctx.invoked_subcommand is not None`).
   - Root `--plain` forces help fallback (exit 0) on bare invocation and is ignored when subcommands are given (e.g. `skill-lens --plain tui` still explicitly launches).
   - Dynamic terminal sensing checks `sys.stdin` and `sys.stdout` at call time. Bare invocation only attempts automatic UI launch when **both** stdin and stdout are interactive TTYs, `--plain` is false, and Textual is installed.
   - All other 14 bare fallback combinations print root help (exit 0) without the install tip.
   - An install tip on stdout is emitted solely when both streams are interactive TTYs, `--plain` is false, and Textual is absent.

3. **Explicit Subcommand Contract & Honest Fault Boundaries:**
   - `skill-lens tui` bypasses terminal isatty checks.
   - Sandbox and working directory options (`--sandbox`, `--cwd`) are validated before checking Textual availability: an escaped cwd raises a usage error (exit 2) even when Textual is absent.
   - If Textual is absent on explicit `tui`, an error hint naming `skill-lens-cli[tui]` is printed to stderr and the process exits with `ExitCode.USAGE` (2).
   - Only `find_spec("textual") is None` indicates Textual is missing; unexpected availability probe exceptions are caught, formatted with plain-English context (`"Error: Failed to check Textual availability: {exc}"`), and exit with `ExitCode.INTERNAL` (3).
   - In U1, the `skill_lens.tui` package does not yet exist. When Textual is present, loading or running the entry point catches exceptions at the CLI boundary, formats plain-English startup context (`"Error: Failed to start the terminal UI: {exc}"`), renders exception details literally (`markup=False, highlight=False`) so square brackets are preserved without Rich markup interference, suppresses stack traces, and exits with `ExitCode.INTERNAL` (3).
   - Lazy adapter boundary is strictly typed via `TuiRunner(Protocol)` and `cast(TuiRunner, runner)` with zero `type: ignore` comments. Production code contains zero test-only globals (`_tui_runner_override` completely removed).

4. **Installed Wheel Verification & Output Parity:**
   - Built wheel smoke tests verified isolated base installation (Textual truly absent, bare fallback exit 0 without tip, explicit `tui` exit 2 with hint) and `[tui]` installation outside the source checkout.
   - Existing snapshots and goldens remain completely unchanged (fixture hashes unchanged), and their full pinned-output suites pass under the installed `[tui]` extra without pinned regeneration.
   - CI packaging workflow `.github/workflows/ci.yml` is extended to gate base fallback behavior, assert installed-wheel provenance (`assert '/tmp/smoke-tui' in skill_lens.__file__`), and execute the 4 pinned-output test suites outside the source checkout.

5. **Empirical Measurement & Behavioral Mutation Evidence:**
   - Reused original P3 600+ skill synthetic benchmarks (Scenarios A and B) from `docs/p3_cost_probe.py` loaded by path against real `capture_session()`: complete capture executes in ~682–991 ms (tracing OFF), retaining ~1.24–2.16 MiB of partial file payload and containers, with simulated refresh peak memory measured at ~9.75–9.98 MiB when tracing starts before initial capture. Unattributed residual is derived honestly (total wall-clock minus hook timers) without arbitrary splits.
   - Behavioral mutation campaign in an outside disposable copy executed 17 distinct mutations covering all new routing branches, dependency declarations, CI steps, lockfile pins, command declarations, and output parity. All 17 mutants compiled cleanly before execution and were killed strictly with pytest exit 1 matching the targeted assertion, with zero survivors. Full logs are persisted under `docs/validation/u1/logs/`.

---

## 2. Delivered Files & Responsibilities

| File | Changes & Responsibilities |
| --- | --- |
| `pyproject.toml` | Added `tui = ["textual>=8.2.8"]` to `[project.optional-dependencies]`; added `textual>=8.2.8` to `dev` extra; base runtime dependencies unchanged. |
| `uv.lock` | Synchronized lockfile recording Textual 8.2.8 and transitive dependencies (`mdit-py-plugins`, `platformdirs`, `linkify-it-py`); Rich remains 15.0.0. |
| `skill_lens/cli.py` | Configured `no_args_is_help=False`, `invoke_without_command=True`, root `--plain` option, call-time stream interactivity checks, Textual availability detector, typed lazy adapter boundary with literal bracket rendering and traceback suppression, and explicit `tui` command with sandbox/cwd validation. |
| `.github/workflows/ci.yml` | Restored baseline matrix and actions from `bc7d04c`; extended `packaging` job with outside-checkout base fallback assertions (Textual absent, noninteractive bare help exit 0 without tip, explicit `tui` exit 2 with hint), installed wheel provenance check, and outside-checkout pinned-output suite execution. |
| `tests/test_tui_routing.py` | Comprehensive unit test suite (36 tests) covering the complete 16-combination stream/plain/extra matrix, command bypass, explicit `tui`, sandbox validation, exit codes 0/2/3, lazy loader contracts, bad callables, unrelated dependency faults, availability errors, literal bracket details, and probe bypass. |
| `tests/test_tui_packaging.py` | Packaging gate suite (6 tests) covering base dependency isolation, extra floors, lockfile metadata, CI packaging steps, `tui` registration, and focused in-process output parity with strict sandbox restoration. |
| `tests/test_phase5_gate.py` | Updated expected CLI command set to include `tui`. |
| `docs/validation/u1/benchmark_capture.py` | Reproducible benchmark harness measuring real `capture_session()` across P3 Scenario A and B fixtures loaded by path from `docs/p3_cost_probe.py`, comparing exact values from `docs/P3_COST_PROBE_RESULTS.md`. |
| `docs/validation/u1/benchmark_raw.json` | Machine-readable raw benchmark runs, timings, and environmental conditions. |
| `docs/validation/u1/BENCHMARK_RESULTS.md` | Measured benchmark results, timings, memory tracking, derived residual, and exact P3 probe comparison. |
| `docs/validation/u1/smoke_wheel.py` | Reproducible local wheel smoke harness validating lean base and `[tui]` installation lanes outside the source checkout with synthetic HOME, clean PYTHONPATH, and archive inspection of 10 registry TOMLs. |
| `docs/validation/u1/smoke_records.json` | Machine-readable smoke test receipt recording provenance, commands, registry files, and statuses. |
| `docs/validation/u1/SMOKE_RESULTS.md` | Verified receipts for isolated built wheel installation. |
| `docs/validation/u1/run_mutations.py` | Disposable-copy mutation test runner executing 17 targeted mutations with pre-execution compilation, source restoration, targeted assertions, and full log persistence. |
| `docs/validation/u1/mutation_records.json` | Machine-readable mutation receipts with full log paths and targeted assertions. |
| `docs/validation/u1/MUTATION_RESULTS.md` | Mutation receipts showing clean control, assertion failure, source restoration, full logs, and no survivors. |
| `docs/validation/u1/logs/` | Persisted full stdout/stderr output logs for control, mutant, and restoration runs for all 17 mutations. |
| `docs/TUI_U1_WALKTHROUGH.md` | This document: comprehensive audit walkthrough of Assignment U1. |

---

## 3. Implementation Contracts & Behaviors

### 3.1 Bare Invocation Decision Tree

```text
Bare Invocation (ctx.invoked_subcommand is None):
  │
  ├─> plain is True OR not (stdin.isatty() AND stdout.isatty())
  │     └─> typer.echo(help)
  │     └─> exit 0 (NO TIP)
  │
  └─> Both streams are TTYs AND plain is False:
        │
        ├─> _is_textual_available():
        │     ├─> Unexpected probe error -> print plain English error -> exit 3
        │     └─> Textual absent (find_spec is None):
        │           └─> typer.echo(help)
        │           └─> typer.echo("\nTip: Install the terminal UI with: pip install 'skill-lens-cli[tui]'")
        │           └─> exit 0 (WITH TIP)
        │
        └─> Textual is Present:
              └─> resolve _effective_home(), _effective_cwd(None, None)
              └─> _launch_tui(home, cwd)
```

### 3.2 Explicit `tui` Subcommand Decision Tree

```text
Explicit Invocation (skill-lens tui [--sandbox DIR] [--cwd DIR]):
  │
  ├─> 1. Resolve effective home and cwd
  ├─> 2. Validate sandbox containment:
  │        └─> cwd outside sandbox -> error_console.print(...) -> exit 2
  ├─> 3. Check Textual availability:
  │        ├─> Unexpected probe error -> print plain English error -> exit 3
  │        └─> Textual absent -> error_console.print("Error: The terminal UI requires 'textual'. Install it with: pip install 'skill-lens-cli[tui]'") -> exit 2
  └─> 4. Textual present:
           └─> _launch_tui(home, cwd)
```

---

## 4. Verification & Validation Evidence

### 4.1 Local Wheel Smoke Verification

Executed via [docs/validation/u1/smoke_wheel.py](validation/u1/smoke_wheel.py):
- Built wheel archive inspected: exactly 10 agent registry TOML files packaged.
- Lean base wheel install in temporary virtualenv:
  - Provenance: imported from isolated virtualenv site-packages (`/tmp/.../venv/lib/...`).
  - Textual absence: confirmed (`find_spec('textual') is None`).
  - Bare noninteractive invocation: exits 0, help text emitted, install tip omitted.
  - Explicit `tui` invocation: exits 2, install hint emitted to stderr naming `skill-lens-cli[tui]`, traceback suppressed.
- `[tui]` wheel install in temporary virtualenv:
  - Provenance: imported from isolated virtualenv site-packages (`/tmp/.../venv/lib/...`).
  - Textual 8.2.8 is successfully imported.
  - Pinned-output suites executed from an isolated test lane outside the source checkout:
    - `tests/test_render_snapshots.py` (all 17 snapshots)
    - `tests/test_fixtures.py` (all 13 scenario goldens)
    - `tests/test_phase3_gate.py` (diff golden)
    - `tests/test_phase4_gate.py` (doctor and compare goldens)
    - All 128 tests passed (exit code 0).
- Detailed receipts saved at [docs/validation/u1/SMOKE_RESULTS.md](validation/u1/SMOKE_RESULTS.md).

### 4.2 Installed Extra Output Parity

- Verified via `tests/test_tui_packaging.py::test_installed_extra_output_parity` and the installed-wheel parity suite:
  - Existing snapshots and goldens remain completely unchanged (fixture file hashes unchanged).
  - All 17 plain-text Rich render snapshots in `tests/fixtures/snapshots/` and all 16 JSON golden files in `tests/fixtures/golden/` pass their full pinned-output test suites under the installed `[tui]` extra.
  - Zero snapshot or golden files were regenerated.

### 4.3 Real capture_session Benchmark

Captured via [docs/validation/u1/benchmark_capture.py](validation/u1/benchmark_capture.py) on Darwin arm64:
- Reuses original fixture constructors from `docs/p3_cost_probe.py` loaded by path.
- Exact original P3 probe measurements from [docs/P3_COST_PROBE_RESULTS.md](P3_COST_PROBE_RESULTS.md) are referenced as baseline.
- Unattributed residual is derived honestly (total wall-clock minus hook timers) and reported without arbitrary splits.
- Restores global sandbox in a `finally` block.
- Detailed report saved at [docs/validation/u1/BENCHMARK_RESULTS.md](validation/u1/BENCHMARK_RESULTS.md) and [docs/validation/u1/benchmark_raw.json](validation/u1/benchmark_raw.json).

### 4.4 Behavioral Mutation Campaign

Executed via [docs/validation/u1/run_mutations.py](validation/u1/run_mutations.py) inside isolated disposable copies outside the checkout:
- 17 distinct mutations tested across all guard categories:
  - `MUT-01` (terminal conjunction): KILLED
  - `MUT-02` (plain override): KILLED
  - `MUT-03` (missing-extra status/hint): KILLED
  - `MUT-04` (command bypass): KILLED
  - `MUT-05` (specific import-fault handling): KILLED
  - `MUT-06` (sandbox containment): KILLED
  - `MUT-07` (launch return propagation): KILLED
  - `MUT-08A` (base runtime dependency isolation): KILLED
  - `MUT-08B` (optional [tui] extra floor): KILLED
  - `MUT-08C` (dev extra floor): KILLED
  - `MUT-08D` (lockfile textual pin): KILLED
  - `MUT-08E` (lockfile rich pin): KILLED
  - `MUT-08F` (tui command registration): KILLED
  - `MUT-09A` (base CI exit code guard): KILLED
  - `MUT-09B` (CI [tui] lane provenance guard): KILLED
  - `MUT-10` (tip forced into noninteractive/plain fallback): KILLED
  - `MUT-11` (installed-extra output parity): KILLED
- Zero survivors observed. Full control, mutant, and restoration logs persisted to `docs/validation/u1/logs/`. Detailed receipts saved at [docs/validation/u1/MUTATION_RESULTS.md](validation/u1/MUTATION_RESULTS.md) and [docs/validation/u1/mutation_records.json](validation/u1/mutation_records.json).

---

## 5. Quality Gate Receipts

All four repository gates execute cleanly:

1. **Test Suite & Coverage:**
   ```bash
   uv run pytest --cov=skill_lens --cov-report=term-missing
   ```
   **Receipt:** 605 passed, 1 skipped (case-insensitive filesystem test), **94.67%** branch coverage (exceeds 90% floor).

2. **Strict Type Checking:**
   ```bash
   uv run mypy
   ```
   **Receipt:** Success: no issues found in 31 source files (strict mode).

3. **Linter:**
   ```bash
   uv run ruff check .
   ```
   **Receipt:** All checks passed!

4. **Code Formatter:**
   ```bash
   uv run ruff format --check .
   ```
   **Receipt:** All files formatted cleanly.
