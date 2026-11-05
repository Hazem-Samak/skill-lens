# Changelog

All notable changes to Skill Lens are recorded here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Every **released** entry below was verified against the repository gate:
`pytest --cov=skill_lens`, `mypy`, `ruff check .` and `ruff format --check .`
all clean. Earlier unreleased work (including Stage H) records local-only
verification. The later CI repair was verified on all nine GitHub jobs; the
dated evidence below distinguishes those results from the historical records.

`[0.2.0]` below is the **published release**: PyPI `skill-lens-cli` 0.2.0
(with the optional `[tui]` extra), tagged `v0.2.0`, released 2026-11-05.

---

## [Unreleased]

Nothing newer than the 0.2.0 release entry is recorded yet. This section is
kept rather than deleted because the version gate
(`test_changelog_documents_the_current_version`) treats `[Unreleased]` as *not* a
released heading, so the next version needs a real section of its own.

---

## [0.2.0] — 2026-11-05

**Published 2026-11-05.** `skill-lens-cli` 0.2.0 is live on PyPI with the
optional `[tui]` extra and tagged `v0.2.0`. Publication followed the plan's
order: frozen plan → implementation → coordinator verification → two
independent final reviews (findings fixed and re-verified) → release wording
finalized → clean-export rebuild and full requalification → hosted CI green on
the release commit → upload → tag. Nothing about the six line-oriented
commands changed; the TUI is additive and opt-in.

Verified before upload (commands, hashes and logs under
[`docs/validation/u9/implementation/`](docs/validation/u9/implementation/)
for the first wave and
[`docs/validation/u9/coordinator/precommit/`](docs/validation/u9/coordinator/precommit/)
for the rebuilt waves — the supersession note names the live archive hashes
of the shipped 0.2.0):

- the four source gates (`pytest --cov=skill_lens`, `mypy`, `ruff check .`,
  `ruff format --check .`) on macOS / Python 3.11.16 / Textual 8.2.8;
- a wheel and a source archive built from a clean export of the reviewed sources,
  with recorded SHA-256 hashes and `twine check` metadata PASS;
- three fresh installations outside the checkout — a base install without
  Textual (CLI lifecycle fallback checks), plus `textual==8.2.8` and
  unconstrained-latest TUI installs that each ran the 14 installed selections
  (461 tests, zero skips), including the 17 CLI snapshots and 16 JSON goldens;
- an automated terminal smoke run of the installed candidate at 100×30 and 60×24.

