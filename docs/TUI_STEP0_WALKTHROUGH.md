# Skill Lens 0.2 — Step 0 Audit Walkthrough (C5)

> **Status:** Accepted by Sol after independent MiniMax review on 2026-10-11. Step 0 is complete.
> **Scope:** Verification of Step 0 prerequisites (C1–C5) against `FULL_SCREEN_TUI.md` §21.1–§21.6 and §22 row C5.
> **Implementer:** Antigravity Gemini 3.8 Flash High.
> **Independent Reviewer:** MiniMax Code (`mcode` / `MiniMax-M3.1-Flash-Preview`) High thinking.
> **Coordinator:** Sol.
> **Reference Plan:** `docs/plans/2026-10-11-tui-c5-step0-audit.md` @ commit `3665e7a38a9b7366c259da61c87f8b0cab656947`.
> **Root Checkout:** Commit `6030c3d` on `main`.

---

## 1. Executive Summary

This walkthrough audits the Step 0 implementation deliverables (Assignments C1 through C5) before optional TUI installation (U1) and interface screen construction (U2–U9) begin.

Step 0 establishes the architectural and behavioral foundation for the full-screen terminal UI:
- In-memory byte helpers, hashing, and parsing without live streaming compromises;
- Injected engine inputs and immutable captured data structures;
- A double-pass capture service (`capture_session`) with cooperative cancellation and change detection;
- In-memory browsing services that guarantee zero live filesystem reads during navigation;
- Shared Rich-free presentation helpers and display maps;
- Regression guards closing previously unexercised identity and configuration decoder paths;
- A reproducible, fail-closed mutation campaign demonstrating behavioral detection of regressions across all five required categories with verified in-process provenance.

All 17 existing render snapshots remain byte-identical against HEAD. All four repository quality gates pass cleanly on Python 3.11 with 94.58% test coverage (563 passed, 1 skipped due to macOS filesystem case-insensitivity).

---

## 2. Delivered Files & Responsibilities (§21.1)

The table below summarizes the delivered files and their architectural responsibilities under `FULL_SCREEN_TUI.md` §21.1:

| File | Delivered Responsibility |
| --- | --- |
| `skill_lens/core/snapshot_models.py` | Immutable data structures (`CapturedFile`, `CapturedInput`, `FrozenDiscoveryIndex`, `SessionSnapshot`). Dataclasses use `frozen=True, slots=True`. Imports `pathlib.Path`, discovery/registry models, and type-only `ScanReport` / `DoctorReport`; performs **zero filesystem operations**. |
| `skill_lens/core/snapshot.py` | Capture, validation, and in-memory browsing services (`capture_session`, `entry_for_path`, `snapshot_why`, `snapshot_diff`, `snapshot_compare`, `snapshot_path`, `snapshot_same_location`, `SnapshotChanged`). `capture_session` is the **sole session service permitted machine reads**; during capture it delegates reads to its discovery, system, hasher, and parser collaborators. |
| `skill_lens/core/cancellation.py` | Lightweight cooperative cancellation helper (`CaptureCancelled`, `check_cancelled`). Free of UI or engine dependencies. |
| `skill_lens/core/hasher.py` | Byte normalization (`normalized_text`), byte hashing (`hash_bytes`), and captured directory hashing (`hash_captured_directory`). Streaming CLI paths remain untouched and accept cooperative cancellation checkpoints. |
| `skill_lens/core/parser.py` | In-memory parsing (`parse_skill_bytes`) with universal newlines, UTF-8 BOM handling, YAML error handling, and shared text parsing extracted via `_parse_skill_text`. Live parsing retains existing `OSError` boundaries. |
| `skill_lens/core/resolver.py` | Pure configuration decoder (`disabled_overrides_from_bytes`), canonical lookup name selector (`lookup_name_for_entry`), identity matching (`_identity_names`), settings loader (`_load_disabled_overrides`), and explicit captured overrides in `resolve_skill`. |
| `skill_lens/core/diff.py` | Explicit `captured_files` injection in `build_diff_report` and `_copy_files`, budget truncation, and omission accounting without live disk fallbacks. |
| `skill_lens/core/discovery.py` & `system.py` | Cooperative cancellation checkpoints across recursive walks (`live_discovery`, `discover`, `iter_files`), and permission guards. |
| `skill_lens/core/compare.py` & `doctor.py` | Injected index and registry support in wrappers (`run_compare`, `run_doctor`), with Doctor report precomputed and frozen at capture time. |
| `skill_lens/core/scanner.py` | Inventory scanning operating over live or injected discovery index. |
| `skill_lens/presentation/state.py` & `text.py` | Shared presentation constants (`STATE_STYLE`, `STATE_MARK`, `SCOPE_LABEL`), plain text structures (`HeadingParts`, `NoticeParts`), and unified diff formatting functions without Rich or Textual imports. |
| `skill_lens/render.py` | Rich line-oriented CLI presentation delegating to shared `presentation/` helpers while preserving existing visual formatting. |
| `tests/test_snapshot_inputs.py` | Step 0 unit tests for pure byte helpers, parser parity, identity helper, settings decoder, model invariants, and configured-key overrides. |
| `tests/test_session_snapshot.py` | Step 0 integration tests for double-pass capture, change detection, cancellation, container ownership, first-visit freezes, and zero-filesystem-fallback navigation. |
| `tests/test_presentation.py` | Step 0 tests for shared presentation structures, literal text handling, and strict architectural dependency boundaries. |

