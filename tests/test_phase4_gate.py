"""Phase 4 gate: doctor, compare, and the live-discovery adapter meet the spec.

The specification's gate for this phase is a live smoke test: with the sandbox
*off* (``bare_home``) the same commands that will run on a developer's machine
must run against a realistic fixture home and produce zero regressions -- no
crash, no write, honest JSON. Everything else here pins the two data contracts
(whole-report goldens) and the read-only promise.
"""

from __future__ import annotations

import json
from pathlib import Path

from skill_lens.core import paths
from skill_lens.core.compare import build_compare_report
from skill_lens.core.doctor import build_doctor_report, run_doctor
from skill_lens.core.scanner import build_scan_report
from skill_lens.core.system import (
    installer_lockfile,
    live_discovery,
    read_json_guarded,
    shared_library,
)
from skill_lens.models import dumps
from skill_lens.models.compare import CompareReport
from skill_lens.models.doctor import DoctorReport
from tests.fixtures.farm import build_acceptance_farm

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden" / "phase4"


def _rel(value: object, home: Path) -> object:
    """Rewrite a path as home-relative so a golden can pin it.

    Handles both forms a report may carry: an absolute string (report home/cwd
    and compare entry paths) and an already-collapsed ``~/...`` display string
    (doctor finding paths). The home itself becomes ``"."``. Either way the
    golden holds no machine path.
    """
    if isinstance(value, str):
        if value.startswith(str(home)):
            rest = Path(value).relative_to(home).as_posix()
            return rest or "."
        shown = paths.display(value)
        if shown == "~":
            return "."
        if shown.startswith("~/"):
            return shown[2:]
    return value


def _normalize(payload: dict, home: Path) -> dict:
    """Home-relative form of a report, so the golden holds no machine paths."""
    normalized = dict(payload)
    for field in ("home", "cwd"):
        normalized[field] = _rel(normalized[field], home)
    if "entries" in normalized:
        normalized["entries"] = [
            {
                **entry,
                "path_a": _rel(entry["path_a"], home),
                "path_b": _rel(entry["path_b"], home),
                "canonical_a": _rel(entry["canonical_a"], home),
                "canonical_b": _rel(entry["canonical_b"], home),
            }
            for entry in payload["entries"]
        ]
    if "findings" in normalized:
        normalized["findings"] = [
            {**finding, "path": _rel(finding["path"], home)} for finding in payload["findings"]
        ]
    return normalized


