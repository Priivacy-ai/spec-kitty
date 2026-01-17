# How to Handle Conflicts (jj)

Resolve conflicts in jujutsu workspaces without blocking your workflow.

---

## The Problem

After running `spec-kitty sync`, you see a message about conflicts:

```
✓ Synced successfully
  Rebased 2 commits onto new upstream
  ⚠ 1 file has conflicts (resolve when ready)
```

With jj, this is **not a blocker**. You can continue working.

---

## Prerequisites

- jj workspace (not git) — conflict handling differs significantly
- Conflicts detected after sync or rebase operation
- spec-kitty 0.12.0+

> **Note**: This guide is jj-specific. For git conflict resolution, see your git documentation or use `git mergetool`.

---

## Key Insight: Non-Blocking Conflicts

Unlike git, jj treats conflicts as **data, not errors**:

| Aspect | git | jj |
|--------|-----|-----|
| Sync with conflicts | **Fails** | **Succeeds** |
| Working state | Blocked | Continues |
| When to resolve | Immediately | When convenient |
| Other work | Cannot proceed | Can proceed |

This is transformative for multi-agent development where multiple agents work in parallel.

---

## Steps

### 1. Continue Working (Optional)

With jj, you can keep working on other parts of your code while conflicts exist:

```bash
# Edit unaffected files
# Run tests that don't depend on conflicted code
# Commit new changes
```

Conflicts will wait until you're ready to resolve them.

### 2. View Conflicts

See which files have conflicts:

```bash
jj status
```

Output:

```
Working copy changes:
C src/models/user.py   (conflict)
M src/api/endpoints.py
```

The `C` indicates a conflict.

### 3. Examine Conflict Markers

Open the conflicting file. You'll see markers like:

```python
class User:
<<<<<<< Conflict 1 of 1
%%%%%%% Changes from base to side #1
-    avatar_url: str
+    avatar_url: Optional[str]
+++++++ Contents of side #2
    avatar_url: str
    avatar_size: int
>>>>>>>
```

This shows:
- **Side #1**: Changes from upstream (Optional[str])
- **Side #2**: Your changes (added avatar_size)

### 4. Resolve the Conflict

Edit the file to contain the correct final code:

```python
class User:
    avatar_url: Optional[str]
    avatar_size: int
```

Remove all conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).

### 5. Mark as Resolved

After editing, squash the resolution into your commit:

```bash
jj squash
```

Or create a new commit with the resolution:

```bash
jj commit -m "Resolve merge conflict in user model"
```

### 6. Verify Resolution

Confirm no conflicts remain:

```bash
jj status
```

Output should show no `C` markers:

```
Working copy changes:
M src/models/user.py
M src/api/endpoints.py
```

---

## Understanding Conflict Markers

jj's conflict markers are more detailed than git's:

```
<<<<<<< Conflict N of M
%%%%%%% Changes from base to side #1
-original line
+modified line from side 1
+++++++ Contents of side #2
line from side 2
>>>>>>>
```

- `%%%%%%%`: Shows what changed between the base and side #1
- `+++++++`: Shows the full content from side #2
- `-` and `+` within `%%%%%%%` show line-by-line changes

---

## Viewing Conflicts in Operation Log

See when conflicts were introduced:

```bash
spec-kitty ops log --verbose
```

```
Operation Log
─────────────────────────────────────────────────
abc123  rebase  2 minutes ago  ⚠ conflicts in src/models/user.py
def456  edit    5 minutes ago  Clean
```

---

## Undoing a Conflicting Merge

If the conflict is too complex, undo the operation that caused it:

```bash
spec-kitty ops undo
```

This restores your workspace to before the sync. Then you can:
- Coordinate with the other agent/developer
- Take a different approach to your changes
- Wait for a better time to merge

---

## Troubleshooting

### "Cannot squash: tree has conflicts"

This error means jj detected unresolved conflict markers in your files. Check:

```bash
jj status
```

And look for files marked with `C`. Resolve them first.

### "Conflict markers still in file"

Make sure you removed ALL conflict markers:

```bash
grep -r "<<<<<<" .
grep -r ">>>>>>>" .
```

### "Lost my changes after resolving"

If you accidentally deleted your changes while resolving, use the operation log:

```bash
spec-kitty ops log
spec-kitty ops restore <operation-id-before-resolve>
```

---

## Why Non-Blocking Conflicts Matter

In multi-agent development:

1. **Agent A** completes WP01 and merges
2. **Agent B** (working on dependent WP02) syncs
3. With git: Agent B is **blocked**, must stop and resolve
4. With jj: Agent B can **continue** working on WP02, resolve conflict later

This keeps all agents productive and reduces coordination overhead.

---

## See Also

- [Sync Workspaces](sync-workspaces.md) — How to sync your workspace
- [Use Operation History](use-operation-history.md) — Undo operations with conflicts
- [Auto-Rebase and Non-Blocking Conflicts](../explanation/auto-rebase-and-conflicts.md) — Conceptual explanation
- [Jujutsu (jj) Workflow Tutorial](../tutorials/jujutsu-workflow.md) — Complete workflow
