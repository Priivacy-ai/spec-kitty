"""ATDD + unit coverage for the WP07 Sync Dispatcher (IC-05 / IC-05a).

Every assertion here is on **observable on-disk / ledger / receiver state** — never
on internal call order (NFR-001). The dispatcher is driven through the WP03 journal,
the WP05 ledger, and a WP06 receiver (the credential-free stub, SC-005); the five
contract §3 "Required tests" map onto the scenario tests below:

* A->B replay (FR-005 / SC-001, contract §3 row 1) — :func:`test_replay_to_new_target_redelivers_and_retains`.
* Re-sync skips already-successful (FR-004, contract §3 row 2) — :func:`test_resync_to_same_target_skips_delivered`.
* Non-destructive success (FR-001) — :func:`test_success_is_non_destructive`.
* Oversized / permanent failure progresses the drain (FR-015 / IC-05a, contract §3 row 4) —
  :func:`test_terminal_failed_parks_event_and_drain_progresses`.
* Idempotent re-delivery (NFR-003) — :func:`test_idempotent_redelivery_yields_duplicate`.

Plus focused unit tests over the select / post / record phases and the D-020
coalescing carry so each helper is exercised directly (T044 / coverage).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import sync as sync_module
from specify_cli.delivery.consent_gate import (
    ProjectTransportDisclosure,
    ProjectTransportRefusal,
    _attempt_spec,
    execute_project_transport_batch,
    stable_transport_id,
)
from specify_cli.delivery.dispatcher import (
    DispatchSummary,
    _decode_payload,
    _dispatcher_payload_reference,
    _install_coalescing,
    _post,
    _record,
    _record_one,
    _select_undelivered,
    dispatch,
    prepare_event_transport,
)
from specify_cli.delivery.ledger import (
    STATUS_DUPLICATE,
    STATUS_PENDING,
    STATUS_SUCCESS,
    STATUS_TERMINAL_FAILED,
    TERMINAL_SUCCESS_STATUSES,
    SqliteDeliveryLedger,
)
from specify_cli.delivery.interfaces import DeliveryTarget, TargetIdentity
from specify_cli.delivery.targets import compute_target_id
from specify_cli.delivery.receivers import (
    DeliveryEffectCertainty,
    DeliveryOutcome,
    DeliveryResult,
    StubReceiver,
    TeamspaceReceiver,
    map_batch_response,
)
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.sync.project_context import AdmissionState, ProjectSyncContext
from specify_cli.sync.project_identity import CanonicalProjectUUID
from specify_cli.sync.project_store import ProjectSyncStore, ProjectUnitOfWork
from specify_cli.sync.transport_attempts import (
    get_delivery_attempt_record,
    prepare_delivery_attempt,
    recover_delivery_attempts,
)
from tests._support.consented_batches import granting

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

_OCCURRED_AT = "2026-06-29T00:00:00+00:00"

# #3030 WP06: selection now requires a consented project identity. These tests are
# about ledger/limit/multi-batch mechanics, so they carry one consented project and
# keep asserting exactly what they always did. Identity-less and non-consenting
# selection are pinned separately (test_incident_reproduction_3030.py,
# test_dispatch_project_consent_3030.py).
_TEST_PROJECT_UUID = "dddddddd-0000-0000-0000-00000000000d"


@pytest.fixture(autouse=True)
def _consent_to_the_test_project(tmp_path: Any, monkeypatch: Any) -> None:
    """Record hosted-sync consent for this module's single project."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "consent-home"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    (tmp_path / "consent-home").mkdir(parents=True, exist_ok=True)
    from specify_cli.sync.consent import record_project_opt_in

    record_project_opt_in(_TEST_PROJECT_UUID, actor="tester")
    _admit_project_for_transport(_TEST_PROJECT_UUID)


def _admit_project_for_transport(project_uuid: str) -> None:
    """Seed the WP06 target admission needed by WP07's final transport gate."""
    store = ProjectSyncStore(project_uuid)
    authority = store.layout_generation()
    authority.begin_cutover("wp07-dispatcher-test")
    authority.publish_project_only("wp07-dispatcher-test", verify_exact=lambda: True)
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'dispatcher-test-target', 'account-test', 'teamspace-test', 1, "
            "'admitted', '1', 'private-teamspace:teamspace-test')",
            (project_uuid,),
        )


# --------------------------------------------------------------------------- #
# Fixtures / builders                                                          #
# --------------------------------------------------------------------------- #


def _make_event(index: int) -> Event:
    """Build a distinct JSON-payload journal event with a deterministic timestamp."""
    event_id = f"evt-{index}"
    payload = json.dumps({"event_id": event_id, "event_type": "mission.updated", "n": index}).encode("utf-8")
    return Event(
        event_id=event_id,
        event_type="mission.updated",
        payload=payload,
        occurred_at=_OCCURRED_AT,
        created_at=f"2026-06-29T00:00:0{index}+00:00",
        project_uuid=_TEST_PROJECT_UUID,
    )


@pytest.fixture
def store() -> ProjectSyncStore:
    value = ProjectSyncStore(_TEST_PROJECT_UUID)
    with value.unit_of_work() as active:
        journal = EventJournal(active, value.layout_generation())
        if journal.count() == 0:
            for index in range(3):
                journal.append(_make_event(index))
    return value


@pytest.fixture
def unit(store: ProjectSyncStore) -> Any:
    with store.unit_of_work() as active:
        yield active


@pytest.fixture
def context(store: ProjectSyncStore) -> ProjectSyncContext:
    return store.create_context()


@pytest.fixture
def journal(store: ProjectSyncStore, unit: ProjectUnitOfWork) -> EventJournal:
    """A journal seeded with three distinct events (the drain universe)."""
    return EventJournal(unit, store.layout_generation())


@pytest.fixture
def ledger(store: ProjectSyncStore, unit: ProjectUnitOfWork) -> SqliteDeliveryLedger:
    return SqliteDeliveryLedger(unit, store.layout_generation())


def _journal_count(store: ProjectSyncStore) -> int:
    with store.unit_of_work() as unit:
        return int(EventJournal(unit, store.layout_generation()).count())


def _journal_read_by_id(store: ProjectSyncStore, event_id: str) -> Event | None:
    with store.unit_of_work() as unit:
        return EventJournal(unit, store.layout_generation()).read_by_id(event_id)


def _ledger_get(store: ProjectSyncStore, event_id: str, target_id: str) -> Any:
    with store.unit_of_work() as unit:
        return SqliteDeliveryLedger(unit, store.layout_generation()).get(event_id, target_id)


