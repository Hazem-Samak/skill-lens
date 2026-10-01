"""Exit-code policy: when a finished report should fail the process.

This module is deliberately pure. It decides *only* whether a set of findings
reached the caller's threshold, and returns the integer a shell should see. It
does not know about Typer, Rich, the filesystem, or any command. ``cli.py``
turns the result into ``typer.Exit``; nothing else decides an exit code.

The contract, in one place:

===== ==========================================================
Code  Meaning
===== ==========================================================
``0`` The command ran and nothing reached the threshold.
``1`` The command ran and findings reached the threshold.
``2`` The command could not run: bad usage, unknown agent,
     unreadable input. Already the pre-Phase-6 behaviour for
     ``why`` and ``compare``.
``3`` Reserved for an unexpected internal fault. Never emitted
     deliberately; it exists so a future bug does not have to
     invent a meaning that collides with the codes above.
===== ==========================================================

Why the default is ``NEVER``
----------------------------

Every Skill Lens command exited ``0`` before this module existed, including
``doctor`` on a machine with real errors. That is the right default for a report
you read and the wrong default for a check you automate. Since a report is the
common case and a gate is opt-in, ``NEVER`` preserves existing behaviour exactly
and ``--fail-on`` is what turns the tool into a gate. Changing the default later
would silently break anyone's CI, so it is not changed later.

A threshold is a *comparison*, never a count: ``--fail-on error`` fails when any
finding is at ``error``, regardless of how many informational notes sit beside
it. Counting would make the exit status depend on unrelated noise.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum

from skill_lens.models.enums import Severity


class ExitCode(IntEnum):
    """Process exit statuses. Values are the integers shells actually see.

    ``IntEnum`` rather than ``StrEnum``: these *are* integers, a shell compares
    them numerically, and ``StrEnum`` would refuse to hold them. They are never
    serialized into the JSON reports, so there is no string form to preserve.
    """

    OK = 0
    """The command ran and nothing reached the threshold."""

    FINDINGS = 1
    """The command ran and findings reached the threshold."""

    USAGE = 2
    """The command could not run: bad usage or an unknown agent."""

    INTERNAL = 3
    """Reserved for an unexpected internal fault."""


class FailOn(StrEnum):
    """Which severity turns a finished report into a failed run."""

    NEVER = "never"
    """Always exit 0. The default, and the pre-Phase-6 behaviour."""

    ERROR = "error"
    """Fail when any finding is an ``error``."""

    WARNING = "warning"
    """Fail when any finding is an ``error`` or a ``warning``."""

    INFO = "info"
    """Fail when any finding exists at all, informational notes included."""


#: Ordering used for both "at or above" comparisons and ``info`` as the floor.
_SEVERITY_RANK: dict[Severity, int] = {
    Severity.ERROR: 0,
    Severity.WARNING: 1,
    Severity.INFO: 2,
}

#: The threshold each ``--fail-on`` value sets, or ``None`` for ``never``.
_THRESHOLD: dict[FailOn, Severity | None] = {
    FailOn.NEVER: None,
    FailOn.ERROR: Severity.ERROR,
    FailOn.WARNING: Severity.WARNING,
    FailOn.INFO: Severity.INFO,
}

_FAIL_ON_HELP = (
    "Lowest severity that makes the command exit "
    f"{int(ExitCode.FINDINGS)} instead of {int(ExitCode.OK)}."
)

#: Appended to the help text so ``--fail-on info`` cannot mislead anyone.
#:
#: ``info`` looks like the strictest setting and is, but it is also effectively
#: unusable as a gate: ``doctor`` emits informational notes about *normal* setups
#: (an absent installer lockfile, a symlink farm that is the installer's normal
#: layout). A completely empty home already produces one, so ``--fail-on info``
#: fails everywhere. Saying so here is cheaper than letting someone discover it
#: as a broken pipeline.
_FAIL_ON_CAVEAT = (
    " Note: 'info' also trips on routine informational notes that describe a "
    "healthy setup, so it fails on almost any machine; use 'error' or 'warning' "
    "for a gate."
)


def fail_on_help() -> str:
    """The ``--fail-on`` help text, including the valid values.

    Kept beside the enum so the CLI cannot drift from the vocabulary it accepts.
    """
    values = ", ".join(option.value for option in FailOn)
    return f"{_FAIL_ON_HELP} One of: {values}.{_FAIL_ON_CAVEAT}"


def exit_code_for(severities: tuple[Severity, ...] | list[Severity], fail_on: FailOn) -> ExitCode:
    """Return the exit status for a finished run.

    ``severities`` is the severity of every finding the report contains, in any
    order. ``fail_on`` is the caller's threshold.

    An empty report always succeeds, whatever the threshold: "nothing was wrong"
    is never a reason to fail, and a gate that fails on an empty report would be
    unusable.
    """
    threshold = _THRESHOLD[fail_on]
    if threshold is None:
        return ExitCode.OK
    # "At or above" in Skill Lens means *more severe than* the threshold, and
    # lower ranks are more severe.
    #
    # An empty report needs no special case: ``any()`` over nothing is False, so
    # a clean run already returns OK at every threshold. That behaviour is
    # asserted by the Phase 6 gate; it is a property of the comparison, not of a
    # guard here. An earlier version had an explicit ``not severities`` branch,
    # which mutation testing showed could be deleted with every test still
    # green -- dead code that looks like protection is worse than none.
    cutoff = _SEVERITY_RANK[threshold]
    if any(_SEVERITY_RANK[severity] <= cutoff for severity in severities):
        return ExitCode.FINDINGS
    return ExitCode.OK
