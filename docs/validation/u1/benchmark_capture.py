#!/usr/bin/env python3
"""U1 Step 1 Capture Benchmark: Real capture_session measurement against P3 fixtures.

Measures actual capture_session performance on Scenario A (mostly unique)
and Scenario B (heavily duplicated) by reusing the original fixture generators
from docs/p3_cost_probe.py loaded by path.

Instruments actual snapshot module call boundaries:
- Discovery pass 1 (live_discovery)
- Configuration reads (_read_input_guarded)
- Build scan report (build_scan_report)
- Run doctor (run_doctor)
- Collect display paths (_collect_display_paths_and_locations)
- Discovery pass 2 (live_discovery validation)
- Honest derived residual (total wall-clock minus hook timers)

Memory tracking:
- Traces heap allocations starting BEFORE old snapshot allocation through retaining
  old snapshot and capturing new snapshot (measuring real refresh peak).
- Reports retained file buffers and selected containers as partial memory only.
- Records machine-readable raw runs and execution conditions.
"""

from __future__ import annotations

import gc
import importlib.util
import json
import platform
import sys
import tempfile
import time
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skill_lens.core import paths, snapshot  # noqa: E402
from skill_lens.core.snapshot import SessionSnapshot, capture_session  # noqa: E402

# Load original fixture generators from docs/p3_cost_probe.py by path
p3_path = REPO_ROOT / "docs" / "p3_cost_probe.py"
spec = importlib.util.spec_from_file_location("p3_cost_probe", p3_path)
assert spec is not None and spec.loader is not None
p3_mod = importlib.util.module_from_spec(spec)
sys.modules["p3_cost_probe"] = p3_mod
spec.loader.exec_module(p3_mod)

generate_scenario_a = p3_mod.generate_scenario_a
generate_scenario_b = p3_mod.generate_scenario_b


@dataclass
class DatasetMetrics:
    total_files: int
    total_bytes: int
    largest_file_bytes: int


def _inspect_dataset(home: Path) -> DatasetMetrics:
    total_files = 0
    total_bytes = 0
    largest_file = 0
    for p in home.rglob("*"):
        if p.is_file() and not p.is_symlink():
            sz = p.stat().st_size
            total_files += 1
            total_bytes += sz
            if sz > largest_file:
                largest_file = sz
    return DatasetMetrics(
        total_files=total_files,
        total_bytes=total_bytes,
        largest_file_bytes=largest_file,
    )


@dataclass
class InstrumentedPhases:
    discovery_1_ms: float
    config_reads_ms: float
    scan_report_ms: float
    doctor_report_ms: float
    display_locations_ms: float
    discovery_2_ms: float
    unattributed_residual_ms: float
    total_wall_ms: float


@dataclass
class BenchmarkScenarioResult:
    scenario: str
    dataset: dict[str, Any]
    canonical_skills: int
    total_entrypoints: int
    clean_run_tracing_off: dict[str, Any]
    memory_run_tracing_on: dict[str, Any]
    retained_partial_memory: dict[str, Any]


