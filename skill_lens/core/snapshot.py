"""Session capture and browsing services (Assignment C3).

Specification reference: FULL_SCREEN_TUI.md §21.2, §21.4, and §21.6.
"""

from __future__ import annotations

import copy
import os
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

from skill_lens.core import paths
from skill_lens.core.cancellation import check_cancelled
from skill_lens.core.compare import run_compare
from skill_lens.core.config import (
    ResolvedAgentControls,
    collect_all_config_paths,
    resolve_agent_controls,
)
from skill_lens.core.diff import build_diff_report
from skill_lens.core.discovery import (
    DiscoveredEntry,
    DiscoveryIndex,
    canonical_key,
)
from skill_lens.core.doctor import run_doctor
from skill_lens.core.hasher import (
    IncompleteTreeError,
    hash_bytes,
    hash_captured_directory,
    iter_files,
)
from skill_lens.core.parser import parse_skill_bytes
from skill_lens.core.resolver import (
    lookup_name_for_entry,
    resolve_skill,
)
from skill_lens.core.scanner import build_scan_report
from skill_lens.core.snapshot_models import (
    CapturedFile,
    CapturedInput,
    FrozenDiscoveryIndex,
    SessionSnapshot,
)
from skill_lens.core.system import installer_lockfile, live_discovery, shared_library
from skill_lens.models.compare import CompareReport
from skill_lens.models.diff import DiffReport
from skill_lens.models.parsing import CanonicalStatus
from skill_lens.models.resolution import ResolutionReport
from skill_lens.registry.loader import AgentDefinition, load_registry


class SnapshotChanged(Exception):
    """Raised when files or configurations changed while scanning."""

    def __init__(self, message: str = "Files changed while scanning. Press r to retry."):
        super().__init__(message)


