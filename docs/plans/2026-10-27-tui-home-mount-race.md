# Plan: TUI Home startup mount race

Status: Agreed
Authorization: The owner asked for this fix on 2026-10-27 ("go ahead with your
recommendation"), explicitly approving the recommendation to have the current
assistant make this small fix without a separate reviewer, then review, commit,
and push it.
Roster: Coordinator/implementer — the current assistant session; the owner
approved the reviewer exception for this one-line fix. No critic models were
named for this mission.
Reference: pending
Risk and review: Normal by the project table (a non-load-bearing product fix),
with the owner's explicit exception from independent critic dispatch. Review is
the requested two-axis `/code-review` pass plus the four project gates.
Expected child tasks: none; the owner explicitly authorized direct
implementation and waived independent reviewer dispatch for this small fix.

## Outcome

If the initial TUI capture completes before the Home screen finishes mounting,
the Home table still appears without the user pressing `r`. A regression test
pins that ordering.

## Current state

- Verified diagnosis: `SkillLensApp.on_mount()` starts the capture worker before
  the default Home screen is marked mounted (`skill_lens/tui/app.py:194-195`).
- If the worker finishes first, `CaptureComplete` makes the controller `ready`
  while `HomeScreen.is_mounted` is still false. `sync_from_controller()` returns
  early (`skill_lens/tui/home.py:490-493`).
- `HomeScreen.on_mount()` later calls `sync_from_controller()` and
  `_host._update_ui()` synchronously, but both run while the screen still
  reports `is_mounted == False`, so neither populates the table.
- No later event re-syncs the screen; the table stays empty until an explicit
  refresh.
- A temporary deterministic probe returned a ready snapshot immediately and
  reproduced `status=ready, home_gen=None, rows=0` in 20/20 runs. The same
  symptom appeared in 26/42 `test_tui_why.py` tests under heavy local CPU load.
  A temporary one-line deferral made the probe pass 20/20 and the loaded test
  file pass 42/42.
- The current CI run at `61d1d9c` fails only the macOS test jobs, with different
  app-startup tests timing out at the shared `_wait_ready` helper.

## Scope and boundaries

Allowed changes:

- `skill_lens/tui/home.py` — defer the post-mount UI reconcile by one refresh.
- `tests/test_tui_home.py` — one deterministic startup-race regression test.
- `CHANGELOG.md` — one Unreleased "Fixed" entry.
- This plan file.

Excluded: capture/discovery behavior, public formats, registry, exit codes,
snapshots/goldens, CI workflow changes, U5 work, and unrelated pre-existing
working-tree files.

## Implementation steps

1. In `HomeScreen.on_mount()`, keep the immediate sync and replace the immediate
   `self._host._update_ui()` call with
   `self.call_after_refresh(self._host._update_ui)`, so the reconcile runs after
   the screen is mounted.
2. Add a regression test that builds a synthetic Home, captures a real snapshot,
   monkeypatches the app's capture service to return that snapshot immediately
   with the requested generation, then asserts the Home table is populated
   without pressing `r`.
3. Record the fix in `CHANGELOG.md` under Unreleased/Fixed.

## Acceptance

- The new test fails when the deferred reconcile is removed and passes with it.
- `pytest --cov=skill_lens`, `mypy`, `ruff check .`, and
  `ruff format --check .` pass.
- The two-axis review (Standards and Spec) reports no unresolved blocker before
  the final commit and push.
- No real home-directory skills are read; all test data remains synthetic.

## Review decisions

- Accepted: deferring the existing post-mount update rather than changing
  capture, discovery, or the controller. It is the smallest change that closes
  the ordering gap.
- Accepted: a regression test that forces the early-completion ordering, because
  a timeout increase would not fix the reproducible blank table.
- Accepted: the owner's explicit exception to independent reviewer dispatch for
  this small fix; the requested `/code-review` still checks both axes.
