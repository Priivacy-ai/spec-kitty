"""Reusable A/B evidence harness for the per-project sync consent incident.

WP01 provides probes, deterministic barriers, differential counters, and
synthetic mutations.  Later work packages import these helpers while replacing
the shared-store implementation; this module does not change production paths.
"""

from __future__ import annotations

import ast
import gzip
import json
import multiprocessing
import sqlite3
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, cast

import pytest

from specify_cli.delivery.consent_gate import consented_batch, resolve_consent_answer
from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.receivers import OutboundEvent, TeamspaceReceiver
from specify_cli.event_journal import Event, EventJournal, resolve_journal_path

pytestmark = [pytest.mark.fast]

UUID_A = "aaaaaaaa-0000-0000-0000-000000000001"
UUID_B = "bbbbbbbb-0000-0000-0000-000000000002"


@dataclass(frozen=True)
class IncidentProject:
    uuid: str
    slug: str
    root: Path

    def planned_store_path(self, state_root: Path) -> Path:
        """The canonical path shape that WP02 will implement."""
        return state_root / "projects" / self.uuid / "sync" / "sync.db"

    def planned_egress_lock_path(self, state_root: Path) -> Path:
        """The store sibling serialized around final transport/cutover."""
        return state_root / "projects" / self.uuid / "sync" / "egress.lock"


@dataclass(frozen=True)
class IncidentPair:
    a: IncidentProject
    b: IncidentProject

    @classmethod
    def same_slug_distinct_uuid(cls, tmp_path: Path) -> IncidentPair:
        return cls(
            IncidentProject(UUID_A, "same-slug", tmp_path / "checkout-a"),
            IncidentProject(UUID_B, "same-slug", tmp_path / "checkout-b"),
        )


class SqliteOpenSpy:
    """Record normalized sqlite targets while delegating to the real driver."""

    def __init__(self) -> None:
        self.targets: list[str] = []
        self._real_connect = cast(Callable[..., sqlite3.Connection], sqlite3.connect)

    def connect(self, database: Any, *args: Any, **kwargs: Any) -> sqlite3.Connection:
        self.targets.append(str(database))
        return self._real_connect(database, *args, **kwargs)

    @contextmanager
    def installed(self, monkeypatch: pytest.MonkeyPatch) -> Iterator[SqliteOpenSpy]:
        monkeypatch.setattr(sqlite3, "connect", self.connect)
        yield self


@dataclass(frozen=True)
class _TransportResponse:
    event_ids: tuple[str, ...]
    status_code: int = 200

    def json(self) -> Mapping[str, object]:
        return {"results": [{"event_id": event_id, "status": "success"} for event_id in self.event_ids]}


@dataclass
class ExactByteTransportSpy:
    """Capture the byte sequence handed to an injected HTTP/WS transport."""

    bodies: list[bytes] = field(default_factory=list)
    event_ids: tuple[str, ...] = ()

    def __call__(
        self,
        _url: str,
        *,
        data: bytes,
        headers: Mapping[str, str],
        timeout: float,
    ) -> _TransportResponse:
        assert headers["Content-Encoding"] == "gzip"
        assert timeout > 0
        self.bodies.append(bytes(data))
        return _TransportResponse(self.event_ids)

    async def send(self, data: bytes | str) -> None:
        self.bodies.append(data.encode() if isinstance(data, str) else bytes(data))


@dataclass
class DifferentialCounter:
    """Count project-labelled operations without hiding the non-target delta."""

    counts: Counter[str] = field(default_factory=Counter)

    def increment(self, project_uuid: str, amount: int = 1) -> None:
        self.counts[project_uuid] += amount

    def snapshot(self) -> dict[str, int]:
        return dict(self.counts)

    def delta(self, before: dict[str, int], project_uuid: str) -> int:
        return self.counts[project_uuid] - before.get(project_uuid, 0)

    def observe_ledger(
        self,
        ledger: SqliteDeliveryLedger,
        project_pairs: Mapping[str, Sequence[tuple[str, str]]],
    ) -> None:
        """Replace counts from the production ledger's public result-read seam."""
        self.counts.clear()
        for project_uuid, pairs in project_pairs.items():
            self.counts[project_uuid] = sum(ledger.get(event_id, target_id) is not None for event_id, target_id in pairs)


class CrossProcessBarrier:
    """Two-event barrier safe to pass to a spawned worker process."""

    def __init__(self, context: multiprocessing.context.BaseContext) -> None:
        self.arrived = context.Event()
        self.released = context.Event()

    def worker_pause(self, timeout: float = 5.0) -> None:
        self.arrived.set()
        if not self.released.wait(timeout):
            raise TimeoutError("controller did not release cross-process barrier")

    def wait_for_worker(self, timeout: float = 5.0) -> None:
        if not self.arrived.wait(timeout):
            raise TimeoutError("worker did not reach cross-process barrier")

    def release(self) -> None:
        self.released.set()


