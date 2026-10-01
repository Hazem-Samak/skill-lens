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

> **Resolved — was an honest caveat.** The local suite had only ever run on
> macOS / Python 3.14. The **first CI run failed on Python 3.11–3.13**, exposing
> two genuine cross-version bugs (real crashes, not flaky tests). They are fixed
> and the suite now passes on Python 3.11–3.14 — see **section 9**. The Linux and
> older-Python rows stay covered by CI on every push.

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
| ~~Version bump~~ | **Resolved.** `0.1.0` in both `pyproject.toml` and `skill_lens/__init__.py`. The manual "keep them in sync" step is now a test: `test_version_is_in_sync_between_pyproject_and_package` fails when the two disagree, and `test_changelog_documents_the_current_version` fails when a version is bumped without a matching `CHANGELOG.md` heading. `CHANGELOG.md` now exists. |
| ~~First CI run~~ | **Done — green.** It failed on Python 3.11–3.13 and the two root-cause defects are fixed (section 9). Two consecutive green runs since. |
| **Python 3.14 in CI** | **Resolved.** Added to the matrix after the suite was verified locally on 3.14.7 (417 passed). The `Programming Language :: Python :: 3.14` classifier was added to match, so PyPI's compatibility filter shows the package to 3.14 users. |
| **Phase 5 gate test** | **Resolved.** `tests/test_phase5_gate.py` (11 tests) pins the packaging *declarations* rather than building a wheel — see section 10. |
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

The engine, command, model, render and fixture files were unchanged by the
Phase 5 packaging work itself. The 417-test gate was unchanged by design — until
the first CI run, which forced the small engine fixes below.

---

## 9. Defect found by the first CI run (and fixed)

The first CI run (run #1, commit `385b0c4`) **failed**: the packaging job passed,
but the test jobs failed on Python 3.11 and 3.12. Reproducing locally on 3.11,
3.12 and 3.13 showed **12 failing tests**; Python 3.14 passed everything. The
cause was not the OS and not flaky tests — it was two real engine bugs, plus one
test that only passed because the local shell had colour off. All three were
invisible because development only ever ran on Python 3.14 at a plain terminal.

**Bug 1 — a symlink loop crashes output on Python ≤3.12.**
`Path.resolve()` raises `RuntimeError` (not `OSError`) for a symlink loop on
Python 3.11/3.12; Python 3.13+ changed it to stop at the loop instead. Both
`paths.display()` (used by `doctor`/`scan` when rendering paths) and
`discovery._is_symlinked_markdown()` caught only `OSError`, so a cyclic link
crashed the command. Fixed: a `_resolved()` helper in `paths.py` catches both,
and `_is_symlinked_markdown` catches both.

**Bug 2 — a permission-blocked directory crashes discovery on Python ≤3.13.**
On Python 3.11–3.13, `Path.is_file()`, `exists()` and `is_dir()` **re-raise**
`PermissionError` (EACCES) when a parent directory is unreadable; Python 3.14
swallows it and returns `False`. Three places assumed the 3.14 behaviour:
* `parser.find_skill_document()` probed `is_file()`/`is_dir()` unguarded, so a
  chmod-000 skill crashed parsing. Fixed: the probes are wrapped; a blocked
  entrypoint falls through to `is_unreadable_directory`, so the skill is
  reported `UNREADABLE` exactly as the spec intends.
* `discovery.discover()` probed `base.exists()`/`is_dir()` unguarded, so a root
  nested under a blocked parent (e.g. `~/.codex/skills/.system` under a blocked
  `~/.codex/skills`) crashed the walk. Fixed: the root probes are wrapped; the
  blocked parent is still recorded as an unreadable root.
* `discovery._directories_for_root()` had the same unguarded project-root probe;
  wrapped for the same reason.

**Bug 3 — a test asserted on colourised text (CI-only, nothing to do with the
engine).** `test_compare_requires_exactly_two_agents` checked that the CLI error
contains the literal `--agent`. On CI colour is forced (`FORCE_COLOR`), and Rich
renders the option name as `-` + an escape code + `-agent`, so the raw string
never contains `--agent`; it passed locally only because a plain terminal has no
colour. (Setting `NO_COLOR` was not enough — Rich still emits bold/dim codes.)
Fixed with a `_PlainRunner` subclass in `tests/test_cli.py` that strips ANSI
escapes from captured stdout/stderr, so every assertion in that file is about the
text and never the colouring. No production code changed.

**Why it matters.** Specification section 4 requires cycles and blocked roots to
be *reported without crashing or hanging*. Before this fix that guarantee held
only on the newest Python; now it holds on every supported version.

**Verification.** The full suite was run locally on Python 3.11, 3.12, 3.13 and
3.14 — **417 passed on each**, and again with `FORCE_COLOR=1` set to mimic CI.
`ruff check .` and `ruff format --check .` clean. No test was weakened; the
production code was made version-independent, and the one fragile assertion was
made colour-independent.

**Files changed:** `skill_lens/core/paths.py`, `skill_lens/core/parser.py`,
`skill_lens/core/discovery.py`, `tests/test_cli.py`.

**Lesson for future agents (keep this habit):** when a supported Python range is
part of the contract, run the suite on the *oldest* supported version before
believing a green local run. 3.14 hid real breakage on 3.11–3.13. Equally, run it
once with `FORCE_COLOR=1`: a test that reads rendered output must not depend on
the host shell's colour setting.

---

## 10. Post-release hardening: the Phase 5 gate test

Section 6 recorded a deliberate decision: *"No packaging test added to `pytest`,
because building a wheel inside the unit test suite is slow and
environment-sensitive."* That reasoning still holds, and this gate does **not**
build a wheel.

What it does instead is pin the **declarations that determine what the wheel
contains**, which is fast, deterministic, and catches the failure this project
cares most about — the agent registry silently dropping out of the distribution —
in under 0.05 seconds, on a developer's machine, with no build step and no
network.

The eleven assertions are all **drift guards**: each compares two sources of truth
that can silently get out of step.

| Assertion | Catches |
| --- | --- |
| version in `pyproject.toml` == `skill_lens.__version__` | an artifact whose `--version` disagrees with its own filename |
| `CHANGELOG.md` has a released heading for the current version | a bump that skips the changelog |
| `skill-lens` maps to an importable `skill_lens.cli:app` | an entrypoint pointing at a renamed module |
| all six spec commands are registered | a command silently dropped from `cli.py` |
| build backend is hatchling, wheel target is `["skill_lens"]` | a narrowed package list that would exclude the `.toml` files |
| `REGISTRY_DIR` resolves *inside* the installed package | the loader becoming cwd-relative, which would leave every installed user with an empty registry |
| exactly 10 registry TOMLs, all loadable | an agent added or removed without updating `EXPECTED_AGENT_COUNT` and the CI packaging job together |
| every CI matrix version is within `requires-python` | testing an interpreter the package does not claim to support |
| CI covers both macOS and Linux | silently dropping a claimed platform |
| CI contains no publish step and keeps `contents: read` | an upload slipping into an automated workflow — publishing must stay a human decision |
| `py.typed` ships and `Typing :: Typed` is claimed | a classifier that is honest in name only |

**Verified to have teeth.** Each guard was mutation-tested: bumping only the
`pyproject.toml` version, appending a `uv publish` step to CI, adding an
unsupported `3.9` to the matrix, and deleting `py.typed` each produced exactly
one failure, and the suite returned to 11 passed after restoring each. A test
that cannot fail is worse than no test, so this was checked rather than assumed.

The end-to-end check that a wheel really does carry the registry remains the CI
`packaging` job, which builds and installs for real.

---
