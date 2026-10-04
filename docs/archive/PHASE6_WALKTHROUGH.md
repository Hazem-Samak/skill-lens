# Phase 6 Walkthrough — Enforceable Findings & Evidence Integrity

> **Status:** shipped and verified. `0.1.0` behaviour is unchanged by default.
> **Origin:** chosen by the owner after the Phase 5 review. Phase 6 is **not** in
> the original roadmap — the spec ended at Phase 5 — and was added to
> `SKILL_LENS_SPECIFICATION.md` as explicitly new scope.
> **Plan:** [`PHASE6_PLAN.md`](./PHASE6_PLAN.md) · **Audience:** the next agent or
> human touching exit codes, `--fail-on`, or the registry's evidence fields.
> **Date:** 2026-10-01.

---

## 1. TL;DR for a non-programmer

Phase 5 boxed the tool up. Phase 6 answers two questions that only appear when
you actually *use* the box.

**"Can it stop a broken setup?"** No — it could only tell you. `doctor` found
five broken skills on the author's own machine and then reported success. It
now has a switch that makes it fail instead, so you can use it as an automatic
alarm. **The default behaviour is unchanged**, so nothing that worked yesterday
breaks today.

**"Does it know what it is talking about?"** Mostly — but two of the ten agents
it describes were educated guesses with no source. This phase went and read the
official documentation for both, and found **both were wrong**:

* **DSH** was missing the two folders where most people's skills actually live.
  The tool could not see them at all.
* **Oh My Pi** had its lowest-priority folder ranked *above* the ones that
  should win — exactly backwards from what the vendor documents.

Both now cite their real documentation, so `skill-lens why` can tell you *why* it
believes something, and you can go check.

---

## 2. Part A — findings that can gate a pipeline

### The exit-code contract

Defined once, in `skill_lens/core/exitcodes.py`, and pure: no Typer, no Rich, no
filesystem. `cli.py` only translates the answer into `typer.Exit`.

| Code | Meaning |
| --- | --- |
| `0` | The command ran and nothing reached the threshold. |
| `1` | The command ran and findings reached the threshold. |
| `2` | The command could not run: bad usage, unknown agent, unreadable input. |
| `3` | Reserved for an unexpected internal fault; never emitted deliberately. |

`ExitCode` is an `IntEnum`, not a `StrEnum`. That was not a stylistic choice —
`StrEnum` **refuses to hold integers** and the module crashed on import until it
was changed. Exit codes are integers; a shell compares them numerically.

### `--fail-on`

On `doctor` and `scan`, defaulting to `never`:

```console
$ skill-lens doctor --fail-on error ; echo "exit=$?"
5 error(s), 1 warning(s), 2 info.
exit=1

$ skill-lens doctor ; echo "exit=$?"     # unchanged from 0.1.0
exit=0
```

Three decisions worth knowing:

* **The default is `never`.** Every command in 0.1.0 exited `0`, including
  `doctor` on a machine with real errors. Changing that default would silently
  break anyone's CI. The gate is opt-in.
* **A threshold is a comparison, not a count.** `--fail-on error` fails on one
  error exactly as it fails on nine, regardless of surrounding notes.
* **The report prints before the failure.** `--fail-on` is not a way to hide the
  evidence that tripped it. This is asserted by a test.

### `--fail-on info` always fails — on purpose

`doctor` emits informational notes about *normal* setups: an absent installer
lockfile, a symlink farm that is the installer's own layout. A completely empty
home already produces one. So `--fail-on info` fails everywhere, always.

Rather than remove the option or quietly ship a trap, the help text now says so
explicitly and a test pins the behaviour. An option that quietly always failed
would be worse than one that tells you in advance.

---

## 3. Part B — the two agents that were guesses

Both agents had `policy_evidence = "inferred"` and an empty `source`. Both were
checked against **primary** documentation only — a vendor's own docs or the
canonical repository. A blog post was found for one of them and deliberately
**not** used.

### `dsh` — DeepSeek Harness

**Source:** `deepseek-ai/deepseek-harness`, `docs/subsystems/skills.md`

The docs publish a complete six-row rank table. The registry had three roots —
and **both user-level roots were missing**. `~/.dsh/skills` and
`~/.agents/skills` are where a real dsh user's skills actually live, so the
registry was blind to the most common case. Both are now declared, in the
documented order.

