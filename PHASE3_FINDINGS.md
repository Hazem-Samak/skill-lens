# Phase 3 Review Findings — Resolved

> **Status:** Phase 3 is built, committed, tested — and **now correct**.
> **All 4 findings (D-01 … D-04) are fixed**, each guarded by a regression test.
> **Reviewed by:** orchestrator self-review + an independent **read-only** review
> delegated to Gemini 3.8 Flash (High) via `agy` 1.2.14 (`agy-delegate` skill,
> 2026-09-30).
> **Commit reviewed:** `88c69a6` (Phase 3).
> **Fix commit:** `9f32e8b`.
> **Gate now:** **355 passed**, `ruff check .` clean, `ruff format --check .` clean.

---

## 1. TL;DR for a non-programmer

Phase 3 added the `skill-lens diff` command, which shows what actually differs
between two copies of the same skill, plus the screen formatting and a set of
"photograph" tests that freeze the terminal output.

An independent reviewer read the code and found **4 real defects — all of them in
the part that trims an over-long diff**, plus one wording problem. Nothing was
wrong with the overall design: the reviewer confirmed every claim about the
architecture, the data contract, the baseline rule and the line-ending rule.

The defects were all of the "only shows up on a very large diff, or on a broken
skill" kind — real, but easy to miss:

* a trimmed diff could print a block that **showed no change at all**;
* a trimmed block could carry a **malformed heading** that standard diff tools
  reject;
* two **different** broken copies could be reported as **"identical"**, when in
  truth nothing had been compared;
* a notice could read **"Truncated: 0 changed lines omitted."**

All four are fixed, and each fix has a test that fails if the bug ever returns.
The reviewer was also right that **my own tests were partly to blame**: they
checked a trimmed block's line counts but not its starting numbers, and one
snapshot test had recorded the malformed heading as if it were correct.

---

## 2. What Phase 3 actually shipped (working, keep it)

