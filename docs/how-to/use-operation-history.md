# How to Use Operation History

View, undo, and restore operations in your workspace using jj's operation log.

---

## The Problem

You need to:
- See what operations have occurred in your workspace
- Undo a mistake (accidental commit, bad merge)
- Restore to a specific point in history

---

## Prerequisites

- **jj workspace** — Full undo/restore functionality requires jujutsu
- spec-kitty 0.12.0+

> **Important**: The `ops undo` and `ops restore` commands are **jj only**. Git users can view the operation log (via reflog), but cannot undo through Spec Kitty. See [Git Alternative](#git-alternative) below.

---

## Steps

### View Operation History

See recent operations:

```bash
spec-kitty ops log
```

Output:

```
Operation Log (last 20)
─────────────────────────────────────────────────
ID        Type     When           Status
─────────────────────────────────────────────────
abc123    rebase   2 minutes ago  Clean
def456    commit   5 minutes ago  Clean
ghi789    fetch    10 minutes ago Clean
jkl012    commit   15 minutes ago Clean
mno345    checkout 20 minutes ago Clean
```

### Show More Operations

Increase the limit:

```bash
spec-kitty ops log --limit 50
```

### Show Full Details

Get complete operation IDs and details:

```bash
spec-kitty ops log --verbose
```

```
Operation Log (verbose)
─────────────────────────────────────────────────
ID: abc123def456789...
Type: rebase
Time: 2026-01-17 14:32:15
Status: Clean
Description: Rebase 3 commits onto upstream

ID: def456ghi789012...
Type: commit
Time: 2026-01-17 14:27:42
Status: Clean
Description: Add user avatar support
```

---

## Undo the Last Operation

Made a mistake? Undo it:

```bash
spec-kitty ops undo
```

Output:

```
Undo Operation
├── ● Identify last operation (abc123: rebase)
└── ● Restore previous state

✓ Undone operation abc123
  Repository restored to state before rebase
```

### Undo a Specific Operation

Undo a specific operation by ID:

```bash
spec-kitty ops undo def456
```

> **Note**: This undoes the specified operation, not everything after it.

---

## Restore to a Specific Point

Jump to any point in history:

```bash
spec-kitty ops restore ghi789
```

Output:

```
Restore Operation
├── ● Load operation ghi789
└── ● Restore repository state

✓ Restored to operation ghi789
  State from: 10 minutes ago
```

### Difference: Undo vs Restore

| Command | What it does |
|---------|--------------|
| `ops undo` | Reverses the last (or specified) operation |
| `ops restore` | Jumps directly to a specific historical state |

**Example scenario**:

```
Operations: A → B → C → D (current)

ops undo        → Undoes D, now at C
ops restore B   → Jumps directly to B (skipping C and D)
```

---

## Common Use Cases

### Undo an Accidental Commit

```bash
# Made a commit you didn't want
jj commit -m "Oops, wrong files"

# Undo it
spec-kitty ops undo
```

### Undo a Bad Sync

```bash
# Sync introduced problems
spec-kitty sync

# Go back to before the sync
spec-kitty ops undo
```

### Restore After Multiple Mistakes

```bash
# View history to find good state
spec-kitty ops log --verbose

# Restore to that point
spec-kitty ops restore abc123
```

### Experiment Safely

```bash
# Note your current operation ID
spec-kitty ops log --limit 1

# Try risky changes
# ...

# If it goes wrong, restore
spec-kitty ops restore <saved-id>
```

---

## Understanding Operation IDs

Operation IDs are unique identifiers for each state change:

- Full ID: `abc123def456789012345678901234567890abcd`
- Short ID: `abc123` (usually sufficient)

Use short IDs for convenience:

```bash
spec-kitty ops restore abc123
```

---

## Git Alternative

For git-based workspaces, Spec Kitty shows the reflog:

```bash
spec-kitty ops log
```

```
Operation Log (git reflog)
─────────────────────────────────────────────────
HEAD@{0}: commit: Add user avatar
HEAD@{1}: commit: Initial setup
HEAD@{2}: checkout: moving to feature-WP01
```

However, `ops undo` and `ops restore` are not available for git. Use git directly:

```bash
# View reflog
git reflog

# Reset to a previous state
git reset --hard HEAD@{2}
```

> **Warning**: `git reset --hard` is destructive and loses uncommitted changes.

---

## Troubleshooting

### "Operation not found"

The operation ID may be truncated or incorrect. Use verbose mode to see full IDs:

```bash
spec-kitty ops log --verbose
```

### "Cannot undo: not a jj workspace"

This command requires jujutsu. Check your VCS:

```bash
spec-kitty verify-setup --diagnostics
```

If using git, see [Git Alternative](#git-alternative).

### "Undo failed: conflicts"

If undoing would create conflicts, jj stores them as non-blocking conflicts. Check:

```bash
jj status
```

And resolve any conflicts (see [Handle Conflicts](handle-conflicts-jj.md)).

### "Lost my work after restore"

Don't worry! The operation that contained your work still exists:

```bash
# Find the operation with your work
spec-kitty ops log --verbose

# Restore back to it
spec-kitty ops restore <operation-with-your-work>
```

---

## Best Practices

1. **Before risky operations**: Note your current operation ID
2. **Use undo liberally**: jj's undo is safe and reversible
3. **Prefer restore for complex recovery**: When multiple undos are needed
4. **Check status after restore**: Verify the state is what you expected

---

## See Also

- [Sync Workspaces](sync-workspaces.md) — Syncing and when to undo syncs
- [Handle Conflicts (jj)](handle-conflicts-jj.md) — Resolving conflicts after operations
- [Jujutsu (jj) Workflow Tutorial](../tutorials/jujutsu-workflow.md) — Complete workflow
- [CLI Commands Reference](../reference/cli-commands.md#spec-kitty-ops) — Full command reference
