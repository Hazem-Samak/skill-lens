"""Tests for frontmatter parsing, identity extraction and canonicalization."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from skill_lens.core.parser import (
    canonicalize,
    find_skill_document,
    parse_skill,
    parse_skill_document,
    split_frontmatter,
)
from skill_lens.models.enums import ParseStatus
from skill_lens.models.parsing import (
    ERR_DANGLING_SYMLINK,
    ERR_MALFORMED_YAML,
    ERR_MISSING_DESCRIPTION,
    ERR_MISSING_FRONTMATTER,
    ERR_SYMLINK_CYCLE,
    ERR_UNDECODABLE_TEXT,
    CanonicalStatus,
)
from tests.fixtures.builders import make_skill, symlink, write_skill

# --- split_frontmatter -----------------------------------------------------


def test_split_frontmatter_basic() -> None:
    frontmatter, body = split_frontmatter("---\nname: x\n---\nBody\n")
    assert frontmatter == "name: x"
    assert body == "Body\n"


def test_split_frontmatter_no_fence() -> None:
    frontmatter, body = split_frontmatter("# Just a body\n")
    assert frontmatter is None
    assert body == "# Just a body\n"


def test_split_frontmatter_unterminated_fence() -> None:
    frontmatter, body = split_frontmatter("---\nname: x\nBody without closing\n")
    assert frontmatter is None
    assert "Body without closing" in body


def test_split_frontmatter_tolerates_bom() -> None:
    frontmatter, _ = split_frontmatter("\ufeff---\nname: x\n---\nBody\n")
    assert frontmatter == "name: x"


def test_split_frontmatter_preserves_body_newline() -> None:
    _, body = split_frontmatter("---\nname: x\n---\nBody text")
    assert body.endswith("\n")


# --- parse_skill_document --------------------------------------------------


def test_parse_valid_document(tmp_path: Path) -> None:
    path = make_skill(tmp_path / "deploy", "deploy", "Deploy things.")
    result = parse_skill_document(path)
    assert result.status is ParseStatus.VALID
    assert result.directory_name == "deploy"
    assert result.frontmatter_name == "deploy"
    assert result.description == "Deploy things."
    assert result.is_valid


def test_parse_missing_description(tmp_path: Path) -> None:
    path = write_skill(tmp_path / "nodesc", "---\nname: nodesc\n---\nBody\n")
    result = parse_skill_document(path)
    assert result.status is ParseStatus.MISSING_DESCRIPTION
    assert ERR_MISSING_DESCRIPTION in result.errors


def test_parse_malformed_yaml(tmp_path: Path) -> None:
    path = write_skill(tmp_path / "broken", "---\nname: [unclosed\ndescription: x\n---\n")
    result = parse_skill_document(path)
    assert result.status is ParseStatus.MALFORMED_YAML
    assert ERR_MALFORMED_YAML in result.errors


def test_parse_missing_frontmatter(tmp_path: Path) -> None:
    path = write_skill(tmp_path / "plain", "# No frontmatter here\n")
    result = parse_skill_document(path)
    assert result.status is ParseStatus.MALFORMED_YAML
    assert ERR_MISSING_FRONTMATTER in result.errors


def test_parse_frontmatter_not_a_mapping(tmp_path: Path) -> None:
    path = write_skill(tmp_path / "list", "---\n- a\n- b\n---\nbody\n")
    result = parse_skill_document(path)
    assert result.status is ParseStatus.MALFORMED_YAML


def test_parse_undecodable_text(tmp_path: Path) -> None:
    path = tmp_path / "binary" / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\xff\xfe\x00\x01 not utf8")
    result = parse_skill_document(path)
    assert result.status is ParseStatus.UNREADABLE
    assert ERR_UNDECODABLE_TEXT in result.errors


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permissions")
def test_parse_permission_denied(tmp_path: Path) -> None:
    path = make_skill(tmp_path / "blocked", "blocked", "Nope.")
    os.chmod(path.parent, 0o000)
    try:
        result = parse_skill_document(path)
        assert result.status is ParseStatus.UNREADABLE
    finally:
        os.chmod(path.parent, 0o755)


def test_parse_directory_name_differs_from_frontmatter(tmp_path: Path) -> None:
    """Claude uses the directory name; Codex uses frontmatter. Both are kept."""
    path = make_skill(tmp_path / "dir-name", "frontmatter-name", "Desc.")
    result = parse_skill_document(path)
    assert result.directory_name == "dir-name"
    assert result.frontmatter_name == "frontmatter-name"
    assert result.identity == "frontmatter-name"


def test_parse_standalone_file_name(tmp_path: Path) -> None:
    path = tmp_path / "skills" / "deploy.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\nname: deploy\ndescription: Standalone.\n---\nBody\n", encoding="utf-8")
    result = parse_skill_document(path)
    assert result.directory_name == "deploy"
    assert result.status is ParseStatus.VALID


def test_parse_preserves_extra_frontmatter(tmp_path: Path) -> None:
    path = make_skill(tmp_path / "extra", "extra", "Has extras.", extra={"allowed-tools": "Bash"})
    result = parse_skill_document(path)
    assert result.frontmatter["allowed-tools"] == "Bash"


# --- find_skill_document / parse_skill -------------------------------------


def test_find_skill_document_in_directory(tmp_path: Path) -> None:
    entry = tmp_path / "deploy"
    make_skill(entry, "deploy", "Desc.")
    assert find_skill_document(entry) == entry / "SKILL.md"


def test_find_skill_document_standalone_file(tmp_path: Path) -> None:
    entry = tmp_path / "deploy.md"
    entry.write_text("---\nname: deploy\ndescription: x\n---\n", encoding="utf-8")
    assert find_skill_document(entry) == entry


def test_find_skill_document_absent(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert find_skill_document(empty) is None


def test_parse_skill_returns_none_without_document(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert parse_skill(empty) is None


# --- canonicalize ----------------------------------------------------------


def test_canonicalize_plain_directory(tmp_path: Path) -> None:
    entry = tmp_path / "deploy"
    entry.mkdir()
    result = canonicalize(entry)
    assert result.status is CanonicalStatus.OK
    assert result.is_symlink is False
    assert Path(result.resolved_path or "") == entry


def test_canonicalize_symlink_to_directory(tmp_path: Path) -> None:
    target = tmp_path / ".agents" / "skills" / "shared"
    target.mkdir(parents=True)
    link = tmp_path / ".claude" / "skills" / "shared"
    symlink(target, link)
    result = canonicalize(link)
    assert result.status is CanonicalStatus.OK
    assert result.is_symlink is True
    assert Path(result.resolved_path or "").resolve() == target.resolve()


def test_canonicalize_relative_symlink_chain(tmp_path: Path) -> None:
    target = tmp_path / "real"
    target.mkdir()
    os.symlink("real", tmp_path / "one")
    second = tmp_path / "two"
    os.symlink("one", second)
    result = canonicalize(second)
    assert result.status is CanonicalStatus.OK
    assert Path(result.resolved_path or "") == target


def test_canonicalize_dangling_symlink(tmp_path: Path) -> None:
    link = tmp_path / "dangling"
    os.symlink(tmp_path / "does-not-exist", link)
    result = canonicalize(link)
    assert result.status is CanonicalStatus.BROKEN
    assert result.error == ERR_DANGLING_SYMLINK


def test_canonicalize_cycle_is_guarded(tmp_path: Path) -> None:
    a = tmp_path / "cycle_a"
    b = tmp_path / "cycle_b"
    os.symlink(b, a)
    os.symlink(a, b)
    result = canonicalize(a)
    assert result.status is CanonicalStatus.CYCLE
    assert result.error == ERR_SYMLINK_CYCLE


def test_canonicalize_self_cycle(tmp_path: Path) -> None:
    link = tmp_path / "self"
    os.symlink(link, link)
    result = canonicalize(link)
    assert result.status is CanonicalStatus.CYCLE
