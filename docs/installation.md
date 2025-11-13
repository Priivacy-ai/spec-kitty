# Installation Guide

> Spec Kitty is a community-maintained fork of GitHub's [Spec Kit](https://github.com/github/spec-kit). Installation commands below target the spec-kitty distribution while crediting the original project.

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

Or initialize in the current directory:

```bash
spec-kitty init .
# or use the --here flag
spec-kitty init --here
```

### Choose AI Agent

You can proactively specify your AI agent during initialization:

```bash
spec-kitty init <project_name> --ai claude
spec-kitty init <project_name> --ai gemini
spec-kitty init <project_name> --ai copilot
```

### Choose Script Type (Shell vs PowerShell)

All automation scripts now have both Bash (`.sh`) and PowerShell (`.ps1`) variants.

Auto behavior:
- Windows default: `ps`
- Other OS default: `sh`
- Interactive mode: you'll be prompted unless you pass `--script`

Force a specific script type:
```bash
spec-kitty init <project_name> --script sh
spec-kitty init <project_name> --script ps
```

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

The `.kittify/scripts` directory will contain both `.sh` and `.ps1` scripts.

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
