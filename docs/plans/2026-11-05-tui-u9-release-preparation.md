# Plan: U9 — Prepare the 0.2.0 release

Status: Agreed — frozen planning contract; implementation needs a later owner instruction.
Date: 5 November 2026.
Baseline: `a2b3987a5fe0c7b4388153b9fddb76c76c9bb1ad` on `main`.
Reference: `f3c652beed4e7b5b745a77a900cc1e93f5a5f105` (operative frozen plan).
Authorization: the owner requested U9 planning, exactly two self-review passes,
then freezing and committing the plan.
Roster: the owner explicitly appointed this current Qoder session as the sole
planner. Session configuration is unchanged; underlying provider/model/effort
identity is not independently verified and is not inferred. No planning critics,
subagents or external workers. Future implementer and final critics are not selected.
Risk and review: High — release packaging and installed compatibility are
load-bearing under AGENTS.md §4. The owner explicitly chose solo planning and two
self-reviews instead of independent planning review for this mission only.
Expected child tasks: zero now; a later High-risk implementation normally needs
one implementer and two independent final critics, before corrections.

## Authorization and stop point

This mission changes only this plan and its records under
`docs/validation/u9/planning/`. The two reviews are by one planner in one context,
not independent review or a guarantee of zero defects. Shared process files and
AGENTS.md remain unchanged. The owner reconfirmed this session as planner after
being asked about the roster; no application default or historical roster is
substituted for that designation.

Freeze with the two-commit procedure in [planning-loop.md](../process/planning-loop.md):
the first commit contains only the agreed plan; the second changes only
`Reference:` to the first commit's full hash. Commit planning evidence separately.
No push, tag, release upload, credential use, product implementation or worker
launch is authorized. A future start instruction must appoint any missing
implementation/review roles and select the actual execution host. This planning
exception does not waive future independent implementation review.

## Outcome and authority

Prepare a locally verifiable 0.2.0 distribution containing the completed optional
TUI. A wheel is the installable package; the source distribution is its source
archive. Test what users would install, not an editable checkout, and leave an
explicit publication decision to the owner.

Authority: [FULL_SCREEN_TUI.md](../../FULL_SCREEN_TUI.md) Step 9, §§6.1, 7,
12, 15 and §22 U9; [DEVELOPMENT.md](../../DEVELOPMENT.md) Releasing;
[Phase 5 history](../archive/PHASE5_WALKTHROUGH.md); and the newer
[Stage G packaging acceptance](../validation/assessment-repairs/g/acceptance.md).
Existing product behavior, dependency policy, CLI output and read-only rules do
not change in U9.

## Verified starting point

- U8 is committed at the baseline. The version in `pyproject.toml`,
  `skill_lens/__init__.py` and the root package entry in `uv.lock` is still 0.1.1.
- The local full gate in this conversation passed: 1,338 tests, one existing
  case-insensitive-filesystem skip, 90.10% combined statement/branch coverage;
  mypy and both Ruff checks passed. This is macOS/Python 3.11.16/Textual 8.2.8
  evidence, not manual visual approval. Final planning verification is recorded
  separately under `docs/validation/u9/planning/`.
- GitHub run `42029802744` for the exact baseline passed all eight macOS/Linux ×
  Python 3.11–3.14 test jobs and its packaging job, verified earlier in this
  conversation. A subsequent API read timed out; that does not replace the
  successful receipt or establish a newer result. This is U8 evidence, not U9.
- `scripts/smoke_wheel.py:40–60` explicitly lists only four original TUI modules
  and nine installed test suites. Its archive manifest omits the eight later
  screen/view modules, and its selected suites omit the U8 complete browsing
  and six-view JSON checks. This is a verification gap, not evidence that the
  current wheel actually lacks those files.
- The canonical runner already provides archive, base, minimum and latest lanes,
  isolated homes, installed-origin checks, copied test fixtures without copied
  application source, bounded execution and JSON receipts. Reuse it.
- The optional floor remains `textual>=8.2.8`; the lock pins Textual 8.2.8 and
  Rich 15.0.0. Existing packaging tests deliberately enforce those pins.
  `uv lock --check --offline` passed during inspection.
- Local tracked files were unchanged at the start. Pre-existing untracked files
  and directories are outside scope; preservation fingerprints are in
  [baseline.json](../validation/u9/planning/baseline.json). Do not delete, stage,
  or package them by accident.

## Allowed implementation scope

These are future implementation paths, not permission to edit them during planning.

