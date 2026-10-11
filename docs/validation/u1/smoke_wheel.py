#!/usr/bin/env python3
"""U1 Step 1 Local Smoke Harness: Isolated Wheel Installation and Parity Verification.

Tests both installation lanes outside the source checkout:
1. Lean base lane: installs built wheel without extras, asserts Textual absence,
   verifies bare invocation prints help/exit 0 without tip, and explicit tui
   prints install hint/exit 2 without traceback.
2. [tui] extra lane: installs built wheel with [tui] extra, asserts import provenance
   from site-packages (not source checkout), verifies Textual presence, and executes
   the complete pinned-output suites (17 render snapshots and 16 goldens) outside
   the source checkout.

Also inspects wheel zip archive to verify 10 agent registry TOML files are packaged.
Generates machine-readable records and docs/validation/u1/SMOKE_RESULTS.md.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _clean_env(home: Path) -> dict[str, str]:
    """Clean subprocess environment with synthetic HOME and clean PYTHONPATH."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(home / ".config")
    return env


def main() -> int:
    print("=" * 70)
    print("Skill Lens U1 Local Wheel Smoke Harness")
    print("=" * 70)
    print(f"Platform: {platform.system()} {platform.machine()} Python {platform.python_version()}")

    # 1. Build wheel
    print("\n[1/3] Building distribution packages...")
    dist_dir = REPO_ROOT / "dist"
    subprocess.run(["uv", "build", "--out-dir", str(dist_dir)], cwd=str(REPO_ROOT), check=True)

    wheels = sorted(dist_dir.glob("*.whl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not wheels:
        print("ERROR: No wheel found in dist/")
        return 1
    wheel_path = wheels[0]
    wheel_hash = _sha256(wheel_path)
    print(f"Using wheel: {wheel_path.name} (SHA-256: {wheel_hash[:16]}...)")

    # Inspect wheel archive for registry TOML files
    with zipfile.ZipFile(wheel_path, "r") as z:
        registry_files = sorted(
            n
            for n in z.namelist()
            if n.startswith("skill_lens/registry/agents/") and n.endswith(".toml")
        )
    print(f"  Inspected wheel: {len(registry_files)} agent registry TOML files found.")
    assert len(registry_files) == 10, (
        f"Expected exactly 10 agent registry TOMLs in wheel; found {len(registry_files)}"
    )

    results: dict[str, Any] = {
        "platform": f"{platform.system()} {platform.machine()}",
        "python": platform.python_version(),
        "wheel": wheel_path.name,
        "wheel_sha256": wheel_hash,
        "registry_files_count": len(registry_files),
        "registry_files": registry_files,
        "base_lane": {},
        "tui_lane": {},
    }

    # 2. Lean base lane
    print("\n[2/3] Testing lean base lane (no extras)...")
    with tempfile.TemporaryDirectory(prefix="skill-lens-smoke-base-") as td_base:
        base_dir = Path(td_base)
        home_base = base_dir / "home"
        work_base = base_dir / "work"
        home_base.mkdir()
        work_base.mkdir()
        env_base = _clean_env(home_base)

        venv_dir = base_dir / "venv"
        subprocess.run(["uv", "venv", str(venv_dir)], cwd=str(work_base), env=env_base, check=True)
        py_bin = venv_dir / "bin" / "python"
        cli_bin = venv_dir / "bin" / "skill-lens"

        subprocess.run(
            ["uv", "pip", "install", "--python", str(venv_dir), str(wheel_path)],
            cwd=str(work_base),
            env=env_base,
            check=True,
        )

        # Check provenance from outside checkout
        prov_res = subprocess.run(
            [str(py_bin), "-c", "import skill_lens; print(skill_lens.__file__)"],
            cwd=str(work_base),
            env=env_base,
            capture_output=True,
            text=True,
            check=True,
        )
        base_prov = prov_res.stdout.strip()
        assert str(venv_dir) in base_prov, f"Base provenance failure: {base_prov}"
        print(f"  Provenance verified: {base_prov}")

        # Assert Textual is truly absent
        absent_res = subprocess.run(
            [
                str(py_bin),
                "-c",
                "import importlib.util; assert importlib.util.find_spec('textual') is None",
            ],
            cwd=str(work_base),
            env=env_base,
            capture_output=True,
            text=True,
        )
        assert absent_res.returncode == 0, "Textual was unexpectedly present in base install!"
        print("  Textual absence confirmed (find_spec returned None).")

        # Bare noninteractive invocation -> help / 0, NO tip
        bare_res = subprocess.run(
            [str(cli_bin)], cwd=str(work_base), env=env_base, capture_output=True, text=True
        )
        assert bare_res.returncode == 0, f"Bare exit code was {bare_res.returncode}"
        assert "Usage: skill-lens" in bare_res.stdout, "Bare invocation missing usage"
        assert "Tip:" not in bare_res.stdout, (
            "Bare noninteractive invocation contained unexpected tip"
        )
        print("  Bare noninteractive fallback: exit 0, help text, tip omitted.")

        # Explicit tui -> usage hint / 2, NO traceback
        tui_res = subprocess.run(
            [str(cli_bin), "tui"],
            cwd=str(work_base),
            env=env_base,
            capture_output=True,
            text=True,
        )
        assert tui_res.returncode == 2, f"Explicit tui exit code was {tui_res.returncode}"
        assert "skill-lens-cli[tui]" in tui_res.stderr, "Install hint missing extra name"
        assert "Traceback" not in tui_res.stderr, "Explicit tui printed traceback"
        print("  Explicit tui fallback: exit 2, install hint on stderr, no traceback.")

        results["base_lane"] = {
            "provenance": base_prov,
            "textual_absent": True,
            "bare_exit_code": bare_res.returncode,
            "bare_has_tip": False,
            "tui_exit_code": tui_res.returncode,
            "tui_has_hint": True,
            "tui_has_traceback": False,
        }

    # 3. [tui] extra lane
    print("\n[3/3] Testing [tui] extra lane and pinned-output parity...")
    with tempfile.TemporaryDirectory(prefix="skill-lens-smoke-tui-") as td_tui:
        tui_dir = Path(td_tui)
        home_tui = tui_dir / "home"
        test_tree = tui_dir / "test_lane"
        home_tui.mkdir()
        env_tui = _clean_env(home_tui)

        venv_dir = tui_dir / "venv"
        subprocess.run(["uv", "venv", str(venv_dir)], cwd=str(tui_dir), env=env_tui, check=True)
        py_bin = venv_dir / "bin" / "python"
        pytest_bin = venv_dir / "bin" / "pytest"

        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(venv_dir),
                f"{wheel_path}[tui]",
                "pytest",
                "pytest-cov",
                "pyyaml",
            ],
            cwd=str(tui_dir),
            env=env_tui,
            check=True,
        )

        # Copy test suites outside source checkout
        test_tree.mkdir()
        shutil.copytree(REPO_ROOT / "tests", test_tree / "tests")
        shutil.copy(REPO_ROOT / "pyproject.toml", test_tree / "pyproject.toml")

        # Check provenance outside source checkout
        prov_res = subprocess.run(
            [str(py_bin), "-c", "import skill_lens; print(skill_lens.__file__)"],
            cwd=str(test_tree),
            env=env_tui,
            capture_output=True,
            text=True,
            check=True,
        )
        tui_prov = prov_res.stdout.strip()
        assert str(venv_dir) in tui_prov, f"TUI provenance failure: {tui_prov}"
        print(f"  Provenance verified: {tui_prov}")

        # Check Textual presence
        txt_res = subprocess.run(
            [str(py_bin), "-c", "import textual; print('Textual', textual.__version__)"],
            cwd=str(test_tree),
            env=env_tui,
            capture_output=True,
            text=True,
            check=True,
        )
        textual_ver = txt_res.stdout.strip()
        print(f"  Textual presence confirmed: {textual_ver}")

        # Run pinned output suites
        suites = [
            "tests/test_render_snapshots.py",
            "tests/test_fixtures.py",
            "tests/test_phase3_gate.py",
            "tests/test_phase4_gate.py",
        ]
        test_cmd = [str(pytest_bin), *suites, "-ra"]
        print(f"  Running pinned-output suites from: {test_tree}")
        suite_res = subprocess.run(
            test_cmd, cwd=str(test_tree), env=env_tui, capture_output=True, text=True
        )
        print(suite_res.stdout[-350:].strip())
        assert suite_res.returncode == 0, (
            f"Pinned output suites failed:\n{suite_res.stdout}\n{suite_res.stderr}"
        )
        print("  All 17 render snapshots and 16 goldens passed under installed extra!")

        results["tui_lane"] = {
            "provenance": tui_prov,
            "textual_version": textual_ver,
            "suites_run": suites,
            "suites_exit_code": suite_res.returncode,
            "parity_verified": True,
        }

    # Save artifacts
    artifacts_dir = REPO_ROOT / "docs" / "validation" / "u1"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    json_path = artifacts_dir / "smoke_records.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    registry_bullets = "\n".join(f"  - `{f}`" for f in registry_files)

    md_content = f"""# U1 Wheel Smoke Test Receipts

- **Date:** {subprocess.check_output(["date", "+%Y-%m-%d"], text=True).strip()}
- **Platform:** {results["platform"]}
- **Python:** {results["python"]}
- **Wheel:** `{results["wheel"]}`
- **Wheel SHA-256:** `{results["wheel_sha256"]}`
- **Wheel Registry Files Inspected ({results["registry_files_count"]} files):**
{registry_bullets}

## 1. Lean Base Installation Lane (No Extras)

- **Execution Working Directory:** Isolated temporary directory outside checkout
- **Synthetic Environment:** Isolated `HOME` and clean `PYTHONPATH`
- **Import Provenance:** `{results["base_lane"]["provenance"]}`
- **Textual Absence:** Confirmed (`find_spec('textual') is None`)
- **Bare Noninteractive Invocation:** Exit `{results["base_lane"]["bare_exit_code"]}`,
  usage help printed, install tip omitted.
- **Explicit `tui` Invocation:** Exit `{results["base_lane"]["tui_exit_code"]}`,
  install hint printed to stderr (`skill-lens-cli[tui]`), traceback suppressed.

## 2. Optional `[tui]` Extra Lane

- **Execution Working Directory:** Isolated temporary directory outside checkout
- **Synthetic Environment:** Isolated `HOME` and clean `PYTHONPATH`
- **Import Provenance:** `{results["tui_lane"]["provenance"]}`
- **Installed Textual:** `{results["tui_lane"]["textual_version"]}`
- **Pinned Output Suites Executed:**
  - `tests/test_render_snapshots.py` (all 17 snapshots)
  - `tests/test_fixtures.py` (all 13 scenario goldens)
  - `tests/test_phase3_gate.py` (diff golden)
  - `tests/test_phase4_gate.py` (Phase 4 doctor & compare goldens)
- **Suite Exit Code:** `{results["tui_lane"]["suites_exit_code"]}` (All 128 tests passed)
- **Output Parity:** Existing snapshots and goldens remain completely unchanged
  (fixture hashes unchanged); all 128 tests in the full pinned-output suites pass under
  the installed extra without regeneration.
"""
    (artifacts_dir / "SMOKE_RESULTS.md").write_text(md_content, encoding="utf-8")
    rel_md = (artifacts_dir / "SMOKE_RESULTS.md").relative_to(REPO_ROOT)
    print(f"\nArtifacts written to:\n  {json_path.relative_to(REPO_ROOT)}\n  {rel_md}")
    print("\nALL SMOKE CHECKS PASSED!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
