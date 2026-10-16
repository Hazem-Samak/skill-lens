"""Capture budget refusal tests (R01).

Specification reference: FULL_SCREEN_TUI.md §9.1 and the frozen plan
``docs/plans/2026-10-16-snapshot-capture-budget.md``.

Stage H recorded R01: snapshot capture had no byte bound, so a byte-heavy home
could pull an unbounded amount of file content into memory. The fix is an
explicit refusal budget. The total skill payload is measured *before* any payload
byte is read, and an oversized home is refused rather than read.

These tests pin four things the reviewers required:

* the boundary is exact — at the limit is admitted, one byte over is refused;
* the refusal is raised before any payload byte is read;
* only skill payload counts, so captured configuration bytes do not tip it over;
* an unreadable tree still raises ``IncompleteTreeError``, never a budget refusal,
  so pre-existing behaviour is preserved.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import skill_lens.core.snapshot as snapshot_module
from skill_lens.core.discovery import (
    CanonicalResult,
    CanonicalStatus,
    DiscoveredEntry,
    DiscoveryIndex,
)
from skill_lens.core.hasher import IncompleteTreeError
from skill_lens.core.snapshot import (
    DEFAULT_MAX_SNAPSHOT_BYTES,
    SnapshotTooLarge,
    _measure_capture_payload,
    capture_session,
    format_bytes,
)
from tests.fixtures.builders import make_skill

ASSET_BYTES = 4096
SKILL_DIR_NAME = "big-skill"


def _home_with_one_skill(home: Path) -> Path:
    """Create one discoverable skill directory carrying a known-size asset."""
    skill_dir = home / ".claude" / "skills" / SKILL_DIR_NAME
    make_skill(skill_dir, SKILL_DIR_NAME, "A skill with a binary asset.")
    (skill_dir / "asset.bin").write_bytes(b"a" * ASSET_BYTES)
    return skill_dir


def _payload_bytes(skill_dir: Path) -> int:
    """Exact payload the capture loop would read for this one skill."""
    return sum(entry.stat().st_size for entry in skill_dir.iterdir() if entry.is_file())


def _entry(
    *,
    name: str,
    root: Path,
    traversal_complete: bool,
    content_hash: str | None,
    is_file: bool = False,
) -> DiscoveredEntry:
    """A minimal discoverable entry for direct sizing tests."""
    return DiscoveredEntry(
        entrypoint_path=str(root),
        name=name,
        is_file=is_file,
        is_symlink=False,
        canonical=CanonicalResult(
            status=CanonicalStatus.OK,
            entrypoint_path=str(root),
            resolved_path=str(root),
            is_symlink=False,
        ),
        parse=None,
        content_hash=content_hash,
        traversal_complete=traversal_complete,
    )


# --- Boundary behaviour ----------------------------------------------------


def test_payload_over_the_limit_is_refused(mock_home: Path) -> None:
    """One byte over the limit refuses, and the error reports both figures."""
    skill_dir = _home_with_one_skill(mock_home)
    payload = _payload_bytes(skill_dir)
    limit = payload - 1

    with pytest.raises(SnapshotTooLarge) as exc_info:
        capture_session(
            generation=1,
            home=mock_home,
            cwd=mock_home,
            max_snapshot_bytes=limit,
        )

    error = exc_info.value
    assert error.total_bytes == payload
    assert error.limit_bytes == limit


def test_payload_exactly_at_the_limit_is_admitted(mock_home: Path) -> None:
    """The boundary is inclusive: equal to the limit still captures."""
    skill_dir = _home_with_one_skill(mock_home)
    payload = _payload_bytes(skill_dir)

    snapshot = capture_session(
        generation=1,
        home=mock_home,
        cwd=mock_home,
        max_snapshot_bytes=payload,
    )

    assert snapshot.generation == 1
    assert payload > 0


@pytest.mark.parametrize("budget", [None, 0])
def test_no_limit_means_unbounded(mock_home: Path, budget: int | None) -> None:
    """``None`` and ``0`` both disable the budget entirely."""
    _home_with_one_skill(mock_home)

    snapshot = capture_session(
        generation=1,
        home=mock_home,
        cwd=mock_home,
        max_snapshot_bytes=budget,
    )

    assert snapshot.generation == 1
    # A limit of 1 byte would have refused this home, so the budget is what
    # changed the outcome rather than the payload being trivially small.
    with pytest.raises(SnapshotTooLarge):
        capture_session(generation=2, home=mock_home, cwd=mock_home, max_snapshot_bytes=1)


# --- Ordering: the refusal must precede the read ---------------------------


def test_refusal_precedes_the_capture_phase_read(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pre-flight sizing walk runs, and the capture-phase read never happens.

    ``hash_bytes`` is reached only after the capture loop has read a whole file
    into memory, so making it raise proves the refusal came first. Discovery runs
    earlier and does parse each skill source document; that read is a recorded
    residual and is deliberately not what this test claims to cover.
    """
    skill_dir = _home_with_one_skill(mock_home)
    payload = _payload_bytes(skill_dir)

    sized: list[Path] = []
    real_stat_size = snapshot_module._stat_size

    def recording_stat_size(path: Path) -> int:
        sized.append(path)
        return real_stat_size(path)

    def forbid_hash(data: bytes) -> str:
        raise AssertionError("payload bytes were read before the refusal")

    monkeypatch.setattr(snapshot_module, "_stat_size", recording_stat_size)
    monkeypatch.setattr(snapshot_module, "hash_bytes", forbid_hash)

    with pytest.raises(SnapshotTooLarge):
        capture_session(
            generation=1,
            home=mock_home,
            cwd=mock_home,
            max_snapshot_bytes=payload - 1,
        )

    assert sized, "the pre-flight sizing walk must have run before refusing"


