---
description: Merge a completed feature into the main branch and clean up worktree
---

# /spec-kitty.merge - Merge Feature to Main

**Version**: 0.11.0+
**Purpose**: Merge ALL completed work packages for a feature into main branch.

## CRITICAL: Workspace-per-WP Model (0.11.0)

In 0.11.0, each work package has its own worktree:
- `.worktrees/###-feature-WP01/`
- `.worktrees/###-feature-WP02/`
- `.worktrees/###-feature-WP03/`

**Merge merges ALL WP branches at once** (not incrementally one-by-one).

## 📍 WORKING DIRECTORY: Run from MAIN repository

**IMPORTANT**: Merge must run from the main repository root, NOT from a WP worktree.

```bash
# If you're in a worktree, return to main first:
cd /path/to/project/root  # Use absolute path to project root

# Then run merge:
spec-kitty merge ###-feature-slug
```

**How to get project root path**: Run this from any worktree:
```bash
git rev-parse --show-toplevel
```

## Prerequisites

Before running this command:

1. ✅ All work packages must be in `done` lane (reviewed and approved)
2. ✅ Feature must pass `/spec-kitty.accept` checks
3. ✅ Working directory must be clean (no uncommitted changes in main)
4. ✅ **You must be in main repository root** (not in a worktree)

## Command Syntax

```bash
spec-kitty merge ###-feature-slug [OPTIONS]
```

**Example**:
```bash
cd /tmp/spec-kitty-test/test-project  # Main repo root
spec-kitty merge 001-cli-hello-world
```

## What This Command Does

1. **Detects** your current feature branch and worktree status
2. **Verifies** working directory is clean
3. **Switches** to the target branch (default: `main`)
4. **Updates** the target branch (`git pull --ff-only`)
5. **Merges** the feature using your chosen strategy
6. **Optionally pushes** to origin
7. **Removes** the feature worktree (if in one)
8. **Deletes** the feature branch

## Usage

### Basic merge (default: merge commit, cleanup everything)

```bash
spec-kitty merge
```

This will:
- Create a merge commit
- Remove the worktree
- Delete the feature branch
- Keep changes local (no push)

### Merge with options

```bash
# Squash all commits into one
spec-kitty merge --strategy squash

# Push to origin after merging
spec-kitty merge --push

# Keep the feature branch
spec-kitty merge --keep-branch

# Keep the worktree
spec-kitty merge --keep-worktree

# Merge into a different branch
spec-kitty merge --target develop

# See what would happen without doing it
spec-kitty merge --dry-run
```

### Common workflows

```bash
# Feature complete, squash and push
spec-kitty merge --strategy squash --push

# Keep branch for reference
spec-kitty merge --keep-branch

# Merge into develop instead of main
spec-kitty merge --target develop --push
```

## Merge Strategies

### `merge` (default)
Creates a merge commit preserving all feature branch commits.
```bash
spec-kitty merge --strategy merge
```
✅ Preserves full commit history
✅ Clear feature boundaries in git log
❌ More commits in main branch

### `squash`
Squashes all feature commits into a single commit.
```bash
spec-kitty merge --strategy squash
```
✅ Clean, linear history on main
✅ Single commit per feature
❌ Loses individual commit details

### `rebase`
Requires manual rebase first (command will guide you).
```bash
spec-kitty merge --strategy rebase
```
✅ Linear history without merge commits
❌ Requires manual intervention
❌ Rewrites commit history

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--strategy` | Merge strategy: `merge`, `squash`, or `rebase` | `merge` |
| `--delete-branch` / `--keep-branch` | Delete feature branch after merge | delete |
| `--remove-worktree` / `--keep-worktree` | Remove feature worktree after merge | remove |
| `--push` | Push to origin after merge | no push |
| `--target` | Target branch to merge into | `main` |
| `--dry-run` | Show what would be done without executing | off |

## Worktree Strategy

Spec Kitty uses an **opinionated worktree approach**:

### The Pattern
```
my-project/                    # Main repo (main branch)
├── .worktrees/
│   ├── 001-auth-system/      # Feature 1 worktree
│   ├── 002-dashboard/        # Feature 2 worktree
│   └── 003-notifications/    # Feature 3 worktree
├── .kittify/
├── kitty-specs/
└── ... (main branch files)
```

### The Rules
1. **Main branch** stays in the primary repo root
2. **Feature branches** live in `.worktrees/<feature-slug>/`
3. **Work on features** happens in their worktrees (isolation)
4. **Merge from worktrees** using this command
5. **Cleanup is automatic** - worktrees removed after merge

### Why Worktrees?
- ✅ Work on multiple features simultaneously
- ✅ Each feature has its own sandbox
- ✅ No branch switching in main repo
- ✅ Easy to compare features
- ✅ Clean separation of concerns

### The Flow
```
1. /spec-kitty.specify           → Creates branch + worktree
2. cd .worktrees/<feature>/      → Enter worktree
3. /spec-kitty.plan              → Work in isolation
4. /spec-kitty.tasks
5. /spec-kitty.implement
6. /spec-kitty.review
7. /spec-kitty.accept
8. /spec-kitty.merge             → Merge + cleanup worktree
9. Back in main repo!            → Ready for next feature
```

## Error Handling

### "Already on main branch"
You're not on a feature branch. Switch to your feature branch first:
```bash
cd .worktrees/<feature-slug>
# or
git checkout <feature-branch>
```

### "Working directory has uncommitted changes"
Commit or stash your changes:
```bash
git add .
git commit -m "Final changes"
# or
git stash
```

### "Could not fast-forward main"
Your main branch is behind origin:
```bash
git checkout main
git pull
git checkout <feature-branch>
spec-kitty merge
```

### "Merge failed - conflicts"
Resolve conflicts manually:
```bash
# Fix conflicts in files
git add <resolved-files>
git commit
# Then complete cleanup manually:
git worktree remove .worktrees/<feature>
git branch -d <feature-branch>
```

## Safety Features

1. **Clean working directory check** - Won't merge with uncommitted changes
2. **Fast-forward only pull** - Won't proceed if main has diverged
3. **Graceful failure** - If merge fails, you can fix manually
4. **Optional operations** - Push, branch delete, and worktree removal are configurable
5. **Dry run mode** - Preview exactly what will happen

## Examples

### Complete feature and push
```bash
cd .worktrees/001-auth-system
/spec-kitty.accept
/spec-kitty.merge --push
```

### Squash merge for cleaner history
```bash
spec-kitty merge --strategy squash --push
```

### Merge but keep branch for reference
```bash
spec-kitty merge --keep-branch --push
```

### Check what will happen first
```bash
spec-kitty merge --dry-run
```

## After Merging

After a successful merge, you're back on the main branch with:
- ✅ Feature code integrated
- ✅ Worktree removed (if it existed)
- ✅ Feature branch deleted (unless `--keep-branch`)
- ✅ Ready to start your next feature!

## Integration with Accept

The typical flow is:

```bash
# 1. Run acceptance checks
/spec-kitty.accept --mode local

# 2. If checks pass, merge
/spec-kitty.merge --push
```

Or combine conceptually:
```bash
# Accept verifies readiness
/spec-kitty.accept --mode local

# Merge performs integration
/spec-kitty.merge --strategy squash --push
```

The `/spec-kitty.accept` command **verifies** your feature is complete.
The `/spec-kitty.merge` command **integrates** your feature into main.

Together they complete the workflow:
```
specify → plan → tasks → implement → review → accept → merge ✅
```
