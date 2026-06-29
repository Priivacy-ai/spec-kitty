"""WP10 — migration off hash-scoped queues into the journal (+ provenance).

These acceptance tests pin the *observable* behaviour required by the binding
contract (``contracts/event-sync-delivery-contract.md`` §5) and the spec's
success criteria SC-006 / SC-011 for ``src/specify_cli/sync/migrate_journal.py``.

They assert on-disk / journal / provenance / conflict state and the command exit
status — never internal call order (NFR-001). A single-DB happy path is
explicitly insufficient (SC-006): the mandatory scenarios cover *multiple*
scoped DBs, an unknown-digest source, an identical-duplicate dedupe, a divergent
duplicate that quarantines, an idempotent re-run, and the C-006 guarantee that
``body_upload_queue`` is untouched.

NFR-001 / per-worker HOME isolation: every test materialises its own temp
spec-kitty home under ``tmp_path`` and passes explicit journal/audit instances,
so nothing touches the operator's real ``~/.spec-kitty``.
"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from specify_cli.event_journal import EventJournal
from specify_cli.sync.migrate_journal import (
    MigrationAudit,
    MigrationResult,
    SourceDb,
    discover_source_dbs,
    migrate_queues_to_journal,
    migration_target_token,
)
from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.target_authority import (
    OverrideMode,
    QueueScopeStatus,
    ResolvedSyncTarget,
)

pytestmark = [pytest.mark.integration]


# ----------------------------------------------------------------------
# Helpers / fixtures
# ----------------------------------------------------------------------


def _digest(scope: str) -> str:
    """Mirror ``scope_db_path``'s SHA-256-truncated digest of a queue scope."""
    return hashlib.sha256(scope.encode("utf-8")).hexdigest()[:16]  # noqa: TID251 - mirrors production scope_db_path filename digest, not the charter freshness hash


def _event(event_id: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "event_type": "custom.event",
        "payload": payload if payload is not None else {"k": event_id},
    }


