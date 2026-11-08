"""Packaging and installed-wheel verification tests (Assignment U1 and Stage G).

Specification reference: FULL_SCREEN_TUI.md §21.7, Stage G brief, F10/R02.
Covers:
1. Base runtime dependencies exclude Textual
2. Optional dependencies declare textual>=8.2.8 floor for [tui] and [dev]
3. uv.lock pins textual 8.2.8 and rich 15.0.0, and tracks the package version
4. CI workflow contains strengthened packaging jobs (archive content gate,
   base fallback lane, min endpoint textual==8.2.8, latest endpoint unconstrained)
5. Packaging validator (verify_wheel_contents and verify_sdist_contents
   from canonical scripts.smoke_wheel):
   - Synthetic clean wheel and sdist pass archive verification
   - Synthetic stale wheel (0 TUI modules) fails due to missing TUI modules
   - Synthetic wheels missing each individual TUI module fail with exact diagnostics
   - Synthetic wheels missing agent registry TOMLs or py.typed fail
   - Synthetic sdist missing required modules or files fails
   - Synthetic sdists missing each individual TUI module fail (U9)
6. Installed extra output parity across command surfaces
7. Installed lane assurance guards:
   - Module provenance failure rejection (base and both endpoint branches)
   - Textual presence failure rejection in base environment
   - Nonzero test suite returncode failure rejection
   - Bounded test suite timeout rejection (partial stdout/stderr preserved, chained cause)
   - Source directory leak in test lane rejection
   - Receipt accuracy: the pytest summary is parsed (modern elapsed form and
     legacy form), an unparsable summary raises instead of reporting zero, and a
     lane that passed no tests is rejected
8. Relative wheel and harness paths normalized before lane cwd switch
9. U9 manifest and selection guards (independent of the production tuples):
   - The 13-module archive manifest equals a hand-maintained expectation and the
     shipped ``skill_lens/tui`` sources
   - The 15 installed test selections equal a hand-maintained expectation
   - Every selected node ID exists, and the selected size case covers 100x30
     and 60x24
   - The full selection reaches the lane's own pytest argv with no silencing filter
"""

from __future__ import annotations

import ast
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

import skill_lens
from skill_lens import cli
from skill_lens.core import paths

_REAL_SUBPROCESS_RUN = subprocess.run

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
UV_LOCK_PATH = REPO_ROOT / "uv.lock"
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
SNAPSHOT_DIR = Path(__file__).parent / "fixtures" / "snapshots"
GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"

# Hand-maintained copies of what the packaging harness must cover (U9).
#
# These are deliberately NOT derived from ``scripts.smoke_wheel``. A guard that
# compares a production tuple with itself can never notice an omitted manifest
# entry or a silently dropped installed test selection; it only proves the tuple
# equals itself. When the manifest legitimately grows, update this list and the
# harness together — one of the equality guards failing is the intended alarm.
EXPECTED_TUI_MODULES: tuple[str, ...] = (
    "skill_lens/tui/__init__.py",
    "skill_lens/tui/app.py",
    "skill_lens/tui/session.py",
    "skill_lens/tui/theme.py",
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

EXPECTED_INSTALLED_TEST_SUITES: tuple[str, ...] = (
    "tests/test_render_snapshots.py",
    "tests/test_fixtures.py",
    "tests/test_phase3_gate.py",
    "tests/test_phase4_gate.py",
    "tests/test_tui_app.py",
    "tests/test_tui_session.py",
    "tests/test_tui_read_only.py",
    "tests/test_stage_g_repairs.py",
    "tests/test_tui_packaging.py",
    "tests/test_tui_routing.py",
    "tests/test_tui_help.py::test_complete_keyboard_browsing_flow_with_help_json_filters_and_refresh",
    "tests/test_tui_help.py::test_views_stay_on_captured_data_until_refresh_after_fixture_edits",
    "tests/test_tui_help.py::test_all_six_json_views_match_the_cli_serializer_on_same_inputs",
    "tests/test_tui_help.py::test_every_screen_and_help_remains_usable_at_both_sizes",
    "tests/test_tui_visual.py",
)

# Options that can narrow a pytest selection while the lane still reports success.
_PYTEST_SELECTION_OPTIONS = frozenset(
    {
        "-k",
        "-m",
        "-x",
        "--maxfail",
        "--deselect",
        "--ignore",
        "--ignore-glob",
        "--lf",
        "--last-failed",
        "--ff",
        "--failed-first",
        "--sw",
        "--stepwise",
        "--co",
        "--collect-only",
        "-p",
    }
)

SYNTHETIC_SDIST_PREFIX = "skill_lens_cli-0.0.0-synthetic/"

# Single canonical packaging validator imported directly from scripts/smoke_wheel.py
try:
    import scripts.smoke_wheel as smoke_wheel
    from scripts.smoke_wheel import (
        REQUIRED_REGISTRY_COUNT,
        REQUIRED_TUI_MODULES,
        REQUIRED_TYPED_MARKER,
        parse_pytest_summary,
        pytest_summary_line,
        verify_base_install,
        verify_sdist_contents,
        verify_tui_endpoint_install,
        verify_wheel_contents,
    )
except ImportError:
    import importlib.util

    script_path = REPO_ROOT / "scripts" / "smoke_wheel.py"
    spec = importlib.util.spec_from_file_location("smoke_wheel", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["scripts.smoke_wheel"] = mod
    spec.loader.exec_module(mod)
    smoke_wheel = mod
    verify_wheel_contents = mod.verify_wheel_contents
    verify_sdist_contents = mod.verify_sdist_contents
    verify_base_install = mod.verify_base_install
    verify_tui_endpoint_install = mod.verify_tui_endpoint_install
    REQUIRED_TUI_MODULES = mod.REQUIRED_TUI_MODULES
    REQUIRED_REGISTRY_COUNT = mod.REQUIRED_REGISTRY_COUNT
    REQUIRED_TYPED_MARKER = mod.REQUIRED_TYPED_MARKER
    parse_pytest_summary = mod.parse_pytest_summary
    pytest_summary_line = mod.pytest_summary_line


def _selected_node_missing(selections: Iterable[str], root: Path = REPO_ROOT) -> list[str]:
    """Return the selections whose test file or test function is absent under ``root``.

    A selected node ID that no longer exists makes pytest exit with "no tests ran"
    only after a slow cold install, so the selection is checked statically first.
    """
    missing: list[str] = []
    for selection in selections:
        file_part, _, node_id = selection.partition("::")
        path = root / file_part
        if not path.is_file():
            missing.append(selection)
            continue
        if node_id and node_id not in _function_names(path.read_text(encoding="utf-8")):
            missing.append(selection)
    return missing


def _function_names(source: str) -> set[str]:
    """Return the module-level function and async-function names in ``source``."""
    return {
        node.name
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }


def _parametrized_sizes(source: str, function: str) -> list[tuple[int, int]]:
    """Return the ``size`` parametrization values declared on ``function``."""
    for node in ast.parse(source).body:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if node.name != function:
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or len(decorator.args) < 2:
                continue
            names = decorator.args[0]
            if not isinstance(names, ast.Constant) or names.value != "size":
                continue
            return [tuple(value) for value in ast.literal_eval(decorator.args[1])]
    return []


def _pytest_selection_overrides(argv: Sequence[str]) -> list[str]:
    """Return any pytest option in ``argv`` that can silently narrow the selection."""
    overrides: list[str] = []
    for arg in argv:
        if arg.split("=", 1)[0] in _PYTEST_SELECTION_OPTIONS:
            overrides.append(arg)
    return overrides


def _add_sdist_entry(tf: tarfile.TarFile, name: str, data: bytes = b"# mock\n") -> None:
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    tf.addfile(info, io.BytesIO(data))


def _synthetic_sdist(path: Path, omit: str | None = None) -> Path:
    """Build a valid synthetic sdist, optionally omitting one required TUI module."""
    with tarfile.open(path, "w:gz") as tf:
        for fname in ("pyproject.toml", "README.md", "LICENSE", REQUIRED_TYPED_MARKER):
            _add_sdist_entry(tf, f"{SYNTHETIC_SDIST_PREFIX}{fname}")
        for module in EXPECTED_TUI_MODULES:
            if module != omit:
                _add_sdist_entry(tf, f"{SYNTHETIC_SDIST_PREFIX}{module}")
        for index in range(10):
            _add_sdist_entry(
                tf, f"{SYNTHETIC_SDIST_PREFIX}skill_lens/registry/agents/agent_{index}.toml"
            )
    return path


def _read_pyproject() -> dict[str, Any]:
    return tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))


