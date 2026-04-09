# Non-Interactive Init Mode

## Summary

✅ **spec-kitty init IS fully non-interactive** when `--non-interactive` (or the environment variable) is set and required options are provided.

## Complete Non-Interactive Syntax

```bash
spec-kitty init <project-name> \
  --ai <agents> \
  [--non-interactive] \
  [--no-git]
```

## Required Arguments for Non-Interactive Mode

### 1. Project Name or Location

**Option A: New project directory**
```bash
spec-kitty init my-project
```

**Option B: Current directory**
```bash
spec-kitty init .
```

### 2. AI Assistants (`--ai`)

**Syntax**: Comma-separated list of agent keys (no spaces)

```bash
--ai codex
--ai claude,codex
--ai claude,codex,cursor,windsurf
--ai copilot,gemini,qwen
```

**Valid agent keys**:
| Key | Agent Name |
|-----|------------|
| `codex` | Codex CLI (OpenAI) |
| `claude` | Claude Code |
| `gemini` | Gemini CLI |
| `cursor` | Cursor |
| `qwen` | Qwen Code |
| `opencode` | opencode |
| `windsurf` | Windsurf |
| `kilocode` | Kilo Code |
| `auggie` | Auggie CLI (Augment Code) |
| `roo` | Roo Code |
| `copilot` | GitHub Copilot |
| `q` | Amazon Q Developer CLI |

**Case-sensitive**: Use lowercase exactly as shown

## Optional Flags

| Flag | Purpose | Default |
|------|---------|---------|
| `--non-interactive` / `--yes` | Disable prompts (required for CI) | Off |
| `--no-git` | Skip git repository initialization | Off (initializes git) |

## Complete Non-Interactive Examples

### Example 1: New project with Codex
```bash
spec-kitty init my-project \
  --ai codex \
  --non-interactive
```

### Example 2: Current directory with multiple agents
```bash
spec-kitty init . \
  --ai claude,codex,cursor \
  --non-interactive
```

### Example 3: Minimal (relies on defaults)
```bash
# In non-interactive environment (CI/CD):
spec-kitty init my-project --ai codex --non-interactive
```

### Example 4: CI/CD friendly
```bash
spec-kitty init . \
  --ai claude \
  --no-git \
  --non-interactive
```

### Example 5: All 12 agents
```bash
spec-kitty init my-project \
  --ai codex,claude,gemini,cursor,qwen,opencode,windsurf,kilocode,auggie,roo,copilot,q \
  --non-interactive
```

## Interactive vs Non-Interactive Behavior

### Interactive Mode (Default)

Triggered when:
- Running from a terminal (TTY)
- `--non-interactive` / `--yes` is NOT provided

Presents:
- Multi-select menu for AI assistants (space to select, enter to confirm)
- Confirmation prompt if directory not empty

### Non-Interactive Mode

Triggered when:
- `--non-interactive` / `--yes` is provided
- OR `SPEC_KITTY_NON_INTERACTIVE=1` is set
- OR running in non-TTY environment (pipes, CI/CD, scripts)

Behavior:
- Uses provided values
- Falls back to defaults for omitted options
- No prompts
- Suitable for automation

## CI/CD Usage

```yaml
# GitHub Actions example
- name: Initialize Spec Kitty
  run: |
spec-kitty init . \
  --ai codex \
  --no-git \
  --non-interactive
```

```bash
# Docker/script example
#!/bin/bash
spec-kitty init /app/project \
  --ai claude,codex \
  --non-interactive
```

## What Gets Created (Agent-Specific)

When you specify agents with `--ai`, spec-kitty creates:

### For `--ai codex`:
- `.codex/prompts/spec-kitty.*.md` (13 command files)
- `.kittify/AGENTS.md` (auto-loaded by Codex)
- No extra context files needed (native AGENTS.md support!)

### For `--ai claude`:
- `.claude/commands/spec-kitty.*.md` (13 command files)
- `.kittify/AGENTS.md`
- `CLAUDE.md` → symlink to `.kittify/AGENTS.md`

### For `--ai cursor`:
- `.cursor/commands/spec-kitty.*.md` (13 command files)
- `.kittify/AGENTS.md`
- `.cursorrules` → symlink to `.kittify/AGENTS.md` (legacy)
- `.cursor/rules/AGENTS.md` → symlink to `.kittify/AGENTS.md` (modern)

### For `--ai windsurf`:
- `.windsurf/workflows/spec-kitty.*.md` (13 workflow files)
- `.kittify/AGENTS.md`
- `.windsurfrules` → symlink to `.kittify/AGENTS.md` (legacy)
- `.windsurf/rules/AGENTS.md` → symlink to `.kittify/AGENTS.md` (modern)

### For `--ai roo`:
- `.roo/commands/spec-kitty.*.md` (13 command files)
- `.kittify/AGENTS.md`
- `.roorules` → symlink to `.kittify/AGENTS.md` (legacy)
- `.roo/rules/AGENTS.md` → symlink to `.kittify/AGENTS.md` (modern)

