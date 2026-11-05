#!/usr/bin/env bash
# Coordinator r2 candidate rebuild + requalification after the documentation
# corrections (CHANGELOG.md and DEVELOPMENT.md are packaged inputs, so the r1
# artifact hashes are superseded). Reuses the implementer's audited scripts
# unchanged; only the work directories and receipt names differ.
set -u
E="<REPO_ROOT>"
D="$E/docs/validation/u9/coordinator/precommit"
W="/tmp/u9-candidate-r2"
mkdir -p "$W" || exit 91

"$E/.venv/bin/python" "$E/docs/validation/u9/implementation/qualify_candidate.py" \
  --work "$W" --out "$D/candidate-r2.json" \
  >"$D/candidate-build-r2.log" 2>&1
rc_build=$?
echo "BUILD_EXIT $rc_build"
[ "$rc_build" -ne 0 ] && exit "$rc_build"

wheel="$W/artifacts/skill_lens_cli-0.2.0-py3-none-any.whl"
sdist="$W/artifacts/skill_lens_cli-0.2.0.tar.gz"

"$E/.venv/bin/python" "$W/src/scripts/smoke_wheel.py" \
  --wheel "$wheel" --sdist "$sdist" \
  --work-dir "$W/smoke" --receipt-out "$W/install-receipt.json" \
  >"$D/install-harness-r2.log" 2>&1
rc_install=$?
echo "INSTALL_EXIT $rc_install"
cp "$W/install-receipt.json" "$D/install-receipt-r2.json" 2>/dev/null
[ "$rc_install" -ne 0 ] && exit "$rc_install"

"$E/.venv/bin/python" "$E/docs/validation/u9/implementation/version_probes.py" \
  --smoke-dir "$W/smoke" --artifacts "$W/artifacts" \
  --out "$D/version-probes-r2.json" \
  >"$D/version-probes-r2.log" 2>&1
rc_probe=$?
echo "PROBES_EXIT $rc_probe"
[ "$rc_probe" -ne 0 ] && exit "$rc_probe"

sha=$("$E/.venv/bin/python" -c "import json;print(json.load(open('$D/candidate-r2.json'))['artifacts']['wheel']['sha256'])")

"$E/.venv/bin/python" "$E/docs/validation/u9/implementation/terminal_check.py" \
  --binary "$W/smoke/min_lane/venv/bin/skill-lens" \
  --base-binary "$W/smoke/base_lane/venv/bin/skill-lens" \
  --lane-python "$W/smoke/min_lane/venv/bin/python" \
  --fixture-root /tmp/u9-terminal-r2 \
  --out "$D/terminal-receipt-r2.json" \
  --artifact-sha256 "$sha" \
  >"$D/terminal-r2.log" 2>&1
rc_term=$?
echo "TERMINAL_EXIT $rc_term"
echo "REQUAL_R2_DONE $rc_build $rc_install $rc_probe $rc_term wheel_sha=$sha"
[ "$rc_term" -ne 0 ] && exit "$rc_term"
