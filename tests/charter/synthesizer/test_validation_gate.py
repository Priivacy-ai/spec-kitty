"""Tests for src/charter/synthesizer/validation_gate.py (T022).

Covers:
- Accept valid overlay (merged graph passes validate_graph).
- Reject dangling URN (one case per link direction: dangling source, dangling target).
- Reject duplicate edge.
- Reject cycle in requires.
- Fail-closed within 5s (NFR-004).
- ProjectDRGValidationError contains the offending URN + artifact + source reference.
- Missing / malformed overlay file surfaced as structured error.
"""

from __future__ import annotations

import io
import time
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from charter.synthesizer.errors import ProjectDRGValidationError
from charter.synthesizer.validation_gate import validate
from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_shipped_graph(
    nodes: list[tuple[str, NodeKind]] | None = None,
    edges: list[tuple[str, str, Relation]] | None = None,
) -> DRGGraph:
    drg_nodes = [DRGNode(urn=urn, kind=kind) for urn, kind in (nodes or [])]
    drg_edges = [DRGEdge(source=src, target=tgt, relation=rel) for src, tgt, rel in (edges or [])]
    return DRGGraph(
        schema_version="1.0",
        generated_at="2026-04-17T00:00:00+00:00",
        generated_by="test-shipped-layer",
        nodes=drg_nodes,
        edges=drg_edges,
    )


def _write_overlay(staging_dir: Path, graph: DRGGraph) -> None:
    """Write a DRGGraph YAML to staging_dir/doctrine/graph.yaml."""
    doctrine_dir = staging_dir / "doctrine"
    doctrine_dir.mkdir(parents=True, exist_ok=True)
    graph_path = doctrine_dir / "graph.yaml"

    nodes_data = [{"urn": n.urn, "kind": n.kind.value, **({"label": n.label} if n.label else {})} for n in graph.nodes]
    edges_data = [{"source": e.source, "target": e.target, "relation": e.relation.value} for e in graph.edges]
    payload = {
        "schema_version": graph.schema_version,
        "generated_at": graph.generated_at,
        "generated_by": graph.generated_by,
        "nodes": nodes_data,
        "edges": edges_data,
    }
    yaml = YAML()
    yaml.default_flow_style = False
    buf = io.StringIO()
    yaml.dump(payload, buf)
    graph_path.write_text(buf.getvalue())


def _make_overlay(
    nodes: list[tuple[str, NodeKind]] | None = None,
    edges: list[tuple[str, str, Relation]] | None = None,
) -> DRGGraph:
    drg_nodes = [DRGNode(urn=urn, kind=kind) for urn, kind in (nodes or [])]
    drg_edges = [DRGEdge(source=src, target=tgt, relation=rel) for src, tgt, rel in (edges or [])]
    return DRGGraph(
        schema_version="1.0",
        generated_at="2026-04-17T12:00:00+00:00",
        generated_by="spec-kitty charter synthesize 0.1.0",
        nodes=drg_nodes,
        edges=drg_edges,
    )


# ---------------------------------------------------------------------------
# 1. Accept valid overlay
# ---------------------------------------------------------------------------


class TestAcceptValidOverlay:
    """validate() must not raise when merged graph is valid."""

    def test_empty_overlay_with_empty_shipped(self, tmp_path: Path) -> None:
        overlay = _make_overlay()
        _write_overlay(tmp_path, overlay)
        shipped = _make_shipped_graph()
        # Should not raise
        validate(tmp_path, shipped)

    def test_project_node_with_shipped_node(self, tmp_path: Path) -> None:
        shipped = _make_shipped_graph(nodes=[("directive:DIRECTIVE_003", NodeKind.DIRECTIVE)])
        overlay = _make_overlay(
            nodes=[("directive:PROJECT_001", NodeKind.DIRECTIVE)],
            edges=[("directive:PROJECT_001", "directive:DIRECTIVE_003", Relation.REQUIRES)],
        )
        _write_overlay(tmp_path, overlay)
        validate(tmp_path, shipped)  # no raise

    def test_multiple_project_nodes_no_edges(self, tmp_path: Path) -> None:
        shipped = _make_shipped_graph()
        overlay = _make_overlay(
            nodes=[
                ("directive:PROJECT_001", NodeKind.DIRECTIVE),
                ("tactic:how-we-apply-p1", NodeKind.TACTIC),
            ]
        )
        _write_overlay(tmp_path, overlay)
        validate(tmp_path, shipped)  # no raise


