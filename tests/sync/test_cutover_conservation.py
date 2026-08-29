"""Cutover copy-identity: conservation + divergent-payload quarantine (WP02).

Pins the FOUNDATION invariants WP03's cutover copy consumes (IC-00/IC-03,
FR-005, NFR-002 / INV-2):

* **Conservation (0 loss / 0 dup, incl. ownerless rows).** Every pre-existing
  ``event_id`` — including legacy rows that predate per-project ownership and so
  carry no ``project_uuid`` — lands in the destination journal exactly once. The
  assertion is a before/after multiset diff (count *and* identity-set), never a
  fixed literal.
* **Ownerless-row attribution (IC-00).** A row with a missing/nil ``project_uuid``
  acquires the destination store's canonical owner *before* the ``append`` owner
  guard, so the copy no longer trips
  ``ValueError("event-declared project UUID does not match store owner")``. A row
  whose payload declares a *different* owner is a genuine
  ``CONFLICTING_PROJECT_UUID`` and is refused, never force-attributed.
* **Divergent-payload quarantine (#2846).** Same ``event_id`` + divergent canonical
  payload parks a conflict for an operator (blocked run) rather than
  last-write-win.
* **Idempotence backstop.** A replayed copy is a no-op — re-running the copy adds
  no rows, and ``journal.append`` short-circuits a replayed ``event_id``.

Isolation: every test resolves its runtime from an isolated ``SPEC_KITTY_HOME`` /
``HOME`` temp root, and the legacy sources live under a *separate* temp dir, so
``discover_source_dbs`` only ever sees the seeded fixtures — never the real
``~/.spec-kitty`` on this live-legacy box (plan Risk MINOR-8 / research Decision 10).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.sync.migrate_journal import (
    LEGACY_DIGEST,
    MigrationAudit,
    discover_source_dbs,
    migrate_queues_to_journal,
)
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

OWNER = "cccccccc-0000-0000-0000-000000000003"
OTHER_OWNER = "dddddddd-0000-0000-0000-000000000004"
NIL_UUID = "00000000-0000-0000-0000-000000000000"


def _isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the runtime store at an isolated temp root; return the legacy root."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    legacy_root = tmp_path / "legacy"
    legacy_root.mkdir(parents=True, exist_ok=True)
    return legacy_root


def _seed_queue(path: Path, rows: tuple[tuple[str, dict[str, object] | None], ...]) -> None:
    """Seed a legacy queue DB with ``(event_id, data_dict)`` rows (``None`` == empty)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE queue (id INTEGER PRIMARY KEY, event_id TEXT UNIQUE, "
        "event_type TEXT, data TEXT, timestamp INTEGER, retry_count INTEGER)"
    )
    for index, (event_id, data) in enumerate(rows, start=1):
        payload = {} if data is None else data
        connection.execute(
            "INSERT INTO queue VALUES (?, ?, 'MissionCreated', ?, ?, 0)",
            (index, event_id, json.dumps(payload, sort_keys=True), index),
        )
    connection.commit()
    connection.close()


def _empty_queue(path: Path) -> None:
    """A scoped queue DB that exists but holds zero queued rows."""
    _seed_queue(path, ())


def _project_only(store: ProjectSyncStore) -> None:
    authority = store.layout_generation()
    authority.begin_cutover("wp02-cutover-test")
    authority.publish_project_only("wp02-cutover-test", verify_exact=lambda: True)


def _run_migration(legacy_root: Path, store: ProjectSyncStore, audit: MigrationAudit) -> object:
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        return migrate_queues_to_journal(legacy_root, journal=journal, audit=audit)


def _destination_event_ids(store: ProjectSyncStore) -> set[str]:
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        return {event.event_id for event in journal.read_all()}


def _destination_count(store: ProjectSyncStore) -> int:
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        return int(journal.count())


# --- T006: conservation (0 loss / 0 dup, incl. ownerless rows) --------------


