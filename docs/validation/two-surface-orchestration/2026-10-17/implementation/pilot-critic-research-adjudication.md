# Pilot critic research adjudication

Researcher: Gemini 3.8 Flash High through T3, requested/configured by retained task/config receipts; upstream served identity unverified. Candidate identities are separate.

## Reproduced facts

- Installed Grok docs 18-sandbox.md lines31,46 permit writes under /tmp and /var/tmp for read-only. Our fixture is in /tmp, so that OS profile does not deny fixture writes. Line201 says built-in sandbox failure may warn and continue unenforced. No runtime enforcement probe was performed.
- Grok docs 14-headless-mode.md tools table distinguishes built-in allowlist from remaining MCP meta-tools. MCPTool deny governs invocation, not proof of no MCP startup/network. macOS child-network restriction is absent in the sandbox table footnote.
- With agent write/edit/shell tools removed, an agent-written Markdown fallback is unavailable. Complete native readback must be demonstrated or P04 stops. Do not widen permissions.
- Grok 13-memory.md documents --no-memory and GROK_MEMORY=0. This is separate from automatic rule and skill discovery described in 12-project-rules.md and 08-skills.md. Compatibility sources can be toggled through documented environment settings; the raw report overstates them as all unconditional. No existing scoped control for all native personal discovery was established in this bounded inspection. This is a current preflight gap, not proof that no conceivable Grok configuration could work.
- The Grok system-prompt-override help does not independently establish suppression of filesystem discovery/import. Redirecting home would disrupt existing auth/integration and is not an approved remedy. No such change was attempted.
- Coordinator independently parsed only xkiro baseUrl and the selected model metadata from ~/.pi/agent/models.json: xkiro has qwen/qwen3.8-max:free, reasoning=true. Pi help independently confirms --no-skills, --no-context-files, --no-mcp, --no-extensions with explicit -e, --tools, --session-dir and high/xhigh thinking. Existing Herdr enum supports pi.

## Decision

Recommend an exact separately reviewed first-critic proposal using native Pi/XKiro Qwen 3.8 Max, thinking high; the user may select xhigh instead. Earlier Grok-effort question is superseded by this source-backed recommendation. No choice is inferred or launched. No anymodel fallback is authorized. Existing MiniMax/mcode xhigh and Pi/WorkBuddy DeepSeek high T3 migration council remains unchanged.

The raw report's PROVEN/100%/Alternative Ready wording is not accepted as runtime evidence. Native flags are documented controls; fresh context, distinct session IDs, inherited settings, state integration, concurrent submissions, complete reports, denied-write boundaries and owned-stop proof still require P01-P09. Two separate Pi processes/sessions may supply role/context independence; two providers or brand labels alone do not verify served-family diversity. The exact named pilot pair requires the user's disclosed unverified-family acceptance.

## Amendment drafting boundary

The user approved existing setup/lifecycle and consideration of a new native pilot critic. Exact replacement/effort selection is pending. Then complete exact draft, obtain both original independent T3 reviews, present concrete operative approval, freeze with two commits and verify push. No active process migration or live pilot before those boundaries.

## Later controlling user selection authority

The user rejected both Grok and XKiro and supplied an exclusive reliable model/provider
list, delegating choice within it. The current proposal is Pi/AnyModel qwen/qwen3.8-max,
thinking high. The earlier XKiro recommendation above is historical and not executable.
Coordinator verified the AnyModel entry through whitelisted metadata and the live catalog.
Review and concrete adoption/freeze remain required before use.
