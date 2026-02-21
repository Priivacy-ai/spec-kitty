# Quickstart: Enhanced Merge Command

Quick reference for the improved `spec-kitty merge` command.

## Basic Usage

```bash
# Merge all WPs for current feature (default)
spec-kitty merge

# Preview what will happen
spec-kitty merge --dry-run

# Merge and push to origin
spec-kitty merge --push
```

## New Features

### Pre-flight Validation

The merge command now checks ALL worktrees before starting:

```
$ spec-kitty merge

Pre-flight Check:
  WP01: ✓ clean
  WP02: ✗ uncommitted changes (2 files)
  WP03: ✓ clean
  WP04: ✗ uncommitted changes (1 file)
  Target: ✗ main has diverged from origin

Fix these issues before merging:
  1. cd .worktrees/017-feature-WP02 && git add . && git commit -m "Final changes"
  2. cd .worktrees/017-feature-WP04 && git add . && git commit -m "Final changes"
  3. git checkout main && git pull
```

### Conflict Forecast

Dry-run now predicts which files will conflict:

```
$ spec-kitty merge --dry-run

Merge Order (dependency-based):
  1. WP01 (no dependencies)
  2. WP03 (depends on WP01)
  3. WP02 (depends on WP01)
  4. WP04 (depends on WP02, WP03)

Conflict Forecast:
  tests/conftest.py: WP01, WP03 (likely)
  kitty-specs/017-feature/tasks.md: WP01, WP02, WP03, WP04 (auto-resolvable)
  src/merge.py: WP02, WP04 (possible)

Status files will be auto-resolved. 1 code file may need manual resolution.
```

### Smart Merge Order

WPs are merged in dependency order, not numerical order:

```yaml
# WP04 frontmatter
---
work_package_id: WP04
dependencies: ["WP02", "WP03"]
---
```

Result: WP01 → WP02 → WP03 → WP04 (not WP01 → WP02 → WP03 → WP04)

### Status File Auto-Resolution

Conflicts in status tracking files are resolved automatically:

| Conflict Type | Resolution |
|---------------|------------|
| `lane: done` vs `lane: for_review` | `lane: done` (more-done wins) |
| `- [x] Task` vs `- [ ] Task` | `- [x] Task` (checked wins) |
| `history:` arrays | Concatenate chronologically |

### Resume Interrupted Merges

```bash
# Merge was interrupted (network, context switch, etc.)
$ spec-kitty merge --resume

Resuming merge for 017-smarter-merge...
  Completed: WP01, WP02
  Current: WP03 (conflicts pending)
  Remaining: WP04

Resolve conflicts in WP03, then run again.
```

### Automatic Cleanup

After successful merge, worktrees and branches are cleaned up automatically:

```
✓ Merged WP01, WP02, WP03, WP04 into main
✓ Removed 4 worktrees from .worktrees/
✓ Deleted 4 branches

Feature 017-smarter-merge successfully merged!
```

## New Flags

| Flag | Description |
|------|-------------|
| `--resume` | Continue interrupted merge |
| `--single` | Merge only current WP (legacy behavior) |
| `--feature <slug>` | Specify feature when running from main |

## Common Scenarios

### Merge from main branch

```bash
# Specify feature explicitly
spec-kitty merge --feature 017-smarter-merge
```

### Keep worktrees for reference

```bash
spec-kitty merge --keep-worktree
```

### Squash all WP commits

```bash
spec-kitty merge --strategy squash
```

### Merge single WP (legacy behavior)

```bash
cd .worktrees/017-feature-WP02
spec-kitty merge --single
```

## Troubleshooting

### "Merge state exists - use --resume or --abort"

A previous merge was interrupted. Either:

```bash
spec-kitty merge --resume   # Continue from where you left off
spec-kitty merge --abort    # Discard state and start fresh
```

### "Circular dependency detected"

Fix your WP frontmatter - dependencies form a cycle:

```
WP01 → WP02 → WP03 → WP01  # Invalid!
```

### "Cannot auto-resolve: non-status conflicts"

Some conflicts are in code files, not status files. Resolve manually:

```bash
# Open conflicted file, fix conflict markers
vim src/merge.py
git add src/merge.py
spec-kitty merge --resume
```