| File | Permitted change |
| --- | --- |
| `pyproject.toml` | Change project version to 0.2.0 only. |
| `skill_lens/__init__.py` | Change `__version__` to 0.2.0 only. |
| `uv.lock` | Refresh root-package version with `uv lock`; preserve unrelated dependency versions. |
| `scripts/smoke_wheel.py` | Complete the TUI archive manifest and append the exact installed test selections below. |
| `tests/test_tui_packaging.py` | Independent manifest/selection guards, their negative controls, and per-module source-archive omission cases. |
| `README.md` | Accurate prepared-versus-published status and instructions for trying the local candidate. Keep links absolute. |
| `DEVELOPMENT.md` | U9 status, exact artifact verification checklist and separate publication approval boundary. |
| `CHANGELOG.md` | Versioned 0.2.0 preparation entry with implemented changes; retain published history. |
| `FULL_SCREEN_TUI.md` | Status, Step 9 and U9 ledger references only. |
| `SKILL_LENS_SPECIFICATION.md` | Phase 7 status/evidence only, without changing behavior. |
| `docs/validation/u9/implementation/`, `docs/validation/u9/coordinator/` | Reproducible commands, results, hashes, review and acceptance records. |

Do not edit core, registry, models, CLI, presentation or TUI behavior; existing
screen tests, snapshots and goldens stay unchanged. Do not modify CI workflow,
permissions, hooks, build backend, dependency constraints, Python support,
coverage threshold or shared process rules. No new release automation, public
API, database, telemetry or feature work. A discovered product defect or a
necessary broader change must return for explicit scope approval and plan amendment.

## Implementation sequence

### 1. Re-establish the baseline

Verify the frozen reference, actual checkout, user-appointed implementation
roster and pre-existing work. Run the four repository gates before edits, or reuse
an unchanged same-session receipt as permitted by the implementation loop.
Capture environment, source/test hashes and Git status. Read Stage G and the
existing timeout regression in `tests/test_tui_packaging.py` before changing the
runner. No test or application smoke may inspect the real skill directories.

### 2. Complete installed-package verification

Keep the four original `REQUIRED_TUI_MODULES` entries and add these exact paths:

```text
skill_lens/tui/home.py
skill_lens/tui/why.py
skill_lens/tui/diff.py
skill_lens/tui/json_view.py
skill_lens/tui/agents.py
skill_lens/tui/compare.py
skill_lens/tui/doctor.py
skill_lens/tui/help.py
```

Preserve all nine existing `INSTALLED_TUI_TEST_SUITES` entries. Append
`tests/test_tui_routing.py` and these four existing selectors from
`tests/test_tui_help.py`:

```text
test_complete_keyboard_browsing_flow_with_help_json_filters_and_refresh
test_views_stay_on_captured_data_until_refresh_after_fixture_edits
test_all_six_json_views_match_the_cli_serializer_on_same_inputs
test_every_screen_and_help_remains_usable_at_both_sizes
```

Each selector is stored as `tests/test_tui_help.py::<name>`; the last includes both
100×30 and 60×24 parametrizations. Read the complete selected tests and their
helpers before implementation. This is a focused installed smoke, not a claim
that every source test runs in each wheel lane. The full source suite remains
mandatory separately. Do not add a second runner or duplicate the browsing tests.

Add independent expected module and selection assertions in
`tests/test_tui_packaging.py`; deriving both the expected value and fixture from
the same production tuple cannot catch an omitted entry. Assert the expanded
selectors reach the actual installed pytest subprocess command, with no test
filter silently overriding them. Extend synthetic sdist tests so omitting each
required TUI module is rejected by the actual validator; retain the equivalent
wheel tests and the registry/typing-marker guards.

Keep current installed-origin, no-source-copy, base-Textual-absence, nonzero-exit,
and timeout guards. Retain the 300-second endpoint bound and its partial-output
error handling; measure each expanded lane. A timeout is a failure to investigate,
not permission to remove tests, skip a lane or silently increase the bound.

Mutation-check every added guard in disposable copies outside the checkout:
remove each new manifest entry, remove each required installed selection, prevent
one selection reaching the subprocess, and bypass each new sdist rejection path.
Require clean/failing/restored runs with the expected behavioral assertion, not
an import, syntax or collection failure. Record each mutation and disposition.

### 3. Prepare versioning and truthful documentation

Bump both version declarations together, run `uv lock` without upgrade flags,
then `uv lock --check`. Inspect the lock diff: only the root version should need
changing. Investigate unexpected resolver changes; do not hand-edit resolved
records or relax the existing pin tests to accept them.

