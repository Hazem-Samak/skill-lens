# Final MiniMax R1 disposition

Sol accepted and independently reproduced the sole blocker. The reviewer probe
passed against the shipped source and failed against the planted token-clearing
mutation. The reproduction log is `rejected-token-reproduction.log`.

DeepSeek added an event-controlled regression that observes the rejected callback
while a newer request remains blocked, checks the exact owned token and active
controller request, and then proves the queue drains. The sixth mutation replaces
the rejected-outcome branch with `self._inflight = None`. Sol's independent
six-case run detects all mutants and all restored controls pass. Product source,
the benchmark, other tests and README remain byte-identical to the R1 candidate.

The harness now accepts `--out` for external receipts. Current documentation
points at the named benchmark receipt and omits a volatile formatter file count.
The R1 `review-ready/` logs and receipt are historical gate-execution evidence;
later Markdown evidence additions change the formatter's inventory without
changing product code. They are preserved rather than rewritten to a later count.
Current evidence is under `review-ready-r2/`.

The unused error parameter and the package's U2-era header/export suggestion are
nonblocking and deferred: changing the product interface or exports adds no
acceptance value to this test-only correction. U4 may revisit them with its
dedicated Why-screen integration. No known product defect is being deferred.

No scope or frozen-contract amendment is needed. Independent targeted R2 and Sol
acceptance remain required. Human visual approval and publishing are not claimed.
