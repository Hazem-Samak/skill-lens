# Stage F Review — Round 1, MiniMax critic report

## Summary

Read-only critic review of Stage F (F15 final-newline explanation, F16 causal precedence
winner, F11 agents rendering) against frozen scope
`docs/plans/2026-10-12-assessment-repairs.md` Section 6 Stage F @ `fe6f89bc55eb3f4f04187567b968dd96ae9c86c1`,
base `3762f1059fe34e79a0c1e93fc5032600bb648b78`.

**Verdict: pass.** No blocking defect was found, and none was reproducible. The change meets
repo rules and preserves compatibility of the diff JSON contract, hunk ranges/budgets,
read-only behaviour, and frozen-input report consumers.

Key design decisions confirmed correct by inspection and independent probing:
- The newline marker is injected only where a line genuinely lacks `\n`, is paired atomically
  with the line it annotates during truncation, and is excluded from old/new line counts and
  the changed-line budget while still charged to the character budget.
- The causal winner is taken from `_active_roles` (top-rank, post-specificity, unique) rather
  than from presentation state, and is suppressed exactly when `coexist_policy` is a
  coexisting policy — a hole that cannot occur, because `_role_for_active` can only yield
  SHADOWED when the policy is not coexisting (or for opencode, whose policy is `shadow`).
- Public JSON keys are unchanged; only a new *value* form may appear inside `lines[]`.

Scope stayed inside the freeze: five product/test files plus one new test file and a doc-only
execution record. No registry behaviour/rank change, no dependency, no packaging/release work,
no golden or fixture file modified.

## Verification performed

Coordinator gates assessed as supplied and not re-run (permitted by the brief):
989 passed / 1 filesystem skip, 91.11% coverage, mypy clean on 36 files, Ruff lint clean,
138 files already formatted. 14 mutation controls each clean/mutant/restored = 0/1/0 with
verified disposable-copy import provenance.

Independent work by this critic (read-only, nothing written into the repository):
- Copied `skill_lens/` to `/tmp/slf-critic/src`, ran with `PYTHONPATH` pinned there and
  `cwd` set to that copy, and asserted `module.__file__` resolves inside it before every
  result below.
- Confirmed the coordinator's `mutation-source` copies of `core/diff.py`, `core/resolver.py`,
  `render.py` and `models/diff.py` are sha256-identical to the current checkout, so the
  mutation run describes the reviewed code.
- Confirmed zero drift between `before-review-fingerprints.json` (515 files) and the working
  tree for all nine watched files including every changed file and its named dependencies.

### Diff engine probes — all passed
- Exhaustive 90-pair sweep over `("", "\n", "a", "a\n", "b", "b\n", "\n\n", "a\nb", "a\nb\n",
  "x\n\ny")`: every hunk's `old_count`/`new_count` equals the number of visible `" "`/`"-"`
  and `" "`/`"+"` lines, and no hunk ever begins with a marker.
- 4 000 randomized truncation trials: `changed` never exceeds `changed_budget`, `chars` never
  exceeds `char_budget`, no marker is orphaned or split from its line, no marker is invented,
  and `_recount` always reproduces the visible counts.
- `_truncate` over 168 budget combinations: `omitted_lines` and `omitted_chars` are exact and
  never negative; kept-changes + omitted-changes always equals total-changes.
- Model/terminal agreement: `presentation.text.unified_text` carries the marker verbatim and
  leaves the `--- / +++ / @@` headers intact.
- JSON: `DiffReport.to_dict()` → JSON → `from_dict()` is lossless with a marker present, and
  the top-level key set is unchanged.

### Resolver probes — all passed
Full sweep over all 10 real registry agents, building scenarios from the agents' own declared
roots (absolute/system roots never touched):
- Every SHADOWED candidate names a real winner; none falls back to the generic
  "Suppressed by a higher-priority copy." string.
- Every SHADOWED cites the winner's `rule_id` and `evidence`, never the loser's own root.
- `codex` (merge) and `omp` (ambiguous) produce no SHADOWED and no suppression claim.
- Nested scenarios still produce explained shadows for all eight shadow-policy agents.

