"""Test for the orchestrator review state handling fix.

This test verifies that when a WP is in REVIEW status and its task completes,
the orchestrator properly restarts it to continue processing instead of
declaring a deadlock.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from specify_cli.orchestrator.config import OrchestratorConfig, WPStatus
from specify_cli.orchestrator.integration import _orchestration_main_loop
from specify_cli.orchestrator.state import OrchestrationRun, WPExecution


@pytest.fixture
def mock_repo_root(tmp_path):
    """Create a mock repository root."""
    return tmp_path


@pytest.fixture
def mock_feature_dir(tmp_path):
    """Create a mock feature directory with task files."""
    feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create WP1 task file (no dependencies)
    task_file = tasks_dir / "WP01-implementation.md"
    task_file.write_text("""---
work_package_id: WP01
title: WP1 Task
---

# WP1

Test work package 1.
""")

    # Create WP2 task file (no dependencies)
    task_file2 = tasks_dir / "WP02-implementation.md"
    task_file2.write_text("""---
work_package_id: WP02
title: WP2 Task
---

# WP2

Test work package 2.
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
    # WP2 starts as PENDING
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


@pytest.mark.asyncio
async def test_wp_in_review_status_gets_restarted(
    mock_state, mock_config, mock_feature_dir, mock_repo_root, mock_console
):
    """Test that WPs in REVIEW status without active tasks get restarted.

    This is the fix for the bug where:
    1. WP1 finishes implementation and enters REVIEW status
    2. The process_wp task completes (review phase done)
    3. WP1 is in REVIEW status but has no active task
    4. Orchestrator incorrectly declares deadlock and fails WP1

    After the fix:
    1. WP1 finishes implementation and enters REVIEW status
    2. Orchestrator detects WP1 is in REVIEW with no task
    3. Orchestrator restarts the task for WP1
    4. WP1 continues to COMPLETED
    """
    from specify_cli.orchestrator.scheduler import ConcurrencyManager

    # Create a dependency graph with no dependencies
    graph = {
        "WP01": [],
        "WP02": [],
    }

    # Track how many times each WP is processed
    process_count = {"WP01": 0, "WP02": 0}

    async def mock_process_wp(*args, **kwargs):
        wp_id = args[0] if args else kwargs.get("wp_id")
        state = kwargs.get("state") or args[1]
        wp = state.work_packages[wp_id]

        process_count[wp_id] += 1

        # First call: start implementation
        if wp.status in [WPStatus.PENDING, WPStatus.READY]:
            wp.status = WPStatus.IMPLEMENTATION
            wp.implementation_started = datetime.now(timezone.utc)
            wp.implementation_completed = datetime.now(timezone.utc)
            # Return - task completes, but WP is now in IMPLEMENTATION status
            # The orchestrator should restart it
            return True

        # Second call: should be in IMPLEMENTATION, transition to REVIEW then COMPLETED
        if wp.status == WPStatus.IMPLEMENTATION:
            wp.status = WPStatus.REVIEW
            wp.review_started = datetime.now(timezone.utc)
            wp.review_completed = datetime.now(timezone.utc)
            # Return - task completes, but WP is now in REVIEW status
            # The orchestrator should restart it
            return True

        # Third call: should be in REVIEW, complete it
        if wp.status == WPStatus.REVIEW:
            wp.status = WPStatus.COMPLETED
            state.wps_completed += 1
            return True

        return True

    # Track running tasks
    running_tasks = {}

    with patch("specify_cli.orchestrator.integration.process_wp", side_effect=mock_process_wp), \
         patch("specify_cli.orchestrator.integration.save_state"):

        iteration_count = 0
        max_iterations = 20

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

        assert wp1.status == WPStatus.COMPLETED, (
            f"WP1 should be COMPLETED, got {wp1.status.value}. "
            f"Process count: {process_count['WP01']}"
        )
        assert wp2.status == WPStatus.COMPLETED, (
            f"WP2 should be COMPLETED, got {wp2.status.value}. "
            f"Process count: {process_count['WP02']}"
        )

        # Each WP should have been processed multiple times
        # (once for implementation, once for review, once for completion)
        assert process_count["WP01"] >= 3, f"WP1 should be processed at least 3 times, got {process_count['WP01']}"
        assert process_count["WP02"] >= 3, f"WP2 should be processed at least 3 times, got {process_count['WP02']}"


@pytest.mark.asyncio
async def test_wp_in_implementation_status_gets_restarted(
    mock_state, mock_config, mock_feature_dir, mock_repo_root, mock_console
):
    """Test that WPs in IMPLEMENTATION status without active tasks get restarted.

    This ensures that if a WP is left in IMPLEMENTATION status (e.g., due to
    a crash or restart), it will be properly restarted.
    """
    from specify_cli.orchestrator.scheduler import ConcurrencyManager

    graph = {
        "WP01": [],
    }

    # Pre-set WP1 to IMPLEMENTATION status (simulating a resumed orchestration)
    mock_state.work_packages["WP01"].status = WPStatus.IMPLEMENTATION
    mock_state.work_packages["WP01"].implementation_started = datetime.now(timezone.utc)

    process_count = 0

    async def mock_process_wp(*args, **kwargs):
        nonlocal process_count
        wp_id = args[0] if args else kwargs.get("wp_id")
        state = kwargs.get("state") or args[1]
        wp = state.work_packages[wp_id]

        process_count += 1

        # Since WP is already in IMPLEMENTATION, it should transition to REVIEW then COMPLETED
        if wp.status == WPStatus.IMPLEMENTATION:
            wp.status = WPStatus.REVIEW
            wp.review_started = datetime.now(timezone.utc)
            wp.review_completed = datetime.now(timezone.utc)
            return True

        if wp.status == WPStatus.REVIEW:
            wp.status = WPStatus.COMPLETED
            state.wps_completed += 1
            return True

        return True

    running_tasks = {}

    with patch("specify_cli.orchestrator.integration.process_wp", side_effect=mock_process_wp), \
         patch("specify_cli.orchestrator.integration.save_state"):

        iteration_count = 0
        max_iterations = 10

        def is_shutdown():
            nonlocal iteration_count
            iteration_count += 1
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

        wp1 = mock_state.work_packages["WP01"]

        assert wp1.status == WPStatus.COMPLETED, (
            f"WP1 should be COMPLETED, got {wp1.status.value}"
        )
        assert process_count >= 2, f"WP1 should be processed at least 2 times, got {process_count}"
