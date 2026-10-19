"""Read-only AST source guard and target preservation tests (Assignment U2).

Specification reference: FULL_SCREEN_TUI.md §10 and Step 2.
Enforces:
1. Recursive AST source inspection over `skill_lens/tui/`
2. Strict rejection of banned root imports:
   shutil, subprocess, tempfile, sqlite3, socket, requests, httpx, skill_lens.render, rich
3. Rejection of os destructive calls (remove, unlink, rmdir, rename, replace) via aliases
4. Rejection of Path write and instance methods
   (write_text, write_bytes, unlink, mkdir, touch, rename, rmdir)
5. Rejection of open write modes ("w", "a", "x", "+") on builtin, io.open,
   Path.open, and unresolved modes
6. Rejection of terminal writes (bare print, sys.stdout.write, sys.stderr.write, console.print)
7. Mutation testing of every guard category (control, mutant, restore)
8. Recursive package traversal proof
9. Synthetic target preservation across the complete TUI lifecycle (bytes, modes, symlinks)
"""

from __future__ import annotations

import ast
import os
import shutil
from pathlib import Path

import pytest
from textual.pilot import Pilot

import skill_lens.tui as tui
from skill_lens.core.exitcodes import ExitCode
from tests.fixtures.scenarios import build_scenario

# TUI_DIR resolves dynamically from the imported skill_lens.tui package.
# This ensures AST source inspection and mutation controls function seamlessly
# both in the development checkout and in clean installed packaging lanes.
assert tui.__file__ is not None, "skill_lens.tui must be an imported package with __file__"
TUI_DIR = Path(tui.__file__).resolve().parent

BANNED_IMPORT_ROOTS = frozenset(
    {
        "shutil",
        "subprocess",
        "tempfile",
        "sqlite3",
        "socket",
        "requests",
        "httpx",
        "rich",
    }
)

BANNED_OS_METHODS = frozenset(
    {
        "remove",
        "unlink",
        "rmdir",
        "rename",
        "replace",
        "chmod",
        "fchmod",
        "lchmod",
        "system",
        "popen",
    }
)

BANNED_PATH_METHODS = frozenset(
    {
        "write_text",
        "write_bytes",
        "unlink",
        "mkdir",
        "touch",
        "rename",
        "replace",
        "chmod",
        "symlink_to",
        "hardlink_to",
        "rmdir",
    }
)

WRITE_MODE_CHARS = frozenset({"w", "a", "x", "+"})


