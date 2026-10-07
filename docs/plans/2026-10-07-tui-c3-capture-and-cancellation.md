# Plan: TUI C3 — capture and cancellation

Status: Agreed
Authorization: Hazem requested “let's start C3”, with Agy implementing and OpenCode Space Bunny Free plus MCode MiniMax M3.1 F reviewing. Hermes coordinates, plans, verifies, judges and commits accepted work; it does not write product code. No push, release or publication is authorized.
Reference: `a5be5bf7fb9f427abfbbf67ce57cb3532e3faf87` (agreed-plan freeze; this line is recorded in a following plan-only provenance commit).
Source baseline: `a1d60e8f99c0fa23e0a9d4b93ebd75454f5eef8c` on `main`.

## Outcome

Take a complete, checked photograph of the skill inventory, files, settings and
health findings. Browsing that photograph stays consistent even if someone edits
the files afterward. A new capture sees those changes together. A cancelled or
inconsistent capture returns no photograph, leaving publication to the later UI.

C3 supplies capture and report services, not an interface. Existing CLI behavior
and output remain unchanged.

## Current state

Authoritative contract: `FULL_SCREEN_TUI.md` §21.1–21.4, C3 tests in §21.6,
and assignment C3 at `:1692`. Base specification §4–7, AGENTS.md, the process
loops and the Phase 2/4 findings remain binding. C1/C2 are accepted.

- `core/snapshot_models.py:21–68` has all four inert data classes. Publication
  still needs owned containers, tuples and read-only mapping tables.
- `core/discovery.py:402–460` scans ordered roots/entries and merges canonical
  copies. Private listing/building helpers do not accept cancellation yet.
  `DiscoveredEntry.variant_label` exists but discovery normally leaves it None;
  engine labels are derived through `labels_for_entries`. Preserve that behavior.
- `core/hasher.py:38–123` walks files and streams text/binary in 64 KiB chunks.
  C1 byte helpers and framing already exist at `:126–160`.
- `core/system.py:83–98` obtains lazy effective home and delegates discovery.
  Its lock path helper is `:37`; `shared_library` is `:27`.
- `core/parser.py:39–63` selects SKILL.md before skill.md. Original parse source
  paths retain alias identity. `parse_skill_bytes` is `:206`. ParseResult equality
  excludes frontmatter (`models/parsing.py:84`), and to_dict excludes body.
- C2 resolution, diff and compare accept frozen inputs and reject missing
  companion inputs. `resolver.lookup_name_for_entry` and the pure settings
  decoder are existing shared rules, not algorithms to recreate.
- Scan counts live symlinks (`scanner.py:148–156`). Doctor reads lock/path/link
  state even with an injected index (`doctor.py:64–89`). Build and validate both
  before publication; navigation must use their stored reports.
- Agent settings paths come from `AgentDefinition.disabled_settings`
  (`registry/loader.py:57`) and currently load as `home / disabled_settings`
  (`resolver.py:207–214`). Capture every configured path even if its decoder
  will ignore it; share duplicate paths in config_inputs.
- `mock_home` is NOT automatic (`tests/conftest.py:53`). Every test calling
  capture/live wrappers requests mock_home explicitly, directly or through a
  fixture that depends on mock_home/sandbox. bare_home leaves the sandbox off and
  is not sufficient: discovery then permits the registry's absolute system roots.
  tmp_path alone does not isolate Doctor's lockfile. C2's accepted plan records
  this previously reproduced safety failure and its correction.

Baseline rerun on the unchanged tree: 515 tests passed, 93.61% coverage; strict
mypy passed over 26 files; Ruff lint and format checks passed (74 files).
These prove baseline parity, not acceptance of unbuilt C3.

### Review and division of responsibility

This is high risk: discovery, cancellation, path/link decisions and already
reviewed engine compatibility. Hazem's explicitly selected two-critic roster
replaces the default full council; do not add other models silently.

| Owner | Work |
| --- | --- |
| Hermes | Inspect, draft/freeze plan, independently verify and reproduce findings, adjudicate and commit accepted C3. No product/test implementation. |
| Agy, gemini-3.8-flash-high | Implement only C3 and its tests after the plan is frozen; own corrections; no commits. |
| OpenCode, opencode/space-bunny-free | Independent planning and fresh-context implementation reviews: consistency algorithm, service behavior, failure cases and proof strength. Record reasoning variant separately. |
| MCode, MiniMax M3.1 Flash | Independent planning and fresh-context implementation reviews: read-only/home safety, ownership, cancellation propagation and compatibility. Verify its exact runtime id/banner; no substitutions. |
| Hazem | Decide only unresolved requirement choices, frozen-plan amendments, scope expansion or non-convergence after two correction rounds. |

Dispatch both critics before waiting. Copy the verbatim council read-only guard
into each task. Record their actual model identity and compare repository byte
fingerprints plus git status before/after; a guard alone does not prove no edits.

### Technical decisions for review

No new user-facing behavior choice is currently required. Review these internal
seams explicitly before freezing:

- Initial supplied-home mismatch is caller misuse: raise ValueError before
  registry/discovery/config reads. Compare the supplied Path to paths.home()
  directly, as the launcher already applied sandbox/cwd validation. Do not
  silently switch homes or alter sandbox state. If effective home changes during
  capture, reject via SnapshotChanged before publication, using its fixed retry
  message. Cancellation is checked before work and between phases.
- Document-to-bytes mapping preserves original parse.source_path for parsing,
  but locates bytes in the canonical captured set. For directories, try the
  source path relative to the original entrypoint first; ValueError from that
  relative-path derivation means no exact key, so try the samefile fallback.
  If its spelling is not
  a captured key, match the selected source to an actually captured file with a
  capture-time samefile check (guard OSError as SnapshotChanged). Check cancellation
  per fallback file and choose the first match in sorted captured-path order. On a
  case-insensitive Mac, parser selection can name SKILL.md while iter_files
  records skill.md. Do not blindly case-fold arbitrary keys: a case-sensitive
  filesystem can hold distinct documents. Standalone documents use their sole
  canonical filename, NOT the alias filename, and still parse with the original
  source string. No source reread or live parser fallback is needed. Retain actual
  captured relative filenames. A genuine missing readable source is a consistency
  failure. Stable no-hash unreadable entries retain their parse and an empty tuple.
  Test aliases, lowercase/case-insensitive spelling and symlinked parents;
  dual-case preference requires two physically distinct files, so condition that
  fixture on filesystem support rather than overwriting one file twice.
