# Worktree Isolation Model - Complete Guide

**Version**: 1.0
**Last Updated**: 2025-11-13
**Status**: Phase 2A Documentation

## Overview

The Spec Kitty workflow uses **Git Worktrees** to isolate feature development work. This guide explains the worktree model, when worktrees are created, how they work, and how to use them effectively.

## What is a Git Worktree?

A **Git Worktree** is a Git feature that allows you to have multiple working directories for the same repository, each checked out to a different branch. This is perfect for spec-driven development because:

- ✅ Each feature has its own isolated working directory
- ✅ Multiple features can be developed in parallel
- ✅ Main branch stays clean and deployable
- ✅ Easy context switching between features
- ✅ Automatic detection of which feature you're working on

### Standard Git Workflow (Without Worktrees)

```
main/
├── src/
├── spec-kitty/
└── .git
    └── Objects and refs for ALL branches
```

When switching branches: `git checkout 001-feature` → All files change

### Spec-Kitty Workflow (With Worktrees)

```
main/  (main worktree, always on 'main' branch)
├── src/
├── spec-kitty/
└── .git
    └── Objects and refs for ALL branches (shared)

.worktrees/  (additional worktrees)
├── 001-feature-name/  (feature worktree, on '001-feature-name' branch)
│   ├── src/
│   ├── kitty-specs/
│   │   └── 001-feature-name/
│   │       ├── spec.md
│   │       ├── plan.md
│   │       └── tasks.md
│   └── .git  (pointer to main .git)
└── 002-another-feature/  (another feature worktree)
    └── ...
```

## Directory Structure

### Primary Layout

```
project-root/
├── main branch files
├── .git/                      (shared Git database)
├── .worktrees/                (feature worktrees directory)
│   ├── 001-first-feature/     (worktree for 001-first-feature branch)
│   │   ├── src/
│   │   ├── kitty-specs/
│   │   │   └── 001-first-feature/
│   │   │       ├── spec.md
│   │   │       ├── plan.md
│   │   │       ├── tasks/
│   │   │       ├── tasks.md
│   │   │       └── ...
│   │   └── .git (symlink to ../.git)
│   │
│   └── 002-second-feature/    (another worktree)
│       └── ...
│
├── kitty-specs/               (main branch specs - optional)
│   └── archived features
│
└── .kittify/                  (spec-kitty templates & scripts)
    └── scripts/bash/
```

### Key Locations

| Location | Purpose | Who Creates It | When |
|----------|---------|-----------------|------|
| `project-root/.worktrees/` | Worktree container | Git (via scripts) | On first feature creation |
| `project-root/.worktrees/NNN-feature/` | Feature worktree | Git (via create-new-feature.sh) | When feature created |
| `project-root/.worktrees/NNN-feature/kitty-specs/NNN-feature/` | Feature specifications | create-new-feature.sh | When feature created |
| `project-root/kitty-specs/` | Main branch specs | Auto-merged on feature merge | When features merged to main |

## Feature Lifecycle with Worktrees

### Phase 1: Feature Creation

```bash
$ /spec-kitty.create-feature "Add user authentication"

[spec-kitty] Creating feature 001-user-auth
[spec-kitty] ✓ Git worktree created at: .worktrees/001-user-auth
[spec-kitty] ✓ Branch: 001-user-auth
[spec-kitty] ✓ Spec file: .worktrees/001-user-auth/kitty-specs/001-user-auth/spec.md

NEXT STEP (REQUIRED):
  cd ".worktrees/001-user-auth"

Then continue with:
  /spec-kitty.plan
```

**What Happened:**
1. Git created a new branch: `001-user-auth`
2. Git created a worktree at `.worktrees/001-user-auth/`
3. Worktree is automatically checked out to `001-user-auth` branch
4. Spec file created at `.worktrees/001-user-auth/kitty-specs/001-user-auth/spec.md`

### Phase 2: Planning & Implementation

```bash
$ cd .worktrees/001-user-auth

$ /spec-kitty.plan
[spec-kitty] ✓ Implementation plan created
[spec-kitty] FEATURE_DIR: .worktrees/001-user-auth/kitty-specs/001-user-auth

$ /spec-kitty.tasks
[spec-kitty] ✓ Task list created

# Now you're in the feature worktree
# All work happens here - spec, plan, tasks, code changes
```

