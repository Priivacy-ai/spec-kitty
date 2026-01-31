# Research: MCP Server for Conversational Spec Kitty Workflow

**Feature**: 025-mcp-server-for-conversational-spec-kitty-workflow  
**Date**: 2026-01-29  
**Purpose**: Document research findings to resolve technical unknowns before Phase 1 design

## Research Areas

### 1. FastMCP Framework Patterns

**Decision**: Use FastMCP with decorator-based tool definitions and domain grouping

**Rationale**:
- FastMCP provides `@mcp.tool()` decorators for clean tool definitions
- Supports both stdio and SSE transports out of the box (FR-015 requirement)
- Automatic parameter validation via Pydantic models
- Built-in error handling and response serialization
- Test utilities for MCP client simulation

**Implementation Notes**:
```python
from fastmcp import FastMCP

mcp = FastMCP("spec-kitty-server")

@mcp.tool()
def feature_operations(
    project_path: str,
    operation: str,
    feature_slug: Optional[str] = None,
    arguments: Optional[dict] = None
) -> dict:
    """Execute Spec Kitty feature workflow operations."""
    # Route to CLI adapter based on operation
    adapter = CLIAdapter(ProjectContext(project_path))
    if operation == "specify":
        return adapter.create_feature(**arguments).to_dict()
    elif operation == "plan":
        return adapter.setup_plan(feature_slug).to_dict()
    # ... more operations
```

**Alternatives Considered**:
- **Custom MCP implementation**: Rejected due to protocol complexity (wire format, transport negotiation)
- **mcp-python SDK**: Lower-level than FastMCP, more boilerplate for same functionality

---

### 2. CLI Integration Strategy

**Decision**: Direct Python imports with CLI adapter abstraction layer

**Rationale**:
- Existing CLI modules are already structured as importable functions
- `src/specify_cli/agent_utils/` contains core logic separate from typer CLI layer
- Direct imports eliminate subprocess overhead (~50-100ms per invocation)
- Adapter pattern maintains architectural independence (AC-002)
- Easy to test (mock adapter, not subprocess)

**Implementation Notes**:
```python
# CLI Adapter wraps existing modules
from specify_cli.agent_utils.feature import create_feature as cli_create_feature
from specify_cli.agent_utils.tasks import move_task as cli_move_task

class CLIAdapter:
    def create_feature(self, slug: str, description: str) -> OperationResult:
        try:
            result = cli_create_feature(
                slug=slug,
                description=description,
                repo_root=self.project_context.project_path
            )
            return OperationResult(
                success=True,
                message=f"Feature {result['feature']} created",
                data=result,
                artifacts=[result['feature_dir'] / 'spec.md']
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=str(e),
                errors=[str(e)]
            )
```

**Key Discovery**:
- Most CLI commands already separate business logic from typer context handling
- Functions like `create_feature()`, `setup_plan()`, `move_task()` are directly callable
- Some commands mix CLI-specific logic (console output, typer prompts) - these need extraction

**Alternatives Considered**:
- **Subprocess calls**: Rejected due to latency, error handling complexity, serialization overhead
- **Shared library extraction**: Rejected as unnecessary - existing structure already supports imports

---

### 3. Conversation State Management

**Decision**: JSON files in `.kittify/mcp-sessions/`, one file per session

**Rationale**:
- Human-readable for debugging (can inspect/edit session files manually)
- Simple persistence model (no schema migrations like SQLite)
- Adequate for single-session access patterns (no complex queries needed)
- Python `json` module in stdlib (no dependencies)
- Version-portable (works across Python versions)

**JSON Schema**:
```json
{
  "session_id": "uuid-v4-here",
  "project_path": "/absolute/path/to/project",
  "workflow": "specify",
  "phase": "discovery",
  "questions_answered": {
    "Q1_mission": "software-dev",
    "Q2_complexity": "complex"
  },
  "questions_pending": ["Q3_nfr", "Q4_integrations"],
  "accumulated_context": {
    "feature_title": "User Authentication System",
    "actors": ["end user", "admin"],
    "constraints": ["GDPR compliance", "SSO integration"]
  },
  "created_at": "2026-01-29T10:00:00Z",
  "updated_at": "2026-01-29T10:05:30Z"
}
```

**Lifecycle**:
1. **Create**: On first MCP tool call starting a workflow (e.g., "specify" operation)
2. **Update**: After each question answered, write updated JSON
3. **Resume**: Load JSON by session_id when client reconnects
4. **Retention**: Indefinite (no automatic cleanup, user can manually delete)

