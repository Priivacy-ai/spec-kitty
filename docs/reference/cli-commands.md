# CLI Command Reference

This reference lists the user-facing `spec-kitty` CLI commands and their flags exactly as surfaced by `--help`. For agent-only commands, see `docs/reference/agent-subcommands.md`.

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
- `accept` - Validate feature readiness before merging to main
- `dashboard` - Open or stop the Spec Kitty dashboard
- `implement` - Create workspace for work package implementation
- `merge` - Merge a completed feature branch into the target branch and clean up resources
- `sync` - Synchronize workspace with upstream changes
- `ops` - Operation history and undo (git reflog)
- `research` - Execute Phase 0 research workflow to scaffold artifacts
- `upgrade` - Upgrade a Spec Kitty project to the current version
- `list-legacy-features` - List legacy worktrees blocking 0.11.0 upgrade
- `validate-encoding` - Validate and optionally fix file encoding in feature artifacts
- `validate-tasks` - Validate and optionally fix task metadata inconsistencies
- `verify-setup` - Verify that the current environment matches Spec Kitty expectations
- `agent` - Commands for AI agents to execute spec-kitty workflows programmatically
- `auth` - Authentication commands for the sync service
- `mission` - View available Spec Kitty missions
- `repair` - Repair broken templates

---

## spec-kitty init

**Synopsis**: `spec-kitty init [OPTIONS] [PROJECT_NAME]`

**Description**: Initialize a new Spec Kitty project from templates.

**Arguments**:
- `PROJECT_NAME`: Name for your new project directory (optional if using `--here`, or use `.` for current directory)

**Options**:
| Flag | Description |
| --- | --- |
| `--ignore-agent-tools` | Skip checks for AI agent tools like Claude Code |
| `--no-git` | Skip git repository initialization |
| `--here` | Initialize project in the current directory instead of creating a new one |
| `--force` | Force merge/overwrite when using `--here` (skip confirmation) |
| `--skip-tls` | Skip SSL/TLS verification (not recommended) |
| `--debug` | Show verbose diagnostic output for network and extraction failures |
| `--github-token TEXT` | GitHub token to use for API requests (or set `GH_TOKEN`/`GITHUB_TOKEN`) |
| `--template-root TEXT` | Override default template location (useful for development mode) |
| `--ai TEXT` | Comma-separated AI assistants (claude,codex,gemini,...) |
| `--script TEXT` | Script type to use: `sh` or `ps` |
| `--agent-strategy TEXT` | Agent selection strategy: `preferred` or `random` |
| `--preferred-implementer TEXT` | Preferred agent for implementation (preferred strategy only) |
| `--preferred-reviewer TEXT` | Preferred agent for review (preferred strategy only) |
| `--non-interactive` / `--yes` | Disable prompts (CI/CD) |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty init my-project
spec-kitty init my-project --ai codex
spec-kitty init my-project --ai codex,claude --script sh
spec-kitty init . --ai codex --force
spec-kitty init --here --ai claude
spec-kitty init my-project --ai codex --agent-strategy random --non-interactive
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
| `--base TEXT` | Base WP to branch from (e.g., `WP01`) |
| `--feature TEXT` | Feature slug (e.g., `001-my-feature`) |
| `--json` | Output in JSON format |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty implement WP01
spec-kitty implement WP02 --base WP01
spec-kitty implement WP01 --feature 001-my-feature
spec-kitty implement WP01 --json
```

---

## spec-kitty accept

**Synopsis**: `spec-kitty accept [OPTIONS]`

**Description**: Validate feature readiness before merging to main.

**Options**:
| Flag | Description |
| --- | --- |
| `--feature TEXT` | Feature slug to accept (auto-detected by default) |
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

**Description**: Merge a completed feature branch into the target branch and clean up resources.

**Options**:
| Flag | Description |
| --- | --- |
| `--strategy TEXT` | Merge strategy: `merge`, `squash`, or `rebase` (default: `merge`) |
| `--delete-branch`, `--keep-branch` | Delete or keep feature branch after merge (default: delete) |
| `--remove-worktree`, `--keep-worktree` | Remove or keep feature worktree after merge (default: remove) |
| `--push` | Push to origin after merge |
| `--target TEXT` | Target branch to merge into (default: `main`) |
| `--dry-run` | Show what would be done without executing |
| `--help` | Show this message and exit |

---

## spec-kitty dashboard

**Synopsis**: `spec-kitty dashboard [OPTIONS]`

**Description**: Open or stop the Spec Kitty dashboard.

**Options**:
| Flag | Description |
| --- | --- |
| `--port INTEGER` | Preferred port for the dashboard (falls back to first available port) |
| `--kill` | Stop the running dashboard for this project and clear its metadata |
| `--help` | Show this message and exit |

---

## spec-kitty research

**Synopsis**: `spec-kitty research [OPTIONS]`

**Description**: Execute Phase 0 research workflow to scaffold artifacts.

**Options**:
| Flag | Description |
| --- | --- |
| `--feature TEXT` | Feature slug to target (auto-detected when omitted) |
| `--force` | Overwrite existing research artifacts |
| `--help` | Show this message and exit |

---

## spec-kitty auth

**Synopsis**: `spec-kitty auth [OPTIONS] COMMAND [ARGS]...`

**Description**: Authentication commands for the spec-kitty sync service.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Commands**:
- `login` - Log in to the sync service
- `logout` - Log out from the sync service
- `status` - Show current authentication status

---

## spec-kitty auth login

**Synopsis**: `spec-kitty auth login [OPTIONS]`

**Description**: Log in to the sync service. Prompts for username and password if not provided via flags. Stores JWT tokens in credential file.

**Options**:
| Flag | Type | Default | Description |
| --- | --- | --- | --- |
| `--username`, `-u` | TEXT | (prompt) | Your username or email |
| `--password`, `-p` | TEXT | (prompt, hidden) | Your password |
| `--force`, `-f` | FLAG | false | Re-authenticate even if already logged in |
| `--help` | | | Show this message and exit |

**Examples**:
```bash
# Interactive login (prompts for credentials)
spec-kitty auth login

