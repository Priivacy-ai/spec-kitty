"""P0 red-main pin for the #3031 capture-gate gap (Defect 3, ungated capture).

Companion to ``tests/sync/test_sync_consent_default_deny.py`` (#3031). That
file's own docstring names two gaps its five tests do NOT cover:

    Not covered here, and tracked in #3031 as separate work: capture is
    ungated (Defect 3 — events reach the journal regardless of consent) and
    drain selection filters per checkout rather than per event (Defect 5).
    Both need their own fixtures; neither is pinned by this file.

This file is additive — a NEW file, per the same-file docstring's own
instruction that these need their own fixtures. It does not edit
``test_sync_consent_default_deny.py``.

Defect 5 (per-event drain filtering) is already pinned by
``tests/delivery/test_dispatch_honours_drain_blocked_3030.py::test_dispatch_excludes_events_with_recorded_drain_blocked_reason``,
which drains one blocked and one unblocked event in a SINGLE ``dispatch()``
call (one process tick) and asserts differential treatment — a fix that
filters per-*process* rather than per-*event* cannot pass that test. No
duplicate is added here for Defect 5.

Defect 3 (ungated capture) is pinned below. ``capture_teamspace_bound``
(``event_journal/journal.py:370-403``) documents ``gate`` as deciding "only
... the recorded drain_blocked_reason (delivery eligibility), never whether
the write happens" for Teamspace-bound families — a deliberate, C-008-backed
invariant for events that ARE Teamspace-bound. But the same function's
``skip_journal`` parameter is the caller's signal that a particular capture
should NOT be written at all (its docstring: "A request to skip the write for
a Teamspace-bound family fails loudly"). Reading the implementation

    if is_teamspace_bound and skip_journal:
        raise TeamspaceBoundDropError(event_id=event_id)
    event = Event(...)
    journal.append(event)
    return event

shows ``skip_journal`` is honoured ONLY as a trigger for the loud-refusal
branch when ``is_teamspace_bound=True``. When ``is_teamspace_bound=False``
(the caller asserting "this fact is not Teamspace-bound, and I am asking you
not to persist it"), ``skip_journal=True`` is silently discarded — execution
falls straight through to the unconditional ``journal.append(event)``. There
is no code path in this function that ever actually skips the write; the gate
snapshot only ever affects the *recorded reason*, never the write itself,
exactly as the docstring for the Teamspace-bound branch says — except the
docstring implies that is a deliberate scope limit, and this test demonstrates
it is actually a total gap: the non-Teamspace-bound, explicit-skip-request
path silently does the opposite of what its caller asked.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.event_journal.journal import CaptureGateState, capture_teamspace_bound
from specify_cli.event_journal.models import Event

pytestmark = [pytest.mark.regression, pytest.mark.fast]

_OCCURRED_AT = "2026-06-29T00:00:00+00:00"

# A non-consenting gate snapshot: every gate closed, exactly the state a
# non-consenting checkout (#3031's incident shape) evaluates to.
_NON_CONSENTING_GATE = CaptureGateState(
    saas_enabled=False,
    checkout_enabled=False,
    authenticated=False,
    team_slug=None,
)


def test_non_consenting_capture_request_does_not_write_the_journal(tmp_path: Path) -> None:
    """A caller that asserts "not Teamspace-bound, please skip the write" must be honoured.

    Reds today: ``capture_teamspace_bound`` writes the event into the journal
    regardless of ``is_teamspace_bound=False, skip_journal=True`` — the write
    is unconditional in every code path through this function, not only the
    (correctly) unconditional Teamspace-bound one. A non-consenting checkout
    calling this with an accurate "do not persist this" signal still gets a
    durable, drainable journal row.
    """
    from specify_cli.event_journal.journal import EventJournal

    journal = EventJournal(tmp_path / "journal.db")
    event_id = "evt-client-confidential-0"

    result = capture_teamspace_bound(
        journal=journal,
        event_id=event_id,
        event_type="WorkPackageApproved",
        payload=b'{"event_id": "evt-client-confidential-0", "project_slug": "client-confidential"}',
        occurred_at=_OCCURRED_AT,
        gate=_NON_CONSENTING_GATE,
        is_teamspace_bound=False,
        skip_journal=True,
    )

    assert isinstance(result, Event)  # the function still returns a value; capture didn't raise
    stored = journal.read_by_id(event_id)
    assert stored is None, (
        "capture_teamspace_bound(is_teamspace_bound=False, skip_journal=True) "
        "must not write the event into the journal at all — the caller "
        "explicitly said this fact is not Teamspace-bound and should be "
        "skipped, but the function falls through to an unconditional "
        "journal.append(event) regardless of is_teamspace_bound/skip_journal "
        "(event_journal/journal.py:390-402); only the Teamspace-bound + "
        "skip_journal combination is gated (by raising), never honoured as "
        "an actual skip for either branch"
    )
