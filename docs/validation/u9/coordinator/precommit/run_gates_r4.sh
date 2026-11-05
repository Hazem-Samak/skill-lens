#!/usr/bin/env bash
# Coordinator r4 gate re-run for the 0.2.0 publication (release wording; pointer
# sentences in five docs + review-round fixes).
set -u
E="/Users/corvette/Documents/Projects Coding/Skill Lens"
D="$E/docs/validation/u9/coordinator/precommit"
cd "$E" || exit 90
"$E/.venv/bin/pytest" --cov=skill_lens -q >"$D/final-pytest-r4.log" 2>&1
p1=$?
"$E/.venv/bin/mypy" >"$D/final-mypy-r4.log" 2>&1
p2=$?
"$E/.venv/bin/ruff" check . >"$D/final-ruff-check-r4.log" 2>&1
p3=$?
"$E/.venv/bin/ruff" format --check . >"$D/final-ruff-format-check-r4.log" 2>&1
p4=$?
echo "GATES_R3_EXIT $p1 $p2 $p3 $p4"
exit $((p1 + p2 + p3 + p4))
