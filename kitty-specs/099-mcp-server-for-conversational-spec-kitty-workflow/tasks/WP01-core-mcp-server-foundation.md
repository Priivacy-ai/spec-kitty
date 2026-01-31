---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Core MCP Server Foundation"
phase: "Phase 1 - Foundation"
lane: "done"
assignee: "cursor"
agent: "cursor"
shell_pid: "48227"
review_status: "approved"
reviewed_by: "Rodrigo Leven"
dependencies: []
history:
  - timestamp: "2026-01-31T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Core MCP Server Foundation

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

**Goal**: Establish the foundational MCP server infrastructure using FastMCP framework with support for both stdio and SSE transports.

**Success Criteria**:
- FastMCP dependency installed and importable
- MCP server module structure created at `src/specify_cli/mcp/`
- MCPServer class implemented with configurable host, port, authentication, and transport
- Both stdio and SSE transport handlers functional
- CLI command `spec-kitty mcp start` launches server successfully
- Server responds to MCP health check and can list registered tools (even if empty at this stage)

---

## Context & Constraints

**Prerequisites**:
- Review `kitty-specs/099-mcp-server-for-conversational-spec-kitty-workflow/spec.md` (User Stories 1-6, FR-001 to FR-019)
- Review `kitty-specs/099-mcp-server-for-conversational-spec-kitty-workflow/plan.md` (Technical Approach, Phase 1 Design)
- Review `kitty-specs/099-mcp-server-for-conversational-spec-kitty-workflow/data-model.md` (MCPServer entity definition)

**Architectural Constraints**:
- AC-001: MCP server acts as thin wrapper around existing CLI code (no business logic duplication)
- AC-002: MCP implementation architecturally independent from CLI implementation
- FR-015: Support both stdio (Claude Desktop/Cursor) and SSE (web clients) transports
- FR-019: Manual lifecycle management only (user starts/stops server explicitly)

**Key Decisions from Plan**:
- FastMCP framework chosen for protocol handling (reduces complexity)
- Server configuration from environment variables with defaults (host=127.0.0.1, port=8000)
- Single Python process (no daemon mode, no auto-restart)

---

## Subtasks & Detailed Guidance

### Subtask T001 – Install FastMCP dependency

**Purpose**: Add FastMCP library to project dependencies with appropriate version constraints.

**Steps**:
1. Open `src/specify_cli/pyproject.toml`
2. Add FastMCP to dependencies section:
   ```toml
   dependencies = [
       # ... existing dependencies ...
       "fastmcp>=1.0.0,<2.0.0",
   ]
   ```
3. Run `uv sync` or equivalent to install the new dependency
4. Verify import works: `python -c "import fastmcp; print(fastmcp.__version__)"`

**Files**:
- `src/specify_cli/pyproject.toml` (modify dependencies section, ~2 lines added)

**Validation**:
- [ ] FastMCP appears in `pyproject.toml` dependencies
- [ ] `import fastmcp` succeeds in Python REPL
- [ ] Version constraint prevents breaking changes (major version pinned)

**Notes**:
- Use version constraint `>=1.0.0,<2.0.0` to allow patch/minor updates but block breaking changes
- FastMCP documentation: https://fastmcp.dev (reference for API usage)

---

### Subtask T002 – Create MCP module structure

**Purpose**: Establish the directory and file structure for the MCP server subsystem.

**Steps**:
1. Create directory: `src/specify_cli/mcp/`
2. Create `__init__.py` with module docstring:
   ```python
   """
   MCP (Model Context Protocol) server implementation for Spec Kitty.
   
   Provides conversational AI interface to Spec Kitty workflows through
   MCP tools, eliminating the need for users to learn slash commands.
   
   Architecture:
   - server.py: FastMCP server initialization and configuration
   - tools/: Domain-grouped MCP tool definitions
   - adapters/: CLI adapter layer (wraps existing CLI modules)
   - session/: Conversation state and project context management
   - auth/: Optional API key authentication
   """
   
   __all__ = ["MCPServer"]
   ```
3. Create subdirectories:
   - `src/specify_cli/mcp/tools/` (MCP tool handlers)
   - `src/specify_cli/mcp/adapters/` (CLI adapter layer)
   - `src/specify_cli/mcp/session/` (state management)
   - `src/specify_cli/mcp/auth/` (authentication)
