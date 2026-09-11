"""``org_chain_graph`` — the shared org-aware base for #4121 (squad MAJOR 2).

Activation-time projection (``plan_project_registration``) has always resolved
profile references against the built-in + org chain; the re-emission seams
(``emit_project_layer``, ``reconcile._classify_conflicts``,
``validation_gate.validate``) were built-in-only, so a project profile
referencing an org-pack artifact activated cleanly and then had its edge
silently dropped (or hard-failed validation) on the next synthesis. All of
those seams now take their base from this one helper, so they see exactly the
universe activation validated against.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from charter.activation._drg_helpers import org_chain_graph

pytestmark = pytest.mark.unit


def _write_org_pack(root: Path, *, node_id: str = "org-runbook", kind: str = "procedures") -> None:
    pack = root / "org-pack"
    (pack / "drg").mkdir(parents=True, exist_ok=True)
    (pack / "drg" / "fragment.yaml").write_text(
        dedent(
            f"""\
            pack_name: org-pack
            source_kind: local_path
            source_ref: {pack}
            layer_index: 1
            provenance_marker: org
            nodes:
              - id: {node_id}
                kind: {kind}
                title: "Org fixture {node_id}"
            edges: []
            """
        )
    )
    (root / ".kittify").mkdir(exist_ok=True)
    (root / ".kittify" / "config.yaml").write_text(
        dedent(
            f"""\
            charter_packs:
              org:
                packs:
                  - name: org-pack
                    local_path: {pack}
            """
        )
    )


def test_returns_none_without_org_config(tmp_path: Path) -> None:
    assert org_chain_graph(tmp_path) is None


def test_returns_none_with_no_packs_declared(tmp_path: Path) -> None:
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text("charter_packs:\n  org:\n    packs: []\n")
    assert org_chain_graph(tmp_path) is None


def test_includes_org_fragment_and_built_in_nodes(tmp_path: Path) -> None:
    _write_org_pack(tmp_path)
    graph = org_chain_graph(tmp_path)
    assert graph is not None
    assert graph.get_node("procedure:org-runbook") is not None
    # the base folds the shipped built-in layer, not just the org pack
    from charter.offering.drg.loader import load_built_in_graph

    assert any(graph.get_node(node.urn) is not None for node in load_built_in_graph().nodes)


def test_excludes_the_committed_project_overlay(tmp_path: Path) -> None:
    """The base is everything BELOW the project layer — a committed project
    node must not leak in (the registration/re-emission lanes re-derive
    project content themselves)."""
    _write_org_pack(tmp_path)
    doctrine = tmp_path / ".kittify" / "doctrine"
    doctrine.mkdir(parents=True)
    (doctrine / "graph.yaml").write_text(
        dedent(
            """\
            schema_version: '1.0'
            generated_at: '2026-09-10T00:00:00+00:00'
            generated_by: test
            nodes:
              - urn: agent_profile:committed-project-profile
                kind: agent_profile
            edges: []
            """
        )
    )
    graph = org_chain_graph(tmp_path)
    assert graph is not None
    assert graph.get_node("agent_profile:committed-project-profile") is None
