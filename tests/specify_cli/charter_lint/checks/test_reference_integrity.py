"""Tests for ReferenceIntegrityChecker.

Uses duck-type SimpleNamespace stubs — the real doctrine DRG package is
not required.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from specify_cli.charter_lint.checks.reference_integrity import ReferenceIntegrityChecker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