def _read_uv_lock() -> dict[str, Any]:
    assert UV_LOCK_PATH.exists(), f"uv.lock must exist at {UV_LOCK_PATH}"
    return tomllib.loads(UV_LOCK_PATH.read_text(encoding="utf-8"))


def _read_ci_workflow() -> dict[str, Any]:
    assert CI_WORKFLOW_PATH.exists(), f"ci.yml must exist at {CI_WORKFLOW_PATH}"
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

    root_pkg = next(p for p in lock.get("package", []) if p["name"] == "skill-lens-cli")
    provides_extras = root_pkg.get("metadata", {}).get("provides-extras", [])
    assert "tui" in provides_extras, (
        f"skill-lens-cli in uv.lock must provide tui extra; found {provides_extras!r}"
    )


def test_uv_lock_root_package_version_matches_the_package() -> None:
    """A version bump must refresh the lock's root package entry as well.

    ``test_phase5_gate`` already pins ``pyproject.toml`` to ``__version__``; this
    closes the third declaration. A stale lock would describe a distribution that
    does not exist, and the lock is what CI installs from.
    """
    lock = _read_uv_lock()
    root_pkg = next(p for p in lock.get("package", []) if p["name"] == "skill-lens-cli")
    assert root_pkg["version"] == skill_lens.__version__, (
        f"uv.lock records skill-lens-cli {root_pkg['version']!r} but the package is "
        f"{skill_lens.__version__!r}; run `uv lock` after bumping the version"
    )


def test_ci_packaging_job_has_base_and_tui_lanes() -> None:
    """The CI packaging job must test base fallback and both min and latest [tui] endpoints."""
    ci = _read_ci_workflow()
    packaging_job = ci["jobs"]["packaging"]
    steps = packaging_job["steps"]

    step_runs = "\n".join(str(s.get("run", "")) for s in steps)

    # 1. Archive content gate
    assert "scripts/smoke_wheel.py --verify-archive-only" in step_runs, (
        "CI packaging job must invoke smoke_wheel.py archive verification"
    )

    # 2. Base lane verification
    assert "scripts/smoke_wheel.py --verify-base-only" in step_runs, (
        "CI packaging job must invoke smoke_wheel.py base lane verification"
    )

    # 3. Min endpoint lane (textual==8.2.8)
    assert "scripts/smoke_wheel.py --verify-min-only" in step_runs, (
        "CI packaging job must invoke smoke_wheel.py min endpoint verification"
    )

    # 4. Latest endpoint lane (unconstrained)
    assert "scripts/smoke_wheel.py --verify-latest-only" in step_runs, (
        "CI packaging job must invoke smoke_wheel.py latest endpoint verification"
    )


def test_tui_command_is_registered() -> None:
    """`tui` must be registered in app.registered_commands."""
    registered = {cmd.callback.__name__ for cmd in cli.app.registered_commands if cmd.callback}
    assert "tui" in registered, f"`tui` must be a registered CLI command; found {registered!r}"


# --- U9 archive manifest and installed-selection guards -------------------