Create `## [0.2.0] — Unreleased (release preparation)` in the changelog and move
implemented pending changes into that versioned entry. Keep a separate
`[Unreleased]` section for subsequent work. State explicitly that 0.2.0 has not
been uploaded; do not invent a publication date or link to a nonexistent tag.
The existing version-heading test checks documentation presence, not publication.
Preserve the 0.1.0/0.1.1 history and date-specific validation claims.

Update the five current-status documents together. Distinguish released PyPI
0.1.1, the locally prepared 0.2.0 candidate, automated checks, human visual
approval and publication. Do not advertise `pip install 'skill-lens-cli[tui]'`
as an already-available PyPI TUI before publication. Record current CI evidence
against its actual commit rather than copying U8's green result onto U9.

### 4. Build and qualify the exact candidate

Use a new, uniquely owned temporary directory outside the checkout. Do not reuse,
clear or overwrite the existing `dist/` or someone else's smoke environment.
Prepare a clean source export from the recorded Git revision, overlaying only
reviewed changes to the allowed tracked implementation files. Preserve file
modes and links; never copy the working directory wholesale. Exclude unrelated
untracked content and `docs/validation/u9/` receipts from this export. Keep those
receipts as sidecar evidence, so adding an artifact hash cannot change the
artifact that it describes. Record the export's complete path/hash manifest,
its exclusions, base revision and any overlaid input hashes.

Set `source_export` to that export, `python` to the absolute path of the
repository environment's Python, and `artifacts`, `smoke` and `receipt` to separate
owned external paths. Keep build outputs, smoke environments and receipts outside
the source export. Resolve `sdist` after the source build and `wheel` after the
wheel build.

Build a source archive with
`uv build "$source_export" --sdist --out-dir "$artifacts"`, then build the wheel
from that exact archive with `uv build "$sdist" --wheel --out-dir "$artifacts"`.
Resolve one explicit 0.2.0 wheel path and one source-archive path; do not use
`dist/*` to choose among stale artifacts. Run `uvx twine check "$wheel" "$sdist"`.

Inspect archive names and metadata: distribution `skill-lens-cli`, version 0.2.0,
Python ≥3.11, optional Textual dependency, unchanged console entry point, all
12 required TUI modules, ten registry TOMLs and the typing marker. Compare
packaged application bytes against the candidate source. Record SHA-256 hashes
for both artifacts and inspect the source-archive file list for unrelated files.

Run the export's complete runner, so the harness and copied tests come from the
same reviewed inputs as the artifact:

```bash
"$python" "$source_export/scripts/smoke_wheel.py" \
  --wheel "$wheel" --sdist "$sdist" \
  --work-dir "$smoke" --receipt-out "$receipt"
```

All three installation environments must be fresh and outside the checkout;
retain the runner's temporary HOME/XDG settings and source-origin checks. The
existing runner records the base console version, but does not compare all three
installed versions. After it returns, use each preserved lane's own
`venv/bin/python` to assert `importlib.metadata.version("skill-lens-cli") ==
skill_lens.__version__ == "0.2.0"`, and that lane's `venv/bin/skill-lens --version`
to check `skill-lens 0.2.0`. Run those probes from outside the checkout using the
same clean lane environment, and retain their output separately. No new public
runner option or runtime feature is needed. Base must contain no Textual.
Minimum must install exactly 8.2.8; latest must resolve without a Textual version
constraint. Capture actual versions
and disclose if the two endpoints coincide. Recheck the stable Textual release
metadata at execution time, but do not change the approved floor in this scope.

Receipts must show the five added selections actually executed, a positive test
count, no unexpected skips, exact command, duration, exit, installed origins and
artifact hashes. Review the 17 CLI snapshots and 16 JSON goldens without updating
them. An unavailable package index is an incomplete lane, never a pass.

Run the four final source gates after all corrections:

