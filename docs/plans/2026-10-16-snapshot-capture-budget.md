# Plan: bound TUI snapshot capture with an explicit refusal budget (R01)

Status: Agreed, amended 2026-10-16 (see the Amendment section at the end)
Authorization: User instruction, 2026-10-16: "ok we will follow GLM composite / create the PR and do
the fix and tell me when it's Merge ready." Scope narrowed by the user's answers to three explicit
questions: refusal budget only (no binary elision), payload bytes only, 256 MiB default, on by default.
Reference: f051b024369ddccb98fbec188b7569ff4ff4d5b7 (amended freeze; original freeze: a802b1f04836bb9641527372be80aee218ad0903)
Risk and review: **High** — the change touches the snapshot capture consistency path and the frozen
error surface of the TUI session controller. Planning review: two independent read-only critics from
verified different families — Codex `gpt-6.1-sol` (OpenAI) and GLM `glm-5.3-flash` (Zhipu). Both
independently rejected the issue's four proposals and the original "release the old generation" phase;
both landed on the explicit-refusal policy, and GLM supplied the pre-flight timing requirement that
makes the bound real.
Expected child tasks: planning critics (2, complete) + implementer + final implementation critics (2).

## Outcome

The TUI refuses to open a home whose captured skill payload exceeds a byte budget, instead of reading
an unbounded amount of file content into memory. The refusal is explicit and explained in the UI, it
preserves the previous valid generation, it never suggests a retry that cannot help, and the
line-oriented CLI keeps working as the fallback for any size.

## Current state

Verified facts, with the evidence each rests on:

- `capture_session()` (`skill_lens/core/snapshot.py:141`) reads every file of every canonical copy into
  `CapturedFile.data: bytes` with no byte bound, and publishes them through
  `SessionSnapshot.files` (`skill_lens/core/snapshot.py:189-247, 459-473`;
  `skill_lens/core/snapshot_models.py:23-29, 55-70`).
- The controller holds the old generation while a worker builds the new one; a successful accept
  replaces it (`skill_lens/tui/session.py:132-144`). Peak is therefore old + new, which is inherent and
  cannot be reduced by releasing after the fact.
- `accept_capture_error` treats `SnapshotChanged` and `IncompleteTreeError` as expected conditions and
  auto-appends `". Press r to retry."` to any message that does not already contain "retry"
  (`skill_lens/tui/session.py:176-181`). A size refusal is permanent, so reusing that branch would
  print misleading guidance.
- Stage H documents R01 as a valid, unbounded resource risk and **not** a reproduced out-of-memory
  failure, and requires the owner to choose a policy before any capture behaviour changes
  (`docs/validation/assessment-repairs/h/resource-risk.md:171-195`).
- Measured scale: 64 MiB of payload retains ~64 MiB for one generation and ~152 MiB transient peak
  during refresh (`docs/validation/assessment-repairs/h/resource-risk.md:44-57`).
- The TUI deliberately has no `--fail-on`, and CI gates on the line commands
  (`FULL_SCREEN_TUI.md:357-370`), so a TUI-only refusal cannot break CLI gating.
- `capture_session` has exactly one product call site, `skill_lens/tui/app.py:236`, so the budget is
  TUI-only by construction.

## Scope and boundaries

In scope:

- Payload sizing and refusal in `capture_session`, measured before the capture
  phase reads any file and enforced again against the bytes actually read.
- A dedicated `SnapshotTooLarge` error carrying the measured total and the configured limit.
- A TUI refusal surface that is distinct from the transient retry surface.
- A `--max-snapshot-bytes` option on `skill-lens tui`, default 256 MiB, with `0` meaning "no limit".
- Documentation, a CHANGELOG entry, an R01 status addendum, and tests.

Out of scope, deliberately:

- Binary elision / changing `CapturedFile.data` to `bytes | None` (the original POV A Phase 1). This
  requires amending `FULL_SCREEN_TUI.md` §21.2-21.6 and working through the §9.2 review checklist
  (report parity, missing-key handling, first visits, refresh consistency). Deferred pending separate
  authorisation.
