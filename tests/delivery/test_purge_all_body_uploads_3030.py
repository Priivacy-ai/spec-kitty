"""FR-017's fourth store: ``--all`` must be able to empty the body-upload queue.

``sync purge --all`` claimed to clear four stores and could not clear this one.
There was no ``purge_all_body_uploads``, and the per-project removal
(``OfflineBodyUploadQueue.remove_project_tasks``) **strips its argument** and returns
0 for a falsy one — so a row whose ``project_uuid`` is blank or whitespace-only was
reachable by *no selector at all*. The CLI detected that and reported it honestly
("NO selector currently reaches these rows"); these tests exist so the claim can
stop being true.

The store matters for the same reason it mattered for FR-016: it holds verbatim
``spec.md`` / ``plan.md`` / ``tasks/WP*.md`` text, and in this product a
``mission_slug`` is a client engagement name. Text nobody can attribute to a project
is exactly the text a total purge exists for.

**Widening ``remove_project_tasks`` was rejected** (operator, 2026-07-30): it is
shared by other callers, and a blank selector that matches everything is precisely
the hazard the frame purge had to guard against. So the total purge is its own
selector over the store this module already owns destructively — the same shape as
:func:`purge_all_events`, which is deliberately not the union of the per-project
selectors either.

Everything here drives a **real** ``OfflineBodyUploadQueue`` on a real SQLite file,
and every test asserts its own precondition first: a probe on this mission once
reported five clean results for a harness that had never run the code.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from specify_cli.delivery.retention import (
    PURGE_ALL_CONFIRMATION,
    PurgeNotConfirmedError,
    purge_all_body_uploads,
    purge_project_body_uploads,
)
from specify_cli.sync.body_queue import OfflineBodyUploadQueue
from specify_cli.sync.queue import OfflineQueue

pytestmark = [pytest.mark.fast]

UUID_X = "xxxxxxxx-0000-0000-0000-0000000000x1"
UUID_Y = "yyyyyyyy-0000-0000-0000-0000000000y1"


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


def _insert(queue: OfflineBodyUploadQueue, project_uuid: str, artifact_path: str) -> None:
    """Insert one queued body with a *verbatim* ``project_uuid``.

    Direct SQL rather than ``enqueue`` because the populations that matter here are
    the ones no public writer produces any more: ``''`` and ``'   '``. The column is
    ``NOT NULL``, so those two strings are the only unattributable forms a row can
    take.
    """
    conn = sqlite3.connect(queue.db_path)
    try:
        conn.execute(
            """INSERT INTO body_upload_queue
               (project_uuid, mission_slug, target_branch, mission_type,
                manifest_version, artifact_path, content_hash, hash_algorithm,
                content_body, size_bytes, retry_count, next_attempt_at, created_at)
               VALUES (?, '047-payroll', 'main', 'software-dev', '1', ?, ?, 'sha256',
                       '# Client engagement detail', 26, 0, 0.0, 0.0)""",
            (project_uuid, artifact_path, f"{project_uuid}-{artifact_path}"),
        )
        conn.commit()
    finally:
        conn.close()


def _rows(queue: OfflineBodyUploadQueue) -> list[str]:
    """The test's OWN read of the store, never the purge's report of itself."""
    conn = sqlite3.connect(queue.db_path)
    try:
        return [str(row[0]) for row in conn.execute("SELECT project_uuid FROM body_upload_queue")]
    finally:
        conn.close()


def _seed(queue: OfflineBodyUploadQueue) -> None:
    """Two attributable projects plus the two populations no selector could reach."""
    _insert(queue, UUID_X, "spec.md")
    _insert(queue, UUID_X, "plan.md")
    _insert(queue, UUID_Y, "spec.md")
    _insert(queue, "", "tasks/WP01-thing.md")
    _insert(queue, "   ", "tasks/WP02-thing.md")


# --------------------------------------------------------------------------- #
# The premise, measured rather than asserted from the issue text               #
# --------------------------------------------------------------------------- #


def test_the_per_project_selectors_cannot_empty_this_store(
    body_queue: OfflineBodyUploadQueue,
) -> None:
    """Why a total primitive is needed at all, proven against the real store.

    Run every census key through the sanctioned per-project removal — which is what
    the CLI's ``--all`` did before this primitive existed — and the blank and
    whitespace-only rows are still there. ``remove_project_tasks`` strips its
    argument and returns 0 for a falsy one, so ``''`` and ``'   '`` are the same
    unreachable row twice over.

    The two attributable projects going *is* this test's positive control: without
    it, a harness that never reached the store would report the same residue.
    """
    _seed(body_queue)
    assert len(_rows(body_queue)) == 5, "precondition: the store really was seeded"

    for key in sorted(body_queue.count_by_project()):
        purge_project_body_uploads(key, body_queue=body_queue, dry_run=False)

    assert sorted(_rows(body_queue)) == ["", "   "], (
        "the per-project union removed the attributable rows (control) and left "
        "exactly the population no selector reaches"
    )


# --------------------------------------------------------------------------- #
# FR-017: the total purge reaches every row                                     #
# --------------------------------------------------------------------------- #


def test_purge_all_empties_the_store_including_the_unreachable_rows(
    body_queue: OfflineBodyUploadQueue,
) -> None:
    _seed(body_queue)
    assert len(_rows(body_queue)) == 5

    result = purge_all_body_uploads(
        body_queue=body_queue, dry_run=False, confirmation=PURGE_ALL_CONFIRMATION
    )

    assert _rows(body_queue) == []
    assert result.removed == 5
    assert result.target_before == 5
    assert result.target_after == 0
    assert result.is_exact


def test_purge_all_on_an_empty_store_is_a_clean_zero(
    body_queue: OfflineBodyUploadQueue,
) -> None:
    """``0 removed`` must be a fact about the store, not about a refusal."""
    assert _rows(body_queue) == []

    result = purge_all_body_uploads(
        body_queue=body_queue, dry_run=False, confirmation=PURGE_ALL_CONFIRMATION
    )

    assert result.removed == 0
    assert result.target_before == 0
    assert result.is_exact


def test_there_is_no_other_project_to_have_a_differential_against(
    body_queue: OfflineBodyUploadQueue,
) -> None:
    """``--all``'s scope is the whole store, so "some other project" is empty.

    Reported as ``0`` and carrying no information — exactly as
    ``ProjectPurgeResult.other_project_journal_differential`` does for
    :func:`purge_all_events`. The load-bearing claim for a total purge is
    ``target_after == 0``, which :attr:`is_exact` asserts.
    """
    _seed(body_queue)

    result = purge_all_body_uploads(
        body_queue=body_queue, dry_run=False, confirmation=PURGE_ALL_CONFIRMATION
    )

    assert result.all_uploads is True
    assert result.other_project_differential == 0
    assert result.after == {}


# --------------------------------------------------------------------------- #
# Dry run is the default, and its prediction is the contract                    #
# --------------------------------------------------------------------------- #


def test_dry_run_is_the_default_and_deletes_nothing(
    body_queue: OfflineBodyUploadQueue,
) -> None:
    _seed(body_queue)
    before = sorted(_rows(body_queue))

    result = purge_all_body_uploads(body_queue=body_queue)

    assert result.dry_run is True
    assert result.removed == 0
    assert sorted(_rows(body_queue)) == before
    assert result.target_before == 5, "a preview that previews nothing is not a preview"
    assert result.is_exact


def test_the_dry_run_predicts_exactly_what_the_real_run_deletes(
    body_queue: OfflineBodyUploadQueue,
) -> None:
    """The one property that makes a dry run worth defaulting to.

    Compared as *numbers the operator was shown* against *rows that disappeared*,
    both read by this test from the store, not from the purge's own arithmetic.
    """
    _seed(body_queue)
    rows_before = len(_rows(body_queue))

    preview = purge_all_body_uploads(body_queue=body_queue)
    executed = purge_all_body_uploads(
        body_queue=body_queue, dry_run=False, confirmation=PURGE_ALL_CONFIRMATION
    )

    rows_after = len(_rows(body_queue))
    assert preview.target_before == rows_before - rows_after, (
        f"the dry run promised {preview.target_before} row(s) and "
        f"{rows_before - rows_after} actually disappeared"
    )
    assert preview.target_before == executed.removed
    assert preview.before == executed.before


def test_a_confirmed_dry_run_still_deletes_nothing(
    body_queue: OfflineBodyUploadQueue,
) -> None:
    """Confirmation authorises; it does not trigger. ``dry_run`` alone decides."""
    _seed(body_queue)
    before = sorted(_rows(body_queue))

    purge_all_body_uploads(
        body_queue=body_queue, dry_run=True, confirmation=PURGE_ALL_CONFIRMATION
    )

    assert sorted(_rows(body_queue)) == before


# --------------------------------------------------------------------------- #
# C-002: nothing reachable from an unattended code path                         #
# --------------------------------------------------------------------------- #


def test_an_unconfirmed_destructive_run_refuses_loudly(
    body_queue: OfflineBodyUploadQueue,
) -> None:
    """Raise, never return a zero-count result.

    A silent no-op is indistinguishable from "there was nothing to purge" — the
    reporting failure this mission keeps finding — and it would let a caller believe
    it had wiped a store it never opened.
    """
    _seed(body_queue)
    before = sorted(_rows(body_queue))

    with pytest.raises(PurgeNotConfirmedError):
        purge_all_body_uploads(body_queue=body_queue, dry_run=False)

    assert sorted(_rows(body_queue)) == before


def test_a_wrong_confirmation_phrase_refuses(
    body_queue: OfflineBodyUploadQueue,
) -> None:
    """A near-miss is a refusal. ``True``-ish is not the contract; the phrase is."""
    _seed(body_queue)
    before = sorted(_rows(body_queue))

    for attempt in (
        "yes",
        "PURGE",
        PURGE_ALL_CONFIRMATION.upper(),
        PURGE_ALL_CONFIRMATION + "!",
        " " + PURGE_ALL_CONFIRMATION,
    ):
        with pytest.raises(PurgeNotConfirmedError):
            purge_all_body_uploads(
                body_queue=body_queue, dry_run=False, confirmation=attempt
            )

    assert sorted(_rows(body_queue)) == before


def test_the_refusal_names_the_phrase_and_says_nothing_was_deleted(
    body_queue: OfflineBodyUploadQueue,
) -> None:
    """An operator who has to guess the phrase will guess ``--force`` instead."""
    _seed(body_queue)

    with pytest.raises(PurgeNotConfirmedError) as excinfo:
        purge_all_body_uploads(body_queue=body_queue, dry_run=False)

    message = str(excinfo.value)
    assert PURGE_ALL_CONFIRMATION in message
    assert "Nothing was deleted" in message


# --------------------------------------------------------------------------- #
# The identifier this module deletes through must be the store's own            #
# --------------------------------------------------------------------------- #


def test_the_table_this_module_deletes_from_is_the_one_the_queue_creates(
    body_queue: OfflineBodyUploadQueue,
) -> None:
    """A rename in ``sync/body_queue.py`` must be a red, not a silent no-op purge.

    ``retention.py`` writes this store directly — it is the sanctioned destructive
    owner, the same way it deletes journal rows through the journal's own canonical
    identifiers. The cost of that is a duplicated table name, so the duplication is
    pinned against the live schema rather than trusted.
    """
    from specify_cli.delivery.retention import _BODY_QUEUE_TABLE

    conn = sqlite3.connect(body_queue.db_path)
    try:
        tables = {
            str(row[0])
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        conn.close()

    assert _BODY_QUEUE_TABLE in tables


def test_the_purge_does_not_touch_the_event_queue_sharing_the_same_db_file(
    body_queue: OfflineBodyUploadQueue, tmp_path: Path
) -> None:
    """The body queue shares its SQLite file with the event offline queue.

    A ``DELETE`` scoped to the wrong table — or a ``DROP``/file removal — would take
    the queued *events* with it. Those are a different store with a different
    selector, and FR-017 clears them through the journal/ledger primitives, not this
    one.
    """
    events = OfflineQueue(db_path=tmp_path / "queue.db")
    conn = sqlite3.connect(events.db_path)
    try:
        conn.execute(
            "INSERT INTO queue (event_id, event_type, data, timestamp, retry_count)"
            " VALUES ('evt-1', 'mission.updated', '{}', 0, 0)"
        )
        conn.commit()
        seeded = int(conn.execute("SELECT COUNT(*) FROM queue").fetchone()[0])
    finally:
        conn.close()
    assert seeded == 1, "precondition: the shared DB file really holds an event row"
    _seed(body_queue)

    purge_all_body_uploads(
        body_queue=body_queue, dry_run=False, confirmation=PURGE_ALL_CONFIRMATION
    )

    conn = sqlite3.connect(events.db_path)
    try:
        assert int(conn.execute("SELECT COUNT(*) FROM queue").fetchone()[0]) == 1
    finally:
        conn.close()
    assert _rows(body_queue) == []
