#!/usr/bin/env bash
# Coordinator r3 gate re-run after the wave-A review corrections (pointer
# sentences in five docs + DEVELOPMENT usability fixes C-S1..C-S4).
set -u
E="/Users/corvette/Documents/Projects Coding/Skill Lens"
D="$E/docs/validation/u9/coordinator/precommit"
cd "$E" || exit 90
"$E/.venv/bin/pytest" --cov=skill_lens -q >"$D/final-pytest-r3.log" 2>&1
p1=$?
"$E/.venv/bin/mypy" >"$D/final-mypy-r3.log" 2>&1
p2=$?
"$E/.venv/bin/ruff" check . >"$D/final-ruff-check-r3.log" 2>&1
p3=$?
"$E/.venv/bin/ruff" format --check . >"$D/final-ruff-format-check-r3.log" 2>&1
p4=$?
echo "GATES_R3_EXIT $p1 $p2 $p3 $p4"
exit $((p1 + p2 + p3 + p4))