- Frozen existing model fields are not deeply immutable. Deep-copy nested parse
  metadata and report containers without changing public model types. Published
  data is session-owned and consumers must treat it read-only; top-level maps
  enforce read-only access, not every nested object.
- Consistency is observable double-pass validation, not an OS transaction.
  Changes completely undone between checks can be unobservable. No automatic
  retry, silent truncation, disk spill, write or stronger atomicity claim.

## Scope and boundaries

Planning/proof documentation edits: only this plan. Raw briefs, receipts,
reports, gate output and disposable probes/copies go under
`/Users/corvette/.hermes/cache/scratch/skill-lens-c3-20261007/`.

Allowed implementation files:

- Create `skill_lens/core/cancellation.py` and `skill_lens/core/snapshot.py`.
- Modify `skill_lens/core/discovery.py`, `system.py`, `hasher.py` for optional
  cancellation propagation only; preserve their existing behavior by default.
- Create `tests/test_session_snapshot.py`.
- Extend `tests/test_discovery.py`, `test_hasher.py`, and `test_doctor.py` only
  for the corresponding cancellation/live-adapter behavior. Keep system adapter
  tests in the existing doctor test file; do not invent an existing test_system.py.
- Coordinator records reviews, implementation evidence and decisions here.

No edits to snapshot_models, parser, resolver, diff, compare, scanner, paths,
registry, public models, CLI, render, fixtures/goldens/snapshots, dependencies,
packaging, lock or other documentation. A concrete contract conflict comes back
before expanding scope. No C4 presentation extraction, C5 audit walkthrough,
Textual controller, screen, benchmark redesign, release or publication.

Preserve public JSON fields, positional parameters, CLI defaults/exits, agent
identity/settings keys, canonical merging, variants, ordering, newline/hash
rules, binary handling, diff budgets, Doctor wording/severity and evidence.
No Rich/Typer/Textual imports or new dependencies in the capture/cancellation
modules. Lower-level discovery/hasher/system do not import snapshot.py or UI.

## Implementation steps

Follow the repository implementation loop, one C3 assignment, not the remaining
TUI roadmap. Agy writes tests first for each missing behavior, records intended
failures, implements, runs focused tests and all four gates. Hermes independently
reads all new/changed files and verifies after completion.

### 1. Cooperative cancellation

Implement CaptureCancelled(Exception) and check_cancelled exactly as §21.4.
None/false predicates return normally; true raises CaptureCancelled.

Add the specified keyword-only optional predicate to live_discovery, discover,
iter_files, hash_file, hash_directory and hash_path, retaining all existing
positional parameters. Thread it through private listing/build-entry and
text/binary streaming helpers. Check before work and between agents/roots,
expanded roots, entries, recursively walked directories, files and chunks;
check around parsing/building phases without changing the parser API.

Forward the same predicate throughout both discovery passes and byte capture.
Keep CaptureCancelled distinct from OSError so permission guards and binary
fallbacks never swallow it. An OS read already blocked cannot be forcibly
interrupted; checks are cooperative. Default CLI calls/hash results and guarded
permission behavior remain unchanged.

### 2. Capture complete inputs

Implement the exact capture_session and SnapshotChanged interfaces in §21.4.
SnapshotChanged's message is exactly:
“Files changed while scanning. Press r to retry.”

Verify effective home; load registry once and pass that same loaded dictionary
to first and validation live_discovery calls. Use normalized index home/cwd
throughout capture/report construction and the published snapshot.

One guarded chunked byte reader captures settings and lock with a CapturedInput
for each absolute path. FileNotFoundError means missing; other OSError means
unreadable; successful empty bytes are not missing. Preserve invalid UTF-8 bytes.
Catch OSError only for guarded I/O; never catch CaptureCancelled with a broad
Exception/BaseException handler or translate it into an unreadable result.
Derive a disabled frozenset for every agent through the existing decoder.

For every canonical_key, publish a files entry. No-hash copies get (). Otherwise
classify the canonical root with its actual is_dir result, like diff._copy_files,
not entry.is_file (a suffixless symlink can point at a standalone file while that
flag is False). Use iter_files for directories or the canonical standalone
filename; collect all
non-excluded files in sorted relative POSIX order, including complete binary
bytes and files beyond 1 MiB. Read chunks with cancellation checks. Calculate
file hashes using hash_bytes and aggregate directories using
hash_captured_directory. Aggregate/single hash must equal discovery's hash;
read failure after a hash was available raises SnapshotChanged.

If entry.parse is None, retain its captured files and skip source reparse;
the second discovery catches any None/present transition. Otherwise, where
readable source bytes exist, reparse with parse_skill_bytes and original source_path;
compare to_dict AND body, including undeclared nested frontmatter and stable
undecodable parses. Reuse existing document selection; do not reimplement YAML,
identity, newline or ignore rules. Never parse canonical bytes under a canonical
name that changes alias identity.

### 3. Reports, paths and full validation

Build scan with build_scan_report(Path(index.home), Path(index.cwd), index,
registry), and run_doctor with that live index and loaded registry.
Check cancellation between these phases. Collect display keys for home/cwd,
canonical/entrypoint paths, all entrypoint_paths and hit paths, unreadable roots,
shared library, lock and every settings path. Store paths.display results now.
Capture both ordered forms of every true entrypoint/canonical pair used by Why,
including agent-specific hit entrypoints; equal strings need no later probe.