# Non-interactive login
spec-kitty auth login --username user@example.com --password secret

# Force re-authentication
spec-kitty auth login --force
```

**Behavior**:
- On success, prints the authenticated username and stores JWT tokens in `~/.spec-kitty/credentials`.
- If already authenticated (without `--force`), prints a message and exits without re-authenticating.

**Errors**:
- Invalid credentials: `Invalid username or password`
- Server unreachable: `Cannot reach server. Check your connection.`
- Server error: `Server temporarily unavailable`
- Session expired: `Session expired. Please log in again.`
- Permission error: `Cannot access credentials file. Check permissions.`

---

## spec-kitty auth logout

**Synopsis**: `spec-kitty auth logout`

**Description**: Log out from the sync service. Clears stored credentials.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty auth logout
```

**Behavior**:
- On success, clears credentials and prints the username that was logged out.
- If no active session exists, prints an informational message and exits.

**Errors**:
- Permission error: `Cannot access credentials file. Check permissions.`

---

## spec-kitty auth status

**Synopsis**: `spec-kitty auth status`

**Description**: Show current authentication status including username, server URL, and token expiry.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty auth status
```

**Output** (authenticated):
```
✅ Authenticated
   Username: user@example.com
   Server:   https://your-server.example.com
   Access token: valid (23h remaining)
   Refresh token: valid (6d remaining)
```

**Output** (not authenticated):
```
❌ Not authenticated
   Run 'spec-kitty auth login' to authenticate.
