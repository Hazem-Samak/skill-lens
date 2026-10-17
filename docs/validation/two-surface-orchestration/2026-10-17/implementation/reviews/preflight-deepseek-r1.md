I have enough verified evidence. Let me do one final check on the grep to confirm which file says 184 files and confirm no pilot was run, then compose the report.

I now have all facts confirmed. Summary of verification:

- **A**: `herdr agent start --help` lists 24 kinds; mcode/minimax absent — CONFIRMED. But the reviewer context (T3 selected pair) differs from Herdr role pool; no permanent roster amendment needed.
- **B**: cmux at `/Applications/cmux.app/...` not in PATH — CONFIRMED (evidence says so honestly).
- **C**: `agent start` "must be at its interactive shell prompt" + "detected in the same terminal"; `agent prompt` targets agent by name from any shell — startup places Hermes in the pane and then needs a *separate* control shell; NOT clearly stated.
- **D**: `--tools` "Keeps MCP tools unless an entry starts with mcp__" — CONFIRMED overclaim; `--no-extensions` also noted.
- **E**: `--ignore-rules` skips AGENTS/SOUL; `--in` = cwd change; agy `--add-dir`/`--project` = context selection — CONFIRMED, "strictly confined" overclaimed.
- **F**: `/tmp/skill-lens-synthetic-fixture/checkout` does not exist (setup.md §6/§7 mismatch) — CONFIRMED.
- **G**: bare `https://github.com` URLs; baseline+tmp logs say 187, docs say 184 — CONFIRMED.
- **H**: P01–P09 all PENDING — CONFIRMED.

---

