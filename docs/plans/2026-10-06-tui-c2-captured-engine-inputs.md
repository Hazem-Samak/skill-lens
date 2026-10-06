# Plan: TUI C2 — explicit captured engine inputs

Status: Agreed
Authorization: Hazem Samak requested the planning loop with Antigravity and OpenCode Space Bunny, with Sol/Hermes judging their findings. This authorizes review and freezing this plan, not product implementation, pushing, or publishing.
Reference: `f9decabc55288037e0cb41d94a9e444f46d1a2b8` (agreed-plan freeze; this line is recorded in a following plan-only provenance commit).
Source baseline: `f659d5682f0324a2fbb9f73bfb74807925364e42` on `main`.

## Outcome

Prepare the existing report engines to accept already-collected skill data instead
of quietly consulting the machine again. This is like teaching them to work from
a photograph. C3 will take and validate the photograph; C2 does not build that
capture service or any screen.

The current CLI continues to behave exactly as before when new inputs are omitted.
Explicit empty inputs mean empty data, not permission to perform a fresh read.

## Current state

The authoritative contract is `FULL_SCREEN_TUI.md` §21.1–21.3, the C2 acceptance
row in §21.6, and assignment C2 in §22 (`FULL_SCREEN_TUI.md:1691`). The base
specification's filesystem, diff, comparison, diagnostics and read-only rules
remain binding. P1, P2, P3 and C1 have shipped; C1 is commit `c45e654`.

Observed on the source baseline:

- `core/discovery.py:228` defines the live, list-backed `DiscoveryIndex`; its
  `all_agents()` derives a fresh set from entry hits.
- `core/resolver.py:163` and `:184` already provide the C1 identity helper and
  pure settings decoder. `_candidates_for()` still reads settings unconditionally
  (`:216–225`); `resolve_skill()` has no captured-overrides parameter (`:581`).
- `core/diff.py:102` collects files from disk and `:392` accepts only a live index
  and registry. The builder has early returns and equal-hash/no-baseline shortcuts
  (`:413–456`) that must not conceal missing captured keys.
- `core/compare.py:23` already accepts optional index/registry in its builder,
  but its live wrapper (`:160`) always loads the registry and discovers.
- `core/doctor.py:63` builds from a live index but still performs lockfile and
  symlink/path checks. Its wrapper (`:461`) always discovers. The evidence helper
  calls `list_agents()` even when given replacement definitions (`:405–436`).
- Existing CLI callers use the live wrappers (`cli.py:277`, `:315`); they need
  no signature or output change. Existing positional engine arguments must remain
  accepted.
- Doctor's existing builder/evidence helper can consume a dictionary or an
  iterable of definitions. Preserve that behaviour; do not narrow a currently
  supported input as a side effect of this work.
- `core/snapshot_models.py` and the capture service do not yet exist.

Baseline checks, rerun during planning using the existing `.venv` (Python
3.11.16): `pytest --cov=skill_lens` passed 491 tests, coverage 93.18%; `mypy`
passed over 25 source files; `ruff check .` and `ruff format --check .` passed
(72 files formatted). The tree was clean before drafting.

### Review level and responsibilities

C2 is high risk because it touches already-reviewed engines and preserves their
compatibility boundaries. The maintainer explicitly selected this two-critic
roster instead of the default full council:

| Owner | Task |
| --- | --- |
| Sol/Hermes | Inspect, write the plan, reproduce findings, judge each one, and freeze only the plan. No product code. |
| Antigravity | Independent read-only feasibility review: data types, import direction, engine changes, C2/C3 boundary. |
| OpenCode Space Bunny | Independent read-only contract/test review: empty inputs, missing inputs, shortcut cases, CLI compatibility and test strength. |
| Hazem | Decide only if a reviewer uncovers a requirement or scope change. |

