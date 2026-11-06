# Developing Skill Lens

This file is for people **working on** Skill Lens. The user-facing overview is
[`README.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/README.md).

Maintainer material lives here rather than in the README because PyPI renders the
README as the project page: keeping the build diary and the release checklist out
of it leaves [pypi.org/project/skill-lens-cli](https://pypi.org/project/skill-lens-cli/)
readable for people who only want to install the tool.

## Build record

`skill-lens-cli` 0.2.0 is **published** (PyPI, tag `v0.2.0`); Phases 0–7 are
complete and reviewed, and development continues from here. The specification lives in
[`SKILL_LENS_SPECIFICATION.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/SKILL_LENS_SPECIFICATION.md)
and the build proceeds by phase:

- [x] **Phase 0** — frozen models, lazy path resolution, 12 golden fixtures
- [x] **Phase 1** — metadata parser, streaming SHA-256 hasher, symlink canonicalization
- [x] **Phase 2** — registry loader, 3-axis resolver, `scan` / `why` / `agents` commands
  — ✅ **reviewed and corrected**: all 20 findings in
  [`PHASE2_FINDINGS.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/docs/archive/PHASE2_FINDINGS.md)
  (F-01 … F-20) are fixed and each is guarded by a regression test
- [x] **Phase 3** — Rich presentation layer and `diff` — unified diff between the
  differing variants of one name, pinned by a golden `diff_*.json` and plain-text
  render snapshots for `scan`, `why` and `diff` — ✅ **reviewed and corrected**: all 4
  findings in
  [`PHASE3_FINDINGS.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/docs/archive/PHASE3_FINDINGS.md)
  (D-01 … D-04) are fixed and each is guarded by a regression test
- [x] **Phase 4** — `doctor` hygiene checks, multi-agent `compare`, and the live
  discovery adapter — pinned by golden `doctor_*.json` / `compare_*.json` fixtures,
  render snapshots, and a live smoke test that runs with the sandbox off
  — ✅ **reviewed and corrected**: all 8 findings in
  [`PHASE4_FINDINGS.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/docs/archive/PHASE4_FINDINGS.md)
  (C-01 ... C-08) are fixed, three suggestions rejected with written reasons
- [x] **Phase 5** — packaging and release readiness: a PEP 561 `py.typed` marker,
  a locked reproducible install (`uv.lock`), a CI workflow running lint and tests on
  macOS and Linux across Python 3.11–3.14, a `CHANGELOG.md`, and verified `pip` /
  `uvx` installs
  — ✅ the first CI run caught and fixed two real cross-version bugs (a symlink
  loop and a permission-blocked directory both crashed old Pythons); the suite now
  passes on Python 3.11–3.14
  — ✅ **post-release hardening**: `tests/test_phase5_gate.py` pins the packaging
  declarations (version sync, console script, wheel target, registry count, CI
  matrix vs `requires-python`, and that CI can never publish)
  — ✅ **published**: `skill-lens-cli` 0.1.0 went live on PyPI on 2026-10-01 and is
  tagged `v0.1.0`; publishing stays manual and deliberate, with the exact steps in
  [Releasing](#releasing) below
- [x] **Phase 6** — *new scope, added after 0.1.0 and not in the original roadmap.*
  Two gaps that only appeared once the tool ran against a real machine:
  — **enforceable findings**: a documented exit-code contract (`0` clean, `1`
  findings, `2` bad usage) plus `--fail-on {never,error,warning,info}` on `doctor`
  and `scan`, so the tool can gate a CI pipeline instead of only reporting.
  **The default is `never`, so 0.1.0 behaviour is unchanged.** See
  [`PHASE6_WALKTHROUGH.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/docs/archive/PHASE6_WALKTHROUGH.md)
  — **evidence integrity**: `dsh` and `omp` were the only agents with no source
  and entirely inferred rules. Both now cite their real vendor documentation —
  which revealed that `dsh` was **missing both user-level roots** and that `omp`'s
  managed-skills folder was ranked **above** the folders that should win. All 10
  agents now cite a source, and an enforced invariant guarantees it.
