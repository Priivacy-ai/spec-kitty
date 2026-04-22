"""Tests for InvocationSaaSPropagator (WP07).

Verifies:
- Non-blocking submit() (< 50ms even with slow mock)
- No-op when _get_saas_client returns None (no error log written)
- Error logged to propagation-errors.jsonl on SaaS failure
- invocation_id present in the event dict passed to client.send_event
- _log_propagation_error swallows OSError (disk full)
"""

from __future__ import annotations

import asyncio
import json
import time
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.invocation.propagator import (
    InvocationSaaSPropagator,
    _IN_FLIGHT_TASKS,
    _log_propagation_error,
    _propagate_one,
)
from specify_cli.invocation.record import InvocationRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_started_record() -> InvocationRecord:
    return InvocationRecord(
        event="started",
        invocation_id="01KPQRX2EVGMRVB4Q1JQBAZJV3",
        profile_id="implementer-fixture",
        action="implement",
        request_text="implement the feature",
        started_at="2026-04-21T10:00:00Z",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_propagator_non_blocking(tmp_path: pytest.TempPathFactory) -> None:
    """submit() returns in < 50ms even if the SaaS call takes 500ms."""
    record = make_started_record()
    propagator = InvocationSaaSPropagator(tmp_path)

    with patch("specify_cli.invocation.propagator._get_saas_client") as mock_client_factory:
        mock_client = MagicMock()

        def slow_send(*args: object, **kwargs: object) -> None:  # noqa: ARG001
            time.sleep(0.5)

        mock_client.send_event.side_effect = slow_send
        mock_client_factory.return_value = mock_client

        start = time.monotonic()
        propagator.submit(record)
        elapsed = time.monotonic() - start

    assert elapsed < 0.05, f"submit() blocked for {elapsed:.3f}s"
    # Clean up: shut down background thread to avoid leaking threads across tests
    propagator._executor.shutdown(wait=False, cancel_futures=True)


def test_propagator_no_op_when_no_token(tmp_path: pytest.TempPathFactory) -> None:
    """When _get_saas_client returns None, no errors and no log entry."""
    record = make_started_record()

    with patch("specify_cli.invocation.propagator._get_saas_client", return_value=None):
        _propagate_one(record, tmp_path)

    error_log = tmp_path / ".kittify" / "events" / "propagation-errors.jsonl"
    assert not error_log.exists(), "Error log should not exist when client is None"


def test_propagator_logs_error_on_saas_failure(tmp_path: pytest.TempPathFactory) -> None:
    """SaaS failure (e.g. RuntimeError) → error logged to propagation-errors.jsonl, no exception."""
    record = make_started_record()

    with patch("specify_cli.invocation.propagator._get_saas_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.send_event.side_effect = RuntimeError("SaaS returned 503")
        mock_factory.return_value = mock_client

        # Must not raise
        _propagate_one(record, tmp_path)

    error_log = tmp_path / ".kittify" / "events" / "propagation-errors.jsonl"
    assert error_log.exists(), "propagation-errors.jsonl should be created on SaaS failure"

    entries = [json.loads(line) for line in error_log.read_text().splitlines() if line.strip()]
    assert len(entries) == 1
    assert "503" in entries[0]["error"]
    assert entries[0]["invocation_id"] == record.invocation_id


def test_propagator_sends_invocation_id_in_event_dict(tmp_path: pytest.TempPathFactory) -> None:
    """invocation_id is included in the event dict passed to client.send_event."""
    record = make_started_record()
    captured: list[dict[str, object]] = []

    with patch("specify_cli.invocation.propagator._get_saas_client") as mock_factory:
        mock_client = MagicMock()

        async def mock_send(event_dict: dict[str, object]) -> None:
            captured.append(event_dict)

        mock_client.send_event = mock_send
        mock_factory.return_value = mock_client

        # Must not raise
        _propagate_one(record, tmp_path)

    # Verify no error was logged (success path)
    error_log = tmp_path / ".kittify" / "events" / "propagation-errors.jsonl"
    assert not error_log.exists(), "No error log should be written on success"

    # The invocation_id must appear in the captured event dict
    assert len(captured) == 1
    assert captured[0]["invocation_id"] == record.invocation_id
    assert captured[0]["event_type"] == "ProfileInvocationStarted"


def test_propagator_tracks_fire_and_forget_tasks(tmp_path: pytest.TempPathFactory) -> None:
    """Tasks scheduled on a running loop stay referenced until completion."""
    record = make_started_record()
    captured: list[dict[str, object]] = []

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        async def mock_send(event_dict: dict[str, object]) -> None:
            captured.append(event_dict)

        class MockClient:
            send_event = staticmethod(mock_send)

        with patch("specify_cli.invocation.propagator._get_saas_client", return_value=MockClient()):
            running_loop = MagicMock()
            running_loop.is_running.return_value = True

            with patch("specify_cli.invocation.propagator.asyncio.get_event_loop", return_value=running_loop):
                _propagate_one(record, tmp_path)
                assert len(_IN_FLIGHT_TASKS) == 1
                loop.run_until_complete(asyncio.gather(*tuple(_IN_FLIGHT_TASKS)))
                loop.run_until_complete(asyncio.sleep(0))

        assert captured[0]["invocation_id"] == record.invocation_id
        assert not _IN_FLIGHT_TASKS
    finally:
        asyncio.set_event_loop(None)
        loop.close()


def test_propagator_error_log_never_raises_on_disk_full(tmp_path: pytest.TempPathFactory) -> None:
    """If propagation error log itself fails (disk full), no exception raised."""
    record = make_started_record()

    # Patch open() to raise OSError simulating a full disk
    with patch("builtins.open", side_effect=OSError("disk full")):
        # Must not raise
        _log_propagation_error(tmp_path, record, "test error")
