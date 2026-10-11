"""Packaging and dependency declaration tests for Skill Lens 0.2 (Assignment U1).

Guards the optional [tui] extra, base runtime dependency isolation,
Textual and Rich lockfile metadata, CI packaging lane definitions, and
output parity under the installed extra.
"""

from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path
from typing import Any, cast

import yaml

import skill_lens.cli as cli

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
UV_LOCK_PATH = REPO_ROOT / "uv.lock"
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
SNAPSHOT_DIR = Path(__file__).parent / "fixtures" / "snapshots"
GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"


def _read_pyproject() -> dict[str, Any]:
    return tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))


def _read_uv_lock() -> dict[str, Any]:
    return tomllib.loads(UV_LOCK_PATH.read_text(encoding="utf-8"))


def _read_ci_workflow() -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(CI_WORKFLOW_PATH.read_text(encoding="utf-8")))


def test_base_runtime_dependencies_exclude_textual() -> None:
    """The base package runtime dependencies must never declare Textual.

    Skill Lens base must remain lean and usable without any full-screen TUI.
    """
    pyproject = _read_pyproject()
    deps = pyproject["project"]["dependencies"]
    for dep in deps:
        assert not dep.lower().startswith("textual"), (
            f"base dependencies must not include Textual; found {dep!r}"
        )


def test_optional_dependencies_declare_textual_floor() -> None:
    """The [tui] extra and [dev] extra must declare textual>=8.2.8."""
    pyproject = _read_pyproject()
    optional = pyproject["project"].get("optional-dependencies", {})
    assert "tui" in optional, "pyproject.toml must declare optional-dependencies.tui"

    tui_deps = optional["tui"]
    assert any(dep.startswith("textual>=8.2.8") for dep in tui_deps), (
        f"[tui] extra must declare textual>=8.2.8; found {tui_deps!r}"
    )

    dev_deps = optional.get("dev", [])
    assert any(dep.startswith("textual>=8.2.8") for dep in dev_deps), (
        f"[dev] extra must declare textual>=8.2.8; found {dev_deps!r}"
    )


def test_uv_lock_pins_textual_and_rich() -> None:
    """uv.lock must pin Textual 8.2.8 and Rich 15.0.0, and provide the tui extra."""
    lock = _read_uv_lock()
    packages = {pkg["name"]: pkg for pkg in lock.get("package", [])}

    assert "textual" in packages, "uv.lock must contain textual"
    assert packages["textual"]["version"] == "8.2.8", (
        f"textual must be pinned to 8.2.8; found {packages['textual']['version']!r}"
    )

    assert "rich" in packages, "uv.lock must contain rich"
    assert packages["rich"]["version"] == "15.0.0", (
        f"rich must be pinned to 15.0.0; found {packages['rich']['version']!r}"
    )

    # Verify skill-lens-cli package in uv.lock provides the tui extra
    root_pkg = next(p for p in lock.get("package", []) if p["name"] == "skill-lens-cli")
    provides_extras = root_pkg.get("metadata", {}).get("provides-extras", [])
    assert "tui" in provides_extras, (
        f"skill-lens-cli in uv.lock must provide tui extra; found {provides_extras!r}"
    )


