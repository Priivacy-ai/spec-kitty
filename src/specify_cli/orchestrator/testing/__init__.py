"""Test utilities for orchestrator end-to-end testing.

This module provides:
- Agent availability detection (availability.py)
- Test path selection based on agent count (paths.py)
- Fixture loading and checkpoint management (fixtures.py)
"""

from specify_cli.orchestrator.testing.availability import (
    AgentAvailability,
    clear_availability_cache,
    detect_all_agents,
    get_available_agents,
)
from specify_cli.orchestrator.testing.paths import (
    TestPath,
    assign_agents,
    clear_test_path_cache,
    determine_path_type,
    select_test_path,
    select_test_path_sync,
)

__all__ = [
    # Availability (WP01 - stub until fully implemented)
    "AgentAvailability",
    "clear_availability_cache",
    "detect_all_agents",
    "get_available_agents",
    # Paths (WP02)
    "TestPath",
    "assign_agents",
    "clear_test_path_cache",
    "determine_path_type",
    "select_test_path",
    "select_test_path_sync",
]
