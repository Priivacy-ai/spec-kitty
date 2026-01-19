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


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


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
def extended_agents_available(available_agents: dict[str, "AgentAvailability"]) -> list[str]:
    """Get list of available extended tier agents.

    Returns:
        List of agent IDs that are installed and authenticated
    """
    from specify_cli.orchestrator.testing.availability import EXTENDED_AGENTS

    return sorted([
        agent_id for agent_id, avail in available_agents.items()
        if avail.is_available and agent_id in EXTENDED_AGENTS
    ])


@pytest.fixture(scope="session")
def core_agents_available(available_agents: dict[str, "AgentAvailability"]) -> list[str]:
    """Get list of available core tier agents.

    Returns:
        List of agent IDs that are installed and authenticated
    """
    from specify_cli.orchestrator.testing.availability import CORE_AGENTS

    return sorted([
        agent_id for agent_id, avail in available_agents.items()
        if avail.is_available and agent_id in CORE_AGENTS
    ])