def _measure_instrumented_capture(home: Path) -> tuple[SessionSnapshot, InstrumentedPhases]:
    """Execute capture_session while recording timers at actual module call boundaries."""
    orig_live_discovery = snapshot.live_discovery
    orig_read_guarded = snapshot._read_input_guarded
    orig_build_scan = snapshot.build_scan_report
    orig_run_doctor = snapshot.run_doctor
    orig_display_locations = snapshot._collect_display_paths_and_locations

    discovery_times: list[float] = []
    config_read_time = 0.0
    scan_report_time = 0.0
    doctor_report_time = 0.0
    display_locations_time = 0.0

    def timed_live_discovery(*args: Any, **kwargs: Any) -> Any:
        t0 = time.perf_counter()
        res = orig_live_discovery(*args, **kwargs)
        discovery_times.append((time.perf_counter() - t0) * 1000)
        return res

    def timed_read_guarded(*args: Any, **kwargs: Any) -> Any:
        nonlocal config_read_time
        t0 = time.perf_counter()
        res = orig_read_guarded(*args, **kwargs)
        config_read_time += (time.perf_counter() - t0) * 1000
        return res

    def timed_build_scan(*args: Any, **kwargs: Any) -> Any:
        nonlocal scan_report_time
        t0 = time.perf_counter()
        res = orig_build_scan(*args, **kwargs)
        scan_report_time += (time.perf_counter() - t0) * 1000
        return res

    def timed_run_doctor(*args: Any, **kwargs: Any) -> Any:
        nonlocal doctor_report_time
        t0 = time.perf_counter()
        res = orig_run_doctor(*args, **kwargs)
        doctor_report_time += (time.perf_counter() - t0) * 1000
        return res

    def timed_display_locations(*args: Any, **kwargs: Any) -> Any:
        nonlocal display_locations_time
        t0 = time.perf_counter()
        res = orig_display_locations(*args, **kwargs)
        display_locations_time += (time.perf_counter() - t0) * 1000
        return res

    snapshot.live_discovery = timed_live_discovery
    snapshot._read_input_guarded = timed_read_guarded
    snapshot.build_scan_report = timed_build_scan
    snapshot.run_doctor = timed_run_doctor
    snapshot._collect_display_paths_and_locations = timed_display_locations

    try:
        gc.collect()
        t_start = time.perf_counter()
        snap = capture_session(generation=1, home=home, cwd=home)
        t_total = (time.perf_counter() - t_start) * 1000
    finally:
        snapshot.live_discovery = orig_live_discovery
        snapshot._read_input_guarded = orig_read_guarded
        snapshot.build_scan_report = orig_build_scan
        snapshot.run_doctor = orig_run_doctor
        snapshot._collect_display_paths_and_locations = orig_display_locations

    d1 = discovery_times[0] if len(discovery_times) > 0 else 0.0
    d2 = discovery_times[1] if len(discovery_times) > 1 else 0.0
    instrumented_sum = (
        d1 + config_read_time + scan_report_time + doctor_report_time + display_locations_time + d2
    )
    residual = max(0.0, t_total - instrumented_sum)

    phases = InstrumentedPhases(
        discovery_1_ms=d1,
        config_reads_ms=config_read_time,
        scan_report_ms=scan_report_time,
        doctor_report_ms=doctor_report_time,
        display_locations_ms=display_locations_time,
        discovery_2_ms=d2,
        unattributed_residual_ms=residual,
        total_wall_ms=t_total,
    )
    return snap, phases


def run_benchmark(generator: Any, scenario_label: str) -> BenchmarkScenarioResult:
    with tempfile.TemporaryDirectory() as td:
        home = Path(td)
        paths.set_sandbox(home)
        try:
            # 1. Generate scenario using original P3 fixture generator
            generator(home)
            ds_metrics = _inspect_dataset(home)

            # 2. Clean timing run with tracing OFF
            snap_clean, clean_phases = _measure_instrumented_capture(home)

            # 3. Retained partial memory calculation
            retained_payload_bytes = 0
            container_bytes = sys.getsizeof(snap_clean.files)
            for key, files_tuple in snap_clean.files.items():
                container_bytes += sys.getsizeof(key)
                container_bytes += sys.getsizeof(files_tuple)
                for cf in files_tuple:
                    container_bytes += sys.getsizeof(cf)
                    retained_payload_bytes += len(cf.data)

            # 4. Traced memory run with tracemalloc ON
            # Start tracing BEFORE old snapshot allocation, retain snap1 while capturing snap2
            gc.collect()
            tracemalloc.start()
            snap_old = capture_session(generation=1, home=home, cwd=home)
            _, peak_first_capture = tracemalloc.get_traced_memory()

            # Hold snap_old while capturing snap_new (simulated refresh)
            snap_new = capture_session(generation=2, home=home, cwd=home)
            _, peak_simulated_refresh = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Retain reference to prevent premature GC before get_traced_memory
            assert snap_old is not None and snap_new is not None

            canonical_skills = len(snap_clean.index.entries)
            total_entrypoints = sum(len(e.entrypoint_paths) for e in snap_clean.index.entries)

            return BenchmarkScenarioResult(
                scenario=scenario_label,
                dataset=asdict(ds_metrics),
                canonical_skills=canonical_skills,
                total_entrypoints=total_entrypoints,
                clean_run_tracing_off=asdict(clean_phases),
                memory_run_tracing_on={
                    "peak_traced_first_capture_bytes": peak_first_capture,
                    "peak_traced_simulated_refresh_bytes": peak_simulated_refresh,
                },
                retained_partial_memory={
                    "retained_file_payload_bytes": retained_payload_bytes,
                    "retained_selected_containers_bytes": container_bytes,
                    "retained_partial_total_bytes": retained_payload_bytes + container_bytes,
                    "note": (
                        "Partial memory only: measures retained file bytes and selected container "
                        "dictionaries/tuples, excluding full Python object graphs and snapshot "
                        "metadata."
                    ),
                },
            )
        finally:
            paths.set_sandbox(None)


