# U9 acceptance matrix

Frozen plan: `docs/plans/2026-11-05-tui-u9-release-preparation.md`
(reference `f3c652beed4e7b5b745a77a900cc1e93f5a5f105`).
Implementation checkout: `da2b8d978d17492e2649d518cc90dea1bcccc4f1`, uncommitted
changes only. Evidence in this directory; every JSON receipt records the command
that produced it.

| ID | Requirement | Evidence | Status |
| --- | --- | --- | --- |
| A1 — scope | Only the ten allowed tracked files changed; pre-existing untracked work preserved; no production behaviour, dependency or policy change. | `inputs.json` (`modified_tracked_files`, `changed_file_hashes`, `preservation`); `baseline-git-status.txt`; `git diff --stat` in the report. The production code diff is two version strings; `scripts/`, `tests/` and docs only otherwise. | Pass |
| A2 — version and lock | Both source versions, the lock root, archive metadata and all three installed lanes read 0.2.0; `uv lock --check` passes; the lock diff changes only the root version. | `lock-check.log`; `candidate.json` → `wheel_name_version`, `sdist_name_version`; `version-probes.json` → all lanes `metadata=0.2.0 package=0.2.0 cli='skill-lens 0.2.0'`; `test_uv_lock_root_package_version_matches_the_package`. | Pass |
| A3 — archives | Explicit wheel/sdist hashes; metadata PASS; twelve TUI modules, ten registry TOMLs and the typing marker in both archives; the wheel is built from the sdist and its packaged bytes equal the export. | `candidate.json` (16/16 checks, both hashes, `packaged_python_matches_export`, `sdist_contains_all_export_files`, `sdist_has_no_unexpected_files`, twine output); `candidate-build.log`. | Pass |
| A4 — meaningful guards | Independent expected manifest and selection lists; a real subprocess-argv assertion with filter detection; per-module sdist omission cases; clean/failing/restored mutation evidence with behavioural assertions. | `tests/test_tui_packaging.py` (26 → 67 collected items; full suite 1338 → 1379 passed); `mutations/mutations.json` → 23/23 caught, each `clean_exit=0`, `mutant_exit=1`, `restored_exit=0`, `mutant_failure_kind=behavioral-assertion`; per-mutation logs. | Pass |
| A5 — clean installs | Base/minimum/latest lanes fresh and outside the checkout, synthetic HOME, installed origins, true base Textual absence, versions and endpoint overlap recorded. | `install-receipt.json` (base `textual_absent=true`, provenance inside each lane venv, `461 passed / 0 skipped` per TUI lane, installed package list, `endpoint_overlap`); `version-probes.json`; `textual-metadata.json` (latest stable 8.2.8 = floor). | Pass |
| A6 — browsing and parity | The five added selections execute in both endpoints; all six JSON views match the CLI serializer; captured data stays fixed until refresh; both terminal sizes are covered. | `install-receipt.json` → `command` carries `tests/test_tui_routing.py` plus the four `tests/test_tui_help.py::…` node IDs, `pytest_summary` = `461 passed in 88.41s` / `89.09s`; the 17 snapshots and 16 goldens are inside those selections and were not regenerated (`git status tests/fixtures` empty); `terminal-receipt.json` → both sizes driven through all six screens. | Pass |
| A7 — quality | Four final gates pass; combined coverage ≥ 90% with `tui/` measured; no unexplained skip; no pinned output regenerated. | `final-pytest.log`, `final-mypy.log`, `final-ruff-check.log`, `final-ruff-format-check.log`; coverage line and skip line in `final-pytest.log`; snapshot/golden directories unmodified. | Pass locally |
| A8 — docs and handoff | The five status documents agree; published 0.1.1, the locally prepared candidate, automated checks, human visual approval and publication are stated separately; no unsupported publication claim. | `README.md`, `DEVELOPMENT.md`, `CHANGELOG.md`, `FULL_SCREEN_TUI.md`, `SKILL_LENS_SPECIFICATION.md` in this diff; `implementation-report.md` §"Publication state". | Pass |
| A9 — review and authority | Two independent implementation reviews remain to be run by the coordinator; remaining publication prerequisites are explicit; no implicit commit/push/upload permission. | This matrix and the report; the work is uncommitted, unpushed, untagged and unpublished. | Awaiting coordinator |

## Explicitly not claimed

- Human visual approval of the candidate interface.
- Hosted CI for the candidate's commit (the candidate is uncommitted; U8's green
  run and this branch's baseline gates prove their own commits, not this one).
- Publication, a tag or a release date. Published PyPI remains 0.1.1.
- Linux or Python 3.12–3.14 execution of this candidate; only macOS 27.0.1 arm64
  with CPython 3.11.16 was exercised locally.
- Bit-reproducible wheel bytes: a rebuild changes the ZIP timestamps, so the
  artifact hash is build-specific. Content identity is checked instead (module
  set and per-file SHA-256 against the export).
