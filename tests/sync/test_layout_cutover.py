"""Layout resolution + canonical crash-safe auto-cutover (WP03, IC-02).

Closes the silent zero-capture defect (#3425) at its origin — the layout-resolution
state machine in ``sync/layout_generation.py``. The three hazards proven here:

* **T011 (greenfield)** — a fresh repository-root checkout with no ``.layout-generation``
  record and no legacy queue data resolves ``PROJECT_ONLY`` *before* any ``LEGACY`` state
  is persisted (Hazard (b): ``_read_locked`` self-destructs the greenfield signal), so its
  first event actually lands in the journal (FR-002 / SC-001).
* **T012 (idempotence under interruption)** — a crash between ``begin_cutover`` and
  ``publish_project_only`` re-enters the *same* deterministic ``migration_id`` and
  converges, never bricking the root, copying each legacy event exactly once
  (FR-003 / NFR-005 / INV-3).
* **T013 (emit during CUTOVER_PENDING)** — a live write arriving while a migration is in
  flight blocks-and-retries within a bounded, hook-driven wait and, on timeout, surfaces
  a distinguishable loud condition — it is **never** silently routed to LEGACY-and-swallowed
  (Hazard (a) / INV-5).
* **T014 (escape hatch)** — ``SPEC_KITTY_NO_AUTO_CUTOVER`` on a legacy-with-data root
  yields a loud, actionable, non-mutating refusal pointing at ``sync project-store-migrate``
  (Cutover Transition 5).

**Isolation is safety-critical (plan Risk MINOR-8).** This dev box is itself a live legacy
root; every test pins BOTH ``SPEC_KITTY_HOME`` and ``HOME`` to ``tmp_path`` so a stray
cutover can never touch the real machine-global ``~/.spec-kitty``. Legacy source DBs are
seeded *inside* the isolated runtime root (that is where ``discover_source_dbs`` reads).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.sync.layout_generation import (
    LayoutAutoCutoverRefusedError,
    LayoutCutoverIncompleteError,
    LayoutDestination,
    LayoutMode,
    LayoutTestHooks,
    LayoutVerificationError,
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


def _isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pin the runtime + home to temp; return the runtime root (== spec_kitty_dir)."""
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("SPEC_KITTY_SYNC_DISABLE", "1")
    monkeypatch.delenv("SPEC_KITTY_NO_AUTO_CUTOVER", raising=False)
    return runtime


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


def _event(event_id: str, owner: str = OWNER) -> Event:
    return Event(
        event_id=event_id,
        event_type="MissionCreated",
        payload=json.dumps({"payload": {"n": 1}}).encode(),
        occurred_at="2026-08-10T00:00:00+00:00",
        created_at="2026-08-10T00:00:01+00:00",
        project_uuid=owner,
    )


def _journal_ids(store: ProjectSyncStore) -> set[str]:
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        return {event.event_id for event in journal.read_all()}


