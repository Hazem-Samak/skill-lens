# Skill Lens

[![CI](https://github.com/Hazem-Samak/skill-lens/actions/workflows/ci.yml/badge.svg)](https://github.com/Hazem-Samak/skill-lens/actions/workflows/ci.yml)

> **Your AI skills, in one place. And why each one is there.**

Skill Lens is a local, read-only **diagnostics and resolution engine for AI agent
skills** (`SKILL.md` and file-based skills). It is the `which`, `brew doctor`,
and capability inspector for the skills scattered across your AI coding agents.

If you run more than one AI coding assistant — Codex, Claude Code, Antigravity,
Pi, Grok, Qoder, Windsurf, OpenCode, and others — your machine slowly fills with
skill folders, symlink farms, and shadowed copies. Skill Lens tells you what
exists, where it lives, and which copy actually wins.

```console
$ skill-lens scan

╭─────────────────────────── Skill Lens: Discovered Skills ───────────────────────────╮
│ Detected Agents: Codex, Claude Code, Antigravity, Pi, Grok, Qoder, Windsurf         │
│ Canonical Library: 83 skills (in ~/.agents/skills across 7 symlink farms)            │
│ Local Project Skills: 3  •  System/Bundled: 12  •  Plugin Skills: 600               │
╰─────────────────────────────────────────────────────────────────────────────────────╯
```

And when two copies of one skill have drifted apart, `diff` shows exactly how:

```console
$ skill-lens diff deploy

╭─────────────── Diff: 'deploy' ────────────────╮
│ Copies: 2                                     │
│ Baseline: ~/.claude/skills/deploy (Variant A) │
╰───────────────────────────────────────────────╯

= ~/.claude/skills/deploy [Variant A] (user, valid)  baseline (no diff shown)
  Reference copy; every diff below is against it.

* ~/.agents/skills/deploy [Variant B] (user, valid)  1 file(s) differ
  SKILL.md modified
--- SKILL.md
+++ SKILL.md
@@ -1,7 +1,7 @@
 ---
 name: deploy
-description: Personal deploy.
+description: Shared-library deploy.
```

## Why

Once you use several agents, three problems appear:

1. **Capability blindness** — *What skills exist, and which agents can see them?*
2. **Precedence confusion** — *Why is Claude running an old global copy while
   Codex warns its context is full?*
3. **Symlink & variant drift** — *Is this skill an identical shortcut to my
   shared library, or did someone edit a local copy?*

Skill Lens answers all three with deterministic, offline logic grounded in how
each agent actually resolves skills.

## Design principles

- **100% read-only.** Skill Lens never creates, edits, moves, or deletes
  anything. It only looks.
- **Offline & deterministic.** No AI calls, no telemetry, no network. Same input,
  same output.
- **Provenance over guesswork.** Every precedence rule is tagged
  `documented`, `empirical`, or `inferred`. When a behaviour is undocumented,
  Skill Lens says `ambiguous` instead of inventing an answer.
- **JSON first.** Every command supports `--json` for scripting and CI, with
  Rich formatting layered purely on top.

## Commands

| Command | Purpose |
| --- | --- |
| `skill-lens scan` | Inventory skills across detected agents, split by scope. |
| `skill-lens why <skill> --agent <id>` | Explain why a skill resolves the way it does. |
| `skill-lens agents` | List known agents, their collision policy and evidence. |
| `skill-lens diff <skill>` | Unified diff of diverging variants of one skill. |
| `skill-lens compare --agent A --agent B` | Compare two agents' capability surfaces: shared, diverged, or one-sided. |
| `skill-lens doctor` | Hygiene checks: broken links, bad frontmatter, budget warnings, permission blocks. |

All six commands are built and tested.

Every command accepts `--json`. `doctor` and `scan` also accept `--fail-on` to
gate a pipeline — see [Exit codes and CI use](#exit-codes-and-ci-use).

## Install

Requires **Python 3.11+** on **macOS or Linux** (Windows is out of scope for v1).

```bash
pip install skill-lens-cli
```

> **Package name note:** the command is `skill-lens` and the Python package is
> `skill_lens`; the distribution is published as `skill-lens-cli` because the
> bare `skill-lens` name was already taken on PyPI.

## Status

Early development. The specification lives in
[`SKILL_LENS_SPECIFICATION.md`](./SKILL_LENS_SPECIFICATION.md) and the build
proceeds by phase:

- [x] **Phase 0** — frozen models, lazy path resolution, 12 golden fixtures
- [x] **Phase 1** — metadata parser, streaming SHA-256 hasher, symlink canonicalization
- [x] **Phase 2** — registry loader, 3-axis resolver, `scan` / `why` / `agents` commands
  — ✅ **reviewed and corrected**: all 20 findings in
  [`PHASE2_FINDINGS.md`](./PHASE2_FINDINGS.md) (F-01 … F-20) are fixed and each is
  guarded by a regression test
- [x] **Phase 3** — Rich presentation layer and `diff` — unified diff between the
  differing variants of one name, pinned by a golden `diff_*.json` and plain-text
  render snapshots for `scan`, `why` and `diff` — ✅ **reviewed and corrected**: all 4
  findings in [`PHASE3_FINDINGS.md`](./PHASE3_FINDINGS.md) (D-01 … D-04) are fixed and
  each is guarded by a regression test
- [x] **Phase 4** — `doctor` hygiene checks, multi-agent `compare`, and the live
  discovery adapter — pinned by golden `doctor_*.json` / `compare_*.json` fixtures,
  render snapshots, and a live smoke test that runs with the sandbox off
  — ✅ **reviewed and corrected**: all 8 findings in
  [`PHASE4_FINDINGS.md`](./PHASE4_FINDINGS.md) (C-01 ... C-08) are fixed, three
  suggestions rejected with written reasons
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
  [`PHASE6_WALKTHROUGH.md`](./PHASE6_WALKTHROUGH.md)
  — **evidence integrity**: `dsh` and `omp` were the only agents with no source
  and entirely inferred rules. Both now cite their real vendor documentation —
  which revealed that `dsh` was **missing both user-level roots** and that `omp`'s
  managed-skills folder was ranked **above** the folders that should win. All 10
  agents now cite a source, and an enforced invariant guarantees it.

Current gate: **470 tests pass** at **93% branch coverage**, `mypy` strict clean,
`ruff check .` clean, `ruff format --check .` clean.

> The Phase 6 plan is [`PHASE6_PLAN.md`](./PHASE6_PLAN.md); what shipped and what
> was wrong along the way is in
> [`PHASE6_WALKTHROUGH.md`](./PHASE6_WALKTHROUGH.md).

## Exit codes and CI use

`doctor` and `scan` can fail a pipeline. By default they exit `0` exactly as they
always have — a report you read. Opt in with `--fail-on`:

```bash
skill-lens doctor --fail-on error      # exit 1 if any error-level finding
skill-lens scan   --fail-on warning    # exit 1 on any error or warning
```

| Code | Meaning |
| --- | --- |
| `0` | The command ran; nothing reached the threshold. |
| `1` | The command ran; findings reached the threshold. |
| `2` | Bad usage, unknown agent, or unreadable input. |

Two things worth knowing: the report is **always printed before** the non-zero
exit, so a gate never hides the evidence that tripped it; and `--fail-on info`
fails on essentially every machine, because `doctor` reports *normal* setups as
informational notes. Use `error` or `warning` for a gate. `why`, `diff`,
`compare` and `agents` have no `--fail-on` — a missing skill is an answer, not a
fault.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest                        # run the test suite
pytest --cov=skill_lens       # …with the coverage gate (fails under 90%)
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
   in [`CHANGELOG.md`](./CHANGELOG.md) under a released heading.
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
6. Tag the release, so the `[0.1.0]` link at the foot of
   [`CHANGELOG.md`](./CHANGELOG.md) resolves instead of 404ing. The tag name is
   not free-form: it must be `v<version>` to match that link.
   ```bash
   git tag -a v0.1.0 -m "skill-lens 0.1.0"
   git push origin v0.1.0
   ```

> Publishing is irreversible: a version can be yanked on PyPI but never reused.
> There is deliberately **no `v0.1.0` tag yet** — it is created in step 6, after
> the upload, so the tag always points at a commit that is actually released.

## License

[MIT](./LICENSE) © 2026 Hazem Samak
