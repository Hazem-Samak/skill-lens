# Stage H Resource-Risk Measurement

**Stage:** H — Reconcile current documentation and measure remaining resource risk
(F13, R01; documents R04 and accepted limitations).
**Plan reference:** `docs/plans/2026-10-12-assessment-repairs.md` §6 Stage H,
frozen commit `fe6f89bc55eb3f4f04187567b968dd96ae9c86c1`.
**Date:** 2026-10-16
**Environment:** macOS (Darwin arm64), Python 3.11.16, `.venv` interpreter.
**Benchmark:** `docs/validation/assessment-repairs/h/benchmark_capture.py` (benchmark
instrumentation uses only the standard library; capture_session exercises the
source checkout with installed third-party dependencies; synthetic fixtures
outside the repo; no live skills, no system-root probes, no network).

## Status

**Stage H is accepted locally.** See the [acceptance record](acceptance.md) for
coordinator checks, independent review, limitations and delivery boundaries.

## Measured results

Byte-heavy capture/refresh benchmarks on synthetic fixtures, 3 repeats each,
all passes. Every fixture's inventory, bytes, modes, symlink targets, and
chunked SHA-256 fingerprints were captured before and after capture and
verified unchanged (preservation). Retained heap is reported as **current**
traced allocations, not peak; transient peaks are reported separately. Synthetic
fixtures contain no symlinks; none were added just to claim hypothetical
coverage.

### Scenario A — 8 skills × 2 MiB binary asset each (~16 MiB payload)

| Metric | Result |
| --- | --- |
| Captured files | 16 (8 SKILL.md + 8 asset.bin) |
| Captured payload | 16,778,912 bytes (~16.0 MiB) |
| Largest file | 2,097,152 bytes (2 MiB) |
| Captured canonical skills | 8 |
| Initial capture wall time (tracing off) | 26.2–27.9 ms (raw current, 3 repeats) |
| Refresh capture wall time (tracing off) | 25.8–27.3 ms (raw current, 3 repeats) |
| Traced heap, one generation (retained current) | 16.04 MiB |
| Traced heap, both generations (retained current) | 32.07 MiB |
| Traced heap, one-generation peak (transient) | 22.05 MiB |
| Refresh overlap peak (both held, transient) | 38.08–38.09 MiB |

### Scenario B — 8 skills × 8 MiB binary asset each (~64 MiB payload)

| Metric | Result |
| --- | --- |
| Captured files | 16 (8 SKILL.md + 8 asset.bin) |
| Captured payload | 67,110,560 bytes (~64.0 MiB) |
| Largest file | 8,388,608 bytes (8 MiB) |
| Captured canonical skills | 8 |
| Initial capture wall time (tracing off) | 83.8–86.2 ms (raw current, 3 repeats) |
| Refresh capture wall time (tracing off) | 83.6–86.0 ms (raw current, 3 repeats) |
| Traced heap, one generation (retained current) | 64.04 MiB |
| Traced heap, both generations (retained current) | 128.07 MiB |
| Traced heap, one-generation peak (transient) | 88.05 MiB |
| Refresh overlap peak (both held, transient) | 152.09 MiB |

### Scenario C — 1 skill × 16 MiB binary asset (~16 MiB payload, single file)

| Metric | Result |
| --- | --- |
| Captured files | 2 (1 SKILL.md + 1 asset.bin) |
| Captured payload | 16,777,429 bytes (~16.0 MiB) |
| Largest file | 16,777,216 bytes (16 MiB) |
| Captured canonical skills | 1 |
| Initial capture wall time (tracing off) | 21.6–23.5 ms (raw current, 3 repeats) |
| Refresh capture wall time (tracing off) | 21.3–22.9 ms (raw current, 3 repeats) |
| Traced heap, one generation (retained current) | 16.02 MiB |
| Traced heap, both generations (retained current) | 32.03 MiB |
| Traced heap, one-generation peak (transient) | 64.04 MiB |
| Refresh overlap peak (both held, transient) | 80.05 MiB |

The tables above summarize the worker's [source-matched run](benchmark-results.json).
The coordinator independently repeated all nine cases; [raw results](coordinator/benchmark-results.json)
and [summary](coordinator/benchmark-summary.json) are retained. Retained/peak
memory agreed to about 0.01 MiB. Timing varied: the coordinator observed initial
capture ranges of 29.3–30.4 ms, 92.7–94.6 ms and 26.7–47.9 ms for A/B/C,
respectively. These warm local timings are observations, not performance promises.

## What was measured and how

- **Capture method:** real `capture_session(generation=N, home=sandbox, cwd=sandbox)`
  against a sandboxed `HOME`. Discovery, config reads, scan report, doctor report,
  display paths, and a second discovery pass (validation) all run inside the
  capture. File bytes are read in 64 KiB chunks and stored in `CapturedFile.data`.
