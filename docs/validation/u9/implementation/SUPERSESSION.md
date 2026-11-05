# Supersession note — first-wave (r1) receipts in this folder

**Read this before using any hash in this folder.** These r1 receipts are
retained unmodified as historical evidence of the implementer's first build,
but their **source-archive hash no longer describes the shipped 0.2.0**:
`CHANGELOG.md` and `DEVELOPMENT.md` are packaged inside the source archive, and
coordinator review corrections changed them twice after r1, with the release
wording (including README, which also rides inside the wheel's metadata)
changing in the final publication wave.

| Wave | Why it ran | Wheel SHA-256 | Sdist SHA-256 | Receipts |
| --- | --- | --- | --- | --- |
| r1 | implementer's original build | `91f6c55329d19b14a5bd9e1a1a7aa1f194d09d17d09dab7b4dc8ffc366c4e107` | `53263ddeb55935874c1efdbe6f28c5efbce8ba7f557aab3bff3fd2ef18430233` (invalidated) | this folder |
| r2 | after coordinator corrections C-F1…C-F5 | `91f6c55329d19b14a5bd9e1a1a7aa1f194d09d17d09dab7b4dc8ffc366c4e107` (byte-identical: the corrected docs are not wheel content) | `92c81c3d4000b8d19651f1c283ee54897e057ce288700e9d7011ea493e38702a` (invalidated) | `docs/validation/u9/coordinator/precommit/*-r2.*` |
| r3 | after review-closure corrections C-F7, C-S1…C-S4 (README in wheel metadata changed → wheel differs from r1/r2) | `9be079b70933f160d334e6806e906fb600ef4e9a735bd5a2d149ed5ea3e4eba7` (invalidated) | `890f91e200256586fb9b32bc229dff5f852ec087d3abf829405078532a812f48` (invalidated) | `docs/validation/u9/coordinator/precommit/*-r3.*` |
| **r4 (PUBLISHED 0.2.0)** | release wording finalized in all five status documents (2026-11-05) | `8c7e5f64d3b08f518c641e249d4219cfc6328ebcaa4fc5392e4289de55970661` | `de5687239d5692cdee466fba9558ec1a868eb901ca76c87cc2a81d1b787f2d6c` | `docs/validation/u9/coordinator/precommit/*-r4.*` |

The artifacts uploaded to PyPI are the **r4 wave**, retained at
`/tmp/u9-candidate-r4/artifacts/` with lane environments under
`/tmp/u9-candidate-r4/smoke/`. Every wave passed the same 16/16 archive
checks, three fresh installations (461 tests / 0 skips on both TUI lanes),
per-lane version probes and the installed terminal smoke. Nothing in this
folder was edited or deleted; this note and the coordinator ledgers are purely
additive.
