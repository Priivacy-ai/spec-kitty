# How to Accept and Merge a Feature

Use this guide to validate feature readiness and merge to `main`.

## Prerequisites

- All WPs are in `lane: "done"`
- You are in the feature worktree

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

## Merge to Main

In your agent:

```text
/spec-kitty.merge --push
```

Or in your terminal:

```bash
spec-kitty merge --push
```

## Merge Strategies

- **Default (merge commit)**: `spec-kitty merge`
- **Squash**: `spec-kitty merge --strategy squash`
- **Rebase**: `spec-kitty merge --strategy rebase`

## Cleanup

By default, merge removes the feature worktree and deletes the feature branch. Use these flags to keep them (in your terminal):

```bash
spec-kitty merge --keep-worktree --keep-branch
```

## Abandon a Feature (Manual Cleanup)

If you decide to drop a feature without merging, remove its worktrees and branches manually.
These steps are safe and reversible until you delete the branch and commit the cleanup.

1. List worktrees to find all workspaces for the feature:
```bash
git worktree list
```

2. Remove each feature worktree:
```bash
git worktree remove .worktrees/<feature>-WP01
git worktree remove .worktrees/<feature>-WP02
```

If a worktree has uncommitted changes you want to discard, use `--force`:
```bash
git worktree remove --force .worktrees/<feature>-WP01
```

3. Delete the feature branches:
```bash
git branch -D <feature>-WP01
git branch -D <feature>-WP02
```

4. Remove the planning artifacts from main (spec/plan/tasks), then commit:
```bash
rm -rf kitty-specs/<feature>
git add kitty-specs/
git commit -m "Remove abandoned feature <feature>"
```

## Troubleshooting

- **Accept reports blockers**: Resolve the listed issues, then rerun `/spec-kitty.accept`.
- **Merge fails**: Ensure your worktree is clean and you are on the feature branch.

---

## Command Reference

- [Slash Commands](../reference/slash-commands.md) - All `/spec-kitty.*` commands
- [CLI Commands](../reference/cli-commands.md) - Full CLI reference

## See Also

- [Review a Work Package](review-work-package.md) - Required before accept
- [Upgrade to 0.11.0](upgrade-to-0-11-0.md) - Breaking changes in v0.11.0

## Background

- [Workspace-per-WP Model](../explanation/workspace-per-wp.md) - Worktree cleanup
- [Git Worktrees](../explanation/git-worktrees.md) - How worktrees work

## Getting Started

- [Your First Feature](../tutorials/your-first-feature.md) - Complete workflow walkthrough
