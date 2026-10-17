# Closed model/provider list authorized by the user

Date: 2026-10-17
User instruction: "That's all the reliable models we have. You need to pick only from those for everything from now on". The user also explicitly rejected Grok and XKiro.

This delegates model selection to the coordinator within the following exact model/provider combinations. It is not permission to use other routes merely because they appear in the catalog. Existing explicit role/settings choices remain in force until an authorized change. There is no new global configuration change or personal-memory write.

| User's reliable model | Authorized route / live T3 model ID |
|---|---|
| GPT 6.1 Sol (coordinator) | Codex: gpt-6.1-sol |
| MiMo V2.6 Flash Free | OpenCode: opencode/mimo-v2.6-flash-free |
| GLM 5.3 Flash Free | OpenCode: opencode/glm-5.3-flash-free |
| Space Bunny Free | OpenCode: opencode/space-bunny-free |
| Gemini 3.8 Flash High | Antigravity: gemini-3.8-flash-high |
| MiniMax M3.1 Flash X High | mcode: m:minimax:MiniMax-M3.1-Flash-Preview:v:thinking, thinkingEffort=xhigh |
| Nemotron 3.5 Super VL Free | Pi/OpenRouter: openrouter/nvidia/nemotron-3.5-super-vl:free |
| GLM 5.3 Flash | Pi/AnyModel: anymodel/glm/glm-5.3-flash |
| Qwen 3.8 Max | Pi/AnyModel: anymodel/qwen/qwen3.8-max |
| DeepSeek V4.1 Flash | Pi/River: river/deepseek-ai/DeepSeek-V4.1-Flash |
| DeepSeek V4.1 Flash | Pi/WorkBuddy: workbuddy/deepseek-v4.1-flash |

Catalog presence and model metadata are configured-route evidence, not a completed model reply or upstream served-identity proof. Availability must still be checked before a dispatch. In particular, the catalog's OpenCode DeepSeek/Nemotron and Pi/XKiro routes are not authorized by this list.

## Selection for the pending amendment

Coordinator selects Qwen 3.8 Max via Pi/AnyModel, thinking=high, as the proposed first Herdr pilot critic. Its native arguments use --provider anymodel --model qwen/qwen3.8-max --thinking high. Coordinator independently verified this exact model exists in the whitelisted AnyModel metadata; no configuration edit or generation was performed.

Second Herdr pilot critic: Pi/WorkBuddy DeepSeek high. T3 migration council: MiniMax/mcode xhigh and Pi/WorkBuddy DeepSeek high. Sole worker: Antigravity Gemini 3.8 Flash High. Coordinator: Sol. Upstream identities remain unverified, as disclosed in the earlier selection question and draft.

The earlier Grok and XKiro research/proposals are superseded and retained only as historical evidence. The coordinator will not ask another high/xhigh model-selection question for this choice: the user explicitly delegated selection within this closed list. Concrete native-mapping amendment review/adoption/freeze and human-started pilot remain separate requirements under the existing operative plan.
