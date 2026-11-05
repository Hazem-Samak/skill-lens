# U9 final review — reviewer 2 axis: installed-test effectiveness, isolation and guard load-bearingness

You are an independent critic on the Skill Lens project (Python CLI + optional
TUI, strictly read-only by design). Risk level: High (release packaging and
installed compatibility are load-bearing). Round 1 of the U9 final review wave.
The coordinator (a Qoder session, underlying model identity unverified)
prepared this brief; the implementer is a separate agent (DeepSeek v4.1 per the
owner). You did not write this code.

READ-ONLY CRITIC TASK. You are reviewing, not implementing.

Do NOT create, edit, move, delete or rename any file in the repository. Do NOT run
any command that writes: no formatters, no linters with --fix, no install, no
git commit/checkout/stash, no snapshot or golden regeneration, no test runs that
write into the checkout. Test output, if you need it, goes only to a temporary
directory outside the repository.

If you believe a change is required, do not make it. Report it instead.

Return only the report format below. Nothing else.

## What you are reviewing

U9 ("Prepare the 0.2.0 release") is implemented as UNCOMMITTED work in the
working tree at HEAD `da2b8d9` on branch `main`, repository:
`<REPO_ROOT>` (use this as your
working directory; read files there).

- Frozen plan (authoritative contract):
  `docs/plans/2026-11-05-tui-u9-release-preparation.md`, frozen at commit
  `f3c652beed4e7b5b745a77a900cc1e93f5a5f105`. Read it in full first; the
  working-tree copy differs from that commit only in the `Reference:` line.
- Core files for YOUR axis: `scripts/smoke_wheel.py` and
  `tests/test_tui_packaging.py` (read both completely, plus
  `tests/test_tui_routing.py` and the four selected functions in
  `tests/test_tui_help.py`), and the evidence under
  `docs/validation/u9/implementation/` (implementer r1: `implementation-report.md`,
  `self-review.md`, `mutations/mutations.json` + logs, `install-receipt.json`,
  `terminal-receipt.json`, `version-probes.json`) plus
  `docs/validation/u9/coordinator/precommit/` (coordinator r2 rebuild receipts
  after two documentation files changed, and the corrections ledger
  `coordinator-corrections.json`). Retained lane environments and artifacts:
  `/tmp/u9-candidate-r2/` and `/tmp/u9-candidate/` (outside the repo, readable).
- Disclosed limitations (not findings unless wrong): min/latest Textual both
  resolve 8.2.8 (today's latest); wheel not bit-reproducible (per-file identity
  verified); single-platform local runs. The candidate has been rebuilt twice
  after the implementer's first wave (r1 → r2 → r3) because packaged
  documentation changed; each wave's receipts live under
  `docs/validation/u9/coordinator/precommit/` and the CURRENT wave is **r3**
  (`candidate-r3.json`, `install-receipt-r3.json`, `version-probes-r3.json`,
  `terminal-receipt-r3.json`, `final-*-r3.log`, plus the wave-A review ledger
  `adjudication-wave-a.json`). Retained lane environments and artifacts:
  `/tmp/u9-candidate-r3/` (current) and `/tmp/u9-candidate-r2/`,
  `/tmp/u9-candidate/` (history) — all outside the repo, readable.

## Your single review question

Are the new and changed package-verification guards genuinely load-bearing,
isolated, and honest in their receipts — or could any of them pass vacuously or
silently under-report what actually ran?

Concretely:

1. **Manifest effectiveness.** `REQUIRED_TUI_MODULES` now lists 12 modules; the
   independent hand-maintained list, the equality guard, and the completeness
   guard against the imported package's `tui/` directory must together catch a
   dropped entry AND a newly shipped module that was never added. Check the
   guards' ordering/derivation logic (the implementer disclosed and fixed an
   initial sorted-vs-declared bug and a source-tree assumption that breaks
   inside an installed lane — verify the fixes are correct in BOTH contexts,
   since `tests/test_tui_packaging.py` itself runs inside the installed lane).
2. **Selection effectiveness.** The 14 installed selections (9 existing + 5 new)
   must reach the lane's own pytest argv unfiltered: verify the argv-capture test
   drives the real command builder, the option-narrowing detector is credible
   (its list is not empty or trivially satisfied), the static node-ID existence
   guard and the 100x30/60x24 parametrization guard parse the real source, and
   the receipt records `pytest_summary`, counts and duration.
3. **Receipt honesty (the parser fix).** The old regex silently receipted a
   451-test lane as zero tests when pytest appended the elapsed parenthetical.
   Verify the new parser cannot under-report: unknown shape raises, zero passed
   fails the lane, and both modern and legacy summary forms are covered —
   including a summary line like `1 failed, 460 passed` (must NOT pass) and
   `461 passed, 1 skipped` expectations vs the recorded 461/0.
4. **Isolation.** Lane venvs, synthetic HOME/XDG, test-lane copies of tests
   without the `skill_lens` source package (and the hostile-copytree rejection),
   installed-origin provenance assertions, and the version probes running from
   the lane directory (the coordinator ledger C-F2 documents a checkout-import
   trap; the executed script is correct — confirm). Confirm the terminal driver
   records `skill_lens_file` inside site-packages and `driver_cwd` outside the
   checkout, and its restore-sequence draining logic (macOS EIO note) is sound.
5. **Mutation load-bearingness (independent spot-rerun).** In a fresh copy of
   the repository under /tmp (copy only; never write into the checkout),
   independently rerun at least THREE of the 23 recorded mutations of your
   choosing — at minimum one manifest omission, one selection drop, and the
   legacy-parser restoration — each must fail the named guard with the expected
   behavioural assertion (not an import/collection error), and restoring must
   pass again. Also design ONE new mutation the implementer missed, if you can,
   and test it.
6. **Timeout and budget discipline.** The 300 s installed-suite bound and its
   partial-output error handling are unchanged; lane runtimes (~88–90 s) leave
   margin; r3 receipts show the same counts as r1 (461/0). Flag it if the margin
   or the evidence would mislead a maintainer on slower hardware.
7. **Quality gate.** Coverage stayed at 90.10% with 41 added test items; no
   existing test was weakened (compare against `git --no-pager diff da2b8d9 --
   tests/` — removals/edits of pre-existing assertions would be blockers unless
   justified).

Report blockers only with location (`path:line`), problem, expected behaviour
and concrete evidence (your rerun's command + output). Without evidence it is a
suggestion. Do not run any test against the user's real `~/.claude`,
`~/.agents` or `~/.codex`; the suites use synthetic homes, and your /tmp copies
inherit that.

## Report format (exactly these fields, nothing else)

EFFECTIVE_MODEL: [ provider/model, settings, runtimeMode, interactionMode | evidence: requested vs configured vs confirmed/unverified — for perch, quote the run JSON receipt fields; mark the model's own self-identification as narrative-only ]
VERDICT:         pass | changes_required | unverified
BLOCKERS:        [ location, problem, expected behaviour, evidence ]
SUGGESTIONS:     [ ... ]        non-blocking
FILES_AT_RISK:   [ ... ]
CONCEDED:        [ ... ]        points withdrawn after argument
