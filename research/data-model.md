# Data Model: Agent Orchestration Configuration

**Purpose**: Define the schema for agent profiles used in autonomous multi-agent orchestration.
**Status**: Complete (populated from WP01-WP06 research)
**Last Updated**: 2026-01-18

## Overview

This document defines the data structures for the spec-kitty multi-agent orchestrator. These schemas are populated from research findings and will be used to manage agent invocation, fallback strategies, and parallel execution.

## Entity: AgentProfile

Represents a single AI coding agent's orchestration capabilities.

```yaml
# Schema for a single agent profile
agent_id: string          # Unique identifier (e.g., "claude-code", "cursor")
display_name: string      # Human-readable name
vendor: string            # Company/organization
spec_kitty_dir: string    # Directory in repo (e.g., ".claude/")
tier: 1 | 2 | 3           # Orchestration readiness tier

cli:
  available: boolean      # Does a CLI exist?
  command: string | null  # Primary CLI command (e.g., "claude", "cursor")
  version: string | null  # Tested version
  installation:
    method: "npm" | "pip" | "brew" | "binary" | "curl"
    package: string       # Package name or download URL
  authentication:
    required: boolean
    method: "api_key" | "oauth" | "token" | "subscription"
    env_var: string | null  # Environment variable for auth

invocation:
  headless_flag: string   # Flag for non-interactive mode (e.g., "-p", "exec")
  auto_approve_flag: string | null  # Flag to skip confirmations (e.g., "--yolo")
  output_format_flag: string | null  # Flag for JSON output
  task_input:
    - method: "argument" | "stdin" | "file"
      flag: string | null   # e.g., "-p", "--prompt", "-f"
      example: string       # Working example command
  working_directory: boolean  # Does it respect cwd?
  context_handling: string    # How it handles codebase context

completion:
  exit_codes:
    success: number[]       # e.g., [0]
    error: number[]         # e.g., [1]
    auth_error: number | null  # Specific auth failure code
  output:
    format: "text" | "json" | "stream-json"
    flag: string | null     # Flag to enable JSON output
  detection_method: string  # How to know it's done

parallel:
  supported: boolean
  max_concurrent: number | null  # null = unlimited
  rate_limits:
    free_tier: string       # Description of free tier limits
    paid_tier: string       # Description of paid tier limits
  session_isolation: boolean  # Does each instance get unique session?

orchestration:
  ready: boolean           # Can participate in autonomous workflow?
  recommended_pattern: string  # Example invocation for orchestration
  limitations: string[]    # What prevents full participation
  complexity: "low" | "medium" | "high"
  recommended_role: "implementation" | "review" | "both" | "none"

sources:
  documentation: string    # Primary docs URL
  repository: string | null
  package: string | null   # npm/pip/etc URL
```

---

## Concrete AgentProfile Instances

### Tier 1: Ready for Autonomous Orchestration

#### claude-code

```yaml
agent_id: "claude-code"
display_name: "Claude Code"
vendor: "Anthropic"
spec_kitty_dir: ".claude/"
tier: 1

cli:
  available: true
  command: "claude"
  version: "2.1.12"
  installation:
    method: "npm"
    package: "@anthropic-ai/claude-code"
  authentication:
    required: true
    method: "api_key"
    env_var: "ANTHROPIC_API_KEY"

invocation:
  headless_flag: "-p"
  auto_approve_flag: "--dangerously-skip-permissions"
  output_format_flag: "--output-format json"
  task_input:
    - method: "argument"
      flag: "-p"
      example: 'claude -p "Your prompt here"'
    - method: "stdin"
      flag: null
      example: 'cat prompt.md | claude -p'
  working_directory: true
  context_handling: "Automatic codebase indexing, respects .gitignore"

completion:
  exit_codes:
    success: [0]
    error: [1]
    auth_error: null
  output:
    format: "json"
    flag: "--output-format json"
  detection_method: "Exit code 0, JSON output with session_id"

parallel:
  supported: true
  max_concurrent: null
  rate_limits:
    free_tier: "Per-model limits from Anthropic"
    paid_tier: "Higher limits with API key"
  session_isolation: true

orchestration:
  ready: true
  recommended_pattern: |
    cat tasks/WP01.md | claude -p \
      --output-format json \
      --allowedTools "Read,Write,Edit,Bash"
  limitations:
    - "No native prompt file flag (use stdin piping)"
    - "Exit codes not extensively documented"
  complexity: "low"
  recommended_role: "both"

sources:
  documentation: "https://code.claude.com/docs/en/headless"
  repository: null
  package: "https://www.npmjs.com/package/@anthropic-ai/claude-code"
```

