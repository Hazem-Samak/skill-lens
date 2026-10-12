"""Acceptance tests for session capture and browsing services (Assignment C3).

Specification reference: FULL_SCREEN_TUI.md §21.2, §21.4, §21.6, and §22.
"""

from __future__ import annotations

import builtins
import datetime
import io
import os
import shutil
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest

from skill_lens.core import paths
from skill_lens.core.cancellation import CaptureCancelled
from skill_lens.core.compare import run_compare
from skill_lens.core.diff import build_diff_report
from skill_lens.core.discovery import (
    CanonicalResult,
    CanonicalStatus,
    DiscoveryIndex,
    RootHit,
    UnreadableRoot,
    canonical_key,
)
from skill_lens.core.doctor import run_doctor
from skill_lens.core.hasher import hash_bytes, iter_files
from skill_lens.core.parser import ParseResult
from skill_lens.core.resolver import (
    lookup_name_for_entry,
    resolve_skill,
)
from skill_lens.core.scanner import build_scan_report
from skill_lens.core.snapshot import (
    SnapshotChanged,
    _read_input_guarded,
    capture_session,
    entry_for_path,
    snapshot_compare,
    snapshot_diff,
    snapshot_path,
    snapshot_same_location,
    snapshot_why,
)
from skill_lens.core.snapshot_models import CapturedFile, CapturedInput
from skill_lens.core.system import installer_lockfile, live_discovery, shared_library
from skill_lens.models import dumps
from skill_lens.models.enums import HeadlineState, Visibility
from skill_lens.registry.loader import list_agents, load_registry
from tests.fixtures.builders import make_skill, symlink, write_skill

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _setup_rich_fixture(home: Path, project: Path) -> dict[str, Any]:
    """Create a rich, realistic filesystem state with skills, configs, and lock."""
    # Ensure project has .git boundary so project roots apply
    (project / ".git").mkdir(parents=True, exist_ok=True)

    # 1. Installer lockfile
    lock_path = home / ".agents" / ".skill-lock.json"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text('{"skills": {"deploy": "1.0", "shared": "2.0"}}', encoding="utf-8")

    # 2. Agent settings with disabled override using actual registry key
    claude_settings = home / ".claude" / "settings.json"
    claude_settings.parent.mkdir(parents=True, exist_ok=True)
    claude_settings.write_text('{"skillOverrides": {"disabled_copy": false}}', encoding="utf-8")

    # 3. Project skill with large binary asset (> 1 MiB) and nested text asset
    large_skill_dir = project / ".claude" / "skills" / "large_asset_skill"
    large_skill_dir.mkdir(parents=True, exist_ok=True)
    write_skill(
        large_skill_dir,
        "---\nname: large_asset_skill\ndescription: Skill with assets.\n---\n# Large Asset Body\n",
    )
    # Binary asset exceeding 1 MiB
    large_bin_content = b"\x00\xff\xfe\x01" + (b"BINARY_CHUNK_" * (100 * 1024))
    (large_skill_dir / "assets").mkdir(parents=True, exist_ok=True)
    (large_skill_dir / "assets" / "large.bin").write_bytes(large_bin_content)
    (large_skill_dir / "assets" / "nested.txt").write_text("nested text file\n", encoding="utf-8")

    # 4. Global shared library skill and symlink entrypoints (Variant A and Variant B)
    shared_lib_dir = home / ".agents" / "skills" / "shared"
    make_skill(shared_lib_dir, "shared", "Shared library skill.", body="# Shared Library Body\n")
    (shared_lib_dir / "assets").mkdir(parents=True, exist_ok=True)
    (shared_lib_dir / "assets" / "shared_nested.txt").write_text(
        "global shared nested asset\n", encoding="utf-8"
    )
    (shared_lib_dir / "assets" / "shared.bin").write_bytes(b"\x01\x02\x03\x04")

    # Symlinks from claude and pi
    claude_shared = home / ".claude" / "skills" / "shared"
    symlink(shared_lib_dir, claude_shared)
    pi_shared = home / ".pi" / "agent" / "skills" / "shared"
    symlink(shared_lib_dir, pi_shared)

    # Project override for shared skill (different body -> variant) with differing assets
    project_shared = project / ".claude" / "skills" / "shared"
    make_skill(
        project_shared, "shared", "Project shared variant.", body="# Project Override Body\n"
    )
    (project_shared / "assets").mkdir(parents=True, exist_ok=True)
    (project_shared / "assets" / "shared_nested.txt").write_text(
        "project override nested asset differing\n", encoding="utf-8"
    )
    (project_shared / "assets" / "shared.bin").write_bytes(b"\x05\x06\x07\x08")

    # 5. Standalone .md skill
    standalone_dir = home / ".codex" / "skills"
    standalone_dir.mkdir(parents=True, exist_ok=True)
    standalone_file = standalone_dir / "standalone.md"
    standalone_file.write_text(
        "---\nname: standalone\ndescription: Standalone file skill.\n---\n# Standalone\n",
        encoding="utf-8",
    )

    # 6. Differing folder name vs frontmatter name with nested metadata
    diff_name_dir = home / ".claude" / "skills" / "folder_name"
    write_skill(
        diff_name_dir,
        "---\n"
        "name: frontmatter_name\n"
        "description: Differing frontmatter name.\n"
        "released: 2024-01-01\n"
        "metadata:\n"
        "  nested_key: original_value\n"
        "  nested_list: [1, 2]\n"
        "---\n"
        "# Differing Body\n",
    )

    # 7. Lowercase document skill.md
    lowercase_dir = home / ".claude" / "skills" / "lowercase_skill"
    write_skill(
        lowercase_dir,
        "---\nname: lowercase_skill\ndescription: Lowercase doc.\n---\n# Lowercase\n",
        filename="skill.md",
    )
    (lowercase_dir / "extra.txt").write_text("extra file\n", encoding="utf-8")

    # 8. Malformed frontmatter skill
    malformed_dir = home / ".claude" / "skills" / "malformed_skill"
    write_skill(
        malformed_dir,
        "---\nname: malformed\ndescription: [unclosed yaml list\n---\n",
    )

    # 9. Disabled skill matching settings
    disabled_dir = home / ".claude" / "skills" / "disabled_copy"
    make_skill(disabled_dir, "disabled_copy", "Disabled by override.")

    # 10. Standalone file outside roots reached by suffixless symlink (parse is None)
    vault_dir = home / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    opaque_target = vault_dir / "opaque_standalone"
    opaque_target.write_bytes(b"initial opaque standalone bytes\n")
    opaque_link = home / ".claude" / "skills" / "opaque_link"
    opaque_link.symlink_to(opaque_target)

    return {
        "large_bin_content": large_bin_content,
        "lock_path": lock_path,
        "claude_settings": claude_settings,
        "shared_lib_dir": shared_lib_dir,
        "project_shared": project_shared,
        "claude_shared": claude_shared,
        "pi_shared": pi_shared,
        "standalone_file": standalone_file,
        "diff_name_dir": diff_name_dir,
        "lowercase_dir": lowercase_dir,
        "malformed_dir": malformed_dir,
        "disabled_dir": disabled_dir,
        "large_skill_dir": large_skill_dir,
        "opaque_target": opaque_target,
        "opaque_link": opaque_link,
    }


# ---------------------------------------------------------------------------
# 1. Snapshot reports match live reports (§21.6)
# ---------------------------------------------------------------------------