def test_budget_is_enforced_against_the_bytes_actually_read(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file that grows after measuring still cannot carry the capture over.

    The pre-flight figure is forced low here, standing in for a file that grew
    between the measurement and the read — including the case a normalised
    fingerprint cannot see, where LF becomes CRLF and the raw bytes double while
    the hash is unchanged.
    """
    skill_dir = _home_with_one_skill(mock_home)
    payload = _payload_bytes(skill_dir)

    monkeypatch.setattr(
        snapshot_module, "_measure_capture_payload", lambda index, **kwargs: (1, True)
    )

    with pytest.raises(SnapshotTooLarge) as exc_info:
        capture_session(
            generation=1,
            home=mock_home,
            cwd=mock_home,
            max_snapshot_bytes=payload - 1,
        )

    assert exc_info.value.total_bytes >= payload
    assert exc_info.value.limit_bytes == payload - 1


# --- Accounting: payload only ---------------------------------------------


def test_configuration_bytes_do_not_count_toward_the_budget(mock_home: Path) -> None:
    """A settings file larger than the whole payload must not tip the budget."""
    skill_dir = _home_with_one_skill(mock_home)
    payload = _payload_bytes(skill_dir)

    settings = mock_home / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps({"pad": "x" * (payload * 4)}), encoding="utf-8")
    assert settings.stat().st_size > payload

    snapshot = capture_session(
        generation=1,
        home=mock_home,
        cwd=mock_home,
        max_snapshot_bytes=payload,
    )

    assert snapshot.generation == 1


def test_standalone_file_entry_is_sized_as_one_file(tmp_path: Path) -> None:
    """A standalone skill document is sized as a single file, not walked as a directory."""
    document = tmp_path / "solo.md"
    document.write_text("x" * 64, encoding="utf-8")
    index = DiscoveryIndex(
        home=str(tmp_path),
        cwd=str(tmp_path),
        entries=[
            _entry(
                name="solo",
                root=document,
                traversal_complete=True,
                content_hash="sha256:" + "0" * 64,
                is_file=True,
            ),
        ],
    )

    total, sized_all = _measure_capture_payload(index)

    assert sized_all is True
    assert total == 64


# --- Preserved behaviour: incomplete trees --------------------------------


def test_unmeasurable_entry_suppresses_the_refusal(tmp_path: Path) -> None:
    """An entry the capture loop cannot size reports ``sized_all=False``."""
    root = tmp_path / "incomplete"
    root.mkdir()
    (root / "SKILL.md").write_text("body", encoding="utf-8")
    index = DiscoveryIndex(
        home=str(tmp_path),
        cwd=str(tmp_path),
        entries=[
            _entry(name="incomplete", root=root, traversal_complete=False, content_hash=None),
        ],
    )

    total, sized_all = _measure_capture_payload(index)

    assert sized_all is False
    assert total == 0


def test_incomplete_tree_still_raises_incomplete_tree_error(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tree that cannot be read keeps its own error, even under a tiny budget."""
    skill_dir = _home_with_one_skill(mock_home)
    index = DiscoveryIndex(
        home=str(mock_home),
        cwd=str(mock_home),
        entries=[
            _entry(
                name=SKILL_DIR_NAME,
                root=skill_dir,
                traversal_complete=False,
                content_hash=None,
            ),
        ],
    )
    monkeypatch.setattr(snapshot_module, "live_discovery", lambda **kwargs: index)

    with pytest.raises(IncompleteTreeError):
        capture_session(generation=1, home=mock_home, cwd=mock_home, max_snapshot_bytes=1)


# --- The refusal message ---------------------------------------------------


def test_refusal_message_never_suggests_a_retry() -> None:
    """Retrying an unchanged oversized home cannot help, so the text must not say so."""
    error = SnapshotTooLarge(total_bytes=300 * 1024 * 1024, limit_bytes=256 * 1024 * 1024)
    message = str(error)

    assert "retry" not in message.lower()
    assert "300.0 MiB" in message
    assert "256.0 MiB" in message
    assert "--max-snapshot-bytes" in message


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (0, "0 B"),
        (512, "512 B"),
        (2048, "2.0 KiB"),
        (256 * 1024 * 1024, "256.0 MiB"),
    ],
)
def test_format_bytes(count: int, expected: str) -> None:
    assert format_bytes(count) == expected


def test_default_budget_is_256_mib() -> None:
    """The documented default is a stable, reviewable number."""
    assert DEFAULT_MAX_SNAPSHOT_BYTES == 256 * 1024 * 1024


def test_snapshot_module_exports_the_budget_api() -> None:
    """The public surface the CLI and TUI rely on stays exported."""
    exported: Any = snapshot_module.__all__
    for name in ("DEFAULT_MAX_SNAPSHOT_BYTES", "SnapshotTooLarge", "format_bytes"):
        assert name in exported
