"""Configuration module for the orchestrator.

This module provides:
    - Status enums (OrchestrationStatus, WPStatus, FallbackStrategy)
    - Config dataclasses (AgentConfig, OrchestratorConfig)
    - YAML parsing and validation
    - Default config generation based on installed agents
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)


# =============================================================================
# Enums (T002)
# =============================================================================


class OrchestrationStatus(str, Enum):
    """Status of an orchestration run."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class WPStatus(str, Enum):
    """Status of a work package execution.

    State machine transitions:
        PENDING → READY (dependencies satisfied)
        READY → IMPLEMENTATION (agent starts)
        IMPLEMENTATION → REVIEW (implementation completes)
        REVIEW → COMPLETED (review approves)
        REVIEW → REWORK (review rejects with feedback)
        REWORK → IMPLEMENTATION (re-implementation starts)
        Any → FAILED (max retries exceeded or unrecoverable error)
    """

    PENDING = "pending"
    READY = "ready"
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    REWORK = "rework"  # Review rejected, needs re-implementation
    COMPLETED = "completed"
    FAILED = "failed"


class FallbackStrategy(str, Enum):
    """Strategy for handling agent failures."""

    NEXT_IN_LIST = "next_in_list"
    SAME_AGENT = "same_agent"
    FAIL = "fail"


# =============================================================================
# Exceptions
# =============================================================================


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


class NoAgentsError(Exception):
    """Raised when no agents are installed or enabled."""

    pass


# =============================================================================
# Dataclasses (T003)
# =============================================================================


@dataclass
class AgentConfig:
    """Configuration for a single AI agent."""

    agent_id: str
    enabled: bool = True
    roles: list[str] = field(default_factory=lambda: ["implementation", "review"])
    priority: int = 50
    max_concurrent: int = 100  # Effectively unlimited - let dependency graph be the limit
    timeout_seconds: int = 600


@dataclass
class OrchestratorConfig:
    """Main orchestrator configuration."""

    version: str = "1.0"
    defaults: dict[str, list[str]] = field(default_factory=dict)
    agents: dict[str, AgentConfig] = field(default_factory=dict)
    fallback_strategy: FallbackStrategy = FallbackStrategy.NEXT_IN_LIST
    max_retries: int = 3
    single_agent_mode: bool = False
    single_agent: str | None = None
    global_concurrency: int = 100  # Effectively unlimited - let dependency graph be the limit
    global_timeout: int = 3600


# =============================================================================
# Agent Detection
# =============================================================================

# Map of agent ID to CLI command name for detection
AGENT_COMMANDS: dict[str, str] = {
    "claude-code": "claude",
    "codex": "codex",
    "copilot": "gh",  # GitHub Copilot uses gh CLI
    "gemini": "gemini",
    "qwen": "qwen",
    "opencode": "opencode",
    "kilocode": "kilocode",
    "augment": "auggie",
    "cursor": "cursor",
}

# Default priority order (lower = higher priority)
AGENT_PRIORITIES: dict[str, int] = {
    "claude-code": 10,
    "codex": 20,
    "copilot": 30,
    "gemini": 40,
    "qwen": 50,
    "opencode": 60,
    "kilocode": 70,
    "augment": 80,
    "cursor": 90,
}


def detect_installed_agents() -> list[str]:
    """Detect which AI agents are installed on the system.

    Returns:
        List of agent IDs that have their CLI tools available.
    """
    installed = []
    for agent_id, command in AGENT_COMMANDS.items():
        if shutil.which(command):
            installed.append(agent_id)
            logger.debug(f"Detected agent: {agent_id} ({command})")
        else:
            logger.debug(f"Agent not found: {agent_id} ({command})")

    return installed


# =============================================================================
# Config Parsing (T004)
# =============================================================================


def _parse_agent_config(agent_id: str, data: dict[str, Any]) -> AgentConfig:
    """Parse a single agent configuration from YAML data."""
    return AgentConfig(
        agent_id=agent_id,
        enabled=data.get("enabled", True),
        roles=data.get("roles", ["implementation", "review"]),
        priority=data.get("priority", AGENT_PRIORITIES.get(agent_id, 50)),
        max_concurrent=data.get("max_concurrent", 2),
        timeout_seconds=data.get("timeout_seconds", 600),
    )


