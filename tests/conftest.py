"""Shared pytest fixtures.

Every test runs against a mock ``$HOME`` under ``tmp_path``. The real
``~/.claude``, ``~/.agents``, ``~/.codex`` and ``/etc/codex`` are never touched
(AGENTS.md rule 2).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from skill_lens.core import paths
from tests.fixtures.scenarios import build_scenario

# Tests must be deterministic whatever shell runs them. Some environments force
# colour (CI exports FORCE_COLOR); Rich then styles parts of a message -- an
# option name renders as ``-`` + an escape code + ``-agent`` -- so a plain
# substring check for ``--agent`` fails there even though it passes on a normal
# terminal. The CLI builds its consoles at import time, so colour has to be
# settled before ``skill_lens.cli`` is imported: pytest loads this conftest
# before collecting the test modules that import it.
os.environ.pop("FORCE_COLOR", None)
os.environ["NO_COLOR"] = "1"


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add the documented in-repo switch for regenerating render snapshots.

    Snapshots are plain text, so regenerating them needs no new dependency --
    only this flag::

        pytest tests/test_render_snapshots.py --update-snapshots
    """
    parser.addoption(
        "--update-snapshots",
        action="store_true",
        default=False,
        help="Rewrite the plain-text render snapshots instead of comparing them.",
    )
    parser.addoption(
        "--update-goldens",
        action="store_true",
        default=False,
        help="Rewrite the Phase 4 JSON goldens instead of comparing them.",
    )


@pytest.fixture
def update_snapshots(request: pytest.FixtureRequest) -> bool:
    """True when ``--update-snapshots`` was passed."""
    return bool(request.config.getoption("--update-snapshots"))


@pytest.fixture
def update_goldens(request: pytest.FixtureRequest) -> bool:
    """True when ``--update-goldens`` was passed."""
    return bool(request.config.getoption("--update-goldens"))


@pytest.fixture
def mock_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A throwaway home directory wired into the environment variables.

    ``HOME`` is monkeypatched so that any *lazy* path resolution follows the
    fixture; a module that expanded ``~`` at import time would not move, which
    is exactly what the guards in ``test_paths.py`` detect.

    The sandbox is activated too, so absolute system roots (``/etc/codex/skills``)
    are never read during a test even on a machine that really has them.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    paths.set_sandbox(home)
    try:
        yield home
    finally:
        paths.set_sandbox(None)


@pytest.fixture
def bare_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A mock home with ``HOME`` patched but the explicit sandbox left *off*.

    Used by the tests that verify lazy path resolution still follows ``HOME``
    without the sandbox override.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    paths.set_sandbox(None)
    try:
        yield home
    finally:
        paths.set_sandbox(None)


@pytest.fixture
def sandbox(mock_home: Path) -> Iterator[Path]:
    """``mock_home`` with the explicit ``--sandbox`` override activated."""
    paths.set_sandbox(mock_home)
    try:
        yield mock_home
    finally:
        paths.set_sandbox(None)


@pytest.fixture
def scenario_factory():
    """Return a factory that builds a named scenario into a home dir."""

    def _build(name: str, home: Path) -> Path:
        build_scenario(name, home)
        return home

    yield _build
