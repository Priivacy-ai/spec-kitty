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
from doctrine.artifact_kinds import (
    CHARTER_ACTIVATABLE_KINDS,
    ArtifactKind,
    MissionTypeNotAnArtifactKind,
)
from doctrine.drg.loader import load_built_in_graph
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


def test_reference_relations_include_scope_and_instantiates() -> None:
    # ADR 2026-08-20-1 (#2829): SCOPE + INSTANTIATES joined the cascade reference
    # set so the forward closure walks the action hop
    # (``mission_type --requires--> action --scope--> governance`` and
    # ``action --instantiates--> template``). REQUIRES/SUGGESTS are the legacy set;
    # REFINES joined in #2079. This is the widened followed set the kind-complete
    # cascade traverses (candidacy is filtered separately).
    expected = frozenset(
        {
            Relation.REQUIRES,
            Relation.SUGGESTS,
            Relation.REFINES,
            Relation.SCOPE,
            Relation.INSTANTIATES,
        }
    )
    assert expected == REFERENCE_RELATIONS


def test_tension_vocabulary_excluded_from_reference_relations() -> None:
    """T032 (FR-013, C-003): tension vocabulary never joins cascade's reference set.

    ``in_tension_with``/``reconciles_tension``/``rejects`` (mission
    ``doctrine-tension-edges-01KY1WPC``) achieve cascade exclusion **by
    omission** -- they must never be added to ``REFERENCE_RELATIONS`` -- so
    activating one side of a tension (or a reconciler) never auto-cascades to
    the other side/reconciled artefacts (INV-003). There is no code change in
    ``cascade.py`` to make this pass; the test IS the deliverable. This is
    deliberately an explicit frozenset-intersection assertion, not a "cascade
    doesn't crash" smoke test, which would pass vacuously.
    """
    assert (
        frozenset(
            {Relation.IN_TENSION_WITH, Relation.RECONCILES_TENSION, Relation.REJECTS}
        )
        & REFERENCE_RELATIONS
        == frozenset()
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
    assert {s.urn for s in plan.skipped_shared} == {"tactic:shared"}
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


# ---------------------------------------------------------------------------
# WP01 (#2829) — kind-complete cascade: follow the action hop, filter to
# CHARTER_ACTIVATABLE_KINDS. ADR docs/adr/3.x/2026-08-20-1-...
# ---------------------------------------------------------------------------

#: The four built-in mission types shipped in the merged DRG.
_BUILT_IN_MISSION_TYPE_URNS: tuple[str, ...] = (
    "mission_type:documentation",
    "mission_type:plan",
    "mission_type:research",
    "mission_type:software-dev",
)

#: The mission types whose action steps ``scope`` onto governance artifacts in the
#: shipped graph — so following the action hop yields a non-empty cascade (C-CAS-1).
#: ``mission_type:plan`` is intentionally absent: its action steps carry only
#: ``instantiates → template`` edges (no ``scope``), so after the ADR 2026-08-20-1
#: activatable-kind filter it cascades to nothing. That is a *graph-data* property
#: (the plan step contracts scope no governance), not a cascade-code defect, and
#: wiring plan governance is outside WP01's code-only scope (see
#: ``test_plan_cascade_is_empty_because_its_actions_scope_no_governance``).
_GOVERNANCE_BEARING_MISSION_TYPE_URNS: tuple[str, ...] = (
    "mission_type:documentation",
    "mission_type:research",
    "mission_type:software-dev",
)

#: Relations that must stay OUT of the followed set (C-CAS-6). A graph with only
#: one of these from the source must cascade to nothing. ``in_tension_with`` is
#: stored canonically with the lexicographically-smaller URN as source.
_EXCLUDED_RELATIONS: tuple[Relation, ...] = (
    Relation.IN_TENSION_WITH,
    Relation.REJECTS,
    Relation.DELEGATES_TO,
    Relation.SPECIALIZES_FROM,
    Relation.ENHANCES,
    Relation.OVERRIDES,
    Relation.REPLACES,
    Relation.APPLIES,
    Relation.VOCABULARY,
)


@pytest.fixture(scope="module")
def built_in_graph() -> DRGGraph:
    """The merged built-in DRG, loaded once for the module."""
    return load_built_in_graph()


@pytest.mark.parametrize("mission_type_urn", _GOVERNANCE_BEARING_MISSION_TYPE_URNS)
def test_cascade_from_governance_bearing_mission_types_is_non_empty(
    built_in_graph: DRGGraph, mission_type_urn: str
) -> None:
    # C-CAS-1 (RED baseline: returned 0 — the #2829 action-hop dead-end).
    # Following the action hop (requires -> action -> scope -> governance) makes
    # the cascade reachable for every mission type whose steps scope governance.
    result = cascade_activation_targets(
        built_in_graph, mission_type_urn, CascadeScope.all()
    )
    assert result.activated, (
        f"cascade from {mission_type_urn} was empty — the #2829 action-hop dead-end"
    )


def test_plan_cascade_is_empty_because_its_actions_scope_no_governance(
    built_in_graph: DRGGraph,
) -> None:
    # SURFACED FINDING (WP01, code-only scope): the #2829 dead-end (the closure
    # stopping at the action node) IS closed for plan too — the traversal now
    # passes *through* its actions. But ``mission_type:plan``'s action steps carry
    # only ``instantiates → template`` edges and no ``scope`` edges in the shipped
    # graph, so after the ADR 2026-08-20-1 activatable-kind filter drops those
    # templates there is nothing left to cascade. This is a graph-data property
    # (plan step contracts scope no governance), NOT a cascade-code defect; wiring
    # plan governance would be a graph-data change outside WP01's owned surface.
    result = cascade_activation_targets(
        built_in_graph, "mission_type:plan", CascadeScope.all()
    )
    assert result.activated == {}


def test_cascade_from_documentation_reaches_governance_kinds(
    built_in_graph: DRGGraph,
) -> None:
    # C-CAS-2: documentation's actions scope onto governance artifacts; the
    # activated mapping must include at least directive, tactic, styleguide.
    result = cascade_activation_targets(
        built_in_graph, "mission_type:documentation", CascadeScope.all()
    )
    for kind_key in ("directive", "tactic", "styleguide"):
        assert kind_key in result.activated, (
            f"{kind_key!r} missing from documentation cascade: "
            f"{sorted(result.activated)}"
        )


def test_cascade_never_proposes_template_or_asset(built_in_graph: DRGGraph) -> None:
    # C-CAS-3: even for a source whose closure reaches templates/assets, neither
    # appears in ``activated`` nor in the no-cascade ``skipped`` report.
    result = cascade_activation_targets(
        built_in_graph, "mission_type:documentation", CascadeScope.all()
    )
    assert "template" not in result.activated
    assert "asset" not in result.activated

    report = referenced_but_not_cascaded(built_in_graph, "mission_type:documentation")
    assert "template" not in report.skipped
    assert "asset" not in report.skipped


@pytest.mark.parametrize("mission_type_urn", _BUILT_IN_MISSION_TYPE_URNS)
def test_cascade_never_emits_action_nodes(
    built_in_graph: DRGGraph, mission_type_urn: str
) -> None:
    # C-CAS-4: ``action:`` is not an ArtifactKind, so it is never a bucket key —
    # the traversal passes *through* actions but never proposes one as a target.
    result = cascade_activation_targets(
        built_in_graph, mission_type_urn, CascadeScope.all()
    )
    assert "action" not in result.activated


@pytest.mark.parametrize("relation", _EXCLUDED_RELATIONS)
def test_excluded_relation_yields_empty_cascade(relation: Relation) -> None:
    # C-CAS-6: a graph carrying only one excluded relation from the source must
    # cascade to nothing — those relations never join REFERENCE_RELATIONS.
    # Construct source < target so an ``in_tension_with`` edge is canonically shaped.
    source = "directive:aaa-source"
    target = "directive:bbb-target"
    graph = _graph(
        nodes=[
            _node(source, NodeKind.DIRECTIVE),
            _node(target, NodeKind.DIRECTIVE),
        ],
        edges=[_edge(source, target, relation)],
    )
    result = cascade_activation_targets(graph, source, CascadeScope.all())
    assert result.activated == {}
    assert result.skipped_by_scope == {}


def test_instantiates_is_followed_but_template_dropped_at_candidacy() -> None:
    # ADR: ``instantiates`` is followed (traversal reaches the template) but its
    # only targets are templates, dropped at candidacy — so it adds no activation
    # target. Traversal reach and candidacy are separate concerns.
    graph = _graph(
        nodes=[
            _node("mission_type:gamma", NodeKind.MISSION_TYPE),
            _node("action:gamma/step", NodeKind.ACTION),
            _node("template:tmpl", NodeKind.TEMPLATE),
        ],
        edges=[
            _edge("mission_type:gamma", "action:gamma/step", Relation.REQUIRES),
            _edge("action:gamma/step", "template:tmpl", Relation.INSTANTIATES),
        ],
    )
    result = cascade_activation_targets(
        graph, "mission_type:gamma", CascadeScope.all()
    )
    assert result.activated == {}


def test_deactivation_shared_via_widened_set_is_skipped() -> None:
    # C-CAS-7: a candidate reachable via the widened (scope) set from another
    # still-active source is skipped (named), never deactivated. RED baseline:
    # scope is unfollowed so the candidate is not even reached (skipped_shared []).
    graph = _graph(
        nodes=[
            _node("mission_type:alpha", NodeKind.MISSION_TYPE),
            _node("mission_type:beta", NodeKind.MISSION_TYPE),
            _node("action:alpha/step", NodeKind.ACTION),
            _node("action:beta/step", NodeKind.ACTION),
            _node("directive:shared-gov", NodeKind.DIRECTIVE),
        ],
        edges=[
            _edge("mission_type:alpha", "action:alpha/step", Relation.REQUIRES),
            _edge("mission_type:beta", "action:beta/step", Relation.REQUIRES),
            _edge("action:alpha/step", "directive:shared-gov", Relation.SCOPE),
            _edge("action:beta/step", "directive:shared-gov", Relation.SCOPE),
        ],
    )
    plan = deactivation_plan(
        graph,
        "mission_type:alpha",
        CascadeScope.all(),
        active_urns={"mission_type:alpha", "mission_type:beta"},
    )
    assert plan.deactivate == []
    assert [s.urn for s in plan.skipped_shared] == ["directive:shared-gov"]
    assert plan.skipped_shared[0].referencing_active_urn == "mission_type:beta"


def test_cascade_candidate_kinds_are_all_charter_activatable(
    built_in_graph: DRGGraph,
) -> None:
    # C-CAS-3/5: every kind the shipped cascade proposes (for any mission type)
    # is a member of CHARTER_ACTIVATABLE_KINDS — the filter admits nothing else.
    activatable_values = {kind.value for kind in CHARTER_ACTIVATABLE_KINDS}
    for mission_type_urn in _BUILT_IN_MISSION_TYPE_URNS:
        result = cascade_activation_targets(
            built_in_graph, mission_type_urn, CascadeScope.all()
        )
        assert set(result.activated) <= activatable_values, (
            f"{mission_type_urn} proposed a non-activatable kind: "
            f"{set(result.activated) - activatable_values}"
        )


def test_instantiates_targets_are_all_non_activatable_today(
    built_in_graph: DRGGraph,
) -> None:
    """Pin ADR 2026-08-20-1's "instantiates adds no activation target today".

    ``instantiates`` is followed for action-hop completeness, but every shipped
    ``instantiates`` edge points at a ``template`` (a non-charter-activatable
    kind dropped at candidacy), so following it contributes ZERO cascade
    candidates. If a future ``instantiates`` edge ever targets a
    charter-activatable kind, cascade output would change silently — this pin
    fails so the change is a conscious decision (update the ADR + tests), not an
    accident.
    """
    activatable_values = {kind.value for kind in CHARTER_ACTIVATABLE_KINDS}
    offenders: list[str] = []
    for edge in built_in_graph.edges:
        if edge.relation is not Relation.INSTANTIATES:
            continue
        prefix = edge.target.split(":", 1)[0] if ":" in edge.target else edge.target
        if prefix in activatable_values:
            offenders.append(edge.target)
    assert not offenders, (
        "instantiates now targets charter-activatable kind(s); following it would "
        "change cascade output. Update ADR 2026-08-20-1 + the cascade tests before "
        f"shipping: {sorted(set(offenders))}"
    )