class ReadOnlyASTVisitor(ast.NodeVisitor):
    """AST visitor that checks source files for prohibited write and terminal operations.

    Known-source limits: This visitor inspects standard AST nodes for known imports,
    aliases, method calls, and open signatures. It is not an adversarial execution
    sandbox and does not attempt dynamic runtime tracing, reflection, or arbitrary
    getattr analysis.
    """

    def __init__(self, filepath: Path) -> None:
        super().__init__()
        self.filepath = filepath
        self.violations: list[str] = []

        # Alias tracking
        self.os_aliases: set[str] = {"os"}
        self.os_banned_func_aliases: dict[str, str] = {}
        self.sys_aliases: set[str] = {"sys"}
        self.sys_stream_aliases: dict[str, str] = {}
        self.module_open_aliases: set[str] = {"io", "builtins", "_io"}
        self.open_func_aliases: set[str] = {"open"}
        self.os_open_aliases: set[str] = set()
        self.print_aliases: set[str] = {"print"}

    def _add_violation(self, node: ast.AST, reason: str) -> None:
        line = getattr(node, "lineno", 0)
        self.violations.append(f"{self.filepath.name}:{line}: {reason}")

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".")[0]
            if root in BANNED_IMPORT_ROOTS:
                self._add_violation(node, f"Banned import '{alias.name}'")
            elif (
                alias.name == "skill_lens.render"
                or alias.name.startswith("skill_lens.render.")
                or "render" in alias.name.split(".")
            ):
                self._add_violation(node, f"Banned render import '{alias.name}'")
            elif alias.name == "os":
                self.os_aliases.add(alias.asname or alias.name)
            elif alias.name == "sys":
                self.sys_aliases.add(alias.asname or alias.name)
            elif alias.name in ("io", "builtins", "_io"):
                self.module_open_aliases.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        root = module.split(".")[0]
        if root in BANNED_IMPORT_ROOTS:
            self._add_violation(node, f"Banned import from '{module}'")
        elif (
            module == "skill_lens.render"
            or module.startswith("skill_lens.render.")
            or module.endswith(".render")
            or module == "render"
            or (
                module == "skill_lens"
                and any(
                    alias.name == "render" or alias.name.startswith("render.")
                    for alias in node.names
                )
            )
        ):
            self._add_violation(node, f"Banned render import from '{module}'")
        elif node.level > 0 and (
            module == "render"
            or module.endswith(".render")
            or any(
                alias.name == "render" or alias.name.startswith("render.") for alias in node.names
            )
        ):
            self._add_violation(node, "Banned render relative import")
        elif module == "os":
            for alias in node.names:
                if alias.name in BANNED_OS_METHODS:
                    self.os_banned_func_aliases[alias.asname or alias.name] = alias.name
                    self._add_violation(node, f"Banned import of os.{alias.name}")
                elif alias.name == "open":
                    self.os_open_aliases.add(alias.asname or alias.name)
        elif module == "sys":
            for alias in node.names:
                if alias.name in ("stdout", "stderr"):
                    self.sys_stream_aliases[alias.asname or alias.name] = alias.name
        elif module in ("io", "builtins", "_io") or module == "":
            for alias in node.names:
                if alias.name == "open":
                    self.open_func_aliases.add(alias.asname or alias.name)
                elif alias.name == "print":
                    self.print_aliases.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # 1. Bare print(...) or print alias
        if isinstance(node.func, ast.Name) and node.func.id in self.print_aliases:
            self._add_violation(node, "Banned bare print() call")

        # 2. Direct calls to imported os destructive/process functions (e.g. rm, system)
        elif isinstance(node.func, ast.Name) and node.func.id in self.os_banned_func_aliases:
            orig = self.os_banned_func_aliases[node.func.id]
            self._add_violation(node, f"Banned call to os.{orig}() via alias '{node.func.id}'")

        # 3. Direct calls to open or open alias (e.g. reader("path", "w"))
        elif isinstance(node.func, ast.Name) and node.func.id in self.os_open_aliases:
            self._check_os_open_call(node)
        elif isinstance(node.func, ast.Name) and node.func.id in self.open_func_aliases:
            self._check_open_call(node, mode_pos_idx=1)

        # 4. Method calls obj.attr(...)
        elif isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            obj = node.func.value

            # os destructive or process execution methods: os.remove, os.system, my_os.popen, etc.
            if (
                isinstance(obj, ast.Name)
                and obj.id in self.os_aliases
                and attr_name in BANNED_OS_METHODS
            ):
                self._add_violation(node, f"Banned call to os.{attr_name}()")

            # Path write methods on any instance: .write_text, .write_bytes, .unlink, .mkdir, etc.
            if attr_name in BANNED_PATH_METHODS:
                self._add_violation(node, f"Banned Path write method '{attr_name}()'")

            # Open calls: builtin open(), io.open(), _io.open(), Path.open(), p.open(), os.open()
            if attr_name == "open":
                if isinstance(obj, ast.Name) and obj.id in self.os_aliases:
                    self._check_os_open_call(node)
                else:
                    is_module_call = isinstance(obj, ast.Name) and (
                        obj.id in self.module_open_aliases
                        or obj.id in ("Path", "PosixPath", "WindowsPath")
                    )
                    mode_pos_idx = 1 if is_module_call else 0
                    self._check_open_call(node, mode_pos_idx=mode_pos_idx)

            # Terminal writes via stdout.write / stderr.write
            if attr_name == "write":
                if isinstance(obj, ast.Attribute) and obj.attr in ("stdout", "stderr"):
                    if isinstance(obj.value, ast.Name) and obj.value.id in self.sys_aliases:
                        self._add_violation(node, f"Banned direct sys.{obj.attr}.write()")
                elif isinstance(obj, ast.Name) and obj.id in self.sys_stream_aliases:
                    orig = self.sys_stream_aliases[obj.id]
                    self._add_violation(node, f"Banned direct {orig}.write() via alias '{obj.id}'")

            # Console terminal writes: console.print(...)
            if attr_name == "print":
                self._add_violation(node, "Banned Console.print() terminal write")

        self.generic_visit(node)

    def _check_os_open_call(self, node: ast.Call) -> None:
        """Inspect flags argument on os.open(path, flags, ...)."""
        if any(isinstance(arg, ast.Starred) for arg in node.args):
            self._add_violation(node, "Unresolved or non-literal flags in os.open call (*args)")
            return

        flags_arg: ast.expr | None = None
        for kw in node.keywords:
            if kw.arg == "flags":
                flags_arg = kw.value
                break
            elif kw.arg is None:
                self._add_violation(
                    node, "Unresolved or non-literal flags in os.open call (**kwargs)"
                )
                return

        if flags_arg is None and len(node.args) > 1:
            flags_arg = node.args[1]

        if flags_arg is None:
            self._add_violation(node, "Missing flags in os.open call")
            return

        banned_flag_names = {
            "O_WRONLY",
            "O_RDWR",
            "O_CREAT",
            "O_APPEND",
            "O_TRUNC",
            "O_EXCL",
        }

        def contains_banned(expr: ast.expr) -> bool:
            if isinstance(expr, ast.Attribute) and expr.attr in banned_flag_names:
                return True
            if isinstance(expr, ast.Name) and expr.id in banned_flag_names:
                return True
            if isinstance(expr, ast.BinOp):
                return contains_banned(expr.left) or contains_banned(expr.right)
            if isinstance(expr, ast.Constant):
                return bool(isinstance(expr.value, int) and expr.value != 0)
            return True

        def is_clean_read_only(expr: ast.expr) -> bool:
            if isinstance(expr, ast.Attribute) and expr.attr == "O_RDONLY":
                return True
            if isinstance(expr, ast.Name) and expr.id == "O_RDONLY":
                return True
            return bool(isinstance(expr, ast.Constant) and expr.value == 0)

        if not is_clean_read_only(flags_arg):
            if contains_banned(flags_arg):
                self._add_violation(node, "Banned write flags in os.open call")
            else:
                self._add_violation(node, "Unresolved or non-literal flags in os.open call")

    def _check_open_call(self, node: ast.Call, *, mode_pos_idx: int) -> None:
        """Inspect mode arguments on open(...), io.open(...), Path.open(...), and obj.open(...)."""
        # Check for *args unpacking
        if any(isinstance(arg, ast.Starred) for arg in node.args):
            self._add_violation(node, "Unresolved or non-literal mode in open call (*args)")
            return

        mode_arg: ast.expr | None = None
        has_kwargs_unpacking = False

        # Check keyword arguments mode=... and **kwargs unpacking
        for kw in node.keywords:
            if kw.arg == "mode":
                mode_arg = kw.value
                break
            elif kw.arg is None:
                has_kwargs_unpacking = True

        # Check positional argument
        if mode_arg is None and len(node.args) > mode_pos_idx:
            mode_arg = node.args[mode_pos_idx]

        if mode_arg is not None:
            # Mode must be a constant string literal without write flags
            if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
                if any(ch in mode_arg.value for ch in WRITE_MODE_CHARS):
                    self._add_violation(node, f"Banned write mode '{mode_arg.value}' in open call")
            else:
                # Dynamic or unresolved mode
                self._add_violation(node, "Unresolved or non-literal mode in open call")
        elif has_kwargs_unpacking:
            self._add_violation(node, "Unresolved or non-literal mode in open call (**kwargs)")