def _parse_fallback_strategy(value: str) -> FallbackStrategy:
    """Parse fallback strategy from string."""
    try:
        return FallbackStrategy(value)
    except ValueError:
        valid = [s.value for s in FallbackStrategy]
        raise ConfigValidationError(
            f"Invalid fallback_strategy '{value}'. Must be one of: {valid}"
        )


def parse_config(data: dict[str, Any]) -> OrchestratorConfig:
    """Parse raw YAML data into OrchestratorConfig.

    Args:
        data: Dictionary loaded from YAML file.

    Returns:
        Parsed OrchestratorConfig instance.
    """
    # Parse agents
    agents: dict[str, AgentConfig] = {}
    agents_data = data.get("agents", {})
    for agent_id, agent_data in agents_data.items():
        if isinstance(agent_data, dict):
            agents[agent_id] = _parse_agent_config(agent_id, agent_data)
        else:
            # Simple enabled/disabled format
            agents[agent_id] = AgentConfig(
                agent_id=agent_id,
                enabled=bool(agent_data),
            )

    # Parse single_agent_mode
    single_agent_mode_data = data.get("single_agent_mode", {})
    if isinstance(single_agent_mode_data, dict):
        single_agent_mode = single_agent_mode_data.get("enabled", False)
        single_agent = single_agent_mode_data.get("agent")
    else:
        single_agent_mode = bool(single_agent_mode_data)
        single_agent = None

    # Parse fallback strategy
    fallback_str = data.get("fallback_strategy", "next_in_list")
    fallback_strategy = _parse_fallback_strategy(fallback_str)

    return OrchestratorConfig(
        version=data.get("version", "1.0"),
        defaults=data.get("defaults", {}),
        agents=agents,
        fallback_strategy=fallback_strategy,
        max_retries=data.get("max_retries", 3),
        single_agent_mode=single_agent_mode,
        single_agent=single_agent,
        global_concurrency=data.get("global_concurrency", 5),
        global_timeout=data.get("global_timeout", 3600),
    )


def validate_config(config: OrchestratorConfig) -> None:
    """Validate orchestrator configuration.

    Args:
        config: Configuration to validate.

    Raises:
        ConfigValidationError: If validation fails.
    """
    errors: list[str] = []

    # Check defaults reference existing agents
    for role, agent_ids in config.defaults.items():
        for agent_id in agent_ids:
            if agent_id not in config.agents:
                errors.append(
                    f"defaults.{role} references unknown agent '{agent_id}'"
                )

    # Check single_agent_mode configuration
    if config.single_agent_mode:
        if not config.single_agent:
            errors.append(
                "single_agent_mode is enabled but no agent specified"
            )
        elif config.single_agent not in config.agents:
            errors.append(
                f"single_agent '{config.single_agent}' not found in agents"
            )
        elif not config.agents[config.single_agent].enabled:
            errors.append(
                f"single_agent '{config.single_agent}' is not enabled"
            )

    # Check numeric constraints
    if config.max_retries < 0:
        errors.append(f"max_retries must be >= 0, got {config.max_retries}")

    if config.global_concurrency < 1:
        errors.append(
            f"global_concurrency must be >= 1, got {config.global_concurrency}"
        )

    if config.global_timeout < 1:
        errors.append(
            f"global_timeout must be >= 1, got {config.global_timeout}"
        )

    # Check at least one agent is enabled
    enabled_agents = [
        aid for aid, ac in config.agents.items()
        if ac.enabled
    ]
    if not enabled_agents:
        errors.append("No agents are enabled in configuration")

    if errors:
        raise ConfigValidationError(
            "Configuration validation failed:\n  - " + "\n  - ".join(errors)
        )


