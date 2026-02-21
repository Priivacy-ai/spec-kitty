# Data Model: Autonomous Multi-Agent Orchestrator

**Purpose**: Define the entities and schemas for orchestration state and configuration.

## Entity: OrchestrationRun

Represents a single execution of the orchestrator for a feature.

```python
@dataclass
class OrchestrationRun:
    """Tracks a complete orchestration execution."""

    run_id: str                    # UUID for this run
    feature_slug: str              # e.g., "020-autonomous-multi-agent-orchestrator"
    started_at: datetime
    completed_at: datetime | None
    status: OrchestrationStatus    # pending, running, paused, completed, failed

    # Configuration snapshot
    config_hash: str               # Hash of agents.yaml at start
    concurrency_limit: int         # Max parallel agents

    # Progress tracking
    wps_total: int
    wps_completed: int
    wps_failed: int

    # Metrics
    parallel_peak: int             # Max concurrent agents observed
    total_agent_invocations: int   # Including retries
```

**Persistence**: `.kittify/orchestration-state.json`

## Entity: WPExecution

Tracks a single work package's execution state.

```python
@dataclass
class WPExecution:
    """Tracks execution of a single work package."""

    wp_id: str                     # e.g., "WP01"
    status: WPStatus               # pending, implementation, review, completed, failed

    # Implementation phase
    implementation_agent: str | None
    implementation_started: datetime | None
    implementation_completed: datetime | None
    implementation_exit_code: int | None
    implementation_retries: int

    # Review phase
    review_agent: str | None
    review_started: datetime | None
    review_completed: datetime | None
    review_exit_code: int | None
    review_retries: int

    # Output tracking
    log_file: Path | None          # Path to captured stdout/stderr
    worktree_path: Path | None     # Path to WP worktree

    # Error tracking
    last_error: str | None
    fallback_agents_tried: list[str]
```

## Entity: AgentConfig

User configuration for a single agent.

```python
@dataclass
class AgentConfig:
    """Per-agent configuration from agents.yaml."""

    agent_id: str                  # e.g., "claude-code"
    enabled: bool                  # Is this agent available?
    roles: list[str]               # ["implementation", "review"]
    priority: int                  # Higher = preferred
    max_concurrent: int            # Agent-specific concurrency limit
    timeout_seconds: int           # Per-invocation timeout
```

## Entity: AgentInvoker

Runtime representation of an agent's invocation capabilities.

```python
class AgentInvoker(Protocol):
    """Protocol for agent-specific invocation logic."""

    agent_id: str
    command: str                   # Base command (e.g., "claude", "codex")

    def is_installed(self) -> bool:
        """Check if agent CLI is available."""
        ...

    def build_command(
        self,
        prompt: str,
        working_dir: Path,
        role: str,  # "implementation" or "review"
    ) -> list[str]:
        """Build full command with agent-specific flags."""
        ...

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> InvocationResult:
        """Parse agent output into structured result."""
        ...
```

## Entity: OrchestratorConfig

Complete orchestration configuration.

```python
@dataclass
class OrchestratorConfig:
    """Full configuration from .kittify/agents.yaml."""

    version: str                   # Schema version

    # Default agent order by role
    defaults: dict[str, list[str]]  # {"implementation": [...], "review": [...]}

    # Per-agent configuration
    agents: dict[str, AgentConfig]

    # Fallback behavior
    fallback_strategy: FallbackStrategy  # next_in_list, same_agent, fail
    max_retries: int

    # Single-agent mode
    single_agent_mode: bool
    single_agent: str | None

    # Global limits
    global_concurrency: int        # Max total parallel agents
    global_timeout: int            # Default timeout per invocation
```

## Entity: InvocationResult

Result from a single agent invocation.

```python
@dataclass
class InvocationResult:
    """Parsed result from agent execution."""

    success: bool
    exit_code: int

    # Parsed from JSON output if available
    files_modified: list[str] | None
    commits_made: list[str] | None
    errors: list[str] | None
    warnings: list[str] | None

    # Raw output
    stdout: str
    stderr: str
    duration_seconds: float
```

## Enums

```python
class OrchestrationStatus(Enum):
    PENDING = "pending"            # Not started
    RUNNING = "running"            # Actively executing
    PAUSED = "paused"              # User interrupted, can resume
    COMPLETED = "completed"        # All WPs done
    FAILED = "failed"              # Unrecoverable failure

class WPStatus(Enum):
    PENDING = "pending"            # Waiting for dependencies
    READY = "ready"                # Dependencies satisfied, not started
    IMPLEMENTATION = "implementation"  # Being implemented
    REVIEW = "review"              # Being reviewed
    COMPLETED = "completed"        # Both phases done
    FAILED = "failed"              # Failed after all retries

class FallbackStrategy(Enum):
    NEXT_IN_LIST = "next_in_list"  # Try next agent in priority order
    SAME_AGENT = "same_agent"      # Retry with same agent
    FAIL = "fail"                  # Stop immediately
```

## File Schemas

### .kittify/agents.yaml

```yaml
version: "1.0"

defaults:
  implementation:
    - claude-code
    - codex
    - opencode
  review:
    - codex
    - claude-code
    - opencode

agents:
  claude-code:
    enabled: true
    roles: [implementation, review]
    priority: 100
    max_concurrent: 2
    timeout_seconds: 600

  codex:
    enabled: true
    roles: [implementation, review]
    priority: 90
    max_concurrent: 3
    timeout_seconds: 300

  cursor:
    enabled: true
    roles: [implementation]
    priority: 80
    max_concurrent: 1
    timeout_seconds: 300  # With timeout wrapper

fallback:
  strategy: next_in_list
  max_retries: 3

single_agent_mode:
  enabled: false
  agent: null

limits:
  global_concurrency: 5
  global_timeout: 600
```

### .kittify/orchestration-state.json

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "feature_slug": "020-autonomous-multi-agent-orchestrator",
  "started_at": "2026-01-18T17:00:00Z",
  "completed_at": null,
  "status": "running",
  "config_hash": "abc123",
  "concurrency_limit": 5,
  "wps_total": 8,
  "wps_completed": 3,
  "wps_failed": 0,
  "parallel_peak": 3,
  "total_agent_invocations": 6,
  "work_packages": {
    "WP01": {
      "status": "completed",
      "implementation_agent": "claude-code",
      "implementation_exit_code": 0,
      "review_agent": "codex",
      "review_exit_code": 0
    },
    "WP02": {
      "status": "implementation",
      "implementation_agent": "claude-code",
      "implementation_started": "2026-01-18T17:05:00Z"
    },
    "WP03": {
      "status": "pending"
    }
  }
}
```

## Validation Rules

### OrchestratorConfig

- All agent IDs in `defaults` must have corresponding `agents` entries
- If `single_agent_mode.enabled`, `single_agent_mode.agent` must be set and enabled
- `fallback.max_retries` must be >= 0
- `limits.global_concurrency` must be >= 1

### WPExecution

- `implementation_completed` requires `implementation_started` to be set
- `review_started` requires `implementation_completed` to be set
- `status` transitions: pending → ready → implementation → review → completed/failed

### OrchestrationRun

- `completed_at` requires `status` in [completed, failed]
- `wps_completed + wps_failed <= wps_total`
