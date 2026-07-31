"""NFR-003/FR-008: the consent predicate's cost must not scale with journal size.

Nothing measured this before. NFR-003 states a *mechanism* — "indexed column lookup
only, via FR-008's filtered read" — and the shipped drain had none of it: the
universe came from an unfiltered ``ORDER BY created_at`` read of every row of every
project, ``CREATE_PROJECT_INDEX_SQL`` was created and referenced by no query, and
payload hydration opened a fresh SQLite connection per event. A 100k-row journal
drained in 1,000-event batches cost ~100 full-table scans plus a sort and ~100,000
connections, and every consent test in the suite passed throughout.

So this file measures, rather than asserting a shape and hoping:

* **VM steps** — ``sqlite3``'s progress handler fires once per virtual-machine
  opcode, so it is a deterministic (not wall-clock) count of work done inside
  SQLite. A full table scan spends ~10 opcodes per row; an indexed range scan
  spends them only on the rows it returns.
* **Statements** — ``set_trace_callback`` counts every statement executed.
* **Connections** — a counting wrapper around ``sqlite3.connect``, filtered to the
  journal file so the in-memory ledger and target registry are not counted.

All three are collected over a real ``dispatch`` and compared between two journals
that differ *only* in how many rows a **non-consented** project contributed. Cost
that tracks the non-consented population is the defect; cost that tracks the
selected batch is correct.

Deliberately not asserted here: elapsed time. A timing assertion on this path would
be a flake generator on CI, and it would also pass for an implementation that read
every row quickly.
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from specify_cli.delivery.dispatcher import dispatch
from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.receivers import StubReceiver
from specify_cli.delivery.targets import SqliteDeliveryTargetRegistry
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import (
    COL_PAYLOAD,
    DISTINCT_PROJECT_UUIDS_SQL,
    Event,
    select_identity_projection_sql,
)

pytestmark = [pytest.mark.fast]

CONSENTED_UUID = "aaaaaaaa-1111-1111-1111-111111111111"
OTHER_UUID = "bbbbbbbb-2222-2222-2222-222222222222"

#: Two journal sizes 20x apart. The consented batch is identical in both, so any
#: cost difference is attributable to the non-consented population alone.
SMALL = 400
LARGE = 8_000
BATCH = 40


@pytest.fixture(autouse=True)
def _consent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    from specify_cli.sync.consent import set_project_consent

    set_project_consent(CONSENTED_UUID, True)
    set_project_consent(OTHER_UUID, False)


# --------------------------------------------------------------------------- #
# Instrumentation                                                              #
# --------------------------------------------------------------------------- #


@dataclass
class JournalCost:
    """What one drain cost the *journal* database, in deterministic units."""

    connections: int = 0
    statements: int = 0
    vm_steps: int = 0
    sql: list[str] = field(default_factory=list)

    def __str__(self) -> str:  # pragma: no cover - assertion messages only
        return (
            f"connections={self.connections} statements={self.statements} "
            f"vm_steps={self.vm_steps}"
        )


@contextmanager
def measure(journal_path: Path) -> Iterator[JournalCost]:
    """Count connections, statements and SQLite VM opcodes against *journal_path*.

    Patches ``sqlite3.connect`` process-wide and filters on the database argument,
    so the delivery ledger and target registry (both ``:memory:``) contribute
    nothing. Restores the original on exit even if the body raises.
    """
    cost = JournalCost()
    real_connect = sqlite3.connect
    target = str(journal_path)

    def _steps() -> int:
        cost.vm_steps += 1
        return 0  # a non-zero return aborts the running statement

    def _connect(database: object = ":memory:", *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        conn = real_connect(database, *args, **kwargs)  # type: ignore[arg-type]
        if str(database) == target:
            cost.connections += 1

            def _trace(statement: str | None) -> None:
                cost.statements += 1
                cost.sql.append(statement or "")

            conn.set_trace_callback(_trace)
            conn.set_progress_handler(_steps, 1)
        return conn

    sqlite3.connect = _connect  # type: ignore[assignment]
    try:
        yield cost
    finally:
        sqlite3.connect = real_connect  # type: ignore[assignment]


def _event(event_id: str, uuid: str, created_at: str) -> Event:
    return Event(
        event_id=event_id,
        event_type="WorkPackageApproved",
        payload=json.dumps({"event_id": event_id, "project_uuid": uuid}).encode(),
        occurred_at=created_at,
        created_at=created_at,
        project_uuid=uuid,
    )


def _seed(db_path: Path, *, others: int, consented: int) -> EventJournal:
    """A journal holding *others* non-consented rows and *consented* consented ones.

    The non-consented rows are strictly older, so FIFO order puts them first and a
    predicate applied after a limit would also be caught.
    """
    journal = EventJournal(db_path)
    for i in range(others):
        journal.append(
            _event(f"evt-other-{i:06d}", OTHER_UUID, f"2026-06-01T00:00:{i % 60:02d}.{i:06d}Z")
        )
    for i in range(consented):
        journal.append(_event(f"evt-mine-{i:04d}", CONSENTED_UUID, f"2026-07-01T00:00:{i:04d}Z"))
    return journal


def _drain(journal: EventJournal) -> tuple[JournalCost, int]:
    ledger = SqliteDeliveryLedger(":memory:")
    registry = SqliteDeliveryTargetRegistry(":memory:")
    target = registry.register(
        url="https://hosted.example.com",
        team_slug="team",
        user_email="operator@example.com",
    )
    receiver = StubReceiver()
    with measure(journal.db_path) as cost:
        summary = dispatch(journal=journal, ledger=ledger, receiver=receiver, target=target)
    assert summary.selected == BATCH, (
        "the drain under measurement must actually have selected the consented "
        f"batch, or the cost numbers mean nothing: selected={summary.selected}"
    )
    assert set(receiver.received_event_ids()) == {
        f"evt-mine-{i:04d}" for i in range(BATCH)
    }, "only the consented project's rows may ship"
    return cost, summary.selected


# --------------------------------------------------------------------------- #
# The mechanism NFR-003 names: an indexed lookup, on a filtered read           #
# --------------------------------------------------------------------------- #


def test_the_universe_read_is_an_indexed_lookup_not_a_table_scan(tmp_path: Path) -> None:
    """NFR-003's stated mechanism: "indexed column lookup only".

    ``CREATE_PROJECT_INDEX_SQL`` shipped with no query referencing ``project_uuid``
    in a predicate, so the index existed and was never consulted. ``EXPLAIN QUERY
    PLAN`` is the only way to assert the difference: an index the planner declines
    to use is indistinguishable, through the API, from an index that is not there.
    """
    journal = _seed(tmp_path / "j.db", others=SMALL, consented=BATCH)

    conn = sqlite3.connect(str(journal.db_path))
    try:
        plan = [
            row[3]
            for row in conn.execute(
                "EXPLAIN QUERY PLAN " + select_identity_projection_sql(1),
                (CONSENTED_UUID,),
            )
        ]
        distinct_plan = [
            row[3] for row in conn.execute("EXPLAIN QUERY PLAN " + DISTINCT_PROJECT_UUIDS_SQL)
        ]
    finally:
        conn.close()

    assert any("idx_event_journal_project_created" in step for step in plan), (
        f"the filtered read must be planned through the project index: {plan}"
    )
    assert not any(step.startswith("SCAN event_journal") for step in plan), (
        f"the filtered read must not be planned as a full table scan: {plan}"
    )
    assert not any(step.startswith("SCAN event_journal") for step in distinct_plan), (
        "enumerating the distinct projects present must seek through the index "
        f"rather than scan every row: {distinct_plan}"
    )


def test_the_filtered_read_carries_no_limit_and_no_payload(tmp_path: Path) -> None:
    """The two constraints an "efficient" rewrite is most likely to violate.

    A ``LIMIT`` here is NFR-002 starvation: ``ledger.select_undelivered`` slices an
    already-filtered universe, so a window filled with already-delivered terminal
    rows is stripped afterwards and yields an empty selection with consented rows
    behind it. A payload BLOB in the projection satisfies NFR-003's letter — no
    scan — while still materialising every byte of a 100k-row project.
    """
    del tmp_path
    sql = select_identity_projection_sql(3)

    assert "LIMIT" not in sql.upper(), (
        "no LIMIT may be pushed into the journal's universe read: the ledger "
        "slices an already-filtered universe, so a limit here lets delivered rows "
        "fill the window and be stripped afterwards (NFR-002 starvation)"
    )
    assert COL_PAYLOAD not in sql, (
        f"the universe read must not select the payload BLOB: {sql}"
    )


def test_the_filtered_read_returns_only_the_requested_projects(tmp_path: Path) -> None:
    """A direct pin on the SQL gate itself, independent of the in-memory one.

    ``selectable_event_ids``'s consent clause is pinned separately by
    ``tests/sync/test_consent_resolver_3030.py``. Both gates stand on the drain
    path, so neither is proven by an end-to-end test alone; each needs its own.
    """
    journal = _seed(tmp_path / "j.db", others=25, consented=BATCH)

    rows = journal.read_identity_projection(project_uuids=[CONSENTED_UUID])

    assert {row.project_uuid for row in rows} == {CONSENTED_UUID}
    assert len(rows) == BATCH, (
        f"expected only the consented project's {BATCH} rows, got {len(rows)} "
        "— the read is not filtering at all"
    )
    assert [row.event_id for row in rows] == sorted(row.event_id for row in rows), (
        "FIFO ordering by created_at must survive the filter"
    )


# --------------------------------------------------------------------------- #
# The measurement NFR-003 actually claims: cost is independent of store size    #
# --------------------------------------------------------------------------- #


def test_nfr003_selection_cost_does_not_scale_with_journal_size(tmp_path: Path) -> None:
    """A 20x larger non-consented population must not cost 20x more to skip.

    Both journals hold the *same* consented batch. Every extra row belongs to a
    project the drain must not ship, so a correct implementation never touches it
    and the numbers below stay flat. The unfiltered ``ORDER BY created_at`` read
    that shipped scales linearly here — that is the finding.
    """
    small_cost, _ = _drain(_seed(tmp_path / "small.db", others=SMALL, consented=BATCH))
    large_cost, _ = _drain(_seed(tmp_path / "large.db", others=LARGE, consented=BATCH))

    assert large_cost.statements == small_cost.statements, (
        "the number of journal statements a drain issues must be fixed by the "
        f"batch, not by the store: {small_cost} vs {large_cost}"
    )
    assert large_cost.connections == small_cost.connections, (
        f"connection count must not track store size: {small_cost} vs {large_cost}"
    )
    # The distinct-project probe seeks the index once per distinct project, so it
    # grows with log(rows) — a 20x row increase must stay far inside 2x work. The
    # unfiltered read that shipped grows ~20x here.
    assert large_cost.vm_steps < small_cost.vm_steps * 2, (
        f"SQLite spent {large_cost.vm_steps} opcodes on a {LARGE}-row journal "
        f"versus {small_cost.vm_steps} on a {SMALL}-row one for the identical "
        f"{BATCH}-event batch. The predicate is scanning the store instead of "
        "seeking the project index (NFR-003)"
    )


def test_payload_hydration_does_not_open_a_connection_per_event(tmp_path: Path) -> None:
    """``dispatcher.py`` hydrated payloads with one ``read_by_id`` — and one
    ``sqlite3.connect`` — per event, so a 1,000-event batch opened 1,000
    connections. Connection count must be fixed by the drain, not the batch."""
    tiny = _seed(tmp_path / "tiny.db", others=10, consented=BATCH)
    ledger = SqliteDeliveryLedger(":memory:")
    registry = SqliteDeliveryTargetRegistry(":memory:")
    target = registry.register(
        url="https://hosted.example.com",
        team_slug="team",
        user_email="operator@example.com",
    )

    with measure(tiny.db_path) as small_batch:
        dispatch(
            journal=tiny,
            ledger=ledger,
            receiver=StubReceiver(),
            target=target,
            limit=2,
        )

    fresh_ledger = SqliteDeliveryLedger(":memory:")
    with measure(tiny.db_path) as full_batch:
        summary = dispatch(
            journal=tiny,
            ledger=fresh_ledger,
            receiver=StubReceiver(),
            target=target,
            limit=BATCH,
        )

    assert summary.selected == BATCH, "the wide drain must have selected the full batch"
    assert full_batch.connections == small_batch.connections, (
        f"hydrating {BATCH} events opened {full_batch.connections} journal "
        f"connections versus {small_batch.connections} for 2 — payload hydration "
        "is opening one connection per event"
    )