> **The rank direction is inverted between the two systems.** dsh documents 100
> as the *highest* priority; Skill Lens ranks *higher numbers win*
> (`max(hits, key=rank)` in `resolver.py`). Copying the upstream numbers would
> have silently inverted every dsh precedence decision. The ranks are
> **translated**, the translation table is written into `dsh.toml`, and a test
> asserts the relative order.

Two documented roots are deliberately **omitted** rather than guessed:
`custom` (300) and `bundled` (600) exist only when the user sets an option, so
asserting them as always-searched would be a guess.

### `omp` — Oh My Pi

**Source:** `can1357/oh-my-pi`, `docs/skills.md`

* **A real defect.** The `omp-managed` (auto-learn) provider is documented at
  priority **5 of nine** and "always defers to a same-named authored skill". The
  registry ranked `.omp/agent` at **70** — claiming managed skills outrank
  authored ones, the opposite of the documentation. Corrected and pinned by a
  test.
* **Collision is namespaced, not suppressed.** When two same-named skills
  differ, the higher-precedence one keeps the bare name and the other survives
  under a `<namespace>/<name>` suffix.

### The judgment call worth recording

`omp`'s collision behaviour is now documented, so the obvious move was
`coexist_policy = "merge"`. That was tried — **and reverted**, because the
resolver prints this reason for `merge`:

> "Listed alongside a higher-priority copy; Oh My Pi merges all roots with **no
> documented winner**."

A winner *is* documented. The tool would have been confidently wrong.

`shadow` is worse: it would claim the loser is suppressed, when it stays
reachable under a namespace.

`ambiguous` under-claims instead — "collision policy is undocumented" — which is
false only in the safe direction. For a tool whose founding rule is *provenance
over hallucination*, under-claiming is the correct direction of error. So
`coexist_policy` stays `ambiguous` while `policy_evidence` becomes `documented`,
and a test pins that split so nobody later "fixes" it into a false statement.

**The honest gap:** this tool cannot represent namespaced coexistence. That is
real missing capability, recorded here as future scope rather than faked.

### One thing that was *not* changed

Upstream states dsh does not support recursive `**/SKILL.md` discovery. The
`dsh_profiles` root nonetheless has `recursive = true` — and that was left
alone, deliberately. It models a **node-module plugin bundle**, a different kind
of root that the native skill docs do not describe, and it exists to keep the
traversal-hazard check exercised (a Phase 4 finding with its own test). Removing
it to satisfy a rule about a different root would delete reviewed coverage. The
root stays `inferred` and the reason is written into the file.

---

## 4. The tool now audits itself

A new `doctor` check reports agents whose precedence Skill Lens had to **infer**,
because no primary documentation could be found. Severity is `info`: it is a
limitation of our knowledge, not a fault on the user's disk, so it must never
trip `--fail-on warning` or `--fail-on error`.

**With the registry as shipped it reports nothing**, because every agent is now
either documented or empirically verified. That is the intended quiet state. The
check exists to catch a regression, and a guard that is always loud is a guard
nobody reads. Its firing path is still tested with a synthetic registry.

An earlier version reported every non-`documented` agent and immediately listed
seven — including `antigravity` and `codex`, which are `empirical` agents that
*do* have real evidence. That was a false alarm on 7 of 10 agents, and it was
wrong. Only genuinely `inferred` agents are reported now.

---

## 5. Evidence is now enforced, not requested

Three invariants replace what used to be a convention. They are strictly stronger
than the test they replaced, which asserted only that two named agents were
`inferred` — pinning a moment rather than a rule, and blind to a *third* agent
quietly claiming `documented` with no citation.

1. No agent may claim `documented` or `empirical` evidence without a `source`.
2. That `source` must be a real `http(s)` URL — a citation in appearance only
   does not count.
3. No root may claim `documented` evidence unless its agent carries a citable
   source.

Rule 3 is deliberately **not** "an agent's policy level must be `documented`".
`antigravity` and `codex` are `empirical` overall while individual roots are
`documented`, and that is legitimate: a vendor document can establish one search
path without establishing a whole collision policy. The first draft of this rule
got that wrong and was corrected.

After this phase: **10 of 10 agents cite a source**, and none is `inferred`.

---