def load_config(config_path: Path) -> OrchestratorConfig:
    """Load and validate orchestrator configuration from YAML file.

    If the config file doesn't exist, generates a default configuration
    based on installed agents.

    Args:
        config_path: Path to agents.yaml file.

    Returns:
        Validated OrchestratorConfig instance.

    Raises:
        ConfigValidationError: If configuration is invalid.
        NoAgentsError: If no agents are installed.
    """
    if not config_path.exists():
        logger.info(f"Config file not found at {config_path}, generating defaults")
        return generate_default_config()

    yaml = YAML()
    yaml.preserve_quotes = True

    try:
        with open(config_path) as f:
            data = yaml.load(f)
    except Exception as e:
        raise ConfigValidationError(f"Failed to parse YAML: {e}")

    if not data:
        logger.info("Config file is empty, generating defaults")
        return generate_default_config()

    config = parse_config(data)
    validate_config(config)

    logger.info(f"Loaded config from {config_path}")
    return config


# =============================================================================
# Default Config Generation (T005)
# =============================================================================


def generate_default_config() -> OrchestratorConfig:
    """Generate default configuration based on installed agents.

    Detects which agents are installed and creates a configuration
    with sensible defaults.

    Returns:
        OrchestratorConfig with detected agents.

    Raises:
        NoAgentsError: If no agents are installed.
    """
    installed = detect_installed_agents()

    if not installed:
        raise NoAgentsError(
            "No AI agents are installed.\n\n"
            "Install at least one agent to use orchestration:\n"
            "  npm install -g @anthropic-ai/claude-code\n"
            "  npm install -g codex\n"
            "  npm install -g opencode\n\n"
            "See documentation for other supported agents."
        )

    logger.info(f"Detected {len(installed)} installed agents: {', '.join(installed)}")

    # Create agent configs sorted by priority
    # No artificial per-agent limits - let dependency graph determine parallelism
    agents: dict[str, AgentConfig] = {}
    for agent_id in installed:
        agents[agent_id] = AgentConfig(
            agent_id=agent_id,
            enabled=True,
            roles=["implementation", "review"],
            priority=AGENT_PRIORITIES.get(agent_id, 50),
            max_concurrent=100,  # Effectively unlimited
            timeout_seconds=600,
        )

    # Sort by priority for defaults
    sorted_agents = sorted(installed, key=lambda x: AGENT_PRIORITIES.get(x, 50))

    # Set defaults based on installed agents
    defaults = {
        "implementation": sorted_agents.copy(),
        "review": sorted_agents.copy(),
    }

    # Determine if single-agent mode should be auto-enabled
    single_agent_mode = len(installed) == 1
    single_agent = installed[0] if single_agent_mode else None

    config = OrchestratorConfig(
        version="1.0",
        defaults=defaults,
        agents=agents,
        fallback_strategy=FallbackStrategy.NEXT_IN_LIST,
        max_retries=3,
        single_agent_mode=single_agent_mode,
        single_agent=single_agent,
        global_concurrency=100,  # Effectively unlimited - dependency graph is the limit
        global_timeout=3600,
    )

    return config


def save_config(config: OrchestratorConfig, config_path: Path) -> None:
    """Save orchestrator configuration to YAML file.

    Args:
        config: Configuration to save.
        config_path: Path to write the YAML file.
    """
    yaml = YAML()
    yaml.default_flow_style = False

    # Convert to serializable dict
    data = {
        "version": config.version,
        "defaults": config.defaults,
        "agents": {
            agent_id: {
                "enabled": ac.enabled,
                "roles": ac.roles,
                "priority": ac.priority,
                "max_concurrent": ac.max_concurrent,
                "timeout_seconds": ac.timeout_seconds,
            }
            for agent_id, ac in config.agents.items()
        },
        "fallback_strategy": config.fallback_strategy.value,
        "max_retries": config.max_retries,
        "single_agent_mode": {
            "enabled": config.single_agent_mode,
            "agent": config.single_agent,
        },
        "global_concurrency": config.global_concurrency,
        "global_timeout": config.global_timeout,
    }

    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        yaml.dump(data, f)

    logger.info(f"Saved config to {config_path}")
