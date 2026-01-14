# Infrastructure Fixes (Out of Scope for Feature 012)

**NOTE**: This document tracks critical infrastructure fixes made during feature 012 development that are OUT OF SCOPE for the documentation mission feature but necessary for the workspace-per-WP system to function correctly.

**Feature Context**: 012-documentation-mission
**Infrastructure Work Done**: 2026-01-13
**Affected Systems**: Workspace-per-work-package (feature 010), workflow commands, template propagation
**Branch**: 012-documentation-mission-WP04
**Commits**: 28d1422, 38292a7, 3c69d5b, 35cbba7

---

## Problem Discovery

While implementing feature 012 (documentation mission), we discovered **WP03 (Divio Templates)** was in a corrupted state:

- **WP03 worktree**: File showed `lane: "for_review"`
- **WP04 worktree**: File showed `lane: "planned"`
- **Main repo**: File showed `lane: "planned"`

**Root cause**: Each worktree had its own COPY of `kitty-specs/` files. When agents updated WP status, changes were LOCAL to that worktree's branch and never propagated.

---

## Critical Fix #1: Worktree State Sync (Jujutsu-Aligned)

**UPDATED 2026-01-13**: Switched from symlinks to **git sparse-checkout** (proper solution).

### The Problem

Each worktree branch contained a copy of `kitty-specs/###-feature/tasks/*.md`. Status updates were local - other worktrees never saw them.

### The Solution

**Git Sparse-Checkout** (Native Git Feature):

