"""Tests for orchestrator exception handling.

When a WP task raises an exception during processing, the orchestrator must:
1. Mark the WP as FAILED (not leave in intermediate state)
2. Record the exception in last_error
3. Allow dependent WPs to recognize the failure
4. Persist state so failure survives restart

Tests:
- T057: Exception marks WP as FAILED and unblocks dependents
- T058: Successful completion allows dependent WP to proceed (regression test)
- T062: Failed state persists across restart
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.orchestrator.config import OrchestratorConfig, WPStatus
from specify_cli.orchestrator.integration import _orchestration_main_loop
from specify_cli.orchestrator.state import OrchestrationRun, WPExecution, save_state, load_state


@pytest.fixture
def mock_repo_root(tmp_path):
    """Create a mock repository root."""
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def mock_feature_dir(tmp_path):
    """Create a mock feature directory with task files."""
    feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create WP1 task file
    task_file = tasks_dir / "WP01-implementation.md"
    task_file.write_text("""---
work_package_id: WP01
title: WP1 Task
---

# WP1

Test work package 1.
""")

    # Create WP2 task file (depends on WP1)
    task_file2 = tasks_dir / "WP02-dependent.md"
    task_file2.write_text("""---
work_package_id: WP02
title: WP2 Task
dependencies:
  - WP01
---

# WP2

