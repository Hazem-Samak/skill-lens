# Supersession note — first-wave (r1) receipts in this folder

**Read this before using any hash in this folder.** These r1 receipts are
retained unmodified as historical evidence of the implementer's first build,
but their **source-archive hash no longer describes the current candidate**:
`CHANGELOG.md` and `DEVELOPMENT.md` are packaged inside the source archive, and
coordinator review corrections changed them twice after r1.

| Wave | Why it ran | Wheel SHA-256 | Sdist SHA-256 | Receipts |
| --- | --- | --- | --- | --- |
| r1 | implementer's original build | `91f6c55329d19b14a5bd9e1a1a7aa1f194d09d17d09dab7b4dc8ffc366c4e107` | `53263ddeb55935874c1efdbe6f28c5efbce8ba7f557aab3bff3fd2ef18430233` (invalidated) | this folder |
| r2 | after coordinator corrections C-F1…C-F5 | `91f6c55329d19b14a5bd9e1a1a7aa1f194d09d17d09dab7b4dc8ffc366c4e107` (byte-identical: the corrected docs are not wheel content) | `92c81c3d4000b8d19651f1c283ee54897e057ce288700e9d7011ea493e38702a` (invalidated) | `docs/validation/u9/coordinator/precommit/*-r2.*` |
| **r3 (current)** | after review-closure corrections C-F7, C-S1…C-S4 (README and four other packaged docs changed → wheel metadata changed too) | `9be079b70933f160d334e6806e906fb600ef4e9a735bd5a2d149ed5ea3e4eba7` | `890f91e200256586fb9b32bc229dff5f852ec087d3abf829405078532a812f48` | `docs/validation/u9/coordinator/precommit/*-r3.*` |

The current qualified candidate is the **r3 wave**; its artifacts are retained
at `/tmp/u9-candidate-r3/artifacts/` and its lane environments under
`/tmp/u9-candidate-r3/smoke/`. Every wave passed the same 16/16 archive
checks, three fresh installations (461 tests / 0 skips on both TUI lanes),
per-lane version probes and the installed terminal smoke. Nothing in this
folder was edited or deleted; this note and the coordinator ledgers are purely
additive.
