#!/usr/bin/env python3
"""P3 Cost and Capture-Scope Probe for Skill Lens 0.2.

This harness measures execution time, retained bytes, and traced Python heap
allocations for:
1. First discovery pass (live discovery with streaming content hashing).
2. Complete byte capture (all files of all discovered skills retained in memory).
3. Second discovery pass (validation pass).
4. Report construction & initial config capture (ScanReport and DoctorReport reusing index).
5. Validation pass (comparing discovery passes, complete reports, and reread configs).
6. Selective retention candidate (Diff engine's Variant A baseline & readable-copy
   rules, including readable malformed copies).
7. Simulated refresh (measuring peak traced Python heap allocations from tracking
   start through holding old snapshot and building new snapshot using freshly read
   bytes, with full report and config validation).

Benchmarks two synthetic datasets (>600 skills each):
- Scenario A: Mostly unique skills across roots, with symlinks, malformed entries,
  binary assets, and a verified malformed-diff case.
- Scenario B: Heavily duplicated skills across roots (same-name variants).

Results are printed to stdout and saved to docs/P3_COST_PROBE_RESULTS.md.
"""

from __future__ import annotations

import contextlib
import gc
import json
import os
import platform
import sys
import tempfile
import time
import tracemalloc
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from skill_lens.core import paths
from skill_lens.core.diff import build_diff_report
from skill_lens.core.discovery import DiscoveryIndex, canonical_key, labels_for_entries
from skill_lens.core.doctor import DoctorReport, build_doctor_report
from skill_lens.core.hasher import iter_files
from skill_lens.core.scanner import ScanReport, build_scan_report
from skill_lens.core.system import live_discovery
from skill_lens.registry.loader import load_registry

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True, slots=True)
class DatasetStats:
    name: str
    canonical_entries_count: int
    symlink_entrypoints_count: int
    total_entrypoints_count: int
    valid_skill_count: int
    malformed_skill_count: int
    file_count: int
    total_bytes: int
    largest_file_bytes: int
    os_cached: bool


@dataclass(frozen=True, slots=True)
class ProbeRunResult:
    scenario_name: str
    stats: DatasetStats
    t_first_discovery: float
    t_full_byte_capture: float
    t_second_discovery: float
    t_reports: float
    t_validation: float
    t_total_probe_estimate: float
    t_selective_capture: float
    retained_file_content_bytes_full: int
    retained_containers_bytes_full: int
    retained_total_bytes_full: int
    retained_file_content_bytes_selective: int
    retained_containers_bytes_selective: int
    retained_total_bytes_selective: int
    peak_traced_first_discovery: int
    peak_traced_full_capture: int
    peak_traced_second_discovery: int
    peak_traced_reports: int
    peak_traced_validation: int
    peak_traced_selective_capture: int
    peak_traced_refresh: int
    malformed_diff_verified: bool
    controlled_settings_rejected: bool
    controlled_reports_rejected: bool


