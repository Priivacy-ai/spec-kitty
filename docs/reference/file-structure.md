# File Structure Reference

This document describes the complete directory structure of a Spec Kitty project.

---

## Project Root Overview

```
my-project/
├── .kittify/              # Spec Kitty configuration and templates
├── kitty-specs/           # Feature specifications
├── .worktrees/            # Git worktrees for execution workspaces (lane-based in 2.x)
├── .claude/               # Claude Code slash commands
├── .cursor/               # Cursor slash commands
├── .gemini/               # Gemini CLI slash commands
├── (other agent dirs)     # Other AI agent directories
├── docs/                  # Project documentation
├── src/                   # Your source code
└── .git/                  # Git repository
```

---

## .kittify/ Directory

Contains Spec Kitty configuration, templates, and project memory.

```
.kittify/
├── templates/                    # Document templates
│   ├── spec-template.md          # Specification template
│   ├── plan-template.md          # Plan template
│   ├── tasks-template.md         # Tasks breakdown template
│   └── task-prompt-template.md   # Individual WP prompt template
├── missions/                     # Mission configurations
│   ├── software-dev/
│   │   └── mission.yaml
│   ├── research/
│   │   └── mission.yaml
│   └── documentation/
│       └── mission.yaml
└── memory/                       # Project memory
    └── charter.md           # Project principles (optional)
```

### Key Files

| File | Purpose |
|------|---------|
| `templates/*.md` | Templates used by `/spec-kitty.specify`, `/spec-kitty.plan`, etc. |
| `missions/*/mission.yaml` | Mission-specific configuration and phases |
| `memory/charter.md` | Project-wide principles referenced by all commands |

---

## kitty-specs/ Directory

Contains all feature specifications. Each feature has its own subdirectory.

```
kitty-specs/
├── 001-user-authentication/      # First feature
│   ├── meta.json                 # Feature metadata
│   ├── spec.md                   # Specification document
│   ├── plan.md                   # Implementation plan
│   ├── research.md               # Research findings (optional)
│   ├── tasks.md                  # Task breakdown
│   ├── data-model.md             # Data model (software-dev)
│   ├── checklists/               # Validation checklists
│   │   └── requirements.md
│   └── tasks/                    # Work package prompts
│       ├── WP01-setup.md
│       ├── WP02-api.md
│       └── WP03-frontend.md
├── 002-payment-processing/       # Second feature
│   └── ...
└── 014-documentation/            # Feature 014
    └── ...
```

### Feature Directory Contents

| File/Directory | Created By | Purpose |
|----------------|------------|---------|
| `meta.json` | `/spec-kitty.specify` | Feature metadata and mission |
| `spec.md` | `/spec-kitty.specify` | User stories, requirements, acceptance criteria |
| `plan.md` | `/spec-kitty.plan` | Architecture, design decisions, implementation approach |
| `research.md` | `/spec-kitty.research` | Research findings and evidence (optional) |
| `tasks.md` | `/spec-kitty.tasks` | Task breakdown with WP groupings |
| `data-model.md` | `/spec-kitty.plan` | Database schema (software-dev mission) |
| `checklists/` | `/spec-kitty.checklist` | Validation checklists |
| `tasks/` | `/spec-kitty.tasks` | Individual WP prompt files |

---

## .worktrees/ Directory (0.11.0+)

Contains Git worktrees for implementation. Features create one shared workspace per execution lane.

```
.worktrees/
├── 014-documentation-lane-a/     # Lane A workspace (shared by sequential WPs)
│   ├── src/                      # Code (on lane branch)
│   ├── docs/                     # Documentation
│   └── .git                      # Pointer to main .git
├── 014-documentation-lane-b/     # Parallel lane workspace
│   └── ...
```

### Key Points

- Features create **one worktree per execution lane**
- Each lane worktree has its own branch: `<feature-slug>-lane-<id>`
- Worktrees share the `.git` database with the repository root checkout
- Created by `spec-kitty implement WP##`
- Removed after merge with `git worktree remove`

