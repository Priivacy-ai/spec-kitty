# CLI Command Reference

This reference lists the user-facing `spec-kitty` CLI commands and their flags exactly as surfaced by `--help`. For agent-only commands, see `docs/reference/agent-subcommands.md`.

Terminology note:
- `Mission Type` = reusable workflow blueprint
- `Mission` = tracked item under `kitty-specs/<mission-slug>/`
- `Mission Run` = runtime/session instance
- As of 3.1.0, `--mission` is the canonical flag name for specifying the mission slug. `--feature` remains a backward-compatibility alias and continues to work on all commands.
- `accept-feature`/`merge-feature` command names are legacy software-dev compatibility surfaces for the tracked mission

## spec-kitty

**Synopsis**: `spec-kitty [OPTIONS] COMMAND [ARGS]...`

**Description**: Spec Kitty CLI entry point.

**Options**:
| Flag | Description |
| --- | --- |
| `--version`, `-v` | Show version and exit |
| `--help` | Show this message and exit |

**Commands**:
- `init` - Initialize a new Spec Kitty project from templates
- `accept` - Validate mission readiness before merging to main
- `config` - Display project configuration and asset resolution information
- `dashboard` - Open or stop the Spec Kitty dashboard
- `implement` - Create workspace for work package implementation
- `specify` - Create a mission scaffold in kitty-specs/
- `plan` - Scaffold plan.md for a mission
- `tasks` - Finalize tasks metadata after task generation
- `merge` - Merge a completed mission branch into the target branch and clean up resources
- `migrate` - Migrate project .kittify/ to centralized model
- `next` - Decide and emit the next agent action for the current mission
- `research` - Execute Phase 0 research workflow to scaffold artifacts
- `upgrade` - Upgrade a Spec Kitty project to the current version
- `list-legacy-features` - List legacy worktrees blocking 0.11.0 upgrade
- `validate-encoding` - Validate and optionally fix file encoding in feature artifacts
- `validate-tasks` - Validate and optionally fix task metadata inconsistencies
- `verify-setup` - Verify that the current environment matches Spec Kitty expectations
- `agent` - Commands for AI agents to execute spec-kitty workflows programmatically
- `auth` - Authentication commands
- `charter` - Charter management commands
- `context` - Query workspace context information
- `doctor` - Project health diagnostics
- `glossary` - Glossary management commands
- `mission` - View available Spec Kitty missions
- `ops` - Operation history (git reflog)
- `orchestrator-api` - Machine-contract API for external orchestrators (JSON envelope interface)
- `repair` - Repair broken templates
- `sync` - Synchronization commands
- `tracker` - Task tracker commands

---

## spec-kitty init

**Synopsis**: `spec-kitty init [OPTIONS] [PROJECT_NAME]`

**Description**: Initialize a new Spec Kitty project from templates.

**Arguments**:
- `PROJECT_NAME`: Name for your new project directory (use `.` for current directory)

**Options**:
| Flag | Description |
| --- | --- |
| `--ai TEXT` | Comma-separated AI assistants (claude,codex,gemini,...) |
| `--non-interactive` / `--yes` | Disable prompts (CI/CD) |
| `--no-git` | Skip git repository initialization |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty init my-project
spec-kitty init my-project --ai codex
spec-kitty init my-project --ai codex,claude
spec-kitty init . --ai codex
spec-kitty init my-project --ai codex --non-interactive
```

**See Also**: `docs/non-interactive-init.md`

---

## spec-kitty upgrade

**Synopsis**: `spec-kitty upgrade [OPTIONS]`

**Description**: Upgrade a Spec Kitty project to the current version.

**Options**:
| Flag | Description |
| --- | --- |
| `--dry-run` | Preview changes without applying |
| `--force` | Skip confirmation prompts |
| `--target TEXT` | Target version (defaults to current CLI version) |
| `--json` | Output results as JSON |
| `--verbose`, `-v` | Show detailed migration information |
| `--no-worktrees` | Skip upgrading worktrees |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty upgrade
spec-kitty upgrade --dry-run
spec-kitty upgrade --target 0.6.5
```

---

## spec-kitty implement

**Synopsis**: `spec-kitty implement [OPTIONS] WP_ID`

**Description**: Create workspace for work package implementation (git worktree).

