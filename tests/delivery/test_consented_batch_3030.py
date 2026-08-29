"""The delivery input cannot be built without a consent decision (#3030 FR-028).

The egress inventory's structural headline: two independent universes feed the
same HTTP sink, ``DeliveryReceiver`` is the object they share, and consent lived
one layer *above* it in a selection function only one of the two callers used.
The type moves the answer into the sink's own input.

A type only does that if it is genuinely unconstructable without an answer. If a
caller can build a :class:`ConsentedBatch` from an arbitrary list, the annotation
is documentation and the next ungated sender ships exactly as ``import-history``
did. These tests are the proof, and they probe the constructions a real caller
would actually reach for — the direct constructor, the constructor with a
plausible witness, ``dataclasses.replace`` on a legitimately-minted batch, and a
subclass that overrides the check — rather than only the easy one.

What is deliberately **not** claimed: immunity to ``object.__new__`` plus
``object.__setattr__``. Python has no private constructors; the bar is that a
sender cannot reach the wire by writing ordinary code.
"""

from __future__ import annotations

import dataclasses

import pytest

from specify_cli.delivery.consent_gate import (
    ConsentAnswer,
    ConsentedBatch,
    ConsentNotResolved,
    UnconsentedDelivery,
    consented_batch,
    resolve_consent_answer,
)
from specify_cli.delivery.receivers import OutboundEvent, StubReceiver

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

_PROJECT_A = "aaaaaaaa-0000-4000-8000-000000000001"
_PROJECT_B = "bbbbbbbb-0000-4000-8000-000000000002"
_ENGAGEMENT = "acme-holdings-carve-out"


def _event(event_id: str, project_uuid: str | None = _PROJECT_A) -> OutboundEvent:
    # canonical-event-exempt(exception-flow): legacy WPStatusChanged has no Payload model; OutboundEvent.payload is a raw Mapping
    payload: dict[str, object] = {
        "event_id": event_id,
        "event_type": "WPStatusChanged",
        "payload": {"mission_slug": _ENGAGEMENT},
    }
    if project_uuid is not None:
        payload["project_uuid"] = project_uuid
    return OutboundEvent(event_id=event_id, payload=payload)


def _answer(*granted: str) -> ConsentAnswer:
    return resolve_consent_answer(list(granted), consent_predicate=lambda c: frozenset(x for x in c if x))


# ── the answer cannot be fabricated ───────────────────────────────────────────


def test_a_consent_answer_cannot_be_constructed_directly() -> None:
    with pytest.raises(ConsentNotResolved):
        ConsentAnswer(granted=frozenset({_PROJECT_A}), asked=(_PROJECT_A,))


def test_a_consent_answer_cannot_be_constructed_with_a_guessed_witness() -> None:
    """The witness is compared by identity, so a plausible stand-in is not one."""
    for guess in (object(), "mint", True, None, ConsentAnswer):
        with pytest.raises(ConsentNotResolved):
            ConsentAnswer(granted=frozenset({_PROJECT_A}), asked=(_PROJECT_A,), _mint=guess)


def test_a_real_answer_cannot_be_widened_by_replace() -> None:
    """``dataclasses.replace`` is the hole a plain sentinel field would leave.

    ``replace`` copies field values, so a witness left live on the instance would
    be copied straight into a fabricated answer granting anything. The mint is
    burned in ``__post_init__`` precisely so this fails.
    """
    answer = _answer(_PROJECT_A)

    with pytest.raises(ConsentNotResolved):
        dataclasses.replace(answer, granted=frozenset({_PROJECT_A, _PROJECT_B}))


# ── the batch cannot be fabricated ────────────────────────────────────────────


def test_a_batch_cannot_be_constructed_from_a_bare_list() -> None:
    """The headline claim: no batch without a decision."""
    with pytest.raises(ConsentNotResolved):
        ConsentedBatch(
            events=(_event("e1"),),
            event_projects={"e1": _PROJECT_A},
            answer=_answer(_PROJECT_A),
        )


def test_a_real_batch_cannot_have_its_events_swapped_by_replace() -> None:
    """A cleared batch must not become a vehicle for a different project's events."""
    batch = consented_batch([_event("e1")], answer=_answer(_PROJECT_A))

    with pytest.raises(ConsentNotResolved):
        dataclasses.replace(batch, events=(_event("e2", _PROJECT_B),))


def test_the_batch_type_refuses_subclassing() -> None:
    """A subclass overriding ``__post_init__`` would defeat the receivers' isinstance."""
    with pytest.raises(TypeError, match="final"):

        class _Forged(ConsentedBatch):  # type: ignore[misc]
            def __post_init__(self) -> None:
                return None


# ── the mint refuses what the answer does not grant ───────────────────────────


def test_minting_refuses_a_project_the_answer_never_granted() -> None:
    with pytest.raises(UnconsentedDelivery) as excinfo:
        consented_batch([_event("e1", _PROJECT_B)], answer=_answer(_PROJECT_A))

    assert _PROJECT_B in str(excinfo.value), "the refusal must name the project it refused"


def test_minting_refuses_a_project_that_was_never_asked_about() -> None:
    """FR-028's exact shape: holding the uuid and never asking it.

    ``import-history`` had ``plan.identity.project_uuid`` in hand throughout and
    never put the question. An answer resolved over an empty candidate set grants
    nothing, so the batch that would have carried that project cannot be minted.
    """
    empty = resolve_consent_answer([], consent_predicate=lambda c: frozenset())

    with pytest.raises(UnconsentedDelivery):
        consented_batch([_event("e1", _PROJECT_A)], answer=empty)


def test_minting_refuses_an_event_with_unresolvable_identity() -> None:
    """NFR-001's second half: ``None ∉ delivered_project_uuids``."""
    with pytest.raises(UnconsentedDelivery) as excinfo:
        consented_batch([_event("e1", None)], answer=_answer(_PROJECT_A))

    assert "unresolvable identity" in str(excinfo.value)


# ── the receiver enforces it at runtime, not only in mypy ─────────────────────


def test_a_receiver_refuses_a_bare_sequence_at_runtime() -> None:
    """An annotation alone is advice; the incident already defeated review.

    ``StubReceiver`` is a real receiver in the production module (§4 rule 2), so
    what it accepts is what every receiver accepts.
    """
    stub = StubReceiver()

    with pytest.raises(ConsentNotResolved, match="ConsentedBatch"):
        stub.deliver([_event("e1")])  # type: ignore[arg-type]

    assert stub.received_events() == (), "nothing may be recorded from a refused call"


def test_a_receiver_delivers_a_minted_batch() -> None:
    """POSITIVE CONTROL: the same receiver does deliver when handed a real batch."""
    stub = StubReceiver()

    results = stub.deliver(consented_batch([_event("e1")], answer=_answer(_PROJECT_A)))

    assert [r.outcome.value for r in results] == ["success"]
    assert stub.received_event_ids() == ("e1",)
