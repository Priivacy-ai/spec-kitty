# Auto-Rebase and Non-Blocking Conflicts

**Divio type**: Explanation

This document explains jujutsu's two most powerful features for multi-agent development: automatic rebasing and non-blocking conflicts. Understanding these concepts helps you leverage jj's advantages in Spec Kitty workflows.

## The Problem: Dependency Chains

In software development, changes often depend on other changes:

```
WP01: Add User model
  ↓
WP02: Build User API (uses User model)
  ↓
WP03: Create User UI (uses User API)
```

When WP01 changes after WP02 has started, WP02 becomes "outdated"—it was built on an old version of WP01. In git, this requires manual rebasing.

## Auto-Rebase: How It Works

### The Traditional Git Approach

Git represents history as a chain of commits:

```
main:  A ─── B ─── C
                    \
WP01:                D ─── E
                           \
WP02:                       F ─── G
```

When commit E is amended (WP01 changes during review), git doesn't automatically update F and G:

```
main:  A ─── B ─── C
                    \
WP01:                D ─── E'  (amended)
                           \
WP02:                       F ─── G  (still based on old E)
```

You must manually rebase:

```bash
cd .worktrees/###-feature-WP02/
git rebase ###-feature-WP01
# Resolve conflicts if any
# Continue rebase
```

### The jj Approach

jj tracks *change IDs* separately from *commit IDs*. When you modify a change, jj knows to update all dependent changes:

```
Before amendment:
WP01: change_id=abc → commit_id=E
WP02: change_id=def → commit_id=G (parent: abc)

After amendment:
WP01: change_id=abc → commit_id=E'  (new commit, same change)
WP02: change_id=def → commit_id=G'  (automatically rebased)
```

When you run `spec-kitty sync` (or `jj rebase`), dependent changes are automatically updated:

```bash
cd .worktrees/###-feature-WP02/
spec-kitty sync
# WP02 is now based on the updated WP01 - automatically
```

### Why This Matters

In a multi-agent workflow with 5 work packages:

| Scenario | Git Manual Steps | jj Auto Steps |
|----------|------------------|---------------|
| WP01 amended | Rebase WP02, WP03, WP04, WP05 | 0 (automatic) |
| WP02 amended | Rebase WP04, WP05 | 0 (automatic) |
| WP03 amended | Rebase WP04, WP05 | 0 (automatic) |

For complex dependency trees, git requires O(n) manual operations. jj requires zero.

## Non-Blocking Conflicts: How They Work

### The Traditional Git Approach

Git conflicts halt progress:

```bash
git rebase main
# CONFLICT (content): Merge conflict in src/config.py
# error: could not apply abc1234... Add new config
# Resolve all conflicts manually, then run "git rebase --continue"
```

Until you resolve the conflict, you cannot:
- Continue the rebase
- Make new commits
- Run tests on the rebased code

The agent (or developer) is blocked.

### The jj Approach

jj stores conflicts *in the file* without blocking:

```bash
jj rebase -d main
# Rebased 1 commits
# New conflicts appeared in these commits:
#   abc12345 Add new config
```

The conflict markers are in the file, but jj continues:

```python
# src/config.py
<<<<<<< Conflict 1 of 1
+++++++ Contents of side #1
DEBUG = True
TIMEOUT = 30
------- Contents of base
DEBUG = False
TIMEOUT = 60
+++++++ Contents of side #2
DEBUG = False
TIMEOUT = 45
>>>>>>> Conflict 1 of 1 ends
```

You can:
- Continue working on other files
- Make new commits (the conflict is preserved)
- Run partial tests
- Come back to the conflict later

### Conflict Resolution

When ready to resolve:

```bash
# Edit the file to remove conflict markers
vim src/config.py

# Or use a merge tool
jj resolve src/config.py

# The file is now resolved
jj status
# No conflicts
```

### Why This Matters

Consider an agent implementing WP02 (API endpoints). A sync brings in WP01 changes that conflict with `config.py`:

**Git behavior**:
1. Agent runs `git pull --rebase`
2. Conflict in `config.py`
3. Agent must stop API work
4. Agent attempts to resolve config conflict
5. Agent may not understand the config context
6. Agent is stuck or makes bad resolution

**jj behavior**:
1. Agent runs `spec-kitty sync`
2. Conflict in `config.py` (stored)
3. Agent continues implementing API endpoints
4. Agent completes all non-conflicting work
5. Agent (or human) resolves config conflict with full context
6. Work continues without blocking

## The Change-Based Model

Understanding jj's model helps explain why these features work:

### Git: Commit-Based

Git tracks *commits*. Each commit is a snapshot with a parent pointer:

```
commit abc123
  parent: def456
  tree: (file contents)
  message: "Add feature"
```

Commits are immutable. Amending creates a *new* commit; the old one is orphaned.

### jj: Change-Based

jj tracks *changes*. Each change has an immutable ID but can point to different commits:

```
change abc123
  current_commit: ghi789
  previous_commits: [def456, xyz...]
  description: "Add feature"
```

When you amend, the change ID stays the same but points to a new commit. Dependent changes (which reference the change ID, not the commit ID) automatically see the update.

## Practical Implications

### For Agents

1. **Sync frequently**: With jj, syncing is safe. Do it often.
2. **Don't fear conflicts**: They won't block you. Finish your work first.
3. **Review conflicts carefully**: Non-blocking doesn't mean non-important.

### For Humans Reviewing Agent Work

1. **Check for conflicts**: Use `jj status` to see unresolved conflicts.
2. **Resolve before merge**: Conflicts must be resolved before the work package can merge.
3. **Use the operation log**: If an agent made a bad resolution, undo it.

### For Spec Kitty Workflows

1. **Automatic dependency updates**: When WP01 is accepted and merged, all dependent WPs are automatically rebased.
2. **Safe parallel work**: Multiple agents can work on dependent WPs; conflicts are stored, not blocking.
3. **Easy recovery**: The operation log means any mistake is undoable.

## Comparison Table

| Aspect | Git | jj |
|--------|-----|-----|
| **Rebase trigger** | Manual command | Automatic on sync |
| **Conflict behavior** | Blocks until resolved | Stored in files |
| **Change tracking** | By commit hash | By change ID |
| **Amend effect** | Creates orphan | Updates dependents |
| **History** | Reflog (hard to use) | Operation log (clear) |
| **Undo** | `git reset --hard` (loses data) | `jj undo` (safe) |

## When Conflicts Are Blocking

Some operations do require conflict resolution:

1. **Merging to main**: The final merge cannot have conflicts
2. **Running tests**: Tests may fail on conflicting files
3. **Building**: Compile errors on conflict markers

jj's non-blocking conflicts delay resolution, not eliminate it. The advantage is *when* you resolve—at a convenient time, with full context, rather than immediately when they appear.

---

## See Also

- [Jujutsu for Multi-Agent Development](jujutsu-for-multi-agent.md) - Why jj is preferred
- [Git Worktrees Explained](git-worktrees.md) - How git worktrees work
- [Workspace-per-WP Model](workspace-per-wp.md) - The workspace model

## Try It

- [Jujutsu Workflow Tutorial](../tutorials/jujutsu-workflow.md) - Hands-on jj workflow

## How-To Guides

- [Sync Workspaces](../how-to/sync-workspaces.md) - Keeping workspaces up to date
- [Handle Conflicts (jj)](../how-to/handle-conflicts-jj.md) - Non-blocking conflict resolution
- [Use Operation History](../how-to/use-operation-history.md) - Undo and restore

## Reference

- [CLI Commands](../reference/cli-commands.md) - sync, ops commands
