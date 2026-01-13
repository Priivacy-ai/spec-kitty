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

### The Problem

Each worktree branch contained a copy of `kitty-specs/###-feature/tasks/*.md`. Status updates were local - other worktrees never saw them.

### The Solution

**Symlink + Auto-Commit Pattern**:

1. **Symlink kitty-specs/ to main** (implement.py:583-633)
2. **Exclude from feature branches** (.gitignore + git rm --cached)
3. **Auto-commit changes to main** (tasks.py, workflow.py)
4. **Helper script** for existing worktrees (fix-worktree-symlinks.sh)

### Result

```
Main:     kitty-specs/ (directory) → Single source of truth
WP01-04:  kitty-specs/ (SYMLINK)   → Instant sync to all

Agent updates WP → Symlink write → Auto-commit → All see it (0ms latency)
```

### Jujutsu Alignment

| Jujutsu | Our Solution |
|---------|--------------|
| Commit graph (centralized status) | Main branch (centralized status) |
| Working copy query | Symlink to main |
| Auto-tracking | Auto-commit |
| Local-only | Local-only |

**Migration path**: Swap symlinks for jj working copy API. Same mental model.

### Files: implement.py (+30), tasks.py (+70), workflow.py (+40), fix-worktree-symlinks.sh (+70)
### Commits: 38292a7, 3c69d5b, 35cbba7

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

**Remove** (~100 lines):
- Symlink creation
- Auto-commit code
- .gitignore exclusion

**Replace with** (~50 lines):
```python
jj describe -m "chore: ..."  # Like our auto-commit
# jj handles working copy sync automatically
```

**Keep** (~400 lines):
- Agent tracking
- PID tracking
- Validation
- Feedback automation
- Workflow output

**Effort**: 2-3 hours, mental model unchanged

---

## Lessons Learned

1. **Dogfood early**: Issues found during real usage (feature 012)
2. **Long output buries instructions**: Always repeat at END
3. **Manual editing fails**: Automate everything
4. **Track ownership**: Required --agent prevents confusion
5. **Template propagation matters**: Update all 12 agents, not just 3
6. **Symlinks work for status**: Jujutsu-aligned, zero latency
7. **Document out-of-scope fixes**: Future developers need this context

---

## Files Modified (Summary)

| File | Purpose | Lines |
|------|---------|-------|
| implement.py | Symlink + exclude | +30 |
| tasks.py | Auto-commit + feedback + slug | +150 |
| workflow.py | PID + auto-commit + visual | +80 |
| m_0_11_2_improved_workflow_templates.py | Migration | +185 |
| review.md, implement.md | Templates | Rewritten |
| fix-worktree-symlinks.sh | Helper | +70 |

**Total**: ~540 lines of infrastructure

---

## Commits on Branch 012-documentation-mission-WP04

1. `28d1422` - Workflow command state corruption fixes
2. `38292a7` - Symlink kitty-specs/ solution  
3. `3c69d5b` - Complete state sync with auto-commit
4. `35cbba7` - PID tracking, feature slug fix, finalize

**These merge to main when WP04 completes and gets accepted.**