**Why This Works:**
- Current directory is `.worktrees/001-user-auth/`
- All scripts source common.sh which detects the feature from the directory structure
- Scripts work seamlessly because they're in the right context
- No manual branch switching needed

### Phase 3: Feature Completion

```bash
$ cd .worktrees/001-user-auth

# Implement all tasks...

$ /spec-kitty.accept
[spec-kitty] ✓ Feature validated
[spec-kitty] ✓ Ready to merge

$ /spec-kitty.merge
[spec-kitty] ✓ Merged 001-user-auth into main
[spec-kitty] ✓ Feature complete
```

**What Happened:**
1. Feature merged into main branch
2. Specs copied to `project-root/kitty-specs/001-user-auth/`
3. Worktree can now be removed

### Phase 4: Cleanup

```bash
$ cd project-root  # Go back to main

$ git worktree remove .worktrees/001-user-auth
[spec-kitty] ✓ Worktree removed
```

## Context Detection & Auto-Switching

### How Context Works

Scripts automatically detect which feature you're working on by:

1. **If you're IN a worktree**: Scripts find your feature from the directory structure
2. **If you're IN main**: Scripts check for recent worktrees and auto-switch to the most recent one

### Example: Auto-Switching

```bash
# You're in main directory
$ pwd
/Users/robert/projects/myapp

# You run a task management command
$ /spec-kitty.merge

# Script detects:
# ✓ You're on main branch
# ✓ .worktrees/001-user-auth/ exists and is recent
# ✓ Auto-switches context

[spec-kitty] Auto-switching to feature worktree: .worktrees/001-user-auth
[spec-kitty] ✓ Merged 001-user-auth into main
```

### When Auto-Switching Happens

These scripts auto-detect and switch context:

- `merge-feature.sh` - If you run from main, switches to latest worktree
- `tasks-move-to-lane.sh` - If you run from main, switches to latest worktree
- `check-prerequisites.sh` - If you run from main, switches to latest worktree

### Manual Context Switching

If you need to manually switch between features:

```bash
# Go to main
$ cd project-root

# Switch to a different feature
$ cd .worktrees/002-another-feature

# Now all scripts work in this feature's context
$ /spec-kitty.plan  # Works in 002-another-feature context
```

## Common Workflows

### Scenario 1: Single Feature Development

```bash
# Create feature
$ /spec-kitty.create-feature "Implement payment processing"
# Output tells you where to cd

$ cd .worktrees/NNN-payment-processing

# Plan and implement
$ /spec-kitty.plan
$ /spec-kitty.tasks
# ... implement tasks ...

# Complete feature
$ /spec-kitty.accept
$ /spec-kitty.merge

# Clean up
$ cd ..  # Back to main
$ git worktree remove .worktrees/NNN-payment-processing
```

### Scenario 2: Parallel Feature Development

```bash
# Terminal 1: Feature A
$ /spec-kitty.create-feature "Add API versioning"
$ cd .worktrees/001-api-versioning
$ /spec-kitty.plan
# ... work on feature A ...

# Terminal 2: Feature B (while Feature A is in progress)
$ /spec-kitty.create-feature "Add rate limiting"
$ cd .worktrees/002-rate-limiting
$ /spec-kitty.plan
# ... work on feature B ...

# Both features exist in parallel
$ ls .worktrees/
001-api-versioning/
002-rate-limiting/

# You can switch between them
$ cd .worktrees/001-api-versioning
$ /spec-kitty.plan

$ cd .worktrees/002-rate-limiting
$ /spec-kitty.plan
```

### Scenario 3: Running Scripts from Main

```bash
# You're in main, working on something else
$ pwd
/Users/robert/projects/myapp

# You need to merge a feature
$ /spec-kitty.merge

# What happens:
# 1. Script detects you're on main
# 2. Script finds latest worktree: .worktrees/001-api-versioning/
# 3. Script auto-switches to that worktree
# 4. Script runs merge in the correct context
# 5. Script returns to main

[spec-kitty] Auto-switching to feature worktree: .worktrees/001-api-versioning
[spec-kitty] ✓ Merged 001-api-versioning into main
```

