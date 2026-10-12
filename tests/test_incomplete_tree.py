"""Targeted regressions and proof for Stage B (F03, F04).

Covers:
1. Incomplete directory traversal and unreadable files raise IncompleteTreeError.
2. Incomplete content never produces a complete hash or false equality.
3. Denied nested assets prevent CompareRelation.SHARED in compare.
4. Denied nested assets prevent 'no differences' in diff.
5. Incomplete capture refuses generation and preserves prior valid generation with real error.
6. Deterministic denied-file and denied-dir cases on all platforms.
7. Real POSIX permission failures where supported.
8. Distinct reasons: denied vs disappeared vs io.
9. Shared scan and doctor exit agreement on broken links, cycles, and invalid UTF-8.
"""

from __future__ import annotations

import os
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from rich.console import Console
from typer.testing import CliRunner

from skill_lens.cli import app
from skill_lens.core.compare import build_compare_report
from skill_lens.core.diff import build_diff_report
from skill_lens.core.discovery import discover
from skill_lens.core.exitcodes import ExitCode
from skill_lens.core.hasher import IncompleteTreeError, hash_path, iter_files
from skill_lens.core.snapshot import capture_session
from skill_lens.models.enums import CompareRelation
from skill_lens.render import render_compare
from skill_lens.tui.session import SessionController

runner = CliRunner()


def test_denied_nested_asset_directory_raises_incomplete_tree_error(mock_home: Path) -> None:
    """When a subfolder cannot be read, iter_files and hash_path raise IncompleteTreeError."""
    skill_dir = mock_home / ".claude" / "skills" / "deploy"
    assets_dir = skill_dir / "assets"
    assets_dir.mkdir(parents=True)
    doc_text = "---\nname: deploy\ndescription: Test skill\n---\n# Deploy\n"
    (skill_dir / "SKILL.md").write_text(doc_text)
    (assets_dir / "secret.txt").write_text("secret payload\n")

    try:
        assets_dir.chmod(0o000)
    except OSError:
        pytest.skip("Filesystem does not support permission removal")

    try:
        try:
            os.listdir(assets_dir)
            permission_worked = False
        except OSError:
            permission_worked = True

        if not permission_worked:
            pytest.skip("Running as superuser or filesystem ignores chmod 000")

        with pytest.raises(IncompleteTreeError) as exc_info:
            iter_files(skill_dir)
        assert exc_info.value.path == assets_dir
        assert exc_info.value.reason == "denied"

        with pytest.raises(IncompleteTreeError):
            hash_path(skill_dir)

        index = discover(mock_home, mock_home)
        deploy_entries = [e for e in index.entries if e.name == "deploy"]
        assert len(deploy_entries) == 1
        entry = deploy_entries[0]
        assert entry.traversal_complete is False
        assert entry.traversal_error == "denied"
        assert entry.content_hash is None
    finally:
        assets_dir.chmod(0o755)


def test_deterministic_injected_denied_directory(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deterministic simulated directory permission denial triggers IncompleteTreeError."""
    skill_dir = mock_home / ".claude" / "skills" / "deploy"
    assets_dir = skill_dir / "assets"
    assets_dir.mkdir(parents=True)
    doc_text = "---\nname: deploy\ndescription: Test skill\n---\n# Deploy\n"
    (skill_dir / "SKILL.md").write_text(doc_text)
    (assets_dir / "data.txt").write_text("asset data\n")

    orig_walk = os.walk

    def guarded_walk(top: Any, *args: Any, **kwargs: Any):
        for dirpath, dirnames, filenames in orig_walk(top, *args, **kwargs):
            if Path(dirpath) == assets_dir or "assets" in dirnames:
                onerror = kwargs.get("onerror")
                if onerror:
                    onerror(PermissionError(13, "Permission denied", str(assets_dir)))
                if "assets" in dirnames:
                    dirnames.remove("assets")
            yield dirpath, dirnames, filenames

    monkeypatch.setattr(os, "walk", guarded_walk)

    with pytest.raises(IncompleteTreeError) as exc_info:
        iter_files(skill_dir)
    assert exc_info.value.reason == "denied"

    with pytest.raises(IncompleteTreeError):
        hash_path(skill_dir)

    index = discover(mock_home, mock_home)
    entry = next(e for e in index.entries if e.name == "deploy")
    assert entry.traversal_complete is False
    assert entry.traversal_error == "denied"
    assert entry.content_hash is None


def test_denied_file_raises_incomplete_tree_error(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When a file cannot be opened, hash_path raises IncompleteTreeError(reason='denied')."""
    skill_dir = mock_home / ".claude" / "skills" / "deploy"
    assets_dir = skill_dir / "assets"
    assets_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: deploy\ndescription: Test\n---\n# Deploy\n")
    secret_file = assets_dir / "secret.txt"
    secret_file.write_text("secret payload\n")

    orig_open = Path.open

    def guarded_open(self: Path, *args: Any, **kwargs: Any):
        if self.resolve() == secret_file.resolve():
            raise PermissionError(13, "Permission denied", str(secret_file))
        return orig_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)

    files = iter_files(skill_dir)
    assert Path("assets/secret.txt") in files

    with pytest.raises(IncompleteTreeError) as exc_info:
        hash_path(skill_dir)
    assert exc_info.value.reason == "denied"
    assert exc_info.value.path == secret_file

    index = discover(mock_home, mock_home)
    entry = next(e for e in index.entries if e.name == "deploy")
    assert entry.traversal_complete is False
    assert entry.traversal_error == "denied"
    assert entry.content_hash is None

    doc_res = runner.invoke(app, ["doctor", "--sandbox", str(mock_home), "--fail-on", "error"])
    assert doc_res.exit_code == int(ExitCode.FINDINGS)
    norm = " ".join(doc_res.output.split())
    assert "refuses to" in norm and "open it" in norm
    assert "disappeared" not in norm


