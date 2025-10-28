---
work_package_id: "WPxx"
subtasks:
  - "Txxx"
title: "Replace with work package title"
phase: "Phase N - Replace with phase name"
lane: "planned"  # planned | doing | for_review | done
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

# Work Package Prompt: {{work_package_id}} – {{title}}

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

1. Capture your shell PID: `echo $$` (or use helper scripts when available).
2. Update frontmatter (`lane`, `assignee`, `agent`, `shell_pid`).
3. Add an entry to the **Activity Log** describing the transition.
4. Run `.kittify/scripts/bash/tasks-move-to-lane.sh <FEATURE> <WPID> <lane>` (PowerShell variant available) to move the prompt, update metadata, and append history in one step.
5. Commit or stage the change, preserving history.

### Optional Phase Subdirectories

For large features, organize prompts under `tasks/planned/phase-<n>-<label>/` to keep bundles grouped while maintaining lexical ordering.