#### github-codex

```yaml
agent_id: "github-codex"
display_name: "GitHub Codex"
vendor: "OpenAI"
spec_kitty_dir: ".codex/"
tier: 1

cli:
  available: true
  command: "codex"
  version: "0.87.0"
  installation:
    method: "brew"
    package: "codex"
  authentication:
    required: true
    method: "api_key"
    env_var: "CODEX_API_KEY"

invocation:
  headless_flag: "exec"
  auto_approve_flag: "--full-auto"
  output_format_flag: "--json"
  task_input:
    - method: "argument"
      flag: null
      example: 'codex exec "Your prompt here"'
    - method: "stdin"
      flag: "-"
      example: 'cat prompt.md | codex exec -'
  working_directory: true
  context_handling: "Operates in current Git repository, --cd for directory"

completion:
  exit_codes:
    success: [0]
    error: [1]
    auth_error: null
  output:
    format: "json"
    flag: "--json"
  detection_method: "Exit code 0, JSON events stream"

parallel:
  supported: true
  max_concurrent: null
  rate_limits:
    free_tier: "OpenAI API limits"
    paid_tier: "Higher with paid plan"
  session_isolation: true

orchestration:
  ready: true
  recommended_pattern: |
    cat tasks/WP01.md | codex exec - \
      --json \
      --full-auto
  limitations:
    - "Requires Git repository by default"
    - "Exit codes not extensively documented"
  complexity: "low"
  recommended_role: "both"

sources:
  documentation: "https://developers.openai.com/codex/cli/"
  repository: "https://github.com/openai/codex"
  package: "https://www.npmjs.com/package/@openai/codex"
```

#### github-copilot

```yaml
agent_id: "github-copilot"
display_name: "GitHub Copilot"
vendor: "GitHub (Microsoft)"
spec_kitty_dir: ".github/prompts/"
tier: 1

cli:
  available: true
  command: "copilot"
  version: "0.0.384"
  installation:
    method: "brew"
    package: "github/gh-copilot/copilot-cli"
  authentication:
    required: true
    method: "subscription"
    env_var: "GITHUB_TOKEN"

invocation:
  headless_flag: "-p"
  auto_approve_flag: "--yolo"
  output_format_flag: "--silent"
  task_input:
    - method: "argument"
      flag: "-p"
      example: 'copilot -p "Your prompt here"'
    - method: "stdin"
      flag: null
      example: 'copilot -p "$(cat prompt.md)"'
  working_directory: true
  context_handling: "Operates in cwd, --add-dir for additional paths"

completion:
  exit_codes:
    success: [0]
    error: [1]
    auth_error: null
  output:
    format: "text"
    flag: "--silent"
  detection_method: "Exit code 0, silent output for scripting"

parallel:
  supported: true
  max_concurrent: null
  rate_limits:
    free_tier: "Requires Copilot subscription"
    paid_tier: "Business/Enterprise: Higher limits"
  session_isolation: true

orchestration:
  ready: true
  recommended_pattern: |
    copilot -p "$(cat tasks/WP01.md)" \
      --yolo \
      --silent
  limitations:
    - "Requires GitHub Copilot subscription"
    - "No offline mode"
  complexity: "low"
  recommended_role: "both"

sources:
  documentation: "https://github.com/github/copilot-cli"
  repository: "https://github.com/github/copilot-cli"
  package: "https://www.npmjs.com/package/@github/copilot-cli"
```

#### google-gemini

