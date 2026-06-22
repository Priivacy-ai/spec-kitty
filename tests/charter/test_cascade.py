"""Unit tests for ``charter.cascade`` (WP11, T052).

Covers the pure cascade engine:

- T048 / Contract C3.3: :class:`CascadeScope` parsing — ``all`` shorthand,
  explicit kind set, and absent/empty → ``None`` (never all).
- T049 / FR-014: scoped cascade activation returns only in-scope kinds and
  reports skipped-by-scope kinds; ``all`` returns every referenced kind.
- T050 / FR-013 / Contract C3.2: no-cascade warning returns the skipped
  reference kinds plus a recovery hint.
- T051 / FR-015/016 / C-005 / Contract C3.4: shared-reference-safe deactivation
  removes exclusively-referenced artifacts and skips shared ones (named), using a
  diamond-reference graph for the shared case.
"""

from __future__ import annotations

import pytest

from charter.cascade import (
    REFERENCE_RELATIONS,
    CascadeScope,
    DeactivationPlan,
    NoCascadeReport,
    cascade_activation_targets,
    deactivation_plan,
    referenced_but_not_cascaded,
)
from doctrine.artifact_kinds import ArtifactKind, MissionTypeNotAnArtifactKind
from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Graph builders
# ---------------------------------------------------------------------------


def _node(urn: str, kind: NodeKind) -> DRGNode:
    return DRGNode(urn=urn, kind=kind)


def _edge(source: str, target: str, relation: Relation = Relation.REQUIRES) -> DRGEdge:
    return DRGEdge(source=source, target=target, relation=relation)


def _graph(nodes: list[DRGNode], edges: list[DRGEdge]) -> DRGGraph:
    return DRGGraph(
        schema_version="1.0",
        generated_at="2026-06-01T00:00:00Z",
        generated_by="test",
        nodes=nodes,
        edges=edges,
    )


def _profile_graph() -> DRGGraph:
    """An agent-profile that requires a tactic and suggests a directive.

    ``agent_profile:pedro`` --requires--> ``tactic:tdd``
    ``agent_profile:pedro`` --suggests--> ``directive:arch``
    """
    return _graph(
        nodes=[
            _node("agent_profile:pedro", NodeKind.AGENT_PROFILE),
            _node("tactic:tdd", NodeKind.TACTIC),
            _node("directive:arch", NodeKind.DIRECTIVE),
        ],
        edges=[
            _edge("agent_profile:pedro", "tactic:tdd", Relation.REQUIRES),
            _edge("agent_profile:pedro", "directive:arch", Relation.SUGGESTS),
        ],
    )


def _diamond_graph() -> DRGGraph:
    """Diamond: two profiles both reference a shared tactic; one also a private one.

    ``agent_profile:pedro`` --requires--> ``tactic:shared``
    ``agent_profile:renata`` --requires--> ``tactic:shared``
    ``agent_profile:pedro`` --requires--> ``tactic:private``
    """
    return _graph(
        nodes=[
            _node("agent_profile:pedro", NodeKind.AGENT_PROFILE),
            _node("agent_profile:renata", NodeKind.AGENT_PROFILE),
            _node("tactic:shared", NodeKind.TACTIC),
            _node("tactic:private", NodeKind.TACTIC),
        ],
        edges=[
            _edge("agent_profile:pedro", "tactic:shared", Relation.REQUIRES),
            _edge("agent_profile:renata", "tactic:shared", Relation.REQUIRES),
            _edge("agent_profile:pedro", "tactic:private", Relation.REQUIRES),
        ],
    )


# ---------------------------------------------------------------------------
# T048 — CascadeScope (Contract C3.3)
# ---------------------------------------------------------------------------


def test_scope_parse_all_shorthand() -> None:
    scope = CascadeScope.parse("all")
    assert scope is not None
    assert scope.is_all is True
    assert scope.selects(ArtifactKind.TACTIC) is True
    assert scope.selects(ArtifactKind.DIRECTIVE) is True


def test_scope_parse_explicit_kind_set() -> None:
    scope = CascadeScope.parse("agent-profile,tactic")
    assert scope is not None
    assert scope.is_all is False
    assert scope.kinds == frozenset({ArtifactKind.AGENT_PROFILE, ArtifactKind.TACTIC})
    assert scope.selects(ArtifactKind.TACTIC) is True
    assert scope.selects(ArtifactKind.DIRECTIVE) is False


