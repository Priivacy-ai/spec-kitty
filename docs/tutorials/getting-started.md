# Getting Started with Spec Kitty

**Divio type**: Tutorial

In this tutorial, you'll install Spec Kitty and create your first feature specification.

**Time**: ~30 minutes
**Prerequisites**: Python 3.11+, Git, an AI coding agent (Claude Code, Cursor, Gemini CLI, etc.)


## Step 1: Install Spec Kitty

Choose one install method:

```bash
pip install spec-kitty-cli
```

```bash
uv tool install spec-kitty-cli
```

Verify the CLI is available:

```bash
spec-kitty --version
```

Expected output (abridged):

```
Spec Kitty ... v0.11.0
```

## Step 2: Initialize a Project

Create a new project directory with the agent you plan to use:

```bash
spec-kitty init my-spec-project --ai claude
cd my-spec-project
```

Expected output (abridged):

```
OK Initialized Spec Kitty project
OK Generated agent commands in .claude/
```

Tip: Use `spec-kitty init --here --ai claude` to initialize the current folder.

## Step 3: Create Your First Specification

Open your AI agent in this repository and run the `specify` command.

In your agent:

```text
/spec-kitty.specify Build a tiny command-line task list app.
```

You'll be asked a discovery interview. Answer each question until the command completes.

Expected results:

- `kitty-specs/###-task-list/spec.md` (feature spec)
- A git commit in `main` with the spec changes

## Step 4: Verify Your Work

Confirm the feature directory exists:

```bash
ls kitty-specs
```

Example output:

```
###-task-list
```

If the command created a new worktree later in the workflow, it will appear here:

```bash
ls .worktrees
```

## Troubleshooting

- **`spec-kitty: command not found`**: Reopen your shell or reinstall via `pipx` or `uv`. Then rerun `spec-kitty --version`.
- **No `/spec-kitty.specify` command available**: Re-run `spec-kitty init --ai <your-agent>` or use `spec-kitty agent context update-context` to refresh agent context.
- **`WAITING_FOR_DISCOVERY_INPUT`**: The command is paused for your answers; provide the requested details and continue.

## What's Next?

Continue with [Your First Feature](your-first-feature.md) for the complete workflow from specification to merge.

### Related How-To Guides

- [Install and Upgrade](../how-to/install-and-upgrade.md) - Additional installation options
- [Create a Specification](../how-to/create-specification.md) - Deep dive into `/spec-kitty.specify`
- [Non-Interactive Init](../how-to/non-interactive-init.md) - Scripted project setup

### Reference Documentation

- [CLI Commands](../reference/cli-commands.md) - Full command reference
- [Slash Commands](../reference/slash-commands.md) - AI agent slash commands
- [Supported Agents](../reference/supported-agents.md) - All 12 supported AI agents

### Learn More

- [Spec-Driven Development](../explanation/spec-driven-development.md) - Why specs matter
- [Mission System](../explanation/mission-system.md) - How missions shape workflows
