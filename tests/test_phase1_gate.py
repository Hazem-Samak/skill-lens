"""Phase 1 gate: the parser must handle every golden fixture scenario.

Each scenario is materialised into a mock home, then every discovered
entrypoint is canonicalized, parsed and hashed. The results are checked
against the hand-written ``golden/<name>.json`` expectations, so the parser
cannot silently drift away from the agreed contract.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_lens.core.hasher import hash_path
from skill_lens.core.parser import canonicalize, parse_skill
from skill_lens.models.enums import Scope
from skill_lens.models.parsing import CanonicalStatus
from tests.fixtures.discovery import list_skill_entrypoints
from tests.fixtures.scenarios import (
    SCENARIO_NAMES,
    build_scenario,
    teardown_scenario,
)

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"


def _golden(name: str) -> dict:
    return json.loads((GOLDEN_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _scope_for(entrypoint: Path, home: Path) -> Scope:
    """Classify an entrypoint's scope from its position in the fixture tree."""
    relative = entrypoint.relative_to(home)
    if relative.parts and relative.parts[0] == "project":
        return Scope.PROJECT
    if ".system" in relative.parts:
        return Scope.SYSTEM
    if ".tmp" in relative.parts and "plugins" in relative.parts:
        return Scope.PLUGIN
    return Scope.USER


@pytest.mark.parametrize("name", SCENARIO_NAMES)
def test_parser_handles_every_scenario(name: str, mock_home: Path) -> None:
    """Every entrypoint parses into a known status without raising."""
    build_scenario(name, mock_home)
    try:
        entries = list_skill_entrypoints(mock_home)
        assert entries, "scenario produced no entrypoints"
        for entrypoint in entries:
            canonical = canonicalize(entrypoint)
            if canonical.status is CanonicalStatus.OK:
                result = parse_skill(entrypoint)
                assert result is not None, f"no document for {entrypoint}"
                assert result.status in {
                    "valid",
                    "malformed_yaml",
                    "missing_description",
                    "unreadable",
                }
    finally:
        teardown_scenario(name, mock_home)


@pytest.mark.parametrize("name", SCENARIO_NAMES)
def test_canonical_paths_match_golden(name: str, mock_home: Path) -> None:
    """Every golden installation's canonical_path exists in the parsed output."""
    build_scenario(name, mock_home)
    try:
        golden = _golden(name)
        found = {
            canonicalize(entrypoint).resolved_path
            for entrypoint in list_skill_entrypoints(mock_home)
        }
        for expected in golden["installations"]:
            if expected["parse_status"] == "unreadable" and expected.get("errors") == [
                "symlink_cycle"
            ]:
                continue  # cycles have no resolvable canonical path
            canonical_str = str(mock_home / expected["canonical_path"])
            matches = {
                path
                for path in found
                if path is not None and Path(path).resolve() == Path(canonical_str).resolve()
            }
            assert matches, f"{name}: no canonical match for {expected['canonical_path']}"
    finally:
        teardown_scenario(name, mock_home)


@pytest.mark.parametrize("name", SCENARIO_NAMES)
def test_parse_status_matches_golden(name: str, mock_home: Path) -> None:
    """The parser's status for each golden skill matches the expectation."""
    build_scenario(name, mock_home)
    try:
        golden = _golden(name)
        by_name: dict[str, str] = {}
        for entrypoint in list_skill_entrypoints(mock_home):
            result = parse_skill(entrypoint)
            if result is not None:
                by_name[result.directory_name] = result.status.value

        for expected in golden["installations"]:
            skill = expected["name"]
            if skill not in by_name:
                continue
            assert by_name[skill] == expected["parse_status"], (
                f"{name}: {skill} parsed as {by_name[skill]}, expected {expected['parse_status']}"
            )
    finally:
        teardown_scenario(name, mock_home)


def test_malformed_scenario_statuses(mock_home: Path) -> None:
    build_scenario("malformed_frontmatter", mock_home)
    statuses = {
        result.directory_name: result.status.value
        for entrypoint in list_skill_entrypoints(mock_home)
        if (result := parse_skill(entrypoint)) is not None
    }
    assert statuses["broken"] == "malformed_yaml"
    assert statuses["nodesc"] == "missing_description"


def test_antigravity_standalone_file_parsed(mock_home: Path) -> None:
    build_scenario("antigravity_file_based", mock_home)
    results = {
        result.directory_name: result
        for entrypoint in list_skill_entrypoints(mock_home)
        if (result := parse_skill(entrypoint)) is not None
    }
    assert results["deploy"].status.value == "valid"
    assert results["deploy"].source_path.endswith("deploy.md")


def test_symlink_farm_shares_one_hash(mock_home: Path) -> None:
    """All entrypoints of a symlink farm fingerprint to the same content hash."""
    build_scenario("symlink_farm_multi_agent", mock_home)
    entries = [e for e in list_skill_entrypoints(mock_home) if e.is_symlink()]
    assert len(entries) == 3
    hashes = {hash_path(e) for e in entries}
    assert len(hashes) == 1


def test_variant_scenario_produces_two_hashes(mock_home: Path) -> None:
    """Differing bytes for one name must produce two distinct hashes."""
    build_scenario("variant_hash_detection", mock_home)
    by_name: dict[str, set[str]] = {}
    for entrypoint in list_skill_entrypoints(mock_home):
        result = parse_skill(entrypoint)
        if result is not None:
            by_name.setdefault(result.directory_name, set()).add(hash_path(entrypoint))
    assert len(by_name["deploy"]) == 2


def test_symlink_cycle_is_detected_not_hung(mock_home: Path) -> None:
    build_scenario("symlink_cycle_guard", mock_home)
    statuses = {canonicalize(entrypoint).status for entrypoint in list_skill_entrypoints(mock_home)}
    assert CanonicalStatus.CYCLE in statuses


def test_tcc_blocked_root_is_survived(mock_home: Path) -> None:
    """A permission-blocked skill dir must not abort discovery or parsing."""
    build_scenario("tcc_permission_error", mock_home)
    try:
        entries = list_skill_entrypoints(mock_home)
        names = {
            result.directory_name
            for entrypoint in entries
            if (result := parse_skill(entrypoint)) is not None
        }
        assert "ok" in names
        blocked = mock_home / ".claude" / "skills" / "blocked"
        assert blocked in entries
        blocked_result = parse_skill(blocked)
        assert blocked_result is not None
        assert blocked_result.status.value == "unreadable"
    finally:
        teardown_scenario("tcc_permission_error", mock_home)


def test_system_container_name_is_not_system(mock_home: Path) -> None:
    build_scenario("system_container_traversal", mock_home)
    entries = list_skill_entrypoints(mock_home)
    names = {
        result.directory_name
        for entrypoint in entries
        if (result := parse_skill(entrypoint)) is not None
    }
    assert names == {"imagegen"}
    assert _scope_for(entries[0], mock_home) is Scope.SYSTEM
