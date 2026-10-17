# Proposed narrow correction for user decision after review round 2

Status: Historical proposal; not applied. The user accepted the existing checkpoint and waived DeepSeek findings for this round. No additional review wave was dispatched. See native-mapping-user-acceptance-20261017.md.

The frozen base and amendment, models, permissions and human lifecycle stay unchanged.

Add to the existing P03 independent verification step, before computing the hash supplied to fresh critics:

```python
from pathlib import Path
import hashlib

expected = b"pilot status: synthetic implementation complete\n"
actual = Path(
    "/tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout/fixture.txt"
).read_bytes()
assert actual == expected, "STOP: fixture does not equal the intended edit"
assert (
    hashlib.sha256(actual).hexdigest()
    == "ae5bd0b0accf1386be898f62f94653335d304bb532f3514b5fd809ce334688e7"
)
```

Add before the first worker/critic submission and apply to every report:

> Save a pre-submission capture and the exact submitted brief. Recover and retain the complete generated assistant report after the correlated submission, distinguishing it from echoed input and older terminal-buffer content. Verify substantive required fields and token, path and target hash against the dispatch record. Token/hash matching alone is insufficient. If the native capture cannot establish that this is the complete fresh assistant response, mark the required capability unavailable and stop; do not accept it, blindly resend, or add write/shell tools. P04 must demonstrate this boundary, including long-response completeness, for the selected roles.

Keep the existing running/idle worker requirement and direct human Hermes procedure; no duplicate startup or permission change is needed. Optionally clarify that the direct coordinator proves Herdr interaction by issuing documented subcommands from its genuine pane, with no agent-start RPC required. Also correct stale administrative gate notes and label mkdtemp suffix spelling.

Recommended disposition: Gemini applies these narrow documentation corrections; Sol verifies; MiniMax and DeepSeek perform one explicitly authorized targeted follow-up on these changes and the disputed findings. Any remaining blocker is reported without silently expanding the review loop. No runtime acceptance or publication is implied.
