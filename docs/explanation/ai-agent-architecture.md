# AI Agent Architecture Explained

Spec Kitty supports 12 different AI agents, allowing teams to use their preferred tools. This document explains how the multi-agent system works and why it's designed this way.

## How Slash Commands Work

Slash commands (like `/spec-kitty.specify`) are a convention for invoking predefined workflows:

1. **User types** `/spec-kitty.specify` in their AI agent
2. **Agent reads** the corresponding command file (e.g., `.claude/commands/spec-kitty.specify.md`)
3. **Agent executes** the instructions in that file
4. **Agent interacts** with the user and codebase

The command file contains:
- A detailed prompt explaining what to do
- Instructions for user interaction
- References to templates and artifacts

This lets each AI agent execute the same workflow, even though they have different interfaces.

## The 12 Supported Agents

Spec Kitty supports multiple AI agents across two categories:

### CLI-Based Agents

These agents run from the command line:

| Agent | Directory | Format | CLI Tool |
|-------|-----------|--------|----------|
| Claude Code | `.claude/commands/` | Markdown | `claude` |
| Gemini CLI | `.gemini/commands/` | TOML | `gemini` |
| Cursor | `.cursor/commands/` | Markdown | `cursor-agent` |
| Qwen Code | `.qwen/commands/` | TOML | `qwen` |
| OpenCode | `.opencode/command/` | Markdown | `opencode` |
| Amazon Q | `.amazonq/prompts/` | Markdown | `q` |

### IDE-Based Agents

These agents run inside an IDE or editor:

| Agent | Directory | Format |
|-------|-----------|--------|
| GitHub Copilot | `.github/prompts/` | Markdown |
| Windsurf | `.windsurf/workflows/` | Markdown |
| Kilocode | `.kilocode/workflows/` | Markdown |
| Augment Code | `.augment/commands/` | Markdown |
| Roo Cline | `.roo/commands/` | Markdown |
| GitHub Codex | `.codex/prompts/` | Markdown |

## Agent-Specific Directories

Each agent has its own directory containing command files:

```
project/
├── .claude/
│   └── commands/
│       ├── spec-kitty.specify.md
│       ├── spec-kitty.plan.md
│       ├── spec-kitty.tasks.md
│       ├── spec-kitty.implement.md
│       ├── spec-kitty.review.md
│       └── spec-kitty.accept.md
│
├── .gemini/
│   └── commands/
│       └── [same commands in TOML format]
│
├── .github/
│   └── prompts/
│       └── [same commands for Copilot]
│
└── ... (10 more agent directories)
```

Each directory follows the conventions expected by that agent.

## Command Template System

### Shared Logic, Different Formats

All agents execute the same workflow, but their command file formats differ. Spec Kitty maintains a single source of truth:

```
src/specify_cli/missions/
└── software-dev/
    └── command-templates/
        ├── specify.md      # Template content
        ├── plan.md
        ├── tasks.md
        └── ...
```

During `spec-kitty init`, these templates are adapted for each agent:
- **Markdown agents** get `.md` files
- **TOML agents** get `.toml` files with converted syntax
- **Different arg syntax** (`$ARGUMENTS` vs `{{args}}`) is handled per agent

### Template Structure

Each command template contains:

```markdown
# /spec-kitty.specify - Create Feature Specification

**Purpose**: [What this command does]

## When to Use
[Guidance on when to run this command]

## Workflow
[Step-by-step instructions for the agent]

## Outputs
[What artifacts will be created]

## Example
[Example usage and expected result]
```

### Keeping Templates in Sync

When you upgrade Spec Kitty (`pip install --upgrade spec-kitty-cli`), migrations update all agent directories:

```python
# Example migration updating all 12 agents
for agent_key, (agent_dir, _) in AGENT_DIRS.items():
    update_command_template(agent_key, "specify.md", new_content)
```

This ensures all agents stay synchronized when the workflow changes.

## Multi-Agent Collaboration

### Different Agents on Different WPs

The workspace-per-WP model enables multi-agent collaboration:

```
Feature: 012-user-auth
├── WP01 → Agent A (Claude Code) in .worktrees/012-user-auth-WP01/
├── WP02 → Agent B (Gemini) in .worktrees/012-user-auth-WP02/
└── WP03 → Agent C (Copilot) in .worktrees/012-user-auth-WP03/
```

Each agent:
- Works in its own worktree
- Has its own branch
- Uses the same command templates
- Follows the same workflow

### Why This Works

All agents:
1. Read the same WP prompt from `tasks/WP##.md`
2. Follow the same implementation workflow
3. Use the same lane transitions (planned → doing → for_review)
4. Produce compatible output (code + commits)

The only difference is which AI model powers each agent.

### Orchestration

You can run multiple agents simultaneously:

```bash
# Terminal 1 (Claude Code)
cd .worktrees/012-user-auth-WP01
claude "/spec-kitty.implement WP01"

# Terminal 2 (Gemini)
cd .worktrees/012-user-auth-WP02
gemini "/spec-kitty.implement WP02"

# Terminal 3 (opencode)
cd .worktrees/012-user-auth-WP03
opencode "/spec-kitty.implement WP03"
```

All three work in parallel without conflicts.

## Why Agent-Agnostic?

### User Choice

Different users prefer different agents:
- Some teams use Claude Code for its reasoning
- Some prefer Copilot for IDE integration
- Some use Gemini for its context handling

Spec Kitty doesn't force a choice—use what works for you.

### Vendor Independence

AI agents evolve rapidly:
- New agents appear regularly
- Existing agents gain new capabilities
- Pricing and availability change

By supporting multiple agents, Spec Kitty isn't locked to any single vendor.

### Team Flexibility

A team might use different agents for different tasks:
- Claude Code for complex feature implementation
- Copilot for quick edits and reviews
- Gemini for research tasks

Spec Kitty's workflows work the same regardless of which agent runs them.

## Adding New Agent Support

When a new AI agent appears, Spec Kitty can add support by:

1. **Adding to AGENT_DIRS**: Update the canonical list
2. **Creating directory structure**: `.<agent>/commands/` (or agent-specific path)
3. **Converting templates**: Generate command files in the agent's format
4. **Adding CLI checks**: Verify the agent's CLI tool is installed (if CLI-based)

See [AGENTS.md](../../AGENTS.md) for detailed integration guide.

## Command Execution Flow

```
User: /spec-kitty.implement WP01

    ↓

Agent reads .claude/commands/spec-kitty.implement.md

    ↓

Agent executes workflow:
1. Read WP01 prompt from tasks/WP01.md
2. Create worktree (if needed)
3. Navigate to workspace
4. Implement according to WP requirements
5. Run tests
6. Commit changes
7. Move WP to for_review

    ↓

Result: WP01 implemented in isolated workspace
```

The command file provides all instructions; the agent executes them.

## See Also

- [Workspace-per-WP](workspace-per-wp.md) - How parallel development enables multi-agent collaboration
- [Kanban Workflow](kanban-workflow.md) - How work moves through lanes regardless of agent
- [Mission System](mission-system.md) - How missions customize commands for different work types

---

*This document explains the multi-agent architecture. For how to use specific agents, see the tutorials and how-to guides.*
