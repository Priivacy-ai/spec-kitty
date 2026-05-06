<div align="center">
    <img src="https://github.com/Priivacy-ai/spec-kitty/raw/main/media/logo_small.webp" alt="Spec Kitty Logo"/>
    <h1>Spec Kitty</h1>
    <p><strong>Spec-driven development for AI coding agents.</strong></p>
</div>

Spec Kitty is an open-source CLI for turning product intent into a repeatable agent workflow:

```text
spec -> plan -> tasks -> next -> review -> accept -> merge
```

It keeps the important context in your repository, creates work packages that agents can execute, and uses git worktrees so implementation work can happen without constantly switching branches.

[![PyPI version](https://img.shields.io/pypi/v/spec-kitty-cli?style=flat-square&logo=pypi)](https://pypi.org/project/spec-kitty-cli/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue?style=flat-square)](https://www.python.org/downloads/)

## Is It For You?

Use Spec Kitty when:

- AI coding sessions are losing requirements, decisions, or acceptance criteria.
- You want specs, plans, tasks, reviews, and merge state stored in the repo.
- Multiple agents or developers need clear work package boundaries.
- You want a local workflow first, with optional hosted tracker and sync integrations later.

It is probably overkill for one-off edits, tiny scripts, or teams that do not use Git.

## What It Provides

| Need | Spec Kitty provides |
| --- | --- |
| Start from intent | Guided `specify`, `plan`, and `tasks` workflows |
| Keep agents aligned | Repository-native mission artifacts under `kitty-specs/` |
| Split implementation | Work packages with lifecycle lanes such as `planned`, `in_progress`, `for_review`, and `done` |
| Avoid branch chaos | Isolated git worktrees under `.worktrees/` |
| See progress | Optional local kanban dashboard with `spec-kitty dashboard` |
| Integrate agents | Slash commands or skills for common AI coding tools |

## Quick Start

Install the CLI:

```bash
pip install spec-kitty-cli
# or
uv tool install spec-kitty-cli
```

Create or initialize a project:

```bash
spec-kitty init my-project --ai claude
cd my-project
spec-kitty verify-setup
```

Replace `claude` with your agent key when needed. Common choices include `codex`, `cursor`, `gemini`, `copilot`, `opencode`, `qwen`, `windsurf`, `kiro`, and `vibe`.

Open your AI coding agent in the project and run the core workflow:

```text
/spec-kitty.charter
/spec-kitty.specify Build a small task list app.
/spec-kitty.plan
/spec-kitty.tasks
```

Then let the runtime choose the next action until the mission is ready:

```bash
spec-kitty next --agent claude --mission <mission-slug>
```

Review, accept, and merge:

```text
/spec-kitty.review
/spec-kitty.accept
/spec-kitty.merge --push
```

For the full walkthrough, see [Your First Feature](docs/tutorials/your-first-feature.md).

## Everyday Commands

| Command | Purpose |
| --- | --- |
| `spec-kitty init . --ai <agent>` | Add Spec Kitty to the current repo |
| `spec-kitty verify-setup` | Check local installation and project wiring |
| `spec-kitty dashboard` | Open the local mission dashboard |
| `spec-kitty next --agent <agent> --mission <slug>` | Ask Spec Kitty what the agent should do next |
| `spec-kitty upgrade` | Update an existing project after upgrading the CLI |
| `spec-kitty --help` | Show available commands |

## Documentation

Start here:

- [Getting Started](docs/tutorials/getting-started.md)
- [Your First Feature](docs/tutorials/your-first-feature.md)
- [CLI Command Reference](docs/reference/cli-commands.md)
- [Slash Commands](docs/reference/slash-commands.md)
- [Supported Agents](docs/reference/supported-agents.md)
- [Dashboard Guide](docs/how-to/use-dashboard.md)
- [Install and Upgrade](docs/how-to/install-and-upgrade.md)

Deeper topics:

- [Spec-Driven Development](docs/explanation/spec-driven-development.md)
- [Mission System](docs/explanation/mission-system.md)
- [Git Worktrees](docs/explanation/git-worktrees.md)
- [Multi-Agent Orchestration](docs/explanation/multi-agent-orchestration.md)
- [External Orchestrator Runbook](docs/how-to/run-external-orchestrator.md)
- [Hosted Sync Workspaces](docs/how-to/sync-workspaces.md)

## Development

```bash
git clone https://github.com/Priivacy-ai/spec-kitty.git
cd spec-kitty
pip install -e ".[test]"
```

When testing templates from a source checkout:

```bash
export SPEC_KITTY_TEMPLATE_ROOT="$(pwd)"
spec-kitty init my-project --ai claude
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## Support

- Open a [GitHub issue](https://github.com/Priivacy-ai/spec-kitty/issues/new) for bugs, feature requests, or questions.
- See [CHANGELOG.md](CHANGELOG.md) for release notes.
- See [CONTRIBUTORS.md](CONTRIBUTORS.md) and the [GitHub contributors graph](https://github.com/Priivacy-ai/spec-kitty/graphs/contributors) for contributor credits.

## License

Spec Kitty is released under the [MIT License](LICENSE).
