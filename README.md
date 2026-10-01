# Skill Lens

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

Every command accepts `--json`.

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

- [x] **Phase 0** — frozen models, lazy path resolution, 13 golden fixtures
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
- [ ] **Phase 5** — packaging and release

Current gate: **417 tests pass**, `ruff check .` clean, `ruff format --check .` clean.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest          # run the test suite
ruff check .    # lint
ruff format .   # format
```

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

## License

[MIT](./LICENSE) © 2026 Hazem Samak
