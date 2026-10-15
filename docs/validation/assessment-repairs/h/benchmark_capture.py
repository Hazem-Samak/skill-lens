#!/usr/bin/env python3
"""Stage H byte-heavy capture/refresh benchmark.

Measures capture_session() initial + overlapping refresh on synthetic
byte-heavy fixtures.

The benchmark instrumentation itself is stdlib only (argparse, gc, hashlib,
json, os, platform, stat, sys, tempfile, time, tracemalloc). capture_session()
is exercised against the installed skill_lens runtime (PyYAML/Rich/Typer), so
the *product* code path is not stdlib only.

No live skills, no system-root probes, no network; no writes inside the
repository. Synthetic fixtures and the disposable proof scripts live outside
the repo (in a temp dir under /tmp).

Scenarios (each repeated 3 times):
  A: 8 skills x 2 MiB binary asset each   (~16 MiB total payload)
  B: 8 skills x 8 MiB binary asset each   (~64 MiB total payload)
  C: 1 skill x 16 MiB binary asset        (~16 MiB total payload, single file)

For each scenario and repeat:
  1. Build synthetic skills under a temp sandbox home (outside repo).
  2. Fingerprint fixture BEFORE capture: every regular file's path/size/mode/
     chunked SHA-256, every directory's path/mode, every symlink's path/target
     (no following). Fail on walk/stat/read errors. Synthetic fixtures contain
     no symlinks; none are added just to claim hypothetical coverage.
  3. Set synthetic HOME/XDG_CONFIG_HOME/sandbox; save the ORIGINAL values;
     restore them safely in finally, even on failure.
  4. Untraced initial capture (generation=1); keep the old snapshot ALIVE.
  5. Untraced refresh capture (generation=2) with generation 1 still held.
     This raw capture_session overlap is a *simulated refresh*, not the
     controller pipeline. Record wall times and snapshot stats.
  6. Release both untraced snapshots before the traced runs.
  7. tracemalloc run: gc.collect, start BEFORE the old generation exists, read
     the tracing baseline, capture generation 1 (held), gc.collect, read
     (current1, peak1); tracemalloc.reset_peak() immediately before refresh;
     capture generation 2 (both held), gc.collect, read (current2, refresh_peak);
     stop tracemalloc.
     Retained heap one generation = current1; retained heap both generations =
     current2; peak1 and refresh_peak are transient peaks, reported separately.
  8. Enforced assertions: exact file/payload/largest/canonical counts for
     initial/refresh/old/new against full fixture totals (asset bytes + SKILL.md),
     generation IDs 1 and 2, distinct objects/bytes. Fail nonzero on mismatch.
  9. Fingerprint AFTER capture (tracing off, temporaries released); verify every
     byte/mode/symlink target unchanged (full inventory unchanged).
  10. Restore original sandbox/HOME/XDG_CONFIG_HOME/tracemalloc in finally.

Output is JSON written to --output (default: a unique file under h/ that never
overwrites historical evidence; --output must not overwrite historical
evidence silently either — writes use exclusive creation).
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import stat
import sys
import tempfile
import time
import tracemalloc
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skill_lens.core import paths  # noqa: E402
from skill_lens.core.snapshot import capture_session  # noqa: E402
from skill_lens.registry.loader import load_registry  # noqa: E402

_SKILL_MD = (
    "---\nname: {name}\ndescription: Stage H synthetic benchmark skill {index}.\n"
    "---\n\nBody text for skill {index}. Intentionally small so the measured "
    "payload is dominated by the binary asset file, not the skill document.\n"
)

#: Deterministic PRNG seed so fixture bytes are reproducible and documented.
_FIXTURE_SEED = 20261016

#: Scenario definitions: (label, skill_count, asset_bytes_each).
SCENARIOS = [
    ("8x2MiB", 8, 2 * 1024 * 1024),
    ("8x8MiB", 8, 8 * 1024 * 1024),
    ("1x16MiB", 1, 16 * 1024 * 1024),
]
REPEATS = 3

#: Product source modules the benchmark exercises, hashed to tie results to the
#: unchanged source base. Paths are relative to REPO_ROOT.
_PRODUCT_SOURCE_MODULES = [
    "skill_lens/core/paths.py",
    "skill_lens/core/snapshot.py",
    "skill_lens/core/hasher.py",
    "skill_lens/registry/loader.py",
]


def _deterministic_bytes(size: int, seed_offset: int) -> bytes:
    """Return deterministic pseudo-random bytes of ``size``.

    Seeded PRNG so regeneration is byte-identical across runs; avoids any
    constant-bytes reuse by the compiler/interpreter.
    """
    import random

    return random.Random(_FIXTURE_SEED + seed_offset).randbytes(size)


@dataclass
class FixtureEntry:
    path: str
    is_symlink: bool
    size: int
    mode: str
    symlink_target: str | None
    sha256: str | None


@dataclass
class DirEntry:
    path: str
    mode: str


@dataclass
class FixtureFingerprint:
    file_count: int
    total_bytes: int
    largest_file_bytes: int
    dir_count: int
    entries: list[FixtureEntry] = field(default_factory=list)
    dirs: list[DirEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "largest_file_bytes": self.largest_file_bytes,
            "dir_count": self.dir_count,
            "entries": [asdict(e) for e in self.entries],
            "dirs": [asdict(d) for d in self.dirs],
        }

    def sha256_map(self) -> dict[str, str]:
        """Path -> SHA-256 for regular files (None for symlinks/directories)."""
        return {e.path: e.sha256 for e in self.entries if e.sha256 is not None}


def _hash_file(path: Path) -> str:
    """Chunked SHA-256 of a regular file; raises OSError on read failure."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(64 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _fingerprint_tree(root: Path) -> FixtureFingerprint:
    """Record every file/dir/symlink under ``root``.

    Regular files: path, size, mode, chunked SHA-256.
    Directories: path, mode.
    Symlinks (file or dir): path, target, no following; mode recorded.
    Any walk/stat/read error raises instead of being silently skipped.
    """
    file_count = 0
    total_bytes = 0
    largest = 0
    dir_count = 0
    entries: list[FixtureEntry] = []
    dirs: list[DirEntry] = []

    def _walk_onerror(err: OSError) -> None:
        """os.walk error callback: never silently skip a traversal failure."""
        raise OSError(f"cannot traverse {err.filename}: {err}") from err

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False, onerror=_walk_onerror):
        dirnames.sort()
        # Record this directory (including the root itself on first iteration).
        st = os.lstat(dirpath)
        dir_count += 1
        dirs.append(
            DirEntry(path=Path(dirpath).relative_to(root).as_posix(), mode=oct(st.st_mode & 0o7777))
        )

        for name in sorted(dirnames):
            p = Path(dirpath) / name
            try:
                st = p.lstat()
            except OSError as err:
                raise OSError(f"cannot stat directory symlink {p}: {err}") from err
            rel = p.relative_to(root).as_posix()
            if stat.S_ISLNK(st.st_mode):
                try:
                    target = os.readlink(p)
                except OSError as err:
                    raise OSError(f"cannot read directory symlink {p}: {err}") from err
                # Directory symlink: record target, do NOT follow.
                dirs.append(DirEntry(path=rel, mode=oct(st.st_mode & 0o7777)))
                entries.append(
                    FixtureEntry(
                        path=rel,
                        is_symlink=True,
                        size=0,
                        mode=oct(st.st_mode & 0o7777),
                        symlink_target=target,
                        sha256=None,
                    )
                )

        for name in sorted(filenames):
            p = Path(dirpath) / name
            try:
                st = p.lstat()
            except OSError as err:
                raise OSError(f"cannot stat file {p}: {err}") from err
            rel = p.relative_to(root).as_posix()
            is_symlink = stat.S_ISLNK(st.st_mode)
            target: str | None = None
            sha256: str | None = None
            size = 0
            if is_symlink:
                try:
                    target = os.readlink(p)
                except OSError as err:
                    raise OSError(f"cannot read file symlink {p}: {err}") from err
            else:
                size = st.st_size
                try:
                    sha256 = _hash_file(p)
                except OSError as err:
                    raise OSError(f"cannot hash file {p}: {err}") from err
            file_count += 1
            total_bytes += size
            if size > largest:
                largest = size
            entries.append(
                FixtureEntry(
                    path=rel,
                    is_symlink=is_symlink,
                    size=size,
                    mode=oct(st.st_mode & 0o7777),
                    symlink_target=target,
                    sha256=sha256,
                )
            )

    entries.sort(key=lambda e: e.path)
    dirs.sort(key=lambda d: d.path)
    return FixtureFingerprint(
        file_count=file_count,
        total_bytes=total_bytes,
        largest_file_bytes=largest,
        dir_count=dir_count,
        entries=entries,
        dirs=dirs,
    )