def test_scope_parse_underscored_tokens_also_accepted() -> None:
    scope = CascadeScope.parse("agent_profile")
    assert scope is not None
    assert scope.kinds == frozenset({ArtifactKind.AGENT_PROFILE})


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_scope_parse_absent_means_no_cascade_not_all(raw: str | None) -> None:
    # Contract C3.3: absence of --cascade is None and NEVER means all.
    assert CascadeScope.parse(raw) is None


def test_scope_parse_unknown_token_raises_no_silent_fallback() -> None:
    with pytest.raises(ValueError, match="Unknown artifact kind token"):
        CascadeScope.parse("not-a-kind")


def test_scope_parse_mission_type_is_distinct_error() -> None:
    with pytest.raises(MissionTypeNotAnArtifactKind):
        CascadeScope.parse("mission-type")


def test_scope_rejects_both_all_and_kinds() -> None:
    with pytest.raises(ValueError, match="either the all-kind shorthand"):
        CascadeScope(is_all=True, kinds=frozenset({ArtifactKind.TACTIC}))


def test_scope_rejects_empty_explicit_set() -> None:
    with pytest.raises(ValueError, match="requires at least one kind"):
        CascadeScope(is_all=False, kinds=frozenset())


def test_reference_relations_are_requires_suggests_and_refines() -> None:
    # REFINES joined the cascade reference set in #2079 so a refinement edge is
    # traversed (not born inert like APPLIES); REQUIRES/SUGGESTS are the legacy set.
    assert (
        frozenset({Relation.REQUIRES, Relation.SUGGESTS, Relation.REFINES})
        == REFERENCE_RELATIONS
    )


# ---------------------------------------------------------------------------
# T049 — scoped cascade activation (FR-014)
# ---------------------------------------------------------------------------


def test_cascade_activation_scoped_to_selected_kinds() -> None:
    graph = _profile_graph()
    scope = CascadeScope.parse("tactic")
    assert scope is not None

    result = cascade_activation_targets(graph, "agent_profile:pedro", scope)

    # Only the tactic is activated; the directive is skipped-by-scope.
    assert result.activated == {"tactic": ["tdd"]}
    assert result.skipped_by_scope == {"directive": ["arch"]}


def test_cascade_activation_all_returns_every_referenced_kind() -> None:
    graph = _profile_graph()
    scope = CascadeScope.all()

    result = cascade_activation_targets(graph, "agent_profile:pedro", scope)

    assert result.activated == {"tactic": ["tdd"], "directive": ["arch"]}
    assert result.skipped_by_scope == {}


def test_cascade_activation_is_transitive() -> None:
    # pedro -> tactic:a -> tactic:b (transitive forward closure).
    graph = _graph(
        nodes=[
            _node("agent_profile:pedro", NodeKind.AGENT_PROFILE),
            _node("tactic:a", NodeKind.TACTIC),
            _node("tactic:b", NodeKind.TACTIC),
        ],
        edges=[
            _edge("agent_profile:pedro", "tactic:a"),
            _edge("tactic:a", "tactic:b"),
        ],
    )
    result = cascade_activation_targets(graph, "agent_profile:pedro", CascadeScope.all())
    assert result.activated == {"tactic": ["a", "b"]}


def test_cascade_follows_refines_edges() -> None:
    # #2079 behavioral guard (not just set membership): REFINES is a cascade
    # reference relation, so activating an artifact cascades to what it REFINES.
    # If REFINES were dropped from REFERENCE_RELATIONS / the traversal, tactic:refined
    # would not appear — this proves the wiring behaviorally, not just by constant.
    graph = _graph(
        nodes=[
            _node("tactic:base", NodeKind.TACTIC),
            _node("tactic:refined", NodeKind.TACTIC),
        ],
        edges=[_edge("tactic:base", "tactic:refined", Relation.REFINES)],
    )
    result = cascade_activation_targets(graph, "tactic:base", CascadeScope.all())
    assert result.activated == {"tactic": ["refined"]}


def test_cascade_activation_no_references_is_empty() -> None:
    graph = _graph([_node("tactic:lonely", NodeKind.TACTIC)], [])
    result = cascade_activation_targets(graph, "tactic:lonely", CascadeScope.all())
    assert result.activated == {}
    assert result.skipped_by_scope == {}


# ---------------------------------------------------------------------------
# T050 — no-cascade warning (FR-013, Contract C3.2)
# ---------------------------------------------------------------------------


