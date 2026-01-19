"""Test path selection based on agent availability.

This module determines which test execution path to use based on the number
of authenticated agents available. The path affects how tests are structured:

- 1-agent: Same agent handles both implementation and review
- 2-agent: Different agents for implementation vs review
- 3+-agent: Third agent available for fallback scenarios
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    pass

# Module-level cache for test path
_test_path_cache: TestPath | None = None


@dataclass
class TestPath:
    """Selected test path based on runtime agent availability."""

    path_type: Literal["1-agent", "2-agent", "3+-agent"]
    """The test path variant to execute."""

    available_agents: list[str]
    """List of authenticated agent IDs available for this run."""

    implementation_agent: str
    """Agent to use for implementation phase."""

    review_agent: str
    """Agent to use for review phase."""

    fallback_agent: str | None
    """Third agent for fallback scenarios (None for 1/2-agent paths)."""

    @property
    def is_cross_agent(self) -> bool:
        """True if implementation and review use different agents."""
        return self.implementation_agent != self.review_agent

    @property
    def has_fallback(self) -> bool:
        """True if a fallback agent is available."""
        return self.fallback_agent is not None

    @property
    def agent_count(self) -> int:
        """Number of available agents."""
        return len(self.available_agents)


def determine_path_type(agent_count: int) -> Literal["1-agent", "2-agent", "3+-agent"]:
    """Determine test path type based on available agent count.

    Args:
        agent_count: Number of available (authenticated) agents

    Returns:
        Path type string indicating which test variant to run

    Raises:
        ValueError: If no agents available
    """
    if agent_count == 0:
        raise ValueError("No agents available for testing")
    elif agent_count == 1:
        return "1-agent"
    elif agent_count == 2:
        return "2-agent"
    else:
        return "3+-agent"


def assign_agents(
    available_agents: list[str],
    path_type: Literal["1-agent", "2-agent", "3+-agent"],
) -> tuple[str, str, str | None]:
    """Assign agents to roles based on path type.

    Agents are sorted alphabetically for deterministic assignment:
    - First agent: implementation role
    - Second agent: review role
    - Third agent: fallback role (if available)

    Args:
        available_agents: List of available agent IDs
        path_type: The test path type

    Returns:
        Tuple of (implementation_agent, review_agent, fallback_agent)

    Raises:
        ValueError: If no agents available
    """
    if not available_agents:
        raise ValueError("No agents available")

    # Sort for deterministic assignment
    agents = sorted(available_agents)

    if path_type == "1-agent":
        # Same agent for both roles
        return agents[0], agents[0], None

    elif path_type == "2-agent":
        # Different agents, no fallback
        return agents[0], agents[1], None

    else:  # 3+-agent
        # Different agents with fallback
        return agents[0], agents[1], agents[2]


def clear_test_path_cache() -> None:
    """Clear the cached test path.

    Call this when agent availability may have changed (e.g., during
    test setup or teardown).
    """
    global _test_path_cache
    _test_path_cache = None


async def select_test_path(force_path: str | None = None) -> TestPath:
    """Select test path based on available agents.

    This is the main entry point for test path selection. It:
    1. Detects available (authenticated) agents
    2. Determines the appropriate path type
    3. Assigns agents to roles
    4. Caches the result for session duration

    Args:
        force_path: Optional path type to force (for testing).
            Valid values: "1-agent", "2-agent", "3+-agent"

    Returns:
        TestPath with agent assignments

    Raises:
        ValueError: If no agents available
    """
    global _test_path_cache

    if _test_path_cache is not None and force_path is None:
        return _test_path_cache

    # Import here to avoid circular imports and allow WP01 to be merged first
    from specify_cli.orchestrator.testing.availability import (
        detect_all_agents,
        get_available_agents,
    )

    # Detect agents
    await detect_all_agents()
    available = get_available_agents()

    if not available:
        raise ValueError(
            "No agents available for testing. "
            "Install and authenticate at least one agent."
        )

    # Determine path type
    if force_path:
        # Validate force_path
        if force_path not in ("1-agent", "2-agent", "3+-agent"):
            raise ValueError(
                f"Invalid force_path: {force_path}. "
                "Must be '1-agent', '2-agent', or '3+-agent'"
            )
        path_type: Literal["1-agent", "2-agent", "3+-agent"] = force_path  # type: ignore[assignment]
    else:
        path_type = determine_path_type(len(available))

    # Assign agents
    impl_agent, review_agent, fallback = assign_agents(available, path_type)

    test_path = TestPath(
        path_type=path_type,
        available_agents=available,
        implementation_agent=impl_agent,
        review_agent=review_agent,
        fallback_agent=fallback,
    )

    if force_path is None:
        _test_path_cache = test_path

    return test_path


def select_test_path_sync(force_path: str | None = None) -> TestPath:
    """Synchronous wrapper for select_test_path.

    Useful for pytest fixtures and non-async contexts.

    Args:
        force_path: Optional path type to force (for testing)

    Returns:
        TestPath with agent assignments
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop - create one
        return asyncio.run(select_test_path(force_path))

    # Running loop exists - use it
    return loop.run_until_complete(select_test_path(force_path))