def _recoverable_attempts_for_event(
    store: ProjectSyncStore,
    *,
    event_id: str,
    target_id: str,
) -> list[tuple[str, str, str]]:
    with store.unit_of_work() as unit:
        return [
            (record.attempt_id, record.native_identity or "", record.state.value)
            for record in recover_delivery_attempts(unit)
            if record.native_identity == event_id
            and record.attempt_id
            == "event:"
            + stable_transport_id(
                "attempt",
                _TEST_PROJECT_UUID,
                target_id,
                event_id,
            )
        ]


def _attempt_record(store: ProjectSyncStore, attempt_id: str) -> tuple[str, str, str]:
    with store.unit_of_work() as unit:
        record = get_delivery_attempt_record(unit, attempt_id=attempt_id)
    assert record is not None
    return record.attempt_id, record.native_identity or "", record.state.value


def _dispatcher_disclosure_for(
    event: Event,
    *,
    target: DeliveryTarget,
    context: ProjectSyncContext,
) -> ProjectTransportDisclosure:
    assert event.project_uuid is not None
    prepared = prepare_event_transport(
        _decode_payload(event),
        event_id=event.event_id,
        project_uuid=event.project_uuid,
        context=context,
    )
    assert prepared.target_id == target.target_id
    return prepared.disclosure


def _select_with_store(
    store: ProjectSyncStore,
    target_id: str,
    *,
    limit: int | None = None,
) -> Any:
    context = store.create_context()
    with store.unit_of_work() as unit:
        return _select_undelivered(
            EventJournal(unit, store.layout_generation()),
            SqliteDeliveryLedger(unit, store.layout_generation()),
            target_id,
            context=context,
            limit=limit,
        )


@pytest.fixture
def target_a() -> DeliveryTarget:
    target = DeliveryTarget(
        target_id="",
        identity=TargetIdentity(
            target_identity="dispatcher-test-target",
            account_identity="account-test",
            private_teamspace_id="teamspace-test",
            project_uuid=CanonicalProjectUUID.parse(_TEST_PROJECT_UUID),
            configuration_generation=1,
        ),
        admission_state=AdmissionState.ADMITTED,
        admission_generation=1,
        binding_audience="private-teamspace:teamspace-test",
        last_error_category=None,
    )
    return DeliveryTarget(
        target_id=compute_target_id(
            target_identity=target.target_identity,
            account_identity=target.account_identity,
            private_teamspace_id=target.private_teamspace_id,
            project_uuid=target.project_uuid,
            configuration_generation=target.configuration_generation,
        ),
        identity=target.identity,
        admission_state=target.admission_state,
        admission_generation=target.admission_generation,
        binding_audience=target.binding_audience,
        last_error_category=target.last_error_category,
    )


@pytest.fixture
def target_b() -> DeliveryTarget:
    target = DeliveryTarget(
        target_id="",
        identity=TargetIdentity(
            target_identity="dispatcher-test-target-b",
            account_identity="account-test",
            private_teamspace_id="teamspace-test",
            project_uuid=CanonicalProjectUUID.parse(_TEST_PROJECT_UUID),
            configuration_generation=2,
        ),
        admission_state=AdmissionState.ADMITTED,
        admission_generation=2,
        binding_audience="private-teamspace:teamspace-test",
        last_error_category=None,
    )
    return DeliveryTarget(
        target_id=compute_target_id(
            target_identity=target.target_identity,
            account_identity=target.account_identity,
            private_teamspace_id=target.private_teamspace_id,
            project_uuid=target.project_uuid,
            configuration_generation=target.configuration_generation,
        ),
        identity=target.identity,
        admission_state=target.admission_state,
        admission_generation=target.admission_generation,
        binding_audience=target.binding_audience,
        last_error_category=target.last_error_category,
    )


def _admit_target(store: ProjectSyncStore, target: DeliveryTarget) -> ProjectSyncContext:
    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE project_target_admissions SET target_identity = ?, account_identity = ?, "
            "private_teamspace_id = ?, configuration_generation = ?, admission_state = ?, "
            "admission_generation = ?, binding_audience = ? WHERE project_uuid = ?",
            (
                target.target_identity,
                target.account_identity,
                target.private_teamspace_id,
                target.configuration_generation,
                target.admission_state.value,
                str(target.admission_generation),
                target.binding_audience,
                _TEST_PROJECT_UUID,
            ),
        )
    return store.create_context()


class _TerminalFailStub:
    """A real DeliveryReceiver (§4) that maps one chosen event to terminal-failed.

    Exercises the FR-015 mixed-batch path: every other event delivers successfully.
    No ``isinstance`` is needed in the dispatcher — it drives this through the same
    contract as :class:`StubReceiver`.
    """

    def __init__(self, *, fail_id: str) -> None:
        self._fail_id = fail_id
        self._delivered: list[str] = []

    @property
    def endpoint_url(self) -> str:
        return "http://localhost/__terminal-fail-stub__/api/v1/events/batch/"

    def auth_headers(self) -> dict[str, str]:
        return {}

    def gates(self) -> tuple[Any, ...]:
        return ()

    def deliver(self, batch: Any) -> list[DeliveryResult]:
        results: list[DeliveryResult] = []
        for event in batch:
            if event.event_id == self._fail_id:
                results.append(
                    DeliveryResult(
                        event_id=event.event_id,
                        outcome=DeliveryOutcome.TERMINAL_FAILED,
                        http_status=413,
                        error="payload too large (oversized, permanent)",
                        effect_certainty=DeliveryEffectCertainty.TERMINAL,
                    )
                )
            else:
                self._delivered.append(event.event_id)
                results.append(
                    DeliveryResult(
                        event_id=event.event_id,
                        outcome=DeliveryOutcome.SUCCESS,
                        http_status=200,
                    )
                )
        return results

    def delivered_ids(self) -> tuple[str, ...]:
        return tuple(self._delivered)