# ---------------------------------------------------------------------------
# 2. Reject dangling source URN
# ---------------------------------------------------------------------------


class TestRejectDanglingSourceUrn:
    """Edge whose source does not exist → validation failure."""

    def test_dangling_source_raises_error(self, tmp_path: Path) -> None:
        shipped = _make_shipped_graph(nodes=[("directive:DIRECTIVE_003", NodeKind.DIRECTIVE)])
        # Overlay edge source "directive:PROJECT_999" is not in shipped or overlay nodes
        overlay = _make_overlay(
            nodes=[("directive:PROJECT_001", NodeKind.DIRECTIVE)],
            edges=[
                # source is a non-existent node
                ("directive:PROJECT_999", "directive:DIRECTIVE_003", Relation.REQUIRES),
            ],
        )
        _write_overlay(tmp_path, overlay)
        with pytest.raises(ProjectDRGValidationError) as exc_info:
            validate(tmp_path, shipped)
        err = exc_info.value
        assert any("PROJECT_999" in e for e in err.errors)

    def test_error_mentions_offending_urn(self, tmp_path: Path) -> None:
        shipped = _make_shipped_graph()
        overlay = _make_overlay(
            nodes=[("directive:PROJECT_001", NodeKind.DIRECTIVE)],
            edges=[("directive:MISSING_SOURCE", "directive:PROJECT_001", Relation.REQUIRES)],
        )
        _write_overlay(tmp_path, overlay)
        with pytest.raises(ProjectDRGValidationError) as exc_info:
            validate(tmp_path, shipped)
        assert "MISSING_SOURCE" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 3. Reject dangling target URN
# ---------------------------------------------------------------------------


class TestRejectDanglingTargetUrn:
    """Edge whose target does not exist → validation failure."""

    def test_dangling_target_raises_error(self, tmp_path: Path) -> None:
        shipped = _make_shipped_graph()
        overlay = _make_overlay(
            nodes=[("directive:PROJECT_001", NodeKind.DIRECTIVE)],
            edges=[("directive:PROJECT_001", "directive:DOES_NOT_EXIST", Relation.REQUIRES)],
        )
        _write_overlay(tmp_path, overlay)
        with pytest.raises(ProjectDRGValidationError) as exc_info:
            validate(tmp_path, shipped)
        err = exc_info.value
        assert any("DOES_NOT_EXIST" in e for e in err.errors)

    def test_error_is_structured_with_errors_field(self, tmp_path: Path) -> None:
        shipped = _make_shipped_graph()
        overlay = _make_overlay(
            nodes=[("directive:PROJECT_001", NodeKind.DIRECTIVE)],
            edges=[("directive:PROJECT_001", "tactic:NONEXISTENT", Relation.APPLIES)],
        )
        _write_overlay(tmp_path, overlay)
        with pytest.raises(ProjectDRGValidationError) as exc_info:
            validate(tmp_path, shipped)
        err = exc_info.value
        assert isinstance(err.errors, tuple)
        assert len(err.errors) >= 1
        assert isinstance(err.merged_graph_summary, str)
        assert len(err.merged_graph_summary) > 0


# ---------------------------------------------------------------------------
# 4. Reject duplicate edge
# ---------------------------------------------------------------------------


class TestRejectDuplicateEdge:
    """Same (source, target, relation) triple twice → validation failure."""

    def test_duplicate_edge_in_overlay_raises_error(self, tmp_path: Path) -> None:
        shipped = _make_shipped_graph(nodes=[("directive:DIRECTIVE_003", NodeKind.DIRECTIVE)])
        overlay = _make_overlay(
            nodes=[("directive:PROJECT_001", NodeKind.DIRECTIVE)],
            edges=[
                ("directive:PROJECT_001", "directive:DIRECTIVE_003", Relation.REQUIRES),
                ("directive:PROJECT_001", "directive:DIRECTIVE_003", Relation.REQUIRES),  # dup
            ],
        )
        _write_overlay(tmp_path, overlay)
        with pytest.raises(ProjectDRGValidationError) as exc_info:
            validate(tmp_path, shipped)
        err = exc_info.value
        assert any("Duplicate" in e for e in err.errors)


# ---------------------------------------------------------------------------
# 5. Reject cycle in requires
# ---------------------------------------------------------------------------


