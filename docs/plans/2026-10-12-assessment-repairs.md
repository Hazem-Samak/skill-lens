<!-- Authorized supplied implementation plan; imported without a planning loop. -->
Status: Agreed
Authorization: User instruction on 2026-10-12 to address the attached assessment through the implementation loop, skipping the planning loop; OpenCode V2 selected explicitly.
Reference: fe6f89bc55eb3f4f04187567b968dd96ae9c86c1
Risk: High

Execution contract: Section 6 of the supplied assessment is the operative staged plan. The assessment below is preserved verbatim. Commit verified changes as coordinator under the implementation loop; do not push, publish, tag, or replace existing dist artifacts. Sole implementer: Antigravity gemini-3.8-flash-high. Independent critics: OpenCode opencode/space-bunny-free variant=max and MCode m:minimax:MiniMax-M3.1-Flash-Preview:v:thinking thinkingEffort=xhigh. Space Bunny family identity is unverified; the user explicitly selected this named pair. OpenCode support: V2 only; disclose V1 as unsupported. Other version/surface corrections must follow primary evidence, preserving supported legacy roots. Measure resource risk without imposing a new memory policy. Test current Textual compatibility before proposing any dependency policy change. U3-U9 and release work remain outside scope.

---

# Skill Lens Project Assessment Final

**Assessment date:** 12 October 2026  
**Project:** `/Users/corvette/Documents/Projects Coding/Skill Lens`  
**Assessed revision:** `9fd55231e26baa1f7bc0d4124123204ae187f9d9` (`main`)  
**Mission:** Independent, single-worker, read-only assessment of the project and all nine reviewer reports. No product fixes, commits, pushes, snapshot updates, or project planning loop were performed.

## 1. Final verdict

**Skill Lens has a sound foundation and a substantial test suite, but passing that suite does not yet establish that its answers match current agent behavior.** Several reviews correctly identified documentation, packaging, test-isolation, and compatibility weaknesses. Their broader conclusions—such as “production-grade A+,” “the engine is finished and trustworthy,” or “only screens and documentation remain”—are stronger than the evidence supports.

The most important findings are about the tool's actual answers:

- Some agent definitions contradict current primary documentation or omit documented default locations and configuration controls.
- Unreadable asset folders can be silently left out, making different skill copies appear identical.
- `scan --fail-on error` can report success for broken skills that make `doctor --fail-on error` fail.
- Relative working-directory input and merged shortcut paths can hide skills or assign the wrong lookup name.
- Ordinary plugin documentation can be treated as a broken skill.

These are correctness problems, not requests for additional TUI screens. **Repair the answer-producing foundation before treating the remaining work as only U3–U9.**

I did not find a demonstrated destructive product operation, telemetry, AI calls, or database usage. The read-only design is real, but the tests are not a mathematical proof that every future write operation will be caught.

### Priority guide

- **High:** Can give a confidently wrong answer, hide a real problem, or falsely certify equivalent content.
- **Medium:** A real failure, incomplete safety check, or operational gap that should be repaired before the next release.
- **Low:** A narrow inconsistency or explanation defect; fix without expanding scope.
- **Risk:** A verified exposure or design limitation, but not a demonstrated current failure of the ordinary supported workflow.

## 2. What was independently verified

I read the nine Desktop assessments, current source, specification, relevant historical findings, tests, CI configuration, TUI contracts, and packaging configuration. I also compared primary agent documentation with the registry and ran targeted reproductions against unchanged source.

Tests, builds, synthetic skill folders, and verification environments were kept in:

`/Users/corvette/.hermes/cache/scratch/skill-lens-final-assessment/`

No real skill library was used as a test fixture. In the full test run, an external guard intercepted `Path.exists()` and `Path.is_symlink()` for `/etc/codex` and `/private/etc/codex`, returning false and recording attempts. This deliberately prevented the test-isolation defect described in F12 from reaching a real system root. It was **not** a blanket interception of every filesystem operation.

### Verification results

| Check | Independently observed result |
|---|---|
| Full test suite, in an isolated source copy with fake HOME and system-root guard | **785 passed, 1 skipped, 0 failures, 0 errors** |
| Project coverage gate | **94.30% overall coverage with branch measurement enabled**, exceeding `fail_under = 90` |
| Statement coverage | **96.15%** |
| Branch-only coverage | **88.22%** — 801 of 908 branches |
| Strict typing | `mypy`: **no issues in 34 source files** |
| Lint | `ruff check`: **all checks passed** |
| Formatting | `ruff format --check`: **117 files already formatted** |
| Fresh wheel/sdist build from unchanged source copy | Succeeded |
| Fresh wheel installed in a clean base environment | All six JSON commands worked; Textual genuinely absent; bare launch printed help; explicit TUI returned exit 2 with the installation hint |
| Fresh wheel installed with `[tui]` in a clean environment | All six JSON commands worked; headless TUI opened and quit with exit 0 |
| Python 3.14 compatibility probe | Commands and headless TUI worked; deprecated asyncio policy call produced a warning; an existing non-running caller loop was restored |
| Local vs remote `main` | Same assessed commit; both published version tags exist remotely |
| Source-tree preservation | Original hashes and recorded metadata unchanged; git working tree remained clean |

**Coverage correction:** The reviewers repeatedly call 94.30% “branch coverage.” It is coverage.py's combined score when branch measurement is enabled, not the branch-only percentage. The current 90% gate applies to that combined score. This does not mean the coverage gate failed; it means the metric should be described accurately.

**Limits of verification:** The full suite was run on the local Python 3.11 environment, not independently across the entire eight-job CI matrix. The Python 3.14 probe reused the installed wheel and compatible pure-Python dependencies through an explicit import path; it was not a separate clean Python 3.14 dependency installation. I did not run native agent sessions, call model providers, reproduce real macOS permission prompts, measure a full live-home library, or execute Python 3.16. Vendor comparisons below establish implementation-versus-documentation mismatches, not a claim that every installed vendor version was exercised.

## 3. Accepted findings and proper fixes

The IDs below are **action groups**, not a claim that each group contains exactly one defect. Related symptoms are grouped so the next implementation fixes their common cause.

### F01 — Agent rules are not sufficiently current or version-specific

**Priority: High. Status: Confirmed current-documentation mismatches and missing documented locations.**

The registry validates that a citation exists and resembles a URL. It does not establish that the citation supports the current rule, which version was tested, or which product surface it describes. The specification itself contains some of the old assumptions, so merely making implementation agree with that specification is insufficient here.

| Agent / concern | Current Skill Lens behavior | Primary-source comparison |
|---|---|---|
| Claude lookup names | `claude.toml` uses directory identity; a folder named `folder-key` with `name: declared-key` cannot be found by `declared-key` | Current Claude docs say the frontmatter name sets the command, while the directory name can also invoke the skill |
| Pi lookup names | `declared-key` is not found; `folder-key` is reported active | Current Pi docs and `loadSkillFromFile()` use the frontmatter name with a directory fallback |
| Qoder priority | A project `.qoder/skills/deploy` wins over the user copy in the reproduction | Current Qoder CLI docs explicitly say **user-level skills override project-level skills** |
| Antigravity CLI locations | A skill in `~/.gemini/antigravity-cli/skills/` is not discovered | Current docs distinguish CLI locations from Antigravity 2.0/IDE locations; the registry's CLI label currently uses the latter's `.gemini/config/skills` location |
| OMP managed location | A skill in `~/.omp/agent/managed-skills/<name>/SKILL.md` is not discovered | The current upstream docs specify that managed-skills location; the registry uses `.omp/agent` without the required traversal |
| OpenCode compatibility roots | A skill under `.claude/skills` is found through Claude but classified `UNSEARCHED` for OpenCode | Both the original and V2 OpenCode docs include Claude-compatible global and project roots |
| OpenCode versions | One frontmatter-identity, ambiguous-collision definition represents OpenCode | V2 docs specify path-derived IDs, documented later-source precedence, recursive `SKILL.md` discovery, and a different permission format. Those rules cannot safely be mixed into a single unversioned definition for both versions |
| Agent-specific validity | A Claude skill without a description is marked `INVALID` | Current Claude docs make description optional and provide a body-line fallback. OMP requirements also differ by provider, and OpenCode V2 makes frontmatter optional at runtime |

**Code anchors:** `skill_lens/registry/agents/{claude,pi,qoder,antigravity,omp,opencode}.toml`; `core/resolver.py:139–182`; `core/parser.py`; `registry/loader.py`.

**Proper solution:**

1. Record the supported agent version or version range, surface (CLI/IDE), source section, and evidence date. Use focused citations rather than a repository homepage when specific documentation exists.
2. Correct each proven rule for that declared target. Do not erase a genuinely supported legacy location solely because newer documentation uses another one.
3. Separate raw file parsing and portability diagnostics from the question “will this particular agent load it?” A uniform missing-description rule may remain a portability warning, but must not falsely assert that every agent rejects the skill.
4. Choose an explicit OpenCode support contract: a documented V1 profile, a V2 profile, or separately selectable profiles. Until that choice is made, disclose the unsupported version rather than claim complete behavior.
5. Add fixtures for differing folder/frontmatter names, Qoder user-vs-project conflicts, the missing default roots, nested discovery where actually supported, and version-specific precedence.
6. Re-check the other registry entries, but **do not invent replacement rules** where primary evidence is unavailable.

