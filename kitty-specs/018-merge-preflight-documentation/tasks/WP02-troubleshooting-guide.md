---
work_package_id: "WP02"
subtasks:
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
title: "Troubleshooting Guide"
phase: "Phase 1 - User Documentation"
lane: "doing"
assignee: ""
agent: "codex"
shell_pid: "56071"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
  - timestamp: "2026-01-18T13:21:55Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Troubleshooting Guide

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-01-18

**Issue 1**: Error message reference is still not exact/complete. It must list the exact user-facing strings. Please add the missing lines and fix mismatches, for example:
- `Error: No merge state to resume` (currently missing the `Error:` prefix)
- `Error: Working directory has uncommitted changes.` (missing `Error:` prefix)
- `Merge failed. Resolve conflicts and try again.` (distinct from `Merge failed. You may need to resolve conflicts.`)
- `Merge failed. You may need to resolve conflicts.` (missing exact text)
- `Error: Already on <branch> branch.` (table hardcodes `main`)
Include other exact red/error strings from `src/specify_cli/cli/commands/merge.py` and `src/specify_cli/merge/preflight.py` that are not in the table.

**Issue 2**: “Missing Worktree” remediation text is inconsistent. The error text says to run `spec-kitty agent workflow implement WP##`, but the guide then adds extra `spec-kitty implement` commands. Please align the fix steps to the actual instruction and avoid redundant/conflicting commands.


## Objectives & Success Criteria

Create `docs/how-to/troubleshoot-merge.md` - a problem-solution guide for merge recovery and conflict resolution.

**Success Criteria:**
- A user with an interrupted merge can recover within 5 minutes using only this guide
- All error messages are documented with solutions
- --resume and --abort usage is clear with examples
- Conflict resolution workflow is documented for both status files and code
- Decision tree helps users quickly identify their situation

## Context & Constraints

**Source Files:**
- `src/specify_cli/cli/commands/merge.py` - Error messages, --resume/--abort handling
- `src/specify_cli/merge/state.py` - MergeState dataclass, JSON structure
- `src/specify_cli/merge/executor.py` - Merge workflow, error conditions
- `src/specify_cli/merge/status_resolver.py` - Auto-resolution behavior
- `src/specify_cli/merge/preflight.py` - Pre-flight error messages

**Style Reference:** Troubleshooting sections in existing docs

**Output Location:** `docs/how-to/troubleshoot-merge.md`

## Subtasks & Detailed Guidance

### Subtask T009 – Extract error messages from merge code
- **Purpose**: Document all user-facing errors
- **Steps**:
  1. Grep for `console.print.*Error` and `console.print.*red` in merge files
  2. Also check `raise typer.Exit` patterns
  3. Compile list: exact error text, when it occurs, cause
- **Files**:
  - `src/specify_cli/cli/commands/merge.py`
  - `src/specify_cli/merge/executor.py`
  - `src/specify_cli/merge/preflight.py`
- **Parallel?**: Yes
- **Command**: `grep -rn "Error\|red" src/specify_cli/merge/ src/specify_cli/cli/commands/merge.py`

### Subtask T010 – Document MergeState structure
- **Purpose**: Help users understand state file for debugging
- **Steps**:
  1. Read `src/specify_cli/merge/state.py`
  2. Document MergeState dataclass fields:
     - feature_slug, target_branch, wp_order
     - completed_wps, current_wp, has_pending_conflicts
     - strategy, started_at, updated_at
  3. Show example JSON from `.kittify/merge-state.json`
- **Files**: `src/specify_cli/merge/state.py`
- **Parallel?**: Yes

### Subtask T011 – Document status file auto-resolution
- **Purpose**: Explain automatic conflict handling
- **Steps**:
  1. Read `src/specify_cli/merge/status_resolver.py`
  2. Document what status files are (lane markers in WP files)
  3. Explain auto-resolution: takes "done" status when conflicts occur
  4. Document when auto-resolution fails
- **Files**: `src/specify_cli/merge/status_resolver.py`
- **Parallel?**: Yes

### Subtask T012 – Write troubleshoot-merge.md structure
- **Purpose**: Establish document skeleton with decision tree
- **Steps**:
  1. Create `docs/how-to/troubleshoot-merge.md`
  2. Start with "Quick Reference" decision tree:
     ```
     Merge failed?
     ├── Pre-flight failed → Section: Pre-flight Failures
     ├── Conflicts during merge → Section: Conflict Resolution
     ├── Interrupted (terminal closed) → Section: --resume
     └── Want to start over → Section: --abort
     ```
  3. Add standard sections: Command Reference, See Also