def test_ci_packaging_job_has_base_and_tui_lanes() -> None:
    """The CI packaging job must test both base fallback and [tui] extra parity."""
    ci = _read_ci_workflow()
    packaging_job = ci["jobs"]["packaging"]
    steps = packaging_job["steps"]

    step_runs = "\n".join(str(s.get("run", "")) for s in steps)

    # 1. Base install assertions
    assert "importlib.util.find_spec('textual') is None" in step_runs, (
        "CI packaging job must assert Textual is absent in base install"
    )
    assert "bare_output=" in step_runs and "Usage: skill-lens" in step_runs, (
        "CI packaging job must assert noninteractive bare invocation prints help"
    )
    assert "Tip:" in step_runs, (
        "CI packaging job must assert tip absence in noninteractive bare invocation"
    )
    assert "skill-lens-cli\\[tui\\]" in step_runs, (
        "CI packaging job must assert explicit tui hint mentions skill-lens-cli[tui]"
    )
    assert 'test "$code" -eq 2' in step_runs, (
        "CI packaging job must assert explicit tui exit code 2"
    )

    # 2. [tui] extra lane assertions
    assert "[tui]" in step_runs, "CI packaging job must install built wheel with [tui] extra"
    assert "import textual" in step_runs, (
        "CI packaging job must verify textual is present in [tui] lane"
    )
    assert "assert '/tmp/smoke-tui' in skill_lens.__file__" in step_runs, (
        "CI packaging job must assert skill_lens.__file__ is inside installed lane"
    )
    assert "/tmp/smoke-tui/bin/pytest" in step_runs, (
        "CI packaging job must run pytest from installed lane virtualenv"
    )
    assert "/tmp/smoke-test-lane" in step_runs, (
        "CI packaging job must run tests outside source checkout"
    )
    assert "test_render_snapshots.py" in step_runs, (
        "CI packaging job must run snapshot suite under installed extra"
    )
    assert "test_fixtures.py" in step_runs, (
        "CI packaging job must run fixtures golden suite under installed extra"
    )
    assert "test_phase3_gate.py" in step_runs, (
        "CI packaging job must run diff golden suite under installed extra"
    )
    assert "test_phase4_gate.py" in step_runs, (
        "CI packaging job must run doctor/compare golden suite under installed extra"
    )


def test_tui_command_is_registered() -> None:
    """`tui` must be registered in app.registered_commands."""
    registered = {cmd.callback.__name__ for cmd in cli.app.registered_commands if cmd.callback}
    assert "tui" in registered, f"`tui` must be a registered CLI command; found {registered!r}"


def test_installed_extra_output_parity(tmp_path: Path) -> None:
    """Focused in-process output parity check: verifying core command renders
    and goldens remain unchanged with Textual installed.

    Full comprehensive parity across all 17 snapshots and 16 goldens is executed
    by the installed wheel packaging lanes in CI and smoke_wheel.py.
    """
    # 1. Verify Textual is actually present in the running test environment
    assert importlib.util.find_spec("textual") is not None, (
        "This parity gate requires Textual to be installed in the environment"
    )

    from skill_lens.core import paths
    from tests import test_fixtures, test_phase3_gate, test_phase4_gate, test_render_snapshots

    try:

        def _make_home(label: str) -> Path:
            h = (tmp_path / label).resolve()
            h.mkdir(parents=True, exist_ok=True)
            paths.set_sandbox(h)
            return h

        # Focused verification across command render surfaces
        test_render_snapshots.test_scan_snapshot(_make_home("snap_scan"), update_snapshots=False)
        test_render_snapshots.test_why_snapshot(_make_home("snap_why"), update_snapshots=False)
        test_render_snapshots.test_diff_snapshot(_make_home("snap_diff"), update_snapshots=False)
        test_render_snapshots.test_doctor_snapshot_findings(
            _make_home("snap_doctor"), update_snapshots=False
        )
        test_render_snapshots.test_compare_snapshot_farm(
            _make_home("snap_compare"), update_snapshots=False
        )

        # Focused golden JSON checks
        test_fixtures.test_golden_installations_match_the_scan(
            "variant_hash_detection", _make_home("golden_scan_1")
        )
        test_fixtures.test_golden_installations_match_the_scan(
            "claude_personal_beats_project", _make_home("golden_scan_2")
        )
        test_phase3_gate.test_diff_matches_the_golden(_make_home("golden_diff"))
        test_phase4_gate.test_doctor_golden_on_the_acceptance_farm(
            _make_home("golden_doctor"), update_goldens=False
        )
        test_phase4_gate.test_compare_golden_on_the_acceptance_farm(
            _make_home("golden_compare"), update_goldens=False
        )

        # Verify fixture counts are intact (17 snapshots, 16 goldens)
        snapshots = list(SNAPSHOT_DIR.glob("*.txt"))
        assert len(snapshots) == 17, f"Expected 17 snapshots; found {len(snapshots)}"

        goldens = list(GOLDEN_DIR.glob("*.json")) + list((GOLDEN_DIR / "phase4").glob("*.json"))
        assert len(goldens) == 16, f"Expected 16 golden JSON files; found {len(goldens)}"
    finally:
        paths.set_sandbox(None)