def check_source_tree(root_dir: Path) -> list[str]:
    """Recursively inspect all Python files under root_dir and return violations."""
    all_violations: list[str] = []
    py_files = sorted(root_dir.rglob("*.py"))
    assert py_files, f"No Python files found under {root_dir}"

    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))
        visitor = ReadOnlyASTVisitor(py_file)
        visitor.visit(tree)
        all_violations.extend(visitor.violations)

    return all_violations


# ---------------------------------------------------------------------------
# Section 10 Shipped Code AST Guard
# ---------------------------------------------------------------------------


def test_shipped_tui_code_has_zero_read_only_violations() -> None:
    """The shipped skill_lens/tui package must have 0 read-only violations."""
    violations = check_source_tree(TUI_DIR)
    assert violations == [], "Shipped tui/ code contains prohibited operations:\n" + "\n".join(
        violations
    )


def test_actual_package_discovery_finds_all_tui_modules() -> None:
    """Verify package discovery inspects __init__.py, app.py, session.py, and subpackages."""
    py_files = {p.name for p in TUI_DIR.rglob("*.py")}
    assert "__init__.py" in py_files
    assert "app.py" in py_files
    assert "session.py" in py_files


def test_skill_lens_app_neutralizes_inherited_writes_and_palette() -> None:
    """SkillLensApp overrides and neutralizes Textual's inherited command palette
    and screenshot/delivery writing methods, enforcing the Section 10 read-only invariant."""
    from skill_lens import __version__
    from skill_lens.tui.app import SkillLensApp

    # Class-level attributes
    assert __version__ == SkillLensApp.SUB_TITLE
    assert SkillLensApp.ENABLE_COMMAND_PALETTE is False
    assert set() == SkillLensApp.COMMANDS

    # Overridden methods to prevent inherited disk writes or command palette exposure
    neutralized_methods = {
        "action_command_palette",
        "get_system_commands",
        "action_screenshot",
        "deliver_screenshot",
        "save_screenshot",
        "deliver_binary",
        "deliver_text",
    }
    for method_name in neutralized_methods:
        assert method_name in SkillLensApp.__dict__, (
            f"SkillLensApp must explicitly override and neutralize '{method_name}'"
        )