### Scenario 4: Debugging Why a Script Doesn't Work

```bash
# Script fails with "Feature directory not found"
$ pwd
/Users/robert/projects/myapp

$ /spec-kitty.tasks

❌ ERROR: Feature directory not found
Expected: .../kitty-specs/NNN-feature

🔧 TO FIX:
1. cd .worktrees/NNN-feature-name
2. Retry command

# Solution:
$ cd .worktrees/001-your-feature
$ /spec-kitty.tasks  # Now works!
```

## Understanding the Worktree Structure

### Why .worktrees/ Directory?

The `.worktrees/` directory is:

- **Explicitly named**: Easy to identify as "this directory contains worktrees"
- **Git-standard**: Follows Git's naming conventions
- **Non-repo**: Not tracked by Git (added to .gitignore)
- **Persistent**: Survives across git operations
- **Isolated**: Features don't interfere with each other

### What's in a Worktree?

Each worktree at `.worktrees/NNN-feature/` contains:

```
.worktrees/NNN-feature/
├── src/              (copy of project source code from this branch)
├── kitty-specs/      (feature specifications)
│   └── NNN-feature/
│       ├── spec.md
│       ├── plan.md
│       ├── tasks.md
│       ├── tasks/    (task prompts organized by lane)
│       └── ...
├── .kittify/         (complete copy of scripts and templates)
├── .git              (pointer to main .git)
└── (all other project files)
```

### Git's Worktree Pointer

Each worktree has a `.git` file that points to the shared Git database:

```bash
$ cat .worktrees/001-feature/.git
gitdir: /Users/robert/projects/myapp/.git/worktrees/001-feature

$ ls -la .git/worktrees/
001-feature/
002-another/
```

This means:
- ✅ All worktrees share the same Git database
- ✅ Small disk footprint (no duplication)
- ✅ Git operations affect all worktrees
- ✅ Automatic cleanup possible

### .kittify/ in Worktrees

The `.kittify/` directory in each worktree is a **complete copy**, not a symlink. This is standard Git worktree behavior:

**Why is .kittify/ copied?**
- Git's `worktree add` command creates a complete checkout of all tracked files
- Since `.kittify/` is tracked in git, each worktree receives a full copy
- This ensures each worktree is self-contained and portable

**Implications:**
- Each worktree is isolated and can be used independently
- Disk usage: ~5MB per worktree for the .kittify/ copy
- Script modifications in a worktree **only affect that worktree**
- Updates to the main `.kittify/` require `git pull` in active worktrees

**⚠️ Important Note:** Do not modify scripts in worktrees expecting changes to propagate to the main repository. To share script improvements:
1. Commit and merge your feature branch to main
2. Pull changes in other worktrees: `git pull origin main`
3. If needed, recreate other worktrees to get updated scripts

## Troubleshooting Worktrees

### "Worktree already exists"

```bash
$ /spec-kitty.create-feature "My feature"
❌ ERROR: Worktree already exists at .worktrees/NNN-feature

# Solution: Either:
# 1. Remove the existing worktree
$ git worktree remove .worktrees/NNN-feature

# 2. Or use a different feature number
$ /spec-kitty.create-feature "My feature" --feature-num 002
```

### "Git worktree not available"

```bash
# This means Git version is too old (< 2.7)
❌ Warning: Git worktree command unavailable; falling back to in-place checkout

# Solution: Update Git or use the in-place checkout (less ideal)
```

### "Can't access worktree files"

```bash
# Symptoms: Permission denied errors in worktree

# Common cause: Permissions changed
$ chmod -R u+w .worktrees/NNN-feature

# Or remove and recreate:
$ git worktree remove .worktrees/NNN-feature
$ git worktree add .worktrees/NNN-feature 001-feature
```

### "Worktree corruption"