**Acceptance:** Every changed rule has version/surface-specific evidence and a regression fixture; the cases above match that declared contract. Unknown behavior remains explicitly unverified. Changing old goldens without reviewing their underlying assumptions does not satisfy this finding.

### F02 — Configuration can disable a skill while Skill Lens still calls it active

**Priority: High. Status: Reproduced; current configuration support is incomplete.**

Three synthetic cases returned `ACTIVE`:

- Claude: `{"skillOverrides":{"deploy":"off"}}` in user settings.
- Codex: `[[skills.config]]` with the skill's `SKILL.md` path and `enabled = false`.
- OpenCode's original configuration format: `permission.skill.deploy = "deny"`.

The Claude decoder only treats the JSON boolean `false` as disabled. Current Claude documentation specifies four string states, including `"off"`, and project/local settings also participate. The current snapshot captures only the registry's single home-relative settings path. Codex and OpenCode controls are not represented by the same mechanism.

**Code anchors:** `core/resolver.py:185–214,242`; `core/snapshot.py:159–176`; `registry/agents/claude.toml:9–11`; the Codex and OpenCode definitions.

**Proper solution:** Implement small, version-specific, pure decoders and configuration precedence rules. Capture their required local inputs during session capture and pass resolved controls to the resolver. Apply overrides to the agent's actual lookup identity/path, not whichever merged entry name happened to be retained first.

Do not flatten “not advertised to the model,” “manual invocation only,” “permission denied,” and “entirely disabled” into the same state. For unsupported controls, report the limitation instead of unqualified `ACTIVE`. Do not fetch remote catalogs, execute agents, or make network/model calls at product runtime. Do not expose full configuration files or secrets in report output.

**Acceptance:** CLI and captured-session results agree for enabled/disabled states, configuration precedence, missing/malformed inputs, and supported permission modes. Once captured, changing the original config does not alter that generation's reports.

### F03 — Unreadable asset folders can be silently omitted and falsely compare equal

**Priority: High. Status: Reproduced with actual denied directory permissions in scratch fixtures.**

Two skills had identical `SKILL.md` files but different `assets/data.txt` contents. Before blocking their asset folders, the directory hashes differed. After the synthetic asset folders were made unreadable:

- Both skills received the same non-null content hash.
- Scan reported no health severity.
- Doctor reported no non-informational finding.
- Diff reported no differences.
- Session capture retained only `SKILL.md` and accepted the incomplete captures.

`os.walk()` skips traversal failures by default when no error callback is supplied. Repeating the same incomplete walk does not make it complete.

**Code anchors:** `core/hasher.py:40–58,117–130`; `core/discovery.py:395–405,508–511`; `core/diff.py:130–139`; `core/snapshot.py:178–218`.

**Proper solution:** Make traversal completeness an explicit result. Record denied/disappearing subfolders and file-read failures; never issue a complete fingerprint for a partial tree. Propagate the failure to discovery, scan, doctor, compare, diff, and capture. A partial/unreadable copy must not qualify as a verified `shared` copy or receive a “no differences” assurance.

Keep ordinary absence, changed-during-scan input, and stable permission denial distinguishable. If capture cannot produce a complete generation, show the reason and retain the previous complete generation, rather than publish a falsely complete one.

**Acceptance:** A denied nested asset directory produces an incomplete/unreadable outcome and visible diagnostics. Its hash cannot certify equality. Tests cover both denied directories and denied files, deterministic injected failures on all platforms, and permission tests where supported. Review snapshots/goldens before any update.

### F04 — Scan and doctor gates disagree on the same broken input

**Priority: High. Status: Reproduced.**

| Synthetic condition | `scan --fail-on error` | `doctor --fail-on error` |
|---|---:|---:|
| Dangling skill shortcut | Exit **0** | Exit **1** |
| Shortcut cycle | Exit **0** | Exit **1** |
| Unreadable/invalid-UTF-8 skill document | Exit **0** | Exit **1** |

For broken links, discovery exposes an `invalid` status not covered by scan's severity mapping. For unreadable documents, scan assigns warning while doctor assigns error. This contradicts scanner comments promising agreement for equivalent conditions and can let a CI gate miss broken skills.

The bad-UTF-8 case also demonstrates misleading wording: doctor says the operating system refused access, although the fixture's problem was decoding the contents.

**Code anchors:** `core/scanner.py:111–141`; `core/doctor.py:102–137`; discovery's error/parse tags; `tests/test_phase6_gate.py:177–190`.

**Proper solution:** Define shared health-condition classification with distinct error causes. Carry the required condition into scan models rather than infer health from an incomplete parse-status string. Preserve the documented distinction between a blocked root and an unusable skill document. Test equivalent findings, not total parity for every doctor-only informational check.

**Acceptance:** For each shared health condition, both commands print their report and give the same threshold result for `never`, `warning`, and `error`. Dangling links and cycles cannot silently pass `scan --fail-on error`. Invalid encoding is not described as a permissions refusal.

### F05 — Relative `--cwd` silently scans the wrong location; XDG resolution is not connected

**Priority: Medium. Status: Reproduced.**

From inside a synthetic Git project containing one local skill:

- Default `scan`: found the skill.
- `scan --cwd .`: found **no** project skill.
- `scan --cwd <absolute-project-path>`: found the skill.

The CLI returns the relative path unchanged outside a sandbox, while discovery interprets all relative paths against HOME. The report can even retain `cwd: "."` while the scan was performed elsewhere.

Separately, `paths.xdg_config_home()` correctly reads a synthetic `XDG_CONFIG_HOME`, but discovery never uses it for the OpenCode root. A skill placed under that custom config root was missed. The specification explicitly assigns XDG resolution to paths.py for OpenCode.

**Code anchors:** `cli.py:172–185`; `core/discovery.py:262–272,301–317`; `core/paths.py:56–61`; `SKILL_LENS_SPECIFICATION.md:252`.

**Proper solution:** Resolve user CLI input once: terminal-relative when live, sandbox-relative when sandboxed. Pass and report the same absolute working directory everywhere. Connect environment-dependent roots through lazy path resolution; do not hard-code all global roots as HOME-relative strings. Ensure sandbox mode cannot inherit an external XDG root and escape isolation.

**Acceptance:** `.`, `..`, a child path, and absolute paths behave consistently across commands. Existing sandbox containment remains intact. Custom XDG and default-XDG discovery work in isolated fixtures without import-time path expansion.

### F06 — Merging shortcut targets loses genuine entrypoint paths and lookup identities

**Priority: Medium. Status: Both cases reproduced.**

A shortcut (symlink) is like a shortcut icon: two different shortcut paths can lead to the same physical skill. Inventory may merge their shared content, but resolution must retain how each agent reaches it.

**Case A — lost path:** Two Codex plugin paths inside one recursive root pointed to one target. Inventory retained two `entrypoint_paths`, but `_union_hits()` retained only one root hit. `why` returned only one candidate, contrary to the resolver's “one candidate per entrypoint” contract.

**Case B — wrong alias:** `.claude/skills/alternate` pointed to `.agents/skills/original`. The merged entry retained `alternate` from the first-discovered root. DSH, whose declared identity is directory-based, could not find `original` through its own root but could find `alternate` through the physical `original` path.

**Code anchors:** `core/discovery.py:535–593`; `core/resolver.py:139–182,217–264`.

**Proper solution:** Keep canonical content identity separate from per-entrypoint identity. Include the entrypoint path in root-hit deduplication. Derive directory/filename aliases from the relevant hit, not one canonical entry's first parse. Apply frontmatter naming and override matching under each agent's supported contract.

**Acceptance:** Both plugin entrypoints survive; different aliases are found under the appropriate agent rules; root declaration order does not change lookup behavior; genuine duplicate hits for the exact same path remain deduplicated. Canonical payloads should still be stored once per physical copy.

### F07 — Ordinary Markdown documentation is wrongly treated as a broken skill

**Priority: Medium. Status: Reproduced.**

A synthetic Codex plugin contained only `skills/README.md`, with ordinary documentation and no skill frontmatter. Doctor returned `malformed_frontmatter` at error severity and exited 1 under `--fail-on error`.

Discovery accepts every direct `.md` file under every root, even though standalone-file support varies by agent, provider, and version. The same broad logic is applied to symlinked Markdown. This is a discovery-policy problem, not merely a badly chosen filename.

**Code anchors:** `core/discovery.py:341–405`; `registry/loader.py` and root metadata; doctor frontmatter checks.

**Proper solution:** Declare supported entry formats per root/provider/version. Use those rules when recording which agent searches an entry. For standalone-file implementations that require qualifying metadata, distinguish incidental Markdown from a declared but invalid `SKILL.md`.

Do **not** fix this with a global `README*` blacklist or by downgrading every malformed skill. Those shortcuts can hide legitimate standalone skills and genuinely broken declared skills. Pi and OpenCode V2, for example, support standalone forms differently from conventional directory-only roots.

