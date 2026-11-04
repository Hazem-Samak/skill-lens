# U6 behavioral mutation checks

Every experiment ran in a temporary copy of the frozen working tree. The receipt was updated after each case with complete test output, runtime assertion markers and exact exit codes. The temporary copy was deleted afterward.

Runner: `/Users/corvette/Documents/Projects Coding/Skill Lens/.venv/bin/pytest`
Temporary imports: `/private/var/folders/tf/jsdyxcts6y72fs98s7wl3dfm0000gn/T/skill-lens-u6-mutations-px9tzqd7/checkout/skill_lens/__init__.py`, `/private/var/folders/tf/jsdyxcts6y72fs98s7wl3dfm0000gn/T/skill-lens-u6-mutations-px9tzqd7/checkout/tests/test_tui_agents.py`, and `/private/var/folders/tf/jsdyxcts6y72fs98s7wl3dfm0000gn/T/skill-lens-u6-mutations-px9tzqd7/checkout/tests/test_tui_compare.py`

| Behavior guarded | Status | Control | Mutant | Restored | Assertion reached |
| --- | --- | ---: | ---: | ---: | --- |
| filter letters open Agents | killed | 0 | 1 | 0 | True |
| picker filters to detected agents | killed | 0 | 1 | 0 | True |
| first visit rereads a captured skill file | killed | 0 | 1 | 0 | True |
| ordered pair is reversed | killed | 0 | 1 | 0 | True |
| stale success enters the report cache | killed | 0 | 1 | 0 | True |
| stale error poisons controller failure state | killed | 0 | 1 | 0 | True |
| old screen cleanup cancels a newer token | killed | 0 | 1 | 0 | True |
| raw refresh leaves the old report and JSON visible | killed | 0 | 1 | 0 | True |
| missing choice dispatches a report worker | killed | 0 | 1 | 0 | True |
| redraw retries a failed report | killed | 0 | 1 | 0 | True |
| delayed close pops the current screen regardless of owner | killed | 0 | 1 | 0 | True |
| raw-mode cursor actions move hidden picker controls | killed | 0 | 1 | 0 | True |
| comparison diagnostic text is parsed as markup | killed | 0 | 1 | 0 | True |

**Result:** 13/13 mutants killed; unresolved cases: 0.
