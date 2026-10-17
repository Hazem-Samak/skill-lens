# Phase-B preflight review adjudication — round 1
Scope: correct preflight evidence and handoff only. No pilot or Phase-C migration acceptance.

Both critics found blockers. DeepSeek's prose says "conditional pass" but lists required fixes; coordinator records it as changes_required, not acceptance. MiniMax's T3 terminal summary lacked the report; durable activity identified its canonical plan.md artifact. Coordinator recovered that full six-field report; its verdict is changes_required. No additional review round was inferred from a narration-only response.

## Confirmed corrections
- Ruff format count is187 in the retained frozen baseline, not184 copied from drafting.
- Bare github.com commit links need actual repo commit URLs.
- Startup must not start an agent in the calling pane via an RPC that requires an available prompt, then assume that pane remains a control shell. Use direct interactive Hermes launch in a real Herdr shell and paste/read its explicit brief there, or demonstrate a separate owned control-pane sequence. Label unrun commands proposed.
- Canonical external checkout exists NOW at /tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout, with fixture.txt baseline recorded in external fixture-manifest.json. It was prepared after reviewers' initial path check; this is preparation, no pilot execution/model call.
- Pi --tools allowlist alone keeps MCP. Proposed settings must include --no-mcp; retain only installed Herdr extension explicitly with --no-extensions -e /Users/corvette/.pi/agent/extensions/herdr-agent-state.ts, skip discovered skills/context, and use fresh session storage. Inspect source: no registerTool/provider calls were found in that state extension. Still not a filesystem jail; guard/fingerprints/live tests remain required.
- Do not claim Hermes --in, agy --add-dir/project, context flags or HOME changes enforce filesystem confinement. Keep agent authentication/session context distinct from synthetic HOME/XDG for exercised fixture commands; no copying credentials or live skills. agy --sandbox is a help-advertised terminal restriction, not empirically certified containment.
- Absolute /Applications/cmux.app/Contents/Resources/bin/cmux works; no persistent PATH change is necessary. Never launch Contents/MacOS/cmux as a CLI.
- Herdr config theme key was misquoted; record only actual safe UI values or omit unnecessary config details. Availability of listed flags is not a live test.
- P01-P09 remain pending. Missing human startup/session+mapping approval is real under frozen sections4.4-5. Last overnight continuation does not silently amend those restrictions.

## Native route research adjudication
Confirmed: installed Herdr kind enum lacks mcode/minimax; mastracode is a distinct canonical executable, not a MiniMax alias. No valid same-selected mcode route was established in the inspected Pi/Hermes configuration. This does NOT prove every possible route globally impossible. Do not enable a provider, change route/model, alias another kind, install a wrapper, or claim a permanent roster amendment is already authorized.
Research's blanket Pi-readonly claim conflicts with actual --tools help; use explicit --no-mcp and scoped extension retention proposal. Its global-config-required/credential-availability claims exceed proven facts; do not present speculative enable-provider commands as a working remedy. Preserve raw report with this correction.
Migration's final reviewers remain T3 MiniMax+mcode and Pi+DeepSeek. Any Herdr pilot role change is separate, explicit and subject to the frozen amendment/selection procedure.

## Acceptance boundary
Accurate, two-reviewed preflight checkpoint is useful progress, never trial-ready/full migration acceptance. PhaseC active process files remain untouched until required pilot cases pass. Obtain minimal concrete user decision for actual lifecycle/roles only after the corrected proposal is reviewable; do not broaden machine authority or invoke a live session from this T3 process.
