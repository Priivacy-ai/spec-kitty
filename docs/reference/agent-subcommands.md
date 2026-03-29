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

## spec-kitty agent mission

**Synopsis**: `spec-kitty agent mission [OPTIONS] COMMAND [ARGS]...`

**Description**: Feature lifecycle commands for AI agents.

**Subcommands**:
- `branch-context`
- `create-mission`
- `check-prerequisites`
- `setup-plan`
- `accept`
- `merge`
- `finalize-tasks`

### spec-kitty agent mission branch-context

**Synopsis**: `spec-kitty agent mission branch-context [OPTIONS]`

**Description**: Return deterministic branch contract for planning-stage prompts.

**Options**:
| Flag | Description |
| --- | --- |
| `--json` | Output JSON format |
| `--target-branch TEXT` | Planned landing branch (defaults to current branch) |
| `--help` | Show this message and exit |

**Example**:
```bash
spec-kitty agent mission branch-context --json
spec-kitty agent mission branch-context --target-branch develop --json
```

### spec-kitty agent mission create-mission

**Synopsis**: `spec-kitty agent mission create-mission [OPTIONS] MISSION_SLUG`

**Description**: Create new mission directory structure in planning repository.

**Arguments**:
- `MISSION_SLUG`: Feature slug (e.g., `user-auth`) [required]

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Mission type (e.g., `documentation`, `software-dev`) |
| `--json` | Output JSON format |
| `--target-branch TEXT` | Target branch (defaults to current branch) |
| `--help` | Show this message and exit |

**Example**:
```bash
spec-kitty agent mission create-mission "new-dashboard" --json
spec-kitty agent mission create-mission "new-dashboard" --mission documentation --target-branch develop
```

### spec-kitty agent mission check-prerequisites

**Synopsis**: `spec-kitty agent mission check-prerequisites [OPTIONS]`

**Description**: Validate feature structure and prerequisites.

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Feature slug (e.g., `020-my-feature`) |
| `--json` | Output JSON format |
| `--paths-only` | Only output path variables |
| `--include-tasks` | Include tasks.md in validation |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent mission check-prerequisites --json
spec-kitty agent mission check-prerequisites --mission 020-my-feature --paths-only --json
```

### spec-kitty agent mission setup-plan

**Synopsis**: `spec-kitty agent mission setup-plan [OPTIONS]`

**Description**: Scaffold implementation plan template in planning repository.

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Feature slug (e.g., `020-my-feature`) |
| `--json` | Output JSON format |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent mission setup-plan --json
spec-kitty agent mission setup-plan --mission 020-my-feature --json
```

### spec-kitty agent mission accept

**Synopsis**: `spec-kitty agent mission accept [OPTIONS]`

**Description**: Perform feature acceptance workflow.

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Feature directory slug (auto-detected if not specified) |
| `--mode TEXT` | Acceptance mode: `auto`, `pr`, `local`, `checklist` (default: `auto`) |
| `--json` | Output results as JSON for agent parsing |
| `--lenient` | Skip strict metadata validation |
| `--no-commit` | Skip auto-commit (report only) |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent mission accept
spec-kitty agent mission accept --json
spec-kitty agent mission accept --lenient --json
```

### spec-kitty agent mission merge

**Synopsis**: `spec-kitty agent mission merge [OPTIONS]`

**Description**: Merge mission branch into target branch.

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Feature directory slug (auto-detected if not specified) |
| `--target TEXT` | Target branch to merge into (default: `main`) |
| `--strategy TEXT` | Merge strategy: `merge`, `squash`, `rebase` (default: `merge`) |
| `--push` | Push to origin after merging |
| `--dry-run` | Show actions without executing |
| `--keep-branch` | Keep mission branch after merge (default: delete) |
| `--keep-worktree` | Keep worktree after merge (default: remove) |
| `--auto-retry`, `--no-auto-retry` | Auto-navigate to a deterministic mission worktree if in wrong location (default: no-auto-retry) |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent mission merge
spec-kitty agent mission merge --target develop --push
spec-kitty agent mission merge --dry-run
spec-kitty agent mission merge --keep-worktree --keep-branch
```

