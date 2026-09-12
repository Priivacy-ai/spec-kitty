"""GREEN sentinel for the reducer ``review_result`` projection (WP10, NFR-004).

Pins commit ``407ea376c4`` — the last-wins-with-carry-forward projection at
``src/specify_cli/status/reducer.py:210-215``. This test is **green on base and
after** WP10; it is deliberately NOT a red-first test. Its job is to fail loudly
if a later change (or a misguided red-hunt) regresses the already-correct
projection. Per C-001, ``reducer.py`` MUST NOT be modified — this sentinel only
observes it.

Projection contract being pinned:

* **Override on verdict** — an event carrying a ``review_result`` lands that
  verdict verbatim into the slot (not merged, not carried-forward).
* **Override to ``None`` on forced in_review exit** — an outbound-from-
  ``in_review`` event with no ``review_result`` lands an explicit ``None``.
* **Sticky carry-forward otherwise** — any other transition preserves the
  previous slot value verbatim, so a verdict is never silently erased.
"""

from __future__ import annotations

import pytest

from specify_cli.status.models import Lane, ReviewResult, StatusEvent
from specify_cli.status.reducer import reduce

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_APPROVED = ReviewResult(
    reviewer="reviewer-rachel",
    verdict="approved",
    reference="approval://sentinel",
)


def _event(
    seq: int,
    from_lane: Lane,
    to_lane: Lane,
    *,
    review_result: ReviewResult | None = None,
) -> StatusEvent:
    return StatusEvent(
        event_id=f"01J{seq:023d}",
        mission_slug="sentinel-mission",
        wp_id="WP01",
        from_lane=from_lane,
        to_lane=to_lane,
        at=f"2026-08-18T22:{seq:02d}:00+00:00",
        actor="claude",
        force=False,
        execution_mode="worktree",
        review_result=review_result,
    )


def _slot(events: list[StatusEvent]) -> object:
    snapshot = reduce(events, [])
    return snapshot.work_packages["WP01"].get("review_result")


def test_verdict_event_overrides_slot() -> None:
    """A verdict-carrying event lands the verdict verbatim (override)."""
    events = [
        _event(1, Lane.PLANNED, Lane.CLAIMED),
        _event(2, Lane.CLAIMED, Lane.IN_PROGRESS),
        _event(3, Lane.IN_PROGRESS, Lane.FOR_REVIEW),
        _event(4, Lane.FOR_REVIEW, Lane.IN_REVIEW),
        _event(5, Lane.IN_REVIEW, Lane.APPROVED, review_result=_APPROVED),
    ]
    assert _slot(events) == _APPROVED.to_dict()


def test_carry_forward_is_sticky_after_verdict() -> None:
    """A later non-verdict transition preserves the verdict (carry-forward)."""
    events = [
        _event(4, Lane.FOR_REVIEW, Lane.IN_REVIEW),
        _event(5, Lane.IN_REVIEW, Lane.APPROVED, review_result=_APPROVED),
        _event(6, Lane.APPROVED, Lane.DONE),  # no verdict, not from in_review
    ]
    assert _slot(events) == _APPROVED.to_dict()


def test_forced_in_review_exit_without_verdict_lands_none() -> None:
    """An outbound-from-in_review event with no verdict overrides to None."""
    events = [
        _event(4, Lane.FOR_REVIEW, Lane.IN_REVIEW),
        _event(5, Lane.IN_REVIEW, Lane.APPROVED, review_result=_APPROVED),
        # Forced bounce back out of in_review carrying no ReviewResult.
        _event(6, Lane.IN_REVIEW, Lane.IN_PROGRESS),
    ]
    assert _slot(events) is None


def test_no_review_activity_leaves_slot_absent() -> None:
    """A WP that never enters review carries no ``review_result`` slot."""
    events = [
        _event(1, Lane.PLANNED, Lane.CLAIMED),
        _event(2, Lane.CLAIMED, Lane.IN_PROGRESS),
    ]
    snapshot = reduce(events, [])
    assert "review_result" not in snapshot.work_packages["WP01"]