def test_snapshot_reports_match_live_reports(mock_home: Path) -> None:
    """Compare snapshot reports and captured files against independent live builders."""
    home = paths.home()
    project = home / "project"
    project.mkdir(parents=True, exist_ok=True)

    fixtures = _setup_rich_fixture(home, project)
    registry = load_registry()

    # Build live expectations before capture
    live_idx = live_discovery(cwd=project, registry=registry)
    norm_home = Path(live_idx.home)
    norm_cwd = Path(live_idx.cwd)

    # Independently collect expected files for each entry BEFORE capture
    expected_files: dict[str, list[CapturedFile]] = {}
    for entry in live_idx.entries:
        key = canonical_key(entry)
        if entry.content_hash is None:
            expected_files[key] = []
            continue
        root = Path(entry.canonical_path or entry.entrypoint_path)
        if root.is_dir():
            rel_paths = iter_files(root)
            items: list[CapturedFile] = []
            for rel in rel_paths:
                file_p = root / rel
                data = file_p.read_bytes()
                fp = hash_bytes(data)
                items.append(CapturedFile(relative_path=rel.as_posix(), data=data, fingerprint=fp))
            expected_files[key] = items
        else:
            data = root.read_bytes()
            fp = hash_bytes(data)
            expected_files[key] = [CapturedFile(relative_path=root.name, data=data, fingerprint=fp)]

    # Independently collect expected display paths
    expected_path_set: set[str] = {
        str(norm_home),
        str(norm_cwd),
        str(shared_library(norm_home)),
        str(installer_lockfile(norm_home)),
    }
    for agent in registry.values():
        if agent.disabled_settings:
            expected_path_set.add(str(norm_home / agent.disabled_settings))
    for ur in live_idx.unreadable_roots:
        expected_path_set.add(str(ur.path))
    for entry in live_idx.entries:
        expected_path_set.add(str(entry.entrypoint_path))
        if entry.canonical_path:
            expected_path_set.add(str(entry.canonical_path))
        for ep in entry.entrypoint_paths:
            expected_path_set.add(str(ep))
        for hit in entry.hits:
            expected_path_set.add(str(hit.entrypoint_path))
    expected_display_paths = {p: paths.display(p) for p in expected_path_set}

    live_scan = build_scan_report(norm_home, norm_cwd, live_idx, registry)
    live_doc = run_doctor(norm_cwd, index=live_idx, registry=registry)

    # Capture session
    snapshot = capture_session(generation=1, home=norm_home, cwd=norm_cwd)

    assert snapshot.generation == 1
    assert snapshot.home == norm_home
    assert snapshot.cwd == norm_cwd

    # 1. DIRECT file retention, bytes, and fingerprint assertions BEFORE report checks
    assert set(snapshot.files.keys()) == set(expected_files.keys())
    for key, exp_list in expected_files.items():
        act_tuple = snapshot.files[key]
        assert len(act_tuple) == len(exp_list)
        assert [cf.relative_path for cf in act_tuple] == [cf.relative_path for cf in exp_list]
        assert [cf.data for cf in act_tuple] == [cf.data for cf in exp_list]
        assert [cf.fingerprint for cf in act_tuple] == [cf.fingerprint for cf in exp_list]
        if exp_list:
            assert all(len(cf.data) > 0 for cf in act_tuple)

    # Specifically assert nested assets, binary assets, and single-copy large asset
    large_entry = next(
        e for e in snapshot.index.entries if "large_asset_skill" in e.entrypoint_path
    )
    large_cfs = {cf.relative_path: cf for cf in snapshot.files[canonical_key(large_entry)]}
    assert "assets/nested.txt" in large_cfs
    assert large_cfs["assets/nested.txt"].data == b"nested text file\n"
    assert "assets/large.bin" in large_cfs
    assert len(large_cfs["assets/large.bin"].data) > 1024 * 1024
    assert large_cfs["assets/large.bin"].data == fixtures["large_bin_content"]

    # Differing copies in Diff: shared library vs project override
    shared_entries = [e for e in snapshot.index.entries if e.name == "shared"]
    assert len(shared_entries) >= 2
    for se in shared_entries:
        s_cfs = {cf.relative_path: cf for cf in snapshot.files[canonical_key(se)]}
        assert "assets/shared_nested.txt" in s_cfs
        assert "assets/shared.bin" in s_cfs
        assert len(s_cfs["assets/shared.bin"].data) > 0

    # Standalone document file retention
    standalone_entry = next(e for e in snapshot.index.entries if "standalone" in e.entrypoint_path)
    st_cfs = snapshot.files[canonical_key(standalone_entry)]
    assert len(st_cfs) == 1
    assert st_cfs[0].relative_path == "standalone.md"
    assert st_cfs[0].data == (home / ".codex" / "skills" / "standalone.md").read_bytes()

    # 2. Config inputs and disabled overrides assertions
    assert set(snapshot.disabled_overrides.keys()) == {a.id for a in snapshot.registry}
    assert snapshot.disabled_overrides["claude"] == frozenset({"disabled_copy"})
    assert snapshot.disabled_overrides["codex"] == frozenset()
    assert snapshot.disabled_overrides["pi"] == frozenset()
    for a in snapshot.registry:
        assert isinstance(snapshot.disabled_overrides[a.id], frozenset)

    expected_lock_bytes = fixtures["lock_path"].read_bytes()
    expected_claude_bytes = fixtures["claude_settings"].read_bytes()
    assert snapshot.config_inputs[str(fixtures["lock_path"])].data == expected_lock_bytes
    assert snapshot.config_inputs[str(fixtures["lock_path"])].error is None
    assert snapshot.config_inputs[str(fixtures["claude_settings"])].data == expected_claude_bytes
    assert snapshot.config_inputs[str(fixtures["claude_settings"])].error is None

    expected_config_keys = {str(fixtures["lock_path"])} | {
        str(norm_home / a.disabled_settings) for a in snapshot.registry if a.disabled_settings
    }
    assert set(snapshot.config_inputs.keys()) == expected_config_keys
    for _p_str, ci in snapshot.config_inputs.items():
        if ci.data is not None:
            assert ci.error is None
        else:
            assert ci.error in ("missing", "unreadable")

    # 3. Complete display paths map
    assert dict(snapshot.display_paths) == expected_display_paths

    # 4. Symmetrical same locations pairs for symlinks
    claude_link = str(fixtures["claude_shared"])
    shared_canon = str(fixtures["shared_lib_dir"])
    assert claude_link != shared_canon
    assert (claude_link, shared_canon) in snapshot.same_locations
    assert (shared_canon, claude_link) in snapshot.same_locations
    assert snapshot_same_location(snapshot, claude_link, shared_canon) is True
    assert snapshot_same_location(snapshot, shared_canon, claude_link) is True

    pi_link = str(fixtures["pi_shared"])
    assert (pi_link, shared_canon) in snapshot.same_locations
    assert (shared_canon, pi_link) in snapshot.same_locations
    assert snapshot_same_location(snapshot, pi_link, shared_canon) is True
    assert snapshot_same_location(snapshot, shared_canon, pi_link) is True

    # 5. Disabled skill resolution assertion
    disabled_entry = next(e for e in snapshot.index.entries if e.name == "disabled_copy")
    dis_why = snapshot_why(snapshot, canonical_key(disabled_entry), "claude")
    assert dis_why.headline == HeadlineState.DISABLED
    assert len(dis_why.candidates) >= 1
    assert dis_why.candidates[0].state == HeadlineState.DISABLED
    assert dis_why.candidates[0].visibility == Visibility.DISABLED
    assert dis_why.candidates[0].rule_id == "claude_skill_override_disabled"

    # Test omission of captured overrides leaves candidate active
    non_disabled_why = resolve_skill(
        "disabled_copy",
        "claude",
        norm_cwd,
        norm_home,
        index=live_idx,
        registry=registry,
        disabled_overrides=frozenset(),
    )
    assert non_disabled_why.headline != HeadlineState.DISABLED

    # 6. Report parity against live engines
    assert snapshot.scan.to_dict() == live_scan.to_dict()
    assert dumps(snapshot.scan.to_dict()) == dumps(live_scan.to_dict())

    assert snapshot.doctor.to_dict() == live_doc.to_dict()
    assert dumps(snapshot.doctor.to_dict()) == dumps(live_doc.to_dict())

    for entry in snapshot.index.entries:
        key = canonical_key(entry)
        for agent_id, agent in registry.items():
            snap_why = snapshot_why(snapshot, key, agent_id)
            lookup_name = lookup_name_for_entry(entry, agent)
            live_why = resolve_skill(
                lookup_name,
                agent_id,
                norm_cwd,
                norm_home,
                index=live_idx,
                registry=registry,
                disabled_overrides=snapshot.disabled_overrides.get(agent_id, frozenset()),
            )
            assert snap_why.to_dict() == live_why.to_dict()
            assert dumps(snap_why.to_dict()) == dumps(live_why.to_dict())

    for entry in snapshot.index.entries:
        key = canonical_key(entry)
        snap_diff = snapshot_diff(snapshot, key)
        live_diff = build_diff_report(
            entry.name,
            norm_cwd,
            norm_home,
            index=live_idx,
            registry=registry,
            captured_files=snapshot.files,
        )
        assert snap_diff.to_dict() == live_diff.to_dict()
        assert dumps(snap_diff.to_dict()) == dumps(live_diff.to_dict())

    agent_ids = sorted(registry.keys())
    for i, a1 in enumerate(agent_ids):
        for a2 in agent_ids[i + 1 :]:
            snap_comp = snapshot_compare(snapshot, a1, a2)
            live_comp = run_compare(a1, a2, cwd=norm_cwd)
            assert snap_comp.to_dict() == live_comp.to_dict()
            assert dumps(snap_comp.to_dict()) == dumps(live_comp.to_dict())

    expected_agents_payload = [
        {
            "id": agent.id,
            "name": agent.name,
            "collision_policy": agent.collision_policy,
            "policy_evidence": agent.policy_evidence.value,
            "roots": len(agent.roots),
        }
        for agent in list_agents()
    ]
    snapshot_agents_payload = [
        {
            "id": agent.id,
            "name": agent.name,
            "collision_policy": agent.collision_policy,
            "policy_evidence": agent.policy_evidence.value,
            "roots": len(agent.roots),
        }
        for agent in snapshot.registry
    ]
    assert dumps(snapshot_agents_payload) == dumps(expected_agents_payload)


# ---------------------------------------------------------------------------
# 2. First visits do not read files (§21.6)
# ---------------------------------------------------------------------------