4. Create `__init__.py` in each subdirectory with appropriate docstrings

**Files**:
- `src/specify_cli/mcp/__init__.py` (new, ~15 lines)
- `src/specify_cli/mcp/tools/__init__.py` (new, ~5 lines)
- `src/specify_cli/mcp/adapters/__init__.py` (new, ~5 lines)
- `src/specify_cli/mcp/session/__init__.py` (new, ~5 lines)
- `src/specify_cli/mcp/auth/__init__.py` (new, ~5 lines)

**Parallel?**: No (foundational structure)

**Validation**:
- [ ] All directories created and contain `__init__.py`
- [ ] Module imports work: `from specify_cli.mcp import MCPServer` (will fail until T003, expected)
- [ ] Docstrings explain purpose of each submodule

---

### Subtask T003 – Implement MCPServer class

**Purpose**: Create the main server class that handles MCP protocol communication, configuration, and tool registration.

**Steps**:
1. Create `src/specify_cli/mcp/server.py`
2. Implement MCPServer class with attributes from data-model.md:
   ```python
   from dataclasses import dataclass, field
   from typing import Dict, Optional
   from pathlib import Path
   from fastmcp import FastMCP
   
   @dataclass
   class MCPServer:
       """Main MCP server instance for Spec Kitty conversational interface."""
       
       host: str = "127.0.0.1"
       port: int = 8000
       auth_enabled: bool = False
       api_key: Optional[str] = None
       transport: str = "stdio"  # "stdio" or "sse"
       active_projects: Dict[str, "ProjectContext"] = field(default_factory=dict)
       _app: Optional[FastMCP] = None
       
       def __post_init__(self):
           """Initialize FastMCP app and validate configuration."""
           if self.auth_enabled and not self.api_key:
               raise ValueError("auth_enabled=True requires api_key to be set")
           
           if self.transport not in ["stdio", "sse"]:
               raise ValueError(f"Invalid transport: {self.transport}")
           
           self._app = FastMCP("spec-kitty-mcp")
       
       def register_tools(self):
           """Register all MCP tools with FastMCP app."""
           # Tool registration will be added in WP05-WP08
           # For now, register a simple health check tool
           @self._app.tool()
           def health_check():
               """Check MCP server health."""
               return {
                   "status": "healthy",
                   "active_projects": len(self.active_projects),
                   "transport": self.transport
               }
       
       def start(self):
           """Start the MCP server with configured transport."""
           self.register_tools()
           
           if self.transport == "stdio":
               # Stdio transport (for Claude Desktop, Cursor)
               self._app.run(transport="stdio")
           elif self.transport == "sse":
               # SSE transport (for web clients)
               self._app.run(
                   transport="sse",
                   sse_host=self.host,
                   sse_port=self.port
               )
       
       @classmethod
       def from_env(cls) -> "MCPServer":
           """Create MCPServer from environment variables."""
           import os
           
           return cls(
               host=os.getenv("SPEC_KITTY_MCP_HOST", "127.0.0.1"),
               port=int(os.getenv("SPEC_KITTY_MCP_PORT", "8000")),
               auth_enabled=os.getenv("SPEC_KITTY_MCP_AUTH_ENABLED", "false").lower() == "true",
               api_key=os.getenv("SPEC_KITTY_MCP_API_KEY"),
               transport=os.getenv("SPEC_KITTY_MCP_TRANSPORT", "stdio")
           )
   ```

**Files**:
- `src/specify_cli/mcp/server.py` (new, ~80 lines)

**Validation**:
- [ ] MCPServer can be instantiated with defaults
- [ ] `from_env()` reads configuration from environment variables
- [ ] Validation raises errors for invalid config (auth without key, invalid transport)
- [ ] `_app` is a FastMCP instance after initialization

**Notes**:
- ProjectContext import will be circular; use string annotation `"ProjectContext"` for now
- Tool registration is minimal in this WP (just health_check); full tools added in WP05-WP08
- Error handling: raise ValueError for configuration errors (caught by CLI layer)

---

### Subtask T004 – Implement stdio transport handler

**Purpose**: Configure FastMCP to support stdio transport for MCP clients like Claude Desktop and Cursor.

