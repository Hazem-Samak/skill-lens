# Phase 4 Review Findings — Resolved

> **Status:** Phase 4 is built, committed, tested — and **now correct**.
> **All 8 findings (C-01 ... C-08) are fixed**, each guarded by a test or a
> deliberate, documented decision.
> **Reviewed by:** orchestrator self-review + **two independent read-only review
> agents** — one checking the code against this repo's standards (`AGENTS.md`
> rules + code-smell baseline), one checking it against the specification
> (`SKILL_LENS_SPECIFICATION.md` sections 6 and 7), 2026-10-01.
> **Commit reviewed:** the Phase 4 working tree on top of `08191f6`.
> **Fix commit:** `eedc211`.
> **Gate now:** **417 passed**, `ruff check .` clean, `ruff format --check .` clean.

---

## 1. TL;DR for a non-programmer

Phase 4 added the two diagnostic commands: `skill-lens doctor` (a health check
for your skill folders) and `skill-lens compare --agent A --agent B` (which
capabilities two agents share and where they diverge).

Two reviewers read the new code. Neither found a rules violation (the engine
is still 100% read-only, tests still never touch the real home folder, JSON is
still the source of truth), but together they found **8 things worth fixing** —
including one real bug:

* **compare could lie in an annoying direction:** two copies of the same skill
  sitting in different folders were labelled "diverged — run `skill-lens diff`"
  even when their text was *byte-for-byte identical*. Running the suggested
  command would then say "no differences". Fixed: identical copies now count as
  shared (C-01).
* **The golden sample files could replace themselves.** If one was deleted, the
  test quietly rewrote it from the code's own current output — so the "proof the
  output is right" could silently become "proof the output is whatever it is
  now". Fixed: a missing golden now fails the test; rewriting needs a deliberate
  `--update-goldens` flag you read the diff before using (C-03).
* **A safety-critical piece of plumbing was decorative.** The spec says the new
  commands must run through the guarded "live filesystem adapter"; they skipped
  it and used the plain path. The guarded code still ran, but not as the
  official door. Fixed: `doctor` and `compare` now genuinely go through it (C-02).

Everything else was tidiness: a dead field nothing ever filled, a helper nothing
called, duplicated blocks, an argument order that was backwards between the two
new engines, magic strings, and documentation that hadn't caught up (C-04 ...
C-08). Three reviewer suggestions were **deliberately not adopted**, with
reasons written down (section 5).

The test count moved **418 → 417**: one new test added, two duplicate tests
removed. All six render snapshots stayed byte-identical through the whole fix
pass — the user-visible output did not change.

---

## 2. What Phase 4 actually shipped (working, keep it)

| Item | State |
| --- | --- |
| `core/doctor.py` — six hygiene checks over one discovery pass | shipped |
| Broken symlink / cycle / unreadable skill → ❌ ERROR; malformed frontmatter → ❌ ERROR | shipped |
| Codex context budget: > ~8,000 chars of descriptions → ⚠️, `evidence=documented`, source URL pinned in a test | shipped |
| Permission-blocked (TCC) search roots → ⚠️ warning; traversal hazards (`node_modules`) → ⚠️ | shipped |
| Symlink-farm health + installer-lockfile status → ℹ️ info | shipped |
| Findings sorted error → warning → info by a fixed key; stable across runs | shipped, guarded by a test |
| `core/compare.py` — pairwise `SHARED / DIVERGED / ONLY_A / ONLY_B` per name | shipped |
| Shared means *one canonical file* or *byte-identical copies* (content hash) | fixed by C-01 |
| `core/system.py` — live adapter: lazy home resolution, guarded reads, OSError-proof walk | shipped, now the real CLI path (C-02) |
| CLI: `doctor` and `compare --agent A --agent B`, both with `--json`; exit 0 when run, 2 on usage errors / unknown agents | shipped |
| Unknown agent rejected *before* any filesystem crawl | fixed by C-02 |
| Models: `DoctorReport`, `CompareReport` — derived counts never serialized; `to_dict`/`from_dict` round-trip | shipped |
| Rich layer: doctor panel + findings, compare table; every dynamic string escaped | shipped |
| Goldens `tests/fixtures/golden/phase4/doctor_farm.json` + `compare_claude_vs_codex.json`, home-relative | shipped, fail-when-missing (C-03) |
| Six render snapshots; live smoke test with the sandbox off; read-only invariant test | shipped |
| No new dependencies, no Rich in any engine (AST guards) | verified |
| Gate at commit | **417 tests pass, `ruff check` + `ruff format --check` clean** |

---

## 3. The findings and their fixes

**C-01 — compare ignored the content hash (real bug, spec reviewer).**
`_classify` judged "shared" only by canonical-path equality, so two
independent but identical copies were called DIVERGED and the report note told
the user to run `diff` — which would then find nothing. Discovery already
fingerprints every file; compare now reuses that: equal non-null hashes →
SHARED (the table still shows both paths, so the layout stays visible), and the
"run skill-lens diff" note appears only for genuine divergences.
Guard: `test_identical_copies_count_as_shared` in `tests/test_compare.py`.

**C-02 — the CLI bypassed the live adapter (spec §7 wiring, spec reviewer).**
`cli.py` called `build_doctor_report` / `build_compare_report` directly, which
fall back to plain discovery; `run_doctor`, `run_compare` and `live_discovery`
had no production caller — the adapter the spec designates as the guarded
bridge existed only in tests. Fixed: both commands now run through
`run_doctor` / `run_compare` in `core/system.py`. `run_compare` additionally
validates both agent ids *before* the walk (a typo costs an error message, not
a crawl) and reuses the loaded registry.

