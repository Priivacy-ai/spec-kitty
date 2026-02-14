"""pytest configuration for orchestrator e2e tests.

Provides fixtures and markers for testing the multi-agent orchestrator.

Markers:
    orchestrator_availability: Tests for agent availability detection
    orchestrator_fixtures: Tests for fixture loading and management
    orchestrator_happy_path: Happy path end-to-end tests
    orchestrator_review_cycles: Review rejection/approval cycle tests
    orchestrator_parallel: Parallel execution and dependency tests
    orchestrator_smoke: Basic smoke tests for agent invocation
    orchestrator_exception_handling: Exception handling and recovery tests
    orchestrator_deadlock_detection: Deadlock detection and prevention tests
    core_agent: Test requires core tier agent (fails if unavailable)
    extended_agent: Test for extended tier agent (skips if unavailable)
    slow: Test expected to take >30 seconds

Fixtures:
    available_agents: Session-scoped agent detection results
    available_agent_ids: List of authenticated agent IDs
    test_path: Selected TestPath based on available agents
    test_context_factory: Factory for creating TestContext from checkpoints
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Generator

import pytest

if TYPE_CHECKING:
    from specify_cli.orchestrator.testing.availability import AgentAvailability
    from specify_cli.orchestrator.testing.fixtures import TestContext
    from specify_cli.orchestrator.testing.paths import TestPath


# =============================================================================
# Agent Tier Definitions
# =============================================================================

# Core tier agents (tests fail if unavailable)
CORE_AGENTS = frozenset({
    "claude",
    "codex",
    "copilot",
    "gemini",
    "opencode",
})

# Extended tier agents (tests skip if unavailable)
EXTENDED_AGENTS = frozenset({
    "cursor",
    "qwen",
    "augment",
    "kilocode",
    "roo",
    "windsurf",
    "amazonq",
})


# =============================================================================
# T027: Custom Markers Registration
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for orchestrator tests."""
    # Availability detection markers
    config.addinivalue_line(
        "markers",
        "orchestrator_availability: tests for agent availability detection"
    )

    # Fixture markers
    config.addinivalue_line(
        "markers",
        "orchestrator_fixtures: tests for fixture loading and management"
    )

    # Test scenario markers
    config.addinivalue_line(
        "markers",
        "orchestrator_happy_path: happy path end-to-end tests"
    )
    config.addinivalue_line(
        "markers",
        "orchestrator_review_cycles: review rejection/approval cycle tests"
    )
    config.addinivalue_line(
        "markers",
        "orchestrator_parallel: parallel execution and dependency tests"
    )
    config.addinivalue_line(
        "markers",
        "orchestrator_smoke: basic smoke tests for agent invocation"
    )
    config.addinivalue_line(
        "markers",
        "orchestrator_exception_handling: exception handling and recovery tests"
    )
    config.addinivalue_line(
        "markers",
        "orchestrator_deadlock_detection: deadlock detection and prevention tests"
    )

    # Agent tier markers
    config.addinivalue_line(
        "markers",
        "core_agent: test requires core tier agent (fails if unavailable)"
    )
    config.addinivalue_line(
        "markers",
        "extended_agent: test for extended tier agent (skips if unavailable)"
    )

    # Performance markers
    config.addinivalue_line(
        "markers",
        "slow: test expected to take >30 seconds"
    )


# =============================================================================
# T028: Configuration Fixture
# =============================================================================


@pytest.fixture(scope="session")
def orchestrator_config():
    """Provide test configuration.

    Returns:
        OrchestratorTestConfig with values from environment
    """
    from tests.specify_cli.orchestrator.config import get_config
    return get_config()


# =============================================================================
# T028: Agent Availability Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def available_agents() -> dict[str, AgentAvailability]:
    """Detect all agents at session start.

    Returns:
        Dict mapping agent_id to AgentAvailability
    """
    from specify_cli.orchestrator.testing.availability import detect_all_agents

    # Run async detection in sync context
    loop = asyncio.new_event_loop()
    try:
        # detect_all_agents() returns dict[str, AgentAvailability]
        return loop.run_until_complete(detect_all_agents())
    finally:
        loop.close()


@pytest.fixture(scope="session")
def available_agent_ids(available_agents: dict[str, AgentAvailability]) -> list[str]:
    """List of agent IDs that are installed and authenticated.

    Returns:
        Sorted list of available agent IDs
    """
    return sorted([
        agent_id for agent_id, avail in available_agents.items()
        if avail.is_authenticated
    ])


@pytest.fixture(scope="session")
def core_agents_available(available_agents: dict[str, AgentAvailability]) -> list[str]:
    """List of available core tier agents."""
    return sorted([
        agent_id for agent_id, avail in available_agents.items()
        if avail.is_authenticated and agent_id in CORE_AGENTS
    ])


@pytest.fixture(scope="session")
def extended_agents_available(available_agents: dict[str, AgentAvailability]) -> list[str]:
    """List of available extended tier agents."""
    return sorted([
        agent_id for agent_id, avail in available_agents.items()
        if avail.is_authenticated and agent_id in EXTENDED_AGENTS
    ])


# =============================================================================
# T029: Test Path Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def test_path(available_agent_ids: list[str]) -> TestPath:
    """Select test path based on available agents.

    Automatically selects 1-agent, 2-agent, or 3+-agent path.

    Returns:
        TestPath with agent assignments

    Raises:
        pytest.skip: If no agents are available
    """
    from specify_cli.orchestrator.testing.paths import (
        clear_test_path_cache,
        select_test_path_sync,
    )

    if not available_agent_ids:
        pytest.skip("No agents available for testing")

    # Clear any cached path from previous sessions
    clear_test_path_cache()

    return select_test_path_sync()


