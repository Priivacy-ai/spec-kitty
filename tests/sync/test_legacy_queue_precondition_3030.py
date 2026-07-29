"""T007 precondition guard: unmigrated legacy rows must fail loudly (#3030 WP02).

WP02 removed the queue-backed event drain from the daemon (FR-012). That is safe
only for rows that already have a journal copy — ``_capture_to_journal`` runs
before every gate, so anything queued *after* journal capture landed is
recoverable. Rows that predate it are not: with the drain gone, nothing reads
them and nothing reports them. Silent stranding of undelivered events is exactly
the failure mode this mission exists to eliminate, so the daemon must refuse
loudly rather than discard.

These tests assert observable state (raised error, emitted log, converge
attempted) — never internal call order (NFR-001).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.sync.background import (
    BackgroundSyncService,
    LegacyQueueNotConvergedError,
)
from specify_cli.sync.config import SyncConfig

pytestmark = [pytest.mark.fast]


def _service(tmp_path: Path) -> BackgroundSyncService:
    from specify_cli.sync.queue import OfflineQueue

    return BackgroundSyncService(
        queue=OfflineQueue(db_path=tmp_path / "queue.db"),
        config=SyncConfig(),
    )


def test_converged_legacy_queue_starts_normally(tmp_path: Path) -> None:
    """Zero legacy rows: the guard passes silently."""
    service = _service(tmp_path)

    with patch("specify_cli.sync.background._count_legacy_event_rows", return_value=0):
        service._assert_legacy_queue_converged()  # must not raise


def test_unconverged_legacy_rows_fail_loudly(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Stranded rows must raise and be logged, not silently dropped."""
    import logging

    service = _service(tmp_path)

    with (
        patch("specify_cli.sync.background._count_legacy_event_rows", return_value=4),
        caplog.at_level(logging.ERROR),
        pytest.raises(LegacyQueueNotConvergedError) as excinfo,
    ):
        service._assert_legacy_queue_converged()

    # Loud: names the count and the operator's recovery command.
    assert "4" in str(excinfo.value)
    assert "sync migrate" in str(excinfo.value)
    assert any(record.levelno >= logging.ERROR for record in caplog.records)


def test_guard_does_not_mutate_the_operators_queues(tmp_path: Path) -> None:
    """T007 requires the migration; it must not silently run one.

    ``converge_legacy_runtime`` deletes journal-confirmed rows from the source
    queues. A background timer thread is the wrong place to do that unasked, so
    the daemon refuses and leaves recovery to explicit ``sync migrate``.
    """
    service = _service(tmp_path)

    with (
        patch("specify_cli.sync.background._count_legacy_event_rows", return_value=3),
        patch("specify_cli.sync.migrate_journal.converge_legacy_runtime") as mock_converge,
        pytest.raises(LegacyQueueNotConvergedError),
    ):
        service._assert_legacy_queue_converged()

    mock_converge.assert_not_called()


def test_an_uncountable_legacy_db_does_not_wedge_the_daemon(tmp_path: Path) -> None:
    """A broken legacy DB is a preflight concern, not a reason to refuse.

    Reporting "dirty" on an unrelated fault would strand body uploads too.
    """
    service = _service(tmp_path)

    with patch(
        "specify_cli.sync.queue.detect_legacy_rows_for_scope",
        side_effect=RuntimeError("malformed database"),
    ):
        service._assert_legacy_queue_converged()  # must not raise


def test_counter_reads_a_real_legacy_queue_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end over a real on-disk legacy queue — no counter stubbing.

    Every other test here patches ``_count_legacy_event_rows``, so a counter
    that always returned 0 (e.g. by raising into its own ``except``) would pass
    them all while the guard never fired. This one puts real rows on disk and
    asserts the guard actually refuses.
    """
    from specify_cli.paths import get_runtime_root
    from specify_cli.sync.background import _count_legacy_event_rows
    from specify_cli.sync.queue import OfflineQueue

    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    spec_kitty_dir = get_runtime_root().base
    spec_kitty_dir.mkdir(parents=True, exist_ok=True)

    legacy = OfflineQueue(db_path=spec_kitty_dir / "queue.db")
    legacy.queue_event({"event_id": "evt-legacy-001", "event_type": "Test", "payload": {}})
    legacy.queue_event({"event_id": "evt-legacy-002", "event_type": "Test", "payload": {}})

    assert _count_legacy_event_rows() == 2

    service = _service(tmp_path)
    with pytest.raises(LegacyQueueNotConvergedError) as excinfo:
        service._assert_legacy_queue_converged()
    assert "2" in str(excinfo.value)


def test_start_refuses_while_legacy_rows_are_stranded(tmp_path: Path) -> None:
    """The guard is wired into the daemon lifecycle, not merely available.

    Without this the guard could exist and never run — the precondition has to
    bind at the point the daemon would otherwise start ignoring the queue.
    """
    service = _service(tmp_path)

    with (
        patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True),
        patch("specify_cli.sync.background._count_legacy_event_rows", return_value=2),
        pytest.raises(LegacyQueueNotConvergedError),
    ):
        service.start()

    assert service.is_running is False
    assert service._timer is None