Both critics receive the same draft and source baseline, different questions,
and the exact read-only guard from `docs/process/council.md`. Start both before
waiting. Record the effective models, not merely requested names. The coordinator
is not an independent critic or a dispatched worker.

### Known boundaries, not open product questions

- Doctor continues to use a live `DiscoveryIndex` during capture. C2 does not
  make Doctor pure over a frozen index; C3 stores its completed report for
  navigation. Do not pass a frozen index to Doctor or add captured-lock inputs.
- Snapshot publication owns/deep-copies nested data in C3. Defining frozen
  dataclasses here does not establish deep immutability; do not advertise it.
- No requirement choices are currently unresolved. A source/contract conflict
  must be escalated before implementation expands scope.

## Scope and boundaries

### Planning edits now

Only this file:
`docs/plans/2026-10-06-tui-c2-captured-engine-inputs.md`.

Critic briefs, launch receipts, raw reports and any throwaway probes belong under
`/Users/corvette/.hermes/cache/scratch/`, outside the checkout. Critics do not
create or edit repository files, including this plan.

### Allowed edits during a separately authorized C2 implementation

Product files:

- Create `skill_lens/core/snapshot_models.py`.
- Modify `skill_lens/core/resolver.py`.
- Modify `skill_lens/core/diff.py`.
- Modify `skill_lens/core/compare.py`.
- Modify `skill_lens/core/doctor.py`.

Tests, only for the named C2 behaviours:

- `tests/test_snapshot_inputs.py`.
- `tests/test_compare.py`.
- `tests/test_doctor.py`.
- `tests/test_phase2_gate.py`.
- `tests/test_phase3_gate.py`.
- `tests/test_phase4_gate.py`.
- `tests/test_phase6_gate.py` (only the supplied-registry evidence boundary).

The coordinator may record C2 proof and any technical decisions in this plan.
No other documentation, fixture, dependency or product file is authorized by C2.

### Unchanged

Public model fields/JSON, CLI arguments/defaults/exits, resolution/identity and
settings-key rules, canonical grouping, variant ordering, binary policy, newline
normalization, diff baseline/truncation, doctor finding wording/severity/evidence,
and registry definitions remain unchanged. No Rich, Typer or Textual in new core
code; no new dependencies, public serialization format, disk cache or writes to
user skills.

Do not edit discovery, system, paths, hasher, parser, scanner, registry TOML, CLI,
rendering, packaging or the lock. No `snapshot.py`, cancellation API, presentation
package or TUI screens in C2. Those are later assignments.

## Implementation steps

Antigravity is the future implementer; Sol/Hermes owns review and any acceptance
commit. This planning request does not dispatch implementation. After separate
authorization, follow `docs/process/implementation-loop.md` one assignment at a
time, with this plan and its recorded frozen reference.

### 1. Define inert snapshot data structures

Create the four dataclasses from `FULL_SCREEN_TUI.md` §21.2 exactly:
`CapturedFile`, `CapturedInput`, `FrozenDiscoveryIndex`, `SessionSnapshot`.
All use `frozen=True, slots=True`, with the specified fields/types and no new
serialized output. Reuse existing discovery, registry and report classes.

Implement `FrozenDiscoveryIndex.all_agents()` like the live index, deriving a
new set on every call. Its entries/unreadable roots are tuples, not lists.

Use future annotations and `TYPE_CHECKING` for report references as necessary,
including `ScanReport`. Resolver, diff and compare need a **runtime import** of
`FrozenDiscoveryIndex` wherever an `isinstance()` guard uses it; importing that
class only under `TYPE_CHECKING` would raise `NameError` at runtime.
The dependency direction is engines → snapshot models → discovery/model types.
Snapshot models must not runtime-import resolver, diff, compare, doctor or scanner;
discovery does not import snapshot models or any session service. Do not add
`Any` or suppressions to evade strict typing. Construct a minimal complete
`SessionSnapshot` in tests so every declared field is exercised. C3, not these
constructors, performs ownership copies and read-only mapping publication.

