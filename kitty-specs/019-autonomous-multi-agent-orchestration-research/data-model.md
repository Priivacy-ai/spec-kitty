# Data Model: Agent Orchestration Configuration

**Purpose**: Define the schema for agent profiles used in autonomous multi-agent orchestration.

## Overview

This document defines the data structures that will be populated by research findings and used by the future orchestrator to manage agent invocation.

## Entity: AgentProfile

Represents a single AI coding agent's orchestration capabilities.

```yaml
# Schema for a single agent profile
agent_id: string          # Unique identifier (e.g., "claude-code", "cursor")
display_name: string      # Human-readable name
vendor: string            # Company/organization
spec_kitty_dir: string    # Directory in repo (e.g., ".claude/")

cli:
  available: boolean      # Does a CLI exist?
  command: string | null  # Primary CLI command (e.g., "claude", "cursor")
  installation:
    method: "npm" | "pip" | "brew" | "binary" | "other"
    package: string       # Package name or download URL
  authentication:
    required: boolean
    method: "api_key" | "oauth" | "token" | "none"
    env_var: string | null  # Environment variable for auth

invocation:
  task_input:
    - method: "argument" | "stdin" | "file" | "prompt_file" | "env"
      flag: string | null   # e.g., "-p", "--prompt", "-f"
      example: string       # Working example command
  working_directory: boolean  # Does it respect cwd?
  context_handling: string    # How it handles codebase context

completion:
  exit_codes:
    success: number[]       # e.g., [0]
    error: number[]         # e.g., [1]
    partial: number[]       # e.g., [2] if applicable
  output:
    format: "text" | "json" | "structured"
    location: "stdout" | "file" | "both"
  detection_method: string  # How to know it's done

parallel:
  supported: boolean
  max_concurrent: number | null  # null = unlimited
  rate_limits:
    requests_per_minute: number | null
    tokens_per_day: number | null
  resource_requirements:
    memory_mb: number | null
    cpu_intensive: boolean

orchestration:
  ready: boolean           # Can participate in autonomous workflow?
  limitations: string[]    # What prevents full participation
  complexity: "low" | "medium" | "high"
  recommended_role: "implementation" | "review" | "both" | "none"

sources:
  documentation: string    # Primary docs URL
  repository: string | null
  package: string | null   # npm/pip/etc URL
  notes: string | null
```

## Entity: OrchestratorConfig

User configuration for agent preferences in `.kittify/agents.yaml`.

```yaml
# Schema for user's agent preferences
version: "1.0"

# Default agents for each role
defaults:
  implementation: string[]  # Ordered list of preferred agents for implementing
  review: string[]          # Ordered list of preferred agents for reviewing

# Per-agent overrides
agents:
  <agent_id>:
    enabled: boolean        # Is this agent available for use?
    roles: ["implementation", "review"]  # What roles can it perform?
    priority: number        # Higher = preferred (for role assignment)
    max_concurrent: number  # Override default concurrency limit

# Fallback behavior
fallback:
  strategy: "next_in_list" | "same_agent" | "fail"
  # next_in_list: Try next agent in defaults list
  # same_agent: Use same agent for both roles (single-agent mode)
  # fail: Stop and alert user if preferred agent unavailable

# Single-agent mode (when only one agent configured)
single_agent_mode:
  enabled: boolean
  agent: string | null      # Which agent handles everything
```

## Entity: AgentInvocation

Runtime state for a single agent invocation.

```yaml
# Tracking an active agent run
invocation_id: string       # UUID
agent_id: string
work_package: string        # e.g., "WP01"
role: "implementation" | "review"
workspace_path: string      # Absolute path to worktree

state: "pending" | "running" | "completed" | "failed" | "timeout"
started_at: datetime | null
completed_at: datetime | null
exit_code: number | null

command: string             # Actual command executed
output_log: string          # Path to captured stdout/stderr
```

## Entity: OrchestrationState

Global state for multi-agent workflow.

```yaml
# Persisted in .kittify/orchestration-state.json
feature_slug: string
started_at: datetime
status: "running" | "paused" | "completed" | "failed"

# Work package states
work_packages:
  <wp_id>:
    status: "planned" | "doing" | "for_review" | "done"
    implementation_agent: string | null
    review_agent: string | null
    current_invocation: string | null  # invocation_id

# Active invocations
active_invocations: string[]  # List of invocation_ids currently running

# Dependency tracking (from WP frontmatter)
dependency_graph:
  <wp_id>: string[]  # List of WP IDs this depends on

# Metrics
metrics:
  wps_completed: number
  wps_total: number
  parallel_peak: number     # Max concurrent agents used
```

## Relationships

```
OrchestratorConfig (1) ----< (*) AgentProfile
     |
     | uses
     v
OrchestrationState (1) ----< (*) AgentInvocation
     |                              |
     | tracks                       | executes
     v                              v
WorkPackage (*)                AgentProfile (1)
```

## Validation Rules

### AgentProfile

- `agent_id` must be unique across all profiles
- If `cli.available` is true, `cli.command` must not be null
- If `authentication.required` is true, `authentication.env_var` should be set
- `invocation.task_input` must have at least one entry if `cli.available`

### OrchestratorConfig

- All agent IDs in `defaults` must exist in known agent profiles
- `fallback.strategy` "same_agent" requires `single_agent_mode.enabled: true`
- If `single_agent_mode.enabled`, `single_agent_mode.agent` must be set

### AgentInvocation

- `workspace_path` must be an existing directory
- `completed_at` must be null if `state` is "pending" or "running"
- `exit_code` must be set if `state` is "completed" or "failed"

## Example Configuration

```yaml
# .kittify/agents.yaml
version: "1.0"

defaults:
  implementation:
    - claude-code
    - opencode
    - codex
  review:
    - codex
    - amazon-q
    - claude-code

agents:
  claude-code:
    enabled: true
    roles: [implementation, review]
    priority: 100
    max_concurrent: 2

  codex:
    enabled: true
    roles: [implementation, review]
    priority: 90
    max_concurrent: 3

  cursor:
    enabled: true
    roles: [implementation]
    priority: 80
    max_concurrent: 1

fallback:
  strategy: next_in_list

single_agent_mode:
  enabled: false
  agent: null
```

## Notes

- This schema is a **proposal** based on research requirements
- Actual field values will be populated during research tasks
- Schema may be refined based on CLI testing findings
- Some agents may not support all fields (graceful degradation)
