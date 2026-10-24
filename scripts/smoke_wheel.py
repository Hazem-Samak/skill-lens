#!/usr/bin/env python3
"""Reusable stdlib packaging and installed-wheel smoke test runner (Stage G).

Verifies:
1. Wheel and sdist archive integrity:
   - All required TUI modules: __init__.py, app.py, session.py, _textual_compat.py
   - All 10 agent registry TOML files
   - py.typed typing marker
2. Base installation lane (lean fallback without [tui] extra):
   - Provenance strictly inside clean virtualenv
   - Textual confirmed absent (find_spec is None)
   - Bare non-interactive invocation: exit 0, help text, install tip omitted
   - Explicit 'tui' invocation: exit 2, hint mentions skill-lens-cli[tui], no traceback
3. Optional [tui] extra installation lanes:
   - Minimum endpoint: textual==8.2.8
   - Latest endpoint: unconstrained textual resolution (resolves current latest on PyPI)
   - Both lanes execute full pinned-output parity and installed TUI lifecycle/read-only suites
     outside the repository checkout without copying skill_lens source packages.
   - Exact installed package origins, versions, commands, test/skip counts, and endpoint overlap
     are recorded in machine-readable receipts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from typing import Any

REQUIRED_TUI_MODULES: tuple[str, ...] = (
    "skill_lens/tui/__init__.py",
    "skill_lens/tui/app.py",
    "skill_lens/tui/session.py",
    "skill_lens/tui/_textual_compat.py",
)

REQUIRED_REGISTRY_COUNT: int = 10
REQUIRED_TYPED_MARKER: str = "skill_lens/py.typed"

INSTALLED_TUI_TEST_SUITES: tuple[str, ...] = (
    "tests/test_render_snapshots.py",
    "tests/test_fixtures.py",
    "tests/test_phase3_gate.py",
    "tests/test_phase4_gate.py",
    "tests/test_tui_app.py",
    "tests/test_tui_session.py",
    "tests/test_tui_read_only.py",
    "tests/test_stage_g_repairs.py",
    "tests/test_tui_packaging.py",
)


def compute_sha256(path: pathlib.Path) -> str:
    """Compute sha256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_wheel_contents(wheel_path: pathlib.Path) -> dict[str, Any]:
    """Verify archive contents of a built wheel.

    Raises ValueError if any required module, registry file, or marker is missing.
    """
    wheel_path = pathlib.Path(wheel_path).resolve()
    if not wheel_path.exists():
        raise FileNotFoundError(f"Wheel does not exist: {wheel_path}")

    with zipfile.ZipFile(wheel_path, "r") as zf:
        namelist = set(zf.namelist())

    missing_tui = [m for m in REQUIRED_TUI_MODULES if m not in namelist]
    if missing_tui:
        raise ValueError(
            f"Wheel archive {wheel_path.name} is missing required TUI module(s): {missing_tui!r}"
        )

    registry_files = [
        n for n in namelist if n.startswith("skill_lens/registry/agents/") and n.endswith(".toml")
    ]
    if len(registry_files) != REQUIRED_REGISTRY_COUNT:
        raise ValueError(
            f"Wheel archive {wheel_path.name} contains {len(registry_files)} agent registry TOMLs; "
            f"expected exactly {REQUIRED_REGISTRY_COUNT}."
        )

    if REQUIRED_TYPED_MARKER not in namelist:
        raise ValueError(
            f"Wheel archive {wheel_path.name} is missing typing marker: {REQUIRED_TYPED_MARKER}"
        )

    return {
        "wheel": str(wheel_path.resolve()),
        "sha256": compute_sha256(wheel_path),
        "tui_modules": list(REQUIRED_TUI_MODULES),
        "registry_count": len(registry_files),
        "registry_files": sorted(registry_files),
        "typed_marker": True,
        "total_files": len(namelist),
    }


