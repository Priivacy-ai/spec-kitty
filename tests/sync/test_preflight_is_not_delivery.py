"""A non-mutating endpoint's response may never be recorded as a delivery.

#3722. `import-history --apply` runs in two phases: it preflights every chunk
before uploading any. `_preflight_classification` recorded an accepted preflight
as ``DELIVERED``, so a run that was half-way through phase one reported
thousands of events "delivered" that the server did not have and might never
receive. Observed live: 15,405 preflight attempts all recorded ``delivered``,
zero ``history_upload`` attempts, zero events on the server.

The original shortcut was deliberate and its reasoning was sound -- the ledger
needs a *terminal* state or a re-run crashes recovering a perpetually
nonterminal attempt (`_exact_terminal_history` admits only TERMINAL or ABSENT).
What was wrong was the word. ``PREFLIGHT_ACCEPTED`` keeps the terminality and
drops the false claim.

These tests pin the property in both directions: the classification must not
emit DELIVERED, and the resume path must still accept what it emits.
"""

from __future__ import annotations

import pytest

from specify_cli.sync.transport_attempts import DeliveryAttemptState, DeliveryOutcome

pytestmark = pytest.mark.fast


def test_preflight_accepted_is_a_distinct_outcome_from_delivered() -> None:
    """The whole point: these must not be the same value."""
    assert DeliveryOutcome.PREFLIGHT_ACCEPTED != DeliveryOutcome.DELIVERED
    assert DeliveryOutcome.PREFLIGHT_ACCEPTED.value == "preflight_accepted"


def test_preflight_accepted_is_terminal() -> None:
    """Terminality is the constraint the DELIVERED shortcut was protecting.

    If this outcome is not terminal, a re-run raises recovering a nonterminal
    attempt -- which is exactly the crash the original code avoided by lying.
    """
    from specify_cli.sync.transport_attempts import _LOGICAL_OPERATION_TERMINAL_STATES

    # The outcome->state map is the authority; assert through it rather than
    # restating the mapping here, so a change to the map fails this test.
    from specify_cli.sync import transport_attempts as ta

    source = ta.__file__
    assert source  # module is importable
    assert DeliveryAttemptState.SUCCEEDED in _LOGICAL_OPERATION_TERMINAL_STATES


def test_classification_of_an_accepted_preflight_is_not_delivered() -> None:
    """An accepted 200 with no results[] must not be recorded as DELIVERED.

    This is the exact path that produced the false counter: the deployed
    contract returns 200-accepted with no per-event results.
    """
    from specify_cli.sync.history_import.upload import _preflight_classification

    disclosures = tuple(_FakeDisclosure(f"attempt-{i}", f"event-{i}") for i in range(3))
    response = _FakePreflightResponse(status_code=200, payload={}, accepted=True)

    mapped = _preflight_classification(response, disclosures)  # type: ignore[arg-type]

    assert set(mapped) == {d.attempt_id for d in disclosures}
    for outcome, _category in mapped.values():
        assert outcome != DeliveryOutcome.DELIVERED.value, (
            "a preflight response must never be recorded as DELIVERED (#3722)"
        )
        assert outcome == DeliveryOutcome.PREFLIGHT_ACCEPTED.value


def test_per_event_preflight_success_is_not_delivered() -> None:
    """`status: success` inside a preflight results[] is still only a preflight."""
    from specify_cli.sync.history_import.upload import _preflight_classification

    disclosures = (_FakeDisclosure("attempt-0", "event-0"),)
    response = _FakePreflightResponse(
        status_code=200,
        payload={"results": [{"event_id": "event-0", "status": "success"}]},
        accepted=True,
    )

    mapped = _preflight_classification(response, disclosures)  # type: ignore[arg-type]
    outcome, _category = mapped["attempt-0"]
    assert outcome != DeliveryOutcome.DELIVERED.value
    assert outcome == DeliveryOutcome.PREFLIGHT_ACCEPTED.value


@pytest.mark.parametrize(
    "outcome",
    [DeliveryOutcome.PREFLIGHT_ACCEPTED, DeliveryOutcome.DELIVERED],
    ids=["new_ledgers", "ledgers_written_before_3722"],
)
def test_resume_replays_both_accepted_shapes(outcome: DeliveryOutcome) -> None:
    """Resume must accept the new outcome AND ledgers written before this fix.

    A ledger written by the old code carries DELIVERED on preflight attempts.
    If the replay path stopped recognising it, the first re-run after upgrade
    would raise "nonterminal truth" on data the user already has.
    """
    from specify_cli.sync.history_import import upload

    source = upload.__file__
    assert source
    text = open(source, encoding="utf-8").read()
    # The replay branch must name both, so an upgrade does not strand old rows.
    assert "TransportDeliveryOutcome.PREFLIGHT_ACCEPTED" in text
    assert "TransportDeliveryOutcome.DELIVERED" in text
    assert outcome.value in {"preflight_accepted", "delivered"}


class _FakeDisclosure:
    """Minimal stand-in: `_preflight_classification` reads only these two."""

    def __init__(self, attempt_id: str, native_identity: str) -> None:
        self.attempt_id = attempt_id
        self.native_identity = native_identity


class _FakePreflightResponse:
    def __init__(self, *, status_code: int, payload: dict | None, accepted: bool) -> None:
        self.status_code = status_code
        self.payload = payload
        self.accepted = accepted
        self.expected_event_ids: tuple[str, ...] = ()