Run the second live_discovery with the same registry/predicate. Compare ordered
entries and every field (canonical metadata, flags, names, source paths, hits,
entrypoint_paths, hashes, variant fields), parse dictionaries AND bodies, and
ordered unreadable roots, plus index home/cwd. Dataclass equality alone is
insufficient. Compare parse presence first: both None agrees, exactly one None
is a difference, and only two present parses invoke to_dict/body comparisons.
Also compare present frontmatter dictionaries directly, alongside the mandated
dictionary/body comparison, so JSON coercion cannot hide metadata type changes.
Rebuild scan/Doctor and display/link decisions from the validation
index and compare whole reports/maps/sets. Finally reread configuration bytes
and status, comparing complete CapturedInputs (not decoded JSON only).

Any observed difference raises SnapshotChanged and returns no candidate.
Check cancellation and effective-home agreement immediately before publication.
Copy entry parses/nested frontmatter and stored report containers; convert index
lists to tuples, keep registry order and copy/wrap the declared SessionSnapshot
Mapping fields with MappingProxyType. Deep-copy ScanReport.unreadable dictionaries
but leave their public dict type intact so existing JSON serialization works.
Do not deepcopy an already wrapped proxy; copy before wrapping.
Return one complete SessionSnapshot with caller generation, normalized home/cwd,
registry, frozen index, captured files/configs/overrides/paths/link decisions and
finished scan/Doctor. No global current state, UI publication or report cache.

### 4. Captured browsing services

Implement every §21.4 service, preserving exact signatures:

- entry_for_path searches canonical_key in the frozen entries; unknown key raises
  KeyError without resolve/discovery.
- snapshot_why validates the captured agent id (KeyError for unknown), translates
  selected entry with lookup_name_for_entry and supplies frozen index, owned
  registry dictionary, home/cwd and captured overrides to resolve_skill.
- snapshot_diff groups by entry.name, not translated Why name, supplying captured
  files/index/registry and coherent snapshot home/cwd to build_diff_report.
- snapshot_compare validates both captured ids (KeyError for unknown) and rejects
  equal ids with ValueError; call existing run_compare with frozen inputs.
- snapshot_path returns a stored display string or the literal input unchanged.
- snapshot_same_location returns string equality or membership in the captured
  ordered pair set. Neither helper probes paths or ambient home.
- Scan, Doctor and Agents are snapshot.scan, snapshot.doctor and
  snapshot.registry. JSON uses existing models.dumps(report.to_dict()) and CLI
  agent payload shape, not a new serialization API or a live command.

Reconstruct registry dictionaries from the captured tuple per engine call.
No first-visit service can reach registry loading, live discovery/settings/file
collection, home lookup, path display/resolve or link probes.

### 5. Acceptance proof and correction loop

Use the mandatory matrix below. Before running tests, inspect new fixture
signatures and fail-closed home/read isolation; even an empty registry can cause
Doctor to read a lock. Prepare genuinely independent live expected reports
before mutating fixtures or banning readers, using the normalized index home/cwd
as the contract requires. Tests bind supplied home to paths.home() after activating
their mock_home sandbox; the initial mismatch test bans registry/discovery reads
and asserts an anchored ValueError, not a loose message substring.
Assert complete dictionaries and
existing JSON, not headline-only equality or nonempty strings.

Use capture-local imported/helper seams for deterministic hooks (snapshot.iter_files,
hash_bytes, guarded byte reader and report/path collection helpers), wrapping
real behavior rather than replacing capture/discovery with fake success.
Avoid global hasher hooks that also mutate discovery's earlier hashing phase
unless that earlier phase is exactly the target under test.

Mutation-test C3 guards in a disposable scratch copy or scoped in-memory
mutation, never by altering active product files. Name the exact function,
mutation and protecting selector; execute actual branches, not stubbed services.
Break identity translation, capture hash/parse/double-pass validation, config
revalidation, ownership copying, no-live-read boundaries and cancellation
forwarding/checkpoints one at a time. Each relevant mutation must fail its
protecting test and pass restored. Record any equivalent/unreachable mutation
with evidence; a surviving relevant mutation blocks acceptance. Existing C2
mutations and the full cross-assignment audit are C5, not new C3 scope.

After coordinator verification, obtain fresh-context implementation reports from
both selected critics against the actual files/diff and frozen plan. Reproduce
findings and route confirmed corrections to Agy. After each correction rerun
focused proof and all gates. Two rounds without convergence requires Hazem's
decision, not a third broad correction. Commit only accepted allowed files.
Settle/release or explicitly retain each worker according to Orca ownership.

## Acceptance

| Test / area | Required observable proof |
| --- | --- |
| test_snapshot_reports_match_live_reports | Isolated mixed user/project fixtures, distinct home/cwd, variants, assets/binary, valid/invalid/undecodable/lowercase/standalone/aliased skills, differing folder/frontmatter name, disabled settings and lock. Compare scan, stored Doctor, every selected-entry/agent Why, each entry-name Diff and all valid ordered compare pairs against independent existing live builders; complete to_dict and existing JSON match. Agent JSON follows cli.py. Independently assert the exact captured file-key inventory, full raw bytes and hash_bytes fingerprint for EVERY copy, including a single-copy asset-bearing skill and files beyond 1 MiB; compare against fixture bytes before banning reads. Include differing copies with binary/nested/large assets so diff's collector is actually exercised, but do not rely on diff alone to prove byte retention. |
| test_first_visits_do_not_read_files | Prepare expectations, capture, then edit/delete/add skills, change settings/lock, retarget shortcut. FIRST visits (no prewarmed report cache) to Why/Diff/Compare/Doctor/Agents/JSON and displayed paths/link equality retain original results. |
| test_navigation_has_no_filesystem_fallback | Scoped post-capture sentinels ban discovery/registry/settings/diff collection and paths.home/display/same_location; ban file read/open, walk/list/stat/lstat/resolve/readlink/link probes. Exercise all C3 services and stored-report/agent serialization, including missing keys/unknown display keys/unknown and identical agent errors. Keep patch context narrow so pytest can read its own files. Presentation helpers do not exist until C4 and are not required here. |
| test_refresh_sees_changed_inputs | After mutation, successful second capture sees inventory/settings/diff/Doctor changes together with requested new generation; original snapshot/JSON/maps remain unchanged. |
| test_change_during_capture_is_rejected | Deterministic phase hooks separately change bytes near end of a large file, nested metadata with unchanged name/description, parse body, config bytes (including decoder-equivalent whitespace), file membership and symlink target. Test initial hash/byte mismatch and second-pass entry/parse/hit/unreadable/report/display/link/config differences, including both directions of None/present parse transition and stable None. Assert exact SnapshotChanged message. No sleep races or returned partial candidate. |
| test_cancelled_capture_does_not_publish | Controlled predicate cancels before work, during text hashing, binary fallback chunks, file walking, roots/entries/recursive directories, guarded byte reads and second-pass/report/config validation phases. CaptureCancelled propagates, not SnapshotChanged or unreadable; no returned candidate. Dedicated helper and forwarding tests cover every public cancellation API. |
| test_snapshot_owns_its_containers | Retain original first index, registry dictionary and builder reports via wrappers that invoke real code. Mutate original lists and nested frontmatter/list/dict values and unreadable report dictionaries AFTER return; snapshot stays unchanged. All mapping tables reject assignment; all_agents returns an independent set. Prove ownership without changing public nested field types. |
| test_capture_never_writes_target | Before/after capture AND navigation, compare complete fake-home file bytes, modes and symlink targets; no writes/extra files, including settings/lock/binaries. Keep permission fixture cleanup separate. |
| boundary/error fixtures | Empty inventory, missing/unreadable/empty/invalid-UTF8 configs, stable unreadable copy/no hash, undecodable document with hash, initial-home mismatch before reads, effective-home drift before return, normalized relative cwd, standalone symlink canonical filename vs original source identity, suffixless symlink to a standalone file (parse=None, is_file=False, nonempty captured canonical file), lower-case and dual-case document preference, symlinked parent aliases. |
| existing compatibility | All old tests and pinned render/JSON fixtures unchanged, no regeneration. Defaults with cancellation omitted and false predicates match original discovery/streaming hashes. Existing OSError guards preserved. |
| scratch mutations | Each relevant new guard fails when broken and passes restored; record selectors and real outputs. |

