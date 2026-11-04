# U7 planning verification — 4 November 2026

The [Doctor plan](../../../plans/2026-11-04-tui-u7-doctor.md) is frozen.
The owner authorized sole-planner work, two separate self-revisions, freeze and
commit, and explicitly waived the normal planning and implementation loops in
this session. No other agents or workers were launched. Implementation remains
subject to a later owner instruction. These are two passes by one planner;
they are not independent-agent review or proof of zero defects.

## Verified starting point

- Baseline `01748933f7108703b796c01e15e85bd0918cc6d7` on `main`.
  Local HEAD and GitHub main matched at mission start.
- `FULL_SCREEN_TUI.md` identifies U7 Doctor as the next assignment after U6.
  U6 local verification is in `docs/validation/u6/coordinator/verification.md`.
- Read current snapshot/model, Doctor producer, CLI serializer/renderer, Home
  filtering/selection/ownership, app screen lifecycle, Agents and JSON patterns,
  read-only tests, DEVELOPMENT and relevant Phase 4 findings.
- Existing `.path` and `docs/validation/2026-10-25/` are outside the mission and
  are excluded from staging. All 1692 preexisting tracked files remain
  byte-identical to the captured baseline. See [integrity.json](integrity.json).
- No product, test, dependency, expected-output, process or AGENTS.md changes.
  The plan specifies future changes; it does not implement them.

## Two separate self-review passes

1. **Source, identity and ownership.** Reviewed the first complete draft against
   producer and consumer APIs. Added generation-bound finding rows and active
   screen guards; made the queued Home jump survive its generation-reset fallback;
   explicitly kept Doctor out of the computed-report/worker protocol.
   [Report](review-1.json), [exact revision](revision-1.patch.gz).
2. **Adversarial acceptance and handoff.** Reviewed the revised plan from error,
   raw JSON, refresh and test-evidence scenarios. Bound saved detail scroll to
   finding identity; required explicit duplicate/ambiguous-path fixtures and
   literal test oracles; covered delayed initial capture; preserved every reverse
   display mapping; named both ScreenResume and explicit close resume paths.
   [Report](review-2.json), [exact revision](revision-2.patch.gz).

Both passes have no unresolved planning blockers. The second revision includes
administrative freeze/result wording after the checks completed. Revision hashes
and patches retain the exact inputs/outputs rather than claiming fresh reviewers.

## Current baseline checks

Commands, durations, exit codes and output hashes: [gates.json](gates.json).

| Command | Observed result |
| --- | --- |
| `.venv/bin/pytest --cov=skill_lens` | 1,220 passed, 1 skipped in 255.28 seconds; combined coverage 90.09% with branch measurement and TUI included. |
| `.venv/bin/mypy` | Passed, 44 source files. |
| `.venv/bin/ruff check .` | Passed. |
| `.venv/bin/ruff format --check .` | Passed, 405 files already formatted. |

All four exited 0. The coverage success line explicitly confirms the unchanged
90% gate was reached; acceptance does not rely on the exit code alone. The skip
requires a case-sensitive filesystem. These are current baseline checks, not
U7 implementation acceptance. Outputs: [pytest](pytest.log), [mypy](mypy.log),
[lint](ruff-check.log), [format](ruff-format-check.log).

A separate temporary sandbox probe passed in 0.06 seconds. It verifies actual
CLI Doctor JSON equality on unchanged captured inputs, a real displayed-tilde
finding backed by the stored display map, a symlink alias in stored same-location
pairs, selectable broken-entry identity, empty versus info-only health, and
unchanged report/path data after deleting fixture files and changing HOME.
Source: [contract-probe.py.txt](contract-probe.py.txt).
Result: [contract-probe.log](contract-probe.log).

The first probe attempt used `missing_description` as a finding code. Inspection
confirmed the existing Doctor producer emits `malformed_frontmatter` for that
case. Corrected only the temporary probe and reran it; no engine or plan behavior
was changed to fit the probe. Preserve the [initial failed output](contract-probe-first.log).
Replay by copying the probe to a temporary `test_contract_probe.py` and baseline
`tests/conftest.py` beside it, then run the command in `gates.json` with the repo
on PYTHONPATH. The fixture patches HOME, activates the sandbox and guards system
roots. The temporary probe does not implement the future path matcher or screen.

## Freeze and delivery boundary

Frozen plan SHA-256: `3350c7a1d15e4f4d60d5861b0a0c5eaa171a70d6af9cd8936ec94d6edc88ad56`.
The commit containing this plan is the authoritative frozen revision. Exact
commit and pushed-reference verification are reported in the delivery message;
a document cannot contain its own future commit hash.

The frozen contract includes Home `h`, the stored findings and JSON, conservative
captured-only path matching, an explicit Home jump that clears blocking filters,
refresh/ownership rules, eleven acceptance groups and required mutation checks.
Implementation, human visual approval, hosted CI acceptance, U8/U9 and publishing
remain outside this mission. The plan's checks and two self-revisions support readiness to implement,
not a guarantee that the future implementation is correct.
