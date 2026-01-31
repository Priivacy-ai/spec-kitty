# Implementation Plan: MCP Server for Conversational Spec Kitty Workflow

**Branch**: `025-mcp-server-for-conversational-spec-kitty-workflow` | **Date**: 2026-01-29 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `kitty-specs/025-mcp-server-for-conversational-spec-kitty-workflow/spec.md`

## Summary

Build an MCP (Model Context Protocol) server that exposes all Spec Kitty CLI functionality through conversational AI interaction. The server acts as a thin wrapper around existing CLI code, translating natural language requests into structured CLI function calls. This eliminates the need for users to learn slash commands while maintaining 100% functional parity with the CLI.

**Core Value**: Enable developers to use Spec Kitty through natural conversation with AI agents (Claude, Cursor, etc.) without learning command syntax.

**Technical Approach**:
- FastMCP framework for MCP protocol handling (stdio/SSE transports)
- Direct Python imports to reuse existing `src/specify_cli/` modules
- Domain-grouped MCP tools (feature_operations, task_operations, workspace_operations, system_operations)
- JSON-based conversation state persistence in `.kittify/mcp-sessions/`
- Cross-platform pessimistic file locking with `filelock` library
- Optional API key authentication with config to disable

## Technical Context

**Language/Version**: Python 3.11+ (matching existing spec-kitty requirement)  
**Primary Dependencies**: 
- `fastmcp` (MCP server framework with stdio/SSE support)
- `filelock` (cross-platform pessimistic locking)
- Existing: `typer`, `rich`, `pyyaml`, `ruamel.yaml`, `pathlib`

**Storage**: 
- Filesystem only (no database)
- Conversation state: JSON files in `.kittify/mcp-sessions/` per project
- Lock files: `.kittify/.lock-<resource>` per locked resource

**Testing**: 
- `pytest` (existing test framework)
- MCP client integration tests (using FastMCP test utilities)
- Contract tests for CLI adapter layer

**Target Platform**: 
- Cross-platform (Windows, macOS, Linux)
- Python environment where spec-kitty CLI runs
- Local development machines (manual server start/stop)

**Project Type**: Single Python project (extends existing `src/specify_cli/` structure)

**Performance Goals**: 
- Server startup: <2 seconds (SC-007)
- Read operation latency: <500ms (SC-007)
- Write operation latency: <2 seconds (includes git commits)
- Concurrent requests: 100 without degradation (SC-010)

**Constraints**: 
- MUST wrap existing CLI code (AC-001, FR-017)
- MUST maintain architectural independence from CLI (AC-002)
- NO subprocess overhead (direct Python imports)
- Lock timeout: 5 minutes with auto-cleanup
- Session persistence: indefinite (not limited to 24 hours)

**Scale/Scope**: 
- ~20+ MCP tools across 4 domains
- Supports multiple concurrent projects
- Handles multi-turn discovery interviews (3-5 questions per feature average)
- 95% command interpretation accuracy (SC-006)

## Constitution Check

*No constitution file exists at `.kittify/memory/constitution.md`. Skipping constitution check.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/025-mcp-server-for-conversational-spec-kitty-workflow/
├── plan.md              # This file
├── research.md          # Phase 0: FastMCP patterns, CLI integration strategies
├── data-model.md        # Phase 1: Session state, project context, lock entities
├── quickstart.md        # Phase 1: MCP server setup, client configuration
├── contracts/           # Phase 1: MCP tool schemas (JSON Schema)
└── tasks.md             # Phase 2: NOT created by this command
```

### Source Code (repository root)

```
src/specify_cli/
├── mcp/                        # NEW: MCP server implementation
│   ├── __init__.py
│   ├── server.py               # FastMCP server initialization
│   ├── tools/                  # Domain-grouped MCP tool definitions
│   │   ├── __init__.py
│   │   ├── feature_tools.py    # Feature operations
│   │   ├── task_tools.py       # Task management
│   │   ├── workspace_tools.py  # Workspace operations
│   │   └── system_tools.py     # System operations
│   ├── adapters/               # CLI adapter layer
│   │   ├── __init__.py
│   │   └── cli_adapter.py      # Wraps existing CLI modules
│   ├── session/                # Conversation state management
│   │   ├── __init__.py
│   │   ├── state.py            # Session persistence (JSON)
│   │   ├── context.py          # Project context tracking
│   │   └── locking.py          # File locking with filelock
│   └── auth/                   # Optional API key authentication
│       ├── __init__.py
│       └── api_key.py          # API key validation
├── cli/                        # EXISTING: CLI commands (unchanged)
├── agent_utils/                # EXISTING: Agent utilities (unchanged)
├── core/                       # EXISTING: Core functionality (reused)
└── ...