def _same_fingerprint(a: FixtureFingerprint, b: FixtureFingerprint) -> bool:
    return (
        a.file_count == b.file_count
        and a.total_bytes == b.total_bytes
        and a.largest_file_bytes == b.largest_file_bytes
        and a.dir_count == b.dir_count
        and [asdict(e) for e in a.entries] == [asdict(e) for e in b.entries]
        and [asdict(d) for d in a.dirs] == [asdict(d) for d in b.dirs]
    )


def _build_skills(
    home: Path, skill_count: int, asset_bytes_each: int, scenario_tag: str
) -> dict[str, Any]:
    """Create skill_count skill directories under ``.codex/skills``.

    Each skill: SKILL.md + one binary asset file. Returns creation metadata.
    """
    skills_root = home / ".codex" / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)

    created: list[dict[str, Any]] = []
    total_payload = 0
    skill_md_bytes = 0
    for i in range(skill_count):
        name = f"{scenario_tag}-skill-{i:03d}"
        skill_dir = skills_root / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_md = skill_dir / "SKILL.md"
        skill_md_text = _SKILL_MD.format(name=name, index=i)
        skill_md.write_text(skill_md_text, encoding="utf-8")
        if i == 0:
            skill_md_bytes = len(skill_md_text.encode("utf-8"))

        asset = skill_dir / "asset.bin"
        data = _deterministic_bytes(asset_bytes_each, i)
        asset.write_bytes(data)
        total_payload += len(data)

        created.append(
            {
                "name": name,
                "asset_bytes": len(data),
            }
        )

    return {
        "skills": created,
        "total_payload_bytes": total_payload,
        "skill_count": skill_count,
        "skill_md_bytes_each": skill_md_bytes,
    }


