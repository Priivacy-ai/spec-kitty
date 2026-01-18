---
work_package_id: "WP04"
subtasks:
  - "T020"
  - "T021"
  - "T022"
title: "New How-To Guides"
phase: "Phase 1 - MVP Content"
lane: "done"
assignee: ""
agent: "codex"
shell_pid: "40527"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
dependencies: ["WP01", "WP02"]
history:
  - timestamp: "2026-01-17T18:14:07Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – New How-To Guides

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-01-17

**Issue 1** (Sync troubleshooting still implies fetch): The sync guide still uses “Failed to fetch: network error,” but `spec-kitty sync` doesn’t fetch; it rebases the base branch (git) or runs `jj workspace update-stale` + auto-rebase. Update the troubleshooting heading/text to avoid fetch semantics (e.g., “Failed to sync/update base”). (`docs/how-to/sync-workspaces.md`)


## Objectives & Success Criteria

- Create three task-oriented how-to guides for jj-specific operations
- Each guide should solve a specific problem in 5-10 minutes
- Follow Divio how-to style: task-oriented, practical, problem-solving
- Success: User can accomplish sync, conflict handling, and operation history tasks

## Context & Constraints

- **Spec**: `kitty-specs/016-jujutsu-vcs-documentation/spec.md` - FR-007, FR-008, FR-009
- **Plan**: `kitty-specs/016-jujutsu-vcs-documentation/plan.md` - New Files to Create section
- **Research**: `kitty-specs/016-jujutsu-vcs-documentation/research.md` - CLI commands, backend differences

### Divio How-To Guidelines

How-to guides are:
- **Task-oriented**: Focus on achieving a specific goal
- **Practical**: Real-world scenarios, not theoretical
- **Problem-solving**: Address a specific need
- **Flexible**: Allow for variations in approach
- **Concise**: Get to the solution quickly

### Command Reference (from research.md)

Use these verified commands:

```bash
# Sync
spec-kitty sync [--repair] [--verbose]

# Operation history
spec-kitty ops log [--limit N] [--verbose]
spec-kitty ops undo [OPERATION_ID]     # jj only
spec-kitty ops restore OPERATION_ID   # jj only
```

## Subtasks & Detailed Guidance

### Subtask T020 – Create sync-workspaces.md

- **Purpose**: Guide users through workspace synchronization
- **Steps**:
  1. Create `docs/how-to/sync-workspaces.md`
  2. Structure:
     - **Problem**: Your workspace is out of date with changes from a dependent WP
     - **Prerequisites**: Active workspace, jj or git backend
     - **Steps**: Using `spec-kitty sync`
     - **Verification**: How to confirm sync succeeded
     - **Troubleshooting**: Common issues and fixes
  3. Include backend comparison callout:
     - jj: Sync always succeeds, conflicts stored
     - git: Sync may fail on conflicts
  4. Document `--repair` flag for recovery scenarios
  5. Cross-reference to tutorial and explanation
- **Files**: `docs/how-to/sync-workspaces.md`
- **Parallel?**: Yes - can be written alongside T021, T022
- **Example structure**:
  ```markdown
  # How to Sync Workspaces

  Keep your workspace up to date with upstream changes.

  ## The Problem

  You're working on WP02, and WP01 (which WP02 depends on) has changed.
  You need to update your workspace with the latest changes.

  ## Prerequisites

  - Active workspace (created via `spec-kitty implement`)
  - spec-kitty 0.12.0+

  ## Steps

  1. Navigate to your workspace...
  ```

### Subtask T021 – Create handle-conflicts-jj.md

- **Purpose**: Guide users through non-blocking conflict resolution
- **Steps**:
  1. Create `docs/how-to/handle-conflicts-jj.md`
  2. Structure:
     - **Problem**: Sync resulted in conflicts (jj shows conflict markers)
     - **Key insight**: Conflicts are NON-BLOCKING in jj
     - **Steps**:
       1. Continue working despite conflicts
       2. View conflicts with `jj status` or conflict list
       3. Resolve conflicts when ready
       4. Mark resolved with `jj resolve` or by editing
     - **Verification**: Confirm no conflicts remain
  3. Explain why non-blocking matters for multi-agent workflows
  4. Compare with git (blocking conflicts)
  5. Cross-reference to explanation article
- **Files**: `docs/how-to/handle-conflicts-jj.md`
- **Parallel?**: Yes
- **Key message**: "With jj, you can keep working while conflicts exist"

### Subtask T022 – Create use-operation-history.md

- **Purpose**: Guide users through operation log, undo, and restore
- **Steps**:
  1. Create `docs/how-to/use-operation-history.md`
  2. Structure:
     - **Problem**: Need to undo a mistake or see what operations occurred
     - **Prerequisites**: jj workspace (undo/restore are jj-only)
     - **Steps**:
       1. View history: `spec-kitty ops log`
       2. Undo last operation: `spec-kitty ops undo`
       3. Restore to specific point: `spec-kitty ops restore <id>`
     - **Verification**: Confirm repository state changed
  3. Explain operation IDs and how to read them
  4. Note differences:
     - `undo`: Reverts most recent operation
     - `restore`: Jumps to any point in history
  5. Include warning: "This only works with jj workspaces"
  6. For git users: Link to reflog documentation as alternative
- **Files**: `docs/how-to/use-operation-history.md`
- **Parallel?**: Yes

## Risks & Mitigations

- **Guides overlap**: Keep clear scope boundaries - sync vs conflicts vs history
- **jj-only confusion**: Prominently mark undo/restore as jj-only features
- **Outdated commands**: Use research.md as authoritative source

## Definition of Done Checklist

- [ ] T020: sync-workspaces.md created with complete guide
- [ ] T021: handle-conflicts-jj.md created with jj-specific workflow
- [ ] T022: use-operation-history.md created with all three commands
- [ ] All guides follow Divio how-to structure
- [ ] Backend differences clearly noted where relevant
- [ ] jj-only features prominently marked
- [ ] Cross-references to related content included
- [ ] Each guide completable in 5-10 minutes

## Review Guidance

- Try each how-to guide - does it solve the stated problem?
- Verify command syntax matches --help output
- Check that jj-only features are clearly marked
- Confirm troubleshooting sections address common issues
- Ensure cross-references are accurate

## Activity Log

- 2026-01-17T18:14:07Z – system – lane=planned – Prompt created.
- 2026-01-17T18:59:09Z – unknown – lane=for_review – Moved to for_review
- 2026-01-17T19:04:22Z – codex – shell_pid=40527 – lane=doing – Started review via workflow command
- 2026-01-17T19:05:41Z – codex – shell_pid=40527 – lane=planned – Moved to planned
- 2026-01-17T19:08:46Z – codex – shell_pid=40527 – lane=doing – Started implementation via workflow command
- 2026-01-17T19:09:55Z – codex – shell_pid=40527 – lane=for_review – Ready for review
- 2026-01-17T19:15:21Z – codex – shell_pid=40527 – lane=doing – Started review via workflow command
- 2026-01-17T19:16:12Z – codex – shell_pid=40527 – lane=planned – Moved to planned
- 2026-01-17T19:17:24Z – claude – shell_pid=69098 – lane=doing – Started implementation via workflow command
- 2026-01-17T19:18:02Z – claude – shell_pid=69098 – lane=for_review – Fixed fetch semantics in sync troubleshooting
- 2026-01-17T19:25:09Z – codex – shell_pid=40527 – lane=doing – Started review via workflow command
- 2026-01-17T19:25:30Z – codex – shell_pid=40527 – lane=done – Review passed