tests/
├── mcp/                        # NEW: MCP server tests
│   ├── test_server.py
│   ├── test_feature_tools.py
│   ├── test_task_tools.py
│   ├── test_workspace_tools.py
│   ├── test_cli_adapter.py
│   ├── test_session_state.py
│   └── test_locking.py
└── ...
```

**Structure Decision**: Single project structure. The MCP server is a new subsystem within `src/specify_cli/`. It reuses existing CLI modules through direct imports, maintaining the thin wrapper architecture (AC-001).

## Complexity Tracking

*No constitution violations to justify.*

## Phase 0: Research

See [research.md](research.md) for detailed findings on:

1. **FastMCP Framework Patterns** - Tool definition, parameter schemas, transport configuration
2. **CLI Integration Strategy** - Mapping CLI commands to MCP tools, extracting reusable logic
3. **Conversation State Management** - JSON schema, session lifecycle, resumption
4. **File Locking Best Practices** - filelock usage, granularity, stale lock cleanup
5. **MCP Tool Organization** - Domain grouping, natural language routing

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md) for complete entity definitions:

- **MCPServer**: Main server instance (host, port, auth config, active projects)
- **ProjectContext**: Single project representation (path, active feature, session dir)
- **ConversationState**: Multi-turn interview tracking (session ID, workflow, phase, questions)
- **ResourceLock**: Pessimistic lock (resource ID, lock file, timeout, owner PID)
- **MCPTool**: Domain-grouped tool (name, description, parameters, handler)
- **OperationResult**: Standardized result format (success, message, data, artifacts, errors)

### API Contracts

See `contracts/` directory for complete JSON Schema definitions:

- `feature_operations.json` - Feature workflow tools (specify, plan, tasks, implement, review, accept)
- `task_operations.json` - Task management tools (list, move, add_history, query_status)
- `workspace_operations.json` - Workspace tools (create_worktree, list, merge)
- `system_operations.json` - System tools (health_check, validate_project, list_missions)

### CLI Adapter Interface

The `CLIAdapter` class (in `src/specify_cli/mcp/adapters/cli_adapter.py`) provides a consistent interface for MCP tools to invoke existing CLI functionality:

```python
class CLIAdapter:
    """Wraps existing CLI modules for MCP tool invocation."""
    
    def __init__(self, project_context: ProjectContext):
        self.project_context = project_context
    
    # Feature operations
    def create_feature(self, slug: str, description: str) -> OperationResult
    def setup_plan(self, feature_slug: str) -> OperationResult
    def create_tasks(self, feature_slug: str) -> OperationResult
    
    # Task operations
    def list_tasks(self, feature_slug: str, lane: Optional[str]) -> OperationResult
    def move_task(self, feature_slug: str, task_id: str, lane: str) -> OperationResult
    
    # Workspace operations
    def create_worktree(self, wp_id: str, base_wp: Optional[str]) -> OperationResult
    def list_worktrees(self) -> OperationResult
    
    # System operations
    def validate_project(self) -> OperationResult
    def get_missions(self) -> OperationResult
```

**Design Principles**:
- Each method maps to existing CLI functions (no duplication)
- Standardized `OperationResult` return format
- Error handling: CLI exceptions → structured errors

### Quickstart Guide

See [quickstart.md](quickstart.md) for:
- Installation instructions
- Server startup (`spec-kitty mcp start`)
- MCP client configuration (Claude Desktop, Cursor examples)
- First tool invocation walkthrough
- Multi-project setup
- Authentication configuration
- Troubleshooting common issues

## Phase 2: Task Breakdown

**STOP**: This command (`/spec-kitty.plan`) ends here. Phase 2 (task breakdown) is triggered by running `/spec-kitty.tasks`.

Planning artifacts are complete and committed to main branch. No worktrees created.

**Next Steps**:
1. Review planning artifacts (research.md, data-model.md, contracts/, quickstart.md)
2. Run `/spec-kitty.tasks` to generate work package breakdown
3. Tasks will be created in `tasks/` directory

---

## Appendix: Technology Choices Rationale

**Why FastMCP over custom MCP implementation?**
- Reduces protocol complexity (stdio/SSE handled automatically)
- Faster development (focus on business logic)
- Community support and documentation
- Testing utilities included

**Why direct Python imports over subprocess calls?**
- Lower latency (no process spawn)
- Better error handling (Python exceptions vs stderr parsing)
- Shared memory space
- Simpler debugging (single process)
- Maintains architectural independence (imports modules, not CLI entry points)

**Why JSON for conversation state?**
- Human-readable (easy debugging)
- Version-portable (no Python lock-in)
- Simpler than SQLite for single-session access
- Easy backup/migration
- Standard library support

**Why filelock library?**
- Cross-platform (Windows + Unix)
- Auto-cleanup on process exit
- Battle-tested in production
- Simple API (context manager)
- Timeout support

**Why domain-grouped tools?**
- Better UX (fewer tools, clear organization)
- Natural language routing within domain
- Easier to extend (add operations vs new tools)
- Reduces boilerplate
- Matches existing CLI structure
