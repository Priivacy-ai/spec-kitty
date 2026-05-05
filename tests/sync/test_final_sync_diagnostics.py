"""Regression tests for final-sync diagnostics."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.diagnostics import mark_invocation_succeeded, reset_for_invocation
from specify_cli.sync.batch import (
    FINAL_SYNC_RETRY_BACKOFF_SECONDS,
    BatchEventResult,
    BatchSyncResult,
    run_final_sync_with_retries,
)
from specify_cli.sync.diagnostics import (
    SyncDiagnosticCode,
    classify_sync_error,
    emit_sync_diagnostic,
    reset_emitted_codes,
)

pytestmark = pytest.mark.fast


@pytest.fixture(autouse=True)
def clear_dedup() -> Iterator[None]:
    reset_for_invocation()
    reset_emitted_codes()
    yield
    reset_for_invocation()
    reset_emitted_codes()


def _queued_service(tmp_path: Path) -> Any:
    from specify_cli.sync.background import BackgroundSyncService
    from specify_cli.sync.queue import OfflineQueue

    queue = OfflineQueue(db_path=tmp_path / "queue.db")
    queue.queue_event(
        {
            "event_id": "EVT000000000000000000000001",
            "event_type": "WPStatusChanged",
            "payload": {"wp_id": "WP05", "from_lane": "doing", "to_lane": "for_review"},
        }
    )
    cfg = MagicMock()
    cfg.get_server_url.return_value = "https://test.example.com"
    return BackgroundSyncService(queue=queue, config=cfg, sync_interval_seconds=300)


def test_sync_diagnostic_code_contract_has_five_members() -> None:
    assert list(SyncDiagnosticCode) == [
        SyncDiagnosticCode.LOCK_UNAVAILABLE,
        SyncDiagnosticCode.AUTH_REFRESH_IN_PROGRESS,
        SyncDiagnosticCode.WEBSOCKET_OFFLINE,
        SyncDiagnosticCode.EVENT_LOOP_UNAVAILABLE,
        SyncDiagnosticCode.SERVER_AUTH_FAILURE,
    ]


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (SyncDiagnosticCode.LOCK_UNAVAILABLE, "sync.final_sync_lock_unavailable"),
        (SyncDiagnosticCode.AUTH_REFRESH_IN_PROGRESS, "sync.auth_refresh_in_progress"),
        (SyncDiagnosticCode.WEBSOCKET_OFFLINE, "sync.websocket_offline"),
        (SyncDiagnosticCode.EVENT_LOOP_UNAVAILABLE, "sync.event_loop_unavailable"),
        (SyncDiagnosticCode.SERVER_AUTH_FAILURE, "sync.server_auth_failure"),
    ],
)
def test_diagnostic_codes_emit_to_stderr_only(
    code: SyncDiagnosticCode,
    expected: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    emit_sync_diagnostic(code, "diagnostic detail")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert expected in captured.err
    assert "fatal=false" in captured.err
    assert "sync_phase=final_sync" in captured.err


def test_deduplication_emits_once_for_same_code(
    capsys: pytest.CaptureFixture[str],
) -> None:
    emit_sync_diagnostic(SyncDiagnosticCode.LOCK_UNAVAILABLE, "first call")
    emit_sync_diagnostic(SyncDiagnosticCode.LOCK_UNAVAILABLE, "second call")

    captured = capsys.readouterr()
    assert captured.err.count("sync.final_sync_lock_unavailable") == 1


def test_deduplication_emits_once_across_mixed_codes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    emit_sync_diagnostic(SyncDiagnosticCode.LOCK_UNAVAILABLE, "lock held")
    emit_sync_diagnostic(SyncDiagnosticCode.AUTH_REFRESH_IN_PROGRESS, "auth refresh")

    captured = capsys.readouterr()
    assert captured.err.count("sync_diagnostic severity=warning") == 1


def test_classify_lock_error() -> None:
    assert classify_sync_error("lock unavailable") == SyncDiagnosticCode.LOCK_UNAVAILABLE
    assert classify_sync_error("lock timeout exceeded") == SyncDiagnosticCode.LOCK_UNAVAILABLE


def test_classify_auth_refresh() -> None:
    assert (
        classify_sync_error(
            "Another spec-kitty process is refreshing the auth session; retry in a moment"
        )
        == SyncDiagnosticCode.AUTH_REFRESH_IN_PROGRESS
    )


def test_classify_websocket_offline() -> None:
    assert classify_sync_error("websocket offline") == SyncDiagnosticCode.WEBSOCKET_OFFLINE
    assert classify_sync_error("ws offline") == SyncDiagnosticCode.WEBSOCKET_OFFLINE


def test_classify_event_loop_unavailable() -> None:
    assert (
        classify_sync_error("can't create new thread at interpreter shutdown")
        == SyncDiagnosticCode.EVENT_LOOP_UNAVAILABLE
    )


def test_classify_server_auth_failure() -> None:
    assert classify_sync_error("401 from server") == SyncDiagnosticCode.SERVER_AUTH_FAILURE
    assert classify_sync_error("token expired") == SyncDiagnosticCode.SERVER_AUTH_FAILURE


def test_final_sync_retry_backoff_exhaustion_emits_once(
    capsys: pytest.CaptureFixture[str],
) -> None:
    attempts = 0
    sleeps: list[float] = []

    def failing_sync() -> BatchSyncResult:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("websocket offline")

    result = run_final_sync_with_retries(failing_sync, sleep=sleeps.append)

    captured = capsys.readouterr()
    assert attempts == 3
    assert sleeps == [FINAL_SYNC_RETRY_BACKOFF_SECONDS, FINAL_SYNC_RETRY_BACKOFF_SECONDS]
    assert result.error_count == 1
    assert "sync.websocket_offline" in captured.err
    assert captured.err.count("sync_diagnostic severity=warning") == 1
    assert captured.out == ""


def test_final_sync_retry_success_suppresses_diagnostic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    attempts = 0
    sleeps: list[float] = []

    def eventually_successful_sync() -> BatchSyncResult:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            result = BatchSyncResult()
            result.error_count = 1
            result.error_messages.append("auth refresh in progress")
            return result
        return BatchSyncResult()

    result = run_final_sync_with_retries(eventually_successful_sync, sleep=sleeps.append)

    captured = capsys.readouterr()
    assert attempts == 3
    assert sleeps == [FINAL_SYNC_RETRY_BACKOFF_SECONDS, FINAL_SYNC_RETRY_BACKOFF_SECONDS]
    assert result.error_count == 0
    assert captured.out == ""
    assert captured.err == ""


def test_final_sync_unauthenticated_result_does_not_retry(
    capsys: pytest.CaptureFixture[str],
) -> None:
    attempts = 0
    sleeps: list[float] = []

    def unauthenticated_sync() -> BatchSyncResult:
        nonlocal attempts
        attempts += 1
        result = BatchSyncResult()
        result.error_count = 1
        result.error_messages.append("Not authenticated: no valid access token")
        result.event_results.append(
            BatchEventResult(
                event_id="EVT000000000000000000000001",
                status="rejected",
                error="Not authenticated: no valid access token",
                error_category="unauthenticated",
            )
        )
        return result

    result = run_final_sync_with_retries(unauthenticated_sync, sleep=sleeps.append)

    captured = capsys.readouterr()
    assert attempts == 1
    assert sleeps == []
    assert result.error_count == 1
    assert "diagnostic_code=sync.server_auth_failure" in captured.err
    assert captured.err.count("sync_diagnostic severity=warning") == 1
    assert captured.out == ""


def test_final_sync_failure_after_local_success_keeps_stdout_strict_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    service = _queued_service(tmp_path)

    print(json.dumps({"result": "success", "wp_id": "WP05"}))
    mark_invocation_succeeded()

    with (
        patch("specify_cli.sync.batch.time.sleep"),
        patch.object(service, "_perform_sync", side_effect=RuntimeError("network down")),
    ):
        service.stop()

    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed == {"result": "success", "wp_id": "WP05"}

    assert captured.err.count("sync_diagnostic severity=warning") == 1
    assert "diagnostic_code=sync.server_auth_failure" in captured.err
    assert "fatal=false" in captured.err
    assert "sync_phase=final_sync" in captured.err
    assert "network down" in captured.err
    assert "[red]" not in captured.err
    assert "[bold red]" not in captured.err
    assert "Connection failed" not in captured.err
    assert "sync_diagnostic" not in captured.out


def test_final_sync_auth_refresh_lock_retries_then_emits_once(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from specify_cli.auth.refresh_transaction import RefreshLockTimeoutError

    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    service = _queued_service(tmp_path)
    sleeps: list[float] = []
    mark_invocation_succeeded()

    with (
        patch(
            "specify_cli.sync.background._fetch_access_token_sync",
            side_effect=RefreshLockTimeoutError(),
        ) as fetch_token,
        patch("specify_cli.sync.batch.time.sleep", side_effect=sleeps.append),
    ):
        service.stop()

    captured = capsys.readouterr()
    assert fetch_token.call_count == 3
    assert sleeps == [FINAL_SYNC_RETRY_BACKOFF_SECONDS, FINAL_SYNC_RETRY_BACKOFF_SECONDS]
    assert captured.out == ""
    assert captured.err.count("sync_diagnostic severity=warning") == 1
    assert "diagnostic_code=sync.auth_refresh_in_progress" in captured.err
    assert "Another spec-kitty process is refreshing the auth session" in captured.err
    assert "fatal=false" in captured.err
    assert "sync_phase=final_sync" in captured.err


class _NeverAcquiredLock:
    def acquire(self, *, timeout: float) -> bool:
        assert timeout == 5.0
        return False

    def release(self) -> None:
        raise AssertionError("release must not be called when acquire() is False")


def test_final_sync_lock_diagnostic_is_deduped_per_invocation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    service = _queued_service(tmp_path)
    service._lock = _NeverAcquiredLock()
    mark_invocation_succeeded()

    service.stop()
    service.stop()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.count("diagnostic_code=sync.final_sync_lock_unavailable") == 1
    assert "fatal=false" in captured.err
    assert "sync_phase=final_sync" in captured.err
    assert "[red]" not in captured.err


class _ShutdownThread:
    daemon = False

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.daemon = bool(kwargs.get("daemon", False))

    def start(self) -> None:
        raise RuntimeError("can't create new thread at interpreter shutdown")

    def join(self, timeout: float | None = None) -> None:
        raise AssertionError("join must not run when start() fails")

    def is_alive(self) -> bool:
        return False


def test_interpreter_shutdown_final_sync_diagnostic_is_deduped(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    service = _queued_service(tmp_path)
    mark_invocation_succeeded()

    with patch("specify_cli.sync.background.threading.Thread", _ShutdownThread):
        service.stop()
        service.stop()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.count("diagnostic_code=sync.event_loop_unavailable") == 1
    assert "can't create new thread at interpreter shutdown" in captured.err
    assert "fatal=false" in captured.err
    assert "sync_phase=final_sync" in captured.err
    assert "[red]" not in captured.err