### 2. Add explicit resolver settings

Implement the exact §21.3 `resolve_skill()` signature: retain all existing
positional parameters, widen index to `DiscoveryIndex | FrozenDiscoveryIndex |
None`, and add keyword-only `disabled_overrides: frozenset[str] | None = None`.

Before loading registry, discovering or reading settings:

- A supplied overrides set requires index and registry both non-`None`.
- A frozen index requires registry and overrides both non-`None`.
- Violations raise `ValueError` with a clear explanation of the missing input.

Widen `_candidates_for()`'s index annotation to
`DiscoveryIndex | FrozenDiscoveryIndex` and add keyword-only
`disabled_overrides: frozenset[str] | None = None`. Thread the public argument to
that helper. Doctor's helpers stay live-index-only; do not widen them.
Only `None` calls the existing live loader. An empty frozenset stays empty.
Keep override matching on `entry.name`,
not the agent lookup name; reuse C1 settings decoding without duplicating it.
All ranking, state, identity, path and labeling algorithms stay unchanged.
Direct `resolve_skill()` retains its explicit cwd argument in the report, even
with a supplied index. C3 passes the snapshot's home/cwd explicitly; C2 does not
introduce an index-overrides-argument rule for direct builders. Companion-input
checks all precede reads; tests need not prescribe an order when several inputs
are missing at once.

### 3. Add captured diff files without altering comparison

Implement the exact §21.3 `build_diff_report()` signature, accepting the live or
frozen index plus keyword-only
`captured_files: Mapping[str, tuple[CapturedFile, ...]] | None = None`.

Before any live work, supplied captured files require index/registry; a frozen
index additionally requires captured files. Use `ValueError` for violations.
After selecting the requested name's entries, **before the entry loop**, validate
that every participating
entry has its `canonical_key(entry)` in a supplied map, including a baseline,
a single/identical copy, an invalid/no-baseline copy and an unreadable copy.
A missing key raises even when an optimization would otherwise skip collection.
An empty map with no selected entries is valid; an empty tuple at a present key
means an empty copy. Do not require unrelated skill groups merely to answer one
diff request.

Extend `_copy_files(entry, *, captured_files=None) -> dict[str, _Collected]`,
typing the new parameter as `Mapping[str, tuple[CapturedFile, ...]] | None`.
Pass it explicitly at both baseline and non-baseline collection call sites.
In `_copy_files()`, branch on `captured_files is not None` before any `Path`
file probe or collector. Turn each captured file into the existing `_Collected`
using C1 `normalized_text()` and its captured fingerprint; invalid UTF-8 means
binary (`text=None`), and binary bytes never enter printable hunks. Empty tuples
return an empty dictionary. The live branch and streaming hasher stay intact.

Keep `_files_between`, hunk construction, valid Variant A baseline, folder-name
grouping, equal-hash shortcut, added/removed paths, sorting and both truncation
budgets unchanged. Do not calculate an independent definition of newline
normalization or re-hash files on disk in the captured branch.
Like resolution, direct `build_diff_report()` preserves its explicit home/cwd
arguments in the report. C3 passes coherent snapshot arguments; only the wrappers
derive their report paths from a supplied index.

### 4. Extend compare and doctor entry points

Compare: widen its builder and any affected index consumers to the frozen index.
Add keyword-only `index`/`registry` to `run_compare()` exactly as §21.3. A frozen
index without registry raises before registry loading. Select the registry with
an explicit `is not None` check, validate both ids before a walk, and discover
through `live_discovery()` only when index is `None`. Pass the chosen registry to
that discovery. With a supplied index, report home/cwd from the index, not the
ambient environment or a competing wrapper cwd. Leave classification, names,
ordering and error messages unchanged. Same-agent rejection belongs to C3's
`snapshot_compare()`, not a new CLI rule here.