def test_required_tui_module_manifest_matches_the_hand_maintained_list() -> None:
    """The archive manifest must be exactly the 13-module expectation.

    The expectation above is written out by hand on purpose: comparing the
    production tuple with itself (or building the fixture from it) cannot catch
    an omitted screen module.
    """
    assert REQUIRED_TUI_MODULES == EXPECTED_TUI_MODULES, (
        "scripts/smoke_wheel.REQUIRED_TUI_MODULES drifted from the independent U9 "
        f"expectation: {REQUIRED_TUI_MODULES!r}"
    )


def test_manifest_covers_every_shipped_tui_source_module() -> None:
    """Every ``skill_lens/tui/*.py`` that ships must be in the manifest.

    This is the completeness half of the guard: a new screen module added later
    would silently escape the archive check until someone remembered it.
    """
    tui_dir = Path(skill_lens.__file__).resolve().parent / "tui"
    assert tui_dir.is_dir(), f"the imported package has no tui directory: {tui_dir}"
    on_disk = sorted(f"skill_lens/tui/{path.name}" for path in tui_dir.glob("*.py"))
    assert on_disk == sorted(EXPECTED_TUI_MODULES), (
        "the required TUI module manifest and the shipped TUI sources disagree: "
        f"on disk {on_disk!r}"
    )


def test_installed_tui_test_selection_matches_the_hand_maintained_list() -> None:
    """The installed lane must keep the nine original suites and the five U9 additions."""
    assert smoke_wheel.INSTALLED_TUI_TEST_SUITES == EXPECTED_INSTALLED_TEST_SUITES, (
        "scripts/smoke_wheel.INSTALLED_TUI_TEST_SUITES drifted from the independent "
        f"U9 expectation: {smoke_wheel.INSTALLED_TUI_TEST_SUITES!r}"
    )


def test_every_installed_selection_resolves_to_a_real_test_node() -> None:
    """All 14 selections must name an existing file and (where given) test function."""
    assert _selected_node_missing(EXPECTED_INSTALLED_TEST_SUITES) == []


def test_selection_existence_guard_rejects_a_renamed_node_id() -> None:
    """Negative control: a renamed test or missing file must be reported."""
    bogus_node = "tests/test_tui_help.py::test_this_node_does_not_exist"
    missing_file = "tests/test_does_not_exist.py"
    assert _selected_node_missing([bogus_node, missing_file]) == [bogus_node, missing_file]


def test_selected_help_size_case_covers_both_terminal_sizes() -> None:
    """The selected parametrized case must really run at 100x30 and 60x24."""
    source = (REPO_ROOT / "tests" / "test_tui_help.py").read_text(encoding="utf-8")
    assert _parametrized_sizes(
        source, "test_every_screen_and_help_remains_usable_at_both_sizes"
    ) == [
        (100, 30),
        (60, 24),
    ]


def test_size_coverage_guard_rejects_a_single_size_parametrization() -> None:
    """Negative control: a one-size parametrization must not satisfy the guard."""
    source = (
        "import pytest\n\n"
        '@pytest.mark.parametrize("size", [(100, 30)])\n'
        "def test_one_size(size):\n"
        "    pass\n"
    )
    sizes = _parametrized_sizes(source, "test_one_size")
    assert sizes == [(100, 30)]
    assert sizes != [(100, 30), (60, 24)]


def test_synthetic_clean_wheel_passes_verification(tmp_path: Path) -> None:
    """A valid synthetic wheel passes the canonical packaging validator."""
    wheel_path = tmp_path / "synthetic_clean.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        for mod in REQUIRED_TUI_MODULES:
            zf.writestr(mod, "# valid\n")
        for i in range(10):
            zf.writestr(f"skill_lens/registry/agents/agent_{i}.toml", "name = 'test'\n")
        zf.writestr(REQUIRED_TYPED_MARKER, "")

    meta = verify_wheel_contents(wheel_path)
    assert meta["typed_marker"] is True
    assert meta["registry_count"] == 10
    assert len(meta["tui_modules"]) == len(REQUIRED_TUI_MODULES)


def test_synthetic_clean_sdist_passes_verification(tmp_path: Path) -> None:
    """A valid synthetic sdist passes the canonical packaging validator."""
    sdist_path = tmp_path / "synthetic_clean_sdist.tar.gz"
    prefix = "skill_lens_cli-0.1.1/"
    with tarfile.open(sdist_path, "w:gz") as tf:
        for fname in ("pyproject.toml", "README.md", "LICENSE", REQUIRED_TYPED_MARKER):
            data = b"# mock\n"
            ti = tarfile.TarInfo(name=f"{prefix}{fname}")
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))
        for mod in REQUIRED_TUI_MODULES:
            data = b"# mock\n"
            ti = tarfile.TarInfo(name=f"{prefix}{mod}")
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))
        for i in range(10):
            data = b"name = 'test'\n"
            ti = tarfile.TarInfo(name=f"{prefix}skill_lens/registry/agents/agent_{i}.toml")
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))

    meta = verify_sdist_contents(sdist_path)
    assert meta["registry_count"] == 10
    assert len(meta["tui_modules"]) == len(REQUIRED_TUI_MODULES)


def test_synthetic_stale_wheel_zero_tui_modules_fails(tmp_path: Path) -> None:
    """A synthetic stale wheel with 0 TUI modules is rejected by canonical validator."""
    wheel_path = tmp_path / "synthetic_stale_zero_tui.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        for i in range(10):
            zf.writestr(f"skill_lens/registry/agents/agent_{i}.toml", "name = 'test'\n")
        zf.writestr(REQUIRED_TYPED_MARKER, "")

    with pytest.raises(ValueError, match="missing required TUI module"):
        verify_wheel_contents(wheel_path)


