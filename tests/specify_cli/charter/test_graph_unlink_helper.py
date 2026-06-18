"""Unit tests for the shared graph-residue unlink helper (WP04 / FR-007).

``charter.synthesizer.graph_residue.unlink_stale_project_graph`` is the single
sanctioned removal of a project ``graph.yaml`` that a ``built_in_only`` writer
disowns. It consolidates the two former bare-``unlink`` sites
(``project_drg.apply_post_condition`` and ``_fresh_doctrine``). These tests pin
its behaviour: present-file removal, missing-file no-op, idempotency, and that
it touches ONLY ``graph.yaml`` (never sibling artifacts).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from charter.synthesizer.graph_residue import unlink_stale_project_graph
from charter.synthesizer.project_drg import _GRAPH_FILENAME

pytestmark = [pytest.mark.fast]


def test_removes_present_graph(tmp_path: Path) -> None:
    """A present ``graph.yaml`` is removed."""
    graph = tmp_path / _GRAPH_FILENAME
    graph.write_text("schema_version: '1.0'\nnodes: []\nedges: []\n", encoding="utf-8")
    assert graph.exists()

    unlink_stale_project_graph(tmp_path)

    assert not graph.exists()


def test_missing_graph_is_noop(tmp_path: Path) -> None:
    """A missing ``graph.yaml`` is a no-op (missing-safe), never raises."""
    assert not (tmp_path / _GRAPH_FILENAME).exists()

    unlink_stale_project_graph(tmp_path)  # must not raise

    assert not (tmp_path / _GRAPH_FILENAME).exists()


def test_idempotent_across_repeat_calls(tmp_path: Path) -> None:
    """Calling twice on a present-then-removed graph is idempotent."""
    graph = tmp_path / _GRAPH_FILENAME
    graph.write_text("nodes: []\n", encoding="utf-8")

    unlink_stale_project_graph(tmp_path)
    unlink_stale_project_graph(tmp_path)  # second call is a clean no-op

    assert not graph.exists()


def test_only_touches_graph_yaml(tmp_path: Path) -> None:
    """Sibling doctrine artifacts are untouched."""
    (tmp_path / _GRAPH_FILENAME).write_text("nodes: []\n", encoding="utf-8")
    sibling = tmp_path / "PROVENANCE.md"
    sibling.write_text("provenance\n", encoding="utf-8")

    unlink_stale_project_graph(tmp_path)

    assert not (tmp_path / _GRAPH_FILENAME).exists()
    assert sibling.exists()
    assert sibling.read_text(encoding="utf-8") == "provenance\n"


def test_reuses_canonical_graph_filename() -> None:
    """FR-007 anti-drift: the helper reuses ``project_drg._GRAPH_FILENAME``.

    Guards against a third copy of the ``graph.yaml`` literal being minted.
    """
    assert _GRAPH_FILENAME == "graph.yaml"
