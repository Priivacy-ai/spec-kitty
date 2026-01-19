"""Agent invokers for the orchestrator.

This subpackage contains implementations of AgentInvoker for each supported
AI coding agent. Each invoker knows how to:
    - Build the command line for that agent
    - Pipe prompts via stdin or file
    - Parse output and detect success/failure

Supported Agents (WP02 - Core):
    - claude-code: Claude Code (Anthropic)
    - codex: GitHub Codex
    - copilot: GitHub Copilot
    - gemini: Google Gemini

Additional agents (WP03):
    - qwen: Qwen Code
    - opencode: OpenCode
    - kilocode: Kilocode
    - augment: Augment Code (auggie)
    - cursor: Cursor (with timeout wrapper)
"""

from specify_cli.orchestrator.agents.base import (
    AgentInvoker,
    BaseInvoker,
    InvocationResult,
)
from specify_cli.orchestrator.agents.claude import ClaudeInvoker
from specify_cli.orchestrator.agents.codex import CodexInvoker
from specify_cli.orchestrator.agents.copilot import CopilotInvoker
from specify_cli.orchestrator.agents.gemini import GeminiInvoker

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
]
