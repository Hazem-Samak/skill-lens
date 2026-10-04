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

The quickest route, and the one that works on a stock Mac, is an installer that
brings its own Python:

```bash
uv tool install skill-lens-cli     # recommended
# or:
pipx install skill-lens-cli
```

Either one puts the `skill-lens` command on your `PATH` in an isolated
environment, so nothing is added to your system Python.

<details>
<summary>Prefer plain <code>pip</code>?</summary>

```bash
pip install skill-lens-cli
```

This works only inside a virtual environment you already manage with Python
3.11+ (see [Development](#development)). On a stock Mac it fails, and the error
is misleading, so read the gotcha below first.

</details>

### If the install fails

**`ERROR: Could not find a version that satisfies the requirement...
No matching distribution found`** — this usually does *not* mean the package is
missing. It means your `python3` is older than 3.11. macOS ships Python 3.9, and
`pip` reports an old interpreter as "no such package." Check with:

```bash
python3 --version
```

If it prints 3.9 or lower, use `uv`/`pipx` above, or `brew install python` and
install into a virtual environment.

**`error: externally-managed-environment`** — you are trying to `pip install`
into Homebrew's Python, which refuses writes outside a virtual environment (a
[PEP 668](https://peps.python.org/pep-0668/) guard). Use `uv`/`pipx`, or create a
venv first. Do **not** reach for `--break-system-packages`; it can damage your
Homebrew Python.

> **Package name note:** the command is `skill-lens` and the Python package is
> `skill_lens`; the distribution is published as `skill-lens-cli` because the
> bare `skill-lens` name was already taken on PyPI.

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

## Status

Early development, and honest about it: the agent registry tags every precedence
rule `documented`, `empirical`, or `inferred`, and says `ambiguous` rather than
guessing. Six phases are complete and reviewed, and the current gate is
**471 tests pass** at **93% branch coverage**, `mypy` strict clean,
`ruff check .` clean, `ruff format --check .` clean.

The build record — every phase, the defects found in each review, and what is
still open — lives in
[`DEVELOPMENT.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/DEVELOPMENT.md).

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest --cov=skill_lens       # test suite + the coverage gate (fails under 90%)
mypy                          # strict type check of skill_lens/
ruff check .                  # lint
ruff format .                 # format
```

The specification is
[`SKILL_LENS_SPECIFICATION.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/SKILL_LENS_SPECIFICATION.md);
the contributor guide, including how snapshots and goldens are regenerated and
how a release is cut, is
[`DEVELOPMENT.md`](https://github.com/Hazem-Samak/skill-lens/blob/main/DEVELOPMENT.md).

All tests run against synthetic fixtures under temporary directories. The test
suite never reads your real `~/.claude`, `~/.agents`, or `~/.codex`.

## License

[MIT](https://github.com/Hazem-Samak/skill-lens/blob/main/LICENSE) © 2026 Hazem Samak
