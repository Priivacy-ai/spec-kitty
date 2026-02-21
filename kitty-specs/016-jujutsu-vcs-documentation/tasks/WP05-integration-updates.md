---
work_package_id: "WP05"
subtasks:
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
  - "T031"
title: "Integration Updates"
phase: "Phase 2 - Integration"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "72761"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
dependencies: ["WP02", "WP03", "WP04"]
history:
  - timestamp: "2026-01-17T18:14:07Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – Integration Updates

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

**Issue 1** (Terminology consistency): The requirement is to use “jujutsu (jj)” on first mention. `docs/tutorials/your-first-feature.md` first mentions “jj” without expanding. Update the first mention to “jujutsu (jj)”.

**Issue 2** (Terminology consistency): `docs/how-to/implement-work-package.md` first mentions “jj workspace” without expanding to “jujutsu (jj)”. Update the first mention accordingly.

## Objectives & Success Criteria

- Update existing documentation to mention jj alongside git
- Ensure existing users discover jj support without needing new pages
- Keep updates minimal but discoverable
- Success: Existing users reading familiar docs learn jj is now supported

## Context & Constraints

- **Spec**: `kitty-specs/016-jujutsu-vcs-documentation/spec.md` - User Story 4 (P2), FR-001 through FR-005
- **Plan**: `kitty-specs/016-jujutsu-vcs-documentation/plan.md` - Files to Update section

### Integration Guidelines

- Use callout boxes for jj-specific information
- Keep updates concise - link to dedicated content for details
- Maintain existing flow and structure
- Use consistent terminology: "jujutsu (jj)" on first mention, "jj" thereafter

### Files to Update

| File | Changes |
|------|---------|
| `tutorials/getting-started.md` | jj installation recommendation |
| `tutorials/your-first-feature.md` | VCS abstraction mention |
| `tutorials/multi-agent-workflow.md` | jj auto-rebase benefits |
| `how-to/install-spec-kitty.md` | jj installation section |
| `how-to/implement-work-package.md` | jj workspace note |
| `how-to/parallel-development.md` | jj benefits for parallel work |
| `how-to/handle-dependencies.md` | sync command mention |
| `explanation/workspace-per-wp.md` | jj workspace information |
| `explanation/git-worktrees.md` | jj workspace comparison |

## Subtasks & Detailed Guidance

### Subtask T023 – Update getting-started.md

- **Purpose**: Surface jj support during onboarding (FR-001)
- **Steps**:
  1. Read `docs/tutorials/getting-started.md`
  2. Find installation/setup section
  3. Add callout recommending jj:

     ```markdown
     > **Recommended**: Install [jujutsu (jj)](https://jj-vcs.github.io/jj/)
     > for automatic rebasing and non-blocking conflicts. spec-kitty will
     > use jj when available. See [Jujutsu Workflow Tutorial](jujutsu-workflow.md).
     ```

  4. Mention that `spec-kitty init` detects and prefers jj
- **Files**: `docs/tutorials/getting-started.md`
- **Parallel?**: Yes

### Subtask T024 – Update your-first-feature.md

- **Purpose**: Mention VCS abstraction
- **Steps**:
  1. Read `docs/tutorials/your-first-feature.md`
  2. Find workspace creation section
  3. Add note that workspace may be jj or git depending on project setup
  4. Link to jujutsu-workflow.md for jj-specific details
- **Files**: `docs/tutorials/your-first-feature.md`
- **Parallel?**: Yes

### Subtask T025 – Update multi-agent-workflow.md

- **Purpose**: Highlight jj benefits for parallel work
- **Steps**:
  1. Read `docs/tutorials/multi-agent-workflow.md`
  2. Find section on parallel development
  3. Add callout:

     ```markdown
     > **With jj**: Multiple agents can work on dependent work packages
     > simultaneously. When one WP changes, others auto-rebase. No manual
     > coordination needed. See [Why Jujutsu for Multi-Agent](../explanation/jujutsu-for-multi-agent.md).
     ```

- **Files**: `docs/tutorials/multi-agent-workflow.md`
- **Parallel?**: Yes

### Subtask T026 – Update install-spec-kitty.md

- **Purpose**: Add jj installation instructions (FR-002)
- **Steps**:
  1. Read `docs/how-to/install-spec-kitty.md`
  2. Add new section: "Installing Jujutsu (Recommended)"
  3. Include installation commands:

     ```bash
     # macOS
     brew install jj

     # Cargo (any platform)
     cargo install jj-cli

     # Verify
     jj --version  # Should show 0.20+
     ```

  4. Explain benefits of jj over git-only setup
  5. Note: jj is recommended but git still works
- **Files**: `docs/how-to/install-spec-kitty.md`
- **Parallel?**: Yes

### Subtask T027 – Update implement-work-package.md

