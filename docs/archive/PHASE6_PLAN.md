# Phase 6 Plan — Enforceable Findings & Evidence Integrity

> **Status:** planned, then implemented. Read this before changing exit codes,
> `--fail-on`, or the evidence fields in `skill_lens/registry/agents/*.toml`.
> **Origin:** chosen by the owner after the Phase 5 review. **Not** in
> `SKILL_LENS_SPECIFICATION.md` — the spec roadmap ends at Phase 5.
> **Date:** 2026-10-01.

---

## 1. Why this phase exists

Phase 5 shipped a complete, correct tool with two gaps that only showed up once
it was actually run against a real machine.

**Gap A — the tool could report but not enforce.** Running `skill-lens doctor`
against a real home directory found five malformed skills and a blown context
budget. The command then exited `0` — success — every time. A diagnostics tool
whose findings cannot change an exit status is a report, not a check. It cannot
gate a CI pipeline, a setup script, or a pre-commit hook, which is the main
reason anyone would install a tool like this.

**Gap B — two registry entries were guesses.** `dsh` and `omp` were the only
agents with `policy_evidence = "inferred"`, an empty `source`, and no citation.
They were the weakest links in a project whose founding rule is *provenance over
hallucination* (AGENTS.md rule 6).

---

## 2. Scope

### Part A — Enforceable findings

1. An explicit **exit-code contract**, implemented in a pure core module:
   | Code | Meaning |
   | --- | --- |
   | `0` | The command ran. No finding reached the threshold. |
   | `1` | The command ran, and findings reached the threshold. |
   | `2` | The command could not run: bad usage, unknown agent, unreadable input. |
   | `3` | Reserved for an unexpected internal fault. Never emitted deliberately. |

2. A `--fail-on {never,error,warning,info}` option on the two commands that
   produce findings (`doctor`, `scan`).
   - **Default `never`** — today's behaviour is preserved exactly. A 0.1.0 user
     who upgrades must not suddenly get a non-zero exit from a clean report.
   - The threshold is a *comparison*, not a count: `--fail-on error` fails when
     any finding is at `error` or above.

3. The decision function lives in `skill_lens/core/exitcodes.py` and is pure —
   no Typer, no Rich, no I/O. `cli.py` only translates the result into
   `typer.Exit`, matching AGENTS.md rule 4 (data first, presentation second).

### Part B — Evidence integrity

4. **Research the two unsourced agents** against their *primary* documentation,
   not blog posts. Record what is documented and what is still not.
5. **Correct `dsh.toml` and `omp.toml`** where documentation contradicts the
   registry.
6. **Enforce the discipline in code.** A new gate asserts that no agent may
   claim `documented` or `empirical` evidence without a real `source` URL, and
   that no root may claim `documented` evidence without one either. Today this
   holds; the point is that it stays true.
7. **Let `doctor` audit the registry.** A new informational finding reports any
   agent whose behaviour Skill Lens cannot cite. The tool now states its own
   limits instead of only the user's.

---

## 3. What the research actually found

Both agents have real primary documentation. Both registry entries were wrong.

### `omp` — Oh My Pi (`can1357/oh-my-pi`, `docs/skills.md`)

* **Collision behaviour is documented**, not inferred: when two same-named skills
  differ, the higher-precedence one keeps the bare name and every other variant
  survives under a `<namespace>/<name>` suffix. The loser is **not suppressed**.
  → `coexist_policy` moves `ambiguous` → `merge`.
* **Managed (auto-learn) skills are documented as dead last** — provider priority
  5, "always defers to a same-named authored skill". The registry ranked
  `.omp/agent` at 70, which claimed managed skills outrank authored ones.
  → rank corrected to sit below every authored root.
* Discovery is **non-recursive**: one level under `skills/`, nested
  `<root>/group/<skill>/SKILL.md` is not found. `omp.toml` never claimed
  recursion, so no correction was needed — recorded as verified.

### `dsh` — DeepSeek Harness (`deepseek-ai/deepseek-harness`, `docs/subsystems/skills.md`)

* **The documented rank table is complete and different from ours.** The
  registry had three roots; the documented model has six:

  | dsh rank | Source | Root |
  | --- | --- | --- |
  | 100 | project-dsh | `<projectRoot>/.dsh/skills` |
  | 200 | project-agents | `<projectRoot>/.agents/skills` |
  | 300 | custom | `Config.customSkillDirs` |
  | 400 | user-dsh | `<dshHome>/skills` |
  | 500 | user-agents | `<agentsHome>/skills` |
  | 600 | bundled | `Config.bundledSkillDir` |

  **Both user-level roots were missing entirely.** `~/.dsh/skills` and
  `~/.agents/skills` are where a real dsh user's skills actually live, so the
  registry was blind to the most common case. → both added.
* **Rank direction is inverted between the two systems.** dsh documents 100 as
  *highest* priority; Skill Lens ranks *higher numbers win*. The dsh ranks must
  be translated, never copied. This is recorded in the file, because copying
  them would silently invert every dsh precedence decision.
* `custom` and `bundled` are config-dependent and are **not** added: a root that
  only exists when a user sets an option cannot be asserted as always-searched.
* The user root **skips its `.system` child** — consistent with the container
  traversal rule already modelled project-wide.
* **Recursive discovery is explicitly unsupported.** This does *not* change the
  registry: `dsh_profiles` is an inferred *plugin* root modelling bundled
  plugin skills, which the native skill docs do not cover, and it exists to
  exercise the traversal-hazard check added in Phase 4 (C-findings). Removing
  recursion would delete reviewed coverage to satisfy a rule about a different
  root. Left `inferred`, with the reason written down.

---

## 4. Explicit non-goals

* **No new dependencies.** `tomllib` and `yaml` are already present.
* **No behaviour change without `--fail-on`.** Default exit stays `0`.
* **No exit codes on `why`, `diff`, `compare`, `agents`.** Those are queries, not
  health checks; a missing skill is an answer, not a fault. Only `doctor` and
  `scan` can gate.
* **No agent is upgraded to `documented` on the strength of a third-party
  blog.** Only primary documentation counts. A source URL must be the vendor's
  own docs or the canonical repository.
* **No regeneration of a pinned golden or snapshot without reading the diff.**

---

## 5. Risks

| Risk | Mitigation |
| --- | --- |
| A non-zero exit surprises an existing user | Default is `never`; the change is opt-in |
| Registry edits invalidate Phase 2/3/4 goldens | Every diff reviewed and recorded before regeneration |
| "Evidence" drifts into self-certification | A `source` URL is required; prose claims are not evidence |
| Copying dsh ranks inverts precedence | Recorded in the TOML; asserted by a test |
| A doctor finding about the registry is mistaken for a fault on the user's machine | Severity is `info`, not `warning`, so it never trips `--fail-on warning` |

---

## 6. Acceptance gate

* `pytest`, `ruff check .`, `ruff format --check .` all clean.
* New exit-code tests cover: default `never` returns 0 on a dirty report; each
  threshold; a clean report at every threshold; unknown `--fail-on` value; and
  exit `2` preserved for bad usage.
* New evidence tests cover: `documented`/`empirical` without a source fails;
  `documented` root without a source fails; every shipped agent satisfies it.
* Every new guard is **mutation-tested** — deliberately broken, confirmed to
  fail, restored. A test that cannot fail is worse than no test.
* Any golden or snapshot change is reviewed and explained, never blind.
