# Data Model: MCP Server for Conversational Spec Kitty Workflow

**Feature**: 099-mcp-server-for-conversational-spec-kitty-workflow  
**Date**: 2026-01-29  
**Purpose**: Define core entities, relationships, and state management for the MCP server

## Entity Definitions

### MCPServer

**Purpose**: Main server instance that handles MCP protocol communication, manages multiple project contexts, and routes tool invocations.

**Attributes**:
- `host: str` - Server bind address (default: "127.0.0.1")
- `port: int` - Server port (default: 8000, configurable)
- `auth_enabled: bool` - Whether API key authentication is required
- `api_key: Optional[str]` - Server API key (if auth_enabled=True)
- `active_projects: Dict[str, ProjectContext]` - Map of project_path → ProjectContext for all active projects
- `transport: str` - MCP transport mode ("stdio" or "sse")

**Lifecycle**:
1. **Start**: User runs `spec-kitty mcp start` command
2. **Initialize**: Load configuration, bind to host:port, register MCP tools
3. **Serve**: Accept MCP client connections, route tool invocations
4. **Stop**: SIGTERM/SIGINT signal or user Ctrl+C

**Validation**:
- Port must be available (not in use)
- If auth_enabled, api_key must be provided
- FastMCP server initialization must succeed

---

### ProjectContext

**Purpose**: Represents a single Spec Kitty project managed by the server. Tracks active feature, mission, and provides access to project state.

**Attributes**:
- `project_path: Path` - Absolute path to project root directory
- `kittify_dir: Path` - Path to `.kittify/` directory (must exist)
- `active_feature: Optional[str]` - Current feature slug (e.g., "025-mcp-server"), None if no active feature
- `mission: Optional[str]` - Active mission (e.g., "software-dev", "research", "documentation")
- `session_dir: Path` - Path to `.kittify/mcp-sessions/` directory (created on first use)
- `lock_dir: Path` - Path to `.kittify/` directory (lock files stored here)
- `config: Dict[str, Any]` - Cached project configuration from `.kittify/config.yaml`

**Lifecycle**:
1. **Create**: When MCP client first references a project_path in a tool invocation
2. **Validate**: Check `.kittify/` directory exists, load config.yaml
3. **Cache**: Store in MCPServer.active_projects for duration of server uptime
4. **Refresh**: Re-validate on each tool invocation (detect manual config changes)

**Validation Rules**:
- `project_path` must be absolute
- `.kittify/` directory must exist
- `.kittify/config.yaml` must be valid YAML
- If `session_dir` doesn't exist, create it automatically

**Methods**:
- `get_feature_dir(feature_slug: str) -> Path` - Returns `kitty-specs/{feature_slug}/`
- `get_active_feature() -> Optional[str]` - Detects active feature from git branch or .kittify metadata
- `list_features() -> List[str]` - Returns all feature slugs from `kitty-specs/`

---

### ConversationState

**Purpose**: Tracks multi-turn discovery interviews (e.g., specify, plan workflows) allowing resumption after client disconnection.

**Attributes**:
- `session_id: str` - Unique identifier (UUID v4)
- `project_path: Path` - Which project this conversation belongs to
- `workflow: str` - Workflow type ("specify", "plan", "tasks", "implement", "review", "accept")
- `phase: str` - Current workflow phase ("discovery", "clarification", "generation", "complete")
- `questions_answered: Dict[str, Any]` - Map of question_id → answer (structured data)
- `questions_pending: List[str]` - List of question IDs not yet answered (ordered)
- `accumulated_context: Dict[str, Any]` - Free-form context gathered during conversation (e.g., feature title, actors, constraints)
- `created_at: str` - ISO 8601 timestamp when session was created
- `updated_at: str` - ISO 8601 timestamp of last update

**Persistence**:
- **Format**: JSON file
- **Location**: `.kittify/mcp-sessions/{session_id}.json`
- **Retention**: Indefinite (no automatic cleanup)
- **Write Strategy**: Atomic (write to `.tmp`, then rename to prevent corruption)

**State Transitions**:
```
[Create Session] → phase="discovery"
   ↓ (questions asked/answered)
phase="discovery" → phase="clarification" (if [NEEDS CLARIFICATION] markers found)
   ↓ (clarifications resolved)
phase="clarification" → phase="generation" (ready to create artifacts)
   ↓ (artifacts generated: spec.md, plan.md, etc.)
phase="generation" → phase="complete"
```

