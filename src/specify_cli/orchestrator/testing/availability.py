"""Agent availability detection for orchestrator e2e tests.

This module provides functions to detect which AI coding agents are installed
and authenticated on the system. Results are categorized into tiers:

- Core tier (5 agents): Tests FAIL if unavailable
  claude, codex, copilot, gemini, opencode

- Extended tier (7 agents): Tests SKIP if unavailable
  cursor, qwen, augment, kilocode, roo, windsurf, amazonq

Example usage:
    from specify_cli.orchestrator.testing.availability import (
        detect_all_agents,
        get_available_agents,
        CORE_AGENTS,
    )

    # Detect all agents (cached for session)
    agents = await detect_all_agents()

    # Get list of available agent IDs
    available = get_available_agents()
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from dataclasses import dataclass
from typing import Literal

# Agent tier constants
# Core tier: Tests fail if these are unavailable
CORE_AGENTS = frozenset({"claude", "codex", "copilot", "gemini", "opencode"})

# Extended tier: Tests skip if these are unavailable
EXTENDED_AGENTS = frozenset({
    "cursor", "qwen", "augment", "kilocode", "roo", "windsurf", "amazonq"
})

# All supported agents
ALL_AGENTS = CORE_AGENTS | EXTENDED_AGENTS

# Mapping from canonical agent IDs to orchestrator registry IDs
# The orchestrator uses "claude-code" but testing uses "claude"
AGENT_ID_TO_REGISTRY: dict[str, str] = {
    "claude": "claude-code",
    "codex": "codex",
    "copilot": "copilot",
    "gemini": "gemini",
    "opencode": "opencode",
    "cursor": "cursor",
    "qwen": "qwen",
    "augment": "augment",
    "kilocode": "kilocode",
    # These 3 don't have invokers yet (TODO: add when implemented)
    "roo": None,
    "windsurf": None,
    "amazonq": None,
}

# Probe timeout in seconds (configurable via environment)
PROBE_TIMEOUT = int(os.environ.get("ORCHESTRATOR_PROBE_TIMEOUT", "10"))


@dataclass
class AgentAvailability:
    """Result of detecting an agent's availability for testing.

    Attributes:
        agent_id: Canonical agent identifier (e.g., 'claude', 'codex')
        is_installed: True if the agent CLI binary exists and is executable
        is_authenticated: True if the agent responded to a probe API call
        tier: Agent tier ('core' or 'extended')
        failure_reason: Human-readable reason if unavailable
        probe_duration_ms: Time taken for auth probe in milliseconds
    """

    agent_id: str
    is_installed: bool
    is_authenticated: bool
    tier: Literal["core", "extended"]
    failure_reason: str | None = None
    probe_duration_ms: int | None = None

    @property
    def is_available(self) -> bool:
        """Agent is available if installed and authenticated."""
        return self.is_installed and self.is_authenticated

    @classmethod
    def get_tier(cls, agent_id: str) -> Literal["core", "extended"]:
        """Determine tier for an agent ID.

        Args:
            agent_id: Canonical agent identifier

        Returns:
            'core' if agent is in core tier, 'extended' otherwise
        """
        if agent_id in CORE_AGENTS:
            return "core"
        return "extended"


def _get_invoker_class(agent_id: str):
    """Get the invoker class for an agent ID.

    Args:
        agent_id: Canonical agent identifier

    Returns:
        Invoker class or None if not available
    """
    # Map canonical ID to registry ID
    registry_id = AGENT_ID_TO_REGISTRY.get(agent_id)
    if registry_id is None:
        return None

    # Import registry to avoid circular imports
    from specify_cli.orchestrator.agents import AGENT_REGISTRY

    return AGENT_REGISTRY.get(registry_id)


def check_installed(agent_id: str) -> tuple[bool, str | None]:
    """Check if an agent CLI is installed.

    Uses shutil.which() to check if the agent's command is in PATH.

    Args:
        agent_id: Canonical agent identifier (e.g., 'claude', 'codex')

    Returns:
        Tuple of (is_installed, failure_reason)
        - is_installed: True if CLI is found in PATH
        - failure_reason: Human-readable reason if not installed, None otherwise
    """
    # Check if we have a mapping for this agent
    registry_id = AGENT_ID_TO_REGISTRY.get(agent_id)
    if registry_id is None:
        # Agent doesn't have an invoker yet
        return False, f"No invoker implemented for agent: {agent_id}"

    # Get invoker class
    invoker_class = _get_invoker_class(agent_id)
    if invoker_class is None:
        return False, f"Unknown agent: {agent_id}"

    # Get the command from the invoker
    command = getattr(invoker_class, "command", None)
    if command is None:
        return False, f"Agent {agent_id} has no command attribute"

    # Check if command exists in PATH
    if shutil.which(command) is not None:
        return True, None

    return False, f"CLI not found: {command}"


async def probe_agent_auth(agent_id: str) -> tuple[bool, str | None, int]:
    """Probe an agent to verify authentication.

    Makes a minimal API call to verify the agent can communicate.
    For agents without a probe() method, assumes authenticated if installed.

    Args:
        agent_id: Canonical agent identifier

    Returns:
        Tuple of (is_authenticated, failure_reason, duration_ms)
        - is_authenticated: True if probe succeeded
        - failure_reason: Human-readable reason if probe failed
        - duration_ms: Time taken for probe in milliseconds
    """
    invoker_class = _get_invoker_class(agent_id)
    if invoker_class is None:
        return False, f"Unknown agent: {agent_id}", 0

    start_time = time.monotonic()

    try:
        # Create invoker instance
        invoker = invoker_class()

        # Check if invoker has a probe() method
        if hasattr(invoker, "probe") and callable(getattr(invoker, "probe")):
            # Call probe method with timeout
            result = await asyncio.wait_for(
                invoker.probe(),
                timeout=PROBE_TIMEOUT
            )
            duration_ms = int((time.monotonic() - start_time) * 1000)

            if result:
                return True, None, duration_ms
            else:
                return False, "Probe returned failure", duration_ms
        else:
            # No probe method - assume authenticated if installed
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return True, None, duration_ms

    except asyncio.TimeoutError:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        return False, f"Probe timed out after {PROBE_TIMEOUT}s", duration_ms
    except Exception as e:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        return False, f"Probe error: {str(e)}", duration_ms


# Module-level cache for agent detection results
_agent_cache: dict[str, AgentAvailability] | None = None


def clear_agent_cache() -> None:
    """Clear the cached agent detection results.

    Call this to force re-detection on the next detect_all_agents() call.
    Useful for testing or when agent availability may have changed.
    """
    global _agent_cache
    _agent_cache = None


async def detect_agent(agent_id: str) -> AgentAvailability:
    """Detect availability of a single agent.

    Checks both installation (CLI in PATH) and authentication (probe API call).

    Args:
        agent_id: Canonical agent identifier (e.g., 'claude', 'codex')

    Returns:
        AgentAvailability with detection results
    """
    tier = AgentAvailability.get_tier(agent_id)

    # Check installation
    is_installed, install_reason = check_installed(agent_id)

    if not is_installed:
        return AgentAvailability(
            agent_id=agent_id,
            is_installed=False,
            is_authenticated=False,
            tier=tier,
            failure_reason=install_reason,
        )

    # Probe authentication
    is_authenticated, auth_reason, duration_ms = await probe_agent_auth(agent_id)

    return AgentAvailability(
        agent_id=agent_id,
        is_installed=True,
        is_authenticated=is_authenticated,
        tier=tier,
        failure_reason=auth_reason,
        probe_duration_ms=duration_ms,
    )


async def detect_all_agents() -> dict[str, AgentAvailability]:
    """Detect availability of all supported agents.

    Results are cached for the session duration. Call clear_agent_cache()
    to force re-detection.

    Returns:
        Dict mapping agent_id to AgentAvailability for all 12 agents,
        sorted alphabetically by agent_id
    """
    global _agent_cache

    if _agent_cache is not None:
        return _agent_cache

    results = {}
    for agent_id in sorted(ALL_AGENTS):
        results[agent_id] = await detect_agent(agent_id)

    _agent_cache = results
    return results


def get_available_agents() -> list[str]:
    """Get list of available (installed + authenticated) agent IDs.

    Returns agent IDs sorted alphabetically.

    Returns:
        List of available agent IDs

    Raises:
        RuntimeError: If detect_all_agents() has not been called yet
    """
    if _agent_cache is None:
        raise RuntimeError(
            "Call detect_all_agents() first before using get_available_agents()"
        )

    return sorted([
        agent_id for agent_id, avail in _agent_cache.items()
        if avail.is_available
    ])


def get_core_agents_available() -> list[str]:
    """Get list of available core tier agents.

    Returns:
        List of available core agent IDs, sorted alphabetically

    Raises:
        RuntimeError: If detect_all_agents() has not been called yet
    """
    if _agent_cache is None:
        raise RuntimeError("Call detect_all_agents() first")

    return sorted([
        agent_id for agent_id, avail in _agent_cache.items()
        if avail.is_available and agent_id in CORE_AGENTS
    ])


def get_extended_agents_available() -> list[str]:
    """Get list of available extended tier agents.

    Returns:
        List of available extended agent IDs, sorted alphabetically

    Raises:
        RuntimeError: If detect_all_agents() has not been called yet
    """
    if _agent_cache is None:
        raise RuntimeError("Call detect_all_agents() first")

    return sorted([
        agent_id for agent_id, avail in _agent_cache.items()
        if avail.is_available and agent_id in EXTENDED_AGENTS
    ])