```

**Errors**:
- Permission error: `Cannot access credentials file. Check permissions.`

---

## spec-kitty sync

**Synopsis**: `spec-kitty sync [OPTIONS] COMMAND [ARGS]...`

**Description**: Synchronization commands for workspaces and server connectivity.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Commands**:
- `workspace` - Sync workspace with upstream changes (local)
- `now` - Push and pull events with the server (remote)
- `status` - Show sync configuration and connection state

---

## spec-kitty sync workspace

**Synopsis**: `spec-kitty sync workspace [OPTIONS]`

**Description**: Synchronize the current workspace with upstream changes. Updates the current workspace with changes from its base branch or parent using `git rebase <base-branch>`.

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

> **Note**: Sync may fail on conflicts. You must resolve conflicts before continuing.

**See Also**: [Sync Workspaces](../how-to/sync-workspaces.md)

---

## spec-kitty sync now

**Synopsis**: `spec-kitty sync now [OPTIONS]`

**Description**: Push locally queued events to the server and pull new events. This drains the offline queue and synchronizes with the team's server.

> **Note**: This command reference is based on the planned interface. Verify against `spec-kitty sync now --help` when the command is available.

**Options**:
| Flag | Type | Default | Description |
| --- | --- | --- | --- |
| `--verbose`, `-v` | FLAG | false | Show per-event sync status |
| `--dry-run`, `-n` | FLAG | false | Show what would be synced without syncing |
| `--help` | | | Show this message and exit |

**Examples**:
```bash
# Push all queued events and pull updates
spec-kitty sync now

# See what would be synced
spec-kitty sync now --dry-run

# Verbose output
spec-kitty sync now --verbose
```

**Behavior**:
- Drains the offline queue (up to 1000 events per request) and uploads events in a single batch request with gzip compression.
- Successfully synced events are removed from the queue.
- Duplicate events on the server are counted but not treated as errors.

---

## spec-kitty sync status

**Synopsis**: `spec-kitty sync status [OPTIONS]`

**Description**: Show WebSocket sync connection status and server configuration.

**Options**:
| Flag | Type | Default | Description |
| --- | --- | --- | --- |
| `--check`, `-c` | FLAG | false | Test connection to server (may be slow if unreachable) |
| `--help` | | | Show this message and exit |

**Examples**:
```bash
# Show configuration only (fast)
spec-kitty sync status

# Test actual connectivity
spec-kitty sync status --check
```

**Output**:
- **Server URL**: Configured sync server address
- **Config File**: Path to the sync configuration file
- **Connection** (with `--check`): Tests actual server connectivity with a 3-second timeout

**Connection states** (with `--check`):
- **Connected**: Successfully reached the server
- **Reachable**: Server is online but authentication is required
- **Unreachable**: Connection timeout or refused
- **Error**: Connection test failed

---

## spec-kitty ops

**Synopsis**: `spec-kitty ops COMMAND [ARGS]...`

**Description**: Operation history via git reflog. View recent git operations.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Commands**:
- `log` - Show operation history (git reflog)

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
| `--feature TEXT` | Feature slug to validate (auto-detected when omitted) |
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
| `--feature TEXT` | Feature slug to validate (auto-detected when omitted) |
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
| `--feature TEXT` | Feature slug to verify (auto-detected when omitted) |
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

### spec-kitty repair repair

**Synopsis**: `spec-kitty repair repair [OPTIONS]`

**Description**: Repair broken templates caused by v0.10.0-0.10.8 bundling bug.

**Options**:
| Flag | Description |
| --- | --- |
| `--project-path PATH`, `-p` | Path to project to repair |
| `--dry-run` | Show what would be changed without making changes |
| `--help` | Show this message and exit |

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
| `list` | View configured agents and available options |
| `add` | Add one or more agents to your project |
| `remove` | Remove one or more agents from your project |
| `status` | Audit agent configuration sync status |
| `sync` | Synchronize filesystem with config.yaml |

**See also**: [Managing AI Agents](../how-to/manage-agents.md) for task-oriented guidance on agent management workflows.

> **Note**: Starting in 0.12.0, agent configuration is config-driven. `.kittify/config.yaml` is the single source of truth, and migrations respect your configuration choices. See [Upgrading to 0.12.0](../how-to/upgrade-to-0-11-0.md#upgrading-to-0120) for migration details.

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

---

## Getting Started
- [Claude Code Integration](../tutorials/claude-code-integration.md)
- [Claude Code Workflow](../tutorials/claude-code-workflow.md)

## Practical Usage
- [Install Spec Kitty](../how-to/install-spec-kitty.md)
- [Use the Dashboard](../how-to/use-dashboard.md)
- [Upgrade to 0.11.0](../how-to/upgrade-to-0-11-0.md)
