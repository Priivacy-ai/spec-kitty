"""ATDD tests for WP08: _node_is_activated per-artifact-ID gate and
filter_graph_by_activation per-artifact-ID filtering.

Covers:
- TestNodeIsActivatedPerArtifactIdGate: 6 tests validating the new Step 3
  per-artifact-ID gate added in WP08 (FR-038).
- TestFilterGraphByActivationPerArtifactId: 2 graph-construction tests
  validating that filter_graph_by_activation respects activated_directives.

WP01 (mission ``drg-relation-parity-activation-gate-01KY48PD``, #2843) fixed
the canonical-URN correctness bug and, as part of that fix, hoisted stem->
canonical resolution out of ``_node_is_activated`` into
``_resolve_activated_urns_by_kind`` (called once per
``filter_graph_by_activation`` call). Two consequences for this file:

1. ``_node_is_activated`` gained a required 4th parameter,
   ``resolved_urns_by_kind`` -- the pre-resolved
   ``dict[str, frozenset[str] | None]`` :func:`filter_graph_by_activation`
   builds once per call. ``TestNodeIsActivatedPerArtifactIdGate`` now
   supplies that map directly (as the real caller would have already
   resolved it) instead of relying on real filesystem stem resolution --
   this keeps the tests hermetic/synthetic, matching their original intent.
2. ``TestFilterGraphByActivationPerArtifactId`` drives the public
   ``filter_graph_by_activation`` (unchanged signature), which now performs
   *real* stem->canonical resolution against the built-in doctrine corpus.
   Synthetic ids that are not real config stems (``"dir-kept"``,
   ``"dir-blocked"``) no longer resolve and are correctly excluded
   (skip-with-report, per ``contracts/activation-gate-contract.md``) --
   this is the intended behavioral correction (research.md D1: "any
   existing test asserting the current (buggy) output is a stale assertion
   to update, not preserve"), so the affected tests below now use the real
   ``001-architectural-integrity-standard`` / ``DIRECTIVE_001`` stem<->
   canonical pair instead of synthetic ids.
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
    """6 tests for the Step 3 per-artifact-ID gate in _node_is_activated.

    Post-WP01, ``_node_is_activated`` takes a required 4th argument,
    ``resolved_urns_by_kind`` -- the pre-resolved canonical-URN map
    :func:`filter_graph_by_activation` builds once per call. These tests
    supply that map directly rather than a raw ``PackContext`` per-kind
    field, since the function itself no longer performs resolution (it is a
    pure membership check).
    """

    def test_non_listed_id_filtered(self):
        """An artifact whose ID is not in the activated set is blocked."""
        assert not _node_is_activated(
            "directive", "dir-blocked",
            _pc(),
            {"directive": frozenset({"directive:dir-ok"})},
        )

    def test_listed_id_passes(self):
        """An artifact whose ID is in the activated set passes."""
        assert _node_is_activated(
            "directive", "dir-ok",
            _pc(),
            {"directive": frozenset({"directive:dir-ok"})},
        )

    def test_none_passes_all(self):
        """Resolved set ``None`` for this kind (key absent from config) → all IDs pass."""
        assert _node_is_activated(
            "directive", "any-id",
            _pc(),
            {"directive": None},
        )

    def test_empty_frozenset_blocks_all(self):
        """An explicit empty resolved set (key present, nothing activated) → no IDs pass."""
        assert not _node_is_activated(
            "directive", "dir-any",
            _pc(),
            {"directive": frozenset()},
        )

    def test_empty_artifact_id_bypasses(self):
        """Malformed URN with empty ID → default-allow (bypass per-artifact gate)."""
        assert _node_is_activated(
            "directive", "",
            _pc(),
            {"directive": frozenset({"directive:dir-only"})},
        )

    def test_unknown_kind_not_gated(self):
        """An unknown kind (not in _SINGULAR_TO_PLURAL) passes unconditionally."""
        assert _node_is_activated("unknown_kind", "some-id", _pc(), {})

    def test_template_kind_not_gated(self):
        """WP06: the mission-tier ``template`` ArtifactKind is not in
        ``_SINGULAR_TO_PLURAL`` (it has no charter activation set) — it must
        pass through the kind-level gate unconditionally, same as any other
        unregistered kind, rather than raising KeyError."""
        assert _node_is_activated("template", "some-template-id", _pc(), {})

    def test_asset_kind_not_gated(self):
        """WP06: the loose-contract ``asset`` ArtifactKind is likewise absent
        from ``_SINGULAR_TO_PLURAL`` — must pass unconditionally, not raise."""
        assert _node_is_activated("asset", "some-asset-id", _pc(), {})

    def test_anti_pattern_kind_is_config_gated_not_default_allow(self) -> None:
        """WP04 (FR-004): unlike template/asset, ``anti_pattern`` IS wired into
        ``_SINGULAR_TO_PLURAL`` — it must be gated by ``activated_kinds`` like
        every other kind, not fall through the unknown-kind default-allow
        branch. The default ``_pc()`` fixture's ``activated_kinds`` does not
        list ``anti_patterns``, so an anti_pattern artifact must be blocked."""
        assert not _node_is_activated("anti_pattern", "force-push-shared-branch", _pc(), {})

    def test_anti_pattern_kind_passes_when_activated_kinds_includes_it(self) -> None:
        """The counterpart to the previous test: once ``anti_patterns`` is
        added to ``activated_kinds``, the kind-level gate passes (per-artifact
        gating below is still governed by ``activated_anti_patterns``)."""
        ctx = _pc(
            activated_kinds=frozenset({
                "directives", "tactics", "styleguides", "toolguides",
                "paradigms", "procedures", "agent_profiles",
                "mission_step_contracts", "anti_patterns",
            }),
        )
        assert _node_is_activated("anti_pattern", "force-push-shared-branch", ctx, {})

    def test_anti_pattern_per_artifact_id_gate(self) -> None:
        """FR-004: ``activated_anti_patterns`` gates individual anti_pattern
        IDs exactly like ``activated_directives`` gates directive IDs.

        Unlike file-backed kinds, ``anti_pattern`` has no config-stem <->
        canonical-id duality (WP01: :data:`_NO_STEM_RESOLUTION_KINDS` in
        ``charter/drg.py`` -- there is no dedicated artifact file), so its
        resolved map already holds direct/canonical ids, unwrapped.
        """
        ctx = _pc(
            activated_kinds=frozenset({
                "directives", "tactics", "styleguides", "toolguides",
                "paradigms", "procedures", "agent_profiles",
                "mission_step_contracts", "anti_patterns",
            }),
        )
        resolved = {"anti_pattern": frozenset({"anti_pattern:ok-smell"})}
        assert _node_is_activated("anti_pattern", "ok-smell", ctx, resolved)
        assert not _node_is_activated("anti_pattern", "blocked-smell", ctx, resolved)


# ---------------------------------------------------------------------------
# TestFilterGraphByActivationPerArtifactId
# ---------------------------------------------------------------------------


class TestFilterGraphByActivationPerArtifactId:
    """2 tests for filter_graph_by_activation per-artifact-ID filtering."""

    def test_directive_not_in_activated_directives_is_removed(self):
        """A directive node whose ID is absent from activated_directives is removed.

        WP01 (mission ``drg-relation-parity-activation-gate-01KY48PD``)
        made ``filter_graph_by_activation`` resolve real config stems
        against the built-in doctrine corpus, so this uses the real
        ``001-architectural-integrity-standard`` / ``003-decision-
        documentation-requirement`` stem<->canonical pairs rather than
        synthetic ids (which no longer resolve -- see module docstring).
        """
        blocked = DRGNode(urn="directive:DIRECTIVE_003", kind=NodeKind.DIRECTIVE, label="Blocked")
        kept = DRGNode(urn="directive:DIRECTIVE_001", kind=NodeKind.DIRECTIVE, label="Kept")
        g = _graph([blocked, kept])

        ctx = _pc(activated_directives=frozenset({"001-architectural-integrity-standard"}))
        filtered = filter_graph_by_activation(g, ctx)

        surviving_urns = {n.urn for n in filtered.nodes}
        assert "directive:DIRECTIVE_001" in surviving_urns
        assert "directive:DIRECTIVE_003" not in surviving_urns

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

    def test_template_and_asset_nodes_survive_filtering(self):
        """WP06: template/asset nodes are not gated by ``activated_kinds`` (the
        kind is absent from ``_SINGULAR_TO_PLURAL``) — they must survive
        ``filter_graph_by_activation`` unconditionally, not be silently
        dropped or raise."""
        template_node = DRGNode(
            urn="template:my-mission/onboarding", kind=NodeKind.TEMPLATE, label="Onboarding"
        )
        asset_node = DRGNode(urn="asset:widget-icon", kind=NodeKind.ASSET, label="Widget icon")
        g = _graph([template_node, asset_node])

        ctx = _pc()
        filtered = filter_graph_by_activation(g, ctx)

        surviving_urns = {n.urn for n in filtered.nodes}
        assert "template:my-mission/onboarding" in surviving_urns
        assert "asset:widget-icon" in surviving_urns

    def test_anti_pattern_node_is_dropped_when_kind_not_activated(self) -> None:
        """WP04 (FR-004): unlike template/asset (unknown kinds, default-allow),
        ``anti_pattern`` is config-gated — with the default ``_pc()`` fixture
        (no ``anti_patterns`` in ``activated_kinds``) the node must be
        filtered out, not silently pass through."""
        smell = DRGNode(
            urn="anti_pattern:force-push-shared-branch",
            kind=NodeKind.ANTI_PATTERN,
            label="Force-push a shared branch",
        )
        g = _graph([smell])

        filtered = filter_graph_by_activation(g, _pc())

        assert filtered.nodes == []

    def test_anti_pattern_node_survives_when_kind_and_id_activated(self) -> None:
        """The positive counterpart: with ``anti_patterns`` activated and the
        artifact's ID listed in ``activated_anti_patterns``, the node
        survives filtering."""
        smell = DRGNode(
            urn="anti_pattern:force-push-shared-branch",
            kind=NodeKind.ANTI_PATTERN,
            label="Force-push a shared branch",
        )
        g = _graph([smell])

        ctx = _pc(
            activated_kinds=frozenset({
                "directives", "tactics", "styleguides", "toolguides",
                "paradigms", "procedures", "agent_profiles",
                "mission_step_contracts", "anti_patterns",
            }),
            activated_anti_patterns=frozenset({"force-push-shared-branch"}),
        )
        filtered = filter_graph_by_activation(g, ctx)

        surviving_urns = {n.urn for n in filtered.nodes}
        assert "anti_pattern:force-push-shared-branch" in surviving_urns
