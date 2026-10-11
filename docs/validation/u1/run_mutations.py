#!/usr/bin/env python3
"""U1 Step 1 Mutation Campaign: Behavioral mutation testing of launch/dependency/CI guards.

Executes each mutation in an isolated disposable copy outside the repository.
Enforces:
- Syntax validation (compiles Python mutants before test execution)
- Import provenance: skill_lens and tests run from the disposable copy
- Clean control pass (exit 0)
- Mutant failure strictly with pytest exit 1, no collection errors, and targeted assertion
- Source restoration in finally block and verified clean restoration rerun (exit 0)
- Machine-readable receipt records, full logs persisted to docs/validation/u1/logs/,
  and zero surviving mutations.

Generates:
- docs/validation/u1/mutation_records.json
- docs/validation/u1/MUTATION_RESULTS.md
- docs/validation/u1/logs/ (control, mutant, and restoration logs for all 17 mutations)
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass
class MutationDef:
    mutation_id: str
    name: str
    target_file: str
    selector: str
    original_snippet: str
    mutated_snippet: str
    expected_assertion_snippet: str
    description: str


MUTATIONS = [
    MutationDef(
        mutation_id="MUT-01",
        name="terminal conjunction",
        target_file="skill_lens/cli.py",
        selector="tests/test_tui_routing.py::test_bare_invocation_stream_matrix",
        original_snippet=(
            "is_interactive = _stream_isatty(sys.stdin) and _stream_isatty(sys.stdout)"
        ),
        mutated_snippet="is_interactive = _stream_isatty(sys.stdin) or _stream_isatty(sys.stdout)",
        expected_assertion_snippet="assert len(called_with) == 0",
        description="Relax conjunction to disjunction (either stream triggers interactive launch).",
    ),
    MutationDef(
        mutation_id="MUT-02",
        name="plain override",
        target_file="skill_lens/cli.py",
        selector="tests/test_tui_routing.py::test_bare_invocation_stream_matrix",
        original_snippet="if plain or not is_interactive:",
        mutated_snippet="if not is_interactive:",
        expected_assertion_snippet="assert len(called_with) == 0",
        description="Ignore the --plain flag on bare invocation.",
    ),
    MutationDef(
        mutation_id="MUT-03",
        name="missing-extra statuses/tip",
        target_file="skill_lens/cli.py",
        selector="tests/test_tui_routing.py::test_explicit_tui_missing_textual_exits_2",
        original_snippet="raise typer.Exit(code=int(ExitCode.USAGE))",
        mutated_snippet="raise typer.Exit(code=int(ExitCode.OK))",
        expected_assertion_snippet="assert result.exit_code == int(ExitCode.USAGE)",
        description="Make explicit `skill-lens tui` exit 0 instead of 2 when Textual is missing.",
    ),
    MutationDef(
        mutation_id="MUT-04",
        name="command bypass",
        target_file="skill_lens/cli.py",
        selector="tests/test_tui_routing.py::test_plain_subcommand_bypass",
        original_snippet="    if ctx.invoked_subcommand is not None:\n        return",
        mutated_snippet="    if ctx.invoked_subcommand is not None:\n        pass",
        expected_assertion_snippet="assert '\"skills\":' in result.stdout",
        description="Remove early return when explicit subcommand is invoked.",
    ),
    MutationDef(
        mutation_id="MUT-05",
        name="specific import-fault handling",
        target_file="skill_lens/cli.py",
        selector="tests/test_tui_routing.py::test_tui_runner_unexpected_exception_exits_3_no_traceback",
        original_snippet="""    except Exception as exc:
        error_console.print(
            f"Error: Failed to start the terminal UI: {exc}",
            soft_wrap=True,
            markup=False,
            highlight=False,
        )
        raise typer.Exit(code=int(ExitCode.INTERNAL)) from None""",
        mutated_snippet="""    except Exception as exc:
        error_console.print(
            f"Error: Failed to start the terminal UI: {exc}",
            soft_wrap=True,
            markup=False,
            highlight=False,
        )
        raise typer.Exit(code=int(ExitCode.USAGE)) from None""",
        expected_assertion_snippet="assert result.exit_code == int(ExitCode.INTERNAL)",
        description="Mislabel internal launch exceptions as usage errors (code 2 instead of 3).",
    ),
    MutationDef(
        mutation_id="MUT-06",
        name="sandbox containment",
        target_file="skill_lens/cli.py",
        selector="tests/test_tui_routing.py::test_explicit_tui_escaped_cwd_rejected_before_availability_check",
        original_snippet=(
            "    if sandbox is not None:\n        _assert_inside_sandbox(working_dir, home)"
        ),
        mutated_snippet="    if sandbox is not None:\n        pass",
        expected_assertion_snippet="--cwd must stay inside --sandbox",
        description="Disable _assert_inside_sandbox in explicit tui command.",
    ),
    MutationDef(
        mutation_id="MUT-07",
        name="launch return propagation",
        target_file="skill_lens/cli.py",
        selector="tests/test_tui_routing.py::test_tui_runner_exit_code_3_propagates",
        original_snippet=(
            "    if code != int(ExitCode.OK):\n        raise typer.Exit(code=int(code))"
        ),
        mutated_snippet="    if code != int(ExitCode.OK):\n        raise typer.Exit(code=0)",
        expected_assertion_snippet="assert result.exit_code == int(ExitCode.INTERNAL)",
        description="Swallow runner failure return codes and exit 0 unconditionally.",
    ),
    MutationDef(
        mutation_id="MUT-08A",
        name="base runtime dependency isolation",
        target_file="pyproject.toml",
        selector="tests/test_tui_packaging.py::test_base_runtime_dependencies_exclude_textual",
        original_snippet=(
            'dependencies = [\n    "typer>=0.12.0",\n    "rich>=13.0.0",\n    "pyyaml>=6.0.0",\n]'
        ),
        mutated_snippet=(
            "dependencies = [\n"
            '    "typer>=0.12.0",\n'
            '    "rich>=13.0.0",\n'
            '    "pyyaml>=6.0.0",\n'
            '    "textual>=8.2.8",\n'
            "]"
        ),
        expected_assertion_snippet="base dependencies must not include Textual",
        description="Leak textual into base runtime dependencies in pyproject.toml.",
    ),
    MutationDef(
        mutation_id="MUT-08B",
        name="optional [tui] extra floor",
        target_file="pyproject.toml",
        selector="tests/test_tui_packaging.py::test_optional_dependencies_declare_textual_floor",
        original_snippet='tui = [\n    "textual>=8.2.8",\n]',
        mutated_snippet='tui = [\n    "textual>=0.80.0",\n]',
        expected_assertion_snippet="[tui] extra must declare textual>=8.2.8",
        description="Lower the textual version floor in [project.optional-dependencies] tui.",
    ),
    MutationDef(
        mutation_id="MUT-08C",
        name="dev extra floor",
        target_file="pyproject.toml",
        selector="tests/test_tui_packaging.py::test_optional_dependencies_declare_textual_floor",
        original_snippet='    "textual>=8.2.8",\n]',
        mutated_snippet='    "textual>=0.80.0",\n]',
        expected_assertion_snippet="[dev] extra must declare textual>=8.2.8",
        description="Lower the textual version floor in the dev extra.",
    ),
    MutationDef(
        mutation_id="MUT-08D",
        name="lockfile textual pin",
        target_file="uv.lock",
        selector="tests/test_tui_packaging.py::test_uv_lock_pins_textual_and_rich",
        original_snippet='name = "textual"\nversion = "8.2.8"',
        mutated_snippet='name = "textual"\nversion = "0.80.0"',
        expected_assertion_snippet="textual must be pinned to 8.2.8",
        description="Corrupt the locked textual version in uv.lock.",
    ),
    MutationDef(
        mutation_id="MUT-08E",
        name="lockfile rich pin",
        target_file="uv.lock",
        selector="tests/test_tui_packaging.py::test_uv_lock_pins_textual_and_rich",
        original_snippet='name = "rich"\nversion = "15.0.0"',
        mutated_snippet='name = "rich"\nversion = "14.2.0"',
        expected_assertion_snippet="rich must be pinned to 15.0.0",
        description="Corrupt the locked rich version in uv.lock.",
    ),
    MutationDef(
        mutation_id="MUT-08F",
        name="tui command registration",
        target_file="skill_lens/cli.py",
        selector="tests/test_tui_packaging.py::test_tui_command_is_registered",
        original_snippet="@app.command()\ndef tui(",
        mutated_snippet="@app.command()\ndef tui_disabled(",
        expected_assertion_snippet="must be a registered CLI command",
        description="Rename or unregister the tui command in cli.py.",
    ),
    MutationDef(
        mutation_id="MUT-09A",
        name="base CI exit code guard",
        target_file=".github/workflows/ci.yml",
        selector="tests/test_tui_packaging.py::test_ci_packaging_job_has_base_and_tui_lanes",
        original_snippet='test "$code" -eq 2',
        mutated_snippet='test "$code" -eq 0',
        expected_assertion_snippet="CI packaging job must assert explicit tui exit code 2",
        description="Corrupt the base CI exit code assertion in ci.yml.",
    ),
    MutationDef(
        mutation_id="MUT-09B",
        name="CI [tui] lane provenance guard",
        target_file=".github/workflows/ci.yml",
        selector="tests/test_tui_packaging.py::test_ci_packaging_job_has_base_and_tui_lanes",
        original_snippet="assert '/tmp/smoke-tui' in skill_lens.__file__",
        mutated_snippet="# provenance check removed",
        expected_assertion_snippet=(
            "CI packaging job must assert skill_lens.__file__ is inside installed lane"
        ),
        description="Remove the installed-lane provenance assertion from CI ci.yml.",
    ),
    MutationDef(
        mutation_id="MUT-10",
        name="tip forced into noninteractive/plain fallback",
        target_file="skill_lens/cli.py",
        selector="tests/test_tui_routing.py::test_bare_invocation_stream_matrix",
        original_snippet=(
            "    if plain or not is_interactive:\n"
            "        typer.echo(ctx.get_help())\n"
            "        raise typer.Exit(code=int(ExitCode.OK))"
        ),
        mutated_snippet=(
            "    if plain or not is_interactive:\n"
            "        typer.echo(ctx.get_help())\n"
            "        typer.echo("
            "\"\\nTip: Install the terminal UI with: pip install 'skill-lens-cli[tui]'\")\n"
            "        raise typer.Exit(code=int(ExitCode.OK))"
        ),
        expected_assertion_snippet='assert "Tip:" not in result.stdout',
        description="Force the install tip into noninteractive and plain fallback paths.",
    ),
    MutationDef(
        mutation_id="MUT-11",
        name="installed-extra output parity",
        target_file="skill_lens/render.py",
        selector="tests/test_tui_packaging.py::test_installed_extra_output_parity",
        original_snippet='title="Skill Lens: Discovered Skills"',
        mutated_snippet='title="Skill Lens: Mutated Render Title"',
        expected_assertion_snippet="snapshot scan_variant_hash_detection.txt changed",
        description="Alter CLI render output to verify the installed-extra parity gate fails.",
    ),
]


def run_disposable_pytest(disp_root: Path, temp_home: Path, selector: str) -> tuple[int, str]:
    """Execute pytest inside the disposable copy with isolated HOME and PYTHONPATH."""
    py_bin = REPO_ROOT / ".venv" / "bin" / "python"
    env = {
        **os.environ,
        "PYTHONPATH": str(disp_root),
        "HOME": str(temp_home),
        "XDG_CONFIG_HOME": str(temp_home / ".config"),
    }
    res = subprocess.run(
        [str(py_bin), "-m", "pytest", "-ra", selector],
        cwd=str(disp_root),
        env=env,
        capture_output=True,
        text=True,
    )
    return res.returncode, res.stdout + res.stderr


def main() -> int:
    print("=" * 70)
    print("Skill Lens U1 Step 1 Behavioral Mutation Campaign")
    print("=" * 70)
    print(f"Platform: {platform.system()} {platform.machine()} Python {platform.python_version()}")

    artifacts_dir = REPO_ROOT / "docs" / "validation" / "u1"
    logs_dir = artifacts_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="skill-lens-u1-mutation-") as td:
        disp_root = Path(td) / "repo"
        temp_home = Path(td) / "home"
        temp_home.mkdir()

        print(f"\n[Setup] Creating outside disposable copy at: {disp_root}")
        shutil.copytree(
            REPO_ROOT,
            disp_root,
            ignore=shutil.ignore_patterns(".venv", ".git", "dist", "*.pyc", "__pycache__"),
            symlinks=True,
        )

        # Verify import provenance in disposable tree
        prov_check = subprocess.run(
            [
                str(REPO_ROOT / ".venv" / "bin" / "python"),
                "-c",
                "import skill_lens; print(skill_lens.__file__)",
            ],
            cwd=str(disp_root),
            env={**os.environ, "PYTHONPATH": str(disp_root), "HOME": str(temp_home)},
            capture_output=True,
            text=True,
            check=True,
        )
        prov_path = prov_check.stdout.strip()
        assert str(disp_root) in prov_path, (
            f"Provenance check failed: {prov_path} not in {disp_root}"
        )
        print(f"  Disposable provenance confirmed: {prov_path}")

        for m in MUTATIONS:
            print(f"\n[{m.mutation_id}] {m.name}...")
            target_path = disp_root / m.target_file
            original_content = target_path.read_text(encoding="utf-8")

            if m.original_snippet not in original_content:
                raise RuntimeError(
                    f"Could not find original snippet for {m.mutation_id} in {m.target_file}!"
                )

            # 1. Clean control run
            ctrl_code, ctrl_out = run_disposable_pytest(disp_root, temp_home, m.selector)
            assert ctrl_code == 0, f"Control run failed for {m.mutation_id}:\n{ctrl_out}"
            print("  1. Control run: PASSED (exit 0)")

            # Persist control log
            ctrl_log_path = logs_dir / f"{m.mutation_id}_control.log"
            ctrl_log_path.write_text(ctrl_out, encoding="utf-8")

            # 2. Mutate and compile check
            mutated_content = original_content.replace(m.original_snippet, m.mutated_snippet, 1)

            if target_path.suffix == ".py":
                try:
                    compile(mutated_content, str(target_path), "exec")
                except Exception as compile_err:
                    raise RuntimeError(
                        f"Mutation {m.mutation_id} generated invalid Python syntax:\n{compile_err}"
                    ) from compile_err

            target_path.write_text(mutated_content, encoding="utf-8")

            mut_code = -1
            mut_out = ""
            try:
                mut_code, mut_out = run_disposable_pytest(disp_root, temp_home, m.selector)
            finally:
                # 3. Always restore original source in finally block
                target_path.write_text(original_content, encoding="utf-8")

            # Persist mutant log
            mut_log_path = logs_dir / f"{m.mutation_id}_mutant.log"
            mut_log_path.write_text(mut_out, encoding="utf-8")

            # Verify mutant failure criteria:
            # - exit code MUST be 1 (test failure, not 2 collection error or 3 internal)
            assert mut_code == 1, (
                f"Mutant {m.mutation_id} failed with exit code {mut_code} (expected 1):\n{mut_out}"
            )
            assert "ERRORS" not in mut_out or "ERROR collecting" not in mut_out, (
                f"Mutant {m.mutation_id} produced collection error:\n{mut_out}"
            )
            assert "FAILED " in mut_out, f"Mutant {m.mutation_id} did not fail cleanly:\n{mut_out}"
            assert m.expected_assertion_snippet in mut_out, (
                f"Mutant {m.mutation_id} did not produce expected assertion "
                f"'{m.expected_assertion_snippet}':\n{mut_out}"
            )
            print("  2. Mutant run: KILLED (exit 1, targeted assertion matched)")

            # 4. Restoration run
            rest_code, rest_out = run_disposable_pytest(disp_root, temp_home, m.selector)
            assert rest_code == 0, f"Restoration run failed for {m.mutation_id}:\n{rest_out}"
            print("  3. Restoration run: PASSED (exit 0)")

            # Persist restoration log
            rest_log_path = logs_dir / f"{m.mutation_id}_restoration.log"
            rest_log_path.write_text(rest_out, encoding="utf-8")

            # Extract failure summary snippet
            fail_line = next(
                (
                    line
                    for line in mut_out.splitlines()
                    if m.expected_assertion_snippet in line
                    or "AssertionError" in line
                    or "FAILED " in line
                ),
                "FAILED",
            )

            results.append(
                {
                    "mutation_id": m.mutation_id,
                    "name": m.name,
                    "target_file": m.target_file,
                    "selector": m.selector,
                    "tests_module_path": m.selector.split("::")[0],
                    "description": m.description,
                    "status": "KILLED",
                    "import_provenance": prov_path,
                    "expected_assertion_snippet": m.expected_assertion_snippet,
                    "failure_evidence": fail_line.strip(),
                    "control_exit_code": ctrl_code,
                    "mutant_exit_code": mut_code,
                    "restoration_exit_code": rest_code,
                    "control_log": f"docs/validation/u1/logs/{m.mutation_id}_control.log",
                    "mutant_log": f"docs/validation/u1/logs/{m.mutation_id}_mutant.log",
                    "restoration_log": f"docs/validation/u1/logs/{m.mutation_id}_restoration.log",
                }
            )

    # Save artifacts
    json_path = artifacts_dir / "mutation_records.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    rows = "\n".join(
        f"| `{r['mutation_id']}` | {r['name']} | `{r['target_file']}` | "
        f"`{r['tests_module_path']}` | **{r['status']}** | `{r['expected_assertion_snippet']}` | "
        f"[`log`]({r['mutant_log'].replace('docs/validation/u1/', '')}) |"
        for r in results
    )

    md_content = f"""# U1 Behavioral Mutation Campaign Results

Conducted across 17 distinct mutations in an outside disposable copy
with strict import provenance, pre-execution compilation checks, and source restoration.
Full execution output logs are persisted in `docs/validation/u1/logs/`.

- **Platform:** {platform.system()} {platform.machine()} Python {platform.python_version()}
- **Date:** {time.strftime("%Y-%m-%d", time.gmtime())}
- **Total Mutations:** {len(results)}
- **Mutants Killed:** {len([r for r in results if r["status"] == "KILLED"])}
- **Survivors:** 0

| ID | Guard Category | Target File | Test Module | Outcome | Targeted Assertion | Log |
| --- | --- | --- | --- | :---: | --- | :---: |
{rows}

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
"""
    (artifacts_dir / "MUTATION_RESULTS.md").write_text(md_content, encoding="utf-8")
    print(
        f"\nArtifacts generated:\n"
        f"  {json_path.relative_to(REPO_ROOT)}\n"
        f"  {(artifacts_dir / 'MUTATION_RESULTS.md').relative_to(REPO_ROOT)}\n"
        f"  {logs_dir.relative_to(REPO_ROOT)}/ ({len(results) * 3} log files)"
    )
    print(f"\nALL {len(results)} MUTATIONS KILLED! ZERO SURVIVORS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
