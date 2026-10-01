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


def test_no_agent_claims_verified_evidence_without_a_source() -> None:
    """Evidence is only meaningful when it can be checked.

    Before Phase 6 this repository asserted that two agents were ``inferred``,
    which was true but weak: it pinned a moment rather than a rule, and it would
    have kept passing if a *third* agent quietly claimed ``documented`` with no
    citation at all.

    The invariant replaces it. ``documented`` and ``empirical`` both assert that
    somebody looked at the agent's real behaviour, so both require a ``source``
    URL pointing at primary documentation. ``inferred`` requires nothing -- that
    is the whole point of it, and it is the honest label for an agent Skill Lens
    cannot cite.
    """
    for agent in list_agents():
        if agent.policy_evidence in (Evidence.DOCUMENTED, Evidence.EMPIRICAL):
            assert agent.source.strip(), (
                f"agent '{agent.id}' claims {agent.policy_evidence.value} evidence "
                "but has no source; cite the vendor docs or downgrade to inferred "
                "(AGENTS.md rule 6: provenance over hallucination)"
            )


def test_documented_source_must_be_a_real_url() -> None:
    """A source that is not a URL is a citation in appearance only."""
    for agent in list_agents():
        if agent.policy_evidence in (Evidence.DOCUMENTED, Evidence.EMPIRICAL):
            assert agent.source.startswith(("http://", "https://")), (
                f"agent '{agent.id}' has a non-URL source: {agent.source!r}"
            )


def test_no_root_claims_documented_evidence_without_a_citable_agent() -> None:
    """A root marked ``documented`` must inherit a real citation.

    The agent's *policy* level is deliberately not the test here. ``antigravity``
    and ``codex`` are ``empirical`` overall while individual roots are
    ``documented``, and that is legitimate: a vendor document can establish one
    search path without establishing the whole collision policy. The rule that
    actually prevents hallucination is narrower and stricter -- if you claim a
    root is documented, the definition must carry a URL someone can open.
    """
    for agent in list_agents():
        for root in agent.roots:
            if root.evidence is Evidence.DOCUMENTED:
                assert agent.source.strip().startswith(("http://", "https://")), (
                    f"agent '{agent.id}' root '{root.id}' claims documented evidence "
                    f"but the agent has no citable source: {agent.source!r}"
                )


def test_no_agent_invents_a_collision_winner_when_inferred() -> None:
    """Inferred agents must not claim a documented winner."""
    for agent in list_agents():
        if agent.policy_evidence is Evidence.INFERRED:
            assert agent.coexist_policy != "shadow", (
                f"{agent.id} claims shadow precedence without evidence"
            )


def test_dsh_declares_every_documented_root(tmp_path: Path) -> None:
    """Regression: Phase 6 found dsh was missing both user-level roots.

    The registry knew only the two project roots and a plugin root, so it could
    not see ``~/.dsh/skills`` or ``~/.agents/skills`` -- the two places a real
    dsh user's skills actually live. This pins the documented rank order so the
    omission cannot come back.

    Upstream ranks are inverted relative to Skill Lens (see dsh.toml), so the
    assertion is on the *relative order*, which is what the docs actually
    guarantee.
    """
    dsh = load_agent("dsh")
    by_id = {root.id: root for root in dsh.roots}
    assert {"dsh_project", "dsh_project_agents", "dsh_user", "dsh_shared_global"} <= set(by_id)

    assert by_id["dsh_project"].path == ".dsh/skills"
    assert by_id["dsh_project"].scope is Scope.PROJECT
    assert by_id["dsh_user"].path == ".dsh/skills"
    assert by_id["dsh_user"].scope is Scope.USER
    assert by_id["dsh_shared_global"].path == ".agents/skills"
    assert by_id["dsh_shared_global"].scope is Scope.USER

    # Documented order: project-dsh > project-agents > user-dsh > user-agents,
    # which Skill Lens expresses as descending numbers.
    assert (
        by_id["dsh_project"].rank
        > by_id["dsh_project_agents"].rank
        > by_id["dsh_user"].rank
        > by_id["dsh_shared_global"].rank
    )
    assert dsh.policy_evidence is Evidence.DOCUMENTED


def test_omp_managed_skills_rank_below_authored_ones() -> None:
    """Regression: Phase 6 found ``.omp/agent`` was ranked above authored roots.

    Upstream documents the ``omp-managed`` provider at priority 5 of nine and
    states it "always defers to a same-named authored skill". The registry
    ranked it at 70 -- claiming the opposite. This pins the corrected ordering.
    """
    omp = load_agent("omp")
    by_id = {root.id: root for root in omp.roots}
    managed = by_id["omp_agent"]
    assert managed.rank < by_id["omp_shared_global"].rank
    assert managed.rank < by_id["omp_project"].rank
    assert managed.rank < by_id["omp_project_agents"].rank
    assert omp.policy_evidence is Evidence.DOCUMENTED


def test_omp_under_claims_rather_than_over_claims_coexistence() -> None:
    """omp namespaces its losers; this tool cannot say so, so it under-claims.

    Upstream documents that a differing same-named variant survives under a
    ``<namespace>/<name>`` suffix. The vocabulary here is shadow / merge /
    ambiguous, and none of them means namespaced: ``shadow`` would claim the
    loser is suppressed, ``merge`` would print "no documented winner" when a
    winner *is* documented. ``ambiguous`` under-claims instead, which is the
    correct direction of error. Pinned so nobody "fixes" it into a false
    statement.
    """
    omp = load_agent("omp")
    assert omp.coexist_policy == "ambiguous"
    assert omp.policy_evidence is Evidence.DOCUMENTED


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
