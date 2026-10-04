# P3 Cost and Capture-Scope Probe Results

> **Specification Reference:** `FULL_SCREEN_TUI.md` §9.2 and §22 (Assignment P3).
> **Run Date:** 2026-10-04 20:41:06
> **Environment:** Python 3.11.16 on Darwin arm64.

## 1. Synthetic Fixture Profiles

| Metric | Scenario A (Mostly Unique) | Scenario B (Heavily Duplicated) |
| --- | --- | --- |
| Discovered Skill Entries | 621 canonical entries + 30 symlink entrypoints (651 total entrypoints) | 615 canonical entries + 0 symlink entrypoints (615 total entrypoints) |
| Valid / Malformed / Symlinks | 601 valid, 20 malformed, 30 symlinks (621 canonical entries) | 600 valid, 15 malformed, 0 symlinks (615 canonical entries) |
| Total Files on Disk | 775 | 1001 |
| Total Size on Disk | 1.08 MiB | 1.98 MiB |
| Largest File Size | 50.00 KiB | 80.00 KiB |
| Filesystem State | Freshly written to temporary directory on local disk; resident in OS page cache | Freshly written to temporary directory on local disk; resident in OS page cache |
| Composition Details | 500 shared, 50 Claude, 50 Codex, 30 Pi symlinks, 20 malformed, binary assets, 1 verified malformed-diff case | 200 distinct skill names x 3 roots = 600 copies + 15 malformed, binary assets |

## 2. Separate Measured Phases (Timings)

| Phase | Scenario A | Scenario B | Description / Status |
| --- | --- | --- | --- |
| 1. First Discovery (Live Walk + Hashes) | 1455.81 ms (1.456 s) | 701.63 ms (0.702 s) | Full walk and streaming SHA-256 calculation |
| 2. Byte Capture (Full Q9) | 68.48 ms (0.068 s) | 76.87 ms (0.077 s) | Reads all file bytes for all discovered entries |
| 3. Second Discovery (Validation Pass) | 1595.53 ms (1.596 s) | 704.19 ms (0.704 s) | Reruns live discovery to verify file stability |
| 4. Report Construction & Config Capture | 65.40 ms (0.065 s) | 54.45 ms (0.054 s) | `build_scan_report`, `build_doctor_report` & guarded config read |
| 5. Validation Pass (Reports & Configs) | 67.51 ms (0.068 s) | 56.19 ms (0.056 s) | Compares complete scan & doctor reports and reread config bytes |
| *(Unavailable Service Phases)* | *N/A (Approximation)* | *N/A (Approximation)* | In-memory cancellation checkpoints (C3), link/display maps (C3), and byte re-parsing (C1) |
| **Total Startup (Probe Estimate)** | **3252.74 ms (3.253 s)** | **1593.33 ms (1.593 s)** | Sum of measured phases 1 + 2 + 3 + 4 + 5 |

### Selective-Retention Comparison (Candidate)

| Candidate Metric | Scenario A | Scenario B | Notes |
| --- | --- | --- | --- |
| Selective Byte Capture Time | 49.14 ms (0.049 s) | 78.16 ms (0.078 s) | Retains support files only for differing Diff candidates |
| Capture Time Difference | -19.3 ms | +1.3 ms | Signed difference vs full capture (negative = faster) |
| Malformed-Diff Rule Verified | YES | N/A | Diff engine's Variant A baseline & readable-copy rules verified |
| Controlled Settings Rejection Verified | YES | YES | Verified that modified settings/lock bytes trigger validation rejection |
| Controlled Same-Count Report Rejection Verified | YES | YES | Verified that same-count mutated reports trigger validation rejection |

## 3. Precise Memory & Allocation Measurements

> **Note on Allocation Labels:** `tracemalloc` measures peak heap allocations tracked by the Python runtime for the monitored block. It does not represent total OS process memory (Resident Set Size). The file payload and container figures below measure captured file content payload plus selected file-storage container overhead (dictionaries, lists, and tuples holding file bytes), rather than total snapshot memory (which also holds index entries, parse results, reports, and configs). Both full and selective capture use the identical memory-accounting method.

| Memory Metric | Scenario A | Scenario B | Description |
| --- | --- | --- | --- |
| Retained File Payload Bytes | 1.07 MiB | 1.98 MiB | Exact sum of in-memory file byte buffers |
| Selected File Container Overhead | 108.39 KiB | 120.23 KiB | Overhead of mapping dicts, lists, and file tuples |
| **File Payload + Selected Container Overhead (Full)** | **1.18 MiB** | **2.10 MiB** | Sum of file bytes and container overhead for full capture |
| **File Payload + Selected Container Overhead (Selective)** | **298.27 KiB** | **2.10 MiB** | Identical calculation for selective candidate (skips support files) |
| Peak Traced: First Discovery | 4.51 MiB | 2.45 MiB | Traced Python heap during initial discovery |
| Peak Traced: Full Byte Capture | 1.22 MiB | 2.15 MiB | Traced Python heap during full byte reading |
| Peak Traced: Reports & Config Capture | 279.93 KiB | 274.93 KiB | Traced Python heap during scan/doctor build & config read |
| Peak Traced: Validation Pass | 278.74 KiB | 274.80 KiB | Traced Python heap during complete reports/config validation |
| **Peak Traced: Simulated Refresh** | **11.30 MiB** | **10.75 MiB** | Peak traced heap while holding old snapshot and building new |

## 4. Architectural Analysis & Decision Record

### 4.1 Probe Findings
1. **Full Capture Time:** Reading all file bytes across 600+ skills requires only **~68.5 ms (Scenario A)** and **~76.9 ms (Scenario B)**.
2. **Total Startup Estimate:** The sum of all five measured startup phases is **~3.25 s (Scenario A)** and **~1.59 s (Scenario B)** on Darwin arm64. Passing the existing index and registry into `build_doctor_report` eliminates the redundant discovery walk. Unimplemented phases (cooperative cancellation checkpoints in C3, path display and link equality maps in C3, and byte re-parsing in C1) are explicitly labeled as approximations.
3. **In-Memory Retention & Precise Accounting:** Total in-memory storage for captured files and containers (using identical accounting methods) is **1.18 MiB (Scenario A)** and **2.10 MiB (Scenario B)**. This accounts for file payload plus selected container overhead.
4. **Refresh Memory:** Tracking heap allocations from start through retaining the entire old snapshot and constructing and validating the replacement snapshot with freshly read bytes peaked at **11.30 MiB (Scenario A)** and **10.75 MiB (Scenario B)** of traced allocations.
5. **Validation Integrity:** The validation pass verifies complete scan and doctor report dataclasses (`scan1 == scan2`, `doc1 == doc2`) and reread configuration bytes. Controlled tests verified that mutated settings and same-count report modifications are reliably detected and rejected.
6. **Selective Retention Evaluation:** Selective retention saves only ~19.3 ms of capture time. Furthermore, to adhere to the Diff engine's Variant A baseline and readable-copy rules (where readable malformed copies with differing support files must be diffed), selective retention must retain support files for those malformed copies as verified in Scenario A. The minor memory reduction does not justify the added state complexity.

### 4.2 Decision Gate
- **Decision:** **Retain §21 Full Capture specification verbatim.**
- **Rationale:** Full capture provides 100% frozen inputs with zero live disk access during navigation, consumes under 3 MiB of retained file payload/containers for 600+ skills, and introduces no fragile conditional caching logic.

---
*Report generated by `docs/p3_cost_probe.py`.*
