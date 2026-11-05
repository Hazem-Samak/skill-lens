#!/usr/bin/env bash
# Reviewer 1 (mcode / MiniMax-M3.1-Flash / xhigh) one-shot critic run.
# All outputs go to /tmp (outside the checkout). Read-only guard is in the brief.
set -u
E="/Users/corvette/Documents/Projects Coding/Skill Lens"
D="$E/docs/validation/u9/coordinator/reviews"
R="/tmp/u9-review-r2/reviewer-1"
mkdir -p "$R" || exit 91
{
  echo "argv: mcode exec --model minimax/MiniMax-M3.1-Flash --effort xhigh --permission smart --cwd $E --timeout 45m --output-format json --input -"
  echo "brief_sha256: $(shasum -a 256 "$D/reviewer-1-brief.md")"
} > "$R/launch-note.txt"
cd "$E" || exit 90
mcode exec --model minimax/MiniMax-M3.1-Flash --effort xhigh --permission smart \
  --cwd "$E" --timeout 45m --output-format json --input - \
  < "$D/reviewer-1-brief.md" > "$R/stdout.json" 2> "$R/stderr.log"
echo "MCODE_EXIT=$?"
