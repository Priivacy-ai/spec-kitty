"""Helpers for mapping canonical skill roots between project and user scopes."""

from __future__ import annotations

from pathlib import Path

from specify_cli.core.config import AGENT_SKILL_CONFIG, SKILL_CLASS_WRAPPER


def get_primary_project_skill_root(agent_key: str) -> str | None:
    """Return the primary project-local skill root for an agent."""
    config = AGENT_SKILL_CONFIG.get(agent_key)
    if config is None or config["class"] == SKILL_CLASS_WRAPPER:
        return None

    roots = config["skill_roots"]
    if not isinstance(roots, list) or not roots:
        return None

    return roots[0]


def get_primary_global_skill_root(agent_key: str) -> Path | None:
    """Return the user-global canonical skill root for an agent.

    The global root mirrors the project-local root beneath the user's home
    directory, for example:

    - ``.claude/skills`` -> ``~/.claude/skills``
    - ``.agents/skills`` -> ``~/.agents/skills``
    """
    root = get_primary_project_skill_root(agent_key)
    if root is None:
        return None

    normalized = root.strip("/")
    return Path.home() / normalized


def iter_installable_agents() -> list[str]:
    """Return all agents that support a skill root."""
    installable: list[str] = []

    for agent_key, config in AGENT_SKILL_CONFIG.items():
        if config["class"] == SKILL_CLASS_WRAPPER:
            continue
        installable.append(agent_key)

    return installable
