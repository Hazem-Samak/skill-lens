#!/usr/bin/env python3
"""Export, build and inspect the exact 0.2.0 candidate (U9).

The default ``uv build`` packages the whole *working directory* into the source
archive, including untracked junk and the very receipts that describe the
artifact. This script therefore builds from a clean export instead:

1. ``git archive`` of the recorded revision — tracked files only, preserving
   file modes and symlinks — with ``docs/validation/u9/`` removed (sidecar
   evidence must never change the artifact it describes);
2. overlaid copies of exactly the reviewed, changed tracked files;
3. a recorded manifest of every exported path with its SHA-256;
4. ``uv build`` of the sdist from the export, then the wheel from that sdist;
5. ``twine check`` and archive/metadata inspection, with packaged application
   bytes compared against the export.

Artifacts, the export and the receipts stay outside the repository. Run it with
the repository environment's Python:

    .venv/bin/python docs/validation/u9/implementation/qualify_candidate.py \
        --work /tmp/u9-candidate --out docs/validation/u9/implementation/candidate.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]

# The only tracked files U9 is allowed to change (plan §"Allowed implementation scope").
OVERLAID_FILES = (
    "CHANGELOG.md",
    "DEVELOPMENT.md",
    "FULL_SCREEN_TUI.md",
    "README.md",
    "SKILL_LENS_SPECIFICATION.md",
    "pyproject.toml",
    "scripts/smoke_wheel.py",
    "skill_lens/__init__.py",
    "tests/test_tui_packaging.py",
    "uv.lock",
)

EXPECTED_TUI_MODULES = (
    "skill_lens/tui/__init__.py",
    "skill_lens/tui/app.py",
    "skill_lens/tui/session.py",
    "skill_lens/tui/_textual_compat.py",
    "skill_lens/tui/home.py",
    "skill_lens/tui/why.py",
    "skill_lens/tui/diff.py",
    "skill_lens/tui/json_view.py",
    "skill_lens/tui/agents.py",
    "skill_lens/tui/compare.py",
    "skill_lens/tui/doctor.py",
    "skill_lens/tui/help.py",
)

EXPECTED_VERSION = "0.2.0"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=str(cwd), env=env, capture_output=True, text=True)
    return {
        "command": command,
        "cwd": str(cwd),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def export_tree(dest: Path) -> dict[str, Any]:
    """git archive HEAD into ``dest``, drop U9 receipts, overlay reviewed files."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    revision = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    archive = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "archive", "--format=tar", revision],
        check=True,
        capture_output=True,
    ).stdout
    tar_path = dest.parent / "export.tar"
    tar_path.write_bytes(archive)
    with tarfile.open(tar_path) as tf:
        names = tf.getnames()
        if any(".." in name.split("/") for name in names):
            raise SystemExit("refusing to extract an archive with parent-directory entries")
        tf.extractall(dest, filter="data")
    tar_path.unlink()

    exclusions = ["docs/validation/u9/ (sidecar implementation evidence)"]
    receipts = dest / "docs" / "validation" / "u9"
    if receipts.exists():
        shutil.rmtree(receipts)

    overlays: dict[str, str] = {}
    for relative in OVERLAID_FILES:
        source = REPO_ROOT / relative
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        overlays[relative] = sha256_file(source)

    manifest: dict[str, Any] = {}
    for path in sorted(dest.rglob("*")):
        if path.is_symlink() or path.is_file():
            manifest[str(path.relative_to(dest))] = {
                "sha256": sha256_file(path),
                "mode": oct(path.lstat().st_mode),
                "symlink": path.is_symlink(),
            }
    return {
        "source_revision": revision,
        "export_dir": str(dest),
        "exclusions": exclusions,
        "overlaid_inputs": overlays,
        "file_count": len(manifest),
        "manifest": manifest,
    }


