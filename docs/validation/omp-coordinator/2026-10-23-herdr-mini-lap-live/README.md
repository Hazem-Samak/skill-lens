# Isolated Mini lap — live proof of manifest 2026.10.23.1

Result: **pass**. The corrected OpenCode 2.1.4 footer rule was deployed as a
local manifest override in a fresh isolated Herdr 0.9.5 session. The one small
read-only Mini task produced a matching complete answer and a finished session.
The normal Herdr session, shared OpenCode service, installed binary and user
configuration were not changed.

## Deployment and rollback

- Manifest: `2026.10.23.1`, SHA-256
  `d86463927f13191fb8123a6fe0efe3435e9e4832a9c7cd6123ee7bfe02857104`.
- Override: `<owned-root>/hc/herdr/agent-detection/opencode.toml`.
- Active source reported by Herdr: that local override; `active_version`
  `2026.10.23.1`.
- Rollback: stop the isolated `lap` server and delete the owned temporary root.
  No normal config/state was written; the installed binary was only executed.
- No install, no service restart, no normal-session change.

## Live trial

- OpenCode v2.1.4, SHA-256 `d8a65dd253dbea759ae0dd829792ff219b40178c7decffea822430a4d1ccadb3`.
- Herdr 0.9.5, SHA-256 `fb77c2232a05a8035421382c894392f4174e4e38a18e48af3dd0290157c3a7e2`.
- Model: `opencode/deepseek-v4.1-flash-free`, variant `max`, Plan.
- One user prompt; a 180-word read-only answer (1,005 bytes), `finish: stop`,
  session `succeeded`, one user message, no active or child work.
- Pre-prompt state: `idle`, no matched rule, manifest `2026.10.23.1`.
- During generation: Herdr `working`, matched
  `status_footer_esc_stop_working`; footer
  `🯦 esc stop · Plan · DeepSeek V4.1 Flash Free [max] · OpenCode`.
- Usage-token footer also appeared and matched `working`:
  `🯦 esc stop · Plan · DeepSeek V4.1 Flash Free [max] · 6.2K (3%)`.
- After completion: `idle`, no matched rule; the idle frame has no stop control.
- `agent prompt --wait` exited 0 with `idle`; no early `done` was observed.
  Completion was accepted from the complete BEGIN/END answer and finished
  native session, not from a premature settled state.
- Wait returned about 3.892 s after native completion (pass margin 322.21 ms);
  no resend.

A second assistant record is the post-answer Plan-mode system-reminder follow-up,
not a second user prompt.

## Evidence

- `deployment.json`, `agent-manifests.json` — isolated override identity and
  active version.
- `pre-prompt.json`, `live-observe.json`, `live-result.json`, `native.json`,
  `clock.json`, `live-frames.jsonl` — timestamps, observed states, native
  messages, completion and frame sequence.
- `working-frame.txt`, `usage-frame.txt`, `idle-after-frame.txt` — key screens.
- `prompt-wait.stdout.txt`, `prompt-wait.stderr.txt` — bounded wait result.
- `manifest.json` / `manifest.sha256` — canonical evidence hashes.

No credentials, private-server password, raw terminal transcript or normal-user
data is included. Formal smoke, full-TUI instrumentation/trace, upstream
publication and other changes were not performed.
