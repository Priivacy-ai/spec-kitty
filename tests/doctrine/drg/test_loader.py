"""Unit tests for DRG loader (T007)."""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.drg.loader import DRGLoadError, load_graph, merge_layers
from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation


class TestLoadGraph:
    def test_load_valid_graph(self, valid_graph_path: Path) -> None:
        graph = load_graph(valid_graph_path)
        assert graph.schema_version == "1.0"
        assert len(graph.nodes) == 11
        assert len(graph.edges) == 15
        assert graph.generated_by == "drg-migration-v1"

    def test_load_empty_graph(self, empty_graph_path: Path) -> None:
        graph = load_graph(empty_graph_path)
        assert graph.nodes == []
        assert graph.edges == []

    def test_load_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(DRGLoadError, match="File not found"):
            load_graph(tmp_path / "nonexistent.yaml")

    def test_load_invalid_yaml(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("{{{{not valid yaml: [")
        with pytest.raises(DRGLoadError, match="YAML parse error"):
            load_graph(bad_file)

    def test_load_non_mapping_yaml(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "list.yaml"
        bad_file.write_text("- item1\n- item2\n")
        with pytest.raises(DRGLoadError, match="Expected a YAML mapping"):
            load_graph(bad_file)

    def test_load_validation_error(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad_schema.yaml"
        bad_file.write_text(
            'schema_version: "2.0"\ngenerated_at: "x"\ngenerated_by: "x"\nnodes: []\nedges: []\n'
        )
        with pytest.raises(DRGLoadError, match="Validation error"):
            load_graph(bad_file)

    def test_load_kind_mismatch_raises(self, fixtures_dir: Path) -> None:
        with pytest.raises(DRGLoadError, match="Validation error"):
            load_graph(fixtures_dir / "kind_mismatch_graph.yaml")

    def test_load_malformed_urn_raises(self, fixtures_dir: Path) -> None:
        with pytest.raises(DRGLoadError, match="Validation error"):
            load_graph(fixtures_dir / "malformed_urn_graph.yaml")


class TestMergeLayers:
    @pytest.fixture()
    def shipped(self) -> DRGGraph:
        return DRGGraph(
            schema_version="1.0",
            generated_at="2026-04-13T10:00:00+00:00",
            generated_by="test",
            nodes=[
                DRGNode(urn="directive:A", kind=NodeKind.DIRECTIVE, label="Shipped A"),
                DRGNode(urn="tactic:B", kind=NodeKind.TACTIC, label="Shipped B"),
            ],
            edges=[
                DRGEdge(source="directive:A", target="tactic:B", relation=Relation.REQUIRES),
            ],
        )

    def test_merge_none_project_returns_shipped(self, shipped: DRGGraph) -> None:
        result = merge_layers(shipped, None)
        assert result is shipped

    def test_merge_adds_new_nodes(self, shipped: DRGGraph) -> None:
        project = DRGGraph(
            schema_version="1.0",
            generated_at="2026-04-13T10:00:00+00:00",
            generated_by="test",
            nodes=[
                DRGNode(urn="tactic:C", kind=NodeKind.TACTIC, label="Project C"),
            ],
            edges=[],
        )
        result = merge_layers(shipped, project)
        assert result.node_urns() == {"directive:A", "tactic:B", "tactic:C"}

    def test_merge_overrides_label(self, shipped: DRGGraph) -> None:
        project = DRGGraph(
            schema_version="1.0",
            generated_at="2026-04-13T10:00:00+00:00",
            generated_by="test",
            nodes=[
                DRGNode(urn="directive:A", kind=NodeKind.DIRECTIVE, label="Overridden A"),
            ],
            edges=[],
        )
        result = merge_layers(shipped, project)
        node = result.get_node("directive:A")
        assert node is not None
        assert node.label == "Overridden A"

    def test_merge_does_not_override_label_when_none(self, shipped: DRGGraph) -> None:
        project = DRGGraph(
            schema_version="1.0",
            generated_at="2026-04-13T10:00:00+00:00",
            generated_by="test",
            nodes=[
                DRGNode(urn="directive:A", kind=NodeKind.DIRECTIVE),
            ],
            edges=[],
        )
        result = merge_layers(shipped, project)
        node = result.get_node("directive:A")
        assert node is not None
        assert node.label == "Shipped A"

    def test_merge_adds_edges(self, shipped: DRGGraph) -> None:
        project = DRGGraph(
            schema_version="1.0",
            generated_at="2026-04-13T10:00:00+00:00",
            generated_by="test",
            nodes=[],
            edges=[
                DRGEdge(source="directive:A", target="tactic:B", relation=Relation.SUGGESTS),
            ],
        )
        result = merge_layers(shipped, project)
        assert len(result.edges) == 2

    def test_merge_does_not_remove_shipped_nodes(self, shipped: DRGGraph) -> None:
        project = DRGGraph(
            schema_version="1.0",
            generated_at="2026-04-13T10:00:00+00:00",
            generated_by="test",
            nodes=[],
            edges=[],
        )
        result = merge_layers(shipped, project)
        assert result.node_urns() == shipped.node_urns()

    def test_merge_does_not_remove_shipped_edges(self, shipped: DRGGraph) -> None:
        project = DRGGraph(
            schema_version="1.0",
            generated_at="2026-04-13T10:00:00+00:00",
            generated_by="test",
            nodes=[],
            edges=[],
        )
        result = merge_layers(shipped, project)
        assert len(result.edges) == len(shipped.edges)

    def test_merge_preserves_metadata(self, shipped: DRGGraph) -> None:
        project = DRGGraph(
            schema_version="1.0",
            generated_at="2026-05-01T00:00:00+00:00",
            generated_by="project-override",
            nodes=[],
            edges=[],
        )
        result = merge_layers(shipped, project)
        # Metadata comes from shipped
        assert result.generated_at == shipped.generated_at
        assert result.generated_by == shipped.generated_by
