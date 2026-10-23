# Plan: accept the OpenCode 2.1.4 Mini footer shape

Status: Agreed
Authorization: Owner, 2026-10-23: “I authorize the rule-change phase for the OpenCode 2.1.4 footer. Plan and freeze it under the OMP planning loop, then implement offline: accept `<spinner> esc stop · <mode> · <model> [<effort>] · (OpenCode | <usage token>)` with the bottom-line anchor, blocked priority, and quoted/prefixed/embedded copies rejected. Fixtures must include varied usage-token shapes (not only `6.7K (3%)`) and negative cases using the new shape in quoted and prefixed forms. Normal final reviews. No deployment, no live trial, no changes to the installed Herdr.”
Reference: 738af8dd18c3b980b25d5da5bd47fcb81d37ad44
Surface: omp; Sol remains native in Tern; review/implementation workers use the authorized Herdr route.
Risk and review: High: changes lifecycle detection consumed by automation. Two fresh independent planning critics and two fresh final critics. Reuse the selected Gemini 3.8 Flash High / Plan and OpenCode DeepSeek V4.1 Flash Free / max / Plan pair; upstream identities remain unverified. No silent model substitution.
Roster: Coordinator requested/configured `openai-codex/gpt-6.1-sol`, thinking high. Implementer: `opencode/deepseek-v4.1-flash-free#max`, Build, reusing the owner's previously approved replacement implementer; edit-only, no checks or delegation. Diagnostic evidence is the captured OpenCode 2.1.4 footer; no live worker/trial is authorized.
Expected child tasks: two planning critics; one edit-only implementer; zero live-trial workers; two fresh final critics. A failed check does not authorize a live trial or installation.

## Outcome

The bundled Herdr 0.9.5 OpenCode detector recognizes the live OpenCode 2.1.4 Mini footer:

```text
🯦 esc stop · Plan · DeepSeek V4.1 Flash Free [max] · OpenCode
🯧 esc stop · Plan · DeepSeek V4.1 Flash Free [max] · 6.7K (3%)
```

It keeps the existing `... · account / provider` footer working, keeps blocked UI ahead of the busy footer, and still rejects quoted, prefixed, embedded or malformed copies. Proved offline only; no installed binary or live session changes.

## Current state and evidence