Run through the existing .venv (no install/update):

```bash
.venv/bin/pytest tests/test_session_snapshot.py tests/test_discovery.py tests/test_hasher.py tests/test_doctor.py
.venv/bin/pytest --cov=skill_lens
.venv/bin/mypy
.venv/bin/ruff check .
.venv/bin/ruff format --check .
git diff --check
```

Full suite passes; coverage meets configured 90% floor; strict typing/lint/format
clean. Read actual tracked and untracked changes; account for every path. Record
observed totals, review identities, mutations and any unresolved limitation here.

## Review decisions

MCode's initial review returned changes_required; its Task `task_09b40ccd8d6b`
and Dispatch `ctx_ecaf933fbdc6` completed with a full report in the external
scratch directory (`mcode-c3-plan-review.md`). OpenCode's initial review also
completed; both initial reviews and targeted rechecks are recorded below.
The draft was amended for reproduced seams before the final freeze decision.

### MCode initial decisions

| Finding | Disposition and evidence |
| --- | --- |
| B-1: lowercase document lookup | Accept. Independent scratch baseline probe reproduced source SKILL.md versus captured skill.md on this Mac. Exact-key-only lookup fails on stable inputs; add capture-time selected-file identity fallback, preserving original parse source and actual captured filename. |
| B-1: aliased standalone lookup | Reject the claim that the draft required alias-filename byte keys: its original text explicitly said canonical filename for standalone documents. Both critics' and coordinator's probes confirm the valid distinction. Retain and emphasize that rule and its acceptance fixture. |
| B-1: case-fold before samefile | Reject prescribing generic case-fold lookup. It must preserve filesystem/document selection, including distinct cases on Linux. Exact key followed by capture-time samefile against collected files handles the reproduced Mac spelling without a guessed identity rule. |
| B-2: sandbox safety | Accept explicit mock_home/sandbox requirement; reject the reading that “requests it” authorized bare_home (it referred to mock_home). A separate scratch probe confirms bare_home permits expansion of /etc/codex/skills while mock_home does not, without probing that external directory. Existing bare_home tests are a separate audit concern, not authorization to edit them in C3. |
| S-1: proxy scope and report JSON | Accept. Wrap only SessionSnapshot Mapping fields; deep-copy nested existing report dictionaries without changing their serialized types. Source shows ScanReport.to_dict returns these dictionaries directly. |
| S-2: registry order | Accept current id/filename-order parity assertion; reject adding a future sorting rule. The specification explicitly preserves load_registry order. Any future divergence is reviewed then, not silently changed here. |
| S-3: initial-home precision | Accept anchored negative guard and exact effective-home fixture setup. live_discovery ignores an independent home argument; pre-check binds the caller's home before reads. |
| S-4: broad catches | Accept explicit cancellation separation in byte reader as well as existing hashing guards. No broad catch may turn cancellation into unreadable status. |
| S-5: config/Doctor order | Accept confirmation. Preserve the prescribed order: configs before Doctor, then second discovery/report comparison, finally raw config reread. These independent comparisons detect observable changes, not changes completely undone between checks. |
| S-6: normalized cwd expectations | Accept clarification. Capture/report parity uses normalized index paths, not a conflicting raw CLI argument; CLI code is unchanged. |
| S-7: scanner scope | Accept confirmation. Scan is built and validated using live indices, stored for navigation; scanner remains excluded from edits. |
| CONCEDED | Record accurately: reviewer did not run gates, did not edit repository and could not attest coordinator identity internally. Coordinator's real gate output remains evidence; MCode's own model picker and running banner identify minimax/MiniMax-M3.1-Flash-Preview / xhigh, a different family from Hermes. |

### Planning probes and process seam

External `planning_seam_probe.py` exercises the existing baseline only. After
fixing its exact-key-only assumption, captured hash/byte-parse parity holds for
aliased standalone/directory, lowercase, dual-spelling and undecodable cases.
It separately proves dataclass equality misses frontmatter, to_dict misses body,
and decoded config equality misses raw-byte differences. The dual-case fixture
on this volume is one physical file; do not claim it proves two-file preference.
`planning_home_probe.py` proves sandbox root expansion policy without touching
the actual system root. These are planning evidence, not C3 implementation tests.