```yaml
agent_id: "google-gemini"
display_name: "Google Gemini"
vendor: "Google"
spec_kitty_dir: ".gemini/"
tier: 1

cli:
  available: true
  command: "gemini"
  version: "0.24.0"
  installation:
    method: "npm"
    package: "@google/gemini-cli"
  authentication:
    required: true
    method: "oauth"
    env_var: "GEMINI_API_KEY"

invocation:
  headless_flag: "-p"
  auto_approve_flag: "--yolo"
  output_format_flag: "--output-format json"
  task_input:
    - method: "argument"
      flag: "-p"
      example: 'gemini -p "Your prompt here"'
    - method: "stdin"
      flag: null
      example: 'cat prompt.md | gemini -p "analyze"'
  working_directory: true
  context_handling: "Automatic indexing, respects .gitignore, uses AGENTS.md"

completion:
  exit_codes:
    success: [0]
    error: [1]
    auth_error: 41
  output:
    format: "json"
    flag: "--output-format json"
  detection_method: "Exit codes (0=success, 41=auth, 42=input, 52=config, 130=cancelled)"

parallel:
  supported: true
  max_concurrent: null
  rate_limits:
    free_tier: "60/min, 1000/day"
    paid_tier: "Vertex AI: Usage-based billing"
  session_isolation: true

orchestration:
  ready: true
  recommended_pattern: |
    gemini -p "$(cat tasks/WP01.md)" \
      --yolo \
      --output-format json
  limitations:
    - "Rate limits on free tier"
    - "1M token context limit"
  complexity: "low"
  recommended_role: "both"

sources:
  documentation: "https://developers.google.com/gemini-code-assist/docs/gemini-cli"
  repository: "https://github.com/google-gemini/gemini-cli"
  package: "https://www.npmjs.com/package/@google/gemini-cli"
```

#### qwen-code

```yaml
agent_id: "qwen-code"
display_name: "Qwen Code"
vendor: "Alibaba"
spec_kitty_dir: ".qwen/"
tier: 1

cli:
  available: true
  command: "qwen"
  version: "0.7.1"
  installation:
    method: "npm"
    package: "@qwen-code/qwen-code"
  authentication:
    required: true
    method: "api_key"
    env_var: "OPENAI_API_KEY"

invocation:
  headless_flag: "-p"
  auto_approve_flag: "--yolo"
  output_format_flag: "--output-format json"
  task_input:
    - method: "argument"
      flag: "-p"
      example: 'qwen -p "Your prompt here"'
    - method: "stdin"
      flag: null
      example: 'cat prompt.md | qwen -p'
  working_directory: true
  context_handling: "Fork of Gemini CLI with identical capabilities"

completion:
  exit_codes:
    success: [0]
    error: [1]
    auth_error: null
  output:
    format: "json"
    flag: "--output-format json"
  detection_method: "Exit code 0, JSON array output"

parallel:
  supported: true
  max_concurrent: null
  rate_limits:
    free_tier: "2000/day"
    paid_tier: "Provider-dependent (OpenAI-compatible)"
  session_isolation: true

orchestration:
  ready: true
  recommended_pattern: |
    qwen -p "$(cat tasks/WP01.md)" \
      --yolo \
      --output-format json
  limitations:
    - "Fork of Gemini CLI"
  complexity: "low"
  recommended_role: "both"

sources:
  documentation: "https://qwenlm.github.io/qwen-code-docs/"
  repository: "https://github.com/QwenLM/qwen-code"
  package: "https://www.npmjs.com/package/@qwen-code/qwen-code"
```

#### opencode

