"""Agent directory configuration utilities.

This module provides constants and functions for working with AI agent directories
across the spec-kitty project. All migrations and commands should import from here
rather than from migration files.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple


from specify_cli.core.agent_surface import get_agent_dir_to_key, get_agent_dirs

# Canonical list derived from AGENT_SURFACE_CONFIG
AGENT_DIRS: List[Tuple[str, str]] = get_agent_dirs()

# Mapping derived from AGENT_SURFACE_CONFIG
AGENT_DIR_TO_KEY: dict[str, str] = get_agent_dir_to_key()


def get_agent_dirs_for_project(project_path: Path) -> List[Tuple[str, str]]:
    """Get agent directories to process based on project config.

    Reads config.yaml to determine which agents are enabled.
    Only returns directories for configured agents.
    Falls back to all agents for legacy projects without config.

    Args:
        project_path: Path to project root

    Returns:
        List of (agent_root, subdir) tuples for configured agents

    Examples:
        >>> # Project with only Claude and Codex configured
        >>> dirs = get_agent_dirs_for_project(Path("/path/to/project"))
        >>> dirs
        [('.claude', 'commands'), ('.codex', 'prompts')]

        >>> # Legacy project without config.yaml
        >>> dirs = get_agent_dirs_for_project(Path("/path/to/legacy"))
        >>> len(dirs)
        12  # All agents
    """
    try:
        from specify_cli.core.agent_config import (
            AgentConfigError,
            get_configured_agents,
        )

        available = get_configured_agents(project_path)

        if not available:
            # Empty config - fallback to all agents
            return list(AGENT_DIRS)

        # Filter AGENT_DIRS to only include configured agents
        configured_dirs = []
        for agent_root, subdir in AGENT_DIRS:
            agent_key = AGENT_DIR_TO_KEY.get(agent_root)
            if agent_key in available:
                configured_dirs.append((agent_root, subdir))

        return configured_dirs

    except AgentConfigError:
        raise
    except Exception:
        # Config missing or error reading - fallback to all agents
        # This handles legacy projects gracefully
        return list(AGENT_DIRS)