Doctor: add keyword-only live `index`/`registry` to `run_doctor()` exactly as
§21.3. Use a supplied index directly and its home/cwd; call `live_discovery()`
only when index is `None`, passing supplied registry definitions through. Pass
the optional registry to `build_doctor_report()` for all evidence checks.
Only call `list_agents()` inside `_registry_evidence_findings()` when registry
is `None`; an explicitly empty dictionary/iterable produces no registry findings
and does not load packaged definitions. Preserve existing supported input shapes
and evidence sorting. Leave lockfile/symlink/path reads and finding algorithms
alone; they are permitted in pre-publication Doctor computation.

### 5. Test first, then prove the guards fail when broken

For each new behaviour, add a failing test before implementation and confirm
it fails for the intended missing behaviour. Use only `mock_home`/`tmp_path`,
paths.py-based isolation and existing fixture builders. Make home and project
cwd distinct when checking path/argument plumbing. Prepare expected reports
before patching read boundaries, within a scoped monkeypatch context.

The acceptance matrix below is mandatory. Extend tests where the behaviour
belongs; do not add a parallel engine implementation to tests. Capture test files
as full bytes with C1 helpers only in local fixtures, not a production-like capture
service. Verify both complete report dictionaries and `models.dumps()` output,
not a handful of headline fields.

Mutation-test the new guards in a disposable scratch copy or scoped in-memory
patches: deliberately replace `is not None` with truthiness for overrides/files/
registry; remove each missing-input guard; return empty for an absent captured
key; route captured collection through the live branch; ignore supplied wrapper
index/registry; unconditionally load Doctor's packaged definitions. Each named
protecting test must fail on its corresponding mutation, then pass restored.
Record results; a surviving relevant mutation blocks C2. Do not perform mutations
on the user's active checkout. Capture/ownership/cancellation mutations wait for
C3; presentation/UI mutations wait for their own assignments.

Name the exact branch and protecting test for each mutation. For diff, distinguish
the public companion-input guards, registry selection, and the private collection
branch. An empty index returns before collection, so its `{}` case alone cannot
kill a mutation inside `_copy_files()`. To exercise that branch, also supply a
populated `dict` subclass whose `__bool__()` returns `False`, with a complete map
for differing copies, and ban the live collector. This is a valid `Mapping` under
the declared API; only `None` may select live reads. The correct branch matches
the expected captured report; its truthiness mutation reaches a banned read.
For diff's empty registry, ban `diff.load_registry` explicitly: otherwise a
packaged read is invisible when the supplied index makes its definitions unused.
No equivalent-mutation exemption replaces these concrete read-boundary tests.

### 6. Verify and hand back C2, not later phases

The implementer runs focused tests, then all four repository gates, and reports
using `docs/process/council.md` §4. The coordinator reads all changed and new
files, independently repeats the gates, and obtains implementation review from
two different model families for this high-risk phase. That future review is not
satisfied by these planning reviews.

Account for exact allowed paths, run `git diff --check`, and compare pinned output
without regeneration. Record actual tests/coverage/mutations and any deviations
in this plan. A contract conflict returns to Hazem for a concrete amendment;
passing a subset of checks is not acceptance. The implementation commit requires
separate authorization and is owned by the coordinator, not the worker.

## Acceptance

### C2-specific proof matrix