---

## 3. Implemented API Signatures (§21.3–§21.5)

The following public and internal interfaces are implemented and verified in the codebase:

```python
# skill_lens/core/hasher.py
def normalized_text(data: bytes) -> str | None: ...
def hash_bytes(data: bytes) -> str: ...
def hash_captured_directory(files: Sequence[tuple[str, str]]) -> str: ...
def hash_file(path: Path, *, cancelled: Callable[[], bool] | None = None) -> str: ...
def hash_directory(root: Path, *, cancelled: Callable[[], bool] | None = None) -> str: ...
def hash_path(path: Path, *, cancelled: Callable[[], bool] | None = None) -> str: ...


# skill_lens/core/parser.py
def parse_skill_bytes(data: bytes, *, source_path: str) -> ParseResult: ...
def _parse_skill_text(raw: str, *, source_path: str) -> ParseResult: ...  # internal shared parser


# skill_lens/core/resolver.py
def lookup_name_for_entry(entry: DiscoveredEntry, agent: AgentDefinition) -> str: ...
def disabled_overrides_from_bytes(agent: AgentDefinition, data: bytes | None) -> frozenset[str]: ...
def resolve_skill(
    name: str,
    agent_id: str,
    cwd: Path,
    home: Path,
    index: DiscoveryIndex | FrozenDiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None,
    *,
    disabled_overrides: frozenset[str] | None = None,
) -> ResolutionReport: ...
def _identity_names(agent: AgentDefinition, entry: DiscoveredEntry) -> set[str]: ...  # internal
def _load_disabled_overrides(agent: AgentDefinition, home: Path) -> set[str]: ...  # internal


# skill_lens/core/diff.py
def build_diff_report(
    name: str,
    cwd: Path,
    home: Path,
    *,
    index: DiscoveryIndex | FrozenDiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None,
    captured_files: Mapping[str, tuple[CapturedFile, ...]] | None = None,
) -> DiffReport: ...
def _copy_files(
    entry: DiscoveredEntry,
    *,
    captured_files: Mapping[str, tuple[CapturedFile, ...]] | None = None,
) -> dict[str, _Collected]: ...  # internal


# skill_lens/core/compare.py
def build_compare_report(
    agent_a: str,
    agent_b: str,
    home: Path,
    cwd: Path,
    index: DiscoveryIndex | FrozenDiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None,
) -> CompareReport: ...
def run_compare(
    agent_a: str,
    agent_b: str,
    cwd: Path | None = None,
    *,
    index: DiscoveryIndex | FrozenDiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None,
) -> CompareReport: ...


# skill_lens/core/doctor.py
def run_doctor(
    cwd: Path | None = None,
    *,
    index: DiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None,
) -> DoctorReport: ...


# skill_lens/core/cancellation.py
class CaptureCancelled(Exception): ...


def check_cancelled(cancelled: Callable[[], bool] | None) -> None: ...


# skill_lens/core/snapshot_models.py
@dataclass(frozen=True, slots=True)
class CapturedFile:
    relative_path: str
    data: bytes
    fingerprint: str


@dataclass(frozen=True, slots=True)
class CapturedInput:
    path: str
    data: bytes | None
    error: Literal["missing", "unreadable"] | None


@dataclass(frozen=True, slots=True)
class FrozenDiscoveryIndex:
    home: str
    cwd: str
    entries: tuple[DiscoveredEntry, ...]
    unreadable_roots: tuple[UnreadableRoot, ...]

    def all_agents(self) -> set[str]: ...


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    generation: int
    home: Path
    cwd: Path
    registry: tuple[AgentDefinition, ...]
    index: FrozenDiscoveryIndex
    files: Mapping[str, tuple[CapturedFile, ...]]
    config_inputs: Mapping[str, CapturedInput]
    disabled_overrides: Mapping[str, frozenset[str]]
    display_paths: Mapping[str, str]
    same_locations: frozenset[tuple[str, str]]
    scan: ScanReport
    doctor: DoctorReport


# skill_lens/core/snapshot.py
class SnapshotChanged(Exception): ...


def capture_session(
    *,
    generation: int,
    home: Path,
    cwd: Path,
    cancelled: Callable[[], bool] | None = None,
) -> SessionSnapshot: ...
def entry_for_path(snapshot: SessionSnapshot, key: str) -> DiscoveredEntry: ...
def snapshot_why(snapshot: SessionSnapshot, key: str, agent_id: str) -> ResolutionReport: ...
def snapshot_diff(snapshot: SessionSnapshot, key: str) -> DiffReport: ...
def snapshot_compare(snapshot: SessionSnapshot, agent_a: str, agent_b: str) -> CompareReport: ...
def snapshot_path(snapshot: SessionSnapshot, path: str) -> str: ...
def snapshot_same_location(snapshot: SessionSnapshot, a: str, b: str) -> bool: ...


# skill_lens/presentation/text.py
@dataclass(frozen=True, slots=True)
class HeadingParts:
    mark: str
    style: str
    path: str
    variant: str
    scope: str
    parse_status: str
    status: str


@dataclass(frozen=True, slots=True)
class NoticeParts:
    label: str
    style: str
    body: str


def range_text(start: int, count: int) -> str: ...
def unified_text(file: DiffFile) -> str: ...
def unreadable_reason(copy: DiffCopy) -> str: ...
def copy_heading(copy: DiffCopy, *, baseline_exists: bool, display_path: str) -> HeadingParts: ...
def no_differences_message(report: DiffReport) -> NoticeParts: ...
def needs_listing(report: DiffReport) -> bool: ...
```

