# Phase 2 Review Findings — Resolved

> **Status:** Phase 2 is built, committed, tested — and **now correct**.
> **All 13 open findings (F-01 … F-13) are fixed**, plus one further critical
> defect found while verifying them (**F-15**) and five more found by an
> independent audit of the fixes themselves (**F-16 … F-20**).
> **Reviewed by:** orchestrator self-review + an independent read-only review
> delegated to Gemini 3.8 Flash High (`agy`, 2026-09-30).
> **Commits reviewed:** `4a7a03c` (Phase 2), `eae309f` (self-review fix).
> **Gate after those fixes:** `311 passed`, `ruff check` clean.
>
> **This is a point-in-time record of Phase 2.** Phases since then have moved the
> gate on — Phase 3 is documented in [`PHASE3_FINDINGS.md`](./PHASE3_FINDINGS.md),
> and the current test count lives in the [README](./README.md). The counts below
> are what was true when each part of this document was written.

---

## 1. TL;DR for a non-programmer

Phase 2 built the part of Skill Lens that answers *"which copy of this skill
actually wins, and why?"*. A review found the **ranking of folders was
backwards for 6 of the 10 AI agents**: the code said *"Project beats Global"*
while giving the Global folder the higher score. That, and 12 smaller problems,
are now all fixed.

While checking the work on this actual machine, one more serious bug surfaced
and was also fixed: Skill Lens counted **502 "global skills" when only 84 real
skill libraries exist**. It treated every agent's shortcut into the same shared
library as a separate skill — exactly the thing the tool exists to prevent.

**None of this is theoretical any more.** Every fix has a test that fails if the
bug ever comes back.

---

## 2. What Phase 2 actually shipped (working, keep it)

| Item | State |
| --- | --- |
| 10 agent definitions as provenance-tagged TOML | shipped |
| Registry loader (TOML → frozen dataclasses) | shipped |
| Discovery: finds skills, tags which agent roots reach them | shipped |
| Symlink farms merge into 1 library with N entrypoints | shipped |
| 3-axis resolver → `ACTIVE / SHADOWED / COEXISTS / DISABLED / UNSEARCHED / INVALID / AMBIGUOUS` | shipped, but see F-01 |
| Every reason carries `rule_id` + `evidence` | shipped |
| Commands `scan`, `why`, `agents`, all with `--json` | shipped |
| Strictly read-only, no network, no DB, no TUI | verified |
| Tests never touch real `~/.claude`, `~/.agents`, `/etc/codex` | verified |
| Gate status at time of writing | **243 tests pass, `ruff check` clean** |

> **Reading section 4:** the detailed write-ups below describe each bug **as it
> was found**, including the code excerpts that were wrong. They are kept as the
> record of what was wrong; section 7 says what each fix actually was.

---

## 3. Findings index

| ID | Severity | Area | One-line summary | State |
| --- | --- | --- | --- | --- |
| **F-01** | 🔴 Critical | Registry ranks | Project-vs-Global precedence is inverted for 6 agents | ✅ **fixed** |
| **F-02** | 🔴 Critical | Discovery | Copies sharing one target collapse, losing the distinction | ✅ **fixed** |
| **F-03** | 🟠 Major | Registry / resolver | Codex declares `merge` but the resolver never honours it | ✅ **fixed** |
| **F-04** | 🟠 Major | Resolver | `why --agent pi` can report *another agent's* folder path | ✅ **fixed** |
| **F-05** | 🟠 Major | Resolver | A broken skill cannot be found by the name inside it | ✅ **fixed** (confirmed, was real) |
| **F-06** | 🟡 Minor | Discovery | A symlinked `.md` file loses its "standalone file" rule | ✅ **fixed** (confirmed, was real) |
| **F-07** | 🟡 Minor | Resolver | The "shadowed" message confusingly quotes the loser itself | ✅ **fixed** |
| **F-08** | 🟡 Minor | Scanner | `variant_label` (Variant A / B) is never populated | ✅ **fixed** |
| **F-09** | 🟡 Minor | CLI | Commands default the working folder to `$HOME`, not your terminal folder | ✅ **fixed** (sandbox isolation preserved) |
| **F-10** | 🟡 Minor | Resolver | A skill that does not exist at all reports `UNSEARCHED` | ✅ **fixed** |
| **F-11** | 🟢 Info | Model | `agent_entrypoints` holds agent *names* where the fixture contract says *paths* | ✅ **fixed** |
| **F-12** | 🟢 Info | Tests | The Phase 2 gate only compares 3 fields, leaving gaps unguarded | ✅ **fixed** (9 fields now) |
| **F-13** | 🟢 Info | Tests | No test covers "Project beats Global" for any agent | ✅ **fixed** (new 13th scenario) |
| **F-14** | ✅ Fixed | Scanner | Symlink entrypoint count was inflated | ✅ fixed in `eae309f` |
| **F-15** | 🔴 Critical | Parser | Unnormalized canonical paths split one library into many | ✅ **fixed** (found while verifying) |