def main() -> None:
    print("=" * 70)
    print("Skill Lens U1 Step 1 Capture Benchmark (Real capture_session)")
    print("=" * 70)
    print(f"Platform: {platform.system()} {platform.machine()} Python {platform.python_version()}")

    print("\n[1/2] Benchmarking Scenario A (Mostly Unique, 600+ skills)...")
    res_a = run_benchmark(generate_scenario_a, "Scenario A (Mostly Unique)")
    print(f"  Complete capture: {res_a.clean_run_tracing_off['total_wall_ms']:.2f} ms")
    print(f"  Discovery 1: {res_a.clean_run_tracing_off['discovery_1_ms']:.2f} ms")
    print(f"  Discovery 2: {res_a.clean_run_tracing_off['discovery_2_ms']:.2f} ms")
    res_a_res = res_a.clean_run_tracing_off["unattributed_residual_ms"]
    print(f"  Derived residual: {res_a_res:.2f} ms")
    peak_a_mib = res_a.memory_run_tracing_on["peak_traced_simulated_refresh_bytes"] / (1024 * 1024)
    print(f"  Simulated refresh peak heap: {peak_a_mib:.2f} MiB")

    print("\n[2/2] Benchmarking Scenario B (Heavily Duplicated, 600+ skills)...")
    res_b = run_benchmark(generate_scenario_b, "Scenario B (Heavily Duplicated)")
    print(f"  Complete capture: {res_b.clean_run_tracing_off['total_wall_ms']:.2f} ms")
    print(f"  Discovery 1: {res_b.clean_run_tracing_off['discovery_1_ms']:.2f} ms")
    print(f"  Discovery 2: {res_b.clean_run_tracing_off['discovery_2_ms']:.2f} ms")
    res_b_res = res_b.clean_run_tracing_off["unattributed_residual_ms"]
    print(f"  Derived residual: {res_b_res:.2f} ms")
    peak_b_mib = res_b.memory_run_tracing_on["peak_traced_simulated_refresh_bytes"] / (1024 * 1024)
    print(f"  Simulated refresh peak heap: {peak_b_mib:.2f} MiB")

    # Machine-readable output
    artifacts_dir = REPO_ROOT / "docs" / "validation" / "u1"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    raw_path = artifacts_dir / "benchmark_raw.json"

    raw_data = {
        "benchmark": "U1 Step 1 capture_session empirical measurement",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "conditions": {
            "platform": f"{platform.system()} {platform.machine()}",
            "python_version": platform.python_version(),
            "filesystem_cache": (
                "Warm operating system page cache likely; cold disk performance may vary."
            ),
            "comparison_caveat": (
                "P3 cost probe used simulated components with different tracing modes; "
                "timings cannot imply speed improvement across differing environments "
                "or tracing configurations."
            ),
        },
        "scenarios": [asdict(res_a), asdict(res_b)],
    }
    raw_path.write_text(json.dumps(raw_data, indent=2), encoding="utf-8")

    ds_a_files = res_a.dataset["total_files"]
    ds_a_mib = res_a.dataset["total_bytes"] / (1024 * 1024)
    ds_a_max_kib = res_a.dataset["largest_file_bytes"] / 1024
    wall_a = res_a.clean_run_tracing_off["total_wall_ms"]
    d1_a = res_a.clean_run_tracing_off["discovery_1_ms"]
    cfg_a = res_a.clean_run_tracing_off["config_reads_ms"]
    scan_a = res_a.clean_run_tracing_off["scan_report_ms"]
    doc_a = res_a.clean_run_tracing_off["doctor_report_ms"]
    disp_a = res_a.clean_run_tracing_off["display_locations_ms"]
    d2_a = res_a.clean_run_tracing_off["discovery_2_ms"]
    pay_a = res_a.retained_partial_memory["retained_file_payload_bytes"] / (1024 * 1024)
    cnt_a = res_a.retained_partial_memory["retained_selected_containers_bytes"] / 1024
    tot_a = res_a.retained_partial_memory["retained_partial_total_bytes"] / (1024 * 1024)
    first_a = res_a.memory_run_tracing_on["peak_traced_first_capture_bytes"] / (1024 * 1024)
    ref_a = res_a.memory_run_tracing_on["peak_traced_simulated_refresh_bytes"] / (1024 * 1024)

    ds_b_files = res_b.dataset["total_files"]
    ds_b_mib = res_b.dataset["total_bytes"] / (1024 * 1024)
    ds_b_max_kib = res_b.dataset["largest_file_bytes"] / 1024
    wall_b = res_b.clean_run_tracing_off["total_wall_ms"]
    d1_b = res_b.clean_run_tracing_off["discovery_1_ms"]
    cfg_b = res_b.clean_run_tracing_off["config_reads_ms"]
    scan_b = res_b.clean_run_tracing_off["scan_report_ms"]
    doc_b = res_b.clean_run_tracing_off["doctor_report_ms"]
    disp_b = res_b.clean_run_tracing_off["display_locations_ms"]
    d2_b = res_b.clean_run_tracing_off["discovery_2_ms"]
    pay_b = res_b.retained_partial_memory["retained_file_payload_bytes"] / (1024 * 1024)
    cnt_b = res_b.retained_partial_memory["retained_selected_containers_bytes"] / 1024
    tot_b = res_b.retained_partial_memory["retained_partial_total_bytes"] / (1024 * 1024)
    first_b = res_b.memory_run_tracing_on["peak_traced_first_capture_bytes"] / (1024 * 1024)
    ref_b = res_b.memory_run_tracing_on["peak_traced_simulated_refresh_bytes"] / (1024 * 1024)

    # Markdown report
    md_content = f"""# U1 Step 1 Capture Benchmark Results

Measured empirical performance of real `capture_session()` across P3 synthetic
datasets (Scenario A and Scenario B), reusing original fixture constructors
from `docs/p3_cost_probe.py` loaded by path.

- **Platform:** {raw_data["conditions"]["platform"]}
- **Python:** {raw_data["conditions"]["python_version"]}
- **Cache Conditions:** {raw_data["conditions"]["filesystem_cache"]}
- **Comparison Caveat:** {raw_data["conditions"]["comparison_caveat"]}

---

## 1. Scenario A: Mostly Unique Skills (621 Canonical, 651 Entrypoints)

- **Dataset:** {ds_a_files} files, {ds_a_mib:.2f} MiB (largest file: {ds_a_max_kib:.1f} KiB)
- **Complete `capture_session()` Wall-Clock:** **{wall_a:.2f} ms** (tracing OFF)

### Component Timings (Measured at Call Boundaries)

| Phase | Call Boundary | Time (ms) |
| --- | --- | ---: |
| Discovery pass 1 | `live_discovery` | {d1_a:.2f} |
| Config reads | `_read_input_guarded` | {cfg_a:.2f} |
| Scan report | `build_scan_report` | {scan_a:.2f} |
| Doctor report | `run_doctor` | {doc_a:.2f} |
| Display paths | `_collect_display_paths_and_locations` | {disp_a:.2f} |
| Discovery pass 2 | `live_discovery` (validation) | {d2_a:.2f} |
| **Unattributed residual (derived)** | File reads, hashing, reparse | **{res_a_res:.2f}** |

*Note: The unattributed residual is derived honestly as total wall-clock
minus the sum of hook timers (file reads, hashing, reparse, and validation loop).*

### Memory Tracking

- **Retained File Payload:** {pay_a:.2f} MiB
- **Retained Selected Containers:** {cnt_a:.1f} KiB
- **Retained Partial Memory Total:** **{tot_a:.2f} MiB**
  *(Partial memory only: measures retained file buffers and selected containers).*
- **First Capture Peak Traced Heap:** **{first_a:.2f} MiB**
- **Simulated Refresh Peak Traced Heap:** **{ref_a:.2f} MiB**
  *(Tracing started BEFORE old snapshot capture, holding old snapshot in memory throughout).*

---

## 2. Scenario B: Heavily Duplicated Skills (615 Canonical, 615 Entrypoints)

- **Dataset:** {ds_b_files} files, {ds_b_mib:.2f} MiB (largest file: {ds_b_max_kib:.1f} KiB)
- **Complete `capture_session()` Wall-Clock:** **{wall_b:.2f} ms** (tracing OFF)

### Component Timings (Measured at Call Boundaries)

| Phase | Call Boundary | Time (ms) |
| --- | --- | ---: |
| Discovery pass 1 | `live_discovery` | {d1_b:.2f} |
| Config reads | `_read_input_guarded` | {cfg_b:.2f} |
| Scan report | `build_scan_report` | {scan_b:.2f} |
| Doctor report | `run_doctor` | {doc_b:.2f} |
| Display paths | `_collect_display_paths_and_locations` | {disp_b:.2f} |
| Discovery pass 2 | `live_discovery` (validation) | {d2_b:.2f} |
| **Unattributed residual (derived)** | File reads, hashing, reparse | **{res_b_res:.2f}** |

*Note: The unattributed residual is derived honestly as total wall-clock
minus the sum of hook timers (file reads, hashing, reparse, and validation loop).*

### Memory Tracking

- **Retained File Payload:** {pay_b:.2f} MiB
- **Retained Selected Containers:** {cnt_b:.1f} KiB
- **Retained Partial Memory Total:** **{tot_b:.2f} MiB**
  *(Partial memory only: measures retained file buffers and selected containers).*
- **First Capture Peak Traced Heap:** **{first_b:.2f} MiB**
- **Simulated Refresh Peak Traced Heap:** **{ref_b:.2f} MiB**
  *(Tracing started BEFORE old snapshot capture, holding old snapshot in memory throughout).*

---

## 3. Comparison Context with Original P3 Probe Results

Original baseline figures recorded in
[docs/P3_COST_PROBE_RESULTS.md](../../P3_COST_PROBE_RESULTS.md)
(recorded 2026-10-04 on Python 3.11.16 on Darwin arm64) vs real U1 `capture_session()`
measurements (Python {platform.python_version()} on {platform.system()} {platform.machine()}):

| Metric | Scen. A (P3) | Scen. A (U1) | Scen. B (P3) | Scen. B (U1) |
| --- | ---: | ---: | ---: | ---: |
| Startup / Capture Time | 3252.74 ms | {wall_a:.2f} ms | 1593.33 ms | {wall_b:.2f} ms |
| Retained File Payload | 1.07 MiB | {pay_a:.2f} MiB | 1.98 MiB | {pay_b:.2f} MiB |
| Payload + Selected Containers | 1.18 MiB | {tot_a:.2f} MiB | 2.10 MiB | {tot_b:.2f} MiB |
| Refresh Peak Traced Heap | 11.30 MiB | {ref_a:.2f} MiB | 10.75 MiB | {ref_b:.2f} MiB |

> [!NOTE]
> **Measurement & Environment Caveat:** The original P3 probe
> ([docs/P3_COST_PROBE_RESULTS.md](../../P3_COST_PROBE_RESULTS.md)) evaluated simulated
> individual service phases on Python 3.11.16 with separate component timers. The U1 capture
> benchmark measures the real unified `capture_session()` implementation. Differing Python
> versions, runtime environments, OS page cache warmup, and tracing overhead mean timings reflect
> different measurement regimes and cannot imply a direct algorithmic speedup.
"""
    (artifacts_dir / "BENCHMARK_RESULTS.md").write_text(md_content, encoding="utf-8")
    rel_raw = raw_path.relative_to(REPO_ROOT)
    rel_md = (artifacts_dir / "BENCHMARK_RESULTS.md").relative_to(REPO_ROOT)
    print(f"\nArtifacts generated:\n  {rel_raw}\n  {rel_md}")


if __name__ == "__main__":
    main()
