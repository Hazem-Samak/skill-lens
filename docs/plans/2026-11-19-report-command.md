# Plan: Exportable diagnostic report (`skill-lens report`, GitHub issue #6)

Status: Agreed (revision 3 + round-3 pass dispositions and incorporated suggestions)
Authorization: Per Hazem's instruction of 2026-11-19: draft the plan for issue #6,
  run independent review with the user-named critics, then commit and freeze the
  agreed plan, create the GitHub branch, link it to issue #6, and push the plan
  there. **Implementation is NOT authorized by this mission.** Push authorization
  is limited to the plan commits on the issue branch.
Roster: (user-named, this mission only; requested vs configured vs confirmed kept separate)
  - coordinator: nous/qwen4-max:free (Hermes CLI session; confirmed by session
    header; coordinator terminal t7w in round 1, t128 from round 2 onward —
    t7w ended mid-mission and the session resumed at t128, verified by screen
    readback).
  - plan critic 1 (rounds 1-3): requested "Minimax M3.1 xhigh" via mcode CLI
    0.7.6. Live catalog offers exactly `minimax/MiniMax-M3.1-Flash` and
    `minimax/MiniMax-M3`; no plain "M3.1". **Owner confirmed 2026-11-19**
    ("yes m3.1F"): minimax/MiniMax-M3.1-Flash at xhigh. Rounds 1-2 confirmed
    by launch banner readback ("M3.1-Flash · Effort xhigh") and critic
    self-reports. Round 3: fresh session, banner re-verified before dispatch.
  - plan critic 2 (rounds 1-2): requested "grok 4.7 high" via grok CLI 1.0.89
    (`grok-4.7`, `--reasoning-effort high`, `--no-subagents`); confirmed by
    banner readback both rounds. After delivering its complete round-2
    report, grok hit "Request failed (402): Grok Build usage balance
    exhausted" (weekly limit dialog). UNAVAILABLE for further rounds; no
    substitute was chosen silently (council §1.3).
  - plan critic 2 replacement (round 3): **owner named 2026-11-19**: "the
    other reviewer will be gemini 3.8 flash high through agy cli" →
    agy CLI 1.5.12, model label `gemini-3.8-flash-high` ("Gemini 3.8 Flash
    (High)"), verified against the live `agy models` catalog; `--effort high`
    passed consistently with the label. Launch banner confirmation recorded
    at dispatch. Inherits the behavior & test-gaps axis; grok's round-1/2
    reports are its findings ledger.
  - implementer: not selected — implementation is not authorized this mission.
  - final critics: not selected — named at the implementation mission.
  Family disclosure (council §1): coordinator = Qwen family (Alibaba, via
  Nous); mcode critic = MiniMax family; grok (rounds 1-2) = xAI Grok family;
  agy critic (round 3) = Gemini family (Google). No critic shares the
  coordinator's family; all critics are distinct families. The user named
  each set explicitly, which records acceptance of the named sets.
  Permission-mode disclosure: mcode and grok ran under the user's
  PRE-EXISTING permissive defaults ("Full access" / "always-approve"); the
  coordinator added no bypass flags. agy runs under its own default
  permission policy — no `--dangerously-skip-permissions` added. Reviewer
  restraint is instruction-based (verbatim council §2 guard) plus
  before/after SHA-256 fingerprints (council §2.3). Rounds 1 AND 2
  fingerprint results: CLEAN (no repository change by any critic).
Reference: f182f22861942c2a2940960ae2caed13b4c4583d
Risk and review: HIGH — new public JSON data format (`models/report.py`)
  that scripted users will parse (project-profile §7). Two user-named
  critics per round, complementary questions:
  - critic 1 (mcode): project rules & compatibility.
  - critic 2 (grok r1-r2, agy r3): behavior & test gaps.
  Council §5 escalation record: rounds 1 and 2 both returned
  changes_required (round 2 confirmed ALL round-1 findings resolved but
  found 5 new precision defects, all coordinator-reproduced). Per §5 the
  coordinator stopped and escalated; the owner chose option 2 on
  2026-11-19: name a replacement second reviewer (agy/gemini-3.8-flash-high)
  for ONE targeted confirmation round with both critics fresh. Round 3 is
  that targeted round — focused on the changed areas and unresolved
  findings, not a third broad wave.
Expected child tasks: round 1 = 2 critics (done); round 2 = 2 critics (done);
  round 3 = 2 fresh targeted critics (mcode + agy) — DONE, both PASS. Later implementation
  mission (separate authorization): implementer + 2 final critics.

## Outcome

`skill-lens report` exports one shareable diagnostic document combining the
detected agents, a known-agents precedence catalog, the canonical-library
summary, the per-agent skill inventory, doctor findings with severity, and an
optional pairwise compare section — as Markdown (default) or one combined JSON
model (`--json`), to stdout or to an explicitly requested `--output <file>`.
Every report carries a pinned-spelling UTC timestamp, the Skill Lens version
and an injectable platform string for reproducibility. In the TUI, the `R` key
copies the captured session's Markdown report through the shipped OSC 52
clipboard channel (owner-approved), on all six browsing screens AND while Help
is open (explicit modal binding). The tool stays 100% read-only except for the
one explicitly requested output file; no engine, model, renderer or TUI code
writes anything.

## Current state (verified 2026-11-19 on branch feat/issue-6-report, base b22dbe7)

- No `report` command exists: cli.py defines tui, scan, why, agents, diff,
  doctor, compare only (cli.py:243-501). Issues #5/#7 untouched.
- Command conventions: `_apply_sandbox`, `_effective_home`, `_effective_cwd`,
  `_assert_inside_sandbox`, `_emit_json`, `_finish` (cli.py:173-241). Every
  command since Phase 2 takes `--sandbox`/`--cwd`. `compare` rejects any
  `--agent` count other than two (cli.py:479-481, sentence "pass --agent
  exactly twice (two agents to compare); got {n}"); `report` must NOT copy
  that rule — zero agents is legal for report, so it needs its own sentence.
  Existing exit-2 sentences to reuse verbatim: unknown agent
  "unknown agent '{id}'. Known agents: {known}" (compare.py:159); duplicate
  "cannot compare agent '{id}' with itself" (compare.py:38).
- Engines accept one shared discovery pass: build_scan_report(home, cwd,
  index=None, registry=None) (scanner.py:163), build_doctor_report(home, cwd,
  index=None, registry=None) (doctor.py:55), build_compare_report(a, b, home,
  cwd, index=None, registry=None) (compare.py:42). Each calls `discover` ONLY
  when index is omitted. run_doctor (doctor.py:615) calls live_discovery once
  and PASSES the index down (:622-624); run_compare (compare.py:253) validates
  agent ids BEFORE any walk (:270-271, finding C-02). live_discovery
  (system.py:84) is the guarded production adapter.
- SPY MECHANICS (round-2 grok B1, reproduced): `discover` is copied into
  consumer namespaces at import time — scanner.py:14-21, doctor.py:21,
  compare.py:16, system.py:23 — and live_discovery calls the SYSTEM-local
  discover (system.py:101). Patching skill_lens.core.discovery.discover
  therefore sees none of those calls. The existing suite patches consumer
  bindings for exactly this reason (test_doctor.py:351-354 patches
  "skill_lens.core.doctor.live_discovery"). Any one-pass proof must wrap the
  bindings the code actually calls.
- Serialization facts: ScanReport/ScanEntry/ScanSummary expose to_dict ONLY
  (no from_dict in core/scanner.py); ScanEntry.to_dict serializes only
  condition.code ("health_status"), so an object-level scan round-trip would
  fabricate unserialized HealthCondition fields. DoctorReport
  (models/doctor.py:51) and CompareReport (models/compare.py:57) DO
  round-trip. ScanSummary.total_skills is a derived @property that to_dict()
  DOES serialize (scanner.py:83-97); C-05's "derived never serialized" rule
  covers doctor/compare dead counters, not the existing scan payload.
  Canonical JSON = dumps (models/__init__.py:73, sort_keys=True, indent=2).
- Agents JSON view: agents_payload → AgentSummary TypedDict
  (presentation/agents.py:11-32), one row per KNOWN registry definition
  (id, name, collision_policy, policy_evidence, roots=count). Its signature
  takes Sequence[AgentDefinition]; iterating a registry DICT yields id
  strings, so callers must pass registry.values() (round-2 grok suggestion).
  scan.summary.detected_agents (scanner.py:201) is the sorted set with actual
  hits; empty when the home has no skills. TUI wording precedent:
  tui/agents.py:350-352, home.py:1552-1555. No core→presentation import
  exists today.
- IMPORT-CYCLE TRAP (round-2 mcode B7, reproduced on a scratch package copy):
  moving agents_payload verbatim into models/agents.py forces a runtime
  `from skill_lens.registry.loader import AgentDefinition`; registry.loader
  itself imports skill_lens.models.enums (loader.py:15), so a registry-first
  import initializes models from inside loader, and models.agents then asks
  the partially-initialized loader for AgentDefinition → hard ImportError.
  Shipped entry points import models first, so the trap is latent but on the
  public import surface. The TYPE_CHECKING-only variant imports cleanly in
  every order and agents_payload output is identical (10 rows, same shape).
- TUI session: SessionSnapshot carries scan, doctor, registry (a TUPLE of
  AgentDefinition), display_paths, FrozenDiscoveryIndex
  (snapshot_models.py:56-73). SessionController: current starts None (:52);
  status order refused → retry → sticky error → loading → ready (:80-92);
  accept_capture does NOT clear sticky failed (:136-140); later refusal or
  retry KEEPS the previous snapshot (:184-206); close() sets closed but does
  NOT clear current (:349-368) and status has no closed token. Export must
  gate on `current is not None`, never on status == "ready"; closed follows
  current.
- TUI keys: r = Refresh (app.py:139), y = Copy via OSC 52, J = JSON, q = quit.
  R and e unbound on every screen. Home's filter Input consumes non-priority
  printable keys (home.py:755-756); filter Help rows at home.py:751-776;
  "?" precedent help.py:48-52. HelpScreen is a ModalScreen[None]
  (help.py:201) that RE-BINDS q→app.quit and r→app.refresh itself
  (:210-211); the frozen U8 plan records why: "Modal bindings stop ordinary
  non-priority app bindings at the modal; Help must explicitly expose
  Refresh and Quit" (2026-11-04-tui-u8-polish-help-docs.md:57-60). A
  non-priority app-level R therefore CANNOT fire while Help is open without
  an explicit HelpScreen binding (round-2 grok B2, reproduced).
  Help's six covered origins: Home, Why, Diff, Agents, Compare, Doctor
  (help.py:55); shared rows from _COMMON_ROWS (help.py:37). The Help
  READ-ONLY paragraph (help.py:135-136) says Skill Lens never creates files
  — no test pins it today. The Compare screen's selected pair
  (_selected_a/_selected_b, compare.py:813-818) lives OUTSIDE the snapshot.
  Every screen's y handler copies the view on screen (e.g. home.py:1846-1849
  copies the JSON document in JSON view).
- OSC 52 channel: tui/clipboard.py — MAX_COPY_BYTES = 75_000 UTF-8 bytes;
  copy_decision precedence BLOCKED (TMUX / TERM=screen*) before TOO_LARGE
  (:53-59); CLIPBOARD_LIMITATION sentence (:29-33). Screen notice strings
  (home.py:1118-1124): BLOCKED "Clipboard not supported in this terminal";
  TOO_LARGE "Too large to copy via terminal clipboard"; copy_to_clipboard
  runs only for SENT.
- MARKDOWN EMISSION HAZARD (round-2 mcode B8, reproduced with the venv's
  rich): the CLI's only printer is Rich Console (cli.py:49). Default
  console.print wraps at console width (80 when piped) — a 105-character
  table row was SPLIT across lines — and markup=True consumes the backslash
  before "[" ('skill \[*bold*\] end' became 'skill [*bold*\] end'). With
  soft_wrap=True, markup=False, highlight=False (the _emit_json idiom,
  cli.py:124-130; plain-text precedent cli.py:358-362) the bytes are
  preserved exactly. tests/test_cli.py:17-32 (_PlainRunner) STRIPS ANSI
  before assertions, so runner equality alone cannot prove byte fidelity.
- TUI read-only contract: FULL_SCREEN_TUI.md §10; AST guard
  tests/test_tui_read_only.py walks ONLY skill_lens/tui/ (:345-349);
  presentation/ importable (§10.3); skill_lens.render/rich banned; the
  "render"-component import ban does not match "report". NO new tui/ module:
  EXPECTED_TUI_MODULES is hand-maintained (test_tui_packaging.py:78-93,
  :378-390).
- Packaging count gates: test_tui_packaging.py:618-622 asserts
  len(SNAPSHOT_DIR.glob("*.txt")) == 17 (NON-recursive) and goldens
  top-level + phase4/ == 16; test_fixtures.py:47 globs golden top level only.
  Snapshot harness _check (test_render_snapshots.py:68-82) resolves
  SNAPSHOT_DIR / f"{name}.txt" and mkdirs path.parent on update —
  subdirectory names like "report/<case>" work and are invisible to the
  count globs. Installed-lane tuples are ORDER-SENSITIVE (equality drift
  guard test_tui_packaging.py:393-398): EXPECTED_INSTALLED_TEST_SUITES
  (:95-111) == INSTALLED_TUI_TEST_SUITES (scripts/smoke_wheel.py:64); the
  lane is bounded at 300 s (smoke_wheel.py:411-414) and currently runs ~360
  tests in roughly two minutes.
- Golden harness: test_phase4_gate.py — fail-on-missing (C-03);
  --update-goldens only after reading the diff; _rel/_normalize (:33-73)
  rewrites top-level home/cwd, compare entry paths, doctor finding paths —
  NOT sufficient for nested report payloads. _rel handles BOTH the absolute
  prefix and the already-collapsed "~/..." display form, and the home itself
  becomes ".". Report goldens need a RECURSIVE application of that rule to
  every string, and the absence check must reject str(home) AND
  str(home.resolve()) when they differ (macOS /tmp vs /private/tmp).
  Snapshot machine-path ban: test_render_snapshots.py:81 (asserts str(home)
  not in rendered — a path OUTSIDE the home would pass the ban while still
  being machine-specific, so fixtures must keep cwd and every skill inside
  the mock HOME; the acceptance farm already does, farm.py:40-44).
  update_goldens/update_snapshots fixtures: conftest.py:152-158.
- CI matrix: ubuntu-latest AND macos-latest (.github/workflows/ci.yml:17-18);
  platform.platform() embeds the Linux kernel release → goldens need an
  injected fixed platform token.
- Doctor findings: seven fields (models/doctor.py:18-24): code, severity,
  message, rule_id, evidence, path, detail. Order: error → warning → info,
  then code, then path (doctor.py:86-88). unreadable_root finding:
  rule_id="doctor_tcc", severity WARNING, evidence EMPIRICAL,
  detail=root.detail, path=root.path (RAW absolute), while the MESSAGE
  already embeds paths.display(root.path) (collapsed "~/...")
  (doctor.py:343-355). registry_uncited_agent finding has path=None
  (doctor.py:609) — display() requires a path, so None must render an empty
  cell. build_acceptance_farm creates NO unreadable root; a separate
  synthetic fixture is required. scan.unreadable rows carry
  agent/root/path/detail (scanner.py:215-223).
- Compare notes (compare.py:124-140) are unverifiable-content warnings,
  serialized (models/compare.py:85-95); counts_by_relation derived, NOT
  serialized. The acceptance farm may produce no notes — a renderer test
  needs a constructed CompareReport with non-empty notes.
- Path display: paths.display() (paths.py:118-135) collapses the effective
  home to "~", trying as-written AND resolved forms against home variants;
  doctor prints entrypoints through it (doctor.py:91-93). TUI uses
  SessionSnapshot.display_paths because live display() resolves against the
  real HOME, not the sandbox.
- Exit codes (exitcodes.py:12-20): 0 ran/no threshold; 1 findings reached
  --fail-on; 2 "The command could not run: bad usage, unknown agent,
  unreadable input"; 3 reserved internal fault, never deliberate.
- Rule documents stating the read-only promise (owner-approved amendment
  targets): SKILL_LENS_SPECIFICATION.md:127 ("NO Write Operations: Zero file
  installations, deletions, or modifications."), :419 (§8.1 "never modifies,
  creates, moves, or deletes user files."), §6 (:133) six commands;
  inline dated amendment precedent at :126 ("Amended for 0.2: ...") and
  :373-378. docs/process/profiles/project-profile.md:71-75 ("never writes,
  modifies, moves or deletes anything on the user's machine. No exceptions,
  no 'just this one' flags."). AGENTS.md §1 Golden Rule 1 speaks of "user
  skills" — a report file is not a skill, so it stands unchanged (mcode S-C).
  tui/help.py:135-136 READ-ONLY paragraph (no test pins it today).
- Release state: 0.2.1 published; __version__ = "0.2.1" (__init__.py:3) —
  embedding it in goldens means a later bump requires reviewed
  golden/snapshot updates. CHANGELOG [Unreleased] exists; README Commands
  table :75-84; README absolute-links-only (phase5 gate). Pinned README
  sentences NOT to reword: "`y` copies the focused content through the
  terminal clipboard (OSC 52)" + CLIPBOARD_LIMITATION
  (test_tui_clipboard.py:475-480). DEVELOPMENT.md:363 says "the 17 CLI
  snapshots and 16 JSON goldens" — still true as TOP-LEVEL counts once
  report fixtures live in subdirectories; gets a one-clause qualification.
- Baseline four gates on the unchanged tree: ALL GREEN (recorded below).

## Owner decisions

1. RESOLVED 2026-11-19 — mcode reviewer identity: "yes m3.1F" →
   minimax/MiniMax-M3.1-Flash at xhigh approved.
2. RESOLVED 2026-11-19 — TUI export mechanism: "clipboard is fine" → R copies
   the session's Markdown report via the shipped OSC 52 decision path plus a
   Help entry. No §10 amendment; CLI --output is the only file-writing surface.
3. RESOLVED 2026-11-19 ("Yes") — wording amendment package approved:
   SKILL_LENS_SPECIFICATION.md (§5 bullet + §8.1 item + §6 entry 7),
   docs/process/profiles/project-profile.md §3, and the Help READ-ONLY
   paragraph (tui/help.py:135-136) all receive the same dated note: the only
   file Skill Lens ever writes is the explicitly requested report output
   (skill-lens report --output <file>); everything else stays strictly
   read-only. Exact texts in step 7. AGENTS.md Golden Rule 1 unchanged
   (user-skills wording; rationale recorded).
4. RESOLVED 2026-11-19 — review completion path after the council §5
   escalation: owner chose option 2 and named the replacement second
   reviewer: "the other reviewer will be gemini 3.8 flash high through agy
   cli" → agy/gemini-3.8-flash-high for one targeted confirmation round
   (round 3) alongside a fresh mcode session. grok's round-1/2 reports remain
   the findings ledger for the behavior axis; grok itself is quota-exhausted
   (402) and was not substituted silently.

## Scope and boundaries

Allowed files (for the LATER implementation mission; this mission touches only
this plan file):
- skill_lens/models/report.py (new), skill_lens/models/agents.py (new),
  skill_lens/models/__init__.py (exports)
- skill_lens/core/report.py (new, pure composition + live adapter entry)
- skill_lens/presentation/report.py (new, pure Markdown renderer + escaper),
  skill_lens/presentation/agents.py (re-export shim only),
  skill_lens/presentation/__init__.py (exports)
- skill_lens/cli.py (new `report` command only)
- skill_lens/tui/app.py (R binding + export helper + notices),
  skill_lens/tui/home.py (filter Help rows), skill_lens/tui/help.py
  (HelpScreen R binding, _COMMON_ROWS entry, READ-ONLY paragraph sentence).
  NO other tui/ file; NO new tui/ module.
- tests/test_report.py (new), tests/test_cli.py (report cases),
  tests/test_tui_home.py, tests/test_tui_help.py, tests/test_tui_read_only.py
  (export coverage + mutation controls),
  tests/test_tui_packaging.py (installed-lane selection + its stale count
  docstrings — 17/16 assertions unchanged), scripts/smoke_wheel.py (lane
  selection ONLY), tests/test_phase5_gate.py (add "report" to the spec↔CLI
  wiring guard's expected set + docstring — round-3 S-R; the subset
  assertion stays green either way, but then guards the new spec promise)
- tests/fixtures/golden/report/ (new goldens),
  tests/fixtures/snapshots/report/ (new SUBDIRECTORY — 17-count gate stays
  green; existing snapshots must not move)
- README.md (additive Commands row + report section + the :86 six→seven
  accuracy fix; the historical 0.2.0 sentence and pinned y sentences NOT
  reworded; absolute links only), CHANGELOG.md ([Unreleased]/Added),
  FULL_SCREEN_TUI.md (additive keymap/Help documentation of R + the
  one-clause top-level count qualification at :367-368; no §10 or other
  contract rewrite)
- SKILL_LENS_SPECIFICATION.md (owner-approved dated amendment: §5 bullet,
  §8.1 item, §6 entry 7 — nothing else)
- docs/process/profiles/project-profile.md (owner-approved dated note on §3
  + §1 tree accuracy lines :19/:22-23 — nothing else)
- DEVELOPMENT.md (one-clause "top-level" qualification at :363 — nothing else)

Excluded / deferred (with reasons):
- HTML format — issue says "optionally HTML"; acceptance requires md + json
  only. --format accepts md only; any other value (including html) → exit 2,
  pinned by a test.
- --fail-on on report — not requested; report is informational (exit 0 on
  success even with findings).
- Any change to existing commands, JSON shapes (agents/scan/doctor/compare
  payloads byte-identical), existing goldens/snapshots, registry TOMLs,
  exit-code contract, or engine behavior. AgentSummary NOT widened (roots
  stays int; no coexist_policy or per-root rank). AGENTS.md unchanged.
- Version bump, release, publishing — separate explicit mission.
- Issues #5/#7 — separate missions. Windows, databases, AI calls, telemetry —
  standing Golden Rule #5.

Constraints:
- Golden Rules 1-6: strictly read-only target execution; the ONLY write is
  the explicit --output file, performed in cli.py, never in an engine/model/
  renderer/TUI module. Tests never touch real $HOME; no module-level path
  expansion; JSON/dataclasses first; provenance preserved (report reuses
  engine outputs verbatim — it invents no agent behavior).
- models/ must NOT import skill_lens.registry at runtime (round-2 B7 rule;
  TYPE_CHECKING-only references allowed).
- Boundary sentence: core/report.py stamps metadata and calls the EXISTING
  builders. It computes no findings, relations, health, or collision policy
  — a composition layer, not a fourth engine ("no new engine logic").
- One discovery pass per report run, PROVEN BY CALL-COUNT SPIES on the
  bindings the code actually calls (round-2 G1), not by output parity alone.
- Engines/renderers pure: no Rich, no Typer in core/report.py,
  models/report.py, models/agents.py, presentation/report.py.
- The 256 MiB budget applies to TUI capture, not line commands (cli.py:260).
  TUI export reuses the published snapshot (no new capture) and the
  75,000-byte OSC 52 cap. Realistic consequence: full reports of real homes
  routinely exceed the cap → TOO_LARGE is normal; the notice points to
  `skill-lens report --output <file>`.

## Implementation steps (for the later authorized mission)

1. **models/agents.py (new) + models/report.py (new)** —
   a. Move AgentSummary (TypedDict) and agents_payload from
      presentation/agents.py into models/agents.py. CRITICAL (B7):
      models/agents.py references AgentDefinition under `if TYPE_CHECKING:`
      ONLY (the file keeps `from __future__ import annotations`;
      agents_payload only reads attributes, so runtime behavior is
      identical). RULE: models/ must not import skill_lens.registry at
      runtime. presentation/agents.py becomes a re-export shim so
      `skill-lens agents --json`, cli.py's import path, test_presentation.py
      and the agents render snapshot stay byte-identical. Invariant: no
      core→presentation import; models/ has no runtime dependency on
      registry/. Verified by probe: the verbatim runtime-import variant
      breaks registry-first imports with ImportError; the TYPE_CHECKING
      variant imports cleanly in every order with identical payload.
   b. Frozen ReportMeta: generated_at (str), skill_lens_version (str),
      platform (str). NO home/cwd fields — they live in the nested payloads
      (single source of truth).
   c. Frozen ReportModel: meta: ReportMeta; agents: tuple[AgentSummary, ...]
      (runtime import from models.agents — same layer, no cycle);
      scan: dict[str, Any] — the canonical ScanReport.to_dict() payload
      stored VERBATIM (ScanReport has no from_dict and its condition field
      is not fully serialized, so dict nesting is the only honest
      round-trip route); doctor: DoctorReport; compare: CompareReport | None.
   d. to_dict(): {"meta": ..., "agents": [...], "scan": <verbatim payload>,
      "doctor": doctor.to_dict(), "compare": compare.to_dict() or None}.
      The "compare" key is ALWAYS present (null without a pair). Nested
      payloads byte-identical to agents/scan/doctor/compare --json,
      INCLUDING scan.summary.total_skills. "Derived values never
      serialized" applies only to NEW report-level fields; ReportModel
      introduces none.
   e. from_dict() round-trips exactly: scan dict passes through; agents
      rebuilt as tuple(payload["agents"]) (to_dict emits a list — without
      the tuple rebuild the equality test fails); doctor/compare reconstruct
      via their from_dict. Hashing ReportModel is not part of the contract
      (dict fields unhashable — existing ScanReport.unreadable precedent).
   f. Export new names from models/__init__.py.
2. **core/report.py (new, pure)** —
   a. assemble_report(scan_payload: dict, doctor: DoctorReport,
      agents: tuple[AgentSummary, ...], compare: CompareReport | None,
      meta: ReportMeta) -> ReportModel — the ONE shared constructor used by
      both the CLI path and the TUI export so the documents cannot drift.
   b. build_report(home, cwd, *, compare_agents: tuple[str, str] | None =
      None, index=None, registry=None, generated_at: datetime | None = None,
      platform_text: str | None = None) -> ReportModel: when compare is
      requested, validate_compare_agents runs BEFORE any walk; discovery =
      supplied index or ONE discover call; the SAME index object goes into
      build_scan_report, build_doctor_report and (when requested)
      build_compare_report — index= is passed to ALL THREE (dropping it
      from any one is a mutation the spy tests must catch). Agent rows =
      tuple(agents_payload(registry.values())) — agents_payload takes a
      SEQUENCE of AgentDefinition (never the dict itself; iterating it yields
      id strings) and RETURNS A LIST, so the tuple() conversion is required
      at BOTH call sites for the mypy-strict tuple field (round-3 S-P).
      platform_text named so it does not shadow the stdlib platform module;
      defaults to platform.platform() ONLY when omitted (injectable for
      CI-matrix-stable goldens).
   c. ONE shared timestamp function, used by build_report AND the TUI:
      utc_timestamp(value: datetime) -> str — REJECTS naive datetimes
      (ValueError), converts aware values with astimezone(timezone.utc),
      returns isoformat(timespec="seconds") → e.g.
      "2026-11-19T14:20:00+00:00". Default generated_at =
      datetime.now(timezone.utc). Tests: an injected +02:00 aware datetime
      produces the +00:00 spelling; a naive datetime raises. Same spelling
      in CLI and TUI; stated in README.
   d. Live adapter entry run_report(cwd=None, *, compare_agents=None,
      registry=None, generated_at=None, platform_text=None): VALIDATES the
      pair BEFORE calling live_discovery (same order as run_compare,
      compare.py:270-271), then calls live_discovery ONCE and passes that
      index AND registry into build_report with the discovered home/cwd
      (mirrors run_doctor, doctor.py:622-624; C-02). Doctor's lockfile read
      on the supplied-index path is allowed; spies target discovery
      functions, not all filesystem reads.
   e. ONE-PASS SPY CONTRACT (G1): tests wrap with call counters (delegating
      to the real functions) exactly these bindings:
      skill_lens.core.report.live_discovery (the name run_report calls),
      skill_lens.core.scanner.discover, skill_lens.core.doctor.discover,
      skill_lens.core.compare.discover. The crawl INSIDE the real
      live_discovery (system-local discover) counts as the one live call and
      does not spend the builder-discover budget. Expectations:
      - valid run_report WITH a two-agent compare: live_discovery×1,
        each builder discover×0;
      - build_report with supplied index AND compare: live×0, builders×0;
      - run_report with unknown id / duplicate pair: live×0, builders×0,
        raises (CLI translates to exit 2) — engine-level proof, not hidden
        by the CLI short-circuit;
      - output parity remains a SECOND assertion, never the one-pass proof.
      Mutations that MUST fail: remove index= from the build_scan_report
      call; from build_doctor_report; from build_compare_report (spy run
      requests a pair); a second live_discovery call in run_report. Record
      every mutation result.
3. **presentation/report.py (new, pure)** —
   markdown_text(model: ReportModel, display: Callable[[str], str]) -> str.
   CLI passes paths.display; TUI passes a lookup from
   SessionSnapshot.display_paths (fallback: raw string when unmapped).
   Every printed path goes through display — no machine account name in a
   shareable document; JSON keeps absolute shapes unchanged. The function
   returns the document WITHOUT a trailing newline; the emission layer prints
   it AS RETURNED and Rich's default end="\n" supplies the single trailing
   newline — do NOT append "\n" to the string first (that yields two;
   measured on rich 15.0.0, round-3 S-M). The TUI clipboard body is
   markdown_text itself and therefore carries NO trailing newline, unlike
   the CLI bytes. Sections in FIXED order:
   1. Title + metadata block: timestamp (pinned spelling), version,
      platform, home, cwd (home/cwd read from the scan payload,
      display-collapsed).
   2. "Detected agents" — ONLY scan.summary.detected_agents, in that tuple's
      sorted order, each id joined to its AgentSummary fields (name,
      collision_policy, policy_evidence, roots). Empty → heading plus
      "No agents detected on this machine." The registry is NEVER printed
      under this heading.
   3. "Known agents and precedence" — the full registry catalog (the agents
      payload verbatim) with a Detected yes/no column derived from
      scan.summary.detected_agents. Source citation URLs deliberately
      absent (matches agents --json).
   4. "Canonical library summary" — scan.summary counts, keeping
      canonical_skill_count (user scope) vs total_skills distinct.
   5. "Per-agent skill inventory" — detected ids in detected_agents order;
      under each, scan.skills whose agents tuple contains the id, in
      scope-then-name order (scanner.py:199). Rows: name, scope via
      SCOPE_LABEL (plugin prints "Plugin" — named assertion), variant
      label, parse/health state, description (printed, escaped), canonical
      path (display-collapsed). Empty home → heading plus an explicit
      empty sentence (no heading with nothing under it).
   6. "Doctor findings" — EVERY field: severity, evidence, rule_id, code,
      message, path (display-collapsed; EMPTY CELL when finding.path is
      None — never call display(None)), detail — in engine order
      (error → warning → info, then code, then path).
   7. "Compare highlights" — ONLY when compare is not None: counts by
      relation (derived in the renderer, never added to JSON), diverged and
      one-sided rows, and CompareReport.notes. Shared skills counts-only.
      Section absent when null.
   ESCAPER (Rich-free, exact oracle — G3): escape exactly this character
   set, SINGLE PASS (inserted backslashes are never re-escaped):
   \ ` * _ [ ] < > |
   Newlines: normalize \r\n → \n first, then replace EACH \n with one space
   (so two consecutive newlines become two spaces). Every interpolated
   dynamic string goes through it: inventory name and description, doctor
   code/message/rule_id/detail/displayed path, compare row names and notes,
   agent names in both agent sections. Dynamic strings never sit at a raw
   line start (always in table cells or after a fixed prefix), so escaped
   inline characters cannot open block structure. Published oracle (the
   plan pins these exact strings; the test asserts byte equality):
     input characters:  a \ b _ c ] d > e | f ` g [ h * i < CR LF k LF LF l
     output characters: a \ \ b \ _ c \ ] d \ > e \ | f \ ` g \ [ h \ * i \ < SPACE k SPACE SPACE l
   As literals:
     input:  "a\\b_c]d>e|f`g[h*i<j\r\nk\n\nl"
     output: "a\\\\b\\_c\\]d\\>e\\|f\\`g\\[h\\*i\\<j k  l"
   The Phase 3/4 Rich-escape lesson does NOT transfer (Rich escape leaves |
   intact; Rich is banned here). The CommonMark backslash escaper is
   compatible with Rich markup=False — belt-and-braces, not a conflict; do
   not "fix" the escaper to suit Rich. No Rich, no Typer, no writes.
4. **cli.py `report` command** — options: --sandbox, --cwd (scan semantics),
   --format (choices: md; default md; any other value → exit 2), --json
   (overrides --format), --output PATH, --agent (repeatable: ZERO → no
   compare; exactly TWO → compare; one/three/unknown/duplicate → exit 2
   BEFORE any discovery call).
   Exit-2 sentences (quoted exactly): unknown id reuses
   "unknown agent '{id}'. Known agents: {known}" (compare.py:159); duplicate
   reuses "cannot compare agent '{id}' with itself" (compare.py:38);
   cardinality gets its OWN sentence stating the legal counts:
   "pass --agent zero times (no compare) or exactly twice (two agents to
   compare); got {n}." — NOT compare's "exactly twice" sentence.
   Validation order, ALL before discovery: format choice → agent
   cardinality/ids (registry validation, no home walk) → --output path
   checks (existing file → exit 2; path is a DIRECTORY → exit 2 saying it
   is a directory; missing parent → exit 2; no mkdir, nothing created) →
   sandbox/cwd resolution (escape refusal unchanged) → run_report.
   EMISSION CONTRACT (B8): stdout is the plain markdown_text bytes (or
   canonical dumps bytes with --json) plus EXACTLY ONE trailing newline,
   UTF-8, emitted with soft_wrap=True, markup=False, highlight=False (the
   _emit_json idiom) — no wrapping, no markup interpretation, no
   highlighting, no ANSI, no Rich render. --output writes EXACTLY those
   same bytes (including the one trailing newline) via an explicit
   encoding="utf-8" write (never the locale default — round-3 S-N), and
   stdout receives NOTHING else. All exit-2 sentences go to STDERR like
   every other command (error_console with the "Error: " prefix for
   unknown/duplicate; typer.BadParameter for cardinality — round-3 S-O), so
   "stdout is exactly the report bytes" holds on the error path too. With --json the bytes are canonical dumps JSON even when
   --format md is also passed. Write failures → exit 2 in the contract's
   words ("the command could not run"); exit 3 reserved. --output is NOT
   clamped by --sandbox (sandbox governs mock-HOME reads; destination
   explicitly user-named). Success exits 0 regardless of findings. No
   --fail-on.
5. **TUI export (clipboard design, owner-approved)** —
   a. App-level R binding ("Export", show=True, NON-priority — matching
      Refresh) on Home, Why, Diff, Agents, Compare, Doctor. PLUS an explicit
      HelpScreen Binding("R", "app.export_report", "Export", show=True) —
      the modal stops non-priority app bindings (U8 precedent), exactly as
      Help already re-binds r→app.refresh (G2). While Home's filter Input
      has focus, R is filter text (same trade-off as "?" and y); the filter
      Help rows (home.py:751-776) and README say so. In EVERY screen's raw
      JSON view, R still exports the captured Markdown session report —
      a different action from y (which copies the view on screen).
   b. State rule: controller.current is None (idle, initial loading,
      initial retry, initial refusal, initial error) → notice "Nothing to
      copy yet.", NO copy_to_clipboard, NO discovery/run_report call.
      current is not None → export THAT published snapshot under ANY
      status: loading (refresh in progress), retry, refused, error,
      sticky-failed, and closed (close() does not clear current — closed
      follows current). Never gate on status == "ready".
   c. Payload: assemble_report fed ONLY from the snapshot:
      scan=snapshot.scan.to_dict(), doctor=snapshot.doctor,
      agents=tuple(agents_payload(snapshot.registry)) (snapshot.registry is
      already a tuple; the payload RESULT is a list and needs the conversion),
      compare=None, meta via the SAME utc_timestamp function (injectable
      clock, default now(UTC)) + __version__ + injectable platform_text
      (default platform.platform()). Home/cwd from the snapshot; display
      function = snapshot.display_paths lookup. NO build_report/run_report/
      discovery from the key — the export can never disagree with the
      screen or re-crawl.
   d. compare=None ALWAYS for TUI export: the session holds no pair; the
      Compare screen's on-screen selection is deliberately NOT included.
      USER-VISIBLE limitation: the Help row and FULL_SCREEN_TUI.md keymap
      line state that R copies the captured scan, doctor and detected-agent
      Markdown and does not include the Compare screen's selected pair.
   e. Emission: clipboard.copy_decision(text, os.environ);
      app.copy_to_clipboard ONLY for SENT. Notices: uniform app-level
      Textual notifications for R (one mechanism across all screens incl.
      Help; y's per-screen Static notices unchanged): SENT → report-specific
      confirmation; BLOCKED → "Clipboard not supported in this terminal";
      TOO_LARGE → "Too large to copy via terminal clipboard" plus guidance
      "For large reports use: skill-lens report --output <file>". BLOCKED
      precedence and the >75,000-UTF-8-byte check are the existing module's.
      Pinned y sentences NOT reworded.
   f. Help: R row in _COMMON_ROWS (help.py:37) so EVERY covered screen shows
      it, with CLIPBOARD_LIMITATION and the compare-limitation sentence;
      test asserts build_help_body for a non-Home origin contains the row
      AND the compare-limitation sentence. Help READ-ONLY paragraph
      (help.py:135-136) gets ONE replacement sentence (owner decision 3):
      "Skill Lens never changes your skills or agent files. The only file
      it ever writes is a report you explicitly request with
      `skill-lens report --output <file>`; the TUI's R export is
      clipboard-only (no file)." — pinned by a new test assertion.
   g. Export helper lives in app.py — NO new tui/ module. No new write
      capability anywhere in tui/; AST guard passes unchanged.
6. **Tests** (synthetic HOME only; tmp_path + monkeypatched paths; fixtures
   keep cwd and every skill INSIDE the mock HOME so display collapses them
   and pinned text is CI-reproducible):
   - tests/test_report.py:
     * Read-only before/after fixture listing around build_report/run_report.
     * ONE-PASS SPIES exactly per step 2e (bindings, budgets, engine-level
       bad-pair 0/0, all four mutations recorded).
     * Cross-command parity: nested agents/scan/doctor/compare payloads
       byte-identical to the respective --json outputs on the same fixture.
     * from_dict(to_dict()) == model on BOTH goldens (agents tuple rebuild);
       compare key null without pair, object with one.
     * Goldens golden/report/report_farm.json +
       report_compare_claude_vs_codex.json on build_acceptance_farm with
       FIXED generated_at AND fixed platform token; RECURSIVE _rel-rule
       rewrite of EVERY string (absolute prefix, ~/ collapsed form,
       resolved home spelling); absence check rejects str(home) AND
       str(home.resolve()); canonical-byte check; fail-on-missing;
       --update-goldens only after reading the diff.
     * Markdown snapshots under snapshots/report/ (name="report/<case>")
       with injected clock + platform; machine-path ban.
     * Timestamp function: aware +02:00 → +00:00 spelling; naive → raises.
     * Empty-home test: the SIX headings present (metadata block, Detected
       agents, Known agents and precedence, Canonical library summary,
       Per-agent skill inventory, Doctor findings), Compare heading ABSENT,
       detected empty sentence + inventory empty sentence, counts zero,
       exit 0, registry NOT under the detected heading.
     * Unreadable-root synthetic fixture (discovery unreadable_roots, no
       live TCC prompt): Markdown contains doctor_tcc, severity warning and
       the DISPLAY-COLLAPSED root (~/...), and str(home) is ABSENT; JSON
       contains the finding plus scan.unreadable with absolute
       agent/root/path/detail. None-path finding (synthetic uncited registry
       entry) renders an empty cell without calling display.
     * Escaper oracle: the EXACT published input/output pair (step 3), byte
       equality; single-pass (no double-escaping); hostile fixture strings
       in name AND description; a doctor message containing | (hostile root
       directory name) stays table-safe; every interpolated-string category
       covered.
     * Plugin label named assertion: plugskill row contains "Plugin".
     * Inventory order: detected-id order, scope-then-name within agent.
     * Compare notes: constructed CompareReport with non-empty notes →
       Markdown contains them (farm alone cannot prove this).
     * agents_payload receives a sequence (registry.values()), never dict
       keys.
     * --format html / any non-md → exit 2.
   - tests/test_cli.py: default md; explicit --format md; --json canonical;
     --json --format md → JSON wins; --output writes exactly the stdout
     bytes and stdout empty; --json --output writes canonical JSON bytes;
     BYTE-FIDELITY proof: captured stdout and file equal
     markdown_text(...).encode("utf-8") + b"\n" (or dumps(...).encode() +
     b"\n") and contain NO ESC (0x1b) byte — _PlainRunner strips ANSI, so
     equality alone is not the proof; a >80-column table row stays intact
     on ONE line; existing file → exit 2; directory → exit 2 (says
     "directory", creates nothing); missing parent → exit 2 (no mkdir); all
     refusals BEFORE discovery (spies); --agent 0/2 legal, 1/3/unknown/
     duplicate → exit 2 with the exact quoted sentences, before discovery;
     --sandbox/--cwd clamping incl. absolute-cwd escape refusal; --output
     outside the sandbox succeeds while reads stay clamped; exit 0 with
     findings; read-only listing: fixture home unchanged, exactly one new
     file when output is outside it.
   - TUI (Pilot): captured-payload proof — injected snapshot whose skill
     name does NOT exist on the live home + discovery monkeypatched to FAIL
     if called → R emits one OSC 52 whose body contains that skill name,
     the version, the pinned timestamp spelling, NO compare section.
     current-is-None cases: idle, loading, refused, error → "Nothing to
     copy yet.", no clipboard call. Retained-snapshot cases: loading
     (pending_generation set, current set), retry (retry_message, current
     kept), refusal (refusal_message, current kept), sticky-failed, closed
     with current → export still works. HELP-OPEN case: Help over a
     captured session, press R → one OSC 52 with the captured Markdown
     (modal binding proof). Home JSON view: R exports Markdown (not the
     JSON y copies); same rule asserted on at least one other screen's
     JSON view. BLOCKED (TMUX/screen) and TOO_LARGE (>75,000 bytes) → exact
     notice strings, NO OSC 52; SENT → confirmation + copy_to_clipboard
     exactly once. Compare screen with pair selected → body has no compare
     section. Help row + compare-limitation SENTENCE present for a non-Home
     origin; Help READ-ONLY paragraph contains the new pinned sentence.
     Home filter focused → R is filter text. AST guard passes; fixture
     preservation across export.
   - Installed lane: test_report.py inserted at the SAME index in BOTH
     tuples (order-sensitive equality guard); the stale docstrings
     (test_tui_packaging.py:394 "nine original suites and the five U9
     additions", :402 "All 14 selections") updated to 15 in the same edit
     (round-3 S-S); record the lane's post-change duration against the 300 s
     bound. 17/16 count assertions NOT touched. No wheel/lane file-list
     update needed: hatchling ships the whole package and smoke_wheel.py:572
     copies the whole tests/ tree (verified round 3).
   - Mutation controls (record every result): banned write planted in the
     export path → AST guard fails, restore → passes; delete a new golden →
     fails; perturb renderer → snapshot fails; the FOUR one-pass mutations
     of step 2e → spy tests fail; remove/weaken the escaper → oracle fails;
     re-introduce the runtime registry import in models/agents.py → the
     registry-first cycle probe fails, restore → passes (round-3 S-Q — every
     new gate must be mutation-tested, project-profile §2).
   - Coverage: baseline 90.23% vs fail_under 90 — new modules near-fully
     covered INCLUDING error paths.
7. **Docs + owner-approved wording package** —
   README: Commands row + report section documenting the timestamp spelling,
   compare:null always present, detected set lives in
   scan.summary.detected_agents while the agents key is the known catalog
   (JSON discoverability), derived counts (scripted users recompute
   counts_by_relation / counts_by_severity), --output semantics (exact
   stdout bytes + one trailing newline, refusals, not sandbox-clamped),
   R key with filter caveat, Help-modal behavior and compare limitation.
   Strictly additive EXCEPT one named accuracy fix (round-3 S-J):
   README.md:86 "All six commands are built and tested." → "All seven
   commands are built and tested." The neighbouring HISTORICAL sentence
   (README.md:225-227, "Published (PyPI skill-lens-cli 0.2.0 …): the six
   line-oriented CLI commands") is a true statement about 0.2.0 and must NOT
   be reworded. Pinned y/CLIPBOARD_LIMITATION sentences not reworded;
   absolute links only. CHANGELOG [Unreleased]/Added entry.
   FULL_SCREEN_TUI.md additive keymap/Help line for R (incl. the modal
   binding and compare limitation; no contract rewrite) PLUS the same
   one-clause "top-level" qualification on its 17/16 sentence (:367-368) as
   DEVELOPMENT.md:363 (round-3 S-K).
   DEVELOPMENT.md:363 one-clause qualification: "the 17 top-level CLI
   snapshots and 16 JSON goldens (top-level + phase4/; report fixtures live
   in subdirectories the count globs do not see)".
   SKILL_LENS_SPECIFICATION.md (owner decision 3, exact texts):
   - §5 bullet, appended inline dated note in the 0.2 style:
     "**Amended for issue #6 (2026-11-19, owner decision):** the only file
     Skill Lens ever writes is the explicitly requested report output
     (`skill-lens report --output <file>`); every other operation remains
     strictly read-only."
   - §8.1 item 1, appended: "**Amended for issue #6 (2026-11-19, owner
     decision):** the single exception is the explicitly requested report
     output file; no skill, agent file, or directory is ever created,
     modified, moved, or deleted."
   - §6 new entry 7 for skill-lens report (options, sections, destination
     rule, exit codes, timestamp spelling, compare:null).
   docs/process/profiles/project-profile.md: §1 tree lines (:19, :22-23)
   updated for the report command and new modules (round-3 S-L accuracy
   fix), and §3 appended dated note:
   "**Amended for issue #6 (2026-11-19, owner decision):** the single
   exception is the explicitly requested report output (`skill-lens report
   --output <file>`); every other operation remains strictly read-only."
   tui/help.py READ-ONLY paragraph: the step 5f sentence (pinned by test).
   AGENTS.md unchanged (Golden Rule 1 speaks of user skills; a report file
   is not a skill — rationale recorded per mcode S-C).
   Existing 17 CLI snapshots + 16 JSON goldens byte-unchanged; a later
   version bump requires reviewed golden/snapshot updates (__version__
   embedded).

## Acceptance

Issue #6 acceptance criteria mapped:
- [ ] report command with --format md and --json (steps 2-4; CLI tests incl.
      flag combinations, non-md rejection, exact exit-2 sentences).
- [ ] --output <file> option (step 4; exact-bytes + trailing-newline,
      stdout-empty, no-ANSI, refusal and pre-discovery-validation tests).
- [ ] Report includes scan + doctor + agents sections (step 3; goldens +
      snapshots pin every section, all seven doctor fields, metadata, the
      detected/known split, empty-home six headings, unreadable-root and
      None-path cases, escaper oracle, compare notes).
- [ ] TUI export action (step 5; Pilot tests incl. None states,
      retained-snapshot states, closed, Help-open modal R, JSON views,
      captured-payload proof, BLOCKED/TOO_LARGE, Compare-pair exclusion,
      Help row + limitation sentence + READ-ONLY paragraph).
- [ ] Tests and snapshot coverage (step 6; fail-on-missing goldens,
      spy-proven one pass with four recorded mutations, installed lane
      extended at matching index, duration recorded).
Project gates (all four, on the final tree):
- [ ] pytest --cov=skill_lens (coverage ≥ 90%, tui/ measured)
- [ ] mypy (strict, skill_lens/)
- [ ] ruff check .
- [ ] ruff format --check .
Invariants:
- [ ] Read-only: engines/models/renderers/TUI write nothing (fixture
      listings + AST guard + discovery spies); the only write is the
      explicit --output file (exact-path confinement, overwrite/directory
      refusal, pre-discovery validation).
- [ ] models/ has no runtime registry import; registry-first import works
      in a fresh interpreter (cycle probe as a test).
- [ ] Existing snapshots/goldens byte-unchanged; 17/16 count gates
      untouched; new pinned output reviewed before regeneration.
- [ ] One discovery pass — PROVEN by call-count spies on the actual
      bindings; validation-before-walk proven at engine AND CLI level.
- [ ] Nested payloads byte-identical to existing --json outputs
      (total_skills included, compare:null always present, no new derived
      serialized fields); agents --json byte-identical after the move.
- [ ] Markdown emission byte-faithful: no wrapping, no markup consumption,
      no ANSI; stdout == file bytes == markdown_text/dumps + one newline.
- [ ] Golden stability across the CI matrix: fixed injected clock AND
      platform token; recursive _rel normalization; no machine path
      (str(home) and str(home.resolve())) in any pinned text.
- [ ] No new dependency; no AI/network/telemetry; provenance verbatim.
- [ ] Owner-approved wording package applied exactly (spec, project-profile,
      Help paragraph); AGENTS.md untouched.

## Review decisions

Round 1 (2026-11-19): both critics changes_required; 13 blockers + 21
suggestions, ALL reproduced and ACCEPTED, folded into revision 2. Full
ledger preserved in the revision-2 text and
~/.hermes/cache/scratch/sl-report-plan/amendments-r1-draft.md; verbatim
reports critic-mcode-r1.md / critic-grok-r1.md. Fingerprints CLEAN.

Round 2 (2026-11-19): both critics changes_required AGAIN, but both
explicitly confirmed ALL round-1 findings resolved. Five NEW precision
defects, all coordinator-reproduced with verified remedies (full evidence:
~/.hermes/cache/scratch/sl-report-plan/round2-ledger.md; probes kept at
scratch/sl-report-plan/cycle-probe):
- mcode B7 ACCEPTED (reproduced: literal step-1a move → registry-first
  ImportError on a scratch package copy; TYPE_CHECKING variant clean,
  payload identical) → step 1a TYPE_CHECKING-only + models-no-runtime-
  registry rule + corrected invariant sentence.
- mcode B8 ACCEPTED (reproduced: default Rich print splits a 105-char row
  and consumes the backslash before "["; safe flags byte-faithful) →
  step 4 emission contract + byte-fidelity tests.
- grok G1 ACCEPTED (reproduced: discover copied into scanner/doctor/compare/
  system namespaces; system.py:101; suite patches consumer bindings) →
  step 2e spy contract on the actual bindings; run_report validates before
  live_discovery; four named mutations.
- grok G2 ACCEPTED (reproduced: HelpScreen ModalScreen re-binds q/r; U8
  frozen plan documents modal blocking) → explicit HelpScreen R binding +
  Help-open Pilot test.
- grok G3 ACCEPTED (reproduced: unreadable_root message embeds display while
  path is raw; registry_uncited path=None; oracle charset subset) →
  published exact escaper input/output, single pass, every interpolated
  string, collapsed-path assertions, None-path empty cell.
- mcode S-A..S-I ALL ACCEPTED (ledger B1 rationale restated: route (i)
  rejected to avoid a second hand-maintained copy of the scan shape —
  adding from_dict would not itself change a public shape; from_dict tuple
  rebuild; wording package extended to project-profile §3 + Help paragraph
  with AGENTS.md rationale; lane tuple same-index + duration record;
  fixtures inside mock HOME; README detected-key discoverability; inventory
  empty sentence; DEVELOPMENT.md top-level qualification; models rule).
- grok suggestions ALL ACCEPTED (three retained-snapshot Pilot cases +
  closed follows current; JSON-view R rule + tests on all screens; Help
  limitation-sentence assertion; exact exit-2 sentences incl. new
  zero-or-two cardinality sentence; no-ESC byte proof; recursive _rel
  normalization incl. resolved-home absence check; six named empty-home
  headings + Compare absent; non-empty notes assertion; registry.values()
  sequence; shared aware-UTC timestamp function + platform_text naming;
  Help READ-ONLY paragraph sentence).
- grok quota incident: 402 weekly-limit AFTER complete report delivery;
  recorded; no silent substitute (council §1.3).
- Council §5 escalation TRIGGERED (two rounds without a clean pass);
  owner resolved it on 2026-11-19: option 2 — replacement second reviewer
  agy/gemini-3.8-flash-high for one targeted confirmation round; wording
  package approved ("Yes"). Owner decisions 3 and 4 recorded above.
Round 1+2 conceded points (8+6 mcode, 6+8 grok) are recorded in the verbatim
reports and are not re-raised.

Round 3 (2026-11-19, targeted confirmation per the owner's escalation
decision): BOTH CRITICS PASS. Fingerprints before/after: CLEAN.
- agy/gemini-3.8-flash-high (critic-agy-r3.md): VERDICT pass; BLOCKERS none;
  SUGGESTIONS none. Every round-2 finding of its axis (G1/G2/G3 + all 10
  suggestions) verified resolved with plan-line citations; the other axis's
  B7/B8 fixes cross-verified against the source; "the plan is sound,
  complete, and ready to freeze." EFFECTIVE_MODEL honest: model confirmed
  from session selection; effort high confirmed by coordinator readback of
  the /model picker (slider at high, status "Gemini 3.8 Flash · high").
- mcode/MiniMax-M3.1-Flash-xhigh (critic-mcode-r3.md): VERDICT pass; zero
  blockers. B7/B8 and S-A..S-I withdrawn as resolved (each re-verified
  against source; the published escaper oracle pair recomputed BY HAND and
  matched byte-for-byte; four potential concerns withdrawn before raising
  after source checks — detail fields, display fallback coverage, phase5
  subset assertion, AST render-ban). Ten NON-BLOCKING suggestions S-J..S-S,
  ALL ACCEPTED and incorporated verbatim into the steps/scope above:
  S-J README:86 six→seven (historical 0.2.0 sentence protected);
  S-K FULL_SCREEN_TUI.md:367-368 top-level qualification;
  S-L project-profile §1 tree lines;
  S-M print-as-returned newline mechanics + TUI body has no trailing newline;
  S-N explicit encoding="utf-8" for --output;
  S-O exit-2 sentences to stderr;
  S-P tuple(agents_payload(...)) at both call sites;
  S-Q cycle-probe mutation control (required by project-profile §2);
  S-R test_phase5_gate.py expected set gains "report";
  S-S lane docstrings 14→15.
  These are the passing critic's own one-line prescriptions — clarifications
  of the already-agreed contract, not behavior/scope changes; incorporated
  under the coordinator's §6 correction authority and recorded here.
No unresolved objections remain on either axis. Owner decisions 1-4 all
resolved. The plan is AGREED and proceeds to the two-commit freeze.

## Baseline gates (unchanged tree, before any dispatch)

Run 2026-11-19 via herdr-core job t117 on base commit b22dbe7 (branch
feat/issue-6-report, identical tree), venv executables, log:
~/.hermes/cache/scratch/sl-report-plan/baseline-gates.log

- pytest --cov=skill_lens: **1446 passed, 1 skipped** in 454.39s; coverage
  **90.23%** (threshold 90.0% reached) — exit 0
- mypy: Success, no issues in 48 source files — exit 0
- ruff check .: All checks passed — exit 0
- ruff format --check .: 447 files already formatted — exit 0

The 1 skipped test and the 13 pre-existing untracked paths are the unchanged
baseline state; this mission does not touch them.

## Execution record — rounds 1-2 (append-only)

Round 1: mcode-critic t116 / grok-critic t115 launched, ended before dispatch
(terminals closed; no task lost). Relaunched t129/t12b (--parent t7w),
banners verified, shown in panel, briefs sent in one wave (started:true).
Reports: critic-mcode-r1.md (6 blockers/13 suggestions/8 conceded),
critic-grok-r1.md (7 blockers/8 suggestions/6 conceded). t7w ended
mid-mission (killed, exit 1); session resumed at t128 (screen-verified);
grok discovered t128 and delivered there. Fingerprints CLEAN. Terminals
settled. Elapsed ~30 min; token usage unavailable.

Round 2: revision 2 written (all round-1 findings folded in). Fresh sessions
t12c (mcode) / t12d (grok), --parent t128, banners verified (M3.1-Flash ·
Effort xhigh; Grok 4.7 (high) · Weekly limit left 6%), shown in panel,
fingerprints captured (2933 lines), briefs sent in one wave (started:true).
Reports: critic-mcode-r2.md (changes_required; B7/B8 + 9 suggestions; all
r1 findings confirmed resolved; invoked §5 escalation), critic-grok-r2.md
(changes_required; G1/G2/G3 + 10 suggestions; r1 findings withdrawn as
resolved). grok then hit 402 weekly-limit (dialog: Upgrade tier / Buy more
credits / Try Again) — report was already complete and delivered.
Coordinator reproduced ALL five new blockers (cycle-probe + rich emission
probe + source verifications; evidence in round2-ledger.md). Fingerprints
CLEAN. t12c/t12d killed+removed (exit notifications confirmed). Council §5
escalation presented to the owner with four options; owner chose option 2
(agy/gemini-3.8-flash-high replacement) and approved the wording package.
Round 3: revision 3 written (all round-2 findings + owner decisions 3/4
folded in). Fresh sessions t12f (mcode) / t12g (agy), --parent t128; banners
verified before dispatch (M3.1-Flash · Effort xhigh; agy /model picker:
"Gemini 3.8 Flash (current)", effort slider high, status line "auto ·
Gemini 3.8 Flash · high" — auto is agy's own default mode, no bypass flag
added); shown in panel; fingerprints captured (2933 lines); briefs sent in
one wave (started:true receipts). Reports: critic-mcode-r3.md (PASS, 0
blockers, 10 non-blocking suggestions), critic-agy-r3.md (PASS, 0 blockers,
0 suggestions). Fingerprints CLEAN. Both terminals settled after collection.
Council §6 receipt (planning mission): expected 2+2+2 critics across three
rounds; actual launches: r1 t116/t115 (ended before dispatch, relaunched
t129/t12b), r2 t12c/t12d, r3 t12f/t12g — 6 successful dispatches, 2 pre-
dispatch terminal losses, 0 extra rounds beyond the owner-approved targeted
round 3; grok quota exhausted after r2 delivery (402), owner named the agy
replacement; token usage unavailable (CLIs do not expose it). Freeze, branch
link and push receipts: appended below after execution.
