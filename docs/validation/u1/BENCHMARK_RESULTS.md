# U1 Step 1 Capture Benchmark Results

Measured empirical performance of real `capture_session()` across P3 synthetic
datasets (Scenario A and Scenario B), reusing original fixture constructors
from `docs/p3_cost_probe.py` loaded by path.

- **Platform:** Darwin arm64
- **Python:** 3.11.16
- **Cache Conditions:** Warm operating system page cache likely; cold disk performance may vary.
- **Comparison Caveat:** P3 cost probe used simulated components with different tracing modes; timings cannot imply speed improvement across differing environments or tracing configurations.

---

## 1. Scenario A: Mostly Unique Skills (621 Canonical, 651 Entrypoints)

- **Dataset:** 775 files, 1.08 MiB (largest file: 50.0 KiB)
- **Complete `capture_session()` Wall-Clock:** **991.39 ms** (tracing OFF)

### Component Timings (Measured at Call Boundaries)

| Phase | Call Boundary | Time (ms) |
| --- | --- | ---: |
| Discovery pass 1 | `live_discovery` | 392.38 |
| Config reads | `_read_input_guarded` | 0.33 |
| Scan report | `build_scan_report` | 7.24 |
| Doctor report | `run_doctor` | 11.52 |
| Display paths | `_collect_display_paths_and_locations` | 95.25 |
| Discovery pass 2 | `live_discovery` (validation) | 390.78 |
| **Unattributed residual (derived)** | File reads, hashing, reparse | **93.91** |

*Note: The unattributed residual is derived honestly as total wall-clock
minus the sum of hook timers (file reads, hashing, reparse, and validation loop).*

### Memory Tracking

- **Retained File Payload:** 1.07 MiB
- **Retained Selected Containers:** 166.8 KiB
- **Retained Partial Memory Total:** **1.24 MiB**
  *(Partial memory only: measures retained file buffers and selected containers).*
- **First Capture Peak Traced Heap:** **7.03 MiB**
- **Simulated Refresh Peak Traced Heap:** **9.98 MiB**
  *(Tracing started BEFORE old snapshot capture, holding old snapshot in memory throughout).*

---

## 2. Scenario B: Heavily Duplicated Skills (615 Canonical, 615 Entrypoints)

- **Dataset:** 1001 files, 1.98 MiB (largest file: 80.0 KiB)
- **Complete `capture_session()` Wall-Clock:** **681.82 ms** (tracing OFF)

### Component Timings (Measured at Call Boundaries)

| Phase | Call Boundary | Time (ms) |
| --- | --- | ---: |
| Discovery pass 1 | `live_discovery` | 242.39 |
| Config reads | `_read_input_guarded` | 0.11 |
| Scan report | `build_scan_report` | 7.35 |
| Doctor report | `run_doctor` | 9.84 |
| Display paths | `_collect_display_paths_and_locations` | 89.91 |
| Discovery pass 2 | `live_discovery` (validation) | 237.01 |
| **Unattributed residual (derived)** | File reads, hashing, reparse | **95.21** |

*Note: The unattributed residual is derived honestly as total wall-clock
minus the sum of hook timers (file reads, hashing, reparse, and validation loop).*

### Memory Tracking

- **Retained File Payload:** 1.98 MiB
- **Retained Selected Containers:** 180.0 KiB
- **Retained Partial Memory Total:** **2.16 MiB**
  *(Partial memory only: measures retained file buffers and selected containers).*
- **First Capture Peak Traced Heap:** **6.11 MiB**
- **Simulated Refresh Peak Traced Heap:** **9.75 MiB**
  *(Tracing started BEFORE old snapshot capture, holding old snapshot in memory throughout).*

---

## 3. Comparison Context with Original P3 Probe Results

Original baseline figures recorded in
[docs/P3_COST_PROBE_RESULTS.md](../../P3_COST_PROBE_RESULTS.md)
(recorded 2026-10-04 on Python 3.11.16 on Darwin arm64) vs real U1 `capture_session()`
measurements (Python 3.11.16 on Darwin arm64):

| Metric | Scen. A (P3) | Scen. A (U1) | Scen. B (P3) | Scen. B (U1) |
| --- | ---: | ---: | ---: | ---: |
| Startup / Capture Time | 3252.74 ms | 991.39 ms | 1593.33 ms | 681.82 ms |
| Retained File Payload | 1.07 MiB | 1.07 MiB | 1.98 MiB | 1.98 MiB |
| Payload + Selected Containers | 1.18 MiB | 1.24 MiB | 2.10 MiB | 2.16 MiB |
| Refresh Peak Traced Heap | 11.30 MiB | 9.98 MiB | 10.75 MiB | 9.75 MiB |

> [!NOTE]
> **Measurement & Environment Caveat:** The original P3 probe
> ([docs/P3_COST_PROBE_RESULTS.md](../../P3_COST_PROBE_RESULTS.md)) evaluated simulated
> individual service phases on Python 3.11.16 with separate component timers. The U1 capture
> benchmark measures the real unified `capture_session()` implementation. Differing Python
> versions, runtime environments, OS page cache warmup, and tracing overhead mean timings reflect
> different measurement regimes and cannot imply a direct algorithmic speedup.
