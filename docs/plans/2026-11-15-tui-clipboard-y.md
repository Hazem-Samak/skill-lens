# Plan: TUI clipboard copy via `y` (OSC 52)

Status: Agreed
Authorization: User (Hazem), 2026-11-15, this mission: plan GitHub issue #8 on
`feat/tui-clipboard` with the named planning council, then commit and freeze the
agreed plan. Implementation is explicitly NOT authorized yet ("We will not start
the implementation yet"). No push, release, or publication is authorized.
Owner decisions (2026-11-15, answering the council's escalation of issue #8's
fallback criterion): (1) block known blockers — tmux and GNU screen — and emit
elsewhere, with a payload size guard; (2) keep the issue's "Copied …"
confirmation wording as explicitly accepted best-effort, with the limitation
stated in Help, README and spec; (3) do not special-case Terminal.app — emit,
trusting the macOS 14+ evidence, and record the conflicting Textual docstring.
Amendment 1 authorization: User (Hazem), 2026-11-16, explicit approval of the
minimal packaging-manifest scope amendment recorded below ("Authorize minimal
amendment"). No push, release, or publication is authorized.
Roster: Coordinator — Qoder (this session; model family unverified, disclosed
below). Plan critics — Grok CLI `grok-4.7` with `--reasoning-effort high`;
MCode CLI `minimax/MiniMax-M3.1-Flash` with thinking `xhigh`. Identity evidence
per round is in the execution receipt; each round uses fresh sessions of the
same user-named routes. Implementer and final critics: unselected; they must be
named by the user before any implementation dispatch, not inherited from this
roster.
Reference: pending until Step 5 (amendment 1 freeze)
Risk and review: Normal. Additive, presentation-only TUI feature: a new key
binding, plain-text assembly from already-frozen report models, and one
escape-sequence emission through Textual's own API. No change to path
resolution, data formats, registry TOML, exit codes, permissions, the snapshot
service, or the session controller contract. The read-only AST guard is not
modified; the feature must pass it unchanged. Normal requires one independent
critic; the user named two, so both review with complementary questions
(council §6). Family disclosure (council §1): the critics' advertised families
are xAI Grok and MiniMax — distinct from each other. The coordinator's family
is unverified; no verified-diversity claim is made. The user named this set
for this mission, which records acceptance of the named set.
Expected child tasks: planning — 2 critics per round, 4 rounds, 8 dispatches
total, all settled. Round 1: both `changes_required`, all findings resolved.
Round 2: both confirmed every round-1 item resolved; narrow new gaps
(overlapping), all resolved. Round 3: both confirmed every round-2
correction; two findings remained (one character-level literal, one oracle
precision), both resolved. Round 4: both **pass**, zero blockers; their
non-blocking precision suggestions adopted as coordinator clarifications
(recorded below). Implementation (later, separately authorized) — 1
implementer + final critic(s) per the risk level then chosen.

## Outcome

In the full-screen TUI, pressing `y` (yank) copies the currently focused
content to the system clipboard through OSC 52 — a terminal escape sequence,
so it works over SSH with no external tools and no new dependencies. The user
gets a brief on-screen confirmation, and a clear fallback message in terminals
known to block OSC 52 (tmux, GNU screen). Issue #8's acceptance checklist is
the contract, as sharpened by the owner decisions above.

## Current state

Verified facts (read on 2026-11-15, branch `feat/tui-clipboard`, base commit
`4e319b7c6c7e4e8fbaa6d6101db34e12c65f8ab5`, no commits ahead of `main`;
round-1 and round-2 review corrections incorporated):

- Issue #8 defines the behaviour: `y` on Home copies the selected skill's
  canonical path; on Why the resolution explanation as plain text; on Diff the
  unified diff; in JSON view the raw JSON; on Doctor the selected finding's
  details. Status-bar confirmation, graceful fallback, key bar updated, tests
  without a real clipboard.
- The spec defers clipboard today: `FULL_SCREEN_TUI.md:140`, §8.6 at `:678`,
  and Q3 at `:1311` — which already notes Textual can copy via OSC 52 with no
  extra dependency. The §8.2 keymap table (`:468-486`) lists every key and must
  gain `y`; the filter prose at `:503-506` explains non-priority `?` staying
  literal filter text and must say the same for `y`. The readiness row at
  `:1381` is a historical finding and stays as one.
- Textual 8.2.8 is the installed version and the `pyproject.toml` floor.
  `App.copy_to_clipboard(text)` base64-encodes the UTF-8 text and writes
  exactly one `\x1b]52;c;<base64>\a` via `self._driver.write`, and stashes the
  text in the public `App.clipboard` property (`textual/app.py:1014-1021`,
  `:1770-1786`). Its docstring says it does not work on macOS Terminal;
  community evidence (georgemandis/pbcopy-pbpaste-remote README) says
  Terminal.app supports OSC 52 writes from macOS 14, enabled by default. The
  conflict is recorded; the owner decision is to emit. Calling this API is not
  a banned terminal write under the AST guard
  (`tests/test_tui_read_only.py`): no `print`, `sys.stdout/stderr.write`,
  `console.print`, `subprocess`, or file write is involved.
- `HeadlessDriver.write` is a no-op, but `copy_to_clipboard` still sets
  `_clipboard` and calls `driver.write`. Tests spy on the **instance** driver's
  `write` to capture the exact sequence, and assert the public `App.clipboard`.
- **Home's key bar is hand-written.** `_hint_bar()` (`tui/home.py:327-344`)
  builds a manual `key_bar()` map mounted as `#footer-help` (`:594`). It is
  NOT the binding-driven `KeyBar` (`tui/theme.py:288-321`), used only by Why,
  Diff, Doctor, Agents and Compare. `tests/test_tui_visual.py:369-406` pins
  Home's exact 12-key list and requires every `show=True` Home binding to
  appear in the map. Most Home bindings are `show=False`; only `h` is
  `show=True`.
- Home rows: `key=entry.canonical_path` (`home.py:180`) but the preview shows
  `row.display_path` (`:189`, `:281`), which `paths.display`
  (`core/paths.py:118-134`) collapses to `~/...`. Issue #8 asks for the
  canonical path.
- **JSON-mode state and the JsonView document diverge in reachable states.**
  Every screen has a public `json_mode` property (`home.py:987-990`,
  `why.py:803`, `diff.py:233`, `doctor.py:285`, `agents.py:207`,
  `compare.py:254`). Home's `leave_json_mode()` (`home.py:1049-1061`) clears
  the flag but NOT the document, so after `J → J` the view still holds the
  scan JSON in ordinary mode. Compare calls `_refresh_json()` when the report
  becomes ready (`compare.py:849-855`), outside JSON mode. Conversely, JSON
  mode can show an explanation: `show_explanation` clears `document`
  (`json_view.py:112-123`; Home's `_refresh_json` at `home.py:1006-1013`).
  The copy gate must therefore be the screen's `json_mode`, with
  `shows_document` deciding only inside that mode.
- **Compare's picker sub-mode cannot enter JSON mode.** `action_toggle_json`
  and `enter_json_mode` return unless `_mode == "result"`
  (`compare.py:1177-1187`); the picker Help already says `J` is "Unavailable
  in the picker; it applies only to result mode." (`compare.py:411-415`).
- Why content: the title block is built by `_refresh_title`
  (`tui/why.py:916-948`): Installation, Name (when the entry exists), Working
  directory, Agent, optional Unavailable agent IDs, Lookup name, Collision
  policy (evidence), Report-wide headline, each report note ONCE; the
  Installation and Working directory paths go through `snapshot_path`
  (`:925-935`). `_build_candidate_blocks` (`:163-213`) builds per-candidate
  plain bodies repeating every report note inside each block; the Collapsible
  title is `{mark} {title_name}  ({state})` (`:1097-1102`). Mounted separately
  and NOT part of the explanation data: the zero-candidate sentences
  (`:1070-1075`), the no-match notice (`:1082-1088`), the agent strip and the
  report-status line (`#why-report-status`).
- Diff content: the render flow (`tui/diff.py:655-724`) is: `not found` →
  `not_found_message`; else summary (`Copies: N`, `Baseline: …` via
  `_summary_content`, both paths through `snapshot_path`), then
  `no_differences_message` when `not report.has_differences` (listing then
  only if `needs_listing`), then INSIDE the listing branch: per-copy
  `_copy_content` — heading via `_heading_content` from `HeadingParts`
  (mark, display path, variant segment exactly as built by `copy_heading`
  with its leading space and brackets, ` (scope, parse_status)`, two spaces,
  status), then `copy_body` indented two spaces OR per-file lines
  `  {path} {change}` plus the marker ` binary` (ONE leading space, NO
  brackets, only when the file is binary — `diff.py:763-772`,
  `BINARY_MARKER = "binary"`), with `file_notice` indented four spaces or the
  FULL `unified_text(file)` output verbatim (including its `---`/`+++`
  headers), then `copy_truncation_notice` indented two spaces — then the
  `report_truncation_notice` with no indent, still inside the listing branch;
  finally the notes block (`_notes_content`) OUTSIDE that branch when
  `baseline_path is not None`. Blocks are separated by one blank line
  (`.diff-block { margin-bottom: 1; }`, `diff.py:177-179` — a CSS margin
  OUTSIDE the Static text; the `#diff-content` container is a Vertical,
  `diff.py:254`). The pure helpers live in `presentation/text.py` and stay
  unedited.
- Doctor: `finding_detail_text(finding)` (`tui/doctor.py:131-143`) is already
  the plain detail block shown in the detail pane.
- JSON: `JsonView.document` is the exact serialized string; `shows_document`
  is true only when a document is set (`tui/json_view.py:84-96`). `dumps()`
  (`models/__init__.py:73-79`) adds no trailing newline; the CLI's
  `_emit_json` (`cli.py:124-130`) prints via `console.print`, which adds
  exactly one. The TUI document equals CLI `--json` stdout minus one trailing
  newline; the existing six-screen CLI JSON oracle lives at
  `tests/test_tui_help.py:2131-2169` (`_cli_document` uses
  `.removesuffix("\n")`). `tests/test_tui_json.py:685-695` forbids
  save/export/clipboard/write actions among **JsonView's own** bindings — the
  copy action lives on the screens, named `copy`, and adds no JsonView
  binding. Checked and clear (round 2): no screen, the app, or Textual binds
  `y`; no `action_copy` exists yet; `copy` trips none of the forbidden
  substrings.
- **Screen lifecycle:** the app pushes detail screens OVER the mounted Home
  and pops them back (`app.py:283-438`); Home is never popped, so its
  `on_unmount` (`home.py:629-630`) runs only at teardown. Home has no
  `on_screen_suspend`; its suspend paths are `suspend_why()` (`home.py:641`,
  called by the app on every detail open) and `suspend_help()` (`:808`).
  Why/Diff/Doctor/Agents/Compare already handle `on_screen_suspend`
  (`why.py:363`, `diff.py:268`, `doctor.py:340`, `agents.py:253`,
  `compare.py:332`). Textual 8.2.8 ships `ScreenSuspend`
  (`textual/events.py:926-928`).
- Notice mechanisms today are per-screen and semantic (Home's
  `#removal-notice` / `#doctor-jump-notice`, Doctor's `navigation_notice`,
  Why/Diff status lines). Copy confirmation gets its own transient line.
- Help is per-screen and mode-branched (`help_context()`); `HelpContext`
  carries `notes` rendered as SCREEN NOTES (`help.py:88`, `:117-119`), so the
  limitation sentence can live in each screen's context without editing
  `help.py`. Home's filter-focused branch enumerates the literal characters
  "q, r, h, d, g, c, J and ?" (`home.py:731-735`). Textual's Input consumes
  printable keys, so a non-priority `y` stays filter text; `priority=True`
  would break that contract.
- OSC 52 environment evidence (verified 2026-11-15): tmux wiki (Clipboard) —
  default `set-clipboard external` "forbids applications inside from" setting
  the clipboard; `on` allows it but is not detectable from the environment.
  GNU screen passes only short device-control strings (chunking out of
  scope). VTE support is conflicting (tmux wiki: none; pbcopy-pbpaste-remote:
  VTE 0.76+) and VTE is not reliably detectable. xterm and iTerm2 need user
  settings. Terminals cap OSC 52 payloads around 100 KB of base64
  (pbcopy-pbpaste-remote, Limits).
- `README.md:164` lists the main keys; `:175-176` says the TUI never writes —
  that sentence is about files, skills, editors, processes and the network,
  and stays true: OSC 52 is a terminal sequence, not a filesystem write.
  `CHANGELOG.md` has NO Unreleased heading; `[0.2.1]` (line 20) is the
  published release (2026-11-15) and must not be edited.
- Council route evidence: `docs/plans/2026-10-29-tui-u5-diff-json.md` records
  MCode `minimax/MiniMax-M3.1-Flash` / `thinkingLevel: xhigh`; rounds 1–2
  re-verified both routes live (receipt below).

## Scope and boundaries

Allowed files (implementation mission, when authorized):

- `skill_lens/tui/clipboard.py` — NEW: pure copy decision + constants.
- `skill_lens/tui/home.py` — `y` binding, `action_copy`, `#copy-notice`,
  `_hint_bar()` entry, mode-branched help rows + notes, filter
  literal-character list, notice clearing in `suspend_why`/`suspend_help`.
- `skill_lens/tui/why.py`, `diff.py`, `doctor.py`, `agents.py`, `compare.py` —
  `y` binding, `action_copy`, `#copy-notice`, plain-text assembly, help rows
  + notes, notice clearing in `on_screen_suspend` with `on_unmount` as the
  backstop.
- `skill_lens/tui/theme.py` — only if the notice line needs shared CSS
  (per-screen `DEFAULT_CSS` is the natural home).
- `tests/test_tui_clipboard.py` — NEW.
- `tests/test_tui_visual.py` — Home's pinned key list gains `y`.
- `tests/test_tui_home.py` — filter-typing test gains `y`.
- `tests/test_tui_help.py` — mode-specific help text assertions.
- `tests/test_tui_read_only.py` — lifecycle traversals gain `y` presses; the
  AST visitor itself is NOT modified.
- `FULL_SCREEN_TUI.md` — Q3 amendment, line 140, §8.6, §8.2 keymap + filter
  prose.
- `README.md` — key list + limitation sentence (never-writes scope kept).
- `CHANGELOG.md` — new `## [Unreleased]` section only, at implementation time.
- `tests/test_tui_packaging.py` — Amendment 1 (2026-11-16): add
  `"skill_lens/tui/clipboard.py"` to `EXPECTED_TUI_MODULES` only; no other
  edit to this file.
- `scripts/smoke_wheel.py` — Amendment 1 (2026-11-16): add
  `"skill_lens/tui/clipboard.py"` to `REQUIRED_TUI_MODULES` only; no other
  edit to this file.
- This plan and its execution record.

Excluded: no change to `core/`, `models/`, `registry/`, `render.py`, the CLI,
`presentation/` (helpers reused, not edited), `tui/help.py` (per-screen
contexts carry the rows and notes), `tui/json_view.py`, the AST guard,
`pyproject.toml`, version numbers, the published `[0.2.1]` changelog section,
or release artifacts. No implementation happens in this mission.

Amendment 1 (2026-11-16, user-authorized): the frozen plan missed that the
new `tui/clipboard.py` module triggers the U9 packaging manifest guard —
`EXPECTED_TUI_MODULES` (`tests/test_tui_packaging.py:78`) and
`REQUIRED_TUI_MODULES` (`scripts/smoke_wheel.py:44`) pin the exact 13-module
TUI manifest, and `test_manifest_covers_every_shipped_tui_source_module`
fails with 14 modules on disk (coordinator-reproduced). The U9 guard comment
(`tests/test_tui_packaging.py:71-77`) prescribes updating both tuples together
when the manifest legitimately grows; the failing guard is the intended
alarm. The amendment adds exactly one entry (`"skill_lens/tui/clipboard.py"`)
to each tuple and carves those two edits out of the exclusions above; every
other exclusion stands. The guards remain exact hand-maintained pins (now 14
modules). No behavior, dependency, version, or release-process change; the
installed-wheel test selection (14 pinned selections) is unchanged.

## Behaviour decisions

1. **Binding.** `Binding("y", "copy", "Copy")` on Home, Why, Diff, Doctor,
   Agents, Compare — non-priority on every screen (Input must keep consuming
   `y` as filter text). On Home `show=False` (like its sibling action keys)
   and the manual `_hint_bar()` gains `("y", "copy")` immediately after
   `("J", "json")`; the pinned visual test becomes the 13-key list
   `q r / a enter d g c h J y tab f1`. On the five `KeyBar` screens
   `show=True`, so the bar renders it automatically. Help itself has no `y`.
   No binding is added to `JsonView`; the screen action is named `copy`.
2. **Content rules — exact recipes.** The JSON-mode branch is evaluated
   FIRST on every screen and is gated on the screen's own `json_mode`
   property — never on `JsonView.shows_document` alone (the document and the
   mode diverge: Home keeps the document after `J → J`; Compare refreshes it
   outside JSON mode).
   - **JSON mode (any of the six screens), `json_mode` true:** if
     `shows_document` is true, copy the exact `JsonView.document` string,
     byte-identical to what `J` displays, which equals CLI `--json` stdout
     minus exactly one trailing newline. If the view shows an explanation
     (`shows_document` false), nothing is copied, notice "Nothing to copy
     yet." — an explanation is never copied as report data.
   - **Home (ordinary):** `controller.selected_key` verbatim — the raw
     canonical path, absolute, NOT the `~`-collapsed display path, even when
     the JsonView still holds a stale document. Empty table / no selection →
     nothing copied, notice.
   - **Why (ordinary, accepted report):** ONE string, defined so the golden
     and the screen-equivalence oracle assert the same text: the plain text
     of `#why-title` exactly as `_refresh_title` builds it with a report
     present, in emission order — Installation (through `snapshot_path`),
     Name (only when the entry exists), Working directory (through
     `snapshot_path`), Agent, optional Unavailable agent IDs, Lookup name,
     Collision policy (evidence), Report-wide headline, each report note
     once. Name, Working directory and Agent appear only when a session
     snapshot is present (`why.py:931-936`); an accepted report implies a
     live session. `fact_block` preserves every character and adds no
     trailing blank
     line (`theme.py:184-195`). A blank line follows the title block ONLY
     when at least one candidate exists; then one block per candidate in
     `report.candidates` order: the Collapsible TITLE line
     `{mark} {title_name}  ({state.value})` (a separate widget from the body,
     `why.py:1096-1108`) followed by the candidate body exactly as
     `_build_candidate_blocks` produces it (the body Static's plain text),
     with one blank line BETWEEN candidates. ALL candidates are included,
     collapsed or not — the copy is data, not the viewport. The per-block
     repetition of report notes is an explicit choice: each block stays
     self-contained, identical to the helper output. A zero-candidate
     accepted report copies the title block ALONE — no trailing blank line.
     Excluded: the zero-candidate sentences (`why.py:1070-1075`, their own
     Statics), the no-match navigation notice (`:1082-1088`, its own
     Static), the agent strip, and the report-status line. No accepted
     report (pending/failed/absent) → nothing copied, notice.
   - **Diff (ordinary, accepted report):** ONE string: the style-stripped
     plain text of the `#diff-content` Statics in mount order, joined by one
     blank line (the on-screen join is the CSS margin
     `.diff-block { margin-bottom: 1; }`, outside the Static text). That
     assembly is (`diff.py:655-724`): `not_found_message` ALONE when
     `not report.found`; else the summary (`Copies: N` / `Baseline: …`,
     paths through `snapshot_path`); `no_differences_message`
     (`{label}{body}`) when `not has_differences`; the per-copy listing when
     `has_differences` or `needs_listing` — heading line
     `{mark} {display_path}{variant} ({scope}, {parse_status})  {status}`
     where `{display_path}` is `snapshot_path(snapshot, copy.path)` and
     `{variant}` is `HeadingParts.variant` verbatim (leading space and
     brackets included), then `copy_body` indented two spaces OR per-file
     lines `  {path} {change}` plus the marker ` binary` (ONE leading space,
     NO brackets, only when the file is binary; the per-file `{path}` is the
     RAW `file.path` from the report, NOT snapshot-mapped — only the heading
     and summary paths are, `diff.py:749,763-772`) with `file_notice`
     indented four spaces or the FULL `unified_text(file)` output verbatim
     (including its `---`/`+++` headers), then `copy_truncation_notice`
     indented two spaces; then `report_truncation_notice` with no indent,
     INSIDE the listing branch only; then the notes block as
     `_notes_content` renders it, OUTSIDE the listing branch, when
     `baseline_path is not None`.
     Implemented as a pure function in `tui/diff.py` reusing the unchanged
     `presentation/text.py` helpers and the same order as the screen. No
     accepted report → nothing copied, notice.
   - **Doctor (ordinary):** `finding_detail_text` of the selected finding.
     No findings / no selection → nothing copied, notice.
   - **Agents (ordinary) and Compare RESULT sub-mode (ordinary):** nothing to
     copy; notice "Nothing to copy here. Press J for JSON, then y."
   - **Compare PICKER sub-mode:** nothing to copy; notice "Nothing to copy
     in the picker. Choose two agents first." — `J` is inert in the picker
     (`compare.py:1177-1187`), so the notice must not point at it.
3. **Emission.** One pure decision function in `tui/clipboard.py` —
   `copy_decision(text, env)` returning SENT / BLOCKED / TOO_LARGE — plus a
   thin screen wrapper that reads `os.environ` AT CALL TIME, passes it in,
   and calls `app.copy_to_clipboard(text)` on SENT (runtime and tests share
   the same code path). Textual owns the base64 + OSC 52 framing. The pure
   function uses `env.get("TMUX")` and `env.get("TERM", "")` (missing keys
   mean not blocked; no module-level expansion). The pure function's unit
   tests pass their own mapping; the SCREEN-level tests monkeypatch
   `os.environ` (`setenv`/`delenv`), because the wrapper reads the live
   environment at call time — that is what makes the runtime path and the
   test path the same code path. Precedence: BLOCKED is checked before
   TOO_LARGE, so the notice is determined when both apply.
4. **Fallback (owner decision 1).** BLOCKED when `env.get("TMUX")` is
   non-empty (tmux; default `set-clipboard external` forbids inner apps —
   tmux wiki) or `env.get("TERM", "")` starts with `screen` (GNU screen;
   passes only short DCS). BLOCKED emits nothing and shows "Clipboard not
   supported in this terminal". Terminal.app is NOT special-cased (owner
   decision 3): emit, trusting the macOS 14+ evidence; the conflicting
   Textual docstring is recorded in the spec amendment. There is NO
   `TERM_PROGRAM` gate. VTE, xterm and iTerm2 settings are not detectable;
   they are documented limitations, not detection targets.
5. **Size guard.** `MAX_COPY_BYTES = 75_000` UTF-8 bytes — a deliberately
   conservative stand-in for the ~100 KB BASE64 cap (75_000 × 4/3 = 100_000
   base64 characters; pbcopy-pbpaste-remote Limits), not an exact reading of
   the cited limit. At most `MAX_COPY_BYTES` is emitted; strictly over it:
   TOO_LARGE, no emission, notice "Too large to copy via terminal clipboard".
   The exact boundary (75_000 bytes) is tested.
6. **Confirmation (owner decision 2).** A dedicated transient `#copy-notice`
   Static on each copying screen — the realisation of issue #8's "status-bar
   confirmation", separate from the session status/removal/navigation
   notices. Success messages, exactly: "Copied skill path", "Copied resolution
   explanation", "Copied diff", "Copied JSON", "Copied finding details".
   Other messages, exactly: "Nothing to copy yet." (no report/selection/
   document, including an explanation in JSON mode), "Nothing to copy here.
   Press J for JSON, then y." (Agents ordinary, Compare result ordinary),
   "Nothing to copy in the picker. Choose two agents first." (Compare
   picker), "Clipboard not supported in this terminal" (BLOCKED), "Too large
   to copy via terminal clipboard" (TOO_LARGE).
   The "Copied …" wording is the owner's explicitly accepted best-effort: it
   means the OSC 52 sequence was sent, not that the terminal confirmed a
   clipboard change. Help, README and the spec must state that same limit.
   Notice lifecycle: `COPY_NOTICE_SECONDS = 3.0` module constant in
   `tui/clipboard.py`; screens read it through the module
   (`clipboard.COPY_NOTICE_SECONDS`, never a `from … import` binding, so
   monkeypatching works). A new notice stops the previous timer
   (`Timer.stop`) before starting its own. Clearing hook: the notice is
   cleared and the timer stopped when the screen is SUSPENDED —
   `on_screen_suspend` on Why/Diff/Doctor/Agents/Compare, and
   `suspend_why()` on Home (which is never popped and has no
   `on_screen_suspend`; `suspend_help()` delegates to `suspend_why()` at
   `home.py:812`, so the clearing code lives in `suspend_why()` ONLY — one
   site, no double-clear); `on_unmount` remains the backstop for popped
   detail screens. On the five detail screens the clearing runs at the TOP
   of `on_screen_suspend`, BEFORE it delegates to `suspend_detail()` /
   `suspend_help()`: the app pre-suspends the origin before pushing the
   covering screen (`app.py:265`, `:320`), so Textual's `ScreenSuspend`
   arrives with the screen already `_suspended` and the delegated method's
   early return (`why.py:377-378`, `diff.py:335-336`, `doctor.py:417-418`,
   `agents.py:335-336`, `compare.py:435-436`) would skip a clearing placed
   after it. Home's `suspend_why()` has no such guard. A covered screen must
   never show a stale "Copied …" line when revealed again.
7. **Help and key bar.** Every screen's `help_context()` gains mode-specific
   `y` rows that match decision 2 exactly:
   - Ordinary Home/Why/Diff/Doctor: what is copied there.
   - Ordinary Agents and Compare result: `y` copies nothing; press `J` then
     `y`. Compare picker: `y` copies nothing until a comparison result is
     open — no `J` pointer (consistent with the existing picker `J` row).
   - JSON mode on every screen: when `shows_document` is true, `y` copies
     the displayed JSON; when the view shows an explanation, `y` copies
     nothing. The row must be conditional, not unconditional.
   - Home's filter-focused branch sentence becomes, in full: "Edits the
     filter literally. q, r, h, d, g, c, J, y and ? are characters here; use
     F1 for Help."
   - The best-effort limitation lives in each screen's `HelpContext.notes`
     (no `help.py` edit): copy sends OSC 52, the terminal may ignore it, tmux
     and GNU screen are blocked. README states the same three facts.
   The key bar changes per decision 1.
8. **Docs.** `FULL_SCREEN_TUI.md`: Q3 gains a dated amendment (2026-11-15,
   issue #8) recording the three owner decisions and the evidence conflicts
   (Textual docstring vs macOS 14+ report; tmux wiki vs VTE 0.76+ report),
   and pointing at the historical readiness row `:1381`. Line 140 and §8.6
   KEEP the 0.2 deferral sentence visible and add the dated lift beside it
   ("0.2 adds no copy action; lifted after 0.2.1 by the 2026-11-15 amendment,
   issue #8") so the published release and the new decision are not one
   claim. §8.2 keymap gains the `y` row; the filter prose (`:503-506`) says
   non-priority `y` stays literal filter text, same as `?`. `README.md`: main
   keys gain `y` plus the limitation sentence; the never-writes sentence
   keeps its scope (files, skills, editors, processes, network).
   `CHANGELOG.md`: at implementation time add a new `## [Unreleased]` heading
   ABOVE `[0.2.1]` with the feature note; never insert into the published
   section. No version bump.

## Implementation steps

(For the later, separately authorized implementation mission.)

1. `tui/clipboard.py`: `CopyDecision` enum, pure `copy_decision(text, env)`
   (env.get semantics; BLOCKED before TOO_LARGE), `MAX_COPY_BYTES`,
   `COPY_NOTICE_SECONDS`.
2. Per-screen `action_copy` + `#copy-notice` widget + timer handling:
   `json_mode` branch first on every screen, content assembly per decision 2
   reusing existing builders/helpers; the Diff plain-text assembler as a pure
   function in `tui/diff.py`; notice clearing in the suspend paths.
3. Home `_hint_bar()` entry; help rows + notes per decision 7; README, spec
   and (implementation-time) changelog per decision 8.
4. Tests per Acceptance, mutation-checking every new guard per the AGENTS.md
   habit: a test that cannot fail is worse than no test.
5. All four gates on the final tree.

## Acceptance

- Issue #8 checklist, mapped to falsifiable tests:
  - `y` copies the exact recipe content on Home (raw canonical path), Why,
    Diff, Doctor, and the exact document in JSON mode on all six screens.
    Why/Diff goldens are AUTHORED FROM THE PLAN'S RECIPES (never captured
    from the implementation's own output) and pinned by exact equality,
    including no-differences, not-found, truncation and binary cases for
    Diff. The SAME string is checked against a screen-equivalence oracle:
    Why — the plain text of `#why-title`, a blank line only when at least
    one candidate exists, then per candidate its Collapsible title LABEL
    `{mark} {title_name}  ({state.value})` (read `Collapsible.title`, NOT
    the rendered `CollapsibleTitle` widget, which prepends a `▶`/`▼`
    disclosure symbol and a space — `textual/widgets/_collapsible.py:85-90`)
    plus its body Static's plain text, one blank line between candidates (the
    zero-candidate and no-match Statics in `#why-candidates` are NOT part of
    the oracle); Diff — the style-stripped plain text of the `#diff-content`
    Statics in mount order joined by one blank line, and `not_found_message`
    alone for a not-found report. Golden and oracle assert ONE string, so a
    recipe-authored golden cannot drift from the screen. JSON-mode copies
    reuse the existing six-screen CLI JSON oracle
    (`tests/test_tui_help.py:2131-2169`): copy == CLI stdout
    `.removesuffix("\n")`.
  - **Mode-gate regression tests:** Home `J → J` round trip — ordinary `y`
    afterwards copies the canonical path, NOT the stale scan JSON; Compare
    ordinary RESULT mode with the report document already refreshed — `y`
    copies nothing and shows the pointer notice; JSON mode showing an
    explanation — `y` copies nothing.
  - OSC 52 emission verified by spying on the instance `driver.write`:
    exactly one write, payload starts `\x1b]52;c;`, ends `\a`, base64
    round-trips to the exact text; public `App.clipboard` equals the text.
  - Confirmation notice appears with the exact decision-6 message and
    clears. Timer test: screens read `clipboard.COPY_NOTICE_SECONDS` through
    the module; patch it to C; copy; wait 2C/3; copy again; wait C/2; assert
    the notice is STILL present (the first timer was stopped); wait past C;
    assert it is gone. Suspend tests, by route: copy on Home → open Why →
    return, notice gone; copy on Why → F1 (Help covers Why) → notice cleared
    → close Help, still gone; copy on Why → open Diff from Why (Why is
    covered via `suspend_detail` / `ScreenSuspend`, `app.py:314-323`) →
    notice cleared. Likewise for each remaining detail screen's suspend
    path.
  - Fallback: with `TMUX` set or `TERM=screen-256color`, ZERO `driver.write`
    calls and the blocked message. Every clipboard test pins `TMUX` and
    `TERM` explicitly in BOTH branches (e.g. unset/`xterm-256color` vs
    set/`screen-256color`); `TERM_PROGRAM` is NOT pinned and NOT read — no
    `TERM_PROGRAM` gate exists (owner decision 3). Missing `TERM`/`TMUX`
    keys → not blocked, copy proceeds.
  - Size guard: exactly `MAX_COPY_BYTES` UTF-8 BYTES → emitted; one byte
    over → no write, too-large message. The boundary string must be
    multi-byte (e.g. built from `é`, 2 bytes per character) so a
    character-count implementation (`len(text)`) FAILS the test. BLOCKED
    outranks TOO_LARGE when both apply.
  - Compare messages: picker shows "Nothing to copy in the picker. Choose
    two agents first."; result ordinary shows the `J` pointer; both texts
    asserted.
  - Key bar: Home's `#footer-help` pins the 13-key list including `y`;
    `KeyBar` screens show `y`; Help names `y` correctly in EVERY mode branch
    (ordinary, JSON document, JSON explanation, filter focus, Compare
    picker/result); the limitation sentence itself is asserted in Help
    notes and README (OSC 52 sent / terminal may ignore / tmux and GNU
    screen blocked), not merely the key's presence; `y` typed in the Home
    filter stays literal (extended typing test); `J`, `?`/F1 and all
    existing bindings unchanged (existing suites green).
- Edge cases tested: explanation-only JSON view, pending/failed Why/Diff
  report, empty Home table, Doctor with no findings, Why zero-candidate
  report (title block ALONE, no trailing blank line, no empty-candidate
  sentences), Agents/Compare ordinary in both Compare sub-modes, repeated
  `y`, notice replacement/expiry/suspend-clearing.
- `tests/test_tui_read_only.py`: AST guard still zero violations (visitor
  unmodified); lifecycle traversals extended with `y` preserve synthetic
  targets byte-for-byte.
- No new dependency; CLI behaviour and pinned CLI snapshots unchanged.
- Four gates: `pytest --cov=skill_lens` (coverage ≥ 90%), `mypy`,
  `ruff check .`, `ruff format --check .`.

## Review decisions

Round 1 (2026-11-15): both critics `changes_required`; every finding
reproduced against the source before acceptance. Reports preserved at
`/tmp/skill-lens-clipboard-council/reports/{grok-r1,mcode-r1}.md`.

- **Accepted — grok B1 / mcode B1 (Home key bar).** Reproduced:
  `home.py:327-344,594`, `tests/test_tui_visual.py:369-406`. Fixed: decision 1
  (manual `_hint_bar` entry, Home `show=False`, five KeyBar screens
  `show=True`), `tests/test_tui_visual.py` allowed, current-state corrected.
- **Accepted — grok B2 / mcode B2 (Home copy target).** Reproduced:
  `home.py:180,189,281`, `core/paths.py:118-134`. Fixed: decision 2 pins the
  raw canonical path; exact absolute-string test.
- **Accepted — grok B3 / mcode B3 (Why copy undefined).** Reproduced:
  `why.py:916-948,163-213,1097-1102`. Fixed: exact recipe, golden tests.
- **Accepted — grok B4 / mcode B3 (Diff copy undefined).** Reproduced:
  `diff.py:99-108,655-724,726-780`. Fixed: full assembly recipe, pure
  function, presentation/ unedited, golden tests.
- **Accepted — grok B5 / mcode B4 (honesty + fallback).** Reproduced:
  `textual/app.py:1770-1786`; tmux wiki; pbcopy-pbpaste-remote README.
  Escalated to the owner (decisions in Authorization). mcode's
  Apple-Terminal-block requirement **rejected by owner decision** (emit),
  evidence conflict recorded; VTE detection **deferred as undetectable**,
  documented as a limitation.
- **Accepted — mcode B5 (test env pinning), B6 (timer lifecycle), B7 (JSON
  newline).** Reproduced and fixed in decisions 2/6 and Acceptance.
- **Accepted — all round-1 suggestions** (non-priority y, filter list, §8.2
  keymap, :1381 historical, CHANGELOG Unreleased, public clipboard,
  Agents/Compare help, instance-driver spy, size guard, notice-line
  realisation, README y).

Round 2 (2026-11-15): both critics confirmed EVERY round-1 item resolved in
the operative sections, then reported narrow new gaps (reports
`reports/{grok-r2,mcode-r2}.md`). All reproduced and accepted:

- **Accepted — mcode r2 B1 (JSON gate signal).** Reproduced:
  `home.py:1049-1061` (document survives `J → J`), `compare.py:849-855`
  (refresh outside JSON mode), `json_mode` properties on all six screens.
  Fixed: decision 2 gates on `json_mode`, `shows_document` only inside it;
  Acceptance adds the two reachable-state regression tests.
- **Accepted — mcode r2 B2 / grok r2 B1 (Compare picker pointer).**
  Reproduced: `compare.py:1177-1187` (`J` inert in picker), `:411-415`
  (existing picker Help). Fixed: distinct picker message and Help row
  (decisions 2, 6, 7); `J` pointer only for Agents ordinary and Compare
  result ordinary; both texts asserted.
- **Accepted — mcode r2 B3 (Home notice clearing).** Reproduced: Home is
  never popped (`app.py:283-438`), no `on_screen_suspend` on Home
  (`home.py:629-646,808`). Fixed: decision 6 names the suspend hooks
  (`on_screen_suspend` on the five detail screens; `suspend_why` /
  `suspend_help` on Home; `on_unmount` backstop); Acceptance adds the
  copy→Why→return clearing test.
- **Accepted — grok r2 B2 (Help/copy rule disagreement).** Reproduced:
  `home.py:1006-1013` + `json_view.py:112-123` (JSON mode can show an
  explanation). Fixed: decision 7 makes JSON-mode Help conditional on
  `shows_document`, limits the Agents/Compare "copies nothing" rows to
  ordinary mode, and gives the picker its own row; Acceptance asserts every
  mode branch.
- **Accepted — round-2 suggestions (both critics):** `snapshot_path` named in
  Why/Diff recipes; truncation indent + listing-branch placement + notes
  placement; `unified_text` full output incl. headers; variant segment
  verbatim; Why zero-candidate sentences, agent strip and report-status line
  excluded; blank line between Why title and first candidate; full filter
  Help sentence; spec keeps the 0.2 deferral visible beside the dated lift;
  §8.2 filter prose; limitation sentence itself pinned in tests; README
  never-writes scope kept; `help.py` shared-line alternative DROPPED
  (per-screen `HelpContext.notes`); `env.get` semantics + BLOCKED-before-
  TOO_LARGE precedence; `## [Unreleased]` heading created above `[0.2.1]`;
  module-attribute constant read + scaled timer recipe; size boundary
  (≤ emits) + missing-env rule + conservative-stand-in note; goldens authored
  from recipes + screen-equivalence oracle + reuse of the six-screen CLI JSON
  oracle; `TERM_PROGRAM` pin DROPPED as vestigial (no such gate exists);
  checked-and-clear record (no `y` collision, `copy` action name safe, single
  OSC 52 write).

Round 3 (2026-11-15, targeted verification of the round-2 corrections):
both critics re-verified EVERY round-2 correction against the source and
confirmed them resolved (reports `reports/{grok-r3,mcode-r3}.md`). Two
narrow findings remained, both reproduced and accepted:

- **Accepted — mcode r3 B1 (binary marker literal).** Reproduced:
  `diff.py:763-772` — `marker = f" {BINARY_MARKER}"`, no brackets;
  `presentation/text.py:48`. The draft's `[ binary]` notation read as a
  literal would add brackets and make the recipe-authored golden and the
  screen-equivalence oracle mutually unsatisfiable. Fixed: both occurrences
  now say `  {path} {change}` plus the marker ` binary` (one leading space,
  no brackets, binary files only).
- **Accepted — grok r3 B1 (Why/Diff recipe vs oracle = three strings).**
  Reproduced: `theme.py:184-195` (fact_block adds no trailing blank line),
  `why.py:1096-1108` (Collapsible title is a separate widget from the body
  Static), `why.py:1070-1088` (zero-candidate and no-match Statics live in
  `#why-candidates`), `diff.py:177-179,254` (CSS margin join outside the
  Static text). Fixed: decision 2 now defines ONE string per screen — Why:
  `#why-title` plain text, blank line only when candidates exist, per
  candidate the Collapsible title line + body Static, blank line between
  candidates, zero-candidate report = title alone; Diff: style-stripped
  `#diff-content` Statics in mount order joined by one blank line,
  not-found alone. Acceptance's golden and oracle assert that same string.
- **Accepted — round-3 suggestions (both critics):** Why title fields listed
  in emission order (Installation, Name, Working directory); scope bullet
  names both suspend and unmount hooks; wrapper reads `os.environ` at call
  time; multi-byte boundary test (`é`) so character-count implementations
  fail; suspend tests named by route (Home→Why→return; Why→F1 Help;
  Why→Diff via `suspend_detail`/`ScreenSuspend`); Home clearing code in
  `suspend_why()` only (`suspend_help` delegates, `home.py:812`); mcode's
  checked-and-clear re-verification recorded (no `y` collision incl.
  Textual's unbound `action_copy_text`, `copy` action name safe, single OSC
  52 write, headless `_display` skips the driver so write-count assertions
  are satisfiable).

No in-scope blocker remains unresolved. Round 4 is a micro-targeted
fresh-session verification of the two round-3 corrections only (council §6
follow-up). Convergence record: round 1 = 12 blockers, round 2 = 5 (3+2,
overlapping), round 3 = 2 (one character-level, one oracle precision); every
round confirmed all prior items resolved, and no substance has been
disputed between the critics or with the coordinator. The two-round
escalation limit bars a third BROAD wave; these are targeted follow-ups on
reproduced, critic-prescribed corrections, not a re-review of settled scope.

Round 4 (2026-11-15, micro-verification of the round-3 corrections):
**both critics PASS, zero blockers** (reports
`reports/{grok-r4,mcode-r4}.md`). Both re-read every cited source line and
confirmed the binary literal, the one-string-per-screen recipes and oracles,
and all adopted suggestions; neither found a new gap or contradiction.
Their non-blocking suggestions were adopted as coordinator clarifications
(council §6 — precision on already-agreed mechanics, no behavior or scope
change), each reproduced against the source first:

- **Adopted — grok r4 S1 (oracle reads the label, not the widget).**
  Reproduced: `textual/widgets/_collapsible.py:85-90,179-180` — the rendered
  `CollapsibleTitle` prepends `▶`/`▼` + space. Acceptance now names
  `Collapsible.title` (the label) explicitly.
- **Adopted — mcode r4 S1 (clearing at the TOP of the hook).** Reproduced:
  `app.py:265,320` pre-suspend the origin; `why.py:377-378`,
  `diff.py:335-336`, `doctor.py:417-418`, `agents.py:335-336`,
  `compare.py:435-436` early-return when already suspended. Decision 6 now
  requires the clearing before delegation, or the Why→F1 and Why→Diff
  acceptance routes would fail.
- **Adopted — mcode r4 S2 (test-patching scope).** Decision 3 now scopes
  "own mapping, no os monkeypatch" to the pure function's unit tests;
  screen-level tests monkeypatch `os.environ` because the wrapper reads the
  live environment at call time.
- **Adopted — mcode r4 S3 (snapshot condition).** Why recipe states Name,
  Working directory and Agent appear only when a snapshot is present
  (`why.py:931-936`).
- **Adopted — mcode r4 S4 (raw per-file path).** Diff recipe states the
  per-file `{path}` is the raw `file.path`, not snapshot-mapped
  (`diff.py:749,763-772`).
- **Recorded — mcode r4 S5 / grok r4 CONCEDED (checked-and-clear):** no `y`
  collision anywhere incl. Textual's unbound `action_copy_text`; `copy`
  action name safe against the JsonView guard; AST guard bans neither
  `copy_to_clipboard` nor `os.environ` reads; single OSC 52 write; headless
  `_display` skips the driver so write-count assertions are satisfiable;
  Home's `#footer-help` is `height: auto` so the 13th key cannot clip; the
  five KeyBar screens have no pinned list to update.

**Council agreement reached: grok-4.7 (high) PASS and MiniMax-M3.1-Flash
(xhigh) PASS, zero unresolved blockers, all owner decisions recorded.**

## Execution receipt

Append-only.

Round 1 (2026-11-15):

- Coordinator: Qoder, this session; family unverified. Fingerprints before
  dispatch: `git status --porcelain` and SHA-256 of all 2101 tracked files
  (`/tmp/skill-lens-clipboard-council/before-{status,fingerprints}.txt`),
  base commit `4e319b7c6c7e4e8fbaa6d6101db34e12c65f8ab5`.
- critic-grok (Herdr `t108`, parent `t7w`): launched
  `grok -m grok-4.7 --reasoning-effort high`, brief `brief-grok-r1.md`.
  Identity: requested grok-4.7/high; configured = launch argv and session
  banner "Grok 4.7 (high)"; upstream weight identity unverified.
  runtimeMode/interactionMode n/a (Herdr host). Verdict `changes_required`;
  5 blockers, 5 suggestions; report `reports/grok-r1.md`; elapsed ≈ 15 min.
  Grok's own permission mode displayed "always-approve" (its CLI default; no
  bypass flag added by the coordinator); restraint instruction-based per
  council §2, verified by fingerprints.
- critic-mcode (Herdr `t10b`, parent `t7w`): launched
  `/Users/corvette/.minimax-code/bin/mcode -m minimax/MiniMax-M3.1-Flash`
  (absolute path required; core does not inherit the coordinator PATH).
  Identity: requested MiniMax-M3.1-Flash/xhigh; configured/confirmed =
  session footer "M3.1-Flash · Effort xhigh" (coordinator readback); the
  critic could not observe effort internally and marked it unverified —
  configured-route evidence, not upstream attestation. Verdict
  `changes_required`; 7 blockers, 8 suggestions; report `reports/mcode-r1.md`;
  elapsed ≈ 8 min.
- Both shown side by side in the Herdr "Clipboard council" tab; focus
  returned to the coordinator. After-fingerprints identical to before:
  neither critic touched any repository file. Terminals killed and removed
  after acceptance of the reports.
- Owner decisions recorded 2026-11-15 via direct question (Authorization).
- Token usage: not exposed by the hosts; grok's screen showed a ≈139k
  transfer counter (unverified semantics). Marked unavailable.

Round 2 (2026-11-15):

- Fresh fingerprints captured (`r2-before-{status,fingerprints}.txt`);
  tracked files identical to round 1.
- critic-grok-r2 (Herdr `t10c`): same route/flags, brief `brief-grok-r2.md`
  carrying the round-1 ledger and owner decisions. Banner "Grok 4.7 (high)".
  Verdict `changes_required`; 2 blockers (both overlapping mcode's), 10
  suggestions; report `reports/grok-r2.md`; elapsed ≈ 12 min. Confirmed all
  round-1 items resolved in the operative sections.
- critic-mcode-r2 (Herdr `t10d`): same route, brief `brief-mcode-r2.md`.
  Footer "M3.1-Flash · Effort xhigh" (coordinator readback). Verdict
  `changes_required`; 3 blockers, 8 suggestions; report `reports/mcode-r2.md`;
  elapsed ≈ 7 min. Confirmed all round-1 items resolved in the operative
  sections.
- Both shown in the "Clipboard council r2" tab. All round-2 findings
  reproduced against the source and accepted (Review decisions above);
  plan revised. After-fingerprints identical to before (status and all 2101
  SHA-256): neither critic touched any repository file. Terminals killed and
  removed after acceptance of the reports.
- Round 3: pending — targeted fresh-session verification of the round-2
  corrections, both critics (both questions affected).

Round 3 (2026-11-15):

- Fresh fingerprints captured (`r3-before-{status,fingerprints}.txt`);
  tracked files identical to rounds 1–2.
- critic-grok-r3 (Herdr `t10f`): same route/flags, brief `brief-grok-r3.md`.
  Identity: launch argv receipt; the critic reports the banner string was
  not visible inside its session (marked unverified by it); upstream weight
  identity unverified. Verdict `changes_required`; 1 blocker (Why/Diff
  oracle precision), 2 suggestions; report `reports/grok-r3.md`; elapsed
  ≈ 13 min. Confirmed all round-2 corrections resolved against the source.
- critic-mcode-r3 (Herdr `t10g`): same route, brief `brief-mcode-r3.md`.
  Identity: the critic could not observe effort internally; the coordinator
  verified the run's `llm-call.json`
  (`~/.minimax/v2/sessions/2026/11/15/11-55-28-528-session_bXZzXzgz…/`):
  provider minimax, model MiniMax-M3.1-Flash, `thinkingLevel: xhigh`, API
  anthropic-messages — configured-route evidence, not upstream attestation
  (same channel as the U5 mission record). Verdict `changes_required`;
  1 blocker (binary marker literal), 5 suggestions + 1 re-verification
  note; report `reports/mcode-r3.md`; elapsed ≈ 9 min. Confirmed all
  round-2 corrections resolved against the source, push-site by push-site.
- Both shown in the "Clipboard council r3" tab. Both round-3 findings
  reproduced and accepted; plan revised (Review decisions above).
  After-fingerprints identical to before (status and all 2101 SHA-256):
  neither critic touched any repository file. Terminals killed and removed
  after acceptance of the reports.
- Round 4: complete — see below.

Round 4 (2026-11-15):

- Fresh fingerprints captured (`r4-before-{status,fingerprints}.txt`);
  tracked files identical to rounds 1–3.
- critic-grok-r4 (Herdr `t10h`): same route/flags, brief `brief-grok-r4.md`.
  Identity: launch argv receipt (pid 96954), session identity "Grok 4.7";
  banner not visible inside the session (marked unverified by the critic);
  upstream weight identity unverified. Verdict **pass**, zero blockers,
  1 non-blocking suggestion (adopted); report `reports/grok-r4.md`;
  elapsed ≈ 10 min.
- critic-mcode-r4 (Herdr `t10j`): same route, brief `brief-mcode-r4.md`.
  Identity: critic could not observe effort internally; coordinator
  verified the run's `llm-call.json`
  (`~/.minimax/v2/sessions/2026/11/15/12-08-21-177-session_bXZzX2I0ZTUw…`,
  session `mvs_b4e506f99ecb4b2689c4a47f03ffa014`): provider minimax, model
  MiniMax-M3.1-Flash, `thinkingLevel: xhigh`, API anthropic-messages —
  configured-route evidence, not upstream attestation. Verdict **pass**,
  zero blockers, 4 non-blocking
  suggestions + 1 re-verification note (all adopted/recorded); report
  `reports/mcode-r4.md`; elapsed ≈ 11 min. The critic's first message lost
  the word "binary" to shell substitution; it resent a corrected summary
  and the report file was intact.
- Both shown in the "Clipboard council r4" tab. After-fingerprints
  identical to before (status and all 2101 SHA-256): neither critic touched
  any repository file. Post-pass clarifications applied by the coordinator
  (Review decisions, round 4) are precision on already-agreed mechanics,
  within council §6 coordinator correction authority; no behavior, scope,
  permission or contract change.
- Planning complete: 8 dispatches over 4 rounds, all settled; council
  agreement recorded; two-commit freeze follows. Terminals killed and
  removed after acceptance of the reports.

Implementation mission (2026-11-16):

- Authorization: user (Hazem), 2026-11-16, direct instruction: start
  implementation of this frozen plan on `feat/tui-clipboard`. No push,
  release, or publication is authorized. The planning-mission
  authorization above is historical; this entry records the new,
  separate grant. Frozen contract unchanged: Reference
  `b838b458482ed3ada8c46e66d5c10c45c32fd89b` verified against HEAD
  `efb0c75b565ec477b06985c10d84d0d393401fe3` (delta is the Reference
  line only).
- Roster (user-named 2026-11-16; council §1): coordinator — Qoder, this
  session (model set to Qwen4-Max, effort xhigh, via /model readback;
  advertised family Qwen, upstream unverified). Implementer — omp CLI,
  `river/deepseek-ai/DeepSeek-V4.1-Flash-1017`, thinking `max` (user
  choice from the live catalog's low/high/max; the user's omp config
  already pins this model at :max), `--approval-mode yolo` explicitly
  authorized by the user for this implementer session only (recorded
  here; no standing waiver). Final critics — mcode CLI
  `minimax/MiniMax-M3.1-Flash`, effort `xhigh` (user naming; the only
  M3.1 in the config whitelist is M3.1-Flash; configured effort xhigh
  via defaultModelThinking, to be verified per round by footer and
  llm-call.json readback); opencode CLI
  `opencode/glm-5.3-flash-free#max`, Plan agent (user naming "glm 5.3
  flash free max"; #variant syntax per project evidence; model bound
  via OPENCODE_CONFIG_CONTENT, agent via shift+tab, both
  footer-verified). Family disclosure (council §1): advertised families
  DeepSeek, MiniMax, GLM (Zhipu), Qwen — distinct from each other;
  upstream weight identity unverified on the aggregator routes (river,
  opencode free tier). The user named this set for this mission, which
  records acceptance of the named set. Risk Normal: one critic
  required; the user named two, so both review with complementary
  questions (council §6).
- Route discovery evidence: `omp models find deepseek/river` (unique
  match DeepSeek-V4.1-Flash-1017); mcode `~/.minimax/config.yaml`
  whitelist (MiniMax-M3, MiniMax-M3.1-Flash) and
  defaultModelThinking.effort xhigh; `opencode models` catalog
  (opencode/glm-5.3-flash-free) plus the user's own config using the
  #max variant. opencode TUI rejects `--model` (probe exit 1,
  "Unrecognized flag"); OPENCODE_CONFIG_CONTENT is honored at runtime
  (probe footer "Plan · GLM-5.3-Flash Free Default / OpenCode · max"
  after one shift+tab); both probes killed and removed. hc launches
  use absolute CLI paths (core does not inherit the coordinator PATH).
- Baseline (Step 1): tracked tree clean at HEAD efb0c75; pre-existing
  untracked scratch preserved. Four gates on the baseline tree, all
  exit 0: pytest --cov=skill_lens 1410 passed, 1 skipped, TOTAL
  coverage 90% (threshold met); mypy clean; ruff check clean; ruff
  format --check clean. Log:
  `/tmp/skill-lens-clipboard-impl/baseline-gates.log`; git state:
  `/tmp/skill-lens-clipboard-impl/baseline-{status,head}.txt`.
  Baseline terminal t10m removed after collecting results.
- Implementer dispatch (2026-11-16): `clipboard-impl` (Herdr `t10r`,
  parent `t7w`), launched `/Users/corvette/.local/bin/omp --model
  river/deepseek-ai/DeepSeek-V4.1-Flash-1017 --thinking max
  --approval-mode yolo --no-skills --no-extensions --no-rules` with
  brief `/tmp/skill-lens-clipboard-impl/brief-impl-r1.md` as the first
  message. Identity: requested DeepSeek-V4.1-Flash-1017/max;
  configured = launch argv; confirmed = session footer "DeepSeek V4.1
  Flash 1017 (River)" (coordinator readback); thinking max configured
  via argv, not banner-confirmed; upstream weight identity unverified
  (river aggregator). runtimeMode/interactionMode n/a (Herdr host).
  yolo is limited to this session per the user's explicit authorization
  above. Shown in the "Clipboard impl" tab; focus returned to the
  coordinator. Baseline gates green before dispatch.
- Amendment 1 (2026-11-16): implementer `clipboard-impl` reported BLOCKED
  with reproduction: the packaging manifest pins 13 TUI modules; the
  plan's new `clipboard.py` makes 14; neither packaging file was in
  allowed scope; it edited neither and held. Coordinator reproduced:
  `PYTHONDONTWRITEBYTECODE=1 COVERAGE_FILE=/tmp/... .venv/bin/pytest -p
  no:cacheprovider tests/test_tui_packaging.py -k
  manifest_covers_every_shipped` → FAILED at
  `tests/test_tui_packaging.py:386` (on disk 14 vs EXPECTED 13). The U9
  design comment prescribes updating both tuples together on legitimate
  growth. User authorized the minimal amendment explicitly (2026-11-16).
  Operative amendment applied to Scope and boundaries; new two-commit
  freeze follows; the final critics review the manifest change under the
  compatibility axis. The implementer receives the amendment brief with
  the new frozen reference before editing the two files.