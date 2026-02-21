---
work_package_id: "WP03"
subtasks:
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
title: "Jujutsu Workflow Tutorial"
phase: "Phase 1 - MVP Content"
lane: "done"
assignee: ""
agent: "codex"
shell_pid: "35960"
review_status: "acknowledged"
reviewed_by: "Robert Douglass"
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-17T18:14:07Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Jujutsu Workflow Tutorial

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

**Issue 1**: Missing required prerequisite for terminal access. The spec explicitly calls for listing terminal access in the Prerequisites section (T013). Add a short item stating a terminal is required (e.g., macOS Terminal/PowerShell).

**Issue 2**: Step numbering does not match the work package guidance. The prompt requires **Step 5: Complete and Merge** (T018), but the document labels this as Step 6 and uses Step 5 for operation history. Please renumber or reorder so “Complete and Merge” is Step 5.

**Issue 3**: T015 asks to explain that jj uses native workspaces (not git worktrees). The current text mentions a “jj workspace” but never explicitly contrasts workspaces vs worktrees. Add a sentence in Step 2 clarifying jj uses native workspaces and Spec Kitty still places them under `.worktrees/` for consistency.

**Issue 4**: Conflict resolution guidance uses `jj squash`, which is not a clear or correct way to resolve conflicts. Please replace with an accurate jj conflict-resolution step (e.g., edit conflicts then `jj resolve` or note that editing the files resolves conflicts and you can continue/commit), consistent with jj docs.

## Objectives & Success Criteria

- Create comprehensive tutorial at `docs/tutorials/jujutsu-workflow.md`
- Guide users through complete jj workflow from project init to feature merge
- Follow Divio tutorial style: learning-oriented, step-by-step
- Success: A user with jj installed can follow the tutorial end-to-end and complete a feature

## Context & Constraints

- **Spec**: `kitty-specs/016-jujutsu-vcs-documentation/spec.md` - User Story 2 (P1)
- **Plan**: `kitty-specs/016-jujutsu-vcs-documentation/plan.md` - New Files to Create section
- **Research**: `kitty-specs/016-jujutsu-vcs-documentation/research.md` - CLI commands, VCS capabilities

### Divio Tutorial Guidelines

Tutorials are:

- **Learning-oriented**: Teaching beginners by doing
- **Step-by-step**: Clear sequence from start to finish
- **Concrete**: Use realistic examples, not abstract concepts
- **Achievable**: User accomplishes something meaningful
- **Repeatable**: Works every time if followed exactly

### Key jj Concepts to Cover

From research.md and feature 015:

- Auto-rebase: Dependent workspaces update automatically
- Non-blocking conflicts: Conflicts stored in files, work continues
- Operation log: Full history with undo capability
- Change IDs: Stable identity across rebases
- Colocated mode: Both .jj/ and .git/ present

## Subtasks & Detailed Guidance

### Subtask T012 – Create jujutsu-workflow.md with Divio structure

- **Purpose**: Establish file structure and frontmatter
- **Steps**:
  1. Create `docs/tutorials/jujutsu-workflow.md`
  2. Add title: "Jujutsu (jj) Workflow Tutorial"
  3. Add introduction explaining what user will learn and accomplish
  4. Include estimated time (30-45 minutes)
- **Files**: `docs/tutorials/jujutsu-workflow.md`
- **Structure**:

  ```markdown
  # Jujutsu (jj) Workflow Tutorial

  Learn how to use spec-kitty with jujutsu (jj) for better multi-agent
  parallel development.

  **Time**: 30-45 minutes
  **Prerequisites**: jj installed, spec-kitty 0.12.0+

  ## What You'll Learn
  - Setting up a jj-based project
  - Creating and managing workspaces
  - Syncing workspaces with auto-rebase
  - Handling non-blocking conflicts
  - Using operation history for undo
  ```

### Subtask T013 – Write prerequisites section

- **Purpose**: Ensure users have everything needed before starting
- **Steps**:
  1. Add Prerequisites section
  2. List: jj installation (link to jj docs), spec-kitty version, terminal access
  3. Include verification commands:
     - `jj --version` (expect 0.20+)
     - `spec-kitty --version` (expect 0.12.0+)
  4. Note: Link to install-spec-kitty.md for installation help
- **Files**: `docs/tutorials/jujutsu-workflow.md`

### Subtask T014 – Write init section showing jj detection

- **Purpose**: Show how to start a project with jj
- **Steps**:
  1. Add "Step 1: Initialize Your Project" section
  2. Show `spec-kitty init my-project --ai claude` command
  3. Explain the jj detection message users will see
  4. Show resulting directory structure with `.jj/` present
  5. Explain colocated mode if both jj and git available
- **Files**: `docs/tutorials/jujutsu-workflow.md`
- **Include output example**:

  ```
  $ spec-kitty init my-project --ai claude
  ✓ Detected jj (0.23.0) - using jujutsu for version control
  ✓ Created .jj/ repository in colocated mode
  ```

