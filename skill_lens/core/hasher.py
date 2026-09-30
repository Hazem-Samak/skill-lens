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

import hashlib
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hashlib import _Hash

HASH_PREFIX = "sha256:"
_CHUNK_SIZE = 64 * 1024
_IGNORED_DIRS = frozenset({".git"})
_IGNORED_FILES = frozenset({".DS_Store"})


def _is_ignored(relative: Path) -> bool:
    """True for paths the fingerprint must skip (VCS, macOS metadata)."""
    if any(part in _IGNORED_DIRS for part in relative.parts):
        return True
    name = relative.name
    return name in _IGNORED_FILES or name.startswith("._")


def iter_files(root: Path) -> list[Path]:
    """Return the hashable files under ``root`` in sorted, stable order.

    Only relative paths are returned, sorted as POSIX strings so the same tree
    fingerprints identically on macOS and Linux.
    """
    collected: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _IGNORED_DIRS)
        for filename in sorted(filenames):
            candidate = Path(dirpath) / filename
            relative = candidate.relative_to(root)
            if not _is_ignored(relative):
                collected.append(relative)
    collected.sort(key=lambda p: p.as_posix())
    return collected


def _update_text(hasher: _Hash, path: Path) -> None:
    """Stream ``path`` as UTF-8 text, normalising ``\\r\\n`` across chunks."""
    pending_cr = False
    with path.open("r", encoding="utf-8", newline="") as handle:
        while True:
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


def _update_binary(hasher: _Hash, path: Path) -> None:
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(_CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)


def hash_file(path: Path) -> str:
    """Fingerprint a single file, choosing text or binary handling.

    UTF-8 decodability decides: decodable files are newline-normalised as text;
    anything else is hashed as raw bytes.
    """
    text_hasher = hashlib.sha256()
    try:
        _update_text(text_hasher, path)
    except UnicodeDecodeError:
        binary_hasher = hashlib.sha256()
        _update_binary(binary_hasher, path)
        return HASH_PREFIX + binary_hasher.hexdigest()
    return HASH_PREFIX + text_hasher.hexdigest()


def hash_directory(root: Path) -> str:
    """Fingerprint an entire skill directory.

    Combines sorted relative paths with each file's own content hash, so a
    rename, an added file or an edited file all change the fingerprint.
    """
    hasher = hashlib.sha256()
    for relative in iter_files(root):
        posix = relative.as_posix()
        file_hash = hash_file(root / relative)
        hasher.update(f"{posix}\0{file_hash}\n".encode())
    return HASH_PREFIX + hasher.hexdigest()


def hash_path(path: Path) -> str:
    """Fingerprint a file or a directory, dispatching on the real type."""
    if path.is_dir():
        return hash_directory(path)
    return hash_file(path)
