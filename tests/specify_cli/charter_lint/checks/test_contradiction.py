"""Tests for ContradictionChecker.

Uses duck-type SimpleNamespace stubs — the real doctrine DRG package is
not required.
"""

from __future__ import annotations

from types import SimpleNamespace


from specify_cli.charter_lint.checks.contradiction import ContradictionChecker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_node(urn: str, kind: str, label: str | None = None, **kwargs) -> SimpleNamespace:
    return SimpleNamespace(urn=urn, kind=kind, label=label, **kwargs)


def _make_drg(nodes: list, edges: list | None = None) -> SimpleNamespace:
    node_map = {getattr(n, "urn", ""): n for n in nodes}

    def get_node(urn: str):
        return node_map.get(urn)

    return SimpleNamespace(nodes=nodes, edges=edges or [], get_node=get_node)


# ---------------------------------------------------------------------------
# Tests — ADR topic clash
# ---------------------------------------------------------------------------


class TestADRTopicClash:
    def test_two_adrs_same_topic_different_decision_flagged(self):
        adr1 = _make_node("adr:ADR-001", "adr", "ADR 001", topic="logging", decision="use structlog")
        adr2 = _make_node("adr:ADR-002", "adr", "ADR 002", topic="logging", decision="use stdlib logging")
        drg = _make_drg(nodes=[adr1, adr2])
        findings = ContradictionChecker().run(drg)
        clash = [f for f in findings if f.type == "adr_topic_clash"]
        assert len(clash) == 1
        assert clash[0].severity == "high"
        assert "logging" in clash[0].id

    def test_two_adrs_same_topic_same_decision_no_finding(self):
        adr1 = _make_node("adr:ADR-001", "adr", topic="logging", decision="use structlog")
        adr2 = _make_node("adr:ADR-002", "adr", topic="logging", decision="use structlog")
        drg = _make_drg(nodes=[adr1, adr2])
        findings = ContradictionChecker().run(drg)
        clash = [f for f in findings if f.type == "adr_topic_clash"]
        assert clash == []

    def test_single_adr_per_topic_no_finding(self):
        adr1 = _make_node("adr:ADR-001", "adr", topic="logging", decision="use structlog")
        drg = _make_drg(nodes=[adr1])
        findings = ContradictionChecker().run(drg)
        assert findings == []

    def test_adr_without_topic_ignored(self):
        adr1 = _make_node("adr:ADR-001", "adr", label="No topic here")
        drg = _make_drg(nodes=[adr1])
        findings = ContradictionChecker().run(drg)
        assert findings == []

    def test_feature_scope_propagated(self):
        adr1 = _make_node("adr:ADR-001", "adr", topic="db", decision="postgres")
        adr2 = _make_node("adr:ADR-002", "adr", topic="db", decision="mysql")
        drg = _make_drg(nodes=[adr1, adr2])
        findings = ContradictionChecker().run(drg, feature_scope="my-feature")
        assert any(f.feature_id == "my-feature" for f in findings)


# ---------------------------------------------------------------------------
# Tests — duplicate glossary senses
# ---------------------------------------------------------------------------


class TestDuplicateGlossarySenses:
    def test_two_glossary_nodes_same_label_flagged(self):
        g1 = _make_node("glossary:workspace-v1", "glossary_scope", "Workspace")
        g2 = _make_node("glossary:workspace-v2", "glossary_scope", "Workspace")
        drg = _make_drg(nodes=[g1, g2])
        findings = ContradictionChecker().run(drg)
        dupes = [f for f in findings if f.type == "duplicate_glossary_sense"]
        assert len(dupes) == 1
        assert dupes[0].severity == "medium"

    def test_case_insensitive_label_comparison(self):
        g1 = _make_node("glossary:ws-upper", "glossary_scope", "Workspace")
        g2 = _make_node("glossary:ws-lower", "glossary_scope", "workspace")
        drg = _make_drg(nodes=[g1, g2])
        findings = ContradictionChecker().run(drg)
        dupes = [f for f in findings if f.type == "duplicate_glossary_sense"]
        assert len(dupes) == 1

    def test_unique_labels_no_finding(self):
        g1 = _make_node("glossary:workspace", "glossary_scope", "Workspace")
        g2 = _make_node("glossary:worktree", "glossary_scope", "Worktree")
        drg = _make_drg(nodes=[g1, g2])
        findings = ContradictionChecker().run(drg)
        dupes = [f for f in findings if f.type == "duplicate_glossary_sense"]
        assert dupes == []

    def test_glossary_node_without_label_ignored(self):
        g1 = _make_node("glossary:nolabel", "glossary_scope", label=None)
        drg = _make_drg(nodes=[g1])
        findings = ContradictionChecker().run(drg)
        assert findings == []


# ---------------------------------------------------------------------------
# Tests — missing/empty DRG
# ---------------------------------------------------------------------------


class TestContradictionCheckerMissingDRG:
    def test_none_drg_returns_empty(self):
        findings = ContradictionChecker().run(None)
        assert findings == []

    def test_empty_drg_returns_empty(self):
        drg = _make_drg(nodes=[], edges=[])
        findings = ContradictionChecker().run(drg)
        assert findings == []

    def test_drg_with_no_nodes_attr_returns_empty(self):
        drg = SimpleNamespace()
        findings = ContradictionChecker().run(drg)
        assert findings == []
