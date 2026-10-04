# Full-screen TUI plan — earlier review history

These are the four review summaries formerly carried in the plan header.
They record earlier revisions, including claims later corrected. The current
design and readiness gates live in [FULL_SCREEN_TUI.md](../../FULL_SCREEN_TUI.md);
consult its sections 20–22 before implementation.

> **Reviewed:** 2026-10-04 — independent read-only review by Gemini 3.8 Flash
> High via `agy` (`--read-only`, zero violations). Four blocking issues were
> raised and are folded in below: the Home screen's non-existent global
> resolution state ([§8.3](../../FULL_SCREEN_TUI.md#83-home-screen-layout)), the base-install regression
> from hijacking bare invocation ([§6](../../FULL_SCREEN_TUI.md#6-technology-choices)), the "held
> snapshot" that did not hold what the UI needs
> ([§5.1](../../FULL_SCREEN_TUI.md#51-what-the-tui-holds-in-memory-corrected)), and the CI/coverage gap
> ([§6.1](../../FULL_SCREEN_TUI.md#61-ci-must-test-both-installs-corrected)). One correction to the
> reviewer: `build_diff_report()` already accepts an `index` keyword, so the
> held state is the `DiscoveryIndex` — better than "recompute on demand".
>
> **Second review (orchestrator, same day), against the source.** Three further
> defects were found and folded in: `run_doctor()` *also* lacked an `index`
> parameter and the "only change to core/" claim was wrong
> ([§5.1](../../FULL_SCREEN_TUI.md#51-what-the-tui-holds-in-memory-corrected)); the live index must come
> from `live_discovery()` or the TCC guard is lost
> ([§5.2](../../FULL_SCREEN_TUI.md#52-the-session-index-must-come-from-live_discovery)); and Textual
> pins a much newer Rich than this project declares, which can move our pinned
> snapshots ([§6.2](../../FULL_SCREEN_TUI.md#62-rich-is-a-shared-dependency-coupling-risk)).
>
> **Third review (orchestrator, 2026-10-04), against the source and the repo.**
> Six further defects were found and folded in: the shared display maps were
> homed in `models/enums.py`, which mixes Rich styles into the pure model layer
> ([§8.4a](../../FULL_SCREEN_TUI.md#84a-sharing-the-presentation-layer--a-refactor-this-plan-must-budget));
> the sharing refactor was under-scoped to two dicts when several diff/why text
> builders are also private to `render.py` (same section); the bare-invocation
> wiring was described but never specified
> ([§7.2](../../FULL_SCREEN_TUI.md#72-how-bare-invocation-is-wired)); the two `index` defaults contradicted
> each other ([§5.1](../../FULL_SCREEN_TUI.md#51-what-the-tui-holds-in-memory-corrected)); the §5.1
> entry-point table omitted two builders that already accept `index` (same
> section); and the coverage gate has only three points of headroom
> ([§6.1](../../FULL_SCREEN_TUI.md#61-ci-must-test-both-installs-corrected),
> [§14](../../FULL_SCREEN_TUI.md#14-risks-and-mitigations)). A note on repository state before Step 0 is
> in [§11](../../FULL_SCREEN_TUI.md#11-implementation-phases-phase-7).

> **Fourth review (Codex, 2026-10-04), against code and temporary fixtures.**
> The held index is not a complete snapshot; folder names are not lookup keys
> for every agent; some proposed shared helpers contain Rich markup; worker
> refresh/error behaviour needs an explicit contract; and two malformed-file
> crashes need prerequisite fixes. Dependency, startup-measurement, repository
> state, default-invocation and clipboard claims were also corrected below.
> The earlier review summaries are historical: this revision supersedes their
> claims that the adapter alone provides permission guards and that Textual
> pins Rich exactly. The finding checklist is in §20.

