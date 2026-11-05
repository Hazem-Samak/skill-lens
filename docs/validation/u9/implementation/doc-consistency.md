# U9 document-consistency check

The plan requires the five status documents to agree and to keep four different
states apart: **published 0.1.1**, the **locally prepared 0.2.0 candidate**,
**automated checks**, and **human visual approval / publication**. This table is
the check; it was read back from the final working tree on 5 November 2026.

| Claim | `README.md` | `DEVELOPMENT.md` | `CHANGELOG.md` | `FULL_SCREEN_TUI.md` | `SKILL_LENS_SPECIFICATION.md` |
| --- | --- | --- | --- | --- | --- |
| Published PyPI release is 0.1.1 and has no TUI or `[tui]` extra | "Published (PyPI `skill-lens-cli` 0.1.1) … no TUI extra" | Phase 7 header: "Not published: PyPI still serves 0.1.1" | 0.2.0 entry: "published release is still `0.1.1`" | Header: "published PyPI 0.1.1 contains no TUI package and no `[tui]` extra" | Phase 7: "Published PyPI 0.1.1 contains no TUI" |
| 0.2.0 exists only as a locally prepared, unpublished candidate | "0.2.0 release candidate (prepared locally, not published)" | "prepared, not published"; candidate qualification section | "`[0.2.0]` … **Prepared locally, not published**" | "U9 prepared the 0.2.0 release candidate locally" | "unpublished candidate" |
| Versions/lock synchronized at 0.2.0 | "Versions … are synchronized at 0.2.0" | Checklist item 2 | Entry records the candidate's contents | Step 9 status: "versions, `uv.lock` … synchronized at 0.2.0" | "0.2.0 is synchronized across `pyproject.toml`, `__version__` and the `uv.lock` root package" |
| Artifacts built from a clean export and checked | "a wheel and a source archive were built from a clean export" | "always build the export, never the live checkout" | "built from a clean export of the reviewed sources … `twine check` metadata PASS" | "built from a clean source export and passed `twine check`" | "built from a clean export of the reviewed sources" |
| Three fresh installations (base / min / latest) | "reinstalled into three fresh environments" | Checklist item 5 | "three fresh installations outside the checkout" | "base, minimum-Textual and latest-Textual installations passed outside the checkout" | "qualified in fresh base, `textual==8.2.8` and unconstrained-latest installations" |
| Automated terminal smoke, not human approval | "Three things are **not** claimed: human visual approval, hosted CI …, publication" | "human visual approval plus hosted CI … still outstanding" | "**Not claimed:** human visual approval, hosted CI …, publication" | "human visual approval plus candidate-specific hosted CI are outstanding" | "no upload, tag, hosted-CI claim or human visual approval exists for 0.2.0" |
| No publication/tag/date claimed | "do not install released `skill-lens-cli[tui]`" | "Neither an upload nor a tag is authorized by this checklist" | "no tag link … while `v0.2.0` does not exist" | "unpublished candidate" | "Publishing remains separate work" |
| CI evidence attributed to its own commit | "U8's earlier green CI run … prove their own commits, not this candidate" | Phase 7 keeps U8's run attributed to U8 | Verification list separates candidate checks from earlier runs | "candidate-specific hosted CI" listed as outstanding | "hosted-CI claim … does not exist for 0.2.0" |

No document advertises `pip install 'skill-lens-cli[tui]'` as an available PyPI
TUI; `README.md` states explicitly that it cannot work until 0.2.0 is published
and gives a clone-and-build route for the candidate instead. `README.md` links
remain absolute URLs (`test_phase5_gate.py::test_readme_has_no_relative_links`
passes).

## Historical records left alone

- `docs/archive/PHASE5_WALKTHROUGH.md` and the Phase 5 release checklist keep
  their 0.1.0/0.1.1 examples; the plan defers rewriting them to a later,
  authorized publication mission.
- U1–U8 validation records are untouched, including their dated gate numbers.
- The U9 planning receipts under `docs/validation/u9/planning/` are unchanged and
  are excluded from the build export.