def verify_sdist_contents(sdist_path: pathlib.Path) -> dict[str, Any]:
    """Verify archive contents of a built sdist tarball.

    Raises ValueError if required root or package files are missing.
    """
    sdist_path = pathlib.Path(sdist_path).resolve()
    if not sdist_path.exists():
        raise FileNotFoundError(f"Sdist does not exist: {sdist_path}")

    with tarfile.open(sdist_path, "r:*") as tf:
        names = tf.getnames()

    # Sdist archives prefix entries with '<pkg>-<version>/'
    prefix = ""
    for name in names:
        if name.endswith("pyproject.toml"):
            prefix = name[: -len("pyproject.toml")]
            break

    missing: list[str] = []
    for required in ("pyproject.toml", "README.md", "LICENSE", REQUIRED_TYPED_MARKER):
        target = f"{prefix}{required}"
        if target not in names:
            missing.append(required)

    for mod in REQUIRED_TUI_MODULES:
        target = f"{prefix}{mod}"
        if target not in names:
            missing.append(mod)

    if missing:
        raise ValueError(
            f"Sdist archive {sdist_path.name} is missing required file(s): {missing!r}"
        )

    registry_files = [
        n for n in names if f"{prefix}skill_lens/registry/agents/" in n and n.endswith(".toml")
    ]
    if len(registry_files) != REQUIRED_REGISTRY_COUNT:
        raise ValueError(
            f"Sdist archive {sdist_path.name} contains {len(registry_files)} agent registry TOMLs; "
            f"expected exactly {REQUIRED_REGISTRY_COUNT}."
        )

    return {
        "sdist": str(sdist_path.resolve()),
        "sha256": compute_sha256(sdist_path),
        "prefix": prefix,
        "tui_modules": list(REQUIRED_TUI_MODULES),
        "registry_count": len(registry_files),
        "total_files": len(names),
    }


def _clean_env(home_dir: pathlib.Path) -> dict[str, str]:
    """Create a pristine environment dictionary outside user home and repo."""
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(home_dir),
        "XDG_CONFIG_HOME": str(home_dir / ".config"),
        "XDG_DATA_HOME": str(home_dir / ".local" / "share"),
        "PYTHONUNBUFFERED": "1",
        "PYTHONNOUSERSITE": "1",
    }
    # Explicitly clear any PYTHONPATH or source-shadowing variables
    for key in ("PYTHONPATH", "VIRTUAL_ENV", "PIP_REQUIRE_VIRTUALENV"):
        env.pop(key, None)
    return env