**EFFECTIVE_MODEL**: Pi/WorkBuddy DeepSeek (`workbuddy/deepseek-v4.1-flash` via `pi` instance), thinking=high, read-only critic tools (`read,grep,find,ls`) per task. Configured selection only; upstream family identity is self-reported and, per the frozen plan, never usable as upstream execution proof (the plan already flags DeepSeek's proposal-round self-mislabel as MiniMax). Treat identity as configured, not upstream-verified.

**VERDICT**: **Conditional pass — accurate, correctly-scoped preflight evidence, with concrete factual corrections required before it can stand as a truthful handoff.** The dispatch stayed read-only: 4 allowed evidence files created, no product/process/frozen-plan/`.path` edits, no pilot executed, all machine probes non-mutating. The setup proposal is correctly scoped and its architecture (human-owned startup, no out-of-Herdr control, blocked MiniMax kind, pending pilot) is honest in structure. However, several concrete claims are inaccurate or overclaimed and must be corrected. This is NOT a runtime/trial-ready approval.

**BLOCKERS** (must fix; all are evidence-accuracy corrections, not new work):

1. **Formatting count is wrong and contradicts the retained log.** `preflight.md:40`, `setup.md` and `preflight-receipt.json:baselineGates.ruffFormat.filesFormatted` say **184**, but both `implementation/baseline/ruff-format.log` and the coordinator's `/tmp/.../ruff-format.log` say **`187 files already formatted`** (verified). The `184` traces to an older planning-round log (`planning/ruff-format.log`). Correct all three to **187**.

2. **Two different synthetic-checkout paths; the startup path does not exist.** `setup.md` §6 Step 3 uses `/tmp/skill-lens-synthetic-fixture/checkout` (verified absent), while §7 and `preflight.md` §7 use `/tmp/skill-lens-herdr-execution-20261017-cg7iv351/synthetic-checkout`. A placeholder/nonexistent checkout must not be presented as a runnable prepared handoff. Pick one canonical path, state it is created at pilot time, and reconcile §6↔§7.

3. **Pi "read-only tools enforced" is overclaimed.** `pi --help` states `--tools` "Keeps MCP tools unless an entry starts with mcp__". So `--tools read,grep,find,ls` does **not** enforce read-only (MCP/extension tools remain). `setup.md:80` and `preflight.md` §5 item 3 must state the residual MCP/extension surface, or add `--no-mcp`/`--no-extensions` with explicit retained `-e` if Herdr integration requires it. Separately, `--no-extensions` suppresses built-in extensions; confirm whether Herdr integration depends on one and, if so, retain it via explicit `-e` (per `pi --help`).

4. **"Strictly confined" isolation claim is not supported by installed help.** `hermes --ignore-rules` skips AGENTS.md/SOUL.md/memory/preloaded-skill injection, and `--in DIR` "Change into DIR" is a cwd selection, not a filesystem sandbox; agy `--add-dir` "Add a directory to the workspace" and `--project` select project context, not a proven path jail. Rewrite `setup.md`/`preflight.md` §7 to claim only what is proven: context/auth separation and fixture-scoped discovery, not path confinement. Either add an explicit controlled deny-write probe or downgrade the wording.

5. **Frozen-commit reference URLs are dead.** `setup.md:5`, `pilot.md:5`, `preflight.md:7` link `[58d48c…](https://github.com)` — a bare host, not the repository. Real remote is `https://github.com/Hazem-Samak/skill-lens.git`; these should point at the actual blob/commit for that repo.

**SUGGESTIONS**:

6. **Control-path ambiguity (Observation C) should be stated, not implied.** `herdr agent start --help` says the pane "must be at its interactive shell prompt" and success means the agent "was detected in the same terminal" — i.e. starting Hermes **occupies** the pane and replaces its shell prompt. `herdr agent prompt` is a separate top-level control command that targets the agent **by name** and can run from any shell, so the handoff is viable only if the human runs `agent prompt` from a **second shell/pane**, not the now-occupied pane. `setup.md` §6 Step 4 reads as if run from the same pane. Add an explicit step: control/`prompt` runs from a separate shell or `herdr pane split` control pane. (No live trial authorized; document the reasoning, don't assert it proven.)

7. **Kind-list finding vs. "no possible route" (Observation A).** Correct to keep the precise claim: `mcode`/`minimax` are not among the 24 native kinds. Do **not** inflate this to proof no supported native route exists, and do not demand a permanent roster amendment — the T3-selected reviewer pair differs from the eventual Herdr role pool. Keep it as a scoped unresolved prerequisite (as the files already mostly do).

8. **`HERDR_PANE_ID` usage is fine** (it is Herdr-exported; `herdr pane --help`/`--skill` confirm). No change needed there.

9. **Receipt label nit:** `preflight-receipt.json` uses `frozenReference` for the frozen commit and `referenceCommit` for current HEAD `a0ffa9e…` — labels are inverted-sounding. Rename to `frozenCommit`/`checkoutHead` for clarity.

10. **Independent work that can proceed safely now:** the four accuracy corrections above are pure documentation edits within the same allowed paths and can be dispatched to the same implementer (Gemini 3.8 Flash High) without any Herdr session, pilot, or approval. No P01–P09 execution, no startup, no restart, no session/mapping approval may be inferred or performed.

**FILES_AT_RISK** (reviewed; corrections would touch these untracked evidence files only):
- `docs/validation/two-surface-orchestration/2026-10-17/setup.md` (lines 5, 77–80, 107–125, §7)
- `docs/validation/two-surface-orchestration/2026-10-17/pilot.md` (line 5)
- `docs/validation/two-surface-orchestration/2026-10-17/implementation/preflight.md` (lines 7, 40, §3 item 3, §7)
- `docs/validation/two-surface-orchestration/2026-10-17/implementation/preflight-receipt.json` (ruffFormat, frozenReference/referenceCommit, roleMappingProposal)
- Frozen `docs/plans/2026-10-17-two-surface-orchestration.md`, `docs/process/**`, product/`tests`, and pre-existing untracked `.path` — **verified unchanged/untouched**; must remain so.

**CONCEDED**:
- **Observation B:** cmux absence from `$PATH` is real and does not require persistent shell edits; the files correctly note absolute-path invocation. No correction needed.
- **Observation F:** confirmed the placeholder path does not exist.
- **Observation G:** confirmed both the bare GitHub URL defect and the 187-vs-184 discrepancy (187 is authoritative).
- **Observation H:** confirmed P01–P09 remain unexecuted; the user's overnight instruction does not repeal the explicit human startup/restart/session+mapping approvals, and no such approval should be inferred.
- **Observation D/E:** confirmed the `--tools`/MCP and `--ignore-rules`/`--in`/`--add-dir` helper text directly from installed help — the "enforced"/"confined" wording is overclaimed.
- **Observation C:** confirmed via `herdr agent start`/`agent prompt` help that the single-pane startup as written is ambiguous and needs a separate control shell; no live trial performed or authorized.
- Scope integrity: read-only review only; no writes, no delegation, no approval, no test runs inside the checkout.