def _record_on_disk(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    raw: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    return raw


# --- T011: greenfield -> PROJECT_ONLY, never persists LEGACY, captures --------


def test_greenfield_resolves_project_only_before_any_legacy_persist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    store = ProjectSyncStore(OWNER)
    authority = store.layout_generation()

    # A snapshot read on a greenfield root must NOT persist anything (Hazard (b)).
    assert authority.peek_state().mode is LayoutMode.LEGACY  # in-memory default only
    assert not authority.record_path.exists()

    # The write-path resolution flips a fresh root to PROJECT_ONLY without ever
    # persisting a LEGACY record (the RED behavior today: _read_locked writes LEGACY).
    permit = authority.issue_write_permit()
    assert permit.destination is LayoutDestination.PROJECT_STORE

    on_disk = _record_on_disk(authority.record_path)
    assert on_disk is not None
    assert on_disk["mode"] == LayoutMode.PROJECT_ONLY.value
    assert on_disk["migration_id"] is None
    assert on_disk["generation"] == 1

    # SC-001: the first live event actually lands (journal 0 -> 1).
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        assert journal.count() == 0
        journal.append(_event("evt-first"))
        assert journal.count() == 1


def test_greenfield_regression_guard_leaves_migrated_root_untouched(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    store = ProjectSyncStore(OWNER)
    authority = store.layout_generation()

    authority.issue_write_permit()  # resolve greenfield -> PROJECT_ONLY
    before_bytes = authority.record_path.read_bytes()
    before_gen = json.loads(before_bytes)["generation"]

    # An already-migrated root is a no-op on every subsequent resolution (NFR-003).
    for _ in range(3):
        authority.issue_write_permit()
    after_bytes = authority.record_path.read_bytes()
    assert after_bytes == before_bytes
    assert json.loads(after_bytes)["generation"] == before_gen


# --- T012: idempotence under interruption (crash between begin/publish) --------


def test_crash_between_begin_and_publish_reenters_same_id_and_converges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec_dir = _isolate(tmp_path, monkeypatch)
    _seed_queue(
        spec_dir / "queue.db",
        (("evt-a", {"payload": {"n": 1}}), ("evt-b", {"payload": {"n": 2}})),
    )
    store = ProjectSyncStore(OWNER)
    authority = store.layout_generation()
    migration_id = authority.auto_migration_id()

    # Simulate a crash: begin_cutover advanced to CUTOVER_PENDING; publish never ran.
    authority.begin_cutover(migration_id)
    assert authority.peek_state().mode is LayoutMode.CUTOVER_PENDING

    # Re-enter the resolution path: it must reuse the SAME migration_id (no "another
    # migration owns cutover"), converge to PROJECT_ONLY, and copy each event once.
    state = authority.resolve_layout_for_write()
    assert state.mode is LayoutMode.PROJECT_ONLY
    assert _journal_ids(store) == {"evt-a", "evt-b"}

    # Convergence is a pure no-op once PROJECT_ONLY: a second pass writes nothing.
    # Prove it on the persisted record — the authority uses __slots__, so a
    # byte-identical record + unchanged generation is the observable "zero writes".
    before_bytes = authority.record_path.read_bytes()
    second = authority.resolve_layout_for_write()
    assert second.mode is LayoutMode.PROJECT_ONLY
    assert authority.record_path.read_bytes() == before_bytes  # zero additional writes (INV-3)
    assert _journal_ids(store) == {"evt-a", "evt-b"}  # no drop, no dup


def test_deterministic_migration_id_is_stable_per_root_and_distinct_across_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    store = ProjectSyncStore(OWNER)
    first = store.layout_generation().auto_migration_id()
    second = store.layout_generation().auto_migration_id()
    assert first == second  # stable across constructions (crash-and-retry re-enters same)

    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "other-runtime"))
    other = ProjectSyncStore(OWNER).layout_generation().auto_migration_id()
    assert other != first  # distinct across roots


def test_incomplete_copy_does_not_publish_project_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec_dir = _isolate(tmp_path, monkeypatch)
    _seed_queue(spec_dir / "queue.db", (("evt-present", {"payload": {"n": 1}}),))
    store = ProjectSyncStore(OWNER)
    authority = store.layout_generation()

    # A copy driver that reports success but leaves the journal empty must NOT publish:
    # verify_exact (conservation) refuses cutover, so the root stays CUTOVER_PENDING.
    with pytest.raises(LayoutVerificationError):
        authority.resolve_layout_for_write(cutover_copy=lambda _mig: False)
    assert authority.peek_state().mode is LayoutMode.CUTOVER_PENDING


# --- T013: emit during CUTOVER_PENDING -> zero loss ---------------------------


def test_live_write_during_cutover_pending_is_never_a_silent_legacy_swallow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    store = ProjectSyncStore(OWNER)
    authority = store.layout_generation()

    # Hold the machine in CUTOVER_PENDING under a *foreign* migration id (an operator
    # migration in flight), so resolution will not auto-complete it.
    authority.begin_cutover("held-by-operator-migration")

    permit = authority.issue_write_permit()
    assert permit.destination is LayoutDestination.LEGACY  # unresolved, still pending

    waited: list[int] = []
    wrote: list[object] = []

    # No publish during the wait -> the write surfaces LOUDLY, never silently written.
    with pytest.raises(LayoutCutoverIncompleteError):
        authority.execute_write(
            permit,
            lambda p: wrote.append(p.destination),
            test_hooks=LayoutTestHooks(before_revalidate=lambda _p: waited.append(1)),
        )
    assert waited  # it blocked-and-retried (bounded), not an instant silent LEGACY write
    assert wrote == []  # the writer never ran against a LEGACY permit


def test_live_write_lands_in_project_store_when_publish_races_the_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    store = ProjectSyncStore(OWNER)
    authority = store.layout_generation()
    authority.begin_cutover("held-by-operator-migration")

    published: list[bool] = []

    def _publish_mid_wait(_permit: object) -> None:
        if not published:
            published.append(True)
            authority.publish_project_only("held-by-operator-migration", verify_exact=lambda: True)

    wrote: list[LayoutDestination] = []
    permit = authority.issue_write_permit()
    authority.execute_write(
        permit,
        lambda p: wrote.append(p.destination),
        test_hooks=LayoutTestHooks(before_revalidate=_publish_mid_wait),
    )
    # Redirected to the project store exactly once (not dropped, not double-written).
    assert wrote == [LayoutDestination.PROJECT_STORE]


