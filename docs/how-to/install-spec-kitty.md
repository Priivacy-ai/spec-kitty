# Installation Guide

> Spec Kitty is inspired by GitHub's [Spec Kit](https://github.com/github/spec-kit). Installation commands below target the spec-kitty distribution while crediting the original project.

> **📖 Looking for the complete workflow?** See the [README: Getting Started guide](https://github.com/Priivacy-ai/spec-kitty#-getting-started-complete-workflow) for the full lifecycle from CLI installation through feature development and merging.

## Prerequisites

- **Linux/macOS** (or Windows; PowerShell scripts now supported without WSL)
- AI coding agent: [Claude Code](https://www.anthropic.com/claude-code), [GitHub Copilot](https://code.visualstudio.com/), or [Gemini CLI](https://github.com/google-gemini/gemini-cli)
- [uv](https://docs.astral.sh/uv/) for package management
- [Python 3.11+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)

## Installation

### Install Spec Kitty CLI

#### From PyPI (Recommended - Stable Releases)

**Using pip:**
```bash
pip install spec-kitty-cli
```

**Using uv:**
```bash
uv tool install spec-kitty-cli
```

#### From GitHub (Latest Development)

**Using pip:**
```bash
pip install git+https://github.com/Priivacy-ai/spec-kitty.git
```

**Using uv:**
```bash
uv tool install spec-kitty-cli --from git+https://github.com/Priivacy-ai/spec-kitty.git
```

### Initialize a New Project

After installation, initialize a new project:

**If installed globally:**
```bash
spec-kitty init <PROJECT_NAME>
```

**One-time usage (without installing):**

**Using pipx:**
```bash
pipx run spec-kitty-cli init <PROJECT_NAME>
```

**Using uvx:**
```bash
uvx spec-kitty-cli init <PROJECT_NAME>
```

### Add to Existing Project

To add Spec Kitty to an existing project, use the `--here` flag:

```bash
# Navigate to your existing project directory
cd /path/to/existing-project

# Initialize Spec Kitty in the current directory
spec-kitty init .
# or use the --here flag
spec-kitty init --here
```

When adding to an existing project:
- Spec Kitty will **merge** its templates with your existing files
- You'll be prompted to confirm if the directory is not empty
- Use `--force` to skip confirmation: `spec-kitty init --here --force`
- Agent configurations, mission system, and dashboard will be added
- Your existing source code and dependencies are preserved

**Best Practices for Existing Projects:**
1. **Backup first**: Commit your current work to git before adding Spec Kitty
2. **Review .gitignore**: Spec Kitty automatically protects agent directories in `.gitignore`
3. **Team alignment**: Add Spec Kitty to a feature branch before merging to main if you're in a team
4. **Follow the workflow**: After init, run `/spec-kitty.specify` to begin your first feature

### Choose AI Agent

You can proactively specify your AI agent during initialization:

```bash
spec-kitty init <project_name> --ai claude
spec-kitty init <project_name> --ai gemini
spec-kitty init <project_name> --ai copilot
```

### Managing Agents After Initialization

After running `spec-kitty init`, you can add or remove agents at any time using the `spec-kitty agent config` command family.

To manage agents post-init:
- **Add agents**: `spec-kitty agent config add <agents>`
- **Remove agents**: `spec-kitty agent config remove <agents>`
- **Check status**: `spec-kitty agent config status`

See [Managing AI Agents](manage-agents.md) for complete documentation on agent management workflows.

### Cross-Platform Python CLI (v0.10.0+)

As of v0.10.0, all automation uses cross-platform Python CLI commands (`spec-kitty agent`).

The legacy `--script` option is no longer needed - all commands work identically across Windows, macOS, and Linux.

> **Migration Note:** Projects created before v0.10.0 had bash/PowerShell scripts. Run `spec-kitty upgrade` to migrate to Python CLI commands. See [Upgrade to 0.11.0](upgrade-to-0-11-0.md) for details.

### Ignore Agent Tools Check

If you prefer to get the templates without checking for the right tools:

```bash
spec-kitty init <project_name> --ai claude --ignore-agent-tools
```

## Verification

After initialization, you should see the following commands available in your AI agent:
- `/spec-kitty.specify` - Create specifications
- `/spec-kitty.plan` - Generate implementation plans  
- `/spec-kitty.research` - Scaffold mission-specific research artifacts (Phase 0)
- `/spec-kitty.tasks` - Break down into actionable tasks

When you run `/spec-kitty.specify` or `/spec-kitty.plan`, expect the assistant to pause with `WAITING_FOR_DISCOVERY_INPUT` or `WAITING_FOR_PLANNING_INPUT` until you answer its question tables.

## Troubleshooting

### Git Credential Manager on Linux

If you're having issues with Git authentication on Linux, you can install Git Credential Manager:

```bash
#!/usr/bin/env bash
set -e
echo "Downloading Git Credential Manager v2.6.1..."
wget https://github.com/git-ecosystem/git-credential-manager/releases/download/v2.6.1/gcm-linux_amd64.2.6.1.deb
echo "Installing Git Credential Manager..."
sudo dpkg -i gcm-linux_amd64.2.6.1.deb
echo "Configuring Git to use GCM..."
git config --global credential.helper manager
echo "Cleaning up..."
rm gcm-linux_amd64.2.6.1.deb
```

## Command Reference
- [`spec-kitty init`](../reference/cli-commands.md#spec-kitty-init)
- [`spec-kitty upgrade`](../reference/cli-commands.md#spec-kitty-upgrade)

## See Also
- [Non-Interactive Init](non-interactive-init.md)
- [Upgrade to 0.11.0](upgrade-to-0-11-0.md)
- [Use the Dashboard](use-dashboard.md)

## Background
- [Spec-Driven Development](../explanation/spec-driven-development.md)
- [Mission System](../explanation/mission-system.md)
