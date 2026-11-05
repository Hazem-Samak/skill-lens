#!/usr/bin/env bash
# Coordinator r2 gate re-run after the C-F1..C-F5 documentation corrections.
# Logs are evidence; the checkout caches are the normal pytest/mypy/ruff ones.
set -u
E="/Users/corvette/Documents/Projects Coding/Skill Lens"
D="$E/docs/validation/u9/coordinator/precommit"
cd "$E" || exit 90
"$E/.venv/bin/pytest" --cov=skill_lens -q >"$D/final-pytest-r2.log" 2>&1
p1=$?
"$E/.venv/bin/mypy" >"$D/final-mypy-r2.log" 2>&1
p2=$?
"$E/.venv/bin/ruff" check . >"$D/final-ruff-check-r2.log" 2>&1
p3=$?
"$E/.venv/bin/ruff" format --check . >"$D/final-ruff-format-check-r2.log" 2>&1
p4=$?
echo "GATES_R2_EXIT $p1 $p2 $p3 $p4"