# ---------------------------------------------------------------------------
# Mutation Suite (Named Categories, Control, Mutant, Restore)
# ---------------------------------------------------------------------------

MUTATION_CASES: list[tuple[str, str, str]] = [
    # Category 1: Banned root imports
    ("import_shutil", "import shutil", "Banned import 'shutil'"),
    ("import_subprocess", "import subprocess", "Banned import 'subprocess'"),
    ("import_tempfile", "import tempfile", "Banned import 'tempfile'"),
    ("import_sqlite3", "import sqlite3", "Banned import 'sqlite3'"),
    ("import_socket", "import socket", "Banned import 'socket'"),
    ("import_requests", "import requests", "Banned import 'requests'"),
    ("import_httpx", "import httpx", "Banned import 'httpx'"),
    ("import_render", "import skill_lens.render", "Banned render import"),
    ("from_render", "from skill_lens.render import render_scan", "Banned render import from"),
    ("import_rich", "import rich", "Banned import 'rich'"),
    ("from_rich", "from rich.console import Console", "Banned import from 'rich.console'"),
    # Category 2: os destructive calls and aliases
    ("os_remove", "import os\nos.remove('target.txt')", "Banned call to os.remove()"),
    ("os_unlink", "import os\nos.unlink('target.txt')", "Banned call to os.unlink()"),
    ("os_rmdir", "import os\nos.rmdir('target_dir')", "Banned call to os.rmdir()"),
    ("os_rename", "import os\nos.rename('a', 'b')", "Banned call to os.rename()"),
    ("os_replace", "import os\nos.replace('a', 'b')", "Banned call to os.replace()"),
    (
        "os_alias_remove",
        "import os as custom_os\ncustom_os.remove('x')",
        "Banned call to os.remove()",
    ),
    (
        "os_from_import_remove",
        "from os import remove as custom_rm\ncustom_rm('x')",
        "Banned import of os.remove",
    ),
    ("os_system", "import os\nos.system('echo hi')", "Banned call to os.system()"),
    ("os_popen", "import os\nos.popen('echo hi')", "Banned call to os.popen()"),
    (
        "os_alias_system",
        "import os as custom_os\ncustom_os.system('echo hi')",
        "Banned call to os.system()",
    ),
    (
        "os_alias_popen",
        "import os as custom_os\ncustom_os.popen('echo hi')",
        "Banned call to os.popen()",
    ),
    (
        "os_from_import_system",
        "from os import system as sys_exec\nsys_exec('echo hi')",
        "Banned import of os.system",
    ),
    (
        "os_from_import_popen",
        "from os import popen as pipe_open\npipe_open('echo hi')",
        "Banned import of os.popen",
    ),
    # Category 3: Path write methods and instance calls
    (
        "path_write_text",
        "from pathlib import Path\nPath('x').write_text('content')",
        "Banned Path write method 'write_text()'",
    ),
    (
        "path_write_bytes",
        "from pathlib import Path\nPath('x').write_bytes(b'content')",
        "Banned Path write method 'write_bytes()'",
    ),
    (
        "path_unlink",
        "from pathlib import Path\nPath('x').unlink()",
        "Banned Path write method 'unlink()'",
    ),
    (
        "path_mkdir",
        "from pathlib import Path\nPath('x').mkdir()",
        "Banned Path write method 'mkdir()'",
    ),
    (
        "path_touch",
        "from pathlib import Path\nPath('x').touch()",
        "Banned Path write method 'touch()'",
    ),
    (
        "path_rename",
        "from pathlib import Path\nPath('x').rename('y')",
        "Banned Path write method 'rename()'",
    ),
    (
        "path_rmdir",
        "from pathlib import Path\nPath('x').rmdir()",
        "Banned Path write method 'rmdir()'",
    ),
    (
        "path_instance_write",
        "def f(p):\n    p.write_text('bad')",
        "Banned Path write method 'write_text()'",
    ),
    (
        "path_replace",
        "from pathlib import Path\nPath('x').replace('y')",
        "Banned Path write method 'replace()'",
    ),
    (
        "path_chmod",
        "from pathlib import Path\nPath('x').chmod(0o777)",
        "Banned Path write method 'chmod()'",
    ),
    (
        "os_chmod",
        "import os\nos.chmod('x', 0o777)",
        "Banned call to os.chmod()",
    ),
    (
        "os_open_wronly",
        "import os\nos.open('x', os.O_WRONLY | os.O_CREAT)",
        "Banned write flags in os.open call",
    ),
    # Category 4: Open write and unresolved modes
    ("builtin_open_w", "open('x', 'w')", "Banned write mode 'w'"),
    ("builtin_open_kw_w", "open('x', mode='w')", "Banned write mode 'w'"),
    ("builtin_open_a", "open('x', 'a')", "Banned write mode 'a'"),
    ("builtin_open_x", "open('x', 'x')", "Banned write mode 'x'"),
    ("builtin_open_r_plus", "open('x', 'r+')", "Banned write mode 'r+'"),
    ("builtin_open_unresolved", "m = 'w'\nopen('x', m)", "Unresolved or non-literal mode"),
    ("io_open_w", "import io\nio.open('x', 'w')", "Banned write mode 'w'"),
    (
        "builtins_open_w",
        "import builtins\nbuiltins.open('probe.md', 'w')",
        "Banned write mode 'w'",
    ),
    (
        "builtins_open_kw_w",
        "import builtins\nbuiltins.open('probe.md', mode='w')",
        "Banned write mode 'w'",
    ),
    (
        "builtins_open_a",
        "import builtins\nbuiltins.open('probe.md', 'a')",
        "Banned write mode 'a'",
    ),
    (
        "builtins_open_x",
        "import builtins\nbuiltins.open('probe.md', 'x')",
        "Banned write mode 'x'",
    ),
    (
        "builtins_open_r_plus",
        "import builtins\nbuiltins.open('probe.md', 'r+')",
        "Banned write mode 'r+'",
    ),
    (
        "builtins_open_unresolved",
        "import builtins\nm = 'w'\nbuiltins.open('probe.md', m)",
        "Unresolved or non-literal mode",
    ),
    (
        "builtins_open_args_unresolved",
        "import builtins\nbuiltins.open('probe.md', *args)",
        "Unresolved or non-literal mode in open call (*args)",
    ),
    (
        "builtins_open_kwargs_unresolved",
        "import builtins\nbuiltins.open('probe.md', **kwargs)",
        "Unresolved or non-literal mode in open call (**kwargs)",
    ),
    (
        "builtins_open_alias_module_w",
        "import builtins as b\nb.open('probe.md', 'w')",
        "Banned write mode 'w'",
    ),
    (
        "io_open_kw_w",
        "import io\nio.open('probe.md', mode='w')",
        "Banned write mode 'w'",
    ),
    (
        "io_open_alias_module_w",
        "import io as my_io\nmy_io.open('probe.md', 'w')",
        "Banned write mode 'w'",
    ),
    (
        "_io_open_w",
        "import _io\n_io.open('probe.md', 'w')",
        "Banned write mode 'w'",
    ),
    (
        "_io_open_kw_w",
        "import _io\n_io.open('probe.md', mode='w')",
        "Banned write mode 'w'",
    ),
    (
        "_io_open_alias_module_w",
        "import _io as raw_io\nraw_io.open('probe.md', 'w')",
        "Banned write mode 'w'",
    ),
    (
        "_io_open_alias_func_w",
        "from _io import open as raw_open\nraw_open('probe.md', 'w')",
        "Banned write mode 'w'",
    ),
    (
        "path_class_open_w",
        "from pathlib import Path\nPath.open(p, 'w')",
        "Banned write mode 'w'",
    ),
    ("path_open_w", "from pathlib import Path\nPath('x').open('w')", "Banned write mode 'w'"),
    (
        "path_open_kw_a",
        "from pathlib import Path\nPath('x').open(mode='a')",
        "Banned write mode 'a'",
    ),
    (
        "path_open_unresolved",
        "from pathlib import Path\nPath('x').open(some_mode)",
        "Unresolved or non-literal mode",
    ),
    # Category 5: Terminal writes
    ("bare_print", "print('hello')", "Banned bare print()"),
    (
        "sys_stdout_write",
        "import sys\nsys.stdout.write('hello')",
        "Banned direct sys.stdout.write()",
    ),
    (
        "sys_stderr_write",
        "import sys\nsys.stderr.write('hello')",
        "Banned direct sys.stderr.write()",
    ),
    (
        "from_sys_stdout_write",
        "from sys import stdout\nstdout.write('hello')",
        "Banned direct stdout.write()",
    ),
    ("console_print", "console.print('hello')", "Banned Console.print()"),
    (
        "io_open_alias_w",
        "from io import open as reader\nreader('x', 'w')",
        "Banned write mode 'w'",
    ),
    (
        "builtins_open_alias_w",
        "from builtins import open as reader\nreader('x', 'w')",
        "Banned write mode 'w'",
    ),
    (
        "builtins_print_alias",
        "from builtins import print as output\noutput('bad')",
        "Banned bare print() call",
    ),
    (
        "from_skill_lens_render",
        "from skill_lens import render as renderer",
        "Banned render import from 'skill_lens'",
    ),
    (
        "relative_render_import",
        "from .. import render",
        "Banned render relative import",
    ),
    (
        "open_kwargs_unresolved",
        "open('x', **options)",
        "Unresolved or non-literal mode in open call",
    ),
    (
        "open_args_unresolved",
        "open('x', *args)",
        "Unresolved or non-literal mode in open call",
    ),
]


