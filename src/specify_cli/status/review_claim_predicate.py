"""Pure role-aware review-claim collision predicate.

This is the single convergence point for the ``in_review`` re-claim collision
decision (``work_package_lifecycle.py`` in-lock re-claim). It is a pure leaf:
it imports nothing from ``wp_state`` / ``work_package_lifecycle`` and performs
no I/O, so it is trivially unit-testable row-by-row against the contract truth
table (``contracts/review-claim-predicate.md``).

Design contract (data-model.md):

* The ``for_review -> in_review`` FSM guard is **hard allow-only** and does NOT
  use this predicate — a stale reviewer role there must still ALLOW.
* Collision detection is **best-effort**: the reduced ``role`` slot is populated
  only when a claim carried a resolved binding. A binding-less holder has
  ``current_role=None`` and therefore degrades to ALLOW (rule 2). This matches
  the mission's primary goal: never false-block a cross-profile review.
* Role is read from the reduced ``role`` slot only, never by splitting the actor
  string (#2861).
"""

from __future__ import annotations

from dataclasses import dataclass

#: Resolved-binding role tokens that mark a holder as an active reviewer. The
#: token is the ``role`` written at the review-claim seam
#: (``workflow_executor._REVIEW_CLAIM_ROLE == "reviewer"``); a local frozenset
#: keeps this predicate a pure leaf with no import into the CLI command layer.
_REVIEWER_ROLES: frozenset[str] = frozenset({"reviewer"})


@dataclass(frozen=True)
class ReviewClaimDecision:
    """Outcome of :func:`review_claim_decision`.

    ``allowed=True`` is ALLOW; ``allowed=False`` is COLLISION and always names
    the current ``holder`` so the caller can build a
    ``WorkPackageClaimConflict`` message.
    """

    allowed: bool
    holder: str | None = None

    @property
    def is_collision(self) -> bool:
        return not self.allowed


_ALLOW = ReviewClaimDecision(allowed=True, holder=None)


def _is_reviewer_role(role: str | None) -> bool:
    return role is not None and role.strip() in _REVIEWER_ROLES


def review_claim_decision(
    current_actor: str | None,
    current_role: str | None,
    requesting_actor: str | None,
    requesting_role: str | None,
) -> ReviewClaimDecision:
    """Decide whether ``requesting_actor`` may re-claim an ``in_review`` WP.

    Rules (contracts/review-claim-predicate.md truth table):

    1. blank/``None`` ``current_actor`` -> ALLOW (never trust a blank identity as
       a positive collision signal).
    2. ``current_role`` is not a reviewer-role -> ALLOW (implementer/other holder;
       also covers the stale-role rework case).
    3. ``current_actor == requesting_actor`` -> ALLOW (idempotent same-actor
       re-claim).
    4. reviewer-role holder AND actors differ -> COLLISION naming the holder.
    """
    # ``requesting_role`` completes the symmetric claim-predicate contract
    # (data-model.md); the documented rules 1-4 key only off the holder's
    # identity/role, so the requester's role is intentionally not consulted.
    del requesting_role

    holder = current_actor.strip() if current_actor is not None else ""
    if not holder:
        return _ALLOW  # rule 1
    if not _is_reviewer_role(current_role):
        return _ALLOW  # rule 2
    requester = requesting_actor.strip() if requesting_actor is not None else ""
    if holder == requester:
        return _ALLOW  # rule 3
    return ReviewClaimDecision(allowed=False, holder=holder)  # rule 4
