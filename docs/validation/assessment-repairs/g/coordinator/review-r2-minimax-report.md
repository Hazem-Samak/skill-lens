# Stage G round-two critic report — corrected installed-lane guards

## Summary

Round-two focused follow-up on one question: **do the corrected tests now independently reject all six
lane-guard failures — including both endpoint origin branches — while preserving the relative-path test and
actual installed-lane execution?**

**Verdict: pass.** I answered this by reproducing the work myself rather than re-reading it. I copied the
repository to a disposable tree outside it (`/tmp/skill-lens-critic-r2a`), proved the imports came from that
copy, confirmed the copies were byte-identical to the current tree, and then re-applied all six guard
mutations myself. Every one died, each with exactly one failing test, every failure behavioural
(`DID NOT RAISE`), no syntax/import/collection failure. I additionally proved that the base-Textual test runs a
*real* child interpreter, that the two endpoint origin branches are killed by *different* parametrized cases,
that the relative-path test still kills both of its lane variants, and that the corrected test bytes are the
ones that actually executed inside the real installed lanes. No product, CI, or test file was changed by this
review; all 602 recorded fingerprints still match the tree afterwards.

Scope was strictly this round's question plus the claims the corrections had to preserve. No third council
wave, no delegation, no edits, no build/install/network rerun.

---

## Independent reproduction (the decisive evidence)

Environment: disposable copy at `/tmp/skill-lens-critic-r2a`, `PYTHONPATH` pinned to it,
`PYTHONDONTWRITEBYTECODE=1`, coverage/pytest cache redirected outside the repository.

**Provenance proof** (imports resolved from the copy, not the checkout or an installed copy):

```
skill_lens : /private/tmp/skill-lens-critic-r2a/skill_lens/__init__.py
tui_compat : /private/tmp/skill-lens-critic-r2a/skill_lens/tui/_textual_compat.py
smoke_wheel: /private/tmp/skill-lens-critic-r2a/scripts/smoke_wheel.py
scripts/smoke_wheel.py        a28bc7f8dade832168a773c190c5f8abc21d75c36b14881460c45d146b8fa331
tests/test_tui_packaging.py   5367a43ca1c0c0a982278a2a421b409c9cad08bc5c7b2611e0bffbc2ee9449fa
```

Both hashes match the live repository and the `mutations.json` `source_hash` values exactly — the coordinator's
mutations ran against these bytes, and so did mine.

**Controls.** Whole packaging file on pristine bytes: `24 passed`. Full suite with coverage:
`1021 passed, 1 skipped`, `Total coverage: 91.16%` — identical to `gates.json` and `pytest.log`.

**The six guards, re-mutated by me** (whole `tests/test_tui_packaging.py`, not just the single node the
coordinator selected — a strictly stronger selection):

| Mutation | Result | Failing case |
|---|---|---|
| `base_origin_guard_removed` (`if False:`) | exit 1, `1 failed, 23 passed` | `DID NOT RAISE AssertionError` |
| `endpoint_pkg_origin_ignored` (drop pkg check) | exit 1, `1 failed, 23 passed` | `DID NOT RAISE AssertionError` |
| `endpoint_tui_origin_ignored` (drop tui check) | exit 1, `1 failed, 23 passed` | `DID NOT RAISE AssertionError` |
| `base_textual_presence_ignored` (`assert True`) | exit 1, `1 failed, 23 passed` | `DID NOT RAISE CalledProcessError` |
| `installed_test_failure_ignored` (`if False:`) | exit 1, `1 failed, 23 passed` | `DID NOT RAISE AssertionError` |
| `source_copy_guard_removed` (`assert True`) | exit 1, `1 failed, 23 passed` | `DID NOT RAISE AssertionError` |

All six: behavioural, no collection error, no import error, and exactly one test failing each time (no
collateral damage, no mutual dependence). After restoration the pristine hash matched and the file went back
to `24 passed`.

### Both endpoint origin branches are independently covered