@pytest.mark.parametrize("omitted_module", EXPECTED_TUI_MODULES)
def test_synthetic_wheel_missing_tui_module_fails(tmp_path: Path, omitted_module: str) -> None:
    """A disposable wheel missing any single required TUI module fails canonical verification."""
    wheel_path = tmp_path / f"synthetic_missing_{Path(omitted_module).stem}.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        for mod in EXPECTED_TUI_MODULES:
            if mod != omitted_module:
                zf.writestr(mod, "# mock\n")
        for i in range(10):
            zf.writestr(f"skill_lens/registry/agents/agent_{i}.toml", "name = 'test'\n")
        zf.writestr(REQUIRED_TYPED_MARKER, "")

    with pytest.raises(ValueError, match=f"missing required TUI module.*{omitted_module}"):
        verify_wheel_contents(wheel_path)


def test_synthetic_wheel_missing_registry_files_fails(tmp_path: Path) -> None:
    """A disposable wheel with fewer than 10 registry agent TOMLs fails canonical verification."""
    wheel_path = tmp_path / "synthetic_missing_registry.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        for mod in REQUIRED_TUI_MODULES:
            zf.writestr(mod, "# mock\n")
        for i in range(5):
            zf.writestr(f"skill_lens/registry/agents/agent_{i}.toml", "name = 'test'\n")
        zf.writestr(REQUIRED_TYPED_MARKER, "")

    with pytest.raises(ValueError, match="contains 5 agent registry TOMLs; expected exactly 10"):
        verify_wheel_contents(wheel_path)


def test_synthetic_wheel_missing_typed_marker_fails(tmp_path: Path) -> None:
    """A disposable wheel missing skill_lens/py.typed fails canonical verification."""
    wheel_path = tmp_path / "synthetic_missing_pytyped.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        for mod in REQUIRED_TUI_MODULES:
            zf.writestr(mod, "# mock\n")
        for i in range(10):
            zf.writestr(f"skill_lens/registry/agents/agent_{i}.toml", "name = 'test'\n")

    with pytest.raises(ValueError, match="missing typing marker: skill_lens/py.typed"):
        verify_wheel_contents(wheel_path)


def test_synthetic_sdist_missing_file_fails(tmp_path: Path) -> None:
    """A disposable sdist missing required files fails canonical verification."""
    sdist_path = tmp_path / "synthetic_bad_sdist.tar.gz"
    prefix = "skill_lens_cli-0.1.1/"

    with tarfile.open(sdist_path, "w:gz") as tf:
        data = b"[project]\nname='test'\n"
        ti = tarfile.TarInfo(name=f"{prefix}pyproject.toml")
        ti.size = len(data)
        tf.addfile(ti, io.BytesIO(data))

    with pytest.raises(ValueError, match="missing required file"):
        verify_sdist_contents(sdist_path)


@pytest.mark.parametrize("omitted_module", EXPECTED_TUI_MODULES)
def test_synthetic_sdist_missing_tui_module_fails(tmp_path: Path, omitted_module: str) -> None:
    """Omitting any single TUI module from the source archive must be rejected.

    The wheel guard cannot see this: an sdist built without a screen module still
    produces a wheel that lacks it, and the sdist is the artifact a downstream
    rebuild starts from.
    """
    sdist_path = _synthetic_sdist(
        tmp_path / f"synthetic_sdist_missing_{Path(omitted_module).stem}.tar.gz",
        omit=omitted_module,
    )

    with pytest.raises(ValueError, match=re.escape(omitted_module)):
        verify_sdist_contents(sdist_path)


def test_synthetic_complete_sdist_passes_the_module_guard(tmp_path: Path) -> None:
    """Control for the omission cases: the same builder with nothing omitted passes."""
    meta = verify_sdist_contents(_synthetic_sdist(tmp_path / "synthetic_complete.tar.gz"))
    assert meta["tui_modules"] == list(REQUIRED_TUI_MODULES)
    assert meta["registry_count"] == 10