Current Orca 1.4.221 rejects worker-start on MCode's terminal as
agent_unconfigured. The documented low-level route works: task-create, dispatch
without injection with return-preamble, then terminal-send the exact returned
preamble to the verified idle MCode terminal. The Task/Dispatch and worker_done
are authoritative, but Orca calls its process lane unsupervised and owns no
terminal resource. Never claim supervised cleanup for that lane. Release of the
completed attempt returned retained/no_owned_resource/processAction none; this
coordinator-created terminal is reused for its immediate targeted review.

All blocking findings need final disposition before agreement/commit. Record
the freeze hash in a following plan-only provenance commit; implementation
baseline explicitly accounts for that metadata-only move.

### OpenCode initial decisions

OpenCode Task `task_c9eefeb58073`, Dispatch `ctx_22ce6857503f` completed with
changes_required against the original draft. Its own session metadata and banner
identify opencode/space-bunny-free, variant max. The initial final report did not
incorporate the coordinator's amended draft; require a targeted second review,
not a claim that the original blockers remain in the amended text. The full
terminal report was inspected through overlapping screen pages (external
`opencode-plan-report-screen-pages.txt`); its export/transcript route was clipped
and is not complete evidence.

| Finding | Disposition and evidence |
| --- | --- |
| B1: lowercase lookup | Accept, already amended for the independently reproduced Mac source-spelling defect. Preserve original parser identity and actual captured filename; samefile fallback occurs only during capture. |
| B2: standard mock_home always mismatches on Mac | Reject blanket claim: coordinator's scratch effective home is equal and MCode actually tested pytest tmp_path as resolved. A raw unresolved tempfile path can differ, as the reviewer's probe demonstrates. Accept explicit paths.home() fixture setup, already added; keep the fail-closed direct-equality API rather than weakening it. |
| B3: absent parse | Accept explicit presence comparison and tests as a real reachable implementation seam, not an existing product crash (C3 is unbuilt and the draft did not mandate an unguarded dereference). Scratch baseline reproduces suffixless standalone link with parse=None, is_file=False and a valid hash. Both-None agrees; one-None is SnapshotChanged. |
| B4: byte-retention proof | Accept. Coordinator reproduces zero _copy_files calls and identical one-copy diff reports for full/empty maps. Add direct exact file inventory/bytes/fingerprint assertions for every published copy and genuinely differing asset-bearing copies. Do not rely on a shortcut report to prove stored bytes. |
| S1: capture-exclusive hooks | Accept narrow local helper/import seams, wrapping real functions. Avoid accidental mutations of the earlier discovery hash phase. |
| S2: scan arguments | Accept explicit builder call with normalized index home/cwd. Scanner stays live and unchanged. |
| S3: fixed changed-message assertion | Accept. Assert exact exception text, not merely exception type or loose substring. |
| S4: numbered mutations | Accept grouped proof obligations below. Each field/check requires a protecting test; group labels do not excuse an unchecked field. |
| S5: classify canonical type | Accept. Scratch suffixless-link probe proves entry.is_file=False even with a canonical standalone file. Match existing diff's canonical is_dir dispatch, and test it. |
| S6: directly compare frontmatter | Accept as corroborating metadata comparison, alongside mandatory to_dict AND body; preserve existing parsing/JSON coercion rules. It must not replace either mandatory check. |
| S7: normalized cwd | Accept clarification, already added for MCode S6. Raw CLI arguments do not override snapshot index paths. |
| S8: differing asset copies | Accept alongside B4; single-copy raw-byte assertions remain independently required. |
| S9: registry order | Accept parity assertion for the current registry; reject a new future sorting rule as already adjudicated for MCode S2. |
| S10: Doctor reverse navigation | Defer to U7 concrete planning. A UI finding-to-row jump is not a new C3 core lookup API; Doctor's stored displayed/raw path conventions stay unchanged. |
| S11: coverage | Accept confirmation: measure the final gate, never predict its coverage. |
| S12: Doctor citations / formatter count | Accept narrower read citations as evidence; original builder lines also show which checks it invokes. Reject treating the before-draft formatted-file count as a future total. The initial real terminal gate remains the baseline record. |
| CONCEDED | Record withdrawn concerns (broad cancellation catches, canonical-key merge collision, differing source after merge, shared-hook blocker, JSON coercion blocker, agent-order blocker, prepublication scan/Doctor reads and scope creep) as withdrawn, not open defects. Relevant narrowed suggestions were adjudicated above. |

The coordinator's `planning_review_probe.py` and `planning-review-proof.json`
reproduce the absent-parse/canonical-file and dead single-copy diff seams using
existing code in a sandbox. These discriminate prospective implementations;
they are not claims that C3 has shipped or its tests passed.

### MCode targeted recheck

Task `task_246f3433ae9a`, Dispatch `ctx_78cb767de88f` returned pass, no blockers,
and withdrew the standalone claim explicitly. Full report:
`mcode-c3-plan-recheck.md` in external scratch. It independently verified samefile,
filesystem-conditioned dual-case fixtures and sandbox policy. R1 (case-fold weaker
than file identity) is recorded as confirmation without adopting new Unicode
rules. R2 (sorted first samefile match) and R3 (per-file cancellation in fallback)
are accepted technical clarifications in the amended mapping decision.
Pre-existing Phase 4 bare_home/system-root exposure is recorded for a separate
C5 safety audit, not a new C3 edit or blanket claim that old tests cannot probe it.

### Named mutation proof obligations

Execute separate mutations within these groups and record the precise target,
selector, failure and restored pass; no synthetic success output:

1. M01: remove initial-home guard/order and final effective-home validation.
2. M02: bypass captured-byte versus initial discovery hash verification.
3. M03: omit captured source to_dict, body, or metadata comparisons separately.
4. M04: skip second discovery/index structural validation; omit entry order,
   index home/cwd, individual canonical/name/flags/hit/entrypoint/hash/variant
   fields, parse presence/dictionary/body and unreadable roots independently.
5. M05: omit rebuilt scan and Doctor report comparisons separately.
6. M06: omit display-path and ordered same-location validation separately.
7. M07: omit raw config/status revalidation, including decoder-equivalent bytes.
8. M08: drop/truncate/zero captured asset bytes or omit a captured filename after
   hashing; direct publication assertions must detect it, including one-copy data.