**Arguments**:
- `WP_ID`: Work package ID (e.g., `WP01`) [required]

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Mission slug (canonical flag; e.g., `001-my-feature`) |
| `--feature TEXT` | Backward-compatibility alias for `--mission` |
| `--recover` | Restore execution context for a WP stuck in `in_progress` after a crash |
| `--base TEXT` | Override base ref for the worktree (advanced; normally auto-detected) |
| `--auto-commit`, `--no-auto-commit` | Auto-commit lane change (default: from project config) |
| `--json` | Output in JSON format |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty implement WP01
spec-kitty implement WP02
spec-kitty implement WP01 --mission 001-my-feature
spec-kitty implement WP01 --recover
spec-kitty implement WP01 --json
```

---

## spec-kitty accept

**Synopsis**: `spec-kitty accept [OPTIONS]`

**Description**: Validate mission readiness before merging to main.

**Options**:
| Flag | Description |
| --- | --- |
| `--feature TEXT` | Mission slug to accept (legacy flag name; compatibility alias for software-dev missions) |
| `--mode TEXT` | Acceptance mode: `auto`, `pr`, `local`, or `checklist` (default: `auto`) |
| `--actor TEXT` | Name to record as the acceptance actor |
| `--test TEXT` | Validation command executed (repeatable) |
| `--json` | Emit JSON instead of formatted text |
| `--lenient` | Skip strict metadata validation |
| `--no-commit` | Skip auto-commit; report only |
| `--allow-fail` | Return checklist even when issues remain |
| `--help` | Show this message and exit |

---

## spec-kitty merge

**Synopsis**: `spec-kitty merge [OPTIONS]`

**Description**: Merge lane branches into the mission branch, merge the mission branch into the target branch, and clean up execution worktrees. Use `--resume` to continue an interrupted merge from saved state. Use `--abort` to clear merge state and abort any in-progress git merge.

**Options**:
| Flag | Description |
| --- | --- |
| `--strategy TEXT` | Merge strategy: `MERGE` (merge commit), `SQUASH` (squash to single commit), or `REBASE` (linear history). Default: `MERGE`. Case-insensitive. |
| `--mission TEXT` | Mission slug when merging from main branch (canonical flag) |
| `--feature TEXT` | Backward-compatibility alias for `--mission` |
| `--delete-branch`, `--keep-branch` | Delete or keep feature branch after merge (default: delete) |
| `--remove-worktree`, `--keep-worktree` | Remove or keep resolved execution worktrees after merge (default: remove) |
| `--push` | Push to origin after merge |
| `--target TEXT` | Target branch to merge into (auto-detected) |
| `--dry-run` | Show what would be done without executing |
| `--json` | Output deterministic JSON (dry-run mode) |
| `--resume` | Resume an interrupted merge from saved state in `.kittify/merge-state.json` |
| `--abort` | Abort and clear merge state |
| `--help` | Show this message and exit |

**Strategy notes**:
- `MERGE` — creates a merge commit; preserves full history; default.
- `SQUASH` — collapses all lane commits into a single commit on the target branch.
- `REBASE` — replays lane commits on top of the target branch for a linear history; may be rejected by repos with linear-history branch protection if commits already exist on a remote.

**Resume / abort**:
```bash
spec-kitty merge --resume   # continue from .kittify/merge-state.json
spec-kitty merge --abort    # clear saved state and abort any in-progress git merge
```

---

## spec-kitty dashboard

**Synopsis**: `spec-kitty dashboard [OPTIONS]`

**Description**: Open or stop the Spec Kitty dashboard.

**Options**:
| Flag | Description |
| --- | --- |
| `--port INTEGER` | Preferred port for the dashboard (falls back to first available port) |
| `--kill` | Stop the running dashboard for this project and clear its metadata |
| `--open` | Open dashboard URL in your default browser (disabled by default) |
| `--help` | Show this message and exit |

---

## spec-kitty research

**Synopsis**: `spec-kitty research [OPTIONS]`

**Description**: Execute Phase 0 research workflow to scaffold artifacts.

**Options**:
| Flag | Description |
| --- | --- |
| `--feature TEXT` | Mission slug to target (legacy flag name; auto-detected when omitted) |
| `--force` | Overwrite existing research artifacts |
| `--help` | Show this message and exit |

---

## spec-kitty orchestrator-api

**Synopsis**: `spec-kitty orchestrator-api [OPTIONS] COMMAND [ARGS]...`

**Description**: Machine-contract API for external orchestrators. Every command emits exactly one JSON envelope and exits non-zero on failure.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Commands**:
- `contract-version` - Return host contract version and provider compatibility minimum
- `feature-state` - Return full mission/WP state snapshot
- `list-ready` - Return `planned` WPs whose dependencies are `done`
- `start-implementation` - Composite claim/start transition for a WP
- `start-review` - Move rejected WP from `for_review` back to `in_progress`
- `transition` - Apply explicit lane transition with state-machine validation
- `append-history` - Append activity history to a WP prompt
- `accept-feature` - Accept a mission when all WPs are `done`
- `merge-feature` - Run preflight and land the mission into the target branch

**See Also**: [Orchestrator API Reference](orchestrator-api.md)

---

## spec-kitty sync

**Synopsis**: `spec-kitty sync [OPTIONS] COMMAND [ARGS]...`

**Description**: Synchronization commands. This is a command group with subcommands for workspace sync, event queue sync, and sync health diagnostics.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Commands**:
- `workspace` - Synchronize workspace with upstream changes
- `server` - Show or set sync server URL
- `now` - Trigger immediate sync of all queued events
- `status` - Show sync queue status, connection state, and auth info
- `diagnose` - Validate queued events locally against the event schema
- `doctor` - Diagnose sync health: queue, auth, and server connectivity

### spec-kitty sync workspace

**Synopsis**: `spec-kitty sync workspace [OPTIONS]`

**Description**: Synchronize workspace with upstream changes. Updates the current workspace with changes from its base branch or parent using `git rebase <base-branch>`. Sync may fail on conflicts; you must resolve conflicts before continuing.

**Options**:
| Flag | Description |
| --- | --- |
| `--repair`, `-r` | Attempt workspace recovery (may lose uncommitted work) |
| `--verbose`, `-v` | Show detailed sync output |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty sync workspace
spec-kitty sync workspace --verbose
spec-kitty sync workspace --repair
```

### spec-kitty sync server

**Synopsis**: `spec-kitty sync server [OPTIONS] [URL]`

**Description**: Show or set sync server URL.

**Arguments**:
- `URL`: Sync server URL to set (must be `https://...`) [optional]

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty sync server
spec-kitty sync server https://spec-kitty-dev.fly.dev
```

### spec-kitty sync now

**Synopsis**: `spec-kitty sync now [OPTIONS]`

**Description**: Trigger immediate sync of all queued events. Drains the offline queue completely, uploading events to the server in batches of 1000 until the queue is empty or all remaining events have exceeded their retry limit.

**Options**:
| Flag | Description |
| --- | --- |
| `--report PATH` | Export per-event failure details to a JSON file |
| `--strict`, `--no-strict` | Exit non-zero on sync errors (default: strict) |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty sync now
spec-kitty sync now --report failures.json
spec-kitty sync now --no-strict
```

### spec-kitty sync status

**Synopsis**: `spec-kitty sync status [OPTIONS]`

**Description**: Show sync queue status, connection state, and auth info. Displays offline queue size, connection/emitter status, last sync timestamp, auth status, and server URL configuration.

**Options**:
| Flag | Description |
| --- | --- |
| `--check`, `-c` | Test connection to server (may be slow if server is unreachable) |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty sync status
spec-kitty sync status --check
```

### spec-kitty sync diagnose

**Synopsis**: `spec-kitty sync diagnose [OPTIONS]`

**Description**: Validate queued events locally against the event schema. Reads all pending events from the offline queue and validates each one against the Pydantic Event model and per-event-type payload rules. Valid events are reported as passing; malformed events show specific field errors grouped by error category.

**Options**:
| Flag | Description |
| --- | --- |
| `--json` | Output results as JSON instead of Rich table |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty sync diagnose
spec-kitty sync diagnose --json
```

### spec-kitty sync doctor

**Synopsis**: `spec-kitty sync doctor [OPTIONS]`

