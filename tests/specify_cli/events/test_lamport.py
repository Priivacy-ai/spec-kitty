"""Unit tests for Lamport logical clock."""

import pytest
from pathlib import Path
from specify_cli.events.lamport import LamportClock


def test_lamport_clock_increment(tmp_path, monkeypatch):
    """Test clock increments monotonically."""
    monkeypatch.setenv("HOME", str(tmp_path))

    clock = LamportClock("test-node")

    val1 = clock.increment()
    val2 = clock.increment()

    assert val2 == val1 + 1
    assert val1 == 1  # First increment from 0
    assert val2 == 2


def test_lamport_clock_update(tmp_path, monkeypatch):
    """Test update logic: max(local, received) + 1."""
    monkeypatch.setenv("HOME", str(tmp_path))

    clock = LamportClock("test-node")
    clock.increment()  # local = 1

    new_val = clock.update(5)  # max(1, 5) + 1 = 6
    assert new_val == 6
    assert clock.current() == 6


def test_lamport_clock_update_when_local_ahead(tmp_path, monkeypatch):
    """Test update when local clock is ahead of received clock."""
    monkeypatch.setenv("HOME", str(tmp_path))

    clock = LamportClock("test-node")
    clock.increment()  # local = 1
    clock.increment()  # local = 2
    clock.increment()  # local = 3

    new_val = clock.update(1)  # max(3, 1) + 1 = 4
    assert new_val == 4


def test_lamport_clock_persistence(tmp_path, monkeypatch):
    """Test clock value persists across instances."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # First instance
    clock1 = LamportClock("test-node")
    clock1.increment()
    clock1.increment()
    final_val = clock1.current()
    assert final_val == 2

    # Second instance (should load persisted value)
    clock2 = LamportClock("test-node")
    assert clock2.current() == 2


def test_lamport_clock_multi_node_support(tmp_path, monkeypatch):
    """Test multiple nodes can store clocks independently."""
    monkeypatch.setenv("HOME", str(tmp_path))

    clock1 = LamportClock("node-alice")
    clock2 = LamportClock("node-bob")

    clock1.increment()
    clock1.increment()
    clock2.increment()

    assert clock1.current() == 2
    assert clock2.current() == 1

    # Reload both nodes
    clock1_reload = LamportClock("node-alice")
    clock2_reload = LamportClock("node-bob")

    assert clock1_reload.current() == 2
    assert clock2_reload.current() == 1


def test_lamport_clock_current_does_not_increment(tmp_path, monkeypatch):
    """Test current() returns value without incrementing."""
    monkeypatch.setenv("HOME", str(tmp_path))

    clock = LamportClock("test-node")
    clock.increment()  # local = 1

    val1 = clock.current()
    val2 = clock.current()

    assert val1 == val2 == 1


def test_lamport_clock_initializes_to_zero(tmp_path, monkeypatch):
    """Test new clock starts at 0."""
    monkeypatch.setenv("HOME", str(tmp_path))

    clock = LamportClock("test-node")
    assert clock.current() == 0
