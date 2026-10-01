# Phase 5 Walkthrough — Packaging, CI & Release Readiness

> **Status:** Phase 5 is built and verified. The package builds, installs and runs.
> **Publishing to PyPI is deliberately NOT done** — the steps are documented and
> ready, but no upload has happened and the CI workflow cannot upload.
> **Audience:** the next AI agent (or human) touching `pyproject.toml`, the wheel
> contents, CI, or the release process.
> **Date:** 2026-10-01.

---

## 1. TL;DR for a non-programmer

Phase 5 is about turning the working tool into something you can **package and
ship**, not about adding features. Nothing in the engine changed.

Think of it like cooking a meal and then boxing it for delivery:

* The **wheel** is the sealed box a customer gets. I checked the box actually
  contains all the parts — the biggest risk was that the 10 agent recipe files
  (`.toml`) would be left out, which would make the tool crash on the user's
  machine. They are all in the box. ✅
* I proved the box works two ways: the customer's way (`pip install`) and the
  no-install trial way (`uvx --from . skill-lens --help`). Both fine. ✅
* I added an **automatic checking machine** (CI) that runs the tests and the
  linter every time code is pushed, on both macOS and Linux. ✅
* I added a small marker file so editors trust the tool's type hints. ✅
* I wrote down, step by step, how to publish later — but **did not publish**,
  because uploading is permanent and you asked to wait. ⏸️

---

## 2. What Phase 5 shipped

| Item | State |
| --- | --- |
| PEP 561 `py.typed` marker in `skill_lens/` | added — makes the `Typing :: Typed` classifier honest |
| `uv.lock` tracked in git | added (commit `d506ee4`) — reproducible, pinned installs |
| CI workflow `.github/workflows/ci.yml` | added — lint + format + tests, plus a packaging job |
| README release instructions | added — a manual, no-automation process |
| README Phase 5 status + CI badge | updated |
| `AGENTS.md` project record | links this file |
| **PyPI publish** | **NOT done — intentionally deferred** |

The console-script entrypoint (`skill-lens = skill_lens.cli:app`), the `hatchling`
build backend, the `pyproject.toml` metadata and the repo `AGENTS.md` already
existed before Phase 5; Phase 5 verified them rather than re-creating them.

---

## 3. How the packaging works (and why the registry files matter)

* Build backend is **hatchling**; `[tool.hatch.build.targets.wheel]` declares
  `packages = ["skill_lens"]`.
* hatchling includes **every file inside the declared package directory**, not
  just `.py` files. That is what carries `skill_lens/registry/agents/*.toml`
  into the wheel.
* The registry loader resolves its data directory **relative to the installed
  package**:

  ```python
  # skill_lens/registry/__init__.py
  REGISTRY_DIR = Path(__file__).parent / "agents"
  ```

  So if the `.toml` files were ever excluded from the wheel, `import skill_lens`
  would still succeed but `skill-lens scan` would fail at runtime. This is the
  single highest-risk packaging failure mode for this project — which is why CI
  asserts the wheel contains exactly **10** registry TOMLs.

**Proof (run locally during Phase 5):**

```
$ uv build --out-dir dist
Successfully built dist/skill_lens_cli-0.1.0.tar.gz
Successfully built dist/skill_lens_cli-0.1.0-py3-none-any.whl

$ unzip -l dist/*.whl | grep -c 'registry/agents/.*\.toml'
10

$ unzip -p dist/*.whl *_cli-0.1.0.dist-info/entry_points.txt
[console_scripts]
skill-lens = skill_lens.cli:app
```

The source distribution additionally carries `LICENSE`, `README.md`,
`pyproject.toml`, `AGENTS.md` and `SKILL_LENS_SPECIFICATION.md`.

---

## 4. The gate — how to verify Phase 5 yourself

Run these from the repository root. They must all pass.

