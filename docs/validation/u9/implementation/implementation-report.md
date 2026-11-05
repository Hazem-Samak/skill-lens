# U9 implementation report — 0.2.0 release preparation

Date: 5 November 2026.
Repository: `Skill Lens`, HEAD `da2b8d978d17492e2649d518cc90dea1bcccc4f1`, changes
**uncommitted** (no commit, push, tag or upload was made).
Frozen plan: `docs/plans/2026-11-05-tui-u9-release-preparation.md`, operative
reference `f3c652beed4e7b5b745a77a900cc1e93f5a5f105`, SHA-256
`68812f6d0951be0ae94d8479799b8a8e9a9c4ba0edfc36fdc5022ab391017b5a`;
the worktree copy differs from that reference only by the `Reference:` line
(`inputs.json`).

OUTCOME: succeeded — locally technically accepted candidate prepared.
FILES CHANGED: `pyproject.toml`, `skill_lens/__init__.py`, `uv.lock`,
`scripts/smoke_wheel.py`, `tests/test_tui_packaging.py`, `README.md`,
`DEVELOPMENT.md`, `CHANGELOG.md`, `FULL_SCREEN_TUI.md`,
`SKILL_LENS_SPECIFICATION.md` — ten tracked files, all inside the plan's allowed
table. Evidence added under `docs/validation/u9/implementation/` (untracked).
DEVIATIONS FROM PLAN: one in-file correction is recorded below (the installed-lane
receipt parser). It changes no product behaviour, dependency or policy.
BLOCKED ON: human visual approval and hosted CI for the candidate commit — both
outside this implementer's authority.

## What changed and why

**Installed-package verification (plan step 2).** `scripts/smoke_wheel.py` now
requires all twelve shipped TUI modules (the four original plus Home, Why, Diff,
JSON view, Agents, Compare, Doctor, Help) in both archives, and its installed
lane runs the five selections the plan names: `tests/test_tui_routing.py` plus
four `tests/test_tui_help.py` node IDs covering the complete keyboard browsing
flow, captured-data stability, six-view CLI JSON parity and both terminal sizes.
The nine original suites are untouched. The receipt now records the pytest
summary line and the suite duration, and refuses to report a lane that passed no
tests (see "Problems found").

**Meaningful packaging guards (plan step 2, last paragraph).**
`tests/test_tui_packaging.py` grew from 26 to 67 collected items with:
an independent, hand-maintained 12-module manifest and 14-selection list
(deliberately not derived from the production tuples); a completeness check that
every shipped `skill_lens/tui/*.py` is in the manifest; a static node-ID existence
check; a parametrization check that the selected size case really covers 100×30
and 60×24; a real subprocess-argv assertion that the full selection reaches the
lane's own pytest with no `-k`/`--deselect`/`--ignore`-style filter; per-module
sdist omission cases; a lock-root version guard; and negative controls for each
guard. The original registry, typing-marker, provenance, timeout and
source-leak guards are retained.

**Versioning and documents (plan step 3).** `pyproject.toml`, `__version__` and
the `uv.lock` root package read 0.2.0; `uv lock` changed only that line and
`uv lock --check` passes. `CHANGELOG.md` gained a
`## [0.2.0] — Unreleased (release preparation)` entry that holds the implemented
changes (with no tag link, because `v0.2.0` does not exist) and keeps
`[Unreleased]` for later work. `README.md`, `DEVELOPMENT.md`,
`FULL_SCREEN_TUI.md` and `SKILL_LENS_SPECIFICATION.md` now separate published
0.1.1, the locally prepared candidate, automated checks, human visual approval and
publication; `DEVELOPMENT.md` gained an exact candidate-qualification checklist.

**Candidate build and qualification (plan step 4).** A clean source export was
made from `git archive HEAD` (1 898 files), `docs/validation/u9/` was removed, and
only the ten reviewed files were overlaid; the default `uv build` of the working
directory would have packaged 804 pre-existing untracked files, so building the
export is not cosmetic. The sdist was built from the export, the wheel from that
sdist, and both passed `twine check`.

## Acceptance criteria → evidence

| ID | Key evidence | State |
| --- | --- | --- |
| A1 | `inputs.json`, `baseline-git-status.txt`; ten changed files; 804 pre-existing untracked paths byte-identical in path set | pass |
| A2 | `lock-check.log`, `candidate.json`, `version-probes.json`, `gates.json` | pass |
| A3 | `candidate-build.log`, `candidate.json` (16/16 checks, both hashes) | pass |
| A4 | `mutations/mutations.json` 23/23 caught (clean/mutant/restored 0/1/0), `final-pytest.log` | pass |
| A5 | `install-receipt.json`, `version-probes.json`, `textual-metadata.json` | pass |
| A6 | `install-receipt.json`, `added-selections.log` (52 passed), `terminal-receipt.json` | pass |
| A7 | `gates.json`, `final-pytest.log` | pass locally |
| A8 | Five documents' diff, `doc-consistency.md` | pass |
| A9 | This report; nothing committed, pushed, tagged or published | awaiting coordinator review |

