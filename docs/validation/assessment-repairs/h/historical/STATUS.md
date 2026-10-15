# Stage H benchmark historical artifact

This directory holds the **pre-correction** Stage H benchmark results as an
immutable historical record. It is **not** the current method and must not be
treated as valid evidence after the Stage H correction.

## Artifacts

- `benchmark-results-pre-correction.json` — results captured 2026-10-15 with the
  pre-correction `benchmark_capture.py` (first attempt; invalid method).
- `benchmark-results-second-attempt.json` — results captured 2026-10-16 with
  the correction-r1 `benchmark_capture.py` (second attempt; invalid method,
  superseded by correction-r2). Source hash does not match the final corrected
  script.

## Status: pre-correction — invalid method

The original benchmark had confirmed defects (reproduced by the coordinator,
see `coordinator-r1-reproduction.json`):

1. `retained_heap_one_generation_bytes` / `retained_heap_both_generations_bytes`
   copied **peak** traced values instead of **current** traced allocations.
2. The untraced "refresh" released the initial snapshot before the second
   capture, so old was not held alive through refresh timing.
3. Fingerprinting checked only size/mode/target with no byte hashes, so a
   same-size `AAAA` → `BBBB` mutation was reported as unchanged.
4. Assertions were booleans, not enforced; `count > 0` missed partial capture.
5. Sandbox/HOME/XDG_CONFIG_HOME/tracemalloc state was not safely restored on
   failure (`paths.set_sandbox(None)` unconditionally; tracing could stay active
   after a capture error).
6. The saved `benchmark-results.json` `source_hash` did **not** match the final
   benchmark script.

## Disposition

Superseded by the corrected `benchmark_capture.py` (correction-r2) and a fresh
`benchmark-results.json` (sibling directory), regenerated 2026-10-16 with the
corrected method: `os.walk` onerror that raises OSError, compact validator LOOP
over initial/refresh/old/new, tracemalloc-active guard, correct
initial_generation/refresh_generation, per-file bytes object identity + SHA-256
vs fixture hash, snap_old/snap_new released before AFTER fingerprint, safe state
restoration, and matching source/product-source hashes.

This file is preserved read-only; do not overwrite or delete it.