def _seed_queue(path: Path, events: list[dict[str, Any]]) -> OfflineQueue:
    """Seed a real scoped queue DB (the live ``queue.py`` schema) at *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    queue = OfflineQueue(db_path=path)
    for event in events:
        assert queue.queue_event(event) is True
    return queue


def _queues_dir(home: Path) -> Path:
    return home / "queues"


def _scoped_path(home: Path, digest: str) -> Path:
    return _queues_dir(home) / f"queue-{digest}.db"


def _journal(home: Path) -> EventJournal:
    return EventJournal(home / "event_journal.db")


def _resolved_for_digest(home: Path, digest: str, *, scope: str) -> ResolvedSyncTarget:
    """A minimal resolved target whose derived queue path carries *digest*."""
    return ResolvedSyncTarget(
        configured_server_url=None,
        env_server_url=None,
        override_mode=OverrideMode.NONE,
        resolved_server_url="https://known.example",
        user_id="u",
        team_slug="t",
        derived_queue_scope=scope,
        queue_db_path=_scoped_path(home, digest),
        active_queue_scope_status=QueueScopeStatus.MATCHES,
    )


# ----------------------------------------------------------------------
# T056 — discovery
# ----------------------------------------------------------------------


def test_discover_finds_all_scoped_and_legacy_skips_malformed(tmp_path: Path) -> None:
    home = tmp_path
    _seed_queue(_scoped_path(home, "aaaa1111bbbb2222"), [_event("e1")])
    _seed_queue(_scoped_path(home, "cccc3333dddd4444"), [_event("e2")])
    _seed_queue(home / "queue.db", [_event("e3")])  # legacy
    # malformed: matches the glob but not the hex-digest shape → skipped
    _seed_queue(_queues_dir(home) / "queue-not-hex.db", [_event("e4")])

    sources = discover_source_dbs(home)
    digests = {s.digest for s in sources}

    assert "aaaa1111bbbb2222" in digests
    assert "cccc3333dddd4444" in digests
    assert any(s.is_legacy for s in sources)
    # malformed filename is not misparsed into a bogus digest
    assert "not-hex" not in digests
    # deterministic ordering for reproducible runs
    assert sources == sorted(sources, key=lambda s: (not s.is_legacy, s.digest))


def test_discover_empty_dir_is_empty_list(tmp_path: Path) -> None:
    assert discover_source_dbs(tmp_path) == []


# ----------------------------------------------------------------------
# SC-006 — multiple scoped DBs migrate in one run (contract §5 row 1)
# ----------------------------------------------------------------------


def test_multiple_scoped_dbs_migrate_in_one_run(tmp_path: Path) -> None:
    home = tmp_path
    _seed_queue(_scoped_path(home, "1111111111111111"), [_event("e1"), _event("e2")])
    _seed_queue(_scoped_path(home, "2222222222222222"), [_event("e3")])
    journal = _journal(home)

    result = migrate_queues_to_journal(home, journal=journal)

    stored = {e.event_id for e in journal.read_all()}
    assert stored == {"e1", "e2", "e3"}  # 100% of queued payloads preserved
    assert set(result.imported_event_ids) == {"e1", "e2", "e3"}
    assert result.exit_code == 0
    assert result.blocked is False


# ----------------------------------------------------------------------
# SC-006 — unknown digest → unknown provenance, no fabricated identity
# ----------------------------------------------------------------------


def test_unknown_digest_attaches_unknown_provenance(tmp_path: Path) -> None:
    home = tmp_path
    scope = "https://known.example|u|t"
    known_digest = _digest(scope)
    resolved = _resolved_for_digest(home, known_digest, scope=scope)

    # A source whose digest does NOT match the resolved target.
    _seed_queue(_scoped_path(home, "deadbeefdeadbeef"), [_event("e_unknown")])
    journal = _journal(home)
    audit = MigrationAudit(home / "migration_audit.db")

    result = migrate_queues_to_journal(
        home, journal=journal, audit=audit, resolved_target=resolved
    )

    assert "e_unknown" in result.unknown_event_ids
    target = audit.target_for("e_unknown")
    assert target is not None and target.startswith("unknown")
    # never fabricate a URL/team identity from a one-way digest
    assert "known.example" not in target
    # source digest is recorded as provenance regardless
    assert "deadbeefdeadbeef" in audit.provenance_for("e_unknown")


def test_matched_digest_attaches_known_target(tmp_path: Path) -> None:
    home = tmp_path
    scope = "https://known.example|u|t"
    known_digest = _digest(scope)
    resolved = _resolved_for_digest(home, known_digest, scope=scope)

    _seed_queue(_scoped_path(home, known_digest), [_event("e_known")])
    journal = _journal(home)
    audit = MigrationAudit(home / "migration_audit.db")

    result = migrate_queues_to_journal(
        home, journal=journal, audit=audit, resolved_target=resolved
    )

    assert "e_known" not in result.unknown_event_ids
    target = audit.target_for("e_known")
    assert target is not None and not target.startswith("unknown")


# ----------------------------------------------------------------------
# SC-011 — identical duplicate dedupes once with all source provenance
# ----------------------------------------------------------------------


def test_identical_duplicate_imports_once_with_all_provenance(tmp_path: Path) -> None:
    home = tmp_path
    digest_a = "aaaaaaaaaaaaaaaa"
    digest_b = "bbbbbbbbbbbbbbbb"
    same = _event("e_same", payload={"v": 1})
    _seed_queue(_scoped_path(home, digest_a), [dict(same)])
    _seed_queue(_scoped_path(home, digest_b), [dict(same)])
    journal = _journal(home)
    audit = MigrationAudit(home / "migration_audit.db")

    result = migrate_queues_to_journal(home, journal=journal, audit=audit)

    rows = [e for e in journal.read_all() if e.event_id == "e_same"]
    assert len(rows) == 1  # one journal row
    assert sorted(audit.provenance_for("e_same")) == sorted([digest_a, digest_b])
    assert "e_same" in result.deduped
    assert rows[0].event_id == "e_same"  # event_id never rewritten (C-005)


# ----------------------------------------------------------------------
# FR-018 / SC-011 — divergent duplicate quarantines; source untouched
# ----------------------------------------------------------------------


def test_divergent_duplicate_creates_conflict_and_preserves_source(tmp_path: Path) -> None:
    home = tmp_path
    digest_a = "aaaaaaaaaaaaaaaa"
    digest_b = "bbbbbbbbbbbbbbbb"
    src_a = _seed_queue(_scoped_path(home, digest_a), [_event("e_div", payload={"v": 1})])
    src_b = _seed_queue(_scoped_path(home, digest_b), [_event("e_div", payload={"v": 2})])
    size_a, size_b = src_a.size(), src_b.size()
    journal = _journal(home)
    audit = MigrationAudit(home / "migration_audit.db")

    result = migrate_queues_to_journal(home, journal=journal, audit=audit)

    # a migration-conflict/audit row exists for the divergent event — both in
    # the in-memory result and persisted in the migration-audit store
    assert audit.has_conflicts() is True
    assert any(c.event_id == "e_div" for c in result.conflicts)
    assert any(c.event_id == "e_div" for c in audit.conflicts())
    # the existing journal payload is NOT mutated/overwritten (one row)
    rows = [e for e in journal.read_all() if e.event_id == "e_div"]
    assert len(rows) == 1
    # both source DBs are left untouched (row counts unchanged)
    assert OfflineQueue(db_path=_scoped_path(home, digest_a)).size() == size_a
    assert OfflineQueue(db_path=_scoped_path(home, digest_b)).size() == size_b
    # cleanup blocked + non-zero / blocked exit
    assert result.cleanup_blocked is True
    assert result.blocked is True
    assert result.exit_code != 0


def test_source_with_clean_and_conflicting_events_still_blocks(tmp_path: Path) -> None:
    home = tmp_path
    _seed_queue(_scoped_path(home, "1111111111111111"), [_event("e_div", payload={"v": 1})])
    _seed_queue(
        _scoped_path(home, "2222222222222222"),
        [_event("e_div", payload={"v": 2}), _event("e_clean")],
    )
    journal = _journal(home)

    result = migrate_queues_to_journal(home, journal=journal)

    stored = {e.event_id for e in journal.read_all()}
    assert "e_clean" in stored  # clean event still imported
    assert result.cleanup_blocked is True  # but cleanup is blocked by the conflict


# ----------------------------------------------------------------------
# NFR-005 — idempotent re-run
# ----------------------------------------------------------------------


def test_re_run_imports_nothing_new(tmp_path: Path) -> None:
    home = tmp_path
    digest_a = "aaaaaaaaaaaaaaaa"
    digest_b = "bbbbbbbbbbbbbbbb"
    _seed_queue(_scoped_path(home, digest_a), [_event("e1")])
    _seed_queue(_scoped_path(home, digest_b), [_event("e1")])  # identical dup
    journal = _journal(home)
    audit = MigrationAudit(home / "migration_audit.db")

    first = migrate_queues_to_journal(home, journal=journal, audit=audit)
    assert set(first.imported_event_ids) == {"e1"}

    second = migrate_queues_to_journal(home, journal=journal, audit=audit)
    assert second.imported_event_ids == []  # nothing new on re-run
    # provenance is not duplicated on re-run
    assert sorted(audit.provenance_for("e1")) == sorted([digest_a, digest_b])
    assert len(journal.read_all()) == 1


# ----------------------------------------------------------------------
# C-006 / contract §6 — body-upload tables untouched by migration
# ----------------------------------------------------------------------


def test_body_upload_rows_untouched_by_migration(tmp_path: Path) -> None:
    home = tmp_path
    path = _scoped_path(home, "1111111111111111")
    _seed_queue(path, [_event("e1")])
    # seed one body_upload_queue row (NOT an event) directly via SQLite
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            "INSERT INTO body_upload_queue ("
            "project_uuid, mission_slug, target_branch, mission_type, "
            "manifest_version, artifact_path, content_hash, content_body, "
            "size_bytes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("p", "m", "b", "software-dev", "1", "a.md", "h", "body", 4, 0.0),
        )
        conn.commit()
    finally:
        conn.close()
    journal = _journal(home)

    migrate_queues_to_journal(home, journal=journal)

    conn = sqlite3.connect(path)
    try:
        body_count = conn.execute("SELECT COUNT(*) FROM body_upload_queue").fetchone()[0]
    finally:
        conn.close()
    assert body_count == 1  # body-upload row preserved (C-006)
    # the body row never leaks into the event journal
    assert {e.event_id for e in journal.read_all()} == {"e1"}


# ----------------------------------------------------------------------
# T061 — only currently-queued payloads survive; empty source is honest
# ----------------------------------------------------------------------


def test_empty_source_migrates_zero_and_reports_honestly(tmp_path: Path) -> None:
    home = tmp_path
    _seed_queue(_scoped_path(home, "1111111111111111"), [])  # schema only, 0 queued
    journal = _journal(home)

    result = migrate_queues_to_journal(home, journal=journal)

    assert result.imported_event_ids == []
    assert journal.read_all() == []
    # report states plainly that only currently-queued payloads survive
    assert "currently-queued" in result.note


# ----------------------------------------------------------------------
# Identifier Safety (charter) — ASCII-only deterministic target token
# ----------------------------------------------------------------------


def test_migration_target_token_is_ascii_for_accented_input() -> None:
    token = migration_target_token("café-équipe")
    assert token.isascii() is True
    assert "é" not in token
    # deterministic
    assert migration_target_token("café-équipe") == token


def test_result_and_source_types_are_exported() -> None:
    assert MigrationResult is not None
    assert SourceDb is not None


# ----------------------------------------------------------------------
# T058 edge case — a corrupt/locked source fails alone, run continues
# ----------------------------------------------------------------------


def test_corrupt_source_is_reported_without_aborting_others(tmp_path: Path) -> None:
    home = tmp_path
    _seed_queue(_scoped_path(home, "1111111111111111"), [_event("e_ok")])
    # a file shaped like a scoped DB but not a valid SQLite database
    corrupt = _scoped_path(home, "2222222222222222")
    corrupt.parent.mkdir(parents=True, exist_ok=True)
    corrupt.write_bytes(b"this is not a sqlite database")
    journal = _journal(home)
    audit = MigrationAudit(home / "migration_audit.db")

    result = migrate_queues_to_journal(home, journal=journal, audit=audit)

    assert {e.event_id for e in journal.read_all()} == {"e_ok"}  # healthy source migrated
    assert any(s.error is not None for s in result.sources)  # corrupt source reported
    assert result.cleanup_blocked is True
    assert result.blocked is True
    assert result.exit_code == 1
    assert audit.connection is not None


# ----------------------------------------------------------------------
# P1 atomicity — a provenance failure leaves NO orphan journal row
# ----------------------------------------------------------------------


def test_provenance_failure_leaves_no_orphan_journal_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed provenance write must roll back the staged journal row too.

    Regression for the WP10 P1 defect: the journal append used to autocommit per
    row *before* provenance was recorded, so a ``record_provenance`` failure left
    an orphan committed journal row with no matching provenance. The per-source
    import is now all-or-nothing — on a ``sqlite3.Error`` from provenance, BOTH
    the staged journal batch and the provenance are rolled back.
    """
    home = tmp_path
    digest = "1111111111111111"
    _seed_queue(_scoped_path(home, digest), [_event("e_orphan")])
    journal = _journal(home)
    audit = MigrationAudit(home / "migration_audit.db")

    def _boom(self: MigrationAudit, **_kwargs: Any) -> None:
        raise sqlite3.Error("provenance write failed")

    monkeypatch.setattr(MigrationAudit, "record_provenance", _boom)

    result = migrate_queues_to_journal(home, journal=journal, audit=audit)

    # No orphan: the staged journal row was rolled back with the provenance.
    assert journal.read_all() == []
    assert audit.provenance_for("e_orphan") == []
    # The failing source is reported (not imported) without aborting the run.
    assert result.imported_event_ids == []
    assert any(s.error is not None for s in result.sources)


