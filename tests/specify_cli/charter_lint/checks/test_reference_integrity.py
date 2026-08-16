"""Tests for ReferenceIntegrityChecker.

Uses duck-type SimpleNamespace stubs — the real doctrine DRG package is
not required.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from specify_cli.charter_runtime.lint.checks.reference_integrity import (
    ReferenceIntegrityChecker,
    _edge_relation_value,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


pytestmark = [pytest.mark.unit, pytest.mark.fast]

def _make_node(urn: str, kind: str, label: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(urn=urn, kind=kind, label=label)


def _make_edge(source: str, target: str, relation: str) -> SimpleNamespace:
    return SimpleNamespace(source=source, target=target, relation=relation)


def _make_drg(nodes: list, edges: list) -> SimpleNamespace:
    node_map = {getattr(n, "urn", ""): n for n in nodes}

    def get_node(urn: str):
        return node_map.get(urn)

    return SimpleNamespace(nodes=nodes, edges=edges, get_node=get_node)


# ---------------------------------------------------------------------------
# Tests — dangling edges
# ---------------------------------------------------------------------------


class TestDanglingEdges:
    def test_edge_to_missing_node_flagged(self):
        source_node = _make_node("wp:WP01", "wp", "WP01")
        edge = _make_edge("wp:WP01", "adr:DELETED-ADR", "references")
        drg = _make_drg(nodes=[source_node], edges=[edge])
        findings = ReferenceIntegrityChecker().run(drg)
        dangling = [f for f in findings if f.type == "dangling_edge"]
        assert len(dangling) == 1
        assert dangling[0].severity == "high"
        assert "DELETED-ADR" in dangling[0].message

    def test_well_formed_edge_no_finding(self):
        wp_node = _make_node("wp:WP01", "wp")
        adr_node = _make_node("adr:ADR-001", "adr")
        edge = _make_edge("wp:WP01", "adr:ADR-001", "references")
        drg = _make_drg(nodes=[wp_node, adr_node], edges=[edge])
        findings = ReferenceIntegrityChecker().run(drg)
        dangling = [f for f in findings if f.type == "dangling_edge"]
        assert dangling == []

    def test_edge_with_empty_target_ignored(self):
        wp_node = _make_node("wp:WP01", "wp")
        edge = _make_edge("wp:WP01", "", "references")
        drg = _make_drg(nodes=[wp_node], edges=[edge])
        findings = ReferenceIntegrityChecker().run(drg)
        assert not any(f.type == "dangling_edge" for f in findings)

    def test_feature_scope_propagated(self):
        source_node = _make_node("wp:WP02", "wp")
        edge = _make_edge("wp:WP02", "ghost:node", "references")
        drg = _make_drg(nodes=[source_node], edges=[edge])
        findings = ReferenceIntegrityChecker().run(drg, feature_scope="my-feature")
        assert any(f.feature_id == "my-feature" for f in findings)

    def test_multiple_dangling_edges_all_reported(self):
        source_node = _make_node("wp:WP03", "wp")
        edge1 = _make_edge("wp:WP03", "ghost:a", "references")
        edge2 = _make_edge("wp:WP03", "ghost:b", "references")
        drg = _make_drg(nodes=[source_node], edges=[edge1, edge2])
        findings = ReferenceIntegrityChecker().run(drg)
        dangling = [f for f in findings if f.type == "dangling_edge"]
        assert len(dangling) == 2


# ---------------------------------------------------------------------------
# Tests — superseded ADR references
# ---------------------------------------------------------------------------


class TestSupersededADRReferences:
    def test_wp_referencing_superseded_adr_flagged(self):
        old_adr = _make_node("adr:ADR-001", "adr", "Old ADR")
        new_adr = _make_node("adr:ADR-002", "adr", "New ADR")
        wp_node = _make_node("wp:WP01", "wp", "WP01")
        # ADR-002 replaces ADR-001 → ADR-001 is superseded
        replaces_edge = _make_edge("adr:ADR-002", "adr:ADR-001", "replaces")
        # WP01 still references the old ADR
        ref_edge = _make_edge("wp:WP01", "adr:ADR-001", "references")
        drg = _make_drg(
            nodes=[old_adr, new_adr, wp_node],
            edges=[replaces_edge, ref_edge],
        )
        findings = ReferenceIntegrityChecker().run(drg)
        superseded = [f for f in findings if f.type == "superseded_adr_reference"]
        assert len(superseded) == 1
        assert superseded[0].severity == "medium"
        assert "ADR-001" in superseded[0].message

    def test_wp_referencing_current_adr_no_finding(self):
        current_adr = _make_node("adr:ADR-002", "adr", "Current ADR")
        wp_node = _make_node("wp:WP01", "wp", "WP01")
        ref_edge = _make_edge("wp:WP01", "adr:ADR-002", "references")
        drg = _make_drg(nodes=[current_adr, wp_node], edges=[ref_edge])
        findings = ReferenceIntegrityChecker().run(drg)
        superseded = [f for f in findings if f.type == "superseded_adr_reference"]
        assert superseded == []

    def test_non_wp_source_not_flagged_for_superseded(self):
        old_adr = _make_node("adr:ADR-001", "adr")
        new_adr = _make_node("adr:ADR-002", "adr")
        some_node = _make_node("directive:DIR-001", "directive")
        replaces_edge = _make_edge("adr:ADR-002", "adr:ADR-001", "replaces")
        # directive references old ADR — should NOT produce a superseded finding
        # (the checker only looks at wp: sources)
        ref_edge = _make_edge("directive:DIR-001", "adr:ADR-001", "governs")
        drg = _make_drg(
            nodes=[old_adr, new_adr, some_node],
            edges=[replaces_edge, ref_edge],
        )
        findings = ReferenceIntegrityChecker().run(drg)
        superseded = [f for f in findings if f.type == "superseded_adr_reference"]
        assert superseded == []

    def test_no_replaces_edges_no_finding(self):
        adr_node = _make_node("adr:ADR-001", "adr")
        wp_node = _make_node("wp:WP01", "wp")
        ref_edge = _make_edge("wp:WP01", "adr:ADR-001", "references")
        drg = _make_drg(nodes=[adr_node, wp_node], edges=[ref_edge])
        findings = ReferenceIntegrityChecker().run(drg)
        superseded = [f for f in findings if f.type == "superseded_adr_reference"]
        assert superseded == []


# ---------------------------------------------------------------------------
# Tests — missing/empty DRG
# ---------------------------------------------------------------------------


class TestEdgeRelationValueHelper:
    """Direct coverage for the extracted ``_edge_relation_value`` helper.

    Extracted (and de-duplicated between the two checks) during Sonar S3776
    cognitive-complexity remediation of ``_check_superseded_adr_references``.
    """

    def test_string_relation_returned_as_is(self):
        edge = _make_edge("wp:WP01", "adr:ADR-001", "replaces")
        assert _edge_relation_value(edge) == "replaces"

    def test_enum_like_relation_uses_value_attribute(self):
        edge = SimpleNamespace(
            source="wp:WP01", target="adr:ADR-001", relation=SimpleNamespace(value="replaces")
        )
        assert _edge_relation_value(edge) == "replaces"

    def test_none_relation_returns_empty_string(self):
        edge = _make_edge("wp:WP01", "adr:ADR-001", None)
        assert _edge_relation_value(edge) == ""

    def test_missing_relation_attribute_returns_empty_string(self):
        edge = SimpleNamespace(source="wp:WP01", target="adr:ADR-001")
        assert _edge_relation_value(edge) == ""


class TestSupersededHelpers:
    """Direct coverage for the extracted superseded-ADR helper functions."""

    def test_collect_superseded_adrs_only_from_replaces_edges(self):
        replaces_edge = _make_edge("adr:ADR-002", "adr:ADR-001", "replaces")
        other_edge = _make_edge("wp:WP01", "adr:ADR-003", "references")
        drg = _make_drg(nodes=[], edges=[replaces_edge, other_edge])
        result = ReferenceIntegrityChecker._collect_superseded_adrs(drg)
        assert result == {"adr:ADR-001"}

    def test_collect_superseded_adrs_ignores_empty_target(self):
        replaces_edge = _make_edge("adr:ADR-002", "", "replaces")
        drg = _make_drg(nodes=[], edges=[replaces_edge])
        result = ReferenceIntegrityChecker._collect_superseded_adrs(drg)
        assert result == set()

    def test_iter_wp_to_superseded_edges_filters_non_wp_sources(self):
        edge = _make_edge("directive:DIR-001", "adr:ADR-001", "governs")
        drg = _make_drg(nodes=[], edges=[edge])
        result = ReferenceIntegrityChecker._iter_wp_to_superseded_edges(
            drg, {"adr:ADR-001"}
        )
        assert result == []

    def test_iter_wp_to_superseded_edges_filters_non_superseded_targets(self):
        edge = _make_edge("wp:WP01", "adr:ADR-002", "references")
        drg = _make_drg(nodes=[], edges=[edge])
        result = ReferenceIntegrityChecker._iter_wp_to_superseded_edges(
            drg, {"adr:ADR-001"}
        )
        assert result == []

    def test_iter_wp_to_superseded_edges_yields_matching_pair(self):
        edge = _make_edge("wp:WP01", "adr:ADR-001", "references")
        drg = _make_drg(nodes=[], edges=[edge])
        result = ReferenceIntegrityChecker._iter_wp_to_superseded_edges(
            drg, {"adr:ADR-001"}
        )
        assert result == [("wp:WP01", "adr:ADR-001")]


class TestReferenceIntegrityCheckerMissingDRG:
    def test_none_drg_returns_empty(self):
        findings = ReferenceIntegrityChecker().run(None)
        assert findings == []

    def test_empty_drg_returns_empty(self):
        drg = _make_drg(nodes=[], edges=[])
        findings = ReferenceIntegrityChecker().run(drg)
        assert findings == []

    def test_drg_with_no_attrs_returns_empty(self):
        drg = SimpleNamespace()
        findings = ReferenceIntegrityChecker().run(drg)
        assert findings == []