```bash
# 1. Full test suite + linters (the repo gate)
uv run pytest                       # expect: 417 passed
uv run ruff check .                 # expect: All checks passed!
uv run ruff format --check .        # expect: 54 files already formatted

# 2. Build the artifacts
uv build --out-dir dist

# 3. The wheel must carry the agent registry (exactly 10)
unzip -l dist/*.whl | grep -c 'registry/agents/.*\.toml'   # expect: 10

# 4. Install exactly what a user receives, then run it
uv venv /tmp/skill-lens-smoke --python 3.13
uv pip install --python /tmp/skill-lens-smoke dist/*.whl
/tmp/skill-lens-smoke/bin/skill-lens --version             # expect: skill-lens 0.1.0
/tmp/skill-lens-smoke/bin/skill-lens --help                # expect: six commands listed

# 5. The "no install" trial path
uvx --from . skill-lens --help                             # expect: six commands listed
```

All five sections were run and passed during Phase 5. The smoke run also
executed `skill-lens doctor --json` against the throwaway environment and
produced valid JSON.

---

## 5. What CI does

File: `.github/workflows/ci.yml`. Two jobs:

1. **`test`** — a matrix of `ubuntu-latest` and `macos-latest` × Python
   `3.11`, `3.12`, `3.13`. Each job runs `uv sync --locked --extra dev`, then
   `ruff check .`, `ruff format --check .` and `pytest`. `--locked` makes CI fail
   if `uv.lock` is stale, so the locked install is enforced, not assumed.
2. **`packaging`** — builds the wheel and sdist, asserts the wheel carries 10
   registry TOMLs, then installs the wheel into a fresh environment and runs
   `skill-lens --version` and `--help`.

CI is **read-only with respect to publishing**: it has `permissions: contents:
read` and no publish/push step. A green CI run never releases anything.

> **Honest caveat (do not skip):** the local test suite has only ever been run on
> **macOS / Python 3.14**. The CI matrix is therefore the *first real run* on
> **Linux and on Python 3.11–3.13**. Tests were written to be OS-neutral (symlinks,
> `chmod 000`, path resolution via `paths.py`), but if the first CI run surfaces a
> Linux- or older-Python-specific failure, that is a genuine finding, not a flaky
> test — fix the code, do not loosen the test.

---

## 6. Decisions made in Phase 5 (and why)

* **Commit `uv.lock`.** This is an application/CLI, not a library. A lock file
  pins exact dependency versions so the tested environment and the user's install
  match. `uv lock --check` confirmed it was in sync before committing.
* **Add `py.typed` rather than drop the classifier.** The package already has
  thorough inline annotations; a marker file makes editors actually use them.
* **CI runs both macOS and Linux.** The spec declares both as supported v1
  platforms; testing only one would leave the other claim unverified.
* **Packaging is a separate CI job.** It is the one check that can silently rot
  if `pyproject.toml` or the package layout changes.
* **No PyPI upload.** Publishing is irreversible and requires the owner's
  credentials. The user explicitly chose "prepare, but don't publish."
* **No packaging test added to `pytest`.** Building a wheel inside the unit test
  suite is slow and environment-sensitive; the same assertion lives in the CI
  `packaging` job where a build is expected anyway.

---

## 7. Open items / next steps

| Item | Notes |
| --- | --- |
| **Publish to PyPI** | Deferred by request. Follow README → "Releasing". Needs `uv publish` (or `twine`) with the owner's credentials. The distribution name is `skill-lens-cli`; the command stays `skill-lens`. |
| **Version bump** | `0.1.0` in both `pyproject.toml` and `skill_lens/__init__.py`. Keep them in sync and refresh `uv.lock`. There is no CHANGELOG yet. |
| **First CI run** | Expect the Linux / 3.11–3.13 rows to be the first true cross-platform check. Review any failure as a real defect. |
| **`.gitignore`** | `dist/`, `build/`, `*.egg-info/` are already ignored, so local builds stay untracked. |

---

## 8. Files touched in Phase 5

| File | Change |
| --- | --- |
| `skill_lens/py.typed` | new — empty PEP 561 marker |
| `.github/workflows/ci.yml` | new — test matrix + packaging job |
| `README.md` | Phase 5 status, CI badge, "Releasing" section |
| `AGENTS.md` | project-record link to this file |
| `PHASE5_WALKTHROUGH.md` | new — this document |
| `uv.lock` | committed earlier as `d506ee4` |

No engine, command, model, render or fixture file was changed in Phase 5. The
417-test gate is unchanged by design.
