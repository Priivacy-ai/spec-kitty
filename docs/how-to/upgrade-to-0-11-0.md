# Upgrading to Spec Kitty 0.11.0

**⚠️ BREAKING CHANGE**: Workspace model changed from workspace-per-feature to workspace-per-work-package

## What Changed

**Old model (0.10.x)**:
- Planning commands created a single worktree per feature
- All work packages shared the same worktree
- Pattern: `.worktrees/###-feature/`

**New model (0.11.0+)**:
- Planning commands work in main repository (no worktree created)
- Each work package gets its own worktree on-demand
- Pattern: `.worktrees/###-feature-WP##/`
- Enables parallel multi-agent development

## Critical: Complete In-Progress Features First

**You MUST complete or delete all in-progress features before upgrading to 0.11.0.**

The migration will be blocked if you have legacy worktrees (0.10.x format) in your `.worktrees/` directory.

## Pre-Upgrade Checklist

Complete ALL items before upgrading:

### ☐ Step 1: Check for Legacy Worktrees

```bash
ls .worktrees/
```

Look for directories matching pattern `###-feature` (without `-WP##` suffix).

**Examples of legacy worktrees**:
- `008-unified-python-cli/` ← Legacy (0.10.x)
- `009-jujutsu-vcs/` ← Legacy (0.10.x)
- `010-workspace-per-wp-WP01/` ← New (0.11.0+, this is OK)

**Or use the utility command (after upgrading spec-kitty-cli)**:
```bash
pip install --upgrade spec-kitty-cli  # Get 0.11.0 first
spec-kitty list-legacy-features       # Then check for legacy worktrees
```

> **Note**: The `list-legacy-features` command is new in 0.11.0. If you're on 0.10.x, use `ls .worktrees/` to manually check for legacy worktrees before running `spec-kitty upgrade`.

### ☐ Step 2: Decide What to Do With Each Feature

For each legacy worktree, choose one:
- **Option A**: Complete the feature (recommended)
- **Option B**: Delete the feature (if abandoning)

### ☐ Step 3: Complete or Delete Features

**Option A: Complete features (recommended)**

For each feature you want to keep:

```bash
# 1. Review what's in the worktree
cd .worktrees/008-unified-python-cli/
git status
git log --oneline

# 2. Make sure all work is committed
git add .
git commit -m "Final changes before merge"

# 3. Go back to main repo
cd /path/to/main/repo

# 4. Merge the feature
spec-kitty merge 008-unified-python-cli
```

Repeat for each legacy feature.

**Option B: Delete features (if abandoning)**

For features you want to discard:

```bash
# 1. Remove the worktree
git worktree remove .worktrees/008-unified-python-cli

# 2. Delete the branch
git branch -D 008-unified-python-cli

# 3. Optionally clean up feature artifacts in main
rm -rf kitty-specs/008-unified-python-cli
git add kitty-specs/
git commit -m "Remove abandoned feature 008"
```

**⚠️ Warning**: Deleting a feature is permanent. Make sure you don't need the code before deleting.

### ☐ Step 4: Verify Clean State

After completing or deleting all features:

```bash
ls .worktrees/
# Should be empty OR only show ###-feature-WP## patterns (new format)
```

If you still see legacy worktrees (directories without `-WP##` suffix), go back to Step 3 and handle them.

> **After upgrading spec-kitty-cli to 0.11.0**, you can also verify with:
> ```bash
> spec-kitty list-legacy-features
> # Should show: "No legacy worktrees detected"
> ```

### ☐ Step 5: Backup (Optional but Recommended)

Before upgrading, back up your repository:

```bash
# Create a backup branch
git checkout -b backup-before-0-11-0
git push origin backup-before-0-11-0

# Go back to main
git checkout main
```

### ☐ Step 6: Read Breaking Changes

Review what changed in 0.11.0:
- Planning commands no longer create worktrees
- New command: `spec-kitty implement WP##`
- Dependency tracking in WP frontmatter
- All 12 agent templates updated

See [Workspace-per-WP documentation](../explanation/workspace-per-wp.md) for details.

### ☐ Step 7: Upgrade

```bash
pip install --upgrade spec-kitty-cli
spec-kitty --version  # Should show 0.11.0
```

If the upgrade is blocked with error message:
```
❌ Cannot upgrade to 0.11.0
Legacy worktrees detected:
  - 008-unified-python-cli
```

Go back to Step 3 and complete/delete the listed features.

### ☐ Step 8: Verify Upgrade

Test the new workflow with a dummy feature:

```bash
# Planning now works in main (no worktree created)
/spec-kitty.specify "Test Feature"

# Check that NO worktree was created
ls .worktrees/
# Should still be empty

# Check that spec was created in main
ls kitty-specs/
# Should show 012-test-feature/ (or next available number)

# Check git log
git log --oneline
# Should show: "Add spec for feature 012-test-feature"

# Clean up test feature

**⚠️ Warning**: Choose a safe cleanup method:

**Option A: Safer - Explicit revert (recommended)**
```bash
rm -rf kitty-specs/012-test-feature
git add kitty-specs/
git commit -m "Remove test feature 012-test-feature"
```

**Option B: Revert the commit**
```bash
git revert HEAD  # Reverts the test feature commit
# Creates new commit that undoes the test
```

**Option C: Hard reset (⚠️ DESTRUCTIVE - only if you're sure)**
```bash
# WARNING: This permanently deletes the commit. Only use if:
#  - The test feature commit has NOT been pushed to remote
#  - You have no other unpushed commits you want to keep
#  - You're absolutely sure you don't need the test

