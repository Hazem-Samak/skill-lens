"""Streaming SHA-256 content fingerprinting.

Rules from the specification (section 4):

* Sorted relative file paths, always with forward slashes ``/``.
* Text files are decoded as UTF-8 with ``\\r\\n`` normalised to ``\\n``.
* Binary files are hashed raw, byte for byte.
* The **entire** file is streamed in chunks (no truncation, no prefix false
  positives).
* ``.git/``, ``.DS_Store`` and AppleDouble ``._*`` entries are ignored.
"""

from __future__ import annotations

import codecs
import hashlib
import os
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from skill_lens.core.cancellation import check_cancelled

if TYPE_CHECKING:
    from hashlib import _Hash

HASH_PREFIX = "sha256:"
_CHUNK_SIZE = 64 * 1024
_IGNORED_DIRS = frozenset({".git"})
_IGNORED_FILES = frozenset({".DS_Store"})


class IncompleteTreeError(OSError):
    """Raised when directory traversal or file reading is incomplete."""

    def __init__(self, path: Path | str, reason: str = "denied", *, payload_bytes: int = 0) -> None:
        self.path = Path(path)
        self.reason = reason
        self.payload_bytes = payload_bytes
        super().__init__(f"Cannot read '{self.path}': {self.reason}")


class PayloadLimitExceeded(Exception):
    """A bounded fingerprint read crossed the byte allowance it was given."""

    def __init__(self, path: Path, limit_bytes: int, total_bytes: int) -> None:
        self.path = path
        self.limit_bytes = limit_bytes
        self.total_bytes = total_bytes
        super().__init__(f"'{path}' read past the {limit_bytes}-byte payload limit")


def _is_ignored(relative: Path) -> bool:
    """True for paths the fingerprint must skip (VCS, macOS metadata)."""
    if any(part in _IGNORED_DIRS for part in relative.parts):
        return True
    name = relative.name
    return name in _IGNORED_FILES or name.startswith("._")


def iter_files(root: Path, *, cancelled: Callable[[], bool] | None = None) -> list[Path]:
    """Return the hashable files under ``root`` in sorted, stable order.

    Only relative paths are returned, sorted as POSIX strings so the same tree
    fingerprints identically on macOS and Linux.
    """
    check_cancelled(cancelled)
    collected: list[Path] = []
    walk_errors: list[OSError] = []

    def _on_walk_error(err: OSError) -> None:
        walk_errors.append(err)

    for dirpath, dirnames, filenames in os.walk(root, onerror=_on_walk_error):
        check_cancelled(cancelled)
        dirnames[:] = sorted(d for d in dirnames if d not in _IGNORED_DIRS)
        for filename in sorted(filenames):
            check_cancelled(cancelled)
            candidate = Path(dirpath) / filename
            relative = candidate.relative_to(root)
            if not _is_ignored(relative):
                collected.append(relative)

    if walk_errors:
        first = walk_errors[0]
        p = Path(getattr(first, "filename", None) or root)
        if isinstance(first, PermissionError):
            reason = "denied"
        elif isinstance(first, FileNotFoundError):
            reason = "disappeared"
        else:
            reason = "io"
        raise IncompleteTreeError(path=p, reason=reason) from first

    collected.sort(key=lambda p: p.as_posix())
    return collected


def _update_text(hasher: _Hash, path: Path, *, cancelled: Callable[[], bool] | None = None) -> None:
    """Stream ``path`` as UTF-8 text, normalising ``\\r\\n`` across chunks."""
    check_cancelled(cancelled)
    pending_cr = False
    with path.open("r", encoding="utf-8", newline="") as handle:
        while True:
            check_cancelled(cancelled)
            chunk = handle.read(_CHUNK_SIZE)
            if not chunk:
                break
            if pending_cr:
                chunk = "\r" + chunk
                pending_cr = False
            if chunk.endswith("\r"):
                chunk = chunk[:-1]
                pending_cr = True
            hasher.update(chunk.replace("\r\n", "\n").encode("utf-8"))
        if pending_cr:
            hasher.update(b"\r")