| Location | Required observable proof |
| --- | --- |
| `tests/test_snapshot_inputs.py` — model tests | Four exact frozen/slotted types; tuple-backed index; `all_agents()` agrees with live hits. Mutate its first returned set with a sentinel and assert the next result lacks that sentinel; complete session field construction; no filesystem work in model operations. Do not claim deep immutability. |
| `tests/test_phase2_gate.py` — resolver explicit emptiness | Synthetic live settings disable a skill; explicit `frozenset()` keeps it enabled while the live settings loader is patched to raise. A nonempty captured override disables the same directory key; differing folder/frontmatter names do not migrate settings keys. |
| `tests/test_phase2_gate.py` — resolver missing inputs and parity | Supplied empty/nonempty overrides without index or registry raise `ValueError`; frozen index missing registry or overrides raises before patched registry/discovery/settings readers run. An empty supplied registry is not replaced by packaged definitions (unknown ids remain errors). Preserve the explicit cwd argument for direct-builder parity; C3 supplies coherent snapshot arguments. |
| `tests/test_phase3_gate.py` — diff captured parity | Complete reports/JSON equal unchanged live reports on differing directory copies with nested assets, added/removed files, standalone files, CRLF/lone-CR/NUL/BOM cases and invalid UTF-8 binaries, plus baseline/no-baseline/unreadable and truncation cases. No binary payload is printed. |
| `tests/test_phase3_gate.py` — diff explicit emptiness and completeness | Present empty tuples remain empty under a patched live collector. An absent selected copy key raises, including single-copy/equal-hash/no-baseline/unreadable shortcuts. Use an empty supplied index and `{}` files against a fake home that does contain the requested name; ban registry/discovery/collection reads and assert captured not-found output. Also use `{}` files when index or registry is missing: raise `ValueError` before reads. Frozen calls lacking files/registry raise before reads. |
| `tests/test_phase3_gate.py` — diff falsey mapping and empty registry | A complete populated file map whose `__bool__()` returns `False` on genuinely differing copies must take the captured branch. Within the report-call patch context, ban `diff._collect`, `diff._read_normalized`, `diff.iter_files`, `diff.hash_file` and `Path.is_dir`. **Do not patch `_copy_files` itself:** the real new branch is under test. Separately use `registry={}`, a supplied index and complete captured files with `diff.load_registry` patched to raise: reports still match. These tests kill the respective collection/registry truthiness mutations; output parity alone cannot prove no read. |
| `tests/test_compare.py` — injected builder and wrapper inputs | Directly test both builder and `run_compare()`, not only the CLI. Cover live index-only, registry-only, both and neither; frozen index plus registry skips patched discovery/loaders; missing registry for frozen calls raises first; explicit `{}` is not replaced (same readable unknown-agent error); ids rejected before scanning. Give index.home, index.cwd and wrapper cwd three distinct fixture paths, assert report home/cwd equal the index, and ban ambient home/cwd lookups. Live defaults retain complete-report/JSON parity. |
| `tests/test_doctor.py` / `tests/test_phase4_gate.py` — wrapper inputs | Direct wrapper tests in `test_doctor.py`; integration parity in `test_phase4_gate.py`. Supplied live index reuses its home/cwd without discovery, even with a differing wrapper cwd. Exercise index-only, registry-only, both and neither. For registry-only `{}`, create malformed/budget-relevant skills on disk and assert no skill findings: the empty registry governs discovery; lockfile info can remain. Ban `skill_lens.core.discovery.load_registry` during that empty-registry discovery. |
| `tests/test_doctor.py` / `tests/test_phase6_gate.py` — evidence definitions | Supplied dictionary/iterable (including empty) bypasses `list_agents()`; a synthetic inferred agent still produces the unchanged informational finding. Patch `skill_lens.registry.loader.list_agents`: Doctor imports it locally inside the function; `doctor.list_agents` is not a module attribute. Doctor's unrelated lock/path reads are not falsely banned. Keep Phase 6 edits limited to this existing evidence boundary. |
| Existing phase/CLI/snapshot tests | All old tests, 17 render snapshots and 16 JSON goldens stay unchanged; CLI defaults, usage errors and exit policy are unaffected. Counts were enumerated programmatically during planning; only one JSON golden is a diff golden. |
| Scratch mutation evidence | Each new relevant guard above is broken once and a named test fails; the restored final implementation passes. |

The required §21.6 `test_explicit_empty_inputs_never_fall_back` may be split into
clearly named engine-specific tests so failures identify the broken boundary.

