# Supported AI Agents Reference

Spec Kitty supports **13 AI coding agents** with slash commands. This document lists all supported agents and their configuration details.

---

## Agent Overview

| Agent | Directory | Commands Subdirectory | Slash Commands |
|-------|-----------|----------------------|----------------|
| Claude Code | `.claude/` | `commands/` | `/spec-kitty.*` |
| GitHub Copilot | `.github/` | `prompts/` | `/spec-kitty.*` |
| Google Gemini | `.gemini/` | `commands/` | `/spec-kitty.*` |
| Cursor | `.cursor/` | `commands/` | `/spec-kitty.*` |
| Qwen Code | `.qwen/` | `commands/` | `/spec-kitty.*` |
| OpenCode | `.opencode/` | `command/` | `/spec-kitty.*` |
| Windsurf | `.windsurf/` | `workflows/` | `/spec-kitty.*` |
| GitHub Codex | `.codex/` | `prompts/` | `/spec-kitty.*` |
| Kilocode | `.kilocode/` | `workflows/` | `/spec-kitty.*` |
| Augment Code | `.augment/` | `commands/` | `/spec-kitty.*` |
| Roo Cline | `.roo/` | `commands/` | `/spec-kitty.*` |
| Amazon Q (legacy) | `.amazonq/` | `prompts/` | `/spec-kitty.*` |
| Kiro | `.kiro/` | `prompts/` | `/spec-kitty.*` |

---

## Managing Active Agents

Spec-kitty supports 13 AI agents (listed above). You can activate or deactivate agents at any time using the `spec-kitty agent config` command family.

To manage which agents are active in your project:
- **View configured agents**: `spec-kitty agent config list`
- **Add agents**: `spec-kitty agent config add <agents>`
- **Remove agents**: `spec-kitty agent config remove <agents>`

See [Managing AI Agents](../how-to/manage-agents.md) for complete documentation on agent management workflows.

---

## Agent Details

### Claude Code

**Primary supported agent** — Full feature support and extensive testing.

| Property | Value |
|----------|-------|
| Directory | `.claude/` |
| Commands subdirectory | `commands/` |
| CLI flag | `--ai claude` |
| Status | Fully supported |

**Features**:
- Full slash command support
- Custom command arguments
- Project-level CLAUDE.md integration
- Best documentation and testing coverage

**Usage**:
```bash
spec-kitty init my-project --ai claude
cd my-project
claude  # Launch Claude Code
/spec-kitty.specify Add user authentication
```

---

### GitHub Copilot

| Property | Value |
|----------|-------|
| Directory | `.github/` |
| Commands subdirectory | `prompts/` |
| CLI flag | `--ai copilot` |
| Status | Supported |

**Usage**:
```bash
spec-kitty init my-project --ai copilot
```

---

### Google Gemini

| Property | Value |
|----------|-------|
| Directory | `.gemini/` |
| Commands subdirectory | `commands/` |
| CLI flag | `--ai gemini` |
| Status | Supported |

**Usage**:
```bash
spec-kitty init my-project --ai gemini
```

---

### Cursor

| Property | Value |
|----------|-------|
| Directory | `.cursor/` |
| Commands subdirectory | `commands/` |
| CLI flag | `--ai cursor` |
| Status | Supported |

**Usage**:
```bash
spec-kitty init my-project --ai cursor
```

---

### Qwen Code

| Property | Value |
|----------|-------|
| Directory | `.qwen/` |
| Commands subdirectory | `commands/` |
| CLI flag | `--ai qwen` |
| Status | Supported |

**Usage**:
```bash
spec-kitty init my-project --ai qwen
```

---

### OpenCode

| Property | Value |
|----------|-------|
| Directory | `.opencode/` |
| Commands subdirectory | `command/` (note: singular) |
| CLI flag | `--ai opencode` |
| Status | Supported |

**Note**: OpenCode uses `command/` (singular) instead of `commands/` (plural).

**Usage**:
```bash
spec-kitty init my-project --ai opencode
```

---

### Windsurf

| Property | Value |
|----------|-------|
| Directory | `.windsurf/` |
| Commands subdirectory | `workflows/` |
| CLI flag | `--ai windsurf` |
| Status | Supported |

**Note**: Windsurf uses `workflows/` instead of `commands/`.

**Usage**:
```bash
spec-kitty init my-project --ai windsurf
```

---

### GitHub Codex

| Property | Value |
|----------|-------|
| Directory | `.codex/` |
| Commands subdirectory | `prompts/` |
| CLI flag | `--ai codex` |
| Status | Supported |

**Environment Variable**: Set `CODEX_HOME` to point to your project:
```bash
export CODEX_HOME="$(pwd)/.codex"
```

**Usage**:
```bash
spec-kitty init my-project --ai codex
```

---

### Kilocode

| Property | Value |
|----------|-------|
| Directory | `.kilocode/` |
| Commands subdirectory | `workflows/` |
| CLI flag | `--ai kilocode` |
| Status | Supported |

**Note**: Kilocode uses `workflows/` instead of `commands/`.

**Usage**:
```bash
spec-kitty init my-project --ai kilocode
```

---

### Augment Code