class _PendingHeadStub:
    """Return pending for the first two events and success for later events."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    @property
    def endpoint_url(self) -> str:
        return "http://localhost/__pending-head-stub__/api/v1/events/batch/"

    def auth_headers(self) -> dict[str, str]:
        return {}

    def gates(self) -> tuple[Any, ...]:
        return ()

    def deliver(self, batch: Any) -> list[DeliveryResult]:
        self.calls.append(tuple(event.event_id for event in batch))
        return [
            DeliveryResult(
                event_id=event.event_id,
                outcome=(DeliveryOutcome.PENDING if event.event_id in {"evt-0", "evt-1"} else DeliveryOutcome.SUCCESS),
                http_status=200,
                effect_certainty=(DeliveryEffectCertainty.ACCEPTED_PENDING if event.event_id in {"evt-0", "evt-1"} else DeliveryEffectCertainty.POSSIBLY_EFFECTIVE),
            )
            for event in batch
        ]


class _DuplicateStub:
    """Return duplicate for every event on the first canonical WP06 attempt."""

    @property
    def endpoint_url(self) -> str:
        return "http://localhost/__duplicate-stub__/api/v1/events/batch/"

    def auth_headers(self) -> dict[str, str]:
        return {}

    def gates(self) -> tuple[Any, ...]:
        return ()

    def deliver(self, batch: Any) -> list[DeliveryResult]:
        return [DeliveryResult(event_id=event.event_id, outcome=DeliveryOutcome.DUPLICATE) for event in batch]


class _RaisingStub:
    def __init__(self) -> None:
        self.calls = 0

    @property
    def endpoint_url(self) -> str:
        return "http://localhost/__raising-stub__/api/v1/events/batch/"

    def auth_headers(self) -> dict[str, str]:
        return {}

    def gates(self) -> tuple[Any, ...]:
        return ()

    def deliver(self, batch: Any) -> list[DeliveryResult]:
        self.calls += 1
        raise RuntimeError("network died after start")


class _AdaptiveOversizedStub:
    """Exercise the canonical mapper's batch-413 then singleton-terminal path."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    @property
    def endpoint_url(self) -> str:
        return "http://localhost/__adaptive-oversized-stub__/api/v1/events/batch/"

    def auth_headers(self) -> dict[str, str]:
        return {}

    def gates(self) -> tuple[Any, ...]:
        return ()

    def deliver(self, batch: Any) -> list[DeliveryResult]:
        events = list(batch)
        self.calls.append(tuple(event.event_id for event in events))
        if events and events[0].event_id == "evt-0":
            return map_batch_response(events, http_status=413, body=None)
        return map_batch_response(
            events,
            http_status=200,
            body={"results": [{"event_id": event.event_id, "status": "success"} for event in events]},
        )


class _ProtocolMismatchStub:
    """A real DeliveryReceiver whose server answers every POST with HTTP 412 (#1553).

    Routes through the canonical :func:`map_batch_response` so the ledger rows
    it produces are exactly what a Teamspace 412 produces.
    """

    _BODY = {
        "error_code": "client-too-old",
        "error_description": "Client protocol version is below the supported minimum.",
        "sync_protocol": {"upgrade_guidance": "Run `spec-kitty upgrade` to update to a supported release."},
    }

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    @property
    def endpoint_url(self) -> str:
        return "http://localhost/__protocol-mismatch-stub__/api/v1/events/batch/"

    def auth_headers(self) -> dict[str, str]:
        return {}

    def gates(self) -> tuple[Any, ...]:
        return ()

    def deliver(self, batch: Any) -> list[DeliveryResult]:
        events = list(batch)
        self.calls.append(tuple(event.event_id for event in events))
        return map_batch_response(events, http_status=412, body=self._BODY)


class _KnownNoEffectOnceStub:
    """First call proves no remote effect for evt-0; later calls succeed."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    @property
    def endpoint_url(self) -> str:
        return "http://localhost/__known-no-effect-once__/api/v1/events/batch/"

    def auth_headers(self) -> dict[str, str]:
        return {}

    def gates(self) -> tuple[Any, ...]:
        return ()

    def deliver(self, batch: Any) -> list[DeliveryResult]:
        self.calls.append(tuple(event.event_id for event in batch))
        if len(self.calls) == 1:
            return [
                DeliveryResult(
                    event_id=event.event_id,
                    outcome=(DeliveryOutcome.REJECTED if event.event_id == "evt-0" else DeliveryOutcome.SUCCESS),
                    http_status=400 if event.event_id == "evt-0" else 200,
                    error="known no effect" if event.event_id == "evt-0" else None,
                    effect_certainty=(DeliveryEffectCertainty.KNOWN_NO_EFFECT if event.event_id == "evt-0" else DeliveryEffectCertainty.POSSIBLY_EFFECTIVE),
                )
                for event in batch
            ]
        return [DeliveryResult(event_id=event.event_id, outcome=DeliveryOutcome.SUCCESS, http_status=200) for event in batch]


class _ProjectNotAdmittedMixedStub:
    """Return one terminal project refusal beside one successful item."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    @property
    def endpoint_url(self) -> str:
        return "http://localhost/__project-not-admitted-mixed__/api/v1/events/batch/"

    def auth_headers(self) -> dict[str, str]:
        return {}

    def gates(self) -> tuple[Any, ...]:
        return ()

    def deliver(self, batch: Any) -> list[DeliveryResult]:
        self.calls.append(tuple(event.event_id for event in batch))
        results: list[DeliveryResult] = []
        for event in batch:
            if event.event_id == "evt-0":
                results.append(
                    DeliveryResult(
                        event_id=event.event_id,
                        outcome=DeliveryOutcome.TERMINAL_FAILED,
                        http_status=200,
                        error="not admitted for project",
                        error_category="project_not_admitted",
                        effect_certainty=DeliveryEffectCertainty.TERMINAL,
                    )
                )
            else:
                results.append(
                    DeliveryResult(
                        event_id=event.event_id,
                        outcome=DeliveryOutcome.SUCCESS,
                        http_status=200,
                    )
                )
        return results


class _FakeCoalesce:
    """Stand-in for WP08's ``event_journal.coalesce`` module (a merge-time sibling)."""

    def __init__(self) -> None:
        self.installed_with: object | None = None

    def install(self, ledger: object) -> str:
        self.installed_with = ledger
        return "fake-strategy"


# --------------------------------------------------------------------------- #
# Scenario 1 — A->B replay (FR-005 / SC-001, contract §3 row 1)                #
# --------------------------------------------------------------------------- #


def test_replay_to_new_target_redelivers_and_retains(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
    target_b: DeliveryTarget,
) -> None:
    stub_a = StubReceiver()
    stub_b = StubReceiver()

    summary_a = dispatch(store=store, receiver=stub_a, target=target_a, context=context)
    assert summary_a.delivered == 3
    assert _journal_count(store) == 3  # retention: nothing deleted on success (FR-001)
    assert set(stub_a.received_event_ids()) == {"evt-0", "evt-1", "evt-2"}
    for index in range(3):
        row = _ledger_get(store, f"evt-{index}", target_a.target_id)
        assert row is not None and row.status in TERMINAL_SUCCESS_STATUSES

    # Switch the active target: the same retained events have no terminal-success
    # row for B, so they re-select and re-deliver — zero manual SQLite copying.
    context_b = _admit_target(store, target_b)
    summary_b = dispatch(store=store, receiver=stub_b, target=target_b, context=context_b)
    assert summary_b.delivered == 3
    assert _journal_count(store) == 3  # still fully retained after BOTH drains (SC-002)
    assert set(stub_b.received_event_ids()) == {"evt-0", "evt-1", "evt-2"}
    for index in range(3):
        row = _ledger_get(store, f"evt-{index}", target_b.target_id)
        assert row is not None and row.status in TERMINAL_SUCCESS_STATUSES


# --------------------------------------------------------------------------- #
# Scenario 2 — re-sync skips already-successful (FR-004, contract §3 row 2)    #
# --------------------------------------------------------------------------- #


