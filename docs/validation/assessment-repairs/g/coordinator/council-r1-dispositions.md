# Stage G first council dispositions and round-two focus

Both first-round critics returned pass without listed blockers. MiniMax identified four assurance gaps as suggestions; the coordinator reproduced all four as clean/mutant/restored 0/0/0 and treated them as required gate repairs. No finding was deferred based merely on its label.

1. Removing installed-origin checks survived: corrected tests cover base origin and each endpoint origin branch independently.
2. Removing Textual absence assertion survived: corrected test executes the actual generated child Python check with Textual present.
3. Ignoring failed installed pytest exit survived: corrected test requires lane rejection on nonzero suite exit.
4. Removing source-copy guard survived: corrected test contaminates the copied test lane and requires rejection.

Gemini changed only tests/test_tui_packaging.py after round one. Full correction delta is coordinator-r2/correction-only.diff. Unchanged product, CI and prior reviewed tests are fingerprint-verified. Current complete eight-file diff is coordinator-r2/complete-product-test.diff. Final coordinator 20 mutations include all original fourteen plus six independent checks for these corrected guards. Each clean/mutant/restored is 0/1/0; the failure logs show behavioral assertions rather than syntax/import errors. Current source hashes match.

Muse's non-blocking suggestions: disclose floor/latest overlap and private API semantic-drift limit; do not claim Linux or full Python matrix execution. Optional fallback simplification was not necessary to meet the frozen contract. These limits remain explicit.

No unresolved reported blocker. Coordinator acceptance is still pending round two; reviewer reports are evidence rather than automatic acceptance. No product behavior, dependency policy or frozen scope changed.

Other MiniMax suggestions remain non-blocking: packaged-byte equality is coordinator evidence, not a harness feature claim; cold-cache timing/PATH inheritance remain bounded risks with absolute lane executable paths and actual fresh-install success; historical version docstring, exact ten-registry contract, unused convenience flag and copied test bytecode are optional cleanup rather than current contract defects. No broader CI/platform success is asserted.
