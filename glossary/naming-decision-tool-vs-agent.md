## Naming Decision: Tool vs Agent

**Date**: 2026-02-15
**Status**: Agreed — apply in Doctrine integration features (040-044+)

**Problem**: Spec-kitty used "agent" to mean the CLI tooling (Claude Code, OpenCode, etc.). New specifications uses "agent" to mean a role-based identity with capabilities and behavioral rules. Using "agent" for both creates collisions.

**Resolution**: Split into two distinct concepts:
- **Tool** = the CLI executable (claude, opencode, codex)
- **Agent** = the Doctrine identity (Python Pedro, Review Rachel)

**Migration**: Canonical glossary language uses `tool` terminology. Current implementation still contains mixed legacy `agent` identifiers and command groups, so migration remains in progress with compatibility mapping.

| Legacy (pre-Doctrine) | Current term |
|----------------------|--------------|
| `AgentInvoker` | `ToolInvoker` |
| `AgentConfig` | `ToolConfig` |
| `agent_id` | `tool_id` |
| `select_agent()` | `select_tool()` |
| `--impl-agent` | `--impl-tool` |
| `--review-agent` | `--review-tool` |
| `agents:` (config) | `tools:` |
| `spec-kitty agent` | `spec-kitty tool` (target canonical naming; CLI group is still `agent` today) |
| `AGENT_DIRS` | `TOOL_DIRS` |

---
