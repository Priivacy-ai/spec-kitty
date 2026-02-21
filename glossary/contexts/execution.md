## Context: Execution (Tools & Invocation)

Terms describing the CLI tooling that executes LLM interactions.

### Tool

|                      |                                                                                                                                                               |
|----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**       | The CLI application that executes LLM prompts on behalf of the orchestrator. A tool wraps a model provider and exposes it as a command-line interface.        |
| **Context**          | Execution                                                                                                                                                     |
| **Status**           | candidate                                                                                                                                                     |
| **In code**          | Canonical naming migration in progress. Runtime still includes legacy `agent` identifiers in several surfaces.                                                |
| **Related terms**    | [Agent](#agent), [Orchestration Assignment](#orchestration-assignment)                                                                                        |
| **Examples**         | Claude Code, OpenCode, GitHub Codex, Cursor, Google Gemini, Windsurf, Qwen Code, Amazon Q, Roo Cline, Kilocode, Augment Code, GitHub Copilot                  |
| **Decision history** | 2026-02-15: Canonical term renamed from "agent" to "tool" to resolve collision with Doctrine agent profiles. See `glossary/naming-decision-tool-vs-agent.md`. |

**Fields**:

- `tool_id` — Unique identifier (e.g., `"claude"`, `"opencode"`, `"codex"`)
- `command` — CLI executable name
- `uses_stdin` — Whether the tool reads prompts from stdin

---

### Tool Invoker

|                   |                                                                                                                                                      |
|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The Protocol (interface) that defines how a tool is invoked: check installation, build command, parse output.                                        |
| **Context**       | Execution                                                                                                                                            |
| **Status**        | candidate                                                                                                                                            |
| **In code**       | Planned canonical interface; current code still uses legacy invoker naming in parts of the runtime. See: `ToolInvoker` (Protocol, runtime_checkable) |
| **Related terms** | [Tool](#tool)                                                                                                                                        |
| **Legacy name**   | `AgentInvoker`                                                                                                                                       |

---

### Invocation Result

|                   |                                                                                                                                                      |
|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | Structured output of a tool execution — captures success status, stdout/stderr, duration, files modified, commits made, errors, and warnings.        |
| **Context**       | Execution                                                                                                                                            |
| **Status**        | candidate                                                                                                                                            |
| **In code**       | Target runtime contract; implementation details are still being consolidated during mission/runtime convergence. See: `InvocationResult` (dataclass) |
| **Related terms** | [Tool Invoker](#tool-invoker), [Execution Event](#execution-event)                                                                                   |

---
