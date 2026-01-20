"""Scheduler for orchestrating work package execution.

This module handles:
    - Dependency graph reading from WP frontmatter
    - Ready WP detection (dependencies satisfied)
    - Agent selection by role and priority
    - Concurrency management via semaphores
    - Single-agent mode handling
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator

from specify_cli.core.dependency_graph import (
    build_dependency_graph,
    detect_cycles,
    topological_sort,
)
from specify_cli.orchestrator.config import OrchestratorConfig, WPStatus
from specify_cli.orchestrator.state import OrchestrationRun, WPExecution

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class SchedulerError(Exception):
    """Base exception for scheduler errors."""

    pass


class DependencyGraphError(SchedulerError):
    """Raised when dependency graph is invalid."""

    pass


class NoAgentAvailableError(SchedulerError):
    """Raised when no agent is available for a role."""

    pass


# =============================================================================
# Dependency Graph (T022)
# =============================================================================


def build_wp_graph(feature_dir: Path) -> dict[str, list[str]]:
    """Build WP dependency graph from task frontmatter.

    Wraps the existing build_dependency_graph function from core module.

    Args:
        feature_dir: Path to feature directory (contains tasks/ subdirectory)

    Returns:
        Dict mapping WP ID to list of dependency WP IDs.
        e.g., {"WP02": ["WP01"], "WP03": ["WP01", "WP02"]}

    Raises:
        DependencyGraphError: If graph has cycles or invalid references.
    """
    graph = build_dependency_graph(feature_dir)

    if not graph:
        logger.warning(f"No work packages found in {feature_dir}")
        return {}

    logger.info(f"Built dependency graph with {len(graph)} work packages")
    return graph


def validate_wp_graph(graph: dict[str, list[str]]) -> None:
    """Validate WP dependency graph.

    Checks for:
    - Circular dependencies
    - Invalid dependency references

    Args:
        graph: Dependency graph from build_wp_graph()

    Raises:
        DependencyGraphError: If validation fails.
    """
    if not graph:
        return

    # Check for cycles
    cycles = detect_cycles(graph)
    if cycles:
        cycle_strs = [" -> ".join(cycle) for cycle in cycles]
        raise DependencyGraphError(
            f"Circular dependencies detected:\n  " + "\n  ".join(cycle_strs)
        )

    # Check all dependencies exist in graph
    all_wp_ids = set(graph.keys())
    for wp_id, deps in graph.items():
        for dep in deps:
            if dep not in all_wp_ids:
                raise DependencyGraphError(
                    f"WP {wp_id} depends on {dep}, but {dep} does not exist"
                )

    logger.debug("Dependency graph validation passed")


def get_topological_order(graph: dict[str, list[str]]) -> list[str]:
    """Get work packages in topological order.

    Returns WPs ordered so that dependencies come before dependents.

    Args:
        graph: Validated dependency graph

    Returns:
        List of WP IDs in topological order
    """
    if not graph:
        return []

    return topological_sort(graph)


# =============================================================================
# Ready WP Detection (T023)
# =============================================================================


def get_ready_wps(
    graph: dict[str, list[str]],
    state: OrchestrationRun,
) -> list[str]:
    """Return WP IDs that are ready to execute.

    A WP is ready if:
    1. All dependencies have completed successfully
    2. WP itself is in "pending" or "rework" status

    REWORK status means the WP was reviewed and rejected, needing
    re-implementation with the review feedback.

    Args:
        graph: Dependency graph from build_wp_graph()
        state: Current orchestration state

    Returns:
        List of WP IDs ready for execution, sorted by topological order
    """
    ready = []

    # Statuses that indicate a WP can be started/restarted
    startable_statuses = {WPStatus.PENDING, WPStatus.REWORK}

    for wp_id, deps in graph.items():
        # Get WP state, defaulting to pending if not tracked yet
        wp_state = state.work_packages.get(wp_id)

        # Skip if not in a startable status
        if wp_state and wp_state.status not in startable_statuses:
            continue

        # Check all dependencies completed successfully
        all_deps_done = True
        for dep_id in deps:
            dep_state = state.work_packages.get(dep_id)
            if not dep_state or dep_state.status != WPStatus.COMPLETED:
                all_deps_done = False
                break

        if all_deps_done:
            ready.append(wp_id)

    # Sort by topological order for determinism
    if ready:
        try:
            topo_order = get_topological_order(graph)
            order_map = {wp: i for i, wp in enumerate(topo_order)}
            ready.sort(key=lambda wp: order_map.get(wp, 999))
        except ValueError:
            # If topo sort fails (shouldn't after validation), just sort by ID
            ready.sort()

    logger.debug(f"Ready WPs: {ready}")
    return ready


def get_blocked_wps(
    graph: dict[str, list[str]],
    state: OrchestrationRun,
) -> dict[str, list[str]]:
    """Get WPs that are blocked waiting on dependencies.

    Args:
        graph: Dependency graph
        state: Current orchestration state

    Returns:
        Dict mapping blocked WP ID to list of blocking dependency IDs
    """
    blocked = {}

    for wp_id, deps in graph.items():
        wp_state = state.work_packages.get(wp_id)

        # Only check pending WPs
        if wp_state and wp_state.status != WPStatus.PENDING:
            continue

        # Find incomplete dependencies
        blocking_deps = []
        for dep_id in deps:
            dep_state = state.work_packages.get(dep_id)
            if not dep_state or dep_state.status != WPStatus.COMPLETED:
                blocking_deps.append(dep_id)

        if blocking_deps:
            blocked[wp_id] = blocking_deps

    return blocked


# =============================================================================
# Agent Selection (T024)
# =============================================================================


def _count_active_agent_tasks(
    agent_id: str,
    state: OrchestrationRun | None,
) -> int:
    """Count how many tasks an agent is currently running.

    Args:
        agent_id: Agent identifier
        state: Current orchestration state

    Returns:
        Number of active tasks for this agent
    """
    if not state:
        return 0

    count = 0
    for wp in state.work_packages.values():
        # Count implementation tasks
        if (
            wp.status == WPStatus.IMPLEMENTATION
            and wp.implementation_agent == agent_id
        ):
            count += 1

        # Count review tasks
        if wp.status == WPStatus.REVIEW and wp.review_agent == agent_id:
            count += 1

    return count


def _agent_at_limit(
    agent_id: str,
    config: OrchestratorConfig,
    state: OrchestrationRun | None,
) -> bool:
    """Check if agent has reached its concurrency limit.

    Args:
        agent_id: Agent identifier
        config: Orchestrator configuration
        state: Current orchestration state

    Returns:
        True if agent is at its max_concurrent limit
    """
    agent_config = config.agents.get(agent_id)
    if not agent_config:
        return True  # Unknown agent treated as at limit

    active_count = _count_active_agent_tasks(agent_id, state)
    return active_count >= agent_config.max_concurrent


def select_agent_from_user_config(
    repo_root: Path,
    role: str,
    exclude_agent: str | None = None,
    override_agent: str | None = None,
) -> str | None:
    """Select agent using user configuration from spec-kitty init.

    This is the preferred way to select agents - uses the configuration
    set by the user during `spec-kitty init`.

    Args:
        repo_root: Repository root for loading config
        role: "implementation" or "review"
        exclude_agent: Agent to exclude (for cross-review)
        override_agent: CLI override to use specific agent

    Returns:
        Canonical agent ID (normalized from aliases) or None if no agents configured
    """
    from specify_cli.orchestrator.agent_config import load_agent_config
    from specify_cli.orchestrator.agents import normalize_agent_id

    # CLI override takes precedence
    if override_agent:
        logger.info(f"Using CLI override agent: {override_agent}")
        return normalize_agent_id(override_agent)

    config = load_agent_config(repo_root)

    if not config.available:
        logger.warning("No agents configured in .kittify/config.yaml")
        return None

    # Select agent and normalize to canonical ID
    if role == "implementation":
        selected = config.select_implementer(exclude=exclude_agent)
    elif role == "review":
        selected = config.select_reviewer(implementer=exclude_agent)
    else:
        logger.warning(f"Unknown role: {role}")
        selected = config.available[0] if config.available else None

    return normalize_agent_id(selected) if selected else None


def select_agent(
    config: OrchestratorConfig,
    role: str,
    exclude_agent: str | None = None,
    state: OrchestrationRun | None = None,
) -> str | None:
    """Select highest-priority available agent for role.

    NOTE: This is the legacy selection method using OrchestratorConfig.
    Prefer select_agent_from_user_config() which uses the configuration
    set during `spec-kitty init`.

    Args:
        config: Orchestrator configuration
        role: "implementation" or "review"
        exclude_agent: Agent to exclude (for cross-agent review)
        state: Current state (for concurrency tracking)

    Returns:
        Agent ID or None if no agent available
    """
    # Get candidates from defaults, maintaining priority order
    candidates = config.defaults.get(role, [])

    if not candidates:
        # Fall back to all enabled agents with this role
        candidates = [
            agent_id
            for agent_id, agent_config in config.agents.items()
            if agent_config.enabled and role in agent_config.roles
        ]
        # Sort by priority
        candidates.sort(
            key=lambda aid: config.agents[aid].priority
        )

    for agent_id in candidates:
        agent_config = config.agents.get(agent_id)
        if not agent_config:
            logger.debug(f"Agent {agent_id} not found in config")
            continue

        if not agent_config.enabled:
            logger.debug(f"Agent {agent_id} is disabled")
            continue

        if role not in agent_config.roles:
            logger.debug(f"Agent {agent_id} does not support role {role}")
            continue

        if agent_id == exclude_agent:
            logger.debug(f"Agent {agent_id} excluded for cross-agent review")
            continue

        # Check concurrency limit
        if _agent_at_limit(agent_id, config, state):
            logger.debug(f"Agent {agent_id} at concurrency limit")
            continue

        logger.info(f"Selected agent {agent_id} for {role}")
        return agent_id

    logger.warning(f"No agent available for role {role}")
    return None


def select_review_agent_from_user_config(
    repo_root: Path,
    implementation_agent: str,
    override_agent: str | None = None,
) -> str | None:
    """Select review agent using user configuration from spec-kitty init.

    Prefers a different agent than implementation for cross-review.

    Args:
        repo_root: Repository root for loading config
        implementation_agent: Agent that did implementation (may be alias or canonical)
        override_agent: CLI override to use specific agent

    Returns:
        Canonical agent ID (normalized from aliases) for review
    """
    from specify_cli.orchestrator.agent_config import load_agent_config
    from specify_cli.orchestrator.agents import normalize_agent_id

    # CLI override takes precedence
    if override_agent:
        logger.info(f"Using CLI override review agent: {override_agent}")
        return normalize_agent_id(override_agent)

    config = load_agent_config(repo_root)

    if not config.available:
        logger.warning("No agents configured, using implementer for review")
        return normalize_agent_id(implementation_agent)

    selected = config.select_reviewer(implementer=implementation_agent)
    return normalize_agent_id(selected) if selected else None


def select_review_agent(
    config: OrchestratorConfig,
    implementation_agent: str,
    state: OrchestrationRun | None = None,
) -> str | None:
    """Select review agent, excluding the implementation agent for cross-review.

    NOTE: This is the legacy selection method using OrchestratorConfig.
    Prefer select_review_agent_from_user_config() which uses the configuration
    set during `spec-kitty init`.

    Args:
        config: Orchestrator configuration
        implementation_agent: Agent that did implementation
        state: Current state for concurrency tracking

    Returns:
        Agent ID for review, or None if unavailable
    """
    # In single-agent mode, use the same agent
    if is_single_agent_mode(config):
        logger.info(
            f"Single-agent mode: using {implementation_agent} for review"
        )
        return implementation_agent

    # Try to find a different agent for cross-review
    review_agent = select_agent(
        config,
        role="review",
        exclude_agent=implementation_agent,
        state=state,
    )

    if review_agent:
        return review_agent

    # If no other agent available, fall back to same agent with warning
    logger.warning(
        f"No cross-review agent available, using {implementation_agent}"
    )
    return implementation_agent


# =============================================================================
# Concurrency Management (T025)
# =============================================================================


class ConcurrencyManager:
    """Manages concurrency limits for orchestration.

    Uses asyncio.Semaphore to limit:
    - Global concurrent processes
    - Per-agent concurrent processes
    """

    def __init__(self, config: OrchestratorConfig):
        """Initialize concurrency manager.

        Args:
            config: Orchestrator configuration with concurrency limits
        """
        self.config = config
        self.global_semaphore = asyncio.Semaphore(config.global_concurrency)
        self.agent_semaphores: dict[str, asyncio.Semaphore] = {}

        # Create per-agent semaphores
        for agent_id, agent_config in config.agents.items():
            self.agent_semaphores[agent_id] = asyncio.Semaphore(
                agent_config.max_concurrent
            )

        logger.info(
            f"ConcurrencyManager initialized: global={config.global_concurrency}, "
            f"agents={len(self.agent_semaphores)}"
        )

    def _get_agent_semaphore(self, agent_id: str) -> asyncio.Semaphore:
        """Get or create semaphore for agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Semaphore for the agent
        """
        if agent_id not in self.agent_semaphores:
            # Create with default limit if not configured
            default_limit = 2
            self.agent_semaphores[agent_id] = asyncio.Semaphore(default_limit)
            logger.warning(
                f"Created default semaphore for unconfigured agent {agent_id}"
            )
        return self.agent_semaphores[agent_id]

    async def acquire(self, agent_id: str) -> None:
        """Acquire both global and agent-specific semaphores.

        Always acquires global first to prevent deadlocks.

        Args:
            agent_id: Agent identifier
        """
        # Always acquire global first to prevent deadlock
        await self.global_semaphore.acquire()
        try:
            agent_sem = self._get_agent_semaphore(agent_id)
            await agent_sem.acquire()
        except Exception:
            # Release global if agent acquisition fails
            self.global_semaphore.release()
            raise

        logger.debug(f"Acquired semaphores for {agent_id}")

    def release(self, agent_id: str) -> None:
        """Release both semaphores.

        Releases in reverse order of acquisition.

        Args:
            agent_id: Agent identifier
        """
        agent_sem = self._get_agent_semaphore(agent_id)
        agent_sem.release()
        self.global_semaphore.release()
        logger.debug(f"Released semaphores for {agent_id}")

    @asynccontextmanager
    async def throttle(self, agent_id: str) -> AsyncIterator[None]:
        """Context manager for throttled execution.

        Acquires semaphores on entry, releases on exit.

        Args:
            agent_id: Agent identifier

        Yields:
            None after acquiring semaphores
        """
        await self.acquire(agent_id)
        try:
            yield
        finally:
            self.release(agent_id)

    def get_available_slots(self) -> int:
        """Get number of available global execution slots.

        Returns:
            Number of slots available (0 if at limit)
        """
        # Semaphore doesn't expose count directly, so we track it
        # This is a heuristic based on the initial value
        return self.config.global_concurrency - (
            self.config.global_concurrency - self.global_semaphore._value
        )

    def get_agent_available_slots(self, agent_id: str) -> int:
        """Get number of available slots for specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Number of slots available for this agent
        """
        agent_sem = self._get_agent_semaphore(agent_id)
        agent_config = self.config.agents.get(agent_id)
        max_concurrent = agent_config.max_concurrent if agent_config else 2
        return max_concurrent - (max_concurrent - agent_sem._value)


# =============================================================================
# Single-Agent Mode (T026)
# =============================================================================


# Default delay between implementation and review in single-agent mode
DEFAULT_SINGLE_AGENT_DELAY = 60  # seconds


def is_single_agent_mode(config: OrchestratorConfig) -> bool:
    """Check if operating in single-agent mode.

    Single-agent mode is active when:
    - Explicitly enabled via config.single_agent_mode
    - Only one agent is enabled (auto-detected)

    Args:
        config: Orchestrator configuration

    Returns:
        True if single-agent mode is active
    """
    # Explicit configuration
    if config.single_agent_mode:
        return True

    # Auto-detect: only one agent enabled
    enabled_agents = [
        aid for aid, ac in config.agents.items()
        if ac.enabled
    ]
    return len(enabled_agents) == 1


def get_single_agent(config: OrchestratorConfig) -> str | None:
    """Get the single agent ID when in single-agent mode.

    Args:
        config: Orchestrator configuration

    Returns:
        Agent ID if in single-agent mode, None otherwise
    """
    if not is_single_agent_mode(config):
        return None

    # Use explicitly configured agent
    if config.single_agent:
        return config.single_agent

    # Auto-detect: return the only enabled agent
    enabled_agents = [
        aid for aid, ac in config.agents.items()
        if ac.enabled
    ]
    return enabled_agents[0] if enabled_agents else None


async def single_agent_review_delay(
    delay_seconds: int | None = None,
) -> None:
    """Apply delay before single-agent review.

    The delay helps the agent "forget" its implementation context
    and review with a fresher perspective.

    Args:
        delay_seconds: Delay in seconds (defaults to 60)
    """
    delay = delay_seconds or DEFAULT_SINGLE_AGENT_DELAY
    logger.info(
        f"Single-agent mode: waiting {delay}s before review "
        "to provide fresh perspective"
    )
    await asyncio.sleep(delay)


# =============================================================================
# Scheduler State
# =============================================================================


class SchedulerState:
    """Tracks scheduler state during orchestration.

    Combines configuration, dependency graph, and concurrency management.
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        feature_dir: Path,
    ):
        """Initialize scheduler state.

        Args:
            config: Orchestrator configuration
            feature_dir: Path to feature directory

        Raises:
            DependencyGraphError: If dependency graph is invalid
        """
        self.config = config
        self.feature_dir = feature_dir

        # Build and validate dependency graph
        self.graph = build_wp_graph(feature_dir)
        validate_wp_graph(self.graph)

        # Initialize concurrency manager
        self.concurrency = ConcurrencyManager(config)

        # Track single-agent mode
        self.single_agent_mode = is_single_agent_mode(config)
        self.single_agent = get_single_agent(config)

        if self.single_agent_mode:
            logger.warning(
                f"Single-agent mode active: {self.single_agent}. "
                "Cross-agent review will not be available."
            )

    def get_ready_wps(self, state: OrchestrationRun) -> list[str]:
        """Get WPs ready for execution.

        Args:
            state: Current orchestration state

        Returns:
            List of ready WP IDs
        """
        return get_ready_wps(self.graph, state)

    def select_implementation_agent(
        self,
        state: OrchestrationRun,
    ) -> str | None:
        """Select agent for implementation.

        Args:
            state: Current orchestration state

        Returns:
            Agent ID or None
        """
        if self.single_agent_mode:
            return self.single_agent
        return select_agent(self.config, "implementation", state=state)

    def select_review_agent(
        self,
        implementation_agent: str,
        state: OrchestrationRun,
    ) -> str | None:
        """Select agent for review.

        Args:
            implementation_agent: Agent that did implementation
            state: Current orchestration state

        Returns:
            Agent ID or None
        """
        return select_review_agent(
            self.config,
            implementation_agent,
            state=state,
        )

    def initialize_wp_state(
        self,
        state: OrchestrationRun,
    ) -> None:
        """Initialize WP execution state for all WPs in graph.

        Creates WPExecution entries for WPs not already in state.

        Args:
            state: Orchestration state to update
        """
        for wp_id in self.graph:
            if wp_id not in state.work_packages:
                state.work_packages[wp_id] = WPExecution(wp_id=wp_id)

        state.wps_total = len(self.graph)


__all__ = [
    # Exceptions
    "SchedulerError",
    "DependencyGraphError",
    "NoAgentAvailableError",
    # Graph functions (T022)
    "build_wp_graph",
    "validate_wp_graph",
    "get_topological_order",
    # Ready detection (T023)
    "get_ready_wps",
    "get_blocked_wps",
    # Agent selection (T024) - user config based (preferred)
    "select_agent_from_user_config",
    "select_review_agent_from_user_config",
    # Agent selection (T024) - legacy (for backwards compatibility)
    "select_agent",
    "select_review_agent",
    # Concurrency (T025)
    "ConcurrencyManager",
    # Single-agent mode (T026)
    "is_single_agent_mode",
    "get_single_agent",
    "single_agent_review_delay",
    "DEFAULT_SINGLE_AGENT_DELAY",
    # State
    "SchedulerState",
]
