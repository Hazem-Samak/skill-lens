# U9 implementation self-review

Date: 5 November 2026. Scope: everything in this implementation directory plus the
ten changed tracked files. This is implementer quality control, not the
coordinator's independent review.

## What was re-checked before handoff

- The complete `git diff` (ten files) was read end to end; no production module
  outside `skill_lens/__init__.py` changed, and that change is the version string.
- Every acceptance item in the matrix was re-run against the final artifacts after
  the last correction, not against an earlier build.
- `git status --porcelain` shows exactly the ten allowed tracked files plus this
  untracked evidence directory; the 804 pre-existing untracked paths are
  unchanged (path set identical to the planning baseline, `inputs.json`).
- No snapshot or golden was regenerated (`git status tests/fixtures` is empty).
- The installed candidate was driven through a real pseudo-terminal at both sizes
  after the final build, not against an editable checkout.

## Problems found during self-review, and what changed

1. **The installed-lane receipt silently reported zero tests.** pytest's summary
   line now carries an elapsed parenthetical (`461 passed in 88.41s (0:01:24)`),
   which the old pattern rejected; the code then fell back to
   `test_count: 0, skip_count: 0` and nothing failed. The first full harness run
   therefore "passed" while describing an empty lane. Fixed by a strict parser
   (`parse_pytest_summary`) that raises on an unknown summary, a positive-count
   guard, and receipt fields `pytest_summary` and `elapsed_seconds`. Covered by
   four new tests and three mutations (`receipt-*`). Re-run: 461 passed in both
   lanes, recorded in `install-receipt.json`.
2. **The completeness guard compared mismatched orderings.** The first version
   compared the sorted on-disk module list with the manifest in its declared
   order and failed spuriously. It now compares sorted sequences; declaration
   order stays pinned by the equality guard.
3. **The completeness guard assumed a source tree.** It read
   `REPO_ROOT/skill_lens/tui`, which does not exist in the installed test lane
   where `tests/test_tui_packaging.py` also runs. It now resolves the directory
   from the imported `skill_lens` package, so it checks the shipped modules in
   both contexts. A rehearsal wheel install confirmed the whole packaging test
   file passes inside a lane before the long harness run.
4. **The terminal driver lost the restore evidence.** Draining the pseudo-terminal
   only after `wait()` returns EIO on macOS once the slave closes, so
   `?1049l`/`?25h` were never seen and the check reported a false restore failure.
   The driver now drains while the process is still alive; all four scenarios
   report `exit=0`, `alt_screen_left=true`, `cursor_shown=true`.
5. **Terminal markers were not actually visible at both sizes.** The Agents table
   truncates display names at 100 columns (`OpenA`) and the 60×24 layout clips the
   detail pane's lower lines. Markers were replaced with text visible at both
   sizes, and navigation now waits for `Ready:` before pressing `g` (an early key
   press was swallowed while the initial capture was still running). This is an
   evidence-quality correction, not a product change; the clipping itself is
   pre-existing U6 layout behaviour outside U9 scope.
6. **The base-lane wording in `DEVELOPMENT.md` was wrong.** It said the base lane
   prints help *plus the install tip*; the harness asserts the opposite for a
   non-interactive bare run, and the tip path needs an interactive terminal.
   Corrected, and a PTY probe now covers the interactive bare + missing-extra
   case (`base_bare_interactive_prints_tip`).
7. **The build root matters more than expected.** Hatchling's default sdist
   packages the whole working directory: a rehearsal build from the live checkout
   embedded all 804 pre-existing untracked files plus this evidence directory.
   The candidate is therefore built only from a clean `git archive` export with
   `docs/validation/u9/` removed and exactly the ten reviewed files overlaid;
   `DEVELOPMENT.md` now warns about this explicitly.
8. **The terminal receipt's provenance line named the checkout, not the lane.**
   The first version probe ran the lane's Python with the repository as its
   working directory, so `python -c` put the checkout on `sys.path` and imported
   `skill_lens` from the source tree. The version numbers happened to match, which
   is exactly why this needed catching: the receipt claimed provenance it had not
   proven. Every probe, fallback and driven app now runs with an explicit working
   directory outside the checkout, and `terminal-receipt.json` records
   `skill_lens_file` inside the lane's `site-packages` plus `driver_cwd`.
9. **`uvx twine` and PTY access needed environment fixes, not code fixes.**
   `uvx` tried to install into `~/.local/share/uv/tools`, outside the writable
   area, so the build script pins `UV_TOOL_DIR`/`UV_TOOL_BIN_DIR` under its
   scratch directory. Pseudo-terminal creation was initially blocked by the
   session's sandbox; after the session's file policy changed, the terminal check
   ran unchanged. Both are environment notes, not product changes.

## Deliberate limitations of this evidence

- Wheel bytes are not bit-reproducible: hatchling records source mtimes from the
  freshly created export, so a rebuild changes the ZIP and its SHA-256 with
  identical content. Content identity is verified per file against the export
  instead (`packaged_python_matches_export`). The final wheel hash is the one in
  `candidate.json`, `install-receipt.json` and `terminal-receipt.json`.
- The minimum and unconstrained-latest Textual endpoints both resolve 8.2.8
  because 8.2.8 is today's latest stable release. That is disclosed rather than
  presented as two-version coverage.
- Automated terminal driving proves the screens render, react and restore; it is
  not human visual approval.