def test_first_visits_do_not_read_files(mock_home: Path) -> None:
    """First visits to all browsing services retain original results despite disk mutations."""
    home = paths.home()
    project = home / "project"
    project.mkdir(parents=True, exist_ok=True)

    fixtures = _setup_rich_fixture(home, project)
    registry = load_registry()
    live_idx = live_discovery(cwd=project, registry=registry)
    norm_home = Path(live_idx.home)
    norm_cwd = Path(live_idx.cwd)

    # Freeze ALL expected reports and JSON outputs BEFORE capture and disk changes
    expected_scan = build_scan_report(norm_home, norm_cwd, live_idx, registry)
    expected_doc = run_doctor(norm_cwd, index=live_idx, registry=registry)

    # Freeze Why for all entries
    expected_whys: dict[tuple[str, str], Any] = {}
    for entry in live_idx.entries:
        key = canonical_key(entry)
        for agent_id, agent in registry.items():
            ln = lookup_name_for_entry(entry, agent)
            expected_whys[(key, agent_id)] = resolve_skill(
                ln,
                agent_id,
                norm_cwd,
                norm_home,
                index=live_idx,
                registry=registry,
                disabled_overrides=(
                    frozenset({"disabled_copy"}) if agent_id == "claude" else frozenset()
                ),
            )

    # Build expected captured files for diff
    temp_captured: dict[str, tuple[CapturedFile, ...]] = {}
    for entry in live_idx.entries:
        k = canonical_key(entry)
        if entry.content_hash is None:
            temp_captured[k] = ()
            continue
        r = Path(entry.canonical_path or entry.entrypoint_path)
        if r.is_dir():
            temp_captured[k] = tuple(
                CapturedFile(
                    relative_path=rel.as_posix(),
                    data=(r / rel).read_bytes(),
                    fingerprint=hash_bytes((r / rel).read_bytes()),
                )
                for rel in iter_files(r)
            )
        else:
            b = r.read_bytes()
            temp_captured[k] = (
                CapturedFile(relative_path=r.name, data=b, fingerprint=hash_bytes(b)),
            )

    expected_diffs: dict[str, Any] = {}
    for entry in live_idx.entries:
        key = canonical_key(entry)
        expected_diffs[key] = build_diff_report(
            entry.name,
            norm_cwd,
            norm_home,
            index=live_idx,
            registry=registry,
            captured_files=temp_captured,
        )

    # Freeze Compare for all pairs
    expected_comps: dict[tuple[str, str], Any] = {}
    agent_ids = sorted(registry.keys())
    for i, a1 in enumerate(agent_ids):
        for a2 in agent_ids[i + 1 :]:
            expected_comps[(a1, a2)] = run_compare(a1, a2, cwd=norm_cwd)

    expected_agents_json = dumps(
        [
            {
                "id": agent.id,
                "name": agent.name,
                "collision_policy": agent.collision_policy,
                "policy_evidence": agent.policy_evidence.value,
                "roots": len(agent.roots),
            }
            for agent in list_agents()
        ]
    )

    snapshot = capture_session(generation=1, home=home, cwd=project)

    # Mutate disk after capture:
    # 1. Delete a skill on disk
    shutil.rmtree(fixtures["diff_name_dir"])
    # 2. Change real settings
    fixtures["claude_settings"].write_text(
        '{"skillOverrides": {"disabled_copy": true}}', encoding="utf-8"
    )
    # 3. Change installer lockfile
    fixtures["lock_path"].write_text('{"skills": {"altered": "9.9"}}', encoding="utf-8")
    # 4. Retarget symlink shortcut
    fixtures["claude_shared"].unlink()
    os.symlink(fixtures["lowercase_dir"], fixtures["claude_shared"])
    # 5. Alter bytes of an asset
    (fixtures["large_skill_dir"] / "assets" / "nested.txt").write_text(
        "CORRUPTED BYTES AFTER CAPTURE\n", encoding="utf-8"
    )

    # FIRST visits to all browsing services: must equal original frozen expectations!
    # Scan
    assert snapshot.scan.to_dict() == expected_scan.to_dict()
    assert dumps(snapshot.scan.to_dict()) == dumps(expected_scan.to_dict())

    # Doctor
    assert snapshot.doctor.to_dict() == expected_doc.to_dict()
    assert dumps(snapshot.doctor.to_dict()) == dumps(expected_doc.to_dict())

    # Why
    for (key, agent_id), exp_why in expected_whys.items():
        snap_why = snapshot_why(snapshot, key, agent_id)
        assert snap_why.to_dict() == exp_why.to_dict()
        assert dumps(snap_why.to_dict()) == dumps(exp_why.to_dict())

    # Diff
    for key, exp_diff in expected_diffs.items():
        snap_diff = snapshot_diff(snapshot, key)
        assert snap_diff.to_dict() == exp_diff.to_dict()
        assert dumps(snap_diff.to_dict()) == dumps(exp_diff.to_dict())

    # Compare
    for (a1, a2), exp_comp in expected_comps.items():
        snap_comp = snapshot_compare(snapshot, a1, a2)
        assert snap_comp.to_dict() == exp_comp.to_dict()
        assert dumps(snap_comp.to_dict()) == dumps(exp_comp.to_dict())

    with pytest.raises(ValueError, match="cannot compare agent 'claude' with itself"):
        snapshot_compare(snapshot, "claude", "claude")

    # Agents JSON
    snapshot_agents_json = dumps(
        [
            {
                "id": agent.id,
                "name": agent.name,
                "collision_policy": agent.collision_policy,
                "policy_evidence": agent.policy_evidence.value,
                "roots": len(agent.roots),
            }
            for agent in snapshot.registry
        ]
    )
    assert snapshot_agents_json == expected_agents_json

    # Display paths retain original values
    assert snapshot_path(snapshot, str(home)) == "~"
    assert snapshot_path(snapshot, str(project)) == "~/project"

    # Symlink same_location retains original captured equality despite retargeting!
    claude_link_str = str(fixtures["claude_shared"])
    shared_canon_str = str(fixtures["shared_lib_dir"])
    assert snapshot_same_location(snapshot, claude_link_str, shared_canon_str) is True


# ---------------------------------------------------------------------------
# 3. Navigation has no filesystem fallback (§21.6)
# ---------------------------------------------------------------------------


