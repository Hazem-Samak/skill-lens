# OpenCode 2.1.4 footer rule — offline implementation

Offline-only change for Herdr 0.9.5. No deployment, live Mini trial, formal smoke,
full-TUI trace or installed-binary change.

## Change

Both OpenCode manifests now use `version = "2026.10.23.1"` and the same
`status_footer_esc_stop_working` regex:

```toml
line_regex = ['''^(?:[\x{1CD00}-\x{1CEBF}\x{1FB00}-\x{1FBFF}]\s+)?esc stop · [^·/\n"'`“”‘’]+ · [^·/\n"'`“”‘’]+ · (?:[^·/\n"'`“”‘’]+ / [\w.\-]+|OpenCode|\d+(?:\.\d+)?[KM]? \((?:100|[1-9]?\d)%\))$''']
```

It accepts the captured live shape ending in `· OpenCode` or a usage token such as
`· 6.7K (3%)`, preserves the older `account / provider` shape, and keeps blocked
priority 300 ahead of this rule at priority 105. The region remains
`bottom_non_empty_lines(1)`.

## Result

- Red test first: `0 passed; 1 failed`, actual `Idle` vs expected `Working`.
- Focused tests: `2 passed; 0 failed`.
- Full detector filter: `102 passed; 0 failed`, 3,546 filtered.
- Clippy with `-D warnings`: passed. `cargo fmt --all -- --check`: passed.
- Real rebuilt CLI: `55/55` (29 preserved cases plus 26 new 2.1.4 cases).
- Stale cache: bundled `2026.10.23.1` selected over cached `2026.10.22.1` and
  `2026.06.10.1`.
- Only the four authorized source-copy paths changed; both manifest copies are
  byte-identical.
- Skill Lens health gates reused because no product/test/checker input changed.

## Files

- `correction-214.patch` — applies to the accepted 2026.10.22.1 source copy.
- `verification.json` — red/green, test, CLI, cache and toolchain receipt.
- `cli-matrix.json`, `stale-cache.json`, `checks.json`, `build.json`.
- `implementer-*-brief.txt`, `implementer-report.txt` — edit-only worker record.
- `worktree-check.json` — only the four allowed paths changed.
- `manifest.json` / `manifest.sha256` — canonical evidence hashes.

The implementer is OpenCode 2.1.4 `opencode/deepseek-v4.1-flash-free`, variant
`max`, Build; upstream identity unverified. Temporary Rust 1.96.1/Zig 0.16.0
toolchains were official, checksum-verified and confined to the owned root.
