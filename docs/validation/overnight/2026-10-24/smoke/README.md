# Bounded smoke on the everyday Herdr session

Result: **pass for the dispatch path**, with scope limits. This is not the
original Sol-coordinator formal smoke and not a full-TUI test.

## What ran

One read-only worker in the user's verified `default` session, in one owned
sibling pane (`wG:pQ`), using the deployed local override and the headless Mini
route:

```text
opencode mini --model opencode/deepseek-v4.1-flash-free#max --agent plan --no-replay
```

The worker was told to use no tools, files, commands or delegation, and to
answer a harmless rule question with BEGIN/END markers.

## Result

| Check | Observed |
| --- | --- |
| startup | `interactive_ready=true`, `idle`, argv exact |
| detection during generation | `working`, matched `status_footer_esc_stop_working`, manifest `2026.10.23.1`, source = local override |
| wait | `agent prompt --wait` exited 0 with `done`, completion sequence 3 |
| wait ordering | returned 0.512 s **after** native completion, not early |
| native session | `outcome=succeeded`, finish `stop`, one user and one assistant turn, zero tool parts |
| answer | complete BEGIN/END text with substantive prose |
| cleanup | worker exited to its original shell; owned pane closed; one focused pane and zero agents remain |

The live working footer used the preserved `Default / OpenCode` branch. The new
2.1.4 `· OpenCode` / usage suffixes were proved in the isolated lap, not here.

## Limits

- Uses the everyday shared OpenCode service, not a private backend.
- The worker's own session snapshot lists coordinator-written evidence files;
  the worker made zero tool calls.
- It does not exercise full-TUI lifecycle waiting and makes no Sol identity
  claim. The original formal smoke remains an owner decision.
