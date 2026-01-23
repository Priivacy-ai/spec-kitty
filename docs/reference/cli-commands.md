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
- `ops` - Operation history and undo (jj: full undo, git: reflog only)
- `research` - Execute Phase 0 research workflow to scaffold artifacts
- `upgrade` - Upgrade a Spec Kitty project to the current version
- `list-legacy-features` - List legacy worktrees blocking 0.11.0 upgrade
- `validate-encoding` - Validate and optionally fix file encoding in feature artifacts
- `validate-tasks` - Validate and optionally fix task metadata inconsistencies
- `verify-setup` - Verify that the current environment matches Spec Kitty expectations
- `agent` - Commands for AI agents to execute spec-kitty workflows programmatically
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
| `--vcs TEXT` | VCS to use: `git` or `jj`. Defaults to jj if available, otherwise git |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty init my-project
spec-kitty init my-project --ai codex
spec-kitty init my-project --ai codex,claude --script sh --mission software-dev
spec-kitty init . --ai codex --force
spec-kitty init --here --ai claude
spec-kitty init my-project --vcs git
```

**VCS Detection Order**: Spec Kitty selects the VCS backend in this order:
1. **Explicit backend (CLI flag)**: `spec-kitty init --vcs git` or `--vcs jj`
   - If a feature has a locked VCS that conflicts, **raises an error** (does not silently override)
2. **Feature meta.json**: If the path is within a feature, use its locked `vcs` field
3. **jj preferred**: If `jj` is installed and meets requirements, use jj
4. **git fallback**: Use git if available

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

## spec-kitty sync

**Synopsis**: `spec-kitty sync [OPTIONS]`

**Description**: Synchronize workspace with upstream changes. Updates the current workspace with changes from its base branch or parent. This is equivalent to:
- **git**: `git rebase <base-branch>`
- **jj**: `jj workspace update-stale` + auto-rebase

**Options**:
| Flag | Description |
| --- | --- |
| `--repair`, `-r` | Attempt workspace recovery (may lose uncommitted work) |
| `--verbose`, `-v` | Show detailed sync output |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty sync
spec-kitty sync --verbose
spec-kitty sync --repair
```

> **jj vs git**: Sync behavior differs between VCS backends:
> - **jj**: Sync always **succeeds**. Conflicts are stored in the working copy and can be resolved later. Auto-rebase handles dependent changes automatically.
> - **git**: Sync may **fail** on conflicts. You must resolve conflicts before continuing.

**See Also**: [Sync Workspaces](../how-to/sync-workspaces.md)

---

## spec-kitty ops

**Synopsis**: `spec-kitty ops COMMAND [ARGS]...`

**Description**: Operation history and undo capability. View operation logs and restore previous states.

> **Note**: Full undo/restore functionality is only available with jj. Git provides limited functionality via reflog.

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Commands**:
- `log` - Show operation history
- `undo` - Undo last operation (jj only)
- `restore` - Restore to a specific operation (jj only)

### spec-kitty ops log

**Synopsis**: `spec-kitty ops log [OPTIONS]`

**Description**: Show operation history. Displays recent operations that have modified the repository state.

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

> **jj vs git**: Operation log differs between backends:
> - **jj**: Shows jj operation log with timestamps and operation IDs
> - **git**: Shows git reflog entries

### spec-kitty ops undo

**Synopsis**: `spec-kitty ops undo [OPTIONS] [OPERATION_ID]`

**Description**: Undo the last operation or a specific operation.

> **jj only**: This command is only available when using jujutsu. Git does not support operation undo.

**Arguments**:
- `OPERATION_ID`: Operation ID to undo (optional, defaults to last operation)

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty ops undo
spec-kitty ops undo abc123
```

### spec-kitty ops restore

**Synopsis**: `spec-kitty ops restore OPERATION_ID`

**Description**: Restore repository to a specific operation state. Unlike undo (which reverses the last operation), restore jumps directly to any previous operation state.

> **jj only**: This command is only available when using jujutsu. Git does not support operation restore.

**Arguments**:
- `OPERATION_ID`: Operation ID to restore to (required)

**Options**:
| Flag | Description |
| --- | --- |
| `--help` | Show this message and exit |

**Examples**:
```bash
spec-kitty ops restore abc123def456
```

**See Also**: [Use Operation History](../how-to/use-operation-history.md)

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

## Getting Started
- [Claude Code Integration](../tutorials/claude-code-integration.md)
- [Claude Code Workflow](../tutorials/claude-code-workflow.md)

## Practical Usage
- [Install Spec Kitty](../how-to/install-spec-kitty.md)
- [Use the Dashboard](../how-to/use-dashboard.md)
- [Upgrade to 0.11.0](../how-to/upgrade-to-0-11-0.md)
