"""§4.5.1 inequality predicate for action-surface calibration.

Implements the two-halves of the calibration inequality from R-005:

    1. ResolvedScope(s) ⊇ RequiredScope(s)          — no missing-context regressions
    2. ResolvedScope(s) is NOT a strict superset of  — no over-broad context
       RequiredScope(s) ∪ known_irrelevant

The predicate never raises; callers decide whether a violation is fatal.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InequalityResult:
    """Result of the §4.5.1 calibration inequality check.

    Attributes:
        holds: True if both halves of the inequality are satisfied.
        missing_urns: URNs present in required_scope but absent from
            resolved_scope (violates half 1 — missing context).
        over_broad_urns: URNs present in resolved_scope but absent from
            both required_scope and known_irrelevant (violates half 2 —
            over-broad context).  When known_irrelevant is empty this is
            simply the set-difference resolved_scope − required_scope.
    """

    holds: bool
    missing_urns: frozenset[str]
    over_broad_urns: frozenset[str]


def assert_inequality_holds(
    *,
    resolved_scope: frozenset[str],
    required_scope: frozenset[str],
    known_irrelevant: frozenset[str] = frozenset(),
) -> InequalityResult:
    """Evaluate the §4.5.1 calibration inequality.

    Args:
        resolved_scope: URNs actually surfaced to the step at runtime
            (output of the DRG resolver).
        required_scope: URNs the step needs to make its decision
            (determined by inspection during calibration).
        known_irrelevant: URNs explicitly classified as irrelevant for
            this step.  When present, the over-broad check is narrowed to
            URNs *not* in this allowlist.

    Returns:
        An :class:`InequalityResult` describing whether both halves hold
        and, if not, which URNs are responsible.

    Notes:
        - Half 1: resolved_scope ⊇ required_scope
          → missing_urns = required_scope − resolved_scope
        - Half 2: resolved_scope is NOT a strict superset of
                  required_scope ∪ known_irrelevant
          → over_broad_urns = resolved_scope − (required_scope | known_irrelevant)
          → Half 2 passes when over_broad_urns is empty (resolved_scope ⊆
            required_scope ∪ known_irrelevant, i.e. every URN is either
            required or known to be irrelevant / tolerated).
    """
    # Half 1 — coverage check
    missing_urns = required_scope - resolved_scope

    # Half 2 — over-broad check
    # URNs that are neither required nor explicitly tolerated as irrelevant
    permitted = required_scope | known_irrelevant
    over_broad_urns = resolved_scope - permitted

    holds = len(missing_urns) == 0 and len(over_broad_urns) == 0

    return InequalityResult(
        holds=holds,
        missing_urns=frozenset(missing_urns),
        over_broad_urns=frozenset(over_broad_urns),
    )
