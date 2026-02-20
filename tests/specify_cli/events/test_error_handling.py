"""Test error handling in event storage."""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, mock_open, MagicMock
from specify_cli.events.store import append_event, get_queue_path
from specify_cli.spec_kitty_events.models import Event


@pytest.fixture
def sample_event():
    """Create a sample event for testing."""
    return Event(
        event_id="01H0X123456789ABCDEFGHJKMN",
        event_type="agent_joined",
        timestamp=datetime.now(),
        mission_id="test-mission",
        aggregate_id="test-aggregate",
        node_id="test-node",
        lamport_clock=1,
        causation_id=None,
        actor_id="test-actor",
        payload={}
    )


def test_append_event_retries_on_transient_io_error(tmp_path, monkeypatch, sample_event):
    """Test that append_event retries on transient I/O errors."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Mock open to fail once, then succeed
    call_count = 0
    original_open = open

    def mock_open_with_retry(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise IOError("Simulated transient I/O error")
        return original_open(*args, **kwargs)

    with patch('builtins.open', side_effect=mock_open_with_retry):
        # This should succeed after retry
        append_event("test-mission", sample_event, replay_status="pending")

    # Verify retry happened (called twice: 1 failure + 1 success)
    assert call_count == 2


def test_append_event_fails_after_max_retries(tmp_path, monkeypatch, sample_event):
    """Test that append_event fails after max retries on persistent I/O errors."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Mock open to always fail
    with patch('builtins.open', side_effect=IOError("Persistent I/O error")):
        with pytest.raises(IOError) as exc_info:
            append_event("test-mission", sample_event, replay_status="pending")

        # Verify error message is helpful
        assert "Failed to write event" in str(exc_info.value)
        assert "after 2 attempts" in str(exc_info.value)
        assert sample_event.event_id in str(exc_info.value)


def test_append_event_raises_permission_error_immediately(tmp_path, monkeypatch, sample_event):
    """Test that append_event raises PermissionError immediately (no retries)."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Mock open to raise PermissionError
    with patch('builtins.open', side_effect=PermissionError("No write permission")):
        with pytest.raises(PermissionError) as exc_info:
            append_event("test-mission", sample_event, replay_status="pending")

        # Verify error message is helpful
        assert "Cannot write to queue file" in str(exc_info.value)
        assert "Check file permissions" in str(exc_info.value)


def test_append_event_handles_mkdir_permission_error(tmp_path, monkeypatch, sample_event):
    """Test that append_event handles permission errors when creating directories."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Mock Path.mkdir to raise PermissionError
    with patch.object(Path, 'mkdir', side_effect=PermissionError("Cannot create directory")):
        with pytest.raises(PermissionError) as exc_info:
            append_event("test-mission", sample_event, replay_status="pending")

        # Verify error message is helpful
        assert "Cannot create queue directory" in str(exc_info.value)
        assert "Check permissions on ~/.spec-kitty" in str(exc_info.value)


def test_append_event_continues_on_chmod_error(tmp_path, monkeypatch, sample_event):
    """Test that append_event continues if chmod fails (non-fatal)."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Create queue directory
    queue_dir = tmp_path / ".spec-kitty"
    queue_dir.mkdir(parents=True, exist_ok=True)

    # Mock Path.chmod to raise PermissionError (should be non-fatal)
    with patch.object(Path, 'chmod', side_effect=PermissionError("Cannot change permissions")):
        # This should succeed despite chmod failure
        try:
            append_event("test-mission", sample_event, replay_status="pending")
        except PermissionError:
            pytest.fail("append_event should not fail on chmod error")

    # Verify event was written despite chmod failure
    queue_path = get_queue_path("test-mission")
    assert queue_path.exists()
    assert queue_path.read_text().strip() != ""