### spec-kitty agent mission finalize-tasks

**Synopsis**: `spec-kitty agent mission finalize-tasks [OPTIONS]`

**Description**: Parse dependencies from tasks.md and update WP frontmatter, then commit to main.

**Options**:
| Flag | Description |
| --- | --- |
| `--json` | Output JSON format |
| `--help` | Show this message and exit |

**Example**:
```bash
spec-kitty agent mission finalize-tasks --json
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
- `map-requirements`
- `validate-workflow`
- `status`
- `list-dependents`

### spec-kitty agent tasks move-task

**Synopsis**: `spec-kitty agent tasks move-task [OPTIONS] TASK_ID`

**Description**: Move task between lanes (planned -> doing -> for_review -> done).

**Arguments**:
- `TASK_ID`: Task ID (e.g., `WP01`) [required]

**Options**:
| Flag | Description |
| --- | --- |
| `--to TEXT` | Target lane (planned/doing/for_review/done) [required] |
| `--mission TEXT` | Feature slug (auto-detected if omitted) |
| `--agent TEXT` | Agent name |
| `--assignee TEXT` | Assignee name (sets assignee when moving to doing) |
| `--shell-pid TEXT` | Shell PID |
| `--note TEXT` | History note |
| `--review-feedback-file PATH` | Path to review feedback file (required for `--to planned`, including with `--force`) |
| `--approval-ref TEXT` | Approval reference for approval/done transitions (e.g., `PR#42`) |
| `--reviewer TEXT` | Reviewer name (auto-detected from git if omitted) |
| `--done-override-reason TEXT` | Required when `--to done` and merge ancestry cannot be verified; recorded in history/event reason |
| `--force` | Force move even with unchecked subtasks (does not bypass planned rollback feedback requirement) |
| `--auto-commit`, `--no-auto-commit` | Automatically commit WP file changes to main branch (default: auto-commit) |
| `--json` | Output JSON format |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent tasks move-task WP01 --to doing --assignee claude --json
spec-kitty agent tasks move-task WP02 --to for_review --agent claude --shell-pid $$
spec-kitty agent tasks move-task WP03 --to done --note "Review passed"
spec-kitty agent tasks move-task WP03 --to planned --review-feedback-file /tmp/spec-kitty-review-feedback-WP03.md --note "Changes requested"
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
| `--mission TEXT` | Feature slug (auto-detected if omitted) |
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
| `--mission TEXT` | Feature slug (auto-detected if omitted) |
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
| `--mission TEXT` | Feature slug (auto-detected if omitted) |
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
| `--mission TEXT` | Feature slug (auto-detected if omitted) |
| `--json` | Output JSON format |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent tasks finalize-tasks --json
spec-kitty agent tasks finalize-tasks --mission 001-my-feature
```

### spec-kitty agent tasks map-requirements

**Synopsis**: `spec-kitty agent tasks map-requirements [OPTIONS]`

**Description**: Register requirement-to-WP mappings with immediate validation.

**Options**:
| Flag | Description |
| --- | --- |
| `--wp TEXT` | WP ID (e.g., `WP04`) |
| `--refs TEXT` | Comma-separated requirement refs (e.g., `FR-001,FR-002`) |
| `--batch TEXT` | JSON batch mapping (e.g., `'{"WP01":["FR-001"],"WP02":["FR-003"]}'`) |
| `--replace` | Replace existing refs instead of merging (default: merge/union) |
| `--mission TEXT` | Feature slug (auto-detected if omitted) |
| `--json` | Output JSON format |
| `--auto-commit`, `--no-auto-commit` | Automatically commit WP file changes (default: from project config) |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent tasks map-requirements --wp WP04 --refs FR-001,FR-002
spec-kitty agent tasks map-requirements --batch '{"WP01":["FR-001"],"WP02":["FR-003"]}' --json
spec-kitty agent tasks map-requirements --wp WP01 --refs FR-005 --replace
```

