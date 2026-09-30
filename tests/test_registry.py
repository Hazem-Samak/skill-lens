"""Tests for the agent registry loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_lens.models.enums import Evidence, Scope
from skill_lens.registry.loader import (
    list_agents,
    load_agent,
    load_agent_file,
    load_registry,
)

EXPECTED_AGENTS = {
    "antigravity",
    "claude",
    "codex",
    "dsh",
    "grok",
    "omp",
    "opencode",
    "pi",
    "qoder",
    "windsurf",
}


def test_all_agents_load() -> None:
    registry = load_registry()
    assert set(registry) == EXPECTED_AGENTS


def test_list_agents_sorted() -> None:
    ids = [agent.id for agent in list_agents()]
    assert ids == sorted(ids)


def test_unknown_agent_raises() -> None:
    with pytest.raises(KeyError, match="unknown agent"):
        load_agent("does-not-exist")


@pytest.mark.parametrize("agent_id", sorted(EXPECTED_AGENTS))
def test_every_agent_has_provenance(agent_id: str) -> None:
    agent = load_agent(agent_id)
    assert agent.policy_evidence in set(Evidence)
    assert agent.collision_policy
    assert agent.roots, "an agent must declare at least one root"


@pytest.mark.parametrize("agent_id", sorted(EXPECTED_AGENTS))
def test_every_root_has_rule_id_and_evidence(agent_id: str) -> None:
    agent = load_agent(agent_id)
    for root in agent.roots:
        assert root.rule_id, f"{agent_id}/{root.id} missing rule_id"
        assert root.evidence in set(Evidence)
        assert root.scope in set(Scope)
        assert isinstance(root.rank, int)


def test_claude_policy_is_documented() -> None:
    claude = load_agent("claude")
    assert claude.policy_evidence is Evidence.DOCUMENTED
    assert claude.identity_source == "directory_name"
    assert claude.disabled_rule_id == "claude_skill_override_disabled"


def test_claude_has_personal_and_project_roots() -> None:
    claude = load_agent("claude")
    kinds = {root.kind for root in claude.roots}
    assert {"global", "project"} <= kinds


def test_opencode_is_ambiguous() -> None:
    opencode = load_agent("opencode")
    assert opencode.coexist_policy == "ambiguous"
    assert opencode.ambiguous_rule_id == "opencode_duplicate_ambiguous"


def test_tier2_agents_are_inferred() -> None:
    for agent_id in ("omp", "dsh"):
        assert load_agent(agent_id).policy_evidence is Evidence.INFERRED


def test_no_agent_invents_a_collision_winner_when_inferred() -> None:
    """Inferred agents must not claim a documented winner."""
    for agent in list_agents():
        if agent.policy_evidence is Evidence.INFERRED:
            assert agent.coexist_policy != "shadow", (
                f"{agent.id} claims shadow precedence without evidence"
            )


def test_load_agent_file_from_custom_dir(tmp_path: Path) -> None:
    (tmp_path / "test.toml").write_text(
        """
id = "test"
name = "Test Agent"
      collision_policy = "Shadow"
      policy_evidence = "documented"
coexist_policy = "shadow"
walk_boundary = "git_root"
unsearched_rule_id = "test_roots"

[[roots]]
id = "test_global"
kind = "global"
path = ".test/skills"
scope = "user"
rank = 50
rule_id = "test_global"
evidence = "documented"
""",
        encoding="utf-8",
    )
    agent = load_agent_file(tmp_path / "test.toml")
    assert agent.id == "test"
    assert len(agent.roots) == 1
    assert agent.roots[0].rank == 50