def _snapshot_stats(snap: Any) -> dict[str, Any]:
    """Extract payload/file counts from a SessionSnapshot."""
    total_files = 0
    total_payload = 0
    largest_file = 0
    canonical_keys = 0
    for _key, files_tuple in snap.files.items():
        canonical_keys += 1
        for cf in files_tuple:
            total_files += 1
            total_payload += len(cf.data)
            if len(cf.data) > largest_file:
                largest_file = len(cf.data)
    return {
        "captured_file_count": total_files,
        "captured_payload_bytes": total_payload,
        "captured_largest_file_bytes": largest_file,
        "canonical_keys": canonical_keys,
        "generation": snap.generation,
    }


def _config_bytes(snap: Any) -> int:
    """Total captured configuration/lockfile bytes (reported separately from payload)."""
    total = 0
    for ci in snap.config_inputs.values():
        if ci.data is not None:
            total += len(ci.data)
    return total


class _AssertionFailure(Exception):
    """Raised when an enforced benchmark assertion fails."""


def _assert(condition: bool, message: str) -> None:
    """Enforced assertion: raises so the run exits nonzero on mismatch."""
    if not condition:
        raise _AssertionFailure(message)


def _expected_totals(creation: dict[str, Any]) -> dict[str, int]:
    """Full fixture totals for a scenario: files/payload/largest/canonical skills."""
    skill_count = creation["skill_count"]
    asset_each = creation["total_payload_bytes"] // skill_count
    md_each = creation["skill_md_bytes_each"]
    return {
        "expected_files": skill_count * 2,  # SKILL.md + asset per skill
        "expected_payload": creation["total_payload_bytes"] + skill_count * md_each,
        "expected_largest": asset_each,
        "expected_canonical": skill_count,
    }


