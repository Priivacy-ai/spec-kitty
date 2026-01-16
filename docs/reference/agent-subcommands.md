# Agent Subcommand Reference

The `spec-kitty agent` commands are designed for AI agents and automation tooling. They generally emit JSON and update task metadata or feature artifacts directly.

## spec-kitty agent

**Synopsis**: `spec-kitty agent [OPTIONS] COMMAND [ARGS]...`

**Description**: Commands for AI agents to execute spec-kitty workflows programmatically.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

---

## spec-kitty agent feature

**Synopsis**: `spec-kitty agent feature [OPTIONS] COMMAND [ARGS]...`

**Description**: Feature lifecycle commands for AI agents.

**Subcommands**:
- `create-feature`
- `check-prerequisites`
- `setup-plan`
- `accept`
- `merge`
- `finalize-tasks`

### spec-kitty agent feature create-feature

**Synopsis**: `spec-kitty agent feature create-feature [OPTIONS] FEATURE_SLUG`

**Description**: Create new feature directory structure in main repository.

**Arguments**:
- `FEATURE_SLUG`: Feature slug (e.g., `user-auth`) [required]

**Options**:
| Flag | Description |
| --- | --- |
| `--json` | Output JSON format |
| `--help` | Show this message and exit |

**Example**:
```bash
spec-kitty agent feature create-feature "new-dashboard" --json
```

### spec-kitty agent feature check-prerequisites

**Synopsis**: `spec-kitty agent feature check-prerequisites [OPTIONS]`

**Description**: Validate feature structure and prerequisites.

**Options**:
| Flag | Description |
| --- | --- |
| `--json` | Output JSON format |
| `--paths-only` | Only output path variables |
| `--include-tasks` | Include tasks.md in validation |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent feature check-prerequisites --json
spec-kitty agent feature check-prerequisites --paths-only --json
```

### spec-kitty agent feature setup-plan

**Synopsis**: `spec-kitty agent feature setup-plan [OPTIONS]`

**Description**: Scaffold implementation plan template in main repository.

**Options**:
| Flag | Description |
| --- | --- |
| `--json` | Output JSON format |
| `--help` | Show this message and exit |

**Example**:
```bash
spec-kitty agent feature setup-plan --json
```

### spec-kitty agent feature accept

**Synopsis**: `spec-kitty agent feature accept [OPTIONS]`

**Description**: Perform feature acceptance workflow.

**Options**:
| Flag | Description |
| --- | --- |
| `--feature TEXT` | Feature directory slug (auto-detected if not specified) |
| `--mode TEXT` | Acceptance mode: `auto`, `pr`, `local`, `checklist` (default: `auto`) |
| `--json` | Output results as JSON for agent parsing |
| `--lenient` | Skip strict metadata validation |
| `--no-commit` | Skip auto-commit (report only) |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent feature accept
spec-kitty agent feature accept --json
spec-kitty agent feature accept --lenient --json
```

### spec-kitty agent feature merge

**Synopsis**: `spec-kitty agent feature merge [OPTIONS]`

**Description**: Merge feature branch into target branch.

