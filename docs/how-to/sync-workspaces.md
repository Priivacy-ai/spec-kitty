# How to Sync Workspaces

Keep your workspace up to date with upstream changes from dependent work packages.

---

## The Problem

You're working on WP02, and WP01 (which WP02 depends on) has changed. You need to update your workspace with the latest changes from upstream.

---

## Prerequisites

- Active workspace created via `spec-kitty implement`
- spec-kitty 0.12.0+
- Changes committed in the upstream workspace

---

## Steps

### 1. Navigate to Your Workspace

```bash
cd .worktrees/001-my-feature-WP02/
```

### 2. Run Sync

```bash
spec-kitty sync
```

You'll see output like:

```
Sync Workspace
├── ● Fetch upstream changes
├── ● Auto-rebase local changes
└── ● Update workspace state

✓ Synced successfully
  Rebased 3 commits onto new upstream
  No conflicts detected
```

### 3. Verify the Sync

Check that upstream changes are now present:

```bash
# With jj
jj log --limit 10

# With git
git log --oneline -10
```

---

## Backend Differences

> **Important**: Sync behavior differs between jj and git backends.

### jj (Jujutsu)

- Sync **always succeeds**
- Conflicts are stored in files as conflict markers
- You can continue working even with conflicts
- Resolve conflicts when convenient

### git

- Sync may **fail** if conflicts are detected
- You must resolve conflicts before proceeding
- Work is blocked until conflicts are resolved

To check which backend your workspace uses:

```bash
spec-kitty verify-setup --diagnostics
```

---

## Using --verbose for Details

Add `--verbose` to see detailed sync information:

```bash
spec-kitty sync --verbose
```

Output includes:
- Which commits were fetched
- Rebase operations performed
- Any conflicts detected

---

## Recovering with --repair

If your workspace is in a broken state (corrupted worktree, detached HEAD), use `--repair`:

```bash
spec-kitty sync --repair
```

> **Warning**: `--repair` may lose uncommitted changes. Commit your work first when possible.

This attempts to:
1. Reset the workspace to a known good state
2. Re-fetch upstream changes
3. Apply your commits on top

---

## Troubleshooting

### "Working copy is not clean"

Commit or stash your changes before syncing:

```bash
# With jj
jj commit -m "WIP: save before sync"

# With git
git add . && git commit -m "WIP: save before sync"
```

### "Cannot rebase: conflicts detected" (git only)

With git, you must resolve conflicts before sync completes:

```bash
# See conflicting files
git status

# Resolve conflicts in your editor
# Then mark as resolved
git add <resolved-files>
git rebase --continue
```

### "Failed to fetch: network error"

Check your network connection and try again:

```bash
spec-kitty sync --verbose
```

### "Workspace not found"

Ensure you're in a valid workspace directory:

```bash
pwd
# Should be: /path/to/project/.worktrees/<feature>-WP##/
```

---

## When to Sync

Sync your workspace:

- **Before starting new work**: Get the latest changes first
- **After a dependent WP is merged**: Incorporate those changes
- **Before code review**: Ensure you have the latest base
- **When CI fails**: Your workspace may be out of date

---

## See Also

- [Jujutsu (jj) Workflow Tutorial](../tutorials/jujutsu-workflow.md) — Complete workflow tutorial
- [Handle Conflicts (jj)](handle-conflicts-jj.md) — Resolving conflicts after sync
- [Auto-Rebase and Non-Blocking Conflicts](../explanation/auto-rebase-and-conflicts.md) — How auto-rebase works
- [CLI Commands Reference](../reference/cli-commands.md#spec-kitty-sync) — Full command reference
