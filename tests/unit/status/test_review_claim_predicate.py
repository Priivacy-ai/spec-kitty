"""Unit tests for the pure review-claim collision predicate (WP01 / T002).

One test per row of the contract truth table
(``contracts/review-claim-predicate.md``). The predicate is a pure leaf, so
these run without any filesystem/reduction setup.
"""

from __future__ import annotations

import pytest

from specify_cli.status.review_claim_predicate import (
    ReviewClaimDecision,
    review_claim_decision,
)

pytestmark = pytest.mark.unit


def test_cross_profile_holder_allows() -> None:
    """Row 1: an implementer holder + reviewer requester -> ALLOW."""
    decision = review_claim_decision(
        current_actor="implementer-ivan",
        current_role="implementer",
        requesting_actor="reviewer-renata",
        requesting_role="reviewer",
    )
    assert decision.allowed is True
    assert decision.is_collision is False
    assert decision.holder is None


def test_blank_current_actor_allows() -> None:
    """Row 2: a blank current_actor is never trusted as a collision -> ALLOW."""
    decision = review_claim_decision(
        current_actor="",
        current_role="",
        requesting_actor="reviewer-renata",
        requesting_role="reviewer",
    )
    assert decision.allowed is True
    assert decision.holder is None


def test_none_current_actor_allows() -> None:
    """Row 2 (None variant): a None current_actor -> ALLOW."""
    decision = review_claim_decision(
        current_actor=None,
        current_role=None,
        requesting_actor="reviewer-renata",
        requesting_role="reviewer",
    )
    assert decision.allowed is True


def test_same_reviewer_reclaim_is_idempotent_allow() -> None:
    """Row 3: the same reviewer re-claiming -> ALLOW (idempotent)."""
    decision = review_claim_decision(
        current_actor="reviewer-renata",
        current_role="reviewer",
        requesting_actor="reviewer-renata",
        requesting_role="reviewer",
    )
    assert decision.allowed is True
    assert decision.holder is None


def test_distinct_reviewer_collides_and_names_holder() -> None:
    """Row 4: two distinct reviewers -> COLLISION naming the holder."""
    decision = review_claim_decision(
        current_actor="reviewer-bob",
        current_role="reviewer",
        requesting_actor="reviewer-renata",
        requesting_role="reviewer",
    )
    assert decision.allowed is False
    assert decision.is_collision is True
    assert decision.holder == "reviewer-bob"


def test_non_reviewer_role_holder_allows() -> None:
    """Row 6: a non-reviewer (architect) holder -> ALLOW (rule 2)."""
    decision = review_claim_decision(
        current_actor="architect-alphonso",
        current_role="architect",
        requesting_actor="reviewer-renata",
        requesting_role="reviewer",
    )
    assert decision.allowed is True
    assert decision.holder is None


def test_binding_less_reviewer_holder_allows_best_effort() -> None:
    """Best-effort degradation: a reviewer holder with no reduced role
    (binding-less claim, ``current_role=None``) -> ALLOW (rule 2)."""
    decision = review_claim_decision(
        current_actor="reviewer-bob",
        current_role=None,
        requesting_actor="reviewer-renata",
        requesting_role="reviewer",
    )
    assert decision.allowed is True
    assert decision.holder is None


def test_requesting_role_does_not_affect_decision() -> None:
    """The requester's role is not consulted: rule 4 fires regardless of it."""
    for requesting_role in (None, "", "reviewer", "implementer"):
        decision = review_claim_decision(
            current_actor="reviewer-bob",
            current_role="reviewer",
            requesting_actor="reviewer-renata",
            requesting_role=requesting_role,
        )
        assert decision.allowed is False
        assert decision.holder == "reviewer-bob"


def test_decision_is_frozen_value_object() -> None:
    decision = ReviewClaimDecision(allowed=True)
    with pytest.raises(AttributeError):
        decision.allowed = False  # type: ignore[misc]