**Options**:
| Flag | Description |
| --- | --- |
| `--feature TEXT` | Feature directory slug (auto-detected if not specified) |
| `--target TEXT` | Target branch to merge into (default: `main`) |
| `--strategy TEXT` | Merge strategy: `merge`, `squash`, `rebase` (default: `merge`) |
| `--push` | Push to origin after merging |
| `--dry-run` | Show actions without executing |
| `--keep-branch` | Keep feature branch after merge (default: delete) |
| `--keep-worktree` | Keep worktree after merge (default: remove) |
| `--auto-retry`, `--no-auto-retry` | Auto-navigate to latest worktree if in wrong location (default: auto-retry) |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent feature merge
spec-kitty agent feature merge --target develop --push
spec-kitty agent feature merge --dry-run
spec-kitty agent feature merge --keep-worktree --keep-branch
```

### spec-kitty agent feature finalize-tasks

**Synopsis**: `spec-kitty agent feature finalize-tasks [OPTIONS]`

**Description**: Parse dependencies from tasks.md and update WP frontmatter, then commit to main.

**Options**:
| Flag | Description |
| --- | --- |
| `--json` | Output JSON format |
| `--help` | Show this message and exit |

**Example**:
```bash
spec-kitty agent feature finalize-tasks --json
```

---

## spec-kitty agent tasks

**Synopsis**: `spec-kitty agent tasks [OPTIONS] COMMAND [ARGS]...`

**Description**: Task workflow commands for AI agents.

**Subcommands**:
- `move-task`
- `mark-status`
- `list-tasks`
- `add-history`
- `finalize-tasks`
- `validate-workflow`
- `status`

### spec-kitty agent tasks move-task

**Synopsis**: `spec-kitty agent tasks move-task [OPTIONS] TASK_ID`

**Description**: Move task between lanes (planned -> doing -> for_review -> done).

**Arguments**:
- `TASK_ID`: Task ID (e.g., `WP01`) [required]

**Options**:
| Flag | Description |
| --- | --- |
| `--to TEXT` | Target lane (planned/doing/for_review/done) [required] |
| `--feature TEXT` | Feature slug (auto-detected if omitted) |
| `--agent TEXT` | Agent name |
| `--assignee TEXT` | Assignee name (sets assignee when moving to doing) |
| `--shell-pid TEXT` | Shell PID |
| `--note TEXT` | History note |
| `--review-feedback-file PATH` | Path to review feedback file (required when moving to planned from review) |
| `--reviewer TEXT` | Reviewer name (auto-detected from git if omitted) |
| `--force` | Force move even with unchecked subtasks or missing feedback |
| `--auto-commit`, `--no-auto-commit` | Automatically commit WP file changes to main branch (default: auto-commit) |
| `--json` | Output JSON format |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent tasks move-task WP01 --to doing --assignee claude --json
spec-kitty agent tasks move-task WP02 --to for_review --agent claude --shell-pid $$
spec-kitty agent tasks move-task WP03 --to done --note "Review passed"
```

### spec-kitty agent tasks mark-status

**Synopsis**: `spec-kitty agent tasks mark-status [OPTIONS] TASK_IDS...`

**Description**: Update task checkbox status in tasks.md for one or more tasks.

**Arguments**:
- `TASK_IDS...`: Task ID(s) - space-separated (e.g., `T001 T002 T003`) [required]

**Options**:
| Flag | Description |
| --- | --- |
| `--status TEXT` | Status: `done` or `pending` [required] |
| `--feature TEXT` | Feature slug (auto-detected if omitted) |
| `--auto-commit`, `--no-auto-commit` | Automatically commit tasks.md changes to main branch (default: auto-commit) |
| `--json` | Output JSON format |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent tasks mark-status T001 --status done
spec-kitty agent tasks mark-status T001 T002 T003 --status done --json
```

### spec-kitty agent tasks list-tasks

**Synopsis**: `spec-kitty agent tasks list-tasks [OPTIONS]`

**Description**: List tasks with optional lane filtering.

**Options**:
| Flag | Description |
| --- | --- |
| `--lane TEXT` | Filter by lane |
| `--feature TEXT` | Feature slug (auto-detected if omitted) |
| `--json` | Output JSON format |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent tasks list-tasks --json
spec-kitty agent tasks list-tasks --lane doing --json
```

### spec-kitty agent tasks add-history

**Synopsis**: `spec-kitty agent tasks add-history [OPTIONS] TASK_ID`

**Description**: Append history entry to task activity log.

**Arguments**:
- `TASK_ID`: Task ID (e.g., `WP01`) [required]

**Options**:
| Flag | Description |
| --- | --- |
| `--note TEXT` | History note [required] |
| `--feature TEXT` | Feature slug (auto-detected if omitted) |
| `--agent TEXT` | Agent name |
| `--shell-pid TEXT` | Shell PID |
| `--json` | Output JSON format |
| `--help` | Show this message and exit |

**Example**:
```bash
spec-kitty agent tasks add-history WP01 --note "Completed implementation" --json
```

### spec-kitty agent tasks finalize-tasks