- **Timing:** untraced wall-clock for initial and refresh captures (performance
  timing), separate from tracemalloc runs (memory measurement).
- **Tracing:** `tracemalloc.start()` is called **before** the old generation
  exists; a baseline is read after start. Generation 1 is captured, held in
  memory, then generation 2 is captured (overlap). `gc.collect()` runs before
  each current reading; `tracemalloc.reset_peak()` runs immediately before the
  refresh.
- **Retained heap (current):** one generation = current traced memory with the
  old generation held; both generations = current traced memory with both held.
  These are the true retained values, separate from transient peaks.
- **Refresh overlap peak:** the peak traced heap while both generations coexist
  (generation 1 held while generation 2 is captured). This is the measured
  fixture's peak for this scenario — **not** a universal bound on "the worst-case
  memory moment."
- **Fingerprint:** `os.walk` with an `onerror` callback that raises `OSError`
  (no traversal failure is silently skipped); chunked SHA-256 per regular file
  before/after; directories including modes; directory symlinks + targets
  recorded with no following; walk/stat/read errors raise rather than being
  silently skipped.
- **Assertions (enforced, fail nonzero):** exact file/payload/largest/canonical
  counts for initial/refresh/old/new against full fixture totals (asset bytes +
  SKILL.md); generation IDs 1 and 2; old and new coexist as distinct objects/
  bytes; fixture preservation checked AFTER releasing snapshot temporaries with
  tracing off.
- **Fixtures:** deterministic PRNG-seeded bytes (seed 20261016), reproducible.
  Fixture construction happens before tracing; no live fixture construction
  buffer is retained inside tracing.
- **Config bytes:** configuration/lockfile inputs are captured separately
  (`CapturedInput`) and are reported separately from payload totals.
- **State restoration:** original `paths.get_sandbox()`, `HOME`,
  `XDG_CONFIG_HOME`, and tracemalloc state are restored in `finally`, including
  on failure.
- **Artifact:** `benchmark-results.json` records exact argv, date/timezone (UTC
  can be Oct 15 while Cairo is Oct 16), environment, methodology, script source
  hash, and hashes of the exercised product source files, tying results to the
  unchanged source base. Default output uses exclusive creation and never
  overwrites historical evidence; `--output` refuses an existing path.

## Reproduce and interpret the artifact

From the source checkout, use a fresh process with tracing initially disabled:

```bash
.venv/bin/python -B docs/validation/assessment-repairs/h/benchmark_capture.py --output /tmp/skill-lens-stage-h-new-run.json
```

Choose an unused output path; existing files are refused. Fixtures are temporary
and outside the repository. The script writes its result artifact to the requested
path; without `--output`, it creates a new artifact under this `h/` directory.
The script's phrase “installed runtime” refers to this editable source checkout
and installed dependencies, not a clean installed wheel. Its four selected
module hashes are supplementary; [coordinator preservation evidence](coordinator/preservation.json)
and the pre-review file hashes establish the unchanged product/test tree.
The completion flags in the JSON are reached only after the enforced checks;
the actual rejection/control evidence is in [guard probes](coordinator/probe_guards.json)
and the [shared-buffer probe](coordinator/identity-probe.json).

The fresh-process tracer precondition is checked after synthetic fixture
construction but before changing HOME, XDG or the sandbox. It does not stop or
reset an existing tracer. Captured buffers can still have temporary references
after snapshot objects are released; the final preservation walk occurs with
tracing stopped and does not affect the reported memory readings. UTC timestamps
may be on 15 October while local Cairo timestamps are on 16 October in the same
session; historical artifact labels use both bases.

## What is explicitly NOT measured or bounded

- **Total process RSS / native allocations:** tracemalloc tracks Python heap
  allocations only. It excludes interpreter overhead, native extension memory,
  and OS page-cache effects.
- **Config bytes:** configuration/lockfile inputs are captured separately
  (`CapturedInput`) and are not part of the payload totals reported above.
- **Full live-home scalability:** benchmarks use bounded synthetic fixtures
  (8 skills, byte-heavy assets). A real user library with hundreds or thousands
  of skills was not measured. Skill count alone is a poor predictor: a small
  number of large assets can outweigh hundreds of text-only skills.
- **Historical U1 measurements:** the U1 capture benchmark on 600+ skill
  fixtures (~9.75–9.98 MiB refresh peak, ~682–991 ms) is retained as historical
  context only; no inferred speedup or solved-memory claim is made.
- **Model provenance:** the task ledger records the configured target/options,
  not a provider-confirmed serving identity, family, or effort. Upstream served
  identity/family/effort is **unverified** unless actual provider session
  evidence is cited; nothing here is described as provider-confirmed.

## R01 — Snapshot memory is unbounded by bytes