# ----------------------------------------------------------------------
# T058 edge case — a body-only legacy DB has no queue table → zero events
# ----------------------------------------------------------------------


def test_source_without_queue_table_migrates_zero(tmp_path: Path) -> None:
    from specify_cli.sync.queue import ensure_body_queue_schema

    home = tmp_path
    path = _scoped_path(home, "3333333333333333")
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        ensure_body_queue_schema(conn)  # body tables only — no `queue` table
        conn.commit()
    finally:
        conn.close()
    journal = _journal(home)

    result = migrate_queues_to_journal(home, journal=journal)

    assert result.imported_event_ids == []
    assert journal.read_all() == []


# ----------------------------------------------------------------------
# T061 — a non-JSON queued payload migrates as raw bytes (no crash)
# ----------------------------------------------------------------------


def test_non_json_payload_migrates_as_raw_bytes(tmp_path: Path) -> None:
    home = tmp_path
    path = _scoped_path(home, "4444444444444444")
    _seed_queue(path, [_event("e_seed")])  # creates the real schema
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            "INSERT INTO queue (event_id, event_type, data, timestamp) VALUES (?, ?, ?, ?)",
            ("e_raw", "custom.event", "not-json{", 0),
        )
        conn.commit()
    finally:
        conn.close()
    journal = _journal(home)

    migrate_queues_to_journal(home, journal=journal)

    raw = journal.read_by_id("e_raw")
    assert raw is not None
    assert raw.payload == b"not-json{"
