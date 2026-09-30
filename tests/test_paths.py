"""Guards for lazy, call-time path resolution (AGENTS.md rule 3)."""

from __future__ import annotations

from pathlib import Path

from skill_lens.core import paths


def test_home_follows_monkeypatched_env(bare_home: Path) -> None:
    assert paths.home() == bare_home


def test_home_reflects_later_env_change(bare_home: Path, monkeypatch, tmp_path: Path) -> None:
    """A change to HOME after import must be visible: proves no import-time freeze."""
    moved = tmp_path / "moved_home"
    moved.mkdir()
    monkeypatch.setenv("HOME", str(moved))
    assert paths.home() == moved


def test_sandbox_overrides_real_home(bare_home: Path, tmp_path: Path) -> None:
    other = tmp_path / "sandboxed"
    other.mkdir()
    paths.set_sandbox(other)
    assert paths.home() == other.resolve()
    paths.set_sandbox(None)
    assert paths.home() == bare_home


def test_mock_home_activates_sandbox(mock_home: Path) -> None:
    """The standard fixture must also block absolute system roots."""
    assert paths.get_sandbox() == mock_home


def test_xdg_config_home_honours_env(bare_home: Path, monkeypatch, tmp_path: Path) -> None:
    custom = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(custom))
    assert paths.xdg_config_home() == custom


def test_terminal_cwd_defaults_to_the_process_folder(bare_home: Path) -> None:
    """F-09: the natural default is where the user is standing, not ``$HOME``."""
    assert paths.terminal_cwd() == Path.cwd()


def test_terminal_cwd_is_the_sandbox_under_sandbox(mock_home: Path) -> None:
    """A sandboxed run must never fall back to the real terminal folder.

    ``$HOME`` is rarely inside a repository, so defaulting there silently
    skipped every project root -- but defaulting to the real terminal folder
    would let a sandboxed run read the real filesystem. Under a sandbox the
    sandbox root wins.
    """
    assert paths.terminal_cwd() == mock_home.resolve()


def test_resolve_joins_lazily(bare_home: Path) -> None:
    assert paths.resolve(".claude", "skills") == bare_home / ".claude" / "skills"


def test_display_collapses_home(bare_home: Path) -> None:
    target = bare_home / ".claude" / "skills" / "deploy"
    assert paths.display(target) == "~/.claude/skills/deploy"


def test_display_leaves_external_paths_absolute(tmp_path: Path, bare_home: Path) -> None:
    external = tmp_path / "elsewhere"
    assert paths.display(external) == str(external)


def test_display_collapses_a_symlinked_home(tmp_path: Path, monkeypatch) -> None:
    """A home behind a symlink must still render as ``~``.

    ``canonicalize()`` returns resolved paths while entrypoints keep the path as
    written, so on a machine whose home is reached through a symlink (macOS
    ``/tmp`` -> ``/private/tmp``) only the resolved form can be collapsed.

    ``HOME`` is pointed at the symlink and the sandbox is left **off**,
    because ``set_sandbox`` resolves its argument: with a sandbox active both
    forms collapse to the same path and the test cannot tell the two branches
    apart. No filesystem scan runs here, so nothing outside ``tmp_path`` is
    ever read (AGENTS.md rule 2).
    """
    real = tmp_path / "real_home"
    (real / ".claude" / "skills").mkdir(parents=True)
    link = tmp_path / "link_home"
    link.symlink_to(real, target_is_directory=True)
    monkeypatch.setenv("HOME", str(link))
    paths.set_sandbox(None)
    # Both the as-written and the fully resolved spelling must collapse.
    assert paths.display(link / ".claude" / "skills" / "deploy") == "~/.claude/skills/deploy"
    assert paths.display(real / ".claude" / "skills" / "deploy") == "~/.claude/skills/deploy"
    # And with a sandbox (which resolves its own argument), a path still
    # written through the symlink must collapse too.
    paths.set_sandbox(real)
    assert paths.display(link / ".claude" / "skills" / "deploy") == "~/.claude/skills/deploy"
    paths.set_sandbox(None)


def test_same_location_sees_through_symlinked_parents(tmp_path: Path) -> None:
    """An entrypoint and its canonical target are one file, not two."""
    real = tmp_path / "real"
    real.mkdir()
    (real / "skill").mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    assert paths.same_location(link / "skill", real / "skill")
    assert not paths.same_location(real / "skill", real / "other")


def test_no_module_level_expansion() -> None:
    """The module must expose only callables, never a pre-expanded constant."""
    for attr in dir(paths):
        value = getattr(paths, attr)
        assert not isinstance(value, Path) or attr == "_SANDBOX", (
            f"unexpected module-level Path constant: {attr}"
        )