### Repository gates

Use the existing repository environment; do not install or update dependencies.
The focused command is a fast first check, not the whole affected surface;
`test_fixtures.py`, `test_phase5_gate.py` and all other tests run in the full gate.

```bash
source .venv/bin/activate
pytest tests/test_snapshot_inputs.py tests/test_compare.py tests/test_doctor.py tests/test_phase2_gate.py tests/test_phase3_gate.py tests/test_phase4_gate.py tests/test_phase6_gate.py tests/test_cli.py tests/test_render_snapshots.py
pytest --cov=skill_lens
mypy
ruff check .
ruff format --check .
git diff --check
```

Expected: focused and full suites pass; coverage stays at or above the configured
90% floor; strict mypy and Ruff are clean; all existing pinned output is unchanged.
Report observed counts, never the baseline count as a prediction.

## Review decisions

The two initial reports are complete. Antigravity returned `pass` / `sound`,
with no blockers. Space Bunny returned `changes_required`, naming two test gaps.
Sol/Hermes reproduced the control-flow and read-boundary claims before deciding.
The adjudicated changes below are contract-preserving test/implementation
clarifications, not a change to §21 or C2 scope. Space Bunny's targeted second
review returned `pass`, with no blockers, and withdrew its two original blockers
and incorrect cwd/count/model-name claims. Sol/Hermes accepts the revised plan.

### Antigravity findings

| Finding | Decision and verified reason |
| --- | --- |
| S-1: private helper index types | **Accept resolver portion; reject Doctor widening.** `_candidates_for` needs the union under strict typing. Doctor explicitly stays live-only (§21.3), so widening its helpers would contradict the boundary. |
| S-2: `_copy_files` signature | **Accept.** Name its keyword-only captured-map parameter and both call sites; conversion remains in this helper as §21.3 requires. |
| S-3: Doctor stays live | **Accept as confirmation.** Source `doctor.py:300,310,353` shows its permitted pre-publication filesystem checks. |
| S-4: guard ordering | **Reject prescribing an order among simultaneous omissions.** All checks precede reads and raise `ValueError`; that is the contract. No product behaviour depends on which missing input is named first. |
| S-5: override directory key | **Accept as confirmation.** `resolver.py:231` and §21.3 agree on `entry.name`; the test preserves it. |
| S-6: upfront map validation | **Accept clarification.** State explicitly that selected-copy keys are checked before the entry loop, including shortcuts. |
| S-7: compare wrapper inputs | **Accept as confirmation.** Supplied definitions/index and early agent validation match §21.3 and current Phase 4 invariants. |
| S-8: conditional Doctor registry read | **Accept as confirmation.** `doctor.py:431–436` reproduces the unnecessary packaged read even with replacement definitions. |
| S-9: effective model | **Record accurately.** The initial Antigravity review reported Claude Opus 4.6 Thinking, not Gemini. The user switched the session to Gemini 3.8 Flash High and explicitly required that model for future agy use; the runtime banner confirms the switch. The initial review remains independent under the user's instruction to continue normally. |
| S-10: import direction | **Accept acyclic direction; reject TYPE_CHECKING-only frozen-index imports.** Runtime `isinstance` needs the class bound at runtime. A scratch Python probe raises `NameError` with a typing-only import. Report references stay typing-only to prevent engine import loops. |
| S-11: allowed files | **Accept as confirmation.** Matches §22 C2; no source/fixture/dependency expansion. |
| S-12: tuple-backed index | **Accept as confirmation.** Existing consumers iterate; the union supports tuple/list entries without changing discovery. |

### Space Bunny findings

