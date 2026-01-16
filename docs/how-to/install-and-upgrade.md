# How to Install and Upgrade Spec Kitty

Use this guide to install the Spec Kitty CLI and upgrade existing projects.

## Install from PyPI

```bash
pip install spec-kitty-cli
```

```bash
uv tool install spec-kitty-cli
```

## Install from GitHub

```bash
pip install git+https://github.com/Priivacy-ai/spec-kitty.git
```

```bash
uv tool install spec-kitty-cli --from git+https://github.com/Priivacy-ai/spec-kitty.git
```

## One-Time Usage

```bash
pipx run spec-kitty-cli init <PROJECT_NAME>
```

```bash
uvx spec-kitty-cli init <PROJECT_NAME>
```

## Upgrade Existing Projects

Run upgrades from the project root so templates and automation stay in sync.

```bash
cd /path/to/project
spec-kitty upgrade
```

Preview changes before applying them:

```bash
spec-kitty upgrade --dry-run
```

## Verify Installation

```bash
spec-kitty --version
```

---

## Command Reference

- [CLI Commands](../reference/cli-commands.md) - Full `spec-kitty` command reference
- [Environment Variables](../reference/environment-variables.md) - Configuration options

## See Also

- [Upgrade to 0.11.0](upgrade-to-0-11-0.md) - Breaking changes in v0.11.0
- [Non-Interactive Init](non-interactive-init.md) - Scripted project setup

## Background

- [Spec-Driven Development](../explanation/spec-driven-development.md) - Why Spec Kitty exists

## Getting Started

- [Getting Started Tutorial](../tutorials/getting-started.md) - First-time walkthrough