class _PutQueue(Protocol):
    def put(self, value: str) -> None: ...


def _barrier_worker(barrier: CrossProcessBarrier, result: _PutQueue) -> None:
    barrier.worker_pause()
    result.put("released")


class MutantKind(StrEnum):
    SHARED_JOURNAL_RESOLVER = "shared-journal-resolver"
    ENVIRONMENT_AS_GRANT = "environment-as-grant"
    MISSING_FINAL_TRANSPORT_GATE = "missing-final-transport-gate"
    CROSS_PAIR_CONTEXT = "cross-pair-context"


@dataclass(frozen=True)
class MutationSpecimen:
    name: str
    kind: MutantKind
    source: str


def _call_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    return names


def mutation_violations(specimen: MutationSpecimen) -> tuple[str, ...]:
    """Return the violated boundary for one in-memory synthetic implementation."""
    tree = ast.parse(specimen.source)
    text = ast.unparse(tree)
    if specimen.kind is MutantKind.SHARED_JOURNAL_RESOLVER:
        uses_uuid = any(isinstance(node, ast.Name) and node.id in {"project_uuid", "uuid"} for node in ast.walk(tree))
        return () if uses_uuid and "sync.db" in text else (specimen.kind.value,)
    if specimen.kind is MutantKind.ENVIRONMENT_AS_GRANT:
        environment = "getenv" in text or "environ" in text
        grants = any(
            isinstance(node, ast.Return)
            and node.value is not None
            and any(isinstance(value, ast.Constant) and value.value is True for value in ast.walk(node.value))
            for node in ast.walk(tree)
        )
        return (specimen.kind.value,) if environment and grants else ()
    if specimen.kind is MutantKind.MISSING_FINAL_TRANSPORT_GATE:
        calls = _call_names(tree)
        transmits = bool(calls & {"post", "send", "deliver"})
        final_gate = "final_transport_eligible" in calls
        return (specimen.kind.value,) if transmits and not final_gate else ()
    if specimen.kind is MutantKind.CROSS_PAIR_CONTEXT:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            values = {kw.arg: ast.unparse(kw.value) for kw in node.keywords if kw.arg in {"journal_uuid", "target_uuid", "ledger_uuid"}}
            if len(set(values.values())) > 1:
                return (specimen.kind.value,)
        return ()
    raise AssertionError(f"unhandled mutant kind: {specimen.kind}")


def assert_context_coherent(*, journal_uuid: str, target_uuid: str, ledger_uuid: str) -> None:
    assert len({journal_uuid, target_uuid, ledger_uuid}) == 1, "journal, target, and ledger must belong to one project UUID"


def test_same_slug_projects_resolve_to_distinct_uuid_store_paths(tmp_path: Path) -> None:
    pair = IncidentPair.same_slug_distinct_uuid(tmp_path)
    state_root = tmp_path / "state"
    assert pair.a.slug == pair.b.slug
    assert pair.a.uuid != pair.b.uuid
    assert pair.a.planned_store_path(state_root) == (state_root / "projects" / UUID_A / "sync" / "sync.db")
    assert pair.b.planned_store_path(state_root) == (state_root / "projects" / UUID_B / "sync" / "sync.db")
    assert pair.a.planned_egress_lock_path(state_root) == (pair.a.planned_store_path(state_root).with_name("egress.lock"))
    assert pair.b.planned_egress_lock_path(state_root) == (pair.b.planned_store_path(state_root).with_name("egress.lock"))