- **Files**: `docs/how-to/troubleshoot-merge.md`
- **Parallel?**: No (must complete before T013-T017)

### Subtask T013 – --resume usage section
- **Purpose**: Guide users through resuming interrupted merges
- **Steps**:
  1. Add "Resume an Interrupted Merge" section
  2. Explain when to use --resume
  3. Show example: merge stopped at WP03, resume continues from there
  4. Include command and expected output
  5. Explain what state.json shows during resume
- **Files**: `docs/how-to/troubleshoot-merge.md`
- **Parallel?**: Yes (after T012)

### Subtask T014 – --abort usage section
- **Purpose**: Guide users through aborting and starting fresh
- **Steps**:
  1. Add "Abort and Start Fresh" section
  2. Explain when to use --abort vs --resume
  3. Show command: `spec-kitty merge --abort`
  4. Explain what gets cleaned up (state file, any in-progress git merge)
  5. Show how to restart merge after abort
- **Files**: `docs/how-to/troubleshoot-merge.md`
- **Parallel?**: Yes (after T012)

### Subtask T015 – Conflict resolution section
- **Purpose**: Document manual conflict resolution workflow
- **Steps**:
  1. Add "Resolve Merge Conflicts" section
  2. Subsection: "Status File Conflicts (Automatic)"
     - Explain these are auto-resolved
     - Show what to do if auto-resolution fails
  3. Subsection: "Code Conflicts (Manual)"
     - Standard git conflict resolution workflow
     - How to continue merge after resolving
     - `git add <files>` then `spec-kitty merge --resume`
- **Files**: `docs/how-to/troubleshoot-merge.md`
- **Parallel?**: Yes (after T012)

### Subtask T016 – Pre-flight failure section
- **Purpose**: Document each pre-flight failure and fix
- **Steps**:
  1. Add "Pre-flight Validation Failures" section
  2. Document each failure type:
     - "Uncommitted changes in WP02" → commit or stash
     - "Missing worktree for WP03" → run spec-kitty implement WP03
     - "Branch not found" → check branch exists
  3. Explain that all issues are shown upfront (not one at a time)
- **Files**: `docs/how-to/troubleshoot-merge.md`
- **Parallel?**: Yes (after T012)

### Subtask T017 – Error message reference table
- **Purpose**: Quick lookup for any error
- **Steps**:
  1. Add "Error Message Reference" section
  2. Create table with columns: Error Message | Cause | Solution
  3. Include all errors from T009
  4. Keep solutions brief with links to detailed sections
- **Files**: `docs/how-to/troubleshoot-merge.md`
- **Parallel?**: Yes (after T012, needs T009 complete)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Missing error cases | Grep all error patterns in source |
| Outdated state format | Extract directly from state.py dataclass |
| Untested recovery flows | Manually test --resume and --abort |

## Definition of Done Checklist

- [ ] All subtasks completed
- [ ] `docs/how-to/troubleshoot-merge.md` created
- [ ] Decision tree in Quick Reference
- [ ] --resume documented with example
- [ ] --abort documented with example
- [ ] Conflict resolution (status + code) documented
- [ ] Pre-flight failures documented with fixes
- [ ] Error message reference table complete
- [ ] Cross-reference sections present

## Review Guidance

1. Verify all error messages from source are in reference table
2. Confirm MergeState fields match state.py
3. Test --resume and --abort commands work as documented
4. Check decision tree covers all failure scenarios

## Activity Log

- 2026-01-18T13:21:55Z – system – lane=planned – Prompt created.
- 2026-01-18T13:27:52Z – codex – shell_pid=56071 – lane=doing – Started review via workflow command
- 2026-01-18T13:28:44Z – codex – shell_pid=56071 – lane=planned – Moved to planned
- 2026-01-18T13:35:16Z – codex – shell_pid=56071 – lane=doing – Started review via workflow command
- 2026-01-18T13:37:09Z – codex – shell_pid=56071 – lane=planned – Moved to planned
- 2026-01-18T13:43:51Z – claude – shell_pid=82572 – lane=doing – Started implementation via workflow command
- 2026-01-18T13:45:18Z – claude – shell_pid=82572 – lane=for_review – Addressed both review issues: exact error messages added, pre-flight remediation text fixed
- 2026-01-18T13:45:29Z – codex – shell_pid=56071 – lane=doing – Started review via workflow command
- 2026-01-18T13:46:50Z – codex – shell_pid=56071 – lane=planned – Moved to planned
- 2026-01-18T13:47:30Z – codex – shell_pid=56071 – lane=doing – Started implementation via workflow command