---

## 4. Architectural Boundaries: Capture vs. Navigation

### 4.1 Unidirectional Dependency Flow
The dependency hierarchy is strictly acyclic:
- `skill_lens/core/snapshot_models.py` imports `pathlib.Path`, discovery models (`DiscoveredEntry`, `UnreadableRoot`), registry models (`AgentDefinition`), and type-only `ScanReport` / `DoctorReport`. It does not import `snapshot.py` and performs no filesystem operations.
- `skill_lens/presentation/` imports data models only; it has zero imports of `render.py`, `rich`, or `textual`.
- `skill_lens/render.py` adapts presentation objects to Rich formatting for line-oriented CLI output.

### 4.2 Capture vs. Navigation Read Boundary
The runtime boundary between capturing session state and navigating that state is absolute:
1. **Capture Phase (`capture_session`):**
   - The only session service permitted machine reads.
   - Executes initial discovery via `live_discovery()`.
   - Reads complete file bytes and calculates content fingerprints (`hash_bytes`, `hash_captured_directory`).
   - Re-parses captured bytes against `entry.parse` to ensure AST, frontmatter, and body stability.
   - Captures installer locks and agent settings files through a guarded reader (`_read_input_guarded`).
   - Performs a full second pass (`live_discovery`, config reread, and report reconciliation).
   - Any difference between passes raises `SnapshotChanged("Files changed while scanning. Press r to retry.")`.
