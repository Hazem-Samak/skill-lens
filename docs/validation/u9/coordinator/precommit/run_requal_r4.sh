#!/usr/bin/env bash
# Coordinator r4 candidate rebuild + requalification after the wave-A review
# corrections (packaged documents changed again; r2 hashes are superseded).
set -u
E="/Users/corvette/Documents/Projects Coding/Skill Lens"
D="$E/docs/validation/u9/coordinator/precommit"
W="/tmp/u9-candidate-r4"
mkdir -p "$W" || exit 91

"$E/.venv/bin/python" "$E/docs/validation/u9/implementation/qualify_candidate.py" \
  --work "$W" --out "$D/candidate-r4.json" \
  >"$D/candidate-build-r4.log" 2>&1
rc_build=$?
echo "BUILD_EXIT $rc_build"
[ "$rc_build" -ne 0 ] && exit "$rc_build"

wheel="$W/artifacts/skill_lens_cli-0.2.0-py3-none-any.whl"
sdist="$W/artifacts/skill_lens_cli-0.2.0.tar.gz"

"$E/.venv/bin/python" "$W/src/scripts/smoke_wheel.py" \
  --wheel "$wheel" --sdist "$sdist" \
  --work-dir "$W/smoke" --receipt-out "$W/install-receipt.json" \
  >"$D/install-harness-r4.log" 2>&1
rc_install=$?
echo "INSTALL_EXIT $rc_install"
cp "$W/install-receipt.json" "$D/install-receipt-r4.json" 2>/dev/null
[ "$rc_install" -ne 0 ] && exit "$rc_install"

"$E/.venv/bin/python" "$E/docs/validation/u9/implementation/version_probes.py" \
  --smoke-dir "$W/smoke" --artifacts "$W/artifacts" \
  --out "$D/version-probes-r4.json" \
  >"$D/version-probes-r4.log" 2>&1
rc_probe=$?
echo "PROBES_EXIT $rc_probe"
[ "$rc_probe" -ne 0 ] && exit "$rc_probe"

sha=$("$E/.venv/bin/python" -c "import json;print(json.load(open('$D/candidate-r4.json'))['artifacts']['wheel']['sha256'])")

"$E/.venv/bin/python" "$E/docs/validation/u9/implementation/terminal_check.py" \
  --binary "$W/smoke/min_lane/venv/bin/skill-lens" \
  --base-binary "$W/smoke/base_lane/venv/bin/skill-lens" \
  --lane-python "$W/smoke/min_lane/venv/bin/python" \
  --fixture-root /tmp/u9-terminal-r4 \
  --out "$D/terminal-receipt-r4.json" \
  --artifact-sha256 "$sha" \
  >"$D/terminal-r4.log" 2>&1
rc_term=$?
echo "TERMINAL_EXIT $rc_term"
echo "REQUAL_R3_DONE build=$rc_build install=$rc_install probes=$rc_probe terminal=$rc_term wheel_sha=$sha"
if [ "$rc_term" -ne 0 ]; then exit "$rc_term"; fi
exit 0
