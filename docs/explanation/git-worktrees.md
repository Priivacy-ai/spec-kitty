# Git Worktrees Explained

Git worktrees are the technology that enables Spec Kitty's parallel development model. This document explains what worktrees are, why Spec Kitty uses them, and how they work.

## What is a Git Worktree?

A git worktree is a linked working directory that lets you check out multiple branches simultaneously, each in its own directory. Unlike cloning a repository multiple times, all worktrees share the same `.git` directory and repository history.

**Normal git workflow** (one branch at a time):
```bash
# You can only have one branch checked out
git checkout feature-a
# To work on feature-b, you must switch branches
git checkout feature-b  # Now you're on feature-b, feature-a is gone
```

**With worktrees** (multiple branches simultaneously):
```bash
# Main repo stays on main branch
my-repo/               # main branch

# Each worktree has its own branch
.worktrees/feature-a/  # feature-a branch
.worktrees/feature-b/  # feature-b branch
```

You can now have three terminal windows open, each in a different directory, each on a different branch, all editing the same repository.

## Why Does Spec Kitty Use Worktrees?

### Parallel Development Without Branch Switching

Without worktrees, only one developer (or agent) can work at a time because git only allows one branch checked out per repository. With worktrees:

- Agent A works in `.worktrees/feature-WP01/` on WP01
- Agent B works in `.worktrees/feature-WP02/` on WP02
- Agent C works in `.worktrees/feature-WP03/` on WP03

All three agents work simultaneously, each with their own files, their own uncommitted changes, and their own branch.

### Each Work Package Gets Isolated Workspace

Problems with shared workspaces:
- Agent A edits `config.py`, breaks it
- Agent B (working on unrelated task) tries to run tests—they fail
- Both agents are now debugging each other's problems

With workspace-per-WP:
- Agent A's broken `config.py` only exists in WP01's workspace
- Agent B's workspace has clean files
- Isolation prevents cross-contamination

### Multiple Agents Can Work Simultaneously

Spec Kitty's parallel model requires:
1. Multiple independent branches
2. Multiple independent working directories
3. Shared repository history (for merging later)

Git worktrees provide all three.

## How Worktrees Work

### The .git Directory

When you clone a repository, git creates a `.git` directory containing:
- All commits
- All branches
- All tags
- Repository configuration

A worktree doesn't duplicate this. Instead, it creates a small file that points back to the main `.git` directory.

```
my-repo/
├── .git/                     # The real git database
├── src/                      # Your source files
├── .worktrees/
│   ├── feature-WP01/
│   │   ├── .git              # Just a pointer file
│   │   └── src/              # Separate copy of source files
│   └── feature-WP02/
│       ├── .git              # Just a pointer file
│       └── src/              # Another separate copy
```

### What Worktrees Share

All worktrees share:
- Commit history (all commits are in one place)
- Branch definitions (branches exist in main `.git`)
- Configuration (global git settings)
- Remote references (origin, upstream, etc.)

### What Worktrees Don't Share

Each worktree has its own:
- Working directory (files on disk)
- Index (staging area)
- Current HEAD (which commit is checked out)
- Uncommitted changes

This means Agent A can have uncommitted changes to `config.py` without affecting Agent B's `config.py`.

## Worktrees vs. Cloning

| Aspect | Worktree | Clone |
|--------|----------|-------|
| **Repository data** | Shared | Duplicated |
| **Disk space** | Minimal | Full copy |
| **Branches** | Shared | Independent |
| **Fetching/pushing** | Once for all | Once per clone |
| **Merging between** | Direct (same repo) | Requires remote |
| **Independence** | Partial | Complete |

**Use worktrees when**:
- Working on the same project
- Need to merge branches together later
- Want to minimize disk usage

**Use clones when**:
- Working on different projects
- Complete isolation is required
- May never merge together

## Git Commands for Worktrees

### List All Worktrees

```bash
git worktree list
```

Example output:
```
/path/to/my-repo               abc1234 [main]
/path/to/my-repo/.worktrees/feature-WP01  def5678 [feature-WP01]
/path/to/my-repo/.worktrees/feature-WP02  ghi9012 [feature-WP02]
```

### Create a New Worktree

