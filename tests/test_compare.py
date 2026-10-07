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


# ---------------------------------------------------------------------------
# C2 Compare Tests: injected builder and wrapper inputs (§21.3)
# ---------------------------------------------------------------------------


def test_compare_injected_inputs_matrix(mock_home: Path, tmp_path: Path) -> None:
    """Cover live index-only, registry-only, both, and neither for builder and wrapper."""
    from skill_lens.core.compare import run_compare
    from skill_lens.registry.loader import load_registry

    build_acceptance_farm(mock_home)
    home = mock_home.resolve()
    registry = load_registry()
    index = discover(home, home, registry)

    from skill_lens.models import dumps

    base_expected = build_compare_report("claude", "codex", home, home).to_dict()
    base_dumps = dumps(base_expected)

    # Neither (live default)
    rep_neither = run_compare("claude", "codex", cwd=home)
    assert rep_neither.to_dict() == base_expected
    assert dumps(rep_neither.to_dict()) == base_dumps

    # Index only
    rep_idx = run_compare("claude", "codex", cwd=home, index=index)
    assert rep_idx.to_dict() == base_expected
    assert dumps(rep_idx.to_dict()) == base_dumps
    b_idx = build_compare_report("claude", "codex", home, home, index=index)
    assert b_idx.to_dict() == base_expected
    assert dumps(b_idx.to_dict()) == base_dumps

    # Registry only
    rep_reg = run_compare("claude", "codex", cwd=home, registry=registry)
    assert rep_reg.to_dict() == base_expected
    assert dumps(rep_reg.to_dict()) == base_dumps
    b_reg = build_compare_report("claude", "codex", home, home, registry=registry)
    assert b_reg.to_dict() == base_expected
    assert dumps(b_reg.to_dict()) == base_dumps

    # Both
    rep_both = run_compare("claude", "codex", cwd=home, index=index, registry=registry)
    assert rep_both.to_dict() == base_expected
    assert dumps(rep_both.to_dict()) == base_dumps
    b_both = build_compare_report("claude", "codex", home, home, index=index, registry=registry)
    assert b_both.to_dict() == base_expected
    assert dumps(b_both.to_dict()) == base_dumps


def test_compare_frozen_index_and_missing_registry(mock_home: Path, tmp_path: Path) -> None:
    """Frozen index skips live discovery/loaders; missing registry raises ValueError first."""
    from unittest.mock import patch

    from skill_lens.core.compare import run_compare
    from skill_lens.core.snapshot_models import FrozenDiscoveryIndex
    from skill_lens.registry.loader import load_registry

    build_acceptance_farm(mock_home)
    home = mock_home.resolve()
    registry = load_registry()
    live_idx = discover(home, home, registry)
    frozen_idx = FrozenDiscoveryIndex(
        home=str(home), cwd=str(home), entries=tuple(live_idx.entries), unreadable_roots=()
    )

    # 1. Frozen index + registry skips patched discovery/loaders
    with (
        patch("skill_lens.core.compare.discover", side_effect=AssertionError("discover banned")),
        patch(
            "skill_lens.core.compare.live_discovery",
            side_effect=AssertionError("live_discovery banned"),
        ),
        patch(
            "skill_lens.core.compare.load_registry",
            side_effect=AssertionError("load_registry banned"),
        ),
    ):
        b_rep = build_compare_report(
            "claude", "codex", home, home, index=frozen_idx, registry=registry
        )
        w_rep = run_compare("claude", "codex", cwd=home, index=frozen_idx, registry=registry)
        assert b_rep.to_dict() == w_rep.to_dict()

    # 2. Missing registry for frozen calls raises ValueError first
    with (
        patch(
            "skill_lens.core.compare.load_registry",
            side_effect=AssertionError("load_registry banned"),
        ),
        patch(
            "skill_lens.core.compare.live_discovery",
            side_effect=AssertionError("live_discovery banned"),
        ),
    ):
        with pytest.raises(ValueError, match="registry"):
            build_compare_report("claude", "codex", home, home, index=frozen_idx, registry=None)
        with pytest.raises(ValueError, match="registry"):
            run_compare("claude", "codex", cwd=home, index=frozen_idx, registry=None)


def test_compare_empty_registry_and_unknown_ids_rejected_before_scanning(
    mock_home: Path, tmp_path: Path
) -> None:
    """Explicit {} registry is not replaced; invalid ids are rejected before scanning."""
    from unittest.mock import patch

    from skill_lens.core.compare import run_compare

    home = mock_home.resolve()

    # Explicit {} is not replaced
    with pytest.raises(KeyError, match="unknown agent 'claude'. Known agents: "):
        run_compare("claude", "codex", cwd=home, registry={})
    with pytest.raises(KeyError, match="unknown agent 'claude'. Known agents: "):
        build_compare_report("claude", "codex", home, home, registry={})

    # Unknown agent id rejected before scanning
    with (
        patch(
            "skill_lens.core.compare.live_discovery",
            side_effect=AssertionError("live_discovery must not be called for unknown agent"),
        ),
        pytest.raises(KeyError, match="unknown agent 'nope'"),
    ):
        run_compare("nope", "codex", cwd=home)


def test_compare_wrapper_uses_index_home_cwd_and_bans_ambient_lookups(
    mock_home: Path, tmp_path: Path
) -> None:
    """Give index.home, index.cwd, wrapper cwd distinct fixture paths; report uses index."""
    from unittest.mock import patch

    from skill_lens.core.compare import run_compare
    from skill_lens.core.snapshot_models import FrozenDiscoveryIndex
    from skill_lens.registry.loader import load_registry

    path_index_home = tmp_path / "distinct_index_home"
    path_index_cwd = tmp_path / "distinct_index_cwd"
    path_wrapper_cwd = tmp_path / "distinct_wrapper_cwd"
    path_index_home.mkdir()
    path_index_cwd.mkdir()
    path_wrapper_cwd.mkdir()

    registry = load_registry()
    frozen_idx = FrozenDiscoveryIndex(
        home=str(path_index_home),
        cwd=str(path_index_cwd),
        entries=(),
        unreadable_roots=(),
    )

    with (
        patch("skill_lens.core.paths.home", side_effect=AssertionError("ambient home banned")),
        patch("pathlib.Path.cwd", side_effect=AssertionError("ambient cwd banned")),
    ):
        report = run_compare(
            "claude",
            "codex",
            cwd=path_wrapper_cwd,
            index=frozen_idx,
            registry=registry,
        )
        assert report.home == str(path_index_home)
        assert report.cwd == str(path_index_cwd)
