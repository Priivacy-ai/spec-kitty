"""Activation identifier normalization at a single boundary (WP06, I-V4 / C-009).

The activation store holds a directive as ``025-boy-scout-rule`` while the
selector / DRG-node form is ``directive:DIRECTIVE_025``. WP06 reconciles the two
forms at **one** boundary (:func:`charter.activation.pack_context.normalize_activation_identifier`)
and partitions the activated-but-unreachable set into
``{not-a-node, node-but-unreachable}`` so that the ~25-artefact swing the
normalization produces is **declared and excluded** from any reachability-progress
claim (C-009 — normalizing the identifier form is *not* SC-005 progress).

Test strategy (WP06 prompt):

    PWHEADLESS=1 pytest tests/charter/test_activation_identifier_normalization.py \
        tests/charter/test_config_sourced_derivation.py -q
"""

from __future__ import annotations

import pytest

from charter.activation.pack_context import (
    normalize_activation_identifier,
    partition_activated_unreachable,
)

pytestmark = [pytest.mark.fast, pytest.mark.unit]


class TestNormalizeActivationIdentifier:
    """T031/T034 — store form and selector form resolve to the same node."""

    def test_directive_store_slug_resolves_to_selector_urn(self) -> None:
        """The store slug ``025-boy-scout-rule`` reconciles to the DRG node URN.

        This is the identifier that does **not** resolve today: the store keeps
        the file slug while the graph node is ``directive:DIRECTIVE_025``. After
        normalization the two forms name the same node.
        """
        assert (
            normalize_activation_identifier("directive", "025-boy-scout-rule")
            == "directive:DIRECTIVE_025"
        )

    def test_already_normalized_directive_is_idempotent(self) -> None:
        """A selector-form identifier passed back through the boundary is a fixed point."""
        assert (
            normalize_activation_identifier("directive", "DIRECTIVE_025")
            == "directive:DIRECTIVE_025"
        )

    def test_non_directive_kind_only_gains_its_kind_prefix(self) -> None:
        """For every non-directive kind, store id == node id (only the prefix is added).

        Probed against the shipped graph: tactics/toolguides/procedures/
        paradigms/styleguides need no id translation — only directives do.
        """
        assert (
            normalize_activation_identifier("tactic", "usage-examples-sync")
            == "tactic:usage-examples-sync"
        )
        assert (
            normalize_activation_identifier("styleguide", "deployable-skill-authoring")
            == "styleguide:deployable-skill-authoring"
        )

    def test_activation_store_key_forms_are_accepted(self) -> None:
        """The boundary accepts the singular kind, the plural, and the
        ``activated_<plural>`` config-key form — the store speaks all three."""
        for kind in ("directive", "directives", "activated_directives"):
            assert (
                normalize_activation_identifier(kind, "025-boy-scout-rule")
                == "directive:DIRECTIVE_025"
            )

    def test_unknown_kind_fails_naming_the_accepted_form(self) -> None:
        """An unrecognised kind fails loudly, naming the accepted kinds (C-006 —
        never silently infer identity from an undecidable kind)."""
        with pytest.raises(ValueError, match="directive"):
            normalize_activation_identifier("not-a-kind", "025-boy-scout-rule")


class TestPartitionActivatedUnreachable:
    """T033/T032 — {not-a-node, node-but-unreachable} + the excluded C-009 swing."""

    def test_directive_store_slug_lands_in_not_a_node(self) -> None:
        """An activated directive whose stored slug is not a node URN lands in
        ``not_a_node``; its normalized selector form is a real node, so it counts
        as a C-009 normalization swing — declared, never node-but-unreachable."""
        node_urns = frozenset({"directive:DIRECTIVE_025"})
        part = partition_activated_unreachable(
            activated={"directive": ["025-boy-scout-rule"]},
            node_urns=node_urns,
            reachable_urns=frozenset(),
        )
        assert part.not_a_node == frozenset({"directive:025-boy-scout-rule"})
        assert part.node_but_unreachable == frozenset()
        assert part.normalization_recovered == frozenset({"directive:DIRECTIVE_025"})
        assert part.normalization_delta == 1

    def test_real_node_that_is_unreachable_is_the_wiring_target(self) -> None:
        """A stored id that already IS a node but is not reached lands in
        ``node_but_unreachable`` — FR-015's real target, distinct from the swing."""
        node_urns = frozenset({"styleguide:deployable-skill-authoring"})
        part = partition_activated_unreachable(
            activated={"styleguide": ["deployable-skill-authoring"]},
            node_urns=node_urns,
            reachable_urns=frozenset(),
        )
        assert part.node_but_unreachable == frozenset(
            {"styleguide:deployable-skill-authoring"}
        )
        assert part.not_a_node == frozenset()
        assert part.normalization_delta == 0

    def test_reachable_identifier_is_in_neither_bucket(self) -> None:
        """A reachable activated id is delivered, so it is in neither partition."""
        urn = "tactic:usage-examples-sync"
        part = partition_activated_unreachable(
            activated={"tactic": ["usage-examples-sync"]},
            node_urns=frozenset({urn}),
            reachable_urns=frozenset({urn}),
        )
        assert part.not_a_node == frozenset()
        assert part.node_but_unreachable == frozenset()
        assert part.normalization_delta == 0

    def test_buckets_are_disjoint_and_swing_is_excluded(self) -> None:
        """The two buckets never overlap, and the C-009 swing is reported as its
        own count so a later pin can subtract it before claiming progress."""
        node_urns = frozenset(
            {
                "directive:DIRECTIVE_025",
                "directive:DIRECTIVE_030",
                "styleguide:deployable-skill-authoring",
                "tactic:usage-examples-sync",
            }
        )
        part = partition_activated_unreachable(
            activated={
                "directive": ["025-boy-scout-rule", "030-test-and-typecheck-quality-gate"],
                "styleguide": ["deployable-skill-authoring"],
                "tactic": ["usage-examples-sync", "id-that-names-nothing"],
            },
            node_urns=node_urns,
            reachable_urns=frozenset({"tactic:usage-examples-sync"}),
        )
        # Disjoint partition.
        assert not (part.not_a_node & part.node_but_unreachable)
        # Two directives are the swing; the stray tactic id is genuinely absent
        # (not a node in either form) so it is NOT counted as recovered.
        assert part.normalization_delta == 2
        assert part.normalization_recovered == frozenset(
            {"directive:DIRECTIVE_025", "directive:DIRECTIVE_030"}
        )
        assert "tactic:id-that-names-nothing" in part.not_a_node
        assert part.node_but_unreachable == frozenset(
            {"styleguide:deployable-skill-authoring"}
        )
        # The genuinely-absent stray is in not_a_node but NOT recovered by
        # normalization — so the swing count stays honest.
        assert "tactic:id-that-names-nothing" not in part.normalization_recovered
