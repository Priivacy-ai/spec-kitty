"""Agent invokers for the orchestrator.

This subpackage contains implementations of AgentInvoker for each supported
AI coding agent. Each invoker knows how to:
    - Build the command line for that agent
    - Pipe prompts via stdin or file
    - Parse output and detect success/failure

Supported Agents (9 total):
    Core (WP02):
    - claude-code: Claude Code (Anthropic)
    - codex: GitHub Codex
    - copilot: GitHub Copilot
    - gemini: Google Gemini

    Additional (WP03):
    - qwen: Qwen Code
    - opencode: OpenCode
    - kilocode: Kilocode
    - augment: Augment Code (auggie)
    - cursor: Cursor (with timeout wrapper)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from specify_cli.orchestrator.agents.augment import AugmentInvoker
from specify_cli.orchestrator.agents.base import (
    AgentInvoker,
    BaseInvoker,
    InvocationResult,
)
from specify_cli.orchestrator.agents.claude import ClaudeInvoker
from specify_cli.orchestrator.agents.codex import CodexInvoker
from specify_cli.orchestrator.agents.copilot import CopilotInvoker
from specify_cli.orchestrator.agents.cursor import CursorInvoker
from specify_cli.orchestrator.agents.gemini import GeminiInvoker
from specify_cli.orchestrator.agents.kilocode import KilocodeInvoker
from specify_cli.orchestrator.agents.opencode import OpenCodeInvoker
from specify_cli.orchestrator.agents.qwen import QwenInvoker

if TYPE_CHECKING:
    pass

# Registry mapping agent IDs to invoker classes
AGENT_REGISTRY: dict[str, type[BaseInvoker]] = {
    "claude-code": ClaudeInvoker,
    "codex": CodexInvoker,
    "copilot": CopilotInvoker,
    "gemini": GeminiInvoker,
    "qwen": QwenInvoker,
    "opencode": OpenCodeInvoker,
    "kilocode": KilocodeInvoker,
    "augment": AugmentInvoker,
    "cursor": CursorInvoker,
}

# Aliases for user-friendly names to canonical registry names
# These match the keys used in AI_CHOICES (core/config.py) and .kittify/config.yaml
AGENT_ALIASES: dict[str, str] = {
    "claude": "claude-code",  # User-facing name -> registry name
    "auggie": "augment",      # Alternative name used in gitignore_manager
}

# Priority order for agent selection (lower index = higher priority)
# Based on feature 019 research recommendations
AGENT_PRIORITY_ORDER = [
    "claude-code",
    "codex",
    "copilot",
    "gemini",
    "qwen",
    "opencode",
    "kilocode",
    "augment",
    "cursor",
]


def normalize_agent_id(agent_id: str) -> str:
    """Normalize agent ID to canonical registry name.

    Resolves user-friendly aliases (e.g., "claude" -> "claude-code").

    Args:
        agent_id: User-provided agent ID (may be an alias).

    Returns:
        Canonical agent ID used in AGENT_REGISTRY.
    """
    return AGENT_ALIASES.get(agent_id, agent_id)


def get_invoker(agent_id: str) -> BaseInvoker:
    """Get invoker instance for agent ID.

    Args:
        agent_id: The agent identifier (e.g., "claude-code", "codex").
                  Aliases like "claude" are automatically resolved.

    Returns:
        Instantiated invoker for the specified agent.

    Raises:
        ValueError: If agent_id is not recognized.
    """
    # Resolve aliases to canonical names
    canonical_id = normalize_agent_id(agent_id)

    invoker_class = AGENT_REGISTRY.get(canonical_id)
    if not invoker_class:
        valid_agents = ", ".join(sorted(AGENT_REGISTRY.keys()))
        # Include aliases in the error message for clarity
        alias_info = ", ".join(f"{k}->{v}" for k, v in AGENT_ALIASES.items())
        raise ValueError(
            f"Unknown agent: {agent_id}. Valid agents: {valid_agents}. "
            f"Aliases: {alias_info}"
        )
    return invoker_class()


def detect_installed_agents() -> list[str]:
    """Detect which agents are installed on the system.

    Returns:
        List of installed agent IDs, sorted by default priority
        (claude-code first, cursor last).
    """
    installed = []
    for agent_id, invoker_class in AGENT_REGISTRY.items():
        invoker = invoker_class()
        if invoker.is_installed():
            installed.append(agent_id)

    # Sort by priority order
    return sorted(
        installed,
        key=lambda x: (
            AGENT_PRIORITY_ORDER.index(x)
            if x in AGENT_PRIORITY_ORDER
            else 999
        ),
    )


__all__ = [
    # Protocol and base classes
    "AgentInvoker",
    "BaseInvoker",
    "InvocationResult",
    # Core invokers (WP02)
    "ClaudeInvoker",
    "CodexInvoker",
    "CopilotInvoker",
    "GeminiInvoker",
    # Additional invokers (WP03)
    "QwenInvoker",
    "OpenCodeInvoker",
    "KilocodeInvoker",
    "AugmentInvoker",
    "CursorInvoker",
    # Registry and utilities
    "AGENT_REGISTRY",
    "AGENT_ALIASES",
    "AGENT_PRIORITY_ORDER",
    "get_invoker",
    "normalize_agent_id",
    "detect_installed_agents",
]
