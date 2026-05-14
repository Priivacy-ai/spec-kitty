"""Side-effect-free claim discovery for ``spec-kitty next --json``.

Issue #988 — Prior to this module, ``spec-kitty next --json`` reported
``mission_state: implement`` while emitting ``wp_id: null``, even though the
explicit ``spec-kitty agent action implement`` would have auto-claimed a
concrete WP. Operators and AI agents driving the readiness loop could not
trust ``next --json`` as the canonical "what should I do next?" signal.

This module provides :func:`preview_claimable_wp`, a **read-only** mirror of
the candidate-selection algorithm used by ``agent action implement``
(specifically :func:`_find_first_planned_wp` in
``specify_cli.cli.commands.agent.workflow``). It walks WP files in the same
order, classifies their lane state from the canonical status event log, and
returns the WP that ``agent action implement`` would claim — together with a
stable ``selection_reason`` token when no claim is possible.

Design constraints (spec FR-001..FR-003, C-001):

* The helper never mutates state. It must not be confused with the actual
  claim path; only :func:`start_implementation_status` mutates the event log.
* When ``mission_state != "implement"`` the ``next --json`` payload's wire
  shape is preserved (no new keys are added).
* When ``wp_id`` is non-``None`` then ``selection_reason`` is ``None`` and
  vice versa (invariant I-001 from ``data-model.md``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from specify_cli.status.models import Lane
from specify_cli.status.reducer import reduce as _reduce_events
from specify_cli.status.store import read_events as _read_events

__all__ = ["ClaimablePreview", "preview_claimable_wp"]


@dataclass(frozen=True)
class ClaimablePreview:
    """Side-effect-free preview of which WP ``agent action implement`` would claim.

    Attributes:
        wp_id: The concrete WP that the explicit action would auto-claim, or
            ``None`` when no WP is selectable.
        selection_reason: A stable token explaining why selection is suppressed
            when ``wp_id`` is ``None``. Always ``None`` when ``wp_id`` is set.
            Tokens: ``"no_planned_wps"``, ``"all_wps_in_progress"``,
            ``"no_tasks_dir"``.
        candidates: Ordered tuple of WP IDs the claim algorithm would have
            considered (matches the order ``_find_first_planned_wp`` walks).
    """

    wp_id: str | None
    selection_reason: str | None
    candidates: tuple[str, ...]


_WP_FILENAME_RE = re.compile(r"(WP\d+)")


def preview_claimable_wp(feature_dir: Path) -> ClaimablePreview:
    """Return the WP that ``agent action implement`` would auto-claim, if any.

    Mirrors :func:`specify_cli.cli.commands.agent.workflow._find_first_planned_wp`
    exactly — same WP file ordering, same lane source (canonical event log),
    same definition of "claimable" (lane ``planned``).

    Args:
        feature_dir: Absolute path to ``kitty-specs/<mission_slug>/``.

    Returns:
        :class:`ClaimablePreview` whose ``wp_id`` matches what ``agent action
        implement`` would claim, or ``None`` with a structured
        ``selection_reason``.
    """
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return ClaimablePreview(
            wp_id=None,
            selection_reason="no_tasks_dir",
            candidates=(),
        )

    wp_files = sorted(tasks_dir.glob("WP*.md"))
    candidates: list[str] = []
    for wp_file in wp_files:
        wp_match = _WP_FILENAME_RE.match(wp_file.stem)
        if wp_match is None:
            continue
        candidates.append(wp_match.group(1))

    if not candidates:
        return ClaimablePreview(
            wp_id=None,
            selection_reason="no_planned_wps",
            candidates=(),
        )

    # Read lanes from the canonical status event log (lane is event-log-only).
    wp_lanes: dict[str, Lane] = {}
    try:
        events = _read_events(feature_dir)
        if events:
            snapshot = _reduce_events(events)
            for wp_id, state in snapshot.work_packages.items():
                wp_lanes[wp_id] = Lane(state.get("lane", Lane.PLANNED))
    except Exception:  # noqa: BLE001 — discovery is best-effort; on read failure default to PLANNED
        wp_lanes = {}

    for wp_id in candidates:
        lane = wp_lanes.get(wp_id, Lane.PLANNED)
        if lane == Lane.PLANNED:
            return ClaimablePreview(
                wp_id=wp_id,
                selection_reason=None,
                candidates=tuple(candidates),
            )

    # No planned candidates found. The `next` decision builder only reaches
    # this code path when at least one WP is in {planned, claimed, in_progress};
    # since we found no planned WP, every remaining candidate is either
    # claimed or in_progress.
    return ClaimablePreview(
        wp_id=None,
        selection_reason="all_wps_in_progress",
        candidates=tuple(candidates),
    )