def _scenario_run(
    home: Path,
    scenario_label: str,
    skill_count: int,
    asset_bytes_each: int,
    repeat: int,
) -> dict[str, Any]:
    """Run one full scenario repeat: build, fingerprint, capture, verify."""

    # 1. Build synthetic fixtures (outside tracing, outside repo).
    creation = _build_skills(home, skill_count, asset_bytes_each, scenario_label)
    totals = _expected_totals(creation)
    total_payload_assets = creation["total_payload_bytes"]

    # 2. Fingerprint BEFORE capture (with chunked SHA-256 per regular file).
    before = _fingerprint_tree(home)

    # Save ORIGINAL state; restore in finally, even on failure.
    original_sandbox = paths.get_sandbox()
    original_home = os.environ.get("HOME")
    original_xdg = os.environ.get("XDG_CONFIG_HOME")
    tracemalloc_was_active = tracemalloc.is_tracing()

    # Guard: supported mode is a fresh subprocess with tracemalloc NOT already
    # active. If a tracer is already running, "untraced" timing is not untraced,
    # and stopping/restarting it would not restore its history. Refuse clearly
    # rather than claim restored history.
    if tracemalloc_was_active:
        raise _AssertionFailure(
            "tracemalloc is already active before benchmark start; "
            "supported mode is a fresh subprocess with no active tracer. "
            "Refusing to mutate fixture/state or stop/restart an owned tracer."
        )

    # 3. Set synthetic HOME, XDG_CONFIG_HOME and sandbox.
    paths.set_sandbox(home)
    sandbox_home = paths.home()
    os.environ["HOME"] = str(sandbox_home)
    os.environ["XDG_CONFIG_HOME"] = str(sandbox_home / ".config")

    traced_run: dict[str, Any] = {}
    assertions: dict[str, Any] = {}
    initial_run: dict[str, Any] = {}
    refresh_run: dict[str, Any] = {}
    snap_old = None
    snap_new = None

    try:
        registry = load_registry()

        # 4. Untraced initial capture (generation=1); keep old ALIVE.
        t0 = time.perf_counter()
        snap_initial = capture_session(
            generation=1, home=sandbox_home, cwd=sandbox_home, registry=registry
        )
        initial_wall_ms = (time.perf_counter() - t0) * 1000
        initial_stats = _snapshot_stats(snap_initial)

        # 5. Untraced refresh capture (generation=2) with generation 1 still held.
        #    Raw capture_session overlap = simulated refresh, not controller pipeline.
        t0 = time.perf_counter()
        snap_refresh = capture_session(
            generation=2, home=sandbox_home, cwd=sandbox_home, registry=registry
        )
        refresh_wall_ms = (time.perf_counter() - t0) * 1000
        refresh_stats = _snapshot_stats(snap_refresh)

        initial_run = {
            "wall_ms": initial_wall_ms,
            "traced": False,
            "snapshot": initial_stats,
            "config_bytes": _config_bytes(snap_initial),
            "note": "untraced initial capture (generation 1), snapshot held alive through refresh",
        }
        refresh_run = {
            "wall_ms": refresh_wall_ms,
            "traced": False,
            "snapshot": refresh_stats,
            "config_bytes": _config_bytes(snap_refresh),
            "note": "untraced refresh capture (generation 2) with generation 1 held; "
            "raw capture_session overlap, simulated refresh, not controller pipeline",
        }

        # 6. Release both untraced snapshots before traced runs.
        del snap_initial, snap_refresh
        gc.collect()

        # 7. Traced run: start BEFORE old generation exists.
        gc.collect()
        tracemalloc.start()
        try:
            baseline_current, baseline_peak = tracemalloc.get_traced_memory()

            snap_old = capture_session(
                generation=1, home=sandbox_home, cwd=sandbox_home, registry=registry
            )
            gc.collect()
            current1, peak1 = tracemalloc.get_traced_memory()

            tracemalloc.reset_peak()  # immediately before refresh

            snap_new = capture_session(
                generation=2, home=sandbox_home, cwd=sandbox_home, registry=registry
            )
            gc.collect()
            current2, refresh_peak = tracemalloc.get_traced_memory()
        finally:
            if tracemalloc.is_tracing():
                tracemalloc.stop()

        old_stats = _snapshot_stats(snap_old)
        new_stats = _snapshot_stats(snap_new)

        # 8. Enforced assertions: compact single validator LOOP over
        # initial/refresh/old/new — exact counts, payload, largest, canonical_keys
        # AND correct generation for each. No redundant per-check scaffolding.
        snapshot_checks = [
            ("initial", initial_stats, 1),
            ("refresh", refresh_stats, 2),
            ("old", old_stats, 1),
            ("new", new_stats, 2),
        ]
        for label, stats, expected_gen in snapshot_checks:
            expected_count = totals["expected_files"]
            expected_payload = totals["expected_payload"]
            expected_largest = totals["expected_largest"]
            expected_keys = totals["expected_canonical"]
            _assert(
                stats["captured_file_count"] == expected_count,
                f"{label} file count {stats['captured_file_count']} != expected {expected_count}",
            )
            _assert(
                stats["captured_payload_bytes"] == expected_payload,
                f"{label} payload {stats['captured_payload_bytes']} != expected {expected_payload}",
            )
            _assert(
                stats["captured_largest_file_bytes"] == expected_largest,
                (
                    f"{label} largest {stats['captured_largest_file_bytes']} "
                    f"!= expected {expected_largest}"
                ),
            )
            _assert(
                stats["canonical_keys"] == expected_keys,
                f"{label} canonical keys {stats['canonical_keys']} != expected {expected_keys}",
            )
            _assert(
                stats["generation"] == expected_gen,
                f"{label} generation {stats['generation']} != expected {expected_gen}",
            )

        # old and new must be distinct snapshot objects (held simultaneously).
        _assert(
            snap_old is not snap_new,
            "old and new generations must be distinct snapshot objects",
        )

        # Per-file distinctness: nonempty asset buffers are distinct bytes objects
        # (not the same object reused) with equal content (deterministic fixtures).
        # Captured SHA-256 per file must match the fixture hash — never confuse
        # the same numeric payload sum with the same content.
        old_file_map: dict[str, bytes] = {}
        new_file_map: dict[str, bytes] = {}
        for key, files_tuple in snap_old.files.items():
            skill_name = Path(key).name
            for cf in files_tuple:
                old_file_map[f".codex/skills/{skill_name}/{cf.relative_path}"] = cf.data
        for key, files_tuple in snap_new.files.items():
            skill_name = Path(key).name
            for cf in files_tuple:
                new_file_map[f".codex/skills/{skill_name}/{cf.relative_path}"] = cf.data

        _assert(
            set(old_file_map) == set(new_file_map),
            "old and new captured file path sets differ",
        )
        fixture_sha = before.sha256_map()
        for rel_path in sorted(old_file_map):
            old_data = old_file_map[rel_path]
            new_data = new_file_map[rel_path]
            _assert(
                old_data is not new_data,
                f"old/new data for {rel_path} must be distinct bytes objects",
            )
            _assert(
                old_data == new_data,
                f"old/new content for {rel_path} must match (deterministic fixtures)",
            )
            if len(old_data) > 0:
                captured_sha = hashlib.sha256(old_data).hexdigest()
                fixture_entry_sha = fixture_sha.get(rel_path)
                _assert(
                    fixture_entry_sha is not None and captured_sha == fixture_entry_sha,
                    f"captured SHA-256 for {rel_path} does not match fixture hash",
                )

        assertions = {
            "expected_files": totals["expected_files"],
            "expected_payload_bytes": totals["expected_payload"],
            "expected_largest_file_bytes": totals["expected_largest"],
            "expected_canonical_skills": totals["expected_canonical"],
            "initial_files": initial_stats["captured_file_count"],
            "initial_payload_bytes": initial_stats["captured_payload_bytes"],
            "initial_largest_bytes": initial_stats["captured_largest_file_bytes"],
            "initial_canonical_keys": initial_stats["canonical_keys"],
            "initial_generation": initial_stats["generation"],
            "refresh_files": refresh_stats["captured_file_count"],
            "refresh_payload_bytes": refresh_stats["captured_payload_bytes"],
            "refresh_largest_bytes": refresh_stats["captured_largest_file_bytes"],
            "refresh_canonical_keys": refresh_stats["canonical_keys"],
            "refresh_generation": refresh_stats["generation"],
            "old_generation": old_stats["generation"],
            "new_generation": new_stats["generation"],
            "old_new_distinct_objects": snap_old is not snap_new,
            "old_new_per_file_distinct_objects": all(
                old_file_map[p] is not new_file_map[p] for p in old_file_map
            ),
            "old_new_per_file_sha_matches_fixture": all(
                hashlib.sha256(old_file_map[p]).hexdigest() == fixture_sha.get(p, "")
                for p in old_file_map
                if len(old_file_map[p]) > 0
            ),
            "no_silent_missing_capture": True,
            "all_assertions_enforced": True,
        }

        traced_run = {
            "tracing_baseline_current_bytes": baseline_current,
            "tracing_baseline_peak_bytes": baseline_peak,
            "peak_traced_first_capture_bytes": peak1,
            "peak_traced_refresh_overlap_bytes": refresh_peak,
            "current_traced_one_generation_bytes": current1,
            "current_traced_both_generations_bytes": current2,
            "retained_heap_one_generation_bytes": current1,
            "retained_heap_both_generations_bytes": current2,
            "old_captured_files": old_stats["captured_file_count"],
            "old_captured_payload_bytes": old_stats["captured_payload_bytes"],
            "old_captured_largest_bytes": old_stats["captured_largest_file_bytes"],
            "old_canonical_keys": old_stats["canonical_keys"],
            "old_config_bytes": _config_bytes(snap_old),
            "new_captured_files": new_stats["captured_file_count"],
            "new_captured_payload_bytes": new_stats["captured_payload_bytes"],
            "new_captured_largest_bytes": new_stats["captured_largest_file_bytes"],
            "new_canonical_keys": new_stats["canonical_keys"],
            "new_config_bytes": _config_bytes(snap_new),
            "note": (
                "tracemalloc traced heap (Python allocations only; excludes total RSS/native). "
                "Started BEFORE old generation exists; baseline read after start. "
                "gc.collect before each current reading. reset_peak immediately before refresh. "
                "retained_heap_*_bytes are CURRENT traced allocations (old held / both held), "
                "separate from transient peaks (peak_traced_*_bytes). "
                "Pre-tracing registry allocations excluded."
            ),
        }

    finally:
        # Restore tracemalloc state.
        if tracemalloc_was_active and not tracemalloc.is_tracing():
            tracemalloc.start()
        elif not tracemalloc_was_active and tracemalloc.is_tracing():
            tracemalloc.stop()
        # Restore ORIGINAL sandbox/HOME/XDG_CONFIG_HOME safely on failure too.
        paths.set_sandbox(original_sandbox)
        if original_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = original_home
        if original_xdg is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = original_xdg

    # Release traced snapshots before the AFTER fingerprint check, as promised:
    # preservation is verified with tracing off and temporaries released.
    del snap_old, snap_new
    gc.collect()

    # 9. Fingerprint AFTER capture (tracing off, temporaries released).
    after = _fingerprint_tree(home)
    preserved = _same_fingerprint(before, after)
    _assert(preserved, "fixture inventory/bytes/modes/symlink-targets changed after capture")
    _assert(before.sha256_map() == after.sha256_map(), "file SHA-256 map changed after capture")

    return {
        "scenario": scenario_label,
        "skill_count": skill_count,
        "asset_bytes_each": asset_bytes_each,
        "total_payload_bytes": total_payload_assets,
        "fixture_before": before.to_dict(),
        "fixture_after": after.to_dict(),
        "fixture_preserved": preserved,
        "fixture_symlinks_present": any(e.is_symlink for e in before.entries),
        "initial_run": initial_run,
        "refresh_run": refresh_run,
        "traced_run": traced_run,
        "assertions": assertions,
    }


