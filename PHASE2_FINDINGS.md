# Phase 2 Review Findings — Open Issues

> **Status:** Phase 2 is built, committed, tested and pushed — but **not correct yet**.
> **Nothing in this list has been fixed.** It is recorded here so it can be addressed later.
> **Reviewed by:** orchestrator self-review + an independent review delegated to
> Gemini 3.8 Flash High (`agy`, read-only run, 2026-09-30).
> **Commits reviewed:** `4a7a03c` (Phase 2), `eae309f` (self-review fix).

---

## 1. TL;DR for a non-programmer

Phase 2 built the part of Skill Lens that answers *"which copy of this skill actually
wins, and why?"* It works and the commands run, but a review found the **ranking of
folders is backwards for 6 of the 10 AI agents**.

Think of it this way. Each agent has a list of folders it looks in, and each folder
has a score. Higher score = "this one wins." The code says in plain English
*"Project beats Global"* — but then gives the **Global** folder the higher score.
So for those 6 agents, Skill Lens would tell you your global skill wins when in
reality your project skill is the one that wins.

That is the main problem. There are 8 others, listed below, most of them small.

**One of the 8 was found and fixed during self-review** (the symlink count), and is
recorded here for completeness.

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

---

## 3. Findings index

| ID | Severity | Area | One-line summary | Verified? |
| --- | --- | --- | --- | --- |
| **F-01** | 🔴 Critical | Registry ranks | Project-vs-Global precedence is inverted for 6 agents | ✅ confirmed by orchestrator |
| **F-02** | 🔴 Critical | Discovery | Copies sharing one target collapse, losing the distinction | ✅ confirmed |
| **F-03** | 🟠 Major | Registry / resolver | Codex declares `merge` but the resolver never honours it | ✅ confirmed |
| **F-04** | 🟠 Major | Resolver | `why --agent pi` can report *another agent's* folder path | ✅ confirmed |
| **F-05** | 🟠 Major | Resolver | A broken skill cannot be found by the name inside it | ⚠️ plausible, not fully traced |
| **F-06** | 🟡 Minor | Discovery | A symlinked `.md` file loses its "standalone file" rule | ⚠️ plausible, not fully traced |
| **F-07** | 🟡 Minor | Resolver | The "shadowed" message confusingly quotes the loser itself | ✅ confirmed |
| **F-08** | 🟡 Minor | Scanner | `variant_label` (Variant A / B) is never populated | ✅ confirmed |
| **F-09** | 🟡 Minor | CLI | Commands default the working folder to `$HOME`, not your terminal folder | ⚠️ plausible (deliberate, needs a sandbox-safe fix) |
| **F-10** | 🟡 Minor | Resolver | A skill that does not exist at all reports `UNSEARCHED` | ✅ confirmed |
| **F-11** | 🟢 Info | Model | `agent_entrypoints` holds agent *names* where the fixture contract says *paths* | ✅ confirmed |
| **F-12** | 🟢 Info | Tests | The Phase 2 gate only compares 3 fields, leaving gaps unguarded | ✅ confirmed |
| **F-13** | 🟢 Info | Tests | No test covers "Project beats Global" for any agent | ✅ confirmed — this gap is why F-01 survived |
| **F-14** | ✅ Fixed | Scanner | Symlink entrypoint count was inflated | ✅ found & fixed in `eae309f` |

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
make_skill(home/".grok/skills/deploy", "deploy", "GLOBAL copy.")
make_skill(home/"proj/.agents/skills/deploy", "deploy", "PROJECT copy.")
resolve_skill("deploy", "grok", home/"proj", home)
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
return HeadlineState.SHADOWED          # <- "merge" falls through to here
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
agent_entrypoints=tuple(hit.agent_id for hit in entry.hits),   # ("claude", "pi", ...)
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
        return entry.name == name      # entry.name is the FOLDER name
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

## 7. Suggested fix order (when picked up)

1. **F-01** — invert project/global ranks in `antigravity`, `pi`, `grok`, `qoder`,
   `windsurf`, `omp`. *Small, safe, and unblocks honest output for 6 agents.*
2. **F-03** — decide Codex `merge` semantics (product call), then honour it.
3. **F-02** — separate *agent entrypoint resolution* from *canonical grouping for
   inventory*. The grouping belongs in `scanner.py`; the resolver needs the real
   per-agent entrypoint. **This is the significant piece of work.**
4. **F-05, F-06, F-07, F-11** — small, localised fixes.
5. **F-08** — implement `variant_label`; add the missing SHADOWED-on-rank path.
6. **F-09, F-10** — UX decisions; both need care to preserve sandbox isolation.
7. **F-12, F-13** — strengthen the gate: compare more fields, and **add a
   `project_beats_global` golden scenario** so F-01 can never regress silently.

A new golden scenario for F-01 should be added to `tests/fixtures/scenarios.py`,
its expectations to `tests/fixtures/golden/`, and registered in `SCENARIO_NAMES`.

---

## 8. Reproducing this review

The independent review was produced with a read-only `agy` dispatch:

```bash
node ~/.pi/agent/skills/agy-delegate/scripts/relay.mjs \
  --brief <brief.txt> \
  --cd "/Users/corvette/Documents/Projects Coding/Skill Lens" \
  --model "gemini-3.8-flash-high" --effort high --read-only
```

Re-verify the findings above before acting on them — that discipline is what
surfaced the `omp` omission in F-01.

**Current gate (unchanged, still green):** `243 passed`, `ruff check` clean.