```bash
# If a worktree becomes corrupted

# Option 1: Quick fix
$ git worktree remove .worktrees/NNN-feature --force

# Option 2: Deep clean (if that doesn't work)
$ rm -rf .worktrees/NNN-feature
$ rm -rf .git/worktrees/NNN-feature
$ git worktree prune
```

## Best Practices

### ✅ DO

- ✅ Create a new feature with `/spec-kitty.create-feature`
- ✅ Navigate to the worktree immediately after creation
- ✅ Do all spec/plan/task work inside the worktree
- ✅ Use auto-switching if you forget which worktree you're in
- ✅ Remove worktrees after merging with `git worktree remove`
- ✅ Keep worktrees for active development only
- ✅ If you modify `.kittify/` scripts in a worktree, commit them as part of your feature
- ✅ Pull the main branch in other worktrees to get script updates after merging

### ❌ DON'T

- ❌ Don't manually create worktrees - let create-new-feature.sh do it
- ❌ Don't edit files in the main directory's kitty-specs during development
- ❌ Don't manually git checkout while in a worktree (use cd instead)
- ❌ Don't delete .worktrees/ directly - use git worktree remove
- ❌ Don't leave stale worktrees around (cleanup after merging)
- ❌ Don't assume scripts work from main - they need the feature context

## Understanding Auto-Context Detection

### How Scripts Find Your Feature

When you run a script, it looks for your feature in this order:

```bash
# 1. Check if we're IN a feature branch
if [[ "$CURRENT_BRANCH" =~ ^[0-9]{3}- ]]; then
    # We're in a feature branch (in a worktree or via checkout)
    FEATURE_SLUG="$CURRENT_BRANCH"
fi

# 2. If not in a feature branch, try to auto-detect latest worktree
if [[ ! "$CURRENT_BRANCH" =~ ^[0-9]{3}- ]]; then
    # Look for recent worktrees
    latest_worktree=$(find_latest_feature_worktree "$repo_root" 2>/dev/null)
    if [[ -d "$latest_worktree" ]]; then
        # Found one! Auto-switch context
        cd "$latest_worktree" && "$0" "$@"
    fi
fi
```

### What "Latest" Means

Scripts find the "latest" worktree by:

1. Looking in `.worktrees/` directory
2. Finding worktrees with modification times (most recently modified = most recently used)
3. Switching to the most recent one

```bash
$ ls -lt .worktrees/  # Sorted by modification time
drwx------ 18 user group 576 Nov 13 14:22 001-payment-processing/  ← Latest
drwx------ 15 user group 512 Nov 13 11:15 002-api-versioning/
```

### Limitations of Auto-Detection

Auto-context detection works best when:

- ✅ You have 1-2 active features
- ✅ You ran something recently in a worktree
- ✅ You're switching back to that feature

Auto-context detection doesn't work well when:

