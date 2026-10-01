# Changelog

All notable changes to Skill Lens are recorded here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Every entry below was verified against the repository gate: `pytest --cov=skill_lens`,
`mypy`, `ruff check .` and `ruff format --check .` all clean, plus a green CI run on
macOS and Linux.

---

## [0.1.1] — 2026-10-01

A documentation and packaging fix. No behaviour changed: no command, exit code or
output differs from 0.1.0.

### Fixed

- **Eleven dead links on the PyPI project page.** PyPI renders `README.md` as the
  project description but does not resolve relative links, so every
  `[LICENSE](./LICENSE)`-style target pointed at pypi.org and 404'd. All README
  links are now absolute URLs to this repository, and
  `test_readme_has_no_relative_links` fails if a relative one is reintroduced.
  (An HTTP-status check cannot catch this class of bug: PyPI answers *every*
  unknown path with the same page, so the dead links report `200`.)

### Changed

- **The README is now user-facing.** The six-phase build diary and the release
  checklist moved to [`DEVELOPMENT.md`](./DEVELOPMENT.md), which the README links
  to. Someone arriving from PyPI now sees what the tool is, how to install it and
  how to use it, without the maintainer notes in between.

[0.1.1]: https://github.com/Hazem-Samak/skill-lens/releases/tag/v0.1.1

## [0.1.0] — 2026-10-01

First release. A local, strictly read-only diagnostics and resolution engine for AI
agent skills (`SKILL.md`), shipped as the `skill-lens` command.

> **Published to PyPI on 2026-10-01** as `skill-lens-cli` 0.1.0, and tagged
> `v0.1.0`. Phase 6 (below) is part of what `0.1.0` contains rather than a change
> after it. Publishing remains deliberately manual — see
> [`PHASE5_WALKTHROUGH.md`](./PHASE5_WALKTHROUGH.md).

### Added

- **Exit-code contract.** `skill-lens doctor` and `skill-lens scan` can now gate
  a pipeline. `0` means the command ran with nothing over the threshold, `1`
  means findings reached it, `2` means the command could not run (bad usage,
  unknown agent), and `3` is reserved for an unexpected internal fault.
- **`--fail-on {never,error,warning,info}`** on `doctor` and `scan`. The default
  is `never`, so every `0.1.0` exit status is unchanged. The report is always
  printed before a non-zero exit, so a gate never hides its own evidence.
- **Registry evidence invariant.** No agent may claim `documented` or
  `empirical` evidence without a citable `source` URL, and no root may claim
  `documented` evidence without one. Previously this was a convention with
  nothing enforcing it.
- **A self-audit check in `doctor`** that reports agents whose precedence had to
  be inferred, so the tool states its own limits instead of only the user's.
  Informational severity; silent with the registry as shipped.

### Fixed

- **`dsh` was missing both user-level skill roots.** Its registry entry knew only
  the two project roots and a plugin root, so Skill Lens could not see
  `~/.dsh/skills` or `~/.agents/skills` — where a real dsh user's skills actually
  live. Both are now declared, in the order the vendor documentation specifies.
- **`omp`'s managed-skills folder was ranked above the folders that should win.**
  The vendor documents the `omp-managed` provider at priority 5 of 9, always
  deferring to an authored skill; the registry ranked it at 70, claiming the
  opposite.
- **dsh's documented rank direction is inverted relative to Skill Lens.** The
  upstream numbers are now translated rather than copied, with the translation
  recorded in the registry file and asserted by a test.

### Changed

- `dsh` and `omp` are no longer entirely `inferred`. Both now cite primary
  vendor documentation, taking the registry to 10 of 10 agents with a source.
- `omp` deliberately keeps `coexist_policy = "ambiguous"` even though its
  collision behaviour is now documented. Neither `shadow` nor `merge` can
  express namespaced coexistence, and both would emit a false statement;
  under-claiming is the correct direction of error. See the walkthrough.
- Dropped the legacy `License :: OSI Approved :: MIT License` classifier. The
  SPDX `license = "MIT"` expression is authoritative under PEP 639, and shipping
  both left the metadata self-contradictory. `twine check` still passes.

### Verification hardening (post-Phase 6)

