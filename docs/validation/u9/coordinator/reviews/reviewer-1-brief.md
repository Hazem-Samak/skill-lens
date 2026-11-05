# U9 final review — reviewer 1 axis: packaging, compatibility and claim accuracy

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
- The complete change: `git --no-pager diff da2b8d9` — exactly ten tracked
  files: `pyproject.toml`, `skill_lens/__init__.py`, `uv.lock`,
  `scripts/smoke_wheel.py`, `tests/test_tui_packaging.py`, `README.md`,
  `DEVELOPMENT.md`, `CHANGELOG.md`, `FULL_SCREEN_TUI.md`,
  `SKILL_LENS_SPECIFICATION.md`. Untracked evidence lives under
  `docs/validation/u9/` (implementation r1 + coordinator r2).
- Coordinator corrections recorded BEFORE your review in
  `docs/validation/u9/coordinator/precommit/coordinator-corrections.json`
  (findings C-F1..C-F6, before/after hashes). Only `CHANGELOG.md` and
  `DEVELOPMENT.md` changed in that wave; r1 hashes for all ten files are in
  `docs/validation/u9/implementation/inputs.json`.

## Current check results (coordinator, this tree)

- r2 gates after corrections: logs under
  `docs/validation/u9/coordinator/precommit/final-*-r2.log` (read the receipts).
- r2 candidate rebuilt from a clean export after the doc corrections:
  `docs/validation/u9/coordinator/precommit/candidate-r2.json`,
  `install-receipt-r2.json`, `version-probes-r2.json`,
  `terminal-receipt-r2.json`; artifacts and lane environments retained at
  `/tmp/u9-candidate-r2/` (outside the repo, readable).
- r1 evidence (original implementer run) under `docs/validation/u9/implementation/`.
- Disclosed limitations (do not re-report as findings unless wrong): minimum
  and latest Textual lanes both resolve 8.2.8 because 8.2.8 is today's latest;
  wheel bytes are not bit-reproducible (per-file content identity is verified);
  local runs are macOS / Python 3.11.16 only; human visual approval and
  candidate-commit hosted CI are deliberately pending.

## Your single review question

Does this change satisfy the plan's packaging, compatibility and
claim-accuracy requirements (A1–A3, A8, A9 boundaries), such that the
documents tell the truth about what was verified?

Concretely:

1. **Version and lock (A2).** `pyproject.toml`, `skill_lens/__init__.py` and
   the `uv.lock` root package all read 0.2.0; the lock diff is the root version
   line only; the `textual>=8.2.8` floor, Python range, wheel target, console
   script and all dependency pins are otherwise unchanged.
2. **Archive correctness (A3).** The 12-module manifest matches the shipped
   `skill_lens/tui/*.py`; the r2 receipts' wheel/sdist hashes match the actual
   files in `/tmp/u9-candidate-r2/artifacts/` (verify with a hash command
   writing only to /tmp); metadata (name, version, extra, entry point) is
   consistent across wheel, sdist and `pyproject.toml`; packaged bytes equal
   the export.
3. **Claim accuracy across the five documents (A8).** Published-vs-candidate
   distinctions are correct everywhere; no sentence advertises a published PyPI
   TUI; the U8 CI run is only ever cited for U8; launch-rule and fallback
   wording matches `FULL_SCREEN_TUI.md` §7 and the stream matrix in
   `tests/test_tui_routing.py`; the changelog keeps 0.1.0/0.1.1 history intact,
   has no tag link for the unpublished 0.2.0, and its "Verified for this
   candidate" bullets match the receipts; README keeps absolute links only.
4. **Release-process documentation.** After correction, are the DEVELOPMENT.md
   generic Releasing steps and the 0.2.0 candidate qualification checklist
   executable and safe (clean-export build, probes run outside the checkout,
   tag after upload)? Try each snippet mentally with a fresh maintainer's cwd
   and flag any command that would mislead or write into the checkout.
5. **Scope (A1).** Nothing outside the allowed file table changed; no CI,
   dependency, coverage-threshold, process or product-behavior change;
   `git --no-pager diff da2b8d9 --stat` accounts for every file; `tests/fixtures`
   untouched (no snapshot/golden regeneration).
6. **Review-authority boundary (A9).** Acceptance language in the tree now
   withholds "locally technically accepted" pending two independent reviews;
   publication is stated as separately authorized. Note the implementer report
   line C-F6 is a superseded label inside an append-only record; judge whether
   the ledger disposition is sufficient.

You may additionally read anything needed to prove a concern
(`docs/process/council.md`, `AGENTS.md`, `SKILL_LENS_SPECIFICATION.md`,
`FULL_SCREEN_TUI.md`). If you must run tests, copy the repository to a fresh
directory under /tmp first; never write into the checkout.

Report blockers only with location (`path:line`), problem, expected behaviour
and concrete evidence. Without evidence it is a suggestion.

## Report format (exactly these fields, nothing else)

EFFECTIVE_MODEL: [ provider/model, settings, runtimeMode, interactionMode | evidence: requested vs configured vs confirmed/unverified — for mcode, quote the exec JSON receipt fields and any banner; mark the model's own self-identification as narrative-only ]
VERDICT:         pass | changes_required | unverified
BLOCKERS:        [ location, problem, expected behaviour, evidence ]
SUGGESTIONS:     [ ... ]        non-blocking
FILES_AT_RISK:   [ ... ]
CONCEDED:        [ ... ]        points withdrawn after argument
