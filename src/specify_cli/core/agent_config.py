"""Canonical agent configuration helpers.

This module stores and loads agent availability from `.kittify/config.yaml`.
It intentionally keeps only `agents.available` and ignores deprecated
orchestration strategy fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

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
        available: List of agent IDs that are available for use.
    """

    available: list[str] = field(default_factory=list)


def load_agent_config(repo_root: Path) -> AgentConfig:
    """Load agent configuration from .kittify/config.yaml."""
    config_file = repo_root / ".kittify" / "config.yaml"

    if not config_file.exists():
        logger.warning("Config file not found: %s", config_file)
        return AgentConfig()

    yaml = YAML()
    yaml.preserve_quotes = True

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.load(f) or {}
    except Exception as exc:
        logger.error("Failed to load config: %s", exc)
        raise AgentConfigError(f"Invalid YAML in {config_file}: {exc}") from exc

    agents_data = data.get("agents", {})
    if not agents_data:
        logger.info("No agents section in config.yaml")
        return AgentConfig()

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

    return AgentConfig(available=available)


def save_agent_config(repo_root: Path, config: AgentConfig) -> None:
    """Save agent configuration to .kittify/config.yaml.

    Merges with existing config and preserves unrelated sections.
    """
    config_dir = repo_root / ".kittify"
    config_file = config_dir / "config.yaml"

    yaml = YAML()
    yaml.preserve_quotes = True

    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.load(f) or {}
    else:
        data = {}
        config_dir.mkdir(parents=True, exist_ok=True)

    data["agents"] = {
        "available": config.available,
    }

    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

    logger.info("Saved agent config to %s", config_file)


def get_configured_agents(repo_root: Path) -> list[str]:
    """Return configured agents (possibly empty)."""
    return load_agent_config(repo_root).available


__all__ = [
    "AgentConfig",
    "AgentConfigError",
    "load_agent_config",
    "save_agent_config",
    "get_configured_agents",
]