- Repository `main` at `f836559c0c46d00adbef5ed80135dcdf07a7ac95`. Preserve the modified historical `docs/validation/omp-coordinator/2026-10-20/herdr-dispatch.md`, untracked `.path` and untracked 2026-10-19 coordinator plan, unchanged and unstaged.
- [Footer capture](../validation/omp-coordinator/2026-10-23-herdr-mini-footer-capture/README.md) and [capture analysis](../validation/omp-coordinator/2026-10-23-herdr-mini-footer-capture/capture-analysis.json): OpenCode v2.1.4, SHA-256 `d8a65dd253dbea759ae0dd829792ff219b40178c7decffea822430a4d1ccadb3`; Herdr 0.9.5, SHA-256 `fb77c2232a05a8035421382c894392f4174e4e38a18e48af3dd0290157c3a7e2`.
- Captured active answer footer: `🯦/🯧 esc stop · Plan · DeepSeek V4.1 Flash Free [max] · OpenCode` (frames 0–75). Captured post-answer follow-up footer: `🯦/🯧 esc stop · Plan · DeepSeek V4.1 Flash Free [max] · 6.7K (3%)` (frames 76–93). Spinner glyphs observed: U+1FBE6 and U+1FBE7.
- Current accepted rule in both OpenCode manifests, version `2026.10.22.1`, priority 105, `bottom_non_empty_lines(1)`:
  `^(?:[\x{1CD00}-\x{1CEBF}\x{1FB00}-\x{1FBFF}]\s+)?esc stop · [^·/\n"'`“”‘’]+ · [^·/\n"'`“”‘’]+ · [^·/\n"'`“”‘’]+ / [\w.\-]+$`
  It requires a fourth field separated by ` / `; the live 2.1.4 footer has three fields and no slash.
- Accepted correction patch SHA-256 `f22d2d7edf26dd8e308394de143b015b37cf58f17148a45ca3c12889b8c6efe8`; pristine archive SHA-256 `5c745bf712aee3320ed88a665c39a9143cbd6b7ce4376e0ae0f0c07988576c13`; source commit `2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01`. The patch already includes the previous rule, tests and docs; this phase extends them.
- Prior offline evidence: 100 detector tests, 29 real-CLI cases, stale-cache proof, two fresh final passes. The temporary build/tools root was removed; this phase needs a fresh owned environment and the pinned Rust 1.96.1/Zig 0.16.0 toolchains.
- The live trial that exposed the mismatch failed with `agent_prompt_stalled` while the model completed. That failure is preserved and is design input, not evidence this new rule works live.

## Scope and boundaries

Allowed maintained source-copy paths, only inside a fresh owned temporary source directory:

- `src/detect/manifests/opencode.toml`
- `distribution/agent-detection/opencode.toml` (local release-consistency artifact; not an upstream publication)
- `src/detect/manifest/tests.rs`
- `docs/next/website/src/content/docs/agents.mdx` (unreleased guide wording)

No edits to `skill_lens/`, its tests, installed binaries/configs/skills, live caches/manifests, settings, services, credentials, or historical evidence. No deployment, live Mini trial, formal smoke, full-TUI trace, upstream PR or publication. No installation of the built binary. The distribution manifest remains a local-only artifact.

## Rule design

Keep one rule `status_footer_esc_stop_working`, priority 105, `bottom_non_empty_lines(1)`, `visible_working = true`, blocked priority 300 unchanged. The exact frozen `line_regex` is:

```toml
line_regex = ['''^(?:[\x{1CD00}-\x{1CEBF}\x{1FB00}-\x{1FBFF}]\s+)?esc stop · [^·/\n"'`“”‘’]+ · [^·/\n"'`“”‘’]+ · (?:[^·/\n"'`“”‘’]+ / [\w.\-]+|OpenCode|\d+(?:\.\d+)?[KM]? \((?:100|[1-9]?\d)%\))$''']
```

- `<mode>`/`<model>`: the existing nonempty field class `[^·/\n"'`“”‘’]+`, excluding `·`, `/`, newline, ASCII/smart quotes and backticks. The model may include spaces and `[max]`.
- `<account> / <provider>`: the existing branch `[^·/\n"'`“”‘’]+ / [\w.\-]+`, preserving the captured pre-2.1.4 footer. The literal ` / ` is required only in this branch.
- `OpenCode`: exact, case-sensitive provider token; not an arbitrary word.
- `<usage>`: `\d+(?:\.\d+)?[KM]? \((?:100|[1-9]?\d)%\)` — uppercase `K`/`M` only, integer percentage 0–100, one literal space before `(`. Examples: `6.7K (3%)`, `12K (4%)`, `1.2M (45%)`, `999 (2%)`, `1.0K (100%)`. `6.7K (300%)`, `6.7k (3%)`, `6.7K(3%)` and `6.7 K (3%)` do not match.
- Spinner leading range remains `[\x{1CD00}-\x{1CEBF}\x{1FB00}-\x{1FBFF}]`; only one optional spinner cell. The `🯦/🯧` shorthand in the captured facts means two separate observed frames, not two spinner cells on one line.
- The regex stays anchored at the bottom nonempty line, so quoted, prefixed, embedded and historical copies fail; a byte-identical unquoted bottom line remains indistinguishable by design.
- Do not add a second competing rule or change unrelated interrupt/progress rules.

## Implementation steps, after freeze and authorized implementation

1. Create a fresh owned directory with prefix `/tmp/skill-lens-herdr-opencode214-20261023-`; record it. Re-download and SHA-256-verify the official pinned Rust 1.96.1 and Zig 0.16.0 packages; unpack only under the owned prefix with isolated HOME/XDG/Cargo/Rustup/target/temp. No system install or persistent PATH/settings change.
2. Extract the pinned archive, apply the accepted patch unchanged, and verify the four accepted source hashes before editing.
3. Add the red-first regression through the real bundled loader: a captured 2.1.4 `OpenCode` footer must be `Working`; observe it fail before the rule edit. Positives must include:
   - captured `🯦/🯧 esc stop · Plan · DeepSeek V4.1 Flash Free [max] · OpenCode` (separate spinner frames);
   - usage tokens `6.7K (3%)`, `12K (4%)`, `1.2M (45%)`, `999 (2%)`, `1.0K (100%)`;
   - undecorated no-spinner positives for both final arms: `esc stop · Plan · DeepSeek V4.1 Flash Free [max] · OpenCode` and `... · 6.7K (3%)`;
   - the preserved old `Default / OpenCode` footer and its undecorated/relabelled forms.

   Negatives must be pinned per arm:
   - `OpenCode` arm: ASCII/smart/backtick quotes, `log:`/`▸` prefixes, embedded sentence, older footer above idle, trailing `OpenCode (copied)`, `OpenCode»`, lowercase `opencode`, uppercase `OPENCODE`, empty/missing final field.
   - usage arm: quoted ASCII/smart/backtick `6.7K (3%)`, `log: ...`/`▸ ...` prefixes, embedded sentence, trailing `6.7K (3%) copied`/`6.7K (3%)»`, lowercase `6.7k (3%)`, `6.7K (300%)`, `6.7K (101%)`, `6.7K (3)`, `6.7K(3%)`, `6.7 K (3%)`, missing/empty final field.
   - common: empty mode/model, incomplete one- or two-field footers, permission UI above the busy footer, ordinary transcript text and the known-agent no-match fallback. Use distinct meaningful fixtures, not duplicate rows.
4. Edit both manifests together to version `2026.10.23.1`, `updated_at = "2026-10-23T00:00:00Z"`, and the exact `line_regex` above. Confirm the new version is newer than the cached accepted version `2026.10.22.1` (or the preserved `2026.06.10.1`) with the existing comparator before relying on it.
5. Update the existing unreleased `agents.mdx` OpenCode Mini paragraph: describe the `OpenCode` and usage-token suffixes, the bottom-line anchor, the quoted/prefixed/embedded negatives, the byte-identical bottom-line limit, and the unresolved full-TUI completion defect. Do not claim request-bound completion or live validation.
6. Run the focused detector tests, Clippy with warnings denied, `cargo fmt --all -- --check`, and the real rebuilt CLI against the captured shapes plus the existing 29-case matrix in `docs/validation/omp-coordinator/2026-10-22-herdr-mini-detection-fix/final-cli-proof.json`. Add a real stale-cache check with cached `2026.10.22.1` (or preserved `2026.06.10.1`) under an isolated state tree; the new bundled `2026.10.23.1` must win. Preserve full outputs.
7. No installation or live trial. Preserve the patch, source hashes, test/CLI outputs, build provenance and complete reports; clean up owned workers/panes and the temporary root only after durable delivery.

## Acceptance and verification

- Captured `OpenCode` footer and each varied usage-token shape → `Working`; old `Default / OpenCode` footer still `Working`; undecorated positives for both final arms work; `100%` is accepted.
- Quoted, prefixed, embedded, historical-above-idle, trailing-suffix, malformed-usage and incomplete-field copies → `Idle`; lowercase/uppercase `opencode`, lowercase `6.7k (3%)`, `101%` and `300%` are rejected; permission UI above the busy footer → `Blocked`; existing interrupt/progress hints and known-agent no-match fallback unchanged.
- Real bundled loader and real rebuilt CLI select manifest `2026.10.23.1` and match the expected state; the stale-cache check selects bundled `2026.10.23.1` over cached `2026.10.22.1` (or preserved `2026.06.10.1`).
- Both manifests parse/validate and keep blocked priority 300 ahead of 105. The two manifest copies remain consistent as a local release artifact; do not add a permanent copied-file parity test.
- Skill Lens gates: `uv run pytest --cov=skill_lens`, `uv run mypy`, `uv run ruff check .`, `uv run ruff format --check .`; reuse prior evidence only if product/test/checker inputs remain unchanged.
- Two fresh final reviews on the same frozen evidence; all in-scope blockers resolved. No deployment, live trial, formal smoke or publication. Freeze in two commits: the first plan-only, the second reference-only; implement only after the frozen reference is verified.
- Deployment, live trial and formal smoke each require separate later approval.

## Review decisions

Round 1 planning reviews ran against draft SHA-256 `2a133cc756cea79f5a26db5549f3a023a0428263a562b4b4c651a6b3511f7a2d`.

- **Gemini 3.8 Flash High / Plan**, session `ed4f8a35-8f73-4a5b-88e9-58db1d497961`: **changes_required**. Blocker: `\d{1,3}%` accepted `6.7K (300%)`, contradicting the required Idle negative. Suggestion: include the exact assembled regex.
- **OpenCode DeepSeek V4.1 Flash Free / max / Plan**, session `ses_e972129baffeEB5TBq1Dpdk3UQ`: **changes_required**. Blockers: the same percentage contradiction; the rule design was schematic rather than a literal regex; no undecorated positives for the new suffix arms; negatives were not pinned per alternation arm. Suggestions: lowercase/uppercase token negatives; uppercase-only K/M and integer-percent assumptions; disambiguate the spinner shorthand; pin the stale-cache fixture and 29-case matrix; use “two-commit freeze” wording.
- No reviewer wrote to the checkout.

Corrections accepted:

1. Usage grammar is now `\d+(?:\.\d+)?[KM]? \((?:100|[1-9]?\d)%\)` — uppercase K/M, integer 0–100; `300%`, `101%`, `6.7k`, `6.7K(3%)` and `6.7 K (3%)` are negatives, while `1.0K (100%)` is a positive.
2. The exact `line_regex` is embedded in the plan; the implementer does not reconstruct grouping.
3. Positives now include undecorated `OpenCode` and usage-arm footers, both spinner frames, `100%`, and the preserved old branch.
4. Negatives are pinned per arm, including quoted/prefixed/embedded/trailing usage copies, lowercase/uppercase provider tokens, and empty/missing final fields.
5. Stale-cache fixture is pinned to `2026.10.22.1` (or `2026.06.10.1`); the CLI matrix is named; “two-commit freeze (plan, then reference)” wording is used.
6. The spinner shorthand is clarified as separate captured frames, not two cells.

Round 2 targeted confirmation ran against corrected draft SHA-256 `a0dea535936fae5a6c1d5b152542495d276f90eb66c4deae08f5fd218954ad57`:

- **Gemini**, session `ed4f8a35-8f73-4a5b-88e9-58db1d497961`: **pass**, no blockers; all six corrections verified.
- **OpenCode**, session `ses_e972129baffeEB5TBq1Dpdk3UQ`: **pass**, no blockers; all prior blockers verified resolved and no new blocker found.
- No reviewer wrote to the checkout. Both critics conceded the byte-identical bottom-line limit, offline-only proof, no live trial/deployment/installation, and unverified upstream identities.

Status is now Agreed. Freeze this plan in two commits (plan-only, then reference-only), verify the exact reference, and implement offline under the owner's 2026-10-23 authorization. No deployment, live trial or installed-binary change.
