# Quickstart: Autonomous Multi-Agent Orchestrator

## Prerequisites

1. **At least one supported agent installed**:
   - Claude Code: `npm install -g @anthropic-ai/claude-code`
   - GitHub Codex: `npm install -g codex`
   - OpenCode: `npm install -g opencode`
   - (See full list of 9 supported agents in plan.md)

2. **A fully planned feature**:
   - Spec, plan, and tasks generated
   - WP dependencies defined in frontmatter

## Basic Usage

### 1. Run Orchestration

```bash
# Start autonomous execution of a feature
spec-kitty orchestrate --feature 020-my-feature

# Or from within a feature context
cd kitty-specs/020-my-feature
spec-kitty orchestrate
```

### 2. Monitor Progress

```bash
# Check current status
spec-kitty orchestrate --status
```

Output:
```
Orchestration: 020-my-feature
Status: running
Progress: 3/8 WPs (37.5%)

Active:
  WP04: claude-code (implementation) - 2m 15s
  WP05: codex (review) - 45s

Completed: WP01, WP02, WP03
Pending: WP06, WP07, WP08
```

### 3. Resume After Interruption

```bash
# If interrupted (Ctrl+C, system restart)
spec-kitty orchestrate --resume
```

### 4. Abort Orchestration

```bash
# Stop and clean up
spec-kitty orchestrate --abort
```

## Configuration

### Agent Preferences

Create `.kittify/agents.yaml` to customize agent selection:

```yaml
version: "1.0"

defaults:
  implementation:
    - claude-code    # First choice for implementation
    - codex          # Fallback
  review:
    - codex          # Different agent for review
    - claude-code    # Fallback

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

fallback:
  strategy: next_in_list  # Try next agent if one fails

limits:
  global_concurrency: 5   # Max parallel agents
```

### Single-Agent Mode

If you only have one agent subscription:

```yaml
single_agent_mode:
  enabled: true
  agent: claude-code
```

The same agent handles both implementation and review.

## Supported Agents

| Agent | Command | Notes |
|-------|---------|-------|
| Claude Code | `claude` | Recommended primary |
| GitHub Codex | `codex` | Good for review |
| GitHub Copilot | `copilot` | |
| Google Gemini | `gemini` | |
| Qwen Code | `qwen` | |
| OpenCode | `opencode` | Multi-provider |
| Kilocode | `kilocode` | |
| Augment Code | `auggie` | |
| Cursor | `cursor` | Requires timeout wrapper |

## Example Workflow

```bash
# 1. Complete planning
/spec-kitty.specify "Add user dashboard"
/spec-kitty.plan
/spec-kitty.tasks

# 2. Configure agents (optional - uses defaults if not set)
cat > .kittify/agents.yaml << 'EOF'
version: "1.0"
defaults:
  implementation: [claude-code]
  review: [codex]
EOF

# 3. Run autonomous orchestration
spec-kitty orchestrate --feature 021-user-dashboard

# 4. Come back later to completed feature
spec-kitty orchestrate --status
# Status: completed
# All 5 WPs done in 23 minutes
```

## Troubleshooting

### Agent Not Found

```
Error: Agent 'claude-code' not installed
```

Install the agent CLI:
```bash
npm install -g @anthropic-ai/claude-code
```

### Authentication Failed

```
Error: Agent 'claude-code' authentication failed
```

Ensure API key is set:
```bash
export ANTHROPIC_API_KEY=sk-...
```

### All Agents Failed

```
Error: WP03 failed after all fallback attempts
```

Check `.kittify/logs/WP03.log` for agent output. Fix the issue manually or adjust the WP prompt.

### Resume Failed

```
Error: No orchestration state found
```

State was lost or corrupted. Start fresh:
```bash
spec-kitty orchestrate --feature 020-my-feature
```
