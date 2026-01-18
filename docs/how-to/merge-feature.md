# How to Merge a Feature

Use this guide to merge completed work packages from a workspace-per-WP feature into main.

## Prerequisites

- All WPs have been reviewed and marked `lane: "done"` in their prompt files
- All worktrees have no uncommitted changes
- You have run `/spec-kitty.accept` to validate the feature is ready

## Quick Start

From any WP worktree or from main with the `--feature` flag:

In your agent:

```text
/spec-kitty.merge
```

Or in your terminal:

```bash
spec-kitty merge
```

Or from main branch:

```bash
spec-kitty merge --feature 015-user-authentication
```

## Pre-flight Validation

Before merging, spec-kitty runs automatic pre-flight checks:

1. **Worktree cleanliness**: All WP worktrees must have no uncommitted changes
2. **Missing worktrees**: All WPs defined in tasks must have worktrees created
3. **Target divergence**: Target branch (main) should not be behind origin

Example pre-flight output when validation passes:

```
Pre-flight Check

┌─────────┬────────┬───────┐
│ WP      │ Status │ Issue │
├─────────┼────────┼───────┤
│ WP01    │ ✓      │       │
│ WP02    │ ✓      │       │
│ WP03    │ ✓      │       │
│ Target  │ ✓      │ Up to date │
└─────────┴────────┴───────┘

Pre-flight passed. Ready to merge.
```

Example when validation fails:

```
Pre-flight Check

┏━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ WP     ┃ Status ┃ Issue                                                      ┃
┡━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ WP01   │ ✓      │                                                            │
│ WP02   │ ✓      │                                                            │
│ WP03   │ ✗      │ Uncommitted changes in                                     │
│        │        │ 018-merge-preflight-documentation-WP03                     │
│ WP04   │ ✗      │ Uncommitted changes in                                     │
│        │        │ 018-merge-preflight-documentation-WP04                     │
│ Target │ ✓      │ Up to date                                                 │
└────────┴────────┴────────────────────────────────────────────────────────────┘

Pre-flight failed. Fix these issues before merging:

  1. Uncommitted changes in 018-merge-preflight-documentation-WP03
  2. Uncommitted changes in 018-merge-preflight-documentation-WP04
```

### Fixing Pre-flight Failures

| Issue | Fix |
|-------|-----|
| Uncommitted changes in WP## | `cd .worktrees/###-feature-WP##` then commit or stash |
| Missing worktree for WP## | `spec-kitty implement WP##` |
| Target is behind origin | `git checkout main && git pull` |

## Preview with Dry-Run

See what would happen without executing:

```bash
spec-kitty merge --dry-run
```

Example output:

```
Dry run - would execute:
  1. git checkout main
  2. git pull --ff-only
  3. git merge --no-ff 018-merge-preflight-documentation-WP01 -m 'Merge WP01'
  4. git merge --no-ff 018-merge-preflight-documentation-WP02 -m 'Merge WP02'
  5. git merge --no-ff 018-merge-preflight-documentation-WP03 -m 'Merge WP03'
  6. git merge --no-ff 018-merge-preflight-documentation-WP04 -m 'Merge WP04'
  7. git worktree remove .worktrees/018-merge-preflight-documentation-WP01
  8. git worktree remove .worktrees/018-merge-preflight-documentation-WP02
  9. git worktree remove .worktrees/018-merge-preflight-documentation-WP03
 10. git worktree remove .worktrees/018-merge-preflight-documentation-WP04
 11. git branch -d 018-merge-preflight-documentation-WP01
 12. git branch -d 018-merge-preflight-documentation-WP02
 13. git branch -d 018-merge-preflight-documentation-WP03
 14. git branch -d 018-merge-preflight-documentation-WP04
```

### Conflict Forecasting

Dry-run also predicts potential conflicts:

```
Conflict Forecast

Found 2 potential conflict(s): 1 auto-resolvable, 1 manual

May require manual resolution:
┌─────────────────────────────────────┬───────────┬────────────┐
│ File                                │ WPs       │ Confidence │
├─────────────────────────────────────┼───────────┼────────────┤
│ docs/how-to/merge-feature.md        │ WP01, WP03│ possible   │
└─────────────────────────────────────┴───────────┴────────────┘

Auto-resolvable (status files):
┌────────────────────────────────────────────────────────────┬───────────┐
│ Status File                                                │ WPs       │
├────────────────────────────────────────────────────────────┼───────────┤
│ kitty-specs/018-merge-preflight-documentation/tasks/WP01.md│ WP01, WP02│
└────────────────────────────────────────────────────────────┴───────────┘

Prepare to resolve 1 conflict(s) manually during merge.
```

