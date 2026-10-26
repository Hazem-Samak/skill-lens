# Project Profile — Skill Lens

**What this is.** The rules that decide what "correct" means in this repository. Read
it before writing a plan or a review. It repeats `AGENTS.md` on purpose: a critic
dispatched in a fresh context must be able to find the rules without guessing.

This file is project truth and does not change when the machine does. Live machine
facts live in `machine-profile.md`.

---

## 1. What the project is

A Python CLI that inspects AI agent skill files (`SKILL.md`) on this machine and
reports what each agent would actually load. Read-only by design.

```
skill_lens/            the package
├── cli.py             Typer commands: scan, why, agents, diff, doctor, compare
├── render.py          all Rich output — presentation only
├── models/            frozen dataclasses
├── core/              engines: paths, parser, hasher, discovery, resolver,
│                      scanner, diff, doctor, compare, system, exitcodes
└── registry/agents/   10 agent TOML files (claude, codex, opencode, pi, …)
```

Source of truth for behaviour: `SKILL_LENS_SPECIFICATION.md`.
The TUI layer is specified in `FULL_SCREEN_TUI.md`. Neither is rewritten by this
process.

---

## 2. The four gates

Run all four before finishing any task. They are the acceptance check for every plan.

```bash
cd "/Users/corvette/Documents/Projects Coding/Skill Lens"
pytest --cov=skill_lens
mypy
ruff check .
ruff format --check .
```

| Gate | Configured in | Fails when |
|---|---|---|
| `pytest --cov=skill_lens` | `[tool.coverage.report] fail_under = 90` | coverage under **90.0%** |
| `mypy` | `[tool.mypy]` — `strict = true`, `files = ["skill_lens"]` | any type error in `skill_lens/` |
| `ruff check .` | `[tool.ruff.lint]` — `E,F,I,UP,B,SIM`, line length 100 | any lint error |
| `ruff format --check .` | `[tool.ruff]` | any file not formatted |

A green gate claim is not evidence. **Run the gates.**

### Every new gate must be mutation-tested

A test that cannot fail is worse than no test. For any new guard, test, or coverage
threshold you add:

1. Deliberately break the thing it protects.
2. Confirm the test **fails**.
3. Restore the break.
4. Confirm it passes again.

Record which mutations survived. Two of the ten Phase 6 mutations survived and exposed
a real hole and a piece of dead code — the habit earns its keep.

---

## 3. The product guarantee: read-only

**Skill Lens never writes, modifies, moves or deletes anything on the user's machine.**
No exceptions, no "just this one" flags. This is promise number one to users.

Anything that would break it — a cache write, a fix command, a cleanup, a migration —
is out of scope unless the user explicitly approved it.

### Tests never touch the real `$HOME`

- Use the `tmp_path` fixture and monkeypatch `HOME` through `skill_lens/core/paths.py`.
- Never run a test against the live `~/.claude`, `~/.agents` or `~/.codex`.
- Concurrent tests must not share output files.

### No module-level path expansion

```python
# WRONG — evaluated at import time, before the test can patch it
DEFAULT_DIR = Path("~/.claude").expanduser()
```

```python
# RIGHT — resolved inside a function, every call
def default_dir() -> Path:
    return Path(os.environ["HOME"]) / ".claude"
```

A path baked in at import time silently defeats every test that relies on `HOME`
patching, and those tests then read the user's real skills.

### JSON and dataclasses first, Rich second

Every core feature returns valid dataclasses and JSON models. `render.py` is a
presentation layer on top. Engines (`diff.py`, `compare.py`, `exitcodes.py`) must stay
pure — no Rich, no Typer. If logic can only be checked by reading coloured output, it
is in the wrong place.

### Bloat rules

No database. No AI API calls. No telemetry. No Windows in v1. The line-oriented CLI is
the primary interface; the Textual TUI is an optional `[tui]` extra and stays
presentation-only.

---

## 4. Provenance over hallucination

**Never invent an agent's collision or precedence behaviour.**

