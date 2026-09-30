"""Phase 4 compare tests: what ``skill-lens compare`` promises to be honest about.

The classification rule is the contract: two agents reading the *same* canonical
file -- or separate files with identical bytes -- share a capability; two agents
reading genuinely different files under one name have diverged and need
``diff``; a name only one side can reach is one-sided. Tests assert relation +
which side is ``None``, never prose.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

import skill_lens.core.compare as compare_module
from skill_lens.core.compare import build_compare_report
from skill_lens.core.discovery import discover
from skill_lens.models import dumps
from skill_lens.models.compare import CompareEntry, CompareReport
from skill_lens.models.enums import CompareRelation
from tests.fixtures.builders import (
    make_skill,
    relative_symlink,
    skill_markdown,
    write_skill,
)
from tests.fixtures.farm import build_acceptance_farm


def _entry(report: CompareReport, name: str) -> CompareEntry:
    return next(entry for entry in report.entries if entry.name == name)


def _claude_vs_codex(home: Path) -> CompareReport:
    return build_compare_report("claude", "codex", home, home)


# --- Classification ----------------------------------------------------------


def test_farm_siblings_classify_as_shared(mock_home: Path) -> None:
    """Every farmed skill is one library read through two entrypoints."""
    build_acceptance_farm(mock_home)
    home = mock_home.resolve()
    report = _claude_vs_codex(home)
    for name in ("alpha", "beta", "gamma", "delta", "epsilon"):
        entry = _entry(report, name)
        assert entry.relation is CompareRelation.SHARED, name
        assert entry.path_a and str(Path(".claude", "skills", name)) in entry.path_a
        assert entry.path_b and str(Path(".agents", "skills", name)) in entry.path_b
        # Shared means *one canonical*, reported twice -- same string on both sides.
        assert entry.canonical_a == entry.canonical_b
    counts = report.counts_by_relation()
    assert counts["shared"] == 5 and counts["diverged"] == 0


def test_codex_only_skills_appear_on_one_side(mock_home: Path) -> None:
    build_acceptance_farm(mock_home)
    home = mock_home.resolve()
    report = _claude_vs_codex(home)
    omega = _entry(report, "omega")
    assert omega.relation is CompareRelation.ONLY_B
    assert omega.path_a is None and omega.canonical_a is None
    assert ".codex" in omega.path_b
    plug = _entry(report, "plugskill")
    assert plug.relation is CompareRelation.ONLY_B


def test_same_name_different_files_diverge(mock_home: Path) -> None:
    home = mock_home.resolve()
    make_skill(home / ".claude" / "skills" / "deploy", "deploy", "Claude copy.")
    make_skill(home / ".codex" / "skills" / "deploy", "deploy", "Codex copy.")
    report = _claude_vs_codex(home)
    entry = _entry(report, "deploy")
    assert entry.relation is CompareRelation.DIVERGED
    assert entry.canonical_a != entry.canonical_b
    assert ".claude" in entry.path_a and ".codex" in entry.path_b


def test_identical_copies_count_as_shared(mock_home: Path) -> None:
    """Separate files with the same bytes are the same capability.

    Telling the user to run ``diff`` on copies that would report "no
    differences" is a false alarm: discovery already fingerprints every
    canonical file, and compare reuses that hash before calling a pair
    divergent. The paths still show both copies, so the layout stays visible.
    """
    home = mock_home.resolve()
    text = skill_markdown("deploy", "Same bytes in both homes.")
    write_skill(home / ".claude" / "skills" / "deploy", text)
    write_skill(home / ".codex" / "skills" / "deploy", text)
    report = _claude_vs_codex(home)
    entry = _entry(report, "deploy")
    assert entry.relation is CompareRelation.SHARED
    assert entry.canonical_a != entry.canonical_b
    assert ".claude" in entry.path_a and ".codex" in entry.path_b
    assert report.notes == ()


def test_divergence_adds_a_note_pointing_at_diff(mock_home: Path) -> None:
    home = mock_home.resolve()
    make_skill(home / ".claude" / "skills" / "deploy", "deploy", "Claude copy.")
    make_skill(home / ".codex" / "skills" / "deploy", "deploy", "Codex copy.")
    report = _claude_vs_codex(home)
    assert len(report.notes) == 1
    assert "'deploy'" in report.notes[0]
    assert "skill-lens diff" in report.notes[0]


def test_shared_only_has_no_note(mock_home: Path) -> None:
    home = mock_home.resolve()
    library = home / ".agents" / "skills" / "shared"
    make_skill(library, "shared", "One library.")
    relative_symlink(library, home / ".claude" / "skills" / "shared")
    report = _claude_vs_codex(home)
    assert _entry(report, "shared").relation is CompareRelation.SHARED
    assert report.notes == ()


def test_reversed_sides_are_mirrors(mock_home: Path) -> None:
    """``codex vs claude`` is the same fact with the sides swapped, not re-judged."""
    build_acceptance_farm(mock_home)
    home = mock_home.resolve()
    forward = _claude_vs_codex(home)
    backward = build_compare_report("codex", "claude", home, home)
    alpha = _entry(forward, "alpha")
    omega = _entry(forward, "omega")
    assert _entry(backward, "alpha").path_b == alpha.path_a
    assert _entry(backward, "omega").relation is CompareRelation.ONLY_A
    assert _entry(backward, "omega").path_a == omega.path_b


def test_two_agents_with_nothing_in_common(mock_home: Path) -> None:
    home = mock_home.resolve()
    make_skill(home / ".claude" / "skills" / "only-mine", "only-mine", "A.")
    make_skill(home / ".grok" / "skills" / "only-yours", "only-yours", "B.")
    report = build_compare_report("claude", "grok", home, home)
    assert _entry(report, "only-mine").relation is CompareRelation.ONLY_A
    assert _entry(report, "only-yours").relation is CompareRelation.ONLY_B
    assert report.counts_by_relation()["shared"] == 0


def test_two_empty_agents_compare_cleanly(mock_home: Path) -> None:
    """Nothing to compare is a fact, not an error (spec: exit code 0)."""
    home = mock_home.resolve()
    report = _claude_vs_codex(home)
    assert report.entries == ()
    assert report.counts_by_relation() == {
        "shared": 0,
        "diverged": 0,
        "only_a": 0,
        "only_b": 0,
    }


# --- Agent validation --------------------------------------------------------


def test_unknown_agent_raises_a_readable_keyerror(mock_home: Path) -> None:
    home = mock_home.resolve()
    with pytest.raises(KeyError) as excinfo:
        _build_unknown(home)
    message = excinfo.value.args[0]
    assert "unknown agent 'nope'" in message
    assert "Known agents:" in message and "claude" in message


def _build_unknown(home: Path) -> CompareReport:
    return build_compare_report("claude", "nope", home, home)


def test_unknown_agent_is_rejected_before_scanning(mock_home: Path) -> None:
    """The usage error must not cost a filesystem crawl."""
    home = mock_home.resolve()
    calls: list[object] = []
    monkey_discover = compare_module.discover
    try:
        compare_module.discover = lambda *a, **k: calls.append(a)  # type: ignore[assignment]
        with pytest.raises(KeyError):
            _build_unknown(home)
    finally:
        compare_module.discover = monkey_discover  # type: ignore[assignment]
    assert calls == []


# --- Report shape ------------------------------------------------------------


def test_report_round_trips(mock_home: Path) -> None:
    build_acceptance_farm(mock_home)
    home = mock_home.resolve()
    report = _claude_vs_codex(home)
    assert CompareReport.from_dict(report.to_dict()) == report


def test_compare_is_deterministic_and_canonical(mock_home: Path) -> None:
    build_acceptance_farm(mock_home)
    home = mock_home.resolve()
    first = dumps(_claude_vs_codex(home).to_dict())
    second = dumps(_claude_vs_codex(home).to_dict())
    assert first == second
    assert first == json.dumps(json.loads(first), sort_keys=True, indent=2)


def test_entries_are_sorted_by_name(mock_home: Path) -> None:
    build_acceptance_farm(mock_home)
    home = mock_home.resolve()
    report = _claude_vs_codex(home)
    names = [entry.name for entry in report.entries]
    assert names == sorted(names)


def test_reuse_of_a_shared_index(mock_home: Path) -> None:
    """One discovery pass can serve several commands; passing it in must not change results."""
    build_acceptance_farm(mock_home)
    home = mock_home.resolve()
    index = discover(home, home)
    with_index = build_compare_report("claude", "codex", home, home, index=index)
    assert dumps(with_index.to_dict()) == dumps(_claude_vs_codex(home).to_dict())


def test_registry_names_are_carried(mock_home: Path) -> None:
    home = mock_home.resolve()
    report = _claude_vs_codex(home)
    assert report.agent_a == "claude" and report.agent_b == "codex"
    assert report.agent_a_name and report.agent_a_name != "claude"
    assert str(home) in report.home


# --- Presentation boundary ----------------------------------------------------


def _no_rich(module: object) -> bool:
    source = Path(module.__file__).read_text(encoding="utf-8")  # type: ignore[attr-defined]
    imported: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return not [name for name in imported if name.split(".")[0] == "rich"]


def test_the_compare_engine_imports_no_rich() -> None:
    assert _no_rich(compare_module)


def test_the_system_adapter_imports_no_rich() -> None:
    import skill_lens.core.system as system_module

    assert _no_rich(system_module)
