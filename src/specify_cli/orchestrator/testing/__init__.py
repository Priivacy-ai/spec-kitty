"""Testing utilities for the orchestrator.

This subpackage provides infrastructure for end-to-end testing of the
multi-agent orchestrator. It includes:

- Agent availability detection (which agents are installed and authenticated)
- Test path selection (1-agent, 2-agent, or 3+-agent test paths)
- Fixture management (checkpoint snapshots for deterministic testing)

Example usage:
    from specify_cli.orchestrator.testing import (
        AgentAvailability,
        detect_all_agents,
        CORE_AGENTS,
        EXTENDED_AGENTS,
        TestPath,
        select_test_path,
        FixtureCheckpoint,
        TestContext,
        load_state_file,
    )

    # Detect available agents
    agents = await detect_all_agents()
    available = [a for a in agents.values() if a.is_available]

    # Select test path based on available agents
    test_path = await select_test_path()
"""

from __future__ import annotations

# Availability detection (WP01)
from specify_cli.orchestrator.testing.availability import (
    CORE_AGENTS,
    EXTENDED_AGENTS,
    ALL_AGENTS,
    AgentAvailability,
    detect_all_agents,
    detect_agent,
    get_available_agents,
    clear_agent_cache,
    check_installed,
    probe_agent_auth,
)

# Test path selection (WP02)
from specify_cli.orchestrator.testing.paths import (
    TestPath,
    assign_agents,
    clear_test_path_cache,
    determine_path_type,
    select_test_path,
    select_test_path_sync,
)

# Fixture management (WP03)
from specify_cli.orchestrator.testing.fixtures import (
    FixtureCheckpoint,
    StateFileError,
    TestContext,
    WorktreeMetadata,
    WorktreesFileError,
    load_state_file,
    load_worktrees_file,
    save_state_file,
    save_worktrees_file,
)

__all__ = [
    # Tier constants
    "CORE_AGENTS",
    "EXTENDED_AGENTS",
    "ALL_AGENTS",
    # Availability detection (WP01)
    "AgentAvailability",
    "detect_all_agents",
    "detect_agent",
    "get_available_agents",
    "clear_agent_cache",
    "check_installed",
    "probe_agent_auth",
    # Test path selection (WP02)
    "TestPath",
    "assign_agents",
    "clear_test_path_cache",
    "determine_path_type",
    "select_test_path",
    "select_test_path_sync",
    # Fixture management (WP03)
    "FixtureCheckpoint",
    "WorktreeMetadata",
    "TestContext",
    "WorktreesFileError",
    "StateFileError",
    "load_worktrees_file",
    "save_worktrees_file",
    "load_state_file",
    "save_state_file",
]