**Description**: Diagnose sync health: queue, auth, and server connectivity. Runs a comprehensive check of offline queue state, authentication validity, and server reachability, printing actionable remediation steps for any issues found.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty sync doctor
```

**See Also**: [Sync Workspaces](../how-to/sync-workspaces.md)

---

## spec-kitty ops

**Synopsis**: `spec-kitty ops COMMAND [ARGS]...`

**Description**: Operation history (git reflog).

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Commands**:
- `log` - Show operation history
- `undo` - Undo is not supported for git

### spec-kitty ops log

**Synopsis**: `spec-kitty ops log [OPTIONS]`

**Description**: Show git reflog entries. Displays recent git operations that have modified the repository state.

**Options**:
| Flag | Description |
| --- | --- |
| `--limit`, `-n INTEGER` | Number of operations to show (default: 20) |
| `--verbose`, `-v` | Show full operation IDs and details |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty ops log
spec-kitty ops log -n 50
spec-kitty ops log --verbose
```

### spec-kitty ops undo

**Synopsis**: `spec-kitty ops undo [OPTIONS]`

**Description**: Undo is not supported for git. Git does not have reversible operation history. Consider using these alternatives manually: `git reset --soft HEAD~1` (undo last commit, keep changes), `git reset --hard HEAD~1` (undo last commit, discard changes), `git revert <commit>` (create reverting commit), or `git reflog` (find previous states).

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

---

## spec-kitty mission

**Synopsis**: `spec-kitty mission [OPTIONS] COMMAND [ARGS]...`

**Description**: View available Spec Kitty missions. Missions are selected per-feature during `/spec-kitty.specify`.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

### spec-kitty mission list

**Synopsis**: `spec-kitty mission list [OPTIONS]`

**Description**: List all available missions with their source (project/built-in).

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

### spec-kitty mission current

**Synopsis**: `spec-kitty mission current [OPTIONS]`

**Description**: Show currently active mission.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

### spec-kitty mission info

**Synopsis**: `spec-kitty mission info [OPTIONS] MISSION_NAME`

**Description**: Show details for a specific mission without switching.

**Arguments**:
- `MISSION_NAME`: Mission name to display details for [required]

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

### spec-kitty mission switch

**Synopsis**: `spec-kitty mission switch [OPTIONS] MISSION_NAME`

**Description**: (deprecated) Switch active mission - removed in v0.8.0.

**Arguments**:
- `MISSION_NAME`: Mission name (no longer supported) [required]

**Options**:
| Flag | Description |
| --- | --- |
| `--force` | (ignored) |
| `--help` | Show this message and exit |

---

## spec-kitty validate-encoding

**Synopsis**: `spec-kitty validate-encoding [OPTIONS]`

**Description**: Validate and optionally fix file encoding in feature artifacts.

**Options**:
| Flag | Description |
| --- | --- |
| `--feature TEXT` | Mission slug to validate (legacy flag name; auto-detected when omitted) |
| `--fix` | Automatically fix encoding errors by sanitizing files |
| `--all` | Check all features, not just one |
| `--backup`, `--no-backup` | Create .bak files before fixing (default: backup) |
| `--help` | Show this message and exit |

---

## spec-kitty validate-tasks

**Synopsis**: `spec-kitty validate-tasks [OPTIONS]`

**Description**: Validate and optionally fix task metadata inconsistencies.

**Options**:
| Flag | Description |
| --- | --- |
| `--feature TEXT` | Mission slug to validate (legacy flag name; auto-detected when omitted) |
| `--fix` | Automatically repair metadata inconsistencies |
| `--all` | Check all features, not just one |
| `--agent TEXT` | Agent name for activity log |
| `--shell-pid TEXT` | Shell PID for activity log |
| `--help` | Show this message and exit |

---

## spec-kitty verify-setup

**Synopsis**: `spec-kitty verify-setup [OPTIONS]`

**Description**: Verify that the current environment matches Spec Kitty expectations.

**Options**:
| Flag | Description |
| --- | --- |
| `--feature TEXT` | Mission slug to verify (legacy flag name; auto-detected when omitted) |
| `--json` | Output in JSON format for AI agents |
| `--check-files` | Check mission file integrity (default: True) |
| `--check-tools` | Check for installed development tools (default: True) |
| `--diagnostics` | Show detailed diagnostics with dashboard health |
| `--help` | Show this message and exit |

---

## spec-kitty list-legacy-features

**Synopsis**: `spec-kitty list-legacy-features [OPTIONS]`

**Description**: List legacy worktrees blocking 0.11.0 upgrade.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

---

## spec-kitty repair

**Synopsis**: `spec-kitty repair [OPTIONS] COMMAND [ARGS]...`

**Description**: Repair broken templates.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Commands**:
- `repair` - Repair broken templates caused by v0.10.0-0.10.8 bundling bug
- `worktree` - Diagnose worktree kitty-specs/ status

### spec-kitty repair repair

**Synopsis**: `spec-kitty repair repair [OPTIONS]`

**Description**: Repair broken templates caused by v0.10.0-0.10.8 bundling bug.

**Options**:
| Flag | Description |
| --- | --- |
| `--project-path PATH`, `-p` | Path to project to repair |
| `--dry-run` | Show what would be changed without making changes |
| `--help` | Show this message and exit |

### spec-kitty repair worktree

**Synopsis**: `spec-kitty repair worktree [OPTIONS] [WORKTREE_PATH]`

**Description**: Diagnose worktree kitty-specs/ status. Checks if worktrees have kitty-specs/ directories and explains how WP operations work: WP lane changes (move-task) always use main repo's kitty-specs/, research artifacts can be added to worktree's kitty-specs/, and stale WP files in worktrees don't affect lane operations.

**Arguments**:
- `WORKTREE_PATH`: Specific worktree path to check (defaults to current directory if in a worktree) [optional]

