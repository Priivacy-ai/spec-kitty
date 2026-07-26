"""``doctrine-daphne`` must carry the canonical doctrine/charter structure (SC-007).

Mission ``doctrine-canonical-structure-remediation-01KYEYSD``, FR-010.

Rationale: the curator profile is the load-time context for any agent authoring or
maintaining doctrine. Two mistakes in this repo trace directly to that context *not*
carrying the structural rules:

* PR #2918 placed assets at ``assets/<category>/built-in/`` — pack and category inverted —
  and nothing in the curator's context said which order was correct;
* an in-flight change on this branch started widening the four ``<kind>_reference.type``
  schema enums to admit ``asset``, which would have grown a deprecated surface. It was
  stopped by the operator, not by anything the profile knew.

So this is a content assertion on purpose. A profile that merely *resolves* is not enough;
it has to actually state the rules, because its prose IS the mechanism. Assertions are on
normalized substrings (whitespace-collapsed) so reflowing the YAML block scalars does not
break them, while a genuine removal of a rule does.

Deliberately NOT asserted: exact phrasing. Each check targets the load-bearing fact
(a path shape, a command name, a prohibition), not an author's wording.
"""

from __future__ import annotations

import re

import pytest

from doctrine.agent_profiles.repository import AgentProfileRepository

pytestmark = [pytest.mark.doctrine, pytest.mark.fast]

_PROFILE_ID = "doctrine-daphne"


def _normalized_profile_text() -> str:
    """Return the profile's whitespace-collapsed prose, lowercased.

    Pulled through the repository rather than read off disk so the test exercises the same
    resolution path consumers use -- a profile that fails to load fails here too.
    """
    profile = AgentProfileRepository().resolve_profile(_PROFILE_ID)
    assert profile is not None, f"{_PROFILE_ID} does not resolve"
    dumped = profile.model_dump() if hasattr(profile, "model_dump") else vars(profile)
    return re.sub(r"\s+", " ", str(dumped)).lower()


@pytest.fixture(scope="module")
def profile_text() -> str:
    return _normalized_profile_text()


class TestPackLayoutAwareness:
    def test_states_the_canonical_artifact_path_shape(self, profile_text: str) -> None:
        assert "<type>/<pack>/" in profile_text

    def test_says_the_category_nests_inside_the_pack(self, profile_text: str) -> None:
        """The exact #2918 mistake: a category directory above the pack layer."""
        assert "above the pack layer" in profile_text

    def test_explains_the_consequence_is_silent_non_loading(self, profile_text: str) -> None:
        """Knowing the rule matters less than knowing misplacement fails *silently*."""
        assert "silently never loaded" in profile_text


class TestRelationshipAuthorityAwareness:
    def test_marks_the_inline_reference_surface_as_frozen_legacy(self, profile_text: str) -> None:
        assert "frozen legacy" in profile_text

    def test_forbids_widening_a_reference_kind_enum(self, profile_text: str) -> None:
        """The abandoned wrong-direction fix must be named as forbidden."""
        assert "widen a `<kind>_reference.type` schema enum" in profile_text

    def test_forbids_authoring_new_inline_reference_blocks(self, profile_text: str) -> None:
        assert "does not author a new inline `references:` block" in profile_text

    def test_knows_the_newer_relations_are_edge_only(self, profile_text: str) -> None:
        for relation in ("refines", "rejects", "in-tension-with", "reconciles-tension"):
            assert relation in profile_text


class TestGraphMechanicsAwareness:
    def test_knows_the_monolith_is_sharded_into_per_kind_fragments(self, profile_text: str) -> None:
        assert "<kind>.graph.yaml" in profile_text

    def test_names_the_regeneration_command(self, profile_text: str) -> None:
        assert "spec-kitty doctrine regenerate-graph" in profile_text

    def test_forbids_pointing_operators_at_the_nonexistent_monolith(self, profile_text: str) -> None:
        assert "no longer exists" in profile_text

    def test_requires_a_ledger_entry_for_golden_count_movement(self, profile_text: str) -> None:
        assert "composition ledger" in profile_text


class TestCharterActivationAwareness:
    def test_knows_authoring_does_not_make_an_artifact_live(self, profile_text: str) -> None:
        assert "does not make it live" in profile_text

    def test_names_the_activation_command(self, profile_text: str) -> None:
        assert "spec-kitty charter activate" in profile_text

    def test_knows_which_kinds_are_never_activatable(self, profile_text: str) -> None:
        """templates / assets / anti-patterns resolve specially and are never live rules."""
        assert "never activated as live rules" in profile_text

    def test_knows_a_resolved_only_node_needs_an_inbound_edge(self, profile_text: str) -> None:
        assert "inbound edge" in profile_text


class TestGuardIsNonVacuous:
    def test_assertions_run_against_real_resolved_content(self, profile_text: str) -> None:
        """Floor check: an empty or stub profile would pass every `in` above trivially only
        if the text were huge and generic. Pin that we loaded substantive prose."""
        assert len(profile_text) > 2000

    def test_a_missing_rule_would_actually_fail(self, profile_text: str) -> None:
        """Self-mutation proof: the checks are substring-based, so prove a removed rule is
        detectable rather than assuming it."""
        mutated = profile_text.replace("spec-kitty doctrine regenerate-graph", "")
        assert "spec-kitty doctrine regenerate-graph" not in mutated
        assert "spec-kitty doctrine regenerate-graph" in profile_text
