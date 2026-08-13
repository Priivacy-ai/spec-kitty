"""T051 / FR-019: real stale-generation parking against a local test authority.

Project A is admitted at generation ``g``. A real CLI write is durably prepared
(the WP06 ``delivery_attempts`` row commits before any I/O), the local test
server's admission authority then advances to ``g+1`` **while that write is in
flight**, and the stale-``g`` write is released. The server double answers the
canonical correlated ``project_not_admitted`` refusal (status ``rejected``,
``retryable: false`` — the exact shape ``saas_client.admission.
parse_project_not_admitted`` validates).

Asserted, all on the client (core owns client parking; SaaS owns server
refusal/side-effect evidence — FR-019):

1. the refusal is correlated to exactly that write (event id and attempt id),
2. exactly that row parks terminally (``refused`` + ``project_not_admitted``),
3. there is **no transient retry** — no retryable classification, no
   re-selection, no automatic resend authorization, and
4. readmission at ``g+1`` does not revive the parked row: fresh admission
   requires fresh rows, and only a fresh row ships at the new generation.

The interleaving is real, not narrated: the server authority is advanced inside
a wrapper around the WP06 ``mark_transport_started`` transition — after the
prepared attempt row is durable, immediately before the physical send — the
same seam ``tests/support/sync_transport_barriers.py`` pauses at for the WP09
matrices.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

import pytest

from specify_cli.delivery.consent_gate import stable_transport_id
from specify_cli.delivery.dispatcher import dispatch
from specify_cli.delivery.receivers import DeliveryResult, OutboundEvent, map_batch_response
from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.saas_client.admission import parse_project_not_admitted
from specify_cli.sync import transport_attempts
from specify_cli.sync.consent import record_project_opt_in
from specify_cli.sync.layout_generation import LayoutMode
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.transport_attempts import (
    DeliveryAttemptState,
    DeliveryOutcome,
    RecoveryAction,
    plan_delivery_attempt_recovery,
)

pytestmark = [pytest.mark.integration, pytest.mark.fast]

PROJECT_A = "aaaaaaaa-0000-0000-0000-00000000000a"
_ACTOR = "stale-generation-parking"
STALE_EVENT_ID = "evt-stale-g1"
FRESH_EVENT_ID = "evt-fresh-g2"


class _GenerationAuthorityServer:
    """A local test server double that OWNS the admission-generation authority.

    ``deliver`` compares every write's carried admission proof against the
    server's current generation and answers the canonical per-event
    ``project_not_admitted`` refusal for a stale proof — correlated by
    ``event_id``, terminal (``retryable: false``), exactly as the SaaS batch
    ingress does. No production admission logic is mocked; the double only
    holds the generation counter this scenario needs to advance.
    """

    def __init__(self, generation: int) -> None:
        self.generation = generation
        self.batches: list[tuple[str, ...]] = []
        self.refused_event_ids: list[str] = []
        self.accepted_event_ids: list[str] = []

    @property
    def endpoint_url(self) -> str:
        return "http://localhost/__stale-generation-authority__/api/v1/events/batch/"

    def auth_headers(self) -> dict[str, str]:
        return {}

    def gates(self) -> tuple[Any, ...]:
        return ()

    def deliver(self, batch: Sequence[OutboundEvent]) -> list[DeliveryResult]:
        events = list(batch)
        self.batches.append(tuple(event.event_id for event in events))
        results: list[dict[str, Any]] = []
        for event in events:
            proof_generation = int(str(event.payload["admission_generation"]))
            if proof_generation != self.generation:
                refusal = {
                    "event_id": event.event_id,
                    "status": "rejected",
                    "error_category": "project_not_admitted",
                    "error": f"admission generation {proof_generation} is stale; authority is at {self.generation}",
                    "retryable": False,
                }
                # The refusal is the canonical correlated shape, provably:
                # parse_project_not_admitted fail-closes on anything else.
                parsed = parse_project_not_admitted("event", refusal, ("event_id",))
                assert parsed.correlation == (("event_id", event.event_id),)
                self.refused_event_ids.append(event.event_id)
                results.append(refusal)
            else:
                self.accepted_event_ids.append(event.event_id)
                results.append({"event_id": event.event_id, "status": "success"})
        return map_batch_response(events, http_status=200, body={"results": results})


def _event(event_id: str, *, ordinal: int) -> Event:
    created_at = f"2026-08-02T00:00:{ordinal:02d}+00:00"
    return Event(
        event_id=event_id,
        event_type="mission.updated",
        payload=json.dumps({"event_id": event_id}).encode("utf-8"),
        occurred_at=created_at,
        created_at=created_at,
        project_uuid=PROJECT_A,
    )


def _append(store: ProjectSyncStore, event: Event) -> None:
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        journal.append(event)


@pytest.fixture
def admitted_store(canonical_home: None, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    """Admit project A at generation g=1 with a real consent + admission row."""
    del canonical_home  # the ONE SPEC_KITTY_HOME owner (R1a #3121) pins the home
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    store = ProjectSyncStore(PROJECT_A)
    authority = store.layout_generation()
    if authority.read_state().mode is LayoutMode.LEGACY:
        authority.begin_cutover(_ACTOR)
        authority.publish_project_only(_ACTOR, verify_exact=lambda: True)
    record_project_opt_in(PROJECT_A, actor=_ACTOR)
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://hosted.example.com', 'operator@example.com', 'team', 1, "
            "'admitted', '1', 'private-teamspace:team')",
            (PROJECT_A,),
        )
    return store


def _resolved_target(store: ProjectSyncStore) -> Any:
    with store.unit_of_work() as unit:
        target = ProjectDeliveryTargetRegistry(store).get_current(unit)
    assert target is not None
    return target


def _attempt_rows(store: ProjectSyncStore) -> list[tuple[str, str, str, str | None, str | None, str | None]]:
    """(attempt_id, state, admission_generation, result_id, outcome, refusal_category) per attempt."""
    with store.unit_of_work() as unit:
        rows = unit.execute(
            "SELECT delivery_attempts.attempt_id, delivery_attempts.state, "
            "delivery_attempts.admission_generation, delivery_results.result_id, "
            "delivery_results.outcome, delivery_results.terminal_refusal_category "
            "FROM delivery_attempts LEFT JOIN delivery_results "
            "ON delivery_results.project_uuid = delivery_attempts.project_uuid "
            "AND delivery_results.attempt_id = delivery_attempts.attempt_id "
            "WHERE delivery_attempts.project_uuid = ? "
            "ORDER BY delivery_attempts.created_at, delivery_attempts.attempt_id",
            (PROJECT_A,),
        ).fetchall()
    return [
        (
            str(row[0]),
            str(row[1]),
            str(row[2]),
            str(row[3]) if row[3] is not None else None,
            str(row[4]) if row[4] is not None else None,
            str(row[5]) if row[5] is not None else None,
        )
        for row in rows
    ]


@contextmanager
def _advance_authority_between_prepare_and_send(
    server: _GenerationAuthorityServer,
    advanced_attempt_ids: list[str],
) -> Iterator[None]:
    """Advance the server to g+1 after the durable prepare, before the send."""
    original_mark = transport_attempts.mark_transport_started

    def _mark(unit: Any, context: Any, attempt_id: str, **kwargs: Any) -> Any:
        if not advanced_attempt_ids:
            server.generation += 1
            advanced_attempt_ids.append(attempt_id)
        return original_mark(unit, context, attempt_id, **kwargs)

    with patch.object(transport_attempts, "mark_transport_started", _mark):
        yield


def test_stale_generation_write_parks_terminally_and_never_revives(
    admitted_store: ProjectSyncStore,
) -> None:
    store = admitted_store
    target = _resolved_target(store)
    server = _GenerationAuthorityServer(generation=1)

    # A real CLI write exists durably at g=1 before any transport starts.
    _append(store, _event(STALE_EVENT_ID, ordinal=0))
    context_g1 = store.create_context()
    expected_attempt_id = "event:" + stable_transport_id("attempt", PROJECT_A, str(target.target_id), STALE_EVENT_ID)

    advanced: list[str] = []
    with _advance_authority_between_prepare_and_send(server, advanced):
        summary = dispatch(store=store, receiver=server, target=target, context=context_g1)

    # The interleaving genuinely happened: the durable attempt row committed at
    # g, THEN the server authority advanced to g+1, THEN the write was released.
    assert advanced == [expected_attempt_id]
    assert server.generation == 2
    assert server.batches == [(STALE_EVENT_ID,)]
    assert server.refused_event_ids == [STALE_EVENT_ID]

    # 1+2: a correlated project_not_admitted refusal parks exactly that row
    # terminally — never a transient/retryable classification.
    assert summary.selected == 1
    assert summary.terminal_failed == 1
    assert summary.delivered == 0 and summary.duplicate == 0
    assert summary.rejected == 0 and summary.transient == 0 and summary.pending == 0
    assert summary.retryable_event_ids == ()
    assert len(summary.failures) == 1
    failure = summary.failures[0]
    assert failure.event_id == STALE_EVENT_ID
    assert failure.outcome == "terminal_failed"
    assert failure.error is not None and "stale" in failure.error

    rows = _attempt_rows(store)
    assert len(rows) == 1, "exactly one durable attempt row may exist for the stale write"
    attempt_id, state, admission_generation, result_id, outcome, category = rows[0]
    assert attempt_id == expected_attempt_id
    assert state == DeliveryAttemptState.REFUSED.value
    assert admission_generation == "1", "the parked row is bound to the stale generation it was prepared under"
    assert result_id == f"{expected_attempt_id}:result"
    assert outcome == DeliveryOutcome.REFUSED.value
    assert category == "project_not_admitted"

    # 3: no transient retry. The WP06 recovery planner refuses automatic
    # resend for the parked row...
    with store.unit_of_work() as unit:
        decision = plan_delivery_attempt_recovery(unit, attempt_id=expected_attempt_id)
    assert decision.may_resend is False
    assert decision.action is RecoveryAction.OPERATOR_REVIEW
    assert "terminal result already exists" in decision.diagnostic

    # ...and a second drain re-selects nothing and reaches the server with
    # nothing: the park is durable exclusion, not an in-memory skip.
    retry_summary = dispatch(store=store, receiver=server, target=target, context=store.create_context())
    assert retry_summary.selected == 0
    assert server.batches == [(STALE_EVENT_ID,)], "the stale write was retransmitted after terminal parking"

    # 4: readmission at g+1 does not revive the parked row.
    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE project_target_admissions SET admission_generation = '2' WHERE project_uuid = ?",
            (PROJECT_A,),
        )
    context_g2 = store.create_context()
    readmitted_summary = dispatch(store=store, receiver=server, target=_resolved_target(store), context=context_g2)
    assert readmitted_summary.selected == 0
    assert server.batches == [(STALE_EVENT_ID,)], "readmission revived a terminally parked stale-generation row"
    assert _attempt_rows(store)[0][1] == DeliveryAttemptState.REFUSED.value

    # Fresh admission requires fresh rows: a NEW write at g+1 ships, carrying
    # the new proof, while the stale row's bytes never travel again.
    _append(store, _event(FRESH_EVENT_ID, ordinal=1))
    fresh_summary = dispatch(store=store, receiver=server, target=_resolved_target(store), context=context_g2)
    assert fresh_summary.selected == 1
    assert fresh_summary.delivered == 1
    assert server.batches == [(STALE_EVENT_ID,), (FRESH_EVENT_ID,)]
    assert server.accepted_event_ids == [FRESH_EVENT_ID]

    rows_after = _attempt_rows(store)
    assert len(rows_after) == 2, "fresh admission must mint a fresh attempt row, never reuse the parked one"
    by_id = {row[0]: row for row in rows_after}
    parked = by_id[expected_attempt_id]
    assert parked[1] == DeliveryAttemptState.REFUSED.value
    assert parked[2] == "1"
    fresh_attempt_id = "event:" + stable_transport_id("attempt", PROJECT_A, str(target.target_id), FRESH_EVENT_ID)
    fresh = by_id[fresh_attempt_id]
    assert fresh[1] == DeliveryAttemptState.SUCCEEDED.value
    assert fresh[2] == "2"
    assert fresh[4] == DeliveryOutcome.DELIVERED.value


def test_readmitted_generation_write_is_accepted_by_the_same_authority(
    admitted_store: ProjectSyncStore,
) -> None:
    """Control: the same server double accepts a matching-generation write.

    Without this, the parking test could pass against a server that refuses
    everything — the refusal would then prove nothing about generation
    staleness.
    """
    store = admitted_store
    target = _resolved_target(store)
    server = _GenerationAuthorityServer(generation=1)
    _append(store, _event("evt-current-g1", ordinal=0))

    summary = dispatch(store=store, receiver=server, target=target, context=store.create_context())

    assert summary.delivered == 1
    assert summary.terminal_failed == 0
    assert server.accepted_event_ids == ["evt-current-g1"]
    assert server.refused_event_ids == []
    rows = _attempt_rows(store)
    assert len(rows) == 1
    assert rows[0][1] == DeliveryAttemptState.SUCCEEDED.value
