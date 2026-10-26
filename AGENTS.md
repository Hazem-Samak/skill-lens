# AGENTS.md — Guardrails for AI Coding Assistants

> **Before any non-trivial change:** read `docs/process/planning-loop.md` and freeze a plan in
> `docs/plans/`. Do not write code until it is committed. Then follow
> `docs/process/implementation-loop.md`.
>
> **The user names the roster:** provider, model, and effort for every role (coordinator,
> implementer, reviewers) are selected by the user per mission. If a roster entry is missing,
> ask once — never default, infer, or substitute (`docs/process/council.md` §1; on the OMP
> surface, `docs/process/omp/README.md`).

Welcome, AI agent. You are pair-programming on **Skill Lens**, a local diagnostics and resolution CLI tool for AI agent capabilities (`SKILL.md`).

This project is built with AI coding assistants under a strict specification. Your job is to be disciplined, reliable, and strictly follow the specification in `SKILL_LENS_SPECIFICATION.md`.

---

## 0. Communication Rules (READ FIRST)

- **Explain everything in plain, simple English.** This project is built with AI assistants and read by people skimming the repo; assume no prior context.
- **No unexplained jargon.** If a technical term is unavoidable, define it in one short sentence the first time you use it.
- **Lead with the outcome, not the mechanics.** Say what changed and why it matters to the user before listing files or code details.
- **Use everyday analogies** for technical concepts (e.g. "a symlink is like a shortcut icon").
- **When reporting a task:** what I did, why it helps, whether it works, and what (if anything) you need from the developer — in that order, in short bullets.
- **When something breaks:** explain it in one plain sentence, then the fix, then confirm it is resolved. Never dump a raw stack trace without a plain-English translation.
- **Ask before assuming.** If a decision affects behaviour or the user's machine, ask in plain language rather than guessing.
- **No walls of text.** Prefer short paragraphs and tight bullet lists over long technical essays.

---

## 1. Absolute Golden Rules

1. **Strictly Read-Only Target Execution:**
   - Skill Lens never writes, modifies, moves, or deletes user skills on their machine. It is 100% read-only.
2. **Never Touch Real `$HOME` in Tests:**
   - All tests must use `tmp_path` fixtures and monkeypatched `HOME` via `skill_lens/core/paths.py`.
   - Never run tests against live `~/.claude`, `~/.agents`, or `~/.codex`.
3. **No Lazy Module-Level Path Expansion:**
   - Do NOT write `DEFAULT_DIR = Path("~/.claude").expanduser()` at the module top level. It will evaluate at import time and bypass test monkeypatching. Always resolve paths inside functions via `paths.py`.
4. **Machine-Readable JSON First:**
   - All core features must output valid dataclasses and JSON models. Rich formatting is strictly a presentation layer on top of the data.
5. **No System Bloat or Creep:**
   - The line-oriented CLI is the **primary** interface. From
     **0.2**, an *additive, optional* full-screen TUI (Textual) is allowed as a
     browsing layer, shipped as the optional `[tui]` extra; it stays strictly
     read-only and presentation-only. See [`FULL_SCREEN_TUI.md`](./FULL_SCREEN_TUI.md).
     Before 0.2, line-oriented CLI only. From 0.2, bare `skill-lens` opens the
     TUI when Textual is installed and both stdin and stdout are interactive
     (terminal input and output); `--plain`, either stream being non-interactive,
     or missing Textual prints help instead.
   - NO SQLite or databases in v1.
   - NO AI API calls or telemetry.
   - NO Windows support in v1. macOS and Linux only.
6. **Provenance Over Hallucination:**
   - Never invent or guess an agent's collision or precedence behavior. Every rule in `registry/agents/*.toml` must declare its evidence kind (`documented`, `empirical`, `inferred`). If undocumented, emit `ambiguous` or `unverified`.

---

## 2. Test & Verification Protocol

- **Linter & Formatter:** `ruff check .` and `ruff format .`
- **Type Checker:** `mypy` (strict, scoped to `skill_lens/` via `[tool.mypy]`)
- **Test Runner:** `pytest`
- **Coverage Gate:** `pytest --cov=skill_lens` (threshold in `[tool.coverage.report]`)
- Before finishing any task, run:
  ```bash
  pytest --cov=skill_lens
  mypy
  ruff check .
  ruff format --check .
  ```
- **Snapshot tests:** the terminal output of `scan`, `why` and `diff` is pinned as
  plain text under `tests/fixtures/snapshots/`. A snapshot failure means the
  rendering changed: read the difference first, then regenerate with
  `pytest tests/test_render_snapshots.py --update-snapshots`. Never regenerate
  without reviewing what changed.
- Commit only when all tests pass cleanly.

---

## 3. Architecture Overview

