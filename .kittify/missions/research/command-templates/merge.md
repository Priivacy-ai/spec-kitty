---
description: Merge a completed feature into the main branch and clean up worktree
---

# Merge Feature Branch

This command merges a completed feature branch into the main/target branch and handles cleanup of worktrees and branches.

## Prerequisites

Before running this command:

1. ✅ Feature must pass `/spec-kitty.accept` checks
2. ✅ All work packages must be in `tasks/`
3. ✅ Working directory must be clean (no uncommitted changes)
4. ✅ You must be on the feature branch (or in its worktree)

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

**Correct the issue:**
1. Navigate to your feature worktree: `cd .worktrees/001-feature-name`
2. Verify you're on the correct feature branch: `git branch --show-current`
3. Then run this merge command again

**Exception (main branch):**
If you are on `main` and need to merge a workspace-per-WP feature, run:
```bash
spec-kitty merge --feature <feature-slug>
```

---

## Location Pre-flight Check (CRITICAL for AI Agents)

Before merging, verify you are in the correct working directory by running this validation:

```bash
python3 -c "
from specify_cli.guards import validate_worktree_location
result = validate_worktree_location()
if not result.is_valid:
    print(result.format_error())
    print('\nThis command MUST run from a feature worktree, not the main repository.')
    print('\nFor workspace-per-WP features, run from ANY WP worktree:')
    print('  cd /path/to/project/.worktrees/<feature>-WP01')
    print('  # or any other WP worktree for this feature')
    raise SystemExit(1)
else:
    print('✓ Location verified:', result.branch_name)
"
```

**What this validates**:
- Current branch follows the feature pattern like `001-feature-name`
- You're not attempting to run from `main` or any release branch
- The validator prints clear navigation instructions if you're outside the feature worktree

**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<feature>/tasks/`). Never refer to a folder by name alone.

## Final Research Integrity Check

Before merging research to main, perform final validation:

```bash
# Quick citation validation
python -c "
from pathlib import Path
from specify_cli.validators.research import validate_citations, validate_source_register

feature_dir = Path('kitty-specs/$FEATURE_SLUG')
evidence = feature_dir / 'research' / 'evidence-log.csv'
sources = feature_dir / 'research' / 'source-register.csv'

if evidence.exists():
    result = validate_citations(evidence)
    if result.has_errors:
        print('ERROR: Evidence log has citation errors')
        exit(1)

if sources.exists():
    result = validate_source_register(sources)
    if result.has_errors:
        print('ERROR: Source register has errors')
        exit(1)

print('✓ Citations validated')
"
```

## What This Command Does

1. **Detects** your current feature branch and worktree status
2. **Runs** pre-flight validation across all worktrees and the target branch
3. **Determines** merge order based on WP dependencies (workspace-per-WP)
4. **Forecasts** conflicts during `--dry-run` and flags auto-resolvable status files
5. **Verifies** working directory is clean (legacy single-worktree)
6. **Switches** to the target branch (default: `main`)
7. **Updates** the target branch (`git pull --ff-only`)
8. **Merges** the feature using your chosen strategy
9. **Auto-resolves** status file conflicts after each WP merge
10. **Optionally pushes** to origin
11. **Removes** the feature worktree (if in one)
12. **Deletes** the feature branch

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

# Run merge from main for a workspace-per-WP feature
spec-kitty merge --feature 017-feature-slug
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
| `--feature` | Feature slug when merging from main branch | none |
| `--resume` | Resume an interrupted merge | off |

## Worktree Strategy

Spec Kitty uses an **opinionated worktree approach**:

### Workspace-per-WP Model (0.11.0+)

In the current model, each work package gets its own worktree:

```
my-project/                              # Main repo (main branch)
├── .worktrees/
│   ├── 001-auth-system-WP01/           # WP01 worktree
│   ├── 001-auth-system-WP02/           # WP02 worktree
│   ├── 001-auth-system-WP03/           # WP03 worktree
│   └── 002-dashboard-WP01/             # Different feature
├── .kittify/
├── kitty-specs/
└── ... (main branch files)
```

**Merge behavior for workspace-per-WP**:
- Run `spec-kitty merge` from **any** WP worktree for the feature
- The command automatically detects all WP branches (WP01, WP02, WP03, etc.)
- Merges each WP branch into main in sequence
- Cleans up all WP worktrees and branches

### Legacy Pattern (0.10.x)
```
my-project/                    # Main repo (main branch)
├── .worktrees/
│   ├── 001-auth-system/      # Feature 1 worktree (single)
│   ├── 002-dashboard/        # Feature 2 worktree (single)
│   └── 003-notifications/    # Feature 3 worktree (single)
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
