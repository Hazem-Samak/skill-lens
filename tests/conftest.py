"""Shared pytest fixtures.

Every test runs against a mock ``$HOME`` under ``tmp_path``. The real
``~/.claude``, ``~/.agents``, ``~/.codex`` and ``/etc/codex`` are never touched
(AGENTS.md rule 2).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from skill_lens.core import paths
from tests.fixtures.scenarios import build_scenario

_PROTECTED_ROOTS = ("/etc/codex", "/private/etc/codex")


def _is_protected_target(p: Any) -> bool:
    try:
        s = os.fspath(p)
        if isinstance(s, bytes):
            s = s.decode("utf-8", "surrogateescape")
        return any(s == root or s.startswith(root + "/") for root in _PROTECTED_ROOTS)
    except Exception:
        return False


_PATH_ORIGINALS: dict[str, Any] = {}
_OS_ORIGINALS: dict[str, Any] = {}
_OS_PATH_ORIGINALS: dict[str, Any] = {}


def _install_system_root_guard() -> None:
    if _PATH_ORIGINALS:
        return

    path_methods = (
        "exists",
        "is_symlink",
        "is_dir",
        "is_file",
        "open",
        "iterdir",
        "read_bytes",
        "read_text",
        "stat",
        "lstat",
    )
    for name in path_methods:
        orig = getattr(Path, name)
        _PATH_ORIGINALS[name] = orig

        def make_guarded(fn_name: str, original_fn: Any):
            def guarded(self: Path, *args: Any, **kwargs: Any) -> Any:
                if _is_protected_target(self):
                    raise AssertionError(
                        f"Unexpected protected system-root operation: Path.{fn_name} {self}"
                    )
                return original_fn(self, *args, **kwargs)

            return guarded

        setattr(Path, name, make_guarded(name, orig))

    os_funcs = ("stat", "lstat", "scandir", "listdir")
    for name in os_funcs:
        if hasattr(os, name):
            orig = getattr(os, name)
            _OS_ORIGINALS[name] = orig

            def make_os_guarded(fn_name: str, original_fn: Any):
                def guarded(path: Any, *args: Any, **kwargs: Any) -> Any:
                    if _is_protected_target(path):
                        raise AssertionError(
                            f"Unexpected protected system-root operation: os.{fn_name} {path}"
                        )
                    return original_fn(path, *args, **kwargs)

                return guarded

            setattr(os, name, make_os_guarded(name, orig))

    os_path_funcs = ("exists", "isdir", "isfile", "islink")
    for name in os_path_funcs:
        if hasattr(os.path, name):
            orig = getattr(os.path, name)
            _OS_PATH_ORIGINALS[name] = orig

            def make_os_path_guarded(fn_name: str, original_fn: Any):
                def guarded(path: Any, *args: Any, **kwargs: Any) -> Any:
                    if _is_protected_target(path):
                        raise AssertionError(
                            f"Unexpected protected system-root operation: os.path.{fn_name} {path}"
                        )
                    return original_fn(path, *args, **kwargs)

                return guarded

            setattr(os.path, name, make_os_path_guarded(name, orig))


def _uninstall_system_root_guard() -> None:
    for name, orig in _PATH_ORIGINALS.items():
        setattr(Path, name, orig)
    _PATH_ORIGINALS.clear()

    for name, orig in _OS_ORIGINALS.items():
        setattr(os, name, orig)
    _OS_ORIGINALS.clear()

    for name, orig in _OS_PATH_ORIGINALS.items():
        setattr(os.path, name, orig)
    _OS_PATH_ORIGINALS.clear()


def pytest_configure(config: pytest.Config) -> None:
    _install_system_root_guard()


def pytest_unconfigure(config: pytest.Config) -> None:
    _uninstall_system_root_guard()


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


@pytest.fixture(autouse=True)
def isolate_system_roots(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Isolate protected system root lookup in every test by default."""
    from skill_lens.core import discovery

    synthetic_root = tmp_path_factory.mktemp("synthetic_codex_system") / "skills"
    orig_directories_for_root = discovery._directories_for_root

    def patched_directories_for_root(
        home: Path, cwd: Path, root: Any, boundary: Path | None
    ) -> list[tuple[Path, bool]]:
        if root.is_absolute:
            if not discovery._absolute_roots_allowed(home):
                return []
            return [(synthetic_root, False)]
        return orig_directories_for_root(home, cwd, root, boundary)

    mp = pytest.MonkeyPatch()
    mp.setattr(discovery, "_directories_for_root", patched_directories_for_root)
    try:
        yield
    finally:
        mp.undo()


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