2. **Navigation Phase (`snapshot_why`, `snapshot_diff`, etc.):**
   - Runs **100% in memory** against the published `SessionSnapshot`.
   - Never falls back to disk reads, live discovery, settings loading, or filesystem probes.
   - Tested under `test_navigation_has_no_filesystem_fallback` where the following functions and OS readers are explicitly patched to raise `AssertionError`:
     - Live discovery & engine entrypoints: `skill_lens.core.system.live_discovery`, `skill_lens.core.discovery.discover`, `skill_lens.registry.loader.load_registry`, `skill_lens.registry.loader.list_agents`, `skill_lens.core.snapshot.load_registry`, `skill_lens.core.resolver.load_registry`, `skill_lens.core.compare.load_registry`, `skill_lens.core.resolver._load_disabled_overrides`, `skill_lens.core.hasher.iter_files`.
     - Path services: `skill_lens.core.paths.home`, `skill_lens.core.paths.display`, `skill_lens.core.paths.same_location`.
     - OS filesystem readers: `os.walk`, `os.listdir`, `os.stat`, `os.lstat`, `os.path.realpath`, `os.path.samefile`, `os.open`, `os.scandir`, `builtins.open`, `io.open`.
     - `Path` methods: `Path.open`, `Path.read_bytes`, `Path.read_text`, `Path.stat`, `Path.lstat`, `Path.resolve`, `Path.readlink`, `Path.iterdir`.
     *(Note: `Path.exists` delegates to `Path.stat` internally, so stat bans intercept it).*

### 4.3 Technical Guarantees & Non-Guarantees
- **Not a Filesystem Transaction:** Capture validation detects observable external modifications between the two discovery passes and file reads. It is an *observed consistency check*, not an OS-level atomic transaction. If an external process modifies a file and restores it to identical bytes before the second pass, the intermediate change cannot be detected.
- **Container Ownership vs. Deep Immutability:** `SessionSnapshot` enforces container immutability via `frozen=True, slots=True`, `MappingProxyType` dictionary wrappers, and tuple sequences. Nested reports (`ScanReport`, `DoctorReport`, `ParseResult.frontmatter`) are deep-copied on capture and owned by the snapshot. However, Python dataclasses are not recursively immutable by runtime enforcement; callers must treat snapshot reports as owned read-only data.

---

## 5. Acceptance Contract (§21.6 Matrix)

Every acceptance requirement from `FULL_SCREEN_TUI.md` §21.6 is satisfied by concrete, passing tests in the active test suite:

| §21.6 Acceptance Row | Realized Test Functions | Test Location | Status |
| --- | --- | --- | --- |
| Non-object settings are ignored | `test_non_object_settings_are_ignored` | `tests/test_phase2_gate.py` | PASSED |
| Non-UTF8 lock reports invalid JSON | `test_non_utf8_lock_reports_invalid_json` | `tests/test_doctor.py` | PASSED |
| `hash_bytes` matches streaming | `test_hash_bytes_matches_streaming` | `tests/test_snapshot_inputs.py` | PASSED |
| Captured directory matches live hash | `test_captured_directory_matches_live_hash` | `tests/test_snapshot_inputs.py` | PASSED |
| Byte parser matches live parser | `test_byte_parser_matches_live_parser` | `tests/test_snapshot_inputs.py` | PASSED |
| Selected entry uses agent identity | `test_selected_entry_uses_agent_identity`<br>`test_hybrid_and_either_resolver_identity` | `tests/test_snapshot_inputs.py`<br>`tests/test_phase2_gate.py` | PASSED |
| Explicit empty inputs never fall back | `test_resolver_explicit_empty_overrides_keeps_enabled_without_settings_read`<br>`test_disabled_overrides_respects_configured_key`<br>`test_diff_falsey_mapping_exercises_captured_branch_without_live_reads`<br>`test_diff_explicit_empty_tuple_remains_empty_under_patched_collector`<br>`test_diff_missing_selected_copy_key_raises_value_error`<br>`test_diff_empty_supplied_index_and_empty_files_returns_not_found`<br>`test_resolver_missing_companion_inputs_raise_value_error` | `tests/test_phase2_gate.py`<br>`tests/test_snapshot_inputs.py`<br>`tests/test_phase3_gate.py`<br>`tests/test_phase3_gate.py`<br>`tests/test_phase3_gate.py`<br>`tests/test_phase3_gate.py`<br>`tests/test_phase2_gate.py` | PASSED |
| Snapshot reports match live reports | `test_snapshot_reports_match_live_reports` | `tests/test_session_snapshot.py` | PASSED |
| First visits do not read files | `test_first_visits_do_not_read_files` | `tests/test_session_snapshot.py` | PASSED |
| Navigation has no filesystem fallback | `test_navigation_has_no_filesystem_fallback` | `tests/test_session_snapshot.py` | PASSED |
| Refresh sees changed inputs | `test_refresh_sees_changed_inputs` | `tests/test_session_snapshot.py` | PASSED |
| Change during capture is rejected | `test_change_during_capture_is_rejected` | `tests/test_session_snapshot.py` | PASSED |
| Cancelled capture does not publish | `test_cancelled_capture_does_not_publish` | `tests/test_session_snapshot.py` | PASSED |
| Snapshot owns its containers | `test_snapshot_owns_its_containers` | `tests/test_session_snapshot.py` | PASSED |
| Capture never writes target | `test_capture_never_writes_target` | `tests/test_session_snapshot.py` | PASSED |
| Plain parts preserve literal text | `test_plain_parts_preserve_literal_text` | `tests/test_presentation.py` | PASSED |

