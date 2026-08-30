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
from specify_cli.event_journal import Event, EventJournal
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

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
        ledgers: Mapping[str, SqliteDeliveryLedger],
        project_pairs: Mapping[str, Sequence[tuple[str, str]]],
    ) -> None:
        """Read each isolated store through the production result-read seam."""
        self.counts.clear()
        for project_uuid, pairs in project_pairs.items():
            ledger = ledgers[project_uuid]
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


def _call_tail(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _expression_names(node: ast.AST) -> frozenset[str]:
    return frozenset(child.id for child in ast.walk(node) if isinstance(child, ast.Name))


def _transmitted_expression(call: ast.Call) -> ast.expr | None:
    for keyword in call.keywords:
        if keyword.arg in {"json", "data", "content", "body", "payload", "event"}:
            return keyword.value
    return call.args[-1] if call.args else None


def _guarded_transport_is_coherent(tree: ast.Module) -> bool:
    """Require the eligibility result to dominate a sink carrying the checked data."""
    sink_names = {"post", "send", "deliver"}

    def check_block(statements: list[ast.stmt], eligible: frozenset[str]) -> bool:
        current = eligible
        for statement in statements:
            if isinstance(statement, ast.If):
                if isinstance(statement.test, ast.UnaryOp) and isinstance(
                    statement.test.op,
                    ast.Not,
                ):
                    inverted = True
                    candidate = statement.test.operand
                else:
                    inverted = False
                    candidate = statement.test
                if isinstance(candidate, ast.Call) and _call_tail(candidate) == "final_transport_eligible":
                    checked = frozenset(
                        name
                        for argument in (
                            *candidate.args,
                            *(keyword.value for keyword in candidate.keywords),
                        )
                        for name in _expression_names(argument)
                    )
                    if (
                        inverted
                        and statement.body
                        and isinstance(
                            statement.body[-1],
                            (ast.Return, ast.Raise),
                        )
                    ):
                        if not check_block(statement.body, current):
                            return False
                        current |= checked
                    elif not inverted:
                        if not check_block(statement.body, current | checked):
                            return False
                    if not check_block(statement.orelse, current):
                        return False
                    continue
            for call in (node for node in ast.walk(statement) if isinstance(node, ast.Call)):
                if _call_tail(call) not in sink_names:
                    continue
                transmitted = _transmitted_expression(call)
                payload_names = _expression_names(transmitted) if transmitted is not None else frozenset()
                if not current & payload_names:
                    return False
        return True

    functions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    return all(check_block(function.body, frozenset()) for function in functions)


def _canonical_resolver_is_coherent(tree: ast.Module) -> bool:
    def path_components(node: ast.expr) -> list[ast.expr]:
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return [*path_components(node.left), *path_components(node.right)]
        return [node]

    def direct_uuid_component(node: ast.expr) -> bool:
        if isinstance(node, ast.Name):
            return node.id in {"project_uuid", "uuid"}
        if isinstance(node, ast.Attribute):
            return node.attr in {"project_uuid", "uuid"}
        if isinstance(node, ast.Call) and _call_tail(node) in {
            "UUID",
            "normalize_project_uuid",
            "str",
        }:
            return len(node.args) == 1 and direct_uuid_component(node.args[0])
        return False

    for node in ast.walk(tree):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        components = path_components(node.value)
        rendered = [ast.unparse(component).strip("'\"") for component in components]
        uuid_positions = [index for index, component in enumerate(components) if direct_uuid_component(component)]
        for uuid_index in uuid_positions:
            prefix = rendered[:uuid_index]
            suffix = rendered[uuid_index + 1 :]
            if "projects" in prefix and len(suffix) >= 2 and suffix[0] == "sync" and suffix[1] == "sync.db":
                return True
    return False


def _stable_identity(
    node: ast.expr,
    mutated_attributes: frozenset[str] = frozenset(),
) -> str | None:
    if isinstance(node, ast.Constant):
        return ast.dump(node, include_attributes=False)
    if isinstance(node, ast.Attribute) and node.attr in {"project_uuid", "uuid"}:
        rendered = ast.dump(node, include_attributes=False)
        return None if ast.unparse(node) in mutated_attributes else rendered
    if (
        isinstance(node, ast.Call)
        and _call_tail(node) in {"UUID", "normalize_project_uuid", "str"}
        and len(node.args) == 1
        and _stable_identity(node.args[0], mutated_attributes) is not None
    ):
        return ast.dump(node, include_attributes=False)
    return None


def _attempt_context_is_coherent(tree: ast.Module) -> bool:
    # TODO(#3280): Track setattr/__dict__/tuple mutations and their ordering; direct attribute mutation is only bounded evidence.
    mutated_attributes = frozenset(
        ast.unparse(target)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
        for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        if isinstance(target, ast.Attribute) and target.attr in {"project_uuid", "uuid"}
    )
    contexts: dict[str, str] = {}
    assignments: Counter[str] = Counter()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        assignments[target.id] += 1
        if not isinstance(node.value, ast.Call) or _call_tail(node.value) != "ProjectSyncContext":
            continue
        project_value = next(
            (keyword.value for keyword in node.value.keywords if keyword.arg == "project_uuid"),
            node.value.args[0] if node.value.args else None,
        )
        if project_value is not None:
            stable = _stable_identity(project_value, mutated_attributes)
            if stable is not None:
                contexts[target.id] = stable
    attempts = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and _call_tail(node) == "DeliveryAttempt"]
    if not attempts:
        return False
    for attempt in attempts:
        values = {keyword.arg: keyword.value for keyword in attempt.keywords if keyword.arg in {"context", "journal_uuid", "target_uuid", "ledger_uuid"}}
        context_node = values.get("context")
        if not isinstance(context_node, ast.Name) or assignments[context_node.id] != 1:
            return False
        expected = contexts.get(context_node.id)
        paired = [_stable_identity(values[field], mutated_attributes) for field in ("journal_uuid", "target_uuid", "ledger_uuid") if field in values]
        if expected is None or len(paired) != 3 or any(value != expected for value in paired):
            return False
    return True


