#!/usr/bin/env python3
"""U3 mutation gate: planted mutant fails, restored copy passes.

Runs on a disposable copy of ``skill_lens/`` + ``tests/`` in a temp directory,
so the checkout is never modified (its ``home.py`` content hash is recorded
before and after and must be identical).

Six gates are exercised on the new Home module:

1. Read-only AST guard: ``import rich`` planted in ``home.py`` must fail the
   shipped-tree guard (reusing the existing U2 guard and mutation categories).
2. No-live-read browsing gate: a live ``paths.home()`` probe planted in
   ``HomeScreen.sync_from_controller`` must fail the sentinel test.
3. Target-read sentinel: a direct ``Path(...).read_text()`` of a synthetic
   target skill file planted in ``HomeScreen._update_preview`` must fail the
   target-specific sentinel (a read that the high-level helper patches missed).
4. Queue liveness: suppressing the post-selection and post-report ``_drive()``
   re-drive must fail the event-controlled liveness test (a stuck queue must not
   pass as "live").
5. Cell-update containment: widening ``_set_state_cell``'s
   ``except CellDoesNotExist`` to ``except Exception`` must fail the
   unexpected-update-fault containment test (an unexpected rendering fault must
   not be swallowed).
6. Rejected-outcome token ownership: clearing the owned token on every rejected
   outcome (replacing the ``elif not accepted:`` ``pass`` with
   ``self._inflight = None``) must fail the race test where the superseded
   request's rejected outcome arrives while a newer request is still owned.

Usage: ``mutation_gate.py [--out PATH]``.  By default the receipt is written
next to this script; ``--out`` lets a reviewer write it outside the checkout
(the checkout is never modified either way).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PYTHON = REPO / ".venv" / "bin" / "python"
DEFAULT_OUT = Path(__file__).resolve().parent / "mutation_gate.json"

READ_ONLY_TEST = "tests/test_tui_read_only.py::test_shipped_tui_code_has_zero_read_only_violations"
LIVE_READ_TEST = (
    "tests/test_tui_home.py::test_home_navigation_and_filtering_never_read_live_filesystem"
)
LIVENESS_TEST = (
    "tests/test_tui_home.py::test_home_selection_change_redrives_and_rejects_late_result"
)
CONTAINMENT_TEST = (
    "tests/test_tui_home.py::test_home_unexpected_cell_update_fault_routes_to_containment_and_exit3"
)
REJECTED_TOKEN_TEST = (
    "tests/test_tui_home.py::test_home_rejected_old_outcome_preserves_newer_owned_token"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(work: Path, selector: str) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(work)
    proc = subprocess.run(
        [str(PYTHON), "-m", "pytest", selector, "-q", "-p", "no:cacheprovider"],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr)[-4000:]


def failing_assertion(output: str) -> str:
    """The first assertion/error line pytest reported, for the receipt."""
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith(("AssertionError", "E ")) and "AssertionError" in stripped:
            return stripped[:200]
    for line in output.splitlines():
        if line.strip().startswith("E "):
            return line.strip()[:200]
    return ""


def main(out: Path) -> int:
    work = Path(tempfile.mkdtemp(prefix="skill-lens-u3-mutation-")).resolve()
    for item in ("skill_lens", "tests"):
        shutil.copytree(
            REPO / item,
            work / item,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    shutil.copy2(REPO / "pyproject.toml", work / "pyproject.toml")

    home_py = work / "skill_lens" / "tui" / "home.py"
    original = home_py.read_text(encoding="utf-8")
    original_hash = sha256(home_py)

    repo_home = REPO / "skill_lens" / "tui" / "home.py"
    receipt: dict[str, object] = {
        "schema": "skill-lens/u3-mutation-gate/4",
        "work_copy": str(work),
        "preservation": {
            "repo_home_sha256_before": sha256(repo_home),
            "work_home_sha256": original_hash,
        },
        "cases": [],
    }

    # Control: every gate passes on the unmodified copy.
    control = {
        "read_only": run(work, READ_ONLY_TEST),
        "live_read": run(work, LIVE_READ_TEST),
        "liveness": run(work, LIVENESS_TEST),
        "containment": run(work, CONTAINMENT_TEST),
        "rejected_token": run(work, REJECTED_TOKEN_TEST),
    }
    receipt["control"] = {name: result[0] for name, result in control.items()}
    for name, result in control.items():
        assert result[0] == 0, f"{name} control failed:\n{result[1]}"

    def exercise(
        name: str,
        mutant: str,
        selector: str,
        pattern: str,
        restore_selector: str | None = None,
    ) -> None:
        assert mutant != original, f"{name}: mutation did not apply"
        home_py.write_text(mutant, encoding="utf-8")
        rc, output = run(work, selector)
        assert rc != 0, f"{name}: mutant survived"
        assert pattern in output, f"{name}: pattern {pattern!r} missing:\n{output}"
        home_py.write_text(original, encoding="utf-8")
        restored = run(work, restore_selector or selector)
        assert restored[0] == 0, f"{name}: restored copy failed:\n{restored[1]}"
        receipt["cases"].append(
            {
                "name": name,
                "selector": selector,
                "mutant_rc": rc,
                "mutant_detected_pattern": pattern,
                "mutant_failing_assertion": failing_assertion(output),
                "restored_rc": restored[0],
            }
        )

    # Mutant 1: banned ``rich`` import in home.py.
    exercise(
        "read_only_guard_detects_rich_import_in_home",
        original + "\nimport rich  # U3 mutation\n",
        READ_ONLY_TEST,
        "rich",
    )

    # Mutant 2: live filesystem probe during browsing.
    live_read_mutant = original.replace(
        "from dataclasses import dataclass",
        "from dataclasses import dataclass\nfrom skill_lens.core import paths as _mutation_paths",
        1,
    ).replace(
        '        """Reconcile the screen with the controller\'s published session."""\n'
        "        if not self.is_mounted:",
        '        """Reconcile the screen with the controller\'s published session."""\n'
        "        _mutation_paths.home()\n"
        "        if not self.is_mounted:",
        1,
    )
    exercise(
        "no_live_read_gate_detects_paths_home_probe",
        live_read_mutant,
        LIVE_READ_TEST,
        "Forbidden live filesystem probe",
    )

    # Mutant 3: a direct synthetic-target read the high-level helper patches miss.
    target_read_mutant = original.replace(
        "    def _update_preview(self) -> None:\n"
        '        preview = self.query_one("#preview-pane", Static)\n'
        "        row = self._selected_row()\n",
        "    def _update_preview(self) -> None:\n"
        '        preview = self.query_one("#preview-pane", Static)\n'
        "        from pathlib import Path as _MutationPath\n"
        "\n"
        "        if self._rows:\n"
        '            _MutationPath(self._rows[0].key, "SKILL.md").read_text()\n'
        "        row = self._selected_row()\n",
        1,
    )
    exercise(
        "target_read_sentinel_detects_direct_path_read",
        target_read_mutant,
        LIVE_READ_TEST,
        "Forbidden synthetic-target filesystem read",
    )

    # Mutant 4: suppress the post-selection and post-report re-drive; a stuck
    # queue must fail the event-controlled liveness test.
    liveness_mutant = original.replace(
        "        controller.set_selected_key(key)\n"
        "        self._abandon_invalid_token()\n"
        "        self._update_preview()\n"
        "        self._drive()\n"
        "\n"
        "    def on_input_changed(self, event: Input.Changed) -> None:\n",
        "        controller.set_selected_key(key)\n"
        "        self._abandon_invalid_token()\n"
        "        self._update_preview()\n"
        "\n"
        "    def on_input_changed(self, event: Input.Changed) -> None:\n",
        1,
    ).replace(
        "        self._drive()\n"
        "\n"
        "    # -- generation / filtering -------------------------------------------\n",
        "\n    # -- generation / filtering -------------------------------------------\n",
        1,
    )
    exercise(
        "queue_liveness_detects_suppressed_redrive",
        liveness_mutant,
        LIVENESS_TEST,
        "timed out waiting for second group and re-driven first group",
    )

    # Mutant 5: widen the state-cell catch so an unexpected update fault is
    # swallowed; the containment test must then time out waiting for sticky
    # failure instead of passing.
    containment_mutant = original.replace(
        "        except CellDoesNotExist:\n",
        "        except Exception:\n",
        1,
    )
    exercise(
        "cell_update_containment_detects_swallowed_fault",
        containment_mutant,
        CONTAINMENT_TEST,
        "timed out waiting for contained fault",
    )

    # Mutant 6: clear the owned token on every rejected outcome, not only when the
    # controller really dropped the superseded request.  The race test must die on
    # the newer-token invariant instead of passing.
    rejected_token_mutant = original.replace(
        "            elif not accepted:\n"
        "                # Rejected data for someone else's token must never clear or\n"
        "                # mark the newer owned token.\n"
        "                pass\n",
        "            elif not accepted:\n                self._inflight = None\n",
        1,
    )
    exercise(
        "rejected_outcome_preserves_newer_owned_token",
        rejected_token_mutant,
        REJECTED_TOKEN_TEST,
        "the newer owned Why token was cleared by a rejected outcome",
    )

    receipt["preservation"]["work_home_sha256_after_restore"] = sha256(home_py)
    receipt["preservation"]["repo_home_sha256_after"] = sha256(repo_home)
    receipt["preservation"]["restored_identical"] = sha256(home_py) == original_hash
    assert receipt["preservation"]["restored_identical"] is True
    assert (
        receipt["preservation"]["repo_home_sha256_before"]
        == receipt["preservation"]["repo_home_sha256_after"]
    )

    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="receipt path (default: next to this script)",
    )
    raise SystemExit(main(parser.parse_args().out))
