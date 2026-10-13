# Stage C Round-2 Implementation Review — Skill Lens (read-only critic seat: mcode)

## Summary

Goal: independently review all current Stage C changes on `main` against baseline `085e28ddb19c01a39a0af7920b7840579da7bbab`, on the primary axis of repository standards, safety and compatibility. Scope is the Stage C slice only (F05 cwd/XDG, F06 one-hit-per-entrypoint and per-hit aliases, F07 root/version entry formats and standalone shortcuts); Stage D owns full vendor identity/precedence/loadability/control integration, so D-only gaps are reported separately and are not treated as C blockers.

HEAD equals the baseline; all Stage C work is uncommitted in the working tree (`git diff HEAD`, 14 modified files + 2 untracked: `tests/test_stage_c_repairs.py`, `docs/validation/assessment-repairs/c/stage-c-evidence.md`). No edits, no commits, no snapshot/golden regeneration, no cache writes were performed by this review.

Verdict: **changes_required** — one reproduced discovery regression affecting five agents, plus one evidence-accuracy defect in the C acceptance artifact.

Key design decisions in the reviewed change: a new `RootBase` / `EntryFormat` enum pair parsed in `registry/loader.py::_parse_root` with an implicit default derived from the unrelated presence of `file_rule_id`; `RootHit.is_file` carries per-hit file-ness so rule attribution and aliases are per-hit; `_candidates_for` computes identity names and override membership per hit rather than per merged entry; `paths.xdg_config_home()` gains sandbox containment; `cli._effective_cwd` resolves live relative cwd against the terminal and sandbox relative cwd against the sandbox; `capture_session` gains optional keyword-only `registry` injection.

Gate evidence read directly from the coordinator's final logs (not reused from worker reports): **848 passed, 1 skipped**, coverage **93.32%**, mypy clean over 35 source files, ruff clean, format clean. These are accepted as gate evidence, not as correctness conclusions.

## Reproduced regression: silent standalone-`.md` loss for five agents

**Location.** `skill_lens/registry/loader.py:72-79` (`_parse_root` default) together with the six agent definitions that declare no `entry_format` and no `file_rule_id`: `claude.toml`, `dsh.toml`, `grok.toml`, `qoder.toml`, `omp.toml`, `windsurf.toml`.

**Problem.** Pre-change, `discovery._list_entries` appended *any* `.md` child of a root as a standalone file skill, so a root-level `README.md` in a codex plugin root also became a false "broken skill". F07 fixes that by introducing per-root entry formats. But the format is inferred rather than declared:

```python
entry_format = EntryFormat(
    raw.get("entry_format", "standalone_md" if raw.get("file_rule_id") else "directory")
)
```

Six agents have no `file_rule_id`, so they silently fall to `DIRECTORY`, which makes `_list_entries` skip `.md` files entirely. Codex's loss is intended and evidenced; the other five are not declared anywhere and not covered by any test in either direction.

**Expected behaviour.** Standalone-`.md` discovery must not change for an agent unless that agent's root explicitly declares `entry_format` with a recorded evidence entry and a test pinning the new behaviour. Either declare `entry_format` for `claude` / `dsh` / `grok` / `qoder` / `omp` (global and `.agents`-shared roots) with provenance, or preserve the baseline discovery surface.

**Evidence.** Read-only `git archive 085e28d` extraction to `/tmp` versus the working tree, same synthetic HOME, `XDG_CONFIG_HOME` cleared, no repo writes. A valid standalone `legacy_standalone.md` plus a `dir_control/SKILL.md` control placed under each root:

| root | baseline 085e28d | current tree |
|---|---|---|
| `.claude/skills` | YES (claude) | **no** |
| `.dsh/skills` | YES (dsh) | **no** |
| `.grok/skills` | YES (grok) | **no** |
| `.qoder/skills` | YES (qoder) | **no** |
| `.agents/skills` | YES (codex, dsh, omp, opencode) | YES (opencode only) |
| `.codex/skills` | YES (codex) | no (intended, evidenced) |
| `.gemini/config/skills` | YES (antigravity) | YES (preserved) |
| `.pi/skills` | YES (pi) | YES (preserved) |

