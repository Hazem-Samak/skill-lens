"""Tests for the streaming SHA-256 fingerprinting rules."""

from __future__ import annotations

from pathlib import Path

import pytest

import skill_lens.core.hasher as hasher_module
from skill_lens.core.cancellation import CaptureCancelled, check_cancelled
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


# --- Cancellation -----------------------------------------------------------


def test_check_cancelled_helper() -> None:
    check_cancelled(None)
    check_cancelled(lambda: False)
    with pytest.raises(CaptureCancelled):
        check_cancelled(lambda: True)


def test_iter_files_cancelled(tmp_path: Path) -> None:
    for name in ("a", "b", "c"):
        (tmp_path / name).write_text(name, encoding="utf-8")

    # Cancelled before walk starts
    with pytest.raises(CaptureCancelled):
        iter_files(tmp_path, cancelled=lambda: True)

    # Cancelled after walking root directory and discovering files
    visited_files: list[str] = []

    def cancel_after_file() -> bool:
        return len(visited_files) >= 1

    orig_is_ignored = hasher_module._is_ignored

    def tracking_is_ignored(rel: Path) -> bool:
        visited_files.append(rel.as_posix())
        return orig_is_ignored(rel)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(hasher_module, "_is_ignored", tracking_is_ignored)
        with pytest.raises(CaptureCancelled):
            iter_files(tmp_path, cancelled=cancel_after_file)
    assert len(visited_files) >= 1, "Expected at least one file visited before cancellation"


def test_hash_file_cancelled_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "large.txt"
    # File is larger than one 64 KiB chunk
    path.write_text("X" * (200 * 1024), encoding="utf-8")

    # Cancelled before open
    with pytest.raises(CaptureCancelled):
        hash_file(path, cancelled=lambda: True)

    # Cancelled during text chunk streaming: prove at least 1 chunk was read
    read_chunks: list[int] = []

    class TrackingTextFile:
        def __init__(self, real_file: object) -> None:
            self._real = real_file

        def read(self, size: int = -1) -> str:
            chunk = self._real.read(size)
            if chunk:
                read_chunks.append(len(chunk))
            return chunk

        def __enter__(self) -> object:
            self._real.__enter__()
            return self

        def __exit__(self, *args: object) -> object:
            return self._real.__exit__(*args)

    orig_open = Path.open

    def tracked_open(self: Path, *args: object, **kwargs: object) -> object:
        handle = orig_open(self, *args, **kwargs)
        if self == path:
            return TrackingTextFile(handle)
        return handle

    monkeypatch.setattr(Path, "open", tracked_open)

    def cancel_after_first_text_chunk() -> bool:
        return len(read_chunks) >= 1

    with pytest.raises(CaptureCancelled):
        hash_file(path, cancelled=cancel_after_first_text_chunk)

    assert len(read_chunks) == 1, f"Expected exactly 1 text chunk read, got {len(read_chunks)}"


def test_hash_file_cancelled_binary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "large.bin"
    # Invalid UTF-8 prefix ensures _update_text fails with UnicodeDecodeError,
    # entering _update_binary fallback.
    path.write_bytes(b"\xff\xfe\x00" + b"Y" * (200 * 1024))

    # Cancelled before open
    with pytest.raises(CaptureCancelled):
        hash_file(path, cancelled=lambda: True)

    # Prove fallback: _update_text fails on UnicodeDecodeError, then _update_binary
    # reads at least 1 binary chunk before cancellation interrupts it.
    text_attempts: list[str] = []
    binary_reads: list[int] = []

    orig_update_text = hasher_module._update_text

    def tracked_update_text(hasher: object, p: Path, *, cancelled: object = None) -> None:
        text_attempts.append("text_failed_decoding")
        orig_update_text(hasher, p, cancelled=cancelled)  # type: ignore[arg-type]

    class TrackingBinaryFile:
        def __init__(self, real_file: object) -> None:
            self._real = real_file

        def read(self, size: int = -1) -> bytes:
            chunk = self._real.read(size)
            if chunk:
                binary_reads.append(len(chunk))
            return chunk

        def __enter__(self) -> object:
            self._real.__enter__()
            return self

        def __exit__(self, *args: object) -> object:
            return self._real.__exit__(*args)

    orig_open = Path.open

    def tracked_open(self: Path, *args: object, **kwargs: object) -> object:
        handle = orig_open(self, *args, **kwargs)
        if self == path and args and "b" in str(args[0]):
            return TrackingBinaryFile(handle)
        return handle

    monkeypatch.setattr(hasher_module, "_update_text", tracked_update_text)
    monkeypatch.setattr(Path, "open", tracked_open)

    def cancel_after_first_binary_chunk() -> bool:
        return len(binary_reads) >= 1

    with pytest.raises(CaptureCancelled):
        hash_file(path, cancelled=cancel_after_first_binary_chunk)

    assert len(text_attempts) == 1, (
        "Expected _update_text to be attempted and fail with UnicodeDecodeError"
    )
    assert len(binary_reads) == 1, f"Expected exactly 1 binary chunk read, got {len(binary_reads)}"


def test_hash_directory_cancelled(tmp_path: Path) -> None:
    root = tmp_path / "skill"
    make_skill(root, "deploy", "Deploy things.")
    (root / "file2.txt").write_text("another file", encoding="utf-8")

    # Cancelled before directory hash begins
    with pytest.raises(CaptureCancelled):
        hash_directory(root, cancelled=lambda: True)

    # Cancelled between files during directory aggregation
    hashed_files: list[str] = []
    orig_hash_file = hasher_module.hash_file

    def tracking_hash_file(p: Path, *, cancelled: object = None) -> str:
        hashed_files.append(p.name)
        return orig_hash_file(p, cancelled=cancelled)  # type: ignore[arg-type]

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(hasher_module, "hash_file", tracking_hash_file)

        def cancel_after_first_file() -> bool:
            return len(hashed_files) >= 1

        with pytest.raises(CaptureCancelled):
            hash_directory(root, cancelled=cancel_after_first_file)

    assert len(hashed_files) == 1, "Expected exactly 1 file hashed before cancellation"


def test_hash_path_cancelled(tmp_path: Path) -> None:
    root = tmp_path / "skill"
    make_skill(root, "deploy", "Deploy things.")
    file_path = tmp_path / "skill.md"
    file_path.write_text("# Skill", encoding="utf-8")

    # Immediate cancellation at hash_path entrance
    with pytest.raises(CaptureCancelled):
        hash_path(root, cancelled=lambda: True)

    # Prove cancelled is forwarded into hash_directory
    calls_dir = 0

    def cancel_in_hash_directory() -> bool:
        nonlocal calls_dir
        calls_dir += 1
        return calls_dir >= 2

    with pytest.raises(CaptureCancelled):
        hash_path(root, cancelled=cancel_in_hash_directory)
    assert calls_dir >= 2, "Expected check_cancelled inside hash_directory"

    # Prove cancelled is forwarded into hash_file
    calls_file = 0

    def cancel_in_hash_file() -> bool:
        nonlocal calls_file
        calls_file += 1
        return calls_file >= 2

    with pytest.raises(CaptureCancelled):
        hash_path(file_path, cancelled=cancel_in_hash_file)
    assert calls_file >= 2, "Expected check_cancelled inside hash_file"
