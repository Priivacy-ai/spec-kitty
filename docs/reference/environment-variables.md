# Environment Variables Reference

This document lists all environment variables used by Spec Kitty.

---

## Feature Detection

### SPECIFY_FEATURE

Override automatic feature detection.

**Purpose**: Force Spec Kitty to use a specific feature when automatic detection fails (e.g., in non-Git repositories or CI environments).

**Example**:

```bash
export SPECIFY_FEATURE=014-comprehensive-docs
spec-kitty agent tasks status
```

**When to use**:

- Running commands outside a Git repository
- CI/CD pipelines where Git context is unavailable
- Testing with a specific feature

---

## Template Customization

### SPEC_KITTY_TEMPLATE_ROOT

Use local templates instead of fetching from GitHub.

**Purpose**: Point to a local directory containing Spec Kitty templates. Useful for template development or air-gapped environments.

**Example**:

```bash
export SPEC_KITTY_TEMPLATE_ROOT=/path/to/spec-kitty/src/specify_cli/templates
spec-kitty init my-project --ai claude
```

**When to use**:

- Developing or testing template changes
- Environments without internet access
- Custom template workflows

### SPECIFY_TEMPLATE_REPO

Override the GitHub repository for templates.

**Purpose**: Fetch templates from a different GitHub repository instead of the default.

**Example**:

```bash
export SPECIFY_TEMPLATE_REPO=my-org/custom-spec-kitty-templates
spec-kitty upgrade
```

**When to use**:

- Organizations with custom templates
- Forked template repositories
- Enterprise GitHub instances

---

## Agent Configuration

### CODEX_HOME

Configure GitHub Codex CLI to find project prompts.

**Purpose**: Point the Codex CLI to the project's `.codex/` directory for slash commands.

**Example**:

```bash
export CODEX_HOME="$(pwd)/.codex"
codex
```

**When to use**:

- Using GitHub Codex as your AI agent
- Codex can't find slash commands automatically

---

## GitHub Integration

### GH_TOKEN / GITHUB_TOKEN

Authenticate with GitHub API.

**Purpose**: Required for operations that use the GitHub API, such as fetching templates or creating pull requests.

**Example**:

```bash
export GH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
spec-kitty init my-project
```

**Precedence**: `GH_TOKEN` takes precedence if both are set.

**When to use**:

- CI/CD pipelines
- Automated workflows
- Rate-limited environments (authenticated requests have higher limits)

---

## Debug and Development

### SPEC_KITTY_DEBUG

Enable debug logging.

**Purpose**: Output verbose debug information for troubleshooting.

**Example**:

```bash
export SPEC_KITTY_DEBUG=1
spec-kitty agent tasks status
```

**When to use**:

- Troubleshooting unexpected behavior
- Reporting bugs
- Understanding internal operations

### SPEC_KITTY_NO_COLOR

Disable colored output.

**Purpose**: Remove ANSI color codes from terminal output.

**Example**:

```bash
export SPEC_KITTY_NO_COLOR=1
spec-kitty agent tasks status
```

**When to use**:

- CI/CD logs that don't support colors
- Piping output to files
- Accessibility needs

### SPEC_KITTY_NON_INTERACTIVE

Force non-interactive mode for CLI commands that normally prompt.

**Purpose**: Disable prompts and arrow-key menus (useful for CI/CD).

**Example**:

```bash
export SPEC_KITTY_NON_INTERACTIVE=1
spec-kitty init my-project --ai codex --non-interactive
```

**When to use**:

- CI/CD pipelines
- Headless scripts
- Non-TTY automation

---

## Summary Table

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| `SPECIFY_FEATURE` | Override feature detection | `014-my-feature` |
| `SPEC_KITTY_TEMPLATE_ROOT` | Local template path | `/path/to/templates` |
| `SPECIFY_TEMPLATE_REPO` | Custom template repo | `org/templates` |
| `CODEX_HOME` | Codex CLI prompt path | `$(pwd)/.codex` |
| `GH_TOKEN` | GitHub authentication | `ghp_xxx...` |
| `GITHUB_TOKEN` | GitHub authentication (alt) | `ghp_xxx...` |
| `SPEC_KITTY_DEBUG` | Enable debug output | `1` |
| `SPEC_KITTY_NO_COLOR` | Disable colors | `1` |
| `SPEC_KITTY_NON_INTERACTIVE` | Disable prompts | `1` |

---

## See Also

- [Configuration](configuration.md) — Configuration file reference
- [CLI Commands](cli-commands.md) — Command line reference
- [Non-Interactive Init](../how-to/non-interactive-init.md) — Common automation patterns

## Getting Started

- [Claude Code Workflow](../tutorials/claude-code-workflow.md)

## Practical Usage

- [Non-Interactive Init](../how-to/non-interactive-init.md)
- [Install Spec Kitty](../how-to/install-spec-kitty.md)