> **Update, 2026-10-16 — a resource policy is now implemented.** The owner chose
> Stage H's *explicit refusal* option (option 2 below) and it shipped the same
> working day. `capture_session` now measures the total skill payload **before**
> reading any of it and refuses an oversized home with `SnapshotTooLarge`: nothing
> is published and the previous generation is kept. The default budget is 256 MiB
> and is overridable with `skill-lens tui --max-snapshot-bytes <bytes>` (`0`
> disables it). Only skill payload counts; configuration bytes stay separately
> accounted. The measurements below are unchanged historical evidence and remain
> the record of *why* the policy exists. Policy: [`FULL_SCREEN_TUI.md` §9.3](../../../../FULL_SCREEN_TUI.md);
> plan: [`docs/plans/2026-10-16-snapshot-capture-budget.md`](../../../plans/2026-10-16-snapshot-capture-budget.md).
> The statements below that "no resource policy is approved or implemented", and
> the list of future owner choices, describe Stage H as it stood at the time and
> are superseded by this update.

**Status: Valid resource risk; not a reproduced out-of-memory failure.**

Capture stores every file's bytes, and refresh overlaps old and new generations.
The measurements above confirm that payload size directly drives retained heap:
a 64 MiB payload retains ~64 MiB for one generation and ~128 MiB retained with
both snapshots held (current traced); the transient refresh overlap peak is
~152 MiB, reported separately. There is **no byte bound** on snapshot content,
and no measured value is a universal worst case.

**No resource policy is approved or implemented.** The benchmark and this
documentation are not a memory bound. The frozen no-post-capture-disk-read contract is preserved:
no lazy disk reads, no caches, no database, no truncation.

### Future owner choices (decisions, not implemented behavior)

The owner must explicitly choose one of the following before any capture behavior
changes:

1. **Warning-only** — disclose the unbounded risk in docs/help; no enforcement.
2. **Explicit refusal** — refuse to capture when payload would exceed a stated
   threshold, preserving the prior valid generation and offering a CLI fallback.
3. **Representation redesign** — metadata-only mode or lazy-content retention
   with an explicit contract amendment and honest completeness reporting.

## R04 — Process-global sandbox state can leak across embedded invocations

**Status: Documented limitation; not fixed.**

In one Python process, a CLI call with `--sandbox` followed by a call without it
reused the first sandbox. `_apply_sandbox(None)` does not clear the module
global. Normal shell invocations start separate processes, so this does not
demonstrate a user-facing leak between ordinary terminal commands.

This is **not fixed** in Stage H. If repeated embedded calls become supported,
use explicit per-invocation context and guaranteed restoration. Do not clear
sandbox state indiscriminately — that would break existing isolated test
fixtures.

## Other accepted limitations disclosed

- **OMP namespaced coexistence** is deliberately under-modelled. Neither `shadow`
  nor `merge` can express namespaced coexistence; under-claiming is the correct
  direction of error.
- **Stage G Textual dependency floor/ceiling overlap:** Stage G acceptance
  discloses that both the minimum and latest constrained Textual installs
  currently select **8.2.8** — the same version. This overlap provides two
  installation checks, not two-version coverage or a guarantee about future
  Textual releases.
- **Unknown registry evidence:** rules without adequate primary evidence are
  reported as `ambiguous` or `unverified`, not guessed. No replacement rule is
  asserted without supporting documentation.
- **Frozen services use requirement:** captured services must be used for TUI
  browsing; live helpers such as `build_scan_report()` can still perform
  filesystem reads.
- **Case-insensitive skip:** filesystem case-sensitivity tests may skip on
  case-insensitive volumes (macOS APFS default); Linux CI covers different
  conditions.
- **`--fail-on info`** is intentionally very strict and explained in help.
- **CI/local scope:** benchmarks and gates were run locally on macOS/Python 3.11.
  Linux, full CI matrix, and unexecuted lanes are not claimed.

## Evidence links

- Benchmark script: [benchmark_capture.py](./benchmark_capture.py)
- Benchmark results: [benchmark-results.json](./benchmark-results.json)
- Pre-correction historical artifact (first attempt): [historical/benchmark-results-pre-correction.json](./historical/benchmark-results-pre-correction.json) (see [historical/STATUS.md](./historical/STATUS.md))
- Second attempt historical artifact (superseded): [historical/benchmark-results-second-attempt.json](./historical/benchmark-results-second-attempt.json)
- Prior U1 measurements (historical, not inferred): [docs/validation/u1/](../../u1/)
- Stage G acceptance: [docs/validation/assessment-repairs/g/acceptance.md](../g/acceptance.md)
- Assessment plan: [docs/plans/2026-10-12-assessment-repairs.md](../../../plans/2026-10-12-assessment-repairs.md)
