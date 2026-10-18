# Human launch (paste inline after T3 accepts preparation)

Exit the previous Hermes conversation to the Herdr shell. If the owned pilot
session is not open, open it from your cmux terminal:

```bash
herdr --session skill-lens-pilot-20261017
```

In that genuine Herdr shell, paste:

```bash
test "${HERDR_ENV:-}" = 1 &&
cd /private/tmp/skill-lens-herdr-p01-repair-20261017-arflso4p/pilot-artifacts/simple-loop-trial-dkn9ufiu/checkout &&
test -f fixture.txt &&
test ! -e ../evidence/entry.json &&
test ! -e ../evidence/result.json &&
HERMES_CODEX_BASE_URL=http://127.0.0.1:8787/chatgpt \
hermes --cli --ignore-rules --toolsets terminal,file \
  --provider openai-codex --pass-session-id \
  --in "$PWD" -m gpt-6.1-sol --reasoning high
```

Then paste this into the fresh Hermes conversation:

> Perform the single-cycle Herdr trial in
> `/Users/corvette/Documents/Projects Coding/Skill Lens/docs/validation/two-surface-orchestration/2026-10-17/implementation/single-cycle/coordinator-brief.md`.
> Read that brief and its frozen plan explicitly. Run its one planning,
> implementation and final-review cycle in the disposable checkout. Keep the
> original Skill Lens repository read-only. Stop after the trial and return your
> verdict and exact evidence directory. Do not resume the observer or P01-P09.

Bring the verdict and evidence path back to T3 for actual file inspection.
If a path/check fails, return the failure here; preserve the existing attempt.