**Options**:
| Flag | Description |
| --- | --- |
| `--all` | Check all worktrees in .worktrees/ directory |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty repair worktree
spec-kitty repair worktree --all
```

---

## spec-kitty agent

**Synopsis**: `spec-kitty agent [OPTIONS] COMMAND [ARGS]...`

**Description**: Commands for AI agents to execute spec-kitty workflows programmatically.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**See Also**: `docs/reference/agent-subcommands.md`

---

### spec-kitty agent config

Manage project AI agent configuration (add, remove, list agents).

**Usage**:
```bash
spec-kitty agent config [OPTIONS] COMMAND [ARGS]...
```

**Description**: The `config` subcommand provides tools for managing which AI agents are active in your project. Agent configuration is stored in `.kittify/config.yaml` and controls which agent directories are present on the filesystem.

**Subcommands**:

| Command | Description |
|---------|-------------|
| `list` | List configured agents and their status |
| `add` | Add agents to the project |
| `remove` | Remove agents from the project |
| `status` | Show which agents are configured vs present on filesystem |
| `sync` | Sync filesystem with config.yaml |
| `set` | Set a project-level agent configuration value |

**See also**: [Managing AI Agents](../how-to/manage-agents.md) for task-oriented guidance on agent management workflows.

> **Note**: Starting in 0.12.0, agent configuration is config-driven. `.kittify/config.yaml` is the single source of truth, and migrations respect your configuration choices. See [Upgrading to 0.12.0](../how-to/upgrade-to-0-12-0.md) for migration details.

#### spec-kitty agent config list

View configured agents and available options.

**Synopsis**:
```bash
spec-kitty agent config list
```

**Description**:

Lists agents currently configured in your project (from `.kittify/config.yaml`) with status indicators, and shows available agents that can be added.

**Arguments**: None

**Options**: None

**Output**:

Two sections:
- **Configured agents**: Agents in `config.yaml` with status indicators:
  - ✓ (green) - Directory exists
  - ⚠ (yellow) - Configured but directory missing
- **Available but not configured**: Agents you can add

**Examples**:

View configured agents:
```bash
spec-kitty agent config list
```

Example output:
```
Configured agents:
  ✓ opencode (.opencode/command/)
  ✓ claude (.claude/commands/)

Available but not configured:
  - codex
  - gemini
  - cursor
  ...
```

#### spec-kitty agent config add

Add one or more agents to your project.

**Synopsis**:
```bash
spec-kitty agent config add <agent1> [agent2] [agent3] ...
```

**Description**:

Adds specified agents to your project by creating agent directories, copying slash command templates, and updating `.kittify/config.yaml`.

**Arguments**:

- `<agents>`: Space-separated list of agent keys to add. Valid keys: `claude`, `codex`, `gemini`, `cursor`, `qwen`, `opencode`, `windsurf`, `kilocode`, `roo`, `copilot`, `auggie`, `q`.

**Options**: None

**Output**:

- Success: `✓ Added <agent-dir>/<subdir>/` for each agent
- Already configured: `Already configured: <agent>` (informational, not an error)
- Error: `Error: Invalid agent keys: <keys>` with list of valid keys

**Side Effects**:

- Creates agent directory (e.g., `.claude/commands/`)
- Copies slash command templates from mission templates
- Adds agent key to `.kittify/config.yaml` under `agents.available`

**Examples**:

Add a single agent:
```bash
spec-kitty agent config add claude
```

Add multiple agents:
```bash
spec-kitty agent config add codex gemini cursor
```

Example output:
```
✓ Added .codex/prompts/
✓ Added .gemini/commands/
✓ Added .cursor/commands/
Updated .kittify/config.yaml
```

Error handling (invalid key):
```bash
spec-kitty agent config add cluade
```
Output:
```
Error: Invalid agent keys: cluade

Valid agent keys:
  claude, codex, gemini, cursor, qwen, opencode,
  windsurf, kilocode, roo, copilot, auggie, q
```

#### spec-kitty agent config remove

Remove one or more agents from your project.

**Synopsis**:
```bash
spec-kitty agent config remove [OPTIONS] <agent1> [agent2] [agent3] ...
```

**Description**:

Removes specified agents from your project by deleting agent directories and updating `.kittify/config.yaml`.

**Arguments**:

- `<agents>`: Space-separated list of agent keys to remove. Valid keys: same as `add` command.

**Options**:

- `--keep-config`: Keep agent in `config.yaml` but delete directory (default: False)

**Output**:

- Success: `✓ Removed <agent-dir>/` for each agent
- Already removed: `• <agent-dir>/ already removed` (dim, informational)
- Error: `Error: Invalid agent keys: <keys>` with list of valid keys

**Side Effects**:

- Deletes entire agent directory (e.g., `.gemini/` and all contents)
- Removes agent key from `.kittify/config.yaml` (unless `--keep-config` used)

**Warning**: Directory deletion is permanent. Ensure you don't have custom modifications in template files before removing.

**Examples**:

Remove a single agent:
```bash
spec-kitty agent config remove gemini
```

Remove multiple agents:
```bash
spec-kitty agent config remove cursor qwen windsurf
```

Example output:
```
✓ Removed .cursor/
✓ Removed .qwen/
✓ Removed .windsurf/
Updated .kittify/config.yaml
```

Keep in config but remove directory:
```bash
spec-kitty agent config remove gemini --keep-config
```

Restore later with:
```bash
spec-kitty agent config sync --create-missing
```

#### spec-kitty agent config status

Audit agent configuration sync status.

**Synopsis**:
```bash
spec-kitty agent config status
```

**Description**:

Displays a comprehensive table showing all 12 supported agents, whether they're configured, whether directories exist, and sync status.

**Arguments**: None

**Options**: None

**Output**:

Rich table with columns:
- **Agent Key** (cyan): Agent identifier
- **Directory** (dim): Filesystem path
- **Configured**: ✓ if in `config.yaml`, ✗ otherwise
- **Exists**: ✓ if directory present, ✗ otherwise
- **Status**: Colored status indicator

**Status values**:
- `[green]OK[/green]`: Configured and directory exists (normal state)
- `[yellow]Missing[/yellow]`: Configured but directory doesn't exist (needs sync)
- `[red]Orphaned[/red]`: Directory exists but not configured (should be cleaned up)
- `[dim]Not used[/dim]`: Neither configured nor present (available to add)

**Actionable message**: If orphaned directories detected, shows: `"Run 'spec-kitty agent config sync --remove-orphaned' to clean up"`

**Examples**:

Audit agent configuration:
```bash
spec-kitty agent config status
```

Example output:
```
Agent Key  Directory                Configured  Exists  Status
──────────────────────────────────────────────────────────────────
claude     .claude/commands/        ✓           ✓       OK
codex      .codex/prompts/          ✗           ✓       Orphaned
gemini     .gemini/commands/        ✓           ✗       Missing
cursor     .cursor/commands/        ✗           ✗       Not used
qwen       .qwen/commands/          ✓           ✓       OK
...

