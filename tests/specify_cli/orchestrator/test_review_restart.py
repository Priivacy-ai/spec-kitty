"""Tests for orchestrator review state restart handling.

When a WP task completes but leaves the WP in REVIEW or IMPLEMENTATION status
(without reaching COMPLETED/FAILED), the orchestrator must detect this and
restart the WP to continue processing.

Tests:
- T059: WP in REVIEW status without active task gets restarted
- T060: WP in IMPLEMENTATION status without active task gets restarted
- T061: Process_wp restarts incomplete implementation before review
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from specify_cli.orchestrator.config import OrchestratorConfig, WPStatus
from specify_cli.orchestrator.integration import (
    ReviewResult,
    _orchestration_main_loop,
    process_wp,
)
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


@pytest.mark.orchestrator_deadlock_detection
class TestReviewStateRestart:
    """Tests for handling WPs stuck in review/implementation state."""

    @pytest.mark.asyncio
    async def test_wp_in_review_status_gets_restarted(
        self, mock_state, mock_config, mock_feature_dir, mock_repo_root, mock_console
    ):
        """T059: WP in REVIEW status without active task gets restarted.

        Before the fix:
        - WP finishes implementation, enters REVIEW status
        - Task completes (review phase done)
        - WP in REVIEW status but no active task
        - Orchestrator declares deadlock and fails WP

        After the fix:
        - WP finishes implementation, enters REVIEW status
        - Orchestrator detects WP in REVIEW with no task
        - Orchestrator restarts the task for WP
        - WP continues to COMPLETED
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
        self, mock_state, mock_config, mock_feature_dir, mock_repo_root, mock_console
    ):
        """T060: WP in IMPLEMENTATION status without active task gets restarted.

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

    @pytest.mark.asyncio
    async def test_process_wp_restarts_incomplete_implementation_before_review(
        self, mock_state, mock_config, mock_feature_dir, mock_repo_root, mock_console
    ):
        """T061: A resumed IMPLEMENTATION without completion should re-run implementation first."""
        from specify_cli.orchestrator.scheduler import ConcurrencyManager

        wp = mock_state.work_packages["WP01"]
        wp.status = WPStatus.IMPLEMENTATION
        wp.implementation_started = datetime.now(timezone.utc)
        wp.implementation_completed = None

        call_order = []

        async def mock_process_wp_implementation(*args, **kwargs):
            state = kwargs.get("state") or args[1]
            wp_id = args[0] if args else kwargs.get("wp_id")
            target_wp = state.work_packages[wp_id]
            call_order.append("implementation")
            target_wp.status = WPStatus.IMPLEMENTATION
            target_wp.implementation_started = target_wp.implementation_started or datetime.now(timezone.utc)
            target_wp.implementation_completed = datetime.now(timezone.utc)
            return True

        async def mock_process_wp_review(*args, **kwargs):
            state = kwargs.get("state") or args[1]
            wp_id = args[0] if args else kwargs.get("wp_id")
            target_wp = state.work_packages[wp_id]
            call_order.append("review")
            target_wp.status = WPStatus.REVIEW
            target_wp.review_started = datetime.now(timezone.utc)
            target_wp.review_completed = datetime.now(timezone.utc)
            return ReviewResult(ReviewResult.APPROVED)

        concurrency = ConcurrencyManager(mock_config)

        with patch(
            "specify_cli.orchestrator.integration.process_wp_implementation",
            side_effect=mock_process_wp_implementation,
        ), patch(
            "specify_cli.orchestrator.integration.process_wp_review",
            side_effect=mock_process_wp_review,
        ), patch(
            "specify_cli.orchestrator.integration.transition_wp_lane",
            new_callable=AsyncMock,
            return_value=True,
        ), patch(
            "specify_cli.orchestrator.integration.select_agent_from_user_config",
            return_value="test-agent",
        ), patch(
            "specify_cli.orchestrator.integration.select_review_agent_from_user_config",
            return_value="test-agent",
        ), patch(
            "specify_cli.orchestrator.integration.is_single_agent_mode",
            return_value=False,
        ), patch("specify_cli.orchestrator.integration.save_state"):
            result = await process_wp(
                wp_id="WP01",
                state=mock_state,
                config=mock_config,
                feature_dir=mock_feature_dir,
                repo_root=mock_repo_root,
                concurrency=concurrency,
                console=mock_console,
            )

        assert result is True
        assert call_order == ["implementation", "review"]
        assert wp.status == WPStatus.COMPLETED