VALID_READ_SNIPPETS: list[str] = [
    "import os\nos.open('data.md', os.O_RDONLY)",
    "import os\nos.open('data.md', 0)",
    "open('x')",
    "open('x', 'r')",
    "open('x', mode='r')",
    "open('x', 'rb')",
    "open('data.md')",
    "open('data.md', 'r')",
    "open('data.md', mode='r')",
    "open('data.md', 'rb')",
    "from io import open as reader\nreader('x')",
    "from io import open as reader\nreader('x', 'r')",
    "from io import open as reader\nreader('data.md', 'rb')",
    "from builtins import open as reader\nreader('x')",
    "from builtins import open as reader\nreader('x', 'r')",
    "from builtins import open as reader\nreader('data.md', 'rb')",
    "from _io import open as reader\nreader('x')",
    "from _io import open as reader\nreader('x', 'r')",
    "from _io import open as reader\nreader('data.md', 'rb')",
    "from pathlib import Path\nPath('x').open()",
    "from pathlib import Path\nPath('x').open('r')",
    "from pathlib import Path\nPath('x').open(mode='r')",
    "from pathlib import Path\nPath('data.md').open('rb')",
    "from pathlib import Path\np = Path('data.md')\nPath.open(p, 'r')",
    "import io\nio.open('x')",
    "import io\nio.open('x', 'r')",
    "import io\nio.open('data.md')",
    "import io\nio.open('data.md', 'r')",
    "import io\nio.open('data.md', mode='r')",
    "import io\nio.open('data.md', 'rb')",
    "import io as my_io\nmy_io.open('x', 'r')",
    "import io as my_io\nmy_io.open('data.md', 'rb')",
    "import builtins\nbuiltins.open('x')",
    "import builtins\nbuiltins.open('x', 'r')",
    "import builtins\nbuiltins.open('data.md')",
    "import builtins\nbuiltins.open('data.md', 'r')",
    "import builtins\nbuiltins.open('data.md', mode='r')",
    "import builtins\nbuiltins.open('data.md', 'rb')",
    "import builtins as b\nb.open('x')",
    "import builtins as b\nb.open('x', 'r')",
    "import builtins as b\nb.open('data.md', 'rb')",
    "import _io\n_io.open('x')",
    "import _io\n_io.open('x', 'r')",
    "import _io\n_io.open('data.md')",
    "import _io\n_io.open('data.md', 'r')",
    "import _io\n_io.open('data.md', mode='r')",
    "import _io\n_io.open('data.md', 'rb')",
    "import _io as raw_io\nraw_io.open('x', 'r')",
    "import _io as raw_io\nraw_io.open('data.md', 'rb')",
    "open('x', encoding='utf-8')",
    "open('data.md', encoding='utf-8')",
    "open('x', mode='r', **extra_kwargs)",
    "import os\nos.getcwd()",
    "import os\nos.listdir('x')",
    "import os\nos.stat('data.md')",
    "import os as my_os\nmy_os.path.exists('x')",
    "from os import getcwd\ngetcwd()",
]


