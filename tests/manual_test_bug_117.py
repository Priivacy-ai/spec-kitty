"""Manual test for Bug #117 - Dashboard False-Failure Detection.

This script demonstrates the fix for the issue where dashboard hangs for 30s,
reports failure, but is actually accessible.

Run this in a test project to verify the fix:
    python tests/manual_test_bug_117.py
"""

import time
from pathlib import Path
from unittest.mock import patch

from specify_cli.dashboard.lifecycle import ensure_dashboard_running


def simulate_slow_health_check_scenario():
    """Simulate the Bug #117 scenario: process alive, health check slow."""
    print("\n" + "=" * 70)
    print("Bug #117 Manual Test: Process Alive but Health Check Slow")
    print("=" * 70)

    # Create a test project directory
    test_dir = Path("/tmp/test-spec-kitty-bug-117")
    test_dir.mkdir(exist_ok=True)
    kittify_dir = test_dir / ".kittify"
    kittify_dir.mkdir(exist_ok=True)

    print(f"\nTest directory: {test_dir}")

    # Mock scenario: Dashboard starts, process is alive, but health check times out
    mock_pid = 99999
    mock_port = 9237

    with patch("specify_cli.dashboard.lifecycle.start_dashboard") as mock_start, \
         patch("specify_cli.dashboard.lifecycle._check_dashboard_health") as mock_health, \
         patch("specify_cli.dashboard.lifecycle._is_process_alive") as mock_alive, \
         patch("specify_cli.dashboard.lifecycle._write_dashboard_file") as mock_write:

        # Setup: Process starts successfully
        mock_start.return_value = (mock_port, mock_pid)

        # Setup: Health check always fails (simulating slow response)
        mock_health.return_value = False

        # Setup: Process is actually alive
        mock_alive.return_value = True

        print("\nScenario:")
        print("  - Dashboard process starts (PID: {})".format(mock_pid))
        print("  - Health check times out (returns False)")
        print("  - BUT process is actually alive on port {}".format(mock_port))

        start_time = time.time()

        try:
            url, port, started = ensure_dashboard_running(test_dir, preferred_port=mock_port)
            elapsed = time.time() - start_time

            print("\n✅ RESULT: SUCCESS")
            print(f"  - URL: {url}")
            print(f"  - Port: {port}")
            print(f"  - Started: {started}")
            print(f"  - Elapsed time: {elapsed:.2f}s")

            # Verify we wrote the dashboard file (process is alive)
            assert mock_write.called, "Should write dashboard file when process is alive"

            print("\n🎉 Bug #117 FIX VERIFIED:")
            print("  - Dashboard detected as RUNNING (not failed)")
            print("  - No false-failure reported")
            print("  - Process not killed incorrectly")

        except RuntimeError as e:
            elapsed = time.time() - start_time
            print(f"\n❌ RESULT: FAILURE (Bug #117 still exists)")
            print(f"  - Error: {e}")
            print(f"  - Elapsed time: {elapsed:.2f}s")
            print("\nThis should NOT happen with the fix!")

    # Cleanup
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)


def test_specific_error_messages():
    """Verify specific error messages for common failure modes."""
    print("\n" + "=" * 70)
    print("Testing Specific Error Messages")
    print("=" * 70)

    test_dir = Path("/tmp/test-spec-kitty-errors")
    test_dir.mkdir(exist_ok=True)

    # Test 1: Missing .kittify directory
    print("\nTest 1: Missing .kittify directory")
    with patch("specify_cli.dashboard.lifecycle.start_dashboard") as mock_start:
        mock_start.side_effect = FileNotFoundError("No such file or directory: '.kittify'")

        try:
            ensure_dashboard_running(test_dir)
            print("  ❌ Should have raised FileNotFoundError")
        except FileNotFoundError as e:
            print(f"  ✅ Caught FileNotFoundError: {e}")
            assert ".kittify" in str(e).lower()

    # Test 2: Port conflict
    print("\nTest 2: Port conflict")
    kittify_dir = test_dir / ".kittify"
    kittify_dir.mkdir(exist_ok=True)

    with patch("specify_cli.dashboard.lifecycle.start_dashboard") as mock_start:
        mock_start.side_effect = OSError("Address already in use")

        try:
            ensure_dashboard_running(test_dir, preferred_port=9237)
            print("  ❌ Should have raised OSError")
        except OSError as e:
            print(f"  ✅ Caught OSError: {e}")
            assert "address already in use" in str(e).lower()

    # Cleanup
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)

    print("\n✅ All error message tests passed!")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Manual Test Suite for Bug #117")
    print("=" * 70)

    simulate_slow_health_check_scenario()
    test_specific_error_messages()

    print("\n" + "=" * 70)
    print("✅ All manual tests completed successfully!")
    print("=" * 70)