- [x] **Phase 7 (0.2) — interactive full-screen TUI** — *new scope; implemented
  through U8 and published by U9 as 0.2.0 on 2026-11-05 (PyPI
  `skill-lens-cli` 0.2.0, tag `v0.2.0`).* An optional, additive, read-only
  browsing layer built on the existing frozen models, shipped as the opt-in
  `[tui]` extra so the base install gains nothing. Overturns the v1 "no
  full-screen TUI" rule for 0.2. The complete plan — vision, screens, phasing
  and gates — is [`FULL_SCREEN_TUI.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/FULL_SCREEN_TUI.md).
  **Status:** C1–C5 (byte/hash helpers, captured engine inputs, capture and
  cancellation, presentation extraction, Step 0 audit) and U1–U3 (optional install, worker controller, Home browsing screen) are
  accepted; U4 Why resolution screen is technically accepted in development
  with independent review and directly verified final test corrections.
  U5 (the read-only unified Diff screen and the raw JSON mode of Home, Why and
  Diff) is **technically accepted in development** after coordinator verification,
  mutation rechecks and both independent final-review follow-ups. Final evidence:
  [`docs/validation/u5/acceptance.md`](docs/validation/u5/acceptance.md).
  U6 Agents and Compare are implemented in the current working tree, with local
  implementer checks in `docs/validation/u6/implementation/` and passing final
  [parent technical verification](docs/validation/u6/coordinator/verification.md).
  U7 Doctor is implemented in the current tree; its local checks and mutation
  evidence are recorded in `docs/validation/u7/implementation/`.
  [Parent technical verification](docs/validation/u7/coordinator/verification.md)
  passed. U8 Help, keyboard polish, empty/error states and user documentation are
  implemented in the current working tree; the frozen plan is
  [`2026-11-04-tui-u8-polish-help-docs.md`](docs/plans/2026-11-04-tui-u8-polish-help-docs.md)
  and local implementation evidence is under
  [`docs/validation/u8/implementation/`](docs/validation/u8/implementation/).
  Coordinator technical verification passed and both independent final reviews
  (mcode/MiniMax-M3.1-Flash/xhigh and OpenCode/GLM-5.3-Flash-Free/max) returned
  pass with no blockers on 5 November 2026; the ledger and verbatim reports are
  under [`docs/validation/u8/coordinator/`](docs/validation/u8/coordinator/).
  U9 prepared the 0.2.0 candidate: both version declarations and the lock root
  read 0.2.0, the archive/installed harness now covers all 12 TUI modules and the
  U8 browsing/parity selections, and a wheel plus source archive were built from a
  clean source export and installed into three fresh environments. Frozen plan:
  [`2026-11-05-tui-u9-release-preparation.md`](docs/plans/2026-11-05-tui-u9-release-preparation.md);
  evidence, hashes and recorded limits are under
  [`docs/validation/u9/implementation/`](docs/validation/u9/implementation/)
  (first wave) and `docs/validation/u9/coordinator/precommit/` (rebuilt
  candidate; see the supersession note).
  **Published 2026-11-05:** uploaded to PyPI as `skill-lens-cli` 0.2.0 and
  tagged `v0.2.0` after two independent final reviews passed, the owner's
  visual approval of the interface, and a green hosted CI matrix on the
  release commit; the review wave and publication receipts are under
  [`docs/validation/u9/coordinator/`](docs/validation/u9/coordinator/). The
  2026-10-04 readiness review recorded two
  engine fixes required before Step 0: P1 (non-object settings robustness) and
  P2 (lock decoding robustness). Both have been implemented and verified with
  regression tests. P3 cost and capture-scope review measured full capture vs
  selective retention on synthetic fixtures (>600 skills), confirming the §21 Q9
  full-capture contract is practical and retained for its limited fixture result.
  Sections 21–22 define the exact Step 0 input types, engine signatures, capture
  algorithm, acceptance tests and ordered assignments for implementers (C1–C5);
  §22 is the ordered assignment list. Bare launch requires both terminal input
  and output.

  **HISTORY INDEX (dated records, marked historical — not edited here):** prior
  plans and walkthroughs under `docs/archive/`:
  [`PHASE2_FINDINGS.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/docs/archive/PHASE2_FINDINGS.md)
  (F-01…F-20), [`PHASE3_FINDINGS.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/docs/archive/PHASE3_FINDINGS.md)
  (D-01…D-04), [`PHASE4_FINDINGS.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/docs/archive/PHASE4_FINDINGS.md)
  (C-01…C-08), [`PHASE5_WALKTHROUGH.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/docs/archive/PHASE5_WALKTHROUGH.md),
  [`PHASE6_PLAN.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/docs/archive/PHASE6_PLAN.md),
  [`PHASE6_WALKTHROUGH.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/docs/archive/PHASE6_WALKTHROUGH.md),
  [`TUI_PLAN_REVIEWS.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/docs/archive/TUI_PLAN_REVIEWS.md).
  The 2026-10-04 readiness review (P1/P2/P3) is recorded in
  `FULL_SCREEN_TUI.md` §20 as a historical readiness finding.
  C1–C5 / U1–U3 plan links (dated, existing docs/plans files; no C1 plan file
  exists — not invented here):
  [`2026-10-06-tui-c2-captured-engine-inputs.md`](docs/plans/2026-10-06-tui-c2-captured-engine-inputs.md),
  [`2026-10-07-tui-c3-capture-and-cancellation.md`](docs/plans/2026-10-07-tui-c3-capture-and-cancellation.md),
  [`2026-10-11-tui-c4-presentation-extraction.md`](docs/plans/2026-10-11-tui-c4-presentation-extraction.md),
  [`2026-10-11-tui-c5-step0-audit.md`](docs/plans/2026-10-11-tui-c5-step0-audit.md),
  [`2026-10-11-tui-u1-optional-install.md`](docs/plans/2026-10-11-tui-u1-optional-install.md),
  [`2026-10-12-tui-u2-controller-skeleton.md`](docs/plans/2026-10-12-tui-u2-controller-skeleton.md),
  [`2026-10-19-tui-u3-home.md`](docs/plans/2026-10-19-tui-u3-home.md),
  [`2026-10-29-tui-u5-diff-json.md`](docs/plans/2026-10-29-tui-u5-diff-json.md).

  **Historical Stage H reconciliation (2026-10-16):** at that date, C1–C5
  and U1–U2 were shipped development work (TUI entrypoint/controller/skeleton),
  with U3–U9 screens and 0.2 publishing remaining future work. Published PyPI
  0.1.1 has no TUI extra; do not recommend released `skill-lens-cli[tui]`.
  *(Superseded 2026-11-06: `skill-lens-cli` 0.2.0 with the optional
  `[tui]` extra is now published and installed from PyPI; the sentence above
  describes the 2026-10-16 state and is kept unmodified as history.)*