Full mapping: [`acceptance-matrix.md`](acceptance-matrix.md).

## Exact commands and results

Baseline before edits (HEAD `da2b8d9`, unchanged source): `pytest --cov=skill_lens`
→ 1 338 passed, 1 skipped, 90.10% combined coverage, 423.87 s; `mypy` → 46 files
clean; `ruff check .` and `ruff format --check .` clean.

Final gates after all corrections (`gates.json`, logs `final-*.log`):

```bash
.venv/bin/pytest --cov=skill_lens   # 1379 passed, 1 skipped, 90.10%, 444.11 s, exit 0
.venv/bin/mypy                      # Success: no issues found in 46 source files
.venv/bin/ruff check .              # All checks passed!
.venv/bin/ruff format --check .     # 433 files already formatted
```

The gates ran after the last code, test and tracked-document change; only untracked
evidence documents were added afterwards (they are outside pytest's `testpaths`,
mypy's file list and the coverage source). ruff's "files" counter includes every
file it walks, which is why it grows with the evidence directory.
The single skip is the pre-existing case-insensitive-filesystem case
(`tests/test_session_snapshot.py:1979`), unchanged from the baseline. The 41 new
passing items are exactly `tests/test_tui_packaging.py` (26 → 67).

Clean export, build and archive inspection (`qualify_candidate.py`,
`candidate.json`, `candidate-build.log`):

```bash
git -C "$root" archive --format=tar HEAD | tar -x -C "$work/src"
rm -rf "$work/src/docs/validation/u9"
# overlay the ten reviewed files
uv build "$work/src" --sdist --out-dir "$work/artifacts"
uv build "$work/artifacts/skill_lens_cli-0.2.0.tar.gz" --wheel --out-dir "$work/artifacts"
uvx twine check "$work/artifacts/skill_lens_cli-0.2.0-py3-none-any.whl" \
  "$work/artifacts/skill_lens_cli-0.2.0.tar.gz"
```

- export: revision `da2b8d9`, 1 898 files, `docs/validation/u9/` excluded, ten
  overlaid inputs with recorded hashes (`candidate.json` → `export`).
- wheel `skill_lens_cli-0.2.0-py3-none-any.whl`, 62 files, SHA-256
  `91f6c55329d19b14a5bd9e1a1a7aa1f194d09d17d09dab7b4dc8ffc366c4e107`, retained at
  `/tmp/u9-candidate/artifacts/`.
- sdist `skill_lens_cli-0.2.0.tar.gz`, 1 899 files, SHA-256
  `53263ddeb55935874c1efdbe6f28c5efbce8ba7f557aab3bff3fd2ef18430233`, retained at
  `/tmp/u9-candidate/artifacts/`.
- `twine check`: PASSED for both. Metadata: `skill-lens-cli` 0.2.0,
  `Requires-Python >=3.11`, `Provides-Extra: dev, tui`,
  `Requires-Dist: textual>=8.2.8; extra == "tui"`, unchanged console script
  `skill-lens = skill_lens.cli:app`, 12 TUI modules, 10 registry TOMLs,
  `skill_lens/py.typed`. Packaged Python bytes equal the export; the sdist
  contains every export file and nothing else (`PKG-INFO` aside).

Installed lanes (`install-receipt.json`, `install-harness.log`), all outside the
checkout with synthetic HOME/XDG and copied tests but no copied source:

```bash
.venv/bin/python "$work/src/scripts/smoke_wheel.py" \
  --wheel "$work/artifacts/skill_lens_cli-0.2.0-py3-none-any.whl" \
  --sdist "$work/artifacts/skill_lens_cli-0.2.0.tar.gz" \
  --work-dir "$work/smoke" --receipt-out "$work/install-receipt.json"
```

- base lane: Textual absent, provenance inside its venv, `skill-lens 0.2.0`,
  bare non-interactive run exit 0 with no tip, explicit `tui` exit 2 with the
  `skill-lens-cli[tui]` hint and no traceback.
- minimum lane (`textual==8.2.8`): **461 passed, 0 skipped**, suite 88.41 s
  (lane elapsed 89.23 s), exit 0.
- latest lane (unconstrained): **461 passed, 0 skipped**, suite 89.09 s
  (lane elapsed 89.92 s), exit 0.
- each lane's own `venv/bin/python` reports
  `importlib.metadata.version("skill-lens-cli") == skill_lens.__version__ == "0.2.0"`,
  each `venv/bin/skill-lens --version` prints `skill-lens 0.2.0`, and the imported
  module lives inside that lane's `site-packages` (`version-probes.json`,
  `terminal-receipt.json`).
- endpoint overlap: both lanes resolve Textual **8.2.8** because that is today's
  latest stable release (`textual-metadata.json`, PyPI JSON API, HTTP 200). This
  is two installation checks, not two-version coverage; the approved floor was
  not changed.