```yaml
agent_id: "opencode"
display_name: "OpenCode"
vendor: "OpenCode AI"
spec_kitty_dir: ".opencode/"
tier: 1

cli:
  available: true
  command: "opencode"
  version: "1.1.14"
  installation:
    method: "curl"
    package: "https://opencode.ai/install"
  authentication:
    required: false
    method: "api_key"
    env_var: null

invocation:
  headless_flag: "run"
  auto_approve_flag: null
  output_format_flag: "--format json"
  task_input:
    - method: "argument"
      flag: null
      example: 'opencode run "Your prompt here"'
    - method: "stdin"
      flag: null
      example: 'cat prompt.md | opencode run'
    - method: "file"
      flag: "-f"
      example: 'opencode run -f prompt.md "Complete this"'
  working_directory: true
  context_handling: "Operates in current directory, multi-provider support"

completion:
  exit_codes:
    success: [0]
    error: [1]
    auth_error: null
  output:
    format: "json"
    flag: "--format json"
  detection_method: "Exit code 0, JSON output"

parallel:
  supported: true
  max_concurrent: null
  rate_limits:
    free_tier: "Provider-dependent"
    paid_tier: "Multi-provider flexibility"
  session_isolation: true

orchestration:
  ready: true
  recommended_pattern: |
    cat tasks/WP01.md | opencode run \
      --format json
  limitations:
    - "No explicit auto-approve flag"
    - "Newer project, documentation evolving"
  complexity: "low"
  recommended_role: "both"

sources:
  documentation: "https://opencode.ai/docs/cli/"
  repository: "https://github.com/opencode-ai/opencode"
  package: "https://www.npmjs.com/package/opencode"
```

#### kilocode

```yaml
agent_id: "kilocode"
display_name: "Kilocode"
vendor: "Kilo Code"
spec_kitty_dir: ".kilocode/"
tier: 1

cli:
  available: true
  command: "kilocode"
  version: "0.23.1"
  installation:
    method: "npm"
    package: "@kilocode/cli"
  authentication:
    required: true
    method: "token"
    env_var: null

invocation:
  headless_flag: "-a"
  auto_approve_flag: "--yolo"
  output_format_flag: "-j"
  task_input:
    - method: "argument"
      flag: null
      example: 'kilocode -a "Your prompt here"'
    - method: "stdin"
      flag: "-i"
      example: 'echo "prompt" | kilocode -i'
  working_directory: true
  context_handling: "Workspace directory, MCP support, --parallel for branches"

completion:
  exit_codes:
    success: [0]
    error: [1]
    auth_error: null
  output:
    format: "json"
    flag: "-j"
  detection_method: "Exit code 0, JSON output"

parallel:
  supported: true
  max_concurrent: null
  rate_limits:
    free_tier: "Provider-dependent"
    paid_tier: "No Kilocode-specific limits"
  session_isolation: true

orchestration:
  ready: true
  recommended_pattern: |
    kilocode -a --yolo -j "$(cat tasks/WP01.md)"
  limitations:
    - "Requires kilocode auth"
  complexity: "low"
  recommended_role: "both"

sources:
  documentation: "https://kilo.ai/docs/"
  repository: "https://github.com/Kilo-Org/kilocode"
  package: "https://www.npmjs.com/package/@kilocode/cli"
```

#### augment-code

```yaml
agent_id: "augment-code"
display_name: "Augment Code (Auggie)"
vendor: "Augment Code"
spec_kitty_dir: ".augment/"
tier: 1

cli:
  available: true
  command: "auggie"
  version: "0.14.0"
  installation:
    method: "npm"
    package: "@augmentcode/auggie"
  authentication:
    required: true
    method: "token"
    env_var: "AUGMENT_SESSION_AUTH"

invocation:
  headless_flag: "--acp"
  auto_approve_flag: null
  output_format_flag: null
  task_input:
    - method: "argument"
      flag: null
      example: 'auggie --acp "Your prompt here"'
    - method: "stdin"
      flag: null
      example: 'cat prompt.md | auggie --acp'
  working_directory: true
  context_handling: "ACP mode for non-interactive operation"

completion:
  exit_codes:
    success: [0]
    error: [1]
    auth_error: null
  output:
    format: "text"
    flag: null
  detection_method: "Exit code 0, structured output in ACP mode"

parallel:
  supported: true
  max_concurrent: null
  rate_limits:
    free_tier: "3000 msg/month"
    paid_tier: "Developer ($30): Unlimited"
  session_isolation: true

orchestration:
  ready: true
  recommended_pattern: |
    auggie --acp "$(cat tasks/WP01.md)"
  limitations:
    - "Service account setup needed for automation"
  complexity: "low"
  recommended_role: "both"

sources:
  documentation: "https://docs.augmentcode.com/cli/setup-auggie/install-auggie-cli"
  repository: null
  package: "https://www.npmjs.com/package/@augmentcode/auggie"
```

