"""T026: the body-upload queue belongs in the purge differential (#3030).

FR-016's ``sync purge --project X`` spans the journal and the delivery ledger.
NFR-006 makes that purge *exact*: "after purging project X, a differential row count
over all other projects is zero". SC-006 wants "100% of X removed and 0% of anything
else".

The body-upload queue is a **third** store holding X's data, and it is the one
holding verbatim ``spec.md`` / ``plan.md`` / ``tasks/WP*.md`` text rather than event
envelopes. It lives inside the offline-queue DB file
(``OfflineBodyUploadQueue(db_path=OfflineQueue().db_path)``), a file a journal+ledger
purge never opens. So a purge counted over journal+ledger alone can honestly report
"100% of X removed" while every one of X's queued documents is still on disk waiting
for the next ``sync now`` — a false remediation attestation on precisely the
artefacts the 2026-07-27 incident leaked.

These tests drive the real ``OfflineBodyUploadQueue`` on a real SQLite file, and the
premise (shared DB file, and a journal-side purge leaving bodies behind) is asserted
rather than assumed. WP08 owns the ``sync purge`` CLI; this pins the retention-layer
primitive it must call, and that primitive is exercisable without any CLI surface.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.retention import gc_payloads, purge_project_body_uploads
from specify_cli.event_journal import Event, EventJournal
from specify_cli.sync.body_queue import OfflineBodyUploadQueue
from specify_cli.sync.namespace import NamespaceRef
from specify_cli.sync.queue import OfflineQueue

pytestmark = [pytest.mark.fast]

UUID_X = "xxxxxxxx-0000-0000-0000-0000000000x1"
UUID_Y = "yyyyyyyy-0000-0000-0000-0000000000y1"
UUID_Z = "zzzzzzzz-0000-0000-0000-0000000000z1"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir(parents=True, exist_ok=True)


@pytest.fixture
def body_queue(tmp_path: Path) -> OfflineBodyUploadQueue:
    """A body queue on the shared offline-queue DB file, as production builds it."""
    db_path = tmp_path / "queue.db"
    OfflineQueue(db_path=db_path)
    return OfflineBodyUploadQueue(db_path=db_path)


def _enqueue(queue: OfflineBodyUploadQueue, project_uuid: str, artifact_path: str) -> None:
    content = f"# {artifact_path}\n\nClient engagement detail for {project_uuid}.\n"
    queue.enqueue(
        namespace=NamespaceRef(
            project_uuid=project_uuid,
            mission_slug="047-payroll",
            target_branch="main",
            mission_type="software-dev",
            manifest_version="1",
        ),
        artifact_path=artifact_path,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),  # noqa: TID251 — body-integrity checksum, the queue's own protocol field
        content_body=content,
        size_bytes=len(content.encode()),
    )


# --- the premise: a store the journal+ledger purge cannot see --------------


def test_the_body_queue_shares_the_offline_queue_db_file() -> None:
    """Why this store is a blind spot rather than an oversight.

    Production builds the body queue on the event offline queue's own DB path
    (``sync/routing.py:disable_checkout_sync``). Purging the journal and the ledger
    therefore cannot possibly touch it: it is not in either of those files.
    """
    events = OfflineQueue()
    bodies = OfflineBodyUploadQueue(db_path=events.db_path)

    assert bodies.db_path == events.db_path


def test_a_journal_side_purge_leaves_the_queued_document_bodies_behind(
    tmp_path: Path, body_queue: OfflineBodyUploadQueue
) -> None:
    """The false attestation, made observable.

    The only pre-existing destructive payload operation reclaims journal rows and
    reports on journal bytes. Run it to completion and project X's documents are
    still queued — so a purge report built from journal (and ledger) counts alone
    would say "100% removed" about a project whose ``spec.md`` is still on disk.
    """
    journal = EventJournal(tmp_path / "event_journal" / "journal.db")
    ledger = SqliteDeliveryLedger()
    at = "2026-07-27T00:00:00+00:00"
    journal.append(
        Event(
            event_id="E1",
            event_type="mission.update",
            payload=b"envelope",
            occurred_at=at,
            created_at=at,
        )
    )
    ledger.record_success("E1", "target-a")
    _enqueue(body_queue, UUID_X, "spec.md")

    result = gc_payloads(journal, ledger, known_target_ids=("target-a",))

    assert result.purged == ("E1",), "the journal side did reclaim everything it owns"
    assert body_queue.count_by_project() == {UUID_X: 1}, (
        "X's document body survived a purge that reports on journal payload bytes"
    )


# --- FR-016: dry-run by default -------------------------------------------


def test_purge_is_dry_run_by_default_and_removes_nothing(
    body_queue: OfflineBodyUploadQueue,
) -> None:
    """A destructive operation over confidential text defaults to reporting only."""
    _enqueue(body_queue, UUID_X, "spec.md")
    _enqueue(body_queue, UUID_X, "plan.md")
    _enqueue(body_queue, UUID_Y, "spec.md")

    result = purge_project_body_uploads(UUID_X, body_queue=body_queue)

    assert result.dry_run is True
    assert result.removed == 0
    assert result.target_before == 2, "it still reports exactly what would go"
    assert body_queue.count_by_project() == {UUID_X: 2, UUID_Y: 1}
    assert result.is_exact, "a dry run that changed nothing is an exact dry run"


# --- SC-006 / NFR-006: 100% of X, 0% of anything else ---------------------


def test_purge_removes_every_queued_body_of_the_target_project(
    body_queue: OfflineBodyUploadQueue,
) -> None:
    _enqueue(body_queue, UUID_X, "spec.md")
    _enqueue(body_queue, UUID_X, "plan.md")
    _enqueue(body_queue, UUID_X, "tasks/WP01-thing.md")

    result = purge_project_body_uploads(UUID_X, body_queue=body_queue, dry_run=False)

    assert result.removed == 3
    assert result.target_after == 0
    assert body_queue.size() == 0


def test_the_differential_over_every_other_project_is_zero(
    body_queue: OfflineBodyUploadQueue,
) -> None:
    """NFR-006 stated as a number the caller can print, not a claim it can make."""
    _enqueue(body_queue, UUID_X, "spec.md")
    _enqueue(body_queue, UUID_X, "plan.md")
    _enqueue(body_queue, UUID_Y, "spec.md")
    _enqueue(body_queue, UUID_Y, "tasks/WP01-thing.md")
    _enqueue(body_queue, UUID_Z, "research.md")

    result = purge_project_body_uploads(UUID_X, body_queue=body_queue, dry_run=False)

    assert result.other_project_differential == 0
    assert result.is_exact
    assert body_queue.count_by_project() == {UUID_Y: 2, UUID_Z: 1}


def test_a_project_with_no_queued_bodies_purges_cleanly(
    body_queue: OfflineBodyUploadQueue,
) -> None:
    """The common case for the incident's own projects once the drain refused them."""
    _enqueue(body_queue, UUID_Y, "spec.md")

    result = purge_project_body_uploads(UUID_X, body_queue=body_queue, dry_run=False)

    assert result.removed == 0
    assert result.target_before == 0
    assert result.is_exact
    assert body_queue.count_by_project() == {UUID_Y: 1}