**Methods**:
- `to_json() -> str` - Serialize to JSON string
- `from_json(data: str) -> ConversationState` - Deserialize from JSON
- `answer_question(question_id: str, answer: Any)` - Record answer, update pending list
- `is_complete() -> bool` - True if phase=="complete"

**Resumption**:
- MCP client includes session_id in tool parameters
- Server loads JSON from `.kittify/mcp-sessions/{session_id}.json`
- Resume workflow from current phase with existing context

---

### ResourceLock

**Purpose**: Represents a pessimistic lock on a project resource (work package, feature, config file) to prevent concurrent modifications.

**Attributes**:
- `resource_id: str` - Identifier of locked resource (e.g., "WP01", "025-mcp-server", "config.yaml")
- `lock_file: Path` - Path to lock file (e.g., `.kittify/.lock-WP01`)
- `acquired_at: str` - ISO 8601 timestamp when lock was acquired
- `timeout_seconds: int` - Lock timeout in seconds (default: 300 = 5 minutes)
- `owner_pid: int` - Process ID of the process holding the lock

**Behavior**:
- **Acquisition**: Use `filelock.FileLock(lock_file, timeout=timeout_seconds).acquire()`
- **Auto-cleanup**: Lock automatically released when process exits (filelock feature)
- **Timeout**: If lock held longer than timeout_seconds, acquisition raises `Timeout` exception
- **Blocking**: Acquisition blocks until lock available or timeout expires

**Lock Granularity**:
- **Per work package**: `.lock-WP01`, `.lock-WP02` (for task operations like move_task)
- **Per feature**: `.lock-025-mcp-server` (for feature-level operations like accept)
- **Per config file**: `.lock-config.yaml` (for agent config updates)

**Error Handling**:
- If lock held beyond timeout, return `OperationResult` with:
  ```python
  OperationResult(
      success=False,
      message=f"Resource {resource_id} is currently locked by another client.",
      errors=["Lock timeout: retry in a moment"]
  )
  ```

**Usage Pattern**:
```python
from filelock import FileLock, Timeout

lock_file = project_context.lock_dir / f".lock-{resource_id}"
lock = FileLock(lock_file, timeout=300)

try:
    with lock.acquire(timeout=300):
        # Perform operation on resource
        result = cli_adapter.move_task(task_id, lane)
except Timeout:
    result = OperationResult(
        success=False,
        message=f"Resource {resource_id} is locked",
        errors=["Lock timeout"]
    )
```

---

### MCPTool

**Purpose**: Represents a domain-grouped MCP tool exposed by the server. Handles parameter validation, routing to CLI adapter, and response serialization.

**Attributes**:
- `name: str` - Tool name (e.g., "feature_operations")
- `description: str` - Human-readable description of tool purpose
- `parameters: Dict[str, Any]` - JSON Schema defining input parameters
- `handler: Callable` - Function that executes the tool operation (routes to CLI adapter)

**Tool Domains**:

#### 1. feature_operations
**Operations**: specify, plan, tasks, implement, review, accept  
**Parameters**:
- `project_path: str` (required)
- `operation: str` (required, enum)
- `feature_slug: Optional[str]` (required for most operations except specify)
- `arguments: Optional[Dict[str, Any]]` (operation-specific args)

#### 2. task_operations
**Operations**: list_tasks, move_task, add_history, query_status  
**Parameters**:
- `project_path: str` (required)
- `operation: str` (required, enum)
- `feature_slug: str` (required)
- `task_id: Optional[str]` (required for move_task, add_history)
- `lane: Optional[str]` (required for move_task)
- `note: Optional[str]` (required for add_history)

#### 3. workspace_operations
**Operations**: create_worktree, list_worktrees, merge  
**Parameters**:
- `project_path: str` (required)
- `operation: str` (required, enum)
- `work_package_id: Optional[str]` (required for create_worktree)
- `base_wp: Optional[str]` (optional, for dependency-based branching)
- `feature_slug: Optional[str]` (required for merge)

#### 4. system_operations
**Operations**: health_check, validate_project, list_missions, server_config  
**Parameters**:
- `operation: str` (required, enum)
- `project_path: Optional[str]` (required for validate_project)

**Handler Signature**:
```python
def feature_operations_handler(
    project_path: str,
    operation: str,
    feature_slug: Optional[str] = None,
    arguments: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    # Validate project_path
    # Create ProjectContext
    # Route to CLI adapter based on operation
    # Return OperationResult.to_dict()
```