**Status files** (WP prompt files in `kitty-specs/*/tasks/*.md`) are auto-resolved by taking the more advanced lane status and merging history entries chronologically.

## Merge Strategies

### Default (Merge Commits)

Creates a merge commit for each WP, preserving full history:

```bash
spec-kitty merge
```

Each WP gets a commit message like: `Merge WP01 from 015-user-authentication`

### Squash

Squashes each WP into a single commit (cleaner history, loses per-commit detail):

```bash
spec-kitty merge --strategy squash
```

### Rebase

Not supported for workspace-per-WP features due to the complexity of rebasing multiple dependent branches. Use `merge` or `squash` instead.

## Cleanup Options

By default, merge removes all WP worktrees and deletes their branches after successful merge.

### Keep Worktrees

Keep worktrees for reference after merge:

```bash
spec-kitty merge --keep-worktree
```

### Keep Branches

Keep branches after merge (useful for PR workflows):

```bash
spec-kitty merge --keep-branch
```

### Keep Both

```bash
spec-kitty merge --keep-worktree --keep-branch
```

### Explicit Cleanup

To explicitly remove worktrees and delete branches (the default behavior):

```bash
spec-kitty merge --remove-worktree --delete-branch
```

These flags are useful when you want to override a config default that keeps artifacts.

## Push After Merge

Push to origin immediately after merge:

```bash
spec-kitty merge --push
```

## Merge from Main Branch

If you're on main and want to merge a feature:

```bash
spec-kitty merge --feature 015-user-authentication
```

This detects all WP worktrees for that feature and merges them in dependency order.

## Target Branch

Merge into a branch other than main:

```bash
spec-kitty merge --target develop
```

## Dependency-Ordered Merging

WPs are merged in dependency order based on the `dependencies` field in their frontmatter:

```yaml
---
work_package_id: "WP03"
dependencies: ["WP01", "WP02"]
---
```

The merge command reads these dependencies and ensures:
- WP01 merges first (no dependencies)
- WP02 merges second (depends on WP01)
- WP03 merges last (depends on WP01 and WP02)

## Interrupted Merge Recovery

If a merge is interrupted (crash, conflict, network issue), use `--resume` to continue:

```bash
spec-kitty merge --resume
```

This picks up where the merge left off, using the saved state in `.kittify/merge-state.json`.

To abandon an interrupted merge and clear state:

```bash
spec-kitty merge --abort
```

This removes the merge state file and lets you start fresh.

For detailed troubleshooting including conflict resolution and error recovery, see [Troubleshoot Merge Issues](troubleshoot-merge.md).

---

## Command Reference

| Flag | Description | Default |
|------|-------------|---------|
| `--strategy` | Merge strategy: `merge`, `squash` (rebase not supported for workspace-per-WP) | `merge` |
| `--delete-branch` / `--keep-branch` | Delete WP branches after merge | Delete |
| `--remove-worktree` / `--keep-worktree` | Remove WP worktrees after merge | Remove |
| `--push` | Push to origin after merge | No push |
| `--target` | Target branch to merge into | `main` |
| `--dry-run` | Show what would be done without executing | - |
| `--feature` | Feature slug (when running from main) | Auto-detect |
| `--resume` | Resume an interrupted merge | - |
| `--abort` | Abort and clear merge state | - |

Full CLI reference: [CLI Commands](../reference/cli-commands.md)

## See Also

- [Troubleshoot Merge Issues](troubleshoot-merge.md) - Recovery and conflict resolution
- [Accept and Merge](accept-and-merge.md) - Feature validation before merge
- [Workspace-per-WP Model](../explanation/workspace-per-wp.md) - How worktrees work
- [Review Work Packages](review-work-package.md) - WP review process

## Background

- [Workspace-per-WP Model](../explanation/workspace-per-wp.md) - How worktrees work
- [Git Worktrees](../explanation/git-worktrees.md) - Git worktree fundamentals

## Getting Started

- [Your First Feature](../tutorials/your-first-feature.md) - Complete workflow walkthrough