| Finding | Decision and verified reason |
| --- | --- |
| B-1: empty-file mutation strength | **Accept gap; replace the proposed discriminator.** `{key: ()}` is truthy. The proposed empty-index/empty-map test returns not-found in both correct/mutated collection branches because `_copy_files` is never called. Keep that no-fallback boundary test, add explicit empty-map companion guards, and use a valid falsey populated Mapping on differing copies to kill the collection mutation. Scratch execution confirms the latter catches the banned live read. |
| B-2: empty diff registry read | **Accept option (a), not exemption.** With a supplied index, definitions are unused but `registry or load_registry()` still performs a forbidden packaged read. The real current builder passes an empty-registry loader sentinel; an in-memory AST mutation reaches it. Add the dedicated sentinel test. |
| S-1: test file locations | **Accept.** Name each exact allowed test file; there is no `test_resolver.py` or `test_diff.py` to invent. |
| S-2: direct compare wrapper tests | **Accept.** Add the proofs in `test_compare.py`; CLI output alone cannot prove no loader/discovery call. |
| S-3: conflicting wrapper cwd | **Accept.** Use three distinct fixture paths for index home/cwd and wrapper cwd; report must use index paths. Covers the actual Phase 4 C-04 plumbing risk. |
| S-4: resolver index should override cwd | **Reject.** Current `resolve_skill` reports its explicit argument (`resolver.py:627`), independently reproduced with a different index cwd. §21.3's index-home/cwd rule names the wrappers; C3 supplies coherent snapshot arguments to direct builders. Reinterpreting the direct builder would change existing semantics. |
| S-5: empty Doctor registry assertions | **Accept.** A skill-populated fake home plus `{}` registry must yield no skill-derived findings; retain permitted lock info and ban packaged registry loading. |
| S-6: independent all_agents sets | **Accept concrete assertion.** Mutate a returned set and confirm the next lacks the sentinel. No need for an extra cache API. |
| S-7: private helpers | **Accept resolver widening and diff map parameter; reject describing `_copy_files` as an index consumer.** It takes `DiscoveredEntry`, a shared type; no index union belongs in its signature. |
| S-8: runtime imports | **Accept.** Confirmed with the runtime guard probe; keep models' engine/report references typing-only. |
| S-9: pinned-output risks/counts | **Accept parity/read-before-regenerate warning; reject counts.** Enumeration gives 17 text snapshots, 16 JSON goldens and one diff JSON golden, not 17 JSON/two diff goldens. Existing normalization/truncation tests remain required. |
| S-10: focused command completeness | **Accept clarification.** It is not exhaustive; full pytest includes fixture and packaging gate tests. |
| Model-name objection | **Reject the claim that “Free” means the max variant was not used; record the exact identity instead.** `opencode debug config` shows provider `opencode`, model `space-bunny-free`, variant `max`, and the actual review terminal banner shows `Space Bunny Free … max`. Max is the reasoning variant, not a separate model ID. No model/config was changed. |
| Six CONCEDED claims | **Record as withdrawn, not remaining defects.** Scanner widening, the already-fixed compare argument inversion, keyword-only migration of existing resolver parameters, adding a compare home argument, snapshot count doubts and source-line doubts were withdrawn after source inspection. No scope change follows from them. |

### Reproduction evidence

Throwaway script (not C2 implementation):
`/Users/corvette/.hermes/cache/scratch/skill-lens-c2-planning-20261006/verify_review_claims.py`.
It uses existing fixture builders and engines, scratch-only fake homes, scoped
in-memory seams/AST mutation, and bans selected live reads. Observed results:
empty-index case misses the collection mutation (zero collector calls in both
branches); falsey populated mapping catches it; empty-registry sentinel catches
the loader mutation; direct resolver keeps the explicit cwd; typing-only runtime
guard raises `NameError`. Source files remain unchanged. This validates the
planning decisions, not future C2 acceptance.

### Targeted second review and final decision

Space Bunny rechecked the amended draft under Task `task_ccb8f6ba6b9c`, Dispatch
`ctx_a9becfd9c6af`: `VERDICT: pass`, `BLOCKERS: []`. The full report is stored
outside the checkout at
`/Users/corvette/.hermes/cache/scratch/skill-lens-c2-planning-20261006/space-bunny-review-final.txt`.

