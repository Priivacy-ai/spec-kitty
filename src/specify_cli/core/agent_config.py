"""Deprecated: Use specify_cli.core.tool_config instead.

This module is a compatibility shim that re-exports the renamed symbols from
tool_config.py. It will be removed in a future release.
"""

from __future__ import annotations

import warnings

from specify_cli.core.tool_config import (
    ToolConfig as AgentConfig,
    ToolSelectionConfig as AgentSelectionConfig,
    ToolConfigError as AgentConfigError,
    load_tool_config as load_agent_config,
    save_tool_config as save_agent_config,
    get_configured_tools as get_configured_agents,
)

warnings.warn(
    "specify_cli.core.agent_config is deprecated. Use specify_cli.core.tool_config instead.",
    DeprecationWarning,
    stacklevel=2,
)

def get_auto_commit_default(repo_root: Path) -> bool:
    """Get the auto_commit default from project config.

    This is the project-level setting that commands should use as their
    default for auto-commit behavior. Per-command flags (--auto-commit/
    --no-auto-commit) override this value.

    Args:
        repo_root: Repository root directory

    Returns:
        True if auto-commit is enabled (the default), False if disabled
    """
    config = load_agent_config(repo_root)
    return config.auto_commit


__all__ = [
    "AgentConfig",
    "AgentSelectionConfig",
    "AgentConfigError",
    "load_agent_config",
    "save_agent_config",
    "get_configured_agents",
    "get_auto_commit_default",
]
