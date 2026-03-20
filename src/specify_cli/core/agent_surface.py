"""Canonical agent surface configuration registry.

This module is the single source of truth for all agent capabilities,
directory layouts, wrapper configs, and distribution classes. Other modules
(config.py, directories.py) derive their legacy constants from here.

IMPORTANT: This module must be self-contained — it must NOT import from
config.py or directories.py to avoid circular imports. The data flow is
one-directional: agent_surface.py defines -> config.py/directories.py derive.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DistributionClass(Enum):
    """How skill files are distributed to an agent's filesystem.

    - SHARED_ROOT_CAPABLE: Agent can read from a shared .agents/skills/ root
      in addition to its own native directory.
    - NATIVE_ROOT_REQUIRED: Agent only reads from its own native root directory.
    - WRAPPER_ONLY: Agent has no skill-file support; only wrappers (slash
      commands) can be installed.
    """

    SHARED_ROOT_CAPABLE = "shared-root-capable"
    NATIVE_ROOT_REQUIRED = "native-root-required"
    WRAPPER_ONLY = "wrapper-only"


@dataclass(frozen=True)
class WrapperConfig:
    """Configuration for generating slash-command wrapper files.

    Attributes:
        dir: Directory path relative to repo root where wrappers are placed.
        ext: File extension for wrapper files (e.g. "md", "prompt.md", "toml").
        arg_format: Placeholder format for arguments in wrapper content.
    """

    dir: str
    ext: str
    arg_format: str


@dataclass(frozen=True)
class AgentSurface:
    """Full capability profile for a single AI agent.

    Attributes:
        key: Unique agent identifier used in config.yaml and CLI commands.
        display_name: Human-readable agent name for UI display.
        distribution_class: How skills are distributed to this agent.
        agent_root: Top-level dotdir for this agent (e.g. ".claude").
        wrapper: Configuration for generating wrapper/slash-command files.
        wrapper_subdir: Subdirectory within agent_root for wrappers.
        skill_roots: Tuple of directories (relative to repo root) where this
            agent looks for skill files. Empty for WRAPPER_ONLY agents.
        compat_notes: Free-text notes about compatibility quirks.
    """

    key: str
    display_name: str
    distribution_class: DistributionClass
    agent_root: str
    wrapper: WrapperConfig
    wrapper_subdir: str
    skill_roots: tuple[str, ...]
    compat_notes: str = ""


# ---------------------------------------------------------------------------
# Canonical registry: the single source of truth for all 12 supported agents
# ---------------------------------------------------------------------------

AGENT_SURFACE_CONFIG: dict[str, AgentSurface] = {
    "claude": AgentSurface(
        key="claude",
        display_name="Claude Code",
        distribution_class=DistributionClass.NATIVE_ROOT_REQUIRED,
        agent_root=".claude",
        wrapper=WrapperConfig(dir=".claude/commands", ext="md", arg_format="$ARGUMENTS"),
        wrapper_subdir="commands",
        skill_roots=(".claude/skills/",),
        compat_notes="Commands merged into skills; also supports personal, plugin, enterprise, nested project skills",
    ),
    "copilot": AgentSurface(
        key="copilot",
        display_name="GitHub Copilot",
        distribution_class=DistributionClass.SHARED_ROOT_CAPABLE,
        agent_root=".github",
        wrapper=WrapperConfig(dir=".github/prompts", ext="prompt.md", arg_format="$ARGUMENTS"),
        wrapper_subdir="prompts",
        skill_roots=(".agents/skills/", ".github/skills/"),
        compat_notes="Also scans .claude/skills/; user roots, plugin dirs, COPILOT_SKILLS_DIRS",
    ),
    "gemini": AgentSurface(
        key="gemini",
        display_name="Gemini CLI",
        distribution_class=DistributionClass.SHARED_ROOT_CAPABLE,
        agent_root=".gemini",
        wrapper=WrapperConfig(dir=".gemini/commands", ext="toml", arg_format="{{args}}"),
        wrapper_subdir="commands",
        skill_roots=(".agents/skills/", ".gemini/skills/"),
        compat_notes="",
    ),
    "cursor": AgentSurface(
        key="cursor",
        display_name="Cursor",
        distribution_class=DistributionClass.SHARED_ROOT_CAPABLE,
        agent_root=".cursor",
        wrapper=WrapperConfig(dir=".cursor/commands", ext="md", arg_format="$ARGUMENTS"),
        wrapper_subdir="commands",
        skill_roots=(".agents/skills/", ".cursor/skills/"),
        compat_notes="",
    ),
    "qwen": AgentSurface(
        key="qwen",
        display_name="Qwen Code",
        distribution_class=DistributionClass.NATIVE_ROOT_REQUIRED,
        agent_root=".qwen",
        wrapper=WrapperConfig(dir=".qwen/commands", ext="toml", arg_format="{{args}}"),
        wrapper_subdir="commands",
        skill_roots=(".qwen/skills/",),
        compat_notes="",
    ),
    "opencode": AgentSurface(
        key="opencode",
        display_name="opencode",
        distribution_class=DistributionClass.SHARED_ROOT_CAPABLE,
        agent_root=".opencode",
        wrapper=WrapperConfig(dir=".opencode/command", ext="md", arg_format="$ARGUMENTS"),
        wrapper_subdir="command",
        skill_roots=(".agents/skills/", ".opencode/skills/"),
        compat_notes="",
    ),
    "windsurf": AgentSurface(
        key="windsurf",
        display_name="Windsurf",
        distribution_class=DistributionClass.SHARED_ROOT_CAPABLE,
        agent_root=".windsurf",
        wrapper=WrapperConfig(dir=".windsurf/workflows", ext="md", arg_format="$ARGUMENTS"),
        wrapper_subdir="workflows",
        skill_roots=(".agents/skills/", ".windsurf/skills/"),
        compat_notes="",
    ),
    "codex": AgentSurface(
        key="codex",
        display_name="Codex CLI",
        distribution_class=DistributionClass.SHARED_ROOT_CAPABLE,
        agent_root=".codex",
        wrapper=WrapperConfig(dir=".codex/prompts", ext="md", arg_format="$ARGUMENTS"),
        wrapper_subdir="prompts",
        skill_roots=(".agents/skills/",),
        compat_notes="",
    ),
    "kilocode": AgentSurface(
        key="kilocode",
        display_name="Kilo Code",
        distribution_class=DistributionClass.NATIVE_ROOT_REQUIRED,
        agent_root=".kilocode",
        wrapper=WrapperConfig(dir=".kilocode/workflows", ext="md", arg_format="$ARGUMENTS"),
        wrapper_subdir="workflows",
        skill_roots=(".kilocode/skills/",),
        compat_notes="",
    ),
    "auggie": AgentSurface(
        key="auggie",
        display_name="Auggie CLI",
        distribution_class=DistributionClass.SHARED_ROOT_CAPABLE,
        agent_root=".augment",
        wrapper=WrapperConfig(dir=".augment/commands", ext="md", arg_format="$ARGUMENTS"),
        wrapper_subdir="commands",
        skill_roots=(".agents/skills/", ".augment/skills/"),
        compat_notes="",
    ),
    "roo": AgentSurface(
        key="roo",
        display_name="Roo Code",
        distribution_class=DistributionClass.SHARED_ROOT_CAPABLE,
        agent_root=".roo",
        wrapper=WrapperConfig(dir=".roo/commands", ext="md", arg_format="$ARGUMENTS"),
        wrapper_subdir="commands",
        skill_roots=(".agents/skills/", ".roo/skills/"),
        compat_notes="",
    ),
    "q": AgentSurface(
        key="q",
        display_name="Amazon Q Developer CLI",
        distribution_class=DistributionClass.WRAPPER_ONLY,
        agent_root=".amazonq",
        wrapper=WrapperConfig(dir=".amazonq/prompts", ext="md", arg_format="$ARGUMENTS"),
        wrapper_subdir="prompts",
        skill_roots=(),
        compat_notes="",
    ),
}


# ---------------------------------------------------------------------------
# Derived view functions — produce legacy-compatible data shapes
# ---------------------------------------------------------------------------


def get_agent_command_config() -> dict[str, dict[str, str]]:
    """Derive AGENT_COMMAND_CONFIG-compatible dict from canonical config.

    Returns:
        Dict mapping agent key to {"dir": ..., "ext": ..., "arg_format": ...}
        with byte-exact values matching the old hardcoded AGENT_COMMAND_CONFIG.
    """
    return {
        key: {"dir": s.wrapper.dir, "ext": s.wrapper.ext, "arg_format": s.wrapper.arg_format}
        for key, s in AGENT_SURFACE_CONFIG.items()
    }


def get_agent_dirs() -> list[tuple[str, str]]:
    """Derive AGENT_DIRS-compatible list from canonical config.

    Returns:
        List of (agent_root, wrapper_subdir) tuples in canonical order,
        matching the old hardcoded AGENT_DIRS exactly.
    """
    return [(s.agent_root, s.wrapper_subdir) for s in AGENT_SURFACE_CONFIG.values()]


def get_agent_dir_to_key() -> dict[str, str]:
    """Derive AGENT_DIR_TO_KEY-compatible dict from canonical config.

    Returns:
        Dict mapping agent_root (e.g. ".github") to agent key (e.g. "copilot"),
        matching the old hardcoded AGENT_DIR_TO_KEY exactly.
    """
    return {s.agent_root: s.key for s in AGENT_SURFACE_CONFIG.values()}


def get_agent_surface(agent_key: str) -> AgentSurface:
    """Return full capability profile for one agent.

    Args:
        agent_key: The agent's unique identifier (e.g. "claude", "copilot").

    Returns:
        The AgentSurface for the requested agent.

    Raises:
        KeyError: If agent_key is not in AGENT_SURFACE_CONFIG.
    """
    return AGENT_SURFACE_CONFIG[agent_key]


__all__ = [
    "AgentSurface",
    "AGENT_SURFACE_CONFIG",
    "DistributionClass",
    "WrapperConfig",
    "get_agent_command_config",
    "get_agent_dir_to_key",
    "get_agent_dirs",
    "get_agent_surface",
]
