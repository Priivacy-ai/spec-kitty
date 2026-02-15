"""Test cross-platform compatibility (file locking, imports)."""

import pytest
import sys
from pathlib import Path


def test_store_module_imports():
    """Test that store.py imports successfully on both POSIX and Windows."""
    # This test verifies the fix for cross-platform file locking imports
    try:
        from specify_cli.events import store
        assert hasattr(store, 'append_event'), "append_event function should exist"
        assert hasattr(store, '_lock_file'), "Cross-platform _lock_file should exist"
        assert hasattr(store, '_unlock_file'), "Cross-platform _unlock_file should exist"
    except ImportError as e:
        pytest.fail(f"Failed to import store module: {e}")


def test_lamport_module_imports():
    """Test that lamport.py imports successfully on both POSIX and Windows."""
    # This test verifies the fix for cross-platform file locking imports
    try:
        from specify_cli.events import lamport
        assert hasattr(lamport, 'LamportClock'), "LamportClock class should exist"
        assert hasattr(lamport, '_lock_file'), "Cross-platform _lock_file should exist"
        assert hasattr(lamport, '_unlock_file'), "Cross-platform _unlock_file should exist"
    except ImportError as e:
        pytest.fail(f"Failed to import lamport module: {e}")


def test_file_locking_works(tmp_path):
    """Test that file locking works correctly on current platform."""
    from specify_cli.events.store import _lock_file, _unlock_file

    test_file = tmp_path / "lock_test.txt"
    test_file.write_text("test")

    # Test that we can lock and unlock without errors
    with open(test_file, "r") as f:
        _lock_file(f)
        # If we get here, lock was acquired
        _unlock_file(f)
        # If we get here, lock was released


def test_lamport_clock_persists_on_current_platform(tmp_path, monkeypatch):
    """Test that Lamport clock persistence works on current platform."""
    from specify_cli.events.lamport import LamportClock

    # Override home directory to use tmp_path
    monkeypatch.setenv("HOME", str(tmp_path))

    # Create clock and increment
    clock = LamportClock("test-node")
    value1 = clock.increment()
    assert value1 == 1

    # Create new instance (should load persisted value)
    clock2 = LamportClock("test-node")
    assert clock2.current() == 1

    # Increment again
    value2 = clock2.increment()
    assert value2 == 2
