"""Surface calibrator -- adjust action scope edges to satisfy governance inequalities.

The minimum-effective-dose model requires:
    |specify| < |plan| < |implement|
    |tasks|   < |implement|
    |review|  >= 0.80 * |implement|   (the "approximately" relation)

The calibrator only **adds** ``scope`` edges; it never removes them.
"""

from __future__ import annotations

from doctrine.drg.models import DRGEdge, DRGNode, Relation


def measure_surface(action_urn: str, edges: list[DRGEdge]) -> int:
    """Count distinct targets of ``scope`` edges originating from *action_urn*."""
    return len({e.target for e in edges if e.source == action_urn and e.relation == Relation.SCOPE})


def _scope_targets(action_urn: str, edges: list[DRGEdge]) -> set[str]:
    """Return the set of target URNs for scope edges from *action_urn*."""
    return {e.target for e in edges if e.source == action_urn and e.relation == Relation.SCOPE}


def calibrate_surfaces(
    nodes: list[DRGNode],
    edges: list[DRGEdge],
) -> list[DRGEdge]:
    """Return *edges* with calibration adjustments applied.

    Currently the only calibration rule is:

    * If ``|review| < 0.80 * |implement|``, copy missing ``scope`` edges from
      ``implement`` to ``review`` until the threshold is met.

    The function is additive-only -- it never removes edges.
    """
    # Discover the action URN prefix used (always "action:software-dev/...")
    implement_urn: str | None = None
    review_urn: str | None = None
    for node in nodes:
        if node.urn.endswith("/implement"):
            implement_urn = node.urn
        elif node.urn.endswith("/review"):
            review_urn = node.urn

    if implement_urn is None or review_urn is None:
        # No implement/review actions found -- nothing to calibrate.
        return list(edges)

    implement_targets = _scope_targets(implement_urn, edges)
    review_targets = _scope_targets(review_urn, edges)

    implement_size = len(implement_targets)
    if implement_size == 0:
        return list(edges)

    threshold = 0.80 * implement_size
    if len(review_targets) >= threshold:
        # Already within tolerance -- no calibration needed.
        return list(edges)

    # Edges present in implement but missing from review, sorted for
    # deterministic output.
    missing = sorted(implement_targets - review_targets)

    new_edges = list(edges)
    for target in missing:
        if len(review_targets) >= threshold:
            break
        new_edges.append(
            DRGEdge(
                source=review_urn,
                target=target,
                relation=Relation.SCOPE,
            )
        )
        review_targets.add(target)

    return new_edges
