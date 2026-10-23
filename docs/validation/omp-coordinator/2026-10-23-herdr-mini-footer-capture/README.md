# OpenCode 2.1.4 Mini footer capture

One isolated capture generation, authorized 2026-10-23. No rule change, code change,
installation, second generation, shared-service use or credential copy.

## Pinned runtimes

- OpenCode `v2.1.4`, SHA-256 `d8a65dd253dbea759ae0dd829792ff219b40178c7decffea822430a4d1ccadb3`
- Herdr `0.9.5`, SHA-256 `fb77c2232a05a8035421382c894392f4174e4e38a18e48af3dd0290157c3a7e2`

## Observed footer shapes

Idle before generation (no stop control):

```text
Plan · DeepSeek V4.1 Flash Free [max] · OpenCode · ctrl+p menu
```

Active during the answer (frames 0–75):

```text
🯦 esc stop · Plan · DeepSeek V4.1 Flash Free [max] · OpenCode
🯧 esc stop · Plan · DeepSeek V4.1 Flash Free [max] · OpenCode
```

Active during the post-answer Plan-mode follow-up (frames 76–93):

```text
🯦 esc stop · Plan · DeepSeek V4.1 Flash Free [max] · 6.7K (3%)
🯧 esc stop · Plan · DeepSeek V4.1 Flash Free [max] · 6.7K (3%)
```

Observed spinner glyphs: `🯦` (U+1FBE6), `🯧` (U+1FBE7).

## Why the offline rule did not match

The accepted offline rule requires three metadata fields followed by
` / <provider>`. The live 2.1.4 footer has no ` / ` separator: it ends in
`· OpenCode` during the answer and in `· 6.7K (3%)` during the follow-up.
The third field therefore cannot satisfy the rule's provider shape.

## Generation facts

- One user prompt; one complete answer (`BEGIN`/`END`, 2,459 bytes).
- The answer completed at `2026-10-23T12:57:21.746Z`; active frames 0–75.
- A post-answer system reminder triggered a second assistant record (374 bytes,
  "Plan mode is active…"), active frames 76–93. This is not a second prompt.
- 152 visible-screen frames were captured at roughly 7 fps from 22 seconds of
  sampling; frames 94–151 are post-completion/idle.

## Files

- `frames/frames.jsonl` — every frame with UTC and monotonic timestamps.
- `key-frames/` — idle, first active, both spinner glyphs, usage footer,
  answer-completion, follow-up-completion and final frames.
- `capture-analysis.json` — footer shapes, frame ranges, native completion times,
  version pins and the rule mismatch.
- `receipts/` — submission, native session/messages, answer text, the extra
  assistant text and the system reminder.
- `manifest.json` / `manifest.sha256` — canonical evidence hashes.

No credential, raw terminal transcript, provider password or normal-user data is
included. The ephemeral private-server password stayed in the owned temporary
launcher and was removed with that root.