### spec-kitty agent tasks validate-workflow

**Synopsis**: `spec-kitty agent tasks validate-workflow [OPTIONS] TASK_ID`

**Description**: Validate task metadata structure and workflow consistency.

**Arguments**:
- `TASK_ID`: Task ID (e.g., `WP01`) [required]

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Feature slug (auto-detected if omitted) |
| `--json` | Output JSON format |
| `--help` | Show this message and exit |

**Example**:
```bash
spec-kitty agent tasks validate-workflow WP01 --json
```

### spec-kitty agent tasks status

**Synopsis**: `spec-kitty agent tasks status [OPTIONS]`

**Description**: Display kanban status board for all work packages in a feature. WPs in "doing" with no commits for `--stale-threshold` minutes are flagged as potentially stale (agent may have stopped).

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT`, `-f` | Feature slug (auto-detected if omitted) |
| `--json` | Output as JSON |
| `--stale-threshold INTEGER` | Minutes of inactivity before a WP is considered stale (default: `10`) |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent tasks status
spec-kitty agent tasks status --mission 012-documentation-mission
spec-kitty agent tasks status --json
spec-kitty agent tasks status --stale-threshold 15
```

### spec-kitty agent tasks list-dependents

**Synopsis**: `spec-kitty agent tasks list-dependents [OPTIONS] WP_ID`

**Description**: Find all WPs that depend on a given WP (downstream dependents). Answers "who depends on me?" -- useful when reviewing a WP to understand the impact of requested changes on downstream work packages. Also shows what the WP itself depends on (upstream dependencies).

**Arguments**:
- `WP_ID`: Work package ID (e.g., `WP01`) [required]

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Feature slug (auto-detected if omitted) |
| `--json` | Output JSON format |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent tasks list-dependents WP13
spec-kitty agent tasks list-dependents WP01 --mission 001-my-feature --json
```

---

## spec-kitty agent config

**Synopsis**: `spec-kitty agent config [OPTIONS] COMMAND [ARGS]...`

**Description**: Manage project AI agent configuration (add, remove, list, sync agents).

**Subcommands**:

| Command | Description |
|---------|-------------|
| `list` | View configured agents and available options |
| `add` | Add one or more agents to your project |
| `remove` | Remove one or more agents from your project |
| `status` | Audit agent configuration sync status |
| `sync` | Synchronize filesystem with config.yaml |
| `set` | Set a project-level agent configuration value |

### spec-kitty agent config set

**Synopsis**: `spec-kitty agent config set [OPTIONS] KEY VALUE`

**Description**: Set a project-level agent configuration value.

**Arguments**:
- `KEY`: Configuration key (e.g., `auto_commit`) [required]
- `VALUE`: Configuration value (e.g., `true`, `false`) [required]

Currently supported keys: `auto_commit` (enable/disable automatic commits by agents).

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent config set auto_commit false
spec-kitty agent config set auto_commit true
```