**Acceptance:** Ordinary Codex plugin documentation does not trip the error gate. Real malformed `SKILL.md` files still do. Legitimate standalone skills remain discoverable for supported agents, including symlinked files, with correct provenance.

### F08 — Explicit TUI launch can hang without an interactive terminal

**Priority: Medium. Status: Reproduced in a bounded subprocess.**

Bare launch checks both input and output interactivity. Explicit `skill-lens tui` checks only whether Textual is installed. With closed/non-interactive input and captured output, it did not exit within the two-second probe; the harness killed and waited for the child safely.

This verifies the reported blocking behavior. It does not imply that every possible non-interactive driver blocks forever.

**Code anchors:** `cli.py:148–160,219–245`.

**Proper solution:** Reject explicit interactive launch when either stream is non-interactive, with a plain message and exit 2. Keep intentional headless testing available through the internal runner; it is not a reason to launch an interactive CLI into a pipe.

**Acceptance:** Non-interactive explicit invocation exits promptly without starting the runner. Test each stream separately, both streams, missing Textual, and a normal interactive launch. Bare fallback behavior remains unchanged.

### F09 — Self-comparison is accepted by the CLI but rejected by captured services

**Priority: Low. Status: Reproduced interface inconsistency.**

`compare --agent claude --agent claude` returns an all-shared report and exit 0. `snapshot_compare(..., "claude", "claude")` raises `ValueError`.

A self-comparison is mathematically valid; calling it universally “meaningless” overstates the issue. The real defect is that the same operation has contradictory contracts, and an accidental duplicate selection is not handled consistently.

**Code anchors:** `cli.py:405–445`; `core/compare.py`; `core/snapshot.py:482`.

**Proper solution:** Use the already stricter captured-service contract for both surfaces: require two distinct known agents through shared validation, and translate the CLI error to exit 2. If the owner instead chooses to allow self-comparison, change both surfaces explicitly and document it; do not leave them inconsistent.

**Acceptance:** CLI, live core, captured core, and UI selection agree; duplicate input gives a clear message rather than a traceback; normal comparison behavior is unchanged.

### F10 — The local wheel is broken for TUI use; installed-wheel TUI verification is missing from CI

**Priority: Medium. Status: Reproduced local artifact defect and confirmed CI gap.**

`dist/skill_lens_cli-0.1.1-py3-none-any.whl` advertises `[tui]` and routes to `skill_lens.tui`, but contains no TUI package. Running its explicit TUI entry returned:

> Exit 3: Failed to start the terminal UI: No module named 'skill_lens.tui'

A fresh build from current source contains `tui/__init__.py`, `tui/app.py`, and `tui/session.py`, includes all ten agent TOMLs, and passed the clean-install smoke checks. **This is not a reproduced defect in the current build configuration.**

The local wheel's SHA-256 is different from the published PyPI 0.1.1 wheel. PyPI's current 0.1.1 metadata has no TUI extra. Therefore, the broken local artifact is **not evidence that the published 0.1.1 TUI is broken**; that release does not ship the new TUI.

CI's extra-install lane currently runs pinned-output and older phase suites, not the installed TUI lifecycle/session suites. Source-checkout tests and archive content checks cannot replace execution of the installed runner.

**Code anchors:** `.github/workflows/ci.yml:55–104`; `tests/test_tui_packaging.py`; `pyproject.toml:41–67`; local `dist/` artifact.

**Proper solution:** Quarantine or rebuild stale local artifacts in an authorized implementation session. Add checks that the declared TUI entry package exists and the installed runner actually opens, refreshes, handles a fault, and quits from outside the source checkout. Preserve a genuinely Textual-free base lane. Resolve source-guard paths from the installed package where appropriate, not from an assumed adjacent source folder.

**Acceptance:** A deliberately missing TUI module fails packaging verification; installed-package provenance is asserted; no source copy masks missing wheel files; both base and extra lanes behave correctly. Publish only fresh, verified artifacts with the planned release version—not a rebuilt development wheel uploaded again as 0.1.1.

### F11 — Several assurance tests do not prove what their names or reviewers claim

**Priority: Medium. Status: Reproduced gaps; no demonstrated product write.**

1. **Severity agreement test:** `tests/test_phase6_gate.py:177–190` checks a scan severity and the existence of doctor's docstring, not agreement. I replaced doctor frontmatter severities with `INFO` in memory; this test still passed.
2. **Coverage-floor guard:** `tests/test_phase5_gate.py:237–243` accepts a floor of 85 although the configured project gate is 90. An in-memory reduction from 90 to 85 survived the guard. This is a weak erosion guard, not proof that coverage.py currently fails to enforce 90.
3. **AST write-guard gaps:** Ordinary source snippets using `Path.replace()`, `Path.chmod()`, and `os.open(..., os.O_WRONLY | os.O_CREAT)` produced no guard violation. These snippets were parsed, **not executed**. They require no reflection or adversarial trickery.
4. **Preservation test's injected error is stale:** `tests/test_tui_read_only.py:743–746` uses request ID 999 with dummy parameters. Instrumentation showed `accept_view_error()` returned false and the controller remained non-failed. The test checks preservation through a rejected stale error, not an accepted unexpected-error lifecycle.
5. **Agents rendering is uncovered:** Independent coverage data lists the body of `render_agents` among missing lines. Add an actual human-readable rendering test/snapshot. Reviewer 2's statement that render.py is the lowest-covered module is incorrect; system.py is lower.

Reviewers 5 and 6 call their first list “three unfailable tests,” but their third example is explicitly a **good, previously repaired test**, not a third defective one. Their first two concerns are valid. The additional guard and preservation gaps above were independently checked.

**Proper solution:** Replace assurance-by-docstring with behavior tests, enforce at least the documented 90 floor, extend known write-operation checks, and assert that injected faults are actually accepted before claiming that path was covered. Add whole-tree preservation checks for normal quit, accepted report/capture failure, and cleanup failure. Keep the AST guard described as a limited source guard, not an execution sandbox.

**Acceptance:** Each targeted wrong behavior causes its guard to fail, and restoring correct behavior makes it pass. A clean AST control still passes. Test mutations stay in synthetic copies. The installed-wheel path is covered without reading real skill roots.

### F12 — Some tests attempt to inspect real system skill roots

**Priority: Medium. Status: Independently observed during the guarded full test run.**

The external guard recorded **82 existence/symlink checks across 16 test cases** against `/etc/codex/skills`. These include live-adapter and TUI tests that monkeypatch HOME/path helpers without setting the product sandbox.

`_absolute_roots_allowed()` intentionally permits system roots when there is no sandbox and the supplied home matches the effective home. Monkeypatching HOME alone therefore does not isolate absolute roots.

I prevented those checks from reaching the system root. I did not assert whether that location exists on this machine, nor read its contents. The defect matters even if it happens to be absent on CI.

**Code anchors:** `core/discovery.py:290–315`; `tests/test_phase4_gate.py` bare-home fixture; `tests/test_tui_app.py` fixtures.

**Proper solution:** Explicitly isolate absolute-root lookup in tests. For tests that must model a live/no-sandbox call, inject synthetic absolute-root mappings or replace that lookup boundary with a controlled fixture. Add a guard that fails on unexpected access to protected system roots. Do not add production logic that detects pytest and silently disables a legitimate live feature.

**Acceptance:** Tests are independent of whether real `/etc/codex/skills` exists. Dedicated synthetic tests still prove live system-root support. Default verification does not even inspect protected root existence/symlink state.

### F13 — Current-status documentation is stale, but historical records should not be rewritten

**Priority: Medium. Status: Confirmed.**

Current README/development statements still quote older test counts; the TUI design header says no TUI code exists; the changelog says nothing is implemented; AGENTS.md's architecture map omits snapshot, cancellation, presentation, and TUI modules. The current branch has the contracts, routing, controller, and placeholder through U2, not a completed browsing UI.

**Proper solution:** Update the current-status surfaces and add a clear release-versus-development distinction:

- Published 0.1.1: six line-oriented commands; no released TUI extra.
- Current development branch: six line-oriented commands plus an optional TUI entrypoint/skeleton through U2.
- U3–U9: remaining planned screens, polish, and 0.2 release work.

Describe coverage accurately, and preferably link a dated verification record or CI rather than maintain multiple supposedly current counters. Update AGENTS.md's map and read-before-changing pointers. Index or mark superseded root walkthroughs as historical rather than deleting evidence by default.

**Acceptance:** Current documents no longer say “nothing implemented,” imply a finished browsing UI, or imply that PyPI already offers this TUI. Historical milestone test counts remain unchanged and dated. README links retain absolute URLs suitable for PyPI.

### F14 — User-controlled agent names can crash error rendering

**Priority: Medium. Status: Reproduced in both relevant CLI paths.**

An unknown agent token `[/]` was passed to `why` and `compare`, including their JSON mode. Instead of the intended plain usage error and exit 2, both produced a Rich `MarkupError`, exit 1, and no useful output.

The error messages interpolate the user-supplied agent name into Rich markup without escaping it.

**Code anchors:** `cli.py:305–308` and the equivalent unknown-agent exception handler in `compare`.

