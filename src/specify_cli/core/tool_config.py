"""Tool (AI agent) configuration (canonical location in core).

This module manages tool configuration that is set during `spec-kitty init`
and used by commands and migrations to select AI tools for implementation
and review.

The canonical configuration key in `.kittify/config.yaml` is `tools`.
Legacy projects may still use `agents`; that key is read as a fallback with
deprecation warning.

Previously named agent_config.py. The rename reflects that "agents" in this
context refers to AI tools/assistants, not autonomous agents in the
multi-agent orchestration sense.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML

from specify_cli.core.config import AI_CHOICES

import logging

logger = logging.getLogger(__name__)


class ToolConfigError(RuntimeError):
    """Raised when .kittify/config.yaml cannot be parsed or validated."""


@dataclass
class ToolSelectionConfig:
    """Configuration for preferred role assignment.

    Attributes:
        preferred_implementer: Tool ID to prefer for implementation tasks.
        preferred_reviewer: Tool ID to prefer for review tasks.
    """

    preferred_implementer: str | None = None
    preferred_reviewer: str | None = None


@dataclass
class ToolConfig:
    """Full tool (AI assistant) configuration.

    Attributes:
        available: List of tool IDs that are available for use
        selection: Configuration for how to select tools
        auto_commit: Whether agents should automatically commit after staging changes
    """

    available: list[str] = field(default_factory=list)
    selection: ToolSelectionConfig = field(default_factory=ToolSelectionConfig)
    auto_commit: bool = True

    def select_implementer(self, exclude: str | None = None) -> str | None:
        """Select a tool for implementation.

        Args:
            exclude: Optional tool ID to exclude from selection

        Returns:
            Selected tool ID or None if no tools available
        """
        candidates = [a for a in self.available if a != exclude]
        if not candidates:
            return None

        if self.selection.preferred_implementer in candidates:
            return self.selection.preferred_implementer
        # Fall back to first available
        return candidates[0]

    def select_reviewer(self, implementer: str | None = None) -> str | None:
        """Select a tool for review.

        Prefers a different tool than the implementer for cross-review.

        Args:
            implementer: Tool that did implementation (prefer different tool)

        Returns:
            Selected tool ID or None if no tools available
        """
        # Prefer different tool for cross-review
        candidates = [a for a in self.available if a != implementer]

        # Fall back to same tool if no other available
        if not candidates:
            candidates = self.available.copy()

        if not candidates:
            return None

        if self.selection.preferred_reviewer in candidates:
            return self.selection.preferred_reviewer
        # Fall back to first available that's not the implementer
        return candidates[0]


def load_tool_config(repo_root: Path) -> ToolConfig:
    """Load tool configuration from .kittify/config.yaml.

    Args:
        repo_root: Repository root directory

    Returns:
        ToolConfig instance (defaults if not configured)
    """
    config_file = repo_root / ".kittify" / "config.yaml"

    if not config_file.exists():
        logger.warning(f"Config file not found: {config_file}")
        return ToolConfig()

    yaml = YAML()
    yaml.preserve_quotes = True

    try:
        with open(config_file) as f:
            data = yaml.load(f) or {}
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise ToolConfigError(f"Invalid YAML in {config_file}: {e}") from e

    tools_data = data.get("tools")
    legacy_agents_data = data.get("agents")

    if tools_data is None and legacy_agents_data is None:
        logger.info("No tools/agents section in config.yaml")
        # Still check for top-level auto_commit before returning defaults.
        top_level = data.get("auto_commit", True)
        if not isinstance(top_level, bool):
            top_level = str(top_level).lower() not in ("false", "0", "no", "off")
        return ToolConfig(auto_commit=top_level)

    if tools_data is None and legacy_agents_data is not None:
        warnings.warn(
            "Config key '.kittify/config.yaml: agents' is deprecated; use 'tools' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        tools_data = legacy_agents_data
    elif tools_data is None:
        tools_data = {}

    # Parse available tools
    available = tools_data.get("available", [])
    if isinstance(available, str):
        available = [available]
    if not isinstance(available, list):
        raise ToolConfigError("Invalid tools.available in config.yaml: expected a list of tool keys")

    invalid_agents = [agent for agent in available if agent not in AI_CHOICES]
    if invalid_agents:
        valid_agents = ", ".join(sorted(AI_CHOICES.keys()))
        unknown = ", ".join(sorted(invalid_agents))
        raise ToolConfigError(
            f"Unknown tool key(s) in config.yaml: {unknown}. "
            f"Valid agents: {valid_agents}"
        )

    # Parse selection config (legacy strategy field ignored)
    selection_data = tools_data.get("selection", {})
    if not isinstance(selection_data, dict):
        selection_data = {}

    selection = ToolSelectionConfig(
        preferred_implementer=selection_data.get("preferred_implementer"),
        preferred_reviewer=selection_data.get("preferred_reviewer"),
    )

    # auto_commit: nested in tools section takes precedence; top-level is fallback.
    top_level_auto_commit = data.get("auto_commit", True)
    raw_auto_commit = tools_data.get("auto_commit", top_level_auto_commit)
    if not isinstance(raw_auto_commit, bool):
        raw_auto_commit = str(raw_auto_commit).lower() not in ("false", "0", "no", "off")
    auto_commit = raw_auto_commit

    return ToolConfig(available=available, selection=selection, auto_commit=auto_commit)


def save_tool_config(repo_root: Path, config: ToolConfig) -> None:
    """Save tool configuration to .kittify/config.yaml.

    Merges with existing config (preserves other sections like vcs).

    Args:
        repo_root: Repository root directory
        config: ToolConfig to save
    """
    config_dir = repo_root / ".kittify"
    config_file = config_dir / "config.yaml"

    yaml = YAML()
    yaml.preserve_quotes = True

    # Load existing config or create new
    if config_file.exists():
        with open(config_file) as f:
            data = yaml.load(f) or {}
    else:
        data = {}
        config_dir.mkdir(parents=True, exist_ok=True)

    # Update canonical tools section.
    data["tools"] = {
        "available": config.available,
        "auto_commit": config.auto_commit,
        "selection": {
            "preferred_implementer": config.selection.preferred_implementer,
            "preferred_reviewer": config.selection.preferred_reviewer,
        },
    }
    # Remove legacy key on save to complete migration in-place.
    if "agents" in data:
        del data["agents"]

    # Write back
    with open(config_file, "w") as f:
        yaml.dump(data, f)

    logger.info(f"Saved tool config to {config_file}")


def get_configured_tools(repo_root: Path) -> list[str]:
    """Get list of configured tools.

    This is the DEFINITIVE list of available tools, set during init.

    Args:
        repo_root: Repository root directory

    Returns:
        List of tool IDs, empty if not configured
    """
    config = load_tool_config(repo_root)
    return config.available


def get_auto_commit_default(repo_root: Path) -> bool:
    """Get the auto_commit default from project config.

    Returns True if auto-commit is enabled (the default), False if disabled.
    """
    config = load_tool_config(repo_root)
    return config.auto_commit


__all__ = [
    "ToolSelectionConfig",
    "ToolConfig",
    "ToolConfigError",
    "load_tool_config",
    "save_tool_config",
    "get_configured_tools",
    "get_auto_commit_default",
]