def test_navigation_has_no_filesystem_fallback(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Post-capture navigation services never invoke live readers or disk probes."""
    home = paths.home()
    project = home / "project"
    project.mkdir(parents=True, exist_ok=True)

    fixtures = _setup_rich_fixture(home, project)
    snapshot = capture_session(generation=1, home=home, cwd=project)

    # Sentinel to raise on forbidden live calls
    def forbid(*args: object, **kwargs: object) -> object:
        raise AssertionError("Forbidden live probe invoked during navigation")

    with monkeypatch.context() as mp:
        # Ban all live engine / discovery / registry / path helpers
        mp.setattr("skill_lens.core.system.live_discovery", forbid)
        mp.setattr("skill_lens.core.discovery.discover", forbid)
        mp.setattr("skill_lens.registry.loader.load_registry", forbid)
        mp.setattr("skill_lens.registry.loader.list_agents", forbid)
        mp.setattr("skill_lens.core.snapshot.load_registry", forbid)
        mp.setattr("skill_lens.core.resolver.load_registry", forbid)
        mp.setattr("skill_lens.core.compare.load_registry", forbid)
        mp.setattr("skill_lens.core.resolver._load_disabled_overrides", forbid)
        mp.setattr("skill_lens.core.hasher.iter_files", forbid)
        mp.setattr("skill_lens.core.paths.home", forbid)
        mp.setattr("skill_lens.core.paths.display", forbid)
        mp.setattr("skill_lens.core.paths.same_location", forbid)

        # Ban OS-level file / directory readers
        mp.setattr(os, "walk", forbid)
        mp.setattr(os, "listdir", forbid)
        mp.setattr(os, "stat", forbid)
        mp.setattr(os, "lstat", forbid)
        mp.setattr(os.path, "realpath", forbid)
        mp.setattr(os.path, "samefile", forbid)

        mp.setattr(Path, "open", forbid)
        mp.setattr(Path, "read_bytes", forbid)
        mp.setattr(Path, "read_text", forbid)
        mp.setattr(Path, "stat", forbid)
        mp.setattr(Path, "lstat", forbid)
        mp.setattr(Path, "resolve", forbid)
        mp.setattr(Path, "readlink", forbid)
        mp.setattr(Path, "iterdir", forbid)

        # Ban builtins.open, io.open, and raw OS open/scandir
        mp.setattr(builtins, "open", forbid)
        mp.setattr(io, "open", forbid)
        mp.setattr(os, "open", forbid)
        mp.setattr(os, "scandir", forbid)

        # 1. entry_for_path
        first_entry = snapshot.index.entries[0]
        valid_key = canonical_key(first_entry)
        assert entry_for_path(snapshot, valid_key).entrypoint_path == first_entry.entrypoint_path

        with pytest.raises(KeyError):
            entry_for_path(snapshot, "/nonexistent/key")

        # 2. snapshot_why
        why_rep = snapshot_why(snapshot, valid_key, "claude")
        assert why_rep.skill_name is not None

        with pytest.raises(KeyError):
            snapshot_why(snapshot, valid_key, "unknown_agent_xyz")

        # 3. snapshot_diff
        diff_rep = snapshot_diff(snapshot, valid_key)
        assert diff_rep.skill_name is not None

        with pytest.raises(KeyError):
            snapshot_diff(snapshot, "/nonexistent/diff_key")

        # 4. snapshot_compare
        comp_rep = snapshot_compare(snapshot, "claude", "codex")
        assert comp_rep.agent_a == "claude"

        with pytest.raises(KeyError):
            snapshot_compare(snapshot, "unknown_agent", "claude")

        with pytest.raises(KeyError):
            snapshot_compare(snapshot, "claude", "unknown_agent")

        with pytest.raises(ValueError):
            snapshot_compare(snapshot, "claude", "claude")

        # 5. snapshot_path
        assert snapshot_path(snapshot, str(home)) == "~"
        assert snapshot_path(snapshot, "/some/random/unseen/path") == "/some/random/unseen/path"

        # 6. snapshot_same_location
        assert snapshot_same_location(snapshot, "same", "same") is True
        assert snapshot_same_location(snapshot, "/unseen/a", "/unseen/b") is False

        claude_link_str = str(fixtures["claude_shared"])
        shared_canon_str = str(fixtures["shared_lib_dir"])
        assert snapshot_same_location(snapshot, claude_link_str, shared_canon_str) is True
        assert snapshot_same_location(snapshot, shared_canon_str, claude_link_str) is True

        # 7. Reports and serialization
        assert dumps(snapshot.scan.to_dict()) is not None
        assert dumps(snapshot.doctor.to_dict()) is not None
        assert dumps([{"id": a.id} for a in snapshot.registry]) is not None


def test_navigation_intercepts_benign_builtin_open(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proves that a benign built-in open during navigation is intercepted."""
    home = paths.home()
    project = home / "project"
    project.mkdir(parents=True, exist_ok=True)
    _setup_rich_fixture(home, project)
    snapshot = capture_session(generation=1, home=home, cwd=project)
    first_entry = snapshot.index.entries[0]
    valid_key = canonical_key(first_entry)

    def forbid(*args: object, **kwargs: object) -> object:
        raise AssertionError("Forbidden live probe invoked during navigation: builtins.open")

    with monkeypatch.context() as mp:
        mp.setattr(builtins, "open", forbid)
        mp.setattr(io, "open", forbid)
        rep = snapshot_diff(snapshot, valid_key)
        assert rep.skill_name is not None


# ---------------------------------------------------------------------------
# 4. Refresh sees changed inputs (§21.6)
# ---------------------------------------------------------------------------


def test_refresh_sees_changed_inputs(mock_home: Path) -> None:
    """A second capture sees updated disk inputs while original snapshot stays unchanged."""
    home = paths.home()
    project = home / "project"
    project.mkdir(parents=True, exist_ok=True)

    fixtures = _setup_rich_fixture(home, project)
    snapshot1 = capture_session(generation=1, home=home, cwd=project)

    # Record snap1 state
    snap1_files = dict(snapshot1.files)
    snap1_disabled = dict(snapshot1.disabled_overrides)
    snap1_scan_dict = snapshot1.scan.to_dict()

    # Modify real settings: enable disabled_copy
    fixtures["claude_settings"].write_text(
        '{"skillOverrides": {"disabled_copy": true}}', encoding="utf-8"
    )
    # Delete a skill
    shutil.rmtree(fixtures["diff_name_dir"])
    # Modify asset bytes
    (fixtures["large_skill_dir"] / "assets" / "nested.txt").write_text(
        "MODIFIED ASSET BYTES\n", encoding="utf-8"
    )

    # Generation 2 capture
    snapshot2 = capture_session(generation=2, home=home, cwd=project)

    assert snapshot2.generation == 2
    assert snapshot2.disabled_overrides["claude"] == frozenset()
    assert snapshot2.scan.to_dict() != snap1_scan_dict
    assert snapshot2.files != snap1_files

    # Assert generation 1 snapshot is completely unchanged
    assert snapshot1.generation == 1
    assert snapshot1.disabled_overrides == snap1_disabled
    assert snapshot1.disabled_overrides["claude"] == frozenset({"disabled_copy"})
    assert snapshot1.scan.to_dict() == snap1_scan_dict
    assert snapshot1.files == snap1_files

    # Cancelled attempt leaves snapshot1 untouched
    with pytest.raises(CaptureCancelled):
        capture_session(generation=3, home=home, cwd=project, cancelled=lambda: True)
    assert snapshot1.generation == 1
    assert snapshot1.disabled_overrides["claude"] == frozenset({"disabled_copy"})


# ---------------------------------------------------------------------------
# 5. Change during capture is rejected (§21.6)
# ---------------------------------------------------------------------------


def test_change_during_capture_is_rejected(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Observable changes between capture phases raise SnapshotChanged with exact message."""
    home = paths.home()
    project = home / "project"
    project.mkdir(parents=True, exist_ok=True)
    _setup_rich_fixture(home, project)

    exact_msg = "Files changed while scanning. Press r to retry."

    import skill_lens.core.parser as parser_module
    import skill_lens.core.snapshot as snapshot_module

    orig_hash_bytes = snapshot_module.hash_bytes
    orig_live_discovery = snapshot_module.live_discovery
    orig_parse_skill_bytes = parser_module.parse_skill_bytes
    orig_build_scan = snapshot_module.build_scan_report
    orig_run_doctor = snapshot_module.run_doctor
    orig_collect = snapshot_module._collect_display_paths_and_locations

    def neutral_builders() -> tuple[Any, Any]:
        scan_1 = None
        doc_1 = None

        def neutral_scan(*args: object, **kwargs: object) -> Any:
            nonlocal scan_1
            res = orig_build_scan(*args, **kwargs)  # type: ignore[arg-type]
            if scan_1 is None:
                scan_1 = res
            return scan_1

        def neutral_doc(*args: object, **kwargs: object) -> Any:
            nonlocal doc_1
            res = orig_run_doctor(*args, **kwargs)  # type: ignore[arg-type]
            if doc_1 is None:
                doc_1 = res
            return doc_1

        return neutral_scan, neutral_doc

    # Sub-case A1: Directory file bytes change during file capture (hash mismatch)
    corrupt_hash_calls = 0

    def corrupting_hash_bytes(data: bytes) -> str:
        nonlocal corrupt_hash_calls
        corrupt_hash_calls += 1
        if corrupt_hash_calls == 2:
            return "sha256:corrupted_hash"
        return orig_hash_bytes(data)

    monkeypatch.setattr(snapshot_module, "hash_bytes", corrupting_hash_bytes)
    with pytest.raises(SnapshotChanged) as exc_info:
        capture_session(generation=1, home=home, cwd=project)
    assert str(exc_info.value) == exact_msg
    monkeypatch.undo()

    # Sub-case A2: Standalone file byte alteration during capture specifically exercising
    # the standalone capture-hash guard (snapshot.py:234).
    # Suffixless link to standalone target outside roots has parse=None.
    # After first discovery, temporarily change bytes; step 3 reads those bytes.
    # Then before second discovery, restore original bytes in first Doctor call.
    # Parse is None (step 4 skipped); second discovery sees original bytes (step 6 passes).
    # Only the first captured-byte fingerprint check (line 234) prevents publication!
    opaque_file = home / "vault" / "opaque_standalone"
    orig_opaque_bytes = b"initial opaque standalone bytes\n"
    disc_calls_a2 = 0
    orig_disc_standalone = snapshot_module.live_discovery
    orig_doc_standalone = snapshot_module.run_doctor

    def mutate_standalone_after_disc(*args: object, **kwargs: object) -> Any:
        nonlocal disc_calls_a2
        idx = orig_disc_standalone(*args, **kwargs)
        disc_calls_a2 += 1
        if disc_calls_a2 == 1:
            opaque_file.write_bytes(b"TEMPORARILY CHANGED STANDALONE BYTES\n")
        return idx

    doc_calls_a2 = 0

    def restore_standalone_in_doctor(*args: object, **kwargs: object) -> Any:
        nonlocal doc_calls_a2
        doc_calls_a2 += 1
        if doc_calls_a2 == 1:
            opaque_file.write_bytes(orig_opaque_bytes)
        return orig_doc_standalone(*args, **kwargs)

    monkeypatch.setattr(snapshot_module, "live_discovery", mutate_standalone_after_disc)
    monkeypatch.setattr(snapshot_module, "run_doctor", restore_standalone_in_doctor)
    with pytest.raises(SnapshotChanged) as exc_info:
        capture_session(generation=1, home=home, cwd=project)
    assert str(exc_info.value) == exact_msg
    opaque_file.write_bytes(orig_opaque_bytes)
    monkeypatch.undo()

    # Sub-case B1: Frontmatter metadata date-coercion drift during source reparse check
    # where to_dict() and body remain identical, but raw frontmatter differs (date vs string)
    def mutating_parse_bytes_fm(data: bytes, *, source_path: str) -> Any:
        res = orig_parse_skill_bytes(data, source_path=source_path)
        if res.frontmatter and "released" in res.frontmatter:
            mutated_fm = dict(res.frontmatter)
            mutated_fm["released"] = "2024-01-01"
            return replace(res, frontmatter=mutated_fm)
        return res

    monkeypatch.setattr(snapshot_module, "parse_skill_bytes", mutating_parse_bytes_fm)
    with pytest.raises(SnapshotChanged) as exc_info:
        capture_session(generation=1, home=home, cwd=project)
    assert str(exc_info.value) == exact_msg
    monkeypatch.undo()

    # Sub-case B2: Body change during source reparse check
    def body_mutating_parse_bytes(data: bytes, *, source_path: str) -> Any:
        res = orig_parse_skill_bytes(data, source_path=source_path)
        return replace(res, body=res.body + "\n# Extra injected body")

    monkeypatch.setattr(snapshot_module, "parse_skill_bytes", body_mutating_parse_bytes)
    with pytest.raises(SnapshotChanged) as exc_info:
        capture_session(generation=1, home=home, cwd=project)
    assert str(exc_info.value) == exact_msg
    monkeypatch.undo()

    # Sub-case B3: to_dict change during source reparse check
    class CustomParseResult(ParseResult):
        def to_dict(self) -> dict[str, Any]:
            d = super().to_dict()
            d["extra_dict_key"] = "drifted"
            return d

    def dict_mutating_parse_bytes(data: bytes, *, source_path: str) -> Any:
        res = orig_parse_skill_bytes(data, source_path=source_path)
        return CustomParseResult(
            status=res.status,
            directory_name=res.directory_name,
            body=res.body,
            frontmatter_name=res.frontmatter_name,
            description=res.description,
            source_path=res.source_path,
            errors=res.errors,
            frontmatter=res.frontmatter,
        )

    monkeypatch.setattr(snapshot_module, "parse_skill_bytes", dict_mutating_parse_bytes)
    with pytest.raises(SnapshotChanged) as exc_info:
        capture_session(generation=1, home=home, cwd=project)
    assert str(exc_info.value) == exact_msg
    monkeypatch.undo()

    # Sub-case C1: Parse transition from None to present in second pass
    n_scan, n_doc = neutral_builders()
    discovery_pass = 0

    def parse_none_to_present_disc(*args: object, **kwargs: object) -> Any:
        nonlocal discovery_pass
        discovery_pass += 1
        idx = orig_live_discovery(*args, **kwargs)
        if discovery_pass == 1:
            new_entries = list(idx.entries)
            new_entries[0] = replace(new_entries[0], parse=None)
            return replace(idx, entries=tuple(new_entries))
        return idx

    monkeypatch.setattr(snapshot_module, "live_discovery", parse_none_to_present_disc)
    monkeypatch.setattr(snapshot_module, "build_scan_report", n_scan)
    monkeypatch.setattr(snapshot_module, "run_doctor", n_doc)
    with pytest.raises(SnapshotChanged) as exc_info:
        capture_session(generation=1, home=home, cwd=project)
    assert str(exc_info.value) == exact_msg
    monkeypatch.undo()

    # Sub-case C2: Parse transition from present to None in second pass
    n_scan, n_doc = neutral_builders()
    discovery_pass = 0

    def parse_present_to_none_disc(*args: object, **kwargs: object) -> Any:
        nonlocal discovery_pass
        discovery_pass += 1
        idx = orig_live_discovery(*args, **kwargs)
        if discovery_pass == 2:
            new_entries = list(idx.entries)
            new_entries[0] = replace(new_entries[0], parse=None)
            return replace(idx, entries=tuple(new_entries))
        return idx

    monkeypatch.setattr(snapshot_module, "live_discovery", parse_present_to_none_disc)
    monkeypatch.setattr(snapshot_module, "build_scan_report", n_scan)
    monkeypatch.setattr(snapshot_module, "run_doctor", n_doc)
    with pytest.raises(SnapshotChanged) as exc_info:
        capture_session(generation=1, home=home, cwd=project)
    assert str(exc_info.value) == exact_msg
    monkeypatch.undo()

    # Sub-case D1: Entry count change in second pass
    discovery_pass = 0

    def entry_count_disc(*args: object, **kwargs: object) -> Any:
        nonlocal discovery_pass
        discovery_pass += 1
        idx = orig_live_discovery(*args, **kwargs)
        if discovery_pass == 2:
            return replace(idx, entries=idx.entries[:-1])
        return idx

    monkeypatch.setattr(snapshot_module, "live_discovery", entry_count_disc)
    with pytest.raises(SnapshotChanged) as exc_info:
        capture_session(generation=1, home=home, cwd=project)
    assert str(exc_info.value) == exact_msg
    monkeypatch.undo()

    @dataclass(frozen=True)
    class _PreserveDictParseResult(ParseResult):
        orig_dict: dict[str, Any] = field(default_factory=dict)

        def to_dict(self) -> dict[str, Any]:
            return self.orig_dict

    # Sub-cases D2 to D13: Individual entry field validation drift using neutral builders
    entry_fields_mutations: list[tuple[str, Any]] = [
        ("entrypoint_path", lambda e: replace(e, entrypoint_path="/mutated/ep")),
        ("name", lambda e: replace(e, name="mutated_name")),
        ("is_file", lambda e: replace(e, is_file=not e.is_file)),
        ("is_symlink", lambda e: replace(e, is_symlink=not e.is_symlink)),
        (
            "canonical",
            lambda e: replace(
                e,
                canonical=CanonicalResult(
                    CanonicalStatus.BROKEN,
                    entrypoint_path=e.entrypoint_path,
                    resolved_path=None,
                    is_symlink=True,
                    error="dangling_symlink",
                ),
            ),
        ),
        ("content_hash", lambda e: replace(e, content_hash="sha256:mutated_content_hash")),
        (
            "hits",
            lambda e: replace(
                e,
                hits=(
                    (replace(e.hits[0], rank=999),) + e.hits[1:]
                    if e.hits
                    else (
                        RootHit(
                            "claude",
                            "c",
                            100,
                            "rule",
                            "doc",
                            "user",
                            False,
                            None,
                            None,
                            2,
                            e.entrypoint_path,
                        ),
                    )
                ),
            ),
        ),
        ("entrypoint_paths", lambda e: replace(e, entrypoint_paths=("/mutated/ep_path",))),
        ("variant_label", lambda e: replace(e, variant_label="Variant Z")),
        (
            "parse_to_dict",
            lambda e: (
                replace(e, parse=replace(e.parse, description="mutated_description"))
                if e.parse
                else e
            ),
        ),
        (
            "parse_body",
            lambda e: (
                replace(e, parse=replace(e.parse, body=e.parse.body + "\n# extra"))
                if e.parse
                else e
            ),
        ),
        (
            "parse_frontmatter",
            lambda e: (
                replace(
                    e,
                    parse=replace(
                        e.parse,
                        frontmatter=dict(
                            e.parse.frontmatter,
                            released="2024-01-01"
                            if isinstance(e.parse.frontmatter.get("released"), datetime.date)
                            else "2024-01-01",
                        ),
                    ),
                )
                if e.parse and "released" in e.parse.frontmatter
                else e
            ),
        ),
        (
            "parse_source_path",
            lambda e: (
                replace(
                    e,
                    parse=_PreserveDictParseResult(
                        status=e.parse.status,
                        directory_name=e.parse.directory_name,
                        body=e.parse.body,
                        frontmatter_name=e.parse.frontmatter_name,
                        description=e.parse.description,
                        source_path="/mutated/source/path",
                        errors=e.parse.errors,
                        frontmatter=e.parse.frontmatter,
                        orig_dict=e.parse.to_dict(),
                    ),
                )
                if e.parse
                else e
            ),
        ),
    ]

    for field_name, mut_fn in entry_fields_mutations:
        n_scan, n_doc = neutral_builders()
        d_pass = 0

        def make_field_disc(fn: Any, name: str) -> Any:
            def field_disc(*args: object, **kwargs: object) -> Any:
                nonlocal d_pass
                d_pass += 1
                idx = orig_live_discovery(*args, **kwargs)
                if d_pass == 2:
                    new_e = list(idx.entries)
                    target_idx = 0
                    if name == "parse_frontmatter":
                        for i_e, e_cand in enumerate(new_e):
                            if e_cand.parse and "released" in e_cand.parse.frontmatter:
                                target_idx = i_e
                                break
                    mutated = fn(new_e[target_idx])
                    if name == "hits":
                        assert isinstance(mutated.hits, tuple)
                        assert all(isinstance(h, RootHit) for h in mutated.hits)
                    new_e[target_idx] = mutated
                    return replace(idx, entries=tuple(new_e))
                return idx

            return field_disc

        monkeypatch.setattr(snapshot_module, "live_discovery", make_field_disc(mut_fn, field_name))
        monkeypatch.setattr(snapshot_module, "build_scan_report", n_scan)
        monkeypatch.setattr(snapshot_module, "run_doctor", n_doc)
        monkeypatch.setattr(
            snapshot_module,
            "_collect_display_paths_and_locations",
            lambda *args, **kwargs: ({}, set()),
        )
        with pytest.raises(SnapshotChanged, match="Files changed while scanning") as exc_info:
            capture_session(generation=1, home=home, cwd=project)
        assert str(exc_info.value) == exact_msg, f"Failed for field: {field_name}"
        monkeypatch.undo()

    # Sub-case E: Unreadable roots drift in second pass
    n_scan, n_doc = neutral_builders()
    discovery_pass = 0

    def unreadable_roots_disc(*args: object, **kwargs: object) -> Any:
        nonlocal discovery_pass
        discovery_pass += 1
        idx = orig_live_discovery(*args, **kwargs)
        if discovery_pass == 2:
            return replace(
                idx,
                unreadable_roots=idx.unreadable_roots
                + [
                    UnreadableRoot("claude", "root_extra", "/unreadable/extra", "Permission denied")
                ],
            )
        return idx

    monkeypatch.setattr(snapshot_module, "live_discovery", unreadable_roots_disc)
    monkeypatch.setattr(snapshot_module, "build_scan_report", n_scan)
    monkeypatch.setattr(snapshot_module, "run_doctor", n_doc)
    with pytest.raises(SnapshotChanged) as exc_info:
        capture_session(generation=1, home=home, cwd=project)
    assert str(exc_info.value) == exact_msg
    monkeypatch.undo()

    # Sub-case F: Index home/cwd mismatch in second pass
    n_scan, n_doc = neutral_builders()
    discovery_pass = 0

    def cwd_mismatch_disc(*args: object, **kwargs: object) -> Any:
        nonlocal discovery_pass
        discovery_pass += 1
        idx = orig_live_discovery(*args, **kwargs)
        if discovery_pass == 2:
            return replace(idx, cwd="/mutated/cwd")
        return idx

    monkeypatch.setattr(snapshot_module, "live_discovery", cwd_mismatch_disc)
    monkeypatch.setattr(snapshot_module, "build_scan_report", n_scan)
    monkeypatch.setattr(snapshot_module, "run_doctor", n_doc)
    with pytest.raises(SnapshotChanged) as exc_info:
        capture_session(generation=1, home=home, cwd=project)
    assert str(exc_info.value) == exact_msg
    monkeypatch.undo()

    # Sub-case G: Scan report drift during second pass
    scan_calls = 0

    def mutating_scan_report(*args: object, **kwargs: object) -> Any:
        nonlocal scan_calls
        scan_calls += 1
        rep = orig_build_scan(*args, **kwargs)  # type: ignore[arg-type]
        if scan_calls == 2:
            new_summary = replace(rep.summary, user_skills=rep.summary.user_skills + 1)
            return replace(rep, summary=new_summary)
        return rep

    monkeypatch.setattr(snapshot_module, "build_scan_report", mutating_scan_report)
    with pytest.raises(SnapshotChanged) as exc_info:
        capture_session(generation=1, home=home, cwd=project)
    assert str(exc_info.value) == exact_msg
    monkeypatch.undo()

    # Sub-case H: Doctor report drift during second pass
    doctor_calls = 0

    def mutating_doctor_report(*args: object, **kwargs: object) -> Any:
        nonlocal doctor_calls
        doctor_calls += 1
        rep = orig_run_doctor(*args, **kwargs)  # type: ignore[arg-type]
        if doctor_calls == 2:
            from skill_lens.models.doctor import DoctorFinding
            from skill_lens.models.enums import Evidence, Severity

            dummy_finding = DoctorFinding(
                code="mutated_check",
                severity=Severity.WARNING,
                message="Mutated finding",
                rule_id="test_rule",
                evidence=Evidence.INFERRED,
            )
            return replace(rep, findings=rep.findings + (dummy_finding,))
        return rep

    monkeypatch.setattr(snapshot_module, "run_doctor", mutating_doctor_report)
    with pytest.raises(SnapshotChanged) as exc_info:
        capture_session(generation=1, home=home, cwd=project)
    assert str(exc_info.value) == exact_msg
    monkeypatch.undo()

    # Sub-case I1: Display paths drift during second pass
    collect_calls = 0

    def mutating_display_paths(*args: object, **kwargs: object) -> Any:
        nonlocal collect_calls
        collect_calls += 1
        dp, sl = orig_collect(*args, **kwargs)  # type: ignore[arg-type]
        if collect_calls == 2:
            mutated_dp = dict(dp)
            mutated_dp["injected_key"] = "injected_display_path"
            return mutated_dp, sl
        return dp, sl

    monkeypatch.setattr(
        snapshot_module, "_collect_display_paths_and_locations", mutating_display_paths
    )
    with pytest.raises(SnapshotChanged) as exc_info:
        capture_session(generation=1, home=home, cwd=project)
    assert str(exc_info.value) == exact_msg
    monkeypatch.undo()

    # Sub-case I2: Same locations drift during second pass
    collect_calls = 0

    def mutating_same_locations(*args: object, **kwargs: object) -> Any:
        nonlocal collect_calls
        collect_calls += 1
        dp, sl = orig_collect(*args, **kwargs)  # type: ignore[arg-type]
        if collect_calls == 2:
            mutated_sl = set(sl)
            mutated_sl.add(("injected_loc_a", "injected_loc_b"))
            return dp, mutated_sl
        return dp, sl

    monkeypatch.setattr(
        snapshot_module, "_collect_display_paths_and_locations", mutating_same_locations
    )
    with pytest.raises(SnapshotChanged) as exc_info:
        capture_session(generation=1, home=home, cwd=project)
    assert str(exc_info.value) == exact_msg
    monkeypatch.undo()

    # Sub-case J: Config reread detects altered bytes (even decoder-equivalent trailing whitespace)
    orig_read_guarded = snapshot_module._read_input_guarded
    read_guarded_calls: dict[str, int] = {}

    def mutating_config_reread(p: Path, *, cancelled: object = None) -> Any:
        key = str(p)
        count = read_guarded_calls.get(key, 0) + 1
        read_guarded_calls[key] = count
        ci = orig_read_guarded(p, cancelled=cancelled)  # type: ignore[arg-type]
        if count == 2 and ci.data is not None:
            return replace(ci, data=ci.data + b" ")
        return ci

    monkeypatch.setattr(snapshot_module, "_read_input_guarded", mutating_config_reread)
    with pytest.raises(SnapshotChanged) as exc_info:
        capture_session(generation=1, home=home, cwd=project)
    assert str(exc_info.value) == exact_msg
    monkeypatch.undo()


# ---------------------------------------------------------------------------
# 6. Cancelled capture does not publish (§21.6)
# ---------------------------------------------------------------------------


def test_cancelled_capture_does_not_publish(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cooperative cancellation propagates CaptureCancelled at all phases with real predicates."""
    home = paths.home()
    project = home / "project"
    project.mkdir(parents=True, exist_ok=True)
    _setup_rich_fixture(home, project)

    import skill_lens.core.snapshot as snapshot_module

    # 1. Immediate cancellation before any work
    with pytest.raises(CaptureCancelled):
        capture_session(generation=1, home=home, cwd=project, cancelled=lambda: True)

    # 2. Real chunk streaming cancellation on >64 KiB config file
    large_config = home / ".claude" / "settings.json"
    large_config.write_bytes(b'{"skillOverrides": {}}' + (b" " * (80 * 1024)))
    config_chunks_read = 0
    orig_open = Path.open

    class ConfigChunkWrapper:
        def __init__(self, f: Any) -> None:
            self._f = f

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *args: Any) -> Any:
            return self._f.__exit__(*args)

        def read(self, *args: Any, **kwargs: Any) -> bytes:
            nonlocal config_chunks_read
            chunk: bytes = self._f.read(*args, **kwargs)
            if chunk:
                config_chunks_read += 1
            return chunk

        def __getattr__(self, name: str) -> Any:
            return getattr(self._f, name)

    def tracking_config_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        handle = orig_open(self, *args, **kwargs)
        if self == large_config:
            return ConfigChunkWrapper(handle)
        return handle

    monkeypatch.setattr(Path, "open", tracking_config_open)

    def cancel_after_first_config_chunk() -> bool:
        return config_chunks_read >= 1

    with pytest.raises(CaptureCancelled):
        capture_session(
            generation=1, home=home, cwd=project, cancelled=cancel_after_first_config_chunk
        )
    assert config_chunks_read == 1, (
        "Expected cancellation after exactly one config chunk before second chunk read"
    )
    monkeypatch.undo()

    # 3. Direct guarded-reader test: verifies >64KiB cancellation and that CaptureCancelled
    # is NEVER caught or swallowed into error='unreadable'
    large_file = home / "test_large_config.json"
    large_file.write_bytes(b"X" * (100 * 1024))
    direct_chunks_read = 0

    class DirectChunkWrapper:
        def __init__(self, f: Any) -> None:
            self._f = f

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *args: Any) -> Any:
            return self._f.__exit__(*args)

        def read(self, *args: Any, **kwargs: Any) -> bytes:
            nonlocal direct_chunks_read
            chunk: bytes = self._f.read(*args, **kwargs)
            if chunk:
                direct_chunks_read += 1
            return chunk

        def __getattr__(self, name: str) -> Any:
            return getattr(self._f, name)

    def tracking_direct_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        handle = orig_open(self, *args, **kwargs)
        if self == large_file:
            return DirectChunkWrapper(handle)
        return handle

    monkeypatch.setattr(Path, "open", tracking_direct_open)

    with pytest.raises(CaptureCancelled):
        _read_input_guarded(large_file, cancelled=lambda: direct_chunks_read >= 1)
    assert direct_chunks_read == 1, "Expected direct reader to cancel after first chunk"

    # Verify CaptureCancelled is raised and not converted to unreadable
    with pytest.raises(CaptureCancelled):
        _read_input_guarded(large_file, cancelled=lambda: True)
    monkeypatch.undo()

    # 4. Cancellation during file bytes streaming (>64KiB binary asset in large_asset_skill)
    reading_large_bin = False
    chunks_read = 0
    disc_done = False
    orig_open = Path.open
    orig_disc = snapshot_module.live_discovery

    def tracking_disc(*args: Any, **kwargs: Any) -> Any:
        nonlocal disc_done
        res = orig_disc(*args, **kwargs)
        disc_done = True
        return res

    monkeypatch.setattr(snapshot_module, "live_discovery", tracking_disc)

    class ChunkTrackingWrapper:
        def __init__(self, f: Any, is_large: bool) -> None:
            self._f = f
            self._is_large = is_large

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *args: Any) -> Any:
            if self._is_large:
                nonlocal reading_large_bin
                reading_large_bin = False
            return self._f.__exit__(*args)

        def read(self, *args: Any, **kwargs: Any) -> bytes:
            data: bytes = self._f.read(*args, **kwargs)
            if self._is_large:
                nonlocal chunks_read
                chunks_read += 1
            return data

        def __getattr__(self, name: str) -> Any:
            return getattr(self._f, name)

    def tracking_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        nonlocal reading_large_bin
        handle = orig_open(self, *args, **kwargs)
        is_large = disc_done and self.name == "large.bin"
        if is_large:
            reading_large_bin = True
        return ChunkTrackingWrapper(handle, is_large)

    monkeypatch.setattr(Path, "open", tracking_open)

    def cancel_on_file_chunk() -> bool:
        if not reading_large_bin:
            return False
        return chunks_read >= 1

    with pytest.raises(CaptureCancelled):
        capture_session(generation=1, home=home, cwd=project, cancelled=cancel_on_file_chunk)
    assert chunks_read == 1, "Expected cancellation after first chunk before entire file is read"
    monkeypatch.undo()

    # 5. Cancellation during iter_files walk in directory file capture
    orig_iter_files = snapshot_module.iter_files
    iter_files_called = False

    def tracking_iter_files(root: Path, *, cancelled: Any = None) -> list[Path]:
        nonlocal iter_files_called
        iter_files_called = True
        assert cancelled is not None, "iter_files in capture must receive cancelled predicate"
        return orig_iter_files(root, cancelled=cancelled)

    monkeypatch.setattr(snapshot_module, "iter_files", tracking_iter_files)

    with pytest.raises(CaptureCancelled):
        capture_session(generation=1, home=home, cwd=project, cancelled=lambda: iter_files_called)
    assert iter_files_called
    monkeypatch.undo()

    # 6. Cancellation during _collect_display_paths_and_locations
    orig_collect = snapshot_module._collect_display_paths_and_locations
    collect_entered = False

    def tracking_collect(*args: object, **kwargs: object) -> Any:
        nonlocal collect_entered
        collect_entered = True
        assert kwargs.get("cancelled") is not None, (
            "display paths collection must receive cancelled predicate"
        )
        return orig_collect(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(snapshot_module, "_collect_display_paths_and_locations", tracking_collect)

    with pytest.raises(CaptureCancelled):
        capture_session(generation=1, home=home, cwd=project, cancelled=lambda: collect_entered)
    assert collect_entered
    monkeypatch.undo()

    # 7. Cancellation during second discovery pass
    orig_live_disc = snapshot_module.live_discovery
    disc_pass = 0

    def tracking_discovery(*args: object, **kwargs: object) -> Any:
        nonlocal disc_pass
        disc_pass += 1
        if disc_pass == 2:
            assert kwargs.get("cancelled") is not None, (
                "second discovery must receive cancelled predicate"
            )
        return orig_live_disc(*args, **kwargs)

    monkeypatch.setattr(snapshot_module, "live_discovery", tracking_discovery)

    with pytest.raises(CaptureCancelled):
        capture_session(generation=1, home=home, cwd=project, cancelled=lambda: disc_pass >= 2)
    assert disc_pass >= 2
    monkeypatch.undo()

    # 8. Cancellation during config input reading
    orig_read_guarded = snapshot_module._read_input_guarded
    read_guarded_called = False

    def tracking_read_guarded(p: Path, *, cancelled: Any = None) -> Any:
        nonlocal read_guarded_called
        read_guarded_called = True
        assert cancelled is not None, (
            "_read_input_guarded in capture must receive cancelled predicate"
        )
        return orig_read_guarded(p, cancelled=cancelled)

    monkeypatch.setattr(snapshot_module, "_read_input_guarded", tracking_read_guarded)

    with pytest.raises(CaptureCancelled):
        capture_session(generation=1, home=home, cwd=project, cancelled=lambda: read_guarded_called)
    assert read_guarded_called
    monkeypatch.undo()

    # 9. Cancellation at samefile fallback candidate loop in step 4
    step_4_samefile_calls = 0
    orig_samefile = os.path.samefile

    def tracking_samefile(p1: Any, p2: Any) -> bool:
        nonlocal step_4_samefile_calls
        res = orig_samefile(p1, p2)
        if "lowercase_skill" in str(p1) and "lowercase_skill" in str(p2):
            step_4_samefile_calls += 1
        return res

    monkeypatch.setattr(os.path, "samefile", tracking_samefile)

    def cancel_on_samefile() -> bool:
        return step_4_samefile_calls >= 1

    with pytest.raises(CaptureCancelled):
        capture_session(generation=1, home=home, cwd=project, cancelled=cancel_on_samefile)
    assert step_4_samefile_calls == 1, (
        "Expected cancellation before second samefile candidate probe"
    )
    monkeypatch.undo()

    # 10. Cancellation at final publication checkpoint
    from skill_lens.core.system import installer_lockfile
    from skill_lens.registry.loader import load_registry

    reg = load_registry()
    unique_config_paths = {str(installer_lockfile(home))} | {
        str(home / a.disabled_settings) for a in reg.values() if a.disabled_settings
    }
    total_expected_reads = 2 * len(unique_config_paths)

    reread_count = 0
    orig_reread = snapshot_module._read_input_guarded

    def tracking_reread(p: Path, *, cancelled: object = None) -> Any:
        nonlocal reread_count
        res = orig_reread(p, cancelled=cancelled)  # type: ignore[arg-type]
        reread_count += 1
        return res

    monkeypatch.setattr(snapshot_module, "_read_input_guarded", tracking_reread)

    def cancel_before_publication() -> bool:
        # Flips to True only AFTER the last actual config reread has completed
        return reread_count >= total_expected_reads

    with pytest.raises(CaptureCancelled):
        capture_session(generation=1, home=home, cwd=project, cancelled=cancel_before_publication)
    assert reread_count == total_expected_reads, (
        f"Expected all {total_expected_reads} reads to complete before publication cancellation"
    )
    monkeypatch.undo()


# ---------------------------------------------------------------------------
# 7. Snapshot owns its containers (§21.6)
# ---------------------------------------------------------------------------


def test_snapshot_owns_its_containers(mock_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Snapshot wraps original discovery index, registry, metadata, and reports."""
    home = paths.home()
    project = home / "project"
    project.mkdir(parents=True, exist_ok=True)
    _setup_rich_fixture(home, project)

    import skill_lens.core.snapshot as snapshot_module

    # Retain the real first index and original registry via wrappers
    captured_first_index: DiscoveryIndex | None = None
    captured_reg: dict[str, Any] | None = None

    orig_live_discovery = snapshot_module.live_discovery
    orig_load_registry = snapshot_module.load_registry

    def wrapping_live_discovery(*args: object, **kwargs: object) -> Any:
        nonlocal captured_first_index
        idx = orig_live_discovery(*args, **kwargs)
        if captured_first_index is None:
            captured_first_index = idx
        return idx

    def wrapping_load_registry(*args: object, **kwargs: object) -> Any:
        nonlocal captured_reg
        reg = orig_load_registry(*args, **kwargs)
        if captured_reg is None:
            captured_reg = reg
        return reg

    monkeypatch.setattr(snapshot_module, "live_discovery", wrapping_live_discovery)
    monkeypatch.setattr(snapshot_module, "load_registry", wrapping_load_registry)

    snapshot = capture_session(generation=1, home=home, cwd=project)

    assert captured_first_index is not None
    assert captured_reg is not None

    # Mutate original structures after capture:
    # 1. Clear original index entries and unreadable_roots
    saved_entries = list(captured_first_index.entries)
    captured_first_index.entries.clear()
    captured_first_index.unreadable_roots.clear()

    # 2. Clear original registry dict
    captured_reg.clear()

    # 3. Mutate original nested frontmatter
    target_orig_entry = next(
        e for e in saved_entries if e.parse and "metadata" in e.parse.frontmatter
    )
    assert target_orig_entry.parse is not None
    target_orig_entry.parse.frontmatter["metadata"]["nested_key"] = "MUTATED_VALUE"
    target_orig_entry.parse.frontmatter["metadata"]["nested_list"].append(999)
    target_orig_entry.parse.frontmatter["injected_key"] = "MUTATED"

    # Assert published snapshot is completely insulated:
    assert len(snapshot.index.entries) > 0
    assert len(snapshot.registry) > 0
    snap_target_entry = next(
        e for e in snapshot.index.entries if e.parse and "metadata" in e.parse.frontmatter
    )
    assert snap_target_entry.parse is not None
    assert snap_target_entry.parse.frontmatter["metadata"]["nested_key"] == "original_value"
    assert snap_target_entry.parse.frontmatter["metadata"]["nested_list"] == [1, 2]
    assert "injected_key" not in snap_target_entry.parse.frontmatter

    # 4. Immutable MappingProxyType on all declared mapping fields
    with pytest.raises(TypeError):
        snapshot.files["new_key"] = ()  # type: ignore[index]

    with pytest.raises(TypeError):
        snapshot.config_inputs["new_path"] = CapturedInput("p", b"", None)  # type: ignore[index]

    with pytest.raises(TypeError):
        snapshot.disabled_overrides["claude"] = frozenset()  # type: ignore[index]

    with pytest.raises(TypeError):
        snapshot.display_paths["new_path"] = "val"  # type: ignore[index]

    # 5. Declared tuple fields are owned immutable tuples
    assert isinstance(snapshot.registry, tuple)
    assert isinstance(snapshot.index.entries, tuple)
    assert isinstance(snapshot.index.unreadable_roots, tuple)
    assert isinstance(snapshot.scan.skills, tuple)
    assert isinstance(snapshot.scan.unreadable, tuple)
    assert isinstance(snapshot.doctor.findings, tuple)
    assert isinstance(snapshot.same_locations, frozenset)

    # 6. all_agents ownership
    agents_set = snapshot.index.all_agents()
    agents_set.add("mutated_agent_xyz")
    assert "mutated_agent_xyz" not in snapshot.index.all_agents()

    # 7. Deep-copied ScanReport unreadable dicts
    orig_scan_builder = snapshot_module.build_scan_report
    injected_unreadable = [{"path": "/some/unreadable", "error": "EACCES"}]

    def scan_with_unreadable(*args: object, **kwargs: object) -> Any:
        rep = orig_scan_builder(*args, **kwargs)  # type: ignore[arg-type]
        return replace(rep, unreadable=tuple(injected_unreadable))

    monkeypatch.setattr(snapshot_module, "build_scan_report", scan_with_unreadable)
    snapshot_with_unreadable = capture_session(generation=1, home=home, cwd=project)

    injected_unreadable[0]["path"] = "/mutated_after_capture"
    assert snapshot_with_unreadable.scan.unreadable[0]["path"] == "/some/unreadable"


# ---------------------------------------------------------------------------
# 8. Capture never writes target (§21.6)
# ---------------------------------------------------------------------------


def test_capture_never_writes_target(mock_home: Path) -> None:
    """Capture and navigation perform strictly read-only execution on the inspected target."""
    home = paths.home()
    project = home / "project"
    project.mkdir(parents=True, exist_ok=True)
    _setup_rich_fixture(home, project)

    # Record complete disk state before capture
    def record_tree_state(base: Path) -> dict[str, tuple[int, int, bytes | str]]:
        state: dict[str, tuple[int, int, bytes | str]] = {}
        for root, dirs, files in os.walk(base):
            for d in dirs:
                p = Path(root) / d
                rel = str(p.relative_to(base))
                if p.is_symlink():
                    state[rel] = (0, 0, os.readlink(p))
                else:
                    st = p.stat()
                    state[rel] = (st.st_mode, st.st_size, b"")
            for f in files:
                p = Path(root) / f
                rel = str(p.relative_to(base))
                if p.is_symlink():
                    state[rel] = (0, 0, os.readlink(p))
                else:
                    st = p.stat()
                    state[rel] = (st.st_mode, st.st_size, p.read_bytes())
        return state

    state_before = record_tree_state(home)

    # Run capture
    snapshot = capture_session(generation=1, home=home, cwd=project)

    state_after_capture = record_tree_state(home)
    assert state_before == state_after_capture, "Capture modified inspected target!"

    # Run all browsing operations
    for entry in snapshot.index.entries:
        key = canonical_key(entry)
        _ = snapshot_why(snapshot, key, "claude")
        _ = snapshot_diff(snapshot, key)
    _ = snapshot_compare(snapshot, "claude", "pi")
    _ = snapshot_path(snapshot, str(home))
    _ = snapshot_same_location(snapshot, str(home), str(home))
    _ = dumps(snapshot.scan.to_dict())
    _ = dumps(snapshot.doctor.to_dict())

    state_after_navigation = record_tree_state(home)
    assert state_before == state_after_navigation, "Navigation modified inspected target!"


# ---------------------------------------------------------------------------
# 9. Boundary and error conditions (§21.6)
# ---------------------------------------------------------------------------


def test_initial_home_mismatch_rejected(mock_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Initial home mismatch raises exact anchored ValueError before any discovery/disk reads."""
    import skill_lens.core.snapshot as snapshot_module

    def forbidden(*args: object, **kwargs: object) -> Any:
        raise AssertionError("Forbidden read/discovery before initial home check!")

    monkeypatch.setattr(snapshot_module, "load_registry", forbidden)
    monkeypatch.setattr(snapshot_module, "live_discovery", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)

    bogus_home = mock_home / "bogus_home"
    with pytest.raises(ValueError) as exc_info:
        capture_session(generation=1, home=bogus_home, cwd=mock_home)
    assert (
        str(exc_info.value)
        == f"supplied home '{bogus_home}' does not match effective home '{paths.home()}'"
    )


def test_effective_home_drift_rejected_before_publication(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Effective home changing during capture is rejected via SnapshotChanged."""
    home = paths.home()
    project = home / "project"
    project.mkdir(parents=True, exist_ok=True)
    _setup_rich_fixture(home, project)

    import skill_lens.core.snapshot as snapshot_module

    orig_read_guarded = snapshot_module._read_input_guarded
    read_calls = 0

    def drifting_read_guarded(p: Path, *, cancelled: object = None) -> Any:
        nonlocal read_calls
        read_calls += 1
        res = orig_read_guarded(p, cancelled=cancelled)  # type: ignore[arg-type]
        if read_calls == 4:
            monkeypatch.setattr(paths, "home", lambda: home / "drifted_before_publication")
        return res

    monkeypatch.setattr(snapshot_module, "_read_input_guarded", drifting_read_guarded)

    with pytest.raises(SnapshotChanged) as exc_info:
        capture_session(generation=1, home=home, cwd=home)

    assert str(exc_info.value) == "Files changed while scanning. Press r to retry."


def test_stable_unreadable_copy_retains_parse_and_empty_files(mock_home: Path) -> None:
    """Unreadable copy with no hash refuses snapshot generation with IncompleteTreeError."""
    from skill_lens.core.hasher import IncompleteTreeError

    home = paths.home()
    skill_dir = home / ".claude" / "skills" / "unreadable_chmod"
    make_skill(skill_dir, "unreadable_chmod", "Unreadable skill.")
    (skill_dir / "SKILL.md").chmod(0o000)

    try:
        with pytest.raises(IncompleteTreeError) as exc_info:
            capture_session(generation=1, home=home, cwd=home)
        assert exc_info.value.reason in ("denied", "io")
    finally:
        (skill_dir / "SKILL.md").chmod(0o644)


def test_suffixless_symlink_to_standalone_file(mock_home: Path) -> None:
    """Suffixless symlink to standalone file outside scanned roots captures canonical file."""
    home = paths.home()
    # Canonical file is INSIDE mock_home, but OUTSIDE all agent search roots
    target_dir = home / "outside_scanned_roots"
    target_dir.mkdir(parents=True, exist_ok=True)
    real_file = target_dir / "standalone_target.md"
    real_file.write_text(
        "---\nname: standalone_target\ndescription: Target.\n---\n# Standalone Target\n",
        encoding="utf-8",
    )

    # Suffixless symlink in an agent search root
    link_path = home / ".claude" / "skills" / "shortcut_no_ext"
    link_path.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(real_file, link_path)

    snapshot = capture_session(generation=1, home=home, cwd=home)
    target_entry = next(
        (e for e in snapshot.index.entries if "shortcut_no_ext" in e.entrypoint_path), None
    )
    assert target_entry is not None, "Expected entry for shortcut_no_ext"
    # First live entry parse is None, is_file is False, content_hash is present
    assert target_entry.parse is None
    assert target_entry.is_file is False
    assert target_entry.content_hash is not None

    key = canonical_key(target_entry)
    assert key in snapshot.files
    captured = snapshot.files[key]
    assert len(captured) == 1
    assert captured[0].relative_path == "standalone_target.md"
    assert captured[0].data == real_file.read_bytes()
    assert captured[0].fingerprint == hash_bytes(real_file.read_bytes())


def test_case_sensitive_dual_case_preference(mock_home: Path) -> None:
    """Dual-case preference test conditioned on filesystem case-sensitivity."""
    # Check if filesystem supports distinct uppercase and lowercase files
    probe_dir = mock_home / "case_probe"
    probe_dir.mkdir(parents=True, exist_ok=True)
    (probe_dir / "a.txt").write_text("lower", encoding="utf-8")
    (probe_dir / "A.txt").write_text("upper", encoding="utf-8")

    is_case_sensitive = (probe_dir / "a.txt").read_text(encoding="utf-8") != (
        probe_dir / "A.txt"
    ).read_text(encoding="utf-8")
    if not is_case_sensitive:
        pytest.skip("Filesystem is case-insensitive; dual distinct physical files unsupported.")

    home = paths.home()
    skill_dir = home / ".claude" / "skills" / "dual_case_skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "skill.md").write_text(
        "---\nname: dual\ndescription: lower\n---\n", encoding="utf-8"
    )
    (skill_dir / "SKILL.md").write_text(
        "---\nname: dual\ndescription: upper\n---\n", encoding="utf-8"
    )

    # Explicitly confirm TWO distinct physical files exist in the tested skill directory
    if (skill_dir / "skill.md").read_text(encoding="utf-8") == (skill_dir / "SKILL.md").read_text(
        encoding="utf-8"
    ):
        pytest.skip("Filesystem is case-insensitive; dual distinct physical files unsupported.")

    snapshot = capture_session(generation=1, home=home, cwd=home)
    entry = next(
        e
        for e in snapshot.index.entries
        if e.name == "dual_case_skill" or e.entrypoint_path.endswith("/dual_case_skill")
    )
    # Parser prefers SKILL.md over skill.md
    assert entry.name == "dual_case_skill"
    assert entry.parse is not None
    assert entry.parse.frontmatter_name == "dual"
    assert entry.parse.description == "upper"


def test_config_inputs_exact_outcomes_and_empty_inventory(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Config inputs assert exact statuses, and empty inventory captures correctly."""
    home = paths.home()
    project = home / "project"
    project.mkdir(parents=True, exist_ok=True)

    # 1. Direct _read_input_guarded checks on exact statuses
    # Missing file -> data=None, error='missing'
    missing_p = home / "missing.json"
    res_missing = _read_input_guarded(missing_p)
    assert res_missing.data is None
    assert res_missing.error == "missing"

    # Present empty file -> data=b"", error=None
    empty_p = home / "empty.json"
    empty_p.write_bytes(b"")
    res_empty = _read_input_guarded(empty_p)
    assert res_empty.data == b""
    assert res_empty.error is None

    # Readable nonempty file -> data=exact_bytes, error=None
    nonempty_p = home / "nonempty.json"
    content = b'{"hello": "world"}'
    nonempty_p.write_bytes(content)
    res_nonempty = _read_input_guarded(nonempty_p)
    assert res_nonempty.data == content
    assert res_nonempty.error is None

    # Unreadable file (PermissionError / OSError) -> data=None, error='unreadable'
    orig_open = Path.open
    with monkeypatch.context() as mp:

        def raise_perm(self: Path, *args: Any, **kwargs: Any) -> Any:
            if self == nonempty_p:
                raise PermissionError("Permission denied")
            return orig_open(self, *args, **kwargs)

        mp.setattr(Path, "open", raise_perm)
        res_unreadable = _read_input_guarded(nonempty_p)
        assert res_unreadable.data is None
        assert res_unreadable.error == "unreadable"

    # 2. Integration in capture_session with empty lock and unreadable settings
    lock = installer_lockfile(home)
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_bytes(b"")  # Present empty lock

    claude_settings = home / ".claude" / "settings.json"
    claude_settings.parent.mkdir(parents=True, exist_ok=True)
    claude_settings.write_bytes(b'{"skillOverrides": {}}')

    # Make claude_settings unreadable via targeted permission error
    with monkeypatch.context() as mp:

        def targeted_open(self: Path, *args: Any, **kwargs: Any) -> Any:
            if self == claude_settings:
                raise PermissionError("Permission denied")
            return orig_open(self, *args, **kwargs)

        mp.setattr(Path, "open", targeted_open)
        snap = capture_session(generation=1, home=home, cwd=project)

    assert snap.config_inputs[str(lock)].data == b""
    assert snap.config_inputs[str(lock)].error is None
    assert snap.config_inputs[str(claude_settings)].data is None
    assert snap.config_inputs[str(claude_settings)].error == "unreadable"

    # 3. Empty inventory capture over bare mock_home
    bare_home = home / "bare_home"
    bare_home.mkdir(parents=True, exist_ok=True)
    paths.set_sandbox(bare_home)
    try:
        empty_snap = capture_session(generation=1, home=bare_home, cwd=bare_home)
        assert empty_snap.index.entries == ()
        assert empty_snap.files == {}
        assert empty_snap.scan.skills == ()
        assert empty_snap.index.all_agents() == set()
        assert set(empty_snap.disabled_overrides.keys()) == {a.id for a in empty_snap.registry}
        assert all(v == frozenset() for v in empty_snap.disabled_overrides.values())
        assert empty_snap.config_inputs[str(installer_lockfile(bare_home))].data is None
        assert empty_snap.config_inputs[str(installer_lockfile(bare_home))].error == "missing"
        assert empty_snap.config_inputs[str(bare_home / ".claude/settings.json")].data is None
        assert empty_snap.config_inputs[str(bare_home / ".claude/settings.json")].error == "missing"
        assert isinstance(empty_snap.files, MappingProxyType)
        assert isinstance(empty_snap.config_inputs, MappingProxyType)
        assert isinstance(empty_snap.disabled_overrides, MappingProxyType)
    finally:
        paths.set_sandbox(home)