def test_cutover_conserves_every_event_including_ownerless(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_root = _isolate(tmp_path, monkeypatch)
    _seed_queue(
        legacy_root / "queues" / "queue-1111111111111111.db",
        (
            ("evt-owned", {"payload": {"n": 1}, "project_uuid": OWNER}),
            ("evt-ownerless", {"payload": {"n": 2}}),  # no project_uuid — the trap
        ),
    )
    _seed_queue(
        legacy_root / "queue.db",
        (("evt-legacy-ownerless", {"payload": {"n": 3}}),),
    )
    # Pre-cutover event-id multiset snapshot (before/after diff, not a literal).
    source_ids = {"evt-owned", "evt-ownerless", "evt-legacy-ownerless"}
    # Fixture matches exactly what the engine walks (do not hand-list paths).
    assert {source.path.name for source in discover_source_dbs(legacy_root)} == {
        "queue-1111111111111111.db",
        "queue.db",
    }

    store = ProjectSyncStore(OWNER)
    _project_only(store)
    audit = MigrationAudit(":memory:")
    result = _run_migration(legacy_root, store, audit)

    assert result.blocked is False  # type: ignore[attr-defined]
    # INV-2: count equality AND identity-set equality; ownerless rows included.
    assert _destination_count(store) == len(source_ids)
    assert _destination_event_ids(store) == source_ids

    # Idempotent re-run adds no rows (leans on the append event_id backstop).
    second_audit = MigrationAudit(":memory:")
    _run_migration(legacy_root, store, second_audit)
    assert _destination_count(store) == len(source_ids)
    assert _destination_event_ids(store) == source_ids


def test_empty_legacy_store_is_a_noop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_root = _isolate(tmp_path, monkeypatch)
    store = ProjectSyncStore(OWNER)
    _project_only(store)
    audit = MigrationAudit(":memory:")

    result = _run_migration(legacy_root, store, audit)

    assert result.blocked is False  # type: ignore[attr-defined]
    assert _destination_count(store) == 0


def test_scoped_db_with_zero_rows_is_skipped_not_errored(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_root = _isolate(tmp_path, monkeypatch)
    _empty_queue(legacy_root / "queues" / "queue-abababababababab.db")
    _seed_queue(
        legacy_root / "queues" / "queue-cdcdcdcdcdcdcdcd.db",
        (("evt-present", {"payload": {"n": 1}}),),
    )
    store = ProjectSyncStore(OWNER)
    _project_only(store)
    audit = MigrationAudit(":memory:")

    result = _run_migration(legacy_root, store, audit)

    assert result.blocked is False  # type: ignore[attr-defined]
    assert _destination_event_ids(store) == {"evt-present"}


def test_identical_duplicate_across_sources_dedups_with_both_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_root = _isolate(tmp_path, monkeypatch)
    shared: dict[str, object] = {"payload": {"k": "v"}}  # ownerless + byte-identical
    _seed_queue(legacy_root / "queues" / "queue-aaaaaaaaaaaaaaaa.db", (("dup", shared),))
    _seed_queue(legacy_root / "queues" / "queue-bbbbbbbbbbbbbbbb.db", (("dup", shared),))
    store = ProjectSyncStore(OWNER)
    _project_only(store)
    audit = MigrationAudit(":memory:")

    result = _run_migration(legacy_root, store, audit)

    assert result.blocked is False  # type: ignore[attr-defined]
    assert _destination_count(store) == 1  # collapse to ONE record …
    # … while accumulating BOTH source provenance rows.
    assert audit.provenance_for("dup") == ["aaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbb"]
    assert audit.has_conflicts() is False  # identical payloads dedup, not quarantine


# --- T007: divergent-payload quarantine (#2846) -----------------------------


def test_divergent_payload_quarantines_not_last_write_win(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_root = _isolate(tmp_path, monkeypatch)
    # Same event_id, divergent canonical payloads (the #2846 shape).
    _seed_queue(
        legacy_root / "queues" / "queue-1111111111111111.db",
        (("shared", {"payload": {"body": "A"}}),),
    )
    _seed_queue(
        legacy_root / "queues" / "queue-2222222222222222.db",
        (("shared", {"payload": {"body": "B"}}),),
    )
    store = ProjectSyncStore(OWNER)
    _project_only(store)
    audit = MigrationAudit(":memory:")

    result = _run_migration(legacy_root, store, audit)

    # Blocked / non-zero exit while the conflict is unresolved.
    assert result.blocked is True  # type: ignore[attr-defined]
    assert result.exit_code != 0  # type: ignore[attr-defined]
    # A quarantined conflict exists for the shared event_id.
    assert audit.has_conflicts() is True
    assert audit.quarantined_count() >= 1
    assert any(conflict.event_id == "shared" for conflict in audit.conflicts())
    # Exactly ONE authoritative record lands (not last-write-win, not two rows).
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        shared_records = [event for event in journal.read_all() if event.event_id == "shared"]
    assert len(shared_records) == 1
    authoritative = shared_records[0].payload

    # Deterministic: a re-run does not flip the authoritative payload.
    second_audit = MigrationAudit(":memory:")
    _run_migration(legacy_root, store, second_audit)
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        replayed = journal.read_by_id("shared")
    assert replayed is not None
    assert replayed.payload == authoritative


# --- T009: ownerless-row attribution (focused unit) -------------------------


def test_attribute_owner_assigns_owner_and_preserves_distinct_reasons() -> None:
    from specify_cli.sync.migrate_journal import _attribute_owner
    from specify_cli.sync.project_store_migration import QuarantineReason

    # Missing project_uuid → attributed to the destination owner (MISSING reason).
    assert _attribute_owner(json.dumps({"payload": {}}), OWNER) == (
        OWNER,
        QuarantineReason.MISSING_PROJECT_UUID,
    )
    # Nil project_uuid → attributed to the destination owner (NIL reason).
    assert _attribute_owner(json.dumps({"project_uuid": NIL_UUID}), OWNER) == (
        OWNER,
        QuarantineReason.NIL_PROJECT_UUID,
    )
    # Matching owner → passes through unchanged, no reason.
    assert _attribute_owner(json.dumps({"project_uuid": OWNER}), OWNER) == (OWNER, None)
    # Divergent declared owner → refused (never force-attributed), CONFLICTING.
    assert _attribute_owner(json.dumps({"project_uuid": OTHER_OWNER}), OWNER) == (
        None,
        QuarantineReason.CONFLICTING_PROJECT_UUID,
    )
    # Malformed declared owner → refused, distinct MALFORMED reason.
    assert _attribute_owner(json.dumps({"project_uuid": "not-a-uuid"}), OWNER) == (
        None,
        QuarantineReason.MALFORMED_PROJECT_UUID,
    )


def test_ownerless_row_satisfies_owner_guard_after_attribution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_root = _isolate(tmp_path, monkeypatch)
    _seed_queue(
        legacy_root / "queue.db",
        (("evt-ownerless", {"payload": {"n": 1}}),),
    )
    store = ProjectSyncStore(OWNER)
    _project_only(store)
    audit = MigrationAudit(":memory:")

    result = _run_migration(legacy_root, store, audit)

    # Attributed (not dropped, not quarantined) and stored under the owner.
    assert result.blocked is False  # type: ignore[attr-defined]
    assert audit.has_conflicts() is False
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        stored = journal.read_by_id("evt-ownerless")
    assert stored is not None
    assert stored.project_uuid == OWNER  # passes the owner guard on copy
    assert audit.provenance_for("evt-ownerless") == [LEGACY_DIGEST]


def test_divergent_declared_owner_is_refused_not_misattributed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_root = _isolate(tmp_path, monkeypatch)
    _seed_queue(
        legacy_root / "queue.db",
        (("evt-foreign", {"payload": {"n": 1}, "project_uuid": OTHER_OWNER}),),
    )
    store = ProjectSyncStore(OWNER)
    _project_only(store)
    audit = MigrationAudit(":memory:")

    result = _run_migration(legacy_root, store, audit)

    # A foreign-owned row is refused: blocked, and it never lands in this store.
    assert result.blocked is True  # type: ignore[attr-defined]
    assert _destination_count(store) == 0
    assert audit.has_conflicts() is True


# --- T010: journal.append event_id idempotence backstop ---------------------


def test_journal_append_is_idempotent_on_replayed_event_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    store = ProjectSyncStore(OWNER)
    _project_only(store)
    event = Event(
        event_id="evt-replay",
        event_type="MissionCreated",
        payload=json.dumps({"payload": {"n": 1}}).encode(),
        occurred_at="2026-08-10T00:00:00+00:00",
        created_at="2026-08-10T00:00:01+00:00",
        project_uuid=OWNER,
    )
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        first = journal.append(event)
        second = journal.append(event)  # replay — must be a no-op

    assert first.inserted is True
    assert second.inserted is False
    assert first.capture_sequence == second.capture_sequence  # no duplicate row
    assert _destination_count(store) == 1
