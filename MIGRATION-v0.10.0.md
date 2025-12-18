# Migration Guide: v0.9.x → v0.10.0 (Bash to Python)

## Overview

Version 0.10.0 removes all bash and PowerShell wrapper scripts in favor of a unified Python CLI under the `spec-kitty agent` namespace. This migration guide helps you update custom workflows and scripts that may reference the old bash commands.

## What Changed

### Removed Scripts

All bash scripts previously in `.kittify/scripts/bash/` and `.kittify/scripts/powershell/` have been removed:

- `create-new-feature.sh` / `create-new-feature.ps1`
- `check-prerequisites.sh` / `check-prerequisites.ps1`
- `setup-plan.sh` / `setup-plan.ps1`
- `update-agent-context.sh` / `update-agent-context.ps1`
- `accept-feature.sh` / `accept-feature.ps1`
- `merge-feature.sh` / `Merge-Feature.ps1`
- `tasks-move-to-lane.sh` / `tasks-move-to-lane.ps1`
- `tasks-list-lanes.sh` / `tasks-list-lanes.ps1`
- `mark-task-status.sh` / `Set-TaskStatus.ps1`
- `tasks-add-history-entry.sh` / `tasks-add-history-entry.ps1`
- `tasks-rollback-move.sh` / `tasks-rollback-move.ps1`
- `validate-task-workflow.sh`
- `move-task-to-doing.sh`
- `common.sh` / `common.ps1`

### New Python CLI Commands

All functionality is now available through `spec-kitty agent` commands:

| Old Bash Script | New Python Command |
|----------------|-------------------|
| `.kittify/scripts/bash/create-new-feature.sh` | `spec-kitty agent create-feature` |
| `.kittify/scripts/bash/check-prerequisites.sh` | `spec-kitty agent check-prerequisites` |
| `.kittify/scripts/bash/setup-plan.sh` | `spec-kitty agent setup-plan` |
| `.kittify/scripts/bash/update-agent-context.sh` | `spec-kitty agent update-context` |
| `.kittify/scripts/bash/accept-feature.sh` | `spec-kitty agent feature accept` |
| `.kittify/scripts/bash/merge-feature.sh` | `spec-kitty agent feature merge` |
| `.kittify/scripts/bash/tasks-move-to-lane.sh` | `spec-kitty agent move-task` |
| `.kittify/scripts/bash/tasks-list-lanes.sh` | `spec-kitty agent list-tasks` |
| `.kittify/scripts/bash/mark-task-status.sh` | `spec-kitty agent mark-status` |
| `.kittify/scripts/bash/tasks-add-history-entry.sh` | `spec-kitty agent add-history` |
| `.kittify/scripts/bash/tasks-rollback-move.sh` | `spec-kitty agent rollback-move` |
| `.kittify/scripts/bash/validate-task-workflow.sh` | `spec-kitty agent validate-workflow` |
| `.kittify/scripts/bash/move-task-to-doing.sh` | `spec-kitty agent move-task --to doing` |

## Automatic Migration

Run the upgrade command to automatically migrate your project:

```bash
spec-kitty upgrade
```

This will:
1. Remove bash scripts from `.kittify/scripts/bash/`
2. Remove PowerShell scripts from `.kittify/scripts/powershell/`
3. Update all slash command templates to use Python CLI
4. Clean up bash scripts in all worktrees

The migration is **idempotent** - safe to run multiple times.

### Dry Run

Preview changes without applying them:

```bash
spec-kitty upgrade --dry-run
```

## Manual Migration

If you have custom scripts or workflows that reference the old bash commands, update them manually:

### Example 1: Feature Creation

**Old:**
```bash
.kittify/scripts/bash/create-new-feature.sh --json --feature-name "Payment Flow"
```

**New:**
```bash
spec-kitty agent create-feature --json --feature-name "Payment Flow"
```

### Example 2: Task Movement

**Old:**
```bash
.kittify/scripts/bash/tasks-move-to-lane.sh WP01 doing --agent claude --note "Started"
```

**New:**
```bash
spec-kitty agent move-task WP01 --to doing --agent claude --note "Started"
```

### Example 3: Acceptance

**Old:**
```bash
.kittify/scripts/bash/accept-feature.sh --json
```

**New:**
```bash
spec-kitty agent feature accept --json
```

### Example 4: Task Validation

**Old:**
```bash
.kittify/scripts/bash/validate-task-workflow.sh WP01 kitty-specs/001-feature
```

**New:**
```bash
spec-kitty agent validate-workflow WP01 --json
```

## Benefits of Python CLI

### Consistent Interface
- All commands follow the same option syntax
- `--json` flag available on all commands for programmatic use
- Unified error handling and output formatting

### Cross-Platform
- Works identically on Windows, macOS, and Linux
- No need to maintain separate bash and PowerShell versions
- Python environment already required by spec-kitty

### Better Error Messages
- Rich console output with color and formatting
- Detailed error messages with actionable suggestions
- JSON output for agent consumption

### Easier Testing
- Full test coverage with pytest
- Integration tests for all workflows
- Easier to debug and maintain

## Troubleshooting

### Command Not Found

If you get `spec-kitty: command not found`:

1. Ensure spec-kitty is installed: `pip install spec-kitty-cli`
2. Verify installation: `spec-kitty --version`
3. Check PATH includes pip installation directory

### Old Scripts Still Referenced

If slash commands still reference old scripts:

1. Run upgrade: `spec-kitty upgrade`
2. Check for custom modifications: The migration warns about non-standard scripts
3. Manually update any custom templates in your project

### Custom Bash Scripts

If you've created custom bash scripts that use `common.sh` utilities:

The `common.sh` functions are no longer available. Consider:

1. **Rewrite in Python**: Use the spec-kitty Python API
2. **Use Agent Commands**: Call `spec-kitty agent` commands from your scripts
3. **Extract Logic**: Copy needed utilities to your own script

Example of calling agent commands from a custom script:

```bash
#!/bin/bash
# Custom workflow using Python CLI

FEATURE=$(spec-kitty agent check-prerequisites --json | jq -r '.feature_slug')

spec-kitty agent move-task WP01 --to doing --json
# ... your custom logic ...
spec-kitty agent move-task WP01 --to for_review --json
```

## Migration Checklist

- [ ] Run `spec-kitty upgrade` on all projects
- [ ] Test slash commands (`/spec-kitty.specify`, `/spec-kitty.implement`, etc.)
- [ ] Update any custom shell scripts that reference bash wrappers
- [ ] Update CI/CD pipelines that call bash scripts
- [ ] Update documentation that references old script paths
- [ ] Remove any git hooks that reference `.kittify/scripts/bash/`
- [ ] Test worktree workflows (create, move tasks, accept, merge)

## Getting Help

If you encounter issues during migration:

1. Check the [GitHub Issues](https://github.com/Priivacy-ai/spec-kitty/issues) for known problems
2. Run `spec-kitty upgrade --verbose` for detailed migration output
3. File a bug report with the `--json` output from your failing command

## Rollback

If you need to temporarily rollback:

```bash
pip install spec-kitty-cli==0.9.1
```

Note: Future versions will not support bash scripts. Please report any migration issues so we can address them.