Installed terminal interface (`terminal_check.py`, `terminal-receipt.json`),
driven through a real pseudo-terminal from outside the checkout against the
installed binary and synthetic fixtures only:

- nonempty fixture (two agents, three variants of one skill, one dangling
  symlink): 20 steps at **100×30** and 20 steps at **60×24** — Home, Help open and
  dismiss, Why, Diff, back-navigation, Agents, Compare picker and result, Doctor
  with the `dangling_symlink` finding, raw JSON on/off, filter with typed
  no-match text and Esc clear, agent filter, refresh, quit.
- empty fixture: 5 steps at each size — empty-state sentence, Help, raw JSON
  on/off.
- every scenario: exit 0, alternate screen left (`?1049l`), cursor shown
  (`?25h`).
- fallbacks: `--plain` in a PTY prints help and not the TUI; bare non-interactive
  prints help with no tip; explicit `tui` non-interactive exits 2; base lane bare
  in a PTY prints help **plus** the install tip; base lane `tui` exits 2 with the
  extra hint and no traceback.
- environment: macOS 27.0.0 arm64, `TERM=xterm-256color`, installed 0.2.0 with
  Textual 8.2.8, wheel SHA-256 as above.
- isolation: every `$HOME`-relative root is remapped into the fixture by
  `--sandbox`, and the registry's only absolute system root (`/etc/codex`) does
  not exist on this host, so no real skill directory was read.

Mutation evidence (`mutations/mutations.json`): 23 deliberate breakages, each in
a disposable copy outside the checkout, each with clean/mutant/restored runs
`0/1/0` and a behavioural assertion — every new manifest entry removed (8), every
added installed selection removed (5), a `-k` filter injected and a selection
truncated before the pytest call (2), the sdist module check removed and its
omission ignored (2), the selected node renamed and the size parametrization
shrunk (2), three receipt-parser breakages, and a stale lock root version (1).
All 23 were caught.

## Problems found during self-review, and corrections

The full list with hashes and reasoning is in [`self-review.md`](self-review.md).
The material ones:

1. **The installed-lane receipt silently claimed zero tests.** pytest's current
   summary line ends with an elapsed parenthetical; the old pattern rejected it
   and the code fell back to `test_count: 0`, so the first full harness run
   "passed" while describing an empty lane. Fixed with a strict parser, a
   positive-count guard, recorded `pytest_summary`/`elapsed_seconds`, four new
   tests and three mutations. The final receipt shows 461 passed in both lanes.
2. **The terminal provenance probe imported the checkout.** It ran the lane's
   Python from the repository directory, so `python -c` found the source tree
   first. Version numbers matched by luck; the receipt is now generated with an
   explicit outside-the-checkout working directory and shows `site-packages`
   provenance plus `driver_cwd`.
3. **The terminal driver lost the exit sequences** by draining the pseudo-terminal
   only after the process exited (macOS returns EIO), which read as a false
   restore failure. It now drains while the app is still running.
4. **Guards needed two corrections**: the completeness check compared sorted
   against declared order, and it assumed a source tree that does not exist in an
   installed lane; both were fixed and re-verified with a rehearsal wheel install
   before the long run.
5. **The build root was unsafe**: `uv build .` packages the whole working
   directory, including 804 pre-existing untracked files. The candidate is built
   only from the clean export, and `DEVELOPMENT.md` now says so.
6. **`DEVELOPMENT.md` mis-described the base lane** (help plus tip on a
   non-interactive run); corrected, and a PTY probe now covers the interactive
   tip path.

## Publication state (three separate states, no overlap)

- **Published:** PyPI `skill-lens-cli` **0.1.1**, six line-oriented commands, no
  TUI extra. Unchanged by this work.
- **Locally technically accepted:** the 0.2.0 candidate described here — versions,
  lock, archives, three fresh installations, installed terminal smoke, four
  source gates and 23/23 mutation checks. Nothing is committed or pushed.
- **Publication ready:** **not reached.** It additionally needs hosted CI green on
  the candidate's own commit (which requires an authorized push) and human visual
  approval of the interface. No upload, tag, release date or announcement exists
  or is implied.

## Retained artifacts and paths

- Evidence: `docs/validation/u9/implementation/` (receipts, logs, scripts,
  mutation copies of the diffs and failure output).
- Export: `/tmp/u9-candidate/src` (manifest in `candidate.json`).
- Artifacts: `/tmp/u9-candidate/artifacts/skill_lens_cli-0.2.0-py3-none-any.whl`,
  `/tmp/u9-candidate/artifacts/skill_lens_cli-0.2.0.tar.gz`.
- Installed lanes (kept for review): `/tmp/u9-candidate/smoke/{base,min,latest}_lane`.
- Receipts: `/tmp/u9-candidate/install-receipt.json` (copy in this directory),
  `/tmp/u9-candidate/logs/`.
- Terminal fixture and driver output: `/tmp/u9-terminal/`.
- Mutation scratch trees: `/tmp/u9-mutations/`.
- Pre-existing local `dist/` was not read, cleared or reused.