@pytest.mark.parametrize("read_snippet", VALID_READ_SNIPPETS)
def test_valid_read_patterns_produce_zero_violations(tmp_path: Path, read_snippet: str) -> None:
    """Valid read-only calls (open 'r', 'rb', default mode, Path.open 'r') must not be flagged."""
    f = tmp_path / "read_module.py"
    f.write_text(f"{read_snippet}\n", encoding="utf-8")
    violations = check_source_tree(tmp_path)
    assert violations == [], f"Valid read snippet was falsely flagged: {read_snippet}\n{violations}"


@pytest.mark.parametrize("case_id,mutant_snippet,expected_pattern", MUTATION_CASES)
def test_guard_mutations_control_mutant_restore(
    tmp_path: Path, case_id: str, mutant_snippet: str, expected_pattern: str
) -> None:
    """For every guard category: clean control, detected mutation, clean restore."""
    # 1. Clean control: copy valid tui package to temp tree outside checkout
    test_tree = tmp_path / f"test_tree_{case_id}"
    shutil.copytree(TUI_DIR, test_tree)

    control_violations = check_source_tree(test_tree)
    assert control_violations == [], f"Control must be clean for {case_id}"

    # 2. Plant mutant in a file inside test_tree
    target_file = test_tree / "app.py"
    original_content = target_file.read_text(encoding="utf-8")
    mutated_content = original_content + f"\n# MUTANT: {case_id}\n{mutant_snippet}\n"
    target_file.write_text(mutated_content, encoding="utf-8")

    mutant_violations = check_source_tree(test_tree)
    assert len(mutant_violations) >= 1, f"Mutant {case_id} was not detected!"
    matched = any(expected_pattern in v for v in mutant_violations)
    assert matched, (
        f"Mutant {case_id} detected but pattern '{expected_pattern}' not found. "
        f"Found: {mutant_violations}"
    )

    # 3. Clean restore: restore original file and assert 0 violations
    target_file.write_text(original_content, encoding="utf-8")
    restored_violations = check_source_tree(test_tree)
    assert restored_violations == [], f"Restore must be clean for {case_id}"