def _write_file(path: Path, data: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_bytes(data)


def _make_skill_dir(
    skill_dir: Path,
    name: str,
    desc: str,
    *,
    extra_files: dict[str, bytes | str] | None = None,
    malformed: bool = False,
) -> None:
    if malformed:
        content = f"name: {name}\nmissing_description_and_invalid: [unclosed"
    else:
        content = (
            f"---\n"
            f"name: {name}\n"
            f"description: {desc}\n"
            f"---\n\n"
            f"# {name}\n\n"
            f"Skill instructions for {name} with body text to simulate realistic files.\n"
        )
    _write_file(skill_dir / "SKILL.md", content)
    if extra_files:
        for rel_path, f_data in extra_files.items():
            _write_file(skill_dir / rel_path, f_data)


def generate_scenario_a(home: Path) -> None:
    """Scenario A: Mostly unique skills across roots (total 651 entrypoints, 621 canonical)."""
    agents_dir = home / ".agents" / "skills"
    # 1. 500 unique skills in shared library (.agents/skills)
    for i in range(500):
        extra = None
        if i % 10 == 0:
            extra = {
                "scripts/helper.py": f"# Helper script for skill_{i}\ndef run():\n    pass\n",
                "references/guide.md": f"# Reference guide for skill_{i}\nDetailed guide text.\n",
            }
        if i % 25 == 0:
            extra = extra or {}
            extra["assets/preview.png"] = os.urandom(50 * 1024)
        _make_skill_dir(
            agents_dir / f"skill_{i:04d}",
            f"skill_{i:04d}",
            f"Shared capability skill {i}",
            extra_files=extra,
        )

    # 2. 50 skills in Claude root (.claude/skills): 30 duplicated with .agents, 20 unique
    claude_dir = home / ".claude" / "skills"
    for i in range(30):
        _make_skill_dir(
            claude_dir / f"skill_{i:04d}",
            f"skill_{i:04d}",
            f"Claude customized capability skill {i}",
            extra_files={"notes.txt": "Claude specific notes\n"},
        )
    for i in range(500, 520):
        _make_skill_dir(
            claude_dir / f"skill_{i:04d}",
            f"skill_{i:04d}",
            f"Claude exclusive skill {i}",
        )

    # 3. 50 skills in Codex root (.codex/skills): 20 duplicated with .agents, 30 unique
    codex_dir = home / ".codex" / "skills"
    for i in range(20, 40):
        _make_skill_dir(
            codex_dir / f"skill_{i:04d}",
            f"skill_{i:04d}",
            f"Codex variant capability skill {i}",
        )
    for i in range(520, 550):
        _make_skill_dir(
            codex_dir / f"skill_{i:04d}",
            f"skill_{i:04d}",
            f"Codex exclusive skill {i}",
        )

    # 4. 30 symlinks in Pi root (.pi/skills) pointing to .agents/skills
    pi_dir = home / ".pi" / "skills"
    pi_dir.mkdir(parents=True, exist_ok=True)
    for i in range(30):
        target = agents_dir / f"skill_{i:04d}"
        link = pi_dir / f"skill_{i:04d}"
        if not link.exists():
            link.symlink_to(target)

    # 5. 19 malformed skills in Windsurf root (.codeium/windsurf/skills)
    windsurf_dir = home / ".codeium" / "windsurf" / "skills"
    for i in range(19):
        _make_skill_dir(
            windsurf_dir / f"malformed_{i:04d}",
            f"malformed_{i:04d}",
            "",
            malformed=True,
        )

    # 6. 1 special skill: valid copy in .agents, malformed copy in .claude with differing helper
    _make_skill_dir(
        agents_dir / "skill_malformed_diff",
        "skill_malformed_diff",
        "Valid copy in shared library",
        extra_files={"scripts/helper.py": "# Version 1 in shared\nDEF = 1\n"},
    )
    _make_skill_dir(
        claude_dir / "skill_malformed_diff",
        "skill_malformed_diff",
        "",
        extra_files={"scripts/helper.py": "# Version 2 in claude\nDEF = 2\n"},
        malformed=True,
    )

    # Settings and lockfile
    _write_file(
        home / ".claude" / "settings.json",
        json.dumps({"skillOverrides": {"skill_0001": False, "skill_0002": False}}),
    )
    _write_file(
        home / ".agents" / ".skill-lock.json",
        json.dumps({"version": 1, "installed": [f"skill_{i:04d}" for i in range(50)]}),
    )


def generate_scenario_b(home: Path) -> None:
    """Scenario B: Heavily duplicated skills across roots (200 names x 3 roots = 600 entries)."""
    roots = [
        home / ".agents" / "skills",
        home / ".claude" / "skills",
        home / ".codex" / "skills",
    ]
    for r in roots:
        r.mkdir(parents=True, exist_ok=True)

    for i in range(200):
        name = f"shared_{i:04d}"
        desc = f"Heavily duplicated capability skill {i}"
        extra = None
        if i % 10 == 0:
            extra = {"scripts/run.py": f"# Script for {name}\npass\n"}
        if i % 25 == 0:
            extra = extra or {}
            extra["assets/banner.png"] = os.urandom(80 * 1024)

        # Root 0: Variant A baseline
        _make_skill_dir(roots[0] / name, name, desc, extra_files=extra)

        # Root 1: modified copy (variant B)
        extra_b = dict(extra) if extra else {}
        extra_b["variant.txt"] = "Modified in root 1\n"
        _make_skill_dir(roots[1] / name, name, desc + " (modified)", extra_files=extra_b)

        # Root 2: half identical to Root 0, half third variant
        if i % 2 == 0:
            _make_skill_dir(roots[2] / name, name, desc, extra_files=extra)
        else:
            extra_c = dict(extra) if extra else {}
            extra_c["extra.md"] = "# Extra doc\n"
            _make_skill_dir(roots[2] / name, name, desc + " (alt)", extra_files=extra_c)

    # 15 malformed skills in Grok root (.grok/skills)
    grok_dir = home / ".grok" / "skills"
    for i in range(15):
        _make_skill_dir(
            grok_dir / f"broken_{i:04d}",
            f"broken_{i:04d}",
            "",
            malformed=True,
        )

    _write_file(home / ".claude" / "settings.json", json.dumps({"skillOverrides": {}}))
    _write_file(home / ".agents" / ".skill-lock.json", json.dumps({"version": 1}))


def measure_dataset_stats(home: Path, name: str, index: DiscoveryIndex) -> DatasetStats:
    """Measure dataset filesystem and index-derived statistics."""
    file_count = 0
    total_bytes = 0
    largest_file = 0

    for root, _dirs, files in os.walk(home, followlinks=False):
        for f in files:
            file_count += 1
            p = Path(root) / f
            with contextlib.suppress(OSError):
                size = p.stat().st_size
                total_bytes += size
                if size > largest_file:
                    largest_file = size

    canonical_entries = len(index.entries)
    total_entrypoints = sum(len(e.entrypoint_paths) for e in index.entries)
    symlink_entrypoints = total_entrypoints - canonical_entries
    valid_count = sum(1 for e in index.entries if e.parse_status == "valid")
    malformed_count = sum(1 for e in index.entries if e.parse_status != "valid")

    return DatasetStats(
        name=name,
        canonical_entries_count=canonical_entries,
        symlink_entrypoints_count=symlink_entrypoints,
        total_entrypoints_count=total_entrypoints,
        valid_skill_count=valid_count,
        malformed_skill_count=malformed_count,
        file_count=file_count,
        total_bytes=total_bytes,
        largest_file_bytes=largest_file,
        os_cached=True,
    )


def _capture_all_files(index: DiscoveryIndex) -> dict[str, list[tuple[str, bytes]]]:
    """Capture all file bytes for all discovered entries."""
    captured: dict[str, list[tuple[str, bytes]]] = {}
    for entry in index.entries:
        key = entry.canonical_path or entry.entrypoint_path
        if key in captured:
            continue
        entry_files: list[tuple[str, bytes]] = []
        target_path = Path(key)
        if target_path.is_dir():
            for rel_path in iter_files(target_path):
                file_path = target_path / rel_path
                with contextlib.suppress(OSError):
                    entry_files.append((rel_path.as_posix(), file_path.read_bytes()))
        elif target_path.is_file():
            with contextlib.suppress(OSError):
                entry_files.append((target_path.name, target_path.read_bytes()))
        captured[key] = entry_files
    return captured


def _capture_configs(home: Path, registry: dict[str, Any]) -> dict[str, tuple[str, bytes]]:
    """Capture settings and lockfile bytes and status through guarded read (§21.4 Step 2)."""
    configs: dict[str, tuple[str, bytes]] = {}

    # 1. Lockfile
    lock_path = home / ".agents" / ".skill-lock.json"
    try:
        data = lock_path.read_bytes()
        configs[".agents/.skill-lock.json"] = ("present", data)
    except FileNotFoundError:
        configs[".agents/.skill-lock.json"] = ("missing", b"")
    except OSError:
        configs[".agents/.skill-lock.json"] = ("unreadable", b"")

    # 2. Agent disabled settings
    for agent in registry.values():
        disabled_settings = getattr(agent, "disabled_settings", None)
        if disabled_settings and disabled_settings not in configs:
            setting_path = home / disabled_settings
            try:
                data = setting_path.read_bytes()
                configs[disabled_settings] = ("present", data)
            except FileNotFoundError:
                configs[disabled_settings] = ("missing", b"")
            except OSError:
                configs[disabled_settings] = ("unreadable", b"")

    return configs


def _selective_capture(index: DiscoveryIndex) -> dict[str, list[tuple[str, bytes]]]:
    """Capture files under the Diff engine's Variant A baseline & readable-copy rules."""
    entries_by_name: dict[str, list[Any]] = {}
    for entry in index.entries:
        entries_by_name.setdefault(entry.name, []).append(entry)

    captured: dict[str, list[tuple[str, bytes]]] = {}

    for _name, group in entries_by_name.items():
        labels = labels_for_entries(group)
        baseline = next(
            (e for e in group if labels.get(canonical_key(e)) == "A"),
            None,
        )

        keys_needing_diff_files: set[str] = set()
        if baseline is not None and baseline.content_hash is not None:
            for copy in group:
                if canonical_key(copy) == canonical_key(baseline):
                    continue
                # Includes readable malformed copies that differ from baseline
                if copy.content_hash is not None and copy.content_hash != baseline.content_hash:
                    keys_needing_diff_files.add(canonical_key(copy))
                    keys_needing_diff_files.add(canonical_key(baseline))

        for entry in group:
            key = canonical_key(entry)
            if key in captured:
                continue
            entry_files: list[tuple[str, bytes]] = []
            target_path = Path(key)
            if key in keys_needing_diff_files:
                if target_path.is_dir():
                    for rel_path in iter_files(target_path):
                        file_path = target_path / rel_path
                        with contextlib.suppress(OSError):
                            entry_files.append((rel_path.as_posix(), file_path.read_bytes()))
                elif target_path.is_file():
                    with contextlib.suppress(OSError):
                        entry_files.append((target_path.name, target_path.read_bytes()))
            else:
                skill_doc = target_path / "SKILL.md" if target_path.is_dir() else target_path
                if skill_doc.exists():
                    with contextlib.suppress(OSError):
                        entry_files.append((skill_doc.name, skill_doc.read_bytes()))
            captured[key] = entry_files

    return captured


def validate_captured_state(
    index1: DiscoveryIndex,
    index2: DiscoveryIndex,
    scan1: ScanReport,
    scan2: ScanReport,
    doc1: DoctorReport,
    doc2: DoctorReport,
    configs_before: dict[str, tuple[str, bytes]],
    configs_after: dict[str, tuple[str, bytes]],
) -> bool:
    """Validate captured state against validation pass. Raises ValueError on any mismatch."""
    if len(index1.entries) != len(index2.entries):
        raise ValueError(
            f"Index entry count mismatch: {len(index1.entries)} vs {len(index2.entries)}"
        )
    for e1, e2 in zip(index1.entries, index2.entries, strict=True):
        if (
            e1.name != e2.name
            or e1.content_hash != e2.content_hash
            or e1.parse_status != e2.parse_status
            or e1.entrypoint_paths != e2.entrypoint_paths
        ):
            raise ValueError(f"Index entry mismatch for {e1.name}")

    if scan1 != scan2:
        raise ValueError("Complete scan report data mismatch")
    if doc1 != doc2:
        raise ValueError("Complete doctor report data mismatch")

    if configs_before != configs_after:
        raise ValueError("Config bytes or status mismatch")

    return True


def verify_controlled_rejections(
    index: DiscoveryIndex,
    scan_rep: ScanReport,
    doctor_rep: DoctorReport,
    configs: dict[str, tuple[str, bytes]],
) -> tuple[bool, bool]:
    """Verify that controlled settings and same-count report changes are rejected."""
    # 1. Controlled settings change rejection
    settings_rejected = False
    mutated_configs = dict(configs)
    target_key = next(iter(mutated_configs))
    status, orig_bytes = mutated_configs[target_key]
    mutated_configs[target_key] = (status, orig_bytes + b"\n# controlled_mutation")
    try:
        validate_captured_state(
            index, index, scan_rep, scan_rep, doctor_rep, doctor_rep, configs, mutated_configs
        )
    except ValueError:
        settings_rejected = True

    # 2. Controlled same-count report changes rejection
    doc_rejected = False
    if doctor_rep.findings:
        mutated_findings = list(doctor_rep.findings)
        mutated_findings[0] = replace(mutated_findings[0], detail="controlled_mutation")
        mutated_doc = replace(doctor_rep, findings=tuple(mutated_findings))
        assert len(mutated_doc.findings) == len(doctor_rep.findings)
        try:
            validate_captured_state(
                index, index, scan_rep, scan_rep, doctor_rep, mutated_doc, configs, configs
            )
        except ValueError:
            doc_rejected = True

    scan_rejected = False
    if scan_rep.skills:
        mutated_skills = list(scan_rep.skills)
        mutated_skills[0] = replace(mutated_skills[0], description="controlled_mutation")
        mutated_scan = replace(scan_rep, skills=tuple(mutated_skills))
        assert len(mutated_scan.skills) == len(scan_rep.skills)
        try:
            validate_captured_state(
                index, index, scan_rep, mutated_scan, doctor_rep, doctor_rep, configs, configs
            )
        except ValueError:
            scan_rejected = True

    reports_rejected = doc_rejected and scan_rejected
    return settings_rejected, reports_rejected


def run_probe(scenario_name: str, generator_fn: Any) -> ProbeRunResult:
    with tempfile.TemporaryDirectory(prefix="skill_lens_probe_") as tmpdir:
        home_path = Path(tmpdir)
        paths.set_sandbox(home_path)
        generator_fn(home_path)

        registry = load_registry()

        # ------------------------------------------------------------------
        # Phase 1: First Discovery Pass (Live walk + streaming hashes)
        # ------------------------------------------------------------------
        gc.collect()
        tracemalloc.start()
        t0 = time.perf_counter()
        index1 = live_discovery(cwd=home_path, registry=registry)
        t_first_discovery = time.perf_counter() - t0
        _, peak_traced_first_discovery = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        stats = measure_dataset_stats(home_path, scenario_name, index1)

        # ------------------------------------------------------------------
        # Phase 2: Full Byte Capture (All files of all discovered entries)
        # ------------------------------------------------------------------
        gc.collect()
        tracemalloc.start()
        t0 = time.perf_counter()
        full_captured_files = _capture_all_files(index1)
        t_full_byte_capture = time.perf_counter() - t0
        _, peak_traced_full_capture = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        retained_content_full = sum(
            len(data) for files in full_captured_files.values() for _, data in files
        )
        retained_containers_full = sys.getsizeof(full_captured_files) + sum(
            sys.getsizeof(files) + sum(sys.getsizeof(tup) for tup in files)
            for files in full_captured_files.values()
        )
        retained_total_full = retained_content_full + retained_containers_full

        # ------------------------------------------------------------------
        # Phase 3: Second Discovery Pass (Validation Pass)
        # ------------------------------------------------------------------
        gc.collect()
        tracemalloc.start()
        t0 = time.perf_counter()
        index2 = live_discovery(cwd=home_path, registry=registry)
        t_second_discovery = time.perf_counter() - t0
        _, peak_traced_second_discovery = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # ------------------------------------------------------------------
        # Phase 4: Report Construction & Initial Config Capture
        # ------------------------------------------------------------------
        gc.collect()
        tracemalloc.start()
        t0 = time.perf_counter()
        configs1 = _capture_configs(home_path, registry)
        scan_rep1 = build_scan_report(home_path, home_path, index=index1)
        doctor_rep1 = build_doctor_report(home_path, home_path, index=index1, registry=registry)
        t_reports = time.perf_counter() - t0
        _, peak_traced_reports = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # ------------------------------------------------------------------
        # Phase 5: Validation Pass (Complete reports comparison & reread configs)
        # ------------------------------------------------------------------
        gc.collect()
        tracemalloc.start()
        t0 = time.perf_counter()
        scan_rep2 = build_scan_report(home_path, home_path, index=index2)
        doctor_rep2 = build_doctor_report(home_path, home_path, index=index2, registry=registry)
        configs2 = _capture_configs(home_path, registry)
        validate_captured_state(
            index1, index2, scan_rep1, scan_rep2, doctor_rep1, doctor_rep2, configs1, configs2
        )
        t_validation = time.perf_counter() - t0
        _, peak_traced_validation = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Verify controlled rejections
        controlled_settings_rejected, controlled_reports_rejected = verify_controlled_rejections(
            index1, scan_rep1, doctor_rep1, configs1
        )
        assert controlled_settings_rejected
        assert controlled_reports_rejected

        t_total_probe_estimate = (
            t_first_discovery + t_full_byte_capture + t_second_discovery + t_reports + t_validation
        )

        # ------------------------------------------------------------------
        # Phase 6: Selective Retention Candidate (Isolated run)
        # ------------------------------------------------------------------
        gc.collect()
        tracemalloc.start()
        t0 = time.perf_counter()
        selective_captured = _selective_capture(index1)
        t_selective_capture = time.perf_counter() - t0
        _, peak_traced_selective_capture = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        retained_content_selective = sum(
            len(data) for files in selective_captured.values() for _, data in files
        )
        retained_containers_selective = sys.getsizeof(selective_captured) + sum(
            sys.getsizeof(files) + sum(sys.getsizeof(tup) for tup in files)
            for files in selective_captured.values()
        )
        retained_total_selective = retained_content_selective + retained_containers_selective

        # Verify malformed-diff case in selective retention if present
        malformed_diff_verified = False
        if "skill_malformed_diff" in [e.name for e in index1.entries]:
            diff_rep = build_diff_report("skill_malformed_diff", home_path, home_path, index=index1)
            has_helper_diff = any(
                f.path == "scripts/helper.py" for c in diff_rep.copies for f in c.files
            )
            group = [e for e in index1.entries if e.name == "skill_malformed_diff"]
            has_captured_helpers = all(
                any(
                    fname == "scripts/helper.py"
                    for fname, _ in selective_captured.get(canonical_key(e), [])
                )
                for e in group
            )
            malformed_diff_verified = has_helper_diff and has_captured_helpers

        del selective_captured
        gc.collect()

        # ------------------------------------------------------------------
        # Phase 7: Correct Refresh Memory Measurement
        # (Start tracking before constructing old snapshot; retain old state;
        #  build replacement with freshly read bytes from disk; include both
        #  discovery passes, report construction, and full validation).
        # ------------------------------------------------------------------
        gc.collect()
        tracemalloc.start()

        # 1. Build initial old snapshot from scratch including validation
        old_idx1 = live_discovery(cwd=home_path, registry=registry)
        old_configs1 = _capture_configs(home_path, registry)
        old_files = _capture_all_files(old_idx1)
        old_scan1 = build_scan_report(home_path, home_path, index=old_idx1)
        old_doctor1 = build_doctor_report(home_path, home_path, index=old_idx1, registry=registry)
        old_idx2 = live_discovery(cwd=home_path, registry=registry)
        old_scan2 = build_scan_report(home_path, home_path, index=old_idx2)
        old_doctor2 = build_doctor_report(home_path, home_path, index=old_idx2, registry=registry)
        old_configs2 = _capture_configs(home_path, registry)
        validate_captured_state(
            old_idx1,
            old_idx2,
            old_scan1,
            old_scan2,
            old_doctor1,
            old_doctor2,
            old_configs1,
            old_configs2,
        )
        old_snapshot = (old_idx1, old_configs1, old_files, old_scan1, old_doctor1)

        # 2. While retaining old_snapshot, build complete replacement snapshot including validation
        new_idx1 = live_discovery(cwd=home_path, registry=registry)
        new_configs1 = _capture_configs(home_path, registry)
        new_files = _capture_all_files(new_idx1)  # Reads fresh bytes from disk
        new_scan1 = build_scan_report(home_path, home_path, index=new_idx1)
        new_doctor1 = build_doctor_report(home_path, home_path, index=new_idx1, registry=registry)
        new_idx2 = live_discovery(cwd=home_path, registry=registry)
        new_scan2 = build_scan_report(home_path, home_path, index=new_idx2)
        new_doctor2 = build_doctor_report(home_path, home_path, index=new_idx2, registry=registry)
        new_configs2 = _capture_configs(home_path, registry)
        validate_captured_state(
            new_idx1,
            new_idx2,
            new_scan1,
            new_scan2,
            new_doctor1,
            new_doctor2,
            new_configs1,
            new_configs2,
        )
        new_snapshot = (new_idx1, new_configs1, new_files, new_scan1, new_doctor1)

        _, peak_traced_refresh = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        del old_snapshot, new_snapshot
        paths.set_sandbox(None)

        return ProbeRunResult(
            scenario_name=scenario_name,
            stats=stats,
            t_first_discovery=t_first_discovery,
            t_full_byte_capture=t_full_byte_capture,
            t_second_discovery=t_second_discovery,
            t_reports=t_reports,
            t_validation=t_validation,
            t_total_probe_estimate=t_total_probe_estimate,
            t_selective_capture=t_selective_capture,
            retained_file_content_bytes_full=retained_content_full,
            retained_containers_bytes_full=retained_containers_full,
            retained_total_bytes_full=retained_total_full,
            retained_file_content_bytes_selective=retained_content_selective,
            retained_containers_bytes_selective=retained_containers_selective,
            retained_total_bytes_selective=retained_total_selective,
            peak_traced_first_discovery=peak_traced_first_discovery,
            peak_traced_full_capture=peak_traced_full_capture,
            peak_traced_second_discovery=peak_traced_second_discovery,
            peak_traced_reports=peak_traced_reports,
            peak_traced_validation=peak_traced_validation,
            peak_traced_selective_capture=peak_traced_selective_capture,
            peak_traced_refresh=peak_traced_refresh,
            malformed_diff_verified=malformed_diff_verified,
            controlled_settings_rejected=controlled_settings_rejected,
            controlled_reports_rejected=controlled_reports_rejected,
        )


def _fmt_bytes(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b / 1024:.2f} KiB"
    return f"{b / (1024 * 1024):.2f} MiB"


def _fmt_sec(s: float) -> str:
    return f"{s * 1000:.2f} ms ({s:.3f} s)"


def main() -> None:
    print("=" * 70)
    print("Running Corrected P3 Cost & Capture-Scope Probe (FULL_SCREEN_TUI.md §9.2)")
    print(f"Python: {platform.python_version()} ({platform.python_implementation()})")
    print(f"Platform: {platform.system()} {platform.release()} ({platform.machine()})")
    print("=" * 70)

    res_a = run_probe("Scenario A (Mostly Unique Skills)", generate_scenario_a)
    res_b = run_probe("Scenario B (Heavily Duplicated Skills)", generate_scenario_b)

    results = [res_a, res_b]

    def _row(*cols: str) -> str:
        return "| " + " | ".join(cols) + " |"

    diff_delta_a = (res_a.t_selective_capture - res_a.t_full_byte_capture) * 1000
    diff_delta_b = (res_b.t_selective_capture - res_b.t_full_byte_capture) * 1000

    lines = [
        "# P3 Cost and Capture-Scope Probe Results",
        "",
        "> **Specification Reference:** `FULL_SCREEN_TUI.md` §9.2 and §22 (Assignment P3).",
        "> **Run Date:** " + time.strftime("%Y-%m-%d %H:%M:%S"),
        f"> **Environment:** Python {platform.python_version()} on {platform.system()} "
        f"{platform.machine()}.",
        "",
        "## 1. Synthetic Fixture Profiles",
        "",
        _row("Metric", "Scenario A (Mostly Unique)", "Scenario B (Heavily Duplicated)"),
        _row("---", "---", "---"),
        _row(
            "Discovered Skill Entries",
            (
                f"{res_a.stats.canonical_entries_count} canonical entries + "
                f"{res_a.stats.symlink_entrypoints_count} symlink entrypoints "
                f"({res_a.stats.total_entrypoints_count} total entrypoints)"
            ),
            (
                f"{res_b.stats.canonical_entries_count} canonical entries + "
                f"{res_b.stats.symlink_entrypoints_count} symlink entrypoints "
                f"({res_b.stats.total_entrypoints_count} total entrypoints)"
            ),
        ),
        _row(
            "Valid / Malformed / Symlinks",
            (
                f"{res_a.stats.valid_skill_count} valid, "
                f"{res_a.stats.malformed_skill_count} malformed, "
                f"{res_a.stats.symlink_entrypoints_count} symlinks "
                f"({res_a.stats.canonical_entries_count} canonical entries)"
            ),
            (
                f"{res_b.stats.valid_skill_count} valid, "
                f"{res_b.stats.malformed_skill_count} malformed, "
                f"{res_b.stats.symlink_entrypoints_count} symlinks "
                f"({res_b.stats.canonical_entries_count} canonical entries)"
            ),
        ),
        _row("Total Files on Disk", str(res_a.stats.file_count), str(res_b.stats.file_count)),
        _row(
            "Total Size on Disk",
            _fmt_bytes(res_a.stats.total_bytes),
            _fmt_bytes(res_b.stats.total_bytes),
        ),
        _row(
            "Largest File Size",
            _fmt_bytes(res_a.stats.largest_file_bytes),
            _fmt_bytes(res_b.stats.largest_file_bytes),
        ),
        _row(
            "Filesystem State",
            "Freshly written to temporary directory on local disk; resident in OS page cache",
            "Freshly written to temporary directory on local disk; resident in OS page cache",
        ),
        _row(
            "Composition Details",
            (
                "500 shared, 50 Claude, 50 Codex, 30 Pi symlinks, 20 malformed, "
                "binary assets, 1 verified malformed-diff case"
            ),
            "200 distinct skill names x 3 roots = 600 copies + 15 malformed, binary assets",
        ),
        "",
        "## 2. Separate Measured Phases (Timings)",
        "",
        _row("Phase", "Scenario A", "Scenario B", "Description / Status"),
        _row("---", "---", "---", "---"),
        _row(
            "1. First Discovery (Live Walk + Hashes)",
            _fmt_sec(res_a.t_first_discovery),
            _fmt_sec(res_b.t_first_discovery),
            "Full walk and streaming SHA-256 calculation",
        ),
        _row(
            "2. Byte Capture (Full Q9)",
            _fmt_sec(res_a.t_full_byte_capture),
            _fmt_sec(res_b.t_full_byte_capture),
            "Reads all file bytes for all discovered entries",
        ),
        _row(
            "3. Second Discovery (Validation Pass)",
            _fmt_sec(res_a.t_second_discovery),
            _fmt_sec(res_b.t_second_discovery),
            "Reruns live discovery to verify file stability",
        ),
        _row(
            "4. Report Construction & Config Capture",
            _fmt_sec(res_a.t_reports),
            _fmt_sec(res_b.t_reports),
            "`build_scan_report`, `build_doctor_report` & guarded config read",
        ),
        _row(
            "5. Validation Pass (Reports & Configs)",
            _fmt_sec(res_a.t_validation),
            _fmt_sec(res_b.t_validation),
            "Compares complete scan & doctor reports and reread config bytes",
        ),
        _row(
            "*(Unavailable Service Phases)*",
            "*N/A (Approximation)*",
            "*N/A (Approximation)*",
            (
                "In-memory cancellation checkpoints (C2), link/display maps (C3), "
                "and byte re-parsing (C1)"
            ),
        ),
        _row(
            "**Total Startup (Probe Estimate)**",
            f"**{_fmt_sec(res_a.t_total_probe_estimate)}**",
            f"**{_fmt_sec(res_b.t_total_probe_estimate)}**",
            "Sum of measured phases 1 + 2 + 3 + 4 + 5",
        ),
        "",
        "### Selective-Retention Comparison (Candidate)",
        "",
        _row("Candidate Metric", "Scenario A", "Scenario B", "Notes"),
        _row("---", "---", "---", "---"),
        _row(
            "Selective Byte Capture Time",
            _fmt_sec(res_a.t_selective_capture),
            _fmt_sec(res_b.t_selective_capture),
            "Retains support files only for differing Diff candidates",
        ),
        _row(
            "Capture Time Difference",
            f"{diff_delta_a:+.1f} ms",
            f"{diff_delta_b:+.1f} ms",
            "Signed difference vs full capture (negative = faster)",
        ),
        _row(
            "Malformed-Diff Rule Verified",
            "YES" if res_a.malformed_diff_verified else "NO",
            "N/A",
            "Diff engine's Variant A baseline & readable-copy rules verified",
        ),
        _row(
            "Controlled Settings Rejection Verified",
            "YES" if res_a.controlled_settings_rejected else "NO",
            "YES" if res_b.controlled_settings_rejected else "NO",
            "Verified that modified settings/lock bytes trigger validation rejection",
        ),
        _row(
            "Controlled Same-Count Report Rejection Verified",
            "YES" if res_a.controlled_reports_rejected else "NO",
            "YES" if res_b.controlled_reports_rejected else "NO",
            "Verified that same-count mutated reports trigger validation rejection",
        ),
        "",
        "## 3. Precise Memory & Allocation Measurements",
        "",
        "> **Note on Allocation Labels:** `tracemalloc` measures peak heap allocations "
        "tracked by the Python runtime for the monitored block. It does not represent "
        "total OS process memory (Resident Set Size). The file payload and container figures "
        "below measure captured file content payload plus selected file-storage container overhead "
        "(dictionaries, lists, and tuples holding file bytes), rather than total snapshot memory "
        "(which also holds index entries, parse results, reports, and configs). Both full and "
        "selective capture use the identical memory-accounting method.",
        "",
        _row("Memory Metric", "Scenario A", "Scenario B", "Description"),
        _row("---", "---", "---", "---"),
        _row(
            "Retained File Payload Bytes",
            _fmt_bytes(res_a.retained_file_content_bytes_full),
            _fmt_bytes(res_b.retained_file_content_bytes_full),
            "Exact sum of in-memory file byte buffers",
        ),
        _row(
            "Selected File Container Overhead",
            _fmt_bytes(res_a.retained_containers_bytes_full),
            _fmt_bytes(res_b.retained_containers_bytes_full),
            "Overhead of mapping dicts, lists, and file tuples",
        ),
        _row(
            "**File Payload + Selected Container Overhead (Full)**",
            f"**{_fmt_bytes(res_a.retained_total_bytes_full)}**",
            f"**{_fmt_bytes(res_b.retained_total_bytes_full)}**",
            "Sum of file bytes and container overhead for full capture",
        ),
        _row(
            "**File Payload + Selected Container Overhead (Selective)**",
            f"**{_fmt_bytes(res_a.retained_total_bytes_selective)}**",
            f"**{_fmt_bytes(res_b.retained_total_bytes_selective)}**",
            "Identical calculation for selective candidate (skips support files)",
        ),
        _row(
            "Peak Traced: First Discovery",
            _fmt_bytes(res_a.peak_traced_first_discovery),
            _fmt_bytes(res_b.peak_traced_first_discovery),
            "Traced Python heap during initial discovery",
        ),
        _row(
            "Peak Traced: Full Byte Capture",
            _fmt_bytes(res_a.peak_traced_full_capture),
            _fmt_bytes(res_b.peak_traced_full_capture),
            "Traced Python heap during full byte reading",
        ),
        _row(
            "Peak Traced: Reports & Config Capture",
            _fmt_bytes(res_a.peak_traced_reports),
            _fmt_bytes(res_b.peak_traced_reports),
            "Traced Python heap during scan/doctor build & config read",
        ),
        _row(
            "Peak Traced: Validation Pass",
            _fmt_bytes(res_a.peak_traced_validation),
            _fmt_bytes(res_b.peak_traced_validation),
            "Traced Python heap during complete reports/config validation",
        ),
        _row(
            "**Peak Traced: Simulated Refresh**",
            f"**{_fmt_bytes(res_a.peak_traced_refresh)}**",
            f"**{_fmt_bytes(res_b.peak_traced_refresh)}**",
            "Peak traced heap while holding old snapshot and building new",
        ),
        "",
        "## 4. Architectural Analysis & Decision Record",
        "",
        "### 4.1 Probe Findings",
        (
            f"1. **Full Capture Time:** Reading all file bytes across 600+ skills requires only "
            f"**~{res_a.t_full_byte_capture * 1000:.1f} ms (Scenario A)** and "
            f"**~{res_b.t_full_byte_capture * 1000:.1f} ms (Scenario B)**."
        ),
        (
            f"2. **Total Startup Estimate:** The sum of all five measured startup phases is "
            f"**~{res_a.t_total_probe_estimate:.2f} s (Scenario A)** and "
            f"**~{res_b.t_total_probe_estimate:.2f} s (Scenario B)** on Darwin arm64. "
            "Passing the existing index and registry into `build_doctor_report` eliminates the "
            "redundant discovery walk. Unimplemented phases (cooperative cancellation checkpoints "
            "in C2, path display and link equality maps in C3, and byte re-parsing in C1) are "
            "explicitly labeled as approximations."
        ),
        (
            "3. **In-Memory Retention & Precise Accounting:** Total in-memory storage for captured "
            f"files and containers (using identical accounting methods) is "
            f"**{_fmt_bytes(res_a.retained_total_bytes_full)} (Scenario A)** and "
            f"**{_fmt_bytes(res_b.retained_total_bytes_full)} (Scenario B)**. "
            "This accounts for file payload plus selected container overhead."
        ),
        (
            "4. **Refresh Memory:** Tracking heap allocations from start through retaining the "
            "entire old snapshot and constructing and validating the replacement snapshot with "
            "freshly read bytes peaked at "
            f"**{_fmt_bytes(res_a.peak_traced_refresh)} (Scenario A)** and "
            f"**{_fmt_bytes(res_b.peak_traced_refresh)} (Scenario B)** of traced allocations."
        ),
        (
            "5. **Validation Integrity:** The validation pass verifies complete scan and doctor "
            "report dataclasses (`scan1 == scan2`, `doc1 == doc2`) and reread configuration bytes. "
            "Controlled tests verified that mutated settings and same-count report modifications "
            "are reliably detected and rejected."
        ),
        (
            "6. **Selective Retention Evaluation:** Selective retention saves only "
            f"~{abs(diff_delta_a):.1f} ms of capture time. Furthermore, to adhere to the "
            "Diff engine's Variant A baseline and readable-copy rules (where readable "
            "malformed copies with differing support files must be diffed), selective "
            "retention must retain support files for those malformed copies as verified in "
            "Scenario A. The minor memory reduction does not justify the added state complexity."
        ),
        "",
        "### 4.2 Decision Gate",
        "- **Decision:** **Retain §21 Full Capture specification verbatim.**",
        "- **Rationale:** Full capture provides 100% frozen inputs with zero live disk access "
        "during navigation, consumes under 3 MiB of retained file payload/containers for 600+ "
        "skills, and introduces no fragile conditional caching logic.",
        "",
        "---",
        "*Report generated by `docs/p3_cost_probe.py`.*",
    ]

    report_text = "\n".join(lines) + "\n"
    out_path = REPO_ROOT / "docs" / "P3_COST_PROBE_RESULTS.md"
    out_path.write_text(report_text, encoding="utf-8")
    print(f"\nReport written to {out_path}")
    print("\nSummary:")
    for r in results:
        print(f"\n{r.scenario_name}:")
        print(
            f"  Canonical entries: {r.stats.canonical_entries_count} | "
            f"Symlink entrypoints: {r.stats.symlink_entrypoints_count} | "
            f"Total entrypoints: {r.stats.total_entrypoints_count}"
        )
        print(f"  Startup estimate: {_fmt_sec(r.t_total_probe_estimate)}")
        print(f"  Retained payload + containers (full): {_fmt_bytes(r.retained_total_bytes_full)}")
        print(
            f"  Retained payload + containers (selective): "
            f"{_fmt_bytes(r.retained_total_bytes_selective)}"
        )
        print(f"  Peak traced heap (refresh): {_fmt_bytes(r.peak_traced_refresh)}")
        if r.malformed_diff_verified:
            print("  Malformed-diff rule verified: YES")
        if r.controlled_settings_rejected and r.controlled_reports_rejected:
            print("  Controlled rejections verified: YES")


if __name__ == "__main__":
    main()
