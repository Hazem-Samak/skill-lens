# Developing Skill Lens

This file is for people **working on** Skill Lens. The user-facing overview is
[`README.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/README.md).

Maintainer material lives here rather than in the README because PyPI renders the
README as the project page: keeping the build diary and the release checklist out
of it leaves [pypi.org/project/skill-lens-cli](https://pypi.org/project/skill-lens-cli/)
readable for people who only want to install the tool.

## Build record

Early development. The specification lives in
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
- [ ] **Phase 7 (0.2) — interactive full-screen TUI** — *new scope, planned, not
  built.* An optional, additive, read-only browsing layer built on the existing
  frozen models, shipped as the opt-in `[tui]` extra so the base install gains
  nothing. Overturns the v1 "no full-screen TUI" rule for 0.2. The complete plan
  — vision, screens, phasing and gates — is
  [`FULL_SCREEN_TUI.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/FULL_SCREEN_TUI.md).
  The 2026-10-04 readiness review recorded two engine fixes required before
  Step 0: P1 (non-object settings robustness) and P2 (lock decoding robustness).
  Both have been implemented and verified with regression tests. P3 cost and
  capture-scope review measured full capture vs selective retention on synthetic
  fixtures (>600 skills), confirming the §21 Q9 full-capture contract is practical
  and retained. Assignment C1 implemented the pure byte/hash helpers,
  shared text parser, settings decoder, and identity helper, backed by
  `tests/test_snapshot_inputs.py`.
  Sections 21–22 define the exact Step 0 input types, engine signatures,
  capture algorithm, acceptance tests and ordered assignments for implementers
  (C1–C5). Bare launch requires both terminal input and output. Earlier review
  history is linked from the plan's short header.

Current gate: **491 tests pass** at **93% branch coverage** (93.18%), `mypy` strict clean,
`ruff check .` clean, `ruff format --check .` clean.

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
3. Build and inspect the artifacts:
   ```bash
   uv build --out-dir dist
   uvx twine check dist/*                    # metadata must PASS
   unzip -l dist/*.whl | grep registry/agents   # must list all 10 agent TOMLs
   ```
4. Smoke-test the exact artifact a user would receive:
   ```bash
   uv venv /tmp/skill-lens-smoke --python 3.13
   uv pip install --python /tmp/skill-lens-smoke dist/*.whl
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
   git tag -a v0.1.1 -m "skill-lens 0.1.1"
   git push origin v0.1.1
   ```

> Publishing is irreversible: a version can be yanked on PyPI but never reused.
> The tag is created in step 6, **after** the upload, so it always points at a
> commit that was actually released.

### One thing that bites first-time maintainers

PyPI renders the README as the project page, but it does **not** resolve relative
links: `[LICENSE](./LICENSE)` works on GitHub and 404s on PyPI. Every link in
`README.md` must therefore be an absolute URL.
`tests/test_phase5_gate.py::test_readme_has_no_relative_links` enforces this.

Editing the README does not change an already-published page either — a new
version is required, because uploaded artifacts are immutable.