- Temp-directory spill, deferred diff reads, and silent capping — all banned by
  `FULL_SCREEN_TUI.md:1294-1296`, `:1522-1523` and `:724`.
- Hash-only degradation of oversize files: a degraded *text* file would need a third render state and
  would change diff output. Refusing to publish is honest; degrading can lie in the diff view.
- Any change to CLI command output, exit codes, or `--fail-on` behaviour.
- The original plan's "release the previous generation after validation" phase: dead as written,
  because `accept_capture` already replaces the current snapshot on success.

## Implementation steps

1. **Core budget and refusal** — `skill_lens/core/snapshot.py`
   - Add `DEFAULT_MAX_SNAPSHOT_BYTES = 256 * 1024 * 1024` and a pure `format_bytes()` helper.
   - Add `SnapshotTooLarge(Exception)` carrying `total_bytes` and `limit_bytes`, with a plain-English
     message that states the measured size, the limit, that nothing was published, and that the command
     line remains available.
   - Add `_measure_capture_payload(index, *, cancelled)` returning `(total_bytes, sized_all)`. It walks
     each `CanonicalStatus.OK` entry with the same `hasher.iter_files()` rules the capture loop uses,
     sums `st_size`, and reports `sized_all=False` when any entry cannot be sized because it would fail
     the capture loop's completeness pre-check.
   - Extend `capture_session(..., max_snapshot_bytes: int | None = None)`. After discovery and before
     the byte-capture loop: if a positive limit is set, size the payload; refuse with
     `SnapshotTooLarge` when `sized_all` is true and the total exceeds the limit. When `sized_all` is
     false, skip the refusal and let the capture loop raise its existing `IncompleteTreeError`, so
     today's behaviour is preserved exactly.

2. **TUI refusal surface** — `skill_lens/tui/session.py`
   - Add `refusal_message: str | None`.
   - `status` returns `"refused"` when a refusal is set, checked before the retry branch.
   - `accept_capture_error` handles `SnapshotTooLarge` first: set `refusal_message` to the exact error
     text, clear `retry_message`, and never apply the "Press r to retry" auto-append.
   - `accept_capture` and `request_refresh` clear `refusal_message`.

3. **Application plumbing** — `skill_lens/tui/app.py`, `skill_lens/tui/__init__.py`
   - `SkillLensApp.__init__(..., max_snapshot_bytes=None)`; `_run_capture` passes it to
     `capture_session`.
   - `_update_ui` renders the `"refused"` status as the refusal message.
   - `run(..., max_snapshot_bytes=None)` forwards it to the app.

4. **CLI option** — `skill_lens/cli.py`
   - Add `--max-snapshot-bytes` (integer bytes, default 256 MiB, `0` disables) to the `tui` command,
     validated to reject negative values, and pass it to `_launch_tui` → `run`.

5. **Documentation**
   - `FULL_SCREEN_TUI.md`: add a refusal policy subsection describing the budget, the pre-flight
     timing requirement, the preserved-generation rule, and the CLI fallback; extend the §9.1 expected
     conditions bullet.
   - `CHANGELOG.md`: `[Unreleased]` entry.
   - `docs/validation/assessment-repairs/h/resource-risk.md`: a dated, clearly-marked addendum on the
     R01 section recording that a policy is now implemented, without altering the original Stage H
     measurements.

6. **Tests**
   - New `tests/test_snapshot_budget.py`: refusal fires before the capture phase reads any file
     (reads patched to
     raise); exactly-at-limit is admitted; one byte over is refused; config and lockfile bytes are not
     counted; an incomplete tree still raises `IncompleteTreeError` rather than `SnapshotTooLarge`;
     `max_snapshot_bytes=None` and `0` mean unbounded.
   - Extend `tests/test_tui_session.py`: refusal sets `refusal_message`, sets status `"refused"`, does
     not set the sticky failed flag, does not contain "Press r to retry", and is cleared by a later
     refresh or successful accept.
   - Extend `tests/test_cli.py`: option plumbing and negative-value rejection.

## Acceptance

- The refusal is raised before the capture phase reads any file, proven by a guard test that patches
  the capture-phase read path to raise, and the budget is enforced again against the bytes actually
  read so a file that grows after the measurement cannot carry the capture past the limit.