⚠ Found 1 orphaned directory
Run 'spec-kitty agent config sync --remove-orphaned' to clean up
```

#### spec-kitty agent config sync

Synchronize filesystem with config.yaml.

**Synopsis**:
```bash
spec-kitty agent config sync [OPTIONS]
```

**Description**:

Automatically aligns filesystem with `.kittify/config.yaml` by creating missing directories and/or removing orphaned directories.

**Arguments**: None

**Options**:

- `--create-missing`: Create directories for configured agents that are missing from filesystem (default: False)
- `--remove-orphaned` / `--keep-orphaned`: Remove orphaned directories (directories present but not configured). Default: `--remove-orphaned` (True)

**Default behavior** (no flags): Removes orphaned directories only. Does NOT create missing directories.

**Output**:

- Creating: `✓ Created <agent-dir>/<subdir>/`
- Removing: `✓ Removed orphaned <agent-dir>/`
- No changes: `No changes needed - filesystem matches config`

**Side Effects**:

- Creates agent directories with slash command templates (if `--create-missing`)
- Deletes orphaned agent directories (if `--remove-orphaned`, default)

**Examples**:

Default sync (remove orphaned only):
```bash
spec-kitty agent config sync
```

Create missing configured agents:
```bash
spec-kitty agent config sync --create-missing
```

Complete sync (both directions):
```bash
spec-kitty agent config sync --create-missing --remove-orphaned
```

Keep orphaned directories:
```bash
spec-kitty agent config sync --keep-orphaned
```

Example output:
```
✓ Created .claude/commands/
✓ Removed orphaned .gemini/
```

No changes needed:
```
No changes needed - filesystem matches config
```

#### spec-kitty agent config set

Set a project-level agent configuration value.

**Synopsis**:
```bash
spec-kitty agent config set KEY VALUE
```

**Description**:

Sets a project-level configuration value in `.kittify/config.yaml`. Currently supported keys: `auto_commit` (enable/disable automatic commits by agents, `true`/`false`).

**Arguments**:
- `KEY`: Configuration key (e.g., `auto_commit`) [required]
- `VALUE`: Configuration value (e.g., `true`, `false`) [required]

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Examples**:

Disable auto-commit:
```bash
spec-kitty agent config set auto_commit false
```

Enable auto-commit:
```bash
spec-kitty agent config set auto_commit true
```

---

### spec-kitty agent release

**Synopsis**: `spec-kitty agent release [OPTIONS] COMMAND [ARGS]...`

**Description**: Release management subcommands for AI agents.

**Commands**:
- `prep` - Prepare a release candidate (bump version, validate changelog, tag)

#### spec-kitty agent release prep

**Synopsis**: `spec-kitty agent release prep [OPTIONS]`

**Description**: Prepare a release candidate: validates `CHANGELOG.md`, bumps version in `pyproject.toml`, creates an annotated git tag, and optionally opens a GitHub release draft. Added in 3.1.0 (mission 068).

**Options**:
| Flag | Description |
| --- | --- |
| `--channel TEXT` | Release channel: `alpha`, `beta`, or `stable` (default: `stable`) |
| `--dry-run` | Show what would change without modifying files or creating a tag |
| `--json` | Machine-readable JSON output |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent release prep --channel alpha --dry-run
spec-kitty agent release prep --channel beta
spec-kitty agent release prep --channel stable
```

---

### spec-kitty agent tests

**Synopsis**: `spec-kitty agent tests [OPTIONS] COMMAND [ARGS]...`

**Description**: Test-suite utility subcommands for AI agents.

**Commands**:
- `stale-check` - Detect test assertions that reference version-dependent or environment-dependent values

#### spec-kitty agent tests stale-check

**Synopsis**: `spec-kitty agent tests stale-check [OPTIONS]`

**Description**: Scan the test suite for stale assertions: version strings, hardcoded timestamps, or environment-specific values that would cause false failures after a release. Uses `ast`-based analysis (no test execution required). Added in 3.1.0 (mission 068).

**Options**:
| Flag | Description |
| --- | --- |
| `--base TEXT` | Base git ref to diff against (default: `HEAD~1`) |
| `--head TEXT` | Head git ref to scan (default: `HEAD`) |
| `--json` | Machine-readable JSON output |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty agent tests stale-check
spec-kitty agent tests stale-check --base main --head HEAD
spec-kitty agent tests stale-check --json
```

---

## spec-kitty specify

**Synopsis**: `spec-kitty specify [OPTIONS] FEATURE`

**Description**: Create a feature scaffold in kitty-specs/.

**Arguments**:
- `FEATURE`: Feature name or slug (e.g., `user-authentication`) [required]

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Mission type (e.g., `software-dev`, `research`) |
| `--json` | Emit JSON result |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty specify user-authentication
spec-kitty specify user-authentication --mission software-dev
spec-kitty specify my-feature --json
```

---

## spec-kitty plan

**Synopsis**: `spec-kitty plan [OPTIONS]`

**Description**: Scaffold plan.md for a mission.

**Options**:
| Flag | Description |
| --- | --- |
| `--feature TEXT` | Mission slug (legacy flag name; e.g., `001-user-authentication`) |
| `--json` | Emit JSON result |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty plan
spec-kitty plan --feature 001-user-authentication
spec-kitty plan --json
```

---

## spec-kitty tasks

**Synopsis**: `spec-kitty tasks [OPTIONS]`

**Description**: Finalize tasks metadata after task generation.

**Options**:
| Flag | Description |
| --- | --- |
| `--json` | Emit JSON result |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty tasks
spec-kitty tasks --json
```

---

## spec-kitty config

**Synopsis**: `spec-kitty config [OPTIONS]`

**Description**: Display project configuration and asset resolution information.