| Item | State |
| --- | --- |
| `models/diff.py` — `DiffChange`, `DiffHunk`, `DiffFile`, `DiffCopy`, `DiffReport` | shipped |
| Every model has `to_dict()` **and** `from_dict()`; `has_differences` is derived, never serialized | shipped |
| `core/diff.py` — pure computation, imports no `rich` | shipped, guarded by an AST test |
| Copies deduplicated by canonical target, so symlinked copies can never diff | shipped |
| Baseline = the Variant A copy; invalid copies take part but get no letter | shipped |
| Unreadable copies (dangling / cycle / permission-denied) listed with no diff | shipped |
| Binary files reported as differing, contents never printed | shipped |
| Added / removed / renamed files detected by relative path | shipped |
| Line-ending-only differences produce no diff (agrees with the content hash) | shipped |
| Truncation: 400 changed lines per copy, 20,000 characters per report | shipped, but see D-01 … D-04 |
| `render_diff` + `render_agents` in `render.py`; no Rich layout left in `cli.py` | shipped |
| `diff <name> [--sandbox] [--cwd] [--json]`, exit 0 for "nothing found" and "no differences" | shipped |
| Snapshot harness: plain text, fixed asserted width, `--update-snapshots` | shipped |
| Strictly read-only; no new declared dependency (`difflib` + Rich's `Syntax`) | verified |
| Gate status at time of writing | **355 tests pass, `ruff check` + `ruff format --check` clean** |

> **Reading section 4:** each write-up describes the defect **as it was found**,
> including the code that was wrong, then the fix. They are kept as the record.

---

## 3. Findings index

| ID | Severity | Area | One-line summary | State |
| --- | --- | --- | --- | --- |
| **D-01** | 🟠 Major | `core/diff.py` | A truncated diff could emit a hunk containing **no changes** | ✅ **fixed** |
| **D-02** | 🟠 Major | `core/diff.py` | A truncated hunk could carry an invalid zero-length range header | ✅ **fixed** |
| **D-03** | 🟡 Minor | `render.py` | Two broken copies reported as "identical" when nothing was compared | ✅ **fixed** |
| **D-04** | 🟢 Info | `render.py` | "Truncated: 0 changed lines omitted." | ✅ **fixed** |

**Gate before the fixes:** 350 tests pass, `ruff check` clean.
**Gate now:** 355 tests pass, `ruff check` clean, `ruff format --check` clean.

---

## 4. Detailed findings

### D-01 🟠 Major — A truncated diff could emit a hunk with no changes

**What the code did** (`core/diff.py`, `_truncate`) — the loop walked the lines of
each hunk and only the *changed* lines counted against the budget:

```python
lines: list[str] = []
for line in hunk.lines:
    changed = 1 if line[:1] in ("-", "+") else 0
    cost = len(line) + 1
    if used_changed + changed > changed_budget or used_chars + cost > char_budget:
        exhausted = True
        break
    lines.append(line)
    used_changed += changed
    used_chars += cost
if lines:
    hunks.append(_recount(hunk, lines))
```

**Why it was wrong.** Context lines cost **0** changed lines, so once the budget
had been spent *exactly* at a hunk boundary, the next hunk's leading context
lines still passed the guard and were collected. The loop then stopped at the
first real change — leaving `lines` holding only unmodified lines. Because
`if lines:` was non-empty, that hunk was kept. A hunk with no additions and no
deletions is not a diff at all.

**Reproduced** with a 2-hunk file and a budget of exactly the first hunk's
changes:

```text
hunk @-1,4 +1,4  changed=2   lines=['-line 0', '+LINE 0', ' line 1', ' line 2', ' line 3']
hunk @-17,3 +17,3 changed=0  lines=[' line 16', ' line 17', ' line 18']   <-- shows nothing
```

**How it would have shown up for a user:** on a large multi-hunk diff, a heading
claiming a change followed by ordinary unchanged code.

**Fix** — `_fit_hunk()` (`core/diff.py:283`) now returns the longest prefix of a
hunk that fits both budgets, and `_truncate()` (`core/diff.py:304`) drops any hunk
that ends up with zero changed lines. Because the hunk is dropped, its context
lines are no longer charged to the budgets either, so the reported "omitted"
totals stay honest.

**Test:** `test_multi_hunk_truncation_never_emits_a_hunk_without_changes`
(`tests/test_phase3_gate.py:510`).

---

### D-02 🟠 Major — A truncated hunk could carry an invalid zero-length range

**What the code did** (`core/diff.py`, `_recount`) — the line **counts** were
recomputed, but the **starts** were carried over unchanged:

```python
return DiffHunk(
    old_start=hunk.old_start,
    old_count=sum(1 for line in lines if line[:1] in (" ", "-")),
    new_start=hunk.new_start,
    new_count=sum(1 for line in lines if line[:1] in (" ", "+")),
    lines=tuple(lines),
)
```

**Why it was wrong.** A unified diff header stores a zero-length range as the
line *before* it — the rule already documented in `DiffHunk` and `_range_start`
(`core/diff.py:143`). The stored start had been computed for the **original**
count, so when truncation emptied one side of a hunk, the start no longer
matched its count: a truncated all-deletions hunk rendered as
`@@ -1,4 +1,0 @@` instead of `@@ -1,4 +0,0 @@`. A standard diff reader rejects
`+1,0` as an invalid range.

**This one was already committed**, in the snapshot the Phase 3 gate had accepted
as correct — which is precisely the trap: a snapshot test proves the output did
not *change*, never that it was *right*.

**Fix** — `_recount_start()` (`core/diff.py:250`) steps the start back one line
when truncation empties a range that was not empty before, and does nothing when
the range was already empty (so a range is never decremented twice).
`_recount()` (`core/diff.py:264`) applies it to both sides.

**Tests:** `test_recount_steps_back_when_truncation_empties_a_range`
(`tests/test_phase3_gate.py:478`),
`test_recount_does_not_step_back_a_range_that_was_already_empty`
(`tests/test_phase3_gate.py:502`), and
`test_a_truncated_hunk_still_adds_up` (`tests/test_phase3_gate.py:446`) now
asserts hunk **starts** as well as counts.

---

### D-03 🟡 Minor — Two broken copies reported as "identical"

**What the code did** (`render.py`, `_no_differences_message`):

```python
readable = [copy for copy in report.copies if copy.is_readable]
if len(report.copies) == 1:
    return "[green]No differences:[/green] only one copy exists, ..."
if len(readable) < 2:
    return "[green]No differences:[/green] fewer than two copies could be read."
return f"[green]No differences:[/green] all {len(readable)} readable copies are identical."
```

**Why it was wrong.** When every copy fails frontmatter validation there is no
Variant A baseline, so `build_diff_report` computes **no diff at all**. Both
copies therefore had empty file lists, `has_differences` was `False`, and the
renderer announced that the copies were *identical* — even when their contents
were completely different. Each copy was also headed "identical to the baseline",
and there was no baseline. (The model's explanatory note *was* printed, so the
information existed — but the headline contradicted it.)

**Fix** — three places now say what actually happened: the headline reads
"Not compared: no copy could serve as a baseline."
(`render.py:251`); `_copy_heading()` (`render.py:206`) takes a `baseline_exists`
flag and reports "not compared: no baseline"; and the per-copy body says the same.

**Also corrected while fixing this:** the model's note was being printed **twice**
— once in the no-differences branch and again at the end of `render_diff`. Notes
are now printed from a single call site (`_print_notes`, `render.py:278`), and a
note the headline already states is not repeated in the terminal (it stays in the
JSON for `--json` consumers).

**Tests:** `test_diff_no_baseline_snapshot`
(`tests/test_render_snapshots.py:172`), which asserts `"identical"` does **not**
appear in the output.

---

### D-04 🟢 Info — "Truncated: 0 changed lines omitted."

**What the code did** (`render.py`):

```python
if copy.truncated:
    console.print(f"  [yellow]Truncated:[/yellow] {copy.omitted_lines} changed lines omitted.")
```

**Why it was wrong.** `copy.truncated` is true when **either** budget bit, but
`omitted_lines` only counts changed lines. A diff cut short purely by the
report-wide *character* budget reported "0 changed lines omitted" — a notice that
says nothing happened while something did.

**Fix** — the line count is quoted only when changed lines really were dropped;
otherwise the notice points at the report total below (`render.py`, in
`render_diff`).

**Test:** `test_diff_truncated_by_characters_snapshot`
(`tests/test_render_snapshots.py:194`).

---

## 5. Test gaps the review identified (now closed)

The reviewer was explicit that three of my own tests were weak, and it was right:

| Gap | Why it mattered | Now |
| --- | --- | --- |
| `test_a_truncated_hunk_still_adds_up` checked counts but not starts | Let **D-02** through undetected | asserts starts too |
| The truncation snapshot recorded the malformed header as correct | Let **D-02** be committed as "passing" | snapshot corrected to `@@ -1,4 +0,0 @@` |
| No test exercised multi-hunk truncation | Let **D-01** through undetected | new multi-hunk regression test |

Two further snapshots were added to cover paths that had no coverage at all:
`diff_no_baseline` (D-03) and `diff_truncated_by_chars` (D-04).

---

## 6. Checked and found sound

The reviewer verified every claim it was given against the code, and confirmed:

* `models/diff.py` defines all five types with `to_dict()` / `from_dict()`, and
  `has_differences` is a derived property, absent from the JSON.
* `core/diff.py` imports no `rich` — checked by parsing the module's import
  statements, not by searching for the word.
* The golden `diff_variant_hash_detection.json` pins the JSON contract and is
  compared field by field.
* The CLI signature, the exit codes, the deduplicated input, the baseline rule,
  the line-ending rule, binary handling, and added/removed files all match the
  specification.
* Moving the `agents` table into `render.py` left `cli.py` free of Rich layout.
* The snapshot harness asserts its width rather than assuming it.
* The Phase 3 boundaries were respected: no new declared dependency, no TUI, and
  `doctor` / `compare` / `system.py` left for Phase 4.
* The Phase 2 refactor (`discovery.labels_for_entries` as the single label rule)
  did not change existing behaviour.

Spec conformance was marked "met" for every rule except truncation, which was
downgraded to "partially met" pending D-01 … D-04.

---

## 7. How this was verified

**The review was read-only and provably could not alter the project.** It ran
through the `agy-delegate` relay with `--read-only` (a sandbox whose writes are
overlaid and discarded). The relay fingerprints the working tree before and after
and reported `readOnlyViolation: false`; the only entry in `touchedFiles` was the
pre-existing untracked `uv.lock`. A post-run `git diff HEAD` was empty.

**Every finding was reproduced locally before being fixed**, with the same
reproduction then re-run after the fix to prove it was gone — not merely that the
test suite went green. Two of the orchestrator's own checks were wrong along the
way and are recorded here for honesty: a first attempt to reproduce D-01 failed
because the two fixture copies had *different* descriptions, so the `SKILL.md`
hunk consumed the budget first; and a first "D-02 still present" verdict was a
false alarm from a regex that also matched the *correct* header `+0,0`.

**Gate after the fixes:** `355 passed` (350 before + 5 new regression tests),
`ruff check .` clean, `ruff format --check .` clean (44 files).

---

## 8. Open observations (verified, not defects)

Recorded so they are not lost. None of these is a bug, and none blocks Phase 4.

1. **`resolver._assign_variant_labels` labels only the first candidate** of a
   duplicated canonical key. When one agent reaches the same library through two
   entrypoints (a project shortcut plus the global copy), only the first carries a
   Variant letter in `why`. This is preserved Phase 2 behaviour, flagged for a
   future decision rather than changed here.
2. **`agents` has no snapshot test.** `scan`, `why` and `diff` are frozen as
   plain-text snapshots; a visual change to the agents table would not be caught.
3. **One diff golden versus thirteen resolution goldens.** Adding goldens for
   invalid copies and multi-file additions/removals would strengthen the contract.

**Two questions the reviewer left open**, with the answers this codebase settled on:

* *Should copies be diffed when none is valid?* No — an invalid copy is never the
  baseline (specification section 6, command 5), so with no valid copy nothing is
  compared, and the terminal now says exactly that (D-03).
* *What happens to a hunk that truncation reduces to context only?* It is dropped
  whole, which is the standard approach and what D-01's fix implements.

---

## 9. Commit trail

| Commit | What |
| --- | --- |
| `a31e3b5` | Phase 3 plan locked down (spec, `AGENTS.md`, README) |
| `88c69a6` | Phase 3 implemented — the commit this review examined |
| `9f32e8b` | D-01 … D-04 fixed, with regression tests and corrected snapshots |
