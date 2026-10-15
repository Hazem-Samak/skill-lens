"""Enumerations for the Skill Lens 3-axis resolution model.

All enums subclass ``enum.StrEnum`` (Python 3.11+), so members serialize
cleanly to JSON and compare equal to their plain-string values.
"""

from __future__ import annotations

from enum import StrEnum


class Scope(StrEnum):
    """Where a skill installation lives in the capability hierarchy."""

    USER = "user"
    PROJECT = "project"
    SYSTEM = "system"
    PLUGIN = "plugin"


class ParseStatus(StrEnum):
    """Outcome of parsing a skill's frontmatter (axis 1)."""

    VALID = "valid"
    MALFORMED_YAML = "malformed_yaml"
    MISSING_DESCRIPTION = "missing_description"
    UNREADABLE = "unreadable"


class Visibility(StrEnum):
    """Whether the agent's search rules can see this installation (axis 2)."""

    ACTIVE_ROOT = "active_root"
    UNSEARCHED_ROOT = "unsearched_root"
    OUTSIDE_WALK_BOUNDARY = "outside_walk_boundary"
    DISABLED = "disabled"


class Collision(StrEnum):
    """How this installation behaves relative to same-named copies (axis 3)."""

    WINNING_ENTRY = "winning_entry"
    SUPPRESSED_SHADOW = "suppressed_shadow"
    COEXISTING_MERGED = "coexisting_merged"
    QUALIFIED_NAMESPACE = "qualified_namespace"
    AMBIGUOUS_TIE = "ambiguous_tie"
    UNVERIFIED_POLICY = "unverified_policy"


class HeadlineState(StrEnum):
    """Derived headline state surfaced by ``skill-lens why``."""

    ACTIVE = "ACTIVE"
    SHADOWED = "SHADOWED"
    COEXISTS = "COEXISTS"
    DISABLED = "DISABLED"
    UNSEARCHED = "UNSEARCHED"
    INVALID = "INVALID"
    AMBIGUOUS = "AMBIGUOUS"


class Evidence(StrEnum):
    """Provenance level backing a rule. Never guess: see AGENTS.md rule 6."""

    DOCUMENTED = "documented"
    EMPIRICAL = "empirical"
    INFERRED = "inferred"


class Severity(StrEnum):
    """Severity of a ``doctor`` finding."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class CompareRelation(StrEnum):
    """How one skill name sits between two agents (``skill-lens compare``)."""

    SHARED = "shared"
    DIVERGED = "diverged"
    ONLY_A = "only_a"
    ONLY_B = "only_b"


class RootBase(StrEnum):
    """Base directory from which a search root path is resolved."""

    HOME = "home"
    XDG_CONFIG_HOME = "xdg_config_home"


class EntryFormat(StrEnum):
    """Format and discovery contract expected under a search root."""

    DIRECTORY = "directory"
    STANDALONE_MD = "standalone_md"
    QUALIFIED_STANDALONE_MD = "qualified_standalone_md"
    OPENCODE_V2 = "opencode_v2"


class InvocationPolicy(StrEnum):
    """How a skill may be invoked under an agent's policy."""

    ALL = "all"
    USER_ONLY = "user_only"
    MODEL_ONLY = "model_only"
    NAME_ONLY = "name_only"
    NONE = "none"
    UNKNOWN = "unknown"


class PermissionEffect(StrEnum):
    """Authorization or consent required to run a skill."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"
    UNKNOWN = "unknown"


class LoadabilityStatus(StrEnum):
    """Whether a specific agent will actually load this candidate entrypoint."""

    LOADABLE = "loadable"
    INVALID = "invalid"
    UNKNOWN = "unknown"
