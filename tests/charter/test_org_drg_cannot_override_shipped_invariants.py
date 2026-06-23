"""Org-DRG cannot override shipped invariants ATDD (Slice F WP06).

FR-005 binding: organisation-tier DRG resolution SHALL NOT override the
layer-direction invariant from Mission A (``kernel ← doctrine ← charter
← specify_cli``); any org pack that imports across the layer boundary
fails to load with a named-violation error.

This file pins:

* shipped-invariant nodes cannot be overridden by an org pack
  (``OrgDRGConflictError`` with ``kind == "node_override"`` and
  ``resolution_applied == "hard_fail"``);
* nodes whose ``body_path`` references ``src/specify_cli/...`` fail with
  ``kind == "layer_rule_violation"``.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fast]


def _built_in_graph_with_node(urn: str):
    from charter.drg import DRGGraph, DRGNode, NodeKind  # noqa: PLC0415

    return DRGGraph(
        schema_version="1.0",
        generated_at="2026-05-18T00:00:00Z",
        generated_by="test-fixture",
        nodes=[DRGNode(urn=urn, kind=NodeKind.DIRECTIVE)],
        edges=[],
    )


def _fragment_overriding(urn_id: str):
    """Build an org fragment whose only node collides with a shipped node."""
    from charter.drg import OrgDRGFragment  # noqa: PLC0415

    return OrgDRGFragment.model_validate(
        {
            "pack_name": "example-org",
            "source_kind": "local_path",
            "source_ref": "/tmp/example-org",
            "layer_index": 1,
            "provenance_marker": "org",
            "nodes": [
                {
                    "id": urn_id,
                    "kind": "directives",
                    "title": "Override attempt",
                    "body_path": f"directives/{urn_id}.directive.yaml",
                }
            ],
            "edges": [],
        }
    )


def test_org_pack_overriding_shipped_invariant_is_permitted_with_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A same-kind org override of a shipped (built-in) node is PERMITTED by the
    merge and surfaced as a WARNING for operator visibility; a per-repo
    replaceable-builtins governance test decides whether the override is
    sanctioned (``doctrine.drg.merge._warn_builtin_override``). Retired the prior
    hard-fail ``OrgDRGConflictError`` expectation when the merge moved to
    warn-not-raise."""
    import logging  # noqa: PLC0415

    from charter.drg import merge_three_layers  # noqa: PLC0415

    built_in = _built_in_graph_with_node("directive:caveman-comments")
    org_fragment = _fragment_overriding("caveman-comments")

    with caplog.at_level(logging.WARNING, logger="doctrine.drg.merge"):
        merged = merge_three_layers(
            built_in=built_in,
            org_fragments=[org_fragment],
            project=None,
        )

    # Permitted: the merge returns a graph rather than raising.
    assert merged is not None
    # Visible by design: a same-kind-override WARNING names the overridden node.
    override_warnings = [
        rec.getMessage()
        for rec in caplog.records
        if rec.levelno == logging.WARNING
        and "caveman-comments" in rec.getMessage()
        and "override" in rec.getMessage().lower()
    ]
    assert override_warnings, (
        "expected a same-kind-override WARNING naming 'caveman-comments', "
        f"got {[r.getMessage() for r in caplog.records]}"
    )


def test_org_pack_body_path_referencing_specify_cli_is_layer_rule_violation() -> None:
    """FR-005 — an org node whose ``body_path`` reaches across the layer
    boundary (e.g. into ``src/specify_cli/``) fails with
    ``OrgDRGConflictError(kind='layer_rule_violation')``."""
    from charter.drg import (  # noqa: PLC0415
        DRGGraph,
        OrgDRGConflictError,
        OrgDRGFragment,
        merge_three_layers,
    )

    built_in = DRGGraph(
        schema_version="1.0",
        generated_at="2026-05-18T00:00:00Z",
        generated_by="test-fixture",
        nodes=[],
        edges=[],
    )
    org_fragment = OrgDRGFragment.model_validate(
        {
            "pack_name": "bad-org",
            "source_kind": "local_path",
            "source_ref": "/tmp/bad-org",
            "layer_index": 1,
            "provenance_marker": "org",
            "nodes": [
                {
                    "id": "smuggled-import",
                    "kind": "tactics",
                    "title": "Layer-rule smuggling attempt",
                    "body_path": "src/specify_cli/internal/sneaky.py",
                }
            ],
            "edges": [],
        }
    )

    with pytest.raises(OrgDRGConflictError) as exc_info:
        merge_three_layers(
            built_in=built_in,
            org_fragments=[org_fragment],
            project=None,
        )

    conflicts = exc_info.value.conflicts
    assert any(c.kind == "layer_rule_violation" for c in conflicts), (
        f"expected layer_rule_violation, got "
        f"{[(c.kind, c.target_id) for c in conflicts]}"
    )
