# Plan: Full-text skill search (`skill-lens search`, GitHub issue #7)

Status: Agreed
Authorization: Contributor request, 2026-11-21 (GitHub account `tezo18`, working
with the owner's agreement to contribute): plan issue #7 on a branch cut from
`main`, have it reviewed by Fable 5.2 as the **only** council member ("there
will be no planning council, you and Fable will be the council"), implement it
after Fable approves, then push the branch to the contributor's fork
(`tezo18/skill-lens`) and open a pull request for the owner (Hazem) to review
and merge. Merging, tagging, releasing and publishing are **not** authorized;
the owner decides those.
Roster (named by the requester for this mission only):
  - coordinator and implementer: Claude Code session, Anthropic Claude Opus 5.5
    (`claude-opus-5-5`); confirmed by the session's own system identity; effort
    is the session default (not separately confirmed).
  - plan critic and final critic: Anthropic Fable 5.2 (`claude-fable-5-2`),
    dispatched as a read-only Claude Code subagent with `model: fable`.
    Round 1 self-reported "Fable 5.2 / claude-fable-5-2" from its system
    identity; provider-side confirmation unverified (no banner on this host).
  - Family disclosure (council §1): coordinator and critic are both Anthropic
    Claude models. No model-family diversity is claimed; the requester named
    this pairing, which records acceptance of it.
Reference: 4b15862983fad503871387a150951369494f0f62
Risk and review: **High** (council §5; project-profile §7). The plan adds a
new public JSON shape (`models/search.py`) that scripts will parse, and
project-profile §7 lists public JSON shapes as high risk (the issue #6 plan
classified itself High for the same reason; raised by the critic, round 1).
High normally needs two user-named critics at plan and implementation stage.
**Requester decision recorded:** the requester explicitly named a single
council member, Fable 5.2, for both stages ("you and Fable will be the
council"); this plan records that acceptance of one critic instead of two and
discloses it in the pull request so the owner can ask for more review before
merging. This is a **mission-scoped exception to council §5 / project-profile
§7**: the requester's instruction ("there will be no planning council, you and
Fable will be the council", with "don't stop till you … open the PR") removed
any wider council for this mission regardless of the risk level; it is not a
coordinator waiver. A **second requester-chosen exception**: the coordinator
also implements and commits (council roles normally separate them). Both are
listed in the pull request for the owner. Everything else is additive: no change to path resolution, discovery,
the resolver, registry TOML, existing JSON shapes, existing exit codes, the
snapshot service or permissions.
Expected child tasks: plan critic rounds (1 dispatch each; escalate after two
non-converging rounds per council §5) + final critic rounds. The coordinator
implements in-session (the requester named the same session as implementer).

## Outcome

`skill-lens search "<words>"` answers "which of my skills can help with X?".
It looks through every discovered skill copy's **name** (folder name and the
frontmatter `name`), **description** and **SKILL.md body text**,
case-insensitively, and lists the matches ranked name > description > body.
Each result says where the words matched, shows a short one-line excerpt, the
copy's scope (global, project, system or plugin), which agents can reach it,
and — when `--agent` is given — whether that copy is the one that agent
actually runs (`ACTIVE`, `SHADOWED`, ...). `--json` returns the same data for
scripts. In the full-screen TUI, the existing `/` filter on Home now also
matches the frontmatter name and body text, so the same question can be asked
without leaving the browser.

Like everything in Skill Lens it only reads: no file is created, changed or
deleted, there is no network access and no AI call.

## Current state

Verified on 2026-11-21 against `main` at `b22dbe7e` (branch
`feat/issue-7-search` cut from it, no commits ahead):

- Issue #7 (open, unassigned, no comments) defines the command, `--agent`,
  `--json`, name > description > body ranking, case-insensitive substring
  matching, plugin skills labelled `scope: plugin`, TUI integration, and tests
  covering all three match tiers.
- **Overlap with issue #6.** Branch `feat/issue-6-report` holds a frozen,
  plan-only plan (`docs/plans/2026-11-19-report-command.md`) for a new
  `report` command; its own text says "Issues #5/#7 untouched". There is no
  behavioural conflict, but both plans edit the same files: `skill_lens/cli.py`
  (a new command and imports), `skill_lens/models/__init__.py`,
  `skill_lens/tui/home.py`, `tests/test_tui_home.py`, `README.md` (including
  the "All six commands" sentence at `README.md:86`), `CHANGELOG.md`,
  `FULL_SCREEN_TUI.md` and `SKILL_LENS_SPECIFICATION.md` §6 (both add a
  "7th" command subsection). Whichever lands second gets small text merge
  conflicts, and the #6 plan's frozen line references into `cli.py` and
  `home.py` will shift. The #6 plan also edits the status text near
  `README.md:225`, which this plan does not touch. Mitigations are in Scope.
- Commands live in `skill_lens/cli.py` (Typer: `tui`, `scan`, `why`, `agents`,
  `diff`, `doctor`, `compare`). Unknown agents and bad usage exit `2`
  (`cli.py:357-364`, `:490-497`); the spec's exit-code contract is in
  `SKILL_LENS_SPECIFICATION.md` §6 (`:135-141`). `--json` goes through
  `_emit_json` → `models.dumps`, which is
  `json.dumps(..., sort_keys=True, indent=2)` (`cli.py:124-130`,
  `models/__init__.py:73-80`): every command's JSON has alphabetically sorted
  keys.
- One discovery pass (`core/discovery.py:discover`, wrapped for the live
  machine by `core/system.py:live_discovery`, `:84-101`) already reads and
  parses every `SKILL.md`. Each `DiscoveredEntry` keeps `parse: ParseResult`
  with `body` and `description` (`models/parsing.py:69-81`,
  `core/discovery.py:194-218`). Verified by the critic: `parse.body` exists for
  every invalid-frontmatter case (`parser.py:116-163`); with a missing or
  unclosed fence the body is the **whole** document, frontmatter lines
  included; unreadable/undecodable copies have `body == ""`; dangling, cycle
  and unreadable-canonical entries have `parse is None`
  (`discovery.py:785-787`).
- `discovery.canonical_key(entry)` (`discovery.py:110-116`) — canonical
  target, or the entrypoint for unresolved copies — is the row key `scan`,
  the TUI and `snapshot_why` use, and equals `ScanEntry.canonical_path` for
  every entry kind.
- `core/scanner.py:build_scan_report` (`:163-230`, sort at `:199`) turns an
  index into `ScanEntry` rows (`name`, `scope`, `canonical_path`,
  `parse_status`, `agents`, `description`, `variant_label`), sorted by scope
  specificity then name.
- `core/compare.py:run_compare` (`:253-279`) is the pattern for a CLI engine:
  validate agent ids **before** the walk, then `live_discovery`, then a pure
  report. `_require` (`:154-160`) raises
  `KeyError("unknown agent '<id>'. Known agents: <sorted list>")`.
- Per-copy resolution state: `resolve_skill(name, agent_id, cwd, home,
  index=, registry=, controls=)` (`resolver.py:736`) resolves by the agent's
  **lookup name**, not necessarily the folder name: agents with
  `identity_source = "frontmatter_name"` (codex, grok, omp, pi, qoder, and the
  loader default, `registry/loader.py:107`) only know a copy by its
  frontmatter `name` (`resolver.py:171-172`). The TUI therefore maps each
  entry through the public `lookup_name_for_entry(entry, agent)`
  (`resolver.py:178`, exported at `:888`) before resolving
  (`tui/home.py:1291`, `core/snapshot.py:617`), then picks the copy's state
  with `tui/home.py:resolution_text` (`:242-270`: match by canonical path,
  fall back to entrypoint path, join distinct states, else `"unknown"`).
  That helper lives in a Textual module, so core code cannot import it. With
  a live index and no `controls=`, each `resolve_skill` call re-reads the
  agent's settings through `resolve_agent_controls` (`resolver.py:770-778`,
  `config.py:639`).
- TUI Home filter: `tui/home.py:build_home_rows` (`:171-197`) stores
  `search_text = f"{name}\n{description}".casefold()`; `filter_home_rows`
  (`:227-239`) keeps rows whose `search_text` contains the stripped,
  casefolded query and that the chosen agent reaches; it runs on the event
  loop on each keystroke (`home.py:1300`, `:1713`). Placeholder:
  `"Filter by name or description  (/)"` (`:587`). No test pins the
  placeholder, and Help (`tui/help.py`, Home's help rows `home.py:749-771`)
  does not name the searched fields. The captured `SessionSnapshot.index`
  holds the same `DiscoveredEntry` objects, so bodies are already in memory.
  Note: per `FULL_SCREEN_TUI.md:858-862` the parsed body kept on each entry is
  **not** bounded by the 256 MiB capture budget; this plan therefore adds no
  second copy of the bodies (decision 14).
- Output tests: terminal output is pinned as plain text at width 100 under
  `tests/fixtures/snapshots/` (`tests/test_render_snapshots.py`; regenerate
  only with `--update-snapshots` after reading the diff). The TUI read-only
  AST guard (`tests/test_tui_read_only.py`) inspects `skill_lens/tui/`.
- Gates on this machine (Windows, the contributor's laptop): the project
  targets macOS and Linux only (`AGENTS.md` rule 5) and CI runs on macOS. The
  baseline of the four gates here, including failures already present on
  `main` under Windows, is in the execution receipt and is not attributed to
  this change. The pull request's macOS CI run is the authoritative gate.

## Scope and boundaries

Allowed files:

- New: `skill_lens/models/search.py`, `skill_lens/core/search.py`,
  `tests/test_search.py`, new snapshot files
  `tests/fixtures/snapshots/search_*.txt`.
- Changed: `skill_lens/cli.py` (new `search` command and its imports only),
  `skill_lens/render.py` (new `render_search` only),
  `skill_lens/models/__init__.py` (export the new models), `skill_lens/tui/home.py`
  (Home row search fields, filter function, placeholder only),
  `tests/test_render_snapshots.py` (new snapshot tests),
  `tests/test_tui_home.py` (new filter tests), and documentation:
  `README.md` (commands table; the `:86` sentence reworded to
  "Every command in the table above is built and tested." so it no longer
  carries a count that #6 also edits), `CHANGELOG.md` (Unreleased entry),
  `SKILL_LENS_SPECIFICATION.md` §6 (new subsection headed
  `` ### `skill-lens search <query> ...` `` appended after `doctor`; if #6 lands
  first, renumber on rebase), `FULL_SCREEN_TUI.md` (Home filter sentence and
  its limits, decision 14), `AGENTS.md` §3 architecture tree (new files,
  `search` in the CLI comment), and this plan.
- Excluded: discovery, parser, hasher, resolver, registry TOML, scanner,
  doctor, compare, diff, the exit-code module, the snapshot service, packaging
  and release files, `tui/help.py` (it names no searched fields), every
  existing JSON shape and every existing snapshot/golden file. No new
  dependency. No fuzzy, regex or semantic matching (issue: v1 is plain
  substring). No dedicated TUI search screen (the issue allows extending the
  `/` filter instead).

## Behaviour decisions

1. **Query.** One positional argument. Leading/trailing whitespace is
   stripped; matching is `casefold()` substring of the stripped query in the
   casefolded field text, so `"Database"` and `"database"` are the same query
   and a multi-word query matches as one phrase. An empty or all-whitespace
   query is a usage error: message on stderr, exit `2`, no discovery walk. A
   query that starts with `-` must follow `--` (`skill-lens search -- -x`),
   because Typer reads it as an option otherwise; this is stated in the help
   text and README.
2. **What is searched, per copy (one result row per copy, exactly the `scan`
   rows; same-named copies are separate rows):**
   - *name*: `ScanEntry.name` (the name `scan`, `why` and `diff` use) **and**
     the frontmatter `name` (`parse.frontmatter_name`) when it exists and
     differs, because frontmatter-name agents such as Codex know a skill only
     by it;
   - *description*: `ScanEntry.description`;
   - *body*: `parse.body` of the copy's `DiscoveredEntry`, found through
     `discovery.canonical_key(entry)` (equal to `ScanEntry.canonical_path` for
     every entry kind). Normally this is the `SKILL.md` text after the
     frontmatter. For a copy whose frontmatter fence is missing or unclosed,
     the parser keeps the whole document as the body, so words from its
     broken frontmatter match as `body`. Copies with `parse is None` (dangling
     link, cycle, unreadable canonical) or an empty body can match only by
     name. Other files inside a skill directory are **not** searched in v1.
     Invalid copies are searched and keep their `parse_status`, like `scan`.
3. **Match tier.** The first field group that contains the query decides the
   tier: `name` (0) > `description` (1) > `body` (2). Each copy appears at
   most once.
4. **Order.** Sort by tier; inside the name tier an exact name match
   (folder or frontmatter name equal to the query, casefolded) comes first,
   then names that start with the query, then other name matches. Ties keep
   `scan` order (scope specificity, then name). Python's sort is stable, so
   the output is identical across runs.
5. **Snippet.** One line, at most 80 characters, from the matched field.
   - For `description` and `body`: find the first match offset in the field.
     If casefolding left the field's length unchanged (casefold never
     shrinks text, so equal length means offsets map one to one), take the
     text from the start of the line holding that offset; otherwise take the
     text from the start of the field. Remove control characters (C0 and C1,
     including ESC; tabs and newlines become spaces), collapse whitespace
     runs to one space. Clean the query the same way and find it again in
     the casefolded cleaned text; if found, cut an 80-character window that
     shows it, otherwise show the first 80 characters. Cut ends are marked
     with `…`. A match that spans a line break is still shown because the
     window runs on past the line end (and a query holding a double space
     still finds its window after both sides are cleaned).
   - For a `name` match the snippet is the description, cut the same way, or
     empty when there is none.
   Snippets, the query, names and every path are data: never parsed as Rich
   markup, and escape sequences in them are not emitted to the terminal
   (snippets strip them; names, paths and the query rely on Rich `Text`,
   pinned by a test).
6. **Agents.** Each result lists the agent ids that reach that copy
   (`ScanEntry.agents`). `--agent <id>` keeps only results that agent reaches,
   the same rule as the TUI agent filter. An unknown id is rejected before
   the walk with exit `2` and exactly `compare`'s sentence:
   `unknown agent '<id>'. Known agents: <sorted ids>`.
7. **State.** Without `--agent`, `state` is `null`: a copy's state only
   exists for one agent, and `FULL_SCREEN_TUI.md` §8.3 likewise shows states
   only with an agent filter. **This is a deliberate deviation from the
   issue's "each result shows … resolution state"; the pull request asks the
   owner to accept it.** With `--agent`, for each matched copy: take its
   `DiscoveredEntry`, compute `lookup_name_for_entry(entry, agent)`, run
   `resolve_skill(lookup_name, agent_id, cwd, home, index=index,
   registry=registry, controls=controls)` **once per distinct lookup name**,
   with `controls` resolved **once** per run through
   `resolve_agent_controls(agent, home, cwd)`, then pick the state by
   canonical path, falling back to entrypoint path, joining distinct states
   with `", "`, else `"unknown"` — the TUI's rule, re-implemented in core
   because core cannot import the Textual module.
8. **Scope.** Plugin and system skills are searched and keep their scope
   (`plugin`, `system`) in JSON and the table, as the issue requires.
9. **Unreadable roots.** Like `scan`, the report carries the roots that could
   not be read, and the terminal output names them, so "no results" is never
   silently caused by a blocked folder.
10. **Exit codes.** `0` whenever the search ran, including zero results.
    `2` for an empty query, an unknown agent, or a bad `--cwd`/`--sandbox`
    (existing helpers). No `--fail-on`: a missing match is an answer, not a
    fault (the same reasoning as `why`, `diff` and `compare`).
11. **Options.** `search <query> [--agent <id>] [--cwd <dir>]
    [--sandbox <dir>] [--json]`, mirroring the other commands' option names
    and help strings.
12. **JSON** (`--json`): canonical JSON like every other command, i.e.
    `models.dumps` with **sorted keys**. Fields:
    - top level: `agent` (id or `null`), `counts` (`body`, `description`,
      `name`), `cwd`, `home`, `query` (the stripped query), `results`,
      `total`, `unreadable` (same objects as `scan`);
    - each result: `agents`, `canonical_path`, `frontmatter_name` (string,
      or `null` when absent or equal to `name`), `match` (`name`,
      `description` or `body`), `name`, `parse_status`, `scope`, `snippet`,
      `state` (string or `null`), `variant_label`.
    - With `--agent`, `total` and `counts` count the filtered results.
13. **Terminal output.** A Rich panel titled `Skill Lens: Search '<query>'`
    with the match counts (and `Agent: <display name>` when filtered), then a
    table: `Skill`, `Match`, `Scope`, `Agents` (or `State` when `--agent` is
    given) and `Excerpt`; when a copy's frontmatter name differs from its
    folder name the Skill cell shows `folder (frontmatter-name)`, so a
    name-tier hit always shows why it matched. All user-derived text (query in the title, names,
    snippets, paths) goes into `rich.text.Text` objects, not markup strings.
    Columns do not wrap: the excerpt column truncates with `…`, so rows stay
    one line at the pinned width of 100. With no results it prints one plain
    line saying nothing matched, plus the unreadable-roots note when there
    are any.
14. **TUI.** Home's `/` filter matches name, frontmatter name, description
    **and body text**; nothing else about Home changes (row order, agent
    filter, preview, keys). `search_text` keeps name, frontmatter name and
    description only; the body is **not** copied into rows. `filter_home_rows`
    gains an optional `bodies` mapping (row key → the entry's existing body
    string, taken from the captured index) and checks a row's body only when
    the cheaper fields did not match, casefolding it at that moment, so no
    second copy of every body is held. The placeholder becomes
    `"Filter by name, description or text  (/)"`. Home stays unranked (scan
    order), the preview does not say which field matched, and short queries
    now match many rows; `FULL_SCREEN_TUI.md` states these limits. A filtering
    measurement over 600 rows with ~4 KB bodies is recorded in the execution
    receipt (§9 asks for measured responsiveness).

## Implementation steps

1. `models/search.py`: `MatchField` (`StrEnum`: `name`, `description`,
   `body`), frozen `SearchHit` and `SearchReport` dataclasses with `to_dict()`
   producing the fields of decision 12; export them from
   `models/__init__.py`.
2. `core/search.py` (pure; no Rich, no Typer):
   - `normalise_query(query) -> str` raising `ValueError` on empty;
   - `snippet(text, needle) -> str` (decision 5);
   - `build_search_report(query, home, cwd, *, agent_id=None, index,
     registry)`: rows from `build_scan_report(home, cwd, index=index,
     registry=registry)`, the entry lookup by `canonical_key`, tiering,
     ordering, counts, and the optional state of decision 7;
   - `run_search(query, cwd=None, *, agent_id=None, index=None,
     registry=None)`: normalise the query and validate the agent **before**
     calling `live_discovery` (imported into `core.search`'s own namespace),
     then build the report — the same shape as `run_compare`.
3. `cli.py`: `search` command with the options of decision 11; `ValueError`
   / `KeyError` → stderr message and exit `2`; `--json` through
   `_emit_json`.
4. `render.py`: `render_search(report, console)` per decision 13.
5. `tui/home.py`: `build_home_rows` takes the frontmatter name from
   `snapshot.index.entries` through `canonical_key` (scan rows do not carry
   it) and adds it to `search_text`; a row with no matching entry keeps name +
   description only. `filter_home_rows(rows, query, agent_id, bodies=None)`;
   Home builds the `bodies` mapping once per snapshot from the same entries
   (it already holds `_entry_by_key`) and passes it; placeholder text.
6. Tests (`tests/test_search.py`, plus snapshot and Home tests), all on the
   synthetic `mock_home`/`tmp_path` fixtures with `--sandbox` for CLI runs,
   never the real `$HOME`, and with no module-level path constants:
   - tiers: one fixture skill per tier, plus exact > prefix > other inside
     the name tier and scan order for ties;
   - frontmatter-name match (folder name differs) found in the name tier;
   - case-insensitivity; multi-word phrase;
   - empty query and unknown agent each → exit 2 **without a walk**, proved
     by a spy on `skill_lens.core.search.live_discovery` (the binding the
     engine calls); the unknown-agent sentence equals `compare`'s;
   - `--agent` filtering; per-copy `ACTIVE` and `SHADOWED` states; a
     frontmatter-name agent (Codex) with one folder whose name ≠ its
     frontmatter name yields `ACTIVE`, not `unknown`; and the two-alias
     `_codex_alias_home` shape (`tests/test_tui_home.py:196-199`) yields
     `AMBIGUOUS` for both copies;
   - plugin scope label; invalid-frontmatter copy still searched (including
     the broken-fence → `body` case); dangling link matches only by name;
   - zero results → exit 0; JSON keys and values from the real CLI output;
   - snippet: window, ellipses, whitespace collapse, control characters and
     ESC removed, casefold-length fallback, line-spanning match, a
     double-space query;
   - Rich markup in a skill body, a skill name and the query printed
     literally; an ESC sequence in a skill name and in a body **not
     emitted** to the terminal;
   - a query beginning with `-` after `--`;
   - read-only proof: every file's bytes and mtime in the fixture tree are
     unchanged after `search`;
   - TUI: the filter keeps a row whose body alone matches, keeps a
     frontmatter-name match, still applies the agent filter, and leaves
     `filter_home_rows` without `bodies` behaving exactly as before;
     placeholder text.
   - New snapshots: `search_results.txt`, `search_agent.txt`,
     `search_no_results.txt`.
7. Mutation checks (project-profile §2): break each guard, show the tests
   fail, restore — tier order swapped; exact/prefix order inside the name
   tier removed; body field dropped; frontmatter name dropped; folder name
   used instead of the lookup name for state; canonical-then-entrypoint state
   match broken; agent filter ignored; validation moved after the walk;
   empty-query check removed; casefold fallback removed; snippet taken from
   the wrong field; control-character stripping removed; `Text` replaced by
   a markup string; unreadable-roots note dropped; TUI body check dropped.
   Survivors are recorded.
8. Documentation per Scope.

## Acceptance

- Issue #7's five checkboxes are met: `search` with a positional query;
  `--agent` and `--json`; name > description > body ranking; TUI integration
  through the Home filter; tests with fixture skills covering all three tiers.
  The `state`-without-`--agent` deviation (decision 7) is stated in the pull
  request.
- Every behaviour decision above holds and is tested.
- No existing snapshot, golden or JSON shape changes; existing tests pass
  unchanged.
- Read-only proof passes; the TUI AST guard passes unchanged.
- The four gates pass: `pytest --cov=skill_lens` (coverage ≥ 90%), `mypy`,
  `ruff check .`, `ruff format --check .` — on this machine compared with the
  recorded baseline, and on the pull request's macOS CI.
- Mutation results and the TUI filtering measurement are recorded in the
  execution receipt.

## Review decisions

Round 1 — Fable 5.2, `changes_required`, 4 blockers, 14 suggestions.

- **B1 Accepted.** State was resolved with the folder name; frontmatter-name
  agents resolve by `lookup_name_for_entry`. Reproduced by the critic in a
  temporary sandbox (`resolve_skill("alias-one", "codex")` → no candidates;
  with the lookup name `"shared"` → `ACTIVE`). Decision 7, step 2, a test and
  a mutation now use the lookup name.
- **B2 Accepted.** `_emit_json` sorts keys (`models/__init__.py:73-80`), so a
  key-order promise could never be seen. Decision 12 now states sorted keys;
  tests check keys and values on real CLI output.
- **B3 Accepted.** A new public JSON shape is High risk (project-profile §7).
  Risk raised to High; the requester's explicit choice of a single council
  member for both stages is recorded under Risk and review and will be
  disclosed in the pull request.
- **B4 Accepted.** The overlap claim about issue #6 was wrong. Current state
  now lists the real shared files; README wording drops the count and the spec
  subsection is appended, so whichever lands second rebases with small text
  conflicts only.
- Suggestions accepted: scanner line references; the capture-budget wording;
  no second copy of bodies in Home rows plus a measurement; the state
  deviation stated for the owner; frontmatter name in the name tier (CLI and
  Home); controls resolved once and passed to `resolve_skill`; the broken-fence
  body behaviour; `canonical_key` named; snippet rules for control characters,
  ESC and line-spanning matches; query escaped in the title and `Text` cells;
  no-wrap truncating columns before snapshots are pinned; spies on the engine's
  own `live_discovery` binding for both pre-walk errors and the exact
  unknown-agent sentence; the extra mutations; "copy" wording; the `--`
  rule for queries starting with `-`; TUI limits written into
  `FULL_SCREEN_TUI.md`; `tui/help.py` moved to Excluded.

Round 2 — Fable 5.2, **`pass`**, no blockers. It re-checked all four round-1
blockers against the code (reproducing B1's fix in a temporary sandbox) and
judged the B3 recording adequate. Its nine suggestions were adopted as
clarifications before freezing: the expected state for the two-alias fixture
is `AMBIGUOUS` (single alias → `ACTIVE`); the exception is named plainly as
mission-scoped, with the coordinator-implements exception listed beside it
(suggestion 2 also asked whether the requester was told of the High rating:
the requester's instruction removed any wider council and asked not to stop,
so the single-critic choice stands and is disclosed in the pull request and to
the requester rather than paused on); the snippet window re-finds a cleaned
query (double-space test); `frontmatter_name` is added to each JSON result and
shown in the Skill cell; `total`/`counts` count filtered results; "not
emitted" wording and an ESC-in-name test; where `build_home_rows` gets the
frontmatter name; the #6 plan's `README.md:225` edit noted.

## Execution receipt

(Append-only; filled during the mission.)

**2026-11-21 — planning.** Round 1 (Fable 5.2): `changes_required`, 4
blockers, all accepted. Round 2 (fresh Fable 5.2 session): `pass`. Both
critics left the checkout unchanged (`git status --porcelain` and SHA-256 of the
plan, `cli.py` and `tui/home.py` identical before and after each dispatch).
Frozen at `4b15862983fad503871387a150951369494f0f62`; reference recorded in
`6a1291d`.

**Environment.** The contributor's laptop runs Windows 11, Python 3.13.14,
which this project does not support (`AGENTS.md` rule 5). Tools were pinned to
the `uv.lock` versions in a local `.venv`: ruff 0.16.9, mypy 2.3.1,
pytest 9.1.1, typer 0.27.2, textual 8.2.8, rich 15.0.0. (A newer ruff, 0.17.6,
reports one pre-existing `SIM102` in `core/discovery.py:606`; the locked
0.16.9 does not.)

**Baseline on `main` (Windows).** `ruff check .` clean; `ruff format --check .`
clean; `mypy` clean. `pytest` stops at collection in `tests/test_parser.py`
(`os.geteuid` does not exist on Windows), so the suite was run with
`--ignore=tests/test_parser.py`: 249 failed + 1 coverage error, 1171 passed,
2 skipped, coverage 79.18%. All of these are Windows-only (symlinks, POSIX
permissions, paths); none touch this change's behaviour.

**Implementation** — commit `229e7b6` (coordinator implemented and committed,
per the recorded requester exception).

- Gates after the change (Windows, same pins): `ruff check .` clean,
  `ruff format --check .` clean, `mypy` clean (50 source files).
- New and touched tests: `tests/test_search.py`, the three search snapshot
  tests and the two new Home tests — 39 passed, 2 skipped. Both skips are
  Windows-only (creating a symlink; an ESC character in a folder name) and
  run on CI.
- Full suite, same flags as the baseline: 250 failed, 1205 passed, 4 skipped.
  Against the baseline list, the failures are the same set except three
  timing-sensitive TUI tests that swapped places
  (`test_tui_app.py::test_headless_report_worker_unexpected_error_marks_failed_and_quits_with_3`,
  `test_tui_app.py::test_real_worker_refresh3_finishes_before_refresh2_stale_error_rejected`,
  `test_tui_routing.py::test_explicit_tui_piped_subprocess_exits_promptly`);
  re-running those three gave 3/3, 3/3 and 2/3 passes, so they are flaky on
  Windows, not caused by this change. Every failure in the five touched or new
  test files (`test_search`, `test_render_snapshots`, `test_tui_home`,
  `test_cli`, `test_tui_read_only`; 30 in all) is in the baseline list. The
  coverage gate cannot be judged on Windows (79% on the untouched baseline);
  new modules: `core/search.py` 97%, `models/search.py` 100%. **The pull
  request's macOS/Ubuntu CI run is the authoritative gate.**
- Mutation checks (project-profile §2): 19 mutations, all killed, none
  survive — tier order; exact/prefix order inside the name tier; body field
  dropped; frontmatter name dropped; folder name used instead of the lookup
  name for state; canonical-then-entrypoint state match (survived the first
  run, killed after adding `test_copy_state_prefers_canonical_then_entrypoint`);
  agent filter ignored; validation moved after the walk; empty-query check
  removed; casefold fallback removed; snippet from the wrong field;
  control-character stripping (snippet); control-character replacement
  (renderer); `Text` replaced by a markup string; unreadable-roots note
  dropped; excerpt refit removed; TUI body check dropped; TUI frontmatter name
  dropped.
- Home filter measurement (`FULL_SCREEN_TUI.md` §9), 600 rows with 4 KB bodies,
  30 runs each, Intel Core (family 6 model 126) laptop: old filter 0.12 ms
  median; new filter with a name hit on every row 0.10 ms; new filter with a
  body-only word (every body scanned) 3.18 ms median, 5.53 ms worst — well under
  one 16 ms frame per keystroke.

**Deviations found during implementation (no behaviour, scope or JSON change):**

1. Rich `Text` does **not** remove control characters, contrary to the
   expectation recorded in plan round 2. `render.py` therefore replaces C0,
   DEL and C1 characters with `?` in every search-derived string (`_safe`);
   tests pin that ESC sequences in a name, the query and a real folder name are
   not emitted. This makes decision 5's "not emitted" promise hold.
2. The terminal excerpt is re-cut to its column (`core/search.refit`) so a
   mid-line match stays visible at 80 columns; the JSON keeps the full
   80-character excerpt. Pure presentation.
3. When casefolding lengthens the cleaned excerpt text, the window is still
   placed on the (approximate) match rather than falling back to the first 80
   characters, matching decision 5's "find it again" wording more closely.

**Final review — Fable 5.2: `pass`, no blockers**, checkout unchanged. Of its
12 suggestions: adopted — keep the matched word visible in narrow columns (2
above); approximate re-find for length-changing casefold (3 above); a
`build_search_report` test with an unreadable root; "no skill file is read
again" wording in `CHANGELOG.md` and the spec (`--agent` reads that agent's
settings once, like `why`); `render.py` line in the `AGENTS.md` tree; committed
snapshots checked as LF (`git ls-files --eol`: `i/lf`); this receipt. Not
adopted, recorded for the owner: a long folder name can still truncate the
`(frontmatter-name)` part of the Skill cell at 100 columns (the JSON
`frontmatter_name` field is complete); Unicode format characters such as
U+202E (right-to-left override) are not removed — outside this plan's C0/C1
scope, suggested as a follow-up; the engine accepts `DiscoveryIndex` only (no
snapshot-backed caller exists yet); `cli.py` maps any `KeyError`/`ValueError`
to exit 2, the same pre-existing pattern as `compare`; consoles narrower than
about 60 columns squeeze the Scope column (no crash, no line overflow).
