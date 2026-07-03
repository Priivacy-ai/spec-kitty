"""Tests for LintEngine (T036).

Uses duck-type SimpleNamespace stubs — the real doctrine DRG package is
not required.  All scenarios run without any LLM client.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.charter_runtime.lint.engine import LintEngine
from specify_cli.charter_runtime.lint.findings import DecayReport, GraphState


# ---------------------------------------------------------------------------
# Fixture DRG helpers
# ---------------------------------------------------------------------------


pytestmark = [pytest.mark.unit, pytest.mark.fast]

def _make_node(urn: str, kind: str, label: str | None = None, **kwargs) -> SimpleNamespace:
    return SimpleNamespace(urn=urn, kind=kind, label=label, **kwargs)


def _make_edge(source: str, target: str, relation: str) -> SimpleNamespace:
    return SimpleNamespace(source=source, target=target, relation=relation)


def _make_drg(nodes: list, edges: list | None = None) -> SimpleNamespace:
    node_map = {getattr(n, "urn", ""): n for n in nodes}

    def get_node(urn: str):
        return node_map.get(urn)

    return SimpleNamespace(nodes=nodes, edges=edges or [], get_node=get_node)


def _make_stale_ts() -> str:
    """Return an ISO timestamp 91 days in the past (beyond the 90-day threshold)."""
    stale = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=91)
    return stale.isoformat()


def _build_four_decay_drg() -> SimpleNamespace:
    """Build a DRG with one decay example per category.

    - orphan: a directive node with no incoming "governs" edge
    - contradiction: two ADR nodes with same topic but different decisions
    - staleness: a synthesized_artifact node with a timestamp 91 days old
    - reference_integrity: a WP node referencing a superseded ADR
                           (ADR-new replaces ADR-old via a "replaces" edge)
    """
    # Orphan: directive with no incoming edge
    dir_node = _make_node("directive:DIR-001", "directive", "DIR-001 Governance")

    # Contradiction: two ADRs with the same topic, different decisions
    adr_clash_a = _make_node("adr:ADR-010", "adr", "ADR 010", topic="caching", decision="use redis")
    adr_clash_b = _make_node("adr:ADR-011", "adr", "ADR 011", topic="caching", decision="use memcached")

    # Staleness: synthesized artifact with old timestamp
    stale_node = _make_node(
        "synthesis:SYN-001",
        "synthesized_artifact",
        "Old Synthesis",
        synthesized_at=_make_stale_ts(),
    )

    # Reference integrity: WP references a superseded ADR
    #   - adr:ADR-OLD is the superseded one
    #   - adr:ADR-NEW replaces adr:ADR-OLD (has a "replaces" edge)
    #   - wp:WP-REF references adr:ADR-OLD
    adr_old = _make_node("adr:ADR-OLD", "adr", "ADR Old (superseded)")
    adr_new = _make_node("adr:ADR-NEW", "adr", "ADR New")
    wp_ref = _make_node("wp:WP-REF", "wp", "WP with stale ADR ref")

    # The "replaces" edge: adr:ADR-NEW replaces adr:ADR-OLD
    replaces_edge = _make_edge("adr:ADR-NEW", "adr:ADR-OLD", "replaces")
    # The WP->ADR edge (references superseded ADR)
    wp_ref_edge = _make_edge("wp:WP-REF", "adr:ADR-OLD", "references_adr")

    nodes = [dir_node, adr_clash_a, adr_clash_b, stale_node, adr_old, adr_new, wp_ref]
    edges = [replaces_edge, wp_ref_edge]
    return _make_drg(nodes, edges)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLintEngineAllChecks:
    """T036-S1: all 4 categories detected in the manufactured DRG."""

    def test_all_four_categories_detected(self, tmp_path: Path) -> None:
        drg = _build_four_decay_drg()
        with patch(
            "specify_cli.charter_runtime.lint.engine.load_merged_drg",
            return_value=(drg, GraphState.MERGED),
        ):
            report = LintEngine(tmp_path).run()

        assert len(report.findings) >= 4, (
            f"Expected at least 4 findings, got {len(report.findings)}: "
            + str([f.category for f in report.findings])
        )
        categories = {f.category for f in report.findings}
        assert "orphan" in categories
        assert "contradiction" in categories
        assert "staleness" in categories
        assert "reference_integrity" in categories

    def test_duration_within_limit(self, tmp_path: Path) -> None:
        drg = _build_four_decay_drg()
        with patch(
            "specify_cli.charter_runtime.lint.engine.load_merged_drg",
            return_value=(drg, GraphState.MERGED),
        ):
            report = LintEngine(tmp_path).run()
        assert report.duration_seconds < 5.0

    def test_drg_node_count_nonzero(self, tmp_path: Path) -> None:
        drg = _build_four_decay_drg()
        with patch(
            "specify_cli.charter_runtime.lint.engine.load_merged_drg",
            return_value=(drg, GraphState.MERGED),
        ):
            report = LintEngine(tmp_path).run()
        assert report.drg_node_count > 0


class TestLintReportWritten:
    """T036-S2: lint-report.json is written and parseable (NFR-005)."""

    def test_report_json_written(self, tmp_path: Path) -> None:
        drg = _build_four_decay_drg()
        with patch(
            "specify_cli.charter_runtime.lint.engine.load_merged_drg",
            return_value=(drg, GraphState.MERGED),
        ):
            LintEngine(tmp_path).run()

        report_path = tmp_path / ".kittify" / "lint-report.json"
        assert report_path.exists(), "lint-report.json must exist after run()"
        parsed = json.loads(report_path.read_text(encoding="utf-8"))
        assert "findings" in parsed
        assert "scanned_at" in parsed

    def test_report_json_written_on_empty_drg(self, tmp_path: Path) -> None:
        """lint-report.json is written even when DRG is missing."""
        with patch(
            "specify_cli.charter_runtime.lint.engine.load_merged_drg",
            return_value=(None, GraphState.MISSING),
        ):
            LintEngine(tmp_path).run()

        report_path = tmp_path / ".kittify" / "lint-report.json"
        assert report_path.exists()
        parsed = json.loads(report_path.read_text(encoding="utf-8"))
        assert parsed["finding_count"] == 0


class TestSingleCheckFilter:
    """T036-S3: run(checks={'orphans'}) returns only orphan findings."""

    def test_only_orphan_findings_returned(self, tmp_path: Path) -> None:
        drg = _build_four_decay_drg()
        with patch(
            "specify_cli.charter_runtime.lint.engine.load_merged_drg",
            return_value=(drg, GraphState.MERGED),
        ):
            report = LintEngine(tmp_path).run(checks={"orphans"})

        assert all(f.category == "orphan" for f in report.findings), (
            f"Expected only orphan findings, got: {[(f.category, f.type) for f in report.findings]}"
        )
        non_orphan_categories = {"contradiction", "staleness", "reference_integrity"}
        found_categories = {f.category for f in report.findings}
        assert found_categories.isdisjoint(non_orphan_categories)


class TestSeverityFilter:
    """T036-S4: run(min_severity='high') filters out low/medium findings."""

    def test_low_medium_findings_excluded(self, tmp_path: Path) -> None:
        drg = _build_four_decay_drg()
        with patch(
            "specify_cli.charter_runtime.lint.engine.load_merged_drg",
            return_value=(drg, GraphState.MERGED),
        ):
            report = LintEngine(tmp_path).run(min_severity="high")

        low_or_medium = [f for f in report.findings if f.severity in {"low", "medium"}]
        assert low_or_medium == [], (
            f"Expected no low/medium findings, got: {[(f.severity, f.type) for f in low_or_medium]}"
        )


class TestMissingDRG:
    """T036-S5+S6: missing DRG returns empty DecayReport without raising."""

    def test_missing_drg_returns_empty_report(self, tmp_path: Path) -> None:
        with patch(
            "specify_cli.charter_runtime.lint.engine.load_merged_drg",
            return_value=(None, GraphState.MISSING),
        ):
            report = LintEngine(tmp_path).run()

        assert isinstance(report, DecayReport)
        assert report.findings == []
        assert report.drg_node_count == 0

    def test_missing_drg_does_not_raise(self, tmp_path: Path) -> None:
        with patch(
            "specify_cli.charter_runtime.lint.engine.load_merged_drg",
            return_value=(None, GraphState.MISSING),
        ):
            # Must not raise any exception
            report = LintEngine(tmp_path).run()
        assert report is not None


class TestGraphStateTriState:
    """WP01 / FR-001..FR-004: ``DecayReport.graph_state`` carries the
    tri-state graph identity and is wired through to the JSON payload.

    These tests pin the contract from
    ``docs/adr/3.x/2026-05-24-1-charter-freshness-ux-contract.md``.
    """

    def test_lint_merged_state_unchanged(self, tmp_path: Path) -> None:
        """FR-001: when the project DRG resolves, ``graph_state == merged``."""
        drg = _build_four_decay_drg()
        with patch(
            "specify_cli.charter_runtime.lint.engine.load_merged_drg",
            return_value=(drg, GraphState.MERGED),
        ):
            report = LintEngine(tmp_path).run()
        assert report.graph_state is GraphState.MERGED

    def test_lint_built_in_only_returns_built_in_only_state(
        self, tmp_path: Path
    ) -> None:
        """FR-002: when the project DRG is absent but the built-in graph
        resolves, the engine scans the built-in graph and the report carries
        ``graph_state == built_in_only``.
        """
        drg = _build_four_decay_drg()
        with patch(
            "specify_cli.charter_runtime.lint.engine.load_merged_drg",
            return_value=(drg, GraphState.BUILT_IN_ONLY),
        ):
            report = LintEngine(tmp_path).run()
        assert report.graph_state is GraphState.BUILT_IN_ONLY
        # The checkers ran against the built-in graph, so the manufactured
        # decay surfaces here too — the engine does NOT short-circuit on
        # built_in_only.
        assert len(report.findings) >= 1
        assert report.drg_node_count > 0

    def test_lint_missing_graph_returns_missing_state(self, tmp_path: Path) -> None:
        """FR-001: when no graph is loadable, the report is empty and
        ``graph_state == missing``.
        """
        with patch(
            "specify_cli.charter_runtime.lint.engine.load_merged_drg",
            return_value=(None, GraphState.MISSING),
        ):
            report = LintEngine(tmp_path).run()
        assert report.graph_state is GraphState.MISSING
        assert report.findings == []
        assert report.drg_node_count == 0

    def test_lint_json_includes_graph_state(self, tmp_path: Path) -> None:
        """FR-004: ``report.to_json()`` emits ``graph_state`` at the top level
        and the value is one of the three contract strings.
        """
        drg = _build_four_decay_drg()
        with patch(
            "specify_cli.charter_runtime.lint.engine.load_merged_drg",
            return_value=(drg, GraphState.BUILT_IN_ONLY),
        ):
            report = LintEngine(tmp_path).run()
        payload = json.loads(report.to_json())
        assert "graph_state" in payload, (
            "FR-004: top-level 'graph_state' key MUST be present"
        )
        assert payload["graph_state"] == "built_in_only"

    def test_decay_report_default_graph_state_is_missing(self) -> None:
        """Dataclass default for ``graph_state`` is :attr:`GraphState.MISSING`."""
        report = DecayReport()
        assert report.graph_state is GraphState.MISSING
        # Round-trip through JSON preserves the contract string.
        payload = json.loads(report.to_json())
        assert payload["graph_state"] == "missing"

    def test_filter_by_severity_preserves_graph_state(self) -> None:
        """``filter_by_severity`` MUST carry ``graph_state`` to the new report."""
        report = DecayReport(graph_state=GraphState.BUILT_IN_ONLY)
        filtered = report.filter_by_severity("high")
        assert filtered.graph_state is GraphState.BUILT_IN_ONLY


class TestNoLLMCalls:
    """T036-S7: no LLM client is imported or called inside charter_lint."""

    def test_no_anthropic_import_in_charter_lint(self) -> None:
        """Verify that the charter_lint package does not import anthropic."""
        import sys
        # Check that anthropic is not imported as part of charter_lint loading
        charter_lint_modules = [
            name for name in sys.modules
            if name.startswith("specify_cli.charter_runtime.lint")
        ]
        for mod_name in charter_lint_modules:
            mod = sys.modules[mod_name]
            # Module should not have anthropic in its globals
            mod_globals = getattr(mod, "__dict__", {})
            assert "anthropic" not in mod_globals, (
                f"Module {mod_name} imported 'anthropic'"
            )

    def test_no_openai_import_in_charter_lint(self) -> None:
        """Verify that the charter_lint package does not import openai."""
        import sys
        charter_lint_modules = [
            name for name in sys.modules
            if name.startswith("specify_cli.charter_runtime.lint")
        ]
        for mod_name in charter_lint_modules:
            mod = sys.modules[mod_name]
            mod_globals = getattr(mod, "__dict__", {})
            assert "openai" not in mod_globals, (
                f"Module {mod_name} imported 'openai'"
            )


class TestPerformance:
    """T036-S8: 500-node fixture completes in < 5 seconds."""

    def _build_large_drg(self, node_count: int = 500) -> SimpleNamespace:
        """Build a synthetic DRG with node_count nodes and some manufactured decay."""
        nodes = []
        edges = []

        # Add some ADR nodes with topic clash (contradiction)
        nodes.append(_make_node("adr:ADR-001", "adr", "ADR 001", topic="perf", decision="cache all"))
        nodes.append(_make_node("adr:ADR-002", "adr", "ADR 002", topic="perf", decision="cache none"))

        # Fill the rest with generic wp nodes
        for i in range(3, node_count + 1):
            nodes.append(_make_node(f"wp:WP-{i:04d}", "wp", f"WP {i}"))

        # Add a few edges
        edges.append(_make_edge("wp:WP-0003", "adr:ADR-001", "references"))

        return _make_drg(nodes, edges)

    def test_large_drg_completes_in_time(self, tmp_path: Path) -> None:
        drg = self._build_large_drg(500)
        with patch(
            "specify_cli.charter_runtime.lint.engine.load_merged_drg",
            return_value=(drg, GraphState.MERGED),
        ):
            report = LintEngine(tmp_path).run()
        assert report.duration_seconds < 5.0
        assert report.drg_node_count == 500
