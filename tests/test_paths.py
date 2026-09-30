"""Guards for lazy, call-time path resolution (AGENTS.md rule 3)."""

from __future__ import annotations

from pathlib import Path

from skill_lens.core import paths


def test_home_follows_monkeypatched_env(mock_home: Path) -> None:
    assert paths.home() == mock_home


def test_home_reflects_later_env_change(mock_home: Path, monkeypatch, tmp_path: Path) -> None:
    """A change to HOME after import must be visible: proves no import-time freeze."""
    moved = tmp_path / "moved_home"
    moved.mkdir()
    monkeypatch.setenv("HOME", str(moved))
    assert paths.home() == moved


def test_sandbox_overrides_real_home(mock_home: Path, tmp_path: Path) -> None:
    other = tmp_path / "sandboxed"
    other.mkdir()
    paths.set_sandbox(other)
    assert paths.home() == other.resolve()
    paths.set_sandbox(None)
    assert paths.home() == mock_home


def test_xdg_config_home_defaults_under_home(mock_home: Path) -> None:
    assert paths.xdg_config_home() == mock_home / ".config"


def test_xdg_config_home_honours_env(mock_home: Path, monkeypatch, tmp_path: Path) -> None:
    custom = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(custom))
    assert paths.xdg_config_home() == custom


def test_resolve_joins_lazily(mock_home: Path) -> None:
    assert paths.resolve(".claude", "skills") == mock_home / ".claude" / "skills"


def test_display_collapses_home(mock_home: Path) -> None:
    target = mock_home / ".claude" / "skills" / "deploy"
    assert paths.display(target) == "~/.claude/skills/deploy"


def test_display_leaves_external_paths_absolute(tmp_path: Path, mock_home: Path) -> None:
    external = tmp_path / "elsewhere"
    assert paths.display(external) == str(external)


def test_no_module_level_expansion() -> None:
    """The module must expose only callables, never a pre-expanded constant."""
    for attr in dir(paths):
        value = getattr(paths, attr)
        assert not isinstance(value, Path) or attr == "_SANDBOX", (
            f"unexpected module-level Path constant: {attr}"
        )
