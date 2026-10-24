# Overnight closure — evidence

Date: 2026-10-24/25. Branch: `fix/overnight-closure-20261024`. Plan:
[2026-10-24-overnight-closure.md](../../../plans/2026-10-24-overnight-closure.md).

This folder holds the reviewable record for the overnight work. The morning
report is [REPORT.md](REPORT.md).

## Contents

- `deployment.json`, `fixtures/` — manifest `2026.10.23.1` installed as a
  local override in the everyday Herdr, with the verification frames and
  rollback. No installed binary, remote manifest or upstream publication was
  changed.
- `ci/` — CI diagnosis and run receipts.
- `trace/` — full-TUI capture attempt and its classification.
- `smoke/` — bounded end-to-end worker dispatch result.

## Deployment in one paragraph

The accepted manifests were rebuilt from the pinned Herdr v0.9.5 archive by
applying the two accepted patches unchanged; the final manifest digest matched
the lap proof (`d8646392…`). It was installed at
`~/.config/herdr/agent-detection/opencode.toml` (no override existed before),
then the running `default` server was told to reload agent manifests through
the official `server.reload_agent_manifests` socket method. The server now
reports `source_kind: local override`, `active_version: 2026.10.23.1`; the
remote `2026.06.10.1` file is untouched and shadowed. Captured busy frames
classify as `working`; the finished frame and quoted/prefixed copies classify
as `idle`. Rollback is deleting that one file and reloading.
