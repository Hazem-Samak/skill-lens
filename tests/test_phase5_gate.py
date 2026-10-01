"""Phase 5 gate: the package would ship complete and self-consistent.

The specification's Phase 5 gate is "``ruff check .`` clean, 100% green
``pytest``" plus a verified ``pip install .`` and ``uvx --from .`` run. The
install runs live in ``PHASE5_WALKTHROUGH.md`` and in the CI ``packaging`` job,
where building a wheel is expected anyway.

This module deliberately does **not** build a wheel: that is slow and
environment-sensitive, and duplicating it here would buy nothing. What it does
instead is pin the *declarations* that determine what the wheel contains, so the
failure mode this project cares most about -- the agent registry silently
dropping out of the distribution -- is caught by ``pytest`` in under a second,
on a developer's machine, without a build step.

Every assertion here is a drift guard: it compares two sources of truth that can
get out of step (``pyproject.toml`` vs the package, CI vs declared support, the
loader vs the data directory) and fails loudly when they do.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import yaml

import skill_lens
from skill_lens.registry import REGISTRY_DIR

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

# Kept in step with the ``packaging`` job in .github/workflows/ci.yml, which
# asserts the built wheel carries exactly this many registry files. If an agent
# is added or removed, both places must change together and this fails first.
EXPECTED_AGENT_COUNT = 10


def _pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def _ci_workflow() -> dict:
    return yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))


# --- version hygiene -------------------------------------------------------


def test_version_is_in_sync_between_pyproject_and_package() -> None:
    """The declared distribution version must equal the importable one.

    A release with two different version strings publishes an artifact whose
    ``skill-lens --version`` disagrees with its own filename. This assertion
    removes the manual "keep them in sync" step the release notes asked for.
    """
    declared = _pyproject()["project"]["version"]
    assert declared == skill_lens.__version__, (
        f"pyproject.toml declares {declared!r} but skill_lens.__version__ is "
        f"{skill_lens.__version__!r}; bump both together"
    )


def test_changelog_documents_the_current_version() -> None:
    """Every shipped version must appear in the changelog under a released heading.

    Not a released heading: ``[Unreleased]`` deliberately does not satisfy this,
    because a version that is about to be published is not documented yet.
    """
    assert CHANGELOG.exists(), "CHANGELOG.md is missing"
    text = CHANGELOG.read_text(encoding="utf-8")
    version = skill_lens.__version__
    assert f"## [{version}]" in text, f"CHANGELOG.md has no released section for {version}"


# --- the console script ----------------------------------------------------


def test_console_script_is_declared_and_importable() -> None:
    """``skill-lens`` must map to a real attribute, or the entrypoint is a lie."""
    scripts = _pyproject()["project"].get("scripts", {})
    assert scripts.get("skill-lens") == "skill_lens.cli:app", (
        "the installed `skill-lens` command must point at skill_lens.cli:app; "
        f"found {scripts.get('skill-lens')!r}"
    )
    # Resolve the dotted target for real, so a renamed module fails here rather
    # than in a user's terminal.
    from skill_lens.cli import app  # noqa: PLC0415

    assert callable(app)


def test_every_spec_command_is_wired() -> None:
    """The six commands the spec and README promise must all be registered."""
    from skill_lens.cli import app  # noqa: PLC0415

    # ``CommandInfo.name`` is still None at registration time; Typer derives the
    # command name from the callback when it builds the Click command, so the
    # callback is the only reliable source here.
    registered = {info.callback.__name__ for info in app.registered_commands}
    expected = {"scan", "why", "agents", "diff", "doctor", "compare"}
    assert expected <= registered, f"missing CLI commands: {sorted(expected - registered)}"


# --- what the wheel will contain ------------------------------------------


def test_build_backend_and_wheel_target_cover_the_package() -> None:
    """hatchling ships every file under the declared package dir.

    That is the mechanism that carries ``registry/agents/*.toml`` into the
    wheel, so the declaration itself is the thing worth pinning.
    """
    build = _pyproject()["build-system"]
    assert build["build-backend"] == "hatchling.build"
    packages = _pyproject()["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    assert packages == ["skill_lens"], (
        "hatchling includes non-.py files only inside the declared package dir; "
        f"an empty or narrowed list would drop the registry. Found {packages!r}"
    )


def test_registry_directory_resolves_inside_the_package() -> None:
    """The loader must find its data relative to the installed package.

    If this ever became relative to the current working directory, every
    installed user would get an empty registry that only appears to work when
    run from a source checkout.
    """
    package_dir = Path(skill_lens.__file__).resolve().parent
    assert package_dir / "registry" / "agents" == REGISTRY_DIR
    assert REGISTRY_DIR.is_dir(), f"registry directory is missing: {REGISTRY_DIR}"


def test_every_registered_agent_file_is_present_and_parses() -> None:
    """One TOML per agent, and the loader must be able to read all of them."""
    from skill_lens.registry.loader import load_registry  # noqa: PLC0415

    files = sorted(REGISTRY_DIR.glob("*.toml"))
    assert len(files) == EXPECTED_AGENT_COUNT, (
        f"expected {EXPECTED_AGENT_COUNT} agent definitions, found {len(files)}; "
        f"update EXPECTED_AGENT_COUNT and the CI packaging job together: "
        f"{[f.name for f in files]}"
    )
    # load_registry is the same call `skill-lens agents` makes, so a malformed
    # file fails the gate instead of the user's terminal.
    registry = load_registry()
    assert len(registry) == EXPECTED_AGENT_COUNT


# --- declared support vs tested support ------------------------------------


def test_ci_matrix_stays_inside_requires_python() -> None:
    """Every Python version CI tests must be a version the package claims to support.

    Without this, adding a version to the CI matrix but forgetting
    ``requires-python`` would let an untested interpreter install the package.
    """
    requires = _pyproject()["project"]["requires-python"]
    minimum = tuple(int(part) for part in requires.removeprefix(">=").split("."))

    matrix = _ci_workflow()["jobs"]["test"]["strategy"]["matrix"]["python-version"]
    for raw in matrix:
        version = tuple(int(part) for part in str(raw).split("."))
        assert version >= minimum, (
            f"CI tests Python {raw} but pyproject.toml only claims >="
            f"{'.'.join(str(p) for p in minimum)}"
        )


def test_ci_matrix_covers_both_claimed_platforms() -> None:
    """The spec declares macOS and Linux; CI must actually run both."""
    matrix = _ci_workflow()["jobs"]["test"]["strategy"]["matrix"]
    systems = {str(entry) for entry in matrix["os"]}
    assert {"ubuntu-latest", "macos-latest"} <= systems, (
        f"CI must cover macOS and Linux; found {sorted(systems)}"
    )


def test_ci_is_not_allowed_to_publish() -> None:
    """A green CI run must never upload to PyPI.

    Publishing is irreversible and needs the owner's credentials, so it stays a
    deliberate human action. This makes that a tested property rather than a
    comment in a walkthrough.
    """
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    for forbidden in ("uv publish", "twine upload", "pypi-server", "PYPI_TOKEN"):
        assert forbidden not in text, f"CI must not contain {forbidden!r}; publishing is manual"
    assert _ci_workflow()["permissions"] == {"contents": "read"}, (
        "CI should keep read-only repository permissions"
    )


# --- the PEP 561 promise ---------------------------------------------------


def test_typed_marker_ships_under_the_declared_package() -> None:
    """The ``Typing :: Typed`` classifier is only honest if ``py.typed`` ships.

    A missing marker file does not break anything at runtime, it just silently
    makes every type hint in the package decorative.
    """
    package_dir = Path(skill_lens.__file__).resolve().parent
    assert (package_dir / "py.typed").is_file(), "py.typed must live inside skill_lens/"
    assert "Typing :: Typed" in _pyproject()["project"]["classifiers"]


# --- verification gates: type check and coverage ---------------------------


def test_dev_extras_declare_the_verification_tools() -> None:
    """A tool CI cannot install is a gate that silently does not exist.

    CI installs with ``uv sync --locked --extra dev``, so the type checker and
    the coverage plugin have to live in the ``dev`` extra to be runnable at all.
    """
    dev = _pyproject()["project"]["optional-dependencies"]["dev"]
    joined = " ".join(dev)
    for tool in ("mypy", "pytest-cov", "types-PyYAML"):
        assert tool in joined, f"{tool} must be a dev dependency; found {dev!r}"


def test_mypy_is_configured_strict_over_the_package() -> None:
    """``py.typed`` promises types; strict mypy is what makes the promise checked."""
    mypy = _pyproject()["tool"]["mypy"]
    assert mypy["strict"] is True, "mypy must run in strict mode to mean anything"
    assert mypy["files"] == ["skill_lens"], (
        f"mypy must check the shipped package, not the whole repo; found {mypy.get('files')!r}"
    )


def test_coverage_threshold_is_declared_and_meaningful() -> None:
    """An unenforced coverage number erodes silently on the next refactor."""
    coverage = _pyproject()["tool"]["coverage"]
    assert coverage["run"]["source"] == ["skill_lens"], "coverage must measure the shipped package"
    assert coverage["report"]["fail_under"] >= 85, (
        f"a threshold of {coverage['report'].get('fail_under')!r} is too low to gate anything"
    )


def test_ci_enforces_the_type_check_and_the_coverage_gate() -> None:
    """Declaring a gate in ``pyproject.toml`` is not running it.

    The coverage threshold itself lives in ``[tool.coverage.report]`` so there is
    exactly one source of truth; CI only has to invoke pytest under ``--cov``.
    """
    steps = _ci_workflow()["jobs"]["test"]["steps"]
    runs = " ".join(str(step.get("run", "")) for step in steps)
    assert "mypy" in runs, "CI must run the type checker"
    assert "--cov" in runs, "CI must run pytest under coverage"


def test_license_is_declared_once_as_an_spdx_expression() -> None:
    """PEP 639: the SPDX expression is authoritative; the legacy classifier is not.

    Shipping both leaves the metadata self-contradictory in the eyes of current
    tooling, which is why the ``License ::`` classifier is deprecated next to a
    ``license`` expression.
    """
    project = _pyproject()["project"]
    assert project["license"] == "MIT"
    legacy = [c for c in project["classifiers"] if c.startswith("License ::")]
    assert not legacy, f"drop the legacy license classifier(s) {legacy!r}; use the SPDX expression"
