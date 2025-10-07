# Installation Guide

> Spec Kitty is a community-maintained fork of GitHub's [Spec Kit](https://github.com/github/spec-kit). Installation commands below target the spec-kitty distribution while crediting the original project.

## Prerequisites

- **Linux/macOS** (or Windows; PowerShell scripts now supported without WSL)
- AI coding agent: [Claude Code](https://www.anthropic.com/claude-code), [GitHub Copilot](https://code.visualstudio.com/), or [Gemini CLI](https://github.com/google-gemini/gemini-cli)
- [uv](https://docs.astral.sh/uv/) for package management
- [Python 3.11+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)

## Installation

### Initialize a New Project

The easiest way to get started is to initialize a new project:

```bash
uvx --from . speckitty init <PROJECT_NAME>
```

Or initialize in the current directory:

```bash
uvx --from . speckitty init .
# or use the --here flag
uvx --from . speckitty init --here
```

> Run these commands from the Spec Kitty repository root so `.` resolves to this checkout.

### Choose AI Agent

You can proactively specify your AI agent during initialization:

```bash
uvx --from . speckitty init <project_name> --ai claude
uvx --from . speckitty init <project_name> --ai gemini
uvx --from . speckitty init <project_name> --ai copilot
```

### Choose Script Type (Shell vs PowerShell)

All automation scripts now have both Bash (`.sh`) and PowerShell (`.ps1`) variants.

Auto behavior:
- Windows default: `ps`
- Other OS default: `sh`
- Interactive mode: you'll be prompted unless you pass `--script`

Force a specific script type:
```bash
uvx --from . speckitty init <project_name> --script sh
uvx --from . speckitty init <project_name> --script ps
```

### Ignore Agent Tools Check

If you prefer to get the templates without checking for the right tools:

```bash
uvx --from . speckitty init <project_name> --ai claude --ignore-agent-tools
```

## Verification

After initialization, you should see the following commands available in your AI agent:
- `/speckitty.specify` - Create specifications
- `/speckitty.plan` - Generate implementation plans  
- `/speckitty.tasks` - Break down into actionable tasks

When you run `/speckitty.specify` or `/speckitty.plan`, expect the assistant to pause with `WAITING_FOR_DISCOVERY_INPUT` or `WAITING_FOR_PLANNING_INPUT` until you answer its question tables.

The `.specify/scripts` directory will contain both `.sh` and `.ps1` scripts.

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
