# Jujutsu (jj) Workflow Tutorial

Learn how to use Spec Kitty with Jujutsu (jj) for better multi-agent parallel development. This tutorial walks you through a complete workflow from project initialization to feature completion.

**Time**: 30-45 minutes

**What You'll Learn**:
- Setting up a jj-based Spec Kitty project
- Creating and managing workspaces for work packages
- Syncing workspaces with automatic rebasing
- Handling non-blocking conflicts
- Using operation history for undo/recovery

---

## Prerequisites

Before starting this tutorial, ensure you have:

### 1. Jujutsu (jj) Installed

```bash
jj --version
# Expected: jj 0.20.0 or higher
```

If not installed, see the [jj installation guide](https://martinvonz.github.io/jj/latest/install/).

### 2. Spec Kitty Installed

```bash
spec-kitty --version
# Expected: 0.12.0 or higher
```

If not installed, see [Install Spec Kitty](../how-to/install-spec-kitty.md).

### 3. An AI Agent Configured

This tutorial uses Claude Code, but any [supported agent](../reference/supported-agents.md) works.

### 4. Terminal Access

You will need a terminal such as macOS Terminal, Windows PowerShell, or a Linux shell.

---

## Step 1: Initialize Your Project

Create a new Spec Kitty project. When jj is available, Spec Kitty automatically uses it.

```bash
spec-kitty init my-jj-project --ai claude
```

You'll see output like:

```
Spec Kitty Project Initializer

✓ Detected jj (0.24.0) - using jujutsu for version control
✓ Created .jj/ repository in colocated mode
✓ Created .git/ for compatibility
✓ Initialized .kittify/ configuration
✓ Installed Claude Code slash commands

Your project is ready at: my-jj-project/
```

### Understanding Colocated Mode

When both jj and git are available, Spec Kitty uses **colocated mode**:

```
my-jj-project/
├── .jj/           # Jujutsu repository (primary)
├── .git/          # Git repository (for compatibility)
├── .kittify/      # Spec Kitty configuration
└── .claude/       # Claude Code commands
```

This means:
- Spec Kitty uses jj for all operations
- You can still `git push` to GitHub
- Team members can use their preferred tool

### Forcing a Specific VCS

To explicitly choose git instead of jj:

```bash
spec-kitty init my-git-project --ai claude --vcs git
```

---

## Step 2: Create a Feature and Workspace

Now let's create a feature and implement it using jj workspaces.

Jujutsu uses native workspaces (not git worktrees). Spec Kitty still places them under `.worktrees/` for consistency across VCS choices.

### 2.1 Start Your Feature

Change into your project and create a specification:

```bash
cd my-jj-project
```

Use the `/spec-kitty.specify` slash command in Claude Code to describe your feature:

```
/spec-kitty.specify Add a user profile page with avatar upload
```

Follow the prompts to create `spec.md` with requirements.

### 2.2 Plan and Generate Tasks

Create your implementation plan:

```
/spec-kitty.plan
```

Generate work packages:

```
/spec-kitty.tasks
```

This creates tasks like:
- `WP01` - Setup database models
- `WP02` - Create API endpoints
- `WP03` - Build frontend components

### 2.3 Create Your First Workspace

Create a workspace for WP01:

```bash
spec-kitty implement WP01
```

Output:

```
Implement WP01
├── ● Detect feature context (Feature: 001-user-profile)
├── ● Validate dependencies (none)
└── ● Create workspace

✓ Created workspace at .worktrees/001-user-profile-WP01/
✓ Created jj workspace 'WP01' with change ID: xyz123abc

Next steps:
  cd .worktrees/001-user-profile-WP01/
  Run /spec-kitty.implement to start coding
```

### 2.4 Work in Your Workspace

Navigate to your workspace and implement the feature:

```bash
cd .worktrees/001-user-profile-WP01/
```

The workspace is isolated - you can make changes without affecting main.

---

## Step 3: Sync Workspaces (Auto-Rebase)

This is where jj shines! When upstream changes occur, jj automatically rebases your work.

### 3.1 Scenario: Multiple Agents Working

Imagine this parallel development scenario:

```
main ─────────────────────────────────────────→
        ↓
      WP01 ─── (you're working here)
        ↓
      WP02 ─── (another agent is working here)
```

When WP01 completes and merges, WP02 needs to incorporate those changes.

### 3.2 Sync Your Workspace

From your workspace, run:

```bash
spec-kitty sync
```

With jj, you'll see:

```
Sync Workspace
├── ● Fetch upstream changes
├── ● Auto-rebase local changes
└── ● Update workspace state

✓ Synced successfully
  Rebased 3 commits onto new upstream
  No conflicts detected
```

**Key difference from git**: With jj, sync **always succeeds**. If there are conflicts, they're stored in the files for later resolution - work continues uninterrupted.

### 3.3 Compare with Git

With git, the same sync might produce:

```
error: Your local changes would be overwritten by merge
hint: Please commit or stash them
```

You'd have to stop, resolve conflicts, then continue. With jj, you keep working.

---

## Step 4: Handle Non-Blocking Conflicts

When sync detects conflicts, jj stores them in your files rather than blocking you.

### 4.1 Understanding Non-Blocking Conflicts

After a sync with conflicts:

```bash
spec-kitty sync
```

```
Sync Workspace
├── ● Fetch upstream changes
├── ● Auto-rebase local changes
└── ● Update workspace state

✓ Synced successfully
  Rebased 2 commits onto new upstream
  ⚠ 1 file has conflicts (resolve when ready)
```

Your work continues! The conflicts are marked in the file:

```python
# src/models/user.py
class User:
<<<<<<< Working copy
    avatar_url: str
    avatar_size: int
=======
    avatar_url: Optional[str]
>>>>>>> Parent commit
```

### 4.2 Workflow for Conflicts

1. **Continue working**: Conflicts don't block other tasks
2. **Resolve when ready**: Edit files to remove conflict markers
3. **Commit resolution**: jj tracks the resolution

```bash
# Edit the file to resolve conflicts
# Then let jj know it's resolved
jj resolve
```

### 4.3 Check Conflict Status

View current conflicts:

```bash
spec-kitty ops log --verbose
```

```
Operation Log
─────────────────────────────────────────────────
abc123  rebase  2 minutes ago  ⚠ conflicts in src/models/user.py
def456  edit    5 minutes ago  Clean
ghi789  fetch   7 minutes ago  Clean
```

**See Also**: [Handle Conflicts (jj)](../how-to/handle-conflicts-jj.md) for detailed resolution strategies.

---

## Step 5: Complete and Merge

When your work is ready, complete the review cycle and merge.

### 5.1 Request Review

From your workspace:

```
/spec-kitty.review
```

This:
- Validates your implementation against requirements
- Runs any defined tests
- Moves the work package to `for_review` lane

### 5.2 Accept the Work Package

After review approval:

```
/spec-kitty.accept
```

This:
- Validates all checklist items are complete
- Records acceptance in the work package history
- Moves to `done` lane

### 5.3 Merge to Main

Finally, merge your completed work:

```bash
spec-kitty merge --push
```

```
Merge Feature
├── ● Validate all WPs complete
├── ● Merge 001-user-profile-WP01 → main
├── ● Clean up workspace
└── ● Push to origin

✓ Feature 001-user-profile merged successfully
```

### 5.4 jj Advantage: Stable Change IDs

Throughout this process, jj maintains **stable Change IDs**. Even after multiple rebases, your changes have the same identity:

```
Change ID: xyz123abc
  ↳ Commit abc001 (initial)
  ↳ Commit def002 (after rebase 1)
  ↳ Commit ghi003 (after rebase 2)  ← Same Change ID!
```

This makes tracking work across multiple agents and rebases much easier.

---

## Step 6: Use Operation History

One of jj's most powerful features is its operation log with full undo capability.

### 6.1 View Operation History

See what operations have been performed:

```bash
spec-kitty ops log
```

```
Operation Log (last 20)
─────────────────────────────────────────────────
ID        Type     When           Status
─────────────────────────────────────────────────
abc123    rebase   2 minutes ago  Clean
def456    commit   5 minutes ago  Clean
ghi789    fetch    10 minutes ago Clean
jkl012    commit   15 minutes ago Clean
```

### 6.2 Undo an Operation

Made a mistake? Undo the last operation:

```bash
spec-kitty ops undo
```

```
Undo Operation
├── ● Identify last operation (abc123: rebase)
└── ● Restore previous state

✓ Undone operation abc123
  Repository restored to state before rebase
```

### 6.3 Restore to a Specific Point

Jump back to any previous operation:

```bash
spec-kitty ops restore def456
```

```
Restore Operation
├── ● Load operation def456
└── ● Restore repository state

✓ Restored to operation def456
  State from: 5 minutes ago
```

> **Important**: The `ops undo` and `ops restore` commands are **jj only**. Git users see the operation log (via reflog) but cannot undo operations through Spec Kitty.

**See Also**: [Use Operation History](../how-to/use-operation-history.md) for advanced recovery scenarios.

---

## Congratulations!

You've completed your first feature using Spec Kitty with jujutsu. You've learned:

- **Auto-rebase**: Upstream changes integrate automatically
- **Non-blocking conflicts**: Work continues even with conflicts
- **Operation history**: Full undo capability for safe experimentation
- **Stable Change IDs**: Track work across rebases

---

## Next Steps

Continue learning with these resources:

### How-To Guides (Task-Oriented)
- [Sync Workspaces](../how-to/sync-workspaces.md) — Detailed sync strategies
- [Handle Conflicts (jj)](../how-to/handle-conflicts-jj.md) — Conflict resolution techniques
- [Use Operation History](../how-to/use-operation-history.md) — Advanced undo scenarios

### Explanations (Understanding-Oriented)
- [Jujutsu for Multi-Agent Development](../explanation/jujutsu-for-multi-agent.md) — Why jj is preferred
- [Auto-Rebase and Non-Blocking Conflicts](../explanation/auto-rebase-and-conflicts.md) — How it works

### Reference
- [CLI Commands](../reference/cli-commands.md) — Complete command reference
- [Configuration](../reference/configuration.md) — VCS configuration options

---

## Troubleshooting

### "jj not found"

Ensure jj is installed and in your PATH:

```bash
which jj
# Should show: /usr/local/bin/jj or similar
```

### "VCS locked to git"

If a feature was started with git, it continues using git. Create a new feature to use jj:

```bash
spec-kitty init new-project --vcs jj
```

### "Conflicts after sync"

This is expected with jj! Conflicts are non-blocking. See [Handle Conflicts (jj)](../how-to/handle-conflicts-jj.md) for resolution.

### "ops undo not available"

The `ops undo` command requires jj. Git projects use `git reflog` for history but cannot undo through Spec Kitty.
