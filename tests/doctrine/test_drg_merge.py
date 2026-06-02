"""Tests for the doctrine-owned three-layer DRG merge (WP03).

Mission ``org-doctrine-profile-integrity-activation-closure-01KT1TV1`` WP03
relocates ``merge_three_layers`` from ``charter.drg`` into
:mod:`doctrine.drg.merge` (OQ-2(ii) / C-009) and fixes the org-fragment
silent-drop of unknown relations (FR-003 / contract C0.3).

These tests import the merge **directly from the doctrine layer** (not via the
``charter.drg`` re-export facade) so they double as a guard that the relocated
module is self-contained and free of any charter/specify_cli dependency. The
``tests/architectural/test_layer_rules.py`` suite enforces the import boundary
statically; this file exercises behaviour.

Coverage:

* T011 — behaviour preservation: a representative built-in + org + project
  input produces a node/edge set that matches an independent recomputation of
  the documented merge semantics (golden recomputation, not a smoke test).
* T011/C0.3 — an org-fragment ``specializes_from`` edge resolves into the
  merged graph (WP02 added the enum member); an unknown relation raises.
* T012 — shipped/org/project fragment parity: a valid lineage edge routes into
  the merged graph identically across all three tiers, and an unknown relation
  is rejected (never silently dropped) on every tier.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from doctrine.drg.merge import (
    OrgDRGConflictError,
    UnknownRelationError,
    merge_three_layers,
)
from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from doctrine.drg.org_pack_loader import OrgDRGFragment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _graph(
    nodes: list[DRGNode] | None = None,
    edges: list[DRGEdge] | None = None,
    *,
    generated_by: str = "unit-test",
) -> DRGGraph:
    return DRGGraph(
        schema_version="1.0",
        generated_at="2026-06-01T00:00:00Z",
        generated_by=generated_by,
        nodes=nodes or [],
        edges=edges or [],
    )


def _fragment(
    pack_name: str,
    nodes: list[dict],
    edges: list[dict],
) -> OrgDRGFragment:
    return OrgDRGFragment.model_validate(
        {
            "pack_name": pack_name,
            "source_kind": "local_path",
            "source_ref": f"/tmp/{pack_name}",
            "layer_index": 1,
            "provenance_marker": "org",
            "nodes": nodes,
            "edges": edges,
        }
    )


# ---------------------------------------------------------------------------
# T011 — behaviour preservation (golden recomputation)
# ---------------------------------------------------------------------------


class TestBehaviorPreservation:
    """The relocated merge must produce the same node/edge set the pre-WP03
    charter merge produced for a representative three-layer input.

    Rather than snapshotting opaque bytes, this recomputes the expected merged
    graph from the documented semantics (built-in seed → org overlay → project
    overlay, with provenance tags) and asserts an exact set equality on the
    merged URNs / edges and their provenance markers.
    """

    def test_built_in_org_project_merge_matches_recomputation(self) -> None:
        built_in = _graph(
            nodes=[
                DRGNode(urn="directive:shipped-d", kind=NodeKind.DIRECTIVE),
                DRGNode(urn="tactic:shipped-t", kind=NodeKind.TACTIC),
            ],
            edges=[
                DRGEdge(
                    source="tactic:shipped-t",
                    target="directive:shipped-d",
                    relation=Relation.APPLIES,
                ),
            ],
            generated_by="built-in-gen",
        )
        org = _fragment(
            "acme",
            nodes=[
                {"id": "policy", "kind": "directives", "title": "Policy"},
                {"id": "play", "kind": "tactics", "title": "Play"},
            ],
            edges=[
                {"source": "play", "target": "policy", "relation": "requires"},
            ],
        )
        project = _graph(
            nodes=[DRGNode(urn="tactic:proj-t", kind=NodeKind.TACTIC)],
            edges=[
                DRGEdge(
                    source="tactic:proj-t",
                    target="directive:shipped-d",
                    relation=Relation.SUGGESTS,
                ),
            ],
        )

        merged = merge_three_layers(
            built_in=built_in, org_fragments=[org], project=project
        )

        # --- Recompute the expected node-URN → provenance mapping. ---
        expected_node_provenance = {
            "directive:shipped-d": "built-in",
            "tactic:shipped-t": "built-in",
            "directive:policy": "org:acme",
            "tactic:play": "org:acme",
            "tactic:proj-t": "project",
        }
        actual_node_provenance = {
            n.urn: getattr(n, "provenance", None) for n in merged.nodes
        }
        assert actual_node_provenance == expected_node_provenance

        # --- Recompute the expected edge set (source, target, relation, prov). ---
        expected_edges = {
            ("tactic:shipped-t", "directive:shipped-d", Relation.APPLIES, "built-in"),
            ("tactic:play", "directive:policy", Relation.REQUIRES, "org:acme"),
            ("tactic:proj-t", "directive:shipped-d", Relation.SUGGESTS, "project"),
        }
        actual_edges = {
            (e.source, e.target, e.relation, getattr(e, "provenance", None))
            for e in merged.edges
        }
        assert actual_edges == expected_edges

        # Graph header is inherited from the built-in layer (preserved).
        assert merged.schema_version == built_in.schema_version
        assert merged.generated_by == built_in.generated_by

    def test_empty_inputs_round_trip(self) -> None:
        merged = merge_three_layers(
            built_in=_graph(), org_fragments=[], project=None
        )
        assert merged.nodes == []
        assert merged.edges == []


# ---------------------------------------------------------------------------
# T011 / C0.3 — specializes_from resolves; unknown relation raises
# ---------------------------------------------------------------------------


class TestSpecializesFromAndUnknownRelation:
    def test_org_specializes_from_edge_appears_in_merged_graph(self) -> None:
        """C0.3: WP02 added ``SPECIALIZES_FROM``; an org-fragment lineage edge
        must now resolve into the merged graph (not be dropped)."""
        org = _fragment(
            "lineage-pack",
            nodes=[
                {"id": "child", "kind": "agent_profiles", "title": "Child"},
                {"id": "parent", "kind": "agent_profiles", "title": "Parent"},
            ],
            edges=[
                {
                    "source": "child",
                    "target": "parent",
                    "relation": "specializes_from",
                },
            ],
        )
        merged = merge_three_layers(
            built_in=_graph(), org_fragments=[org], project=None
        )
        lineage_edges = [
            e for e in merged.edges if e.relation is Relation.SPECIALIZES_FROM
        ]
        assert len(lineage_edges) == 1
        assert lineage_edges[0].source == "agent_profile:child"
        assert lineage_edges[0].target == "agent_profile:parent"
        assert getattr(lineage_edges[0], "provenance", None) == "org:lineage-pack"

    def test_org_unknown_relation_raises_structured_error(self) -> None:
        """C0.3 / FR-003: an unrecognised relation fails closed with a
        structured error that names the relation, the fragment, and the valid
        token set — it is NOT silently dropped."""
        org = _fragment(
            "bad-rel-pack",
            nodes=[
                {"id": "a", "kind": "directives", "title": "A"},
                {"id": "b", "kind": "tactics", "title": "B"},
            ],
            edges=[{"source": "a", "target": "b", "relation": "bogus"}],
        )
        with pytest.raises(UnknownRelationError) as exc_info:
            merge_three_layers(built_in=_graph(), org_fragments=[org], project=None)
        err = exc_info.value
        assert err.relation == "bogus"
        assert "bad-rel-pack" in err.source_marker
        # Valid token set is surfaced for the operator.
        assert "specializes_from" in err.valid_relations
        assert "bogus" in str(err)

    def test_org_known_alias_still_resolves(self) -> None:
        """Behaviour preservation: a known alias (``refines`` → APPLIES) is
        still translated, not raised."""
        org = _fragment(
            "alias-pack",
            nodes=[
                {"id": "a", "kind": "directives", "title": "A"},
                {"id": "b", "kind": "tactics", "title": "B"},
            ],
            edges=[{"source": "a", "target": "b", "relation": "refines"}],
        )
        merged = merge_three_layers(
            built_in=_graph(), org_fragments=[org], project=None
        )
        assert len(merged.edges) == 1
        assert merged.edges[0].relation is Relation.APPLIES


# ---------------------------------------------------------------------------
# T012 — shipped / org / project parity
# ---------------------------------------------------------------------------


class TestThreeSourceParity:
    """A valid lineage edge routes into the merged graph identically from
    shipped, org, and project sources; an unknown relation is rejected on every
    tier (no silent path on any source)."""

    def _shipped_lineage_graph(self) -> DRGGraph:
        return _graph(
            nodes=[
                DRGNode(urn="agent_profile:child", kind=NodeKind.AGENT_PROFILE),
                DRGNode(urn="agent_profile:parent", kind=NodeKind.AGENT_PROFILE),
            ],
            edges=[
                DRGEdge(
                    source="agent_profile:child",
                    target="agent_profile:parent",
                    relation=Relation.SPECIALIZES_FROM,
                ),
            ],
        )

    def test_shipped_valid_lineage_edge_present(self) -> None:
        merged = merge_three_layers(
            built_in=self._shipped_lineage_graph(),
            org_fragments=[],
            project=None,
        )
        assert any(
            e.relation is Relation.SPECIALIZES_FROM
            and e.source == "agent_profile:child"
            and e.target == "agent_profile:parent"
            for e in merged.edges
        )

    def test_org_valid_lineage_edge_present(self) -> None:
        org = _fragment(
            "p",
            nodes=[
                {"id": "child", "kind": "agent_profiles", "title": "Child"},
                {"id": "parent", "kind": "agent_profiles", "title": "Parent"},
            ],
            edges=[
                {
                    "source": "child",
                    "target": "parent",
                    "relation": "specializes_from",
                }
            ],
        )
        merged = merge_three_layers(
            built_in=_graph(), org_fragments=[org], project=None
        )
        assert any(
            e.relation is Relation.SPECIALIZES_FROM
            and e.source == "agent_profile:child"
            and e.target == "agent_profile:parent"
            for e in merged.edges
        )

    def test_project_valid_lineage_edge_present(self) -> None:
        merged = merge_three_layers(
            built_in=_graph(),
            org_fragments=[],
            project=self._shipped_lineage_graph(),
        )
        assert any(
            e.relation is Relation.SPECIALIZES_FROM
            and e.source == "agent_profile:child"
            and e.target == "agent_profile:parent"
            for e in merged.edges
        )

    def test_shipped_unknown_relation_rejected(self) -> None:
        """The shipped/project tiers reject an unknown relation at DRGEdge
        construction time (Pydantic ValidationError) — the loud path the
        org tier now matches."""
        with pytest.raises(ValidationError):
            DRGEdge(
                source="agent_profile:child",
                target="agent_profile:parent",
                relation="bogus",  # type: ignore[arg-type]
            )

    def test_org_unknown_relation_rejected(self) -> None:
        org = _fragment(
            "p",
            nodes=[
                {"id": "child", "kind": "agent_profiles", "title": "Child"},
                {"id": "parent", "kind": "agent_profiles", "title": "Parent"},
            ],
            edges=[{"source": "child", "target": "parent", "relation": "bogus"}],
        )
        with pytest.raises(UnknownRelationError):
            merge_three_layers(built_in=_graph(), org_fragments=[org], project=None)

    def test_project_unknown_relation_rejected(self) -> None:
        """A project-tier DRGGraph cannot even be constructed with an unknown
        relation, so the unknown-relation path is closed before merge."""
        with pytest.raises(ValidationError):
            _graph(
                nodes=[
                    DRGNode(urn="tactic:x", kind=NodeKind.TACTIC),
                    DRGNode(urn="directive:y", kind=NodeKind.DIRECTIVE),
                ],
                edges=[
                    DRGEdge(
                        source="tactic:x",
                        target="directive:y",
                        relation="bogus",  # type: ignore[arg-type]
                    ),
                ],
            )


# ---------------------------------------------------------------------------
# Invariant regressions preserved through the relocation
# ---------------------------------------------------------------------------


class TestInvariantsPreserved:
    def test_org_override_of_shipped_invariant_hard_fails(self) -> None:
        built_in = _graph(
            nodes=[DRGNode(urn="directive:locked", kind=NodeKind.DIRECTIVE)]
        )
        org = _fragment(
            "rogue",
            nodes=[{"id": "locked", "kind": "directives", "title": "Override"}],
            edges=[],
        )
        with pytest.raises(OrgDRGConflictError) as exc_info:
            merge_three_layers(built_in=built_in, org_fragments=[org], project=None)
        assert any(c.kind == "node_override" for c in exc_info.value.conflicts)

    def test_layer_rule_violation_hard_fails(self) -> None:
        org = _fragment(
            "smuggler",
            nodes=[
                {
                    "id": "x",
                    "kind": "tactics",
                    "title": "X",
                    "body_path": "src/specify_cli/sneaky.py",
                }
            ],
            edges=[],
        )
        with pytest.raises(OrgDRGConflictError) as exc_info:
            merge_three_layers(built_in=_graph(), org_fragments=[org], project=None)
        assert any(
            c.kind == "layer_rule_violation" for c in exc_info.value.conflicts
        )
