"""Phase 0.5 Gate: fixture inventory reconciliation.

The specification's acceptance gate for Phase 0.5 is to prove that the tool
models one canonical library plus N symlink entrypoints -- rather than N
duplicate installations. Until the Phase 1 parser and Phase 2 resolver exist,
this test performs the reconciliation directly over the acceptance farm using
only the frozen contracts, so the gate is enforced from day one.

Phase 2 will replace the local walk below with ``resolve`` / ``scan`` output;
the assertion shape lives here permanently.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from skill_lens.models import ParseStatus, Scope, SkillInstallation, dumps
from tests.fixtures import farm


def _skill_entries(home: Path) -> list[Path]:
    """Enumerate skill entrypoints without following symlinked directories.

    pathlib's ``rglob`` refuses to descend through symlinked directories, so we
    list each known skills root explicitly -- exactly like the live scanner
    will. A symlink entry is itself the installation; its target is canonical.
    """
    entries: list[Path] = []
    for root in sorted(p for p in home.rglob("skills") if p.is_dir() and not p.is_symlink()):
        try:
            children = list(root.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_symlink():
                entries.append(child)
            elif child.is_dir():
                if child.name == ".system":
                    entries.extend(sorted(p for p in child.iterdir() if p.is_dir()))
                else:
                    entries.append(child)
            elif child.suffix == ".md":
                entries.append(child)
    return entries


def _inventory(home: Path) -> list[SkillInstallation]:
    """Minimal structural inventory of the acceptance farm.

    Deliberately simple: it only canonicalizes paths and groups entrypoints.
    Full frontmatter parsing and hashing arrive in Phase 1.
    """
    by_target: dict[Path, SkillInstallation] = {}
    for entrypoint in _skill_entries(home):
        canonical = entrypoint.resolve()
        is_symlink = entrypoint.is_symlink()

        scope = Scope.USER
        rel = entrypoint.relative_to(home)
        if rel.parts and rel.parts[0] == "project":
            scope = Scope.PROJECT
        elif ".system" in rel.parts:
            scope = Scope.SYSTEM
        elif ".tmp" in rel.parts and "plugins" in rel.parts:
            scope = Scope.PLUGIN

        existing = by_target.get(canonical)
        if existing is None:
            by_target[canonical] = SkillInstallation(
                name=entrypoint.name if entrypoint.suffix != ".md" else entrypoint.stem,
                entrypoint_path=str(entrypoint),
                canonical_path=str(canonical),
                scope=scope,
                parse_status=ParseStatus.VALID,
                is_symlink=is_symlink,
                agent_entrypoints=(str(entrypoint),),
            )
        elif str(entrypoint) not in existing.agent_entrypoints:
            by_target[canonical] = dataclasses.replace(
                existing,
                is_symlink=existing.is_symlink or is_symlink,
                agent_entrypoints=(*existing.agent_entrypoints, str(entrypoint)),
            )
    return list(by_target.values())


def test_gate_one_canonical_library_many_entrypoints(mock_home: Path) -> None:
    farm.build_acceptance_farm(mock_home)
    inventory = _inventory(mock_home)

    user_canonical = [
        i
        for i in inventory
        if i.scope is Scope.USER and i.canonical_path.startswith(str(mock_home / ".agents"))
    ]
    assert len(user_canonical) == len(farm.CANONICAL_SKILLS), (
        "each canonical skill must appear exactly once, regardless of symlink count"
    )

    symlink_entrypoints = [
        ep for i in inventory for ep in i.agent_entrypoints if Path(ep).is_symlink()
    ]
    assert len(symlink_entrypoints) == farm.canonical_entrypoint_count()

    # The canonical source dir is itself a searched root for some agents, so
    # it appears as an entrypoint too. The farm links are the symlinked ones.
    farm_links = [
        i
        for i in inventory
        if i.is_symlink
        and i.scope is Scope.USER
        and i.canonical_path.startswith(str(mock_home / ".agents"))
    ]
    assert len(farm_links) == len(farm.CANONICAL_SKILLS)
    for install in farm_links:
        symlink_eps = [ep for ep in install.agent_entrypoints if Path(ep).is_symlink()]
        assert len(symlink_eps) == len(farm.AGENT_FARMS)


def test_gate_scope_separation(mock_home: Path) -> None:
    farm.build_acceptance_farm(mock_home)
    inventory = _inventory(mock_home)
    scopes = {i.scope for i in inventory}
    assert {Scope.USER, Scope.PROJECT, Scope.SYSTEM} <= scopes
    assert len(inventory) == (
        len(farm.CANONICAL_SKILLS) + 3  # system, project, plugin
    )


def test_gate_output_is_json_serializable(mock_home: Path) -> None:
    farm.build_acceptance_farm(mock_home)
    payload = [i.to_dict() for i in _inventory(mock_home)]
    encoded = dumps(payload)
    assert json.loads(encoded) == json.loads(json.dumps(payload, sort_keys=True, indent=2))
