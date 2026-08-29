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
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch
from uuid import NAMESPACE_URL, uuid5

import pytest

from specify_cli.delivery.dispatcher import dispatch
from specify_cli.delivery.receivers import StubReceiver
from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import (
    COL_PAYLOAD,
    Event,
    select_identity_projection_sql,
)
from specify_cli.sync.consent import record_project_opt_in, record_project_opt_out
from specify_cli.sync.layout_generation import LayoutMode
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

CONSENTED_UUID = "aaaaaaaa-1111-1111-1111-111111111111"
OTHER_UUID = "bbbbbbbb-2222-2222-2222-222222222222"

#: Two journal sizes 20x apart. The consented batch is identical in both, so any
#: cost difference is attributable to the non-consented population alone.
SMALL = 400
LARGE = 8_000
BATCH = 40


@pytest.fixture(autouse=True)
def _consent(canonical_home: None, monkeypatch: pytest.MonkeyPatch) -> None:
    del canonical_home  # R1b (#3121): home isolation provided by the canonical SPEC_KITTY_HOME owner
    # The WP06 transport lease binds egress eligibility only while the machine
    # kill switch is armed (arming is NOT consent — #3030; the per-project
    # consent rows below still decide what ships).
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")


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
        return f"connections={self.connections} statements={self.statements} vm_steps={self.vm_steps}"


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

    def _connect(
        database: str | bytes | os.PathLike[str] | os.PathLike[bytes] = ":memory:",
        *args: Any,
        **kwargs: Any,
    ) -> sqlite3.Connection:
        conn = cast(sqlite3.Connection, real_connect(database, *args, **kwargs))
        if str(database) == target:
            cost.connections += 1

            def _trace(statement: str | None) -> None:
                cost.statements += 1
                cost.sql.append(statement or "")

            conn.set_trace_callback(_trace)
            conn.set_progress_handler(_steps, 1)
        return conn

    with patch.object(sqlite3, "connect", _connect):
        yield cost


def _event(event_id: str, uuid: str, created_at: str) -> Event:
    return Event(
        event_id=event_id,
        event_type="WorkPackageApproved",
        payload=json.dumps({"event_id": event_id, "project_uuid": uuid}).encode(),
        occurred_at=created_at,
        created_at=created_at,
        project_uuid=uuid,
    )


def _initialize(store: ProjectSyncStore, *, consented: bool) -> None:
    authority = store.layout_generation()
    if authority.read_state().mode is LayoutMode.LEGACY:
        authority.begin_cutover("nfr003-test")
        authority.publish_project_only("nfr003-test", verify_exact=lambda: True)
    if consented:
        record_project_opt_in(str(store.project_uuid), actor="nfr003-test")
        with store.unit_of_work() as unit:
            unit.execute(
                "INSERT INTO project_target_admissions "
                "(project_uuid, target_identity, account_identity, private_teamspace_id, "
                "configuration_generation, admission_state, admission_generation, binding_audience) "
                "VALUES (?, 'https://hosted.example.com', 'operator@example.com', 'team', 1, "
                "'admitted', '1', 'private-teamspace:team')",
                (str(store.project_uuid),),
            )
    else:
        record_project_opt_out(str(store.project_uuid), actor="nfr003-test")


def _seed(db_path: Path, *, others: int, consented: int) -> ProjectSyncStore:
    """A journal holding *others* non-consented rows and *consented* consented ones.

    The non-consented rows are strictly older, so FIFO order puts them first and a
    predicate applied after a limit would also be caught.
    """
    consented_uuid = str(uuid5(NAMESPACE_URL, f"consented:{db_path}"))
    other_uuid = str(uuid5(NAMESPACE_URL, f"other:{db_path}"))
    store = ProjectSyncStore(consented_uuid)
    other_store = ProjectSyncStore(other_uuid)
    _initialize(store, consented=True)
    _initialize(other_store, consented=False)
    with other_store.unit_of_work() as unit:
        journal = EventJournal(unit, other_store.layout_generation())
        for i in range(others):
            journal.append(
                _event(
                    f"evt-other-{i:06d}",
                    other_uuid,
                    f"2026-06-01T00:00:{i % 60:02d}.{i:06d}Z",
                )
            )
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        for i in range(consented):
            journal.append(
                _event(
                    f"evt-mine-{i:04d}",
                    consented_uuid,
                    f"2026-07-01T00:00:{i:04d}Z",
                )
            )
    return store