def test_referenced_but_not_cascaded_lists_skipped_kinds() -> None:
    graph = _profile_graph()
    report = referenced_but_not_cascaded(graph, "agent_profile:pedro")

    assert isinstance(report, NoCascadeReport)
    assert report.source_urn == "agent_profile:pedro"
    assert report.skipped == {"tactic": ["tdd"], "directive": ["arch"]}
    assert report.has_skipped is True
    # Recovery hint names --cascade and the consistency check (Contract C3.2).
    assert "--cascade" in report.recovery_hint
    assert "consistency-check" in report.recovery_hint


def test_referenced_but_not_cascaded_empty_when_no_refs() -> None:
    graph = _graph([_node("tactic:lonely", NodeKind.TACTIC)], [])
    report = referenced_but_not_cascaded(graph, "tactic:lonely")
    assert report.skipped == {}
    assert report.has_skipped is False


# ---------------------------------------------------------------------------
# T051 — shared-reference-safe deactivation (FR-015/016, C-005, Contract C3.4)
# ---------------------------------------------------------------------------


def test_deactivation_removes_exclusive_skips_shared_diamond() -> None:
    graph = _diamond_graph()
    # Both pedro and renata are active. Deactivating pedro:
    #   - tactic:private is exclusive to pedro  -> deactivate
    #   - tactic:shared is still referenced by renata -> skip, name renata
    plan = deactivation_plan(
        graph,
        "agent_profile:pedro",
        CascadeScope.all(),
        active_urns={"agent_profile:pedro", "agent_profile:renata"},
    )

    assert isinstance(plan, DeactivationPlan)
    assert plan.deactivate == ["tactic:private"]
    assert len(plan.skipped_shared) == 1
    skip = plan.skipped_shared[0]
    assert skip.urn == "tactic:shared"
    assert skip.referencing_active_urn == "agent_profile:renata"


def test_deactivation_removes_all_when_no_other_active_source() -> None:
    graph = _diamond_graph()
    # Only pedro is active: both its references are exclusive (C-005 satisfied —
    # no shared artifact removed because none is shared).
    plan = deactivation_plan(
        graph,
        "agent_profile:pedro",
        CascadeScope.all(),
        active_urns={"agent_profile:pedro"},
    )
    assert plan.deactivate == ["tactic:private", "tactic:shared"]
    assert plan.skipped_shared == []


def test_deactivation_target_own_references_do_not_keep_candidate_alive() -> None:
    # Guard: target_urn is excluded from "remaining active sources", so its own
    # forward references never spuriously mark a candidate as shared.
    graph = _profile_graph()
    plan = deactivation_plan(
        graph,
        "agent_profile:pedro",
        CascadeScope.all(),
        active_urns={"agent_profile:pedro"},
    )
    assert plan.deactivate == ["directive:arch", "tactic:tdd"]
    assert plan.skipped_shared == []


def test_deactivation_respects_scope() -> None:
    graph = _profile_graph()
    # Only cascade tactics; the suggested directive is not a candidate at all.
    scope = CascadeScope.parse("tactic")
    assert scope is not None
    plan = deactivation_plan(
        graph,
        "agent_profile:pedro",
        scope,
        active_urns={"agent_profile:pedro"},
    )
    assert plan.deactivate == ["tactic:tdd"]
    assert plan.skipped_shared == []


def test_deactivation_transitive_shared_reference_is_skipped() -> None:
    # pedro -> tactic:a -> tactic:deep ; renata -> tactic:deep (transitively shared)
    graph = _graph(
        nodes=[
            _node("agent_profile:pedro", NodeKind.AGENT_PROFILE),
            _node("agent_profile:renata", NodeKind.AGENT_PROFILE),
            _node("tactic:a", NodeKind.TACTIC),
            _node("tactic:deep", NodeKind.TACTIC),
        ],
        edges=[
            _edge("agent_profile:pedro", "tactic:a"),
            _edge("tactic:a", "tactic:deep"),
            _edge("agent_profile:renata", "tactic:deep"),
        ],
    )
    plan = deactivation_plan(
        graph,
        "agent_profile:pedro",
        CascadeScope.all(),
        active_urns={"agent_profile:pedro", "agent_profile:renata"},
    )
    # tactic:a is exclusive to pedro; tactic:deep is reachable from renata -> skip.
    assert plan.deactivate == ["tactic:a"]
    assert [s.urn for s in plan.skipped_shared] == ["tactic:deep"]
    assert plan.skipped_shared[0].referencing_active_urn == "agent_profile:renata"
