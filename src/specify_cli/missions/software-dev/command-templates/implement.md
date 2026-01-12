---
description: Create an isolated workspace (worktree) for implementing a specific work package.
---

# /spec-kitty.implement - Create Workspace for Work Package

**Version**: 0.11.0+
**Purpose**: Create an isolated workspace (git worktree) for implementing a specific work package.

## CRITICAL: This is a TWO-STEP Command

**Step 1**: Get the WP prompt and implementation instructions
```bash
spec-kitty agent workflow implement WP##
```
This displays the full WP prompt with detailed requirements and shows:
```
WHEN YOU'RE DONE:
================================================================================
✓ Implementation complete and tested:
  spec-kitty agent tasks move-task WP## --to for_review --note "Ready for review"
```

**Step 2**: Create the workspace (if needed) and implement according to the prompt
```bash
spec-kitty implement WP##              # No dependencies (branches from main)
spec-kitty implement WP## --base WPXX  # With dependencies (branches from base WP)
```

## Completion Requirements

**Your work is NOT complete until**:
1. ✅ **Set assignee when starting**: `spec-kitty agent tasks move-task WP## --to doing --assignee <your-name>`
2. ✅ **Mark each subtask complete after finishing it**: `spec-kitty agent tasks mark-status T001 --status done`
3. ✅ All subtasks in WP prompt are marked `[x]` in tasks.md
4. ✅ All tests pass (if required)
5. ✅ Changes committed to the WP workspace
6. ✅ **WP moved to for_review lane**: `spec-kitty agent tasks move-task WP## --to for_review --note "Ready for review"`

**IMPORTANT - Two-Tier Tracking**:
- **Work Package Level**: WP file in `tasks/WP##-*.md` with `lane:` frontmatter (updated by `move-task`)
- **Subtask Level**: Checkboxes `- [ ]` / `- [x]` in `tasks.md` (updated by `mark-status`)
- **Both must be complete** before moving to `for_review` - the system will block you if subtasks are unchecked

**The WP file location determines status**:
- In `tasks/WP##-*.md` with `lane: "doing"` = IN PROGRESS (not done)
- Need to move to `for_review` lane when complete

## When to Use

After `/spec-kitty.tasks` generates work packages in the main repository:
- Planning artifacts (spec, plan, tasks) are already in main
- Run `spec-kitty agent workflow implement WP01` to get the full prompt
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

## Implementation Workflow Example

**Correct workflow with subtask tracking (Issue #72)**:
```bash
# 1. Create workspace and claim task
spec-kitty implement WP01
cd .worktrees/###-feature-WP01
spec-kitty agent tasks move-task WP01 --to doing --assignee claude

# 2. Implement first subtask (T001)
# ... write code ...
git add . && git commit -m "Implement T001"
spec-kitty agent tasks mark-status T001 --status done

# 3. Implement second subtask (T002)
# ... write code ...
git add . && git commit -m "Implement T002"
spec-kitty agent tasks mark-status T002 --status done

# 4. Implement remaining subtasks
# ... repeat for T003, T004, etc. ...

# 5. After ALL subtasks complete and tests pass
spec-kitty agent tasks move-task WP01 --to for_review --note "All subtasks complete, ready for review"
# System validates all subtasks are [x] before allowing move
```

**What NOT to do**:
```bash
# ❌ Moving to for_review without marking subtasks
spec-kitty agent tasks move-task WP01 --to for_review
# ERROR: Cannot move WP01 to for_review - unchecked subtasks:
#   - [ ] T001 Change FK ondelete RESTRICT → CASCADE
#   - [ ] T003 Integrate uniqueness check into create_finished_unit()

# ❌ Missing --assignee when starting
spec-kitty agent tasks move-task WP01 --to doing
# Warning: No assignee set (will cause acceptance failure)
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
# 1. Get the full WP prompt and instructions
spec-kitty agent workflow implement WP##

# 2. Read the "WHEN YOU'RE DONE" section at the top of the prompt
# It will show exactly what command to run when complete:
#   spec-kitty agent tasks move-task WP## --to for_review --note "..."

# 3. Create workspace (if not exists)
spec-kitty implement WP##              # Or with --base if dependencies

# 4. Navigate to workspace
cd .worktrees/###-feature-WP##/

# 5. Implement according to WP prompt
# ... write code, run tests, commit changes ...

# 6. Move to for_review (REQUIRED - not optional!)
spec-kitty agent tasks move-task WP## --to for_review --note "Ready for review"
```

**IMPORTANT**: Step 6 is MANDATORY. The WP is NOT complete until moved to `for_review` lane.

## Lane Status

Work packages move through lanes:
- `planned` → Initial state after `/spec-kitty.tasks`
- `doing` → Agent is implementing (automatically set by workflow command)
- `for_review` → Implementation complete, waiting for review ← **YOU MUST MOVE HERE**
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
- Check: Did you move to for_review? `spec-kitty agent tasks move-task WP## --to for_review`
- The WP file must be moved to for_review lane for the workflow to continue