9. M09: remove deep-copy ownership for original lists, nested parse metadata and
   report dictionaries; remove top-level read-only wrappers separately.
10. M10: remove Why identity translation, use translated rather than directory
    name for Diff, or omit captured engine arguments/navigation map boundaries.
11. M11: route a browsing service through a live reader/path/home probe. Its
    raising sentinels must detect the forbidden call even if output would match.
12. M12: remove each cancellation public/private forwarding edge or checkpoint
    class (roots, entries, recursive dirs, files, text/binary chunks, byte reads,
    phase transitions, validation, samefile fallback, final publication).

This list describes proof obligations, not a promised mutation count. The
implementation record enumerates the actual independent mutations and survives
only with zero unadjudicated relevant survivors. Broader C1–C5 audit stays C5.

### OpenCode amended-plan recheck decisions

Task `task_80ae3ce929c5`, Dispatch `ctx_9d1e09daa74e` closed all original
findings in durable message `msg_31842710b7e2`, but requested one additional
capture-phase clarification. Its actual report, not merely its summary, is the
review evidence. The coordinator adjudicates as follows before freeze:

| Finding | Decision |
| --- | --- |
| R1: absent parse during initial capture | Accept explicit skip before dereferencing parse.source_path. It is the same reproduced suffixless-link seam; keep captured bytes and let second-pass validation compare parse presence. Strengthen M03 and boundary tests to cover initial stable None as well as transitions, without claiming an existing unbuilt crash. |
| R2: relative_to ValueError | Accept no-exact-key fallback to capture-time samefile; preserve original source and cancellation/error guards. Source currently keeps source under its entrypoint, so this is defensive plumbing, not a new path-resolution rule. |
| R3: stale review status paragraph | Accept and update historical/current review accounting above. |
| R4: durable report messages | Accept evidence preservation; record actual message IDs and save report bodies externally. Clipped exports are not a substitute for full report evidence. |
| R5: hash/canonical invariant | Accept confirmation. Existing _build_entry computes a hash only for CanonicalStatus.OK, whose canonical path is populated. Capture uses the canonical_key/root, including suffixless file targets, and never reclassifies by entry.is_file. |

Stable parse=None capture is part of M03's source-presence guard and the
boundary/error fixture. Do not replace it with an artificial post-capture model
that never executes the real initial byte-capture branch.

## Planning acceptance and implementation baseline

OpenCode's final narrow closure Task `task_70f4a8e7d3a8`, Dispatch
`ctx_170a2c98bb1d` returned pass with no blockers/suggestions. Complete durable
report: `msg_d697a8ee1996`; exact completion: `msg_478caf10a8ad`. It verified
the actual amended step-2 skip, acceptance fixture/mutation obligations,
relative-path fallback and corrected review accounting. MCode's targeted pass
remains applicable; final amendments only make the already-reviewed parse-None
and evidence-accounting rules explicit. No product behavior or scope was added.

The coordinator accepts this plan. Every finding is adjudicated, both selected
critics have closed their blockers, and the user already authorized C3
implementation. Final planning gates on unchanged product code: 515 tests pass,
93.61% coverage; strict mypy clean over 26 files; Ruff lint/format clean
(75 files now counted after adding this document); git diff --check clean.
Independent byte fingerprints differ from the pre-review tree only in this
coordinator-authored plan. Product/test/registry/pinned fixture files are unchanged.

Raw proof and launch/readback receipts live outside the checkout under the named
scratch directory, including planning-final-gates.json and the three planning
seam probes. These are baseline/design checks, not proof of C3 code. Reviewer
release retains attached OpenCode terminals as external_terminal; MCode's low-level
Dispatches have no owned resource and its coordinator-created idle terminal is
closed separately after settlement. No active planning reviewer or reclaimable
coordinator-owned worker may remain at the implementation boundary.

Freeze only this agreed plan, then record its literal hash in a separate
plan-only provenance commit. Agy builds that frozen contract; the next HEAD
deliberately differs solely by the provenance line. All C3 product/test edits,
actual acceptance gates, fresh independent implementation reviews and final
commit are still required. Nothing is pushed or published.

## C3 implementation acceptance record

The coordinator accepts C3 after the initial implementation, two consolidated
correction rounds, independent verification and the selected critics' final
passes. This record is appended under the documentation permission at :128;
the agreed implementation contract and original freeze reference above are
unchanged. Implementation checkout baseline was
`cc48438c7110431a8b0774c8937d07a3d68db2a4`, the authorized provenance-only
successor to the frozen plan. No push, release or publication is authorized.

### What shipped and what did not

Agy wrote the nine permitted product/test files. `core/cancellation.py` supplies
the shared cancellation exception/check; discovery, its private listing/building
helpers, the live adapter and streaming hasher forward the optional predicate.
Default CLI calls keep their existing behavior. `core/snapshot.py` captures
complete canonical file bytes, original parsing identity, settings/lock read
outcomes, per-agent overrides, finished Scan/Doctor reports and path/link
decisions. It checks them against a second discovery/report/input pass before
constructing an owned session snapshot. A cancelled or inconsistent capture
returns no snapshot. Why, Diff, Compare and path/location helpers use captured
inputs only, including their error paths.

No UI, controller, presentation, C4/C5, packaging, registry or other engine work
was added. Public JSON, existing CLI output and all pinned fixtures remain
unchanged. The only coordinator checkout edit is this appended evidence record;
other documentation remains outside this assignment's scope.

### Actual verification, not the implementer's self-report

The coordinator read the complete new code and all changed tests, checked live
test fixture signatures for `mock_home`/sandbox isolation, and independently ran
the final checkout gates:

| Gate | Actual result |
| --- | --- |
| `.venv/bin/pytest --cov=skill_lens` | 542 passed, 1 conditional filesystem skip; 543 collected; 94.19% coverage against the 90% gate |
| `.venv/bin/mypy` | No issues in 28 source files |
| `.venv/bin/ruff check .` | All checks passed |
| `.venv/bin/ruff format --check .` | 78 files already formatted |
| `git diff --check` | Clean |

