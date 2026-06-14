"""Lane alias resolution and the thin ``validate_transition`` delegator.

Single-ownership (WP01, DM-01KTH03G): the WPState objects in ``wp_state.py``
are the SOLE authority for the transition edge graph AND for the act of
transitioning (structural edge + guards + force-override). This module no longer
contains any edge table, guard logic, or force logic — ``validate_transition``
resolves aliases and delegates the entire decision to ``wp_state_for(from)``.

``ALLOWED_TRANSITIONS`` is retained ONLY as a non-authoritative derived
projection for tests and graph/visualisation tooling. It is computed from the
state objects' ``allowed_targets()`` and MUST NOT be consulted by production
code as an edge/transition gate (NFR-002, I1).
"""

from __future__ import annotations

from typing import Any

from specify_cli.status_lanes import CANONICAL_LANES as CANONICAL_LANES
from specify_cli.status_lanes import LANE_ALIASES, TERMINAL_LANES

from .models import GuardContext, Lane
from .wp_state import InvalidTransitionError, wp_state_for

__all__ = [
    "ALLOWED_TRANSITIONS",
    "CANONICAL_LANES",
    "LANE_ALIASES",
    "TERMINAL_LANES",
    "is_terminal",
    "resolve_lane_alias",
    "validate_transition",
]


def _derive_allowed_transitions() -> frozenset[tuple[str, str]]:
    """Derive the edge set from the FSM's per-state ``allowed_targets()``.

    NON-AUTHORITATIVE: this is a projection of the WPState edge graph, provided
    for tests and graph tooling only. Production edge-legality questions go
    through ``wp_state_for(from).may_transition_to(to)`` — never this set.
    """
    edges: set[tuple[str, str]] = set()
    for lane in Lane:
        state = wp_state_for(lane)
        for target in state.allowed_targets():
            edges.add((lane.value, target.value))
    return frozenset(edges)


# Non-authoritative derived projection (see module docstring / I1). Do NOT use
# this as a gate in production code; it exists for tests and graph tooling.
ALLOWED_TRANSITIONS: frozenset[tuple[str, str]] = _derive_allowed_transitions()


def resolve_lane_alias(lane: str) -> str:
    """Resolve alias to canonical lane name. Returns input if not an alias."""
    normalized = lane.strip().lower()
    resolved: str = LANE_ALIASES.get(normalized, normalized)
    return resolved


def is_terminal(lane: str) -> bool:
    """Check if a lane is terminal (done or canceled)."""
    return resolve_lane_alias(lane) in TERMINAL_LANES


def validate_transition(
    from_lane: str,
    to_lane: str,
    ctx: GuardContext | None = None,
) -> tuple[bool, str | None]:
    """Validate a lane transition. Returns ``(ok, error_message)``.

    Thin delegator: resolves aliases to canonical lanes, then hands the entire
    edge + guard + force transition primitive to the source state object
    (``wp_state_for(resolved_from).transition_to(resolved_to, ctx)``). No edge,
    guard, or force logic lives in this module (NFR-002, I1, I4).
    """
    ctx = ctx or GuardContext()
    resolved_from = resolve_lane_alias(from_lane)
    resolved_to = resolve_lane_alias(to_lane)

    try:
        from_lane_enum = Lane(resolved_from)
    except ValueError:
        return False, f"Unknown lane: {from_lane}"
    try:
        target_lane_enum = Lane(resolved_to)
    except ValueError:
        return False, f"Unknown lane: {to_lane}"

    try:
        wp_state_for(from_lane_enum).transition_to(target_lane_enum, ctx)
    except InvalidTransitionError as exc:
        # Guarantee a non-None reason: a guard override or a reasonless
        # InvalidTransitionError could otherwise propagate (False, None), breaking
        # callers that expect a message (#1775 review m4).
        return False, exc.reason or f"Illegal transition: {resolved_from} -> {resolved_to}"
    return True, None


def _run_guard(
    from_lane: str,
    to_lane: str,
    ctx: GuardContext | None = None,
    /,
    **legacy_kwargs: Any,
) -> tuple[bool, str | None]:
    """Run the source state's entry guard for a transition (guard-only).

    Thin delegator retained for guard-equivalence tests. Builds a
    ``GuardContext`` from legacy kwargs when needed, then asks the FSM. Force
    and edge legality are NOT evaluated here — only the entry guard for the
    structurally-allowed edge (mirrors the historical guard-only contract:
    transitions with no guard, or with no edge at all, return ``(True, None)``).
    """
    if ctx is not None and legacy_kwargs:
        raise TypeError("_run_guard accepts either a GuardContext or legacy keyword arguments, not both")
    if ctx is None:
        ctx = GuardContext(**legacy_kwargs)
    elif not isinstance(ctx, GuardContext):
        raise TypeError("_run_guard expects a GuardContext or legacy keyword arguments")

    resolved_from = resolve_lane_alias(from_lane)
    resolved_to = resolve_lane_alias(to_lane)
    state = wp_state_for(Lane(resolved_from))
    target = Lane(resolved_to)
    if not state.may_transition_to(target):
        # No edge: the historical guard map had no entry, so it returned (True, None).
        return True, None
    return state.guard_for(target, ctx)