| Property | Value |
|----------|-------|
| Directory | `.augment/` |
| Commands subdirectory | `commands/` |
| CLI flag | `--ai auggie` |
| Status | Supported |

**Usage**:
```bash
spec-kitty init my-project --ai augment
```

---

### Roo Cline

| Property | Value |
|----------|-------|
| Directory | `.roo/` |
| Commands subdirectory | `commands/` |
| CLI flag | `--ai roo` |
| Status | Supported |

**Usage**:
```bash
spec-kitty init my-project --ai roo
```

---

### Amazon Q (legacy)

| Property | Value |
|----------|-------|
| Directory | `.amazonq/` |
| Commands subdirectory | `prompts/` |
| CLI flag | `--ai q` |
| Status | Legacy — rebranded to Kiro |

Amazon Q Developer CLI has been [rebranded to Kiro CLI](https://kiro.dev/docs/cli/migrating-from-q/). Existing projects using `--ai q` continue to work; new projects should select `--ai kiro`. The Kiro installer automatically copies `~/.aws/amazonq/` to `~/.kiro/` at the user level.

**Usage**:
```bash
spec-kitty init my-project --ai q  # legacy
```

---

### Kiro

| Property | Value |
|----------|-------|
| Directory | `.kiro/` |
| Commands subdirectory | `prompts/` |
| CLI flag | `--ai kiro` |
| Binary | `kiro-cli` |
| Status | Supported |

Kiro CLI (formerly Amazon Q Developer CLI) supports slash-command arguments via `$ARGUMENTS`, but the full invocation must be shell-quoted for arguments to pass through. See [kirodotdev/Kiro#4141](https://github.com/kirodotdev/Kiro/issues/4141).

```bash
# Correct — arguments reach $ARGUMENTS
kiro '@speckit.specify my feature description'

# Incorrect — arguments are swallowed
kiro @speckit.specify my feature description
```

**Usage**:
```bash
spec-kitty init my-project --ai kiro
```

---

## Multi-Agent Setup

You can initialize a project with multiple agents:

```bash
# Initialize with Claude and Codex
spec-kitty init my-project --ai claude,codex

# Initialize with all agents
spec-kitty init my-project --ai claude,copilot,gemini,cursor,qwen,opencode,windsurf,codex,kilocode,augment,roo,q
```

This creates command directories for all specified agents, allowing team members to use their preferred tool.

---

## Adding Agents Later

To add agent support to an existing project:

```bash
# Upgrade regenerates all agent directories
spec-kitty upgrade
```

Or manually create the directory structure:

```bash
mkdir -p .cursor/commands
# Copy command files from another agent
cp .claude/commands/*.md .cursor/commands/
```

---

## Slash Commands

All agents support the same 13 slash commands:

| Command | Purpose |
|---------|---------|
| `/spec-kitty.specify` | Create feature specification |
| `/spec-kitty.plan` | Create implementation plan |
| `/spec-kitty.tasks` | Generate work packages |
| `/spec-kitty.implement` | Start WP implementation |
| `/spec-kitty.review` | Review completed work |
| `/spec-kitty.accept` | Accept feature for merge |
| `/spec-kitty.merge` | Merge feature to main |
| `/spec-kitty.status` | Show kanban status |
| `/spec-kitty.dashboard` | Open web dashboard |
| `/spec-kitty.charter` | Create project principles |
| `/spec-kitty.research` | Conduct research |
| `/spec-kitty.checklist` | Generate checklists |
| `/spec-kitty.analyze` | Analyze codebase |

See [Slash Commands](slash-commands.md) for complete documentation.

---

## Agent Selection Guidelines

| Scenario | Recommended Agent |
|----------|-------------------|
| Best overall experience | Claude Code |
| VS Code integration | Cursor, GitHub Copilot |
| JetBrains IDEs | Cursor |
| AWS environment | Kiro (formerly Amazon Q) |
| Open source preference | OpenCode, Qwen |
| Enterprise/air-gapped | Any (local templates available) |

---

## Troubleshooting

### Slash commands not appearing

1. Verify the agent directory exists:
   ```bash
   ls -la .claude/commands/
   ```

2. Regenerate commands:
   ```bash
   spec-kitty upgrade
   ```

3. Restart your AI agent

### Agent-specific issues

**Kiro / Amazon Q**: Slash-command arguments only pass through when the full invocation is shell-quoted (e.g. `kiro '@speckit.specify <description>'`). Without quoting, the trailing text is not forwarded to `$ARGUMENTS`. See [kirodotdev/Kiro#4141](https://github.com/kirodotdev/Kiro/issues/4141).

**Codex**: Ensure `CODEX_HOME` is set:
```bash
export CODEX_HOME="$(pwd)/.codex"
```

---

## See Also

- [Slash Commands](slash-commands.md) — Complete command reference
- [CLI Commands](cli-commands.md) — `spec-kitty` command reference
- [Install & Upgrade](../how-to/install-spec-kitty.md) — Installation guide

## Getting Started
- [Claude Code Integration](../tutorials/claude-code-integration.md)

## Practical Usage
- [Install Spec Kitty](../how-to/install-spec-kitty.md)
- [Use the Dashboard](../how-to/use-dashboard.md)

## Background
- [AI Agent Architecture](../explanation/ai-agent-architecture.md)
