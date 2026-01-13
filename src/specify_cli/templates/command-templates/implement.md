---
description: Create an isolated workspace (worktree) for implementing a specific work package.
---

# /spec-kitty.implement - Create Workspace for Work Package

**Version**: 0.11.0+
**Purpose**: Create an isolated workspace (git worktree) for implementing a specific work package.

## CRITICAL: This is a TWO-STEP Command

**Step 1**: Get the WP prompt and implementation instructions (then continue immediately to Step 2; do not pause for confirmation)
```bash
spec-kitty agent workflow implement WP##
```
This displays the full WP prompt with detailed requirements and shows:
```
WHEN YOU'RE DONE:
================================================================================
✓ Implementation complete and tested:
  The workflow auto-moves the work package to for_review.
```

**Step 2**: Create the workspace (if needed) and implement according to the prompt
```bash
spec-kitty implement WP##              # No dependencies (branches from main)
spec-kitty implement WP## --base WPXX  # With dependencies (branches from base WP)
```

## Completion Requirements

**Your work is NOT complete until**:
1. ✅ All subtasks in WP prompt are finished
2. ✅ All tests pass (if required)
3. ✅ Changes committed to the WP workspace
4. ✅ **WP moved to for_review lane** automatically by the workflow command

**The WP file location determines status**:
- In `tasks/WP##-*.md` with `lane: "doing"` = IN PROGRESS (not done)
- `for_review` is set by the workflow command (no manual move needed)

## When to Use

After `/spec-kitty.tasks` generates work packages in the main repository:
- Planning artifacts (spec, plan, tasks) are already in main
- Run `spec-kitty agent workflow implement WP01` to get the full prompt, then continue with workspace setup and implementation
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

## Complete Implementation Workflow

**ALWAYS follow this sequence**:

```bash
# 1. Get the full WP prompt and instructions (then continue immediately)
spec-kitty agent workflow implement WP##

# 2. Read the "WHEN YOU'RE DONE" section at the top of the prompt
# The workflow handles lane transitions automatically.

# 3. Create workspace (if not exists)
spec-kitty implement WP##              # Or with --base if dependencies

# 4. Navigate to workspace
cd .worktrees/###-feature-WP##/

# 5. Implement according to WP prompt
# ... write code, run tests, commit changes ...

```

**IMPORTANT**: The workflow command is responsible for moving the WP to `for_review`.

## Lane Status

Work packages move through lanes:
- `planned` → Initial state after `/spec-kitty.tasks`
- `doing` → Agent is implementing (automatically set by workflow command)
- `for_review` → Implementation complete, waiting for review
- `done` → Review passed, WP complete

**Check current lane**:
```bash
grep "^lane:" kitty-specs/###-feature/tasks/WP##-*.md
```

## Troubleshooting

**Error: "Base workspace WP01 does not exist"**
- Solution: Implement WP01 first: `spec-kitty implement WP01`

**Error: "WP02 has dependencies. Use: spec-kitty implement WP02 --base WP01"**
- Solution: Add --base flag as suggested

**Warning: "Base branch has changed. Consider rebasing..."**
- Solution: Run suggested rebase command (git limitation, fixed in future jj integration)

**"I finished implementing but nothing happened"**
- Re-run the workflow command to ensure the lane transition is applied.
