---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
  - "T008"
title: "Merge Guide"
phase: "Phase 1 - User Documentation"
lane: "doing"
assignee: ""
agent: "codex"
shell_pid: "53316"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-18T13:21:55Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Merge Guide

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create `docs/how-to/merge-feature.md` - a comprehensive guide for users completing workspace-per-WP features.

**Success Criteria:**
- A new user can follow the guide to successfully merge a multi-WP feature
- All CLI flags are documented with examples
- Pre-flight validation is explained with interpretation guidance
- Dry-run output is shown with real examples
- Guide follows existing `docs/how-to/accept-and-merge.md` style

## Context & Constraints

**Source Files:**
- `src/specify_cli/cli/commands/merge.py` - CLI interface, flags, help text
- `src/specify_cli/merge/preflight.py` - Validation checks
- `src/specify_cli/merge/executor.py` - Merge workflow steps
- `src/specify_cli/merge/forecast.py` - Conflict forecasting

**Style Reference:** `docs/how-to/accept-and-merge.md`

**Output Location:** `docs/how-to/merge-feature.md`

## Subtasks & Detailed Guidance

### Subtask T001 – Extract CLI flags from merge.py
- **Purpose**: Gather all command-line options for documentation
- **Steps**:
  1. Read `src/specify_cli/cli/commands/merge.py`
  2. Find the `merge()` function with typer.Option decorators
  3. Extract: flag name, help text, default value
- **Files**: `src/specify_cli/cli/commands/merge.py`
- **Parallel?**: Yes
- **Expected flags**: --strategy, --delete-branch/--keep-branch, --remove-worktree/--keep-worktree, --push, --target, --dry-run, --feature, --resume, --abort

### Subtask T002 – Extract pre-flight validation checks
- **Purpose**: Document what pre-flight validates
- **Steps**:
  1. Read `src/specify_cli/merge/preflight.py`
  2. Find `run_preflight()` function
  3. Document each check: dirty worktrees, missing worktrees, branch existence
- **Files**: `src/specify_cli/merge/preflight.py`
- **Parallel?**: Yes

### Subtask T003 – Capture dry-run output example
- **Purpose**: Show users what dry-run looks like
- **Steps**:
  1. Find a feature with multiple WPs (or create test scenario)
  2. Run `spec-kitty merge --dry-run` from a WP worktree
  3. Capture the output showing planned merge sequence
- **Files**: Terminal output
- **Parallel?**: Yes
- **Note**: If no suitable feature exists, show the format based on executor.py

### Subtask T004 – Write merge-feature.md structure
- **Purpose**: Establish document skeleton
- **Steps**:
  1. Create `docs/how-to/merge-feature.md`
  2. Follow `accept-and-merge.md` structure:
     - Title, intro paragraph
     - Prerequisites section
     - Main workflow sections
     - Troubleshooting link
     - Command Reference, See Also, Background, Getting Started
- **Files**: `docs/how-to/merge-feature.md`
- **Parallel?**: No (must complete before T005-T008)

### Subtask T005 – Merge strategies section
- **Purpose**: Explain merge/squash/rebase options
- **Steps**:
  1. Add "Merge Strategies" section
  2. Document each strategy with command example:
     - Default merge: `spec-kitty merge`
     - Squash: `spec-kitty merge --strategy squash`
     - Rebase: `spec-kitty merge --strategy rebase`
  3. Explain when to use each
- **Files**: `docs/how-to/merge-feature.md`
- **Parallel?**: Yes (after T004)

### Subtask T006 – Pre-flight validation section
- **Purpose**: Help users understand automatic checks
- **Steps**:
  1. Add "Pre-flight Validation" section
  2. List what gets checked (from T002)
  3. Show example output when validation passes
  4. Show example output when validation fails
  5. Explain how to fix each failure type
- **Files**: `docs/how-to/merge-feature.md`
- **Parallel?**: Yes (after T004)

### Subtask T007 – Dry-run and conflict forecasting section
- **Purpose**: Show users how to preview merge
- **Steps**:
  1. Add "Preview with Dry-Run" section
  2. Include command: `spec-kitty merge --dry-run`
  3. Include captured output from T003
  4. Explain conflict forecasting feature
  5. Show what predicted conflicts look like
- **Files**: `docs/how-to/merge-feature.md`
- **Parallel?**: Yes (after T004)

### Subtask T008 – Cleanup options section
- **Purpose**: Document post-merge cleanup behavior
- **Steps**:
  1. Add "Cleanup Options" section
  2. Document default behavior (removes worktree, deletes branch)
  3. Show how to keep: `--keep-worktree`, `--keep-branch`
  4. Explain when you'd want to keep them
- **Files**: `docs/how-to/merge-feature.md`
- **Parallel?**: Yes (after T004)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Stale examples | Use actual command output, not fabricated |
| Missing flags | Cross-check against `spec-kitty merge --help` |
| Style inconsistency | Compare each section against accept-and-merge.md |

## Definition of Done Checklist

- [ ] All subtasks completed
- [ ] `docs/how-to/merge-feature.md` created
- [ ] All CLI flags documented (--strategy, --dry-run, --push, --resume, --abort, etc.)
- [ ] Pre-flight validation explained
- [ ] Dry-run example included
- [ ] Follows accept-and-merge.md style
- [ ] Both agent and terminal commands shown
- [ ] Cross-reference sections present (Command Reference, See Also, etc.)

## Review Guidance

1. Verify all flags from `merge.py` are documented
2. Confirm dry-run output matches actual command output
3. Check style matches `accept-and-merge.md`
4. Test any copy-pasteable commands

## Activity Log

- 2026-01-18T13:21:55Z – system – lane=planned – Prompt created.
- 2026-01-18T13:27:09Z – codex – shell_pid=53316 – lane=doing – Started review via workflow command
