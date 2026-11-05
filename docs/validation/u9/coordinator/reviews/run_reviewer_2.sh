#!/usr/bin/env bash
# Reviewer 2 (perch, requested glm-5.3-flash-starter / max; deviation
# disclosed in approvals.json — served model unverified, effort capped to high)
# one-shot critic run. All outputs go to /tmp (outside the checkout).
set -u
E="<REPO_ROOT>"
D="$E/docs/validation/u9/coordinator/reviews"
R="/tmp/u9-review-r2/reviewer-2"
mkdir -p "$R" || exit 91
{
  echo "argv: perch run --cwd $E --effort max --json <brief text>"
  echo "brief_sha256: $(shasum -a 256 "$D/reviewer-2-brief.md")"
} > "$R/launch-note.txt"
cd "$E" || exit 90
perch run --cwd "$E" --effort max --json "$(cat "$D/reviewer-2-brief.md")" \
  > "$R/stdout.json" 2> "$R/stderr.log"
echo "PERCH_EXIT=$?"