**Implementation Notes**:
- Use `fcntl` flock during JSON read/write to prevent corruption from concurrent access
- Atomic writes: write to `.tmp` file, then rename (prevents partial reads)
- Session ID in MCP response metadata (client can save for resumption)

**Alternatives Considered**:
- **Python pickle**: Rejected due to version incompatibility, security risks, binary format
- **SQLite**: Rejected as overkill for simple key-value access, adds dependency complexity
- **In-memory only**: Rejected due to FR-011 requirement (persist indefinitely)

---

### 4. File Locking Best Practices

**Decision**: Use `filelock` library with 5-minute timeout, per-resource granularity

**Rationale**:
- Cross-platform (works on Windows and Unix without platform-specific code)
- Auto-cleanup on process exit (prevents stale locks from crashed clients)
- Simple context manager API: `with FileLock("path"):`
- Timeout support (configurable acquisition timeout)
- Battle-tested (used by pip, tox, many production tools)

**Implementation Notes**:
```python
from filelock import FileLock, Timeout

class ResourceLocker:
    def __init__(self, kittify_dir: Path, timeout: int = 300):
        self.lock_dir = kittify_dir
        self.timeout = timeout
    
    def acquire_lock(self, resource_id: str) -> FileLock:
        lock_file = self.lock_dir / f".lock-{resource_id}"
        lock = FileLock(lock_file, timeout=self.timeout)
        try:
            lock.acquire()
            return lock
        except Timeout:
            raise LockConflictError(
                f"Resource {resource_id} is currently locked by another client. "
                f"Retry in a moment."
            )
    
    def release_lock(self, lock: FileLock):
        lock.release()
```

**Lock Granularity**:
- Per work package: `.lock-WP01`, `.lock-WP02`, etc.
- Per feature (for feature-level operations): `.lock-025-mcp-server`
- Per config file (for config updates): `.lock-config.yaml`

**Stale Lock Handling**:
- `filelock` auto-releases on process exit (no manual cleanup needed)
- For manual timeout, check lock age in metadata (if needed)

**Alternatives Considered**:
- **fcntl (Unix-only)**: Rejected due to lack of Windows support
- **Simple PID files**: Rejected due to manual cleanup complexity, race conditions
- **Optimistic locking**: Rejected per clarification session (user chose pessimistic)

---

### 5. MCP Tool Organization

**Decision**: Domain-grouped tools with operation parameter for routing

**Rationale**:
- Reduces tool count from 20+ to 4 (better MCP client UX)
- Natural language routing within domain (e.g., "list tasks" → task_operations, operation="list_tasks")
- Easier to extend (add operation enum value vs create new tool)
- Matches existing CLI structure (`spec-kitty agent feature`, `spec-kitty agent tasks`)
- Parameter-driven routing enables flexible composition

**Tool Domains**:

1. **feature_operations**
   - Operations: specify, plan, tasks, implement, review, accept
   - Parameters: project_path, operation, feature_slug, arguments (dict)

2. **task_operations**
   - Operations: list_tasks, move_task, add_history, query_status
   - Parameters: project_path, operation, feature_slug, task_id, lane, note

3. **workspace_operations**
   - Operations: create_worktree, list_worktrees, merge
   - Parameters: project_path, operation, work_package_id, base_wp, feature_slug

4. **system_operations**
   - Operations: health_check, validate_project, list_missions, server_config
   - Parameters: operation, project_path (optional)

**Routing Pattern**:
```python
@mcp.tool()
def feature_operations(project_path: str, operation: str, **kwargs) -> dict:
    adapter = CLIAdapter(ProjectContext(project_path))
    
    # Route based on operation
    if operation == "specify":
        return adapter.create_feature(**kwargs).to_dict()
    elif operation == "plan":
        return adapter.setup_plan(**kwargs).to_dict()
    # ... more operations
    else:
        raise ValueError(f"Unknown operation: {operation}")
```

**Alternatives Considered**:
- **One tool per command**: Rejected due to tool explosion (20+ tools), discovery burden
- **Single conversational tool**: Rejected due to complex natural language parsing, ambiguity handling
- **Hierarchical tools** (feature.specify, feature.plan): Rejected as FastMCP doesn't support namespacing

---

## Summary

All research questions resolved. Key decisions:

1. **FastMCP** for MCP protocol handling
2. **Direct Python imports** with CLI adapter layer
3. **JSON files** for conversation state persistence
4. **filelock library** for pessimistic locking
5. **Domain-grouped tools** (4 tools, operation-based routing)

No blocking unknowns remain. Ready for Phase 1 design.
