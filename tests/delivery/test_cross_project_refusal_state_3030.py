"""FR-004's refusal must not destroy the consented project's events (#3030 H1).

``_cross_project_refusal`` is a safety net: it fires when the selection predicate
has already regressed and a batch spans two projects. Spec US1a AS-1 requires it
to refuse "before any POST, name the projects, and exit non-zero **without
mutating delivery state or bumping retry counts**".

Mapping the whole batch to ``TERMINAL_FAILED`` did the opposite. The dispatcher
routes that to ``record_terminal_failed`` -> ``STATUS_TERMINAL_FAILED``, and
``select_undelivered`` excludes terminal statuses *forever* — so a single refused
window permanently parked the **consented** project's events too. The net
destroyed more than the leak it was catching.

These tests pin the round-trip that the unit-level "no POST happened" assertion
in ``test_receivers.py`` could not see: after a refusal, the events are still
selectable, and they really do deliver on the next drain.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from specify_cli.delivery.dispatcher import dispatch
from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.receivers import TeamspaceReceiver
from specify_cli.delivery.targets import SqliteDeliveryTargetRegistry
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event

pytestmark = pytest.mark.fast

_CONSENTED = "aaaaaaaa-0000-0000-0000-00000000000a"
_OTHER = "bbbbbbbb-0000-0000-0000-00000000000b"
_SERVER_URL = "https://teamspace.example.com"
_TOKEN = "test-token"


@pytest.fixture(autouse=True)
def _consent_to_both_projects(tmp_path: Any, monkeypatch: Any) -> None:
    """Both projects consent, so selection hands the receiver a cross-project batch.

    This is the H1 failure scenario: consent is not what regressed — the selection
    *window* spanned two projects (e.g. after a backfill), and the pre-POST net
    fired on a batch whose events were all legitimately deliverable.
    """
    home = tmp_path / "consent-home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    from specify_cli.sync.consent import set_project_consent

    set_project_consent(_CONSENTED, True)
    set_project_consent(_OTHER, True)


def _event(event_id: str, project_uuid: str, index: int) -> Event:
    payload = json.dumps(
        {
            "event_id": event_id,
            "event_type": "mission.updated",
            "project_uuid": project_uuid,
        }
    ).encode("utf-8")
    return Event(
        event_id=event_id,
        event_type="mission.updated",
        payload=payload,
        occurred_at="2026-07-29T00:00:00+00:00",
        created_at=f"2026-07-29T00:00:0{index}+00:00",
        project_uuid=project_uuid,
    )


class _FakeResponse:
    def __init__(self, status_code: int, body: dict[str, Any]) -> None:
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body)

    def json(self) -> dict[str, Any]:
        return self._body


@pytest.fixture
def journal(tmp_path: Any) -> EventJournal:
    jrnl = EventJournal(tmp_path / "journal.db")
    jrnl.append(_event("evt-consented", _CONSENTED, 1))
    jrnl.append(_event("evt-other", _OTHER, 2))
    return jrnl


@pytest.fixture
def ledger() -> SqliteDeliveryLedger:
    return SqliteDeliveryLedger(":memory:")


@pytest.fixture
def target(tmp_path: Any) -> Any:
    registry = SqliteDeliveryTargetRegistry(":memory:")
    return registry.register(
        url=_SERVER_URL, team_slug="team", user_email="u@example.com"
    )


def test_refused_cross_project_batch_leaves_both_events_selectable(
    journal: EventJournal, ledger: SqliteDeliveryLedger, target: Any
) -> None:
    """The refusal must not park anything: state stays as if nothing was attempted."""
    posts: list[str] = []

    def _never(url: str, *, data: Any, headers: Any, timeout: Any) -> Any:
        posts.append(url)
        raise AssertionError("a cross-project batch must never be POSTed")

    receiver = TeamspaceReceiver(
        resolved_server_url=_SERVER_URL, auth_token=_TOKEN, poster=_never
    )

    summary = dispatch(
        journal=journal, ledger=ledger, receiver=receiver, target=target
    )

    assert posts == [], "no HTTP request may be made for a cross-project batch"
    assert summary.selected == 2
    assert summary.delivered == 0
    # The whole point of H1: nothing may be parked permanently.
    assert summary.terminal_failed == 0, (
        "a pre-POST refusal is not a permanent delivery failure; parking the batch "
        "destroys the consented project's events (spec US1a AS-1)"
    )
    still_selectable = ledger.select_undelivered(
        target_id=target.target_id,
        event_universe=["evt-consented", "evt-other"],
    )
    assert still_selectable == ["evt-consented", "evt-other"], (
        "both events must survive the refusal as selectable work"
    )
    # The refusal must still be observable and still name the projects.
    assert {f.event_id for f in summary.failures} == {"evt-consented", "evt-other"}
    assert all("more than one project" in (f.error or "") for f in summary.failures)
    assert any(_CONSENTED in (f.error or "") for f in summary.failures)


def test_consented_events_deliver_on_the_next_drain_after_a_refusal(
    journal: EventJournal, ledger: SqliteDeliveryLedger, target: Any
) -> None:
    """Round-trip proof: the refusal cost the consented project nothing.

    Drain 1 spans two projects and is refused. Drain 2 narrows the window (what a
    correct selection does) and the consented event delivers. With the refusal
    recorded as ``terminal_failed`` this second drain selected **nothing** — the
    event was gone from the selection set for good.
    """

    def _never(url: str, *, data: Any, headers: Any, timeout: Any) -> Any:
        raise AssertionError("a cross-project batch must never be POSTed")

    refused = TeamspaceReceiver(
        resolved_server_url=_SERVER_URL, auth_token=_TOKEN, poster=_never
    )
    dispatch(journal=journal, ledger=ledger, receiver=refused, target=target)

    delivered: list[bytes] = []

    def _ok(url: str, *, data: Any, headers: Any, timeout: Any) -> Any:
        delivered.append(data)
        return _FakeResponse(
            200, {"results": [{"event_id": "evt-consented", "status": "success"}]}
        )

    second = TeamspaceReceiver(
        resolved_server_url=_SERVER_URL, auth_token=_TOKEN, poster=_ok
    )
    summary = dispatch(
        journal=journal,
        ledger=ledger,
        receiver=second,
        target=target,
        exclude=frozenset({"evt-other"}),
    )

    assert summary.selected == 1, (
        "the consented event must still be selectable after the refusal"
    )
    assert summary.delivered == 1
    assert len(delivered) == 1


def test_a_refused_batch_does_not_wedge_the_multi_batch_drain(
    journal: EventJournal, ledger: SqliteDeliveryLedger, target: Any
) -> None:
    """Non-terminal must not mean "re-select the same refusal forever".

    Keeping the events selectable is only safe if the drain loop can still
    advance. ``sync now`` walks batches with an in-memory ``exclude`` set fed from
    ``retryable_event_ids``; this reproduces that loop and asserts it terminates.
    Without the events appearing in ``retryable_event_ids``, the identical
    cross-project window would be re-selected and re-refused on every iteration.
    """

    def _never(url: str, *, data: Any, headers: Any, timeout: Any) -> Any:
        raise AssertionError("a cross-project batch must never be POSTed")

    receiver = TeamspaceReceiver(
        resolved_server_url=_SERVER_URL, auth_token=_TOKEN, poster=_never
    )

    skip: set[str] = set()
    iterations = 0
    while iterations < 10:
        iterations += 1
        batch = dispatch(
            journal=journal,
            ledger=ledger,
            receiver=receiver,
            target=target,
            exclude=frozenset(skip),
        )
        before = len(skip)
        skip.update(batch.retryable_event_ids)
        progressed = (batch.delivered + batch.duplicate + batch.terminal_failed) > 0
        if batch.selected == 0 or not (progressed or len(skip) > before):
            break

    assert iterations <= 3, (
        f"the drain loop must advance past a refused batch, took {iterations} passes"
    )
    # And the events are still there for the next command.
    assert ledger.select_undelivered(
        target_id=target.target_id,
        event_universe=["evt-consented", "evt-other"],
    ) == ["evt-consented", "evt-other"]