**C-03 — goldens auto-wrote and skipped when missing (standards reviewer).**
The Phase 4 gate tests wrote a missing golden from the code's own output, then
`pytest.skip`ped — a deleted or stale contract could be silently replaced,
against the spirit of "never regenerate without reading the diff". Fixed: a
missing golden is now a hard failure; regeneration happens only via a new
`--update-goldens` flag (same pattern as `--update-snapshots`), documented in
README. The one legitimate regeneration during this pass (removal of the dead
`notes` field, C-05) was verified by reading the diff: it changed exactly one
line, `"notes": []`.

**C-04 — the two new engines took `(home, cwd)` in opposite orders.**
`build_doctor_report(home, cwd, ...)` vs `build_compare_report(..., cwd, home, ...)`,
with both CLI calls positional — the kind of trap that turns into a silent
swap later. Fixed: compare now takes `(agent_a, agent_b, home, cwd, ...)` like
doctor; every call site and test updated. (Most call sites passed `(home,
home)`, which is why the inversion survived the first test pass — noted as a
test-design lesson.)

**C-05 — dead code: fields and helpers with no producer or caller.**
`DoctorReport.notes` was always empty (its render loop could never fire),
`probe_readonly` in the adapter was test-only, and `CompareReport` carried
three ways of counting the same thing (`shared_count`, `diverged_count`,
`counts_by_relation`). Fixed: all removed; `counts_by_relation()` remains the
single derived view (compare's `notes` stays — it does have a real producer).
Removing the serialized `notes` key from doctor's JSON is the one contract
change, pinned by the regenerated golden.

**C-06 — duplicated code (standards reviewer).**
`_symlink_findings` was four near-identical `DoctorFinding` blocks; the test
suite re-typed the severity rank map, and `test_compare.py` carried a second
copy of doctor's own no-Rich guard. Fixed: one table `_SYMLINK_CLAUSES` drives
the message wording (a new error tag now needs one row, not a new block); the
sort test reads the engine's own `_severity_order`; the duplicate guard test
was deleted (doctor's file guards itself).

**C-07 — magic strings where constants belong.**
`"missing"` / `"not_json"` were spelled inline in the adapter and doctor.
Fixed: `ERR_MISSING_FILE` / `ERR_NOT_JSON` named constants next to the
`ERR_*` convention they join; `read_json_guarded` returns them, doctor compares
them. The serialized values are unchanged, so no golden moved.

**C-08 — documentation drift.**
`AGENTS.md`'s architecture diagram omitted `core/compare.py`; the `cli.py` and
`render.py` header comments still listed only the Phase 2/3 commands; a
`#:`-style comment sat above the wrong function in the adapter. All fixed, and
this file + the README status line carry the record.

---

## 4. Defects the first pass caught during building (not review findings)

Kept here because they explain odd code you may see:

* A **chmod-000 skill directory under a readable root** arrives as a normal
  entry whose *parse* is unreadable — no error tag at all. `_symlink_findings`
  needed a third branch for it (`unreadable_skill`), proven by the
  `tcc_permission_error` golden fixture.
* The farm check must compare **resolved** library paths: on macOS `/tmp` is
  really `/private/tmp`, so an unresolved home spelled the same folder two ways.
* Fixture directory names containing `/` silently create nested folders; a
  symlink named `[bold evil]` is how markup-escaping is tested instead.
* `render_compare` printed an empty table when both agents had no skills; it now
  stops after the "neither agent has any skills" line.

---

## 5. Reviewer suggestions deliberately NOT adopted (with reasons)

* **`unreadable_skill` should be a warning, not an error** (the spec lists
  permission-blocked *roots* at ⚠️). Rejected: a *skill* the OS refuses to
  open cannot be loaded by any agent — exactly the impact of a dangling link,
  which the spec itself puts at ❌. The rationale is a comment in
  `_symlink_findings`.
* **Detect the spec's literal `node_modules/**/SKILL.md` pattern anywhere.**
  Rejected as bounded: section 5 of the spec forbids unbounded crawls, and
  discovery only descends into directories named `skills` — a stray
  `SKILL.md` outside any `skills/` folder is never collected, so there is
  nothing to warn about. The realistic live hazard (a recursive `skills` root
  punching *through* a `node_modules` tree) is detected. Explanation added as
  a scope note in `_traversal_findings`.
* **Lockfile trouble should be ℹ️, per the spec's info row.** Kept at ⚠️: an
  installer that wrote garbage JSON will mis-read it later — a real defect
  worth flagging. A *missing* lockfile stays ℹ️ as the spec intends.
* **`--sandbox` / `--cwd` on the new commands is scope creep.** Kept: every
  command since Phase 2 takes them, and without them the new commands could
  not be tested against fixtures at all.

---

## 6. Numbers you can check

* Tests: 418 → **417** (+1 C-01 regression test, −2 dead/duplicate tests).
* New source: `core/doctor.py` (407 lines), `core/compare.py` (172),
  `core/system.py` (96), `models/compare.py` (104).
* New tests: `test_doctor.py` 21, `test_compare.py` 18, `test_phase4_gate.py` 9,
  doctor/compare cases inside `test_cli.py`, 6 snapshots.
* Budget threshold: **8,000 characters**, documented evidence
  <https://developers.openai.com/codex/skills>, pinned in a test assertion.

---

## 7. Commit trail

| Commit | What |
| --- | --- |
| `08191f6` | last pre-Phase-4 commit (review fixed point) |
| `eedc211` | Phase 4 shipped — doctor, compare, live adapter, models, render, tests, **and** the C-01 ... C-08 review fixes in one pass |
