"""Version-specific configuration decoders and agent-specific loadability rules.

Pure, read-only configuration decoders for:
1. Claude Code settings (local > project > user precedence;
   off/on/name-only/user-invocable-only/false).
2. OpenAI Codex config ([[skills.config]] tables; per-SKILL.md path enabled=false).
3. OpenCode V2 config & permissions (project > user; action: "skill", effect: allow/deny/ask).

Security & privacy:
- Decoders only parse skill controls. No raw configs, tokens, secrets, or unrelated settings
  are ever returned or stored in resolution models.
- Missing, malformed, and unreadable controls are distinctly categorized.
"""

from __future__ import annotations

import json
import os
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

from skill_lens.core import paths
from skill_lens.core.discovery import (
    DiscoveredEntry,
    RootHit,
    find_walk_boundary,
)
from skill_lens.core.system import installer_lockfile
from skill_lens.models.enums import (
    InvocationPolicy,
    LoadabilityStatus,
    ParseStatus,
    PermissionEffect,
)
from skill_lens.models.parsing import ERR_MISSING_DESCRIPTION, ERR_MISSING_FRONTMATTER
from skill_lens.registry.loader import AgentDefinition

if TYPE_CHECKING:
    from skill_lens.core.snapshot_models import CapturedInput


def strip_jsonc_comments_and_trailing_commas(text: str) -> str:
    """Pure, string-aware preprocessor for JSONC text.

    Strips // line comments and /* ... */ block comments outside string literals.
    Strips trailing commas before } and ] outside string literals.
    Does not alter https:// or other characters within string literals.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    escape = False

    while i < n:
        c = text[i]
        if in_string:
            out.append(c)
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            i += 1
            continue

        if c == '"':
            in_string = True
            out.append(c)
            i += 1
            continue

        if c == "/" and i + 1 < n:
            next_c = text[i + 1]
            if next_c == "/":
                i += 2
                while i < n and text[i] != "\n":
                    i += 1
                continue
            elif next_c == "*":
                i += 2
                while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                    i += 1
                i += 2
                continue

        if c == ",":
            j = i + 1
            is_trailing = False
            while j < n:
                cj = text[j]
                if cj in " \t\r\n":
                    j += 1
                elif cj == "/" and j + 1 < n and text[j + 1] == "/":
                    j += 2
                    while j < n and text[j] != "\n":
                        j += 1
                elif cj == "/" and j + 1 < n and text[j + 1] == "*":
                    j += 2
                    while j + 1 < n and not (text[j] == "*" and text[j + 1] == "/"):
                        j += 1
                    j += 2
                elif cj in ("}", "]"):
                    is_trailing = True
                    break
                else:
                    break
            if is_trailing:
                i += 1
                continue

        out.append(c)
        i += 1

    return "".join(out)


def entrypoint_alias(path: str | Path, is_file: bool = False) -> str:
    """Return the filename stem (for files) or directory name for an entrypoint path."""
    p = Path(path)
    if is_file:
        return p.stem
    return p.name


# --- 1. Claude Settings Decoders -------------------------------------------


def decode_claude_settings_with_status(
    data: bytes | None,
) -> tuple[dict[str, str | bool], str | None]:
    """Pure decoder for Claude settings JSON bytes, preserving error status."""
    if data is None:
        return {}, None
    if len(data) == 0:
        return {}, "malformed"
    try:
        text = data.decode("utf-8")
        clean_text = strip_jsonc_comments_and_trailing_commas(text)
        parsed = json.loads(clean_text)
    except (UnicodeDecodeError, ValueError):
        return {}, "malformed"
    if not isinstance(parsed, dict):
        return {}, "malformed"
    overrides = parsed.get("skillOverrides")
    if overrides is None:
        return {}, None
    if not isinstance(overrides, dict):
        return {}, "malformed"
    result: dict[str, str | bool] = {}
    error_status: str | None = None
    for key, val in overrides.items():
        if not isinstance(key, str) or not key:
            error_status = "malformed"
            continue
        if type(val) is bool or (
            isinstance(val, str) and val in ("on", "off", "name-only", "user-invocable-only")
        ):
            result[key] = val
        else:
            error_status = "malformed"
    return result, error_status


def decode_claude_settings(data: bytes | None) -> dict[str, str | bool]:
    """Pure decoder for Claude settings JSON bytes.

    Extracts skillOverrides mapping.
    Only recognized string values ('on', 'off', 'name-only', 'user-invocable-only')
    and boolean values (True, False) are retained. All unrelated keys are ignored.
    """
    settings, _ = decode_claude_settings_with_status(data)
    return settings


def resolve_claude_settings(
    user_data: bytes | dict[str, str | bool] | None = None,
    project_data: bytes | dict[str, str | bool] | None = None,
    local_data: bytes | dict[str, str | bool] | None = None,
) -> dict[str, str | bool]:
    """Resolve effective Claude settings across precedence stack.

    Precedence order: Local > Project > User.
    """
    merged: dict[str, str | bool] = {}
    for d in (user_data, project_data, local_data):
        if d:
            if isinstance(d, dict):
                merged.update(d)
            else:
                merged.update(decode_claude_settings(d))
    return merged


# --- 2. Codex Config Decoders ----------------------------------------------


def decode_codex_config_with_status(
    data: bytes | None,
) -> tuple[dict[str, bool], list[str], str | None]:
    """Pure decoder for Codex config.toml bytes with status preservation."""
    if data is None:
        return {}, [], None
    if len(data) == 0:
        return {}, [], "malformed"
    try:
        text = data.decode("utf-8")
        parsed = tomllib.loads(text)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        return {}, [], "malformed"
    if not isinstance(parsed, dict):
        return {}, [], "malformed"
    skills_obj = parsed.get("skills")
    if skills_obj is None:
        return {}, [], None
    if not isinstance(skills_obj, dict):
        return {}, [], "malformed"
    configs = skills_obj.get("config")
    if configs is None:
        return {}, [], None
    if not isinstance(configs, list):
        return {}, [], "malformed"
    result: dict[str, bool] = {}
    unsupported: list[str] = []
    error_status: str | None = None
    for item in configs:
        if isinstance(item, dict):
            path_val = item.get("path")
            enabled_val = item.get("enabled")
            if isinstance(path_val, str) and type(enabled_val) is bool:
                norm_p = path_val.strip()
                if norm_p:
                    result[norm_p] = enabled_val
            else:
                error_status = "malformed"
        else:
            error_status = "malformed"
    return result, unsupported, error_status


def decode_codex_config(data: bytes | None) -> dict[str, bool]:
    """Pure decoder for Codex config.toml bytes.

    Parses [[skills.config]] tables into a path -> enabled mapping.
    """
    res, _, _ = decode_codex_config_with_status(data)
    return res


# --- 3. OpenCode V2 Config & Permission Decoders ---------------------------


@dataclass(frozen=True, slots=True)
class OpenCodePermissionRule:
    """One skill permission rule decoded from opencode.json."""

    resource: str
    effect: str  # "allow", "deny", "ask"


def decode_opencode_permissions_with_status(
    data: bytes | None,
) -> tuple[list[OpenCodePermissionRule], list[str], str | None]:
    """Pure decoder for OpenCode V2 config JSON/JSONC bytes.

    Parses permissions array for action == "skill" or wildcard "*".
    Preserves rule ordering.
    Returns (rules, unsupported_controls, error_status).
    """
    if data is None:
        return [], [], None
    if len(data) == 0:
        return [], [], "malformed"
    try:
        text = data.decode("utf-8")
        clean_text = strip_jsonc_comments_and_trailing_commas(text)
        parsed = json.loads(clean_text)
    except (UnicodeDecodeError, ValueError):
        return [], [], "malformed"
    if not isinstance(parsed, dict):
        return [], [], "malformed"

    rules: list[OpenCodePermissionRule] = []
    unsupported: list[str] = []
    error_status: str | None = None

    # Detect default_agent or agent selection overrides
    default_agent = parsed.get("default_agent")
    if default_agent is not None and (
        not isinstance(default_agent, str) or default_agent != "build"
    ):
        unsupported.append(
            "Non-default OpenCode agent selection ('default_agent') is unmodelled; "
            "permission confidence is unknown"
        )

    # Detect V1 forms if present
    if "permission" in parsed:
        unsupported.append("OpenCode V1 'permission' key is unsupported in V2")

    # Detect unmodelled local skills array
    if "skills" in parsed and parsed.get("skills"):
        unsupported.append("OpenCode 'skills' array sources are unmodelled at runtime")

    # Detect agent-specific permissions if present
    if "agents" in parsed and isinstance(parsed["agents"], dict):
        has_agent_permissions = False
        for ag_cfg in parsed["agents"].values():
            if isinstance(ag_cfg, dict) and "permissions" in ag_cfg:
                has_agent_permissions = True
                break
        if has_agent_permissions:
            unsupported.append(
                "Agent-specific permissions are unsupported; permission confidence is unknown"
            )

    perms = parsed.get("permissions")
    if perms is not None:
        if not isinstance(perms, list):
            return [], unsupported, "malformed"
        for item in perms:
            if not isinstance(item, dict):
                error_status = "malformed"
                continue
            action = item.get("action")
            resource = item.get("resource")
            effect = item.get("effect")

            if "permission" in item or "pattern" in item:
                unsupported.append("Unsupported permission/pattern rule format")

            if action in ("skill", "*"):
                if not isinstance(resource, str) or not isinstance(effect, str):
                    error_status = "malformed"
                    continue
                eff_lower = effect.lower()
                if eff_lower in {"allow", "deny", "ask"}:
                    rules.append(OpenCodePermissionRule(resource=resource, effect=eff_lower))
                else:
                    unsupported.append("Invalid permission effect")
                    error_status = "malformed"
            elif isinstance(action, str):
                continue
            else:
                error_status = "malformed"

    return rules, unsupported, error_status


def decode_opencode_permissions(data: bytes | None) -> list[OpenCodePermissionRule]:
    """Pure decoder for OpenCode V2 config JSON/JSONC bytes."""
    rules, _, _ = decode_opencode_permissions_with_status(data)
    return rules


# --- 4. Agent-Specific Loadability & Portability Separation ----------------


def is_loadable_for_agent(
    agent: AgentDefinition,
    entry: DiscoveredEntry,
    hit: RootHit | None = None,
) -> tuple[LoadabilityStatus, str | None]:
    """Separate generic parser portability status from agent-specific loadability.

    Returns (status, qualification_reason):
    - LOADABLE: The specific agent's runtime loader will successfully load this skill.
    - INVALID: The specific agent's runtime loader will reject or fail to load this skill.
    - UNKNOWN: The loadability on this search root is unverified.
    """
    parse = entry.parse
    if parse is None:
        if entry.parse_status == ParseStatus.UNREADABLE.value:
            return LoadabilityStatus.INVALID, "Unreadable skill document or directory"
        return LoadabilityStatus.INVALID, "Skill could not be parsed"

    # 1. Fatal errors ALWAYS invalidate first: unreadable, syntax errors in YAML
    if entry.parse_status == ParseStatus.UNREADABLE.value:
        return LoadabilityStatus.INVALID, "Unreadable skill content"
    if entry.parse_status == ParseStatus.MALFORMED_YAML.value and (
        parse.errors and any("malformed_yaml" in str(e) for e in parse.errors)
    ):
        return LoadabilityStatus.INVALID, "Malformed frontmatter YAML"

    # 2. Check root loadability and verification boundaries
    if hit is not None:
        root = agent.root_by_id(hit.root_id)
        if (
            (root is not None and getattr(root, "loadability", None) in ("unknown", "unverified"))
            or hit.evidence == "inferred"
            or hit.root_id == "omp_agent"
        ):
            return LoadabilityStatus.UNKNOWN, "Search root vendor loadability is unverified"

    # 3. Check for missing frontmatter
    if "missing_frontmatter" in (parse.errors or ()) or (
        parse.errors and ERR_MISSING_FRONTMATTER in parse.errors
    ):
        if agent.id == "opencode":
            return (
                LoadabilityStatus.LOADABLE,
                "OpenCode V2 supports skills without frontmatter",
            )
        return LoadabilityStatus.INVALID, "Missing frontmatter fence"

    # 4. Check for missing description
    if entry.parse_status == ParseStatus.MISSING_DESCRIPTION.value or (
        parse.errors and ERR_MISSING_DESCRIPTION in parse.errors
    ):
        if agent.id == "claude":
            return (
                LoadabilityStatus.LOADABLE,
                "Claude supports optional description with body-line fallback",
            )
        if agent.id == "opencode":
            return (
                LoadabilityStatus.LOADABLE,
                "OpenCode V2 supports optional description (manual invocation only)",
            )
        if agent.id == "omp":
            root_id = hit.root_id if hit else ""
            if root_id == "omp_project" or "managed" in root_id or root_id == "omp_agent":
                return LoadabilityStatus.INVALID, "OMP native provider requires description"
            return (
                LoadabilityStatus.LOADABLE,
                "OMP foreign provider roots support optional description",
            )
        return LoadabilityStatus.INVALID, f"{agent.name} requires description"

    # 4. Check for missing frontmatter
    if parse.errors and ERR_MISSING_FRONTMATTER in parse.errors:
        if agent.id == "opencode":
            return (
                LoadabilityStatus.LOADABLE,
                "OpenCode V2 supports skills without frontmatter",
            )
        return LoadabilityStatus.INVALID, "Missing frontmatter fence"

    return LoadabilityStatus.LOADABLE, None


# --- 5. Unified Resolved Agent Controls -----------------------------------


def _opencode_pattern_matches(pattern: str, text: str) -> bool:
    """Match OpenCode resource pattern against skill ID.

    Only '*' and '?' are wildcards ('*' matches 0+ chars, '?' matches 1 char).
    All other characters (including '[', ']', '(', ')', '.', etc.) are literal.
    """
    regex_parts = ["^"]
    for ch in pattern:
        if ch == "*":
            regex_parts.append(".*")
        elif ch == "?":
            regex_parts.append(".")
        else:
            regex_parts.append(re.escape(ch))
    regex_parts.append("$")
    return bool(re.match("".join(regex_parts), text))


OPENCODE_BOUNDED_DISCLOSURE_NOTE = (
    "OpenCode evaluation assumes base 'build' agent in a new session; "
    "system/managed configuration locations, system skills, existing-session selections, "
    "and agent-specific policies are omitted from runtime modeling, which may affect "
    "permission and discovery confidence."
)


@dataclass(frozen=True, slots=True)
class ResolvedAgentControls:
    """Immutable resolved controls for an agent across its configuration stack."""

    agent_id: str
    disabled_names: frozenset[str] = frozenset()
    claude_settings: MappingProxyType[str, str | bool] | None = None
    codex_disabled_paths: MappingProxyType[str, bool] | None = None
    opencode_rules: tuple[OpenCodePermissionRule, ...] = ()
    unsupported_controls: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.agent_id == "opencode" and OPENCODE_BOUNDED_DISCLOSURE_NOTE not in self.notes:
            object.__setattr__(self, "notes", (OPENCODE_BOUNDED_DISCLOSURE_NOTE, *self.notes))

    def evaluate_opencode_permission(self, skill_name: str) -> PermissionEffect:
        """Evaluate OpenCode V2 permissions using 'last matching rule wins'."""
        if not self.opencode_rules:
            return PermissionEffect.ALLOW
        last_match: str | None = None
        for rule in self.opencode_rules:
            if _opencode_pattern_matches(rule.resource, skill_name):
                last_match = rule.effect
        if last_match == "deny":
            return PermissionEffect.DENY
        if last_match == "ask":
            return PermissionEffect.ASK
        return PermissionEffect.ALLOW

    def is_codex_path_disabled(
        self,
        entrypoint_path: str,
        canonical_path: str | None = None,
        home: Path | None = None,
    ) -> bool:
        """Evaluate Codex disabled paths using pure string lexical matching.

        NO filesystem I/O, stat, resolve, or is_dir calls are made at evaluation time.
        """
        if not self.codex_disabled_paths:
            return False

        cands = [entrypoint_path]
        if not entrypoint_path.endswith("/SKILL.md"):
            cands.append(f"{entrypoint_path}/SKILL.md")
        else:
            cands.append(entrypoint_path.rsplit("/SKILL.md", 1)[0])

        if canonical_path:
            cands.append(canonical_path)
            if not canonical_path.endswith("/SKILL.md"):
                cands.append(f"{canonical_path}/SKILL.md")
            else:
                cands.append(canonical_path.rsplit("/SKILL.md", 1)[0])

        return any(self.codex_disabled_paths.get(c) is False for c in cands)


def _ancestor_chain(cwd: Path, boundary: Path | None) -> list[Path]:
    chain: list[Path] = []
    current = cwd
    while True:
        chain.append(current)
        if (boundary is not None and current == boundary) or current.parent == current:
            break
        current = current.parent
    return list(reversed(chain))


def collect_agent_config_paths(
    agent: AgentDefinition,
    home: Path,
    cwd: Path,
) -> list[Path]:
    """Collect all config file paths relevant to an agent in deterministic evaluation order."""
    if agent.id == "opencode":
        boundary = paths.get_sandbox()
        ancestors = _ancestor_chain(cwd, boundary)
    else:
        boundary = find_walk_boundary(cwd, agent.walk_boundary)
        ancestors = _ancestor_chain(cwd, boundary)
    paths_list: list[Path] = []

    if agent.id == "claude":
        # 1. User settings
        paths_list.append(home / ".claude" / "settings.json")
        # 2. Project settings (boundary down to cwd)
        for d in ancestors:
            paths_list.append(d / ".claude" / "settings.json")
        # 3. Local settings (boundary down to cwd)
        for d in ancestors:
            paths_list.append(d / ".claude" / "settings.local.json")

    elif agent.id == "codex":
        paths_list.append(home / ".codex" / "config.toml")

    elif agent.id == "opencode":
        # 1. Global configs
        xdg_base = paths.xdg_config_home()
        paths_list.extend(
            [
                xdg_base / "opencode" / "opencode.json",
                xdg_base / "opencode" / "opencode.jsonc",
                home / ".opencode" / "opencode.json",
                home / ".opencode" / "opencode.jsonc",
            ]
        )
        # 2. Project direct configs (farthest down to closest)
        for d in ancestors:
            paths_list.append(d / "opencode.json")
            paths_list.append(d / "opencode.jsonc")
        # 3. Project hidden .opencode configs (farthest down to closest)
        for d in ancestors:
            paths_list.append(d / ".opencode" / "opencode.json")
            paths_list.append(d / ".opencode" / "opencode.jsonc")

    elif agent.disabled_settings:
        paths_list.append(home / agent.disabled_settings)

    seen: set[Path] = set()
    deduped: list[Path] = []
    for p in paths_list:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    return deduped


def collect_all_config_paths(
    registry: Mapping[str, AgentDefinition],
    home: Path,
    cwd: Path,
) -> list[Path]:
    """Collect all config file paths for all registered agents plus installer lockfile."""
    all_paths: list[Path] = [installer_lockfile(home)]
    for agent in registry.values():
        all_paths.extend(collect_agent_config_paths(agent, home, cwd))
    seen: set[Path] = set()
    deduped: list[Path] = []
    for p in all_paths:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    return deduped


def resolve_agent_controls(
    agent: AgentDefinition,
    home: Path,
    cwd: Path,
    config_inputs: Mapping[str, CapturedInput] | None = None,
) -> ResolvedAgentControls:
    """Resolve unified configuration controls for an agent from captured or live inputs."""
    disabled: set[str] = set()
    errors: list[str] = []
    notes: list[str] = []
    unsupported: list[str] = []
    claude_settings_map: dict[str, str | bool] | None = None
    codex_paths_map: dict[str, bool] | None = None
    opencode_rules_list: list[OpenCodePermissionRule] = []

    def get_input(path: Path) -> tuple[bytes | None, str | None]:
        path_str = str(path)
        if config_inputs is not None:
            ci = config_inputs.get(path_str)
            if ci is None:
                return None, "missing"
            return ci.data, ci.error
        try:
            if not path.is_file():
                return None, "missing"
            return path.read_bytes(), None
        except OSError:
            return None, "unreadable"

    if agent.id == "opencode":
        boundary = paths.get_sandbox()
        ancestors = _ancestor_chain(cwd, boundary)
    else:
        boundary = find_walk_boundary(cwd, agent.walk_boundary)
        ancestors = _ancestor_chain(cwd, boundary)

    # 1. Claude
    if agent.id == "claude":
        claude_settings_map = {}
        # Precedence stack: User -> Project (boundary down to cwd) -> Local (boundary down to cwd)
        user_p = home / ".claude" / "settings.json"
        u_bytes, u_err = get_input(user_p)
        if u_err == "unreadable":
            errors.append(f"Unreadable user settings: {user_p}")
            notes.append(f"Settings file '{user_p}' could not be read.")
        elif u_bytes is not None:
            u_dict, dec_err = decode_claude_settings_with_status(u_bytes)
            if dec_err:
                errors.append(f"Malformed user settings: {user_p}")
                notes.append(
                    f"Settings file '{user_p}' is malformed; configuration confidence is unknown."
                )
            claude_settings_map.update(u_dict)

        for d in ancestors:
            proj_p = d / ".claude" / "settings.json"
            p_bytes, p_err = get_input(proj_p)
            if p_err == "unreadable":
                errors.append(f"Unreadable project settings: {proj_p}")
                notes.append(f"Settings file '{proj_p}' could not be read.")
            elif p_bytes is not None:
                p_dict, dec_err = decode_claude_settings_with_status(p_bytes)
                if dec_err:
                    errors.append(f"Malformed project settings: {proj_p}")
                    notes.append(
                        f"Settings file '{proj_p}' is malformed; "
                        f"configuration confidence is unknown."
                    )
                claude_settings_map.update(p_dict)

        for d in ancestors:
            loc_p = d / ".claude" / "settings.local.json"
            l_bytes, l_err = get_input(loc_p)
            if l_err == "unreadable":
                errors.append(f"Unreadable local settings: {loc_p}")
                notes.append(f"Settings file '{loc_p}' could not be read.")
            elif l_bytes is not None:
                l_dict, dec_err = decode_claude_settings_with_status(l_bytes)
                if dec_err:
                    errors.append(f"Malformed local settings: {loc_p}")
                    notes.append(
                        f"Settings file '{loc_p}' is malformed; "
                        f"configuration confidence is unknown."
                    )
                claude_settings_map.update(l_dict)

        for name, val in claude_settings_map.items():
            if val is False or val == "off":
                disabled.add(name)

    # 2. Codex
    elif agent.id == "codex":
        codex_paths_map = {}
        codex_p = home / ".codex" / "config.toml"
        c_bytes, c_err = get_input(codex_p)
        if c_err == "unreadable":
            errors.append(f"Unreadable codex config: {codex_p}")
            notes.append(f"Codex config at '{codex_p}' could not be read.")
        elif c_bytes is not None:
            raw_map, unsup, dec_err = decode_codex_config_with_status(c_bytes)
            unsupported.extend(unsup)
            if dec_err:
                errors.append(f"Malformed codex config: {codex_p}")
                notes.append(
                    f"Config file '{codex_p}' is malformed; configuration confidence is unknown."
                )
            for p_str, en in raw_map.items():
                if en is False:
                    if not os.path.isabs(p_str):
                        unsupported.append("Relative path in Codex config is unsupported")
                        notes.append(
                            f"Relative path in Codex config is unsupported ('{codex_p}'); "
                            f"configuration confidence is unknown."
                        )
                        continue
                    norm = os.path.normpath(p_str)
                    codex_paths_map[norm] = False
                    if norm.endswith("/SKILL.md"):
                        codex_paths_map[os.path.dirname(norm)] = False
                    else:
                        codex_paths_map[os.path.join(norm, "SKILL.md")] = False
                    try:
                        real = str(Path(norm).resolve())
                        codex_paths_map[real] = False
                        if real.endswith("/SKILL.md"):
                            codex_paths_map[os.path.dirname(real)] = False
                        else:
                            codex_paths_map[os.path.join(real, "SKILL.md")] = False
                    except (OSError, RuntimeError):
                        unsupported_msg = "Unresolvable path in Codex config is unsupported"
                        if unsupported_msg not in unsupported:
                            unsupported.append(unsupported_msg)
                        note_msg = (
                            f"Path in Codex config could not be resolved ('{codex_p}'); "
                            f"configuration confidence is unknown."
                        )
                        if note_msg not in notes:
                            notes.append(note_msg)
                    disabled.add(norm)

    # 3. OpenCode V2
    elif agent.id == "opencode":
        notes.append(OPENCODE_BOUNDED_DISCLOSURE_NOTE)
        xdg_base = paths.xdg_config_home()
        global_cands = [
            xdg_base / "opencode" / "opencode.json",
            xdg_base / "opencode" / "opencode.jsonc",
            home / ".opencode" / "opencode.json",
            home / ".opencode" / "opencode.jsonc",
        ]
        for gc in global_cands:
            g_bytes, g_err = get_input(gc)
            if g_err == "unreadable":
                errors.append(f"Unreadable OpenCode global config: {gc}")
                notes.append(f"Config file '{gc}' could not be read.")
            elif g_bytes is not None:
                rules, unsup, dec_err = decode_opencode_permissions_with_status(g_bytes)
                unsupported.extend(unsup)
                if dec_err:
                    errors.append(f"Malformed OpenCode global config: {gc}")
                    notes.append(
                        f"Config file '{gc}' is malformed; configuration confidence is unknown."
                    )
                opencode_rules_list.extend(rules)

        # Layer 1: ALL direct project configs farthest->closest
        for ad in ancestors:
            for cand in (ad / "opencode.json", ad / "opencode.jsonc"):
                d_bytes, d_err = get_input(cand)
                if d_err == "unreadable":
                    errors.append(f"Unreadable OpenCode project config: {cand}")
                    notes.append(f"Config file '{cand}' could not be read.")
                elif d_bytes is not None:
                    rules, unsup, dec_err = decode_opencode_permissions_with_status(d_bytes)
                    unsupported.extend(unsup)
                    if dec_err:
                        errors.append(f"Malformed OpenCode project config: {cand}")
                        notes.append(
                            f"Config file '{cand}' is malformed; "
                            f"configuration confidence is unknown."
                        )
                    opencode_rules_list.extend(rules)

        # Layer 2: ALL hidden .opencode directory configs farthest->closest
        for ad in ancestors:
            for cand in (ad / ".opencode" / "opencode.json", ad / ".opencode" / "opencode.jsonc"):
                d_bytes, d_err = get_input(cand)
                if d_err == "unreadable":
                    errors.append(f"Unreadable OpenCode directory config: {cand}")
                    notes.append(f"Config file '{cand}' could not be read.")
                elif d_bytes is not None:
                    rules, unsup, dec_err = decode_opencode_permissions_with_status(d_bytes)
                    unsupported.extend(unsup)
                    if dec_err:
                        errors.append(f"Malformed OpenCode directory config: {cand}")
                        notes.append(
                            f"Config file '{cand}' is malformed; "
                            f"configuration confidence is unknown."
                        )
                    opencode_rules_list.extend(rules)

        if unsupported:
            for u in unsupported:
                notes.append(f"Unsupported OpenCode configuration detected: {u}")

    # 4. Standard agent.disabled_settings
    elif agent.disabled_settings:
        sett_p = home / agent.disabled_settings
        d_bytes, d_err = get_input(sett_p)
        if d_err == "unreadable":
            errors.append(f"Unreadable settings: {sett_p}")
            notes.append(f"Settings file '{sett_p}' could not be read.")
        elif d_bytes is not None and agent.disabled_key:
            try:
                parsed = json.loads(d_bytes.decode("utf-8"))
                if isinstance(parsed, dict) and isinstance(parsed.get(agent.disabled_key), dict):
                    for k, v in parsed[agent.disabled_key].items():
                        if v is False or v == "off":
                            disabled.add(str(k))
            except (UnicodeDecodeError, ValueError):
                errors.append(f"Malformed settings: {sett_p}")
                notes.append(
                    f"Settings file '{sett_p}' is malformed; configuration confidence is unknown."
                )

    return ResolvedAgentControls(
        agent_id=agent.id,
        disabled_names=frozenset(disabled),
        claude_settings=MappingProxyType(claude_settings_map)
        if claude_settings_map is not None
        else None,
        codex_disabled_paths=MappingProxyType(codex_paths_map)
        if codex_paths_map is not None
        else None,
        opencode_rules=tuple(opencode_rules_list),
        unsupported_controls=tuple(unsupported),
        errors=tuple(errors),
        notes=tuple(notes),
    )


# --- 6. Effective Invocation & Permission Controls -------------------------


@dataclass(frozen=True, slots=True)
class ResolvedCandidateControls:
    """Resolved invocation policy, permission effect, and override state for a candidate."""

    is_disabled: bool
    invocation: InvocationPolicy
    permission: PermissionEffect
    qualification: str | None = None


def resolve_candidate_controls(
    agent: AgentDefinition,
    entry: DiscoveredEntry,
    hit: RootHit | None,
    hit_names: set[str],
    *,
    controls: ResolvedAgentControls | None = None,
    claude_settings: dict[str, str | bool] | None = None,
    codex_disabled_paths: dict[str, bool] | None = None,
    opencode_permissions: dict[str, str] | None = None,
    captured_disabled_overrides: frozenset[str] | None = None,
) -> ResolvedCandidateControls:
    """Determine effective invocation, permission, and disabled state for a candidate hit."""
    entrypoint_path = hit.entrypoint_path if hit else entry.entrypoint_path
    canonical_path = entry.canonical_path if entry.canonical is not None else entrypoint_path

    # Construct unified controls if not provided
    if controls is None:
        disabled_names_set = set(captured_disabled_overrides or ())
        controls = ResolvedAgentControls(
            agent_id=agent.id,
            disabled_names=frozenset(disabled_names_set),
            claude_settings=MappingProxyType(claude_settings)
            if claude_settings is not None
            else None,
            codex_disabled_paths=MappingProxyType(codex_disabled_paths)
            if codex_disabled_paths is not None
            else None,
            opencode_rules=tuple(
                OpenCodePermissionRule(resource=k, effect=v)
                for k, v in (opencode_permissions or {}).items()
            ),
        )

    # Check explicit custom API disabled_overrides first
    overrides = captured_disabled_overrides
    if (
        overrides is None
        and controls is not None
        and controls.claude_settings is None
        and controls.disabled_names
    ):
        overrides = controls.disabled_names

    if overrides is not None and overrides:
        if bool(hit_names & overrides):
            return ResolvedCandidateControls(
                is_disabled=True,
                invocation=InvocationPolicy.NONE,
                permission=PermissionEffect.DENY,
                qualification="Disabled by agent configuration",
            )
        if entrypoint_path in overrides or (canonical_path and canonical_path in overrides):
            return ResolvedCandidateControls(
                is_disabled=True,
                invocation=InvocationPolicy.NONE,
                permission=PermissionEffect.DENY,
                qualification="Disabled by agent configuration path",
            )

    has_config_error = bool(controls.errors) or bool(controls.unsupported_controls)

    # 1. Claude
    if agent.id == "claude":
        alias = entrypoint_alias(entrypoint_path, hit.is_file if hit else entry.is_file)
        command_name = (
            entry.parse.frontmatter_name if entry.parse and entry.parse.frontmatter_name else alias
        )
        val = (
            controls.claude_settings.get(command_name)
            if controls.claude_settings is not None
            else None
        )

        if (
            val is False
            or val == "off"
            or (controls.claude_settings is None and command_name in controls.disabled_names)
        ):
            return ResolvedCandidateControls(
                is_disabled=True,
                invocation=InvocationPolicy.NONE,
                permission=PermissionEffect.DENY,
                qualification="Disabled by Claude settings",
            )

        inv = InvocationPolicy.ALL
        if val == "user-invocable-only":
            inv = InvocationPolicy.USER_ONLY
        elif val == "name-only":
            inv = InvocationPolicy.NAME_ONLY
        elif val is True or val == "on":
            inv = InvocationPolicy.ALL
        else:
            fm = (
                entry.parse.frontmatter
                if entry.parse and isinstance(entry.parse.frontmatter, dict)
                else {}
            )
            if fm.get("user-invocable") is False or fm.get("userInvocable") is False:
                inv = InvocationPolicy.MODEL_ONLY
            elif (
                fm.get("disable-model-invocation") is True
                or fm.get("disableModelInvocation") is True
            ):
                inv = InvocationPolicy.USER_ONLY

        perm = PermissionEffect.UNKNOWN if has_config_error else PermissionEffect.ALLOW
        return ResolvedCandidateControls(
            is_disabled=False,
            invocation=inv,
            permission=perm,
        )

    # 2. Codex
    if agent.id == "codex":
        if controls.is_codex_path_disabled(entrypoint_path, canonical_path):
            return ResolvedCandidateControls(
                is_disabled=True,
                invocation=InvocationPolicy.NONE,
                permission=PermissionEffect.DENY,
                qualification="Disabled via Codex [[skills.config]]",
            )
        fm = (
            entry.parse.frontmatter
            if entry.parse and isinstance(entry.parse.frontmatter, dict)
            else {}
        )
        inv = (
            InvocationPolicy.USER_ONLY
            if (
                fm.get("disable-model-invocation") is True
                or fm.get("disableModelInvocation") is True
            )
            else InvocationPolicy.ALL
        )
        perm = PermissionEffect.UNKNOWN if has_config_error else PermissionEffect.ALLOW
        return ResolvedCandidateControls(
            is_disabled=False,
            invocation=inv,
            permission=perm,
        )

    # 3. OpenCode V2
    if agent.id == "opencode":
        hit_id = entrypoint_alias(entrypoint_path, hit.is_file if hit else entry.is_file)
        eff = controls.evaluate_opencode_permission(hit_id)
        if eff is PermissionEffect.DENY:
            return ResolvedCandidateControls(
                is_disabled=True,
                invocation=InvocationPolicy.NONE,
                permission=PermissionEffect.DENY,
                qualification="Denied by OpenCode skill permission",
            )

        fm = (
            entry.parse.frontmatter
            if (entry.parse is not None and isinstance(entry.parse.frontmatter, dict))
            else {}
        )
        raw_meta = fm.get("metadata") if isinstance(fm, dict) else None
        meta = raw_meta if isinstance(raw_meta, dict) else {}
        autoinvoke = meta.get("opencode/autoinvoke")
        if autoinvoke is None:
            autoinvoke = meta.get("autoinvoke")
        if autoinvoke is None:
            autoinvoke = fm.get("autoinvoke")

        has_desc = bool(entry.parse and entry.parse.description)
        if not has_desc:
            # Missing description precludes model advertisement even if autoinvoke is true
            inv = InvocationPolicy.USER_ONLY
        elif autoinvoke is True:
            # Metadata autoinvoke boolean true outranks disable-model-invocation
            # only when description exists
            inv = InvocationPolicy.ALL
        elif autoinvoke is False:
            inv = InvocationPolicy.USER_ONLY
        elif autoinvoke is not None and not isinstance(autoinvoke, bool):
            inv = InvocationPolicy.UNKNOWN
        elif fm.get("disable-model-invocation") is True or fm.get("disableModelInvocation") is True:
            inv = InvocationPolicy.USER_ONLY
        else:
            inv = InvocationPolicy.ALL

        perm = PermissionEffect.UNKNOWN if has_config_error else eff
        return ResolvedCandidateControls(
            is_disabled=False,
            invocation=inv,
            permission=perm,
        )

    # 4. OMP
    if agent.id == "omp":
        fm = (
            entry.parse.frontmatter
            if entry.parse and isinstance(entry.parse.frontmatter, dict)
            else {}
        )
        if fm.get("enabled") is False or bool(hit_names & controls.disabled_names):
            return ResolvedCandidateControls(
                is_disabled=True,
                invocation=InvocationPolicy.NONE,
                permission=PermissionEffect.DENY,
                qualification="Disabled via frontmatter enabled: false",
            )
        inv = InvocationPolicy.ALL
        if (
            fm.get("hide") is True
            or fm.get("disable-model-invocation") is True
            or fm.get("disableModelInvocation") is True
        ):
            inv = InvocationPolicy.USER_ONLY
        perm = PermissionEffect.UNKNOWN if has_config_error else PermissionEffect.ALLOW
        return ResolvedCandidateControls(
            is_disabled=False,
            invocation=inv,
            permission=perm,
        )

    # Other agents
    if bool(hit_names & controls.disabled_names):
        return ResolvedCandidateControls(
            is_disabled=True,
            invocation=InvocationPolicy.NONE,
            permission=PermissionEffect.DENY,
        )
    fm = (
        entry.parse.frontmatter if entry.parse and isinstance(entry.parse.frontmatter, dict) else {}
    )
    inv = (
        InvocationPolicy.USER_ONLY
        if (fm.get("disable-model-invocation") is True or fm.get("disableModelInvocation") is True)
        else InvocationPolicy.ALL
    )
    perm = PermissionEffect.UNKNOWN if has_config_error else PermissionEffect.ALLOW
    return ResolvedCandidateControls(
        is_disabled=False,
        invocation=inv,
        permission=perm,
    )