Latest dated verification: the U9 review wave and publication receipts under
[`docs/validation/u9/coordinator/`](docs/validation/u9/coordinator/)
(5 November 2026) — two independent final review reports, the r2/r3/r4 rebuild
qualifications, fingerprints and the publication record. The prior
[U8 coordinator review receipt, 5 November 2026](docs/validation/u8/coordinator/review-receipt.json)
records the four-gate baseline, the native pseudo-terminal smoke run, and both
independent final reviews passing with no blockers. U8 Help implementation
and its local gate/mutation evidence remain recorded under
[`docs/validation/u8/implementation/`](docs/validation/u8/implementation/); that
is implementer evidence. Earlier dated records such as
[U7 parent technical verification, 4 November 2026](docs/validation/u7/coordinator/verification.md)
are retained: it records native Doctor implementation, parent review and the four
local gates; coverage is the combined score
with branch measurement enabled, not the branch-only percentage. Earlier
[Stage G acceptance](docs/validation/assessment-repairs/g/acceptance.md) retains
its packaging and installed-wheel evidence. Unexecuted CI lanes are not claimed.

Historical Stage H closed the assessment repairs with status documentation and
[synthetic byte-heavy capture/refresh measurements](docs/validation/assessment-repairs/h/resource-risk.md).
Stage H itself added no resource policy. Later R01 added the default 256 MiB
captured skill-payload budget; discovery still parses source files before that
measurement. U3 supplies the Home table, filters and metadata preview, U4 the
Why detail screen, and U5 adds the Diff screen plus the raw JSON mode of Home,
Why and Diff (technically accepted after coordinator verification, mutation
rechecks and both independent final-review follow-ups). U6 Agents and Compare
are implemented with local implementer evidence under
`docs/validation/u6/implementation/` and passing parent checks under
`docs/validation/u6/coordinator/verification.md`. U7 Doctor is implemented in
the current tree with local evidence under `docs/validation/u7/implementation/`;
[parent verification](docs/validation/u7/coordinator/verification.md) passed.
U8 adds the Help overlay, contextual keymap, covered-screen worker suspension,
empty/error polish and user documentation; its frozen plan and local evidence are
linked above. U9 prepared, reviewed and published 0.2.0 on 5 November 2026
(upload first, then tag `v0.2.0`).

