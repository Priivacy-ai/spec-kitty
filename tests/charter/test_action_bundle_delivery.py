"""WP10 — the delivery rail carries every kind (FR-009, FR-011, C-006, C-008).

Every kind the action bundle *resolves* must reach the *rendered* output, and
the delivery gate must be a **total function over ``NodeKind``** rather than an
enumerated exception. The load-bearing trap these tests pin:

* An equality stated as ``activated ∩ reachable`` makes ``asset_ids = []`` the
  conforming implementation forever, because ``activated(asset)`` is ``∅`` by
  construction (assets are not activation-eligible). ``gate(kind)`` is therefore
  a column of the same ``NodeKind``-keyed table as the slot —
  ``ACTIVATED`` for activation-eligible kinds, ``ALL`` for delivered-but-ungated
  kinds (assets) — and ``delivered(kind) = gate(kind) ∩ channel_reachable``.

The reachability channel is exercised through the **real** pipeline
(:func:`charter.drg.filter_graph_by_activation` → :func:`charter.offering.drg.query.resolve_context`),
never a hand-rolled walk, so a gate-table drift from the runtime filter reddens
here (R-1).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from pathlib import Path

import pytest

from charter import context
from charter.drg import filter_graph_by_activation
from charter.activation.pack_context import PackContext
from charter.offering.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from charter.offering.drg.query import resolve_context

pytestmark = [pytest.mark.fast]

_ACTION_URN = "action:demo/build"


def _scope_graph() -> DRGGraph:
    """An action that directly scopes one node of every delivered kind.

    All five artefact nodes are reachable at depth 1 (a single ``scope`` hop),
    so reachability is not the variable under test here — the activation gate
    is. ``asset:a1`` is the load-bearing node: ``asset`` is not activation-
    eligible, so a ``activated ∩ reachable`` reading would drop it forever.
    """
    nodes = [
        DRGNode(urn=_ACTION_URN, kind=NodeKind.ACTION),
        DRGNode(urn="directive:d1", kind=NodeKind.DIRECTIVE),
        DRGNode(urn="tactic:t1", kind=NodeKind.TACTIC),
        DRGNode(urn="procedure:p1", kind=NodeKind.PROCEDURE),
        DRGNode(urn="asset:a1", kind=NodeKind.ASSET),
    ]
    edges = [
        DRGEdge(source=_ACTION_URN, target=n.urn, relation=Relation.SCOPE)
        for n in nodes[1:]
    ]
    return DRGGraph(
        schema_version="1.0",
        generated_at="2026-07-29T00:00:00+00:00",
        generated_by="test_action_bundle_delivery",
        nodes=nodes,
        edges=edges,
    )


def _pack(*, kinds: frozenset[str]) -> PackContext:
    """Hermetic PackContext gating on *kinds* (plural kind names) alone."""
    return PackContext(
        activated_kinds=kinds,
        activated_mission_types=frozenset({"demo"}),
        pack_roots=(),
        org_pack_names=(),
        repo_root=Path("/nonexistent"),
    )


# ---------------------------------------------------------------------------
# T053 — _classify_artifact_urns returns a slot-keyed mapping (no sixth
#        positional per-kind projection).
# ---------------------------------------------------------------------------


def test_classify_returns_slot_keyed_mapping() -> None:
    graph = _scope_graph()
    resolved = resolve_context(graph, _ACTION_URN, depth=2)

    result = context._classify_artifact_urns(resolved.artifact_urns, graph, set())

    assert isinstance(result, Mapping)
    assert result["directives"] == ("d1",)
    assert result["procedures"] == ("p1",)
    assert result["assets"] == ("a1",)


# ---------------------------------------------------------------------------
# T054 — the bundle carries procedure_ids and asset_ids (and keeps the
#        mission/service fields the contract sketch omits).
# ---------------------------------------------------------------------------


def test_classify_skips_unresolvable_urn_and_out_of_scope_directive() -> None:
    """Two ``_classify_artifact_urns`` guards: a stale URN and directive scoping.

    ``artifact_urns`` is caller-supplied and can include a URN the merged
    graph carries no node for (a stale/mismatched reference) -- that entry is
    skipped rather than raising ``AttributeError`` on ``node.kind``. Separately,
    a resolved ``DIRECTIVE`` whose id is not in a non-empty
    ``project_directives`` is scope-filtered out -- a project only receives
    the directives it actually selected, not every directive reachable from
    the graph.
    """
    graph = _scope_graph()

    result = context._classify_artifact_urns(
        artifact_urns={"directive:d1", "tactic:ghost-urn-with-no-node"},
        merged=graph,
        project_directives={"some-other-directive"},
    )

    # d1 resolves to a real DIRECTIVE node but is not in project_directives.
    assert result["directives"] == ()
    # the ghost URN has no node in the graph; it never reaches a slot at all.
    assert result.get("tactics", ()) == ()


def test_bundle_carries_procedure_and_asset_fields() -> None:
    field_names = {f.name for f in dataclasses.fields(context._ActionDoctrineBundle)}

    assert {"procedure_ids", "asset_ids"} <= field_names
    assert {"mission", "service", "directive_ids"} <= field_names


# ---------------------------------------------------------------------------
# T056 — the slot table projects PROCEDURE and ASSET into real slots.
# ---------------------------------------------------------------------------


def test_slot_table_projects_procedures_and_assets() -> None:
    assert context.action_bundle_bucket(NodeKind.PROCEDURE) == "procedures"
    assert context.action_bundle_bucket(NodeKind.ASSET) == "assets"


# ---------------------------------------------------------------------------
# T055 — the delivery gate is a TOTAL function over NodeKind.
#
#   gate(kind) = ACTIVATED  for activation-eligible kinds
#              = ALL        for delivered-but-ungated kinds (assets)
#   delivered(kind) = gate(kind) ∩ channel_reachable
#
# Stating this as ``activated ∩ reachable`` is a defect: ``activated(asset)``
# is ∅ by construction, so a uniform reading ships ``asset_ids = []`` forever
# and passes.
# ---------------------------------------------------------------------------


def test_gate_is_total_over_every_node_kind() -> None:
    for kind in NodeKind:
        assert context.action_bundle_gate(kind) in (
            context._Gate.ACTIVATED,
            context._Gate.ALL,
        ), f"gate(kind) must be total; {kind!r} has no column value"


def test_asset_gate_is_all_and_directive_gate_is_activated() -> None:
    # The load-bearing distinction: asset delivery is ungated (ALL), so
    # activated(asset)=∅ does NOT force asset_ids=[].
    assert context.action_bundle_gate(NodeKind.ASSET) is context._Gate.ALL
    # TEMPLATE is ungated too, but excluded via its slot=None stated reason —
    # it is not ASSET's untreated twin (B-1a).
    assert context.action_bundle_gate(NodeKind.TEMPLATE) is context._Gate.ALL
    assert context.action_bundle_gate(NodeKind.DIRECTIVE) is context._Gate.ACTIVATED
    assert context.action_bundle_gate(NodeKind.PROCEDURE) is context._Gate.ACTIVATED


def test_delivered_equals_gate_intersect_reachable_through_real_pipeline() -> None:
    """delivered(kind) = gate(kind) ∩ reachable, measured through the runtime.

    ``activated_kinds`` lists ``directives`` and ``procedures`` but NOT
    ``tactics`` (an ACTIVATED kind) and NOT ``assets`` (an ALL kind). The gate
    therefore drops the tactic (activated∩reachable = ∅) yet keeps the asset
    (ALL∩reachable = reachable) — proving ``asset_ids = []`` is not the
    conforming outcome.
    """
    graph = _scope_graph()
    pack = _pack(kinds=frozenset({"directives", "procedures"}))

    filtered = filter_graph_by_activation(graph, pack)
    resolved = resolve_context(filtered, _ACTION_URN, depth=2)
    delivered = context._classify_artifact_urns(resolved.artifact_urns, filtered, set())

    # ACTIVATED kind, activated → delivered.
    assert delivered.get("directives") == ("d1",)
    assert delivered.get("procedures") == ("p1",)
    # ACTIVATED kind, NOT activated → gated to empty.
    assert delivered.get("tactics", ()) == ()
    # ALL kind, ungated → delivered by reachability alone.
    assert delivered.get("assets") == ("a1",), (
        "asset must survive the gate (gate=ALL); an activated∩reachable reading "
        "would ship asset_ids=[] forever"
    )


# ---------------------------------------------------------------------------
# T058 — GovernanceResolution carries an asset field so it is not one kind
#        narrower than the bundle. Any population is from the canonical
#        PackContext path (V-4), never a second store reader.
# ---------------------------------------------------------------------------


def test_governance_resolution_carries_asset_field() -> None:
    from charter.activation.resolver import GovernanceResolution

    field_names = {f.name for f in dataclasses.fields(GovernanceResolution)}
    assert "assets" in field_names, "GovernanceResolution must carry assets, parallel to procedures"
    assert "procedures" in field_names

    resolution = GovernanceResolution(
        paradigms=[], directives=[], tools=[], template_set="x", metadata={}
    )
    assert resolution.assets == []