# --- T014: SPEC_KITTY_NO_AUTO_CUTOVER -> loud actionable refusal, no mutation --


def test_escape_hatch_on_legacy_data_root_refuses_loudly_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec_dir = _isolate(tmp_path, monkeypatch)
    _seed_queue(spec_dir / "queue.db", (("evt-x", {"payload": {"n": 1}}),))
    monkeypatch.setenv("SPEC_KITTY_NO_AUTO_CUTOVER", "1")
    store = ProjectSyncStore(OWNER)
    authority = store.layout_generation()

    assert not authority.record_path.exists()
    with pytest.raises(LayoutAutoCutoverRefusedError) as excinfo:
        authority.resolve_layout_for_write()
    assert "sync project-store-migrate" in str(excinfo.value)

    # No mutation: no begin_cutover, no record persisted, nothing captured.
    assert not authority.record_path.exists()
    assert _journal_ids(store) == set()


def test_escape_hatch_still_allows_greenfield_journaling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    monkeypatch.setenv("SPEC_KITTY_NO_AUTO_CUTOVER", "1")
    store = ProjectSyncStore(OWNER)
    authority = store.layout_generation()

    # The hatch suppresses auto-cutover of legacy data, NOT greenfield journaling.
    state = authority.resolve_layout_for_write()
    assert state.mode is LayoutMode.PROJECT_ONLY
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        journal.append(_event("evt-green"))
    assert _journal_ids(store) == {"evt-green"}


def test_escape_hatch_still_completes_an_already_begun_cutover(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec_dir = _isolate(tmp_path, monkeypatch)
    _seed_queue(spec_dir / "queue.db", (("evt-inflight", {"payload": {"n": 1}}),))
    store = ProjectSyncStore(OWNER)
    authority = store.layout_generation()
    migration_id = authority.auto_migration_id()
    authority.begin_cutover(migration_id)  # migration already authorized

    # The hatch gates *initiating* auto-cutover, not *finishing* one already begun.
    monkeypatch.setenv("SPEC_KITTY_NO_AUTO_CUTOVER", "1")
    state = authority.resolve_layout_for_write()
    assert state.mode is LayoutMode.PROJECT_ONLY
    assert _journal_ids(store) == {"evt-inflight"}


# --- T015: detection-before-persist via the real reader -----------------------


def test_detects_greenfield_for_absent_empty_and_malformed_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec_dir = _isolate(tmp_path, monkeypatch)
    authority = ProjectSyncStore(OWNER).layout_generation()

    # (a) absent queue dir -> greenfield
    assert authority.has_legacy_data() is False

    # (b) present-but-empty scoped DB -> not legacy data awaiting migration
    _seed_queue(spec_dir / "queues" / "queue-abababababababab.db", ())
    assert authority.has_legacy_data() is False

    # (c) malformed filename -> skipped, still greenfield
    _seed_queue(spec_dir / "queues" / "queue-notahex.db", (("ghost", {"payload": {}}),))
    assert authority.has_legacy_data() is False

    # (d) a real scoped DB with a queued row -> legacy data present
    _seed_queue(spec_dir / "queues" / "queue-cdcdcdcdcdcdcdcd.db", (("evt", {"payload": {}}),))
    assert authority.has_legacy_data() is True


def test_detects_legacy_data_in_the_legacy_queue_db(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec_dir = _isolate(tmp_path, monkeypatch)
    authority = ProjectSyncStore(OWNER).layout_generation()
    _seed_queue(spec_dir / "queue.db", (("evt-legacy", {"payload": {}}),))
    assert authority.has_legacy_data() is True


# --- T016: lazy auto-cutover invoking the canonical engine --------------------


def test_auto_cutover_copies_via_canonical_engine_and_publishes_project_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec_dir = _isolate(tmp_path, monkeypatch)
    _seed_queue(
        spec_dir / "queues" / "queue-1111111111111111.db",
        (("evt-owned", {"payload": {"n": 1}, "project_uuid": OWNER}),),
    )
    _seed_queue(spec_dir / "queue.db", (("evt-ownerless", {"payload": {"n": 2}}),))
    store = ProjectSyncStore(OWNER)
    authority = store.layout_generation()

    state = authority.resolve_layout_for_write()

    assert state.mode is LayoutMode.PROJECT_ONLY
    assert state.migration_id is None
    # Conservation via the canonical engine: every legacy event, incl. ownerless.
    assert _journal_ids(store) == {"evt-owned", "evt-ownerless"}