**Options**:
| Flag | Description |
| --- | --- |
| `--show-origin` | Show where each resolved asset comes from (tier label + path) |
| `--mission`, `-m TEXT` | Mission to resolve assets for (default: `software-dev`) |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty config
spec-kitty config --show-origin
spec-kitty config -m documentation
```

---

## spec-kitty next

**Synopsis**: `spec-kitty next [OPTIONS]`

**Description**: Decide and emit the next agent action for the current mission. Agents call this command repeatedly in a loop. The system inspects the mission state machine, evaluates guards, and returns a deterministic decision with an action and prompt file.

The public contract distinguishes two forms:

- **Query mode**: `spec-kitty next --mission-run <slug> --json`
- **Advancing mode**: `spec-kitty next --agent <name> --mission-run <slug> [--result ...] --json`

Query mode is read-only and does not advance runtime state. On a fresh run, the canonical query JSON returns `mission_state: "not_started"` plus a non-null `preview_step`. `unknown` is no longer the canonical fresh-run query state.

**Options**:
| Flag | Description |
| --- | --- |
| `--agent TEXT` | Agent name for advancing mode. Query mode does not require it, but callers may still pass it as a compatibility form without changing query behavior. |
| `--result TEXT` | Result of previous step: `success`, `failed`, or `blocked`. If omitted, the command stays in read-only query mode. |
| `--mission-run TEXT` | Canonical mission-run selector for query and advancing mode |
| `--mission TEXT` | Compatibility alias for `--mission-run` |
| `--feature TEXT` | Legacy compatibility alias for `--mission-run` |
| `--json` | Output JSON decision only |
| `--answer TEXT` | Answer to a pending decision |
| `--decision-id TEXT` | Decision ID (required if multiple pending) |
| `--help` | Show this message and exit |

**Examples**:
```bash
# Query mode — inspect current state without advancing
spec-kitty next --mission-run 034-my-feature --json

# Compatibility query form (still read-only)
spec-kitty next --agent claude --mission-run 034-my-feature --json

# Advancing loop examples
spec-kitty next --agent codex --mission-run 034-my-feature --result success --json
spec-kitty next --agent gemini --mission-run 034-my-feature --result failed --json
spec-kitty next --agent claude --mission-run 034-my-feature --answer "yes" --json
spec-kitty next --agent claude --mission-run 034-my-feature --answer "approve" --decision-id "input:review" --json
```

**Compatibility notes**:

- Fresh-run query JSON is now `mission_state: "not_started"` plus `preview_step`; do not teach or depend on `unknown` as the primary fresh-run state.
- Query mode still accepts `--agent` as a compatibility form for existing callers, but `spec-kitty next --mission-run <slug>` is the primary contract to teach and automate against.
- Planning-artifact work packages execute in repository root outside the lane graph, so query and step responses may refer to the main checkout instead of a lane worktree.
- Status payloads use a canonical nested `stale` object. Temporary flat stale fields remain available only as a transitional compatibility path for existing callers.

---

## spec-kitty migrate

**Synopsis**: `spec-kitty migrate [OPTIONS]`

**Description**: Migrate project .kittify/ to centralized model. First ensures the global runtime (`~/.kittify/`) is up to date, then classifies per-project files as identical (removed), customized (moved to overrides/), or project-specific (kept). Running this command multiple times is safe (idempotent). After the first successful run, subsequent invocations are a near-instant no-op.

**Options**:
| Flag | Description |
| --- | --- |
| `--dry-run` | Show what would change without modifying the filesystem |
| `--verbose`, `-v` | Show file-by-file detail |
| `--force` | Skip confirmation prompt |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty migrate --dry-run
spec-kitty migrate --force
spec-kitty migrate --verbose
```

---

## spec-kitty auth

**Synopsis**: `spec-kitty auth [OPTIONS] COMMAND [ARGS]...`

**Description**: Authentication commands.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Commands**:
- `login` - Log in to the sync service
- `logout` - Log out from the sync service
- `status` - Show current authentication status

### spec-kitty auth login

**Synopsis**: `spec-kitty auth login [OPTIONS]`

**Description**: Log in to the sync service.

**Options**:
| Flag | Description |
| --- | --- |
| `--username`, `-u TEXT` | Your username or email |
| `--password`, `-p TEXT` | Your password |
| `--force`, `-f` | Re-authenticate even if already logged in |
| `--help` | Show this message and exit |

### spec-kitty auth logout

**Synopsis**: `spec-kitty auth logout [OPTIONS]`

**Description**: Log out from the sync service.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

### spec-kitty auth status

**Synopsis**: `spec-kitty auth status [OPTIONS]`

**Description**: Show current authentication status.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

---

## spec-kitty charter

**Synopsis**: `spec-kitty charter [OPTIONS] COMMAND [ARGS]...`

**Description**: Charter management commands. As of 3.1.0 (mission 063), `spec-kitty charter` is the canonical command. `spec-kitty constitution` has been removed; all existing `constitution` references should be updated to `charter`.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Commands**:
- `interview` - Capture charter interview answers for later generation
- `generate` - Generate charter bundle from interview answers + doctrine references
- `context` - Render charter context for a specific workflow action
- `sync` - Sync charter.md to structured YAML config files
- `status` - Display charter sync status

### spec-kitty charter interview

**Synopsis**: `spec-kitty charter interview [OPTIONS]`

**Description**: Capture charter interview answers for later generation.

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Mission key for charter defaults (default: `software-dev`) |
| `--profile TEXT` | Interview profile: `minimal` or `comprehensive` (default: `minimal`) |
| `--defaults` | Use deterministic defaults without prompts |
| `--selected-paradigms TEXT` | Comma-separated paradigm IDs override |
| `--selected-directives TEXT` | Comma-separated directive IDs override |
| `--available-tools TEXT` | Comma-separated tool IDs override |
| `--json` | Output JSON |
| `--help` | Show this message and exit |

### spec-kitty charter generate

**Synopsis**: `spec-kitty charter generate [OPTIONS]`

**Description**: Generate charter bundle from interview answers + doctrine references.

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Mission key for template-set defaults |
| `--template-set TEXT` | Override doctrine template set (must exist in packaged doctrine missions) |
| `--from-interview`, `--no-from-interview` | Load interview answers if present (default: `--from-interview`) |
| `--profile TEXT` | Default profile when no interview is available (default: `minimal`) |
| `--force`, `-f` | Overwrite existing charter bundle |
| `--json` | Output JSON |
| `--help` | Show this message and exit |

### spec-kitty charter context

**Synopsis**: `spec-kitty charter context [OPTIONS]`

**Description**: Render charter context for a specific workflow action.

**Options**:
| Flag | Description |
| --- | --- |
| `--action TEXT` | Workflow action (`specify`, `plan`, `implement`, `review`) [required] |
| `--mark-loaded`, `--no-mark-loaded` | Persist first-load state (default: `--mark-loaded`) |
| `--json` | Output JSON |
| `--help` | Show this message and exit |