`test_verify_tui_endpoint_install_invalid_provenance_fails` is parametrized `(pkg_outside, tui_outside)` =
`(True, False)`, `(False, True)`, `(True, True)`. The two mutants die on *different* parameters — dropping the
`pkg_prov` check kills only `[True-False]`, dropping the `tui_prov` check kills only `[False-True]` (this
matches the coordinator's logs and my own runs). Neither branch is inferred from the other; each is rejected
by its own case.

### The base-Textual test executes a real child process

This was the claim most open to doubt — a `subprocess.run` double could, in principle, kill the mutant for
the wrong reason. Two probes settle it:

- **Probe A** — I changed only the assertion *message* in the generated command. The test then failed on its
  own stderr assertion with a live interpreter traceback:
  `assert 'Textual must be absent' in '... File "<string>", line 1 ... AssertionError: PROBE-MARKER-XYZ'`
  inside `CalledProcessError(1, [venv/bin/python, '-c', "import importlib.util; assert
  importlib.util.find_spec('textual') is None, 'PROBE-MARKER-XYZ'"])`. A real child Python process genuinely
  ran and genuinely failed.
- **Probe B** — I changed `find_spec('textual')` to `find_spec('textual_typo')`, making the guard vacuous
  (it would never detect Textual). The test failed. So the test detects a base-Textual guard that does not
  actually detect Textual.

Both probes restored cleanly.

### Relative-path test preserved and still load-bearing

`test_relative_wheel_and_harness_paths_normalized_before_cwd_switch`
(`tests/test_tui_packaging.py:485`) still exists and still exercises `main()`, `verify_base_install` and
`verify_tui_endpoint_install` with relative wheel/work/receipt inputs, asserting absolute paths after the cwd
switch. I re-ran both un-normalization variants against it (`verify_base_install` body and
`verify_tui_endpoint_install` body separately): each killed it alone (`1 failed, 23 passed`).

`correction-only.diff` is a single-file change to `tests/test_tui_packaging.py`. The relative-path test's
removal in that diff is a re-format (module-level `import subprocess` instead of a function-local import),
not a deletion — the test and its assertions are intact in the current file.

### Actual installed-lane execution preserved

- The corrected test bytes are present in **both** installed lanes and match the repository exactly:
  `5367a43c…` in `installed-work/min_lane/test_lane/tests/`, `latest_lane/test_lane/tests/`, and the repo.
- The receipt shows both endpoint lanes ran nine suites including `tests/test_tui_packaging.py`, from
  `rootdir …/installed-work/<lane>/test_lane`, `test_count 353`, `skip_count 0`, `suites_exit_code 0`.
- Base lane is genuinely Textual-free: its `site-packages` has `rich` but no `textual`; `textual_absent: true`.
- Min lane has Textual **8.2.8 physically installed** (`textual-8.2.8.dist-info`).
- Neither endpoint `test_lane` contains a `skill_lens` source directory (only `pyproject.toml`, `scripts`,
  `tests`, `uv.lock`), so the installed lanes really do run against the installed package.
- Installed `site-packages/skill_lens` is byte-identical to the current tree (only an untracked, gitignored
  `.DS_Store` differs, and it is not in the wheel — 53 entries, zero `DS_Store`).
- Artifact hashes match the recorded values: wheel `59707ca7…`, sdist `273ef448…`.

### No drift, and the gates reproduce

All 602 entries in `before-review-fingerprints.json` match the live tree — before *and* after my review.
`HEAD` is still `491f9ce`, `git status` is byte-for-byte the recorded status, and `scripts/smoke_wheel.py` /
`tests/test_tui_packaging.py` still hash to the mutation `source_hash` values. Independently reproduced in my
copy: `ruff check` → "All checks passed!", `ruff format --check` → "148 files already formatted", `mypy` →
"Success: no issues found in 37 source files". My mutations touched only the `/tmp` copy.

---

## Report

EFFECTIVE_MODEL: [ requested: independent MiniMax M3.1 Flash (thinking / mcode), xHigh, runtimeMode
full-access, interactionMode plan | configured: `m:minimax:MiniMax-M3.1-Flash-Preview:v:thinking` per runtime
context | confirmed: model identity + `thinking` effort variant + Plan interaction mode (plan-mode directive and
T3 interaction-mode instruction both active) | unverified: server-side runtimeMode could not be confirmed from
inside the session; upstream served model/family identity remains unverified under the owner-selected named
pair, as already disclosed ]

VERDICT: pass

BLOCKERS: [ none ]

The four MiniMax round-one suggestions that were reproduced as 0/0/0 false passes are now genuine kills, and I
reproduced all six myself rather than relying on the coordinator's record. Nothing in this round's evidence
rises to a current artifact, source, or provenance failure.

SUGGESTIONS: [ non-blocking ]

1. **Implicit environment precondition in the base-Textual test.** `test_verify_base_install_fails_when_textual_is_present`
   depends on Textual being importable by the running interpreter. That holds today — the CI unit job installs
   `--extra dev` (which declares `textual>=8.2.8`), and both endpoint lanes have Textual — and the base lane
   does not run test suites (the receipt shows no suites for it). But the precondition is not asserted, so a
   future Textual-less unit run would fail confusingly. An explicit precondition assert with a message, or a
   skip with a stated reason, would make the requirement visible.
2. **Bare `assert` in the source-copy guard.** `assert not (test_lane / "skill_lens").exists(), (...)` is
   stripped under `python -O`. CI invokes plain `python`, so it is correct today; `raise AssertionError` would
   match the style of the neighbouring guards and remove the dependence on interpreter flags.
3. **Substring dispatch in the shared double.** `_make_packaging_subprocess_runner` recognises commands by
   substring (`skill_lens.__file__`, `find_spec('textual')`, `textual.__version__`, `pytest`). Drift in the
   generated commands falls through to a synthetic success, which fails the test loudly — the safe direction —
   but Probes A and B show the *real-execution* property of the base-Textual test depends on the
   `find_spec('textual')` substring specifically. A short comment recording this would help the next editor.
4. **`all_packaged_source_bytes_match` is still coordinator-side**, not a harness feature (round-one item,
   unchanged). I independently re-established the stronger equivalent myself: installed `site-packages` is
   byte-identical to the tree, and both lane test copies match the corrected test bytes.
5. **Floor and latest still resolve the same version** (8.2.8 / 8.2.8, `endpoint_overlap.overlap: true`,
   honestly disclosed in the receipt). No version diversity today; retain the disclosure, and no future Textual
   compatibility claim is warranted.
6. **Private adapter is audited for existence and callability, not semantic drift** (unchanged round-one item);
   loud failure remains the correct mitigation. Behaviour-drift testing is future work.
7. **Evidence is macOS / Python 3.11 only.** No Linux, no executed CI, no full Python matrix claim appears
   anywhere in the material I read. Keep that disclosure.
8. **Hygiene, no action required:** `REQUIRED_REGISTRY_COUNT` remains exact-equality; `--verify-tui-only` is
   still unused by CI; the lane copytree still carries `tests/__pycache__`. Optional cleanup, not contract defects.

FILES_AT_RISK: [ scripts/smoke_wheel.py (six guard sites — now genuinely mutation-covered; bare `assert` at the
source-copy guard; generated-command coupling to the test double), tests/test_tui_packaging.py (shared
`_make_packaging_subprocess_runner` and the five new tests; unstated Textual-import precondition),
.github/workflows/ci.yml (packaging lanes structurally verified, never executed on Linux/CI),
skill_lens/tui/_textual_compat.py (private Textual coupling, existence-only audit), pyproject.toml
(`textual>=8.2.8` floor, open-ended) ]

CONCEDED: [ (a) Withdrawn — "the corrected tests may still mock the guards away". The lane functions themselves
execute for real; only the subprocess boundary is doubled, and Probe A shows an actual child interpreter running
the generated check and failing. (b) Withdrawn — "both endpoint origin branches may ride on one asymmetric
assertion". The test is parametrized and the two mutants die on two different parameters, `[True-False]` and
`[False-True]`. (c) Withdrawn — "the correction may have invalidated the installed-lane evidence". The lane test
copies are byte-identical to the corrected repo test, and each lane ran that file. (d) Withdrawn — "the shared
double could kill mutants for the wrong reason". Every kill is a `DID NOT RAISE` at the intended
`pytest.raises` line, with exactly one failing test and no collection or import error. (e) Noted but not a
finding — the ruff file-count difference between the repo and my ad-hoc `/tmp` copy (148 vs 149) is an artifact
of how I assembled the scratch tree; the repository's own counts match the coordinator exactly, and the two
trees' file lists are identical. ]

---

## Unresolved decisions / risks

None blocking acceptance. The two standing limits are disclosure items, not defects: evidence covers macOS and
Python 3.11 only (no Linux/CI/full-matrix execution), and no forward compatibility with future Textual releases
is claimed. Both are already stated in the material under review and I found nothing contradicting them.