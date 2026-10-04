# Skill Lens 0.2 — Full-Screen TUI

> **Status:** 📋 **Plan only — not implemented.** This document is the agreed
> design for the `0.2` release, subject to the readiness gates in §11. No TUI
> code has been written against it yet.
> It overturns a v1 rule ("no full-screen TUI"), so it is deliberately detailed:
> the point of the plan is that the next person can scaffold the work without
> re-litigating the decisions below.
>
> **Version:** 0.2.0 (major surface change; see [§15 Compatibility](#15-compatibility-and-migration))
> **Supersedes:** the "NO full-screen TUI" rule in `AGENTS.md` §1.5 and
> `SKILL_LENS_SPECIFICATION.md` §5.
> **Author:** maintainer, 2026-10-04.
> **Reviewed:** 2026-10-04 — independent read-only review by Gemini 3.8 Flash
> High via `agy` (`--read-only`, zero violations). Four blocking issues were
> raised and are folded in below: the Home screen's non-existent global
> resolution state ([§8.3](#83-home-screen-layout)), the base-install regression
> from hijacking bare invocation ([§6](#6-technology-choices)), the "held
> snapshot" that did not hold what the UI needs
> ([§5.1](#51-what-the-tui-holds-in-memory-corrected)), and the CI/coverage gap
> ([§6.1](#61-ci-must-test-both-installs-corrected)). One correction to the
> reviewer: `build_diff_report()` already accepts an `index` keyword, so the
> held state is the `DiscoveryIndex` — better than "recompute on demand".
>
> **Second review (orchestrator, same day), against the source.** Three further
> defects were found and folded in: `run_doctor()` *also* lacked an `index`
> parameter and the "only change to core/" claim was wrong
> ([§5.1](#51-what-the-tui-holds-in-memory-corrected)); the live index must come
> from `live_discovery()` or the TCC guard is lost
> ([§5.2](#52-the-session-index-must-come-from-live_discovery)); and Textual
> pins a much newer Rich than this project declares, which can move our pinned
> snapshots ([§6.2](#62-rich-is-a-shared-dependency-coupling-risk)).
>
> **Third review (orchestrator, 2026-10-04), against the source and the repo.**
> Six further defects were found and folded in: the shared display maps were
> homed in `models/enums.py`, which mixes Rich styles into the pure model layer
> ([§8.4a](#84a-sharing-the-presentation-layer--a-refactor-this-plan-must-budget));
> the sharing refactor was under-scoped to two dicts when several diff/why text
> builders are also private to `render.py` (same section); the bare-invocation
> wiring was described but never specified
> ([§7.2](#72-how-bare-invocation-is-wired)); the two `index` defaults contradicted
> each other ([§5.1](#51-what-the-tui-holds-in-memory-corrected)); the §5.1
> entry-point table omitted two builders that already accept `index` (same
> section); and the coverage gate has only three points of headroom
> ([§6.1](#61-ci-must-test-both-installs-corrected),
> [§14](#14-risks-and-mitigations)). A note on repository state before Step 0 is
> in [§11](#11-implementation-phases-phase-7).

> **Fourth review (Codex, 2026-10-04), against code and temporary fixtures.**
> The held index is not a complete snapshot; folder names are not lookup keys
> for every agent; some proposed shared helpers contain Rich markup; worker
> refresh/error behaviour needs an explicit contract; and two malformed-file
> crashes need prerequisite fixes. Dependency, startup-measurement, repository
> state, default-invocation and clipboard claims were also corrected below.
> The earlier review summaries are historical: this revision supersedes their
> claims that the adapter alone provides permission guards and that Textual
> pins Rich exactly. The finding checklist is in §20.

> **Q9 confirmed by the maintainer, 2026-10-04:** use Option 1 for 0.2.
> Catalog, skill contents, settings and diagnostic inputs remain fixed until
> explicit refresh (`r`). This settles the remaining behaviour choice; the
> engine prerequisites and implementation gates still apply.

> **Implementer handoff:** [§21](#21-step-0-implementation-contract) specifies
> Step 0 types, function signatures, files and acceptance tests.
> [§22](#22-assignments-for-the-implementer) is the ordered assignment list.
> Start with P1; complete and review each gate before the next assignment.

---

## 1. Purpose — why we are doing this

Skill Lens today is a **line-oriented CLI**: you run a command, it prints a
report, it exits. That is excellent for scripts and CI, and it is what `0.1.x`
ships. But it makes the tool hard to *explore*.

Concretely, the three questions the tool exists to answer are all **relational**:

1. *What skills exist, and which agents can see them?*
2. *Why is Claude running an old global copy while Codex warns its context is full?*
3. *Is this a shortcut to my shared library, or a local copy someone edited?*

Every one of those is a follow-up question. Today the user answers them by
chaining commands by hand:

```console
$ skill-lens scan                       # spot a name
$ skill-lens why supabase --agent claude   # retype the name
$ skill-lens diff supabase                 # retype the name again
$ skill-lens compare --agent claude --agent codex
```

Each step is a fresh process, a retyped argument, and lost context. For a
developer with 80+ skills across 10 agents, the tool tells them the answer but
gives them no way to *browse* the answers.

**The purpose of 0.2 is to add a browsing layer** — a full-screen terminal UI
you can open once and navigate — **without weakening** the guarantees that make
the CLI trustworthy: read-only, offline, deterministic, JSON-first.

---

## 2. Vision — what 0.2 feels like

> **"Open Skill Lens once, and wander through your skills."**

Picture the experience:

- You type `skill-lens` (with no arguments) and a full-screen interface opens.
- The **left side** lists every skill on the machine, grouped by scope, marked by
  **health** (`*` valid, `x` malformed). It shows **no resolution state** here,
  and that is deliberate — see [§8.3](#83-home-screen-layout).
- You press the **arrow keys** to move through the list. A **right panel**
  previews the highlighted skill: which agents reach it, its canonical path, its
  hash.
- Pressing **Enter** on a skill opens its detail view — the same information
  `why` prints today, but navigable, with one entry per agent.
- Pressing **`d`** on a skill opens the unified diff of its variants.
- Pressing **`c`** opens the two-agent comparison view, with both agents chosen
  from a picker.
- Pressing **`J`** displays the raw JSON of whatever you are looking at.
  Clipboard support is deferred; 0.2 adds no copy action.
- Pressing **`?`** shows a help overlay; **`q`** quits.

The whole thing is **the existing reports, made navigable**. It is not a new
engine and it is not a new source of truth. Think of it as wrapping the CLI's
already-computed answers in a window you can scroll through, the way a file
manager wraps `ls`, `stat` and `diff`.

**Public report data stays the same.** The TUI reads the same frozen report
models as JSON output. Internal session inputs may need new in-memory types
under the chosen consistency policy (§5.1).

---

## 3. The core decision (and what it costs)

A full-screen TUI needs a library that takes over the terminal: raw key input,
alternate screen buffer, layout and re-rendering. Rich alone does not do this.
The standard choice in the Python world is **Textual** (same authors as Rich),
which is why the v1 rule named it explicitly.

**Decision:** add **Textual** as an *optional* dependency and ship a new
`tui` surface behind it. Keep every existing explicit command unchanged; bare
invocation follows the TUI/fallback rules in §7.

### What this changes about the project's rules

- `AGENTS.md` rule 5 said *"NO full-screen TUI (Textual). Line-oriented CLI
  only."* — **this plan lifts that ban** for 0.2. The rule is rewritten to say
  the line-oriented CLI stays the primary **interface** (every command, flag,
  JSON shape and exit code is unchanged), while bare `skill-lens` becomes the
  default **entry point** into the UI. `--plain`, a non-TTY stdout and a
  missing Textual all keep the old behaviour reachable.
- The specification's "Forbidden in v1" list is amended the same way.

### What this must **not** change

These guarantees are load-bearing and survive verbatim:

| Guarantee | Why it must survive |
| --- | --- |
| **100% read-only** | The TUI must not add a single write. It is a viewer. |
| **Offline / no network / no telemetry** | Textual is local; nothing new phones home. |
| **Deterministic** | Same inputs, same core reports; the TUI does not invent resolution rules. |
| **JSON-first / models are the source of truth** | The TUI consumes the frozen dataclasses, never invents fields. |
| **Provenance over hallucination** | Every screen shows the same `rule_id` / `evidence` the CLI does. |
| **No real `$HOME` in tests** | TUI tests use `--sandbox` / monkeypatched `HOME` like everything else. |

---

## 4. Goals and non-goals

### Goals

1. A `skill-lens tui` command (and bare `skill-lens`) that opens a full-screen,
   keyboard-driven interface.
2. Browse skills from `scan`; drill into a skill's resolution (`why`), variants
   (`diff`), and any agent's view of it.
3. Compare two agents (`compare`) from inside the UI.
4. View `doctor` findings in a navigable list that jumps to the offending path.
5. Preserve existing explicit commands, JSON shapes, output and exit codes for
   supported inputs. The two malformed-input crashes in §11 are intentional
   robustness fixes; bare invocation changes as specified in §7.
6. Keep the TUI **presentation-only**: no computation that the CLI does not
   already do.

### Non-goals (explicitly out of scope for 0.2)

- ❌ **No editing, installing, moving, or deleting skills.** Read-only forever.
- ❌ **No file watching / automatic background refresh** in 0.2. `r` requests
  a complete new snapshot of catalog and report inputs, as defined in §5.1.
- ❌ **No config file, themes marketplace, or plugin system** for the TUI.
- ❌ **No mouse-first design** — keyboard is the contract; mouse is a bonus.
- ❌ **No invented skill facts or changed public report fields.** Session
  generation/loading/error state is presentation state, not a new skill fact.
- ❌ **No Windows support** (unchanged from v1).

---

## 5. Architecture — where the TUI sits

The codebase already has the right shape for this. The split is:

```text
skill_lens/
├── core/              # report logic + read-only file access (no terminal/Rich)
├── models/            # the data shapes, with to_dict() for JSON
├── presentation/      # (new) shared, Rich-free display maps + plain-text builders
├── render.py          # Rich line-oriented presentation  ← existing
└── (new) tui/         # Textual full-screen presentation  ← this plan
```

The TUI is **a third presentation layer beside `render.py`**. It must obey the
same rule `render.py` does: *take an already-computed model, and print nothing
else.*

```text
            ┌─────────────┐
            │   core/     │  discovery, resolver, diff, doctor, compare
            │ (read-only) │  → frozen report dataclasses
            └──────┬──────┘
                   │ same models
        ┌──────────┴───────────┐
        ▼                      ▼
  render.py                tui/
  (Rich, line-oriented)    (Textual, full-screen)
        │                      │
        ▼                      ▼
   scan/why/diff/…          interactive screens
```

**The one architectural rule for this phase:** `tui/` may import from `models/`,
`core/` and the new `presentation/`, and must **not** duplicate
resolution/diff/compare logic — nor the display formatting that `render.py` and
`tui/` share through `presentation/`
([§8.4a](#84a-sharing-the-presentation-layer--a-refactor-this-plan-must-budget)).
If a screen needs a value, that value comes from an existing model or it is not
shown.

### 5.1 What the TUI holds in memory (corrected)

An earlier draft implied the UI could drive itself from a held `ScanReport`.
**It cannot**, and this section replaces that:

- `ScanReport` (`core/scanner.py`) carries summary counts and `ScanEntry` rows —
  name, scope, parse status, paths, hash. It holds **no file contents and no
  discovery index**.

What each entry point already accepts:

| Entry point | `index` parameter today? |
| --- | --- |
| `build_scan_report()` — `core/scanner.py` | ✅ already |
| `resolve_skill()` — `core/resolver.py` | ✅ already |
| `build_diff_report()` — `core/diff.py` | ✅ already |
| `build_compare_report()` — `core/compare.py` | ✅ already |
| `build_doctor_report()` — `core/doctor.py` | ✅ already |
| `run_compare()` — `core/compare.py` | ❌ builds its own via `live_discovery()` |
| `run_doctor()` — `core/doctor.py` | ❌ builds its own via `live_discovery()` |

Two live wrappers lack the parameter. Adding it is useful plumbing, but is not
enough to guarantee a frozen session. The exact types, signatures, capture
algorithm and acceptance tests are specified in [§21](#21-step-0-implementation-contract).

Note *which* two: only the `run_*` **live wrappers** lack it. Their `build_*`
counterparts already accept `index=`, so the TUI could call those with a held
index today — the new parameter exists so the **CLI entry points** can also be
driven from a held index, not because the builders need it. That narrows the
change but does not remove it.

**Session state** (Q9: all report inputs frozen until explicit refresh):

```text
SessionState
├── generation: int        ← identifies one published session
├── home:  Path
├── cwd:   Path
├── registry: agent definitions
├── index: FrozenDiscoveryIndex ← tuple-based captured catalog
├── inputs: captured file contents, settings and diagnostic metadata
├── scan:  ScanReport       ← derived from the index, cached for the list
├── doctor: DoctorReport    ← computed before publication
└── reports: UI-owned cache keyed by view + lookup arguments + generation
```

- The index is mutable today (`entries` and `unreadable_roots` are lists). Publish
  the tuple-based `FrozenDiscoveryIndex` defined in §21; build replacements separately.
- Passing `index=state.index` avoids repeating **discovery**. It does not avoid
  all filesystem walks or reads: diff lists, reads and hashes each compared
  copy; resolution rereads agent settings; doctor rereads the installer lock.
- Reproduced with a held index: a diff included changed text with old hashes,
  Claude switched `ACTIVE` → `DISABLED`, and doctor changed its lockfile finding,
  all without refresh. A cached `ScanReport` cannot prevent these effects.
- The `compare` and `doctor` wrappers accept keyword-only `index` and `registry`
  inputs, defaulting to `None`. Existing calls follow the same live discovery
  path. Doctor is built during capture and stored, rather than rerun on navigation.
- Core scope includes the two robustness fixes in §11, the shared identity
  helper in §8.4, and the input-capture changes required by Q9. No longer claim
  that two wrapper parameters are the only core changes. Existing public JSON
  shapes and supported-input behaviour remain unchanged.

**Locked contract — Option 1: freeze all report inputs until `r`.**

- Capture the catalog, required skill file contents/fingerprints, agent settings,
  installer-lock input and diagnostic metadata in memory for one generation.
  Parsed metadata, hashes and diff text must describe the same captured content.
- Derive lazy reports through core functions using those captured inputs.
  Opening an unvisited view must not read newer skill/config content or probe
  current link/path state. Previously missing or unreadable inputs keep their
  captured status until refresh; the app does not silently retry them on view.
- Edits, deletions, additions and setting changes made elsewhere after capture
  do not change any screen in that generation. They appear only after `r`
  successfully publishes a complete replacement, following §9.1.
- Keep the previous snapshot usable while refresh runs. Replace catalog, inputs
  and report caches together; a failed or superseded refresh cannot partly
  replace the displayed snapshot. Caches are keyed by view arguments and
  generation, and are cleared when a replacement is published.
- Use in-memory inputs only: no snapshot directory or database. Capture is
  specific to the TUI; existing CLI commands keep their live-read behaviour.
  Internal capture types may be added without changing public report fields.

**Step 0 gate:** implement the API and read boundaries in §21, including scanner
link counts, path-display decisions and path-dependent doctor checks. After a
snapshot is published, assert that all
view/report navigation uses captured inputs. Change skill contents, settings
and the lockfile; add/delete skills; verify unchanged reports before `r` and
updated reports after a successful refresh.

Capture cannot promise an atomic picture of an externally changing filesystem:
detect inconsistent reads during capture and require retry/refresh rather than
publishing conflicting fingerprints and text. Test changes during capture and
failed/superseded refreshes as well as ordinary edits between views.

### 5.2 The session index must come from `live_discovery()`

**Rule:** use `live_discovery()` as the session entry point, matching the live
`doctor` and `compare` wrappers. It resolves the effective home through
`paths.py` and delegates to `discover()`. Apply `--sandbox` and validate `--cwd`
through the existing CLI helpers before starting any worker.

The permission guards actually live in `discover()` and its filesystem helpers;
the adapter does not add a separate guarded walk. Calling `discover()` directly
does not inherently lose those guards, but bypasses the agreed environment
entry point. Tests must prove sandbox isolation and unreadable-root reporting
through the TUI's actual launch path, rather than merely checking an import.

The new `index` parameters default to `None`. When `index is None` the function
calls `live_discovery(...)` itself — that is today's code path verbatim, so the
CLI is untouched and `--sandbox` keeps working because `live_discovery()` is what
resolves `paths.home()`. (An earlier draft wrote "default to `live_discovery(...)`";
a function call cannot be a Python default argument evaluated per call, so the
sentinel is `None` and the call happens inside the function.)

---

## 6. Technology choices

| Concern | Choice | Rationale |
| --- | --- | --- |
| TUI framework | **Textual** (optional extra) | Same maintainers as Rich; batteries-included widgets, CSS-like layout, async event loop. |
| Dependency shape | `[project.optional-dependencies] tui = ["textual>=<floor>"]`; the `dev` extra also gets `textual` | Keeps the base install lean while keeping the coverage gate able to measure `tui/`. |
| Rendering | Textual widgets over existing models | No new formatting logic where avoidable. |
| Data access | Core capture service, stored scan/doctor, lazy snapshot report services | Reuses the tested engine and prevents live reads during browsing. |
| Key handling | A small keymap module | Testable in isolation; documentable in one place. |

### Why optional, not required

The base tool must keep working for scripts and CI on a machine with no Textual.
The two invocations answer different requests, so they degrade differently:

| Invocation | Textual missing | Why |
| --- | --- | --- |
| `skill-lens tui` (explicit) | Plain-English install hint, **exit `2`** | The user explicitly asked for something that is not installed — that is a usage error. |
| bare `skill-lens` | **Help text + a one-line tip**, **exit `0`** | The user did not ask for the UI, so the tool must not fail. |

The second row matters most: a plain `pip install skill-lens-cli` must never
leave the most basic command broken. Neither path prints a traceback.

### 6.1 CI must test both installs (corrected)

`pyproject.toml` enforces `fail_under = 90` branch coverage, and CI runs macOS +
Linux × Python 3.11–3.14. Adding `skill_lens/tui/` therefore requires:

1. **The `dev` extra gains `textual`**, so `pip install -e ".[dev]"` in CI can
   import *and measure* `tui/`. Without this, `tui/` is unimportable or skipped
   and the coverage gate fails outright.
2. **A second, lean CI lane** that installs the base package *without* the extra
   and asserts both fallback paths (bare → help/exit `0`, `tui` → hint/exit
   `2`). Otherwise the missing-Textual guard is never executed and rots
   unnoticed.
3. **The margin is thin.** The 2026-10-04 review measured **92.67%** coverage
   with branch tracking enabled against the **90%** floor, so a new `tui/`
   package has less than three points of headroom. Budget for it: factor keymap,
   formatting and session-state logic out of widgets so it is unit-testable
   *before* Step 2 lands, not after the gate goes red.

### 6.2 Rich is a shared dependency (coupling risk)

Textual and Skill Lens both depend on Rich. Verified on 2026-10-04 against
[Textual 8.2.8's published metadata](https://pypi.org/pypi/textual/8.2.8/json):

```text
textual 8.2.8  →  requires  rich>=14.2.0
this project   →  declares  rich>=13.0.0   (uv.lock pins 15.0.0)
```

Three consequences:

1. **The combined requirements raise the effective floor to Rich 14.2.0**
   for `[tui]`; Textual does not require exactly 15.0.0. The current lock's
   15.0.0 already satisfies both. Keep the base declaration separate from the
   extra's combined constraints; do not raise the base floor merely because
   an optional dependency needs more. Re-check metadata when selecting Textual.
2. **Our pinned output can move for an unrelated reason.** There are 17 plain-text
   Rich snapshots in `tests/fixtures/snapshots/` and 16 JSON goldens. A
   transitive constraint from an *optional* feature could change `render.py`'s
   output and fail our own snapshot gate, for a cause that has nothing to do with
   the TUI. **No test currently asserts that installing `[tui]` leaves existing
   output byte-identical** — one must be added.
3. **Select the current stable floor, then lock the resolved version.**
   `textual>=0.80.0` is an unnecessarily old minimum, not an exact pin; it also
   permits 8.x. The current verified release is 8.2.8. Re-check at scaffolding
   and each release ([§19 Q2](#19-decisions)).

---

## 7. Command surface

New and changed commands:

| Invocation | Behaviour |
| --- | --- |
| `skill-lens` (no args) | **Changes** from printing help to opening the TUI. ✅ *Decided (Q1).* If Textual is absent, prints help + tip instead — never a hard failure. |
| `skill-lens --plain` | Prints the help text instead of opening the TUI — the escape hatch for scripts and old terminals (✅ decided, Q4). |
| `skill-lens tui` | Explicitly opens the TUI (same as bare invocation). |
| `skill-lens tui --sandbox <dir>` | Opens the TUI against a mock `$HOME`. |
| `skill-lens tui --cwd <dir>` | Opens the TUI with a chosen working directory. |
| All existing commands | **Unchanged**, still line-oriented, still `--json`. |

> **Decided (Q1):** bare `skill-lens` opens the TUI. Scripts, pipes and
> non-interactive shells use `--plain`, which prints the help text and exits.
> This keeps the friendly default while leaving an explicit escape hatch.
> (See [§19](#19-decisions).)

### 7.1 Exit codes from the TUI

Phase 6 established an exit-code contract and `--fail-on`. An interactive app
needs an explicit answer, so it is decided here:

- **`skill-lens tui` exits `0` on a normal quit**, whatever the findings were. An
  interactive browser that a human drove to completion is not a gate, and making
  the quit key raise a non-zero status would surprise anyone who ran it from a
  shell expecting an app.
- **CI must keep using the line commands** (`doctor --fail-on error`,
  `scan --fail-on warning`). That is the supported way to fail a pipeline, and
  this decision does not weaken it.
- A crash still exits non-zero (`3`, the reserved internal-fault code), so a
  genuinely broken UI is not silently reported as success.
- `skill-lens tui` deliberately has **no `--fail-on`**: there is no threshold for
  a human to cross on their way out.

### 7.2 How bare invocation is wired

The bare-invocation change is CLI mechanics, not UI, and an earlier draft
described the behaviour without saying how it is achieved. Today the app is
declared with `no_args_is_help=True` and a `@app.callback()` that only handles
`--version`; that combination prints help when no arguments are given. Opening
the TUI instead needs three concrete edits in `cli.py`:

1. Set `no_args_is_help=False` on the `Typer` app, and
   `invoke_without_command=True` on the callback, so the callback runs even with
   no subcommand.
2. Add a root `--plain` flag on the callback.
3. Inside the callback, decide in this order:
   - `--version` has already short-circuited (it is `is_eager`).
   - if `ctx.invoked_subcommand is not None` → a real command was given; do
     nothing and let Typer dispatch it.
   - else if `--plain` was passed, or `not sys.stdout.isatty()` → print help and
     exit `0` (the fallback path).
   - else check whether Textual is absent; if absent print help plus the
     one-line install tip and exit `0`.
   - if present, import the TUI lazily and launch through the §9.1 fault boundary.
     An unrelated import/launch failure is an internal fault (`3`), not a false
     claim that Textual is missing. The explicit `tui` command uses the same
     boundary, with exit `2` only for the missing-extra/usage case.

No existing test pins bare-invocation behaviour — the CLI tests all pass an
explicit subcommand — so this is additive. `--help` and the packaging smoke test
(`skill-lens --help`) are unaffected, because neither is a bare invocation.

---

## 8. Screens and navigation

### 8.1 Screen map

```text
Home (Skill list)
 ├── Skill detail ──┬── Resolution per agent (the `why` view)
 │                  ├── Variant diff (the `diff` view)
 │                  └── Raw JSON (the `--json` view)
 ├── Agents ────────┴── Agent detail (policy, evidence, roots)
 ├── Compare ────────── pick two agents → comparison table
 ├── Doctor ─────────── findings list → in-app jump to a skill
 └── Help overlay (?)
```

### 8.2 Keymap (draft)

| Key | Action |
| --- | --- |
| `↑` / `↓` / `j` / `k` | Move selection |
| `Enter` | Open / drill in |
| `Esc` / `Backspace` | Back |
| `Tab` | Move focus between panes |
| `/` | Filter the current list |
| `a` | Cycle the agent filter |
| `d` | Open diff for the selected skill |
| `c` | Open compare |
| `J` | Toggle raw JSON for the current view |
| `r` | Request a new catalog/session |
| `?` | Help overlay |
| `q` / `Ctrl-C` | Quit |

### 8.3 Home screen layout

**There is deliberately no resolution-state column here.** `ScanEntry`
(`core/scanner.py`) has no such field: `ACTIVE` / `SHADOWED` / `AMBIGUOUS` are
computed **per agent** by `resolve_skill()`, and one skill can legitimately be
active for Claude, shadowed for Codex and unsearched for Grok simultaneously.
Inventing a single global state for the list would put resolution logic inside
the TUI — precisely what [§5](#5-architecture--where-the-tui-sits) forbids. The
list shows what `scan` actually knows: **scope** and **parse status**. Resolution
states appear only in the detail view, where an agent is chosen
([§8.4](#84-skill-detail-the-why-view-made-navigable)).

```text
┌ Skill Lens ─────────────────────────────────────────────── ? help  q quit ┐
│ Skills (83)                    │ supabase                                  │
│                                │ Scope:    Global                           │
│ ▸ * agent-browser   Global     │ Path:     ~/.agents/skills/supabase        │
│   * supabase        Global     │ Agents:   Claude, Pi, Grok, Qoder (4)      │
│   x imagegen        System     │ Hash:     sha256:7f83b1…                   │
│   x broken-skill    Project    │ Parse:    valid                            │
│                                │ Variant:  B                                │
│                                │ ────────────────────────────────────────  │
│                                │ Enter: detail   a: agent   d: diff         │
└────────────────────────────────────────────────────────────────────────────┘
Detected: Codex, Claude, Antigravity, Pi, Grok, Qoder, Windsurf           0.2.0
```

* `*` = parse status valid, `x` = invalid (malformed YAML / missing description).
* `a` cycles an agent filter. **Only while an agent is selected** does the list
  gain a per-agent resolution mark, produced by calling `resolve_skill()` for
  that *one* agent — never for all ten at once (which would also blow the startup
  budget in [§9](#9-data-flow-and-performance)).

### 8.4 Skill detail (the `why` view, made navigable)

`ResolutionReport` resolves **one skill for one agent**, so the screen is built
around an explicit agent selector rather than pretending one report covers all:

- A horizontal **agent strip** lists every agent that reaches this skill (from
  `ScanEntry.agents`), with the current one highlighted.
- `Tab` / `Shift+Tab` move between agents; each switch requests that agent's
  report under the session policy in §5.1 and re-renders in place.
- Below the strip, one collapsible block per candidate copy, in the same order
  and with the same `rule_id` / `evidence` fields the CLI prints.
- Colours and marks come from the **shared** state-mapping tables (see below) so
  the two layers can never drift.
- A skill reached by **no** agent (a project-local skill, say) shows a
  plain-English explanation in place of the strip, not an empty bar.

**Selection is an installation, not just a name.** Key Home rows by the existing
canonical path, and retain the selected discovery entry. `ScanEntry.name` is
normally the folder name; it is not a universal resolver key. For example,
`.codex/skills/folder-key/SKILL.md` with `name: declared-key` appears in scan as
`folder-key`, but `resolve_skill("folder-key", "codex", ...)` finds nothing.

Before resolving, a core helper derives the lookup name from the selected
entry's existing `ParseResult` and the agent's `identity_source`, using the
resolver's existing identity rules. The TUI calls that helper; it must not
reimplement the rule. Keep the folder name as the key for the existing `diff`
command, which groups on `DiscoveredEntry.name`. The detail report's
`skill_name` and raw JSON use the agent's actual lookup name. Select the
candidate matching the chosen installation when several copies resolve.

Step 0 must test directory names differing from declared names for directory-,
frontmatter- and either-name agents, plus invalid/missing frontmatter and
multiple copies. It must preserve existing `why`/`diff` lookup behaviour and
public JSON fields. For either-name agents, use the folder name already shown
by scan; for frontmatter-only agents, use the existing resolver's declared-name
fallback. Unparsed entries keep the resolver's existing entry-name fallback.

### 8.4a Sharing the presentation layer — a refactor this plan must budget

Two separate problems live here, and an earlier draft fixed only the first.

**Problem 1 — the maps are private.** `_STATE_STYLE` and `_STATE_MARK` currently
live in `render.py` as **private** module-level dicts. That leaves two bad
options: import underscore-prefixed names from another module (fragile, and they
are presentation internals), or copy them into `tui/` — which is the duplication
§5 forbids, and which will drift. The same is true of `_SCOPE_LABEL`, which the
Home preview needs in order to render `Global` / `Project` / `System` / `Plugin`.

**Problem 2 — the sharing is wider than two dicts.** §10 forbids `tui/` from
importing `skill_lens.render`, because a stray `Console().print()` corrupts the
alternate screen buffer. But the unified-diff text layout the Diff screen must
show lives *only* in `render.py` as private helpers — `_unified_text`,
`_range_text`, `_copy_heading`, `_no_differences_message`, `_needs_listing` —
plus `_short`, the path collapser. If the TUI cannot import them it must
re-implement them, which is exactly the drift the §14 risk table warns about. An
earlier draft budgeted only the two dicts and missed this.

**Problem 3 — some helpers are not plain text.** `_copy_heading()` calls
`rich.markup.escape()` and emits tags such as `[dim]`; `_no_differences_message()`
also emits Rich tags. Moving them verbatim violates the proposed package's
no-Rich rule. Returning `str` alone does not make a helper formatting-neutral.

**Decision:** create a small presentation-neutral package
`skill_lens/presentation/`:

```text
skill_lens/presentation/
├── __init__.py    # re-exports the shared names
├── state.py       # STATE_STYLE, STATE_MARK, SCOPE_LABEL
│                  #   HeadlineState/Scope → style string, glyph, label
└── text.py        # shared plain text, heading parts, unreadable reasons,
                   # range_text(), unified_text(), needs_listing()
                   #   no Rich imports, markup tags or Console
```

- Move genuinely plain helpers directly. Split markup-producing helpers into
  shared plain content/heading parts and renderer-specific styling. Include
  `_UNREADABLE_REASON` / `_unreadable_reason`, which headings depend on.
- Shared content keeps names, paths and descriptions unescaped. `render.py`
  owns Rich escaping at its output boundary; Textual widgets display untrusted
  strings with markup disabled and apply styles separately. Do not copy Rich's
  escaping implementation into `presentation/` to evade the import rule.
- `render.py` imports from `skill_lens.presentation` and retains Rich styling,
  escaping and Console-bound glue (`Table`, `Panel`, `_print_notes`).
- `tui/` imports from `skill_lens.presentation` — **never** from `render.py`.
- The package holds **no `rich` import**. Style names remain constants; plain
  text/heading parts carry no embedded markup. Formatting adapters preserve
  the existing visible output, including colour, wrapping and punctuation.
- `models/` is deliberately **not** the home. `models/__init__.py` states the
  rule — *"Presentation (Rich) is always a layer on top of these models — never
  the other way around"* — and `STATE_STYLE` holds Rich style strings. Putting
  them in `models/enums.py` would invert the dependency AGENTS.md rule 4
  enforces.

This is an extraction plus a behaviour-preserving formatting refactor, not a
file move. Budget both into Step 0; all 17 snapshots must remain unchanged.
Test literal markup-looking names, descriptions and paths in both adapters.
See [§19 Q7/Q8](#19-decisions).

### 8.5 Empty and error states

Every screen must handle "nothing found" the way the CLI does — as an answer,
not a crash:
- No agents detected → explanatory panel, still usable.
- No copies of a skill → a message, no traceback.
- Unreadable roots (macOS TCC) → listed as `unreadable`, scan continues.
- Any unexpected internal error → a plain-English panel with in-memory details;
  no log file and no terminal traceback. Exit behaviour is specified in §9.1.

### 8.6 Doctor — what "jump to path" actually does

"Jump" means **select inside the app only**. It never launches an editor, never
shells out, never opens a file — `subprocess` is forbidden outright.

- `Enter` on a finding selects the matching skill in the Home list, when the
  finding's path corresponds to a known entry.
- When the path is **not** in the catalog (a dangling symlink, an unreadable
  root, a cycle), the panel explains that there is no matching catalog entry and
  displays the path as literal text. There is no clipboard action in 0.2 (Q3).

### 8.7 Compare — the picker and its edge cases

- `c` opens a two-column picker: pick agent A, then agent B. Both columns list
  only ids the registry actually defines.
- Choosing the **same agent twice** is rejected inline ("Pick two different
  agents."), mirroring the CLI's `--agent`-twice check.
- **Fewer than two agents detected** → an explanatory panel naming what was
  found and how many more are needed; no crash.
- Confirming uses `snapshot_compare(state.current, a, b)`, which passes both
  frozen index and captured registry to `run_compare()`. An unknown id uses
  the CLI error wording in an inline message; ordinary in-app input errors do
  not change the normal-quit exit contract in §7.1.

### 8.8 What `J` shows on each screen

`J` uses `models.dumps(report.to_dict())` (or the existing agents payload),
exactly the CLI serializer. Byte equality is asserted for **the same arguments
and inputs**. A later live CLI run may see changed files; it cannot be the
oracle for an earlier session. Agent detail uses its translated lookup name
from §8.4, not automatically the Home row's folder name.

| Screen | JSON payload |
| --- | --- |
| Home (list) | full `ScanReport` — same as `skill-lens scan --json` |
| Skill detail | that agent's `ResolutionReport` — same as `why --json` |
| Diff | `DiffReport` — same as `skill-lens diff --json` |
| Compare | `CompareReport` — same as `compare --json` |
| Doctor | `DoctorReport` — same as `doctor --json` |
| Agents | the same list `skill-lens agents --json` emits |

---

## 9. Data flow and performance

- **One published session in memory.** Launch builds the index and scan;
  `r` requests a complete replacement. Input retention, report caches and
  changed-file handling obey §5.1/Q9.
- **Views use captured inputs.** An `index` argument alone saves catalog
  discovery, not diff's file walk or resolution's settings read. The planned
  capture-aware core APIs must eliminate those live reads during navigation.
- **Keep the event loop responsive.** The event loop is the main task that
  handles keys and redraws. Discovery, file capture, diff, doctor, compare and
  resolution from captured settings run in background workers, never key handlers.
- **Measure the complete startup path:** time `live_discovery()`, Q9 input
  capture, `build_scan_report(index=...)`, and first usable list separately and
  together. Hashing happens in discovery's `_build_entry()` / `hash_path()`;
  `build_scan_report()` with a supplied index does not hash skill contents.
  Measuring that last function alone misses the expensive work. Do not claim
  hashing dominates until measurements show it.
- **Benchmark large synthetic lists.** Choose an actual Textual widget and
  record navigation/filtering responsiveness for 600+ entries. Do not assume
  [`ListView`](https://textual.textualize.io/widgets/list_view/) is virtualised:
  it mounts child `ListItem` widgets. Select the
  widget after checking the chosen Textual release and measurements, without
  building a custom list engine merely to meet an invented target.
- **Progress must be honest.** Show an indeterminate "Scanning…" indicator while
  the worker runs; the current discovery API has no incremental skill count.
  Show `N skills` only once known, or if a tested core progress API is explicitly
  budgeted. Keep help, cancellation and quit responsive throughout.
- **Record measurements, not promises.** Step 1 records startup timings for
  reproducible synthetic fixtures. An optional reference-machine measurement is
  a read-only manual check, never a test against real `$HOME`. Record environment
  and fixture size; no unmeasured 1.5s target. UI timing is measured in Step 3.

### 9.1 Background work, refresh and errors

The [Textual worker contract](https://textual.textualize.io/guide/workers/)
requires explicit handling: threads are not stopped like async tasks, UI updates
must return to the main thread, and unhandled worker errors normally terminate
the app with a traceback. Merely adding `@work(thread=True)` is insufficient.

- Each refresh request receives a new generation number. Build its session in
  isolation and publish the whole result on the UI thread. Never mutate the
  currently displayed index while another view uses it.
- Publish only the newest requested generation. A superseded worker may finish
  reading, but its result cannot replace the newer state. Use cancellation
  checks and generation checks together; cancellation alone is not the gate.
- Each view request also carries its arguments/selection and a request number.
  Results update the screen only if generation, request number and current
  selection still match. Leaving a screen prevents its late result updating it.
- A successful refresh clears previous report caches. Preserve selection by
  canonical path when that installation remains; otherwise select a valid row
  or show the empty state. Publish matching scan/report data together.
- Use `call_from_thread()` or thread-safe messages for updates. Workers read
  the validated session home/cwd and do not reset global sandbox state.
- Handle expected conditions (missing skills, unreadable roots, invalid agent
  selection) as ordinary model results or inline messages.
- Set `exit_on_error=False` for workers and handle their error events. An
  unexpected internal fault shows a plain-English error panel, retains details
  in memory and marks the run as failed. Acknowledging/exiting then returns `3`;
  normal quit with no internal fault returns `0`. CLI launch failures also map
  internal faults to `3` without printing a terminal traceback. Add no log file.
- Quit cancels owned work and prevents late updates. Test prompt return with a
  deliberately slow, controlled worker; if core work needs cooperative stopping,
  budget that API before promising prompt quit. Do not claim thread cancellation
  can forcibly stop an ongoing file read.

**Step 2/3 gates:** delay two refreshes so the older finishes last; change
selection while a report loads; leave a loading screen; inject worker and launch
errors; quit during a slow scan. Assert newest-result publication, safe UI
updates, no traceback, responsive navigation and the defined `0`/`3` exits.

---

## 10. Read-only guarantee

The single most important invariant. Enforcement strategy:

1. TUI data comes through `core/`, `models/`, the registry and `presentation/`.
   Textual and read-only standard-library use are allowed; filesystem writes,
   process execution, database and network operations are forbidden.
2. A dedicated AST guard test — written in **Step 2** and gated there, not
   deferred to a cleanup — fails the build if `tui/` reaches for a write.
   Concretely it rejects:
   - imports of `shutil`, `subprocess`, `tempfile`, `sqlite3`, `socket`;
   - `os.remove`, `os.unlink`, `os.rmdir`, `os.rename`, `os.replace`;
   - `open(...)`, `Path.open(...)` or `io.open(...)` with any mode containing
     `w`, `a`, `x` or `+`, including keyword modes; unresolved modes require
     review rather than silently passing;
   - calls to `Path.write_text`, `Path.write_bytes`, `Path.unlink`,
     `Path.mkdir`, `Path.touch`, `Path.rename`, `Path.rmdir`;
   - any `requests` / `httpx` import.

   Check instance calls and imported aliases, not just literal `Path.method`
   spelling. Pair the source guard with before/after fixture checks across
   navigation, refresh, errors and quit. A syntax guard catches known operations;
   it is not proof against every possible indirect write in dependencies.

3. **The guard also bans writes to the terminal**, which the primitive list above
   does not cover. Inside a Textual app the alternate screen buffer belongs to
   Textual; a stray `Console().print()` from `render.py` corrupts the display.
   So the guard rejects, inside `tui/`:
   - any import of `skill_lens.render` (the shared helpers live in
     `skill_lens.presentation`, which `tui/` *may* import);
   - any `rich` import (styling uses Textual; shared content remains neutral);
   - `rich.console.Console` / `Console.print` / `console.print`;
   - bare `print(...)`.

   The TUI renders through Textual widgets only.
4. `--sandbox` semantics carry over exactly: the TUI can be pointed at a mock
   `$HOME`, so a demo can never touch real skills.
5. Mutation-test each guard category, including aliased imports, instance
   `.open(mode="w")`, terminal output and network/process imports. One planted
   banned call proves only that branch, not the entire read-only contract.

---

## 11. Implementation phases (Phase 7)

Numbering continues the existing roadmap. Each step ends with a gate; no step
starts before the previous gate is green.

**Repository state:** the documentation move and original plan already landed
in `d37f218`. The working tree was clean at the 2026-10-04 review. Check actual
Git state before work; there is no pending move to commit.

**Before Step 0 — baseline and two engine fixes (no TUI code):**

- Re-run all four repository checks. The review baseline was 471 passing tests,
  92.67% coverage with branch tracking, clean mypy and lint, but a formatting
  failure in this document's Python example. This revision replaces the examples;
  only a new full gate establishes the current baseline.
- Reproduce each defect in a `tmp_path`/monkeypatched-home regression test:
  `.claude/settings.json` containing `[]` makes `_load_disabled_overrides()`
  raise `AttributeError`; an installer lockfile containing invalid UTF-8 raises
  `UnicodeDecodeError` in `read_json_guarded()` before its JSON handler runs.
- Validate the settings top-level shape before `.get()`; use the existing
  invalid-JSON fallback for non-object JSON. Catch decoding failure at the file
  read boundary and return the existing `ERR_NOT_JSON`, so doctor reports its
  normal invalid-lockfile warning. Preserve valid-input output and report shapes.
- Read Phase 2/4 findings before these narrow fixes. Keep them separate from
  UI plumbing. Passing existing tests does not count as fixing these defects.
- **Gate:** both regressions fail before their fixes and pass after; all four
  checks pass; existing snapshots and goldens remain unchanged. These fixes are
  planned prerequisites, not implemented by this document revision.

### Step 0 — Contracts (no UI code)
- Execute assignments C1–C5 in [§22](#22-assignments-for-the-implementer), in order.
  §21 is the technical contract for the frozen-input core API, cache keys and
  capture/refresh rules. Do not redesign those contracts while implementing.
- Verify the current Textual release and its declared Rich constraints; record
  the intended floor. Dependency declarations and lock changes land in Step 1.
- Add keyword-only `index` and `registry` inputs to **both** `run_compare()` and
  `run_doctor()`, each defaulting to `None`; call `live_discovery()` when
  `index` is `None`
  ([§5.1](#51-what-the-tui-holds-in-memory-corrected), [§5.2](#52-the-session-index-must-come-from-live_discovery)).
- Expose a core installation-to-agent lookup helper using the existing resolver
  identity rules; test the Home → detail mapping in §8.4 without UI code.
- Implement the frozen-input contract in core, with regression tests for edits,
  settings changes, additions/deletions and inconsistent capture reads. All
  views, including first-time visits, use the captured inputs until refresh.
- Create `skill_lens/presentation/`, extract the plain helpers and split the
  markup-producing helpers into neutral content and renderer-specific formatting
  ([§8.4a](#84a-sharing-the-presentation-layer--a-refactor-this-plan-must-budget)).
- **Gate:** existing suite green; `compare --json` and `doctor --json` goldens
  byte-identical for unchanged supported inputs; all 17 render snapshots
  unmoved; full mypy/lint/format/coverage gate green. Name mapping and the selected
  frozen-input contract must pass their new tests before Step 1.

### Step 1 — Optional dependency plumbing
- Add the `tui` extra to `pyproject.toml`, and add `textual` to the `dev` extra
  so the coverage gate can measure `tui/`.
- Add the two-path missing-Textual guard: bare `skill-lens` → help + tip, exit
  `0`; `skill-lens tui` → install hint, exit `2`. Plus the root `--plain` flag.
- Wire the second, lean CI lane that installs without the extra
  ([§6.1](#61-ci-must-test-both-installs-corrected)).
- Add the gate that **[tui] does not change existing output**: install with the
  extra and assert the 17 render snapshots and 16 goldens are byte-identical
  ([§6.2](#62-rich-is-a-shared-dependency-coupling-risk)).
- Measure discovery, any captured inputs, and `build_scan_report(index=...)`
  separately and together on synthetic fixtures; record conditions and timings
  in §9. A reference-machine run is an optional manual read-only measurement.
- **Gate:** base install has zero new runtime deps; both fallback paths asserted;
  plumbing mutation-tested (break each branch, confirm exactly one failure).

### Step 2 — TUI skeleton
- `skill_lens/tui/app.py` — the `App` subclass, screen stack, quit handling.
- `skill_lens/tui/__init__.py` — the `run(...)` entry point the CLI calls.
- A placeholder home screen.
- Implement worker error handling and launch fault → exit `3` from §9.1 here;
  do not defer the exception/traceback contract to polish.
- **The read-only AST guard lands here** ([§10](#10-read-only-guarantee)) — it is
  a gate of this step, not a later cleanup — including the terminal-write bans.
- **Strict `mypy` applies immediately.** `[tool.mypy] files = ["skill_lens"]` with
  `strict = true` means the new package is type-checked from its first commit,
  Textual's `@work(thread=True)` typing included.
- **Gate:** `skill-lens tui --sandbox <fixture>` opens and quits on `q` in a
  headless test (Textual's `run_test()` harness); `mypy` strict clean over
  `skill_lens/`; each read-only guard category is mutation-tested; injected
  worker/launch faults produce no terminal traceback and exit `3`.

### Step 3 — Home / skill list
- Use the Step 0 snapshot service under the §21 contract; render the list + preview
  from `ScanReport` (resolution states only with an agent filter, per §8.3).
- Keyboard navigation, filtering, and an agent filter that uses
  `snapshot_why()` for the one selected agent.
- Run discovery in a worker thread, not on the event loop.
- Add generation checks, per-view request checks, cache invalidation and
  whole-session publication from §9.1. Benchmark the actual list widget.
- **Gate:** navigation tests against fixtures; list stays responsive with a
  large synthetic set; older refresh/report results cannot replace newer ones;
  quit during a controlled slow scan returns promptly without late UI updates.

### Step 4 — Skill detail / resolution view
- Reuse `ResolutionReport`; select the lookup key via the core helper from §8.4,
  with one block per candidate and selection matched to the canonical path.
- Show `rule_id` + `evidence` exactly as the CLI does.
- **Gate:** rendered content matches the model; escaping verified (skill text
  can never inject markup, mirroring the existing rule).

### Step 5 — Diff and JSON views
- `d` opens the `DiffReport` view using the folder-name grouping of the existing
  command and coherent inputs under §5.1; an index alone does not freeze text.
- `J` toggles raw JSON per the mapping in [§8.8](#88-what-j-shows-on-each-screen).
- **Gate:** diff view obeys the same truncation/binary/escaping rules as
  `render.py`; no report mixes old hashes with newly read text; each screen's
  JSON is byte-identical to CLI serialization for the same arguments and inputs.

### Step 6 — Agents and Compare
- Agents screen reading the registry definitions.
- Compare flow per [§8.7](#87-compare--the-picker-and-its-edge-cases).
- **Gate:** unknown-agent handling matches the CLI; same-agent-twice rejected;
  fewer-than-two-agents handled; snapshot service supplies index and registry.

### Step 7 — Doctor screen
- Findings list sorted by severity, with "jump" defined exactly as in
  [§8.6](#86-doctor--what-jump-to-path-actually-does) — in-app selection only.
- **Gate:** severity ordering and message text match the model; a finding whose
  path is not in the catalog explains itself instead of crashing.

### Step 8 — Polish, help, docs
- Help overlay, final keymap, empty/error states.
- Update README, DEVELOPMENT, CHANGELOG, SPEC references.
- **Gate:** full repo gate green, coverage ≥ 90% **with `tui/` measured**.

### Step 9 — Release 0.2.0
- Bump versions, refresh lock, follow `DEVELOPMENT.md` `Releasing`.
- **Gate:** all release checks pass; TUI smoke-tested from the built wheel.

---

## 12. Testing and verification strategy

The existing protocol is strict (100% … well, 90% branch coverage, mutation-tested
gates, snapshot discipline). The TUI must meet it.

| Layer | How it is tested |
| --- | --- |
| Keymap / navigation logic | Pure unit tests, no terminal needed. |
| Screens | Textual's built-in `run_test()` headless harness — drive keys, assert on the rendered tree. |
| Models consumed | Reuse existing golden JSON — assert the TUI reads the same objects. |
| Read-only guard | Source checks for all banned categories plus before/after fixture checks; mutation-test each category (§10). |
| Missing Textual | Test bare help/tip + `0` with interactive stdout, bare non-TTY help + `0`, and explicit `tui` hint + `2` in a true base install. Unrelated import faults must exit `3`. |
| Input consistency | Change skill bytes, settings and lockfile; add/delete skills; assert all views remain unchanged until refresh, then update together. Cover inconsistent capture and failed refresh (§5.1). |
| Lookup identity | Drive Home → detail with folder/declared names differing across identity policies; preserve `why` and `diff` keys. |
| Worker lifetime | Delay/out-of-order refreshes and view results; change selection, leave screens, inject faults and quit during controlled slow work (§9.1). |
| Existing engine defects | Non-object settings JSON and non-UTF8 lockfile regressions must fail before the prerequisite fixes and pass after. |
| Screen behaviour | Textual's `Pilot` API (`app.run_test()`): drive real key presses and assert on widget state, focus and bindings — **semantic, not pixels**. |
| Gate integrity | Any new gate is **mutation-tested** — deliberately broken to prove it fails (the repo's own rule). |

> **No full-screen text-grid snapshots.** An earlier draft of this plan proposed
> pinning plain-text screen exports. That was a bad idea and has been removed:
> CI runs macOS + Linux × Python 3.11–3.14, and full-screen dumps vary with
> terminal size, Unicode cell widths and Textual's own renderer. They would flap,
> and a flapping suite trains everyone to regenerate blindly — the exact habit
> this repo forbids. Behaviour is asserted through `Pilot` instead. The few
> genuinely textual widgets (the diff body, the `why` blocks) reuse the
> **existing** line-oriented snapshot harness, which is already stable.

---

## 13. Documentation changes required

This plan implies edits to the repository's own rules. The list:

| File | Change |
| --- | --- |
| `AGENTS.md` | TUI allowance already landed; default-invocation wording aligned by this revision. |
| `SKILL_LENS_SPECIFICATION.md` | Allowance/roadmap already landed; primary-interface wording aligned by this revision. |
| `docs/archive/PHASE2_FINDINGS.md` | Historical record; the 0.2 amendment already exists. Keep the original findings. |
| `docs/archive/PHASE3_FINDINGS.md` | Historical record; the 0.2 amendment already exists. Keep the original findings. |
| `docs/archive/` | Finished records were moved, not deleted, in `d37f218`; no pending move. |
| `README.md` | Add a short "Interactive mode" section and a roadmap line. |
| `DEVELOPMENT.md` | Phase 7 entry already exists; retain readiness prerequisites and update verified implementation results as steps land. |
| `CHANGELOG.md` | Planned/Unreleased note already exists; record shipped changes only when implemented. |
| `FULL_SCREEN_TUI.md` (this file) | Update as decisions land. |

**Why amendment notes for the findings files:** the repo treats those documents
as permanent, point-in-time records of what was wrong and why. Rewriting them
would destroy provenance, which is exactly what the project forbids elsewhere.
An added note keeps the history honest while marking the rule as since-changed.

---

## 14. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Full-screen snapshots flap across terminals/versions | High | Medium | **Avoided by design**: no text-grid snapshots. Assert via `Pilot`; any narrow snapshot stays pure text and reuses the existing harness. |
| "No system bloat" rule violated by a heavy dep | Medium | High | Optional extra only; base install unchanged; guard message when absent. |
| A write sneaks into the TUI | Low | Critical | Import/AST read-only guard + sandbox-only demos. |
| The TUI drifts from the CLI's answers | Medium | High | TUI reads the same models; no logic duplication; shared display maps **and** text builders via `skill_lens/presentation/` ([§8.4a](#84a-sharing-the-presentation-layer--a-refactor-this-plan-must-budget)). |
| Scope creep into editing/install | Medium | Critical | Non-goals are explicit; read-only guard enforces it. |
| Accessibility / non-interactive shells | Medium | Medium | `skill-lens --plain` forces plain text; a non-TTY stdout falls back automatically. |
| Coverage gate hard to hit for UI code | Medium | Medium | `dev` extra includes `textual` so `tui/` is measured; factor logic out of widgets (keymap, formatting, session state) so it is unit-testable. |
| Coverage headroom is thin (92.67% vs 90% at review) for a whole new package | Medium | Medium | Extract widget logic (keymap, formatting, session state) so it is unit-testable; land tests with each step, never after the gate goes red ([§6.1](#61-ci-must-test-both-installs-corrected)). |
| CI never exercises the base install | Medium | High | Second lean CI lane without the extra, asserting both missing-Textual paths ([§6.1](#61-ci-must-test-both-installs-corrected)). |
| A resolution state leaks into the UI | Medium | High | Only `ScanReport` fields on Home; resolution strictly per-agent in the detail view ([§8.3](#83-home-screen-layout)). |
| Reports mix inputs from different times | High | High | Capture all report inputs in core; use them until explicit refresh; test edits between views and inconsistent capture (§5.1). |
| Home opens a nonexistent agent lookup name | Medium | High | Key selection by canonical path; core identity helper translates names; fixture with differing folder/declared names (§8.4). |
| An older worker overwrites a newer screen | Medium | High | Generation and request checks; whole-session publication; controlled out-of-order tests (§9.1). |
| Malformed settings/lockfile abort browsing | Medium | High | Reproduce and fix both engine crashes before Step 0; retain regression tests (§11). |

---

## 15. Compatibility and migration

- **CLI:** existing explicit commands, flags, JSON shapes and supported-input
  output/exit codes are unchanged. Malformed-input crashes are fixed in the
  prerequisites; they are not output formats to preserve.
  This is a **major** version bump because the *surface* grows, not because
  anything breaks.
- **Scripts:** existing explicit command invocations are unaffected for supported
  inputs. `--json` output is byte-identical for the same inputs.
- **No-arg invocation:** changes to open the TUI (✅ Q1). `--plain` restores the
  old help output; a non-TTY stdout *and* a missing Textual both fall back to
  help automatically — so a base install never regresses.
- **Install:** base install unchanged; `[tui]` extra is opt-in.
- **Removing the extra:** keeps explicit CLI commands available. Bare invocation
  still follows the new help/exit-`0` fallback, rather than claiming it restores
  every detail of 0.1.x bare invocation.

---

## 16. Launch flow (implementation reference)

This is control flow, not runnable Python. Implement it with typed functions;
§7 and §9.1 define the observable behaviour and fault handling.

```text
Root callback:
  --version / --help             → existing eager output
  explicit existing subcommand   → existing dispatch
  bare --plain or non-TTY stdout → help, exit 0
  bare with Textual absent       → help + install tip, exit 0
  bare with Textual present      → validated launch below

Explicit tui command:
  apply sandbox and validate cwd using existing CLI helpers
  Textual absent                 → install hint, exit 2
  Textual present                → validated launch below

Validated launch:
  lazily import TUI (other import errors are internal faults)
  start responsive app; capture complete frozen-input session in worker
  update screens only with matching generation/request results
  expected empty/unreadable/input state → model result or inline explanation
  unexpected worker fault        → error panel, details in memory, failed run
  unexpected import/launch fault → plain-English CLI error, exit 3
  quit / acknowledge fatal panel → clean terminal restoration; 0 or 3 per §9.1
```

Detect missing Textual specifically (for example, check its module availability
before importing the UI). A broad `except ImportError` around the entire TUI
would mislabel an implementation defect as a missing optional installation.
Tests exercise both cases.

---

## 17. Success criteria

0.2 is done when:

1. Bare `skill-lens` (and `skill-lens tui`) opens a navigable interface on macOS
   and Linux; `skill-lens --plain` prints help and exits.
2. Existing explicit commands retain supported-input behaviour, JSON shapes and
   snapshots. The two malformed-input regressions pass after their fixes.
3. Skill facts come from existing report/discovery data; session status is
   presentation state, and internal capture types do not change public JSON.
4. Read-only source guards and before/after navigation/refresh/error fixture
   checks pass; every guard category has a failing mutation test.
5. Base install pulls **zero** new runtime dependencies, and a base install
   running bare `skill-lens` prints help rather than failing.
6. Both CI lanes pass: full (`[dev]` + `tui`, under coverage) and lean (base
   install, missing-Textual paths).
7. The full repository gate is green, coverage ≥ 90% **including `tui/`**, and
   every new gate is mutation-tested.
8. No resolution state is displayed anywhere the models do not define one.
9. Installing `[tui]` leaves all 17 render snapshots and 16 goldens
   **byte-identical** — the optional feature cannot move the existing output.
10. The session index comes from `live_discovery()` with validated home/cwd;
    actual launch-path tests verify sandbox isolation and unreadable roots.
11. `skill-lens tui` exits `0` on a normal quit, `3` on an internal fault, and
    offers no `--fail-on` ([§7.1](#71-exit-codes-from-the-tui)).
12. `tui/` imports neither `render.py` nor `rich`; all shared display logic comes
    from `skill_lens/presentation/`
    ([§8.4a](#84a-sharing-the-presentation-layer--a-refactor-this-plan-must-budget)).
13. All report inputs remain frozen until `r`: edits/additions/deletions and
    settings/lockfile changes do not affect any view before refresh, and appear
    together after a successful refresh. Consistency tests cover first-time views.
14. Home rows with differing folder/declared names open the correct per-agent
    report; diff keeps the existing folder-name grouping.
15. Superseded refreshes and report requests cannot overwrite current state;
    worker/launch fault handling and slow-scan quit tests satisfy §9.1.
16. Startup measurements cover discovery, frozen-input capture and
    scan construction; list responsiveness is measured with the chosen widget.

---

## 18. Glossary (plain English)

- **TUI** — "text user interface": a full-screen app *inside* the terminal, like
  `htop` or `lazygit`, that takes over the window and responds to key presses.
- **CLI** — "command-line interface": typing a command, getting output, and
  exiting. What Skill Lens is today.
- **Textual** — the Python library that makes full-screen terminal apps; made by
  the same people as Rich.
- **Rich** — the Python library Skill Lens uses today to print coloured tables
  and panels, one screen at a time.
- **Read-only** — the tool only looks; it never changes your files.
- **Frozen model / dataclass** — a plain data object that cannot be changed after
  it is created; the single source of truth the UI renders.

---

## 19. Decisions

Q1–Q9 are locked. The maintainer selected Option 1 for Q9: all report inputs
remain fixed until explicit refresh. Step 0 implements that contract; it does
not reopen the behaviour choice.

**Q1 — Bare `skill-lens` opens the TUI.** ✅ *Decided: open the UI.* Typing
`skill-lens` with no command opens the full-screen interface. **Refined after
review:** if Textual is not installed, bare invocation prints help plus a tip
instead of failing — a base install must never regress. `skill-lens --plain` is
the explicit escape hatch (see Q4).

**Q2 — Require the newest stable version of Textual.** ✅ *Decided.* Pick the
latest stable release on the day scaffolding begins. **Refined after review:** the
*floor* goes in `pyproject.toml` (`textual>=X`) so downstream installs are never
hard-pinned, and the *exact* pin is carried by `uv.lock` for reproducible local
and CI runs. Revisit the floor at each release.

**Q3 — `J` only displays the JSON.** ✅ *Decided: display only.* Pressing `J`
shows the raw JSON in the UI; copying to the clipboard is deferred to a later
version. *(The reviewer noted Textual can copy via OSC 52 with no extra
dependency, so a `y` key would be cheap to add — but display-only stands for
0.2.)*

**Q4 — Add a `--plain` flag.** ✅ *Decided: yes.* `skill-lens --plain` forces the
old line-oriented behaviour (printing help rather than opening the UI) for
scripts, pipes and terminals that cannot run a full-screen app. As safety nets, a
non-interactive stdout (not a TTY) *and* a missing Textual both fall back to
help automatically, so a pipe can never hang inside a UI and a base install never
fails.

**Q5 — What exit code does the TUI return?** ✅ *Decided.* `skill-lens tui` exits
`0` on a normal quit regardless of findings, `3` on an internal fault, and has
no `--fail-on`. CI keeps using `doctor --fail-on` / `scan --fail-on`, which
remain the supported way to fail a pipeline. See [§7.1](#71-exit-codes-from-the-tui).

**Q6 — What is the real startup time?** ✅ *Decided: measure it, don't guess.*
The 1.5s figure in an earlier draft was invented and has been removed. Step 1
times discovery, input capture and scan construction on synthetic fixtures and
records the environment; reference-machine timing is an optional manual check.
A truthful progress indicator is mandatory either way
([§9](#9-data-flow-and-performance)).

**Q7 — Where do the shared display maps live?** ✅ *Decided: a new
`skill_lens/presentation/` package.* **Not** `models/enums.py`, which is pure
data; `STATE_STYLE` holds Rich style strings and would invert the model layer's
"presentation on top, never the other way around" rule. `render.py` and `tui/`
both import from `presentation/`; `tui/` still may not import `render.py`. See
[§8.4a](#84a-sharing-the-presentation-layer--a-refactor-this-plan-must-budget).

**Q8 — How wide is the shared-presentation refactor?** ✅ *Decided: share
plain content and display maps, with renderer-specific styling.* Pure builders
move directly; markup-producing helpers are split before extraction. Include
their unreadable-reason dependencies. Rich escaping/styling stays in `render.py`;
Textual uses literal content and separate widget styles. See §8.4a.

**Q9 — What remains fixed until refresh?** ✅ *Decided by the maintainer:
Option 1 for 0.2.* Capture catalog, skill file contents, settings, installer-lock
input and diagnostic metadata in memory. All views use that captured state,
including views opened for the first time. External changes appear only after
`r` successfully publishes a complete replacement snapshot. §5.1 defines the
capture and consistency gates; holding an index alone does not fulfil them.

---

## 20. Readiness review checklist (2026-10-04)

These findings were checked against source; behavioural reproductions used
temporary mock homes. This table records plan corrections, not completed code.

| Finding | Correction / implementation gate |
| --- | --- |
| Held index does not freeze contents, settings or lockfile | Q9 selects complete in-memory input capture; §5.1/Step 0 require its core scope and consistency tests. |
| Folder name can fail as an agent lookup key | §8.4 defines selection and core name translation; Step 0 tests differing names. |
| Proposed shared helpers use Rich escaping/tags | §8.4a budgets splitting plain content from renderer formatting; Step 0 preserves all snapshots. |
| Background refresh, selection and errors lacked a contract | §9.1 specifies generations, request checks, publication, error exits and cancellation tests in Steps 2/3. |
| Non-object Claude settings JSON crashes resolution | §11 requires defensive shape validation and a regression before Step 0. |
| Invalid UTF-8 installer lockfile crashes doctor | §11 requires read-boundary decoding handling and a regression before Step 0. |
| Textual was claimed to require exactly Rich 15 | §6.2 cites published `rich>=14.2.0` metadata and separates requirements from the lock. |
| Startup benchmark omitted discovery hashing | §9 and Step 1 measure the complete input/discovery/scan path. |
| Documentation move was described as pending | §11/§13 record the committed move (`d37f218`). |
| Default behaviour contradicted project rules | §3/§7 and companion AGENTS/spec wording distinguish primary CLI from bare-invocation TUI. |
| Doctor offered clipboard support despite Q3 | §8.6 displays unmatched paths; copy actions remain deferred, including JSON in §2. |
| Full gate was claimed green despite formatting failure | Non-runnable Python sketches replaced with explicit launch flow; §11 records the review baseline and requires a new full gate. |

**Readiness:** the architectural direction remains suitable. Before session
implementation, fix the two engine crashes and pass the prerequisite gate.
Q9 is settled; implementation can proceed through the planned gates once those
prerequisites pass. This document does not mark the fixes or TUI as implemented
or establish release readiness.

---

## 21. Step 0 implementation contract

This section supplies the design decisions that an implementer would otherwise
have to invent. It is authoritative for Step 0. §22 splits it into assignments;
§11 still governs dependency installation, screens and release. These are
planned APIs, not functions already present in the repository.

Read `SKILL_LENS_SPECIFICATION.md`, `DEVELOPMENT.md`, and the Phase 2, 3 and 4
findings before changing their respective engines. Read the Phase 5 walkthrough
before Step 1 changes packaging. Preserve public report fields, JSON shapes,
precedence, variant ordering, diff limits and CLI defaults. Internal snapshot
objects are not a new public JSON format.

### 21.1 File ownership and dependency direction

| File | Responsibility in this contract |
| --- | --- |
| `core/snapshot_models.py` (new) | Captured input and session dataclasses; no filesystem operations. |
| `core/snapshot.py` (new) | Capture, validation and report services. The only session service allowed to read the machine is `capture_session()`. |
| `core/cancellation.py` (new) | Cancellation exception and checkpoint helper; no UI dependencies. |
| `core/hasher.py` | Add byte-based helpers; retain the streaming CLI path. |
| `core/parser.py` | Extract parsing from captured bytes while retaining live read-error handling. |
| `core/resolver.py` | Shared lookup-name helper, pure settings decoder, explicit captured overrides. |
| `core/diff.py` | Explicit captured-file input; existing comparison and truncation rules. |
| `core/discovery.py`, `core/system.py` | Optional cancellation checkpoints; existing discovery and permission guards. |
| `core/compare.py`, `core/doctor.py` | Injected index/registry in wrappers. Doctor is computed before publication. |
| `core/scanner.py` | Existing builder is used before publication; no new live navigation path. |
| `presentation/__init__.py`, `state.py`, `text.py` (new) | Shared constants and plain text/heading parts. |
| `render.py` | Rich adapters over shared content; existing visible output. |
| `tests/test_snapshot_inputs.py`, `test_session_snapshot.py`, `test_presentation.py` (new) | Step 0 acceptance tests below. Extend existing engine tests where the behaviour belongs there. |

Use future annotations and `TYPE_CHECKING` imports for report type references
where necessary. `discovery`, `hasher` and `parser` must not import `snapshot.py`
or Textual. `snapshot.py` may call the existing engines. Avoid a dependency loop:
`snapshot_models.py` can reference discovery types; discovery must not import
snapshot models. Widen index annotations only in consumers that accept the frozen
index, including their private helpers. Do not suppress strict typing with `Any`.

### 21.2 Exact internal data structures

All new dataclasses below use `frozen=True, slots=True`. Import existing
`DiscoveredEntry`, `UnreadableRoot`, `AgentDefinition`, `ScanReport` and report
models; do not duplicate their fields or resolution logic.

```text
CapturedFile
    relative_path: str
    data: bytes
    fingerprint: str

CapturedInput
    path: str
    data: bytes | None
    error: Literal["missing", "unreadable"] | None

FrozenDiscoveryIndex
    home: str
    cwd: str
    entries: tuple[DiscoveredEntry, ...]
    unreadable_roots: tuple[UnreadableRoot, ...]
    all_agents(self) -> set[str]

SessionSnapshot
    generation: int
    home: Path
    cwd: Path
    registry: tuple[AgentDefinition, ...]
    index: FrozenDiscoveryIndex
    files: Mapping[str, tuple[CapturedFile, ...]]
    config_inputs: Mapping[str, CapturedInput]
    disabled_overrides: Mapping[str, frozenset[str]]
    display_paths: Mapping[str, str]
    same_locations: frozenset[tuple[str, str]]
    scan: ScanReport
    doctor: DoctorReport
```

- `files` uses **`discovery.canonical_key(entry)`**, never a hand-built key.
  Every index entry has a key, including an unreadable copy with an empty tuple.
  Directory files use sorted relative POSIX paths and the existing ignore rules.
  A standalone file uses its canonical filename, matching `_copy_files()` today.
- `data` is the entire file, including binary files. No prefix limit, text-only
  shortcut, disk cache or silent skipping. Decode only for parsing/comparison;
  never display binary bytes. Preserve the existing output truncation budgets.
- `config_inputs` is keyed by absolute path. Capture the installer lock and every
  configured agent settings file, including missing/unreadable status.
  `disabled_overrides` has an entry for **every** registry agent, even when empty.
  A successful read has bytes (possibly empty) and `error=None`; a failed read
  has `data=None` and one of the two error codes. No ambiguous third state.
- Copy dictionaries and wrap them in `MappingProxyType` before publication.
  Keep registry order from `load_registry()`; reconstruct an owned
  `{agent.id: agent for agent in snapshot.registry}` for existing engine calls.
- Copy the original index lists into tuples. Deep-copy each parse's
  `frontmatter`, which is a mutable dictionary inside a frozen `ParseResult`.
  Deep-copy nested containers in stored reports. Published objects are owned by
  the session and must never be mutated. Do not change existing public model
  field types to claim deep immutability; frozen dataclasses alone do not provide it.
- `all_agents()` returns the same set derived from hits as the existing index.
  Returning a new set does not expose owned state for mutation.
- `same_locations` stores both ordered forms of each true
  `(entrypoint_path, canonical_path)` comparison needed by Why, evaluated during
  capture. Equal strings are also equal without a disk probe.
- `display_paths` includes home/cwd, canonical and entrypoint paths, all hit
  entrypoints, unreadable roots, shared library, lock and settings paths. Compute
  their displayed strings through `paths.display()` during capture. Doctor's
  message/path strings are already stored in its report. An unknown display key
  returns its original string; it must never trigger a live fallback.

### 21.3 Byte helpers and engine signatures

The following signatures are the implementation target. Code blocks here are
interface definitions, not runnable examples. Existing positional parameters
stay positional; new input parameters are keyword-only.

```text
# core/hasher.py
normalized_text(data: bytes) -> str | None
hash_bytes(data: bytes) -> str
hash_captured_directory(files: Sequence[tuple[str, str]]) -> str

# core/parser.py
parse_skill_bytes(data: bytes, *, source_path: str) -> ParseResult

# core/resolver.py
lookup_name_for_entry(entry: DiscoveredEntry, agent: AgentDefinition) -> str
disabled_overrides_from_bytes(
    agent: AgentDefinition, data: bytes | None
) -> frozenset[str]
resolve_skill(
    name: str, agent_id: str, cwd: Path, home: Path,
    index: DiscoveryIndex | FrozenDiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None,
    *, disabled_overrides: frozenset[str] | None = None
) -> ResolutionReport

# core/diff.py
build_diff_report(
    name: str, cwd: Path, home: Path, *,
    index: DiscoveryIndex | FrozenDiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None,
    captured_files: Mapping[str, tuple[CapturedFile, ...]] | None = None
) -> DiffReport

# core/compare.py
build_compare_report(
    agent_a: str, agent_b: str, home: Path, cwd: Path,
    index: DiscoveryIndex | FrozenDiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None
) -> CompareReport
run_compare(
    agent_a: str, agent_b: str, cwd: Path | None = None, *,
    index: DiscoveryIndex | FrozenDiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None
) -> CompareReport

# core/doctor.py (only the live index is needed here)
run_doctor(
    cwd: Path | None = None, *, index: DiscoveryIndex | None = None,
    registry: dict[str, AgentDefinition] | None = None
) -> DoctorReport
```

`normalized_text()` decodes UTF-8 and replaces CRLF with LF; invalid UTF-8 returns
`None`. A lone CR stays unchanged, and a NUL byte does not by itself make a file
binary: preserve the existing UTF-8 rule. `hash_bytes()` hashes that normalized
UTF-8 text, or raw bytes if decoding fails, with the existing `sha256:` prefix.
`hash_captured_directory()` sorts `(relative_path, fingerprint)` pairs and hashes
the existing `relative_path + NUL + fingerprint + LF` sequence. These helpers
must agree with the current streaming hasher, which remains the CLI default.

`parse_skill_bytes()` preserves the current parser's universal-newline behaviour
(CRLF and lone CR become LF), BOM handling, YAML checks and metadata coercion.
Derive directory/file identity from `source_path`, using the existing filename
rules. Extract a shared decoded-text parser so both byte and live paths use the
same validation. Live `parse_skill_document()` retains its OSError handling;
undecodable captured bytes produce the same `ERR_UNDECODABLE_TEXT` result.

`lookup_name_for_entry()` reuses `_identity_names()` and the agent policy. Choose
directory name for `directory_name` or `either`, frontmatter name with the current
directory fallback for `frontmatter_name`, and `entry.name` when no parse exists.
The returned name must belong to `_identity_names(agent, entry)`. This is a
lookup key, not a replacement for the Home row's displayed name. Preserve
override matching against `entry.name`; do not introduce a settings-key migration.

The settings decoder returns an empty set for missing/unreadable/undecodable
input, invalid JSON, a non-object top level or a non-object overrides member.
Only a value that **is `False`** disables a name. The live loader reads its file
and delegates to this decoder; do not duplicate JSON rules in `snapshot.py`.

**Explicit input must never fall back to live reads.** `None` means the current
CLI path. A supplied empty set/map means captured emptiness. In `resolve_skill`,
supplied overrides require both index and registry, then `_candidates_for()` uses
the supplied set. In `build_diff_report`, supplied files require both index and
registry, then `_copy_files()` uses that map and converts captured bytes to
`_Collected` using the shared helpers. A missing map key is a `ValueError`
contract violation, not an invitation to read disk or return an empty copy.
These contract violations become unexpected worker errors in the UI.

For a `FrozenDiscoveryIndex`, reject omitted overrides in resolution, omitted
captured files in diff, or omitted registry in any consumer. This prevents a
caller accidentally making the frozen index behave like a live CLI request.
Widen `build_compare_report()` and its helper annotations to accept the frozen
index too; its algorithm remains unchanged. Both wrappers use provided registry
definitions and index home/cwd; when omitted, keep their existing live defaults.
In doctor, call `list_agents()` only when no registry was supplied; the current
unconditional call before replacing its result is an unnecessary packaged-file
read. The supplied definitions govern its evidence check throughout capture.
Do not call `run_doctor()` on view navigation: the stored report is the answer.

### 21.4 Cancellation and capture algorithm

Add `CaptureCancelled(Exception)` and
`check_cancelled(cancelled: Callable[[], bool] | None) -> None` in
`core/cancellation.py`. The helper raises when the predicate returns true.
Add keyword-only `cancelled: Callable[[], bool] | None = None` to
`live_discovery()`, `discover()`, `hash_path()`, `hash_directory()` and
`hash_file()`, and to `iter_files()`. Pass it down and check between roots,
entries, walked directories, files and streaming chunks. Snapshot byte reads use
chunks with the same checkpoints. Defaults
preserve CLI calls. Do not swallow cancellation as an unreadable-file error.
Check between scan/doctor/validation phases as well. This is cooperative
cancellation: it cannot force a blocked operating-system read to return.

```text
# Existing positional parameters remain accepted.
live_discovery(
    cwd: Path | None = None,
    registry: dict[str, AgentDefinition] | None = None, *,
    cancelled: Callable[[], bool] | None = None
) -> DiscoveryIndex
discover(
    home: Path, cwd: Path,
    registry: dict[str, AgentDefinition] | None = None, *,
    cancelled: Callable[[], bool] | None = None
) -> DiscoveryIndex
iter_files(root: Path, *, cancelled: Callable[[], bool] | None = None) -> list[Path]
hash_file(path: Path, *, cancelled: Callable[[], bool] | None = None) -> str
hash_directory(root: Path, *, cancelled: Callable[[], bool] | None = None) -> str
hash_path(path: Path, *, cancelled: Callable[[], bool] | None = None) -> str
```

The public capture and browsing services in `core/snapshot.py` are:

```text
capture_session(
    *, generation: int, home: Path, cwd: Path,
    cancelled: Callable[[], bool] | None = None
) -> SessionSnapshot
entry_for_path(snapshot: SessionSnapshot, key: str) -> DiscoveredEntry
snapshot_why(
    snapshot: SessionSnapshot, key: str, agent_id: str
) -> ResolutionReport
snapshot_diff(snapshot: SessionSnapshot, key: str) -> DiffReport
snapshot_compare(
    snapshot: SessionSnapshot, agent_a: str, agent_b: str
) -> CompareReport
snapshot_path(snapshot: SessionSnapshot, path: str) -> str
snapshot_same_location(snapshot: SessionSnapshot, a: str, b: str) -> bool
```

Add `SnapshotChanged(Exception)` in `snapshot.py`. It means capture observed
changing inputs and cannot publish a consistent replacement. It is an expected
inline error, with the message “Files changed while scanning. Press r to retry.”
It does not set the internal-error exit flag. Never automatically spin retries.

Implement `capture_session()` in this order:

1. The launcher has already applied sandbox and validated cwd. Verify that the
   supplied home matches `paths.home()` before starting. Load registry once;
   call `live_discovery(cwd=cwd, registry=registry, cancelled=cancelled)`.
   Use the resulting normalized index home/cwd in the snapshot.
2. Capture settings and lock bytes/status through one guarded reader. Distinguish
   `FileNotFoundError` (`missing`) from other OSError (`unreadable`). Invalid UTF-8
   remains bytes, allowing each existing decoder to apply its normal policy.
   Derive all agents' disabled sets using the pure decoder.
3. For each discovered canonical copy with a non-None content hash, collect all
   hashable files using `iter_files()` or its standalone filename. Read complete
   bytes and calculate file hashes from those bytes. The aggregate hash must
   equal `entry.content_hash`. A read failure for a previously hashable copy is
   `SnapshotChanged`; a stably unreadable copy with no hash remains an empty tuple.
4. Where a parse has readable source bytes, parse the captured document using
   its original `parse.source_path`; compare both `to_dict()` **and `body`** with
   discovery's result. Dataclass equality alone misses frontmatter differences.
   `SKILL.md`/`skill.md` selection and standalone source naming remain unchanged.
   A stable undecodable document retains its captured unreadable parse result.
5. Build scan and doctor from the live index with the loaded registry. Capture
   display strings and link equality for the path set in §21.2. This deliberately
   pays for doctor once at startup; opening Doctor later simply uses stored data.
6. Validate before publication: perform a second `live_discovery()` with the
   same registry. Compare ordered entries,
   canonical metadata, hits, entrypoint paths, names, parse dictionaries/bodies,
   hashes, variant labels and unreadable roots. Rebuild scan/doctor and the path
   display/link decisions against this validation index and compare results.
   Finally reread configs and compare bytes/status with the captured inputs.
   Any difference raises `SnapshotChanged`. Do not publish either partial pass.
7. Check cancellation and that effective home still agrees. Copy/freeze owned
   containers and return one complete `SessionSnapshot`. Do not set current UI
   state here. The UI publishes it only if its generation is still the newest.

This validation detects observable changes; it is not a filesystem transaction.
An external change that happens and is completely undone between checks may be
unobservable. Do not advertise stronger atomicity. Include both discovery
passes, byte capture and doctor validation in the §9 startup benchmark. If this
is too slow on the synthetic gate, report measurements before changing the
locked consistency behaviour. Memory exhaustion is an unexpected worker error;
do not silently cap inputs or create temporary files to work around it.

Browsing service rules:

- `entry_for_path()` matches `canonical_key(entry)` and raises `KeyError` if
  absent. It does not resolve a path or discover a newly added skill.
- `snapshot_why()` validates agent against the captured registry, translates
  the selected entry through `lookup_name_for_entry()` and calls `resolve_skill`
  with frozen index, registry and that agent's captured overrides.
- `snapshot_diff()` uses the entry's **directory grouping name (`entry.name`)**
  with captured index/registry/files. It preserves CLI grouping even when Why
  uses a different frontmatter name.
- `snapshot_compare()` validates both ids and rejects identical ids before
  calling `run_compare(index=..., registry=...)`. Do not reinterpret disabled
  settings as compare availability: preserve the existing comparison model.
- Scan and Doctor use `snapshot.scan` and `snapshot.doctor`. Agents uses
  `snapshot.registry`. JSON serializes these same report objects using the
  existing CLI encoder/options, not a fresh live command.
- `snapshot_path()` is a map lookup with literal-string fallback.
  `snapshot_same_location()` checks equal strings or the captured pair set.
  Neither calls `Path.resolve`, `paths.display`, `paths.home` or `same_location`.

### 21.5 Presentation interfaces

Re-export `STATE_STYLE`, `STATE_MARK` and `SCOPE_LABEL` from `presentation/state.py`
with their current keys/values. Add the following in `presentation/text.py`:

```text
HeadingParts (frozen, slots)
    mark: str
    style: str
    path: str
    variant: str
    scope: str
    parse_status: str
    status: str

NoticeParts (frozen, slots)
    label: str
    style: str
    body: str

range_text(start: int, count: int) -> str
unified_text(file: DiffFile) -> str
unreadable_reason(copy: DiffCopy) -> str
copy_heading(
    copy: DiffCopy, *, baseline_exists: bool, display_path: str
) -> HeadingParts
no_differences_message(report: DiffReport) -> NoticeParts
needs_listing(report: DiffReport) -> bool
```

Move the existing range/unified/reason/listing algorithms unchanged. Heading
parts retain the current marker/style/status branches, variant text (including
its leading space), scope and parse status. Notice parts retain current wording,
with a separate `label` such as `Not compared:` and body including the following
space. `copy_heading()` takes an already displayed path; no filesystem dependency
belongs in these helpers. Literal user strings may contain brackets; the package
must not add escaping or formatting tags to them.

`render.py` uses `paths.display()` for its live CLI path and joins/escapes parts
into the current Rich output. The TUI passes `snapshot_path()` results, uses
markup-disabled widgets, and applies the parts' styles separately. Retaining
small private Rich adapter functions in `render.py` is allowed; duplicated
status/wording logic is not. Re-export these public helpers through
`presentation/__init__.py`. No Rich/Textual/Console imports in this package.

### 21.6 Concrete acceptance tests

All fixtures use `tmp_path` and paths.py-based sandbox/home isolation. Construct
expected reports **before** banning reads or modifying fixtures. Use synthetic
skills and settings only. Do not inspect installed skills in the developer's home.

| Test / location | Setup and required assertion |
| --- | --- |
| `test_non_object_settings_are_ignored` in existing resolver tests | Parametrize `[]`, `null`, a string and a number. Resolution completes with the normal empty-override result; valid object overrides still work. |
| `test_non_utf8_lock_reports_invalid_json` in system/doctor tests | Write invalid UTF-8 lock bytes in fake home. Reader returns `ERR_NOT_JSON`; doctor produces its existing invalid-lock warning. |
| `test_hash_bytes_matches_streaming` in `test_snapshot_inputs.py` | Compare helper and live hash for LF, CRLF crossing the 64 KiB boundary, lone CR, BOM, valid UTF-8 with NUL, invalid UTF-8 and a >1 MiB file changed near the end. |
| `test_captured_directory_matches_live_hash` in the same file | Nested files and renamed files; `.git`, `.DS_Store`, `._*` exclusions; input order shuffled; directory aggregate equals live hash. Standalone file hash is not a directory aggregate. |
| `test_byte_parser_matches_live_parser` in the same file | Valid, malformed, missing description, lowercase document, standalone file, BOM, lone CR and undecodable bytes. Compare `to_dict()` plus body, preserving source-path identity. |
| `test_selected_entry_uses_agent_identity` in resolver tests | `folder-key/SKILL.md` declares `name: declared-key`; directory/frontmatter/either agents find the selected installation using the helper. Include absent parse/name and invalid metadata with a usable declared name. |
| `test_explicit_empty_inputs_never_fall_back` in engine tests | Supplied empty override set remains enabled despite a live disabled setting. Captured empty file tuple remains empty; missing copy key raises. Patch live settings/file collection to raise if invoked. Frozen-index calls missing required captured arguments raise. |
| `test_snapshot_reports_match_live_reports` in `test_session_snapshot.py` | Before external changes, compare scan, every selected-name/agent Why, Diff, Doctor and all valid compare pairs against current builders using identical index/registry/settings. Assert report dictionaries and existing CLI JSON serialization match. |
| `test_first_visits_do_not_read_files` in the same file | Capture; edit/delete/add skills, change settings/lock and retarget a shortcut. On **first** visits to Why/Diff/Compare/Doctor/Agents/JSON, reports and displayed paths remain equal to the original expected data. |
| `test_navigation_has_no_filesystem_fallback` in the same file | After capture, patch live discovery, registry loading, settings loading, diff collection, `paths.home/display/same_location`, filesystem read/walk/stat/resolve/link probes to raise. Call every browsing service and shared presentation helper; no call reaches a patched boundary. Scope patches to navigation so pytest can still read its own files. |
| `test_refresh_sees_changed_inputs` in the same file | A second successful capture after the above changes shows the new inventory, settings, diff and doctor findings together. Original snapshot remains unchanged. |
| `test_change_during_capture_is_rejected` in the same file | Deterministic monkeypatch hooks change file bytes, config bytes, file membership or a symlink between capture phases. Each causes `SnapshotChanged`; no candidate is returned. Do not use sleep races. |
| `test_cancelled_capture_does_not_publish` in the same file | A controlled predicate becomes true during hashing/byte capture/validation. `CaptureCancelled` propagates; no partial snapshot escapes. |
| `test_snapshot_owns_its_containers` in the same file | Mutate original discovery lists and nested parse frontmatter after capture. Snapshot data is unchanged; its mapping tables reject assignment. |
| `test_capture_never_writes_target` in the same file | Compare fake-home files' bytes, modes and symlink targets before/after capture and navigation, not just the filename list. |
| `test_plain_parts_preserve_literal_text` in `test_presentation.py` | Names/paths containing `[red]`, closing tags and backslashes survive literally in parts; binary payloads never become printable content. Rich snapshots remain byte-identical. Textual rendering is checked later in Step 4/5. |

The first two regressions must fail on the pre-fix implementation. New gate
tests must be mutation-tested: temporarily break the empty-input check, captured
diff branch, identity translation, capture validation and no-live-read boundary,
one at a time; each corresponding test must fail. Restore each change before
the next mutation. Record the mutations and results; surviving mutations block
the gate. Never alter expected snapshots/goldens to make this contract pass.

### 21.7 Refresh and report handoff contract for Steps 2–3

Keep report caching and worker control in the UI, outside `SessionSnapshot`.
A **generation** identifies a published capture; a **request id** identifies one
attempt to fill a particular view. Workers receive an owned snapshot/reference
and immutable arguments. The UI owns these fields:

```text
current: SessionSnapshot | None
next_generation: int                    # starts at 1; never reused
pending_generation: int | None
next_request_id: int                    # starts at 1; never reused
active_requests: dict[ViewName, ViewRequest]
cache: dict[tuple[int, ViewName, tuple[str, ...]], ReportValue]
selected_key: str | None                # discovery.canonical_key
failed: bool                           # unexpected accepted error occurred
closed: bool

ViewName = Literal["why", "diff", "compare"]
ReportValue = ResolutionReport | DiffReport | CompareReport
ViewRequest (frozen, slots)
    generation: int
    request_id: int
    view: ViewName
    arguments: tuple[str, ...]
```

Why arguments are `(selected_key, agent_id)`; Diff arguments are `(selected_key,)`;
Compare arguments are `(agent_a, agent_b)` in selected order. Scan/Doctor/Agents
need no background report request because capture already supplies their data.
The Home agent filter uses the Why service and this same cache contract.

1. Refresh allocates a generation and its own `threading.Event`. Superseding
   refresh/quit sets the old event. Capture receives `event.is_set`; it must not
   read widget state from its worker thread. Old snapshot remains available.
2. Accept a capture result only while open and when its generation equals
   `pending_generation` and the returned snapshot's generation. On the UI thread,
   swap current, clear report cache/requests, and preserve selected key if it
   still exists; otherwise choose the first row, or None for an empty catalog.
3. A view request allocates an id and records generation/view/arguments together.
   Use cache only for that full key. Accept a result/error only if current
   generation and the active request all match. Changing arguments or leaving
   the view invalidates the prior request. Ignore stale results **and errors**.
4. An expected `SnapshotChanged` refresh error keeps current and displays its
   retry message. Cancellation is quiet. An accepted unexpected error keeps the
   previous usable data, sets `failed=True`, and exposes an in-memory error panel
   with optional traceback details. No terminal print or logfile.
5. Quit marks closed, sets all worker events, invalidates pending requests and
   returns `3` if failed, otherwise `0`. Callbacks after close are ignored.
   Do not wait for an entire scan to finish before leaving the interface.

Implement these transitions in a small UI controller module without Textual
imports (`tui/session.py`), then connect worker completion through Textual messages or
`call_from_thread()` on the UI thread. Use `exit_on_error=False`; the controller,
not Textual's default worker crash handling, owns the error path.

Required deterministic tests: complete refresh 3 before refresh 2; report request
2 before request 1; change selection/agent during work; leave and return to a
view; quit before completion; fail a newest refresh with and without an existing
snapshot; ignore a superseded worker's exception. Verify one atomic publication,
no stale cache entry/update, and exact 0/3 exit behaviour. Use controlled events,
not timing assumptions. Headless Textual integration tests then prove the worker
adapter obeys those transitions and controlled slow-scan quit is prompt.

## 22. Assignments for the implementer

Dispatch **one row at a time**, with this document and AGENTS.md as context.
Finish its tests and full repository gate, then review its diff before dispatching
the next row. A row's allowed scope includes its named files and corresponding
tests only. If source differs from this contract or a required check fails,
report the concrete discrepancy; do not silently redesign behaviour or proceed
to screens. This is a sequence of supervised assignments, not a promise that
an arbitrary model can safely implement the whole project in one prompt.

| Assignment | Allowed scope / concrete deliverable | Review gate |
| --- | --- | --- |
| P1 — settings robustness | `core/resolver.py`, existing resolver tests. Fix non-object settings crash only. | New failing-before/passing-after shape tests; valid settings behaviour unchanged. |
| P2 — lock decoding | `core/system.py`, existing system/doctor tests. Invalid UTF-8 follows `ERR_NOT_JSON` path. | Regression proves doctor warning; existing doctor goldens unchanged. |
| C1 — bytes and identity | `core/hasher.py`, `parser.py`, `resolver.py`, `test_snapshot_inputs.py`, relevant existing tests. Implement pure helpers, identity helper and settings decoder from §21.3. | Hash/parser parity and identity cases in §21.6; no snapshot/TUI code yet. |
| C2 — explicit captured engine inputs | `core/snapshot_models.py`, `resolver.py`, `diff.py`, `compare.py`, `doctor.py`, engine tests. Implement data types and signatures. | Live default parity; empty inputs never fall back; frozen calls reject missing inputs. |
| C3 — capture and cancellation | `core/snapshot.py`, `cancellation.py`, `discovery.py`, `system.py`, `hasher.py`, `test_session_snapshot.py`. Implement §21.4 and cancellation propagation. | First-visit freeze, no-live-read tests, capture consistency, refresh, ownership, read-only and cancellation all pass. |
| C4 — presentation extraction | `presentation/`, `render.py`, `test_presentation.py`. Implement §21.5 without Rich in shared code. | All 17 existing snapshots unchanged; literal text checks; dependency direction clean. |
| C5 — Step 0 audit | Relevant tests and a factual Step 0 walkthrough under `docs/`; correction to this plan only if a reviewed source mismatch requires it. No new feature code. | Run mutation checks from §21.6; report files/API/read boundaries and all four gates. Step 0 is complete only after review. |
| U1 — optional install | Step 1 files: `pyproject.toml`, `uv.lock`, `cli.py`, CI and packaging/CLI tests; Phase 5 record read first. | Both installation lanes, exact fallback exits, CLI output parity and mutation-tested launch gate. |
| U2 — worker controller and skeleton | `tui/`, CLI launch adapter and TUI tests; Steps 2 and §21.7. Placeholder screen only. | Controller races/errors/quit, read-only guard mutations, strict mypy, headless launch. |
| U3 — Home | Home widgets/tests and measured benchmark; Step 3. Reuse C3 capture and U2 controller. | Canonical selection, filters, empty state, complete refresh and actual 600-skill widget responsiveness. |
| U4 — Why | Why screen/tests; Step 4. Call snapshot service and shared parts. | Agent identity mapping, evidence display and literal markup rendering. |
| U5 — Diff and JSON | Diff/JSON screens/tests; Step 5. No new engine algorithms. | Existing binary/truncation rules and same-input CLI JSON equality on every implemented screen. |
| U6 — Agents and Compare | Picker/screens/tests; Step 6. | Captured registry, fewer than two agents, same/unknown agent errors and frozen comparison. |
| U7 — Doctor | Doctor screen/tests; Step 7. Use stored report. | Severity/message parity; in-app jump and unmatched paths; no live doctor rerun. |
| U8 — polish | Step 8 help/keymap/error/empty states and user docs. | Complete headless browsing flow, full gate with TUI coverage, measured limitations recorded. |
| U9 — release preparation | Step 9 version/lock/release checklist and built-wheel smoke tests. | Follow DEVELOPMENT release rules; passing preparation does not itself authorize publishing. |

After **each row**, run `pytest --cov=skill_lens`, `mypy`, `ruff check .` and
`ruff format --check .` using the repository environment. State what changed,
why, test results and remaining blockers. Do not mark later rows complete,
regenerate pinned output without reviewing the difference, publish a release,
or create a commit unless the current assignment authorizes it. The maintainer
or supervising reviewer verifies each row before handing over the next one.