> The Phase 6 plan is
> [`PHASE6_PLAN.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/docs/archive/PHASE6_PLAN.md);
> what shipped and what was wrong along the way is in
> [`PHASE6_WALKTHROUGH.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/docs/archive/PHASE6_WALKTHROUGH.md).

## Development workflow

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest --cov=skill_lens       # test suite + the coverage gate (fails under 90%)
mypy                          # strict type check of skill_lens/
ruff check .                  # lint
ruff format .                 # format
```

The coverage threshold lives in `[tool.coverage.report]` and the type-check
scope in `[tool.mypy]`, both in `pyproject.toml` — one source of truth each, so
CI enforces exactly what a local run does.

### Replaying the U8 Help and lifecycle checks

The U8 acceptance evidence is reproducible from the checkout:

```bash
pytest tests/test_tui_help.py              # Help, keymap, worker, refresh and state matrix
pytest tests/test_tui_read_only.py         # AST guard + target-preservation lifecycle
pytest tests/test_tui_home.py tests/test_tui_why.py tests/test_tui_diff.py \
       tests/test_tui_agents.py tests/test_tui_compare.py tests/test_tui_doctor.py
```

The semantic tests drive real Textual `Pilot` key events and assert focus, stack
identity, scroll, controller ownership and literal content; they do not pin
text-grid screenshots. Covered-worker tests use threading events and bounded
waits for delayed Why/Diff/Compare work, then deliver old and current outcomes
explicitly. Mutation controls, failure output, restored controls and the exact
commands are recorded in
[`docs/validation/u8/implementation/mutations/`](docs/validation/u8/implementation/mutations/);
they run in disposable copies outside the reviewed checkout. Final gate logs,
source/test hashes and the acceptance-to-test map are in
[`docs/validation/u8/implementation/`](docs/validation/u8/implementation/).
These are local, headless checks: they do not establish human visual approval,
installed-wheel qualification, hosted CI acceptance or a release.

Terminal output is pinned by plain-text snapshots under
`tests/fixtures/snapshots/`. After an intentional change to the presentation
layer, review the difference and regenerate them with:

```bash
pytest tests/test_render_snapshots.py --update-snapshots
```

The Phase 4 machine-readable contracts are pinned as JSON goldens under
`tests/fixtures/golden/phase4/`. A missing or stale golden fails the test --
regenerate only after reading the diff, with:

```bash
pytest tests/test_phase4_gate.py --update-goldens
```

All tests run against synthetic fixtures under temporary directories. The test
suite never reads your real `~/.claude`, `~/.agents`, or `~/.codex`.

## Releasing

Releases are **manual and deliberate**. Nothing publishes automatically and the
CI workflow never uploads anything.

1. Bump `version` in `pyproject.toml` and `__version__` in
   `skill_lens/__init__.py`, then refresh the lock with `uv lock`.
   `test_phase5_gate.py` fails if those two versions ever disagree, and
   `test_changelog_documents_the_current_version` fails if the new version is not
   in [`CHANGELOG.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/CHANGELOG.md)
   under a released heading.
