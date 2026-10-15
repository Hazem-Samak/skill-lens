# Stage D first council evidence — coordinator receipt

Status: Under review; NOT accepted.
Frozen contract: docs/plans/2026-10-12-assessment-repairs.md @ fe6f89bc55eb3f4f04187567b968dd96ae9c86c1.
Base: 249057601637d90b436e9313e8532ce44ed5f57c.
Coordinator: Codex gpt-6.1-sol/high, Full access/default.
Implementer: Antigravity gemini-3.8-flash-high. Three implementation tasks are terminal with no pending child runs. Requested/configured identity is corroborated by T3; provider-served identity remains unverified. Some worker reports overclaim identity/readiness.

Independent checks on the current source/test/config tree: 904 passed, one physical dual-case filename skip, 90.44% combined coverage; strict mypy 36 files; Ruff lint/format clean. Actual coordinator logs and receipts are adjacent. These are local macOS/Python3.11 results, not all CI lanes. The preceding tree had 89.51% coverage and was rejected even though pytest returned exit0; actual output/threshold was inspected.

All ten previous targeted coordinator reproductions now match their expected output. The print-only scripts are diagnostic examples, not asserted tests; the worker's initial 20/20 pass claim was not test proof.

Four guards were independently mutated in a verified disposable source copy with import provenance, exact source mutation diff/hashes, actual intended AssertionError failures, and clean/mutant/restored exits 0/1/0: frozen Codex lookup, declared Claude settings identity, OpenCode ancestor precedence, and invalid Claude override status. This receipt establishes four coordinator-verified proofs, not an exhaustive mutation score. Worker receipts report ten mutations with retained assertion excerpts/current hashes; their provider-owned temporary sources no longer exist. Treat those as reported evidence with that limitation.

Known boundary findings independently reproduced in coordinator-reviewed-r2-boundaries.json (scratch /var/folders/tf/jsdyxcts6y72fs98s7wl3dfm0000gn/T/skill-lens-stage-d-resume-20261013-bt9bpeqe/reviewed_r2_boundaries.py):
- Codex disable config naming an alternate symlink path into a discovered skill: live DISABLED versus captured ACTIVE. Live acquisition resolves config path while captured decoding does not.
- OpenCode deny config above a Git boundary: ACTIVE/allow, no limitation note, although V2 config documentation searches higher ancestors.
- Qoder retained .agents compatibility root: ACTIVE/loadable, no qualification; its vendor loadability remains unverified in Stage C/D records.
- OpenCode metadata autoinvoke true with no description: invocation all, despite unadvertised missing-description behavior.
- Explicit disabled_overrides containing a supported Claude folder alias is not applied after hybrid identity (check prior API contract, distinguish this from settings-file command matching).
- A skill beyond the V2 depth cap is silently absent with only no-copy-found note; evidence says truncation guarded but no runtime disclosure exists.
- Doctor still says OpenCode will skip a plain optional-frontmatter skill; health classifier supplies malformed_yaml, so the new missing_frontmatter consumer branch is not reached.

These are evidence for the first independent review, not resolved/deferred issues. Neither council verdict nor green gates is coordinator acceptance. The council must independently determine blockers, scope and required corrections. Two non-converged council rounds require escalation; earlier A/B/C focused exceptions do not apply to Stage D.

Allowed edits remained confined to necessary Stage D core/models/registry/tests/fixtures/evidence; unchanged .path preserved. U3-U9, E-H, release/dependency/resource policy are excluded. Full diff including untracked config/test/evidence files: /var/folders/tf/jsdyxcts6y72fs98s7wl3dfm0000gn/T/skill-lens-stage-d-resume-20261013-bt9bpeqe/stage-d-complete.diff. Before-wave status/fingerprints: /var/folders/tf/jsdyxcts6y72fs98s7wl3dfm0000gn/T/skill-lens-stage-d-resume-20261013-bt9bpeqe/council-r1-before.json (refresh follows this administrative receipt). No product code was written by the coordinator.

