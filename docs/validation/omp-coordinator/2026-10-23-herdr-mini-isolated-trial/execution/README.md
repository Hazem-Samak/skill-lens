# Isolated Mini live trial — failure record

Result: **failure**. The single live Mini attempt returned `agent_prompt_stalled`; the bounded observer timed out; Herdr evaluated the screen as `idle` with no matched rule. The model itself generated a complete, substantive answer in about 9.8 seconds.

This is a missed-busy observation, not an early completion. The accepted offline footer rule did not classify the live OpenCode 2.1.4 Mini screen as working. The active footer shape was not captured during generation, so the next correction cannot be selected from this evidence without a separately authorized diagnostic capture.

No resend, code change, installation, full-TUI trace, formal smoke or publication occurred. The normal Herdr session, shared OpenCode service, installed binaries and the three pre-existing user files are unchanged.

## Evidence map

- `live-trial-result.json` — consolidated failure, timing and native metadata.
- `live-trial-observe.json` — prompt wait, observer, screen state and detection readback.
- `live-trial-native.json` — native session, messages, active and child-session checks.
- `assistant-text.txt` — the model's complete answer.
- `prompt-wait.stderr.txt` — exact `agent_prompt_stalled` error.
- `prompt-wait.stdout.txt` — empty prompt-wait output.
- `pre-prompt-final.json` / `pre-prompt-session.json` — Mini footer, Herdr idle, zero messages and the discarded setup session.
- `agent-readiness.json` — pre-prompt Herdr readiness.
- `clock-bracket.json` — UTC/monotonic bracket and offset.
- `preflight.json` — credential-free model and `max` variant proof.
- `toolchain-downloads.json`, `source-patch.json`, `build.json`, `checks.json`, `cli-matrix.json` — pinned build and offline checks.
- `herdr-server-start.json`, `herdr-panes.json` — isolated session/socket/pane identity.
- `private-opencode.json` — private backend/session metadata; password retained only in the owned temporary launcher, never copied here.
- `cleanup.json` — owned process/server stop evidence.
- `environment.json` — normal environment and binary/user-file preservation.

The canonical evidence manifest and its SHA-256 are in `manifest.json` and `manifest.sha256`. The manifest excludes itself and hashes the sorted relative paths above. Raw transcripts, provider credentials and the ephemeral private-server password are not included.