The skipped test is `test_case_sensitive_dual_case_preference`: this macOS
volume cannot hold two distinct `SKILL.md`/`skill.md` files in the same directory.
Its corrected branch selects the actual directory identity `dual_case_skill`,
asserts frontmatter name `dual` separately and verifies distinct document
contents before uppercase preference. The physical two-file branch was not
exercised here; Linux execution is not claimed. Lowercase-only selection and
the actual suffixless standalone `parse=None` boundary did run.

A separate coordinator-written, actually executed scratch-only exercise used
the existing live builders for independent expected outputs before capture.
It verified 7 canonical copies, 14 complete files and 1,345,238 retained raw
bytes; all 10 registry agents, 70 complete Why reports, 7 Diff reports and 90
ordered Compare reports; exactly 15 displayed paths and 11 ordered true
location pairs. It then changed/deleted skills, settings, lock bytes and a link
target before first report-service calls. All original full JSON remained equal
under bans on discovery, configuration, registry, path, file-open and OS
readers. It mutated retained original index/registry/nested metadata and proved
owned snapshot insulation. A new generation changed inventory, disabled
resolution, Diff and Doctor while the old snapshot stayed unchanged. Cancelled
and deliberately inconsistent replacements never invoked publication. Whole
synthetic-home bytes, modes, sizes and link targets were unchanged by capture
and navigation. All probes used explicit scratch homes, not installed skills.

Repository Compare parity selects each `i+1` agent combination; the independent
exercise additionally checks both orders. Do not call the repository loop 90
ordered tests. Location tables separately assert both true link/target orders.

### Review provenance and decisions

Orca Run: `run_7ff09c704694`. Agy's effective model was independently observed
as `gemini-3.8-flash-high` in launch receipts and its own high-effort banner.
Permissions were preserved; no model substitution or global settings edits.
Initial implementer Task/Dispatch: `task_3f0ed4e831a7` / `ctx_ff8dc32935a5`.
Correction round 1: `task_a781c812f431` / `ctx_43cc40fb4ac9`.
Correction round 2: `task_0fc79bea4577` / `ctx_02ce66a70a60`.

Initial fresh-context implementation reviews returned changes_required on both
axes. OpenCode: `task_c57f865f0e6c` / `ctx_1d51d5aac424`, full report
`msg_4f59b103ad7e`. MCode: `task_bdcf96c935e6` / `ctx_81dd6be82fa9`, full
report `msg_6d08481821b5`. Round-1 targeted rechecks still found narrow proof
gaps: OpenCode `ctx_fe4dd16ef3f7`, report `msg_0a675af0a763`; MCode
`ctx_ff9f57c5835d`, report `msg_6b4421563119`. Their broad closure claims
were qualified by the coordinator's actual phase counters, malformed hits
payload and benign-open experiment rather than accepted blindly.

Final closure used fresh contexts after the prior custom terminals were
positively observed exited:

- OpenCode `opencode/space-bunny-free`, variant `max`, Plan mode:
  `task_2061ad9b58b8` / `ctx_39e86adb4dce`; final pass and completion
  `msg_24857ea59e31`. It reproduced all four gates and 14 targeted mutations;
  an early run using an interpreter without pytest was discarded, not counted.
- MCode `minimax/MiniMax-M3.1-Flash-Preview`, effort `xhigh`:
  `task_e53f332fd2f7` / `ctx_6fca771b3cce`; full pass report
  `msg_2491d4ff1b53`, completion `msg_2d5b66a4db5c`. It inspected all 114
  final mutated/restored logs and independently reproduced six targeted kills.

The coordinator reproduced confirmed findings before dispatching corrections.
All accepted behavior/proof rows are closed. Style-only duplicate literals,
singleton canonical-set cleanup and unrelated discovery/Phase4 changes were
deferred as unneeded scope, not hidden remaining behavior defects.

One original MCode claim was rejected: the recorded M03a mutation removed the
whole source `to_dict`/body/frontmatter block, not frontmatter alone. That whole
removal genuinely failed. Separate raw metadata clauses still needed tests:
YAML dates normalize to strings in JSON, so equal `to_dict()` can conceal
unequal raw metadata. Both source and validation clauses now have independently
killed date-coercion cases. Existing-tuple-to-tuple conversion alone is narrowly
equivalent; removing `MappingProxyType` is NOT equivalent and read-only tests
protect it. These qualifications replace the worker report's ambiguous wording.

### Mistakes reproduced and corrected

- The initial settings fixture wrote ignored `disabled_skills`; it now uses
  real `skillOverrides` values that are `False`, and asserts actual DISABLED
  state, complete captured inputs and every registry agent's overrides entry.
- The initial ownership assertion mutated the published object itself. Tests
  now mutate retained original index lists, registry dictionaries, nested
  parsed metadata and report dictionaries and assert snapshot insulation.
- Iterating only returned files could miss an omitted asset. Direct assertions
  now compare exact independently collected keys, sorted filenames, complete
  raw bytes and hashes BEFORE report parity can abort. Differing copies carry
  different nested/binary assets; single-copy large data is asserted directly.
- A separately discovered canonical document hid the initial suffixless
  `parse=None` seam through merging. Its target is now outside scanned roots
  but inside `mock_home`; absence, file flag, hash and bytes are explicit.
- Cancellation invocation counts were mistaken for reached file chunks.
  Actual read wrappers now flip after the first chunk and prevent the second.
  Final cancellation flips AFTER the last real config reread, with input count
  derived from the registry instead of magic `4`.
- A missing tuple comma made a hits mutation fail through an unrelated scanner
  TypeError. The payload now preserves a valid tuple of real hits; the omitted
  guard fails through the intended missing SnapshotChanged assertion.
- Corrupting a published standalone fingerprint did not test the earlier
  discovery/capture hash guard. A real parse-absent standalone temporarily
  changes bytes and restores them before validation; omitting that first hash
  check now independently permits the forbidden publication and fails the test.
- Path-method sentinels missed a benign built-in open returning identical
  output. Narrow navigation bans now include builtins/io/raw OS opens and
  readers; the matching-output read is caught by the sentinel itself.
