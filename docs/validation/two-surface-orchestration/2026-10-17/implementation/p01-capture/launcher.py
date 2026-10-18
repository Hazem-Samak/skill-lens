"""Native Hermes launcher for P01 request evidence capture.

Uses hermes_cli._launchers.runtime_command to exec Hermes under its native managed
Python environment with hermes_bootstrap and authentic HERMES_HOME.
Requires genuine HERDR_ENV=1 for real agent launch, while allowing offline --help
and test inspection.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

APPROVED_BASE_URL = "http://127.0.0.1:8787/chatgpt"
APPROVED_PROVIDER = "openai-codex"
APPROVED_MODEL = "gpt-6.1-sol"
APPROVED_REASONING = "high"
APPROVED_TOOLSETS = "terminal,file"

DEFAULT_HERMES_ROOT = Path("/Users/corvette/.hermes/hermes-agent")
DEFAULT_MANAGED_PYTHON = Path(
    "/Users/corvette/.hermes/tools/python-3.14.7+20260901-darwin-arm64/bin/python3"
)
OBSERVER_SCRIPT_PATH = Path(__file__).parent / "observer.py"


def is_strictly_help(args: list[str]) -> bool:
    """Return True only if args strictly contains help flag(s) and nothing else."""
    return bool(args) and set(args).issubset({"-h", "--help"})


def validate_launch_arguments(args: list[str]) -> None:
    """Validate that CLI arguments strictly match approved P01 options and reject injection."""
    # Check for forbidden injection flags without echoing values
    forbidden = {"-z", "--oneshot", "--eval", "-q", "--query"}
    for f in forbidden:
        if f in args:
            raise ValueError("Forbidden prompt/execution flag rejected")

    # Parse and check approved structure
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--cli", action="store_true")
    parser.add_argument("--ignore-rules", action="store_true")
    parser.add_argument("--toolsets", type=str)
    parser.add_argument("--provider", type=str)
    parser.add_argument("--pass-session-id", action="store_true")
    parser.add_argument("--in", dest="in_dir", type=str)
    parser.add_argument("-m", "--model", type=str)
    parser.add_argument("--reasoning", type=str)

    parsed, unknown = parser.parse_known_args(args)
    if unknown:
        raise ValueError("Unapproved extra CLI flags rejected")

    if not parsed.cli:
        raise ValueError("Missing required flag: --cli")
    if not parsed.ignore_rules:
        raise ValueError("Missing required flag: --ignore-rules")
    if not parsed.pass_session_id:
        raise ValueError("Missing required flag: --pass-session-id")
    if parsed.provider != APPROVED_PROVIDER:
        raise ValueError(f"Provider must be {APPROVED_PROVIDER}")
    if parsed.model != APPROVED_MODEL:
        raise ValueError(f"Model must be {APPROVED_MODEL}")
    if parsed.reasoning != APPROVED_REASONING:
        raise ValueError(f"Reasoning must be {APPROVED_REASONING}")
    if parsed.toolsets != APPROVED_TOOLSETS:
        raise ValueError(f"Toolsets must be {APPROVED_TOOLSETS}")
    if not parsed.in_dir:
        raise ValueError("Missing required flag: --in <directory>")


def build_runtime_command(
    args: list[str],
    *,
    repo_root: Path | None = None,
    observer_script: Path | None = None,
    python_path: Path | None = None,
    is_offline_help: bool = False,
) -> list[str]:
    """Construct the runtime argv using hermes_cli._launchers.runtime_command."""
    root = (repo_root or DEFAULT_HERMES_ROOT).resolve()
    obs = (observer_script or OBSERVER_SCRIPT_PATH).resolve()
    py = (python_path or DEFAULT_MANAGED_PYTHON).resolve()

    if not obs.exists():
        raise FileNotFoundError(f"Observer script not found: {obs}")

    literal_code: str | None = None

    if is_offline_help:
        if not is_strictly_help(args):
            raise ValueError("Help bypass is strictly for -h/--help flags alone")
        # For offline help, do not execute observer trampoline; invoke native CLI directly
        literal_code = None
    else:
        # Require genuine HERDR_ENV=1 for real agent launch
        if os.environ.get("HERDR_ENV") != "1":
            raise RuntimeError(
                "Genuine HERDR_ENV=1 required for real launch; refusing to launch agent without "
                "Herdr environment."
            )

        # Validate HERMES_CODEX_BASE_URL without echoing environment values
        base_url = os.environ.get("HERMES_CODEX_BASE_URL", "")
        if base_url.rstrip("/") != APPROVED_BASE_URL:
            raise ValueError(f"Invalid HERMES_CODEX_BASE_URL: expected {APPROVED_BASE_URL}")

        validate_launch_arguments(args)
        # Literal pinned observer script path executed via runpy.run_path
        literal_code = f"import runpy; runpy.run_path({repr(str(obs))}, run_name='__main__')"

    # Import hermes_cli._launchers
    sys.path.insert(0, str(root))
    import hermes_bootstrap  # noqa: F401
    from hermes_cli import _launchers

    cmd = _launchers.runtime_command(root, args, code=literal_code, python=py)
    return cmd


def main() -> None:
    """CLI launcher entrypoint."""
    args = sys.argv[1:]
    is_help = is_strictly_help(args)

    try:
        cmd = build_runtime_command(args, is_offline_help=is_help)
    except Exception as exc:
        print(f"Launcher configuration error: {exc}", file=sys.stderr)
        sys.exit(2)

    # Exec without shell
    os.execv(cmd[0], cmd)


if __name__ == "__main__":
    main()
