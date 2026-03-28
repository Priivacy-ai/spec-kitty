---
work_package_id: "WPxx"
title: "Replace with work package title"
dependencies: []
planning_base_branch: "{{planning_base_branch}}"  # Planning branch active when this WP prompt was generated
merge_target_branch: "{{merge_target_branch}}"    # Final landing branch for completed changes
branch_strategy: "{{branch_strategy}}"            # Repeat this branch contract before coding; never guess
subtasks:
  - "Txxx"
phase: "Phase N - Replace with phase name"
assignee: ""      # Optional friendly name when in doing/for_review
agent: ""         # CLI agent identifier (claude, codex, etc.)
shell_pid: ""     # PID captured when the task moved to the current lane
history:
  - timestamp: "{{TIMESTAMP}}"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---
*Path: [templates/task-prompt-template.md](templates/task-prompt-template.md)*


# Work Package Prompt: {{work_package_id}} – {{title}}

## Branch Strategy

- **Planning/base branch at prompt creation**: `{{planning_base_branch}}`
- **Final merge target for completed work**: `{{merge_target_branch}}`
- **Actual worktree base may differ later**: `/spec-kitty.implement` populates frontmatter `base_branch` when the worktree is created. For stacked WPs it may point at another WP branch, but the final merge target remains `{{merge_target_branch}}` unless the human explicitly changes the landing branch.
- **If human instructions contradict these fields**: stop and resolve the intended landing branch before coding.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback Details

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## ⚠️ Dependency Rebase Guidance

**If this WP depends on other WPs** (check frontmatter `dependencies:` field):

When a parent WP changes during review:
1. You'll need to rebase your workspace to get latest changes
2. Command: `cd .worktrees/{{feature_slug}}-{{work_package_id}} && git rebase {{feature_slug}}-{{base_wp_id}}`
3. Resolve any conflicts
4. Continue work on updated foundation

**Check if rebase needed**:
```bash
cd .worktrees/{{feature_slug}}-{{work_package_id}}
git log --oneline HEAD..{{base_branch}}  # Shows commits in the base branch that are not in your workspace yet
```

**If this WP has dependent WPs** (other WPs depend on this one):

When you make changes:
1. Notify agents working on dependent WPs
2. They'll need to rebase their workspaces to get your changes
3. This is a git limitation - future jj integration will auto-rebase

The `spec-kitty implement` command will display warnings when:
- You resume work and the base has changed
- You start work and other WPs depend on you

---

## Objectives & Success Criteria

- Summarize the exact outcomes that mark this work package complete.
- Call out key acceptance criteria or success metrics for the bundle.

## Context & Constraints

- Reference prerequisite work and related documents.
- Link to supporting specs: `.kittify/constitution/constitution.md`, `kitty-specs/.../plan.md`, `kitty-specs/.../tasks.md`, data model, contracts, research, quickstart.
- Highlight architectural decisions, constraints, or trade-offs to honor.

## Subtasks & Detailed Guidance

### Subtask TXXX – Replace with summary
- **Purpose**: Explain why this subtask exists.
- **Steps**: Detailed, actionable instructions.
- **Files**: Canonical paths to update or create.
- **Parallel?**: Note if this can run alongside others.
- **Notes**: Edge cases, dependencies, or data requirements.

### Subtask TYYY – Replace with summary
- Repeat the structure above for every included `Txxx` entry.

## Test Strategy (include only when tests are required)

- Specify mandatory tests and where they live.
- Provide commands or scripts to run.
- Describe fixtures or data seeding expectations.

## Risks & Mitigations

- List known pitfalls, performance considerations, or failure modes.
- Provide mitigation strategies or monitoring notes.

## Review Guidance

- Key acceptance checkpoints for `/spec-kitty.review`.
- Any context reviewers should revisit before approving.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:
1. Scroll to the bottom of this file (Activity Log section below "Valid lanes")
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – lane=<lane> – <action>`
4. Timestamp MUST be current time in UTC (ISO-8601 `YYYY-MM-DDTHH:MM:SSZ`) and should be generated without shell commands (prefer `NOW_UTC_ISO` from `check-prerequisites --json --paths-only`)
5. Lane MUST match the frontmatter `lane:` field exactly
6. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:
```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – lane=<lane> – <brief action description>
```

**Example (correct chronological order)**:
```
- 2026-01-12T10:00:00Z – system – lane=planned – Prompt created
- 2026-01-12T10:30:00Z – claude – lane=doing – Started implementation
- 2026-01-12T11:00:00Z – codex – lane=for_review – Implementation complete, ready for review
- 2026-01-12T11:30:00Z – claude – lane=done – Review passed, all tests passing  ← LATEST (at bottom)
```

**Common mistakes (DO NOT DO THIS)**:
- ❌ Adding new entry at the top (breaks chronological order)
- ❌ Using future timestamps (causes acceptance validation to fail)
- ❌ Lane mismatch: frontmatter says `lane: "done"` but log entry says `lane=doing`
- ❌ Inserting in middle instead of appending to end

**Why this matters**: The acceptance system reads the LAST activity log entry as the current state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:
- {{TIMESTAMP}} – system – lane=planned – Prompt created.

---

### Updating Lane Status

To change a work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry
2. **Use CLI**: `spec-kitty agent tasks move-task <WPID> --to <lane> --note "message"`

The CLI command updates both frontmatter and activity log automatically (recommended).

**Valid lanes**: `planned`, `doing`, `for_review`, `done`

### File Structure

All WP files live in a flat `tasks/` directory. The lane is determined by the `lane:` frontmatter field, not the directory location.
