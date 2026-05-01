"""FR-016 regression: :func:`doctrine.drg.validator.assert_valid` is invoked
on every live path that loads the DRG.

Ensures the Phase 0 merged-graph validator is not bypassed as the live
charter resolver / compiler evolves through Phase 1 cutovers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from charter._drg_helpers import load_validated_graph

pytestmark = pytest.mark.fast


def test_load_validated_graph_invokes_assert_valid(tmp_path: Path) -> None:
    """Loading the validated DRG via the shared helper must call
    :func:`assert_valid`."""
    shipped_root = tmp_path / "doctrine"
    shipped_root.mkdir()
    (shipped_root / "graph.yaml").write_text(
        "schema_version: '1.0'\n"
        "generated_at: '2026-04-14T00:00:00Z'\n"
        "generated_by: test\n"
        "nodes: []\n"
        "edges: []\n",
        encoding="utf-8",
    )

    with patch(
        "charter._drg_helpers.resolve_doctrine_root",
        return_value=shipped_root,
    ), patch("charter._drg_helpers.assert_valid") as mock_validator:
        load_validated_graph(tmp_path)
    assert mock_validator.called, "assert_valid() was not called"


def test_load_validated_graph_overlays_project_graph(tmp_path: Path) -> None:
    """When a project-overlay ``.kittify/doctrine/graph.yaml`` exists, the
    helper merges it onto the shipped graph before validating."""
    shipped_root = tmp_path / "doctrine"
    shipped_root.mkdir()
    (shipped_root / "graph.yaml").write_text(
        "schema_version: '1.0'\n"
        "generated_at: '2026-04-14T00:00:00Z'\n"
        "generated_by: test\n"
        "nodes:\n"
        "- {urn: 'directive:shipped-one', kind: directive}\n"
        "edges: []\n",
        encoding="utf-8",
    )

    project_graph_dir = tmp_path / ".kittify" / "doctrine"
    project_graph_dir.mkdir(parents=True)
    (project_graph_dir / "graph.yaml").write_text(
        "schema_version: '1.0'\n"
        "generated_at: '2026-04-14T00:00:00Z'\n"
        "generated_by: test\n"
        "nodes:\n"
        "- {urn: 'directive:project-one', kind: directive}\n"
        "edges: []\n",
        encoding="utf-8",
    )

    with patch(
        "charter._drg_helpers.resolve_doctrine_root",
        return_value=shipped_root,
    ):
        graph = load_validated_graph(tmp_path)

    urns = {n.urn for n in graph.nodes}
    assert "directive:shipped-one" in urns
    assert "directive:project-one" in urns


def test_load_validated_graph_rejects_invalid_merge(tmp_path: Path) -> None:
    """A corrupted (e.g. duplicate-edge) merged graph must raise via
    :func:`assert_valid`."""
    shipped_root = tmp_path / "doctrine"
    shipped_root.mkdir()
    # Dangling edge target -> should fail validation.
    (shipped_root / "graph.yaml").write_text(
        "schema_version: '1.0'\n"
        "generated_at: '2026-04-14T00:00:00Z'\n"
        "generated_by: test\n"
        "nodes:\n"
        "- {urn: 'directive:a', kind: directive}\n"
        "edges:\n"
        "- {source: 'directive:a', target: 'directive:missing', relation: requires}\n",
        encoding="utf-8",
    )
    with patch(
        "charter._drg_helpers.resolve_doctrine_root",
        return_value=shipped_root,
    ):
        with pytest.raises(Exception):  # noqa: B017, assert_valid may raise a variety
            load_validated_graph(tmp_path)


def test_shipped_graph_is_valid() -> None:
    """Shipped ``src/doctrine/graph.yaml`` passes :func:`assert_valid` today.

    This is the live-path backstop: if the shipped graph regresses into an
    invalid shape (dangling edges, duplicate edges, cycles in ``requires``),
    every downstream charter build will fail loudly instead of silently
    losing artifacts.
    """
    repo_root = Path(__file__).resolve().parents[2]
    from doctrine.drg.loader import load_graph, merge_layers
    from doctrine.drg.validator import assert_valid

    shipped_graph_path = repo_root / "src" / "doctrine" / "graph.yaml"
    assert shipped_graph_path.is_file(), f"missing shipped graph: {shipped_graph_path}"
    merged = merge_layers(load_graph(shipped_graph_path), None)
    assert_valid(merged)
