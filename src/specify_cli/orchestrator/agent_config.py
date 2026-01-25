"""Agent configuration for the orchestrator.

This module manages agent configuration that is set during `spec-kitty init`
and used by the orchestrator to select agents for implementation and review.

The configuration is stored in .kittify/config.yaml under the `agents` key.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from specify_cli.core.config import AI_CHOICES

import logging

logger = logging.getLogger(__name__)


class AgentConfigError(RuntimeError):
    """Raised when .kittify/config.yaml cannot be parsed or validated."""


class SelectionStrategy(str, Enum):
    """Strategy for selecting agents."""

    PREFERRED = "preferred"  # Use user-specified preferred agents
    RANDOM = "random"  # Randomly select from available agents


@dataclass
class AgentSelectionConfig:
    """Configuration for agent selection.

    Attributes:
        strategy: How to select agents (preferred or random)
        preferred_implementer: Agent ID for implementation (if strategy=preferred)
        preferred_reviewer: Agent ID for review (if strategy=preferred)
    """

    strategy: SelectionStrategy = SelectionStrategy.PREFERRED
    preferred_implementer: str | None = None
    preferred_reviewer: str | None = None


@dataclass
class AgentConfig:
    """Full agent configuration.

    Attributes:
        available: List of agent IDs that are available for use
        selection: Configuration for how to select agents
    """

    available: list[str] = field(default_factory=list)
    selection: AgentSelectionConfig = field(default_factory=AgentSelectionConfig)

    def select_implementer(self, exclude: str | None = None) -> str | None:
        """Select an agent for implementation.

        Args:
            exclude: Optional agent ID to exclude from selection

        Returns:
            Selected agent ID or None if no agents available
        """
        candidates = [a for a in self.available if a != exclude]
        if not candidates:
            return None

        if self.selection.strategy == SelectionStrategy.PREFERRED:
            if self.selection.preferred_implementer in candidates:
                return self.selection.preferred_implementer
            # Fall back to first available
            return candidates[0]
        else:  # RANDOM
            return random.choice(candidates)

    def select_reviewer(self, implementer: str | None = None) -> str | None:
        """Select an agent for review.

        Prefers a different agent than the implementer for cross-review.

        Args:
            implementer: Agent that did implementation (prefer different agent)

        Returns:
            Selected agent ID or None if no agents available
        """
        # Prefer different agent for cross-review
        candidates = [a for a in self.available if a != implementer]

        # Fall back to same agent if no other available
        if not candidates:
            candidates = self.available.copy()

        if not candidates:
            return None

        if self.selection.strategy == SelectionStrategy.PREFERRED:
            if self.selection.preferred_reviewer in candidates:
                return self.selection.preferred_reviewer
            # Fall back to first available that's not the implementer
            return candidates[0]
        else:  # RANDOM
            return random.choice(candidates)


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

    # Parse selection config
    selection_data = agents_data.get("selection", {})
    strategy_str = selection_data.get("strategy", "preferred")
    try:
        strategy = SelectionStrategy(strategy_str)
    except ValueError:
        logger.warning(f"Invalid strategy '{strategy_str}', defaulting to 'preferred'")
        strategy = SelectionStrategy.PREFERRED

    selection = AgentSelectionConfig(
        strategy=strategy,
        preferred_implementer=selection_data.get("preferred_implementer"),
        preferred_reviewer=selection_data.get("preferred_reviewer"),
    )

    return AgentConfig(available=available, selection=selection)


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
        "selection": {
            "strategy": config.selection.strategy.value,
            "preferred_implementer": config.selection.preferred_implementer,
            "preferred_reviewer": config.selection.preferred_reviewer,
        },
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
    "SelectionStrategy",
    "AgentSelectionConfig",
    "AgentConfig",
    "AgentConfigError",
    "load_agent_config",
    "save_agent_config",
    "get_configured_agents",
]