**Proper solution:** Use literal error output (`markup=False`, no highlighting) or escape every dynamic part while keeping only fixed styling as markup. Apply the fix to sibling error paths, not only the reproduced command.

**Acceptance:** Agent tokens containing brackets and closing tags remain literal and produce exit 2 with no traceback. JSON stdout remains unpolluted by usage errors. Normal unknown-agent messages still list known agents.

**Important distinction:** Reviewer 8's cited headline print uses an internal enum and fixed style map; that specific print is **not** a demonstrated injection vulnerability. F14 is a different, actually user-controlled error path.

### F15 — A final-newline-only difference is detected but not explained by diff hunks

**Priority: Low. Status: Reproduced.**

Two valid skill documents differed only by the final newline. Their fingerprints differed, and the report correctly marked `SKILL.md` as modified and assigned different variants. However, its text `hunks` array was empty. `_lines()` strips the final newline, erasing the difference before hunk construction.

This is **not** a claim that the entire report says “identical.” It is a missing explanation for a real text difference.

**Code anchors:** `core/diff.py:145–185,238–243`.

**Proper solution:** Preserve end-of-file newline information and represent it in JSON and terminal output, normally with the conventional “No newline at end of file” marker. Keep newline normalization consistent with hashing. Marker lines must not incorrectly increase hunk old/new line counts or corrupt truncation budgets.

**Acceptance:** Adding/removing a final newline produces a visible explanation in live and captured diffs. CRLF-vs-LF remains equivalent as specified; lone carriage returns retain their existing semantics; hunk headers and truncation accounting remain valid.

### F16 — A nested winning copy can lose its explanation and cause rule

**Priority: Low. Status: Reproduced.**

A synthetic nested project copy received `COEXISTS` while the global copy was `SHADOWED`. The resolver searches only for an `ACTIVE` candidate when selecting the winner used to explain shadows. It therefore supplied no winner and emitted “Suppressed by a higher-priority copy,” citing the losing root's rule rather than the actual beating copy's rule.

**Code anchors:** `core/resolver.py:465–469,513–517,629–631`.

**Proper solution:** Determine the causal winner from the precedence decision itself, not by looking for a presentation label afterward. Do not arbitrarily choose any coexisting candidate; merged or ambiguous policies may have no causal winner.

**Acceptance:** A nested winner names the root and evidence that actually caused suppression. Ambiguous/merged cases do not invent a winner. Use a controlled registry fixture rather than preserve an obsolete vendor-specific precedence rule merely to keep this test.

## 4. Real risks and accepted limitations — not proven release-blocking bugs

### R01 — Snapshot memory is unbounded by content size

**Assessment: Valid resource risk; not a reproduced out-of-memory failure.**

Capture stores every file's bytes and refresh overlaps old and new generations. Skill count alone is a poor predictor: a small number of large assets can outweigh hundreds of text-only skills.

A new synthetic measurement used **eight skills with one 2 MiB binary asset each**, plus their small skill documents:

- Captured payload: **16,777,720 bytes**.
- Capture wall time without tracing: **41.60 ms** on warm local input.
- Two complete snapshots retained under tracing: **32.09 MiB** of Python heap.
- Peak traced heap during the two-capture experiment: **38.09 MiB**.

These are fixture-specific Python allocation measurements, not total process memory or a forecast for a real library. Existing U1 records also contain real `capture_session()` measurements on synthetic 600-plus-skill fixtures: approximately 682–991 ms, with roughly 9.75–9.98 MiB refresh peak. Reviewer extrapolations to thousands of skills should not be treated as measured results.

**Proper next step:** Add byte-heavy benchmarks and report total payload/largest file. Decide an explicit resource policy before changing capture: warning-only, a visible capture refusal with CLI fallback, or a redesigned snapshot representation. Any limit must be disclosed and preserve the prior valid generation.

**Do not implement the reviewers' suggested “lazy-read only when a view opens” as a quick fix.** Reading changed source files on selection breaks the frozen-generation/no-post-capture-disk-read contract. A metadata-only mode or lazy-content redesign needs an explicit contract amendment and honest completeness reporting. Avoid disk caches/databases and silent truncation.

### R02 — Textual private hooks make future dependency upgrades risky

**Assessment: Confirmed coupling; current supported-version failure not reproduced.**

The app relies on `_handle_exception`, `_exception`, `_exception_event`, and `_return_code`. `textual>=8.2.8` is open-ended, while the development lock currently resolves the tested version. Package installation does not inherit the project's lockfile.

Prefer a public exception hook if it can preserve fault containment and prompt shutdown. Otherwise centralize the private adapter, test its expected shape and behavior, and choose an explicit tested version range. Test minimum and latest-allowed versions, including rendering parity and fault/quit paths. An arbitrary upper bound is a policy decision, not evidence that a particular newer version is broken.

### R03 — The asyncio policy call is deprecated, not a current Python 3.14 crash

**Assessment: Reproduced compatibility warning; reviewers overstate the restoration defect.**

`asyncio.get_event_loop_policy()` warns on Python 3.14 and is scheduled for removal in Python 3.16. The current code catches the no-current-loop error. In an actual headless run with an existing non-running loop, Python 3.14 restored that exact loop successfully.

Therefore, statements that restoration is effectively dead or that a caller loop is always lost on Python 3.14 are false. There is still an avoidable deprecated dependency. Python 3.16 behavior was not executed.

Replace the deprecated lookup while preserving the ownership contract. Do not blindly use `get_running_loop()` alone—it misses an existing non-running caller loop. Do not remove cleanup or introduce an executor join that breaks prompt quit. Add warning-sensitive, targeted tests for no loop, a borrowed non-running loop, failures, and restoration. Avoid globally suppressing deprecations or globally treating unrelated dependency warnings as errors without review.

### R04 — Process-global sandbox state can leak across embedded invocations

**Assessment: Reproduced low-priority embedding/test-harness limitation, not a normal separate-process shell bug.**

In one Python process, a CLI call with `--sandbox` followed by a call without it reused the first sandbox. `_apply_sandbox(None)` does not clear the module global. Normal shell invocations start separate processes, so this does not demonstrate a user-facing leak between ordinary terminal commands.

If repeated embedded calls become supported, use explicit per-invocation context and guaranteed restoration. Do not “fix” it by clearing sandbox state indiscriminately in a way that breaks existing isolated test fixtures. Add restoration tests before changing ownership.

### Other limitations to keep explicit

- **TUI browsing is intentionally unfinished.** The U2 placeholder is correct for its milestone. Missing U3–U9 screens are planned work, not bugs to fold into this repair campaign.
- **OMP namespaced coexistence is deliberately under-modelled.** Do not change it to ordinary shadow or merge merely to remove ambiguity; those claims would be less accurate. The current wording “policy is undocumented” is also too broad: the limitation is in Skill Lens's representation, not necessarily vendor documentation.
- **Frozen browsing is currently tested behavior, not an impermeable import boundary.** A live helper such as `build_scan_report()` can still perform filesystem reads. New screens must use captured services and continue no-disk-read tests. No current selection-path disk-read defect was reproduced here.
- **Case-sensitive filesystem tests may legitimately skip on a case-insensitive volume.** Linux and macOS CI cover different filesystem conditions. This is not evidence of an APFS bug.
- **`--fail-on info` is intentionally very strict and explained in help.** It is not an error-policy defect.
- **Raw validation logs are retained evidence.** Their maintenance cost is a reasonable discussion, but automatically deleting or ignoring them would remove part of the project's audit record. No runtime bug or urgent repository-size problem was established.
- **The distribution/command naming difference is deliberate.** Installation uses `skill-lens-cli`; the command is `skill-lens`; the import package is `skill_lens`. The README already explains it.
- **Pre-alpha classification, missing `__all__` pins, redundant exception tuples, and test-function reuse are lower-priority maintenance suggestions**, not evidence of a broken release. Reusing a test with a changed signature would normally fail visibly, not silently.

## 5. Judgment of the nine reviews

Agreement among reviews is not independent proof. Several repeat the same claims and severity labels. The table below records what survives independent checking.