---

### OperationResult

**Purpose**: Standardized result format for all MCP tool operations. Provides consistent structure for success/failure, messages, data, and artifacts.

**Attributes**:
- `success: bool` - Whether operation succeeded
- `message: str` - Human-readable outcome description
- `data: Optional[Dict[str, Any]]` - Structured result data (e.g., feature slug, task list, worktree paths)
- `artifacts: List[Path]` - Files created or modified by the operation
- `errors: List[str]` - Error messages if operation failed
- `warnings: List[str]` - Non-fatal issues (e.g., "stale lock detected but released")

**Examples**:

#### Success (create_feature):
```python
OperationResult(
    success=True,
    message="Feature 099-mcp-server created successfully",
    data={
        "feature": "099-mcp-server-for-conversational-spec-kitty-workflow",
        "feature_dir": "/path/to/kitty-specs/025-mcp-server/",
        "spec_file": "/path/to/kitty-specs/025-mcp-server/spec.md"
    },
    artifacts=[Path("kitty-specs/025-mcp-server/spec.md")],
    errors=[],
    warnings=[]
)
```

#### Failure (lock timeout):
```python
OperationResult(
    success=False,
    message="Failed to move task WP01: resource locked",
    data=None,
    artifacts=[],
    errors=["Lock timeout: WP01 is currently being modified by another client"],
    warnings=[]
)
```

#### Success with warnings (stale lock cleaned up):
```python
OperationResult(
    success=True,
    message="Task WP01 moved to for_review lane",
    data={"task_id": "WP01", "lane": "for_review"},
    artifacts=[Path("kitty-specs/025-mcp-server/tasks/WP01.md")],
    errors=[],
    warnings=["Stale lock from PID 12345 was cleaned up"]
)
```

**Serialization**:
```python
def to_dict(self) -> Dict[str, Any]:
    return {
        "success": self.success,
        "message": self.message,
        "data": self.data,
        "artifacts": [str(p) for p in self.artifacts],
        "errors": self.errors,
        "warnings": self.warnings
    }
```

---

## Relationships

```
MCPServer
  └─> active_projects: Dict[str, ProjectContext]
       └─> ProjectContext
            ├─> session_dir: Path (.kittify/mcp-sessions/)
            │    └─> ConversationState files (*.json)
            └─> lock_dir: Path (.kittify/)
                 └─> ResourceLock files (.lock-*)

MCPTool
  └─> handler: Callable
       └─> CLIAdapter (wraps existing CLI modules)
            └─> OperationResult
```

**Key Flows**:
1. MCP client → MCPTool → handler → ProjectContext → CLIAdapter → CLI modules → OperationResult → MCP client
2. Workflow starts → ConversationState created → JSON persisted → resume later → ConversationState loaded
3. Tool invocation → ResourceLock acquired → operation executes → lock released

---

## Storage Locations

| Entity | Storage | Location | Format |
|--------|---------|----------|--------|
| MCPServer | In-memory | N/A | Python object |
| ProjectContext | In-memory (cached) | N/A | Python object |
| ConversationState | Filesystem | `.kittify/mcp-sessions/{session_id}.json` | JSON |
| ResourceLock | Filesystem | `.kittify/.lock-{resource_id}` | Binary (filelock) |
| OperationResult | In-memory (returned) | N/A | Python object → JSON |

---

## State Management

**Server Startup**:
1. Load configuration (host, port, auth settings)
2. Initialize FastMCP server with tool registrations
3. Bind to host:port
4. Start accepting MCP connections

**Tool Invocation**:
1. MCP client calls tool (e.g., `feature_operations`)
2. Server validates parameters against JSON Schema
3. Handler creates/retrieves ProjectContext
4. Acquires ResourceLock if modifying state
5. Delegates to CLIAdapter
6. CLIAdapter calls existing CLI module
7. Returns OperationResult
8. Releases lock (if acquired)
9. Serializes result to MCP response

**Conversation Resumption**:
1. MCP client includes `session_id` in tool parameters
2. Server loads ConversationState from `.kittify/mcp-sessions/{session_id}.json`
3. Resume workflow from current phase
4. Update ConversationState after each question/answer
5. Save updated JSON atomically

**Lock Management**:
1. Before modifying resource, acquire ResourceLock
2. filelock handles blocking and timeout
3. Operation executes while lock held
4. Lock automatically released on context manager exit
5. Process crash → filelock auto-cleanup