def test_package_discovery_detects_nested_subdirectories(tmp_path: Path) -> None:
    """Actual package discovery traverses subdirectories recursively."""
    test_tree = tmp_path / "nested_tree"
    shutil.copytree(TUI_DIR, test_tree)

    # Create deep nested package
    nested_dir = test_tree / "subpkg" / "deep"
    nested_dir.mkdir(parents=True)
    nested_file = nested_dir / "nested_bad.py"
    nested_file.write_text("import shutil\n", encoding="utf-8")

    violations = check_source_tree(test_tree)
    assert any("nested_bad.py" in v and "shutil" in v for v in violations), (
        f"Deeply nested file must be discovered; got {violations}"
    )


# ---------------------------------------------------------------------------
# Target Directory Preservation Across Complete Lifecycle
# ---------------------------------------------------------------------------


def _snapshot_tree_state(root: Path) -> dict[str, tuple[bytes, int, str | None]]:
    """Capture relative path -> (content_bytes, st_mode, symlink_target)."""
    snapshot: dict[str, tuple[bytes, int, str | None]] = {}
    for entry in root.rglob("*"):
        rel = str(entry.relative_to(root))
        if entry.is_symlink():
            target = os.readlink(entry)
            snapshot[rel] = (b"", entry.lstat().st_mode, target)
        elif entry.is_file():
            snapshot[rel] = (entry.read_bytes(), entry.stat().st_mode, None)
        elif entry.is_dir():
            snapshot[rel] = (b"", entry.stat().st_mode, None)
    return snapshot


