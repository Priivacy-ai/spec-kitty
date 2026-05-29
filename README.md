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
| Split implementation | Work packages with lifecycle lanes such as `planned`, `in_progress`, `for_review`, `approved`, and `done` |
| Avoid branch chaos | Isolated git worktrees under `.worktrees/` |
| See progress | Optional local kanban dashboard with `spec-kitty dashboard` |
| Integrate agents | Slash commands or skills for common AI coding tools |
| Learn from missions | Every completed mission generates a retrospective by default. Tune via `.kittify/config.yaml#retrospective` or charter; see [how-to](docs/how-to/use-retrospective-learning.md). |

## Governance layer

Spec Kitty keeps runtime governance in the repo instead of treating it as
agent-only prompt text. The trail model in [docs/trail-model.md](docs/trail-model.md)
describes how `spec-kitty advise`, `spec-kitty ask`, and `spec-kitty do` map
operator intent to runtime behavior, while
[docs/host-surface-parity.md](docs/host-surface-parity.md) tracks parity across
CLI, slash-command, and hosted surfaces.

## Quick Start

Install the CLI:

```bash
pipx install spec-kitty-cli
```

`pipx` is the preferred installer for the CLI because it keeps Spec Kitty in its
own virtual environment and avoids the `externally-managed-environment` errors
common on modern Linux distributions.

Other supported install methods:

```bash
uv tool install spec-kitty-cli
# or, inside an activated virtual environment
python -m pip install spec-kitty-cli
```

Create or initialize a project:

```bash
spec-kitty init my-project --ai claude
cd my-project
spec-kitty verify-setup
```

Replace `claude` with your agent key when needed. Common choices include `codex`, `cursor`, `gemini`, `copilot`, `opencode`, `qwen`, `windsurf`, `kiro`, `vibe`, `pi`, and `letta`.

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

Review, accept, merge, and close the loop:

```text
/spec-kitty.review
/spec-kitty.accept
/spec-kitty.merge --push
```

After merge, run `/spec-kitty-mission-review`. The mission's
`retrospective.yaml` is authored during the runtime terminus (HiC prompt or
autonomous facilitator), not by `merge`. Once it exists, use
`spec-kitty retrospect summary` for the cross-mission view and
`spec-kitty agent retrospect synthesize --mission <mission-slug>` to apply any
staged proposals (dry-run by default — pass `--apply` to mutate).

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
- [Orchestrator Quickstart](docs/tutorials/orchestrator-quickstart.md)
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

Hosted auth, sync, and tracker flows remain opt-in today. Internal /
pre-launch operators dogfooding the hidden hosted-readiness mode behind
`SPEC_KITTY_ENABLE_SAAS_SYNC=1` should read
[Internal Hosted-Readiness (Pre-Launch)](docs/how-to/internal-hosted-readiness.md).
The launch-day behavior that will replace today's defaults is staged
under [Launch-Readiness Behavior (Coming Soon)](docs/explanation/launch-readiness-future.md).

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

## Identity-Boundary CI Gate

The `drift-detector` required check runs
`tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition` on every PR
against `main`. It catches drift between the canonical registries in this
repo and the consumer-recognition contract that
`spec-kitty-end-to-end-testing#41` closed over an 8-RC peeling cycle
(rc14 → rc22). Workflow file:
[`.github/workflows/drift-detector.yml`](.github/workflows/drift-detector.yml).

This is one of three coordinated CI gates tracked under
[`#1247`](https://github.com/Priivacy-ai/spec-kitty/issues/1247):

- `drift-detector` here (this repo).
- `cross-repo-harness-tests` in [`spec-kitty-events`](https://github.com/Priivacy-ai/spec-kitty-events) — workflow `.github/workflows/cross-repo-harness-tests.yml`.
- `identity-boundary-canary` in [`spec-kitty-saas`](https://github.com/Priivacy-ai/spec-kitty-saas) — workflow `.github/workflows/canary-gate.yml`.

This repo's drift-detector pins no external SHA — it only runs an in-repo
test. The sibling repos' workflows pin a specific commit of
`Priivacy-ai/spec-kitty-end-to-end-testing`; see each sibling's README
"Identity-Boundary CI Gate" section for the SHA-bump procedure.

**Admin action required (one-time per repo)**: after this gate merges, a
repo admin must register the check as required on `main`:

1. Open https://github.com/Priivacy-ai/spec-kitty/settings/branches.
2. Edit the rule for `main`.
3. Under "Require status checks to pass before merging", add the exact
   name `drift-detector`.
4. Save.

Until that step is done, the workflow still runs on every PR but its
red status does not block merge.

## Support

- Open a [GitHub issue](https://github.com/Priivacy-ai/spec-kitty/issues/new) for bugs, feature requests, or questions.
- See [CHANGELOG.md](CHANGELOG.md) for release notes.
- See [CONTRIBUTORS.md](CONTRIBUTORS.md) and the [GitHub contributors graph](https://github.com/Priivacy-ai/spec-kitty/graphs/contributors) for contributor credits.

## License

Spec Kitty is released under the [MIT License](LICENSE).