**See**:
- [CLI Reference: spec-kitty agent config](cli-commands.md#spec-kitty-agent-config) - Complete command syntax and options
- [Managing AI Agents](../how-to/manage-agents.md) - Task-oriented guide for agent management workflows

---

## spec-kitty agent context

**Synopsis**: `spec-kitty agent context [OPTIONS] COMMAND [ARGS]...`

**Description**: Agent context management commands.

**Subcommands**:
- `resolve`
- `update-context`

### spec-kitty agent context resolve

**Synopsis**: `spec-kitty agent context resolve [OPTIONS]`

**Description**: Resolve canonical feature/work-package/action context for prompt execution.

**Options**:
| Flag | Description |
| --- | --- |
| `--action TEXT` | Action to resolve context for (`tasks`, `tasks_outline`, `tasks_packages`, `tasks_finalize`, `implement`, `review`) [required] |
| `--mission TEXT` | Feature slug (e.g., `020-my-feature`) |
| `--wp-id TEXT` | Work package ID (e.g., `WP01`) |
| `--base TEXT` | Explicit base WP for implement |
| `--agent TEXT` | Agent name for exact command rendering |
| `--json` | Output results as JSON |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent context resolve --action implement --wp-id WP01 --json
spec-kitty agent context resolve --action review --mission 020-my-feature --agent claude
spec-kitty agent context resolve --action implement --wp-id WP02 --base WP01
```

### spec-kitty agent context update-context

**Synopsis**: `spec-kitty agent context update-context [OPTIONS]`

**Description**: Update agent context file with tech stack from plan.md.

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Feature slug (e.g., `020-my-feature`) |
| `--agent-type TEXT`, `-a` | Agent type to update. Supported: claude, gemini, copilot, cursor, qwen, opencode, codex, windsurf, kilocode, auggie, roo, q. (default: `claude`) |
| `--json` | Output results as JSON for agent parsing |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent context update-context
spec-kitty agent context update-context --mission 020-my-feature --agent-type gemini --json
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

**Description**: Display work package prompt with implementation instructions. Automatically moves WP from planned to doing lane (requires `--agent` to track who is working). If `--base` is provided, creates a worktree for this WP branching from the base WP's branch.

**Arguments**:
- `WP_ID`: Work package ID (e.g., `WP01`, `wp01`, `WP01-slug`) - auto-detects first planned if omitted

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Feature slug (auto-detected if omitted) |
| `--agent TEXT` | Agent name (required for auto-move to doing lane) |
| `--base TEXT` | Base WP to branch from (e.g., `WP01`) - creates worktree if provided |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent workflow implement WP01 --agent claude
spec-kitty agent workflow implement WP02 --agent claude --base WP01
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
| `--mission TEXT` | Feature slug (auto-detected if omitted) |
| `--agent TEXT` | Agent name (required for auto-move to doing lane) |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent workflow review WP01 --agent claude
spec-kitty agent workflow review --agent gemini
```

---

## spec-kitty agent status

**Synopsis**: `spec-kitty agent status [OPTIONS] COMMAND [ARGS]...`

**Description**: Canonical status management commands.

**Subcommands**:
- `emit`
- `materialize`
- `doctor`
- `migrate`
- `validate`
- `reconcile`

### spec-kitty agent status emit

**Synopsis**: `spec-kitty agent status emit [OPTIONS] WP_ID`

**Description**: Emit a status transition event for a work package. Records a lane transition in the canonical event log, validates the transition against the state machine, materializes a snapshot, and updates legacy compatibility views.

**Arguments**:
- `WP_ID`: Work package ID (e.g., `WP01`) [required]

**Options**:
| Flag | Description |
| --- | --- |
| `--to TEXT` | Target lane (e.g., `claimed`, `in_progress`, `for_review`, `approved`, `done`) [required] |
| `--actor TEXT` | Who is making this transition [required] |
| `--mission TEXT` | Feature slug (auto-detected if omitted) |
| `--force` | Force transition bypassing guards |
| `--reason TEXT` | Reason for forced transition |
| `--evidence-json TEXT` | JSON string with done evidence |
| `--review-ref TEXT` | Review feedback reference |
| `--workspace-context TEXT` | Workspace context identifier for claimed->in_progress |
| `--subtasks-complete` | Whether required subtasks are complete for in_progress->for_review |
| `--implementation-evidence-present` | Whether implementation evidence exists for in_progress->for_review |
| `--execution-mode TEXT` | Execution mode: `worktree` or `direct_repo` (default: `worktree`) |
| `--json` | Machine-readable JSON output |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent status emit WP01 --to claimed --actor claude
spec-kitty agent status emit WP01 --to done --actor claude --evidence-json '{"review": {"reviewer": "alice", "verdict": "approved", "reference": "PR#1"}}'
spec-kitty agent status emit WP01 --to in_progress --actor claude --force --reason "resuming after crash"
```

### spec-kitty agent status materialize

**Synopsis**: `spec-kitty agent status materialize [OPTIONS]`

**Description**: Rebuild status.json from the canonical event log. Reads all events from status.events.jsonl, applies the deterministic reducer to produce a snapshot, writes status.json, and updates legacy compatibility views.

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Feature slug (auto-detected if omitted) |
| `--json` | Machine-readable JSON output |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent status materialize
spec-kitty agent status materialize --mission 034-my-feature
spec-kitty agent status materialize --json
```

### spec-kitty agent status doctor

**Synopsis**: `spec-kitty agent status doctor [OPTIONS]`

**Description**: Run health checks for status hygiene and global runtime. Detects global runtime issues (missing ~/.kittify/, version mismatch, corrupted missions) and project-level issues (stale claims, orphan workspaces, drift). Exit code 0 = healthy, 1 = issues found.

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Feature slug |
| `--stale-claimed-days INTEGER` | Threshold for stale claims in days (default: `7`) |
| `--stale-in-progress-days INTEGER` | Threshold for stale in-progress in days (default: `14`) |
| `--json` | Machine-readable JSON output |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent status doctor
spec-kitty agent status doctor --mission 034-my-feature
spec-kitty agent status doctor --stale-claimed-days 3 --json
```

### spec-kitty agent status migrate

**Synopsis**: `spec-kitty agent status migrate [OPTIONS]`

**Description**: Bootstrap canonical event logs from existing frontmatter state. Reads WP frontmatter lanes and creates bootstrap StatusEvents in status.events.jsonl. Resolves aliases (e.g. `doing` -> `in_progress`). Idempotent: features with existing event logs are skipped.

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT`, `-f` | Single feature slug to migrate |
| `--all` | Migrate all missions in kitty-specs/ |
| `--dry-run` | Preview migration without writing events |
| `--json` | Output results as JSON |
| `--actor TEXT` | Actor name for bootstrap events (default: `migration`) |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent status migrate --mission 034-feature-name --dry-run
spec-kitty agent status migrate --all
spec-kitty agent status migrate --all --json
```

### spec-kitty agent status validate

**Synopsis**: `spec-kitty agent status validate [OPTIONS]`

**Description**: Validate canonical status model integrity. Runs all validation checks: event schema, transition legality, done-evidence completeness, materialization drift, and derived-view drift. Exit code 0 for pass (no errors), exit code 1 for fail (any errors). Warnings do not cause failure.

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Feature slug (auto-detected if omitted) |
| `--json` | Machine-readable JSON output |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent status validate
spec-kitty agent status validate --mission 034-my-feature
spec-kitty agent status validate --json
```

### spec-kitty agent status reconcile

**Synopsis**: `spec-kitty agent status reconcile [OPTIONS]`

**Description**: Detect planning-vs-implementation drift and suggest reconciliation events. Scans target repositories for WP-linked branches and commits, compares against the canonical snapshot state, and generates StatusEvent objects to align planning with implementation reality. Default mode is `--dry-run` which previews without persisting. Use `--apply` to emit reconciliation events (Phase 1+ required).

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT`, `-f` | Feature slug (auto-detected if omitted) |
| `--dry-run`, `--apply` | Preview vs persist reconciliation events (default: `dry-run`) |
| `--target-repo PATH`, `-t` | Target repo path(s) to scan |
| `--json` | Machine-readable JSON output |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent status reconcile --dry-run
spec-kitty agent status reconcile --mission 034-feature-name --json
spec-kitty agent status reconcile --apply --target-repo /path/to/repo
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
- No subcommands are currently exposed in 2.x.

## Getting Started
- [Claude Code Workflow](../tutorials/claude-code-workflow.md)

## Practical Usage
- [Use the Dashboard](../how-to/use-dashboard.md)
- [Non-Interactive Init](../how-to/non-interactive-init.md)