def test_synthetic_target_preservation_across_lifecycle(mock_home: Path) -> None:
    """The TUI lifecycle (launch, refresh, reports, errors, navigation, quit)
    preserves target bytes, file modes, and symlink targets without any writes.
    """
    build_scenario("claude_personal_beats_project", mock_home)

    # Seed explicit synthetic symlink and specific file mode
    target_skill_dir = mock_home / ".claude" / "skills" / "deploy"
    real_target = target_skill_dir / "SKILL.md"
    assert real_target.exists(), "Scenario must contain deploy/SKILL.md"
    symlink_file = target_skill_dir / "symlink_doc.txt"
    symlink_file.symlink_to("SKILL.md")
    real_target.chmod(0o640)

    # Capture initial state of mock HOME
    before = _snapshot_tree_state(mock_home)
    assert len(before) > 0, "Initial target must contain files"
    assert any(s[2] is not None for s in before.values()), "Target must include synthetic symlinks"

    async def full_lifecycle(pilot: Pilot) -> None:
        app = pilot.app
        assert isinstance(app, tui.SkillLensApp)
        # 1. Initial capture
        for _ in range(50):
            if app.controller.current is not None:
                break
            await pilot.pause(0.02)
        assert app.controller.current is not None, "Current snapshot must be available"
        # 2. Home text filter, agent filter (queues Why work) and navigation
        await pilot.press("slash")
        await pilot.press(*"deploy")
        await pilot.press("enter")
        await pilot.press("a")
        for _ in range(50):
            if app.controller.active_requests.get("why") is None:
                break
            await pilot.pause(0.02)
        await pilot.press("escape")
        await pilot.press("down")
        await pilot.press("up")
        await pilot.pause()
        # 3. Refresh
        await pilot.press("r")
        await pilot.pause()
        # 4. Report query
        if app.controller.selected_key:
            app.request_report("why", (app.controller.selected_key, "claude"))
            await pilot.pause()
        # 5. Inject genuinely accepted error and test navigation
        for _ in range(50):
            if app.controller.current is not None:
                break
            await pilot.pause(0.02)
        assert app.controller.current is not None, "Current snapshot must be available"
        gen = app.controller.current.generation
        req, _, _ = app.controller.request_view("why", ("fault_injection_target", "claude"))
        assert req is not None, "Active view request must be registered"
        accepted = app.controller.accept_view_error(
            "why", req.request_id, gen, req.arguments, RuntimeError("injected error")
        )
        assert accepted is True, "Injected view error must be accepted by controller"
        assert app.controller.failed is True, "Controller must be marked failed on unexpected error"
        app._update_ui()
        await pilot.pause()
        # 6. Retry refresh
        await pilot.press("r")
        await pilot.pause()
        # 7. Quit
        await pilot.press("q")

    code = tui.run(mock_home, mock_home, headless=True, auto_pilot=full_lifecycle)
    assert code == int(ExitCode.INTERNAL)

    # Capture state after complete lifecycle
    after = _snapshot_tree_state(mock_home)

    # Assert exact inventory, byte equality, mode equality, and symlink targets
    assert before.keys() == after.keys(), "File inventory in target was modified!"
    for rel_path, before_state in before.items():
        after_state = after[rel_path]
        before_bytes, before_mode, before_symlink = before_state
        after_bytes, after_mode, after_symlink = after_state

        assert before_bytes == after_bytes, f"Bytes changed for {rel_path}"
        assert before_mode == after_mode, f"File mode changed for {rel_path}"
        assert before_symlink == after_symlink, f"Symlink target changed for {rel_path}"


def test_target_preservation_when_cleanup_fails(
    mock_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When cleanup fails (e.g. exception during shutdown), the target directory
    remains untouched and byte-identical, and the failure path is entered."""
    build_scenario("claude_personal_beats_project", mock_home)
    target_skill_dir = mock_home / ".claude" / "skills" / "deploy"
    real_target = target_skill_dir / "SKILL.md"
    symlink_file = target_skill_dir / "symlink_doc.txt"
    symlink_file.symlink_to("SKILL.md")
    real_target.chmod(0o640)

    before = _snapshot_tree_state(mock_home)

    cleanup_called = False
    orig_close = tui.SessionController.close

    def failing_close(self: tui.SessionController) -> int:
        nonlocal cleanup_called
        cleanup_called = True
        orig_close(self)
        raise RuntimeError("simulated cleanup failure")

    monkeypatch.setattr(tui.SessionController, "close", failing_close)

    async def quit_pilot(pilot: Pilot) -> None:
        await pilot.pause()
        await pilot.press("q")

    with pytest.raises(RuntimeError, match="simulated cleanup failure"):
        tui.run(mock_home, mock_home, headless=True, auto_pilot=quit_pilot)

    assert cleanup_called is True, "Cleanup path must have been entered"

    after = _snapshot_tree_state(mock_home)
    assert before == after, "Target files modified despite cleanup failure"
