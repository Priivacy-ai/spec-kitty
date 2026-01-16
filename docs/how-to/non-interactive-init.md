# Non-Interactive Init Mode

## Summary

✅ **spec-kitty init IS fully non-interactive** when all required options are provided via command-line arguments.

## Complete Non-Interactive Syntax

```bash
spec-kitty init <project-name> \
  --ai <agents> \
  --script <type> \
  --mission <mission> \
  [--force] \
  [--no-git] \
  [--ignore-agent-tools]
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
# or
spec-kitty init --here
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

### 3. Script Type (`--script`)

**Valid values**: `sh` or `ps`

```bash
--script sh   # POSIX shell (bash/zsh) - for Mac/Linux
--script ps   # PowerShell - for Windows
```

**Auto-detection**: If omitted and not TTY:
- Windows → `ps`
- Mac/Linux → `sh`

### 4. Mission (`--mission`)

**Valid values**: `software-dev` or `research`

```bash
--mission software-dev   # Software Dev Kitty (default)
--mission research       # Deep Research Kitty
```

**Auto-selection**: If omitted and not TTY, defaults to `software-dev`

## Optional Flags

| Flag | Purpose | Default |
|------|---------|---------|
| `--force` | Skip confirmation when directory not empty | Off (will prompt) |
| `--no-git` | Skip git repository initialization | Off (initializes git) |
| `--ignore-agent-tools` | Skip verification that agent CLIs are installed | Off (checks tools) |
| `--skip-tls` | Skip SSL/TLS verification (not recommended) | Off |
| `--debug` | Show verbose diagnostic output | Off |
| `--github-token` | GitHub API token for template download | Uses GH_TOKEN env var |

## Complete Non-Interactive Examples

### Example 1: New project with Codex
```bash
spec-kitty init my-project \
  --ai codex \
  --script sh \
  --mission software-dev
```

### Example 2: Current directory with multiple agents
```bash
spec-kitty init . \
  --ai claude,codex,cursor \
  --script sh \
  --mission research \
  --force
```

### Example 3: Current directory (--here syntax)
```bash
spec-kitty init --here \
  --ai windsurf \
  --script sh \
  --mission software-dev \
  --force
```

### Example 4: Minimal (relies on defaults)
```bash
# In non-interactive environment (CI/CD):
spec-kitty init my-project --ai codex
# Auto-selects: --script sh (or ps on Windows), --mission software-dev
```

### Example 5: CI/CD friendly
```bash
spec-kitty init . \
  --ai claude \
  --script sh \
  --mission software-dev \
  --force \
  --ignore-agent-tools \
  --no-git
```

### Example 6: All 12 agents
```bash
spec-kitty init my-project \
  --ai codex,claude,gemini,cursor,qwen,opencode,windsurf,kilocode,auggie,roo,copilot,q \
  --script sh \
  --mission software-dev
```

## Interactive vs Non-Interactive Behavior

### Interactive Mode (Default)

Triggered when:
- Running from a terminal (TTY)
- Missing `--ai`, `--script`, or `--mission` options

Presents:
- Multi-select menu for AI assistants (space to select, enter to confirm)
- Arrow selection for script type
- Arrow selection for mission
- Confirmation prompt if directory not empty (unless `--force`)

### Non-Interactive Mode

Triggered when:
- All required options provided via flags
- OR running in non-TTY environment (pipes, CI/CD, scripts)

Behavior:
- Uses provided values
- Falls back to defaults for omitted options
- No prompts (unless `--force` missing and dir not empty)
- Suitable for automation

## CI/CD Usage

```yaml
# GitHub Actions example
- name: Initialize Spec Kitty
  run: |
    spec-kitty init . \
      --ai codex \
      --script sh \
      --mission software-dev \
      --force \
      --no-git
```

```bash
# Docker/script example
#!/bin/bash
spec-kitty init /app/project \
  --ai claude,codex \
  --script sh \
  --mission software-dev \
  --ignore-agent-tools
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
- `.kittify/memory/` (for constitution, etc.)

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
**Recommended**: Edit `.kittify/AGENTS.md` and run `spec-kitty init --here --force` to refresh

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

### "Invalid script type"
```bash
# ERROR
spec-kitty init proj --script bash

# CORRECT
spec-kitty init proj --script sh
```

Valid values: `sh` or `ps`

### "Invalid mission"
```bash
# ERROR
spec-kitty init proj --mission dev

# CORRECT
spec-kitty init proj --mission software-dev
```

Valid values: `software-dev` or `research`

### "Do you want to continue?" prompt appears

This happens when initializing in non-empty directory without `--force`:

```bash
# Add --force to skip prompt
spec-kitty init . --ai codex --force
```

## Complete Reference

### Minimal Non-Interactive Init
```bash
spec-kitty init my-project --ai codex
```

### Maximum Options
```bash
spec-kitty init my-project \
  --ai codex,claude,cursor \
  --script sh \
  --mission research \
  --force \
  --no-git \
  --ignore-agent-tools \
  --debug
```

### Current Directory
```bash
spec-kitty init . --ai codex --force
# or
spec-kitty init --here --ai codex --force
```

## Environment Variables

Can also be set via environment:
- `GH_TOKEN` or `GITHUB_TOKEN` - GitHub API token (instead of `--github-token`)
- `SPECIFY_TEMPLATE_REPO` - Override template source (e.g., `myorg/custom-templates`)

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid args, missing tools, directory conflict, etc.) |

Use in scripts:
```bash
if spec-kitty init my-project --ai codex --script sh; then
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
  --script sh \
  --mission software-dev \
  --ignore-agent-tools || exit 1

cd "$PROJECT_NAME"
echo "Project initialized successfully!"
```

Usage:
```bash
./setup-project.sh my-new-project codex
./setup-project.sh another-project "claude,codex,cursor"
```