git reset --hard HEAD~1
# ⚠️ Cannot be undone!
```

**Recommended**: Use Option A or B. They're safer and create a clear history.
```

**Success!** You're now on 0.11.0.

## What's Different After Upgrading

### Planning Commands (Now in Main)

**Before (0.10.x)**:
```bash
/spec-kitty.specify "My Feature"
→ Created .worktrees/010-my-feature/
→ You work inside the worktree
```

**After (0.11.0)**:
```bash
/spec-kitty.specify "My Feature"
→ Creates kitty-specs/010-my-feature/spec.md in main
→ Commits to main
→ NO worktree created
→ You stay in main repository
```

Same for `/spec-kitty.plan` and `/spec-kitty.tasks`.

### Implementation Command (New)

**Before (0.10.x)**:
```bash
# Agents work in shared worktree created during planning
cd .worktrees/010-my-feature/
# All WPs implemented here
```

**After (0.11.0)**:
```bash
# Create worktree for specific WP
spec-kitty implement WP01
→ Creates .worktrees/010-my-feature-WP01/
→ Agent A works here

# Create worktree for another WP (parallel!)
spec-kitty implement WP02
→ Creates .worktrees/010-my-feature-WP02/
→ Agent B works here simultaneously
```

### Dependencies (New Feature)

Work packages can now declare dependencies in frontmatter:

```yaml
---
work_package_id: "WP02"
title: "API Endpoints"
dependencies: ["WP01"]  # WP02 depends on WP01
---
```

Implement with dependencies:
```bash
spec-kitty implement WP02 --base WP01
# WP02 branches from WP01's branch, includes WP01's changes
```

## New Commands in 0.11.0

### `spec-kitty implement WP## [--base WPXX]`

Create worktree for a specific work package.

**Usage**:
```bash
# Independent WP (branches from main)
spec-kitty implement WP01

# Dependent WP (branches from another WP)
spec-kitty implement WP02 --base WP01
```

**What it does**:
1. Creates `.worktrees/###-feature-WP##/` directory
2. Creates git branch `###-feature-WP##`
3. Checks out code in the worktree
4. Moves WP from `planned` → `doing` lane

### `spec-kitty list-legacy-features`

Check for legacy worktrees before upgrading.

**Usage**:
```bash
spec-kitty list-legacy-features
```

**Output examples**:
```bash
# No legacy worktrees
No legacy worktrees detected. Safe to upgrade to 0.11.0.

# Legacy worktrees found
Legacy worktrees detected:
  - 008-unified-python-cli
  - 009-jujutsu-vcs

Complete or delete these features before upgrading to 0.11.0.
```

## Updated Commands in 0.11.0

### `/spec-kitty.specify`

**Before**: Created worktree
**After**: Works in main, commits spec.md to main, NO worktree created

### `/spec-kitty.plan`

**Before**: Worked in worktree
**After**: Works in main, commits plan.md to main

### `/spec-kitty.tasks`