- Missing/unreadable/empty input outcomes and empty inventory are now exact,
  unconditional assertions. Targeted permission faults remain portable even
  under elevated test users; no real-home execution or silent passing branch.
- The skipped dual-case branch selected a frontmatter name rather than its
  directory identity. The selector and separate identity assertions are fixed;
  the unexercised physical-filesystem limitation is conceded above.

### Mutation accounting verified by the coordinator

The coordinator actually replayed all 57 final substitutions in a DIFFERENT
scratch checkout, then read every failure reason and restored result. All 57
mutated runs failed and all 57 restored runs passed, with zero payload-TypeError,
setup, syntax or collection failures counted. Most fail through an intended
assertion or missing expected exception. M04 entry-count and unreadable-count
guard omissions instead expose `zip(strict=True)` ValueError: these are
retry-exception-contract failures on legal changing inputs, not fabricated
payload crashes or proof of a successful partial snapshot.

| Frozen group | Replayed substitutions | Protecting selectors / real outcome |
| --- | --- | --- |
| M01 | 3 | Initial supplied-home/order and late effective-home guards; forbidden-reader sentinel or missing SnapshotChanged |
| M02 | 2 | Directory aggregate and actual standalone capture/discovery hash; missing SnapshotChanged |
| M03 | 8 | Source and validation dictionaries/body/raw date metadata, parse presence and source identity; missing SnapshotChanged |
| M04 | 12 | Entry count, paths/names/file/link flags/canonical/hash/hits/variants, unreadable count and index home/cwd; intended rejection contract |
| M05 | 2 | Rebuilt Scan and Doctor comparisons; missing SnapshotChanged |
| M06 | 3 | Display/location revalidation and reverse-pair retention; missing rejection or direct true-pair assertion |
| M07 | 3 | Raw input revalidation, exact missing/unreadable and readable empty; direct outcome/retry assertion |
| M08 | 2 | Valid-shape zero binary bytes and omitted nested filename; DIRECT retained-file assertion before Diff |
| M09 | 4 | Original nested frontmatter/report ownership and file/input read-only maps; direct isolation/TypeError assertion |
| M10 | 4 | Agent-specific Why identity, unchanged Diff grouping, overrides and same-agent error; full report/error assertions |
| M11 | 5 | Home/registry/display/location fallbacks and matching-output real built-in open; forbidden-reader sentinel |
| M12 | 9 | Real text/binary/config/asset chunks, recursive walk, discovery hash exception separation, samefile candidates, final publication and adapter forwarding; reached-phase/cancellation assertions |

Most table rows use `test_change_during_capture_is_rejected`; retained-data,
identity and pairing rows use `test_snapshot_reports_match_live_reports`;
ownership uses `test_snapshot_owns_its_containers`; navigation uses
`test_navigation_has_no_filesystem_fallback` and
`test_navigation_intercepts_benign_builtin_open`; exact input outcomes use
`test_config_inputs_exact_outcomes_and_empty_inventory`; cancellation uses
`test_cancelled_capture_does_not_publish`, the text/binary hasher tests,
`test_discover_cancelled_during_recursive_listing`,
`test_build_entry_cancellation_separation` and `test_live_discovery_cancelled`.
The three M01 selectors are `test_initial_home_mismatch_rejected` and
`test_effective_home_drift_rejected_before_publication`.

Round-1 forwarding/proxy targets also supplied real earlier proof; their
product paths did not change in round 2. No claim that 57 chosen substitutions
exhaust every imaginable defect is made. Required guards remain in the source;
the table counts actual applied mutations, not 57 named specification groups.

Worker snippets frequently quoted pytest source context rather than the actual
E-line, and one footer still said 44. The coordinator preserved those raw
reports and wrote corrected, exact-selector/full-failure receipts instead of
overwriting history. Approved evidence:
`coordinator-final-adjudicated-mutation-receipts.json`, the two
`coordinator-round2-semantic-batch*.json` files, complete logs under
`coordinator-round2-replay/receipts/`, and
`coordinator-round2-gates-and-full-probe.json`, all under the named scratch.
Those paths are supplementary local receipts, not a substitute for this
permanent acceptance record or the committed protecting tests.

### Accepted source identity and cleanup

SHA-256 of the accepted product/test files (before this documentation append):

| File | SHA-256 |
| --- | --- |
| `core/cancellation.py` | `a57076cdca9e5925c46c79c2a3d552ac375f75066265e346e7995d779890a0ca` |
| `core/snapshot.py` | `86d50b2b5e8b6dccc18c7e8920decd9aa6b789ba07906231858d92be181a3fe8` |
| `core/discovery.py` | `d50b4602dfa985526692be3de67d59dcd6e9070fa12f1cea60745d5761bb406d` |
| `core/hasher.py` | `677741ee6c7938e8923779e46a141590aa495733f8499b38828890e69d6e6f62` |
| `core/system.py` | `adafb6258f7e60df5cbf191bb03bb22a49dbb38374e48df06c45294b64bbec28` |
| `tests/test_session_snapshot.py` | `e15ad0c96eb3a4399fdf6b05086ef82dcbab409117fe5ac03ce05ae7127f4903` |
| `tests/test_discovery.py` | `a90edcca975fd7dc277eb2cfe930a89849e609ecc2339a880e5df59c3154fd7e` |
| `tests/test_hasher.py` | `e13165b29f0cd782c984695133e44866b98edad95bb848949c775922717a19dd` |
| `tests/test_doctor.py` | `c53ee08b36db9ade8c7e26b7ad586bc1335e616844627a68a3b7a1c78eb01262` |

All 128 pre-final-review checkout fingerprints matched after critic work and
coordinator mutation replay. All three Agy worker resources were released,
closing their owned terminals. Final custom critic Dispatches were settled and
released; their coordinator-created, proven-idle terminals were then closed
individually. Prior protected/user-owned surfaces were not force-closed.
The final Run query returned no reclaimable worker resources. No active
implementation/review work remains. Commit only these nine files and this
authorized appended record, after the final four-gate rerun; no push or publish.