### For `--ai gemini`:
- `.gemini/commands/spec-kitty.*.toml` (13 command files in TOML format)
- `.kittify/AGENTS.md`
- `GEMINI.md` → symlink to `.kittify/AGENTS.md`

### For `--ai copilot`:
- `.github/prompts/spec-kitty.*.prompt.md` (13 prompt files)
- `.kittify/AGENTS.md`
- `.github/copilot-instructions.md` → symlink to `.kittify/AGENTS.md`

### For `--ai kilocode`:
- `.kilocode/workflows/spec-kitty.*.md` (13 workflow files)
- `.kittify/AGENTS.md`
- `.kilocoderules` → symlink to `.kittify/AGENTS.md`

### For `--ai opencode`:
- `.opencode/command/spec-kitty.*.md` (13 command files)
- `.kittify/AGENTS.md`
- Note: Requires manual config entry in opencode.json

### For `--ai auggie`:
- `.augment/commands/spec-kitty.*.md` (13 command files)
- `.kittify/AGENTS.md`
- `.augmentrules` → symlink to `.kittify/AGENTS.md` (assumed)

### For `--ai qwen`:
- `.qwen/commands/spec-kitty.*.toml` (13 command files in TOML format)
- `.kittify/AGENTS.md`

### For `--ai q`:
- `.amazonq/prompts/spec-kitty.*.md` (13 prompt files)
- `.kittify/AGENTS.md`
- Note: May have discovery issues (known bug)

## Always Created (Regardless of Agent Selection)

- `.kittify/` directory structure
- `.kittify/AGENTS.md` (master copy)
- `.kittify/templates/` (command templates)
- `.kittify/scripts/` (helper scripts)
- `.kittify/memory/` (for charter, etc.)

## Platform-Specific Behavior

### Unix/Mac (Has Symlinks)
All agent-specific context files are **symlinks** to `.kittify/AGENTS.md`:
```bash
ls -l CLAUDE.md
# lrwxr-xr-x  CLAUDE.md -> .kittify/AGENTS.md
```

**Benefit**: Single source of truth, updates to AGENTS.md instantly affect all agents

### Windows (No Symlinks by Default)
All agent-specific context files are **copies** of `.kittify/AGENTS.md`:
```powershell
ls CLAUDE.md
# -rw-r--r--  CLAUDE.md
```

**Tradeoff**: Multiple copies, need to update each if editing manually
**Recommended**: Edit `.kittify/AGENTS.md` and run `spec-kitty upgrade` to refresh

## Verification

After non-interactive init, verify with:

```bash
# Check what was created
ls -la | grep -E "^(l|-).*AGENTS|rules$"

# Check command files for specific agent
ls .codex/prompts/          # Codex
ls .claude/commands/        # Claude
ls .cursor/commands/        # Cursor
ls .gemini/commands/        # Gemini (TOML)
```

## Troubleshooting

### "Invalid AI assistant"
```bash
# ERROR
spec-kitty init proj --ai CODEX

# CORRECT (lowercase)
spec-kitty init proj --ai codex
```

Valid keys are lowercase: `codex`, `claude`, `gemini`, `cursor`, `qwen`, `opencode`, `windsurf`, `kilocode`, `auggie`, `roo`, `copilot`, `q`

## Complete Reference

### Minimal Non-Interactive Init
```bash
spec-kitty init my-project --ai codex --non-interactive
```

### Maximum Options
```bash
spec-kitty init my-project \
  --ai codex,claude,cursor \
  --no-git \
  --non-interactive
```

### Current Directory
```bash
spec-kitty init . --ai codex --non-interactive
```

## Environment Variables

Can also be set via environment:
- `SPECIFY_TEMPLATE_REPO` - Override template source (e.g., `myorg/custom-templates`)
- `SPEC_KITTY_NON_INTERACTIVE` - Force non-interactive mode (set to `1`)

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid args, missing tools, directory conflict, etc.) |

Use in scripts:
```bash
if spec-kitty init my-project --ai codex; then
  echo "Init succeeded"
else
  echo "Init failed with code $?"
fi
```

## Automation Example

```bash
#!/bin/bash
# Automated project setup script

PROJECT_NAME="$1"
AI_AGENTS="${2:-codex}"  # Default to codex

spec-kitty init "$PROJECT_NAME" \
  --ai "$AI_AGENTS" \
  --non-interactive || exit 1

cd "$PROJECT_NAME"
echo "Project initialized successfully!"
```

Usage:
```bash
./setup-project.sh my-new-project codex
./setup-project.sh another-project "claude,codex,cursor"
```

## Command Reference
- [`spec-kitty init`](../reference/cli-commands.md#spec-kitty-init)
- [`spec-kitty dashboard`](../reference/cli-commands.md#spec-kitty-dashboard)
- [`spec-kitty agent`](../reference/agent-subcommands.md)

## See Also
- [Install Spec Kitty](install-spec-kitty.md)
- [Upgrade to 0.11.0](install-and-upgrade.md)

## Background
- [AI Agent Architecture](../explanation/ai-agent-architecture.md)
- [Execution Lanes](../explanation/execution-lanes.md)