- ❌ You have many active features (picks the most recent, not what you want)
- ❌ You want to work on an older feature (it won't find it)
- ❌ You haven't used any worktree recently (nothing to auto-detect)

**In these cases**: Always explicitly `cd .worktrees/NNN-feature` to be sure.

## Integration with Agents/LLMs

### How Agents Use Worktrees

LLM agents using spec-kitty should:

1. **After `/spec-kitty.create-feature`**: Parse JSON output to get worktree path
2. **Before any script**: Always run from the worktree directory
3. **For context queries**: Use `check-prerequisites.sh --json` to confirm location
4. **For context switching**: Use explicit `cd .worktrees/NNN-feature` (not auto-detection)

### JSON Output for Agents

Scripts return JSON to stdout with worktree information:

```bash
$ /spec-kitty.create-feature "My feature" --json
{
  "BRANCH_NAME": "001-my-feature",
  "WORKTREE_PATH": "/Users/robert/projects/myapp/.worktrees/001-my-feature",
  "FEATURE_DIR": "/Users/robert/projects/myapp/.worktrees/001-my-feature/kitty-specs/001-my-feature"
}

# Agent uses this to:
1. cd to WORKTREE_PATH
2. All subsequent scripts run in correct context
3. No ambiguity about where you are
```

## Worktree vs. Main Branch Specs

### Two Spec Locations

| Location | Purpose | Created By | Contains |
|----------|---------|------------|----------|
| `.worktrees/NNN-feature/kitty-specs/NNN-feature/` | Active development | create-new-feature.sh | Current feature work |
| `kitty-specs/NNN-feature/` | Historical record | merge-feature.sh (after merge) | Completed feature specs |

### When Specs Move

1. **Feature created**: Specs at `.worktrees/NNN-feature/kitty-specs/NNN-feature/`
2. **Feature in development**: All work happens in worktree specs
3. **Feature merged**: Specs copied to `kitty-specs/NNN-feature/`
4. **Worktree removed**: Worktree deleted, but specs stay in `kitty-specs/`

```bash
# Before merge
.worktrees/
└── 001-feature/
    └── kitty-specs/
        └── 001-feature/  ← Active specs
            ├── spec.md
            ├── plan.md
            └── tasks.md

kitty-specs/            ← Empty or old features only

# After merge
.worktrees/             ← (001-feature worktree removed)

kitty-specs/
└── 001-feature/        ← Archived specs
    ├── spec.md
    ├── plan.md
    └── tasks.md
```

## FAQ

### Q: Can I have multiple worktrees for the same feature?

**A:** No, each feature has exactly one worktree. But you can have multiple worktrees for different features.

### Q: What if I delete a worktree while it's checked out?

**A:** Git will prevent this. You must `cd` out of the worktree first, then remove it.

### Q: Can I commit from within a worktree?

**A:** Yes! Commits in a worktree go to the worktree's branch (001-feature-name). They affect that branch only.

### Q: What if the main branch changes while I'm in a worktree?

**A:** No problem. Your worktree stays on its branch (001-feature-name). You can merge main into your branch to sync:

```bash
$ cd .worktrees/001-feature
$ git merge main  # Bring in main's changes
```

### Q: Can I manually move a worktree to a different location?

**A:** Not recommended. Use `git worktree repair` if needed. Better to remove and recreate it.

### Q: How much disk space do worktrees use?

**A:** ~5-10MB each (depending on project size), since they share Git objects with main.

### Q: Do worktrees affect the main branch?

**A:** No. Worktrees are completely isolated. Changes in a worktree only affect its branch.

### Q: Can I use worktrees with different Git hosts?

**A:** Yes. Worktrees follow Git's standard behavior. Works with GitHub, GitLab, etc.

### Q: If I modify `.kittify/` scripts in a worktree, do changes appear in the main repo?

**A:** No. Scripts in a worktree are a complete copy, isolated from the main repository.

**If you improve a script:**
1. Edit it in your worktree's `.kittify/scripts/`
2. Commit the improvement as part of your feature branch
3. When you merge your feature to main, the improved script goes with it
4. Other worktrees won't get the update until they pull from main
5. Consider recreating worktrees to get the latest scripts after pulling updates

**Why it works this way**: Each worktree is self-contained, so changes don't automatically propagate. This prevents unexpected side effects when multiple developers work on features simultaneously.

### Q: I'm in a worktree and modified a script. How do I make it available to other worktrees?

**A:**
1. Make sure your changes are committed: `git add .kittify/scripts/... && git commit -m "improve: ..."`
2. Merge your feature branch to main: `/spec-kitty.merge`
3. Go to other worktrees and pull: `git pull origin main`
4. If other worktrees are still active, you may need to recreate them to get updated `.kittify/` files

This ensures all worktrees stay in sync with the latest scripts.

## Summary

The worktree model provides:

| Benefit | How It Works |
|---------|-------------|
| **Isolation** | Each feature in its own `.worktrees/NNN-feature/` directory |
| **Parallel Development** | Multiple features active simultaneously |
| **Clean Main** | Main branch stays pristine, unaffected by feature work |
| **Easy Context** | Auto-detection switches context, or `cd .worktrees/NNN-feature` |
| **Low Overhead** | Worktrees share Git objects, minimal disk space |
| **Automation-Friendly** | Scripts know where they are, no manual branch switching |

---

**Next Step**: See [CONTEXT_SWITCHING_GUIDE.md](CONTEXT_SWITCHING_GUIDE.md) for detailed context switching documentation for agents.