### Worktree vs Repository Root Checkout

| Location | When to Use |
|----------|-------------|
| Repository root checkout (`my-project/`) | Planning: `/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.tasks` |
| Worktree (`.worktrees/...`) | Implementation: `/spec-kitty.implement`, coding, testing in the resolved execution workspace |

---

## VCS Directories

Spec Kitty uses Git as the version control backend.

### .git/ Directory

Standard Git repository directory.

```
.git/
├── config         # Repository configuration
├── HEAD           # Current branch reference
├── objects/       # Git object database
├── refs/          # Branch and tag references
└── worktrees/     # Git worktree info (managed internally)
```

---

## Agent Directories

Each supported AI agent has its own directory for slash commands.

```
my-project/
├── .claude/
│   └── commands/
│       ├── spec-kitty.specify.md
│       ├── spec-kitty.plan.md
│       ├── spec-kitty.tasks.md
│       ├── spec-kitty.implement.md
│       ├── spec-kitty.review.md
│       ├── spec-kitty.accept.md
│       ├── spec-kitty.merge.md
│       ├── spec-kitty.status.md
│       ├── spec-kitty.dashboard.md
│       ├── spec-kitty.charter.md
│       ├── spec-kitty.research.md
│       ├── spec-kitty.checklist.md
│       └── spec-kitty.analyze.md
├── .cursor/
│   └── commands/
│       └── (same files)
├── .gemini/
│   └── commands/
│       └── (same files)
└── (10 more agent directories)
```

See [Supported Agents](supported-agents.md) for the complete list.

---

## docs/ Directory (Divio Structure)

Documentation organized by the Divio 4-type system.

```
docs/
├── index.md                      # Landing page
├── toc.yml                       # Navigation structure
├── docfx.json                    # Build configuration
├── tutorials/                    # Learning-oriented
│   ├── getting-started.md
│   └── your-first-feature.md
├── how-to/                       # Task-oriented
│   ├── install-spec-kitty.md
│   ├── create-specification.md
│   └── implement-work-package.md
├── reference/                    # Information-oriented
│   ├── cli-commands.md
│   ├── slash-commands.md
│   └── configuration.md
├── explanation/                  # Understanding-oriented
│   ├── spec-driven-development.md
│   └── execution-lanes.md
└── assets/
    ├── images/
    └── css/
```

---

## Complete Example

Here's a complete project structure with one active feature:

```
my-project/
├── .git/                            # Git repository
├── .gitignore
├── .kittify/
│   ├── templates/
│   │   ├── spec-template.md
│   │   ├── plan-template.md
│   │   ├── tasks-template.md
│   │   └── task-prompt-template.md
│   ├── missions/
│   │   ├── software-dev/
│   │   ├── research/
│   │   └── documentation/
│   └── memory/
│       └── charter.md
├── .claude/
│   └── commands/
│       └── (13 slash command files)
├── kitty-specs/
│   └── 001-auth-system/
│       ├── meta.json
│       ├── spec.md
│       ├── plan.md
│       ├── tasks.md
│       └── tasks/
│           ├── WP01-setup.md
│           ├── WP02-api.md
│           └── WP03-ui.md
├── .worktrees/
│   ├── 001-auth-system-lane-a/
│   └── 001-auth-system-lane-b/
├── docs/
│   └── (documentation)
├── src/
│   └── (source code)
├── tests/
│   └── (test files)
├── pyproject.toml
└── README.md
```

---

## See Also

- [Configuration](configuration.md) — Configuration file formats
- [Execution Lanes](../explanation/execution-lanes.md) — How worktrees work
- [Git Worktrees](../explanation/git-worktrees.md) — Git worktrees explained

## Getting Started
- [Claude Code Integration](../tutorials/claude-code-integration.md)

## Practical Usage
- [Install Spec Kitty](../how-to/install-spec-kitty.md)
- [Upgrade to 0.11.0](../how-to/install-and-upgrade.md)
