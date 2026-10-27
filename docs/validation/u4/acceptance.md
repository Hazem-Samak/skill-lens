# U4 Why screen — local technical acceptance

Date: 27 October 2026. Frozen operative plan: `docs/plans/2026-10-26-tui-u4-why.md` at `684cdb7aa0e3a28e5bb722bf65e4f3953edc6f76`.

## Scope and behavior

U4 adds a dedicated Why screen opened with Enter from a focused, nonempty Home table. It displays captured resolution candidates, evidence, paths and agent choices; supports keyboard navigation and expansion; and returns to Home with its filter, cursor, selection and focus preserved. Refresh publishes a new captured session explicitly. Covered Home work is suspended, worker results are accepted only for their owning request, and detail cleanup runs before returning Home. Long content and status are reachable through one vertical scroll area at 100×30 and 60×24.

Skill Lens remains read-only against target files. No core, controller, model, registry, presentation, CLI or dependency implementation changed. No snapshots/goldens were regenerated. U5–U9, human visual approval, hosted CI acceptance, release and publishing are outside this local acceptance.

## Roster and independent review

Coordinator: Codex `gpt-6.1-sol`, Medium. Authorized implementer: Antigravity `gemini-3.8-flash-high`, replacing the owner's original Nemotron route after provider failures and quota exhaustion. Critics: MCode MiniMax M3.1 Flash thinking/High and River/Pi DeepSeek V4.1 Flash 1017 thinking/High. These are requested/configured route identities; upstream serving/weight attestation was not available. Distinct family names alone are not attestation.

The implementation went through independent review and bounded correction. Preserve every historical verdict:

- [DeepSeek bounded final report](implementation/coordinator/deepseek-bounded-final.md): pass. It independently reproduced layout readability, three genuinely pending Home groups during refresh, the four requested display/mapping assertions, quality gates and the eleven then-existing mutations.
- [MiniMax bounded final report](implementation/coordinator/minimax-bounded-final.md): changes_required. It confirmed those fixes and found B1: the layout test rewrite had removed navigation assertions, allowing three previously detected navigation mutations to survive. Current product behavior was correct in its probes.
- [Checkpoint](implementation/coordinator/bounded-final-safe-stop.md): the coordinator stopped as authorized and presented the concrete remaining correction. Owner then replied: "yes a final authorization no problem".

The coordinator directly performed that small final review correction under the T3 instruction to fix small findings without another delegate. Restored assertions cover candidate-focused arrows, Shift+Tab and return traversal, and focus following strip selection at both terminal sizes. The Tab search is bounded to twelve presses. Three disposable navigation mutations now fail for the intended behavioral assertions; all restored copies pass. No product code changed in this final correction. MiniMax's report remains changes_required historically; it is not represented as a later independent pass. Coordinator adjudication: B1 resolved by direct discriminating evidence. The earlier independent product review remains applicable to unchanged product hashes.

## Verification and limits

Current execution receipt: [final correction verification](implementation/coordinator/final-correction-verification.json). Full test log: [pytest](implementation/coordinator/final-correction-pytest.log). Expanded mutation receipt: [revision 5](implementation/mutation_gate_r5.json), fourteen detected mutations, nine passing controls, all restores passing and product hashes unchanged. The test module retains 41 functions / 42 collected cases.

The [current mapping](implementation/acceptance_mapping_r4.md) narrows exact path-display claims to header/canonical strings actually exercised. Entrypoint presence/suppression is tested separately; exact entrypoint display-path formatting remains implementation-only in the identity fixture. This is disclosed rather than claimed as covered. The older r3 mapping is marked superseded. Narrow terminals may require scrolling past a tall agent strip, as allowed by the frozen wrap-or-scroll requirement.

All reviewer tasks are terminal without pending children or questions. The coordinator verified all 2380 pre-review manifest files unchanged after review; final authorized changes are limited to tests, the mutation harness, documentation and execution records. Unrelated user paths remain untouched and excluded from delivery.

Local technical acceptance requires the four final gates in the linked receipt to pass. Git delivery is recorded separately; no hosted CI or release success is inferred from local tests or a push.
