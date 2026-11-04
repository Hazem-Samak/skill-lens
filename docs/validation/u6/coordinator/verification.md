# U6 coordinator review and verification — 3 November 2026

Status: Locally technically verified on the final implementation/test tree.
The owner-requested native implementation, parent review and parent checks are
complete. The owner subsequently authorized commit and push with
“if all good comm and push please” and confirmed “continue please”.

## Authority and review scope

The owner requested a native `gpt-6-luna` subagent at Max effort, followed by this
coordinator's own review and tests. See [native-authorization.md](native-authorization.md).
The frozen product plan remains unchanged. The review base is
`3a266b4986f5b9bd6838e773a298b2a862904a08`.

The coordinator reviewed both repository standards and the approved U6 behavior,
including the new untracked source/test files as well as the tracked diff. No
additional review agents were dispatched. This is parent review of a separate
implementer's work, not a claim of the ordinary two-critic council process.

## Review findings and corrections

- Removed-agent refresh initially changed Compare state without changing its
  visible mode. The implementation now reveals a usable picker in both ordinary
  and JSON modes and clears invalid old JSON. Parent key-driven tests verify it.
- Compare before its first capture initially suggested an empty registry. It now
  explains the actual session state. Worker tests distinguish refusal/no capture
  from a genuinely captured empty registry.
- Controlled stale-result/error tests originally relied on a short pause. They
  now observe worker completion and UI handoff, and hold token tests behind barriers.
- The new coverage exclusions were removed. The existing threshold, measurement
  scope and expected output files remain unchanged.
- Target preservation now includes an actual U6 traversal with before/after
  inventory, bytes, modes and symlink targets. It is separate from tests that
  deliberately change synthetic captured inputs.
- The old implemented-keymap documentation was reconciled with `g`, `c` and the
  new JSON modes, and Compare eligibility counts captured registry definitions.
- The first parent full run passed all tests but measured only 89.64% coverage
  and found nine lint errors. Real navigation, metadata, button and explicit-retry
  cases were added; the next parent full run passed at 90.09% with clean static checks.
- The mutation campaign exposed an invalid-input test gap: a fast forbidden worker
  could finish before an `active_requests` check. The required correction proves
  that no request is dispatched, independent of completion timing. The final
  request spy, allocation/cache checks and mutation fail directly on illicit work.
  The retry test also holds a second worker so it fails at the actual call count,
  rather than letting a retry storm obscure that assertion behind a UI timeout.

No remaining in-scope product or test blocker was found. Luna's own changed-file
and check report is retained separately in
[implementation-report.md](../implementation/implementation-report.md).

## Parent-authored UI checks

The coordinator independently authored six Pilot checks, using temporary HOME
and the repository's existing sandbox/system-root fixtures. They verify frozen
first comparison after deletion, actual CLI JSON parity, Home filter typing,
ordinary/raw removed-ID refresh with a usable replacement pair, and accepted
fault behavior without automatic retry. Normal and fault layouts cover 100×30
and 60×24. All six passed in 7.33 seconds on the corrected implementation.

Source: [independent-checks.py.txt](independent-checks.py.txt).
Output: [independent-checks-final.log](independent-checks-final.log).
These headless UI checks are not human visual approval.

## Full project checks

The parent uses separate coverage data and mypy caches to avoid collisions with
the worker. Results are tied to source/test/configuration hashes in
[full-gates.json](full-gates.json). Acceptance checks the observed coverage number
and failure text as well as the exit status: the first run printed a coverage
failure despite pytest returning zero.

- [First full run](first-full-run/full-gates.json): retained failure evidence,
  1217 passed/1 skipped, 89.64% combined coverage and nine lint findings.
- [Second full run](second-full-run/full-gates.json): 1220 passed/1 skipped,
  90.09% combined coverage, mypy clean over 44 source files, Ruff lint clean and
  401 files formatted. Source/test/configuration hashes were unchanged during it.
- Final run after the mutation-driven test correction: **1220 passed, 1 skipped
  in 254.18 seconds; 90.09% combined coverage**. Mypy passed over 44 source files,
  Ruff lint passed and Ruff format check reported 404 files already formatted.
  Every command exited 0, coverage explicitly reached the unchanged 90% threshold,
  and all recorded source/test/configuration hashes remained unchanged during the run.
  The six independent UI checks remain valid: their product bytes match this final
  tree exactly. Complete final output: [pytest.log](pytest.log), [mypy.log](mypy.log),
  [ruff-check.log](ruff-check.log), [ruff-format-check.log](ruff-format-check.log).

The existing skip needs a case-sensitive filesystem. Coverage is combined
statement/branch measurement, not a branch-only percentage.

## Dotted coverage-source diagnosis

A diagnostic command targeting `skill_lens.tui.agents` and
`skill_lens.tui.compare` as dotted coverage sources exposed a tooling import
problem. The coordinator reproduced the first UI failure with full output in
[targeted-coverage-reproduction.log](targeted-coverage-reproduction.log).
The same single test passes in 1.59 seconds with the repository's normal
`--cov=skill_lens`; its deliberately partial-suite coverage score is not a gate
result. See [whole-package-single-test.log](whole-package-single-test.log).

The installed coverage source-package discovery calls `find_spec` inside
`sys_modules_saved`, which removes modules imported during discovery. A dotted
source imports the TUI parent and asyncio before that cleanup. Fresh-process
task-cancellation probes show that the raised exception then has the same printed
name as `asyncio.CancelledError` but a different class identity, so the current
class does not catch it. Whole-package mode retains the correct identity.

The coordinator reproduced the identity mismatch using an isolated git-archive
copy of the pre-U6 baseline too. The archive was deleted afterward. This establishes
that U6 did not introduce the mechanism. No package, framework, settings or timeout
change was made to mask it. Probe receipts:
[current implementation](coverage-import-diagnosis.json),
[pre-U6 baseline](baseline-coverage-import-diagnosis.json).
The worker's interrupted duplicate and original-attempt limitations are retained
in its evidence rather than represented as completed full logs.

## Mutation evidence and preservation

Worker campaign: [implementation mutations](../implementation/mutations.json).
The parent inspected all intended assertions and temporary-copy provenance, not
just nonzero statuses. **13/13 final mutants were caught**, each with a passing
clean control and restored control. Cases 9 and 10 were rerun after their test
corrections and fail at the request-spy and call-count assertions. Case 12's
existing hidden-cursor tuple mismatch was accepted from its complete retained
output without an unnecessary rerun. No final in-scope mutation remains unresolved.
Earlier harness-selector failures and the redundant-JSON-clearing probe remain
recorded in [attempt dispositions](../implementation/mutation-attempts.md).

[baseline.json](baseline.json) records the frozen plan hash and 990 unrelated
entries under `.path` and `docs/validation/2026-10-25/`. Final preservation and
Git checks passed: all 990 entries, the frozen plan, excluded engines/controller/
models/registry/dependencies/process files and expected outputs are unchanged.
At the verification checkpoint, the index was empty and HEAD was the starting
`3a266b4` commit. Receipt:
[preservation-and-mutations.json](preservation-and-mutations.json).
The preservation receipts and `final-integrity.json` record the checkpoint before
delivery authorization; their no-commit fields are historical. The owner has
since authorized commit and push. No release, hosted CI result or human visual
approval is claimed. U7 is not started by this verification.
