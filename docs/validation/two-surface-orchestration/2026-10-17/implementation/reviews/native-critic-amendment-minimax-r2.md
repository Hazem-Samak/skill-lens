EFFECTIVE_MODEL
Provider/model: `m:minimax:MiniMax-M3.1-Flash-Preview:v:thinking` (mcode / MiniMax M3.1 Flash) — the unchanged council first-critic route. Council setting is `thinkingEffort=xhigh` (base plan:59–60); the effort actually executed is not observable from inside the session, so effort level is **unverified**. runtimeMode=full-access, interactionMode=plan. Requested/configured = the m:minimax route at the frozen council setting. Confirmed only: execution on the m:minimax route under full-access with plan interaction (session runtime info). Upstream served identity and family remain **unverified** and are never execution proof (base plan:71–73).

VERDICT
**pass** — for draft content only. This approves the exact draft for later user adoption. It grants no runtime acceptance, no freeze permission, and waives no missing pilot evidence.

BLOCKERS
None. My round-1 blocker is resolved.

Round-1 blocker (session-storage mismatch) — **resolved by option (b)**, verified at token level, not merely by reading the prose. I extracted both the approved `setup.md:94` critic-2 command and the amendment's `amendment:54` template and diffed them token by token. Exactly three tokens differ, and nothing else:

1. `critic_deepseek` → `critic_deepseek_<dispatch-token>` (agent name)
2. `<pane-id>` → `<second-available-shell-pane-id>` (distinct pane)
3. `…/pilot-artifacts/pi-sessions` → `…/pilot-artifacts/pi-critic-deepseek-<dispatch-token>/sessions`

`--provider workbuddy`, `--model deepseek-v4.1-flash`, `--thinking high`, `--tools read,grep,find,ls`, `--no-mcp`, `--no-extensions`, `-e …/herdr-agent-state.ts`, `--no-skills`, `--no-context-files` are byte-identical. The coordinator's "retaining its provider/model/thinking/tool/context flags while replacing only its session directory" claim is exact and independently reproduced; no silent weakening of the approved critic-2 controls occurred.

Topology is now coherent and internally consistent. Every claim site matches the mapping: §1:14, §3:44, §3:51, §3:57, §3:59, §4:69, §5:77 and §7:100 all scope per-dispatch empty directories to **both** critics. The two paths are distinct in both the `pi-critic-qwen-<dispatch-token>` and `pi-critic-deepseek-<dispatch-token>` components and, per §3:59, in the token values themselves. §4:69 no longer asserts a property the mapping fails to deliver — the §4 overstatement is gone. §3:51 names the old fixed path only to mark it replaced; no stale `pi-sessions` survives in executable instructions. Independence is still proven at runtime, not assumed (P02).

SUGGESTIONS (nonblocking)

1. `amendment:14` says critic 2 changes "only its session-storage template", but the template also tokenizes the agent name and the pane placeholder (confirmed by the diff above). Tighten to "only its session-storage template and its per-dispatch name/pane identity change" so §1 does not read narrower than §3:54. Execution is unambiguous either way; this is precision only.
2. `amendment:69` makes P02 prove *parallel submission*, while §3:44 asserts directories are "newly created empty". Consider one clause stating P02 must observe the per-dispatch directories as freshly created/empty at dispatch rather than infer it from the template — this is precisely the property that was previously overstated, so naming it closes the loop. Base plan:140–143 already carries the fresh-context requirement, so this is strengthening, not a defect.
3. `amendment:10` ("2 independent T3 amendment critics before corrections") predates the correction round. The trailing clause covers extra rounds, but the count could be reworded so it is not read as the final expected-task total; §8:104 carries the accurate history.
4. Gate figures (1048 passed, 1 expected skip, 91.11%, mypy 37, ruff check clean, format 205) match `implementation/pilot-critic-amendment-gates/` as cited at §8:106, with per-run labeling intact. Confirm at adoption whether they are carried forward or re-run; the base records three different format counts across runs.

FILES_AT_RISK

- `docs/plans/2026-10-17-herdr-native-pilot-critic-amendment.md` — untracked, SHA-256 `011648051eb7cd77a3b5d9fa4100cf1c9b9facbf5a8471d19b761132739ad1c3` at review start and end; the only file authorized for pre-adoption editing, plus appends under `…/implementation/`.
- `docs/plans/2026-10-17-two-surface-orchestration.md` — frozen base; working tree matches HEAD blob `e62381c1…` and is unmodified. `58d48cea…` is the frozen **commit** "docs: freeze plan two-surface orchestration", not a content hash — consistent with the base's own references. Unchanged.
- Post-adoption allow-list: `…/setup.md`, `…/pilot.md`, `…/acceptance.md`, `…/implementation/preflight-receipt.json`, `…/implementation/human-pilot-brief.md` — must apply both per-dispatch templates (§6 step 4); current uncommitted edits remain administrative.
- `/Users/corvette/.pi/agent/extensions/herdr-agent-state.ts` — read-only machine reference in executable text; explicit `-e` retention must survive any future edit.
- `grok-native-controls-research-r1/r2.md`, `pilot-critic-research-terminal-receipts.json` — raw historical research; leakage into executable instructions is the live risk, forbidden by §7:100.
- `.path` — 0 bytes, untracked, timestamp Oct 16, unchanged.
- No `skill_lens/`, `tests/`, `docs/process/`, `pyproject.toml` or `AGENTS.md` change exists.

CONCEDED

Draft hash and HEAD match the round-2 targets exactly (`0116480…ad1c3`, `b6d5a17…b60`).

Targeted question answered **yes**: the explicit both-critic storage delta resolves my concern, and the wider topology/scope is coherent. I independently confirmed the rejected overstatement was *not* reintroduced — the draft nowhere claims the two commands literally shared one path.

Authority, precedence and staging hold. Closed-list authorization with Grok/XKiro excluded and no automatic fallback (§1:16, §7:100). Migration council remains MiniMax/mcode xhigh + Pi/WorkBuddy DeepSeek high (§1:14, §5:83), Gemini sole implementer, Sol coordinator — unchanged. Adoption/freeze correctly staged: `Reference: pending`, concrete approval plus two-commit freeze and push verification, "A commit does not create authorization" (§1:5, §1:20, §6:91). Frozen-reference precedence respected — base text preserved, both operative references must be named in receipts (§1:20). The session-directory change is an explicit amendment delta requiring the same adoption/freeze, not a silent flag change to pass a test (base plan:284, §3:57).

Scope discipline is correct. The read-only Pi mappings cannot write the §4.2 Markdown fallback, and the draft limits that consequence to these two mappings rather than removing the base fallback for other kinds (§3:65) — a conservative narrowing, not a policy waiver, with P04 requiring complete native recovery or an explicit unavailable-and-stop. Served-family identity remains unverified with the exact named pair disclosed for adoption (§4:71). All P01–P09 remain PENDING and unexecuted. Source gates are evidence of source health only, never pilot proof.

My review wave made no repository mutation: HEAD unchanged, 20 porcelain entries before and after, draft hash and `.path` identical, no tests, installs, formatters, regenerations, Herdr control, delegation, or writes inside the checkout. Temporary comparison files were written only under `/tmp`.
