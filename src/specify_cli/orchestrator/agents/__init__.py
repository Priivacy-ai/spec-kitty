"""Agent invokers for the orchestrator.

This subpackage contains implementations of AgentInvoker for each supported
AI coding agent. Each invoker knows how to:
    - Build the command line for that agent
    - Pipe prompts via stdin or file
    - Parse output and detect success/failure

Supported Agents:
    - claude-code: Claude Code (Anthropic)
    - codex: GitHub Codex
    - copilot: GitHub Copilot
    - gemini: Google Gemini
    - qwen: Qwen Code
    - opencode: OpenCode
    - kilocode: Kilocode
    - augment: Augment Code (auggie)
    - cursor: Cursor (with timeout wrapper)
"""

# Agent invokers will be exported here after WP02/WP03 implementation
__all__: list[str] = []