### Subtask T015 – Write workspace creation section

- **Purpose**: Show how to create workspaces for work packages
- **Steps**:
  1. Add "Step 2: Create a Feature Workspace" section
  2. Walk through `/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.tasks`
  3. Show `spec-kitty implement WP01` creating a jj workspace
  4. Explain that jj uses native workspaces (not worktrees)
  5. Show the workspace at `.worktrees/feature-WP01/`
- **Files**: `docs/tutorials/jujutsu-workflow.md`

### Subtask T016 – Write sync section demonstrating auto-rebase

- **Purpose**: Show the key jj benefit - automatic rebase
- **Steps**:
  1. Add "Step 3: Sync Workspaces (Auto-Rebase)" section
  2. Create scenario: WP01 changes while working on dependent WP02
  3. Show `spec-kitty sync` in WP02 workspace
  4. Explain that jj automatically rebases WP02 on top of new WP01
  5. Compare with git (would require manual rebase)
- **Files**: `docs/tutorials/jujutsu-workflow.md`
- **Key point**: With jj, `spec-kitty sync` always succeeds

### Subtask T017 – Write conflict handling section

- **Purpose**: Demonstrate non-blocking conflicts
- **Steps**:
  1. Add "Step 4: Handle Non-Blocking Conflicts" section
  2. Create scenario: sync results in conflicts
  3. Show that sync SUCCEEDS (unlike git which would fail)
  4. Show conflict markers in files
  5. Explain workflow: continue working → resolve conflicts later → commit resolution
  6. Show `spec-kitty ops log` to see conflict state
- **Files**: `docs/tutorials/jujutsu-workflow.md`
- **Key point**: Conflicts don't block agents from continuing work

### Subtask T018 – Write merge completion section

- **Purpose**: Show how to complete and merge work
- **Steps**:
  1. Add "Step 5: Complete and Merge" section
  2. Show `/spec-kitty.review` workflow
  3. Explain how jj's stable Change IDs help track work across rebases
  4. Show `/spec-kitty.accept` and final merge
  5. Celebrate completion!
- **Files**: `docs/tutorials/jujutsu-workflow.md`

### Subtask T019 – Add cross-references

- **Purpose**: Connect to related content for deeper learning
- **Steps**:
  1. Add "Next Steps" section at end
  2. Link to:
     - `how-to/sync-workspaces.md` - detailed sync guide
     - `how-to/handle-conflicts-jj.md` - conflict resolution details
     - `how-to/use-operation-history.md` - undo operations
     - `explanation/jujutsu-for-multi-agent.md` - why jj is preferred
     - `explanation/auto-rebase-and-conflicts.md` - conceptual deep dive
  3. Add "See Also" links in each section where relevant
- **Files**: `docs/tutorials/jujutsu-workflow.md`

## Risks & Mitigations

- **Tutorial too long**: Keep focused on happy path, link to how-tos for edge cases
- **Outdated commands**: Use research.md as source of truth for CLI syntax
- **User gets stuck**: Include troubleshooting tips and links to how-tos

## Definition of Done Checklist

- [ ] T012: File created with Divio tutorial structure
- [ ] T013: Prerequisites section with verification commands
- [ ] T014: Init section showing jj detection
- [ ] T015: Workspace creation with spec-kitty implement
- [ ] T016: Sync section demonstrating auto-rebase benefit
- [ ] T017: Non-blocking conflict handling explained
- [ ] T018: Merge completion workflow documented
- [ ] T019: Cross-references to all related content
- [ ] Tutorial is end-to-end completable
- [ ] Both "jj" and "jujutsu" terms used for searchability

## Review Guidance

- Follow the tutorial as a new user - does it work?
- Check that each step has clear expected output
- Verify cross-references point to correct files
- Ensure jj benefits are clearly articulated
- Confirm backend differences are highlighted

## Activity Log

- 2026-01-17T18:14:07Z – system – lane=planned – Prompt created.
- 2026-01-17T18:47:32Z – codex – shell_pid=35960 – lane=doing – Started implementation via workflow command
- 2026-01-17T18:59:09Z – codex – shell_pid=35960 – lane=for_review – Moved to for_review
- 2026-01-17T19:03:59Z – codex – shell_pid=35960 – lane=doing – Started review via workflow command
- 2026-01-17T19:05:19Z – codex – shell_pid=35960 – lane=planned – Moved to planned
- 2026-01-17T19:08:58Z – codex – shell_pid=35960 – lane=doing – Started implementation via workflow command
- 2026-01-17T19:10:10Z – codex – shell_pid=35960 – lane=for_review – Ready for review: addressed feedback on prerequisites, step ordering, workspace note, conflict resolution
- 2026-01-17T19:11:03Z – codex – shell_pid=35960 – lane=doing – Started review via workflow command
- 2026-01-17T19:11:08Z – codex – shell_pid=35960 – lane=done – Review passed: feedback addressed and tutorial meets spec