def _update_binary(
    hasher: _Hash, path: Path, *, cancelled: Callable[[], bool] | None = None
) -> None:
    check_cancelled(cancelled)
    with path.open("rb") as handle:
        while True:
            check_cancelled(cancelled)
            chunk = handle.read(_CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)


def hash_file(path: Path, *, cancelled: Callable[[], bool] | None = None) -> str:
    """Fingerprint a single file, choosing text or binary handling.

    UTF-8 decodability decides: decodable files are newline-normalised as text;
    anything else is hashed as raw bytes.
    """
    check_cancelled(cancelled)
    text_hasher = hashlib.sha256()
    try:
        _update_text(text_hasher, path, cancelled=cancelled)
    except UnicodeDecodeError:
        binary_hasher = hashlib.sha256()
        try:
            _update_binary(binary_hasher, path, cancelled=cancelled)
        except IncompleteTreeError:
            raise
        except OSError as err:
            reason = (
                "denied"
                if isinstance(err, PermissionError)
                else ("disappeared" if isinstance(err, FileNotFoundError) else "io")
            )
            raise IncompleteTreeError(path=path, reason=reason) from err
        return HASH_PREFIX + binary_hasher.hexdigest()
    except IncompleteTreeError:
        raise
    except OSError as err:
        reason = (
            "denied"
            if isinstance(err, PermissionError)
            else ("disappeared" if isinstance(err, FileNotFoundError) else "io")
        )
        raise IncompleteTreeError(path=path, reason=reason) from err
    return HASH_PREFIX + text_hasher.hexdigest()


def format_directory_entry(relative_posix: str, file_hash: str) -> bytes:
    """Format one directory entry framing for hashing: relative_path + NUL + hash + LF."""
    return f"{relative_posix}\0{file_hash}\n".encode()


def hash_directory(root: Path, *, cancelled: Callable[[], bool] | None = None) -> str:
    """Fingerprint an entire skill directory.

    Combines sorted relative paths with each file's own content hash, so a
    rename, an added file or an edited file all change the fingerprint.
    """
    check_cancelled(cancelled)
    hasher = hashlib.sha256()
    for relative in iter_files(root, cancelled=cancelled):
        check_cancelled(cancelled)
        posix = relative.as_posix()
        try:
            file_hash = hash_file(root / relative, cancelled=cancelled)
        except IncompleteTreeError:
            raise
        except OSError as err:
            reason = (
                "denied"
                if isinstance(err, PermissionError)
                else ("disappeared" if isinstance(err, FileNotFoundError) else "io")
            )
            raise IncompleteTreeError(path=root / relative, reason=reason) from err
        hasher.update(format_directory_entry(posix, file_hash))
    return HASH_PREFIX + hasher.hexdigest()


def hash_path(path: Path, *, cancelled: Callable[[], bool] | None = None) -> str:
    """Fingerprint a file or a directory, dispatching on the real type."""
    check_cancelled(cancelled)
    if path.is_dir():
        return hash_directory(path, cancelled=cancelled)
    return hash_file(path, cancelled=cancelled)


