# Coordinator concerns for independent review R1

Both reproduced product bugs C1/C2 now pass their external probes. Whole-repo Ruff initially caught unformatted coordinator evidence; coordinator formatted that evidence only. Product/source/tests were not changed by coordinator. Direct full gates and fresh mutations accompany the reviewed source fingerprints.

The implementer report and acceptance_mapping_r2.md are claims to audit, not acceptance authority. Some mapped test selectors do not exist, and sys.monitoring is claimed without use. Preserve historical claims and record errata; require actual evidence before acceptance.

Specific remaining concerns from source inspection:

1. tests/test_tui_why.py:1313-1413: frozen/preservation test records before but ends only with len(before)>0. It performs only a conditional file write, with no assertion it happened; no deletion/shortcut retarget, no expected report/render parity, no after-manifest comparison. Does not prove its claimed preservation/full data-freeze acceptance.
2. :1421-1500: test name claims directory/frontmatter/unresolved identity, but creates two manually constructed candidates and assigns a synthetic report. No distinct-name fixtures or agent-specific snapshot_why comparison.
3. :782-821: non-capture accepted-event test posts request 123 for diff with no active diff request registered; controller should reject it. It also uses Home All filter, so hidden Home has no work to cancel. Verify actual accepted event/active detail token/filtered pending Home instead.
4. :496-665: real-worker tests use time pauses after releasing workers without acknowledged outcome completion; test docstring says stale success/error but workers only return successful reports. Cancellation events not asserted. Pending-capture test does not keep Home agent-filter queue pending or assert exact unchanged detail token before publication. Determine exact frozen proof gaps.
5. :1236-1307: All-filter return matrix sets controller fields manually and never verifies app exit result; it omits changed count and a true still-running capture. Existing real capture error test covers actual exceptions but does not return Home per each state.
6. :1553-1600: layout test uses ordinary short fixture; checks only focus not None after Tab. No long content, focus destination, toggle result, viewport geometry/reachability/scroll assertions.
7. Scope/style: Home CSS changes include catalog warning color and narrow height; determine whether justified integration or unrelated cleanup. Detail lacks lifecycle suspend cleanup except unmount; opening/back covers only ordinary path. Home on_input_changed/on_input_submitted/action_clear_filter still have no suspended guard. Removal notice doesn't clear on r refresh. Detail strip reconciliation appends surviving/new IDs without reordering if eligibility changes; inspect deterministic order after refresh. Potential product defects require concrete proof, not automatic blocker labels.

These are observations and review questions; reproduce product defects and report actual frozen-contract gaps, consolidate duplicates, distinguish blockers from optional polish. No outside-scope widening. Both independent reviews required before acceptance.