A second, independent audit of the fixes found five more problems —
**F-16 … F-20** — all now fixed. See section 8.

**Gate before the fixes:** 243 tests pass, `ruff check` clean.
**Gate now:** 311 tests pass, `ruff check` clean.

---

## 4. Detailed findings

### F-01 🔴 Critical — Project-vs-Global precedence is inverted for 6 agents

**What the code claims** (in each agent's own TOML `collision_policy`):
`Shadow (Project > Global)` / `Shadow (Project > User > Builtin)`.

**What the code does** — the Global root is scored higher than the Project root,
and `resolver.py:208` picks the highest score:

```python
top_rank = max(c.rank for c in searched_valid)
winners = [c for c in searched_valid if c.rank == top_rank]
```

**Affected agents and scores**

| Agent | Global root (score) | Project root (score) | Correct? |
| --- | --- | --- | --- |
| antigravity | `.gemini/config/skills` (90) | `.agents/skills` (80) | ❌ |
| pi | `.pi/agent/skills` (90), `.pi/skills` (85) | `.pi/skills` (70), `.agents/skills` (60) | ❌ |
| grok | `.grok/skills` (90) | `.agents/skills` (70) | ❌ |
| qoder | `.qoder/skills` (90) | `.qoder/skills` (70), `.agents/skills` (65) | ❌ |
| windsurf | `.codeium/windsurf/skills` (90) | `.windsurf/skills` (70), `.agents/skills` (65) | ❌ |
| omp | `.omp/agent` (80), `.agents/skills` (75) | `.omp/skills` (65), `.agents/skills` (60) | ❌ |

**Correctly configured (do not change):**

| Agent | Scores | Why it is right |
| --- | --- | --- |
| claude | personal `~/.claude/skills` (100) > project (50) | spec says **Personal > Project** — the opposite rule |
| dsh | project (60, 55) > plugin profiles (40) | project already wins |
| codex | project (90) > global (85, 80) | consistent with "merged" |
| opencode | 80 / 80 vs 70 / 70 | ties are intentional → `AMBIGUOUS` |

**How to reproduce**

```python
# temp home; (home/"proj"/".git") created; then:
make_skill(home / ".grok/skills/deploy", "deploy", "GLOBAL copy.")
make_skill(home / "proj/.agents/skills/deploy", "deploy", "PROJECT copy.")
resolve_skill("deploy", "grok", home / "proj", home)
# observed: project copy -> SHADOWED   (policy says it should be ACTIVE)
```

> ⚠️ **Reproducing this is easy to get wrong.** An early check by the orchestrator
> appeared to pass 4 of the 6 agents purely because the test placed the "global"
> copy in `.agents/skills`, which is **not** those agents' global root. Use each
> agent's real global root path from the table above.

**Also note:** the independent reviewer reported 5 affected agents; the
orchestrator's verification found **6** — `omp` was missed by the reviewer.

---

### F-02 🔴 Critical — Copies that share one target collapse, losing the distinction

`discovery.py:350 _merge_entries()` groups every entrypoint by its **canonical
target** before the resolver ever sees it:

```python
merged[key] = DiscoveredEntry(
    entrypoint_path=existing.entrypoint_path,   # keeps only the FIRST path
    ...
)
```

**Failing case A — a project shortcut and a global copy pointing at the same library**

```
canonical library : ~/.agents/skills/deploy
project shortcut  : <repo>/.agents/skills/deploy  -> same library
resolving for codex from the repo
observed : 1 candidate (ACTIVE) — the "2 copies, 1 shadows the other" story is lost
expected : 2 candidates, the global one SHADOWED
```

This directly contradicts the spec's split (section 4):
*Precedence & Collision* must be judged on the **entrypoint path**;
*Inventory & Identity* may use the **canonical target**.

**Failing case B — `why` reports the wrong agent's folder**

```
~/.agents/skills/shared        (real library)
~/.claude/skills/shared   ->   symlink
~/.pi/agent/skills/shared ->   symlink

skill-lens why shared --agent pi
observed : Path reported to the user = ~/.claude/skills/shared
expected : the Pi entrypoint, i.e. ~/.pi/agent/skills/shared
```

The reported entrypoint is whichever root was walked first (alphabetical agent
order), not the one the requested agent actually uses.

---

### F-03 🟠 Major — Codex's `merge` coexistence policy is never honoured

`registry/agents/codex.toml` declares `coexist_policy = "merge"`, and the spec
describes Codex as *"Unverified / Merged (Both listed)"*. But `resolver.py:237`
only special-cases the literal string `"ambiguous"`:

```python
if agent.coexist_policy == "ambiguous":
    return HeadlineState.COEXISTS
return HeadlineState.SHADOWED  # <- "merge" falls through to here
```

**Failing case:** `~/.codex/skills/deploy` + `<repo>/.agents/skills/deploy`
resolved for codex → observed `SHADOWED` / collision `suppressed_shadow`;
expected `COEXISTS` (both listed, neither suppressed).

**Open design question:** what should Codex's headline be when both copies coexist
but neither is documented to win? Candidates: `COEXISTS`, or `AMBIGUOUS` with
`unverified` provenance. This is a **product decision, not a pure bug fix.**

---

### F-04 🟠 Major — `agent_entrypoints` contradicts the Phase 0 contract

The Phase 0 golden fixture defines this field as **paths**:

```json
"agent_entrypoints": [
  ".claude/skills/shared", ".pi/agent/skills/shared", ".qoder/skills/shared"
]
```
(`tests/fixtures/golden/symlink_farm_multi_agent.json:13`)

But `resolver.py:298` fills it with **agent ids**:

```python
agent_entrypoints = (tuple(hit.agent_id for hit in entry.hits),)  # ("claude", "pi", ...)
```

`DiscoveredEntry` now carries the real paths in `entrypoint_paths`, so the fix is
small — but the *model docstring* (`models/installation.py:22`) is also ambiguous
and should be tightened at the same time.

---

### F-05 🟠 Major — A broken skill cannot be found by the name written inside it

`resolver.py:118`:

```python
def _matches(agent, entry, name) -> bool:
    if not _is_valid(entry):
        return entry.name == name  # entry.name is the FOLDER name
```

**Failing case:** folder `~/.codex/skills/custom_folder/SKILL.md` contains
`name: my-skill` but no `description` (so it is `INVALID`).
Codex identifies skills by frontmatter name, so:

```
skill-lens why my-skill --agent codex
observed : 0 candidates, headline UNSEARCHED
expected : 1 candidate, headline INVALID, reason "missing description"
```

The fix is to consult `entry.parse.frontmatter_name` even when the parse status is
not `VALID` — that field is populated for `MISSING_DESCRIPTION` results.

---

### F-06 🟡 Minor — A symlinked `.md` file loses its standalone-file rule

`discovery.py:229`:

```python
if child.is_symlink():
    results.append((child, False))   # is_file forced to False
elif ...
elif child.suffix.lower() == ".md":
    results.append((child, True))
```

A symlink pointing at a standalone `.md` skill is classified as a directory skill,
so Antigravity emits `antigravity_global_skills` instead of the correct
`antigravity_standalone_md`. Not traced to a proven end-to-end failure, but the
branch is clearly wrong by inspection.

---

### F-07 🟡 Minor — The "shadowed" explanation quotes the loser itself

`resolver.py:327`:

```python
return f"Suppressed by a higher-priority copy ({candidate.reason_fragment})."
```

`reason_fragment` is the **losing** candidate's own description, so the output reads:

```
Reason: Suppressed by a higher-priority copy (Project deploy helper.)
```

as though the project copy were the thing doing the suppressing. Should instead
name the winning copy's location/root, or use a neutral phrase.

---

### F-08 🟡 Minor — `variant_label` (Variant A / B) is never populated

Golden fixture scenario 8 is literally named `variant_hash_detection` and its
expectations carry `"variant_label": "A"` / `"B"`. The field exists on
`SkillInstallation` and `ScanEntry` but is **always `None`**, because nothing in
Phase 2 assigns labels to differing content hashes.

Related: `resolver.py:239` also has no path that returns `SHADOWED` for a candidate
whose copy sits in a root the agent *does* search but loses on rank — the
"Variant A / Variant B" story from the spec is unfinished.

---

### F-09 🟡 Minor — Commands default the working folder to `$HOME`

`cli.py:_effective_cwd` returns `paths.home()` when `--cwd` is omitted, so running
`skill-lens why deploy --agent claude` from inside a repository finds **no project
skills** (there is no git boundary at `$HOME`, so project roots are correctly
skipped). The natural default is the terminal's current directory.

⚠️ **This default was chosen deliberately for sandbox safety:** a relative
`--cwd` is resolved *against the mock home* by
`discovery.normalize_cwd()`, which keeps `--sandbox` runs from escaping. If the
default is changed to the real `Path.cwd()`, that clamping must be preserved or
sandboxed runs will start reading the real filesystem.

---

### F-10 🟡 Minor — A nonexistent skill reports `UNSEARCHED`

`_headline_from_states([])` returns `UNSEARCHED`. Per spec section 2, `UNSEARCHED`
means *"exists on disk, but this agent never looks there"* — which is not the same
as *"no copy of this name exists anywhere."*

`skill-lens why fake-skill --agent claude` prints `UNSEARCHED` with an empty
candidate list and exit code 0. A distinct outcome (or at least a clear message)
would be better. Note: the existing test
`test_unknown_skill_returns_unsearched` currently *asserts* this behaviour, so it
must be updated alongside any change.

---

### F-11 / F-12 / F-13 — Test-suite gaps (why F-01 survived)

- The Phase 2 gate (`tests/test_phase2_gate.py`) compares only
  `(state, canonical_path, rule_id)`. It never checks `entrypoint_path`, `scope`,
  `agent_entrypoints`, `variant_label`, `visibility`, `collision`, or `reason` —
  which is exactly why F-04 and F-08 pass unnoticed.
- **No fixture or test exercises "Project beats Global" for any agent.** All 12
  golden scenarios test project-vs-project collisions on Claude only. F-01 sat
  undetected for this reason. A new golden scenario is needed.
- The symlink-farm test asserts only that Pi finds 1 candidate; it never checks
  *which* entrypoint Pi is shown, so F-04 (wrong agent's path) also slipped through.

---

### F-14 ✅ Fixed — Symlink entrypoint count was inflated

Found during the orchestrator's own self-review, fixed in commit `eae309f`.

`scan` reported the number of *(agent, root) pairs* reaching an entrypoint rather
than the number of actual symlinks. Because several agent roots reach the same
physical path, the number was inflated (2 real symlinks reported as 5).

`DiscoveredEntry` now records deduplicated `entrypoint_paths`, the scanner counts
real symlinks from those paths, and `tests/test_discovery.py` asserts the reported
count equals the symlinks actually on disk.

---

## 5. What the independent reviewer got wrong or overstated

Recorded so this is not re-litigated later:

| Reviewer claim | Assessment |
| --- | --- |
| "5 agents affected" (F-01) | **Undercount.** Orchestrator verification found **6** — `omp` was missed. |
| "Golden fixture edit masks a bug" (their §4.5) | **Not agreed.** The edit to `variant_hash_detection.json` corrected a genuine Phase 0 imprecision: the copy sits in the *personal* root, so `claude_personal_beats_project` is the correct rule id. It is *semantically odd* (a rule named "beats project" attached to a skill with no project copy), which is a real readability smell worth addressing, but it is not a masked defect. |
| "Phase 2 is not ready to ship" | **Agreed.** F-01 and F-02 are correctness bugs in the tool's central promise. |

---

## 6. What was checked and is genuinely fine

Do not re-investigate these:

- Strict read-only guarantee — no writes, no network, no telemetry, no database.
- Test hermeticity — real `~/.claude`, `~/.agents`, `~/.codex`, `/etc/codex` are
  never read. `mock_home` also activates the sandbox so absolute system roots stay
  closed; `test_absolute_roots_skipped_under_sandbox` guards this.
- Lazy path resolution (AGENTS.md rule 3) — no import-time `~` expansion.
- Symlink cycle protection — tracked by `(st_dev, st_ino)`, reports `CYCLE`, never hangs.
- Streaming SHA-256 — full-file, no truncation; CRLF normalised; binaries raw.
- Claude's **Personal > Project** ordering — correct, and correctly the inverse of
  the other agents. This is the case the golden fixtures cover well.
- JSON output — emitted unwrapped/unhighlighted; verified parseable.
- Rich markup escaping — skill descriptions cannot inject terminal markup.
- Performance — a synthetic farm of 83 skills × 10 roots scans in ~120 ms.
- Presentation separation — Rich is strictly a layer over serializable models.

---

## 7. How each finding was fixed, and the judgement calls

Every fix below has a named regression test. Reverting the fix turns that test red.

| ID | The fix | Guarded by |
| --- | --- | --- |
| F-01 | Project roots re-scored above global roots in 6 TOMLs (project roots now 85–90, global 65–75, built-in lowest). | `test_project_beats_global_for_every_shadow_agent` (6 cases) + the new golden scenario |
| F-02 | `RootHit` now carries the **entrypoint path that root reaches the skill through**, and the resolver builds one candidate per entrypoint instead of per canonical library. | `test_project_shortcut_and_global_copy_stay_separate_candidates` |
| F-03 | `coexist_policy = "merge"` is honoured: a lower-ranked copy is `COEXISTS`, never `SHADOWED`. | `test_codex_merge_policy_is_honoured` |
| F-04 | The reported `entrypoint_path` comes from the requested agent's own hit. | `test_reported_entrypoint_belongs_to_the_requested_agent` |
| F-05 | Identity lookup consults `frontmatter_name` even for copies that failed validation. | `test_broken_skill_is_findable_by_its_frontmatter_name` |
| F-06 | A symlink resolving to a `.md` file keeps the root's `file_rule_id`. | `test_symlinked_markdown_keeps_the_standalone_file_rule` |
| F-07 | A shadowed copy's reason and `rule_id` now name the **winning** copy's root. | `test_shadowed_reason_names_the_winner_not_the_loser`, `test_shadowed_rule_cites_the_winning_root` |
| F-08 | `variant_label` is populated in both `why` and `scan`. | 4 variant tests |
| F-09 | `--cwd` defaults to the terminal's folder via `paths.terminal_cwd()`. | `test_why_defaults_to_the_terminal_folder`, `test_terminal_cwd_is_the_sandbox_under_sandbox`, `test_sandboxed_run_cannot_escape_into_the_real_terminal_folder` |
| F-10 | New `ResolutionReport.found` flag plus a clear note and terminal message. | `test_unknown_skill_is_not_found_rather_than_unsearched`, `test_why_reports_a_missing_skill_clearly` |
| F-11 | `agent_entrypoints` now holds paths. | `test_agent_entrypoints_are_paths_not_agent_ids` |
| F-12 | The gate compares 9 fields, and *fails if a golden omits one*. | the gate itself |
| F-13 | New `project_beats_global` golden scenario (13th), one skill per agent in that agent's real roots. | `test_all_scenarios_present`, the new golden |

### 7.1 Three places where the fix changed documented behaviour

These are decisions, not accidents, and are called out so they are not
"discovered" later as surprises.

1. **F-02 case A now ends `COEXISTS` for Codex, not `SHADOWED`.**
   The original finding expected the global copy to be `SHADOWED`. But the same
   finding list (F-03) requires Codex's `merge` policy to be honoured, and spec
   section 2 defines merged roots as *both listed, neither suppressed*. With
   F-03 fixed, `COEXISTS` is the correct answer for Codex. The `SHADOWED` story
   is still covered, by the five agents that actually declare a shadow policy
   (see the new golden scenario).

2. **F-08: "Variant A" now has one rule, shared by `scan` and `why`.**
   The Phase 0 fixtures carried `A`/`B` labels, but the field was never
   implemented, so those letters were placeholders with no rule behind them.
   The rule is now: copies of one name whose bytes differ are labelled
   **most-specific scope first** (project, then user, then system, then plugin),
   then discovery order — identical in both commands, so a copy is never
   "Variant A" in `scan` and "B" in `why`. Three consequences: identical bytes
   share one label (same content, not variants), copies that failed validation
   get no label at all (no content to compare), and **which copy wins is
   reported by the candidate's `state`, not by its letter.** For nine of the
   ten agents "most specific scope" and "wins" agree; they differ only for
   Claude, whose documented rule is Personal > Project, so Claude's project copy
   is Variant A even though the personal copy is ACTIVE.

   Ordering was deliberately *not* left agent-dependent: an earlier attempt
   ordered `why` by rank and `scan` by scope, and an independent audit caught
   the two commands labelling the same file in opposite orders.

3. **F-05 has a side effect worth knowing: identity is now consistent.**
   Previously an *invalid* copy was matched on its folder name regardless of the
   agent's identity source, while a *valid* copy respected it. For Codex
   (frontmatter identity) `why custom_folder` used to find a skill whose
   declared name was `my-skill`; now it correctly does not. Claude
   (directory-name identity) still finds it by folder name. Both directions are
   pinned by tests.

### 7.2 F-15 🔴 Critical — one library was being counted many times (found during verification)

This one was not in the original review. It surfaced when the fixed tool was run
against this machine for real.

`scan` reported **502 global skills**. The machine has **84** distinct skill
libraries under `~/.agents/skills`. The cause: `canonicalize()` walked the
symlink chain but never normalized the result, so a relative farm link
(`~/.pi/agent/skills/x -> ../../../.agents/skills/x`) produced the canonical
string `~/.pi/agent/skills/../../../.agents/skills/x`. Every agent's link into
the shared library therefore hashed to a *different* "canonical" key, and the
one-library-with-N-entrypoints grouping the specification demands simply did not
happen.

Every fixture used *absolute* symlink targets, which is why 243 green tests
missed it completely.

`canonicalize()` now returns `os.path.realpath()` of the terminal node, which
normalizes the path and resolves any symlinked parent. The live farm now
reports 84 global skills and 443 symlink entrypoints against 84 libraries.
Regression coverage: `test_relative_symlinks_still_merge_to_one_canonical_library`,
and the Phase 0.5 acceptance farm now builds **relative** links, as a real farm
does.

---

## 8. Second review — auditing the fixes (F-16 … F-20)

The fixes above were then audited independently, by reverting each one in a
throwaway copy of the repo and checking the named test actually went red.
Eleven of thirteen reverted cleanly and their tests caught them. **Two did
not**, and one more problem was found by inspection. All are fixed now.

| ID | Severity | What the audit found | State |
| --- | --- | --- | --- |
| **F-16** | 🔴 Critical | `scan` and `why` labelled the same file differently. `scan` ordered variants by scope, `why` by the agent's rank, so a copy could be "Variant A" in one command and "B" in the other. | ✅ **fixed** — one shared rule in `discovery.variant_labels`. |
| **F-17** | 🟠 Major | The F-06 test was **tautological**. It also created a real `.md` sibling inside the same root, and merging the two entries supplied `is_file` anyway — so it passed with the bug restored. | ✅ **fixed** — the target now lives outside the scanned root; confirmed red on revert. |
| **F-18** | 🟠 Major | The F-15 `realpath` change made `canonical_path` resolved while `entrypoint_path` stayed as written. Where home sits behind a symlink (macOS `/tmp`), `~` collapsing broke and `why` printed a redundant "Link:" line pointing at the same file. | ✅ **fixed** — `paths.display()` and the new `paths.same_location()` compare both as-written and resolved forms. |
| **F-19** | 🟠 Major | `--sandbox H --cwd /somewhere/else` was accepted and read outside the sandbox. Pre-existing (relative `--cwd` was clamped, absolute was not), but it is the same guarantee F-09 depends on. | ✅ **fixed** — a `--cwd` outside the sandbox is now refused with a clear error. |
| **F-20** | 🟡 Minor | The gate's own field list could be narrowed back to 3 fields with every test still green, and the golden `installations` blocks were checked for key presence only — so the F-11 path contract and the variant labels there were asserted by nothing. | ✅ **fixed** — the field list is pinned by its own test, and every golden installation is now compared against a real scan. |

Also corrected during the audit: the F-09 CLI test had been written with the
sandbox **off**, which re-opened `/etc/codex` to the test suite and contradicts
AGENTS.md rule 2. It now runs inside the sandbox and redirects only
`paths.terminal_cwd`, which is what the CLI is actually responsible for; the
sandbox/non-sandbox behaviour of `terminal_cwd()` is pinned separately in
`tests/test_paths.py`.

**Re-verified by the audit:** the read-only guarantee (the only file opens in
the package are read modes; no write, network, database or telemetry), test
hermeticity, lazy path resolution, and that cycle / broken-link / self-loop
detection all survive the `realpath` change.

### 8.1 A third pass, on the audit's own fixes

The five fixes above were audited again. Three of them were still wrong:

| ID | What the second audit found | State |
| --- | --- | --- |
| **F-16 (residual)** | The shared rule was extracted, but the two commands still passed **different scopes into it**: `scan` used the most project-specific scope any root assigns, `why` used the scope of the one root the *requested* agent uses. A library reachable as a user root for Claude and a project root for Grok was "A" in `scan` and "B" in `why --agent claude`. | ✅ **fixed** — scope now comes from `discovery.entry_scope()`, a property of the entry, on both sides. Pinned by `test_scan_and_why_agree_on_variant_labels_across_scopes`. |
| **F-18 (residual)** | The `display()` test could not tell its two branches apart, because `set_sandbox()` pre-resolves its argument — so the symlinked-home handling was untested. Mutating it away left every test green. | ✅ **fixed** — the test now drives `HOME` directly and covers both directions, including the sandbox case. Mutating `_home_variants` or the resolved-target fallback now turns it red. |
| **F-19 (regression)** | Refusing an out-of-sandbox `--cwd` also refused a *relative* one, so the documented `--sandbox H --cwd project` form broke and `normalize_cwd()`'s home-relative clamping became unreachable. | ✅ **fixed** — relative values are clamped into the sandbox first, then the containment check runs. Pinned by `test_relative_cwd_stay_inside_the_sandbox`. |

Also noted and accepted: variant labels stop at six (A–F); further copies are
left unlabelled rather than given an invented letter, and this is now stated in
`discovery.variant_labels`.

**Method note.** Each fix was checked by reverting it in a throwaway copy of the
repo and confirming the named test turned red. Two "caught" results in the first
audit were re-checked because the mutation had weakened the guard itself rather
than the code — a mutation that proves nothing.

**Gate after the audit:** `311 passed`, `ruff check` clean.

---

## 9. Reproducing this review

The independent review was produced with a read-only `agy` dispatch:

```bash
node ~/.pi/agent/skills/agy-delegate/scripts/relay.mjs \
  --brief <brief.txt> \
  --cd "/Users/corvette/Documents/Projects Coding/Skill Lens" \
  --model "gemini-3.8-flash-high" --effort high --read-only
```

Re-verify the findings above before acting on them — that discipline is what
surfaced the `omp` omission in F-01, and re-verification during the fix is what
surfaced F-15.

**Gate when the review was written:** `243 passed`, `ruff check` clean.
**Gate after the fixes:** `311 passed`, `ruff check` clean.
