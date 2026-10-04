# Skill Lens 0.2 — Full-Screen TUI

> **Status:** 📋 **Plan only — not implemented.** This document is the agreed
> design for the `0.2` major release. No code has been written against it yet.
> It overturns a v1 rule ("no full-screen TUI"), so it is deliberately detailed:
> the point of the plan is that the next person can scaffold the work without
> re-litigating the decisions below.
>
> **Version:** 0.2.0 (major surface change; see [§15 Compatibility](#15-compatibility--migration))
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
- Pressing **`j`** toggles the raw JSON of whatever you are looking at, so a
  power user can copy the exact machine-readable payload.
- Pressing **`?`** shows a help overlay; **`q`** quits.

The whole thing is **the existing reports, made navigable**. It is not a new
engine and it is not a new source of truth. Think of it as wrapping the CLI's
already-computed answers in a window you can scroll through, the way a file
manager wraps `ls`, `stat` and `diff`.

**Nothing about the underlying data changes.** The TUI reads the same frozen
models the JSON output is built from.

---

## 3. The core decision (and what it costs)

A full-screen TUI needs a library that takes over the terminal: raw key input,
alternate screen buffer, layout and re-rendering. Rich alone does not do this.
The standard choice in the Python world is **Textual** (same authors as Rich),
which is why the v1 rule named it explicitly.

**Decision:** add **Textual** as an *optional* dependency and ship a new
`tui` surface behind it. Keep every existing command and the pure line-oriented
default exactly as they are.

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
| **Deterministic** | Same machine, same answers — the TUI recomputes nothing itself. |
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
5. Preserve every CLI guarantee and every CLI command byte-for-byte.
6. Keep the TUI **presentation-only**: no computation that the CLI does not
   already do.

### Non-goals (explicitly out of scope for 0.2)

- ❌ **No editing, installing, moving, or deleting skills.** Read-only forever.
- ❌ **No file watching / live refresh** in 0.2 — one snapshot per session,
  refreshable with a key. (Watch mode is a candidate for 0.3.)
- ❌ **No config file, themes marketplace, or plugin system** for the TUI.
- ❌ **No mouse-first design** — keyboard is the contract; mouse is a bonus.
- ❌ **No new data** — if a field is not in an existing model, the TUI cannot
  show it in 0.2.
- ❌ **No Windows support** (unchanged from v1).

---

## 5. Architecture — where the TUI sits

The codebase already has the right shape for this. The split is:

```text
skill_lens/
├── core/              # pure logic → frozen dataclasses (no terminal, no Rich)
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
            │  (pure)     │  → frozen dataclasses
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

So **two** entry points need the parameter, not one. An earlier draft of this
plan claimed one and was wrong.

Note *which* two: only the `run_*` **live wrappers** lack it. Their `build_*`
counterparts already accept `index=`, so the TUI could call those with a held
index today — the new parameter exists so the **CLI entry points** can also be
driven from a held index, not because the builders need it. That narrows the
change but does not remove it.

**Decision:** the TUI holds one small immutable session state:

```text
SessionState
├── home:  Path
├── cwd:   Path
├── index: DiscoveryIndex   ← built once, rebuilt with `r`
└── scan:  ScanReport       ← derived from the index, cached for the list
```

- `diff` passes `index=state.index` — no second filesystem walk.
- `compare` and `doctor` each need **one new keyword-only `index` parameter**,
  defaulting to `None` so today's behaviour is byte-identical and the Phase 4
  goldens keep passing. These two are the **only** changes to `core/` this plan
  authorises.

### 5.2 The session index must come from `live_discovery()`

This is the safety-critical detail. `run_compare()` and `run_doctor()` do not
build an index themselves — they call `live_discovery()` in `core/system.py`,
the module whose own docstring says it is *"the only place that touches the
filesystem defensively"*, and which exists precisely because macOS TCC refuses
to list some folders and an `OSError` from one directory must never abort a run.

**Rule:** the session index is produced by `live_discovery()`. The TUI must not
call `discover()` directly. If it bypassed that adapter, a permission-blocked
directory would raise instead of being recorded as `unreadable` — regressing a
guarantee the Phase 4 review specifically paid for.

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
| Data access | `core/` functions, called once per view | Reuses the tested engine. |
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
3. **The margin is thin.** The suite currently measures **93%** branch coverage
   against the **90%** floor (`DEVELOPMENT.md`), so a whole new `tui/` package
   has only three points of headroom. Budget for it: factor keymap, formatting
   and session-state logic out of widgets so it is unit-testable *before* Step 2
   lands, not after the gate goes red.

### 6.2 Rich is a shared dependency (coupling risk)

Textual and Skill Lens both depend on Rich. Resolved on 2026-10-04:

```text
textual 8.2.8  →  requires  rich==15.0.0
this project   →  declares  rich>=13.0.0   (uv.lock pins 15.0.0)
```

Three consequences, none of which the plan previously acknowledged:

1. **`rich>=13.0.0` stops being true** for anyone installing `[tui]` — pip
   silently upgrades Rich from 13/14 to ≥15. The declared floor should state the
   `[tui]`-adjusted reality, or the extra's own requirement will surprise users.
2. **Our pinned output can move for an unrelated reason.** There are 17 plain-text
   Rich snapshots in `tests/fixtures/snapshots/` and 16 JSON goldens. A
   transitive constraint from an *optional* feature could change `render.py`'s
   output and fail our own snapshot gate, for a cause that has nothing to do with
   the TUI. **No test currently asserts that installing `[tui]` leaves existing
   output byte-identical** — one must be added.
3. **The floor is 8.x, not 0.80.** A review suggestion of `textual>=0.80.0`
   would have pinned an ancient, API-different Textual. Textual moves fast
   through majors; the floor gets re-checked every release ([§19 Q2](#19-decisions-locked)).

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
> (See [§19](#19-decisions-locked).)

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
   - else try to import `skill_lens.tui`; on `ImportError` print help plus the
     one-line install tip and exit `0`; on success run the app.

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
| `r` | Refresh the snapshot |
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
- `Tab` / `Shift+Tab` move between agents; each switch re-runs `resolve_skill()`
  against the already-held index and re-renders in place.
- Below the strip, one collapsible block per candidate copy, in the same order
  and with the same `rule_id` / `evidence` fields the CLI prints.
- Colours and marks come from the **shared** state-mapping tables (see below) so
  the two layers can never drift.
- A skill reached by **no** agent (a project-local skill, say) shows a
  plain-English explanation in place of the strip, not an empty bar.

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

**Decision:** create a small presentation-neutral package
`skill_lens/presentation/`:

```text
skill_lens/presentation/
├── __init__.py    # re-exports the shared names
├── state.py       # STATE_STYLE, STATE_MARK, SCOPE_LABEL
│                  #   HeadlineState/Scope → style string, glyph, label
└── text.py        # short_path(), range_text(), unified_text(), copy_heading(),
                   #   no_differences_message(), needs_listing()
                   #   pure strings, no Console
```

- `render.py` imports from `skill_lens.presentation` and keeps only the
  Console-bound glue (`_print_notes`, the Rich `Table` / `Panel` assembly).
- `tui/` imports from `skill_lens.presentation` — **never** from `render.py`.
- The package holds **no `rich` import**: `STATE_STYLE` is plain strings and the
  `text.py` builders return `str`, so it is safe for Textual and for tests.
- `models/` is deliberately **not** the home. `models/__init__.py` states the
  rule — *"Presentation (Rich) is always a layer on top of these models — never
  the other way around"* — and `STATE_STYLE` holds Rich style strings. Putting
  them in `models/enums.py` would invert the dependency AGENTS.md rule 4
  enforces.

This is a behaviour-preserving refactor of `render.py` (its 17 snapshots must not
move) and it is budgeted into Step 0. See [§19 Q7/Q8](#19-decisions-locked).

### 8.5 Empty and error states

Every screen must handle "nothing found" the way the CLI does — as an answer,
not a crash:
- No agents detected → explanatory panel, still usable.
- No copies of a skill → a message, no traceback.
- Unreadable roots (macOS TCC) → listed as `unreadable`, scan continues.
- Any unexpected internal error → a plain-English panel and a logged detail, not
  a stack trace splashed over the screen.

### 8.6 Doctor — what "jump to path" actually does

"Jump" means **select inside the app only**. It never launches an editor, never
shells out, never opens a file — `subprocess` is forbidden outright.

- `Enter` on a finding selects the matching skill in the Home list, when the
  finding's path corresponds to a known entry.
- When the path is **not** in the catalog (a dangling symlink, an unreadable
  root, a cycle), the panel says so in plain English and offers to copy the
  path. It does not pretend there is something to jump to.

### 8.7 Compare — the picker and its edge cases

- `c` opens a two-column picker: pick agent A, then agent B. Both columns list
  only ids the registry actually defines.
- Choosing the **same agent twice** is rejected inline ("Pick two different
  agents."), mirroring the CLI's `--agent`-twice check.
- **Fewer than two agents detected** → an explanatory panel naming what was
  found and how many more are needed; no crash.
- Confirming runs `run_compare(a, b, index=state.index)`. An unknown id surfaces
  the same message and exit-code semantics as the CLI.

### 8.8 What `J` shows on each screen

`J` always renders **the same payload the matching `--json` flag emits**, so the
UI can never disagree with the CLI:

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

- **One session state, held in memory.** On launch, build the `DiscoveryIndex`
  and `ScanReport` once ([§5.1](#51-what-the-tui-holds-in-memory-corrected)).
  `r` rebuilds both.
- **Diff and compare reuse the held index** — no second filesystem walk. They
  still *compute* on demand when their screen opens, because the result depends
  on which skill or which pair of agents you picked.
- **Never block the event loop.** Discovery, diff, doctor and compare all touch
  the filesystem and must run inside a Textual worker (`@work(thread=True)`), not
  on the main loop, or the UI drops keystrokes and stutters during the walk over
  600+ skills.
- **Large lists.** 600+ plugin skills must scroll smoothly — use Textual's
  virtualised list, not a pre-built table.
- **Startup is dominated by hashing, not listing.** `build_scan_report`
  computes a streaming SHA-256 over the *entire content of every file* in every
  skill. With 600+ plugin skills that is the real cost, and the held-index design
  only helps the *second* view — never the first scan.
- **Therefore: measure before promising.** The earlier draft asserted "interactive
  within ~1.5s". That number was invented. Step 1 measures `build_scan_report`
  on the reference machine and the plan is amended with the real figure. Until
  then the requirement is qualitative: *show progress, never a frozen screen.*
  A progress indicator ("Scanning… N skills") is mandatory, and the app must
  remain responsive before the scan completes.

---

## 10. Read-only guarantee

The single most important invariant. Enforcement strategy:

1. The TUI layer imports only from `core/` and `models/`, never `open(...,"w")`,
   `Path.write_*`, `os.remove`, `shutil`, or `subprocess`.
2. A dedicated AST guard test — written in **Step 2** and gated there, not
   deferred to a cleanup — fails the build if `tui/` reaches for a write.
   Concretely it rejects:
   - imports of `shutil`, `subprocess`, `tempfile`, `sqlite3`, `socket`;
   - `os.remove`, `os.unlink`, `os.rmdir`, `os.rename`;
   - `open(...)` with any mode containing `w`, `a`, `x` or `+`;
   - calls to `Path.write_text`, `Path.write_bytes`, `Path.unlink`,
     `Path.mkdir`, `Path.touch`, `Path.rename`, `Path.rmdir`;
   - any `requests` / `httpx` import.

   False positives are the real risk, so the guard is written as a walk that
   fails on the *banned names* — ordinary reading of files stays fine.

4. **The guard also bans writes to the terminal**, which the primitive list above
   does not cover. Inside a Textual app the alternate screen buffer belongs to
   Textual; a stray `Console().print()` from `render.py` corrupts the display.
   So the guard rejects, inside `tui/`:
   - any import of `skill_lens.render` (the shared helpers live in
     `skill_lens.presentation`, which `tui/` *may* import);
   - `rich.console.Console` / `Console.print` / `console.print`;
   - bare `print(...)`.

   The TUI renders through Textual widgets only.
3. `--sandbox` semantics carry over exactly: the TUI can be pointed at a mock
   `$HOME`, so a demo can never touch real skills.

---

## 11. Implementation phases (Phase 7)

Numbering continues the existing roadmap. Each step ends with a gate; no step
starts before the previous gate is green.

**Before Step 0 — land the pending documentation move.** The working tree already
contains the [§13](#13-documentation-changes-required) changes (AGENTS.md, the
specification, CHANGELOG and DEVELOPMENT updated; the Phase 2–6 records moved
into `docs/archive/`; this file added) as **uncommitted** work. Commit that
first. Otherwise the first Phase 7 commit entangles an unrelated documentation
move with the TUI plumbing, and the history becomes unreadable.

### Step 0 — Contracts (no UI code)
- Confirm the locked decisions in [§19](#19-decisions-locked).
- Set the Textual **floor** in `pyproject.toml` to the real 8.x line — *not*
  `0.80.x` — and let `uv.lock` carry the exact pin ([§6.2](#62-rich-is-a-shared-dependency-coupling-risk)).
- Add the keyword-only `index` parameter to **both** `run_compare()` and
  `run_doctor()`, each defaulting to `None` and calling `live_discovery()` when
  it is `None`
  ([§5.1](#51-what-the-tui-holds-in-memory-corrected), [§5.2](#52-the-session-index-must-come-from-live_discovery)).
- Create `skill_lens/presentation/` and move the shared display maps and the pure
  diff/why text builders out of `render.py` into it — **not** into `models/`
  ([§8.4a](#84a-sharing-the-presentation-layer--a-refactor-this-plan-must-budget)).
- **Gate:** existing suite green; `compare --json` and `doctor --json` goldens
  byte-identical; all 17 render snapshots unmoved; `mypy` strict still clean for
  the moved code.

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
- **Measure `build_scan_report()` on the reference machine** and record the real
  startup figure in [§9](#9-data-flow-and-performance), replacing the invented
  1.5s target.
- **Gate:** base install has zero new runtime deps; both fallback paths asserted;
  plumbing mutation-tested (break each branch, confirm exactly one failure).

### Step 2 — TUI skeleton
- `skill_lens/tui/app.py` — the `App` subclass, screen stack, quit handling.
- `skill_lens/tui/__init__.py` — the `run(...)` entry point the CLI calls.
- A placeholder home screen.
- **The read-only AST guard lands here** ([§10](#10-read-only-guarantee)) — it is
  a gate of this step, not a later cleanup — including the terminal-write bans.
- **Strict `mypy` applies immediately.** `[tool.mypy] files = ["skill_lens"]` with
  `strict = true` means the new package is type-checked from its first commit,
  Textual's `@work(thread=True)` typing included.
- **Gate:** `skill-lens tui --sandbox <fixture>` opens and quits on `q` in a
  headless test (Textual's `run_test()` harness); `mypy` strict clean over
  `skill_lens/`; the AST guard passes and is mutation-tested by planting one
  banned call and confirming it fails.

### Step 3 — Home / skill list
- Build `SessionState`; render the list + preview pane from `ScanReport` only (no
  resolution states — see [§8.3](#83-home-screen-layout)).
- Keyboard navigation, filtering, and an agent filter that triggers
  `resolve_skill()` for the one selected agent.
- Run discovery in a worker thread, not on the event loop.
- **Gate:** navigation tests against fixtures; list stays responsive with a
  large synthetic set.

### Step 4 — Skill detail / resolution view
- Reuse the `ResolutionReport` model; one block per copy.
- Show `rule_id` + `evidence` exactly as the CLI does.
- **Gate:** rendered content matches the model; escaping verified (skill text
  can never inject markup, mirroring the existing rule).

### Step 5 — Diff and JSON views
- `d` opens the `DiffReport` view (unified diff, same truncation rules), passing
  the held index so no second walk happens.
- `J` toggles raw JSON per the mapping in [§8.8](#88-what-j-shows-on-each-screen).
- **Gate:** diff view obeys the same truncation/binary/escaping rules as
  `render.py`; each screen's JSON is byte-identical to the matching `--json`.

### Step 6 — Agents and Compare
- Agents screen reading the registry definitions.
- Compare flow per [§8.7](#87-compare--the-picker-and-its-edge-cases).
- **Gate:** unknown-agent handling matches the CLI; same-agent-twice rejected;
  fewer-than-two-agents handled; `run_compare(index=…)` used.

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
| Read-only guard | Import/AST test forcing no write primitives in `tui/`. |
| Missing Textual | A test that simulates the import failure and asserts the friendly message + exit `2`. |
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
| `AGENTS.md` | Rewrite rule 5: CLI stays primary; TUI allowed as an additive, optional, read-only surface. |
| `SKILL_LENS_SPECIFICATION.md` | Update "Primary Interface" (§ intro) and the "Forbidden in v1" list (§5); note the TUI under the roadmap. |
| `docs/archive/PHASE2_FINDINGS.md` | Historical record — add an **amendment note** (do not rewrite the finding). |
| `docs/archive/PHASE3_FINDINGS.md` | Historical record — add an **amendment note**. |
| `docs/archive/` | New home for finished phase records (findings, walkthroughs, plans). Moved, **not deleted** — the history is kept, just out of the root. **Already staged in the working tree; commit it before Step 0 (see [§11](#11-implementation-phases-phase-7)).** |
| `README.md` | Add a short "Interactive mode" section and a roadmap line. |
| `DEVELOPMENT.md` | Add an unchecked Phase 7 build-record entry. |
| `CHANGELOG.md` | Add a `Planned`/`Unreleased` note for the 0.2 TUI. |
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
| Coverage headroom is thin (93% vs 90%) for a whole new package | Medium | Medium | Extract widget logic (keymap, formatting, session state) so it is unit-testable; land tests with each step, never after the gate goes red ([§6.1](#61-ci-must-test-both-installs-corrected)). |
| CI never exercises the base install | Medium | High | Second lean CI lane without the extra, asserting both missing-Textual paths ([§6.1](#61-ci-must-test-both-installs-corrected)). |
| A resolution state leaks into the UI | Medium | High | Only `ScanReport` fields on Home; resolution strictly per-agent in the detail view ([§8.3](#83-home-screen-layout)). |

---

## 15. Compatibility and migration

- **CLI:** every existing command, flag, JSON shape, and exit code is unchanged.
  This is a **major** version bump because the *surface* grows, not because
  anything breaks.
- **Scripts:** unaffected. `--json` output is byte-identical.
- **No-arg invocation:** changes to open the TUI (✅ Q1). `--plain` restores the
  old help output; a non-TTY stdout *and* a missing Textual both fall back to
  help automatically — so a base install never regresses.
- **Install:** base install unchanged; `[tui]` extra is opt-in.
- **Downgrade:** removing the extra and using the CLI restores 0.1.x behaviour
  exactly.

---

## 16. Reference sketches (non-binding)

```python
# skill_lens/tui/__init__.py  (illustrative only — not implemented)
from skill_lens.tui.app import SkillLensApp

def run(*, home, cwd):  # called by the `tui` command
    SkillLensApp(home=home, cwd=cwd).run()
```

```python
# skill_lens/cli.py  (illustrative only — not implemented)

app = typer.Typer(
    name="skill-lens",
    help="Local, read-only diagnostics and resolution for AI agent skills.",
    no_args_is_help=False,            # bare invocation is handled by the callback
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[bool, typer.Option("--version", is_eager=True,
                                           callback=_version_callback)] = False,
    plain: Annotated[bool, typer.Option("--plain",
                                        help="Print help instead of opening the TUI.")] = False,
) -> None:
    """Skill Lens: know what skills you have, and why each one wins."""
    if ctx.invoked_subcommand is not None:      # a real command was given
        return
    if plain or not sys.stdout.isatty():        # scripts, pipes, old terminals
        _print_help_and_exit_ok()
        return
    try:
        from skill_lens.tui import run
    except ImportError:                          # base install: never fail
        _print_help_with_tip_and_exit_ok()
        return
    run(home=paths.home(), cwd=paths.terminal_cwd())


# The explicit command is the opposite case: the user *did* ask for the UI, so a
# missing Textual is a usage error (exit 2), not a silent fallback.
@app.command()
def tui(...):
    """Open the interactive full-screen browser."""
    try:
        from skill_lens.tui import run
    except ImportError:
        error_console.print("[red]Textual is not installed.[/red] "
                            "Install it with: pip install 'skill-lens-cli[tui]'")
        raise typer.Exit(code=2) from None
    run(home=home, cwd=working_dir)
```

---

## 17. Success criteria

0.2 is done when:

1. Bare `skill-lens` (and `skill-lens tui`) opens a navigable interface on macOS
   and Linux; `skill-lens --plain` prints help and exits.
2. Every other CLI command still behaves identically (existing tests untouched
   and green).
3. The TUI shows only data that already exists in the frozen models.
4. No write operation exists anywhere in `tui/`, proven by a test.
5. Base install pulls **zero** new runtime dependencies, and a base install
   running bare `skill-lens` prints help rather than failing.
6. Both CI lanes pass: full (`[dev]` + `tui`, under coverage) and lean (base
   install, missing-Textual paths).
7. The full repository gate is green, coverage ≥ 90% **including `tui/`**, and
   every new gate is mutation-tested.
8. No resolution state is displayed anywhere the models do not define one.
9. Installing `[tui]` leaves all 17 render snapshots and 16 goldens
   **byte-identical** — the optional feature cannot move the existing output.
10. The session index comes from `live_discovery()`, so TCC-blocked roots are
   still reported as `unreadable` rather than raising.
11. `skill-lens tui` exits `0` on a normal quit, `3` on an internal fault, and
    offers no `--fail-on` ([§7.1](#71-exit-codes-from-the-tui)).
12. `tui/` imports neither `render.py` nor `rich`; all shared display logic comes
    from `skill_lens/presentation/`
    ([§8.4a](#84a-sharing-the-presentation-layer--a-refactor-this-plan-must-budget)).

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

## 19. Decisions (locked)

These were the open questions. All eight are now **decided**, and the plan above
reflects the answers.

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
times `build_scan_report()` on the reference machine and the plan is amended with
the measured figure; a progress indicator is mandatory either way
([§9](#9-data-flow-and-performance)).

**Q7 — Where do the shared display maps live?** ✅ *Decided: a new
`skill_lens/presentation/` package.* **Not** `models/enums.py`, which is pure
data; `STATE_STYLE` holds Rich style strings and would invert the model layer's
"presentation on top, never the other way around" rule. `render.py` and `tui/`
both import from `presentation/`; `tui/` still may not import `render.py`. See
[§8.4a](#84a-sharing-the-presentation-layer--a-refactor-this-plan-must-budget).

**Q8 — How wide is the shared-presentation refactor?** ✅ *Decided: share the
pure text builders, not just the two dicts.* `_SCOPE_LABEL`, `_short`,
`_unified_text`, `_range_text`, `_copy_heading`, `_no_differences_message` and
`_needs_listing` move to `presentation/` too, because §10 forbids `tui/` from
importing `render.py` and re-implementing them is the drift the §14 table warns
about. Console-bound glue stays in `render.py`.
