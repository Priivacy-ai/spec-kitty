---
description: Merge a completed feature into the main branch and clean up worktree
scripts:
  sh: ".kittify/scripts/bash/merge-feature.sh"
  ps: ".kittify/scripts/powershell/Merge-Feature.ps1"
---
**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<feature>/tasks/`). Never refer to a folder by name alone.

*Path: [templates/commands/merge.md](templates/commands/merge.md)*


# Merge Feature Branch

This command merges a completed feature branch into the main/target branch and handles cleanup of worktrees and branches.

## ⛔ Location Pre-flight Check (CRITICAL)

**BEFORE PROCEEDING:** You MUST be in the feature worktree, NOT the main repository.

Verify your current location:
```bash
pwd
git branch --show-current
```

**Expected output:**
- `pwd`: Should end with `.worktrees/001-feature-name` (or similar feature worktree)
- Branch: Should show your feature branch name like `001-feature-name` (NOT `main` or `release/*`)

**If you see:**
- Branch showing `main` or `release/`
- OR pwd shows the main repository root

⛔ **STOP - DANGER! You are in the wrong location!**

This command merges your feature INTO main. Running from the wrong location can cause:
- Loss of work
- Merge conflicts
- Repository corruption

**Correct the issue:**
1. Navigate to your feature worktree: `cd .worktrees/001-feature-name`
2. Verify you're on the correct feature branch: `git branch --show-current`
3. Then run this merge command again

---

## Prerequisites

Before running this command:

1. ✅ Feature must pass `/spec-kitty.accept` checks
2. ✅ All work packages must be in `tasks/done/`
3. ✅ Working directory must be clean (no uncommitted changes)
4. ✅ Run the command from the feature worktree (Spec Kitty will move the merge to the primary repo automatically)

## What This Command Does

1. **Detects** your current feature branch and worktree status
2. **Verifies** working directory is clean
3. **Switches** to the target branch (default: `main`) in the primary repository
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
4. **Merge from worktrees** using this command – the CLI will hop to the primary repo for the Git merge
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
2. **Primary repo hand-off** - Automatically runs Git operations from the main checkout when invoked in a worktree
3. **Fast-forward only pull** - Won't proceed if main has diverged
4. **Graceful failure** - If merge fails, you can fix manually
5. **Optional operations** - Push, branch delete, and worktree removal are configurable
6. **Dry run mode** - Preview exactly what will happen

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
