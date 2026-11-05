# Sanitization note — U9 evidence (pre-publication privacy pass)

Date: 5 November 2026. On the owner's instruction before publishing 0.2.0,
the coordinator replaced personal-machine strings across every file under
`docs/validation/u9/`:

| Was | Now |
| --- | --- |
| `/Users/corvette/Documents/Projects Coding/Skill Lens` | `<REPO_ROOT>` |
| `/Users/corvette` | `<HOME>` |
| `corvette@MacBook-Air-Hazem.local` | `<USER>@<HOST>` |
| `pytest-of-corvette` (temp-dir fragments) | `pytest-of-<USER>` |

89 + 21 files changed. Every `.json` under this folder re-parses after the
edits; residual searches for the old strings return nothing here.

**Artifacts are unaffected.** `docs/validation/u9/` is deliberately excluded
from every build export (`qualify_candidate.py` removes it before building),
so the r4 wheel and sdist — whose bytes live only under the retained external
build directory — are unchanged by this pass; the supersession note's hashes
remain exact.

Deliberately **not** touched, disclosed for a possible future scrub mission:

1. Older validation evidence outside this folder (pre-U9 waves) contains the
   same local paths; several files' contents are cross-checked by SHA-256
   values inside sibling receipts, so silent rewriting would break the very
   verification those receipts exist for.
2. `docs/validation/omp-coordinator/2026-10-22-herdr-investigation/source/`
   holds vendored third-party data (including git-object author emails) pinned
   by its own integrity manifest — editing it would falsify investigation
   evidence.
3. Git **commit metadata** of already-pushed commits carries the account's
   author email and, for early commits, a machine hostname. History rewriting
   is not performed by this mission and would need its own explicit decision.
