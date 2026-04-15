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

### Add to an Existing Project

To add Spec Kitty to an existing repository, run `init` from that repository root:

```bash
cd /path/to/existing-project
spec-kitty init . --ai claude
```

What this does today:
- Creates the `.kittify/` scaffold in the current directory
- Adds the selected agent command directories
- Updates ignore files such as `.gitignore` / `.claudeignore`
- Leaves your Git history untouched; `init` does not initialize Git or create commits

**Best practices for existing projects:**
1. Commit or stash your current work before adding Spec Kitty.
2. Review `.gitignore` after init so agent directories remain untracked.
3. Use `spec-kitty verify-setup --diagnostics` if you want a post-install health check.
4. Start the workflow with `/spec-kitty.specify`; mission selection happens there, not during `init`.

### Choose AI Agent

You can proactively specify your AI agent during initialization:

```bash
spec-kitty init <project_name> --ai claude
spec-kitty init <project_name> --ai gemini
spec-kitty init <project_name> --ai codex
spec-kitty init <project_name> --ai claude,codex
```

### Managing Agents After Initialization

After running `spec-kitty init`, you can add or remove agents at any time using the `spec-kitty agent config` command family.

To manage agents post-init:
- **Add agents**: `spec-kitty agent config add <agents>`
- **Remove agents**: `spec-kitty agent config remove <agents>`
- **Check status**: `spec-kitty agent config status`

See [Managing AI Agents](manage-agents.md) for complete documentation on agent management workflows.

### Non-Interactive Setup

For CI or scripts, use the non-interactive mode documented by `spec-kitty init --help`:

```bash
spec-kitty init <project_name> --ai claude --non-interactive
```

## Verification

After initialization, you should see the following commands available in your AI agent:
- `/spec-kitty.specify` - Create specifications
- `/spec-kitty.plan` - Generate implementation plans  
- `/spec-kitty.research` - Scaffold mission-specific research artifacts (Phase 0)
- `/spec-kitty.tasks` - Break down into actionable tasks

Run `spec-kitty dashboard --open` if you want the live dashboard immediately after setup.

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
- [`spec-kitty verify-setup`](../reference/cli-commands.md#spec-kitty-verify-setup)

## See Also

- [Non-Interactive Init](non-interactive-init.md)
- [Upgrade to 0.11.0](install-and-upgrade.md)
- [Use the Dashboard](use-dashboard.md)

## Background

- [Spec-Driven Development](../explanation/spec-driven-development.md)
- [Mission System](../explanation/mission-system.md)
