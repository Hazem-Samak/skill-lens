"""Tests for the streaming SHA-256 fingerprinting rules."""

from __future__ import annotations

from pathlib import Path

from skill_lens.core.hasher import (
    HASH_PREFIX,
    hash_directory,
    hash_file,
    hash_path,
    iter_files,
)
from tests.fixtures.builders import make_skill, symlink

# --- hash_file -------------------------------------------------------------


def test_hash_file_has_prefix(tmp_path: Path) -> None:
    path = tmp_path / "a.txt"
    path.write_text("hello\n", encoding="utf-8")
    digest = hash_file(path)
    assert digest.startswith(HASH_PREFIX)
    assert len(digest) == len(HASH_PREFIX) + 64


def test_hash_file_is_deterministic(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("same\n", encoding="utf-8")
    b.write_text("same\n", encoding="utf-8")
    assert hash_file(a) == hash_file(b)


def test_hash_file_crlf_normalisation(tmp_path: Path) -> None:
    """CRLF and LF text must fingerprint identically."""
    lf = tmp_path / "lf.txt"
    crlf = tmp_path / "crlf.txt"
    lf.write_bytes(b"line1\nline2\n")
    crlf.write_bytes(b"line1\r\nline2\r\n")
    assert hash_file(lf) == hash_file(crlf)


def test_hash_file_only_normalises_crlf(tmp_path: Path) -> None:
    """Only CRLF is normalised; a lone CR is a real byte difference."""
    mac = tmp_path / "cr.txt"
    unix = tmp_path / "lf.txt"
    mac.write_bytes(b"a\rb\r")
    unix.write_bytes(b"a\nb\n")
    assert hash_file(mac) != hash_file(unix)


def test_hash_file_detects_any_byte_change(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("x" * 5000, encoding="utf-8")
    b.write_text("x" * 4999 + "y", encoding="utf-8")
    assert hash_file(a) != hash_file(b)


def test_hash_file_binary_is_raw(tmp_path: Path) -> None:
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    # Bytes that are NOT valid UTF-8 are hashed raw, so a CRLF difference shows.
    a.write_bytes(b"\xff\xfe\x00\r\n")
    b.write_bytes(b"\xff\xfe\x00\n")
    assert hash_file(a) != hash_file(b)


def test_hash_file_streams_beyond_chunk_size(tmp_path: Path) -> None:
    """No 1 MiB truncation: a difference past the first chunk is detected."""
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("A" * (200 * 1024) + "END", encoding="utf-8")
    b.write_text("A" * (200 * 1024) + "end", encoding="utf-8")
    assert hash_file(a) != hash_file(b)


# --- iter_files ------------------------------------------------------------


def test_iter_files_is_sorted_posix(tmp_path: Path) -> None:
    for name in ("b", "a", "c"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    result = [p.as_posix() for p in iter_files(tmp_path)]
    assert result == ["a", "b", "c"]


def test_iter_files_ignores_vcs_and_macos(tmp_path: Path) -> None:
    (tmp_path / "keep.txt").write_text("keep", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x", encoding="utf-8")
    (tmp_path / ".DS_Store").write_text("junk", encoding="utf-8")
    (tmp_path / "._resource").write_text("appledouble", encoding="utf-8")
    assert [p.as_posix() for p in iter_files(tmp_path)] == ["keep.txt"]


def test_iter_files_nested_sorting(tmp_path: Path) -> None:
    (tmp_path / "z").mkdir()
    (tmp_path / "a").mkdir()
    (tmp_path / "z" / "one.txt").write_text("1", encoding="utf-8")
    (tmp_path / "a" / "two.txt").write_text("2", encoding="utf-8")
    assert [p.as_posix() for p in iter_files(tmp_path)] == ["a/two.txt", "z/one.txt"]


# --- hash_directory --------------------------------------------------------


def test_hash_directory_stable_across_trees(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    make_skill(first, "deploy", "Deploy things.")
    make_skill(second, "deploy", "Deploy things.")
    assert hash_directory(first) == hash_directory(second)


def test_hash_directory_detects_edit(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    make_skill(first, "deploy", "Deploy things.")
    make_skill(second, "deploy", "Deploy things.", body="# Different body\n")
    assert hash_directory(first) != hash_directory(second)


def test_hash_directory_detects_added_file(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    make_skill(first, "deploy", "Deploy things.")
    make_skill(second, "deploy", "Deploy things.")
    (second / "extra.txt").write_text("extra", encoding="utf-8")
    assert hash_directory(first) != hash_directory(second)


def test_hash_directory_ignores_vcs(tmp_path: Path) -> None:
    root = tmp_path / "skill"
    make_skill(root, "deploy", "Deploy things.")
    before = hash_directory(root)
    (root / ".git").mkdir()
    (root / ".git" / "HEAD").write_text("ref", encoding="utf-8")
    assert hash_directory(root) == before


# --- hash_path -------------------------------------------------------------


def test_hash_path_dispatches_directory(tmp_path: Path) -> None:
    root = tmp_path / "skill"
    make_skill(root, "deploy", "Deploy things.")
    assert hash_path(root) == hash_directory(root)


def test_hash_path_dispatches_file(tmp_path: Path) -> None:
    path = tmp_path / "deploy.md"
    path.write_text("---\nname: deploy\ndescription: x\n---\n", encoding="utf-8")
    assert hash_path(path) == hash_file(path)


def test_hash_path_follows_symlink(tmp_path: Path) -> None:
    """A symlink entrypoint fingerprints the same as its canonical target."""
    target = tmp_path / ".agents" / "skills" / "shared"
    make_skill(target, "shared", "Shared.")
    link = tmp_path / ".claude" / "skills" / "shared"
    symlink(target, link)
    assert hash_path(link) == hash_path(target)
