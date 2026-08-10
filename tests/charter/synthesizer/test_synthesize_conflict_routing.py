"""WP02 — merged-overlay conflict routing (report, not crash).

Covers T007-T010 (`kitty-specs/charter-synthesize-reconciliation-01KZJQN6/
tasks/WP02-merged-overlay-conflict-routing.md`): ``validation_gate.validate``
receives WP01's classified ``ReconciliationConflict`` sequence in-memory
(widened signature, no ``.reconcile-conflicts.json`` sidecar) and makes the
suppress-vs-raise routing decision:

- ``provenance="preserved"`` (content that survived only because the
  reconciliation seam preserved it, not because the current run emitted it)
  is suppressed — already reported via ``ReconciliationDelta.conflicts`` —
  and must NOT raise (NFR-003: no silent-loss input may crash instead).
- ``provenance="new_emit"`` (the current run's own output colliding with
  itself or the built-in layer) remains a hard error, unchanged.

These tests call ``validation_gate.validate`` directly — the same pattern
``test_validation_gate.py`` already uses — rather than the full
``orchestrator.synthesize()`` entry point. This is a deliberate scope
boundary, not a shortcut: WP02 owns only ``validation_gate.py`` (routing),
not ``orchestrator.py`` (WP01's owned call site). Direct calls exercise
exactly the routing logic this WP delivers, with hand-built
``ReconciliationConflict`` objects standing in for WP01's classification —
matching the widened ``validate(staging_dir, built_in_drg, conflicts=...)``
contract precisely, independent of how any particular caller wires it.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from charter.synthesizer.errors import ProjectDRGValidationError
from charter.synthesizer.reconcile import _RECONCILE_REMEDIATIONS, ReconciliationConflict
from charter.synthesizer.validation_gate import validate
from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation

pytestmark = [pytest.mark.unit]


# ---------------------------------------------------------------------------
# Helpers (mirrors test_validation_gate.py's local graph-building pattern)
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


def _write_overlay(staging_dir: Path, graph: DRGGraph) -> None:
    """Write a DRGGraph YAML to staging_dir/doctrine/graph.yaml."""
    doctrine_dir = staging_dir / "doctrine"
    doctrine_dir.mkdir(parents=True, exist_ok=True)
    graph_path = doctrine_dir / "graph.yaml"

    nodes_data = [
        {"urn": n.urn, "kind": n.kind.value, **({"label": n.label} if n.label else {})} for n in graph.nodes
    ]
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


def _edge_key(source: str, relation: Relation, target: str) -> str:
    """Same label format ``validation_gate._edge_conflict_key`` builds."""
    return f"{source}--{relation.value}-->{target}"


# ---------------------------------------------------------------------------
# Case 1 — preserved duplicate-triple: reported, not raised
# ---------------------------------------------------------------------------


class TestPreservedDuplicateTripleIsReportedNotRaised:
    def test_preserved_duplicate_edge_does_not_raise(self, tmp_path: Path) -> None:
        shipped = _make_shipped_graph(nodes=[("directive:DIRECTIVE_003", NodeKind.DIRECTIVE)])
        overlay = _make_overlay(
            nodes=[("directive:PROJECT_001", NodeKind.DIRECTIVE)],
            edges=[
                ("directive:PROJECT_001", "directive:DIRECTIVE_003", Relation.REQUIRES),
                # A second, identical (source, target, relation) triple -- the
                # kind of leftover on-disk repeat reconciliation preserves.
                ("directive:PROJECT_001", "directive:DIRECTIVE_003", Relation.REQUIRES),
            ],
        )
        _write_overlay(tmp_path, overlay)

        conflict = ReconciliationConflict(
            kind="duplicate_triple",
            target_id=_edge_key("directive:PROJECT_001", Relation.REQUIRES, "directive:DIRECTIVE_003"),
            backing_artifact=None,
            remediation=_RECONCILE_REMEDIATIONS["duplicate_triple"],
            provenance="preserved",
        )
        assert conflict.remediation, "reported conflict class must carry a non-empty remediation"

        validate(tmp_path, shipped, conflicts=(conflict,))  # must not raise

    def test_same_duplicate_without_conflict_routing_still_raises(self, tmp_path: Path) -> None:
        """Control: without the conflict, the pre-WP02 hard-fail is unchanged."""
        shipped = _make_shipped_graph(nodes=[("directive:DIRECTIVE_003", NodeKind.DIRECTIVE)])
        overlay = _make_overlay(
            nodes=[("directive:PROJECT_001", NodeKind.DIRECTIVE)],
            edges=[
                ("directive:PROJECT_001", "directive:DIRECTIVE_003", Relation.REQUIRES),
                ("directive:PROJECT_001", "directive:DIRECTIVE_003", Relation.REQUIRES),
            ],
        )
        _write_overlay(tmp_path, overlay)

        with pytest.raises(ProjectDRGValidationError):
            validate(tmp_path, shipped)


# ---------------------------------------------------------------------------
# Case 2 — preserved dangling endpoint: reported, not raised
# ---------------------------------------------------------------------------


class TestPreservedDanglingEndpointIsReportedNotRaised:
    def test_preserved_dangling_target_does_not_raise(self, tmp_path: Path) -> None:
        shipped = _make_shipped_graph()
        overlay = _make_overlay(
            nodes=[("directive:PROJECT_001", NodeKind.DIRECTIVE)],
            edges=[
                # Target URN absent from both the current built-in snapshot
                # and the overlay's own nodes -- a preserved edge whose
                # endpoint the current run no longer emits.
                ("directive:PROJECT_001", "tactic:retired-legacy-tactic", Relation.APPLIES),
            ],
        )
        _write_overlay(tmp_path, overlay)

        conflict = ReconciliationConflict(
            kind="preserved_dangling_endpoint",
            target_id=_edge_key("directive:PROJECT_001", Relation.APPLIES, "tactic:retired-legacy-tactic"),
            backing_artifact=".kittify/doctrine/tactic/retired-legacy-tactic.tactic.yaml",
            remediation=_RECONCILE_REMEDIATIONS["preserved_dangling_endpoint"],
            provenance="preserved",
        )
        assert conflict.remediation, "reported conflict class must carry a non-empty remediation"

        validate(tmp_path, shipped, conflicts=(conflict,))  # must not raise; graph not silently truncated

    def test_same_dangling_edge_without_conflict_routing_still_raises(self, tmp_path: Path) -> None:
        """Control: without the conflict, the pre-WP02 hard-fail is unchanged."""
        shipped = _make_shipped_graph()
        overlay = _make_overlay(
            nodes=[("directive:PROJECT_001", NodeKind.DIRECTIVE)],
            edges=[("directive:PROJECT_001", "tactic:retired-legacy-tactic", Relation.APPLIES)],
        )
        _write_overlay(tmp_path, overlay)

        with pytest.raises(ProjectDRGValidationError):
            validate(tmp_path, shipped)


# ---------------------------------------------------------------------------
# Case 3 — new-emit collision still raises (regression guard)
# ---------------------------------------------------------------------------


class TestNewEmitCollisionStillRaises:
    def test_new_emit_duplicate_edge_still_raises(self, tmp_path: Path) -> None:
        """A ``new_emit`` conflict is left untouched -- the additive guard still bites."""
        shipped = _make_shipped_graph(nodes=[("directive:DIRECTIVE_003", NodeKind.DIRECTIVE)])
        overlay = _make_overlay(
            nodes=[("directive:PROJECT_001", NodeKind.DIRECTIVE)],
            edges=[
                ("directive:PROJECT_001", "directive:DIRECTIVE_003", Relation.REQUIRES),
                ("directive:PROJECT_001", "directive:DIRECTIVE_003", Relation.REQUIRES),
            ],
        )
        _write_overlay(tmp_path, overlay)

        conflict = ReconciliationConflict(
            kind="duplicate_triple",
            target_id=_edge_key("directive:PROJECT_001", Relation.REQUIRES, "directive:DIRECTIVE_003"),
            backing_artifact=None,
            remediation=_RECONCILE_REMEDIATIONS["duplicate_triple"],
            provenance="new_emit",
        )

        with pytest.raises(ProjectDRGValidationError) as exc_info:
            validate(tmp_path, shipped, conflicts=(conflict,))
        assert any("Duplicate" in e for e in exc_info.value.errors)

    def test_conflict_not_classified_preserved_still_raises(self, tmp_path: Path) -> None:
        """Belt-and-suspenders: only an explicit ``preserved`` provenance suppresses."""
        shipped = _make_shipped_graph()
        overlay = _make_overlay(
            nodes=[("directive:PROJECT_001", NodeKind.DIRECTIVE)],
            edges=[("directive:PROJECT_001", "directive:GHOST", Relation.REQUIRES)],
        )
        _write_overlay(tmp_path, overlay)

        conflict = ReconciliationConflict(
            kind="preserved_dangling_endpoint",
            target_id=_edge_key("directive:PROJECT_001", Relation.REQUIRES, "directive:GHOST"),
            backing_artifact=None,
            remediation=_RECONCILE_REMEDIATIONS["preserved_dangling_endpoint"],
            provenance="new_emit",
        )

        with pytest.raises(ProjectDRGValidationError):
            validate(tmp_path, shipped, conflicts=(conflict,))


# ---------------------------------------------------------------------------
# Unrelated errors (e.g. cycles) still raise even with suppressed conflicts
# ---------------------------------------------------------------------------


class TestUnrelatedErrorsStillRaiseAlongsideSuppressedConflicts:
    def test_cycle_error_survives_when_an_unrelated_conflict_is_suppressed(self, tmp_path: Path) -> None:
        shipped = _make_shipped_graph()
        overlay = _make_overlay(
            nodes=[
                ("directive:PROJECT_001", NodeKind.DIRECTIVE),
                ("directive:PROJECT_002", NodeKind.DIRECTIVE),
            ],
            edges=[
                ("directive:PROJECT_001", "directive:PROJECT_002", Relation.REQUIRES),
                ("directive:PROJECT_002", "directive:PROJECT_001", Relation.REQUIRES),
                # An unrelated preserved dangling edge that must be suppressed
                # without hiding the genuine cycle above.
                ("directive:PROJECT_001", "tactic:retired-legacy-tactic", Relation.APPLIES),
            ],
        )
        _write_overlay(tmp_path, overlay)

        conflict = ReconciliationConflict(
            kind="preserved_dangling_endpoint",
            target_id=_edge_key("directive:PROJECT_001", Relation.APPLIES, "tactic:retired-legacy-tactic"),
            backing_artifact=None,
            remediation=_RECONCILE_REMEDIATIONS["preserved_dangling_endpoint"],
            provenance="preserved",
        )

        with pytest.raises(ProjectDRGValidationError) as exc_info:
            validate(tmp_path, shipped, conflicts=(conflict,))
        assert any("Cycle" in e or "cycle" in e for e in exc_info.value.errors)
        assert not any("retired-legacy-tactic" in e for e in exc_info.value.errors), (
            "suppressed preserved-dangling conflict leaked into the surfaced errors"
        )
