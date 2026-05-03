"""Final-sync diagnostics preserve local success output."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.diagnostics import mark_invocation_succeeded, reset_for_invocation

pytestmark = pytest.mark.fast


@pytest.fixture(autouse=True)
def _reset_diagnostics():
    reset_for_invocation()
    yield
    reset_for_invocation()


def _queued_service(tmp_path: Path):
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


def test_final_sync_failure_after_local_success_keeps_stdout_strict_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A final-sync exception is a stderr diagnostic, not a JSON stdout contaminant."""
    service = _queued_service(tmp_path)

    print(json.dumps({"result": "success", "wp_id": "WP05"}))
    mark_invocation_succeeded()

    with patch.object(service, "_perform_sync", side_effect=RuntimeError("network down")):
        service.stop()

    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed == {"result": "success", "wp_id": "WP05"}

    assert "sync_diagnostic" in captured.err
    assert "severity=warning" in captured.err
    assert "diagnostic_code=sync.final_sync_failed" in captured.err
    assert "fatal=false" in captured.err
    assert "sync_phase=final_sync" in captured.err
    assert "network down" in captured.err
    assert "[red]" not in captured.err
    assert "sync_diagnostic" not in captured.out


def test_final_sync_failure_after_text_local_success_uses_structured_diagnostic(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Text commands get structured final-sync diagnostics without JSON success flags."""
    service = _queued_service(tmp_path)

    print("Moved WP05 to for_review")

    with patch.object(service, "_perform_sync", side_effect=RuntimeError("network down")):
        service.stop()

    captured = capsys.readouterr()
    assert captured.out == "Moved WP05 to for_review\n"

    assert "sync_diagnostic" in captured.err
    assert "severity=warning" in captured.err
    assert "diagnostic_code=sync.final_sync_failed" in captured.err
    assert "fatal=false" in captured.err
    assert "sync_phase=final_sync" in captured.err
    assert "network down" in captured.err
    assert "[red]" not in captured.err
    assert "sync_diagnostic" not in captured.out


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
    """Repeated lock-contention shutdown messages render once per invocation."""
    service = _queued_service(tmp_path)
    service._lock = _NeverAcquiredLock()  # type: ignore[assignment]
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
    """Repeated interpreter-shutdown final-sync failures render once."""
    from specify_cli.sync import background as background_module

    service = _queued_service(tmp_path)
    mark_invocation_succeeded()

    with patch.object(background_module.threading, "Thread", _ShutdownThread):
        service.stop()
        service.stop()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.count("diagnostic_code=sync.final_sync_shutdown_unavailable") == 1
    assert "can't create new thread at interpreter shutdown" in captured.err
    assert "fatal=false" in captured.err
    assert "sync_phase=final_sync" in captured.err
    assert "[red]" not in captured.err
