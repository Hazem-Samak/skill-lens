#!/usr/bin/env bash
# Reviewer 2 ROUND 1 RETRY (perch, non-interactive approval policy auto_review;
# deviation ledger in approvals.json + adjudication-wave-a.json: requested
# glm-5.3-flash-starter/max unverifiable on this account — served model is
# Perch auto-failover, effort capped to high; owner said continue with perch).
set -u
E="/Users/corvette/Documents/Projects Coding/Skill Lens"
D="$E/docs/validation/u9/coordinator/reviews"
R="/tmp/u9-review-r3/reviewer-2"
mkdir -p "$R" || exit 91
{
  echo "argv: perch run --permission auto_review --cwd $E --effort max --json <brief text>"
  echo "brief: reviewer-2-brief.md sha256 $(shasum -a 256 "$D/reviewer-2-brief.md")"
} > "$R/launch-note.txt"
cd "$E" || exit 90
perch run --permission auto_review --cwd "$E" --effort max --json \
  "$(cat "$D/reviewer-2-brief.md")" > "$R/stdout.json" 2> "$R/stderr.log"
echo "PERCH_EXIT=$?"
exit 0