### spec-kitty charter sync

**Synopsis**: `spec-kitty charter sync [OPTIONS]`

**Description**: Sync charter.md to structured YAML config files.

**Options**:
| Flag | Description |
| --- | --- |
| `--force`, `-f` | Force sync even if not stale |
| `--json` | Output JSON |
| `--help` | Show this message and exit |

### spec-kitty charter status

**Synopsis**: `spec-kitty charter status [OPTIONS]`

**Description**: Display charter sync status.

**Options**:
| Flag | Description |
| --- | --- |
| `--json` | Output JSON |
| `--help` | Show this message and exit |

---

## spec-kitty context

**Synopsis**: `spec-kitty context [OPTIONS] COMMAND [ARGS]...`

**Description**: Query workspace context information.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Commands**:
- `info` - Show context information for current or specified workspace
- `list` - List all workspace contexts
- `cleanup` - Clean up orphaned workspace contexts

### spec-kitty context info

**Synopsis**: `spec-kitty context info [OPTIONS]`

**Description**: Show context information for current or specified workspace.

**Options**:
| Flag | Description |
| --- | --- |
| `--workspace`, `-w TEXT` | Workspace name (auto-detected if inside worktree) |
| `--json` | Output in JSON format |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty context info
spec-kitty context info --workspace 010-feature-lane-a
spec-kitty context info --json
```

### spec-kitty context list

**Synopsis**: `spec-kitty context list [OPTIONS]`

**Description**: List all workspace contexts.

**Options**:
| Flag | Description |
| --- | --- |
| `--json` | Output in JSON format |
| `--orphaned` | Show only orphaned contexts |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty context list
spec-kitty context list --orphaned
spec-kitty context list --json
```

### spec-kitty context cleanup

**Synopsis**: `spec-kitty context cleanup [OPTIONS]`

**Description**: Clean up orphaned workspace contexts. Removes context files for workspaces that no longer exist.

**Options**:
| Flag | Description |
| --- | --- |
| `--dry-run` | Show what would be cleaned up without deleting |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty context cleanup --dry-run
spec-kitty context cleanup
```

---

## spec-kitty doctor

**Synopsis**: `spec-kitty doctor [OPTIONS] COMMAND [ARGS]...`

**Description**: Project health diagnostics. As of 3.1.0, running `spec-kitty doctor` (without a subcommand) also performs a full mission health scan: stale claims (WPs stuck in `claimed` or `in_progress` with no recent activity), orphaned worktrees (worktrees whose WPs are all terminal), and unresolved materialization drift. Use this as the first step when recovering from a crash or unexpected interruption.

```bash
# Full project health scan (3.1.0+)
spec-kitty doctor
spec-kitty doctor --mission 034-my-feature
```

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Restrict scan to a specific mission slug |
| `--json` | Machine-readable JSON output |
| `--help` | Show this message and exit |

**Commands**:
- `state-roots` - Show state roots, surface classification, and safety warnings

### spec-kitty doctor state-roots

**Synopsis**: `spec-kitty doctor state-roots [OPTIONS]`

**Description**: Show state roots, surface classification, and safety warnings. Displays the three state roots with resolved paths, all registered state surfaces grouped by root with authority and Git classification, and warnings for any runtime surfaces not covered by .gitignore.

**Options**:
| Flag | Description |
| --- | --- |
| `--json` | Machine-readable JSON output |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty doctor state-roots
spec-kitty doctor state-roots --json
```

---

## spec-kitty glossary

**Synopsis**: `spec-kitty glossary [OPTIONS] COMMAND [ARGS]...`

**Description**: Glossary management commands.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Commands**:
- `list` - List all terms in glossary
- `conflicts` - Display conflict history from event log
- `resolve` - Resolve a conflict asynchronously

### spec-kitty glossary list

**Synopsis**: `spec-kitty glossary list [OPTIONS]`

**Description**: List all terms in glossary.

**Options**:
| Flag | Description |
| --- | --- |
| `--scope TEXT` | Filter by scope (`mission_local`, `team_domain`, `audience_domain`, `spec_kitty_core`) |
| `--status TEXT` | Filter by status (`active`, `deprecated`, `draft`) |
| `--json` | Output as JSON (machine-parseable) |
| `--help` | Show this message and exit |

### spec-kitty glossary conflicts

**Synopsis**: `spec-kitty glossary conflicts [OPTIONS]`

**Description**: Display conflict history from event log.

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Filter conflicts by mission ID |
| `--unresolved` | Show only unresolved conflicts |
| `--strictness TEXT` | Filter by effective strictness level (`off`, `medium`, `max`) |
| `--json` | Output as JSON (machine-parseable) |
| `--help` | Show this message and exit |

### spec-kitty glossary resolve

**Synopsis**: `spec-kitty glossary resolve [OPTIONS] CONFLICT_ID`

**Description**: Resolve a conflict asynchronously.

**Arguments**:
- `CONFLICT_ID`: Conflict ID to resolve [required]

**Options**:
| Flag | Description |
| --- | --- |
| `--mission TEXT` | Mission ID for event log (auto-detected if omitted) |
| `--help` | Show this message and exit |

---

## spec-kitty tracker

**Synopsis**: `spec-kitty tracker [OPTIONS] COMMAND [ARGS]...`

**Description**: Task tracker commands.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Commands**:
- `providers` - List supported tracker providers
- `bind` - Bind the current project to a tracker
- `status` - Show tracker binding and sync status
- `unbind` - Remove tracker binding for this project
- `map` - Work-package mapping commands
- `sync` - Tracker synchronization commands

### spec-kitty tracker providers

**Synopsis**: `spec-kitty tracker providers [OPTIONS]`

**Description**: List supported tracker providers, grouped into SaaS-backed (`linear`, `jira`, `github`, `gitlab`) and local/native (`beads`, `fp`) modes.

**Options**:
| Flag | Description |
| --- | --- |
| `--json` | Render provider list as JSON |
| `--help` | Show this message and exit |

### spec-kitty tracker bind

**Synopsis**: `spec-kitty tracker bind [OPTIONS]`

**Description**: Bind the current project to a tracker. SaaS-backed providers require `--project-slug` and authenticate through `spec-kitty auth login`; local/native providers require `--workspace` and may accept `--credential`.