- **Purpose**: Explain jj workspace vs git worktree (FR-003)
- **Steps**:
  1. Read `docs/how-to/implement-work-package.md`
  2. Find workspace creation section
  3. Add note explaining:
     - git projects use worktrees
     - jj projects use native workspaces
     - Both appear in `.worktrees/` directory
     - Behavior is abstracted - commands work the same
- **Files**: `docs/how-to/implement-work-package.md`
- **Parallel?**: Yes

### Subtask T028 – Update parallel-development.md

- **Purpose**: Emphasize jj benefits for parallel work (FR-004)
- **Steps**:
  1. Read `docs/how-to/parallel-development.md`
  2. Add section or callout on jj advantages:
     - Auto-rebase eliminates manual coordination
     - Non-blocking conflicts let work continue
     - Multiple agents can work simultaneously without blocking
  3. Link to explanation article and sync how-to
- **Files**: `docs/how-to/parallel-development.md`
- **Parallel?**: Yes

### Subtask T029 – Update handle-dependencies.md

- **Purpose**: Mention sync command for dependent WPs
- **Steps**:
  1. Read `docs/how-to/handle-dependencies.md`
  2. Find section on keeping dependencies updated
  3. Add mention of `spec-kitty sync` command
  4. Explain difference: jj syncs seamlessly, git may require conflict resolution
  5. Link to sync-workspaces.md for details
- **Files**: `docs/how-to/handle-dependencies.md`
- **Parallel?**: Yes

### Subtask T030 – Update workspace-per-wp.md

- **Purpose**: Add jj workspace information
- **Steps**:
  1. Read `docs/explanation/workspace-per-wp.md`
  2. Find workspace implementation section
  3. Add paragraph explaining jj workspace mechanics
  4. Note that jj workspaces share the same repository state
  5. Explain auto-rebase benefit in context of WP dependencies
- **Files**: `docs/explanation/workspace-per-wp.md`
- **Parallel?**: Yes

### Subtask T031 – Update git-worktrees.md

- **Purpose**: Compare with jj workspaces (FR-005)
- **Steps**:
  1. Read `docs/explanation/git-worktrees.md`
  2. Add section: "Comparison with jj Workspaces"
  3. Create comparison table:

     | Aspect | git worktrees | jj workspaces |
     |--------|---------------|---------------|
     | Isolation | Separate working trees | Same repo, different commits |
     | Rebase | Manual | Automatic |
     | Conflicts | Blocking | Non-blocking |

  4. Explain when each is appropriate
  5. Link to jujutsu-for-multi-agent.md
- **Files**: `docs/explanation/git-worktrees.md`
- **Parallel?**: Yes

## Risks & Mitigations

- **Overwhelming existing content**: Keep additions brief, use callouts
- **Inconsistent terminology**: Use "jujutsu (jj)" on first mention consistently
- **Broken links**: Wait for WP02-04 to complete before adding cross-references

## Definition of Done Checklist

- [ ] T023: getting-started.md updated with jj recommendation
- [ ] T024: your-first-feature.md mentions VCS abstraction
- [ ] T025: multi-agent-workflow.md highlights jj benefits
- [ ] T026: install-spec-kitty.md has jj installation section
- [ ] T027: implement-work-package.md explains workspace types
- [ ] T028: parallel-development.md emphasizes jj advantages
- [ ] T029: handle-dependencies.md mentions sync command
- [ ] T030: workspace-per-wp.md includes jj workspace info
- [ ] T031: git-worktrees.md compares with jj workspaces
- [ ] All cross-references point to correct files
- [ ] Existing content flow preserved

## Review Guidance

- Verify updates are discoverable but not overwhelming
- Check that jj is consistently presented as "recommended, not required"
- Ensure cross-references to new content work
- Confirm existing users can still follow original workflows

## Activity Log

- 2026-01-17T18:14:07Z – system – lane=planned – Prompt created.
- 2026-01-17T18:59:10Z – unknown – lane=for_review – Moved to for_review
- 2026-01-17T19:17:59Z – codex – shell_pid=40527 – lane=doing – Started review via workflow command
- 2026-01-17T19:19:16Z – codex – shell_pid=40527 – lane=planned – Moved to planned
- 2026-01-17T19:24:18Z – claude – shell_pid=71003 – lane=doing – Started implementation via workflow command
- 2026-01-17T19:26:12Z – claude – shell_pid=71003 – lane=for_review – Ready for review: Fixed terminology - now uses 'jujutsu (jj)' on first mention in your-first-feature.md and implement-work-package.md
- 2026-01-17T19:31:26Z – claude – shell_pid=72761 – lane=doing – Started review via workflow command
- 2026-01-17T19:32:35Z – claude – shell_pid=72761 – lane=done – Review passed: All 9 subtasks verified, review feedback addressed (terminology now uses 'jujutsu (jj)' on first mention)
