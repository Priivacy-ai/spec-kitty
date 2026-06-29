"""ATDD acceptance tests for WP11 — status report assembly + GC/archive (IC-08).

These tests pin **observable JSON output and on-disk/ledger state** (NFR-001),
never internal call order or mock invocation sequence. They lock the contract
§6 "Required tests" plus SC-010 / SC-003 / US4 / NFR-004 / FR-010 / NFR-006 /
C-006:

* the seven additive JSON sections are present AND the old top-level fields are
  preserved unchanged (SC-010);
* the distinct counts (retained / current-target delivered / previous-target
  delivered / terminal-failed / body-upload) plus oldest retained timestamp are
  separate JSON values, not one number reused (SC-003, US4 scenario 1);
* the GC suggestion surfaces only when the journal is large AND fully delivered
  to all known targets, while journal size is *always* surfaced (NFR-004);
* GC/archive are explicit-operator-only and preserve delivery-ledger
  history/provenance (FR-010, contract §3); a ``sync now``-style path never
  triggers retention (US4 scenario 3);
* no status field implies body-upload rows are event-journal rows (NFR-006,
  C-006) — body-upload counts live only in ``body_upload_compatibility``.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import pytest

from specify_cli.delivery.retention import (
    RetentionResult,
    archive_payloads,
    gc_payloads,
)
from specify_cli.delivery.status_report import (
    ADDITIVE_SECTION_KEYS,
    BODY_UPLOAD_COMPAT_KEY,
    DELIVERY_LEDGER_KEY,
    DELIVERY_TARGETS_KEY,
    EVENT_JOURNAL_KEY,
    GC_LARGE_JOURNAL_THRESHOLD_BYTES,
    MIGRATION_CONFLICTS_KEY,
    TARGET_AUTHORITY_KEY,
    TERMINAL_FAILURES_KEY,
    build_status_report,
    default_status_sections,
    evaluate_gc_suggestion,
)
from specify_cli.delivery.targets import SqliteDeliveryTargetRegistry
from specify_cli.event_journal import Event, EventJournal
from specify_cli.sync.migrate_journal import MigrationAudit, MigrationConflict
from specify_cli.sync.target_authority import (
    OverrideMode,
    QueueScopeStatus,
    ResolvedSyncTarget,
)

pytestmark = pytest.mark.fast

CURRENT_URL = "https://current.example"
PREVIOUS_URL = "https://previous.example"
TEAM = "team-x"
USER = "user@example.com"


# ---------------------------------------------------------------------------
# Fixture builders (real domain objects, not mocks — NFR-001)
# ---------------------------------------------------------------------------


def _resolved(server_url: str = CURRENT_URL) -> ResolvedSyncTarget:
    """A descriptive resolved target for the ``target_authority`` section."""
    return ResolvedSyncTarget(
        configured_server_url=server_url,
        env_server_url=None,
        override_mode=OverrideMode.NONE,
        resolved_server_url=server_url,
        user_id=USER,
        team_slug=TEAM,
        derived_queue_scope="scope-current",
        queue_db_path=Path("queue.db"),
        active_queue_scope_status=QueueScopeStatus.ABSENT,
    )


def _event(event_id: str, *, payload: bytes = b"x", at: str = "2026-06-01T00:00:00+00:00") -> Event:
    return Event(
        event_id=event_id,
        event_type="mission.update",
        payload=payload,
        occurred_at=at,
        created_at=at,
    )


@pytest.fixture
def journal(tmp_path: Path) -> EventJournal:
    return EventJournal(tmp_path / "event_journal" / "journal.db")


@pytest.fixture
def ledger() -> object:
    from specify_cli.delivery.ledger import SqliteDeliveryLedger

    led = SqliteDeliveryLedger(":memory:")
    yield led
    led.close()


@pytest.fixture
def registry() -> object:
    reg = SqliteDeliveryTargetRegistry(":memory:")
    yield reg
    reg.close()


def _register(reg: object, url: str) -> object:
    return reg.register(url=url, team_slug=TEAM, user_email=USER)


def _legacy_base() -> dict[str, object]:
    """A representative pre-existing ``sync status --check --json`` payload."""
    return {
        "ok": True,
        "exit_code": 0,
        "foreground": {"package_version": "3.2.0", "queue_db_path": "/q/queue.db"},
        "daemon_owner_record": {"status": "absent"},
        "active_queue": {"path": "/q/queue.db", "event_count": 0, "body_upload_count": 0},
        "legacy_queue": {"path": "/q/legacy.db", "event_count": 0, "body_upload_count": 0, "rows_in_scope": 0},
        "mismatches": [],
        "orphan_records": [],
    }


def _insert_body_upload_row(db_path: Path) -> None:
    """Insert one queued body-upload row directly (test-only, raw SQL)."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO body_upload_queue
               (project_uuid, mission_slug, target_branch, mission_type,
                manifest_version, artifact_path, content_hash, hash_algorithm,
                content_body, size_bytes, retry_count, next_attempt_at, created_at, last_error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0.0, ?, NULL)""",
            ("p", "m", "main", "software-dev", "1", "a/b.md", "h", "sha256", "body", 4, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# default_status_sections — zero-state with all seven keys (single-sourced)
# ---------------------------------------------------------------------------


def test_default_status_sections_has_all_seven_keys() -> None:
    sections = default_status_sections()

    # Key set is single-sourced: exactly the exported additive keys, no drift.
    assert set(sections) == set(ADDITIVE_SECTION_KEYS)

    # Each section carries its empty/default shape (no missing keys, no None
    # sections) so a CLI fallback never emits a partial section.
    assert sections[TARGET_AUTHORITY_KEY] == {}
    assert sections[EVENT_JOURNAL_KEY] == {
        "retained_event_count": 0,
        "archived_event_count": 0,
        "oldest_retained_event_at": None,
        "journal_size_bytes": 0,
        "gc_suggested": False,
        "gc_suggestion": None,
    }
    assert sections[DELIVERY_TARGETS_KEY] == {"current": None, "previous": []}
    assert sections[DELIVERY_LEDGER_KEY] == {
        "delivered_current_target": 0,
        "delivered_previous_target": 0,
        "pending": 0,
        "rejected": 0,
        "transient": 0,
    }
    assert sections[MIGRATION_CONFLICTS_KEY] == {
        "count": 0,
        "cleanup_blocked": False,
        "conflicts": [],
    }
    assert sections[TERMINAL_FAILURES_KEY] == {"count": 0, "events": []}
    assert sections[BODY_UPLOAD_COMPAT_KEY] == {
        "body_upload_queue_count": 0,
        "body_upload_failure_log_count": 0,
    }

    # The zero-state is JSON-serializable (FR-019 round-trip) and a fresh dict
    # each call (no shared mutable default that a caller could mutate).
    assert json.loads(json.dumps(sections)) == sections
    default_status_sections()[TERMINAL_FAILURES_KEY]["events"].append("x")
    assert default_status_sections()[TERMINAL_FAILURES_KEY]["events"] == []


# ---------------------------------------------------------------------------
# SC-010 — seven additive sections present + old top-level fields preserved
# ---------------------------------------------------------------------------


def test_report_has_seven_sections_and_preserves_base(
    journal: EventJournal, ledger: object, registry: object
) -> None:
    base = _legacy_base()
    report = build_status_report(
        base=base,
        resolved_target=_resolved(),
        journal=journal,
        ledger=ledger,
        target_registry=registry,
    )

    # All seven additive sections present.
    for key in ADDITIVE_SECTION_KEYS:
        assert key in report, f"missing additive section {key!r}"
    assert set(ADDITIVE_SECTION_KEYS) == {
        TARGET_AUTHORITY_KEY,
        EVENT_JOURNAL_KEY,
        DELIVERY_TARGETS_KEY,
        DELIVERY_LEDGER_KEY,
        MIGRATION_CONFLICTS_KEY,
        TERMINAL_FAILURES_KEY,
        BODY_UPLOAD_COMPAT_KEY,
    }

    # Every old top-level field is preserved unchanged (additive only).
    for key, value in base.items():
        assert report[key] == value

    # The full payload is JSON-serializable (FR-019 round-trip).
    assert json.loads(json.dumps(report))


def test_target_authority_section_mirrors_resolved_target(
    journal: EventJournal, ledger: object, registry: object
) -> None:
    resolved = _resolved()
    report = build_status_report(
        resolved_target=resolved, journal=journal, ledger=ledger, target_registry=registry
    )
    assert report[TARGET_AUTHORITY_KEY] == resolved.to_diagnostics_dict()


# ---------------------------------------------------------------------------
# SC-003 / US4 scenario 1 — distinct counts
# ---------------------------------------------------------------------------


def test_distinct_counts_retained_previous_current(
    journal: EventJournal, ledger: object, registry: object
) -> None:
    previous = _register(registry, PREVIOUS_URL)
    _register(registry, CURRENT_URL)  # current target known but undelivered

    retained = 124
    for index in range(retained):
        event_id = f"evt-{index:03d}"
        journal.append(_event(event_id))
        ledger.record_success(event_id, previous.target_id)

    report = build_status_report(
        resolved_target=_resolved(CURRENT_URL),
        journal=journal,
        ledger=ledger,
        target_registry=registry,
    )

    journal_section = report[EVENT_JOURNAL_KEY]
    ledger_section = report[DELIVERY_LEDGER_KEY]

    assert journal_section["retained_event_count"] == 124
    assert ledger_section["delivered_previous_target"] == 124
    assert ledger_section["delivered_current_target"] == 0
    assert journal_section["oldest_retained_event_at"] is not None

    # The three numbers are genuinely distinct values, not one reused.
    assert journal_section["retained_event_count"] != ledger_section["delivered_current_target"]
    assert ledger_section["delivered_previous_target"] != ledger_section["delivered_current_target"]

    # The previous target is summarised distinctly from the current target.
    targets_section = report[DELIVERY_TARGETS_KEY]
    assert targets_section["current"]["target_id"] != previous.target_id
    previous_ids = {item["target_id"]: item for item in targets_section["previous"]}
    assert previous.target_id in previous_ids
    assert previous_ids[previous.target_id]["delivered_count"] == 124


# ---------------------------------------------------------------------------
# NFR-004 — GC suggestion gating; journal size always surfaced
# ---------------------------------------------------------------------------


def _fill(journal: EventJournal, ledger: object, target_id: str, *, count: int, deliver: int) -> None:
    for index in range(count):
        event_id = f"evt-{index}"
        journal.append(_event(event_id, payload=b"payload-bytes"))
        if index < deliver:
            ledger.record_success(event_id, target_id)


def test_gc_suggested_when_large_and_fully_delivered(
    journal: EventJournal, ledger: object, registry: object
) -> None:
    target = _register(registry, CURRENT_URL)
    _fill(journal, ledger, target.target_id, count=3, deliver=3)

    report = build_status_report(
        resolved_target=_resolved(),
        journal=journal,
        ledger=ledger,
        target_registry=registry,
        large_threshold_bytes=10,
    )
    section = report[EVENT_JOURNAL_KEY]
    assert section["gc_suggested"] is True
    assert section["gc_suggestion"] is not None
    assert section["journal_size_bytes"] > 0  # size unconditional


def test_gc_not_suggested_when_not_fully_delivered_but_size_shown(
    journal: EventJournal, ledger: object, registry: object
) -> None:
    target = _register(registry, CURRENT_URL)
    _fill(journal, ledger, target.target_id, count=3, deliver=2)  # one undelivered

    report = build_status_report(
        resolved_target=_resolved(),
        journal=journal,
        ledger=ledger,
        target_registry=registry,
        large_threshold_bytes=10,
    )
    section = report[EVENT_JOURNAL_KEY]
    assert section["gc_suggested"] is False
    assert section["gc_suggestion"] is None
    assert section["journal_size_bytes"] > 0  # size still surfaced


def test_gc_not_suggested_when_small_but_size_shown(
    journal: EventJournal, ledger: object, registry: object
) -> None:
    target = _register(registry, CURRENT_URL)
    _fill(journal, ledger, target.target_id, count=1, deliver=1)

    report = build_status_report(
        resolved_target=_resolved(),
        journal=journal,
        ledger=ledger,
        target_registry=registry,
        # default (large) threshold -> tiny journal is not "large"
    )
    section = report[EVENT_JOURNAL_KEY]
    assert section["gc_suggested"] is False
    assert "journal_size_bytes" in section


def test_gc_not_suggested_with_zero_known_targets(
    journal: EventJournal, ledger: object, registry: object
) -> None:
    # Events present and "large", but no delivery target configured/known.
    for index in range(3):
        journal.append(_event(f"evt-{index}", payload=b"payload-bytes"))

    report = build_status_report(
        resolved_target=_resolved(),
        journal=journal,
        ledger=ledger,
        target_registry=registry,
        large_threshold_bytes=10,
    )
    section = report[EVENT_JOURNAL_KEY]
    assert section["gc_suggested"] is False
    assert section["journal_size_bytes"] > 0


def test_evaluate_gc_suggestion_threshold_boundary() -> None:
    # Exactly-at-threshold is "large"; below is not. No targets -> never suggested.
    suggested, suggestion = evaluate_gc_suggestion(
        retained_event_ids=(),
        journal_size_bytes=GC_LARGE_JOURNAL_THRESHOLD_BYTES,
        ledger=object(),
        known_target_ids=(),
        large_threshold_bytes=GC_LARGE_JOURNAL_THRESHOLD_BYTES,
    )
    assert suggested is False
    assert suggestion is None


def test_delivery_ledger_non_terminal_counts(
    journal: EventJournal, ledger: object, registry: object
) -> None:
    target = _register(registry, CURRENT_URL)
    ledger.record_pending("evt-p", target.target_id)
    ledger.record_rejected("evt-r", target.target_id, error="bad content")
    ledger.record_transient("evt-t", target.target_id, error="5xx")

    report = build_status_report(
        resolved_target=_resolved(), journal=journal, ledger=ledger, target_registry=registry
    )
    section = report[DELIVERY_LEDGER_KEY]
    assert section["pending"] == 1
    assert section["rejected"] == 1
    assert section["transient"] == 1


def test_known_target_without_deliveries_is_not_listed_as_previous(
    journal: EventJournal, ledger: object, registry: object
) -> None:
    _register(registry, CURRENT_URL)
    previous = _register(registry, PREVIOUS_URL)
    unused = registry.register(url="https://unused.example", team_slug=TEAM, user_email=USER)
    journal.append(_event("evt-x"))
    ledger.record_success("evt-x", previous.target_id)

    report = build_status_report(
        resolved_target=_resolved(CURRENT_URL),
        journal=journal,
        ledger=ledger,
        target_registry=registry,
    )
    previous_ids = {item["target_id"] for item in report[DELIVERY_TARGETS_KEY]["previous"]}
    assert previous.target_id in previous_ids
    assert unused.target_id not in previous_ids  # zero deliveries -> not surfaced


def test_malformed_resolved_url_yields_unregistered_current(
    journal: EventJournal, ledger: object, registry: object
) -> None:
    report = build_status_report(
        resolved_target=_resolved("not-a-valid-url"),
        journal=journal,
        ledger=ledger,
        target_registry=registry,
    )
    current = report[DELIVERY_TARGETS_KEY]["current"]
    assert current["target_id"] is None
    assert current["canonical_url"] == "not-a-valid-url"


def test_evaluate_gc_suggestion_empty_retained_is_vacuously_delivered(ledger: object) -> None:
    suggested, suggestion = evaluate_gc_suggestion(
        retained_event_ids=(),
        journal_size_bytes=GC_LARGE_JOURNAL_THRESHOLD_BYTES,
        ledger=ledger,
        known_target_ids=("tgt-known",),
        large_threshold_bytes=10,
    )
    assert suggested is True
    assert suggestion is not None


# ---------------------------------------------------------------------------
# terminal_failures + migration_conflicts sections
# ---------------------------------------------------------------------------


def test_terminal_failures_inspectable(
    journal: EventJournal, ledger: object, registry: object
) -> None:
    target = _register(registry, CURRENT_URL)
    journal.append(_event("evt-oversized"))
    ledger.record_terminal_failed("evt-oversized", target.target_id, error="payload too large")

    report = build_status_report(
        resolved_target=_resolved(), journal=journal, ledger=ledger, target_registry=registry
    )
    section = report[TERMINAL_FAILURES_KEY]
    assert section["count"] == 1
    failure = section["events"][0]
    assert failure["event_id"] == "evt-oversized"
    assert failure["last_error"] == "payload too large"


def test_migration_conflicts_block_cleanup(
    journal: EventJournal, ledger: object, registry: object
) -> None:
    audit = MigrationAudit(":memory:")
    audit.record_conflict(
        MigrationConflict(
            event_id="evt-dup",
            source_digest="abc123",
            existing_sha="sha-existing",
            incoming_sha="sha-incoming",
            detail="divergent canonical payload",
        )
    )
    audit.commit()

    report = build_status_report(
        resolved_target=_resolved(),
        journal=journal,
        ledger=ledger,
        target_registry=registry,
        migration_audit=audit,
    )
    section = report[MIGRATION_CONFLICTS_KEY]
    assert section["count"] == 1
    assert section["cleanup_blocked"] is True
    assert section["conflicts"][0]["event_id"] == "evt-dup"


def test_migration_conflicts_section_present_when_none(
    journal: EventJournal, ledger: object, registry: object
) -> None:
    report = build_status_report(
        resolved_target=_resolved(), journal=journal, ledger=ledger, target_registry=registry
    )
    section = report[MIGRATION_CONFLICTS_KEY]
    assert section["count"] == 0
    assert section["cleanup_blocked"] is False
    assert section["conflicts"] == []


# ---------------------------------------------------------------------------
# NFR-006 / C-006 — body-upload separation
# ---------------------------------------------------------------------------


def test_body_upload_counts_only_in_compat_section(
    tmp_path: Path, journal: EventJournal, ledger: object, registry: object
) -> None:
    from specify_cli.sync.body_queue import OfflineBodyUploadQueue

    body_db = tmp_path / "queue.db"
    body_queue = OfflineBodyUploadQueue(db_path=body_db)
    _insert_body_upload_row(body_db)

    # Journal has a *different* number of events so a leak would be visible.
    for index in range(2):
        journal.append(_event(f"evt-{index}"))

    report = build_status_report(
        resolved_target=_resolved(),
        journal=journal,
        ledger=ledger,
        target_registry=registry,
        body_upload_queue=body_queue,
    )

    compat = report[BODY_UPLOAD_COMPAT_KEY]
    assert compat["body_upload_queue_count"] == 1
    assert compat["body_upload_failure_log_count"] == 0

    # Journal/ledger counts are sourced independently — no body-upload leak.
    assert report[EVENT_JOURNAL_KEY]["retained_event_count"] == 2
    journal_blob = json.dumps(report[EVENT_JOURNAL_KEY])
    ledger_blob = json.dumps(report[DELIVERY_LEDGER_KEY])
    assert "body_upload" not in journal_blob
    assert "body_upload" not in ledger_blob


# ---------------------------------------------------------------------------
# FR-010 / contract §3 — retention preserves ledger; explicit-only
# ---------------------------------------------------------------------------


def test_archive_marks_and_preserves_ledger(
    journal: EventJournal, ledger: object, registry: object
) -> None:
    target = _register(registry, CURRENT_URL)
    ids = ["evt-a", "evt-b", "evt-c"]
    for event_id in ids:
        journal.append(_event(event_id))
        ledger.record_success(event_id, target.target_id)

    result = archive_payloads(journal, event_ids=ids)
    assert isinstance(result, RetentionResult)
    assert result.archived_count == 3

    # Journal rows remain (archive is non-destructive) but carry the marker.
    for event_id in ids:
        stored = journal.read_by_id(event_id)
        assert stored is not None
        assert stored.archived_at is not None
        # Ledger provenance intact.
        assert ledger.get(event_id, target.target_id).status == "success"

    # Archived rows leave the "retained" surface.
    report = build_status_report(
        resolved_target=_resolved(), journal=journal, ledger=ledger, target_registry=registry
    )
    assert report[EVENT_JOURNAL_KEY]["retained_event_count"] == 0
    assert report[EVENT_JOURNAL_KEY]["archived_event_count"] == 3


def test_archive_is_idempotent(journal: EventJournal) -> None:
    journal.append(_event("evt-a"))
    first = archive_payloads(journal, event_ids=["evt-a"])
    second = archive_payloads(journal, event_ids=["evt-a"])
    assert first.archived_count == 1
    assert second.archived_count == 0
    assert "evt-a" in second.skipped


def test_gc_purges_delivered_preserves_undelivered_and_ledger(
    journal: EventJournal, ledger: object, registry: object
) -> None:
    target = _register(registry, CURRENT_URL)
    journal.append(_event("evt-delivered"))
    journal.append(_event("evt-undelivered"))
    ledger.record_success("evt-delivered", target.target_id)

    # P1-gc fix: gc reclaims only events delivered to ALL known targets, so the
    # target universe must be supplied (the prior delivered_anywhere purge would
    # have destroyed re-drainability to a not-yet-delivered target — FR-005).
    result = gc_payloads(journal, ledger, known_target_ids=[target.target_id])
    assert "evt-delivered" in result.purged
    assert "evt-undelivered" in result.skipped

    # Delivered payload reclaimed; undelivered payload preserved (durability).
    assert journal.read_by_id("evt-delivered") is None
    assert journal.read_by_id("evt-undelivered") is not None

    # Ledger history/provenance preserved (FR-010).
    assert ledger.get("evt-delivered", target.target_id).status == "success"


def test_archive_without_event_ids_scans_retained(journal: EventJournal) -> None:
    journal.append(_event("evt-a"))
    journal.append(_event("evt-b"))
    result = archive_payloads(journal)  # no explicit ids -> scan retained
    assert set(result.archived) == {"evt-a", "evt-b"}
    assert result.archived_count == 2


def test_gc_with_no_delivered_events_purges_nothing(
    journal: EventJournal, ledger: object
) -> None:
    journal.append(_event("evt-undelivered"))
    result = gc_payloads(journal, ledger)  # nothing delivered anywhere
    assert result.purged_count == 0
    assert result.skipped_count == 1
    assert journal.read_by_id("evt-undelivered") is not None


def test_sync_now_style_path_does_not_trigger_retention(
    journal: EventJournal, ledger: object, registry: object
) -> None:
    # Simulate a normal capture + deliver cycle (US4 scenario 3): no explicit
    # cleanup command is invoked, so no journal payload is ever deleted.
    target = _register(registry, CURRENT_URL)
    journal.append(_event("evt-keep"))
    ledger.record_success("evt-keep", target.target_id)

    assert journal.read_by_id("evt-keep") is not None
    assert journal.count() == 1


# ---------------------------------------------------------------------------
# Edge — empty journal report
# ---------------------------------------------------------------------------


def test_empty_journal_report(journal: EventJournal, ledger: object, registry: object) -> None:
    report = build_status_report(
        resolved_target=_resolved(), journal=journal, ledger=ledger, target_registry=registry
    )
    section = report[EVENT_JOURNAL_KEY]
    assert section["retained_event_count"] == 0
    assert section["archived_event_count"] == 0
    assert section["oldest_retained_event_at"] is None
    assert section["gc_suggested"] is False
    assert report[DELIVERY_TARGETS_KEY]["previous"] == []