def _hash_file_bounded(
    path: Path, *, max_bytes: int, cancelled: Callable[[], bool] | None = None
) -> tuple[str, int]:
    """Fingerprint one file while counting and bounding the raw bytes read.

    One pass feeds both a text hash (UTF-8, CRLF normalised) and a binary hash.
    The text hash is kept only when the whole file decodes, which is exactly
    :func:`hash_file`'s choice; non-document files are never buffered in memory.
    """
    check_cancelled(cancelled)
    text_hasher = hashlib.sha256()
    binary_hasher = hashlib.sha256()
    decoder = codecs.getincrementaldecoder("utf-8")()
    text_ok = True
    pending_cr = False
    total = 0
    try:
        with path.open("rb") as handle:
            while True:
                check_cancelled(cancelled)
                chunk = handle.read(min(_CHUNK_SIZE, max_bytes - total + 1))
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise PayloadLimitExceeded(path, max_bytes, total)
                binary_hasher.update(chunk)
                if not text_ok:
                    continue
                try:
                    decoded = decoder.decode(chunk)
                except UnicodeDecodeError:
                    text_ok = False
                    continue
                if pending_cr:
                    decoded = "\r" + decoded
                    pending_cr = False
                if decoded.endswith("\r"):
                    decoded = decoded[:-1]
                    pending_cr = True
                text_hasher.update(decoded.replace("\r\n", "\n").encode("utf-8"))
            if text_ok:
                try:
                    tail = decoder.decode(b"", final=True)
                except UnicodeDecodeError:
                    text_ok = False
                else:
                    if pending_cr:
                        tail = "\r" + tail
                    text_hasher.update(tail.replace("\r\n", "\n").encode("utf-8"))
    except PayloadLimitExceeded:
        raise
    except IncompleteTreeError:
        raise
    except OSError as err:
        reason = (
            "denied"
            if isinstance(err, PermissionError)
            else ("disappeared" if isinstance(err, FileNotFoundError) else "io")
        )
        raise IncompleteTreeError(path=path, reason=reason, payload_bytes=total) from err
    hasher = text_hasher if text_ok else binary_hasher
    return HASH_PREFIX + hasher.hexdigest(), total


def hash_path_bounded(
    path: Path, *, max_bytes: int, cancelled: Callable[[], bool] | None = None
) -> tuple[str, int]:
    """Fingerprint a file or directory, refusing to read past ``max_bytes``.

    Returns ``(fingerprint, raw_payload_bytes)``. The fingerprint matches
    :func:`hash_path`; the count is the payload size, counted once per file even
    when its text hash needed a decode attempt. Support files are streamed, so a
    file that grew after a pre-flight measurement cannot be read without bound.
    """
    check_cancelled(cancelled)
    if max_bytes < 0:
        raise ValueError("max_bytes must not be negative")
    if path.is_dir():
        hasher = hashlib.sha256()
        total = 0
        for relative in iter_files(path, cancelled=cancelled):
            check_cancelled(cancelled)
            remaining = max_bytes - total
            try:
                file_hash, size = _hash_file_bounded(
                    path / relative, max_bytes=remaining, cancelled=cancelled
                )
            except PayloadLimitExceeded as err:
                raise PayloadLimitExceeded(err.path, max_bytes, total + err.total_bytes) from err
            except IncompleteTreeError as err:
                raise IncompleteTreeError(
                    err.path, err.reason, payload_bytes=total + err.payload_bytes
                ) from err
            total += size
            hasher.update(format_directory_entry(relative.as_posix(), file_hash))
        return HASH_PREFIX + hasher.hexdigest(), total
    return _hash_file_bounded(path, max_bytes=max_bytes, cancelled=cancelled)


def normalized_text(data: bytes) -> str | None:
    """Decode UTF-8 and replace CRLF with LF.

    Returns None if decoding fails. A lone CR stays unchanged, and a NUL byte
    does not by itself make a file binary.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return text.replace("\r\n", "\n")


def hash_bytes(data: bytes) -> str:
    """Fingerprint in-memory file bytes with sha256: prefix.

    Matches hash_file: decodable UTF-8 is newline-normalized as text; anything else
    is hashed as raw bytes.
    """
    norm = normalized_text(data)
    if norm is not None:
        return HASH_PREFIX + hashlib.sha256(norm.encode("utf-8")).hexdigest()
    return HASH_PREFIX + hashlib.sha256(data).hexdigest()


def hash_captured_directory(files: Sequence[tuple[str, str]]) -> str:
    """Fingerprint a captured directory from (relative_path, fingerprint) pairs.

    Pairs are sorted by relative path and hashed using relative_path + NUL +
    fingerprint + LF.
    """
    hasher = hashlib.sha256()
    for rel_path, fingerprint in sorted(files, key=lambda item: item[0]):
        hasher.update(format_directory_entry(rel_path, fingerprint))
    return HASH_PREFIX + hasher.hexdigest()