def test_resync_to_same_target_skips_delivered(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
) -> None:
    stub = StubReceiver()

    first = dispatch(store=store, receiver=stub, target=target_a, context=context)
    assert first.selected == 3 and first.delivered == 3

    second = dispatch(store=store, receiver=stub, target=target_a, context=context)
    assert second.selected == 0  # all terminal-successful for A → nothing to drain
    assert second.delivered == 0
    # The stub was not asked to deliver anything new on the second drain.
    assert len(stub.received_event_ids()) == 3


def test_sync_now_public_command_reports_empty_admitted_project_store(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public command reports an admitted empty selection as a zero drain."""
    delivered = StubReceiver()
    first = dispatch(store=store, receiver=delivered, target=target_a, context=context)
    assert first.delivered == 3

    receiver = StubReceiver()
    runtime = sync_module._ProjectDispatchRuntime(
        target=SimpleNamespace(resolved_server_url="https://app.spec-kitty.ai"),
        store=store,
        context=context,
        delivery_target=target_a,
    )
    service = SimpleNamespace(
        queue=SimpleNamespace(size=lambda: 0),
        drain_body_uploads_only=lambda: None,
    )
    preflight = SimpleNamespace(ok=True, render=lambda _console: None)
    gate = SimpleNamespace(blocked=False, unsatisfied=())
    config = SimpleNamespace(mode=SimpleNamespace(name="TEAMSPACE"))

    monkeypatch.setattr("specify_cli.sync.preflight.run_preflight", lambda **_: preflight)
    monkeypatch.setattr("specify_cli.sync.background.get_sync_service", lambda: service)
    monkeypatch.setattr(sync_module, "enforce_teamspace_mission_state_ready", lambda **_: None)
    monkeypatch.setattr(sync_module, "_event_sync_retained_work_present", lambda: False)
    monkeypatch.setattr(sync_module, "_open_project_dispatch_runtime", lambda: runtime)
    monkeypatch.setattr(sync_module, "_load_event_sync_config", lambda: config)
    monkeypatch.setattr(sync_module, "_event_sync_access_token", lambda: "token")
    monkeypatch.setattr(
        sync_module,
        "_resolve_gated_receiver",
        lambda *_args, **_kwargs: (receiver, gate),
    )

    result = CliRunner().invoke(sync_module.app, ["now"])

    assert result.exit_code == 0, result.output
    assert "delivered 0" in result.output
    assert "selected 0" in result.output
    assert sync_module._NOTHING_TO_DELIVER in result.output
    assert receiver.received_event_ids() == ()


# --------------------------------------------------------------------------- #
# Scenario 3 — non-destructive success (FR-001)                               #
# --------------------------------------------------------------------------- #


def test_success_is_non_destructive(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
) -> None:
    before = _journal_count(store)
    stub = StubReceiver()

    dispatch(store=store, receiver=stub, target=target_a, context=context)

    assert _journal_count(store) == before  # row count identical before/after (no DELETE)
    for index in range(3):
        event_id = f"evt-{index}"
        assert _journal_read_by_id(store, event_id) is not None  # payload retained
        row = _ledger_get(store, event_id, target_a.target_id)
        assert row is not None and row.status == STATUS_SUCCESS


# --------------------------------------------------------------------------- #
# Scenario 4 — oversized / permanent failure (FR-015 / IC-05a, §3 row 4)      #
# --------------------------------------------------------------------------- #


def test_terminal_failed_parks_event_and_drain_progresses(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
) -> None:
    stub = _TerminalFailStub(fail_id="evt-1")

    summary = dispatch(store=store, receiver=stub, target=target_a, context=context)

    # The deliverable events progressed; the oversized one parked — drain did not stall.
    assert summary.delivered == 2
    assert summary.terminal_failed == 1
    assert stub.delivered_ids() == ("evt-0", "evt-2")

    # The oversized event is terminal-failed (NOT deleted, NOT success) and retained.
    parked = _ledger_get(store, "evt-1", target_a.target_id)
    assert parked is not None and parked.status == STATUS_TERMINAL_FAILED
    assert _journal_count(store) == 3  # nothing destroyed
    assert _journal_read_by_id(store, "evt-1") is not None  # inspectable (FR-015)

    # The next drain does NOT re-select the parked event (selector-exclusion is how
    # we keep the drain progressing without destroying the payload).
    next_selection = _select_with_store(store, target_a.target_id)
    assert [event.event_id for event in next_selection.events] == []

    second = dispatch(store=store, receiver=stub, target=target_a, context=context)
    assert second.selected == 0  # parked + delivered all excluded


def test_terminal_failed_is_per_target(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
    target_b: DeliveryTarget,
) -> None:
    dispatch(store=store, receiver=_TerminalFailStub(fail_id="evt-1"), target=target_a, context=context)

    # An event terminal-failed on A is still selectable for B (terminal-failed is
    # per-target, contract §3 / T043 edge case).
    _admit_target(store, target_b)
    selectable_for_b = _select_with_store(store, target_b.target_id)
    assert "evt-1" in [event.event_id for event in selectable_for_b.events]


# --------------------------------------------------------------------------- #
# Scenario 5 — idempotent re-delivery (NFR-003)                               #
# --------------------------------------------------------------------------- #


def test_idempotent_redelivery_yields_duplicate(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
) -> None:
    summary = dispatch(store=store, receiver=_DuplicateStub(), target=target_a, context=context)

    assert summary.duplicate == 3
    assert _journal_count(store) == 3
    for index in range(3):
        row = _ledger_get(store, f"evt-{index}", target_a.target_id)
        assert row is not None and row.status == STATUS_DUPLICATE
        assert row.attempt_count == 1


def test_unknown_dispatch_attempt_is_not_resent_or_replaced(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
) -> None:
    raising = _RaisingStub()

    with pytest.raises(RuntimeError, match="network died"):
        dispatch(store=store, receiver=raising, target=target_a, context=context, limit=1)

    retry = StubReceiver()
    second = dispatch(store=store, receiver=retry, target=target_a, context=context, limit=1)

    assert second.selected == 1
    assert second.delivered == 1
    assert raising.calls == 1
    assert retry.received_event_ids() == ("evt-1",)
    with store.unit_of_work() as unit:
        attempts = unit.execute(
            "SELECT payload_reference, state FROM delivery_attempts WHERE project_uuid = ? ORDER BY attempt_id",
            (_TEST_PROJECT_UUID,),
        ).fetchall()
    evt0_attempts = [row for row in attempts if "evt-0" in str(row[0])]
    assert len(evt0_attempts) == 1
    assert str(evt0_attempts[0][1]) == "unknown"


def test_dispatcher_projection_ignores_unrelated_transport_attempts(
    store: ProjectSyncStore,
    target_a: DeliveryTarget,
) -> None:
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO delivery_attempts "
            "(attempt_id, project_uuid, epoch_id, consent_generation, target_generation, "
            "admission_generation, binding_audience, payload_hash, payload_reference, "
            "state, deadline_at, reconciliation_policy, created_at) "
            "VALUES ('body-attempt', ?, 1, 1, 1, '1', 'private-teamspace:teamspace-test', "
            "'sha256:body', ?, 'prepared', '2999-01-01T00:00:00Z', 'operator_review', ?)",
            (
                _TEST_PROJECT_UUID,
                json.dumps({"write_kind": "body_upload", "payload_reference": "body:x"}),
                _OCCURRED_AT,
            ),
        )
    selected = _select_with_store(store, target_a.target_id)
    assert [event.event_id for event in selected.events] == ["evt-0", "evt-1", "evt-2"]


def test_dispatcher_projection_rejects_conflicting_terminal_history(
    store: ProjectSyncStore,
    target_a: DeliveryTarget,
) -> None:
    reference = json.dumps(
        {
            "schema": "spec-kitty.dispatcher.v1",
            "event_id": "evt-0",
            "target_id": target_a.target_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    metadata = json.dumps(
        {
            "write_kind": "dispatcher_http_event",
            "payload_reference": reference,
        },
        sort_keys=True,
    )
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO delivery_attempts "
            "(attempt_id, project_uuid, epoch_id, consent_generation, target_generation, "
            "admission_generation, binding_audience, payload_hash, payload_reference, "
            "state, deadline_at, reconciliation_policy, created_at) "
            "VALUES ('dispatcher-conflict', ?, 1, 1, 1, '1', 'private-teamspace:teamspace-test', "
            "'sha256:event', ?, 'succeeded', '2999-01-01T00:00:00Z', 'native_identity_retry', ?)",
            (_TEST_PROJECT_UUID, metadata, _OCCURRED_AT),
        )
        for result_id, outcome in (
            ("dispatcher-conflict:delivered", "delivered"),
            ("dispatcher-conflict:refused", "refused"),
        ):
            unit.execute(
                "INSERT INTO delivery_results "
                "(result_id, project_uuid, epoch_id, attempt_id, target_generation, "
                "admission_generation, outcome, terminal_refusal_category, recorded_at) "
                "VALUES (?, ?, 1, 'dispatcher-conflict', 1, '1', ?, ?, ?)",
                (
                    result_id,
                    _TEST_PROJECT_UUID,
                    outcome,
                    "project_refused" if outcome == "refused" else None,
                    _OCCURRED_AT,
                ),
            )
    with store.unit_of_work() as unit:
        ledger = SqliteDeliveryLedger(unit, store.layout_generation())
        with pytest.raises(ValueError, match="conflicting result history"):
            ledger.get("evt-0", target_a.target_id)


def test_record_rolls_back_batch_on_mid_record_failure(
    store: ProjectSyncStore,
    unit: ProjectUnitOfWork,
    journal: EventJournal,
    target_a: DeliveryTarget,
) -> None:
    """A ledger failure while recording a remote batch leaves no partial rows."""
    for event_id in ("evt-a", "evt-b"):
        journal.append(
            Event(
                event_id=event_id,
                event_type="mission.updated",
                payload=json.dumps({"event_id": event_id}).encode("utf-8"),
                occurred_at=_OCCURRED_AT,
                created_at="2026-06-29T00:00:09+00:00",
                project_uuid=_TEST_PROJECT_UUID,
            )
        )

    class _FailAfterFirstLedger(SqliteDeliveryLedger):
        calls = 0

        def record_result(self, *, event_id: str, target_id: str, result: object) -> None:
            self.calls += 1
            super().record_result(event_id=event_id, target_id=target_id, result=result)
            if self.calls == 1:
                raise sqlite3.OperationalError("synthetic ledger failure")

    ledger = _FailAfterFirstLedger(unit, store.layout_generation())
    results = [
        DeliveryResult(event_id="evt-a", outcome=DeliveryOutcome.SUCCESS),
        DeliveryResult(event_id="evt-b", outcome=DeliveryOutcome.SUCCESS),
    ]

    with pytest.raises(sqlite3.OperationalError):
        _record(ledger, target_a.target_id, results, selected=2)

    assert ledger.get("evt-a", target_a.target_id) is None
    assert ledger.get("evt-b", target_a.target_id) is None


# --------------------------------------------------------------------------- #
# No active target → no-op (T039 step 4)                                       #
# --------------------------------------------------------------------------- #


def test_no_active_target_is_a_noop(store: ProjectSyncStore) -> None:
    stub = StubReceiver()

    summary = dispatch(store=store, receiver=stub, target=None)

    assert summary.target_id is None
    assert summary.selected == 0
    assert summary.recorded == 0
    assert stub.received_event_ids() == ()  # the receiver was never invoked
    assert _journal_count(store) == 3  # nothing touched


# --------------------------------------------------------------------------- #
# Phase-level unit tests (T044: each phase independently testable)            #
# --------------------------------------------------------------------------- #


def test_select_undelivered_uses_universe_and_excludes_terminal(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
) -> None:
    # Initially every journal event is undelivered for A.
    selected = _select_undelivered(journal, ledger, target_a.target_id, context=context)
    assert [event.event_id for event in selected.events] == ["evt-0", "evt-1", "evt-2"]

    # Mark one delivered and one terminal-failed → both leave the selection set.
    ledger.record_success("evt-0", target_a.target_id)
    ledger.record_terminal_failed("evt-2", target_a.target_id)
    remaining = _select_undelivered(journal, ledger, target_a.target_id, context=context)
    assert [event.event_id for event in remaining.events] == ["evt-1"]


def test_select_undelivered_honours_limit(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
) -> None:
    selected = _select_undelivered(journal, ledger, target_a.target_id, context=context, limit=2)
    assert [event.event_id for event in selected.events] == ["evt-0", "evt-1"]


def test_post_empty_selection_short_circuits() -> None:
    stub = StubReceiver()
    assert _post(stub, [], granting(), target_id="target-test") == []
    assert stub.received_event_ids() == ()  # receiver not called for an empty batch


def test_record_one_terminal_failed_routes_to_terminal_writer(
    ledger: SqliteDeliveryLedger,
    target_a: DeliveryTarget,
) -> None:
    result = DeliveryResult(
        event_id="evt-0",
        outcome=DeliveryOutcome.TERMINAL_FAILED,
        http_status=413,
        error="too large",
    )
    _record_one(ledger, target_a.target_id, result)
    row = ledger.get("evt-0", target_a.target_id)
    assert row is not None
    assert row.status == STATUS_TERMINAL_FAILED
    assert row.last_http_status == 413
    assert row.last_error == "too large"


def test_record_one_non_terminal_forwards_metadata(
    ledger: SqliteDeliveryLedger,
    target_a: DeliveryTarget,
) -> None:
    result = DeliveryResult(
        event_id="evt-0",
        outcome=DeliveryOutcome.REJECTED,
        http_status=400,
        error="bad content",
    )
    _record_one(ledger, target_a.target_id, result)
    row = ledger.get("evt-0", target_a.target_id)
    assert row is not None
    assert row.status == "rejected"
    assert row.last_http_status == 400
    assert row.last_error == "bad content"


def test_decode_payload_parses_json_object() -> None:
    event = _make_event(7)
    decoded = _decode_payload(event)
    assert decoded["event_id"] == "evt-7"
    assert decoded["n"] == 7


def test_decode_payload_wraps_non_json_bytes() -> None:
    event = Event(
        event_id="evt-raw",
        event_type="mission.updated",
        payload=b"\x00\x01not-json",
        occurred_at=_OCCURRED_AT,
        created_at=_OCCURRED_AT,
    )
    decoded = _decode_payload(event)
    assert decoded["event_id"] == "evt-raw"
    assert decoded["event_type"] == "mission.updated"


def test_dispatch_summary_counts_and_recorded() -> None:
    empty = DispatchSummary.empty()
    assert empty.target_id is None
    assert empty.selected == 0
    assert empty.recorded == 0

    counts = dict.fromkeys(DeliveryOutcome, 0)
    counts[DeliveryOutcome.SUCCESS] = 2
    counts[DeliveryOutcome.PENDING] = 1
    summary = DispatchSummary.from_counts("tgt", selected=3, counts=counts)
    assert summary.delivered == 2
    assert summary.pending == 1
    assert summary.recorded == 3


def test_record_exposes_retryable_ids_without_calling_pending_a_failure(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
) -> None:
    """The batch loop can skip every retryable outcome without report drift."""
    for index, event_id in enumerate(("pending", "rejected", "transient", "terminal"), start=4):
        journal.append(
            Event(
                event_id=event_id,
                event_type="mission.updated",
                payload=json.dumps({"event_id": event_id}).encode("utf-8"),
                occurred_at=_OCCURRED_AT,
                created_at=f"2026-06-29T00:00:{index:02d}+00:00",
                project_uuid=_TEST_PROJECT_UUID,
            )
        )
    results = [
        DeliveryResult(event_id="pending", outcome=DeliveryOutcome.PENDING),
        DeliveryResult(event_id="rejected", outcome=DeliveryOutcome.REJECTED),
        DeliveryResult(event_id="transient", outcome=DeliveryOutcome.TRANSIENT),
        DeliveryResult(
            event_id="terminal",
            outcome=DeliveryOutcome.TERMINAL_FAILED,
        ),
    ]

    summary = _record(ledger, "target", results, selected=len(results))

    assert summary.retryable_event_ids == ("pending", "rejected", "transient")
    assert [failure.event_id for failure in summary.failures] == [
        "rejected",
        "transient",
        "terminal",
    ]


def test_multi_batch_drain_skips_pending_head_through_live_dispatcher(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pending rows enter recovery/query state while later rows drain now."""
    with store.unit_of_work() as unit:
        EventJournal(unit, store.layout_generation()).append(_make_event(3))
    receiver = _PendingHeadStub()
    runtime = SimpleNamespace(store=store, journal=None, ledger=None, context=context)
    monkeypatch.setattr(sync_module, "_EVENT_SYNC_DISPATCH_BATCH_LIMIT", 2)

    summary = sync_module._run_dispatch_batches(runtime, receiver, target_a)

    assert receiver.calls == [("evt-0", "evt-1"), ("evt-2", "evt-3")]
    assert summary.selected == 4
    assert summary.pending == 2
    assert summary.delivered == 2
    remaining = _select_with_store(store, target_a.target_id)
    assert [event.event_id for event in remaining.events] == []
    assert _ledger_get(store, "evt-0", target_a.target_id).status == STATUS_PENDING
    assert _ledger_get(store, "evt-1", target_a.target_id).status == STATUS_PENDING


def test_pending_remote_dispatcher_row_is_status_visible_and_not_resent(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receiver = _PendingHeadStub()
    runtime = SimpleNamespace(store=store, context=context)
    monkeypatch.setattr(sync_module, "_EVENT_SYNC_DISPATCH_BATCH_LIMIT", 1)

    first = sync_module._run_dispatch_batches(runtime, receiver, target_a)
    second = sync_module._run_dispatch_batches(runtime, receiver, target_a)

    assert first.pending == 2
    assert second.selected == 0
    assert receiver.calls == [("evt-0",), ("evt-1",), ("evt-2",)]
    row = _ledger_get(store, "evt-0", target_a.target_id)
    assert row.status == STATUS_PENDING
    assert row.server_drain_state == "pending_remote"


def test_retryable_no_effect_reselects_same_attempt_and_native_identity(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
) -> None:
    receiver = _KnownNoEffectOnceStub()

    first = dispatch(store=store, receiver=receiver, target=target_a, context=context, limit=1)
    before = _recoverable_attempts_for_event(store, event_id="evt-0", target_id=target_a.target_id)
    second = dispatch(store=store, receiver=receiver, target=target_a, context=context, limit=1)
    after = _attempt_record(store, before[0][0])

    assert first.rejected == 1
    assert second.delivered == 1
    assert len(before) == 1
    assert after == (before[0][0], before[0][1], "succeeded")
    assert receiver.calls == [("evt-0",), ("evt-0",)]


def test_project_transport_refusal_reports_only_correlated_item(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = [_make_event(0), _make_event(1)]
    captured: list[ProjectTransportDisclosure] = []

    def _refuse_one(
        disclosures: Sequence[ProjectTransportDisclosure],
        **_: Any,
    ) -> ProjectTransportRefusal:
        captured.extend(disclosures)
        return ProjectTransportRefusal(
            project_uuid=_TEST_PROJECT_UUID,
            attempt_id=disclosures[0].attempt_id,
            category="project_not_admitted",
            diagnostic="revoked before send",
        )

    monkeypatch.setattr("specify_cli.delivery.dispatcher.execute_project_transport_batch", _refuse_one)

    results = _post(StubReceiver(), events, granting(), target=target_a, context=context)

    assert len(captured) == 2
    assert [result.event_id for result in results] == ["evt-0"]
    assert results[0].outcome is DeliveryOutcome.TERMINAL_FAILED
    assert "project_not_admitted" in (results[0].error or "")


def test_existing_prepared_attempt_requires_retry_policy_before_start(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
) -> None:
    disclosure = _dispatcher_disclosure_for(_make_event(0), target=target_a, context=context)
    from specify_cli.sync.transport_lease import acquire_project_transport_lease

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, lease_context):
        spec = replace(_attempt_spec(disclosure), reconciliation_policy="operator_review")
        prepare_delivery_attempt(unit, lease_context, spec)

    send_calls = 0

    def _send() -> object:
        nonlocal send_calls
        send_calls += 1
        return {}

    refusal = execute_project_transport_batch(
        [disclosure],
        send=_send,
        classify=lambda _value: {disclosure.attempt_id: ("delivered", None)},
    )

    assert isinstance(refusal, ProjectTransportRefusal)
    assert refusal.category == "delivery_attempt_recovery_required"
    assert send_calls == 0
    assert _attempt_record(store, disclosure.attempt_id)[2] == "prepared"


def test_batch_start_failure_rolls_back_prior_in_flight_transition(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
) -> None:
    first = _dispatcher_disclosure_for(_make_event(0), target=target_a, context=context)
    second = replace(
        _dispatcher_disclosure_for(_make_event(1), target=target_a, context=context),
        deadline_at="2026-08-10T00:00:00+00:00",
    )
    send_calls = 0

    def _send() -> object:
        nonlocal send_calls
        send_calls += 1
        return {}

    refusal = execute_project_transport_batch(
        [first, second],
        send=_send,
        classify=lambda _value: {
            first.attempt_id: ("delivered", None),
            second.attempt_id: ("delivered", None),
        },
    )

    assert isinstance(refusal, ProjectTransportRefusal)
    assert refusal.attempt_id == second.attempt_id
    assert "deadline expired" in refusal.diagnostic
    assert send_calls == 0
    assert _attempt_record(store, first.attempt_id)[2] == "prepared"
    assert _attempt_record(store, second.attempt_id)[2] == "prepared"


def test_server_project_not_admitted_parks_only_correlated_item_durably(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
    target_b: DeliveryTarget,
) -> None:
    receiver = _ProjectNotAdmittedMixedStub()

    first = dispatch(store=store, receiver=receiver, target=target_a, context=context, limit=2)

    refused_row = _ledger_get(store, "evt-0", target_a.target_id)
    succeeded_row = _ledger_get(store, "evt-1", target_a.target_id)
    assert first.selected == 2
    assert first.terminal_failed == 1
    assert first.delivered == 1
    assert refused_row is not None
    assert refused_row.status == STATUS_TERMINAL_FAILED
    assert refused_row.last_error == "project_not_admitted"
    assert succeeded_row is not None
    assert succeeded_row.status == STATUS_SUCCESS

    with store.unit_of_work() as unit:
        refused_attempt = get_delivery_attempt_record(
            unit,
            attempt_id="event:" + stable_transport_id("attempt", _TEST_PROJECT_UUID, target_a.target_id, "evt-0"),
        )
        succeeded_attempt = get_delivery_attempt_record(
            unit,
            attempt_id="event:" + stable_transport_id("attempt", _TEST_PROJECT_UUID, target_a.target_id, "evt-1"),
        )
    assert refused_attempt is not None
    assert refused_attempt.state.value == "refused"
    assert succeeded_attempt is not None
    assert succeeded_attempt.state.value == "succeeded"

    second = dispatch(store=store, receiver=receiver, target=target_a, context=context, limit=2)

    assert second.delivered == 1
    assert receiver.calls == [("evt-0", "evt-1"), ("evt-2",)]

    with store.unit_of_work() as unit:
        attempts_before_reselection = unit.execute(
            "SELECT COUNT(*) FROM delivery_attempts WHERE project_uuid = ?",
            (_TEST_PROJECT_UUID,),
        ).fetchone()[0]
    _admit_target(store, target_b)
    assert [event.event_id for event in _select_with_store(store, target_b.target_id).events] == ["evt-1", "evt-2"]
    with store.unit_of_work() as unit:
        assert (
            unit.execute(
                "SELECT COUNT(*) FROM delivery_attempts WHERE project_uuid = ?",
                (_TEST_PROJECT_UUID,),
            ).fetchone()[0]
            == attempts_before_reselection
        ), "canonical refusal projection must park without writing a legacy attempt"


def test_live_project_refused_response_stays_parked_after_target_switch(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
    target_b: DeliveryTarget,
) -> None:
    """The receiver's complete terminal-policy vocabulary drives ledger parking."""
    posts: list[str] = []

    def _project_refused(
        url: str,
        *,
        data: bytes,
        headers: dict[str, str],
        timeout: float,
    ) -> Any:
        del data, headers, timeout
        posts.append(url)
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "results": [
                    {
                        "event_id": "evt-0",
                        "status": "rejected",
                        "error": "project policy refused this event",
                        "error_category": "project_refused",
                    }
                ]
            },
        )

    receiver = TeamspaceReceiver(
        resolved_server_url=target_a.target_identity,
        auth_token="test-token",
        poster=_project_refused,
    )
    first = dispatch(
        store=store,
        receiver=receiver,
        target=target_a,
        context=context,
        limit=1,
    )
    assert first.terminal_failed == 1
    assert len(posts) == 1
    assert _ledger_get(store, "evt-0", target_a.target_id).last_error == "project_refused"

    with store.unit_of_work() as unit:
        attempts_before_reselection = unit.execute(
            "SELECT COUNT(*) FROM delivery_attempts WHERE project_uuid = ?",
            (_TEST_PROJECT_UUID,),
        ).fetchone()[0]
    _admit_target(store, target_b)
    with store.unit_of_work() as unit:
        assert (
            SqliteDeliveryLedger(unit, store.layout_generation()).select_undelivered(
                target_id=target_b.target_id,
                event_universe=("evt-0",),
            )
            == []
        )
        assert (
            unit.execute(
                "SELECT COUNT(*) FROM delivery_attempts WHERE project_uuid = ?",
                (_TEST_PROJECT_UUID,),
            ).fetchone()[0]
            == attempts_before_reselection
        ), "target-switch projection must not create a legacy attempt"