def verify_base_install(
    wheel_path: pathlib.Path,
    work_dir: pathlib.Path,
    python_bin: str = sys.executable,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    """Verify lean base installation behavior in an isolated virtualenv."""
    wheel_path = pathlib.Path(wheel_path).resolve()
    work_dir = pathlib.Path(work_dir).resolve()
    if not wheel_path.exists():
        raise FileNotFoundError(f"Wheel does not exist: {wheel_path}")

    lane_dir = work_dir / "base_lane"
    lane_dir.mkdir(parents=True, exist_ok=True)
    home_dir = lane_dir / "home"
    home_dir.mkdir(parents=True, exist_ok=True)
    env = _clean_env(home_dir)

    venv_dir = lane_dir / "venv"
    if venv_dir.exists():
        shutil.rmtree(venv_dir)
    if shutil.which("uv"):
        subprocess.run(
            ["uv", "venv", str(venv_dir), "--python", python_bin],
            cwd=str(lane_dir),
            env=env,
            check=True,
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["uv", "pip", "install", "--python", str(venv_dir), str(wheel_path)],
            cwd=str(lane_dir),
            env=env,
            check=True,
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
        )
    else:
        subprocess.run(
            [python_bin, "-m", "venv", str(venv_dir)],
            cwd=str(lane_dir),
            env=env,
            check=True,
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
        )
        pip_bin = venv_dir / "bin" / "pip"
        subprocess.run(
            [str(pip_bin), "install", str(wheel_path)],
            cwd=str(lane_dir),
            env=env,
            check=True,
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
        )

    py_exe = venv_dir / "bin" / "python"
    cli_exe = venv_dir / "bin" / "skill-lens"

    # 1. Assert provenance is inside the virtualenv
    prov_res = subprocess.run(
        [str(py_exe), "-c", "import skill_lens; print(skill_lens.__file__)"],
        cwd=str(lane_dir),
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    provenance = prov_res.stdout.strip()
    if str(venv_dir) not in provenance:
        raise AssertionError(f"Expected skill_lens inside venv {venv_dir}; got: {provenance}")

    # 2. Assert Textual is truly absent
    check_textual_cmd = (
        "import importlib.util; "
        "assert importlib.util.find_spec('textual') is None, 'Textual must be absent'"
    )
    subprocess.run(
        [str(py_exe), "-c", check_textual_cmd],
        cwd=str(lane_dir),
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )

    # 3. Assert --version and --help succeed
    v_res = subprocess.run(
        [str(cli_exe), "--version"],
        cwd=str(lane_dir),
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    subprocess.run(
        [str(cli_exe), "--help"],
        cwd=str(lane_dir),
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )

    # 4. Bare non-interactive invocation: exit 0, help text, tip omitted
    bare_res = subprocess.run(
        [str(cli_exe)],
        cwd=str(lane_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if bare_res.returncode != 0:
        raise AssertionError(
            f"Bare invocation returned exit code {bare_res.returncode}; expected 0"
        )
    if "Usage: skill-lens" not in bare_res.stdout:
        raise AssertionError(f"Bare invocation missing usage:\n{bare_res.stdout}")
    if "Tip:" in bare_res.stdout:
        raise AssertionError(
            f"Bare non-interactive invocation included unexpected tip:\n{bare_res.stdout}"
        )

    # 5. Explicit tui invocation: exit 2, hint mentions skill-lens-cli[tui], no traceback
    tui_res = subprocess.run(
        [str(cli_exe), "tui"],
        cwd=str(lane_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if tui_res.returncode != 2:
        raise AssertionError(f"Explicit tui returned exit code {tui_res.returncode}; expected 2")
    if "skill-lens-cli[tui]" not in tui_res.stderr:
        raise AssertionError(f"Explicit tui missing extra hint:\n{tui_res.stderr}")
    if "Traceback" in tui_res.stderr:
        raise AssertionError(f"Explicit tui printed unexpected traceback:\n{tui_res.stderr}")

    return {
        "status": "passed",
        "provenance": provenance,
        "textual_absent": True,
        "version_output": v_res.stdout.strip(),
        "bare_exit_code": bare_res.returncode,
        "bare_tip_omitted": True,
        "explicit_tui_exit_code": tui_res.returncode,
        "explicit_tui_hint_present": True,
        "explicit_tui_no_traceback": True,
    }


def verify_tui_endpoint_install(
    wheel_path: pathlib.Path,
    work_dir: pathlib.Path,
    endpoint_name: str,
    textual_spec: str | None = None,
    python_bin: str = sys.executable,
    repo_root: pathlib.Path | None = None,
    # The installed-lane suite runs 360 tests in a cold virtualenv. On the
    # 2-core runner it finishes in roughly two minutes; 300 s leaves headroom
    # while still failing a hang quickly. Partial output is preserved below.
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Verify [tui] installation, lifecycle, and parity in an isolated virtualenv."""
    wheel_path = pathlib.Path(wheel_path).resolve()
    work_dir = pathlib.Path(work_dir).resolve()
    if not wheel_path.exists():
        raise FileNotFoundError(f"Wheel does not exist: {wheel_path}")
    if repo_root is None:
        repo_root = pathlib.Path(__file__).resolve().parent.parent
    repo_root = pathlib.Path(repo_root).resolve()

    lane_dir = work_dir / f"{endpoint_name}_lane"
    lane_dir.mkdir(parents=True, exist_ok=True)
    home_dir = lane_dir / "home"
    home_dir.mkdir(parents=True, exist_ok=True)
    env = _clean_env(home_dir)

    venv_dir = lane_dir / "venv"
    if venv_dir.exists():
        shutil.rmtree(venv_dir)
    test_lane = lane_dir / "test_lane"
    if test_lane.exists():
        shutil.rmtree(test_lane)
    install_packages = [f"{wheel_path}[tui]"]
    if textual_spec:
        install_packages.append(textual_spec)
    install_packages.extend(["pytest", "pytest-cov", "pyyaml"])

    if shutil.which("uv"):
        subprocess.run(
            ["uv", "venv", str(venv_dir), "--python", python_bin],
            cwd=str(lane_dir),
            env=env,
            check=True,
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["uv", "pip", "install", "--python", str(venv_dir), *install_packages],
            cwd=str(lane_dir),
            env=env,
            check=True,
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
        )
        pkg_list_res = subprocess.run(
            ["uv", "pip", "list", "--python", str(venv_dir), "--format=json"],
            cwd=str(lane_dir),
            env=env,
            check=True,
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
        )
        installed_packages = json.loads(pkg_list_res.stdout)
    else:
        subprocess.run(
            [python_bin, "-m", "venv", str(venv_dir)],
            cwd=str(lane_dir),
            env=env,
            check=True,
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
        )
        pip_bin = venv_dir / "bin" / "pip"
        subprocess.run(
            [str(pip_bin), "install", *install_packages],
            cwd=str(lane_dir),
            env=env,
            check=True,
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
        )
        pkg_list_res = subprocess.run(
            [str(pip_bin), "list", "--format=json"],
            cwd=str(lane_dir),
            env=env,
            check=True,
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
        )
        installed_packages = json.loads(pkg_list_res.stdout)

    py_exe = venv_dir / "bin" / "python"
    cli_exe = venv_dir / "bin" / "skill-lens"
    pytest_exe = venv_dir / "bin" / "pytest"

    # 1. Assert provenance is inside virtualenv
    prov_res = subprocess.run(
        [
            str(py_exe),
            "-c",
            (
                "import skill_lens, skill_lens.tui; "
                "print(skill_lens.__file__); print(skill_lens.tui.__file__)"
            ),
        ],
        cwd=str(lane_dir),
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    lines = prov_res.stdout.strip().splitlines()
    pkg_prov, tui_prov = lines[0], lines[1]
    if str(venv_dir) not in pkg_prov or str(venv_dir) not in tui_prov:
        raise AssertionError(f"Expected installed wheel provenance inside {venv_dir}; got: {lines}")

    # 2. Assert Textual is present and retrieve version
    txt_res = subprocess.run(
        [str(py_exe), "-c", "import textual; print(textual.__version__)"],
        cwd=str(lane_dir),
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    textual_ver = txt_res.stdout.strip()
    if textual_spec and "==" in textual_spec:
        expected_spec_ver = textual_spec.split("==")[1]
        if textual_ver != expected_spec_ver:
            raise AssertionError(
                f"Expected textual {expected_spec_ver} for endpoint {endpoint_name}; "
                f"got: {textual_ver}"
            )

    # 3. Non-interactive explicit tui invocation: must exit 2 (requires interactive terminal)
    tui_cli_res = subprocess.run(
        [str(cli_exe), "tui"],
        cwd=str(lane_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if tui_cli_res.returncode != 2:
        raise AssertionError(
            f"Explicit non-interactive tui returned exit code {tui_cli_res.returncode}; expected 2"
        )
    if "requires an interactive terminal" not in tui_cli_res.stderr:
        raise AssertionError(
            f"Missing interactive terminal requirement message:\n{tui_cli_res.stderr}"
        )
    if "Traceback" in tui_cli_res.stderr:
        raise AssertionError(
            f"Explicit non-interactive tui emitted traceback:\n{tui_cli_res.stderr}"
        )

    # 4. Prepare isolated test execution directory WITHOUT copying skill_lens source
    test_lane = lane_dir / "test_lane"
    test_lane.mkdir(parents=True, exist_ok=True)
    shutil.copytree(repo_root / "tests", test_lane / "tests")
    shutil.copytree(repo_root / "scripts", test_lane / "scripts")
    shutil.copy(repo_root / "pyproject.toml", test_lane / "pyproject.toml")
    shutil.copy(repo_root / "uv.lock", test_lane / "uv.lock")
    (test_lane / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    shutil.copy(
        repo_root / ".github" / "workflows" / "ci.yml",
        test_lane / ".github" / "workflows" / "ci.yml",
    )

    # Strictly assert no skill_lens source package exists in test_lane
    assert not (test_lane / "skill_lens").exists(), (
        "skill_lens source package must not be copied into test lane"
    )

    # 5. Run test suites with bounded timeout
    test_cmd = [str(pytest_exe), *INSTALLED_TUI_TEST_SUITES, "-ra"]
    try:
        test_res = subprocess.run(
            test_cmd,
            cwd=str(test_lane),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        partial_stdout = (
            exc.stdout
            if isinstance(exc.stdout, str)
            else (exc.stdout or b"").decode("utf-8", "replace")
        )
        partial_stderr = (
            exc.stderr
            if isinstance(exc.stderr, str)
            else (exc.stderr or b"").decode("utf-8", "replace")
        )
        raise AssertionError(
            f"Installed test suites exceeded the {timeout_seconds}s bound "
            f"([{', '.join(test_cmd)}]):\n"
            f"STDOUT (partial):\n{partial_stdout}\n"
            f"STDERR (partial):\n{partial_stderr}"
        ) from exc
    if test_res.returncode != 0:
        raise AssertionError(
            f"Installed test suites failed with code {test_res.returncode}:\n"
            f"STDOUT:\n{test_res.stdout}\n"
            f"STDERR:\n{test_res.stderr}"
        )

    # Parse test and skip counts from summary
    summary_match = re.search(r"=+\s*(.*?)\s+in\s+[\d\.]+s\s*=+", test_res.stdout)
    summary_text = summary_match.group(1) if summary_match else ""
    passed_match = re.search(r"(\d+)\s+passed", summary_text)
    skipped_match = re.search(r"(\d+)\s+skipped", summary_text)
    test_count = int(passed_match.group(1)) if passed_match else 0
    skip_count = int(skipped_match.group(1)) if skipped_match else 0

    return {
        "status": "passed",
        "endpoint": endpoint_name,
        "textual_constraint": textual_spec,
        "textual_version": textual_ver,
        "provenance_pkg": pkg_prov,
        "provenance_tui": tui_prov,
        "installed_packages": installed_packages,
        "explicit_non_tty_tui_exit_code": tui_cli_res.returncode,
        "suites_executed": list(INSTALLED_TUI_TEST_SUITES),
        "suites_exit_code": test_res.returncode,
        "test_count": test_count,
        "skip_count": skip_count,
        "command": test_cmd,
        "stdout": test_res.stdout,
        "stderr": test_res.stderr,
        "tests_run_outside_checkout": True,
        "source_unshadowed": True,
    }


def run_all(
    wheel_path: pathlib.Path,
    sdist_path: pathlib.Path | None = None,
    work_dir: pathlib.Path | None = None,
    receipt_out: pathlib.Path | None = None,
    python_bin: str = sys.executable,
    repo_root: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Execute complete packaging verification across base, min endpoint, and latest endpoint."""
    wheel_path = pathlib.Path(wheel_path).resolve()
    if not wheel_path.exists():
        raise FileNotFoundError(f"Wheel does not exist: {wheel_path}")
    if sdist_path is not None:
        sdist_path = pathlib.Path(sdist_path).resolve()
        if not sdist_path.exists():
            raise FileNotFoundError(f"Sdist does not exist: {sdist_path}")
    if work_dir is not None:
        work_dir = pathlib.Path(work_dir).resolve()
    if receipt_out is not None:
        receipt_out = pathlib.Path(receipt_out).resolve()
    if repo_root is None:
        repo_root = pathlib.Path(__file__).resolve().parent.parent
    repo_root = pathlib.Path(repo_root).resolve()

    temp_ctx = None
    if work_dir is None:
        temp_ctx = tempfile.TemporaryDirectory(prefix="skill-lens-smoke-")
        effective_work_dir = pathlib.Path(temp_ctx.name)
    else:
        work_dir.mkdir(parents=True, exist_ok=True)
        effective_work_dir = work_dir

    try:
        wheel_meta = verify_wheel_contents(wheel_path)
        sdist_meta = verify_sdist_contents(sdist_path) if sdist_path is not None else None

        base_results = verify_base_install(wheel_path, effective_work_dir, python_bin=python_bin)
        min_results = verify_tui_endpoint_install(
            wheel_path,
            effective_work_dir,
            endpoint_name="min",
            textual_spec="textual==8.2.8",
            python_bin=python_bin,
            repo_root=repo_root,
        )
        latest_results = verify_tui_endpoint_install(
            wheel_path,
            effective_work_dir,
            endpoint_name="latest",
            textual_spec=None,
            python_bin=python_bin,
            repo_root=repo_root,
        )

        min_ver = min_results.get("textual_version")
        latest_ver = latest_results.get("textual_version")
        overlap = min_ver == latest_ver

        receipt: dict[str, Any] = {
            "platform": platform.platform(),
            "python": sys.version,
            "wheel": wheel_meta,
            "sdist": sdist_meta,
            "base_lane": base_results,
            "min_endpoint_lane": min_results,
            "latest_endpoint_lane": latest_results,
            "endpoint_overlap": {
                "min_version": min_ver,
                "latest_version": latest_ver,
                "overlap": overlap,
                "note": (
                    "PyPI latest stable equals declared floor (8.2.8) at current index resolution"
                    if overlap
                    else "PyPI latest stable differs from declared floor"
                ),
            },
            "all_passed": True,
        }

        if receipt_out is not None:
            receipt_out.parent.mkdir(parents=True, exist_ok=True)
            receipt_out.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

        return receipt
    finally:
        if temp_ctx is not None:
            temp_ctx.cleanup()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for smoke_wheel."""
    parser = argparse.ArgumentParser(
        description="Verify skill-lens built packaging archives and clean virtualenv execution."
    )
    parser.add_argument(
        "--wheel", type=pathlib.Path, required=True, help="Path to the .whl artifact."
    )
    parser.add_argument(
        "--sdist", type=pathlib.Path, default=None, help="Path to the .tar.gz sdist artifact."
    )
    parser.add_argument(
        "--work-dir", type=pathlib.Path, default=None, help="Isolated working directory."
    )
    parser.add_argument(
        "--receipt-out", type=pathlib.Path, default=None, help="Path to write JSON receipt."
    )
    parser.add_argument(
        "--python-bin", type=str, default=sys.executable, help="Python binary to use."
    )
    parser.add_argument(
        "--verify-archive-only",
        action="store_true",
        help="Only verify wheel and sdist archive contents.",
    )
    parser.add_argument(
        "--verify-base-only",
        action="store_true",
        help="Only verify base installation lane.",
    )
    parser.add_argument(
        "--verify-min-only",
        action="store_true",
        help="Only verify minimum endpoint (textual==8.2.8) installation lane.",
    )
    parser.add_argument(
        "--verify-latest-only",
        action="store_true",
        help="Only verify latest endpoint (unconstrained textual) installation lane.",
    )
    parser.add_argument(
        "--verify-tui-only",
        action="store_true",
        help="Only verify both [tui] endpoint installation lanes (min and latest).",
    )

    args = parser.parse_args(argv)

    wheel_path = args.wheel.resolve()
    sdist_path = args.sdist.resolve() if args.sdist else None
    work_dir = args.work_dir.resolve() if args.work_dir else None
    receipt_out = args.receipt_out.resolve() if args.receipt_out else None

    if args.verify_archive_only:
        wheel_meta = verify_wheel_contents(wheel_path)
        print(f"Verified wheel {wheel_path.name}: {wheel_meta['sha256']}")
        sdist_meta = None
        if sdist_path:
            sdist_meta = verify_sdist_contents(sdist_path)
            print(f"Verified sdist {sdist_path.name}: {sdist_meta['sha256']}")
        if receipt_out:
            receipt_out.parent.mkdir(parents=True, exist_ok=True)
            receipt_out.write_text(
                json.dumps({"wheel": wheel_meta, "sdist": sdist_meta}, indent=2),
                encoding="utf-8",
            )
        return 0

    if args.verify_base_only:
        effective_work_dir = work_dir or pathlib.Path(tempfile.mkdtemp(prefix="smoke-base-"))
        results = verify_base_install(wheel_path, effective_work_dir, python_bin=args.python_bin)
        print("Base installation lane passed successfully.")
        if receipt_out:
            receipt_out.parent.mkdir(parents=True, exist_ok=True)
            receipt_out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        return 0

    if args.verify_min_only:
        effective_work_dir = work_dir or pathlib.Path(tempfile.mkdtemp(prefix="smoke-min-"))
        results = verify_tui_endpoint_install(
            wheel_path,
            effective_work_dir,
            endpoint_name="min",
            textual_spec="textual==8.2.8",
            python_bin=args.python_bin,
        )
        print("Minimum endpoint installation lane passed successfully.")
        if receipt_out:
            receipt_out.parent.mkdir(parents=True, exist_ok=True)
            receipt_out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        return 0

    if args.verify_latest_only:
        effective_work_dir = work_dir or pathlib.Path(tempfile.mkdtemp(prefix="smoke-latest-"))
        results = verify_tui_endpoint_install(
            wheel_path,
            effective_work_dir,
            endpoint_name="latest",
            textual_spec=None,
            python_bin=args.python_bin,
        )
        print("Latest endpoint installation lane passed successfully.")
        if receipt_out:
            receipt_out.parent.mkdir(parents=True, exist_ok=True)
            receipt_out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        return 0

    if args.verify_tui_only:
        effective_work_dir = work_dir or pathlib.Path(tempfile.mkdtemp(prefix="smoke-tui-"))
        min_res = verify_tui_endpoint_install(
            wheel_path,
            effective_work_dir,
            endpoint_name="min",
            textual_spec="textual==8.2.8",
            python_bin=args.python_bin,
        )
        latest_res = verify_tui_endpoint_install(
            wheel_path,
            effective_work_dir,
            endpoint_name="latest",
            textual_spec=None,
            python_bin=args.python_bin,
        )
        print("TUI extra installation lanes (min and latest) passed successfully.")
        if receipt_out:
            receipt_out.parent.mkdir(parents=True, exist_ok=True)
            receipt_out.write_text(
                json.dumps({"min": min_res, "latest": latest_res}, indent=2), encoding="utf-8"
            )
        return 0

    run_all(
        wheel_path=wheel_path,
        sdist_path=sdist_path,
        work_dir=work_dir,
        receipt_out=receipt_out,
        python_bin=args.python_bin,
    )
    print(f"All packaging and installed smoke checks passed! Receipt: {receipt_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
