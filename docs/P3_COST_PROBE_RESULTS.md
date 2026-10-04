# P3 Cost and Capture-Scope Probe Results

> **Specification Reference:** `FULL_SCREEN_TUI.md` §9.2 and §22 (Assignment P3).
> **Run Date:** 2026-10-04 20:19:59
> **Environment:** Python 3.11.16 on Darwin arm64.

## 1. Synthetic Fixture Profiles

| Metric | Scenario A (Mostly Unique) | Scenario B (Heavily Duplicated) |
| --- | --- | --- |
| Discovered Skill Entries | 651 | 615 |
| Valid / Malformed / Symlinks | 601 valid, 20 malformed, 30 symlinks | 600 valid, 15 malformed, 0 symlinks |
| Total Files on Disk | 775 | 1001 |
| Total Size on Disk | 1.08 MiB | 1.98 MiB |
| Largest File Size | 50.00 KiB | 80.00 KiB |
| Filesystem State | Freshly written to temporary directory on local disk; resident in OS page cache | Freshly written to temporary directory on local disk; resident in OS page cache |
| Composition Details | 500 shared, 50 Claude, 50 Codex, 30 Pi symlinks, 20 malformed, binary assets, 1 verified malformed-diff case | 200 distinct skill names x 3 roots = 600 copies + 15 malformed, binary assets |

## 2. Separate Measured Phases (Timings)

| Phase | Scenario A | Scenario B | Description / Status |
| --- | --- | --- | --- |
| 1. First Discovery (Live Walk + Hashes) | 1245.03 ms (1.245 s) | 731.20 ms (0.731 s) | Full walk and streaming SHA-256 calculation |
| 2. Byte Capture (Full Q9) | 62.39 ms (0.062 s) | 77.88 ms (0.078 s) | Reads all file bytes for all discovered entries |
| 3. Second Discovery (Validation Pass) | 1208.87 ms (1.209 s) | 680.45 ms (0.680 s) | Reruns live discovery to verify file stability |
| 4. Report Construction | 63.95 ms (0.064 s) | 54.67 ms (0.055 s) | `build_scan_report` & `build_doctor_report` reusing index & registry |
| 5. Validation Work | 62.24 ms (0.062 s) | 55.60 ms (0.056 s) | Compares discovery passes, reports and configs |
| *(Unavailable Service Phases)* | *N/A (C3)* | *N/A (C3)* | In-memory cancellation checkpoints, `display_paths` & `same_locations` |
| **Total Startup (Probe Estimate)** | **2642.48 ms (2.642 s)** | **1599.80 ms (1.600 s)** | Sum of measured phases 1 + 2 + 3 + 4 + 5 |

### Selective-Retention Comparison (Candidate)

| Candidate Metric | Scenario A | Scenario B | Notes |
| --- | --- | --- | --- |
| Selective Byte Capture Time | 39.98 ms (0.040 s) | 74.89 ms (0.075 s) | Retains support files only for differing Diff candidates |
| Capture Time Difference | -22.4 ms | -3.0 ms | Signed difference vs full capture (negative = faster) |
| Malformed-Diff Rule Verified | YES | N/A | Diff engine's Variant A baseline & readable-copy rules verified |

## 3. Precise Memory & Allocation Measurements

> **Note on Allocation Labels:** `tracemalloc` measures peak heap allocations tracked by the Python runtime for the monitored block. It does not represent total OS process memory (Resident Set Size). Content bytes and container overheads are measured directly via Python data lengths and `sys.getsizeof`.

| Memory Metric | Scenario A | Scenario B | Description |
| --- | --- | --- | --- |
| Retained File Content Bytes | 1.07 MiB | 1.98 MiB | Exact sum of in-memory file byte buffers |
| Retained Container Overhead | 108.39 KiB | 120.23 KiB | Overhead of mapping dicts and file tuples |
| **Total Retained Snapshot Data** | **1.18 MiB** | **2.10 MiB** | Sum of file bytes and container overhead |
| Selective Candidate Retained Data | 208.65 KiB | 2.00 MiB | Skips support assets for identical/isolated copies |
| Peak Traced: First Discovery | 4.12 MiB | 2.45 MiB | Traced Python heap during initial discovery |
| Peak Traced: Full Byte Capture | 1.22 MiB | 2.15 MiB | Traced Python heap during full byte reading |
| Peak Traced: Reports Construction | 278.74 KiB | 274.34 KiB | Traced Python heap during scan & doctor build |
| Peak Traced: Validation Pass | 278.67 KiB | 274.74 KiB | Traced Python heap during consistency checks |
| **Peak Traced: Simulated Refresh** | **11.04 MiB** | **10.48 MiB** | Peak traced heap while holding old snapshot and building new |

## 4. Architectural Analysis & Decision Record

### 4.1 Probe Findings
1. **Full Capture Time:** Reading all file bytes across 600+ skills requires only **~62.4 ms (Scenario A)** and **~77.9 ms (Scenario B)**.
2. **Total Startup Estimate:** The sum of all five measured startup phases is **~2.64 s (Scenario A)** and **~1.60 s (Scenario B)** on Darwin arm64. Passing the existing index and registry into `build_doctor_report` eliminates the redundant discovery walk.
3. **In-Memory Retention:** Total in-memory storage for all captured files and containers is **1.18 MiB (Scenario A)** and **2.10 MiB (Scenario B)**.
4. **Refresh Memory:** Tracking heap allocations from start through retaining the entire old snapshot and constructing the replacement snapshot with freshly read bytes peaked at **11.04 MiB (Scenario A)** and **10.48 MiB (Scenario B)** of traced allocations.
5. **Selective Retention Evaluation:** Selective retention saves only ~22.4 ms of capture time. Furthermore, to adhere to the Diff engine's Variant A baseline and readable-copy rules (where readable malformed copies with differing support files must be diffed), selective retention must retain support files for those malformed copies as verified in Scenario A. The minor memory reduction does not justify the added state complexity.

### 4.2 Decision Gate
- **Decision:** **Retain §21 Full Capture specification verbatim.**
- **Rationale:** Full capture provides 100% frozen inputs with zero live disk access during navigation, consumes under 3 MiB of retained data for 600+ skills, and introduces no fragile conditional caching logic.

---
*Report generated by `docs/p3_cost_probe.py`.*