---

## 6. Mandatory Regression Guards Added in Step 2

Planning council reviews identified two subtle test gaps where mutations passed the existing test suite:
1. **Hybrid and Either Resolver Identity:**
   - *Regression:* Mutating `_identity_names` to return only `{directory_name}` for hybrid (`antigravity`) and supplied `either` agents passed because existing tests resolved by helper name only, never directly by declared frontmatter name.
   - *Guard:* Added `test_hybrid_and_either_resolver_identity` in `tests/test_phase2_gate.py`. Sets up differing folder and frontmatter names, exercises both helper-selected name and declared name into the real resolver, and asserts selected canonical installation and active state.
2. **Configured Settings Key Override:**
   - *Regression:* Mutating `disabled_overrides_from_bytes` to hard-code `parsed.get("skillOverrides")` passed because existing tests used Claude whose configured key is `skillOverrides`.
   - *Guard:* Added `test_disabled_overrides_respects_configured_key` in `tests/test_snapshot_inputs.py`. Replaces Claude's configured key with a distinct key (`customOverrides`), supplies conflicting data under `skillOverrides`, and asserts that only entries under the configured key are disabled.

Both guards pass on unmodified source and reliably catch the regressions.

---

## 7. Mutation Testing Campaign

A reproducible, fail-closed mutation testing campaign was implemented and executed using an automated harness at `docs/validation/c5/run_campaign.py`.

### 7.1 Rigorous In-Process Isolation & Provenance Rules
To prevent false kills and verify isolation:
- All mutations were performed one at a time on an owned disposable scratch directory (`/private/tmp/c5-mutations-...`) outside the repository.
- Each mutant run was executed inside a `try/finally` block verifying that original source bytes were restored before the next run.
- Each child test run executed with scratch as CWD, `PYTHONPATH` pointing strictly to scratch, and `PYTHONDONTWRITEBYTECODE="1"`.
- All `__pycache__` directories and `*.pyc` files were cleared before every run.
- Pytest hooks injected into `scratch/tests/conftest.py` asserted that `skill_lens.__file__` and the loaded test module (`item.module.__file__`) belonged to scratch, logging resolved paths and execution phases directly from the executing process.
- Complete test collection was verified to match the active tree (564 collected tests).
- Fail-closed evaluation classifies any syntax error, import error, internal error, missing provenance, provenance outside scratch, setup error, or non-assertion exception as **INVALID**, failing the entire campaign. Only a genuine named-test call-phase `AssertionError` or pytest `Failed` matching the expected behavior marker counts as a kill.

### 7.2 Reproducibility Command
The campaign can be reproduced with output directed outside the repository:
```bash
.venv/bin/python docs/validation/c5/run_campaign.py --output /tmp/c5-results.json
```

Or run the runner self-test demonstrating fail-closed defect rejection:
```bash
.venv/bin/python docs/validation/c5/run_campaign.py --validate-runner
```

### 7.3 Results Across Five Categories
All 12 mutations were caught with genuine behavioral/assertion failures (100% kill rate, 0 survivors, 0 invalids):

