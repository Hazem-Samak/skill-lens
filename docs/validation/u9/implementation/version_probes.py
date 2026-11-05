#!/usr/bin/env python3
"""Probe the installed version of every preserved installation lane (U9).

``scripts/smoke_wheel.py`` records the base lane's console version but does not
compare all three installed versions. This runs, in each lane's own virtualenv,
from a directory outside the checkout, with the lane's synthetic HOME:

* ``importlib.metadata.version("skill-lens-cli")``
* ``skill_lens.__version__``
* ``<lane>/bin/skill-lens --version``
* the imported ``skill_lens`` file, to prove it is the installed copy
* Textual's version, and its absence in the base lane

Usage:
    python version_probes.py --smoke-dir /tmp/u9-candidate/smoke \
        --artifacts /tmp/u9-candidate/artifacts --out probes.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

EXPECTED = "0.2.0"

LANES = {
    "base": "base_lane",
    "min": "min_lane",
    "latest": "latest_lane",
}

VERSION_SCRIPT = (
    "import importlib.metadata as m, skill_lens, json, importlib.util\n"
    "textual = importlib.util.find_spec('textual')\n"
    "print(json.dumps({\n"
    "    'metadata_version': m.version('skill-lens-cli'),\n"
    "    'package_version': skill_lens.__version__,\n"
    "    'module_file': skill_lens.__file__,\n"
    "    'textual_installed': textual is not None,\n"
    "    'textual_version': (\n"
    "        __import__('textual').__version__ if textual is not None else None\n"
    "    ),\n"
    "}))\n"
)


def probe_lane(name: str, lane_dir: Path, artifacts: list[str]) -> dict[str, Any]:
    venv = lane_dir / "venv"
    python = venv / "bin" / "python"
    cli = venv / "bin" / "skill-lens"
    home = lane_dir / "home"
    home.mkdir(parents=True, exist_ok=True)
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "PYTHONUNBUFFERED": "1",
        "PYTHONNOUSERSITE": "1",
    }
    version_run = subprocess.run(
        [str(python), "-c", VERSION_SCRIPT],
        cwd=str(lane_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    cli_run = subprocess.run(
        [str(cli), "--version"],
        cwd=str(lane_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    parsed = json.loads(version_run.stdout) if version_run.returncode == 0 else {}
    module_file = parsed.get("module_file") or ""
    checks = {
        "metadata_is_0_2_0": parsed.get("metadata_version") == EXPECTED,
        "package_version_is_0_2_0": parsed.get("package_version") == EXPECTED,
        "cli_reports_0_2_0": cli_run.stdout.strip() == f"skill-lens {EXPECTED}",
        "module_inside_lane_venv": str(venv) in module_file,
        "textual_absent_in_base": parsed.get("textual_installed") is False
        if name == "base"
        else None,
        "textual_present_in_tui_lane": parsed.get("textual_installed") is True
        if name != "base"
        else None,
    }
    checks = {key: value for key, value in checks.items() if value is not None}
    return {
        "lane": name,
        "lane_dir": str(lane_dir),
        "cwd": str(lane_dir),
        "home": str(home),
        "python": str(python),
        "metadata_version": parsed.get("metadata_version"),
        "package_version": parsed.get("package_version"),
        "module_file": module_file,
        "textual_installed": parsed.get("textual_installed"),
        "textual_version": parsed.get("textual_version"),
        "cli_output": cli_run.stdout.strip(),
        "cli_exit_code": cli_run.returncode,
        "python_exit_code": version_run.returncode,
        "stderr": version_run.stderr + cli_run.stderr,
        "checks": checks,
        "all_checks_passed": all(checks.values()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-dir", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    artifacts = sorted(str(path) for path in args.artifacts.glob("skill_lens_cli-0.2.0*"))
    lanes = {
        name: probe_lane(name, args.smoke_dir.resolve() / folder, artifacts)
        for name, folder in LANES.items()
    }
    receipt = {
        "python": sys.version,
        "smoke_dir": str(args.smoke_dir.resolve()),
        "artifacts": artifacts,
        "expected_version": EXPECTED,
        "lanes": lanes,
        "all_passed": all(lane["all_checks_passed"] for lane in lanes.values()),
        "note": (
            "Each probe runs that lane's own venv Python and console script from the lane "
            "directory, outside the repository checkout, with the lane's synthetic HOME."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    for name, lane in lanes.items():
        venv_prefix = str(args.smoke_dir.resolve() / LANES[name] / "venv")
        inside = "yes" if venv_prefix in lane["module_file"] else "NO"
        print(
            f"{name:6s} metadata={lane['metadata_version']} package={lane['package_version']} "
            f"cli={lane['cli_output']!r} textual={lane['textual_version']} inside_venv={inside}"
        )
    print(f"all_passed: {receipt['all_passed']}")
    return 0 if receipt["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