def metadata_fields(text: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for line in text.splitlines():
        if not line or line.startswith(" ") or ": " not in line:
            continue
        key, value = line.split(": ", 1)
        fields.setdefault(key, []).append(value)
    return fields


def inspect_wheel(wheel: Path, export: Path) -> dict[str, Any]:
    with zipfile.ZipFile(wheel) as zf:
        names = sorted(zf.namelist())
        metadata_name = next(n for n in names if n.endswith(".dist-info/METADATA"))
        metadata_text = zf.read(metadata_name).decode("utf-8")
        entry_points = zf.read(next(n for n in names if n.endswith(".dist-info/entry_points.txt")))
        packaged = {
            name: sha256_bytes(zf.read(name))
            for name in names
            if name.startswith("skill_lens/") and name.endswith(".py")
        }
    fields = metadata_fields(metadata_text)
    missing_modules = [m for m in EXPECTED_TUI_MODULES if m not in names]
    registry = [
        n for n in names if n.startswith("skill_lens/registry/agents/") and n.endswith(".toml")
    ]

    mismatched = []
    for name, digest in packaged.items():
        source = export / name
        if not source.is_file():
            mismatched.append({"file": name, "problem": "missing from export"})
            continue
        if sha256_file(source) != digest:
            mismatched.append({"file": name, "problem": "bytes differ from export"})
    export_sources = sorted(
        str(p.relative_to(export)) for p in (export / "skill_lens").rglob("*.py") if p.is_file()
    )
    if sorted(packaged) != export_sources:
        mismatched.append(
            {
                "problem": "packaged module set differs from export",
                "packaged": sorted(packaged),
                "export": export_sources,
            }
        )
    return {
        "path": str(wheel),
        "sha256": sha256_file(wheel),
        "name_version": fields.get("Name", []) + fields.get("Version", []),
        "requires_python": fields.get("Requires-Python", []),
        "provides_extra": fields.get("Provides-Extra", []),
        "requires_dist": fields.get("Requires-Dist", []),
        "entry_points": entry_points.decode("utf-8").strip().splitlines(),
        "tui_modules_present": len(EXPECTED_TUI_MODULES) - len(missing_modules),
        "missing_tui_modules": missing_modules,
        "registry_toml_count": len(registry),
        "typed_marker": "skill_lens/py.typed" in names,
        "total_files": len(names),
        "packaged_python_matches_export": not mismatched,
        "packaged_source_problems": mismatched,
        "metadata": metadata_text,
    }


def inspect_sdist(sdist: Path, export: Path) -> dict[str, Any]:
    with tarfile.open(sdist, "r:*") as tf:
        members = [m for m in tf.getmembers() if m.isfile()]
        names = [m.name for m in members]
        prefix = next(n for n in names if n.endswith("pyproject.toml"))[: -len("pyproject.toml")]
        pkg_info = next(name for name in names if name == f"{prefix}PKG-INFO")
        metadata_text = tf.extractfile(pkg_info).read().decode("utf-8")  # type: ignore[union-attr]
    fields = metadata_fields(metadata_text)
    relative = [name[len(prefix) :] for name in names]
    expected = {str(p.relative_to(export)) for p in export.rglob("*") if p.is_file()}
    unexpected = sorted(set(relative) - expected - {"PKG-INFO"})
    missing = sorted(expected - set(relative))
    missing_modules = [m for m in EXPECTED_TUI_MODULES if m not in set(relative)]
    return {
        "path": str(sdist),
        "sha256": sha256_file(sdist),
        "prefix": prefix,
        "name_version": fields.get("Name", []) + fields.get("Version", []),
        "requires_python": fields.get("Requires-Python", []),
        "provides_extra": fields.get("Provides-Extra", []),
        "requires_dist": fields.get("Requires-Dist", []),
        "tui_modules_present": len(EXPECTED_TUI_MODULES) - len(missing_modules),
        "missing_tui_modules": missing_modules,
        "registry_toml_count": sum(
            1
            for n in relative
            if n.startswith("skill_lens/registry/agents/") and n.endswith(".toml")
        ),
        "typed_marker": "skill_lens/py.typed" in relative,
        "total_files": len(names),
        "files_not_in_export": unexpected,
        "export_files_missing_from_sdist": missing,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True, help="Owned scratch directory.")
    parser.add_argument("--out", type=Path, required=True, help="JSON receipt path in the repo.")
    args = parser.parse_args(argv)

    work = args.work.resolve()
    export_dir = work / "src"
    artifacts = work / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.setdefault("UV_CACHE_DIR", str(work / "uv-cache"))
    env.setdefault("UV_TOOL_DIR", str(work / "uv-tools"))
    env.setdefault("UV_TOOL_BIN_DIR", str(work / "uv-tools-bin"))

    export_receipt = export_tree(export_dir)
    wheel = artifacts / f"skill_lens_cli-{EXPECTED_VERSION}-py3-none-any.whl"
    sdist = artifacts / f"skill_lens_cli-{EXPECTED_VERSION}.tar.gz"
    for path in (wheel, sdist):
        if path.exists():
            path.unlink()
    builds: dict[str, Any] = {}
    builds["sdist"] = run(
        ["uv", "build", str(export_dir), "--sdist", "--out-dir", str(artifacts)],
        cwd=work,
        env=env,
    )
    builds["wheel"] = run(
        ["uv", "build", str(sdist), "--wheel", "--out-dir", str(artifacts)],
        cwd=work,
        env=env,
    )
    builds["twine"] = run(["uvx", "twine", "check", str(wheel), str(sdist)], cwd=work, env=env)
    for name, result in builds.items():
        if result["exit_code"] != 0:
            print(json.dumps(result, indent=2))
            raise SystemExit(f"{name} build step failed")

    wheel_info = inspect_wheel(wheel, export_dir)
    sdist_info = inspect_sdist(wheel.parent / sdist.name, export_dir)
    checks = {
        "wheel_name_version": wheel_info["name_version"] == ["skill-lens-cli", EXPECTED_VERSION],
        "sdist_name_version": sdist_info["name_version"] == ["skill-lens-cli", EXPECTED_VERSION],
        "wheel_requires_python": ">=3.11" in " ".join(wheel_info["requires_python"]),
        "wheel_tui_extra": "tui" in wheel_info["provides_extra"],
        "wheel_textual_requirement": any(
            dep.startswith("textual>=8.2.8") for dep in wheel_info["requires_dist"]
        ),
        "wheel_entry_point": "skill-lens = skill_lens.cli:app"
        in " ".join(wheel_info["entry_points"]),
        "wheel_all_tui_modules": wheel_info["tui_modules_present"] == len(EXPECTED_TUI_MODULES),
        "sdist_all_tui_modules": sdist_info["tui_modules_present"] == len(EXPECTED_TUI_MODULES),
        "wheel_registry_count": wheel_info["registry_toml_count"] == 10,
        "sdist_registry_count": sdist_info["registry_toml_count"] == 10,
        "wheel_typed_marker": wheel_info["typed_marker"] is True,
        "sdist_typed_marker": sdist_info["typed_marker"] is True,
        "wheel_bytes_match_export": wheel_info["packaged_python_matches_export"] is True,
        "sdist_has_no_unexpected_files": sdist_info["files_not_in_export"] == [],
        "sdist_contains_all_export_files": sdist_info["export_files_missing_from_sdist"] == [],
        "twine_check_passed": builds["twine"]["exit_code"] == 0,
    }
    receipt = {
        "export": export_receipt,
        "artifacts": {"wheel": wheel_info, "sdist": sdist_info},
        "builds": builds,
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "claim_boundary": (
            "Built from a clean export of the working tree's reviewed changes on the recorded "
            "revision. These hashes describe this candidate only and are invalidated by any "
            "later packaged source or document change."
        ),
    }
    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(checks, indent=2))
    print(f"wheel sha256: {wheel_info['sha256']}")
    print(f"sdist sha256: {sdist_info['sha256']}")
    print(f"all_checks_passed: {receipt['all_checks_passed']}")
    return 0 if receipt["all_checks_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