def _load(name: str) -> dict:
    return json.loads((GOLDEN_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _write(name: str, payload: dict) -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    (GOLDEN_DIR / f"{name}.json").write_text(dumps(payload), encoding="utf-8")


# --- Doctor + compare goldens ------------------------------------------------


def test_doctor_golden_on_the_acceptance_farm(mock_home: Path, update_goldens: bool) -> None:
    """The farm's doctor output is pinned: two info findings, nothing invented."""
    home = mock_home.resolve()
    build_acceptance_farm(home)
    normalized = _normalize(build_doctor_report(home, home).to_dict(), home)
    if update_goldens:
        _write("doctor_farm", normalized)
    # A missing golden is a FAILURE, never a silent re-write: the file is the
    # reviewed contract (AGENTS.md -- never regenerate without reading the diff).
    assert normalized == _load("doctor_farm")
    assert [finding["code"] for finding in normalized["findings"]] == [
        "installer_lockfile",
        "symlink_farm",
    ]


def test_compare_golden_on_the_acceptance_farm(mock_home: Path, update_goldens: bool) -> None:
    """claude vs codex over the farm: five shared, two codex-only."""
    home = mock_home.resolve()
    build_acceptance_farm(home)
    normalized = _normalize(build_compare_report("claude", "codex", home, home).to_dict(), home)
    if update_goldens:
        _write("compare_claude_vs_codex", normalized)
    assert normalized == _load("compare_claude_vs_codex")
    relations = {entry["name"]: entry["relation"] for entry in normalized["entries"]}
    assert all(
        relations[name] == "shared" for name in ("alpha", "beta", "gamma", "delta", "epsilon")
    )
    assert relations["omega"] == "only_b"
    assert relations["plugskill"] == "only_b"


def test_golden_json_is_canonical(tmp_path: Path) -> None:
    """Goldens must be byte-canonical, exactly like --json output."""
    for name in ("doctor_farm", "compare_claude_vs_codex"):
        path = GOLDEN_DIR / f"{name}.json"
        text = path.read_text(encoding="utf-8")
        assert text == json.dumps(json.loads(text), sort_keys=True, indent=2), name
        assert str(tmp_path) not in text, "a golden must not embed a machine path"


# --- Live adapter (system.py) ------------------------------------------------


def test_live_discovery_follows_home_without_a_sandbox(bare_home: Path) -> None:
    """The Phase 4 gate: discovery through the *real* environment variables.

    ``bare_home`` patches $HOME but leaves the explicit sandbox off, so
    ``live_discovery`` must resolve lazily exactly like a real terminal run --
    and find the fixture skills, not the developer's own.
    """
    build_acceptance_farm(bare_home)
    index = live_discovery(cwd=bare_home)
    assert Path(index.home).resolve() == bare_home.resolve()
    names = {entry.name for entry in index.entries}
    assert {"alpha", "beta", "omega", "plugskill"} <= names


def test_the_live_adapter_never_writes_anything(bare_home: Path) -> None:
    """Read-only promise (AGENTS.md rule 1) over the whole Phase 4 surface."""
    build_acceptance_farm(bare_home)
    before = sorted(p.as_posix() for p in bare_home.rglob("*"))
    report = run_doctor(cwd=bare_home)
    compare = build_compare_report("claude", "codex", paths.home(), bare_home)
    scan = build_scan_report(paths.home(), bare_home)
    after = sorted(p.as_posix() for p in bare_home.rglob("*"))
    assert before == after, "a diagnostic run must not create, move, or delete a file"
    assert report.healthy is True
    assert compare.counts_by_relation()["shared"] == 5
    assert scan.summary.total_skills >= 7


def test_run_doctor_is_the_live_entry_point(bare_home: Path) -> None:
    build_acceptance_farm(bare_home)
    report = run_doctor(cwd=bare_home)
    assert isinstance(report, DoctorReport)
    assert DoctorReport.from_dict(report.to_dict()) == report


def test_read_json_guarded_never_raises(tmp_path: Path) -> None:
    good = tmp_path / "good.json"
    good.write_text('{"skills": 1}', encoding="utf-8")
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    missing = tmp_path / "gone.json"

    data, error = read_json_guarded(good)
    assert data == {"skills": 1} and error is None
    data, error = read_json_guarded(broken)
    assert data is None and error == "not_json"
    non_utf8 = tmp_path / "non_utf8.json"
    non_utf8.write_bytes(b"\xff\xfe\x00\x00")
    data, error = read_json_guarded(non_utf8)
    assert data is None and error == "not_json"
    data, error = read_json_guarded(missing)
    assert data is None and error == "missing"


def test_lockfile_and_library_paths_stay_lazy(bare_home: Path) -> None:
    """No module-level ``~`` expansion: the paths must follow the environment."""
    assert shared_library() == Path.home() / ".agents" / "skills"
    assert installer_lockfile() == Path.home() / ".agents" / ".skill-lock.json"
    assert str(bare_home) in str(shared_library())


def test_live_smoke_over_json_stays_machine_readable(bare_home: Path) -> None:
    build_acceptance_farm(bare_home)
    report = run_doctor(cwd=bare_home)
    text = dumps(report.to_dict())
    assert text == json.dumps(json.loads(text), sort_keys=True, indent=2)
    compare = build_compare_report("claude", "codex", paths.home(), bare_home)
    assert CompareReport.from_dict(compare.to_dict()) == compare
