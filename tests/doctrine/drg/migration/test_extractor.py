"""Tests for doctrine.drg.migration.extractor.

Includes:
- T012/T013 unit tests against real shipped doctrine
- T016 end-to-end graph generation
- T017 edge-count completeness validation
- Idempotency verification
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from doctrine.drg.migration.calibrator import measure_surface
from doctrine.drg.migration.extractor import (
    _SKIP_REF_TYPES,
    extract_action_edges,
    extract_artifact_edges,
    generate_graph,
)
from doctrine.drg.models import DRGGraph, NodeKind, Relation
from doctrine.drg.validator import validate_graph

# Path to the shipped doctrine root inside the repo.
DOCTRINE_ROOT: Path = Path(__file__).resolve().parents[4] / "src" / "doctrine"

_yaml = YAML(typ="safe")


def _count_inline_refs(doctrine_root: Path) -> int:
    """Count every inline reference field entry across all shipped artifacts.

    This mirrors the extraction logic but only counts -- used for the T017
    completeness assertion.
    """
    total = 0

    # Directives
    directives_dir = doctrine_root / "directives" / "shipped"
    if directives_dir.is_dir():
        for path in sorted(directives_dir.glob("*.directive.yaml")):
            data: Any = _yaml.load(path)
            if not data:
                continue
            total += len(data.get("tactic_refs", []) or [])
            for ref in data.get("references", []) or []:
                if ref.get("type", "") not in _SKIP_REF_TYPES:
                    total += 1
            for opp in data.get("opposed_by", []) or []:
                if opp.get("type", "") not in _SKIP_REF_TYPES:
                    total += 1

    # Tactics
    tactics_dir = doctrine_root / "tactics" / "shipped"
    if tactics_dir.is_dir():
        for path in sorted(tactics_dir.rglob("*.tactic.yaml")):
            data = _yaml.load(path)
            if not data:
                continue
            for ref in data.get("references", []) or []:
                if ref.get("type", "") not in _SKIP_REF_TYPES:
                    total += 1
            for step in data.get("steps", []) or []:
                for ref in step.get("references", []) or []:
                    if ref.get("type", "") not in _SKIP_REF_TYPES:
                        total += 1

    # Paradigms
    paradigms_dir = doctrine_root / "paradigms" / "shipped"
    if paradigms_dir.is_dir():
        for path in sorted(paradigms_dir.glob("*.paradigm.yaml")):
            data = _yaml.load(path)
            if not data:
                continue
            total += len(data.get("tactic_refs", []) or [])
            total += len(data.get("directive_refs", []) or [])
            for opp in data.get("opposed_by", []) or []:
                if opp.get("type", "") not in _SKIP_REF_TYPES:
                    total += 1

    # Action indices
    missions_dir = doctrine_root / "missions"
    if missions_dir.is_dir():
        for index_path in sorted(missions_dir.rglob("actions/*/index.yaml")):
            data = _yaml.load(index_path)
            if not data:
                continue
            for field in ("directives", "tactics", "styleguides", "toolguides", "procedures"):
                total += len(data.get(field, []) or [])

    return total


# ---------------------------------------------------------------------------
# T012: Artifact walker tests
# ---------------------------------------------------------------------------


@pytest.mark.doctrine
class TestExtractArtifactEdges:
    def test_returns_nodes_and_edges(self) -> None:
        nodes, edges = extract_artifact_edges(DOCTRINE_ROOT)
        assert len(nodes) > 0
        assert len(edges) > 0

    def test_directive_nodes_present(self) -> None:
        nodes, _ = extract_artifact_edges(DOCTRINE_ROOT)
        directive_urns = {n.urn for n in nodes if n.kind == NodeKind.DIRECTIVE}
        # We know DIRECTIVE_001, DIRECTIVE_024, DIRECTIVE_003 exist
        assert "directive:DIRECTIVE_001" in directive_urns
        assert "directive:DIRECTIVE_024" in directive_urns
        assert "directive:DIRECTIVE_003" in directive_urns

    def test_tactic_nodes_present(self) -> None:
        nodes, _ = extract_artifact_edges(DOCTRINE_ROOT)
        tactic_urns = {n.urn for n in nodes if n.kind == NodeKind.TACTIC}
        assert "tactic:tdd-red-green-refactor" in tactic_urns
        assert "tactic:adr-drafting-workflow" in tactic_urns

    def test_paradigm_nodes_present(self) -> None:
        nodes, _ = extract_artifact_edges(DOCTRINE_ROOT)
        paradigm_urns = {n.urn for n in nodes if n.kind == NodeKind.PARADIGM}
        assert "paradigm:domain-driven-design" in paradigm_urns
        assert "paradigm:atomic-design" in paradigm_urns
        assert "paradigm:c4-incremental-detail-modeling" in paradigm_urns

    def test_no_duplicate_nodes(self) -> None:
        nodes, _ = extract_artifact_edges(DOCTRINE_ROOT)
        urns = [n.urn for n in nodes]
        assert len(urns) == len(set(urns)), "Duplicate node URNs found"

    def test_directive_tactic_refs_produce_requires(self) -> None:
        """Directive tactic_refs should produce 'requires' edges."""
        _, edges = extract_artifact_edges(DOCTRINE_ROOT)
        # DIRECTIVE_001 has tactic_refs including adr-drafting-workflow
        d001_requires = [
            e for e in edges
            if e.source == "directive:DIRECTIVE_001"
            and e.relation == Relation.REQUIRES
        ]
        assert len(d001_requires) > 0
        targets = {e.target for e in d001_requires}
        assert "tactic:adr-drafting-workflow" in targets

    def test_directive_opposed_by_produces_replaces(self) -> None:
        """Directive opposed_by should produce 'replaces' edges."""
        _, edges = extract_artifact_edges(DOCTRINE_ROOT)
        d024_replaces = [
            e for e in edges
            if e.source == "directive:DIRECTIVE_024"
            and e.relation == Relation.REPLACES
        ]
        assert len(d024_replaces) == 1
        assert d024_replaces[0].target == "directive:DIRECTIVE_025"

    def test_paradigm_directive_refs_normalised(self) -> None:
        """Paradigm directive_refs (DIRECTIVE_NNN format) should be normalised."""
        _, edges = extract_artifact_edges(DOCTRINE_ROOT)
        ddd_requires = [
            e for e in edges
            if e.source == "paradigm:domain-driven-design"
            and e.relation == Relation.REQUIRES
            and e.target.startswith("directive:")
        ]
        targets = {e.target for e in ddd_requires}
        assert "directive:DIRECTIVE_001" in targets
        assert "directive:DIRECTIVE_031" in targets
        assert "directive:DIRECTIVE_032" in targets

    def test_tactic_references_produce_suggests(self) -> None:
        """Tactic references should produce 'suggests' edges."""
        _, edges = extract_artifact_edges(DOCTRINE_ROOT)
        pd_suggests = [
            e for e in edges
            if e.source == "tactic:problem-decomposition"
            and e.relation == Relation.SUGGESTS
        ]
        # problem-decomposition has 4 top-level refs (skipping template)
        # -> eisenhower-prioritisation, stakeholder-alignment, review-intent-and-risk-first
        targets = {e.target for e in pd_suggests}
        assert "tactic:eisenhower-prioritisation" in targets

    def test_walks_all_shipped_directives(self) -> None:
        nodes, _ = extract_artifact_edges(DOCTRINE_ROOT)
        directive_count = len(
            list(
                (DOCTRINE_ROOT / "directives" / "shipped").glob("*.directive.yaml")
            )
        )
        graph_directive_nodes = [
            n for n in nodes
            if n.kind == NodeKind.DIRECTIVE and n.label is not None
        ]
        # Each shipped directive should appear as a labelled node
        assert len(graph_directive_nodes) >= directive_count

    def test_walks_all_shipped_paradigms(self) -> None:
        nodes, _ = extract_artifact_edges(DOCTRINE_ROOT)
        paradigm_files = list(
            (DOCTRINE_ROOT / "paradigms" / "shipped").glob("*.paradigm.yaml")
        )
        graph_paradigm_nodes = [
            n for n in nodes
            if n.kind == NodeKind.PARADIGM and n.label is not None
        ]
        assert len(graph_paradigm_nodes) == len(paradigm_files)


# ---------------------------------------------------------------------------
# T013: Action index walker tests
# ---------------------------------------------------------------------------


@pytest.mark.doctrine
class TestExtractActionEdges:
    def test_returns_nodes_and_edges(self) -> None:
        nodes, edges = extract_action_edges(DOCTRINE_ROOT)
        assert len(nodes) > 0
        assert len(edges) > 0

    def test_action_nodes_created(self) -> None:
        nodes, _ = extract_action_edges(DOCTRINE_ROOT)
        action_urns = {n.urn for n in nodes if n.kind == NodeKind.ACTION}
        expected = {
            "action:software-dev/specify",
            "action:software-dev/plan",
            "action:software-dev/tasks",
            "action:software-dev/implement",
            "action:software-dev/review",
        }
        assert expected.issubset(action_urns)

    def test_directive_slugs_normalised(self) -> None:
        """Directive slugs in action indices should be normalised to DIRECTIVE_NNN."""
        _, edges = extract_action_edges(DOCTRINE_ROOT)
        implement_edges = [
            e for e in edges
            if e.source == "action:software-dev/implement"
            and e.target.startswith("directive:")
        ]
        for edge in implement_edges:
            assert edge.target.startswith("directive:DIRECTIVE_")

    def test_scope_edges_only(self) -> None:
        """All action edges should be scope edges."""
        _, edges = extract_action_edges(DOCTRINE_ROOT)
        for edge in edges:
            assert edge.relation == Relation.SCOPE

    def test_empty_lists_produce_no_edges(self) -> None:
        """Empty styleguides/toolguides/procedures lists should produce no edges."""
        _, edges = extract_action_edges(DOCTRINE_ROOT)
        specify_edges = [
            e for e in edges
            if e.source == "action:software-dev/specify"
        ]
        # specify has 2 directives + 1 tactic = 3 scope edges
        assert len(specify_edges) == 3

    def test_tasks_action_has_six_refs(self) -> None:
        """The new tasks action index should produce 6 scope edges."""
        _, edges = extract_action_edges(DOCTRINE_ROOT)
        tasks_edges = [
            e for e in edges
            if e.source == "action:software-dev/tasks"
        ]
        assert len(tasks_edges) == 6

    def test_nonexistent_doctrine_root(self) -> None:
        nodes, edges = extract_action_edges(Path("/nonexistent"))
        assert nodes == []
        assert edges == []


# ---------------------------------------------------------------------------
# T016: generate_graph end-to-end
# ---------------------------------------------------------------------------


@pytest.mark.doctrine
class TestGenerateGraph:
    def test_generates_valid_graph(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        errors = validate_graph(graph)
        assert errors == [], f"Validation errors: {errors}"

    def test_graph_file_exists(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        generate_graph(DOCTRINE_ROOT, output)
        assert output.exists()

    def test_schema_version(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        assert graph.schema_version == "1.0"

    def test_generated_by(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        assert graph.generated_by == "drg-migration-v1"

    def test_all_node_urns_unique(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        urns = [n.urn for n in graph.nodes]
        assert len(urns) == len(set(urns))

    def test_all_edge_triples_unique(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        triples = [(e.source, e.target, e.relation.value) for e in graph.edges]
        assert len(triples) == len(set(triples))

    def test_idempotent(self, tmp_path: Path) -> None:
        """Running generate_graph twice must produce identical output."""
        out1 = tmp_path / "graph1.yaml"
        out2 = tmp_path / "graph2.yaml"
        generate_graph(DOCTRINE_ROOT, out1)
        generate_graph(DOCTRINE_ROOT, out2)
        h1 = hashlib.sha256(out1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(out2.read_bytes()).hexdigest()
        assert h1 == h2, "generate_graph is not idempotent"

    def test_surface_inequalities(self, tmp_path: Path) -> None:
        """Verify governance surface inequalities after calibration."""
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)

        specify = measure_surface("action:software-dev/specify", graph.edges)
        plan = measure_surface("action:software-dev/plan", graph.edges)
        tasks = measure_surface("action:software-dev/tasks", graph.edges)
        implement = measure_surface("action:software-dev/implement", graph.edges)
        review = measure_surface("action:software-dev/review", graph.edges)

        assert specify < plan, f"|specify| ({specify}) should be < |plan| ({plan})"
        assert plan < implement, f"|plan| ({plan}) should be < |implement| ({implement})"
        assert tasks < implement, f"|tasks| ({tasks}) should be < |implement| ({implement})"
        assert review >= 0.80 * implement, (
            f"|review| ({review}) should be >= 80% of |implement| ({implement})"
        )

    def test_discovers_styleguide_nodes(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        styleguide_nodes = [n for n in graph.nodes if n.kind == NodeKind.STYLEGUIDE]
        # At least the shipped styleguides should be present
        assert len(styleguide_nodes) >= 1

    def test_discovers_toolguide_nodes(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        toolguide_nodes = [n for n in graph.nodes if n.kind == NodeKind.TOOLGUIDE]
        assert len(toolguide_nodes) >= 1

    def test_discovers_procedure_nodes(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        procedure_nodes = [n for n in graph.nodes if n.kind == NodeKind.PROCEDURE]
        assert len(procedure_nodes) >= 1


# ---------------------------------------------------------------------------
# T017: Edge-count completeness validation
# ---------------------------------------------------------------------------


@pytest.mark.doctrine
class TestEdgeCountCompleteness:
    def test_edge_count_gte_inline_refs(self, tmp_path: Path) -> None:
        """Total edge count must be >= total inline reference field count.

        The >= accounts for calibration-added edges.
        """
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        total_inline = _count_inline_refs(DOCTRINE_ROOT)
        assert len(graph.edges) >= total_inline, (
            f"Edge count ({len(graph.edges)}) < inline refs ({total_inline}). "
            f"Some references were dropped."
        )

    def test_per_directive_edges_complete(self) -> None:
        """Each directive's inline refs should have corresponding edges."""
        _, edges = extract_artifact_edges(DOCTRINE_ROOT)
        directives_dir = DOCTRINE_ROOT / "directives" / "shipped"
        for path in sorted(directives_dir.glob("*.directive.yaml")):
            data: Any = _yaml.load(path)
            if not data:
                continue
            src_id = data.get("id", "")
            src_urn = f"directive:{src_id}"
            src_edges = [e for e in edges if e.source == src_urn]

            expected_count = len(data.get("tactic_refs", []) or [])
            for ref in data.get("references", []) or []:
                if ref.get("type", "") not in _SKIP_REF_TYPES:
                    expected_count += 1
            for opp in data.get("opposed_by", []) or []:
                if opp.get("type", "") not in _SKIP_REF_TYPES:
                    expected_count += 1

            assert len(src_edges) >= expected_count, (
                f"{path.name}: expected >= {expected_count} edges from "
                f"{src_urn}, found {len(src_edges)}"
            )

    def test_per_paradigm_edges_complete(self) -> None:
        """Each paradigm's inline refs should have corresponding edges."""
        _, edges = extract_artifact_edges(DOCTRINE_ROOT)
        paradigms_dir = DOCTRINE_ROOT / "paradigms" / "shipped"
        for path in sorted(paradigms_dir.glob("*.paradigm.yaml")):
            data: Any = _yaml.load(path)
            if not data:
                continue
            src_id = data.get("id", "")
            src_urn = f"paradigm:{src_id}"
            src_edges = [e for e in edges if e.source == src_urn]

            expected_count = (
                len(data.get("tactic_refs", []) or [])
                + len(data.get("directive_refs", []) or [])
            )
            for opp in data.get("opposed_by", []) or []:
                if opp.get("type", "") not in _SKIP_REF_TYPES:
                    expected_count += 1

            assert len(src_edges) >= expected_count, (
                f"{path.name}: expected >= {expected_count} edges from "
                f"{src_urn}, found {len(src_edges)}"
            )

    def test_per_action_edges_complete(self) -> None:
        """Each action's scope refs should have corresponding edges."""
        _, edges = extract_action_edges(DOCTRINE_ROOT)
        missions_dir = DOCTRINE_ROOT / "missions"
        for index_path in sorted(missions_dir.rglob("actions/*/index.yaml")):
            data: Any = _yaml.load(index_path)
            if not data:
                continue
            action_name = data.get("action", index_path.parent.name)
            mission_name = index_path.parent.parent.parent.name
            action_urn = f"action:{mission_name}/{action_name}"
            action_edges = [e for e in edges if e.source == action_urn]

            expected_count = 0
            for field in ("directives", "tactics", "styleguides", "toolguides", "procedures"):
                expected_count += len(data.get(field, []) or [])

            assert len(action_edges) == expected_count, (
                f"{action_name}: expected {expected_count} edges, "
                f"found {len(action_edges)}"
            )