### Tier 2: Partial Support (Workarounds Needed)

#### cursor

```yaml
agent_id: "cursor"
display_name: "Cursor"
vendor: "Cursor Inc"
spec_kitty_dir: ".cursor/"
tier: 2

cli:
  available: true
  command: "cursor"
  version: "2026.01.17"
  installation:
    method: "binary"
    package: "Bundled with Cursor IDE"
  authentication:
    required: true
    method: "subscription"
    env_var: "CURSOR_API_KEY"

invocation:
  headless_flag: "agent -p"
  auto_approve_flag: "--force"
  output_format_flag: "--output-format json"
  task_input:
    - method: "argument"
      flag: "-p"
      example: 'cursor agent -p "Your prompt here"'
  working_directory: true
  context_handling: "IDE context, may hang after completion"

completion:
  exit_codes:
    success: [0]
    error: [1]
    auth_error: null
  output:
    format: "json"
    flag: "--output-format json"
  detection_method: "JSON output (may hang - use timeout wrapper)"

parallel:
  supported: true
  max_concurrent: null
  rate_limits:
    free_tier: "Limited"
    paid_tier: "Pro: Higher limits"
  session_isolation: true

orchestration:
  ready: true
  recommended_pattern: |
    timeout 300 cursor agent -p --force --output-format json "$(cat tasks/WP01.md)"
  limitations:
    - "CLI may hang after completion - requires timeout wrapper"
    - "Stdin problematic - use shell substitution"
    - "Exit codes not well documented"
  complexity: "medium"
  recommended_role: "implementation"

sources:
  documentation: "https://cursor.com/docs/cli/headless"
  repository: null
  package: null
```

### Tier 3: Not Suitable for Autonomous Orchestration

#### windsurf

```yaml
agent_id: "windsurf"
display_name: "Windsurf"
vendor: "Codeium"
spec_kitty_dir: ".windsurf/"
tier: 3

cli:
  available: false
  command: "windsurf"
  version: "1.106.0"
  installation:
    method: "binary"
    package: "Desktop application"
  authentication:
    required: true
    method: "subscription"
    env_var: null

invocation:
  headless_flag: null
  auto_approve_flag: null
  output_format_flag: null
  task_input: []
  working_directory: true
  context_handling: "GUI only - windsurf chat opens IDE"

completion:
  exit_codes:
    success: []
    error: []
    auth_error: null
  output:
    format: "text"
    flag: null
  detection_method: "N/A - GUI only"

parallel:
  supported: false
  max_concurrent: null
  rate_limits:
    free_tier: "N/A"
    paid_tier: "N/A"
  session_isolation: false

orchestration:
  ready: false
  recommended_pattern: null
  limitations:
    - "GUI-only, no native headless mode"
    - "Docker workaround (windsurfinabox) is fragile"
  complexity: "high"
  recommended_role: "none"

sources:
  documentation: "https://docs.windsurf.com"
  repository: null
  package: null
```

#### roo-code

```yaml
agent_id: "roo-code"
display_name: "Roo Code"
vendor: "Roo Code Inc"
spec_kitty_dir: ".roo/"
tier: 3

cli:
  available: false
  command: null
  version: null
  installation:
    method: "other"
    package: "VS Code extension"
  authentication:
    required: true
    method: "token"
    env_var: null

invocation:
  headless_flag: null
  auto_approve_flag: null
  output_format_flag: null
  task_input: []
  working_directory: false
  context_handling: "IPC requires VS Code running"

completion:
  exit_codes:
    success: []
    error: []
    auth_error: null
  output:
    format: "text"
    flag: null
  detection_method: "IPC messages"

parallel:
  supported: false
  max_concurrent: null
  rate_limits:
    free_tier: "N/A"
    paid_tier: "N/A"
  session_isolation: false

orchestration:
  ready: false
  recommended_pattern: null
  limitations:
    - "No official CLI yet"
    - "IPC requires VS Code running"
    - "Third-party tools (roo-cli) available but not official"
  complexity: "high"
  recommended_role: "none"

sources:
  documentation: "https://docs.roocode.com/"
  repository: "https://github.com/RooCodeInc/Roo-Code"
  package: null
```

