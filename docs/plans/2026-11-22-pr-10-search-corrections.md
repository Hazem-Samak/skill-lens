# Plan: Correct Skill Lens search before merging PR #10

Status: Agreed

Authorization: The maintainer requested the reviewed corrections to PR #10 in T3 Code, with one implementer, the coordinator as sole reviewer, and a separate merge decision. The existing PR is the delivery target. The reviewed starting commit is `343f1b47af25097c988424bea4cf6a20c6103242`.

Roster: Codex GPT-6.2 Sol High coordinates and reviews. Pi River DeepSeek V4.1 Flash 1017 Max implements. This is a high-risk change because it touches search results and file reads. The maintainer chose direct coordinator review for this correction.

Reference: 7341cd53983a42581a5b34d43512872298a08943

## Outcome and scope

- Keep search read-only and based on one discovery pass. Apply the existing 256 MiB payload limit to CLI search. Count discovered skill payloads once per canonical copy, including support files, and reject oversized inventories clearly before reading the oversized payload. Bound actual skill-document reads, including standalone qualification, so file growth cannot cause an unbounded read. Keep existing root, symlink, error and hash behavior unless needed for bounded search. Preserve existing commands and the TUI capture policy. Report refusal on stderr with a nonzero status and no partial output.
- Report resolution per reachable agent and lookup name using the existing resolver and discovery index. With `--agent`, a match against an agent's exact usable alias must show that alias's state and agree with `why`. Keep the selected-agent `state` field and make mixed states explicit. Without `--agent`, expose states by agent and name, since one copy can have different states. Ensure terminal users can see all reachable agents and applicable states without a permanent column cap. JSON must carry the full names and states in a stable shape.
- Keep ordinary Unicode body and description matches visible in excerpts even when earlier characters expand during case folding. Keep the existing length limit and safe literal text rendering. Pin a portable border style, review the output diffs, and update the packaging parity guard to cover the three search snapshots.
- Update the search specification and user documentation where these repairs change the behavior described. Keep changes within search, bounded discovery dependencies, the relevant renderer, and their tests. Preserve the existing Home text filter.

## Acceptance

- Reproduce the alias collision against `why`, state differences across agents, a Unicode query after an expanding prefix, full agent display, and bounded rejection with unchanged fixture bytes. Cover an oversized document and an oversized support file, under-budget results, a repeated alias, and the existing early-validation behavior.
- Read the search snapshot diffs before accepting them. The initial macOS run at the reviewed commit had 1,482 passes, one skip, and four expected failures (three search snapshots and the packaging snapshot count). Type, lint and format checks passed. On the finished change, all four local verification gates must pass in a temporary home, followed by hosted checks at the pushed commit.
- The implementer returns changed paths, verification, effective model evidence and any unresolved issue. The coordinator reviews, verifies, and makes the delivery commit. The maintainer will decide when to merge.
