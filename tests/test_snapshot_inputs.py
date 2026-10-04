"""Acceptance tests for Step 0 pure helpers (Assignment C1).

Specification reference: FULL_SCREEN_TUI.md §21.3, §21.6, and §22.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from skill_lens.core.discovery import DiscoveredEntry
from skill_lens.core.hasher import (
    hash_bytes,
    hash_captured_directory,
    hash_directory,
    hash_file,
    iter_files,
    normalized_text,
)
from skill_lens.core.parser import (
    ERR_UNDECODABLE_TEXT,
    ParseResult,
    ParseStatus,
    parse_skill_bytes,
    parse_skill_document,
)
from skill_lens.core.resolver import (
    _load_disabled_overrides,
    disabled_overrides_from_bytes,
    lookup_name_for_entry,
)
from skill_lens.models.parsing import CanonicalResult, CanonicalStatus
from skill_lens.registry.loader import AgentDefinition, AgentRoot, load_registry


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


# ---------------------------------------------------------------------------
# 1. Hasher Parity Tests (§21.6)
# ---------------------------------------------------------------------------


def test_hash_bytes_matches_streaming(tmp_path: Path) -> None:
    """Compare hash_bytes and hash_file streaming for all required variations."""
    cases: list[tuple[str, bytes]] = [
        # Empty file
        ("empty.txt", b""),
        # Standard LF
        ("lf.txt", b"# Title\nLine 1\nLine 2\n"),
        # CRLF crossing the 64 KiB buffer boundary (chunk size = 64 * 1024)
        (
            "crlf_boundary.txt",
            b"A" * 65535 + b"\r\nMore content after the boundary.\r\n",
        ),
        # Lone CR crossing the buffer boundary
        (
            "cr_boundary.txt",
            b"A" * 65535 + b"\rMore content after the boundary.\n",
        ),
        # Lone CR (not followed by LF)
        ("lone_cr.txt", b"Line 1\rLine 2 without LF\rLine 3\n"),
        # Trailing lone CR at EOF
        ("trailing_cr.txt", b"Body with trailing CR\r"),
        # UTF-8 BOM
        ("bom.txt", b"\xef\xbb\xbf# Title with BOM\r\nSome body\r\n"),
        # Valid UTF-8 with embedded NUL byte
        ("nul.txt", b"Valid text with \x00 embedded NUL byte\r\nLine 2\n"),
        # Invalid UTF-8
        ("invalid_utf8.bin", b"\xff\xfe\x00\x00Not UTF-8 binary data\x80\x81\x82"),
        # > 1 MiB file
        ("large1.txt", b"Header\r\n" + b"X" * (1024 * 1024) + b"\r\nFooter Alpha\r\n"),
        ("large2.txt", b"Header\r\n" + b"X" * (1024 * 1024) + b"\r\nFooter Beta\r\n"),
    ]

    for filename, content in cases:
        file_path = tmp_path / filename
        _write(file_path, content)

        streaming_hash = hash_file(file_path)
        byte_hash = hash_bytes(content)

        assert byte_hash == streaming_hash, f"Hash mismatch for {filename}"

    # Verify that changing near the end of >1 MiB file changes the fingerprint
    h1 = hash_bytes(cases[-2][1])
    h2 = hash_bytes(cases[-1][1])
    assert h1 != h2, "Large files differing at end must produce different hashes"


def test_normalized_text_rules() -> None:
    """Verify UTF-8 decoding and CRLF normalization rules."""
    assert normalized_text(b"hello\r\nworld\r\n") == "hello\nworld\n"
    assert normalized_text(b"hello\rworld") == "hello\rworld"
    assert normalized_text(b"\xff\xfe") is None
    assert normalized_text(b"text\x00with\x00nul") == "text\x00with\x00nul"


def test_captured_directory_matches_live_hash(tmp_path: Path) -> None:
    """Compare hash_captured_directory and live hash_directory with exclusions and order."""
    root = tmp_path / "skill_dir"
    root.mkdir()

    # Nested files
    _write(root / "SKILL.md", b"---\nname: skill-test\ndescription: Test\n---\n# Body\n")
    _write(root / "scripts" / "run.sh", b"#!/bin/bash\necho 'running'\n")
    _write(root / "docs" / "guide.md", b"# Guide\r\nWindows style line endings.\r\n")
    _write(root / "assets" / "data.bin", b"\xff\xfe\x00\x01\x02binary")

    # Files whose path sorting opposes their content hash sorting:
    # 'a_file.txt' < 'z_file.txt', but hash('z_file.txt') < hash('a_file.txt')
    _write(root / "a_file.txt", b"content_a_1")
    _write(root / "z_file.txt", b"content_z_1")

    # Excluded items: .git, .DS_Store, AppleDouble ._*
    _write(root / ".git" / "config", b"[core]\nrepositoryformatversion = 0\n")
    _write(root / ".git" / "HEAD", b"ref: refs/heads/main\n")
    _write(root / ".DS_Store", b"junk")
    _write(root / "scripts" / ".DS_Store", b"junk")
    _write(root / "._SKILL.md", b"appledouble")

    live_hash = hash_directory(root)

    # Collect pairs from iter_files (which excludes ignored files)
    pairs = [(rel.as_posix(), hash_bytes((root / rel).read_bytes())) for rel in iter_files(root)]

    # Verify exclusions are not present
    rel_paths = [p[0] for p in pairs]
    assert not any(".git" in p for p in rel_paths)
    assert not any(".DS_Store" in p for p in rel_paths)
    assert not any("._" in p for p in rel_paths)

    # Shuffled input order must produce the identical directory aggregate
    shuffled_pairs = list(reversed(pairs))
    captured_hash = hash_captured_directory(shuffled_pairs)
    assert captured_hash == live_hash

    # Renamed file changes the hash
    renamed_pairs = [(p if p != "scripts/run.sh" else "scripts/exec.sh", h) for p, h in pairs]
    assert hash_captured_directory(renamed_pairs) != live_hash

    # Standalone file hash is not equal to directory aggregate
    standalone_bytes = (root / "SKILL.md").read_bytes()
    standalone_hash = hash_bytes(standalone_bytes)
    single_file_dir_hash = hash_captured_directory([("SKILL.md", standalone_hash)])
    assert standalone_hash != single_file_dir_hash


# ---------------------------------------------------------------------------
# 2. Parser Parity Tests (§21.6)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        # Valid directory skill
        ("valid/SKILL.md", b"---\nname: valid-skill\ndescription: Valid\n---\n# Body\nText\n"),
        # Malformed YAML
        ("malformed/SKILL.md", b"---\nname: [unclosed yaml\ndescription: test\n---\nBody\n"),
        # Missing description
        ("missing_desc/SKILL.md", b"---\nname: no-desc\n---\nBody\n"),
        # Lowercase skill.md
        ("lower/skill.md", b"---\nname: lower-skill\ndescription: Lowercase\n---\nBody\n"),
        # Standalone file skill
        ("standalone.md", b"---\nname: standalone\ndescription: Standalone\n---\nBody\n"),
        # UTF-8 BOM
        ("bom/SKILL.md", b"\xef\xbb\xbf---\nname: bom-skill\ndescription: BOM\n---\nBody\n"),
        # Lone CR
        ("cr/SKILL.md", b"---\rname: cr-skill\rdescription: CR\r---\rBody with CR\r"),
        # Document without frontmatter containing lone CR
        (
            "no_fm_lone_cr.txt",
            b"# Plain document without frontmatter\rLine 2 with lone CR\rLine 3\n",
        ),
        # Undecodable bytes
        ("undecodable/SKILL.md", b"\xff\xfe\x00\x00invalid utf8"),
    ],
)
def test_byte_parser_matches_live_parser(tmp_path: Path, filename: str, content: bytes) -> None:
    """Compare parse_skill_bytes to parse_skill_document across all document types."""
    target_path = tmp_path / filename
    _write(target_path, content)

    live_res = parse_skill_document(target_path)
    byte_res = parse_skill_bytes(content, source_path=str(target_path))

    assert byte_res.status == live_res.status
    assert byte_res.directory_name == live_res.directory_name
    assert byte_res.frontmatter_name == live_res.frontmatter_name
    assert byte_res.description == live_res.description
    assert byte_res.body == live_res.body
    assert byte_res.source_path == live_res.source_path
    assert byte_res.errors == live_res.errors
    assert byte_res.to_dict() == live_res.to_dict()

    if content == b"\xff\xfe\x00\x00invalid utf8":
        assert byte_res.status == ParseStatus.UNREADABLE
        assert ERR_UNDECODABLE_TEXT in byte_res.errors


# ---------------------------------------------------------------------------
# 3. Identity Helper Tests (§21.6)
# ---------------------------------------------------------------------------


def _make_agent(agent_id: str, identity_source: str) -> AgentDefinition:
    return AgentDefinition(
        id=agent_id,
        name=agent_id.capitalize(),
        identity_source=identity_source,
        collision_policy="Personal > Project",
        policy_evidence="documented",
        coexist_policy="shadow",
        walk_boundary="git_worktree_root",
        unsearched_rule_id="test_unsearched",
        disabled_rule_id="test_disabled",
        disabled_settings=None,
        disabled_key=None,
        source="test",
        roots=(
            AgentRoot(
                id=f"{agent_id}_root",
                kind="global",
                path=f".{agent_id}/skills",
                scope="user",
                rank=100,
                rule_id="test_rule",
                evidence="documented",
            ),
        ),
    )


def test_selected_entry_uses_agent_identity() -> None:
    """Verify lookup_name_for_entry adheres to agent identity policies and fallback rules."""
    agent_dir = _make_agent("dir_agent", identity_source="directory_name")
    agent_fm = _make_agent("fm_agent", identity_source="frontmatter_name")
    agent_either = _make_agent("either_agent", identity_source="either")
    agent_hybrid = _make_agent("hybrid_agent", identity_source="hybrid")

    # Shipped agents exercising directory_name, frontmatter_name, and hybrid
    registry = load_registry()
    claude = registry["claude"]  # directory_name
    codex = registry["codex"]  # frontmatter_name
    antigravity = registry["antigravity"]  # hybrid

    # 1. folder-key/SKILL.md declaring name: declared-key
    parse_valid = ParseResult(
        status=ParseStatus.VALID,
        directory_name="folder-key",
        frontmatter_name="declared-key",
        description="A valid skill",
        body="# Body",
        source_path="/skills/folder-key/SKILL.md",
    )
    entry_valid = DiscoveredEntry(
        entrypoint_path="/skills/folder-key",
        name="folder-key",
        is_file=False,
        is_symlink=False,
        canonical=CanonicalResult(
            status=CanonicalStatus.OK,
            entrypoint_path="/skills/folder-key",
            resolved_path="/skills/folder-key",
            is_symlink=False,
        ),
        parse=parse_valid,
        content_hash="sha256:abc",
    )

    assert lookup_name_for_entry(entry_valid, agent_dir) == "folder-key"
    assert lookup_name_for_entry(entry_valid, agent_fm) == "declared-key"
    assert lookup_name_for_entry(entry_valid, agent_either) == "folder-key"
    assert lookup_name_for_entry(entry_valid, agent_hybrid) == "folder-key"
    assert lookup_name_for_entry(entry_valid, claude) == "folder-key"
    assert lookup_name_for_entry(entry_valid, codex) == "declared-key"
    assert lookup_name_for_entry(entry_valid, antigravity) == "folder-key"

    # 2. Invalid metadata with a usable declared name (missing description)
    parse_invalid_meta = ParseResult(
        status=ParseStatus.MISSING_DESCRIPTION,
        directory_name="folder-key",
        frontmatter_name="declared-key",
        description=None,
        body="# Body",
        source_path="/skills/folder-key/SKILL.md",
    )
    entry_invalid_meta = replace(entry_valid, parse=parse_invalid_meta)

    assert lookup_name_for_entry(entry_invalid_meta, agent_dir) == "folder-key"
    assert lookup_name_for_entry(entry_invalid_meta, agent_fm) == "declared-key"
    assert lookup_name_for_entry(entry_invalid_meta, agent_either) == "folder-key"
    assert lookup_name_for_entry(entry_invalid_meta, agent_hybrid) == "folder-key"
    assert lookup_name_for_entry(entry_invalid_meta, claude) == "folder-key"
    assert lookup_name_for_entry(entry_invalid_meta, codex) == "declared-key"
    assert lookup_name_for_entry(entry_invalid_meta, antigravity) == "folder-key"

    # 3. Absent frontmatter name (malformed YAML)
    parse_malformed = ParseResult(
        status=ParseStatus.MALFORMED_YAML,
        directory_name="folder-key",
        frontmatter_name=None,
        description=None,
        body="# Body",
        source_path="/skills/folder-key/SKILL.md",
    )
    entry_malformed = replace(entry_valid, parse=parse_malformed)

    # Frontmatter agent falls back to directory name when frontmatter_name is absent
    assert lookup_name_for_entry(entry_malformed, agent_dir) == "folder-key"
    assert lookup_name_for_entry(entry_malformed, agent_fm) == "folder-key"
    assert lookup_name_for_entry(entry_malformed, agent_either) == "folder-key"
    assert lookup_name_for_entry(entry_malformed, agent_hybrid) == "folder-key"
    assert lookup_name_for_entry(entry_malformed, claude) == "folder-key"
    assert lookup_name_for_entry(entry_malformed, codex) == "folder-key"
    assert lookup_name_for_entry(entry_malformed, antigravity) == "folder-key"

    # 4. Absent parse (entry.parse is None)
    entry_no_parse = replace(entry_valid, parse=None)
    assert lookup_name_for_entry(entry_no_parse, agent_dir) == "folder-key"
    assert lookup_name_for_entry(entry_no_parse, agent_fm) == "folder-key"
    assert lookup_name_for_entry(entry_no_parse, agent_either) == "folder-key"
    assert lookup_name_for_entry(entry_no_parse, agent_hybrid) == "folder-key"
    assert lookup_name_for_entry(entry_no_parse, claude) == "folder-key"
    assert lookup_name_for_entry(entry_no_parse, codex) == "folder-key"
    assert lookup_name_for_entry(entry_no_parse, antigravity) == "folder-key"


# ---------------------------------------------------------------------------
# 4. Settings Decoder Tests (§21.3)
# ---------------------------------------------------------------------------


def test_disabled_overrides_from_bytes(tmp_path: Path) -> None:
    """Verify disabled_overrides_from_bytes and _load_disabled_overrides delegation."""
    registry = load_registry()
    claude = registry["claude"]

    # None data
    assert disabled_overrides_from_bytes(claude, None) == frozenset()

    # Agent without disabled settings
    bare_agent = _make_agent("bare", "directory_name")
    assert disabled_overrides_from_bytes(bare_agent, b'{"overrides": {}}') == frozenset()

    # Agent with disabled_settings set but disabled_key=None
    agent_no_key = replace(claude, disabled_key=None)
    assert disabled_overrides_from_bytes(agent_no_key, b'{"skillOverrides": {"a": false}}') == (
        frozenset()
    )

    # Agent with disabled_key set but disabled_settings=None
    agent_no_settings = replace(claude, disabled_settings=None)
    assert (
        disabled_overrides_from_bytes(agent_no_settings, b'{"skillOverrides": {"a": false}}')
        == frozenset()
    )

    # Agent with disabled_settings set but disabled_key="" (empty string)
    agent_empty_key = replace(claude, disabled_key="")
    assert disabled_overrides_from_bytes(agent_empty_key, b'{"": {"a": false}}') == frozenset()

    # Undecodable bytes and invalid JSON
    assert disabled_overrides_from_bytes(claude, b"\xff\xfe") == frozenset()
    assert disabled_overrides_from_bytes(claude, b"not json") == frozenset()

    # Non-object top levels
    assert disabled_overrides_from_bytes(claude, b"[]") == frozenset()
    assert disabled_overrides_from_bytes(claude, b"null") == frozenset()
    assert disabled_overrides_from_bytes(claude, b'"string"') == frozenset()
    assert disabled_overrides_from_bytes(claude, b"42") == frozenset()
    assert disabled_overrides_from_bytes(claude, b"true") == frozenset()

    # Non-object overrides field
    assert disabled_overrides_from_bytes(claude, b'{"skillOverrides": "disabled"}') == frozenset()
    assert disabled_overrides_from_bytes(claude, b'{"skillOverrides": [1, 2]}') == frozenset()
    assert disabled_overrides_from_bytes(claude, b'{"skillOverrides": null}') == frozenset()

    # Boolean is False check
    data = json.dumps(
        {
            "skillOverrides": {
                "disabled_one": False,
                "disabled_two": False,
                "enabled_one": True,
                "zero": 0,
                "none_val": None,
                "empty_str": "",
            }
        }
    ).encode("utf-8")

    result = disabled_overrides_from_bytes(claude, data)
    assert result == frozenset({"disabled_one", "disabled_two"})

    # Test delegation in _load_disabled_overrides
    settings_file = tmp_path / ".claude" / "settings.json"
    _write(settings_file, data)
    assert _load_disabled_overrides(claude, tmp_path) == {"disabled_one", "disabled_two"}

    # Missing file returns empty set
    missing_home = tmp_path / "nonexistent"
    assert _load_disabled_overrides(claude, missing_home) == set()
