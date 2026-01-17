# Jujutsu for Multi-Agent Development

**Divio type**: Explanation

This document explains why Spec Kitty recommends jujutsu (jj) for multi-agent parallel development workflows, and when git remains the appropriate choice.

## The Multi-Agent Challenge

When multiple AI agents (or humans) work on a feature simultaneously, each in their own workspace, three coordination problems emerge:

1. **Dependency synchronization**: When WP01 changes, WP02 (which depends on WP01) needs those changes
2. **Conflict handling**: Two agents may modify the same file
3. **History management**: Mistakes happen; agents need safe undo capabilities

Git handles these problems, but requires manual intervention. Jujutsu automates them.

## Why jj is Preferred

### Automatic Rebasing

In git, when a parent work package changes, dependent workspaces must be manually rebased:

```bash
# Git: Manual rebase required
cd .worktrees/###-feature-WP02/
git fetch origin
git rebase origin/###-feature-WP01
# May have conflicts - blocks agent
```

In jj, dependent changes are automatically rebased when you sync:

```bash
# jj: Automatic rebase
cd .worktrees/###-feature-WP02/
spec-kitty sync
# Changes automatically rebased - agent continues
```

This matters because multi-agent workflows involve frequent dependency updates. With three agents and five work packages, manual rebasing becomes a significant overhead.

### Non-Blocking Conflicts

Git conflicts halt work. When `git rebase` encounters a conflict, you must resolve it before continuing:

```bash
# Git: Conflicts block progress
git rebase origin/main
# CONFLICT (content): Merge conflict in config.py
# Agent is stuck until conflict is resolved
```

jj stores conflicts in the working copy without blocking:

```bash
# jj: Conflicts stored, work continues
spec-kitty sync
# Conflict in config.py - stored as conflict markers
# Agent can continue working on other files
```

The agent can finish implementing other parts of the work package, then address conflicts when ready. This keeps momentum and allows human review of complex conflicts.

### Operation History with Undo

Git's reflog exists but is difficult to use safely:

```bash
# Git: Recovery requires expertise
git reflog
# a1b2c3d HEAD@{0}: rebase: finish
# e4f5g6h HEAD@{1}: commit: Add feature
git reset --hard HEAD@{1}  # Dangerous - loses commits
```

jj provides a clear operation log with safe undo:

```bash
# jj: Clear history, safe undo
spec-kitty ops log
#  @  12345abc 2024-01-15 10:30 (current operation)
#  │  commit working copy
#  ○  67890def 2024-01-15 10:15
#  │  edit commit 87654321
spec-kitty ops undo
# Safely reverts to previous state
```

Agents can experiment freely, knowing mistakes are recoverable.

### First-Class Workspaces

Git worktrees are an afterthought—a way to have multiple checkouts of the same repository. They work, but branch handling is manual.

jj workspaces are first-class:

```bash
# jj: Native workspace support
jj workspace add ../feature-WP01
# Automatically tracks the right commit
# Auto-rebases when dependencies change
```

This aligns perfectly with Spec Kitty's workspace-per-WP model.

## When Git is Appropriate

Git remains the right choice when:

### Team Familiarity

If your team knows git and is unfamiliar with jj, the learning curve may slow initial productivity. Git works—jj optimizes.

### Existing CI/CD

If your CI/CD pipeline is deeply integrated with git-specific features (branch protection rules, required checks on branches, GitHub Actions branch triggers), jj's colocated mode helps but adds complexity.

### Collaboration with External Teams

If you collaborate with teams that use git exclusively, a pure git workflow reduces friction. Colocated mode (jj + git) works but requires understanding both tools.

### Simple Workflows

If your work packages rarely have dependencies, or you typically work on one package at a time, git's manual rebasing is infrequent enough to not matter.

## How Spec Kitty Uses jj

### VCS Detection

Spec Kitty detects your VCS based on CLI flags, feature locks, and tool availability. See [VCS Detection Order](../reference/configuration.md#vcs-detection-order) for the full algorithm.

In most cases:
- New features use jj if installed (preferred for multi-agent workflows)
- Existing features use their locked VCS from `meta.json`
- `--vcs git` or `--vcs jj` overrides auto-detection (and errors if it conflicts)

### Colocated Mode

When both `.jj/` and `.git/` exist, Spec Kitty uses jj while maintaining git compatibility:

```
my-project/
├── .jj/           # jj operations
├── .git/          # git compatibility
└── kitty-specs/   # Feature specs
```

This allows gradual migration—start with git, add jj later, keep both.

### Command Abstraction

Spec Kitty commands work the same regardless of backend:

```bash
# Same command, different implementations
spec-kitty sync              # jj: update-stale + auto-rebase, git: rebase base branch
spec-kitty ops log           # jj: operation log, git: reflog
spec-kitty ops undo          # jj only (not supported for git)
```

## The Multi-Agent Difference

Consider a typical multi-agent scenario:

```
        WP01 (Schema)
       /    \
    WP02    WP03
   (API)   (UI)
       \    /
        WP04
      (Integration)
```

### With Git (Manual Coordination)

1. Agent A completes WP01
2. Agent B starts WP02, Agent C starts WP03 (parallel)
3. Agent A reviews WP01, requests changes → modifies schema
4. **Manual step**: Agent B must rebase WP02 onto updated WP01
5. **Manual step**: Agent C must rebase WP03 onto updated WP01
6. Agents B and C complete their work
7. Agent D starts WP04, merging WP02 and WP03
8. **Manual step**: Agent D must handle merge conflicts

### With jj (Automatic Coordination)

1. Agent A completes WP01
2. Agent B starts WP02, Agent C starts WP03 (parallel)
3. Agent A reviews WP01, requests changes → modifies schema
4. **Automatic**: When Agents B and C sync, they get updated WP01
5. Conflicts (if any) are stored, not blocking
6. Agents B and C complete their work
7. Agent D starts WP04 → jj handles multi-parent automatically
8. **Automatic**: Merge is handled; conflicts stored if any

The git workflow requires 3+ manual interventions. The jj workflow requires zero—agents focus on implementation.

## Migration Path

### Starting Fresh

For new projects, initialize with jj:

```bash
spec-kitty init --vcs jj
```

### Adding jj to Git Projects

Enable colocated mode:

```bash
cd my-git-project
jj git init --colocate
```

Now both tools work. Spec Kitty prefers jj when `.jj/` exists.

### Gradual Adoption

1. Install jj alongside git
2. Enable colocated mode
3. Try jj for new features
4. Eventually, use jj as primary

---

## See Also

- [Auto-Rebase and Non-Blocking Conflicts](auto-rebase-and-conflicts.md) - How these features work
- [Git Worktrees Explained](git-worktrees.md) - How git worktrees work
- [Workspace-per-WP Model](workspace-per-wp.md) - Why one workspace per work package

## Try It

- [Jujutsu Workflow Tutorial](../tutorials/jujutsu-workflow.md) - Hands-on jj workflow

## How-To Guides

- [Sync Workspaces](../how-to/sync-workspaces.md) - Keeping workspaces up to date
- [Handle Conflicts (jj)](../how-to/handle-conflicts-jj.md) - Non-blocking conflict resolution

## Reference

- [CLI Commands](../reference/cli-commands.md) - sync, ops commands
- [Configuration](../reference/configuration.md) - VCS configuration options
