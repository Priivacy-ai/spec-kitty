"""ATDD tests for WP08: _node_is_activated per-artifact-ID gate and
filter_graph_by_activation per-artifact-ID filtering.

Covers:
- TestNodeIsActivatedPerArtifactIdGate: 6 tests validating the new Step 3
  per-artifact-ID gate added in WP08 (FR-038).
- TestFilterGraphByActivationPerArtifactId: 2 graph-construction tests
  validating that filter_graph_by_activation respects activated_directives.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from charter.drg import (
    DRGGraph,
    DRGNode,
    DRGEdge,
    NodeKind,
    filter_graph_by_activation,
    _node_is_activated,
)
from charter.pack_context import PackContext

pytestmark = [pytest.mark.unit]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _pc(**kw) -> PackContext:
    """Construct a hermetic PackContext for per-artifact-ID gate tests."""
    defaults: dict = {
        "activated_kinds": frozenset({
            "directives", "tactics", "styleguides", "toolguides",
            "paradigms", "procedures", "agent_profiles", "mission_step_contracts",
        }),
        "activated_mission_types": frozenset({"software-dev", "documentation"}),
        "pack_roots": (Path("."),),
        "org_pack_names": (),
        "repo_root": Path("."),
    }
    defaults.update(kw)
    return PackContext(**defaults)


def _graph(nodes: list[DRGNode], edges: list[DRGEdge] | None = None) -> DRGGraph:
    """Construct a hermetic DRGGraph using model_construct (skips validators)."""
    return DRGGraph.model_construct(
        schema_version="1.0",
        generated_at="2026-05-31T00:00:00Z",
        generated_by="test",
        nodes=nodes,
        edges=edges or [],
    )


# ---------------------------------------------------------------------------
# TestNodeIsActivatedPerArtifactIdGate
# ---------------------------------------------------------------------------


class TestNodeIsActivatedPerArtifactIdGate:
    """6 tests for the Step 3 per-artifact-ID gate in _node_is_activated."""

    def test_non_listed_id_filtered(self):
        """An artifact whose ID is not in the activated set is blocked."""
        assert not _node_is_activated(
            "directive", "dir-blocked",
            _pc(activated_directives=frozenset({"dir-ok"})),
        )

    def test_listed_id_passes(self):
        """An artifact whose ID is in the activated set passes."""
        assert _node_is_activated(
            "directive", "dir-ok",
            _pc(activated_directives=frozenset({"dir-ok"})),
        )

    def test_none_passes_all(self):
        """``activated_directives=None`` (key absent) → all IDs pass."""
        assert _node_is_activated(
            "directive", "any-id",
            _pc(activated_directives=None),
        )

    def test_empty_frozenset_blocks_all(self):
        """``activated_directives=frozenset()`` (explicit empty) → no IDs pass."""
        assert not _node_is_activated(
            "directive", "dir-any",
            _pc(activated_directives=frozenset()),
        )

    def test_empty_artifact_id_bypasses(self):
        """Malformed URN with empty ID → default-allow (bypass per-artifact gate)."""
        assert _node_is_activated(
            "directive", "",
            _pc(activated_directives=frozenset({"dir-only"})),
        )

    def test_unknown_kind_not_gated(self):
        """An unknown kind (not in _SINGULAR_TO_PLURAL) passes unconditionally."""
        assert _node_is_activated("unknown_kind", "some-id", _pc())


# ---------------------------------------------------------------------------
# TestFilterGraphByActivationPerArtifactId
# ---------------------------------------------------------------------------


class TestFilterGraphByActivationPerArtifactId:
    """2 tests for filter_graph_by_activation per-artifact-ID filtering."""

    def test_directive_not_in_activated_directives_is_removed(self):
        """A directive node whose ID is absent from activated_directives is removed."""
        blocked = DRGNode(urn="directive:dir-blocked", kind=NodeKind.DIRECTIVE, label="Blocked")
        kept = DRGNode(urn="directive:dir-kept", kind=NodeKind.DIRECTIVE, label="Kept")
        g = _graph([blocked, kept])

        ctx = _pc(activated_directives=frozenset({"dir-kept"}))
        filtered = filter_graph_by_activation(g, ctx)

        surviving_urns = {n.urn for n in filtered.nodes}
        assert "directive:dir-kept" in surviving_urns
        assert "directive:dir-blocked" not in surviving_urns

    def test_activated_directives_none_preserves_all_directive_nodes(self):
        """``activated_directives=None`` → all directive nodes survive."""
        node_a = DRGNode(urn="directive:dir-a", kind=NodeKind.DIRECTIVE, label="A")
        node_b = DRGNode(urn="directive:dir-b", kind=NodeKind.DIRECTIVE, label="B")
        g = _graph([node_a, node_b])

        ctx = _pc(activated_directives=None)
        filtered = filter_graph_by_activation(g, ctx)

        surviving_urns = {n.urn for n in filtered.nodes}
        assert "directive:dir-a" in surviving_urns
        assert "directive:dir-b" in surviving_urns