2. Run the full gate: `pytest --cov=skill_lens`, `mypy`, `ruff check .`,
   `ruff format --check .`.
3. Build and inspect the artifacts — **from a clean export, never the live
   checkout** (`uv build .` packages the whole working directory, untracked
   files included; see the 0.2.0 candidate qualification checklist below).
   With `$root` the repository and `$work` a fresh scratch directory you own
   outside it:
   ```bash
   mkdir -p "$work/src" "$work/artifacts"
   git -C "$root" archive --format=tar HEAD | tar -x -C "$work/src"
   # overlay the reviewed changes onto the export, then:
   uv build "$work/src" --sdist --out-dir "$work/artifacts"
   uv build "$work/artifacts/skill_lens_cli-<version>.tar.gz" --wheel --out-dir "$work/artifacts"
   uvx twine check "$work/artifacts"/*                # metadata must PASS
   unzip -l "$work/artifacts/skill_lens_cli-<version>-py3-none-any.whl" \
     | grep registry/agents                           # must list all 10 agent TOMLs
   ```
4. Smoke-test the exact artifact a user would receive. For a version that ships
   the TUI, run the full three-lane qualification below instead of only this
   basic check:
   ```bash
   uv venv /tmp/skill-lens-smoke --python 3.13
   uv pip install --python /tmp/skill-lens-smoke "$work/artifacts/skill_lens_cli-<version>-py3-none-any.whl"
   /tmp/skill-lens-smoke/bin/skill-lens --version
   /tmp/skill-lens-smoke/bin/skill-lens --help
   ```
5. Publish — **only when you mean it** — using your own PyPI credentials:
   ```bash
   uv publish        # or: twine upload dist/*
   ```
