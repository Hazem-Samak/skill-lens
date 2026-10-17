# Native pilot critic amendment round 1 adjudication

Target reviewed: draft SHA256 a40ecffa2a271c636e34d50d1f8244fedf86a3c26680ba4ec071b9356b1e5c41, HEAD b6d5a172aeeb4bb271103ad6634459c4bd212b60.

## Findings and dispositions

- MiniMax: changes_required. Accepted the real mismatch: both critics were promised newly empty per-dispatch session directories, but only Qwen had that explicit template; current DeepSeek used fixed pilot-artifacts/pi-sessions. Reproduced by extracting exact commands. Corrected by explicitly adding DeepSeek's storage-template change to the amendment delta and supplying its complete native template. Do not weaken the fresh-context requirement to get a pass.
- Rejected one supporting overstatement: the two reviewed commands did not literally share one directory. Qwen was tokenized; DeepSeek was fixed. A fixed directory alone without resume flags does not prove automatic recall occurred. The unresolved issue was the draft's unsupported mapping guarantee, not an observed leak.
- Adopted MiniMax's nonblocking topology clarification: two distinct available shell panes, separate tokens/names/directories, both submissions before completion collection. Existing model/provider/effort/tool controls are preserved for DeepSeek; its session-storage delta is now explicit and awaits adoption/freeze like the Qwen mapping.
- DeepSeek original task: incomplete terminal narration, no report/VERDICT. Checked full durable activity; no completed report artifact existed. Not counted as review. One fresh same-model completion retry inspected the same unchanged draft and returned PASS, no blockers. This is result recovery within round 1, not a third review wave or fabricated agreement.
- Adopted DeepSeek's nonblocking P04 scope clarification: no-write Pi mappings require complete native recovery, or capability unavailable/stop. Base section 4.2 fallback remains for other mappings that genuinely support it; do not widen tools. The raw report calls this section 4.1; the actual source is 4.2, so the draft uses 4.2.
- Served-family identity remains unverified. Exact named-pair disclosure/adoption is still required; user model-selection delegation does not establish upstream identity. The closed eleven-route list and explicit Grok/XKiro exclusions remain controlling; all new tasks used only the existing selected T3 critics.
- Gate receipts remain in the explicitly allowed implementation evidence path. DeepSeek's suggestion about keeping them out of the frozen allow-list is not adopted: the original base allow-list expressly includes implementation/**. Logs are source-health evidence only, never pilot proof.

## Review window and next step

The original before/after fingerprint comparison showed zero changed paths, head unchanged and status unchanged after MiniMax and the DeepSeek completion result, before coordinator report retention/correction. No reviewer edits accepted. Both questions are affected by the clarified shared session contract, so dispatch both original critics in fresh round 2 tasks. No third broad review wave if two rounds fail to converge. No live pilot, configuration changes or active process implementation occurred.
