---
description: Create an isolated workspace (worktree) for implementing a specific work package.
---

# /spec-kitty.implement - Create Workspace for Work Package

**Version**: 0.11.0+
**Purpose**: Create an isolated workspace (git worktree) for implementing a specific work package.

## Command Syntax

```bash
spec-kitty implement WP##              # No dependencies (branches from main)
spec-kitty implement WP## --base WPXX  # With dependencies (branches from base WP)
```

## When to Use

After `/spec-kitty.tasks` generates work packages in the main repository:
- Planning artifacts (spec, plan, tasks) are already in main
- Run `spec-kitty implement WP01` to create a workspace for the first WP
- Run `spec-kitty implement WP02 --base WP01` if WP02 depends on WP01
- Each WP gets its own isolated worktree in `.worktrees/###-feature-WP##/`

## Workflow

**Planning Phase** (main repo, no worktrees):
```
/spec-kitty.specify → Creates spec.md in main
/spec-kitty.plan → Creates plan.md in main
/spec-kitty.tasks → Creates tasks/*.md in main
```

**Implementation Phase** (creates worktrees on-demand):
```
spec-kitty implement WP01 → Creates .worktrees/###-feature-WP01/
spec-kitty implement WP02 --base WP01 → Creates .worktrees/###-feature-WP02/
```

## Examples

**Independent WP** (no dependencies):
```bash
spec-kitty implement WP01
# Creates: .worktrees/010-workspace-per-wp-WP01/
# Branches from: main
# Contains: Planning artifacts (spec, plan, tasks)
```

**Dependent WP**:
```bash
spec-kitty implement WP02 --base WP01
# Creates: .worktrees/010-workspace-per-wp-WP02/
# Branches from: 010-workspace-per-wp-WP01 branch
# Contains: Planning artifacts + WP01's code changes
```

## Validation

The command validates:
- Base workspace exists (if --base specified)
- Suggests --base if WP has dependencies in frontmatter
- Errors if trying to branch from a non-existent base

## Parallel Development

Multiple agents can implement different WPs simultaneously:
```bash
# Agent A
spec-kitty implement WP01

# Agent B (in parallel)
spec-kitty implement WP03

# Both work in isolated worktrees without conflicts
```

## Dependencies

Work package dependencies are declared in frontmatter:
```yaml
dependencies: ["WP01"]  # This WP depends on WP01
```

The implement command reads this field and validates the --base flag matches.

## Troubleshooting

**Error: "Base workspace WP01 does not exist"**
- Solution: Implement WP01 first: `spec-kitty implement WP01`

**Error: "WP02 has dependencies. Use: spec-kitty implement WP02 --base WP01"**
- Solution: Add --base flag as suggested

**Warning: "Base branch has changed. Consider rebasing..."**
- Solution: Run suggested rebase command (git limitation, fixed in future jj integration)