| Reviewer | Findings retained | Corrections / findings not accepted as stated |
|---|---|---|
| **1** | Documentation drift; relative `--cwd` defect; source-evidence audit; full-byte memory risk; Textual coupling; asyncio warning | GitHub is not behind the assessed local commit: remote main matches and both version tags exist. The placeholder and process weight are design/progress observations. A full live-home benchmark was not independently repeated; synthetic capture benchmarks already exist |
| **2** | Broken local TUI wheel; documentation drift; missing agents rendering coverage; explicit non-interactive TUI blocking | Fresh current-source wheel works. The stale wheel is not the published PyPI artifact. `render.py` is not the lowest-covered module. Redundant exception tuple is informational only |
| **3** | Asyncio deprecation; stale contributor status; future snapshot-boundary and coverage watchpoints | Python 3.14 does restore an existing non-running loop; the claimed dead restoration branch is overstated. No current captured-view read was reproduced. 94.30% is not branch-only coverage |
| **4** | Structural strengths; U2-versus-U3 status; memory overlap; dependency-upgrade risk; intentional release-version timing | “Production Grade A+” and complete assurance are not supported by the reproduced correctness defects. Killing 73 selected mutations does not prove all possible writes are prohibited. No separate case-insensitive filesystem defect was demonstrated |
| **5** | Severity agreement guard gap; weak coverage-floor guard; real-system-root test exposure; self-comparison inconsistency; ordinary Markdown false alarms; nested-winner explanation loss; docs/package/CI gaps; private-API risk | Only two defective tests are in its “three tests” list—the third is a repaired positive example. Same-agent comparison is not inherently meaningless. Memory estimates/live figures were not all independently reproduced. Lazy view-time file reads would violate the capture contract. Asyncio loop-loss claim is overstated |
| **6** | Corroborated source/test/CI observations from Reviewer 5; specific root-hit merge concern, now reproduced; stale documentation | Its own method did not rerun the full gate. Broad “finished and trustworthy engine” conclusion is too strong. Same corrections apply to the three-tests wording, Python 3.14 loop claim, and suggested lazy-read memory fix |
| **7** | Global sandbox-state risk, now reproduced for same-process invocations; current-doc drift; coverage gaps; intentional placeholder; platform-aware test skip | Committed validation evidence and pre-alpha metadata are optional maintenance choices, not runtime defects. AST checks are not a complete capability barrier. Its large-live-home performance concern was unmeasured in that review |
| **8** | Useful documentation-index/maintenance suggestions; platform-testing limitations; intentional skeleton status | Its cited enum headline print is not a user-input injection bug. The package name difference is explained already. “No defects found” describes that review's scope, not overall correctness; real CLI markup failure is separately reproduced in F14 |
| **9** | Stale AGENTS.md map; intentionally limited OMP namespacing; event-loop compatibility seam; process-overhead watchpoint | The 0.2 release direction is already specified, not undecided between 0.1.2 and 0.2.0. Documentation has more drift than only AGENTS.md. `--fail-on info` is intentional. Passing gates and a published 0.1.1 do not establish development-TUI release readiness |

**Additional independent findings:** Incomplete asset fingerprints, actual scan/doctor gate disagreement, current-vendor rule/configuration mismatches, alias identity contamination, direct write-guard omissions, stale-only fault injection, literal-error rendering failures, and final-newline diff omissions were verified beyond the reviewers' general assurances.

## 6. Implementation handoff plan

**This section is a plan, not completed work. No fix described below was applied.** It is designed to be handed to a new session without needing this conversation or temporary scratch artifacts.

### Scope and guardrails

- Work only in the Skill Lens repository and dedicated synthetic test/build directories.
- Never modify, repair, execute, move, or delete user skills.
- Do not use live HOME or real system skills as test fixtures. Sandbox environment-dependent roots too.
- Do not call agent sessions, model providers, telemetry, or network APIs from the product.
- Keep JSON/dataclass contracts first; rendering stays presentation-only.
- Do not build U3–U9, add databases/caches, refactor unrelated code, or delete audit evidence as part of these repairs.
- Do not commit, push, publish, or replace old artifacts without the owner's applicable authorization.
- Read the relevant historical findings before altering their areas. This assessment did not run or create an additional project planning loop.

### Division of labor

| Work | Next implementation agent | Owner decision needed |
|---|---|---|
| Isolated reproductions, local correctness fixes, regression tests, verification | Executes | Normally none beyond implementation authorization |
| Choose/version the current-vendor support contract, especially OpenCode V1/V2 and Antigravity surfaces | Presents bounded options and implements the selected contract | **Approve scope if the current specification must change** |
| Snapshot memory limit/mode and Textual support range | Measures, recommends, tests | **Approve behavior/dependency policy before imposing it** |
| Publishing/tagging and removal/replacement of stale artifacts | Verifies readiness; executes only when authorized | **Explicit release/artifact authorization** |

No coding work is required from the owner. Decisions must not be guessed just because the repair agent can implement them.

### Stage A — Make verification trustworthy first

**Addresses:** F11, F12; adds failing reproductions for the high-priority findings.

1. Isolate absolute system roots in every default fixture, including live/no-sandbox adapter tests.
2. Replace the severity docstring assertion with comparison of real classified conditions and command exit results.
3. Tighten the coverage-floor erosion test to the documented minimum of 90.
4. Extend the AST guard for the direct write methods/flags described in F11, with clean-control and detected-mutation cases.
5. Make target-preservation tests cover a genuinely accepted fault and cleanup failure; assert the intended controller path was entered.

**Done when:** The targeted mutations fail, clean controls pass, and an access guard records no unexpected protected system-root inspection. Do not weaken guards to obtain green tests.

### Stage B — Repair incomplete-content and health-gate answers

**Addresses:** F03, F04.

1. Introduce explicit traversal/read completeness without treating skipped content as a complete hash.
2. Propagate completeness through discovery, inventory, diagnostic findings, comparison, diff, and capture.
3. Share classification of common health conditions between scan and doctor; retain doctor-only informational checks separately.
4. Preserve old complete snapshots on a failed capture and show a truthful error reason.

**Done when:** Denied nested assets cannot yield verified equality; broken shortcuts cannot pass the error gate; decoding errors are distinguished from permission errors; live and captured services agree.

### Stage C — Repair paths and entrypoint discovery

**Addresses:** F05, F06, F07.

1. Normalize CLI working-directory input at one boundary, preserving terminal-relative live behavior and sandbox-relative test behavior.
2. Wire XDG/global config roots lazily and keep them contained under sandbox policy.
3. Preserve one root hit per actual entrypoint path and agent/root context.
4. Preserve per-entrypoint aliases independently of canonical content storage.
5. Add root/version-specific entry-format support, including symlinked standalone files.

**Done when:** Default and `--cwd .` find the same project; custom XDG works without escaping a sandbox; both plugin paths survive; alias/root order does not affect lookup; ordinary documentation is not promoted into broken skills.

### Stage D — Align supported agent rules and configuration with evidence

**Addresses:** F01, F02; depends on the discovery model from Stage C.

1. Create a concise evidence table covering supported version/surface, identity, default roots, recursion, collision behavior, and disable/permission controls.
2. Resolve explicit version/surface scope with the owner where the specification must change. Especially avoid combining OpenCode V1 and V2 rules.
3. Implement the proven root/name/precedence corrections for that chosen scope.
4. Add version-specific, read-only configuration decoding and capture-time configuration resolution.
5. Distinguish portability validity from actual per-agent loadability and distinguish invocation/advertisement/permission states.
6. Update fixtures/goldens only after reviewing the changed answer and its primary evidence.

**Done when:** Each accepted mismatch has an evidence-linked fixture; configuration-disabled skills are not falsely active; unknown/unmodelled behavior is disclosed; snapshots remain frozen after capture. Do not expand this into support for every possible plugin or remote catalog.

### Stage E — Repair command boundaries and compatibility

**Addresses:** F08, F09, F14, R03.

1. Fail fast for explicit non-interactive TUI launch, retaining the internal headless testing interface.
2. Share validation for distinct comparison agents and map errors to exit 2.
3. Emit user-containing error messages literally across sibling handlers.
4. Replace the deprecated event-loop lookup without losing non-running borrowed-loop restoration or prompt worker shutdown.

**Done when:** Bounded non-TTY tests exit promptly; unusual agent tokens cannot crash rendering; CLI/captured compare validation agrees; targeted Python 3.14 warning tests are clean; ordinary TUI open/refresh/fault/quit behavior remains intact.

### Stage F — Repair missing explanations

**Addresses:** F15, F16; adds the agents render test from F11.

1. Represent final-newline differences without corrupting hunk or truncation counts.
2. Carry the causal precedence winner into explanations independent of presentation states.
3. Pin human-readable `agents` output and unusual agent labels with an actual rendering test.

**Done when:** Hash-different newline cases have a visible explanation; nested suppression names the correct rule; ambiguous policies still do not invent winners; reviewed terminal snapshots remain stable except for intentional fixes.

### Stage G — Verify the artifact and dependency boundary

**Addresses:** F10, R02.

1. Build fresh wheel/sdist in an isolated output directory.
2. Assert TUI package content as well as registry content.
3. Install base and extra wheels into separate clean environments and run outside source.
4. Execute installed TUI lifecycle/session checks, including faults and shutdown, while preserving the source provenance assertion.
5. Test the minimum and selected latest-allowed Textual versions and rendering parity. Centralize any necessary private adapter.
6. Replace/quarantine stale local artifacts only with authorization. Do not publish current development work under an already released version.

**Done when:** Removing a required wheel module breaks the packaging gate; base has no Textual; extra opens/quits correctly; source tests do not mask package omissions; compatibility policy is explicit.

### Stage H — Reconcile current documentation and measure remaining resource risk

**Addresses:** F13, R01; documents R04 and accepted limitations.

1. Update README, DEVELOPMENT, CHANGELOG current/unreleased sections, TUI status header, and AGENTS.md map/pointers.
2. Preserve dated historical measurements and evidence files.
3. Run byte-heavy capture/refresh benchmarks in synthetic fixtures, recording payload, largest file, retained heap, and peak heap with the tracing method stated.
4. Obtain approval before changing snapshot resource behavior. If no memory policy change is approved, document the limitation rather than pretending it is solved.
5. Leave U3–U9 and 0.2 publishing as a separate feature/release campaign.