**Synopsis**: `spec-kitty agent tasks finalize-tasks [OPTIONS]`

**Description**: Parse tasks.md and inject dependencies into WP frontmatter.

**Options**:
| Flag | Description |
| --- | --- |
| `--feature TEXT` | Feature slug (auto-detected if omitted) |
| `--json` | Output JSON format |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent tasks finalize-tasks --json
spec-kitty agent tasks finalize-tasks --feature 001-my-feature
```

### spec-kitty agent tasks validate-workflow

**Synopsis**: `spec-kitty agent tasks validate-workflow [OPTIONS] TASK_ID`

**Description**: Validate task metadata structure and workflow consistency.

**Arguments**:
- `TASK_ID`: Task ID (e.g., `WP01`) [required]

**Options**:
| Flag | Description |
| --- | --- |
| `--feature TEXT` | Feature slug (auto-detected if omitted) |
| `--json` | Output JSON format |
| `--help` | Show this message and exit |

**Example**:
```bash
spec-kitty agent tasks validate-workflow WP01 --json
```

### spec-kitty agent tasks status

**Synopsis**: `spec-kitty agent tasks status [OPTIONS]`

**Description**: Display kanban status board for all work packages in a feature.

**Options**:
| Flag | Description |
| --- | --- |
| `--feature TEXT`, `-f` | Feature slug (auto-detected if omitted) |
| `--json` | Output as JSON |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent tasks status
spec-kitty agent tasks status --feature 012-documentation-mission
spec-kitty agent tasks status --json
```

---

## spec-kitty agent context

**Synopsis**: `spec-kitty agent context [OPTIONS] COMMAND [ARGS]...`

**Description**: Agent context management commands.

**Subcommands**:
- `update-context`

### spec-kitty agent context update-context

**Synopsis**: `spec-kitty agent context update-context [OPTIONS]`

**Description**: Update agent context file with tech stack from plan.md.

**Options**:
| Flag | Description |
| --- | --- |
| `--agent-type TEXT`, `-a` | Agent type to update (default: claude) |
| `--json` | Output results as JSON for agent parsing |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent context update-context
spec-kitty agent context update-context --agent-type gemini --json
```

---

## spec-kitty agent workflow

**Synopsis**: `spec-kitty agent workflow [OPTIONS] COMMAND [ARGS]...`

**Description**: Workflow commands that display prompts and instructions for agents.

**Subcommands**:
- `implement`
- `review`

### spec-kitty agent workflow implement

**Synopsis**: `spec-kitty agent workflow implement [OPTIONS] [WP_ID]`

**Description**: Display work package prompt with implementation instructions.

**Arguments**:
- `WP_ID`: Work package ID (e.g., `WP01`) - auto-detects first planned if omitted

**Options**:
| Flag | Description |
| --- | --- |
| `--feature TEXT` | Feature slug (auto-detected if omitted) |
| `--agent TEXT` | Agent name (required for auto-move to doing lane) |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent workflow implement WP01 --agent claude
spec-kitty agent workflow implement --agent gemini
```

### spec-kitty agent workflow review

**Synopsis**: `spec-kitty agent workflow review [OPTIONS] [WP_ID]`

**Description**: Display work package prompt with review instructions.

**Arguments**:
- `WP_ID`: Work package ID (e.g., `WP01`) - auto-detects first for_review if omitted

**Options**:
| Flag | Description |
| --- | --- |
| `--feature TEXT` | Feature slug (auto-detected if omitted) |
| `--agent TEXT` | Agent name (required for auto-move to doing lane) |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent workflow review WP01 --agent claude
spec-kitty agent workflow review --agent gemini
```

---

## spec-kitty agent release

**Synopsis**: `spec-kitty agent release [OPTIONS] COMMAND [ARGS]...`

**Description**: Release packaging commands for AI agents.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Notes**:
- No subcommands are currently exposed in v0.11.0.

## Getting Started
- [Claude Code Workflow](../tutorials/claude-code-workflow.md)

## Practical Usage
- [Use the Dashboard](../how-to/use-dashboard.md)
- [Non-Interactive Init](../how-to/non-interactive-init.md)