# --- unattributable rows --------------------------------------------------


def test_rows_with_no_project_identity_are_counted_but_never_purged_by_project(
    body_queue: OfflineBodyUploadQueue,
) -> None:
    """They are in the census, so the report cannot silently disagree with the store.

    They are not swept by X's purge either: text that cannot be attributed to a
    project must not be deleted under another project's remediation. ``sync purge
    --all`` (FR-017) is where they belong.

    ``project_uuid`` is ``NOT NULL`` in the schema, so a blank string is the only
    unattributable form a row can actually take — hence the direct insert rather
    than a ``NULL``.
    """
    import sqlite3

    _enqueue(body_queue, UUID_X, "spec.md")
    conn = sqlite3.connect(body_queue.db_path)
    try:
        conn.execute(
            "INSERT INTO body_upload_queue (project_uuid, mission_slug, target_branch,"
            " mission_type, manifest_version, artifact_path, content_hash,"
            " hash_algorithm, content_body, size_bytes, retry_count, next_attempt_at,"
            " created_at, last_error)"
            " VALUES ('', '047-payroll', 'main', 'software-dev', '1', 'plan.md',"
            " 'deadbeef', 'sha256', '# Plan', 6, 0, 0.0, 1.0, NULL)"
        )
        conn.commit()
    finally:
        conn.close()

    result = purge_project_body_uploads(UUID_X, body_queue=body_queue, dry_run=False)

    assert result.before == {UUID_X: 1, "": 1}, "unattributable rows are visible"
    assert result.after == {"": 1}
    assert result.other_project_differential == 0
    assert result.is_exact


def test_a_blank_target_purges_nothing(body_queue: OfflineBodyUploadQueue) -> None:
    """No project id, no deletion — a blank argument is not a wildcard."""
    _enqueue(body_queue, UUID_X, "spec.md")

    result = purge_project_body_uploads("   ", body_queue=body_queue, dry_run=False)

    assert result.removed == 0
    assert body_queue.size() == 1