def test_installed_extra_output_parity(mock_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Focused in-process output parity check: verifying core command renders
    and goldens remain unchanged with Textual installed.

    Full comprehensive parity across all 17 snapshots and 16 goldens is executed
    by the installed wheel packaging lanes in CI and smoke_wheel.py.
    """
    assert importlib.util.find_spec("textual") is not None, (
        "This parity gate requires Textual to be installed in the environment"
    )

    from tests import test_fixtures, test_phase3_gate, test_phase4_gate, test_render_snapshots

    def _make_home(label: str) -> Path:
        h = (mock_home / label).resolve()
        h.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(h))
        paths.set_sandbox(h)
        return h

    try:
        test_render_snapshots.test_scan_snapshot(_make_home("snap_scan"), update_snapshots=False)
        test_render_snapshots.test_why_snapshot(_make_home("snap_why"), update_snapshots=False)
        test_render_snapshots.test_diff_snapshot(_make_home("snap_diff"), update_snapshots=False)
        test_render_snapshots.test_doctor_snapshot_findings(
            _make_home("snap_doctor"), update_snapshots=False
        )
        test_render_snapshots.test_compare_snapshot_farm(
            _make_home("snap_compare"), update_snapshots=False
        )

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

        snapshots = list(SNAPSHOT_DIR.glob("*.txt"))
        assert len(snapshots) == 17, f"Expected 17 snapshots; found {len(snapshots)}"

        goldens = list(GOLDEN_DIR.glob("*.json")) + list((GOLDEN_DIR / "phase4").glob("*.json"))
        assert len(goldens) == 16, f"Expected 16 golden JSON files; found {len(goldens)}"
    finally:
        paths.set_sandbox(None)


def _make_packaging_subprocess_runner(
    *,
    base_provenance: str | None = None,
    endpoint_pkg_provenance: str | None = None,
    endpoint_tui_provenance: str | None = None,
    simulate_textual_in_base: bool = False,
    pytest_returncode: int = 0,
    pytest_stdout: str = "================ 10 passed in 0.1s ================\n",
    pytest_stderr: str = "",
    captured_calls: list[dict[str, Any]] | None = None,
    pytest_timeout: bool = False,
    pytest_partial_bytes: bool = False,
) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Create a deterministic subprocess runner double for installed lane packaging tests.

    With ``pytest_timeout=True`` the ``pytest`` invocation raises
    ``subprocess.TimeoutExpired`` after the earlier install/provenance calls,
    simulating an exceeded suite run. The partial output is bytes when
    ``pytest_partial_bytes=True`` and str otherwise.
    """

    def mock_subprocess_run(
        cmd: list[str], *args: Any, **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        cwd = kwargs.get("cwd")
        if captured_calls is not None:
            captured_calls.append({"cmd": list(cmd), "cwd": cwd, "env": kwargs.get("env")})

        # Check for wheel references in the command
        for arg in cmd:
            if "skill_lens_cli" in arg:
                # Strip extras if present (e.g. "...whl[tui]")
                wheel_part = arg.split("[")[0] if "[" in arg else arg
                target = Path(wheel_part)
                # If target is relative, the subprocess resolves it relative to cwd
                lookup_path = (
                    target if target.is_absolute() else (Path(cwd) / target if cwd else target)
                )
                if not lookup_path.exists():
                    raise subprocess.CalledProcessError(
                        1,
                        cmd,
                        output="",
                        stderr=f"File not found from subprocess cwd {cwd}: {lookup_path}",
                    )

        # Mock standard subprocess responses expected by smoke_wheel
        cmd_exe = Path(cmd[0]).name if cmd else ""

        if cmd_exe == "uv":
            if "list" in cmd:
                list_json = json.dumps(
                    [
                        {"name": "skill-lens-cli", "version": "0.1.1"},
                        {"name": "textual", "version": "8.2.8"},
                    ]
                )
                return subprocess.CompletedProcess(cmd, 0, stdout=list_json, stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        if cmd_exe.startswith("python"):
            if "-c" in cmd:
                code_arg = cmd[cmd.index("-c") + 1]
                if "skill_lens.__file__" in code_arg:
                    default_venv = Path(cwd) / "venv" if cwd else Path("/dummy/venv")
                    default_site = (
                        default_venv / "lib" / "python3.11" / "site-packages" / "skill_lens"
                    )
                    if "skill_lens.tui" in code_arg:
                        pkg_p = (
                            endpoint_pkg_provenance
                            if endpoint_pkg_provenance is not None
                            else str(default_site / "__init__.py")
                        )
                        tui_p = (
                            endpoint_tui_provenance
                            if endpoint_tui_provenance is not None
                            else str(default_site / "tui" / "__init__.py")
                        )
                        out = f"{pkg_p}\n{tui_p}\n"
                        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")
                    pkg_p = (
                        base_provenance
                        if base_provenance is not None
                        else str(default_site / "__init__.py")
                    )
                    return subprocess.CompletedProcess(cmd, 0, stdout=f"{pkg_p}\n", stderr="")
                if "find_spec('textual')" in code_arg:
                    if simulate_textual_in_base:
                        res = _REAL_SUBPROCESS_RUN(
                            [sys.executable, "-c", code_arg],
                            capture_output=True,
                            text=True,
                        )
                        if res.returncode != 0:
                            raise subprocess.CalledProcessError(
                                res.returncode, cmd, output=res.stdout, stderr=res.stderr
                            )
                        return subprocess.CompletedProcess(
                            cmd, 0, stdout=res.stdout, stderr=res.stderr
                        )
                    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
                if "textual.__version__" in code_arg:
                    return subprocess.CompletedProcess(cmd, 0, stdout="8.2.8\n", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        if cmd_exe == "skill-lens":
            if len(cmd) == 1:
                return subprocess.CompletedProcess(
                    cmd, 0, stdout="Usage: skill-lens [OPTIONS] COMMAND [ARGS]...\n", stderr=""
                )
            if "--version" in cmd:
                return subprocess.CompletedProcess(cmd, 0, stdout="skill-lens 0.1.1\n", stderr="")
            if "--help" in cmd:
                return subprocess.CompletedProcess(
                    cmd, 0, stdout="Usage: skill-lens [OPTIONS]\n", stderr=""
                )
            if cmd[1:] == ["tui"]:
                if cwd and "base_lane" in str(cwd):
                    msg = (
                        "Error: The 'tui' command requires the optional [tui] extra. "
                        "Install with: pip install 'skill-lens-cli[tui]'\n"
                    )
                else:
                    msg = "Error: The terminal UI requires an interactive terminal.\n"
                return subprocess.CompletedProcess(cmd, 2, stdout="", stderr=msg)

        if cmd_exe == "pytest":
            if pytest_timeout:
                stdout_partial: str | bytes = (
                    b"PARTIAL SUITE STDOUT" if pytest_partial_bytes else "PARTIAL SUITE STDOUT"
                )
                stderr_partial: str | bytes = (
                    b"PARTIAL SUITE STDERR" if pytest_partial_bytes else "PARTIAL SUITE STDERR"
                )
                raise subprocess.TimeoutExpired(
                    list(cmd),
                    timeout=kwargs.get("timeout"),
                    output=stdout_partial,
                    stderr=stderr_partial,
                )
            if pytest_returncode != 0:
                return subprocess.CompletedProcess(
                    cmd, pytest_returncode, stdout=pytest_stdout, stderr=pytest_stderr
                )
            return subprocess.CompletedProcess(cmd, 0, stdout=pytest_stdout, stderr=pytest_stderr)

        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    return mock_subprocess_run


def test_expanded_installed_selection_reaches_the_real_pytest_command(
    tmp_path: Path, mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every U9 selection must reach the lane's own pytest argv, unfiltered.

    The runner builds its own command list, so a narrowing option (``-k``,
    ``--deselect``, ``--ignore`` …) or a hand-trimmed list could drop the new
    browsing/parity cases while the lane still reports success. This drives the
    real command builder through a deterministic subprocess double and reads back
    the argv it would execute.
    """
    invoking_cwd = tmp_path / "invoking_cwd"
    invoking_cwd.mkdir()
    wheel_file = invoking_cwd / "skill_lens_cli-0.2.0-py3-none-any.whl"
    wheel_file.write_bytes(bytes([80, 75, 5, 6]) + bytes(18))
    monkeypatch.chdir(invoking_cwd)

    captured_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        subprocess, "run", _make_packaging_subprocess_runner(captured_calls=captured_calls)
    )

    result = verify_tui_endpoint_install(
        wheel_file,
        tmp_path / "work_dir",
        endpoint_name="min",
        textual_spec="textual==8.2.8",
        repo_root=REPO_ROOT,
    )

    pytest_calls = [call for call in captured_calls if Path(call["cmd"][0]).name == "pytest"]
    assert len(pytest_calls) == 1, pytest_calls
    argv = pytest_calls[0]["cmd"]

    lane_dir = (tmp_path / "work_dir" / "min_lane").resolve()
    assert Path(argv[0]).parent == lane_dir / "venv" / "bin", (
        f"the lane must run its own pytest, not the repository one: {argv[0]!r}"
    )
    assert Path(pytest_calls[0]["cwd"]) == lane_dir / "test_lane"
    assert tuple(argv[1:]) == (*EXPECTED_INSTALLED_TEST_SUITES, "-ra"), (
        f"installed pytest argv does not carry the expected selection: {argv[1:]!r}"
    )
    assert _pytest_selection_overrides(argv) == []
    assert tuple(result["suites_executed"]) == EXPECTED_INSTALLED_TEST_SUITES


def test_selection_override_guard_rejects_a_narrowing_option() -> None:
    """Negative control: the argv guard must see options that silently skip tests."""
    assert _pytest_selection_overrides(["-k", "not slow"]) == ["-k"]
    assert _pytest_selection_overrides(["--deselect=tests/x.py::test_y"]) == [
        "--deselect=tests/x.py::test_y"
    ]
    assert _pytest_selection_overrides([*EXPECTED_INSTALLED_TEST_SUITES, "-ra"]) == []


def test_relative_wheel_and_harness_paths_normalized_before_cwd_switch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Relative wheel, work-dir, and receipt paths must be resolved to absolute paths
    before changing subprocess cwd to lane_dir.

    A failure to normalize causes subprocess tools (like uv pip install) running inside
    isolated lane_dir to look up relative paths relative to lane_dir rather than
    the invoking cwd, reproducing the CI failure.
    """
    invoking_cwd = tmp_path / "invoking_cwd"
    invoking_cwd.mkdir()
    artifacts_dir = invoking_cwd / "artifacts"
    artifacts_dir.mkdir()
    wheel_file = artifacts_dir / "skill_lens_cli-0.1.1-py3-none-any.whl"
    wheel_file.write_bytes(bytes([80, 75, 5, 6]) + bytes(18))  # minimal zip empty payload
    receipts_dir = invoking_cwd / "receipts"
    receipts_dir.mkdir()

    monkeypatch.chdir(invoking_cwd)

    captured_calls: list[dict[str, Any]] = []
    mock_run = _make_packaging_subprocess_runner(captured_calls=captured_calls)
    monkeypatch.setattr(subprocess, "run", mock_run)

    # 1. Test CLI main with relative wheel, work-dir, and receipt-out
    rel_wheel_arg = "artifacts/skill_lens_cli-0.1.1-py3-none-any.whl"
    rel_work_arg = "rel_work"
    rel_receipt_arg = "receipts/base_receipt.json"

    ret = smoke_wheel.main(
        [
            "--verify-base-only",
            "--wheel",
            rel_wheel_arg,
            "--work-dir",
            rel_work_arg,
            "--receipt-out",
            rel_receipt_arg,
        ]
    )
    assert ret == 0
    assert (invoking_cwd / rel_receipt_arg).exists()

    # 2. Test direct verify_base_install with relative paths
    base_res = verify_base_install(
        Path(rel_wheel_arg),
        Path("rel_work_direct"),
    )
    assert base_res["bare_exit_code"] == 0

    # 3. Test direct verify_tui_endpoint_install with relative paths
    tui_res = verify_tui_endpoint_install(
        Path(rel_wheel_arg),
        Path("rel_work_direct"),
        endpoint_name="min",
        textual_spec="textual==8.2.8",
        repo_root=REPO_ROOT,
    )
    assert tui_res["endpoint"] == "min"

    # Assert all install calls received absolute wheel paths and executed in isolated lane cwd
    install_calls = [c for c in captured_calls if any("pip" in arg for arg in c["cmd"])]
    assert len(install_calls) >= 3
    for call in install_calls:
        cwd_p = Path(call["cwd"])
        assert cwd_p.is_absolute()
        for arg in call["cmd"]:
            if "skill_lens_cli" in arg:
                wheel_p = Path(arg.split("[")[0])
                assert wheel_p.is_absolute(), (
                    f"Wheel path in subprocess call must be absolute, got: {arg}"
                )
                assert wheel_p == wheel_file.resolve()


def test_verify_base_install_invalid_provenance_fails(
    tmp_path: Path, mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """verify_base_install must raise AssertionError when skill_lens provenance is outside venv."""
    invoking_cwd = tmp_path / "invoking_cwd"
    invoking_cwd.mkdir()
    wheel_file = invoking_cwd / "skill_lens_cli-0.1.1-py3-none-any.whl"
    wheel_file.write_bytes(bytes([80, 75, 5, 6]) + bytes(18))
    monkeypatch.chdir(invoking_cwd)

    runner = _make_packaging_subprocess_runner(
        base_provenance="/system/site-packages/skill_lens/__init__.py"
    )
    monkeypatch.setattr(subprocess, "run", runner)

    with pytest.raises(AssertionError, match="Expected skill_lens inside venv"):
        verify_base_install(wheel_file, tmp_path / "work_dir")


@pytest.mark.parametrize(
    "pkg_outside,tui_outside",
    [
        (True, False),
        (False, True),
        (True, True),
    ],
)
def test_verify_tui_endpoint_install_invalid_provenance_fails(
    tmp_path: Path,
    mock_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    pkg_outside: bool,
    tui_outside: bool,
) -> None:
    """verify_tui_endpoint_install must fail when package or tui module provenance is outside venv.

    Covers BOTH origin branches of:
        if str(venv_dir) not in pkg_prov or str(venv_dir) not in tui_prov:
    """
    invoking_cwd = tmp_path / "invoking_cwd"
    invoking_cwd.mkdir()
    wheel_file = invoking_cwd / "skill_lens_cli-0.1.1-py3-none-any.whl"
    wheel_file.write_bytes(bytes([80, 75, 5, 6]) + bytes(18))
    monkeypatch.chdir(invoking_cwd)

    pkg_prov = "/system/site-packages/skill_lens/__init__.py" if pkg_outside else None
    tui_prov = "/system/site-packages/skill_lens/tui/__init__.py" if tui_outside else None

    runner = _make_packaging_subprocess_runner(
        endpoint_pkg_provenance=pkg_prov,
        endpoint_tui_provenance=tui_prov,
    )
    monkeypatch.setattr(subprocess, "run", runner)

    with pytest.raises(AssertionError, match="Expected installed wheel provenance inside"):
        verify_tui_endpoint_install(
            wheel_file,
            tmp_path / "work_dir",
            endpoint_name="min",
            textual_spec="textual==8.2.8",
            repo_root=REPO_ROOT,
        )


def test_verify_base_install_fails_when_textual_is_present(
    tmp_path: Path, mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """verify_base_install must fail when Textual is present in base environment.

    Executes the actual check_textual_cmd generated by smoke_wheel against the active
    Python environment (where Textual is installed) to prove that the subprocess check
    fails and is load-bearing. Removing the find_spec assertion turns this test red.
    """
    invoking_cwd = tmp_path / "invoking_cwd"
    invoking_cwd.mkdir()
    wheel_file = invoking_cwd / "skill_lens_cli-0.1.1-py3-none-any.whl"
    wheel_file.write_bytes(bytes([80, 75, 5, 6]) + bytes(18))
    monkeypatch.chdir(invoking_cwd)

    runner = _make_packaging_subprocess_runner(simulate_textual_in_base=True)
    monkeypatch.setattr(subprocess, "run", runner)

    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        verify_base_install(wheel_file, tmp_path / "work_dir")
    assert "Textual must be absent" in exc_info.value.stderr


@pytest.mark.parametrize(
    "line,expected",
    [
        (
            "======================== 451 passed in 84.29s (0:01:24) ========================",
            (451, 0),
        ),
        ("================ 10 passed in 0.1s ================", (10, 0)),
        ("======= 1 failed, 9 passed in 0.50s (0:00:00) =======", (9, 0)),
        ("==== 3 passed, 2 skipped, 1 warning in 1.20s ====", (3, 2)),
        ("== 1 passed, 1 skipped in 0.03s ==", (1, 1)),
    ],
)
def test_pytest_summary_parsing_reads_modern_and_legacy_lines(
    line: str, expected: tuple[int, int]
) -> None:
    """The installed-lane receipt must read pytest's real summary formats.

    pytest appends an elapsed parenthetical on current versions; the old pattern
    did not allow for it and silently receipted a 451-test lane as zero tests.
    """
    stdout = f"collected 451 items\n\n{line}\n"
    assert parse_pytest_summary(stdout) == expected
    assert line.strip("= ").strip() in pytest_summary_line(stdout)


@pytest.mark.parametrize("stdout", ["", "collected 0 items\n\nno tests ran in 0.01s\n"])
def test_pytest_summary_parsing_refuses_an_unrecognised_summary(stdout: str) -> None:
    """Negative control: an unknown shape must raise, never look like zero tests."""
    with pytest.raises(ValueError, match="could not find a pytest summary line"):
        parse_pytest_summary(stdout)


def test_installed_lane_receipt_records_positive_counts_and_duration(
    tmp_path: Path, mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A passing lane must receipt its real counts, summary line and duration."""
    invoking_cwd = tmp_path / "invoking_cwd"
    invoking_cwd.mkdir()
    wheel_file = invoking_cwd / "skill_lens_cli-0.2.0-py3-none-any.whl"
    wheel_file.write_bytes(bytes([80, 75, 5, 6]) + bytes(18))
    monkeypatch.chdir(invoking_cwd)

    summary = "======================== 451 passed in 84.29s (0:01:24) ========================"
    runner = _make_packaging_subprocess_runner(pytest_stdout=f"{summary}\n")
    monkeypatch.setattr(subprocess, "run", runner)

    result = verify_tui_endpoint_install(
        wheel_file,
        tmp_path / "work_dir",
        endpoint_name="min",
        textual_spec="textual==8.2.8",
        repo_root=REPO_ROOT,
    )

    assert result["test_count"] == 451
    assert result["skip_count"] == 0
    assert result["elapsed_seconds"] >= 0
    assert result["pytest_summary"] == "451 passed in 84.29s (0:01:24)"


def test_installed_lane_rejects_a_run_that_passed_no_tests(
    tmp_path: Path, mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A lane whose summary reports no passes cannot be accepted as green.

    ``0 passed, 3 skipped`` parses cleanly, so only the positive-count guard
    stops it from being receipted as a passing lane.
    """
    invoking_cwd = tmp_path / "invoking_cwd"
    invoking_cwd.mkdir()
    wheel_file = invoking_cwd / "skill_lens_cli-0.2.0-py3-none-any.whl"
    wheel_file.write_bytes(bytes([80, 75, 5, 6]) + bytes(18))
    monkeypatch.chdir(invoking_cwd)

    runner = _make_packaging_subprocess_runner(
        pytest_stdout="================ 0 passed, 3 skipped in 0.10s ================\n"
    )
    monkeypatch.setattr(subprocess, "run", runner)

    with pytest.raises(AssertionError, match="reported no passed tests"):
        verify_tui_endpoint_install(
            wheel_file,
            tmp_path / "work_dir",
            endpoint_name="min",
            textual_spec="textual==8.2.8",
            repo_root=REPO_ROOT,
        )


def test_installed_lane_rejects_an_unparsable_summary(
    tmp_path: Path, mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A lane whose output has no summary line must not report zero tests."""
    invoking_cwd = tmp_path / "invoking_cwd"
    invoking_cwd.mkdir()
    wheel_file = invoking_cwd / "skill_lens_cli-0.2.0-py3-none-any.whl"
    wheel_file.write_bytes(bytes([80, 75, 5, 6]) + bytes(18))
    monkeypatch.chdir(invoking_cwd)

    runner = _make_packaging_subprocess_runner(
        pytest_stdout="collected 0 items\n\nno tests ran in 0.01s\n"
    )
    monkeypatch.setattr(subprocess, "run", runner)

    with pytest.raises(ValueError, match="could not find a pytest summary line"):
        verify_tui_endpoint_install(
            wheel_file,
            tmp_path / "work_dir",
            endpoint_name="min",
            textual_spec="textual==8.2.8",
            repo_root=REPO_ROOT,
        )


def test_verify_tui_endpoint_install_fails_on_nonzero_test_suite_exit(
    tmp_path: Path, mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """verify_tui_endpoint_install must raise AssertionError on nonzero test suite returncode."""
    invoking_cwd = tmp_path / "invoking_cwd"
    invoking_cwd.mkdir()
    wheel_file = invoking_cwd / "skill_lens_cli-0.1.1-py3-none-any.whl"
    wheel_file.write_bytes(bytes([80, 75, 5, 6]) + bytes(18))
    monkeypatch.chdir(invoking_cwd)

    runner = _make_packaging_subprocess_runner(
        pytest_returncode=1,
        pytest_stdout="================ 1 failed, 9 passed in 0.1s ================\n",
        pytest_stderr="FAILED tests/test_demo.py::test_fail - AssertionError\n",
    )
    monkeypatch.setattr(subprocess, "run", runner)

    with pytest.raises(AssertionError, match="Installed test suites failed with code 1"):
        verify_tui_endpoint_install(
            wheel_file,
            tmp_path / "work_dir",
            endpoint_name="min",
            textual_spec="textual==8.2.8",
            repo_root=REPO_ROOT,
        )


@pytest.mark.parametrize("partial_output_is_bytes", [False, True])
def test_verify_tui_endpoint_install_fails_on_test_suite_timeout(
    tmp_path: Path,
    mock_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    partial_output_is_bytes: bool,
) -> None:
    """verify_tui_endpoint_install must convert a suite TimeoutExpired into an AssertionError.

    Covers the ``except subprocess.TimeoutExpired`` branch around the installed
    suite run: the error must name the timeout bound and command, preserve both
    partial output streams (decoding them when the subprocess handed over bytes),
    and chain the original timeout as ``__cause__``. Removing that handler turns
    this test red (a bare ``TimeoutExpired`` escapes instead).
    """
    invoking_cwd = tmp_path / "invoking_cwd"
    invoking_cwd.mkdir()
    wheel_file = invoking_cwd / "skill_lens_cli-0.1.1-py3-none-any.whl"
    wheel_file.write_bytes(bytes([80, 75, 5, 6]) + bytes(18))
    monkeypatch.chdir(invoking_cwd)

    runner = _make_packaging_subprocess_runner(
        pytest_timeout=True, pytest_partial_bytes=partial_output_is_bytes
    )
    monkeypatch.setattr(subprocess, "run", runner)

    with pytest.raises(AssertionError, match=r"exceeded the 42s bound") as exc_info:
        verify_tui_endpoint_install(
            wheel_file,
            tmp_path / "work_dir",
            endpoint_name="min",
            textual_spec="textual==8.2.8",
            repo_root=REPO_ROOT,
            timeout_seconds=42,
        )

    message = str(exc_info.value)
    assert "pytest" in message, f"timeout error must name the suite command: {message}"
    assert "PARTIAL SUITE STDOUT" in message
    assert "PARTIAL SUITE STDERR" in message
    assert isinstance(exc_info.value.__cause__, subprocess.TimeoutExpired)

    if partial_output_is_bytes:
        # The bytes case must go through the decode path: a raw bytes repr
        # ("b'PARTIAL SUITE STDOUT'") leaking into the message means the
        # str() fallback stood in for the actual decode.
        assert "b'PARTIAL SUITE" not in message, (
            f"bytes partial output must be decoded, not repr'd: {message}"
        )


def test_verify_tui_endpoint_install_fails_when_source_copied_into_test_lane(
    tmp_path: Path, mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """verify_tui_endpoint_install must fail when skill_lens source is present in test_lane."""
    invoking_cwd = tmp_path / "invoking_cwd"
    invoking_cwd.mkdir()
    wheel_file = invoking_cwd / "skill_lens_cli-0.1.1-py3-none-any.whl"
    wheel_file.write_bytes(bytes([80, 75, 5, 6]) + bytes(18))
    monkeypatch.chdir(invoking_cwd)

    runner = _make_packaging_subprocess_runner()
    monkeypatch.setattr(subprocess, "run", runner)

    orig_copytree = shutil.copytree

    def hostile_copytree(src: Any, dst: Any, *args: Any, **kwargs: Any) -> Any:
        res = orig_copytree(src, dst, *args, **kwargs)
        # Simulate hostile leak of skill_lens source directory into test_lane
        (Path(dst).parent / "skill_lens").mkdir(exist_ok=True)
        return res

    monkeypatch.setattr(shutil, "copytree", hostile_copytree)

    with pytest.raises(
        AssertionError, match="skill_lens source package must not be copied into test lane"
    ):
        verify_tui_endpoint_install(
            wheel_file,
            tmp_path / "work_dir",
            endpoint_name="min",
            textual_spec="textual==8.2.8",
            repo_root=REPO_ROOT,
        )