**Done when:** Release and development status are unambiguous, metrics are accurately labelled, and resource decisions are explicit. Documentation must not claim that a warning or a benchmark alone bounds memory.

### Final verification gate

From an isolated test environment, after installing the project's locked development dependencies:

```bash
pytest --cov=skill_lens
mypy
ruff check .
ruff format --check .
```

Also require:

- Targeted failing-before/fixed-after regressions for every implemented finding.
- Guard mutations in disposable copies, with control/failure/restore evidence.
- Reviewed snapshot/golden diffs; never regenerate to hide an unexplained failure.
- Base and `[tui]` installed-wheel checks from outside source, with fake HOME and protected system-root isolation.
- Supported Python/macOS/Linux CI results, without claiming unexecuted lanes passed.
- Before/after preservation of synthetic target inventory, bytes, permissions, and shortcut targets.
- A short final report linking each implemented finding ID to its change and actual test result, with unresolved owner decisions listed plainly.

## 7. Evidence and reproducibility

### Local evidence retained for this assessment

These files are temporary audit artifacts, **not dependencies of the implementation plan**. Hermes scratch storage may later prune them.

Under `/Users/corvette/.hermes/cache/scratch/skill-lens-final-assessment/`:

- `gate.xml`, `coverage.json`: independent test totals and coverage measurements.
- `system-root-attempts.json`: intercepted system-root existence/symlink attempts.
- `probe_findings.py`, `probe-results.json`: working-directory, gate, root-hit, alias, nested-winner, documentation-file, comparison, XDG, permission, and weak-guard reproductions.
- `additional_probes.py`, `additional-results.json`: missing default roots, alias contamination, direct AST omissions, rejected preservation-test error, byte-heavy snapshot measurement, and non-interactive launch probe.
- `final_behavior_probes.py`, `final-behavior-results.json`: Qoder priority, Pi identity, current disable controls, CLI markup failures, and final-newline diff reproduction.
- `wheel_smoke.py`, `wheel-smoke-{base,extra,py314}-results.json`: artifact provenance, command smoke tests, headless runner, and borrowed-loop restoration.
- `original_inventory.json`: original content hashes and source-tree metadata for preservation comparison.
- `fresh-build/`: newly built artifacts, outside the repository. The repository's original `dist/` files were not replaced.

The high-priority behavioral recipes are described directly in F01–F07, so the next session can rebuild them under `tmp_path` rather than depend on this scratch directory.

### Primary sources consulted

Retrieved during this assessment. Online documents can change; pin the supported version and evidence date when implementing.