- Boundary behaviour is exact: total equal to the limit is admitted; one byte more is refused.
- Only skill payload bytes count toward the limit; captured configuration and lockfile bytes do not.
- An unreadable or incomplete tree still produces `IncompleteTreeError`, unchanged.
- A refusal preserves the previously published generation, leaves the controller non-failed, and
  returns exit code `0` on a normal quit.
- The refusal message never advises a retry.
- `--max-snapshot-bytes 0` disables the limit; a negative value is rejected as a usage error.
- The `tui/` read-only AST guard still passes; no writes, temp files, or new dependencies.
- All four gates clean: `pytest --cov=skill_lens` (90% floor), strict `mypy`, `ruff check .`,
  `ruff format --check .`.

## Review decisions

- **Accepted** (GLM): refusal must be evaluated pre-flight. A check placed after byte capture leaves
  the transient overlap spike intact and bounds only retained heap, which does not close the symptom
  R01 measured.
- **Accepted** (GLM): a dedicated refusal surface is required. The existing expected-condition branch
  would append "Press r to retry" to a permanent refusal and mislead the user.
- **Accepted** (Codex and GLM): explicit refusal over hash-only degradation, because a degraded text
  file must render as something and would change diff output.
- **Accepted** (Codex): the Stage H benchmark keeps working, because `CapturedFile.data` is unchanged
  by this plan; no harness re-baseline is required.
- **Accepted** (both critics): the original plan's release-after-validation phase is removed as dead.
- **Deferred**: binary elision. Correct and output-safe for binary files, but it reduces a measured
  workload rather than bounding the risk class, and it requires a §21.2-21.6 amendment plus the §9.2
  review checklist. It becomes worthwhile only with evidence about the real-world binary/text
  composition of retained payloads, which Stage H explicitly did not measure.
- **Rejected**: the issue's proposals 1-4, for the contract reasons recorded above.

## Amendment (2026-10-16) — scope of the pre-read guarantee

**Authorization:** the owner selected "Amend the guarantee" on 2026-10-16 in response to the
independent implementation review. This amendment changes the execution contract, so it was frozen
with the same two-commit procedure as the original plan.

**Finding that forced it.** The implementation review (Codex `gpt-6.1-sol`) showed that the original
acceptance criterion — the refusal is raised "before any payload byte is read" — is **not
achievable**, and that this plan was internally inconsistent: the implementation steps place the
measurement *after* `live_discovery()`, while the acceptance criterion demanded a guarantee that
ordering cannot provide. The reason is structural, not a placement mistake:

- `capture_session` must call `live_discovery()` before it can measure anything, because discovery is
  what determines the set of entrypoints to measure.
- Discovery parses each skill's source document (`discovery.py:785-790` → `parser.py:185`,
  `path.read_text()`) and retains the body on the entry.
- Discovery's own enumeration reads a candidate document to decide whether a qualified standalone
  markdown file qualifies at all (`discovery.py:368-384`).

Meeting the original criterion would therefore require redesigning how discovery identifies
candidates — a change to a load-bearing module, with its own plan and review round. The owner chose
not to fold that into this change.

**Amended contract.** The budget now guarantees:

- the capture phase reads no payload once the home is known to be over budget; and
- the budget is enforced again against the bytes actually read, so a file that grows after the
  measurement cannot carry the capture past the limit. Normalised fingerprints cannot catch that
  alone: replacing LF with CRLF doubles the raw bytes while leaving the normalised hash unchanged.

It does **not** bound discovery's parse of each skill source document. That read is a recorded
residual, stated as such in `FULL_SCREEN_TUI.md` §9.3, the CHANGELOG entry, and the R01 addendum.

**Why the residual is acceptable.** The payload R01 measured is support-file assets, which discovery
only streams for hashing and never retains; the budget fully covers them. What sits outside it is a
single skill source document large enough to matter on its own. Closing that is recorded as future
work, not claimed as done.

**Also amended by this round**, from the same review: the budget is enforced against bytes actually
read; an accepted internal fault clears a standing refusal so a fault is never masked; and the
documentation no longer claims the line-oriented commands retain no payload.
