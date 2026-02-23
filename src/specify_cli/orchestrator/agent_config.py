"""Agent configuration for the orchestrator.

This module manages agent configuration that is set during `spec-kitty init`
and used by the orchestrator and related commands to determine which agents are enabled.

The configuration is stored in .kittify/config.yaml under the `agents` key.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from specify_cli.core.config import AI_CHOICES

import logging

logger = logging.getLogger(__name__)


class AgentConfigError(RuntimeError):
    """Raised when .kittify/config.yaml cannot be parsed or validated."""


@dataclass
class AgentConfig:
    """Full agent configuration.

    Attributes:
        available: List of agent IDs that are available for use
    """

    available: list[str] = field(default_factory=list)


def load_agent_config(repo_root: Path) -> AgentConfig:
    """Load agent configuration from .kittify/config.yaml.

    Args:
        repo_root: Repository root directory

    Returns:
        AgentConfig instance (defaults if not configured)
    """
    config_file = repo_root / ".kittify" / "config.yaml"

    if not config_file.exists():
        logger.warning(f"Config file not found: {config_file}")
        return AgentConfig()

    yaml = YAML()
    yaml.preserve_quotes = True

    try:
        with open(config_file, "r") as f:
            data = yaml.load(f) or {}
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise AgentConfigError(
            f"Invalid YAML in {config_file}: {e}"
        ) from e

    agents_data = data.get("agents", {})
    if not agents_data:
        logger.info("No agents section in config.yaml")
        return AgentConfig()

    # Parse available agents
    available = agents_data.get("available", [])
    if isinstance(available, str):
        available = [available]
    if not isinstance(available, list):
        raise AgentConfigError(
            "Invalid agents.available in config.yaml: expected a list of agent keys"
        )

    invalid_agents = [agent for agent in available if agent not in AI_CHOICES]
    if invalid_agents:
        valid_agents = ", ".join(sorted(AI_CHOICES.keys()))
        unknown = ", ".join(sorted(invalid_agents))
        raise AgentConfigError(
            f"Unknown agent key(s) in config.yaml: {unknown}. "
            f"Valid agents: {valid_agents}"
        )

    # Ignore any legacy role-preference fields that may still exist in old configs.
    return AgentConfig(available=available)


def save_agent_config(repo_root: Path, config: AgentConfig) -> None:
    """Save agent configuration to .kittify/config.yaml.

    Merges with existing config (preserves other sections like vcs).

    Args:
        repo_root: Repository root directory
        config: AgentConfig to save
    """
    config_dir = repo_root / ".kittify"
    config_file = config_dir / "config.yaml"

    yaml = YAML()
    yaml.preserve_quotes = True

    # Load existing config or create new
    if config_file.exists():
        with open(config_file, "r") as f:
            data = yaml.load(f) or {}
    else:
        data = {}
        config_dir.mkdir(parents=True, exist_ok=True)

    # Update agents section
    data["agents"] = {
        "available": config.available,
    }

    # Write back
    with open(config_file, "w") as f:
        yaml.dump(data, f)

    logger.info(f"Saved agent config to {config_file}")


def get_configured_agents(repo_root: Path) -> list[str]:
    """Get list of configured agents.

    This is the DEFINITIVE list of available agents, set during init.

    Args:
        repo_root: Repository root directory

    Returns:
        List of agent IDs, empty if not configured
    """
    config = load_agent_config(repo_root)
    return config.available


__all__ = [
    "AgentConfig",
    "AgentConfigError",
    "load_agent_config",
    "save_agent_config",
    "get_configured_agents",
]
