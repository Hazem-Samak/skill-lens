"""Dedicated tests for live system-root discovery isolation (F12).

Verifies that:
1. Dedicated synthetic live-root support works without touching host /etc/codex.
2. Direct unisolated access to protected /etc/codex triggers the system-root guard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from skill_lens.core import discovery, paths


def test_synthetic_live_system_root_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When a synthetic system root is mapped, live discovery (sandbox=None) discovers it."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    paths.set_sandbox(None)

    synthetic_root = tmp_path / "custom_etc_codex_skills"
    synthetic_root.mkdir(parents=True)
    skill_dir = synthetic_root / "sys_tool"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: sys_tool\ndescription: A system tool\n---\nBody\n",
        encoding="utf-8",
    )

    orig_directories_for_root = discovery._directories_for_root

    def patched_directories_for_root(
        home: Path, cwd: Path, root: Any, boundary: Path | None
    ) -> list[tuple[Path, bool]]:
        if root.is_absolute:
            if not discovery._absolute_roots_allowed(home):
                return []
            return [(synthetic_root, False)]
        return orig_directories_for_root(home, cwd, root, boundary)

    monkeypatch.setattr(discovery, "_directories_for_root", patched_directories_for_root)

    index = discovery.discover(home=fake_home, cwd=fake_home)
    codex_entries = [
        e
        for e in index.entries
        if any(h.agent_id == "codex" and h.scope.value == "system" for h in e.hits)
    ]
    assert len(codex_entries) == 1
    assert codex_entries[0].name == "sys_tool"
    assert codex_entries[0].content_hash is not None


def test_protected_system_root_guard_prevents_unisolated_access() -> None:
    """Direct inspection of /etc/codex must fail with AssertionError."""
    with pytest.raises(AssertionError, match="Unexpected protected system-root operation"):
        _ = Path("/etc/codex/skills").exists()

    with pytest.raises(AssertionError, match="Unexpected protected system-root operation"):
        _ = Path("/private/etc/codex/skills").is_symlink()


def test_autouse_isolation_survives_test_monkeypatch_undo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proves that a test calling monkeypatch.undo() cannot remove the autouse boundary."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    paths.set_sandbox(None)

    # Test monkeypatch.undo() resets test vars, but must NOT undo isolate_system_roots
    monkeypatch.undo()

    from skill_lens.registry.loader import load_registry

    codex_agent = load_registry()["codex"]
    system_root = next(r for r in codex_agent.roots if r.is_absolute)
    effective_home = paths.home()
    dirs = discovery._directories_for_root(effective_home, effective_home, system_root, None)
    assert len(dirs) == 1
    # Points to synthetic root created by autouse fixture, NOT host /etc/codex/skills
    assert "synthetic_codex_system" in str(dirs[0][0])