#### amazon-q

```yaml
agent_id: "amazon-q"
display_name: "Amazon Q Developer"
vendor: "Amazon Web Services"
spec_kitty_dir: ".amazonq/"
tier: 3

cli:
  available: false
  command: "q"
  version: null
  installation:
    method: "other"
    package: "AWS CLI extension"
  authentication:
    required: true
    method: "token"
    env_var: null

invocation:
  headless_flag: null
  auto_approve_flag: null
  output_format_flag: null
  task_input: []
  working_directory: false
  context_handling: "Chat-based, transitioning to Kiro"

completion:
  exit_codes:
    success: []
    error: []
    auth_error: null
  output:
    format: "text"
    flag: null
  detection_method: "Not documented"

parallel:
  supported: false
  max_concurrent: null
  rate_limits:
    free_tier: "Unknown"
    paid_tier: "Unknown"
  session_isolation: false

orchestration:
  ready: false
  recommended_pattern: null
  limitations:
    - "Product transitioning to Kiro"
    - "Unclear headless automation story"
    - "CLI is chat-based, not task-oriented"
  complexity: "high"
  recommended_role: "none"

sources:
  documentation: "https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line.html"
  repository: null
  package: null
```

---

## Entity: OrchestratorConfig

User configuration for agent preferences in `.kittify/agents.yaml`.

```yaml
# Schema for user's agent preferences
version: "1.0"

# Global settings
global:
  timeout_seconds: 300           # Default timeout for agent invocations
  retry_count: 2                 # Number of retries on transient failures
  rate_limit_buffer: 0.8         # Stay at 80% of rate limits
  workspace_isolation: true      # Use git worktrees for parallel execution

# Default agents for each role (ordered by preference)
defaults:
  implementation:
    - string                     # Ordered list of preferred agents for implementing
  review:
    - string                     # Ordered list of preferred agents for reviewing

# Per-agent overrides
agents:
  <agent_id>:
    enabled: boolean             # Is this agent available for use?
    roles: ["implementation", "review"]  # What roles can it perform?
    priority: number             # Higher = preferred (for role assignment)
    max_concurrent: number       # Override default concurrency limit
    timeout_seconds: number      # Override default timeout
    custom_flags: string[]       # Additional CLI flags to pass

# Fallback behavior when preferred agent unavailable
fallback:
  strategy: "next_in_list" | "same_agent" | "fail" | "queue"
  # next_in_list: Try next agent in defaults list
  # same_agent: Use same agent for both roles (single-agent mode)
  # fail: Stop and alert user if preferred agent unavailable
  # queue: Wait and retry later

  max_fallback_attempts: number  # How many agents to try before failing
  queue_timeout_minutes: number  # For queue strategy: max wait time

# Single-agent mode (when only one agent configured or available)
single_agent_mode:
  enabled: boolean | "auto"      # "auto" = detect based on available agents
  agent: string | null           # Which agent handles everything (null = auto-select)
  review_delay_seconds: number   # Delay before same agent reviews its own work
```

### Validation Rules

1. All agent IDs in `defaults` must exist in known agent profiles or `agents` overrides
2. `fallback.strategy` "same_agent" is automatically enabled when only one agent available
3. If `single_agent_mode.enabled: true`, `single_agent_mode.agent` must reference an enabled agent
4. `priority` values must be unique within the same role
5. `max_concurrent` cannot exceed system limits (recommended: 5)
6. `timeout_seconds` must be between 60 and 3600

---

## Entity: AgentInvocation

Runtime state for a single agent invocation.

