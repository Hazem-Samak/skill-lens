#!/usr/bin/env python3
"""Drive the installed 0.2.0 candidate's terminal interface through a PTY (U9).

This is automated technical smoke evidence, **not** human visual approval. It
runs the binary from a fresh installation lane (never an editable checkout), with
an explicit ``--sandbox`` and ``--cwd`` inside a synthetic fixture, so no real
skill directory is read.

Per scenario it drives real key presses at a fixed terminal size and asserts on
literal on-screen text captured from the pseudo-terminal:

    Home -> Help -> Why -> Diff -> Agents -> Compare -> Doctor
         -> raw JSON -> filter -> agent filter -> refresh -> quit

It also records the restore sequences emitted on exit (alternate screen off,
cursor shown) and checks the base/missing-extra and ``--plain`` fallbacks.

Usage:
    python terminal_check.py --binary <lane>/bin/skill-lens \
        --base-binary <base-lane>/bin/skill-lens \
        --lane-python <lane>/venv/bin/python \
        --fixture-root /tmp/u9-terminal --out receipt.json
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import pty
import re
import select
import shutil
import struct
import subprocess
import sys
import termios
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ANSI_CSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
ANSI_OSC = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
ANSI_OTHER = re.compile(r"\x1b[@-Z\\-_]")

KEYS = {
    "enter": b"\r",
    "escape": b"\x1b",
    "down": b"\x1b[B",
    "up": b"\x1b[A",
    "space": b" ",
    "backspace": b"\x7f",
    "help": b"?",
    "json": b"J",
    "filter": b"/",
    "agent_filter": b"a",
    "refresh": b"r",
    "quit": b"q",
    "agents": b"g",
    "compare": b"c",
    "doctor": b"h",
    "diff": b"d",
}


def strip_ansi(data: str) -> str:
    data = ANSI_OSC.sub("", data)
    data = ANSI_CSI.sub("", data)
    data = ANSI_OTHER.sub("", data)
    return data.replace("\r\n", "\n").replace("\r", "")


def write_skill(path: Path, name: str, description: str, body: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n{body}\n",
        encoding="utf-8",
    )


def build_nonempty_fixture(root: Path) -> Path:
    """Two agents, three variants of one skill, and one dangling symlink."""
    home = root / "home"
    if home.exists():
        shutil.rmtree(home)
    write_skill(
        home / ".claude" / "skills" / "alpha",
        "alpha",
        "Alpha skill from Claude personal.",
        "Alpha body line one.",
    )
    write_skill(
        home / ".claude" / "skills" / "beta",
        "beta",
        "Beta skill only in Claude personal.",
        "Beta body.",
    )
    write_skill(
        home / ".agents" / "skills" / "alpha",
        "alpha",
        "Alpha skill from the shared agents library.",
        "Alpha body line one, edited in the shared copy.",
    )
    write_skill(
        home / ".codex" / "skills" / "alpha",
        "alpha",
        "Alpha skill from Codex global.",
        "Alpha body line one, edited in the codex copy.",
    )
    (home / ".claude" / "skills").mkdir(parents=True, exist_ok=True)
    (home / ".claude" / "skills" / "broken").symlink_to("../missing-target")
    (home / "project").mkdir(parents=True, exist_ok=True)
    return home


def build_empty_fixture(root: Path) -> Path:
    home = root / "empty-home"
    if home.exists():
        shutil.rmtree(home)
    (home / "project").mkdir(parents=True, exist_ok=True)
    return home


@dataclass
class StepResult:
    id: str
    description: str
    keys: list[str]
    expected: list[str]
    ok: bool
    missing: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    screen_excerpt: str = ""


class PtySession:
    """One installed binary running in a pseudo-terminal of a fixed size."""

    def __init__(
        self,
        argv: list[str],
        env: dict[str, str],
        size: tuple[int, int],
        cwd: Path | None = None,
    ) -> None:
        self.argv = argv
        self.env = env
        self.size = size
        self.cwd = cwd
        self.master = -1
        self.proc: subprocess.Popen[bytes] | None = None
        self.raw = b""

    def __enter__(self) -> PtySession:
        rows, cols = self.size[1], self.size[0]
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        self.proc = subprocess.Popen(
            self.argv,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            env=self.env,
            cwd=str(self.cwd) if self.cwd is not None else None,
            close_fds=True,
            start_new_session=True,
        )
        os.close(slave)
        os.set_blocking(master, False)
        self.master = master
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=10)
        if self.master >= 0:
            with contextlib.suppress(OSError):
                os.close(self.master)
            self.master = -1

    def read_available(self, budget: float) -> str:
        chunks: list[bytes] = []
        end = time.monotonic() + budget
        while time.monotonic() < end:
            ready, _, _ = select.select([self.master], [], [], 0.05)
            if not ready:
                if self.proc is not None and self.proc.poll() is not None:
                    break
                continue
            try:
                data = os.read(self.master, 65536)
            except (BlockingIOError, InterruptedError):
                continue
            except OSError:
                break
            if not data:
                break
            self.raw += data
            chunks.append(data)
        return b"".join(chunks).decode("utf-8", "replace")

    def send(self, payload: bytes) -> None:
        os.write(self.master, payload)

    def expect(self, markers: list[str], timeout: float) -> tuple[bool, list[str], str]:
        """Read until every marker has appeared (or the timeout expires)."""
        seen = ""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            seen += strip_ansi(self.read_available(0.15))
            missing = [marker for marker in markers if marker not in seen]
            if not missing:
                return True, [], seen[-1200:]
        return False, [marker for marker in markers if marker not in seen], seen[-1200:]

    def wait_exit(self, timeout: float) -> int | None:
        if self.proc is None:
            return None
        try:
            return self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return None


@dataclass
class PlanStep:
    id: str
    description: str
    keys: list[str]
    expected: list[str]
    timeout: float = 20.0


def drive(
    binary: Path,
    home: Path,
    size: tuple[int, int],
    plan: list[PlanStep],
    base_env: dict[str, str],
) -> dict[str, Any]:
    argv = [
        str(binary),
        "tui",
        "--sandbox",
        str(home),
        "--cwd",
        str(home / "project"),
    ]
    env = dict(base_env)
    results: list[StepResult] = []
    restore: dict[str, Any] = {}
    with PtySession(argv, env, size, cwd=home.parent) as session:
        for step in plan:
            started = time.monotonic()
            for key in step.keys:
                if key.startswith("type:"):
                    session.send(key[len("type:") :].encode("utf-8"))
                else:
                    session.send(KEYS[key])
                time.sleep(0.25)
            ok, missing, excerpt = session.expect(step.expected, step.timeout)
            results.append(
                StepResult(
                    id=step.id,
                    description=step.description,
                    keys=step.keys,
                    expected=step.expected,
                    ok=ok,
                    missing=missing,
                    elapsed_seconds=round(time.monotonic() - started, 2),
                    screen_excerpt=excerpt,
                )
            )
            if not ok:
                break
        before_quit = len(session.raw)
        session.send(KEYS["quit"])
        # Drain while the process is still alive: macOS returns EIO once the
        # slave side closes, which would discard the restore sequences.
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline and session.proc.poll() is None:
            session.read_available(0.1)
        returncode = session.wait_exit(10)
        session.read_available(0.5)
        tail = session.raw[before_quit:].decode("utf-8", "replace")
        restore = {
            "returncode": returncode,
            "alternate_screen_left": "\x1b[?1049l" in tail,
            "cursor_shown": "\x1b[?25h" in tail,
            "tail_escapes": sorted({escape for escape in re.findall(r"\x1b\[\?[0-9;]+[hl]", tail)}),
            "tail_excerpt": strip_ansi(tail)[-600:],
        }
    return {
        "binary": str(binary),
        "home": str(home),
        "terminal_size": {"columns": size[0], "rows": size[1]},
        "command": argv,
        "steps": [step.__dict__ for step in results],
        "steps_passed": all(step.ok for step in results),
        "restore": restore,
        "all_passed": all(step.ok for step in results)
        and restore["returncode"] == 0
        and restore["alternate_screen_left"]
        and restore["cursor_shown"],
    }


def full_plan() -> list[PlanStep]:
    return [
        PlanStep(
            "home",
            "Home lists the captured catalogue and shows the installed version",
            [],
            ["Skill Lens — 0.2.0", "Skill Lens Home", "alpha", "Ready:"],
            timeout=40.0,
        ),
        PlanStep(
            "help-open",
            "Help overlay opens and names its close control",
            ["help"],
            ["Help", "Close"],
        ),
        PlanStep(
            "help-dismiss",
            "Esc returns to the Home screen",
            ["escape"],
            ["Skill Lens Home"],
        ),
        PlanStep(
            "why",
            "Enter opens the Why resolution screen for the focused skill",
            ["enter"],
            ["Installation:", "Name: alpha", "Claude Code"],
        ),
        PlanStep(
            "diff",
            "d opens the Diff screen with all captured copies",
            ["diff"],
            ["Diff: 'alpha'", "Baseline"],
        ),
        PlanStep(
            "back-home-1",
            "Esc from Diff returns to Why, Esc again returns Home",
            ["escape", "escape"],
            ["Skill Lens Home"],
        ),
        PlanStep(
            "agents",
            "g opens the Agents screen with the captured registry detail",
            ["agents"],
            # The 60x24 layout clips the lower part of the detail pane, so the
            # markers are the ones visible at both tested sizes.
            ["Agents", "Collision policy:", "Policy evidence:"],
        ),
        PlanStep(
            "back-home-2",
            "Esc returns to Home",
            ["escape"],
            ["Skill Lens Home"],
        ),
        PlanStep(
            "compare-picker",
            "c opens the Compare picker",
            ["compare"],
            ["Compare agents"],
        ),
        PlanStep(
            "compare-result",
            "Choosing two agents renders the comparison summary",
            ["enter", "down", "enter"],
            ["Shared:", "Relation:"],
            timeout=40.0,
        ),
        PlanStep(
            "back-home-3",
            "Esc leaves the comparison and the picker",
            ["escape", "escape"],
            ["Skill Lens Home"],
        ),
        PlanStep(
            "doctor",
            "h opens the Doctor screen showing the dangling-symlink finding",
            ["doctor"],
            ["Doctor", "dangling_symlink"],
        ),
        PlanStep(
            "back-home-4",
            "Esc returns to Home",
            ["escape"],
            ["Skill Lens Home"],
        ),
        PlanStep(
            "raw-json",
            "J on Home shows the canonical JSON document",
            ["json"],
            ['"cwd":'],
        ),
        PlanStep(
            "raw-json-off",
            "J toggles back to the ordinary table",
            ["json"],
            ["Skill Lens Home", "alpha"],
        ),
        PlanStep(
            "filter",
            "/ focuses the filter input",
            ["filter"],
            ["Filter by name or description"],
        ),
        PlanStep(
            "filter-no-match",
            "A no-match filter explains how to clear it",
            ["type:nosuchskill"],
            ["No skills match the current filter"],
        ),
        PlanStep(
            "filter-clear",
            "Esc clears the filter and restores the captured rows",
            ["escape"],
            ["alpha"],
        ),
        PlanStep(
            "agent-filter",
            "a cycles the agent filter and labels the active agent",
            ["agent_filter"],
            ["Agent: ", "(claude)"],
        ),
        PlanStep(
            "refresh",
            "r refreshes and the session reports ready again",
            ["refresh"],
            ["Ready:"],
            timeout=40.0,
        ),
    ]


def empty_plan() -> list[PlanStep]:
    return [
        PlanStep(
            "empty-home",
            "An empty synthetic home reports no discovered skills",
            [],
            ["Skill Lens — 0.2.0", "Skill Lens Home", "No skills discovered in this session"],
            timeout=40.0,
        ),
        PlanStep(
            "help-open",
            "Help is available with no captured skills",
            ["help"],
            ["Help", "Close"],
        ),
        PlanStep(
            "help-dismiss",
            "Esc returns to the empty Home screen",
            ["escape"],
            ["Skill Lens Home"],
        ),
        PlanStep(
            "raw-json",
            "Raw JSON works for an empty session",
            ["json"],
            ['"cwd":'],
        ),
        PlanStep(
            "raw-json-off",
            "J toggles back to the empty table",
            ["json"],
            ["No skills discovered in this session"],
        ),
    ]


def probe(argv: list[str], env: dict[str, str], cwd: Path, timeout: float = 60.0) -> dict[str, Any]:
    completed = subprocess.run(
        argv,
        env=env,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
    )
    return {
        "command": argv,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def pty_probe(
    argv: list[str], env: dict[str, str], size: tuple[int, int], cwd: Path
) -> dict[str, Any]:
    """Run a non-TUI command in a PTY so both streams look interactive."""
    with PtySession(argv, env, size, cwd=cwd) as session:
        output = session.read_available(0.2)
        deadline = time.monotonic() + 30
        while session.proc is not None and session.proc.poll() is None:
            if time.monotonic() > deadline:
                break
            output += session.read_available(0.1)
        returncode = session.wait_exit(10)
        output += session.read_available(0.3)
    return {"command": argv, "exit_code": returncode, "output": strip_ansi(output)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True, help="Installed skill-lens.")
    parser.add_argument("--base-binary", type=Path, required=True, help="Base-lane skill-lens.")
    parser.add_argument("--lane-python", type=Path, required=True, help="Lane Python.")
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--artifact-sha256", type=str, default="")
    args = parser.parse_args(argv)

    root = args.fixture_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    nonempty_home = build_nonempty_fixture(root)
    empty_home = build_empty_fixture(root)

    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(root / "operator-home"),
        "XDG_CONFIG_HOME": str(root / "operator-home" / ".config"),
        "TERM": "xterm-256color",
        "COLORTERM": "truecolor",
        "PYTHONUNBUFFERED": "1",
        "PYTHONNOUSERSITE": "1",
    }
    (root / "operator-home").mkdir(parents=True, exist_ok=True)

    outside = args.fixture_root.resolve()
    versions = {
        "skill_lens_metadata": probe(
            [
                str(args.lane_python),
                "-c",
                "import importlib.metadata as m, skill_lens, textual; "
                "print(m.version('skill-lens-cli')); print(skill_lens.__version__); "
                "print(textual.__version__); print(skill_lens.__file__)",
            ],
            env,
            outside,
        ),
        "cli_version": probe([str(args.binary), "--version"], env, outside),
    }

    scenarios = {
        "nonempty_100x30": drive(args.binary, nonempty_home, (100, 30), full_plan(), env),
        "nonempty_60x24": drive(args.binary, nonempty_home, (60, 24), full_plan(), env),
        "empty_100x30": drive(args.binary, empty_home, (100, 30), empty_plan(), env),
        "empty_60x24": drive(args.binary, empty_home, (60, 24), empty_plan(), env),
    }

    fallbacks = {
        "extra_plain_pty": pty_probe([str(args.binary), "--plain"], env, (100, 30), outside),
        "extra_bare_noninteractive": probe([str(args.binary)], env, outside),
        "extra_tui_noninteractive": probe([str(args.binary), "tui"], env, outside),
        "base_bare_interactive_pty": pty_probe([str(args.base_binary)], env, (100, 30), outside),
        "base_bare_noninteractive": probe([str(args.base_binary)], env, outside),
        "base_tui_noninteractive": probe([str(args.base_binary), "tui"], env, outside),
        "base_tui_explicit_sandbox": probe(
            [str(args.base_binary), "tui", "--sandbox", str(empty_home)], env, outside
        ),
    }

    fallback_checks = {
        "plain_prints_help": fallbacks["extra_plain_pty"]["exit_code"] == 0
        and "Usage: skill-lens" in fallbacks["extra_plain_pty"]["output"]
        and "Skill Lens Home" not in fallbacks["extra_plain_pty"]["output"],
        "bare_noninteractive_prints_help": fallbacks["extra_bare_noninteractive"]["exit_code"] == 0
        and "Usage: skill-lens" in fallbacks["extra_bare_noninteractive"]["stdout"]
        and "Skill Lens Home" not in fallbacks["extra_bare_noninteractive"]["stdout"],
        "bare_noninteractive_has_no_tip": "Tip:"
        not in fallbacks["extra_bare_noninteractive"]["stdout"],
        "tui_noninteractive_exits_2": fallbacks["extra_tui_noninteractive"]["exit_code"] == 2
        and "requires an interactive terminal" in fallbacks["extra_tui_noninteractive"]["stderr"],
        "base_bare_prints_help_without_tip": fallbacks["base_bare_noninteractive"]["exit_code"] == 0
        and "Usage: skill-lens" in fallbacks["base_bare_noninteractive"]["stdout"]
        and "Tip:" not in fallbacks["base_bare_noninteractive"]["stdout"],
        "base_bare_interactive_prints_tip": fallbacks["base_bare_interactive_pty"]["exit_code"] == 0
        and "Usage: skill-lens" in fallbacks["base_bare_interactive_pty"]["output"]
        and "Tip:" in fallbacks["base_bare_interactive_pty"]["output"]
        and "skill-lens-cli[tui]" in fallbacks["base_bare_interactive_pty"]["output"],
        "base_tui_missing_extra_exits_2": fallbacks["base_tui_noninteractive"]["exit_code"] == 2
        and "skill-lens-cli[tui]" in fallbacks["base_tui_noninteractive"]["stderr"]
        and "Traceback" not in fallbacks["base_tui_noninteractive"]["stderr"],
        "base_tui_with_sandbox_exits_2": fallbacks["base_tui_explicit_sandbox"]["exit_code"] == 2,
    }

    version_lines = versions["skill_lens_metadata"]["stdout"].strip().splitlines()
    receipt = {
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "os": os.uname().sysname + " " + os.uname().release,
        "machine": os.uname().machine,
        "terminal": env["TERM"],
        "driver_python": sys.version,
        "artifact_sha256": args.artifact_sha256,
        "installed": {
            "metadata_version": version_lines[0] if version_lines else "",
            "package_version": version_lines[1] if len(version_lines) > 1 else "",
            "textual_version": version_lines[2] if len(version_lines) > 2 else "",
            "skill_lens_file": version_lines[3] if len(version_lines) > 3 else "",
            "cli_version_output": versions["cli_version"]["stdout"].strip(),
        },
        "driver_cwd": str(outside),
        "scenarios": scenarios,
        "fallbacks": fallbacks,
        "fallback_checks": fallback_checks,
        "claim_boundary": (
            "Automated pseudo-terminal smoke evidence only. It is not human visual approval, "
            "hosted CI, or a release."
        ),
    }
    receipt["all_passed"] = (
        all(scenario["all_passed"] for scenario in scenarios.values())
        and all(fallback_checks.values())
        and receipt["installed"]["metadata_version"] == "0.2.0"
        and receipt["installed"]["package_version"] == "0.2.0"
        and receipt["installed"]["cli_version_output"] == "skill-lens 0.2.0"
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    for name, scenario in scenarios.items():
        print(f"{name}: {'pass' if scenario['all_passed'] else 'FAIL'}")
        for step in scenario["steps"]:
            status = "ok" if step["ok"] else f"MISSING {step['missing']}"
            print(f"   {step['id']:18s} {status}")
        print(
            f"   restore: exit={scenario['restore']['returncode']} "
            f"alt_screen_left={scenario['restore']['alternate_screen_left']} "
            f"cursor_shown={scenario['restore']['cursor_shown']}"
        )
    for name, ok in fallback_checks.items():
        print(f"fallback {name}: {'ok' if ok else 'FAIL'}")
    print(f"all_passed: {receipt['all_passed']}")
    return 0 if receipt["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