```text
skill_lens/
├── __init__.py
├── cli.py                  # Typer commands (scan, why, agents, diff, doctor, compare)
├── render.py               # All Rich layout (scan, why, diff, agents, doctor, compare)
├── models/                 # Frozen dataclasses (SkillInstallation, DiffReport, ...)
├── core/
│   ├── paths.py            # Lazy environment & path resolution
│   ├── parser.py           # Frontmatter extraction & symlink canonicalization
│   ├── hasher.py           # Streaming SHA-256 fingerprint (newline-normalised)
│   ├── discovery.py        # Agent-agnostic entrypoint discovery + variant labels
│   ├── resolver.py         # 3-axis resolution engine
│   ├── scanner.py          # Inventory view over one discovery pass
│   ├── diff.py             # Unified diff computation (pure; no Rich)
│   ├── doctor.py           # Phase 4: diagnostics & hygiene checks
│   ├── compare.py          # Phase 4: pairwise capability comparison (pure; no Rich)
│   ├── config.py           # Resolved agent controls and config-path collection
│   ├── health.py           # Health checks
│   ├── system.py           # Phase 4: TCC-resilient live discovery adapter
│   ├── exitcodes.py        # Phase 6: exit-code contract + --fail-on policy (pure; no Typer/Rich)
│   ├── cancellation.py     # Cancellation exception and checkpoint helper (Assignment C3)
│   ├── snapshot_models.py  # Captured input and session dataclasses (Assignment C2)
│   └── snapshot.py         # Capture, validation and report services (Assignment C3)
├── presentation/           # Shared plain-text/heading parts (Assignment C4)
│   ├── __init__.py
│   ├── state.py
│   └── text.py
├── tui/                    # Optional Textual-free SessionController + Textual app (U1-U2)
│   ├── __init__.py
│   ├── app.py
│   ├── session.py
│   └── _textual_compat.py
└── registry/
    ├── loader.py           # TOML agent-definition loader
    └── agents/             # Agent definition TOML files (codex.toml, claude.toml, ...)
```

---

## 4. Project record (read before changing a finished phase)

Each reviewed phase keeps its findings as a permanent record, including the code
that was wrong and why. Read the relevant one before touching that area — the
rules in them were paid for:

- [`DEVELOPMENT.md`](./DEVELOPMENT.md) — the contributor entry point: the build
  record, the verification gate, how snapshots and goldens are regenerated, and
  the release steps. It also explains why `README.md` must link with absolute
  URLs only — PyPI renders the README as the project page and cannot resolve
  relative links, so a `./FILE.md` target 404s there.
- [`PHASE2_FINDINGS.md`](./docs/archive/PHASE2_FINDINGS.md) — 20 findings (F-01 … F-20) in the
  registry, discovery and resolver. Load-bearing for anything touching precedence,
  variant labels or canonical paths.
- [`PHASE3_FINDINGS.md`](./docs/archive/PHASE3_FINDINGS.md) — 4 findings (D-01 … D-04) in the
  `diff` truncation and presentation layer, plus the test gaps that let them
  through.
- [`PHASE4_FINDINGS.md`](./docs/archive/PHASE4_FINDINGS.md) — 8 findings (C-01 ... C-08) in the
  `doctor` / `compare` engines and the golden-file harness, plus the review
  suggestions deliberately not adopted and why.
- [`PHASE6_PLAN.md`](./docs/archive/PHASE6_PLAN.md) — the Phase 6 plan: the exit-code
  contract, `--fail-on`, and the evidence-integrity work. Phase 6 is *new scope*
  added after 0.1.0, not part of the original roadmap.
- [`PHASE6_WALKTHROUGH.md`](./docs/archive/PHASE6_WALKTHROUGH.md) — what Phase 6 shipped: the
  two registry defects found by reading vendor docs, the mutation results, and
  the mistakes made. Read it before changing `core/exitcodes.py`, adding a
  `--fail-on`, or editing an agent's `evidence` / `source` fields.
- [`PHASE5_WALKTHROUGH.md`](./docs/archive/PHASE5_WALKTHROUGH.md) — **historical**
  (pre-Stage G): the packaging and release walkthrough — what shipped in the
  wheel, the CI gate, and the deliberate decision to defer publishing. Section 10
  covers the Phase 5 gate test. Read it before changing `pyproject.toml`, the
  contents of the wheel, or the release steps. For current packaging and
  fault-adapter gates, see Stage G acceptance under
  [`docs/validation/assessment-repairs/g/acceptance.md`](docs/validation/assessment-repairs/g/acceptance.md).
- [`docs/validation/assessment-repairs/h/resource-risk.md`](./docs/validation/assessment-repairs/h/resource-risk.md)
  — Stage H resource-risk measurement: byte-heavy capture/refresh benchmarks on
  synthetic fixtures, measured results, limitations, and explicit (not
  implemented) resource-policy choices. Read before touching snapshot capture
  behavior or imposing any memory bound.
- [`FULL_SCREEN_TUI.md`](./FULL_SCREEN_TUI.md) §21–22 — read-before-changing
  contract for the snapshot service (`core/snapshot.py`), presentation layer
  (`presentation/`), and TUI controller/skeleton (`tui/`): Step 0 input types,
  engine signatures, capture algorithm, and the ordered C1–C5 / U1–U2
  assignments.

They were produced by independent read-only review delegated to other models
(Phase 4 by two axes: one reviewer per repo standards, one per specification),
then reproduced and fixed by the orchestrator. Two habits came out of them and
should be kept: **reproduce a reported defect before believing it** (a false
alarm costs as much as a miss), and **never regenerate a snapshot or golden
without reading the diff** — pinned output proves the output did not change,
not that it was right.

A third habit came from the first CI run: **a test that cannot fail is worse than
no test.** `tests/test_phase5_gate.py` and `tests/test_phase6_gate.py` were
mutation-tested — each guard was deliberately broken to confirm it fails. Do the
same for any new gate. Two of the ten Phase 6 mutations *survived* and exposed a
real hole (a scan test that only ever scanned a clean sandbox) and a piece of
dead code, so the habit earns its keep.
