# U9 final review — round 2, reviewer 1 (targeted follow-up)

You are re-reviewing after your round-1 report on the U9 implementation
(packaging, compatibility and claim accuracy; risk High). You previously
returned **changes_required** with one blocker (C-F7) and four suggestions.
The coordinator applied corrections; this round verifies closure. Everything
from your original brief still governs: same repository
(`<REPO_ROOT>`, HEAD `da2b8d9`, work
uncommitted), same frozen plan
(`docs/plans/2026-11-05-tui-u9-release-preparation.md` @
`f3c652beed4e7b5b745a77a900cc1e93f5a5f105`), same diff command
(`git --no-pager diff da2b8d9`, still exactly ten tracked files), same scope
rules, same disclosed limitations.

READ-ONLY CRITIC TASK. You are reviewing, not implementing.

Do NOT create, edit, move, delete or rename any file in the repository. Do NOT run
any command that writes: no formatters, no linters with --fix, no install, no
git commit/checkout/stash, no snapshot or golden regeneration, no test runs that
write into the checkout. Test output, if you need it, goes only to a temporary
directory outside the repository.

If you believe a change is required, do not make it. Report it instead.

Return only the report format below. Nothing else.

## The blocker you raised, and the disposition

**C-F7 (accepted):** all five status documents pointed only at
`docs/validation/u9/implementation/`, whose receipts hold the invalidated r1
source-archive hash; the rebuilt-candidate receipts live in
`docs/validation/u9/coordinator/precommit/` and nothing pointed there.

Coordinator corrections (see
`docs/validation/u9/coordinator/precommit/adjudication-wave-a.json` for the
full ledger):

1. Every one of the nine pointer sentences in README, CHANGELOG (two),
   DEVELOPMENT, FULL_SCREEN_TUI (four) and the specification now names BOTH
   folders — "(first wave)" and "(rebuilt candidate; see the supersession
   note)".
2. A new append-only `docs/validation/u9/implementation/SUPERSESSION.md`
   explains the r1→r2→r3 invalidation chain, records each wave's exact wheel
   and sdist SHA-256, states r1 files were not rewritten, and directs readers
   to the highest-numbered wave.
3. These documentation edits are themselves packaged changes, so the whole
   candidate was rebuilt again: the **r3 wave** receipts
   (`candidate-r3.json`, `install-receipt-r3.json`, `version-probes-r3.json`,
   `terminal-receipt-r3.json`, `final-*-r3.log`) under
   `docs/validation/u9/coordinator/precommit/` are the live evidence; r2 is
   superseded the same way r1 was. Artifacts are retained at
   `/tmp/u9-candidate-r3/` (readable, outside the repo).

## Your suggestions, and dispositions

- **S1 (mkdir -p missing in the export snippet): accepted.** Both the generic
  Releasing step 3 and the U9 checklist step 1 now create `$work/src` and
  `$work/artifacts`.
- **S2 ($root/$work undefined at generic step 3): accepted.** The step now
  defines them at first use.
- **S3 (contradictory probe comment): accepted.** The comment is rewritten:
  the script itself is safe to launch from anywhere; what must be outside the
  checkout is each lane interpreter's working directory.
- **S4 (manifest recording not shown at step 1): accepted with a pointer** —
  step 1 now says `qualify_candidate.py` records the export manifest and
  overlaid input hashes into `candidate.json`.

## What to verify (your single question, narrowed)

Does the wave-A closure restore claim accuracy, without introducing new
inaccuracies? Specifically:

1. Do all nine pointer sentences resolve, name both folders, and keep README's
   links absolute (the `test_readme_has_no_relative_links` rule)?
2. Is `SUPERSESSION.md` accurate against the receipts — recompute at least the
   r3 wheel and sdist hashes yourself (`shasum -a 256` on
   `/tmp/u9-candidate-r3/artifacts/*`) and confirm they match
   `candidate-r3.json`, `install-receipt-r3.json`, `terminal-receipt-r3.json`
   and the supersession note; confirm the wheel CHANGED from r1/r2 (README is
   now inside the wheel metadata) and that the note says so.
3. Do the corrected DEVELOPMENT snippets now run cleanly as written (mentally
   execute with fresh variables; flag anything still misleading)?
4. Still true: exactly ten tracked files changed, no product behavior change,
   no CI/dependency/policy change, snapshots/goldens untouched, gates r3 green
   (read `final-*-r3.log`; 1379/1 expected), acceptance wording still withholds
   the final states, "Not published" claims unchanged.
5. Anything your round-1 pass items should now re-check given the new README
   bytes (wheel metadata Description embeds it): the claim sentences in README
   remain truthful and the metadata in `candidate-r3.json` is consistent with
   them.

If closure is satisfactory and you find no new blocker, return VERDICT: pass
with any remaining non-blocking suggestions. Blockers still need
`path:line` + evidence.

## Report format (exactly these fields, nothing else)

EFFECTIVE_MODEL: [ provider/model, settings, runtimeMode, interactionMode | evidence: requested vs configured vs confirmed/unverified — quote your exec JSON receipt fields; mark self-identification as narrative-only ]
VERDICT:         pass | changes_required | unverified
BLOCKERS:        [ location, problem, expected behaviour, evidence ]
SUGGESTIONS:     [ ... ]        non-blocking
FILES_AT_RISK:   [ ... ]
CONCEDED:        [ ... ]        points withdrawn after argument