def test_cli_loop_skips_expired_prepared_head_for_current_pass_and_continues(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expired = replace(
        _dispatcher_disclosure_for(_make_event(0), target=target_a, context=context),
        deadline_at="2026-08-10T00:00:00+00:00",
    )
    first_refusal = execute_project_transport_batch(
        [expired],
        send=lambda: pytest.fail("expired preparation must not send"),
        classify=lambda _value: {expired.attempt_id: ("delivered", None)},
    )
    assert isinstance(first_refusal, ProjectTransportRefusal)
    assert _attempt_record(store, expired.attempt_id)[2] == "prepared"

    receiver = StubReceiver()
    runtime = SimpleNamespace(store=store, context=context)
    monkeypatch.setattr(sync_module, "_EVENT_SYNC_DISPATCH_BATCH_LIMIT", 1)

    summary = sync_module._run_dispatch_batches(runtime, receiver, target_a)

    assert summary.terminal_failed == 1
    assert summary.delivered == 2
    assert receiver.received_event_ids() == ("evt-1", "evt-2")
    assert _ledger_get(store, "evt-0", target_a.target_id).status == "failed_transient"


def test_multi_batch_drain_continues_after_singleton_terminal_failure(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Canonical 413 halving parks one event, then drains the success tail.

    After the oversized head (evt-0) is halved to a singleton and parked as
    terminal_failed, the limit grows back (1 -> 2), so the healthy tail
    (evt-1, evt-2) drains in one grown batch rather than one-event-per-POST.
    The grow-back is the throughput-cliff fix; the old behavior emitted
    ``("evt-1",), ("evt-2",)`` as separate singleton calls.
    """
    receiver = _AdaptiveOversizedStub()
    runtime = SimpleNamespace(store=store, journal=None, ledger=None, context=context)
    monkeypatch.setattr(sync_module, "_EVENT_SYNC_DISPATCH_BATCH_LIMIT", 2)

    summary = sync_module._run_dispatch_batches(runtime, receiver, target_a)

    assert receiver.calls == [
        ("evt-0", "evt-1"),
        ("evt-0",),
        ("evt-1", "evt-2"),
    ]
    assert summary.selected == 3
    assert summary.terminal_failed == 1
    assert summary.delivered == 2
    assert _select_with_store(store, target_a.target_id).events == []


def test_expired_attempt_refusal_is_recovery_required_not_project_not_admitted(
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
) -> None:
    """Deadline/recovery failures are not mislabeled as admission refusals."""
    disclosure = ProjectTransportDisclosure(
        project_uuid=_TEST_PROJECT_UUID,
        epoch_id=context.epoch_id or 0,
        consent_generation=context.consent_generation or 0,
        target_identity=target_a.target_identity,
        account_identity=target_a.account_identity,
        private_teamspace_id=target_a.private_teamspace_id,
        target_project_uuid=target_a.project_uuid.storage_token,
        target_generation=target_a.configuration_generation,
        admission_generation=str(target_a.admission_generation),
        binding_audience=str(target_a.binding_audience),
        write_kind="dispatcher_http_event",
        native_identity=f"dispatcher-http:{target_a.target_id}:expired",
        payload_hash="sha256:expired",
        payload_reference=_dispatcher_payload_reference("expired", target_a.target_id),
        attempt_id="dispatcher-http:expired",
        deadline_at="2026-08-10T00:00:00Z",
        reconciliation_policy="native_identity_retry",
    )

    result = execute_project_transport_batch(
        [disclosure],
        send=lambda: pytest.fail("expired attempt must not send"),
        classify=lambda _value: {},
    )

    assert isinstance(result, ProjectTransportRefusal)
    assert result.category == "delivery_attempt_recovery_required"
    assert "deadline expired" in result.diagnostic


# --------------------------------------------------------------------------- #
# D-020 coalescing carry — install(ledger) on the live dispatch path (FR-011) #
# --------------------------------------------------------------------------- #


def test_install_coalescing_invokes_install_with_ledger(
    ledger: SqliteDeliveryLedger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeCoalesce()
    monkeypatch.setattr("specify_cli.delivery.dispatcher._load_coalesce", lambda: fake)
    assert _install_coalescing(ledger) is True
    assert fake.installed_with is ledger


def test_install_coalescing_degrades_when_module_absent(
    ledger: SqliteDeliveryLedger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _missing() -> Any:
        raise ModuleNotFoundError("no coalesce module in this lane")

    monkeypatch.setattr("specify_cli.delivery.dispatcher._load_coalesce", _missing)
    # The drain must not break when WP08's coalesce module is not yet merged.
    assert _install_coalescing(ledger) is False


def test_dispatch_activates_coalescing_on_live_path(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeCoalesce()
    monkeypatch.setattr("specify_cli.delivery.dispatcher._load_coalesce", lambda: fake)
    stub = StubReceiver()

    dispatch(store=store, receiver=stub, target=target_a, context=context)

    # The live dispatch path registered the real coalescing strategy bound to the
    # delivery ledger (D-020): without this, FR-011 coalescing is dead in production.
    assert isinstance(fake.installed_with, SqliteDeliveryLedger)
    assert fake.installed_with.project_uuid == _TEST_PROJECT_UUID


# -- HTTP 412 protocol skew halts the pass and parks nothing (#1553) ------------


def test_protocol_mismatch_412_halts_pass_after_first_post_and_parks_nothing(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One 412 -> one POST; the rest of the journal is never sent, no row is terminal."""
    receiver = _ProtocolMismatchStub()
    runtime = SimpleNamespace(store=store, journal=None, ledger=None, context=context)
    monkeypatch.setattr(sync_module, "_EVENT_SYNC_DISPATCH_BATCH_LIMIT", 1)

    summary = sync_module._run_dispatch_batches(runtime, receiver, target_a)

    # Halted after the FIRST POST: evt-1 / evt-2 were never attempted this pass.
    assert receiver.calls == [("evt-0",)]
    assert summary.selected == 1
    assert summary.transient == 1
    assert summary.terminal_failed == 0
    assert summary.delivered == 0
    # The one attempted row is retained as retryable, never parked.
    assert _ledger_get(store, "evt-0", target_a.target_id).status == "failed_transient"
    assert _ledger_get(store, "evt-1", target_a.target_id) is None
    assert _ledger_get(store, "evt-2", target_a.target_id) is None
    # The server's guidance rides the failure record for the command to print.
    assert [f.error for f in summary.failures] == ["Run `spec-kitty upgrade` to update to a supported release."]


def test_protocol_mismatch_412_events_are_reselected_and_deliver_after_skew_clears(
    store: ProjectSyncStore,
    context: ProjectSyncContext,
    target_a: DeliveryTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The next ``sync now`` (CLI/server now agree) drains everything the 412 halted."""
    runtime = SimpleNamespace(store=store, journal=None, ledger=None, context=context)
    monkeypatch.setattr(sync_module, "_EVENT_SYNC_DISPATCH_BATCH_LIMIT", 2)

    halted = sync_module._run_dispatch_batches(runtime, _ProtocolMismatchStub(), target_a)
    assert halted.transient == 2
    assert halted.terminal_failed == 0
    # Everything is still selectable for the next pass (nothing terminal/parked).
    remaining = _select_with_store(store, target_a.target_id)
    assert sorted(event.event_id for event in remaining.events) == ["evt-0", "evt-1", "evt-2"]

    healed = StubReceiver()
    drained = sync_module._run_dispatch_batches(runtime, healed, target_a)

    assert drained.delivered == 3
    assert drained.terminal_failed == 0
    assert set(healed.received_event_ids()) == {"evt-0", "evt-1", "evt-2"}
    for event_id in ("evt-0", "evt-1", "evt-2"):
        assert _ledger_get(store, event_id, target_a.target_id).status == STATUS_SUCCESS