```bash
.venv/bin/pytest --cov=skill_lens
.venv/bin/mypy
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

### 5. Terminal check and readiness handoff

Use the installed candidate with explicit `tui --sandbox <temporary-home>
--cwd <temporary-project>`, never a development editable import or live skills.
At 100×30 and 60×24, inspect Home → Why → Diff → Agents → Compare → Doctor,
Help, raw JSON, filtering, back navigation, refresh and normal quit. Include an
empty fixture and a nonempty fixture with findings. Confirm the cursor and normal
terminal screen return on exit. Check base bare-help/missing-extra behavior and
the extra install's `--plain`/non-interactive fallbacks without scanning live roots.
Record the terminal, OS, installed versions and artifact hash.

Automated terminal driving is technical smoke evidence, not human visual
approval. Ask the owner to review the candidate; if unavailable, mark human
approval pending and withhold publication-ready status. Preserve baseline CI
facts, but require all eight test jobs and packaging to pass on the candidate's
actual commit before publication-ready status; pushing that commit needs separate
authorization. A pending hosted run is not a reason to claim success or publish.

Complete independent final review under the implementation loop, using two
owner-named critics: one on packaging/compatibility/claim accuracy, one on installed
test coverage/isolation/guard effectiveness. Supply the exact council guard and
report schema, full diff, artifact receipts and mutation evidence. Resolve all
in-scope blockers before technical acceptance. Passing U9 preparation never
allows an upload, tag, push or release announcement without separate authorization.

Use two distinct handoff states: **locally technically accepted** means the
local A1–A9 requirements and independent reviews passed, with hosted/human states
reported honestly; **publication ready** additionally requires candidate-specific
hosted CI and human visual approval. Neither state means **published**.

A later authorized publication mission must finalize the release date and public
installation/status wording, rebuild and requalify any artifacts whose packaged
documents changed, and upload only the explicitly checked files. Keep the release
checklist's tag-after-successful-upload order and update its old version examples
for 0.2.0. U9's deliberately unpublished preparation artifacts are not permission
to upload a README that still says the TUI is unavailable.

## Acceptance checklist

| ID | Evidence required |
| --- | --- |
| A1 — scope | Only allowed files changed; pre-existing work preserved; no production behavior or policy change. |
| A2 — version and lock | Both source versions, lock root, archive metadata and installed outputs equal 0.2.0; unchanged dependency policy; lock check passes. |
| A3 — archives | Explicit wheel/sdist hashes, metadata PASS, twelve TUI modules, ten registry files and typing marker; sdist-derived wheel matches source. |
| A4 — meaningful guards | Independent expected manifests/selections, real subprocess-command assertion, per-module sdist omissions and clean/failing/restored mutation evidence. |
| A5 — clean installs | Base/min/latest all pass outside checkout with synthetic HOME, no source leakage, true base Textual absence, and versions/overlap recorded. |
| A6 — browsing and parity | Added selectors execute in both endpoints; all six JSON views match CLI; captured data stays fixed until refresh; both terminal sizes covered. |
| A7 — quality | Four final gates pass; ≥90% combined coverage with TUI measured; no unexplained skip or regenerated pinned output. |
| A8 — docs and handoff | Five status documents agree; exact candidate CI, terminal and human-approval states recorded separately; no unsupported publication claim. |
| A9 — review and authority | Two independent implementation reviews pass; remaining publication prerequisites explicit; no implicit commit/push/upload permission for future work. |

## Risks and stop rules

- Coverage margin is only 0.10 percentage points at baseline. Do not lower the
  threshold or exclude the TUI; unrelated coverage refactoring is not U9 scope.
- The latest dependency endpoint and package indexes can change. Retain exact
  resolved versions and logs, and do not substitute cached/minimum evidence.
- A green U8 packaging job proves only its older selected checks. A green local
  candidate does not prove Linux/matrix success or human approval.
- Any packaged source/doc change after artifact qualification invalidates that
  candidate's hashes; rebuild and repeat affected artifact checks before delivery.
- Do not publish from a wildcard-filled old `dist/` or edit historical evidence
  to make the current result look newer.

## Self-review and freeze record

Two self-review passes are required. Pass 1 checks specification, scope, package
contracts and authorization. Pass 2 checks execution order, acceptance evidence,
negative controls and closure of first-pass findings. Record actual findings,
corrections and before/after hashes under `docs/validation/u9/planning/`.

Pass 1 is complete. It verified the named module paths, existing selectors,
version-heading guard and baseline lock, and corrected two execution gaps:
clean source export with sidecar evidence (avoiding unrelated files and circular
artifact hashes), and explicit installed-version probes in every lane. Details
and revision hashes are in `docs/validation/u9/planning/review-1.json`.

Pass 2 is complete. It tied the runner/test inputs to the same source export as
the package and separated local technical acceptance, publication readiness and
the later publication-document rebuild. The exact proposed installed selection
ran against unchanged source: 420 passed, zero skips, 88.06 seconds pytest time
(88.50 seconds enclosing command). This is a local feasibility probe, not an
installed-wheel, cold-environment or CI result. Details and revision hashes are
in `docs/validation/u9/planning/review-2.json`.

Exactly two formal self-reviews are complete, with no unresolved planning-scope
blocker. Final gate results and preservation checks are recorded separately in
`docs/validation/u9/planning/verification.json`; these are verification, not a
third review. The first plan-only freeze commit is authoritative, and the second
changes only `Reference:`. Future implementation and publication remain unstarted.