def test_spies_and_counter_observe_current_production_write_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_home = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime_home))
    journal_path = resolve_journal_path(user_id="operator", team_slug="team")
    event = Event(
        event_id="event-a-current-write",
        event_type="WPStatusChanged",
        payload=json.dumps(
            {
                "event_id": "event-a-current-write",
                "project_uuid": UUID_A,
                "payload": {"wp_id": "WP01"},
            }
        ).encode(),
        occurred_at="2026-08-09T12:00:00+00:00",
        created_at="2026-08-09T12:00:01+00:00",
        project_uuid=UUID_A,
        project_slug="same-slug",
    )
    open_spy = SqliteOpenSpy()
    with open_spy.installed(monkeypatch):
        journal = EventJournal(journal_path)
        journal.append(event)
    assert journal.count() == 1
    assert open_spy.targets
    assert set(open_spy.targets) == {str(journal_path)}

    wire_payload = {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "project_uuid": UUID_A,
    }
    outbound = OutboundEvent(event_id=event.event_id, payload=wire_payload)
    answer = resolve_consent_answer(
        [UUID_A],
        consent_predicate=lambda candidates: frozenset(str(candidate) for candidate in candidates if candidate),
    )
    batch = consented_batch(
        [outbound],
        answer=answer,
        event_projects={event.event_id: UUID_A},
    )
    byte_spy = ExactByteTransportSpy(event_ids=(event.event_id,))
    receiver = TeamspaceReceiver(
        resolved_server_url="https://app.spec-kitty.ai",
        auth_token="test-token",
        poster=byte_spy,
    )
    results = receiver.deliver(batch)
    assert [result.event_id for result in results] == [event.event_id]
    assert len(byte_spy.bodies) == 1
    assert gzip.decompress(byte_spy.bodies[0]) == json.dumps({"events": [wire_payload]}).encode()

    ledger = SqliteDeliveryLedger(str(tmp_path / "result-ledger.db"))
    target_id = "target-a"
    ledger.record_success("event-a-before", target_id)
    ledger.record_success("event-b-before", target_id)
    counter = DifferentialCounter()
    pairs = {
        UUID_A: (("event-a-before", target_id), ("event-a-after", target_id)),
        UUID_B: (("event-b-before", target_id), ("event-b-after", target_id)),
    }
    counter.observe_ledger(ledger, pairs)
    before = counter.snapshot()
    ledger.record_success("event-a-after", target_id)
    counter.observe_ledger(ledger, pairs)
    assert counter.delta(before, UUID_A) == 1
    assert counter.delta(before, UUID_B) == 0
    ledger.close()


def test_cross_process_barrier_releases_only_after_controller_signal() -> None:
    context = multiprocessing.get_context("spawn")
    barrier = CrossProcessBarrier(context)
    result = context.Queue()
    worker = context.Process(target=_barrier_worker, args=(barrier, result))
    worker.start()
    try:
        barrier.wait_for_worker()
        assert result.empty()
        barrier.release()
        assert result.get(timeout=5.0) == "released"
    finally:
        worker.join(timeout=5.0)
        if worker.is_alive():
            worker.terminate()
            worker.join(timeout=5.0)
    assert worker.exitcode == 0


@pytest.mark.parametrize(
    ("clean", "mutant"),
    [
        (
            MutationSpecimen(
                "uuid store",
                MutantKind.SHARED_JOURNAL_RESOLVER,
                "def path(root, project_uuid): return root / project_uuid / 'sync.db'",
            ),
            MutationSpecimen(
                "shared journal",
                MutantKind.SHARED_JOURNAL_RESOLVER,
                "def path(root, project_uuid): return root / 'journal.db'",
            ),
        ),
        (
            MutationSpecimen(
                "env arms only",
                MutantKind.ENVIRONMENT_AS_GRANT,
                "def decide(): return explicit_decision() if os.getenv('ARMED') else False",
            ),
            MutationSpecimen(
                "env grants",
                MutantKind.ENVIRONMENT_AS_GRANT,
                "def decide(): return True if os.getenv('ARMED') else False",
            ),
        ),
        (
            MutationSpecimen(
                "final gate",
                MutantKind.MISSING_FINAL_TRANSPORT_GATE,
                "def send(client, body):\n if final_transport_eligible(body): client.post(body)",
            ),
            MutationSpecimen(
                "gate removed",
                MutantKind.MISSING_FINAL_TRANSPORT_GATE,
                "def send(client, body): client.post(body)",
            ),
        ),
        (
            MutationSpecimen(
                "coherent attempt",
                MutantKind.CROSS_PAIR_CONTEXT,
                "attempt = DeliveryAttempt(journal_uuid=a.uuid, target_uuid=a.uuid, ledger_uuid=a.uuid)",
            ),
            MutationSpecimen(
                "cross-paired attempt",
                MutantKind.CROSS_PAIR_CONTEXT,
                "attempt = DeliveryAttempt(journal_uuid=a.uuid, target_uuid=b.uuid, ledger_uuid=a.uuid)",
            ),
        ),
    ],
    ids=lambda specimen: specimen.name,
)
def test_mutation_runner_accepts_clean_and_rejects_synthetic_mutants(
    clean: MutationSpecimen,
    mutant: MutationSpecimen,
) -> None:
    assert mutation_violations(clean) == ()
    assert mutation_violations(mutant) == (mutant.kind.value,)


def test_cross_pair_context_assertion_has_same_project_positive_control() -> None:
    assert_context_coherent(journal_uuid=UUID_A, target_uuid=UUID_A, ledger_uuid=UUID_A)
    with pytest.raises(AssertionError, match="one project UUID"):
        assert_context_coherent(journal_uuid=UUID_A, target_uuid=UUID_B, ledger_uuid=UUID_A)
