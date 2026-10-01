# Changelog

All notable changes to Skill Lens are recorded here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Every entry below was verified against the repository gate: `pytest`, `ruff check .`
and `ruff format --check .` all clean, plus a green CI run on macOS and Linux.

---

## [0.1.0] — 2026-10-01

First release. A local, strictly read-only diagnostics and resolution engine for AI
agent skills (`SKILL.md`), shipped as the `skill-lens` command.

### Added

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

### Fixed

- A symlink cycle no longer crashes `scan` or `doctor` on Python 3.11–3.12,
  where `Path.resolve()` raises `RuntimeError` rather than `OSError`.
- A permission-blocked directory is now reported as `unreadable` on Python
  3.11–3.13 instead of crashing discovery — those versions re-raise
  `PermissionError` from `is_file()`/`is_dir()` where 3.14 returns `False`.
- CLI test assertions strip ANSI escapes, so they no longer depend on whether
  the host terminal happens to be colourised.

### Known limitations

- macOS and Linux only. Windows is out of scope for v1.
- Live discovery is advisory. Where an agent's real precedence behaviour is not
  documented, Skill Lens says `inferred` or `unverified` instead of guessing.
- Exit status does not yet encode findings, so the tool reports but cannot gate
  a CI pipeline.

[0.1.0]: https://github.com/Hazem-Samak/skill-lens/releases/tag/v0.1.0
