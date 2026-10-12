# U2 Mutation Campaign Results (AST Guard & Watchdog Discriminator)

Conducted across 73 distinct mutations in isolated disposable trees
and runtime pilot harnesses exercising both the recursive AST checker `check_source_tree`
and the discriminating watchdog prompt-quit selector.
Full execution logs are persisted under `docs/validation/u2/logs/`.

- **Platform:** Darwin arm64 Python 3.11.16
- **Total Mutations:** 73
- **Mutants Killed:** 73
- **Survivors:** 0
- **Duration:** 1.13s

| ID | Snippet / Defect | Expected Violation Pattern / Failure | Outcome | Log |
| --- | --- | --- | :---: | :---: |
| `import_shutil` | `import shutil` | `Banned import 'shutil'` | **KILLED** | [`log`](logs/import_shutil.log) |
| `import_subprocess` | `import subprocess` | `Banned import 'subprocess'` | **KILLED** | [`log`](logs/import_subprocess.log) |
| `import_tempfile` | `import tempfile` | `Banned import 'tempfile'` | **KILLED** | [`log`](logs/import_tempfile.log) |
| `import_sqlite3` | `import sqlite3` | `Banned import 'sqlite3'` | **KILLED** | [`log`](logs/import_sqlite3.log) |
| `import_socket` | `import socket` | `Banned import 'socket'` | **KILLED** | [`log`](logs/import_socket.log) |
| `import_requests` | `import requests` | `Banned import 'requests'` | **KILLED** | [`log`](logs/import_requests.log) |
| `import_httpx` | `import httpx` | `Banned import 'httpx'` | **KILLED** | [`log`](logs/import_httpx.log) |
| `import_render` | `import skill_lens.render` | `Banned render import` | **KILLED** | [`log`](logs/import_render.log) |
| `from_render` | `from skill_lens.render import render_scan` | `Banned render import from` | **KILLED** | [`log`](logs/from_render.log) |
| `import_rich` | `import rich` | `Banned import 'rich'` | **KILLED** | [`log`](logs/import_rich.log) |
| `from_rich` | `from rich.console import Console` | `Banned import from 'rich.console'` | **KILLED** | [`log`](logs/from_rich.log) |
| `os_remove` | `import os os.remove('target.txt')` | `Banned call to os.remove()` | **KILLED** | [`log`](logs/os_remove.log) |
| `os_unlink` | `import os os.unlink('target.txt')` | `Banned call to os.unlink()` | **KILLED** | [`log`](logs/os_unlink.log) |
| `os_rmdir` | `import os os.rmdir('target_dir')` | `Banned call to os.rmdir()` | **KILLED** | [`log`](logs/os_rmdir.log) |
| `os_rename` | `import os os.rename('a', 'b')` | `Banned call to os.rename()` | **KILLED** | [`log`](logs/os_rename.log) |
| `os_replace` | `import os os.replace('a', 'b')` | `Banned call to os.replace()` | **KILLED** | [`log`](logs/os_replace.log) |
| `os_alias_remove` | `import os as custom_os custom_os.remove('x')` | `Banned call to os.remove()` | **KILLED** | [`log`](logs/os_alias_remove.log) |
| `os_from_import_remove` | `from os import remove as custom_rm custom_rm('x')` | `Banned import of os.remove` | **KILLED** | [`log`](logs/os_from_import_remove.log) |
| `os_system` | `import os os.system('echo hi')` | `Banned call to os.system()` | **KILLED** | [`log`](logs/os_system.log) |
| `os_popen` | `import os os.popen('echo hi')` | `Banned call to os.popen()` | **KILLED** | [`log`](logs/os_popen.log) |
| `os_alias_system` | `import os as custom_os custom_os.system('echo hi')` | `Banned call to os.system()` | **KILLED** | [`log`](logs/os_alias_system.log) |
| `os_alias_popen` | `import os as custom_os custom_os.popen('echo hi')` | `Banned call to os.popen()` | **KILLED** | [`log`](logs/os_alias_popen.log) |
| `os_from_import_system` | `from os import system as sys_exec sys_exec('echo hi')` | `Banned import of os.system` | **KILLED** | [`log`](logs/os_from_import_system.log) |
| `os_from_import_popen` | `from os import popen as pipe_open pipe_open('echo hi')` | `Banned import of os.popen` | **KILLED** | [`log`](logs/os_from_import_popen.log) |
| `path_write_text` | `from pathlib import Path Path('x').write_text('content')` | `Banned Path write method 'write_text()'` | **KILLED** | [`log`](logs/path_write_text.log) |
| `path_write_bytes` | `from pathlib import Path Path('x').write_bytes(b'content')` | `Banned Path write method 'write_bytes()'` | **KILLED** | [`log`](logs/path_write_bytes.log) |
| `path_unlink` | `from pathlib import Path Path('x').unlink()` | `Banned Path write method 'unlink()'` | **KILLED** | [`log`](logs/path_unlink.log) |
| `path_mkdir` | `from pathlib import Path Path('x').mkdir()` | `Banned Path write method 'mkdir()'` | **KILLED** | [`log`](logs/path_mkdir.log) |
| `path_touch` | `from pathlib import Path Path('x').touch()` | `Banned Path write method 'touch()'` | **KILLED** | [`log`](logs/path_touch.log) |
| `path_rename` | `from pathlib import Path Path('x').rename('y')` | `Banned Path write method 'rename()'` | **KILLED** | [`log`](logs/path_rename.log) |
| `path_rmdir` | `from pathlib import Path Path('x').rmdir()` | `Banned Path write method 'rmdir()'` | **KILLED** | [`log`](logs/path_rmdir.log) |
| `path_instance_write` | `def f(p):     p.write_text('bad')` | `Banned Path write method 'write_text()'` | **KILLED** | [`log`](logs/path_instance_write.log) |
| `builtin_open_w` | `open('x', 'w')` | `Banned write mode 'w'` | **KILLED** | [`log`](logs/builtin_open_w.log) |
| `builtin_open_kw_w` | `open('x', mode='w')` | `Banned write mode 'w'` | **KILLED** | [`log`](logs/builtin_open_kw_w.log) |
| `builtin_open_a` | `open('x', 'a')` | `Banned write mode 'a'` | **KILLED** | [`log`](logs/builtin_open_a.log) |
| `builtin_open_x` | `open('x', 'x')` | `Banned write mode 'x'` | **KILLED** | [`log`](logs/builtin_open_x.log) |
| `builtin_open_r_plus` | `open('x', 'r+')` | `Banned write mode 'r+'` | **KILLED** | [`log`](logs/builtin_open_r_plus.log) |
| `builtin_open_unresolved` | `m = 'w' open('x', m)` | `Unresolved or non-literal mode` | **KILLED** | [`log`](logs/builtin_open_unresolved.log) |
| `io_open_w` | `import io io.open('x', 'w')` | `Banned write mode 'w'` | **KILLED** | [`log`](logs/io_open_w.log) |
| `builtins_open_w` | `import builtins builtins.open('probe.md', 'w')` | `Banned write mode 'w'` | **KILLED** | [`log`](logs/builtins_open_w.log) |
| `builtins_open_kw_w` | `import builtins builtins.open('probe.md', mode='w')` | `Banned write mode 'w'` | **KILLED** | [`log`](logs/builtins_open_kw_w.log) |
| `builtins_open_a` | `import builtins builtins.open('probe.md', 'a')` | `Banned write mode 'a'` | **KILLED** | [`log`](logs/builtins_open_a.log) |
| `builtins_open_x` | `import builtins builtins.open('probe.md', 'x')` | `Banned write mode 'x'` | **KILLED** | [`log`](logs/builtins_open_x.log) |
| `builtins_open_r_plus` | `import builtins builtins.open('probe.md', 'r+')` | `Banned write mode 'r+'` | **KILLED** | [`log`](logs/builtins_open_r_plus.log) |
| `builtins_open_unresolved` | `import builtins m = 'w' builtins.open('probe.md', m)` | `Unresolved or non-literal mode` | **KILLED** | [`log`](logs/builtins_open_unresolved.log) |
| `builtins_open_args_unresolved` | `import builtins builtins.open('probe.md', *args)` | `Unresolved or non-literal mode in open call (*args)` | **KILLED** | [`log`](logs/builtins_open_args_unresolved.log) |
| `builtins_open_kwargs_unresolved` | `import builtins builtins.open('probe.md', **kwargs)` | `Unresolved or non-literal mode in open call (**kwargs)` | **KILLED** | [`log`](logs/builtins_open_kwargs_unresolved.log) |
| `builtins_open_alias_module_w` | `import builtins as b b.open('probe.md', 'w')` | `Banned write mode 'w'` | **KILLED** | [`log`](logs/builtins_open_alias_module_w.log) |
| `io_open_kw_w` | `import io io.open('probe.md', mode='w')` | `Banned write mode 'w'` | **KILLED** | [`log`](logs/io_open_kw_w.log) |
| `io_open_alias_module_w` | `import io as my_io my_io.open('probe.md', 'w')` | `Banned write mode 'w'` | **KILLED** | [`log`](logs/io_open_alias_module_w.log) |
| `_io_open_w` | `import _io _io.open('probe.md', 'w')` | `Banned write mode 'w'` | **KILLED** | [`log`](logs/_io_open_w.log) |
| `_io_open_kw_w` | `import _io _io.open('probe.md', mode='w')` | `Banned write mode 'w'` | **KILLED** | [`log`](logs/_io_open_kw_w.log) |
| `_io_open_alias_module_w` | `import _io as raw_io raw_io.open('probe.md', 'w')` | `Banned write mode 'w'` | **KILLED** | [`log`](logs/_io_open_alias_module_w.log) |
| `_io_open_alias_func_w` | `from _io import open as raw_open raw_open('probe.md', 'w')` | `Banned write mode 'w'` | **KILLED** | [`log`](logs/_io_open_alias_func_w.log) |
| `path_class_open_w` | `from pathlib import Path Path.open(p, 'w')` | `Banned write mode 'w'` | **KILLED** | [`log`](logs/path_class_open_w.log) |
| `path_open_w` | `from pathlib import Path Path('x').open('w')` | `Banned write mode 'w'` | **KILLED** | [`log`](logs/path_open_w.log) |
| `path_open_kw_a` | `from pathlib import Path Path('x').open(mode='a')` | `Banned write mode 'a'` | **KILLED** | [`log`](logs/path_open_kw_a.log) |
| `path_open_unresolved` | `from pathlib import Path Path('x').open(some_mode)` | `Unresolved or non-literal mode` | **KILLED** | [`log`](logs/path_open_unresolved.log) |
| `bare_print` | `print('hello')` | `Banned bare print()` | **KILLED** | [`log`](logs/bare_print.log) |
| `sys_stdout_write` | `import sys sys.stdout.write('hello')` | `Banned direct sys.stdout.write()` | **KILLED** | [`log`](logs/sys_stdout_write.log) |
| `sys_stderr_write` | `import sys sys.stderr.write('hello')` | `Banned direct sys.stderr.write()` | **KILLED** | [`log`](logs/sys_stderr_write.log) |
| `from_sys_stdout_write` | `from sys import stdout stdout.write('hello')` | `Banned direct stdout.write()` | **KILLED** | [`log`](logs/from_sys_stdout_write.log) |
| `console_print` | `console.print('hello')` | `Banned Console.print()` | **KILLED** | [`log`](logs/console_print.log) |
| `io_open_alias_w` | `from io import open as reader reader('x', 'w')` | `Banned write mode 'w'` | **KILLED** | [`log`](logs/io_open_alias_w.log) |
| `builtins_open_alias_w` | `from builtins import open as reader reader('x', 'w')` | `Banned write mode 'w'` | **KILLED** | [`log`](logs/builtins_open_alias_w.log) |
| `builtins_print_alias` | `from builtins import print as output output('bad')` | `Banned bare print() call` | **KILLED** | [`log`](logs/builtins_print_alias.log) |
| `from_skill_lens_render` | `from skill_lens import render as renderer` | `Banned render import from 'skill_lens'` | **KILLED** | [`log`](logs/from_skill_lens_render.log) |
| `relative_render_import` | `from .. import render` | `Banned render relative import` | **KILLED** | [`log`](logs/relative_render_import.log) |
| `open_kwargs_unresolved` | `open('x', **options)` | `Unresolved or non-literal mode in open call` | **KILLED** | [`log`](logs/open_kwargs_unresolved.log) |
| `open_args_unresolved` | `open('x', *args)` | `Unresolved or non-literal mode in open call` | **KILLED** | [`log`](logs/open_args_unresolved.log) |
| `waiting_runner_quit_watchdog` | `def mutant_run(home, cwd, **kw):     code = tui.run(home, cwd, **kw)     worker_finished.wait()     return code` | `Watchdog fired before run() returned! Runner blocked waiting for worker completion.` | **KILLED** | [`log`](logs/waiting_runner_quit_watchdog.log) |
| `command_palette_screenshot_write_discriminator` | `class MutantApp(SkillLensApp):     ENABLE_COMMAND_PALETTE = True     save_screenshot = App.save_screenshot` | `Sentinel caught write attempt to screenshot file` | **KILLED** | [`log`](logs/command_palette_screenshot_write_discriminator.log) |
| `status_display_precedence_discriminator` | `class MutantController(SessionController):     @property     def status(self):         if self.failed: return 'error'         if self.retry_message is not None: return 'retry'...` | `Expected status 'retry' but mutant returned 'error'` | **KILLED** | [`log`](logs/status_display_precedence_discriminator.log) |

## Execution Summary

1. **Clean Control:** Every cycle verifies that benign code or real runner produces 0 violations.
2. **Strict Pattern Match:** Every mutation is detected by the AST guard or active watchdog timer with the exact expected failure or violation pattern.
3. **Clean Restoration:** Every cycle restores benign code/runner and confirms clean execution.
4. **Outcome Summary:** 73/73 killed (0 survivors).
