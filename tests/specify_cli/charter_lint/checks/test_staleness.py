"""Tests for StalenessChecker.

Uses duck-type SimpleNamespace stubs — the real doctrine DRG package is
not required.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from types import SimpleNamespace


from specify_cli.charter_lint.checks.staleness import StalenessChecker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_days_ago(days: int) -> str:
    """Return an ISO-8601 UTC string for *days* ago."""
    dt = datetime.now(tz=UTC) - timedelta(days=days)
    return dt.isoformat()


def _make_node(urn: str, kind: str, label: str | None = None, **kwargs) -> SimpleNamespace:
    return SimpleNamespace(urn=urn, kind=kind, label=label, **kwargs)


def _make_drg(nodes: list, edges: list | None = None) -> SimpleNamespace:
    node_map = {getattr(n, "urn", ""): n for n in nodes}

    def get_node(urn: str):
        return node_map.get(urn)

    return SimpleNamespace(nodes=nodes, edges=edges or [], get_node=get_node)


# ---------------------------------------------------------------------------
# Tests — stale synthesized artifacts
# ---------------------------------------------------------------------------


class TestStaleSynthesizedArtifact:
    def test_old_synthesis_node_flagged(self):
        node = _make_node(
            "synthesis:retro-2024",
            "synthesis",
            "Retro 2024-01",
            synthesized_at=_utc_days_ago(200),
        )
        drg = _make_drg(nodes=[node])
        findings = StalenessChecker(staleness_threshold_days=90).run(drg)
        stale = [f for f in findings if f.type == "stale_synthesized_artifact"]
        assert len(stale) == 1
        assert stale[0].severity == "medium"
        assert stale[0].id == "synthesis:retro-2024"

    def test_retro_finding_node_flagged(self):
        node = _make_node(
            "retro:finding-001",
            "retro_finding",
            updated_at=_utc_days_ago(120),
        )
        drg = _make_drg(nodes=[node])
        findings = StalenessChecker(staleness_threshold_days=90).run(drg)
        assert any(f.type == "stale_synthesized_artifact" for f in findings)

    def test_fresh_node_no_finding(self):
        node = _make_node(
            "synthesis:recent",
            "synthesis",
            synthesized_at=_utc_days_ago(10),
        )
        drg = _make_drg(nodes=[node])
        findings = StalenessChecker(staleness_threshold_days=90).run(drg)
        stale = [f for f in findings if f.type == "stale_synthesized_artifact"]
        assert stale == []

    def test_node_without_timestamp_no_finding(self):
        node = _make_node("synthesis:no-ts", "synthesis")
        drg = _make_drg(nodes=[node])
        findings = StalenessChecker(staleness_threshold_days=90).run(drg)
        assert findings == []

    def test_non_synthesized_kind_ignored(self):
        node = _make_node(
            "adr:ADR-001",
            "adr",
            synthesized_at=_utc_days_ago(200),
        )
        drg = _make_drg(nodes=[node])
        findings = StalenessChecker(staleness_threshold_days=90).run(drg)
        stale = [f for f in findings if f.type == "stale_synthesized_artifact"]
        assert stale == []

    def test_feature_scope_propagated(self):
        node = _make_node("synthesis:x", "synthesis", synthesized_at=_utc_days_ago(200))
        drg = _make_drg(nodes=[node])
        findings = StalenessChecker().run(drg, feature_scope="feat-001")
        assert any(f.feature_id == "feat-001" for f in findings)

    def test_custom_threshold_respected(self):
        node = _make_node("synthesis:y", "synthesis", synthesized_at=_utc_days_ago(30))
        drg = _make_drg(nodes=[node])
        # With 20-day threshold, a 30-day-old node should be flagged
        findings_20 = StalenessChecker(staleness_threshold_days=20).run(drg)
        assert any(f.type == "stale_synthesized_artifact" for f in findings_20)
        # With 90-day threshold, it should not be flagged
        findings_90 = StalenessChecker(staleness_threshold_days=90).run(drg)
        assert not any(f.type == "stale_synthesized_artifact" for f in findings_90)


# ---------------------------------------------------------------------------
# Tests — dangling context sources
# ---------------------------------------------------------------------------


class TestDanglingContextSources:
    def test_profile_with_dangling_context_source_flagged(self):
        profile = _make_node(
            "agent_profile:implementer",
            "agent_profile",
            "Implementer Profile",
            context_sources=["adr:ADR-DELETED"],
        )
        drg = _make_drg(nodes=[profile])
        findings = StalenessChecker().run(drg)
        dangling = [f for f in findings if f.type == "dangling_context_source"]
        assert len(dangling) == 1
        assert dangling[0].severity == "low"
        assert "ADR-DELETED" in dangling[0].message

    def test_profile_with_valid_context_source_no_finding(self):
        adr_node = _make_node("adr:ADR-001", "adr")
        profile = _make_node(
            "agent_profile:implementer",
            "agent_profile",
            context_sources=["adr:ADR-001"],
        )
        drg = _make_drg(nodes=[adr_node, profile])
        findings = StalenessChecker().run(drg)
        dangling = [f for f in findings if f.type == "dangling_context_source"]
        assert dangling == []

    def test_profile_with_empty_context_sources_no_finding(self):
        profile = _make_node(
            "agent_profile:reviewer",
            "agent_profile",
            context_sources=[],
        )
        drg = _make_drg(nodes=[profile])
        findings = StalenessChecker().run(drg)
        assert not any(f.type == "dangling_context_source" for f in findings)


# ---------------------------------------------------------------------------
# Tests — missing/empty DRG
# ---------------------------------------------------------------------------


class TestStalenessCheckerMissingDRG:
    def test_none_drg_returns_empty(self):
        findings = StalenessChecker().run(None)
        assert findings == []

    def test_empty_drg_returns_empty(self):
        drg = _make_drg(nodes=[], edges=[])
        findings = StalenessChecker().run(drg)
        assert findings == []

    def test_drg_with_no_nodes_attr_returns_empty(self):
        drg = SimpleNamespace()
        findings = StalenessChecker().run(drg)
        assert findings == []