1. **Use sparse-checkout to exclude kitty-specs/** (implement.py:583-616)
   ```python
   # Enable sparse-checkout for worktree
   git config core.sparseCheckout true

   # Write pattern to .git/info/sparse-checkout
   /*           # Include everything at root level
   !/kitty-specs/   # Exclude kitty-specs/ directory

   # Apply (removes kitty-specs/ from working tree)
   git read-tree -mu HEAD
   ```

2. **Auto-commit changes to main** (tasks.py, workflow.py)
   - move-task: Commits WP file changes to main
   - mark-status: Commits tasks.md changes to main
   - workflow implement/review: Commits when claiming WPs

3. **Helper script** for existing worktrees (fix-worktrees-to-sparse-checkout.sh)

### Result

```
Main branch:
  kitty-specs/ (directory) → Single source of truth, fully tracked

Worktree branches:
  kitty-specs/ (NOT PRESENT) → Excluded via sparse-checkout
  Agents read from: /main/kitty-specs/ (absolute paths)
  Agents write to: /main/kitty-specs/ (auto-commits to main)

Benefits:
  - Clean merges (git knows kitty-specs/ isn't in worktree)
  - Native git (not a hack)
  - Jujutsu-aligned (partial working copies)
```

### Why Sparse-Checkout > Symlinks

| Aspect | Symlinks (Initial) | Sparse-Checkout (Final) |
|--------|-------------------|-------------------------|
| Merge conflicts | Yes (180+ conflicts) | No (git understands) |
| Native git | No (filesystem trick) | Yes (designed for this) |
| Complexity | High (symlink+gitignore+git rm) | Low (one pattern file) |
| Correctness | Workaround | Proper solution |
| Jujutsu migration | Need to rewrite | Direct mapping to jj sparse |

**Decision point**: After merging WP01 caused 180 conflicts, switched to sparse-checkout. This is the **superior long-term solution**.

### Jujutsu Alignment

| Jujutsu | Sparse-Checkout Solution |
|---------|--------------------------|
| Partial working copies | Sparse-checkout |
| Commit graph (centralized status) | Main branch (centralized status) |
| Query from any working copy | Read from main (absolute paths) |
| Auto-tracking | Auto-commit to main |
| Local-only | Local-only |

**Migration path**: Replace sparse-checkout with jj's sparse support. Same mental model, native jj feature.

### Files Modified

- `src/specify_cli/cli/commands/implement.py` (~30 lines)
- `src/specify_cli/cli/commands/agent/tasks.py` (~70 lines for auto-commit)
- `src/specify_cli/cli/commands/agent/workflow.py` (~40 lines for auto-commit)
- `fix-worktrees-to-sparse-checkout.sh` (+95 lines, conversion script)

### Commits

- `38292a7` - Initial symlink solution (replaced)
- `3c69d5b` - Auto-commit implementation (kept)
- `35cbba7` - PID tracking + finalize (kept)
- (Pending) - Switch from symlinks to sparse-checkout

---

## Critical Fix #2: Workflow Command State Corruption

### The Problem

- Instructions at TOP, then 1312 lines of prompt → agents forgot what to do
- Manual file editing required → error-prone
- No agent tracking → abandoned WPs
- Only 3/12 agents had templates

### The Solution

**4-Part Fix**:

1. **Repeat instructions at END** (workflow.py:459-495)
   - Visual markers before/after prompt
   - Completion commands after 1312 lines
   - Impossible to miss

2. **Automate feedback** (tasks.py:243-351)
   - New: `--review-feedback-file feedback.md`
   - Auto-inserts into ## Review Feedback section
   - No manual editing!

3. **Require --agent** (workflow.py:204-211, 444-451)
   - Tracks WHO is working
   - Prevents anonymous abandoned WPs

4. **Update all 12 agents** (m_0_11_2_improved_workflow_templates.py)
   - Migration propagates to ALL agents
   - Templates warn: "scroll to BOTTOM"
   - Templates show --agent requirement

### Impact

| Before | After |
|--------|-------|
| Manual editing | Eliminated |
| 2+ commands | 1 command |
| Instructions buried | At END |
| No tracking | Required --agent |
| 3/12 agents | 12/12 agents |

### Files: workflow.py (+80), tasks.py (+87), review.md (rewritten: 23 lines), m_0_11_2 (+185)
### Commits: 28d1422

---

## Critical Fix #3: PID Tracking Restoration

### The Problem

Feature 010 originally had PID tracking but it was lost. Cannot detect abandoned WPs.

### The Solution

```python
shell_pid = str(os.getppid())
updated_front = set_scalar(updated_front, "shell_pid", shell_pid)
```

Captured in: workflow implement, workflow review

### Result

```yaml
shell_pid: "45599"  # In frontmatter
```

```markdown
- 2026-01-13T09:38:02Z – agent – shell_pid=45599 – lane=doing – ...
```

### Files: workflow.py (+12 per function)
### Commits: 35cbba7

---

## Critical Fix #4: Feature Slug Detection

### The Problem

From worktree: branch `012-documentation-mission-WP04` → detected as slug `012-documentation-mission-WP04` → Error "no tasks directory"

### The Solution

```python
branch_name = re.sub(r'-WP\d+$', '', branch_name)
# "012-documentation-mission-WP04" → "012-documentation-mission"
```

### Files: tasks.py (+3)
### Commits: 35cbba7

---

## Complete Working Flow

```bash
# Claim WP
spec-kitty agent workflow implement WP03 --agent claude
✓ Claimed WP03 (agent: claude, PID: 12345)
→ Commits to main, all worktrees see instantly

# Mark subtasks
spec-kitty agent tasks mark-status T001 --status done
→ Commits to main, all worktrees see instantly

# Complete
spec-kitty agent tasks move-task WP03 --to for_review
→ Commits to main, all worktrees see instantly

# Review with feedback
cat > feedback.md <<EOF
**Issue**: Missing error handling
EOF
spec-kitty agent tasks move-task WP03 --to planned --review-feedback-file feedback.md
→ Feedback auto-inserted, commits to main, all see instantly

# Re-implement and approve
spec-kitty agent workflow implement WP03 --agent claude  # Sees feedback
spec-kitty agent tasks move-task WP03 --to for_review
spec-kitty agent workflow review WP03 --agent codex
spec-kitty agent tasks move-task WP03 --to done
→ All done, all worktrees know it
```

---

## Future: When We Add Jujutsu

**Remove** (~60 lines):
- Sparse-checkout configuration code
- Auto-commit code

**Replace with** (~40 lines):
```python
# jj sparse set to exclude kitty-specs/ from working copies
jj sparse set --clear --add '!kitty-specs/**'

# jj describe for status changes (like our auto-commit)
jj describe -m "chore: Move {task_id} to {lane} [{agent}]"
```

**Keep** (~400 lines):
- Agent tracking
- PID tracking
- Validation
- Feedback automation
- Workflow output

**Effort**: 1-2 hours (sparse-checkout → jj sparse is direct mapping)

---

## Lessons Learned

1. **Dogfood early**: Issues found during real usage (feature 012)
2. **Long output buries instructions**: Always repeat at END
3. **Manual editing fails**: Automate everything
4. **Track ownership**: Required --agent prevents confusion
5. **Template propagation matters**: Update all 12 agents, not just 3
6. **Use native git features**: Sparse-checkout > symlinks (no merge conflicts)
7. **Test merge early**: 180 conflicts revealed symlink approach was wrong
8. **Document out-of-scope fixes**: Future developers need this context

---

## Files Modified (Summary)

| File | Purpose | Lines |
|------|---------|-------|
| implement.py | Sparse-checkout configuration | +33 |
| tasks.py | Auto-commit + feedback + slug | +150 |
| workflow.py | PID + auto-commit + visual | +80 |
| m_0_11_2_improved_workflow_templates.py | Migration | +185 |
| review.md, implement.md | Templates | Rewritten |
| fix-worktrees-to-sparse-checkout.sh | Conversion helper | +95 |

**Total**: ~543 lines of infrastructure

---

## Commits on Branch 012-documentation-mission-WP04

1. `28d1422` - Workflow command state corruption fixes
2. `38292a7` - Symlink kitty-specs/ solution (initial approach, later replaced)
3. `3c69d5b` - Complete state sync with auto-commit
4. `35cbba7` - PID tracking, feature slug fix, finalize
5. `6c79e3d` - WP sizing guidance rewrite

**Commits on Main After Merge**:

1. `7061c67` - Merged WP01 (cherry-picked src/ only, avoided symlink conflicts)
2. `3f0fc49` - Merged WP02
3. `2f7aebd` - Merged WP03
4. `e57d02f` - Merged WP04 (all infrastructure fixes)
5. `d0c158f` - Switched from symlinks to sparse-checkout (proper solution)

---

## Critical Fix #5: Work Package Sizing Guidance

### The Problem

**Constrained by WP COUNT instead of SIZE**:
- Old guidance: "Target 4-10 work packages. Do not exceed 10 work packages."
- Agents optimized for minimum WP count → packed 20+ subtasks into each WP
- Result: 1312-line WP prompts that overwhelmed implementing agents
- Agents made mistakes, skipped details, cut corners to handle overwhelming context

**Token-conscious agents panic**:
- Seeing "create 10 WPs for complex feature" → agents try to minimize token usage
- Rush through planning to save tokens
- Write brief, vague prompts
- Result: Poor quality planning that costs 10x more tokens during implementation rework

### The Solution

**Rewritten tasks.md command template** (567 lines) with SIZE-FIRST guidance:

#### Part 1: Quality-Over-Speed Messaging (lines 9-23)

```markdown
## ⚠️ CRITICAL: THIS IS THE MOST IMPORTANT PLANNING WORK

**You are creating the blueprint for implementation**. The quality of work packages determines:
- How easily agents can implement the feature
- How parallelizable the work is
- How reviewable the code will be
- Whether the feature succeeds or fails

**QUALITY OVER SPEED**: This is NOT the time to save tokens or rush. Take your time to:
- Understand the full scope deeply
- Break work into clear, manageable pieces
- Write detailed, actionable guidance
- Think through risks and edge cases

**Token usage is EXPECTED and GOOD here**. A thorough task breakdown saves 10x the effort during implementation. Do not cut corners.
```

**Impact**: Agents know this is critical work, invest appropriate effort.

#### Part 2: Size-Based Guidance (lines 103-116, 217-292)

**Removed**:
- ❌ "Target 4-10 work packages"
- ❌ "Do not exceed 10 work packages"

**Added**:
- ✅ "Target: 3-7 subtasks per WP (200-500 line prompts)"
- ✅ "Maximum: 10 subtasks per WP (700 line prompts)"
- ✅ "Complex feature: 80-120 subtasks → 15-20 WPs ← **Totally fine!**"
- ✅ "Very complex: 150+ subtasks → 25-30 WPs ← **Also fine!**"
- ✅ "Better to have 20 focused WPs than 5 overwhelming WPs"

#### Part 3: Sizing Algorithm (lines 358-374)

```
For each cohesive unit of work:
  1. List related subtasks
  2. Count subtasks
  3. Estimate prompt lines (subtasks × 50 lines avg)

  If subtasks <= 7 AND estimated lines <= 500:
    ✓ Good WP size - create it

  Else if subtasks > 10 OR estimated lines > 700:
    ✗ Too large - split into 2+ WPs

  Else if subtasks < 3 AND can merge with related WP:
    → Consider merging (but don't force it)
```

#### Part 4: Validation Requirements (lines 406-414)

```markdown
**CRITICAL VALIDATION**: After generating each prompt:
1. Count lines in the prompt
2. If >700 lines: GO BACK and split the WP
3. If >1000 lines: **STOP - this will fail** - you MUST split it

**Self-check**:
- Subtask count: 3-7? ✓ | 8-10? ⚠️ | 11+? ❌ SPLIT
- Estimated lines: 200-500? ✓ | 500-700? ⚠️ | 700+? ❌ SPLIT
- Can implement in one session? ✓ | Multiple sessions needed? ❌ SPLIT
```

#### Part 5: Common Mistakes Section (lines 462-552)

**MISTAKE 1**: Optimizing for WP Count
- Bad: "I'll create exactly 5-7 WPs" → 20 subtasks per WP
- Good: "Each WP should be 3-7 subtasks. If that means 15 WPs, fine."

**MISTAKE 2**: Token Conservation During Planning
- Bad: "Save tokens with brief prompts" → confused agents, rework
- Good: "Invest tokens now for thorough prompts" → correct first time

**MISTAKE 3**: Mixing Unrelated Concerns
- Bad: "WP03: Misc Backend Work (12 subtasks)"
- Good: Split by concern (User Mgmt, Infrastructure, Admin)

**MISTAKE 4**: Insufficient Detail
- Bad: 20 lines per subtask ("Create endpoint, add validation, test it")
- Good: 60 lines per subtask (specific steps, files, validation criteria, edge cases)

### Benefits

| Aspect | Before | After |
|--------|--------|-------|
| WP count constraint | "4-10 WPs max" | "No limit - optimize for size" |
| Subtasks per WP | 15-25 (too many) | 3-7 (ideal), max 10 |
| Prompt size | 1000-1500 lines | 200-500 lines (ideal), max 700 |
| Agent panic | High (big job, save tokens) | Low (quality emphasized) |
| Quality messaging | None | Prominent at top |
| Validation | None | Required (check sizes) |
| Examples | Minimal | Extensive (good vs bad) |
| Complex feature WP count | 5-7 (forced) | 15-20 (appropriate) |

### Expected Outcomes

**For simple features** (10-15 subtasks):
- Before: 2-3 WPs of 5-7 subtasks each ✓ (Already worked)
- After: 2-4 WPs of 3-5 subtasks each ✓ (Similar, slightly better)

**For medium features** (30-50 subtasks):
- Before: 5-7 WPs of 6-10 subtasks each (prompts: 400-700 lines) ⚠️ (Borderline)
- After: 6-10 WPs of 4-6 subtasks each (prompts: 250-400 lines) ✓ (Much better)

**For complex features** (80-120 subtasks):
- Before: 8-10 WPs of 10-15 subtasks each (prompts: 700-1100 lines) ❌ (Broken - like feature 012!)
- After: 15-20 WPs of 5-7 subtasks each (prompts: 300-450 lines) ✓ (Manageable)

### Files Modified

- `src/specify_cli/missions/software-dev/command-templates/tasks.md` (rewritten: 567 lines)
- `src/specify_cli/templates/command-templates/tasks.md` (copied from software-dev)

### Commits

- (Pending) - fix: Rewrite WP sizing guidance to optimize for size, not count

### Migration

**Not needed** - templates are used directly during `/spec-kitty.tasks` execution. Next time an agent runs the command, they'll see the updated guidance.

The migration system handles OTHER command templates (review, implement) but NOT the tasks command template (it's read inline during execution).

### Testing

**Test by running /spec-kitty.tasks on a new feature**:
- Agent should see: "⚠️ CRITICAL: THIS IS THE MOST IMPORTANT PLANNING WORK"
- Agent should see: "QUALITY OVER SPEED: This is NOT the time to save tokens"
- Agent should follow: 3-7 subtasks per WP guideline
- Agent should validate: Prompt sizes and split if >700 lines
- Agent should report: Size distribution in final summary

### Real-World Example

**Feature 012 (this feature)**:
- 86 total subtasks across 10 WPs
- Average: 8.6 subtasks per WP ← **Too high!**
- Some WPs had 10+ subtasks → 1000+ line prompts

**With new guidance, feature 012 would have been**:
- 86 subtasks across 15-17 WPs
- Average: 5-6 subtasks per WP ✓
- All prompts: 300-500 lines ✓
- Easier implementation, better parallelization

**Lesson**: Current feature 012 proves the old guidance was broken. New guidance fixes it for future features.
