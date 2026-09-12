"""Shared status-lane constants without importing status orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

CANONICAL_LANES: tuple[str, ...] = (
    "planned",
    "claimed",
    "in_progress",
    "for_review",
    "in_review",
    "approved",
    "done",
    "blocked",
    "canceled",
)

LANE_ALIASES: dict[str, str] = {
    "doing": "in_progress",
    # NOTE: "in_review" is NO LONGER an alias — it is a first-class lane (FR-012a)
}

TERMINAL_LANES: frozenset[str] = frozenset({"done", "canceled"})

#: Lanes that are an acceptable mission ending *unconditionally* — approved and
#: done are always a valid ending regardless of provenance. ``canceled`` is a
#: TERMINAL lane (see :data:`TERMINAL_LANES`) but is deliberately NOT here:
#: acceptability, terminality, and provenance are three separable decisions
#: (post-spec squad F2). ``canceled`` is acceptable only with operator-authored
#: provenance, decided in :func:`is_acceptable_ending`.
_UNCONDITIONALLY_ACCEPTABLE_LANES: frozenset[str] = frozenset({"approved", "done"})

#: The ``reason_source`` discriminator value that marks a canceled event's
#: reason as operator-authored (as opposed to the CLI's auto-synthesized
#: default). Projected onto the reduced snapshot by
#: ``specify_cli.status.reducer`` (FR-001 / C-002).
OPERATOR_REASON_SOURCE = "operator"


def is_acceptable_ending(lane: str, *, has_provenance: bool) -> bool:
    """Return whether ``lane`` is an acceptable mission ending.

    The single acceptable-ending authority (FR-005), consumed by ``accept``,
    ``merge``, and the dependency-readiness gate. Terminality
    (``{done, canceled}``), acceptability (``{approved, done}``), and provenance
    are three separable decisions (post-spec squad F2): this predicate must NOT
    be confused with a terminal-lane check.

    Truth table (contract ``acceptable-ending-predicate.md``):

    * ``approved`` / ``done`` → ``True`` (``has_provenance`` ignored).
    * ``canceled`` → ``True`` iff ``has_provenance`` (operator-authored).
    * every other lane → ``False``.

    Pure: no I/O. Provenance is resolved by the caller from the reduced
    snapshot via :func:`has_operator_provenance` (C-002). References the
    canonical :data:`TERMINAL_LANES` set only to classify ``canceled``.
    """
    if lane in _UNCONDITIONALLY_ACCEPTABLE_LANES:
        return True
    # ``done`` already returned above, so the only remaining TERMINAL lane is
    # ``canceled`` — the sole lane whose acceptability turns on provenance.
    if lane in TERMINAL_LANES:
        return has_provenance
    return False


def has_operator_provenance(wp_snapshot: Mapping[str, Any] | None) -> bool:
    """Return whether a reduced WP snapshot carries operator-authored cancellation provenance.

    The single shared reader of WP01's ``reason_source`` snapshot slot (paula:
    avoid a 3-site ``reason_source == "operator"`` whack-a-field). ``accept``
    (WP02), ``merge`` (WP03), and the dependency gate (WP04) all read provenance
    through this one accessor rather than inlining the slot name.

    Returns ``False`` for a ``None`` snapshot, a snapshot with no
    ``reason_source`` key (a legacy snapshot, or any non-canceled WP — the slot
    is only ever projected onto a canceled snapshot, NFR-002), and a synthetic
    cancellation. Returns ``True`` only when ``reason_source`` is exactly
    ``operator``. Pure: no I/O.
    """
    if wp_snapshot is None:
        return False
    return wp_snapshot.get("reason_source") == OPERATOR_REASON_SOURCE
