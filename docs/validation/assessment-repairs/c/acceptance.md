# Stage C acceptance — 13 October 2026

Stage C of the supplied assessment plan is accepted under reference `fe6f89bc55eb3f4f04187567b968dd96ae9c86c1`. The coordinator owns this conclusion; reviewer reports and green tests alone do not establish it. The Stage D–H repairs remain unfinished.

## Changes and proof

- CLI relative working directories now resolve against the terminal in live execution and against the sandbox in sandboxed execution. Default cwd and explicit `--cwd .` locate the same project. Lazy XDG lookup is contained in sandbox tests and reaches custom live config roots.
- Discovery retains every actual entrypoint/root/agent hit; canonical storage does not erase shortcut aliases. Resolution uses the correct hit identity and disable-override synonyms. Distinct paths and same-path roots have separate controls; reversed root order keeps the stronger same-path rule.
- Root entry formats separate directory bundles, standalone Markdown, qualified Pi Markdown, and the selected OpenCode V2 discovery shape. Directory-only native roots ignore incidental flat documentation. DSH native roots explicitly support flat files and directories. Six uncertain retained roots preserve earlier inventory compatibility, with actual vendor loadability unverified and assigned to Stage D.
- OpenCode nested directory shortcuts retain reached-path provenance without unbounded link traversal. Current depth, container-link and declared-directory traversal limits are disclosed for Stage D rather than described as complete vendor parity.
- Standalone root `SKILL.md` inventory naming agrees across consumers. Files use their stem; directories ending in `.md` keep their full name. A broken shortcut whose type is unknown keeps the full name; this deliberate diagnostic name change is a non-blocking follow-up item, not an assertion of its target type.
- The raw 20-root declaration guard reads the imported package's registry, not the process cwd. Actual-package corruption fails even from a valid decoy starting directory; corruption of the decoy does not change the answer. The test additionally changes cwd to a fresh temporary directory. The earlier doctor-test `.location` access was corrected to the actual `DoctorFinding.path` field; a short-circuited expression had hidden that incorrect field.
- Opaque captured-byte transient changes have an isolated positive/negative proof. The initial combined mutation failed an earlier subcase and did not prove this specific guard; the coordinator required isolation and independently verified the intended failure.

## Acceptance gates and independent review

The coordinator ran `pytest --cov=skill_lens`, `mypy`, `ruff check .`, and `ruff format --check .` on the final code/test tree with synthetic HOME and XDG cleared. Results: **860 passed, 1 skipped**, **93.38% combined branch coverage**, mypy clean on **35 package files**, Ruff lint clean and **123 files formatted**. The skip is physical dual-case filenames unsupported on this filesystem. These are local macOS/Python 3.11 results; unexecuted CI lanes are not claimed.

The final changed-cwd guard edit did not change any product, TOML, loader, fixture or evidence-table byte from the tree MiniMax accepted. MiniMax's prior product/safety pass is retained for that verified unchanged scope. OpenCode accepted the guard correction in a fresh affected-critic task and retained all its previously conceded product objections. No remaining in-scope blocker is deferred.

Verified coordinator and implementer mutation records establish control/mutant/restored results of **0/1/0** in disposable verified source copies for directory-only file omission, exact Pi declaration, per-hit overrides, metadata validation, standalone naming, nested shortcuts, opaque capture, file-type alias, same-path rank selection, raw declaration presence, and uncertain-root flat compatibility. The records include source paths and relevant restoration hashes; they do not claim a full mutation score.

After two council rounds failed to converge, the owner explicitly approved focused Stage C corrections and targeted review. The final follow-up fixed only the new guard's cwd dependence. Both critics used the user's selected targets: OpenCode `opencode/space-bunny-free` at `variant=max` and MCode `m:minimax:MiniMax-M3.1-Flash-Preview:v:thinking` at `thinkingEffort=xhigh`. T3 configuration corroborates model/options/modes, while actual provider-served identity and effort remain unverified without backend evidence. Space Bunny family identity remains unverified. Full-access/plan restraint was instruction-based; fingerprints and git status confirmed no reviewer edits.

A correction worker introduced an unreported loader rewrite that removed defaults/slots, changed root properties/API and silently swallowed invalid registry definitions. The coordinator detected it in the complete delta and reproduced a custom-registry failure. The implementer restored the reviewed file exactly except for a three-line comment, preserving fail-loud behavior and all earlier interfaces. That failed intermediate tree was never accepted.

## Receipt and retained boundaries

Expected first Stage C batch: one implementer and two critics. Actual: **17 child launches** (10 implementation/correction tasks and 7 reviews), including source-evidence corrections, owner escalation, and the final test-only guard fix. All 17 are terminal with no pending child runs. Active compute time and provider token usage are unavailable; no measured token-savings claim is made. Unnecessary repeat broad review was avoided for the final test-only correction.

Stage D retains full supported version/surface/identity/root/precedence/control and per-agent loadability alignment: OpenCode V2 only with V1 unsupported; missing `.claude` compatibility roots; Pi lookup policy; Antigravity CLI versus IDE legacy roots; OMP managed path; unknown retained shared/plugin/bundled loadability; casing/traversal limits. Root-format declarations preserve existing rank, scope and precedence evidence. Documented native directory forms deliberately stop admitting flat files the earlier generic discovery accepted; this is a source-backed correction, not preserved flat-file compatibility on those roots.

Non-blocking reviewer suggestions on test naming, extra CLI-level parity, diagnostic pinning and future all-agent explicit-format coverage are recorded in the full reports. A pre-existing empty untracked `.path` file is preserved and excluded from the commit. U3–U9, release/push/publishing, old artifact replacement, arbitrary resource/dependency policies remain outside this stage.

The adjacent source evidence record and saved coordinator logs, mutation evidence, terminal receipts and reviewer reports are the durable acceptance record. Temporary source copies may be removed; the test suite recreates the relevant controls without depending on those scratch directories.