| ID | Category | Mutation Description | Protecting Test Selector | Control Exit | Mutant Exit | Restored Exit | Verdict |
| --- | --- | --- | --- | :---: | :---: | :---: | --- |
| **MUT-01** | Explicit-empty inputs | `resolve_skill` treats `disabled_overrides` empty set as falsy, calling live loader | `tests/test_phase2_gate.py::test_resolver_explicit_empty_overrides_keeps_enabled_without_settings_read` | 0 | 1 | 0 | **KILLED** (`Live settings loader must not be called`) |
| **MUT-02** | Explicit-empty inputs (settings key) | `disabled_overrides_from_bytes` hard-codes `"skillOverrides"` instead of `agent.disabled_key` | `tests/test_snapshot_inputs.py::test_disabled_overrides_respects_configured_key` | 0 | 1 | 0 | **KILLED** (`disabled-by-shipped` in set) |
| **MUT-03** | Captured diff branch (outer) | `build_diff_report` passes `captured_files=None` for baseline copy | `tests/test_phase3_gate.py::test_diff_falsey_mapping_exercises_captured_branch_without_live_reads` | 0 | 1 | 0 | **KILLED** (`Path.is_dir banned`) |
| **MUT-04** | Captured diff branch (inner) | `_copy_files` evaluates truthiness of `captured_files` instead of `is not None` | `tests/test_phase3_gate.py::test_diff_falsey_mapping_exercises_captured_branch_without_live_reads` | 0 | 1 | 0 | **KILLED** (`Path.is_dir banned`) |
| **MUT-05** | Identity translation (real consumer) | `_identity_names` returns directory-only for hybrid/either | `tests/test_phase2_gate.py::test_hybrid_and_either_resolver_identity` | 0 | 1 | 0 | **KILLED** (`assert rep_declared_ag.found is True`) |
| **MUT-06** | Identity translation (helper) | `lookup_name_for_entry` ignores frontmatter policy, always selecting directory | `tests/test_snapshot_inputs.py::test_selected_entry_uses_agent_identity` | 0 | 1 | 0 | **KILLED** (`assert chosen in _identity_names(agent, entry)`) |
| **MUT-07** | Identity translation (service) | `snapshot_why` passes `entry.name` directly without helper translation | `tests/test_session_snapshot.py::test_snapshot_reports_match_live_reports` | 0 | 1 | 0 | **KILLED** (`assert snap_why.to_dict() == live_why.to_dict()`) |
| **MUT-08** | Capture validation (captured-byte) | `capture_session` suppresses reparse comparison against `entry.parse` | `tests/test_session_snapshot.py::test_change_during_capture_is_rejected` | 0 | 1 | 0 | **KILLED** (`Failed: DID NOT RAISE SnapshotChanged`) |
| **MUT-09** | Capture validation (second-pass discovery) | `capture_session` suppresses second-discovery `e1.content_hash != e2.content_hash` check | `tests/test_session_snapshot.py::test_change_during_capture_is_rejected` | 0 | 1 | 0 | **KILLED** (`Failed: DID NOT RAISE SnapshotChanged`) |
| **MUT-10** | Capture validation (second-pass config) | `capture_session` suppresses config reread comparison in second pass | `tests/test_session_snapshot.py::test_change_during_capture_is_rejected` | 0 | 1 | 0 | **KILLED** (`Failed: DID NOT RAISE SnapshotChanged`) |
| **MUT-11** | No-live-read boundary (display paths) | `snapshot_path` calls live `paths.display()` instead of stored map | `tests/test_session_snapshot.py::test_navigation_has_no_filesystem_fallback` | 0 | 1 | 0 | **KILLED** (`Forbidden live probe invoked during navigation`) |
| **MUT-12** | No-live-read boundary (same location) | `snapshot_same_location` calls live `paths.same_location()` probe | `tests/test_session_snapshot.py::test_navigation_has_no_filesystem_fallback` | 0 | 1 | 0 | **KILLED** (`Forbidden live probe invoked during navigation`) |

Machine-readable results and execution provenances are persisted in `docs/validation/c5/results.json`.

---

## 8. Quality Gates & Snapshot Parity

### 8.1 Four Repository Quality Gates
Executing against Python 3.11 with synthetic `HOME`:

1. **Pytest & Coverage:**
   ```
   563 passed, 1 skipped in 6.01s
   Total test coverage: 94.58% (required threshold: 90.0%)
   ```
2. **Type Checking (`mypy`):**
   ```
   Success: no issues found in 31 source files
   ```
3. **Linting (`ruff check .`):**
   ```
   All checks passed!
   ```
4. **Formatting (`ruff format --check .`):**
   ```
   93 files already formatted
   ```