The release gate now checks two properties it previously only asserted in prose.

- **Strict type checking.** `mypy --strict` runs over `skill_lens/` in CI, with
  `types-PyYAML` supplying the one missing stub. The `py.typed` marker and the
  `Typing :: Typed` classifier already shipped; a strict checker is what makes
  that promise verifiable rather than decorative. It surfaced exactly two
  findings, both fixed: an unparameterised `dict` in the registry loader, and a
  presentation-layer import that reached through `core.resolver` for a model it
  should have taken from `models.resolution`.
- **A coverage gate.** `pytest --cov=skill_lens` now fails below 90% branch
  coverage; the suite currently measures **93%**. The threshold lives in
  `[tool.coverage.report]` and the type-check scope in `[tool.mypy]`, so CI
  enforces exactly what a local run does.
- **Drift guards for both.** Five assertions in `tests/test_phase5_gate.py` pin
  the dev-dependency list, the mypy scope, the coverage threshold, and that CI
  actually invokes both. Each was mutation-tested: breaking the declaration
  produces exactly one failure.

### Known limitations

- Namespaced coexistence — a losing variant that survives under
  `<namespace>/<name>` — is not modelled. `omp` under-claims as a result.
- `--fail-on info` fails on essentially any machine, because `doctor` reports
  normal setups as informational notes. Use `error` or `warning` for a gate.

### Also in this release (Phases 0–5)

The engine itself:
- **`scan`** — inventory of every skill visible to an agent, grouped by canonical
  library versus entrypoint, with status labels (`ACTIVE`, `COEXISTS`, `SHADOWED`,
  `DISABLED`, `INVALID`, `AMBIGUOUS`, `UNREADABLE`, `UNSEARCHED`).
- **`why <skill> --agent <agent>`** — explains, axis by axis, why a given agent
  resolves a given skill to the copy it picked. Every reason carries a stable
  `rule_id` and an evidence level.
- **`diff`** — unified diff between every copy of one skill, with truncation that
  is honest about what it dropped.
- **`agents`** — the agent registry table: collision policy, evidence kind, and
  how many roots each agent declares.
- **`doctor`** — hygiene checks: broken symlinks, unreadable (TCC-blocked)
  directories, malformed frontmatter, and the Codex context-budget check.
- **`compare --agent A --agent B`** — pairwise capability comparison between two
  agents, including the skills only one of them can see.
- **Three-axis resolver** — agent, location rank, and variant identity resolved
  independently, then reconciled.
- **Agent registry** — 10 agent definitions as TOML with per-rule provenance
  (`documented`, `empirical`, `inferred`). Rules without evidence are reported as
  `ambiguous` or `unverified` rather than guessed.
- **`--json` on every command** — stable, sorted-key, machine-readable output. The
  presentation layer is strictly downstream of the data.
- **Golden fixtures** — 16 hand-written scenarios pinning behaviour (the spec's 12
  core scenarios plus the Phase 3 and Phase 4 additions), plus 17 plain-text
  render snapshots.
- **Packaging** — `skill-lens` console script, `py.typed` marker, tracked
  `uv.lock`, and a CI job that asserts the wheel carries all 10 registry files.

### Fixed (engine, Phases 0–5)

- A symlink cycle no longer crashes `scan` or `doctor` on Python 3.11–3.12,
  where `Path.resolve()` raises `RuntimeError` rather than `OSError`.
- A permission-blocked directory is now reported as `unreadable` on Python
  3.11–3.13 instead of crashing discovery — those versions re-raise
  `PermissionError` from `is_file()`/`is_dir()` where 3.14 returns `False`.
- CLI test assertions strip ANSI escapes, so they no longer depend on whether
  the host terminal happens to be colourised.

### Known limitations (engine, Phases 0–5)

- macOS and Linux only. Windows is out of scope for v1.
- Live discovery is advisory. Where an agent's real precedence behaviour is not
  documented, Skill Lens says `inferred` or `unverified` instead of guessing.
  *(Closed for the two agents that were uncited in Phase 6; all 10 agents now
  cite a primary source.)*

[0.1.0]: https://github.com/Hazem-Samak/skill-lens/releases/tag/v0.1.0