def _read_input_guarded(
    path: Path, *, cancelled: Callable[[], bool] | None = None
) -> CapturedInput:
    """Read an entire configuration or lockfile in 64 KiB chunks with cancellation."""
    check_cancelled(cancelled)
    path_str = str(path)
    try:
        with path.open("rb") as f:
            chunks: list[bytes] = []
            while True:
                check_cancelled(cancelled)
                chunk = f.read(64 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
        data = b"".join(chunks)
        return CapturedInput(path=path_str, data=data, error=None)
    except FileNotFoundError:
        return CapturedInput(path=path_str, data=None, error="missing")
    except OSError:
        return CapturedInput(path=path_str, data=None, error="unreadable")


def _collect_display_paths_and_locations(
    home: Path,
    cwd: Path,
    index: DiscoveryIndex,
    registry: dict[str, AgentDefinition],
    *,
    cancelled: Callable[[], bool] | None = None,
) -> tuple[dict[str, str], set[tuple[str, str]]]:
    """Derive display paths map and symmetric same-location pairs."""
    check_cancelled(cancelled)
    path_candidates: set[str] = {
        str(home),
        str(cwd),
        str(shared_library(home)),
        str(installer_lockfile(home)),
    }
    for agent in registry.values():
        if agent.disabled_settings:
            path_candidates.add(str(home / agent.disabled_settings))
    for ur in index.unreadable_roots:
        path_candidates.add(str(ur.path))

    same_locations: set[tuple[str, str]] = set()

    for entry in index.entries:
        check_cancelled(cancelled)
        path_candidates.add(str(entry.entrypoint_path))
        if entry.canonical_path:
            path_candidates.add(str(entry.canonical_path))
        for ep in entry.entrypoint_paths:
            path_candidates.add(str(ep))
        for hit in entry.hits:
            path_candidates.add(str(hit.entrypoint_path))

        entry_paths = (
            {entry.entrypoint_path}
            | set(entry.entrypoint_paths)
            | {hit.entrypoint_path for hit in entry.hits}
        )
        canonical = entry.canonical_path or entry.entrypoint_path
        entry_canonicals = {canonical}
        if entry.canonical_path:
            entry_canonicals.add(entry.canonical_path)

        for ep in entry_paths:
            for c in entry_canonicals:
                check_cancelled(cancelled)
                if paths.same_location(ep, c):
                    same_locations.add((ep, c))
                    same_locations.add((c, ep))

    display_paths = {p: paths.display(p) for p in path_candidates}
    return display_paths, same_locations


def capture_session(
    *,
    generation: int,
    home: Path,
    cwd: Path,
    registry: dict[str, AgentDefinition] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> SessionSnapshot:
    """Capture a consistent photograph of the skill inventory, files, and health."""
    check_cancelled(cancelled)
    if home != paths.home():
        raise ValueError(f"supplied home '{home}' does not match effective home '{paths.home()}'")

    check_cancelled(cancelled)
    registry_dict = registry if registry is not None else load_registry()

    check_cancelled(cancelled)
    index_1 = live_discovery(cwd=cwd, registry=registry_dict, cancelled=cancelled)
    norm_home = Path(index_1.home)
    norm_cwd = Path(index_1.cwd)

    # 2. Capture settings and lock bytes/status through guarded reader
    # Unconditionally register candidate paths so absent -> created mid-capture
    # triggers recheck failure
    check_cancelled(cancelled)
    config_paths = collect_all_config_paths(registry_dict, norm_home, norm_cwd)

    config_inputs: dict[str, CapturedInput] = {}
    for p in config_paths:
        p_str = str(p)
        if p_str not in config_inputs:
            config_inputs[p_str] = _read_input_guarded(p, cancelled=cancelled)

    # Resolve full immutable configuration controls for all agents from captured inputs
    disabled_overrides: dict[str, frozenset[str]] = {}
    resolved_controls_map: dict[str, ResolvedAgentControls] = {}
    for agent in registry_dict.values():
        check_cancelled(cancelled)
        ctrl = resolve_agent_controls(
            agent,
            norm_home,
            norm_cwd,
            config_inputs=config_inputs,
        )
        resolved_controls_map[agent.id] = ctrl
        disabled_overrides[agent.id] = ctrl.disabled_names

    # 3. Capture file bytes for each discovered canonical copy
    captured_files: dict[str, tuple[CapturedFile, ...]] = {}
    for entry in index_1.entries:
        check_cancelled(cancelled)
        key = canonical_key(entry)
        if entry.canonical.status is not CanonicalStatus.OK:
            captured_files[key] = ()
            continue

        if not entry.traversal_complete or entry.content_hash is None:
            root = Path(entry.canonical_path or entry.entrypoint_path)
            reason = entry.traversal_error or "denied"
            raise IncompleteTreeError(path=root, reason=reason)

        root = Path(entry.canonical_path or entry.entrypoint_path)
        if root.is_dir():
            try:
                rel_paths = iter_files(root, cancelled=cancelled)
            except IncompleteTreeError:
                raise
            except OSError as err:
                reason = (
                    "denied"
                    if isinstance(err, PermissionError)
                    else ("disappeared" if isinstance(err, FileNotFoundError) else "io")
                )
                raise IncompleteTreeError(path=root, reason=reason) from err
            items: list[CapturedFile] = []
            for rel in rel_paths:
                file_path = root / rel
                try:
                    with file_path.open("rb") as f:
                        chunks: list[bytes] = []
                        while True:
                            check_cancelled(cancelled)
                            chunk = f.read(64 * 1024)
                            if not chunk:
                                break
                            chunks.append(chunk)
                    data = b"".join(chunks)
                except PermissionError as err:
                    raise IncompleteTreeError(path=file_path, reason="denied") from err
                except FileNotFoundError:
                    raise SnapshotChanged(
                        "Files changed while scanning. Press r to retry."
                    ) from None
                except OSError as err:
                    raise IncompleteTreeError(path=file_path, reason="io") from err
                fingerprint = hash_bytes(data)
                items.append(
                    CapturedFile(
                        relative_path=rel.as_posix(),
                        data=data,
                        fingerprint=fingerprint,
                    )
                )
            agg_hash = hash_captured_directory([(cf.relative_path, cf.fingerprint) for cf in items])
            if agg_hash != entry.content_hash:
                raise SnapshotChanged("Files changed while scanning. Press r to retry.")
            captured_files[key] = tuple(items)
        else:
            try:
                with root.open("rb") as f:
                    chunks = []
                    while True:
                        check_cancelled(cancelled)
                        chunk = f.read(64 * 1024)
                        if not chunk:
                            break
                        chunks.append(chunk)
                data = b"".join(chunks)
            except PermissionError as err:
                raise IncompleteTreeError(path=root, reason="denied") from err
            except FileNotFoundError:
                raise SnapshotChanged("Files changed while scanning. Press r to retry.") from None
            except OSError as err:
                raise IncompleteTreeError(path=root, reason="io") from err
            fingerprint = hash_bytes(data)
            if fingerprint != entry.content_hash:
                raise SnapshotChanged("Files changed while scanning. Press r to retry.")
            captured_files[key] = (
                CapturedFile(
                    relative_path=root.name,
                    data=data,
                    fingerprint=fingerprint,
                ),
            )

        # 4. Source reparse check
        if entry.parse is not None and entry.parse.source_path is not None:
            cf_tuple = captured_files[key]
            source_bytes: bytes | None = None
            if root.is_dir():
                rel_key: str | None = None
                try:
                    rel_key = (
                        Path(entry.parse.source_path).relative_to(entry.entrypoint_path).as_posix()
                    )
                except ValueError:
                    rel_key = None

                files_by_rel = {cf.relative_path: cf for cf in cf_tuple}
                if rel_key is not None and rel_key in files_by_rel:
                    source_bytes = files_by_rel[rel_key].data
                else:
                    source_p = Path(entry.parse.source_path)
                    for cf in cf_tuple:
                        check_cancelled(cancelled)
                        target_p = root / cf.relative_path
                        try:
                            if os.path.samefile(source_p, target_p):
                                source_bytes = cf.data
                                break
                        except OSError:
                            raise SnapshotChanged(
                                "Files changed while scanning. Press r to retry."
                            ) from None
                if source_bytes is None:
                    raise SnapshotChanged("Files changed while scanning. Press r to retry.")
            else:
                if not cf_tuple:
                    raise SnapshotChanged("Files changed while scanning. Press r to retry.")
                source_bytes = cf_tuple[0].data

            reparsed = parse_skill_bytes(source_bytes, source_path=entry.parse.source_path)
            if (
                reparsed.to_dict() != entry.parse.to_dict()
                or reparsed.body != entry.parse.body
                or reparsed.frontmatter != entry.parse.frontmatter
            ):
                raise SnapshotChanged("Files changed while scanning. Press r to retry.")

    # 5. Build scan and doctor, collect display paths & same locations
    check_cancelled(cancelled)
    scan_report = build_scan_report(norm_home, norm_cwd, index_1, registry_dict)
    check_cancelled(cancelled)
    doctor_report = run_doctor(norm_cwd, index=index_1, registry=registry_dict)
    check_cancelled(cancelled)
    display_paths, same_locations = _collect_display_paths_and_locations(
        norm_home, norm_cwd, index_1, registry_dict, cancelled=cancelled
    )

    # 6. Validate before publication (second discovery pass)
    check_cancelled(cancelled)
    index_2 = live_discovery(cwd=cwd, registry=registry_dict, cancelled=cancelled)
    check_cancelled(cancelled)

    if index_1.home != index_2.home or index_1.cwd != index_2.cwd:
        raise SnapshotChanged("Files changed while scanning. Press r to retry.")

    if len(index_1.unreadable_roots) != len(index_2.unreadable_roots):
        raise SnapshotChanged("Files changed while scanning. Press r to retry.")

    for ur1, ur2 in zip(index_1.unreadable_roots, index_2.unreadable_roots, strict=True):
        if ur1 != ur2:
            raise SnapshotChanged("Files changed while scanning. Press r to retry.")

    if len(index_1.entries) != len(index_2.entries):
        raise SnapshotChanged("Files changed while scanning. Press r to retry.")

    for e1, e2 in zip(index_1.entries, index_2.entries, strict=True):
        if (
            e1.entrypoint_path != e2.entrypoint_path
            or e1.name != e2.name
            or e1.is_file != e2.is_file
            or e1.is_symlink != e2.is_symlink
            or e1.canonical != e2.canonical
            or e1.content_hash != e2.content_hash
            or e1.hits != e2.hits
            or e1.entrypoint_paths != e2.entrypoint_paths
            or e1.variant_label != e2.variant_label
        ):
            raise SnapshotChanged("Files changed while scanning. Press r to retry.")

        if (e1.parse is None) != (e2.parse is None):
            raise SnapshotChanged("Files changed while scanning. Press r to retry.")

        if (
            e1.parse is not None
            and e2.parse is not None
            and (
                e1.parse.to_dict() != e2.parse.to_dict()
                or e1.parse.body != e2.parse.body
                or e1.parse.frontmatter != e2.parse.frontmatter
                or e1.parse.source_path != e2.parse.source_path
            )
        ):
            raise SnapshotChanged("Files changed while scanning. Press r to retry.")

    # Rebuild scan and compare
    check_cancelled(cancelled)
    scan_2 = build_scan_report(norm_home, norm_cwd, index_2, registry_dict)
    if (
        scan_report.to_dict() != scan_2.to_dict()
        or scan_report.skills != scan_2.skills
        or scan_report.summary != scan_2.summary
        or scan_report.unreadable != scan_2.unreadable
    ):
        raise SnapshotChanged("Files changed while scanning. Press r to retry.")

    # Rebuild doctor and compare
    check_cancelled(cancelled)
    doctor_2 = run_doctor(norm_cwd, index=index_2, registry=registry_dict)
    if doctor_report.to_dict() != doctor_2.to_dict() or doctor_report.findings != doctor_2.findings:
        raise SnapshotChanged("Files changed while scanning. Press r to retry.")

    # Rebuild display paths and locations and compare
    check_cancelled(cancelled)
    dp2, sl2 = _collect_display_paths_and_locations(
        norm_home, norm_cwd, index_2, registry_dict, cancelled=cancelled
    )
    if display_paths != dp2 or same_locations != sl2:
        raise SnapshotChanged("Files changed while scanning. Press r to retry.")

    # Reread configs and compare
    check_cancelled(cancelled)
    for path_str, ci in config_inputs.items():
        new_ci = _read_input_guarded(Path(path_str), cancelled=cancelled)
        if ci != new_ci:
            raise SnapshotChanged("Files changed while scanning. Press r to retry.")

    # Recheck mapping stability for resolved controls
    # (ensures canonical identities/targets are unchanged)
    for agent in registry_dict.values():
        check_cancelled(cancelled)
        new_ctrl = resolve_agent_controls(
            agent,
            norm_home,
            norm_cwd,
            config_inputs=config_inputs,
        )
        old_ctrl = resolved_controls_map.get(agent.id)
        if old_ctrl != new_ctrl:
            raise SnapshotChanged("Files changed while scanning. Press r to retry.")

    # 7. Check cancellation and effective-home agreement immediately before publication
    check_cancelled(cancelled)
    if paths.home() != norm_home:
        raise SnapshotChanged("Files changed while scanning. Press r to retry.")

    # Build owned containers
    frozen_entries: list[DiscoveredEntry] = []
    for entry in index_1.entries:
        frozen_parse = None
        if entry.parse is not None:
            frozen_parse = replace(
                entry.parse,
                frontmatter=copy.deepcopy(entry.parse.frontmatter),
            )
        frozen_entries.append(
            replace(
                entry,
                parse=frozen_parse,
                hits=tuple(entry.hits),
                entrypoint_paths=tuple(entry.entrypoint_paths),
            )
        )

    frozen_index = FrozenDiscoveryIndex(
        home=index_1.home,
        cwd=index_1.cwd,
        entries=tuple(frozen_entries),
        unreadable_roots=tuple(index_1.unreadable_roots),
    )

    owned_scan = replace(
        scan_report,
        skills=tuple(scan_report.skills),
        unreadable=tuple(copy.deepcopy(d) for d in scan_report.unreadable),
    )

    return SessionSnapshot(
        generation=generation,
        home=norm_home,
        cwd=norm_cwd,
        registry=tuple(registry_dict.values()),
        index=frozen_index,
        files=MappingProxyType(dict(captured_files)),
        config_inputs=MappingProxyType(dict(config_inputs)),
        disabled_overrides=MappingProxyType(dict(disabled_overrides)),
        display_paths=MappingProxyType(dict(display_paths)),
        same_locations=frozenset(same_locations),
        scan=owned_scan,
        doctor=doctor_report,
        resolved_controls=MappingProxyType(dict(resolved_controls_map)),
    )


def entry_for_path(snapshot: SessionSnapshot, key: str) -> DiscoveredEntry:
    """Find a discovered entry by canonical key in the frozen index."""
    for entry in snapshot.index.entries:
        if canonical_key(entry) == key:
            return entry
    raise KeyError(f"unknown canonical key '{key}'")


def snapshot_why(snapshot: SessionSnapshot, key: str, agent_id: str) -> ResolutionReport:
    """Resolve a skill entry for a specific agent using captured session state."""
    entry = entry_for_path(snapshot, key)
    registry_dict = {a.id: a for a in snapshot.registry}
    if agent_id not in registry_dict:
        known = ", ".join(sorted(registry_dict))
        raise KeyError(f"unknown agent '{agent_id}'. Known agents: {known}")
    agent = registry_dict[agent_id]
    lookup_name = lookup_name_for_entry(entry, agent)
    ctrl = (
        snapshot.resolved_controls.get(agent_id)
        if hasattr(snapshot, "resolved_controls") and snapshot.resolved_controls
        else None
    )
    overrides = (
        snapshot.disabled_overrides.get(agent_id)
        if hasattr(snapshot, "disabled_overrides") and snapshot.disabled_overrides
        else None
    )
    disp_paths = snapshot.display_paths if hasattr(snapshot, "display_paths") else None
    return resolve_skill(
        lookup_name,
        agent_id,
        snapshot.cwd,
        snapshot.home,
        index=snapshot.index,
        registry=registry_dict,
        controls=ctrl,
        disabled_overrides=overrides if ctrl is None else None,
        display_paths=disp_paths,
    )


def snapshot_diff(snapshot: SessionSnapshot, key: str) -> DiffReport:
    """Build a unified diff report using the entry directory name and captured files."""
    entry = entry_for_path(snapshot, key)
    registry_dict = {a.id: a for a in snapshot.registry}
    return build_diff_report(
        entry.name,
        snapshot.cwd,
        snapshot.home,
        index=snapshot.index,
        registry=registry_dict,
        captured_files=snapshot.files,
    )


def snapshot_compare(snapshot: SessionSnapshot, agent_a: str, agent_b: str) -> CompareReport:
    """Compare two agents using captured index and registry."""
    registry_dict = {a.id: a for a in snapshot.registry}
    if agent_a not in registry_dict:
        known = ", ".join(sorted(registry_dict))
        raise KeyError(f"unknown agent '{agent_a}'. Known agents: {known}")
    if agent_b not in registry_dict:
        known = ", ".join(sorted(registry_dict))
        raise KeyError(f"unknown agent '{agent_b}'. Known agents: {known}")
    if agent_a == agent_b:
        raise ValueError(f"cannot compare agent '{agent_a}' with itself")
    return run_compare(
        agent_a,
        agent_b,
        cwd=snapshot.cwd,
        index=snapshot.index,
        registry=registry_dict,
    )


def snapshot_path(snapshot: SessionSnapshot, path: str) -> str:
    """Return stored display path or the literal string unchanged."""
    return snapshot.display_paths.get(path, path)


def snapshot_same_location(snapshot: SessionSnapshot, a: str, b: str) -> bool:
    """Return whether two paths refer to the same location without disk probes."""
    return a == b or (a, b) in snapshot.same_locations


__all__ = [
    "SnapshotChanged",
    "capture_session",
    "entry_for_path",
    "snapshot_compare",
    "snapshot_diff",
    "snapshot_path",
    "snapshot_same_location",
    "snapshot_why",
]