Every rule in `skill_lens/registry/agents/*.toml` declares its evidence kind:
`documented`, `empirical`, or `inferred`. If the behaviour is not documented, emit
`ambiguous` or `unverified` — do not fill the gap with a plausible guess.

A guess here produces wrong output for the user with total confidence, and nothing in
the test suite can catch it. Cite the vendor document or label the rule.

---

## 5. Read `AGENTS.md` §4 before changing a finished phase

Those files record defects that were already found and fixed. Skipping them is the
cheapest way to reintroduce a bug someone already paid for.

| File | Read it before touching |
|---|---|
| [`DEVELOPMENT.md`](../../../DEVELOPMENT.md) | build record, the verification gate, snapshot/golden regeneration, the release steps. Also: `README.md` links must be absolute URLs, because PyPI renders the README as the project page and `./FILE.md` 404s there. |
| [`PHASE2_FINDINGS.md`](../../archive/PHASE2_FINDINGS.md) | precedence, variant labels, canonical paths, registry, discovery, resolver |
| [`PHASE3_FINDINGS.md`](../../archive/PHASE3_FINDINGS.md) | `diff` truncation, the presentation layer |
| [`PHASE4_FINDINGS.md`](../../archive/PHASE4_FINDINGS.md) | `doctor`, `compare`, the golden-file harness |
| [`PHASE6_PLAN.md`](../../archive/PHASE6_PLAN.md) | the exit-code contract, `--fail-on`, evidence integrity |
| [`PHASE6_WALKTHROUGH.md`](../../archive/PHASE6_WALKTHROUGH.md) | `core/exitcodes.py`, adding a `--fail-on`, editing any agent's `evidence` / `source` fields |
| [`PHASE5_WALKTHROUGH.md`](../../archive/PHASE5_WALKTHROUGH.md) | `pyproject.toml`, wheel contents, the release steps |

Two habits came out of those reviews and are not optional:

- **Reproduce a reported defect before believing it.** A false alarm costs as much as
  a miss.
- **Never regenerate a snapshot or golden without reading the diff.** Pinned output
  proves the output did not change, not that it is right.

---

## 6. Snapshots and goldens

Terminal output of `scan`, `why` and `diff` is pinned as plain text under
`tests/fixtures/snapshots/`. Golden JSON lives under `tests/fixtures/golden/`.

A snapshot failure means **the rendering changed**. Read the difference first:

```bash
cd "/Users/corvette/Documents/Projects Coding/Skill Lens"
pytest tests/test_render_snapshots.py          # read the diff in the failure output
pytest tests/test_render_snapshots.py --update-snapshots   # only after you have read it
```

---

## 7. High-risk areas

Treat these as **high risk**: they get two critics named by the user at planning
and again at implementation, with each critic's model family disclosed, overlap
flagged, and the user's acceptance recorded ([council §1](../council.md#1-the-roster-and-roles),
[council §5](../council.md#5-review-risk-levels-and-escalation)).

- Path resolution (`core/paths.py`) and anything environment-dependent
- Public data formats: the JSON shapes in `models/`, the golden files
- Registry TOML in `skill_lens/registry/agents/`, and any `evidence` / `source` field
- Permissions and unreadable directories (the TCC-resilient paths in `core/system.py`)
- Exit codes and `--fail-on` (`core/exitcodes.py`)
- Compatibility: anything a scripted user or CI pipeline parses
- Anything `AGENTS.md` §4 flags as load-bearing

---

## 8. What needs the human's approval

Stop and ask. Do not guess.

- **Scope changes** beyond the frozen plan
- **Compatibility changes** — anything that alters an exit code, a JSON key, a default
- **Anything that touches the user's machine** outside the read-only guarantee
- **Registry evidence** that would have to be guessed rather than cited
- **A plan amendment** — see the plan-change table in `../implementation-loop.md`
- **Release and publishing** — see the steps in `DEVELOPMENT.md`

Ask in plain language, one question at a time, and say what you recommend.

---

## 9. Reporting

The project reports in plain English: lead with the outcome, no unexplained jargon,
no walls of text, no raw stack traces without a one-sentence translation. See
`AGENTS.md` §0.