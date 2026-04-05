# How to Merge a Feature

Use this guide to merge completed work packages from a Spec Kitty feature into main.

## Prerequisites

- All WPs have been reviewed and marked `lane: "done"` in their prompt files
- All resolved execution worktrees have no uncommitted changes
- You have run `/spec-kitty.accept` to validate the feature is ready

## Quick Start

From any execution workspace or from main with the `--feature` flag:

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

1. **Workspace cleanliness**: All resolved execution workspaces must have no uncommitted changes
2. **Missing workspaces**: All WPs defined in tasks must have execution workspaces created if they are expected to merge
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
│        │        │ 018-merge-preflight-documentation-lane-b                   │
│ WP04   │ ✗      │ Uncommitted changes in                                     │
│        │        │ 018-merge-preflight-documentation-lane-c                   │
│ Target │ ✓      │ Up to date                                                 │
└────────┴────────┴────────────────────────────────────────────────────────────┘

Pre-flight failed. Fix these issues before merging:

  1. Uncommitted changes in 018-merge-preflight-documentation-lane-b
  2. Uncommitted changes in 018-merge-preflight-documentation-lane-c
```

### Fixing Pre-flight Failures

| Issue | Fix |
|-------|-----|
| Uncommitted changes in a workspace | `cd <workspace path printed by spec-kitty implement>` then commit or stash |
| Missing workspace for WP## | `spec-kitty implement WP##` |
| Target is behind origin | `git checkout main && git pull` |

## Preview with Dry-Run

See what would happen without executing:

```bash
spec-kitty merge --dry-run
```

Example output:

```
Lane-based feature detected: 4 work packages across 3 execution workspaces
  - WP01: 018-merge-preflight-documentation-lane-a
  - WP02: 018-merge-preflight-documentation-lane-a
  - WP03: 018-merge-preflight-documentation-lane-b
  - WP04: 018-merge-preflight-documentation-lane-c

Validating all execution workspaces...
✓ All execution workspaces validated
Feature Merge

Dry run - would execute:
  1. git checkout main
  2. git pull --ff-only
  3. git merge --no-ff kitty/mission-018-merge-preflight-documentation
  4. git worktree remove /.../.worktrees/018-merge-preflight-documentation-lane-a
  5. git worktree remove /.../.worktrees/018-merge-preflight-documentation-lane-b
  6. git worktree remove /.../.worktrees/018-merge-preflight-documentation-lane-c
  7. git branch -d kitty/mission-018-merge-preflight-documentation-lane-a
  8. git branch -d kitty/mission-018-merge-preflight-documentation-lane-b
  9. git branch -d kitty/mission-018-merge-preflight-documentation-lane-c
  10. git branch -d kitty/mission-018-merge-preflight-documentation
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

Not supported for multi-workspace features due to the complexity of rebasing multiple dependent branches. Use `merge` or `squash` instead.

## Cleanup Options

By default, merge removes all resolved execution worktrees and deletes their branches after successful merge.

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

For detailed troubleshooting including conflict resolution and error recovery, see [Accept and Merge](accept-and-merge.md#troubleshooting).

---

## Command Reference

| Flag | Description | Default |
|------|-------------|---------|
| `--strategy` | Merge strategy: `merge`, `squash` (rebase not supported for multi-workspace features) | `merge` |
| `--delete-branch` / `--keep-branch` | Delete lane and mission branches after merge | Delete |
| `--remove-worktree` / `--keep-worktree` | Remove resolved execution worktrees after merge | Remove |
| `--push` | Push to origin after merge | No push |
| `--target` | Target branch to merge into | `main` |
| `--dry-run` | Show what would be done without executing | - |
| `--feature` | Feature slug (when running from main) | Auto-detect |
| `--resume` | Resume an interrupted merge | - |
| `--abort` | Abort and clear merge state | - |

Full CLI reference: [CLI Commands](../reference/cli-commands.md)

## See Also

- [Accept and Merge](accept-and-merge.md#troubleshooting) - Recovery and conflict resolution
- [Accept and Merge](accept-and-merge.md) - Feature validation before merge
- [Execution Lanes](../explanation/execution-lanes.md) - How worktrees work
- [Review Work Packages](review-work-package.md) - WP review process

## Background

- [Execution Lanes](../explanation/execution-lanes.md) - How worktrees work
- [Git Worktrees](../explanation/git-worktrees.md) - Git worktree fundamentals

## Getting Started

- [Your First Feature](../tutorials/your-first-feature.md) - Complete workflow walkthrough