| Second-review suggestion | Final decision |
| --- | --- |
| S-1: name falsey-map test patch symbols | **Accept.** Name the live collector/read/walk/hash/probe symbols and explicitly keep real `_copy_files` unpatched. The scratch seam is a planning discriminator only, not the future implementation test. |
| S-2: Doctor evidence patch target | **Accept.** The local import at `doctor.py:429` binds from `registry.loader.list_agents`, not a nonexistent Doctor module attribute. Discovery's loader is module-bound at `discovery.py:30`, so patch it there. |
| S-3: direct diff path arguments | **Accept clarification.** `diff.py:417–418,485–486` preserves explicit arguments, like the resolver. This is not a new index precedence rule. |
| S-4: runtime get_type_hints | **Defer to C3 only if it introduces annotation introspection.** C2 needs neither runtime type-hint evaluation nor snapshot serialization; no new API or runtime import is added for an unused case. |
| S-5: fixture names | **Accept confirmation.** `tests/conftest.py` defines the named isolated fixtures; no fixture invention is needed. |
| S-6: shortcut reachability | **Accept confirmation.** The baseline's single-copy/equal-hash/no-baseline/unreadable branches are real and the upfront selected-key tests address them. |

An optional additional Antigravity/Gemini recheck was not dispatched: the current
session reported “Individual quota reached” after the completed initial review.
No other model was substituted. The original Antigravity feasibility review and
both Space Bunny reports are complete; the coordinator's verified, scope-preserving
corrections and the targeted pass close the planning loop. This limit affects
future Gemini implementation availability, not a missing initial review.

Final planning gate on the unchanged product tree: 491 tests passed, 93.18%
coverage; strict mypy passed (25 source files); Ruff lint and format checks passed.
`git diff --check` was clean and tracked product/fixture changes were empty.
These are baseline/parity checks, not proof that future C2 code exists.

Reviewer cleanup was requested through `worker-release` after exact Task/Dispatch
completion validation. Orca retained the attached Antigravity terminal as
`external_terminal`; it retained the original OpenCode terminal as `user_takeover`
and its reused second-review Dispatch as `external_terminal`. Both are settled,
not active review workers. Respect these protected ownership receipts rather than
closing the user's terminals; verify no reclaimable owned worker before finishing.

### Process decisions

- The user-selected two-critic roster is explicit; do not silently add Cline,
  MCode, Pi or a different OpenCode model.
- The current Orca `worker-start --help` has no agent-argv forwarding flag.
  Antigravity's required `--mode plan` therefore needs an explicitly launched
  terminal attached through `worker-start --terminal`, rather than an invented
  `worker-start --mode` flag. Future agy launches explicitly use
  `--model gemini-3.8-flash-high` as requested; confirm effective identity when
  reusing the user's already-switched session. OpenCode's exact model is
  `opencode/space-bunny-free`, reasoning variant `max`, verified against both
  configuration metadata and the actual review terminal banner.
- A Git commit cannot contain its own final hash. Freeze the agreed plan first,
  then make a plan-only provenance commit that records the first commit's hash
  here. These two documentation commits do not authorize product work. The
  implementation baseline check must explicitly account for the provenance-only
  second commit; no silent re-freezing or product-tree drift.

## Done when

Planning is complete only when both actual critic reports are read, every finding
has an evidenced accept/reject/defer decision, no blocker remains, all four gates
are verified on the unchanged product tree, the agreed plan is committed with its
frozen reference recorded, and every reviewer has a documented reuse/release or
protected-retention outcome with no coordinator-owned reclaimable worker left.
Orca may retain externally attached or user-taken-over terminals; do not close
those against its ownership receipt. Report any remaining requirement choice
rather than calling a draft frozen.
