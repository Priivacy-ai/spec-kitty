"""Canonical shared reader for the reduced-snapshot ``review`` slot.

Mission ``runtime-state-corpus-cutover`` — IC-04 / WP05 (D-14 campsite seam).

The merge gate (``merge/done_bookkeeping``) and the CLI review-context
resolution (``cli/commands/agent/workflow_cores``) both used to interpret
review-related *frontmatter* with **different** fallbacks, so the merge-gate
and the CLI could diverge on reviewer attribution. This module is the single
canonical interpretation of the snapshot ``review`` slot (a
:class:`ReviewOverride`), so both consumers read it through one seam.

The slot is populated as an off-axis ``InnerStateChanged`` delta
(``WPInnerStateDelta.review``) and stored by the reducer as a plain dict
(``ReviewOverride.to_dict()``); this reader reduces the event stream, looks up
the WP's snapshot, and reconstructs the typed view.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from specify_cli.status.models import EventStream, ReviewOverride
from specify_cli.status.reducer import reduce
from specify_cli.status.store import read_event_stream


def resolve_event_stream_review(
    event_stream: EventStream,
    wp_id: str,
) -> ReviewOverride | None:
    """Return the review override from an already-resolved event stream."""
    snapshot = reduce(
        event_stream.transitions,
        event_stream.annotations,
    ).work_packages.get(wp_id)
    if snapshot is None:
        return None
    review_raw = snapshot.get("review")
    if not isinstance(review_raw, Mapping):
        return None
    return ReviewOverride.from_dict(review_raw)


def resolve_snapshot_review(feature_dir: Path, wp_id: str) -> ReviewOverride | None:
    """Return the reduced-snapshot ``review`` override for *wp_id*, or ``None``.

    ``reduce`` → :func:`wp_snapshot_state` → ``.get("review")`` →
    :meth:`ReviewOverride.from_dict`. Returns ``None`` when the WP has no
    snapshot entry or carries no ``review`` slot — never raises for the
    absent case.
    """
    return resolve_event_stream_review(read_event_stream(feature_dir), wp_id)