Test work package 2 (depends on WP1).
""")

    return feature_dir


@pytest.fixture
def mock_state():
    """Create a mock orchestration state with WP1 and WP2."""
    state = OrchestrationRun(
        run_id="test-run-001",
        feature_slug="001-test-feature",
        started_at=datetime.now(timezone.utc),
    )
    # WP1 starts as PENDING
    state.work_packages["WP01"] = WPExecution(wp_id="WP01")
    # WP2 starts as PENDING (depends on WP1)
    state.work_packages["WP02"] = WPExecution(wp_id="WP02")
    state.wps_total = 2
    return state


@pytest.fixture
def mock_config():
    """Create a mock orchestrator config."""
    return OrchestratorConfig(
        global_timeout=300,
        max_retries=3,
        agents={
            "test-agent": MagicMock(enabled=True, max_concurrent=1),
        },
    )


@pytest.fixture
def mock_console():
    """Create a mock Rich console."""
    return MagicMock()


@pytest.mark.orchestrator_exception_handling
class TestExceptionHandling:
    """Tests for WP exception handling and failure recovery."""

    @pytest.mark.asyncio
    async def test_exception_in_task_marks_wp_as_failed(
        self, mock_state, mock_config, mock_feature_dir, mock_repo_root, mock_console
    ):
        """T057: Exception during processing marks WP as FAILED.

        Before the fix:
        - WP task raises exception
        - WP stays in IMPLEMENTATION status
        - Dependent WPs blocked with "No progress possible"

        After the fix:
        - WP task raises exception
        - WP marked FAILED immediately
        - Dependent WPs marked FAILED (blocked by failed dependency)
        """
        from specify_cli.orchestrator.scheduler import ConcurrencyManager

        # Create a dependency graph where WP2 depends on WP1
        graph = {
            "WP01": [],
            "WP02": ["WP01"],  # WP2 depends on WP1
        }

        # Mock process_wp to raise an exception for WP1
        async def mock_process_wp_that_raises(*args, **kwargs):
            wp_id = args[0] if args else kwargs.get("wp_id")
            state = kwargs.get("state") or args[1]
            wp = state.work_packages[wp_id]

            # Simulate that implementation started
            wp.status = WPStatus.IMPLEMENTATION
            wp.implementation_started = datetime.now(timezone.utc)

            # Then raise an exception (simulating agent crash, worktree error, etc.)
            raise RuntimeError(f"Simulated error in {wp_id}")

        # Track running tasks
        running_tasks = {}

        # Mock the process_wp function
        with patch("specify_cli.orchestrator.integration.process_wp", side_effect=mock_process_wp_that_raises), \
             patch("specify_cli.orchestrator.integration.save_state") as mock_save_state:

            # Set up shutdown condition - we'll let it run a few iterations then stop
            iteration_count = 0
            max_iterations = 5

            def is_shutdown():
                nonlocal iteration_count
                iteration_count += 1
                return iteration_count > max_iterations

            def update_display():
                pass

            # Create concurrency manager
            concurrency = ConcurrencyManager(mock_config)

            # Run the main loop
            await _orchestration_main_loop(
                state=mock_state,
                config=mock_config,
                graph=graph,
                feature_dir=mock_feature_dir,
                repo_root=mock_repo_root,
                concurrency=concurrency,
                console=mock_console,
                running_tasks=running_tasks,
                is_shutdown=is_shutdown,
                update_display=update_display,
            )

            # After the loop:
            # - WP1 should be FAILED (not still IMPLEMENTATION)
            # - WP2 should also be FAILED (blocked by failed dependency)

            wp1 = mock_state.work_packages["WP01"]
            wp2 = mock_state.work_packages["WP02"]

            # CRITICAL: WP1 must be FAILED, not IMPLEMENTATION
            assert wp1.status == WPStatus.FAILED, (
                f"BUG: WP1 status is {wp1.status.value}, expected FAILED. "
                f"This means the exception handler didn't mark it as failed."
            )

            # WP1 should have an error message
            assert wp1.last_error is not None, "WP1 should have a last_error set"
            assert "Simulated error" in wp1.last_error or "Task exception" in wp1.last_error, (
                f"WP1 last_error should contain exception info, got: {wp1.last_error}"
            )

            # WP2 should also be failed (blocked by WP1 failure)
            assert wp2.status == WPStatus.FAILED, (
                f"WP2 status is {wp2.status.value}, expected FAILED (blocked by WP1)."
            )

            # Verify save_state was called (to persist the failure)
            assert mock_save_state.called, "save_state should be called to persist failure status"

    @pytest.mark.asyncio
    async def test_successful_completion_allows_dependent_wp_to_start(
        self, mock_state, mock_config, mock_feature_dir, mock_repo_root, mock_console
    ):
        """T058: Successful completion allows dependent WP to proceed (regression test)."""
        from specify_cli.orchestrator.scheduler import ConcurrencyManager

        # Create a dependency graph where WP2 depends on WP1
        graph = {
            "WP01": [],
            "WP02": ["WP01"],  # WP2 depends on WP1
        }

        # Track which WPs were processed
        processed_wps = []

        async def mock_process_wp_that_succeeds(*args, **kwargs):
            wp_id = args[0] if args else kwargs.get("wp_id")
            state = kwargs.get("state") or args[1]
            wp = state.work_packages[wp_id]

            processed_wps.append(wp_id)

            # Simulate successful completion
            wp.status = WPStatus.COMPLETED
            wp.implementation_completed = datetime.now(timezone.utc)
            state.wps_completed += 1

            return True

        # Track running tasks
        running_tasks = {}

        with patch("specify_cli.orchestrator.integration.process_wp", side_effect=mock_process_wp_that_succeeds), \
             patch("specify_cli.orchestrator.integration.save_state"):

            iteration_count = 0
            max_iterations = 10

            def is_shutdown():
                nonlocal iteration_count
                iteration_count += 1
                # Stop when all WPs are done or max iterations reached
                all_done = all(
                    wp.status in [WPStatus.COMPLETED, WPStatus.FAILED]
                    for wp in mock_state.work_packages.values()
                )
                return all_done or iteration_count > max_iterations

            def update_display():
                pass

            concurrency = ConcurrencyManager(mock_config)

            await _orchestration_main_loop(
                state=mock_state,
                config=mock_config,
                graph=graph,
                feature_dir=mock_feature_dir,
                repo_root=mock_repo_root,
                concurrency=concurrency,
                console=mock_console,
                running_tasks=running_tasks,
                is_shutdown=is_shutdown,
                update_display=update_display,
            )

            # Both WPs should be completed
            wp1 = mock_state.work_packages["WP01"]
            wp2 = mock_state.work_packages["WP02"]

            assert wp1.status == WPStatus.COMPLETED, f"WP1 should be COMPLETED, got {wp1.status.value}"
            assert wp2.status == WPStatus.COMPLETED, f"WP2 should be COMPLETED, got {wp2.status.value}"

            # Both should have been processed
            assert "WP01" in processed_wps, "WP1 should have been processed"
            assert "WP02" in processed_wps, "WP2 should have been processed"

    @pytest.mark.asyncio
    async def test_failed_state_persists_across_restart(
        self, mock_state, mock_config, mock_feature_dir, mock_repo_root, mock_console
    ):
        """T062: Failed WP state should persist and be reloadable after restart."""
        from specify_cli.orchestrator.scheduler import ConcurrencyManager

        # Create a simple graph with just WP1
        graph = {"WP01": []}

        # Mock process_wp to raise an exception
        async def mock_process_wp_that_raises(*args, **kwargs):
            wp_id = args[0] if args else kwargs.get("wp_id")
            state = kwargs.get("state") or args[1]
            wp = state.work_packages[wp_id]

            wp.status = WPStatus.IMPLEMENTATION
            wp.implementation_started = datetime.now(timezone.utc)

            raise RuntimeError("Simulated error for persistence test")

        running_tasks = {}

        # Use real save_state (not mocked) so we can test persistence
        with patch("specify_cli.orchestrator.integration.process_wp", side_effect=mock_process_wp_that_raises):
            iteration_count = 0
            max_iterations = 5

            def is_shutdown():
                nonlocal iteration_count
                iteration_count += 1
                return iteration_count > max_iterations

            def update_display():
                pass

            concurrency = ConcurrencyManager(mock_config)

            await _orchestration_main_loop(
                state=mock_state,
                config=mock_config,
                graph=graph,
                feature_dir=mock_feature_dir,
                repo_root=mock_repo_root,
                concurrency=concurrency,
                console=mock_console,
                running_tasks=running_tasks,
                is_shutdown=is_shutdown,
                update_display=update_display,
            )

            # Verify WP1 is marked as FAILED
            wp1 = mock_state.work_packages["WP01"]
            assert wp1.status == WPStatus.FAILED
            assert wp1.last_error is not None

            # Save state to file
            state_file = mock_repo_root / ".kittify" / "orchestration-state.json"
            save_state(mock_state, mock_repo_root)

            # Verify file was created
            assert state_file.exists(), "State file should be created"

            # Load state in new instance
            reloaded = load_state(mock_repo_root)
            assert reloaded is not None, "State should be loadable"

            # Verify persistence
            reloaded_wp1 = reloaded.work_packages["WP01"]
            assert reloaded_wp1.status == WPStatus.FAILED, "Failed status should persist"
            assert reloaded_wp1.last_error is not None, "Error message should persist"
            assert "exception" in reloaded_wp1.last_error.lower() or "simulated error" in reloaded_wp1.last_error.lower(), \
                f"Error message should describe exception: {reloaded_wp1.last_error}"