6. Tag the release, so the version link at the foot of
   [`CHANGELOG.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/CHANGELOG.md)
   resolves instead of 404ing. The tag name is not free-form: it must be
   `v<version>` to match that link.
   ```bash
   git tag -a v0.2.0 -m "skill-lens 0.2.0"
   git push origin v0.2.0
   ```

> Publishing is irreversible: a version can be yanked on PyPI but never reused.
> The tag is created in step 6, **after** the upload, so it always points at a
> commit that was actually released.

### 0.2.0 candidate qualification (U9)

0.2.0 is **published** (2026-11-05, PyPI `skill-lens-cli` 0.2.0, tag `v0.2.0`).
The steps below produced and requalified the release build on macOS with Python
3.11.16; they are the checklist a reviewer re-runs for any future release
candidate. `$root` is this repository and `$work` is a fresh directory you own
outside it.

```bash
# 1. Clean source export: tracked files at the reviewed revision only.
mkdir -p "$work/src" "$work/artifacts"
git -C "$root" archive --format=tar HEAD | tar -x -C "$work/src"
rm -rf "$work/src/docs/validation/u9"        # sidecar evidence, never packaged
# Overlay exactly the reviewed tracked changes onto the export;
# qualify_candidate.py records the export manifest and the overlaid input
# hashes into candidate.json.

# 2. Source archive first, wheel built from that exact archive.
uv build "$work/src" --sdist --out-dir "$work/artifacts"
uv build "$work/artifacts/skill_lens_cli-0.2.0.tar.gz" --wheel --out-dir "$work/artifacts"
uvx twine check "$work/artifacts/skill_lens_cli-0.2.0-py3-none-any.whl" \
  "$work/artifacts/skill_lens_cli-0.2.0.tar.gz"

# 3. Archive checks plus three fresh installations, outside the checkout.
.venv/bin/python "$work/src/scripts/smoke_wheel.py" \
  --wheel "$work/artifacts/skill_lens_cli-0.2.0-py3-none-any.whl" \
  --sdist "$work/artifacts/skill_lens_cli-0.2.0.tar.gz" \
  --work-dir "$work/smoke" --receipt-out "$work/receipt.json"

# 4. Version probes for all three preserved lanes (base, min, latest).
#    The probes must execute each lane's own interpreter and console script
#    with that lane's directory as the working directory. Running a lane
#    interpreter with the repository as the working directory instead imports
#    skill_lens from the source tree and proves nothing about the install;
#    version_probes.py handles the lane cwd itself, from anywhere.
.venv/bin/python docs/validation/u9/implementation/version_probes.py \
  --smoke-dir "$work/smoke" --artifacts "$work/artifacts" \
  --out "$work/probes.json"
# asserts, per lane: importlib.metadata version == skill_lens.__version__ ==
# `skill-lens --version` == 0.2.0, and skill_lens.__file__ sits inside that
# lane's site-packages
```

The default `uv build` packages the whole working directory into the source
archive, including untracked junk, so **always build the export**, never the live
checkout. Each item below must be recorded with its actual output, not just
ticked:

- [ ] `pytest --cov=skill_lens`, `mypy`, `ruff check .` and
      `ruff format --check .` clean, with coverage ≥ 90% and `tui/` measured.
- [ ] Both source versions and the `uv.lock` root package read 0.2.0;
      `uv lock --check` passes; the lock diff changes only the root version.
- [ ] `twine check` PASS for both artifacts; metadata shows distribution
      `skill-lens-cli`, version 0.2.0, `Requires-Python >=3.11`, the optional
      Textual extra and the unchanged `skill-lens` console entry point.
- [ ] Archive contents: all 12 TUI modules, ten registry TOMLs and
      `skill_lens/py.typed`; the sdist-derived wheel matches the packaged source
      bytes; the source-archive list contains no unrelated files.
- [ ] Base lane: Textual absent; a bare **non-interactive** run prints help and
      exits 0 with no install tip, while an explicit `tui` exits 2 with the extra
      hint and no traceback. (The help-plus-tip fallback needs an interactive
      terminal, so check it in a pseudo-terminal, not a captured pipe.)
- [ ] Minimum (`textual==8.2.8`) and latest (unconstrained) lanes: the installed
      selections pass with a positive count and no unexpected skips, including
      the 17 CLI snapshots and 16 JSON goldens.
- [ ] Per-lane probes (each run from outside the checkout):
      `importlib.metadata.version`, `skill_lens.__version__` and
      `skill-lens --version` all report 0.2.0, and the imported
      `skill_lens.__file__` sits inside that lane's `site-packages`.
- [ ] Installed terminal smoke at 100×30 and 60×24: Home → Why → Diff → Agents →
      Compare → Doctor, Help, raw JSON, filters, back navigation, refresh and a
      normal quit; the cursor and the normal screen come back.
- [ ] SHA-256 hashes for both artifacts, the export manifest and every overlaid
      input, retained with the commands that produced them.

**Publication is a separate, explicit decision at every step.** A passing run
makes the candidate *locally verified*: *locally technically accepted*
additionally requires the two independent final reviews of the frozen plan, and
*publication ready* further requires hosted CI green on the candidate's own
commit and human visual approval of the interface. This ladder is exactly how
0.2.0 shipped on 2026-11-05 — reviews, then the owner's visual approval, then
CI green on the release commit, then the authorized upload, then the tag. The
checklist itself authorizes none of those. Any packaged source or document
change after
qualification invalidates the recorded hashes, so rebuild and repeat the affected
checks; keep the tag-after-successful-upload order from step 6 above.

### One thing that bites first-time maintainers

PyPI renders the README as the project page, but it does **not** resolve relative
links: `[LICENSE](./LICENSE)` works on GitHub and 404s on PyPI. Every link in
`README.md` must therefore be an absolute URL.
`tests/test_phase5_gate.py::test_readme_has_no_relative_links` enforces this.

Editing the README does not change an already-published page either — a new
version is required, because uploaded artifacts are immutable.
