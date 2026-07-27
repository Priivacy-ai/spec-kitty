# Quickstart: Frontmatter-Only Lane Management

## Overview

This feature refactors Spec Kitty's lane management from directory-based to frontmatter-only. After implementation:

- All WP files live in flat `tasks/` directory
- The `lane:` YAML frontmatter field is the single source of truth
- The `move` command is renamed to `update`
- No backwards compatibility - migration required for existing projects

## For Developers

### Changed Commands

| Old Command | New Command | Notes |
|-------------|-------------|-------|
| `tasks_cli.py move <feature> <wp> <lane>` | `tasks_cli.py update <feature> <wp> <lane>` (deprecated) | No file movement, frontmatter only (now use `spec-kitty agent workflow`) |
| `tasks_cli.py list <feature>` | `tasks_cli.py list <feature>` | Now scans flat directory |
| `tasks_cli.py status [feature]` | `tasks_cli.py status [feature]` | Groups by frontmatter lane |

### Migration

If you have an existing project with directory-based lanes:

```bash
spec-kitty upgrade
```

This will:
1. Find all features in `kitty-specs/` and `.worktrees/*/kitty-specs/`
2. Move WP files from `tasks/{lane}/` to flat `tasks/`
3. Preserve `lane:` frontmatter from source directory
4. Remove empty lane subdirectories

### Direct Lane Editing

You can now directly edit the `lane:` field in WP frontmatter:

```yaml
---
work_package_id: "WP01"
lane: "for_review"  # Change this directly
---
```

This is now the **recommended approach** for AI agents.

## For AI Agents

### Lane Updates

To change a work package's lane:

**Option 1**: Use the update command
```bash
spec-kitty agent workflow review WP01
```

**Option 2**: Edit frontmatter directly
```yaml
# In tasks/WP01-description.md
---
lane: "for_review"  # Changed from "doing"
activity_log: |
  - 2025-12-17T10:00:00Z – agent-001 – lane=doing – Started
  - 2025-12-17T14:30:00Z – agent-001 – lane=for_review – Ready for review
---
```

### Valid Lanes

- `planned` - Work defined but not started
- `doing` - Work in progress
- `for_review` - Implementation complete, awaiting review
- `done` - Reviewed and accepted

### Legacy Format Detection

If you see this error:
```
Error: Legacy directory-based lanes detected.
Run 'spec-kitty upgrade' to migrate to frontmatter-only lanes.
```

The project needs migration. Run `spec-kitty upgrade` first.

## Key Files Changed

| File | Change |
|------|--------|
| `scripts/tasks/tasks_cli.py` | `move` → `update`, no file movement |
| `scripts/tasks/task_helpers.py` | `locate_work_package()` searches flat `tasks/` |
| `src/specify_cli/dashboard/scanner.py` | Reads lane from frontmatter |
| `src/specify_cli/commands/upgrade.py` | NEW: Migration command |
| `src/specify_cli/legacy_detector.py` | NEW: Old format detection |

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_tasks_cli_commands.py -v

# Run migration tests
pytest tests/test_migration.py -v
```