The loss is silent: no doctor finding, no scan note, no registry declaration. For a read-only diagnostics tool this is indistinguishable from "not installed", which is the same failure class as a hallucinated precedence rule under golden rule 6. Stage D cannot safely build per-agent loadability on an inventory that has already dropped capability without a record.

Note that the historical F17 external standalone shortcut test was originally anchored on `.claude/skills` and was re-homed to `.pi` / `.gemini` without recording that Claude lost the surface.

## Evidence-accuracy defect in the C acceptance artifact

**Location.** `docs/validation/assessment-repairs/c/stage-c-evidence.md` §2 line 30.

**Problem.** The record states that OpenCode V2 discovery applies to each source "including shared roots (`.agents/skills`, `.claude/skills`)". `opencode.toml` registers `opencode_native`, `opencode_shared_global` (`.agents/skills`), `opencode_project` and `opencode_project_agents` (`.agents/skills`) — it has **no** `.claude/skills` root. A skill under `.claude/skills` is therefore still `UNSEARCHED` for OpenCode, which is exactly the baseline gap recorded in the frozen plan (line 90, "OpenCode compatibility roots").

**Expected behaviour.** The evidence record must distinguish the vendor specification from what Skill Lens actually registers, so a reader does not infer that Stage C closed the `.claude/skills` compatibility gap.

**Evidence.** `skill_lens/registry/agents/opencode.toml` root list; `docs/plans/2026-10-12-assessment-repairs.md:90`. The underlying missing root is Stage D vendor scope; the inaccurate claim is in the Stage C deliverable.

## In-scope correctness assessed as sound

- `capture_session` is genuinely keyword-only (`def capture_session(*, generation, home, cwd, registry=None, cancelled=None)`), so adding `registry` before `cancelled` breaks no positional caller.
- Test isolation is intact: `tests/conftest.py:202,220` `delenv("XDG_CONFIG_HOME")` in both `mock_home` and `bare_home`, so the new XDG base cannot reach the real filesystem under test; ambient `XDG_CONFIG_HOME` is unset here anyway.
- XDG base preserves baseline behaviour when the variable is unset (`home()/.config` + `opencode/skills`), so the F05 fix is additive, not a move.
- F06 is well proved: `test_root_and_agent_order_invariant_aliases` permutes both the agent mapping and every agent's root tuple, asserts rank/rule/state/alias under the permutation, adds alias negative controls per agent, and checks live-vs-snapshot parity including `s1.files[key] == s2.files[key]`.
- F07 per-format tests carry both positive and negative controls and preserve diagnostics: codex file-symlink ignored while the dangling shortcut still yields `ERR_DANGLING_SYMLINK` plus a doctor finding; Pi exact/lowercase/dot-case positives and negatives with a malformed-declaration ERROR; OpenCode V2 depth-0 and depth-1 nested symlinks with wrong-case, no-declaration, dangling and cycle negatives.
- `_list_recursive_entries` does not double-append OpenCode V2 root children (the root-enumeration loop handles only files and symlinks; plain directories are reached solely by `os.walk`), so evidence doc §2 dedup claim holds.
- The removed `test_phase2_gate` override test encoded the pre-fix bug: it asserted that overriding the frontmatter name did *not* disable a `frontmatter_name`-identity agent, which is the opposite of the agent's declared identity. The synthetic replacement covers all three `identity_source` values with positive and negative override controls.
- `LEGACY_FILE` is fully absent from `skill_lens/` and `tests/`; the opaque captured-byte proof is isolated with counters proving failure at the file-capture fingerprint check (`disc_calls_a2 == 1`, `doc_calls_a2 == 0`) plus a non-mutating positive control.
- No snapshots or goldens changed; no source files changed outside the declared Stage C set.

## Stage D carryover (not C blockers)

Vendor loadability vs generic parser validity for OpenCode V2 frontmatter-optional files; Pi vendor lookup-ID policy; Antigravity root/surface alignment and the builtin-root path; OpenCode `.claude/skills` compatibility root; traversal limits (no recursion through symlinked container directories, stop at declared skill boundary, inherited `MAX_WALK_DEPTH = 4` vs vendor unbounded recursion); generic lowercase `skill.md` parser compatibility retained for unconstrained formats and not vendor-proven.