```yaml
# Tracking an active agent run
invocation_id: string       # UUID
agent_id: string
work_package: string        # e.g., "WP01"
role: "implementation" | "review"
workspace_path: string      # Absolute path to worktree

state: "pending" | "running" | "completed" | "failed" | "timeout" | "cancelled"
started_at: datetime | null
completed_at: datetime | null
exit_code: number | null
retry_count: number         # How many times this invocation has been retried

command: string             # Actual command executed
output_log: string          # Path to captured stdout/stderr
error_message: string | null  # Error description if failed

# Metrics
tokens_used: number | null
duration_seconds: number | null
```

---

## Entity: OrchestrationState

Global state for multi-agent workflow.

```yaml
# Persisted in .kittify/orchestration-state.json
feature_slug: string
started_at: datetime
updated_at: datetime
status: "running" | "paused" | "completed" | "failed"

# Work package states
work_packages:
  <wp_id>:
    status: "planned" | "doing" | "for_review" | "done"
    implementation_agent: string | null
    review_agent: string | null
    current_invocation: string | null  # invocation_id
    attempts: number                    # Total invocation attempts

# Active invocations
active_invocations: string[]  # List of invocation_ids currently running

# Dependency tracking (from WP frontmatter)
dependency_graph:
  <wp_id>: string[]  # List of WP IDs this depends on

# Agent health
agent_health:
  <agent_id>:
    last_success: datetime | null
    last_failure: datetime | null
    consecutive_failures: number
    is_rate_limited: boolean
    rate_limit_reset: datetime | null

# Metrics
metrics:
  wps_completed: number
  wps_total: number
  parallel_peak: number     # Max concurrent agents used
  total_tokens: number
  total_duration_seconds: number
```

---

## Fallback Strategy Details

### Strategy: `next_in_list`

When the preferred agent is unavailable, try the next agent in the defaults list.

```yaml
# Example: claude-code is rate-limited
# defaults.implementation: [claude-code, codex, opencode]
# Result: Tries codex, then opencode if codex also unavailable
```

**Triggers**:
- Agent not installed
- Authentication failed
- Rate limit exceeded
- Invocation timed out
- Non-zero exit code

**Behavior**:
1. Log failure and reason
2. Mark current agent as temporarily unavailable
3. Select next agent from defaults list
4. Retry invocation with new agent
5. After `max_fallback_attempts`, fail the WP

### Strategy: `same_agent`

Use the same agent for both implementation and review roles.

```yaml
# Single-agent mode
# Same agent implements and reviews
# Built-in delay before review to prevent cached context
```

**Use Cases**:
- Only one agent available
- User preference for consistency
- Cost optimization

**Behavior**:
1. Agent completes implementation
2. Wait `review_delay_seconds` (default: 30)
3. Same agent performs review
4. May result in less thorough reviews

### Strategy: `fail`

Stop immediately when preferred agent is unavailable.

```yaml
# Strict mode - no fallback
# Useful for CI/CD where specific agent is required
```

**Behavior**:
1. Log failure and reason
2. Mark WP as failed
3. Pause orchestration
4. Alert user

### Strategy: `queue`

Wait and retry later when agent becomes available.

```yaml
# Useful when rate-limited
# Waits until rate limit resets
```

**Behavior**:
1. Log reason for queuing
2. Calculate retry time (based on rate limit reset or backoff)
3. Queue invocation
4. Continue with other WPs if possible
5. Retry after wait period
6. Fail if `queue_timeout_minutes` exceeded

---

## Single-Agent Mode

When only one agent is configured or available, the orchestrator operates in single-agent mode.

### Configuration

```yaml
single_agent_mode:
  enabled: "auto"        # Automatically enable when only one agent
  agent: null            # Auto-select the available agent
  review_delay_seconds: 30
```

### Behavior

1. **Detection**: If `enabled: "auto"`, check how many agents are enabled
2. **Selection**: Use `agent` if specified, otherwise use the only enabled agent
3. **Implementation**: Normal invocation
4. **Review**: Same agent reviews after delay
5. **Quality Considerations**:
   - Log warning that same agent is reviewing its own work
   - Consider longer delay (60s) to reduce context carryover
   - May want to use different temperature or system prompt for review