Before publication the owner visually approved the running interface, and the
hosted CI matrix ran green on the release commit; receipts in
`docs/validation/u9/coordinator/`. Earlier green runs (including U8's packaging
job and this branch's baseline gates) proved their own commits, not this
release.

### Added

- **Optional full-screen TUI (major surface change).** `skill-lens` can now be
  opened once and navigated: Home, Why, Diff, Agents, Compare and Doctor screens,
  a raw JSON mode of every view, and a read-only Help overlay. It is *optional*,
  additive, strictly read-only and presentation-only — it reads the same frozen
  models the `--json` output is built from — and it ships as the opt-in `[tui]`
  extra over `textual>=8.2.8`, so the base install gains no new runtime
  dependency. All existing commands, flags, JSON shapes and exit codes are
  unchanged, and the line-oriented CLI remains the primary interface. Launch
  rules: bare `skill-lens` opens the TUI only when Textual is installed and both
  stdin and stdout are interactive; `--plain`, a non-interactive stream or a
  missing extra prints help instead and exits `0` — the install tip appears only
  when both streams are interactive and the extra is missing — and explicit
  `skill-lens tui` without the extra exits `2`. Screens stay on one captured
  session until a successful refresh; the default capture budget is 256 MiB
  (`--max-snapshot-bytes`, `0` disables it); a normal quit exits `0` and an
  accepted unexpected internal fault makes quit exit `3`. This overturns the v1
  "no full-screen TUI" rule for 0.2. Design: [`FULL_SCREEN_TUI.md`](./FULL_SCREEN_TUI.md).
  Implementation record: C1–C5 (byte/hash helpers, captured engine inputs,
  capture and cancellation, presentation extraction, Step 0 audit) and U1–U8 are
  complete. U5 (Diff and raw JSON) final local gate evidence recorded 1192
  passed, 1 skipped, 90.15% combined coverage — see
  [U5 acceptance](docs/validation/u5/acceptance.md). U6 and U7 carry local
  implementer evidence plus passing parent verification
  (`docs/validation/u6/coordinator/verification.md`,
  `docs/validation/u7/coordinator/verification.md`). U8's coordinator
  verification and both independent final reviews passed on 5 November 2026
  (`docs/validation/u8/coordinator/`). U9 prepared this candidate; its evidence
  is under [`docs/validation/u9/implementation/`](docs/validation/u9/implementation/)
  (first wave) and `docs/validation/u9/coordinator/precommit/` (rebuilt
  candidate; see the supersession note).

- **Help overlay, contextual keymap and empty-state polish (U8).** The
  TUI now has one read-only Help modal over Home, Why, Diff, Agents,
  Compare and Doctor, including raw JSON, initial-loading and no-session states.
  `?` opens it outside the Home filter input; the app-level priority `F1` toggles
  it even while typing. The body is scrollable, keeps the Close button visible,
  and names the keys that actually work for the current screen, mode and focus.
  It shows live session status, distinguishes an initial scan from a refresh with
  retained data, and keeps literal in-memory fault details visible. Opening Help
  starts no capture, report computation or filesystem discovery; covered Home,
  Why, Diff and Compare work is suspended through the existing exact-owner
  tokens and reconciled once on reveal. Diff and Compare gain bounded suspend and
  resume hooks; Agents and Doctor guard covered selection and deferred focus.
  Home's filter now explains that `Esc` clears a no-match filter. The README,
  DEVELOPMENT, specification, TUI design and this changelog describe the tested
  behavior; the six line-oriented commands remain primary. Local implementer
  evidence, mutation results and gates are under
  `docs/validation/u8/implementation/`. Coordinator technical verification passed
  and both independent final reviews passed with no blockers (ledger under
  `docs/validation/u8/coordinator/`); this is not a 0.2 release claim.

- **Why resolution screen (U4).** The TUI now provides a dedicated
  Why resolution screen accessible by pressing Enter on a focused Home skill row.
  Shows candidate collapsibles in resolution order, active agent switching strip,
  lookup details, and honest loading/refreshed states. See the
  [U4 walkthrough](docs/TUI_U4_WALKTHROUGH.md) and
  [local technical acceptance](docs/validation/u4/acceptance.md). Human visual
  approval and 0.2 publishing remain separate and are not claimed here.

- **Home browsing screen (U3).** The TUI now shows a skill table,
  scrollable metadata preview, text and agent filters, and optional per-agent
  resolution states. Selection, refresh and late worker results preserve the
  frozen session contract; browsing stays read-only. Local checks, a synthetic
  600-skill benchmark and six mutation checks were independently reviewed.
  See the [U3 walkthrough](docs/TUI_U3_WALKTHROUGH.md) and
  [acceptance record](docs/validation/u3/acceptance.md). Human visual approval
  and 0.2 publishing are separate; neither is claimed here.

- **Bounded TUI snapshot capture (R01).** The TUI now refuses to open a home
  whose captured skill payload exceeds a byte budget, instead of reading an
  unbounded amount of file content into memory. The total is measured before the
  capture phase reads any file and is enforced again against the bytes actually
  read, so a file that grows after the measurement cannot carry the capture past
  the limit. Only skill payload counts; captured configuration and
  lockfile bytes are accounted separately. The default budget is 256 MiB —
  headroom over the largest measured fixture (a 64 MiB payload whose transient
  refresh peak measured ~152 MiB). `skill-lens tui --max-snapshot-bytes <bytes>`
  overrides it and `0` disables the limit; a negative value is a usage error, and
  bare invocation uses the same default. A refusal is an expected condition: it
  keeps the previously published generation, leaves a normal quit at exit `0`,
  and never suggests a retry that cannot help. An accepted internal fault clears
  a standing refusal, so a fault is never masked by it. The line-oriented
  commands are unaffected by this policy and remain the fallback for any size. No
  temporary files, no disk cache and no truncation; a tree that cannot be read
  still raises `IncompleteTreeError`. Discovery parses each skill source document
  before the measurement, so that read is a recorded residual rather than a
  bounded one; see `FULL_SCREEN_TUI.md` §9.3. This supersedes the "no resource
  policy is approved or implemented" note in the Stage H section above. Policy:
  [`FULL_SCREEN_TUI.md`](./FULL_SCREEN_TUI.md) §9.3; plan:
  [`docs/plans/2026-10-16-snapshot-capture-budget.md`](./docs/plans/2026-10-16-snapshot-capture-budget.md).

### Fixed

- **Installed-lane receipts under-reported their test counts.** pytest appends an
  elapsed parenthetical to its summary line; the packaging harness's pattern did
  not allow for it, so a lane that really ran 451 tests was receipted as
  `test_count: 0`, and nothing failed. The pattern now accepts both forms, an
  unparsable summary raises instead of silently defaulting to zero, a lane with no
  passed tests is rejected, and the receipt records the summary line and duration.
  Each new guard is mutation-tested.

- **TUI Home could stay empty after its initial scan.** If the first capture
  finished before the Home screen finished mounting, the ready snapshot was
  published while the screen still treated itself as unmounted, and no later
  event repopulated the table. The post-mount update now runs after the screen
  has finished mounting. A regression test covers the early-completion ordering.

- **Codex configuration symlink loops on Python 3.13 and later.** Resolve
  existing configuration paths strictly before allowing missing paths. A
  circular shortcut is reported as unsupported instead of silently surviving
  non-strict path resolution. Missing paths retain their existing behavior.

- **Linux cancellation coverage.** Isolated the cancellation case that needs a
  case-insensitive filesystem and skip only that case when unavailable. The
  remaining capture-cancellation phases still run on Linux and macOS.

- **TUI quit checks and packaging diagnostics.** Two blocked-worker tests allow
  the screen to finish mounting before sending `q`, avoiding the observed
  Python 3.13 hang while retaining their quit watchdogs. Installed-wheel TUI
  checks now have a 300-second limit and include partial output on timeout.
  The repaired packaging job completed in 98 seconds. Diagnosis and limits:
  [overnight CI record](docs/validation/overnight/2026-10-24/ci/diagnosis.md).

- **The install instructions did not work on a stock Mac.** `pip install
  skill-lens-cli` was the only documented route, and it fails on a new Mac two
  different ways: Apple's built-in `python3` is 3.9, below the declared
  `requires-python = ">=3.11"`, so pip reports *"No matching distribution
  found"* — which reads as "this package does not exist" and sends the reader
  hunting for a publishing mistake. Installing into Homebrew's Python instead is
  refused by PEP 668 with `externally-managed-environment`. The install section
  now leads with `uv tool install` / `pipx install`, which carry their own
  interpreter, and explains both error messages in plain English, including the
  `python3 --version` check and a warning against `--break-system-packages`.
  Both routes were verified against real installs, and the README was rendered
  through PyPI's own `readme_renderer` to confirm the new `<details>` block and
  its page anchor survive there.

### Documentation and process records

Recorded because they are repo-visible work on this branch. They are
documentation and measurement changes only; none of them ships inside the wheel.

#### Workflow documentation

- Corrected T3 Nightly model readback, delegated worktree isolation, and launch
  request IDs against the installed API. Shared policy now routes explicitly to
  T3, Herdr, BB, and Rex without leaking one host's permission or lifecycle rules
  into another.
- Repaired Herdr status fields, parent report addresses, blocked-answer handling,
  existing-worker display, and per-terminal cleanup. Added native BB and Rex
  adapters covering explicit checkout selection, complete evidence, waits,
  messaging, optional workflow capabilities, and ownership-safe cleanup.

#### Development documentation and resource measurements (Stage H)

These are documentation and measurement repairs only — no product, test, CI,
dependency, snapshot or golden changes. Local verification and independent
review are recorded in the [Stage H acceptance record](docs/validation/assessment-repairs/h/acceptance.md).

- **README/DEVELOPMENT status reconciliation.** Published 0.1.1 (six CLI
  commands, no TUI extra) vs current development (six CLI commands plus C1–C5
  and U1–U2 TUI entrypoint/controller/skeleton; U3–U9 future work). Dated gate
  numbers linked instead of stale counters; historical measurements preserved.
- **FULL_SCREEN_TUI.md status header.** Reflects C1–C5 + U1–U2 as complete
  development work and U3–U9 as future work; operative contract and historical
  metrics preserved.
- **AGENTS.md architecture map/pointers.** Read-before-changing pointers updated
  to reference Stage H validation evidence.
- **Resource-risk measurement.** Byte-heavy capture/refresh benchmarks on
  synthetic fixtures (8 skills × 2 MiB, 8 × 8 MiB, one larger aggregate file,
  3 repeats each) with tracemalloc traced heap, retention and preservation
  reporting. See
  [`docs/validation/assessment-repairs/h/resource-risk.md`](./docs/validation/assessment-repairs/h/resource-risk.md)
  and [`benchmark_capture.py`](./docs/validation/assessment-repairs/h/benchmark_capture.py).
  No resource policy is approved or implemented; the snapshot remains
  unbounded by bytes.

[0.2.0]: https://github.com/Hazem-Samak/skill-lens/releases/tag/v0.2.0

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
> [`PHASE5_WALKTHROUGH.md`](./docs/archive/PHASE5_WALKTHROUGH.md).

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