### Independent correctness of the pinned agents table
Re-derived every row from the registry TOMLs themselves rather than trusting the golden:
10/10 agents present, and `name`, `id`, `collision_policy`, `policy_evidence` and root counts
all match. The one apparent mismatch (`omp`) is a cell that wraps across two table lines —
the text matches once joined. The pinned snapshot is right, not merely self-consistent.

## Blockers

None.

## Non-blocking suggestions

1. **Inline snapshot constants bypass the sanctioned regeneration path.**
   `tests/test_render_snapshots.py::_check` writes goldens to `tests/fixtures/snapshots/`
   under `--update-snapshots` and asserts `str(home) not in rendered`. The two new `agents`
   pins are module-level string constants, so the AGENTS.md §2 command
   `pytest tests/test_render_snapshots.py --update-snapshots` does nothing for them and the
   machine-path guard does not apply. Risk is low (the agents table contains no paths) and
   this is not a contract breach — AGENTS.md §2 names only scan/why/diff, and Stage F item 3
   asks for "an actual rendering test". But a future registry edit means hand-editing two
   large box-drawing constants by hand.

2. **Duplicated agents assertions.** `test_render_snapshots.py::test_render_agents_snapshot_pinned`
   and `test_stage_f_repairs.py::test_render_agents_pins_real_registry_output` assert the same
   constant through the same `_render`/`Console` path; the markup-escaping test is likewise
   duplicated. Both modules import the constants from each other, so the duplication buys
   maintenance cost and no extra coverage. Coordinator already flagged this; agreed, not a
   defect.

3. **Stale comment above the resolver call site.** `skill_lens/core/resolver.py:790-791`
   still reads "The winning copy explains every shadow, so it is resolved first and passed
   to the rest" — describing the `winner = next(...)` line that this change removed. It now
   sits above a blank line, and `_sort_resolutions` sorts after every resolution is built, so
   "resolved first" is not what happens. Worth rewording to state the new contract: the
   winner comes from `_active_roles` and is independent of presentation state.

4. **The fix is slightly wider than the docstring claims.** `_split_lines` also repairs the
   empty↔newline case: previously `""` versus `"\n"` produced zero hunks, i.e. a file reported
   as `modified` with an empty body — the same F15 symptom in a second disguise. Verified
   fixed. Correct, but undocumented.

5. **Consumer-visible JSON shape.** No key changed, but `lines[]` may now contain an element
   whose first character is neither `" "`, `"-"` nor `"+"`. External consumers that classify
   `lines` by first character must handle it. `models/diff.py` now documents this; worth a
   CHANGELOG line when Stage H reconciles documentation.

6. **Marker characters now count against `MAX_CHARS_PER_REPORT`.** A report can in principle be
   flagged `truncated` where it previously was not, if the budget is exhausted within 32
   characters of the limit. Practically unreachable; model and truncation accounting stay
   mutually consistent, which is the property that matters.

## Risks / limits of this review

- The full suite was not re-run; the coordinator's direct gates were assessed as supplied, as
  the brief permits. The 14 mutation controls independently re-ran 14 of the new tests and
  corroborate a meaningful subset.
- The mutations prove the *selected* guards fail when broken; they are not an exhaustive
  correctness proof. My probes are property-style and adversarial but still not exhaustive.
- No Linux/CI/Python-version matrix claim is made or implied.
- Upstream served identity and model-family diversity remain unverified; only the configured
  target and its availability were confirmed.

## Concessions

- Withdrawn: an initial suspicion that `causal_winner` gated on `coexist_policy` could leave a
  SHADOWED candidate with no winner. `_role_for_active` yields SHADOWED only when
  `coexist_policy not in _COEXISTING_POLICIES`, or for opencode, whose policy is `shadow` —
  so the hole is unreachable. Confirmed empirically across all 10 registry agents.
- Withdrawn: an initial suspicion that `winner` (previously "first ACTIVE candidate") could
  diverge from the new top-rank winner and silently change existing shadow output. Traced all
  branches: the only behavioural delta is the nested-winner-displayed-as-COEXISTS case, which
  is precisely the F16 fix.
- Withdrawn: an initial suspicion that a `\`-prefixed detection in `_fit_hunk` could misfire on
  real content. Every emitted line carries a `" "`, `"-"` or `"+"` prefix, so a marker is the
  only line that can begin with `\`. Verified exhaustively.
