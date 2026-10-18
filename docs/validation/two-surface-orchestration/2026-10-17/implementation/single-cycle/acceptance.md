# Prepared single-cycle trial

Surface: t3 prepares and inspects; herdr performs the human-started trial.
Status: **preparation accepted; live trial pending**.
Frozen plan: ad19c3115f518b8f10d1ab2ef23c04254196886b.
Provenance: 1aab76b5d5e4af90c37ebf23d3341e7588ac9c27.

The complete launch and native coordinator brief are ready for the human. The
disposable checkout contains only the unchanged initial fixture, has clean Git
status and no remote, and its evidence directory is unused. No Python code or
tests were prewritten. Only the human starts real Herdr/Hermes.

Planning review converged: MiniMax's surface/freeze-gate findings were corrected
and its R2 passed; DeepSeek's bounded completion passed after its first task ended
without a verdict. Final DeepSeek review passed. Final MiniMax verified the actual
contract, checkout and protected original repository and reported one blocker:
an old snapshot described superseded hashes as current. Sol reproduced that
bookkeeping error and performed the exact requested mechanical refresh from
actual final files. The raw changes_required verdict remains in its report; it is
not relabeled as a later pass. No execution-contract change followed final review,
so a further review wave for the metadata refresh was unnecessary.

All four product gates passed: 1048 tests, one expected macOS filesystem skip,
91.11% coverage; mypy 37 files clean; Ruff lint/format clean. Logs are in gates/.
No source/config changed after the gate run. All 1046 protected baseline files,
including the empty untracked .path, remain byte-identical. Only the permitted
plan, trial record and additive setup/pilot pointers changed. All six T3 child
tasks are terminal, with no pending questions or child runs.

The human receives the complete command and prompt inline, then returns the
verdict and actual evidence directory for T3 to inspect. That future result must
prove the whole native planning/implementation/review cycle; this preparation is
not a live pass. Old P01 stays unverified and P02-P09, observer work, recovery
experiments and Phase C stay paused. A successful normal trial will inform the
remaining minimal process adaptation; it is not full migration acceptance.
