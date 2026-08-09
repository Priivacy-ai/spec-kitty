"""Reusable A/B evidence harness for the per-project sync consent incident.

WP01 provides probes, deterministic barriers, differential counters, and
synthetic mutations.  Later work packages import these helpers while replacing
the shared-store implementation; this module does not change production paths.
"""

from __future__ import annotations

import ast
import multiprocessing
import sqlite3
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import pytest

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
        return state_root / "projects" / self.uuid / "sync.db"


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
        self._real_connect = sqlite3.connect

    def connect(self, database: Any, *args: Any, **kwargs: Any) -> sqlite3.Connection:
        self.targets.append(str(database))
        return self._real_connect(database, *args, **kwargs)

    @contextmanager
    def installed(self, monkeypatch: pytest.MonkeyPatch) -> Iterator[SqliteOpenSpy]:
        monkeypatch.setattr(sqlite3, "connect", self.connect)
        yield self


@dataclass
class ExactByteTransportSpy:
    """Capture the byte sequence handed to an injected HTTP/WS transport."""

    bodies: list[bytes] = field(default_factory=list)

    def __call__(self, _url: str, *, data: bytes, **_kwargs: Any) -> object:
        self.bodies.append(bytes(data))
        return type("Response", (), {"status_code": 200, "json": lambda _self: {}})()

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


def _barrier_worker(barrier: CrossProcessBarrier, result: Any) -> None:
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
            isinstance(node, ast.Return) and any(isinstance(value, ast.Constant) and value.value is True for value in ast.walk(node.value))
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
    assert pair.a.planned_store_path(state_root) != pair.b.planned_store_path(state_root)


def test_store_open_and_exact_byte_spies_have_same_path_positive_controls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "same.db"
    open_spy = SqliteOpenSpy()
    with open_spy.installed(monkeypatch):
        sqlite3.connect(db).close()
        sqlite3.connect(db).close()
    assert open_spy.targets == [str(db), str(db)]

    body = b'{"project_uuid":"same-project","event_id":"01"}'
    byte_spy = ExactByteTransportSpy()
    byte_spy("https://example.invalid/events", data=body)
    byte_spy("https://example.invalid/events", data=body)
    assert byte_spy.bodies == [body, body]


def test_differential_counter_exposes_other_project_changes() -> None:
    counter = DifferentialCounter()
    counter.increment(UUID_A, 2)
    counter.increment(UUID_B, 3)
    before = counter.snapshot()
    counter.increment(UUID_A)
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