def _drain(store: ProjectSyncStore) -> tuple[JournalCost, int]:
    with store.unit_of_work() as unit:
        target = ProjectDeliveryTargetRegistry(store).get_current(unit)
    assert target is not None
    receiver = StubReceiver()
    with measure(store.database_path) as cost:
        summary = dispatch(
            store=store,
            receiver=receiver,
            target=target,
            context=store.create_context(),
        )
    assert summary.selected == BATCH, (
        f"the drain under measurement must actually have selected the consented batch, or the cost numbers mean nothing: selected={summary.selected}"
    )
    assert set(receiver.received_event_ids()) == {f"evt-mine-{i:04d}" for i in range(BATCH)}, "only the consented project's rows may ship"
    return cost, summary.selected


# --------------------------------------------------------------------------- #
# The mechanism NFR-003 names: an indexed lookup, on a filtered read           #
# --------------------------------------------------------------------------- #


def test_the_universe_read_is_an_indexed_lookup_not_a_table_scan(tmp_path: Path) -> None:
    """NFR-003's stated mechanism: "indexed column lookup only".

    Historical node, premise superseded by #3262: the original pin proved the
    machine-global ``event_journal`` read used ``idx_event_journal_project_created``
    instead of scanning every project's rows. Under per-project stores there is no
    shared journal to scan — the non-consented population lives in a different
    database file entirely — so the surviving NFR-003 question is that the
    project's own journal read (``journal_entries`` keyed by ``project_uuid`` and
    ordered by ``capture_sequence``) is planned through an index, not a full-table
    scan. ``EXPLAIN QUERY PLAN`` remains the only way to assert the difference: an
    index the planner declines to use is indistinguishable, through the API, from
    an index that is not there.
    """
    store = _seed(tmp_path / "j.db", others=SMALL, consented=BATCH)

    conn = sqlite3.connect(str(store.database_path))
    try:
        plan = [
            row[3]
            for row in conn.execute(
                "EXPLAIN QUERY PLAN SELECT entry_id, created_at, payload_json FROM journal_entries WHERE project_uuid = ? ORDER BY capture_sequence, entry_id",
                (str(store.project_uuid),),
            )
        ]
    finally:
        conn.close()

    assert any("USING INDEX" in step or "USING COVERING INDEX" in step for step in plan), (
        f"the project journal read must be planned through an index: {plan}"
    )
    assert not any(step.startswith("SCAN journal_entries") for step in plan), (
        f"the project journal read must not be planned as a full table scan: {plan}"
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
    assert COL_PAYLOAD not in sql, f"the universe read must not select the payload BLOB: {sql}"


def test_the_filtered_read_returns_only_the_requested_projects(tmp_path: Path) -> None:
    """A direct pin on the SQL gate itself, independent of the in-memory one.

    ``selectable_event_ids``'s consent clause is pinned separately by
    ``tests/sync/test_consent_resolver_3030.py``. Both gates stand on the drain
    path, so neither is proven by an end-to-end test alone; each needs its own.
    """
    store = _seed(tmp_path / "j.db", others=25, consented=BATCH)
    with store.unit_of_work() as unit:
        rows = EventJournal(unit, store.layout_generation()).read_identity_projection(project_uuids=[str(store.project_uuid)])

    assert {row.project_uuid for row in rows} == {str(store.project_uuid)}
    assert len(rows) == BATCH, f"expected only the consented project's {BATCH} rows, got {len(rows)} — the read is not filtering at all"
    assert [row.event_id for row in rows] == sorted(row.event_id for row in rows), "FIFO ordering by created_at must survive the filter"


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
        f"the number of journal statements a drain issues must be fixed by the batch, not by the store: {small_cost} vs {large_cost}"
    )
    assert large_cost.connections == small_cost.connections, f"connection count must not track store size: {small_cost} vs {large_cost}"
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
    with tiny.unit_of_work() as unit:
        target = ProjectDeliveryTargetRegistry(tiny).get_current(unit)
    assert target is not None

    with measure(tiny.database_path) as small_batch:
        dispatch(
            store=tiny,
            receiver=StubReceiver(),
            target=target,
            context=tiny.create_context(),
            limit=2,
        )

    with tiny.unit_of_work() as unit:
        unit.execute("DELETE FROM delivery_results")
        unit.execute("DELETE FROM delivery_attempts")
    with measure(tiny.database_path) as full_batch:
        summary = dispatch(
            store=tiny,
            receiver=StubReceiver(),
            target=target,
            context=tiny.create_context(),
            limit=BATCH,
        )

    assert summary.selected == BATCH, "the wide drain must have selected the full batch"
    assert full_batch.connections == small_batch.connections, (
        f"hydrating {BATCH} events opened {full_batch.connections} journal "
        f"connections versus {small_batch.connections} for 2 — payload hydration "
        "is opening one connection per event"
    )