def test_disappeared_file_raises_incomplete_tree_error(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When a file disappears between listing and hashing, reason is 'disappeared'."""
    skill_dir = mock_home / ".claude" / "skills" / "deploy"
    assets_dir = skill_dir / "assets"
    assets_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: deploy\ndescription: Test\n---\n# Deploy\n")
    data_file = assets_dir / "data.txt"
    data_file.write_text("transient payload\n")

    orig_open = Path.open

    def disappearing_open(self: Path, *args: Any, **kwargs: Any):
        if self.resolve() == data_file.resolve():
            raise FileNotFoundError(2, "No such file or directory", str(data_file))
        return orig_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", disappearing_open)

    with pytest.raises(IncompleteTreeError) as exc_info:
        hash_path(skill_dir)
    assert exc_info.value.reason == "disappeared"
    assert exc_info.value.path == data_file

    index = discover(mock_home, mock_home)
    entry = next(e for e in index.entries if e.name == "deploy")
    assert entry.traversal_complete is False
    assert entry.traversal_error == "disappeared"

    doc_res = runner.invoke(app, ["doctor", "--sandbox", str(mock_home), "--fail-on", "error"])
    assert doc_res.exit_code == int(ExitCode.FINDINGS)
    norm = " ".join(doc_res.output.split())
    assert "disappeared" in norm and "while scanning" in norm
    assert "refuses to open it" not in norm


def test_io_error_file_raises_incomplete_tree_error(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When a file triggers generic OSError on reading, reason is 'io'."""
    skill_dir = mock_home / ".claude" / "skills" / "deploy"
    assets_dir = skill_dir / "assets"
    assets_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: deploy\ndescription: Test\n---\n# Deploy\n")
    data_file = assets_dir / "data.txt"
    data_file.write_text("corrupted payload\n")

    orig_open = Path.open

    def broken_open(self: Path, *args: Any, **kwargs: Any):
        if self.resolve() == data_file.resolve():
            raise OSError(5, "Input/output error", str(data_file))
        return orig_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", broken_open)

    with pytest.raises(IncompleteTreeError) as exc_info:
        hash_path(skill_dir)
    assert exc_info.value.reason == "io"
    assert exc_info.value.path == data_file

    index = discover(mock_home, mock_home)
    entry = next(e for e in index.entries if e.name == "deploy")
    assert entry.traversal_complete is False
    assert entry.traversal_error == "io"

    doc_res = runner.invoke(app, ["doctor", "--sandbox", str(mock_home), "--fail-on", "error"])
    assert doc_res.exit_code == int(ExitCode.FINDINGS)
    norm = " ".join(doc_res.output.lower().split())
    assert "cannot be" in norm and "read" in norm and "i/o error" in norm
    assert "refuses to open it" not in norm


def test_unreadable_nested_assets_prevents_shared_comparison(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Skills with unreadable asset folders must result in DIVERGED, never SHARED."""
    claude_dir = mock_home / ".claude" / "skills" / "deploy"
    codex_dir = mock_home / ".codex" / "skills" / "deploy"
    for d in (claude_dir, codex_dir):
        (d / "assets").mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: deploy\ndescription: Test skill\n---\n# Deploy\n")
        (d / "assets" / "data.txt").write_text("data\n")

    orig_walk = os.walk

    def guarded_walk(top: Any, *args: Any, **kwargs: Any):
        for dirpath, dirnames, filenames in orig_walk(top, *args, **kwargs):
            if "assets" in dirnames:
                onerror = kwargs.get("onerror")
                if onerror:
                    denied_path = Path(dirpath) / "assets"
                    onerror(PermissionError(13, "Permission denied", str(denied_path)))
                dirnames.remove("assets")
            yield dirpath, dirnames, filenames

    monkeypatch.setattr(os, "walk", guarded_walk)

    index = discover(mock_home, mock_home)
    report = build_compare_report("claude", "codex", mock_home, mock_home, index=index)
    deploy_entries = [e for e in report.entries if e.name == "deploy"]
    assert len(deploy_entries) == 1
    assert deploy_entries[0].relation is CompareRelation.DIVERGED

    # Truthful compare reporting for incomplete copies: explicit unreadable reason,
    # ABSENCE of false different-copies or text-diff promises.
    expected_note = "names where content is unreadable or unverifiable (denied): 'deploy'."
    assert report.notes == (expected_note,)
    assert not any("different copies" in n for n in report.notes)
    assert not any("text differences" in n for n in report.notes)

    # Actual JSON output
    rep_json = report.to_dict()
    assert rep_json["notes"] == [expected_note]
    assert not any("different copies" in n for n in rep_json["notes"])
    assert not any("text differences" in n for n in rep_json["notes"])

    # Actual human report output
    stream = StringIO()
    console = Console(file=stream, force_terminal=False, width=200)
    render_compare(report, console=console)
    rendered = stream.getvalue()
    assert expected_note in rendered
    assert "different copies" not in rendered
    assert "text differences" not in rendered


def test_unreadable_nested_assets_prevents_no_differences_in_diff(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unreadable skill copy is marked is_readable=False and content_hash=None in diff."""
    claude_dir = mock_home / ".claude" / "skills" / "deploy"
    codex_dir = mock_home / ".codex" / "skills" / "deploy"
    for d in (claude_dir, codex_dir):
        (d / "assets").mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: deploy\ndescription: Test skill\n---\n# Deploy\n")
        (d / "assets" / "data.txt").write_text("data\n")

    orig_walk = os.walk

    def guarded_walk(top: Any, *args: Any, **kwargs: Any):
        for dirpath, dirnames, filenames in orig_walk(top, *args, **kwargs):
            if "assets" in dirnames:
                onerror = kwargs.get("onerror")
                if onerror:
                    denied_path = Path(dirpath) / "assets"
                    onerror(PermissionError(13, "Permission denied", str(denied_path)))
                dirnames.remove("assets")
            yield dirpath, dirnames, filenames

    monkeypatch.setattr(os, "walk", guarded_walk)

    index = discover(mock_home, mock_home)
    report = build_diff_report("deploy", mock_home, mock_home, index=index)
    assert report.found is True
    for copy in report.copies:
        assert copy.is_readable is False
        assert copy.content_hash is None


def test_initial_capture_failure_is_retryable_user_error(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Initial capture failure produces retry status without sticky fault."""
    skill_dir = mock_home / ".claude" / "skills" / "deploy"
    assets_dir = skill_dir / "assets"
    assets_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: deploy\ndescription: Test\n---\n# Deploy\n")
    (assets_dir / "data.txt").write_text("data\n")

    orig_walk = os.walk

    def guarded_walk(top: Any, *args: Any, **kwargs: Any):
        for dirpath, dirnames, filenames in orig_walk(top, *args, **kwargs):
            if "assets" in dirnames:
                onerror = kwargs.get("onerror")
                if onerror:
                    onerror(PermissionError(13, "Permission denied", str(Path(dirpath) / "assets")))
                dirnames.remove("assets")
            yield dirpath, dirnames, filenames

    monkeypatch.setattr(os, "walk", guarded_walk)

    controller = SessionController()
    req = controller.request_refresh()
    assert req is not None
    gen, _ = req

    # Real capture fails and raises IncompleteTreeError
    with pytest.raises(IncompleteTreeError) as exc_info:
        capture_session(generation=gen, home=mock_home, cwd=mock_home)

    real_err = exc_info.value
    accepted = controller.accept_capture_error(gen, real_err)
    assert accepted is True
    assert controller.current is None
    assert controller.is_failed is False
    assert controller.status == "retry"
    assert "denied" in (controller.retry_message or "")


def test_failed_refresh_preserves_prior_generation_and_reports_real_error(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When refresh encounters IncompleteTreeError, prior generation is preserved."""
    skill_dir = mock_home / ".claude" / "skills" / "deploy"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: deploy\ndescription: Test\n---\n# Deploy\n")

    controller = SessionController()
    req = controller.request_refresh()
    assert req is not None
    gen1, _ = req

    snap1 = capture_session(generation=gen1, home=mock_home, cwd=mock_home)
    assert controller.accept_capture(snap1, gen1) is True
    assert controller.current is not None
    assert controller.current.generation == gen1
    target1 = next(e for e in snap1.index.entries if e.name == "deploy")
    assert target1.content_hash is not None

    # Now add unreadable assets
    assets = skill_dir / "assets"
    assets.mkdir()
    (assets / "file.bin").write_text("payload")

    orig_walk = os.walk

    def guarded_walk(top: Any, *args: Any, **kwargs: Any):
        for dirpath, dirnames, filenames in orig_walk(top, *args, **kwargs):
            if "assets" in dirnames:
                onerror = kwargs.get("onerror")
                if onerror:
                    onerror(PermissionError(13, "Permission denied", str(Path(dirpath) / "assets")))
                dirnames.remove("assets")
            yield dirpath, dirnames, filenames

    monkeypatch.setattr(os, "walk", guarded_walk)

    req2 = controller.request_refresh()
    assert req2 is not None
    gen2, _ = req2

    with pytest.raises(IncompleteTreeError) as exc_info:
        capture_session(generation=gen2, home=mock_home, cwd=mock_home)

    real_err = exc_info.value
    accepted = controller.accept_capture_error(gen2, real_err)
    assert accepted is True
    # Prior snapshot generation is preserved!
    assert controller.current is not None
    assert controller.current.generation == gen1
    assert controller.is_failed is False
    assert controller.status == "retry"
    assert "denied" in (controller.retry_message or "")


def test_scan_and_doctor_exit_agreement_on_shared_health_conditions(mock_home: Path) -> None:
    """scan --fail-on error and doctor --fail-on error produce identical exit results."""
    # 1. Clean state -> Exit 0
    clean_dir = mock_home / ".claude" / "skills" / "clean"
    clean_dir.mkdir(parents=True)
    clean_doc = "---\nname: clean\ndescription: Clean skill\n---\n# Clean\n"
    (clean_dir / "SKILL.md").write_text(clean_doc)

    res_scan = runner.invoke(app, ["scan", "--sandbox", str(mock_home), "--fail-on", "error"])
    res_doc = runner.invoke(app, ["doctor", "--sandbox", str(mock_home), "--fail-on", "error"])
    assert res_scan.exit_code == res_doc.exit_code == int(ExitCode.OK)

    # 2. Dangling symlink -> Exit 1
    dangling = mock_home / ".claude" / "skills" / "dangling"
    dangling.symlink_to(mock_home / "nonexistent")

    res_scan = runner.invoke(app, ["scan", "--sandbox", str(mock_home), "--fail-on", "error"])
    res_doc = runner.invoke(app, ["doctor", "--sandbox", str(mock_home), "--fail-on", "error"])
    assert res_scan.exit_code == res_doc.exit_code == int(ExitCode.FINDINGS)
    dangling.unlink()

    # 3. Shortcut cycle -> Exit 1
    cycle_a = mock_home / ".claude" / "skills" / "cycle_a"
    cycle_b = mock_home / ".claude" / "skills" / "cycle_b"
    cycle_a.symlink_to(cycle_b)
    cycle_b.symlink_to(cycle_a)

    res_scan = runner.invoke(app, ["scan", "--sandbox", str(mock_home), "--fail-on", "error"])
    res_doc = runner.invoke(app, ["doctor", "--sandbox", str(mock_home), "--fail-on", "error"])
    assert res_scan.exit_code == res_doc.exit_code == int(ExitCode.FINDINGS)
    cycle_a.unlink()
    cycle_b.unlink()

    # 4. Undecodable UTF-8 -> Exit 1, and doctor explicitly diagnoses undecodable_skill
    bad_utf8 = mock_home / ".claude" / "skills" / "bad_utf8"
    bad_utf8.mkdir(parents=True)
    (bad_utf8 / "SKILL.md").write_bytes(b"\xff\xfe\x00\x00 undecodable bytes")

    res_scan = runner.invoke(app, ["scan", "--sandbox", str(mock_home), "--fail-on", "error"])
    res_doc = runner.invoke(app, ["doctor", "--sandbox", str(mock_home), "--fail-on", "error"])
    assert res_scan.exit_code == res_doc.exit_code == int(ExitCode.FINDINGS)
    assert "invalid utf-8" in res_doc.output.lower() or "undecodable" in res_doc.output.lower()
    assert "refuses to open it" not in res_doc.output.lower()


def test_collect_preserves_cause_vocabulary_and_does_not_label_failed_text_read_binary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from skill_lens.core import diff
    from skill_lens.core.hasher import IncompleteTreeError

    test_file = tmp_path / "sample.txt"
    test_file.write_text("hello world\n", encoding="utf-8")

    # 1. Normal text collection
    collected = diff._collect(test_file)
    assert collected.is_binary is False
    assert collected.text == "hello world\n"

    # 2. Binary collection
    bin_file = tmp_path / "binary.bin"
    bin_file.write_bytes(b"\xff\xfe\x00\x00not utf8")
    collected_bin = diff._collect(bin_file)
    assert collected_bin.is_binary is True
    assert collected_bin.text is None

    # 3. Denied read must raise IncompleteTreeError(reason="denied"), not label binary
    orig_open = Path.open

    def denied_open(self: Path, *args: Any, **kwargs: Any):
        if self == test_file:
            raise PermissionError(13, "Permission denied", str(test_file))
        return orig_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied_open)
    with pytest.raises(IncompleteTreeError) as exc_info:
        diff._collect(test_file)
    assert exc_info.value.path == test_file
    assert exc_info.value.reason == "denied"

    # 4. Disappeared read during text open must raise IncompleteTreeError(reason="disappeared")
    def disappeared_open(self: Path, *args: Any, **kwargs: Any):
        if self == test_file:
            raise FileNotFoundError(2, "No such file", str(test_file))
        return orig_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", disappeared_open)
    with pytest.raises(IncompleteTreeError) as exc_info:
        diff._collect(test_file)
    assert exc_info.value.path == test_file
    assert exc_info.value.reason == "disappeared"

    # 5. Generic I/O error during text open must raise IncompleteTreeError(reason="io")
    def io_open(self: Path, *args: Any, **kwargs: Any):
        if self == test_file:
            raise OSError(5, "I/O error", str(test_file))
        return orig_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", io_open)
    with pytest.raises(IncompleteTreeError) as exc_info:
        diff._collect(test_file)
    assert exc_info.value.path == test_file
    assert exc_info.value.reason == "io"


def test_mid_run_diff_collection_failure_raises_incomplete_tree_error(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mid-run read failure during collection raises IncompleteTreeError with preserved cause."""
    from skill_lens.core import diff
    from skill_lens.core.diff import build_diff_report
    from skill_lens.core.hasher import IncompleteTreeError

    # Two copies with different SKILL.md / assets
    copy1 = mock_home / ".claude" / "skills" / "demo"
    copy1.mkdir(parents=True)
    (copy1 / "SKILL.md").write_text("---\nname: demo\ndescription: Demo 1\n---\n# A\n")
    (copy1 / "assets").mkdir()
    (copy1 / "assets" / "data.txt").write_text("data 1\n")

    copy2 = mock_home / ".agents" / "skills" / "demo"
    copy2.mkdir(parents=True)
    (copy2 / "SKILL.md").write_text("---\nname: demo\ndescription: Demo 2\n---\n# B\n")
    (copy2 / "assets").mkdir()
    target_data = copy2 / "assets" / "data.txt"
    target_data.write_text("data 2\n")

    # In mid-run collection: monkeypatch diff._collect to return None or raise for target_data
    orig_collect = diff._collect

    def failing_collect(path: Path):
        if path == target_data:
            return None
        return orig_collect(path)

    monkeypatch.setattr(diff, "_collect", failing_collect)
    with pytest.raises(IncompleteTreeError) as exc_info:
        build_diff_report("demo", mock_home, mock_home)
    assert exc_info.value.path == target_data
    assert exc_info.value.reason in ("denied", "disappeared", "io")


def test_cli_diff_mid_run_failure_exit2_and_unpolluted_json(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mid-run unreadable file produces visible plain CLI usage error exit 2, unpolluted JSON."""
    from skill_lens.core import diff

    copy1 = mock_home / ".claude" / "skills" / "demo"
    copy1.mkdir(parents=True)
    (copy1 / "SKILL.md").write_text("---\nname: demo\ndescription: Demo 1\n---\n# A\n")
    (copy1 / "assets").mkdir()
    (copy1 / "assets" / "data.txt").write_text("data 1\n")

    copy2 = mock_home / ".agents" / "skills" / "demo"
    copy2.mkdir(parents=True)
    (copy2 / "SKILL.md").write_text("---\nname: demo\ndescription: Demo 2\n---\n# B\n")
    (copy2 / "assets").mkdir()
    target_data = copy2 / "assets" / "data.txt"
    target_data.write_text("data 2\n")

    orig_collect = diff._collect

    def failing_collect(path: Path):
        if path == target_data:
            raise IncompleteTreeError(target_data, reason="denied")
        return orig_collect(path)

    monkeypatch.setattr(diff, "_collect", failing_collect)

    # 1. Plain text invocation
    res_plain = runner.invoke(app, ["diff", "demo", "--sandbox", str(mock_home)])
    assert res_plain.exit_code == int(ExitCode.USAGE)
    assert f"Error: Cannot read '{target_data}': denied" in res_plain.output

    # 2. JSON invocation
    res_json = runner.invoke(app, ["diff", "demo", "--sandbox", str(mock_home), "--json"])
    assert res_json.exit_code == int(ExitCode.USAGE)
    # Stderr has the error, stdout is not polluted by invalid JSON
    assert f"Error: Cannot read '{target_data}': denied" in res_json.output


def test_real_subprocess_diff_mid_run_collection_race(tmp_path: Path) -> None:
    """Real subprocess race at collection stage exits 2 with unpolluted JSON stdout."""
    import subprocess
    import sys

    fake_home = tmp_path / "home"
    fake_home.mkdir()

    copy1 = fake_home / ".claude" / "skills" / "demo"
    copy1.mkdir(parents=True)
    (copy1 / "SKILL.md").write_text("---\nname: demo\ndescription: Demo 1\n---\n# A\n")
    (copy1 / "assets").mkdir()
    (copy1 / "assets" / "data.txt").write_text("data 1\n")

    copy2 = fake_home / ".agents" / "skills" / "demo"
    copy2.mkdir(parents=True)
    (copy2 / "SKILL.md").write_text("---\nname: demo\ndescription: Demo 2\n---\n# B\n")
    (copy2 / "assets").mkdir()
    target_data = copy2 / "assets" / "data.txt"
    target_data.write_text("data 2\n")

    script = f"""
import sys
from skill_lens.core import diff
from skill_lens.core.hasher import IncompleteTreeError
from skill_lens.cli import app
from pathlib import Path

target = Path({repr(str(target_data))})
orig_collect = diff._collect

def race_collect(path):
    if path == target:
        raise IncompleteTreeError(target, reason="denied")
    return orig_collect(path)

diff._collect = race_collect

sys.argv = ["skill-lens", "diff", "demo", "--sandbox", {repr(str(fake_home))}, "--json"]
try:
    app()
except SystemExit as exc:
    sys.exit(exc.code)
"""
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert proc.returncode == 2
    assert proc.stdout == ""
    assert f"Error: Cannot read '{target_data}': denied" in proc.stderr


def test_why_and_diff_fixtures_preserve_accurate_parse_and_agent_resolution(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DiscoveredEntry.parse_status describes document independently of traversal.

    why attributes state to accurate agent precedence rule (ACTIVE) rather than
    falsely claiming frontmatter parser invalidity. Incomplete content is surfaced
    via report notes with empirical evidence.
    diff preserves valid document (is_valid=True) while distinctively reporting
    unreadable content (is_readable=False, cannot be read: permission denied).
    """
    from skill_lens.core.resolver import resolve_skill
    from skill_lens.models.enums import HeadlineState, ParseStatus
    from skill_lens.models.parsing import ERR_PERMISSION_DENIED

    skill_dir = mock_home / ".claude" / "skills" / "deploy"
    assets_dir = skill_dir / "assets"
    assets_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: deploy\ndescription: Valid deploy skill\n---\n# Deploy\n"
    )
    (assets_dir / "payload.bin").write_text("asset")

    orig_walk = os.walk

    def guarded_walk(top: Any, *args: Any, **kwargs: Any):
        for dirpath, dirnames, filenames in orig_walk(top, *args, **kwargs):
            if "assets" in dirnames:
                onerror = kwargs.get("onerror")
                if onerror:
                    onerror(PermissionError(13, "Permission denied", str(Path(dirpath) / "assets")))
                dirnames.remove("assets")
            yield dirpath, dirnames, filenames

    monkeypatch.setattr(os, "walk", guarded_walk)

    index = discover(mock_home, mock_home)
    entry = next(e for e in index.entries if e.name == "deploy")
    assert entry.parse_status == "valid"
    assert entry.traversal_complete is False
    assert entry.traversal_error == "denied"
    assert entry.content_hash is None

    # 1. why resolution semantics: ACTIVE, agent rule attribution, NOT invalid frontmatter
    why_rep = resolve_skill("deploy", "claude", mock_home, mock_home, index=index)
    assert why_rep.headline is HeadlineState.ACTIVE
    assert len(why_rep.candidates) == 1
    cand = why_rep.candidates[0]
    assert cand.state is HeadlineState.ACTIVE
    assert cand.rule_id == "claude_personal_beats_project"
    assert cand.installation.parse_status is ParseStatus.VALID
    assert cand.installation.content_hash is None
    # Note surfaces incomplete content separately with empirical cause
    assert any("incomplete (denied)" in note for note in why_rep.notes)

    # 2. diff: document validity and content readability remain distinct
    diff_rep = build_diff_report("deploy", mock_home, mock_home, index=index)
    assert len(diff_rep.copies) == 1
    copy = diff_rep.copies[0]
    assert copy.parse_status == "valid"
    assert copy.is_valid is True
    assert copy.is_readable is False
    assert copy.content_hash is None
    assert copy.error == ERR_PERMISSION_DENIED


def test_shared_canonical_symlink_farm_incomplete_merge_and_consumers(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Shared-canonical symlink-farm: incomplete traversal prevents SHARED in compare.

    Merge invariant: incomplete => content_hash is None even if one input has hash.
    Actual consumers with merged index:
    - compare canonical SHARED branch refuses SHARED (returns DIVERGED)
    - diff cannot certify equality (is_readable=False)
    """
    from skill_lens.core.discovery import DiscoveredEntry, _merge_entries
    from skill_lens.core.parser import canonicalize, parse_skill
    from skill_lens.models.enums import CompareRelation

    shared_dir = mock_home / ".shared" / "skills" / "deploy"
    assets_dir = shared_dir / "assets"
    assets_dir.mkdir(parents=True)
    (shared_dir / "SKILL.md").write_text(
        "---\nname: deploy\ndescription: Shared deploy skill\n---\n# Deploy\n"
    )
    (assets_dir / "asset.txt").write_text("data")

    claude_dir = mock_home / ".claude" / "skills" / "deploy"
    claude_dir.parent.mkdir(parents=True, exist_ok=True)
    claude_dir.symlink_to(shared_dir)

    codex_dir = mock_home / ".codex" / "skills" / "deploy"
    codex_dir.parent.mkdir(parents=True, exist_ok=True)
    codex_dir.symlink_to(shared_dir)

    orig_walk = os.walk

    def guarded_walk(top: Any, *args: Any, **kwargs: Any):
        for dirpath, dirnames, filenames in orig_walk(top, *args, **kwargs):
            if "assets" in dirnames:
                onerror = kwargs.get("onerror")
                if onerror:
                    onerror(PermissionError(13, "Permission denied", str(Path(dirpath) / "assets")))
                dirnames.remove("assets")
            yield dirpath, dirnames, filenames

    monkeypatch.setattr(os, "walk", guarded_walk)

    # Invariant test on _merge_entries directly: incomplete side clears content_hash
    e_complete = DiscoveredEntry(
        entrypoint_path=str(claude_dir),
        name="deploy",
        is_file=False,
        is_symlink=True,
        canonical=canonicalize(claude_dir),
        parse=parse_skill(claude_dir),
        content_hash="abc123verifiedhash",
        traversal_complete=True,
        traversal_error=None,
    )
    e_incomplete = DiscoveredEntry(
        entrypoint_path=str(codex_dir),
        name="deploy",
        is_file=False,
        is_symlink=True,
        canonical=canonicalize(codex_dir),
        parse=parse_skill(codex_dir),
        content_hash=None,
        traversal_complete=False,
        traversal_error="denied",
    )
    merged = _merge_entries([e_complete, e_incomplete])
    assert len(merged) == 1
    assert merged[0].traversal_complete is False
    assert merged[0].content_hash is None
    assert merged[0].traversal_error == "denied"

    # End-to-end consumers with merged index
    index = discover(mock_home, mock_home)
    deploy_entries = [e for e in index.entries if e.name == "deploy"]
    assert len(deploy_entries) == 1
    shared_entry = deploy_entries[0]
    assert shared_entry.canonical_path == str(shared_dir.resolve())
    assert shared_entry.traversal_complete is False
    assert shared_entry.content_hash is None

    # compare consumer: both agents reach the same canonical path, but incomplete => DIVERGED
    comp_rep = build_compare_report("claude", "codex", mock_home, mock_home, index=index)
    c_entry = next(e for e in comp_rep.entries if e.name == "deploy")
    assert c_entry.relation is CompareRelation.DIVERGED

    # Shared canonical copy: explicit unreadable note, ABSENCE of false different-copies promise
    expected_shared_note = (
        "names where claude and codex share a canonical copy "
        "but content is unreadable or unverifiable (denied): 'deploy'."
    )
    assert comp_rep.notes == (expected_shared_note,)
    assert not any("different copies" in n for n in comp_rep.notes)
    assert not any("text differences" in n for n in comp_rep.notes)

    # Actual JSON output
    comp_json = comp_rep.to_dict()
    assert comp_json["notes"] == [expected_shared_note]
    assert not any("different copies" in n for n in comp_json["notes"])
    assert not any("text differences" in n for n in comp_json["notes"])

    # Actual human report output
    stream = StringIO()
    console = Console(file=stream, force_terminal=False, width=200)
    render_compare(comp_rep, console=console)
    rendered = stream.getvalue()
    assert expected_shared_note in rendered
    assert "different copies" not in rendered
    assert "text differences" not in rendered

    # diff consumer: cannot certify equality, is_readable is False
    diff_rep = build_diff_report("deploy", mock_home, mock_home, index=index)
    for copy in diff_rep.copies:
        assert copy.is_readable is False
        assert copy.content_hash is None


def test_truthful_early_capture_refusal_vs_snapshot_changed(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deterministic discovery hash reports denial, later capture walk/read succeeds.

    Asserts exact early IncompleteTreeError(reason='denied') at entry root rather
    than downstream misleading SnapshotChanged. Controller accepts error and
    retains prior generation.
    """
    from skill_lens.core import discovery as discovery_mod

    skill_dir = mock_home / ".claude" / "skills" / "deploy"
    assets_dir = skill_dir / "assets"
    assets_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: deploy\ndescription: Test\n---\n# Deploy\n")
    (assets_dir / "data.txt").write_text("data payload\n")

    controller = SessionController()
    req1 = controller.request_refresh()
    assert req1 is not None
    gen1, _ = req1
    snap1 = capture_session(generation=gen1, home=mock_home, cwd=mock_home)
    assert controller.accept_capture(snap1, gen1) is True
    assert controller.current is not None
    assert controller.current.generation == gen1

    # Simulate: discovery hash reports denial (e.g. transient PermissionError during discovery),
    # but subsequent capture iter_files/file reading on disk succeeds!
    orig_hash_path = discovery_mod.hash_path

    def discovery_denied_hash_path(path: Path, *args: Any, **kwargs: Any):
        if path.resolve() == skill_dir.resolve():
            raise IncompleteTreeError(path=skill_dir, reason="denied")
        return orig_hash_path(path, *args, **kwargs)

    monkeypatch.setattr(discovery_mod, "hash_path", discovery_denied_hash_path)

    req2 = controller.request_refresh()
    assert req2 is not None
    gen2, _ = req2

    # Capture must refuse EARLY with IncompleteTreeError, NOT SnapshotChanged
    with pytest.raises(IncompleteTreeError) as exc_info:
        capture_session(generation=gen2, home=mock_home, cwd=mock_home)

    err = exc_info.value
    assert err.reason == "denied"
    assert err.path == skill_dir.resolve() or err.path == skill_dir

    # Controller acceptance: retains prior valid generation
    accepted = controller.accept_capture_error(gen2, err)
    assert accepted is True
    assert controller.current is not None
    assert controller.current.generation == gen1
    assert controller.is_failed is False
    assert controller.status == "retry"
    assert "denied" in (controller.retry_message or "")


def test_compare_conditional_notes_incomplete_and_verified_trees(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise all conditional compare notes in one report:
    1. Shared canonical with unreadable content -> unverifiable shared note.
    2. Different canonicals with unreadable content -> unverifiable diff note.
    3. Different canonicals with verified differing hashes -> verified diverged note.
    Asserts exact notes, JSON output, human rendering, and ABSENCE of false promises.
    """
    from io import StringIO

    from rich.console import Console

    from skill_lens.render import render_compare

    # 1. shared_inc: shared canonical target with denied nested assets
    shared_dir = mock_home / ".shared" / "skills" / "shared_inc"
    (shared_dir / "assets").mkdir(parents=True)
    (shared_dir / "SKILL.md").write_text("---\nname: shared_inc\ndescription: Shared\n---\n")
    (shared_dir / "assets" / "data.txt").write_text("secret\n")

    claude_shared = mock_home / ".claude" / "skills" / "shared_inc"
    claude_shared.parent.mkdir(parents=True, exist_ok=True)
    claude_shared.symlink_to(shared_dir)

    codex_shared = mock_home / ".codex" / "skills" / "shared_inc"
    codex_shared.parent.mkdir(parents=True, exist_ok=True)
    codex_shared.symlink_to(shared_dir)

    # 2. diff_inc: separate physical folders with denied assets
    claude_inc = mock_home / ".claude" / "skills" / "diff_inc"
    codex_inc = mock_home / ".codex" / "skills" / "diff_inc"
    for d in (claude_inc, codex_inc):
        (d / "assets").mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: diff_inc\ndescription: Inc\n---\n")
        (d / "assets" / "data.txt").write_text("secret\n")

    # 3. diff_ver: separate physical folders, complete traversal, differing content
    claude_ver = mock_home / ".claude" / "skills" / "diff_ver"
    codex_ver = mock_home / ".codex" / "skills" / "diff_ver"
    claude_ver.mkdir(parents=True)
    codex_ver.mkdir(parents=True)
    (claude_ver / "SKILL.md").write_text("---\nname: diff_ver\ndescription: Claude version\n---\n")
    (codex_ver / "SKILL.md").write_text("---\nname: diff_ver\ndescription: Codex version\n---\n")

    orig_walk = os.walk

    def guarded_walk(top: Any, *args: Any, **kwargs: Any):
        for dirpath, dirnames, filenames in orig_walk(top, *args, **kwargs):
            if "assets" in dirnames:
                onerror = kwargs.get("onerror")
                if onerror:
                    onerror(PermissionError(13, "Permission denied", str(Path(dirpath) / "assets")))
                dirnames.remove("assets")
            yield dirpath, dirnames, filenames

    monkeypatch.setattr(os, "walk", guarded_walk)

    index = discover(mock_home, mock_home)
    report = build_compare_report("claude", "codex", mock_home, mock_home, index=index)

    # Verify relations
    by_name = {e.name: e for e in report.entries}
    assert by_name["shared_inc"].relation is CompareRelation.DIVERGED
    assert by_name["diff_inc"].relation is CompareRelation.DIVERGED
    assert by_name["diff_ver"].relation is CompareRelation.DIVERGED

    # Exactly three notes in sorted category order
    expected_notes = [
        "names where claude and codex read different copies: 'diff_ver'. "
        "Run 'skill-lens diff <name>' to see the text differences.",
        "names where claude and codex share a canonical copy "
        "but content is unreadable or unverifiable (denied): 'shared_inc'.",
        "names where content is unreadable or unverifiable (denied): 'diff_inc'.",
    ]
    assert list(report.notes) == expected_notes

    # JSON representation matches exactly
    rep_json = report.to_dict()
    assert rep_json["notes"] == expected_notes

    # Rendered human report includes all notes, diff suggestion ONLY for verified
    console = Console(file=StringIO(), force_terminal=False, width=200)
    render_compare(report, console=console)
    rendered = console.file.getvalue()
    for note in expected_notes:
        assert note in rendered

    # No false text difference promise for unreadable entries
    assert "Run 'skill-lens diff shared_inc'" not in rendered
    assert "Run 'skill-lens diff diff_inc'" not in rendered
