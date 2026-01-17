<div align="center">
    <img src="assets/images/logo_small.webp" alt="Spec Kitty Logo"/>
    <h1>Spec Kitty Documentation</h1>
    <p><strong>Build high-quality software faster with AI-powered spec-driven development.</strong></p>
</div>

---

## What is Spec Kitty?

Spec Kitty is a toolkit for **spec-driven development** with AI coding agents. It structures your AI workflows around specifications, plans, and work packages—ensuring that AI agents build exactly what you need, with live progress tracking via a kanban dashboard.

Works with Claude Code, Cursor, Windsurf, Gemini CLI, GitHub Copilot, and 7 other AI coding agents.

---

## Quick Navigation

### 📚 Tutorials — Learning-Oriented

New to Spec Kitty? Start here to learn the fundamentals.

- [Claude Code Integration](tutorials/claude-code-integration.md) — Setup and first run
- [Claude Code Workflow](tutorials/claude-code-workflow.md) — End-to-end workflow walkthrough

### 🔧 How-To Guides — Task-Oriented

Solve specific problems with step-by-step instructions.

- [Install & Upgrade](how-to/install-spec-kitty.md) — Installation methods and upgrades
- [Use the Dashboard](how-to/use-dashboard.md) — Monitor progress in real-time
- [Upgrade to 0.11.0](how-to/upgrade-to-0-11-0.md) — Migration guide
- [Non-Interactive Init](how-to/non-interactive-init.md) — Run init without prompts

### 📖 Reference — Information-Oriented

Complete command and configuration documentation.

- [CLI Commands](reference/cli-commands.md) — All `spec-kitty` commands
- [Slash Commands](reference/slash-commands.md) — All `/spec-kitty.*` commands
- [Agent Subcommands](reference/agent-subcommands.md) — `spec-kitty agent *` commands
- [Configuration](reference/configuration.md) — Config files and options
- [Environment Variables](reference/environment-variables.md) — All env vars
- [File Structure](reference/file-structure.md) — Directory layout
- [Missions](reference/missions.md) — Mission types and configuration
- [Supported Agents](reference/supported-agents.md) — All 12 supported AI agents

### 💡 Explanations — Understanding-Oriented

Understand the concepts and architecture.

- [Spec-Driven Development](explanation/spec-driven-development.md) — The philosophy
- [Workspace-per-WP Model](explanation/workspace-per-wp.md) — How workspaces work
- [Git Worktrees](explanation/git-worktrees.md) — Git worktrees explained
- [Mission System](explanation/mission-system.md) — Why missions exist
- [Kanban Workflow](explanation/kanban-workflow.md) — Lane-based workflow
- [AI Agent Architecture](explanation/ai-agent-architecture.md) — Multi-agent design

---

## Dashboard Preview

Spec Kitty includes a **live dashboard** for real-time progress tracking:

<div align="center">
  <img src="assets/images/dashboard-kanban.png" alt="Spec Kitty Dashboard - Kanban Board View" width="800"/>
  <p><em>Kanban board showing work packages across all lanes</em></p>
</div>

<div align="center">
  <img src="assets/images/dashboard-overview.png" alt="Spec Kitty Dashboard - Feature Overview" width="800"/>
  <p><em>Feature overview with completion metrics</em></p>
</div>


## Quick Start

```bash
# Install
pip install spec-kitty-cli

# Initialize a new project
spec-kitty init my-project --ai claude
cd my-project

# Launch your AI agent and use slash commands
/spec-kitty.specify Add user authentication with email/password
/spec-kitty.plan
/spec-kitty.tasks
/spec-kitty.implement
```

**Ready to start?** [Getting Started Tutorial →](tutorials/getting-started.md)

---

## Support

- **Issues**: [GitHub Issues](https://github.com/Priivacy-ai/spec-kitty/issues)
- **Discussions**: [GitHub Issues](https://github.com/Priivacy-ai/spec-kitty/issues)
