"""Tests for OrphanChecker.

Uses duck-type SimpleNamespace stubs — the real doctrine DRG package is
not required.  All scenarios pass without WP5.1 being available.
"""

from __future__ import annotations

from types import SimpleNamespace


from specify_cli.charter_lint.checks.orphan import OrphanChecker


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
# Tests
# ---------------------------------------------------------------------------


class TestOrphanCheckerManufacturedDecay:
    """Verify that orphaned nodes generate findings."""

    def test_orphaned_directive_detected(self):
        directive_node = _make_node("directive:DIR-001", "directive", "DIR-001 Governance")
        drg = _make_drg(nodes=[directive_node], edges=[])
        findings = OrphanChecker().run(drg)
        assert len(findings) == 1
        f = findings[0]
        assert f.category == "orphan"
        assert f.type == "orphaned_directive"
        assert f.id == "directive:DIR-001"
        assert f.severity == "medium"

    def test_orphaned_adr_detected(self):
        adr_node = _make_node("adr:ADR-001", "adr", "ADR-001 Use YAML")
        drg = _make_drg(nodes=[adr_node], edges=[])
        findings = OrphanChecker().run(drg)
        assert any(f.type == "orphaned_adr" for f in findings)

    def test_orphaned_glossary_scope_detected(self):
        gs_node = _make_node("glossary:workspace", "glossary_scope", "Workspace")
        drg = _make_drg(nodes=[gs_node], edges=[])
        findings = OrphanChecker().run(drg)
        assert any(f.type == "orphaned_glossary_scope" for f in findings)

    def test_feature_scope_propagated(self):
        directive_node = _make_node("directive:DIR-002", "directive")
        drg = _make_drg(nodes=[directive_node], edges=[])
        findings = OrphanChecker().run(drg, feature_scope="test-feature")
        assert findings[0].feature_id == "test-feature"

    def test_remediation_hint_present(self):
        directive_node = _make_node("directive:DIR-003", "directive")
        drg = _make_drg(nodes=[directive_node], edges=[])
        findings = OrphanChecker().run(drg)
        assert findings[0].remediation_hint is not None


class TestOrphanCheckerCleanDRG:
    """Verify that a well-connected DRG produces zero orphan findings."""

    def test_connected_directive_no_finding(self):
        directive_node = _make_node("directive:DIR-001", "directive", "DIR-001")
        referencing_node = _make_node("mission:001", "mission")
        edge = _make_edge("mission:001", "directive:DIR-001", "governs")
        drg = _make_drg(nodes=[directive_node, referencing_node], edges=[edge])
        findings = OrphanChecker().run(drg)
        assert findings == []

    def test_connected_adr_no_finding(self):
        adr_node = _make_node("adr:ADR-001", "adr")
        wp_node = _make_node("wp:WP01", "wp")
        edge = _make_edge("wp:WP01", "adr:ADR-001", "references")
        drg = _make_drg(nodes=[adr_node, wp_node], edges=[edge])
        findings = OrphanChecker().run(drg)
        assert findings == []

    def test_connected_glossary_no_finding(self):
        gs_node = _make_node("glossary:workspace", "glossary_scope", "Workspace")
        action_node = _make_node("action:implement", "action")
        edge = _make_edge("action:implement", "glossary:workspace", "vocabulary")
        drg = _make_drg(nodes=[gs_node, action_node], edges=[edge])
        findings = OrphanChecker().run(drg)
        assert findings == []

    def test_non_monitored_kind_ignored(self):
        """Node kinds not in the orphan rules should produce no findings."""
        node = _make_node("action:some-action", "action", "Some Action")
        drg = _make_drg(nodes=[node], edges=[])
        findings = OrphanChecker().run(drg)
        assert findings == []


class TestOrphanCheckerMissingDRG:
    """Verify graceful handling of a missing/empty DRG."""

    def test_none_drg_returns_empty(self):
        findings = OrphanChecker().run(None)
        assert findings == []

    def test_empty_nodes_returns_empty(self):
        drg = _make_drg(nodes=[], edges=[])
        findings = OrphanChecker().run(drg)
        assert findings == []

    def test_drg_with_no_nodes_attr_returns_empty(self):
        drg = SimpleNamespace()  # no .nodes attribute
        findings = OrphanChecker().run(drg)
        assert findings == []