### Quality Mitigations

```yaml
# For single-agent mode, consider appending to system prompt:
single_agent_mode:
  enabled: true
  agent: "claude-code"
  review_delay_seconds: 60
  review_system_prompt_append: |
    You are now reviewing code that you previously wrote.
    Be especially critical and look for issues you might have overlooked.
    Focus on: edge cases, error handling, security, and maintainability.
```

---

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

---

## Example Configuration Files

### Full Configuration

```yaml
# .kittify/agents.yaml
version: "1.0"

global:
  timeout_seconds: 300
  retry_count: 2
  rate_limit_buffer: 0.8
  workspace_isolation: true

defaults:
  implementation:
    - claude-code      # Best overall for implementation
    - github-codex     # Strong alternative
    - opencode         # Multi-provider fallback
  review:
    - github-codex     # Different perspective for review
    - google-gemini    # Large context window
    - claude-code      # Fallback

agents:
  claude-code:
    enabled: true
    roles: [implementation, review]
    priority: 100
    max_concurrent: 2

  github-codex:
    enabled: true
    roles: [implementation, review]
    priority: 90
    max_concurrent: 3

  google-gemini:
    enabled: true
    roles: [review]
    priority: 80
    max_concurrent: 2

  opencode:
    enabled: true
    roles: [implementation]
    priority: 70
    max_concurrent: 2

  cursor:
    enabled: true
    roles: [implementation]
    priority: 60
    max_concurrent: 1
    timeout_seconds: 600  # Longer timeout due to potential hanging
    custom_flags:
      - "--force"

fallback:
  strategy: next_in_list
  max_fallback_attempts: 3
  queue_timeout_minutes: 30

single_agent_mode:
  enabled: "auto"
  agent: null
  review_delay_seconds: 30
```

### Minimal Single-Agent Configuration

```yaml
# .kittify/agents.yaml
# For users with only Claude Code
version: "1.0"

defaults:
  implementation: [claude-code]
  review: [claude-code]

agents:
  claude-code:
    enabled: true
    roles: [implementation, review]
    priority: 100

fallback:
  strategy: fail

single_agent_mode:
  enabled: true
  agent: claude-code
  review_delay_seconds: 60
```

### Enterprise Multi-Agent Configuration

```yaml
# .kittify/agents.yaml
# For enterprise with multiple agents
version: "1.0"

global:
  timeout_seconds: 600
  retry_count: 3
  rate_limit_buffer: 0.7
  workspace_isolation: true

defaults:
  implementation:
    - github-copilot   # Enterprise has higher limits
    - claude-code
    - github-codex
    - kilocode
  review:
    - google-gemini    # Large context for comprehensive review
    - github-codex
    - claude-code

agents:
  github-copilot:
    enabled: true
    roles: [implementation]
    priority: 100
    max_concurrent: 5
    custom_flags:
      - "--model"
      - "gpt-5.2-codex"

  claude-code:
    enabled: true
    roles: [implementation, review]
    priority: 95
    max_concurrent: 3

  github-codex:
    enabled: true
    roles: [implementation, review]
    priority: 90
    max_concurrent: 4

  google-gemini:
    enabled: true
    roles: [review]
    priority: 85
    max_concurrent: 2

  kilocode:
    enabled: true
    roles: [implementation]
    priority: 80
    max_concurrent: 3
    custom_flags:
      - "--parallel"

fallback:
  strategy: next_in_list
  max_fallback_attempts: 4
  queue_timeout_minutes: 60

single_agent_mode:
  enabled: false
  agent: null
```

---

## Notes

- AgentProfile schema populated from WP01-WP06 research (2026-01-18)
- 8 Tier-1 agents, 1 Tier-2 agent, 3 Tier-3 agents
- Schema designed for extensibility as agent capabilities evolve
- Fallback strategies handle real-world scenarios: rate limits, auth failures, timeouts
- Single-agent mode provides graceful degradation for simple setups
