# How to Accept and Merge a Feature

Use this guide to validate feature readiness and merge to the mission's target branch.

## Prerequisites

- All WPs are in `lane: "done"`
- You are in a checkout where the feature can be resolved (repository root checkout or execution workspace)

## Accept the Feature

In your agent:

```text
/spec-kitty.accept
```

Or in your terminal:

```bash
spec-kitty accept
```

### What Accept Checks

- All WPs are in `done`
- Required metadata and activity logs are present
- No unresolved `[NEEDS CLARIFICATION]` markers remain

To run a read-only checklist (in your terminal):

```bash
spec-kitty accept --mode checklist
```

## Merge to the Target Branch

In your agent:

```text
/spec-kitty.merge --push
```

Or in your terminal:

```bash
spec-kitty merge --push
```

By default, `spec-kitty merge` lands in the mission's recorded target branch. Use `spec-kitty merge --target <branch>` only when you intentionally need to override that destination.

For detailed merge options including dry-run, strategies, and cleanup flags, see [Merge a Feature](merge-feature.md).

## Merge Strategies

- **Default (merge commit)**: `spec-kitty merge`
- **Squash**: `spec-kitty merge --strategy squash`

Note: Rebase is not supported for multi-workspace features. Use `merge` or `squash` instead.

## Cleanup

By default, merge removes resolved execution worktrees and deletes the feature branch. Use these flags to keep them (in your terminal):

```bash
spec-kitty merge --keep-worktree --keep-branch
```

## Abandon a Feature (Manual Cleanup)

If you decide to drop a feature without merging, remove its execution worktrees and branches manually.
These steps are safe and reversible until you delete the branch and commit the cleanup.

1. List worktrees to find all workspaces for the feature:
```bash
git worktree list
```

2. Remove each execution worktree for the feature:
```bash
git worktree remove .worktrees/<feature>-lane-a
git worktree remove .worktrees/<feature>-lane-b
```

If a worktree has uncommitted changes you want to discard, use `--force`:
```bash
git worktree remove --force .worktrees/<feature>-lane-a
```

3. Delete the feature branches:
```bash
git branch -D <feature>-lane-a
git branch -D <feature>-lane-b
```

4. Remove the planning artifacts from the repository root checkout (spec/plan/tasks), then commit:
```bash
rm -rf kitty-specs/<feature>
git add kitty-specs/
git commit -m "Remove abandoned feature <feature>"
```

## Troubleshooting

- **Accept reports blockers**: Resolve the listed issues, then rerun `/spec-kitty.accept`.
- **Merge fails**: Ensure your current checkout is clean and the feature resolves correctly.
- **Merge is heading to the wrong branch**: Inspect the mission's recorded target branch before retrying, and use `spec-kitty merge --target <branch>` only if you intend to override it.

For detailed troubleshooting including pre-flight failures, conflict resolution, and merge recovery, see [Troubleshoot Merge Issues](troubleshoot-merge.md).

---

## Command Reference

- [Slash Commands](../reference/slash-commands.md) - All `/spec-kitty.*` commands
- [CLI Commands](../reference/cli-commands.md) - Full CLI reference

## See Also

- [Merge a Feature](merge-feature.md) - Detailed merge workflow
- [Keep Main Clean](keep-main-clean.md) - Choose a target branch without changing planning location
- [Troubleshoot Merge Issues](troubleshoot-merge.md) - Recovery and conflict resolution
- [Review a Work Package](review-work-package.md) - Required before accept
- [Upgrade to 0.11.0](install-and-upgrade.md) - Breaking changes in v0.11.0

## Background

- [Execution Lanes](../explanation/execution-lanes.md) - Worktree cleanup
- [Git Worktrees](../explanation/git-worktrees.md) - How worktrees work

## Getting Started

- [Your First Feature](../tutorials/your-first-feature.md) - Complete workflow walkthrough
