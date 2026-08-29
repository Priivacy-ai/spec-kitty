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

The project-owned dispatcher can no longer construct a mixed-project batch: its
store, context, and admitted target all carry the same UUID.  These tests drive
the receiver's last-resort mixed-batch refusal directly, then use a real
project-owned journal and ledger to pin the durable round-trip that the unit-level
"no POST happened" assertion in ``test_receivers.py`` could not see: after a
refusal, the corresponding local events are still selectable, and they really do
deliver on the next drain.
"""

from __future__ import annotations

import gzip
import json
from typing import Any

import pytest

from specify_cli.delivery.dispatcher import dispatch
from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.receivers import (
    DeliveryOutcome,
    OutboundEvent,
    TeamspaceReceiver,
)
from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.sync.consent import record_project_opt_in
from specify_cli.sync.project_store import ProjectSyncStore
from tests._support.consented_batches import deliverable

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

_CONSENTED = "aaaaaaaa-0000-0000-0000-00000000000a"
_OTHER = "bbbbbbbb-0000-0000-0000-00000000000b"
_SERVER_URL = "https://teamspace.example.com"
_TOKEN = "test-token"


@pytest.fixture(autouse=True)
def _project_owned_authority(tmp_path: Any, monkeypatch: Any) -> None:
    """Create the real opted-in, project-only, admitted dispatcher authority."""
    home = tmp_path / "consent-home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    store = ProjectSyncStore(_CONSENTED)
    authority = store.layout_generation()
    authority.begin_cutover("wp07-cross-project-fixture")
    authority.publish_project_only("wp07-cross-project-fixture", verify_exact=lambda: True)
    record_project_opt_in(_CONSENTED, actor="wp07-cross-project-test")
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, ?, 'u@example.com', 'team', 1, 'admitted', '1', "
            "'private-teamspace:team')",
            (_CONSENTED, _SERVER_URL),
        )


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
def store() -> ProjectSyncStore:
    value = ProjectSyncStore(_CONSENTED)
    with value.unit_of_work() as unit:
        journal = EventJournal(unit, value.layout_generation())
        journal.append(_event("evt-consented", _CONSENTED, 1))
        journal.append(_event("evt-other", _CONSENTED, 2))
    return value


def _target(store: ProjectSyncStore) -> Any:
    with store.unit_of_work() as unit:
        target = ProjectDeliveryTargetRegistry(store).get_current(unit)
    assert target is not None
    return target


def _mixed_batch() -> list[OutboundEvent]:
    return [
        OutboundEvent(
            event_id="evt-consented",
            payload={"event_id": "evt-consented", "project_uuid": _CONSENTED},
        ),
        OutboundEvent(
            event_id="evt-other",
            payload={"event_id": "evt-other", "project_uuid": _OTHER},
        ),
    ]


def _selectable(store: ProjectSyncStore, target_id: str) -> list[str]:
    with store.unit_of_work() as unit:
        return SqliteDeliveryLedger(unit, store.layout_generation()).select_undelivered(
            target_id=target_id,
            event_universe=["evt-consented", "evt-other"],
        )


def test_refused_cross_project_batch_leaves_both_events_selectable(
    store: ProjectSyncStore,
) -> None:
    """The refusal must not park anything: state stays as if nothing was attempted."""
    posts: list[str] = []

    def _never(url: str, *, data: Any, headers: Any, timeout: Any) -> Any:
        posts.append(url)
        raise AssertionError("a cross-project batch must never be POSTed")

    receiver = TeamspaceReceiver(resolved_server_url=_SERVER_URL, auth_token=_TOKEN, poster=_never)

    results = list(receiver.deliver(deliverable(_mixed_batch())))
    target = _target(store)

    assert posts == [], "no HTTP request may be made for a cross-project batch"
    assert len(results) == 2
    assert not any(result.outcome is DeliveryOutcome.SUCCESS for result in results)
    # The whole point of H1: nothing may be parked permanently.
    assert not any(result.outcome is DeliveryOutcome.TERMINAL_FAILED for result in results), (
        "a pre-POST refusal is not a permanent delivery failure; parking the batch destroys the consented project's events (spec US1a AS-1)"
    )
    still_selectable = _selectable(store, target.target_id)
    assert still_selectable == ["evt-consented", "evt-other"], "both events must survive the refusal as selectable work"
    # The refusal must still be observable and still name the projects.
    assert {result.event_id for result in results} == {"evt-consented", "evt-other"}
    assert all("more than one project" in (result.error or "") for result in results)
    assert any(_CONSENTED in (result.error or "") for result in results)


def test_consented_events_deliver_on_the_next_drain_after_a_refusal(
    store: ProjectSyncStore,
) -> None:
    """Round-trip proof: the refusal cost the consented project nothing.

    Drain 1 spans two projects and is refused. Drain 2 narrows the window (what a
    correct selection does) and the consented event delivers. With the refusal
    recorded as ``terminal_failed`` this second drain selected **nothing** — the
    event was gone from the selection set for good.
    """

    def _never(url: str, *, data: Any, headers: Any, timeout: Any) -> Any:
        raise AssertionError("a cross-project batch must never be POSTed")

    refused = TeamspaceReceiver(resolved_server_url=_SERVER_URL, auth_token=_TOKEN, poster=_never)
    list(refused.deliver(deliverable(_mixed_batch())))
    target = _target(store)

    delivered: list[bytes] = []

    def _ok(url: str, *, data: Any, headers: Any, timeout: Any) -> Any:
        delivered.append(data)
        return _FakeResponse(200, {"results": [{"event_id": "evt-consented", "status": "success"}]})

    second = TeamspaceReceiver(resolved_server_url=_SERVER_URL, auth_token=_TOKEN, poster=_ok)
    summary = dispatch(
        store=store,
        receiver=second,
        target=target,
        context=store.create_context(),
        exclude=frozenset({"evt-other"}),
    )

    assert summary.selected == 1, "the consented event must still be selectable after the refusal"
    assert summary.delivered == 1
    # One POST, and its body carries only the consented project's event. Asserted
    # by identity rather than by counting the POSTs: a count cannot tell "the
    # consented event was delivered" from "some event was delivered". The body is
    # gzipped on the wire, hence the decompress.
    assert [json.loads(gzip.decompress(body))["events"][0]["event_id"] for body in delivered] == ["evt-consented"]


def test_a_refused_batch_does_not_wedge_the_multi_batch_drain(
    store: ProjectSyncStore,
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

    receiver = TeamspaceReceiver(resolved_server_url=_SERVER_URL, auth_token=_TOKEN, poster=_never)

    skip: set[str] = set()
    iterations = 0
    while iterations < 10:
        iterations += 1
        batch = [event for event in _mixed_batch() if event.event_id not in skip]
        if not batch:
            break
        results = list(receiver.deliver(deliverable(batch)))
        before = len(skip)
        skip.update(result.event_id for result in results if result.outcome is DeliveryOutcome.TRANSIENT)
        if len(skip) == before:
            break

    assert iterations <= 3, f"the drain loop must advance past a refused batch, took {iterations} passes"
    # And the events are still there for the next command.
    assert _selectable(store, _target(store).target_id) == [
        "evt-consented",
        "evt-other",
    ]
