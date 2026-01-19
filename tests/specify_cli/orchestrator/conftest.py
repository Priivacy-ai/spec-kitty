"""Pytest fixtures for orchestrator tests.

This module provides fixtures for agent availability detection
used by smoke tests and other orchestrator e2e tests.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from specify_cli.orchestrator.testing.availability import AgentAvailability

from tests.specify_cli.orchestrator.config import OrchestratorTestConfig, get_config

# Re-export constants from availability module for test convenience
from specify_cli.orchestrator.testing.availability import CORE_AGENTS, EXTENDED_AGENTS

# Re-export helpers from fixture module
from tests.fixtures.orchestrator import get_checkpoint_path
from specify_cli.orchestrator.testing.fixtures import cleanup_test_context as _cleanup_test_context


# =============================================================================
# Custom skip reasons for better reporting
# =============================================================================


class OrchestratorSkipReasons:
    """Standard skip reasons for orchestrator tests."""

    @staticmethod
    def agent_not_available(agent_id: str, reason: str | None = None) -> str:
        """Format skip reason for unavailable agent."""
        if reason:
            return f"Agent '{agent_id}' not available: {reason}"
        return f"Agent '{agent_id}' not available"

    @staticmethod
    def insufficient_agents(required: int, available: int) -> str:
        """Format skip reason for insufficient agents."""
        return f"Test requires {required} agents, only {available} available"

    @staticmethod
    def fixture_not_found(fixture_name: str) -> str:
        """Format skip reason for missing fixture."""
        return f"Fixture '{fixture_name}' not found"

    @staticmethod
    def prerequisite_failed(wp_id: str) -> str:
        """Format skip reason when prerequisite WP failed."""
        return f"Prerequisite WP '{wp_id}' failed"


# Make available to tests
skip_reasons = OrchestratorSkipReasons()


def skip_if_agent_unavailable(
    agent_id: str, available_agents: dict, tier: str = "any"
):
    """Skip test if agent is unavailable.

    Args:
        agent_id: Agent to check
        available_agents: Dict from fixture
        tier: 'core' (fail), 'extended' (skip), or 'any' (skip)
    """
    from specify_cli.orchestrator.testing.availability import CORE_AGENTS

    avail = available_agents.get(agent_id)

    if avail is None or not avail.is_available:
        reason = avail.failure_reason if avail else "Not detected"

        if tier == "core" or (tier == "any" and agent_id in CORE_AGENTS):
            # Core agents should fail, not skip
            pytest.fail(skip_reasons.agent_not_available(agent_id, reason))
        else:
            pytest.skip(skip_reasons.agent_not_available(agent_id, reason))


# =============================================================================
# Session-scoped fixtures
# =============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def orchestrator_config() -> OrchestratorTestConfig:
    """Provide test configuration."""
    return get_config()


@pytest.fixture(scope="session")
def available_agents(event_loop) -> dict[str, "AgentAvailability"]:
    """Detect which agents are available on the system.

    This fixture runs once per session and caches the results.

    Returns:
        Dict mapping agent_id to AgentAvailability for all 12 agents
    """
    from specify_cli.orchestrator.testing.availability import detect_all_agents

    # Run async detection in the event loop
    agents = event_loop.run_until_complete(detect_all_agents())
    return agents


@pytest.fixture(scope="session")
def extended_agents_available(
    available_agents: dict[str, "AgentAvailability"]
) -> list[str]:
    """Get list of available extended tier agents.

    Returns:
        List of agent IDs that are installed and authenticated
    """
    from specify_cli.orchestrator.testing.availability import EXTENDED_AGENTS

    return sorted(
        [
            agent_id
            for agent_id, avail in available_agents.items()
            if avail.is_available and agent_id in EXTENDED_AGENTS
        ]
    )


@pytest.fixture(scope="session")
def core_agents_available(
    available_agents: dict[str, "AgentAvailability"]
) -> list[str]:
    """Get list of available core tier agents.

    Returns:
        List of agent IDs that are installed and authenticated
    """
    from specify_cli.orchestrator.testing.availability import CORE_AGENTS

    return sorted(
        [
            agent_id
            for agent_id, avail in available_agents.items()
            if avail.is_available and agent_id in CORE_AGENTS
        ]
    )


# =============================================================================
# Fixture loading helpers
# =============================================================================


@pytest.fixture(scope="function")
def test_context_factory(tmp_path):
    """Factory fixture for loading test contexts from checkpoints.

    Usage:
        ctx = test_context_factory("wp_created")
        ctx = test_context_factory("review_pending")

    Returns:
        Factory function that loads TestContext from checkpoint name
    """
    from tests.fixtures.orchestrator import load_checkpoint

    def _factory(checkpoint_name: str):
        return load_checkpoint(checkpoint_name, tmp_path)

    return _factory
