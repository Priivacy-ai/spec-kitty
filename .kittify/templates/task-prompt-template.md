---
work_package_id: "WPxx"
subtasks:
  - "Txxx"
title: "Replace with work package title"
phase: "Phase N - Replace with phase name"
lane: "planned"  # DO NOT EDIT - use: tasks_cli.py move <feature> <WP> <lane>
assignee: ""      # Optional friendly name when in doing/for_review
agent: ""         # CLI agent identifier (claude, codex, etc.)
shell_pid: ""     # PID captured when the task moved to the current lane
review_status: "" # empty | has_feedback | acknowledged (populated by reviewers/implementers)
reviewed_by: ""   # Agent ID of the reviewer (if reviewed)
history:
  - timestamp: "{{TIMESTAMP}}"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---
*Path: [templates/task-prompt-template.md](templates/task-prompt-template.md)*


# Work Package Prompt: {{work_package_id}} – {{title}}

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Objectives & Success Criteria

- Summarize the exact outcomes that mark this work package complete.
- Call out key acceptance criteria or success metrics for the bundle.

## Context & Constraints

- Reference prerequisite work and related documents.
- Link to supporting specs: `.kittify/memory/constitution.md`, `kitty-specs/.../plan.md`, `kitty-specs/.../tasks.md`, data model, contracts, research, quickstart.
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

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] Documentation updated (if needed)
- [ ] Metrics/telemetry added (if applicable)
- [ ] Observability/logging requirements satisfied
- [ ] `tasks.md` updated with status change

## Review Guidance

- Key acceptance checkpoints for `/spec-kitty.review`.
- Any context reviewers should revisit before approving.

## Activity Log

> Append entries when the work package changes lanes. Include timestamp, agent, shell PID, lane, and a short note.

- {{TIMESTAMP}} – system – lane=planned – Prompt created.

---

### Updating Metadata When Changing Lanes

**IMPORTANT: Never manually edit the `lane:` field.** The lane is determined by the file's directory location, not the YAML field. Editing the field without moving the file creates a mismatch that breaks the system.

**Always use the move command:**
```bash
python3 .kittify/scripts/tasks/tasks_cli.py move <FEATURE> <WPID> <lane> --note "Your note"
```

This command:
1. Moves the file to the correct `tasks/<lane>/` directory
2. Updates the `lane:` field in YAML
3. Updates `agent` and `shell_pid` metadata
4. Appends an entry to the Activity Log
5. Stages the changes for commit

You can add `--agent <name>` and `--shell-pid <pid>` flags for explicit metadata.

### Optional Phase Subdirectories

For large features, organize prompts under `tasks/planned/phase-<n>-<label>/` to keep bundles grouped while maintaining lexical ordering.