**Steps**:
1. In `server.py`, ensure stdio transport branch in `start()` method (already added in T003)
2. Test stdio transport:
   - Create a test script `tests/mcp/test_stdio_transport.py`:
   ```python
   from specify_cli.mcp.server import MCPServer
   
   def test_stdio_transport_initialization():
       """Test that stdio transport can be configured."""
       server = MCPServer(transport="stdio")
       assert server.transport == "stdio"
       assert server._app is not None
   ```
3. Verify FastMCP supports stdio: Check FastMCP docs for `run(transport="stdio")` API
4. Add comment documenting stdio transport usage:
   ```python
   # Stdio transport:
   # - Used by Claude Desktop, Cursor, and other local MCP clients
   # - Communicates via stdin/stdout (JSON-RPC messages)
   # - No network binding required (host/port ignored)
   # - Ideal for trusted local development environments
   ```

**Files**:
- `src/specify_cli/mcp/server.py` (modify start() method, add comments, ~10 lines)
- `tests/mcp/test_stdio_transport.py` (new, ~15 lines)

**Parallel?**: Yes (independent from T005 SSE transport)

**Validation**:
- [ ] `server.start()` with `transport="stdio"` does not raise errors
- [ ] stdio transport initialization test passes
- [ ] FastMCP stdio API confirmed in documentation

---

### Subtask T005 – Implement SSE transport handler

**Purpose**: Configure FastMCP to support SSE (Server-Sent Events) transport for web-based MCP clients.

**Steps**:
1. In `server.py`, ensure SSE transport branch in `start()` method (already added in T003)
2. Add port availability check before SSE start:
   ```python
   import socket
   
   def _check_port_available(self, host: str, port: int) -> bool:
       """Check if port is available for binding."""
       try:
           with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
               s.bind((host, port))
               return True
       except OSError:
           return False
   
   # In start() method, before SSE transport:
   if self.transport == "sse":
       if not self._check_port_available(self.host, self.port):
           raise RuntimeError(f"Port {self.port} already in use")
   ```
3. Test SSE transport:
   - Create `tests/mcp/test_sse_transport.py`:
   ```python
   from specify_cli.mcp.server import MCPServer
   
   def test_sse_transport_initialization():
       """Test that SSE transport can be configured."""
       server = MCPServer(transport="sse", host="127.0.0.1", port=8001)
       assert server.transport == "sse"
       assert server.host == "127.0.0.1"
       assert server.port == 8001
   ```
4. Add comment documenting SSE transport usage:
   ```python
   # SSE transport:
   # - Used by web-based MCP clients
   # - HTTP server with Server-Sent Events for streaming
   # - Binds to host:port (network accessible)
   # - Requires port availability check
   ```

**Files**:
- `src/specify_cli/mcp/server.py` (add _check_port_available method, ~15 lines)
- `tests/mcp/test_sse_transport.py` (new, ~15 lines)

**Parallel?**: Yes (independent from T004 stdio transport)

**Validation**:
- [ ] Port availability check detects occupied ports
- [ ] SSE transport initialization test passes
- [ ] `start()` raises RuntimeError if port unavailable

**Notes**:
- SSE transport requires network binding; stdio does not
- Default to stdio for local development; SSE for multi-user scenarios

---

### Subtask T006 – Add CLI command for server startup

**Purpose**: Integrate MCP server into spec-kitty CLI with `spec-kitty mcp start` command.

**Steps**:
1. Create `src/specify_cli/cli/commands/mcp.py`:
   ```python
   """MCP server management commands."""
   import typer
   from rich.console import Console
   from specify_cli.mcp.server import MCPServer
   
   app = typer.Typer(help="MCP server management")
   console = Console()
   
   @app.command()
   def start(
       host: str = typer.Option("127.0.0.1", help="Server host (SSE only)"),
       port: int = typer.Option(8000, help="Server port (SSE only)"),
       transport: str = typer.Option("stdio", help="Transport: stdio or sse"),
       auth: bool = typer.Option(False, help="Enable API key authentication"),
       api_key: str = typer.Option(None, help="API key (if auth enabled)")
   ):
       """Start the MCP server."""
       try:
           server = MCPServer(
               host=host,
               port=port,
               transport=transport,
               auth_enabled=auth,
               api_key=api_key
           )
           
           console.print(f"[green]Starting MCP server...[/green]")
           console.print(f"Transport: {transport}")
           if transport == "sse":
               console.print(f"Listening on {host}:{port}")
           
           server.start()
       except Exception as e:
           console.print(f"[red]Error starting server:[/red] {e}")
           raise typer.Exit(1)
   ```