def mutation_violations(specimen: MutationSpecimen) -> tuple[str, ...]:
    """Return the violated boundary for one in-memory synthetic implementation."""
    tree = ast.parse(specimen.source)
    text = ast.unparse(tree)
    if specimen.kind is MutantKind.SHARED_JOURNAL_RESOLVER:
        return () if _canonical_resolver_is_coherent(tree) else (specimen.kind.value,)
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
        transmits = any(isinstance(node, ast.Call) and _call_tail(node) in {"post", "send", "deliver"} for node in ast.walk(tree))
        return (specimen.kind.value,) if transmits and not _guarded_transport_is_coherent(tree) else ()
    if specimen.kind is MutantKind.CROSS_PAIR_CONTEXT:
        return () if _attempt_context_is_coherent(tree) else (specimen.kind.value,)
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
    store_a = ProjectSyncStore(UUID_A)
    store_b = ProjectSyncStore(UUID_B)
    authority_a = store_a.layout_generation()
    authority_a.begin_cutover("incident-spy")
    authority_a.publish_project_only("incident-spy", verify_exact=lambda: True)
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
    with open_spy.installed(monkeypatch), store_a.unit_of_work() as unit_a:
        journal = EventJournal(unit_a, authority_a)
        journal.append(event)
        journal_count = journal.count()
    assert journal_count == 1
    assert open_spy.targets
    assert set(open_spy.targets) == {str(store_a.database_path)}

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
    assert gzip.decompress(byte_spy.bodies[0]) == json.dumps(
        {"events": [wire_payload]},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    target_id = "target-a"
    event_ids = {
        UUID_A: ("event-a-before", "event-a-after"),
        UUID_B: ("event-b-before", "event-b-after"),
    }
    for store, project_uuid in ((store_a, UUID_A), (store_b, UUID_B)):
        with store.unit_of_work() as unit:
            journal = EventJournal(unit, store.layout_generation())
            for event_id in event_ids[project_uuid]:
                journal.append(
                    Event(
                        event_id=event_id,
                        event_type="WPStatusChanged",
                        payload=json.dumps(
                            {
                                "event_id": event_id,
                                "project_uuid": project_uuid,
                                "payload": {"wp_id": "WP01"},
                            }
                        ).encode(),
                        occurred_at="2026-08-09T12:00:00+00:00",
                        created_at="2026-08-09T12:00:01+00:00",
                        project_uuid=project_uuid,
                        project_slug="same-slug",
                    )
                )
            SqliteDeliveryLedger(unit, store.layout_generation()).record_success(
                event_ids[project_uuid][0],
                target_id,
            )

    counter = DifferentialCounter()
    pairs = {
        UUID_A: (("event-a-before", target_id), ("event-a-after", target_id)),
        UUID_B: (("event-b-before", target_id), ("event-b-after", target_id)),
    }
    with store_a.unit_of_work() as unit_a, store_b.unit_of_work() as unit_b:
        counter.observe_ledger(
            {
                UUID_A: SqliteDeliveryLedger(unit_a, store_a.layout_generation()),
                UUID_B: SqliteDeliveryLedger(unit_b, store_b.layout_generation()),
            },
            pairs,
        )
    before = counter.snapshot()
    store_b_before = store_b.database_path.read_bytes()
    open_spy.targets.clear()
    with open_spy.installed(monkeypatch), store_a.unit_of_work() as unit_a:
        SqliteDeliveryLedger(unit_a, store_a.layout_generation()).record_success(
            "event-a-after",
            target_id,
        )
    assert set(open_spy.targets) == {str(store_a.database_path)}
    assert store_b.database_path.read_bytes() == store_b_before
    with store_a.unit_of_work() as unit_a, store_b.unit_of_work() as unit_b:
        counter.observe_ledger(
            {
                UUID_A: SqliteDeliveryLedger(unit_a, store_a.layout_generation()),
                UUID_B: SqliteDeliveryLedger(unit_b, store_b.layout_generation()),
            },
            pairs,
        )
    assert counter.delta(before, UUID_A) == 1
    assert counter.delta(before, UUID_B) == 0


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
                "def path(root, project_uuid): return root / 'projects' / project_uuid / 'sync' / 'sync.db'",
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
                "context = ProjectSyncContext(project_uuid=a.uuid)\n"
                "attempt = DeliveryAttempt(context=context, journal_uuid=a.uuid, target_uuid=a.uuid, ledger_uuid=a.uuid)",
            ),
            MutationSpecimen(
                "cross-paired attempt",
                MutantKind.CROSS_PAIR_CONTEXT,
                "context = ProjectSyncContext(project_uuid=a.uuid)\n"
                "attempt = DeliveryAttempt(context=context, journal_uuid=a.uuid, target_uuid=b.uuid, ledger_uuid=a.uuid)",
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


@pytest.mark.parametrize(
    "mutant",
    [
        MutationSpecimen(
            "uuid decoy",
            MutantKind.SHARED_JOURNAL_RESOLVER,
            "def path(root, project_uuid):\n    audit(project_uuid)\n    return root / 'sync.db'\n",
        ),
        MutationSpecimen(
            "ignored final result",
            MutantKind.MISSING_FINAL_TRANSPORT_GATE,
            "def send(client, body):\n    final_transport_eligible(body)\n    client.post(body)\n",
        ),
        MutationSpecimen(
            "unrelated coherent decoy",
            MutantKind.CROSS_PAIR_CONTEXT,
            "decoy = ProjectSyncContext(project_uuid=a.uuid)\n"
            "context = ProjectSyncContext(project_uuid=b.uuid)\n"
            "attempt = DeliveryAttempt(context=context, journal_uuid=a.uuid, target_uuid=a.uuid, ledger_uuid=a.uuid)\n",
        ),
        MutationSpecimen(
            "uuid tuple decoy",
            MutantKind.SHARED_JOURNAL_RESOLVER,
            "def path(root, project_uuid):\n    return root / 'projects' / (audit(project_uuid), 'shared')[1] / 'sync' / 'sync.db'\n",
        ),
        MutationSpecimen(
            "foreign body audit header",
            MutantKind.MISSING_FINAL_TRANSPORT_GATE,
            "def send(client, body, foreign):\n"
            "    if final_transport_eligible(body):\n"
            "        client.post('/events', json=foreign, headers={'X-Audit': str(body)})\n",
        ),
        MutationSpecimen(
            "rebound project identity",
            MutantKind.CROSS_PAIR_CONTEXT,
            "project = a.uuid\n"
            "context = ProjectSyncContext(project_uuid=project)\n"
            "project = b.uuid\n"
            "attempt = DeliveryAttempt(context=context, journal_uuid=project, target_uuid=project, ledger_uuid=project)\n",
        ),
        MutationSpecimen(
            "rebound attribute identity",
            MutantKind.CROSS_PAIR_CONTEXT,
            "context = ProjectSyncContext(project_uuid=a.uuid)\n"
            "a.uuid = b.uuid\n"
            "attempt = DeliveryAttempt(context=context, journal_uuid=a.uuid, target_uuid=a.uuid, ledger_uuid=a.uuid)\n",
        ),
    ],
    ids=lambda specimen: specimen.name,
)
def test_mutation_runner_rejects_incidental_boundary_vocabulary(
    mutant: MutationSpecimen,
) -> None:
    assert mutation_violations(mutant) == (mutant.kind.value,)


def test_cross_pair_context_assertion_has_same_project_positive_control() -> None:
    assert_context_coherent(journal_uuid=UUID_A, target_uuid=UUID_A, ledger_uuid=UUID_A)
    with pytest.raises(AssertionError, match="one project UUID"):
        assert_context_coherent(journal_uuid=UUID_A, target_uuid=UUID_B, ledger_uuid=UUID_A)