class TestRejectCycleInRequires:
    """Cycle among requires edges → validation failure."""

    def test_cycle_in_project_nodes_raises_error(self, tmp_path: Path) -> None:
        shipped = _make_shipped_graph()
        overlay = _make_overlay(
            nodes=[
                ("directive:PROJECT_001", NodeKind.DIRECTIVE),
                ("directive:PROJECT_002", NodeKind.DIRECTIVE),
            ],
            edges=[
                ("directive:PROJECT_001", "directive:PROJECT_002", Relation.REQUIRES),
                ("directive:PROJECT_002", "directive:PROJECT_001", Relation.REQUIRES),
            ],
        )
        _write_overlay(tmp_path, overlay)
        with pytest.raises(ProjectDRGValidationError) as exc_info:
            validate(tmp_path, shipped)
        err = exc_info.value
        assert any("Cycle" in e or "cycle" in e for e in err.errors)


# ---------------------------------------------------------------------------
# 6. NFR-004: fail-closed within 5 seconds
# ---------------------------------------------------------------------------


class TestFailClosedTiming:
    """NFR-004: validation failure detected and raised within 5 seconds."""

    def test_dangling_ref_fails_within_5s(self, tmp_path: Path) -> None:
        shipped = _make_shipped_graph()
        overlay = _make_overlay(
            nodes=[("directive:PROJECT_001", NodeKind.DIRECTIVE)],
            edges=[("directive:PROJECT_001", "directive:NONEXISTENT", Relation.REQUIRES)],
        )
        _write_overlay(tmp_path, overlay)

        start = time.monotonic()
        with pytest.raises(ProjectDRGValidationError):
            validate(tmp_path, shipped)
        elapsed = time.monotonic() - start

        assert elapsed < 5.0, f"validation_gate.validate took {elapsed:.2f}s — must be < 5s (NFR-004)"

    def test_valid_overlay_passes_within_5s(self, tmp_path: Path) -> None:
        shipped = _make_shipped_graph()
        overlay = _make_overlay()  # empty — trivially valid
        _write_overlay(tmp_path, overlay)

        start = time.monotonic()
        validate(tmp_path, shipped)  # no raise
        elapsed = time.monotonic() - start

        assert elapsed < 5.0, f"validation_gate.validate took {elapsed:.2f}s — must be < 5s (NFR-004)"


# ---------------------------------------------------------------------------
# 7. Missing / malformed overlay file
# ---------------------------------------------------------------------------


class TestMissingOrMalformedOverlay:
    """validate() raises ProjectDRGValidationError on missing/malformed overlay."""

    def test_missing_overlay_file_raises_error(self, tmp_path: Path) -> None:
        shipped = _make_shipped_graph()
        # No overlay file written
        with pytest.raises(ProjectDRGValidationError) as exc_info:
            validate(tmp_path, shipped)
        err = exc_info.value
        assert len(err.errors) >= 1
        assert "graph.yaml" in err.errors[0] or "doctrine" in err.errors[0] or "not found" in err.errors[0].lower()

    def test_malformed_yaml_raises_error(self, tmp_path: Path) -> None:
        doctrine_dir = tmp_path / "doctrine"
        doctrine_dir.mkdir()
        (doctrine_dir / "graph.yaml").write_text(": this: is: not: valid: yaml: [[[")
        shipped = _make_shipped_graph()
        with pytest.raises(ProjectDRGValidationError) as exc_info:
            validate(tmp_path, shipped)
        assert len(exc_info.value.errors) >= 1


# ---------------------------------------------------------------------------
# 8. Structured error carries enough info for CLI panel (US-5)
# ---------------------------------------------------------------------------


class TestStructuredErrorForCliPanel:
    """ProjectDRGValidationError carries offending URN + summary."""

    def test_error_fields_are_populated(self, tmp_path: Path) -> None:
        shipped = _make_shipped_graph()
        overlay = _make_overlay(
            nodes=[("directive:PROJECT_001", NodeKind.DIRECTIVE)],
            edges=[("directive:PROJECT_001", "directive:GHOST_URN", Relation.REQUIRES)],
        )
        _write_overlay(tmp_path, overlay)
        with pytest.raises(ProjectDRGValidationError) as exc_info:
            validate(tmp_path, shipped)
        err = exc_info.value

        # errors is a non-empty tuple of strings
        assert isinstance(err.errors, tuple)
        assert len(err.errors) >= 1
        assert all(isinstance(e, str) for e in err.errors)

        # merged_graph_summary is a non-empty string
        assert isinstance(err.merged_graph_summary, str)
        assert len(err.merged_graph_summary) > 0

        # Summary mentions project URNs for operator diagnosis
        assert "PROJECT_001" in err.merged_graph_summary or "project_nodes" in err.merged_graph_summary