### 8.2 Snapshot Parity
All 17 terminal render snapshots in `tests/fixtures/snapshots/*.txt` remain byte-identical against HEAD commit `6030c3d`:
- `compare_claude_vs_codex_farm.txt` (`82bbb29b73446d54e10b306d7113e313e3fdbc02bd1a68af1e2b1a41f451d99e`)
- `compare_diverged.txt` (`3b5f7e3c371f79b4bc1eaa5e4077762f298a11e231650da11a727b01b77b0f73`)
- `compare_empty.txt` (`a44031f88ce561bf8391b0fc9b9aa17b88a6adbea47dd4a38058c8defd6886e5`)
- `diff_invalid_copy.txt` (`0efc2a6562d61dce3edc37e7a2e57e92860e08dca49b8fd6b8b9581b9967a354`)
- `diff_markup_is_literal.txt` (`2a89076ca13d27d6e050ad158975bf83bb9f9ed09e91d2c8ad429ba55c6feb6a`)
- `diff_no_baseline.txt` (`004a695cd12072d96de0ee6ab8cef01c170e14fabf18e9492d4e30285b6a4a2a`)
- `diff_no_differences.txt` (`7c604c597e172bbb78582052bb703a46980e8a747a4046c9305fa748c898b898`)
- `diff_not_found.txt` (`62b4b9975695e1a642ae88b5197c16f182e7de499d731fe77b52523bd98d9067`)
- `diff_truncated.txt` (`690e7d75c4c3c3480497ad77f346e307f8ac7d6af246e6c37b8417f947176d06`)
- `diff_truncated_by_chars.txt` (`e7c51a57c3ba9baa95e89a4a3c08ff71f263e058af76e29f7b562a19cc2d9610`)
- `diff_unreadable_copy.txt` (`fd1bf86bb91914bda5f620becb93c1600e860a6ab91eb0b99a907f814b1dd85a`)
- `diff_variant_hash_detection.txt` (`b23489e5e3a1ccb5f5eb2ed5b772d374357ffbcca2685da3e417ae781a2cca92`)
- `doctor_findings.txt` (`88b22aba5b2789bbbafec997f7f95ee661f0364c81200d0d7de9e1fbcbe96edc`)
- `doctor_healthy.txt` (`57d91a4f019e309492d426b0a5eafb1d189b25774ad42c66c20cc0fc83c6e399`)
- `doctor_markup_is_literal.txt` (`0f3f5e72c5e55cfe64884cf27d5180d054fa9716692924e6581c0e6bd91b77ac`)
- `scan_variant_hash_detection.txt` (`4a3d075e87969d8874934eb6d7e8bbf9dee721414ab22630180d47f191bf5762`)
- `why_claude_personal_beats_project.txt` (`2ec1a2c2727f0c26d3acc90f55904fa858b6cad510ae6d2bba92e82e2fe37044`)

Zero snapshot files were modified.

### 8.3 Known Skips & Environmental Boundaries
- **Case-Insensitive Filesystem Skip:** One test (`tests/test_session_snapshot.py:1886`, skip executed at line 1898: `test_case_sensitive_dual_case_preference`) skips on macOS APFS filesystems because distinct physical paths with differing casing cannot coexist on case-insensitive filesystems. This is expected and handled gracefully via `pytest.skip`.
- **Scope Restriction:** This walkthrough audits Step 0 only. No Textual dependency has been installed, no packaging changes made, and no UI screens constructed. Assignments U1 through U9 remain distinct subsequent tasks.

## 9. Coordinator Acceptance

Sol inspected the complete C5 change, independently reproduced all 12 mutation
checks and verified the four gates: **563 passed, 1 skipped, 94.58% coverage**,
strict mypy clean over 31 source files, and Ruff lint/format clean. All 17
snapshot files and production source remain unchanged. Every documented
function signature was checked against source.

MiniMax High returned **pass, no blockers**. Sol accepts that conclusion based
on the direct verification above. The two confirmed planning gaps and the
runner defects found during coordinator review are resolved. Optional follow-ups
are recorded in the dated plan: disable ignored root collection caches, replace
the helper mutation's product-invariant marker with a test-owned assertion, and
split the hybrid/either guard for separate per-policy mutation evidence. None
changes the current acceptance result.

The coordinator verified that deliberately breaking seven runner classification
outcomes makes the protecting self-tests fail; all 15 scenarios pass restored.
The external-output campaign left checkout hashes and status unchanged. Review
fingerprints match, and all six delegated tasks completed with no pending runs.
The dated plan's append-only execution record retains task identities, roster
provenance, review dispositions and timing. C5 completes Step 0; later TUI
installation and screen assignments have not started.