| Subject | Primary source |
|---|---|
| Claude names, description fallback, overrides, scopes | [Claude Code skills](https://code.claude.com/docs/en/skills) and [settings files/precedence](https://code.claude.com/docs/en/settings) |
| Codex skill roots and per-path disabling | [Build skills](https://developers.openai.com/codex/skills) — redirects to current ChatGPT/Codex documentation |
| Pi names, recursion, collisions, standalone qualification | [Pi skills documentation](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/skills.md) and [skill loader source](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/src/core/skills.ts) |
| Qoder user-over-project priority | [Qoder CLI Skills](https://docs.qoder.com/cli/Skills) |
| Antigravity CLI versus IDE/2.0 roots | [Antigravity Agent skills](https://antigravity.google/docs/skills) |
| OMP managed root, provider-specific validity, namespacing | [Oh My Pi skills](https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md) |
| OpenCode original documented discovery/permissions | [OpenCode Agent Skills](https://opencode.ai/docs/skills) |
| OpenCode V2 IDs, discovery, precedence, permissions | [OpenCode V2 Skills](https://opencode.ai/v2/docs/skills/) |
| DSH documented roots/priority | [DeepSeek Harness skills](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md) |
| Windsurf/Cascade legacy and current locations | [Cascade Skills](https://docs.devin.ai/desktop/cascade/skills) — current documentation distinguishes preferred and legacy locations |
| asyncio policy deprecation | [Python 3.14 event-loop policies](https://docs.python.org/3.14/library/asyncio-policy.html) and local interpreter probes |
| Published package version, extras, artifact hashes | [PyPI package metadata](https://pypi.org/pypi/skill-lens-cli/json) |

Some old registry URLs were missing, redirected, or insufficiently specific. A broken URL alone does not prove a precedence rule false. In particular, no replacement Grok rule is asserted here without adequate primary evidence. Likewise, current Windsurf/Devin documentation is a reason to version and revisit that support contract, not permission to silently merge different products and their settings.

## 8. Closing assessment

**Keep the architecture, read-only product boundary, JSON-first models, evidence discipline, and reviewed output tests. Repair the places where those promises are not yet reflected in behavior.**

The next agent should not blindly implement every recommendation from all nine reviews. Use this report's reproduced cases, explicit limitations, and staged acceptance conditions. Prioritize trustworthy discovery, complete content comparisons, correct health gating, and supported-version evidence before adding the remaining browsing screens.

**No fixes were applied during this assessment. The only permanent deliverable created outside scratch verification storage is this Desktop Markdown report.**


## Execution record — Stages A/B accepted, 12 October 2026

This append-only record does not alter the supplied operative plan or its frozen reference.

- Implemented F03/F04, F12, and F11 assurance items 1–4. F11 agents rendering remains assigned to Stage F.
- Incomplete traversal/read cannot issue a verified hash, certify shared content, or replace the prior complete capture. Scan and doctor classify common health causes consistently. Invalid UTF-8 is distinct from denied, disappeared, and I/O input.
- Document parse validity stays separate from content completeness. `why` preserves evidence-backed agent resolution and reports incomplete content as an observed note; no asset failure is attributed to a documented frontmatter rule. Comparison retains existing relation values and explicitly explains unverifiable rows rather than promising known text differences.
- Default fixtures isolate system roots; strict test guards reject unintended protected-root probes. Target-preservation tests enter accepted fault and cleanup-failure paths. AST write controls and the 90% coverage erosion guard are discriminating.
- Deliberate output changes: scan JSON adds `traversal_complete`, `error_reason`, and `health_status`; the scan table gains Status. Broken skills now trip opt-in scan error thresholds. Mid-run diff read failures give literal stderr and exit 2, with JSON stdout unpolluted. Only the reviewed scan snapshot changed.
- Coordinator verification: **825 passed, 1 skipped**, **93.31% combined coverage with branch measurement**, strict mypy clean on 35 files, Ruff lint and format checks clean. This is local macOS/Python 3.11 evidence; unexecuted CI lanes are not claimed.
- Independent acceptance: MiniMax xHigh pass on the approved correction tree; Space Bunny Max pass after the final comparison-note follow-up. Coordinator checked the intervening three-file delta: comparison notes/tests and model docstring only, unchanged JSON keys/enums and safety contracts. MiniMax's unaffected safety/shape verdict was retained.
- Requested and T3-configured reviewer options agree. Actual serving effort remains unverified where provider introspection does not expose it. Space Bunny family identity remains unverified under the user's explicit selected-pair authorization. Reviewer restraint is instruction-based; status/SHA-256 checks confirmed no repository changes during reviews.
- After two review rounds failed to converge, the owner explicitly approved focused corrections and targeted follow-up. All original objections and the subsequent false comparison-note claim were resolved; no acceptance blocker is deferred.
- Receipt: expected first batch 3 child tasks (one implementer plus two critics); actual **14 launches** including corrections, focused review rounds, and one internal-error implementer run/recovery. All 14 terminal with no pending child runs at acceptance. Approximately 5h28m elapsed from first dispatch to acceptance, including asynchronous turnaround and the owner-decision interval; active compute time and provider token usage unavailable. No measured token-savings claim.
- Non-blocking duplicate test calls, fixture-directory overhead, redundant defenses, and pre-existing cleanup ordering are retained suggestions. Current-version registry/configuration, paths/entry identities, packaging, reporting, and resource risks remain assigned to C–H. U3–U9, publishing, dependency policy, and old artifact replacement remain outside this batch.

Durable evidence: [Stage A/B validation files](../validation/assessment-repairs/ab/). This includes coordinator gate logs, actual disposable control/mutant/restore receipts, terminal task receipts, and final reviewer reports. Tests used synthetic HOME/targets only. Raw reviewer assertions about enforced read-only modes are not coordinator claims; T3 caller configuration and fingerprint evidence determine the recorded protection above.


## Execution record — Stage C accepted, 13 October 2026

This append-only execution record does not alter the supplied plan or frozen reference.

- F05 working-directory/XDG behavior and F06 hit/alias retention are repaired and tested through real consumers and frozen services. Root order is checked for both different entrypoint aliases and the same physical path with distinct ranks.
- F07 discovery formats are explicit and source-linked. Native directory-only forms no longer treat flat documentation as skills; DSH supports documented flat files; unverified retained roots preserve historical inventory compatibility. Full per-agent validity/loadability and selected version/surface alignment remain Stage D. OpenCode V2 is the chosen profile, V1 unsupported; the currently absent `.claude` roots are not claimed implemented.
- The coordinator independently verified **860 passed, 1 skipped, 93.38% combined coverage**, strict mypy on 35 package files, Ruff lint/format clean. The final raw declaration guard is package-bound and has actual-package versus decoy positive/negative proof.
- MiniMax xHigh accepted the product correction; Space Bunny Max accepted the final test-only guard correction and retained its prior product concessions. Fingerprints show unchanged MiniMax scope. All 17 Stage C child tasks are terminal with no pending runs. The owner explicitly approved focused corrections after two non-converged council rounds.
- Unreported loader drift and inaccurate source/combined-mutation claims were detected and corrected before acceptance. Final loader differs from the reviewed pre-correction version only by its fallback comment. No snapshot/golden changes were required. Actual token/compute use unavailable; no savings claim.
- Durable evidence and remaining boundaries: [Stage C acceptance](../validation/assessment-repairs/c/acceptance.md). Stage D–H, U3–U9 and release/push work remain outside this acceptance.


## Execution record — Stage D checkpoint resumed, 15 October 2026

This append-only execution record changes neither the operative contract nor its frozen reference.

- The owner explicitly resumed the saved Stage D checkpoint. The accepted base remains `249057601637d90b436e9313e8532ce44ed5f57c`; all 396 saved repository file fingerprints matched at resume. Stage D remains unaccepted until final verification and independent review. Later stages and release/push work remain excluded.
- Session roster selected by the owner: sole implementer Antigravity `gemini-3.8-flash-high`; Reviewer 1/council member MCode `m:minimax:MiniMax-M3.1-Flash-Preview:v:thinking`, `thinkingEffort=xhigh`; Reviewer 2/council member OpenCode `opencode/muse-spark-1.3-contributor-free`, `variant=xhigh`. The owner explicitly approved xHigh because the live Muse catalog does not offer Max. Muse's underlying family/serving identity is unverified; the named pair is the owner's explicit session selection. Historical Space Bunny receipts remain historical evidence.
- Coordinator Full access/default and root-checkout binding were read back through T3. Workers use Full access; reviewers receive the council's verbatim report-only guard, plan interaction mode, and before/after fingerprint checks. This restraint is instruction-based, not enforced write isolation.
- Fresh resume baseline: 912 passed, one filesystem skip, 90.91% combined coverage; mypy 36 files and Ruff lint/format clean. Independent reproduction found remaining Claude live/captured identity drift, incomplete OpenCode confidence disclosure, raw config values in diagnostics, and doctor treating unknown root support as rejection. One Gemini correction batch addressed these; coordinator gates then passed 916 tests, one skip, 91.10% coverage.
- A further boundary reproduction found cyclic Codex config paths escaping as RuntimeError and truncation-warning formatting probing the filesystem during frozen navigation. A second Gemini batch addressed those paths and preserved custom snapshot fallback. Both implementer tasks are completed with no pending child runs. Worker reports are evidence, not acceptance; final coordinator gates and council round two follow.
- Only one broad council wave occurred before this resume. Round two will include the original briefs, previous findings/dispositions, resumed corrections, complete current product/test diff, and current coordinator evidence. The existing two-round escalation rule remains in force. No third broad wave is authorized by this record.

- At the owner's subsequent explicit instruction, work stopped after coordinator review and before sending to council. Three resumed Gemini correction tasks are terminal with no pending child runs; no reviewer was launched in this session. Final direct gates: **922 passed, one skip, 90.50% combined coverage**, strict mypy 36 files, Ruff lint/format clean. Thirteen disposable production mutations have clean/mutant/restored exits 0/1/0. The third batch fixed exact-depth leaf omissions in OpenCode/Pi/standard recursive walks without increasing their caps.
- Status at stop: coordinator-reviewed and ready for independent round two; **unaccepted and uncommitted**. No Stage E, commit, push, release, dependency policy or resource policy work started. Receipt: 3 resumed child launches for confirmed correction batches; elapsed active compute time and billed tokens unavailable. Historical task counts and results are retained, not replaced by these session counts.
- Durable resume checkpoint: `/Users/corvette/.t3/userdata/skill-lens-repair-checkpoints/2026-10-15-stage-d-reviewed-stop/resume.md`. The user must explicitly resume before council dispatch. Compare saved status and file fingerprints first; changed files invalidate affected verification evidence.

## Execution record — Stage D council round two complete, 15 October 2026

The owner explicitly resumed the reviewed checkpoint and requested council round two. This append-only record does not alter the operative contract or frozen reference.

- All 396 saved repository fingerprints and Git status matched the reviewed checkpoint. Fresh coordinator checks passed: 922 tests, one case-insensitive-filesystem skip, 90.50% combined coverage; mypy clean on 36 files; Ruff lint/format clean on 130 files. The 13 coordinator mutation source hashes still match, with recorded clean/mutant/restored exits 0/1/0.
- Reviewer 1: MCode MiniMax M3.1 Flash thinking, `thinkingEffort=xhigh`, **pass**, no blockers. Reviewer 2: OpenCode Muse Spark 1.3 Free, owner-approved `variant=xhigh`, **pass**, no blockers. T3 readbacks corroborate configured targets/options and Full access/plan; actual serving identity/effort remain unverified. The owner-selected named pair is retained without claiming verified family diversity.
- Both fresh child tasks completed with no pending child runs. All 396 file fingerprints and Git status remained unchanged through both reviews. Only administrative evidence and this execution record were added afterward. No correction batch or third broad council wave was launched.
- Coordinator inspected the reported non-blocking suggestions; no new in-scope blocker remains from this round. The requested independent review is complete and converged. Stage D remains unaccepted and uncommitted pending the separate acceptance/delivery step. No later phase, commit/push, release, or policy work started.
- Receipt: expected two review launches; actual two, zero failures/retries or new implementer tasks. Task/run identities, full briefs, configured modes/options, gate logs and fingerprints are retained in `/Users/corvette/.t3/userdata/skill-lens-repair-checkpoints/2026-10-15-stage-d-council-r2/`. Exact elapsed seconds are recorded in its task ledger; active compute time and billed tokens are unavailable.
- Combined dispositions and reviewer limits: [council round-two adjudication](../validation/assessment-repairs/d/coordinator/council-r2-adjudication.md). No snapshot/golden regeneration or product/test edit was made by this review session.


## Execution record — Stage D accepted, 15 October 2026

The owner authorized the next described steps with “go ahead”: accept/commit Stage D, then begin Stage E. This record does not alter the frozen contract. Coordinator accepted the exact reviewed product/test tree after verifying all gate/review evidence, allowed-file accounting and terminal task receipts. Both round-two critics passed with no blockers; 922 tests/one skip, 90.50% coverage, mypy and Ruff clean; 13 source-matched mutation controls. Full acceptance, limits and durable logs: [Stage D acceptance](../validation/assessment-repairs/d/acceptance.md). Pre-existing `.path` remains excluded. Local commit is authorized; push/release remain excluded.

## Execution record — Stage E started, 15 October 2026

Owner authorized Stage E after Stage D acceptance and local commit `f0cf52684dfcc638a2f5a49509a5be80faddc951`. Frozen Section 6 Stage E (F08/F09/F14/R03) remains the operative plan; no new planning loop or contract amendment. Risk: High because validation/exit behavior and event-loop ownership affect CLI compatibility. Expected tasks: one Gemini implementer plus two fresh independent implementation critics, before corrections. Same-session roster: Antigravity `gemini-3.8-flash-high`; MCode MiniMax M3.1 Flash thinking/xHigh; OpenCode Muse Spark 1.3 Free/xHigh. Named-pair identity limits remain disclosed.

Coordinator independently reproduced the piped explicit-TUI timeout, duplicate-agent CLI success, unknown-agent Rich markup failures and Python 3.14 policy deprecation warning. Same-session Stage D source/test gates serve as the unchanged Stage E baseline. `.path` remains preserved and excluded. Exact reproduction outputs, baseline fingerprints and allowed-file implementation brief are in `/Users/corvette/.t3/userdata/skill-lens-repair-checkpoints/2026-10-15-stage-e-work/`. Gemini writes only Stage E product/tests; coordinator verifies, reviews, adjudicates and commits. Stages F–H, U3–U9, push/release and dependency/resource policies remain outside this batch.


Stage E coordinator verification before council: initial implementation and one proof-only correction completed with no pending children. Correction repaired ambient-HOME use and two loop assertions whose wrong production mutations survived; product behavior did not change. Current direct gates: 967 passed/one skip,90.53% coverage, mypy on 36 files/Ruff on 134 files clean;37 targeted Python 3.14 passed. Thirteen independently executed production mutations have 15 clean/mutant/restored0/1/0 interpreter executions, including both repaired guards on 3.11 and3.14. Two fresh critics review Stage E round one with selected MiniMax/Muse xHigh roster. [Current evidence](../validation/assessment-repairs/e/coordinator/first-council-evidence.md). Expected initial3 tasks became4 because the coordinator reproduced test-proof gaps; no prior Stage E council wave.


## Execution record — Stage E accepted, 15 October 2026

Coordinator accepted F08/F09/F14/R03 after complete scoped diff/consumer review, direct final gates and converged independent first council wave. Current proof:967 passed/one skip,90.53% combined coverage,mypy on 36 files/Ruff on 134 files clean;37 targeted Python 3.14;13 distinct production mutations/15 interpreter executions all0/1/0. Three pre-council test-proof gaps were fixed by Gemini; no product change followed verified review. Both critics passed, all 506 fingerprints/status unchanged during reviews. Expected three tasks;actual five:initial implementation, proof correction, provider-failed MiniMax attempt, Muse review, successful same-model MiniMax recovery. All five terminal/no pending. Configured targets/options/modes verified; upstream identity/effort remain unverified. Exact receipts, elapsed wall time, limits and non-blocking dispositions: [Stage E acceptance](../validation/assessment-repairs/e/acceptance.md). Active compute/tokens unavailable. `.path` preserved/excluded. Local commit authorized; no push/release or Stage F started.


## Execution record — Stage F started, 15 October 2026

Owner explicitly authorized “start Stage F” with coordinator Sol, sole implementer Antigravity Gemini 3.8 Flash High, and independent MiniMax M3.1 Flash thinking through mcode plus Muse Spark 1.3 Free through OpenCode. Owner selected xHigh for both critics and accepted the named pair with upstream family identity disclosed as unverified. Live catalog confirms configured targets are available; historical deferred-mcode text does not override this selection. Frozen Section 6 Stage F (F15/F16/F11 agents rendering) @ `fe6f89bc55eb3f4f04187567b968dd96ae9c86c1` remains operative; no new planning cycle or behavior amendment.

Base: accepted Stage E `3762f1059fe34e79a0c1e93fc5032600bb648b78`. Root checkout `main`, no bound worktree, Full access verified. Pre-existing untracked `.path` preserved/excluded. Direct baseline: 967 passed/one filesystem skip, 90.53% coverage; mypy on 36 files and Ruff lint/format clean (137 files). Coordinator independently reproduced missing final-newline hunks and nested-winner suppression citing the losing root; synthetic fixtures only. Risk High because diff budgets/data contract and precedence explanation are load-bearing. Expected launches: three (one implementer, two fresh independent critics), before corrections. Exact scope, commands, hashes and baseline logs: `/Users/corvette/.t3/userdata/skill-lens-repair-checkpoints/2026-10-15-stage-f-work/`. Gemini writes product/tests; coordinator verifies, adjudicates and commits. Stage G/H, U3–U9, push/release, dependencies and resource policy remain excluded.


## Execution record — Stage F accepted, 15 October 2026

Coordinator accepted F15/F16/F11 agents rendering after complete scoped diff/consumer inspection, direct final gates and a converged independent first council wave. Proof: 989 passed/one filesystem skip,91.11% combined coverage,mypy36/Ruff138 clean;14 source-matched production mutations all clean/mutant/restored0/1/0;4235 generated budget cases and true nested COEXISTS-winner frozen adapter proof. Gemini corrected pre-council test-proof/isolation gaps; no product/test changes followed final gates or review. Both selected xHigh critics passed/no blockers;515 hashes and Git status unchanged through review. MiniMax final verdict recovered from its original session artifact after task summary omitted it; full report/limits retained. Configured targets/options/full-access/plan verified; upstream identity/family diversity unverified. Expected three launches;actual four due to one proof correction;all terminal/no pending. Exact wall time, receipts, original briefs, logs and non-blocking dispositions: [Stage F acceptance](../validation/assessment-repairs/f/acceptance.md). Active compute/billed tokens unavailable. `.path` preserved/excluded. Coordinator local commit authorized;no push/release or Stage G started.


## Execution record — Stage F delivered and Stage G started, 15 October 2026

Owner instructed “if all good comm and push and start stage G”. Coordinator verified accepted Stage F and pushed main, including already accepted D/E/F local commits. Local HEAD, origin/main and git ls-remote all match `491f9ce5902f98a7dd687c03418c308dcb88bcfd`. This later delivery authorization supersedes the earlier no-push boundary for those accepted commits; it does not authorize publication/tagging, old dist replacement or later phase work.

Stage G (F10/R02) now follows frozen Section 6 @ `fe6f89bc55eb3f4f04187567b968dd96ae9c86c1`. Same-session roster/settings retained: sole Antigravity Gemini 3.8 Flash High implementer, independent MiniMax M3.1 Flash/mcode thinking xHigh and Muse Spark 1.3 Free/OpenCode variant xHigh. Configured catalog targets available; upstream served/family identity remains unverified as disclosed for the selected pair. Risk High: installed package completeness, fault containment and dependency compatibility. Expected initial three tasks (implementer plus two critics), before corrections. Root main/Full access verified; pre-existing .path preserved/excluded.

Baseline reuses same-session direct Stage F gates (989 passed/one skip,91.11%,mypy36/Ruff138) after exact source/test/config fingerprints and unchanged environment were checked. Old dist wheel has10registry TOMLs but no TUI modules; fresh isolated wheel/sdist contain TUI, so current build configuration is not called broken. The existing registry-only gate misses a removed TUI app module. Live PyPI latest stable Textual8.2.8 currently equals declared minimum; endpoint overlap must be recorded honestly, no arbitrary dependency cap. Original dist artifacts are fingerprinted/preserved, not replaced. Receipts and bounded worker brief: `/Users/corvette/.t3/userdata/skill-lens-repair-checkpoints/2026-10-15-stage-g-work/`. Coordinator owns verification/review/commit; Stage H/U3–U9, release, dependency/resource-policy changes and old artifact replacement remain excluded.

## Execution record — Stage G accepted, 15 October 2026

Coordinator accepted F10/R02 after complete eight-file product/tool/test inspection, direct final verification and converged independent second-round review. Current proof: **1021 passed, one filesystem skip, 91.16% combined coverage**, strict mypy 37 source files and Ruff lint/format 148 files clean; twenty independent source-matched production/CI mutations all clean/mutant/restored 0/1/0. Fresh external wheel/sdist match product source; corrected harness/tests are packaged. Base has no Textual; separate minimum/latest installed environments each execute 353 tests with zero skips outside source. Both resolve Textual 8.2.8; overlap disclosed and existing `textual>=8.2.8` policy retained. No future-version, Linux, CI-execution or full Python-matrix claim.

MiniMax and Muse, both owner-selected xHigh, pass with no blockers. Four first-round suggestions exposed confirmed false-pass guards and were corrected by sole Gemini implementer; only packaging tests changed after round one. Both fresh targeted follow-ups assessed current proof; MiniMax independently repeated six corrected mutations and the full suite. Its full second-round report was recovered from its external native plan artifact after the terminal summary omitted the verdict; the native plan-exit question auto-cancelled and no implementation was approved. All 602 repository fingerprints and Git status stayed unchanged through review. Configured targets/options/modes verified; upstream served identity, effective effort and family diversity remain unverified under the selected named pair.

Expected initial three launches became eight: implementation, two pre-council corrections, two first-round critics, one tests-only council correction and two focused second-round critics. No failed provider launches; all eight completed with no pending child runs/questions; no extra worktree. Original dist artifacts preserved. Early worker deletion of pre-existing empty `.path` was verified/restored to exact baseline bytes; it remains excluded. Full acceptance, original briefs/reports, historical false-pass evidence, current gates/mutations/install receipts, wall times and non-blocking dispositions: [Stage G acceptance](../validation/assessment-repairs/g/acceptance.md). Active compute/billed tokens unavailable. Coordinator local commit authorized; frozen no-push boundary remains for Stage G. Stage H/U3–U9, release, tagging, old-dist replacement and dependency/resource-policy changes have not started.

## Execution record — Stage G delivered, 16 October 2026

Owner instructed "comm and push and tell me what is next step supposed to be". No product, test or CI file changed in this delivery step: the accepted Stage G commit `4acce920dfd73b116f4359fc8842d32ca149864d` was already committed locally, and the tracked working tree was clean apart from the pre-existing untracked empty `.path`, which remains preserved and excluded. Delivery therefore reused the Stage G acceptance gate results rather than re-running them; no new verification claim is made here.

Push executed to `origin main`: `491f9ce..4acce92 main -> main`. Local HEAD, `origin/main` and `git ls-remote origin refs/heads/main` all resolve to `4acce920dfd73b116f4359fc8842d32ca149864d`. This later owner authorization supersedes the earlier no-push boundary for the accepted Stage G commit only; it does not authorize publication, tagging, replacement of the original `dist/` artifacts, or dependency/resource-policy changes. The earlier push is unchanged: accepted Stages D/E/F remain at `491f9ce5902f98a7dd687c03418c308dcb88bcfd`.

This delivery step is documentation only, committed by the coordinator so the record matches the remote; it is not part of the Stage G product scope and carries no separate product evidence. Next per frozen Section 6 is **Stage H — Reconcile current documentation and measure remaining resource risk** (F13, R01; document R04 and accepted limitations), which has not started. U3–U9 and 0.2 publishing remain a separate feature/release campaign.