2. Register command group in main CLI (`src/specify_cli/cli/main.py` or equivalent):
   ```python
   from specify_cli.cli.commands import mcp
   
   app.add_typer(mcp.app, name="mcp")
   ```
3. Test command:
   ```bash
   spec-kitty mcp start --help
   spec-kitty mcp start --transport stdio
   ```

**Files**:
- `src/specify_cli/cli/commands/mcp.py` (new, ~40 lines)
- `src/specify_cli/cli/main.py` (modify to register mcp command group, ~2 lines)

**Validation**:
- [ ] `spec-kitty mcp start --help` shows command options
- [ ] `spec-kitty mcp start --transport stdio` launches server without errors
- [ ] Server responds to MCP health_check tool (test with MCP inspector if available)

**Notes**:
- Server runs in foreground (blocks terminal)
- Ctrl+C to stop server
- Add status and stop commands in WP12

---

## Test Strategy

**Unit Tests**:
- `tests/mcp/test_server.py`: MCPServer initialization, configuration validation
- `tests/mcp/test_stdio_transport.py`: Stdio transport initialization
- `tests/mcp/test_sse_transport.py`: SSE transport initialization, port checks

**Integration Tests** (WP10):
- End-to-end server startup with FastMCP test client
- Health check tool invocation via MCP protocol

**Manual Verification**:
1. Start server: `spec-kitty mcp start --transport stdio`
2. Use MCP inspector to verify server is reachable
3. Invoke health_check tool, expect `{"status": "healthy"}`

---

## Risks & Mitigations

**Risk 1: FastMCP API changes**
- **Mitigation**: Pin major version (`>=1.0.0,<2.0.0`), monitor release notes

**Risk 2: Port conflicts (SSE transport)**
- **Mitigation**: Port availability check before binding, clear error messages

**Risk 3: Server hangs on startup**
- **Mitigation**: Add timeout for FastMCP initialization, log startup phases

**Risk 4: Configuration errors (auth without key)**
- **Mitigation**: Validation in `__post_init__`, raise ValueError with actionable message

---

## Review Guidance

**Key Checkpoints**:
- [ ] FastMCP dependency installed and version pinned
- [ ] MCP module structure follows plan.md (server.py, tools/, adapters/, session/, auth/)
- [ ] MCPServer class matches data-model.md specification
- [ ] Both stdio and SSE transports functional (tested separately)
- [ ] CLI command `spec-kitty mcp start` works for both transports
- [ ] Health check tool responds correctly
- [ ] Error handling: invalid config → clear error messages
- [ ] Code quality: type hints, docstrings, PEP 8 compliance

**Acceptance Criteria**:
- Server can be started with `spec-kitty mcp start`
- Health check tool returns status via MCP protocol
- No hardcoded values (config from env vars/CLI options)

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**How to Add Entries**:
1. Scroll to bottom of this section
2. Append new entry at END (do NOT prepend)
3. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – lane=<lane> – <action>`
4. Ensure timestamp is current (UTC)
5. Lane must match frontmatter `lane:` field

**Initial entry**:
- 2026-01-31T00:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks

---

### Updating Lane Status

To change lane:
1. **Edit directly**: Update `lane:` in frontmatter AND append activity log entry
2. **Use CLI** (recommended): `spec-kitty agent tasks move-task WP01 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`

**Implementation Command**:
```bash
spec-kitty implement WP01
```
(No --base flag needed, this is the first WP with no dependencies)
- 2026-01-31T11:38:04Z – cursor – shell_pid=5310 – lane=doing – Started implementation via workflow command
- 2026-01-31T11:45:20Z – cursor – shell_pid=5310 – lane=for_review – Ready for review: Core MCP server foundation complete with FastMCP integration, stdio/SSE transport support, CLI command, and comprehensive tests
- 2026-01-31T12:19:57Z – cursor – shell_pid=48227 – lane=doing – Started review via workflow command
- 2026-01-31T12:21:41Z – cursor – shell_pid=48227 – lane=done – Review passed: Excellent implementation of MCP server foundation. All subtasks complete with proper FastMCP integration, comprehensive tests, CLI command, and architecture compliance. Ready for dependent WPs (WP02, WP08, WP09, WP11, WP12) to proceed.
