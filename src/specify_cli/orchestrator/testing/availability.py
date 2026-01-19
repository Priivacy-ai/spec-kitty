"""Agent availability detection for testing.

NOTE: This is a stub module that will be fully implemented by WP01.
It provides the minimal interface needed by paths.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Module-level cache for availability results
_availability_cache: list["AgentAvailability"] | None = None


@dataclass
class AgentAvailability:
    """Result of detecting an agent's availability for testing.

    NOTE: Full implementation in WP01.
    """

    agent_id: str
    """Canonical agent identifier (e.g., 'claude', 'codex', 'gemini')."""

    is_installed: bool
    """True if the agent CLI binary exists and is executable."""

    is_authenticated: bool
    """True if the agent responded to a probe API call."""

    tier: Literal["core", "extended"]
    """Agent tier: 'core' (fail if unavailable) or 'extended' (skip if unavailable)."""

    failure_reason: str | None
    """Human-readable reason if is_installed or is_authenticated is False."""

    probe_duration_ms: int | None = None
    """Time taken for auth probe in milliseconds (None if not probed)."""


async def detect_all_agents() -> list[AgentAvailability]:
    """Detect availability of all supported agents.

    NOTE: Stub implementation. Full implementation in WP01.

    Returns:
        List of AgentAvailability results for all agents
    """
    global _availability_cache

    # Return empty list - actual detection to be implemented in WP01
    if _availability_cache is None:
        _availability_cache = []

    return _availability_cache


def get_available_agents() -> list[str]:
    """Get list of authenticated agent IDs.

    NOTE: Stub implementation. Full implementation in WP01.

    Returns:
        List of agent IDs that are installed and authenticated
    """
    if _availability_cache is None:
        return []

    return [a.agent_id for a in _availability_cache if a.is_authenticated]


def clear_availability_cache() -> None:
    """Clear the cached availability results.

    Call this when agent availability may have changed.
    """
    global _availability_cache
    _availability_cache = None