**Options**:
| Flag | Description |
| --- | --- |
| `--provider TEXT` | Provider name (`linear`, `jira`, `github`, `gitlab`, `beads`, `fp`) [required] |
| `--project-slug TEXT` | SaaS project identifier used for control-plane routing (SaaS-backed providers only) |
| `--workspace TEXT` | Provider workspace/team/project identifier (local/native providers only) |
| `--doctrine-mode TEXT` | Doctrine mode: `external_authoritative`, `spec_kitty_authoritative`, or `split_ownership` (default: `external_authoritative`) |
| `--field-owner TEXT` | Split ownership mapping: `field=owner` (local/native providers only) |
| `--credential TEXT` | Provider credential key/value: `key=value` (local/native providers only) |
| `--help` | Show this message and exit |

### spec-kitty tracker status

**Synopsis**: `spec-kitty tracker status [OPTIONS]`

**Description**: Show tracker binding and sync status. SaaS-backed providers read status from the Spec Kitty SaaS control plane; local/native providers show local config and cache details.

**Options**:
| Flag | Description |
| --- | --- |
| `--json` | Render status as JSON |
| `--help` | Show this message and exit |

### spec-kitty tracker unbind

**Synopsis**: `spec-kitty tracker unbind [OPTIONS]`

**Description**: Remove tracker binding for this project. For SaaS-backed providers this clears only local project config; unlinking the provider account still happens in the Spec Kitty dashboard.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

### spec-kitty tracker map

**Synopsis**: `spec-kitty tracker map [OPTIONS] COMMAND [ARGS]...`

**Description**: Work-package mapping commands.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Commands**:
- `add` - Add or update a WP-to-external issue mapping
- `list` - List tracker mappings

#### spec-kitty tracker map add

**Synopsis**: `spec-kitty tracker map add [OPTIONS]`

**Description**: Add or update a WP-to-external issue mapping. For SaaS-backed providers this command hard-fails and directs you to the Spec Kitty dashboard, where mappings are managed server-side.

**Options**:
| Flag | Description |
| --- | --- |
| `--wp-id TEXT` | Work package ID (e.g., `WP01`) [required] |
| `--external-id TEXT` | External issue ID [required] |
| `--external-key TEXT` | External issue key |
| `--external-url TEXT` | External issue URL |
| `--help` | Show this message and exit |

#### spec-kitty tracker map list

**Synopsis**: `spec-kitty tracker map list [OPTIONS]`

**Description**: List tracker mappings. For SaaS-backed providers this reads the SaaS-authoritative mapping view; for local/native providers it reads the local mapping store.

**Options**:
| Flag | Description |
| --- | --- |
| `--json` | Render mappings as JSON |
| `--help` | Show this message and exit |

### spec-kitty tracker sync

**Synopsis**: `spec-kitty tracker sync [OPTIONS] COMMAND [ARGS]...`

**Description**: Tracker synchronization commands.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Commands**:
- `pull` - Pull tracker updates into the local cache
- `push` - Push explicit tracker mutations to the upstream provider
- `run` - Run pull+push synchronization in one operation
- `publish` - Legacy snapshot publish command

#### spec-kitty tracker sync pull

**Synopsis**: `spec-kitty tracker sync pull [OPTIONS]`

**Description**: Pull tracker updates into the local cache.

**Options**:
| Flag | Description |
| --- | --- |
| `--limit INTEGER` | Maximum items to pull (default: 100, range: 1-10000) |
| `--json` | Render sync result as JSON |
| `--help` | Show this message and exit |

#### spec-kitty tracker sync push

**Synopsis**: `spec-kitty tracker sync push [OPTIONS]`

**Description**: Push explicit tracker mutations to the upstream provider. For SaaS-backed providers this is an explicit-mutation path and requires `--items-json`; use `tracker sync run` for the normal full-sync path.

**Options**:
| Flag | Description |
| --- | --- |
| `--limit INTEGER` | Maximum items to push (local/native providers only; default: 100, range: 1-10000) |
| `--items-json TEXT` | Path to a JSON file containing a `PushItem[]` array for SaaS-backed providers. Use `-` for stdin |
| `--json` | Render sync result as JSON |
| `--help` | Show this message and exit |

#### spec-kitty tracker sync run

**Synopsis**: `spec-kitty tracker sync run [OPTIONS]`

**Description**: Run pull+push synchronization in one operation. For SaaS-backed providers this is the normal full-sync path executed entirely through Spec Kitty SaaS.

**Options**:
| Flag | Description |
| --- | --- |
| `--limit INTEGER` | Maximum items per direction (default: 100, range: 1-10000) |
| `--json` | Render sync result as JSON |
| `--help` | Show this message and exit |

#### spec-kitty tracker sync publish

**Synopsis**: `spec-kitty tracker sync publish [OPTIONS]`

**Description**: Publish a local tracker snapshot to Spec Kitty SaaS. This command is retired for SaaS-backed providers and fails with guidance to use `tracker sync push` or `tracker sync run` instead.

**Options**:
| Flag | Description |
| --- | --- |
| `--server-url TEXT` | Spec Kitty SaaS base URL |
| `--auth-token TEXT` | Bearer token for SaaS API authentication |
| `--timeout-seconds FLOAT` | Request timeout in seconds (default: 10.0, range: 1.0-120.0) |
| `--json` | Render publish result as JSON |
| `--help` | Show this message and exit |

---

## Lane Values

The Spec Kitty status model uses 7 lanes plus one alias:

| Lane | Description |
| --- | --- |
| `planned` | Work package is planned but not started |
| `claimed` | Work package has been claimed by an agent |
| `in_progress` | Work package is actively being implemented |
| `for_review` | Work package is submitted for review |
| `approved` | Work package has been approved |
| `done` | Work package is complete (terminal) |
| `blocked` | Work package is blocked (reachable from planned/claimed/in_progress/for_review) |
| `canceled` | Work package is canceled (terminal, reachable from all non-done lanes) |

> **Note**: `doing` is accepted as an alias for `in_progress` at input boundaries but is never persisted in events.

---

## Getting Started
- [Claude Code Integration](../tutorials/claude-code-integration.md)
- [Claude Code Workflow](../tutorials/claude-code-workflow.md)

## Practical Usage
- [Install Spec Kitty](../how-to/install-spec-kitty.md)
- [Use the Dashboard](../how-to/use-dashboard.md)
- [Upgrade to 0.11.0](../how-to/install-and-upgrade.md)