## 6. Golden and snapshot changes (reviewed, not regenerated blind)

Both were read line by line before being updated.

**`tests/fixtures/golden/project_beats_global.json`** — two `rule_id` values for
`omp` only: `omp_inferred_project` → `omp_documented_project`, and
`omp_inferred_global` → `omp_documented_managed_last`. State, scope, visibility,
collision, variant label and **reason text were all unchanged** — which is the
proof that keeping `coexist_policy = "ambiguous"` was the right call.

**`tests/fixtures/snapshots/scan_variant_hash_detection.txt`** — `dsh` now appears
as a detected agent and now reaches `~/.agents/skills/deploy`. The table simply
grew four characters wider to fit it. This is the missing-root defect becoming
visible: the snapshot now shows a skill `dsh` can actually see.

---

## 7. Mutation testing — and what it caught

Every new guard was deliberately broken to confirm it fails. A test that cannot
fail is worse than no test.

| # | Mutation | Result |
| --- | --- | --- |
| M1 | `error` threshold weakened to `warning` | caught |
| M2 | explicit empty-report guard removed | **not caught — dead code removed** |
| M3 | default `--fail-on` changed to `error` | caught |
| M4 | `scan` severities replaced with `()` | **not caught — test strengthened** |
| M5 | `malformed_yaml` downgraded to a warning | caught |
| M6 | `dsh` user root outranked the project roots | caught |
| M7 | `omp` managed skills outranked authored ones | caught |
| M8 | `omp` over-claimed `shadow` coexistence | caught |
| M9 | registry check matched the wrong evidence level | caught |
| M10 | registry finding escalated to `warning` | caught |

**Two mutations survived, and both mattered.**

* **M2** exposed a `not severities` branch that was pure decoration — deleting it
  left every test green, because `any()` over an empty sequence is already
  `False`. It was **deleted**, and the test docstring was corrected: it pins the
  *behaviour*, not a branch that no longer exists. Dead code that looks like
  protection is worse than no code.
* **M4** exposed a real hole: the scan tests only ever scanned a **clean**
  sandbox, so replacing `scan_severities(report)` with `()` passed everything.
  A test was added that scans a sandbox with a deliberately broken skill and
  asserts the gate trips. A gate is only trustworthy once proven to fail.

M3 is worth a footnote: the shell helper used for the batch reported it as
surviving, but running it explicitly showed two failures. **The harness gave a
false negative**; the guard was sound. Recorded because the lesson is the same
one from Phase 5 — reproduce the result yourself before believing it.

---

## 8. Mistakes made in this phase

Written down because they cost time and would cost the next agent the same.

* **`git checkout skill_lens/cli.py` destroyed uncommitted work.** The file had
  never been committed, so "restore the file" wiped the entire `--fail-on`
  wiring. It had to be rewritten from scratch. Back up before mutating; never
  use `git checkout` on a file whose changes are not committed.
* **A mutation harness reported a false negative** (M3) and, separately, a
  first draft of the root-evidence invariant was too strict. Both were found by
  checking the result against a direct, explicit run.

---

## 9. Gate

```bash
uv run pytest                      # 465 passed
uv run ruff check .                # All checks passed!
uv run ruff format --check .       # 59 files already formatted
```

Phase 6 added 41 tests (31 in `tests/test_phase6_gate.py`, plus registry
invariants and the two registry-regression tests). `tests/test_phase6_gate.py` is
the phase gate; `PHASE6_PLAN.md` section 6 holds the acceptance criteria.

---

## 10. Known limitations carried forward

* **Namespaced coexistence is not modelled.** `omp`'s documented behaviour —
  a loser that survives under `<namespace>/<name>` — has no representation in the
  shadow/merge/ambiguous vocabulary. `omp` therefore under-claims. Closing this
  means adding a fourth coexist policy, not editing a TOML.
* **`--fail-on info` is not usable as a gate**, by design (section 2).
* **`scan` and `doctor` must agree about severity.** `_PARSE_STATUS_SEVERITY` in
  `scanner.py` mirrors doctor's own choices deliberately; a test asserts it.
* **Two agents were corrected from documentation, not from running them.** The
  authors do not have dsh or omp installed, so these are `documented`, not
  `empirical`. Confirming against a real installation would upgrade them and is
  the obvious next piece of evidence work.