```bash
# Create worktree with existing branch
git worktree add .worktrees/feature-WP01 feature-WP01

# Create worktree and create new branch
git worktree add -b feature-WP01 .worktrees/feature-WP01

# Create worktree from specific commit/branch
git worktree add -b feature-WP02 .worktrees/feature-WP02 feature-WP01
```

### Remove a Worktree

```bash
# Clean removal (worktree must be clean)
git worktree remove .worktrees/feature-WP01

# Force removal (discards uncommitted changes)
git worktree remove --force .worktrees/feature-WP01
```

### Clean Up Stale Worktrees

```bash
# Prune worktrees whose directories no longer exist
git worktree prune
```

## Sparse Checkouts

A sparse checkout limits which files appear in your working directory. Combined with worktrees, this allows each WP workspace to have only the files it needs.

**Without sparse checkout**:
```
.worktrees/feature-WP01/
├── docs/           # Agent doesn't need docs
├── tests/          # Agent doesn't need tests
├── src/
│   └── module.py   # Agent only needs this
└── README.md       # Agent doesn't need this
```

**With sparse checkout**:
```
.worktrees/feature-WP01/
└── src/
    └── module.py   # Only what the agent needs
```

Spec Kitty uses sparse checkouts to:
- Keep the `kitty-specs/` directory only in the main repo
- Reduce noise in WP workspaces
- Ensure status tracking stays centralized

### Configure Sparse Checkout

```bash
# Enable sparse checkout
git sparse-checkout init --cone

# Include only specific paths
git sparse-checkout set src/ tests/
```

## Common Issues

### "Worktree already exists"

**Error**:
```
fatal: 'feature-WP01' already has a worktree at '.worktrees/feature-WP01'
```

**Cause**: You're trying to create a worktree for a branch that's already checked out somewhere.

**Solution**:
```bash
# Find where it's checked out
git worktree list

# Either remove the existing worktree
git worktree remove .worktrees/feature-WP01

# Or use that existing worktree instead
cd .worktrees/feature-WP01
```

### "Branch is already checked out"

**Error**:
```
fatal: 'feature-WP01' is already checked out at '/path/to/other/worktree'
```

**Cause**: Git won't let two worktrees have the same branch checked out.

**Solution**:
```bash
# Find the other worktree
git worktree list

# Remove it if not needed
git worktree remove /path/to/other/worktree

# Or work in the existing worktree
cd /path/to/other/worktree
```

### Cleanup After Crashes

If Spec Kitty or your system crashes mid-operation, worktrees may be left in an inconsistent state.

**Symptoms**:
- `git worktree list` shows non-existent directories
- Errors about locked worktrees
- Can't create new worktrees

**Solution**:
```bash
# Clean up stale worktree references
git worktree prune

# Force unlock if needed
git worktree unlock .worktrees/stuck-worktree

# Verify cleanup
git worktree list
```

### HEAD Detached in Worktree

**Symptom**: Commits in worktree aren't on any branch.

**Cause**: Worktree was created from a commit, not a branch.

**Solution**:
```bash
cd .worktrees/feature-WP01
git checkout -b feature-WP01  # Create and switch to branch
```

## Further Reading

- [Git Worktree Documentation](https://git-scm.com/docs/git-worktree) - Official git documentation
- [Git Sparse Checkout](https://git-scm.com/docs/git-sparse-checkout) - Sparse checkout documentation

## See Also

- [Workspace-per-WP Model](workspace-per-wp.md) - How Spec Kitty uses worktrees
- [Spec-Driven Development](spec-driven-development.md) - The methodology that requires parallel work
- [Kanban Workflow](kanban-workflow.md) - How work progresses through lanes

---

*This document explains git worktrees for understanding. For practical steps in Spec Kitty, see the how-to guides.*

## Try It
- [Claude Code Workflow](../tutorials/claude-code-workflow.md)

## How-To Guides
- [Upgrade to 0.11.0](../how-to/upgrade-to-0-11-0.md)
- [Install Spec Kitty](../how-to/install-spec-kitty.md)

## Reference
- [File Structure](../reference/file-structure.md)
- [CLI Commands](../reference/cli-commands.md)