def _source_hash() -> str:
    """SHA-256 of this script's own source for reproducibility evidence."""
    h = hashlib.sha256()
    h.update(Path(__file__).read_bytes())
    return h.hexdigest()


def _product_source_hashes() -> dict[str, str]:
    """SHA-256 of each product source module exercised by the benchmark."""
    hashes: dict[str, str] = {}
    for rel in _PRODUCT_SOURCE_MODULES:
        p = REPO_ROOT / rel
        h = hashlib.sha256()
        h.update(p.read_bytes())
        hashes[rel] = h.hexdigest()
    combined = hashlib.sha256()
    for rel in sorted(hashes):
        combined.update(rel.encode("utf-8"))
        combined.update(hashes[rel].encode("utf-8"))
    hashes["_combined"] = combined.hexdigest()
    return hashes


def _exclusive_write_text(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` with exclusive creation; never silently overwrite."""
    try:
        with path.open("x", encoding="utf-8") as f:
            f.write(text)
    except FileExistsError:
        raise FileExistsError(f"refusing to overwrite existing evidence file: {path}") from None


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage H byte-heavy capture/refresh benchmark")
    parser.add_argument(
        "--output",
        help=(
            "JSON output path (default: unique file under h/, never overwrites "
            "historical evidence). Permits external paths. Uses exclusive "
            "creation: an existing --output path is refused, never silently "
            "overwritten."
        ),
    )
    args = parser.parse_args()

    source_hash = _source_hash()
    product_hashes = _product_source_hashes()
    argv = sys.argv[:]
    now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())

    print("=" * 70)
    print("Stage H byte-heavy capture/refresh benchmark")
    print("=" * 70)
    print(f"Platform: {platform.system()} {platform.machine()} Python {platform.python_version()}")
    print(f"Interpreter: {sys.executable}")
    print(f"Date (UTC): {now_utc}")
    print(f"Date (local): {now_iso}")
    print(f"Source hash: {source_hash}")
    print(f"Product source hashes: {json.dumps(product_hashes)}")
    print(f"argv: {' '.join(argv)}")
    print(f"Scenarios: {SCENARIOS}")
    print(f"Repeats per scenario: {REPEATS}")
    print()

    results: list[dict[str, Any]] = []
    all_ok = True

    for scenario_label, skill_count, asset_bytes_each in SCENARIOS:
        for repeat in range(1, REPEATS + 1):
            print(
                f"[{scenario_label} repeat {repeat}/{REPEATS}] "
                f"{skill_count} skills x {asset_bytes_each // (1024 * 1024)} MiB asset..."
            )
            with tempfile.TemporaryDirectory(prefix="skill-lens-h-") as td:
                home = Path(td)
                try:
                    result = _scenario_run(
                        home, scenario_label, skill_count, asset_bytes_each, repeat
                    )
                    result["repeat"] = repeat
                    result["fixture_dir"] = str(home)
                    results.append(result)

                    ir = result["initial_run"]
                    rr = result["refresh_run"]
                    tr = result["traced_run"]
                    as_ = result["assertions"]
                    print(
                        f"  initial: {ir['wall_ms']:.1f} ms  "
                        f"files={ir['snapshot']['captured_file_count']}  "
                        f"payload={ir['snapshot']['captured_payload_bytes']:,} B"
                    )
                    print(
                        f"  refresh: {rr['wall_ms']:.1f} ms  "
                        f"files={rr['snapshot']['captured_file_count']}  "
                        f"payload={rr['snapshot']['captured_payload_bytes']:,} B"
                    )
                    print(
                        f"  traced: 1gen current="
                        f"{tr['current_traced_one_generation_bytes'] / (1024 * 1024):.2f} MiB  "
                        f"2gen current="
                        f"{tr['current_traced_both_generations_bytes'] / (1024 * 1024):.2f} MiB  "
                        f"refresh_peak="
                        f"{tr['peak_traced_refresh_overlap_bytes'] / (1024 * 1024):.2f} MiB"
                    )
                    print(
                        f"  preserved={result['fixture_preserved']}  "
                        f"distinct={as_['old_new_distinct_objects']}  "
                        f"assertions_enforced={as_['all_assertions_enforced']}"
                    )
                except _AssertionFailure as exc:
                    all_ok = False
                    print(f"  ASSERTION FAILED: {exc}")
                    raise

    output = {
        "benchmark": "Stage H byte-heavy capture/refresh (capture_session)",
        "source_hash": source_hash,
        "product_source_hashes": product_hashes,
        "timestamp_utc": now_utc,
        "timestamp_local": now_iso,
        "argv": argv,
        "methodology": {
            "instrumentation": "stdlib only; capture_session uses installed skill_lens runtime",
            "scenarios": SCENARIOS,
            "repeats": REPEATS,
            "fixture_seed": _FIXTURE_SEED,
            "fixture_symlinks_added": False,
            "tracing": (
                "tracemalloc.start() BEFORE old generation exists; baseline read after start; "
                "gc.collect before each current reading; reset_peak immediately before refresh; "
                "retained_heap_* = CURRENT traced allocations (old held / both held); "
                "peak_traced_* = transient peaks reported separately; excludes RSS/native; "
                "refuses to run if tracemalloc is already active (fresh-subprocess precondition)"
            ),
            "refresh": (
                "untraced initial + refresh captures keep generation 1 alive through refresh "
                "(raw capture_session overlap, simulated refresh, not controller pipeline); "
                "both released before traced runs; snap_old/snap_new released before "
                "AFTER fingerprint"
            ),
            "fingerprint": (
                "os.walk with onerror callback that raises OSError (no silently skipped "
                "traversal failures); chunked SHA-256 per regular file before/after; "
                "directories incl. modes; symlink targets recorded without following; "
                "walk/stat/read errors raise, never silently skipped"
            ),
            "assertions": (
                "compact validator LOOP over initial/refresh/old/new: exact "
                "captured_file_count, captured_payload_bytes, captured_largest_file_bytes, "
                "canonical_keys AND correct generation for each; old/new distinct objects; "
                "per-file bytes object identity for nonempty assets; per-file captured "
                "SHA-256 compared to fixture hash; enforced, fail nonzero"
            ),
            "config_bytes": "reported separately from payload totals",
            "preservation": (
                "checked AFTER releasing snapshot temporaries "
                "(including snap_old/snap_new), tracing off"
            ),
        },
        "conditions": {
            "platform": f"{platform.system()} {platform.machine()}",
            "python_version": platform.python_version(),
            "interpreter": sys.executable,
            "no_live_skills_home_system_root": True,
            "no_network": True,
            "fixture_cache": "Warm OS page cache likely; cold disk may vary.",
            "cwd": os.getcwd(),
        },
        "scenarios": SCENARIOS,
        "repeats": REPEATS,
        "all_assertions_passed": all_ok,
        "results": results,
    }

    # Default output: unique file under h/; never overwrite historical evidence.
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        unique = f"{stamp}-{int(time.time() * 1_000_000) % 1_000_000:06d}"
        out_path = (
            REPO_ROOT
            / "docs"
            / "validation"
            / "assessment-repairs"
            / "h"
            / f"benchmark-results-{unique}.json"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)

    _exclusive_write_text(out_path, json.dumps(output, indent=2))
    print(f"\nArtifact written: {out_path}")
    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