**Before**: Worked in worktree
**After**: Works in main, commits tasks/*.md to main, generates dependencies in frontmatter

### `spec-kitty merge`

**Before**: Merged single feature branch
**After**: Merges all WP branches for a feature, validates workspace-per-WP model

## Workflow Example: Creating a Feature in 0.11.0

Let's walk through creating a feature using the new workflow:

### Step 1: Planning (in main)

```bash
# Ensure you're in main
git checkout main

# Create specification
/spec-kitty.specify "Add user authentication"
→ kitty-specs/011-user-authentication/spec.md created in main
→ Committed to main

# Create plan
/spec-kitty.plan
→ kitty-specs/011-user-authentication/plan.md created in main
→ Committed to main

# Generate work packages
/spec-kitty.tasks
→ Creates WP01.md, WP02.md, WP03.md in main
→ Generates dependencies in frontmatter
→ Committed to main

# Check what was created
ls kitty-specs/011-user-authentication/tasks/
→ WP01-database-schema.md
→ WP02-api-endpoints.md
→ WP03-frontend-components.md

# Check worktrees (should be empty)
ls .worktrees/
→ (empty)
```

### Step 2: Implementation (create worktrees)

```bash
# Implement WP01 (foundation)
spec-kitty implement WP01
→ Created .worktrees/011-user-authentication-WP01/
→ Branch: 011-user-authentication-WP01 (from main)

# Agent A works here
cd .worktrees/011-user-authentication-WP01/
# ... implement database schema ...
git add .
git commit -m "Implement database schema"

# Go back to main
cd /path/to/main/repo

# Implement WP02 (depends on WP01)
spec-kitty implement WP02 --base WP01
→ Created .worktrees/011-user-authentication-WP02/
→ Branch: 011-user-authentication-WP02 (from WP01)
→ Includes WP01's code

# Agent B works here (in parallel with Agent A!)
cd .worktrees/011-user-authentication-WP02/
# ... implement API endpoints ...

# Implement WP03 (independent)
spec-kitty implement WP03
→ Created .worktrees/011-user-authentication-WP03/
→ Branch: 011-user-authentication-WP03 (from main)

# Agent C works here (also in parallel!)
cd .worktrees/011-user-authentication-WP03/
# ... implement frontend components ...
```

**Result**: Three agents working simultaneously on different WPs!

### Step 3: Review and Merge

```bash
# Review WP01
/spec-kitty.review WP01
→ Moves to for_review lane
→ Warns: "WP02 depends on WP01. If changes requested, WP02 needs rebase"

# After all WPs complete, merge feature
spec-kitty merge 011-user-authentication
→ Merges all WP branches to main
→ Optionally removes worktrees
```

## Troubleshooting Upgrade Issues

### Issue: "Cannot upgrade, legacy worktrees detected"

**Error message**:
```
❌ Cannot upgrade to 0.11.0
Legacy worktrees detected:
  - 008-unified-python-cli
  - 009-jujutsu-vcs

Complete or delete these features before upgrading.
```

**Solution**: Go back to "Pre-Upgrade Checklist" → Step 3 and complete or delete each listed feature.

### Issue: "Uncommitted changes in worktree"

When trying to complete a feature:
```
❌ Cannot merge feature 008-unified-python-cli
Uncommitted changes detected in .worktrees/008-unified-python-cli/
```

**Solution**:
```bash
cd .worktrees/008-unified-python-cli/
git status  # Check what's uncommitted
git add .
git commit -m "Commit remaining changes"
cd /path/to/main/repo
spec-kitty merge 008-unified-python-cli
```

### Issue: "Feature artifacts in main but no worktree"

If you have `kitty-specs/009-feature/` in main but no worktree:

**Scenario 1**: Feature was already merged
```bash
# Check git history
git log --all --grep="009-feature"

# If merged, clean up artifacts
rm -rf kitty-specs/009-feature
git add kitty-specs/
git commit -m "Clean up merged feature 009 artifacts"
```

**Scenario 2**: Feature was planned but never implemented
```bash
# Feature exists in main but was never started
# Safe to delete if you don't need it
rm -rf kitty-specs/009-feature
git add kitty-specs/
git commit -m "Remove unimplemented feature 009"
```

### Issue: Upgrade broke my workflow

If you encounter issues after upgrading:

**Rollback to 0.10.12**:
```bash
pip install spec-kitty-cli==0.10.12
spec-kitty --version  # Should show 0.10.12
```

**Note**: Features planned in 0.11.0 format (artifacts in main) will need re-planning if you rollback to 0.10.12 (worktree model).

**Report the issue**:
Please report bugs at: https://github.com/Priivacy-ai/spec-kitty/issues

Include:
- Error message
- Output of `spec-kitty --version`
- Steps to reproduce

## Benefits of the New Model

After upgrading, you'll benefit from:

1. **Parallel development**: Multiple agents work on different WPs simultaneously
2. **Better isolation**: Each WP has its own worktree and branch
3. **Explicit dependencies**: Dependencies declared in frontmatter, validated automatically
4. **Cleaner main**: Planning artifacts visible in main (no need to cd to worktree to see plan)
5. **Scalability**: Features with 10+ WPs can have multiple agents working in parallel
6. **Foundation for jj**: Future jj integration will enable automatic rebasing

## Getting Help

- **Documentation**: [Workspace-per-WP guide](../explanation/workspace-per-wp.md)
- **Issues**: https://github.com/Priivacy-ai/spec-kitty/issues

## Summary

**Before upgrading to 0.11.0**:
1. ✅ Check for legacy worktrees: `ls .worktrees/` (look for directories without `-WP##` suffix)
2. ✅ Complete or delete each legacy feature
3. ✅ Verify clean state: `ls .worktrees/` (should be empty or only new format)
4. ✅ Upgrade CLI: `pip install --upgrade spec-kitty-cli`
5. ✅ Upgrade project: `spec-kitty upgrade` (in your project directory)
6. ✅ Test with dummy feature to verify new workflow

**After upgrading**:
- Planning commands work in main (no worktree created)
- Use `spec-kitty implement WP##` to create worktrees
- Enjoy parallel multi-agent development!

Welcome to Spec Kitty 0.11.0! 🎉

## Command Reference
- [`spec-kitty upgrade`](../reference/cli-commands.md#spec-kitty-upgrade)
- [`spec-kitty list-legacy-features`](../reference/cli-commands.md#spec-kitty-list-legacy-features)

## See Also
- [Install Spec Kitty](install-spec-kitty.md)
- [Non-Interactive Init](non-interactive-init.md)

## Background
- [Workspace-per-WP Model](../explanation/workspace-per-wp.md)
- [Git Worktrees](../explanation/git-worktrees.md)