@pytest.fixture
def forced_test_path() -> Generator:
    """Factory fixture to force a specific test path.

    Usage:
        @pytest.mark.parametrize("path_type", ["1-agent", "2-agent", "3+-agent"])
        def test_something(forced_test_path, path_type):
            path = forced_test_path(path_type)
    """
    from specify_cli.orchestrator.testing.paths import (
        TestPath,
        clear_test_path_cache,
        select_test_path_sync,
    )

    def _force_path(path_type: str) -> TestPath:
        clear_test_path_cache()
        return select_test_path_sync(force_path=path_type)

    yield _force_path

    # Cleanup: clear cache after test
    clear_test_path_cache()


@pytest.fixture
def require_2_agent_path(test_path: TestPath) -> None:
    """Skip test if not running 2-agent or 3+-agent path."""
    if test_path.path_type == "1-agent":
        pytest.skip("Test requires at least 2 agents")


@pytest.fixture
def require_3_agent_path(test_path: TestPath) -> None:
    """Skip test if not running 3+-agent path."""
    if test_path.path_type != "3+-agent":
        pytest.skip("Test requires at least 3 agents")


# =============================================================================
# T030: Test Context Fixtures
# =============================================================================


# Fixture checkpoint directory (relative to tests/fixtures/orchestrator/)
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "orchestrator"


def get_checkpoint_path(checkpoint_name: str) -> Path:
    """Get path to a checkpoint fixture directory.

    Args:
        checkpoint_name: Name of checkpoint (e.g., 'wp_created')

    Returns:
        Absolute path to checkpoint directory
    """
    return FIXTURES_DIR / f"checkpoint_{checkpoint_name}"


@pytest.fixture
def test_context_factory(
    test_path: TestPath,
    tmp_path: Path,
) -> Generator:
    """Factory fixture for creating test contexts from checkpoints.

    Returns a function that loads a checkpoint by name.

    Usage:
        def test_something(test_context_factory):
            ctx = test_context_factory("wp_created")
            # Use ctx...
    """
    import shutil

    from specify_cli.orchestrator.testing.fixtures import (
        FixtureCheckpoint,
        TestContext,
        load_worktrees_file,
    )

    contexts_to_cleanup: list[TestContext] = []

    def _create_context(checkpoint_name: str) -> TestContext:
        """Load a checkpoint and return TestContext."""
        checkpoint_path = get_checkpoint_path(checkpoint_name)

        if not checkpoint_path.exists():
            pytest.skip(f"Checkpoint fixture not found: {checkpoint_name}")

        checkpoint = FixtureCheckpoint(
            name=checkpoint_name,
            path=checkpoint_path,
            orchestrator_version="test",
            created_at=datetime.now(),
        )

        # Create isolated test directory
        test_dir = tmp_path / f"test_{checkpoint_name}"
        test_dir.mkdir(parents=True, exist_ok=True)

        # Copy feature directory from checkpoint to test dir
        feature_dir = test_dir / "feature"
        if checkpoint.feature_dir.exists():
            shutil.copytree(checkpoint.feature_dir, feature_dir)
        else:
            feature_dir.mkdir(parents=True, exist_ok=True)

        # Copy state.json to expected location
        state_file = feature_dir / ".orchestration-state.json"
        if checkpoint.state_file.exists():
            shutil.copy2(checkpoint.state_file, state_file)

        # Initialize git repo for tests that need it
        git_dir = test_dir / ".git"
        git_dir.mkdir(parents=True, exist_ok=True)

        # Load worktrees metadata
        worktrees = []
        if checkpoint.worktrees_file.exists():
            worktrees = load_worktrees_file(checkpoint.worktrees_file)

        ctx = TestContext(
            temp_dir=test_dir,
            repo_root=test_dir,
            feature_dir=feature_dir,
            test_path=test_path,
            checkpoint=checkpoint,
            orchestration_state=None,
            worktrees=worktrees,
        )
        contexts_to_cleanup.append(ctx)
        return ctx

    yield _create_context

    # Cleanup all created contexts
    for ctx in contexts_to_cleanup:
        _cleanup_test_context(ctx)


def _cleanup_test_context(ctx: TestContext) -> None:
    """Clean up a test context after test completion.

    Removes temporary directories and worktrees.

    Args:
        ctx: TestContext to clean up
    """
    import shutil

    try:
        if ctx.temp_dir.exists():
            shutil.rmtree(ctx.temp_dir, ignore_errors=True)
    except Exception:
        # Log but don't fail - cleanup is best effort
        pass


@pytest.fixture
def test_context_wp_created(test_context_factory) -> TestContext:
    """Pre-loaded test context at wp_created checkpoint."""
    return test_context_factory("wp_created")


@pytest.fixture
def test_context_wp_implemented(test_context_factory) -> TestContext:
    """Pre-loaded test context at wp_implemented checkpoint."""
    return test_context_factory("wp_implemented")


@pytest.fixture
def test_context_review_pending(test_context_factory) -> TestContext:
    """Pre-loaded test context at review_pending checkpoint."""
    return test_context_factory("review_pending")


@pytest.fixture
def test_context_review_rejected(test_context_factory) -> TestContext:
    """Pre-loaded test context at review_rejected checkpoint."""
    return test_context_factory("review_rejected")


@pytest.fixture
def test_context_review_approved(test_context_factory) -> TestContext:
    """Pre-loaded test context at review_approved checkpoint."""
    return test_context_factory("review_approved")


@pytest.fixture
def test_context_wp_merged(test_context_factory) -> TestContext:
    """Pre-loaded test context at wp_merged checkpoint."""
    return test_context_factory("wp_merged")
